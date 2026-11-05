"""U16-F12p (the fourth capture review, R4 c30 B2 and B3): the Spanish texts the regulatory bake writes into the calculators
document, which the Methodology calculators print on the Spanish page. No English technical word (ruling 6 of 2026-10-27: swap,
swaption, forward, commodities, bucket, spread), no English subscript of a symbol (K_reduced, K_full, K_hedged), no spelled
Greek letter or ASCII root, and every decimal in the Spanish form. Read from the document the bake builds, never from a re-bake."""
from __future__ import annotations

import re

import pytest

ENGLISH = re.compile(r"(?<![\w-])(swaps?|swaptions?|forwards?|commodit(?:y|ies)|buckets?|spreads?|spot|sum|rho|beta|sqrt)(?![\w-])", re.I)
SUBSCRIPT = re.compile(r"[A-Za-z]_(reduced|full|hedged|nominated|only)\b")
# a decimal in the English form: "0.75", "11.661904"; a paragraph reference ("MAR21.4", "CRE52.72") is not one
DECIMAL = re.compile(r"(?<![A-Za-z\d.])\d+\.\d+")


def _spanish(doc: dict) -> list[tuple[str, str]]:
    out = []
    for k in ("official_examples", "invariant_cases"):
        for e in doc[k]:
            for f in ("title", "statement"):
                if e.get(f):
                    out.append((f"{k}/{e['id']}/{f}", e[f]["es"]))
    for t in doc["parameter_tables"]:
        out.append((f"parameter_tables/{t['id']}/title", t["title"]["es"]))
    return out


@pytest.mark.parametrize("check", ["english", "subscript", "decimal"])
def test_the_spanish_texts_of_the_built_document_are_spanish(built, check) -> None:
    texts = _spanish(built)
    assert len(texts) >= 15
    rx = {"english": ENGLISH, "subscript": SUBSCRIPT, "decimal": DECIMAL}[check]
    bad = [f"{where}: {m.group(0)} in {es!r}" for where, es in texts for m in rx.finditer(es)]
    assert bad == []


def test_the_cre99_sets_name_their_products_in_spanish(built) -> None:
    titles = {e["id"]: e["title"]["es"] for e in built["official_examples"]}
    assert titles["cre99-netting-set-1"] == "CRE99 conjunto 1: permutas de tasa y una opción sobre permuta, sin margen"
    assert titles["cre99-netting-set-3"] == "CRE99 conjunto 3: contratos a plazo y permutas de materias primas"
    assert titles["cre99-netting-set-5"] == "CRE99 conjunto 5: tasas y materias primas con margen"


def test_the_english_texts_keep_their_wording(built) -> None:
    by = {e["id"]: e for e in built["official_examples"] + built["invariant_cases"]}
    assert by["cre99-netting-set-1"]["title"]["en"] == "CRE99 netting set 1: interest rate swaps and a swaption, unmargined"
    assert by["ba-cva-hedges-floor"]["title"]["en"] == "Hedges never take K_full below beta K_reduced"
    assert by["cascade-two-horizons"]["statement"]["en"].startswith("ES = sqrt(ES_T(P)^2")
