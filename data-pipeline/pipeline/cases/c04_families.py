"""C04's known-truth generator families (contract section 2, requirement CT-405).

The simulated families draw obligors' rating paths from riskvalidation's ``RatingPaths`` (exact continuous-time paths
from a known generator Q, default absorbing, observed at annual snapshots as CEREP's stock model observes ratings: ESMA,
CEREP help file, ESMA65-8-10634) and measure, over seeded repetitions, what the engine's estimators, intervals and tests
make of them, each rate and each mean with its Monte Carlo standard error (``riskvalidation.harness``; Morris, White
and Crowther 2019, doi:10.1002/sim.8086, Table 6); the thin family is exact and draws nothing. Design:
docs/design/features/c04-transitions/design.md and contract.md; the theory is research dossier 13 and the engine's
docs/transitions pages and docs/generators/05_rating-paths.md.

- ``markov``: the one-year PD by grade from the cohort matrix pooled over the five years (Anderson and Goodman 1957,
  doi:10.1214/aoms/1177707039, (2.8)), the duration generator (Lando and Skodeberg 2002,
  doi:10.1016/S0378-4266(01)00228-X), the EM generator of the snapshot counts (Bladt and Sorensen 2005, as presented by
  Smith and dos Reis 2018, doi:10.1080/14697688.2017.1383627) and the diagonal (2), weighted (2') and JLT (3)
  generators of the pooled matrix (Israel, Rosenthal and Wei 2001, doi:10.1111/1467-9965.00114), against the truth;
  the size of the four transition tests with the feeds of the engine's size study (tests/test_size.py); the coverage
  of the Wald (2.2) and Agresti-Coull (3.3) intervals of Schuermann and Hanson (2004, FRBNY Staff Report 190), of the
  Jeffreys interval (Brown, Cai and DasGupta 2001) and of the resampling bootstrap of the duration PD (their section
  2.3).
- ``momentum``: the self-exciting downgrade intensity of dos Reis, Pfeuffer and Smith (2020, arXiv 1809.09889,
  section 4.2), beta alpha exp(-beta (t - tau)) after every downgrade, along the ladder alpha 0, 0.025, 0.05, 0.125
  and 0.25 (beta 1): on the EM generator of S&P's counts alpha 0.125 gives the hazard coefficient they estimate on
  Moody's data (c = 0.33010, their Table 2; dossier 13 section 16), so the ladder runs from a fifth of the empirical
  strength to twice it. Per rung: the rejection rates of time homogeneity, order and the momentum hazard test; the
  hazard's fitted coefficient c (``rating_momentum``'s ``extras["coefficient"]``, 0 for a Markov chain, so its truth
  is 0 and its bias the mean c); the five-year default frequency of the initial cohort against the Markov projections
  from the one-year data (the pooled cohort matrix to the fifth power, exp(5 Q^) of the duration generator).
- ``cycle``: every downgrade rate times k in the third year (a regime of the generator); time homogeneity across the
  five annual matrices and the third year's counts against the pooled matrix of the same draw; the stressed year's
  cohort PD against the stable chain's one-year PD, the deviation a rating philosophy insensitive to the economy shows
  in a bad year (EBA/GL/2017/16 paragraph 66(c)); the long-run average default rate of paragraph 84, "the observed
  average of the one-year default rates" (the mean of the five yearly cohort PDs, as ``c04_agency``'s ``lra.rate``),
  against the five years' true average; and the pooled PD of Anderson and Goodman (2.8), which weights each year by
  its cohort and so is not paragraph 84's average once the stressed year moves the cohort's mix.
- ``withdrawals``: withdrawal at 6% a year, at 6% (1 + k) within the year before default, against the truth: the
  pooled one-year PD with withdrawals removed ("the industry standard", Schuermann and Hanson footnote 4; CEREP's
  transition page); kept in the denominator unfollowed (withdrawals a ninth, absorbing state); followed, each year's
  cohort as observed (the ratings outstanding at its start) with its end read on the latent path, so a rating
  withdrawn within the year that defaults by its end counts as a default (EBA/GL/2017/16 paragraphs 73 and 76, at the
  one-year level); and the latent chain's own pooled PD (every obligor followed every year, withdrawn or not). The
  matrix tests a validator has: time homogeneity across the five annual matrices, and the last year's counts against
  exp(Q) (the last, not the first: every path starts at time 0 with no withdrawal history, so the first year's cohort
  still holds the ratings a later cohort has lost to withdrawal before their default year; its removed PD is the least
  biased of the five).
- ``thin``: the exact coverage and expected length of the three intervals at the true one-year PD, and the probability
  that adjacent grades' Jeffreys intervals overlap (Hanson and Schuermann's question whether notches can be told
  apart), each by enumerating the binomial counts: riskvalidation's ``exact_coverage`` and ``overlap_probability``.

The Markov family also measures the order test's two forms over ten times its repetitions, on a seed of their own:
which form holds its size depends on the design's sparsity (riskvalidation chose the chi-square on an even five-grade
chain; on these S&P-like cohorts the harness measures both again).

Seeds: one per rung, ``_seed(case_seed, "<family>:<rung>")`` with C22's helper; a rung's simulation rows share it
(C22 derives one per row, from ``"<family>:<key>"``), because the harness spawns one stream per repetition from it
(``SeedSequence(seed).spawn(reps)``) and this module reads the same streams, so the tests and the estimators of a rung
see the same datasets (common random numbers), and repetition i re-runs alone to the same data.

Inputs are refused where the engine would accept them and the artifact would mislead: a non-finite rate (it passes the
generator check, where comparisons with NaN are false, and the path simulation then never ends), a grade from which
default is unreachable (its true PD is 0, so every interval covers it and every error is 0), and a cohort size that is
not a positive integer.
"""
from __future__ import annotations

