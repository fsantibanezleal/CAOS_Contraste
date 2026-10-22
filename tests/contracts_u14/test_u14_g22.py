"""Decision G22 (2026-10-20): `c02-outputs` 1.1.0 makes `term_structure` nullable with `term_structure_reason`.

The horizon files are independent samples, not one cohort, so no cumulative curve is forced: null with its reason when the points cannot
form a cumulative curve, the block as before when they can. The schema change is a minor step (every 1.0.0 document stays valid: the new
field is optional and the block still validates); the checker pairs the two.
"""
from __future__ import annotations

import copy

import contract_schemas as cs
import pytest
from test_u14_contracts import H1, POOLED, SCHEMAS, load

REF = "c02/variant-horizon"
REASON = {"en": "The five files are independent samples of different forecast years, not one cohort followed through time; their rates fall with "
                "the horizon, so no cumulative PD is read from them.",
          "es": "Los cinco archivos son muestras independientes de distintos años de pronóstico, no una cohorte seguida en el tiempo; sus tasas "
                "bajan con el horizonte, así que no se lee de ellos una PD acumulada."}


def sem():
    import semantics

    return semantics


def errors(doc: dict) -> list[str]:
    return list(cs.errors(REF, doc))


def null_block(doc: dict, reason=REASON) -> dict:
    d = copy.deepcopy(doc)
    d["outputs"]["term_structure"] = None
    d["outputs"]["term_structure_reason"] = reason
    return d


def test_the_schema_makes_the_block_nullable_and_the_reason_optional_so_every_1_0_0_document_stays_valid() -> None:
    schema = load(SCHEMAS / "c02" / "variant-horizon.schema.json")
    out = schema["$defs"]["c02Outputs"]
    assert schema["$defs"]["c02TermStructure"]["type"] == ["object", "null"]          # a widened type: the gate's mechanical floor sees no break
    assert "term_structure" in out["required"] and "term_structure_reason" in out["properties"] and "term_structure_reason" not in out["required"]
    assert "2.0.0" in schema["description"]          # U16-F2: the contract moved to 2.0.0 (BiText impact texts, transfer cells keyed on the model)
    h1 = load(H1)
    old = copy.deepcopy(h1)
    old["outputs"].pop("term_structure_reason", None)                                    # a 1.0.0 document has no such key
    assert errors(old) == [] and sem().check_c02(old) == []


def test_the_fixtures_show_both_shapes_and_validate() -> None:
    h1, pooled = load(H1), load(POOLED)
    assert h1["outputs"]["term_structure"] is not None and h1["outputs"]["term_structure_reason"] is None
    assert pooled["outputs"]["term_structure"] is None and pooled["outputs"]["term_structure_reason"] is not None
    for d in (h1, pooled):
        assert errors(d) == [] and sem().check_c02(d) == []


def test_a_null_block_with_its_reason_passes_and_the_curve_checks_run_only_where_the_block_is_present() -> None:
    doc = null_block(load(H1))
    assert errors(doc) == [] and sem().check_c02(doc) == []
    bad = copy.deepcopy(load(H1))
    bad["outputs"]["term_structure"]["points"][2]["cumulative_pd"] = 0.01
    assert any("term structure" in m for m in sem().check_c02(bad))                    # the existing curve checks still run on a block


def test_the_pairing_is_checked_a_null_block_needs_a_reason_and_a_block_needs_a_null_reason() -> None:
    no_reason = null_block(load(H1))
    no_reason["outputs"].pop("term_structure_reason")
    assert any("term_structure_reason" in m for m in sem().check_c02(no_reason))
    null_reason = null_block(load(H1), reason=None)
    assert any("term_structure_reason" in m for m in sem().check_c02(null_reason))
    both = copy.deepcopy(load(H1))
    both["outputs"]["term_structure_reason"] = REASON
    assert any("term_structure_reason" in m for m in sem().check_c02(both))
    assert errors(both) == []                                                          # the schema does not pair them: the checker does


def test_a_reason_that_is_not_a_bilingual_text_is_refused_by_the_schema() -> None:
    bad = null_block(load(H1), reason="the rates fall")
    assert errors(bad)


def test_the_catalog_row_keeps_its_1_1_0_history_line() -> None:
    text = (cs.ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith("| c02-outputs | 2."))      # U16-F2 moved the row to 2.0.0
    assert row.startswith("| c02-outputs | 2.0.0 |")
    hist = [line for line in text.splitlines() if line.startswith("| c02-outputs | 1.1.0 | 2026-10-20 |")]
    assert len(hist) == 1 and "term_structure block nullable with term_structure_reason (U14 G22)" in hist[0] and hist[0].rstrip().endswith("| minor |")
    assert "independent samples, not one cohort" in hist[0] and "every 1.0.0 document stays valid" in hist[0]


@pytest.mark.parametrize("name", ["variant-horizon-h1-fixture.json", "variant-horizon-pooled-fixture.json"])
def test_every_c02_fixture_names_the_reason_key(name: str) -> None:
    assert "term_structure_reason" in load(cs.ROOT / "docs" / "contracts" / "fixtures" / "c02" / name)["outputs"]
