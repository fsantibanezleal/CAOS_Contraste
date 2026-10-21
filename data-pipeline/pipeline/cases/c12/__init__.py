"""C12, swap exposure, CVA and SA-CCR: a synthetic USD swap book on the US Treasury curves, in six variants (unit U9-P1).

The case package (see ``docs/cases/C12.md`` and ``docs/design/features/c12/``): ``fetch`` (the raw Treasury and HQM files and their
provenance), ``data`` (the readers, the backtest dates, the HQM spread), ``book`` (the named parameters and the synthetic book),
``calibration`` (the AR(1) fit up to a date), ``exposure`` (the paths, the sticky-date close-out, variation and initial margin),
``credit`` (CVA, DVA, wrong-way risk), ``regulatory`` (SA-CCR, BA-CVA, GIRR), ``backtest`` (the PIT backtest), ``ore`` and
``reconcile`` (ORE 1.8.17.0 and QuantLib 1.44), ``variant`` (one document), ``models`` (the models document), ``bake`` (the
documents, the checksums and the manifest) and ``page`` (the results block of the case page). ``ore_inputs/`` holds the committed
ORE XML inputs of the bake. The heavy modules load when the case bakes, never at discovery.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

CASE_ID = "C12"
SOURCES = ("treasury-par-curve", "treasury-hqm")


#: why this case reads what it reads of other cases, keyed by the document or the module its producer names: ``depends_on`` refuses a list that differs
#: from the source (core.manifest.derive_depends_on), so the manifest cannot state what the code does not do
DEPENDS_REASONS: dict[str, dict[str, str]] = {}


class C12:
    id = CASE_ID
    slug = "swap-exposure-cva-sa-ccr"
    title = {"en": "How large is the counterparty exposure of a swap book, and what CVA does it imply?",
             "es": "¿Qué tan grande es la exposición a la contraparte de un libro de swaps y qué CVA implica?"}
    category_id = "market-ccr"
    kind = "synthetic"
    question = {
        "en": "How large is the counterparty exposure of a swap book, what CVA does it imply, and would the simulated exposures have held "
              "against the curves later realised?",
        "es": "¿Qué tan grande es la exposición a la contraparte de un libro de swaps, qué CVA implica y habrían resistido las exposiciones "
              "simuladas frente a las curvas realizadas después?"}
    sources = SOURCES

    def depends_on(self) -> list[dict[str, Any]]:
        """What this case reads of other cases, as the manifest states it (``depends_on``)."""
        from ...core.manifest import derive_depends_on

        return derive_depends_on(self.id, DEPENDS_REASONS)

    def bake(self, seed: int, paths: Any, data_root: Path | None) -> dict[str, Any]:
        from .bake import bake_case

        return bake_case(seed, paths, data_root)


CASE = C12()
