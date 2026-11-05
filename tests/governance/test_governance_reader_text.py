"""U16-F10p (the third capture review, R3 c23 B3 and B5): the reader text of the governance documents carries no plan or decision code
(``W15-13``, ``(W15-5)``) and no engine key or developer text (``test_id@model``, ``risk_accepted``, ``dim_cube``, ``bake``), in either
language. Tested on the producer's functions and inputs; the documents are re-baked by the integrator.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pipeline.governance.reader import reader_text

INPUTS = Path(__file__).resolve().parents[2] / "data-pipeline" / "pipeline" / "governance" / "inputs.json"
PLAN = re.compile(r"\bW15-\d+\b")
ENGINE = re.compile(r"test_id@|risk_accepted|dim_cube|spec\(|KeyError|\bbake\b")


def test_a_leading_or_bracketed_plan_code_leaves_the_sentence_whole():
    assert reader_text({"en": "W15-13: the date of the newest release heading.", "es": "W15-13: la fecha del encabezado."}) == {
        "en": "The date of the newest release heading.", "es": "La fecha del encabezado."}
    assert reader_text({"en": "open results or stated limits (W15-5)", "es": "resultados abiertos o límites declarados (W15-5)"}) == {
        "en": "open results or stated limits", "es": "resultados abiertos o límites declarados"}
    assert reader_text({"en": "a convention (W15-3, W15-4); the rest", "es": "una convención (W15-3, W15-4); el resto"}) == {
        "en": "a convention; the rest", "es": "una convención; el resto"}


def test_the_anchor_reason_of_a_finding_without_a_test_row_reads_in_words():
    engine = {"en": "the evidence is not a test_id@model row (it is a design:, contract:, rate: or bare test id), so no statistic is read",
              "es": "la evidencia no es una fila test_id@modelo (es design:, contract:, rate: o un id de prueba sin modelo), por lo que no se lee estadístico"}
    out = reader_text(engine)
    assert out == {"en": "the finding cites a design limit, a contract check or a rate, not one test row of a model, so no statistic is read",
                   "es": "el hallazgo cita un límite de diseño, una verificación de contrato o una tasa, no una fila de prueba de un modelo, por lo que no se lee estadístico"}


def test_engine_keys_become_words():
    out = reader_text({"en": "1 red row on the mean initial margin against ORE's dim_cube; not risk_accepted",
                       "es": "1 fila roja sobre el margen inicial medio frente al dim_cube de ORE; no risk_accepted"})
    assert out == {"en": "1 red row on the mean initial margin against ORE's dynamic initial margin cube; not risk accepted",
                   "es": "1 fila roja sobre el margen inicial medio frente al cubo de margen inicial dinámico de ORE; no aceptados como riesgo"}


def test_the_as_of_basis_the_bake_writes_carries_no_plan_code_and_no_developer_word():
    basis = json.loads(INPUTS.read_text(encoding="utf-8"))["as_of"]["basis"]
    for lang in ("en", "es"):
        assert not PLAN.search(basis[lang]), basis[lang]
        assert not ENGINE.search(basis[lang]), basis[lang]


def test_the_engine_report_element_reads_cadena_de_calculo_in_spanish():
    # U16-F11 (ruling of 2026-10-27): the engine (riskvalidation 1.0.1) writes "pipeline"; the Spanish page says one term for it.
    out = reader_text({"en": "Independent replication of the pipeline", "es": "Replicación independiente del pipeline"})
    assert out["es"] == "Replicación independiente de la cadena de cálculo"
    assert out["en"] == "Independent replication of the pipeline"
    assert reader_text({"es": "el pipeline corre; el pipeline y pipeline"})["es"] == "la cadena de cálculo corre; la cadena de cálculo y cadena de cálculo"
    assert "canalización" not in reader_text({"es": "del pipeline"})["es"]
    # a path or a key that holds the word is code, never text
    assert reader_text({"es": "data-pipeline/ y el pipeline"})["es"] == "data-pipeline/ y la cadena de cálculo"
