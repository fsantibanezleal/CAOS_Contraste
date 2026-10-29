"""S-5 (method tiers plan, section 3): the machine-learning LGD benchmark beyond one boosted model, a random forest and a neural
rung (Bellotti et al. 2021), on the same split as the six rungs before them.

Acceptance criterion of the plan: out-of-time calibration by bucket and the ladder's metrics on the same split as L1 to L6, the
hypothesis stated before the run and reported whatever the result. Tested on the producer's tables and on the sample bake; the
committed documents carry the real run."""
from __future__ import annotations

import json

import numpy as np
import pytest

from pipeline.cases.c08 import cutoff as C
from pipeline.cases.c08 import ml_benchmark as ml
from pipeline.cases.c08 import models as md_
from pipeline.cases.c08.ladder import RUNGS, fit_ladder

from c08_helpers import COMMITTED

NEW = ("L7-random-forest", "L8-neural-network")


@pytest.fixture(scope="module")
def fitted(tables):
    d = tables["defaults"]
    train = d.take(C.training_mask(d, "2008-12-31"))
    lad = fit_ladder(train.design(), train.y, "2008-12-31", 42)
    return lad, train, d.take(d.year >= 2009)


def test_the_ladder_adds_a_random_forest_and_a_neural_rung_after_the_six():
    assert [r for r, _ in RUNGS][-2:] == list(NEW)
    assert dict(RUNGS)["L7-random-forest"] == "random-forest" and dict(RUNGS)["L8-neural-network"] == "neural-network"
    assert len(RUNGS) == 8


def test_each_new_rung_is_fitted_on_the_training_span_and_predicts_inside_zero_one(fitted):
    lad, train, test = fitted
    x = test.design()
    for rid in NEW:
        rung = lad.rungs[rid]
        assert rung.evaluated and rung.reason is None and rung.fit is None and rung.booster is not None, rid
        p = lad.predict(rung, x)
        assert p.shape == (test.n,) and np.isfinite(p).all() and (p >= 0).all() and (p <= 1).all(), rid
        assert rung.library == "scikit-learn", rid
        assert rung.booster.n_features_in_ == x.shape[1], rid
    assert lad.rungs["L7-random-forest"].booster.n_estimators == ml.FOREST["n_estimators"]
    assert lad.n_fitted == train.n - lad.n_out_of_range


def test_the_new_rungs_are_pure_functions_of_the_data_and_the_seed(tables, fitted):
    lad, train, test = fitted
    x = test.design()
    same = fit_ladder(train.design(), train.y, "2008-12-31", 42)
    other = fit_ladder(train.design(), train.y, "2008-12-31", 7)
    for rid in NEW:
        a, b, c = (m.predict(m.rungs[rid], x) for m in (lad, same, other))
        assert np.array_equal(a, b), f"{rid}: same seed, same predictions"
        assert not np.array_equal(a, c), f"{rid}: the seed moves it"
    for rid, _ in RUNGS[:6]:  # the six rungs before them do not depend on anything the new rungs add
        if lad.rungs[rid].evaluated and rid != "L5-gradient-boosted":
            assert np.array_equal(lad.predict(lad.rungs[rid], x), other.predict(other.rungs[rid], x)), rid


def test_a_new_rung_that_cannot_be_fitted_is_not_evaluated_with_its_reason_and_no_number(tables, monkeypatch):
    d = tables["defaults"]
    train = d.take(C.training_mask(d, "2008-12-31"))

    def boom(*a, **k):
        raise ValueError("planted failure")

    monkeypatch.setattr(ml, "fit_forest", boom)
    monkeypatch.setattr(ml, "fit_network", boom)
    lad = fit_ladder(train.design(), train.y, "2008-12-31", 1)
    for rid in NEW:
        r = lad.rungs[rid]
        assert not r.evaluated and "planted failure" in r.reason and r.booster is None
    assert lad.rungs["L1-ols"].evaluated


def test_the_comparison_buckets_and_tests_carry_both_new_rungs_in_every_variant(docs):
    for vid, doc in docs["variants"].items():
        o = doc["outputs"]
        by = {r["rung_id"]: r for r in o["rung_comparison"]}
        assert all(rid in by for rid in NEW), vid
        for rid in NEW:
            assert np.isfinite([by[rid][k] for k in ("rmse", "mae", "calibration_gap")]).all()
            buckets = [b for b in o["calibration_by_bucket"] if b["rung_id"] == rid]
            assert [b["bucket"] for b in buckets] == [1, 2, 3, 4, 5], (vid, rid)
            ids = {t["test_id"] for t in doc["tests"] if t["model_id"] == rid}
            assert ids == {"lgd_ead.lgd_calibration_by_segment", "lgd_ead.lgd_discrimination", "lgd_ead.lgd_calibration_over_time"}
        models = {m["id"]: m for m in docs["models"][f"models-{vid}"]["model"]}
        assert models["L7-random-forest"]["licence"] == models["L8-neural-network"]["licence"] == "BSD-3-Clause"
        assert models["L7-random-forest"]["engine"] == "scikit-learn"


