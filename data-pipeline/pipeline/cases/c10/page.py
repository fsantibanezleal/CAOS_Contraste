"""The result tables of ``docs/cases/C10.md``, generated from the committed documents (CT-1112), and the claims check.

``python data-pipeline/pipeline/cases/c10/page.py`` rewrites the block between the two markers of the case page from
``data/derived/C10``; the test compares the page's block with ``results_block`` so the page cannot drift from the documents.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

MARK_START = "<!-- c10-results:start -->"
MARK_END = "<!-- c10-results:end -->"
NEGATION = re.compile(r"\b(not|no|never|without|illustrative|constructed|neither|nor)\b", re.IGNORECASE)
BANK = re.compile(r"\b(a|the|any)\s+bank'?s?\s+(own\s+|real\s+|actual\s+)?(portfolio|book|loans?)\b", re.IGNORECASE)
LOAN_TYPES = ("commercial-industrial", "commercial-real-estate", "residential", "credit-cards", "other-consumer")
RUNG_COLUMNS = (("c1-lhp", "C1 LHP"), ("c2-gaussian-1f", "C2 Gaussian 1F"), ("c2-gaussian-mf", "C2 Gaussian MF"),
                ("c3-student-t", "C3 Student-t"), ("c4-creditrisk-plus", "C4 CreditRisk+"), ("c5-granularity", "C5 LHP + GA"),
                ("c6-is-gaussian", "C6 importance"))


def claim_findings(text: str) -> list[str]:
    """A line that calls the portfolio a bank's must deny it; the page must say illustrative, name the Federal Reserve and name
    the LHP and the IRB form as approximations."""
    out = []
    for n, line in enumerate(text.splitlines(), start=1):
        if BANK.search(line) and not NEGATION.search(line):
            out.append(f"line {n}: calls the portfolio a bank's without denying it: {line.strip()[:80]}")
    low = text.lower()
    for need in ("illustrative", "federal reserve", "approximation", "known correlation"):
        if need not in low:
            out.append(f"the page does not say {need!r}")
    return out


def _doc(derived: Path, vid: str) -> dict:
    return json.loads((derived / "C10" / f"{vid}.json").read_text(encoding="utf-8"))


def _m(rung: dict, level: float) -> dict:
    return next(m for m in rung["measures"] if m["level"] == level)


def _musd(x: float) -> str:
    return f"{x / 1e6:.2f}"


def results_block(derived: Path) -> str:
    fit_head = ("| Loan type | Years in the fit | PD (ML) | Correlation (ML) | 95% interval | Correlation (moments) | IRB correlation | "
                "Fitted LHP capital / IRB | 2007-2012 years above the fitted 99% quantile | Upper binomial p-value |")
    lad_head = "| Loan type | EL | " + " | ".join(name for _, name in RUNG_COLUMNS) + " |"
    es_head = "| Loan type | C1 ES | C2 Gaussian 1F ES | C3 Student-t ES | C4 CreditRisk+ ES | GA (share of EAD) | GA / LHP VaR | Effective names | Largest group share of the Gaussian 1F VaR |"
    fit_rows, lad_rows, es_rows = [], [], []
    for vid in LOAN_TYPES:
        o = _doc(derived, vid)["outputs"]
        ml, mo = o["fit"]["maximum_likelihood"], o["fit"]["moments"]
        bt = next(r for r in o["backtest"]["rows"] if r["level"] == 0.99)
        years = ", ".join(map(str, bt["years_exceeding"])) or "none"
        i = o["irb_reference"]
        fit_rows.append(f"| {o['label']['en']} | {o['fit']['n_years_used']} | {ml['pd']['estimate']:.4f} | {ml['rho']['estimate']:.3f} | "
                        f"{ml['rho']['ci_low']:.3f} to {ml['rho']['ci_high']:.3f} | {mo['rho']['estimate']:.3f} | {i['irb_correlation']:.3f} | "
                        f"{i['ratio_fitted_to_irb']:.2f} | {bt['observed_exceedances']} of {o['backtest']['n_years_evaluated']} ({years}) | "
                        f"{bt['p_value_upper']:.4f} |")
        by = {r["id"]: r for r in o["rungs"]}
        lad_rows.append(f"| {o['label']['en']} | {_musd(_m(by['c1-lhp'], 0.999)['el'])} | " +
                        " | ".join(_musd(_m(by[rid], 0.999)["var"]) for rid, _ in RUNG_COLUMNS) + " |")
        g = next(x for x in o["granularity"]["levels"] if x["q"] == 0.999)
        c1v = _m(by["c1-lhp"], 0.999)["var"]
        e1 = o["euler"][0]["levels"][1]
        big = max(e1["rows"], key=lambda r: r["share_var"])
        es_rows.append(f"| {o['label']['en']} | {_musd(_m(by['c1-lhp'], 0.999)['es'])} | {_musd(_m(by['c2-gaussian-1f'], 0.999)['es'])} | "
                       f"{_musd(_m(by['c3-student-t'], 0.999)['es'])} | {_musd(_m(by['c4-creditrisk-plus'], 0.999)['es'])} | "
                       f"{100 * g['ga']:.3f}% | {g['ga_money'] / c1v:.1%} | {o['portfolio']['effective_names']:.0f} | "
                       f"{big['group_id']} {big['share_var']:.0%} |")
    sim_head = ("| Known correlation | Role | Mean ML estimate (22 y) | ML rejection rate (22 y) | Moments rejection rate (22 y) | "
                "Mean ML estimate (40 y) | ML rejection rate (40 y) | Moments rejection rate (40 y) |")
    g22, g40 = _doc(derived, "grid-22")["outputs"]["cells"], _doc(derived, "grid-40")["outputs"]["cells"]
    sim_rows = []
    for a, b in zip(g22, g40, strict=True):
        ma, mb = a["estimators"], b["estimators"]
        sim_rows.append(f"| {a['known_rho']:.2f} | {a['role']} | {ma[0]['mean_estimate']:.3f} | {ma[0]['rejection_rate']:.3f} | "
                        f"{ma[1]['rejection_rate']:.3f} | {mb[0]['mean_estimate']:.3f} | {mb[0]['rejection_rate']:.3f} | "
                        f"{mb[1]['rejection_rate']:.3f} |")
    sep = lambda n: "|" + "---|" * n  # noqa: E731
    return "\n".join([
        "**The fit and the 2007-2012 tail** (rates are decimals per year; the fit window is 1985-2006)", "", fit_head, sep(10), *fit_rows, "",
        "**VaR at 99.9% of the illustrative portfolio by rung** (millions of USD; exposure 100 million)", "", lad_head,
        sep(len(RUNG_COLUMNS) + 2), *lad_rows, "",
        "**Expected shortfall at 99.9%, the granularity adjustment and the concentration**", "", es_head, sep(9), *es_rows, "",
        "**Size and power of the correlation estimates on the simulator with a known correlation** (H0: rho = 0.12 at the 5% level; "
        f"{g22[0]['n_replications']} replications per cell)", "", sim_head, sep(8), *sim_rows]) + "\n"


def write(page_path: Path, derived: Path) -> None:
    text = page_path.read_text(encoding="utf-8")
    head, rest = text.split(MARK_START, 1)
    tail = rest.split(MARK_END, 1)[1]
    page_path.write_text(f"{head}{MARK_START}\n{results_block(derived)}{MARK_END}{tail}", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[4]
    write(root / "docs" / "cases" / "C10.md", root / "data" / "derived")
    print("docs/cases/C10.md: results block written")
