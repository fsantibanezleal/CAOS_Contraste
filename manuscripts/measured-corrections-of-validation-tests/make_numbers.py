"""The number macros of the manuscript: every number the prose quotes is a macro defined in ``tables/numbers.tex`` from the experiment
results and the committed documents, so that the text cannot differ from the script output it cites. Also writes
``tables/hypotheses.tex`` (each prediction, its measured value and whether it held) and ``numbers-index.json``, the list of every
macro with its value and the result it comes from (the traceability of the manuscript).

Usage, from the repository root: python manuscripts/measured-corrections-of-validation-tests/make_numbers.py
(run make_tables.py first: this script reads ``tables/committed_*.tex`` only through the same sources).
"""
from __future__ import annotations

import json
import math
import re

import numpy as np
from scipy import stats

import _data as D
import exp_coverage
import exp_shift
import exp_situation
import exp_situation_indep
from _data import COVERAGE, EXACT, PAIRS, SHIFT, SITUATION, SITUATION_INDEP, cov_cell, figkit, shift_cell, sit_cell, sit_indep_cell

NUM: dict[str, tuple[str, str]] = {}
THETA = 0.05


def put(name: str, text: str, source: str) -> None:
    if not re.fullmatch(r"[A-Za-z]+", name):
        raise ValueError(f"macro name {name!r} is not letters only")
    if name in NUM:
        raise ValueError(f"macro {name} defined twice")
    NUM[name] = (text, source)


def f3(x: float) -> str:
    return f"{x:.3f}"


def f4(x: float) -> str:
    return f"{x:.4f}"


def sci(x: float, digits: int = 2) -> str:
    mant, exp = f"{x:.{digits}e}".split("e")
    return f"${mant} \\times 10^{{{int(exp)}}}$"


def thousands(n: int) -> str:
    return f"{n:,}"


# ---------------------------------------------------------------------------------------------------------------------
SHAPE = {1.02: "Two", 1.05: "Five", 1.10: "Ten", 1.20: "Twenty"}
RULE_COV = {"bin": "Bin", "bb": "BB", "bb_eqtail": "Eq", "z_inflated": "Zinf", "bb_n_half": "Half", "bb_n_double": "Double", "bin_oracle": "Oracle"}


