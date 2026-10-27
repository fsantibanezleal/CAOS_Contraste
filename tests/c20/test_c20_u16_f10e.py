"""U16-F10e (fix round 4, the third capture review R3, batch c20): the C20 producer texts.

B3 the synthetic-shift block commits the evaluation set's id and its row count as two fields (the view names the dataset and writes the
count in the reader's language); B7 the Spanish texts carry no "scoring" and no "benchmark" (ruling of 2026-10-27), and the latent
Spanish of the Taiwan variants writes Taiwan with its accent."""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pipeline.cases.c20 as pkg
from pipeline.cases.c20 import battery, conv, v_shift, v_shock

ENGLISH_IN_SPANISH = re.compile(r"\b(scoring|benchmark|bootstrap|commit|shock)\b|\bTaiwan\b")


def _spanish_args() -> list[tuple[str, int, str]]:
    """The Spanish argument of every ``t(en, es)`` call of the C20 producer (the texts a Spanish reader sees)."""
    out = []
    for path in Path(pkg.__file__).parent.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "t" and len(node.args) == 2:
                parts = [s.value for s in ast.walk(node.args[1]) if isinstance(s, ast.Constant) and isinstance(s.value, str)]
                out.append((path.name, node.lineno, "".join(parts)))
    return out


def test_b3_the_evaluation_set_is_its_id_and_its_rows() -> None:
    # the id and the count in the one string of the contract, the form the view parses into a name and a localised count
    block = v_shift.evaluation_set_block(3151)
    assert block == {"evaluation_set": "uci-polish-3year-holdout (3,151 rows, locked)"}
    assert v_shift.EVALUATION_SET == "uci-polish-3year-holdout"


def test_b7_the_sgcd_texts_say_scoring_and_benchmark_in_spanish() -> None:
    notice = conv.sgcd_notice()["text"]
    assert "scoring" not in notice["es"] and "calificación de crédito real" in notice["es"], notice["es"]
    limit = v_shock.SGCD_LIMIT
    assert "benchmark" not in limit["es"] and "scoring" not in limit["es"], limit["es"]
    assert "conjunto de referencia de investigación" in limit["es"]
    assert limit["en"].startswith("SGCD is a research benchmark")


def test_b7_no_english_technical_word_and_taiwan_with_its_accent_in_any_spanish_text() -> None:
    bad = [(f, n, s) for f, n, s in _spanish_args() if ENGLISH_IN_SPANISH.search(s)]
    assert bad == []
    assert "Taiwán" in battery.notice()["es"] and "benchmark" not in battery.notice()["es"]
