"""C14, IRRBB: the six standardised shocks on the USD balance sheet of the bank that failed in March 2023 (unit U10-P1).

The case package (see ``docs/cases/C14.md`` and ``docs/design/features/c14/``): ``fetch`` (the raw FDIC and Treasury files and their
provenance), ``fdic`` (the reader and the dating rule; the Treasury reader is the shared ``pipeline.io.treasury``), ``bands`` and ``slotting`` (the call-report bands over the 19
buckets, the items), ``assumptions`` (the named behavioural assumptions), ``fits`` (the replicating portfolio, the deposit betas and the
volatility, on the history up to the date), ``variant`` (one valuation date through ``riskvalidation.irrbb``), ``models`` (the models
document), ``bake`` (the documents, the checksums and the manifest) and ``page`` (the results block of the case page).
The heavy modules load when the case bakes, never at discovery.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

CASE_ID = "C14"
SOURCES = ("fdic-bankfind", "treasury-par-curve")


class C14:
    id = CASE_ID
    slug = "irrbb-six-shocks-svb"
    title = {"en": "IRRBB, six shocks on a USD balance sheet: the bank that failed in 2023",
             "es": "IRRBB, seis choques sobre un balance en USD: el banco que quebró en 2023"}
    category_id = "balance-sheet"
    kind = "real"
    question = {
        "en": "Would the standardised EVE outlier test and the NII sensitivity have flagged the position of the bank that failed in March "
              "2023, read on its call reports, and how much does the answer hang on the deposit assumptions?",
        "es": "¿Habría señalado el test de valores atípicos del EVE estandarizado y la sensibilidad del NII la posición del banco que quebró "
              "en marzo de 2023, leída en sus reportes, y cuánto depende la respuesta de los supuestos sobre depósitos?"}
    sources = SOURCES

    def bake(self, seed: int, paths: Any, data_root: Path | None) -> dict[str, Any]:
        from .bake import bake_case

        return bake_case(seed, paths, data_root)


CASE = C14()
