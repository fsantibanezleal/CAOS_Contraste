"""CT-0211, CT-0216: the committed C02 documents, from the real bake."""
from __future__ import annotations

import contract_schemas as cs
from c02_support import C02, DERIVED, MODELS, VARIANTS, all_documents, committed, listing_problems, load, semantics

from pipeline.cases.c02 import conventions as cv

MANIFEST = DERIVED / "manifests" / "C02.json"


def problems(doc: dict, name: str) -> list[str]:
    ref = cs.schema_for_document(C02 / f"{name}.json", doc)
    out = list(cs.errors(ref, doc))
    if "kind" in doc.get("outputs", {}):
        out += semantics().check_c02(doc)
    return out


def test_every_committed_document_validates_passes_the_checks_and_is_listed_with_its_hash() -> None:
    docs = all_documents()
    assert set(docs) == {*VARIANTS, MODELS}
    for name, doc in docs.items():
        assert problems(doc, name) == [], name
        for row in doc.get("tests", []):
            assert cs.errors("common/test-result", row) == [], (name, row["test_id"])
            if row["light"] == "not_evaluated":
                assert row["statistic"] is None and row["p_value"] is None and row["metric"] is None
    manifest = load(MANIFEST)
    entries = {e["variant_id"]: e for e in manifest["artifacts"]}
    assert set(entries) == {*VARIANTS, MODELS} and manifest["case_id"] == "C02" and manifest["default_variant"] == "h1"
    assert listing_problems(C02, manifest) == []
    for name in docs:
        path = C02 / f"{name}.json"
        assert entries[name]["path"] == f"C02/{name}.json" and entries[name]["bytes"] == path.stat().st_size
        if name != MODELS:
            assert entries[name]["models_ref"] == f"C02/{MODELS}.json" and entries[name]["truth_status"] == "real-outcomes"
    assert manifest["sources"] == ["uci-polish"] and manifest["source_details"]["uci-polish"]["class"] == "mirror-allowed"
    assert manifest["contract"]["uci-polish"]["counts"]["rejected"] == 0 and manifest["expect"]
    counts = {h: committed(h)["outputs"]["counts"] for h in VARIANTS}
    assert [(counts[f"h{k}"]["rows"], counts[f"h{k}"]["events"]) for k in range(1, 6)] == [cv.expected_counts(k) for k in range(1, 6)]
    assert (counts["pooled"]["rows"], counts["pooled"]["events"]) == (43405, 2091)
    for h in VARIANTS:
        o = committed(h)["outputs"]
        assert o["parameters"] == cv.parameters() and o["requirements"] and all(r in {f"CT-02{n:02d}" for n in range(1, 19)} for r in o["requirements"])
        assert {r["rung"] for r in o["rungs"]} == {"P0", "P1", "P2a", "P2b", "P3", "P4"}


def test_no_out_of_time_claim_and_the_caveats_are_in_the_documents() -> None:
    for name in VARIANTS:
        doc = committed(name)
        o = doc["outputs"]
        assert o["split"]["out_of_time_claim"] is False and o["split"]["protocol"] == "locked-stratified-holdout"
        assert o["split"]["calibration_map_on_separate_slice"] and o["split"]["fit_on_training_slice_only"] and not o["split"]["resampling_before_calibration"]
        for block in ("transfer", "term_structure", "impact_detail"):
            assert o[block]["label"] == "exploratory", (name, block)
        ids = {f["id"]: f for f in doc["findings"]}
        assert "F-HORIZON-MAPPING" not in ids                    # decision G21: the mapping is a stated basis, not an open finding
        paper = ids["F-PAPER-READING"]
        assert paper["severity"] == "S4" and paper["status"] == "accepted" and paper["evidence"] == ["design:paper-reading-unverified"]
        assert "UNVERIFIED against Zieba, Tomczak and Tomczak 2016" in paper["title"]["en"]
        assert ids["F-NO-OUT-OF-TIME"]["status"] == "accepted" and ids["F-NO-OUT-OF-TIME"]["evidence"] == ["design:no-date"]
        text = str(doc["findings"]).lower()
        assert "out-of-time validation passed" not in text and "out of time validation passed" not in text
        if name == "pooled":
            assert o["firm_overlap_caveat"] == cv.OVERLAP_CAVEAT and "UNVERIFIED" in o["firm_overlap_caveat"]["en"]
            assert o["pooled"]["horizon_indicator"] is True and o["years"] is None and "F-FIRM-OVERLAP" in ids
        else:
            assert o["firm_overlap_caveat"] is None and o["pooled"] is None


def test_the_mapping_is_asserted_per_variant_and_stated_beside_the_horizon() -> None:
    """Decision G21: h{n} (n years ahead) reads the file {6-n}year; every document states the file beside its horizon."""
    from c02_support import MODELS

    models = committed(MODELS)["fit"]["files"]
    assert [(f["horizon_id"], f["years"], f["file"]) for f in models] == [(f"h{n}", n, f"{6 - n}year.arff") for n in range(1, 6)]
    for n in range(1, 6):
        doc = committed(f"h{n}")
        o = doc["outputs"]
        rows, events = cv.expected_counts(n)
        assert (o["horizon_id"], o["years"]) == (f"h{n}", n) and (o["counts"]["rows"], o["counts"]["events"]) == (rows, events)
        text = o["counts"]["event_definition"]
        assert f"{6 - n}year.arff" in text["en"] and f"{n} year" in text["en"] and f"{6 - n}year.arff" in text["es"]
        assert doc["outputs"]["firm_overlap_caveat"] is None
    pooled = committed("pooled")["outputs"]["pooled"]["files"]
    assert [(f["years"], f["file"]) for f in pooled] == [(n, f"{6 - n}year.arff") for n in range(1, 6)]
