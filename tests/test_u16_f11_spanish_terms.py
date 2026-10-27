"""U16-F11 (the ruling of 2026-10-27): the Spanish technical terms of the producers, tested on the producers' text.

The committed documents still hold the old Spanish until the integrator re-bakes them, so these tests read the producer's constant or
source, never a committed document.
"""
from __future__ import annotations

from pathlib import Path

from pipeline import registry
from pipeline.core import readiness
from pipeline.io import contract

PIPE = Path(__file__).resolve().parents[1] / "data-pipeline" / "pipeline"
CATEGORY_ES = "Puntuación crediticia"
OLD_WORDS = ("Scoring de crédito", "momentum de calificación", "Alfa de momentum", "riesgo de momentum", "backtests y ventanas")


def test_the_credit_scoring_category_reads_puntuacion_crediticia_in_the_registry():
    assert registry.CATEGORIES["credit-scoring"] == {"en": "Credit scoring", "es": CATEGORY_ES}


def test_the_credit_scoring_category_reads_the_same_in_the_three_case_producers():
    for rel in ("cases/c01_retail_pd.py", "cases/c02/bake.py", "cases/c03/_case.py"):
        src = (PIPE / rel).read_text(encoding="utf-8")
        assert f'category={{"en": "Credit scoring", "es": "{CATEGORY_ES}"}}' in src, rel


def test_no_producer_keeps_the_old_spanish_wording():
    for path in PIPE.rglob("*.py"):
        src = path.read_text(encoding="utf-8")
        for old in OLD_WORDS:
            assert old not in src, (path.name, old)


def test_the_momentum_rung_reads_impulso_in_the_c04_producers():
    fam = (PIPE / "cases" / "c04_families.py").read_text(encoding="utf-8")
    assert '"Alfa del impulso (beta 1 por año)"' in fam
    tr = (PIPE / "cases" / "c04_transitions.py").read_text(encoding="utf-8")
    assert '_t("Momentum", "Impulso")' in tr and "Impulso de calificación (dos Reis" in tr
    assert '"riesgo instantáneo de impulso"' in tr


def test_the_not_baked_notice_and_the_contract_series_read_in_the_ruled_words():
    assert readiness.T_NOT_BAKED[1] == "La cadena de cálculo no ha generado esta versión."
    assert contract.MARKET_SERIES.used_by["es"] == "VaR y ES, pruebas retrospectivas y ventanas de estrés: una fila por serie y fecha."


def test_the_governance_independence_finding_names_the_cadena_de_calculo():
    src = (PIPE / "governance" / "bake.py").read_text(encoding="utf-8")
    assert '"La cadena de cálculo (desarrollador) y el motor (validador)' in src