def test_the_models_document_records_the_settings_and_the_diagnostics(docs):
    models = {m["id"]: m for m in docs["models"]["models-dc-2009-10"]["model"]}
    rf, nn = models["L7-random-forest"]["details"], models["L8-neural-network"]["details"]
    assert rf["settings"]["n_estimators"] == ml.FOREST["n_estimators"] and rf["settings"]["min_samples_leaf"] == ml.FOREST["min_samples_leaf"]
    assert abs(sum(rf["feature_importance"].values()) - 1.0) < 1e-9
    assert nn["settings"]["hidden_layer_sizes"] == list(ml.NETWORK["hidden_layer_sizes"]) and nn["n_iter"] >= 1
    assert nn["best_validation_score"] is not None
    ladder = docs["models"]["models-dc-2009-10"]["fit"]["ladder"]
    assert {r["kind"] for r in ladder} >= {"random-forest", "neural-network"}


def test_the_cohort_result_is_the_best_ml_rung_against_the_best_of_the_six():
    rows = [{"rung_id": r, "rmse": v} for r, v in
            [("L1-ols", 0.33), ("L2-fractional-logit", 0.32), ("L5-gradient-boosted", 0.30), ("L6-tobit", 0.36),
             ("L7-random-forest", 0.295), ("L8-neural-network", 0.31)]]
    res = ml.cohort_result(rows)
    assert res["classical"] == ("L5-gradient-boosted", 0.30) and res["ml"] == ("L7-random-forest", 0.295)
    assert res["gain"] == pytest.approx(0.005) and res["ml_wins"] is True
    worse = ml.cohort_result([*rows[:5], {"rung_id": "L8-neural-network", "rmse": 0.31}][:4] +
                             [{"rung_id": "L7-random-forest", "rmse": 0.33}, {"rung_id": "L8-neural-network", "rmse": 0.34}])
    assert worse["ml_wins"] is False and worse["gain"] < 0


def test_the_verdict_is_stated_for_a_win_a_loss_and_the_middle_never_dropped():
    assert ml.verdict(5, 6) == "holds" and ml.verdict(4, 6) == "holds"
    assert ml.verdict(3, 6) == "mixed"
    assert ml.verdict(2, 6) == "refuted" and ml.verdict(0, 6) == "refuted"
    assert ml.HYPOTHESIS["en"] and ml.HYPOTHESIS["es"] and ml.REFUTED_IF["en"] and ml.REFUTED_IF["es"]


def test_adversarial_a_missing_ml_rung_is_found_not_skipped():
    rows = [{"rung_id": "L1-ols", "rmse": 0.3}, {"rung_id": "L7-random-forest", "rmse": 0.2}]
    with pytest.raises(ValueError, match="L8-neural-network"):
        ml.cohort_result(rows)


def test_every_variant_carries_the_ml_impact_and_it_is_the_comparison_difference(docs):
    for vid, doc in docs["variants"].items():
        item = doc["impact"]["ml_rmse_gain"]
        res = ml.cohort_result(doc["outputs"]["rung_comparison"])
        assert item["value"] == pytest.approx(res["gain"], abs=1e-8) and item["unit"] == "share"
        assert item["label"]["en"] and item["label"]["es"], vid


def test_the_committed_documents_carry_the_run_and_the_models_name_the_two_rungs():
    manifest = json.loads((COMMITTED / "manifests" / "C08.json").read_text(encoding="utf-8"))
    n = 0
    for a in (x for x in manifest["artifacts"] if x["role"] == "variant"):
        doc = json.loads((COMMITTED / a["path"]).read_text(encoding="utf-8"))
        assert {r["rung_id"] for r in doc["outputs"]["rung_comparison"]} >= set(NEW), a["variant_id"]
        assert "ml_rmse_gain" in doc["impact"]
        n += 1
    assert n == 6
    out = md_.RUNG_KIND
    assert out["L7-random-forest"] == "random-forest"


def test_the_case_page_states_the_s5_block_the_verdict_and_the_hypothesis_from_the_committed_documents():
    from pathlib import Path

    from pipeline.cases.c08 import page

    root = Path(__file__).resolve().parents[2]
    text = (root / "docs" / "cases" / "C08.md").read_text(encoding="utf-8")
    assert text.count(page.ML_START) == 1 and text.count(page.ML_END) == 1
    block = text.split(page.ML_START, 1)[1].split(page.ML_END, 1)[0].strip("\n")
    assert block == page.ml_block(root / "data" / "derived").strip("\n"), "regenerate it: python data-pipeline/pipeline/cases/c08/page.py"
    v = page.ml_verdict(root / "data" / "derived")
    assert v["cohorts"] == 6 and 0 <= v["wins"] <= 6 and v["verdict"] == ml.verdict(v["wins"], 6)
    assert f"**Verdict: {v['verdict']}.**" in block and f"in {v['wins']} of 6" in block
    assert ml.HYPOTHESIS["en"].split("Hypothesis S-5: ")[1][:40] in text.replace("\n", " ") or "Hypothesis, stated before the run" in text
