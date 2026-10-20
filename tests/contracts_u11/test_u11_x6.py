"""U11 integration, decision X6 and item 5: the null Level 2 shares of an empty HQLA stock and the maturity-band call-report fields.

``l2_share`` and ``l2b_share`` of ``c16Hqla`` are nullable; ``shares_reason`` is required and nullable: a reason (a label) where the
shares are null, null where they are numbers. The schema (a ``oneOf`` of the two states) and the producer checker (``semantics.check_document``) both hold the rule. The fixture ``variant-scenario-lcr-empty-stock-fixture.json`` is the document of an empty stock. The ``c16Report.fields`` and
``source_fields`` enumeration names the maturity-band fields the ladder reads (U11-P integration item 5).
"""
from __future__ import annotations

import copy
import importlib.util
import sys

import contract_schemas as cs
import pytest
from test_u11_contracts import FIXTURES, ROOT, SC, errs, load, sm

EMPTY = FIXTURES / "c16" / "variant-scenario-lcr-empty-stock-fixture.json"
REASON = {"en": "The HQLA stock is empty: the Level 2 and Level 2B shares are undefined, not zero.",
          "es": "El stock HQLA esta vacio: las proporciones de nivel 2 y 2B no estan definidas, no son cero."}
BAND_FIELDS = ["SCNM3LES", "SCPTOV15", "LNRS1T3", "LNOT5T15", "OTHBFH1L", "OTBOTOV5", "CD3LES", "CDOV3S", "SUBND", "NTRTIME"]


def empty_doc() -> dict:
    return cs.load_json(EMPTY)


def hq(doc: dict) -> dict:
    return doc["outputs"]["lcr"]["hqla"]


def checker(doc: dict) -> str:
    return " | ".join(sm.check_document(doc))


def test_the_empty_stock_document_validates_and_passes_the_checker() -> None:
    doc = empty_doc()
    assert cs.errors(SC, doc) == [] and sm.check_document(doc) == []
    h = hq(doc)
    assert h["hqla"] == 0 and h["l2_share"] is None and h["l2b_share"] is None and h["shares_reason"] is not None
    assert doc["outputs"]["lcr"]["ratio"] == 0


def test_every_other_fixture_has_numeric_shares_and_a_null_reason() -> None:
    doc = load("lcr-standard")
    h = hq(doc)
    assert isinstance(h["l2_share"], float) and isinstance(h["l2b_share"], float) and h["shares_reason"] is None
    assert errs(SC, doc) == [] and sm.check_document(doc) == []


def test_null_shares_without_a_reason_fail() -> None:
    bad = empty_doc()
    hq(bad)["shares_reason"] = None
    assert errs(SC, bad) != [], "the schema refuses the pairing"
    assert "shares_reason" in checker(bad)


@pytest.mark.parametrize("which", ["l2_share", "l2b_share"])
def test_one_null_share_without_a_reason_fails(which: str) -> None:
    bad = load("lcr-standard")
    hq(bad)[which] = None
    assert errs(SC, bad) != []
    assert "shares_reason" in checker(bad)


def test_numeric_shares_with_a_reason_fail() -> None:
    bad = load("lcr-standard")
    hq(bad)["shares_reason"] = REASON
    assert errs(SC, bad) != []
    assert "shares_reason" in checker(bad)


def test_one_null_and_one_numeric_share_fail_even_with_a_reason() -> None:
    bad = load("lcr-standard")
    hq(bad)["l2b_share"] = None
    hq(bad)["shares_reason"] = REASON
    assert errs(SC, bad) != []
    assert "both" in checker(bad)


def test_the_reason_key_is_required_and_the_shares_cannot_be_a_string() -> None:
    bad = load("lcr-standard")
    del hq(bad)["shares_reason"]
    assert errs(SC, bad) != []
    bad = load("lcr-standard")
    hq(bad)["l2_share"] = "none"
    assert errs(SC, bad) != []
    bad = empty_doc()
    hq(bad)["shares_reason"] = {"en": ""}
    assert errs(SC, bad) != []


@pytest.mark.parametrize("field", BAND_FIELDS)
def test_a_document_may_name_a_maturity_band_field_it_read(field: str) -> None:
    doc = copy.deepcopy(load("list-adverse"))
    doc["outputs"]["data"]["call_reports"][0]["fields"].append(field)
    assert errs(SC, doc) == []


def test_a_field_outside_the_record_still_fails() -> None:
    doc = copy.deepcopy(load("list-adverse"))
    doc["outputs"]["data"]["call_reports"][0]["fields"].append("RCON2200")
    assert errs(SC, doc) != []


def test_the_bake_writes_null_shares_with_their_reason_for_an_empty_stock_and_never_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    """The C16 bake's LCR block on a report whose HQLA stock is empty (the securities levels forced to zero): null shares, their
    reason, a zero ratio; the block lies in the schema and the checker accepts it as the HQLA part of a scenario document."""
    sys.path.insert(0, str(ROOT / "data-pipeline"))
    spec = importlib.util.spec_from_file_location("c16_helpers_x6", ROOT / "tests" / "c16" / "helpers.py")
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    from pipeline.cases.c16 import assumptions, balance, variant

    real = balance.lcr_balances

    def empty(report, factor):
        inp = real(report, factor)
        inp["levels"] = {k: 0.0 for k in inp["levels"]}
        return inp

    monkeypatch.setattr(balance, "lcr_balances", empty)
    block = variant.lcr_block(helpers.sample_report(), assumptions.conventions())
    h = block["hqla"]
    assert h["hqla"] == 0 and h["l2_share"] is None and h["l2b_share"] is None
    assert h["shares_reason"]["en"] and h["shares_reason"]["es"] and block["ratio"] == 0
    doc = empty_doc()
    doc["outputs"]["lcr"]["hqla"] = h
    assert cs.errors(SC, doc) == []
