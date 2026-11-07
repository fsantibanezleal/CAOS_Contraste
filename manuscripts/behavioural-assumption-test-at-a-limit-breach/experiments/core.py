"""What every experiment of the manuscript shares: the engine's test, the comparators, the generators of histories with a planted
assumption change, the calibration of the tolerance, and the interval and area statistics.

Nothing here is typed from a result: the generator of the fitted regime is calibrated from the committed C14 raw inputs
(``raw/`` under the device data root that ``CONTRASTE_DATA`` names), the replicating portfolio and the two
comparator tests of the engine are called, not re-implemented, and the engine's test itself is called on every history.

    python -m pytest manuscripts/behavioural-assumption-test-at-a-limit-breach/experiments -q
"""
from __future__ import annotations

import math
import os
import pathlib
import sys
from dataclasses import dataclass

import numpy as np
from riskvalidation.irrbb import behavioural as rv_beh
from riskvalidation.validation import irrbb as rv_irrbb
from scipy import stats

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))

#: the seven tranche maturities of the C14 replicating portfolio, years (pipeline.cases.c14.assumptions.TRANCHES)
MATS = np.array([0.25, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0])
J = MATS.size
#: the weighted average maturity of the whole weight on the longest tranche, years (the engine's m / 2 rule)
WAM_MAX = float(MATS[-1] / 2.0)
#: the estimation window of the C14 fits, quarters (pipeline.cases.c14.assumptions.FIT_QUARTERS)
FIT_QUARTERS = 16
#: the default length of a history, quarters
T_DEFAULT = 12
#: quarterly dates for the engine (strictly increasing; only the order matters to the test)
def dates(t: int) -> np.ndarray:
    return np.datetime64("2019-01-01", "D") + 91 * np.arange(t)


def data_root() -> pathlib.Path:
    """The device data root of the raw C14 inputs, from ``CONTRASTE_DATA`` (as the pipeline's bakes read it)."""
    root = os.environ.get("CONTRASTE_DATA")
    if not root:
        raise FileNotFoundError("the fitted regime reads the raw C14 inputs of the device data root: set CONTRASTE_DATA")
    return pathlib.Path(root)


# ---------------------------------------------------------------------------------------------------- real inputs

@dataclass(frozen=True)
class RealSeries:
    """The quarterly series of the C14 fits up to 2022-Q4 and the rolling replicating-portfolio fits on them."""

    dates: list[str]
    client_rate: np.ndarray
    tranche_yields: np.ndarray
    fit_dates: list[str]
    weights: np.ndarray            # (n_fits, J), the engine's weights at each date from the 16th quarter on

    @property
    def wam(self) -> np.ndarray:
        return self.weights @ MATS / 2.0


def load_real() -> RealSeries:
    """The call-report cost of deposits and the Treasury par yields of the pipeline's case C14, with the rolling fits."""
    from pipeline.cases.c14 import fetch, fits
    from pipeline.io import fdic, treasury

    raw = data_root() / "raw"
    reports = fdic.read_financials(raw / fetch.FDIC_DIR / fetch.fdic_name(fetch.CERT), fetch.CERT)
    curves = treasury.read_par(raw / fetch.TREASURY_DIR)
    s = fits.quarterly_series(reports, curves, "2022-12-31")
    w, d = [], []
    for end in range(FIT_QUARTERS - 1, len(s.dates)):
        f = fits.replicating_fit(s, end)
        w.append(f["weights"])
        d.append(s.dates[end])
    return RealSeries(s.dates, s.client_rate, s.tranche_yields, d, np.array(w))


# ---------------------------------------------------------------------------------------------------- generator of the fitted regime

#: the length, quarters, of the blocks of the circular block bootstrap of the real quarterly rows (fixed before any detection experiment)
BLOCK = 6


def resample_rows(rng: np.random.Generator, n_real: int, n: int, block: int = BLOCK) -> np.ndarray:
    """Row indices of a circular block bootstrap of the ``n_real`` real quarters: blocks of ``block`` consecutive quarters from uniform
    random starts, concatenated to ``n`` rows. A row keeps the client rate and the seven tranche yields of its real quarter."""
    idx: list[int] = []
    while len(idx) < n:
        start = int(rng.integers(0, n_real))
        idx.extend((start + k) % n_real for k in range(block))
    return np.array(idx[:n])


