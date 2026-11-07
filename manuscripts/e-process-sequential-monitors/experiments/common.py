"""Numerics shared by the experiment scripts of the e-process manuscript.

The engine ``riskvalidation.validation.sequential`` (release 1.1.0) supplies the e-process monitors and its generators
supply the hit streams and the default counts. This module holds what the engine does not: the comparators that read a
back-test every day (the Kupiec test on a growing or a trailing window, the Basel traffic light, Christoffersen's
independence test), the group-sequential and change-detection comparators whose boundary is calibrated by simulation to the
same size (Sidak correction, a constant Kupiec critical value, a CUSUM), the published e-backtest of Wang, Wang and Ziegel
(2022) for VaR with the growth-rate betting rule they give, the Beta mixture e-process, and the summary statistics (Wilson
intervals, bootstrap intervals of a median).

Every function is vectorised over the replications: arrays are (replications, days) and a day is 1-based in the results.
"""
from __future__ import annotations

import math
import pathlib
from typing import Any

import numpy as np
from scipy import special, stats

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DERIVED = ROOT / "data" / "derived"

ALPHA, LEVEL, WINDOW, HORIZON = 0.01, 0.05, 250, 1000
CROSS = -math.log(LEVEL)
INF = math.inf
FIRST_LOOK = 50  # the growing-window Kupiec test is read from day 50, the engine evaluation's convention


# ---------------------------------------------------------------------------------------------------------------------
# summaries

def first_true(mask: np.ndarray, start: int = 0) -> np.ndarray:
    """The 1-based first column at or after ``start`` (0-based) where the row is true, infinity when it never is."""
    m = mask[:, start:]
    any_ = m.any(axis=1)
    idx = np.argmax(m, axis=1) + start + 1
    return np.where(any_, idx, INF).astype(float)


def wilson(k: float, n: int, z: float = 1.959964) -> tuple[float, float]:
    """The Wilson 95 % interval of a proportion ``k / n``."""
    p = k / n
    d = 1.0 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def _finite(x: float) -> float | None:
    return None if not math.isfinite(x) else float(x)


def boot_median(days: np.ndarray, rng: np.random.Generator, b: int = 2000) -> tuple[float | None, float | None]:
    """The 95 % percentile-bootstrap interval of the median of ``days`` (infinity for a series that never rejects); an
    infinite end is reported as ``None`` (the median exceeds the horizon)."""
    n = days.size
    idx = rng.integers(0, n, size=(b, n))
    med = np.median(days[idx], axis=1)
    with np.errstate(invalid="ignore"):
        lo, hi = np.percentile(med, [2.5, 97.5])
    return _finite(lo), _finite(hi)


def summarise(days: np.ndarray, by: int, rng: np.random.Generator) -> dict[str, Any]:
    """The readings of one method on one scenario: the share of series rejected at some day of the horizon and by day
    ``by`` (each with its Wilson interval), the median first-rejection day over all series (``None`` when more than half
    never reject) with its bootstrap interval, and the median among the rejected series."""
    n = days.size
    fin = np.isfinite(days)
    k_ever, k_by = int(fin.sum()), int((days <= by).sum())
    med = float(np.median(days))
    lo, hi = boot_median(days, rng)
    return {
        "n": int(n), "ever": k_ever / n, "ever_ci": list(wilson(k_ever, n)),
        "by": k_by / n, "by_ci": list(wilson(k_by, n)),
        "median_day": _finite(med), "median_ci": [lo, hi],
        "median_day_among_detected": float(np.median(days[fin])) if fin.any() else None,
    }


# ---------------------------------------------------------------------------------------------------------------------
# fixed-window comparators read every day

def kupiec_lr(k: np.ndarray, t: np.ndarray, p: float) -> np.ndarray:
    """Kupiec's proportion-of-failures likelihood ratio, ``k`` exceptions in ``t`` days against the rate ``p``."""
    pi = np.where(t > 0, k / np.maximum(t, 1), 0.0)
    lr = -2.0 * (special.xlogy(t - k, 1 - p) + special.xlogy(k, p) - special.xlogy(t - k, 1 - pi) - special.xlogy(k, pi))
    return np.maximum(lr, 0.0)


def kupiec_reject(k: np.ndarray, t: np.ndarray, p: float, level: float = LEVEL) -> np.ndarray:
    return stats.chi2.sf(kupiec_lr(k, t, p), 1) < level


