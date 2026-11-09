"""Tests of what the review fixes added to the e-process manuscript: the exact rejection probability of the rate monitor,
the product's own PD tests as comparators on the same default histories, the equal-size chi-square rule, the matched
single alternative at each severity, and the contract of the new outputs.

    python -m pytest manuscripts/e-process-sequential-monitors/experiments/test_review_fixes.py
"""
from __future__ import annotations

import itertools
import json
import math
import pathlib
import sys

import numpy as np
import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as cm  # noqa: E402


def load(name: str) -> dict:
    path = HERE / name
    assert path.exists(), f"{name} has not been produced: run the experiment script"
    return json.loads(path.read_text(encoding="utf-8"))


# --- exact rejection probability ----------------------------------------------------------------------------------

@pytest.mark.parametrize("kw", [{}, {"direction": "upper"}, {"multipliers": [3.0]}])
def test_exact_rejection_probability_equals_the_enumeration_of_the_engine_monitor(kw):
    p, t, cross = 0.2, 12, math.log(3.0)
    h = np.array(list(itertools.product([0, 1], repeat=t)), dtype=bool)
    pr = p ** h.sum(axis=1) * (1 - p) ** (t - h.sum(axis=1))
    ever = (cm.engine_paths(h, p, **kw) >= cross).any(axis=1)
    got = cm.exact_rejection_probability(p, t, cm.engine_multipliers(p, **kw), cross)[-1]
    assert got == pytest.approx(float(pr @ ever), abs=1e-12)


def test_exact_rejection_probability_is_nondecreasing_and_under_the_size():
    r = cm.exact_rejection_probability(0.01, 400, cm.engine_multipliers(0.01))
    assert all(b >= a for a, b in zip(r, r[1:]))
    assert 0.0 < r[249] < r[-1] < cm.LEVEL


def test_exact_rejection_probability_refuses_an_alternative_at_one():
    with pytest.raises(ValueError):
        cm.exact_rejection_probability(0.5, 5, [2.0])


# --- the product's PD tests as comparators ------------------------------------------------------------------------

def pdc():
    import exp_pd_comparators as m

    return m


def test_pd_pvalue_table_equals_the_engine_function():
    from riskvalidation.validation import calibration as c

    m = pdc()
    tab = m.pvalue_table("vasicek", 2000, 0.02, 0.12, 80)
    for d in (0, 5, 40, 80):
        assert tab[d] == pytest.approx(c.pd_binomial_vasicek(2000, d, 0.02, 0.12).p_value, rel=1e-12)
    tab = m.pvalue_table("binomial", 2000, 0.02, 0.0, 80)
    assert tab[33] == pytest.approx(c.pd_binomial(2000, 33, 0.02).p_value, rel=1e-12)
    tab = m.pvalue_table("jeffreys", 2000, 0.02, 0.0, 80)
    assert tab[33] == pytest.approx(c.pd_jeffreys(2000, 33, 0.02).p_value, rel=1e-12)


def test_bonferroni_reading_every_year_and_once():
    m = pdc()
    p = np.ones((3, 4, 2))
    p[0, 2, 1] = 0.0004   # history 0: grade 1 at year 3 (index 2) is below 0.05 / 8
    p[1, 3, 0] = 0.009    # history 1: grade 0 at the last year is below 0.05 / 2 but not below 0.05 / 8
    every, once = m.read_rules(p)
    assert list(every) == [3.0, np.inf, np.inf]
    assert list(once) == [False, True, False]


def test_equal_size_chi_square_has_at_most_the_stated_size_on_its_calibration_histories():
    m = pdc()
    stat = np.abs(np.random.default_rng(0).standard_normal((4000, 10))).cumsum(axis=1)
    cv = cm.constant_critical_value(stat, 0.05)
    assert np.mean(stat.max(axis=1) > cv) <= 0.05


def test_same_histories_reproduce_the_committed_chi_square_of_the_correlation_experiment():
    """The comparator regenerates the histories of exp_pd_correlation.py, so its chi-square readings equal the committed ones."""
    m = pdc()
    committed = load("results_pd_correlation.json")
    row = next(r for r in committed["rows"] if r["rho"] == 0.03)
    got = m.chi2_readings(m.draw_correlation(0.03, 1, 2000, committed["meta"]["seed"]))
    assert got["every_year"] == pytest.approx(row["chi2_every_year"]["ever"], abs=1e-12)
    assert got["year_10"] == pytest.approx(row["chi2_one_shot_year_10"]["ever"], abs=1e-12)


# --- outputs ------------------------------------------------------------------------------------------------------

def test_matched_single_alternative_output_has_every_severity():
    out = load("results_matched.json")
    assert set(out["factors"]) == {"x1.5", "x2", "x3", "x4", "x6", "x10"}
    for f, r in out["factors"].items():
        assert r["multiplier"] == float(f[1:]) and r["n"] >= 2000
        assert r["ever"] >= r["by"]


def test_theory_has_the_exact_spending_and_the_exact_one_shot_sizes():
    th = load("results_theory.json")
    ex = th["exact_spending"]
    assert 0.0 < ex["rate_two_sided"]["by_250"] < ex["rate_two_sided"]["by_1000"] < cm.LEVEL
    assert ex["single_3"]["by_250"] > ex["rate_two_sided"]["by_250"]
    sm = th["size_matched_power"]
    assert sm["e_process_size_by_window"] == pytest.approx(ex["rate_two_sided"]["by_250"], abs=1e-15)
    assert "single_3_np_power_at_3" in sm
    one = th["one_shot_sizes"]
    assert one["kupiec"] == pytest.approx(sm["kupiec_size"], abs=1e-15)
    assert 0.1 < one["traffic_light"] < 0.12
    pr = th["product_counterexample"]["hits_rate_times_cluster"]
    assert 0.0 < pr["reject_probability_by_day_10"] <= 1.0


def test_pd_comparators_output_contract():
    out = load("results_pd_comparators.json")
    rules = {"binomial", "jeffreys", "vasicek_assumed", "vasicek_true"}
    for r in out["correlation"]:
        for k in rules:
            assert {"every_year", "once"} <= set(r[k])
        lo, hi = r["vasicek_true"]["every_year"]["ever_ci"]
        assert lo <= r["vasicek_true"]["every_year"]["ever"] <= hi
    eq = out["equal_size_chi2"]
    assert eq["critical_value_5pct"] > 0 and eq["matched_size"] > 0
    assert set(eq["scenarios"]) >= {"all-x1", "all-x1.05", "all-x1.1", "all-x1.25", "grade5-x1.3"}
    # the Vasicek test at the true correlation keeps a size of at most 5 % in every correlation row
    for r in out["correlation"]:
        assert r["vasicek_true"]["every_year"]["ever"] <= 0.05 + 3 * math.sqrt(0.05 * 0.95 / r["reps"])
        assert r["vasicek_true"]["once"]["ever"] <= 0.05 + 3 * math.sqrt(0.05 * 0.95 / r["reps"])
