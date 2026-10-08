"""C04's known-truth generator families (CT-405, contract section 2). At a few repetitions of CEREP-like cohorts: the
contract's keys for every family, JSON-safe values, determinism, the harness's datasets equal to the estimators', the
truncation of the withdrawal draws, the thin family's exact sums against brute force, the planted defects seen where
they are strong, and the inputs refused. At 30 repetitions of 2,000 obligors per grade, where the values are
informative: each estimate against its truth within four Monte Carlo standard errors (the Markov estimators, the
Markov projections at no momentum, the stressed year and the long-run average, the latent and the followed PD), the
coverage of the intervals, the removed PD's understatement under informative withdrawal, and the RMSE against a direct
computation. The full run (200 repetitions per rung) is the bake's."""
from __future__ import annotations

import json
import math

import numpy as np
import pytest
from scipy import stats
from scipy.linalg import expm

from pipeline.cases import c04_families as fam
from riskvalidation.harness import estimator_performance, simulate, size_bound
from riskvalidation.transitions.estimators import WITHDRAWN
from riskvalidation.transitions.intervals import pd_agresti_coull, pd_jeffreys, pd_wald
from riskvalidation.validation.transitions import rating_momentum

REPS = 6
SEED = 20261006
OBLIGORS = [80, 550, 1800, 1500, 800, 900, 200]  # about S&P's EU cohort by grade
SOURCE = "a hand-made generator with CEREP-like rates (tests/test_c04_families.py)"
VALUE_REPS, VALUE_SEED, VALUE_OBLIGORS = 30, 20261007, [2000] * 7
Z = 4.0                         # a value check fails beyond four Monte Carlo standard errors
CHECKED = slice(3, 7)           # BBB to CCC-C: grades with enough defaults for the checks to be informative


def _generator() -> np.ndarray:
    """A hand-made generator with CEREP-like rates (seven grades and default): the top grade's one-year PD about 1bp
    (0.96bp), CCC-C's about 25%."""
    q = np.array([
        # AAA   AA      A       BBB     BB      B       CCC-C    D
        [0.0, 0.0800, 0.0080, 0.0010, 0.0003, 0.0001, 0.00002, 0.00008],
        [0.0100, 0.0, 0.0900, 0.0070, 0.0020, 0.0006, 0.0001, 0.0002],
        [0.0010, 0.0250, 0.0, 0.0600, 0.0060, 0.0020, 0.0004, 0.0006],
        [0.0003, 0.0030, 0.0450, 0.0, 0.0500, 0.0080, 0.0017, 0.0020],
        [0.0001, 0.0010, 0.0050, 0.0650, 0.0, 0.0900, 0.0100, 0.0090],
        [0.0, 0.0003, 0.0020, 0.0050, 0.0700, 0.0, 0.0900, 0.0330],
        [0.0, 0.0, 0.0010, 0.0020, 0.0100, 0.1500, 0.0, 0.3100],
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    ])
    np.fill_diagonal(q, -q.sum(axis=1))
    return q


def _rebalanced(q: np.ndarray) -> np.ndarray:
    """``q`` with its diagonal set so the rows sum to 0."""
    out = q.copy()
    np.fill_diagonal(out, 0.0)
    np.fill_diagonal(out, -out.sum(axis=1))
    return out


Q = _generator()
PD1, PD5 = expm(Q)[:7, 7], expm(5.0 * Q)[:7, 7]
RATE_KEYS = {"rejections", "n", "undefined", "rate", "se", "wilson_low", "wilson_high"}
PERF_KEYS = {"n", "truth", "mean", "bias", "bias_mcse", "empirical_se", "empirical_se_mcse", "rmse", "rmse_mcse"}
#: the Markov family's two extra rows: the order test's chi-square and likelihood ratio over ten times the repetitions
FORM_KEYS = {"rating.markov_order@form-chi2", "rating.markov_order@form-lr"}
RUNG_KEYS = {
    "markov": {"value", "seed_key", "seed", "level", "obligor_years", "estimators", "em", "coverage", "bootstrap"},
    "momentum": {"value", "seed_key", "seed", "momentum", "investment_grades", "coefficient", "pd_1y_cohort",
                 "pd_5y_frequency", "pd_5y_cohort_power", "pd_5y_duration", "error_cohort_power", "error_duration"},
    "cycle": {"value", "seed_key", "seed", "stressed_period", "pd_true_base", "pd_true_stressed", "pd_true_average",
              "pd_stressed_year", "pd_lra", "pd_pooled"},
    "withdrawals": {"value", "seed_key", "seed", "withdrawal_rate", "window", "truncation_verified",
                    "withdrawn_obligors_mean", "withdrawn_share", "pd_removed", "pd_kept", "pd_followed", "pd_latent"},
    "thin": {"value", "level", "expected_defaults", "coverage", "length", "overlap_jeffreys"},
}
TH, ORDER, REF, MOM = "rating.time_homogeneity", "rating.markov_order", "rating.matrix_reference", "rating.momentum"
TESTS = {"markov": {TH, ORDER, REF, MOM}, "momentum": {TH, ORDER, MOM}, "cycle": {TH, REF}, "withdrawals": {TH, REF},
         "thin": set()}
