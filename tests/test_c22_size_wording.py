"""The size wording of C22: a count of tests that pass the size screen on the committed cells is not "hold their size".

The size-and-power manuscript reserves "hold their size" for its own definition (an interval that includes the level, on 200,000
null repetitions); the product's count is the screen's on cells of 4,000 repetitions, so the producer and the documents it writes
say "pass the size screen" (Spanish in step: "pasan el filtro de tamaño"). The committed documents are checked as committed (no
test bakes the case, ADR-0074)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
C22 = ROOT / "data" / "derived" / "C22"
PRODUCER = ROOT / "data-pipeline" / "pipeline" / "cases" / "c22_validator.py"
OLD = re.compile(r"hold(s)? (their|its) size|mantienen su tama|mantiene su tama", re.I)


def _texts(node, out: list[str]) -> list[str]:
    if isinstance(node, dict):
        if set(node) == {"en", "es"} and all(isinstance(v, str) for v in node.values()):
            out.extend(node.values())
        else:
            for v in node.values():
                _texts(v, out)
    elif isinstance(node, list):
        for v in node:
            _texts(v, out)
    return out


def _doc(name: str) -> dict:
    return json.loads((C22 / f"{name}.json").read_text(encoding="utf-8"))


def test_the_producer_never_says_hold_their_size():
    assert OLD.search(PRODUCER.read_text(encoding="utf-8")) is None


def test_no_committed_c22_document_says_hold_their_size_in_either_language():
    for p in sorted(C22.glob("*.json")):
        found = [t for t in _texts(json.loads(p.read_text(encoding="utf-8")), []) if OLD.search(t)]
        assert found == [], (p.name, found[:1])


def test_the_counts_say_pass_the_size_screen_in_both_languages():
    # the validator writes both counts and the F-OTHER-SIZE finding into the null variant's document
    null = _doc("null")
    for key in ("tests_within_bound", "other_tests_within_bound"):
        label = null["impact"][key]["label"]
        assert "pass the size screen" in label["en"] and "pasan el filtro de tamaño" in label["es"]
    f = next(x for x in null["findings"] if x["id"] == "F-OTHER-SIZE")["title"]
    assert "pass the size screen" in f["en"] and "pasan el filtro de tamaño" in f["es"]


def test_the_transition_finding_states_the_order_test_as_the_cells_measure_it():
    doc = _doc("null")
    f = next(x for x in doc["findings"] if x["id"] == "F-TRANSITION-SIZE")["title"]
    sims = {s["key"]: s for s in doc["outputs"]["simulations"]}
    small, big = sims["rating.markov_order@null"]["rates"]["p<0.05"], sims["rating.markov_order@null-20000"]["rates"]["p<0.05"]
    assert "pass the size screen" in f["en"] and "pasan el filtro de tamaño" in f["es"]
    # the interval of the 4,000-repetition cell lies wholly above the level: the finding says so, from the document's own numbers
    assert small["wilson_low"] > 0.05
    assert "above" in f["en"] and "interval" in f["en"] and "sobre" in f["es"] and "intervalo" in f["es"]
    from pipeline.cases.c22_validator import _pct

    for rate in (small, big):
        for x in (rate["rate"], rate["wilson_low"], rate["wilson_high"]):
            assert _pct(x, 2)["en"] in f["en"] and _pct(x, 2)["es"] in f["es"], x
