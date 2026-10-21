"""U15-P: adversarial checks. Each test plants a defect the brief says to refute and holds that the bake or its checkers refuse it.

A mutant of an engine function makes the bake refuse (its documents would no longer agree with the independent checker of U15-S), which also proves
that the value came from the engine and not from arithmetic of the bake's own. A planted text, label or input is refused by the guard that owns it.
"""
from __future__ import annotations

import copy
import json
from datetime import date, timedelta

import gov_support as gs
import pytest


def test_adversarial_a_tier_the_engine_did_not_compute_is_refused(monkeypatch):
    """The matrix is the engine's: with matrix_tier forced to 4 the documents disagree with the checker and the bake publishes nothing."""
    from pipeline.governance import bake
    from pipeline.governance.readers import BakeError
    from riskvalidation.governance import tiering

    monkeypatch.setattr(tiering, "matrix_tier", lambda m, c: 4)
    with pytest.raises((BakeError, ValueError)):
        bake.build()


def test_adversarial_a_due_date_the_engine_did_not_compute_is_refused(monkeypatch):
    from pipeline.governance import bake
    from pipeline.governance.readers import BakeError
    from riskvalidation.governance import findings

    real = findings.due_date
    monkeypatch.setattr(findings, "due_date", lambda raised, days: real(raised, days) + timedelta(days=1))
    with pytest.raises((BakeError, ValueError)):
        bake.build()


def test_adversarial_an_opinion_the_engine_did_not_compute_is_refused(monkeypatch):
    from pipeline.governance import bake
    from pipeline.governance.readers import BakeError
    from riskvalidation.governance import opinion, report

    monkeypatch.setattr(opinion, "opinion_level", lambda pairs: 1)
    monkeypatch.setattr(report, "opinion_level", lambda pairs: 1)  # the report module binds the name at import
    with pytest.raises((BakeError, ValueError)):
        bake.build()


def test_adversarial_a_schedule_the_engine_did_not_compute_is_refused(monkeypatch):
    from pipeline.governance import bake
    from pipeline.governance.readers import BakeError
    from riskvalidation.governance import schedule

    real = schedule.next_dates
    monkeypatch.setattr(schedule, "next_dates", lambda tier, last, *a, **k: tuple(None if d is None else d + timedelta(days=1) for d in real(tier, last, *a, **k)))
    with pytest.raises((BakeError, ValueError)):
        bake.build()


def test_adversarial_an_approval_text_planted_in_any_document_is_refused(baked):
    from pipeline.governance import bake
    from pipeline.governance.readers import BakeError

    inv = copy.deepcopy(baked.inventory)
    inv["entries"][0]["lifecycle"]["basis"] = "The model is approved by Contraste."
    with pytest.raises(BakeError, match="approv"):
        bake.check_documents(inv, baked.findings, baked.appetite, baked.reports, gs.copied_texts())
    inv = copy.deepcopy(baked.inventory)
    inv["entries"][0]["title"]["es"] = "Modelo aprobado y certificado"
    with pytest.raises(BakeError):
        bake.check_documents(inv, baked.findings, baked.appetite, baked.reports, gs.copied_texts())
    inv = copy.deepcopy(baked.inventory)
    inv["entries"][0]["scope"]["basis"] = "The entry is compliant with SR 26-2."
    with pytest.raises(BakeError, match="compliance"):
        bake.check_documents(inv, baked.findings, baked.appetite, baked.reports, gs.copied_texts())


def test_adversarial_a_convention_called_regulatory_is_refused(baked):
    from pipeline.governance import bake
    from pipeline.governance.readers import BakeError

    inv = copy.deepcopy(baked.inventory)
    inv["conventions"]["frequency"]["label"] = "regulatory"
    with pytest.raises(BakeError, match="regulatory"):
        bake.check_documents(inv, baked.findings, baked.appetite, baked.reports, gs.copied_texts())
    inv = copy.deepcopy(baked.inventory)
    inv["conventions"]["frequency"]["basis"] = "a regulatory requirement of the supervisor"
    with pytest.raises(BakeError):
        bake.check_documents(inv, baked.findings, baked.appetite, baked.reports, gs.copied_texts())


def test_adversarial_a_wall_clock_as_of_date_is_refused(baked):
    """The as-of date is the newest CHANGELOG heading: a date after it (the clock) or before a raised date is refused by the checker."""
    from pipeline.governance import bake
    from pipeline.governance.readers import BakeError

    fnd = copy.deepcopy(baked.findings)
    fnd["as_of"] = "2020-01-01"
    with pytest.raises(BakeError):
        bake.check_documents(baked.inventory, fnd, baked.appetite, baked.reports, gs.copied_texts())
    inv = copy.deepcopy(baked.inventory)
    inv["as_of"] = (date.fromisoformat(inv["as_of"]) + timedelta(days=30)).isoformat()
    with pytest.raises(BakeError, match="as_of"):
        bake.check_documents(inv, baked.findings, baked.appetite, baked.reports, gs.copied_texts())


