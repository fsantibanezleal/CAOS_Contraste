"""Adversarial checks of the C09 requirements (docs/design/features/c09/validation.md): each plants one defect in a copy of
the in-memory documents or inputs and asserts the clean copy passes and the planted copy is found."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import c09_invariants as invariants
import numpy as np
import pytest
from pipeline.cases.c09 import bake, calibration, estimators, generator, page, params
from riskvalidation.lgd_ead import ccf as engine_ccf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import contract_schemas as cs  # noqa: E402


def doc_path(vid: str) -> Path:
    return ROOT / "data" / "derived" / "C09" / f"{vid}.json"


def test_adversarial_a_marginal_without_a_source_is_refused() -> None:
    calibration.validate_marginals(calibration.marginals())
    bad = [{**r, "source": ""} if i == 2 else r for i, r in enumerate(calibration.marginals())]
    with pytest.raises(calibration.MarginalError):
        calibration.validate_marginals(bad)
    unknown = [{**r, "source": "somewhere else"} if i == 0 else r for i, r in enumerate(calibration.marginals())]
    with pytest.raises(calibration.MarginalError):
        calibration.validate_marginals(unknown)


def test_adversarial_a_generator_with_another_ccf_is_not_recovered() -> None:
    pop = generator.draw_population(21, 120_000)
    est = estimators.aggregate(estimators.observe(generator.realise(pop, 0), "fixed-horizon"), "none", "mean").value
    assert abs(est - params.known_ccf(0)) < params.TOLERANCE
    assert abs(est - params.known_ccf(5)) > params.TOLERANCE      # the level 5 truth is not what a level 0 generator draws with


def test_adversarial_replications_sharing_a_seed_are_found() -> None:
    plan = bake.plan(42, 0.02)
    assert invariants.independent(plan) == []
    shared = {**plan, "test_seeds": [plan["development_seeds"][0], *plan["test_seeds"][1:]]}
    assert invariants.independent(shared) == ["a seed is shared by the development and the test replications"]
    repeated = {**plan, "development_seeds": [plan["development_seeds"][0]] * 2}
    assert any("repeats" in m for m in invariants.independent(repeated))


def test_adversarial_levels_out_of_order_are_refused() -> None:
    params.validate_levels(params.LEVELS)
    reversed_levels = tuple(reversed(params.LEVELS))
    with pytest.raises(params.LevelError):
        params.validate_levels(reversed_levels)
    accelerated = (dict(params.LEVELS[0], factor=1.5, window=6), *params.LEVELS[1:])
    with pytest.raises(params.LevelError):
        params.validate_levels(accelerated)                      # level 0 must carry no acceleration


def test_adversarial_a_clipped_untreated_ccf_is_found(monkeypatch) -> None:
    d = generator.generate(31, 5, 80_000)
    obs = estimators.observe(d, "fixed-horizon")
    assert invariants.unclipped(obs.ccf, estimators.treat(obs, "none").values) == []
    real = engine_ccf.treat_ccf
    monkeypatch.setattr(engine_ccf, "treat_ccf", lambda c, t: real(c, "floor-cap"))
    assert invariants.unclipped(obs.ccf, estimators.treat(obs, "none").values) != []
    clean = json.loads(doc_path("level-5").read_text(encoding="utf-8"))
    ref = cs.schema_for_document(doc_path("level-5"), clean)
    assert cs.errors(ref, clean) == []
    row = next(r for r in clean["outputs"]["ccf_by_design"]["rows"] if r["treatment"] == "none")
    row["estimate"] = {"value": 1.2, "flag": "in-range"}              # a value above 1 flagged in-range is a clip in disguise
    assert cs.errors(ref, clean) != []


def test_adversarial_a_ccf_of_zero_on_a_fully_drawn_line_is_found() -> None:
    d = generator.generate(32, 3, 80_000)
    obs = estimators.observe(d, "fixed-horizon")
    undrawn = obs.limit_ref - obs.drawn_ref
    assert invariants.undefined_is_nan(obs.ccf, undrawn) == []
    planted = np.where(undrawn <= 0, 0.0, obs.ccf)
    assert invariants.undefined_is_nan(planted, undrawn) != []


def test_adversarial_a_number_not_from_the_engine_is_found(built, monkeypatch) -> None:
    d = generator.generate(33, 1, 20_000)
    obs = estimators.observe(d, "fixed-horizon")
    clean = estimators.aggregate(obs, "none", "pooled").value
    monkeypatch.setattr(engine_ccf, "aggregate_ccf", lambda c, u, a: 0.5)
    assert estimators.aggregate(obs, "none", "pooled").value == 0.5 != clean
    row = next(r for r in built["variants"]["level-1"]["outputs"]["ccf_by_design"]["rows"] if r["treatment"] == "none" and r["estimator"] == "pooled")
    assert row["estimate"]["value"] != 0.5                         # a baked estimate is what the real engine returned


def test_adversarial_a_document_failing_its_schema_or_its_hash_is_found() -> None:
    p = doc_path("level-2")
    doc = json.loads(p.read_text(encoding="utf-8"))
    ref = cs.schema_for_document(p, doc)
    assert cs.errors(ref, doc) == []
    broken = copy.deepcopy(doc)
    del broken["outputs"]["ccf_by_design"]
    assert cs.errors(ref, broken) != []
    sums = dict(reversed(line.split("  ", 1)) for line in (p.parent / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines())
    assert hashlib.sha256(p.read_bytes()).hexdigest() == sums["C09/level-2.json"]
    edited = p.read_bytes().replace(b"synthetic", b"synthetiC", 1)
    assert hashlib.sha256(edited).hexdigest() != sums["C09/level-2.json"]


def test_adversarial_a_document_without_its_known_ccf_is_found(built) -> None:
    out = built["variants"]["level-4"]["outputs"]
    assert invariants.known_truth(out) == []
    broken = copy.deepcopy(out)
    del broken["ccf_by_design"]["rows"][0]["truth"]
    assert invariants.known_truth(broken) != []
    wrong = copy.deepcopy(out)
    wrong["ccf_by_design"]["rows"][3]["truth"] = {"value": params.known_ccf(0), "flag": "in-range"}
    assert invariants.known_truth(wrong) != []
    ref = cs.schema_for_document(doc_path("level-4"), built["variants"]["level-4"])
    schema_broken = copy.deepcopy(built["variants"]["level-4"])
    del schema_broken["outputs"]["ccf_by_design"]["rows"][0]["truth"]
    assert cs.errors(ref, schema_broken) != []
    no_gen = copy.deepcopy(built["variants"]["level-4"])
    del no_gen["outputs"]["generator"]["true_ccf"]
    assert cs.errors(ref, no_gen) != []


def test_adversarial_a_direct_ead_model_without_its_clipped_counts_is_found(built) -> None:
    doc = built["variants"]["level-0"]
    ref = cs.schema_for_document(doc_path("level-0"), doc)
    assert cs.errors(ref, doc) == []
    broken = copy.deepcopy(doc)
    m = next(x for x in broken["outputs"]["ead_models"] if x["kind"] == "direct-ead")
    m["n_clipped_above"] = None
    assert cs.errors(ref, broken) != []
    neg = copy.deepcopy(doc)
    row = neg["outputs"]["ead_backtest"]["rows"][0]
    row["predicted_ead"], row["prediction_flag"] = -5.0, "in-range"
    assert cs.errors(ref, neg) != []


def test_adversarial_a_different_seed_gives_different_bytes(built) -> None:
    other = bake.build(43, 0.02)
    a = json.dumps(built["variants"]["level-3"], sort_keys=True)
    b = json.dumps(other["variants"]["level-3"], sort_keys=True)
    assert hashlib.sha256(a.encode()).hexdigest() != hashlib.sha256(b.encode()).hexdigest()


def test_adversarial_a_notice_that_drops_the_word_synthetic_is_found(built) -> None:
    doc = built["variants"]["level-5"]
    assert invariants.synthetic(doc) == []
    bad = copy.deepcopy(doc)
    bad["outputs"]["generator"]["notice"]["en"] = "Lines of a portfolio."
    assert invariants.synthetic(bad) != []
    status = copy.deepcopy(doc)
    status["provenance"]["truth_status"] = "real-outcomes"
    assert invariants.synthetic(status) != []


def test_adversarial_a_page_block_that_differs_from_the_documents_is_found() -> None:
    block = page.results_block(ROOT / "data" / "derived").strip("\n")
    text = (ROOT / "docs" / "cases" / "C09.md").read_text(encoding="utf-8")
    assert text.split(page.MARK_START, 1)[1].split(page.MARK_END, 1)[0].strip("\n") == block
    lines = block.splitlines()
    assert len(lines) >= 8
    tampered = "\n".join([*lines[:3], lines[3].replace("0", "7", 1), *lines[4:]])
    assert tampered != block                                       # the comparison of the test would fail on it
    assert page.claim_findings(text) == []
    assert page.claim_findings("These generated lines are real cards of a real bank.\n") != []
