"""CT-916: the case page says what the data are and what they are not, and its results are the committed documents'."""
from __future__ import annotations

from pathlib import Path

from pipeline.cases.c08 import page

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "docs" / "cases" / "C08.md"


def test_the_case_page_states_its_proxy_and_its_results_come_from_the_documents():
    text = PAGE.read_text(encoding="utf-8")
    assert page.claim_findings(text) == [], page.claim_findings(text)
    low = text.lower()
    assert "grosschargeoffamount" in low and "grossapproval" in low and "biased low" in low
    assert "small-business" in low and "not mortgage" in low
    assert "freddie mac" in low and "account is missing" in low
    assert "limits" in low and "no recovery" in low
    start, end = page.MARK_START, page.MARK_END
    assert text.count(start) == 1 and text.count(end) == 1
    block = text.split(start, 1)[1].split(end, 1)[0].strip("\n")
    assert block == page.results_block(ROOT / "data" / "derived").strip("\n"), "regenerate it: python data-pipeline/pipeline/cases/c08/page.py"


def test_adversarial_a_page_that_claims_a_mortgage_or_freddie_result_is_found():
    assert page.claim_findings("This case reports Freddie Mac mortgage results for 2008 and also reads the SBA 7(a) file.\n")
    assert page.claim_findings("The data are mortgage loans on the SBA file.\n")
    assert page.claim_findings("The SBA 7(a) data are small-business loans, not mortgages, and Freddie Mac's account is missing.\n") == []
    assert page.claim_findings("The data are small-business loans, not mortgages.\n") == ["the page does not name the SBA data"]