def simulate_fits(seed: tuple[int, ...], client: np.ndarray, yields: np.ndarray, t: int = T_DEFAULT, block: int = BLOCK) -> np.ndarray:
    """The ``t`` rolling replicating-portfolio weights (the engine's fits on 16 quarters) of one simulated bank, shape (t, J): the quarterly rows
    are a block bootstrap of the real ones (8 burn-in rows are dropped), so the regime of the real bank, its rates and its deposit cost, is kept."""
    rng = np.random.default_rng(list(seed))
    burn = 8
    idx = resample_rows(rng, client.size, burn + FIT_QUARTERS + t - 1, block)[burn:]
    cl, y = client[idx], yields[idx]
    out = []
    for end in range(FIT_QUARTERS - 1, FIT_QUARTERS - 1 + t):
        lo = end + 1 - FIT_QUARTERS
        out.append(rv_beh.replicating_portfolio(cl[lo:end + 1], y[lo:end + 1], MATS).weights)
    return np.array(out)


# ---------------------------------------------------------------------------------------------------- histories with a planted change

def breach_chain(rng: np.random.Generator, t: int, prevalence: float, stay: float = 0.8, min_breaches: int = 1) -> np.ndarray:
    """A two-state Markov chain of breach flags with stationary prevalence ``prevalence`` and ``P(b_t=1|b_{t-1}=1)=stay``,
    redrawn until at least ``min_breaches`` of the dates after the first are breached (the test can flag nothing otherwise)."""
    enter = prevalence * (1.0 - stay) / (1.0 - prevalence)
    while True:
        b = np.empty(t, dtype=bool)
        b[0] = rng.random() < prevalence
        for k in range(1, t):
            b[k] = rng.random() < (stay if b[k - 1] else enter)
        if int(b[1:].sum()) >= min_breaches:
            return b


def plant_dates(rng: np.random.Generator, b: np.ndarray, prob: float) -> np.ndarray:
    """The breach dates (after the first) at which an assumption is changed to address the breach: each with probability
    ``prob``, at least one (a uniformly chosen breach date when none is drawn). A boolean mask of the dates."""
    cand = np.flatnonzero(b)
    cand = cand[cand >= 1]
    mask = np.zeros(b.size, dtype=bool)
    mask[cand[rng.random(cand.size) < prob]] = True
    if not mask.any():
        mask[rng.choice(cand)] = True
    return mask


def plant_dates_before_spell(rng: np.random.Generator, b: np.ndarray, prob: float) -> np.ndarray:
    """The dates that precede the first date of a breach spell (``b`` is 0 at the date and 1 at the next one), each with probability ``prob``, at least one
    when any exists: the dates at which an assumption is changed in anticipation of a breach. None of them is a breach date, and none is the first date (an addition
    from the first date on is a constant, which no detector can tell from the history without it). A boolean mask of the dates."""
    cand = np.flatnonzero(~b[:-1] & b[1:])
    cand = cand[cand >= 1]
    mask = np.zeros(b.size, dtype=bool)
    if cand.size == 0:
        return mask
    mask[cand[rng.random(cand.size) < prob]] = True
    if not mask.any():
        mask[rng.choice(cand)] = True
    return mask


def overlay_weights(w: np.ndarray, planted: np.ndarray, share: float) -> np.ndarray:
    """A persistent override of the fitted replicating portfolio toward the longest tranche: from each planted date on the
    weights used are ``(1 - s) w + s e_J`` with ``s`` the cumulative share ``min(1, share * planted-so-far)``."""
    s = np.minimum(1.0, share * np.cumsum(planted))[:, None]
    e = np.zeros(J)
    e[-1] = 1.0
    return (1.0 - s) * w + s * e


def stated_draws(rng: np.random.Generator, t: int, rate: float) -> dict[str, np.ndarray]:
    """The random numbers of one stated parameter, drawn once so that the history without and with a planted change share them: the
    dates and the signed amounts of the changes that have nothing to do with a breach (each date with probability ``rate``, 0.25 to
    1.0 years of random sign) and the amount a planted change would add (0.5 to 2.0 years, lengthening)."""
    chg = rng.random(t) < rate
    amount = rng.choice([-1.0, 1.0], t) * rng.uniform(0.25, 1.0, t)
    return {"innocent": np.where(chg, amount, 0.0), "planted": rng.uniform(0.5, 2.0, t)}


def stated_history(draws: dict[str, np.ndarray], planted: np.ndarray | None) -> np.ndarray:
    """A stated parameter (a core maturity, years) starting at 4: at each date it moves by the innocent amount, plus the planted amount at
    a planted date, with a floor of 0.5 years."""
    t = draws["innocent"].size
    th = np.empty(t)
    th[0] = 4.0
    for k in range(1, t):
        d = draws["innocent"][k] + (draws["planted"][k] if planted is not None and planted[k] else 0.0)
        th[k] = max(th[k - 1] + d, 0.5)
    return th


