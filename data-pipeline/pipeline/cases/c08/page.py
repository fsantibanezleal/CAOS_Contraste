"""The result table of ``docs/cases/C08.md``, generated from the committed documents (CT-916), and the claims check.

``python data-pipeline/pipeline/cases/c08/page.py`` rewrites the block between the two markers of the case page from
``data/derived/C08``; the test compares the page's block with ``results_block`` so the page cannot drift from the documents.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

MARK_START = "<!-- c08-results:start -->"
MARK_END = "<!-- c08-results:end -->"
DOWN_START = "<!-- c08-downturn:start -->"
DOWN_END = "<!-- c08-downturn:end -->"
NEGATION = re.compile(r"\b(not|no|never|without|twin|missing|absent|cannot|isn't|none)\b", re.IGNORECASE)
REFERENCE = "L2-fractional-logit"


def claim_findings(text: str) -> list[str]:
    """A line that mentions mortgages or Freddie Mac must also deny a result or say the data is absent or a twin; a page
    that never names the SBA data is a finding."""
    out = []
    for n, line in enumerate(text.splitlines(), start=1):
        low = line.lower()
        if ("mortgage" in low or "freddie" in low) and not NEGATION.search(line):
            out.append(f"line {n}: names mortgages or Freddie Mac without saying they are absent or a twin: {line.strip()[:80]}")
    if "sba" not in text.lower():
        out.append("the page does not name the SBA data")
    return out


def _f(x, fmt):
    return "n/a" if x is None else format(x, fmt)


def _lines(derived: Path) -> list[dict]:
    manifest = json.loads((derived / "manifests" / "C08.json").read_text(encoding="utf-8"))
    rows = []
    for a in manifest["artifacts"]:
        if a["role"] != "variant":
            continue
        d = json.loads((derived / a["path"]).read_text(encoding="utf-8"))
        o = d["outputs"]
        dist = o["lgd_distribution"]
        cmp = {r["rung_id"]: r for r in o["rung_comparison"]}
        ref = cmp.get(REFERENCE)
        cal = next((t for t in d["tests"] if t["test_id"] == "lgd_ead.lgd_calibration_by_segment" and t["model_id"] == REFERENCE), None)
        best = min(o["rung_comparison"], key=lambda r: r["rmse"])
        rows.append({
            "cohort": o["cohort"]["id"], "cutoff": o["training"]["cutoff_date"], "train": o["training"]["n_defaults"], "n": dist["n"],
            "mean": dist["mean"]["value"], "median": dist["median"]["value"], "one": dist["mass_at_one"]["share"],
            "above": dist["share_above_one"], "pred": None if ref is None else next(
                r["predicted"]["value"] for r in o["realised_vs_predicted"] if r["rung_id"] == REFERENCE and r["cohort_id"] == o["cohort"]["id"]),
            "gap": None if ref is None else ref["calibration_gap"], "cal_light": cal["light"] if cal else "n/a",
            "rho": None if ref is None else ref["spearman"], "best": best["rung_id"], "best_rmse": best["rmse"],
            "n_fitted": len(o["rung_comparison"]),
        })
    return rows


def results_block(derived: Path) -> str:
    head = ("| Test cohort | Training cutoff | Training defaults | Cohort defaults | Mean LGD proxy | Median | Share at 1 | Share above 1 | "
            "L2 predicted mean | L2 gap (points) | L2 calibration | L2 rank correlation | Lowest RMSE | Rungs fitted |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    body = []
    for r in _lines(derived):
        body.append(f"| {r['cohort']} | {r['cutoff']} | {r['train']:,} | {r['n']:,} | {r['mean']:.3f} | {r['median']:.3f} | "
                    f"{100 * r['one']:.1f}% | {100 * r['above']:.1f}% | {_f(r['pred'], '.3f')} | "
                    f"{_f(None if r['gap'] is None else 100 * r['gap'], '.1f')} | {r['cal_light']} | {_f(r['rho'], '.3f')} | "
                    f"{r['best']} ({r['best_rmse']:.3f}) | {r['n_fitted']} of 6 |")
    return "\n".join([head, *body]) + "\n"


def downturn_block(derived: Path) -> str:
    manifest = json.loads((derived / "manifests" / "C08.json").read_text(encoding="utf-8"))
    first = next(a for a in manifest["artifacts"] if a["role"] == "variant")
    dn = json.loads((derived / first["path"]).read_text(encoding="utf-8"))["outputs"]["downturn"]
    head = "| Downturn cohort | Defaults | Long-run LGD proxy | Downturn LGD proxy | Add-on (points) | Realised in the cohort | Covered | Shortfall (points) |\n|---|---|---|---|---|---|---|---|"
    body = [f"| {r['cohort_id']} | {r['n']:,} | {r['long_run_lgd']['value']:.3f} | {r['downturn_lgd']['value']:.3f} | "
            f"{100 * r['add_on']:.1f} | {r['crisis_realised_lgd']['value']:.3f} | {'yes' if r['covered'] else 'no'} | {100 * r['shortfall']:.1f} |"
            for r in dn["rows"]]
    return "\n".join([head, *body]) + "\n"


def _swap(text: str, start: str, end: str, block: str) -> str:
    pre, rest = text.split(start, 1)
    _, post = rest.split(end, 1)
    return f"{pre}{start}\n{block}{end}{post}"


def update(page: Path, derived: Path) -> None:
    text = page.read_text(encoding="utf-8")
    text = _swap(text, MARK_START, MARK_END, results_block(derived))
    text = _swap(text, DOWN_START, DOWN_END, downturn_block(derived))
    page.write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[4]
    update(root / "docs" / "cases" / "C08.md", root / "data" / "derived")
    print("updated", root / "docs" / "cases" / "C08.md")
