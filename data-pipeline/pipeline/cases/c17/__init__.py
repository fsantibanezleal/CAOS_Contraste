"""C17, operational risk: the LDA against the SMA (U12-P): a seeded generator of annual operational loss histories of a synthetic
bank, calibrated to the BCBS 2008 LDCE medians, with a known true annual loss distribution at four tail indices (0.6, 0.8, 0.96 and
1.1), 5 or 10 years of data and a collection threshold of EUR 10,000 or 20,000, estimated through ``riskvalidation.oprisk`` (the
Poisson-lognormal LDA that ignores the threshold, the truncated lognormal LDA, the lognormal body and GPD tail splice, the single
loss approximation, the scenario combination by Bayesian credibility) and the standardised approach of OPE25.

The design is docs/design/features/c17/design.md; requirements CT-1701 to CT-1715 hold it. Truth status synthetic-known-truth: the
losses are generated, not observed, and the true 99.9 percent annual loss quantile of each variant is stated by ``truth.py``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

CASE_ID = "C17"


class C17:
    id = CASE_ID
    slug = "operational-risk-lda-sma"
    title = {"en": "Operational risk: LDA vs SMA", "es": "Riesgo operacional: LDA vs SMA"}
    category_id = "operational"
    kind = "synthetic"
    question = {"en": "How do the loss distribution approach and the standardised measurement approach differ on heavy-tailed operational losses?",
                "es": "¿En qué difieren el enfoque de distribución de pérdidas y el enfoque de medición estandarizado con pérdidas operacionales de cola pesada?"}
    sources: tuple[str, ...] = ()  # no registered input file: the LDCE medians are committed in params with their source

    def bake(self, seed: int, paths: Any, data_root: Path | None, scale: float = 1.0) -> dict[str, Any]:
        from .bake import bake_case

        return bake_case(seed, paths, data_root, scale, title=self.title, question=self.question)


CASE = C17()
