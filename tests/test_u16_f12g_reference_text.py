"""U16-F12g (fix round 5, the R4 capture review, ruling 1): the reference texts name no plan, unit or contract id.

"U9 research addendum R4" reads "research addendum R4" (c15 B2, c16 B1), and "contract engine-ml-api 2.0.0" names the engine's
documented interface in words (c03 Q, c24 Q1), in both languages. A third-party program and its function (SciPy
chi2_contingency, SciPy ks_2samp, probatus sample_similarity, QuantLib discountBondOption) is a citation and stays (ruling 2).
Every reference the engine writes for C02 and C20 has its bilingual text, so their bakes can carry ``extras.reference_text``.
Tested on the producer's function; the committed documents are re-baked by the integrator.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from pipeline.cases.reference_text import REFERENCE_ES, reference_text

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
RAW = re.compile(r"\bU\d+\b|engine-ml-api|\bcontra(?:ct|to) engine")


def refs(case: str) -> set[str]:
    out: set[str] = set()
    for p in sorted((DERIVED / case).glob("*.json")):
        out |= {t["reference"] for t in json.loads(p.read_text(encoding="utf-8")).get("tests") or []}
    return out


def test_no_reference_text_prints_a_plan_unit_or_a_contract_id():
    for ref in REFERENCE_ES:
        t = reference_text(ref)
        for lang in ("en", "es"):
            assert not RAW.search(t[lang]), (lang, t[lang])


def test_the_u9_addendum_reads_research_addendum_r4():
    ref = "U9 research addendum R4: the theta fit reprices today's curve, so discounted bond prices are martingales (QuantLib 1.44 hullwhite.hpp)"
    t = reference_text(ref)
    assert t["en"].startswith("research addendum R4: the theta fit reprices today's curve")
    assert t["es"].startswith("adenda de investigación R4: el ajuste de theta")
    both = [r for r in REFERENCE_ES if "U9" in r]
    assert len(both) == 2
    assert "the research addendum R4: the Hull-White one-factor closed forms" in reference_text(both[1] if "C.4" in both[1] else both[0])["en"]


def test_the_engine_contract_is_named_in_words():
    ref = next(r for r in REFERENCE_ES if "C.7 l.1016-1018, I.1 l.1187" in r)
    t = reference_text(ref)
    assert "the engine's documented ML validation interface, version 2.0.0 (C.7 l.1016-1018, I.1 l.1187)" in t["en"]
    assert "la interfaz documentada de validación de ML del motor, versión 2.0.0 (C.7 l.1016-1018, I.1 l.1187)" in t["es"]


def test_a_program_and_its_function_stay_as_a_citation():
    for ref, token in (("Two-sample Kolmogorov-Smirnov test (SciPy ks_2samp)", "SciPy ks_2samp"),
                       ("Pearson chi-square test of homogeneity on a 2 x B contingency table (SciPy chi2_contingency)", "SciPy chi2_contingency"),
                       ("QuantLib 1.44 hullwhite.cpp discountBondOption (addendum R4); relative difference gate 1e-6", "discountBondOption")):
        t = reference_text(ref)
        assert token in t["en"] and token in t["es"], (ref, t)


@pytest.mark.parametrize("case", ["C02", "C20"])
def test_every_reference_of_c02_and_c20_has_its_bilingual_text(case):
    found = refs(case)
    assert found
    missing = sorted(r for r in found if r not in REFERENCE_ES)
    assert missing == []
    for r in found:
        t = reference_text(r)
        assert t["en"] and t["es"] and not RAW.search(t["en"] + t["es"])


def test_the_c20_remarks_are_translated_and_the_citations_kept():
    t = reference_text("Two-sample Kolmogorov-Smirnov test (SciPy ks_2samp)")
    assert t["es"] == "prueba de Kolmogorov-Smirnov de dos muestras (SciPy ks_2samp)"
    sr = next(r for r in REFERENCE_ES if "SR 11-7" in r)
    es = reference_text(sr)["es"]
    assert "análisis de sensibilidad" in es and "SR 26-2" in es and "superseded" not in es


def test_c10_m12_the_add_on_reads_ajuste_in_spanish():
    """R4 c10 m12 (C08): the view says "Ajuste" everywhere; the reference said "el add-on es el propio de Contraste"."""
    ref = next(r for r in REFERENCE_ES if r.startswith("EBA/GL/2019/03 and EBA/RTS/2018/04"))
    es = reference_text(ref)["es"]
    assert "add-on" not in es
    assert "el ajuste es el propio de Contraste, basado en cohortes (dossier 04 F.4)" in es
