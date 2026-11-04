"""Tables and numbers of the ratings chapter of the technical report (``sections/07-ratings.tex``).

Every number of the chapter's results comes from here: the committed artifacts of cases C02, C04 and C05 under
``data/derived`` are read, the credit-cycle factors are recomputed with the engine's closed form, and the tables are
written as booktabs files ``tables/ratings-*.tex`` through ``figkit.table``. The numbers quoted in the prose are
written to ``tables/ratings-numbers.tex`` as ``\\newcommand`` macros (names made of letters only), so a new engine
release or a new bake changes the text at the next run instead of leaving a retyped value behind.

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/tables/make_ratings.py

The figure script ``figures/make_ratings.py`` imports ``compute`` from this file.
"""
from __future__ import annotations

import pathlib
import sys
from typing import Any

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

AGENCIES = (("sp", "S&P"), ("moodys", "Moody's"), ("fitch", "Fitch"))
GRADES = ("AAA", "AA", "A", "BBB", "BB", "B", "CCC-C")
ZGRADES = (4, 5, 6)  # BB, B, CCC-C: the grades with a default in most cohorts
LDP_GRADES = ("A", "B", "C")
APPROACHES = (
    ("A1-idp", "Invariant default profile"),
    ("A2-iar", "Invariant accuracy ratio"),
    ("A3-spd", "Scaled PDs"),
    ("A4-slr", "Scaled likelihood ratio"),
    ("B1-ilr", "Invariant likelihood ratio, PD known"),
    ("C1-ipc", "Invariant PD curve (2009 curve unchanged)"),
    ("C2-ls", "Conditional profiles, least squares"),
    ("C3-chi2", "Conditional profiles, least chi-square"),
    ("C4-ilr", "Invariant likelihood ratio, profile known"),
)
YT = {2010: "ya", 2011: "yb"}
AS = {"A1-idp": "idp", "A2-iar": "iar", "A3-spd": "spd", "A4-slr": "slr", "B1-ilr": "ilrb", "C1-ipc": "ipc",
      "C2-ls": "ls", "C3-chi2": "chi", "C4-ilr": "ilrc"}
GT = {0.5: "a", 0.75: "b", 0.9: "c", 0.95: "d", 0.99: "e", 0.999: "f"}
HT = {"h1": "one", "h2": "two", "h3": "three", "h4": "four", "h5": "five", "pooled": "pooled"}
CS = {"P2a-l1": "logit", "P2b-pltr": "pltr", "P3-ebm": "ebm", "P4-lightgbm": "lgbm", "P4-xgboost": "xgb"}
ESTIMATORS = (("cohort", "Cohort"), ("duration", "Duration"), ("em", "EM"), ("diagonal", "Diagonal repair"),
              ("weighted", "Weighted repair"), ("jlt", "Jarrow, Lando, Turnbull"))
HORIZONS = ("h1", "h2", "h3", "h4", "h5", "pooled")
CHALLENGERS = (("P2a-l1", "L1 logistic"), ("P2b-pltr", "PLTR"), ("P3-ebm", "EBM"), ("P4-lightgbm", "LightGBM"),
               ("P4-xgboost", "XGBoost"))
#: Tolerances of the engine's reproduction of Tasche (2013), as ``golden.tolerances`` of the C05 artifact states them:
#: table 5 one unit of the third decimal; tables 6 and 7 one unit of the fourth decimal plus 0.01 percent of the value.
TOL = {"table5": (1e-3, 0.0), "table6": (1e-4, 1e-4), "table7": (1e-4, 1e-4)}


def name(*parts: Any) -> str:
    """A macro name made of letters only (LaTeX control words take no digits): digits spell out, other signs drop."""
    spell = {"0": "Zero", "1": "One", "2": "Two", "3": "Three", "4": "Four", "5": "Five", "6": "Six", "7": "Seven",
             "8": "Eight", "9": "Nine"}
    words = []
    for part in parts:
        out = []
        for ch in str(part):
            if ch in spell:
                out.append(spell[ch])
            elif ch.isalpha():
                out.append(ch)
        word = "".join(out)
        words.append(word[:1].upper() + word[1:])
    return "rtg" + "".join(words)


def pct(x: float | None, d: int = 2) -> str:
    return "--" if x is None else f"{100 * x:.{d}f}"


def pm(x: float, e: float, d: int = 2) -> str:
    return f"${100 * x:.{d}f}\\pm{100 * e:.{d}f}$"


def _gh_mean(ttc: float, rho: float, n: int = 120) -> float:
    """The mean of the conditional PD over the systematic factor by Gauss-Hermite quadrature (probabilists' nodes)."""
    from riskvalidation.engines import vasicek

    x, w = np.polynomial.hermite_e.hermegauss(n)
    return float(np.sum(w * np.asarray(vasicek.conditional_pd(ttc, rho, x))) / np.sqrt(2 * np.pi))


