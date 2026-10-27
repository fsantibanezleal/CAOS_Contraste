"""U16-F12b (fix round 5, the R4 capture review of C02, batch c03 minors m11, n3 and n5), on the producer's functions and the
committed rows: every test row carries its bilingual reference (the Spanish Reason column printed nothing), the stability finding
says a PSI red by its chi-square p-value is a detectable shift with the PSI it rests on (not that the distribution "moved"), and
the Spanish texts name the firm overlap and the transfer one way. The committed documents are re-baked by the integrator."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from c02_support import ROOT  # noqa: F401  (puts the pipeline and the contract test folders on the path)

import contract_schemas as cs
from pipeline.cases.c02 import bake, conventions, findings

DERIVED = Path(__file__).resolve().parents[2] / "data" / "derived" / "C02"
FILES = ("h1", "h2", "h3", "h4", "h5", "pooled")


def _rows(name: str) -> list[dict]:
    rows = json.loads((DERIVED / f"{name}.json").read_text(encoding="utf-8"))["tests"]
    # the rows as the battery writes them, before the bake adds the bilingual reference
    return [{**r, "extras": {k: v for k, v in r["extras"].items() if k != "reference_text"}} for r in rows]


@pytest.mark.parametrize("name", FILES)
def test_m11_every_test_row_of_a_document_carries_its_bilingual_reference(name: str) -> None:
    rows = bake.document_tests(_rows(name))
    assert rows and all(isinstance(r["extras"].get("reference_text"), dict) for r in rows)
    for r in rows:
        ref = r["extras"]["reference_text"]
        assert ref["en"] == r["reference"] and ref["es"], r["test_id"]
    hl = next(r for r in rows if r["test_id"] == "pd.hosmer_lemeshow")["extras"]["reference_text"]["es"]
    assert hl.startswith("Hosmer and Lemeshow (1980)")


def _psi(model: str, light: str, psi: float) -> dict:
    return {"test_id": "stability.psi", "model_id": model, "segment": "portfolio", "light": light, "statistic": psi, "metric": psi,
            "p_value": 0.001, "extras": {}}


def test_n5_the_stability_title_says_a_detectable_shift_with_its_psi_and_its_size() -> None:
    out = {f["id"]: f for f in findings.build([_psi("pooled-P4-lightgbm", "red", 0.0023), _psi("pooled-P4-xgboost", "red", 0.0014)])}
    t = out["F-STABILITY"]["title"]
    assert t["en"] == ("The holdout PD distribution shifts detectably against the training slice for P4 LightGBM, P4 XGBoost (PSI up to "
                       "0.0023, a small change below the 0.10 convention; the light is the chi-square p-value)")
    assert t["es"] == ("La distribución de la PD de la muestra reservada se desplaza de forma detectable respecto del tramo de entrenamiento "
                       "para P4 LightGBM, P4 XGBoost (PSI de hasta 0,0023, un cambio pequeño bajo la convención de 0,10; la luz es el "
                       "valor p de chi-cuadrado)")
    assert "moved" not in t["en"] and "se movió" not in t["es"]


def test_n5_a_psi_at_or_above_the_convention_is_not_called_small() -> None:
    t = {f["id"]: f for f in findings.build([_psi("h1-P2a-l1", "red", 0.1234)])}["F-STABILITY"]["title"]
    assert "(PSI up to 0.1234; the light is the chi-square p-value)" in t["en"]
    assert "(PSI de hasta 0,1234; la luz es el valor p de chi-cuadrado)" in t["es"]


def test_n3_the_spanish_names_the_firm_overlap_and_the_transfer_one_way() -> None:
    texts = [conventions.TRANSFER_REASON["es"], conventions.TERM_STRUCTURE_REASON["es"], *(es for *_, es in findings.LIMITS)]
    joined = " ".join(texts)
    assert "traslape" not in joined and "traslado" not in joined
    assert "solapamiento de empresas" in joined and "AUC de transferencia" in joined


def test_n3_the_pooled_variant_is_named_in_the_gender_of_the_file() -> None:
    assert conventions.POOLED_TITLE == {"en": "Pooled: the five files stacked", "es": "Agrupado: los cinco archivos apilados"}
    assert conventions.POOLED_SHORT == {"en": "Pooled", "es": "Agrupado"}


def test_contract_the_planted_bake_writes_a_bilingual_reference_on_every_row_and_validates(built) -> None:
    """The produced side of c02-outputs 4.0.0: every test row of the planted bake's documents carries ``extras.reference_text``."""
    for vid, doc in built.variants.items():
        assert cs.errors("c02/variant-horizon", doc) == [], vid
        for r in doc["tests"]:
            ref = r["extras"]["reference_text"]
            assert set(ref) == {"en", "es"} and ref["en"] == r["reference"], (vid, r["test_id"])


def test_contract_the_schema_types_the_reference_text_and_keeps_the_committed_rows_valid() -> None:
    doc = cs.load_json(cs.DERIVED / "C02" / "h1.json")
    assert cs.errors("c02/variant-horizon", doc) == []          # a document baked before carries no reference_text
    doc["tests"][0]["extras"]["reference_text"] = "Hosmer and Lemeshow (1980)"
    assert cs.errors("c02/variant-horizon", doc) != []          # a string is not a bilingual text
    doc["tests"][0]["extras"]["reference_text"] = {"en": "x", "es": "y"}
    assert cs.errors("c02/variant-horizon", doc) == []
