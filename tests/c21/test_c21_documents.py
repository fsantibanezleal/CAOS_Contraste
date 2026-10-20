"""CT-2111, CT-2112, CT-2114, CT-2117: the committed C21 documents, from the real bake."""
from __future__ import annotations

from pathlib import Path

import contract_schemas as cs
from c21_support import C21, DERIVED, MODELS, PAIRS, VARIANTS, all_documents, listing_problems, load, semantics, values

from pipeline.cases.c21 import legal

OUTCOME_CONDITIONED = ("fair.equalized_odds", "fair.equal_opportunity", "fair.calibration_within_groups", "fair.auc_by_group")
ALLOWLIST = {"fair.demographic_parity", "fair.adverse_impact", "fair.two_proportion_z", "fair.fisher_exact", "fair.conditional_disparity",
             "fair.rate_spread_disparity", "fair.replication", "fair.situation_testing"}
MANIFEST = DERIVED / "manifests" / "C21.json"


def problems(doc: dict, path: Path | None = None) -> list[str]:
    """Schema errors, then the semantic findings, of one committed document."""
    ref = cs.schema_for_document(path or (C21 / "x.json"), doc)
    out = list(cs.errors(ref, doc))
    if "pair_id" in doc.get("outputs", {}):
        out += semantics().check_c21(doc)
    return out


def test_every_committed_document_validates_passes_the_checks_and_is_listed_with_its_hash() -> None:
    docs = all_documents()
    assert set(docs) == {*VARIANTS, MODELS}
    for name, doc in docs.items():
        assert problems(doc, C21 / f"{name}.json") == [], name
        for row in doc["tests"] if "tests" in doc else []:
            assert cs.errors("common/test-result", row) == [], (name, row["test_id"])
    manifest = load(MANIFEST)
    entries = {e["variant_id"]: e for e in manifest["artifacts"]}
    assert set(entries) == {*VARIANTS, MODELS} and manifest["case_id"] == "C21" and manifest["default_variant"] == VARIANTS[-1]
    assert listing_problems(C21, manifest) == []
    for name in docs:
        path = C21 / f"{name}.json"
        assert entries[name]["path"] == f"C21/{name}.json" and entries[name]["bytes"] == path.stat().st_size
        if name != MODELS:
            assert entries[name]["models_ref"] == f"C21/{MODELS}.json" and entries[name]["truth_status"] == "real-outcomes"
    for name in VARIANTS:       # the rows whose light is not a p-value threshold carry their levels in extras and no alphas (estimates._segment)
        for row in load(C21 / f"{name}.json")["tests"]:
            if row["test_id"] in ("fair.conditional_disparity", "fair.rate_spread_disparity"):
                assert row["alpha_amber"] is None and row["alpha_red"] is None and row["extras"]["thresholds"]["interval_level"] == 0.95
                assert "interval_level=0.95" in row["policy_version"] and row["p_value"] is not None
            elif row["test_id"] == "fair.situation_testing":
                assert row["alpha_amber"] is None and row["alpha_red"] is None and row["extras"]["thresholds"]["amber"] == 0.2
            elif row["test_id"] in ("fair.two_proportion_z", "fair.fisher_exact"):
                assert (row["alpha_amber"], row["alpha_red"]) == (0.05, 0.01)
            else:
                assert row["alpha_amber"] is None and row["alpha_red"] is None
    assert manifest["sources"] == ["hmda"] and manifest["source_details"]["hmda"]["class"] == "mirror-allowed"
    assert manifest["contract"]["hmda"]["counts"]["rejected"] == 0 and manifest["expect"]
    for pid, name in zip(PAIRS, VARIANTS):
        o = docs[name]["outputs"]
        assert o["pair_id"] == pid and (o["fit_year"], o["confirm_year"]) == (int(pid[:4]), int(pid[:4]) + 1)
        assert docs[name]["provenance"]["riskvalidation_version"].endswith("+2a21c0b") and docs[name]["provenance"]["truth_status"] == "real-outcomes"


