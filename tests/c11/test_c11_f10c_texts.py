"""U16-F10c (R3 batch c12, C11): no plan-unit code or internal decision id is printed in reader text ("the U8 bake", "(decision D3)",
"(D-10)"; the 2026-10-27 ruling on raw ids); the Spanish producer texts say "prueba retrospectiva", never "backtest"; a window
where every model passes its gates records no finding of zero failures, and a window with no eligible model says so. Tested on the
producer's functions and constants, never by re-baking."""
from __future__ import annotations

import re

import numpy as np

from pipeline.cases.c11 import _case, documents, forecast

RAW = re.compile(r"\bU\d+\b|\(decisi[oó]n [A-Z]\d+\)|\(D-\d+\)")
ENGLISH_ES = re.compile(r"\bback-?tests?\b|\bbacktesting\b", re.I)


def test_the_challenger_reason_names_no_plan_unit():
    reason = forecast.CHALLENGER["reason"]
    assert not RAW.search(reason), reason
    assert reason == "challenger only: it must enter the 90 percent MCS on FZ0 out of sample, and the published run does not train it"


def test_no_rung_source_cites_an_internal_decision():
    for s in forecast.LADDER:
        assert not RAW.search(s.source), s.source
    assert not RAW.search(forecast.CHALLENGER["source"])


def test_the_traffic_light_reason_cites_no_decision_id():
    tl = documents.traffic_light(np.zeros(104, dtype=bool), 104)
    assert tl["final_zone"] == "not_evaluated"
    assert not RAW.search(tl["reason"]), tl["reason"]
    assert tl["reason"] == ("fewer than 250 forecast days (104): the Basel traffic light of MAR32.9 is defined on 250 observations and "
                            "the window has no lead-in")


def test_the_case_title_and_question_say_prueba_retrospectiva_in_spanish():
    m = {"title": _case.C11.title, "question": _case.C11.question}
    for k in ("title", "question"):
        assert not ENGLISH_ES.search(m[k]["es"]), m[k]["es"]
    assert m["title"]["es"].startswith("Pruebas retrospectivas de VaR/ES de mercado")


def test_the_scoring_rule_says_pruebas_retrospectivas_in_spanish():
    rule = documents.SCORING_RULE
    assert not ENGLISH_ES.search(rule["es"]), rule["es"]
    assert rule["es"].startswith("Las pruebas retrospectivas tradicionales")


def _model(mid, eligible):
    return {"model_id": mid, "eligible": eligible}


def test_no_finding_records_zero_failures():
    """A window where every model passes says so, accepted, instead of an open finding of "0 of 17 models fail"."""
    out = documents.findings([_model("a", True), _model("b", True)], [])
    assert all(not f["title"]["en"].startswith("0 of") for f in out)
    assert [(f["id"], f["severity"], f["status"]) for f in out] == [("c11-gates", "S4", "accepted")]
    assert out[0]["title"]["en"] == "All 2 models pass every eligibility gate (coverage, conditional coverage and the ES test)."
    assert out[0]["title"]["es"] == "Los 2 modelos pasan todas las compuertas de elegibilidad (cobertura, cobertura condicional y la prueba de ES)."


def test_a_finding_on_the_models_that_fail_keeps_its_count():
    out = documents.findings([_model("a", False), _model("b", True)], [])
    assert out[0]["id"] == "c11-gates" and out[0]["title"]["en"].startswith("1 of 2 models fail")


def test_no_champion_says_no_model_is_eligible_when_none_is():
    assert documents.no_champion_reason(n_eligible=0) == "no model is eligible: every model fails at least one gate"
    assert documents.no_champion_reason(n_eligible=3) == "no eligible model has an ES on every day, so none has an FZ0 score to rank"
