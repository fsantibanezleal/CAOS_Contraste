"""The result tables of ``docs/cases/C03.md``, generated from the committed documents (CT-812), and the claims checks.

``python data-pipeline/pipeline/cases/c03/page.py`` rewrites the block between the two markers of the case page from
``data/derived/C03``; the test compares the page's block with ``results_block`` so the page cannot drift from the documents.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

MARK_START = "<!-- c03-results:start -->"
MARK_END = "<!-- c03-results:end -->"
NEGATION = re.compile(r"\b(not|no|never|without|cannot|isn't|none)\b", re.IGNORECASE)
BANK_CLAIM = re.compile(r"bank-wide|bank-level|a bank's (sme|portfolio|book)|bank portfolio", re.IGNORECASE)
WINDOW = re.compile(r"FY(\d{4}) to FY(\d{4})")
REQUIRED = (("sba 7(a)", "does not name the SBA 7(a) data"), ("small-business", "does not say the loans are small-business loans"),
            ("right-censor", "does not state the right-censoring of the active loans"),
            ("not a bank", "does not say the loans are not a bank's SME book"))


def claim_findings(text: str) -> list[str]:
    """A line that claims a bank-wide or bank-portfolio result must deny it; the page must name the data, say they are
    small-business loans, state the censoring and say the loans are not a bank's SME book."""
    out = []
    for n, line in enumerate(text.splitlines(), start=1):
        if BANK_CLAIM.search(line) and not NEGATION.search(line):
            out.append(f"line {n}: claims a bank result without denying it: {line.strip()[:80]}")
    low = text.lower()
    out += [f"the page {msg}" for needle, msg in REQUIRED if needle not in low]
    return out


def _models(derived: Path) -> dict:
    return json.loads((derived / "C03" / "models-sba-7a.json").read_text(encoding="utf-8"))


def window_findings(text: str, derived: Path) -> list[str]:
    """Every training window the page states (``FYa to FYb``) must be the window of a cohort in the documents."""
    allowed = {(w["training"]["first_fy"], w["training"]["last_fy"]) for w in _models(derived)["fit"]["cohort_windows"]}
    return [f"the page states the window FY{a} to FY{b}, which no document holds"
            for a, b in sorted({(int(a), int(b)) for a, b in WINDOW.findall(text)}) if (a, b) not in allowed]


def _variants(derived: Path) -> list[dict]:
    manifest = json.loads((derived / "manifests" / "C03.json").read_text(encoding="utf-8"))
    return [json.loads((derived / a["path"]).read_text(encoding="utf-8")) for a in manifest["artifacts"] if a["role"] == "variant"]


def _pct(x: float | None, nd: int = 1) -> str:
    return "n/a" if x is None else f"{100 * x:.{nd}f}%"


def results_block(derived: Path) -> str:
    docs = _variants(derived)
    head = ("| Test cohort | Training window | Crisis in training | Training 5-year rate | Observed 5-year PD | Predicted 5-year PD (scorecard) | "
            "Gap (points) | Scorecard AUC | Level test (Jeffreys) |\n|---|---|---|---|---|---|---|---|---|")
    body = []
    for d in docs:
        o = d["outputs"]
        tr, imp = o["training"], d["impact"]
        champ = next(r for r in o["rung_comparison"] if r["rung_id"] == o["calibration"]["rung_id"])
        jeff = next((t for t in d["tests"] if t["test_id"] == "pd.jeffreys" and t["model_id"] == champ["rung_id"] and t["segment"] == "portfolio"), None)
        gap = imp["calibration_gap_5y"]["value"]
        body.append(f"| {o['cohort']['label']['en']} | FY{tr['first_fy']} to FY{tr['last_fy']} | {'yes' if tr['crisis_included'] else 'no'} | "
                    f"{_pct(imp['training_event_rate']['value'])} | {_pct(imp['observed_5y_pd']['value'])} | {_pct(imp['predicted_5y_pd']['value'])} | "
                    f"{100 * gap:+.1f} | {champ['auc']:.3f} | {jeff['light'] if jeff else 'n/a'} |")
    ids = [r["rung_id"] for r in docs[0]["outputs"]["rung_comparison"]]
    rhead = "| Rung | " + " | ".join(d["outputs"]["cohort"]["label"]["en"] for d in docs) + " |\n|---|" + "---|" * len(docs)
    rbody = []
    for rid in ids:
        cells = []
        for d in docs:
            r = next(x for x in d["outputs"]["rung_comparison"] if x["rung_id"] == rid)
            cells.append("not fitted" if r["auc"] is None and r["reason"] else ("n/a" if r["auc"] is None else f"{r['auc']:.3f}"))
        rbody.append(f"| {rid} | " + " | ".join(cells) + " |")
    seq = [d["outputs"]["sequential"] for d in docs]
    shead = ("| Test cohort | Vintages that reject alone (first month) | Cohort by average (first month) | Cohort by product (first month) | "
             "Largest log E of the average |\n|---|---|---|---|---|")
    sbody = []
    for d, q in zip(docs, seq):
        alone = [f"FY{v['fiscal_year']} ({v['rejection_month']})" for v in q["vintages"] if v["rejection_month"] is not None]
        first = [("never" if q[k]["rejection_month"] is None else str(q[k]["rejection_month"])) for k in ("average", "product")]
        sbody.append(f"| {d['outputs']['cohort']['label']['en']} | {', '.join(alone) or 'none'} | {first[0]} | {first[1]} | "
                     f"{q['average']['max_log_e']:.1f} |")
    cap = (f"E-process of defaults against the predicted PD, read at every age (12 to 60 months; it rejects when log E reaches log "
           f"{seq[0]['threshold']:g} = {math.log(seq[0]['threshold']):.1f}):")
    return "\n".join([head, *body, "", "AUC of each rung on the pooled vintages of the cohort, at their 5-year marks:", "", rhead, *rbody,
                      "", cap, "", shead, *sbody]) + "\n"


def update(page: Path, derived: Path) -> None:
    text = page.read_text(encoding="utf-8")
    pre, rest = text.split(MARK_START, 1)
    _, post = rest.split(MARK_END, 1)
    page.write_text(f"{pre}{MARK_START}\n{results_block(derived)}{MARK_END}{post}", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[4]
    update(root / "docs" / "cases" / "C03.md", root / "data" / "derived")
    print("updated", root / "docs" / "cases" / "C03.md")