def compute() -> dict[str, Any]:
    """Read the artifacts and return every derived quantity of the chapter (tables, figures and prose numbers)."""
    from riskvalidation.engines import vasicek
    from riskvalidation.regulatory import irb

    R: dict[str, Any] = {"num": {}}
    num = R["num"]

    # ---- C04, the three agencies: long-run PD by grade, the implied credit-cycle factor, the generator repairs
    agencies: dict[str, Any] = {}
    for aid, _ in AGENCIES:
        d = figkit.doc(f"C04/{aid}.json")
        o = d["outputs"]
        labels = [c["label"] for c in o["cohorts"]]
        d2 = np.array([[np.nan if v is None else v for v in row] for row in o["pd"]["d2"]], dtype=float)
        lra = o["lra"]["d2"]
        rec: dict[str, Any] = {"labels": labels, "d2": d2, "lra": lra, "out": o, "version": d["provenance"]["riskvalidation_version"]}
        z: dict[int, Any] = {}
        for g in ZGRADES:
            ttc = float(lra["rate"][g])
            rho = float(irb.correlation("corporate", ttc))
            rate = d2[:, g]
            ok = np.isfinite(rate) & (rate > 0)
            zs = np.full(len(rate), np.nan)
            zs[ok] = vasicek.implied_factor(rate[ok], ttc, rho)
            z[g] = {"ttc": ttc, "rho": rho, "z": zs, "n": int(ok.sum()), "cohorts": len(rate),
                    "mean": float(np.nanmean(zs)), "sd": float(np.nanstd(zs, ddof=1)),
                    "pit_mean": _gh_mean(ttc, rho)}
            z[g]["pit_error"] = abs(z[g]["pit_mean"] - ttc) / ttc
        rec["z"] = z
        agencies[aid] = rec
    R["agencies"] = agencies
    sp = agencies["sp"]
    zb, zc, zbb = sp["z"][5], sp["z"][6], sp["z"][4]

    def corr(a: np.ndarray, b: np.ndarray) -> float:
        m = np.isfinite(a) & np.isfinite(b)
        return float(np.corrcoef(a[m], b[m])[0, 1])

    R["z_corr"] = {"bb_b": corr(zbb["z"], zb["z"]), "b_ccc": corr(zb["z"], zc["z"]), "bb_ccc": corr(zbb["z"], zc["z"])}
    num[name("zcorr", "bb", "b")] = f"{R['z_corr']['bb_b']:.2f}"
    num[name("zcorr", "b", "ccc")] = f"{R['z_corr']['b_ccc']:.2f}"
    num[name("zcorr", "bb", "ccc")] = f"{R['z_corr']['bb_ccc']:.2f}"
    for aid, rec in agencies.items():
        for g in ZGRADES:
            zz = rec["z"][g]
            num[name("z", aid, GRADES[g], "mean")] = f"{zz['mean']:.2f}"
            num[name("z", aid, GRADES[g], "sd")] = f"{zz['sd']:.2f}"
            num[name("z", aid, GRADES[g], "n")] = str(zz["n"])
            num[name("z", aid, GRADES[g], "rho")] = f"{zz['rho']:.3f}"
        num[name("cohorts", aid)] = str(len(rec["labels"]))
        for gi, g in enumerate(GRADES):
            num[name("lra", aid, g)] = pct(rec["lra"]["rate"][gi], 3)
            num[name("lraTwo", aid, g)] = pct(rec["lra"]["rate"][gi], 2)
    pit_max = max(rec["z"][g]["pit_error"] for rec in agencies.values() for g in ZGRADES)
    R["pit_max_error"] = pit_max
    num[name("pit", "max", "error")] = f"{pit_max:.1e}"
    lo_year = lambda zz: sp["labels"][int(np.nanargmin(zz["z"]))]  # noqa: E731
    hi_year = lambda zz: sp["labels"][int(np.nanargmax(zz["z"]))]  # noqa: E731
    for g in ZGRADES:
        zz = sp["z"][g]
        num[name("z", "sp", GRADES[g], "min")] = f"{np.nanmin(zz['z']):.2f}"
        num[name("z", "sp", GRADES[g], "minyear")] = lo_year(zz)
        num[name("z", "sp", GRADES[g], "max")] = f"{np.nanmax(zz['z']):.2f}"
        num[name("z", "sp", GRADES[g], "maxyear")] = hi_year(zz)
    # the grades' PIT PD at a two-standard-deviation bad year, as the model maps it
    for g in ZGRADES:
        zz = sp["z"][g]
        pit_bad = float(vasicek.conditional_pd(zz["ttc"], zz["rho"], -2.0))
        pit_good = float(vasicek.conditional_pd(zz["ttc"], zz["rho"], 2.0))
        num[name("pit", "bad", GRADES[g])] = pct(pit_bad)
        num[name("pit", "good", GRADES[g])] = pct(pit_good, 3)
    # the definition of default moves the long-run PD (D4 over D2), S&P
    gap = sp["out"]["definition_gap"]["d4_over_d2"]
    for gi, g in enumerate(GRADES):
        if gap[gi] is not None:
            num[name("gap", "dfour", g)] = f"{gap[gi]:.2f}"
    for aid, rec in agencies.items():
        gens = rec["out"]["generators"]
        for k in ("em", "diagonal", "weighted", "jlt"):
            num[name("l1", aid, k)] = f"{gens[k]['l1']:.4f}"
        num[name("emit", aid)] = str(gens["em"]["iterations"])
        emb = rec["out"]["embedding"]
        num[name("unreach", aid)] = str(len(emb["theorem3"]["c"]))
        num[name("sconv", aid)] = f"{emb['S']:.3f}"
        num[name("det", aid)] = f"{emb['det']:.3f}"
        num[name("proddiag", aid)] = f"{emb['prod_diagonal']:.3f}"
    g_sp = sp["out"]["generators"]
    for k in ("em", "diagonal", "weighted", "jlt"):
        num[name("pifive", k)] = pct(g_sp[k]["pd_5y"][6])
        num[name("pione", k)] = pct(g_sp[k]["pd_1y"][6], 3)
    num[name("pifive", "cohort")] = pct(g_sp["cohort_power"]["pd_5y"][6])
    num[name("sp", "homog", "stat")] = f"{sp['out']['homogeneity']['annual']['statistic']:.0f}"
    num[name("sp", "homog", "dof")] = str(sp["out"]["homogeneity"]["annual"]["dof"])

    # ---- C04, the known-truth Markov family: the estimators against the generator's truth
    mk = figkit.doc("C04/markov.json")["outputs"]
    rung = mk["rungs"][0]
    est = rung["estimators"]
    R["markov"] = {"est": est, "reps": mk["design"]["reps"], "years": mk["design"]["years"],
                   "obligor_years": rung["obligor_years"]}
    num[name("mk", "reps")] = str(mk["design"]["reps"])
    num[name("mk", "snap")] = str(mk["design"]["years"])
    truth = est["cohort"]["truth"]
    for gi in (0, 1, 2, 6):
        num[name("mk", "truth", GRADES[gi])] = f"{1e4 * truth[gi]:.2f}"
        num[name("mk", "zero", GRADES[gi])] = pct(est["cohort"]["zero"][gi]["rate"], 0)
        num[name("mk", "oy", GRADES[gi])] = f"{rung['obligor_years'][gi]:.0f}"
    for k, _ in ESTIMATORS:
        for gi in (0, 1, 5, 6):
            num[name("mk", k, GRADES[gi], "rmse")] = f"{1e4 * est[k]['rmse'][gi]:.1f}"
            num[name("mk", k, GRADES[gi], "se")] = f"{1e4 * est[k]['empirical_se'][gi]:.1f}"
    num[name("mk", "emconv")] = pct(rung["em"]["converged"]["rate"], 0)
    num[name("mk", "emiter")] = f"{rung['em']['iterations_mean']:.1f}"

    # ---- C04, the published answers (Israel et al., Schuermann and Hanson, Engelmann)
    pub = figkit.doc("C04/published.json")["outputs"]
    R["pub"] = pub
    irw_rows = pub["irw"]["rows"]
    num[name("irw", "agree")] = str(sum(1 for r in irw_rows if r["agrees"]))
    num[name("irw", "total")] = str(len(irw_rows))
    sr_rows = pub["sr190"]["rows"]
    num[name("sr", "agree")] = str(sum(1 for r in sr_rows if r["agrees"]))
    num[name("sr", "total")] = str(len(sr_rows))
    num[name("sr", "defaults")] = str(pub["sr190"]["defaults"])
    num[name("sr", "n")] = str(pub["sr190"]["n"])
    eng = pub["engelmann"]
    num[name("eng", "ttc")] = pct(eng["ttc_pd"]["recomputed"], 3)
    for i, pf in enumerate(eng["portfolios"]):
        path = np.array(pf["pd_path"])
        num[name("eng", "start", "abcd"[i])] = pct(path[0], 3)
        num[name("eng", "min", "abcd"[i])] = pct(path.min(), 3)
        num[name("eng", "max", "abcd"[i])] = pct(path.max(), 3)
        num[name("eng", "last", "abcd"[i])] = pct(path[-1], 3)
        num[name("eng", "argmax", "abcd"[i])] = str(int(path.argmax()))
        num[name("eng", "argmin", "abcd"[i])] = str(int(path.argmin()))
    num[name("eng", "years")] = str(len(eng["portfolios"][0]["pd_path"]))

    # ---- C05, the S&P calibration to 2010 and 2011 (Tasche 2013) and the low-default example (Pluto and Tasche)
    cal: dict[int, Any] = {}
    for y in (2010, 2011):
        d = figkit.doc(f"C05/sp-{y}.json")
        o = d["outputs"]
        pv = {t["model_id"]: t for t in d["tests"] if t["test_id"] == "pd.default_profile"}
        cal[y] = {"o": o, "tests": pv, "impact": d["impact"], "version": d["provenance"]["riskvalidation_version"]}
        for aid, _ in APPROACHES:
            a = o["approaches"][aid]
            num[name("cal", YT[y], AS[aid], "pd")] = pct(a["pd"], 3)
            num[name("cal", YT[y], AS[aid], "ar")] = pct(a["accuracy_ratio"], 1)
            num[name("cal", YT[y], AS[aid], "p")] = pct(pv[aid]["p_value"], 1)
            num[name("cal", YT[y], AS[aid], "rw")] = pct(d["impact"][f"rw_{aid}"]["value"], 1)
            num[name("cal", YT[y], AS[aid], "stat")] = f"{pv[aid]['statistic']:.1f}"
        num[name("cal", YT[y], "obs")] = pct(o["pd1"], 3)
        num[name("cal", YT[y], "ar", "obs")] = pct(o["ar1"], 1)
        num[name("cal", YT[y], "n")] = f"{o['n_obligors']:,}".replace(",", "\\,")
        num[name("cal", YT[y], "d")] = str(o["n_defaults"])
        num[name("cal", YT[y], "spread")] = pct(d["impact"]["rw_spread_case1"]["value"], 1)
        num[name("cal", YT[y], "stale")] = pct(d["impact"]["rw_stale_vs_slr"]["value"], 1)
        num[name("cal", YT[y], "cpd")] = f"{o['approaches']['A3-spd']['constants']['c_pd']:.4f}"
        c = o["approaches"]["A4-slr"]["constants"]
        num[name("cal", YT[y], "clr")] = f"{c['c_lr']:.4f}"
        num[name("cal", YT[y], "lrlo")] = f"{c['bracket_low']:.4f}"
        num[name("cal", YT[y], "lrhi")] = f"{c['bracket_high']:.4f}"
        num[name("cal", YT[y], "mcse", "max")] = pct(max(t["extras"]["mc_standard_error"] for t in pv.values()), 2)
    q = cal[2010]["o"]["qmm0"]
    num[name("qmm", "alpha")] = f"{q['alpha']:.4f}"
    num[name("qmm", "beta")] = f"{q['beta']:.4f}"
    num[name("qmm", "alpha", "start")] = f"{q['start'][0]:.3f}"
    num[name("qmm", "beta", "start")] = f"{q['start'][1]:.3f}"
    num[name("qmm", "pd")] = pct(cal[2010]["o"]["pd0"], 3)
    num[name("qmm", "ar")] = pct(cal[2010]["o"]["ar0"], 2)
    num[name("grades", "tasche")] = str(len(cal[2010]["o"]["grades"]))
    R["cal"] = cal
    # the case-3 profile tests (an output of the case, not a registered test)
    for y in (2010, 2011):
        for aid, t in cal[y]["o"]["case3_profile_tests"].items():
            num[name("c3", YT[y], AS[aid], "p")] = f"{t['p_value']:.4f}"

    # golden reproductions: Tasche (2013) tables 5 to 9, counted against the engine's tolerances
    gold: dict[str, Any] = {}
    cells5 = cal[2010]["o"]["golden"]["table5"]
    cells6 = cal[2010]["o"]["golden"]["table6"]
    cells7 = [c for lst in cal[2010]["o"]["golden"]["table7"].values() for c in lst]
    cells7 += [c for lst in cal[2011]["o"]["golden"]["table7"].values() for c in lst]

    def within(cells: list[dict[str, Any]], key: str) -> tuple[int, int, int, float]:
        a, b = TOL[key]
        ident = sum(1 for c in cells if abs(c["gap"]) < 1e-12)
        ok = sum(1 for c in cells if abs(c["gap"]) <= a + b * abs(c["printed"]) + 1e-12)
        return len(cells), ident, ok, max(abs(c["gap"]) for c in cells)

    gold["t5"], gold["t6"], gold["t7"] = within(cells5, "table5"), within(cells6, "table6"), within(cells7, "table7")
    t8 = [r for y in (2010, 2011) for r in cal[y]["o"]["golden"]["table8"]]
    gold["t8"] = (len(t8), max(abs(r["ours_pct"] - r["printed_pct"]) for r in t8))
    t7p = [r for y in (2010, 2011) for r in cal[y]["o"]["golden"]["table7_p_values"]]
    gold["t7p"] = (len(t7p), max(abs(r["ours_pct"] - r["printed_pct"]) for r in t7p),
                   max(r["mc_se_pct"] for r in t7p))
    R["gold_tasche"] = gold
    for key, label in (("t5", "five"), ("t6", "six"), ("t7", "seven")):
        n, ident, ok, mx = gold[key]
        num[name("gold", label, "n")] = str(n)
        num[name("gold", label, "ident")] = str(ident)
        num[name("gold", label, "ok")] = str(ok)
        num[name("gold", label, "max")] = f"{mx:.4f}"
    num[name("gold", "eight", "n")] = str(gold["t8"][0])
    num[name("gold", "eight", "max")] = f"{gold['t8'][1]:.3f}"
    num[name("gold", "sevenp", "n")] = str(gold["t7p"][0])
    num[name("gold", "sevenp", "max")] = f"{gold['t7p'][1]:.2f}"

    ldp = figkit.doc("C05/ldp-published.json")
    lo = ldp["outputs"]
    R["ldp"] = lo
    cells = lo["golden"]["cells"]
    byt: dict[int, list[dict[str, Any]]] = {}
    for c in cells:
        byt.setdefault(c["table"], []).append(c)
    R["ldp_tables"] = byt
    num[name("pt", "cells")] = str(len(cells))
    num[name("pt", "ident")] = str(sum(1 for c in cells if abs(c["gap"]) < 1e-9))
    num[name("pt", "maxgap")] = f"{max(abs(c['gap']) for c in cells):.2f}"
    ind, cor = lo["bounds"]["independent"], lo["bounds"]["correlated"]
    gam = lo["gammas"]
    for gi, g in enumerate(gam):
        for ai, a in enumerate(LDP_GRADES):
            num[name("ldp", "ind", GT[g], a)] = pct(ind[gi][ai], 2)
            num[name("ldp", "cor", GT[g], a)] = pct(cor[gi][ai], 2)
    su = lo["bounds"]["scaled_upper_bound"]
    for gi, g in enumerate(gam):
        num[name("ldp", "k", GT[g])] = f"{su[gi]['k']:.2f}"
    num[name("ldp", "expert", "A")] = pct(lo["expert_pd"][0], 2)
    num[name("ldp", "expert", "B")] = pct(lo["expert_pd"][1], 2)
    num[name("ldp", "expert", "C")] = pct(lo["expert_pd"][2], 2)
    num[name("ldp", "rho")] = f"{100 * lo['rho']:.0f}"
    for k, v in ldp["impact"].items():
        num[name("ldp", k)] = pct(v["value"], 1)
    sim = figkit.doc("C05/ldp-sim-0.json")["outputs"]
    kt = sim["known_truth"]
    R["sim"] = sim
    num[name("sim", "years")] = f"{kt['years']:,}".replace(",", "\\,")
    for grade in LDP_GRADES:
        for kind in ("independent", "correlated", "scaled"):
            for row in kt["coverage"][kind][grade]:
                num[name("cov", kind, grade, GT[row["gamma"]])] = pct(row["coverage"], 1)
        num[name("sim", "true", grade)] = pct(sim["true_pd"][LDP_GRADES.index(grade)], 2)
    num[name("sim", "overdisp", "model")] = f"{kt['overdispersion']['variance_model']:.2f}"
    num[name("sim", "overdisp", "sim")] = f"{kt['overdispersion']['variance_simulated']:.2f}"
    num[name("sim", "overdisp", "ind")] = f"{kt['overdispersion']['variance_independent']:.2f}"
    num[name("sim", "rho", "hat")] = f"{100 * kt['overdispersion']['rho_moment_estimate']:.1f}"
    r1 = kt["coverage"]["independent"]["C"][2]
    num[name("sim", "ratio", "med")] = f"{r1['ratio_median']:.1f}"
    for variant in ("ldp-sim-0", "ldp-sim-1", "ldp-sim-3"):
        s = figkit.doc(f"C05/{variant}.json")["outputs"]
        num[name("simdef", variant)] = str(sum(s["defaults"]))
    sim1 = figkit.doc("C05/ldp-sim-1.json")["outputs"]["known_truth"]
    R["power"] = sim1["tests"]
    for who in ("true", "expert"):
        for k, v in sim1["tests"][who].items():
            num[name("pow", who, k)] = pct(v["reject_5"], 1)

    # ---- C02, the master scale as the rule that counts a grade disagreement
    c02: dict[str, Any] = {}
    for h in HORIZONS:
        d = figkit.doc(f"C02/{h}.json")
        c02[h] = {"counts": d["outputs"]["counts"], "challenger": {c["challenger"].split("-", 1)[1]: c for c in d["outputs"]["challenger"]},
                  "version": d["provenance"]["riskvalidation_version"]}
    R["c02"] = c02
    num[name("cz", "rows")] = f"{c02['pooled']['counts']['rows']:,}".replace(",", "\\,")
    num[name("cz", "events")] = f"{c02['pooled']['counts']['events']:,}".replace(",", "\\,")
    for h in HORIZONS:
        for cid, _ in CHALLENGERS:
            num[name("cz", HT[h], CS[cid])] = pct(c02[h]["challenger"][cid]["grade_disagreement_share"], 1)
    num[name("cz", "min")] = pct(min(c02[h]["challenger"][c]["grade_disagreement_share"] for h in HORIZONS for c, _ in CHALLENGERS), 1)
    num[name("cz", "max")] = pct(max(c02[h]["challenger"][c]["grade_disagreement_share"] for h in HORIZONS for c, _ in CHALLENGERS), 1)
    num[name("cz", "l1", "max")] = pct(max(c02[h]["challenger"]["P2a-l1"]["grade_disagreement_share"] for h in HORIZONS), 1)
    num[name("cz", "l1", "min")] = pct(min(c02[h]["challenger"]["P2a-l1"]["grade_disagreement_share"] for h in HORIZONS), 1)
    # the master scale itself (the pipeline's rule), read from the product's own module through the models artifact of C01
    ms = figkit.doc("C01/models-taiwan.json")["fit"]["master_scale"]
    R["master"] = ms
    num[name("ms", "grades")] = str(len(ms["grades"]))
    num[name("ms", "first")] = pct(ms["upper"][0], 2)
    num[name("ms", "tenth")] = pct(ms["upper"][10], 1)
    num[name("ms", "ratio")] = f"{ms['upper'][1] / ms['upper'][0]:.2f}"
    num[name("rv", "version")] = agencies["sp"]["version"]
    num[name("cz", "other", "min")] = pct(min(c02[h]["challenger"][c]["grade_disagreement_share"] for h in HORIZONS
                                              for c, _ in CHALLENGERS if c != "P2a-l1"), 1)
    # the acceptance checks of the estimators: rows of a matrix sum to 1, rows of a generator to 0
    for aid, rec in agencies.items():
        o = rec["out"]
        p = np.array(o["pooled"]["matrix"], dtype=float)
        num[name("rowsum", aid)] = f"{np.max(np.abs(p.sum(axis=1) - 1.0)):.0e}"
        for k in ("em", "diagonal", "weighted", "jlt"):
            q = np.array(o["generators"][k]["generator"], dtype=float)
            num[name("genrow", aid, k)] = f"{np.max(np.abs(q.sum(axis=1))):.0e}"
        for gi in (0, 6):
            for k in ("em", "diagonal", "weighted", "jlt"):
                num[name("pifive", aid, GRADES[gi], k)] = pct(o["generators"][k]["pd_5y"][gi], 3)
            num[name("pifive", aid, GRADES[gi], "cohort")] = pct(o["generators"]["cohort_power"]["pd_5y"][gi], 3)
        for gi, g in enumerate(GRADES):
            num[name("lran", aid, g)] = f"{int(rec['lra']['n'][gi]):,}"
            num[name("lrad", aid, g)] = str(int(rec["lra"]["defaults"][gi]))
            num[name("jeffup", aid, g)] = pct(rec["lra"]["jeffreys"]["upper"][gi], 3)
    # the sampling standard deviation of an implied factor at z = 0 for the median cohort size of the grade (delta method)
    from scipy.stats import norm

    for aid, rec in agencies.items():
        sizes = np.array([c["size"] for c in rec["out"]["cohorts"]], dtype=float)
        for g in ZGRADES:
            zz = rec["z"][g]
            n_med = float(np.median(sizes[sizes[:, g] > 0, g]))
            p0 = float(vasicek.conditional_pd(zz["ttc"], zz["rho"], 0.0))
            slope = np.sqrt(1.0 - zz["rho"]) / (np.sqrt(zz["rho"]) * norm.pdf(norm.ppf(p0)))
            zz["samp_sd"] = float(slope * np.sqrt(p0 * (1.0 - p0) / n_med))
            zz["n_med"] = n_med
            num[name("z", aid, GRADES[g], "samp")] = f"{zz['samp_sd']:.2f}"
            num[name("z", aid, GRADES[g], "nmed")] = f"{n_med:,.0f}"
    # the tables of Pluto and Tasche that the acceptance criterion names (tables 1, 2, 3, 4 and 7)
    spec = [c for t in (1, 2, 3, 4, 7) for c in byt[t]]
    num[name("pt", "spec", "n")] = str(len(spec))
    num[name("pt", "spec", "ident")] = str(sum(1 for c in spec if abs(c["gap"]) < 1e-9))
    num[name("pt", "spec", "max")] = f"{max(abs(c['gap']) for c in spec):.2f}"
    return R


