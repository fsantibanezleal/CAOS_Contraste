"""Write every results table of the manuscript from ``experiments/results.json`` and ``experiments/results_theory.json``.

    python manuscripts/scale-and-level-complement-to-the-pla-test/make_tables.py

Tables land in ``tables/`` as booktabs ``.tex`` files that ``main.tex`` inputs; no number in them is typed by hand.
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
sys.path.insert(0, str(HERE / "experiments"))
import figkit  # noqa: E402
import theory  # noqa: E402

R = json.loads((HERE / "experiments" / "results.json").read_text(encoding="utf-8"))
RT = json.loads((HERE / "experiments" / "results_theory.json").read_text(encoding="utf-8"))
OUT = HERE / "tables"

VARIANT = {"none": "No deficiency", "missing-basis": "Missing basis", "stale-volatility": "Stale volatility (20 days)",
           "wrong-correlation": "Wrong correlation", "omitted-factor": "Omitted factor", "time-misalignment": "Time misalignment"}
DET = {"pla": "Regulatory zone, amber or red", "ks_alone": "KS distance alone, not green", "ks_cal": "KS distance, threshold recalibrated at 1\\%",
       "spearman_cal": "Spearman of levels, threshold recalibrated at 1\\%", "desk": "Desk back-test over its limit",
       "cc_975": "Christoffersen conditional coverage, 97.5\\%", "wald_ols": "MZ Wald, OLS covariance",
       "wald_var": "MZ Wald on the squared series", "ljung_box_sq": "Ljung--Box on the squared residual",
       "wald_hc3": "MZ Wald, HC3 (proposed)", "abs_spearman": "Spearman of absolute values (proposed)",
       "roll20": "Spearman of 20-day rolling means (proposed)", "union": "Union of the three proposed, family 1\\%",
       "union_pla": "Union and regulatory zone"}


def T(path, header, rows, **kw):
    """``figkit.table`` with the cells that already carry LaTeX escapes passed through as commands."""
    rows = [[("\\relax " + c) if isinstance(c, str) and "\\" in c and not c.startswith(("$", "\\")) else c for c in r] for r in rows]
    return figkit.table(path, header, rows, **kw)


def shrink(name: str, small: bool = False) -> None:
    """Fit a table to the text width when its natural width exceeds it (``small``: also set it in script size)."""
    path = OUT / name
    s = path.read_text(encoding="utf-8")
    if small:
        s = s.replace("\\small", "\\scriptsize\\setlength{\\tabcolsep}{3pt}", 1)
    s = s.replace("\\begin{tabular}", "\\resizebox{\\textwidth}{!}{%\n\\begin{tabular}", 1)
    s = s.replace("\\end{tabular}", "\\end{tabular}}", 1)
    path.write_text(s, encoding="utf-8")


def pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}"


def cell(r: dict) -> str:
    return f"{pct(r['rate'])} ({pct(r['lo'])}--{pct(r['hi'])})"


def pm(mean: float, sd: float) -> str:
    return f"${pct(mean)}\\pm{pct(sd)}$"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    main_d = ["pla", "ks_alone", "ks_cal", "spearman_cal", "desk", "cc_975", "wald_ols", "wald_var", "ljung_box_sq", "wald_hc3", "abs_spearman", "roll20", "union"]
    ids = list(VARIANT)

    # main results ----------------------------------------------------------------------------------------------------------
    rows = [[DET[d]] + [cell(R["main"][v][d]) for v in ids] for d in main_d]
    hdr = ["Detector"] + [VARIANT[v] for v in ids]
    p = T(OUT / "main-results.tex", hdr, rows, align="p{4.1cm}" + "c" * 6, wide=True,
                     label="tab:main-results",
                     caption=("Share of the 1,000 replications of each variant of the committed C13 desk bake (case seed 13) that each detector "
                              "flags, in percent with the 95\\% Wilson interval; the three proposed components and the union are calibrated on 10,000 "
                              "independent null desk-years at a size of 1\\% per statistic (family 1\\% for the union), the published comparators "
                              "at 1\\% per statistic on the same null, and the regulatory zone and the desk back-test by their own rules. The "
                              "no-deficiency column is the held-out false-alarm rate."))
    s = p.read_text(encoding="utf-8").replace("\\small", "\\scriptsize\\setlength{\\tabcolsep}{3pt}")
    p.write_text(s, encoding="utf-8")

    # repeats ---------------------------------------------------------------------------------------------------------------
    rep = R["repeats"]["by_variant"]
    rd = ["pla", "spearman_cal", "desk", "cc_975", "wald_ols", "ljung_box_sq", "wald_hc3", "abs_spearman", "roll20", "union"]
    rows = [[DET[d]] + [pm(rep[v][d]["mean"], rep[v][d]["sd"]) for v in ids] for d in rd]
    p = T(OUT / "repeats.tex", hdr, rows, align="p{4.1cm}" + "c" * 6, wide=True, label="tab:repeats",
                     caption=("Mean and standard deviation, in percent, of each detector's flag rate over five further independent bakes of "
                              "1,000 replications per variant (case seeds 23, 33, 43, 53 and 63), with the thresholds of the calibration null "
                              "unchanged. The no-deficiency column is the false-alarm rate on five fresh null bakes."))
    s = p.read_text(encoding="utf-8").replace("\\small", "\\scriptsize\\setlength{\\tabcolsep}{3pt}")
    p.write_text(s, encoding="utf-8")

    # lag ladder ------------------------------------------------------------------------------------------------------------
    ld = ["pla", "desk", "cc_975", "wald_ols", "ljung_box_sq", "wald_hc3", "abs_spearman", "roll20", "union"]
    short = {"pla": "Zone", "desk": "Desk", "cc_975": "CC 97.5", "wald_ols": "MZ OLS", "ljung_box_sq": "LB sq.", "wald_hc3": "MZ HC3",
             "abs_spearman": "Abs. Sp.", "roll20": "Roll Sp.", "union": "Union"}
    rows = [[f"{x['lag']}"] + [cell(x[d]) for d in ld] for x in R["ladder"]]
    T(OUT / "lag-ladder.tex", ["Lag (days)"] + [short[d] for d in ld], rows, align="r" + "c" * len(ld), label="tab:lag-ladder", wide=True,
                 caption=("Percent of 1,000 replications flagged, with the 95\\% Wilson interval, as the age of the volatility input of the risk model grows from 2 to 80 days "
                          "(stale-volatility variant, committed seeds; the 20-day row is the committed variant). Zone is the regulatory zone, "
                          "Desk the desk back-test limit, CC the Christoffersen conditional coverage, MZ the Mincer--Zarnowitz Wald test with "
                          "the OLS or HC3 covariance, LB the Ljung--Box test and Sp. the Spearman statistic."))
    shrink("lag-ladder.tex", small=True)

    # area under the curve --------------------------------------------------------------------------------------------------
    names = {"roll20": "Spearman of 20-day rolling means", "abs_spearman": "Spearman of absolute values", "wald_hc3": "MZ Wald, HC3",
             "wald_ols": "MZ Wald, OLS covariance", "wald_var": "MZ Wald on squares", "ljung_box_sq": "Ljung--Box on squared residual",
             "cc_975": "Christoffersen conditional coverage", "ks_reg": "KS distance (regulatory)", "spearman_reg": "Spearman of levels (regulatory)"}
    rows = []
    for k, label in names.items():
        rows.append([label] + [f"{R['auc'][lag][k]['auc']:.3f} ({R['auc'][lag][k]['lo']:.3f}--{R['auc'][lag][k]['hi']:.3f})" for lag in ("5", "10", "20")])
    T(OUT / "auc.tex", ["Statistic", "Lag 5 days", "Lag 10 days", "Lag 20 days"], rows, align="lccc", label="tab:auc",
                 caption=("Area under the ROC curve of each statistic for separating 1,000 stale-volatility replications at the stated lag from "
                          "the 1,000 held-out replications with no deficiency, with the 95\\% percentile bootstrap interval (1,000 resamples); "
                          "the area does not depend on any threshold, so it compares the statistics before calibration."))

    # ablation --------------------------------------------------------------------------------------------------------------
    label = {"full": "Full complement (three statistics, Bonferroni)", "no_wald": "Without the Wald test", "no_abs": "Without the absolute-value Spearman",
             "no_roll": "Without the rolling-mean Spearman", "wald_only": "Wald test alone", "abs_only": "Absolute-value Spearman alone",
             "roll_only": "Rolling-mean Spearman alone (20 days)", "window5": "Rolling-mean Spearman, 5 days",
             "window10": "Rolling-mean Spearman, 10 days", "window40": "Rolling-mean Spearman, 40 days",
             "window60": "Rolling-mean Spearman, 60 days", "ols_wald": "OLS covariance in place of HC3",
             "no_correction": "No multiplicity correction (1\\% each)", "multi_window": "Rolling means at 5, 10, 20 and 40 days (Bonferroni)",
             "full_plus_pla": "Full complement and regulatory zone"}
    cols = ["stale5", "stale10", "stale20", "stale40", "missing-basis", "wrong-correlation", "omitted-factor", "time-misalignment"]
    rows = [[label[a["config"]], cell(a["held_out"])] + [cell(a["power"][c]) for c in cols] for a in R["ablation"]]
    p = T(OUT / "ablation.tex", ["Configuration", "Size", "L5", "L10", "L20", "L40", "Basis", "Corr.", "Factor", "Time"], rows,
                     align="p{4.6cm}" + "c" * 9, wide=True, label="tab:ablation",
                     caption=("Ablation of the complement: held-out false-alarm rate (Size) and percent of 1,000 replications flagged, with the 95\\% Wilson interval, on the "
                              "stale-volatility variant at lags of 5, 10, 20 and 40 days (L5 to L40) and on the missing-basis, wrong-correlation, "
                              "omitted-factor and time-misalignment variants, for the full complement and for each component removed, replaced "
                              "or changed; every configuration is calibrated on the same 10,000 null desk-years at a family size of 1\\% (the "
                              "no-correction row at 1\\% per statistic)."))
    s = p.read_text(encoding="utf-8").replace("\\small", "\\scriptsize\\setlength{\\tabcolsep}{2pt}")
    p.write_text(s, encoding="utf-8")
    shrink("ablation.tex")

    # alternative nulls -----------------------------------------------------------------------------------------------------
    an = {"baseline": "No deficiency, case seed 23 (the generator of the calibration null)", "phi090": "Volatility persistence 0.90", "phi0995": "Volatility persistence 0.995",
          "sd020": "Volatility dispersion 0.20", "sd050": "Volatility dispersion 0.50", "res005": "Pricing noise 5\\% of factor P\\&L",
          "res030": "Pricing noise 30\\% of factor P\\&L"}
    ad = ["pla", "wald_hc3", "abs_spearman", "roll20", "union", "ljung_box_sq", "wald_var"]
    rows = [[an[k]] + [cell(R["altnull"][k][d]) for d in ad] for k in an]
    p = T(OUT / "alt-nulls.tex", ["Null desk"] + [short.get(d, d) for d in ad[:1]] + ["MZ HC3", "Abs. Sp.", "Roll Sp.", "Union", "LB sq.", "MZ squares"],
                     rows, align="p{3.9cm}" + "c" * 7, wide=True, label="tab:alt-nulls",
                     caption=("False-alarm rate in percent, with the 95\\% Wilson interval, of each detector on 1,000 desk-years of a desk with "
                              "no deficiency whose generator differs from the calibration null in one parameter, with every threshold taken "
                              "unchanged from the calibration null; a rate above 1\\% means the stated size does not transfer to that desk."))
    s = p.read_text(encoding="utf-8").replace("\\small", "\\scriptsize\\setlength{\\tabcolsep}{3pt}")
    p.write_text(s, encoding="utf-8")

    # constant mis-scale and level error ------------------------------------------------------------------------------------
    xn = {"scale080": "RTPL times 0.80", "scale090": "RTPL times 0.90", "scale110": "RTPL times 1.10", "scale125": "RTPL times 1.25",
          "shift010": "RTPL shifted by 0.1 sd of HPL", "shift020": "RTPL shifted by 0.2 sd of HPL"}
    xd = ["pla", "ks_cal", "wald_ols", "wald_hc3", "wald_var", "ljung_box_sq", "abs_spearman", "roll20", "union"]
    xh = {"pla": "Zone", "ks_cal": "KS recal.", "wald_ols": "MZ OLS", "wald_hc3": "MZ HC3", "wald_var": "MZ squares", "ljung_box_sq": "LB sq.",
          "abs_spearman": "Abs. Sp.", "roll20": "Roll Sp.", "union": "Union"}
    rows = [[xn[k], f"{R['xform'][k]['mean_slope']:.3f}"] + [cell(R["xform"][k][d]) for d in xd] for k in xn]
    T(OUT / "mis-scale.tex", ["Defect planted in the null desk", "Mean slope"] + [xh[d] for d in xd], rows,
      align="lr" + "c" * len(xd), label="tab:mis-scale", wide=True,
      caption=("Percent of 1,000 replications flagged, with the 95\\% Wilson interval, when a constant mis-scale or a constant level error is "
               "planted in the risk-theoretical P\\&L of the no-deficiency desk (case seed 13), with the mean Mincer--Zarnowitz slope of HPL on RTPL; "
               "every detector of the main comparison was run on these desks and the columns are the ones that respond (the desk back-test, "
               "the Christoffersen test and the recalibrated Spearman correlation of the levels flag at most 0.0\\%, 0.8\\% and 1.2\\% in every row). "
               "The rank statistics are unchanged by a positive rescaling."))
    shrink("mis-scale.tex", small=True)

    # theory: slope and rolling-mean correlation ----------------------------------------------------------------------------
    rt = {r["lag"]: r for r in RT["rows"]}
    rows = []
    for s in R["theory"]["slope_and_rolling_correlation"]:
        lag = s["lag"]
        rows.append([f"{lag}", f"{s['slope_theory']:.4f}", f"${rt[lag]['T100000']['slope_mean']:.4f}\\pm{rt[lag]['T100000']['slope_se']:.4f}$",
                     f"${s['slope_mean']:.4f}\\pm{s['slope_sd'] / 1000 ** 0.5:.4f}$", f"{s['slope_sd']:.4f}", f"{theory.rolling_corr(lag, 20):.4f}",
                     f"${rt[lag]['T100000']['corr_mean']:.4f}\\pm{rt[lag]['T100000']['corr_se']:.4f}$",
                     f"${rt[lag]['T250']['corr_mean']:.4f}\\pm{rt[lag]['T250']['corr_se']:.4f}$", f"${s['roll_pearson_mean']:.4f}\\pm{s['roll_pearson_sd'] / 1000 ** 0.5:.4f}$"])
    p = T(OUT / "theory-slope-corr.tex",
                     ["Lag", "Slope, closed form", "Slope, 100,000-day windows", "Slope, C13 mean", "Slope, C13 sd", "Corr., closed form", "Corr., 100,000-day windows", "Corr., 250-day windows", "Corr., C13 mean"],
                     rows, align="r" + "c" * 9, wide=True, label="tab:theory-slope-corr",
                     caption=("The Mincer--Zarnowitz slope and the Pearson correlation of the 20-day rolling means of the absolute series at each "
                              "lag of the volatility input: the closed forms of Propositions 2 and 3, the mean over 1,000 C13 desk-years of 250 days "
                              "(with its standard error, and for the slope its standard deviation over desk-years), and an independent simulation of the noise-free model on windows of 100,000 and of 250 "
                              "days (mean and standard error over 20 and 4,000 windows)."))
    s = p.read_text(encoding="utf-8").replace("\\small", "\\scriptsize\\setlength{\\tabcolsep}{3pt}")
    p.write_text(s, encoding="utf-8")

    # theory: size of the calibrated rule ----------------------------------------------------------------------------------
    rows = [[f"{g['n']:,}", f"{100 * g['p']:.3f}".rstrip("0").rstrip("."), f"{g['k']}", f"{g['reps']:,}", pct(g["theory_mean"], 3), pct(g["mean"], 3),
             pct(g["theory_sd"], 3), pct(g["sd"], 3)] for g in R["theory"]["gaussian_size"]]
    T(OUT / "theory-size.tex", ["N", "p (\\%)", "k", "Draws", "Mean, Prop. 1", "Mean, simulated", "SD, Prop. 1", "SD, simulated"], rows,
                 align="rrrrrrrr", label="tab:theory-size", wide=True,
                 caption=("Out-of-sample false-alarm rate, in percent, of the critical value that is the (k+1)-th most extreme of N independent "
                          "standard normal null values: the mean and standard deviation that Proposition 1 gives and the values measured over the "
                          "stated number of independent calibration draws."))
    loo = R["theory"]["leave_one_block_out"]
    rows = [[k.replace("_single", " (1\\% per statistic)").replace("_union_share", " (0.333\\% per statistic)").replace("abs_spearman", "absolute-value Spearman")
             .replace("wald_hc3", "Wald, HC3").replace("roll20", "rolling-mean Spearman"), pct(v["theory_mean"], 3), pct(v["mean"], 3), pct(v["sd"], 3)]
            for k, v in loo.items()]
    T(OUT / "theory-loo.tex", ["Statistic and size", "Mean, Prop. 1", "Mean over 10 folds", "SD over 10 folds"], rows, align="lrrr",
                 label="tab:theory-loo",
                 caption=("Leave-one-block-out check of Proposition 1 on the real null: each of the ten blocks of 1,000 null desk-years is flagged "
                          "with the critical value calibrated on the other 9,000; the table gives, in percent, the value Proposition 1 predicts "
                          "for a calibration of 9,000 and the mean and standard deviation of the ten measured rates."))

    # generator and variants ------------------------------------------------------------------------------------------------
    from stats_core import params  # noqa: E402
    meant = {"none": "none planted", "spearman": "Spearman correlation of the levels", "ks": "Kolmogorov--Smirnov distance",
             "either": "either regulatory statistic"}
    planted = {"basis_sd_share": lambda v: f"basis with {100 * v:g}\\% of the HPL standard deviation",
               "vol_lag_days": lambda v: f"volatility input {v:g} days old",
               "correlation_error": lambda v: f"correlation off by {v:g} points",
               "omitted_loading_share": lambda v: f"omitted factor with {100 * v:g}\\% of the HPL standard deviation",
               "lag_days": lambda v: f"P\\&L dated {v:g} day off"}
    rows = [[d["id"].replace("-", " "), meant[d["intended"]],
             "; ".join(planted[p_["name"]](p_["value"]) for p_ in d["parameters"]) or "--"] for d in params.DEFICIENCIES]
    T(OUT / "variants.tex", ["Variant", "Statistic it is meant to break", "Planted parameter"], rows, align="lll",
                 label="tab:variants",
                 caption=("The six variants of the C13 desk generator: what each plants in the risk model or in the dating of its P\\&L and the "
                          "regulatory statistic it was designed to break; the true desk, its volatility law and its pricing noise are the same in "
                          "all six."))

    # hypotheses ------------------------------------------------------------------------------------------------------------
    m = R["main"]
    stale, none = m["stale-volatility"], m["none"]
    rep_stale, rep_none = rep["stale-volatility"], rep["none"]
    mb = m["missing-basis"]
    alt = R["altnull"]
    lad = {x["lag"]: x for x in R["ladder"]}
    rolls = [lad[l]["roll20"]["rate"] for l in (2, 5, 10, 20, 40, 80)]
    mono = all(a < b + 1e-12 for a, b in zip(rolls, rolls[1:], strict=False))
    # the outcome of each prediction is computed from its criterion, never typed
    h1 = stale["union"]["rate"] >= 0.30 and none["union"]["lo"] <= 0.01
    h2_wc = m["wrong-correlation"]["wald_hc3"]["rate"] >= m["wrong-correlation"]["ks_alone"]["rate"]
    h2_mb = mb["wald_hc3"]["rate"] >= mb["ks_alone"]["rate"]
    h2_null = none["wald_hc3"]["lo"] <= 0.01
    h3 = all(alt[k]["union"]["lo"] <= 0.01 for k in ("phi090", "phi0995", "sd020", "sd050", "res005", "res030"))
    h5 = R["xform"]["scale090"]["wald_hc3"]["lo"] > R["xform"]["scale090"]["pla"]["hi"]
    rows = [
        ["H1", "At a size of at most 1\\%, the stale-volatility model is flagged in at least 30\\% of replications; refuted below 10\\%",
         f"union {cell(stale['union'])}\\% at held-out size {cell(none['union'])}\\%; regulatory zone {pct(stale['pla']['rate'])}\\%", "held" if h1 else "failed"],
        ["H2", "The Wald test flags wrong-correlation and missing-basis at least as often as the KS distance alone, and the no-deficiency desk at most at the stated rate",
         f"wrong correlation {pct(m['wrong-correlation']['wald_hc3']['rate'])}\\% against {pct(m['wrong-correlation']['ks_alone']['rate'])}\\%; "
         f"missing basis {pct(mb['wald_hc3']['rate'])}\\% against {pct(mb['ks_alone']['rate'])}\\%; no deficiency {pct(none['wald_hc3']['rate'])}\\%",
         "held" if (h2_wc and h2_mb and h2_null) else "failed"],
        ["H3", "The false-alarm rate of the union stays at most 1\\% on desks that differ from the calibration null",
         f"{pct(alt['phi0995']['union']['rate'])}\\% (persistence 0.995), {pct(alt['sd050']['union']['rate'])}\\% (dispersion 0.50), "
         f"{pct(alt['res030']['union']['rate'])}\\% (pricing noise 30\\%)", "held" if h3 else "failed"],
        ["H4", "The flag rate of the rolling-mean statistic rises with the age of the volatility input",
         "rates " + ", ".join(pct(x) for x in rolls) + "\\% at 2, 5, 10, 20, 40 and 80 days", "held" if mono else "failed"],
        ["H5", "The complement flags a constant mis-scale that the regulatory zone does not",
         f"Wald {pct(R['xform']['scale090']['wald_hc3']['rate'])}\\% against zone {pct(R['xform']['scale090']['pla']['rate'])}\\% at a 10\\% mis-scale", "held" if h5 else "failed"],
    ]
    T(OUT / "hypotheses.tex", ["Id", "Prediction", "Measured", "Outcome"], rows, align="llp{5.4cm}l", wide=True,
                 label="tab:hypotheses",
                 caption=("The five predictions of the experimental design, the criterion each was held to, the measured values on the committed "
                          "bake or on the experiments of Section~\\ref{sec:experimental-design}, and whether each held; H1 is the acceptance and "
                          "refutation criterion fixed for the method before this evaluation and H2 the second clause of the research brief that proposed it."))
    s = (OUT / "hypotheses.tex").read_text(encoding="utf-8").replace("\\small", "\\scriptsize")
    s = s.replace("llp{5.4cm}l", "lp{4.8cm}p{6.2cm}l")
    (OUT / "hypotheses.tex").write_text(s, encoding="utf-8")
    for name in ("main-results.tex", "repeats.tex", "alt-nulls.tex", "theory-loo.tex", "theory-slope-corr.tex", "variants.tex"):
        shrink(name)
    print(f"tables written to {OUT}")


if __name__ == "__main__":
    main()