LABEL = {"markov": lambda v: "null", "momentum": lambda v: f"alpha{v:g}", "cycle": lambda v: f"k{v:g}",
         "withdrawals": lambda v: f"k{v:g}"}
SEED_KEY = {"markov": lambda v: "markov:null", "momentum": lambda v: f"momentum:alpha={v:g}",
            "cycle": lambda v: f"cycle:k={v:g}", "withdrawals": lambda v: f"withdrawals:informative={v:g}"}


@pytest.fixture(scope="module")
def outputs() -> dict[str, dict]:
    return {f: fam.family_outputs(f, Q, OBLIGORS, SEED, reps=REPS, source=SOURCE) for f in fam.FAMILIES}


@pytest.fixture(scope="module")
def informative() -> dict[str, dict]:
    """The simulated families where their values are informative: 2,000 obligors per grade, 30 repetitions."""
    return {f: fam.family_outputs(f, Q, VALUE_OBLIGORS, VALUE_SEED, reps=VALUE_REPS, source=SOURCE)
            for f in ("markov", "momentum", "cycle", "withdrawals")}


def _plain(x) -> bool:
    """Only lists, dicts with string keys, str, bool, int, finite float and None."""
    if isinstance(x, dict):
        return all(isinstance(k, str) and _plain(v) for k, v in x.items())
    if isinstance(x, list):
        return all(_plain(v) for v in x)
    if isinstance(x, float):
        return math.isfinite(x)
    return x is None or isinstance(x, (str, bool, int))


def _blocks(x, keys: set[str]):
    """Every dict below ``x`` whose keys are exactly ``keys``."""
    if isinstance(x, dict):
        if set(x) == keys:
            yield x
        for v in x.values():
            yield from _blocks(v, keys)
    elif isinstance(x, list):
        for v in x:
            yield from _blocks(v, keys)


def _z(block: dict, truth=None) -> np.ndarray:
    """(mean - truth) / its Monte Carlo SE, BBB to CCC-C; the block's own truth unless another is given."""
    t = np.asarray(block["truth"] if truth is None else truth, dtype=float)
    mean, mcse = np.asarray(block["mean"], dtype=float), np.asarray(block["bias_mcse"], dtype=float)
    return ((mean - t) / mcse)[CHECKED]


def _rung(out: dict, value: float) -> dict:
    return next(r for r in out["rungs"] if r["value"] == value)


def _rate(out: dict, key: str) -> float:
    return next(s for s in out["simulations"] if s["key"] == key)["rates"]["p<0.05"]["rate"]