def cumulative_lr(h: np.ndarray, p: float) -> np.ndarray:
    """The Kupiec statistic of every growing window ``1..t``, columns 0-based; columns before ``FIRST_LOOK`` are zero."""
    c = np.cumsum(h, axis=1).astype(float)
    days = np.arange(1, h.shape[1] + 1, dtype=float)
    lr = kupiec_lr(c, np.broadcast_to(days, c.shape), p)
    lr[:, : FIRST_LOOK - 1] = 0.0
    return lr


def trailing_kupiec(h: np.ndarray, p: float, window: int = WINDOW, level: float = LEVEL) -> np.ndarray:
    """The Kupiec test on the trailing ``window`` days, true from day ``window`` where the p-value is below ``level``."""
    c0 = np.concatenate([np.zeros((h.shape[0], 1)), np.cumsum(h, axis=1).astype(float)], axis=1)
    tr = c0[:, window:] - c0[:, :-window]
    out = np.zeros(h.shape, dtype=bool)
    out[:, window - 1:] = kupiec_reject(tr, np.full(tr.shape, float(window)), p, level)
    return out


def traffic_light_days(h: np.ndarray, window: int = WINDOW, coverage: float = 0.99) -> tuple[np.ndarray, int]:
    """The first day on which the trailing-window exception count is outside the green zone of the Basel traffic light
    (the engine's own zone function sets the smallest non-green count), per series; infinity when it never is."""
    from riskvalidation.market import frtb

    k_min = next(k for k in range(window + 1) if frtb.traffic_light_zone(k, window, coverage) != "green")
    c0 = np.concatenate([np.zeros((h.shape[0], 1)), np.cumsum(h, axis=1)], axis=1)
    out = np.zeros(h.shape, dtype=bool)
    for t in range(window, h.shape[1] + 1):
        out[:, t - 1] = (c0[:, t] - c0[:, t - window]) >= k_min
    return first_true(out, window - 1), int(k_min)


def independence_reject(h: np.ndarray, window: int = WINDOW, level: float = LEVEL) -> np.ndarray:
    """Christoffersen's independence likelihood ratio on the trailing ``window`` days, read every day from ``window``."""
    a, b = h[:, :-1].astype(float), h[:, 1:].astype(float)
    pairs = {"00": (1 - a) * (1 - b), "01": (1 - a) * b, "10": a * (1 - b), "11": a * b}
    n_rows, n_cols = h.shape
    cs = {k: np.concatenate([np.zeros((n_rows, 1)), np.cumsum(v, axis=1)], axis=1) for k, v in pairs.items()}
    out = np.zeros((n_rows, n_cols), dtype=bool)
    w = window - 1
    with np.errstate(divide="ignore", invalid="ignore"):
        for t in range(window, n_cols + 1):
            n00, n01, n10, n11 = (cs[k][:, t - 1] - cs[k][:, t - 1 - w] for k in ("00", "01", "10", "11"))
            pi = (n01 + n11) / (n00 + n01 + n10 + n11)
            d0, d1 = n00 + n01, n10 + n11
            pi01 = np.divide(n01, d0, out=np.zeros_like(n01), where=d0 > 0)
            pi11 = np.divide(n11, d1, out=np.zeros_like(n11), where=d1 > 0)
            null = special.xlogy(n00 + n10, 1 - pi) + special.xlogy(n01 + n11, pi)
            alt = (special.xlogy(n00, 1 - pi01) + special.xlogy(n01, pi01) + special.xlogy(n10, 1 - pi11)
                   + special.xlogy(n11, pi11))
            lr = np.maximum(-2.0 * (null - alt), 0.0)
            out[:, t - 1] = (stats.chi2.sf(lr, 1) < level) & (lr > 0)
    return out


# ---------------------------------------------------------------------------------------------------------------------
# comparators calibrated to the same size by simulation

def sidak_level(looks: int, level: float = LEVEL) -> float:
    """The per-look level of ``looks`` tests whose family-wise size is ``level`` when the looks are independent."""
    return 1.0 - (1.0 - level) ** (1.0 / looks)


def cusum_paths(h: np.ndarray, p: float, m: float) -> np.ndarray:
    """Page's CUSUM of the log likelihood ratio of a hit rate ``m p`` against ``p`` (reflected at zero), per day."""
    q = m * p
    llr = h * math.log(q / p) + (1 - h) * math.log((1 - q) / (1 - p))
    s = np.zeros(h.shape)
    cur = np.zeros(h.shape[0])
    for t in range(h.shape[1]):
        cur = np.maximum(0.0, cur + llr[:, t])
        s[:, t] = cur
    return s


