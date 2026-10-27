"""U16-F10b (fix round 4, the R3 capture review of C03, batch c04 minors), on the producer's functions: a model has one name in the
findings and the views (m7), the recession is written as years, not a date (m12), the Spanish title reads "hasta 2008" (m6) and the
TabPFN reason names no repository path (m9). The committed documents are re-baked by the integrator."""
from __future__ import annotations

from types import SimpleNamespace

from pipeline.cases.c03 import _case, fit, variant


def _cohort() -> SimpleNamespace:
    return SimpleNamespace(name="FY2008-10", first_fy=2008, last_fy=2010)


def _titles(tests: list[dict], crisis: int = 0) -> dict[str, dict[str, str]]:
    wf = SimpleNamespace(rungs={"P1-scorecard": object(), "P4-lightgbm": object()})
    return {f["id"]: f["title"] for f in variant._findings(tests, wf, _cohort(), crisis, "P1-scorecard")}


def _red(test_id: str, rung: str) -> dict:
    return {"model_id": rung, "test_id": test_id, "light": "red", "segment": "portfolio"}


def test_m7_a_finding_names_the_rung_as_the_views_do() -> None:
    by = _titles([_red("pd.jeffreys", "P1-scorecard"), _red("pd.jeffreys", "P4-lightgbm")])
    sc, gbm = by["F-CL-P1-scorecard"], by["F-CL-P4-lightgbm"]
    assert sc["en"].startswith("WoE scorecard:") and sc["es"].startswith("Tarjeta de puntuación WoE:")
    assert gbm["en"].startswith("Monotone gradient boosting:") and gbm["es"].startswith("Potenciación del gradiente monótona:")
    for t in (sc, gbm):
        assert "P1 Scorecard" not in t["en"] and "P4 LightGBM" not in t["en"]


def test_m12_the_recession_is_written_as_years() -> None:
    t = _titles([])["F-CRISIS"]
    assert "2007 to 2009 recession" in t["en"] and "2007-09" not in t["en"]
    assert "recesión de 2007 a 2009" in t["es"] and "2007-09" not in t["es"]


def test_m6_the_spanish_title_reads_until_2008() -> None:
    assert _case.C03.title == {"en": "SME PD by vintage through 2008", "es": "PD de pymes por cosecha hasta 2008"}


def test_m9_the_tabpfn_reason_names_no_repository_path() -> None:
    assert "requirements-tabpfn.txt" not in fit.TABPFN_REASON and "data-pipeline/" not in fit.TABPFN_REASON
    assert fit.TABPFN_REASON.startswith("TabPFN is an optional extra of the bake environment")
