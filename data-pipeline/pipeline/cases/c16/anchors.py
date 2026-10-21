"""The event anchors of C16: constants with their source and page, never inputs of a valuation.

The Federal Reserve review of the supervision of SVB (2023-04-28) states the size of the run; the BCBS Table A.1 rows are the
engine's (``riskvalidation.liquidity.runoff.TABLE_A1``, addendum L2.1). The review is fetched with the other raw files and the bake
checks that the quoted sentence is on the page named here (``verify_review``), so a constant cannot drift from its source.
"""
from __future__ import annotations

import re
from pathlib import Path

EVENT_DATE = "2023-03-10"
EVENT_HORIZON_DAYS = 2
#: "over 40 billion USD on 9 March plus over 100 billion USD expected on 10 March", in thousands of USD (the sum of the two figures)
EVENT_AMOUNT = 140_000_000.0
BOARD_SHARE = 0.85          # "roughly 85 percent" of the deposit base (the Board's own statement)
REVIEW_TITLE = "Review of the Federal Reserve's Supervision and Regulation of Silicon Valley Bank"
REVIEW_DATE = "2023-04-28"
REVIEW_URL = "https://www.federalreserve.gov/publications/files/svb-review-20230428.pdf"
REVIEW_PAGE = 18             # PDF page of the sentences below (also stated on PDF pages 7 and 38)
REVIEW_QUOTES = (
    "On March 9, SVB lost over $40 billion in deposits, and SVBFG management expected to lose over $100 billion more on March 10.",
    "represented roughly 85 percent of the bank",
)
REVIEW_SOURCE = f"Federal Reserve, {REVIEW_TITLE}, {REVIEW_DATE}, PDF page {REVIEW_PAGE}"
ANCHOR_SOURCE = ("BCBS, Report on the 2023 banking turmoil (d555), Box A, Table A.1 (SVB 2023, printed page 9); "
                 f"{REVIEW_TITLE}, {REVIEW_DATE}")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("’", "'").replace("�", "'"))


def verify_review(pdf_path: str | Path) -> None:
    """Refuse a review file whose page ``REVIEW_PAGE`` does not hold the quoted sentences (the anchors would not be its figures)."""
    from pypdf import PdfReader

    page = PdfReader(str(pdf_path)).pages[REVIEW_PAGE - 1].extract_text() or ""
    text = _norm(page)
    for q in REVIEW_QUOTES:
        if _norm(q) not in text:
            raise ValueError(f"{pdf_path}: page {REVIEW_PAGE} does not hold the sentence {q!r}")
