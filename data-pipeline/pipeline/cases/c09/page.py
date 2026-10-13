"""The result table of ``docs/cases/C09.md``, generated from the committed documents (CT-913), and the claims check.

``python data-pipeline/pipeline/cases/c09/page.py`` rewrites the block between the two markers of the case page from
``data/derived/C09``; the test compares the page's block with ``results_block`` so the page cannot drift from the documents.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

MARK_START = "<!-- c09-results:start -->"
MARK_END = "<!-- c09-results:end -->"
NEGATION = re.compile(r"\b(not|no|never|without|hypothetical|synthetic|neither|nor)\b", re.IGNORECASE)
REAL = re.compile(r"\breal\b.*\b(cards?|banks?|portfolios?|accounts?|lines?|issuers?)\b|\b(cards?|banks?|portfolios?|accounts?|lines?)\b.*\breal\b",
                  re.IGNORECASE)


def claim_findings(text: str) -> list[str]:
    """A line that calls the generated lines real must also deny it; a page that never says synthetic, or never names the Federal
    Reserve files the marginals follow, is a finding."""
    out = []
    for n, line in enumerate(text.splitlines(), start=1):
        if REAL.search(line) and not NEGATION.search(line):
            out.append(f"line {n}: calls the generated lines real without denying it: {line.strip()[:80]}")
    low = text.lower()
    if "synthetic" not in low:
        out.append("the page does not say the data are synthetic")
    if "federal reserve" not in low:
        out.append("the page does not name the Federal Reserve files")
    return out


def _docs(derived: Path) -> list[dict]:
    manifest = json.loads((derived / "manifests" / "C09.json").read_text(encoding="utf-8"))
    return [json.loads((derived / a["path"]).read_text(encoding="utf-8")) for a in manifest["artifacts"] if a["role"] == "variant"]


def _row(out: dict, design: str, treatment: str, agg: str) -> dict:
    return next(r for r in out["ccf_by_design"]["rows"] if (r["design"], r["treatment"], r["estimator"]) == (design, treatment, agg))


def _gap(out: dict, model: str) -> float:
    return max(abs(r["relative_gap"]) for r in out["ead_backtest"]["rows"] if r["model_id"] == model)


def results_block(derived: Path) -> str:
    head = ("| Level | Acceleration | Known CCF | Fixed-horizon mean (bias) | Fixed-horizon pooled (bias) | Cohort pooled (bias) | "
            "Variable-horizon pooled (bias) | Fixed-horizon floor-cap mean (bias) | Lines with no CCF | Worst band EAD gap, CCF at 12 months | "
            "Worst band EAD gap, direct EAD |")
    lines = [head, "|" + "---|" * 11]
    for doc in _docs(derived):
        o = doc["outputs"]
        g = o["generator"]
        fx, fp = _row(o, "fixed-horizon", "none", "mean"), _row(o, "fixed-horizon", "none", "pooled")
        co, va = _row(o, "cohort", "none", "pooled"), _row(o, "variable-horizon", "none", "pooled")
        fc = _row(o, "fixed-horizon", "floor-cap", "mean")
        n_def = o["replications"]["test"]["n_defaults"]
        n_def_fixed = fx["n_defaults"]
        acc = "none" if g["acceleration_window_months"] == 0 else f"x{g['acceleration_factor']:g} in the last {g['acceleration_window_months']} months"

        def cell(r: dict) -> str:
            return f"{r['estimate']['value']:.3f} ({r['bias']:+.3f})"

        lines.append(f"| {o['level']} | {acc} | {g['true_ccf']['value']:.3f} | {cell(fx)} | {cell(fp)} | {cell(co)} | {cell(va)} | {cell(fc)} | "
                     f"{1 - n_def_fixed / n_def:.1%} | {_gap(o, 'ccf-fixed-horizon-floor-cap'):.1%} | {_gap(o, 'direct-ead'):.1%} |")
    return "\n".join(lines) + "\n"


def write(page_path: Path, derived: Path) -> None:
    text = page_path.read_text(encoding="utf-8")
    head, rest = text.split(MARK_START, 1)
    tail = rest.split(MARK_END, 1)[1]
    page_path.write_text(f"{head}{MARK_START}\n{results_block(derived)}{MARK_END}{tail}", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[4]
    write(root / "docs" / "cases" / "C09.md", root / "data" / "derived")
    print("docs/cases/C09.md: results block written")
