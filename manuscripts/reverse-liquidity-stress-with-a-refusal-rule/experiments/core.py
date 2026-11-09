"""What the experiments of the manuscript share: the committed C16 bases rebuilt from their documents, an independent oracle for the
threshold multiplier, a seeded corpus of synthetic banks with known structure, and the solvers that are compared with the engine's.

The engine under test is ``riskvalidation`` 1.1.0 (``riskvalidation.liquidity.reverse``). The oracle below shares the model of the engine
(the net liquidity position of the scaled scenario) and none of its solver code: it finds the root of the window function by plain
bisection on its own forward computation, so that an error of the engine's bracketing, rounding or refusal logic shows as a disagreement.
Every number the manuscript quotes is written by a ``run_*.py`` script to a ``results_*.json`` next to it.
"""
from __future__ import annotations

import json
import math
import pathlib
import time
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
from scipy import optimize

from riskvalidation.liquidity import cbc as ecbc
from riskvalidation.liquidity import ladder as eladder
from riskvalidation.liquidity import reverse as ereverse
from riskvalidation.liquidity.scenarios import Scenario, ScenarioSegment

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
C16 = ROOT / "data" / "derived" / "C16"
ROUNDING = 1e-6
TARGETS = (2, 5, 10, 30)
HORIZONS = (5, 30, 60, 125)
MONETISATION = {
    "immediate": [(1, 1.0)],
    "central": [(1, 0.5), (2, 0.8), (3, 1.0)],
    "slow": [(1, 0.25), (5, 0.6), (10, 1.0)],
}


def doc(name: str) -> Any:
    """A committed document of case C16 (``data/derived/C16/<name>.json``)."""
    return json.loads((C16 / f"{name}.json").read_text(encoding="utf-8"))


def grid_convention() -> list[float]:
    """The multiplier grid of the case design (``runoff_multiplier_grid`` of the models document)."""
    return [float(x) for x in doc("models-svb-liquidity")["fit"]["conventions"]["runoff_multiplier_grid"]["values"]]


# ------------------------------------------------------------------------------------------------ the committed bases


def scenario_from_doc(d: dict[str, Any]) -> tuple[Scenario, dict[str, Any]]:
    """The scenario of a committed path document (a segment with no stored rates is the full run-off of rate 1) and its ladder block."""
    lad = d["outputs"]["path"]["ladder"]
    h = len(lad["day_index"])
    segs = []
    for s in lad["segments"]:
        rates = np.ones(h) if s["daily_rates"] is None else np.array(s["daily_rates"], dtype=float)
        segs.append(ScenarioSegment(s["segment"], s["list_class"], float(s["opening_balance"]), rates))
    v = d["outputs"]["variant"]
    return Scenario(v["scenario_family"], v["phase"], h, tuple(segs)), lad


def effective_cbc(lad: dict[str, Any], cbc_total: np.ndarray | None = None) -> np.ndarray:
    """The capacity the engine's reverse stress takes so that its position is the ladder's: the capacity plus the cumulative inflows less
    the cumulative flows that do not run off by segment (the case pipeline's ``effective_cbc``)."""
    seg_out = np.sum([s["outflows"] for s in lad["segments"]], axis=0)
    c = np.array(lad["cbc_total"] if cbc_total is None else cbc_total, dtype=float)
    return c + np.cumsum(lad["total_inflows"]) - np.cumsum(np.array(lad["total_outflows"]) - seg_out)


def c16_base(base_id: str) -> tuple[Scenario, np.ndarray, dict[str, Any], dict[str, Any]]:
    d = doc(base_id)
    scn, lad = scenario_from_doc(d)
    return scn, effective_cbc(lad), lad, d


# --------------------------------------------------------------------------------------------------- the oracle


def nlp_np(opening: np.ndarray, rates: np.ndarray, cbc: np.ndarray, m: float, cap: bool = True) -> np.ndarray:
    """The net liquidity position with every rate scaled to ``min(m q, 1)`` (or ``m q`` when ``cap`` is false), by the closed form of the
    stock: outflow of day d is the opening times the stock share left by days before d times the rate of day d."""
    q = np.minimum(m * rates, 1.0) if cap else m * rates
    before = np.concatenate([np.ones((q.shape[0], 1)), np.cumprod(1.0 - q, axis=1)[:, :-1]], axis=1)
    out = (opening[:, None] * before * q).sum(axis=0)
    return cbc - np.cumsum(out)


