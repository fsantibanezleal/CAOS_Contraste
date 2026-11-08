"""Write every results table of the manuscript and ``tables/numbers.tex`` from ``experiments/results_*.json``.

    python manuscripts/reverse-liquidity-stress-with-a-refusal-rule/make_tables.py

Tables land in ``tables/`` as booktabs ``.tex`` files that the sections input; numbers.tex defines one macro per number of the prose.
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
sys.path.insert(0, str(HERE))
import figkit  # noqa: E402
import make_numbers as mn  # noqa: E402

OUT = HERE / "tables"
OUT.mkdir(exist_ok=True)
C = mn.load("results_reverse_c16.json")
K = mn.load("results_corpus.json")
T = mn.load("results_theory.json")
pc, ci = mn.pc, mn.ci


def write(name: str, text: str) -> None:
    (OUT / f"{name}.tex").write_text(text, encoding="utf-8", newline="\n")


def tab(caption: str, label: str, body: list[str], align: str, header: str, star: bool = False) -> str:
    env = "table*" if star else "table"
    return "\n".join([f"\\begin{{{env}}}[htbp]", "\\centering", "\\small", "\\setlength{\\tabcolsep}{3pt}", f"\\caption{{{caption}}}", f"\\label{{{label}}}",
                      f"\\begin{{tabular}}{{{align}}}", "\\toprule", header + " \\\\", "\\midrule", *body, "\\bottomrule", "\\end{tabular}", f"\\end{{{env}}}", ""])


def day(x) -> str:
    return "survives" if x is None else str(x)


def notation() -> None:
    rows = [
        ("$S$, $H$", "number of deposit segments, horizon in days", "1, days"),
        ("$A_j$", "opening balance of segment $j$", "money"),
        ("$q_{j,d}$", "base daily run-off rate of segment $j$ on day $d$, in $[0,1]$", "per day"),
        ("$m$", "run-off multiplier applied to every rate", "1"),
        ("$m_{\\max}$", "cap: $1/\\max\\{q_{j,d}<1\\}$", "1"),
        ("$F_j(t;m)$", "cumulative outflow share of segment $j$ by day $t$ at multiplier $m$", "share"),
        ("$X_t(m)$", "cumulative segment outflow $\\sum_j A_j F_j(t;m)$", "money"),
        ("$C_t$", "effective capacity: counterbalancing capacity plus cumulative inflows less cumulative flows outside the segments", "money"),
        ("$\\mathrm{NLP}_t(m)$", "net liquidity position $C_t-X_t(m)$", "money"),
        ("$\\mathrm{SP}(m)$", "survival period: first day with negative position, $\\infty$ if none", "days"),
        ("$T$", "target survival period", "days"),
        ("$w_T(m)$", "window function $\\min_{t\\le T}\\mathrm{NLP}_t(m)$", "money"),
        ("$m_0$, $m^\\ast$", "root of $w_T$ and its six-decimal upward rounding", "1"),
        ("$\\delta$", "rounding step, $10^{-6}$", "1"),
        ("$\\kappa$", "capacity over opening balance, one segment", "1"),
        ("$O_{j,d}$", "outflow of segment $j$ on day $d$", "money"),
        ("$U_T$", "set of multipliers in $[1,m_{\\max}]$ at which the survival period is at most $T$", "set"),
        ("$\\bar m$", "upper end of the bracket: the cap when finite, 1 when no rate can be scaled", "1"),
        ("$\\mathrm{SP}_1$", "survival period of the unscaled scenario, $\\mathrm{SP}(1)$", "days"),
        ("$Q_T$", "bound $\\sum_jA_j\\sum_{s\\le T}q_{j,s}$ on the slope of $X_T$ in $m$", "money"),
        ("$O_T(m)$", "outflow of day $T$ at multiplier $m$", "money"),
        ("$a$, $b$", "$-\\ln(1-\\kappa)$ and $-\\ln(1-q)$, one segment", "1"),
        ("$\\tilde m$", "hyperbolic rule $\\mathrm{SP}(1)/T$", "1"),
        ("$\\varepsilon$", "level shift of the effective capacity", "money"),
        ("$t_0$", "day at which $\\mathrm{NLP}_t(m_0)$ is smallest over $t\\le T$", "days"),
        ("$X'_t(m)$", "derivative of $X_t$ in $m$", "money"),
        ("$n$", "horizon of a row of the labelled run, in days", "days"),
        ("$\\hat q$, $q_{\\mathrm{fast}}$", "implied daily rate of a row, and the rate of the fast-run base, the maximum of $\\hat q$ over $\\mathcal R_{<2023}$", "per day"),
        ("$\\mathcal R_{<2023}$", "rows of the table of observed outflows dated before 2023", "set"),
        ("$F^{\\mathrm{mod}}_n$, $F^{\\mathrm{obs}}$", "modelled and observed cumulative outflow share of the deposit base at the horizon of a row", "share"),
        ("$m_{\\mathrm{run}}$", "multiplier at which the modelled share equals the observed one", "1"),
        ("$e$, $\\tau$", "signed relative error of an answer $\\hat m$, and its threshold-property indicator", "1"),
    ]
    body = [f"{a} & {b} & {c} \\\\" for a, b, c in rows]
    write("notation", tab("Notation of the reverse stress: every symbol of the problem formulation, the method and the theory with its meaning and unit, the money unit being that of the balance sheet it is applied to (thousands of US dollars for case C16).",
                          "tab:notation", body, "lp{9.2cm}l", "Symbol & Meaning & Unit"))


def design() -> None:
    d = K["design"]
    rows = [("instances (banks $\\times$ targets)", f"{d['instances']:,}"), ("solved by the oracle", f"{d['solved']:,}"),
            ("refused: target not below the horizon", f"{d['refused_horizon']:,}"), ("refused: base survival period already at or below the target", f"{d['refused_base']:,}"),
            ("refused: no multiplier under the cap reaches the target", f"{d['refused_unreachable']:,}"),
            ("solved, constant capacity and no inflow", f"{d['solved_flat_no_inflow']:,}"), ("solved, capacity on a monetisation schedule", f"{d['solved_growing']:,}")]
    body = [f"{a} & {b} \\\\" for a, b in rows]
    write("design", tab(f"Composition of the seeded corpus: {len(d['seeds'])} independent corpora of {d['banks_per_seed']:,} synthetic banks, each solved at the targets of 2, 5, 10 and 30 days, counted by the outcome of the independent oracle.",
                        "tab:design", body, "lr", "Outcome of the oracle & Instances"))


def main_results() -> None:
    m = K["methods"]
    names = [("proposed", "proposed solver"), ("grid_case", "scan of the case grid"), ("grid_fine", "scan of a fine grid"),
             ("brent_sp", "Brent on the survival period"), ("bisect_no_refusal", "bisection without refusal")]
    a = []
    for k, lab in names:
        x = m[k]
        a.append(f"{lab} & {ci(x['false_answer_on_refused'])} & {ci(x['miss_on_solved'])} & {ci(x['threshold_property_on_solved'])} & "
                 f"{x['abs_rel_error_median']['est']:.1e} & {x['evals_mean_solved']:.1f} & {x['time_us_median'] / 1000:.2f} \\\\")
    for k, nm in (("proposed", "P"), ("grid_case", "G"), ("grid_fine", "F"), ("brent_sp", "B"), ("bisect_no_refusal", "N")):
        pass
    b = []
    for base, lab in (("list-adverse", "LiST Adverse"), ("list-extreme", "LiST Extreme"), ("fast-run", "2023 fast run")):
        e = C["bases"][base]
        en = e["engine"]
        if en["status"] == "solved":
            b.append(f"{lab} & {day(e['base_sp'])} & {e['cap']:.1f} & {en['multiplier']:.6f} & {en['sp_at']} & {day(en['sp_just_below'])} \\\\")
        else:
            b.append(f"{lab} & {day(e['base_sp'])} ({e['horizon']}-day horizon) & {e['cap']:.1f} & refused, no number & -- & -- \\\\")
    cap = ("Main results. Panel A: the proposed solver and four comparators scored against the independent oracle on 20,000 instances of the seeded corpus; "
           "rates in per cent with 95\\% Wilson intervals, median absolute relative error of the multiplier on solved instances, mean forward evaluations per solved instance and median time per call; the scans call the engine's own forward function, which is slower per evaluation than the lighter function the solver and Brent's method call, so the cost is compared by evaluations. "
           "Panel B: the same solver on the three committed bases of case C16 at a target of 30 days, with the survival period reached at the multiplier and just below it.")
    text = "\n".join(["\\begin{table*}[htbp]", "\\centering", "\\small", "\\setlength{\\tabcolsep}{3pt}", f"\\caption{{{cap}}}", "\\label{tab:main-results}",
                      "\\begin{tabular}{p{2.8cm}p{2.3cm}p{2.3cm}p{2.3cm}p{1.5cm}p{1.6cm}p{1.1cm}}", "\\toprule",
                      "\\multicolumn{7}{l}{\\textit{Panel A: corpus of synthetic banks}} \\\\",
                      "Method & answers where refused (\\%) & no answer where solved (\\%) & threshold property (\\%) & median $|$rel. error$|$ & evaluations & ms per call \\\\",
                      "\\midrule", *a, "\\bottomrule", "\\end{tabular}", "", "\\medskip", "",
                      "\\begin{tabular}{p{3.0cm}p{3.0cm}p{1.4cm}p{2.3cm}p{1.8cm}p{2.3cm}}", "\\toprule", "\\multicolumn{6}{l}{\\textit{Panel B: committed bases of case C16, target of 30 days}} \\\\",
                      "Base & base SP (days) & cap & multiplier $m^\\ast$ & SP at $m^\\ast$ & SP at $m^\\ast-10^{-6}$ \\\\", "\\midrule", *b, "\\bottomrule", "\\end{tabular}", "\\end{table*}", ""])
    write("main-results", text)


def spread() -> None:
    """Spread of the rates over the five corpora and bootstrap intervals of the median error (the statistics of the experimental design)."""
    m = K["methods"]
    names = [("proposed", "proposed solver"), ("grid_case", "scan of the case grid"), ("grid_fine", "scan of a fine grid"),
             ("brent_sp", "Brent on the survival period"), ("bisect_no_refusal", "bisection without refusal")]
    body = []
    for k, lab in names:
        x = m[k]
        e = x["abs_rel_error_median"]
        body.append(f"{lab} & {pc(x['false_answer_on_refused']['sd_over_corpora'], 2)} & {pc(x['miss_on_solved']['sd_over_corpora'], 2)} & "
                    f"{pc(x['threshold_property_on_solved']['sd_over_corpora'], 2)} & {e['est']:.2e} ({e['lo']:.2e} to {e['hi']:.2e}) \\\\")
    write("spread", tab("Spread of the rates of Panel A of \\cref{tab:main-results} over the five corpora of 1,000 banks, as the standard deviation of the rate of a corpus in percentage points, "
                        "and the median absolute relative error with its 95\\% bootstrap percentile interval (1,000 resamples of the solved instances).",
                        "tab:spread", body, "p{3.8cm}p{2.2cm}p{2.2cm}p{2.2cm}p{4.4cm}",
                        "Method & SD, answers where refused & SD, no answer where solved & SD, threshold property & median $|$rel. error$|$ (95\\% interval)", star=True))


def theory_checks() -> None:
    cf = T["closed_form_single_segment"]
    er = T["exact_round_trip"]
    rows = [
        ("Monotone position", f"{T['monotone_in_multiplier']['banks']:,} corpus banks, {T['monotone_in_multiplier']['comparisons']:,} pairs of adjacent points of a 40-point multiplier grid",
         f"{T['monotone_in_multiplier']['violations']} increases above a tolerance of $10^{{-9}}$ of the opening balance (largest increase {T['monotone_in_multiplier']['largest_increase']:.1e})"),
        ("Threshold: non-increasing in the target", f"{T['monotone_in_target']['banks']:,} banks, {T['monotone_in_target']['pairs']:,} pairs of targets", f"{T['monotone_in_target']['violations']} violations"),
        ("Threshold: non-decreasing in the capacity", f"{T['monotone_in_capacity']['banks']:,} banks, {T['monotone_in_capacity']['pairs']:,} pairs of solves with the capacity raised by 5\\%", f"{T['monotone_in_capacity']['violations']} violations"),
        ("Closed form, outcome", f"{cf['instances']:,} single-segment banks", f"{cf['condition_mismatches']} disagreements between the engine's outcome and the stated conditions"),
        ("Closed form, value", f"{cf['solved']:,} solved", f"largest difference {cf['max_abs_difference'] * 1e6:.4f} millionths, {cf['engine_below_closed_form']} engine values below the closed form, {cf['multiplier_bound_violations']} violations of the bounds on the root"),
        ("Hyperbolic rule", f"{cf['hyperbolic_instances']:,} solved instances with $a<2T$", f"{cf['hyperbolic_bound_violations']} violations of the two-sided bound; median relative error {pc(cf['hyperbolic_relative_error_median'])}\\%"),
        ("Exact round trip", f"{er['solved_flat_no_inflow']:,} solved banks with a constant capacity and no inflow", f"condition holds on {er['condition_holds']:,}, round trip exact on {er['exact']:,}, {er['violations_of_the_proposition']} violations; margin at least {er['margin_min']:.0f}, median {er['margin_median']:,.0f}"),
    ]
    body = [f"{a} & {b} & {c} \\\\" for a, b, c in rows]
    write("theory-checks", tab(f"Numerical checks of the propositions of \\cref{{sec:theory}} on banks drawn with seed {T['seed']}: what was tested, on how many cases, and what was found. "
                               "The checks test the statements and do not replace the proofs.",
                               "tab:theory-checks", body, "p{3.2cm}p{4.6cm}p{6.6cm}", "Statement & Sample & Result"))


def ablation() -> None:
    m = K["methods"]
    rows = [("proposed solver (all components)", "proposed"), ("without the cap on the scaled rates", "uncapped"), ("without the refusal rule", "bisect_no_refusal"),
            ("without the continuous window function (Brent on SP)", "brent_sp"), ("without upward rounding and the neighbour check", "nearest"),
            ("without inflows and flows outside the segments", "raw_capacity")]
    body = []
    for lab, k in rows:
        x = m[k]
        body.append(f"{lab} & {pc(x['false_answer_on_refused']['rate'])} & {pc(x['miss_on_solved']['rate'])} & {pc(x['threshold_property_on_solved']['rate'])} & "
                    f"{pc(x['answered_beyond_cap']['rate'], 2)} & {x['abs_rel_error_median']['est']:.1e} \\\\")
    write("ablation", tab("Ablation on the corpus of 20,000 instances: each row removes one component of the proposed solver; the columns are the share of refused instances answered with a number, "
                          "the share of solved instances left without a number, the share of solved instances whose multiplier is a threshold, the share of all instances answered with a multiplier above the cap, and the median relative error.",
                          "tab:ablation", body, "p{4.4cm}p{1.9cm}p{1.9cm}p{1.9cm}p{1.9cm}p{1.9cm}", "Variant & answer if refused (\\%) & no answer if solved (\\%) & threshold (\\%) & beyond cap (\\%) & median rel. error", star=True))


def band() -> None:
    body = []

    def row(label: str, r: dict, c0: float) -> str:
        if r["multiplier"] is None:
            return f"{label} & refused & & \\\\"
        return f"{label} & {r['multiplier']:.6f} & {100 * (r['multiplier'] / c0 - 1):+.1f} & {r['sp_at']} \\\\"

    for base, lab in (("list-adverse", "Adverse"), ("list-extreme", "Extreme")):
        b = C["band"][base]
        c0 = C["bases"][base]["engine"]["multiplier"]
        body.append(f"\\multicolumn{{4}}{{l}}{{\\textit{{LiST {lab} base, central multiplier {c0:.6f}}}}} \\\\")
        for r in b["one_at_a_time"]:
            body.append(row(r["factor"], r, c0))
        for r in b["mapping"]:
            if r["mapping"].endswith("(central)"):
                continue
            body.append(row(f"uninsured as {r['mapping']}", r, c0))
        for hc in ("low", "central", "high"):
            lo = [r for r in b["haircut_x_monetisation"] if r["haircut"] == hc and r["monetisation"] == "slow"][0]
            body.append(row(f"joint: haircut {hc} and slow monetisation", lo, c0))
    write("band", tab("Sensitivity of the threshold multiplier at a target of 30 days to the conventions of case C16: the haircut band of 0.05, the immediate and slow monetisation schedules, "
                      "the placement of the uninsured balance, and the three corners of the joint band that use the slow schedule; the last column is the survival period at the multiplier, "
                      "which is the target wherever the round trip is exact and falls short of it where the slow schedule turns the threshold into a step; a refusal is stated, never a number.",
                      "tab:band", body, "lrrr", "Convention changed & Multiplier & Change (\\%) & SP at $m^\\ast$"))


def labelled() -> None:
    L = C["labelled_run"]
    body = []
    for r in L["rows"]:
        if r["modelled"] is None:
            body.append(f"{r['bank']} {r['year']} & {r['days']} & {r['observed']:.2f} & beyond the 5-day ladder & -- & -- \\\\")
        else:
            body.append(f"{r['bank']} {r['year']} ({r['role']}) & {r['days']} & {r['observed']:.2f} & {r['modelled']:.4f} & {r['ratio']:.3f} & {r['light']} \\\\")
    write("labelled-run", tab("The fast-run base calibrated on the Table A.1 rows dated before 2023 and scored on the rows of the run: the modelled cumulative outflow share at the horizon of each row, "
                              "its ratio to the observed share and the light of the case design (green from 0.8, amber from 0.5); rows with a horizon beyond the 5-day ladder are not scored.",
                              "tab:labelled-run", body, "lccccc", "Row & Days & Observed & Modelled & Ratio & Light"))


def hypotheses() -> None:
    k = K
    r = C
    H = r["H"]
    rows = [
        ("R1", "reproduction", "Adverse multiplier 2.118175", f"{r['bases']['list-adverse']['engine']['multiplier']:.6f}", "reproduced"),
        ("R2", "reproduction", "Extreme multiplier 1.383141", f"{r['bases']['list-extreme']['engine']['multiplier']:.6f}", "reproduced"),
        ("R3", "reproduction", "fast run refused at 30 days", "refused", "reproduced"),
        ("R4", "reproduction", "modelled 2-day loss 0.17083", f"{r['labelled_run']['svb_modelled_2d']:.5f}", "reproduced"),
        ("R5", "reproduction", "round trip of the threshold", "SP 30, just below 31", "reproduced"),
        ("H1", "outcome equals the oracle's", "0 disagreements", f"{k['H1']['disagreements']} of {k['H1']['instances']:,}", "held"),
        ("H2", "threshold within the rounding step", "0 to $10^{-6}$ above the root", f"{k['H2']['diff_min'] * 1e6:.3f} to {k['H2']['diff_max'] * 1e6:.3f} $\\times10^{{-6}}$", "held"),
        ("H3", "exact round trip: flat capacity; schedule", "$\\ge$99\\%; $\\ge$5\\% with a gap", f"{pc(k['H3']['monotone']['rate'])}\\%; {pc(k['H3']['growing']['rate'])}\\%", "held"),
        ("H4", "case grid overshoots by more than 10\\%", "$\\ge$30\\% of the solved instances it answers", f"{pc(k['H4']['rate'])}\\%", "held"),
        ("H5", "Brent on SP misses the threshold", "$\\ge$10\\% of solved", f"{pc(k['H5']['rate_of_all_solved'])}\\%", "held"),
        ("H6", "SP(1)/T within 10\\% of the threshold", "$\\ge$80\\%, flat capacity", f"{pc(k['H6']['rate'])}\\%", "failed"),
        ("H7", "derivative equals finite difference", "within 1\\%", f"{100 * max(H['H7'].values()):.4f}\\%", "held"),
        ("H8", "Adverse multiplier within 25\\% over the band", "$<$25\\%", f"{pc(H['H8_joint_max_rel_deviation'])}\\%", "failed"),
        ("H9", "uninsured as legal entities: refusal", "refused", "refused", "held"),
        ("H10", "2-day outflow reaches the amber bar", "ratio $\\ge$0.5", f"{H['H10_ratio_2d']:.3f}", "failed"),
        ("H11", "labelled multiplier $\\ge2\\times$ that bringing SP to at most 2 days", "$\\ge$2", f"{H['H11_ratio']:.2f}", "held"),
        ("H12", "other calibration rules stay below amber", "ratio $<$0.5", f"{H['H12_max_ratio_other_rules']:.3f}", "held"),
    ]
    body = [f"{a} & {b} & {c} & {d} & {e} \\\\" for a, b, c, d, e in rows]
    write("hypotheses", tab("Reproductions and predictions with the value each one took. R1 to R5 restate values committed before the design document named them; H1 to H12 were written into a file whose modification time precedes that of the three result files (\\cref{sec:experimental-design}). "
                            "Three predictions failed (H6, H8, H10): the hyperbolic rule, the stability of the Adverse multiplier over the joint convention band, and the amber bar of the labelled run.",
                            "tab:hypotheses", body, "lp{4.6cm}p{3.0cm}p{3.4cm}l", "Id & Statement & Criterion & Measured & Outcome", star=True))


if __name__ == "__main__":
    notation()
    design()
    main_results()
    ablation()
    band()
    labelled()
    hypotheses()
    spread()
    theory_checks()
    mn.write()
    print("tables written to", OUT)
