"""U9-P2: the regulatory parity bake. The producer test of the regulatory-calculators contract: the document validates, the
cross-field checks are clean, every engine value equals the official one, and every value comes from the engine."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest
from reg_support import COMMITTED, EAD_PUBLISHED, ENGINE_COMMIT, INPUTS, REQUIREMENTS, ROOT, by_id, load_semantics, out

sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import contract_schemas as cs  # noqa: E402

REF = "regulatory/calculators"


def committed() -> dict:
    assert COMMITTED.exists(), "data/derived/regulatory/calculators.json is the bake's document and is committed"
    return json.loads(COMMITTED.read_text(encoding="utf-8"))


# --- the document, built and committed ----------------------------------------------------------------------------------


def test_the_built_document_validates_against_the_schema_and_the_checker_is_clean(built) -> None:
    assert cs.errors(REF, built) == []
    assert load_semantics().check_regulatory(built) == []


def test_the_committed_document_validates_and_the_checker_is_clean() -> None:
    doc = committed()
    assert cs.schema_for_document(COMMITTED, doc) == REF
    assert cs.errors(REF, doc) == []
    assert load_semantics().check_regulatory(doc) == []


def test_the_committed_document_is_the_one_the_bake_makes(built) -> None:
    assert committed() == json.loads(json.dumps(built))


# --- the official values ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("which", ["built", "committed"])
def test_the_five_cre99_eads_round_to_the_published_integers_and_the_multiplier_is_0_965208(which, request) -> None:
    doc = request.getfixturevalue("built") if which == "built" else committed()
    ex = by_id(doc)
    for k, want in EAD_PUBLISHED.items():
        assert math.floor(out(ex[k], "ead") + 0.5) == want, k
        assert {p["name"]: p["value"] for p in ex[k]["published"]}["ead"] == want
    assert round(out(ex["cre99-netting-set-2"], "multiplier"), 6) == 0.965208
    assert round(out(ex["cre99-netting-set-5"], "multiplier"), 6) == 0.958123
    assert round(out(ex["cre99-netting-set-1"], "swaption_delta"), 4) == -0.2694
    assert out(ex["rbc20-13-output-floor"], "rwa_floored") == pytest.approx(101.5, rel=1e-12)
    assert out(ex["rbc20-13-output-floor-capped"], "rwa_floored") == pytest.approx(95.0, rel=1e-12)


def test_the_intermediates_of_the_five_netting_sets_match_the_printed_values(built) -> None:
    ex = by_id(built)
    s1, s2, s3, s5 = (ex[f"cre99-netting-set-{i}"] for i in (1, 2, 3, 5))
    assert round(out(s1, "en_usd")) == 59270 and round(out(s1, "en_eur")) == 10083 and round(out(s1, "addon_ir")) == 347
    assert round(out(s2, "term_1")) == 2253 and round(out(s2, "term_2")) == 77344 and round(out(s2, "addon_credit")) == 282
    assert round(out(s3, "addon_energy")) == 2041 and round(out(s3, "addon_metals")) == 1800
    assert round(out(s5, "addon_ir")) == 123 and round(out(s5, "addon_commodity")) == 1278
    assert out(s5, "maturity_factor") == pytest.approx(1.5 * math.sqrt(14 / 250), rel=1e-12)


def test_every_published_value_is_matched_by_an_output(built) -> None:
    for e in built["official_examples"]:
        names = {v["name"] for v in e["outputs"]}
        for p in e["published"]:
            assert p["name"] in names, (e["id"], p["name"])


# --- every value comes from the engine, none is copied -----------------------------------------------------------------


def test_the_inputs_file_holds_no_output_value_only_the_specs_of_the_outputs() -> None:
    data = json.loads(INPUTS.read_text(encoding="utf-8"))
    for e in data["official_examples"] + data["invariant_cases"]:
        assert "outputs" not in e, e["id"]
        for spec in e["output_specs"]:
            assert set(spec) == {"name", "symbol", "unit", "basis", "paragraph"}, (e["id"], spec)
    assert all("risk_weight" not in g for g in data["cre20_grid_keys"])
    assert all("rows" not in t for t in data["parameter_tables"])


def test_the_ead_is_what_the_engine_returns_not_a_copied_number(monkeypatch) -> None:
    """Plant a sentinel in the engine's netting_set_ead: the document must carry it, so the EAD is read from the engine's result."""
    from pipeline.regulatory import bake
    from riskvalidation.regulatory import sa_ccr

    real = sa_ccr.netting_set_ead

    def planted(*a, **k):
        r = real(*a, **k)
        return type(r)(r.rc, r.addon_aggregate, r.multiplier, r.pfe, 123456.789, r.alpha)

    monkeypatch.setattr(sa_ccr, "netting_set_ead", planted)
    doc = bake.build()
    assert all(out(by_id(doc)[k], "ead") == 123456.789 for k in EAD_PUBLISHED)


def test_a_planted_engine_value_reaches_the_floor_the_cascade_and_the_grid(monkeypatch) -> None:
    from pipeline.regulatory import bake
    from riskvalidation.regulatory import frtb, output_floor, standardised

    monkeypatch.setattr(output_floor, "floored_rwa", lambda *a, **k: 7.5)
    monkeypatch.setattr(frtb, "liquidity_cascade_es", lambda *a, **k: 4.25)
    real = standardised.lookup
    monkeypatch.setattr(standardised, "lookup", lambda *a, **k: type(real("sovereign", "unrated"))(9.0, "CRE20.7", "CRE20 Table 1", "2023-01-01"))
    doc = bake.build()
    ex = by_id(doc)
    assert out(ex["rbc20-13-output-floor"], "rwa_floored") == 7.5 and out(ex["cascade-two-horizons"], "es") == 4.25
    assert {g["risk_weight"] for g in doc["cre20_grid"]} == {9.0}


def test_the_bake_refuses_an_input_the_engine_refuses(monkeypatch) -> None:
    from pipeline.regulatory import bake
    from riskvalidation.regulatory import sa_ccr

    def refuse(*a, **k):
        raise ValueError("planted refusal (CRE52.72)")

    monkeypatch.setattr(sa_ccr, "supervisory_duration", refuse)
    with pytest.raises(ValueError, match="planted refusal"):
        bake.build()


def test_the_bake_refuses_a_document_the_checker_refuses(tmp_path: Path, monkeypatch) -> None:
    from pipeline.regulatory import bake

    monkeypatch.setattr(bake, "_semantics", lambda: type("S", (), {"check_regulatory": staticmethod(lambda d: ["planted finding"])}))
    with pytest.raises(ValueError, match="planted finding"):
        bake.bake(tmp_path)
    assert not (tmp_path / "regulatory" / "calculators.json").exists()


# --- paragraphs and in-force dates --------------------------------------------------------------------------------------


def test_every_grid_cell_phase_in_row_and_table_row_is_the_engines_with_its_paragraph_and_date(built) -> None:
    from riskvalidation.regulatory import ba_cva, frtb, output_floor, sa_ccr, standardised

    for g in built["cre20_grid"]:
        p = standardised.lookup(g["exposure_class"], g["key"], short_term=g["short_term"], cash_flow_dependent=g["cash_flow_dependent"],
                                counterparty_weight=g["counterparty_weight"])
        assert (g["risk_weight"], g["table"], g["paragraph"], g["in_force_date"]) == (p.value, p.table, p.paragraph, p.in_force)
    for r in built["output_floor_phase_in"]:
        p = output_floor.phase_in_factor(r["year"])
        assert (r["factor"], r["table"], r["paragraph"], r["in_force_date"]) == (p.value, p.table, p.paragraph, p.in_force)
    tables = {t["id"]: t for t in built["parameter_tables"]}
    assert {(r["key"], r["parameter"]): r["value"] for r in tables["cre52-72-table-2"]["rows"]} == \
        {k: p.value for k, p in sa_ccr.SUPERVISORY_PARAMETERS.items()}
    assert {(r["key"], r["parameter"]): r["value"] for r in tables["mar50-16-table-1"]["rows"]} == \
        {k: p.value for k, p in ba_cva.SECTOR_RISK_WEIGHTS.items()}
    assert {(r["key"], r["parameter"]): r["value"] for r in tables["mar33-12-table-2"]["rows"]} == \
        {k: p.value for k, p in frtb.LIQUIDITY_HORIZONS_TABLE_2.items()}
    assert {(r["key"], r["parameter"]): r["value"] for r in tables["mar33-4-table-1"]["rows"]} == \
        {k: p.value for k, p in frtb.LIQUIDITY_HORIZONS_TABLE_1.items()}
    for t in tables.values():
        assert t["paragraph"] and t["table"] and t["in_force_date"]


def test_every_entry_cites_its_paragraph_and_the_in_force_date_of_the_engines_chapter(built) -> None:
    from riskvalidation.regulatory import ba_cva, frtb, output_floor, sa_ccr

    dates = {"CRE": sa_ccr.CRE52_IN_FORCE, "MAR50": ba_cva.MAR50_IN_FORCE, "MAR21": frtb.MAR21_IN_FORCE,
             "MAR33": frtb.MAR33_IN_FORCE, "RBC": output_floor.RBC_IN_FORCE}
    for e in built["official_examples"] + built["invariant_cases"]:
        assert e["paragraph"] and e["paragraph_range"] and e["in_force_date"] and e["published_date"]
        chapter = "CRE" if e["paragraph"].startswith("CRE") else e["paragraph"][:5] if e["paragraph"].startswith("MAR") else "RBC"
        assert e["in_force_date"] == dates[chapter], e["id"]
        for v in e["inputs"] + e["outputs"] + e["published"]:
            assert v["paragraph"], (e["id"], v["name"])


# --- the GIRR convention ------------------------------------------------------------------------------------------------


def test_the_girr_headline_divides_the_weights_by_sqrt2_and_the_undivided_charge_is_beside_it(built) -> None:
    e = by_id(built)["girr-delta-charge-sqrt2"]
    headline, undivided = out(e, "girr_charge"), out(e, "girr_charge_undivided")
    assert headline == pytest.approx(0.011 * 8.0e7 / math.sqrt(2), rel=1e-12)
    assert undivided == pytest.approx(0.011 * 8.0e7, rel=1e-12)
    assert undivided == pytest.approx(headline * math.sqrt(2), rel=1e-12)
    assert out(e, "risk_weight_divisor") == pytest.approx(math.sqrt(2), rel=1e-15)
    assert "MAR21.44" in e["statement"]["en"] and "convention" in e["statement"]["en"]
    assert e["holds"] is True and e["tolerance_relative"] == 1e-9


def test_the_sbm_cascade_and_ba_cva_cases_have_the_engines_values(built) -> None:
    ex = by_id(built)
    fb = ex["sbm-cross-bucket-fallback"]
    assert out(fb, "fallback_medium") == 1.0 and out(fb, "fallback_low") == 0.0
    assert out(fb, "sbm_charge") == pytest.approx(10.954451150103322, rel=1e-12)
    assert out(ex["sbm-bucket-and-cross-bucket-aggregation"], "fallback_medium") == 0.0
    assert out(ex["cascade-all-lh-ten"], "es") == pytest.approx(10.0, rel=1e-12)
    assert out(ex["cascade-two-horizons"], "es") == pytest.approx(math.sqrt(136.0), rel=1e-12)
    assert out(ex["ba-cva-rho-one"], "k_reduced") == pytest.approx(30.0, rel=1e-12)
    assert out(ex["ba-cva-hedges-floor"], "k_full") == pytest.approx(7.5, rel=1e-12)
    assert [out(ex["sbm-low-and-high-scenarios"], n) for n in ("rho_low", "rho_medium", "rho_high")] == pytest.approx([0.375, 0.5, 0.625])


# --- provenance, determinism, the pin -----------------------------------------------------------------------------------


def test_the_provenance_names_no_third_party_file_and_the_engine_commit(built) -> None:
    p = built["provenance"]
    assert p["inputs"] == [] and p["licence_classes"] == {} and p["truth_status"] == "published-answer"
    assert built["engine"]["name"] == "riskvalidation" and ENGINE_COMMIT[:7] in built["engine"]["version"]
    assert p["riskvalidation_version"] == built["engine"]["version"]
    assert built["lane"]["lane"] in ("live", "precompute")


def test_the_engine_is_pinned_to_the_reviewed_batch_3_commit() -> None:
    text = REQUIREMENTS.read_text(encoding="utf-8")
    assert f"CAOS_RiskValidation@{ENGINE_COMMIT}" in text and "@v0.07.000" not in text


def test_two_bakes_write_byte_identical_documents(tmp_path: Path) -> None:
    from pipeline.regulatory import bake

    a, b = bake.bake(tmp_path / "a"), bake.bake(tmp_path / "b")
    pa, pb = tmp_path / "a" / "regulatory" / "calculators.json", tmp_path / "b" / "regulatory" / "calculators.json"
    assert pa.read_bytes() == pb.read_bytes() and a == b


def test_a_sandbox_bake_reproduces_the_committed_bytes(tmp_path: Path) -> None:
    from pipeline.regulatory import bake

    bake.bake(tmp_path)
    assert (tmp_path / "regulatory" / "calculators.json").read_bytes() == COMMITTED.read_bytes()
