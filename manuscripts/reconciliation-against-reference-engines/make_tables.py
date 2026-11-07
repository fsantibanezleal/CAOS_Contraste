"""Write the result tables of the reconciliation manuscript (``tables/*.tex``) from ``experiments/results_*.json`` and the committed
documents.

    python manuscripts/reconciliation-against-reference-engines/make_tables.py

Each table is a booktabs ``table`` environment that the text ``\\input``s; no number is typed here.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
import figkit  # noqa: E402

EXP = HERE / "experiments"
OUT = HERE / "tables"


def load(name: str) -> dict:
    return json.loads((EXP / name).read_text(encoding="utf-8"))


def R(text: str) -> str:
    """A cell that holds LaTeX: the table writer leaves a cell that starts with a backslash as it is."""
    return "\\relax " + text


def sci(x: float, d: int = 1) -> str:
    """A number in scientific notation as a LaTeX math string."""
    if x == 0:
        return "$0$"
    m, e = f"{x:.{d}e}".split("e")
    return f"${m}\\times10^{{{int(e)}}}$"


def pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}"


def rate(cell: dict, d: int = 1) -> str:
    return f"{pct(cell['rate'], d)} [{pct(cell['lo'], d)}, {pct(cell['hi'], d)}]"


def short(name: str) -> str:
    return (name.replace("Pluto and Tasche (2005)", "Pluto and Tasche 2005").replace("Schuermann and Hanson (2004)", "Schuermann and Hanson 2004")
            .replace("Israel, Rosenthal and Wei (2001)", "Israel et al. 2001").replace("Engelmann (2024)", "Engelmann 2024").replace("Tasche (2013)", "Tasche 2013"))


def main() -> None:
    OUT.mkdir(exist_ok=True)
    pr, rt, cf, cm_, cr, tm, pa = (load(f"results_{n}.json") for n in ("printed", "routes", "closedforms", "committed", "criterion", "transition_matrix", "pairs"))
    ore = {v: load(f"results_ore_{v}.json") for v in ("netting-set", "single-swap", "csa-mpor-10d")}
    seed42 = {v: load(f"results_ore_seed42_{v}.json") for v in ("single-swap", "netting-set", "csa-mpor-10d", "csa-mpor-20d")}

    # ------------------------------------------------------------------ the main table
    t = pr["totals"]
    v = cm_["variants"]
    p1, p2 = rt["part1"], cf["part2"]
    rows = [
        ["Printed answers, five papers (P)", f"{t['n']} printed numbers", f"{t['agree']} agree to the digit; {t['n'] - t['agree']} gaps listed, largest {max(s['max_unit_gap'] for s in pr['sources']):.1f} units", "gaps explained in part"],
        ["Independent routes (I)", R(f"{p1['grid_comparisons']} $p$-values, grid of {p1['grid_cases']}"), R(f"largest difference {sci(max(p1['jeffreys_max_gap'], p1['binomial_max_gap']))}, tolerance $10^{{-9}}$"), "agree"],
        ["Independent routes (I)", R(f"{p1['random_comparisons']} $p$-values, seeded draw"), R(f"largest difference {sci(max(p1['random_jeffreys_max_gap'], p1['random_binomial_max_gap']))}"), "agree"],
        ["Closed forms in QuantLib (F)", "4 cases of the product", R(f"largest relative difference {sci(max(x['relative_difference'] for x in cf['part1'].values()))}, gate $10^{{-6}}$"), "agree"],
        ["Closed forms in QuantLib (F)", f"{p2['cases']} seeded cases", R(f"{p2['within_gate']} within the gate; largest {sci(p2['max_relative_difference'])}"), "one case beyond"],
        [R("Cohort estimators in \\texttt{transitionMatrix} (F)"), f"{tm['elements_compared']:,} matrix elements, {tm['panels']} panels",
         R(f"largest difference {sci(max(tm['state_period_max_abs_diff'], tm['state_pooled_max_abs_diff'], tm['exclude_period_max_abs_diff'], tm['exclude_pooled_max_abs_diff']))}"), "agree, two findings"],
        ["Appendix of Hull and White 2012 (P)", f"{pr['wrong_way_appendix']['n']} printed numbers", f"{pr['wrong_way_appendix']['agree']} agree to the digit; one at {max(c['unit_gap'] for c in pr['wrong_way_appendix']['cells']):.2f} units", "agree within two units"],
    ]
    for name, lab in (("single-swap", "Exposure of the single swap (M)"), ("netting-set", "Exposure of the netting set (M)"),
                      ("csa-mpor-10d", "Exposure under a CSA, 10 days (M)"), ("csa-mpor-20d", "Exposure under a CSA, 20 days (M)"), ("with-im", "Exposure under a CSA with initial margin (M)")):
        x = v[name]
        outcome = "agree" if x["rule_two_se"] else "gap"
        rows.append([lab, "33 dates, EEPE, CVA", R(f"{x['n_beyond_two']} dates beyond 2; largest $\\lvert z\\rvert$ {x['max_abs_z']:.2f}; EEPE $z$ {x['eepe']['z']:+.2f}, CVA $z$ {x['cva']['z']:+.2f}"), outcome])
    figkit.table(OUT / "main-results.tex", ["Reference (class)", "Compared", "Result", "Outcome"], rows,
                 caption="Main comparison: every reference class against the engine, with the number compared, the result with its size, and the outcome of the rule fixed for the class; "
                         "$z$ is the standardised difference of ORE and the engine on the product's draws, and the three collateralised rows are the reported gaps.",
                 label="tab:main-results", align="p{3.9cm}p{3.2cm}p{5.6cm}l", wide=False)

    # ------------------------------------------------------------------ the printed answers by source
    rows = []
    for s in pr["sources"]:
        rows.append([short(s["source"]), "recomputed" if s["kind"] == "recomputed" else "as recorded", s["n"], s["agree"], f"{100 * s['agree'] / s['n']:.0f}", f"{s['max_unit_gap']:.2f}"])
    rows.append(["All sources", "", t["n"], t["agree"], f"{100 * t['agree'] / t['n']:.0f}", f"{max(s['max_unit_gap'] for s in pr['sources']):.2f}"])
    figkit.table(OUT / "printed.tex", ["Source", "Inputs", "Printed numbers", "Agree to the digit", "Share (\\%)", "Largest gap (units)"], rows,
                 caption="Printed numbers of five papers recomputed with the engine or read as the committed documents record them, with the count that agrees to the printed digit and "
                         "the largest absolute gap in units of the last printed digit; the sources of the last three rows keep their inputs outside the repository.",
                 label="tab:printed", align="p{5.2cm}lrrrr", wide=False)

    # ------------------------------------------------------------------ the explanation of the misses
    ex = pr["explain_scaled"]
    rows = [[f"Table {k[5:]}", ex[k]["cells"], ex[k]["agree_with_exact_bounds"], ex[k]["agree_with_printed_bounds"], f"{ex[k]['worst_unit_gap_exact']:.2f}", f"{ex[k]['worst_unit_gap_printed']:.2f}"] for k in ex]
    figkit.table(OUT / "explain-scaled.tex", ["Table of Pluto and Tasche", "Cells", "Agree, exact bounds", "Agree, printed bounds", "Worst gap, exact", "Worst gap, printed"], rows,
                 caption="The scaled bounds of Tables 9 to 12 of Pluto and Tasche, computed from the exact bounds and from the printed and rounded bounds of Tables 4 to 8 that the paper scaled, "
                         "with the count of cells that agree to the printed digit and the worst gap in units of the last digit for each route.",
                 label="tab:explain-scaled", align="lrrrrr", wide=False)
    cat = pr["miss_categories"]
    order = ["rounded printed inputs (tested)", "confidence level of the print (tested)", "documented tolerance (recorded)", "print at or above the exact bound (recorded)",
             "Monte Carlo print (recorded)", "printed generator (recorded)", "no explanation; within one unit", "no explanation; beyond one unit"]
    rows = [[k, cat.get(k, 0)] for k in order] + [["All gaps", pr["n_misses"]]]
    figkit.table(OUT / "miss-categories.tex", ["Explanation of the gap", "Gaps"], rows,
                 caption="The gaps of the printed-answer reconciliation by what explains them: a rounding explanation tested here, a recorded tolerance or note of the committed documents, "
                         "or none, with the count of gaps in each class over the 438 printed numbers.",
                 label="tab:miss-categories", align="p{9cm}r", wide=False)

    # ------------------------------------------------------------------ routes and planted defects
    rows = []
    b = rt["defect_tail_convention"]
    rows.append(["Tail convention of the binomial helper moved by one", "n/a", sci(b["C1_binomial"]) if b["C1_binomial"] else "$0$", sci(b["C2_binomial"]), sci(b["C3_binomial"]),
                 "C2 and C3"])
    for r in rt["defect_relative"]:
        flags = [k for k in ("C1", "C2", "C3") if r["flag"][f"{k}_binomial"]]
        rows.append([R("Relative error $\\epsilon$ in SciPy"), sci(r["eps"], 0), "$0$" if r["C1_binomial"] == 0 else sci(r["C1_binomial"]),
                     "$0$" if r["C2_binomial"] == 0 else sci(r["C2_binomial"]), sci(r["C3_binomial"]), " and ".join(flags) if flags else "none"])
    figkit.table(OUT / "routes-defects.tex", ["Planted defect", "Size", "C1 reuse", "C2 same library", "C3 independent", "Flagged by"], rows,
                 caption="Largest difference between the defective engine's binomial p-value and three kinds of reference on the grid of 36 cases, for a tail convention moved by one and for a "
                         "relative error planted inside SciPy; a defect is flagged when the difference exceeds the tolerance of $10^{-9}$.",
                 label="tab:routes-defects", align="p{4.6cm}lllll", wide=False)

    # ------------------------------------------------------------------ the committed ORE reconciliations
    rows = []
    names = {"single-swap": "Single swap", "netting-set": "Netting set", "csa-mpor-10d": "CSA, 10 days", "csa-mpor-20d": "CSA, 20 days", "with-im": "CSA, 10 days, initial margin"}
    for k, x in v.items():
        mta = "n/a" if x["mta0_max_z"] is None else f"{x['mta0_max_z']:.2f}"
        rows.append([names[k], f"{x['n_beyond_two']}", f"{x['max_abs_z']:.2f}", f"{x['mean_z']:+.2f}", f"{x['eepe']['z']:+.2f}", f"{x['cva']['z']:+.2f}", mta,
                     f"{100 * x['eepe']['equivalence_margin_rel']:.1f}", f"{100 * x['eepe']['min_detectable_rel_80']:.1f}"])
    figkit.table(OUT / "committed-ore.tex", ["Variant", "Dates beyond 2", "Largest $\\lvert z\\rvert$", "Mean $z$", "EEPE $z$", "CVA $z$", "Largest $\\lvert z\\rvert$, zero MTA", "EEPE equiv. margin (\\%)", "EEPE detectable gap (\\%)"], rows,
                 caption="The five exposure variants reconciled with ORE on the product's draws: the number of the 33 report dates beyond two combined standard errors, the largest and the mean standardised "
                         "difference, the EEPE and CVA differences, the diagnostic run with a zero minimum transfer amount, and the equivalence margin and the 80 percent detectable gap of the EEPE.",
                 label="tab:committed-ore", align="p{3.1cm}rrrrrrrr", wide=True)

    # ------------------------------------------------------------------ the size and power of the rules
    rules = [("product", "Product rule (dates, EEPE, CVA; bound 2)"), ("sidak", "Product errors, bound 3.18"), ("pair", "Pair-aware errors, bound 2"),
             ("pair+sidak", "Pair-aware errors, bound 3.18"), ("dates", "Dates only (bound 2)"), ("eepe", "EEPE only (bound 2)"), ("cva", "CVA only (bound 2)"),
             ("fixed 1%", "Fixed tolerance 1 % of the peak"), ("fixed 2%", "Fixed tolerance 2 % of the peak"), ("fixed 5%", "Fixed tolerance 5 % of the peak")]
    T = cr["table"]
    cols = [("single-swap|null", "Size, single"), ("netting-set|null", "Size, netting"), ("netting-set|sigma+2%", "Vol. +2 \\%"), ("netting-set|sigma+5%", "Vol. +5 \\%"),
            ("netting-set|a+50%", "Rev. +50 \\%"), ("netting-set|measure", "Measure")]
    rows = [[lab] + [rate(T[c][key]) for c, _ in cols] for key, lab in rules]
    figkit.table(OUT / "rule-size-power.tex", ["Rule"] + [c for _, c in cols], rows,
                 caption=f"Rejection rate in percent, with its Wilson 95 percent interval, of ten acceptance rules over {cr['reps']} paired runs of the engine and a reference of the same model: "
                         "the size on the single swap and on the netting set, and the power on the netting set against a volatility raised by 2 and 5 percent, a mean reversion raised by 50 percent, and a measure error.",
                 label="tab:rule-size-power", align="p{4.6cm}llllll", wide=True)

    # ------------------------------------------------------------------ the ablation of the refinement
    steps = [("pair+sidak", "Refinement: pair-aware errors and bound 3.18"), ("pair", "without the family-wise bound (bound 2)"), ("sidak", "without the pair-aware errors (product errors, bound 3.18)"),
             ("product", "without either (the product's rule)"), ("dates", "dates only, product errors"), ("eepe", "EEPE only"), ("cva", "CVA only")]
    cols = [("netting-set|null", "Size"), ("netting-set|sigma+2%", "Vol. +2 \\%"), ("netting-set|sigma+5%", "Vol. +5 \\%"), ("netting-set|a+50%", "Rev. +50 \\%"), ("netting-set|measure", "Measure")]
    rows = [[lab] + [pct(T[c][key]["rate"]) for c, _ in cols] for key, lab in steps]
    figkit.table(OUT / "ablation.tex", ["Component removed or changed"] + [c for _, c in cols], rows,
                 caption="Contribution of each part of the acceptance rule on the netting set: rejection rate in percent when the pair-aware errors, the family-wise bound, or the comparison of the "
                         "dates, of the EEPE or of the CVA is taken away, under the null (size) and against four planted defects (power).",
                 label="tab:ablation", align="p{6.4cm}lllll", wide=False)

    # ------------------------------------------------------------------ calibration of the standard errors
    cal_s, cal_n = cr["calibration"]["single-swap"], cr["calibration"]["netting-set"]
    rows = [["Expected exposure, dates (median over dates)", f"{cal_s['median_sd_z']:.2f}", f"{cal_n['median_sd_z']:.2f}", f"{cal_s['median_sd_z_pair']:.2f}", f"{cal_n['median_sd_z_pair']:.2f}"],
            ["EEPE (batch error)", f"{cal_s['sd_ze']:.2f}", f"{cal_n['sd_ze']:.2f}", "n/a", "n/a"],
            ["CVA", f"{cal_s['sd_zc']:.2f}", f"{cal_n['sd_zc']:.2f}", f"{pa['single-swap']['predicted_sd_z_cva']:.2f} (predicted)", f"{pa['netting-set']['predicted_sd_z_cva']:.2f} (predicted)"]]
    figkit.table(OUT / "calibration.tex", ["Statistic", "Single swap, product errors", "Netting set, product errors", "Single swap, pair-aware", "Netting set, pair-aware"], rows,
                 caption=f"Standard deviation over {cr['reps']} paired runs of the same model of the standardised difference, for the product's errors and the pair-aware errors, and for the CVA the value "
                         "that Proposition~\\ref{prop:antithetic} predicts from the measured pair correlation; a calibrated statistic has a standard deviation of one.",
                 label="tab:calibration", align="p{5.0cm}llll", wide=True)

    # ------------------------------------------------------------------ the repeated ORE runs
    rows = []
    for k in ("single-swap", "netting-set", "csa-mpor-10d"):
        s = ore[k]["summary"]
        reps = ore[k]["replicates"]
        s42 = seed42[k]["replicates"][0]
        rows.append([names[k], s["reps"], f"{s['passed_product_rule']} ({100 * s['pass_lo']:.0f}--{100 * s['pass_hi']:.0f})", f"{s['mean_of_mean_z']:+.2f}", f"{s['mean_of_mean_z_pair']:+.2f}",
                     f"{s['mean_z_eepe']:+.2f}", f"{s['mean_z_cva']:+.2f}", f"{s['median_max_abs_z']:.2f}", f"{s42['max_abs_z']:.2f}"])
    figkit.table(OUT / "ore-replicates.tex", ["Variant", "Seeds", "Rule passed (95\\% interval, \\%)", "Mean $z$", "Mean $z$, pair-aware", "Mean EEPE $z$", "Mean CVA $z$", "Median largest $\\lvert z\\rvert$", "Largest $\\lvert z\\rvert$ at seed 42"], rows,
                 caption="The engine against ORE on new seeds: the number of seeds on which the product's rule passes, the mean standardised difference over seeds and dates with the product's and the pair-aware "
                         "errors, the mean EEPE and CVA differences, and the largest difference at the product's seed 42 rerun here.",
                 label="tab:ore-replicates", align="p{3.1cm}rlrrrrrr", wide=True)

    # ------------------------------------------------------------------ the transition-matrix comparison
    ld = tm["last_record_double_count"]
    rows = [["Cohort, withdrawals kept as a state, per period", sci(tm["state_period_max_abs_diff"]) if tm["state_period_max_abs_diff"] else "$0$", "agree"],
            ["Cohort, withdrawals kept as a state, pooled", sci(tm["state_pooled_max_abs_diff"]) if tm["state_pooled_max_abs_diff"] else "$0$", "agree"],
            ["Cohort, withdrawals excluded, per period", sci(tm["exclude_period_max_abs_diff"]), "agree"],
            ["Cohort, withdrawals excluded, pooled", sci(tm["exclude_pooled_max_abs_diff"]), "agree"],
            ["Last record of the last entity, package unguarded", f"{ld['min_gap_without_sentinel']:.4f} to {ld['max_gap_without_sentinel']:.4f}", "gap: the package counts the last migration twice"],
            ["Same, engine counts corrected by that migration", sci(ld["max_gap_after_correction"]) if ld["max_gap_after_correction"] else "$0$", "explained"],
            ["Aalen--Johansen increment on the four-obligor example", f"{tm['aalen_johansen']['difference']:.4f}", "gap: risk set counted after the exit (3 against 4)"]]
    figkit.table(OUT / "transition-matrix.tex", ["Comparison", "Largest difference", "Outcome"], rows,
                 caption=f"The engine's cohort and Aalen--Johansen estimators against \\texttt{{transitionMatrix}} {tm['transitionMatrix']} on {tm['panels']} seeded panels of {tm['entities']} entities with withdrawals: "
                         "the largest element-wise difference for each convention, and the two differences that the package's own code explains.",
                 label="tab:transition-matrix", align="p{6.3cm}p{2.8cm}p{5.2cm}", wide=False)
    # ------------------------------------------------------------------ the ablation of the protocol parts
    sw = {x["units"]: x["agree"] for x in pr["tolerance_sweep"]}
    exa = sum(x["agree_with_exact_bounds"] for x in ex.values())
    prt = sum(x["agree_with_printed_bounds"] for x in ex.values())
    ncell = sum(x["cells"] for x in ex.values())
    def nflags(k: str) -> int:
        return int(rt["defect_tail_convention"]["flag"][f"{k}_binomial"]) + sum(r["flag"][f"{k}_binomial"] for r in rt["defect_relative"])
    ndef = 1 + len(rt["defect_relative"])
    def NS(k: str) -> dict:
        return T[f"netting-set|{k}"]
    rows = [
        ["Gap in units of the last digit", "numbers classed by the size of the gap", f"{pr['unit_gap_bins']['half']}, {pr['unit_gap_bins']['to_one']}, {pr['unit_gap_bins']['to_two']}, {pr['unit_gap_bins']['beyond_two']} in four bins", f"{t['agree']} agree, {t['n'] - t['agree']} fail"],
        ["Tested explanation of a gap", f"cells of Tables 9 to 12 agreeing (of {ncell})", f"{prt} (printed inputs scaled)", f"{exa} (exact inputs)"],
        ["Independent route", f"planted defects flagged (of {ndef})", f"{nflags('C3')} (C3)", f"{nflags('C2')} (C2) and {nflags('C1')} (C1)"],
        ["Pair-aware errors", "power against a 2 percent volatility error, netting set, bound 3.18", f"{pct(NS('sigma+2%')['pair+sidak']['rate'])} percent", f"{pct(NS('sigma+2%')['sidak']['rate'])} percent"],
        ["Family-wise bound", "size on the netting set, pair-aware errors", f"{pct(NS('null')['pair+sidak']['rate'])} percent (bound 3.18)", f"{pct(NS('null')['pair']['rate'])} percent (bound 2)"],
        ["Diagnostic with a zero minimum transfer amount", "largest standardised difference, 10 and 20 days", f"{v['csa-mpor-10d']['mta0_max_z']:.2f} and {v['csa-mpor-20d']['mta0_max_z']:.2f}", f"{v['csa-mpor-10d']['max_abs_z']:.2f} and {v['csa-mpor-20d']['max_abs_z']:.2f}"],
        ["Equivalence margin and detectable gap", "what a pass on the single swap EEPE supports", f"equivalent within {100 * v['single-swap']['eepe']['equivalence_margin_rel']:.1f} percent; gap of {100 * v['single-swap']['eepe']['min_detectable_rel_80']:.1f} percent detectable", "agreement, no size"],
        ["Scope list", "comparisons listed as not run", "wrong-way variant against ORE", "silence"],
    ]
    figkit.table(OUT / "ablation-protocol.tex", ["Part of the protocol", "Measurement", "With the part", "Without it"], rows,
                 caption="Contribution of each part of the protocol, measured by what the reconciliation reports with the part and without it: the unit of the gap, the tested explanation, the independent route, "
                         "the pair-aware error, the family-wise bound, the diagnostic run, the equivalence margin and the scope list.",
                 label="tab:ablation-protocol", align="p{3.6cm}p{4.2cm}p{4.0cm}p{3.0cm}", wide=True)

    # ------------------------------------------------------------------ the outcomes
    def rl(k: str) -> dict:
        return ore[k]["summary"]
    mx = max(c["unit_gap"] for c in pr["wrong_way_appendix"]["cells"])
    n_tested = sum(1 for m in pr["misses"] if "tested" in m["explanation"])
    rows = [
        ["H1", "not met as stated", f"{t['n']} printed numbers and {t['agree']} agreeing against the {pr['sdd_statement']['n']} and {pr['sdd_statement']['agree']} quoted; the quoted counts are those of the tally without Tasche's Tables 8 and 9 "
                                    f"({pr['without_tasche_tables_8_and_9']['n']} and {pr['without_tasche_tables_8_and_9']['agree']}); all {pr['n_misses']} gaps are listed, {n_tested} with a tested explanation"],
        ["H2", "held", f"{p1['within_tol_grid']} of {p1['grid_comparisons']} comparisons within $10^{{-9}}$ on the grid, {p1['random_within_tol']} of {p1['random_comparisons']} on the seeded draw"],
        ["H3", "held", f"single swap and netting set pass on the product's draws (largest $\\lvert z\\rvert$ {v['single-swap']['max_abs_z']:.2f} and {v['netting-set']['max_abs_z']:.2f}); the rule passes on {rl('single-swap')['passed_product_rule']} of {rl('single-swap')['reps']} and {rl('netting-set')['passed_product_rule']} of {rl('netting-set')['reps']} new seeds"],
        ["H4", "held with one case beyond the gate", f"four cases within $10^{{-6}}$; {p2['within_gate']} of {p2['cases']} on the grid, the case beyond at {sci(p2['max_relative_difference'])} on a price of {p2['worst'][0]['quantlib']:.1f} USD"],
        ["H5", f"held for {pr['wrong_way_appendix']['agree']} of {pr['wrong_way_appendix']['n']} numbers", f"{pr['wrong_way_appendix']['agree']} of {pr['wrong_way_appendix']['n']} printed numbers agree to the digit; the second constant is {mx:.2f} units from its print"],
        ["H6", "held", f"largest expected-exposure gaps {v['csa-mpor-10d']['max_abs_z']:.1f}, {v['csa-mpor-20d']['max_abs_z']:.1f} and {v['with-im']['max_abs_z']:.1f}, valuation-adjustment gaps {v['csa-mpor-10d']['cva']['z']:.1f} and {v['csa-mpor-20d']['cva']['z']:.1f}, mean margin ratio {v['with-im']['dim']['mean_ratio_ore_over_python']:.2f}; the 10-day variant fails the rule on {rl('csa-mpor-10d')['reps'] - rl('csa-mpor-10d')['passed_product_rule']} of {rl('csa-mpor-10d')['reps']} new seeds"],
    ]
    figkit.table(OUT / "outcomes.tex", ["Hypothesis", "Outcome", "Evidence"], [[a, b, R(c)] for a, b, c in rows],
                 caption="Outcome of each hypothesis of Table~\\ref{tab:hypotheses} with the evidence that decides it: a hypothesis held when the measurement meets its claim, and is reported as not met or "
                         "held with a qualification when a count or a bound of the claim fails in part.",
                 label="tab:outcomes", align="llp{10.4cm}", wide=False)
    print("tables written:", sorted(p.name for p in OUT.glob("*.tex")))


if __name__ == "__main__":
    main()
