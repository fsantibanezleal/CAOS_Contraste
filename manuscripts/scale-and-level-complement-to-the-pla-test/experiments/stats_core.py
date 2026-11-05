"""The detectors this manuscript compares, computed on one 250-day desk-year, and the null-calibrated decision rule they share.

Every detector reads the same pair (HPL, RTPL) from the committed C13 generator (``pipeline.cases.c13.generator``, read only).
The regulatory statistics, the three statistics of the proposed complement and the desk back-test counts are return values of the
engine ``riskvalidation`` 1.1.0 (``market.frtb``, ``market.pla_complement``, ``validation.market``). The comparators the engine does
not carry (the Mincer-Zarnowitz Wald test with the ordinary (OLS) covariance, the same regression on the squared series, the Ljung-Box
test on the squared residual) are written here from their published definitions and checked against independent implementations in
``check_core.py``.

Run from the repository root of CAOS_Contraste; nothing here draws a random number except through the generator seeds.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from pipeline.cases.c13 import generator, params  # noqa: E402
from riskvalidation.market import frtb  # noqa: E402
from riskvalidation.market import pla_complement as pc  # noqa: E402
from riskvalidation.validation import market as vm  # noqa: E402

#: the columns of a statistic row, in order
COLUMNS = (
    "wald_hc3",        # proposed: Mincer-Zarnowitz Wald test of (0, 1), HC3 covariance (engine)
    "abs_spearman",    # proposed: Spearman of |HPL| and |RTPL| (engine)
    "roll5", "roll10", "roll20", "roll40", "roll60",   # proposed: Spearman of the w-day rolling means of |HPL|, |RTPL| (engine)
    "wald_ols",        # comparator: Mincer-Zarnowitz (1969) Wald test of (0, 1), ordinary (OLS) covariance
    "wald_var",        # comparator: the regression on the squared series (variance proxy), HC3 Wald of (0, 1)
    "ljung_box_sq",    # comparator: Ljung-Box Q(10) on the squared residual HPL - RTPL
    "spearman_reg",    # regulatory: Spearman of the levels (engine)
    "ks_reg",          # regulatory: Kolmogorov-Smirnov distance (engine)
    "cc_975",          # comparator: Christoffersen conditional coverage LR, desk 97.5 percent VaR (engine)
    "cc_99",           # comparator: the same at 99 percent (engine)
    "exc_975",         # desk exceptions in 250 days at 97.5 percent (engine)
    "exc_99",          # and at 99 percent
    "slope",           # Mincer-Zarnowitz slope of HPL on RTPL (engine)
    "intercept",       # and intercept
    "roll20_pearson",  # Pearson correlation of the 20-day rolling means of |HPL| and |RTPL| (diagnostic for the theory)
    "zone",            # regulatory zone: 0 green, 1 amber, 2 red (engine)
    "zone_ks",         # the zone of the KS statistic alone (Spearman held at its best value, engine)
    "zone_sp",         # the zone of the Spearman statistic alone (KS held at its best value, engine)
)
IDX = {c: i for i, c in enumerate(COLUMNS)}
ROLL_WINDOWS = (5, 10, 20, 40, 60)
LB_LAGS = 10
#: detectors that flag on a LARGE statistic; every other calibrated detector flags on a SMALL one
HIGH = ("wald_hc3", "wald_ols", "wald_var", "ljung_box_sq", "cc_975", "cc_99", "exc_975", "exc_99", "ks_reg")
LOW = ("abs_spearman", "roll5", "roll10", "roll20", "roll40", "roll60", "spearman_reg")


def wald_ols(h: np.ndarray, r: np.ndarray) -> float:
    """Wald test of (a, b) = (0, 1) in HPL = a + b RTPL + e with the ordinary (OLS) covariance s^2 (X'X)^-1."""
    x = np.column_stack([np.ones(h.size), r])
    xtx_inv = np.linalg.inv(x.T @ x)
    beta = xtx_inv @ (x.T @ h)
    e = h - x @ beta
    s2 = float(e @ e) / (h.size - 2)
    d = beta - np.array([0.0, 1.0])
    return float(d @ np.linalg.solve(s2 * xtx_inv, d))


def ljung_box(x: np.ndarray, lags: int = LB_LAGS) -> float:
    """The Ljung-Box statistic Q = n (n + 2) sum_{k=1}^{m} rho_k^2 / (n - k) of the series ``x``."""
    x = np.asarray(x, dtype=float)
    n = x.size
    xc = x - x.mean()
    den = float(xc @ xc)
    if den == 0.0:
        return 0.0
    rho = np.array([float(xc[k:] @ xc[:-k]) / den for k in range(1, lags + 1)])
    return float(n * (n + 2) * np.sum(rho ** 2 / (n - np.arange(1, lags + 1))))


def roll_pearson(h: np.ndarray, r: np.ndarray, w: int = 20) -> float:
    k = np.ones(w) / w
    return float(np.corrcoef(np.convolve(np.abs(h), k, "valid"), np.convolve(np.abs(r), k, "valid"))[0, 1])


def row(rep: generator.Replication) -> np.ndarray:
    """All detector statistics of one replication."""
    h, r = rep.hpl, rep.rtpl
    mz = pc.pla_mz_wald(h, r)
    sp, ks = frtb.pla_spearman(h, r), frtb.pla_ks(h, r)
    code = {"green": 0, "amber": 1, "red": 2}
    zone = code[frtb.pla_zone(sp, ks)]
    ex975, ex99 = rep.loss > rep.var[0.025], rep.loss > rep.var[0.01]
    cc = []
    for ex, a in ((ex975, 0.025), (ex99, 0.01)):
        res = vm.christoffersen_conditional_coverage(ex, a)
        # the engine does not evaluate the test without an exceedance (its statistic is NaN): no evidence, so statistic 0
        stat = float(res.statistic) if res.statistic is not None else 0.0
        cc.append(stat if np.isfinite(stat) else 0.0)
    out = {
        "wald_hc3": mz.wald, "abs_spearman": pc.pla_abs_spearman(h, r),
        "wald_ols": wald_ols(h, r), "wald_var": pc.pla_mz_wald(h ** 2, r ** 2).wald,
        "ljung_box_sq": ljung_box((h - r) ** 2), "spearman_reg": sp, "ks_reg": ks, "cc_975": cc[0], "cc_99": cc[1],
        "exc_975": float(ex975.sum()), "exc_99": float(ex99.sum()), "slope": mz.slope, "intercept": mz.intercept,
        "roll20_pearson": roll_pearson(h, r, 20), "zone": float(zone),
        "zone_ks": float(code[frtb.pla_zone(1.0, ks)]), "zone_sp": float(code[frtb.pla_zone(sp, 0.0)]),
    }
    for w in ROLL_WINDOWS:
        out[f"roll{w}"] = pc.pla_rolling_abs_spearman(h, r, w)
    return np.array([out[c] for c in COLUMNS], dtype=float)


def block(did: str, case_seed: int, n: int = params.N_REPLICATIONS, lag: float | None = None) -> np.ndarray:
    """The statistic rows of replications 0..n-1 of variant ``did`` under ``case_seed`` (``lag`` replaces the stale-volatility lag)."""
    return np.vstack([row(generator.replicate(did, i, case_seed, vol_lag_days=lag)) for i in range(n)])


def critical(null: np.ndarray, p: float, high: bool) -> float:
    """The engine's rule (``pla_complement_calibrate``): with k = floor(p N), the (k+1)-th largest (or smallest) null value, so at
    most k <= p N null desk-years lie strictly beyond it. ``ValueError`` when the null cannot resolve p."""
    n = null.size
    k = int(np.floor(p * n + 1e-9))
    if k < 1:
        raise ValueError(f"{n} null values cannot resolve a size of {p}")
    s = np.sort(null)
    return float(s[::-1][k] if high else s[k])


def flag(values: np.ndarray, thr: float, high: bool) -> np.ndarray:
    return values > thr if high else values < thr


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """The Wilson (1927) score interval of a share."""
    p = k / n
    d = 1.0 + z * z / n
    c = (p + z * z / (2 * n)) / d
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return float(max(0.0, c - half)), float(min(1.0, c + half))


def is_high(name: str) -> bool:
    return name in HIGH