def coverage_macros() -> None:
    src = "experiments/results/coverage.json"
    for tag, (n, m) in PAIRS.items():
        null = cov_cell(n, m, 1.0)
        for rule, code in RULE_COV.items():
            r = null["rates"][rule]
            put(f"CovSin{code}{tag}", f3(r["rate"]), f"{src}: n={n}, m={m}, b=1, {rule}")
            put(f"CovSe{code}{tag}", f3(r["se"]), f"{src}: n={n}, m={m}, b=1, {rule}")
            for b, bn in SHAPE.items():
                if b == 1.02 and rule not in ("bin", "bb"):
                    continue
                c = cov_cell(n, m, b)
                put(f"CovPow{code}{tag}{bn}", f3(c["rates"][rule]["rate"]), f"{src}: n={n}, m={m}, b={b}, {rule}")
                put(f"CovPowSe{code}{tag}{bn}", f3(c["rates"][rule]["se"]), f"{src}: n={n}, m={m}, b={b}, {rule}")
        put(f"CovExBin{tag}", f3(null["exact"]["bin"]), f"{src}: exact sum, n={n}, m={m}")
        put(f"CovExBB{tag}", f3(null["exact"]["bb"]), f"{src}: exact sum, n={n}, m={m}")
        put(f"CovNormalBin{tag}", f3(null["normal_approx_binomial"]), f"{src}: normal approximation, n={n}, m={m}")
        for b, bn in SHAPE.items():
            put(f"CovMean{tag}{bn}", f3(cov_cell(n, m, b)["mean_coverage"]), f"{src}: mean coverage, n={n}, m={m}, b={b}")
        put(f"CovOracleCut{tag}", f"{null['oracle_threshold']:.4f}" if null["oracle_threshold"] >= 1e-3 else sci(null["oracle_threshold"], 1), f"{src}: size-calibrated binomial cut, n={n}, m={m}")
    size_cells = [c for c in COVERAGE["cells"] if c["b"] == 1.0 and "exact" in c]
    grid = [c for c in size_cells if c["n"] in exp_coverage.SIZE_NS and any(abs(c["ratio"] - r) < 1e-9 for r in exp_coverage.SIZE_RATIOS)]
    put("CovGridCells", str(len(grid)), f"{src}: the size grid")
    put("CovTotalCells", str(len(COVERAGE["cells"])), f"{src}: all cells")
    put("CovTotalReps", thousands(sum(c["reps"] for c in COVERAGE["cells"])), f"{src}: replications over all cells")
    put("CovReps", thousands(COVERAGE["meta"]["reps"]), f"{src}: replications per cell")
    ver = COVERAGE["meta"]["versions"]
    tm = json.loads((D.RESULTS / "timings.json").read_text(encoding="utf-8"))
    tsrc = "experiments/results/timings.json"
    for key, nm in (("coverage", "Cov"), ("shift", "Shift"), ("situation", "Sit"), ("situation_indep", "SitIn")):
        put(f"Time{nm}Min", f"{tm[key]['seconds'] / 60.0:.1f}", f"{tsrc}: wall time of the cold run of {key}, minutes")
    put("TimeExactSec", f"{tm['exact']['seconds']:.0f}", f"{tsrc}: wall time of exact_theory.py, seconds")
    put("TimeWorkers", str(tm["shift"]["workers"]), f"{tsrc}: worker processes of the cold runs")
    put("TimeCpus", str(tm["shift"]["cpu_count"]), f"{tsrc}: logical cores of the machine of the cold runs")
    assert len({tm[k]["workers"] for k in ("coverage", "shift", "situation", "situation_indep")}) == 1
    put("EnvEngine", ver["riskvalidation"], f"{src}: meta.versions.riskvalidation")
    put("EnvNumpy", ver["numpy"], f"{src}: meta.versions.numpy")
    put("EnvScipy", ver["scipy"], f"{src}: meta.versions.scipy")
    put("RootSeed", str(COVERAGE["meta"]["base_seed"]), f"{src}: meta.base_seed")
    put("CovEngineMismatches", str(sum(c["engine_mismatches"] for c in COVERAGE["cells"])), f"{src}: engine p-value against the vectorised p-value")
    put("CovBBMaxExact", f4(max(c["exact"]["bb"] for c in size_cells)), f"{src}: maximum exact Beta-Binomial size over the size cells")
    put("CovBBMaxRate", f3(max(c["rates"]["bb"]["rate"] for c in grid)), f"{src}: maximum simulated Beta-Binomial size over the size grid")
    viol = [c for c in grid if c["rates"]["bb"]["rate"] > THETA + 2 * c["rates"]["bb"]["se"]]
    put("CovBBOverBound", str(len(viol)), f"{src}: size-grid cells where the Beta-Binomial rate exceeds 0.05 plus two standard errors")
    worst = max(abs(c["rates"][r]["rate"] - c["exact"][r]) / max(c["rates"][r]["se"], 1e-9) for c in size_cells for r in ("bin", "bb"))
    put("CovMcExactMaxZ", f"{worst:.1f}", f"{src}: largest simulated minus exact size in standard errors")
    put("CovNormalMaxErr", f3(max(abs(c["exact"]["bin"] - c["normal_approx_binomial"]) for c in size_cells)), f"{src}: largest exact minus normal binomial size")
    bins1 = [c["exact"]["bin"] for c in grid if c["ratio"] == 1.0]
    bins4 = [c["exact"]["bin"] for c in grid if c["ratio"] == 4.0]
    bins8 = [c["exact"]["bin"] for c in grid if c["ratio"] == 8.0]
    bins01 = [c["exact"]["bin"] for c in grid if c["ratio"] == 0.1]
    for nm, v in (("One", bins1), ("Four", bins4), ("Eight", bins8), ("Tenth", bins01)):
        put(f"CovExBinMin{nm}", f3(min(v)), f"{src}: exact binomial size, ratio {nm}")
        put(f"CovExBinMax{nm}", f3(max(v)), f"{src}: exact binomial size, ratio {nm}")
    # the size of the binomial test at the ratios of the size grid, simulated
    for ratio, nm in ((1.0, "One"), (4.0, "Four")):
        v = [c["rates"]["bin"]["rate"] for c in grid if c["ratio"] == ratio]
        put(f"CovSimBinMin{nm}", f3(min(v)), f"{src}: simulated binomial size, ratio {ratio}")
        put(f"CovSimBinMax{nm}", f3(max(v)), f"{src}: simulated binomial size, ratio {ratio}")
    # the BB test is conservative at small windows: exact size for the smallest ratio
    small = [c for c in grid if c["ratio"] == 0.1]
    put("CovExBBMinTenth", f3(min(c["exact"]["bb"] for c in small)), f"{src}: exact Beta-Binomial size at ratio 0.1")
    put("CovExBBMaxTenth", f3(max(c["exact"]["bb"] for c in small)), f"{src}: exact Beta-Binomial size at ratio 0.1")
    # an off-by-one rank, exact
    for (n, m), nm in (((1000, 1000), "One"), ((1000, 4000), "Four")):
        t = exp_coverage.tables(n, m)
        k = exp_coverage.rank(n)
        law_off = stats.betabinom.pmf(np.arange(m + 1), m, k + 1, n - k)
        put(f"RankOffBB{nm}", f3(float(law_off[t["bb"] < THETA].sum())), f"exact: Beta-Binomial test of rank k on a law of rank k+1, n={n}, m={m}")
        put(f"RankOffBin{nm}", f3(float(law_off[t["bin"] < THETA].sum())), f"exact: binomial test on a law of rank k+1, n={n}, m={m}")
    vr = EXACT["variance_ratio"]
    put("VarRatioMaxErr", sci(vr["max_abs_error"], 1), "experiments/results/exact.json: variance ratio")
    for row, nm in zip(vr["rows"], ("A", "B", "C", "D", "E")):
        put(f"VarRatio{nm}", f3(row["ratio_exact"]), f"exact.json: variance ratio n={row['n']}, m={row['m']}")
    put("PowerExactMaxGap", f3(max(abs(p["power"]["bb"] - cov_cell(p["n"], p["m"], round(p["b"], 2))["rates"]["bb"]["rate"])
                                   for p in EXACT["power_curves"] if any(abs(p["b"] - b) < 1e-9 for b in SHAPE))),
        "exact.json power curve against coverage.json simulated power, Beta-Binomial")
    # power of the oracle-calibrated binomial against the Beta-Binomial, exact
    for tag in ("B", "C"):
        n, m = PAIRS[tag]
        rows = [p for p in EXACT["power_curves"] if p["n"] == n and p["m"] == m and abs(p["b"] - 1.10) < 1e-9]
        put(f"ExPowBB{tag}Ten", f3(rows[0]["power"]["bb"]), f"exact.json: exact power b=1.10, n={n}, m={m}")
        put(f"ExPowOracle{tag}Ten", f3(rows[0]["power"]["bin_oracle"]), f"exact.json: exact power b=1.10, n={n}, m={m}")
        put(f"ExPowBin{tag}Ten", f3(rows[0]["power"]["bin"]), f"exact.json: exact power b=1.10, n={n}, m={m}")
    names = {19: "Nineteen", 39: "ThirtyNine", 99: "NinetyNine", 199: "Full"}
    for g in EXACT["granularity"]:
        put(f"GranSmallest{names[g['draws']]}", f3(g["smallest_p"]), "exact.json: granularity")
        put(f"GranAllowed{names[g['draws']]}", str(g["max_null_draws_above_observed"]), "exact.json: granularity")
        put(f"GranExact{names[g['draws']]}", f"{(g['max_null_draws_above_observed'] + 1) / (g['draws'] + 1):.3f}",
            "exact.json: granularity, the exact size (number of attainable p-values below 0.05) over R + 1")
    # the limit of the size of the binomial test when n grows with m / n fixed at r (Proposition 4)
    for r, nm in ((0.1, "Tenth"), (1.0, "One"), (4.0, "Four"), (8.0, "Eight")):
        put(f"LimBin{nm}", f3(float(2.0 * stats.norm.sf(1.959964 / math.sqrt(1.0 + r)))), f"Proposition 4: 2 Phi(-1.96 / sqrt(1 + r)) at r = {r}")
    put("ExPowGapMax", f3(max(abs(p["power"]["bb"] - p["power"]["bin_oracle"]) for p in EXACT["power_curves"])),
        "exact.json power curves: largest difference between the exact power of the Beta-Binomial test and of the size-calibrated binomial test")
    put("CovMcCompare", str(2 * len(size_cells)), f"{src}: simulated against exact size comparisons (two rules, every size cell)")
    # the acceptance region of each test at n = m = 1000 (the counts whose p-value is at least 0.05), as shares of the window
    t11 = exp_coverage.tables(1000, 1000)
    for rule, nm in (("bin", "Bin"), ("bb", "BB")):
        accept = np.flatnonzero(t11[rule] >= THETA)
        put(f"Region{nm}Lo", f3(accept.min() / 1000), f"exact: lowest accepted coverage at n = m = 1000, {rule}")
        put(f"Region{nm}Hi", f3(accept.max() / 1000), f"exact: highest accepted coverage at n = m = 1000, {rule}")
    put("RedMinDraws", str(next(r for r in range(1, 10**4) if 1.0 / (r + 1) < 0.01)), "smallest number of draws whose smallest p-value 1 / (R + 1) is below the red level 0.01")
    put("ExPowGapCells", str(len(EXACT["power_curves"])), "exact.json power curves: cells (window pair and drift shape)")
    put("ExPowPairs", str(len({(p["n"], p["m"]) for p in EXACT["power_curves"]})), "exact.json power curves: window pairs")
    put("ExPowShapes", str(len({p["b"] for p in EXACT["power_curves"]})), "exact.json power curves: drift shapes")
    put("ExPowNodes", thousands(EXACT["meta"]["nodes"]), "exact.json: quantiles of the Beta law used by the midpoint rule")
    put("VarRatioPairs", str(len(vr["rows"])), "exact.json: window pairs of the variance comparison")
    # the pooled size of the permutation reference over the four evaluation sizes, against the exact size of the p-value grid
    for r, nm in ((19, "Nineteen"), (39, "ThirtyNine"), (99, "NinetyNine"), (199, "Full")):
        rates = [c["rules"][f"perm_{r}"] for c in SHIFT["cells"] if c["shift"] == 0.0]
        put(f"ShPermPooled{nm}", f3(sum(x["rate"] for x in rates) / len(rates)), f"shift.json: mean size over the four evaluation sizes, {r} draws")
        put(f"ShPermPooledSe{nm}", f3(math.sqrt(sum(x["se"] ** 2 for x in rates)) / len(rates)), f"shift.json: standard error of that mean, {r} draws")