def test_contract_keys_of_every_family(outputs):
    """Contract section 2: the top-level shape, the generator and its truth, the design, the ladder printed with its
    rungs, the per-rung quantities by grade (the fitted momentum coefficient a scalar), and C22-style simulation rows
    seeded by the rung's key."""
    for f, out in outputs.items():
        assert set(out) == {"kind", "family", "generator", "design", "ladder", "rungs", "simulations"}, f
        assert out["kind"] == "generator" and out["family"] == f
        g = out["generator"]
        assert set(g) == {"q", "pd_1y", "pd_5y", "obligors", "source"} and g["obligors"] == OBLIGORS
        assert g["q"] == Q.tolist() and g["source"] == SOURCE
        np.testing.assert_allclose(g["pd_1y"], PD1, rtol=1e-12)
        np.testing.assert_allclose(g["pd_5y"], PD5, rtol=1e-12)
        if f == "thin":  # exact: one year, nothing drawn, no seed
            assert out["design"] == {"years": 1, "snapshots": [0.0, 1.0], "reps": 0, "seed_key": None}
        else:
            assert out["design"] == {"years": 5, "snapshots": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0], "reps": REPS,
                                     "seed_key": fam.SEED_KEYS[f]} and isinstance(fam.SEED_KEYS[f], str)
        if f == "markov":
            assert out["ladder"] is None and [r["value"] for r in out["rungs"]] == [None]
        else:
            ladder = out["ladder"]
            assert set(ladder) == {"name", "unit", "values"} and set(ladder["name"]) == {"en", "es"}
            assert [r["value"] for r in out["rungs"]] == ladder["values"] and isinstance(ladder["unit"], str)
        for rung in out["rungs"]:
            assert set(rung) == RUNG_KEYS[f], (f, set(rung) ^ RUNG_KEYS[f])
            if f in SEED_KEY:
                assert rung["seed_key"] == SEED_KEY[f](rung["value"])
                assert rung["seed"] == fam._seed(SEED, rung["seed_key"])
        scalar = [r["coefficient"] for r in out["rungs"] if f == "momentum"]
        for block in _blocks(out["rungs"], PERF_KEYS):
            if any(block is s for s in scalar):
                assert all(isinstance(v, (int, float)) for v in block.values()), f
            else:
                assert all(isinstance(v, list) and len(v) == 7 for v in block.values()), f
        # simulation rows: one per test and rung, keyed test@rung, the rung's seed, both levels
        forms = [s for s in out["simulations"] if s["key"] in FORM_KEYS]
        assert len(forms) == (2 if f == "markov" else 0)
        for s in forms:
            assert s["test_id"] == "rating.markov_order" and s["rung"] is None
            assert s["n_rep"] == fam.ORDER_FORM_FACTOR * REPS and s["seed"] == fam._seed(SEED, "markov:order-forms")
            assert all(r["n"] == s["n_rep"] for r in s["rates"].values())
        sims = [s for s in out["simulations"] if s["key"] not in FORM_KEYS]
        assert {s["test_id"] for s in sims} == TESTS[f] and len(sims) == len(out["rungs"]) * len(TESTS[f])
        assert len({s["key"] for s in sims}) == len(sims)
        seeds = {r["value"]: r.get("seed") for r in out["rungs"]}
        for s in sims:
            assert set(s) == {"key", "test_id", "rung", "rates", "seed", "n_rep"}
            assert s["key"] == f"{s['test_id']}@{LABEL[f](s['rung'])}" and s["seed"] == seeds[s["rung"]]
            assert set(s["rates"]) == {"p<0.05", "p<0.01"} and s["n_rep"] == REPS
            for r in s["rates"].values():
                assert set(r) == RATE_KEYS and r["n"] == REPS
                assert r["se"] == pytest.approx(math.sqrt(r["rate"] * (1 - r["rate"]) / REPS), abs=1e-12)
    for rung in outputs["withdrawals"]["rungs"]:  # a share with its Monte Carlo SE, by grade
        share = rung["withdrawn_share"]
        assert set(share) == {"n", "mean", "mean_mcse"} and all(len(v) == 7 for v in share.values())


def test_outputs_are_json_safe(outputs):
    for f, out in outputs.items():
        assert _plain(out), f
        json.dumps(out, allow_nan=False)


def test_markov_estimators_intervals_and_tests(outputs):
    """The six estimators by grade with their errors, zero shares and the EM's convergence; the coverage of the three
    intervals and of the bootstrap; the four tests at their null."""
    rung = outputs["markov"]["rungs"][0]
    est = rung["estimators"]
    assert list(est) == list(fam.ESTIMATORS)
    for name, block in est.items():
        assert set(block) == PERF_KEYS | {"zero"}, name
        assert None not in block["mean"] and None not in block["rmse"], name
        for b, r in zip(block["bias"], block["rmse"], strict=True):
            assert r >= abs(b) - 1e-15  # RMSE^2 = bias^2 + (n - 1)/n EmpSE^2
        assert len(block["zero"]) == 7 and all(set(z) == RATE_KEYS and z["n"] == REPS for z in block["zero"])
    # the duration PD reaches default through the paths and is never exactly zero; the cohort PD of the top grade
    # (about 400 obligor-years at 1bp) is zero in most repetitions (finding F-COHORT-ZERO)
    assert all(z["rejections"] == 0 for z in est["duration"]["zero"])
    assert est["cohort"]["zero"][0]["rate"] > 0.5
    assert rung["em"]["converged"]["n"] == REPS and rung["em"]["iterations_max"] >= rung["em"]["iterations_mean"]
    assert set(rung["coverage"]) == {"wald", "agresti_coull", "jeffreys", "bootstrap"}
    assert all(r["n"] == min(fam.BOOT_REPS, REPS) for r in rung["coverage"]["bootstrap"])
    assert rung["bootstrap"]["n_boot"] == 500 and rung["level"] == 0.95
    assert all(s["rung"] is None and (s["key"].endswith("@null") or s["key"] in FORM_KEYS)
               for s in outputs["markov"]["simulations"])


