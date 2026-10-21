"""C13, FRTB desk eligibility: the P&L attribution (PLA) test and the desk back-test (U8-P2): a seeded generator of desk
hypothetical and risk-theoretical P&L with a known risk model and the six planted deficiencies of the SDD, 250-day windows,
1,000 independent replications per deficiency, every statistic, zone and count returned by ``riskvalidation.market`` (engine
contract ``engine-market-api`` 1.0.0).

The design is docs/design/features/c13/design.md; requirements CT-1301 to CT-1313 hold it. Truth status synthetic-known-truth:
the desk P&L is generated, not observed, and the deficiency each variant plants is stated by ``params.DEFICIENCIES``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

CASE_ID = "C13"


#: why this case reads what it reads of other cases, keyed by the document or the module its producer names: ``depends_on`` refuses a list that differs
#: from the source (core.manifest.derive_depends_on), so the manifest cannot state what the code does not do
DEPENDS_REASONS: dict[str, dict[str, str]] = {}


class C13:
    id = CASE_ID
    slug = "frtb-desk-eligibility"
    title = {"en": "FRTB desk eligibility: PLA and desk backtesting", "es": "Elegibilidad de mesas FRTB: PLA y backtesting de mesa"}
    category_id = "market-ccr"
    kind = "synthetic"
    question = {"en": "Do the P&L attribution and desk backtesting tests of FRTB detect planted model deficiencies?",
                "es": "¿Detectan las pruebas de atribución de P&L y de backtesting de mesa de FRTB deficiencias de modelo plantadas?"}
    sources: tuple[str, ...] = ()  # a generator: no registered input file

    def depends_on(self) -> list[dict[str, Any]]:
        """What this case reads of other cases, as the manifest states it (``depends_on``)."""
        from ...core.manifest import derive_depends_on

        return derive_depends_on(self.id, DEPENDS_REASONS)

    def bake(self, seed: int, paths: Any, data_root: Path | None, scale: float = 1.0) -> dict[str, Any]:
        from .bake import bake_case

        return bake_case(seed, paths, data_root, scale, title=self.title, question=self.question)


CASE = C13()
