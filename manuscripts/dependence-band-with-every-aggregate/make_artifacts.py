"""Figures, tables and number macros of the manuscript on the dependence band, from the committed documents under
``data/derived/C18`` and the outputs of the experiment scripts (``experiments/e1`` to ``e4``). No number of the text is typed: every
figure is ``figures/*.pdf``, every table ``tables/*.tex`` and every number quoted in prose is a macro of ``tables/numbers.tex``.

    python manuscripts/dependence-band-with-every-aggregate/make_artifacts.py

Run time: under a minute (one rearrangement on a 2,000-cell matrix for the illustration figure).
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
sys.path.insert(0, str(HERE / "experiments"))
import figkit  # noqa: E402
import bandkit as bk  # noqa: E402

FIG = HERE / "figures"
TAB = HERE / "tables"
TAB.mkdir(exist_ok=True)

LABELS = {"lower-bound": "lower bound", "simple-sum": "simple sum (headline)", "variance-covariance": "square-root rule",
          "gaussian-copula": "Gaussian copula", "t-copula-nu4": "$t$ copula, $\\nu=4$", "t-copula-nu8": "$t$ copula, $\\nu=8$",
          "t-copula-nu30": "$t$ copula, $\\nu=30$", "worst-case": "worst case"}
PLAIN = {k: v.replace("$", "").replace("\\nu", "nu") for k, v in LABELS.items()}
ORDER = list(LABELS)
INTERIOR = ["variance-covariance", "gaussian-copula", "t-copula-nu4", "t-copula-nu8", "t-copula-nu30"]

e1 = json.loads((HERE / "experiments" / "e1_structure.json").read_text(encoding="utf-8"))
e2 = json.loads((HERE / "experiments" / "e2_reproduce.json").read_text(encoding="utf-8"))
e3 = json.loads((HERE / "experiments" / "e3_planted_truth.json").read_text(encoding="utf-8"))
e4 = json.loads((HERE / "experiments" / "e4_ablation.json").read_text(encoding="utf-8"))
e5 = json.loads((HERE / "experiments" / "e5_timing.json").read_text(encoding="utf-8"))
case = bk.Case()

MAC: dict[str, str] = {}


def M(name: str, value: str) -> None:
    assert name.isalpha(), name
    MAC[name] = value


def bn(x: float, d: int = 1) -> str:
    return f"{x / 1e3:,.{d}f}".replace(",", "{,}")


def pc(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}"


def n0(x: float) -> str:
    return f"{x:,.0f}".replace(",", "{,}")


def cap(name: str) -> str:
    return {"tab": "Table", "fig": "Figure"}[name]


# ---------------------------------------------------------------------------------------------------------------- macros
base, stress = e1["base_rows"], e1["stress_rows"]
H = e1["headline"]
M("bdHeadline", bn(H)); M("bdHeadlineM", n0(H))
for key, nm in (("lower-bound", "Lower"), ("variance-covariance", "Vc"), ("gaussian-copula", "Gauss"), ("t-copula-nu4", "TFour"),
                ("t-copula-nu8", "TEight"), ("t-copula-nu30", "TThirty"), ("worst-case", "Worst")):
    M("bd" + nm, bn(base[key])); M("bd" + nm + "M", n0(base[key])); M("bd" + nm + "Df", f"{base[key] / H:.3f}")
    M("bd" + nm + "Stress", bn(stress[key])); M("bd" + nm + "StressDf", f"{stress[key] / H:.3f}")
    M("bd" + nm + "Move", pc(stress[key] / base[key] - 1.0))
M("bdWidth", bn(base["worst-case"] - base["lower-bound"])); M("bdWidthOverHeadline", f"{(base['worst-case'] - base['lower-bound']) / H:.3f}")
M("bdWorstOverHeadline", f"{base['worst-case'] / H:.3f}"); M("bdWorstAbove", pc(base["worst-case"] / H - 1.0))
M("bdLowerOverHeadline", f"{base['lower-bound'] / H:.3f}")
M("bdGaussBelow", pc(1.0 - base["gaussian-copula"] / H)); M("bdAdditiveOver", pc(H / base["gaussian-copula"] - 1.0))
M("bdSumEs", bn(e1["analytic_bound"]["sum_of_es"])); M("bdWorstVar", bn(e1["analytic_bound"]["worst_var"]))
M("bdLowerVar", bn(e1["analytic_bound"]["lower_var"]))
M("bdSlack", bn(e1["analytic_bound"]["slack"])); M("bdWorstOverEs", f"{e1['analytic_bound']['worst_var_over_sum_of_es']:.3f}")
M("bdElTotal", bn(e1["analytic_bound"]["el_total"])); M("bdSumVar", bn(e1["analytic_bound"]["sum_of_var"]))
M("bdVcSquareDiff", f"{e1['closed_form']['square_difference'] / 1e9:.1f}")
M("bdVcClosedDiff", f"{e1['closed_form']['closed_form_difference'] / 1e9:.1f}")
M("bdDistinct", str(e1["distinct_aggregates"])); M("bdAggregates", str(e1["H1"]["aggregates"]))
for k, v in e1["marginals"].items():
    M("bdEc" + k.capitalize(), bn(v["ec"])); M("bdVar" + k.capitalize(), bn(v["var"])); M("bdEs" + k.capitalize(), bn(v["es"]))
    M("bdEl" + k.capitalize(), bn(v["el"]))
M("bdGridPoints", n0(e1["grid_points"]))
M("bdMarketGridMin", bn(e1["grid_minimum"]["market"]))
mr = e1["model_risk"]["barrieu_scandolo"]; gx = e1["model_risk"]["glasserman_xu"]
M("bdAm", pc(mr["am"])); M("bdRm", f"{mr['rm']:.3f}")
M("bdGxBase", bn(gx["baseline_clp_m"])); M("bdGxWorst", bn(gx["worst_case_clp_m"])); M("bdGxEta", f"{gx['relative_entropy_budget']:.2f}")
M("bdEulerGap", f"{e1['euler']['additivity']['relative_error']:.1e}".replace("e-", "\\times 10^{-") + "}")
M("bdEsTotal", bn(e1["euler"]["es_total_clp_m"]))
cs = {r["nu"]: r for r in e1["copula_sensitivity"]}
for nu in (4.0, 8.0, 30.0):
    M("bdCopulaDiff" + {4.0: "Four", 8.0: "Eight", 30.0: "Thirty"}[nu], pc(cs[nu]["relative_difference"]))
rs = e1["rosenberg_schuermann"]; M("bdRsOver", pc(rs["case_additive_overestimate"]))
tl = {t["test_id"]: t for t in e1["tests_of_the_document"]}
M("bdCopulaStat", pc(tl["aggregation.copula_choice_sensitivity"]["statistic"])); M("bdStressStat", pc(tl["aggregation.correlation_stress"]["statistic"]))
M("bdBracketStat", bn(tl["aggregation.worst_case_bracket"]["statistic"]))
M("bdGaussSe", bn(next(r for r in case.committed_band if r["method"] == "gaussian-copula")["mc_se_clp_m"]))
# e2
r2 = e2["H2"]["per_row"]
M("bdMaxRelDiff", f"{max(abs(v['relative_difference']) for v in r2.values()) * 100:.4f}")
M("bdLowerRelDiff", f"{abs(r2['lower-bound']['relative_difference']) * 100:.4f}"); M("bdWorstRelDiff", f"{abs(r2['worst-case']['relative_difference']) * 100:.4f}")
M("bdGaussRelDiff", f"{abs(r2['gaussian-copula']['relative_difference']) * 100:.4f}")
h3 = e2["H3"]
M("bdWidthOverSe", f"{h3['committed']['width_over_max_se']:.0f}"); M("bdMaxSe", bn(h3["committed"]["max_se"]))
fr = h3["committed"]["farthest_row_relative_difference"]
M("bdFarthestMin", pc(min(fr.values()), 0)); M("bdFarthestMax", pc(max(fr.values()), 0))
for k, nm in (("simple-sum", "Sum"), ("gaussian-copula", "Gauss"), ("worst-case", "Worst"), ("variance-covariance", "Vc"), ("lower-bound", "Lower")):
    M("bdFarthest" + nm, pc(fr[k], 0))
br = e2["bound_ranges"]
M("bdWorstOverComo", pc(e1["analytic_bound"]["worst_var"] / br["comonotonic_var"] - 1.0))
M("bdComoOverSum", pc(br["comonotonic_var"] / e1["analytic_bound"]["sum_of_var"] - 1.0, 2))
M("bdLowerRangeWidth", bn(br["lower_range"][1] - br["lower_range"][0], 2)); M("bdUpperRangeWidth", f"{br['upper_range'][1] - br['upper_range'][0]:.1f}".replace(",", "{,}"))
M("bdLowerRangeLo", bn(br["lower_range"][0])); M("bdLowerRangeHi", bn(br["lower_range"][1]))
M("bdUpperRangeLo", bn(br["upper_range"][0], 3)); M("bdUpperRangeHi", bn(br["upper_range"][1], 3))
M("bdSweeps", ", ".join(str(s) for s in br["sweeps"])); M("bdComoVar", bn(br["comonotonic_var"]))
rb = e2["repetitions_base"]["rows"]; rst = e2["repetitions_stress"]["rows"]
M("bdRepsBase", str(len(e2["repetitions_base"]["seeds"]))); M("bdRepsStress", str(len(e2["repetitions_stress"]["seeds"])))
M("bdGaussSd", bn(rb["gaussian-copula"]["sd"])); M("bdTFourSd", bn(rb["t-copula-nu4"]["sd"]))
M("bdBoundsSd", f"{max(rb['lower-bound']['sd'], rb['worst-case']['sd']):.1f}")
M("bdMaxSd", bn(max(v["sd"] for v in rb.values())))
nuc = e2["nu_curve"]
M("bdTTwoFive", bn(nuc["base"][0])); M("bdTThree", bn(nuc["base"][1])); M("bdTHundred", bn(nuc["base"][-1]))
M("bdTLambdaFour", f"{nuc['tail_dependence_rho05'][2]:.3f}"); M("bdTLambdaThirty", f"{nuc['tail_dependence_rho05'][6]:.4f}")
M("bdBandSeconds", f"{e5['band_seconds']:.0f}"); M("bdBoundsSeconds", f"{e5['bounds_seconds']:.0f}")
M("bdRmPct", pc(mr["rm"], 0))
M("bdTLambdaTwoFive", f"{nuc['tail_dependence_rho05'][0]:.3f}"); M("bdTLambdaThree", f"{nuc['tail_dependence_rho05'][1]:.3f}"); M("bdTLambdaLowFour", f"{nuc['tail_dependence_rho02'][2]:.3f}")
M("bdNuSpanBase", bn(nuc["base"][0] - nuc["base"][-1])); M("bdNuSpanPc", pc(nuc["base"][0] / nuc["base"][-1] - 1.0))
M("bdNuHundredGap", bn(nuc["base"][-1] - nuc["gaussian_base"], 1))
ec_ = np.array([e1["marginals"][r]["ec"] for r in bk.RISKS])
M("bdSqrtFloor", bn(float(np.sqrt((ec_ ** 2).sum()))))
for _r, _v in zip(bk.RISKS, ec_):
    M("bdEcShare" + _r.capitalize(), f"{100 * _v / ec_.sum():.0f}")
# e3
st = e3["structures"]
M("bdNStruct", str(len(st))); M("bdTruthReps", str(e3["reps"]))
for key in ("H4a", "H4b", "H4c"):
    pass
M("bdCovSharp", str(sum(r["covered_sharp_range"] for r in st))); M("bdCovInterior", str(sum(r["covered_interior"] for r in st)))
M("bdCovInteriorStress", str(sum(r["covered_interior_with_stress"] for r in st)))
M("bdGaussWithin", str(sum(r["gaussian_within_tolerance"] for r in st)))
errs = {r["id"]: r["relative_error"] for r in st}
M("bdGaussMaxErr", pc(max(abs(e["gaussian-copula"]) for e in errs.values())))
M("bdGaussMedErr", pc(float(np.median([abs(e["gaussian-copula"]) for e in errs.values()]))))
M("bdSumMaxErr", pc(max(abs(e["simple-sum"]) for e in errs.values())))
_sum_err = {i: e["simple-sum"] for i, e in errs.items() if i != "gaussian-independent"}
M("bdSumErrMin", pc(min(_sum_err.values()), 0)); M("bdSumErrMaxOther", pc(max(_sum_err.values()), 0))
_gauss_dep = [e["gaussian-copula"] for i, e in errs.items() if i in ("gaussian-stress", "gaussian-crisis", "t3-base", "t25-base", "t3-crisis", "clayton-survival", "gumbel")]
M("bdGaussDepMin", pc(-max(_gauss_dep), 0)); M("bdGaussDepMax", pc(-min(_gauss_dep), 0))
_k_tail = [abs(errs[i]["gaussian-kendall-calibrated"]) for i in ("t3-base", "t25-base", "t3-crisis", "clayton-survival", "gumbel")]
_stress_gauss = [abs(e3["band_rows_used"]["stress"]["gaussian-copula"] / r["truth"] - 1.0) for r in st if r["id"] in ("gaussian-stress", "gaussian-crisis", "t3-base", "t25-base", "t3-crisis", "clayton-survival", "gumbel")]
M("bdGaussStressDepMin", pc(min(_stress_gauss))); M("bdGaussStressDepMax", pc(max(_stress_gauss)))
M("bdKTailMin", pc(min(_k_tail), 0)); M("bdKTailMax", pc(max(_k_tail), 0))
_k_g = [abs(errs[i]["gaussian-kendall-calibrated"]) for i in ("gaussian-base", "gaussian-stress", "gaussian-crisis", "gaussian-independent", "regime-mixture")]
M("bdKGaussMax", pc(max(_k_g), 0))
M("bdHybridMedErr", pc(float(np.median([abs(e["hybrid-calibrated"]) for e in errs.values()]))))
M("bdHybridMaxErr", pc(max(abs(e["hybrid-calibrated"]) for e in errs.values())))
M("bdKendallMedErr", pc(float(np.nanmedian([abs(e["gaussian-kendall-calibrated"]) for e in errs.values()]))))
M("bdKendallMaxErr", pc(float(np.nanmax([abs(e["gaussian-kendall-calibrated"]) for e in errs.values()]))))
tmax = max(st, key=lambda r: r["truth"]); tmin = min(st, key=lambda r: r["truth"])
M("bdTruthMax", bn(tmax["truth"])); M("bdTruthMin", bn(tmin["truth"])); M("bdTruthMaxOverWorst", f"{tmax['truth'] / base['worst-case']:.3f}")
M("bdTruthMaxOverHeadline", f"{tmax['truth'] / H:.3f}")
M("bdTruthSeMax", bn(max(r["truth_se"] for r in st)))
sc = e3["self_checks"]
M("bdClaytonTauSim", f"{sc['clayton']['tau_simulated']:.3f}"); M("bdClaytonTauExact", f"{sc['clayton']['tau_closed_form']:.3f}")
M("bdGumbelTauSim", f"{sc['gumbel']['tau_simulated']:.3f}"); M("bdGumbelTauExact", f"{sc['gumbel']['tau_closed_form']:.3f}")
for r in st:
    nm = "".join(w.capitalize() for w in r["id"].replace("25", "twofive").replace("3", "three").split("-"))
    M("bdTruth" + nm, bn(r["truth"])); M("bdGaussErr" + nm, pc(r["relative_error"]["gaussian-copula"]))
    M("bdTruthDf" + nm, f"{r['truth'] / H:.3f}")
M("bdTauBar", f"{np.mean([bk.kendall_from_corr(case.corr[i, j]) for i in range(4) for j in range(i + 1, 4)]):.4f}")
sidx = {r["id"]: r for r in st}
M("bdClaytonTheta", f"{[s for s in bk.structures(case) if s['id'] == 'clayton-survival'][0]['theta']:.2f}")
M("bdGumbelTheta", f"{[s for s in bk.structures(case) if s['id'] == 'gumbel'][0]['theta']:.2f}")
# e4
h6, h7, eu = e4["H6"], e4["H7"], e4["euler"]
M("bdMarketEcNineNine", bn(h6["market_ec_at_99"])); M("bdMarketEcChange", pc(h6["market_ec_change"], 0)); M("bdHeadlineChange", pc(h6["headline_change"]))
M("bdSumMismatch", bn(h6["simple_sum_mismatched"]))
M("bdRunnableGaussOnly", str(len(h7["runnable_with_gaussian_only"]))); M("bdTestsTotal", str(h7["criterion"]["tests_total"]))
M("bdEulerMaxGap", f"{eu['max_relative_gap']:.1e}".replace("e-", "\\times 10^{-") + "}")
M("bdStandaloneOver", f"{eu['standalone_over_aggregate_es']:.3f}")
M("bdEsTotalMean", bn(eu["es_total_mean"])); M("bdEsTotalSd", bn(eu["es_total_sd"], 2)); M("bdSumStandaloneEs", bn(eu["sum_of_standalone_es"]))
for i, r in enumerate(bk.RISKS):
    M("bdShare" + r.capitalize(), pc(eu["share_mean"][i])); M("bdShareSd" + r.capitalize(), pc(eu["share_sd"][i]))
    M("bdSaShare" + r.capitalize(), pc(eu["standalone_share"][i])); M("bdBenefit" + r.capitalize(), pc(eu["benefit_by_risk_mean"][i], 0))
var = {v["variant"]: v for v in e4["ablation_variants"]}
names = list(var)
M("bdAblFull", str(var[names[0]]["covered"])); M("bdAblNoBounds", str(var[names[1]]["covered"])); M("bdAblNoStress", str(var[names[2]]["covered"]))
M("bdAblNoT", str(var[names[3]]["covered"]))
M("bdAblFullWidth", f"{var[names[0]]['median_width_over_truth']:.2f}"); M("bdAblNoBoundsWidth", f"{var[names[1]]['median_width_over_truth']:.2f}")
M("bdAblNoStressWidth", f"{var[names[2]]['median_width_over_truth']:.2f}"); M("bdAblNoTWidth", f"{var[names[3]]['median_width_over_truth']:.2f}")
M("bdAblGaussPoint", str(var[names[4]]["covered"])); M("bdAblVcPoint", str(var[names[5]]["covered"])); M("bdAblSumPoint", str(var[names[6]]["covered"]))
M("bdAblHybridPoint", str(var[names[7]]["covered"])); M("bdAblKendallPoint", str(var[names[8]]["covered"])); M("bdAblGaussTen", str(var[names[9]]["covered"]))
LBL = {r["id"]: r["label"] for r in st}
M("bdAblNoTStress", str(var[names[10]]["covered"])); M("bdAblNoTStressWidth", f"{var[names[10]]['median_width_over_truth']:.2f}")
M("bdAblWidthBounds", f"{var[names[0]]['median_width_over_truth'] - var[names[1]]['median_width_over_truth']:.2f}")
M("bdAblWidthStress", f"{var[names[1]]['median_width_over_truth'] - var[names[2]]['median_width_over_truth']:.2f}")
M("bdAblStressGain", str(var[names[1]]["covered"] - var[names[2]]["covered"]))
M("bdAblBoundsGain", str(var[names[0]]["covered"] - var[names[1]]["covered"]))
M("bdShareSdMin", pc(min(eu["share_sd"]))); M("bdShareSdMax", pc(max(eu["share_sd"])))
M("bdAblTOnly", str(var[names[11]]["covered"])); M("bdAblTOnlyWidth", f"{var[names[11]]['median_width_over_truth']:.2f}")
M("bdMissedNoBounds", " and ".join(LBL[i] for i in var[names[1]]["missed"]))
for h, o in (("HOne", e1["H1"]["outcome"]), ("HTwo", e2["H2"]["outcome"]), ("HThree", e2["H3"]["outcome"]), ("HFiveInv", e1["H5"]["outcome"]),
             ("HFourA", e3["H4a"]["outcome"]), ("HFourB", e3["H4b"]["outcome"]), ("HFourC", e3["H4c"]["outcome"]), ("HSix", h6["outcome"]), ("HSeven", h7["outcome"])):
    M("bdVerdict" + h, o)

# ---------------------------------------------------------------------------------------------------------------- tables


def T(path, header, rows, **kw):
    """figkit.table with every text cell written as given (the cells hold their own LaTeX), prefixed so that figkit does not escape it."""
    rows = [[("\\relax " + c) if isinstance(c, str) and not c.startswith(("\\", "$")) else c for c in r] for r in rows]
    out = figkit.table(path, header, rows, **kw)
    text = path.read_text(encoding="utf-8")
    text = text.replace("\\begin{tabular}", "\\fitwidth{\\begin{tabular}", 1).replace("\\end{tabular}", "\\end{tabular}}", 1)
    path.write_text(text, encoding="utf-8", newline="\n")
    return out

RISK_NAMES = {"credit": "credit", "market": "market", "irrbb": "IRRBB", "operational": "operational"}


def t_marginals() -> None:
    rows = [[RISK_NAMES[k], bn(v["el"]), bn(v["var"]), bn(v["es"]), bn(v["ec"]), bn(v["var_se"], 2) if v["var_se"] else "--"] for k, v in e1["marginals"].items()]
    rows.append(["total (simple sum of capital)", bn(sum(v["el"] for v in e1["marginals"].values())), bn(sum(v["var"] for v in e1["marginals"].values())),
                 bn(sum(v["es"] for v in e1["marginals"].values())), bn(H), "--"])
    T(TAB / "marginals.tex", ["Risk", "EL", "VaR", "ES", "EC", "VaR s.e."], rows,
                 caption="The four marginals of Banco Andino at one year and 99.9 percent, in CLP billion: expected loss, value at risk, expected shortfall, economic capital "
                         "(value at risk less expected loss) and the Monte Carlo standard error of the value at risk where the marginal is simulated, read from the committed baseline document.",
                 label="tab:marginals", align="lrrrrr")


def t_protocol() -> None:
    desc = {
        "lower-bound": ("best value at risk over all couplings, less the expected losses", "rearrangement, outer end of the range"),
        "simple-sum": ("sum of the marginal capitals; the comonotonic row", "closed form"),
        "variance-covariance": ("$\\sqrt{\\mathrm{EC}^{\\top}R\\,\\mathrm{EC}}$ with the named matrix $R$", "closed form"),
        "gaussian-copula": ("value at risk of the sum under the Gaussian copula of $R$, less expected losses", "Monte Carlo, $10^6$ draws"),
        "t-copula-nu4": ("the same under the $t$ copula with $\\nu=4$ and the matrix $R$", "Monte Carlo, $10^6$ draws"),
        "t-copula-nu8": ("the same with $\\nu=8$", "Monte Carlo, $10^6$ draws"),
        "t-copula-nu30": ("the same with $\\nu=30$", "Monte Carlo, $10^6$ draws"),
        "worst-case": ("worst value at risk over all couplings, less the expected losses", "rearrangement, outer end of the range"),
    }
    rows = [[str(i + 1), LABELS[k], desc[k][0], desc[k][1], "headline capital" if k == "simple-sum" else "information, not capital"] for i, k in enumerate(ORDER)]
    T(TAB / "protocol.tex", ["\\#", "Row", "Capital of the row", "Computation", "Status"], rows,
                 caption="The eight rows of the band in the order in which every aggregate shows them, with the quantity each row reports, how the engine computes it and the status label it carries; "
                         "only the simple sum is labelled headline capital.", label="tab:protocol", align="rp{2.0cm}p{5.2cm}p{2.7cm}p{2.3cm}", wide=False)


def t_main() -> None:
    rows = []
    for k in ORDER:
        c = next(r for r in case.committed_band if case.label(r["method"], r["nu"]) == k)
        rr, rs = rb[k], rst[k]
        se = c["mc_se_clp_m"]
        rows.append([PLAIN[k] if False else LABELS[k], f"{bn(c['capital_clp_m'])}" + (f" $\\pm$ {bn(se)}" if se else ""), f"{c['diversification_factor']:.3f}",
                     f"{bn(rr['mean'])} $\\pm$ {bn(rr['sd'])}", f"{bn(rs['mean'])} $\\pm$ {bn(rs['sd'])}", f"{rs['mean'] / rr['mean'] - 1.0 + 0.0:+.3f}".replace("-0.000", "0.000")])
    T(TAB / "main-results.tex", ["Row", "Committed", "DF", f"Rebuilt, base", "Rebuilt, market-credit 0.8", "Change"], rows,
                 caption="The dependence band of Banco Andino at one year and 99.9 percent in CLP billion: the committed rows with their Monte Carlo standard error and diversification factor "
                         "against the simple sum, then the rows rebuilt by the engine from the committed marginal grids as mean and standard deviation over independent seeds "
                         f"({len(e2['repetitions_base']['seeds'])} for the base matrix, {len(e2['repetitions_stress']['seeds'])} for the matrix with market-credit correlation 0.8) and the relative change under the stress. "
                         "The two bound rows do not move with the matrix.", label="tab:main-results", align="lrrrrr", wide=False)


def t_truth() -> None:
    rows = []
    for r in st:
        e = r["relative_error"]
        rows.append([r["label"], f"{bn(r['truth'])} $\\pm$ {bn(r['truth_se'], 2)}", f"{e['gaussian-copula'] * 100:+.1f}", f"{e['variance-covariance'] * 100:+.1f}",
                     f"{e['hybrid-calibrated'] * 100:+.1f}", f"{e['gaussian-kendall-calibrated'] * 100:+.1f}", "yes" if r["covered_interior"] else "no",
                     "yes" if r["covered_interior_with_stress"] else "no", "yes" if r["covered_sharp_range"] else "no"])
    T(TAB / "planted-truth.tex", ["Planted structure", "Capital", "Gauss.", "Sqrt", "Hybrid", "Gauss. rank", "Hull", "Hull+s", "Range"], rows,
                 caption="Ten planted dependence structures on the marginals of Banco Andino: the capital of the structure in CLP billion with its standard error over independent samples, "
                         "the relative error in percent of the Gaussian copula row, of the square-root row, of the hybrid quantile with the correlation of the structure and of the Gaussian copula "
                         "with its rank correlation, and whether the interior rows (hull), the interior rows of both matrices (hull+s) and the sharp range from the lower bound to the worst case contain it.",
                 label="tab:planted-truth", align="lrrrrrccc", wide=True)


def missed_text(v):
    """The structures an interval misses: listed when at most three, else the ones it does cover."""
    if not v["missed"]:
        return "none"
    if len(v["missed"]) <= 3:
        return "; ".join(LBL[i] for i in v["missed"])
    return "covers only " + "; ".join(LBL[i] for i in LBL if i not in v["missed"])


def t_ablation() -> None:
    rows = []
    for v in sorted(e4["ablation_variants"], key=lambda v: v["kind"] != "interval"):
        if v["kind"] == "interval":
            rows.append([v["variant"], "contains the capital", f"{v['covered']} of {v['of']}", f"{v['median_width_over_truth']:.2f}", missed_text(v)])
        else:
            rows.append([v["variant"], f"within {int(100 * v['tolerance'])} percent", f"{v['covered']} of {v['of']}", f"{v['median_abs_error']:.2f}",
                         "median error"])
    T(TAB / "ablation.tex", ["Variant", "Covered when", "Structures covered", "Median width / error", "Missed"], rows,
                 caption="What each component of the protocol contributes on the ten planted structures: for an interval, the number of structures whose capital it contains and its median width "
                         "relative to the capital; for a single figure, the number within the stated tolerance and its median absolute relative error.",
                 label="tab:ablation", align="p{5.6cm}lcrp{3.4cm}", wide=True)


def t_hyp() -> None:
    hyp = bk.hypotheses()
    short = {"H1": "structure of the band in six committed aggregates", "H2": "rebuilt rows reproduce the committed rows",
             "H3": "band wider than 100 standard errors; no row speaks for it", "H4a": "sharp range contains every planted capital",
             "H4b": "interior rows contain at least 75 percent of planted capitals", "H4c": "Gaussian row within 5 percent in at most half",
             "H5": "bounds invariant to the matrix; Gaussian row moves over 10 percent", "H6": "level mismatch changes the sum over 10 percent and the test is red",
             "H7": "tests need the rows; Gaussian row alone runs at most half"}
    meas = {"H1": f"{e1['H1']['aggregates']} of {e1['H1']['aggregates']} pass", "H2": f"largest difference {max(abs(v['relative_difference']) for v in r2.values()) * 100:.4f} percent",
            "H3": f"width {h3['committed']['width_over_max_se']:.0f} s.e.; closest row {min(fr.values()) * 100:.0f} percent from another",
            "H4a": f"{sum(r['covered_sharp_range'] for r in st)} of {len(st)}", "H4b": f"{sum(r['covered_interior'] for r in st)} of {len(st)} ({sum(r['covered_interior_with_stress'] for r in st)} with the stressed matrix)",
            "H4c": f"{sum(r['gaussian_within_tolerance'] for r in st)} of {len(st)}", "H5": f"bounds differ by {max(e1['H5']['lower_relative_difference'], e1['H5']['worst_relative_difference']):.0f}; Gaussian row moves {e1['H5']['gaussian_move'] * 100:.1f} percent",
            "H6": f"sum {h6['headline_change'] * 100:+.1f} percent; test {h6['consistency_light_mismatched_level']}", "H7": f"{len(h7['runnable_with_gaussian_only'])} of {h7['criterion']['tests_total']} run on the Gaussian row"}
    out = {"H1": e1["H1"]["outcome"], "H2": e2["H2"]["outcome"], "H3": e2["H3"]["outcome"], "H4a": e3["H4a"]["outcome"], "H4b": e3["H4b"]["outcome"], "H4c": e3["H4c"]["outcome"],
           "H5": e1["H5"]["outcome"], "H6": h6["outcome"], "H7": h7["outcome"]}
    rows = [[k, short[k], meas[k], out[k]] for k in hyp if not k.startswith("_")]
    T(TAB / "hypotheses.tex", ["Id", "Prediction", "Measured", "Outcome"], rows,
                 caption="The nine predictions, the measured quantity of each and whether it held or was refuted, from the outputs of the experiment scripts.",
                 label="tab:hypotheses", align="llp{5.2cm}l")


def t_tests() -> None:
    rows = []
    for k, v in h7["tests"].items():
        gl = v.get("with_gaussian_only", {}).get("runnable")
        rows.append([k.split(".")[-1].replace("_", " "), "; ".join(v["needs"]).replace("_", "\\_"), v.get("light_in_committed_document") or "--", "yes" if gl else "no"])
    T(TAB / "tests-rows.tex", ["Test of the aggregation battery", "Inputs it reads", "Light on the committed aggregate", "Runs on the Gaussian row alone"], rows,
                 caption="The nine tests of the aggregation battery, the rows or inputs each one reads, the light each returns on the committed aggregate and whether the test can be run when the Gaussian "
                         "copula row is the only aggregate figure kept; the two amber lights belong to tests that read more than one row.",
                 label="tab:tests-rows", align="p{4.4cm}p{5.6cm}ll")


def t_euler() -> None:
    rows = [[RISK_NAMES[r], bn(eu["euler_contribution_mean"][i]), f"{pc(eu['share_mean'][i])} $\\pm$ {pc(eu['share_sd'][i])}", bn(eu["standalone_es"][i]),
             pc(eu["standalone_share"][i]), pc(eu["benefit_by_risk_mean"][i], 0)] for i, r in enumerate(bk.RISKS)]
    rows.append(["sum", bn(sum(eu["euler_contribution_mean"])), "100.0", bn(eu["sum_of_standalone_es"]), "100.0", "--"])
    T(TAB / "euler.tex", ["Risk", "Euler contribution", "Share, percent", "Stand-alone ES", "Share, percent", "Benefit, percent"], rows,
                 caption="The Euler allocation of the expected shortfall of the Gaussian copula aggregate at 99.9 percent in CLP billion, as mean over independent seeds with the standard deviation of the "
                         "share, against the stand-alone expected shortfall of each marginal, which sums to more than the aggregate; the benefit is one minus the contribution over the stand-alone figure.",
                 label="tab:euler", align="lrrrrr")


def t_notation() -> None:
    rows = [
        ["$K$, $k$", "number of risks (four) and a risk index", "1"],
        ["$L_k$, $F_k$", "loss of risk $k$ over the horizon and its distribution function", "CLP billion"],
        ["$\\alpha$, $h$", "confidence level (0.999) and horizon (one year)", "1, year"],
        ["$S$", "total loss $\\sum_k L_k$", "CLP billion"],
        ["$\\mathrm{EL}_k$, $\\mathrm{VaR}_k$, $\\mathrm{ES}_k$", "expected loss, value at risk and expected shortfall of $L_k$ at level $\\alpha$", "CLP billion"],
        ["$\\mathrm{EC}_k$", "economic capital $\\mathrm{VaR}_k-\\mathrm{EL}_k$", "CLP billion"],
        ["$R$, $\\rho_{ij}$", "correlation matrix of the copulas and its entries", "1"],
        ["$\\nu$", "degrees of freedom of the $t$ copula", "1"],
        ["$b_j$", "capital of row $j$ of the band", "CLP billion"],
        ["$H$", "headline capital, the simple sum $\\sum_k\\mathrm{EC}_k$", "CLP billion"],
        ["$\\mathrm{DF}_j$", "diversification factor $b_j/H$ of row $j$", "1"],
        ["$\\underline{b}$, $\\overline{b}$", "lower bound and worst case of the band", "CLP billion"],
        ["$\\lambda_\\nu(\\rho)$", "upper tail dependence coefficient of the bivariate $t$ copula", "1"],
        ["$\\tau$", "Kendall rank correlation", "1"],
    ]
    T(TAB / "notation.tex", ["Symbol", "Meaning", "Unit"], rows,
                 caption="The notation of the formulation and of the proposed method: the main symbols with their meaning and their unit; money is in CLP billion unless a table states CLP million.",
                 label="tab:notation", align="lp{9cm}l")


def t_matrices() -> None:
    mats = [case.corr, case.corr_stress, bk.crisis_corr()]
    rows = []
    for i in range(4):
        for j in range(i + 1, 4):
            rows.append([f"{RISK_NAMES[bk.RISKS[i]]} and {RISK_NAMES[bk.RISKS[j]]}"] + [f"{m[i, j]:.2f}" for m in mats])
    T(TAB / "matrices.tex", ["Pair of risks", "Base", "Market-credit 0.8", "Crisis"], rows,
      caption="The three correlation matrices of the study, one entry per pair of risk types (the matrices are symmetric with a unit diagonal): the base matrix of the committed documents, "
              "the matrix of the market-credit stress, and the crisis matrix of two planted structures.",
      label="tab:matrices", align="lrrr")


for fn in (t_marginals, t_protocol, t_main, t_truth, t_ablation, t_hyp, t_tests, t_euler, t_notation, t_matrices):
    fn()

# ---------------------------------------------------------------------------------------------------------------- figures
figkit.style()
import matplotlib.pyplot as plt  # noqa: E402

SHORT = {"lower-bound": "lower bound", "simple-sum": "simple sum", "variance-covariance": "square-root", "gaussian-copula": "Gaussian",
         "t-copula-nu4": "t, nu 4", "t-copula-nu8": "t, nu 8", "t-copula-nu30": "t, nu 30", "worst-case": "worst case"}


def fig_band() -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    y = np.arange(len(ORDER))[::-1]
    se_b = {case.label(r["method"], r["nu"]): r["mc_se_clp_m"] or 0.0 for r in case.committed_band}
    se_s = {case.label(r["method"], r["nu"]): r["mc_se_clp_m"] or 0.0 for r in case.committed_stress_band}
    ax.axvspan(base["lower-bound"] / 1e3, base["worst-case"] / 1e3, color="0.92")
    ax.errorbar([base[k] / 1e3 for k in ORDER], y + 0.15, xerr=[2 * se_b[k] / 1e3 for k in ORDER], fmt="o", color="0.0", capsize=2, label="market-credit 0.5")
    ax.errorbar([stress[k] / 1e3 for k in ORDER], y - 0.15, xerr=[2 * se_s[k] / 1e3 for k in ORDER], fmt="s", color="0.5", capsize=2, label="market-credit 0.8")
    ax.axvline(H / 1e3, color="0.2", linestyle="--", linewidth=0.8)
    ax.text(H / 1e3, len(ORDER) - 0.35, " headline", fontsize=7, va="bottom")
    ax.set_yticks(y); ax.set_yticklabels([SHORT[k] for k in ORDER])
    ax.set_xlabel("economic capital, CLP billion"); ax.legend(loc="center left", bbox_to_anchor=(0.0, 0.42))
    figkit.save(fig, FIG, "band")


def fig_protocol() -> None:
    fig, ax = plt.subplots(figsize=(6.8, 2.2)); ax.axis("off")
    boxes = ["marginals $F_k$\nEC, EL, ES at\none horizon,\none level", "named inputs\n$R$ and the set\nof $\\nu$ values", "eight rows\nlower, sum,\nroot, Gauss,\n3 t, worst",
             "status labels\nsum: headline,\nrest: not\ncapital", "gates\norder, level,\nbracket, sign,\nEuler sum", "readings\nwidth, DF,\nmodel-risk\nmeasures"]
    w, gap = 0.145, 0.026
    for i, text in enumerate(boxes):
        x = i * (w + gap)
        ax.add_patch(plt.Rectangle((x, 0.2), w, 0.6, fill=False, linewidth=0.8, clip_on=False))
        ax.text(x + w / 2, 0.5, text, ha="center", va="center", fontsize=5.8)
        if i < len(boxes) - 1:
            ax.annotate("", xy=(x + w + gap, 0.5), xytext=(x + w, 0.5), arrowprops={"arrowstyle": "-|>", "linewidth": 0.8, "shrinkA": 0, "shrinkB": 0})
    ax.set_xlim(-0.005, 5 * (w + gap) + w + 0.005); ax.set_ylim(0.1, 0.9)
    figkit.save(fig, FIG, "protocol")


def fig_nu() -> None:
    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    nu = nuc["nu"]
    ax.errorbar(nu, [v / 1e3 for v in nuc["base"]], yerr=[2 * v / 1e3 for v in nuc["base_se"]], color="0.0", marker="o", capsize=2, label="t copula, market-credit 0.5")
    ax.errorbar(nu, [v / 1e3 for v in nuc["stress"]], yerr=[2 * v / 1e3 for v in nuc["stress_se"]], color="0.45", marker="s", linestyle="--", capsize=2, label="t copula, market-credit 0.8")
    ax.axhline(nuc["gaussian_base"] / 1e3, color="0.0", linestyle=":", linewidth=0.9); ax.axhline(nuc["gaussian_stress"] / 1e3, color="0.45", linestyle=":", linewidth=0.9)
    ax.axhline(base["variance-covariance"] / 1e3, color="0.6", linestyle="-.", linewidth=0.8)
    ax.text(100, base["variance-covariance"] / 1e3 + 3, "square-root, base (dash-dot)", fontsize=7, ha="right")
    ax.text(100, nuc["gaussian_base"] / 1e3 - 9, "Gaussian, base (dotted)", fontsize=7, ha="right")
    ax.text(100, nuc["gaussian_stress"] / 1e3 - 9, "Gaussian, market-credit 0.8 (dotted)", fontsize=7, ha="right")
    ax.set_ylim(470, 618)
    ax.set_xscale("log"); ax.set_xlabel("degrees of freedom of the t copula"); ax.set_ylabel("economic capital, CLP billion"); ax.legend(loc="upper right", fontsize=7)
    figkit.save(fig, FIG, "nu-curve")


def fig_truth() -> None:
    fig, ax = plt.subplots(figsize=(6.6, 4.0))
    methods = [("simple-sum", "simple sum", 0), ("variance-covariance", "square-root", 1), ("gaussian-copula", "Gaussian", 2), ("t-copula-nu4", "t, nu 4", 3),
               ("t-copula-nu30", "t, nu 30", 4), ("hybrid-calibrated", "hybrid, truth correlation", 5), ("gaussian-kendall-calibrated", "Gaussian, truth rank corr.", 6)]
    y = np.arange(len(st))[::-1]
    for key, lab, i in methods:
        s = figkit.STYLES[i % len(figkit.STYLES)]
        ax.plot([100 * r["relative_error"][key] for r in st], y, linestyle="none", marker=s["marker"] if i < len(figkit.STYLES) else "P", color=s["color"], mfc=("none" if i >= len(figkit.STYLES) else None), label=lab, markersize=4)
    ax.axvline(0, color="0.2", linewidth=0.8)
    ax.axvspan(-5, 5, color="0.93")
    ax.set_yticks(y); ax.set_yticklabels([r["label"] for r in st], fontsize=7)
    ax.set_xlabel("relative error against the planted capital, percent"); ax.legend(fontsize=6.5, loc="lower right")
    figkit.save(fig, FIG, "truth-errors")


def fig_cov() -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    vs = e4["ablation_variants"]
    labs = ["full band", "no bounds", "no stressed\nmatrix", "no t rows", "Gaussian\n(5%)", "sqrt rule\n(5%)", "simple sum\n(5%)", "hybrid\n(5%)", "Gauss. rank\n(5%)"]
    vals = [v["covered"] for v in vs[:9]]
    ax.bar(range(len(vals)), vals, color=["0.15"] * 4 + ["0.6"] * 5, edgecolor="0.0")
    for i, v in enumerate(vals):
        ax.text(i, v + 0.1, str(v), ha="center", fontsize=7)
    ax.set_xticks(range(len(vals))); ax.set_xticklabels(labs, fontsize=6.5, rotation=30, ha="right"); ax.set_ylim(0, len(st) + 1)
    ax.set_ylabel(f"planted structures covered, of {len(st)}")
    figkit.save(fig, FIG, "coverage")


def fig_rearr() -> None:
    n = 2000
    probs = bk.LEVEL + (1 - bk.LEVEL) * (np.arange(n) + 0.5) / n
    mat = np.column_stack([f(probs) for f in case.ppfs])
    como = np.sort(mat.sum(axis=1))
    rea, val, sweeps, ok = bk.rv_bounds.rearrangement_algorithm(mat, "max-min-row-sum", 1e-3, 1000, 7)
    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    x = np.arange(n) / n
    ax.plot(x, como / 1e3, color="0.0", label="comonotonic (sorted columns)")
    ax.plot(x, np.sort(rea.sum(axis=1)) / 1e3, color="0.5", linestyle="--", label="after the rearrangement")
    ax.set_yscale("log"); ax.set_xlabel("scenario in the tail, as a fraction of the cells, sorted by row sum"); ax.set_ylabel("row sum, CLP billion (log scale)"); ax.legend(fontsize=7)
    figkit.save(fig, FIG, "rearrangement")
    M("bdRearrMinComo", bn(float(como.min()))); M("bdRearrMinAfter", bn(float(np.sort(rea.sum(axis=1)).min()))); M("bdRearrSweeps", str(sweeps))
    M("bdRearrMaxComo", bn(float(como.max()))); M("bdRearrMaxAfter", bn(float(rea.sum(axis=1).max())))
    M("bdRearrCells", n0(n))


def fig_euler() -> None:
    fig, ax = plt.subplots(figsize=(5.6, 3.0))
    x = np.arange(4)
    ax.bar(x - 0.2, [100 * v for v in eu["share_mean"]], 0.4, yerr=[200 * v for v in eu["share_sd"]], color="0.2", capsize=2, label="Euler share of the aggregate")
    ax.bar(x + 0.2, [100 * v for v in eu["standalone_share"]], 0.4, color="0.7", edgecolor="0.0", label="share of the stand-alone figures")
    ax.set_xticks(x); ax.set_xticklabels([RISK_NAMES[r] for r in bk.RISKS]); ax.set_ylabel("share, percent"); ax.legend(fontsize=7)
    figkit.save(fig, FIG, "euler")


for fn in (fig_band, fig_protocol, fig_nu, fig_truth, fig_cov, fig_rearr, fig_euler):
    fn()

(TAB / "numbers.tex").write_text("% Generated by make_artifacts.py: every number quoted in the prose.\n" + "\n".join(f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in sorted(MAC.items())) + "\n",
                                 encoding="utf-8", newline="\n")
print("figures", sorted(p.name for p in FIG.glob("*.pdf")), "tables", sorted(p.name for p in TAB.glob("*.tex")), "macros", len(MAC))
