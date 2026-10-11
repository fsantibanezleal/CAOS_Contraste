"""CONTRACT 1 (ingestion), CT-001: every family rejects what violates it, naming the field, the expected range and
the policy; flags what is suspicious but valid; excludes what is valid but outside the case's use; never coerces."""
from __future__ import annotations

import json

import pytest

from pipeline.io import contract as c


def _one(report: c.ContractReport) -> dict:
    assert len(report.rejected) == 1, report.rejected
    return report.rejected[0]["violations"][0]


def test_reject_out_of_range():
    rep = c.validate("scored_sample", [
        {"id": "a1", "observation_date": "2005-09-30", "target": 1, "pd": 0.04},
        {"id": "a2", "observation_date": "2005-09-30", "target": 0, "pd": 1.2},
    ])
    assert [r["id"] for r in rep.accepted] == ["a1"]
    v = _one(rep)
    assert v["field"] == "pd" and v["value"] == 1.2 and v["policy"] == "reject"
    assert v["expected"] == "a finite number in (0, 1) (probability)"
    assert v["reason"] == "out of range"


@pytest.mark.parametrize("value,reason", [
    ("0.5x", "not a number"), (True, "a boolean where a number is declared"), (float("inf"), "not finite"),
])
def test_numbers_are_parsed_strictly_never_coerced(value, reason):
    rep = c.validate("scored_sample", [{"id": "a", "observation_date": "2005-09-30", "target": 0, "pd": value}])
    assert _one(rep)["reason"] == reason and not rep.accepted


def test_text_from_a_csv_is_read_as_its_declared_kind():
    rep = c.validate("scored_sample", [{"id": "a", "observation_date": "2005-09-30", "target": "1", "pd": "0.25"}])
    assert rep.accepted == [{"id": "a", "observation_date": __import__("datetime").date(2005, 9, 30), "target": 1,
                             "score": None, "pd": 0.25, "grade": None, "segment": None, "protected_attr": None}]


def test_missing_required_is_rejected_and_missing_feature_is_flagged():
    feature = c.Field("limit_bal", "float", {"en": "Credit limit", "es": "Cupo"}, unit="NTD", lo=0.0, on_missing="flag")
    rep = c.validate("scored_sample", [
        {"id": "a", "observation_date": "2005-09-30", "target": 0, "limit_bal": None},
        {"id": "b", "observation_date": None, "target": 0, "limit_bal": 5000},
    ], extra_fields=[feature])
    assert [r["id"] for r in rep.accepted] == ["a"]
    assert rep.flagged[0]["field"] == "limit_bal" and rep.flagged[0]["policy"] == "flag"
    assert _one(rep)["field"] == "observation_date" and _one(rep)["reason"] == "missing"


def test_undeclared_columns_are_listed_and_never_used():
    rep = c.validate("scored_sample", [{"id": "a", "observation_date": "2005-09-30", "target": 0, "secret": 9}])
    assert rep.ignored_columns == ["secret"] and "secret" not in rep.accepted[0]


def test_a_closed_family_refuses_added_fields():
    with pytest.raises(c.ContractError, match="declares all its fields"):
        c.validate("curve", [], extra_fields=[c.Field("x", "float", {"en": "x", "es": "x"})])


def test_unknown_grade_rejected_and_scale_required():
    rows = [{"id": "a", "observation_date": "2005-09-30", "target": 0, "grade": "AAA"}]
    assert _one(c.validate("scored_sample", rows))["reason"].startswith("no value set declared")
    rep = c.validate("scored_sample", rows, params={"grades": ["A", "B", "C"]})
    assert _one(rep)["field"] == "grade" and "one of {A, B, C}" in _one(rep)["expected"]


def test_duplicates_rejected_by_group_rule():
    rep = c.validate("scored_sample", [
        {"id": "a", "observation_date": "2005-09-30", "target": 0},
        {"id": "a", "observation_date": "2005-09-30", "target": 1},
    ])
    assert len(rep.accepted) == 1 and rep.rejected[0]["violations"][0]["rule"] == "SS-UNIQUE"


