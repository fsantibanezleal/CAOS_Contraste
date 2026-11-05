"""The BS-14 tables of ``docs/cases/C04.md``, generated from the committed documents.

``python data-pipeline/pipeline/cases/c04_page.py`` rewrites the block between the two markers of the case page
from ``data/derived/C04``; the test compares the page's block with ``bounds_block`` so the page cannot drift from the
documents.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

MARK_START = "<!-- c04-bounds:start -->"
MARK_END = "<!-- c04-bounds:end -->"
DESIGNS = (("first_year", "first-year cohort"), ("pooled", "five cohorts pooled"), ("capture70", "second source counts 70%"),
           ("first_year_x10", "ten times the cohort"))
TREATMENTS = (("industry", "removed (k 1)"), ("unfollowed", "kept (k 0)"), ("followed", "followed (oracle)"),
              ("anchored", "anchored"), ("identified", "identified band"))
AGENCIES = (("sp", "S&P"), ("fitch", "Fitch"))


def _doc(derived: Path, name: str) -> dict:
    return json.loads((derived / "C04" / f"{name}.json").read_text(encoding="utf-8"))


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.1%}"


def _num(x: float | None, digits: int = 3) -> str:
    return "n/a" if x is None else f"{x:.{digits}g}"


def bounds_block(derived: Path) -> str:
    """Three tables: coverage of the true PD of B by design, treatment and k; the plan's criteria with their verdict;
    the anchored k of the real cohorts per agency and grade."""
    w = _doc(derived, "withdrawals")["outputs"]
    v = w["bounds_verdict"]
    g = v["grade"]
    rungs = w["rungs"]
    ks = [r["value"] for r in rungs]
    head = "| Design | Treatment | " + " | ".join(f"k {k:g}" for k in ks) + " |"
    lines = [head, "|" + "---|" * (2 + len(ks))]
    for did, dname in DESIGNS:
        for tid, tname in TREATMENTS:
            cells = []
            for r in rungs:
                d = next(x for x in r["bounds"]["designs"] if x["id"] == did)
                tr = next(x for x in d["treatments"] if x["id"] == tid)
                cells.append(_pct(tr["coverage"][g]["rate"]))
            lines.append(f"| {dname} | {tname} | " + " | ".join(cells) + " |")
    lines += ["", "| Criterion | Design | k | Treatment | Coverage (MC SE) | Threshold | Holds |", "|---|---|---|---|---|---|---|"]
    dname = dict(DESIGNS)
    tname = dict(TREATMENTS)
    for row in v["rows"]:
        lines.append(f"| {row['id']} | {dname[row['design']]} | {row['informative']:g} | {tname[row['treatment']]} | "
                     f"{row['value']:.1%} ({row['mcse']:.1%}) | {row['comparison'].replace('_', ' ')} {row['threshold']:.1%} | "
                     f"{'yes' if row['holds'] else 'no'} |")
    lines += ["", "| Agency | Grade | Pooled anchored k (band) | Cohorts whose band holds the pooled k | Stable at 80% | Tipping k to the next grade |",
              "|---|---|---|---|---|---|"]
    for code, name in AGENCIES:
        wb = _doc(derived, code)["outputs"]["withdrawal_bounds"]
        for gr in wb["grades"]:
            if gr["pooled"] is None:
                continue
            p, st, tip = gr["pooled"], gr["stability"], gr["tipping"]
            band = f"{_num(p['k'])} ({_num(p['k_low'])} to {_num(p['k_high'])})"
            hold = f"{st['cohorts_containing_pooled_k']} of {st['usable_cohorts']}"
            tipping = "n/a" if tip is None else f"{_num(tip['k'])} ({tip['status'].replace('_', ' ')}, to {tip['next_grade']})"
            lines.append(f"| {name} | {gr['grade']} | {band} | {hold} | {'yes' if st['stable'] else 'no'} | {tipping} |")
    s = v["summary"]
    lines += ["", f"Summary on {['AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC-C'][g]} ({v['reps']} repetitions per design and k): anchored covers at "
              f"least 90% everywhere: {'yes' if s['anchored_covers_90'] else 'no'}; every existing treatment under 50% at k 9: "
              f"{'yes' if s['existing_under_50'] else 'no'}; refuted on coverage: {'yes' if s['refuted'] else 'no'}."]
    return "\n".join(lines) + "\n"


def write(page: Path, derived: Path) -> bool:
    """Rewrite the block of ``page``; True when it changed."""
    text = page.read_text(encoding="utf-8")
    a, b = text.index(MARK_START) + len(MARK_START), text.index(MARK_END)
    new = text[:a] + "\n" + bounds_block(derived) + text[b:]
    if new != text:
        page.write_text(new, encoding="utf-8")
    return new != text


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    changed = write(root / "docs" / "cases" / "C04.md", root / "data" / "derived")
    print("docs/cases/C04.md: block rewritten" if changed else "docs/cases/C04.md: block current")
    sys.exit(0)
