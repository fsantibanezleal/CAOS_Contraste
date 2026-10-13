"""CT-812: the case page says what the data are and are not, states each variant's training window, and its results are the committed
documents'."""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.cases.c03 import page

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "docs" / "cases" / "C03.md"
DERIVED = ROOT / "data" / "derived"


def test_the_case_page_states_its_data_and_its_results_come_from_the_documents():
    text = PAGE.read_text(encoding="utf-8")
    assert page.claim_findings(text) == [], page.claim_findings(text)
    assert page.window_findings(text, DERIVED) == [], page.window_findings(text, DERIVED)
    low = text.lower()
    assert "small-business" in low and "sba 7(a)" in low and "right-censor" in low and "not a bank" in low
    start, end = page.MARK_START, page.MARK_END
    assert text.count(start) == 1 and text.count(end) == 1
    block = text.split(start, 1)[1].split(end, 1)[0].strip("\n")
    assert block == page.results_block(DERIVED).strip("\n"), "regenerate it: python data-pipeline/pipeline/cases/c03/page.py"
    models = json.loads((DERIVED / "C03" / "models-sba-7a.json").read_text(encoding="utf-8"))
    for w in models["fit"]["cohort_windows"]:
        assert f"FY{w['training']['first_fy']} to FY{w['training']['last_fy']}" in block, "every window of the documents is on the page"


def test_adversarial_a_page_with_a_wrong_window_or_a_bank_wide_claim_is_found():
    ok = ("The SBA 7(a) loans are small-business loans, not a bank's SME book. The active loans are right-censored. "
          "FY2006-07 trains on FY1991 to FY2000.\n")
    assert page.claim_findings(ok) == []
    assert page.window_findings(ok, DERIVED) == []
    assert page.claim_findings("This case reports the PD of a bank-wide SME portfolio.\n") != []
    assert page.claim_findings("The SBA 7(a) data are small-business loans.\n") != [], "the censoring is not stated"
    wrong = ok.replace("FY2000", "FY2001")
    assert page.window_findings(wrong, DERIVED) != []
