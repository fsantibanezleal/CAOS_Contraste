"""U16-F12c (R4 batch c14 NB1 and n5, C11): when no model fails an eligibility gate the finding says which gates did not run, with their
counts by tail level, never that every model passed them (mixed-2023: conditional coverage not evaluated for 17 of 17 models at the 1 %
tail); the Spanish rule names the coverage test, not "POF". Tested on the producer's functions, never by re-baking."""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.cases.c11 import documents
from pipeline.core.text import NBSP

ROOT = Path(__file__).resolve().parents[2]


def _doc(w):
    return json.loads((ROOT / "data" / "derived" / "C11" / f"{w}.json").read_text(encoding="utf-8"))


def _model(mid, eligible):
    return {"model_id": mid, "eligible": eligible}


def _row(test, mid, alpha, light):
    return {"test_id": test, "model_id": mid, "segment": f"alpha={alpha}", "light": light}


def test_the_committed_mixed_window_states_the_gates_that_did_not_run():
    d = _doc("mixed-2023")
    out = documents.findings(d["outputs"]["models"], d["tests"])
    f = next(x for x in out if x["id"] == "c11-gates")
    en, es = f["title"]["en"], f["title"]["es"]
    assert "pass every eligibility gate" not in en
    assert "pasan todas las compuertas" not in es
    assert en == ("No model fails an eligibility gate, but not every gate ran: the conditional coverage test was not evaluated for "
                  f"17 of 17 models at the 1{NBSP}% tail and 15 of 17 at the 2.5{NBSP}% tail, the ES test for 3 of 17 at each tail.")
    assert es == ("Ningún modelo falla una compuerta de elegibilidad, pero no todas corrieron: la prueba de cobertura condicional no se "
                  f"evaluó para 17 de 17 modelos en la cola de 1{NBSP}% y para 15 de 17 en la de 2,5{NBSP}%; la prueba de ES, para 3 de 17 "
                  "en cada cola.")
    assert (f["severity"], f["status"]) == ("S4", "open")


def test_a_window_where_every_gate_ran_and_passed_says_so_accepted():
    models = [_model("a", True), _model("b", True)]
    tests = [_row(g, m, a, "green") for g in documents.GATES for m in ("a", "b") for a in (0.01, 0.025)]
    out = documents.findings(models, tests)
    assert [(f["id"], f["severity"], f["status"]) for f in out] == [("c11-gates", "S4", "accepted")]
    assert out[0]["title"]["en"] == "All 2 models pass every eligibility gate (coverage, conditional coverage and the ES test)."


def test_a_gate_not_run_for_one_model_at_one_tail_is_counted():
    models = [_model("a", True), _model("b", True)]
    tests = [_row(g, m, a, "green") for g in documents.GATES for m in ("a", "b") for a in (0.01, 0.025)]
    tests[0] = {**tests[0], "light": "not_evaluated"}
    en = documents.findings(models, tests)[0]["title"]["en"]
    assert en.endswith(f"the coverage test was not evaluated for 1 of 2 models at the 1{NBSP}% tail.")


def test_no_committed_window_claims_a_gate_passed_that_did_not_run():
    for w in ("calm-2004-06", "equity-2007-09", "equity-2020", "fx-2008", "mixed-2023", "rates-2022"):
        d = _doc(w)
        for f in documents.findings(d["outputs"]["models"], d["tests"]):
            if "pass every eligibility gate" in f["title"]["en"]:
                gates = [t for t in d["tests"] if t["test_id"] in documents.GATES]
                assert all(t["light"] != "not_evaluated" for t in gates), w


def test_the_spanish_rule_names_the_coverage_test_not_pof():
    assert "POF" not in documents.SCORING_RULE["es"]
    assert "proporción de fallas" in documents.SCORING_RULE["es"]


def test_the_eligible_count_label_says_no_gate_rejects_them():
    assert documents.ELIGIBLE_LABEL == {"en": "Models no eligibility gate rejects", "es": "Modelos que ninguna compuerta de elegibilidad rechaza"}