def test_no_outcome_conditioned_test_runs_and_only_the_allowlisted_ids_appear() -> None:
    for name, doc in all_documents().items():
        ids = {r["test_id"] for r in doc.get("tests", [])}
        assert ids <= ALLOWLIST, (name, ids - ALLOWLIST)
        assert not ids & set(OUTCOME_CONDITIONED)
        blob = str(doc.get("outputs", doc.get("fit")))
        for t in OUTCOME_CONDITIONED:
            assert t not in blob
        if name != MODELS:
            assert "target" not in doc["outputs"] and "y_true" not in blob                  # HMDA has no outcome
    for name in VARIANTS:
        ids = {r["test_id"] for r in load(C21 / f"{name}.json")["tests"]}
        assert ids == ALLOWLIST


def test_every_document_carries_the_label_and_the_legal_sentences() -> None:
    v = values()
    for name, doc in all_documents().items():
        block = (doc["outputs"] if name != MODELS else doc["fit"])["legal"]
        assert block["label"] == {"en": "no legal claim", "es": "sin afirmacion legal"}
        for key, quote in (("regulation_b", "reg_b"), ("fair_housing_act", "fha"), ("procedures", "procedures")):
            assert (block[key]["citation"], block[key]["quote"]) == tuple(v.QUOTES[quote]) and block[key]["text"]["en"] == block[key]["quote"]
        assert block["unconditional_rates_are"] == "indicators-only"
        assert block["controlled_disparity_is"] == "approximation-of-comparative-evidence" and block["is_a_finding_of_violation"] is False
        assert block == legal.legal_block()
        for row in doc.get("tests", []):
            assert "no legal claim" in row["notes"], (name, row["test_id"], row["segment"])
    quotes = " ".join(legal.QUOTES[k][1] for k in legal.QUOTES)
    assert "effects test" in quotes and "disparate-impact" in quotes and "Gross HMDA" in quotes
    assert "12 CFR 1002.6(a)" in legal.QUOTES["reg_b"][0] and "91 FR 21620" in legal.QUOTES["fha"][0]


def test_the_reference_groups_and_the_missing_outcome_are_labelled_in_every_document() -> None:
    """Review m5 and m6, decision G14: the reference group of each attribute is a convention, and the missing outcome has its sentence."""
    for name, doc in all_documents().items():
        conv = (doc["outputs"] if name != MODELS else doc["fit"])["conventions"]
        text = conv["group_exclusion"]["en"]
        assert "reference group" in text and "convention" in text and "customary comparison group" in text, name
        for ref in legal.REFERENCE.values():
            assert ref in text, (name, ref)
        assert "35-44" in text and "no source names a reference age band" in text
        assert "No outcome-conditioned test runs: public HMDA carries no loan outcome." in conv["outcome"]["note"]["en"]
        assert "No hay ninguna prueba condicionada al resultado" in conv["outcome"]["note"]["es"]
    assert legal.conventions_block() == (all_documents()[VARIANTS[0]]["outputs"]["conventions"])


def test_the_alphas_of_the_built_documents_are_the_engines_own(built) -> None:
    """Review m4: the alpha assertion of the committed documents, run on the documents of the planted bake too."""
    for name in built.order:
        for row in built.variants[name]["tests"]:
            if row["test_id"] in ("fair.conditional_disparity", "fair.rate_spread_disparity", "fair.situation_testing"):
                assert row["alpha_amber"] is None and row["alpha_red"] is None, (name, row["test_id"])
            elif row["test_id"] in ("fair.two_proportion_z", "fair.fisher_exact"):
                assert (row["alpha_amber"], row["alpha_red"]) == (0.05, 0.01), (name, row["test_id"])
            else:
                assert row["alpha_amber"] is None and row["alpha_red"] is None, (name, row["test_id"])


def test_the_licence_stays_unverified_and_quotes_the_platform_terms() -> None:
    v = values()
    for name, doc in all_documents().items():
        lic = (doc["outputs"] if name != MODELS else doc["fit"])["licence"]
        assert lic["status"] == "UNVERIFIED" and lic["platform_terms"] == v.HMDA_PLATFORM_TERMS and lic["modified_statement"] == v.HMDA_MODIFIED
        assert lic["platform_terms_cover"] == "the software package, not the published datasets"
        assert set(lic) == {"status", "platform_terms", "platform_terms_cover", "modified_statement", "note"}      # no data licence field
        assert "UNVERIFIED" in lic["note"]["en"]
    assert "UNVERIFIED" in load(MANIFEST)["source_details"]["hmda"]["licence"]
