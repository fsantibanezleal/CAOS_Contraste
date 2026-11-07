"""The tables and the number macros of the manuscript, written from ``experiments/results.json`` and the committed documents.

No number of the text or of a table is typed: ``numbers.tex`` defines one macro per figure quoted in the prose and each ``tab-*.tex``
is a booktabs table. Run from the repository root after ``experiments/analyse.py``::

    python manuscripts/instability-of-operational-risk-capital/tables/make_tables.py
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

R = json.loads((HERE.parent / "experiments" / "results.json").read_text(encoding="utf-8"))
CELLS = R["cells"]
VAR = {"xi-0-6": "A", "xi-0-8": "B", "xi-0-96": "C", "xi-1-1": "D"}
CELL = {"y5-h10000": "Fa", "y5-h20000": "Fb", "y10-h10000": "Ta", "y10-h20000": "Tb"}
RUNG = {"lda_lognormal": "Lg", "lda_lognormal_truncated": "Tr", "lda_splice": "Sp", "sla": "Sl", "sla_mean_corrected": "Mc", "scenario": "Sc",
        "sla_mean_adjusted": "Ma", "sla_cvm": "Cv", "sla_obre": "Ob", "sla_cvm_lognormal": "Cl"}
LABEL = {"lda_lognormal": "Lognormal, threshold ignored", "lda_lognormal_truncated": "Truncated lognormal", "lda_splice": "Lognormal-GPD splice",
         "sla": "Single loss approximation", "sla_mean_corrected": "Single loss approximation, mean correction", "scenario": "Scenario combination",
         "sla_mean_adjusted": "Mean-adjusted single loss approximation", "sla_cvm": "Cram\\'er-von Mises GPD", "sla_obre": "Optimally bias-robust GPD",
         "sla_cvm_lognormal": "Cram\\'er-von Mises lognormal"}
ABL = {"threshold": "Model the collection threshold", "heavy_tail": "Splice a GPD tail onto the body", "closed_form": "Closed-form tail instead of aggregation",
       "mean_correction": "Add the mean correction", "expert_prior": "Replace the tail by the scenario credibility tail",
       "mean_adjusted": "Adjust the approximation by one mean", "cvm": "Fit the GPD by Cram\\'er-von Mises", "obre": "Fit the GPD by the bias-robust estimator",
       "wrong_family": "Fit a lognormal instead of the GPD"}
MACROS: dict[str, str] = {}
SIZE = {50: "Fifty", 100: "Hundred", 250: "TwoFifty", 500: "FiveHundred", 1000: "Thousand"}


def mac(name: str, value: str) -> None:
    assert name.isalpha(), name
    MACROS[name] = value


def f2(x: float) -> str:
    return f"{x:.2f}"


def f3(x: float) -> str:
    return f"{x:.3f}"


def pc(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}"


def ci(lo: float, hi: float, d: int = 2) -> str:
    return f"[{lo:.{d}f}, {hi:.{d}f}]"


def table(name: str, body: str) -> None:
    (HERE / f"{name}.tex").write_text(body, encoding="utf-8")


def eur_m(x: float) -> str:
    return f"{x / 1e6:,.0f}".replace(",", "{,}")


# ---------------------------------------------------------------------------------------------------------------- macros
def macros() -> None:
    mac("nHist", "16{,}000")
    mac("nCells", "16")
    mac("nPer", str(CELLS[0]["n_replications"]))
    for c in CELLS:
        v, k = VAR[c["variant"]], CELL[c["id"]]
        for r, rs in RUNG.items():
            s = c["rungs"][r]
            if not s["n_defined"]:
                continue
            p = f"c{rs}{v}{k}"
            mac(p + "Med", f2(s["median"]))
            mac(p + "Iqr", f2(s["iqr"]))
            mac(p + "IqrLo", f2(s["ci"]["iqr"][0]))
            mac(p + "IqrHi", f2(s["ci"]["iqr"][1]))
            mac(p + "Below", pc(s["share_below_one"], 0))
            mac(p + "Ndef", str(s["n_defined"]))
            mac(p + "Sd", f2(s["log_sd"]))
            mac(p + "Plo", f"{s['p05']:.3f}")
            mac(p + "Phi", f"{s['p95']:.1f}")
        t = c["theory"]
        mac(f"cTh{v}{k}Sd", f2(t["sd_log"]))
        mac(f"cTh{v}{k}Iqr", f2(t["iqr"]))
        mac(f"cTh{v}{k}Yrs", f"{t['years_green']:.0f}")
        mac(f"cTh{v}{k}Rec", f"{t['records_green']:,.0f}".replace(",", "{,}"))
        mac(f"cTh{v}{k}K", f"{t['k']:.0f}")
        mac(f"cTh{v}{k}SdXi", f3(t["sd_log_xi_hat"]))
        mac(f"cTh{v}{k}Share", pc(t["share_xi_hat_at_least_one"], 1))
        mac(f"cXi{v}{k}Share", pc(c["tail_profile"][0]["share_at_least_one"], 1))
        for j, m in enumerate(("One", "Two", "Four", "Eight")):
            mac(f"cXi{v}{k}{m}", pc(c["tail_profile"][j]["share_at_least_one"], 0))
            mac(f"cXi{v}{k}{m}N", str(c["tail_profile"][j]["n_fits"]))
        mac(f"cXi{v}{k}Med", f2(c["tail_profile"][0]["median"]))
    for vid, d in R["variants"].items():
        v = VAR[vid]
        mac(f"truth{v}", eur_m(d["truth_eur"]))
        mac(f"xi{v}", f"{d['tail_index']:g}")
        mac(f"lamfloor{v}", f"{d['lambda_floor']:.1f}")
        mac(f"scale{v}", f"{d['scale_eur']:,.0f}".replace(",", "{,}"))
        mac(f"mcz{v}", f2(abs(d["mc_check"]["value_eur"] - d["truth_eur"]) / d["mc_check"]["standard_error_eur"]))
        if d["mean_eur"] is not None:
            mac(f"mean{v}", f"{d['mean_eur'] / 1e6:.1f}")
    lo, hi = R["splice_iqr_range"]
    mac("spIqrMin", f2(lo))
    mac("spIqrMax", f2(hi))
    L = R["lights"]
    mac("redTotal", str(L["total"]))
    mac("redSix", str(L["six_rung_red"]))
    mac("rowsSix", str(L["six_rung_rows"]))
    inf = R["infinite_mean"]
    mac("infLo", pc(inf["xi_0_96_conclude_infinite"][0], 1))
    mac("infHi", pc(inf["xi_0_96_conclude_infinite"][1], 1))
    mac("finLo", pc(inf["xi_1_1_conclude_finite"][0], 1))
    mac("finHi", pc(inf["xi_1_1_conclude_finite"][1], 1))
    tv = R["theory_verdict"]
    mac("thSdMaxErr", pc(tv["max_relative_error_sd"], 1))
    mac("thSdMeanErr", pc(tv["mean_relative_error_sd"], 2))
    mac("thShareMaxErr", pc(tv["max_abs_error_share_near_one"], 1))
    mac("preSd", pc(R["settings"]["pre_stated"]["sd_relative_error"], 0))
    mac("preShare", pc(R["settings"]["pre_stated"]["share_absolute_error"], 0))
    yrs = [c["theory"]["years_green"] for c in CELLS]
    mac("yrsMin", f"{min(yrs):.0f}")
    mac("yrsMax", f"{max(yrs):.0f}")
    ch = R["check"]
    mac("chkRatio", f"{ch['max_abs_diff_ratio_percentile']:.1e}".replace("e-0", "\\times 10^{-").replace("e-", "\\times 10^{-") + "}")
    mac("chkShare", f"{ch['max_abs_diff_share']:.3f}")
    for name, a in R["ablation"].items():
        n = name.replace("_", "").title().replace(" ", "")
        mac(f"ab{n}From", pc(a["from_within"], 1))
        mac(f"ab{n}To", pc(a["to_within"], 1))
        mac(f"ab{n}Delta", pc(a["delta_within"], 1))
        mac(f"ab{n}Lo", pc(a["delta_within_ci"][0], 1))
        mac(f"ab{n}Hi", pc(a["delta_within_ci"][1], 1))
        mac(f"ab{n}N", f"{a['n_paired']:,}".replace(",", "{,}"))
    for r, rs in RUNG.items():
        p = R["pooled"][r]
        mac(f"pl{rs}Within", pc(p["share_within_factor"], 1))
        mac(f"pl{rs}Def", pc(p["share_defined"], 0))
        mac(f"pl{rs}Iqr", f2(p["mean_cell_iqr"]))
        mac(f"pl{rs}Med", f2(p["mean_cell_median"]))
    # the precision of the measurement: relative standard deviation of the IQR over random subsets, pooled over cells
    for rung, rs in (("lda_splice", "Sp"), ("sla", "Sl")):
        for m in R["settings"]["subset_sizes"]:
            rel = [c["subset_iqr"][rung][str(m)]["sd"] / c["subset_iqr"][rung][str(m)]["mean"] for c in CELLS
                   if rung in c["subset_iqr"] and str(m) in c["subset_iqr"][rung] and c["subset_iqr"][rung][str(m)]["mean"] > 0]
            if rel:
                import statistics
                mac(f"sub{rs}{SIZE[m]}", pc(statistics.median(rel), 0))
    for vid, c in sma_rows():
        if c["id"] == "y10-h20000":
            o = c["sma"]["orc_over_true_quantile"]
            mac(f"sma{VAR[vid]}", f"{o['median']:.2f}")
            mac(f"smaIqr{VAR[vid]}", f"{o['p75'] - o['p25']:.3f}")
    for vid in R["variants"]:
        qd = figkit.doc(f"C17/{vid}.json")["outputs"]["exceedance"]["quantile_999_eur"]
        mac(f"slGap{VAR[vid]}", pc(1 - qd["sla"] / qd["fft"], 1))
        mac(f"panGap{VAR[vid]}", f"{100 * abs(qd['panjer'] / qd['fft'] - 1):.2f}")
    mac("slBelowCells", str(sum(1 for c in CELLS if c["rungs"]["sla"]["median"] < 1)))
    mac("slMeanMed", f2(R["pooled"]["sla"]["mean_cell_median"]))
    mac("nFailed", str(sum(c["n_failed"] for c in CELLS)))
    # the worked example of the theory: xi = 0.96, 5 years, threshold EUR 10,000 and the band of indistinguishability
    ex = next(c for c in CELLS if c["variant"] == "xi-0-96" and c["id"] == "y5-h10000")["theory"]
    xi_ = 0.96
    big_l = math.log(ex["lam_h"] / (1 - R["settings"]["level"]))
    ell = big_l - 1 / xi_
    lead = math.sqrt(((1 + xi_) * ((1 + xi_) * ell ** 2 - 2 * ell + 2) + xi_ ** 2) / ex["k"])
    mac("exL", f"{big_l:.1f}")
    mac("exEll", f"{ell:.1f}")
    mac("exK", f"{ex['k']:.0f}")
    mac("exLam", f"{ex['lam_h']:.1f}")
    mac("exSdXi", f2((1 + xi_) / math.sqrt(ex["k"])))
    mac("exSigmaLead", f2(lead))
    mac("exFactor", f"{math.exp(lead):.1f}")
    mac("exBandC", f2(1.959964 * (1 + xi_) / math.sqrt(ex["k"])))
    k11 = next(c for c in CELLS if c["variant"] == "xi-1-1" and c["id"] == "y10-h10000")["theory"]["k"]
    mac("exKEleven", f"{k11:.0f}")
    mac("exBandD", f2(1.959964 * 2.1 / math.sqrt(k11)))
    sig_star = math.asinh(R["settings"]["green_iqr"] / 2) / 0.6744897501960817
    mac("sigmaStar", f3(sig_star))
    ks = [c["theory"]["k"] for c in CELLS]
    mac("kMin", f"{min(ks):.0f}")
    mac("kMax", f"{max(ks):.0f}")
    sd = {(c["variant"], c["years"], c["threshold_eur"]): c["rungs"]["sla"]["log_sd"] for c in CELLS}
    yr = [sd[(v, 5, h)] / sd[(v, 10, h)] for v in R["variants"] for h in (10000, 20000)]
    th = [sd[(v, y, 20000)] / sd[(v, y, 10000)] for v in R["variants"] for y in (5, 10)]
    mac("yrRatio", f2(sum(yr) / len(yr)))
    mac("yrRatioMin", f2(min(yr)))
    mac("yrRatioMax", f2(max(yr)))
    mac("thrRatio", f2(sum(th) / len(th)))
    mac("thrRatioMin", f2(min(th)))
    mac("thrRatioMax", f2(max(th)))
    mac("sqrtTwo", f2(math.sqrt(2)))
    over = [t["iqr_predicted"] / t["iqr_measured"] - 1 for t in R["theory_check"]]
    mac("thIqrMaxErr", pc(max(abs(x) for x in over), 0))
    mac("thIqrOver", str(sum(1 for x in over if x > 0)))
    mac("thIqrMean", pc(sum(over) / len(over), 0))
    # the number of splice histories undefined
    und = [1000 - c["rungs"]["lda_splice"]["n_defined"] for c in CELLS]
    mac("spUndMin", str(min(und)))
    mac("spUndMax", str(max(und)))
    out = ["% Written by tables/make_tables.py from experiments/results.json: one macro per number quoted in the text."]
    out += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in sorted(MACROS.items())]
    (HERE / "numbers.tex").write_text("\n".join(out) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------------------------------------------- tables
def tab_truth() -> None:
    rows = []
    for vid, d in R["variants"].items():
        doc = figkit.doc(f"C17/{vid}.json")
        err = doc["outputs"]["calibration"]["fit"]["max_abs_log_error"]
        mean = f"{d['mean_eur'] / 1e6:.1f}" if d["mean_eur"] is not None else "none"
        mc = d["mc_check"]
        rows.append(f"{d['tail_index']:g} & {d['scale_eur']:,.0f} & {d['lambda_floor']:.1f} & {d['truth_eur'] / 1e6:,.1f} & {mean} & "
                    f"{abs(mc['value_eur'] - d['truth_eur']) / mc['standard_error_eur']:.2f} & {err:.3f} \\\\".replace(",", "{,}"))
    table("tab-truth", "\\begin{table}[htbp]\n\\centering\\small\n\\caption{The generator and its known truth at the four tail indices: the scale of the generalised Pareto severity above the floor of EUR 10,000, "
          "the rate of losses a year above the floor, the true 99.9 percent quantile of the annual loss by Fourier aggregation, the true mean, the distance between the Monte Carlo "
          "of ten million years and the Fourier quantile in standard errors of the Monte Carlo, and the largest log error of the calibration to the four median percentiles of the 2008 exercise.}\n"
          "\\label{tab:truth}\n\\fitwidth{\\begin{tabular}{rrrrrrr}\n\\toprule\n$\\xi$ & Scale (EUR) & Rate (a year) & True quantile (EUR m) & True mean (EUR m) & Monte Carlo gap ($\\mathrm{se}$) & Calibration error \\\\\n\\midrule\n"
          + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}}\n\\end{table}\n")


def tab_main() -> None:
    rows = []
    for c in CELLS:
        s, a = c["rungs"]["lda_splice"], c["rungs"]["sla"]
        rows.append(f"{c['tail_index']:g} & {c['years']} & {c['threshold_eur'] // 1000} & {s['n_defined']} & {f2(s['median'])} & {f2(s['iqr'])} {ci(*s['ci']['iqr'])} & "
                    f"{pc(s['share_below_one'], 0)} & {f2(a['median'])} & {f2(a['iqr'])} {ci(*a['ci']['iqr'])} & {pc(a['share_below_one'], 0)} \\\\")
        if c["id"] == "y10-h20000" and c["tail_index"] != 1.1:
            rows.append("\\midrule")
    table("tab-main-results", "\\begin{table}[htbp]\n\\centering\\scriptsize\n\\caption{The 99.9 percent capital of the lognormal-GPD splice and of the single loss approximation as a multiple of the true quantile, "
          "in the 16 cells of 1{,}000 independent histories each: the histories on which the splice is defined, the median ratio, the interquartile range of the ratio with its 95 percent "
          "percentile bootstrap interval over the histories (2{,}000 resamples), and the percentage of histories below the truth. The single loss approximation is defined on every history.}\n"
          "\\label{tab:main-results}\n\\fitwidth{\\begin{tabular}{rrrr|rrr|rrr}\n\\toprule\n & & & \\multicolumn{4}{c|}{Splice} & \\multicolumn{3}{c}{Single loss approximation} \\\\\n"
          "$\\xi$ & Years & $H$ (EUR k) & Defined & Median & IQR [95\\% CI] & Below 1 (\\%) & Median & IQR [95\\% CI] & Below 1 (\\%) \\\\\n\\midrule\n"
          + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}}\n\\end{table}\n")


def tab_rungs() -> None:
    rows = []
    for r in RUNG:
        p = R["pooled"][r]
        iq = [c["rungs"][r]["iqr"] for c in CELLS if c["rungs"][r]["n_defined"]]
        lo, hi = p["share_within_factor_ci"]
        rows.append(f"{LABEL[r]} & {pc(p['share_defined'], 0)} & {f2(p['mean_cell_median'])} & {f2(min(iq))} to {f2(max(iq))} & {pc(p['share_within_factor'], 1)} [{pc(lo, 1)}, {pc(hi, 1)}] & "
                    f"{R['lights']['by_rung'][r.replace('_', '-')]['red']} of {sum(R['lights']['by_rung'][r.replace('_', '-')].values())} \\\\")
        if r == "scenario":
            rows.append("\\midrule")
    table("tab-rungs", "\\begin{table}[htbp]\n\\centering\\small\n\\caption{The ten estimation rungs over the 16 cells: the share of the 16{,}000 histories on which the rung returns a capital, the mean over cells of the "
          "median ratio to the truth, the range over cells of the interquartile range of the ratio, the share of defined histories within a factor of two of the truth with its Wilson 95 percent interval, "
          "and the number of cells on which the capital stability test is red.}\n\\label{tab:rungs}\n"
          "\\fitwidth{\\begin{tabular}{lrrrrr}\n\\toprule\nRung & Defined (\\%) & Mean median & IQR range over cells & Within factor 2 (\\%) [95\\% CI] & Red cells \\\\\n\\midrule\n"
          + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}}\n\\end{table}\n")


def tab_tail() -> None:
    rows = []
    for c in CELLS:
        p = c["tail_profile"][0]
        t = c["theory"]
        rows.append(f"{c['tail_index']:g} & {c['years']} & {c['threshold_eur'] // 1000} & {p['n_fits']} & {f2(p['median'])} {ci(p['p05'], p['p95'])} & "
                    f"{pc(p['share_at_least_one'], 1)} [{pc(p['ci_at_least_one'][0], 1)}, {pc(p['ci_at_least_one'][1], 1)}] & {pc(t['share_xi_hat_at_least_one'], 1)} & "
                    f"{' & '.join(pc(c['tail_profile'][j]['share_at_least_one'], 0) for j in (1, 2, 3))} \\\\")
        if c["id"] == "y10-h20000" and c["tail_index"] != 1.1:
            rows.append("\\midrule")
    table("tab-tail-index", "\\begin{table}[htbp]\n\\centering\\scriptsize\n\\caption{The tail index fitted above the collection threshold in each cell: the histories with a fit, the median and the 5th to 95th "
          "percentiles of the fitted index, the percentage of histories whose index is 1 or more with its Wilson 95 percent interval, the percentage predicted by the normal approximation of the maximum likelihood "
          "estimator, and the measured percentage when the fit is made above two, four and eight times the threshold.}\n\\label{tab:tail-index}\n"
          "\\fitwidth{\\begin{tabular}{rrrrrrrrrr}\n\\toprule\n$\\xi$ & Years & $H$ (EUR k) & Fits & Median $\\hat\\xi$ [5\\%, 95\\%] & $\\hat\\xi\\ge1$ (\\%) [95\\% CI] & Predicted (\\%) & $2H$ & $4H$ & $8H$ \\\\\n\\midrule\n"
          + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}}\n\\end{table}\n")


def tab_theory() -> None:
    rows = []
    for c, t in zip(CELLS, R["theory_check"], strict=True):
        th = c["theory"]
        rows.append(f"{c['tail_index']:g} & {c['years']} & {c['threshold_eur'] // 1000} & {th['k']:.0f} & {f3(t['sd_measured'])} & {f3(t['sd_predicted'])} & {100 * t['relative_error']:+.1f} & "
                    f"{f2(t['iqr_measured'])} & {f2(t['iqr_predicted'])} & {t['years_green']:.0f} \\\\")
        if c["id"] == "y10-h20000" and c["tail_index"] != 1.1:
            rows.append("\\midrule")
    table("tab-theory", "\\begin{table}[htbp]\n\\centering\\scriptsize\n\\caption{The dispersion of the single loss approximation predicted by the delta method at the true parameters against the dispersion measured "
          "over the 1{,}000 histories of each cell: the expected number of recorded losses $k$, the standard deviation of the logarithm of the ratio, measured and predicted, the relative error of the prediction in percent, "
          "the interquartile range of the ratio, measured and predicted by a lognormal of the predicted dispersion, and the years of history at which the predicted interquartile range reaches 0.25.}\n\\label{tab:theory}\n"
          "\\fitwidth{\\begin{tabular}{rrrrrrrrrr}\n\\toprule\n$\\xi$ & Years & $H$ (EUR k) & $k$ & $\\mathrm{sd}$ measured & $\\mathrm{sd}$ predicted & Error (\\%) & IQR measured & IQR predicted & Years for 0.25 \\\\\n\\midrule\n"
          + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}}\n\\end{table}\n")


def tab_ablation() -> None:
    rows = []
    for name, a in R["ablation"].items():
        pairs = f"{a['n_paired']:,}".replace(",", "{,}")
        rows.append(f"{ABL[name]} & {LABEL[a['from']]} to {LABEL[a['to']]} & {pairs} & {pc(a['from_within'], 1)} & {pc(a['to_within'], 1)} & "
                    f"{100 * a['delta_within']:+.1f} [{100 * a['delta_within_ci'][0]:+.1f}, {100 * a['delta_within_ci'][1]:+.1f}] & {f2(a['from_log_sd'])} to {f2(a['to_log_sd'])} \\\\")
    table("tab-ablation", "\\begin{table}[htbp]\n\\centering\\scriptsize\n\\caption{The ablation of the estimation ladder: for each component, the paired comparison on the histories of the 16 cells where both rungs return a capital, "
          "the share of those histories within a factor of two of the truth before and after, the change in percentage points with its 95 percent bootstrap interval over the paired histories, and the standard deviation of the "
          "logarithm of the ratio before and after.}\n\\label{tab:ablation}\n"
          "\\fitwidth{\\begin{tabular}{llrrrrr}\n\\toprule\nComponent & Rungs compared & Pairs & Before (\\%) & After (\\%) & Change (points) [95\\% CI] & $\\mathrm{sd}$ of $\\ln$ ratio \\\\\n\\midrule\n"
          + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}}\n\\end{table}\n")


def tab_lights() -> None:
    rows = []
    for m, d in R["lights"]["by_rung"].items():
        rows.append(f"{m.replace('-', ' ')} & {d['green']} & {d['amber']} & {d['red']} \\\\")
    table("tab-lights", "\\begin{table}[htbp]\n\\centering\\small\n\\caption{The lights of the capital stability test over the 16 cells for each rung, against the limits of 0.25 and 0.50 on the "
          "interquartile range of the ratio and 0.10 and 0.25 on the absolute bias: the number of cells in which each rung is green, amber and red, from the committed documents.}\n\\label{tab:lights}\n"
          "\\begin{tabular}{lrrr}\n\\toprule\nRung & Green & Amber & Red \\\\\n\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")


def tab_hypotheses() -> None:
    inf, tv, L = R["infinite_mean"], R["theory_verdict"], R["lights"]
    lo, hi = R["splice_iqr_range"]
    rows = [
        ("H1", "The interquartile range of the splice capital over the true quantile lies between 1.35 and 3.30 in the 16 cells",
         f"{lo:.4f} to {hi:.4f}", "Held" if round(lo, 2) == 1.35 and round(hi, 2) == 3.30 else "Refuted"),
        ("H2", "Every capital stability row of the six-rung ladder is red", f"{L['six_rung_red']} of {L['six_rung_rows']} rows red ({L['red']} of {L['total']} with the four robust rungs)",
         "Held" if L["six_rung_red"] == L["six_rung_rows"] else "Refuted"),
        ("H3", "27 to 34 percent (whole percent) of the histories at $\\xi=0.96$ conclude an infinite mean", f"{pc(inf['xi_0_96_conclude_infinite'][0])} to {pc(inf['xi_0_96_conclude_infinite'][1])} percent",
         "Held" if round(100 * inf["xi_0_96_conclude_infinite"][0]) == 27 and round(100 * inf["xi_0_96_conclude_infinite"][1]) == 34 else "Refuted"),
        ("H4", "9 to 27 percent (whole percent) of the histories at $\\xi=1.1$ conclude a finite mean", f"{pc(inf['xi_1_1_conclude_finite'][0])} to {pc(inf['xi_1_1_conclude_finite'][1])} percent",
         "Held" if round(100 * inf["xi_1_1_conclude_finite"][0]) == 9 and round(100 * inf["xi_1_1_conclude_finite"][1]) == 27 else "Refuted"),
        ("H5", "The delta-method dispersion of the single loss approximation is within 25 percent of the measured one in every cell",
         f"largest relative error {pc(tv['max_relative_error_sd'])} percent", "Held" if tv["sd_held"] else "Refuted"),
        ("H6", "The predicted share of histories with $\\hat\\xi\\ge1$ is within 5 points of the measured one in every cell at $\\xi=0.96$ and $1.1$",
         f"largest absolute error {pc(tv['max_abs_error_share_near_one'])} points", "Held" if tv["share_held"] else "Refuted")]
    body = "\n".join(f"{a} & {b} & {c} & {d} \\\\" for a, b, c, d in rows)
    table("tab-hypotheses", "\\begin{table}[htbp]\n\\centering\\small\n\\caption{The six predictions stated before the measurements, the value measured on the 16{,}000 histories, and whether each held. "
          "H1 to H4 are the quantitative statements of the measurement; H5 and H6 are the predictions of the theory, with the tolerances fixed before they were compared with the 16 cells.}\n\\label{tab:hypotheses}\n"
          "\\begin{tabularx}{\\textwidth}{lXXl}\n\\toprule\nId & Prediction & Measured & Outcome \\\\\n\\midrule\n" + body + "\n\\bottomrule\n\\end{tabularx}\n\\end{table}\n")


def sma_rows() -> list[tuple[str, dict]]:
    """The cells of the committed documents with their standardised-approach block (the ratio of its capital to the truth by history)."""
    out = []
    for vid in R["variants"]:
        doc = figkit.doc(f"C17/{vid}.json")
        for c in doc["outputs"]["cells"]:
            out.append((vid, c))
    return out


def tab_sma() -> None:
    rows = []
    for vid, c in sma_rows():
        o = c["sma"]["orc_over_true_quantile"]
        xi = R["variants"][vid]["tail_index"]
        rows.append(f"{xi:g} & {c['years']} & {c['collection_threshold_eur'] // 1000} & {o['median']:.3f} & {o['p25']:.3f} to {o['p75']:.3f} & {o['p75'] - o['p25']:.3f} & "
                    f"{c['sma']['orc_eur']['median'] / 1e6:.1f} \\\\")
        if c["id"] == "y10-h20000" and xi != 1.1:
            rows.append("\\midrule")
    table("tab-sma", "\\begin{table}[htbp]\n\\centering\\small\n\\caption{The standardised approach against the true quantile in the 16 cells: the median over the 1{,}000 histories of the "
          "operational risk capital divided by the true 99.9 percent quantile, its first and third quartiles, its interquartile range and the median capital in EUR million, at the business indicator "
          "component of EUR 180 million of the synthetic bank.}\n\\label{tab:sma}\n\\begin{tabular}{rrrrrrr}\n\\toprule\n$\\xi$ & Years & $H$ (EUR k) & Median ratio & Quartiles & IQR & Median capital (EUR m) \\\\\n\\midrule\n"
          + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")


def main() -> int:
    macros()
    for fn in (tab_truth, tab_main, tab_rungs, tab_tail, tab_theory, tab_ablation, tab_lights, tab_hypotheses, tab_sma):
        fn()
    print("wrote numbers.tex with", len(MACROS), "macros and 9 tables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