def _lra_table(R: dict[str, Any], out: pathlib.Path) -> None:
    header = ["Grade"]
    for _, label in AGENCIES:
        tex_label = label.replace("&", "\\&")
        header += [f"{tex_label} average", f"{tex_label} pooled, Jeffreys 95\\%"]
    rows = []
    for gi, g in enumerate(GRADES):
        row: list[Any] = [g]
        for aid, _ in AGENCIES:
            lra = R["agencies"][aid]["lra"]
            j = lra["jeffreys"]
            row.append(pct(lra["rate"][gi], 3))
            row.append(f"{pct(lra['pooled_rate'][gi], 3)} ({pct(j['lower'][gi], 3)}, {pct(j['upper'][gi], 3)})")
        rows.append(row)
    figkit.table(
        out / "ratings-lra.tex", header, rows, align="lrrrrrr", wide=True,
        caption=("Long-run average one-year default rate by grade from the default page of the ESMA CEREP publication for the EU entities "
                 "of three agencies, in percent: the average of the yearly rates (the quantity of EBA/GL/2017/16 paragraph 84) and, in "
                 "parentheses, the 95\\% Jeffreys interval of the pooled rate. Corporate long-term ratings, annual cohorts."),
        label="tab:ratings-lra")


def _z_table(R: dict[str, Any], out: pathlib.Path) -> None:
    header = ["Agency", "Grade", "TTC PD (\\%)", "$\\rho$", "Years used", "Mean $\\hat z$", "SD $\\hat z$", "Sampling SD", "PIT mean error"]
    rows = []
    for aid, label in AGENCIES:
        for g in ZGRADES:
            zz = R["agencies"][aid]["z"][g]
            rows.append([label, GRADES[g], pct(zz["ttc"], 2), f"{zz['rho']:.3f}", f"{zz['n']} of {zz['cohorts']}",
                         f"${zz['mean']:.2f}$", f"{zz['sd']:.2f}", f"{zz['samp_sd']:.2f}", f"{zz['pit_error']:.1e}"])
    figkit.table(
        out / "ratings-zfactor.tex", header, rows, align="llrrrrrrr", wide=True,
        caption=("Credit-cycle factor implied by the yearly default rate of the three speculative grades with a default in most cohorts: "
                 "the through-the-cycle PD, the asset correlation of the Basel III corporate function at that PD, the cohorts with a "
                 "positive rate, the mean and standard deviation of the implied factor, the standard deviation that the finite cohort "
                 "alone would give at a factor of zero (delta method, median cohort size), and the relative error with which the mean "
                 "of the conditional PD over a standard normal factor returns the through-the-cycle PD."),
        label="tab:ratings-zfactor")


