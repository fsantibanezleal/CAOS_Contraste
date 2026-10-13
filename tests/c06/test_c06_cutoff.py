"""CT-504 and CT-505: no look-ahead, and the censoring of open loans."""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd
import pytest

from pipeline.cases.c06 import ladder, macro, panel
from pipeline.cases.c06.panel import EXIT_DEFAULT, EXIT_MATURED, EXIT_OPEN, EXIT_PAID
from pipeline.io.sba import FedTables
from pipeline.cases.c06.run import run_date

R = np.datetime64("2010-12-31")


def _frame(rows):
    cols = ["asof_date", "approval_date", "gross_approval", "guaranteed_approval", "interest_rate_pct", "term_months", "naics",
            "status", "paid_date", "chargeoff_date", "chargeoff_amount", "revolver"]
    d = pd.DataFrame(rows, columns=cols)
    for c in ("asof_date", "approval_date", "paid_date", "chargeoff_date"):
        d[c] = pd.to_datetime(d[c])
    d["naics"] = d["naics"].astype("string")
    d["status"] = d["status"].astype("string")
    return d


def _loan(approval, term, status, paid=None, chargeoff=None, amount=100_000.0, coa=None):
    return ["2026-06-30", approval, amount, 80_000.0, 6.0, float(term), "722511", status, paid, chargeoff, coa, False]


