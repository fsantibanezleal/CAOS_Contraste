"""CT-1715: the results block of docs/cases/C17.md is generated from the committed documents."""
from __future__ import annotations

from conftest import DERIVED, ROOT
from pipeline.cases.c17 import page


def test_the_case_page_results_block_is_generated_from_the_committed_documents():
    text = (ROOT / "docs" / "cases" / "C17.md").read_text(encoding="utf-8")
    assert page.MARK_START in text and page.MARK_END in text
    block = text.split(page.MARK_START, 1)[1].split(page.MARK_END, 1)[0].strip("\n")
    assert block == page.results_block(DERIVED).strip("\n")
    assert page.claim_findings(text) == []
