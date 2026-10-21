"""C09, EAD and CCF for revolving lines (U6-P3): a seeded generator of credit-line histories with a known CCF, shaped on the
Federal Reserve 2025 hypothetical card portfolios, at six utilisation acceleration levels, estimated through ``riskvalidation``
0.6.0 (``lgd_ead.ccf``, ``lgd_ead.floors``, ``lgd_ead.lgd_models``, ``validation.lgd_ead``).

The design is docs/design/features/c09/design.md; requirements CT-1001 to CT-1013 hold it. Truth status synthetic-known-truth: the
lines are generated, not observed, and the CCF each level is drawn with is stated by the parameters (``params.known_ccf``).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

CASE_ID = "C09"


#: why this case reads what it reads of other cases, keyed by the document or the module its producer names: ``depends_on`` refuses a list that differs
#: from the source (core.manifest.derive_depends_on), so the manifest cannot state what the code does not do
DEPENDS_REASONS: dict[str, dict[str, str]] = {}


class C09:
    id = CASE_ID
    slug = "ead-ccf-revolving-lines"
    title = {"en": "EAD and CCF for revolving lines", "es": "EAD y CCF de líneas rotativas"}
    category_id = "lgd-ead"
    kind = "synthetic"
    question = {"en": "Can exposure at default and the credit conversion factor of revolving lines be recovered when utilisation accelerates?",
                "es": "¿Se pueden recuperar la exposición al incumplimiento y el factor de conversión de crédito de líneas rotativas cuando se acelera la utilización?"}
    sources: tuple[str, ...] = ()  # no registered input file: the Fed marginals are committed in params with their hashes

    def depends_on(self) -> list[dict[str, Any]]:
        """What this case reads of other cases, as the manifest states it (``depends_on``)."""
        from ...core.manifest import derive_depends_on

        return derive_depends_on(self.id, DEPENDS_REASONS)

    def bake(self, seed: int, paths: Any, data_root: Path | None, scale: float = 1.0) -> dict[str, Any]:
        from .bake import bake_case

        return bake_case(seed, paths, data_root, scale, title=self.title, question=self.question)


CASE = C09()
