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

    def bake(self, seed: int, paths: Any, data_root: Path | None) -> dict[str, Any]:
        from .bake import bake_case

        return bake_case(seed, paths, data_root)


CASE = C18()
