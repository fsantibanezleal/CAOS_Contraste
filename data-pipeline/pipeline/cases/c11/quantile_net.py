"""R10 of the C11 ladder: a quantile network trained on the FZ0 loss (S-1 of the method tiers; state of the art).

A one-hidden-layer network maps the causal features of a day to the joint VaR and ES of that day's standardised return and is
trained by minimising the mean FZ0 loss (Fissler and Ziegel 2016; Patton, Ziegel and Chen 2019, arXiv 1707.05108 eq 6) over the
estimation window of the forecast day, ``y[i-w:i]``: the day itself and everything after it never enter a feature, a target or a
standardisation constant. The joint VaR and ES targets follow the neural joint-forecast line of work (the cross-sectional
ReSGA preprint, arXiv 2606.04576, is the motivation; this rung is the compact single-series network of that family, not ReSGA).

Design, in the order the numbers are made:

- ``features(y)``: for each day ``t`` of the window the five previous returns and their absolute values, each divided by the
  RiskMetrics volatility ``sigma_t`` (lambda 0.94, seeded on the window's first 20 days), and the log ratio of that volatility to a
  slow one (lambda 0.99). Every row reads ``y[:t]`` only.
- the network output is two positive numbers through a softplus: ``v = -softplus(o1)`` and ``e = v - softplus(o2)``, so that
  ``e <= v < 0`` always (the domain of FZ0). The target is ``y_t / sigma_t``; FZ0 is scale-covariant (it shifts by ``log c``), so a
  forecast is ``sigma * (v, e)`` of the standardised problem.
- ``fit_net``: Adam, full batch, ``n_starts`` seeded starts, the lowest final training loss wins; the seed and every count are
  fixed by the compute budget and the determinism rule (``NetHyper``), never tuned on a test window.

Torch is used for the gradient of the loss only (a CPU wheel, BSD-3-Clause); the forward pass of a forecast is plain numpy. The
engine has no neural rung, so this is the pipeline's own code (the engine's FZ0 is numpy and has no gradient); the loss here is
checked against the engine's ``fz0_loss`` by ``tests/c11/test_c11_quantile_net.py``.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy.signal import lfilter
from scipy.stats import norm

LAGS = 5
SEED_DAYS = 20          # the volatility recursions start from the variance of the window's first days
FIRST_ROW = 60          # the first day with a full feature row
LAMBDA_FAST, LAMBDA_SLOW = 0.94, 0.99
MIN_TRAIN_ROWS = 100
N_FEATURES = 2 * LAGS + 1


@dataclass(frozen=True)
class NetHyper:
    """Fixed by the compute budget and the determinism rule, not tuned (no span search): the network is deliberately small."""

    hidden_units: int = 8
    epochs: int = 200
    learning_rate: float = 0.02
    weight_decay: float = 1e-3
    n_starts: int = 3
    refit_every_days: int = 20

    def to_json(self) -> dict:
        return asdict(self)


NET = NetHyper()


@dataclass(frozen=True)
class NetFit:
    w1: np.ndarray
    b1: np.ndarray
    w2: np.ndarray
    b2: np.ndarray
    mu: np.ndarray
    sd: np.ndarray
    train_fz0: float
    converged: bool


def _ewma_variance(y: np.ndarray, lam: float) -> np.ndarray:
    """``v[t]`` for t = SEED_DAYS+1 .. n, the variance after reading ``y[:t]`` (``v[n]`` is the forecast day's)."""
    v0 = float(np.var(y[:SEED_DAYS]))
    out = lfilter([1.0 - lam], [1.0, -lam], y[SEED_DAYS:] ** 2, zi=[lam * v0])[0]
    return out


def features(y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Rows for the days t = FIRST_ROW .. len(y) (the last row is the day after the window) and their volatility ``sigma_t``."""
    y = np.asarray(y, dtype=float)
    n = y.size
    if n < FIRST_ROW + 1:
        raise ValueError(f"{n} observed days: the features need at least {FIRST_ROW + 1}")
    fast, slow = _ewma_variance(y, LAMBDA_FAST), _ewma_variance(y, LAMBDA_SLOW)
    off = FIRST_ROW - (SEED_DAYS + 1)                        # v[0] is the day SEED_DAYS + 1
    sf, ss = np.sqrt(fast[off:]), np.sqrt(slow[off:])
    t = np.arange(FIRST_ROW, n + 1)
    if np.any(sf <= 0.0) or not np.all(np.isfinite(sf)):
        raise ValueError("the volatility of the window collapsed to zero")
    cols = [y[t - k] / sf for k in range(1, LAGS + 1)] + [np.abs(y[t - k]) / sf for k in range(1, LAGS + 1)] + [np.log(sf / ss)]
    return np.column_stack(cols), sf


def net_loss(y, v, e, alpha: float):
    """The mean FZ0 loss as a torch expression (so it has a gradient): ``-(1/(alpha e)) 1{y<=v}(v-y) + v/e + log(-e) - 1``."""
    import torch

    hit = (y <= v).to(v.dtype)
    return torch.mean(-(1.0 / (alpha * e)) * hit * (v - y) + v / e + torch.log(-e) - 1.0)


def _inv_softplus(x: float) -> float:
    return float(np.log(np.expm1(x)))


def fit_net(win: np.ndarray, alpha: float, nh: NetHyper, seed: int) -> NetFit:
    """Train on the days of ``win`` only. A window too short or with no volatility is a ValueError (a failed fit)."""
    import torch

    torch.set_num_threads(1)
    win = np.asarray(win, dtype=float)
    if not np.all(np.isfinite(win)):
        raise ValueError("the window holds a non-finite return")
    x_all, sig = features(win)
    x, z = x_all[:-1], win[FIRST_ROW:] / sig[:-1]            # rows t < n and their standardised targets y_t / sigma_t
    if x.shape[0] < MIN_TRAIN_ROWS:
        raise ValueError(f"{x.shape[0]} training rows: at least {MIN_TRAIN_ROWS} are needed")
    mu, sd = x.mean(axis=0), np.maximum(x.std(axis=0), 1e-8)
    xt = torch.tensor((x - mu) / sd, dtype=torch.float64)
    zt = torch.tensor(z, dtype=torch.float64)
    q0 = abs(float(norm.ppf(alpha)))
    bias = torch.tensor([_inv_softplus(q0), _inv_softplus(0.15 * q0)], dtype=torch.float64)
    best: tuple[float, tuple] | None = None
    for s in range(nh.n_starts):
        g = torch.Generator().manual_seed(int(seed) * 1000 + s)
        w1 = (torch.randn(N_FEATURES, nh.hidden_units, generator=g, dtype=torch.float64) / np.sqrt(N_FEATURES)).requires_grad_()
        b1 = torch.zeros(nh.hidden_units, dtype=torch.float64, requires_grad=True)
        w2 = (0.1 * torch.randn(nh.hidden_units, 2, generator=g, dtype=torch.float64)).requires_grad_()
        b2 = bias.clone().requires_grad_()
        opt = torch.optim.Adam([w1, b1, w2, b2], lr=nh.learning_rate, weight_decay=nh.weight_decay)

        def loss_of():
            o = torch.tanh(xt @ w1 + b1) @ w2 + b2
            v = -torch.nn.functional.softplus(o[:, 0])
            e = v - torch.nn.functional.softplus(o[:, 1])
            return net_loss(zt, v, e, alpha)

        for _ in range(nh.epochs):
            opt.zero_grad()
            loss = loss_of()
            if not torch.isfinite(loss):
                break
            loss.backward()
            opt.step()
        with torch.no_grad():
            final = float(loss_of())
        if np.isfinite(final) and (best is None or final < best[0]):
            best = (final, tuple(p.detach().numpy().copy() for p in (w1, b1, w2, b2)))
    if best is None:
        raise RuntimeError("the network did not reach a finite training loss in any start")
    return NetFit(*best[1], mu, sd, best[0], True)


def predict(fit: NetFit, win: np.ndarray) -> tuple[float, float]:
    """The VaR and ES (return convention, negative) of the day after ``win``, from ``win`` and the fitted weights."""
    x, sig = features(win)
    h = np.tanh(((x[-1] - fit.mu) / fit.sd) @ fit.w1 + fit.b1)
    o = h @ fit.w2 + fit.b2
    v = -float(np.logaddexp(0.0, o[0]))
    e = v - float(np.logaddexp(0.0, o[1]))
    return float(sig[-1]) * v, float(sig[-1]) * e
