"""CT-918 to CT-920: the S-5 machine-learning benchmark carries loan-level bootstrap intervals beside its pre-registered verdict.

The bootstrap resamples the defaults of the test cohort with replacement and holds the predictions fixed: it measures the sampling
noise of the comparison, not of the fits. The tests state it on known truth (a planted case of rungs that differ by noise only), on
the point differences of ``cohort_result`` (the replicate that draws every default once) and on the documents of the sample bake."""
from __future__ import annotations

import hashlib
import inspect
import json

import numpy as np
import pytest

from pipeline.cases import bootstrap as bs
from pipeline.cases.c08 import ml_benchmark as ml
from pipeline.cases.c08 import ml_bootstrap as mb

REPLICATES = 80
CLASSICAL = ml.CLASSICAL_RUNGS


def _planted(n: int, seed: int, ml_better: float = 0.0):
    """A realised LGD proxy and one prediction per rung: every rung is the truth plus its own independent noise; the two machine-learning
    rungs have ``ml_better`` less noise than the six before them (0: all alike)."""
    rng = np.random.default_rng(seed)
    truth = rng.beta(2.0, 2.0, n)
    y = np.clip(truth + rng.normal(0.0, 0.15, n), 0.0, 1.0)
    preds = {}
    for rid in (*CLASSICAL, *ml.ML_RUNGS):
        sd = 0.12 - (ml_better if rid in ml.ML_RUNGS else 0.0)
        preds[rid] = np.clip(truth + rng.normal(0.0, sd, n), 0.0, 1.0)
    return y, preds


def _rmse(y, p):
    return float(np.sqrt(np.mean((y - p) ** 2)))


def test_the_point_differences_are_the_comparison_of_cohort_result() -> None:
    y, preds = _planted(3000, 1, 0.03)
    out = mb.compare(y, preds, seed=1, replicates=REPLICATES)
    rows = [{"rung_id": r, "rmse": _rmse(y, p)} for r, p in preds.items()]
    res = ml.cohort_result(rows)
    assert out["better_rung"] == res["ml"][0]
    assert out["against_best"]["difference"] == pytest.approx(res["gain"], abs=1e-12) and out["against_best"]["rung_id"] == res["classical"][0]
    for rid in CLASSICAL:
        assert out["against"][rid]["difference"] == pytest.approx(_rmse(y, preds[rid]) - res["ml"][1], abs=1e-12)


def test_the_identity_replicate_reproduces_the_point_differences_and_the_intervals_follow_the_seed() -> None:
    y, preds = _planted(2000, 2, 0.03)
    point = mb.point_differences(y, preds)
    one = mb.compare(y, preds, seed=5, replicates=REPLICATES)
    again = mb.compare(y, preds, seed=5, replicates=REPLICATES)
    other = mb.compare(y, preds, seed=6, replicates=REPLICATES)
    assert one == again and one != other
    assert point["against_best"] == pytest.approx(one["against_best"]["difference"], abs=1e-12)
    for rid in CLASSICAL:
        assert point["against"][rid] == pytest.approx(one["against"][rid]["difference"], abs=1e-12)
    assert one["against_best"]["difference"] == other["against_best"]["difference"]
    for d in (one["against_best"], *one["against"].values()):
        assert d["lo"] <= d["hi"] and d["n_valid"] == REPLICATES and d["reason"] is None


def test_adversarial_a_different_seed_moves_the_interval_and_noise_covers_zero() -> None:
    for seed in (1, 2, 3, 4):
        y, preds = _planted(4000, seed)                       # every rung alike: the better of two against each of six
        out = mb.compare(y, preds, seed=9, replicates=REPLICATES)
        covered = [r for r, d in out["against"].items() if d["lo"] < 0 < d["hi"]]
        assert len(covered) >= 4, (seed, {r: (d["lo"], d["hi"]) for r, d in out["against"].items()})
    y, preds = _planted(4000, 1)
    a = mb.compare(y, preds, seed=1, replicates=REPLICATES)
    b = mb.compare(y, preds, seed=2, replicates=REPLICATES)
    assert a["against_best"]["lo"] != b["against_best"]["lo"]


