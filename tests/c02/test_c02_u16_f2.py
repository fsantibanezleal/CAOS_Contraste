"""U16-F2 (the R2 fix round, C02): Spanish text and numbers in the producer's bilingual fields; transfer cells keyed on the model."""
from __future__ import annotations

import re

import numpy as np
from c02_support import VARIANTS, committed

from pipeline.cases.c02 import blocks
from pipeline.cases.c02 import conventions as cv

ENGLISH_DECIMAL = re.compile(r"\b\d+\.\d{3,}\b")


def _bitext(x: object) -> bool:
    return isinstance(x, dict) and set(x) == {"en", "es"} and all(isinstance(v, str) and v for v in x.values())


def test_the_impact_detail_texts_are_bilingual_and_the_spanish_is_spanish() -> None:
    """PR-C02 (b01 B1): unit, pd_basis and reason_if_null were English-only strings printed in the Spanish capture."""
    for hid in VARIANTS:
        d = committed(hid)["outputs"]["impact_detail"]
        assert _bitext(d["unit"]) and _bitext(d["pd_basis"]), hid
        assert d["unit"]["es"] != d["unit"]["en"] and "ECL per unit" not in d["unit"]["es"], hid
        assert d["pd_basis"]["es"] != d["pd_basis"]["en"] and "the five file" not in d["pd_basis"]["es"], hid
        assert d["reason_if_null"] is None or _bitext(d["reason_if_null"]), hid


def test_the_reason_with_no_ecl_writes_its_numbers_as_the_language_does() -> None:
    d = committed("h1")["outputs"]["impact_detail"]
    reason = d["reason_if_null"]
    assert reason is not None
    assert "0.0694" in reason["en"] and "0,0694" in reason["es"] and not ENGLISH_DECIMAL.search(reason["es"])
    assert "strictly increasing" not in reason["es"] and "estrictamente" in reason["es"]


def test_the_term_structure_reason_spanish_has_spanish_numbers_and_no_english_abbreviation() -> None:
    reason = committed("pooled")["outputs"]["term_structure_reason"]
    assert "1y 0.0694" in reason["en"]                                   # the English wording is unchanged
    assert "0,0694" in reason["es"] and not ENGLISH_DECIMAL.search(reason["es"]) and not re.search(r"\b\dy\b", reason["es"])


def test_the_impact_block_function_returns_bilingual_texts() -> None:
    detail, impact = blocks.impact_block(np.array([0.03, 0.04, 0.04, 0.06, 0.08]), cv.t("basis", "base"))
    assert _bitext(detail["unit"]) and _bitext(detail["pd_basis"]) and _bitext(detail["reason_if_null"])
    assert "0,0300" in detail["reason_if_null"]["es"] and "0.0300" in detail["reason_if_null"]["en"]
    assert isinstance(impact["ecl_12m_effect"]["unit"], str)             # the envelope's unit stays a string (the shared schema)


def test_every_transfer_cell_names_its_model_so_the_two_p4_models_never_share_a_code() -> None:
    """V02-1 (b01 M2): rung code P4 names LightGBM and XGBoost; a cell is found by the model id."""
    for hid in VARIANTS[:5]:
        cells = committed(hid)["outputs"]["transfer"]["cells"]
        assert cells and {c["model_id"] for c in cells} == set(cv.TRANSFER_RUNGS), hid
        assert all(cv.RUNG_CODE[c["model_id"]] == c["rung"] for c in cells), hid
