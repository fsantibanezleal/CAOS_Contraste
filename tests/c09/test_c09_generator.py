"""CT-1002, CT-1004: the known CCF is a closed form of the parameters and the generator reproduces it; the six levels."""
from __future__ import annotations

import math

import numpy as np
from pipeline.cases.c09 import estimators, generator, params


def test_the_fixed_horizon_estimate_reproduces_the_known_ccf_at_a_large_sample() -> None:
    pop = generator.draw_population(7, 250_000)
    for level in range(6):
        d = generator.realise(pop, level)
        obs = estimators.observe(d, "fixed-horizon")
        est = estimators.aggregate(obs, "none", "mean")
        truth = params.known_ccf(level)
        assert est.n_facilities > 5000, (level, est.n_facilities)
        assert abs(est.value - truth) < params.TOLERANCE, (level, est.value, truth)
    assert math.isclose(params.known_ccf(0), params.PARAMS["ccf_anchor"], abs_tol=1e-9)


def test_the_known_ccf_is_the_closed_form_of_the_parameters() -> None:
    p = params.PARAMS
    w = params.defined_tier_weights()
    assert math.isclose(sum(w), 1.0, abs_tol=1e-12)
    for level in range(6):
        s = params.horizon_weight(level, 12)
        by_hand = sum(wt * (1.0 - (1.0 + p["draw_rate"] * rho * s / p["frailty_shape"]) ** (-p["frailty_shape"]))
                      for wt, rho in zip(w, p["tier_rate_multiplier"], strict=True))
        assert math.isclose(params.known_ccf(level), by_hand, rel_tol=1e-12)


def last_six_share(d: generator.Defaulters) -> float:
    i = d.interior
    total = d.window[i, 12] - d.window[i, 0]
    late = d.window[i, 12] - d.window[i, 6]
    return float(np.median(late / np.maximum(total, 1e-9)))


def test_the_six_levels_are_ordered_and_share_their_facilities() -> None:
    lv = params.LEVELS
    assert [x["level"] for x in lv] == [0, 1, 2, 3, 4, 5]
    assert lv[0]["factor"] == 1.0 and lv[0]["window"] == 0
    assert all(b["factor"] >= a["factor"] for a, b in zip(lv, lv[1:], strict=False))
    truths = [params.known_ccf(x["level"]) for x in lv]
    assert all(b > a for a, b in zip(truths, truths[1:], strict=False)), truths
    params.validate_levels(lv)
    pop = generator.draw_population(5, 8000)
    d0, d5 = generator.realise(pop, 0), generator.realise(pop, 5)
    assert np.array_equal(d0.limit, d5.limit) and np.array_equal(d0.tier, d5.tier)
    assert np.array_equal(d0.default_month, d5.default_month)
    assert np.array_equal(d0.drawn[:, 0], d5.drawn[:, 0])             # the same balance twelve months before default
    assert d5.ead.mean() > d0.ead.mean()                              # the stronger level draws more
    assert last_six_share(d5) > last_six_share(d0)                    # and more of it falls in the last six months


def test_the_generator_is_a_pure_function_of_its_seed_and_level() -> None:
    a, b, c = generator.generate(3, 2, 6000), generator.generate(3, 2, 6000), generator.generate(4, 2, 6000)
    assert np.array_equal(a.drawn, b.drawn) and np.array_equal(a.ead, b.ead)
    assert a.drawn.shape != c.drawn.shape or not np.array_equal(a.drawn, c.drawn)


def test_the_generator_floors_the_ead_at_zero_rarely() -> None:
    d = generator.generate(9, 5, 200_000)
    assert d.n_floored / d.ead.size < 0.002
    assert (d.ead >= 0).all()
