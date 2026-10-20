"""CT-0213: the results block of docs/cases/C02.md is the one generated from the committed documents."""
from __future__ import annotations

from c02_support import MODELS, ROOT, VARIANTS, committed

from pipeline.cases.c02 import page

PAGE = ROOT / "docs" / "cases" / "C02.md"


def generated() -> str:
    return page.results_block({v: committed(v) for v in VARIANTS}, committed(MODELS)).strip("\n")


def test_the_case_page_results_block_is_generated_from_the_committed_documents() -> None:
    text = PAGE.read_text(encoding="utf-8")
    assert page.BEGIN in text and page.END in text
    assert page.block_of(text) == generated()
    for token in ("exploratory", "no out-of-time", "UNVERIFIED", "firm overlap", "convention", "6 - k", "undated"):
        assert token.lower() in text.lower(), token
    assert "## Executive brief" in text and text.index("## Executive brief") < text.index("## Data and what is real")
    docs = {v: committed(v) for v in VARIANTS}
    auc = {k: next(r for r in docs[f"h{k}"]["outputs"]["rungs"] if r["model_id"].endswith("P1-scorecard"))["discrimination"]["auc"] for k in range(1, 6)}
    brief = text.split("## Executive brief", 1)[1].split("## Why this case exists", 1)[0]
    assert all(f"{auc[k]:.3f}" in brief for k in range(1, 6))
    assert f"falls from {auc[1]:.3f} at 1 year to {auc[5]:.3f} at 5 years" in brief and all(auc[k] > auc[5] for k in range(1, 5))
    lgb = next(r for r in docs["h5"]["outputs"]["rungs"] if r["model_id"].endswith("P4-lightgbm"))["discrimination"]["auc"]
    assert f"LightGBM reaches {lgb:.3f} against {auc[5]:.3f}" in brief
    flags = {h: sum(r["overfit"]["flag"] for r in docs[h]["outputs"]["rungs"]) for h in ("h4", "h5")}
    assert flags == {"h4": 6, "h5": 6} and "6 of the 7 rungs on the 4-year and 5-year horizons" in brief
    for h in docs:       # a learned rung is supported over the scorecard in every document
        assert any(c["delong_p_value"] < 0.05 and c["auc_diff"] > 0 for c in docs[h]["outputs"]["challenger"]), h
        assert sum(r["calibration"]["hosmer_lemeshow"]["p_value"] < 0.01 for r in docs[h]["outputs"]["rungs"]) >= 2, h
    cells = [c["auc"] for c in docs["h5"]["outputs"]["transfer"]["cells"] if c["rung"] == "P1" and c["scored_on_years"] != 5]
    assert f"{min(cells):.3f} to {max(cells):.3f}" in brief
    # decisions G21 and G22 are stated with their source
    for token in ("5year.arff", "6 - k", "UCI page", "independent samples", "UNVERIFIED against Zieba, Tomczak and Tomczak 2016", "term_structure_reason"):
        assert token in text, token
    assert "F-HORIZON-MAPPING" not in text