# ---------------------------------------------------------------------------------------------------------------------
RULE_SH = {"fixed_0.05": "FixedFive", "fixed_0.10": "FixedTen", "z_rule": "Zrule", "perm_19": "PermNineteen", "perm_39": "PermThirtyNine",
           "perm_99": "PermNinetyNine", "perm_199": "Perm"}
EVAL_CODE = {125: "A", 250: "B", 500: "C", 1000: "D"}
SHIFT_CODE = {0.0: "Z", 1.0: "O", 2.0: "T", 3.0: "H"}


def shift_macros() -> None:
    src = "experiments/results/shift.json"
    put("ShReps", str(SHIFT["meta"]["reps"]), f"{src}: replications per cell")
    put("ShTotalReps", thousands(sum(c["n"] + c["skipped"] for c in SHIFT["cells"])), f"{src}: replications over all cells")
    put("ShCells", str(len(SHIFT["cells"])), f"{src}: cells")
    for c in SHIFT["cells"]:
        e, s = EVAL_CODE[c["n_eval"]], SHIFT_CODE[c["shift"]]
        tagsrc = f"{src}: eval {c['n_eval']}, shift {c['shift']}"
        for rule, code in RULE_SH.items():
            put(f"ShRate{code}{e}{s}", f3(c["rules"][rule]["rate"]), tagsrc + f", {rule}")
            put(f"ShSe{code}{e}{s}", f3(c["rules"][rule]["se"]), tagsrc + f", {rule}")
        put(f"ShMeanDrop{e}{s}", f3(c["mean_drop"]), tagsrc)
        put(f"ShSdDrop{e}{s}", f3(c["sd_drop"]), tagsrc)
        put(f"ShQNinetyFive{e}{s}", f3(c["q95_drop"]), tagsrc)
        put(f"ShNullMean{e}{s}", f4(c["mean_null_mean"]), tagsrc)
        put(f"ShSkipped{e}{s}", str(c["skipped"]), tagsrc)
        put(f"ShN{e}{s}", str(c["n"]), tagsrc)
        draws_total = c["n"] * exp_shift.DRAWS
        put(f"ShUndefPct{e}{s}", f"{100 * c['undefined_draws'] / draws_total:.1f}", tagsrc + ": draws left out for a single-class subsample, percent")
    for s_val, s in SHIFT_CODE.items():
        r = D.oracle_fixed(500, s_val)
        put(f"ShOracleRate{s}", f3(r["rate"]), f"{src}: eval 500, fixed cut at the 95th percentile of the null drops, shift {s_val}")
        put(f"ShOracleSe{s}", f3(r["se"]), f"{src}: eval 500, shift {s_val}")
    put("ShOracleCut", f3(D.oracle_fixed(500, 0.0)["cut"]), f"{src}: eval 500, 95th percentile of the null drops")
    # the perm rule at the three small cells against the nominal bound
    over = [c for c in SHIFT["cells"] if c["shift"] == 0.0 and c["rules"]["perm_199"]["rate"] > THETA + 2 * c["rules"]["perm_199"]["se"]]
    put("ShPermOverBound", str(len(over)), f"{src}: no-shift cells where the permutation rule (199 draws) exceeds 0.05 plus two standard errors")
    over_z = [c for c in SHIFT["cells"] if c["shift"] == 0.0 and c["rules"]["z_rule"]["rate"] > THETA + 2 * c["rules"]["z_rule"]["se"]]
    put("ShZOverBound", str(len(over_z)), f"{src}: no-shift cells where the z rule exceeds 0.05 plus two standard errors")
    put("ShPermPowerGapMin", f3(min(c["rules"]["fixed_0.05"]["rate"] - c["rules"]["perm_199"]["rate"] for c in SHIFT["cells"] if c["shift"] > 0)),
        f"{src}: smallest power of the fixed cut 0.05 minus the power of the permutation rule")
    put("ShShareShifted", "0.25", "the engine plant: a quarter of the evaluation rows is shifted")
    for e_val, e in EVAL_CODE.items():
        c = shift_cell(e_val, 2.0)
        put(f"ShPowGap{e}T", f3(c["rules"]["fixed_0.05"]["rate"] - c["rules"]["perm_199"]["rate"]), f"{src}: eval {e_val}, shift 2, power of the fixed cut 0.05 minus power of the permutation reference")
    c5, c0 = shift_cell(500, 2.0), D.oracle_fixed(500, 2.0)
    se_d = math.sqrt(c5["rules"]["perm_199"]["se"] ** 2 + c0["se"] ** 2)
    put("ShOracleDiffT", f3(c0["rate"] - c5["rules"]["perm_199"]["rate"]), f"{src}: eval 500, shift 2, power of the calibrated fixed cut minus power of the reference")
    put("ShOracleDiffSe", f3(se_d), f"{src}: standard error of that difference (independent rates)")
    put("ShFixedPermDiffT", f3(c5["rules"]["fixed_0.05"]["rate"] - c5["rules"]["perm_199"]["rate"]), f"{src}: eval 500, shift 2, fixed cut 0.05 minus reference")
    put("ShFixedOracleDiffT", f3(c5["rules"]["fixed_0.05"]["rate"] - c0["rate"]), f"{src}: eval 500, shift 2, fixed cut 0.05 minus calibrated fixed cut")
    excess = {}
    for r, nm in ((39, "ThirtyNine"), (99, "NinetyNine"), (199, "Full")):
        rates = [c["rules"][f"perm_{r}"] for c in SHIFT["cells"] if c["shift"] == 0.0]
        pooled = sum(x["rate"] for x in rates) / len(rates)
        se_p = math.sqrt(sum(x["se"] ** 2 for x in rates)) / len(rates)
        exact_r = next(g for g in EXACT["granularity"] if g["draws"] == r)
        ex = (exact_r["max_null_draws_above_observed"] + 1) / (r + 1)
        excess[nm] = (pooled - ex, (pooled - ex) / se_p)
        put(f"ShPermExcess{nm}", f3(pooled - ex), f"{src}: pooled size minus the exact size of the p-value grid, {r} draws")
    zx = []
    for r_, nm in ((39, "ThirtyNine"), (99, "NinetyNine"), (199, "Full")):
        cells0 = [c for c in SHIFT["cells"] if c["shift"] == 0.0]
        exact_r = next(g for g in EXACT["granularity"] if g["draws"] == r_)
        ex = (exact_r["max_null_draws_above_observed"] + 1) / (r_ + 1)
        se_ex = math.sqrt(sum(ex * (1 - ex) / c["n"] for c in cells0)) / len(cells0)
        zx.append(excess[nm][0] / se_ex)
    put("ShPermExcessZExactMin", f"{min(zx):.1f}", f"{src}: that excess in standard errors of the exact null rate sqrt(p (1 - p) / n), minimum")
    put("ShPermExcessZExactMax", f"{max(zx):.1f}", f"{src}: that excess in standard errors of the exact null rate sqrt(p (1 - p) / n), maximum")
    put("ShPermCUpper", f3(THETA + 2 * math.sqrt(THETA * (1 - THETA) / shift_cell(500, 0.0)["n"])), f"{src}: 0.05 plus two exact-null standard errors at 500 rows")
    put("ShPermExcessZMin", f"{min(v[1] for v in excess.values()):.1f}", f"{src}: that excess in standard errors, minimum")
    put("ShPermExcessZMax", f"{max(v[1] for v in excess.values()):.1f}", f"{src}: that excess in standard errors, maximum")


