"""U16-F2 (the R2 fix round, C03): the Spanish rationale writes its numbers as Spanish, the calibration scope is bilingual."""
from __future__ import annotations

import json
import re

from .helpers import COHORT_IDS, COMMITTED

ENGLISH_GROUPED = re.compile(r"\d,\d{3}\b")


def _doc(cid: str) -> dict:
    return json.loads((COMMITTED / "C03" / f"{cid}.json").read_text(encoding="utf-8"))


def test_the_spanish_rationale_has_spanish_numbers_in_every_variant_and_in_the_models_document() -> None:
    """PR-C03 (b02 M6): '413,083 créditos' read as 413.083 in Spanish."""
    models = json.loads((COMMITTED / "C03" / "models-sba-7a.json").read_text(encoding="utf-8"))
    for cid in COHORT_IDS:
        t = _doc(cid)["outputs"]["training"]
        es, en = t["rationale"]["es"], t["rationale"]["en"]
        assert not ENGLISH_GROUPED.search(es), (cid, es)
        assert f"{t['n_loans']:,}" in en
        assert f"{t['n_loans']:,}".replace(",", ".") in es and f"{t['n_events']:,}".replace(",", ".") in es, cid
        w = next(x for x in models["fit"]["cohort_windows"] if x["id"] == cid)
        assert w["training"] == t, cid


def test_the_calibration_scope_is_a_bilingual_text() -> None:
    """V03-2 (b02 B2): the view printed the English scope in the Spanish capture."""
    for cid in COHORT_IDS:
        scope = _doc(cid)["outputs"]["calibration"]["scope"]
        assert isinstance(scope, dict) and set(scope) == {"en", "es"}, cid
        assert scope["en"].startswith("vintages with an observed 5-year mark: FY")
        assert "vintages" not in scope["es"] and "FY" not in scope["es"] and "AF" in scope["es"], cid