import sys
import time
import zlib
from collections.abc import Callable, Mapping
from typing import Any

import numpy as np
from scipy.linalg import expm

from riskvalidation.generators import jsonable
from riskvalidation.generators.paths import RatingPaths
from riskvalidation.harness import Rate, estimator_performance, simulate
from riskvalidation.transitions import embedding
from riskvalidation.transitions.em import em_generator
from riskvalidation.transitions.estimators import WITHDRAWN, cohort, duration_generator, pooled_cohort
from riskvalidation.transitions.intervals import (
    exact_coverage,
    overlap_probability,
    pd_agresti_coull,
    pd_bootstrap,
    pd_jeffreys,
    pd_wald,
)
from riskvalidation.validation.transitions import rating_momentum

from ..io.cerep import GRADES as CEREP_GRADES
from .c01_ladder import _t

FAMILIES = ("markov", "momentum", "cycle", "withdrawals", "thin")
GRADES = list(CEREP_GRADES)
STATES = GRADES + ["D"]
M = len(STATES)                  # seven grades and default
D = M - 1                        # default: the last state, absorbing
YEARS = 5
SNAPSHOTS = tuple(float(t) for t in range(YEARS + 1))
LEVELS = (0.05, 0.01)            # the test levels every rate is read at
LEVEL = 0.95                     # the intervals' confidence
SOURCE = "EM generator (riskvalidation.transitions.em) of S&P's pooled annual CEREP counts, computed by the case"

ESTIMATORS = ("cohort", "duration", "em", "diagonal", "weighted", "jlt")
INTERVALS: dict[str, Callable[..., dict[str, Any]]] = {
    "wald": pd_wald, "agresti_coull": pd_agresti_coull, "jeffreys": pd_jeffreys}
BOOT_REPS, N_BOOT = 100, 500     # the bootstrap's repetitions (the first ones) and replicates
#: the order test's two forms are measured over this many times the family's repetitions (2,000 at the bake's 200)
ORDER_FORM_FACTOR = 10

#: dos Reis et al.'s momentum strength: none, two weak rungs, the empirical strength (alpha 0.125 fits their c = 0.33 on
#: the EM generator of S&P's counts, dossier 13 section 16) and twice it
ALPHAS = (0.0, 0.025, 0.05, 0.125, 0.25)
BETA = 1.0
INVESTMENT_GRADES = 4            # AAA to BBB: a downgrade from them is dos Reis et al.'s first type
CYCLE_K = (1.0, 1.25, 1.5, 2.0, 3.0)
STRESS = (2.0, 3.0)              # the stressed generator holds over the third year
STRESSED_STEP = 2                # the annual step from 2 to 3
INFORMATIVE = (0.0, 1.0, 3.0, 9.0)
WITHDRAWAL_RATE = 0.06
WINDOW = 1.0
THIN_N = (50, 100, 200, 500, 1000)

