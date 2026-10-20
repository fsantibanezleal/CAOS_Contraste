"""CT-1821: the results block of docs/cases/C18.md is the one generated from the committed documents."""
from __future__ import annotations

import json
from pathlib import Path

from c18_support import C18, ROOT

from pipeline.cases.c18 import page

PAGE = ROOT / "docs" / "cases" / "C18.md"
NAMES = {"baseline": "baseline", "eba-2025-adverse": "eba-2025-adverse", "fed-2026-severely-adverse": "fed-2026-severely-adverse",
         "ngfs-delayed-transition": "ngfs-delayed-transition", "t-copula-baseline": "t-copula-baseline", "reverse-stress": "reverse-stress"}


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_the_case_page_results_block_is_generated_from_the_committed_documents() -> None:
    text = PAGE.read_text(encoding="utf-8")
    assert page.BEGIN in text and page.END in text
    got = text.split(page.BEGIN, 1)[1].split(page.END, 1)[0].strip("\n")
    variants = {v: load(C18 / f"{v}.json") for v in NAMES}
    want = page.results_block(variants, load(C18 / "models-banco-andino.json")).strip("\n")
    assert got == want
    for token in ("simple sum", "synthetic", "US-calibrated", "UNVERIFIED", "convention", "Annex 3", "out-of-time"):
        assert token.lower() in text.lower(), token
