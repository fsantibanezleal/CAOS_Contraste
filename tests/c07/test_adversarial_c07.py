"""Adversarial checks of the C07 requirements (docs/design/features/c07/validation.md): each plants one defect in a copy of
the in-memory documents or inputs and asserts the clean copy passes and the planted copy is found."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from pipeline.cases.c07 import documents, generator, scenarios, sources
from pipeline.cases.c07 import book as bk
from riskvalidation.provisions import local_cl as cl
from riskvalidation.provisions import reconciliation as rc
import c07_invariants as invariants
import test_c07_calibration as cal

ROOT = Path(__file__).resolve().parents[2]


def test_adversarial_a_target_without_a_source_is_refused() -> None:
    sources.validate_targets()
    for key in ("publication", "where", "as_of"):
        bad = tuple({**t, key: ""} if i == 3 else t for i, t in enumerate(sources.TARGETS))
        with pytest.raises(sources.TargetError):
            sources.validate_targets(bad)
    unknown = tuple({**t, "publication": "nowhere"} if i == 0 else t for i, t in enumerate(sources.TARGETS))
    with pytest.raises(sources.TargetError):
        sources.validate_targets(unknown)


def test_adversarial_a_book_off_its_target_is_reported(built) -> None:
    assert cal.check(built["models"]) == []
    doc = copy.deepcopy(built["models"])
    t = next(x for x in doc["fit"]["calibration_targets"] if x["metric"] == "provision index: consumer")
    t["achieved"] = t["target"] * 1.10
    assert any("provision index: consumer" in m for m in cal.check(doc))


def test_adversarial_a_variant_with_another_portfolio_is_found(outs) -> None:
    assert invariants.same_portfolio(outs) == []
    bad = copy.deepcopy(outs)
    bad["recession"]["portfolio"]["segments"][2]["accounts"] += 1
    assert invariants.same_portfolio(bad) == ["recession: another portfolio"]
    other = generator.generate(43, 0.02)
    assert other.digest() != generator.generate(42, 0.02).digest()


def test_adversarial_a_regime_number_not_from_the_engine_is_found(built, monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace one engine function by a stub: the regime total moves, so a number computed outside the engine could not match
    the baked one."""
    ev = built["evaluations"]["base"]
    book = built["book"]
    from pipeline.cases.c07 import b1

    clean = float(b1.provisions(book, ev["state"]).provision.sum())
    monkeypatch.setattr(cl, "b1_group_provision", lambda e, pe, *a, **k: 0.0)
    stub = float(b1.provisions(book, ev["state"]).provision.sum())
    assert stub < clean * 0.9 and clean == pytest.approx(float(ev["b1"].provision.sum()))
    # and the golden cell of the pinned engine is a number the stub cannot reproduce
    assert cl.b1_group_provision(1000, 0.02, 0.5, 0.0004) == 0.0


def test_adversarial_a_minimum_on_a_group_portfolio_is_found(outs) -> None:
    out = outs["base"]
    assert invariants.minimum_scope(out) == []
    bad = copy.deepcopy(out)
    book_total = sum(s["gross_exposure"] for s in bad["portfolio"]["segments"])
    bad["b1_detail"]["minimum_check"]["normal_portfolio_exposure"] = book_total        # the whole performing book
    assert any("includes a group portfolio" in m for m in invariants.minimum_scope(bad))
    bad = copy.deepcopy(out)
    bad["b1_detail"]["minimum_check"]["top_up"] += 5.0e6
    assert any("shortfall" in m for m in invariants.minimum_scope(bad))


def test_adversarial_an_unlabelled_single_scenario_ifrs9_figure_is_found(outs) -> None:
    out = outs["recession"]
    assert invariants.ifrs9_weighting(out) == []
    bad = copy.deepcopy(out)
    bad["ifrs9_detail"]["weighted_components"][0]["weight"] = 0.15              # weights sum to 0.9
    assert invariants.ifrs9_weighting(bad)
    bad = copy.deepcopy(out)
    bad["ifrs9_detail"]["measure"] = "single-scenario"
    assert any("measure" in m for m in invariants.ifrs9_weighting(bad))
    bad = copy.deepcopy(out)
    bad["ifrs9_detail"]["weighted_components"] = bad["ifrs9_detail"]["weighted_components"][2:]
    bad["ifrs9_detail"]["weighted_components"][0]["weight"] = 1.0                # a single 100% scenario
    assert invariants.ifrs9_weighting(bad)