# ---------------------------------------------------------------------------------------------------------------------
RULE_SI = {"cut_0.05": "CutFive", "cut_0.075": "CutSevenFive", "cut_0.1": "CutTen", "cut_0.15": "CutFifteen", "cut_0.2": "CutTwenty",
           "cut_0.25": "CutTwentyFive", "cut_0.3": "CutThirty", "count_binomial": "CountBin", "bonferroni_any": "Bonf"}
N_CODE = {400: "Small", 1000: "Large"}
GAP_CODE = {0.0: "Z", 0.1: "A", 0.2: "B", 0.4: "C", 0.8: "D"}


def rho_bar(c: dict) -> float:
    """The average correlation of the complainant indicators: Var(S) = t0 (1 - t0) [1 + (Q - 1) rho] / Q solved for rho, with t0 the null mean
    share of the cell (not the level 0.05, which the design effect of the result files uses)."""
    q, t0, var = c["mean_complainants"], c["mean_share"], c["sd_share"] ** 2
    return (q * var / (t0 * (1.0 - t0)) - 1.0) / (q - 1.0)


def situation_macros() -> None:
    src = "experiments/results/situation.json"
    put("SiRepsNull", thousands(exp_situation.REPS_NULL), f"{src}: replications at gap 0")
    put("SiRepsGap", str(exp_situation.REPS_GAP), f"{src}: replications at the other gaps")
    for c in SITUATION["cells"]:
        n, g = N_CODE[c["n"]], GAP_CODE[c["gap"]]
        tagsrc = f"{src}: n {c['n']}, gap {c['gap']}"
        for rule, code in RULE_SI.items():
            put(f"SiRate{code}{n}{g}", f3(c["rules"][rule]["rate"]), tagsrc + f", {rule}")
            put(f"SiSe{code}{n}{g}", f3(c["rules"][rule]["se"]), tagsrc + f", {rule}")
        put(f"SiMeanShare{n}{g}", f3(c["mean_share"]), tagsrc)
        put(f"SiSdShare{n}{g}", f3(c["sd_share"]), tagsrc)
        put(f"SiQNinetyFive{n}{g}", f3(c["q95_share"]), tagsrc)
        put(f"SiDesign{n}{g}", f"{c['design_effect']:.1f}", tagsrc + ": design effect")
        put(f"SiComplainants{n}{g}", f"{c['mean_complainants']:.0f}", tagsrc)
        put(f"SiMeanCases{n}{g}", f3(c["mean_share_cases"]), tagsrc)
    for n_val, n in N_CODE.items():
        c = sit_cell(n_val, 0.0)
        for cut, nm in ((0.10, "Ten"), (0.20, "Twenty")):
            pred = float(stats.norm.sf((cut - c["mean_share"]) / c["sd_share"]))
            put(f"SiNormalPred{nm}{n}", f3(pred), f"{src}: normal approximation from the mean and standard deviation of the null share, n {n_val}, cut {cut}")
    def chosen(cell_fn, n_val: int, key: str) -> str:
        """The smallest cut of the grid whose size is within 0.05 plus two standard errors (the rule of the proposed method)."""
        c0 = cell_fn(n_val, 0.0)
        for cut in sorted(exp_situation.CUTS):
            r = c0["rules"][f"cut_{cut:g}"]
            if r["rate"] <= THETA + 2 * r["se"]:
                s = f"{cut:g}"
                return s if len(s) >= 4 else f"{cut:.2f}"
        return "none"

    for n_val, n in N_CODE.items():
        put(f"SiChosenThr{n}", chosen(sit_cell, n_val, "thr"), f"{src}: cut chosen by the rule of the proposed method on the threshold-bias plant, n {n_val}")
        put(f"SiChosenInd{n}", chosen(sit_indep_cell, n_val, "ind"), f"experiments/results/situation_indep.json: cut chosen on the independent-attributes design, n {n_val}")
    put("SiMarkovTwenty", f3(THETA / 0.20), "Proposition 6: Markov bound at the cut 0.20 from a mean share of 0.05")
    put("SiMarkovTen", f3(THETA / 0.10), "Proposition 6: Markov bound at the cut 0.10")
    for n_val, n in N_CODE.items():
        c = sit_cell(n_val, 0.0)
        put(f"SiRho{n}", f3(rho_bar(c)), f"{src}: average correlation of eq:design-effect solved with the null mean share, n {n_val}")
    put("SiIndepSd", f3(math.sqrt(THETA * (1 - THETA) / sit_cell(400, 0.0)["mean_complainants"])), "the standard deviation of a share of independent complainants, n 400")