def _est_table(R: dict[str, Any], out: pathlib.Path) -> None:
    est = R["markov"]["est"]
    header = ["Estimator"]
    for gi in (0, 1, 5, 6):
        header += [f"{GRADES[gi]} bias", f"{GRADES[gi]} RMSE"]
    rows = []
    for k, label in ESTIMATORS:
        row: list[Any] = [label]
        for gi in (0, 1, 5, 6):
            e = est[k]
            row.append(f"${1e4 * e['bias'][gi]:+.1f}\\pm{1e4 * e['bias_mcse'][gi]:.1f}$")
            row.append(f"{1e4 * e['rmse'][gi]:.1f}")
        rows.append(row)
    truth = est["cohort"]["truth"]
    rows.append(["True one-year PD"] + sum(([f"{1e4 * truth[gi]:.2f}", ""] for gi in (0, 1, 5, 6)), []))
    figkit.table(
        out / "ratings-estimators.tex", header, rows, align="lrrrrrrrr", wide=True,
        caption=("Bias with its Monte Carlo standard error and root mean squared error, in basis points, of the one-year PD of four grades "
                 "under six estimators of the migration matrix, over repeated panels of five annual snapshots drawn from a Markov chain "
                 "whose generator is the EM generator of the pooled S\\&P counts; the last row is the chain's true one-year PD."),
        label="tab:ratings-estimators")


