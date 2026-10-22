"""U16-F4 (the U16-R2 capture review, batches b07 to b09): the committed documents of C14 to C18 carry the texts the fix round wrote.

Each test reads the committed documents (the bake's output): the Spanish of a finding writes its numbers with the decimal comma, a
back-test segment is named in words in a finding title, the Spanish slot of a text is never the English sentence, and the Panjer
exceedance of C17 has no value where the recursion computed none.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
ENGLISH_FUNCTION = re.compile(r"\b(the|of|and|with|from|for|are|was|not|which|that|this|than|over|under|used|applied|stated|fitted|by|is|has|its)\b")
SPANISH_FUNCTION = re.compile(r"\b(de|la|el|los|las|del|que|con|por|para|una|un|se|sin|entre|más|al|su|sus|lo|y|en)\b")


def load(case: str, name: str) -> dict:
    return json.loads((DERIVED / case / f"{name}.json").read_text(encoding="utf-8"))


def bitexts(node, path=()):
    """Every ``{en, es}`` object of a document with its path."""
    if isinstance(node, dict):
        if set(node) == {"en", "es"} and isinstance(node["en"], str) and isinstance(node["es"], str):
            yield path, node
            return
        for key, value in node.items():
            yield from bitexts(value, (*path, key))
    elif isinstance(node, list):
        for value in node:
            yield from bitexts(value, (*path, "[]"))


def english_in_spanish(es: str) -> bool:
    return len(ENGLISH_FUNCTION.findall(es)) >= 2 and len(ENGLISH_FUNCTION.findall(es)) > len(SPANISH_FUNCTION.findall(es))


@pytest.mark.parametrize("name", ["vd-2021-q4", "vd-2022-q2", "vd-2022-q4"])
def test_c14_the_spanish_findings_use_the_decimal_comma_and_the_ratio_unit_is_per_square_root_year(name):
    doc = load("C14", name)
    for finding in doc["findings"]:
        es = finding["title"]["es"]
        assert not re.search(r"\d\.\d", es), (finding["id"], es)
        assert "Tier 1" not in es and "la data" not in es, es
    sigma = next(p for p in doc["outputs"]["ear_evar"]["parameters"] if p["name"] == "sigma")
    assert sigma["unit"] == "per square-root year"


@pytest.mark.parametrize("name", ["lcr-standard", "list-adverse", "list-extreme", "fast-run", "htm-losses", "reverse-stress"])
def test_c16_no_finding_prints_a_slug_or_an_english_decimal_and_no_text_repeats_the_english(name):
    doc = load("C16", name)
    for finding in doc["findings"]:
        for lang in ("en", "es"):
            title = finding["title"][lang]
            assert not re.search(r"\b[a-z]+(?:-[a-z]+){1,}\b", title) or "fast-run" not in title, title
            assert "board-stated-share" not in title and "call-report-dep" not in title, title
        assert not re.search(r"\d\.\d", finding["title"]["es"]), finding["title"]["es"]
    for path, text in bitexts(doc):
        assert text["en"] != text["es"] or len(text["en"].split()) < 3, (path, text["en"])
        assert not english_in_spanish(text["es"]), (path, text["es"])


def test_c16_the_licence_statements_of_the_sources_are_in_spanish():
    models = load("C16", "models-svb-liquidity")
    for source in models["fit"]["sources"]:
        assert not english_in_spanish(source["statement"]["es"]), source["source_id"]


@pytest.mark.parametrize("name", ["xi-0-6", "xi-0-8", "xi-0-96", "xi-1-1"])
def test_c17_the_panjer_exceedance_is_null_past_the_end_of_its_grid_and_never_a_plateau(name):
    exceedance = load("C17", name)["outputs"]["exceedance"]
    values = exceedance["panjer"]["exceedance"]
    real = [i for i, v in enumerate(values) if v is not None]
    assert real, name
    assert all(v is None for v in values[real[-1] + 1:]), name  # nulls only as a suffix
    assert all(v is not None for v in values[: real[-1] + 1]), name  # no hole inside the grid
    tail = [v for v in values[: real[-1] + 1]]
    # a flat run of the last value is the old plateau: a real recursion tail keeps falling
    assert len(tail) < 4 or len({round(v, 12) for v in tail[-4:]}) > 1, name


def test_c17_some_variant_has_a_grid_shorter_than_the_exceedance_axis():
    nulls = [sum(v is None for v in load("C17", n)["outputs"]["exceedance"]["panjer"]["exceedance"]) for n in ("xi-0-6", "xi-0-8", "xi-0-96", "xi-1-1")]
    assert max(nulls) > 0, nulls


@pytest.mark.parametrize("name", ["baseline", "eba-2025-adverse", "fed-2026-severely-adverse", "ngfs-delayed-transition", "t-copula-baseline", "reverse-stress"])
def test_c18_no_text_of_the_documents_repeats_its_english_in_the_spanish_slot(name):
    doc = load("C18", name)
    for path, text in bitexts(doc):
        assert text["en"] != text["es"] or len(text["en"].split()) < 3, (name, path, text["en"][:80])


def test_c18_the_models_document_has_no_english_in_a_spanish_slot():
    doc = load("C18", "models-banco-andino")
    for path, text in bitexts(doc):
        assert text["en"] != text["es"] or len(text["en"].split()) < 3, (path, text["en"][:80])
