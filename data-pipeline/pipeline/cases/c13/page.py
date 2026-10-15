"""The result table of ``docs/cases/C13.md``, generated from the committed documents (CT-1313), and the claims check.

``python data-pipeline/pipeline/cases/c13/page.py`` rewrites the block between the two markers of the case page from
``data/derived/C13``; the test compares the page's block with ``results_block`` so the page cannot drift from the documents.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

MARK_START = "<!-- c13-results:start -->"
MARK_END = "<!-- c13-results:end -->"
NEGATION = re.compile(r"\b(not|no|never|without|hypothetical|synthetic|neither|nor)\b", re.IGNORECASE)
REAL = re.compile(r"\breal\b.*\b(desks?|books?|banks?|portfolios?|traders?)\b|\b(desks?|books?|banks?|portfolios?)\b.*\breal\b", re.IGNORECASE)


def claim_findings(text: str) -> list[str]:
    """A line that calls the generated desk real must also deny it; a page that never says synthetic is a finding."""
    out = []
    for n, line in enumerate(text.splitlines(), start=1):
        if REAL.search(line) and not NEGATION.search(line):
            out.append(f"line {n}: calls the generated desk real without denying it: {line.strip()[:80]}")
    if "synthetic" not in text.lower():
        out.append("the page does not say the data are synthetic")
    return out


def _docs(derived: Path) -> list[dict]:
    manifest = json.loads((derived / "manifests" / "C13.json").read_text(encoding="utf-8"))
    return [json.loads((derived / a["path"]).read_text(encoding="utf-8")) for a in manifest["artifacts"] if a["role"] == "variant"]


def _param(k: dict) -> str:
    return "none" if not k["parameters"] else ", ".join(f"{p['name']} {p['value']:g} {p['unit']}" for p in k["parameters"])


def results_block(derived: Path) -> str:
    head = ("| Variant | Planted parameter | Meant to break | PLA amber or red (95% interval) | PLA red | Spearman flags | KS flags | "
            "Mean Spearman | Mean KS | Desk over limit at 97.5% | Desk over limit at 99% |")
    lines = [head, "|" + "---|" * 11]
    for doc in _docs(derived):
        o = doc["outputs"]
        k, d, z = o["known_deficiency"], o["detection"], o["pla"]
        n = d["n_replications"]
        desk = {r["alpha"]: r for r in o["desk_backtest"]}
        lines.append(
            f"| {k['deficiency_id']} | {_param(k)} | {k['intended_to_fail']} | {d['share_amber_or_red']:.1%} ({d['ci_low']:.1%} to {d['ci_high']:.1%}) | "
            f"{d['share_red']:.1%} | {d['by_test']['spearman_flagged'] / n:.1%} | {d['by_test']['ks_flagged'] / n:.1%} | "
            f"{z['spearman']['mean']:.3f} | {z['ks']['mean']:.3f} | {desk[0.025]['share_over_limit']:.1%} | {desk[0.01]['share_over_limit']:.1%} |")
    return "\n".join(lines) + "\n"


def write(page_path: Path, derived: Path) -> None:
    text = page_path.read_text(encoding="utf-8")
    head, rest = text.split(MARK_START, 1)
    tail = rest.split(MARK_END, 1)[1]
    page_path.write_text(f"{head}{MARK_START}\n{results_block(derived)}{MARK_END}{tail}", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[4]
    write(root / "docs" / "cases" / "C13.md", root / "data" / "derived")
    print("docs/cases/C13.md: results block written")
