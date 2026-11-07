"""Every table of the manuscript, written to ``tables/`` from the experiment results (``experiments/results``) and the committed
documents of cases C20 and C21 (``data/derived``), through the booktabs writer of ``manuscripts/_shared/figkit.py``.

Usage, from the repository root: python manuscripts/measured-corrections-of-validation-tests/make_tables.py
"""
from __future__ import annotations

import glob
import math

import numpy as np

import _data as D
import exp_coverage
import exp_shift
import exp_situation
import exp_situation_indep
from _data import PAIRS, cov_cell, figkit, pm, shift_cell, sit_cell, sit_indep_cell

T = D.TABLES
LEVEL = 0.05


def _passthrough(cell):
    """A text cell that holds math is passed to LaTeX as written: figkit escapes any cell that does not start with ``$`` or a backslash."""
    if isinstance(cell, str) and "$" in cell and not cell.startswith(("$", "\\")):
        return "\\relax " + cell
    return cell


def table(name: str, header, rows, **kw) -> None:
    """Write the booktabs table, then scale the tabular down to the text width when it is wider (``\\fitwidth`` of the shared preamble)."""
    path = figkit.table(T / f"{name}.tex", header, [[_passthrough(c) for c in r] for r in rows], **kw)
    text = path.read_text(encoding="utf-8")
    text = text.replace("\\begin{tabular}", "\\fitwidth{\\begin{tabular}", 1).replace("\\end{tabular}", "\\end{tabular}}", 1)
    path.write_text(text, encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------------------------------------------------
def design() -> None:
    rows = [
        ["Coverage test", "\\texttt{conformal\\_}\\allowbreak\\texttt{coverage}", "uniform scores, calibration $n$ in 200, 1,000, 5,000; $m/n$ from 0.1 to 8",
         f"{len(exp_coverage.cells())}", f"{exp_coverage.REPS:,}"],
        ["Resilience test", "\\texttt{shift\\_}\\allowbreak\\texttt{development\\_}\\allowbreak\\texttt{reference}", "\\texttt{CovariateShiftPlant}, evaluation 125 to 1,000, shift 0 to 3",
         f"{len(exp_shift.CELLS)}", f"{exp_shift.REPS}"],
        ["Situation light", "\\texttt{situation\\_}\\allowbreak\\texttt{test}", "\\texttt{ThresholdBiasPlant}, 400 and 1,000 applicants, gap 0 to 0.8, $k=30$",
         f"{len(exp_situation.NS) * len(exp_situation.GAPS)}", f"{exp_situation.REPS_NULL:,} (gap 0), {exp_situation.REPS_GAP} (others)"],
        ["Situation light, second design", "\\texttt{situation\\_}\\allowbreak\\texttt{test}", "two independent uniform attributes, 400 and 1,000 applicants, bias 0 to 0.4, $k=30$",
         f"{len(exp_situation_indep.NS) * len(exp_situation_indep.BIASES)}", f"{exp_situation_indep.REPS_NULL:,} (bias 0), {exp_situation_indep.REPS_BIAS} (others)"],
    ]
    table("design", ["Experiment", "Engine function", "Data and grid", "Cells", "Replications per cell"], rows,
          caption="The four experiments: the engine function each one calls, the seeded generator and the grid of settings it runs, the number of "
                  "cells and the replications of each cell; every rate of the results carries the standard error of its replications.",
          label="tab:design", align=">{\\raggedright\\arraybackslash}p{2.4cm}>{\\raggedright\\arraybackslash}p{3.2cm}>{\\raggedright\\arraybackslash}p{5.6cm}r>{\\raggedright\\arraybackslash}p{2.8cm}")


# ---------------------------------------------------------------------------------------------------------------------
def main_results() -> None:
    rows = []
    for tag, label in (("A", "0.1"), ("B", "1"), ("C", "4")):
        n, m = PAIRS[tag]
        null, drift = cov_cell(n, m, 1.0), cov_cell(n, m, 1.10)
        for rule, name in (("bin", "binomial p-value"), ("bb", "Beta-Binomial p-value")):
            rows.append(["Coverage", f"{name}, $m/n = {label}$", pm(null["rates"][rule]), pm(drift["rates"][rule]), "shape $b=1.10$"])
    e = shift_cell(500, 0.0)
    p = shift_cell(500, 2.0)
    for rule, name in (("fixed_0.05", "fixed drop above 0.05"), ("fixed_0.10", "fixed drop above 0.10"), ("z_rule", "variance z rule"),
                       ("perm_199", "permutation reference, 199 draws")):
        rows.append(["Resilience", name, pm(e["rules"][rule]), pm(p["rules"][rule]), "shift 2"])
    s0, s4 = sit_cell(400, 0.0), sit_cell(400, 0.4)
    for rule, name in (("cut_0.1", "share cut 0.10"), ("cut_0.2", "share cut 0.20")):
        rows.append(["Situation", name, pm(s0["rules"][rule]), pm(s4["rules"][rule]), "gap 0.4"])
    table("main_results", ["Test", "Rule", "Size (no defect)", "Power (planted defect)", "Defect"], rows,
          caption="The rejection rate of each rule on data without a defect (size, level 0.05) and with a planted defect (power), each with its Monte Carlo "
                  "standard error, for the three tests: the coverage test at three window ratios, the resilience test with 500 evaluation rows and the situation "
                  "light with 400 applicants.",
          label="tab:main-results", align="llccl", wide=False)


# ---------------------------------------------------------------------------------------------------------------------
def exact_size() -> None:
    rows = []
    for n in exp_coverage.SIZE_NS:
        for r in (0.1, 0.5, 1.0, 2.0, 4.0, 8.0):
            m = int(round(r * n))
            c = cov_cell(n, m, 1.0)
            rows.append([f"{n:,}", f"{m:,}", f"{m / n:.1f}", f"{c['exact']['bin']:.4f}", f"{c['normal_approx_binomial']:.4f}", pm(c["rates"]["bin"]),
                         f"{c['exact']['bb']:.4f}", pm(c["rates"]["bb"])])
    table("exact_size", ["$n$", "$m$", "$m/n$", "Binomial, exact", "Binomial, normal", "Binomial, simulated", "Beta-Binomial, exact", "Beta-Binomial, simulated"], rows,
          caption="The size of the binomial and of the Beta-Binomial coverage test at level 0.05 for calibration windows of 200, 1,000 and 5,000 rows and test windows "
                  "from 0.1 to 8 times as long: the exact sum of the Beta-Binomial law, the normal approximation of the binomial size, and the engine's functions on "
                  f"{exp_coverage.REPS:,} seeded replications with the standard error.",
          label="tab:exact-size", align="rrrccccc", wide=False)


# ---------------------------------------------------------------------------------------------------------------------
COVERAGE_VARIANTS = (("bin", "binomial p-value (published practice)"), ("bb", "Beta-Binomial p-value, minimum-likelihood rule (proposed)"),
                     ("bb_eqtail", "Beta-Binomial, equal-tail p-value"), ("z_inflated", "normal test with the variance ratio of Proposition 2"),
                     ("bb_n_half", "Beta-Binomial with the calibration size halved"), ("bb_n_double", "Beta-Binomial with the calibration size doubled"),
                     ("bin_oracle", "binomial with the exact size-calibrated cut"))


def coverage_ablation() -> None:
    rows = []
    for rule, name in COVERAGE_VARIANTS:
        row = [name]
        for tag in ("B", "C"):
            n, m = PAIRS[tag]
            row += [pm(cov_cell(n, m, 1.0)["rates"][rule]), pm(cov_cell(n, m, 1.05)["rates"][rule]), pm(cov_cell(n, m, 1.10)["rates"][rule])]
        rows.append(row)
    table("coverage_ablation", ["Variant", "Size", "Power, $b=1.05$", "Power, $b=1.10$", "Size ", "Power, $b=1.05$ ", "Power, $b=1.10$ "], rows,
          caption="The components of the coverage test removed or changed one at a time on the same covered counts: the size and the power at two shapes of drift for "
                  "equal windows (the first three columns) and for a test window four times the calibration window (the last three); simulated rates with their standard errors.",
          label="tab:coverage-ablation", align="p{5.2cm}cccccc", wide=False)


# ---------------------------------------------------------------------------------------------------------------------
SHIFT_RULES = (("fixed_0.05", "fixed drop above 0.05"), ("fixed_0.10", "fixed drop above 0.10"), ("z_rule", "variance z rule"),
               ("perm_19", "permutation reference, 19 draws"), ("perm_39", "permutation reference, 39 draws"),
               ("perm_99", "permutation reference, 99 draws"), ("perm_199", "permutation reference, 199 draws"))


def shift_ablation() -> None:
    rows = []
    for rule, name in SHIFT_RULES:
        rows.append([name] + [pm(shift_cell(500, s)["rules"][rule]) for s in (0.0, 1.0, 2.0, 3.0)])
    rows.append(["fixed drop above the 95th percentile of the null drops"] + [pm(D.oracle_fixed(500, s)) for s in (0.0, 1.0, 2.0, 3.0)])
    table("shift_ablation", ["Rule", "Size (shift 0)", "Power (shift 1)", "Power (shift 2)", "Power (shift 3)"], rows,
          caption="The rejection rate of each rule of the resilience test with 500 evaluation rows, 1,000 development rows and the worst quarter as the subsample: the size "
                  "without shift and the power at three planted shifts, with the permutation reference read at four numbers of draws; rates with their standard errors.",
          label="tab:shift-ablation", align="lcccc", wide=False)


def shift_eval_size() -> None:
    rows = []
    for rule, name in (("fixed_0.05", "fixed 0.05"), ("fixed_0.10", "fixed 0.10"), ("z_rule", "z rule"), ("perm_199", "permutation, 199")):
        for kind, s in (("size", 0.0), ("power", 2.0)):
            rows.append([name, kind] + [pm(shift_cell(e, s)["rules"][rule]) for e in exp_shift.EVAL_SIZES])
    table("shift_eval_size", ["Rule", "Rate", "$n_{\\mathrm{eval}}=125$", "250", "500", "1,000"], rows,
          caption="The size (shift 0) and the power (shift 2) of four rules of the resilience test as the evaluation sample grows from 125 to 1,000 rows, with the development "
                  "sample twice as large; rates with their standard errors over the replications of each cell.",
          label="tab:shift-eval-size", align="llcccc", wide=False)


# ---------------------------------------------------------------------------------------------------------------------
SIT_RULES = (("cut_0.05", "share cut 0.05"), ("cut_0.075", "share cut 0.075"), ("cut_0.1", "share cut 0.10"), ("cut_0.15", "share cut 0.15"),
             ("cut_0.2", "share cut 0.20"), ("cut_0.25", "share cut 0.25"), ("cut_0.3", "share cut 0.30"),
             ("count_binomial", "binomial test of the count"), ("bonferroni_any", "one significant at the Bonferroni level"))


def situation_ablation() -> None:
    rows = []
    worst = 0.0
    for rule, name in SIT_RULES:
        row = [name]
        for n in (400, 1000):
            for g in (0.0, 0.2, 0.4):
                r = sit_cell(n, g)["rules"][rule]
                worst = max(worst, r["se"])
                row.append(f"{r['rate']:.3f}")
        rows.append(row)
    table("situation_ablation", ["Rule", "$n=400$, gap 0", "gap 0.2", "gap 0.4", "$n=1{,}000$, gap 0", "gap 0.2", "gap 0.4"], rows,
          caption="The rejection rate of nine rules of the situation-testing light: the size (gap 0) and the power at two planted gaps for 400 and for 1,000 applicants, with "
                  f"the standard error of every rate at most {worst:.3f} over 1,000 replications at gap 0 and 400 at the others.",
          label="tab:situation-ablation", align="lcccccc", wide=False)


# ---------------------------------------------------------------------------------------------------------------------
def situation_designs() -> None:
    rows = []
    for design_name, cell in (("threshold-bias plant", sit_cell), ("independent attributes", sit_indep_cell)):
        for n in (400, 1000):
            c0 = cell(n, 0.0)
            row = [design_name, f"{n:,}", f"{c0['mean_complainants']:.0f}", f"{c0['mean_share']:.3f}", f"{c0['sd_share']:.3f}", f"{c0['design_effect']:.1f}"]
            for rule in ("cut_0.1", "cut_0.2"):
                row.append(pm(c0["rules"][rule]))
            rows.append(row)
    table("situation_designs", ["Design", "Applicants", "Complainants", "Mean share", "SD of share", "Design effect", "Size, cut 0.10", "Size, cut 0.20"], rows,
          caption="The null law of the share of significant complainants and the size of the amber cuts 0.10 and 0.20 on two planted designs without bias, for 400 and for "
                  "1,000 applicants: the mean number of complainants, the mean and standard deviation of the share, the variance of the count over the binomial variance, "
                  "and the size with its Monte Carlo standard error over 1,000 and 2,000 replications.",
          label="tab:situation-designs", align="llrrrrcc", wide=False)


# ---------------------------------------------------------------------------------------------------------------------
def committed() -> dict:
    """The committed rows of C20 and C21, with the engine's function recomputing every conformal p-value from its counts."""
    from riskvalidation.ml import conformal

    fed = D.jload(D.figkit.ROOT / "data" / "derived" / "C20" / "fed-shift.json")
    rows, worst, out = [], 0.0, {}
    for t in fed["tests"]:
        if t["test_id"] != "ml.conformal_coverage":
            continue
        x = t["extras"]
        m, c = t["n"], int(round(t["metric"] * t["n"]))
        res = conformal.conformal_coverage(np.column_stack([np.arange(m) < c, np.zeros(m, dtype=bool)]), np.zeros(m, dtype=int), 0.1, n_cal=x["n_cal"])
        worst = max(worst, abs(math.log10(res.p_value) - math.log10(t["p_value"])), abs(math.log10(res.p_value_binomial) - math.log10(x["p_value_binomial"])))
        rows.append([t["segment"].replace("window:", "").replace("fed-higher-risk-", "higher risk "), f"{x['n_cal']:,}", f"{m:,}", f"{t['metric']:.4f}",
                     f"{t['p_value']:.3g}", f"{x['p_value_binomial']:.3g}", t["light"]])
        out[t["segment"]] = {"p_bb": t["p_value"], "p_bin": x["p_value_binomial"], "coverage": t["metric"], "m": m, "n_cal": x["n_cal"]}
    table("committed_conformal", ["Window", "$n$", "$m$", "Coverage", "$p$ Beta-Binomial", "$p$ binomial", "Light"], rows,
          caption="The conformal coverage rows of the committed shift variant of the gradient-boosting model fitted on the Polish company bankruptcy data, evaluated on the locked holdout "
                  "shifted by sizes taken from the Federal Reserve corporate portfolios: the calibration and test sizes, the empirical coverage against the target 0.90, both p-values of the "
                  "engine and the light the Beta-Binomial p-value sets; the light never reads the binomial one.",
          label="tab:committed-conformal", align="lrrcccl")
    res_row = next(t for t in fed["tests"] if t["test_id"] == "ml.shift_resilience")
    out["resilience"] = {"drop": res_row["metric"], "p": res_row["p_value"], "n": res_row["n"], "draws": res_row["extras"]["shift_permutations"],
                         "null_mean": res_row["extras"]["null_mean"], "null_p95": res_row["extras"]["null_p95"], "light": res_row["light"]}
    rows2, shares = [], []
    for path in sorted(glob.glob(str(D.figkit.ROOT / "data" / "derived" / "C21" / "pair-*.json"))):
        h = D.jload(D.pathlib.Path(path))
        t = next(t for t in h["tests"] if t["test_id"] == "fair.situation_testing")
        x = t["extras"]
        rows2.append([h["variant_id"].replace("pair-", ""), f"{x['n_complainants']:,}", f"{x['n_significant']:,}", f"{t['metric']:.4f}", f"{x['thresholds']['amber']:.2f}", t["light"]])
        shares.append((h["variant_id"], t["metric"], t["light"]))
    table("committed_fair", ["Year pair", "Complainants", "Significant", "Share", "Amber cut", "Light"], rows2,
          caption="The situation-testing row of each committed Delaware mortgage year pair: the complainants of the protected group, how many are significant at level 0.05 with "
                  "thirty neighbours, their share, the amber cut point the engine applies and the light that follows; the light is never red.",
          label="tab:committed-fair", align="lrrccl")
    out["pairs"] = shares
    out["max_log10_p_difference"] = worst
    return out


# ---------------------------------------------------------------------------------------------------------------------
def notation() -> None:
    rows = [
        ["$\\alpha$", "miscoverage of the conformal set, 0.10", "dimensionless"],
        ["$n$", "calibration rows of the conformal set", "rows"],
        ["$m$", "test rows whose coverage is read", "rows"],
        ["$k$", "rank of the conformal quantile, $\\lceil (n+1)(1-\\alpha)\\rceil$", "dimensionless"],
        ["$C$", "number of test rows whose set holds the true label", "rows"],
        ["$V$", "coverage of the set given the calibration rows", "dimensionless"],
        ["$\\mu_0$", "target coverage $1-\\alpha$", "dimensionless"],
        ["$b$", "shape of the drift of the test scores, $\\Prob(\\text{coverage})=q^b$", "dimensionless"],
        ["$\\delta_s$", "shift of the covariates of the shifted rows", "standard deviations"],
        ["$s$", "share of the evaluation rows in the worst subsample, 0.25", "dimensionless"],
        ["$D$", "AUC drop on the worst subsample, $\\mathrm{AUC}_{\\mathrm{all}}-\\mathrm{AUC}_{\\mathrm{worst}}$", "AUC points"],
        ["$R$", "permutation draws of the reference", "draws"],
        ["$\\gamma$", "gap of the group-dependent decision cut-off", "log-odds"],
        ["$k_{\\mathrm{nn}}$", "neighbours of each complainant in each group, 30", "rows"],
        ["$S$", "share of significant complainants", "dimensionless"],
        ["$c_0$", "amber cut point of the share", "dimensionless"],
        ["$\\theta$", "level of every test, 0.05", "dimensionless"],
    ]
    table("notation", ["Symbol", "Meaning", "Unit"], rows,
          caption="The notation of the manuscript: the symbols of the coverage test, the resilience test and the situation-testing light, their meaning and their unit; a symbol "
                  "that two sections share has the same meaning in both.",
          label="tab:notation", align="lll")


def main() -> None:
    design()
    main_results()
    exact_size()
    coverage_ablation()
    shift_ablation()
    shift_eval_size()
    situation_ablation()
    situation_designs()
    committed()
    notation()
    print("tables written to", T)


if __name__ == "__main__":
    main()