# ---------------------------------------------------------------------------------------------------- detectors

def engine_test(theta: np.ndarray, b: np.ndarray):
    """The engine's ``irrbb.behavioural_change_at_breach`` on one history."""
    return rv_irrbb.behavioural_change_at_breach(np.asarray(theta, dtype=float), dates(theta.size), np.asarray(b, dtype=bool))


def closed_form_count(theta: np.ndarray, b: np.ndarray) -> int:
    """Equation of the proposed test: ``sum_t 1[theta_t != theta_{t-1}] 1[b_t]``."""
    return int(np.sum((theta[1:] != theta[:-1]) & b[1:]))


def peak_at_breach(theta: np.ndarray, b: np.ndarray, lookahead: bool = False) -> float:
    """``max |Δθ_t|`` over the dates of a breach (with ``lookahead``: of a breach at that date or the next one)."""
    d = np.abs(np.diff(theta))
    flag = b[1:].copy()
    if lookahead:
        flag[:-1] |= b[2:]
    return float(d[flag].max()) if flag.any() else 0.0


#: the shortest segment, in dates, on each side of a candidate break of ``shift_statistic``
SHIFT_MIN_SEGMENT = 3


def shift_statistic(theta: np.ndarray) -> tuple[float, int]:
    """The one-sided supremum-t statistic of a single upward shift in the level of a series (the Quandt-Andrews family of tests of a break at an unknown date):
    for each first date ``tau`` of a new regime (at least ``SHIFT_MIN_SEGMENT`` dates on each side) the difference of the means after and before, divided by its
    standard error under the pooled variance of the two segments; returns the largest value and the date at which it is reached (0 and -1 when the series is too
    short for two segments)."""
    th = np.asarray(theta, dtype=float)
    n = th.size
    if n < 2 * SHIFT_MIN_SEGMENT:
        return 0.0, -1
    best, at = -np.inf, SHIFT_MIN_SEGMENT
    for tau in range(SHIFT_MIN_SEGMENT, n - SHIFT_MIN_SEGMENT + 1):
        x, y = th[:tau], th[tau:]
        ssr = float(((x - x.mean()) ** 2).sum() + ((y - y.mean()) ** 2).sum())
        s2 = max(ssr / (n - 2), 1e-12)
        t = (y.mean() - x.mean()) / math.sqrt(s2 * (1.0 / x.size + 1.0 / y.size))
        if t > best:
            best, at = t, tau
    return float(best), int(at)


