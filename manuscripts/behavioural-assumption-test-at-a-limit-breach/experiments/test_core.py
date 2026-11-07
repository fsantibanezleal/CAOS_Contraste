"""Tests of the shared core of the experiments: the engine against the closed form, the statistics, the generators and their determinism.

    python -m pytest manuscripts/behavioural-assumption-test-at-a-limit-breach/experiments -q
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import core


def test_engine_matches_closed_form_on_a_known_history():
    theta = np.array([4.0, 4.0, 4.5, 4.5, 5.0])
    b = np.array([True, False, True, False, True])
    r = core.engine_test(theta, b)
    assert r.statistic == 2.0 == core.closed_form_count(theta, b)
    assert r.light.value == "red"
    assert r.extras["flagged_dates"] == [str(core.dates(5)[2]), str(core.dates(5)[4])]


def test_single_date_is_not_evaluated_and_held_parameter_is_green():
    r = core.engine_test(np.array([4.0, 4.0, 4.0]), np.array([True, True, True]))
    assert r.light.value == "green" and r.statistic == 0.0
    from riskvalidation.validation import irrbb
    one = irrbb.behavioural_change_at_breach(np.array([4.0]), core.dates(1), np.array([True]))
    assert one.light.value == "not_evaluated"


def test_the_test_depends_on_the_series_only_through_the_change_indicator():
    rng = np.random.default_rng(3)
    theta = np.round(rng.normal(3, 1, 10), 1)
    b = rng.random(10) < 0.5
    base = core.closed_form_count(theta, b)
    for f in (lambda x: 12.0 * x, lambda x: np.exp(x), lambda x: x ** 3 + 7.0):
        assert core.closed_form_count(f(theta), b) == base


def test_hypergeometric_false_flag_probability():
    assert core.p_coincidence_hypergeometric(11, 1, 1) == pytest.approx(1 / 11)
    assert core.p_coincidence_hypergeometric(4, 2, 3) == 1.0
    assert core.p_coincidence_hypergeometric(11, 0, 5) == 0.0
    assert core.p_coincidence_hypergeometric(5, 2, 2) == pytest.approx(1 - math.comb(3, 2) / math.comb(5, 2))


def test_wilson_interval_contains_the_rate_and_is_ordered():
    p, lo, hi = core.wilson(30, 100)
    assert lo < p < hi and 0 <= lo and hi <= 1
    assert core.wilson(0, 1000)[1] == 0.0 and core.wilson(0, 1000)[2] == pytest.approx(0.00383, abs=1e-4)


def test_auc_of_separated_and_tied_scores():
    assert core.auc(np.array([1, 2, 3]), np.array([4, 5, 6])) == 1.0
    assert core.auc(np.array([1, 1, 1]), np.array([1, 1])) == 0.5
    assert core.auc(np.array([4, 5, 6]), np.array([1, 2, 3])) == 0.0


def test_conformal_threshold_is_the_ceil_order_statistic():
    s = np.arange(1, 100, dtype=float)
    assert core.conformal_threshold(s, 0.1) == s[math.ceil(100 * 0.9) - 1]
    assert core.conformal_threshold(s[:5], 0.05) == float("inf")


def test_breach_chain_has_a_breach_after_the_first_date_and_is_deterministic():
    for seed in range(20):
        b = core.breach_chain(np.random.default_rng(seed), 12, 0.1)
        assert b[1:].any() and b.size == 12
    a = core.breach_chain(np.random.default_rng(5), 12, 0.25)
    assert np.array_equal(a, core.breach_chain(np.random.default_rng(5), 12, 0.25))


def test_plant_dates_picks_only_breach_dates_after_the_first_and_at_least_one():
    rng = np.random.default_rng(1)
    b = np.array([True, False, True, True, False, True])
    for _ in range(50):
        m = core.plant_dates(rng, b, 0.0)
        assert m.sum() == 1 and b[m].all() and not m[0]


def test_stated_history_pair_shares_the_innocent_changes():
    draws = core.stated_draws(np.random.default_rng(9), 12, 0.2)
    plant = np.zeros(12, dtype=bool)
    plant[5] = True
    a, b = core.stated_history(draws, None), core.stated_history(draws, plant)
    assert np.array_equal(a[:5], b[:5]) and b[5] != a[5]


def test_overlay_moves_the_weights_toward_the_longest_tranche_only_from_the_planted_date():
    w = np.full((6, core.J), 1.0 / core.J)
    plant = np.zeros(6, dtype=bool)
    plant[3] = True
    out = core.overlay_weights(w, plant, 0.2)
    assert np.allclose(out[:3], w[:3]) and np.allclose(out.sum(axis=1), 1.0)
    assert out[3, -1] > w[3, -1] and np.allclose(out[3], out[5])
    full = core.overlay_weights(w, plant, 1.0)
    assert np.allclose(full[3:] @ core.MATS / 2.0, core.WAM_MAX)


def test_the_decision_rules_follow_their_definitions():
    sc = {"engine_count": 1.0, "any_change": 3.0, "fisher_p": 0.04, "mannwhitney_p": 0.06, "welch_p": 0.5, "stability": 0.3, "peak": 1.2, "peak_lookahead": 1.5}
    assert core.flag(sc, "engine") and core.flag(sc, "any_change") and core.flag(sc, "fisher") and not core.flag(sc, "mannwhitney")
    assert core.flag(sc, "stability") and core.flag(sc, "tolerance", 1.0) and not core.flag(sc, "tolerance", 1.2)
    assert core.flag(sc, "tolerance_lookahead", 1.4)


def test_scores_agree_with_the_engine_count():
    rng = np.random.default_rng(11)
    for _ in range(200):
        t = int(rng.integers(3, 15))
        theta = np.round(rng.normal(3, 1, t), 1)
        b = rng.random(t) < 0.4
        assert core.scores(theta, b)["engine_count"] == core.closed_form_count(theta, b)