def _gen_table(R: dict[str, Any], out: pathlib.Path) -> None:
    header = ["Agency", "$S$", "Unreachable zero cells", "EM", "Diagonal", "Weighted", "JLT", "EM iterations"]
    rows = []
    for aid, label in AGENCIES:
        o = R["agencies"][aid]["out"]
        g = o["generators"]
        rows.append([label, f"{o['embedding']['S']:.3f}", str(len(o["embedding"]["theorem3"]["c"])),
                     f"{g['em']['l1']:.4f}", f"{g['diagonal']['l1']:.4f}", f"{g['weighted']['l1']:.4f}",
                     f"{g['jlt']['l1']:.4f}", str(g["em"]["iterations"])])
    figkit.table(
        out / "ratings-generators.tex", header, rows, align="lrrrrrrr", wide=True,
        caption=("Embedding diagnostics of the pooled annual matrix of each agency and the L1 distance between the matrix and the exponential "
                 "of each generator: the convergence number $S$ of the logarithm series, the zero cells whose state is reachable through "
                 "other states, and the distance for the EM generator and the diagonal, weighted and Jarrow--Lando--Turnbull (JLT) repairs."),
        label="tab:ratings-generators")


def _cal_table(R: dict[str, Any], out: pathlib.Path) -> None:
    header = ["Approach"]
    for y in (2010, 2011):
        header += [f"{y} PD (\\%)", f"{y} AR (\\%)", f"{y} $p$ (\\%)", f"{y} RW (\\%)"]
    rows = []
    for aid, label in APPROACHES:
        row: list[Any] = [label]
        for y in (2010, 2011):
            a = R["cal"][y]["o"]["approaches"][aid]
            t = R["cal"][y]["tests"][aid]
            row += [pct(a["pd"], 3), pct(a["accuracy_ratio"], 1), pm(t["p_value"], t["extras"]["mc_standard_error"], 1),
                    pct(R["cal"][y]["impact"][f"rw_{aid}"]["value"], 1)]
        rows.append(row)
    rows.append(["Observed"] + sum(([pct(R["cal"][y]["o"]["pd1"], 3), pct(R["cal"][y]["o"]["ar1"], 1), "", ""] for y in (2010, 2011)), []))
    figkit.table(
        out / "ratings-calibration.tex", header, rows, align="lrrrrrrrr", wide=True,
        caption=("The 2009 S\\&P rating system carried to 2010 and 2011 by the nine calibration approaches: the PD each forecasts for the "
                 "portfolio (the first four use the observed PD of the forecast year), the accuracy ratio (AR) of the model it implies, the "
                 "Monte Carlo $p$-value of the default-profile test with its standard error (100,000 samples), and the average IRB "
                 "risk weight (RW) of the forecast portfolio, in percent of exposure."),
        label="tab:ratings-calibration")


