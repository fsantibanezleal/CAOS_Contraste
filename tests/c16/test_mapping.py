"""CT-1605 to CT-1608: the call-report mapping (deposits and their denominators, the named mapping table, the securities by type
and the pledged ones, the missing items and the reconciliation)."""
from __future__ import annotations

import copy

import pytest

from .helpers import sample_report


def test_the_deposits_block_states_both_denominators():
    from pipeline.cases.c16 import balance

    r = sample_report()
    d = balance.deposits_block(r)
    assert (d["dep"], d["depdom"], d["depuna"], d["depins"]) == (r.get("DEP"), r.get("DEPDOM"), r.get("DEPUNA"), r.get("DEPINS"))
    assert (d["depsmamt"], d["deplgamt"]) == (r.get("DEPSMAMT"), r.get("DEPLGAMT"))
    assert d["denominators"] == {"insured_uninsured": "DEPDOM", "total": "DEP"}
    assert d["uninsured_share_of_dep"] == pytest.approx(r.get("DEPUNA") / r.get("DEP"), rel=1e-12)
    assert d["uninsured_share_of_depdom"] == pytest.approx(r.get("DEPUNA") / r.get("DEPDOM"), rel=1e-12)
    assert d["uninsured_share_of_dep"] < d["uninsured_share_of_depdom"]
    assert d["size_threshold"]["value"] == 250000 and d["size_threshold"]["unit"] == "USD"
    # the segments the ladder runs: insured, uninsured and foreign-office deposits, summing to DEP
    segs = balance.deposit_segments(r)
    assert [s["segment"] for s in segs] == ["retail-insured", "non-operational-corporate", "financial"]
    assert [s["opening"] for s in segs] == [r.get("DEPINS"), r.get("DEPUNA"), r.get("DEPFOR")]
    assert sum(s["opening"] for s in segs) == pytest.approx(r.get("DEPDOM") + r.get("DEPFOR"), rel=1e-3)


def test_the_deposit_mapping_is_a_named_table_with_a_sensitivity_band():
    from riskvalidation.liquidity import runoff
    from riskvalidation.regulatory import lcr_nsfr

    from pipeline.cases.c16 import assumptions

    m = assumptions.deposit_category_mapping()
    assert m["status"] == "convention"
    assert [(r["basis"], r["role"]) for r in m["rows"]] == [("insured", "central"), ("uninsured", "central")]
    assert {r["lcr_category"] for r in m["sensitivity_band"]} == {"operational", "non_financial_corporate", "other_legal_entity"}
    classes = set(runoff.LIST_PARAMETERS["adverse"]["open_maturity"])
    for r in [*m["rows"], *m["sensitivity_band"]]:
        assert r["lcr_category"] in lcr_nsfr.LCR_OUTFLOW_RATES and r["list_class"] in classes
        assert r["label"]["en"] and r["label"]["es"]
    assert m["basis"]["en"].lower().count("convention") >= 1 and "never a regulatory classification" in m["basis"]["en"]


def test_securities_are_split_by_type_and_the_pledged_ones_leave_the_cbc():
    from pipeline.cases.c16 import balance

    r = sample_report()
    classes = balance.securities_classes(r)
    by = {c.class_id: c for c in classes}
    assert list(by) == ["cash-and-balances", "treasury", "mortgage-backed", "other-agency", "municipal", "other-debt"]
    assert by["treasury"].carrying == r.get("SCUST") and by["mortgage-backed"].carrying == r.get("SCMTGBK")
    assert by["other-agency"].carrying == r.get("SCASPNSUM") and by["municipal"].carrying == r.get("SCMUNI")
    assert by["other-debt"].carrying == r.get("SCDOMO") + r.get("SCFORD")
    # the pledged securities are encumbered pro rata across the types and sum to SCPLEDGE; cash is never encumbered
    share = r.get("SCPLEDGE") / r.get("SC")
    for cid in ("treasury", "mortgage-backed", "other-agency", "municipal", "other-debt"):
        assert by[cid].encumbered == pytest.approx(by[cid].carrying * share, rel=1e-12)
    assert sum(c.encumbered for c in classes) == pytest.approx(r.get("SCPLEDGE"), rel=1e-3)
    assert by["cash-and-balances"].encumbered == 0.0 and by["cash-and-balances"].fair_value is None
    # the held-to-maturity loss is applied to the whole book pro rata: one factor, never a by-type reported loss
    factor = (r.get("SCHF") + r.get("SCAF")) / (r.get("SCHA") + r.get("SCAF"))
    assert balance.fair_value_factor(r) == pytest.approx(factor, rel=1e-15) and factor < 1.0
    for cid in ("treasury", "mortgage-backed", "other-agency", "municipal", "other-debt"):
        assert by[cid].fair_value == pytest.approx(by[cid].carrying * factor, rel=1e-12)


def test_a_missing_call_report_item_is_null_with_its_reason_and_the_sheet_reconciles():
    from pipeline.cases.c16 import balance
    from pipeline.io.fdic import Report

    r = sample_report()
    sheet = balance.balance_sheet(r)
    items = {i["item_id"]: i for i in sheet["items"]}
    assets = sum(i["amount"] for i in sheet["items"] if i["side"] == "asset")
    liabs = sum(i["amount"] for i in sheet["items"] if i["side"] == "liability")
    assert assets == pytest.approx(r.get("ASSET"), rel=1e-12) and liabs == pytest.approx(r.get("ASSET"), rel=1e-12)
    assert sheet["total_assets"] == r.get("ASSET")
    for i in sheet["items"]:
        assert (i["reported_amount"] is None) == (i["reason_missing"] is not None)
    assert items["other-assets"]["reported_amount"] is None and items["other-assets"]["reason_missing"]["en"]
    assert items["deposits-uninsured"]["insured"] == 0 and items["deposits-insured"]["insured"] == 1   # 1 insured, 0 not insured
    # DEPFOR not reported: derived as DEP minus DEPDOM with its reason, never a number from elsewhere
    values = copy.deepcopy(dict(r.values))
    values["DEPFOR"] = None
    gap = balance.balance_sheet(Report(r.report_date, values))
    f = {i["item_id"]: i for i in gap["items"]}["deposits-foreign"]
    assert f["reported_amount"] is None and f["reason_missing"]["en"] and f["amount"] == r.get("DEP") - r.get("DEPDOM")
    # FREPO not reported: no reported amount, the reason, and an assumption that says it is taken as zero
    values = copy.deepcopy(dict(r.values))
    values["FREPO"] = None
    gap = balance.balance_sheet(Report(r.report_date, values))
    f = {i["item_id"]: i for i in gap["items"]}["reverse-repo"]
    assert f["reported_amount"] is None and f["amount"] == 0.0 and "zero" in f["assumption"]
    assert sum(i["amount"] for i in gap["items"] if i["side"] == "asset") == pytest.approx(r.get("ASSET"), rel=1e-12)
    # an item the sheet cannot do without is refused, naming the field
    values = copy.deepcopy(dict(r.values))
    values["DEPUNA"] = None
    with pytest.raises(ValueError, match="DEPUNA"):
        balance.balance_sheet(Report(r.report_date, values))
