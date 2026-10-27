"""U16-R2 b06 B2 (PR-C13): the committed C13 documents say in Spanish what the Spanish view prints, with the Spanish number form."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from f3_spanish_text import ROOT, document_leaks, load  # noqa: E402

FOLDER = ROOT / "data" / "derived" / "C13"
DOCUMENTS = sorted(p.name for p in FOLDER.glob("*.json"))


@pytest.mark.parametrize("name", DOCUMENTS)
def test_no_spanish_text_carries_an_english_number_form(name):
    assert document_leaks(load(f"data/derived/C13/{name}")) == []


def test_the_pla_title_names_the_deficiency_in_spanish_and_writes_its_numbers_the_spanish_way():
    doc = load("data/derived/C13/omitted-factor.json")
    title = next(f for f in doc["findings"] if f["id"] == "F-PLA")["title"]
    assert "factor de riesgo omitido" in title["es"] and "omitted risk factor" in title["en"]  # U16-F10c names the factor a risk factor
    assert "\u00a0%" in title["es"] and "1.000 replicaciones" in title["es"] and "1,000 replications" in title["en"]
