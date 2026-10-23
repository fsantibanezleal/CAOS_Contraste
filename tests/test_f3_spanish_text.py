"""The text checks of tests/f3_spanish_text.py: a citation locator is not an English number form, a decimal still is."""
from __future__ import annotations

from f3_spanish_text import leaks


def test_a_citation_locator_is_the_same_in_both_languages():
    pairs = [
        ("CMF CNCB Chapter B-1 (Circular 2.346), dossier 03 section D.3; read through riskvalidation.provisions.local_cl (2.1)",
         "CMF CNCB Capítulo B-1 (Circular 2.346), dossier 03 sección D.3; leído con riskvalidation.provisions.local_cl (2.1)"),
        ("Cohort matrix, pooled over the years (Anderson and Goodman 2.8)", "Matriz de cohortes, agrupada en los años (Anderson y Goodman 2.8)"),
    ]
    for en, es in pairs:
        assert leaks(en, es) == [], es


def test_a_decimal_point_or_a_glued_percent_in_a_spanish_sentence_still_leaks():
    assert leaks("The event rate is 0.0694 over 2.5 years", "La tasa de eventos es 0.0694 en 2.5 años") == ["0.0694", "2.5"]
    assert leaks("(LGD 50%)", "(LGD 50%)") == ["0%"]
    assert leaks("(Goodman 2.8) against 0.31", "(Goodman 2.8) frente a 0.31") == ["0.31"]
