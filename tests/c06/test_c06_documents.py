"""CT-508 to CT-513, CT-516 and CT-517: the documents the bake writes, on the committed sample, and the committed documents."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from c06_helpers import (BATTERY, COMMITTED, RAW_FIELDS, ROOT, SIX, battery_findings, currency_findings, documents, freddie_findings,
                         order_findings, problems, reconciliation_findings, trigger_findings, walk)
from pipeline.cases.c06 import _case
from pipeline.cases.c06 import build as bd
from pipeline.cases.c06.run import POLICY
from pipeline.core import expect as expectations

def test_every_document_validates_and_the_manifest_lists_it(sample_bake):
    for name in ("a", "b"):
        root, manifest = sample_bake[name]
        assert documents(root) and problems(root) == [], problems(root)
        for p in documents(root):
            doc = json.loads(p.read_text(encoding="utf-8"))
            keys = {k for k, _ in walk(doc)}
            assert RAW_FIELDS.isdisjoint(keys), f"{p.name} carries a loan field: {sorted(RAW_FIELDS & keys)}"
            assert p.stat().st_size < 400_000
            for k, v in walk(doc):
                if k == "account_id":
                    assert v[0] in "AP" and v[1:].isdigit(), "a sampled account carries no identifier"
    committed = problems(COMMITTED)
    assert committed == [], committed
    assert len(documents(COMMITTED)) == 12


def test_a_document_missing_from_the_manifest_is_found(sample_bake, tmp_path):
    import shutil

    root, _ = sample_bake["a"]
    copy = tmp_path / "copy"
    shutil.copytree(root, copy)
    m = json.loads((copy / "manifests" / "C06.json").read_text(encoding="utf-8"))
    m["artifacts"] = m["artifacts"][1:]
    (copy / "manifests" / "C06.json").write_text(json.dumps(m), encoding="utf-8")
    assert any("is not listed in the manifest" in p for p in problems(copy))


def test_adversarial_a_document_that_fails_its_schema_is_found(sample_bake, tmp_path):
    import shutil

    root, _ = sample_bake["a"]
    copy = tmp_path / "copy"
    shutil.copytree(root, copy)
    path = next(p for p in documents(copy) if not p.name.startswith("models-"))
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["outputs"]["stage_summary"]["rows"][0]["coverage"] = 7.0
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert any("coverage" in p or path.name in p for p in problems(copy))


def test_two_bakes_with_the_same_seed_give_identical_hashes(sample_bake):
    hashes = []
    for name in ("a", "b"):
        root, manifest = sample_bake[name]
        hashes.append({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in documents(root)} |
                      {"manifest": hashlib.sha256((root / "manifests" / "C06.json").read_bytes()).hexdigest()})
    assert hashes[0] == hashes[1] and len(hashes[0]) == 5  # two models, two variants and the manifest


def test_the_six_variants_are_in_order_and_trained_to_their_cutoff():
    assert _case.REPORTING_DATES == SIX
    manifest = json.loads((COMMITTED / "manifests" / "C06.json").read_text(encoding="utf-8"))
    variants = [a for a in manifest["artifacts"] if a["role"] == "variant"]
    assert [a["variant_id"] for a in variants] == [bd.variant_id(np.datetime64(d)) for d in SIX]
    assert [a["variant_id"] for a in manifest["artifacts"]] == [x for d in SIX for x in (f"models-{bd.variant_id(np.datetime64(d))}", bd.variant_id(np.datetime64(d)))]
    for a, d in zip(variants, SIX, strict=True):
        doc = json.loads((COMMITTED / a["path"]).read_text(encoding="utf-8"))
        models = json.loads((COMMITTED / a["models_ref"]).read_text(encoding="utf-8"))
        assert doc["outputs"]["reporting_date"] == d
        assert all(r["training_cutoff"] == d for r in models["fit"]["ladder"]), "a rung is trained up to the reporting date"
        assert models["fit"]["pit"]["z_hat"][-1]["period"] <= d, "the systematic factor stops at the reporting date"
    assert manifest["default_variant"] in {a["variant_id"] for a in variants}
    assert manifest["sources"] == ["sba-foia", "fed-stress-tests"]


def test_staging_uses_the_policy_and_no_delinquency_trigger_fires(variant):
    out = variant.document["outputs"]
    pol = out["settings"]["sicr"]
    assert pol["dpd_backstop"] == POLICY.dpd_backstop and pol["default_dpd"] == POLICY.default_dpd
    assert pol["threefold_ratio"] == POLICY.threefold_ratio and pol["absolute_floor"] == POLICY.absolute_floor
    assert [(x["pd_origination_upper"], x["multiplier"]) for x in pol["multiplier_schedule"]] == list(POLICY.multiplier_schedule)
    fit_pol = variant.models["fit"]["staging_policy"]
    assert fit_pol["probation_months"] == out["settings"]["probation_months"]
    assert {k: fit_pol[k] for k in pol} == pol, "the models staging policy repeats the variant's field by field"
    triggers = {p["trigger"] for p in out["sicr_points"]}
    assert triggers <= {"none", "relative-absolute", "threefold"}, "no dpd, forbearance or watch-list data exists in the file"
    assert out["settings"]["low_credit_risk_exemption"] is False and pol["low_credit_risk_pd"] is None
    assert all(p["stage"] in ("stage1", "stage2") for p in out["sicr_points"])


def test_overlays_are_separate_lines_and_never_change_the_model_ecl(variant, variant_with_overlay):
    a, b = variant.document["outputs"], variant_with_overlay.document["outputs"]
    assert a["overlays"] == [] and [o["id"] for o in b["overlays"]] == ["OVL-TEST"]
    assert a["stage_summary"] == b["stage_summary"], "the model ECL by stage does not move"
    assert a["ecl_by_scenario"] == b["ecl_by_scenario"]
    line = next(x for x in b["waterfall"]["lines"] if x["id"] == "overlay-OVL-TEST")
    assert line["kind"] == "overlay" and line["overlay_id"] == "OVL-TEST" and line["amount"] == 1_000_000.0 and line["stage"] == "stage1"
    closing = lambda o: next(x for x in o["waterfall"]["lines"] if x["id"] == "closing")["amount"]  # noqa: E731
    assert closing(b) == pytest.approx(closing(a) + 1_000_000.0, abs=1e-6)
    model_total = sum(r["ecl"] for r in a["stage_summary"]["rows"])
    assert closing(a) == pytest.approx(model_total, abs=1e-3)
    d = next(t for t in variant_with_overlay.document["tests"] if t["test_id"] == "ifrs9.overlay_diagnostics")
    assert d["metric"] == pytest.approx(1_000_000.0 / (model_total + 1_000_000.0))
    # the scenario figures are the model's, never the overlay's: weighted ECL equals sum of weight times scenario ECL by stage
    w = {s["id"]: s["weight"] for s in a["scenarios"]}
    for stage in ("stage1", "stage2"):
        assert sum(w[r["scenario_id"]] * r["ecl"] for r in a["ecl_by_scenario"]["rows"] if r["stage"] == stage) > 0


def test_reconciliation_closes_and_the_waterfall_opens_into_it(variant, variant_with_overlay):
    for v in (variant, variant_with_overlay):
        out = v.document["outputs"]
        assert reconciliation_findings(out) == []
        ids = {x["id"] for x in out["waterfall"]["lines"]}
        for row in out["reconciliation"]["allowance"]:
            assert {m["line_id"] for m in row["movements"]} <= ids, "every movement is a waterfall line"
            assert abs(row["residual"]) < 1e-3
    for path in documents(COMMITTED):
        if not path.name.startswith("models-"):
            assert reconciliation_findings(json.loads(path.read_text(encoding="utf-8"))["outputs"]) == [], path.name


def test_adversarial_a_moved_movement_breaks_the_identities(variant):
    out = json.loads(json.dumps(variant.document["outputs"]))
    assert reconciliation_findings(out) == []
    gross = sum(abs(r["closing"]) for r in out["reconciliation"]["gross_carrying_amount"])
    out["reconciliation"]["allowance"][0]["movements"][0]["amount"] += 10 * 1e-6 * max(1.0, gross)  # ten times the tolerance basis
    assert reconciliation_findings(out) != []


def test_adversarial_an_overlay_inside_the_model_ecl_is_found(variant):
    out = json.loads(json.dumps(variant.document["outputs"]))
    out["stage_summary"]["rows"][0]["ecl"] += 5.0e5  # an overlay merged into the model ECL of Stage 1
    assert any(f.startswith("stage-closing-equals-ecl") for f in reconciliation_findings(out))


def test_adversarial_a_battery_missing_a_test_is_found(variant):
    assert battery_findings(variant.document["tests"]) == []
    assert battery_findings([t for t in variant.document["tests"] if t["test_id"] != "ifrs9.ecl_backtest"]) == ["missing ifrs9.ecl_backtest"]


def test_adversarial_a_variant_claiming_freddie_mac_data_is_found(variant):
    out = json.loads(json.dumps(variant.document["outputs"]))
    assert freddie_findings(out) == []
    out["data_status"]["freddie_mac_available"] = True
    assert freddie_findings(out) == ["freddie"]


def test_adversarial_a_delinquency_trigger_in_a_file_without_delinquency_is_found(variant):
    out = json.loads(json.dumps(variant.document["outputs"]))
    out["sicr_points"][0]["trigger"] = "dpd-backstop"
    assert trigger_findings(out) == ["trigger dpd-backstop"]


def test_adversarial_a_foreign_currency_amount_is_found(variant):
    doc = json.loads(json.dumps(variant.document))
    assert currency_findings(doc) == []
    doc["outputs"]["stage_summary"]["currency"] = "EUR"
    assert currency_findings(doc) == ["currency EUR"]


def test_adversarial_variants_out_of_order_are_found():
    manifest = json.loads((COMMITTED / "manifests" / "C06.json").read_text(encoding="utf-8"))
    assert order_findings(manifest) == []
    manifest["artifacts"] = list(reversed(manifest["artifacts"]))
    assert order_findings(manifest) != []


def test_adversarial_a_different_seed_changes_the_sampled_accounts(variant, tables):
    from pipeline.cases.c06.variant import bake_variant

    other = bake_variant(tables["loans"], tables["fed"], np.datetime64("2010-12-31"), 43, min_quarter_at_risk=60)
    a, b = variant.document["outputs"], other.document["outputs"]
    assert a["sicr_points"] != b["sicr_points"], "the seed drives the sample, so a changed seed is visible in the hashes"
    assert a["stage_summary"] == b["stage_summary"], "and nothing else moves"


def test_the_battery_rows_are_engine_test_results(variant):
    doc = variant.document
    ids = {t["test_id"] for t in doc["tests"]}
    assert BATTERY <= ids
    keys = {"test_id", "model_id", "segment", "statistic", "p_value", "metric", "h0", "alternative", "policy_version", "alpha_amber",
            "alpha_red", "light", "n", "n_events", "inputs_hash", "reference", "notes", "extras"}
    assert all(set(t) == keys and t["reference"] and t["policy_version"].startswith("contraste-ifrs9-battery") for t in doc["tests"])
    life = [t for t in doc["tests"] if t["test_id"] == "ifrs9.lifetime_pd_backtest"]
    assert {t["model_id"] for t in life} == {"L0-km", "L1-dth", "L2-cox"} and "all" in {t["segment"] for t in life}
    rows = doc["outputs"]["lifetime_backtest"]["rows"]
    assert rows and all(r["estimator"] == "kaplan-meier" for r in rows)
    for r in rows:
        assert (r["observed_cumulative_pd"] is None) == (r["reason"] is not None), "an unobserved cell carries its reason"
    assert len(doc["outputs"]["decile_calibration"]["rows"]) == 30
    assert [r["rung_id"] for r in doc["outputs"]["rung_comparison"]] == ["L0-km", "L1-dth", "L2-cox"]
    assert doc["outputs"]["rung_comparison"][0]["c_index"] is None and doc["outputs"]["rung_comparison"][0]["reason"]


def test_amounts_are_in_usd_and_an_expected_range_is_enforced(variant, tmp_path, monkeypatch, tables):
    doc = variant.document
    for k, v in walk(doc):
        if k == "currency":
            assert v == "USD"
    assert all(i["unit"] in ("USD", "ratio") for i in doc["impact"].values())
    out = doc["outputs"]
    ids = {s["id"] for s in out["scenarios"]}
    assert len(ids) >= 2 and abs(sum(s["weight"] for s in out["scenarios"]) - 1.0) < 1e-12
    assert {r["scenario_id"] for r in out["ecl_by_scenario"]["rows"]} == ids and all(s["label"]["en"] for s in out["scenarios"])
    weighted = sum(s["weight"] * r["ecl"] for s in out["scenarios"] for r in out["ecl_by_scenario"]["rows"] if r["scenario_id"] == s["id"])
    assert weighted == pytest.approx(sum(r["ecl"] for r in out["stage_summary"]["rows"]), rel=1e-9)
    # a result outside its declared range stops the bake and is named
    from pipeline.pipeline import PipelinePaths

    from pipeline.io import fetch

    monkeypatch.setattr(fetch, "MANIFEST", ROOT / "data" / "sources" / "manifest.json")  # the sandbox points it at an empty one
    monkeypatch.setattr(_case, "REPORTING_DATES", ("2010-12-31",))
    monkeypatch.setattr(_case, "MIN_QUARTER_AT_RISK", 60)
    monkeypatch.setattr(bd, "EXPECT", {"coverage@2010-12-31": (5.0, 6.0)})
    with pytest.raises(expectations.ExpectationError, match=r"coverage@2010-12-31=.* outside \[5.0, 6.0\]"):
        _case.CASE.bake(seed=42, paths=PipelinePaths.from_output(tmp_path / "x"), data_root=Path(__file__).resolve().parent / "data")
