"""S-6: the committed result of reject inference on the German twin (data/derived/C01/german-twin.json, outputs.reject_inference).

The tests recompute what the document states from its own numbers (the reduction, the intervals, the verdicts), hold the design's
sanity bounds (the oracle is unbiased, the population default rate is the data's, a stronger private signal biases the
accepted-only model more) and, when the raw German file is on the device, re-run the first repetitions of the method and compare
them with the committed ones, so the document is reproduced by the code and not typed in.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest

from pipeline.cases import c01_reject as rj
from pipeline.io import fetch

ROOT = Path(__file__).resolve().parents[2]
DERIVED = ROOT / "data" / "derived" / "C01"
GERMAN = json.loads((DERIVED / "german-twin.json").read_text(encoding="utf-8"))
RI = GERMAN["outputs"]["reject_inference"]
SEED = GERMAN["provenance"]["seed"]
REAL_MANIFEST = fetch.MANIFEST  # the suite's sandbox points the licence manifest at an empty file for every test
DATA = os.environ.get("CONTRASTE_DATA", "")  # read at collection: the suite's sandbox resets the environment per test


def by_regime(rid: str) -> dict[str, dict]:
    return {r["id"]: r for g in RI["regimes"] if g["id"] == rid for r in g["rungs"]}


def test_only_the_german_twin_carries_the_block_and_the_other_variants_state_null() -> None:
    assert RI is not None
    for path in sorted(DERIVED.glob("*.json")):
        if path.name.startswith("models-") or path.name == "german-twin.json":
            continue
        assert json.loads(path.read_text(encoding="utf-8"))["outputs"]["reject_inference"] is None, path.name


def test_the_design_states_what_was_run() -> None:
    d = RI["design"]
    assert d["population"] == "uci-german" and d["n_rows"] == 1000
    assert d["n_dev"] + d["n_test"] == 1000 and d["reps"] >= 100 and d["bootstrap"] == rj.BOOTSTRAP
    assert [g["id"] for g in RI["regimes"]] == [r["id"] for r in rj.REGIMES]
    assert [r["id"] for r in RI["rungs"]] == list(rj.RUNGS)
    for g in RI["regimes"]:
        assert [r["id"] for r in g["rungs"]] == list(rj.RUNGS)
        for r in g["rungs"]:
            assert len(r["reps"]["bias"]) == len(r["reps"]["auc"]) == d["reps"]


def test_every_statistic_is_recomputed_from_the_per_repetition_values() -> None:
    for k_reg, g in enumerate(RI["regimes"]):
        b0 = np.array(by_regime(g["id"])["accepted-only"]["reps"]["bias"])
        for k, r in enumerate(g["rungs"]):
            b = np.array(r["reps"]["bias"])
            a = np.array(r["reps"]["auc"])
            assert r["bias"]["mean"] == pytest.approx(b.mean(), abs=1e-5)
            assert r["auc"]["mean"] == pytest.approx(a.mean(), abs=1e-5)
            assert r["abs_bias"] == pytest.approx(np.abs(b).mean(), abs=1e-5)
            point, lo, hi = rj.reduction(b0, b, seed=SEED + 31 * k_reg + k)
            assert r["reduction"]["value"] == pytest.approx(point, abs=2e-3)
            assert r["reduction"]["lo"] == pytest.approx(lo, abs=0.02) and r["reduction"]["hi"] == pytest.approx(hi, abs=0.02)
            assert r["bias"]["lo"] <= r["bias"]["mean"] <= r["bias"]["hi"]


def test_the_hypotheses_are_the_verdicts_of_the_stored_numbers() -> None:
    again = rj.verdicts(RI)
    assert [h["id"] for h in RI["hypotheses"]] == [h["id"] for h in again] == ["H1", "H2", "H3"]
    for stored, fresh in zip(RI["hypotheses"], again, strict=True):
        assert stored["holds"] == fresh["holds"] and stored["rung"] == fresh["rung"]
        assert stored["value"] == pytest.approx(fresh["value"]) and stored["outcome"] == fresh["outcome"]
        assert stored["statement"]["en"] and stored["statement"]["es"]


def test_the_oracle_is_unbiased_and_the_population_rate_is_the_datas() -> None:
    for g in RI["regimes"]:
        assert abs(by_regime(g["id"])["oracle"]["bias"]["mean"]) < 0.01, g["id"]
        assert g["default_rate"]["population"] == pytest.approx(0.30, abs=1e-6)


def test_a_stronger_private_signal_biases_the_accepted_only_model_more() -> None:
    bias = {g["id"]: by_regime(g["id"])["accepted-only"]["bias"]["mean"] for g in RI["regimes"]}
    assert abs(bias["mar"]) < 0.03, "an ignorable policy leaves the accepted-only level near the truth"
    assert 0 > bias["weak"] > bias["moderate"] > bias["strong"]
    accepted = {g["id"]: g["default_rate"]["accepted"] for g in RI["regimes"]}
    assert accepted["mar"] > accepted["weak"] > accepted["moderate"] > accepted["strong"]


def test_the_method_computes_and_reads_no_committed_result() -> None:
    src = (ROOT / "data-pipeline" / "pipeline" / "cases" / "c01_reject.py").read_text(encoding="utf-8")
    for needle in ("json", "open(", "read_text", "data/derived", "np.load"):
        assert needle not in src.replace("json.dumps", ""), needle


@pytest.mark.skipif(not DATA or not (Path(DATA) / "raw" / "uci-german").exists(), reason="the raw German file is not on this device")
def test_the_first_repetitions_are_reproduced_by_the_code_on_the_raw_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetch, "MANIFEST", REAL_MANIFEST)
    from pipeline.cases import c01_features as feat
    from pipeline.cases import c01_retail_pd as c01

    df, _ = c01._load_german(Path(DATA))
    fresh = rj.run(df, feat.GERMAN_FEATURES, feat.GERMAN_CATEGORICAL, seed=SEED, reps=2, population="uci-german")
    for g, f in zip(RI["regimes"], fresh["regimes"], strict=True):
        for r, q in zip(g["rungs"], f["rungs"], strict=True):
            assert r["reps"]["bias"][:2] == pytest.approx(q["reps"]["bias"], abs=1e-6), (g["id"], r["id"])
            assert r["reps"]["auc"][:2] == pytest.approx(q["reps"]["auc"], abs=1e-6), (g["id"], r["id"])
