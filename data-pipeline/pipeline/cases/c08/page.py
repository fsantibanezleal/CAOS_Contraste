"""The result table of ``docs/cases/C08.md``, generated from the committed documents (CT-916), and the claims check.

``python data-pipeline/pipeline/cases/c08/page.py`` rewrites the block between the two markers of the case page from
``data/derived/C08``; the test compares the page's block with ``results_block`` so the page cannot drift from the documents.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

try:
    from . import ml_benchmark as ml
except ImportError:  # run as a script: ``python data-pipeline/pipeline/cases/c08/page.py``
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ml_benchmark as ml  # type: ignore[no-redef]

MARK_START = "<!-- c08-results:start -->"
MARK_END = "<!-- c08-results:end -->"
DOWN_START = "<!-- c08-downturn:start -->"
DOWN_END = "<!-- c08-downturn:end -->"
ML_START = "<!-- c08-ml:start -->"
ML_END = "<!-- c08-ml:end -->"
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
                    f"{r['best']} ({r['best_rmse']:.3f}) | {r['n_fitted']} of 8 |")
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


def bucket_gap(rows: list[dict], rung_id: str) -> float | None:
    """The default-weighted mean absolute gap, in LGD points, between the predicted and the realised mean of the five calibration
    buckets of one rung (the out-of-time calibration by bucket of the plan's S-5 criterion)."""
    mine = [b for b in rows if b["rung_id"] == rung_id]
    if not mine:
        return None
    n = sum(b["n"] for b in mine)
    return 100.0 * sum(b["n"] * abs(b["realised"]["value"] - b["predicted"]["value"]) for b in mine) / n


def ml_rows(derived: Path) -> list[dict]:
    """One row per test cohort: the best of the six earlier rungs against the better of the two new ones, with their RMSE and the
    bucket gaps; read from the committed variant documents."""
    manifest = json.loads((derived / "manifests" / "C08.json").read_text(encoding="utf-8"))
    out = []
    for a in manifest["artifacts"]:
        if a["role"] != "variant":
            continue
        o = json.loads((derived / a["path"]).read_text(encoding="utf-8"))["outputs"]
        res = ml.cohort_result(o["rung_comparison"])
        rmse = {r["rung_id"]: r["rmse"] for r in o["rung_comparison"]}
        out.append({"cohort": o["cohort"]["id"], "train": o["training"]["n_defaults"], "n": o["lgd_distribution"]["n"], "res": res,
                    "rmse": rmse, "gap": {rid: bucket_gap(o["calibration_by_bucket"], rid)
                                          for rid in ("L5-gradient-boosted", *ml.ML_RUNGS)}})
    return out


def ml_verdict(derived: Path) -> dict:
    rows = ml_rows(derived)
    wins = sum(r["res"]["ml_wins"] for r in rows)
    return {"wins": int(wins), "cohorts": len(rows), "verdict": ml.verdict(wins, len(rows)),
            "train_min": min(r["train"] for r in rows), "train_max": max(r["train"] for r in rows),
            "test_total": sum(r["n"] for r in rows)}


def ml_block(derived: Path) -> str:
    head = ("| Test cohort | Best of L1 to L6 (RMSE) | L5 gradient boosting | L7 random forest | L8 neural network | Gain of the better of L7 and L8 "
            "(RMSE points) | L7 or L8 lower | Bucket gap L5 (points) | Bucket gap L7 | Bucket gap L8 |\n"
            "|---|---|---|---|---|---|---|---|---|---|")
    body = []
    for r in ml_rows(derived):
        c = r["res"]["classical"]
        body.append(f"| {r['cohort']} | {c[0]} ({c[1]:.4f}) | {r['rmse']['L5-gradient-boosted']:.4f} | {r['rmse']['L7-random-forest']:.4f} | "
                    f"{r['rmse']['L8-neural-network']:.4f} | {100 * r['res']['gain']:.3f} | {'yes' if r['res']['ml_wins'] else 'no'} | "
                    f"{r['gap']['L5-gradient-boosted']:.2f} | {r['gap']['L7-random-forest']:.2f} | {r['gap']['L8-neural-network']:.2f} |")
    v = ml_verdict(derived)
    verdict = (f"**Measured:** the better of the random forest and the neural network has the lower RMSE in {v['wins']} of {v['cohorts']} test "
               f"cohorts, trained on {v['train_min']:,} to {v['train_max']:,} defaults per cohort and tested on {v['test_total']:,} defaults "
               f"in all (seed 42, one thread). **Verdict: {v['verdict']}.**")
    return "\n".join([head, *body]) + "\n\n" + verdict + "\n"


def _swap(text: str, start: str, end: str, block: str) -> str:
    pre, rest = text.split(start, 1)
    _, post = rest.split(end, 1)
    return f"{pre}{start}\n{block}{end}{post}"


def update(page: Path, derived: Path) -> None:
    text = page.read_text(encoding="utf-8")
    text = _swap(text, MARK_START, MARK_END, results_block(derived))
    text = _swap(text, DOWN_START, DOWN_END, downturn_block(derived))
    text = _swap(text, ML_START, ML_END, ml_block(derived))
    page.write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[4]
    update(root / "docs" / "cases" / "C08.md", root / "data" / "derived")
    print("updated", root / "docs" / "cases" / "C08.md")
