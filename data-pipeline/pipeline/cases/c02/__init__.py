"""C02, corporate PD across the 1 to 5 year horizons on the UCI Polish bankruptcy files (unit U14-P1).

The case package (see ``docs/cases/C02.md`` and ``docs/design/features/c02/``): ``conventions`` (the named parameters, the texts and the
vocabulary), ``reader`` (the ARFF reader, the verified zip, contract 1), ``prep`` (the leakage-safe preprocessing), ``fits`` (the
locked splits, the pooled union and the C01 ladder), ``battery`` (the rung battery, the challenger table and the transfer block, all
through ``riskvalidation``), ``blocks`` (the term-structure and Impact blocks), ``findings``, ``models`` (the models document),
``bake`` (the documents, the checksums and the manifest) and ``page`` (the results block of the case page). The heavy modules load when
the case bakes, never at discovery.

The files carry no date: the case makes no out-of-time claim.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

CASE_ID = "C02"
SOURCES = ("uci-polish",)


class C02:
    id = CASE_ID
    slug = "corporate-pd-horizons-polish"
    title = {"en": "Corporate PD across 1 to 5 year horizons", "es": "PD corporativa a horizontes de 1 a 5 años"}
    category_id = "credit-scoring"
    kind = "real"
    question = {
        "en": "How fast does discrimination fall from the 1-year to the 5-year horizon, do the learned rungs beat the scorecard by a margin "
              "a paired test supports, and do they stay calibrated?",
        "es": "¿Qué tan rápido cae la discriminación del horizonte de 1 año al de 5 años, superan los escalones de aprendizaje al scorecard "
              "por un margen que respalda una prueba pareada y se mantienen calibrados?"}
    sources = SOURCES

    def bake(self, seed: int, paths: Any, data_root: Path | None) -> dict[str, Any]:
        from .bake import bake_case

        return bake_case(seed, paths, data_root)


CASE = C02()
