"""U16-F10e (fix round 4, the third capture review R3, batch c21): the C21 producer texts.

B2 the Spanish conventions name the categories and the reference groups in Spanish; B4 the Spanish S4 finding quotes the Interagency
sentence in Spanish with the original marked and the Spanish name of the source; B5 no "odds" in the Spanish finding titles; B7 the
identifiers note says "the identifier", not the key ``id``; m4 one group contrast is singular."""
from __future__ import annotations

import re

from c21_support import VARIANTS, committed

from pipeline.cases.c21 import findings, legal


def _titles() -> list[dict[str, str]]:
    return [f["title"] for v in VARIANTS for f in findings.build(committed(v)["tests"])]


def test_b2_the_spanish_conventions_name_categories_and_reference_groups_in_spanish() -> None:
    es = legal.conventions_block()["group_exclusion"]["es"]
    for english in ("Joint", "Not Available", "Free Form Text Only", "White", "Not Hispanic or Latino", "Male"):
        assert not re.search(rf"\b{english}\b", es), (english, es)
    for spanish in ("Conjunto", "No disponible", "Solo texto libre", "Blanco", "No hispano ni latino", "Hombre"):
        assert spanish in es, spanish


def test_b4_the_spanish_quote_of_the_interagency_sentence() -> None:
    es = [t["es"] for t in _titles() if "indicador" in t["es"]]
    assert es
    for t in es:
        assert legal.QUOTES_ES["procedures"] in t, t
        assert "Procedimientos Interagenciales de Examen de Préstamos Justos" in t and "original en inglés" in t, t
        assert "Interagency Fair Lending Examination Procedures, cita en inglés" not in t


def test_b5_no_odds_in_the_spanish_titles_and_m4_the_singular() -> None:
    for t in _titles():
        assert not re.search(r"\bodds\b", t["es"]), t["es"]
        assert not re.search(r"\b1 (group contrasts|contrastes)\b", t["en"] + " " + t["es"]), t


def test_b7_the_identifiers_note_names_the_identifier() -> None:
    note = legal.conventions_block()["identifiers"]["note"]
    assert "id is the row" not in note["en"] and "the identifier is the row" in note["en"]
    assert "id es la" not in note["es"] and "el identificador es la" in note["es"]
