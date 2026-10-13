"""CT-808 to CT-811: the documents the bake writes (producer test of ``c03-outputs`` and ``c03-models``), on the committed sample,
and the documents as committed."""
from __future__ import annotations

import hashlib
import json
import shutil

import pytest

from pipeline.cases.c03 import _case, windows
from pipeline.core import expect as expectations

from .helpers import (COHORT_IDS, COMMITTED, RAW_FIELDS, currency_findings, documents, order_findings, problems, walk)


def _variants(root):
    return [json.loads(p.read_text(encoding="utf-8")) for p in documents(root) if not p.name.startswith("models-")]


def test_every_document_validates_and_the_manifest_lists_it(sample_bake):
    for name in ("a", "b"):
        root, manifest = sample_bake[name]
        assert documents(root) and problems(root) == [], problems(root)
        assert {a["role"] for a in manifest["artifacts"]} == {"models", "variant"}
        for p in documents(root):
            doc = json.loads(p.read_text(encoding="utf-8"))
            keys = {k for k, _ in walk(doc)}
            assert RAW_FIELDS.isdisjoint(keys), f"{p.name} carries a loan field: {sorted(RAW_FIELDS & keys)}"
            assert currency_findings(doc) == []
            assert p.stat().st_size < 1_000_000
    committed = problems(COMMITTED)
    assert committed == [], committed
    assert len(documents(COMMITTED)) == 6  # one models document and five variants


def test_a_sample_variant_states_the_training_window_of_its_cohort(sample_bake):
    root, _ = sample_bake["a"]
    models = json.loads((root / "C03" / "models-sba-7a.json").read_text(encoding="utf-8"))
    by_id = {w["id"]: w for w in models["fit"]["cohort_windows"]}
    for doc in _variants(root):
        o = doc["outputs"]
        assert o["training"] == by_id[o["cohort"]["id"]]["training"]
        assert o["training"]["last_fy"] <= o["cohort"]["first_fy"] - 6
        assert o["currency"] == "USD" and doc["provenance"]["truth_status"] == "real-outcomes"


def test_adversarial_a_document_that_fails_its_schema_is_found(sample_bake, tmp_path):
    root, _ = sample_bake["a"]
    copy = tmp_path / "copy"
    shutil.copytree(root, copy)
    assert problems(copy) == []
    path = next(p for p in documents(copy) if not p.name.startswith("models-"))
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["outputs"]["vintage_summary"]["rows"][0]["predicted_5y_pd"] = 1.0
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert any(path.name in p for p in problems(copy))
    m = json.loads((copy / "manifests" / "C03.json").read_text(encoding="utf-8"))
    m["artifacts"] = m["artifacts"][1:]
    (copy / "manifests" / "C03.json").write_text(json.dumps(m), encoding="utf-8")
    assert any("is not listed in the manifest" in p for p in problems(copy))


def test_two_bakes_with_the_same_seed_give_identical_hashes(sample_bake):
    hashes = []
    for name in ("a", "b"):
        root, _ = sample_bake[name]
        hashes.append({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in documents(root)} |
                      {"manifest": hashlib.sha256((root / "manifests" / "C03.json").read_bytes()).hexdigest()})
    assert hashes[0] == hashes[1] and len(hashes[0]) == 3  # one models document, one variant and the manifest


def test_adversarial_a_different_seed_changes_the_documents(tables, cohort_2008):
    from pipeline.cases.c03 import fit

    window = windows.training_window(cohort_2008)
    a = fit.fit_window(tables["loans"], window, 42, min_events=10**9)
    b = fit.fit_window(tables["loans"], window, 43, min_events=10**9)
    c = fit.fit_window(tables["loans"], window, 42, min_events=10**9)
    assert a.X_fit.equals(c.X_fit) and a.X_cal.equals(c.X_cal), "one seed, one sample"
    assert not a.X_fit.equals(b.X_fit), "the seed reaches the sampled training rows"


def test_the_five_variants_are_in_order_and_each_carries_its_own_window():
    manifest = json.loads((COMMITTED / "manifests" / "C03.json").read_text(encoding="utf-8"))
    variants = [a for a in manifest["artifacts"] if a["role"] == "variant"]
    assert [a["variant_id"] for a in variants] == list(COHORT_IDS)
    assert [a["variant_id"] for a in manifest["artifacts"]][0] == "models-sba-7a"
    models = json.loads((COMMITTED / "C03" / "models-sba-7a.json").read_text(encoding="utf-8"))
    assert [w["id"] for w in models["fit"]["cohort_windows"]] == list(COHORT_IDS)
    for a, c in zip(variants, windows.COHORTS, strict=True):
        doc = json.loads((COMMITTED / a["path"]).read_text(encoding="utf-8"))
        o = doc["outputs"]
        w = next(x for x in models["fit"]["cohort_windows"] if x["id"] == c.id)
        assert o["training"] == w["training"]
        assert (o["cohort"]["first_fy"], o["cohort"]["last_fy"]) == (c.first_fy, c.last_fy)
        assert w["training"]["last_fy"] == c.first_fy - 6 and w["training"]["cutoff_date"] == f"{c.first_fy - 1}-09-30"
        assert w["training"]["crisis_included"] == (c.first_fy >= 2011)
        assert a["models_ref"] == "C03/models-sba-7a.json" and doc["provenance"]["code_version"]
        for r in o["rung_comparison"]:
            for k in ("auc", "brier"):
                assert r[k] is None or 0.0 <= r[k] <= 1.0
        for vc in o["vintage_curves"]:
            assert all(0.0 < p < 1.0 for p in vc["predicted_cumulative_pd"])
        # every mark of the committed cohorts is observed at the files' as-of date (2026-06-30)
        assert all(r["mark_observed"] for r in o["vintage_summary"]["rows"])
        assert o["data_status"]["files_as_of"] == "2026-06-30"
    assert order_findings([a["variant_id"] for a in variants]) == []


def test_adversarial_variants_out_of_order_are_found():
    assert order_findings(list(reversed(COHORT_IDS))) != []
    assert order_findings(list(COHORT_IDS)) == []


def test_an_expected_range_is_enforced(sample_bake):
    root, manifest = sample_bake["a"]
    assert manifest["expect"], "the manifest carries the ranges"
    assert set(manifest["expect"]) == {"observed_5y_pd@fy2008-10"}
    committed = json.loads((COMMITTED / "manifests" / "C03.json").read_text(encoding="utf-8"))
    assert {"observed_5y_pd@fy2006-07", "training_event_rate@fy2018-20"} <= set(committed["expect"])
    assert set(committed["expect"]) == set(_case.EXPECT)
    for name, (lo, hi) in _case.EXPECT.items():
        assert lo < hi, name


def test_adversarial_a_value_outside_its_expected_range_is_found():
    values = {"observed_5y_pd@fy2006-07": 0.04}
    with pytest.raises(expectations.ExpectationError, match="observed_5y_pd@fy2006-07"):
        expectations.check("C03", {"observed_5y_pd@fy2006-07": _case.EXPECT["observed_5y_pd@fy2006-07"]}, values)
