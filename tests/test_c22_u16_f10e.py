"""U16-F10e (fix round 4, the third capture review R3, batch c22): the C22 producer texts.

B4 the WP14 scenario of the cell that does not agree is named in words as WP14's Table 3 describes it, never by its code DV_LV; B5 the
Spanish test and panel labels say "prueba retrospectiva" and "impulso", not "Backtest" and "Momentum" (ruling of 2026-10-27); m9
Székely with its accent; m4 a Spanish percent with its no-break space in the note it touches."""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pipeline.cases.c22_studies as studies
import pipeline.cases.c22_validator as validator


def _texts(module) -> list[tuple[str, str]]:
    out = []
    for node in ast.walk(ast.parse(Path(module.__file__).read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_t" and len(node.args) == 2:
            en, es = ("".join(s.value for s in ast.walk(a) if isinstance(s, ast.Constant) and isinstance(s.value, str)) for a in node.args)
            out.append((en, es))
    return out


def test_b4_no_wp14_scenario_code_in_reader_text() -> None:
    for module in (studies, validator):
        for en, es in _texts(module):
            assert not re.search(r"\b(I_SC|I_LC|DC_SC|DC_LC|I_SV|I_LV|DV_SV|DV_LV)\b", en + es), en
    notes = [en for en, _ in _texts(validator) if "does not agree" in en]
    assert notes and "time dependence, varying asset correlations, larger and varying unconditional PDs" in notes[0]
    es = [s for _, s in _texts(validator) if "no concuerda" in s][0]
    assert "al 0,1\u00a0%" in es and "dependencia temporal" in es


def test_b5_no_backtest_and_no_momentum_in_spanish_and_m9_szekely() -> None:
    for module in (studies, validator):
        for en, es in _texts(module):
            assert not re.search(r"(?i)\bbacktests?\b|\bmomentum\b", es), es
            assert "Szekely" not in en + es
    assert studies.TEST_LABEL["market.acerbi_szekely"]["es"] == "Prueba de ES de Acerbi-Székely"