LADDERS: dict[str, dict[str, Any] | None] = {
    "markov": None,
    "momentum": {"name": _t("Momentum alpha (beta 1 a year)", "Alfa de momentum (beta 1 por año)"),
                 "unit": "unitless", "values": list(ALPHAS)},
    "cycle": {"name": _t("Downgrade rates times k in the third year",
                         "Tasas de rebaja multiplicadas por k en el tercer año"),
              "unit": "ratio", "values": list(CYCLE_K)},
    "withdrawals": {"name": _t("Informative withdrawal k: 6% a year, times 1 + k in the year before default",
                               "Retiro informativo k: 6% al año, multiplicado por 1 + k en el año previo al "
                               "incumplimiento"),
                    "unit": "ratio", "values": list(INFORMATIVE)},
    "thin": {"name": _t("Obligors per grade", "Deudores por grado"), "unit": "count", "values": list(THIN_N)},
}
#: the seed key of each rung (the thin family is exact: nothing is drawn, no seed)
SEED_KEYS: dict[str, str | None] = {"markov": "markov:null", "momentum": "momentum:alpha=<rung>",
                                    "cycle": "cycle:k=<rung>", "withdrawals": "withdrawals:informative=<rung>",
                                    "thin": None}
PERFORMANCE = ("mean", "bias", "bias_mcse", "empirical_se", "empirical_se_mcse", "rmse", "rmse_mcse")

_T0 = time.perf_counter()


