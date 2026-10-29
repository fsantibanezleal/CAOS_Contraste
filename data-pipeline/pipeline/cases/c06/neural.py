"""The L3 rung of the C06 ladder (S-4, method tiers plan): PC-Hazard, a neural discrete-time survival model.

Kvamme and Borgan (2019, "Continuous and discrete-time survival prediction with neural networks", arXiv 1910.06724) assume a
hazard that is piecewise constant on a grid of intervals and let a feed-forward network map the covariates of a loan to the
hazard rate of every interval. The likelihood of a loan observed for a time ``t`` (default at ``t`` when ``event``) is

    event * log(rate[j(t)]) - sum_j rate[j] * exposure_j(t)

with ``exposure_j(t)`` the time the loan spent in interval ``j``. This is the Poisson likelihood of the interval counts, so
the data enter only through two tables, the defaults and the exposure of each (stratum, interval) cell (``interval_statistics``):
the training is exact, full batch and deterministic, and costs the same on 1.7 million loans as on a few thousand.

The rung stands on the same information as the Cox rung (L2): the loan covariates of ``ladder.static_design`` (size, term,
sector, revolver) and loan age in months as the time scale, trained on the loans as known at the reporting date, prepayment
and maturity censoring (``competing_prepayment`` false). What it adds is the shape: no proportional hazards, a free age
profile per stratum. Whether that shape beats Cox out of time is what the evaluation (``backtest``) measures and the models
document reports, win or lose.

Network: ``F`` dummy columns, two hidden layers of 32 ReLU units, ``N_INTERVALS`` outputs through a softplus (a positive rate per
month). The last bias starts at the pooled rate of each interval. Adam with L2 weight decay, full batch; a seeded random fifth of
the loans is held out and the epoch of the lowest hold-out loss is kept (early stopping). The seed is fixed per reporting date.

``torch`` (BSD-3-Clause family, see ``data-pipeline/config/licences.json``) is imported when a network is fitted, never at import
time, so the other rungs do not need it. The Aalen-Johansen estimator below is the observed side of the calibration.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np

from .ladder import Status, check_enough, static_design
from .panel import N_STRATA, Loans, Observation

#: intervals of ``WIDTH`` months of loan age: 60 quarters, 15 years; the last interval is open (its rate holds beyond)
N_INTERVALS = 60
WIDTH = 3.0
SEED = 4506
HIDDEN = (32, 32)
LEARNING_RATE = 0.01
WEIGHT_DECAY = 1e-4
MAX_EPOCHS = 1500
PATIENCE = 60
VAL_SHARE = 0.2
RATE_FLOOR = 1e-10


# ---------------------------------------------------------------------------------------------------------------------
# the sufficient statistics and the curve of a piecewise-constant hazard


def interval_statistics(stratum: np.ndarray, time: np.ndarray, event: np.ndarray, *, n_strata: int = N_STRATA,
                        n_intervals: int = N_INTERVALS, width: float = WIDTH) -> tuple[np.ndarray, np.ndarray]:
    """``(events, exposure)``, each ``(n_strata, n_intervals)``: the defaults that fall in each interval and the months
    of observation spent in it. A loan observed for ``time`` months spends a full ``width`` in every interval before the one
    that holds ``time`` and ``time`` minus the interval's start in that one; the last interval is open, so it takes all the time
    past its start."""
    j = np.minimum(np.floor(np.asarray(time, dtype=float) / width).astype(np.int64), n_intervals - 1)
    partial = np.asarray(time, dtype=float) - width * j
    flat = np.asarray(stratum, dtype=np.int64) * n_intervals + j
    size = n_strata * n_intervals
    ends = np.bincount(flat, minlength=size).reshape(n_strata, n_intervals).astype(float)
    part = np.bincount(flat, weights=partial, minlength=size).reshape(n_strata, n_intervals)
    events = np.bincount(flat[np.asarray(event, dtype=bool)], minlength=size).reshape(n_strata, n_intervals).astype(float)
    later = np.cumsum(ends[:, ::-1], axis=1)[:, ::-1] - ends     # loans whose terminal interval comes after j
    return events, width * later + part


def cumulative_hazard(rates: np.ndarray, stratum: np.ndarray, t: np.ndarray, width: float = WIDTH) -> np.ndarray:
    """The integrated hazard at ``t`` months (accounts by points) of the rates ``(strata, intervals)`` per month."""
    m = rates.shape[1]
    knots = np.concatenate([np.zeros((rates.shape[0], 1)), np.cumsum(rates * width, axis=1)], axis=1)   # H at the interval starts
    j = np.minimum(np.floor(t / width).astype(np.int64), m - 1)
    s = np.asarray(stratum, dtype=np.int64)[:, None]
    return knots[s, j] + rates[s, j] * (t - width * j)


def conditional_cumulative_pd(rates: np.ndarray, stratum: np.ndarray, age_months: np.ndarray, horizon_months: np.ndarray,
                              width: float = WIDTH) -> np.ndarray:
    """P(default within ``h`` more months | alive at ``age``) = 1 - exp(-(H(age + h) - H(age))), accounts by horizons. The
    horizons are ``(H,)`` for all accounts or ``(A, H)``."""
    age = np.asarray(age_months, dtype=float)
    h = np.broadcast_to(np.asarray(horizon_months, dtype=float), (age.shape[0], np.asarray(horizon_months).shape[-1]))
    ahead = cumulative_hazard(rates, stratum, age[:, None] + h, width)
    base = cumulative_hazard(rates, stratum, age[:, None], width)
    return 1.0 - np.exp(-(ahead - base))


# ---------------------------------------------------------------------------------------------------------------------
# the network


@dataclass(frozen=True)
class NetFit:
    rates: np.ndarray                 # (rows of x, intervals) hazard rate per month
    weights_sha256: str
    n_parameters: int
    best_epoch: int
    epochs: int
    train_nll: float
    val_nll: float
    train_nll_curve: np.ndarray = field(default_factory=lambda: np.zeros(0))
    val_nll_curve: np.ndarray = field(default_factory=lambda: np.zeros(0))
    hidden: tuple[int, ...] = HIDDEN


def _inverse_softplus(y: np.ndarray) -> np.ndarray:
    return np.log(np.expm1(y))


def fit_network(x: np.ndarray, events: np.ndarray, exposure: np.ndarray, *, val_events: np.ndarray | None = None,
                val_exposure: np.ndarray | None = None, seed: int = SEED, hidden: tuple[int, ...] = HIDDEN,
                learning_rate: float = LEARNING_RATE, weight_decay: float = WEIGHT_DECAY, max_epochs: int = MAX_EPOCHS,
                patience: int = PATIENCE) -> NetFit:
    """Train the PC-Hazard network on the interval statistics of the rows of ``x`` (full batch, float64, CPU, ``seed``).
    The loss is the negative log-likelihood per training default; early stopping reads the hold-out loss
    (the training loss when no hold-out is given). Returns the rates of every row of ``x``."""
    import torch

    torch.manual_seed(seed)
    torch.set_num_threads(1)
    dt = torch.float64
    xt = torch.as_tensor(np.asarray(x, dtype=float), dtype=dt)
    ev = torch.as_tensor(np.asarray(events, dtype=float), dtype=dt)
    ex = torch.as_tensor(np.asarray(exposure, dtype=float), dtype=dt)
    has_val = val_events is not None and val_exposure is not None
    vev = torch.as_tensor(np.asarray(val_events if has_val else events, dtype=float), dtype=dt)
    vex = torch.as_tensor(np.asarray(val_exposure if has_val else exposure, dtype=float), dtype=dt)
    n_in, m = xt.shape[1], ev.shape[1]
    sizes = (n_in, *hidden)
    layers: list = []
    for a, b in zip(sizes[:-1], sizes[1:], strict=True):
        layers += [torch.nn.Linear(a, b), torch.nn.ReLU()]
    out = torch.nn.Linear(sizes[-1], m)
    pooled = np.maximum(ev.sum(0).numpy() / np.maximum(ex.sum(0).numpy(), 1e-12), 1e-6)
    with torch.no_grad():
        out.bias.copy_(torch.as_tensor(_inverse_softplus(pooled), dtype=dt))
    net = torch.nn.Sequential(*layers, out).to(dt)

    def rates_of(inp):
        return torch.nn.functional.softplus(net(inp)) + RATE_FLOOR

    def nll(rate, e, x_):
        return -((e * torch.log(rate)).sum() - (rate * x_).sum()) / torch.clamp(e.sum(), min=1.0)

    opt = torch.optim.Adam(net.parameters(), lr=learning_rate, weight_decay=weight_decay)
    train_curve, val_curve = [], []
    best, best_state, best_epoch, since = float("inf"), None, 0, 0
    for epoch in range(1, max_epochs + 1):
        net.train()
        opt.zero_grad()
        loss = nll(rates_of(xt), ev, ex)
        loss.backward()
        opt.step()
        with torch.no_grad():
            r = rates_of(xt)
            tr, va = float(nll(r, ev, ex)), float(nll(r, vev, vex))
        train_curve.append(tr)
        val_curve.append(va)
        if va < best - 1e-12:
            best, best_epoch, since = va, epoch, 0
            best_state = {k: v.detach().clone() for k, v in net.state_dict().items()}
        else:
            since += 1
            if since >= patience:
                break
    net.load_state_dict(best_state)
    with torch.no_grad():
        rates = rates_of(xt).numpy()
    digest = hashlib.sha256()
    for k in sorted(best_state):
        digest.update(k.encode())
        digest.update(np.ascontiguousarray(best_state[k].numpy(), dtype="<f8").tobytes())
    return NetFit(rates=rates, weights_sha256=digest.hexdigest(), n_parameters=int(sum(p.numel() for p in net.parameters())),
                  best_epoch=best_epoch, epochs=len(val_curve), train_nll=train_curve[best_epoch - 1], val_nll=best,
                  train_nll_curve=np.array(train_curve), val_nll_curve=np.array(val_curve), hidden=tuple(hidden))


# ---------------------------------------------------------------------------------------------------------------------
# the rung on the loans


@dataclass(frozen=True)
class PchModel:
    status: Status
    names: tuple[str, ...] = ()
    keep: tuple[int, ...] = ()
    rates: np.ndarray = field(default_factory=lambda: np.zeros((0, 0)))     # (N_STRATA, N_INTERVALS) per month
    weights_sha256: str | None = None
    n_parameters: int = 0
    best_epoch: int = 0
    epochs: int = 0
    train_nll: float = float("nan")
    val_nll: float = float("nan")
    n_train_loans: int = 0
    n_val_loans: int = 0
    seed: int = 0
    hidden: tuple[int, ...] = HIDDEN

    def cumulative(self, stratum: np.ndarray, age_months: np.ndarray, horizon_months: np.ndarray) -> np.ndarray:
        """P(default by age + h | alive at age) for accounts (A,) by horizons (H,), as ``CoxModel.cumulative``."""
        return conditional_cumulative_pd(self.rates, stratum, age_months, np.asarray(horizon_months, dtype=float))


def fit_pch(loans: Loans, obs: Observation, *, reporting_date: np.datetime64, seed: int = SEED) -> PchModel:
    """Fit L3 on the loans selected at ``obs.reporting_date``, time in months of loan age plus a half month (as Cox)."""
    sel = np.flatnonzero(obs.selected)
    n, d = int(sel.size), int(obs.event.sum())
    status = check_enough(n, d, "L3-pch")
    if not status.evaluated:
        return PchModel(status=status)
    stratum = loans.stratum[sel]
    time = obs.age_months[sel].astype(float) + 0.5
    event = obs.event[sel]
    present = np.flatnonzero(np.bincount(stratum, minlength=N_STRATA) > 0)
    design, names = static_design(np.arange(N_STRATA))
    keep = [k for k in range(design.shape[1]) if np.ptp(design[present, k]) > 0.0]
    day = int(np.datetime64(reporting_date, "D").astype(np.int64))
    seed_run = int(seed) + day
    val = np.random.default_rng([int(seed), day]).random(n) < VAL_SHARE
    ev_t, ex_t = interval_statistics(stratum[~val], time[~val], event[~val])
    ev_v, ex_v = interval_statistics(stratum[val], time[val], event[val])
    fit = fit_network(design[:, keep], ev_t, ex_t, val_events=ev_v, val_exposure=ex_v, seed=seed_run)
    return PchModel(status=status, names=tuple(names[k] for k in keep), keep=tuple(keep), rates=fit.rates,
                    weights_sha256=fit.weights_sha256, n_parameters=fit.n_parameters, best_epoch=fit.best_epoch, epochs=fit.epochs,
                    train_nll=fit.train_nll, val_nll=fit.val_nll, n_train_loans=int((~val).sum()), n_val_loans=int(val.sum()),
                    seed=seed_run, hidden=fit.hidden)


# ---------------------------------------------------------------------------------------------------------------------
# Aalen-Johansen, the observed cumulative incidence when a competing cause exists


def aalen_johansen(time: np.ndarray, cause: np.ndarray, horizons: np.ndarray, target: int = 1) -> np.ndarray:
    """Cumulative incidence of cause ``target`` at each horizon: ``cause`` is 0 for a censored observation, 1, 2, ... for the
    cause of an exit. At an event time with ``n`` at risk, ``d`` exits of any cause and ``d_c`` of the target, the incidence
    gains ``S(t-) * d_c / n`` with ``S`` the overall (any cause) Kaplan-Meier. A horizon beyond the last event time takes the
    last value (the caller limits the horizons to the follow-up)."""
    time = np.asarray(time, dtype=float)
    cause = np.asarray(cause)
    horizons = np.asarray(horizons, dtype=float)
    hit = cause > 0
    if not hit.any():
        return np.zeros(horizons.shape)
    ut, inv = np.unique(time[hit], return_inverse=True)
    d_all = np.bincount(inv).astype(float)
    d_tar = np.bincount(inv, weights=(cause[hit] == target).astype(float))
    order = np.sort(time)
    at_risk = (time.size - np.searchsorted(order, ut, side="left")).astype(float)
    surv = np.cumprod(1.0 - d_all / at_risk)
    prev = np.concatenate([[1.0], surv[:-1]])
    cif = np.cumsum(prev * d_tar / at_risk)
    pos = np.searchsorted(ut, horizons, side="right") - 1
    return np.where(pos >= 0, cif[np.clip(pos, 0, None)], 0.0)


__all__ = ["N_INTERVALS", "NetFit", "PchModel", "SEED", "WIDTH", "aalen_johansen", "conditional_cumulative_pd", "cumulative_hazard",
           "fit_network", "fit_pch", "interval_statistics"]
