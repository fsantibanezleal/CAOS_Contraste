"""CT-1414: the results block of docs/cases/C14.md is the one generated from the committed documents."""
from __future__ import annotations

import c14_docs as d

from pipeline.cases.c14 import page

PAGE = d.ROOT / "docs" / "cases" / "C14.md"


def test_the_case_page_results_block_is_generated_from_the_committed_documents() -> None:
    text = PAGE.read_text(encoding="utf-8")
    assert page.BEGIN in text and page.END in text
    got = text.split(page.BEGIN, 1)[1].split(page.END, 1)[0].strip("\n")
    want = page.results_block({v: d.variant(v) for v in d.VARIANTS}, d.models()).strip("\n")
    assert got == want
    for token in ("Tier 1", "behavioural", "synthetic", "2016", "out-of-sample", "EaR"):
        assert token.lower() in text.lower(), token


def test_the_executive_brief_and_the_raw_file_table_carry_the_figures_of_the_documents() -> None:
    text = PAGE.read_text(encoding="utf-8")
    brief = text.split("## Executive brief", 1)[1].split("## Why this case exists", 1)[0]
    ratios = {}
    for vid in d.VARIANTS:
        sc = {(s["calibration"], s["nmd_assumption"]): s for s in d.variant(vid)["outputs"]["scenarios"]}
        ratios[vid] = (sc[("2024", "behavioural")]["outlier"]["ratio"], sc[("2024", "contractual")]["outlier"]["ratio"])
    beh = ", ".join(f"{ratios[v][0] * 100:.1f}" for v in d.VARIANTS)
    con = ", ".join(f"{ratios[v][1] * 100:.1f}" for v in d.VARIANTS)
    assert f"is {beh.rsplit(', ', 1)[0]} and {beh.rsplit(', ', 1)[1]} percent" in brief
    assert f"it is {con.rsplit(', ', 1)[0]} and {con.rsplit(', ', 1)[1]} percent" in brief
    oos = d.variant("vd-2021-q4")["outputs"]["out_of_sample"]
    assert f"{oos['relative_error'] * 100:.0f} percent away" in brief
    assert f"{-oos['projected_delta_nii'] / 1e6:.2f} billion" in brief and f"{-oos['realised_delta_nii'] / 1e6:.2f} billion" in brief
    for f in [x for v in d.load(d.C14 / "raw-sources.txt")["sources"].values() for x in v["files"]]:
        assert f["sha256"] in text and f"{f['bytes']:,}" in text, f["name"]
