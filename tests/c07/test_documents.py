"""CT-709, CT-713: the committed documents of C07 validate, are listed with their hash, and say synthetic."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import contract_schemas as cs  # noqa: E402
import invariants  # noqa: E402

DERIVED = ROOT / "data" / "derived"
VARIANTS = ("base", "recession", "consumer-arrears-shock", "house-price-fall", "uf-inflation-spike", "combined-severe")


def committed() -> list[Path]:
    return sorted((DERIVED / "C07").glob("*.json"))


def test_every_committed_document_validates_and_is_listed_with_its_hash() -> None:
    files = committed()
    assert [f.name for f in files] == sorted(["models-banco-andino.json", *(f"{v}.json" for v in VARIANTS)])
    manifest = json.loads((DERIVED / "manifests" / "C07.json").read_text(encoding="utf-8"))
    assert cs.errors("common/case-manifest", manifest) == []
    listed = {a["path"]: a for a in manifest["artifacts"]}
    sums = dict(reversed(line.split("  ", 1)) for line in (DERIVED / "C07" / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines())
    assert set(listed) == {f"C07/{f.name}" for f in files} == set(sums)
    for f in files:
        doc = json.loads(f.read_text(encoding="utf-8"))
        ref = cs.schema_for_document(f, doc)
        assert ref in ("c07/models", "c07/variant-three-regime"), (f.name, ref)
        assert cs.errors(ref, doc) == [], f.name
        rel = f"C07/{f.name}"
        assert listed[rel]["bytes"] == f.stat().st_size, rel
        assert hashlib.sha256(f.read_bytes()).hexdigest() == sums[rel], rel
        assert doc["provenance"]["truth_status"] == "synthetic-calibrated" and listed[rel]["truth_status"] == "synthetic-calibrated"
    assert manifest["default_variant"] == "base" and manifest["case_id"] == "C07" and manifest["sources"] == []
    for f in files:
        if f.name != "models-banco-andino.json":
            doc = json.loads(f.read_text(encoding="utf-8"))
            assert invariants.all_variant(doc["outputs"]) == [], f.name


def test_the_small_bake_validates_against_the_schemas(built) -> None:
    for sid, doc in built["variants"].items():
        ref = cs.schema_for_document(ROOT / "data" / "derived" / "C07" / f"{sid}.json", doc)
        assert ref == "c07/variant-three-regime" and cs.errors(ref, doc) == []
    ref = cs.schema_for_document(ROOT / "data" / "derived" / "C07" / "models-banco-andino.json", built["models"])
    assert ref == "c07/models" and cs.errors(ref, built["models"]) == []


def test_no_text_presents_banco_andino_as_a_real_bank(built) -> None:
    docs = [built["models"], *built["variants"].values()]
    for d in docs:
        assert invariants.synthetic(d) == []
    for f in committed():
        assert invariants.synthetic(json.loads(f.read_text(encoding="utf-8"))) == [], f.name
    page = (ROOT / "docs" / "cases" / "C07.md").read_text(encoding="utf-8")
    assert "synthetic" in page.lower() and "Banco Andino" in page
    assert not re.search(r"Banco Andino (is|es) (a )?(real|un banco real)", page)
    for pattern in (r"real bank's", r"audits? (a |the )?bank"):
        assert not re.search(pattern, page.lower()) or "not" in page.lower()
    fit = built["models"]["fit"]
    assert fit["bank"]["synthetic"] is True and "not a real bank" in fit["bank"]["notice"]["en"] or "generated bank" in fit["bank"]["notice"]["en"]
    assert fit["bank"]["name"] == "Banco Andino"


def test_the_models_document_holds_every_b1_cell_and_the_engine_tables(built) -> None:
    fit = built["models"]["fit"]
    tables = {t["table_id"]: t for t in fit["b1_tables"]}
    assert len(tables["mortgage-pe"]["cells"]) == 20 and len(tables["consumer-pi"]["cells"]) == 16
    assert len(tables["individual-categories"]["cells"]) == 10
    cell = next(c for c in tables["mortgage-pe"]["cells"] if c["row"] == "40<pvg<=80" and c["column"] == "0")
    assert (cell["pi"], cell["pdi"], cell["pe"]) == pytest.approx((0.019158, 0.021955, 0.000421))
    assert [c["category"] for c in fit["b1_default_categories"]] == ["C1", "C2", "C3", "C4", "C5", "C6"]
    assert fit["b1_default_categories"][-1]["tpe_upper"] is None
    assert fit["bde"]["doubtful_bucket_upper_days"] == [183, 274, 365, 457, 548, 639, None]
    segs = {s["segment"]: s for s in fit["bde"]["normal_coverage"]}
    assert segs["B.1.1"]["normal"] == 0.007 and segs["B.2.1"]["normal"] == 0.010
    assert {s["bde_segment"] for s in fit["segments"]} == {"B.1.1", "B.1.2", "B.2", "B.2.1", "A.2.2", "A.2.1"}
