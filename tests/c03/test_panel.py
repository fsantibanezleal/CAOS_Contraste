"""CT-801: the panel of C03 (the shared SBA 7(a) reader, counted exclusions, origination attributes as the only inputs)."""
from __future__ import annotations

import dataclasses

import numpy as np

from pipeline.cases.c03 import panel

from .helpers import frame

OUTCOME_WORDS = ("exit", "status", "charge", "paid", "default", "horizon", "label")


def test_the_panel_counts_every_exclusion_and_the_inputs_are_origination_attributes(tables):
    loans, counts = tables["loans"], tables["counts"]
    excluded = sum(v for k, v in counts.items() if k not in ("rows-read", "loans-kept"))
    assert counts["rows-read"] == counts["loans-kept"] + excluded == len(tables["frame"])
    assert loans.n == counts["loans-kept"] and loans.n > 10_000
    # no name, address or identifier is a field of the panel
    fields = {f.name for f in dataclasses.fields(loans)}
    assert not {"BorrName", "BorrStreet", "LocationID", "name", "address", "id", "loan_id"} & fields
    # the model inputs are origination attributes: named so, and unchanged when every outcome is changed
    assert panel.FEATURES == ("log10_amount", "guarantee_share", "term_months", "sector", "revolver")
    assert not any(w in f for f in panel.FEATURES for w in OUTCOME_WORDS)
    x = panel.features(loans)
    assert list(x.columns) == list(panel.FEATURES) and len(x) == loans.n
    assert x.notna().all().all(), "an input has no missing value (the sector has its own unknown group)"
    changed = dataclasses.replace(loans, exit_kind=np.zeros_like(loans.exit_kind), exit_date=np.full(loans.n, np.datetime64("NaT"), "datetime64[D]"))
    assert panel.features(changed).equals(x)


def test_the_fiscal_year_starts_on_the_first_of_october():
    d = np.array(["2009-09-30", "2009-10-01", "2010-01-15", "2010-09-30", "2010-10-01"], dtype="datetime64[D]")
    assert panel.fiscal_year(d).tolist() == [2009, 2010, 2010, 2010, 2011]


def test_adversarial_a_planted_bad_row_is_counted_under_its_reason():
    clean = frame([{}, {"status": "CHGOFF", "chargeoff_date": "2013-01-01", "chargeoff_amount": 1.0}])
    planted = frame([
        {}, {"status": "CHGOFF", "chargeoff_date": "2013-01-01", "chargeoff_amount": 1.0},
        {"status": "CANCLD"}, {"term_months": 0.0}, {"status": "CHGOFF", "chargeoff_date": None},
        {"status": "CHGOFF", "chargeoff_date": "2009-06-01"},
    ])
    _, c0 = panel.prepare(clean)
    loans, c1 = panel.prepare(planted)
    assert c0["loans-kept"] == 2 and sum(v for k, v in c0.items() if k not in ("rows-read", "loans-kept")) == 0
    assert loans.n == 2 and c1["rows-read"] == 6
    assert c1["not-disbursed-or-cancelled"] == 1 and c1["term-missing-or-implausible"] == 1
    assert c1["chargeoff-without-date"] == 1 and c1["chargeoff-before-approval"] == 1
    assert c1["rows-read"] == c1["loans-kept"] + sum(v for k, v in c1.items() if k not in ("rows-read", "loans-kept"))
