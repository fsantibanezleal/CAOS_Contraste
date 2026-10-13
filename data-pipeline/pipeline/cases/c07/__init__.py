"""C07, the Chile provisions trilogy (U5-P2): one synthetic bank, "Banco Andino", provisioned under CMF CNCB B-1, IFRS 9
and BdE Circular 4/2017 Annex 9 on the same portfolio, in six scenario variants.

The design is docs/design/features/c07/design.md; requirements CT-701 to CT-713 hold it. The accounts are generated from a
seed and calibrated to the CMF system aggregates of ``sources.TARGETS`` (truth status synthetic-calibrated: Banco Andino is not
a real bank); every regime number is a ``riskvalidation`` 0.5.0 result (``provisions.local_cl``, ``provisions.local_es``,
``provisions.ecl`` and the staging, term-structure, overlay and reconciliation modules, ``validation.ifrs9``).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


CASE_ID = "C07"


class C07:
    id = CASE_ID
    slug = "provisions-trilogy"
    title = {"en": "Chile provisions trilogy: CMF B-1 vs IFRS 9 vs BdE Annex 9",
             "es": "Trilogía de provisiones en Chile: CMF B-1 vs IFRS 9 vs Anexo 9 del BdE"}
    category_id = "provisions"
    kind = "synthetic"
    question = {"en": "How far apart are the provisions of CMF B-1, IFRS 9 and BdE Annex 9 on the same portfolio under stress?",
                "es": "¿Qué tan distintas son las provisiones de CMF B-1, IFRS 9 y el Anexo 9 del BdE sobre una misma cartera bajo tensión?"}
    sources: tuple[str, ...] = ()  # no third-party input file: the CMF figures are committed targets with their hashes

    def bake(self, seed: int, paths: Any, data_root: Path | None, scale: float = 1.0) -> dict[str, Any]:
        from .bake import bake_case

        return bake_case(seed, paths, data_root, scale, title=self.title, question=self.question)


CASE = C07()
