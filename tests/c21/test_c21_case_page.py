"""CT-2116: the results block of docs/cases/C21.md is the one generated from the committed documents."""
from __future__ import annotations

from c21_support import MODELS, ROOT, VARIANTS, committed

from pipeline.cases.c21 import page

PAGE = ROOT / "docs" / "cases" / "C21.md"


def generated() -> str:
    return page.results_block({v: committed(v) for v in VARIANTS}, committed(MODELS)).strip("\n")


def test_the_case_page_results_block_is_generated_from_the_committed_documents() -> None:
    text = PAGE.read_text(encoding="utf-8")
    assert page.BEGIN in text and page.END in text
    assert page.block_of(text) == generated()
    for token in ("no legal claim", "employment benchmark", "credit score", "UNVERIFIED", "ceteris paribus", "Delaware", "convention"):
        assert token.lower() in text.lower(), token
    assert "## Executive brief" in text and text.index("## Executive brief") < text.index("## Data and what is real")


def test_the_executive_brief_and_the_row_table_carry_the_figures_of_the_documents() -> None:
    import re

    text = PAGE.read_text(encoding="utf-8")
    brief = text.split("## Executive brief", 1)[1].split("## Why this case exists", 1)[0]
    docs = {v: committed(v) for v in VARIANTS}

    def black_white(v: str) -> tuple[float, float, float, dict]:
        race = next(a for a in docs[v]["outputs"]["attributes"] if a["field"] == "derived_race")
        rate = {g["group"]: g["selection_rate"] for g in race["groups"]}
        c = next(c for c in race["contrasts"] if c["group"] == "Black or African American")
        return rate["Black or African American"], rate["White"], c["parity_ratio"], c

    b0, w0, r0, _ = black_white(VARIANTS[0])
    b5, w5, r5, _ = black_white(VARIANTS[-1])
    assert f"approved at {b0 * 100:.1f} percent in 2018 against {w0 * 100:.1f} percent" in brief and f"(parity ratio {r0:.3f})" in brief
    assert f"at {b5 * 100:.1f} against {w5 * 100:.1f} percent in 2024 ({r5:.3f})" in brief
    ratios = [black_white(v)[2] for v in VARIANTS]
    assert f"never rose above {max(ratios):.3f}" in brief
    odds = [black_white(v)[3]["controlled"]["estimate"]["odds_ratio"] for v in VARIANTS]
    assert f"odds ratio is {min(odds):.2f} to {max(odds):.2f} in every year" in brief
    sizes = [black_white(v)[3]["confirmation"]["estimate"]["size_ratio"] for v in VARIANTS]
    assert all(black_white(v)[3]["confirmation"]["estimate"]["same_sign"] for v in VARIANTS)
    assert f"size ratios from {min(sizes):.2f} to {max(sizes):.2f}" in brief and "6 of 6 for Black applicants" in brief
    contrasts = [c for d in docs.values() for a in d["outputs"]["attributes"] for c in a["contrasts"]]
    excluded = sum(1 for c in contrasts if c["controlled"]["estimate"]["ci"]["lo"] > 0 or c["controlled"]["estimate"]["ci"]["hi"] < 0)
    same = sum(1 for c in contrasts if c["confirmation"]["estimate"]["same_sign"])
    assert f"in {excluded} of {len(contrasts)} group contrasts" in brief and f"same sign in {same} of {len(contrasts)} contrasts" in brief
    flagged_black = [v for v in VARIANTS if any(r["flag"] for a in docs[v]["outputs"]["attributes"] if a["field"] == "derived_race"
                                                for r in a["four_fifths"]["groups"] if r["group"] == "Black or African American")]
    assert flagged_black == [VARIANTS[0]] and "Black applicants only in 2018" in brief
    per_year = [sum(r["flag"] for a in docs[v]["outputs"]["attributes"] if a["field"] == "derived_race" for r in a["four_fifths"]["groups"]) for v in VARIANTS]
    assert (min(per_year), max(per_year)) == (2, 4) and "two to four groups of the race attribute" in brief
    # the row table: decision rows of each year are the fit-year rows (and the confirm rows of the last pair); the file rows add the left-out codes
    for v in VARIANTS:
        o = docs[v]["outputs"]
        left = int(re.search(r"(\d+) rows of codes 4 to 8", next(n for n in o["data_notes"] if n["field"] == "action_taken")["reason"]["en"]).group(1))
        assert f"| {o['fit_year']} | {o['scope']['rows_fit'] + left:,} | {o['scope']['rows_fit']:,} |" in text
    assert f"{docs[VARIANTS[-1]]['outputs']['scope']['rows_confirm']:,} |" in text
