"""CT-1112: the case page says what the portfolio is and is not, and its results are the committed documents'."""
from __future__ import annotations

from pathlib import Path

from pipeline.cases.c10 import page

ROOT = Path(__file__).resolve().parents[2]


def test_the_case_page_results_block_is_generated_from_the_committed_documents() -> None:
    text = (ROOT / "docs" / "cases" / "C10.md").read_text(encoding="utf-8")
    assert page.claim_findings(text) == [], page.claim_findings(text)
    start, end = page.MARK_START, page.MARK_END
    assert text.count(start) == 1 and text.count(end) == 1
    block = text.split(start, 1)[1].split(end, 1)[0].strip("\n")
    assert block == page.results_block(ROOT / "data" / "derived").strip("\n"), "regenerate it: python data-pipeline/pipeline/cases/c10/page.py"
