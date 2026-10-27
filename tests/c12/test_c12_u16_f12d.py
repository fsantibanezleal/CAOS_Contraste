"""U16-F12d (fix round 5, R4 c15): the C12 producer texts a Spanish reader sees name the instruments in Spanish (permuta, opción
sobre permuta, diferencial, al contado, a plazo: ruling 6 of 2026-10-27, B1), render FRED's English licence label in Spanish with
the original marked (B3), keep the citation the English BA-CVA limit gives (n1) and write the survival formula in symbols (n2)."""
from __future__ import annotations

import re

from pipeline.cases.c12 import C12, bake, models, regulatory, variant

INSTRUMENT = re.compile(r"\b(swaps?|swaptions?|spreads?|spot|t-forward|forward|wheel)\b", re.IGNORECASE)


def spanish_texts() -> list[str]:
    curve = models.credit_curve_block()
    texts = [C12.title["es"], C12.question["es"], bake.REGIME["es"], variant.MEASURE_NOTE["es"], regulatory.BA_CVA_LIMIT["es"],
             curve["derivation"]["es"], curve["licence_basis"]["es"], *(t["es"] for t in models.LIMITS)]
    for _, es_title, _, es_what in bake.TITLES.values():
        texts += [es_title, es_what]
    return texts


def test_b1_no_spanish_text_names_an_instrument_in_english() -> None:
    """B1: swap(s) 70 times, spread 15, swaption 6, spot 3, "t-forward" in the Spanish C12 captures."""
    found = [t for t in spanish_texts() if INSTRUMENT.search(t)]
    assert found == []
    assert "libro de permutas" in C12.title["es"] and "libro de permutas" in C12.question["es"]
    assert bake.TITLES["single-swap"][1] == "Una sola permuta"
    assert "medida a plazo t" in variant.MEASURE_NOTE["es"]
    assert "la opción sobre permuta" in variant.MEASURE_NOTE["es"]
    # the English texts keep their words
    assert "t-forward measure" in variant.MEASURE_NOTE["en"] and "swaption" in variant.MEASURE_NOTE["en"]
    assert C12.title["en"] == "How large is the counterparty exposure of a swap book, and what CVA does it imply?"


def test_b3_the_licence_label_is_rendered_in_spanish_with_the_original_marked() -> None:
    """B3: "FRED etiqueta la serie HQM como Public Domain: Citation Requested" in the Spanish Context."""
    basis = models.credit_curve_block()["licence_basis"]
    assert basis["es"].startswith("FRED etiqueta la serie HQM como de dominio público con cita solicitada (en el original: "
                                  "«Public Domain: Citation Requested»);")
    assert basis["en"].startswith("FRED tags the HQM series Public Domain: Citation Requested;")


def test_n1_the_spanish_ba_cva_limit_keeps_the_citation() -> None:
    """n1: the English limit cites "the invariants of dossier 01 M.1", the Spanish dropped it."""
    assert "the invariants of dossier 01 M.1" in regulatory.BA_CVA_LIMIT["en"]
    assert "los invariantes del dossier 01 M.1" in regulatory.BA_CVA_LIMIT["es"]


def test_n2_the_survival_formula_is_written_in_symbols() -> None:
    """n2: "survival is exp(-s t / LGD)" in ASCII."""
    d = models.credit_curve_block()["derivation"]
    for lang in ("en", "es"):
        assert "exp(-s t / LGD)" not in d[lang]
        assert "exp(−s·t / LGD)" in d[lang], lang
