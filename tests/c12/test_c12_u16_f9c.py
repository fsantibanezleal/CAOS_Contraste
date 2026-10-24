"""U16-F9c (fix round 3, R2b c13): the C12 texts a reader sees name the SA-CCR block, say in words what was not checked (no
"UNVERIFIED" process marker in the product's own sentences) and name each measure of a finding title in English as in Spanish."""
from __future__ import annotations

import inspect

from pipeline.cases.c12 import models, regulatory, variant


def test_the_measure_note_names_the_sa_ccr_block() -> None:
    """B4: "the replacement cost of the sa_ccr block" printed the JSON key in prose where the name SA-CCR exists."""
    note = variant.MEASURE_NOTE
    assert "sa_ccr" not in note["en"] and "sa_ccr" not in note["es"]
    assert "replacement cost of the SA-CCR block" in note["en"]
    assert "reemplazo del bloque SA-CCR" in note["es"]


def test_the_ba_cva_limit_says_what_was_not_checked_in_words() -> None:
    """m2: "(the paragraph was not re-read: UNVERIFIED)" is a process marker; the limit says it in a sentence."""
    src = inspect.getsource(regulatory)
    assert "UNVERIFIED" not in src.split('"limit"', 1)[1].split("}}", 1)[0]
    assert "UNVERIFICADO" not in src
    assert "the reading of the paragraph has not been checked again" in src


def test_the_licence_basis_says_what_was_not_checked_in_words() -> None:
    src = inspect.getsource(models)
    assert "the Treasury-side sentence is UNVERIFIED" not in src
    assert "NO VERIFICADA" not in src
    assert "no Treasury page states the licence" in src


def _row(test_id: str, light: str, segment: str) -> dict:
    return {"test_id": test_id, "model_id": "hw1f-exposure", "segment": segment, "light": light}


def test_a_finding_title_names_its_measure_and_counts_its_rows_in_english() -> None:
    """The raw-id scan: "1 red row(s) on the EE profile against ORE 1.8.17.0 (minimum-transfer-amount-0)"."""
    out = variant.findings_of([_row("ccr.reconcile_ee_profile", "red", "minimum-transfer-amount-0")])
    title = out[0]["title"]
    assert "minimum-transfer-amount-0" not in title["en"] and "minimum-transfer-amount-0" not in title["es"]
    assert "(minimum transfer amount 0)" in title["en"]
    assert title["en"].startswith("1 red row on ")
    two = variant.findings_of([_row("ccr.reconcile_ee_profile", "red", "book-10bd"), _row("ccr.reconcile_ee_profile", "red", "book-20bd")])
    assert two[0]["title"]["en"].startswith("2 red rows on ")