def sp_np(nlp: np.ndarray) -> float:
    """The survival period: the first day the position is negative; ``inf`` when it survives the horizon."""
    neg = np.flatnonzero(nlp < 0.0)
    return float(neg[0] + 1) if neg.size else math.inf


def cap_of(rates: np.ndarray) -> float:
    below = rates[rates < 1.0]
    top = float(below.max()) if below.size else 0.0
    return math.inf if top <= 0.0 else 1.0 / top


@dataclass
class Oracle:
    status: str  # "solved" or "refused"
    reason: str | None  # "horizon", "base" or "unreachable"
    m0: float | None  # the root of the window function: the infimum of the multipliers that reach the target
    sp0: float
    cap: float


def oracle(opening: np.ndarray, rates: np.ndarray, cbc: np.ndarray, target: int) -> Oracle:
    """The threshold multiplier by bisection on the window function ``w(m) = min_{t <= T} NLP_t(m)``, and the refusal reason by the three
    conditions of the proposed rule, tested in the order the rule states them."""
    h = rates.shape[1]
    cap = cap_of(rates)
    sp0 = sp_np(nlp_np(opening, rates, cbc, 1.0))
    if target >= h:
        return Oracle("refused", "horizon", None, sp0, cap)
    if sp0 <= target:
        return Oracle("refused", "base", None, sp0, cap)

    def w(m: float) -> float:
        return float(nlp_np(opening, rates, cbc, m)[:target].min())

    top = cap if math.isfinite(cap) else 1.0
    if not w(top) < 0.0:
        return Oracle("refused", "unreachable", None, sp0, cap)
    lo, hi = 1.0, top
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if w(mid) < 0.0:
            hi = mid
        else:
            lo = mid
        if hi - lo < 1e-13 * max(1.0, hi):
            break
    return Oracle("solved", None, hi, sp0, cap)


def threshold_ok(opening: np.ndarray, rates: np.ndarray, cbc: np.ndarray, target: int, m: float) -> bool:
    """The threshold property of a multiplier, on the independent forward computation: the target is reached at ``m`` and not just below it."""
    at = sp_np(nlp_np(opening, rates, cbc, m))
    below = sp_np(nlp_np(opening, rates, cbc, round(m - ROUNDING, 6)))
    return at <= target < below


# ---------------------------------------------------------------------------------------------------- the corpus


@dataclass
class Bank:
    scn: Scenario
    opening: np.ndarray
    rates: np.ndarray
    cbc_raw: np.ndarray  # the capacity schedule only
    cbc_eff: np.ndarray  # capacity plus cumulative inflows less cumulative other outflows
    flat: bool  # constant capacity
    inflows: bool
    others: bool
    horizon: int


def make_bank(rng: np.random.Generator) -> Bank:
    """A synthetic bank of known structure: two to six deposit segments (a financial segment of rate 1 with probability 0.15), constant
    daily rates drawn log-uniformly from 0.0005 to 0.08 (a two-phase path with probability 0.3), a capacity of 3% to 50% of the deposits on
    one of three monetisation schedules, day-1 inflows with probability 0.3 and a constant daily outflow outside the segments with
    probability 0.5; the horizon is 5, 30, 60 or 125 days."""
    h = int(rng.choice(HORIZONS))
    s = int(rng.integers(2, 7))
    weights = rng.lognormal(0.0, 1.0, s)
    fin = rng.random(s) < 0.15
    weights = np.where(fin, 0.2 * weights, weights)
    opening = 100.0 * weights / weights.sum()
    rates = np.empty((s, h))
    for j in range(s):
        if fin[j]:
            rates[j] = 1.0
            continue
        q = float(np.exp(rng.uniform(np.log(5e-4), np.log(0.08))))
        rates[j] = q
        if rng.random() < 0.3:
            k = int(rng.integers(2, 6))
            rates[j, :k] = min(q * float(rng.uniform(1.5, 4.0)), 0.9)
    total = float(opening.sum())
    c = float(rng.uniform(0.03, 0.5)) * total
    kind = str(rng.choice(["immediate", "central", "slow"]))
    cbc_raw = np.asarray(ecbc.monetisation_capacity(c, MONETISATION[kind], h), dtype=float)
    inflow = np.zeros(h)
    has_in = bool(rng.random() < 0.3)
    if has_in:
        inflow[0] = float(rng.uniform(0.0, 0.08)) * total
    other = np.zeros(h)
    has_other = bool(rng.random() < 0.5)
    if has_other:
        other[:] = float(rng.uniform(0.0, 0.002)) * total
    cbc_eff = cbc_raw + np.cumsum(inflow) - np.cumsum(other)
    scn = Scenario("idiosyncratic", "acute" if h <= 5 else "protracted", h,
                   tuple(ScenarioSegment(f"s{j}", "synthetic", float(opening[j]), rates[j]) for j in range(s)))
    return Bank(scn, opening, rates, cbc_raw, cbc_eff, kind == "immediate", has_in, has_other, h)


