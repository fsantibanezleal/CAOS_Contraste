"""U16-R2 b06 B2 (PR-C12): the committed C12 documents say in Spanish what the Spanish view prints, with the Spanish light words."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from f3_spanish_text import ROOT, document_leaks, load  # noqa: E402

FOLDER = ROOT / "data" / "derived" / "C12"
DOCUMENTS = sorted(p.name for p in FOLDER.glob("*.json"))


@pytest.mark.parametrize("name", DOCUMENTS)
def test_no_spanish_text_carries_an_english_number_form_or_light_word(name):
    assert document_leaks(load(f"data/derived/C12/{name}")) == []


def test_the_finding_titles_use_the_spanish_light_measure_and_count():
    titles = [f["title"]["es"] for name in DOCUMENTS for f in load(f"data/derived/C12/{name}").get("findings", [])]
    assert titles
    assert all("fila" in t and "(s)" not in t and "(book)" not in t and "risk factor" not in t for t in titles), titles
    assert any(t.startswith("1 fila roja sobre") for t in titles) and any(t.startswith("18 filas rojas sobre") for t in titles)
    assert any("(cartera)" in t for t in titles) and any("(factor de riesgo)" in t for t in titles)
