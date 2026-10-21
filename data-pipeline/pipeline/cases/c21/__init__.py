"""C21, fair-lending disparity testing on public HMDA decisions, Delaware, year pairs 2018-19 to 2023-24 (unit U14-P3).

The case package (see ``docs/cases/C21.md`` and ``docs/design/features/c21/``): ``fetch`` (the raw HMDA files and their provenance),
``legal`` (the named conventions, the legal label and the group vocabulary), ``reader`` (the Data Browser reader, the decision and
identity conventions, contract 1), ``estimates`` (the rates, the tests, the controlled estimates, the confirmation and the situation
test, all through ``riskvalidation``), ``models`` (the models document), ``bake`` (the documents, the checksums and the manifest) and
``page`` (the results block of the case page). The heavy modules load when the case bakes, never at discovery.

The case measures statistical disparity in public decisions and scores nobody; every document says "no legal claim".
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

CASE_ID = "C21"
SOURCES = ("hmda",)


#: why this case reads what it reads of other cases, keyed by the document or the module its producer names: ``depends_on`` refuses a list that differs
#: from the source (core.manifest.derive_depends_on), so the manifest cannot state what the code does not do
DEPENDS_REASONS: dict[str, dict[str, str]] = {}


class C21:
    id = CASE_ID
    slug = "fair-lending-disparity-hmda"
    title = {"en": "Fair-lending disparity testing", "es": "Pruebas de disparidad en crédito justo"}
    category_id = "ml-ai-risk"
    kind = "real"
    question = {
        "en": "Do disparity tests find the same gaps in lending decisions from one year to the next?",
        "es": "¿Encuentran las pruebas de disparidad las mismas brechas en las decisiones de crédito de un año al siguiente?"}
    sources = SOURCES

    def depends_on(self) -> list[dict[str, Any]]:
        """What this case reads of other cases, as the manifest states it (``depends_on``)."""
        from ...core.manifest import derive_depends_on

        return derive_depends_on(self.id, DEPENDS_REASONS)

    def bake(self, seed: int, paths: Any, data_root: Path | None) -> dict[str, Any]:
        from .bake import bake_case

        return bake_case(seed, paths, data_root)


CASE = C21()