def _log(msg: str) -> None:
    print(f"[C04 families {time.perf_counter() - _T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


def _seed(case_seed: int, key: str) -> int:
    """C22's seed helper (``pipeline.cases.c22_validator._seed``), copied: a seed per simulation, a pure function of
    the case seed and the simulation's key."""
    return int(np.random.SeedSequence([case_seed, zlib.crc32(key.encode("utf-8"))]).generate_state(1)[0])


def _children(seed: int, reps: int) -> list[np.random.SeedSequence]:
    """One seed sequence per repetition, spawned exactly as ``harness.simulate`` spawns them from the same seed."""
    return np.random.SeedSequence(seed).spawn(reps)


def _paths(q: np.ndarray, obligors: list[int], **defect: Any) -> RatingPaths:
    """The rating-path generator over five years with annual snapshots, with an optional planted defect."""
    return RatingPaths(q, tuple(obligors), horizon=float(YEARS), snapshots=SNAPSHOTS, **defect)


def _pd(gen: RatingPaths, years: int = 1) -> np.ndarray:
    """The generator's true PD by grade at a horizon (its truth, exp(tQ)'s default column)."""
    return np.asarray(gen.truth()["pd_by_grade"][f"{float(years):g}"], dtype=float)


def _pooled(steps: list[dict[str, Any]], treatment: str = "exclude") -> dict[str, Any]:
    """Anderson and Goodman's pooled cohort matrix (2.8) of the annual steps, withdrawals by ``treatment``."""
    return pooled_cohort([s["counts"] for s in steps], [s["withdrawn"] for s in steps], treatment=treatment)


# ---------------------------------------------------------------------------------------------------------------------
# the summaries of repeated estimates


def _performance(est: np.ndarray, truth: np.ndarray) -> dict[str, list[Any]]:
    """``harness.estimator_performance`` of each grade's estimates (repetitions x grades) against its truth, as
    arrays by grade; undefined estimates (NaN) are left out, and a grade with fewer than two defined is None."""
    out: dict[str, list[Any]] = {"n": [], "truth": [], **{k: [] for k in PERFORMANCE}}
    for g in range(est.shape[1]):
        col = est[:, g]
        ok = int(np.isfinite(col).sum())
        out["truth"].append(float(truth[g]))
        out["n"].append(ok)
        perf = estimator_performance(col, float(truth[g])) if ok >= 2 else None
        for k in PERFORMANCE:
            out[k].append(None if perf is None else float(perf[k]))
    return out


def _mean_mcse(x: np.ndarray) -> dict[str, list[Any]]:
    """The mean by grade of a quantity with no truth (a share), with its Monte Carlo SE: the harness's bias MCSE,
    sqrt(sum((x_i - mean)^2) / (n (n - 1))), which does not depend on the truth."""
    perf = _performance(x, np.zeros(x.shape[1]))
    return {"n": perf["n"], "mean": perf["mean"], "mean_mcse": perf["bias_mcse"]}


def _scalar_performance(est: np.ndarray, truth: float) -> dict[str, Any] | None:
    """``harness.estimator_performance`` of one quantity per repetition (undefined ones, NaN, left out), or None with
    fewer than two defined."""
    return estimator_performance(est, truth) if int(np.isfinite(est).sum()) >= 2 else None


def _rates(hits: np.ndarray, undefined: np.ndarray | None = None) -> list[dict[str, Any]]:
    """A harness ``Rate`` per grade: the repetitions (rows) where ``hits`` holds, the undefined ones counted apart."""
    reps = hits.shape[0]
    und = np.zeros(hits.shape[1], dtype=int) if undefined is None else undefined.sum(axis=0)
    return [Rate(int(hits[:, g].sum()), reps, int(und[g])).to_dict() for g in range(hits.shape[1])]


# ---------------------------------------------------------------------------------------------------------------------
# the tests, run by the harness on the rung's datasets; the first four feeds are the engine's size study's
# (NULL_SCENARIOS)


def _feed_periods(d: dict[str, Any]) -> dict[str, Any]:
    return {"counts_by_period": [s["counts"] for s in d["steps"]]}


def _feed_triplets(d: dict[str, Any]) -> dict[str, Any]:
    return {"triplets": d["triplets"]}


def _feed_paths(d: dict[str, Any]) -> dict[str, Any]:
    return {"paths": d["segments"]}


def _feed_first_step(reference: np.ndarray) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def feed(d: dict[str, Any]) -> dict[str, Any]:
        return {"counts": d["steps"][0]["counts"], "reference": reference}

    return feed


def _feed_last_step(reference: np.ndarray) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def feed(d: dict[str, Any]) -> dict[str, Any]:
        return {"counts": d["steps"][-1]["counts"], "reference": reference}

    return feed


def _feed_stressed_step(d: dict[str, Any]) -> dict[str, Any]:
    """The third year's counts against the pooled matrix of the same draw."""
    return {"counts": d["steps"][STRESSED_STEP]["counts"], "reference": _pooled(d["steps"])["matrix"]}


def _simulations(gen: RatingPaths, tests: list[tuple[str, Callable[[dict[str, Any]], dict[str, Any]]]], *,
                 seed: int, reps: int, rung: float | None, label: str) -> list[dict[str, Any]]:
    """C22-style rows: each test's rejection rates at 5% and 1% over the rung's repetitions (``harness.simulate``),
    every row with the rung's seed, so each test reads the datasets the rung's estimators read."""
    rows = []
    for tid, feed in tests:
        sim = simulate(tid, gen, n_rep=reps, seed=seed, feed=feed, alphas=LEVELS)
        rows.append({"key": f"{tid}@{label}", "test_id": sim.test_id, "rung": rung,
                     "rates": {r: v.to_dict() for r, v in sim.rates.items()}, "seed": seed, "n_rep": reps})
    return rows


# ---------------------------------------------------------------------------------------------------------------------
# the families


Family = tuple[list[dict[str, Any]], list[dict[str, Any]]]


def _markov(q: np.ndarray, obligors: list[int], case_seed: int, reps: int) -> Family:
    """The Markov null: six estimators of the one-year PD against the truth, the four tests' size, interval coverage."""
    gen = _paths(q, obligors)
    pd1 = _pd(gen)
    key = SEED_KEYS["markov"]
    seed = _seed(case_seed, key)
    est = {name: np.full((reps, D), np.nan) for name in ESTIMATORS}
    cover = {name: np.zeros((reps, D), dtype=bool) for name in INTERVALS}
    n_boot = min(BOOT_REPS, reps)
    boot = np.zeros((n_boot, D), dtype=bool)
    obligor_years = np.zeros((reps, D))
    em_iterations = np.zeros(reps, dtype=int)
    em_converged = np.zeros(reps, dtype=bool)
    for i, child in enumerate(_children(seed, reps)):
        rng = np.random.default_rng(child)
        d = gen.draw(rng)
        pooled = _pooled(d["steps"])
        p = pooled["matrix"]
        est["cohort"][i] = p[:D, D]
        est["duration"][i] = expm(duration_generator(d["segments"], M)["generator"])[:D, D]
        fit = em_generator([{"counts": s["counts"], "dt": 1.0} for s in d["steps"]])
        est["em"][i] = expm(fit["generator"])[:D, D]
        em_iterations[i], em_converged[i] = fit["iterations"], fit["converged"]
        for method in ("diagonal", "weighted", "jlt"):
            try:
                est[method][i] = expm(embedding.generator(p, method=method)["generator"])[:D, D]
            except ValueError:
                pass  # the log series diverges (S >= 1) or a p_ii is 0: undefined in this repetition, counted apart
        # the intervals on the pooled cohort counts: defaults over the obligor-years in each grade
        defaults, n = pooled["counts"][:D, D], pooled["row_sizes"][:D]
        obligor_years[i] = n
        for name, interval in INTERVALS.items():
            r = interval(defaults, n, level=LEVEL)
            cover[name][i] = (r["lower"] <= pd1) & (pd1 <= r["upper"])
        if i < n_boot:
            # the bootstrap's seed comes from the repetition's stream after its data, as the harness seeds a test
            # with randomness of its own
            b = pd_bootstrap(d["segments"], M, method="resample", horizon=1.0, n_boot=N_BOOT, level=LEVEL,
                             seed=int(rng.integers(0, 2**63 - 1)))
            boot[i] = (b["lower"] <= pd1) & (pd1 <= b["upper"])
        if (i + 1) % 50 == 0:
            _log(f"markov: {i + 1} of {reps} repetitions")
    tests = [("rating.time_homogeneity", _feed_periods), ("rating.markov_order", _feed_triplets),
             ("rating.matrix_reference", _feed_first_step(np.asarray(gen.truth()["one_year_matrix"]))),
             ("rating.momentum", _feed_paths)]
    sims = _simulations(gen, tests, seed=seed, reps=reps, rung=None, label="null")
    # the order test's two forms over ten times the repetitions: which form holds its size depends on the design's
    # sparsity (riskvalidation measured both on an even five-grade chain and chose the chi-square there); on S&P-like
    # cohorts the harness measures them again, on its own seed so the rows are independent of the family's
    form_seed = _seed(case_seed, "markov:order-forms")
    for form in ("chi2", "lr"):
        sim = simulate("rating.markov_order", gen, n_rep=ORDER_FORM_FACTOR * reps, seed=form_seed,
                       feed=_feed_triplets, alphas=LEVELS, test_kwargs={"form": form})
        sims.append({"key": f"rating.markov_order@form-{form}", "test_id": sim.test_id, "rung": None,
                     "rates": {r: v.to_dict() for r, v in sim.rates.items()}, "seed": form_seed,
                     "n_rep": ORDER_FORM_FACTOR * reps})
    rung = {
        "value": None, "seed_key": key, "seed": seed, "level": LEVEL,
        "obligor_years": obligor_years.mean(axis=0).tolist(),
        "estimators": {name: {**_performance(e, pd1), "zero": _rates(e == 0.0, np.isnan(e))}
                       for name, e in est.items()},
        "em": {"converged": Rate(int(em_converged.sum()), reps).to_dict(),
               "iterations_mean": float(em_iterations.mean()), "iterations_max": int(em_iterations.max())},
        "coverage": {**{name: _rates(c) for name, c in cover.items()}, "bootstrap": _rates(boot)},
        "bootstrap": {"method": "resample", "estimate": "duration", "horizon": 1.0, "n_boot": N_BOOT,
                      "repetitions": n_boot},
    }
    return [rung], sims


def _momentum(q: np.ndarray, obligors: list[int], case_seed: int, reps: int) -> Family:
    """Downward momentum along alpha: the path tests' power and the hazard's fitted coefficient; the five-year frequency
    against the Markov projections."""
    base = _paths(q, obligors)
    pd1, pd5 = _pd(base), _pd(base, YEARS)
    rungs, sims = [], []
    for alpha in ALPHAS:
        mom = None if alpha == 0 else ((alpha, BETA), (alpha, BETA))
        gen = base if mom is None else _paths(q, obligors, momentum=mom, investment_grades=INVESTMENT_GRADES)
        key = f"momentum:alpha={alpha:g}"
        seed = _seed(case_seed, key)
        one, freq, power, dur = (np.zeros((reps, D)) for _ in range(4))
        coefficient = np.full(reps, np.nan)
        for i, child in enumerate(_children(seed, reps)):
            d = gen.draw(np.random.default_rng(child))
            p = _pooled(d["steps"])["matrix"]
            one[i] = p[:D, D]
            # the chain's own five-year default rate: the cohort estimator on the step from the first snapshot to the
            # last, the initial cohort followed to year five (the momentum chain's truth, estimated)
            five = gen.snapshot_counts(d["snapshot_states"][:, [0, YEARS]])[0]
            freq[i] = cohort(five["counts"], five["withdrawn"])["matrix"][:D, D]
            power[i] = np.linalg.matrix_power(p, YEARS)[:D, D]
            dur[i] = expm(YEARS * duration_generator(d["segments"], M)["generator"])[:D, D]
            # the hazard test on this draw, fed as the harness feeds it: its fitted c (absent, so undefined, when no
            # grade has stays of both kinds with exits)
            coefficient[i] = rating_momentum(**_feed_paths(d)).extras.get("coefficient", np.nan)
        zero = np.zeros(D)
        rungs.append({
            "value": alpha, "seed_key": key, "seed": seed,
            "momentum": None if mom is None else [list(m) for m in mom], "investment_grades": INVESTMENT_GRADES,
            # c of lambda = q_g exp(c Z), Z = 1 for a stay entered by a downgrade: 0 for a Markov chain, its truth
            "coefficient": _scalar_performance(coefficient, 0.0),
            "pd_1y_cohort": _performance(one, pd1),
            "pd_5y_frequency": _performance(freq, pd5),
            "pd_5y_cohort_power": _performance(power, pd5),
            "pd_5y_duration": _performance(dur, pd5),
            # the projections' errors against the frequency, paired by repetition
            "error_cohort_power": _performance(power - freq, zero),
            "error_duration": _performance(dur - freq, zero),
        })
        tests = [("rating.time_homogeneity", _feed_periods), ("rating.markov_order", _feed_triplets),
                 ("rating.momentum", _feed_paths)]
        sims += _simulations(gen, tests, seed=seed, reps=reps, rung=alpha, label=f"alpha{alpha:g}")
        _log(f"momentum alpha {alpha:g}")
    return rungs, sims


def stressed_generator(q: np.ndarray, k: float) -> np.ndarray:
    """The recession regime: every downgrade rate of the performing rows (the upper triangle, default included) times
    k, the diagonal rebalanced so the rows sum to 0; default stays absorbing."""
    qk = np.array(q, dtype=float)
    qk[np.triu_indices(M, k=1)] *= k
    qk[D] = 0.0
    np.fill_diagonal(qk, 0.0)
    np.fill_diagonal(qk, -qk.sum(axis=1))
    return qk


def _cycle(q: np.ndarray, obligors: list[int], case_seed: int, reps: int) -> Family:
    """A recession year in a stable chain: what time homogeneity and the reference test see; the stressed year's PD,
    the long-run average and the pooled PD."""
    base = _paths(q, obligors)
    pd1 = _pd(base)
    rungs, sims = [], []
    for k in CYCLE_K:
        qk = stressed_generator(q, k)
        gen = base if k == 1 else _paths(q, obligors, regimes=((STRESS[0], qk), (STRESS[1], q)))
        pd_k = _pd(_paths(qk, obligors))
        # the five years' true one-year PDs averaged: four years at Q, the third at Q_k
        pd_average = ((YEARS - 1) * pd1 + pd_k) / YEARS
        key = f"cycle:k={k:g}"
        seed = _seed(case_seed, key)
        stressed, lra, pooled = (np.zeros((reps, D)) for _ in range(3))
        for i, child in enumerate(_children(seed, reps)):
            d = gen.draw(np.random.default_rng(child))
            # each year's cohort PD (the engine's cohort matrix of the step, NaN for a grade without ratings)
            yearly = np.array([cohort(s["counts"], s["withdrawn"])["matrix"][:D, D] for s in d["steps"]])
            stressed[i] = yearly[STRESSED_STEP]
            # paragraph 84: the mean of the yearly rates, over the years where the grade has ratings
            used = np.isfinite(yearly).sum(axis=0)
            lra[i] = np.divide(np.nansum(yearly, axis=0), used, out=np.full(D, np.nan), where=used > 0)
            pooled[i] = _pooled(d["steps"])["matrix"][:D, D]
        rungs.append({
            "value": k, "seed_key": key, "seed": seed, "stressed_period": list(STRESS) if k != 1 else None,
            "pd_true_base": pd1.tolist(), "pd_true_stressed": pd_k.tolist(), "pd_true_average": pd_average.tolist(),
            # against the stable chain's truth: the stressed year's deviation (paragraph 66(c))
            "pd_stressed_year": _performance(stressed, pd1),
            # against the five years' true average, the quantity paragraph 84's average estimates
            "pd_lra": _performance(lra, pd_average),
            # Anderson and Goodman (2.8) against the stable chain's truth: the stressed year's weight in the pooled
            # matrix, each year weighted by its cohort
            "pd_pooled": _performance(pooled, pd1),
        })
        tests = [("rating.time_homogeneity", _feed_periods), ("rating.matrix_reference", _feed_stressed_step)]
        sims += _simulations(gen, tests, seed=seed, reps=reps, rung=k, label=f"k{k:g}")
        _log(f"cycle k {k:g}")
    return rungs, sims


def _ordered(seg: Mapping[str, Any]) -> dict[str, np.ndarray]:
    s = {k: np.asarray(seg[k]) for k in ("obligor", "start", "stop", "state", "to")}
    order = np.lexsort((s["start"], s["obligor"]))
    return {k: v[order] for k, v in s.items()}


def truncation(latent: Mapping[str, Any], observed: Mapping[str, Any]) -> dict[str, int]:
    """Verify that every observed path is its latent path truncated at a withdrawal: the same stays up to it, the stay
    it falls in cut there (``to`` WITHDRAWN, before the latent stay ends), nothing after it; an obligor never withdrawn
    keeps its whole path. Returns the obligors and how many were withdrawn; raises ValueError where it does not hold."""
    lat, obs = _ordered(latent), _ordered(observed)
    n = int(max(lat["obligor"].max(), obs["obligor"].max())) + 1
    n_lat = np.bincount(lat["obligor"], minlength=n)
    n_obs = np.bincount(obs["obligor"], minlength=n)
    if np.any(n_obs < 1) or np.any(n_obs > n_lat):
        raise ValueError("an obligor's observed path is missing or longer than its latent path")
    pos = np.arange(obs["obligor"].size) - (np.cumsum(n_obs) - n_obs)[obs["obligor"]]
    j = (np.cumsum(n_lat) - n_lat)[obs["obligor"]] + pos  # the latent stay each observed stay must be
    same = (obs["start"] == lat["start"][j]) & (obs["state"] == lat["state"][j])
    whole = (obs["stop"] == lat["stop"][j]) & (obs["to"] == lat["to"][j])
    cut = (obs["to"] == WITHDRAWN) & (obs["start"] < obs["stop"]) & (obs["stop"] < lat["stop"][j])
    last = pos == n_obs[obs["obligor"]] - 1
    complete = (n_obs == n_lat)[obs["obligor"]]
    ok = same & np.where(last, (whole & complete) | cut, whole)
    if not np.all(ok):
        bad = int(obs["obligor"][np.flatnonzero(~ok)[0]])
        raise ValueError(f"obligor {bad}: the observed path is not its latent path truncated at a withdrawal")
    return {"obligors": n, "withdrawn": int(np.sum(last & cut))}


def _withdrawals(q: np.ndarray, obligors: list[int], case_seed: int, reps: int) -> Family:
    """Informative withdrawal along k: three treatments of the withdrawn ratings and the latent chain against the
    truth, on paired draws; what time homogeneity and the reference test see of it."""
    latent_gen = _paths(q, obligors)
    pd1 = _pd(latent_gen)
    tests = [("rating.time_homogeneity", _feed_periods),
             ("rating.matrix_reference", _feed_last_step(np.asarray(latent_gen.truth()["one_year_matrix"])))]
    rungs, sims = [], []
    for k in INFORMATIVE:
        gen = _paths(q, obligors, withdrawal_rate=WITHDRAWAL_RATE, informative=k, window=WINDOW)
        key = f"withdrawals:informative={k:g}"
        seed = _seed(case_seed, key)
        removed, kept, followed, latent, share = (np.zeros((reps, D)) for _ in range(5))
        withdrawn = np.zeros(reps)
        for i, child in enumerate(_children(seed, reps)):
            # the same seed with and without withdrawals: the engine draws the withdrawals after the path, from the
            # same stream, so the observed paths should be the latent ones truncated; verified, not assumed
            lat = latent_gen.draw(np.random.default_rng(child))
            obs = gen.draw(np.random.default_rng(child))
            withdrawn[i] = truncation(lat["segments"], obs["segments"])["withdrawn"]
            ex = _pooled(obs["steps"])
            removed[i] = ex["matrix"][:D, D]
            share[i] = ex["withdrawn_share"][:D]
            kept[i] = _pooled(obs["steps"], treatment="state")["matrix"][:D, D]
            # followed: each year's cohort as observed (the ratings outstanding at its start), its end read on the
            # latent paths, so a rating withdrawn within the year that defaults by its end counts as a default
            o, la = obs["snapshot_states"], lat["snapshot_states"]
            if o.shape != la.shape:
                raise ValueError("the observed and latent snapshots cover different obligors")
            steps = [gen.snapshot_counts(np.column_stack([o[:, t], la[:, t + 1]]))[0] for t in range(YEARS)]
            followed[i] = _pooled(steps)["matrix"][:D, D]
            latent[i] = _pooled(lat["steps"])["matrix"][:D, D]
        rungs.append({
            "value": k, "seed_key": key, "seed": seed, "withdrawal_rate": WITHDRAWAL_RATE, "window": WINDOW,
            "truncation_verified": reps, "withdrawn_obligors_mean": float(withdrawn.mean()),
            # the pooled share of each grade's ratings withdrawn within a year, w / (n + w), with its MC SE
            "withdrawn_share": _mean_mcse(share),
            "pd_removed": _performance(removed, pd1),
            "pd_kept": _performance(kept, pd1),
            "pd_followed": _performance(followed, pd1),
            # every obligor followed every year, withdrawn or not: the latent chain's own cohort PD
            "pd_latent": _performance(latent, pd1),
        })
        sims += _simulations(gen, tests, seed=seed, reps=reps, rung=k, label=f"k{k:g}")
        _log(f"withdrawals informative {k:g}")
    return rungs, sims


def _thin(q: np.ndarray, obligors: list[int]) -> Family:
    """Exact coverage, expected length and adjacent overlap of the intervals at n obligors per grade, by enumerating
    the binomial count: riskvalidation's ``exact_coverage`` and ``overlap_probability`` (0.04.002)."""
    pd1 = _pd(_paths(q, obligors))
    rungs = []
    for n in THIN_N:
        coverage, length = {}, {}
        for name in INTERVALS:
            ex = exact_coverage(name, n, pd1, level=LEVEL)
            coverage[name] = [float(x) for x in ex["coverage"]]
            length[name] = [float(x) for x in ex["expected_length"]]
        rungs.append({
            "value": n, "level": LEVEL, "expected_defaults": (n * pd1).tolist(),
            "coverage": coverage, "length": length,
            # P(the Jeffreys intervals of grades g and g + 1 overlap), summed over every pair of counts
            "overlap_jeffreys": [overlap_probability("jeffreys", n, float(pd1[g]), float(pd1[g + 1]), level=LEVEL)
                                 for g in range(D - 1)],
        })
    return rungs, []


# ---------------------------------------------------------------------------------------------------------------------


def family_outputs(family: str, q: np.ndarray, obligors: list[int], case_seed: int, reps: int = 200, *,
                   source: str = SOURCE) -> dict[str, Any]:
    """The outputs of one generator family (contract section 2): ``q`` the 8 x 8 generator (seven grades and default,
    default absorbing, finite, default reachable from every grade), ``obligors`` the cohort size by grade (positive
    integers), ``reps`` the repetitions per rung (the thin family is exact and draws nothing), ``source`` what ``q``
    is, printed in the outputs."""
    if family not in FAMILIES:
        raise ValueError(f"family must be one of {FAMILIES}, got {family!r}")
    qa = np.asarray(q, dtype=float)
    if qa.shape != (M, M):
        raise ValueError(f"q must be {M} x {M} (seven grades and default), got shape {qa.shape}")
    if not np.all(np.isfinite(qa)):
        # the engine's generator check compares, and a comparison with NaN is false: a NaN rate would pass it and
        # the path simulation would never end
        raise ValueError("q must be finite: every rate a number")
    sizes = np.asarray(obligors, dtype=float)
    if sizes.shape != (D,) or not np.all(np.isfinite(sizes)) or np.any(sizes <= 0) or np.any(sizes != np.round(sizes)):
        raise ValueError("obligors must give a positive integer cohort size for each of the seven grades")
    ob = [int(x) for x in sizes]
    if family != "thin" and reps < 2:
        raise ValueError("at least two repetitions are needed for a Monte Carlo standard error")
    gen = _paths(qa, ob)  # checks that q is a generator with default absorbing
    pd1 = _pd(gen)
    unreachable = [GRADES[g] for g in range(D) if not pd1[g] > 0.0]
    if unreachable:
        # a true PD of 0 makes every interval cover it and every error 0: an artifact that looks perfect
        raise ValueError(f"default is unreachable from {', '.join(unreachable)} (true one-year PD 0): q needs a path "
                         "of positive rates to default from every grade")
    t0 = time.perf_counter()
    if family == "thin":
        rungs, sims = _thin(qa, ob)
    else:
        run = {"markov": _markov, "momentum": _momentum, "cycle": _cycle, "withdrawals": _withdrawals}[family]
        rungs, sims = run(qa, ob, int(case_seed), int(reps))
    _log(f"{family}: {len(rungs)} rungs, {len(sims)} simulations, {time.perf_counter() - t0:.1f} s")
    exact = family == "thin"
    out = {
        "kind": "generator",
        "family": family,
        "generator": {"q": qa.tolist(), "pd_1y": pd1.tolist(), "pd_5y": _pd(gen, YEARS).tolist(),
                      "obligors": ob, "source": str(source)},
        "design": {"years": 1 if exact else YEARS, "snapshots": [0.0, 1.0] if exact else list(SNAPSHOTS),
                   "reps": 0 if exact else int(reps), "seed_key": SEED_KEYS[family]},
        "ladder": LADDERS[family],
        "rungs": rungs,
        "simulations": sims,
    }
    return jsonable(out)
