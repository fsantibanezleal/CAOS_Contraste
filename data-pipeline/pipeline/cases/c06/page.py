"""The result table of ``docs/cases/C06.md``, generated from the committed documents (CT-514), and the claims check.

``python data-pipeline/pipeline/cases/c06/page.py`` rewrites the block between the two markers of the case page from
``data/derived/C06``; the test compares the page's block with ``results_block`` so the page cannot drift from the documents.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

MARK_START = "<!-- c06-results:start -->"
MARK_END = "<!-- c06-results:end -->"
NEGATION = re.compile(r"\b(not|no|never|without|twin|missing|absent|cannot|isn't|none)\b", re.IGNORECASE)


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


def _lines(derived: Path) -> list[dict]:
    manifest = json.loads((derived / "manifests" / "C06.json").read_text(encoding="utf-8"))
    rows = []
    for a in manifest["artifacts"]:
        if a["role"] != "variant":
            continue
        d = json.loads((derived / a["path"]).read_text(encoding="utf-8"))
        o = d["outputs"]
        gca = sum(r["gross_carrying_amount"] for r in o["stage_summary"]["rows"])
        ecl = sum(r["ecl"] for r in o["stage_summary"]["rows"])
        s2 = next(r for r in o["stage_summary"]["rows"] if r["stage"] == "stage2")
        accounts = sum(r["accounts"] for r in o["stage_summary"]["rows"])
        t = {(x["test_id"], x["model_id"], x["segment"]): x for x in d["tests"]}
        ecl_bt = t.get(("ifrs9.ecl_backtest", "L1-dth", None))
        life = t.get(("ifrs9.lifetime_pd_backtest", "L1-dth", "all"))
        sicr = t.get(("ifrs9.sicr_effectiveness", "L1-dth", None))
        cmp = {r["rung_id"]: r for r in o["rung_comparison"]}
        rows.append({
            "date": o["reporting_date"], "accounts": accounts, "gca_bn": gca / 1e9, "s2": s2["gross_carrying_amount"] / gca if gca else 0.0,
            "ecl_m": ecl / 1e6, "cov": ecl / gca if gca else 0.0,
            "bt": None if ecl_bt is None or ecl_bt["metric"] is None else ecl_bt["metric"], "bt_light": ecl_bt["light"] if ecl_bt else "n/a",
            "gap": None if life is None else life["metric"], "gap_light": life["light"] if life else "n/a",
            "sicr": None if sicr is None or sicr["metric"] is None else sicr["metric"], "sicr_light": sicr["light"] if sicr else "n/a",
            "auc": cmp["L1-dth"]["c_index"], "nl": d["impact"]["nl_index"]["value"],
        })
    return rows


def _f(x, fmt):
    return "n/a" if x is None else format(x, fmt)


def results_block(derived: Path) -> str:
    head = ("| Reporting date | Accounts | Gross carrying amount (USD bn) | Stage 2 share | Model ECL (USD m) | Coverage | "
            "Realised 12-month losses over ECL | Largest lifetime PD gap (L1, points) | SICR default-rate ratio | L1 c-index | ECL non-linearity |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|")
    body = []
    for r in _lines(derived):
        body.append(f"| {r['date']} | {r['accounts']:,} | {r['gca_bn']:.1f} | {100 * r['s2']:.1f}% | {r['ecl_m']:,.0f} | {100 * r['cov']:.2f}% | "
                    f"{_f(r['bt'], '.2f')} ({r['bt_light']}) | {_f(None if r['gap'] is None else 100 * r['gap'], '.1f')} ({r['gap_light']}) | "
                    f"{_f(r['sicr'], '.2f')} ({r['sicr_light']}) | {_f(r['auc'], '.3f')} | {100 * r['nl']:.1f}% |")
    return "\n".join([head, *body]) + "\n"


def update(page: Path, derived: Path) -> None:
    text = page.read_text(encoding="utf-8")
    pre, rest = text.split(MARK_START, 1)
    _, post = rest.split(MARK_END, 1)
    page.write_text(f"{pre}{MARK_START}\n{results_block(derived)}{MARK_END}{post}", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[4]
    update(root / "docs" / "cases" / "C06.md", root / "data" / "derived")
    print("updated", root / "docs" / "cases" / "C06.md")
