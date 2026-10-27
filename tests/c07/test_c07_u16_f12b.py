"""U16-F12b (fix round 5, the R4 capture review of C07, batch c09 B1): the Spanish bank notice carries no English technical word
("hash" reads "huella", ruling 6 of 2026-10-27), on the producer's function; the English keeps its wording. The committed models
document is re-baked by the integrator."""
from __future__ import annotations

import re

from pipeline.cases.c07 import documents

ENGLISH = re.compile(r"\b(?:hash|port|shell|benchmark|seed)\b", re.IGNORECASE)


def test_b1_the_spanish_bank_notice_says_huella_and_no_english_word() -> None:
    n = documents.bank_notice()
    assert not ENGLISH.search(n["es"]), n["es"]
    assert "parámetros y huella criptográfica en el registro del modelo generador" in n["es"]
    assert n["en"].startswith("Synthetic: Banco Andino is a generated bank, calibrated to public CMF system aggregates (parameters and hash in the generator model record)")