def test_adversarial_an_edge_to_an_unknown_entry_or_a_cycle_is_refused(baked):
    from pipeline.governance import bake
    from pipeline.governance.readers import BakeError

    inv = copy.deepcopy(baked.inventory)
    inv["edges"].append({"upstream": inv["entries"][0]["key"], "downstream": "C99/none", "kind": "code", "stated_source": "planted"})
    with pytest.raises(BakeError, match="C99/none"):
        bake.check_documents(inv, baked.findings, baked.appetite, baked.reports, gs.copied_texts())
    inv = copy.deepcopy(baked.inventory)
    e = inv["edges"][0]
    inv["edges"].append({"upstream": e["downstream"], "downstream": e["upstream"], "kind": "code", "stated_source": "planted"})
    with pytest.raises(BakeError, match="cycle"):
        bake.check_documents(inv, baked.findings, baked.appetite, baked.reports, gs.copied_texts())


def test_adversarial_a_variant_assigned_to_a_fit_by_name_similarity_alone_stays_excluded(baked):
    """C05 ldp-sim-0 shares only a name prefix with the ldp fit: no committed identity places it, so the bake excludes it."""
    inv = baked.inventory
    assert not any(v["variant_id"] == "ldp-sim-0" for e in inv["entries"] for v in e["variants"])
    x = next(x for x in inv["excluded"] if x["variant_id"] == "ldp-sim-0")
    assert x["reason"]["en"].strip() and "ldp-sim-0" not in {r["variant_id"] for r in baked.findings["rows"]}


def test_adversarial_an_input_without_its_pointer_or_tag_is_refused(tmp_path):
    from pipeline.governance import bake
    from pipeline.governance.readers import BakeError

    for mutate, text in (
        (lambda d: d["cases"]["C20"]["tier"]["regulatory_use"].update(pointer=""), "C20"),
        (lambda d: d["cases"]["C02"]["tier"]["decision_criticality"].update(tag="guess"), "C02"),
        (lambda d: d["cases"]["C20"]["tier"]["factors"][2].update(pointer=None), "C20"),
        (lambda d: d["cases"]["C02"]["tier"]["exposure"].update(basis=""), "C02"),
    ):
        tree = gs.copy_tree(tmp_path / f"t{abs(hash(text)) % 99}")
        p = tree / "data-pipeline/pipeline/governance/inputs.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        mutate(d)
        p.write_text(json.dumps(d), encoding="utf-8")
        with pytest.raises(BakeError, match=text):
            bake.build(tree)
        import shutil

        shutil.rmtree(tree)


def test_adversarial_a_register_row_without_its_variant_document_is_found(baked):
    """Every register row traces to a finding of a committed variant document: a row planted with an unknown id has none."""
    planted = copy.deepcopy(baked.findings["rows"][0])
    planted["id"] = "PLANTED"
    doc = gs.read(f"data/derived/{planted['case_id']}/{planted['variant_id']}.json")
    assert not any(f["id"] == "PLANTED" for f in doc["findings"])
    sm = gs.load_semantics()
    fnd = copy.deepcopy(baked.findings)
    fnd["rows"][0]["key"] = "C01/holdout/PLANTED"
    assert any("key is not case_id/variant_id/id" in m for m in sm.violations(fnd))


def test_adversarial_a_changed_tier_input_changes_the_entry_and_is_found(tmp_path, baked):
    """A decision-criticality score of 4 for C03 lifts M to 4 and the tier from 2 to 1; the bake follows the input, and the committed bytes no longer match."""
    from pipeline.governance import bake

    tree = gs.copy_tree(tmp_path / "t")
    p = tree / "data-pipeline/pipeline/governance/inputs.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["cases"]["C03"]["tier"]["decision_criticality"]["score"] = 4
    p.write_text(json.dumps(d), encoding="utf-8")
    changed = bake.build(tree)
    was = next(e for e in baked.inventory["entries"] if e["key"] == "C03/sba-7a")["tier_block"]["tier"]
    now = next(e for e in changed.inventory["entries"] if e["key"] == "C03/sba-7a")["tier_block"]["tier"]
    assert (was, now) == (2, 1)
    assert bake.serialise(changed.inventory) != bake.serialise(baked.inventory)