def _ldp_table(R: dict[str, Any], out: pathlib.Path) -> None:
    lo = R["ldp"]
    header = ["Level"] + [f"{a}, independent" for a in LDP_GRADES] + [f"{a}, $\\rho = 12$\\%" for a in LDP_GRADES]
    rows = []
    for gi, g in enumerate(lo["gammas"]):
        rows.append([f"{100 * g:g}\\%"] + [pct(lo["bounds"]["independent"][gi][ai], 2) for ai in range(3)]
                    + [pct(lo["bounds"]["correlated"][gi][ai], 2) for ai in range(3)])
    figkit.table(
        out / "ratings-ldp.tex", header, rows, align="lrrrrrr", wide=True,
        caption=("Most prudent upper bound of the PD, in percent, of the three grades of the Pluto and Tasche portfolio (100, 400 and 300 "
                 "obligors with 0, 2 and 1 defaults) at six confidence levels, for independent defaults and for an asset correlation of 12\\%. "
                 "The bounds rise with the level and with the correlation, and keep the order of the grades."),
        label="tab:ratings-ldp")


def _cov_table(R: dict[str, Any], out: pathlib.Path) -> None:
    kt = R["sim"]["known_truth"]
    header = ["Level"]
    for kind, label in (("independent", "independent"), ("correlated", "correlated"), ("scaled", "scaled")):
        header += [f"{g}, {label}" for g in LDP_GRADES]
    rows = []
    for gi in range(5):
        gamma = kt["coverage"]["independent"]["A"][gi]["gamma"]
        row: list[Any] = [f"{100 * gamma:g}\\%"]
        for kind in ("independent", "correlated", "scaled"):
            for g in LDP_GRADES:
                c = kt["coverage"][kind][g][gi]
                row.append(f"{100 * c['coverage']:.1f}")
        rows.append(row)
    figkit.table(
        out / "ratings-ldp-coverage.tex", header, rows, align="lrrrrrrrrr", wide=True,
        caption=("Share of 20,000 generated years in which the most prudent bound of each grade lies at or above the true PD (0.05\\%, 0.10\\% "
                 "and 0.20\\%, correlation 12\\%), in percent, for the independent bound, the correlated bound and the independent bound "
                 "scaled to the portfolio bound at the same level; the binomial standard error is at most 0.4 points."),
        label="tab:ratings-ldp-coverage")


