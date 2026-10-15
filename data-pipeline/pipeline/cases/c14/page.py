"""The generated results block of docs/cases/C14.md: every figure is read from the committed documents, never typed.

``results_block`` renders the block between ``BEGIN`` and ``END``; ``write_page`` replaces the block in the page and a test compares
the committed block with a fresh render (CT-1414).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

BEGIN = "<!-- c14-results:begin -->"
END = "<!-- c14-results:end -->"
SHOCKS = ("parallel-up", "parallel-down", "steepener", "flattener", "short-up", "short-down")


def m(x: float) -> str:
    """USD thousands as USD million with one decimal."""
    return f"{x / 1000.0:,.1f}"


def pct(x: float) -> str:
    return f"{x * 100:.1f}"


def _sc(out: dict[str, Any], cal: str, assumption: str) -> dict[str, Any]:
    return next(s for s in out["scenarios"] if s["calibration"] == cal and s["nmd_assumption"] == assumption)


def results_block(variants: dict[str, dict[str, Any]], models: dict[str, Any]) -> str:
    lines: list[str] = []
    w = lines.append
    ids = sorted(variants)
    w("### The outlier test")
    w("")
    w("The EVE risk measure is the largest positive delta EVE of the six shocks (USD million); the test compares it with 15 percent of Tier 1. "
      "Behavioural is the standardised treatment with the SRP31 Table 4 caps; contractual puts every non-maturity deposit overnight.")
    w("")
    w("| Date | Tier 1 | Calibration | Behavioural measure | Share of Tier 1 | Breached | Contractual measure | Share of Tier 1 | Breached |")
    w("|---|---:|---|---:|---:|---|---:|---:|---|")
    for vid in ids:
        o = variants[vid]["outputs"]
        for cal in ("2024", "2016"):
            b, c = _sc(o, cal, "behavioural"), _sc(o, cal, "contractual")
            w(f"| {o['valuation_date']} | {m(b['outlier']['tier1'])} | {cal} | {m(b['eve_risk_measure'])} | {pct(b['outlier']['ratio'])} percent | "
              f"{'yes' if b['outlier']['breached'] else 'no'} | {m(c['eve_risk_measure'])} | {pct(c['outlier']['ratio'])} percent | "
              f"{'yes' if c['outlier']['breached'] else 'no'} |")
    w("")
    w("### Delta EVE by shock, 2024 calibration (USD million, positive is a loss)")
    w("")
    w("| Date | NMD | " + " | ".join(SHOCKS) + " |")
    w("|---|---|" + "---:|" * 6)
    for vid in ids:
        o = variants[vid]["outputs"]
        for a in ("behavioural", "contractual"):
            w(f"| {o['valuation_date']} | {a} | " + " | ".join(m(x["delta_eve"]) for x in _sc(o, "2024", a)["shocks"]) + " |")
    w("")
    w("### Delta NII under the parallel shocks and the gap approximation (USD million, positive is a loss)")
    w("")
    w("| Date | NMD | Parallel up | Parallel down | Gap approximation, +100 bp | Duration gap (years) |")
    w("|---|---|---:|---:|---:|---:|")
    for vid in ids:
        o = variants[vid]["outputs"]
        for a, lad in zip(("behavioural", "contractual"), o["ladder"]):
            sh = _sc(o, "2024", a)["shocks"]
            w(f"| {o['valuation_date']} | {a} | {m(sh[0]['delta_nii'])} | {m(sh[1]['delta_nii'])} | {m(lad['delta_nii_gap_100bp_up'])} | "
              f"{lad['duration_gap']['duration_gap_years']:.2f} |")
    w("")
    w("### Dynamic NII, EaR and EVaR (12 months, USD million)")
    w("")
    w("| Date | Base NII | NII, +200 bp | NII, -200 bp | EaR 95 | EaR 99 (error) | EVaR 95 | EVaR 99 (error) | Paths | Seed |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for vid in ids:
        o = variants[vid]["outputs"]
        d, e = o["dynamic_nii"]["scenarios"], o["ear_evar"]
        l95, l99 = e["levels"]
        w(f"| {o['valuation_date']} | {m(d[0]['total'])} | {m(d[1]['total'])} | {m(d[2]['total'])} | {m(l95['ear'])} | {m(l99['ear'])} "
          f"({m(l99['ear_se'])}) | {m(l95['evar'])} | {m(l99['evar'])} ({m(l99['evar_se'])}) | {e['n_paths']:,} | {e['seed']} |")
    w("")
    w("### Out-of-sample: the 2021-Q4 projection against the realised 2022")
    w("")
    first = variants[ids[0]]["outputs"]
    oos = first["out_of_sample"]
    if oos["applicable"]:
        w(f"The projected 12-month change of NII for the +{first['scenarios'][0]['shock_size']['parallel_bp']:.0f} bp parallel shock is "
          f"{m(oos['projected_delta_nii'])} USD million (positive is a loss); the realised change from 2021 to 2022, from the two year-end "
          f"call reports, is {m(oos['realised_delta_nii'])}; the relative error is {pct(oos['relative_error'])} percent.")
    else:
        w(oos["reason"]["en"])
    w("")
    w("### Deposit assumptions and their caps")
    w("")
    w("| Date | Category | Balance | Requested share | Used share | Requested maturity (years) | Used maturity (years) | Cap applied |")
    w("|---|---|---:|---:|---:|---:|---:|---|")
    for vid in ids:
        o = variants[vid]["outputs"]
        for s in o["nmd_segments"]:
            w(f"| {o['valuation_date']} | {s['category']} | {m(s['balance'])} | {s['requested_core_share']:.2f} | {s['core_share_used']:.2f} | "
              f"{s['requested_core_maturity_years']:.1f} | {s['core_maturity_used_years']:.1f} | {'yes' if s['cap_applied'] else 'no'} |")
    w("")
    w("### The fitted replicating portfolio and the deposit betas")
    w("")
    w("| Date | Weighted average maturity (years) | Margin volatility | Beta up | Beta down | Window |")
    w("|---|---:|---:|---:|---:|---|")
    for nm in models["fit"]["nmd_models"]:
        last = nm["stability"][-1]
        mv = "n/a" if nm["margin_volatility"] is None else f"{nm['margin_volatility'] * 100:.3f} percent"
        w(f"| {nm['valuation_date']} | {nm['weighted_average_maturity_years']:.2f} | {mv} | {nm['deposit_beta']['up']:.3f} | "
          f"{nm['deposit_beta']['down']:.3f} | {last['window_start']} to {last['window_end']} |")
    w("")
    w("### Validation tests")
    w("")
    w("| Date | Test | Light | Statistic |")
    w("|---|---|---|---:|")
    for vid in ids:
        v = variants[vid]
        for tr in v["tests"]:
            st = "n/a" if tr["statistic"] is None else f"{tr['statistic']:.4g}"
            w(f"| {v['outputs']['valuation_date']} | {tr['test_id']} | {tr['light']} | {st} |")
    return "\n".join(lines) + "\n"


def write_page(page: Path, variants: dict[str, dict[str, Any]], models: dict[str, Any]) -> None:
    text = page.read_text(encoding="utf-8")
    head, rest = text.split(BEGIN, 1)
    tail = rest.split(END, 1)[1]
    page.write_text(f"{head}{BEGIN}\n{results_block(variants, models)}{END}{tail}", encoding="utf-8", newline="\n")
