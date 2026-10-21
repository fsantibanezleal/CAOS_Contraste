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


#: why this case reads what it reads of other cases, keyed by the document or the module its producer names: ``depends_on`` refuses a list that differs
#: from the source (core.manifest.derive_depends_on), so the manifest cannot state what the code does not do
DEPENDS_REASONS: dict[str, dict[str, str]] = {
    "pipeline.cases.c07.book": {"en": "Reads the C07 book parameters (the total exposure of Banco Andino) that size the C15 loan book.",
        "es": "Lee los parámetros de la cartera de C07 (la exposición total de Banco Andino) que dimensionan la cartera de préstamos de C15."},
    "pipeline.cases.c07.sources": {"en": "Reads the C07 publication, the as-of date and the calibration targets that the C15 book is calibrated to.",
        "es": "Lee la publicación, la fecha de corte y los objetivos de calibración de C07 a los que se calibra la cartera de C15."},
}


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

    def depends_on(self) -> list[dict[str, Any]]:
        """What this case reads of other cases, as the manifest states it (``depends_on``)."""
        from ...core.manifest import derive_depends_on

        return derive_depends_on(self.id, DEPENDS_REASONS)

    def bake(self, seed: int, paths: Any, data_root: Path | None) -> dict[str, Any]:
        from .bake import bake_case

        return bake_case(seed, paths, data_root)


CASE = C15()
