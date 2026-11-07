"""Builds every table and every number macro of the manuscript from the committed outputs, so that no number is typed by hand.

Inputs: ``experiments/results/*.json`` (the experiment scripts of this folder) and the committed documents of ``data/derived``
(C01, C02, C03, C22). Outputs: ``tables/tab-*.tex`` (booktabs floats, ``\\input`` by the sections), ``tables/numbers.tex`` (one
``\\num@<key>`` macro per quoted number, typeset with ``\\nv{<key>}``) and ``tables/numbers.json`` (the source of each key).

    python manuscripts/leakage-safe-validation-protocol/make_artifacts.py
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
sys.path.insert(0, str(HERE / "experiments"))
import figkit  # noqa: E402
import leaklab as L  # noqa: E402

_table = figkit.table


def _raw(v):
    if isinstance(v, str) and ("\\" in v or "$" in v) and not (v.startswith("$") or v.startswith("\\")):
        return "\\relax " + v
    return v


def table(path, header, rows, **kw):
    """figkit.table with every text cell that carries LaTeX passed through as it is (figkit escapes any other text), and the tabular
    scaled to the text width when it is wider (the shared fitwidth macro of the preamble)."""
    out = _table(path, header, [[_raw(c) for c in r] for r in rows], **kw)
    txt = pathlib.Path(out).read_text(encoding="utf-8")
    txt = txt.replace("\\begin{tabular}", "\\fitwidth{%\n\\begin{tabular}", 1).replace("\\end{tabular}", "\\end{tabular}%\n}", 1)
    pathlib.Path(out).write_text(txt, encoding="utf-8", newline="\n")
    return out


figkit_table = table
RES = HERE / "experiments" / "results"
TAB = HERE / "tables"
NUM: dict[str, dict[str, str]] = {}

LK = {"none": "none", "impute_full": "imp", "scale_full": "scale", "bin_full": "bin", "woe_full": "woe", "screen_full": "scr",
      "fit_full": "fit", "select_test": "sel", "cal_test": "caltest", "cal_overlap": "calov", "cv_in": "cvin", "cv_pre": "cvpre",
      "fit_full_": "fit"}
LEAK_TEXT = {
    "none": "proposed protocol", "impute_full": "imputation on all rows", "scale_full": "scaling on all rows",
    "bin_full": "bin edges on all rows", "woe_full": "WoE with holdout labels", "screen_full": "screen with holdout labels",
    "fit_full": "everything fitted on training and holdout", "select_test": "configuration chosen on the holdout",
    "cal_test": "calibration map fitted on the holdout", "cal_overlap": "calibration slice overlapping the holdout",
    "cv_in": "five-fold, preprocessing inside the folds", "cv_pre": "five-fold, preprocessing before the folds"}
MK = {"woe": "w", "linear": "l", "product": "p"}
MODEL_TEXT = {"woe": "WoE scorecard", "linear": "standardised logit", "product": "product scorecard"}


def sg(x: float, d: int = 3) -> str:
    s = f"{abs(x):.{d}f}"
    if float(s) == 0.0:
        return s
    return ("+" if x > 0 else "$-$") + s


def put(key: str, text: str, source: str) -> str:
    NUM[key] = {"text": text, "source": source}
    return text


def load(name: str) -> dict:
    return json.loads((RES / name).read_text(encoding="utf-8"))


def ratio(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}"


# ---------------------------------------------------------------------------------------------------------- E1 numbers

def e1_numbers() -> dict[str, dict]:
    out = {}
    for ds, f in (("syn", "e1_synthetic.json"), ("small", "e1_synthetic-small.json"), ("tw", "e1_taiwan.json"),
                  ("prod", "e1_product.json")):
        d = load(f)
        out[ds] = d
        put(f"{ds}.reps", str(d["reps"]), f"experiments/results/{f} reps")
        put(f"{ds}.n", f"{d['n_total']:,}", f"experiments/results/{f} n_total")
        put(f"{ds}.oracle", f"{d['n_oracle']:,}", f"experiments/results/{f} n_oracle")
        put(f"{ds}.p", str(d["p"]), f"experiments/results/{f} p")
        put(f"{ds}.seed", str(d["base_seed"]), f"experiments/results/{f} base_seed")
        for key, v in d["summary"].items():
            m, leak = key.split("/")
            k = f"{ds}.{MK[m]}.{LK[leak]}"
            src = f"experiments/results/{f} summary[{key}]"
            put(f"{k}.bias", sg(v["auc_bias"]), src + ".auc_bias")
            put(f"{k}.abias", f"{abs(v['auc_bias']):.3f}", src + ".auc_bias")
            put(f"{k}.ci", f"{1.96 * v['auc_bias_se']:.3f}", src + ".auc_bias_se x 1.96")
            put(f"{k}.rmse", f"{v['auc_rmse']:.3f}", src + ".auc_rmse")
            put(f"{k}.est", f"{v['auc_est']:.3f}", src + ".auc_est")
            put(f"{k}.orc", f"{v['auc_oracle']:.3f}", src + ".auc_oracle")
            if "coverage" in v:
                put(f"{k}.cov", ratio(v["coverage"]), src + ".coverage")
                put(f"{k}.covlo", ratio(v["coverage_lo"]), src + ".coverage_lo")
                put(f"{k}.covhi", ratio(v["coverage_hi"]), src + ".coverage_hi")
                put(f"{k}.brier", sg(v["brier_bias"], 4), src + ".brier_bias")
                put(f"{k}.brierci", f"{1.96 * v['brier_bias_se']:.4f}", src + ".brier_bias_se x 1.96")
                put(f"{k}.ece", sg(v["ece_bias"], 4), src + ".ece_bias")
    # the split sizes the design implies
    rng = np.random.default_rng(1)
    for ds, n in (("syn", 2500), ("small", 800)):
        _, y = L.planted(n, 40, rng)
        tr, ca, ho = L.stratified_slices(y, rng)
        put(f"{ds}.train", f"{len(tr):,}", "leaklab.stratified_slices on a planted sample")
        put(f"{ds}.cal", f"{len(ca):,}", "leaklab.stratified_slices on a planted sample")
        put(f"{ds}.hold", f"{len(ho):,}", "leaklab.stratified_slices on a planted sample")
    return out


# ------------------------------------------------------------------------------------------------------------ E1 tables

def pm(v: float, ci: float, d: int = 3) -> str:
    s = f"{abs(v):.{d}f}"
    sign = "" if float(s) == 0 or v > 0 else "-"
    plus = "+" if v > 0 else ""
    return f"${plus}{sign}{s}\\pm{ci:.{d}f}$"


def main_table(d: dict) -> None:
    rows = []
    for m in ("woe", "linear"):
        for leak in (["none", "impute_full", "bin_full", "woe_full", "screen_full", "fit_full", "select_test", "cal_test", "cal_overlap",
                      "cv_in", "cv_pre"] if m == "woe" else
                     ["none", "impute_full", "scale_full", "screen_full", "fit_full", "select_test", "cal_test", "cal_overlap",
                      "cv_in", "cv_pre"]):
            v = d["summary"][f"{m}/{leak}"]
            cov = (f"{100 * v['coverage']:.1f} [{100 * v['coverage_lo']:.0f}, {100 * v['coverage_hi']:.0f}]"
                   if "coverage" in v else "--")
            br = pm(v["brier_bias"], 1.96 * v["brier_bias_se"], 4) if "brier_bias" in v else "--"
            ec = pm(v["ece_bias"], 1.96 * v["ece_bias_se"], 4) if "ece_bias" in v else "--"
            rows.append([MODEL_TEXT[m] if leak == "none" else "", LEAK_TEXT[leak], pm(v["auc_bias"], 1.96 * v["auc_bias_se"]),
                         v["auc_rmse"], cov, br, ec])
    table(TAB / "tab-main-results.tex",
                 ["Model", "Validation procedure", "AUC bias $\\pm$ 95\\% half-width", "RMSE", "Coverage \\% [Wilson 95\\%]",
                  "Brier bias", "ECE bias"], rows,
                 caption=(f"Bias of the holdout estimate of the AUC, the Brier score and the calibration error against the value on a "
                          f"reference sample of {d['n_oracle']:,} rows that no step read, for the proposed protocol and for each leaked "
                          f"variant, on {d['reps']} planted data sets of {d['n_total']:,} rows with {d['p']} inputs; the coverage column "
                          f"is the share of the 95\\% intervals of the engine's AUC variance that contain the reference value. "
                          f"The two five-fold rows compare the cross-validated AUC with the mean reference AUC of the fold models."),
                 label="tab:main-results", align="llrrrrr", digits=3, wide=True)


def other_table(sets: dict) -> None:
    leaks = ["none", "impute_full", "bin_full", "woe_full", "screen_full", "fit_full", "select_test", "cal_test", "cal_overlap", "cv_in",
             "cv_pre"]
    rows = []
    for leak in leaks:
        row = [LEAK_TEXT[leak]]
        for ds in ("small", "tw"):
            v = sets[ds]["summary"][f"woe/{leak}"]
            row += [pm(v["auc_bias"], 1.96 * v["auc_bias_se"]), f"{100 * v['coverage']:.0f}" if "coverage" in v else "--"]
        pv = sets["prod"]["summary"].get(f"product/{leak}")
        row += [pm(pv["auc_bias"], 1.96 * pv["auc_bias_se"]) if pv else "--", f"{100 * pv['coverage']:.0f}" if pv else "--"]
        rows.append(row)
    table(TAB / "tab-other-data.tex",
                 ["Validation procedure", "Small sample bias", "Cov.", "Card holders bias", "Cov.", "Product scorecard bias", "Cov."], rows,
                 caption=(f"Bias of the holdout AUC (with its 95\\% half-width) and coverage of the 95\\% interval in percent for the WoE "
                          f"scorecard on planted data of {sets['small']['n_total']} rows ({sets['small']['reps']} repetitions), on the "
                          f"{sets['tw']['n_total']:,}-row subsamples of the 30,000 card holders of C01 ({sets['tw']['reps']} repetitions, "
                          f"10,000 rows set aside per repetition as the reference), and for the product's own optbinning scorecard on "
                          f"planted data ({sets['prod']['reps']} repetitions; only the variants that call the product's fit appear)."),
                 label="tab:other-data", align="lrrrrrr", wide=True)


# ------------------------------------------------------------------------------------------------------------------- E2

def e2_numbers_tables() -> dict:
    m = load("e2_matrix.json")
    dr = load("e2_draws.json")
    ld = load("e2_ladder.json")
    put("e2.reps", str(m["reps"]), "experiments/results/e2_matrix.json reps")
    put("e2.n", f"{m['n']:,}", "experiments/results/e2_matrix.json n")
    for key, v in m["pass_rates"].items():
        model, leak = key.split("/")
        k = f"e2.{MK[model]}.{LK[leak]}"
        src = f"experiments/results/e2_matrix.json pass_rates[{key}]"
        for g in ("G1", "G2", "G3"):
            put(f"{k}.{g}", f"{100 * (1 - v[g]):.0f}", src + f".{g} (detection = 1 - pass rate)")
        put(f"{k}.any", f"{100 * v['any_gate_fails']:.0f}", src + ".any_gate_fails")
        put(f"{k}.nv", f"{100 * v['non_vacuous']:.0f}", src + ".non_vacuous")
    for model, vals in dr["detection_by_draws"].items():
        for dd, p in vals.items():
            put(f"e2.draws.{MK[model]}.{dd}", f"{100 * p:.1f}", f"experiments/results/e2_draws.json detection_by_draws[{model}][{dd}]")
    put("e2.draws.reps", str(dr["reps"]), "experiments/results/e2_draws.json reps")
    for name, c in ld["conditions"].items():
        put(f"e2.ladder.{name}.changed", str(c["rungs_changed"]), f"experiments/results/e2_ladder.json conditions[{name}].rungs_changed")
        put(f"e2.ladder.{name}.rungs", str(c["rungs"]), f"experiments/results/e2_ladder.json conditions[{name}].rungs")
    put("e2.ladder.n", f"{ld['n']:,}", "experiments/results/e2_ladder.json n")
    put("e2.ladder.seconds", f"{ld['seconds']:.0f}", "experiments/results/e2_ladder.json seconds (the three conditions, one machine)")
    put("e2.ladder.hold", f"{ld['holdout_n']:,}", "experiments/results/e2_ladder.json holdout_n")
    rows = []
    for key, v in m["pass_rates"].items():
        model, leak = key.split("/")
        if leak == "none":
            rows.append([MODEL_TEXT[model], "none (false alarm rate)"] + [f"{100 * (1 - v[g]):.0f}" for g in ("G1", "G2", "G3")] +
                        [f"{100 * v['any_gate_fails']:.0f}"])
        else:
            rows.append(["", LEAK_TEXT[leak]] + [f"{100 * (1 - v[g]):.0f}" for g in ("G1", "G2", "G3")] + [f"{100 * v['any_gate_fails']:.0f}"])
    table(TAB / "tab-gates.tex", ["Model", "Leak planted in the fitting path", "G1", "G2", "G3", "Any gate"], rows,
                 caption=(f"Share of {m['reps']} data draws of {m['n']:,} rows in which each gate fails, so that the leak is detected: G1 moves "
                          f"the inputs outside the training slice, G2 requires disjoint slices and a calibration map unchanged when the "
                          f"holdout labels are flipped, G3 perturbs the holdout inputs and labels (one perturbation draw) and requires every "
                          f"fitted parameter unchanged. The first row of each model is the proposed protocol, where a failure is a false alarm."),
                 label="tab:gates", align="llrrrr")
    return {"matrix": m, "draws": dr, "ladder": ld}


# ------------------------------------------------------------------------------------------------------------------- E3

def e3_numbers_tables() -> dict:
    d = load("e3_planted_leak.json")
    th = load("theory_checks.json")
    put("e3.reps", str(d["reps"]), "experiments/results/e3_planted_leak.json reps")
    rows = []
    for s, v in d["levels"].items():
        k = f"e3.s{s}"
        src = f"experiments/results/e3_planted_leak.json levels[{s}]"
        put(f"{k}.dev", f"{v['dev_auc']['mean']:.3f}", src + ".dev_auc.mean")
        put(f"{k}.devcf", f"{v['closed_form']['dev_auc']:.3f}", src + ".closed_form.dev_auc")
        put(f"{k}.cur", f"{v['cur_auc']['mean']:.3f}", src + ".cur_auc.mean")
        put(f"{k}.curcf", f"{v['closed_form']['cur_auc']:.3f}", src + ".closed_form.cur_auc")
        put(f"{k}.feat", f"{v['closed_form']['feature_auc']:.3f}", src + ".closed_form.feature_auc")
        put(f"{k}.infl", f"{v['closed_form']['dev_auc'] - v['closed_form']['cur_auc']:.3f}", src + ".closed_form dev_auc - cur_auc")
        for t in ("auc_test", "csi_test", "single_feature_flag", "resemblance_flag"):
            put(f"{k}.{t}", ratio(v[t]["rate"]), src + f".{t}.rate")
        put(f"{k}.psi", f"{v['psi']['mean']:.4f}", src + ".psi.mean")
        put(f"{k}.psipop", f"{v['engine_truth']['feature_population_psi']:.4f}", src + ".engine_truth.feature_population_psi")
        zdev = (v["dev_auc"]["mean"] - v["closed_form"]["dev_auc"]) / v["dev_auc"]["se"]
        zcur = (v["cur_auc"]["mean"] - v["closed_form"]["cur_auc"]) / v["cur_auc"]["se"]
        put(f"{k}.zdev", f"{zdev:.1f}", src + " (simulated mean - closed form) / se")
        put(f"{k}.zcur", f"{zcur:.1f}", src + " (simulated mean - closed form) / se")
        rows.append([f"{float(s):g}", f"{v['dev_auc']['mean']:.3f}", f"{v['closed_form']['dev_auc']:.3f}", f"{v['cur_auc']['mean']:.3f}",
                     f"{v['closed_form']['cur_auc']:.3f}", ratio(v["auc_test"]["rate"], 1), ratio(v["csi_test"]["rate"], 1),
                     ratio(v["resemblance_flag"]["rate"], 1), ratio(v["single_feature_flag"]["rate"], 1)])
    table(TAB / "tab-planted-leak.tex",
                 ["Leak $s$", "Dev. AUC sim.", "Dev. AUC Prop.", "Current AUC sim.", "Current AUC Prop.", "AUC test power",
                  "CSI power", "Resemblance power", "Single-feature flag"], rows,
                 caption=(f"The leak planted by the engine generator (150 defaulters and 4,850 survivors per sample, {d['reps']} repetitions per "
                          f"level): simulated mean AUC in development and at decision time beside the closed forms of Proposition 4, and "
                          f"the percentage of repetitions in which each detector rejects at 5\\%: the AUC-against-development test, the "
                          f"characteristic stability index of the leaked feature, the resemblance AUC and the single-feature AUC screen "
                          f"at its default threshold of 0.95."),
                 label="tab:planted-leak", align="rrrrrrrrr", wide=True)
    # theory numbers
    for mm, v in th["detection"]["by_m"].items():
        put(f"th.det.{mm}.sim", f"{100 * v['simulated']:.1f}", f"experiments/results/theory_checks.json detection.by_m[{mm}].simulated")
        put(f"th.det.{mm}.exact", f"{100 * v['exact']:.1f}", f"experiments/results/theory_checks.json detection.by_m[{mm}].exact")
        put(f"th.det.{mm}.approx", f"{100 * v['approx']:.1f}", f"experiments/results/theory_checks.json detection.by_m[{mm}].approx")
    put("th.det.trials", f"{th['detection']['trials']:,}", "experiments/results/theory_checks.json detection.trials")
    put("th.det.ntrain", f"{th['detection']['n_train']:,}", "experiments/results/theory_checks.json detection.n_train")
    put("th.det.nout", f"{th['detection']['n_out']:,}", "experiments/results/theory_checks.json detection.n_out")
    for K, v in th["max_bound"]["in_units_of_sigma"].items():
        put(f"th.max.{K}.bound", f"{v['bound']:.2f}", f"experiments/results/theory_checks.json max_bound[{K}].bound")
        for r in ("0.0", "0.5", "0.9"):
            put(f"th.max.{K}.r{r}", f"{v['rho=' + r]:.2f}", f"experiments/results/theory_checks.json max_bound[{K}][rho={r}]")
    for s, v in th["psi"].items():
        if s.startswith("null"):
            put("th.psi.null", f"{v:.4f}", "experiments/results/theory_checks.json psi.null_expectation_10_bins")
            continue
        for k2 in ("engine_psi", "binned_chi2_form", "continuous_form"):
            put(f"th.psi.{s}.{k2}", f"{v[k2]:.4f}", f"experiments/results/theory_checks.json psi[{s}].{k2}")
    for s, v in th["leak_auc"]["optimal_weights"].items():
        for k2 in ("dev", "cur", "clean"):
            put(f"th.opt.{s}.{k2}", f"{v[k2]:.3f}", f"experiments/results/theory_checks.json leak_auc.optimal_weights[{s}].{k2}")
    rows = []
    for mm, v in th["detection"]["by_m"].items():
        rows.append([f"edge shift, m = {mm}", f"{100 * v['simulated']:.1f} $\\pm$ {196 * v['se']:.1f}", f"{100 * v['exact']:.2f}", f"{100 * v['approx']:.2f}"])
    table(TAB / "tab-theory-detection.tex", ["Perturbation of the outside rows", "Simulated detection (\\%)", "Exact (\\%)",
                                                    "$1-0.1^m$ (\\%)"], rows,
                 caption=(f"Probability that sending m outside rows beyond the training range changes at least one decile edge of a "
                          f"pooled sample of {th['detection']['n_train'] + th['detection']['n_out']:,} rows ({th['detection']['n_train']:,} "
                          f"development and {th['detection']['n_out']:,} outside), simulated with the pipeline's own edge function over "
                          f"{th['detection']['trials']:,} trials per row, against the exact hypergeometric expression and its approximation "
                          f"of Proposition 2."),
                 label="tab:theory-detection", align="lrrr")
    return {"e3": d, "th": th}


# ------------------------------------------------------------------------------------------------------------------- E4

def e4_numbers_tables() -> dict:
    d = load("e4_out_of_time.json")
    rows = []
    for c in d["cohorts"]:
        k = f"e4.{c['id'].replace('fy', '')}"
        src = f"experiments/results/e4_out_of_time.json cohorts[{c['cohort']}]"
        put(f"{k}.window", f"{c['window_loans']:,}", src + ".window_loans")
        put(f"{k}.hold", f"{c['random_holdout_rows']:,}", src + ".random_holdout_rows")
        put(f"{k}.oot", f"{c['oot_rows']:,}", src + ".oot_rows")
        put(f"{k}.lastfy", str(c["window"][1]), src + ".window[1]")
        put(f"{k}.cutoff", c["cutoff"], src + ".cutoff")
        put(f"{k}.rate_random", ratio(c["random_rate"]), src + ".random_rate")
        put(f"{k}.rate_oot", ratio(c["oot_rate"]), src + ".oot_rate")
        for rid, short in (("P1-scorecard", "sc"), ("P4-lightgbm", "gbm")):
            r = c["rungs"][rid]
            for f_ in ("random_auc", "oot_auc", "random_brier", "oot_brier"):
                put(f"{k}.{short}.{f_}", f"{r[f_]:.3f}", src + f".rungs[{rid}].{f_}")
            for f_ in ("random_gap", "oot_gap"):
                put(f"{k}.{short}.{f_}", sg(100 * r[f_], 1), src + f".rungs[{rid}].{f_} x 100 (points)")
                put(f"{k}.{short}.a{f_}", f"{abs(100 * r[f_]):.1f}", src + f".rungs[{rid}].{f_} x 100 (points)")
            put(f"{k}.{short}.dauc", f"{r['random_auc'] - r['oot_auc']:.3f}", src + f".rungs[{rid}] random_auc - oot_auc")
        sc, gb = c["rungs"]["P1-scorecard"], c["rungs"]["P4-lightgbm"]
        tv = abs(sc["oot_gap"] - sc["random_gap"]) / 2.0
        put(f"{k}.tv", f"{100 * tv:.1f}", src + " |oot_gap - random_gap| / 2 (lower bound on the total variation distance, points)")
        rows.append([c["cohort"], f"{c['window_loans']:,}", f"{sc['random_auc']:.3f}",
                     f"{sc['oot_auc']:.3f}", sg(100 * sc["random_gap"], 1), sg(100 * sc["oot_gap"], 1), f"{gb['random_auc']:.3f}",
                     f"{gb['oot_auc']:.3f}", sg(100 * gb["random_gap"], 1), sg(100 * gb["oot_gap"], 1)])
    table(TAB / "tab-out-of-time.tex",
                 ["Cohort", "Window loans", "\\shortstack{Score.\\\\AUC rand.}", "\\shortstack{Score.\\\\AUC OOT}", "\\shortstack{Score.\\\\gap rand.}",
                  "\\shortstack{Score.\\\\gap OOT}", "\\shortstack{GBM\\\\AUC rand.}", "\\shortstack{GBM\\\\AUC OOT}", "\\shortstack{GBM\\\\gap rand.}",
                  "\\shortstack{GBM\\\\gap OOT}"], rows,
                 caption=("Two estimates of the same fitted models on the SBA 7(a) loans of C03: a random sample of the training window's own "
                          "loans that neither the fit nor the calibration used (rand.), and the declared out-of-time cohort at the 5-year mark of each "
                          "vintage (OOT). The gap is the observed minus the predicted 5-year charge-off rate in percentage points; the columns "
                          "are the WoE scorecard (Score.) and the monotone gradient-boosting rung (GBM), and the training window of each cohort is in the table of splits."),
                 label="tab:out-of-time", align="lrrrrrrrrr", wide=True)
    for c_, v in d["reproduction"].items():
        key = "e4." + c_.replace("FY", "").replace("-", "_")
        put(key + ".repauc", f"{v['committed_scorecard_auc']:.3f}", f"experiments/results/e4_out_of_time.json reproduction[{c_}].committed_scorecard_auc")
        put(key + ".rundiff", f"{abs(v['committed_scorecard_auc'] - v['run_scorecard_auc']):.4f}",
            f"experiments/results/e4_out_of_time.json reproduction[{c_}] |committed - run|")
    put("e4.holdse", f"{100 * 0.5 / math.sqrt(d['random_holdout_cap']):.2f}",
        "experiments/results/e4_out_of_time.json random_holdout_cap: largest binomial standard error of a rate, 100 x 0.5 / sqrt(rows), points")
    put("e4.maxrepdiff",f"{max(abs(v['committed_scorecard_auc'] - v['run_scorecard_auc']) for v in d['reproduction'].values()):.4f}",
        "experiments/results/e4_out_of_time.json reproduction, maximum |committed - run| of the scorecard AUC")
    return d


# ------------------------------------------------------------------------------------------------------------------- E5

def e5_numbers_tables() -> dict:
    d = load("e5_cv_scaling.json")
    fit = d["loglog_fit_p40"]
    put("e5.exp", f"{abs(fit['exponent']):.2f}", "experiments/results/e5_cv_scaling.json loglog_fit_p40.exponent (absolute value)")
    put("e5.expse", f"{fit['exponent_se']:.2f}", "experiments/results/e5_cv_scaling.json loglog_fit_p40.exponent_se")
    put("e5.reps", str(d["reps"]), "experiments/results/e5_cv_scaling.json reps")
    rows = []
    for c in d["cells"]:
        k = f"e5.n{c['n']}.p{c['p']}"
        put(f"{k}.out", sg(c["outside"]["bias"]), f"experiments/results/e5_cv_scaling.json cells n={c['n']} p={c['p']} outside.bias")
        put(f"{k}.in", sg(c["inside"]["bias"]), f"experiments/results/e5_cv_scaling.json cells n={c['n']} p={c['p']} inside.bias")
        rows.append([f"{c['n']:,}", c["p"], pm(c["inside"]["bias"], 1.96 * c["inside"]["se"]), pm(c["outside"]["bias"], 1.96 * c["outside"]["se"])])
    table(TAB / "tab-cv-scaling.tex", ["Development rows", "Inputs", "Preprocessing inside the folds", "Preprocessing before the folds"],
                 rows, caption=(f"Bias of five-fold cross-validated AUC against the mean reference AUC of the fold models for the WoE scorecard on planted "
                                f"data (five informative inputs, the rest noise), {d['reps']} repetitions per row, with the preprocessing fitted "
                                f"inside each training fold or on all development rows before the folds; the 95\\% half-widths are over repetitions."),
                 label="tab:cv-scaling", align="rrrr")
    return d


# ------------------------------------------------------------------------------------------------------ committed splits

def split_table() -> None:
    der = figkit.DERIVED
    rows = []
    m = figkit.doc("C01/models-taiwan.json")["fit"]["split"]
    put("c01.train", f"{m['train']['n']:,}", "data/derived/C01/models-taiwan.json fit.split.train.n")
    put("c01.cal", f"{m['calibration']['n']:,}", "data/derived/C01/models-taiwan.json fit.split.calibration.n")
    put("c01.hold", f"{m['holdout']['n']:,}", "data/derived/C01/models-taiwan.json fit.split.holdout.n")
    put("c01.holdev", f"{m['holdout']['defaults']:,}", "data/derived/C01/models-taiwan.json fit.split.holdout.defaults")
    put("c01.rate", ratio(m["holdout"]["default_rate"]), "data/derived/C01/models-taiwan.json fit.split.holdout.default_rate")
    rows.append(["C01 card holders", "locked stratified holdout (30\\%), calibration slice, training slice",
                 f"{m['train']['n']:,} / {m['calibration']['n']:,} / {m['holdout']['n']:,}", f"{m['holdout']['defaults']:,}",
                 "none: single snapshot"])
    for h in ("h1", "h2", "h3", "h4", "h5"):
        s = figkit.doc(f"C02/{h}.json")["outputs"]["split"]
        put(f"c02.{h}.hold", f"{s['holdout_rows']:,}", f"data/derived/C02/{h}.json outputs.split.holdout_rows")
        put(f"c02.{h}.ev", f"{s['holdout_events']:,}", f"data/derived/C02/{h}.json outputs.split.holdout_events")
        rows.append([f"C02 horizon {h[1]}", "locked stratified holdout, calibration map on a separate slice",
                     f"{s['train_rows']:,} / {s['calibration_rows']:,} / {s['holdout_rows']:,}", f"{s['holdout_events']:,}",
                     "none: files carry no date" if not s["out_of_time_claim"] else "yes"])
    for cid in ("fy2006-07", "fy2008-10", "fy2011-14", "fy2015-17", "fy2018-20"):
        doc = figkit.doc(f"C03/{cid}.json")["outputs"]
        t, c = doc["training"], doc["cohort"]
        put(f"c03.{cid[2:]}.nloans", f"{t['n_loans']:,}", f"data/derived/C03/{cid}.json outputs.training.n_loans")
        put(f"c03.{cid[2:]}.events", f"{t['n_events']:,}", f"data/derived/C03/{cid}.json outputs.training.n_events")
        put(f"c03.{cid[2:]}.last", str(t["last_fy"]), f"data/derived/C03/{cid}.json outputs.training.last_fy")
        put(f"c03.{cid[2:]}.cutoff", t["cutoff_date"], f"data/derived/C03/{cid}.json outputs.training.cutoff_date")
        rows.append([f"C03 cohort FY{cid[2:6]}-{cid[7:]}", f"out-of-time cohort at the 5-year mark; window FY{t['first_fy']} to FY{t['last_fy']}, "
                                                           f"outcomes read to {t['cutoff_date']}", f"{t['n_loans']:,} window loans",
                     f"{t['n_events']:,}", "yes"])
    table(TAB / "tab-splits.tex", ["Case", "Split declared in the artifact", "Training / calibration / holdout rows", "Events",
                                         "Out-of-time claim"], rows,
                 caption=("The split each case declares in its committed documents: the locked stratified holdout and the disjoint calibration "
                          "slice of C01 and C02 (the events are those of the holdout) and the out-of-time training windows of C03 (the events are "
                          "the window's 5-year charge-offs), with the out-of-time claim each case makes or declines to make."),
                 label="tab:splits", align="llrrl", wide=True)


# ------------------------------------------------------------------------------------------------- hypotheses, ablation

def hypotheses(e1: dict, e2: dict, e3: dict, e4: dict, e5: dict) -> None:
    S, Sm, T = e1["syn"]["summary"], e1["small"]["summary"], e1["tw"]["summary"]
    P = e1["prod"]["summary"]

    def ci0(v):
        return abs(v["auc_bias"]) <= 1.96 * v["auc_bias_se"]

    def pos(v):
        return v["auc_bias"] - 1.96 * v["auc_bias_se"] > 0

    h1 = [ci0(ds[f"{m}/none"]) and ds[f"{m}/none"]["coverage_lo"] <= 0.95 <= ds[f"{m}/none"]["coverage_hi"]
          for ds in (S, Sm, T) for m in ("woe", "linear")]
    h1 += [ci0(P["product/none"]) and P["product/none"]["coverage_lo"] <= 0.95 <= P["product/none"]["coverage_hi"]]
    # every cell of the paper in which a step reads holdout labels: each model over the cells it has
    h2_cells = {"woe": ["woe_full", "screen_full", "fit_full"], "linear": ["screen_full", "fit_full"]}
    h2 = {name: [pos(ds[f"{m}/{lk}"]) for m, lks in h2_cells.items() for lk in lks]
          for name, ds in (("syn", S), ("small", Sm), ("tw", T))}
    h2["prod"] = [pos(P["product/fit_full"])]
    h3 = [abs(ds[f"{m}/{lk}"]["auc_bias"]) < 0.005 for ds in (S, Sm, T) for m, lk in (("woe", "impute_full"), ("woe", "bin_full"),
                                                                                 ("linear", "impute_full"), ("linear", "scale_full"))]
    h4 = [pos(ds[f"{m}/cal_test"]) and ds[f"{m}/cal_test"]["brier_bias"] + 1.96 * ds[f"{m}/cal_test"]["brier_bias_se"] < 0
          for ds in (S, Sm, T) for m in ("woe", "linear")]
    h4 += [pos(P["product/cal_test"]) and P["product/cal_test"]["brier_bias"] + 1.96 * P["product/cal_test"]["brier_bias_se"] < 0]
    put("h1.cells", str(len(h1)), "make_artifacts.hypotheses H1: cells scored (two models on three data sets and the product's scorecard)")
    put("h1.ok", str(sum(h1)), "make_artifacts.hypotheses H1: cells that satisfy the rule")
    put("h4.cells", str(len(h4)), "make_artifacts.hypotheses H4: cells scored")
    put("h2.cells.tw", str(len(h2["tw"])), "make_artifacts.hypotheses H2: label-reading cells on the card holders")
    put("h2.ok.tw", str(sum(h2["tw"])), "make_artifacts.hypotheses H2: label-reading cells on the card holders whose bias interval is above 0")
    mt = e2["matrix"]["pass_rates"]
    detect_any = {k: v["any_gate_fails"] for k, v in mt.items() if not k.endswith("/none")}
    false_alarm = {k: v["any_gate_fails"] for k, v in mt.items() if k.endswith("/none")}
    put("h5.detected", str(sum(1 for v in detect_any.values() if v >= 0.999)), "experiments/results/e2_matrix.json leaks with any_gate_fails = 1")
    put("h5.total", str(len(detect_any)), "experiments/results/e2_matrix.json leak rows")
    put("h5.minany", ratio(min(detect_any.values()), 0), "experiments/results/e2_matrix.json minimum any_gate_fails over leaks")
    put("h5.false", ratio(max(false_alarm.values()), 0), "experiments/results/e2_matrix.json maximum any_gate_fails on the protocol")
    lv = e3["e3"]["levels"]
    h6 = lv["0.5"]["auc_test"]["lo"] >= 0.97 and lv["1.0"]["csi_test"]["hi"] <= 0.20 and lv["1.0"]["single_feature_flag"]["hi"] <= 0.02
    h7 = all(abs(v["dev_auc"]["mean"] - v["closed_form"]["dev_auc"]) <= 3 * v["dev_auc"]["se"] and
             abs(v["cur_auc"]["mean"] - v["closed_form"]["cur_auc"]) <= 3 * v["cur_auc"]["se"] for v in lv.values())
    rungs = ("P1-scorecard", "P4-lightgbm")
    cells8 = [(c["cohort"], r, c["rungs"][r]["random_gap"], c["rungs"][r]["oot_gap"]) for c in e4["cohorts"] for r in rungs]
    h8a = sum(abs(rg) < 0.01 for _, _, rg, _ in cells8)
    h8b = sum(abs(og) >= 0.02 for _, _, _, og in cells8)
    h8 = h8a == len(cells8) and h8b == len(cells8)
    h8fail = [(coh, r, og) for coh, r, _, og in cells8 if abs(og) < 0.02]
    put("h8.cells", str(len(cells8)), "two printed rungs times five cohorts")
    put("h8.rand", str(h8a), "cells with |random gap| < 1 point")
    put("h8.oot", str(h8b), "cells with |out-of-time gap| >= 2 points")
    put("h8.failed", " and ".join(f"{coh[2:]} ({sg(100 * og, 1)})" for coh, r, og in h8fail), "cells of the gradient-boosting rung below 2 points")
    c03min = min(abs(next(r for r in figkit.doc(f"C03/{cid}.json")["outputs"]["rung_comparison"] if r["rung_id"] == "P1-scorecard")["calibration_gap_5y"])
                 for cid in ("fy2006-07", "fy2008-10", "fy2011-14", "fy2015-17", "fy2018-20"))
    put("c03.mingap", f"{100 * c03min:.2f}", "data/derived/C03/fy*.json outputs.rung_comparison[P1-scorecard].calibration_gap_5y, smallest absolute value x 100")
    h9pos = [pos(ds[f"{m}/cv_pre"]) for ds in (S, Sm, T) for m in ("woe", "linear")]
    h9null = [ci0(ds[f"{m}/cv_in"]) for ds in (S, Sm, T) for m in ("woe", "linear")]
    zin = abs(S["linear/cv_in"]["auc_bias"]) / S["linear/cv_in"]["auc_bias_se"]
    put("h9.in.z", f"{zin:.2f}", "experiments/results/e1_synthetic.json summary[linear/cv_in] |auc_bias| / auc_bias_se")
    put("h9.in.chance", f"{100 * (1 - 0.95 ** len(h9null)):.0f}", "100 x (1 - 0.95^n) for the n inside-fold cells: probability that at least one 95% interval excludes a true zero")
    put("h9.in.bias", sg(S["linear/cv_in"]["auc_bias"], 4), "experiments/results/e1_synthetic.json summary[linear/cv_in] auc_bias")
    put("h9.in.ci", f"{1.96 * S['linear/cv_in']['auc_bias_se']:.4f}", "experiments/results/e1_synthetic.json summary[linear/cv_in] auc_bias_se x 1.96")
    put("h9.in.n", str(len(h9null)), "number of inside-fold cells (two models on three data sets)")
    h9 = all(h9pos) and all(h9null)
    put("h9.pos", str(sum(h9pos)), "pairs of data set and model with the outside-fold bias interval above 0, of six")
    put("h9.null", str(sum(h9null)), "pairs of data set and model with the inside-fold bias interval containing 0, of six")
    put("h9.failcells", str(12 - sum(h9pos) - sum(h9null)), "cells of the twelve that fail")
    sel = e5["loglog_fit_p40"]
    res = {"H1": (all(h1), f"{sum(h1)} of {len(h1)} cells"), "H2": (all(all(v) for v in h2.values()),
           ", ".join(f"{k}: {sum(v)} of {len(v)}" for k, v in h2.items())), "H3": (all(h3), f"{sum(h3)} of {len(h3)} cells"),
           "H4": (all(h4), f"{sum(h4)} of {len(h4)} cells"), "H5": (all(v >= 0.999 for v in detect_any.values()) and max(false_alarm.values()) == 0,
           f"{sum(1 for v in detect_any.values() if v >= 0.999)} of {len(detect_any)} leaks, false alarms {100 * max(false_alarm.values()):.0f}\\%"),
           "H6": (h6, f"AUC test power {ratio(lv['0.5']['auc_test']['rate'])}\\% at s = 0.5; CSI power {ratio(lv['1.0']['csi_test']['rate'])}\\% and single-feature flag {ratio(lv['1.0']['single_feature_flag']['rate'])}\\% at s = 1"),
           "H7": (h7, f"largest absolute z {max(max(abs((v['dev_auc']['mean'] - v['closed_form']['dev_auc']) / v['dev_auc']['se']), abs((v['cur_auc']['mean'] - v['closed_form']['cur_auc']) / v['cur_auc']['se'])) for v in lv.values()):.1f} over seven levels"),
           "H8": (h8, f"random gap below 1 point in {h8a} of {len(cells8)} cohort and rung cells; "
                      f"out-of-time gap at least 2 points in {h8b} of {len(cells8)}"),
           "H9": (h9, f"outside-fold bias positive in {sum(h9pos)} of {len(h9pos)} and inside-fold bias null in {sum(h9null)} of {len(h9null)} "
                      f"pairs of data set and model")}
    nh = sum(1 for ok, _ in res.values() if ok)
    words = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}
    put("h.held", str(nh), "make_artifacts.hypotheses: predictions whose rule holds")
    put("h.notheld", str(9 - nh), "make_artifacts.hypotheses: predictions whose rule fails")
    put("h.held.word", words[nh], "make_artifacts.hypotheses")
    put("h.notheld.word", words[9 - nh], "make_artifacts.hypotheses")
    for k, (ok, ev) in res.items():
        put(f"verdict.{k}", "held" if ok else "not held", f"make_artifacts.hypotheses {k}")
        put(f"verdict.{k}.ev", ev, f"make_artifacts.hypotheses {k}")
    txt = {
        "H1": "The proposed protocol's holdout AUC is unbiased for the fitted model's true AUC (the 95\\% interval of the bias contains 0) and its 95\\% interval covers (the Wilson interval of the coverage contains 0.95); refuted if either fails in any cell (two models on three data sets, and the product's scorecard).",
        "H2": "A step that reads holdout labels (WoE, screen, or the whole fit) inflates the AUC (the 95\\% interval of the bias excludes 0 from above); refuted if any such cell does not, over the steps of each model (WoE scorecard, logit, product's scorecard) in every data set.",
        "H3": "A step that reads only holdout inputs (imputation, scaling, bin edges) leaves the estimate within 0.005 of the truth.",
        "H4": "A calibration map fitted on the holdout biases the AUC and the Brier score optimistically (positive AUC bias, negative Brier bias, intervals excluding 0), for two models on three data sets and for the product's scorecard.",
        "H5": "At least one of the three gates fails on every leak planted in the fitting path, in every draw, and none fails on the proposed protocol.",
        "H6": "A leak that exists only in development is flagged by the AUC-against-development test (power at least 97\\% at s = 0.5) and not by the CSI of the leaked feature (power at most 20\\% at s = 1) or the single-feature screen (at most 2\\% at s = 1).",
        "H7": "The closed forms of Proposition 4 reproduce the generator's exact development and decision-time AUC and the simulated means within three standard errors.",
        "H8": "A random split inside the training window reports a level gap below 1 point for every cohort, while the out-of-time gap is at least 2 points, for the scorecard and for the gradient-boosting rung.",
        "H9": "Preprocessing fitted before the folds inflates the cross-validated AUC; fitted inside the folds it does not, for both models on every data set.",
    }
    tag = {"H6": "H6$^{\\dagger}$", "H8": "H8$^{\\dagger}$"}
    rows = [[tag.get(k, k), txt[k], res[k][1], "held" if res[k][0] else "not held"] for k in txt]
    table(TAB / "tab-hypotheses.tex", ["Id", "Prediction", "Evidence", "Outcome"], rows,
                 caption=("The nine predictions of the experimental design, each with the quantity that decides it and its outcome, computed by the table "
                          "script from the cells of the paper that the prediction names: H1, H2 and H4 on the two models and three data sets and on the product's "
                          "own scorecard, H3 and H9 on the two models and three data sets, H5 on the planted leaks of the compact pipeline, H6 and H7 on the "
                          "levels of the planted leak, and H8 on the scorecard and the gradient-boosting rung over five cohorts. The predictions were written in the table script together with the outputs "
                          "that decide them; none was registered before the runs. A dagger marks the two whose thresholds were set with the "
                          "committed values of the cases C22 and C03 already known (Section~\\ref{sec:experimental-design}). A prediction that fails is "
                          "reported as not held."),
                 label="tab:hypotheses", align="lp{7.2cm}p{4.6cm}l", wide=True)


def ablation(e1: dict, e2: dict) -> None:
    S = e1["syn"]["summary"]
    mt = e2["matrix"]["pass_rates"]
    comps = [
        ("Statistics fitted on the training slice only", ["impute_full", "bin_full", "woe_full", "screen_full", "fit_full"]),
        ("Configuration chosen inside the training slice", ["select_test"]),
        ("Calibration slice disjoint from the test slice", ["cal_test", "cal_overlap"]),
    ]
    rows = []
    for name, leaks in comps:
        worst = max(leaks, key=lambda lk: S[f"woe/{lk}"]["auc_bias"])
        v = S[f"woe/{worst}"]
        rows.append([name, LEAK_TEXT[worst], pm(v["auc_bias"], 1.96 * v["auc_bias_se"]), f"{100 * v['coverage']:.1f}",
                     sg(v["brier_bias"], 4)])
    for lk in ("cv_pre",):
        v = S[f"woe/{lk}"]
        rows.append(["Preprocessing inside the cross-validation folds", LEAK_TEXT[lk], pm(v["auc_bias"], 1.96 * v["auc_bias_se"]), "--", "--"])
    table(TAB / "tab-ablation-components.tex",
                 ["Component of the protocol removed", "Worst resulting leak", "AUC bias", "Coverage \\%", "Brier bias"], rows,
                 caption=("Removing one component of the protocol at a time on the planted data of the main comparison (WoE scorecard): the leak that "
                          "results from the removal with the largest AUC bias, its bias with the 95\\% half-width, the coverage of the 95\\% interval "
                          "and the Brier bias. The reference row of the protocol is in the main comparison table."),
                 label="tab:ablation-components", align="llrrr")
    # gate subsets
    leaks = [k for k in mt if not k.endswith("/none")]
    subsets = [("G1 only", "G1"), ("G2 only", "G2"), ("G3 only", "G3"), ("G1 and G2", "G1+G2"), ("G1 and G3", "G1+G3"),
               ("G2 and G3", "G2+G3"), ("G1, G2 and G3", "G1+G2+G3")]
    rows = []
    for name, sub in subsets:
        rates = [mt[k]["subsets"][sub] for k in leaks]
        never = sum(1 for r in rates if r == 0)
        full = sum(1 for r in rates if r >= 0.999)
        fa = max(mt[k]["subsets"][sub] for k in mt if k.endswith("/none"))
        rows.append([name, f"{full} of {len(leaks)}", f"{never}", f"{100 * np.mean(rates):.1f}", f"{100 * fa:.0f}"])
        tag = sub.replace("+", "")
        put(f"abl.{tag}.full", str(full), "experiments/results/e2_matrix.json pass_rates[*].subsets")
        put(f"abl.{tag}.never", str(never), "experiments/results/e2_matrix.json pass_rates[*].subsets")
        put(f"abl.{tag}.mean", f"{100 * np.mean(rates):.1f}", "experiments/results/e2_matrix.json pass_rates[*].subsets")
        put(f"abl.{tag}.fa", f"{100 * fa:.0f}", "experiments/results/e2_matrix.json pass_rates[none].subsets")
    table(TAB / "tab-ablation-gates.tex",
                 ["Gates kept", "Leaks always detected", "Leaks never detected", "Mean detection \\%", "False alarm \\%"], rows,
                 caption=(f"Ablation of the gates over the {len(leaks)} leaks planted in the compact pipeline ({e2['matrix']['reps']} draws each): the "
                          f"number of leaks that at least one gate of the subset detects in every draw, the number never detected by any gate of the "
                          f"subset, the mean over leaks of the share of draws in which at least one gate of the subset fails, and the largest false alarm "
                          f"rate on the protocol."),
                 label="tab:ablation-gates", align="lrrrr")


def notation() -> None:
    rows = [
        ["$D=(X,y)$", "the development data: inputs $X\\in\\R^{n\\times p}$ and binary outcomes $y\\in\\{0,1\\}^n$", "--"],
        ["$T,C,H$", "index sets of the training, calibration and holdout slices, pairwise disjoint", "rows"],
        ["$\\mathcal A$", "the fitting procedure: a map from the rows it reads to the fitted parameters $\\theta$", "--"],
        ["$R_s$", "the row set that step $s$ of $\\mathcal A$ reads ($T$ under the protocol)", "rows"],
        ["$\\Pi$", "a perturbation of the rows outside $T$: inputs moved, labels redrawn", "--"],
        ["$\\hat A,\\ A^{\\ast}$", "the holdout AUC of a fitted model and its value on the population", "1"],
        ["$b$", "the bias of an estimate: $\\hat A-A^{\\ast}$, averaged over repetitions", "1"],
        ["$s^2$", "the engine's variance of the AUC (DeLong form)", "1"],
        ["$d,\\ s$", "separation of the genuine and of the leaked feature for defaulters", "standard deviations"],
        ["$\\pi$", "the default share of the development sample", "1"],
        ["$N,\\ m$", "pooled rows read by a step and number of outside rows perturbed", "rows"],
        ["$K$", "number of configurations compared", "1"],
    ]
    table(TAB / "tab-notation.tex", ["Symbol", "Meaning", "Unit"], rows,
                 caption=("Notation of the manuscript: the data and its three slices, the fitting procedure with the row set each of its steps reads, the "
                          "perturbation used by the gates, the AUC and its bias, the planted-leak parameters and the counts used by the propositions."),
                 label="tab:notation", align="lp{9cm}l")


def oracle_error(e1: dict) -> None:
    """The sampling error of the reference sample of each experiment: the Hanley and McNeil (1982) standard error of an AUC of the
    protocol's mean reference value on the reference rows, with the event share of the data (simulated for the planted data)."""
    rng = np.random.default_rng(7)
    _, y_big = L.planted(400_000, 40, rng)
    share = {"syn": float(y_big.mean()), "small": float(y_big.mean()), "prod": float(y_big.mean()), "tw": float(NUM["c01.rate"]["text"]) / 100.0}
    put("syn.share", ratio(share["syn"]), "mean of the planted outcome on 400,000 rows (seed 7), leaklab.planted")
    for ds, d in e1.items():
        a = d["summary"][{"syn": "woe/none", "small": "woe/none", "tw": "woe/none", "prod": "product/none"}[ds]]["auc_oracle"]
        n = d["n_oracle"]
        n1, n0 = share[ds] * n, (1 - share[ds]) * n
        q1, q2 = a / (2 - a), 2 * a * a / (1 + a)
        var = (a * (1 - a) + (n1 - 1) * (q1 - a * a) + (n0 - 1) * (q2 - a * a)) / (n1 * n0)
        put(f"{ds}.orcse", f"{math.sqrt(var):.4f}", f"Hanley and McNeil standard error of the reference AUC {a:.3f} on {n:,} rows with event share {share[ds]:.3f}")


