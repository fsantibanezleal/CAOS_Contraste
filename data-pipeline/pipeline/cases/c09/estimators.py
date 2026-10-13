"""The CCF observations, treatments and estimates of C09, every number returned by ``riskvalidation`` 0.6.0 (CT-905, CT-906, CT-907).

``observe`` reads each defaulter's balance path at the reference dates of a design through ``ccf.reference_indices`` and
``ccf.ccf_observations``; ``treat`` applies a named treatment through ``ccf.treat_ccf``; ``aggregate`` returns the estimate through
``ccf.aggregate_ccf``. The product selects, subsets and counts; it computes no CCF, no treatment and no aggregate. Engine functions
are called through their module (``ccf.treat_ccf``), so a test can replace one and see every number change.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from riskvalidation.lgd_ead import ccf, lgd_models
from riskvalidation.lgd_ead.workout import range_flag

from .generator import Defaulters
from .params import HORIZON

DESIGNS = ("fixed-horizon", "cohort", "variable-horizon")
TREATMENTS = ("none", "censor", "floor-cap", "bounded-scale")
ESTIMATORS = ("mean", "pooled")
FEATURE_NAMES = ("intercept", "utilisation", "log_limit", "credit_score")


@dataclass(frozen=True)
class Observations:
    """The (facility, reference date) observations of one design on one replication (or several, concatenated)."""

    design: str
    fac: np.ndarray             # (K,) index of the defaulter
    ccf: np.ndarray             # (K,) NaN where the undrawn amount at the reference date is not positive
    undrawn: np.ndarray
    drawn_ref: np.ndarray
    limit_ref: np.ndarray
    ead: np.ndarray             # the realised EAD of the facility
    score: np.ndarray
    n_defaults: int             # defaulters of the replication(s)
    n_excluded: int             # defaulters the design cannot place a reference date before (cohort: a default in its first month)


def observe(d: Defaulters, design: str) -> Observations:
    fac, cc, un, dr, li, ea, sc = [], [], [], [], [], [], []
    excluded = 0
    t = d.drawn.shape[1]
    for i in range(d.ead.size):
        td = int(d.default_month[i])
        if design == "cohort":
            start = 12 * (td // 12)
            if start >= td:
                excluded += 1
                continue
            idx = ccf.reference_indices("cohort", td, cohort_start_index=start, horizon=HORIZON)
        else:
            idx = ccf.reference_indices(design, td, horizon=HORIZON, n_reference=4, step=3)
        limit = np.full(t, d.limit[i])
        c, u = ccf.ccf_observations(d.drawn[i], limit, float(d.ead[i]), idx)
        k = idx.size
        fac.append(np.full(k, i))
        cc.append(c)
        un.append(u)
        dr.append(d.drawn[i][idx])
        li.append(np.full(k, d.limit[i]))
        ea.append(np.full(k, d.ead[i]))
        sc.append(np.full(k, d.score[i]))
    cat = lambda xs, dt=float: np.concatenate(xs) if xs else np.empty(0, dtype=dt)  # noqa: E731
    return Observations(design, cat(fac, int), cat(cc), cat(un), cat(dr), cat(li), cat(ea), cat(sc), int(d.ead.size), excluded)


def join(parts: list[Observations]) -> Observations:
    """Several replications' observations as one sample (the facility indices stay unique by offset)."""
    off = np.cumsum([0] + [p.n_defaults for p in parts[:-1]])
    return Observations(parts[0].design, np.concatenate([p.fac + o for p, o in zip(parts, off, strict=True)]),
                        *(np.concatenate([getattr(p, f) for p in parts]) for f in ("ccf", "undrawn", "drawn_ref", "limit_ref", "ead", "score")),
                        sum(p.n_defaults for p in parts), sum(p.n_excluded for p in parts))


@dataclass(frozen=True)
class Treated:
    values: np.ndarray          # the CCFs that remain after the treatment
    undrawn: np.ndarray         # the undrawn amounts of those observations
    mask: np.ndarray            # (K,) which observations of the sample remain
    n_undefined: int            # NaN: no undrawn amount at the reference date
    n_finite: int
    n_below_zero: int           # counted before the treatment, as ``ccf.treat_ccf`` returns them
    n_above_one: int
    n_dropped: int


