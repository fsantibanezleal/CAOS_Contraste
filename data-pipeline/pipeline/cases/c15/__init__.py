"""C15, IRRBB on a CLP and UF balance sheet under RAN 21-13 Annex 1: the synthetic Banco Andino on the Banco Central de Chile curves (U10-P2).

The case package (see ``docs/cases/C15.md`` and ``docs/design/features/c15/``): ``curves`` (the choice of the BCCh F022 series, the valuation date
and the zero curves the engine fits), ``targets`` and ``assumptions`` (the CMF aggregates the book is calibrated to and the named synthetic
assumptions), ``book`` (the Banco Andino banking book and the six variant specifications), ``variant`` (one variant through ``riskvalidation.irrbb``),
``models`` (the models document), ``bake`` (the documents, the checksums and the manifest) and ``page`` (the results block of the case page). The
reader of the raw files and their fetch is the shared ``pipeline.io.bcch``. The heavy modules load when the case bakes, never at discovery.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

CASE_ID = "C15"
SOURCES = ("bcch-bde",)


class C15:
    id = CASE_ID
    slug = "irrbb-clp-uf-annex1"
    title = {"en": "IRRBB on a CLP and UF balance sheet: RAN 21-13 Annex 1",
             "es": "IRRBB sobre un balance en CLP y UF: Anexo 1 de la RAN 21-13"}
    category_id = "balance-sheet"
    kind = "synthetic"
    question = {
        "en": "How much EVE and NII does a synthetic Chilean bank lose under the CMF's prescribed shocks on the Banco Central curves, how much of "
              "it is the indexation of its UF position, and what does the 50 percent offset between the pesos and UF legs change?",
        "es": "¿Cuánto EVE y NII pierde un banco chileno sintético bajo los choques prescritos por la CMF sobre las curvas del Banco Central, "
              "cuánto de eso es la reajustabilidad de su posición en UF, y qué cambia la compensación de 50 por ciento entre pesos y UF?"}
    sources = SOURCES

    def bake(self, seed: int, paths: Any, data_root: Path | None) -> dict[str, Any]:
        from .bake import bake_case

        return bake_case(seed, paths, data_root)


CASE = C15()