# ---------------------------------------------------------------------------------------------------------------------
BIAS_CODE = {0.0: "Z", 0.1: "A", 0.2: "B", 0.4: "C"}


def situation_indep_macros() -> None:
    src = "experiments/results/situation_indep.json"
    put("SiInRepsNull", thousands(exp_situation_indep.REPS_NULL), f"{src}: replications at bias 0")
    for c in SITUATION_INDEP["cells"]:
        n, g = N_CODE[c["n"]], BIAS_CODE[c["bias"]]
        tagsrc = f"{src}: n {c['n']}, bias {c['bias']}"
        for rule, code in RULE_SI.items():
            put(f"SiInRate{code}{n}{g}", f3(c["rules"][rule]["rate"]), tagsrc + f", {rule}")
            put(f"SiInSe{code}{n}{g}", f3(c["rules"][rule]["se"]), tagsrc + f", {rule}")
        put(f"SiInMeanShare{n}{g}", f3(c["mean_share"]), tagsrc)
        put(f"SiInSdShare{n}{g}", f3(c["sd_share"]), tagsrc)
        put(f"SiInDesign{n}{g}", f"{c['design_effect']:.1f}", tagsrc + ": design effect")
        put(f"SiInComplainants{n}{g}", f"{c['mean_complainants']:.0f}", tagsrc)
    for n_val, n in N_CODE.items():
        c = sit_indep_cell(n_val, 0.0)
        put(f"SiInRho{n}", f3(rho_bar(c)), f"{src}: average correlation of eq:design-effect solved with the null mean share, n {n_val}")
    eng = "CAOS_RiskValidation docs/fairness/06_validation-tests.md l.77 (recorded by the engine's size-and-power suite, 4,000 repetitions)"
    put("EngSiSizeTwenty", "0.0395", eng + ": size of the cut 0.20")
    put("EngSiSeTwenty", "0.0031", eng + ": standard error of the size of the cut 0.20")
    put("EngSiSizeTen", "0.194", eng + ": size of the former cut 0.10")
    # the standard deviation of the null drop scales with the inverse square root of the evaluation sample
    scale = [SHIFT_ZERO_SD[e] * math.sqrt(e) for e in (125, 250, 500, 1000)]
    put("ShSdScaleMin", f"{min(scale):.2f}", "experiments/results/shift.json: standard deviation of the drop without shift times the square root of the evaluation rows, minimum over four sizes")
    put("ShSdScaleMax", f"{max(scale):.2f}", "experiments/results/shift.json: same, maximum")


SHIFT_ZERO_SD = {c["n_eval"]: c["sd_drop"] for c in SHIFT["cells"] if c["shift"] == 0.0}