def test_a_clearly_better_machine_learning_rung_gives_intervals_that_exclude_zero() -> None:
    y, preds = _planted(4000, 1, 0.05)
    out = mb.compare(y, preds, seed=1, replicates=REPLICATES)
    assert out["against_best"]["excludes_zero"] is True and out["against_best"]["lo"] > 0
    assert all(d["excludes_zero"] is True and d["lo"] > 0 for d in out["against"].values())


def test_the_bootstrap_resamples_defaults_and_never_refits(monkeypatch) -> None:
    y, preds = _planted(500, 3, 0.02)

    def boom(*a, **k):
        raise AssertionError("a fit was asked for inside the replicates")

    monkeypatch.setattr(ml, "fit_forest", boom)
    monkeypatch.setattr(ml, "fit_network", boom)
    out = mb.compare(y, preds, seed=1, replicates=7)
    assert out["against_best"]["n_valid"] == 7
    assert sum(1 for c in bs.draws(y.size, 3, 1)) == 3 and all(c.shape == y.shape for c in bs.draws(y.size, 2, 1))


def test_adversarial_an_unfitted_rung_gives_no_interval_with_its_reason() -> None:
    y, preds = _planted(1500, 4, 0.03)
    blk = mb.interval_block(y, {k: v for k, v in preds.items() if k != "L6-tobit"}, {"L6-tobit": "planted: too few defaults"}, seed=1,
                            replicates=REPLICATES)
    rows = {r["rung_id"]: r for r in blk["against"]}
    assert [r["rung_id"] for r in blk["against"]] == list(CLASSICAL)
    t = rows["L6-tobit"]
    assert t["difference"] is None and t["lo"] is None and t["hi"] is None and t["excludes_zero"] is None
    assert "planted" in t["reason"]["en"] and t["reason"]["es"]
    assert blk["evaluated"] is True and rows["L1-ols"]["lo"] is not None
    no_ml = mb.interval_block(y, {k: v for k, v in preds.items() if k not in ml.ML_RUNGS},
                              {"L7-random-forest": "planted", "L8-neural-network": "planted"}, seed=1, replicates=REPLICATES)
    assert no_ml["evaluated"] is False and no_ml["reason"]["en"] and no_ml["better_rung"] is None
    assert no_ml["against_best"]["lo"] is None and all(r["lo"] is None and r["reason"] for r in no_ml["against"])
    none = mb.interval_block(y, {}, dict.fromkeys((*CLASSICAL, *ml.ML_RUNGS), "planted"), seed=1, replicates=REPLICATES)
    assert none["evaluated"] is False


def test_adversarial_a_count_that_disagrees_with_the_cohorts_is_found() -> None:
    def blk(excl, evaluated=True):
        return {"evaluated": evaluated, "interval_excludes_zero": excl}

    wins = [True, True, False, True, None]
    blocks = [blk(True), blk(False), blk(True), blk(True), blk(None, False)]
    ok = mb.overall(wins, blocks)
    assert ok == {"cohorts": 5, "evaluable": 4, "wins": 3, "wins_excluding_zero": 2, "verdict": "holds"}
    assert mb.overall_findings(ok, wins, blocks) == []
    assert mb.overall_findings(dict(ok, wins_excluding_zero=3), wins, blocks) != []
    assert mb.overall_findings(dict(ok, verdict="mixed"), wins, blocks) != []
    assert mb.overall_findings(ok, [True, False, False, True, None], blocks) != []


# ---------------------------------------------------------------------------------------------------------------------
# the documents of the sample bake