def test_harness_tests_read_the_estimators_datasets(outputs):
    """Common random numbers: the harness draws repetition i of a rung from the same stream as the module does, so a
    test's statistic in the harness equals the statistic on the module's own draw, and the fitted coefficient the
    module reports is the hazard test's on those draws."""
    alpha = fam.ALPHAS[-1]
    rung = _rung(outputs["momentum"], alpha)
    gen = fam._paths(Q, OBLIGORS, momentum=((alpha, fam.BETA), (alpha, fam.BETA)),
                     investment_grades=fam.INVESTMENT_GRADES)
    sim = simulate(MOM, gen, n_rep=REPS, seed=rung["seed"], feed=fam._feed_paths)
    coefficients = []
    for i, child in enumerate(fam._children(rung["seed"], REPS)):
        r = rating_momentum(gen.draw(np.random.default_rng(child))["segments"])
        assert r.statistic == sim.statistics[i]
        coefficients.append(r.extras["coefficient"])
    c = rung["coefficient"]
    assert c["n"] == REPS and c["truth"] == 0.0
    assert c["mean"] == pytest.approx(float(np.mean(coefficients)), rel=1e-12)
    assert c["bias_mcse"] == pytest.approx(float(np.std(coefficients, ddof=1) / math.sqrt(REPS)), rel=1e-9)


def test_determinism(outputs):
    """CT-409: the same seed gives identical outputs; another seed does not."""
    for f in fam.FAMILIES:
        again = fam.family_outputs(f, Q, OBLIGORS, SEED, reps=REPS, source=SOURCE)
        assert json.dumps(again, sort_keys=True) == json.dumps(outputs[f], sort_keys=True), f
    other = fam.family_outputs("cycle", Q, OBLIGORS, SEED + 1, reps=REPS, source=SOURCE)
    assert json.dumps(other, sort_keys=True) != json.dumps(outputs["cycle"], sort_keys=True)


def test_withdrawals_truncate_the_latent_paths(outputs):
    """The observed paths are the latent ones (the same seed without withdrawals) truncated at each withdrawal; the
    check refuses a path changed before its withdrawal, a stay dropped, a path cut without a withdrawal and a cut past
    the latent stay. The three treatments order as their definitions force."""
    latent_gen = fam._paths(Q, OBLIGORS)
    gen = fam._paths(Q, OBLIGORS, withdrawal_rate=0.06, informative=9.0, window=1.0)
    child = fam._children(fam._seed(SEED, "withdrawals:informative=9"), 1)[0]
    lat = latent_gen.draw(np.random.default_rng(child))["segments"]
    obs = gen.draw(np.random.default_rng(child))["segments"]
    check = fam.truncation(lat, obs)
    assert check["obligors"] == sum(OBLIGORS) and check["withdrawn"] == int(np.sum(obs["to"] == WITHDRAWN)) > 0

    def tampered(rows: np.ndarray, **change) -> dict[str, np.ndarray]:
        out = {k: np.delete(v, rows) if change.get("drop") else v.copy() for k, v in obs.items()}
        for k, v in change.items():
            if k != "drop":
                out[k][rows] = v
        return out

    ob, to = obs["obligor"], obs["to"]
    first_of_two = np.flatnonzero((ob[:-1] == ob[1:]))[0]          # a stay followed by another of the same obligor
    with pytest.raises(ValueError):
        fam.truncation(lat, tampered(np.array([first_of_two]), stop=obs["stop"][first_of_two] + 1e-3))
    with pytest.raises(ValueError):
        fam.truncation(lat, tampered(np.array([first_of_two]), drop=True))
    kept_whole = np.flatnonzero((to != WITHDRAWN) & np.r_[ob[1:] != ob[:-1], True] & np.r_[False, ob[1:] == ob[:-1]])[0]
    with pytest.raises(ValueError):  # the last stay of a path never withdrawn, dropped
        fam.truncation(lat, tampered(np.array([kept_whole]), drop=True))
    cut = np.flatnonzero(to == WITHDRAWN)[0]
    with pytest.raises(ValueError):
        fam.truncation(lat, tampered(np.array([cut]), stop=10.0))
    for rung in outputs["withdrawals"]["rungs"]:
        assert rung["truncation_verified"] == REPS and rung["withdrawn_obligors_mean"] > 0
        removed, kept, followed = (np.array(rung[k]["mean"]) for k in ("pd_removed", "pd_kept", "pd_followed"))
        # kept counts the withdrawn as survivors: below removed (a larger denominator) and below followed (fewer
        # defaults)
        assert np.all(kept <= removed + 1e-15) and np.all(kept <= followed + 1e-15)
        assert all(0.0 < s < 0.5 for s in rung["withdrawn_share"]["mean"])
        assert all(0.0 < e < s for s, e in zip(rung["withdrawn_share"]["mean"], rung["withdrawn_share"]["mean_mcse"],
                                               strict=True))