def notebook_macros() -> None:
    """The small-design measurements of the product's notebook "Measured size and power of the corrected tests", read from the saved outputs of its cells."""
    import re

    nb = D.jload(figkit.ROOT / "notebooks" / "en" / "13-ml-and-ai-risk" / "09-measured-size-and-power-of-the-corrected-tests.ipynb")
    src = "notebooks/en/13-ml-and-ai-risk/09-measured-size-and-power-of-the-corrected-tests.ipynb"

    def output(i: int) -> str:
        return "".join("".join(o.get("text", [])) for o in nb["cells"][i].get("outputs", []))

    cov = [re.findall(r"[0-9.]+", line) for line in output(10).splitlines() if "|" in line and "n_cal" not in line]
    for (n, m, ratio, bin_rate, bin_se, bb_rate, bb_se), name in zip(cov, ("Tenth", "One", "Four")):
        put(f"NbBin{name}", bin_rate, f"{src}: cell 10 output, m/n = {ratio}")
        put(f"NbBB{name}", bb_rate, f"{src}: cell 10 output, m/n = {ratio}")
    put("NbCovReps", "1,500", f"{src}: cell 10, REPS")
    shift_rows = {float(r[0]): r for r in (re.findall(r"[0-9.]+", line.split("|")[0]) + re.findall(r"[0-9.]+", line.split("|")[1])
                                           for line in output(17).splitlines() if "|" in line and "shift" not in line)}
    z, t = shift_rows[0.0], shift_rows[2.0]
    put("NbFixedFiveZ", z[4], f"{src}: cell 17 output, shift 0, drop above 0.05")
    put("NbFixedTenZ", z[5], f"{src}: cell 17 output, shift 0, drop above 0.10")
    put("NbPermZ", z[6], f"{src}: cell 17 output, shift 0, permutation")
    put("NbFixedFiveT", t[4], f"{src}: cell 17 output, shift 2, drop above 0.05")
    put("NbFixedTenT", t[5], f"{src}: cell 17 output, shift 2, drop above 0.10")
    put("NbPermT", t[6], f"{src}: cell 17 output, shift 2, permutation")
    put("NbShiftReps", "60", f"{src}: cell 17, replications per shift")
    sit = {float(r[0]): r for r in (re.findall(r"[0-9.]+", line.split("|")[0]) + re.findall(r"[0-9.]+", line.split("|")[1])
                                    for line in output(24).splitlines() if "|" in line and "gap" not in line)}
    put("NbSitCutTenZ", sit[0.0][3], f"{src}: cell 24 output, gap 0, share above 0.10")
    put("NbSitCutTwentyZ", sit[0.0][4], f"{src}: cell 24 output, gap 0, share above 0.20")
    put("NbSitReps", "200", f"{src}: cell 24, replications per gap")


# ---------------------------------------------------------------------------------------------------------------------
def committed_macros() -> None:
    import glob

    fed = D.jload(figkit.ROOT / "data" / "derived" / "C20" / "fed-shift.json")
    codes = {"window:baseline": "Base", "window:fed-higher-risk-x0.25": "Quarter", "window:fed-higher-risk-x0.5": "Half",
             "window:fed-higher-risk-x1": "One", "window:pooled": "Pool"}
    src = "data/derived/C20/fed-shift.json"
    for t in fed["tests"]:
        if t["test_id"] == "ml.conformal_coverage":
            code = codes[t["segment"]]
            put(f"Cm{code}BB", sci(t["p_value"], 2) if t["p_value"] < 0.001 else f3(t["p_value"]), f"{src}: {t['segment']} p_value")
            put(f"Cm{code}Bin", sci(t["extras"]["p_value_binomial"], 2) if t["extras"]["p_value_binomial"] < 0.001 else f3(t["extras"]["p_value_binomial"]),
                f"{src}: {t['segment']} extras.p_value_binomial")
            put(f"Cm{code}Cov", f"{t['metric']:.4f}", f"{src}: {t['segment']} metric")
            put(f"Cm{code}M", thousands(t["n"]), f"{src}: {t['segment']} n")
            put(f"Cm{code}Light", t["light"], f"{src}: {t['segment']} light")
            ncal = t["extras"]["n_cal"]
    put("CmNcal", thousands(ncal), f"{src}: extras.n_cal")
    res = next(t for t in fed["tests"] if t["test_id"] == "ml.shift_resilience")
    put("CmResDrop", f4(res["metric"]), f"{src}: shift_resilience metric")
    put("CmResP", f3(res["p_value"]), f"{src}: shift_resilience p_value")
    put("CmResDraws", str(res["extras"]["shift_permutations"]), f"{src}: shift_resilience extras.shift_permutations")
    put("CmResNullMean", f4(res["extras"]["null_mean"]), f"{src}: shift_resilience extras.null_mean")
    put("CmResNullP", f4(res["extras"]["null_p95"]), f"{src}: shift_resilience extras.null_p95")
    put("CmResN", thousands(res["n"]), f"{src}: shift_resilience n")
    shares, lights, qs = [], [], []
    for path in sorted(glob.glob(str(figkit.ROOT / "data" / "derived" / "C21" / "pair-*.json"))):
        h = D.jload(D.pathlib.Path(path))
        t = next(t for t in h["tests"] if t["test_id"] == "fair.situation_testing")
        shares.append(t["metric"])
        lights.append(t["light"])
        qs.append(t["n"])
    put("CmFairMin", f"{min(shares):.4f}", "data/derived/C21/pair-*.json: situation_testing metric, minimum")
    put("CmFairMax", f"{max(shares):.4f}", "data/derived/C21/pair-*.json: situation_testing metric, maximum")
    put("CmFairPairs", str(len(shares)), "data/derived/C21/pair-*.json: year pairs")
    put("CmFairAmber", str(lights.count("amber")), "data/derived/C21/pair-*.json: pairs with an amber light")
    put("CmFairGreen", str(lights.count("green")), "data/derived/C21/pair-*.json: pairs with a green light")
    put("CmFairAboveTen", str(sum(s >= 0.10 for s in shares)), "data/derived/C21/pair-*.json: pairs whose share of significant complainants is at least 0.10")
    green = sorted(s for s, light in zip(shares, lights) if light == "green")
    put("CmFairGreenLo", f"{green[0]:.4f}", "data/derived/C21/pair-*.json: lowest share among the green pairs")
    put("CmFairGreenHi", f"{green[-1]:.4f}", "data/derived/C21/pair-*.json: highest share among the green pairs")
    null_means = [c["mean_share"] for c in (*SITUATION["cells"], *SITUATION_INDEP["cells"]) if c.get("gap", c.get("bias")) == 0.0]
    put("SiNullMeanMax", f3(max(null_means)), "experiments/results/situation.json and situation_indep.json: largest null mean share over the four cells with no planted gap or bias")
    put("CmFairGreenOverNull", f"{math.floor(10 * green[0] / max(null_means)) / 10:.1f}", "data/derived/C21/pair-*.json lowest green share over the largest null mean share of the plants, rounded down to one decimal")
    put("CmFairQMin", thousands(min(qs)), "data/derived/C21/pair-*.json: smallest number of complainants")
    put("CmFairQMax", thousands(max(qs)), "data/derived/C21/pair-*.json: largest number of complainants")
    # the p-values recomputed with the engine function from the committed counts
    from riskvalidation.ml import conformal

    worst = 0.0
    for t in fed["tests"]:
        if t["test_id"] != "ml.conformal_coverage":
            continue
        m, c = t["n"], int(round(t["metric"] * t["n"]))
        r = conformal.conformal_coverage(np.column_stack([np.arange(m) < c, np.zeros(m, dtype=bool)]), np.zeros(m, dtype=int), 0.1, n_cal=t["extras"]["n_cal"])
        worst = max(worst, abs(math.log10(r.p_value) - math.log10(t["p_value"])), abs(math.log10(r.p_value_binomial) - math.log10(t["extras"]["p_value_binomial"])))
    put("CmRecomputeDiff", sci(max(worst, 1e-16), 1), "make_numbers.py: largest difference in log10 p between the engine function on the committed counts and the committed value")


