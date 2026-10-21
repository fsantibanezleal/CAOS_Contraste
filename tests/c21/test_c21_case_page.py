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


def test_the_lights_sentence_agrees_with_the_red_rows_of_the_committed_documents() -> None:
    """Review M1: the page said that no light is red by contract, and 112 of 522 rows are red."""
    docs = {v: committed(v) for v in VARIANTS}
    red: dict[str, int] = {}
    for d in docs.values():
        for r in d["tests"]:
            red[r["test_id"]] = red.get(r["test_id"], 0) + (r["light"] == "red")
    block = page.block_of(PAGE.read_text(encoding="utf-8"))
    sentence = next(line for line in block.splitlines() if line.startswith("An amber light"))
    assert "none is red by contract" not in block
    assert sum(red.values()) == 112 and {t for t, n in red.items() if n} == {"fair.two_proportion_z", "fair.fisher_exact"}
    for test_id, n in red.items():
        name = test_id.removeprefix("fair.")
        assert (name in sentence.split("never red by contract")[0]) == bool(n), (name, sentence)
    assert "red below the 0.01 p-value convention" in sentence and "112 of 522 rows" in sentence
    assert "the other tests are never red by contract" in sentence and "none is a finding of a violation" in sentence


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
    fit_last = docs[VARIANTS[-1]]["outputs"]["fit_year"]      # the rates of a pair are those of its fit year (review M2: 2023, not 2024)
    assert f"at {b5 * 100:.1f} against {w5 * 100:.1f} percent in {fit_last} ({r5:.3f})" in brief and fit_last == 2023
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
    # review M3: the 61 contrasts point both ways, so the proof point says how many sit below 1 and how many above, and leads with the
    # Black against White comparison, whose unconditional and controlled odds ratios agree
    kept = [c for c in contrasts if c["controlled"]["estimate"]["ci"]["lo"] > 0 or c["controlled"]["estimate"]["ci"]["hi"] < 0]
    below = sum(1 for c in kept if c["controlled"]["estimate"]["odds_ratio"] < 1)
    above = len(kept) - below
    assert (below, above) == (37, 24) and f"{below} with an odds ratio below 1 and {above} above 1" in brief
    assert "Most of the gap survives" not in brief and "For Black applicants the gap survives the permitted controls" in brief
    fisher = [black_white(v)[3]["fisher_exact"]["odds_ratio"] for v in VARIANTS]
    assert f"unconditional odds ratio {min(fisher):.2f} to {max(fisher):.2f}" in brief
    small = ("American Indian or Alaska Native", "Native Hawaiian or Other Pacific Islander", "2 or more minority races")
    years = [sum(r["flag"] for v in VARIANTS for a in docs[v]["outputs"]["attributes"] if a["field"] == "derived_race"
                 for r in a["four_fifths"]["groups"] if r["group"] == g) for g in small]
    assert min(years) >= 4 and "flags rarely" not in brief                                      # review m1: 17 of 30 non-White group-years
    assert f"flags the three small race groups in {years[0]}, {years[1]} and {years[2]} of the 6 years" in brief
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
