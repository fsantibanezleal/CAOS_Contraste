"""U16-F10d (fix round 4, R3 c16): the C15 producer texts a Spanish reader sees are bilingual at the source: the reference of the
prioritised-bank tests (B2: "RAN 21-13 Annex 1" in the Spanish Thresholds view) and the two formulas, written with symbols and a
legend instead of the document keys ``pn_ur`` and ``surprise_pp`` (the ruling of 2026-10-27; m14: one case for PN_UR)."""
from __future__ import annotations

import re

from pipeline.cases.c15 import variant

KEYS = re.compile(r"\b(pn_ur|surprise_pp|loss-positive)\b")


def test_b2_the_thresholds_reference_is_bilingual() -> None:
    ref = variant.THRESHOLDS_REFERENCE
    assert ref == {"en": "RAN 21-13 Annex 1 (banco priorizado, dossier 03 F.2)", "es": "RAN 21-13 Anexo 1 (banco priorizado, dossier 03 F.2)"}
    assert "Annex" not in ref["es"]


def test_q_the_formulas_write_symbols_with_a_legend_in_both_languages() -> None:
    for f in (variant.CHARGE_FORMULA, variant.CPI_FORMULA):
        assert set(f) == {"en", "es"}
        for lang in ("en", "es"):
            assert not KEYS.search(f[lang]), (lang, f[lang])
            assert "PN_UR" in f[lang]
    assert variant.CHARGE_FORMULA["en"] == "charge = 0.025 × |PN_UR|, where PN_UR is the net UF position times the UF value"
    assert variant.CHARGE_FORMULA["es"] == "cargo = 0,025 × |PN_UR|, donde PN_UR es la posición neta en UF por el valor de la UF"
    assert variant.CPI_FORMULA["en"] == ("effect = −PN_UR × s / 100, positive is a loss, where PN_UR is the net UF position in CLP and s the "
                                         "CPI surprise in percentage points")
    assert variant.CPI_FORMULA["es"] == ("efecto = −PN_UR × s / 100, positivo es una pérdida, donde PN_UR es la posición neta en UF en CLP y s "
                                         "la sorpresa de IPC en puntos porcentuales")
