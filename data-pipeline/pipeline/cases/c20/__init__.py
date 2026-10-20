"""C20, ML model validation: drift, robustness, explanation stability and leakage on the SantanderAI stressed German credit data, the UCI
models and the Federal Reserve corporate portfolios as shift probes (unit U14-P2).

The case package (see ``docs/cases/C20.md`` and ``docs/design/features/c20/``): ``conv`` (the named parameters and the texts), ``fetch``
(the SGCD files at the pinned commit and the Fed portfolios, with their provenance), ``sgcd``, ``fed`` and ``polish`` (the readers),
``shocks`` (Contraste's own application of the shock families to the structured view), ``data`` (the model frames through contract 1),
``fits`` (the ladder rungs, the attributions and the effect curves), ``battery`` (the fairness battery and the decision-flip impact),
``variants`` (the six variants through ``riskvalidation``), ``models`` (the models document), ``bake`` (the documents, the checksums and
the manifest) and ``page`` (the results block of the case page). The heavy modules load when the case bakes, never at discovery.

The data of SGCD must not be used for real-world credit scoring: every SGCD document carries the dataset card sentence.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

CASE_ID = "C20"
SOURCES = ("santanderai-sgcd", "uci-taiwan", "uci-polish", "fed-stress-tests")


class C20:
    id = CASE_ID
    slug = "ml-model-validation-drift-robustness"
    title = {"en": "ML model validation: drift, robustness, explanation stability",
             "es": "Validación de modelos de ML: deriva, robustez y estabilidad de explicaciones"}
    category_id = "ml-ai-risk"
    kind = "real"
    question = {
        "en": "Do performance, drift, attribution and reason-code stability survive shocks the model has and has not seen, shifted "
              "populations, input noise and retraining seeds, and does the leakage screen catch a planted leak?",
        "es": "¿Sobreviven el desempeño, la deriva, la atribución y la estabilidad de los códigos de razón a choques que el modelo ha visto "
              "y no ha visto, a poblaciones desplazadas, al ruido de entrada y a las semillas de reentrenamiento, y detecta la prueba de "
              "fuga un dato filtrado plantado?"}
    sources = SOURCES

    def bake(self, seed: int, paths: Any, data_root: Path | None) -> dict[str, Any]:
        from .bake import bake_case

        return bake_case(seed, paths, data_root)


CASE = C20()
