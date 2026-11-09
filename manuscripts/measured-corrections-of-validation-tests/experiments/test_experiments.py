"""Tests of the experiment scripts of this manuscript: the vectorised p-values against the engine and scipy, the exact sizes
against their guarantees, the seed reproducibility of one replication, and the invariants of the committed results.

Run from the repository root: python -m pytest manuscripts/measured-corrections-of-validation-tests/experiments -q
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from scipy import stats  # noqa: E402

import exact_theory  # noqa: E402
import exp_coverage  # noqa: E402
import exp_shift  # noqa: E402
import exp_situation  # noqa: E402
import exp_situation_indep  # noqa: E402

RESULTS = common.RESULTS


def test_min_likelihood_p_equals_scipy_binomtest_at_every_count():
    m = 60
    pmf = stats.binom.pmf(np.arange(m + 1), m, 0.9)
    mine = exp_coverage.min_likelihood_p(pmf)
    ref = np.array([stats.binomtest(c, m, 0.9).pvalue for c in range(m + 1)])
    assert np.max(np.abs(mine - ref)) < 1e-9


def test_vectorised_beta_binomial_p_equals_the_engine_function():
    from riskvalidation.ml import conformal

    n, m = 300, 500
    t = exp_coverage.tables(n, m)
    zeros, blank = np.zeros(m, dtype=int), np.zeros(m, dtype=bool)
    for c in (0, 100, 380, 430, 450, 470, 500):
        covered = np.arange(m) < c
        res = conformal.conformal_coverage(np.column_stack([covered, blank]), zeros, 0.1, n_cal=n)
        assert res.p_value == pytest.approx(t["bb"][c], abs=1e-9)
        assert res.p_value_binomial == pytest.approx(t["bin"][c], abs=1e-9)


@pytest.mark.parametrize("n,m", [(200, 20), (200, 800), (1000, 1000), (1000, 4000)])
def test_the_beta_binomial_test_has_exact_size_at_most_its_level_and_the_binomial_one_exceeds_it(n, m):
    t = exp_coverage.tables(n, m)
    exact = exp_coverage.exact_sizes(t, exp_coverage.oracle_threshold(t["bin"], t["law"]))
    assert exact["bb"] <= common.LEVEL + 1e-12
    assert exact["bin_oracle"] <= common.LEVEL + 1e-12
    if m >= n:
        assert exact["bin"] > 2 * common.LEVEL


def test_the_variance_of_the_count_is_the_binomial_one_times_the_closed_form_ratio():
    assert exact_theory.variance_ratio()["max_abs_error"] < 1e-9


def test_the_granularity_of_a_permutation_p_value():
    rows = {r["draws"]: r for r in exact_theory.granularity()}
    assert rows[19]["can_reject_below_0.05"] is False
    assert rows[39]["max_null_draws_above_observed"] == 0
    assert rows[99]["max_null_draws_above_observed"] == 3
    assert rows[199]["max_null_draws_above_observed"] == 8


def test_one_shift_replication_is_reproducible_and_reads_the_first_draws_of_the_longest_reference():
    a = exp_shift.one_replication((125, 2.0, 0))
    b = exp_shift.one_replication((125, 2.0, 0))
    assert a == b
    assert not a["skipped"]
    assert a["p"]["199"] == pytest.approx(a["p"]["199"])
    for r, p in a["p"].items():
        assert 1.0 / (int(r) + 1) <= p <= 1.0


def test_one_situation_replication_returns_counts_that_are_ordered():
    n_c, n_cases, n_sig, n_bonf = exp_situation.one_replication((400, 0.4, 0))
    assert n_c > 0 and n_sig <= n_cases <= n_c and n_bonf <= n_sig


def test_the_summary_of_situation_counts_applies_the_cuts_inclusively():
    rows = [[100, 30, 20, 5], [100, 30, 19, 0], [100, 30, 4, 0], [100, 30, 40, 9]]
    s = exp_situation.summarise(rows)
    assert s["rules"]["cut_0.2"]["rate"] == 0.5
    assert s["rules"]["bonferroni_any"]["rate"] == 0.5


@pytest.mark.skipif(not (RESULTS / "coverage.json").exists(), reason="results not produced yet")
def test_committed_coverage_results_agree_with_the_engine_and_with_the_exact_sizes():
    d = json.loads((RESULTS / "coverage.json").read_text(encoding="utf-8"))
    assert all(c["engine_mismatches"] == 0 for c in d["cells"])
    for c in d["cells"]:
        if c["b"] != 1.0:
            continue
        for name in ("bb", "bin"):
            r = c["rates"][name]
            assert abs(r["rate"] - c["exact"][name]) < 5 * max(r["se"], 1e-3)


@pytest.mark.skipif(not (RESULTS / "shift.json").exists(), reason="results not produced yet")
def test_committed_shift_results_are_complete():
    d = json.loads((RESULTS / "shift.json").read_text(encoding="utf-8"))
    for c in d["cells"]:
        assert c["n"] + c["skipped"] == d["meta"]["reps"]
        assert c["undefined_draws"] == 0 or c["undefined_draws"] >= 0
        for rule in c["rules"].values():
            assert 0.0 <= rule["rate"] <= 1.0 and math.isfinite(rule["se"])


def test_the_independent_attribute_plant_has_the_engine_suite_structure_and_a_reproducible_replication():
    rng = np.random.default_rng(1)
    x, group, decision = exp_situation_indep.draw(4000, 0.0, rng)
    assert x.shape == (4000, 2) and x.min() >= 0.0 and x.max() <= 10.0
    assert abs(group.mean() - 0.4) < 0.03 and abs((decision == 0).mean() - 0.25) < 0.03
    rng = np.random.default_rng(1)
    _, g2, d2 = exp_situation_indep.draw(4000, 0.4, rng)
    assert abs((d2[g2 == 1] == 0).mean() - 0.65) < 0.04
    a = exp_situation_indep.one_replication((400, 0.4, 0))
    assert a == exp_situation_indep.one_replication((400, 0.4, 0))
    assert a[0] > 0 and a[2] <= a[1] <= a[0] and a[3] <= a[2]


@pytest.mark.skipif(not (RESULTS / "situation_indep.json").exists(), reason="results not produced yet")
def test_committed_independent_design_results_are_complete_and_reproduce_the_engine_record():
    d = json.loads((RESULTS / "situation_indep.json").read_text(encoding="utf-8"))
    for c in d["cells"]:
        assert c["reps"] == (exp_situation_indep.REPS_NULL if c["bias"] == 0.0 else exp_situation_indep.REPS_BIAS)
    null = next(c for c in d["cells"] if c["n"] == 400 and c["bias"] == 0.0)
    # the engine's size-and-power suite records 0.0395 (se 0.0031) for the cut 0.20 and 0.194 for the cut 0.10 at 400 applicants
    assert abs(null["rules"]["cut_0.2"]["rate"] - 0.0395) < 3 * 0.0051
    assert abs(null["rules"]["cut_0.1"]["rate"] - 0.194) < 3 * 0.011
