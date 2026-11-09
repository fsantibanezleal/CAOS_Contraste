"""Tests of the shared code of the experiments (``core.py``) on cases whose answer is known without the engine.

    python -m pytest manuscripts/reverse-liquidity-stress-with-a-refusal-rule/experiments/test_core.py
"""
from __future__ import annotations

import math
import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import core  # noqa: E402
from riskvalidation.liquidity.scenarios import Scenario, ScenarioSegment  # noqa: E402


def one_segment(opening: float, q: float, cbc: float, h: int) -> core.Bank:
    rates = np.full((1, h), q)
    scn = Scenario("idiosyncratic", "protracted", h, (ScenarioSegment("s", "synthetic", opening, rates[0]),))
    c = np.full(h, cbc)
    return core.Bank(scn, np.array([opening]), rates, c, c, True, False, False, h)


def test_the_golden_value_of_the_engine_is_the_closed_form_and_the_oracle() -> None:
    b = one_segment(1000.0, 0.01, 100.0, 125)
    closed = (1.0 - (1.0 - 100.0 / 1000.0) ** (1.0 / 5.0)) / 0.01
    o = core.oracle(b.opening, b.rates, b.cbc_eff, 5)
    a = core.solve_engine(b, 5)
    assert o.status == "solved" and a.answered
    assert abs(o.m0 - closed) < 1e-9
    assert a.m == pytest.approx(2.085164, abs=1e-12)
    assert 0.0 <= a.m - o.m0 <= 1e-6 + 1e-9


def test_the_three_refusals_are_told_apart() -> None:
    b = one_segment(1000.0, 0.01, 100.0, 125)
    assert core.oracle(b.opening, b.rates, b.cbc_eff, 125).reason == "horizon"
    assert core.oracle(b.opening, b.rates, b.cbc_eff, 100).reason == "base"
    big = one_segment(1000.0, 0.01, 5000.0, 125)
    assert core.oracle(big.opening, big.rates, big.cbc_eff, 5).reason == "unreachable"
    for bank, t, reason in ((b, 125, "horizon"), (b, 100, "base"), (big, 5, "unreachable")):
        a = core.solve_engine(bank, t)
        assert not a.answered and a.reason == reason


def test_the_threshold_property_holds_at_the_engine_multiplier_and_fails_when_rounded_down() -> None:
    b = one_segment(1000.0, 0.01, 100.0, 125)
    m = core.solve_engine(b, 5).m
    assert core.threshold_ok(b.opening, b.rates, b.cbc_eff, 5, m)
    assert not core.threshold_ok(b.opening, b.rates, b.cbc_eff, 5, m - 2e-6)


def test_the_cap_keeps_every_rate_at_most_one() -> None:
    b = one_segment(1000.0, 0.5, 100.0, 10)
    assert core.cap_of(b.rates) == pytest.approx(2.0)
    q = np.minimum(core.cap_of(b.rates) * b.rates, 1.0)
    assert q.max() == 1.0


def test_the_corpus_is_reproducible_and_covers_the_three_refusals() -> None:
    a = core.corpus(7, 60)
    b = core.corpus(7, 60)
    assert all(np.array_equal(x.rates, y.rates) and np.array_equal(x.cbc_eff, y.cbc_eff) for x, y in zip(a, b))
    reasons = {core.oracle(x.opening, x.rates, x.cbc_eff, t).reason for x in core.corpus(11, 400) for t in core.TARGETS}
    assert {"horizon", "base", "unreachable", None} <= reasons


def test_the_wilson_interval_contains_the_proportion_and_is_proper_at_zero() -> None:
    p, lo, hi = core.wilson(30, 100)
    assert lo < p < hi
    p0, lo0, hi0 = core.wilson(0, 500)
    assert p0 == 0.0 and lo0 < 1e-12 and 0.0 < hi0 < 0.01
    assert math.isnan(core.wilson(0, 0)[0])
