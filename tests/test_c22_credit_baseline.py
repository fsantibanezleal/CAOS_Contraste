"""U16-P2: C22 gains the p-value tests of the other seven families without moving one number of the five credit families.

The digests below were taken from the committed artifacts before U16-P2 touched C22 (engine 0.4.3, pipeline 0.07.000): for
each variant, the simulations of the credit families' tests with their rates, seeds and histograms, the generators they
use, the published reproductions, the exact curves, the estimators, the specimen, the credit findings and decision
numbers. The re-bake on the engine of U16 must reproduce every one of them (the provenance block, which names the
versions, and the manifest are not numbers and are left out)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"

#: the five families C22 measured before U16 (CT-301)
C22_CREDIT_FAMILIES = frozenset({"discrimination", "pd-calibration", "rating-system", "stability", "transitions"})
#: what U16-P2 adds to a document carries one of these prefixes, so the credit view leaves it out
NEW_PREFIXES = ("F-OTHER-", "other_")

#: sha256 of the canonical JSON of credit_view(document), its bilingual texts left out (numbers_only), per variant. Pinned at the
#: 1.00.000 release (2026-10-27) from the documents of 7db68ec (the U16-F4 pins, checked path by path against bd42589, the documents
#: before U16-P2) and equal on the re-baked documents: no rate, seed, histogram or count moved; the texts are reviewed by the Spanish
#: guard and the views, not by this digest.
BASELINE = {
    "broken-monotonicity": "8fc911616fe7cdbd0c0cde539f9c1364cc444f1963c70ea94152de1cd67659df",
    "clustering": "f276a5266a1a5416bb35113cc4758e833ade52e700cd41cc10b1bd295236dc2c",
    "concentration": "bbca530dc53888ddb9c2d87bbbbb9c772793674de62e0a765b3d814adf0bd2ce",
    "discrimination-decay": "5f52891afe717b684f8f7eda8ca60cbe129c494e97cd40f7474af6ecb95790e9",
    "drift": "ef001f02b3a053411b14ce5ac02d1aa27780d03b95afc36b62c3cbc191588677",
    "leakage": "f03b69868fbf4ca3cdf2364c6b9e2f577e2ff901ce2385e276e3ce4d4480944b",
    "miscalibration": "260b4f95a91e3dd6b49fa95574b3f7e611b83fa9bb50743d1220a044fc9e2b5d",
    "null": "ceb29a4e5e591f2bd90ea5fd1088425420c857872ec1a8526456cf898174dafe",
}


def credit_test_ids() -> frozenset[str]:
    import riskvalidation.validation  # noqa: F401  (registers every test)
    from riskvalidation.core.registry import catalogue

    return frozenset(s.test_id for s in catalogue() if s.decision == "p_value" and s.family in C22_CREDIT_FAMILIES)


def credit_view(doc: dict, credit_ids: frozenset[str] | None = None) -> dict:
    """The part of a C22 variant document that belongs to the credit families: everything U16-P2 adds is excluded."""
    ids = credit_ids if credit_ids is not None else credit_test_ids()
    o = doc["outputs"]
    # `study` is the block c22-variant 2.0.0 adds to every simulation (null for the credit families): a key, not a number
    sims = [{k: v for k, v in s.items() if k != "study"} for s in o["simulations"] if s["test_id"] in ids]
    used = {s["generator"] for s in sims}
    credit_panels = [p for p in o["panels"] if any(s["panel"] == p["id"] for s in sims)]
    keep = lambda key: not str(key).startswith(NEW_PREFIXES)  # noqa: E731
    return {
        "variant_id": doc["variant_id"],
        "ladder": o["ladder"] if doc["variant_id"] != "other-families" else None,
        "levels": o["levels"],
        "panels": credit_panels,
        "simulations": sims,
        "generators": {k: v for k, v in o["generators"].items() if k in used},
        "golden": o["golden"],
        "exact_curves": o["exact_curves"],
        "estimators": o["estimators"],
        "specimen": o["specimen"],
        "tests": doc["tests"],
        "impact": {k: v for k, v in doc["impact"].items() if keep(k)},
        # the generic red-row findings (F-RED-NN) are the pipeline's layer over the tests, tested in tests/test_u16_f12g_red_findings.py
        "findings": [f for f in doc["findings"] if keep(f["id"]) and not f["id"].startswith("F-RED-")],
    }


def numbers_only(obj):
    """The object with every bilingual text ({en, es}) left out: the baseline pins the numbers, never the wording of a label or a
    scenario, which the reader-text reviews change (U16-F11: log-odds in Spanish)."""
    if isinstance(obj, dict):
        if set(obj) == {"en", "es"}:
            return None
        return {k: numbers_only(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [numbers_only(x) for x in obj]
    return obj


def digest(view: dict) -> str:
    return hashlib.sha256(json.dumps(numbers_only(view), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _documents() -> dict[str, dict]:
    manifest = json.loads((DERIVED / "manifests" / "C22.json").read_text(encoding="utf-8"))
    return {a["variant_id"]: json.loads((DERIVED / a["path"]).read_text(encoding="utf-8"))
            for a in manifest["artifacts"] if a["role"] == "variant"}


@pytest.fixture(scope="module")
def documents() -> dict[str, dict]:
    return _documents()


def test_the_credit_families_numbers_are_those_of_the_baseline(documents):
    """The eight variants' credit-family numbers are byte-identical to the ones committed before U16-P2."""
    ids = credit_test_ids()
    assert len(ids) == 21
    for variant, expected in BASELINE.items():
        assert variant in documents, variant
        assert digest(credit_view(documents[variant], ids)) == expected, variant


def test_the_digest_detects_a_changed_number(documents):
    """The guard itself: a plant (one rejection count moved by one) changes the null variant's digest."""
    ids = credit_test_ids()
    doc = json.loads(json.dumps(documents["null"]))
    before = digest(credit_view(doc, ids))
    first = next(s for s in doc["outputs"]["simulations"] if s["test_id"] in ids)
    first["rates"]["p<0.05"]["rejections"] += 1
    assert digest(credit_view(doc, ids)) != before
    doc2 = json.loads(json.dumps(documents["null"]))
    doc2["outputs"]["simulations"][0]["seed"] += 1
    assert digest(credit_view(doc2, ids)) != before
