"""The generated results block of docs/cases/C12.md: every figure is read from the committed documents, never typed.

``results_block`` renders the block between ``BEGIN`` and ``END``; ``write_page`` replaces the block in the page and a test compares
the committed block with a fresh render (CT-1219).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

BEGIN = "<!-- c12-results:begin -->"
END = "<!-- c12-results:end -->"
ORDER = ("single-swap", "netting-set", "csa-mpor-10d", "csa-mpor-20d", "with-im", "wrong-way-risk")
NAMES = {"single-swap": "Single swap", "netting-set": "Netting set", "csa-mpor-10d": "CSA, MPoR 10 days", "csa-mpor-20d": "CSA, MPoR 20 days",
         "with-im": "With initial margin", "wrong-way-risk": "Wrong-way risk"}


def _usd(x: float) -> str:
    return f"{x:,.0f}"


def _table(head: list[str], rows: list[list[str]]) -> list[str]:
    return ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|", *("| " + " | ".join(r) + " |" for r in rows)]


def results_block(docs: dict[str, dict[str, Any]], models: dict[str, Any]) -> str:
    o = {v: docs[v]["outputs"] for v in ORDER}
    base = o["netting-set"]
    cal = base["calibration_used"]
    lines = [f"### The curve and the calibration ({base['curve']['curve_date']})", "",
             f"The Treasury par curve of {base['curve']['curve_date']} (tenors present: "
             f"{', '.join(f'{t:g}' for t in base['curve']['tenors_present'])} years; absent: "
             f"{', '.join(f'{t:g}' for t in base['curve']['tenors_absent']) or 'none'}), bootstrapped to continuously compounded zero rates. "
             f"Hull-White a = {cal['a']:.4f} (standard error {cal['a_se']:.4f}) and sigma = {cal['sigma']:.5f} ({cal['sigma_se']:.5f}), "
             f"from {cal['n_obs']:,} observations of the 3 month zero rate between {cal['sample_start']} and {cal['sample_end']} "
             f"({cal['history_years']:.2f} years). The models document holds the calibration of all {len(models['fit']['calibrations'])} "
             "backtest dates.", ""]
    lines += ["### Exposure, CVA and the regulatory measures (USD)", ""]
    rows = []
    for v in ORDER:
        x = o[v]
        rg = x["regulatory_comparison"]
        rows.append([NAMES[v], _usd(x["exposure"]["eepe"]["amount"]), _usd(max(x["exposure"]["pfe"]["values"])),
                     f"{x['cva_dva']['cva']['amount']:,.1f}", f"{x['cva_dva']['dva']['amount']:,.1f}", _usd(x["sa_ccr"]["ead"]["amount"]),
                     _usd(rg["alpha_times_eepe"]["amount"]), _usd(rg["stressed"]["effective_epe"]["amount"]),
                     _usd(x["ba_cva"]["capital"]["amount"]), _usd(x["girr"]["delta_charge"]["amount"])])
    lines += _table(["Variant", "EEPE", "Peak PFE 95%", "CVA", "DVA", "SA-CCR EAD", "1.4 x EEPE", "Stressed EEPE", "BA-CVA capital",
                     "GIRR delta"], rows)
    lines += ["", "EEPE and the stressed EEPE are the first-year averages of the effective EE; the peak PFE is the largest 95 percent "
              "quantile of the exposure over the grid; the GIRR delta charge divides the weights by the square root of 2 (MAR21.44), the "
              "undivided charge is in the documents.", ""]
    nb = base["netting_benefit"]
    k1 = base["exposure"]["time_grid_years"].index(1.0)
    lines += ["### What netting, collateral and initial margin remove", ""]
    rows = []
    for v in ORDER[:5]:
        e = o[v]["exposure"]
        rows.append([NAMES[v], _usd(e["ee"]["values"][k1]), _usd(max(e["ee"]["values"])), _usd(e["eepe"]["amount"]),
                     f"{o[v]['regulatory_comparison']['effective_maturity_years']:.2f}"])
    lines += _table(["Variant", "EE at 1 year", "Peak EE", "EEPE", "Effective maturity M (years)"], rows)
    lines += ["", f"Netting: at one year the sum of the single-trade EE is {_usd(nb['sum_of_single_trade_ee']['values'][k1])} and the netted "
              f"EE {_usd(nb['netted_ee']['values'][k1])}, a benefit of {_usd(nb['benefit']['values'][k1])} USD.", ""]
    w = o["wrong-way-risk"]["wrong_way_risk"]
    lines += ["### Wrong-way risk: CVA against b (per USD million of portfolio value)", ""]
    lines += _table(["b", "CVA (USD)", "Monte Carlo error", "Calibration error of a(t)"],
                    [[f"{p['b']:g}", f"{p['cva']['amount']:,.1f}", f"{p['cva']['mc_se']:,.1f}", f"{p['a_calibration_max_error']:.1e}"]
                     for p in w["sweep"]])
    lines += ["", f"The largest portfolio value on the simulated paths is {w['w_max_usd_million']:.3f} USD million, so the largest "
              f"exponent b w of the grid is {w['largest_b_w']:.2f}.", ""]
    bt = base["backtest"]
    lines += [f"### The exposure backtest ({bt['window_start']} to {bt['window_end']}, {len(bt['dates'])} monthly dates, "
              f"{bt['paths_per_date']:,} paths per date)", ""]
    rows = []
    for blk, tag in ((bt["book_horizons"], "Netting-set value"), (bt["risk_factor"]["horizons"], "3 month zero rate")):
        for h in blk:
            c95 = next(e for e in h["exceedances"] if e["quantile"] == 0.95)
            rows.append([tag, h["horizon"], f"{h['w2']:.2f}", f"{h['critical_simulated']['p05']:.2f}", f"{h['critical_simulated']['p01']:.2f}",
                         f"{h['effective_sample_size']:.1f}", "yes" if h["reject_at_5pct"] else "no", f"{c95['count']} of {c95['expected']:.1f}"])
    lines += _table(["Measure", "Horizon", "W^2", "Critical 5% (simulated)", "Critical 1% (simulated)", "Effective sample size",
                     "Rejected at 5%", "95% exceedances (observed of expected)"], rows)
    lines += ["", "The iid table values of the Anderson-Darling statistic are 2.492 (5 percent) and 3.880 (1 percent); the simulated ones "
              "come from the whole backtest simulated under the model with the same dates and overlapping horizons. The exceedance "
              "counts are a secondary row (BCBS 185 paragraph 27).", ""]
    rows = []
    for sw in bt["sub_windows"]:
        for r in sw["results"]:
            rows.append([sw["window"], f"{sw['start']} to {sw['end']}", r["horizon"], str(r["n"]), f"{r['w2']:.2f}"])
    lines += ["Sub-windows (book value):", ""] + _table(["Window", "Dates", "Horizon", "n", "W^2"], rows) + [""]
    lines += ["### Sensitivity of EE and PFE to the calibration (netting set)", ""]
    rows = [[s["case"], f"{s['a']:.4f}", f"{s['sigma']:.5f}", _usd(s["eepe"]["amount"]), _usd(s["pfe_peak"]["amount"])]
            for s in base["calibration_sensitivity"]]
    lines += _table(["Case", "a", "sigma", "EEPE", "Peak PFE"], rows) + [""]
    lines += ["### Reconciliation with ORE 1.8.17.0 and QuantLib 1.44", ""]
    rows = []
    for v in ORDER[:5]:
        r = o[v]["ore_reconciliation"]
        pts = r["agreement"]
        worst = max(abs(a["difference"]) / a["combined_se"] if a["combined_se"] > 0 else 0.0 for a in pts)
        rows.append([NAMES[v], _usd(r["eepe_agreement"]["python"]), _usd(r["eepe_agreement"]["ore"]), f"{r['cva_agreement']['python']:,.1f}",
                     f"{r['cva_agreement']['ore']:,.1f}", f"{sum(a['within_two_se'] for a in pts)} of {len(pts)}", f"{worst:.1f}",
                     "yes" if r["all_within_two_se"] else "no", f"{r['run_seconds']:.0f}"])
    lines += _table(["Variant", "EEPE Python", "EEPE ORE", "CVA Python", "CVA ORE", "Grid points within 2 SE", "Largest gap (SE)",
                     "All within 2 SE", "ORE seconds"], rows)
    lines += ["", f"ORE: {o['netting-set']['ore_reconciliation']['platform']}. The wrong-way variant is not reconciled: ORE's wrong-way "
              "example is a different model.", ""]
    ql = [t for t in docs["netting-set"]["tests"] if t["test_id"].startswith("ccr.quantlib_")]
    lines += _table(["Check", "Engine", "QuantLib 1.44", "Relative difference"],
                    [[t["test_id"].removeprefix("ccr.quantlib_"), f"{t['extras']['engine']:.10g}", f"{t['extras']['quantlib']:.10g}",
                      f"{t['statistic']:.1e}"] for t in ql]) + [""]
    lines += ["### Validation tests of the netting set", ""]
    tests = docs["netting-set"]["tests"]
    counts = {k: sum(t["light"] == k for t in tests) for k in ("green", "amber", "red", "not_evaluated")}
    lines += [f"{len(tests)} test rows: {counts['green']} green, {counts['amber']} amber, {counts['red']} red, "
              f"{counts['not_evaluated']} not evaluated.", ""]
    rows = [[t["test_id"], t.get("segment") or "", t["light"], "" if t["statistic"] is None else f"{t['statistic']:.4g}"]
            for t in tests if t["test_id"] in {"ccr.martingale_discounted_bonds", "ccr.eepe_recomputed", "ccr.cva_recomputed", "ccr.path_convergence",
                                               "ccr.reconcile_ee_profile", "ccr.ore_eepe_agreement", "ccr.ore_cva_agreement"}]
    lines += _table(["Test", "Segment", "Light", "Statistic"], rows)
    return "\n".join(lines).rstrip("\n") + "\n"


def write_page(page: Path, docs: dict[str, dict[str, Any]], models: dict[str, Any]) -> None:
    text = page.read_text(encoding="utf-8")
    head, rest = text.split(BEGIN, 1)
    tail = rest.split(END, 1)[1]
    page.write_text(head + BEGIN + "\n" + results_block(docs, models) + END + tail, encoding="utf-8", newline="\n")