def _gold_table(R: dict[str, Any], out: pathlib.Path) -> None:
    g = R["gold_tasche"]
    header = ["Source and table", "Cells", "Identical at the printed digits", "Within tolerance", "Largest gap"]
    rows: list[list[Any]] = []
    byt = R["ldp_tables"]
    groups = (("Pluto and Tasche, tables 1 to 6 (independent)", range(1, 7)), ("Pluto and Tasche, tables 7 and 8 (correlated)", (7, 8)),
              ("Pluto and Tasche, tables 9 to 12 (scaled)", range(9, 13)), ("Pluto and Tasche, tables 13 and 14 (five years)", (13, 14)))
    for label, tabs in groups:
        cells = [c for t in tabs for c in byt[t]]
        rows.append([label, str(len(cells)), str(sum(1 for c in cells if abs(c["gap"]) < 1e-9)), "--",
                     f"{max(abs(c['gap']) for c in cells):.2f} pp"])
    for key, label, unit in (("t5", "Tasche, table 5 (smoothed curve, 2009)", ""), ("t6", "Tasche, table 6 (implied default profile, 2009)", ""),
                             ("t7", "Tasche, table 7 (136 forecast cells)", "")):
        n, ident, ok, mx = g[key]
        rows.append([label, str(n), str(ident), str(ok), f"{mx:.4f}"])
    rows.append(["Tasche, table 8 (case 3 forecast PD)", str(g["t8"][0]), "--", "--", f"{g['t8'][1]:.3f} pp"])
    rows.append(["Tasche, table 7 $p$-values", str(g["t7p"][0]), "--", "--", f"{g['t7p'][1]:.2f} pp"])
    irw = R["pub"]["irw"]["rows"]
    rows.append(["Israel, Rosenthal and Wei, nine distances", str(len(irw)), str(sum(1 for r in irw if r["agrees"])), "--", "--"])
    sr = R["pub"]["sr190"]["rows"]
    rows.append(["Schuermann and Hanson, table 5 intervals", str(len(sr)), str(sum(1 for r in sr if r["agrees"])), "--", "--"])
    figkit.table(
        out / "ratings-golden.tex", header, rows, align="lrrrr", wide=True,
        caption=("Printed values of the five papers the engine reproduces for these methods, recomputed from the committed inputs: the cells "
                 "recomputed, those identical to the printed digits, those within the engine's stated tolerance for the table, and the "
                 "largest gap (in percentage points for the Pluto and Tasche tables and Tasche table 8, in the printed unit otherwise)."),
        label="tab:ratings-golden")