def test_thin_coverage_and_overlap_against_brute_force(outputs):
    """The thin family's exact coverage, summed count by count with the engine's scalar intervals, and the overlap of
    adjacent Jeffreys intervals summed pair by pair."""
    out = outputs["thin"]
    pd1 = np.array(out["generator"]["pd_1y"])
    rungs = {r["value"]: r for r in out["rungs"]}
    n = 200
    for g in (3, 6):
        p = pd1[g]
        for name, f in (("wald", pd_wald), ("agresti_coull", pd_agresti_coull), ("jeffreys", pd_jeffreys)):
            total = 0.0
            for d in range(n + 1):
                r = f(d, n)
                if r["lower"] <= p <= r["upper"]:
                    total += float(stats.binom.pmf(d, n, p))
            assert rungs[n]["coverage"][name][g] == pytest.approx(total, abs=1e-12), (name, g)
    m = 50
    iv = [pd_jeffreys(d, m) for d in range(m + 1)]
    for g in (0, 5):
        total = 0.0
        for d1 in range(m + 1):
            for d2 in range(m + 1):
                if iv[d1]["lower"] <= iv[d2]["upper"] and iv[d2]["lower"] <= iv[d1]["upper"]:
                    total += float(stats.binom.pmf(d1, m, pd1[g]) * stats.binom.pmf(d2, m, pd1[g + 1]))
        assert rungs[m]["overlap_jeffreys"][g] == pytest.approx(total, abs=1e-12), g
    for r in out["rungs"]:
        assert len(r["overlap_jeffreys"]) == 6 and all(0.0 <= x <= 1.0 for x in r["overlap_jeffreys"])
        np.testing.assert_allclose(r["expected_defaults"], r["value"] * pd1)


def test_planted_defects_are_seen_where_strong(outputs):
    """At twice the empirical momentum (alpha 0.25) the momentum hazard test rejects in most repetitions; with every
    downgrade rate tripled in the third year time homogeneity does; the stressed truth is above the stable one wherever
    downgrades lead to default."""
    assert fam.ALPHAS == (0.0, 0.025, 0.05, 0.125, 0.25)
    momentum = {s["key"]: s for s in outputs["momentum"]["simulations"]}
    assert momentum["rating.momentum@alpha0.25"]["rates"]["p<0.05"]["rate"] > 0.5
    cycle = {s["key"]: s for s in outputs["cycle"]["simulations"]}
    assert cycle["rating.time_homogeneity@k3"]["rates"]["p<0.05"]["rate"] > 0.5
    rungs = {r["value"]: r for r in outputs["cycle"]["rungs"]}
    assert rungs[1.0]["stressed_period"] is None and rungs[3.0]["stressed_period"] == [2.0, 3.0]
    np.testing.assert_allclose(rungs[1.0]["pd_true_stressed"], rungs[1.0]["pd_true_base"], rtol=1e-12)
    assert all(s > b for s, b in zip(rungs[3.0]["pd_true_stressed"], rungs[3.0]["pd_true_base"], strict=True))
    np.testing.assert_allclose(rungs[3.0]["pd_true_average"],
                               (4 * np.array(rungs[3.0]["pd_true_base"]) + rungs[3.0]["pd_true_stressed"]) / 5)