# ---------------------------------------------------------------------------------------------------------------------
def hypotheses() -> list[list[str]]:
    rows = []
    # H1: coverage
    grid = [c for c in COVERAGE["cells"] if c["b"] == 1.0 and "exact" in c and c["n"] in exp_coverage.SIZE_NS and any(abs(c["ratio"] - r) < 1e-9 for r in exp_coverage.SIZE_RATIOS)]
    bin1 = [c for c in grid if c["ratio"] == 1.0]
    bin4 = [c for c in grid if c["ratio"] == 4.0]
    held_a = all(c["rates"]["bin"]["rate"] + 2 * c["rates"]["bin"]["se"] >= 0.15 for c in bin1) and all(
        c["rates"]["bin"]["rate"] + 2 * c["rates"]["bin"]["se"] >= 0.35 for c in bin4)
    held_b = all(c["rates"]["bb"]["rate"] <= THETA + 2 * c["rates"]["bb"]["se"] for c in grid) and all(c["exact"]["bb"] <= THETA for c in grid)
    rows.append(["H1a", "The binomial coverage test rejects in at least 0.15 of exchangeable replications at $m/n=1$ and 0.35 at $m/n=4$, up to two standard errors",
                 f"{min(c['rates']['bin']['rate'] for c in bin1):.3f} to {max(c['rates']['bin']['rate'] for c in bin1):.3f} and "
                 f"{min(c['rates']['bin']['rate'] for c in bin4):.3f} to {max(c['rates']['bin']['rate'] for c in bin4):.3f}", "held" if held_a else "refuted"])
    rows.append(["H1b", "The Beta-Binomial test rejects in at most 0.05 plus two standard errors at every ratio of the grid, and its exact size is at most 0.05",
                 f"largest simulated {max(c['rates']['bb']['rate'] for c in grid):.3f}, largest exact {max(c['exact']['bb'] for c in grid):.4f}", "held" if held_b else "refuted"])
    # H2: shift
    c125, c250 = shift_cell(125, 0.0), shift_cell(250, 0.0)
    a_small = all(c["rules"]["fixed_0.05"]["rate"] > THETA + 2 * c["rules"]["fixed_0.05"]["se"] for c in SHIFT["cells"] if c["shift"] == 0.0)
    ten_small = c125["rules"]["fixed_0.10"]["rate"] > THETA + 2 * c125["rules"]["fixed_0.10"]["se"]
    rows.append(["H2a", "A fixed drop of 0.05 AUC points fires above 0.05 plus two standard errors on shift-free replications; a fixed drop of 0.10 does so at the smallest design",
                 f"cut 0.05: {min(c['rules']['fixed_0.05']['rate'] for c in SHIFT['cells'] if c['shift'] == 0.0):.3f} to "
                 f"{max(c['rules']['fixed_0.05']['rate'] for c in SHIFT['cells'] if c['shift'] == 0.0):.3f} over four sizes; cut 0.10 at 125 rows: "
                 f"{c125['rules']['fixed_0.10']['rate']:.3f}", "held" if (a_small and ten_small) else "held in part"])
    perm_ok = all(c["rules"]["perm_199"]["rate"] <= THETA + 2 * c["rules"]["perm_199"]["se"] for c in SHIFT["cells"] if c["shift"] == 0.0)
    rows.append(["H2b", "The permutation reference with 199 draws rejects in at most 0.05 plus two standard errors without shift, at every evaluation size",
                 f"{min(c['rules']['perm_199']['rate'] for c in SHIFT['cells'] if c['shift'] == 0.0):.3f} to "
                 f"{max(c['rules']['perm_199']['rate'] for c in SHIFT['cells'] if c['shift'] == 0.0):.3f}", "held" if perm_ok else "refuted"])
    cost = all(c["rules"]["perm_199"]["rate"] < c["rules"]["fixed_0.05"]["rate"] for c in SHIFT["cells"] if c["shift"] > 0)
    gaps2 = [shift_cell(e, 2.0)["rules"]["fixed_0.05"]["rate"] - shift_cell(e, 2.0)["rules"]["perm_199"]["rate"] for e in (125, 250, 500, 1000)]
    narrows = all(a > b for a, b in zip(gaps2, gaps2[1:]))
    rows.append(["H2c", "The permutation reference detects a planted shift less often than the fixed cut 0.05 in every cell, and the difference at shift 2 falls at each larger evaluation size",
                 f"shift 2: gap {shift_cell(125, 2.0)['rules']['fixed_0.05']['rate'] - shift_cell(125, 2.0)['rules']['perm_199']['rate']:.3f} at 125 rows, "
                 f"{shift_cell(1000, 2.0)['rules']['fixed_0.05']['rate'] - shift_cell(1000, 2.0)['rules']['perm_199']['rate']:.3f} at 1,000 rows", "held" if (cost and narrows) else "refuted"])
    # H3: situation
    s0, s8 = sit_cell(400, 0.0), sit_cell(400, 0.8)
    ok20 = s0["rules"]["cut_0.2"]["rate"] <= THETA + 2 * s0["rules"]["cut_0.2"]["se"]
    bad10 = s0["rules"]["cut_0.1"]["rate"] > THETA + 2 * s0["rules"]["cut_0.1"]["se"]
    pw = s8["rules"]["cut_0.2"]["rate"] >= 0.95
    rows.append(["H3a", "With 400 applicants and thirty neighbours the amber cut 0.20 fires in at most 0.05 plus two standard errors of the replications without bias and the cut 0.10 above it",
                 f"cut 0.20: {s0['rules']['cut_0.2']['rate']:.3f}; cut 0.10: {s0['rules']['cut_0.1']['rate']:.3f}", "held" if (ok20 and bad10) else "refuted"])
    rows.append(["H3b", "The cut 0.20 detects the planted gap of 0.8 in at least 0.95 of the replications",
                 f"{s8['rules']['cut_0.2']['rate']:.3f}", "held" if pw else "refuted"])
    s4 = sit_cell(400, 0.4)
    s2 = sit_cell(400, 0.2)
    se_diff = lambda a, b: (a["se"] ** 2 + b["se"] ** 2) ** 0.5  # noqa: E731
    costs = [c["rules"]["cut_0.1"]["rate"] - c["rules"]["cut_0.2"]["rate"] > 2 * se_diff(c["rules"]["cut_0.1"], c["rules"]["cut_0.2"]) for c in (s2, s4)]
    rows.append(["H3c", "The cut 0.20 costs no power against the cut 0.10 at the planted gaps 0.2 and 0.4 (a cost is a deficit beyond twice the standard error of the difference)",
                 f"gap 0.4: {s4['rules']['cut_0.2']['rate']:.3f} against {s4['rules']['cut_0.1']['rate']:.3f}; gap 0.2: {s2['rules']['cut_0.2']['rate']:.3f} against {s2['rules']['cut_0.1']['rate']:.3f}",
                 "refuted" if any(costs) else "held"])
    l0 = sit_cell(1000, 0.0)
    rows.append(["H3d", "The size of the cut 0.10 measured at 400 applicants carries over to 1,000 applicants (the two sizes differ by at most twice the standard error of their difference)",
                 f"{s0['rules']['cut_0.1']['rate']:.3f} at 400, {l0['rules']['cut_0.1']['rate']:.3f} at 1,000",
                 "refuted" if abs(l0["rules"]["cut_0.1"]["rate"] - s0["rules"]["cut_0.1"]["rate"]) > 2 * se_diff(l0["rules"]["cut_0.1"], s0["rules"]["cut_0.1"]) else "held"])
    i4, i4t = sit_indep_cell(400, 0.0), sit_cell(400, 0.0)
    se = lambda a, b: (a["se"] ** 2 + b["se"] ** 2) ** 0.5  # noqa: E731
    differ = any(abs(i4["rules"][k]["rate"] - i4t["rules"][k]["rate"]) > 2 * se(i4["rules"][k], i4t["rules"][k]) for k in ("cut_0.1", "cut_0.2"))
    rows.append(["H3e", "The size of the cuts 0.10 and 0.20 at 400 applicants is the same on a second planted design with independent attributes",
                 f"cut 0.10: {i4t['rules']['cut_0.1']['rate']:.3f} and {i4['rules']['cut_0.1']['rate']:.3f}; cut 0.20: {i4t['rules']['cut_0.2']['rate']:.3f} and "
                 f"{i4['rules']['cut_0.2']['rate']:.3f}", "refuted" if differ else "held"])
    return rows


