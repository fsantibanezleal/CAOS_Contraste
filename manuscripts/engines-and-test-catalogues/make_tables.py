"""Write every results table and every number of the prose from ``experiments/results_*.json`` and the committed artifacts.

    python manuscripts/engines-and-test-catalogues/make_tables.py

Tables land in ``tables/`` as booktabs files the sections input; ``tables/numbers.tex`` defines one macro per number quoted in the
prose, each preceded by a comment naming its source, so no number is typed by hand.
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


CAT, ECB, PRT, IRR, ABL = (load(n) for n in ("results_catalogue.json", "results_ecb.json", "results_portfolio.json",
                                             "results_irrbb.json", "results_ablation.json"))
NUMS: dict[str, tuple[str, str]] = {}
H3_CUTOFF = 3.0  # |z| <= 3: the acceptance criterion of Hypothesis H3 for each stochastic comparison
LAYER_E_CUTOFF = 4.0  # layer E of the ablation rejects when the mean difference is at least 4 standard errors (run_ablation.py layer_e)
POWER_Z = 0.8416  # standard normal quantile of a power of 0.8


def sci(x: float, d: int = 1) -> str:
    if x == 0:
        return "0"
    e = int(math.floor(math.log10(abs(x))))
    m = x / 10 ** e
    return f"\\ensuremath{{{m:.{d}f}\\times 10^{{{e}}}}}"


def put(name: str, text: str, source: str) -> str:
    NUMS[name] = (text, source)
    return text


def f(x: float, d: int = 3) -> str:
    return f"{x:.{d}f}"


def tex_sci_cell(x: float, d: int = 1) -> str:
    return "$" + sci(x, d).replace("\\ensuremath{", "")[:-1] + "$" if x != 0 else "0"


# ------------------------------------------------------------------------------------------------------- numbers
inv, ecbc, scan, sv = CAT["inventory"], CAT["ecb"], CAT["installed_scan"], CAT["survey"]
src = "results_catalogue.json"
put("inventoryVersion", inv["version"], src + " inventory.version")
put("testsTotal", f"{inv['tests']}", src + " inventory.tests")
put("familiesTotal", f"{inv['families']}", src + " inventory.families")
put("pvalueTests", f"{inv['by_decision']['p_value']}", src + " inventory.by_decision")
put("metricTests", f"{inv['by_decision']['metric']}", src + " inventory.by_decision")
put("ecbSections", f"{ecbc['sections']}", src + " ecb.sections")
put("ecbImpl", f"{ecbc['implemented']}", src + " ecb.implemented")
put("ecbRelated", f"{ecbc['related_only']}", src + " ecb.related_only")
put("ecbAbsent", f"{ecbc['absent']}", src + " ecb.absent")
put("distScanned", f"{scan['distributions']}", src + " installed_scan.distributions")
put("filesScanned", f"{scan['python_files']:,}", src + " installed_scan.python_files")
put("pypiQueried", f"{sv['queried']}", src + " survey.queried")
put("pypiFound", f"{sv['found']}", src + " survey.found")
put("pypiDate", sv["date"], src + " survey.date")
hold = figkit.doc("C01/holdout.json")["outputs"]
put("holdN", f"{hold['n']:,}", "data/derived/C01/holdout.json outputs.n")
put("holdD", f"{hold['defaults']:,}", "data/derived/C01/holdout.json outputs.defaults")
missing = [r["name"] for r in sv["rows"] if r["status"] != "found"]
put("pypiMissing", f"{len(missing)}", "results_catalogue.json survey rows not found")
put("pypiMissingNames", ", ".join("\\texttt{" + m + "}" for m in missing), "results_catalogue.json survey rows not found")
pa = ECB["part_a"]
src = "results_ecb.json"
put("ecbInputs", f"{pa['pd.jeffreys']['n_inputs']}", src + " part_a")
put("ecbAllMax", sci(max(pa[k]["max_abs_diff"] for k in pa)), src + " part_a, largest of the five")
put("ecbJeffMax", sci(pa["pd.jeffreys"]["max_abs_diff"]), src + " part_a pd.jeffreys")
put("ecbAucMax", sci(pa["disc.auc_vs_initial"]["max_abs_diff"]), src + " part_a disc.auc_vs_initial")
put("ecbSsqMax", sci(pa["disc.auc_vs_initial"]["max_abs_diff_s2"]), src + " part_a disc.auc_vs_initial s2")
put("ecbMwbMax", sci(pa["rating.mwb"]["max_abs_diff"]), src + " part_a rating.mwb")
put("ecbMigMax", sci(pa["rating.migration_ztests"]["max_abs_diff"]), src + " part_a rating.migration_ztests")
put("ecbMigCells", f"{pa['rating.migration_ztests']['n_cells']:,}", src + " part_a rating.migration_ztests n_cells")
put("ecbHhiMax", sci(pa["rating.hhi"]["max_abs_diff"]), src + " part_a rating.hhi")
pb = ECB["part_b"]
put("cCells", f"{pb['cells']}", src + " part_b.cells")
for a, tag in (("0.05", "Five"), ("0.01", "One")):
    put(f"flagJeff{tag}", f"{pb['alpha_' + a]['flag_jeffreys']}", src + f" part_b alpha_{a}")
    put(f"flagBin{tag}", f"{pb['alpha_' + a]['flag_binomial']}", src + f" part_b alpha_{a}")
    put(f"disagree{tag}", f"{pb['alpha_' + a]['disagree']}", src + f" part_b alpha_{a}")
dif = [r for r in pb["rows"] if (r["p_jeffreys"] < 0.05) != (r["p_binomial"] < 0.05)][0]
for k, v in (("diffN", f"{dif['n']:,}"), ("diffD", f"{dif['d']:,}"), ("diffPj", f(dif["p_jeffreys"])), ("diffPb", f(dif["p_binomial"])),
             ("diffGrade", dif["grade"]), ("diffModel", dif["model"])):
    put(k, v, src + " part_b.rows (the cell where the 5 percent decisions differ)")
put("smMatch", f"{pb['statsmodels_flag_equals_engine_005']}", src + " part_b.statsmodels_flag_equals_engine_005")
put("committedGap", sci(pb["committed_match"]["max_abs_gap"]), src + " part_b.committed_match")
put("maxPGap", f(pb["max_abs_p_gap"]), src + " part_b.max_abs_p_gap")
put("medPGap", f(pb["median_abs_p_gap"]), src + " part_b.median_abs_p_gap")
worst = max(pb["rows"], key=lambda r: abs(r["p_jeffreys"] - r["p_binomial"]))
put("worstGapN", f"{worst['n']:,}", src + " part_b.rows (worst cell)")
put("worstGapD", f"{worst['d']:,}", src + " part_b.rows (worst cell)")
put("worstGapPj", f(worst["p_jeffreys"]), src + " part_b.rows (worst cell)")
put("worstGapPb", f(worst["p_binomial"]), src + " part_b.rows (worst cell)")
put("worstGapModel", worst["model"], src + " part_b.rows (worst cell)")

an, mc, rg, gd, ce, ie = (PRT[k] for k in ("anchors", "mc", "regeneration", "grids", "cell", "is_euler"))
src = "results_portfolio.json"
put("lhpMax", sci(an["lhp_integral"]["max_abs_diff"]), src + " anchors.lhp_integral")
put("irbDiff", f"{an['irb']['abs_diff_module']:.1f}", src + " anchors.irb")
put("irbK", f(an["irb"]["k_scipy"], 6), src + " anchors.irb.k_scipy")
put("irbPd", f(an["irb"]["pd"], 6), src + " anchors.irb.pd")
cf = an["crp_closed_form"]
put("crpPzero", f"{cf['p0_engine']:.6f}", src + " anchors.crp_closed_form")
put("crpMean", f"{cf['mean_engine']:.2f}", src + " anchors.crp_closed_form")
put("crpVar", f"{cf['var_engine']:,.1f}", src + " anchors.crp_closed_form")
put("crpVarGap", sci(cf["rel_gap_var"]), src + " anchors.crp_closed_form.rel_gap_var")
put("crpMass", sci(cf["mass_outside"]), src + " anchors.crp_closed_form.mass_outside")
put("crpNmax", f"{cf['n_max']:,}", src + " anchors.crp_closed_form.n_max")
put("crpSigma", f(cf["sigma2"], 4), src + " anchors.crp_closed_form.sigma2")
ci_ = an["crp_independent"]
put("crpIndMax", sci(ci_["max_abs_diff_stable"]), src + " anchors.crp_independent")
put("crpIndPanjer", sci(ci_["max_abs_diff_panjer"]), src + " anchors.crp_independent")
put("crpIndRel", sci(ci_["max_rel_diff_stable"]), src + " anchors.crp_independent.max_rel_diff_stable")
put("crpIndPositive", f"{ci_['n_positive']:,}", src + " anchors.crp_independent.n_positive")
put("crpCompared", f"{ci_['n_compared']:,}", src + " anchors.crp_independent")
put("gaDelta", f(an["granularity"]["delta"], 4), src + " anchors.granularity")
put("gaSpread", sci(an["granularity"]["rel_spread"]), src + " anchors.granularity")
put("gaTimesN", f(an["granularity"]["ga_times_n"][0], 8), src + " anchors.granularity")
put("mcReps", f"{mc['replications']}", src + " mc")
put("mcScen", f"{mc['scenarios_each']:,}", src + " mc")
put("mcRho", f(mc["rho"], 4), src + " mc.rho")
for nm, tag in (("var99", "VarNinetyNine"), ("es99", "EsNinetyNine"), ("var999", "VarNinetyNineNine"), ("es999", "EsNinetyNineNine"), ("mean", "Mean")):
    q = mc["quantities"][nm]
    put(f"mc{tag}Eng", f"{q['engine_mean']:,.0f}", src + f" mc.quantities.{nm}")
    put(f"mc{tag}EngSd", f"{q['engine_sd']:,.0f}", src + f" mc.quantities.{nm}")
    put(f"mc{tag}Ind", f"{q['independent_mean']:,.0f}", src + f" mc.quantities.{nm}")
    put(f"mc{tag}IndSd", f"{q['independent_sd']:,.0f}", src + f" mc.quantities.{nm}")
    put(f"mc{tag}Z", f"{q['z_difference']:+.2f}", src + f" mc.quantities.{nm}.z_difference")
    put(f"mcMdd{tag}", f"{100 * (H3_CUTOFF + POWER_Z) * math.sqrt((q['engine_sd'] ** 2 + q['independent_sd'] ** 2) / mc['replications']) / q['independent_mean']:.2f}",
        src + f" mc.quantities.{nm} (3 + 0.8416) sqrt((sd_e^2 + sd_i^2) / R) / independent mean, in percent; 3 is the cutoff of H3")
put("mcElExact", f"{mc['expected_loss_exact']:,.0f}", src + " mc.expected_loss_exact")
put("regenRel", sci(rg["max_rel_diff"]), src + " regeneration.max_rel_diff")
put("regenN", f"{rg['n_scenarios']:,}", src + " regeneration")
put("regenSeed", f"{rg['seed']}", src + " regeneration")
put("regenChunk", f"{rg['chunk']:,}", src + " regeneration")
put("regenSeconds", f"{rg['seconds']:.0f}", src + " regeneration.seconds")
band = 2.576
for kind, tag in (("maximum-likelihood", "Ml"), ("moments", "Mom")):
    cells = [(y, c) for y in ("22", "40") for c in gd[y]["cells"]]
    fails = [(y, c) for y, c in cells if abs(c[kind]["z_coverage"]) > band]
    put(f"grid{tag}Cells", f"{len(cells)}", src + " grids")
    put(f"grid{tag}Fail", f"{len(fails)}", src + f" grids |z coverage| > {band}")
    wy, wc = min(cells, key=lambda t: t[1][kind]["coverage"])
    put(f"grid{tag}WorstCov", f(wc[kind]["coverage"]), src + " grids (lowest coverage)")
    put(f"grid{tag}WorstRho", f(wc["rho"], 2), src + " grids (lowest coverage)")
    put(f"grid{tag}WorstYears", wy, src + " grids (lowest coverage)")
    put(f"grid{tag}WorstZ", f"{wc[kind]['z_coverage']:+.2f}", src + " grids (lowest coverage)")
    put(f"grid{tag}MeanCov", f(sum(c[kind]["coverage"] for _, c in cells) / len(cells)), src + " grids (mean coverage)")
below = [c for _, c in cells if c["maximum-likelihood"]["coverage"] < 0.95]
put("gridMlBelow", f"{len(below)}", src + " grids (ML coverage below 0.95)")
put("gridMlNegBias", f"{sum(c['maximum-likelihood']['bias'] < 0 for _, c in cells)}", src + " grids (ML bias below zero)")
put("gridMlBiasMin", f"{min(c['maximum-likelihood']['bias'] for _, c in cells):+.4f}", src + " grids (most negative ML bias)")
put("gridMlBiasMax", f"{max(c['maximum-likelihood']['bias'] for _, c in cells):+.4f}", src + " grids (least negative ML bias)")
_n = sum(gd[y]["n_replications"] * len(gd[y]["cells"]) for y in ("22", "40"))
_cov = sum(c["maximum-likelihood"]["coverage"] * gd[y]["n_replications"] for y in ("22", "40") for c in gd[y]["cells"]) / _n
put("gridMlPooledReps", f"{_n:,}", src + " grids (cells times replications)")
put("gridMlPooledZ", f"{(_cov - 0.95) / math.sqrt(0.95 * 0.05 / _n):+.1f}", src + " grids (pooled ML coverage against 0.95 over all replications, valid only if the cells are independent)")
put("gridChance", f"{len(cells) * 0.01:.2f}", src + " grids (24 cells times 0.01)")
put("gridReps", f"{gd['22']['n_replications']}", src + " grids")
put("gridBandHalf", f(band * math.sqrt(0.95 * 0.05 / gd["22"]["n_replications"])), src + " grids (2.576 sqrt(0.95 0.05 / 400))")
put("gridMlBiasTwentyFour", f"{[c for c in gd['22']['cells'] if abs(c['rho'] - 0.24) < 1e-9][0]['maximum-likelihood']['bias']:+.4f}", src + " grids")
put("gridMomBiasTwentyFour", f"{[c for c in gd['22']['cells'] if abs(c['rho'] - 0.24) < 1e-9][0]['moments']['bias']:+.4f}", src + " grids")
put("gridMomCovTwentyFour", f"{[c for c in gd['22']['cells'] if abs(c['rho'] - 0.24) < 1e-9][0]['moments']['coverage']:.3f}", src + " grids")
put("gridMlCovTwentyFour", f"{[c for c in gd['22']['cells'] if abs(c['rho'] - 0.24) < 1e-9][0]['maximum-likelihood']['coverage']:.3f}", src + " grids")
put("cellReps", f"{ce['reps']}", src + " cell")
for c in ce["cells"]:
    t = {0.02: "Low", 0.12: "Mid", 0.24: "High"}[c["rho"]]
    put(f"cell{t}Cov", f(c["coverage"], 3), src + f" cell rho={c['rho']}")
    put(f"cell{t}CovSe", f(c["coverage_se"], 3), src + f" cell rho={c['rho']}")
    put(f"cell{t}Bias", f"{c['bias']:+.4f}", src + f" cell rho={c['rho']}")
    put(f"cell{t}BiasSe", f(c["bias_se"], 4), src + f" cell rho={c['rho']}")
put("isReps", f"{ie['replications']}", src + " is_euler")
put("isScen", f"{ie['scenarios_each']:,}", src + " is_euler")
put("isThreshold", f"{ie['threshold']:,.0f}", src + " is_euler.threshold")
put("isPlainMean", f(ie["plain_mean"], 5), src + " is_euler")
put("isPlainSd", f(ie["plain_sd"], 5), src + " is_euler")
put("isMean", f(ie["is_mean"], 5), src + " is_euler")
put("isSd", sci(ie["is_sd"]), src + " is_euler")
put("isZ", f"{-ie['z_difference']:+.2f}", src + " is_euler.z_difference, sign reversed: the file holds plain minus importance sampler; the text reports engine (importance sampler) minus reference (plain)")
put("isRatio", f"{ie['variance_ratio']:.0f}", src + " is_euler.variance_ratio")
put("eulerGap", f"{ie['euler_rel_gap']:.1f}", src + " is_euler.euler_rel_gap")
put("eulerEs", f"{ie['es']:,.0f}", src + " is_euler.es")

we, va = IRR["worked_example"], IRR["variants"]
src = "results_irrbb.json"
put("irrAlpha", f(we["alpha_short"]["engine"], 4), src + " worked_example.alpha_short")
put("irrShort", f(we["short-up"]["engine"], 2), src + " worked_example.short-up")
put("irrSteep", f(we["steepener"]["engine"], 2), src + " worked_example.steepener")
put("irrFlat", f(we["flattener"]["engine"], 2), src + " worked_example.flattener")
put("irrFlatDev", f(we["flattener"]["abs_dev"], 3), src + " worked_example.flattener.abs_dev")
put("irrSteepDev", f(we["steepener"]["abs_dev"], 3), src + " worked_example.steepener.abs_dev")
put("irrShortDev", f(we["short-up"]["abs_dev"], 3), src + " worked_example.short-up.abs_dev")
put("irrAlphaDev", f(we["alpha_short"]["abs_dev"], 5), src + " worked_example.alpha_short.abs_dev")
put("irrLegs", f"{va['n_legs_shocks']}", src + " variants.n_legs_shocks")
put("irrVariants", f"{va['n_variants']}", src + " variants.n_variants")
put("irrQlMax", sci(va["max_rel_ql"]), src + " variants.max_rel_ql")
put("irrEngMax", f"{va['max_rel_engine']:.1f}", src + " variants.max_rel_engine")
put("irrShapeInd", sci(va["max_shape_independent"]), src + " variants.max_shape_independent")
put("irrShapeEng", f"{va['max_shape_engine']:.1f}", src + " variants.max_shape_engine")
put("irrPair", f"{va['pair_max_abs']:.1f}", src + " variants.pair_max_abs")

src = "results_ablation.json"
mut = ABL["mutants"]
put("ablMutants", f"{len(mut)}", src + " mutants")
real = [m for m in mut if not m["equivalent"]]
put("ablReal", f"{len(real)}", src + " mutants (not equivalent)")
put("ablEquiv", f"{len(mut) - len(real)}", src + " mutants (equivalent)")
put("ablCEquiv", f"{sum(m['detected_by']['C'] for m in mut if m['equivalent'])}", src + " equivalent mutants detected by layer C")
put("ablFalseAlarms", f"{sum(ABL['baseline_false_alarms'].values())}", src + " baseline_false_alarms")
for k in "ABCDE":
    put(f"abl{k}All", f"{sum(m['detected_by'][k] for m in mut)}", src + f" layer {k} detections, all mutants")
    put(f"abl{k}Real", f"{sum(m['detected_by'][k] for m in real)}", src + f" layer {k} detections, real defects")
put("ablAny", f"{sum(any(m['detected_by'].values()) for m in real)}", src + " real defects detected by at least one layer")
put("ablOnly", f"{sum(sum(m['detected_by'].values()) == 1 for m in real)}", src + " real defects detected by exactly one layer")
put("ablNone", f"{sum(not any(m['detected_by'].values()) for m in real)}", src + " real defects detected by no layer")
uniq = {k: sum(m["detected_by"][k] and sum(m["detected_by"].values()) == 1 for m in real) for k in "ABCDE"}
for k in "ABCDE":
    put(f"abl{k}Unique", f"{uniq[k]}", src + f" real defects detected by layer {k} and by no other layer")
put("ablHEight", "held" if all(v >= 1 for v in uniq.values()) else "was refuted", src + " layers with at least one unique detection among the real defects")
put("ablLayersWithUnique", f"{sum(v >= 1 for v in uniq.values())}", src + " layers with at least one unique detection")
put("ablRetriesCommitted", f"{len(ABL.get('retries', []))}", src + " retries (a layer that raised an exception and was run again)")
REP = load("results_ablation_reproduction.json")
put("ablReruns", f"{REP['reruns']}", "results_ablation_reproduction.json reruns")
put("ablReproduced", f"{REP['reproduced']}", "results_ablation_reproduction.json reproduced")
put("ablRerunRetries", f"{sum(r['retries'] for r in REP['per_run'])}", "results_ablation_reproduction.json per_run retries, committed run and reruns")
put("ablRerunSentence",
    f"The detection matrix of the committed ablation was reproduced cell for cell by {REP['reproduced']} of {REP['reruns']} reruns written with \\texttt{{--out}} and compared by "
    f"\\texttt{{compare\\_ablation\\_runs.py}}; in the committed run and the reruns together a layer was run again after an exception {sum(r['retries'] for r in REP['per_run'])} times.",
    "results_ablation_reproduction.json")
WORDS = ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve"]
for i, m in enumerate(mut):
    put(f"ablDet{WORDS[i]}", ",".join(k for k in "ABCDE" if m["detected_by"][k]) or "none", src + f" {m['id']}")


EFF = load("results_ablation_effect.json")
src = "results_ablation_effect.json"
put("effLoadingFactor", f"{EFF['loading_factor']:.2f}", src + " loading_factor")
put("effCorrPct", f"{100 * (1 - EFF['correlation_factor']):.1f}", src + " correlation_factor")
put("effReps", f"{EFF['replications']}", src + " replications")
put("effScen", f"{EFF['scenarios_each']:,}", src + " scenarios_each")
SCALE = math.sqrt((mc["replications"] * mc["scenarios_each"]) / (3 * 40_000))
for nm, tag in (("var99", "VarNinetyNine"), ("es99", "EsNinetyNine"), ("var999", "VarNinetyNineNine"), ("es999", "EsNinetyNineNine")):
    put(f"effChange{tag}", f"{abs(100 * EFF['relative_change'][nm]):.1f}", src + f" relative_change.{nm}, absolute value in percent")
q = mc["quantities"]["var99"]
put("effMddVarNinetyNine", f"{100 * (LAYER_E_CUTOFF + POWER_Z) * SCALE * math.sqrt((q['engine_sd'] ** 2 + q['independent_sd'] ** 2) / mc['replications']) / q['independent_mean']:.1f}",
    "results_portfolio.json mc.quantities.var99 scaled by sqrt((10 x 200000) / (3 x 40000)), the size of layer E, at its cutoff of 4 standard errors")
FS = EFF["fullsize_comparison"]
put("fsReps", f"{FS['replications']}", src + " fullsize_comparison.replications")
put("fsScen", f"{FS['scenarios_each']:,}", src + " fullsize_comparison.scenarios_each")
for nm, tag in (("var99", "VarNinetyNine"), ("es99", "EsNinetyNine"), ("var999", "VarNinetyNineNine"), ("es999", "EsNinetyNineNine")):
    put(f"fsZ{tag}", f"{FS['quantities'][nm]['z_defect_minus_independent']:+.1f}", src + f" fullsize_comparison.quantities.{nm}.z_defect_minus_independent")
    put(f"fsShift{tag}", f"{abs(100 * FS['quantities'][nm]['relative_shift']):.1f}", src + f" fullsize_comparison.quantities.{nm}.relative_shift, absolute value in percent")
put("fsFlagged", f"{sum(abs(v['z_defect_minus_independent']) > H3_CUTOFF for v in FS['quantities'].values())}", src + " fullsize_comparison, measures with |z| above the cutoff of 3")

RUNS = [("run_ecb.py", "results_ecb.json", "Ecb", "run"), ("run_irrbb.py", "results_irrbb.json", "Irrbb", "run"),
        ("run_catalogue.py", "results_catalogue.json", "Catalogue", "run"), ("run_portfolio.py", "results_portfolio.json", "Portfolio", "run"),
        ("run_ablation.py", "results_ablation.json", "Ablation", "run"), ("run_ablation_effect.py", "results_ablation_effect.json", "Effect", "run")]
RUN = {}
for script, fname, tag, key in RUNS:
    r = load(fname)[key]
    RUN[script] = r
    put(f"run{tag}Seconds", f"{r['seconds'] / 60:.0f}" if r["seconds"] >= 120 else f"{r['seconds']}", fname + f" {key}.seconds, in minutes when at least two minutes")
    put(f"run{tag}Unit", "minutes" if r["seconds"] >= 120 else "seconds", fname + f" {key}.seconds")
    put(f"run{tag}Mb", f"{r['peak_working_set_mb']:,}", fname + f" {key}.peak_working_set_mb")
put("runPython", RUN["run_ecb.py"]["python"], "results_ecb.json run.python")
put("runPeakMax", f"{max(r['peak_working_set_mb'] for r in RUN.values()):,}", "largest peak_working_set_mb of the six result files")

# ------------------------------------------------------------------------------------------------------- tables
def table_runs() -> None:
    rows = []
    for script, fname, tag, key in RUNS:
        r = RUN[script]
        t = f"{r['seconds'] / 60:.0f} min" if r["seconds"] >= 120 else f"{r['seconds']} s"
        rows.append(("\\texttt{" + figkit.tex_escape(script) + "}", "\\texttt{" + figkit.tex_escape(fname) + "}", t, f"{r['peak_working_set_mb']:,}"))
    figkit.table(OUT / "runs.tex", ["Script", "Writes", "Wall time", "Peak memory (MB)"], rows,
                 caption="Wall time and peak resident memory of one run of each experiment script, as recorded in the \\texttt{run} field of its results file, on the machine described in Section~\\ref{sec:reproducibility}.",
                 label="tab:runs", align="llrr", digits=0)


def table_catalogue() -> None:
    rows = [(k.replace("_", "-"), v) for k, v in inv["by_family"].items()]
    half = (len(rows) + 1) // 2
    left, right = rows[:half], rows[half:] + [("", "")] * (2 * half - len(rows))
    figkit.table(OUT / "catalogue.tex", ["Family", "Tests", "Family", "Tests"],
                 [(a[0], a[1], b[0], b[1] if b[1] != "" else "") for a, b in zip(left, right)],
                 caption=f"Tests registered by the engine release {inv['version']}, by family: {inv['tests']} tests in {inv['families']} families, "
                         f"{inv['by_decision']['p_value']} decided by a p-value and {inv['by_decision']['metric']} by a metric, each with its primary source.",
                 label="tab:catalogue", align="lrlr", digits=0)


def table_ecb() -> None:
    rows = []
    for r in ecbc["rows"]:
        status = "as specified" if r["engine_id"] else ("related, two-sided" if r["related_id"] else "not implemented")
        rows.append((r["section"], figkit.tex_escape(r["statistic"]), "\\texttt{" + figkit.tex_escape(r["engine_id"] or r["related_id"] or "--").replace("\\_", "\\_\\allowbreak{}").replace(".", ".\\allowbreak{}") + "}", status))
    figkit.table(OUT / "ecb-coverage.tex", ["Section", "Statistic fixed by the instructions", "Engine id", "Status"], rows,
                 caption="Statistics that the ECB 2019 instructions for reporting IRB credit-risk validation results fix, with the registered test of the engine that "
                         "implements each as specified, the one related test that departs from the specification, and the statistics the engine does not implement.",
                 label="tab:ecb-coverage", align="lp{5.4cm}p{4.4cm}l")


def table_conformance() -> None:
    names = {"pd.jeffreys": "Jeffreys test", "disc.auc_vs_initial": "AUC against development AUC", "rating.mwb": "Matrix weighted bandwidth",
             "rating.migration_ztests": "Migration z-tests (every cell)", "rating.hhi": "Concentration in grades"}
    rows = []
    for k, nm in names.items():
        v = pa[k]
        rows.append((nm, v["n_inputs"], tex_sci_cell(v["max_abs_diff"]), tex_sci_cell(v["mean_abs_diff"])))
    figkit.table(OUT / "ecb-conformance.tex", ["Test", "Random inputs", "Largest absolute difference", "Mean absolute difference"], rows,
                 caption="The five ECB statistics of the engine against an independent transcription of the instructions written with loops, the math module and "
                         "tanh-sinh quadrature, on seeded random inputs; the Jeffreys difference is the accuracy of the quadrature.",
                 label="tab:ecb-conformance", align="l>{\\raggedleft\\arraybackslash}p{2.4cm}>{\\raggedleft\\arraybackslash}p{2.9cm}>{\\raggedleft\\arraybackslash}p{2.9cm}", digits=0)


def table_toolkits() -> None:
    toks = list(inv_tokens())
    rows = []
    for t in toks:
        scan_hits = scan["hits"].get(t, {})
        sv_hits = [r["name"] for r in sv["rows"] if r.get("hits", {}).get(t)]
        rows.append((t, len(scan_hits), ", ".join(sorted(scan_hits)) or "--", len(sv_hits), ", ".join(sv_hits) or "--"))
    figkit.table(OUT / "toolkits.tex", ["Vocabulary", "Installed packages with a match", "Which", "PyPI texts with a match", "Which"], rows,
                 caption=f"Where the catalogue's vocabulary appears in the Python sources of {scan['distributions']} installed distributions and in the PyPI summary and "
                         f"description of {sv['found']} toolkits read on {sv['date']}; a match is a word, not an implementation of the specified test.",
                 label="tab:toolkits", align="p{2.9cm}>{\\raggedleft\\arraybackslash}p{2.2cm}p{3.1cm}>{\\raggedleft\\arraybackslash}p{2.2cm}p{3.1cm}", digits=0)


def inv_tokens():
    return scan["hits"].keys()


def table_ablation() -> None:
    rows = []
    for m in mut:
        rows.append((m["id"].replace("m", "P"), figkit.tex_escape(m["defect"]), "yes" if m["equivalent"] else "no") + tuple("x" if m["detected_by"][k] else "." for k in "ABCDE"))
    rows.append(("", "Detections of the defects that change a result", "") + tuple(str(sum(m["detected_by"][k] for m in real)) for k in "ABCDE"))
    figkit.table(OUT / "ablation.tex", ["Id", "Defect planted in the engine", "Equivalent", "A", "B", "C", "D", "E"], rows,
                 caption="Defects planted one at a time in the released engine and the verification layers that detect each: A analytic anchors, B published vectors and the "
                         "ECB transcription, C regeneration of the committed rung, D known-truth simulator, E cross-implementation; x marks a detection.",
                 label="tab:ablation", align="lp{6.4cm}cccccc", digits=0)


def table_main() -> None:
    q = mc["quantities"]
    rows = [
        ("ECB statistics", "five statistics, independent transcription", f"{ecbc['implemented']} of {ecbc['sections']} sections", "largest difference " + tex_sci_cell(max(
            pa[k]["max_abs_diff"] for k in pa), 1), "held (quadrature accuracy)"),
        ("ECB Jeffreys test, C01 holdout", "grades flagged at 5\\%, all models", f"{pb['alpha_0.05']['flag_jeffreys']} of {pb['cells']}",
         f"binomial {pb['alpha_0.05']['flag_binomial']} of {pb['cells']}", f"{pb['alpha_0.05']['disagree']} cell differs"),
        ("Large-portfolio law", "density integral against distribution function", tex_sci_cell(an["lhp_integral"]["max_abs_diff"]), "adaptive quadrature", "held"),
        ("IRB capital", "credit-card book, retail revolving", f(an["irb"]["k_scipy"], 6), "SciPy formula, difference 0", "held"),
        ("CreditRisk+ recursion", "mean, variance, probability of no loss", f"variance gap {tex_sci_cell(cf['rel_gap_var'])}", f"independent recursion {tex_sci_cell(ci_['max_abs_diff_stable'])}", "held"),
        ("Granularity adjustment", "delta at xi 0.25, level 0.999", f(an["granularity"]["delta"], 4), "published 4.83", "held"),
        ("Gaussian copula, 99.9\\% VaR", f"{mc['replications']} runs of {mc['scenarios_each']:,}", f"{q['var999']['engine_mean']:,.0f} $\\pm$ {q['var999']['engine_sd']:,.0f}",
         f"independent {q['var999']['independent_mean']:,.0f} $\\pm$ {q['var999']['independent_sd']:,.0f}", f"z {q['var999']['z_difference']:+.2f}"),
        ("Gaussian copula, 99\\% ES", f"{mc['replications']} runs of {mc['scenarios_each']:,}", f"{q['es99']['engine_mean']:,.0f} $\\pm$ {q['es99']['engine_sd']:,.0f}",
         f"independent {q['es99']['independent_mean']:,.0f} $\\pm$ {q['es99']['independent_sd']:,.0f}", f"z {q['es99']['z_difference']:+.2f}"),
        ("Committed seeded rung", f"{rg['n_scenarios']:,} scenarios, eight values", "relative difference " + tex_sci_cell(rg["max_rel_diff"]), "committed file", "held"),
        ("Importance sampler", f"{ie['replications']} seeds, P(L at or above 99.9\\% VaR)", f"{ie['is_mean']:.5f} $\\pm$ {tex_sci_cell(ie['is_sd'])}", f"plain {ie['plain_mean']:.5f} $\\pm$ {ie['plain_sd']:.5f}",
         f"z {-ie['z_difference']:+.2f}, variance ratio {ie['variance_ratio']:.0f}"),
        ("Correlation estimator, 24 cells", "coverage of the 95\\% interval, maximum likelihood", f"mean {NUMS['gridMlMeanCov'][0]}, lowest {NUMS['gridMlWorstCov'][0]}",
         f"band $\\pm${figkit.fmt(2.576 * math.sqrt(0.95 * 0.05 / gd['22']['n_replications']))}", f"{NUMS['gridMlFail'][0]} of {NUMS['gridMlCells'][0]} cells outside; {NUMS['gridMlBelow'][0]} below 0.95"),
        ("Correlation estimator, 24 cells", "coverage, moments", f"mean {NUMS['gridMomMeanCov'][0]}", "same band", f"{NUMS['gridMomFail'][0]} of {NUMS['gridMomCells'][0]} cells outside"),
        ("IRRBB shock shapes", "SRP31.92 example, flattener", f"{we['flattener']['engine']:.2f} bp", "printed $-1.6$ bp", f"deviation {we['flattener']['abs_dev']:.3f} bp"),
        ("IRRBB present values", f"{va['n_legs_shocks']} leg and shock pairs, six variants", "relative difference " + tex_sci_cell(va["max_rel_ql"]), "QuantLib", "held"),
    ]
    rows = [[("\\relax " + c) if isinstance(c, str) and not c.startswith(("$", "\\")) else c for c in r] for r in rows]
    figkit.table(OUT / "main-results.tex", ["Component", "Quantity", "Engine", "Reference", "Outcome"], rows,
                 caption="Main comparison: each component of the engine against the independent reference run on the same input, with the repetition uncertainty (plus or minus one "
                         "standard deviation) where the quantity is random; z is the difference of the two means over its standard error.",
                 label="tab:main-results", align="p{2.8cm}p{3.2cm}p{2.7cm}p{2.9cm}p{2.3cm}", wide=False)


def table_grid() -> None:
    rows = []
    for y in ("22", "40"):
        for c in gd[y]["cells"]:
            rows.append((int(y), c["rho"], c["maximum-likelihood"]["coverage"], c["maximum-likelihood"]["z_coverage"],
                         c["moments"]["coverage"], c["moments"]["z_coverage"]))
    sel = [r for r in rows if round(r[1], 2) in (0.02, 0.12, 0.24)]
    figkit.table(OUT / "grid.tex", ["Years", "True correlation", "ML coverage", "z", "Moments coverage", "z"], sel,
                 caption=f"Coverage of the nominal 95\\% interval at three of the twelve known correlations of the committed simulator, for 22 and 40 years, with {gd['22']['n_replications']} "
                         "replications per cell; z is the distance of the coverage from 0.95 in binomial standard errors.", label="tab:grid", align="rrrrrr", digits=3)


def table_notation() -> None:
    rows = [("$\\PD$, $\\LGD$, $\\EAD$", "probability of default, loss given default, exposure at default", "decimal, decimal, money"),
            ("$\\rho$", "asset correlation of the one-factor model", "decimal"),
            ("$N$, $D$", "obligors and defaults of a grade in the observation year", "count"),
            ("$S$", "statistic of a validation test", "varies"),
            ("$\\Phi$", "standard normal distribution function", "--"),
            ("$\\delta$, $\\xi$, $\\gamma$", "granularity adjustment factor; precision of the Gamma systematic factor (variance $1/\\xi$); LGD-variance parameter, $\\mathrm{V}[\\mathrm{LGD}]=\\gamma\\,\\mathrm{E}[\\mathrm{LGD}](1-\\mathrm{E}[\\mathrm{LGD}])$", "decimal"),
            ("$\\sigma^2$", "variance of the common factor $Y$ of CreditRisk+", "decimal"),
            ("$\\nu_i$, $M_i$", "loss of name $i$ in units of the loss unit; Poisson count of defaults of name $i$", "integer, count"),
            ("$Y$", "common Gamma factor of CreditRisk+, mean one", "decimal"),
            ("$\\vartheta$", "shift that a planted defect adds to the mean of a stochastic component", "as the component"),
            ("$t_k$, $r_k$", "mid-point of time bucket $k$ and its continuously compounded zero rate", "years, decimal"),
            ("$\\mathrm{CF}_k$", "net cash flow of bucket $k$", "money"),
            ("$\\Delta_s(t)$", "shock $s$ in basis points at time $t$", "basis points")]
    # figkit.table escapes a cell that does not start with a command or a dollar sign; a meaning that carries math starts with \relax
    rows = [(a, ("\\relax " + b) if "$" in b else b, c) for a, b, c in rows]
    figkit.table(OUT / "notation.tex", ["Symbol", "Meaning", "Unit"], rows,
                 caption="Notation used in the problem formulation, the proposed method and the theory, with the unit of each symbol; further symbols are defined where they first appear in an equation.",
                 label="tab:notation", align="lp{8.2cm}l")


for fn in (table_runs, table_catalogue, table_ecb, table_conformance, table_toolkits, table_ablation, table_main, table_grid, table_notation):
    fn()
lines = ["% Generated by make_tables.py from experiments/results_*.json; do not edit."]
for k, (v, s) in NUMS.items():
    lines.append(f"% {s}")
    lines.append(f"\\newcommand{{\\{k}}}{{{v}}}")
(OUT / "numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print(len(NUMS), "numbers;", len(list(OUT.glob("*.tex"))), "files")