def _perturb(loans, r):
    """Everything after ``r`` changed: the exits after it, the approvals after it, the charge-off amounts."""
    rng = np.random.default_rng(7)
    after = (loans.exit_date > r) & ~np.isnat(loans.exit_date)
    flip = after & (rng.random(loans.n) < 0.5)
    kind = np.where(flip, np.where(loans.exit_kind == EXIT_PAID, EXIT_DEFAULT, EXIT_PAID), loans.exit_kind)
    date = np.where(after, loans.exit_date + np.timedelta64(333, "D"), loans.exit_date)
    late = loans.approval > r
    amount = np.where(late, loans.amount * 7.0, loans.amount)
    term = np.where(late, loans.term // 2 + 1, loans.term)
    coa = np.where(after, 12345.0, loans.chargeoff_amount)
    return dataclasses.replace(loans, exit_kind=kind.astype(np.int64), exit_date=date, amount=amount, term=term, chargeoff_amount=coa)


def _perturb_fed(fed, r):
    h = fed.history.copy()
    jump = pd.Timestamp(macro.FED_JUMPOFF)
    later = (h["date"] > pd.Timestamp(r)) & (h["date"] != jump)
    h.loc[later, ["real_gdp_growth", "unemployment_rate", "prime_rate"]] = [-9.0, 19.0, 0.5]
    return FedTables(history=h, scenarios=fed.scenarios, files=fed.files)


def test_a_model_for_a_date_ignores_everything_after_it(tables):
    loans, fed = tables["loans"], tables["fed"]
    base = run_date(loans, fed, R, min_quarter_at_risk=60)
    moved = run_date(_perturb(loans, R), _perturb_fed(fed, R), R, min_quarter_at_risk=60)
    assert base.a == moved.a and np.array_equal(base.idx, moved.idx)
    assert np.array_equal(base.ladder.dth.params, moved.ladder.dth.params)
    assert np.array_equal(base.ladder.cox.params, moved.ladder.cox.params)
    assert np.array_equal(base.ladder.km.survival.value, moved.ladder.km.survival.value)
    assert np.array_equal(base.ecl12, moved.ecl12) and np.array_equal(base.ecl_life, moved.ecl_life)
    assert np.array_equal(base.stage, moved.stage)
    assert base.lgd_segments == moved.lgd_segments
    # the control: the same perturbation one year later does change a later model (the check can fail)
    later = np.datetime64("2011-12-31")
    a = run_date(loans, fed, later, min_quarter_at_risk=60)
    b = run_date(_perturb(loans, R), _perturb_fed(fed, R), later, min_quarter_at_risk=60)
    assert not np.array_equal(a.ladder.dth.params, b.ladder.dth.params)


def test_the_book_of_a_date_holds_only_loans_open_at_it(tables):
    loans = tables["loans"]
    obs = panel.observe(loans, R)
    book = obs.in_book
    assert (loans.approval[book] <= R).all()
    exits = loans.exit_date[book]
    assert (np.isnat(exits) | (exits > R)).all(), "a loan that exited on or before the date is not in its book"
    assert (loans.term[book] > obs.age_at_reporting[book]).all(), "a loan past its maturity is not in the book"
    assert not obs.selected[loans.approval > R].any()


def test_open_loans_are_censored_not_performing_to_term():
    rows = [
        _loan("2005-01-15", 120, "EXEMPT"),                                   # open at the date, ten-year term
        _loan("2002-03-10", 60, "EXEMPT"),                                    # past its maturity at the date
        _loan("2006-05-01", 84, "P I F", paid="2007-02-01"),                  # repaid before the date
        _loan("2006-05-01", 84, "CHGOFF", chargeoff="2008-06-01", coa=50_000.0),  # defaulted before the date
        _loan("2007-02-01", 84, "CHGOFF", chargeoff="2009-11-01", coa=40_000.0),  # defaults AFTER the date
    ]
    loans, counts = panel.prepare(_frame(rows))
    obs = panel.observe(loans, np.datetime64("2008-12-31"))
    assert list(obs.end_kind) == [EXIT_OPEN, EXIT_MATURED, EXIT_PAID, EXIT_DEFAULT, EXIT_OPEN]
    assert list(obs.event) == [False, False, False, True, False]
    assert list(obs.in_book) == [True, False, False, False, True]
    assert obs.age_months[0] == 47 and obs.age_months[1] == 60   # censored at the date, and at its maturity
    cells = ladder.build_cells(loans, obs)
    # the open loan of 47 months adds 15 full quarters and two thirds of one: not 40 quarters of a ten-year term
    only = panel.observe(loans, np.datetime64("2008-12-31"))
    sel = np.zeros(loans.n, dtype=bool)
    sel[0] = True
    one = dataclasses.replace(only, selected=sel)
    c = ladder.build_cells(loans, one)
    assert abs(c.at_risk.sum() - (15 + 2 / 3)) < 1e-9 and c.events.sum() == 0
    assert cells.events.sum() == 1


def test_adversarial_a_charge_off_after_the_date_is_not_an_event():
    rows = [_loan("2007-02-01", 84, "CHGOFF", chargeoff="2009-11-01", coa=40_000.0)]
    loans, _ = panel.prepare(_frame(rows))
    before = panel.observe(loans, np.datetime64("2008-12-31"))
    after = panel.observe(loans, np.datetime64("2009-12-31"))
    assert not before.event.any() and before.in_book.all()
    assert after.event.all() and not after.in_book.any()


@pytest.mark.parametrize("bad", ["2007-02-01"])
def test_adversarial_a_loan_approved_after_the_date_is_not_selected(bad):
    rows = [_loan(bad, 84, "EXEMPT")]
    loans, _ = panel.prepare(_frame(rows))
    obs = panel.observe(loans, np.datetime64("2006-12-31"))
    assert not obs.selected.any() and not obs.in_book.any()


def test_adversarial_an_open_loan_counted_to_its_term_is_found():
    """A loan of a ten-year term observed for 47 months contributes 15 and two thirds of a quarter, never its 40 quarters."""
    loans, _ = panel.prepare(_frame([_loan("2005-01-15", 120, "EXEMPT")]))
    cells = ladder.build_cells(loans, panel.observe(loans, np.datetime64("2008-12-31")))
    assert cells.at_risk.sum() < 40 and abs(cells.at_risk.sum() - (15 + 2 / 3)) < 1e-9
