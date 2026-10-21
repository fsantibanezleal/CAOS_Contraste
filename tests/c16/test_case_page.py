"""CT-1622: the results block of the case page is generated from the committed documents."""
from __future__ import annotations

import json

from .helpers import ROOT, committed_documents

PAGE = ROOT / "docs" / "cases" / "C16.md"


def test_the_case_page_results_block_is_generated_from_the_committed_documents():
    from pipeline.cases.c16 import page

    text = PAGE.read_text(encoding="utf-8")
    assert page.BEGIN in text and page.END in text
    assert text.count(page.BEGIN) == 1 and text.count(page.END) == 1
    block = text.split(page.BEGIN, 1)[1].split(page.END, 1)[0].strip("\n")
    docs = committed_documents()
    assert block == page.results_block(docs["lcr-standard"], docs["list-adverse"], docs["list-extreme"], docs["fast-run"],
                                       docs["htm-losses"], docs["reverse-stress"], docs["models-svb-liquidity"]).strip("\n")
    # the page states what it must: both denominators, the label of the LCR, the real-aggregates statement
    for needle in ("DEPDOM", "never the reported or regulatory LCR", "synthetic", "Basel formula"):
        assert needle in text, needle
    # the table of raw files is the one generated from the committed record, which names the four sources of the manifest
    raw = json.loads((ROOT / "data" / "derived" / "C16" / "raw-sources.txt").read_text(encoding="utf-8"))
    got = text.split(page.RAW_BEGIN, 1)[1].split(page.RAW_END, 1)[0].strip("\n")
    assert got == page.raw_block(raw).strip("\n")
    assert set(raw["sources"]) == {"fdic-bankfind", "fed-h8", "fed-svb-review", "treasury-par-curve"}
