"""CT-0214: the engine is pinned by the release tag that the SDD technology row names, and every document names its release."""
from __future__ import annotations

from c02_support import ROOT, all_documents

from engine_pin import engine_pin_findings

PIN, RELEASE = "v0.08.001", "0.8.1"


def test_the_engine_is_pinned_at_the_release_tag_that_the_sdd_names() -> None:
    req = (ROOT / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    sdd = (ROOT / "docs" / "design" / "SDD.md").read_text(encoding="utf-8")
    assert engine_pin_findings(req, sdd) == []
    assert f"CAOS_RiskValidation.git@{PIN}" in req and f"| engine | riskvalidation | {PIN} |" in sdd
    for name, doc in all_documents().items():
        assert doc["provenance"]["riskvalidation_version"] == RELEASE, name
        assert doc["provenance"]["truth_status"] == "real-outcomes" and doc["provenance"]["inputs"][0]["source"] == "uci-polish"
