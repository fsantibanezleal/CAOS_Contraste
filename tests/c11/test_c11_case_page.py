"""CT-615: the case page states its data, its derived-only rule and its limits, and its results are the committed documents'."""
from __future__ import annotations

from pathlib import Path

from pipeline.cases.c11 import page

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "docs" / "cases" / "C11.md"


def test_the_case_page_states_its_data_and_its_results_come_from_the_documents():
    text = PAGE.read_text(encoding="utf-8")
    assert page.claim_findings(text) == [], page.claim_findings(text)
    low = text.lower()
    assert "derived-only" in low and "limits" in low and "refit" in low and "1995-01-01" in low
    assert text.count(page.MARK_START) == 1 and text.count(page.MARK_END) == 1
    block = text.split(page.MARK_START, 1)[1].split(page.MARK_END, 1)[0].strip("\n")
    want = page.blocks(ROOT / "data" / "derived", ROOT / "docs" / "design" / "features" / "c11").strip("\n")
    assert block == want, "regenerate it: python data-pipeline/pipeline/cases/c11/page.py"


def test_adversarial_a_hand_edited_results_block_or_a_page_that_hides_the_derived_only_rule_is_found():
    assert page.claim_findings("The French returns are listed below.\n") != []
    ok = ("Treasury and H.10 series. The French returns are derived-only and withheld. The Z2 null is tail-consistent. "
          "Raw French files stay out.\n")
    assert page.claim_findings(ok) == []
    assert page.claim_findings("Treasury, H.10 and a tail-consistent null.\n") != []      # derived-only never named