def shift_scores(theta: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """The statistic of the shift test and of the rule "a shift is found and its estimated break date is a breach date" (the statistic when that date is a
    breach date, 0 otherwise); the second is the break-then-coincide comparator of the proposed test."""
    stat, at = shift_statistic(theta)
    return stat, (stat if at >= 0 and bool(b[at]) else 0.0)


def scores(theta: np.ndarray, b: np.ndarray, w: np.ndarray | None = None) -> dict[str, float]:
    """Every detector's statistic on one history. ``engine_count`` is the engine's statistic, ``peak`` and ``peak_lookahead`` the largest change at a
    breach date, ``any_change`` the number of changes whatever the breach flags; ``fisher_p``, ``mannwhitney_p`` and ``welch_p`` are the one-sided
    p-values of the published tests (1 when the test is undefined on the history), ``stability`` the engine's sup-norm distance between the weights."""
    d = np.diff(theta)
    ad = np.abs(d)
    bb = b[1:]
    chg = ad > 0.0
    out: dict[str, float] = {}
    out["engine_count"] = float(engine_test(theta, b).statistic)
    out["peak"] = peak_at_breach(theta, b)
    out["peak_lookahead"] = peak_at_breach(theta, b, lookahead=True)
    out["any_change"] = float(chg.sum())
    out["shift"], out["shift_at_breach"] = shift_scores(theta, b)
    tab = [[int((chg & bb).sum()), int((chg & ~bb).sum())], [int((~chg & bb).sum()), int((~chg & ~bb).sum())]]
    out["fisher_p"] = float(stats.fisher_exact(tab, alternative="greater")[1])
    mw = wp = 1.0
    if bb.any() and (~bb).any():
        if np.ptp(ad) > 0:
            mw = float(stats.mannwhitneyu(ad[bb], ad[~bb], alternative="greater", method="asymptotic")[1])
        if d.size > 2 and np.ptp(d) > 0:
            wp = float(stats.ttest_ind(d[bb], d[~bb], equal_var=False, alternative="greater")[1])
            wp = 1.0 if wp != wp else wp
    out["mannwhitney_p"] = mw
    out["welch_p"] = wp
    if w is not None:
        out["stability"] = float(rv_irrbb.nmd_parameter_stability(w, MATS).statistic)
    return out


# ---------------------------------------------------------------------------------------------------- statistics

def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """The rate ``k/n`` and its 95% Wilson interval."""
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return p, max(0.0, centre - half), min(1.0, centre + half)


def auc(null: np.ndarray, alt: np.ndarray) -> float:
    """The probability that an alternative score exceeds a null one, a tie counting one half."""
    null, alt = np.asarray(null, float), np.asarray(alt, float)
    ranks = stats.rankdata(np.concatenate([alt, null]))
    u = ranks[: alt.size].sum() - alt.size * (alt.size + 1) / 2.0
    return float(u / (alt.size * null.size))


def auc_ci(null: np.ndarray, alt: np.ndarray, rng: np.random.Generator, reps: int = 500) -> tuple[float, float, float]:
    """The area and its percentile bootstrap interval (``reps`` resamples of both arms)."""
    a0 = auc(null, alt)
    vals = [auc(rng.choice(null, null.size), rng.choice(alt, alt.size)) for _ in range(reps)]
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return a0, float(lo), float(hi)


def conformal_threshold(null_scores: np.ndarray, alpha: float) -> float:
    """The ``ceil((n+1)(1-alpha))``-th smallest null score: a new null score above it has probability at most ``alpha`` when it is
    exchangeable with the calibration scores (``inf`` when the sample is too small for the level)."""
    s = np.sort(np.asarray(null_scores, float))
    k = math.ceil((s.size + 1) * (1.0 - alpha))
    return float("inf") if k > s.size else float(s[k - 1])


def p_coincidence_hypergeometric(n_dates: int, n_changes: int, n_breaches: int) -> float:
    """``P(c >= 1) = 1 - C(n-k, m) / C(n, m)``: the probability that at least one of ``k`` changes falls on one of ``m`` breach
    dates when the breach dates are placed uniformly among ``n`` dates (Proposition on the false-flag rate)."""
    if n_breaches > n_dates - n_changes:
        return 1.0
    return 1.0 - math.comb(n_dates - n_changes, n_breaches) / math.comb(n_dates, n_breaches)


# ---------------------------------------------------------------------------------------------------- decisions

#: the size of the published tests, and the red limit of the engine's stability test (``gap_red`` of ``irrbb.nmd_parameter_stability``)
ALPHA = 0.05
STABILITY_RED = 0.25
DETECTORS = ("engine", "any_change", "fisher", "mannwhitney", "welch", "stability", "tolerance", "tolerance_lookahead", "shift", "shift_at_breach")
LABEL = {"engine": "Proposed test (exact change at a breach)", "any_change": "Any change, whatever the breach flags",
         "fisher": "Fisher exact test, change against breach", "mannwhitney": "Mann-Whitney test of the size of the changes",
         "welch": "Welch test of the signed changes", "stability": "Stability of the weights (engine)",
         "tolerance": "Tolerance on the change at a breach", "tolerance_lookahead": "Tolerance with a one-date look-ahead",
         "shift": "Test for a shift in the level, whatever the breach flags", "shift_at_breach": "Test for a shift in the level that falls on a breach date"}


def flag(sc: dict[str, float], name: str, delta: float | None = None) -> bool:
    """Whether a detector flags the history whose statistics are ``sc`` (``delta`` is the tolerance of the two tolerance rules and the critical value of the two shift rules)."""
    if name == "engine":
        return sc["engine_count"] >= 1.0
    if name == "any_change":
        return sc["any_change"] >= 1.0
    if name in ("fisher", "mannwhitney", "welch"):
        return sc[name + "_p"] <= ALPHA
    if name == "stability":
        return sc["stability"] > STABILITY_RED
    if name == "tolerance":
        return sc["peak"] > delta
    if name == "tolerance_lookahead":
        return sc["peak_lookahead"] > delta
    if name in ("shift", "shift_at_breach"):
        return sc[name] > delta
    raise KeyError(name)


def roc_score(sc: dict[str, float], name: str) -> float:
    """The statistic a detector thresholds, oriented so that a larger value is more extreme."""
    if name == "engine":
        return sc["engine_count"]
    if name == "any_change":
        return sc["any_change"]
    if name in ("fisher", "mannwhitney", "welch"):
        return -sc[name + "_p"]
    if name == "stability":
        return sc["stability"]
    if name == "tolerance":
        return sc["peak"]
    if name == "tolerance_lookahead":
        return sc["peak_lookahead"]
    if name in ("shift", "shift_at_breach"):
        return sc[name]
    raise KeyError(name)
