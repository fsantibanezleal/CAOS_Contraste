"""S-1: the committed C11 documents carry the R10 quantile network as a fitted rung, through the same gates and ranking as R1 to R9."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from riskvalidation.market import scoring

from pipeline.cases.c11.constants import LEVELS, WINDOWS

ROOT = Path(__file__).resolve().parents[2]
DERIVED = ROOT / "data" / "derived" / "C11"
EVIDENCE = ROOT / "docs" / "design" / "features" / "c11"


def _load(name: str) -> dict:
    return json.loads((DERIVED / name).read_text(encoding="utf-8"))


def test_the_models_document_holds_r10_as_a_fitted_rung_with_a_fit_in_every_window():
    models = _load("models-ladder.json")
    last = models["fit"]["ladder"][-1]
    assert last["model_id"] == "nn-fz" and last["rung"] == "R10" and last["status"] == "fitted" and last["not_run_reason"] is None
    assert [f["window_id"] for f in last["window_fits"]] == [w.window_id for w in WINDOWS]
    for f in last["window_fits"]:
        names = {p["name"] for p in f["parameters"]}
        assert f["n_refits"] > 0 and {"train_fz0@0.01", "train_fz0@0.025"} <= names
    assert not any(r["status"] == "challenger-not-run" for r in models["fit"]["ladder"])
    assert len([r for r in models["fit"]["ladder"]]) == 18


def test_every_window_scores_r10_like_the_other_rungs_and_the_gates_decide_eligibility():
    sel = json.loads((EVIDENCE / "network-selection.json").read_text(encoding="utf-8"))["selected"]
    models = _load("models-ladder.json")
    params = next(m for m in models["model"] if m["id"] == "nn-fz")["parameters"]
    assert params["hidden_units"]["value"] == sel["hidden_units"] and params["weight_decay"]["value"] == sel["weight_decay"]
    for w in WINDOWS:
        doc = _load(f"{w.window_id}.json")
        o = doc["outputs"]
        m = next(x for x in o["models"] if x["model_id"] == "nn-fz")
        assert m["rung"] == "R10" and m["eligible"] == (not m["failed_gates"])
        for lv in m["by_level"]:
            assert lv["es_status"] == "forecast" and lv["n_fz0"] == lv["n_scored"] and np.isfinite(lv["fz0_mean"])
            var, es = np.array(lv["var"]), np.array(lv["es"], dtype=float)
            assert np.all(var > 0) and np.all(es >= var)                          # losses, and the ES is at least the VaR
        tests = [t for t in doc["tests"] if t["model_id"] == "nn-fz"]
        assert {t["test_id"] for t in tests} >= {"market.kupiec_pof", "market.christoffersen_conditional_coverage", "market.acerbi_szekely"}
        assert len(tests) == len([t for t in doc["tests"] if t["model_id"] == "ewma"])           # the same battery as a baseline rung
        for c in o["comparison"]["champions"]:
            assert c["model_id"] != "nn-fz" or m["eligible"]                                    # a champion is always eligible
        for s in o["comparison"]["mcs"]:
            assert "nn-fz" in {x["model_id"] for x in s["members"]}
        others = {r["name"]: r["value"] for r in o["hyperparameters"]["others"]}
        assert others["nn_hidden_units"] == sel["hidden_units"] and others["nn_weight_decay"] == sel["weight_decay"]
        if o["grid"]["realised_loss"]["loss"] is not None:       # a window whose realised loss is committed: the FZ0 recomputes from the arrays
            y = -np.array(o["grid"]["realised_loss"]["loss"])
            for a, lv in zip(LEVELS, m["by_level"], strict=True):
                sc = scoring.mean_scores(y, -np.array(lv["var"]), -np.array(lv["es"], dtype=float), a)
                assert abs(sc.fz0_mean - lv["fz0_mean"]) < 1e-6