def test_inputs_are_checked():
    """Refused: an unknown family, a wrong shape, a missing or empty grade, one repetition, a default that is not
    absorbing, a non-finite rate (it would pass the engine's generator check and stall the simulation), a grade that
    never reaches default, and a cohort size that is not an integer. An integral float is a count."""
    with pytest.raises(ValueError):
        fam.family_outputs("drift", Q, OBLIGORS, SEED, reps=REPS)
    with pytest.raises(ValueError):
        fam.family_outputs("cycle", Q[:7, :7], OBLIGORS, SEED, reps=REPS)
    with pytest.raises(ValueError):
        fam.family_outputs("cycle", Q, OBLIGORS[:6], SEED, reps=REPS)
    with pytest.raises(ValueError):
        fam.family_outputs("cycle", Q, [0, *OBLIGORS[1:]], SEED, reps=REPS)
    with pytest.raises(ValueError):
        fam.family_outputs("cycle", Q, OBLIGORS, SEED, reps=1)
    bad = Q.copy()
    bad[7, 0] = 0.1  # default must stay absorbing
    with pytest.raises(ValueError):
        fam.family_outputs("cycle", bad, OBLIGORS, SEED, reps=REPS)
    for value in (np.nan, np.inf):
        bad = Q.copy()
        bad[2, 3], bad[2, 2] = value, -value  # a diagonal that "balances" it: only the finiteness check refuses inf
        with pytest.raises(ValueError, match="finite"):
            fam.family_outputs("cycle", bad, OBLIGORS, SEED, reps=REPS)
    no_default = Q.copy()
    no_default[:7, 7] = 0.0
    with pytest.raises(ValueError, match="unreachable from AAA, AA, A, BBB, BB, B, CCC-C "):
        fam.family_outputs("markov", _rebalanced(no_default), OBLIGORS, SEED, reps=REPS)
    closed = Q.copy()
    closed[:2, 2:] = 0.0  # AAA and AA only move between themselves
    with pytest.raises(ValueError, match=r"unreachable from AAA, AA \("):
        fam.family_outputs("thin", _rebalanced(closed), OBLIGORS, SEED)
    with pytest.raises(ValueError, match="integer"):
        fam.family_outputs("thin", Q, [80.5, *OBLIGORS[1:]], SEED)
    out = fam.family_outputs("thin", Q, [float(x) for x in OBLIGORS], SEED)
    assert out["generator"]["obligors"] == OBLIGORS and all(type(x) is int for x in out["generator"]["obligors"])
    assert out["generator"]["source"] == fam.SOURCE


# ---------------------------------------------------------------------------------------------------------------------
# the values against the truth, where they are informative (2,000 obligors per grade, 30 repetitions)


def test_markov_values_against_the_truth(informative):
    """The consistent estimators' one-year PDs lie within four MCSE of the truth (BBB to CCC-C), JLT's approximation
    (3) does not; the EM on the five years' counts is as precise as the cohort estimator on the same counts (an EM on
    fewer years is not); Agresti-Coull, Jeffreys and the bootstrap cover BB to CCC-C; the RMSE is its definition."""
    rung = informative["markov"]["rungs"][0]
    est = rung["estimators"]
    for name in ("cohort", "duration", "em", "diagonal", "weighted"):
        assert np.all(np.abs(_z(est[name])) <= Z), (name, _z(est[name]))
    assert np.all(_z(est["jlt"])[1:3] > Z)  # BB and B: the JLT generator overstates them
    se = {name: np.asarray(est[name]["empirical_se"])[CHECKED] for name in ("em", "cohort")}
    assert np.all(se["em"] <= 1.2 * se["cohort"]), se
    for name in ("agresti_coull", "jeffreys", "bootstrap"):
        assert all(c["rate"] >= 0.8 for c in rung["coverage"][name][4:]), name
    for block in est.values():
        n = np.asarray(block["n"], dtype=float)
        rmse = np.asarray(block["rmse"], dtype=float)
        emp, bias = np.asarray(block["empirical_se"], dtype=float), np.asarray(block["bias"], dtype=float)
        np.testing.assert_allclose(rmse**2, bias**2 + (n - 1) / n * emp**2, rtol=1e-9)


