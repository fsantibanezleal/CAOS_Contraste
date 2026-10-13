"""CT-1008, CT-1009, CT-1010, CT-1012: the committed documents of C09 validate, are listed with their hash, carry the known CCF
beside every estimate and say synthetic."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import c09_invariants as invariants

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import contract_schemas as cs  # noqa: E402

DERIVED = ROOT / "data" / "derived"
VARIANTS = tuple(f"level-{k}" for k in range(6))
MODELS = "models-generator.json"


def committed() -> list[Path]:
    return sorted((DERIVED / "C09").glob("*.json"))


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_every_committed_document_validates_and_is_listed_with_its_hash() -> None:
    files = committed()
    assert [f.name for f in files] == sorted([MODELS, *(f"{v}.json" for v in VARIANTS)])
    manifest = load(DERIVED / "manifests" / "C09.json")
    assert cs.errors("common/case-manifest", manifest) == []
    listed = {a["path"]: a for a in manifest["artifacts"]}
    sums = dict(reversed(line.split("  ", 1)) for line in (DERIVED / "C09" / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines())
    assert set(listed) == {f"C09/{f.name}" for f in files} == set(sums)
    for f in files:
        doc = load(f)
        ref = cs.schema_for_document(f, doc)
        assert ref in ("c09/models", "c09/variant-acceleration-level"), (f.name, ref)
        assert cs.errors(ref, doc) == [], f.name
        rel = f"C09/{f.name}"
        assert listed[rel]["bytes"] == f.stat().st_size, rel
        assert hashlib.sha256(f.read_bytes()).hexdigest() == sums[rel], rel
        assert doc["provenance"]["truth_status"] == "synthetic-known-truth" and listed[rel]["truth_status"] == "synthetic-known-truth"
    assert manifest["default_variant"] == "level-3" and manifest["case_id"] == "C09" and manifest["sources"] == []


def test_the_small_bake_validates_against_the_schemas(built) -> None:
    for vid, doc in built["variants"].items():
        ref = cs.schema_for_document(DERIVED / "C09" / f"{vid}.json", doc)
        assert ref == "c09/variant-acceleration-level" and cs.errors(ref, doc) == []
    ref = cs.schema_for_document(DERIVED / "C09" / MODELS, built["models"])
    assert ref == "c09/models" and cs.errors(ref, built["models"]) == []


def test_every_estimate_carries_its_known_truth_and_a_consistent_bias(built) -> None:
    docs = [(f.name, load(f)) for f in committed() if f.name != MODELS] + list(built["variants"].items())
    assert len(docs) == 12
    for name, doc in docs:
        out = doc["outputs"]
        assert invariants.known_truth(out) == [], name
        rows = out["ccf_by_design"]["rows"]
        assert {(r["design"], r["treatment"], r["estimator"]) for r in rows} == {
            (d, t, e) for d in ("fixed-horizon", "cohort", "variable-horizon")
            for t in ("none", "censor", "floor-cap", "bounded-scale") for e in ("mean", "pooled")}, name
        assert out["generator"]["true_ccf"]["flag"] == "in-range" and out["level"] == int(doc["variant_id"].split("-")[1])
        by = {(t["model_id"]): t for t in doc["tests"] if t["test_id"] == "lgd_ead.ccf_estimator_bias"}
        assert len(by) == len(rows), name
        for r in rows:
            t = by[f"ccf-{r['design']}-{r['treatment']}-{r['estimator']}"]
            assert t["extras"]["thresholds"]["tolerance"] == out["ccf_by_design"]["tolerance"]
            if t["metric"] is not None:
                assert abs(t["metric"] - r["bias"]) < 1e-6, (name, r["design"], r["treatment"])
    levels = [doc["outputs"]["generator"]["true_ccf"]["value"] for _, doc in docs[:6]]
    assert all(b > a for a, b in zip(levels, levels[1:], strict=False)), levels
    fit = built["models"]["fit"]
    assert [x["level"] for x in fit["levels"]] == [0, 1, 2, 3, 4, 5] and fit["generator"]["true_ccf"]["value"] == levels[0]


def test_the_ead_models_report_their_clipped_counts_and_the_backtest_flags_unclipped_predictions(built) -> None:
    docs = [load(f) for f in committed() if f.name != MODELS] + list(built["variants"].values())
    for doc in docs:
        out = doc["outputs"]
        models = {m["model_id"]: m for m in out["ead_models"]}
        direct = [m for m in models.values() if m["kind"] == "direct-ead"]
        assert len(direct) == 1 and isinstance(direct[0]["n_clipped_below"], int) and isinstance(direct[0]["n_clipped_above"], int)
        assert direct[0]["n_clipped_above"] > 0                                    # overlimit lines exist and are counted
        assert all(m["n_clipped_below"] is None for m in models.values() if m["kind"] != "direct-ead")
        rows = out["ead_backtest"]["rows"]
        assert {r["model_id"] for r in rows} == set(models) and out["ead_backtest"]["currency"] == "USD"
        edges = out["ead_backtest"]["bands"]
        for r in rows:
            assert abs(r["gap"] - (r["predicted_ead"] - r["realised_ead"])) < 1e-3 * max(1.0, abs(r["realised_ead"]))
            assert abs(r["relative_gap"] - r["gap"] / r["realised_ead"]) < 1e-6
            assert r["utilisation_lower"] in edges and r["utilisation_upper"] in edges
            if r["prediction_flag"] == "in-range":
                assert r["predicted_ead"] >= 0
        bt = {t["model_id"] for t in doc["tests"] if t["test_id"] == "lgd_ead.ead_backtest_by_band"}
        assert bt == set(models)
    flags = {r["prediction_flag"] for doc in docs for r in doc["outputs"]["ead_backtest"]["rows"] if r["model_id"] == "utilisation-change"}
    assert "outside-range" in flags                                                # the unclipped utilisation-change prediction is flagged


def test_no_text_presents_the_generated_lines_as_real_data(built) -> None:
    docs = [built["models"], *built["variants"].values(), *(load(f) for f in committed())]
    for d in docs:
        assert invariants.synthetic(d) == []
    page = (ROOT / "docs" / "cases" / "C09.md").read_text(encoding="utf-8")
    assert "synthetic" in page.lower() and "Federal Reserve" in page
    assert not re.search(r"(these|the) (lines|accounts|cards) (are|were) real", page, re.IGNORECASE)
    assert all("not observations" in d["outputs"]["generator"]["notice"]["en"] for d in built["variants"].values())
