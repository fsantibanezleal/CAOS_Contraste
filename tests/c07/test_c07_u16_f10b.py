"""U16-F10b (fix round 4, the R3 capture review of C07, batch c08): the producer's texts a Spanish view prints are Spanish, tested on
the producer's functions and on the test-size bake in memory (the committed documents are re-baked by the integrator, never here).

- B1: the calibration targets' source and the bank's calibration source are bilingual texts; the Spanish quotes the CMF report with
  its accents and carries no English word ("published", "column", "section", "includes loans to banks").
- The raw-id scan row (m9): no engine module name in a reader text ("read through riskvalidation.provisions.local_cl").
- m6: the Spanish says PCE, as the interface does, never ECL.
- m7: a Spanish percent is joined to its number by the no-break space.
- m10: a numeral of a CMF chapter is written "N°", never a bare "N".
- "Shock" is translated ("Choque", the ruling of 2026-10-27).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "contracts"))

import contract_schemas as cs  # noqa: E402
from pipeline.cases.c07 import documents, sources  # noqa: E402

NBSP = " "
ENGLISH_IN_ES = re.compile(r"\bpublished\b|\bcolumn\b|\bsection \d|includes loans|\bof Comercial\b|Desempeno|dias o mas|\bindice\b|\bcreditos\b|participacion")
PLAIN_PERCENT = re.compile(r"\d \%")
BARE_N = re.compile(r"\bN \d")


def _bitext(x: object) -> bool:
    return isinstance(x, dict) and set(x) == {"en", "es"} and all(isinstance(v, str) and v for v in x.values())


def _texts(doc: object):
    """Every bilingual text of a document, as (path, text)."""
    stack = [("$", doc)]
    while stack:
        path, x = stack.pop()
        if _bitext(x):
            yield path, x
        elif isinstance(x, dict):
            stack.extend((f"{path}/{k}", v) for k, v in x.items())
        elif isinstance(x, list):
            stack.extend((f"{path}/{i}", v) for i, v in enumerate(x))


def test_b1_a_target_source_is_bilingual_and_the_spanish_is_spanish() -> None:
    for t in sources.TARGETS:
        s = sources.source_text(t)
        assert _bitext(s), t["metric"]
        assert not ENGLISH_IN_ES.search(s["es"]), s["es"]
        assert "Informe del Desempeño del Sistema Bancario y Cooperativas" in s["es"] and "Desempeño" in s["en"]
        for text in s.values():
            assert sources.PUBLICATIONS[t["publication"]]["url"] in text
            assert not PLAIN_PERCENT.search(text) and not BARE_N.search(text), text
    by = {t["metric"]: sources.source_text(t) for t in sources.TARGETS}
    assert "publicado el 2026-09-29" in by["loan mix: commercial"]["es"] and "Cuadro N° 1, columna Bancos" in by["loan mix: commercial"]["es"]
    assert "(incluye créditos a bancos)" in by["provision index: total"]["es"]
    assert "morosidad de 90 días o más" in by["90-day delinquency: total"]["es"]
    assert "créditos en cuotas, producto con la mayor participación en consumo" in by["consumer product split: instalment loans"]["es"]
    assert "published 2026-09-29" in by["loan mix: commercial"]["en"]           # the English wording is kept


def test_b1_the_bank_calibration_source_is_bilingual() -> None:
    s = documents.calibration_source()
    assert _bitext(s)
    assert "publicación web pública (falta la clave de la API de CMF Bancos)" in s["es"] and "generador " in s["es"] and "parámetros sha256 " in s["es"]
    assert "public web publication" in s["en"] and "Desempeño" in s["en"] and "Desempeño" in s["es"]
    assert not ENGLISH_IN_ES.search(s["es"]) and "public web" not in s["es"]


def test_the_raw_id_scan_row_no_engine_module_in_a_b1_table_source() -> None:
    for table in documents.b1_tables():
        for text in table["source"].values():
            assert "riskvalidation" not in text and "local_cl" not in text, text
        assert "sección" in table["source"]["es"]


def test_m6_m7_m10_and_shock_on_the_test_size_bake(built) -> None:
    docs = {**built["variants"], "models": built["models"]}
    for name, doc in docs.items():
        for path, t in _texts(doc):
            es = t["es"]
            assert not re.search(r"\bECL\b", es), (name, path, es)
            assert not PLAIN_PERCENT.search(es), (name, path, es)
            assert not BARE_N.search(es) and not BARE_N.search(t["en"]), (name, path, t)
            assert not re.search(r"\b[Ss]hock\b", es), (name, path, es)
            for text in t.values():
                assert "riskvalidation.provisions" not in text, (name, path, text)


def test_the_test_size_models_document_validates_against_the_bumped_schema(built) -> None:
    """The produced side of c07-models 3.0.0: the bilingual sources validate, and the committed string form still does."""
    fit = built["models"]
    assert cs.errors("c07/models", fit) == []
    assert all(_bitext(t["source"]) for t in fit["fit"]["calibration_targets"])
    assert _bitext(fit["fit"]["bank"]["calibration_source"])
    committed = cs.load_json(cs.DERIVED / "C07" / "models-banco-andino.json")
    assert cs.errors("c07/models", committed) == []
    committed["fit"]["calibration_targets"][0]["source"] = {"en": "only English"}
    assert cs.errors("c07/models", committed) != []
