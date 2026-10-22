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

#: sha256 of the canonical JSON of credit_view(document), per variant, from the artifacts before U16-P2. Re-pinned at U16-F4 (2026-10-22): the
#: only change is the last binary digit of the generators' exact truth.auc_model (about 1e-16, riskvalidation 1.0 on the bake host); checked
#: path by path against the documents of bd42589, no rate, seed, histogram or count moved.
BASELINE = {
    "broken-monotonicity": "1353430545beba524d04b5869e8006e4348be47e083f54d7645408a99a9aa986",
    "clustering": "14ef54b5b8e450ba644850964f444fcf00b383a664300974e59c12af1a7e412f",
    "concentration": "b854fa1e8ab1455aba25c2152dd1da0c1ee2a46512254eddaad2ac12254ff37f",
    "discrimination-decay": "0a7f17d26796dee90bb8f615ba72f06e0bf4ed4856d5480f13a0564287582f02",
    "drift": "46a6974a98addf80803a775db2edbbb09f7e69e96523b732b6b98870267255b4",
    "leakage": "ad0ce3fdfb19516b3cbab87dd3ff99cb7761ff6033410c2c2f4a5db614fac1e1",
    "miscalibration": "bbeb3090c2bb034cf8892b4814d2a7be771d39fc93f5c3b8b2f212dd7195621f",
    "null": "538b97efd13b301c0af4ad4552f999fbe8c3159b548896c75e22af2a739a30eb",
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
        "findings": [f for f in doc["findings"] if keep(f["id"])],
    }


def digest(view: dict) -> str:
    return hashlib.sha256(json.dumps(view, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


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
