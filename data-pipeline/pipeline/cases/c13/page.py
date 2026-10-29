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
COMPLEMENT_START = "<!-- c13-complement:start -->"
COMPLEMENT_END = "<!-- c13-complement:end -->"
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


def _r(r: dict) -> str:
    return f"{r['rate']:.1%} ({r['k']}/{r['n']})"


def complement_block(derived: Path) -> str:
    """The BS-13 tables of the page (the complement per variant, the lag ladder, the power by size) and the plan's verdict, all from the documents."""
    docs = _docs(derived)
    head = ("| Variant | Regulatory PLA, amber or red | Wald, 1% | Abs. Spearman, 1% | Rolling Spearman, 1% | Any of the three, 1% each | "
            "Any, 1% for the union | Union or PLA | Wald against KS alone |")
    lines = [head, "|" + "---|" * 9]
    for doc in docs:
        o = doc["outputs"]
        c = o["pla_complement"]
        f = c["flags"]
        ks = c["against_ks"]
        lines.append(f"| {o['known_deficiency']['deficiency_id']} | {_r(f['pla_amber_or_red'])} | {_r(f['per_statistic']['wald'])} | "
                     f"{_r(f['per_statistic']['spearman_abs'])} | {_r(f['per_statistic']['spearman_roll'])} | {_r(f['per_statistic']['any'])} | "
                     f"{_r(f['family']['any'])} | {_r(f['family_with_pla'])} | "
                     f"{'n/a' if ks is None else str(ks['wald_flagged']) + ' against ' + str(ks['ks_flagged'])} |")
    stale = next(d for d in docs if d["outputs"]["known_deficiency"]["deficiency_id"] == "stale-volatility")["outputs"]["pla_complement"]
    lines += ["", "| Lag (days) | Regulatory PLA | Wald, 1% | Abs. Spearman, 1% | Rolling Spearman, 1% | Any, 1% for the union |", "|" + "---|" * 6]
    for r in stale["lag_ladder"]:
        ps = r["per_statistic"]
        lines.append(f"| {r['lag_days']} | {_r(r['pla_amber_or_red'])} | {_r(ps['wald'])} | {_r(ps['spearman_abs'])} | {_r(ps['spearman_roll'])} | "
                     f"{_r(r['family_any'])} |")
    lines += ["", "| Size per statistic | Rolling Spearman power | Rolling Spearman false alarms | Wald power | Wald false alarms |", "|" + "---|" * 5]
    for r in stale["by_size"]:
        lines.append(f"| {r['size']:.1%} | {r['spearman_roll']['rate']:.1%} | {r['spearman_roll_held_out']['rate']:.1%} | "
                     f"{r['wald']['rate']:.1%} | {r['wald_held_out']['rate']:.1%} |")
    h = stale["hypothesis"]
    lines += ["", f"Verdict of the plan's hypothesis (`{h['verdict']}`): {h['reading']['en']}"]
    return "\n".join(lines) + "\n"


def write(page_path: Path, derived: Path) -> None:
    text = page_path.read_text(encoding="utf-8")
    head, rest = text.split(MARK_START, 1)
    _, rest = rest.split(MARK_END, 1)
    between, rest = rest.split(COMPLEMENT_START, 1)
    tail = rest.split(COMPLEMENT_END, 1)[1]
    page_path.write_text(
        f"{head}{MARK_START}\n{results_block(derived)}{MARK_END}{between}{COMPLEMENT_START}\n{complement_block(derived)}{COMPLEMENT_END}{tail}",
        encoding="utf-8", newline="\n")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[4]
    write(root / "docs" / "cases" / "C13.md", root / "data" / "derived")
    print("docs/cases/C13.md: results block written")
