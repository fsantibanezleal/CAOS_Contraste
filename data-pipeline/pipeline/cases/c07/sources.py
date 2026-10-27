"""The calibration targets of C07 and the publications they come from (CT-701).

Every figure is read from a CMF primary publication fetched on 2026-10-12 into the device data root
(``raw/cmf-public/``, never the repository); each target carries its value, unit, URL, publication, month and the SHA-256
of the file it was read from. The CMF Bancos API key is an owner prerequisite still missing (owner-prerequisites item 5),
so the figures come from the CMF public web publication "Informe del Desempeño del Sistema Bancario y Cooperativas"
(reuse clause: "autoriza la reproduccion total o parcial de la informacion contenida en este Website, siempre y cuando se
mencione la fuente", dossier 08 A.8). A target not found on a primary source would be recorded UNVERIFIED; the one such
input of this case (the split of the commercial book between group and individual assessment) is an assumption of the
case, not a target.
"""
from __future__ import annotations

from typing import Any

AS_OF = "2026-08-31"
CURRENCY = "CLP"
UF_VALUE = 40873.77        # CLP per UF at 2026-08-31, SII "UF 2026" table (primary)
UF_DATE = "2026-08-31"

#: the fetched publications: the device-data-root file name, URL, size, SHA-256 and the fetch date
PUBLICATIONS: dict[str, dict[str, Any]] = {
    "cmf-informe-2026-08": {
        "file": "cmf-informe-desempeno-2026-08.pdf",
        "url": "https://www.cmfchile.cl/portal/estadisticas/617/articles-113863_recurso_1.pdf",
        "title": "CMF, Informe del Desempeño del Sistema Bancario y Cooperativas, agosto 2026 (published 2026-09-29)",
        "title_es": "CMF, Informe del Desempeño del Sistema Bancario y Cooperativas, agosto 2026 (publicado el 2026-09-29)",
        "month": "2026-08",
        "bytes": 309015,
        "sha256": "5116240cb2ed92d37048defe70ab4c5dd6b6680ef0ecb2b6b2c7912fed71329e",
        "fetched": "2026-10-12",
    },
    "cmf-informe-listing": {
        "file": "listing-informe-desempeno.html",
        "url": "https://www.cmfchile.cl/portal/estadisticas/617/w3-propertyvalue-30207.html",
        "title": "CMF, Informe del Desempeño del Sistema Bancario y Cooperativas, listing of monthly reports",
        "title_es": "CMF, Informe del Desempeño del Sistema Bancario y Cooperativas, listado de los informes mensuales",
        "month": "2026-10",
        "bytes": 395471,
        "sha256": "f32465799f71f6db05f4ed9a513d6de97e249f6c4275b98435a1b68f487fc7f5",
        "fetched": "2026-10-12",
    },
    "sii-uf-2026": {
        "file": "sii-uf2026.htm",
        "url": "https://www.sii.cl/valores_y_fechas/uf/uf2026.htm",
        "title": "Servicio de Impuestos Internos, Valor de la UF 2026",
        "month": "2026-08",
        "bytes": 52262,
        "sha256": "2b0fe76200db4c39c573d5ddc793f264f39c4085fb7d631b62096b53abef1ccd",
        "fetched": "2026-10-12",
    },
}

_P = "cmf-informe-2026-08"


def _w(en: str, es: str) -> dict[str, str]:
    """A locator in the report, in both languages."""
    return {"en": en, "es": es}


def _s(section: str, quote: str, note_en: str = "", note_es: str = "") -> dict[str, str]:
    """A locator of a section of the report: the report's own Spanish words quoted in both languages, with a note of Contraste."""
    return _w(f"section {section}: {quote}{note_en}", f"sección {section}: {quote}{note_es}")


def _t(metric: str, unit: str, value: float, where: dict[str, str], group: str | None = None) -> dict[str, Any]:
    return {"metric": metric, "unit": unit, "value": value, "publication": _P, "where": where, "as_of": AS_OF,
            "group": group, "status": "CMF primary"}


