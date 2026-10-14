"""C10, portfolio credit capital on the Federal Reserve charge-off rates and a known-correlation simulator (unit U7-P).

The Vasicek distribution is fitted to the yearly net charge-off rates of five loan types on 1985-2006 and the 2007-2012 tail is
placed in it; an illustrative portfolio per loan type gets its loss distribution by the six rungs of the ladder (large homogeneous
portfolio, Gaussian copula, Student-t copula, CreditRisk+, granularity adjustment, importance sampling) with Euler contributions;
a simulator with a known asset correlation gives the exact size and power of the correlation estimates. Every capital, quantile,
contribution, adjustment and test comes from ``riskvalidation`` 0.7 (``portfolio``, ``validation.portfolio``); the product reads
the Board's page, builds the inputs and orders the answers.

The case page is ``docs/cases/C10.md`` and the design ``docs/design/features/c10/``; requirements CT-1101 to CT-1112 hold it.
The heavy modules load when the case bakes, never at discovery.

Registration. ``pipeline/cases/__init__.py`` discovers a case by a module-level ``CASE``. This package exposes ``CASE_C10`` and not
``CASE``: the registry, the index, the readiness, the planned-case list and the case-count tests are the integrator's files
(unit U7 sizing, "Integrator and merge order"), and a ``CASE`` here would break them on this branch alone. The integration commit adds
the line ``CASE = CASE_C10`` below; until then the bake runs as ``python -m pipeline.cases.c10.bake`` from ``data-pipeline/``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

CASE_ID = "C10"


class C10:
    id = CASE_ID
    slug = "portfolio-credit-capital"
    title = {"en": "Portfolio credit capital: ASRF, Vasicek fit, copula MC",
             "es": "Capital de crédito de cartera: ASRF, ajuste de Vasicek, Monte Carlo con cópula"}
    category_id = "portfolio-capital"
    kind = "real"
    question = {"en": "Do the ASRF formula, a fitted Vasicek model and a copula simulation agree on portfolio credit capital, "
                      "including the 2007 to 2012 tail?",
                "es": "¿Coinciden la fórmula ASRF, un modelo de Vasicek ajustado y una simulación con cópula en el capital de crédito "
                      "de cartera, incluida la cola de 2007 a 2012?"}
    sources = ("fed-chargeoff",)

    def bake(self, seed: int, paths: Any, data_root: Path | None, scale: float = 1.0, page: Path | None = None,
             only: tuple[str, ...] | None = None, lengths: tuple[int, ...] | None = None) -> dict[str, Any]:
        from .bake import bake_case

        return bake_case(seed, paths, data_root, scale, title=self.title, question=self.question, page=page, only=only, lengths=lengths)


CASE_C10 = C10()
