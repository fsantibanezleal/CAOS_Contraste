"""CT-906, CT-910, CT-913 to CT-915 and CT-917: the documents the bake writes, on the committed sample, and the committed documents."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from c08_helpers import (COHORT_IDS, COMMITTED, RAW_FIELDS, ROOT, VARIANT_IDS, currency_findings, documents, freddie_findings,
                         order_findings, out_of_time_findings, problems, result_row_findings, walk)

from pipeline.cases.c08 import _case, panel
from pipeline.cases.c08 import build as bd
from pipeline.core import expect as expectations
from pipeline.core.schemas import SchemaViolation, validate_document
from pipeline.io import sba as readers

DATA = Path(__file__).resolve().parent / "data"
RUNG_IDS = ["L1-ols", "L2-fractional-logit", "L3-beta", "L4-hurdle", "L5-gradient-boosted", "L6-tobit",
            "L7-random-forest", "L8-neural-network"]


def _committed_manifest():
    return json.loads((COMMITTED / "manifests" / "C08.json").read_text(encoding="utf-8"))


def test_every_document_validates_and_the_manifest_lists_it(sample_bake):
    for name in ("a", "b"):
        root, manifest = sample_bake[name]
        assert documents(root) and problems(root) == [], problems(root)
        assert len(documents(root)) == 12 and manifest["sources"] == ["sba-foia"]
        for p in documents(root):
            doc = json.loads(p.read_text(encoding="utf-8"))
            keys = {k for k, _ in walk(doc)}
            assert RAW_FIELDS.isdisjoint(keys), f"{p.name} carries a loan field: {sorted(RAW_FIELDS & keys)}"
            assert p.stat().st_size < 400_000
    committed = problems(COMMITTED)
    assert committed == [], committed
    assert len(documents(COMMITTED)) == 12


def test_a_document_missing_from_the_manifest_is_found(sample_bake, tmp_path):
    import shutil

    root, _ = sample_bake["a"]
    copy_ = tmp_path / "copy"
    shutil.copytree(root, copy_)
    m = json.loads((copy_ / "manifests" / "C08.json").read_text(encoding="utf-8"))
    m["artifacts"] = m["artifacts"][1:]
    (copy_ / "manifests" / "C08.json").write_text(json.dumps(m), encoding="utf-8")
    assert any("is not listed in the manifest" in p for p in problems(copy_))


def test_adversarial_a_document_that_fails_its_schema_is_found(docs, tmp_path):
    import shutil

    root = docs["root"]
    copy_ = tmp_path / "copy"
    shutil.copytree(root, copy_)
    path = copy_ / "C08" / "dc-2009-10.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["outputs"]["lgd_distribution"]["mean"] = {"value": 1.3, "flag": "in-range"}   # above one without its flag
    path.write_text(json.dumps(doc), encoding="utf-8")
    found = problems(copy_)
    assert found and any("dc-2009-10" in p for p in found)
    with pytest.raises(SchemaViolation):
        validate_document("data/derived/C08/dc-2009-10.json", doc)


def test_two_bakes_with_the_same_seed_give_identical_hashes(sample_bake):
    hashes = []
    for name in ("a", "b"):
        root, _ = sample_bake[name]
        hashes.append({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in documents(root)} |
                      {"manifest": hashlib.sha256((root / "manifests" / "C08.json").read_bytes()).hexdigest()})
    assert hashes[0] == hashes[1] and len(hashes[0]) == 13  # six models, six variants and the manifest


def test_adversarial_a_different_seed_changes_the_boosted_predictions(tables):
    from pipeline.cases.c08 import cutoff as C
    from pipeline.cases.c08.ladder import fit_ladder

    d = tables["defaults"]
    train = d.take(C.training_mask(d, "2008-12-31"))
    a, b, c = (fit_ladder(train.design(), train.y, "2008-12-31", s) for s in (1, 1, 2))
    x = d.take(d.year >= 2009).design()
    boosted = "L5-gradient-boosted"
    assert np.array_equal(a.predict(a.rungs[boosted], x), b.predict(b.rungs[boosted], x))
    assert not np.array_equal(a.predict(a.rungs[boosted], x), c.predict(c.rungs[boosted], x))
    assert np.array_equal(a.rungs["L1-ols"].fit.coefficients, c.rungs["L1-ols"].fit.coefficients), "nothing else moves with the seed"


def test_the_six_cohorts_are_in_order_and_each_variant_is_out_of_time(docs):
    assert order_findings(docs["manifest"]) == []
    assert [a["variant_id"] for a in docs["manifest"]["artifacts"]] == [x for v in VARIANT_IDS for x in (f"models-{v}", v)]
    for cid, vid in zip(COHORT_IDS, VARIANT_IDS, strict=True):
        o = docs["variants"][vid]["outputs"]
        assert o["cohort"]["id"] == cid and o["kind"] == "default-cohort"
        assert out_of_time_findings(o, docs["models"][f"models-{vid}"]) == [], vid
        assert [r["cohort_id"] for r in o["realised_vs_predicted"] if r["rung_id"] == "L1-ols"] == list(COHORT_IDS[COHORT_IDS.index(cid):])
    manifest = _committed_manifest()
    assert order_findings(manifest) == [] and manifest["default_variant"] == _case.DEFAULT_VARIANT == "dc-2009-10"
    for a in (x for x in manifest["artifacts"] if x["role"] == "variant"):
        doc = json.loads((COMMITTED / a["path"]).read_text(encoding="utf-8"))
        models = json.loads((COMMITTED / a["models_ref"]).read_text(encoding="utf-8"))
        assert out_of_time_findings(doc["outputs"], models) == [], a["variant_id"]


def test_adversarial_variants_out_of_order_are_found(docs):
    m = copy.deepcopy(docs["manifest"])
    assert order_findings(m) == []
    m["artifacts"] = list(reversed(m["artifacts"]))
    assert order_findings(m)
    o = copy.deepcopy(docs["variants"]["dc-2009-10"]["outputs"])
    models = docs["models"]["models-dc-2009-10"]
    o["training"]["cutoff_date"] = "2010-12-31"       # a variant that trains on its own cohort
    assert out_of_time_findings(o, models)
    o2 = copy.deepcopy(docs["variants"]["dc-2009-10"]["outputs"])
    o2["realised_vs_predicted"][0]["cohort_id"] = "2003-06"
    assert any("not out of time" in f for f in out_of_time_findings(o2, models))


def test_the_tests_are_engine_test_results_and_a_rung_that_is_not_fitted_is_not_evaluated(docs):
    for vid, doc in docs["variants"].items():
        tests = doc["tests"]
        assert result_row_findings(tests) == [], vid
        models = docs["models"][f"models-{vid}"]["model"]
        by_model = {}
        for t in tests:
            by_model.setdefault(t["model_id"], set()).add(t["test_id"])
        for m in models:
            assert by_model[m["id"]] == {"lgd_ead.lgd_calibration_by_segment", "lgd_ead.lgd_discrimination",
                                         "lgd_ead.lgd_calibration_over_time"}, (vid, m["id"])
        n_down = len(doc["outputs"]["downturn"]["rows"])
        assert sum(t["test_id"] == "lgd_ead.downturn_coverage" for t in tests) == n_down >= 1
        for t in tests:
            assert t["h0"] and t["reference"] and t["policy_version"], t["test_id"]
        evaluated = {r["rung_id"] for r in doc["outputs"]["rung_comparison"]}
        for m in models:
            rows = [t for t in tests if t["model_id"] == m["id"]]
            if m["id"] in evaluated:
                assert any(t["light"] != "not_evaluated" for t in rows)
            else:
                assert all(t["light"] == "not_evaluated" and t["notes"] for t in rows)


def test_adversarial_a_test_row_with_a_number_on_a_not_evaluated_light_is_found(docs):
    tests = copy.deepcopy(docs["variants"]["dc-2009-10"]["tests"])
    assert result_row_findings(tests) == []
    row = {**tests[0], "light": "not_evaluated", "statistic": 1.5, "notes": "a reason"}
    assert result_row_findings([row]) == [f"{row['test_id']}@{row['model_id']}: a number on a not_evaluated light"]
    assert result_row_findings([{**tests[0], "test_id": "ifrs9.ecl_backtest"}]) == ["ifrs9.ecl_backtest is not an engine LGD test"]


def test_every_document_declares_the_freddie_mac_slot_absent(docs):
    with pytest.raises(readers.DeclaredAbsence):
        readers.read_freddie(".")
    reason = readers.FREDDIE_REASON
    for vid, doc in docs["variants"].items():
        st = doc["outputs"]["data_status"]
        assert st == bd.data_status_block(reason), vid
        assert freddie_findings(st) == []
        assert docs["models"][f"models-{vid}"]["fit"]["data_status"] == st
        assert "freddie" not in json.dumps(doc["outputs"]["rung_comparison"]).lower()
    assert freddie_findings(_committed_variant()["outputs"]["data_status"]) == []


def _committed_variant():
    return json.loads((COMMITTED / "C08" / "dc-2009-10.json").read_text(encoding="utf-8"))


def test_adversarial_a_variant_claiming_freddie_mac_data_is_found(docs):
    st = copy.deepcopy(docs["variants"]["dc-2009-10"]["outputs"]["data_status"])
    assert freddie_findings(st) == []
    assert freddie_findings({**st, "freddie_mac_available": True, "freddie_mac_reason": None}) == ["freddie"]
    assert freddie_findings({**st, "primary_source": "freddie-mac-sflld"}) == ["freddie"]
    planted = copy.deepcopy(docs["variants"]["dc-2009-10"])
    planted["outputs"]["data_status"]["freddie_mac_available"] = True
    with pytest.raises(SchemaViolation):
        validate_document("data/derived/C08/dc-2009-10.json", planted)


def test_amounts_are_in_usd_and_an_expected_range_is_enforced(docs, annual, tmp_path, monkeypatch):
    for doc in (*docs["variants"].values(), *docs["models"].values()):
        assert currency_findings(doc) == []
    for doc in docs["variants"].values():
        o = doc["outputs"]
        assert o["currency"] == o["exposure"]["currency"] == "USD"
    ok = expectations.check("C08", {"mean-proxy@2009-10": (0.0, 2.0)}, {"mean-proxy@2009-10": 0.8})
    assert ok == {"mean-proxy@2009-10": [0.0, 2.0]}
    with pytest.raises(expectations.ExpectationError, match="mean-proxy@2009-10"):
        expectations.check("C08", {"mean-proxy@2009-10": (0.0, 0.1)}, {"mean-proxy@2009-10": 0.8})
    from pipeline.io import fetch
    from pipeline.pipeline import PipelinePaths

    monkeypatch.setattr(fetch, "MANIFEST", ROOT / "data" / "sources" / "manifest.json")  # the sandbox points it at an empty one
    monkeypatch.setattr(bd, "EXPECT", {"mean-proxy@2009-10": (0.0, 0.01), "n-defaults-total": (0.0, 1e18)})
    monkeypatch.setattr(panel, "annual_rate", lambda df: annual)
    with pytest.raises(expectations.ExpectationError, match="mean-proxy@2009-10"):
        _case.CASE.bake(seed=42, paths=PipelinePaths.from_output(tmp_path / "x"), data_root=DATA)
    assert not (tmp_path / "x" / "manifests" / "C08.json").exists(), "a bake outside its expected range writes no manifest"


def test_adversarial_a_foreign_currency_amount_is_found(docs):
    doc = copy.deepcopy(docs["variants"]["dc-2009-10"])
    assert currency_findings(doc) == []
    doc["outputs"]["exposure"]["currency"] = "EUR"
    assert currency_findings(doc) == ["currency EUR"]
