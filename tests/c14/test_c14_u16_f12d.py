"""U16-F12d (fix round 5, R4 c17): the C14 producer texts say what the dynamic NII leaves out (n7: "Non-interest items are left
out" sat above a table that holds the non-interest deposits) and the Spanish case question says "prueba", as the product does
everywhere else (n8)."""
from __future__ import annotations

from pipeline.cases.c14 import C14, variant


def test_n7_the_dynamic_nii_assumption_names_what_it_leaves_out() -> None:
    d = variant.DYNAMIC_ASSUMPTION
    assert "Non-interest items are left out" not in d["en"]
    assert d["en"] == ("Constant balance sheet: maturing and repricing flows are replaced by identical new ones. Items not sensitive to "
                       "rates (other assets, other liabilities) are left out; non-interest deposits stay at a zero rate.")
    assert d["es"] == ("Balance constante: los flujos que vencen o reprecian se reemplazan por otros idénticos. Las partidas no sensibles "
                       "a tasas (otros activos, otros pasivos) se omiten; los depósitos sin interés quedan a tasa cero.")


def test_n8_the_spanish_question_says_prueba() -> None:
    q = C14.question["es"]
    assert " test " not in q
    assert q.startswith("¿Habría señalado la prueba de valores atípicos del EVE estandarizado")