def corpus(seed: int, n: int) -> list[Bank]:
    rng = np.random.default_rng(seed)
    return [make_bank(rng) for _ in range(n)]


# ------------------------------------------------------------------------------------------------------ solvers


@dataclass
class Answer:
    answered: bool
    m: float | None
    evals: int
    reason: str | None = None


class _Count:
    """Counts the forward computations of the engine's solver by wrapping its internal position function."""

    def __init__(self) -> None:
        self.n = 0
        self._orig = ereverse._nlp

    def __enter__(self) -> "_Count":
        def wrapped(*a: Any, **k: Any) -> Any:
            self.n += 1
            return self._orig(*a, **k)

        ereverse._nlp = wrapped  # type: ignore[assignment]
        return self

    def __exit__(self, *exc: Any) -> None:
        ereverse._nlp = self._orig  # type: ignore[assignment]


def solve_engine(b: Bank, target: int, cbc: np.ndarray | None = None) -> Answer:
    """The proposed solver: ``riskvalidation.liquidity.reverse.solve_multiplier``."""
    c = b.cbc_eff if cbc is None else cbc
    with _Count() as cnt:
        r = ereverse.solve_multiplier(b.scn, c, target)
    if r.status != "solved":
        reason = r.reason or ""
        key = "horizon" if "not below the horizon" in reason else "base" if "already at or below" in reason else "unreachable"
        return Answer(False, None, cnt.n, key)
    return Answer(True, float(r.multiplier), cnt.n)


def _sp_engine(b: Bank, ms: np.ndarray) -> list[float]:
    res = ereverse.survival_vs_multiplier(b.scn, b.cbc_eff, ms)
    return [math.inf if r.survives else float(r.day) for r in res]


def _grid_up_to_cap(grid: list[float], cap: float) -> np.ndarray:
    g = [x for x in grid if x <= cap * (1.0 + 1e-12)]
    return np.array(g, dtype=float)


def solve_grid(b: Bank, target: int, grid: list[float]) -> Answer:
    """The scan of a fixed multiplier grid with the engine's forward function: the first grid multiplier whose survival period is at most
    the target, no number when none is."""
    g = _grid_up_to_cap(grid, cap_of(b.rates))
    if g.size == 0 or g[0] != 1.0:
        g = np.concatenate([[1.0], g])
    sp = _sp_engine(b, g)
    for m, s in zip(g, sp):
        if s <= target:
            return Answer(True, float(m), int(g.size))
    return Answer(False, None, int(g.size), "no grid multiplier reaches the target")


def fine_grid() -> list[float]:
    """A grid of step 0.1 from 1 to 20 and the case grid above it."""
    return [round(1.0 + 0.1 * k, 10) for k in range(0, 191)] + [x for x in grid_convention() if x > 20.0]


def solve_brent_on_sp(b: Bank, target: int) -> Answer:
    """Brent's method on ``SP(m) - T`` over ``[1, cap]``, a survival period that survives the horizon counted as ``H + 1``: the literal reading of
    'the multiplier at which the survival period equals the target'."""
    cap = cap_of(b.rates)
    top = cap if math.isfinite(cap) else 1.0
    h = b.horizon

    def f(m: float) -> float:
        s = sp_np(nlp_np(b.opening, b.rates, b.cbc_eff, m))
        return (h + 1 if math.isinf(s) else s) - target

    try:
        root, info = optimize.brentq(f, 1.0, top, xtol=1e-12, full_output=True)
    except ValueError:
        return Answer(False, None, 2, "no sign change on [1, cap]")
    return Answer(True, float(root), int(info.function_calls))