#: the calibration targets (system level, banks, amortised-cost loans, 2026-08-31); each locator in both languages, the report's
#: Spanish quoted with its accents (U16-R3 c08 B1)
TARGETS: tuple[dict[str, Any], ...] = (
    # Cuadro N° 1 (MMUSD, Bancos column): commercial 163,602; consumer 34,491; mortgage 104,610
    _t("loan mix: commercial", "share of the three portfolios", 163602 / (163602 + 34491 + 104610),
       _w("Cuadro N° 1, column Bancos: Comercial 163.602 of Comercial + Consumo + Vivienda 302.703 MMUSD",
          "Cuadro N° 1, columna Bancos: Comercial 163.602 de Comercial + Consumo + Vivienda 302.703 MMUSD"), "commercial"),
    _t("loan mix: consumer", "share of the three portfolios", 34491 / (163602 + 34491 + 104610),
       _w("Cuadro N° 1, column Bancos: Consumo 34.491 MMUSD", "Cuadro N° 1, columna Bancos: Consumo 34.491 MMUSD"), "consumer"),
    _t("loan mix: mortgage", "share of the three portfolios", 104610 / (163602 + 34491 + 104610),
       _w("Cuadro N° 1, column Bancos: Vivienda 104.610 MMUSD", "Cuadro N° 1, columna Bancos: Vivienda 104.610 MMUSD"), "mortgage"),
    # section 2.2 (Sistema Bancario)
    _t("provision index: commercial", "share of loans", 0.0256, _s("2.2", "indicador de provisiones comercial 2,56 %"), "commercial"),
    _t("provision index: consumer", "share of loans", 0.0821, _s("2.2", "indicador de provisiones consumo 8,21 %"), "consumer"),
    _t("provision index: mortgage", "share of loans", 0.0062, _s("2.2", "índice de provisiones vivienda 0,62 %"), "mortgage"),
    _t("provision index: total", "share of loans", 0.0251,
       _s("2.2", "indicador de provisiones del Sistema Bancario 2,51 %", " (includes loans to banks)", " (incluye créditos a bancos)"), "total"),
    _t("90-day delinquency: commercial", "share of loans", 0.0217, _s("2.2", "morosidad de 90 días o más comercial 2,17 %"), "commercial"),
    _t("90-day delinquency: consumer", "share of loans", 0.0257, _s("2.2", "morosidad de 90 días o más consumo 2,57 %"), "consumer"),
    _t("90-day delinquency: mortgage", "share of loans", 0.0257, _s("2.2", "morosidad de 90 días o más vivienda 2,57 %"), "mortgage"),
    _t("90-day delinquency: total", "share of loans", 0.0234,
       _s("2.2", "morosidad de 90 días o más del Sistema Bancario 2,34 %"), "total"),
    _t("consumer product split: instalment loans", "share of consumer loans", 0.5338,
       _s("2.1", "créditos en cuotas, producto con la mayor participación en consumo (53,38 %)"), "consumer"),
)

#: relative tolerance of an achieved aggregate against its target (tested at the test size and at the bake size)
TOLERANCE = 0.01
#: tolerance of the derived totals (the system total includes loans to banks, which the book does not hold)
TOLERANCE_TOTAL = 0.02


class TargetError(ValueError):
    """A calibration target without its source."""


def validate_targets(targets: tuple[dict[str, Any], ...] = TARGETS) -> None:
    """Refuse a target without a value, a unit, a publication, a locator in it or a month (CT-701)."""
    for t in targets:
        for key in ("metric", "unit", "publication", "where", "as_of"):
            if not t.get(key):
                raise TargetError(f"calibration target {t.get('metric')!r} lacks {key}")
        if t.get("status") not in ("CMF primary", "UNVERIFIED"):
            raise TargetError(f"calibration target {t['metric']!r} has no status")
        if not isinstance(t.get("value"), (int, float)) or not 0.0 < t["value"] < 1.0:
            raise TargetError(f"calibration target {t['metric']!r} has no value in (0, 1)")
        pub = PUBLICATIONS.get(t["publication"])
        if pub is None or not pub["url"].startswith("https://") or len(pub["sha256"]) != 64:
            raise TargetError(f"calibration target {t['metric']!r} names no fetched publication")


def source_text(t: dict[str, Any]) -> dict[str, str]:
    """The source of a target in the models document, a bilingual text (U16-R3 c08 B1): publication, locator, URL, file hash."""
    pub = PUBLICATIONS[t["publication"]]
    return {lang: f"{pub.get('title_' + lang, pub['title']) if lang == 'es' else pub['title']}; {t['where'][lang]}; {pub['url']}; sha256 {pub['sha256']}"
            for lang in ("en", "es")}


def target(metric: str) -> float:
    return next(t["value"] for t in TARGETS if t["metric"] == metric)
