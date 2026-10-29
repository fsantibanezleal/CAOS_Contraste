"""BS-14 in the committed C04 documents: the withdrawals family's rungs carry the coverage study at the bake's 200
repetitions, its verdict is what the verdict function reads off those rungs, the agency documents carry the anchored k
of the real cohorts recomputed here from their own counts, and the findings state the result in both languages with
the numbers the documents hold."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pytest

from pipeline.cases import c04_bounds as bnd

DERIVED = Path(__file__).resolve().parents[1] / "data" / "derived" / "C04"


def _doc(name: str) -> dict:
    return json.loads((DERIVED / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def withdrawals() -> dict:
    return _doc("withdrawals")


def test_every_rung_carries_the_study_at_the_bakes_repetitions(withdrawals):
    out = withdrawals["outputs"]
    assert [r["value"] for r in out["rungs"]] == [0.0, 1.0, 3.0, 9.0]
    for r in out["rungs"]:
        b = r["bounds"]
        assert b["level"] == 0.95 and len(b["truth"]) == 7
        assert [d["id"] for d in b["designs"]] == ["first_year", "pooled", "capture70", "first_year_x10"]
        assert all(d["reps"] == 200 for d in b["designs"])
        # the study's own seeds: never the rung's
        assert all(d["seed_key"].startswith("withdrawals-bounds:") and d["seed"] != r["seed"] for d in b["designs"])


def test_the_verdict_is_what_the_rungs_say(withdrawals):
    out = withdrawals["outputs"]
    assert out["bounds_verdict"] == json.loads(json.dumps(bnd.verdict(out["rungs"])))
    v = out["bounds_verdict"]
    assert v["reps"] == 200 and v["grade"] == 5
    # the criteria are the plan's, fixed before the run
    assert {(r["id"], r["threshold"]) for r in v["rows"] if r["id"] != "anchored-better"} == {
        ("anchored-coverage", 0.90), ("existing-coverage", 0.50)}


def test_the_truth_is_the_generators_and_the_rungs_agree_on_it(withdrawals):
    out = withdrawals["outputs"]
    truths = {tuple(r["bounds"]["truth"]) for r in out["rungs"]}
    assert len(truths) == 1
    assert list(truths.pop()) == pytest.approx(out["generator"]["pd_1y"], rel=1e-9)


def test_the_finding_states_the_hypothesis_the_numbers_and_the_verdict(withdrawals):
    f = next(x for x in withdrawals["findings"] if x["id"] == "F-WITHDRAW-BOUNDS")
    v = withdrawals["outputs"]["bounds_verdict"]
    en, es = f["title"]["en"], f["title"]["es"]
    first = next(r for r in v["rows"] if r["id"] == "anchored-coverage" and r["design"] == "first_year"
                 and r["informative"] == 9.0)
    assert f"{100 * first['value']:.1f}%" in en
    assert ("holds" if v["summary"]["anchored_covers_90"] else "does not hold") in en
    assert ("se sostiene" if v["summary"]["anchored_covers_90"] else "no se sostiene") in es
    assert ("is met" if v["summary"]["refuted"] else "is not met") in en
    assert "200 repetitions" in en and "200 repeticiones" in es
    for text in (en, es):
        assert "—" not in text and "→" not in text


@pytest.mark.parametrize("agency", ["sp", "moodys", "fitch"])
def test_the_agency_documents_carry_the_anchor(agency):
    wb = _doc(agency)["outputs"]["withdrawal_bounds"]
    if agency == "moodys":  # no default category on its transition page: there is no D to anchor
        assert wb is None
        return
    assert wb["level"] == 0.95 and wb["stability_share"] == 0.80
    assert [g["grade"] for g in wb["grades"]] == ["AAA", "AA", "A", "BBB", "BB", "B", "CCC-C"]
    for g in wb["grades"]:
        for rec in [*g["cohorts"], *([g["pooled"]] if g["pooled"] else [])]:
            # the anchored count X = N A / Na - D, clipped to [0, W], is the same one the engine inverts
            n = rec["defaults"] + rec["survivors"] + rec["withdrawn"]
            x = min(max(n * rec["anchor_defaults"] / rec["anchor_cohort"] - rec["defaults"], 0.0), rec["withdrawn"])
            assert rec["defaults_implied"] == pytest.approx(x, abs=1e-6)
            if rec["k"] is not None and rec["reason"] == "ok":
                assert rec["k"] == pytest.approx(x * rec["survivors"] / (rec["defaults"] * (rec["withdrawn"] - x)),
                                                 rel=1e-9) or rec["flag"] != "ok"


def test_the_pooled_counts_are_the_sums_of_the_cohorts():
    for agency in ("sp", "fitch"):
        for g in _doc(agency)["outputs"]["withdrawal_bounds"]["grades"]:
            if not g["cohorts"]:
                continue
            for field in ("defaults", "survivors", "withdrawn", "anchor_defaults", "anchor_cohort"):
                assert g["pooled"][field] == pytest.approx(sum(c[field] for c in g["cohorts"]))


def test_the_anchor_finding_is_in_both_languages_with_the_pooled_k():
    doc = _doc("sp")
    f = next(x for x in doc["findings"] if x["id"] == "F-WITHDRAW-ANCHOR")
    ccc = doc["outputs"]["withdrawal_bounds"]["grades"][6]
    k = ccc["pooled"]["k"]
    assert f"{k:.1f}" in f["title"]["en"]
    assert re.search(r"\d+,\d", f["title"]["es"])  # the Spanish decimal comma
    assert ("above" if ccc["k_above_1"]["holds"] else "not above") in f["title"]["en"]
    assert "—" not in f["title"]["en"] + f["title"]["es"]
    assert not any(x["id"] == "F-WITHDRAW-ANCHOR" for x in _doc("moodys")["findings"])


def test_existing_numbers_of_the_withdrawals_rungs_are_the_ones_the_page_quotes(withdrawals):
    # the plan's baseline: B's PD with withdrawals removed is understated by about a third, followed by about a seventh
    r9 = next(r for r in withdrawals["outputs"]["rungs"] if r["value"] == 9.0)
    truth = r9["pd_removed"]["truth"][5]
    assert -0.45 < r9["pd_removed"]["bias"][5] / truth < -0.25
    assert -0.25 < r9["pd_followed"]["bias"][5] / truth < -0.05
    assert math.isfinite(truth)