def solve_bisect_no_refusal(b: Bank, target: int, upper: float = 100.0) -> Answer:
    """Bisection of the predicate 'the target is reached' on a fixed bracket ``[1, upper]``, the right end returned when the bracket does not
    hold at the top and the left end when it holds already at 1: a solver without the refusal rule."""
    def reached(m: float) -> bool:
        return sp_np(nlp_np(b.opening, b.rates, b.cbc_eff, m)) <= target

    n = 2
    if reached(1.0):
        return Answer(True, 1.0, n)
    if not reached(upper):
        return Answer(True, upper, n)
    lo, hi = 1.0, upper
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        n += 1
        if reached(mid):
            hi = mid
        else:
            lo = mid
    return Answer(True, math.ceil(hi / ROUNDING) * ROUNDING, n)


def solve_uncapped(b: Bank, target: int, upper: float = 1000.0) -> Answer:
    """The proposed solver with the cap removed: the scaled rate ``m q`` is not limited to 1, so a multiplier may drive a rate above 1."""
    def reached(m: float) -> bool:
        with np.errstate(all="ignore"):  # a rate above 1 makes the stock product overflow: the artefact this variant exhibits
            return sp_np(nlp_np(b.opening, b.rates, b.cbc_eff, m, cap=False)) <= target

    n = 2
    if b.horizon <= target or reached(1.0):
        return Answer(False, None, n, "refused")
    if not reached(upper):
        return Answer(False, None, n, "refused")
    lo, hi = 1.0, upper
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        n += 1
        if reached(mid):
            hi = mid
        else:
            lo = mid
    return Answer(True, math.ceil(hi / ROUNDING) * ROUNDING, n)


def solve_nearest(b: Bank, target: int) -> Answer:
    """The proposed solver with the upward rounding and the neighbour check removed: Brent's root of the window function, rounded to the
    nearest six decimals."""
    h = b.horizon
    if target >= h:
        return Answer(False, None, 0, "horizon")
    if sp_np(nlp_np(b.opening, b.rates, b.cbc_eff, 1.0)) <= target:
        return Answer(False, None, 1, "base")
    cap = cap_of(b.rates)
    top = cap if math.isfinite(cap) else 1.0

    def w(m: float) -> float:
        return float(nlp_np(b.opening, b.rates, b.cbc_eff, m)[:target].min())

    if not w(top) < 0.0:
        return Answer(False, None, 2, "unreachable")
    if w(1.0) <= 0.0:
        return Answer(True, 1.0, 2)
    root, info = optimize.brentq(w, 1.0, top, xtol=1e-14, rtol=4.0 * np.finfo(float).eps, maxiter=500, full_output=True)
    return Answer(True, round(float(root), 6), int(info.function_calls))


def solve_raw_capacity(b: Bank, target: int) -> Answer:
    """The proposed solver handed the capacity schedule alone, the inflows and the flows outside the segments left out of the window function."""
    return solve_engine(b, target, cbc=b.cbc_raw)


def timed(fn: Callable[[], Answer]) -> tuple[Answer, float]:
    t0 = time.perf_counter()
    a = fn()
    return a, time.perf_counter() - t0


# ------------------------------------------------------------------------------------------------------ statistics


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float, float]:
    """The proportion with its Wilson 95% interval (Brown, Cai and DasGupta 2001); ``(nan, nan, nan)`` for an empty denominator."""
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    den = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, centre - half), min(1.0, centre + half)


def boot_quantile(x: np.ndarray, q: float, rng: np.random.Generator, reps: int = 1000) -> tuple[float, float, float]:
    """A sample quantile with its bootstrap percentile interval (Efron 1979)."""
    if x.size == 0:
        return float("nan"), float("nan"), float("nan")
    est = float(np.quantile(x, q))
    idx = rng.integers(0, x.size, size=(reps, x.size))
    qs = np.quantile(x[idx], q, axis=1)
    return est, float(np.quantile(qs, 0.025)), float(np.quantile(qs, 0.975))