def test_momentum_values_at_no_momentum_and_along_the_ladder(informative):
    """At alpha 0 the chain is Markov: both Markov projections hit the five-year frequency and the frequency the truth,
    within four MCSE, and the fitted coefficient is 0 within four MCSE; along the ladder the coefficient grows."""
    out = informative["momentum"]
    r0 = _rung(out, 0.0)
    assert np.all(np.abs(_z(r0["error_cohort_power"])) <= Z), _z(r0["error_cohort_power"])
    assert np.all(np.abs(_z(r0["error_duration"])) <= Z), _z(r0["error_duration"])
    assert np.all(np.abs(_z(r0["pd_5y_frequency"], PD5)) <= Z), _z(r0["pd_5y_frequency"], PD5)
    assert np.all(np.abs(_z(r0["pd_1y_cohort"], PD1)) <= Z)
    c0 = r0["coefficient"]
    assert abs(c0["mean"]) <= Z * c0["bias_mcse"] and c0["n"] == VALUE_REPS
    c = [_rung(out, a)["coefficient"]["mean"] for a in fam.ALPHAS]
    assert all(b > a for a, b in zip(c, c[1:], strict=False)), c
    assert _rate(out, "rating.momentum@alpha0.25") > 0.9


def test_cycle_values_against_the_truth(informative):
    """At every k the stressed year's cohort PD estimates the stressed generator's PD and paragraph 84's long-run
    average the five years' true average, each within four MCSE (BBB to CCC-C)."""
    for rung in informative["cycle"]["rungs"]:
        z_year = _z(rung["pd_stressed_year"], rung["pd_true_stressed"])
        z_lra = _z(rung["pd_lra"])
        assert np.all(np.abs(z_year) <= Z) and np.all(np.abs(z_lra) <= Z), (rung["value"], z_year, z_lra)
        np.testing.assert_allclose(rung["pd_lra"]["truth"], rung["pd_true_average"], rtol=1e-12)


def test_withdrawals_values_against_the_truth(informative):
    """The latent chain's PD is the truth within four MCSE at every k, and so is the followed PD without
    informativeness; at k 9 the PD with withdrawals removed is below the truth by more than four MCSE, and the
    reference test of the last year sees it in most repetitions while it holds its size at k 0."""
    out = informative["withdrawals"]
    for rung in out["rungs"]:
        assert np.all(np.abs(_z(rung["pd_latent"])) <= Z), (rung["value"], _z(rung["pd_latent"]))
    assert np.all(np.abs(_z(_rung(out, 0.0)["pd_followed"])) <= Z)
    assert np.all(_z(_rung(out, 9.0)["pd_removed"]) < -Z), _z(_rung(out, 9.0)["pd_removed"])
    assert _rate(out, "rating.matrix_reference@k9") > 0.5
    assert _rate(out, "rating.matrix_reference@k0") <= size_bound(0.05, VALUE_REPS)


def test_rmse_against_a_direct_computation():
    """The RMSE by grade and its MCSE, from riskvalidation's ``estimator_performance`` (0.4.2: Morris et al. Table 6
    for the MSE, the delta method to the root), against a direct computation; undefined estimates left out; a grade
    with fewer than two defined is None."""
    rng = np.random.default_rng(7)
    est = rng.lognormal(-4.0, 0.6, size=(200, 3))
    est[:5, 1] = np.nan
    est[1:, 2] = np.nan
    truth = np.array([0.02, 0.025, 0.03])
    got = fam._performance(est, truth)
    for g in range(2):
        e = est[np.isfinite(est[:, g]), g] - truth[g]
        n = e.size
        mse = np.mean(e**2)
        assert got["rmse"][g] == pytest.approx(math.sqrt(mse), rel=1e-12)
        mcse_mse = np.std(e**2, ddof=1) / math.sqrt(n)
        assert got["rmse_mcse"][g] == pytest.approx(mcse_mse / (2.0 * math.sqrt(mse)), rel=1e-12)
        perf = estimator_performance(est[:, g], truth[g])
        assert got["rmse"][g] ** 2 == pytest.approx(perf["bias"] ** 2 + (n - 1) / n * perf["empirical_se"] ** 2,
                                                    rel=1e-12)
    assert got["rmse"][2] is None and got["rmse_mcse"][2] is None
