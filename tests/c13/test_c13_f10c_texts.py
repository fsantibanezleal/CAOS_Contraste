"""U16-F10c (R3 batch c14, C13): one deficiency has one name and one verb per language, the names the views use ("base omitida",
"sembrada"), and the Spanish producer texts say "prueba", never "test" or "backtesting" (the 2026-10-27 ruling). Tested on the
producer's functions over the committed outputs, never by re-baking."""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from pipeline.cases import c13
from pipeline.cases.c13 import documents

ROOT = Path(__file__).resolve().parents[2]
VARIANTS = ["none", "missing-basis", "omitted-factor", "stale-volatility", "time-misalignment", "wrong-correlation"]
ENGLISH_ES = re.compile(r"\btests?\b|\bbacktesting\b|\bback-?tests?\b", re.I)
#: the names the C13 views give each deficiency (frontend/src/workbench/c13/selection.ts DEFICIENCY_TEXT), lower case in a sentence
VIEW_NAMES = {"missing-basis": ("missing basis", "base omitida"), "stale-volatility": ("stale volatility", "volatilidad desactualizada"),
              "wrong-correlation": ("wrong correlation", "correlación errónea"), "omitted-factor": ("omitted risk factor", "factor de riesgo omitido"),
              "time-misalignment": ("time misalignment", "desfase temporal")}


def _outputs(v: str) -> dict:
    doc = json.loads((ROOT / "data" / "derived" / "C13" / f"{v}.json").read_text(encoding="utf-8"))
    return copy.deepcopy(doc["outputs"])


@pytest.mark.parametrize("v", VARIANTS)
def test_the_spanish_titles_say_prueba_and_sembrada(v):
    for f in documents.findings(_outputs(v)):
        es = f["title"]["es"]
        assert not ENGLISH_ES.search(es), es
        assert "plantad" not in es, es


@pytest.mark.parametrize("v", [x for x in VARIANTS if x != "none"])
def test_a_deficiency_is_named_as_the_views_name_it(v):
    en, es = VIEW_NAMES[v]
    pla = next(f for f in documents.findings(_outputs(v)) if f["id"] == "F-PLA")
    assert f"the planted {en} in" in pla["title"]["en"], pla["title"]["en"]
    assert f"la deficiencia sembrada ({es})" in pla["title"]["es"], pla["title"]["es"]


def test_the_mechanism_of_the_control_and_the_notice_say_prueba_and_sembrada():
    assert not ENGLISH_ES.search(documents.MECHANISM["none"]["es"])
    assert "plantad" not in documents.NOTICE["es"] and "sembrada" in documents.NOTICE["es"]
    assert "planta nada" not in documents.TRUE_MODEL["es"]


def test_the_case_title_and_question_say_prueba_retrospectiva():
    for k in ("title", "question"):
        es = getattr(c13.C13, k)["es"]
        assert not ENGLISH_ES.search(es), es
        assert "prueba retrospectiva de mesa" in es or "pruebas retrospectivas de mesa" in es, es


def test_the_sign_convention_says_nocional_as_the_views():
    es = documents.SIGN_CONVENTION["definition"]["es"]
    assert "nominal" not in es and "nocional de la mesa" in es
