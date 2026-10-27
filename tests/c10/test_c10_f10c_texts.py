"""U16-F10c (R3 batch c11, C10): the producer's finding titles never round a small p-value to 0.000, group a count of effective
names in English as the shell does, write the Greek parameter names as symbols (rho, nu), and the Spanish impact label says
"prueba", not "test" (the 2026-10-27 ruling). Tested on the producer's functions over the committed documents' outputs, never by
re-baking: the numbers are the committed ones."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from f3_spanish_text import load  # noqa: E402

from pipeline.cases.c10 import documents as docs

LOANS = ["commercial-industrial", "commercial-real-estate", "credit-cards", "other-consumer", "residential"]


def _findings(variant: str) -> dict[str, dict[str, str]]:
    doc = load(f"data/derived/C10/{variant}.json")
    out = doc["outputs"]
    by_id = {r["id"]: r for r in out["rungs"]}
    _imp, find = docs.impact_and_findings({"label": out["label"]}, out, by_id, doc["tests"], 0.0)
    return {f["id"]: f["title"] for f in find}


@pytest.mark.parametrize("variant", LOANS)
def test_the_committed_titles_are_rebuilt_from_the_committed_outputs(variant):
    """The producer's titles over the committed outputs: every finding of the document is rebuilt (the test reads real numbers)."""
    committed = {f["id"] for f in load(f"data/derived/C10/{variant}.json")["findings"]}
    assert set(_findings(variant)) == committed


@pytest.mark.parametrize("variant", ["other-consumer", "residential"])
def test_a_small_upper_tail_is_written_below_0_001_never_0_000(variant):
    t = _findings(variant)["f-c10-tail"]
    assert "0.000" not in t["en"] and "0,000" not in t["es"]
    assert "upper binomial tail below 0.001" in t["en"]
    assert "cola binomial superior menor que 0,001" in t["es"]


def test_a_tail_above_0_001_keeps_its_three_decimals():
    t = _findings("credit-cards")["f-c10-tail"]
    assert "upper binomial tail 0.001)" in t["en"] or "upper binomial tail 0.00" in t["en"]


@pytest.mark.parametrize("variant", LOANS)
def test_the_effective_names_are_grouped_in_english_as_in_spanish(variant):
    doc = load(f"data/derived/C10/{variant}.json")
    eff = doc["outputs"]["portfolio"]["effective_names"]
    t = _findings(variant)["f-c10-granularity"]
    from pipeline.core.text import number
    assert f"{number(eff, 0, lang='en')} effective names" in t["en"]
    assert f"{number(eff, 0, lang='es')} nombres efectivos" in t["es"]


def test_the_student_t_degrees_of_freedom_are_written_nu():
    t = _findings("commercial-industrial")["f-c10-tail-dependence"]
    assert "(ν 5)" in t["en"] and "(ν 5)" in t["es"]
    assert "nu 5" not in t["en"] and "nu 5" not in t["es"]


@pytest.mark.parametrize("grid", ["grid-22", "grid-40"])
def test_the_grid_findings_write_rho_as_a_symbol(grid):
    doc = load(f"data/derived/C10/{grid}.json")
    for f in docs.grid_findings(doc):
        for lang in ("en", "es"):
            assert "rho = " not in f["title"][lang], f["title"][lang]
            assert "ρ = " in f["title"][lang]


def test_the_spanish_impact_labels_of_a_grid_say_prueba():
    doc = load("data/derived/C10/grid-22.json")
    g = docs.grid_document(22, [(c, []) for c in doc["outputs"]["cells"]], 400, "x")
    for k in ("size_ml", "size_moments"):
        assert "test" not in g["impact"][k]["label"]["es"]
    assert g["impact"]["size_ml"]["label"]["es"] == "Tamaño de la prueba de máxima verosimilitud"