def hypothesis_table(rows: list[list[str]]) -> None:
    from make_tables import table

    table("hypotheses", ["Id", "Statement", "Measured", "Outcome"], rows,
          caption="The predictions: H1a, H1b, H2a, H2b and H3a restate as bounds the small-design results of the product's notebook, and H2c and H3b to H3e were formulated "
                  "with the experiments; each with the value the experiments measured and whether it held: "
                  "held, held in part, or refuted; the bound used is 0.05 plus two Monte Carlo standard errors of the rate, and a difference of two rates is real when it "
                  "exceeds twice the standard error of the difference.",
          label="tab:hypotheses", align=">{\\raggedright\\arraybackslash}p{0.8cm}>{\\raggedright\\arraybackslash}p{6.6cm}>{\\raggedright\\arraybackslash}p{4.2cm}>{\\raggedright\\arraybackslash}p{1.8cm}")


def main() -> None:
    coverage_macros()
    shift_macros()
    situation_macros()
    situation_indep_macros()
    notebook_macros()
    committed_macros()
    rows = hypotheses()
    hypothesis_table(rows)
    put("HypTotal", str(len(rows)), "make_numbers.py: predictions of the hypotheses table")
    put("HypRefuted", str(sum(r[3] == "refuted" for r in rows)), "make_numbers.py: predictions refuted")
    put("HypHeld", str(sum(r[3] == "held" for r in rows)), "make_numbers.py: predictions held")
    put("HypPartial", str(sum(r[3] == "held in part" for r in rows)), "make_numbers.py: predictions held in part")
    lines = ["% Generated by make_numbers.py from experiments/results and data/derived: do not edit.\n"]
    for name, (text, _) in sorted(NUM.items()):
        lines.append(f"\\newcommand{{\\{name}}}{{{text}}}\n")
    (D.TABLES / "numbers.tex").write_text("".join(lines), encoding="utf-8", newline="\n")
    index = {name: {"value": text, "source": src} for name, (text, src) in sorted(NUM.items())}
    (D.HERE / "numbers-index.json").write_text(json.dumps(index, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print("macros", len(NUM), "hypothesis rows", len(rows))
    for r in rows:
        print(r[0], r[3], "|", r[2])


if __name__ == "__main__":
    main()