def derived_numbers() -> None:
    """Numbers that follow from the committed outputs by a stated formula: the Wilson bound of a zero count, the prediction of
    Proposition 6 and the standardised difference of Proposition 2."""
    from e1_estimator_bias import wilson

    m = load("e2_matrix.json")
    n = m["reps"]
    put("e2.fa.upper", ratio(wilson(0, n)[1]), f"Wilson 95% upper bound of 0 false alarms in {n} draws (experiments/results/e2_matrix.json reps)")
    dr = load("e2_draws.json")
    put("e2.draws.se", ratio(math.sqrt(0.25 / dr["reps"])), f"largest binomial standard error of a detection rate in {dr['reps']} draws, points")
    for model, K in (("w", 8), ("l", 2)):
        for d_ in (1, 2, 3, 5):
            put(f"e2.draws.pred.{model}.{d_}", ratio(1.0 - K ** (-d_)), f"Proposition 6: 1 - K^(-d) with K = {K}, d = {d_}")
    th = load("theory_checks.json")["detection"]
    zs = []
    for mm, v in th["by_m"].items():
        ex, sim, t = v["exact"], v["simulated"], th["trials"]
        sd = math.sqrt(max(ex * (1 - ex), 1e-18) / t)
        zs.append(abs(sim - ex) / sd)
    put("th.det.zmax", f"{max(zs):.1f}", "largest |simulated - exact| / sqrt(exact (1 - exact) / trials) over m, experiments/results/theory_checks.json detection")
    doc = json.loads((figkit.DERIVED / "C22" / "leakage.json").read_text(encoding="utf-8"))
    for sim in doc["outputs"]["simulations"]:
        kind, _, lv = sim["key"].partition("@l")
        if kind in ("disc.auc_vs_initial", "stability.csi") and lv.replace(".", "").isdigit():
            tag = "auc" if kind.startswith("disc") else "csi"
            put(f"c22.{tag}.{lv}", ratio(sim["rates"]["p<0.05"]["rate"]), f"data/derived/C22/leakage.json simulations[{sim['key']}] rate at 5%, {sim['rates']['p<0.05']['n']} repetitions")
    c22null = next(sim["rates"]["p<0.05"] for sim in doc["outputs"]["simulations"] if sim["key"] == "disc.auc_vs_initial@l0")
    e3full = load("e3_planted_leak.json")
    e3n, e3reps = e3full["levels"]["0.0"]["auc_test"], e3full["reps"]
    x1, n1, x2, n2 = c22null["rate"] * c22null["n"], c22null["n"], e3n["rate"] * e3reps, e3reps
    pp = (x1 + x2) / (n1 + n2)
    zz2 = (x1 / n1 - x2 / n2) / math.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2))
    put("c22.null.diff", f"{100 * (x1 / n1 - x2 / n2):.2f}", "C22 null rate minus the e3 null rate of the test against development, points")
    put("c22.null.rate", f"{100 * c22null['rate']:.2f}", "data/derived/C22/leakage.json simulations[disc.auc_vs_initial@l0] rate at 5%")
    put("c22.null.x", f"{c22null['rejections']}", "data/derived/C22/leakage.json simulations[disc.auc_vs_initial@l0] rejections")
    put("c22.null.n", f"{c22null['n']:,}", "data/derived/C22/leakage.json simulations[disc.auc_vs_initial@l0] n")
    put("c22.null.lo", ratio(c22null["wilson_low"]), "data/derived/C22/leakage.json simulations[disc.auc_vs_initial@l0] wilson_low")
    put("c22.null.hi", ratio(c22null["wilson_high"]), "data/derived/C22/leakage.json simulations[disc.auc_vs_initial@l0] wilson_high")
    put("c22.null.z", f"{zz2:.1f}", "pooled two-proportion z of the C22 and e3 null rates")
    put("c22.null.p", f"{math.erfc(zz2 / math.sqrt(2)):.3f}", "two-sided p of the pooled two-proportion z")
    put("e3.s0.0.auc_lo", ratio(e3n["lo"]), "experiments/results/e3_planted_leak.json levels[0.0].auc_test.lo")
    put("e3.s0.0.auc_hi", ratio(e3n["hi"]), "experiments/results/e3_planted_leak.json levels[0.0].auc_test.hi")
    for mm in ("3", "5"):
        v = th["by_m"][mm]
        put(f"th.det.{mm}.miss", str(round((1 - v["simulated"]) * th["trials"])), f"theory_checks.json detection.by_m[{mm}] misses among the trials")
        put(f"th.det.{mm}.missexp", f"{(1 - v['exact']) * th['trials']:.1f}", f"theory_checks.json detection.by_m[{mm}] expected misses = (1 - exact) x trials")
    e4d = load("e4_out_of_time.json")
    ses = [100 * math.sqrt(c["random_rate"] * (1 - c["random_rate"]) / e4d["random_holdout_cap"]) for c in e4d["cohorts"]]
    put("e4.sed.lo", f"{min(ses):.2f}", "binomial standard error of the random-split rate at the window rate, smallest cohort, points")
    put("e4.sed.hi", f"{max(ses):.2f}", "binomial standard error of the random-split rate at the window rate, largest cohort, points")
    put("e4.maxz", f"{max(abs(100 * c['rungs'][r]['random_gap']) / se for c, se in zip(e4d['cohorts'], ses) for r in ('P1-scorecard', 'P4-lightgbm')):.1f}",
        "largest |random gap| / binomial standard error at the window rate over the two printed rungs and five cohorts")
    zd = []
    for model, K in (("woe", 8), ("linear", 2)):
        for d_, obs in dr["detection_by_draws"][model].items():
            pr = 1.0 - K ** (-int(d_))
            sd = math.sqrt(pr * (1 - pr) / dr["reps"])
            if sd > 0:
                zd.append(abs(obs - pr) / sd)
    put("e2.draws.zmax", f"{max(zd):.1f}", "largest |observed - 1 + K^-d| / sqrt(p (1 - p) / reps) over the cells of the repeated-perturbation study")
    put("c22.reps", f"{doc['outputs']['simulations'][0]['rates']['p<0.05']['n']:,}", "data/derived/C22/leakage.json simulations[0] n")
    e3 = load("e3_planted_leak.json")["levels"]
    zz = []
    for v in e3.values():
        zz.append(abs((v["dev_auc"]["mean"] - v["closed_form"]["dev_auc"]) / v["dev_auc"]["se"]))
        zz.append(abs((v["cur_auc"]["mean"] - v["closed_form"]["cur_auc"]) / v["cur_auc"]["se"]))
    put("e3.zmax", f"{max(zz):.1f}", "experiments/results/e3_planted_leak.json: largest |simulated mean AUC - closed form| / standard error over the seven levels, development and decision time")
    for tag, f, key in (("e1syn", "e1_synthetic.json", "seconds"), ("e1small", "e1_synthetic-small.json", "seconds"), ("e1tw", "e1_taiwan.json", "seconds"),
                        ("e1prod", "e1_product.json", "seconds"), ("e2matrix", "e2_matrix.json", "seconds"), ("e2draws", "e2_draws.json", "seconds"),
                        ("e3", "e3_planted_leak.json", "seconds")):
        put(f"run.{tag}", f"{load(f)[key]:,.0f}", f"experiments/results/{f} {key} (wall clock, one machine with 32 logical processors)")
    put("run.e4max", f"{max(c['seconds'] for c in load('e4_out_of_time.json')['cohorts']):,.0f}", "experiments/results/e4_out_of_time.json cohorts[*].seconds, the longest cohort (cohorts run in parallel)")


def main() -> None:
    TAB.mkdir(exist_ok=True)
    e1 = e1_numbers()
    main_table(e1["syn"])
    other_table(e1)
    e2 = e2_numbers_tables()
    e3 = e3_numbers_tables()
    e4 = e4_numbers_tables()
    e5 = e5_numbers_tables()
    split_table()
    oracle_error(e1)
    derived_numbers()
    hypotheses(e1, e2, e3, e4, e5)
    ablation(e1, e2)
    notation()
    tex = ["% generated by make_artifacts.py: do not edit"]
    for k in sorted(NUM):
        tex.append(f"\\expandafter\\def\\csname num@{k}\\endcsname{{{NUM[k]['text']}}}")
    (TAB / "numbers.tex").write_text("\n".join(tex) + "\n", encoding="utf-8", newline="\n")
    (TAB / "numbers.json").write_text(json.dumps(NUM, indent=1), encoding="utf-8", newline="\n")
    print(len(NUM), "numbers")


if __name__ == "__main__":
    main()
