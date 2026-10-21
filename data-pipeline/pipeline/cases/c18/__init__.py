"""C18, ICAAP and IAPE capital aggregation under macro scenarios: the synthetic Banco Andino under the Fed, EBA and NGFS paths (unit U13-P1).

The case package (see ``docs/cases/C18.md`` and ``docs/design/features/c18/``): ``params`` (the windows, the loan-type map and the named parameters),
``fetch`` (the EBA workbook, the NGFS runs through the IIASA API, the BCCh EUR to CLP series and the provenance of every raw file), ``fed``, ``eba``,
``ngfs`` and ``fx`` (the readers), ``anchors`` (Banco Andino from the committed documents of C07, C11, C15 and C17), ``satellites`` (the fits on 1985 to
2019, the projections and the out-of-time back-cast), ``scenarios`` (the paths transposed onto the jump-off), ``marginals`` (credit, market, IRRBB and
operational at one year and 99.9 percent), ``aggregation`` (the band, the Euler allocation, the model risk and the tests of G.5), ``capital`` (the IAPE
capital engine), ``reverse`` (the minimum Mahalanobis distance scenario), ``models`` and ``documents`` (the documents), ``bake`` (the checks, the
checksums and the manifest) and ``page`` (the results block of the case page). The heavy modules load when the case bakes, never at discovery.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

CASE_ID = "C18"
SOURCES = ("fed-stress-tests", "fed-chargeoff", "eba-esrb-stress-2025", "ngfs-phase-v", "bcch-bde")


#: why this case reads what it reads of other cases, keyed by the document or the module its producer names: ``depends_on`` refuses a list that differs
#: from the source (core.manifest.derive_depends_on), so the manifest cannot state what the code does not do
DEPENDS_REASONS: dict[str, dict[str, str]] = {
    "C07/base.json": {"en": "Reads the C07 base variant: the segments of Banco Andino with their accounts and gross exposure.",
        "es": "Lee la variante base de C07: los segmentos de Banco Andino con sus cuentas y su exposición bruta."},
    "C07/models-banco-andino.json": {"en": "Reads the C07 models document: the IFRS 9 fit of each segment (PD through the cycle, LGD and asset correlation).",
        "es": "Lee el documento de modelos de C07: el ajuste IFRS 9 de cada segmento (PD a través del ciclo, LGD y correlación de activos)."},
    "C11/mixed-2023.json": {"en": "Reads the C11 mixed-2023 variant: the VaR and ES of the champion at the 1 percent level, for the market risk marginal.",
        "es": "Lee la variante mixed-2023 de C11: el VaR y el ES del campeón al nivel de 1 por ciento, para el marginal de riesgo de mercado."},
    "C15/models-banco-andino-2026-09.json": {"en": "Reads the C15 models document: the calibration targets of the bank (equity over total assets).",
        "es": "Lee el documento de modelos de C15: los objetivos de calibración del banco (patrimonio sobre activos totales)."},
    "C17/models-generator.json": {"en": "Reads the C17 models document: the generator parameter set of the operational loss variant xi-0-8.",
        "es": "Lee el documento de modelos de C17: el conjunto de parámetros del generador de la variante de pérdida operacional xi-0-8."},
    "C15/long-uf.json": {"en": "Reads the C15 long-uf variant, the default variant of C15: the outputs that hold the Tier 1 threshold and the net interest margin.",
        "es": "Lee la variante long-uf de C15, su variante por defecto: las salidas que contienen el umbral de Tier 1 y el margen neto de intereses."},
    "manifests/C15.json": {"en": "Reads the C15 manifest to check that its default variant is still long-uf, the variant C18 reads; C18 stops if C15 changes it.",
        "es": "Lee el manifiesto de C15 para comprobar que su variante por defecto sigue siendo long-uf, la que lee C18; C18 se detiene si C15 la cambia."},
    "pipeline.cases.c10.fed": {"en": "Reads the Fed charge-off table with the C10 reader (read_table and URL), so the two cases parse the file the same way.",
        "es": "Lee la tabla de castigos de la Fed con el lector de C10 (read_table y URL), de modo que ambos casos interpretan el archivo de la misma manera."},
}


class C18:
    id = CASE_ID
    slug = "icaap-iape-capital-aggregation"
    title = {"en": "ICAAP and IAPE capital aggregation under macro scenarios",
             "es": "Agregación de capital ICAAP e IAPE bajo escenarios macro"}
    category_id = "capital-stress"
    kind = "real"
    question = {
        "en": "Does Banco Andino hold its internal capital target for three years under each scenario once credit, market, IRRBB and operational risk are "
              "aggregated, and how much of the answer rests on the aggregation method?",
        "es": "¿Mantiene Banco Andino su objetivo interno de capital durante tres años bajo cada escenario una vez agregados los riesgos de crédito, mercado, "
              "IRRBB y operacional, y cuánto de la respuesta depende del método de agregación?"}
    sources = SOURCES

    def depends_on(self) -> list[dict[str, Any]]:
        """What this case reads of other cases, as the manifest states it (``depends_on``)."""
        from ...core.manifest import derive_depends_on

        return derive_depends_on(self.id, DEPENDS_REASONS)

    def bake(self, seed: int, paths: Any, data_root: Path | None) -> dict[str, Any]:
        from .bake import bake_case

        return bake_case(seed, paths, data_root)


CASE = C18()
