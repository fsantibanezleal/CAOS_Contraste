"""The CMF aggregates the Banco Andino book of C15 is calibrated to (CT-1505), all read from the CMF publication C07 already fetched.

The publication is "Informe del Desempeno del Sistema Bancario y Cooperativas", August 2026, Cuadro N 1, column Bancos (million USD;
file, URL and SHA-256 in ``cases/c07/sources.py``, read here without changing it, reservation R3 of the U10 sizing). The three loan
portfolios are the C07 targets (the same mix, so the two cases describe one bank); the other four aggregates are the figures of the
same table. The book is scaled so that its three loan portfolios equal the C07 total (``cases/c07/book.py`` PARAMS); every other
aggregate is the same multiple of its CMF figure. The month of the figures (August 2026) is the last one the CMF had published
before the valuation date: the report of September appears at the end of October.
"""
from __future__ import annotations

from typing import Any

from ..c07 import book as c07_book
from ..c07 import sources as c07_src

AS_OF = c07_src.AS_OF
PUBLICATION = "cmf-informe-2026-08"
#: Cuadro N 1, column Bancos, million USD at 929.18 CLP per USD of 2026-08-31 (only the ratios are used)
CMF_MMUSD = {
    "commercial": 163602.0, "consumer": 34491.0, "mortgage": 104610.0, "interbank": 2200.0,
    "total_assets": 464795.0, "deposits": 239166.0, "securities": 64059.0, "equity": 41582.0,
}
WHERE = {
    "interbank": "Cuadro N 1, column Bancos: Adeudado por Bancos 2.200 of Activos totales 464.795 MMUSD",
    "securities": "Cuadro N 1, column Bancos: Instrumentos financieros de deuda 64.059 of Activos totales 464.795 MMUSD",
    "deposits": "Cuadro N 1, column Bancos: Depositos totales 239.166 of Activos totales 464.795 MMUSD",
    "equity": "Cuadro N 1, column Bancos: Patrimonio 41.582 of Activos totales 464.795 MMUSD",
}
LOAN_METRICS = ("loan mix: commercial", "loan mix: consumer", "loan mix: mortgage")
#: relative tolerance of an achieved aggregate against its target
TOLERANCE = 0.01


def total_loans_clp_million() -> float:
    """The three loan portfolios in CLP million: the C07 book's total exposure, so C15 and C07 are one bank."""
    return float(c07_book.PARAMS["total_exposure_clp"]) / 1e6


def scale() -> float:
    """CLP million per million USD of the CMF table."""
    return total_loans_clp_million() / (CMF_MMUSD["commercial"] + CMF_MMUSD["consumer"] + CMF_MMUSD["mortgage"])


def amount(name: str) -> float:
    """An aggregate of the CMF table in CLP million at the book's scale."""
    return CMF_MMUSD[name] * scale()


def targets() -> list[dict[str, Any]]:
    """The calibration targets: ``metric``, ``unit``, ``value``, ``where``, ``as_of`` and the publication they come from."""
    rows = [dict(t, status="CMF primary") for t in c07_src.TARGETS if t["metric"] in LOAN_METRICS]
    total = CMF_MMUSD["total_assets"]
    for key, metric in (("interbank", "loans to banks over total assets"), ("securities", "securities over total assets"),
                        ("deposits", "deposits over total assets"), ("equity", "equity over total assets")):
        rows.append({"metric": metric, "unit": "share of total assets", "value": CMF_MMUSD[key] / total, "publication": PUBLICATION,
                     "where": WHERE[key], "as_of": AS_OF, "group": key, "status": "CMF primary"})
    return rows


def source_text(row: dict[str, Any]) -> str:
    return c07_src.source_text(row)
