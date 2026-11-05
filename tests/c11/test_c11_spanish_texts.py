"""U16-R2 b05 B5 (PR-C11): the committed C11 documents and manifest say in Spanish what the Spanish view prints."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from f3_spanish_text import ROOT, document_leaks, load  # noqa: E402

FOLDER = ROOT / "data" / "derived" / "C11"
DOCUMENTS = sorted(p.name for p in FOLDER.glob("*.json"))


@pytest.mark.parametrize("name", DOCUMENTS)
def test_no_spanish_text_carries_an_english_number_form(name):
    assert document_leaks(load(f"data/derived/C11/{name}")) == []


def test_the_rail_chips_of_the_windows_are_named_in_both_languages_never_by_their_id():
    manifest = load("data/derived/manifests/C11.json")
    chips = {a["variant_id"]: a["short_title"] for a in manifest["artifacts"] if a["role"] == "variant"}
    assert len(chips) == 6
    for variant_id, chip in chips.items():
        assert chip["es"] != variant_id and chip["en"] != variant_id, variant_id
        assert ":" not in chip["es"]
    assert chips["equity-2007-09"] == {"en": "Equity 2007 to 2009", "es": "Renta variable 2007 a 2009"}
    assert chips["rates-2022"]["es"] == "Tasas 2022"