def treat(obs: Observations, treatment: str) -> Treated:
    finite = np.isfinite(obs.ccf)
    t = ccf.treat_ccf(obs.ccf, treatment)
    mask = finite & (obs.ccf >= 0.0) & (obs.ccf <= 1.0) if treatment == "censor" else finite
    if t.values.size != int(mask.sum()):
        raise ValueError(f"treatment {treatment}: the engine kept {t.values.size} observations, the subset has {int(mask.sum())}")
    return Treated(t.values, obs.undrawn[mask], mask, int((~finite).sum()), int(finite.sum()), int(t.n_below_zero), int(t.n_above_one),
                   int(t.n_dropped))


@dataclass(frozen=True)
class Estimate:
    value: float
    flag: str
    n_facilities: int           # distinct defaulters that contribute
    n_observations: int
    n_undefined: int
    share_below_zero: float
    share_above_one: float


def features(obs: Observations) -> np.ndarray:
    """The covariates read at the reference date: utilisation, ln(limit / e^8) and the credit score in hundreds from 700."""
    return np.column_stack([np.ones(obs.ccf.size), obs.drawn_ref / obs.limit_ref, np.log(obs.limit_ref) - 8.0, (obs.score - 700.0) / 100.0])


def aggregate(obs: Observations, treatment: str, estimator: str, fit: lgd_models.LgdFit | None = None) -> Estimate:
    """The estimate of one design, treatment and aggregator. ``bounded-scale`` needs the fractional logit ``fit`` and returns the
    mean (or the undrawn-weighted mean) of its predicted CCF over the observations."""
    tr = treat(obs, treatment)
    if treatment == "bounded-scale":
        if fit is None:
            raise ValueError("the bounded-scale estimate is the predicted mean of a fractional logit: pass its fit")
        values = lgd_models.predict_lgd(fit, features(obs)[tr.mask])
    else:
        values = tr.values
    value = float(ccf.aggregate_ccf(values, tr.undrawn, estimator))
    n_fac = int(np.unique(obs.fac[tr.mask]).size)
    return Estimate(value, str(range_flag(np.array([value]))[0]), n_fac, int(tr.mask.sum()), tr.n_undefined,
                    tr.n_below_zero / tr.n_finite if tr.n_finite else 0.0, tr.n_above_one / tr.n_finite if tr.n_finite else 0.0)


def thin(obs: Observations, k: int) -> Observations:
    """Every k-th observation, in sample order (k = 1 is the whole sample)."""
    m = np.arange(obs.ccf.size) % k == 0
    return Observations(obs.design, obs.fac[m], obs.ccf[m], obs.undrawn[m], obs.drawn_ref[m], obs.limit_ref[m], obs.ead[m], obs.score[m],
                        obs.n_defaults, obs.n_excluded)


#: the engine's fractional-logit solver compares log-likelihoods of the order of the sample size to 1e-14, so on a pooled sample of
#: tens of thousands of observations it can stall at the optimum and report non-convergence (found in the C09 bake, reported to the
#: engine owner); the fit is then repeated on every k-th observation, and the thinning used is written in the document
THINNING = (1, 2, 3, 4, 6, 8)


def fit_robust(fit_fn, obs: Observations):
    """``fit_fn(obs)`` on the whole sample, or on the first thinning of the sample on which the engine's solver converges.
    Returns ``(fit, k)``; any other error is raised."""
    last: Exception | None = None
    for k in THINNING:
        try:
            return fit_fn(thin(obs, k) if k > 1 else obs), k
        except ValueError as exc:
            if "did not converge" not in str(exc):
                raise
            last = exc
    raise ValueError(f"the engine's fractional logit did not converge on any thinning of the sample: {last}")


def fit_bounded(obs: Observations) -> tuple[lgd_models.LgdFit, int]:
    """The fractional logit of the bounded-scale CCFs (clipped to [0, 1] by ``treat_ccf``) on the reference-date covariates, and the
    thinning of the sample it was fitted on."""
    def fit(o: Observations) -> lgd_models.LgdFit:
        tr = treat(o, "bounded-scale")
        return lgd_models.fit_fractional_logit(features(o)[tr.mask], tr.values, FEATURE_NAMES)

    return fit_robust(fit, obs)