def max_statistics(null_hits: np.ndarray, p: float) -> tuple[np.ndarray, np.ndarray]:
    """Per null series, the largest growing-window Kupiec statistic and the largest CUSUM value (``m = 3``) over the
    horizon: the two quantities whose upper quantile calibrates a constant critical value to the size ``LEVEL``."""
    return cumulative_lr(null_hits, p).max(axis=1), cusum_paths(null_hits, p, 3.0).max(axis=1)


def critical_values(lr_max: np.ndarray, cs_max: np.ndarray) -> dict[str, float]:
    """The critical values that give a size of ``LEVEL`` over the horizon of the simulated null series: a rule rejects
    when its statistic is strictly above the value, so its size on the calibration series is at most ``LEVEL`` (the
    discreteness of the counts makes it conservative)."""
    return {"kupiec_cumulative": float(np.quantile(lr_max, 1.0 - LEVEL, method="higher")),
            "cusum_m3": float(np.quantile(cs_max, 1.0 - LEVEL, method="higher"))}


# ---------------------------------------------------------------------------------------------------------------------
# published and textbook e-processes written here because the engine does not carry them

def wwz_log_e(h: np.ndarray, p: float, gamma: float = 0.5) -> np.ndarray:
    """The e-backtest of Wang, Wang and Ziegel (2022) for the VaR hit rate: the backtest e-statistic ``e = hit / p`` of
    their Theorem 4, the bet ``1 - lam + lam e`` with the growth-rate betting process they call GREL (their equation 15
    and the special case of their Appendix A) estimated on all past days and capped at ``gamma`` (they use 1/2). The first
    day bets nothing. Returns ``log M_t`` per series and day."""
    n = h.shape[1]
    x = h.astype(float)
    hits_before = np.concatenate([np.zeros((h.shape[0], 1)), np.cumsum(x, axis=1)[:, :-1]], axis=1)
    t_before = np.arange(0, n, dtype=float)[None, :]
    num = hits_before / p - t_before
    den = hits_before * (1.0 / p - 1.0) ** 2 + (t_before - hits_before)
    lam = np.clip(np.divide(num, den, out=np.zeros_like(num), where=den > 0), 0.0, gamma)
    return np.cumsum(np.log1p(lam * (x / p - 1.0)), axis=1)


def beta_mixture_log_e(h: np.ndarray, p: float) -> np.ndarray:
    """The Bayes factor of a uniform prior on the hit rate against the point null ``p``, a test martingale of the
    Bernoulli stream (Shafer et al., 2011): ``B(k + 1, t - k + 1) / (p^k (1-p)^(t-k))`` after ``k`` hits in ``t`` days."""
    c = np.cumsum(h, axis=1).astype(float)
    t = np.arange(1, h.shape[1] + 1, dtype=float)[None, :]
    return special.betaln(c + 1.0, t - c + 1.0) - special.xlogy(c, p) - special.xlogy(t - c, 1.0 - p)


# ---------------------------------------------------------------------------------------------------------------------
# the engine's monitors over a batch of series

def engine_paths(h: np.ndarray, p: float, **kw: Any) -> np.ndarray:
    """``log E_t`` of the engine's rate e-process on every series (``kw`` are its options)."""
    from riskvalidation.validation.sequential import var_hit_eprocess

    return np.array([var_hit_eprocess(x, p, **kw).log_e for x in h])


def engine_cluster_paths(h: np.ndarray, p: float, **kw: Any) -> np.ndarray:
    from riskvalidation.validation.sequential import var_hit_clustering_eprocess

    return np.array([var_hit_clustering_eprocess(x, p, **kw).log_e for x in h])


def engine_battery_paths(h: np.ndarray, p: float, combine: str = "average") -> np.ndarray:
    from riskvalidation.validation.sequential import (
        eprocess_battery,
        var_hit_clustering_eprocess,
        var_hit_eprocess,
    )

    return np.array([eprocess_battery({"rate": var_hit_eprocess(x, p), "cluster": var_hit_clustering_eprocess(x, p)},
                                      combine=combine).log_e for x in h])


def draw_hits(seed: int, tag: int, reps: int, *, t: int = HORIZON, alpha: float = ALPHA, **kw: Any) -> np.ndarray:
    """``reps`` hit streams of ``t`` days from the engine's generator ``VarHits`` (no VaR series), one seed sequence
    ``[seed, tag]`` per scenario so that a scenario does not depend on the others."""
    from riskvalidation.generators import VarHits

    gen = VarHits(t=t, alpha=alpha, with_var=False, **kw)
    rng = np.random.default_rng(np.random.SeedSequence([seed, tag]))
    return np.array([gen.draw(rng)["hits"] for _ in range(reps)])