def _loan(**kw):
    base = {"account_id": "L1", "reporting_date": "2020-01-31", "origination_date": "2018-05-01", "balance": 900.0,
            "limit": 1000.0, "revolving": 1, "eir": 0.18, "dpd": 0, "default_flag": 0, "prepay_flag": 0,
            "writeoff_flag": 0}
    base.update(kw)
    return base


def test_loan_panel_cross_field_rules():
    rep = c.validate("loan_panel", [
        _loan(),
        _loan(account_id="L2", origination_date="2021-01-01"),          # originated after the report
        _loan(account_id="L3", limit=800.0),                            # limit below balance
        _loan(account_id="L4", limit=None),                             # revolving without a limit
        _loan(account_id="L5", workout_cashflow=120.0),                 # cash flow without a date
        _loan(account_id="L6", eir=1.5),                                # out of [0, 1]
    ])
    assert [r["account_id"] for r in rep.accepted] == ["L1"]
    rules = {r["key"].split()[0]: r["violations"][0].get("rule", r["violations"][0]["field"]) for r in rep.rejected}
    assert rules == {"L2": "LP-DATES", "L3": "LP-LIMIT", "L4": "LP-LIMIT", "L5": "LP-CASHFLOW", "L6": "eir"}


def test_loan_panel_dpd_jump_flagged_and_open_workout_excluded():
    rows = [
        _loan(reporting_date="2020-01-31", dpd=0),
        _loan(reporting_date="2020-02-29", dpd=60),                      # +60 in one month: flagged
        _loan(account_id="W", reporting_date="2020-03-31", dpd=95, default_flag=1),
        _loan(account_id="W", reporting_date="2020-04-30", dpd=120, default_flag=1, workout_closed=0),
    ]
    rep = c.validate("loan_panel", rows, params={"workout_cutoff": "2020-06-30"})
    assert [f["rule"] for f in rep.flagged] == ["LP-DPD-JUMP"]
    assert len(rep.excluded) == 2 and all(e["rule"] == "LP-WORKOUT-OPEN" for e in rep.excluded)
    assert [r["account_id"] for r in rep.accepted] == ["L1", "L1"]


def test_rating_history_scale_and_withdrawn_conventions():
    rows = [{"obligor_id": "o1", "date": "2019-12-31", "grade": "A"},
            {"obligor_id": "o1", "date": "2020-12-31", "grade": "WR"},
            {"obligor_id": "o2", "date": "2020-12-31", "grade": "Z"}]
    with pytest.raises(c.ContractError, match="no default grade 'D'"):
        c.validate("rating_history", rows, params={"grades": ["A", "B"], "wr_convention": "exclude"})
    ex = c.validate("rating_history", rows, params={"grades": ["A", "B", "D"], "wr_convention": "exclude"})
    assert len(ex.accepted) == 1 and ex.excluded[0]["rule"] == "RH-WR-EXCLUDE" and _one(ex)["field"] == "grade"
    ce = c.validate("rating_history", rows, params={"grades": ["A", "B", "D"], "wr_convention": "censor"})
    assert len(ce.accepted) == 2 and ce.flagged[0]["rule"] == "RH-WR-CENSOR"
    st = c.validate("rating_history", rows, params={"grades": ["A", "B", "D"], "wr_convention": "state"})
    assert len(st.accepted) == 2 and not st.flagged


def test_market_series_gap_flagged_over_five_business_days():
    rows = [{"date": "2020-03-02", "series_id": "SPX", "value": 0.01, "unit": "return"},
            {"date": "2020-03-09", "series_id": "SPX", "value": -0.07, "unit": "return"},   # 5 business days
            {"date": "2020-03-17", "series_id": "SPX", "value": 0.02, "unit": "return"}]    # 6 business days
    rep = c.validate("market_series", rows)
    assert len(rep.accepted) == 3 and [f["row"] for f in rep.flagged] == [2]


