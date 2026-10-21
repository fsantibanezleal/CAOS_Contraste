"""C16, liquidity stress, the LCR and the March 2023 run, on the call reports of the bank that failed on 2023-03-10 (unit U11-P).

The case package (see ``docs/cases/C16.md`` and ``docs/design/features/c16/``): ``fetch`` (the raw FDIC and H.8 files and their
provenance; the Treasury files are C14's), ``h8`` (the release reader), ``anchors`` (the event constants with their source and page),
``assumptions`` (the named parameters and the mapping tables, every one a convention), ``balance`` (the call-report mapping: deposits,
securities by type, the sheet, the contractual ladder), ``variant`` (one scenario variant through ``riskvalidation``), ``reverse`` (the
reverse stress), ``models`` (the models document: tables, calibration, generator), ``bake`` (the documents, the checksums and the
manifest) and ``page`` (the results block of the case page). The product computes no liquidity quantity: every ratio, run-off,
haircut, survival period and multiplier is a ``riskvalidation`` call (ADR-0069). The heavy modules load when the case bakes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

CASE_ID = "C16"
SOURCES = ("fdic-bankfind", "fed-h8", "fed-svb-review", "treasury-par-curve")


#: why this case reads what it reads of other cases, keyed by the document or the module its producer names: ``depends_on`` refuses a list that differs
#: from the source (core.manifest.derive_depends_on), so the manifest cannot state what the code does not do
DEPENDS_REASONS: dict[str, dict[str, str]] = {}


class C16:
    id = CASE_ID
    slug = "liquidity-lcr-march-2023-run"
    title = {"en": "Liquidity stress, LCR and the March 2023 run", "es": "Estrés de liquidez, LCR y la corrida de marzo de 2023"}
    category_id = "balance-sheet"
    kind = "real"
    question = {
        "en": "Would the LCR and liquidity stress models have flagged the March 2023 deposit run?",
        "es": "¿Habrían alertado el LCR y los modelos de estrés de liquidez sobre la corrida de depósitos de marzo de 2023?"}
    sources = SOURCES

    def depends_on(self) -> list[dict[str, Any]]:
        """What this case reads of other cases, as the manifest states it (``depends_on``)."""
        from ...core.manifest import derive_depends_on

        return derive_depends_on(self.id, DEPENDS_REASONS)

    def bake(self, seed: int, paths: Any, data_root: Path | None) -> dict[str, Any]:
        from .bake import bake_case

        return bake_case(seed, paths, data_root)


CASE = C16()
