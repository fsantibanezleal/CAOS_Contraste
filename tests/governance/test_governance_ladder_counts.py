"""SHOW-F F7: the register's C11 gate rows count the ladder their window document holds.

The viz review of the story found "17 of 17 models fail at least one eligibility gate" in the register beside a step that counts 18 models: the
register had not been re-baked after the ladder grew. The bake now refuses a window document whose own gate finding quotes a model count that is
not the size of its ladder (``outputs.models``), and a committed register that quotes another count than the documents is found by the second test
(it is re-baked at the release, after the manifests index, so it is marked as the expected failure until then; the marker flips the suite red the day
the register is re-baked, which is the signal to delete it).
"""
from __future__ import annotations

import json
import re

import gov_support as gs
import pytest

C11_WINDOWS = ["equity-2007-09", "equity-2020", "rates-2022", "fx-2008", "mixed-2023", "calm-2004-06"]


def _doc(window: str) -> dict:
    return gs.read(f"data/derived/C11/{window}.json")


def test_the_ladder_size_check_accepts_every_committed_window_document():
    from pipeline.governance.bake import ladder_size_problems

    for w in C11_WINDOWS:
        assert ladder_size_problems(_doc(w), f"C11/{w}.json") == [], w


def test_a_gate_finding_that_counts_another_ladder_is_found_in_both_languages():
    from pipeline.governance.bake import ladder_size_problems

    doc = _doc("equity-2007-09")
    size = len(doc["outputs"]["models"])
    assert size == 18
    for f in doc["findings"]:
        if f["id"] == "c11-gates":
            f["title"]["en"] = f["title"]["en"].replace(f"{size} of {size}", f"{size - 1} of {size - 1}")
            f["title"]["es"] = f["title"]["es"].replace(f"{size} de {size}", f"{size - 1} de {size - 1}")
    problems = ladder_size_problems(doc, "C11/equity-2007-09.json")
    assert len(problems) == 2
    assert all("ladder has 18" in p and "C11/equity-2007-09.json" in p for p in problems)


def test_the_check_reads_the_not_every_gate_ran_form_and_the_all_pass_form():
    from pipeline.governance.bake import ladder_size_problems

    base = {"case_id": "C11", "outputs": {"models": [{}] * 18}}
    ok = [
        "No model fails an eligibility gate, but not every gate ran: the conditional coverage test was not evaluated for 18 of 18 models at the 1 % tail and 15 of 18 at the 2.5 % tail, the ES test for 3 of 18 at each tail.",
        "All 18 models pass every eligibility gate (coverage, conditional coverage and the ES test).",
        "18 of 18 models fail at least one eligibility gate (coverage, conditional coverage or the ES test).",
    ]
    for t in ok:
        assert ladder_size_problems({**base, "findings": [{"id": "c11-gates", "title": {"en": t, "es": t.replace(" of ", " de ")}}]}, "x") == [], t
    for t in [ok[0].replace("15 of 18", "15 of 17"), ok[1].replace("All 18", "All 17"), ok[2].replace("18 of 18", "17 of 17")]:
        assert ladder_size_problems({**base, "findings": [{"id": "c11-gates", "title": {"en": t, "es": t}}]}, "x"), t


def test_a_case_that_is_not_c11_or_a_document_without_a_ladder_is_not_checked():
    from pipeline.governance.bake import ladder_size_problems

    assert ladder_size_problems({"case_id": "C13", "findings": [{"id": "c11-gates", "title": {"en": "3 of 99 models", "es": ""}}]}, "x") == []
    assert ladder_size_problems({"case_id": "C11", "findings": [{"id": "c11-gates", "title": {"en": "3 of 99 models", "es": ""}}]}, "x") == []


def test_the_bake_refuses_a_window_document_whose_gate_finding_counts_another_ladder(tmp_path):
    from pipeline.governance import bake
    from pipeline.governance.readers import BakeError

    tree = gs.copy_tree(tmp_path / "tree")
    p = tree / "data/derived/C11/equity-2007-09.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    for f in d["findings"]:
        if f["id"] == "c11-gates":
            f["title"]["en"] = re.sub(r"\b18\b", "17", f["title"]["en"])
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(BakeError, match=r"C11/equity-2007-09\.json.*ladder has 18"):
        bake.build(tree)


@pytest.mark.xfail(strict=True, reason="the committed register still counts the 17-model ladder; it is re-baked at the release after the manifests index (brief show-f-story-fixes-2026-11-07)")
def test_the_committed_register_quotes_the_ladder_size_of_each_window_document():
    findings = gs.read("data/derived/governance/findings.json")
    rows = {r["key"]: r for r in findings["rows"] if r["id"] == "c11-gates"}
    assert len(rows) == len(C11_WINDOWS)
    for w in C11_WINDOWS:
        size = len(_doc(w)["outputs"]["models"])
        title = rows[f"C11/{w}/c11-gates"]["title"]["en"]
        counted = {int(m.group(1) or m.group(2)) for m in re.finditer(r"\bof (\d+)\b|\bAll (\d+) models\b", title)}
        assert counted <= {size}, f"{w}: the register quotes {sorted(counted)}, the document's ladder has {size}"
