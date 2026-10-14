"""CT-1313: the results block of the case page is the one generated from the committed documents."""
from __future__ import annotations

from pathlib import Path

from pipeline.cases.c13 import page

ROOT = Path(__file__).resolve().parents[2]


def test_the_case_page_results_block_is_generated_from_the_committed_documents() -> None:
    text = (ROOT / "docs" / "cases" / "C13.md").read_text(encoding="utf-8")
    head, rest = text.split(page.MARK_START, 1)
    block = rest.split(page.MARK_END, 1)[0].strip("\n")
    assert block == page.results_block(ROOT / "data" / "derived").strip("\n")
    assert page.claim_findings(text) == []
