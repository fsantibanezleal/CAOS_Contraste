"""Unit tests of ``common.py``: the comparators equal the engine's own tests where the engine has them, the e-processes
written in this folder have expectation one under the null by exact enumeration (the property that makes them
e-processes), and the summaries behave on the edge cases (a series that never rejects, an empty rejection set).

    python -m pytest manuscripts/e-process-sequential-monitors/experiments/test_common.py
"""
from __future__ import annotations

import itertools
import math
import pathlib
import sys

import numpy as np
import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as cm  # noqa: E402


def enumerate_hits(t: int) -> np.ndarray:
    return np.array(list(itertools.product([0, 1], repeat=t)), dtype=bool)


def null_probs(h: np.ndarray, p: float) -> np.ndarray:
    k = h.sum(axis=1)
    return p ** k * (1 - p) ** (h.shape[1] - k)


@pytest.mark.parametrize("p", [0.1, 0.3])
def test_wwz_e_process_has_mean_one_under_the_null_at_every_time(p):
    h = enumerate_hits(11)
    paths = np.exp(cm.wwz_log_e(h, p))
    np.testing.assert_allclose(null_probs(h, p) @ paths, np.ones(h.shape[1]), rtol=0, atol=1e-10)


@pytest.mark.parametrize("p", [0.1, 0.3])
def test_beta_mixture_has_mean_one_under_the_null_at_every_time(p):
    h = enumerate_hits(11)
    paths = np.exp(cm.beta_mixture_log_e(h, p))
    np.testing.assert_allclose(null_probs(h, p) @ paths, np.ones(h.shape[1]), rtol=0, atol=1e-10)


def test_wwz_first_bet_is_zero_and_the_cap_binds():
    # with every day a hit the estimated bet is p / (1 - p): 1/9 at p = 0.1 and above the cap of 1/2 at p = 0.5
    h = np.ones((1, 12), dtype=bool)
    log_e = cm.wwz_log_e(h, 0.1)[0]
    assert log_e[0] == 0.0
    assert log_e[2] - log_e[1] == pytest.approx(math.log(1 - 1 / 9 + (1 / 9) / 0.1))
    capped = cm.wwz_log_e(h, 0.5)[0]
    assert capped[2] - capped[1] == pytest.approx(math.log(0.5 + 0.5 / 0.5))


def test_wwz_matches_the_closed_form_of_their_appendix():
    p = 0.2
    rng = np.random.default_rng(3)
    h = rng.random((1, 40)) < 0.35
    n = h.shape[1]
    x = h[0].astype(float)
    lam = np.zeros(n)
    for t in range(2, n + 1):
        k = t - 1 - x[: t - 1].sum()  # days without a hit among the first t - 1
        level = 1 - p  # their p is the VaR level, the code's p the exceedance probability
        raw = (1 - level) * ((t - 1) * level - k) / ((t - 1) * level**2 + (1 - 2 * level) * k)
        lam[t - 1] = min(max(raw, 0.0), 0.5)
    expected = np.cumsum(np.log(1 - lam + lam * x / p))
    np.testing.assert_allclose(cm.wwz_log_e(h, p)[0], expected, rtol=0, atol=1e-10)


def test_kupiec_statistic_equals_the_engine():
    from riskvalidation.validation.market import kupiec_pof

    rng = np.random.default_rng(5)
    for t, p in ((250, 0.01), (500, 0.025), (120, 0.05)):
        h = rng.random(t) < p * 2
        res = kupiec_pof(h, p)
        mine = cm.kupiec_lr(np.array([float(h.sum())]), np.array([float(t)]), p)[0]
        assert mine == pytest.approx(res.statistic, rel=1e-12)


def test_traffic_light_uses_the_engines_zone_and_the_first_full_window():
    h = np.zeros((1, 300), dtype=bool)
    h[0, :5] = True
    days, k_min = cm.traffic_light_days(h)
    assert k_min == 5 and days[0] == 250
    days0, _ = cm.traffic_light_days(np.zeros((1, 300), dtype=bool))
    assert math.isinf(days0[0])


def test_independence_test_flags_a_chain_of_hits():
    h = np.zeros((1, 300), dtype=bool)
    h[0, 100:110] = True
    h[0, 200:210] = True
    assert cm.independence_reject(h, 250).any()


def test_sidak_level_is_the_inverse_of_the_family_size():
    for looks in (1, 10, 951):
        assert 1 - (1 - cm.sidak_level(looks)) ** looks == pytest.approx(cm.LEVEL, rel=1e-12)


def test_cusum_is_reflected_at_zero_and_grows_on_hits():
    h = np.zeros((1, 50), dtype=bool)
    h[0, 10:14] = True
    s = cm.cusum_paths(h, 0.01, 3.0)[0]
    assert s.min() == 0.0 and s[13] > s[9]


def test_critical_values_bound_the_calibration_size():
    h = cm.draw_hits(7, 1, 600, t=300)
    lr_max, cs_max = cm.max_statistics(h, cm.ALPHA)
    cv = cm.critical_values(lr_max, cs_max)
    assert np.mean(lr_max > cv["kupiec_cumulative"]) <= cm.LEVEL
    assert np.mean(cs_max > cv["cusum_m3"]) <= cm.LEVEL


def test_summarise_handles_a_method_that_never_rejects():
    rng = np.random.default_rng(0)
    out = cm.summarise(np.full(200, np.inf), 250, rng)
    assert out["ever"] == 0.0 and out["median_day"] is None and out["median_day_among_detected"] is None
    assert out["ever_ci"][0] == 0.0


def test_wilson_interval_contains_the_proportion_and_stays_in_the_unit_interval():
    for k, n in ((0, 100), (7, 100), (100, 100)):
        lo, hi = cm.wilson(k, n)
        assert 0.0 <= lo <= k / n <= hi <= 1.0


def test_draw_hits_is_deterministic_per_seed_and_scenario():
    a = cm.draw_hits(11, 3, 5, t=60)
    b = cm.draw_hits(11, 3, 5, t=60)
    c = cm.draw_hits(11, 4, 5, t=60)
    assert (a == b).all() and not (a == c).all()


def test_engine_rate_monitor_matches_the_closed_form_one_point_alternative():
    h = cm.draw_hits(2, 9, 3, t=80, rate_factor=3.0)
    got = cm.engine_paths(h, 0.01, multipliers=[3.0])
    c = np.cumsum(h, axis=1)
    t = np.arange(1, 81)[None, :]
    expected = c * math.log(3.0) + (t - c) * math.log((1 - 0.03) / (1 - 0.01))
    np.testing.assert_allclose(got, expected, rtol=0, atol=1e-10)
