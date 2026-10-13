"""CT-803: every test cohort trains on a strict out-of-time window (decision D1)."""
from __future__ import annotations

import numpy as np
import pytest

from pipeline.cases.c03 import panel, windows

from .helpers import COHORT_IDS


def test_each_window_closes_its_five_year_marks_before_the_first_approval_of_its_cohort():
    assert [c.id for c in windows.COHORTS] == list(COHORT_IDS)
    assert [(c.first_fy, c.last_fy) for c in windows.COHORTS] == [(2006, 2007), (2008, 2010), (2011, 2014), (2015, 2017), (2018, 2020)]
    expected_last = {"fy2006-07": 2000, "fy2008-10": 2002, "fy2011-14": 2005, "fy2015-17": 2009, "fy2018-20": 2012}
    for c in windows.COHORTS:
        w = windows.training_window(c)
        assert w.first_fy == 1991 and w.last_fy == expected_last[c.id] == c.first_fy - 6
        assert w.cutoff == f"{c.first_fy - 1}-09-30"
        windows.check_window(c, w)
        last_approval = np.array([f"{w.last_fy}-09-30"], dtype="datetime64[D]")
        assert panel.horizon_end(last_approval)[0] <= np.datetime64(w.cutoff), "the 5-year horizon of the last approval closes by the cutoff"
        assert np.datetime64(f"{c.first_fy - 1}-10-01") > np.datetime64(w.cutoff)
        assert c.fiscal_years == tuple(range(c.first_fy, c.last_fy + 1))


def test_the_crisis_flag_follows_the_charge_offs_of_the_window(tables):
    loans = tables["loans"]
    flags = {c.id: windows.crisis_events(loans, windows.training_window(c)) for c in windows.COHORTS}
    assert flags["fy2006-07"] == 0 and flags["fy2008-10"] == 0, "a window closed before December 2007 holds no recession outcome"
    assert flags["fy2011-14"] > 0 and flags["fy2015-17"] > 0 and flags["fy2018-20"] > 0
    assert flags["fy2011-14"] <= flags["fy2015-17"] <= flags["fy2018-20"]


def test_adversarial_a_window_that_overlaps_its_cohort_is_refused():
    c = next(c for c in windows.COHORTS if c.id == "fy2008-10")
    ok = windows.training_window(c)
    windows.check_window(c, ok)
    one_too_long = windows.Window(ok.first_fy, ok.last_fy + 1, ok.cutoff)
    with pytest.raises(ValueError, match="5-year mark"):
        windows.check_window(c, one_too_long)
    late_cutoff = windows.Window(ok.first_fy, ok.last_fy, f"{c.first_fy}-03-31")
    with pytest.raises(ValueError, match="cutoff"):
        windows.check_window(c, late_cutoff)