def _c02_table(R: dict[str, Any], out: pathlib.Path) -> None:
    header = ["Document", "Rows", "Events"] + [label for _, label in CHALLENGERS]
    rows = []
    names = {"h1": "1-year file", "h2": "2-year file", "h3": "3-year file", "h4": "4-year file", "h5": "5-year file", "pooled": "Pooled"}
    for h in HORIZONS:
        c = R["c02"][h]
        rows.append([names[h], c["counts"]["rows"], c["counts"]["events"]]
                    + [pct(c["challenger"][cid]["grade_disagreement_share"], 1) for cid, _ in CHALLENGERS])
    figkit.table(
        out / "ratings-c02.tex", header, rows, align="lrrrrrrr", wide=True,
        caption=("Share of the holdout companies of each Polish bankruptcy document whose master-scale grade under a challenger differs by at "
                 "least two grades from the grade under the logistic scorecard, in percent; the grade of a PD is its position on the "
                 "geometric master scale of twelve grades."),
        label="tab:ratings-c02")


def numbers(R: dict[str, Any], out: pathlib.Path) -> pathlib.Path:
    lines = ["% Written by tables/make_ratings.py: every number quoted in sections/07-ratings.tex. Do not edit."]
    for k in sorted(R["num"]):
        value = R["num"][k]
        if value.startswith("-") and not value.startswith("--"):
            value = "\\ensuremath{-}" + value[1:]  # a true minus sign in text mode
        lines.append(f"\\newcommand{{\\{k}}}{{{value}}}")
    path = out / "ratings-numbers.tex"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path


def fit_width(path: pathlib.Path) -> None:
    """Wrap the tabular of a table file in a box that shrinks it to the line width when it is wider (never enlarges it)."""
    text = path.read_text(encoding="utf-8")
    if "\\resizebox" in text:
        return
    text = text.replace("\\begin{tabular}", "\\resizebox{\\ifdim\\width>\\linewidth\\linewidth\\else\\width\\fi}{!}{%\n\\begin{tabular}", 1)
    text = text.replace("\\end{tabular}", "\\end{tabular}}", 1)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    R = compute()
    out = HERE
    _lra_table(R, out)
    _z_table(R, out)
    _est_table(R, out)
    _gen_table(R, out)
    _cal_table(R, out)
    _ldp_table(R, out)
    _cov_table(R, out)
    _gold_table(R, out)
    _c02_table(R, out)
    numbers(R, out)
    for table in sorted(out.glob("ratings-*.tex")):
        if table.name != "ratings-numbers.tex":
            fit_width(table)
    print(f"wrote {len(list(out.glob('ratings-*.tex')))} files, {len(R['num'])} numbers")


if __name__ == "__main__":
    main()
