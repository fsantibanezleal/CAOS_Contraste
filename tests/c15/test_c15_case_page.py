"""CT-1514: the results block of docs/cases/C15.md is the one generated from the committed documents."""
from __future__ import annotations

import c15_docs as d
from c15_support import VARIANT_IDS

from pipeline.cases.c15 import page

PAGE = d.ROOT / "docs" / "cases" / "C15.md"
NL = chr(10)


def test_the_case_page_results_block_is_generated_from_the_committed_documents() -> None:
    text = PAGE.read_text(encoding="utf-8")
    variants = {v: d.variant(v) for v in VARIANT_IDS}
    want = page.render(variants, d.models(), d.load(d.C15 / "raw-sources.txt"))
    assert set(want) == {"outcomes", "files", "results"}
    for name, body in want.items():
        begin, end = page.BLOCKS[name]
        assert begin in text and end in text, name
        got = text.split(begin, 1)[1].split(end, 1)[0].strip(NL)
        assert got == body.strip(NL), name
    for token in ("indexation", "offset", "floor", "dynamic NII", "synthetic", "adaptation", "Banco Central de Chile", "limits"):
        assert token.lower() in text.lower(), token
    # the raw files are listed with their hash and size, and the case page says what is real and what is synthetic
    for f in [x for v in d.load(d.C15 / "raw-sources.txt")["sources"].values() for x in v["files"]]:
        assert f["sha256"] in text and f"{f['bytes']:,}" in text, f["name"]