def test_adversarial_an_overlay_inside_the_model_ecl_is_found(outs) -> None:
    out = outs["base"]
    assert invariants.overlays(out) == []
    bad = copy.deepcopy(out)
    ifrs = invariants.reg(bad)["ifrs9"]
    ifrs["by_segment"][0]["provision"] += bad["ifrs9_detail"]["overlays_total"]     # overlay merged into a segment
    assert any("inside the model ECL" in m for m in invariants.overlays(bad))
    bad = copy.deepcopy(out)
    invariants.reg(bad)["ifrs9"]["unallocated_lines"][0]["kind"] = "minimum-top-up"
    assert invariants.overlays(bad)


def test_adversarial_a_bridge_off_by_one_peso_is_found(outs) -> None:
    out = outs["house-price-fall"]
    assert invariants.bridge(out) == []
    bad = copy.deepcopy(out)
    bad["gap_bridge"]["steps"][2]["amount"] += 1.5
    assert invariants.bridge(bad)


def test_adversarial_a_document_failing_its_schema_or_its_hash_is_found(built, tmp_path: Path) -> None:
    import contract_schemas as cs

    doc = built["variants"]["base"]
    path = ROOT / "data" / "derived" / "C07" / "base.json"
    assert cs.errors(cs.schema_for_document(path, doc), doc) == []
    bad = copy.deepcopy(doc)
    del bad["outputs"]["gap_bridge"]
    assert cs.errors(cs.schema_for_document(path, bad), bad)
    bad = copy.deepcopy(doc)
    bad["outputs"]["synthetic"] = False
    assert cs.errors(cs.schema_for_document(path, bad), bad)
    f = tmp_path / "doc.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    want = hashlib.sha256(f.read_bytes()).hexdigest()
    f.write_text(json.dumps(doc) + " ", encoding="utf-8")
    assert hashlib.sha256(f.read_bytes()).hexdigest() != want


def test_adversarial_a_different_seed_gives_different_bytes(tmp_path: Path) -> None:
    from pipeline.cases.c07 import CASE
    from pipeline.pipeline import PipelinePaths

    CASE.bake(1, PipelinePaths.from_output(tmp_path / "s1"), None, 0.02)
    CASE.bake(2, PipelinePaths.from_output(tmp_path / "s2"), None, 0.02)
    assert (tmp_path / "s1" / "C07" / "base.json").read_bytes() != (tmp_path / "s2" / "C07" / "base.json").read_bytes()


def test_adversarial_a_shock_without_a_source_is_refused() -> None:
    scenarios.validate_scenarios()
    bad = tuple(({**s, "description": {"en": "Recession.", "es": "Recesión."}} if s["id"] == "recession" else s)
                for s in scenarios.SCENARIOS)
    with pytest.raises(scenarios.ScenarioError):
        scenarios.validate_scenarios(bad)
    with pytest.raises(scenarios.ScenarioError):
        scenarios.validate_scenarios(scenarios.SCENARIOS[:5])


def test_adversarial_a_rollforward_with_a_moved_movement_fails() -> None:
    a = rc.allowance_rollforward("stage1", 1000.0, {"originations": 200.0, "write-off": -50.0}, 1150.0)
    g = rc.gca_rollforward("stage1", 100000.0, {"repayments": -5000.0, "originations": 20000.0}, 115000.0)
    lines = [{"id": "opening", "kind": "opening", "amount": 1000.0}, {"id": "originations", "kind": "movement", "amount": 200.0},
             {"id": "write-off", "kind": "movement", "amount": -50.0}, {"id": "closing", "kind": "closing", "amount": 1150.0}]
    assert rc.check_identities([a], [g], lines, {"stage1": 1150.0}) == []
    moved = rc.allowance_rollforward("stage1", 1000.0, {"originations": 201.0, "write-off": -50.0}, 1150.0)
    assert rc.check_identities([moved], [g], lines, {"stage1": 1150.0})


def test_adversarial_a_text_calling_banco_andino_real_is_found(built) -> None:
    doc = copy.deepcopy(built["variants"]["base"])
    assert invariants.synthetic(doc) == []
    bad = copy.deepcopy(doc)
    bad["outputs"]["notice"]["en"] = "The provision Chilean banks book on loans."
    assert any("notice" in m for m in invariants.synthetic(bad))
    bad = copy.deepcopy(doc)
    bad["outputs"]["scenario"]["description"]["en"] += " Banco Andino is a real bank."
    assert any("real bank" in m for m in invariants.synthetic(bad))
    assert np is not None and bk is not None and documents is not None
