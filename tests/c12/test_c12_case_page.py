"""CT-1219: the results block of docs/cases/C12.md is the one generated from the committed documents."""
from __future__ import annotations

import c12_docs as d

from pipeline.cases.c12 import page

PAGE = d.ROOT / "docs" / "cases" / "C12.md"


def test_the_case_page_results_block_is_generated_from_the_committed_documents() -> None:
    text = PAGE.read_text(encoding="utf-8")
    assert page.BEGIN in text and page.END in text
    got = text.split(page.BEGIN, 1)[1].split(page.END, 1)[0].strip("\n")
    want = page.results_block({v: d.variant(v) for v in d.VARIANTS}, d.models()).strip("\n")
    assert got == want
    for token in ("CRE52.17", "Treasury", "HQM", "ORE 1.8.17.0", "QuantLib", "SIMM", "sticky", "UNVERIFIED", "synthetic"):
        assert token.lower() in text.lower(), token
    raw = d.load(d.C12 / "raw-sources.txt")["sources"]
    for f in [x for v in raw.values() for x in v["files"]]:
        assert f["sha256"] in text and f"{f['bytes']:,}" in text, f["name"]