def test_every_cohort_carries_an_interval_per_fitted_rung_and_one_against_the_best(docs) -> None:
    for vid, doc in docs["variants"].items():
        blk = doc["outputs"]["ml_benchmark"]
        assert blk["replicates"] == bs.REPLICATES and blk["level"] == 0.95 and blk["seed"] == 42
        assert blk["resampled_unit"] == "default" and blk["predictions_refit"] is False and blk["method"]["en"] and blk["method"]["es"]
        assert [r["rung_id"] for r in blk["against"]] == list(CLASSICAL), vid
        fitted = {r["rung_id"] for r in doc["outputs"]["rung_comparison"]}
        for r in blk["against"]:
            if r["rung_id"] in fitted and blk["evaluated"]:
                assert r["lo"] <= r["hi"], vid
                assert r["excludes_zero"] == (r["lo"] > 0 or r["hi"] < 0) and r["n_valid"] == bs.REPLICATES and r["reason"] is None
            else:
                assert r["difference"] is None and r["lo"] is None and r["excludes_zero"] is None and r["reason"]["en"] and r["reason"]["es"], vid
        assert blk["defaults"] == doc["outputs"]["lgd_distribution"]["n"]


def test_the_intervals_are_reproducible_across_two_bakes(sample_bake) -> None:
    a, b = sample_bake["a"], sample_bake["b"]
    for art in a[1]["artifacts"]:
        if art["role"] != "variant":
            continue
        da = json.loads((a[0] / art["path"]).read_text(encoding="utf-8"))["outputs"]["ml_benchmark"]
        db = json.loads((b[0] / art["path"]).read_text(encoding="utf-8"))["outputs"]["ml_benchmark"]
        assert da == db


def test_the_verdict_is_the_preregistered_rule_and_the_count_of_intervals_excluding_zero_is_stated(docs) -> None:
    wins, excl = [], []
    for vid, doc in docs["variants"].items():
        o = doc["outputs"]
        blk = o["ml_benchmark"]
        res = ml.cohort_result(o["rung_comparison"])        # the rule, from the point RMSE of the rungs, never from an interval
        assert blk["against_best"]["difference"] == pytest.approx(res["gain"], abs=1e-8)
        assert blk["better_rung"] == res["ml"][0] and blk["against_best"]["rung_id"] == res["classical"][0]
        wins.append(res["ml_wins"])
        excl.append(blk["interval_excludes_zero"])
        assert blk["interval_excludes_zero"] == blk["against_best"]["excludes_zero"]
    overall = next(iter(docs["variants"].values()))["outputs"]["ml_benchmark"]["overall"]
    assert overall["cohorts"] == len(wins) and overall["wins"] == sum(wins) and overall["verdict"] == ml.verdict(sum(wins), len(wins))
    assert overall["wins_excluding_zero"] == sum(1 for w, e in zip(wins, excl, strict=True) if w and e)
    assert all(d["outputs"]["ml_benchmark"]["overall"] == overall for d in docs["variants"].values())


def test_the_case_page_prints_each_interval_beside_its_difference_and_the_count(docs) -> None:
    from pipeline.cases.c08 import page

    block = page.ml_block(docs["root"])
    assert "95% interval" in block and f"{bs.REPLICATES:,} replicates" in block and "excludes zero" in block.lower()
    overall = next(iter(docs["variants"].values()))["outputs"]["ml_benchmark"]["overall"]
    assert f"{overall['wins_excluding_zero']} of the {overall['wins']} cohorts" in block
    assert f"**Verdict: {overall['verdict']}.**" in block


def test_the_hypothesis_and_its_verdict_rule_are_unchanged() -> None:
    """The verdict is the pre-registered rule: the bootstrap adds a block beside it and touches neither (the hash pins the text)."""
    text = json.dumps(ml.HYPOTHESIS, sort_keys=True) + json.dumps(ml.REFUTED_IF, sort_keys=True) + inspect.getsource(ml.verdict) + inspect.getsource(ml.cohort_result)
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == PREREGISTERED_SHA256


# the SHA-256 of ``HYPOTHESIS`` and ``REFUTED_IF`` (sorted JSON) followed by the sources of ``verdict`` and ``cohort_result`` as committed
# before this unit (1.01.000 M1)
PREREGISTERED_SHA256 = "fa1dffd675b5cd6238f0dfd7bee3d8db718e7d7240ca28d61083802be97778b2"
