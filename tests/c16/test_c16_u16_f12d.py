"""U16-F12d (fix round 5, R4 c19 and c20): the C16 producer texts. The run-off event label no longer makes the run the bank (c20
n5), the compounding tolerance writes one notation in its value and its basis (c20 n6), and the Spanish names the NLP in the
feminine as everywhere else (c19 n11)."""
from __future__ import annotations

from pipeline.cases.c16 import assumptions, variant


def test_c20_n5_the_event_label_puts_the_run_at_the_bank() -> None:
    assert variant.EVENT_LABEL == {
        "en": "The deposit run of 9 and 10 March 2023 at the bank that failed on 2023-03-10",
        "es": "La corrida de depósitos del 9 y 10 de marzo de 2023 en el banco que quebró el 2023-03-10",
    }


def test_c20_n6_the_tolerance_basis_writes_the_value_as_the_value_cell_does() -> None:
    basis = assumptions.conventions()["list_compounding_tolerance"]["basis"]
    for lang in ("en", "es"):
        assert "5e-7" not in basis[lang], lang
        assert "5E-7" in basis[lang], lang


def test_c19_n11_the_spanish_nlp_is_feminine() -> None:
    es = assumptions.conventions()["nlp_identity_tolerance"]["basis"]["es"]
    assert es == "La identidad de la NLP se cumple al redondeo de seis decimales."
