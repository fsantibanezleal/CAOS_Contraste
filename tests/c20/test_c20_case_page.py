"""CT-2019: the results block of docs/cases/C20.md is the one generated from the committed documents."""
from __future__ import annotations

from c20_support import MODELS, PROHIBITED, ROOT, VARIANTS, committed

from pipeline.cases.c20 import page

PAGE = ROOT / "docs" / "cases" / "C20.md"


def generated() -> str:
    return page.results_block({v: committed(v) for v in VARIANTS}, committed(MODELS)).strip("\n")


def test_the_case_page_results_block_is_generated_from_the_committed_documents() -> None:
    text = PAGE.read_text(encoding="utf-8")
    assert page.BEGIN in text and page.END in text
    assert page.block_of(text) == generated()
    assert PROHIBITED in page.block_of(text) and "must not be used for real-world credit scoring" in text
    for token in ("convention", "estimate", "not a compliance statement", "locked holdout", "SGCD", "Federal Reserve", "synthetic"):
        assert token.lower() in text.lower(), token
    assert "## Executive brief" in text and text.index("## Executive brief") < text.index("## Data and what is real")
    assert "four-fifths" not in page.block_of(text).lower()


def test_the_executive_brief_carries_the_figures_of_the_documents() -> None:
    text = PAGE.read_text(encoding="utf-8")
    brief = text.split("## Executive brief", 1)[1].split("## Why this case exists", 1)[0]
    perturb = committed("perturbation-grid")["outputs"]["rows"]
    preset = next(r for r in perturb if r["eps"] == 0.1)
    assert f"{-preset['metric']['auc_delta']:.3f} AUC points at noise 0.1" in brief
    seeds = {r["rung"]: r for r in committed("seed-sweep")["outputs"]["rows"]}
    assert f"{seeds['P4-lightgbm']['reason_code_overlap']['mean']:.2f}" in brief
    leak = committed("leakage-planted")["outputs"]
    assert f"{leak['performance']['development_auc']:.4f}" in brief and f"{leak['performance']['decision_time_auc']:.3f}" in brief
    shift = committed("fed-shift")["outputs"]["synthetic_shift"]
    pooled = shift["label_free"]["conformal"]["coverage"]
    assert f"{pooled * 100:.1f} percent" in brief