def test_curve_monotone_tenors_and_plausible_rates():
    rows = [{"date": "2022-12-30", "tenor_years": t, "rate": r, "compounding": "annual"}
            for t, r in ((0.25, 0.044), (1.0, 0.047), (0.5, 0.046), (30.0, 0.39))]
    rep = c.validate("curve", rows)
    assert _one(rep)["rule"] == "CV-MONOTONE" and rep.rejected[0]["row"] == 2
    assert [f["rule"] for f in rep.flagged] == ["CV-RANGE"]


def test_balance_sheet_bands_currency_and_nmd_caps():
    ok = {"as_of": "2022-12-31", "item": "deposits", "currency": "USD", "amount": -1e9, "repricing_bucket": "ON",
          "behavioural_class": "nmd_retail_transactional", "core_share": 0.95, "core_avg_maturity_years": 4.0}
    rep = c.validate("balance_sheet", [ok, {**ok, "currency": "GBP"}, {**ok, "repricing_bucket": "30Y"}])
    assert len(rep.accepted) == 1 and len(rep.rejected) == 2
    assert "above the cap 0.9" in rep.flagged[0]["reason"]
    assert len(c.REPRICING_BANDS) == 19 and c.REPRICING_BANDS[-1] == ("20Y+", 25.0)


def test_loss_events_threshold_and_types():
    params = {"collection_threshold": 20_000.0, "currency": "EUR"}
    ev = {"event_id": "e1", "date": "2015-06-30", "business_line": "retail banking", "event_type": "external_fraud",
          "gross_loss": 25_000.0}
    rep = c.validate("loss_events", [ev, {**ev, "event_id": "e2", "gross_loss": 19_999.0},
                                      {**ev, "event_id": "e3", "event_type": "fraud"}], params=params)
    assert [r["event_id"] for r in rep.accepted] == ["e1"]
    assert {r["violations"][0].get("rule", r["violations"][0]["field"]) for r in rep.rejected} == {"LE-THRESHOLD", "event_type"}
    with pytest.raises(c.ContractError, match="collection_threshold"):
        c.validate("loss_events", [ev], params={"currency": "EUR"})


def test_macro_path_vintage_after_observation_rejected():
    p = {"scenario": "severely adverse", "date": "2026-06-30", "variable": "unemployment", "value": 0.10,
         "unit": "rate", "vintage_date": "2026-02-01"}
    rep = c.validate("macro_path", [p, {**p, "date": "2026-09-30", "vintage_date": "2026-11-01"}],
                     params={"observation_date": "2026-03-31"})
    assert len(rep.accepted) == 1 and _one(rep)["rule"] == "MP-VINTAGE"


def test_every_family_exports_a_bilingual_declaration(tmp_path):
    written = c.export_contracts(tmp_path)
    assert sorted(written) == sorted([f"{n}.json" for n in c.FAMILIES] + ["index.json"])
    for name in c.FAMILIES:
        doc = json.loads((tmp_path / f"{name}.json").read_text(encoding="utf-8"))
        assert doc["schema"] == c.SCHEMA and doc["family"] == name
        texts = [doc["title"], doc["used_by"]] + [f["meaning"] for f in doc["fields"]] + [r["statement"] for r in doc["rules"]]
        assert all(set(t) == {"en", "es"} and t["en"] and t["es"] for t in texts), name


def test_the_committed_contract_export_is_current(tmp_path):
    """The web reads data/derived/contract/; it must be what the code declares today."""
    c.export_contracts(tmp_path)
    from pipeline.pipeline import REPO_ROOT
    committed = REPO_ROOT / "data" / "derived" / "contract"
    for f in sorted(tmp_path.iterdir()):
        assert (committed / f.name).read_bytes() == f.read_bytes(), f"{f.name}: re-export with data-pipeline/run.py"
