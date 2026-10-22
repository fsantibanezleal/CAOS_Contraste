"""U16-R2 b04 B4, B7 (PR-C07-2 and V09-2): the committed C09 documents say in Spanish what the Spanish view prints."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from f3_spanish_text import ROOT, bitexts, document_leaks, load  # noqa: E402

LEVELS = sorted(p.name for p in (ROOT / "data" / "derived" / "C09").glob("level-*.json"))


@pytest.mark.parametrize("name", LEVELS)
def test_no_spanish_text_carries_an_english_number_form(name):
    doc = load(f"data/derived/C09/{name}")
    assert document_leaks(doc) == []
    assert len(list(bitexts(doc["findings"]))) == 6


@pytest.mark.parametrize("name", LEVELS)
def test_the_floor_rule_is_bilingual(name):
    rule = load(f"data/derived/C09/{name}")["outputs"]["ead_floor"]["rule"]
    assert isinstance(rule, dict) and set(rule) == {"en", "es"}
    assert "CRE32.36, CRE32.64" in rule["en"] and "fuera de balance" in rule["es"] and "(CRE32.36, CRE32.64)" in rule["es"]


def test_the_findings_write_their_numbers_in_the_language_of_the_title():
    from pipeline.cases.c09 import documents

    en, es = documents._side(-0.0214)
    assert en == "0.021 below" and es == "0,021 por debajo"
    assert documents._g(1.5, "es") == "1,5" and documents._g(2.0, "es") == "2" and documents._g(2.0, "en") == "2"
