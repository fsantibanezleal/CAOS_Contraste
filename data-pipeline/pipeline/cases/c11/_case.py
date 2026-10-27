"""The C11 case object (SDD C11): what discovery reads; the bake loads when it runs, never at discovery."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .constants import CASE_ID

SOURCES = ("french-data-library", "treasury-par-curve", "fred-public-domain")


def _t(en: str, es: str) -> dict:
    return {"en": en, "es": es}


#: why this case reads what it reads of other cases, keyed by the document or the module its producer names: ``depends_on`` refuses a list that differs
#: from the source (core.manifest.derive_depends_on), so the manifest cannot state what the code does not do
DEPENDS_REASONS: dict[str, dict[str, str]] = {}


class C11:
    id = CASE_ID
    slug = "market-var-es"
    category_id = "market-ccr"
    kind = "real"
    title = _t("Market VaR/ES backtesting across 2008, 2020, 2022, 2023", "Pruebas retrospectivas de VaR/ES de mercado en 2008, 2020, 2022 y 2023")
    question = _t("Do VaR and expected shortfall models pass their backtests across the 2008, 2020, 2022 and 2023 episodes?",
                  "¿Pasan los modelos de VaR y de pérdida esperada en cola sus pruebas retrospectivas en los episodios de 2008, 2020, 2022 y 2023?")
    sources = SOURCES

    def depends_on(self) -> list[dict[str, Any]]:
        """What this case reads of other cases, as the manifest states it (``depends_on``)."""
        from ...core.manifest import derive_depends_on

        return derive_depends_on(self.id, DEPENDS_REASONS)

    def bake(self, seed: int, paths: Any, data_root: Path, cache_dir: Path | None = None, workers: int = 4) -> dict[str, Any]:
        from . import bake as _bake

        cache = Path(cache_dir) if cache_dir else Path(data_root) / "cache" / "c11"
        return _bake.bake_all(paths.root, Path(data_root), cache, workers=workers, seed=seed)


CASE = C11()
