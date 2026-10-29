"""BS-15 on C03 (method tiers plan, unit D15): the e-process of defaults against the predicted PD by age, per vintage, read at every
age step (12, 24, 36, 48, 60 months) instead of once at the 5-year mark. The builder is a pure function of the vintage curves and the
fixed-window rows of the document; the committed documents are checked as committed (no test bakes the real data, ADR-0074)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from pipeline.cases.c03 import sequential as sq

ROOT = Path(__file__).resolve().parents[2]
DERIVED = ROOT / "data" / "derived" / "C03"
MONTHS = [12, 24, 36, 48, 60]


def _curve(fy: int, n: int, pred: list[float], obs: list[float | None]) -> dict:
    until = 12 * sum(o is not None for o in obs)
    return {"fiscal_year": fy, "n": n, "gross_approval": 1.0, "months": MONTHS, "predicted_cumulative_pd": pred,
            "observed_cumulative_pd": obs, "observed_until_month": until, "reason": None if until >= 60 else "unobserved"}


PRED = [0.01, 0.03, 0.05, 0.065, 0.075]


def _scaled(f: float, n: int) -> list[float]:
    """The observed cumulative curve of a vintage whose true PD is f times the predicted one (counts are whole numbers)."""
    return [round(p * f * n) / n for p in PRED]


def test_interval_counts_are_whole_numbers_and_the_increments_of_the_curve():
    c = _curve(2006, 10_000, PRED, _scaled(2.0, 10_000))
    d, n, p = sq.interval_counts(c)
    assert d.tolist() == [200.0, 400.0, 400.0, 300.0, 200.0]
    assert n.tolist() == [10_000.0] * 5
    assert p == pytest.approx([0.01, 0.02, 0.02, 0.015, 0.01])


def test_unobserved_ages_have_no_obligors_and_contribute_nothing():
    c = _curve(2020, 5_000, PRED, [round(0.01 * 3 * 5000) / 5000, round(0.03 * 3 * 5000) / 5000, None, None, None])
    d, n, p = sq.interval_counts(c)
    assert n.tolist() == [5000.0, 5000.0, 0.0, 0.0, 0.0] and d[2:].sum() == 0


def test_an_underpredicted_vintage_is_rejected_at_the_first_age():
    b = sq.build([_curve(2006, 80_000, PRED, _scaled(3.0, 80_000))], [], "P1-scorecard")
    assert b["months"] == MONTHS
    assert b["average"]["rejection_month"] == 12 and b["product"]["rejection_month"] == 12
    assert b["vintages"][0]["rejection_month"] == 12
    assert b["average"]["log_e"][0] > math.log(20)


def test_a_vintage_on_its_prediction_is_not_rejected():
    b = sq.build([_curve(2012, 50_000, PRED, _scaled(1.0, 50_000))], [], "P1-scorecard")
    assert b["average"]["rejection_month"] is None and b["product"]["rejection_month"] is None
    assert b["average"]["anytime_p_value"] > 0.05


def test_an_overpredicted_vintage_is_never_rejected_in_the_upper_direction():
    b = sq.build([_curve(2012, 50_000, PRED, _scaled(0.4, 50_000))], [], "P1-scorecard")
    assert b["direction"] == "upper"
    assert b["average"]["rejection_month"] is None
    assert max(x for x in b["average"]["log_e"] if x is not None) < 0.0


def test_the_five_year_light_is_read_from_the_fixed_window_row_of_the_vintage():
    tests = [{"test_id": "pd.binomial", "model_id": "P1-scorecard", "segment": "fy2006", "light": "red"},
             {"test_id": "pd.binomial", "model_id": "P1-scorecard", "segment": "fy2007", "light": "green"},
             {"test_id": "pd.binomial", "model_id": "P4-lightgbm", "segment": "fy2006", "light": "green"}]
    b = sq.build([_curve(2006, 80_000, PRED, _scaled(3.0, 80_000)), _curve(2007, 80_000, PRED, _scaled(1.0, 80_000))], tests,
                 "P1-scorecard")
    assert [v["five_year_light"] for v in b["vintages"]] == ["red", "green"]
    assert b["vintages"][0]["months_before_the_mark"] == 48 and b["vintages"][1]["months_before_the_mark"] is None


def test_the_combination_by_average_is_an_e_process_whatever_the_dependence_and_is_the_headline():
    b = sq.build([_curve(2006, 80_000, PRED, _scaled(3.0, 80_000)), _curve(2007, 80_000, PRED, _scaled(1.0, 80_000))], [], "P1")
    assert b["headline"] == "average"
    # the average of two vintages' e-processes is the log of their mean; the product is the sum of their logs
    g0, g1 = b["vintages"][0]["log_e"][0], b["vintages"][1]["log_e"][0]
    assert b["average"]["log_e"][0] == pytest.approx(float(np.logaddexp(g0, g1)) - math.log(2), abs=1e-4)
    assert b["product"]["log_e"][0] == pytest.approx(g0 + g1, abs=1e-4)


def test_a_cohort_without_an_observed_age_is_refused():
    with pytest.raises(ValueError):
        sq.build([_curve(2020, 5_000, PRED, [None] * 5)], [], "P1")


# ---------------------------------------------------------------------------------------------------------------------
# the committed documents

COHORTS = ["fy2006-07", "fy2008-10", "fy2011-14", "fy2015-17", "fy2018-20"]


def _doc(c: str) -> dict:
    return json.loads((DERIVED / f"{c}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("c", COHORTS)
def test_every_committed_cohort_carries_the_block_and_it_is_the_build_of_its_own_curves(c):
    d = _doc(c)
    s = d["outputs"]["sequential"]
    champ = d["outputs"]["calibration"]["rung_id"]
    again = sq.build([x for x in d["outputs"]["vintage_curves"]], d["tests"], champ)
    assert again == {k: v for k, v in s.items() if k in again}
    assert s["months"] == MONTHS and s["alpha_level"] == 0.05 and s["threshold"] == 20.0
    assert s["engine"] == "riskvalidation.validation.sequential" and s["engine_version"] == "1.1.0"
    for t in ("reading", "limits"):
        assert set(s[t]) == {"en", "es"}


def test_the_level_gap_of_the_crisis_cohorts_is_seen_at_the_first_age_and_the_calm_cohorts_are_not_rejected():
    first = {c: _doc(c)["outputs"]["sequential"]["average"]["rejection_month"] for c in COHORTS}
    assert first["fy2006-07"] == 12 and first["fy2008-10"] == 12
    assert first["fy2011-14"] is None and first["fy2015-17"] is None
