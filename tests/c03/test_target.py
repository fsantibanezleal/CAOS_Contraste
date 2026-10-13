"""CT-802 and CT-805: the 5-year charge-off target and the rule that a vintage's 5-year value exists only at its 5-year mark."""
from __future__ import annotations

import json

import numpy as np

from pipeline.cases.c03 import panel, windows

from .helpers import frame, mark_findings


def _loans(rows):
    return panel.prepare(frame(rows))[0]


CHG = {"status": "CHGOFF", "chargeoff_amount": 10_000.0}


def test_the_label_is_an_event_a_non_event_or_censored_by_the_observation_date():
    rows = [
        {**CHG, "chargeoff_date": "2013-05-20"},                      # 0: month 40
        {**CHG, "chargeoff_date": "2016-03-01"},                      # 1: month 62, after the horizon
        {"paid_date": "2011-02-01"},                                  # 2: paid in full in month 12
        {"status": "EXEMPT"},                                         # 3: still active
        {**CHG, "chargeoff_date": "2015-01-15"},                      # 4: on the horizon end
        {**CHG, "chargeoff_date": "2015-01-16"},                      # 5: the day after
    ]
    loans = _loans(rows)
    assert loans.horizon_end[0] == np.datetime64("2015-01-15")
    late = panel.label(loans, np.datetime64("2026-06-30"))
    assert late.tolist() == [1, 0, 0, 0, 1, 0]
    # observed at month 59 (2014-12-31): the horizon is not over
    early = panel.label(loans, np.datetime64("2014-12-31"))
    assert early.tolist() == [1, -1, -1, -1, -1, -1], "an open loan is censored, not performing"
    # observed on the horizon end: a loan with no charge-off by then is a non-event
    on_end = panel.label(loans, np.datetime64("2015-01-15"))
    assert on_end.tolist() == [1, 0, 0, 0, 1, 0]
    # a leap-day approval ends its horizon on the last day of February
    leap = _loans([{"approval_date": "2012-02-29"}])
    assert leap.horizon_end[0] == np.datetime64("2017-02-28")


def test_adversarial_a_label_read_beyond_the_observation_date_is_found():
    loans = _loans([{**CHG, "chargeoff_date": "2013-05-20"}, {"status": "EXEMPT"}])
    at_month_30 = panel.label(loans, np.datetime64("2012-07-15"))
    assert at_month_30.tolist() == [-1, -1], "a charge-off at month 40 is not seen at month 30"
    assert (at_month_30 != 1).all()
    at_month_47 = panel.label(loans, np.datetime64("2013-12-15"))
    assert at_month_47[1] == -1, "a loan open for 47 months is not a non-event"
    assert at_month_47[0] == 1


def test_the_five_year_mark_is_the_thirtieth_of_september_five_years_after_the_fiscal_year():
    assert windows.five_year_mark(2018) == "2023-09-30"
    assert windows.mark_observed(2020, "2026-06-30") and not windows.mark_observed(2021, "2026-06-30")
    assert windows.mark_observed(2019, "2024-09-30") and not windows.mark_observed(2019, "2024-09-29")


def test_a_vintage_before_its_five_year_mark_carries_no_observed_value(tables, fit_2008, cohort_2008):
    from pipeline.cases.c03 import variant

    for observed_at, observed_years in (("2014-06-30", [2008]), ("2015-06-30", [2008, 2009])):
        res = variant.bake_cohort(tables["loans"], cohort_2008, 42, observed_at=observed_at, fit=fit_2008)
        o = res.document["outputs"]
        assert mark_findings(o) == [], mark_findings(o)
        rows = {r["fiscal_year"]: r for r in o["vintage_summary"]["rows"]}
        assert [fy for fy, r in rows.items() if r["mark_observed"]] == observed_years
        for fy, r in rows.items():
            curve = next(c for c in o["vintage_curves"] if c["fiscal_year"] == fy)
            if r["mark_observed"]:
                assert r["observed_5y_pd"] is not None and r["reason"] is None and curve["observed_until_month"] >= 60
                assert curve["observed_cumulative_pd"][-1] is not None
            else:
                assert r["observed_5y_pd"] is None and r["gap"] is None and r["brier"] is None and r["auc"] is None
                assert r["reason"] and curve["reason"] and curve["observed_until_month"] < 60
                assert curve["observed_cumulative_pd"][-1] is None
                assert r["n_exempt_censored"] > 0, "the loans without an outcome are counted, not dropped"
            assert r["n"] == r["n_resolved"] + r["n_exempt_censored"]
        assert o["data_status"]["files_as_of"] == observed_at
        unobserved = [s for s in o["stability"]["rows"] if not rows[s["fiscal_year"]]["mark_observed"]]
        assert unobserved and all(s["observed_5y_pd"] is None for s in unobserved)
        assert o["calibration"]["rows"], "the deciles pool the vintages whose mark is observed"


def test_a_cohort_with_no_observed_mark_is_refused_not_filled(tables, fit_2008, cohort_2008):
    import pytest

    from pipeline.cases.c03 import variant

    with pytest.raises(ValueError, match="5-year mark"):
        variant.bake_cohort(tables["loans"], cohort_2008, 42, observed_at="2012-06-30", fit=fit_2008)


def test_adversarial_a_five_year_value_before_the_mark_is_found(tables, fit_2008, cohort_2008):
    from pipeline.cases.c03 import variant

    res = variant.bake_cohort(tables["loans"], cohort_2008, 42, observed_at="2014-06-30", fit=fit_2008)
    planted = json.loads(json.dumps(res.document["outputs"]))
    assert mark_findings(planted) == []
    planted["vintage_summary"]["rows"][-1]["observed_5y_pd"] = 0.2
    planted["stability"]["rows"][-1]["observed_5y_pd"] = 0.2
    found = mark_findings(planted)
    assert any("before its mark" in f for f in found) and any("stability" in f for f in found)
