"""U16-R2 b04 B4, B5 (PR-C07-2, PR-C08): the committed C08 documents say in Spanish what the Spanish view prints."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from f3_spanish_text import bitexts, document_leaks, load, ROOT  # noqa: E402

VARIANTS = sorted(p.name for p in (ROOT / "data" / "derived" / "C08").glob("dc-*.json"))
MODELS = sorted(p.name for p in (ROOT / "data" / "derived" / "C08").glob("models-dc-*.json"))


def _is_bitext(x) -> bool:
    return isinstance(x, dict) and set(x) == {"en", "es"} and all(isinstance(v, str) and v for v in x.values())


@pytest.mark.parametrize("name", VARIANTS)
def test_the_finding_titles_and_texts_carry_no_english_number_form_in_spanish(name):
    doc = load(f"data/derived/C08/{name}")
    assert document_leaks(doc) == []
    assert len(list(bitexts(doc["findings"]))) >= 1


@pytest.mark.parametrize("name", VARIANTS)
def test_the_strings_a_spanish_view_prints_are_bilingual(name):
    o = load(f"data/derived/C08/{name}")["outputs"]
    assert _is_bitext(o["data_status"]["freddie_mac_reason"]) and "cuenta" in o["data_status"]["freddie_mac_reason"]["es"]
    assert _is_bitext(o["workout"]["incomplete_workouts"]["reason"])
    assert _is_bitext(o["downturn"]["period"]["indicator"]) and _is_bitext(o["downturn"]["period"]["macro_source"])
    assert o["downturn"]["period"]["indicator"]["es"].startswith("tasa anual de castigos")


@pytest.mark.parametrize("name", MODELS)
def test_the_models_documents_carry_the_same_bilingual_strings(name):
    fit = load(f"data/derived/C08/{name}")["fit"]
    assert _is_bitext(fit["data_status"]["freddie_mac_reason"])
    assert _is_bitext(fit["workout"]["incomplete_workouts"]["reason"])
    assert _is_bitext(fit["downturn"]["period"]["indicator"]) and _is_bitext(fit["downturn"]["period"]["macro_source"])


def test_a_calibration_finding_title_writes_its_points_in_the_language():
    from pipeline.cases.c08 import variant
    from pipeline.cases.c08.downturn import DownturnPlan  # noqa: F401  (the plan is not read when the cohort is covered)

    class Down:
        rows: list = []

    cal = {"light": "red", "metric": -0.1234}
    f = variant._findings(cal, "L2-fractional-logit", "all", Down())[0]
    assert "12.3 points" in f["title"]["en"] and "12,3 puntos" in f["title"]["es"]
