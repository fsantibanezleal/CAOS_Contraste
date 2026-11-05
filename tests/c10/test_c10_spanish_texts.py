"""U16-R2 b05 M4 (PR-C10): the committed C10 documents say in Spanish what the Spanish view prints, with the Spanish number form."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from f3_spanish_text import ROOT, document_leaks, load  # noqa: E402

FOLDER = ROOT / "data" / "derived" / "C10"
VARIANTS = sorted(p.name for p in FOLDER.glob("*.json") if not p.name.startswith("models-"))


@pytest.mark.parametrize("name", VARIANTS)
def test_no_spanish_text_carries_an_english_number_form(name):
    assert document_leaks(load(f"data/derived/C10/{name}")) == []


def test_the_findings_titles_group_thousands_and_mark_decimals_the_spanish_way():
    doc = load("data/derived/C10/commercial-industrial.json")
    titles = {f["id"]: f["title"] for f in doc["findings"]}
    assert "1.120 nombres" in titles["f-c10-granularity"]["es"] and "1,120 names" in titles["f-c10-granularity"]["en"]
    assert "0,064" in titles["f-c10-correlation"]["es"] and "0.064" in titles["f-c10-correlation"]["en"]
    assert "veces" in titles["f-c10-tail-dependence"]["es"] and "4,12" in titles["f-c10-tail-dependence"]["es"]


def test_the_data_notice_writes_the_size_of_the_file_with_the_spanish_grouping():
    notice = load("data/derived/C10/commercial-industrial.json")["outputs"]["data_status"]["notice"]
    assert "131.057 bytes" in notice["es"] and "131,057 bytes" in notice["en"]


def test_the_short_titles_of_the_rungs_are_spanish_where_the_english_is_not():
    models = load("data/derived/C10/commercial-industrial.json")["model"]
    short = {m["id"]: m["short_title"] for m in models}
    assert short["m-gaussian-1f"] == {"en": "Gaussian 1F", "es": "Gaussiana 1F"}
    assert short["m-student-t"]["es"] == "t de Student"
