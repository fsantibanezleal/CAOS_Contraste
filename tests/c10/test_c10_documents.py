"""CT-1110, CT-1111: the committed documents of C10 validate, pass the cross-field checks of the contract, are listed with their hash
and name the Board's page; the small bake validates the same way."""
from __future__ import annotations

import json
from pathlib import Path

from c10_invariants import DERIVED, ROOT, hash_findings, label_findings, schema_findings, violations

from pipeline.cases.c10 import params as P

LOAN_TYPES = [lt["id"] for lt in P.LOAN_TYPES]
VARIANTS = (*LOAN_TYPES, "grid-22", "grid-40")
MODELS = "models-c10.json"


def committed() -> list[Path]:
    return sorted((DERIVED / "C10").glob("*.json"))


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_every_committed_document_validates_passes_the_checks_and_is_listed_with_its_hash() -> None:
    files = committed()
    assert [f.name for f in files] == sorted([MODELS, *(f"{v}.json" for v in VARIANTS)])
    manifest = load(DERIVED / "manifests" / "C10.json")
    assert schema_findings("data/derived/manifests/C10.json", manifest) == []
    assert hash_findings(DERIVED) == []
    assert manifest["case_id"] == "C10" and manifest["sources"] == ["fed-chargeoff"] and manifest["default_variant"] in VARIANTS
    for f in files:
        doc = load(f)
        assert schema_findings(f"data/derived/C10/{f.name}", doc) == [], f.name
        assert violations(doc) == [], (f.name, violations(doc))
        entry = next(a for a in manifest["artifacts"] if a["path"] == f"C10/{f.name}")
        assert entry["truth_status"] == doc["provenance"]["truth_status"]
        if f.name.startswith("grid"):
            years = int(f.stem.split("-")[1])
            cells = doc["outputs"]["cells"]
            assert [c["known_rho"] for c in cells] == list(P.RHO_GRID) and all(c["series_length_years"] == years for c in cells)
            assert all("known_rho" in c for c in cells) and doc["outputs"]["generator"]["null_rho"] == P.NULL_RHO
        elif f.name != MODELS:
            assert label_findings(doc) == [], f.name
            assert doc["outputs"]["windows"]["fit"]["last_year"] == 2006 and doc["outputs"]["windows"]["evaluation"]["first_year"] == 2007
    models = load(DERIVED / "C10" / MODELS)
    assert models["fit"]["simulator"]["rho_grid"] == list(P.RHO_GRID) and models["fit"]["simulator"]["series_lengths_years"] == [22, 40]
    assert [lt["id"] for lt in models["fit"]["loan_types"]] == LOAN_TYPES


def test_the_small_bake_validates_against_the_schemas(built) -> None:
    for vid, doc in built["variants"].items():
        assert schema_findings(f"data/derived/C10/{vid}.json", doc) == [], vid
        assert violations(doc) == [], vid
    assert schema_findings(f"data/derived/C10/{MODELS}", built["models"]) == []
    assert violations(built["models"]) == []


def test_the_provenance_pins_the_board_page_and_the_truth_statuses() -> None:
    sources = (DERIVED / "C10" / "SOURCES.txt").read_text(encoding="utf-8")
    for needle in (P.RAW["url"], f"bytes: {P.RAW['bytes']}", f"sha256: {P.RAW['sha256']}", f"retrieved: {P.RAW['retrieved']}",
                   f"as_of: {P.RAW['files_as_of']}", f"window_sha256: {P.RAW['window_sha256']}"):
        assert needle in sources, needle
    for vid in LOAN_TYPES:
        doc = load(DERIVED / "C10" / f"{vid}.json")
        prov = doc["provenance"]
        assert prov["truth_status"] == "real-outcomes" and prov["licence_classes"]["fed-chargeoff"] == "mirror-allowed"
        board = next(i for i in prov["inputs"] if i["source"] == "fed-chargeoff")
        assert board["files"] == [{"name": P.RAW["name"], "sha256": P.RAW["sha256"]}]
        assert prov["seed"] == 42 and prov["riskvalidation_version"] and prov["code_version"]
        assert doc["outputs"]["data_status"]["files_as_of"] == P.RAW["files_as_of"] and doc["outputs"]["data_status"]["table"] == "chgallsa"
    for vid in ("grid-22", "grid-40"):
        prov = load(DERIVED / "C10" / f"{vid}.json")["provenance"]
        assert prov["truth_status"] == "synthetic-known-truth" and prov["inputs"] == [] and prov["generators"] == [P.GENERATOR]
    assert (ROOT / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8").count("riskvalidation @ git+") == 1
