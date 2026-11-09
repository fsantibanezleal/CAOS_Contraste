"""The tables of the manuscript and ``numbers.tex``, the numbers its prose quotes, from the committed C04 documents and
the experiment outputs. Nothing is typed: every number is read, computed here and written either into a table or into a
LaTeX macro of ``numbers.tex`` (with its source in ``numbers.json``).

Run from the repository root, after the five experiment scripts::

    python manuscripts/default-definition-withdrawals-thin-grades/tables/make_tables.py
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
MS = HERE.parent
ROOT = MS.parents[1]
sys.path.insert(0, str(ROOT / "manuscripts" / "_shared"))

import figkit  # noqa: E402

GRADES = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC-C"]
B_, C_ = 5, 6  # the indices of B and CCC to C


def ex(name: str) -> dict:
    return json.loads((MS / "experiments" / f"{name}.json").read_text(encoding="utf-8"))


DEF, WD, TH, THIN, EXTRA = ex("definitions"), ex("withdrawals"), ex("theory"), ex("thin"), ex("extra")
FIP = DEF["fitch_populated_years"]
W_RATE = TH["withdrawal_rate"]
COMMITTED_WD = figkit.doc("C04/withdrawals.json")["outputs"]
COMMITTED_THIN = figkit.doc("C04/thin.json")["outputs"]
SP, FI, MO = DEF["agencies"]["sp"], DEF["agencies"]["fitch"], DEF["agencies"]["moodys"]
SPDOC = figkit.doc("C04/sp.json")["outputs"]

NUM: dict[str, dict[str, str]] = {}


def put(name: str, value: str, src: str) -> str:
    """Record a macro: its value (text) and the source of the number."""
    assert name.isalpha(), name
    assert name not in NUM, name
    NUM[name] = {"value": value, "source": src}
    return value


def f(x: float, d: int = 2) -> str:
    return f"{x:.{d}f}"


def pc(x: float, d: int = 2) -> str:
    return f"{100 * x:.{d}f}"


KT = {0: "Zero", 1: "One", 2: "Two", 3: "Three", 5: "Five", 9: "Nine", 19: "Nineteen"}


def sci(x: float) -> str:
    mant, exp = f"{x:.1e}".split("e")
    return f"{mant}\\times10^{{{int(exp)}}}"


def _num(x: float, d: int) -> str:
    s = f"{x:.{d}f}"
    return s.lstrip("-") if float(s) == 0 else s


def m(x: float, d: int = 2) -> str:
    return f"${_num(x, d)}$"


def pm(x: float, se: float, d: int = 1) -> str:
    return f"${_num(x, d)}\\pm{_num(se, d)}$"


FIT = {"main-results", "thin", "theory", "ablation", "data", "definitions", "duration"}  # the tables wider than the text, scaled down to it


def write(name: str, header, rows, caption: str, label: str, align: str | None = None, small: bool = True) -> None:
    path = HERE / f"{name}.tex"
    group = lambda n: f"{n:,}".replace(",", "{,}")  # noqa: E731
    for token, value in (("@BOOT@", group(DEF["bootstrap_resamples"])), ("@REPS@", group(WD["rungs"][0]["reps"])),
                         ("@REPSTESTS@", group(WD["tests"][0]["n_rep"])),
                         ("@THREPS@", str(TH["chains"]["B"]["rows"][0]["reps"])),
                         ("@THOBLIG@", group(TH["chains"]["B"]["rows"][0]["obligors"]))):
        caption = caption.replace(token, value)
    # every string cell of this script is LaTeX; figkit.table passes a cell through when it starts with "\\" or "$"
    rows = [[("\\relax " + c) if isinstance(c, str) and not c.startswith(("$", "\\")) else c for c in r] for r in rows]
    figkit.table(path, header, rows, caption=caption, label=label, align=align)
    if small:
        text = path.read_text(encoding="utf-8").replace("\\small", "\\footnotesize", 1)
        text = text.replace("\\centering", "\\centering\n\\setlength{\\tabcolsep}{3.5pt}", 1)
        if name in FIT:
            text = text.replace("\\begin{tabular}", "\\resizebox{\\linewidth}{!}{\\begin{tabular}", 1)
            text = text.replace("\\end{tabular}", "\\end{tabular}}", 1)
        path.write_text(text, encoding="utf-8", newline="\n")


# ------------------------------------------------------------------------------------------------------ definitions
def definitions() -> None:
    lra = lambda a, k, g: a["point"][k]["lra"][g]  # noqa: E731
    sp_b = SP["bootstrap"]
    # numbers of the prose
    for key, nm in (("d2", "Dtwo"), ("d3", "Dthree"), ("d4", "Dfour"), ("keep", "Keep")):
        put(f"spLra{nm}Ccc", pc(lra(SP, key, C_)), f"experiments/definitions.json agencies.sp.point.{key}.lra[6]")
        put(f"spLra{nm}B", pc(lra(SP, key, B_)), f"experiments/definitions.json agencies.sp.point.{key}.lra[5]")
        put(f"spRw{nm}", pc(SP["point"][key]["rw"], 1), f"experiments/definitions.json agencies.sp.point.{key}.rw")
    for key, nm in (("d2", "Dtwo"), ("d4", "Dfour"), ("keep", "Keep")):
        put(f"fiLra{nm}Ccc", pc(lra(FI, key, C_)), f"experiments/definitions.json agencies.fitch.point.{key}.lra[6]")
        put(f"fiLra{nm}B", pc(lra(FI, key, B_)), f"experiments/definitions.json agencies.fitch.point.{key}.lra[5]")
        put(f"fiRw{nm}", pc(FI["point"][key]["rw"], 1), f"experiments/definitions.json agencies.fitch.point.{key}.rw")
    put("moLraDtwoCcc", pc(lra(MO, "d2", C_)), "experiments/definitions.json agencies.moodys.point.d2.lra[6]")
    put("moRwDtwo", pc(MO["point"]["d2"]["rw"], 1), "experiments/definitions.json agencies.moodys.point.d2.rw")
    for code, a, tag in (("sp", SP, "sp"), ("fitch", FI, "fi")):
        r = a["bootstrap"]["ratio_d4_over_d2"]
        put(f"{tag}RatioCcc", f(r[C_]["median"], 3), f"experiments/definitions.json agencies.{code}.bootstrap.ratio_d4_over_d2[6].median")
        put(f"{tag}PtRatioCcc", f(a["point"]["d4"]["lra"][C_] / a["point"]["d2"]["lra"][C_], 3), f"experiments/definitions.json agencies.{code}.point d4.lra[6] over d2.lra[6] (Equation gap-index on the averages)")
        put(f"{tag}PtRatioB", f(a["point"]["d4"]["lra"][B_] / a["point"]["d2"]["lra"][B_], 3), f"agencies.{code}.point d4.lra[5] over d2.lra[5]")
        put(f"{tag}RatioCccLo", f(r[C_]["lo"], 3), f"... ratio_d4_over_d2[6].lo")
        put(f"{tag}RatioCccHi", f(r[C_]["hi"], 3), f"... ratio_d4_over_d2[6].hi")
        put(f"{tag}RatioB", f(r[B_]["median"], 3), f"... ratio_d4_over_d2[5].median")
        put(f"{tag}RatioBLo", f(r[B_]["lo"], 3), "... ratio_d4_over_d2[5].lo")
        put(f"{tag}RatioBHi", f(r[B_]["hi"], 3), "... ratio_d4_over_d2[5].hi")
        d = a["bootstrap"]["rw_d2_minus_d4"]
        put(f"{tag}RwGap", pc(a["point"]["d2"]["rw"] - a["point"]["d4"]["rw"], 1), f"experiments/definitions.json agencies.{code}.point d2.rw minus d4.rw")
        put(f"{tag}RwGapLo", pc(d["lo"], 1), f"agencies.{code}.bootstrap.rw_d2_minus_d4.lo")
        put(f"{tag}RwGapHi", pc(d["hi"], 1), f"agencies.{code}.bootstrap.rw_d2_minus_d4.hi")
        put(f"{tag}RwGapShare", pc(a["bootstrap"]["share_rw_d2_above_d4"], 1), f"agencies.{code}.bootstrap.share_rw_d2_above_d4")
    sd = [a["bootstrap"]["second_seed"]["max_abs_diff_of_limits"] for a in (SP, FI)]
    put("bootSeedRatio", f(max(x["ratio_ccc"] for x in sd), 3), "experiments/definitions.json bootstrap.second_seed.max_abs_diff_of_limits.ratio_ccc, largest over S&P and Fitch")
    put("bootSeedRw", f(100 * max(x["rw_gap"] for x in sd), 1), "experiments/definitions.json bootstrap.second_seed.max_abs_diff_of_limits.rw_gap (points), largest over S&P and Fitch")
    put("bootB", f"{DEF['bootstrap_resamples']:,}".replace(",", "{,}"), "experiments/definitions.json bootstrap_resamples")
    below = SP["years_d4_below_d2"]
    put("spYearsBelowB", str(below[B_]["d4_below_d2"]), "agencies.sp.years_d4_below_d2[5].d4_below_d2")
    put("spYearsB", str(below[B_]["years"]), "agencies.sp.years_d4_below_d2[5].years")
    put("spYearsBelowCcc", str(below[C_]["d4_below_d2"]), "agencies.sp.years_d4_below_d2[6].d4_below_d2")
    put("spYearsCcc", str(below[C_]["years"]), "agencies.sp.years_d4_below_d2[6].years")
    put("fiYearsBelowCcc", str(FI["years_d4_below_d2"][C_]["d4_below_d2"]), "agencies.fitch.years_d4_below_d2[6].d4_below_d2")
    put("fiYearsCcc", str(FI["years_d4_below_d2"][C_]["years"]), "agencies.fitch.years_d4_below_d2[6].years")
    # the committed pooled counts and their Jeffreys intervals (S&P)
    for key, nm in (("d2", "Dtwo"), ("d4", "Dfour")):
        pc_ = SP["pooled_counts"][key]
        put(f"spPooledDef{nm}Ccc", f"{pc_['defaults'][C_]:,}".replace(",", "{,}"), f"experiments/definitions.json agencies.sp.pooled_counts.{key}.defaults[6]")
        put(f"spPooledN{nm}Ccc", f"{pc_['n'][C_]:,}".replace(",", "{,}"), f"agencies.sp.pooled_counts.{key}.n[6]")
        rate = pc_["defaults"][C_] / pc_["n"][C_]
        jl, ju = SP["jeffreys"][key]["lower"][C_], SP["jeffreys"][key]["upper"][C_]
        put(f"spPooledRate{nm}Ccc", pc(rate), f"defaults/n of agencies.sp.pooled_counts.{key}")
        put(f"spJeffLo{nm}Ccc", pc(jl), f"agencies.sp.jeffreys.{key}.lower[6]")
        put(f"spJeffHi{nm}Ccc", pc(ju), f"agencies.sp.jeffreys.{key}.upper[6]")
    for code, tag in (("sp", "sp"), ("moodys", "mo"), ("fitch", "fi")):
        gaps = [c["tab2_gap"] for c in figkit.doc(f"C04/{code}.json")["outputs"]["cohorts"] if c["tab2_gap"] is not None]
        put(f"{tag}GapYears", str(sum(1 for x in gaps if x > 0)), f"data/derived/C04/{code}.json outputs.cohorts[].tab2_gap > 0")
    # peaks of the CCC to C series of S&P
    labels = SP["labels"]
    for key, nm in (("d2", "Dtwo"), ("d4", "Dfour")):
        series = np.array([[np.nan if v is None else v for v in r] for r in SPDOC["pd"][key]], dtype=float)[:, C_]
        i = int(np.nanargmax(series))
        put(f"spPeakYearCcc{nm}", labels[i], f"data/derived/C04/sp.json outputs.pd.{key}[:, 6] argmax")
        put(f"spPeakRateCcc{nm}", pc(series[i], 1), f"data/derived/C04/sp.json outputs.pd.{key}[:, 6] max")
    put("spRatioCccInverse", f(lra(SP, "d2", C_) / lra(SP, "d4", C_), 1), "experiments/definitions.json agencies.sp.point d2.lra[6] over d4.lra[6]")
    put("agencyRatio",f(lra(SP, "d2", C_) / lra(MO, "d2", C_), 1), "experiments/definitions.json default-page LRA of CCC to C, S&P over Moody's")
    # the share of ratings withdrawn within the year in S&P's cohorts, against the generator's rate
    wd = np.array([c["withdrawn"] for c in SPDOC["cohorts"]], dtype=float)
    sz = np.array([c["size"] for c in SPDOC["cohorts"]], dtype=float)
    put("spWdShareAll", pc(wd.sum() / sz.sum(), 1), "data/derived/C04/sp.json outputs.cohorts[].withdrawn summed over size summed")
    put("spWdShareB", pc(wd[:, B_].sum() / sz[:, B_].sum(), 1), "same, grade B")
    put("spWdShareCcc", pc(wd[:, C_].sum() / sz[:, C_].sum(), 1), "same, grade CCC to C")
    put("spWdShareAaa", pc(wd[:, 0].sum() / sz[:, 0].sum(), 1), "same, grade AAA")
    # Fitch on the years in which the transition page's default column is populated
    put("fiPopYears", str(len(FIP["kept_years"])), "experiments/definitions.json fitch_populated_years.kept_years, number")
    put("fiPopDropped", f"{FIP['dropped_years'][0]} to {FIP['dropped_years'][-1]}", "experiments/definitions.json fitch_populated_years.dropped_years, first and last")
    put("fiPopSeed", str(FIP["seed"]), "experiments/definitions.json fitch_populated_years.seed")
    put("fiPopDroppedN", str(len(FIP["dropped_years"])), "fitch_populated_years.dropped_years, number")
    put("fiPopLraDtwoCcc", pc(FIP["point"]["d2"]["lra"][C_]), "fitch_populated_years.point.d2.lra[6]")
    put("fiPopLraDfourCcc", pc(FIP["point"]["d4"]["lra"][C_]), "fitch_populated_years.point.d4.lra[6]")
    put("fiPopPtRatioCcc", f(FIP["point"]["d4"]["lra"][C_] / FIP["point"]["d2"]["lra"][C_], 3), "fitch_populated_years.point d4.lra[6] over d2.lra[6]")
    put("fiPopRatioCccLo", f(FIP["ratio_d4_over_d2"][C_]["lo"], 3), "fitch_populated_years.ratio_d4_over_d2[6].lo")
    put("fiPopRatioCccHi", f(FIP["ratio_d4_over_d2"][C_]["hi"], 3), "fitch_populated_years.ratio_d4_over_d2[6].hi")
    put("fiPopRwDtwo", pc(FIP["point"]["d2"]["rw"], 1), "fitch_populated_years.point.d2.rw")
    put("fiPopRwDfour", pc(FIP["point"]["d4"]["rw"], 1), "fitch_populated_years.point.d4.rw")
    put("fiPopRwGap", pc(FIP["rw_gap_point"], 1), "fitch_populated_years.rw_gap_point")
    put("fiPopRwGapLo", pc(FIP["rw_d2_minus_d4"]["lo"], 1), "fitch_populated_years.rw_d2_minus_d4.lo")
    put("fiPopRwGapHi", pc(FIP["rw_d2_minus_d4"]["hi"], 1), "fitch_populated_years.rw_d2_minus_d4.hi")
    # tab:definitions (S&P): a ratio is printed for a grade with at least three years of nonzero rate under both pages
    pd_sp = {k: np.array([[np.nan if v is None else v for v in row] for row in SPDOC["pd"][k]], dtype=float) for k in ("d2", "d4")}
    nonzero = [min(int(np.sum(pd_sp["d2"][:, g] > 0)), int(np.sum(pd_sp["d4"][:, g] > 0))) for g in range(7)]
    put("spAaNonzeroYears", str(int(np.sum(pd_sp["d2"][:, 1] > 0))), "data/derived/C04/sp.json outputs.pd.d2[:, 1] > 0, count of years")
    rows = []
    for g in range(7):
        r = sp_b["ratio_d4_over_d2"][g]
        ratio = "--" if r.get("n", 0) == 0 or lra(SP, "d2", g) == 0 or nonzero[g] < 3 else (
            f"${r['median']:.2f}$ [{r['lo']:.2f}, {r['hi']:.2f}]" if r["n"] > 0 else "--")
        rows.append([GRADES[g]] + [m(100 * lra(SP, k, g), 3) for k in ("d2", "d3", "d4", "keep")] + [ratio])
    rows.append(["IRB risk weight (\\%)"] + [m(100 * SP["point"][k]["rw"], 1) for k in ("d2", "d3", "d4", "keep")]
                + [f"${100 * (SP['point']['d2']['rw'] - SP['point']['d4']['rw']):.1f}$ points"])
    write("definitions", ["Grade", "Default page", "Defaults page", "Transition page", "Withdrawals kept",
                          "Transition over default page"], rows,
          caption="Long-run average one-year PD (percent) of S\\&P's corporate ratings by grade under the four definitions "
                  "of a default over the 26 annual CEREP cohorts, and the IRB risk weight of the cohort mix; the last "
                  "column is the ratio of the transition page's average to the default page's with its 95\\% bootstrap "
                  "interval over cohort years (grades with fewer than three nonzero years carry no ratio).",
          label="tab:definitions", align="lrrrrr")
    # tab:rw
    rows = []
    for code, name, a in (("sp", "S\\&P", SP), ("moodys", "Moody's", MO), ("fitch", "Fitch", FI)):
        for key, label in (("d2", "default page"), ("d3", "defaults page"), ("d4", "transition page"), ("keep", "withdrawals kept")):
            if key not in a["bootstrap"]:
                continue
            b = a["bootstrap"][key]["rw"]
            gap = "--"
            if key == "d4" or key == "keep":
                d = np.array([a["point"]["d2"]["rw"] - a["point"][key]["rw"]])
                gap = f"${100 * d[0]:.1f}$"
            rows.append([name, label, m(100 * a["point"][key]["rw"], 1), f"[{100 * b['lo']:.1f}, {100 * b['hi']:.1f}]", gap])
    for key, label, nm in (("d2", "default page, 15 years", "rw_d2"), ("d4", "transition page, 15 years", "rw_d4")):
        b = FIP[nm]
        rows.append(["Fitch", label.replace("15", str(len(FIP["kept_years"]))), m(100 * FIP["point"][key]["rw"], 1),
                     f"[{100 * b['lo']:.1f}, {100 * b['hi']:.1f}]",
                     "--" if key == "d2" else f"${100 * FIP['rw_gap_point']:.1f}$"])
    write("rw", ["Agency", "Definition", "Risk weight (\\%)", "95\\% bootstrap interval", "Below default page (points)"], rows,
          caption="IRB risk weight of each agency's cohort mix (F-IRB corporate, LGD 45\\%, maturity 2.5 years, Basel III "
                  "function) when the one-year PD of every grade is read under each definition, with the percentile "
                  "interval of @BOOT@ resamples of the cohort years; Moody's transition page has no default category, and the last "
                  "two rows restrict Fitch to the years in which its transition page's default column is populated.",
          label="tab:rw", align="llrrr")
    # tab:data
    rows = []
    for code, name, a in (("sp", "S\\&P", SP), ("moodys", "Moody's", MO), ("fitch", "Fitch", FI)):
        doc = figkit.doc(f"C04/{code}.json")["outputs"]
        sizes = np.array([c["size"] for c in doc["cohorts"]], dtype=float)
        lab = a["labels"]
        pcs = a["pooled_counts"]
        d4 = pcs.get("d4")
        rows.append([name, str(a["cohorts"]), f"{lab[0]} to {lab[-1]}", str(int(round(sizes.sum(axis=1).mean()))),
                     f"{pcs['d2']['defaults'][C_]}/{pcs['d2']['n'][C_]}",
                     "none" if d4 is None else f"{d4['defaults'][C_]}/{d4['n'][C_]}"])
        put(f"{ 'sp' if code == 'sp' else 'mo' if code == 'moodys' else 'fi'}Cohorts", str(a["cohorts"]), f"experiments/definitions.json agencies.{code}.cohorts")
        put(f"{ 'sp' if code == 'sp' else 'mo' if code == 'moodys' else 'fi'}MeanCohort", str(int(round(sizes.sum(axis=1).mean()))), f"data/derived/C04/{code}.json outputs.cohorts[].size summed, mean")
    write("data", ["Agency", "Cohorts", "Years", "Mean cohort size", "CCC to C, default page (defaults/ratings)",
                   "CCC to C, transition page (defaults/ratings)"], rows,
          caption="The CEREP data behind the real-data comparison: three agencies' corporate long-term ratings, annual "
                  "cohorts, the mean number of ratings in a cohort and the pooled defaults over rated ratings of the "
                  "CCC to C grade under the default page and the transition page.",
          label="tab:data", align="lrlrrr")


# ------------------------------------------------------------------------------------------------------ withdrawals
def rung(k: float) -> dict:
    return [r for r in WD["rungs"] if r["k"] == k][0]


def withdrawals() -> None:
    n_reps = WD["rungs"][0]["reps"]
    put("repsNew", f"{n_reps:,}".replace(",", "{,}"), "experiments/withdrawals.json rungs[0].reps")
    put("minWd", f"{WD['seconds'] / 60:.0f}", "experiments/withdrawals.json seconds / 60")
    put("minTheory", f"{max(1, round(TH['seconds'] / 60))}", "experiments/theory.json seconds / 60 (at least one)")
    put("minExtra", f"{EXTRA['seconds'] / 60:.0f}", "experiments/extra.json seconds / 60")
    put("repsCommitted", "200", "data/derived/C04/withdrawals.json design.reps")
    put("repsTests", f"{ex('withdrawals')['tests'][0]['n_rep']:,}".replace(",", "{,}"), "experiments/withdrawals.json tests[0].n_rep")
    truth = np.array(WD["truth_pd"])
    put("truthB", pc(truth[B_]), "experiments/withdrawals.json truth_pd[5]")
    put("truthCcc", pc(truth[C_]), "experiments/withdrawals.json truth_pd[6]")
    put("rwTruth", pc(WD["rw_truth"], 1), "experiments/withdrawals.json rw_truth")
    put("reproMax", f"{max(r['max_abs_diff_of_means'] for r in WD['reproduction']):.0e}".replace("e-", "\\times10^{-").replace("0", "", 0) + "}", "experiments/withdrawals.json reproduction[].max_abs_diff_of_means")
    for k in (0.0, 1.0, 2.0, 3.0, 5.0, 9.0, 19.0):
        r = rung(k)
        tag = "k" + KT[int(k)]
        for arm in ("removed", "kept", "followed", "latent"):
            for g, gn in ((B_, "B"), (C_, "Ccc")):
                put(f"{arm}{gn}{tag}", f(100 * r[arm]["rel_bias"][g], 1), f"experiments/withdrawals.json rungs[k={k:g}].{arm}.rel_bias[{g}]")
                put(f"{arm}{gn}{tag}se", f(100 * r[arm]["rel_bias_mcse"][g], 1), f"rungs[k={k:g}].{arm}.rel_bias_mcse[{g}]")
            for g, gn in ((3, "Bbb"), (4, "Bb"), (B_, "B"), (C_, "Ccc")):
                put(f"{arm}Yone{gn}{tag}", f(100 * r[arm + "_y1"]["rel_bias"][g], 1), f"rungs[k={k:g}].{arm}_y1.rel_bias[{g}]")
                put(f"{arm}Yone{gn}{tag}se", f(100 * r[arm + "_y1"]["rel_bias_mcse"][g], 1), f"rungs[k={k:g}].{arm}_y1.rel_bias_mcse[{g}]")
            put(f"rw{arm}{tag}", f(100 * r["rw"][arm]["error"], 2), f"rungs[k={k:g}].rw.{arm}.error")
            put(f"rw{arm}{tag}se", f(100 * r["rw"][arm]["error_mcse"], 2), f"rungs[k={k:g}].rw.{arm}.error_mcse")
            put(f"rwAbs{arm}{tag}", f(abs(100 * r["rw"][arm]["error"]), 2), f"absolute value of rungs[k={k:g}].rw.{arm}.error")
    put("latentRwMaxZ", f(max(abs(r["rw"]["latent"]["error"] / r["rw"]["latent"]["error_mcse"]) for r in WD["rungs"]), 1),
        "experiments/withdrawals.json rungs[].rw.latent.error / error_mcse, largest absolute value")
    # the committed 200-repetition numbers the SDD quotes
    c9 = [r for r in COMMITTED_WD["rungs"] if r["value"] == 9.0][0]
    c0 = [r for r in COMMITTED_WD["rungs"] if r["value"] == 0.0][0]
    for arm in ("removed", "kept", "followed"):
        for r_, tag in ((c9, "kNine"), (c0, "kZero")):
            p = r_[f"pd_{arm}"]
            put(f"committed{arm}{tag}", f(100 * p["bias"][B_] / p["truth"][B_], 0), f"data/derived/C04/withdrawals.json rungs[value={r_['value']:g}].pd_{arm}.bias[5]/truth[5]")
    put("committedremovedkZeroPrec", f(100 * c0["pd_removed"]["bias"][B_] / c0["pd_removed"]["truth"][B_], 1), "data/derived/C04/withdrawals.json rungs[0].pd_removed.bias[5]/truth[5]")
    # pairing
    pc9 = rung(9.0)["paired_contrast_vs_latent"]["removed"]
    put("seRemovedPaired", f"{1e5 * pc9['se_paired'][B_]:.1f}", "experiments/withdrawals.json rungs[k=9].paired_contrast_vs_latent.removed.se_paired[5] (x1e5)")
    put("seRemovedUnpaired", f"{1e5 * pc9['se_unpaired'][B_]:.1f}", "... se_unpaired[5] (x1e5)")
    put("seRatio", f(pc9["se_unpaired"][B_] / pc9["se_paired"][B_], 2), "se_unpaired[5]/se_paired[5]")
    put("seRatioPct", f(100 * (1 - pc9["se_paired"][B_] / pc9["se_unpaired"][B_]), 0), "1 - se_paired/se_unpaired")
    # tests
    for t in WD["tests"]:
        tag = ("th" if "homogeneity" in t["test_id"] else "mr") + "k" + KT[int(t["rung"])]
        for lvl, ln in (("p<0.05", "five"), ("p<0.01", "one")):
            r_ = t["rates"][lvl]
            put(f"test{tag}{ln}", pc(r_["rate"], 1), f"experiments/withdrawals.json tests[{t['key']}].rates[{lvl}].rate")
            put(f"test{tag}{ln}lo", pc(r_["wilson_low"], 1), f"tests[{t['key']}].rates[{lvl}].wilson_low")
            put(f"test{tag}{ln}hi", pc(r_["wilson_high"], 1), f"tests[{t['key']}].rates[{lvl}].wilson_high")
    # zeros of the removed arm in the lowest grades
    r9 = rung(9.0)
    put("zeroAaaRemoved", pc(r9["removed"]["share_zero"][0], 0), "rungs[k=9].removed.share_zero[0]")
    put("zeroAaaDuration", pc([x for x in EXTRA["duration"] if x["k"] == 9.0][0]["duration"]["share_zero"][0], 0),
        "experiments/extra.json duration[k=9].duration.share_zero[0]")
    conjecture_and_extra()
    # tab:main-results
    rows = []
    for k in (0.0, 1.0, 2.0, 3.0, 5.0, 9.0, 19.0):
        r = rung(k)
        rows.append([f"{k:g}",
                     pm(100 * r["removed"]["rel_bias"][B_], 100 * r["removed"]["rel_bias_mcse"][B_]),
                     pm(100 * r["kept"]["rel_bias"][B_], 100 * r["kept"]["rel_bias_mcse"][B_]),
                     pm(100 * r["followed"]["rel_bias"][B_], 100 * r["followed"]["rel_bias_mcse"][B_]),
                     pm(100 * r["removed"]["rel_bias"][C_], 100 * r["removed"]["rel_bias_mcse"][C_]),
                     pm(100 * r["followed"]["rel_bias"][C_], 100 * r["followed"]["rel_bias_mcse"][C_]),
                     pm(100 * r["rw"]["removed"]["error"], 100 * r["rw"]["removed"]["error_mcse"], 2),
                     pm(100 * r["rw"]["followed"]["error"], 100 * r["rw"]["followed"]["error_mcse"], 2)])
    write("main-results",
          ["$k$", "B removed", "B kept", "B followed", "CCC-C removed", "CCC-C followed", "Risk weight, removed", "Risk weight, followed"],
          rows,
          caption="Relative bias (percent of the true one-year PD, mean $\\pm$ Monte Carlo standard error over @REPS@ "
                  "repetitions) of the pooled cohort estimator with withdrawals removed, kept in the denominator and "
                  "followed, for grades B and CCC to C, and the error of the IRB risk weight of S\\&P's cohort mix "
                  "(percentage points), against the informativeness $k$ of withdrawal in the year before default.",
          label="tab:main-results", align="rrrrrrrr")
    # tab:tests
    rows = []
    labels = {"rating.time_homogeneity": "time homogeneity", "rating.matrix_reference": "last year against $\\exp(Q)$",
              "rating.markov_order": "Markov order", "rating.momentum": "rating momentum",
              "rating.migration_ztests": "monotonicity z-tests"}
    for t in WD["tests"] + EXTRA["tests"]:
        r5, r1 = t["rates"]["p<0.05"], t["rates"]["p<0.01"]
        rows.append([labels[t["test_id"]], f"{t['rung']:g}",
                     f"${100 * r5['rate']:.1f}$ [{100 * r5['wilson_low']:.1f}, {100 * r5['wilson_high']:.1f}]",
                     f"${100 * r1['rate']:.1f}$ [{100 * r1['wilson_low']:.1f}, {100 * r1['wilson_high']:.1f}]"])
    order = list(labels.values())
    rows.sort(key=lambda r: (order.index(r[0]), float(r[1])))
    write("tests", ["Transition test", "$k$", "Rejections at 5\\% (Wilson 95\\%)", "Rejections at 1\\% (Wilson 95\\%)"], rows,
          caption="Rejection rates, in percent, of five transition tests of the engine on five annual matrices of the "
                  "withdrawal generator, over @REPSTESTS@ repetitions per $k$ with Wilson intervals, the same draws for "
                  "every test at a given $k$; the first two tests are the case's, the other three were run after them, "
                  "once their results were known. At the level of the test a rate near 5 or 1 means the test does not see "
                  "the withdrawals; the matrix weighted bandwidth, a descriptive metric with no rejection rule, is not run.",
          label="tab:tests", align="lrrr")


def first_order(arm: str, k: float) -> float:
    """Equation (first-order): the relative bias of the first cohort of a small-PD grade, removal or keeping."""
    theta = W_RATE * (1 + k)
    if arm == "removed":
        return math.exp(W_RATE) * (1 - math.exp(-theta)) / theta - 1
    return (1 - math.exp(-theta)) / theta - 1


def conjecture_and_extra() -> None:
    """The conjecture of the Theory section against the first-cohort measurements, the duration estimator, and the
    transition tests that the first version of the experiment did not run."""
    ks = (0.0, 1.0, 2.0, 3.0, 5.0, 9.0, 19.0)
    grades = ((3, "BBB"), (4, "BB"), (B_, "B"), (C_, "CCC-C"))
    zs: dict[tuple[int, str, float], float] = {}
    rows = []
    for g, gname in grades:
        for arm, aname in (("removed", "removal"), ("kept", "keeping")):
            cells = []
            for k in ks:
                r = rung(k)[arm + "_y1"]
                z = (r["rel_bias"][g] - first_order(arm, k)) / r["rel_bias_mcse"][g]
                zs[(g, arm, k)] = z
                zr = round(z, 1) + 0.0  # no negative zero
                cells.append(f"${zr:.1f}$" if abs(z) < 3 else f"$\\mathbf{{{zr:.1f}}}$")
            rows.append([gname, aname] + cells)
    write("conjecture", ["Grade", "Treatment"] + [f"$k={k:g}$" for k in ks], rows,
          caption="Standardised difference $z$ between the measured first-cohort relative bias and the first-order formula "
                  "of Equation~\\eqref{eq:first-order} (measured minus formula, over the Monte Carlo standard error of "
                  "@REPS@ repetitions) for the four lowest-rated grades, removal and keeping, at each $k$; a value above "
                  "three in absolute value, in bold, refutes the conjecture for that case.",
          label="tab:conjecture", align="llrrrrrrr")
    for k in (2.0, 5.0, 9.0, 19.0):
        put(f"zCccRemk{KT[int(k)]}", f(zs[(C_, "removed", k)], 2), f"z of CCC to C removal at k = {k:g}: (rungs[k].removed_y1.rel_bias[6] minus first-order) / rel_bias_mcse[6]")
    put("zBKeptkNineteen", f(zs[(B_, "kept", 19.0)], 2), "z of B keeping at k = 19, same construction")
    put("zCccKeptkTwo", f(zs[(C_, "kept", 2.0)], 2), "z of CCC to C keeping at k = 2, same construction")
    restricted = [abs(z) for (g, arm, k), z in zs.items() if g in (3, 4, B_) and k <= 9.0]
    put("conjMaxZRestricted", f(max(restricted), 2), "largest |z| over BBB, BB and B, removal and keeping, k up to 9")
    put("conjNRestricted", str(len(restricted)), "number of those comparisons")
    put("lambdaCcc", f(-math.log(1 - THIN["pd_1y"][C_]), 3), "experiments/thin.json pd_1y[6]: lambda = -log(1 - p) of CCC to C")
    put("lambdaB", f(-math.log(1 - THIN["pd_1y"][B_]), 4), "experiments/thin.json pd_1y[5]: lambda of B")
    # the two-state closed form against the multi-state measurement (pooled, k = 9)
    for gn, cn, g in (("B", "B", B_), ("Ccc", "CCC-C", C_)):
        r9_ = rung(9.0)
        for arm in ("removed", "followed"):
            closed = TH["chains"][cn]["rows"][[x["k"] for x in TH["chains"][cn]["rows"]].index(9.0)]["simulated"]["pooled"][arm]["rel_bias_closed_form"]
            meas, se = r9_[arm]["rel_bias"][g], r9_[arm]["rel_bias_mcse"][g]
            put(f"zTwoState{arm}{gn}", f(abs(closed - meas) / se, 1), f"|two-state closed form (theory.json chains.{cn}, k = 9, pooled, {arm}) minus rungs[k=9].{arm}.rel_bias[{g}]| over its MCSE")
    # the exact two-state closed form of Proposition 1 (first cohort) against the multi-state first-cohort measurement
    for cn, g, gn in (("CCC-C", C_, "Ccc"), ("B", B_, "B")):
        zz = []
        for r_ in TH["chains"][cn]["rows"]:
            rr = rung(r_["k"])
            for arm in ("removed", "kept"):
                cf = r_["simulated"]["first_year"][arm]["rel_bias_closed_form"]
                zz.append((rr[arm + "_y1"]["rel_bias"][g] - cf) / rr[arm + "_y1"]["rel_bias_mcse"][g])
        put(f"exactMaxZ{gn}", f(max(abs(z) for z in zz), 2), f"largest |z| of the exact closed form (theory.json chains.{cn}, first cohort) against the multi-state first-cohort measurement, removal and keeping, over the k of theory.json")
        put(f"exactNZ{gn}", str(len(zz)), f"number of those comparisons for {cn}")
    # the duration estimator
    dur = {x["k"]: x["duration"] for x in EXTRA["duration"]}
    for k in ks:
        tag = "k" + KT[int(k)]
        for g, gn in ((B_, "B"), (C_, "Ccc")):
            put(f"dur{gn}{tag}", f(100 * dur[k]["rel_bias"][g], 1), f"experiments/extra.json duration[k={k:g}].duration.rel_bias[{g}]")
            put(f"dur{gn}{tag}se", f(100 * dur[k]["rel_bias_mcse"][g], 1), f"duration[k={k:g}].duration.rel_bias_mcse[{g}]")
    rows = []
    for k in ks:
        r = rung(k)
        d = dur[k]
        rows.append([f"{k:g}",
                     pm(100 * r["removed"]["rel_bias"][B_], 100 * r["removed"]["rel_bias_mcse"][B_]),
                     pm(100 * r["kept"]["rel_bias"][B_], 100 * r["kept"]["rel_bias_mcse"][B_]),
                     pm(100 * r["followed"]["rel_bias"][B_], 100 * r["followed"]["rel_bias_mcse"][B_]),
                     pm(100 * d["rel_bias"][B_], 100 * d["rel_bias_mcse"][B_]),
                     pm(100 * r["removed"]["rel_bias"][C_], 100 * r["removed"]["rel_bias_mcse"][C_]),
                     pm(100 * r["kept"]["rel_bias"][C_], 100 * r["kept"]["rel_bias_mcse"][C_]),
                     pm(100 * d["rel_bias"][C_], 100 * d["rel_bias_mcse"][C_]),
                     m(100 * r["removed"]["share_zero"][0], 1), m(100 * d["share_zero"][0], 1)])
    write("duration", ["$k$", "B removed", "B kept", "B followed", "B duration", "CCC-C removed", "CCC-C kept", "CCC-C duration",
                       "AAA zero, removed (\\%)", "AAA zero, duration (\\%)"], rows,
          caption="The duration estimator, which treats a withdrawal as a censoring of the continuous-time path, against "
                  "the pooled cohort treatments (removed, kept, followed) on the same @REPS@ paired draws: relative bias (percent, mean $\\pm$ Monte "
                  "Carlo standard error) for grades B and CCC to C, and the share of repetitions in which the estimated PD "
                  "of AAA is exactly zero.",
          label="tab:duration", align="rrrrrrrrrr")
    # the further transition tests
    names = {"rating.markov_order": ("ord", "test of the Markov order"), "rating.momentum": ("mom", "momentum test"),
             "rating.migration_ztests": ("zt", "monotonicity z-tests")}
    for t in EXTRA["tests"]:
        tag, _ = names[t["test_id"]]
        kt = "k" + KT[int(t["rung"])]
        r5 = t["rates"]["p<0.05"]
        put(f"test{tag}{kt}five", pc(r5["rate"], 1), f"experiments/extra.json tests[{t['key']}].rates[p<0.05].rate")
        put(f"test{tag}{kt}fivelo", pc(r5["wilson_low"], 1), f"tests[{t['key']}].rates[p<0.05].wilson_low")
        put(f"test{tag}{kt}fivehi", pc(r5["wilson_high"], 1), f"tests[{t['key']}].rates[p<0.05].wilson_high")


# ------------------------------------------------------------------------------------------------------ theory
def theory() -> None:
    ch = TH["chains"]["B"]
    zs = [v["z"] for c in TH["chains"].values() for r in c["rows"] for s in r["simulated"].values() for v in s.values()]
    put("thMaxZ", f(max(abs(z) for z in zs), 2), "experiments/theory.json max |z| over all chains, rows, scopes and arms")
    put("thNcmp", str(len(zs)), "experiments/theory.json number of comparisons")
    # the comparisons that are distinct: on the first cohort the followed estimator and the no-withdrawal reference read the
    # same draws and have the same closed form, so each such pair counts once
    distinct: dict[str, dict] = {"first_year": {}, "pooled": {}}
    for cname, c in TH["chains"].items():
        for r in c["rows"]:
            for scope in distinct:
                for arm, v in r["simulated"][scope].items():
                    distinct[scope][(cname, r["k"], v["mean"], v["mcse"], v["closed_form"])] = abs(v["z"])
    put("thNcmpDistinct", str(sum(len(d) for d in distinct.values())), "experiments/theory.json comparisons after merging the pairs with equal simulated mean, standard error and closed form")
    put("thNcmpFirst", str(len(distinct["first_year"])), "same, first-cohort scope")
    put("thNcmpPooled", str(len(distinct["pooled"])), "same, pooled scope")
    put("thMaxZFirst", f(max(distinct["first_year"].values()), 2), "largest |z| over the first-cohort comparisons")
    put("thMaxZPooled", f(max(distinct["pooled"].values()), 2), "largest |z| over the pooled comparisons")
    put("thRepsB", str(ch["rows"][0]["reps"]), "experiments/theory.json chains.B.rows[0].reps")
    put("thObligB", f"{ch['rows'][0]['obligors']:,}".replace(",", "{,}"), "experiments/theory.json chains.B.rows[0].obligors")
    put("thObligC", f"{TH['chains']['CCC-C']['rows'][0]['obligors']:,}".replace(",", "{,}"), "experiments/theory.json chains.CCC-C.rows[0].obligors")
    put("thLambdaB", f(ch["lambda"], 5), "experiments/theory.json chains.B.lambda")
    for cname, cn in (("B", "B"), ("CCC-C", "Ccc")):
        for r in TH["chains"][cname]["rows"]:
            k = int(r["k"])
            for scope, sn in (("pooled", "Pool"), ("first_year", "Yone")):
                for arm in ("removed", "kept", "followed"):
                    v = r["simulated"][scope][arm]
                    put(f"th{cn}{arm}{sn}k{KT[k]}", f(100 * v["rel_bias_closed_form"], 1), f"experiments/theory.json chains.{cname}.rows[k={k}].simulated.{scope}.{arm}.rel_bias_closed_form")
    rows = []
    for r in ch["rows"]:
        for arm in ("removed", "kept", "followed"):
            a, b = r["simulated"]["pooled"][arm], r["simulated"]["first_year"][arm]
            rows.append([f"{r['k']:g}", arm,
                         m(100 * a["rel_bias_closed_form"], 1), pm(100 * a["rel_bias_sim"], 100 * a["rel_bias_mcse"]), m(a["z"], 2),
                         m(100 * b["rel_bias_closed_form"], 1), pm(100 * b["rel_bias_sim"], 100 * b["rel_bias_mcse"]), m(b["z"], 2)])
    write("theory", ["$k$", "Estimator", "Pooled: numerical evaluation", "Pooled: simulated", "$z$", "First year: closed form",
                     "First year: simulated", "$z$"], rows,
          caption="The closed forms of the Theory section (first cohort) and the numerical evaluation of the model's masses "
                  "(pooled over five cohorts) against the engine's simulation on a two-state chain with the PD "
                  "of grade B (relative bias of the one-year PD in percent; the simulated value is the mean $\\pm$ Monte "
                  "Carlo standard error of @THREPS@ paired draws of @THOBLIG@ obligors, $z$ the standardised difference).",
          label="tab:theory", align="rlrrrrrr")
    w = TH["withdrawal_rate"]
    for k in (0, 1, 2, 3, 5, 9, 19):
        theta = w * (1 + k)
        fo_rem = math.exp(w) * (1 - math.exp(-theta)) / theta - 1
        fo_kept = (1 - math.exp(-theta)) / theta - 1
        fo_fol = ((1 - math.exp(-k * w)) / (k * w) - 1) if k > 0 else 0.0
        put(f"foRemk{KT[k]}", f(100 * fo_rem, 1), f"first-order closed form e^w (1 - e^-theta)/theta - 1 with w = {w}, theta = w (1 + k), k = {k}")
        put(f"foKeptk{KT[k]}", f(100 * fo_kept, 1), f"first-order closed form (1 - e^-theta)/theta - 1, k = {k}")
        put(f"foFolk{KT[k]}", f(100 * fo_fol, 1), f"first-order closed form (1 - e^-kw)/(kw) - 1 for a later cohort, k = {k}")
    put("genSizes", ", ".join(f"{x:,}".replace(",", "{,}") for x in WD["obligors"]), "experiments/withdrawals.json obligors (cohort sizes of the generator, AAA to CCC to C)")
    put("wRate", f(100 * w, 0), "experiments/theory.json withdrawal_rate (percent)")
    put("limKeptKone", "100", "Proposition 1: the relative bias tends to -100 percent as k grows (experiments/theory.json limits_first_year)")


# ------------------------------------------------------------------------------------------------------ thin
def thin() -> None:
    thin_c = COMMITTED_THIN["rungs"]
    r50 = [r for r in thin_c if r["value"] == 50][0]
    r1000 = [r for r in thin_c if r["value"] == 1000][0]
    r200 = [r for r in thin_c if r["value"] == 200][0]
    put("waldAaaFifty", pc(r50["coverage"]["wald"][0], 2), "data/derived/C04/thin.json rungs[value=50].coverage.wald[0]")
    put("waldAaaFiftyFour", pc(r50["coverage"]["wald"][0], 4), "data/derived/C04/thin.json rungs[value=50].coverage.wald[0]")
    put("acAaaFifty", pc(r50["coverage"]["agresti_coull"][0], 2), "rungs[value=50].coverage.agresti_coull[0]")
    put("jeffAaaFifty", pc(r50["coverage"]["jeffreys"][0], 2), "rungs[value=50].coverage.jeffreys[0]")
    put("waldAaFifty", pc(r50["coverage"]["wald"][1], 1), "data/derived/C04/thin.json rungs[value=50].coverage.wald[1]")
    put("jeffAaaThou", pc(r1000["coverage"]["jeffreys"][0], 1), "rungs[value=1000].coverage.jeffreys[0]")
    put("jeffBbThou", pc(r1000["coverage"]["jeffreys"][4], 1), "rungs[value=1000].coverage.jeffreys[4]")
    put("waldAaaGen", pc(THIN["coverage_at_generator_sizes"]["wald"][0], 1), "experiments/thin.json coverage_at_generator_sizes.wald[0]")
    put("waldAaGen", pc(THIN["coverage_at_generator_sizes"]["wald"][1], 1), "coverage_at_generator_sizes.wald[1]")
    put("waldAGen", pc(THIN["coverage_at_generator_sizes"]["wald"][2], 0), "coverage_at_generator_sizes.wald[2]")
    put("waldBbbFifty", pc(r50["coverage"]["wald"][3], 1), "rungs[value=50].coverage.wald[3]")
    put("waldBFifty", pc(r50["coverage"]["wald"][B_], 1), "rungs[value=50].coverage.wald[5]")
    put("waldCccFifty", pc(r50["coverage"]["wald"][C_], 1), "rungs[value=50].coverage.wald[6]")
    put("jeffMinFifty", pc(min(r50["coverage"]["jeffreys"]), 1), "min of rungs[value=50].coverage.jeffreys")
    put("acMinFifty", pc(min(r50["coverage"]["agresti_coull"]), 1), "min of rungs[value=50].coverage.agresti_coull")
    put("waldAaaThou", pc(r1000["coverage"]["wald"][0], 1), "rungs[value=1000].coverage.wald[0]")
    put("waldAaTwoHundred", pc(r200["coverage"]["wald"][1], 2), "rungs[value=200].coverage.wald[1]")
    put("pAaa", pc(THIN["pd_1y"][0], 4), "experiments/thin.json pd_1y[0]")
    put("pB", pc(THIN["pd_1y"][B_], 3), "experiments/thin.json pd_1y[5]")
    put("pCcc", pc(THIN["pd_1y"][C_], 2), "experiments/thin.json pd_1y[6]")
    # the closed form against the enumeration at n = 50, AAA
    cf = [r for r in THIN["closed_forms"] if r["n"] == 50][0]
    put("cfAaaFifty", pc(cf["closed_form_wald"][0], 4), "experiments/thin.json closed_forms[n=50].closed_form_wald[0]")
    put("cfAaaFiftyDiff", f"{abs(cf['closed_form_wald'][0] - cf['enumerated_wald'][0]):.1e}".replace("e-", "\\times10^{-") + "}", "difference closed form minus enumerated, n=50, AAA")
    maxd = 0.0
    for r in THIN["closed_forms"]:
        if r["n"] <= 200:
            maxd = max(maxd, max(abs(a - b) for a, b in zip(r["closed_form_jeffreys_lower"][:3], r["enumerated_jeffreys"][:3])))
    put("cfJeffMaxDiff", f"{maxd:.1e}".replace("e-", "\\times10^{-") + "}", "max |(1-p)^n - enumerated Jeffreys coverage| over n <= 200 and the three lowest grades")
    lg = COMMITTED_THIN["rungs"][0]["length"]
    put("lenWaldAaaFifty", f"{1e4 * lg['wald'][0]:.1f}", "data/derived/C04/thin.json rungs[value=50].length.wald[0] (x1e4: basis points)")
    put("lenJeffAaaFifty", f"{1e4 * lg['jeffreys'][0]:.0f}", "rungs[value=50].length.jeffreys[0] (x1e4: basis points)")
    put("lenAcAaaFifty", f"{1e4 * lg['agresti_coull'][0]:.0f}", "rungs[value=50].length.agresti_coull[0] (x1e4: basis points)")
    put("pAaaBp", f"{1e4 * THIN['pd_1y'][0]:.2f}", "experiments/thin.json pd_1y[0] (x1e4: basis points)")
    put("pAaBp", f"{1e4 * THIN['pd_1y'][1]:.2f}", "experiments/thin.json pd_1y[1] (x1e4: basis points)")
    for gi, gn in ((0, "Aaa"), (1, "Aa"), (2, "A"), (3, "Bbb"), (4, "Bb"), (B_, "B"), (C_, "Ccc")):
        put(f"jeffThou{gn}", pc(r1000["coverage"]["jeffreys"][gi], 1), f"data/derived/C04/thin.json rungs[value=1000].coverage.jeffreys[{gi}]")
    # overlap
    ov = [r for r in thin_c if r["value"] == 1000][0]["overlap_jeffreys"]
    put("overlapAaaAaThou", f(ov[0], 2), "data/derived/C04/thin.json rungs[value=1000].overlap_jeffreys[0]")
    put("overlapBCccTwo", f([r for r in thin_c if r["value"] == 200][0]["overlap_jeffreys"][5], 2), "rungs[value=200].overlap_jeffreys[5]")
    # first grid n reaching 90%
    fg = THIN["first_grid_n_reaching"]["0.90"]["wald"]
    put("waldFirstBb", f"{fg[4]:,}".replace(",", "{,}") if fg[4] else "none", "experiments/thin.json first_grid_n_reaching[0.90].wald[4]")
    put("waldFirstCcc", f"{fg[6]:,}".replace(",", "{,}") if fg[6] else "none", "first_grid_n_reaching[0.90].wald[6]")
    put("waldFirstAaa", f"{fg[0]:,}".replace(",", "{,}") if fg[0] else "none within the grid", "first_grid_n_reaching[0.90].wald[0]")
    put("waldAaaFiftyK", pc(THIN["coverage_grid"]["wald"][-1][0], 1), "experiments/thin.json coverage_grid.wald[n=50000][0]")
    put("gridMax", f"{THIN['grid'][-1]:,}".replace(",", "{,}"), "experiments/thin.json grid[-1]")
    # tab:thin
    gs = THIN["generator_sizes"]
    rows = []
    for g in range(7):
        rows.append([GRADES[g], m(100 * THIN["pd_1y"][g], 3)]
                    + [m(100 * r["coverage"][mm][g], 1) for r in (r50, r1000) for mm in ("wald", "agresti_coull", "jeffreys")]
                    + [str(gs[g])] + [m(100 * THIN["coverage_at_generator_sizes"][mm][g], 1) for mm in ("wald", "jeffreys")])
    write("thin", ["Grade", "$p$ (\\%)", "Wald, 50", "A-C, 50", "Jeffreys, 50", "Wald, 1000", "A-C, 1000", "Jeffreys, 1000",
                   "Cohort size", "Wald, size", "Jeffreys, size"], rows,
          caption="Exact coverage (percent, nominal 95) of the Wald, Agresti-Coull and Jeffreys intervals at the true "
                  "one-year PD of each grade, by enumeration of the binomial count, with 50 and 1{,}000 obligors per grade "
                  "and at the cohort sizes of the S\\&P-like generator; the PDs are those of the C04 generator.",
          label="tab:thin", align="lrrrrrrrrrr")
    # fraction of reps needed for the simulation to resolve the AAA coverage at n = 50
    c = r50["coverage"]["wald"][0]
    need = (1 - c) / c / 0.1 ** 2
    put("repsNeeded", f"{int(round(need, -2)):,}".replace(",", "{,}"), "(1 - c)/(c * 0.1^2) with c = Wald coverage of AAA at n = 50 (relative standard error 10 percent)")


# ------------------------------------------------------------------------------------------------------ ablation
def ablation() -> None:
    r9, r0 = rung(9.0), rung(0.0)
    pc9 = r9["paired_contrast_vs_latent"]["removed"]
    rows = [
        ["Report the three pages' definitions side by side", "Report the transition page only",
         "S\\&P CCC to C, long-run PD (\\%)", f"${NUM['spLraDtwoCcc']['value']}$ and ${NUM['spLraDfourCcc']['value']}$", f"${NUM['spLraDfourCcc']['value']}$ (the gap is not seen)"],
        ["The same, carried to capital", "Report the transition page only",
         "S\\&P risk weight (\\%)", f"${NUM['spRwDtwo']['value']}$ and ${NUM['spRwDfour']['value']}$", f"${NUM['spRwDfour']['value']}$ (${NUM['spRwGap']['value']}$ points lower)"],
        ["Informativeness ladder of $k$", "Run $k=0$ only",
         "B, removed estimator, relative bias (\\%)", pm(100 * r9["removed"]["rel_bias"][B_], 100 * r9["removed"]["rel_bias_mcse"][B_]) + " at $k=9$",
         pm(100 * r0["removed"]["rel_bias"][B_], 100 * r0["removed"]["rel_bias_mcse"][B_]) + " at $k=0$ (opposite sign)"],
        ["Known-truth reference", "Compare the three treatments with one another",
         "B at $k=9$: bias of the least biased treatment (followed)",
         pm(100 * r9["followed"]["rel_bias"][B_], 100 * r9["followed"]["rel_bias_mcse"][B_]) + " against the truth",
         f"treatments span ${100 * (r9['followed']['rel_bias'][B_] - r9['kept']['rel_bias'][B_]):.1f}$ points; the offset of every one from the truth is unknown"],
        ["First-year cohort alone", "Pool five annual cohorts",
         "B, followed estimator, relative bias at $k=9$ (\\%)", pm(100 * r9["followed_y1"]["rel_bias"][B_], 100 * r9["followed_y1"]["rel_bias_mcse"][B_]) + " (first year)",
         pm(100 * r9["followed"]["rel_bias"][B_], 100 * r9["followed"]["rel_bias_mcse"][B_]) + " (pooled)"],
        ["Paired observed and latent draws", "Independent draws",
         "Standard error of removed minus latent, B, $k=9$ ($10^{-5}$)", f"${1e5 * pc9['se_paired'][B_]:.1f}$", f"${1e5 * pc9['se_unpaired'][B_]:.1f}$"],
        ["Exact enumeration of the coverage", "Estimate the coverage by simulation",
         "Repetitions to resolve the Wald coverage of AAA at $n=50$ to 10\\% relative error", "0 (exact)", f"${NUM['repsNeeded']['value']}$"],
        ["Matrix tests as the screen for withdrawals", "None needed (no screen)",
         "Rejection rate at 5\\% of the weaker test at $k=9$ (\\%)", f"${NUM['testmrkNinefive']['value']}$ and ${NUM['testthkNinefive']['value']}$",
         "the screen rejects at about its size, and the bias is not seen"],
    ]
    write("ablation", ["Component of the protocol", "Without it", "Quantity", "With the component", "Without the component"], rows,
          caption="Ablation of the proposed protocol: each row removes one component and reports, on the same data, "
                  "the quantity the component makes visible; the first two rows read the committed CEREP artifacts, the "
                  "next four the known-truth draws, the last two the exact enumeration and the matrix tests.",
          label="tab:ablation", align="p{3.2cm}p{2.6cm}p{3.2cm}p{2.4cm}p{3cm}")


# ------------------------------------------------------------------------------------------------------ outcomes
def outcomes() -> None:
    n = lambda key: NUM[key]["value"]  # noqa: E731
    rows = [
        ["H1", "On S\\&P's CEREP cohorts the transition page's long-run PD of CCC to C is below one half of the default page's "
               "(95\\% interval of the ratio below 0.5), and the risk weight of the cohort mix falls by more than 5 points",
         f"${n('spPtRatioCcc')}$ [{n('spRatioCccLo')}, {n('spRatioCccHi')}]; ${n('spRwGap')}$ points [{n('spRwGapLo')}, {n('spRwGapHi')}]",
         "held (the point values reproduce the committed ones; the bootstrap interval is new)"],
        ["H2", "With $k=9$ the pooled B PD with withdrawals removed and with withdrawals followed are each at least 10\\% below the truth "
               "(95\\% interval of the relative bias below $-10$\\%)",
         f"removed ${n('removedBkNine')}\\pm{n('removedBkNinese')}$, followed ${n('followedBkNine')}\\pm{n('followedBkNinese')}$",
         "held"],
        ["H3", "At $k=9$ neither the test of time homogeneity nor the test of the last matrix rejects more than 10\\% of the "
               "repetitions at the 5\\% level (upper Wilson bound below 10\\%). The statement behind it, that no transition test "
               "of the engine sees the withdrawals, is refuted by a rate whose lower bound is above 10\\% at any $k$ or any test",
         f"$k=9$: ${n('testthkNinefive')}$ [{n('testthkNinefivelo')}, {n('testthkNinefivehi')}] and ${n('testmrkNinefive')}$ "
         f"[{n('testmrkNinefivelo')}, {n('testmrkNinefivehi')}]; last matrix at $k=19$: ${n('testmrkNineteenfive')}$ "
         f"[{n('testmrkNineteenfivelo')}, {n('testmrkNineteenfivehi')}]; Markov order at $k=9$: ${n('testordkNinefive')}$ "
         f"[{n('testordkNinefivelo')}, {n('testordkNinefivehi')}]",
         "held for the two tests at $k=9$; the statement is not held, the last-matrix test sees the withdrawals at $k=19$"],
        ["H4", "With 50 obligors the Wald interval covers the PD of AAA in $0.33\\%$ of the samples (to two digits) and the Jeffreys "
               "and Agresti-Coull intervals cover at least 95\\% in every grade",
         f"Wald ${n('waldAaaFifty')}$\\%; minimum ${n('jeffMinFifty')}$\\% (Jeffreys), ${n('acMinFifty')}$\\% (A-C)",
         "reproduced (an exact enumeration of values already committed; it could not fail)"],
        ["H5a", "The closed forms of Proposition~\\ref{prop:first-year} agree with the simulated means of the first cohort within three "
                "Monte Carlo standard errors",
         f"largest $|z|={n('thMaxZFirst')}$ over {n('thNcmpFirst')} distinct comparisons", "held"],
        ["H5b", "The numerical evaluation of the model's masses over five cohorts, with the horizon truncation, agrees with the "
                "pooled simulated means within three Monte Carlo standard errors",
         f"largest $|z|={n('thMaxZPooled')}$ over {n('thNcmpPooled')} distinct comparisons", "held"],
        ["Conj.", "The first-order formula of Equation~\\eqref{eq:first-order} describes the first-cohort bias of a grade with a small "
                  "PD to within three standard errors",
         f"CCC to C, removal: $z={n('zCccRemkTwo')}$, ${n('zCccRemkFive')}$, ${n('zCccRemkNineteen')}$ at $k=2,5,19$; B, keeping, "
         f"$k=19$: $z={n('zBKeptkNineteen')}$",
         "refuted for CCC to C and, at $k=19$, for keeping in B"],
    ]
    write("outcomes", ["Id", "Prediction", "Result", "Outcome"], rows,
          caption="The predictions of the experimental design and the outcome of each: the four statements of the "
                  "measurements on the default definition, informative withdrawals and thin grades, the closed forms "
                  "of the Theory section, and the conjecture of that section, with the quantity that decides each.",
          label="tab:outcomes", align="lp{5.2cm}p{4.2cm}p{2.6cm}", small=True)


def main() -> None:
    definitions()
    withdrawals()
    theory()
    thin()
    ablation()
    outcomes()
    lines = ["% Generated by tables/make_tables.py: the numbers the prose quotes. Do not edit."]
    for name, v in NUM.items():
        lines.append(f"\\newcommand{{\\{name}}}{{{v['value']}}}")
    (HERE / "numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    (HERE / "numbers.json").write_text(json.dumps(NUM, indent=1), encoding="utf-8", newline="\n")
    print(len(NUM), "macros")


if __name__ == "__main__":
    main()
