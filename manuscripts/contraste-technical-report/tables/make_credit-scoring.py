"""Tables and number macros of the credit-scoring section (sections/06-credit-scoring.tex), built from the committed
artifacts under ``data/derived`` (cases C01, C02 and C03) through ``figkit``; nothing in the section is typed by hand.

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/tables/make_credit-scoring.py

Writes ``tables/credit-scoring-<name>.tex`` (booktabs tables, one per result table of the section) and
``tables/credit-scoring-numbers.tex`` (``\\newcommand`` macros ``\\cs...``, one per number the prose reads, so that the text
and the artifacts cannot drift apart). The figure script imports ``derive`` from this file.
"""
from __future__ import annotations

import bisect
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

OUT = HERE
VARIANTS = ["holdout", "drift-moderate", "drift-severe", "prior-shift", "label-noise", "small-sample", "german-twin"]
VARIANT_CODE = {"holdout": "Ho", "drift-moderate": "Dm", "drift-severe": "Ds", "prior-shift": "Ps", "label-noise": "Ln",
                "small-sample": "Ss", "german-twin": "Gt"}
VARIANT_LABEL = {"holdout": "Holdout", "drift-moderate": "Drift 0.25", "drift-severe": "Drift 0.6",
                 "prior-shift": "Prior shift x1.5", "label-noise": "Label noise 5\\%", "small-sample": "2,000 rows",
                 "german-twin": "German twin"}
#: the rung ids of the committed ladder, the short code each macro uses and the name the text gives the method
RUNGS = [("P0-constant", "Cn", "Constant PD"), ("P0-single", "Pz", "Single variable"), ("P1-scorecard", "Sc", "WoE scorecard"),
         ("P2a-l1", "Ll", "L1 logistic"), ("P2b-pltr", "Pl", "PLTR"), ("P3-ebm", "Eb", "EBM"),
         ("P4-lightgbm", "Lg", "LightGBM"), ("P4-xgboost", "Xg", "XGBoost"), ("P5-tabpfn", "Tp", "TabPFN")]
CODE = {r: c for r, c, _ in RUNGS}
NAME = {r: n for r, _, n in RUNGS}
CHALLENGERS = ["P2a-l1", "P2b-pltr", "P3-ebm", "P4-lightgbm", "P4-xgboost"]
HORIZONS = ["h1", "h2", "h3", "h4", "h5", "pooled"]
HORIZON_CODE = {"h1": "A", "h2": "B", "h3": "C", "h4": "D", "h5": "E", "pooled": "P"}
HORIZON_LABEL = {"h1": "1 year", "h2": "2 years", "h3": "3 years", "h4": "4 years", "h5": "5 years", "pooled": "Pooled"}
COHORTS = ["fy2006-07", "fy2008-10", "fy2011-14", "fy2015-17", "fy2018-20"]
COHORT_CODE = {"fy2006-07": "A", "fy2008-10": "B", "fy2011-14": "C", "fy2015-17": "D", "fy2018-20": "E"}
COHORT_LABEL = {"fy2006-07": "FY2006--07", "fy2008-10": "FY2008--10", "fy2011-14": "FY2011--14", "fy2015-17": "FY2015--17",
                "fy2018-20": "FY2018--20"}
REJECT_RUNGS = ["oracle", "accepted-only", "augmentation", "hard-cutoff", "parcelling", "parcelling-prudent", "fuzzy"]
REJECT_CODE = {"oracle": "Or", "accepted-only": "Ao", "augmentation": "Au", "hard-cutoff": "Hc", "parcelling": "Pa",
               "parcelling-prudent": "Pp", "fuzzy": "Fu"}
REJECT_NAME = {"oracle": "Oracle", "accepted-only": "Accepted only", "augmentation": "Augmentation",
               "hard-cutoff": "Hard cut-off", "parcelling": "Parcelling", "parcelling-prudent": "Parcelling, prudence 2",
               "fuzzy": "Fuzzy augmentation"}
REGIMES = ["mar", "weak", "moderate", "strong"]
REGIME_CODE = {"mar": "Mar", "weak": "Weak", "moderate": "Mod", "strong": "Str"}


# ----------------------------------------------------------------------------------------------------------------------
# formatting

def f3(x: float) -> str:
    return f"{x:.3f}"


def f4(x: float) -> str:
    return f"{x:.4f}"


def signed(x: float, d: int = 3) -> str:
    if round(x, d) == 0:
        return f"{0:.{d}f}"
    return f"{x:+.{d}f}".replace("-", "$-$") if x < 0 else f"{x:+.{d}f}"


def pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}"


def pfmt(p: float) -> str:
    """A p-value as the text reads it: fixed digits above 0.001, a power of ten below it."""
    if p is None:
        return "--"
    if p >= 0.001:
        return f"{p:.3f}"
    if p == 0.0:
        return "\\ensuremath{<10^{-300}}"
    mant, exp = f"{p:.1e}".split("e")
    return f"\\ensuremath{{{mant}\\times10^{{{int(exp)}}}}}"


def pm(x: float, lo: float, hi: float, d: int = 3) -> str:
    return f"${x:.{d}f}\\pm{(hi - lo) / 2:.{d}f}$"


def interval(x: float, lo: float, hi: float, d: int = 3, scale: float = 1.0) -> str:
    def s(v: float) -> str:
        return f"${v * scale:.{d}f}$"

    return f"{s(x)} [{s(lo)}, {s(hi)}]"


def sci(x: float) -> str:
    """A small positive number as a power of ten for a macro (zero stays 0)."""
    if x == 0:
        return "0"
    mant, exp = f"{x:.1e}".split("e")
    return f"\\ensuremath{{{mant}\\times10^{{{int(exp)}}}}}"


def sh(*lines: str) -> str:
    """A header cell of several lines."""
    return "\\shortstack{" + "\\\\".join(lines) + "}"


def tbl(path, header, rows, size="small", **kw):
    """``figkit.table`` with every string cell passed as LaTeX (the cells below are built as LaTeX, so none is escaped); ``size``
    replaces the font size of the table environment."""
    rows = [[("\\relax " + c) if isinstance(c, str) else c for c in r] for r in rows]
    out = figkit.table(path, header, rows, **kw)
    if size != "small":
        text = path.read_text(encoding="utf-8").replace("\\small", "\\" + size + "\n\\setlength{\\tabcolsep}{3.5pt}", 1)
        path.write_text(text, encoding="utf-8", newline="\n")
    return out


# ----------------------------------------------------------------------------------------------------------------------
# loading and derivation

def _portfolio(doc: dict) -> dict[str, dict]:
    """The portfolio-level rows of a C01 or C02 variant document, by model id."""
    out: dict[str, dict] = {}
    for t in doc["tests"]:
        if t["segment"] != "portfolio":
            continue
        m = out.setdefault(t["model_id"], {})
        e = t["extras"]
        tid = t["test_id"]
        if tid == "disc.auc":
            m.update(auc=t["metric"], lo=e["ci95_low"], hi=e["ci95_high"], se=e["se"], n=t["n"], events=t["n_events"])
        elif tid == "disc.ks":
            m["ks"] = t["metric"]
        elif tid == "pd.brier":
            m.update(brier=t["metric"], skill=e["brier_skill"])
        elif tid == "pd.ece":
            m["ece"] = t["metric"]
        elif tid == "disc.delong":
            m.update(dl_diff=e["difference"], dl_p=t["p_value"], dl_light=t["light"])
        elif tid == "pd.hosmer_lemeshow":
            m.update(hl_p=t["p_value"], hl_light=t["light"])
        elif tid == "pd.spiegelhalter":
            m.update(sp_p=t["p_value"], sp_light=t["light"])
        elif tid == "stability.psi":
            m["psi"] = t["metric"]
            m["psi_bench"] = e["benchmark_05"]
    return out


def _points_check(models: dict, holdout: dict) -> dict:
    """Recompute the points of the 50 scored applicants of the holdout document from the points table and the bins alone."""
    sc = next(m for m in models["model"] if m["id"] == "P1-scorecard")["details"]
    sample = holdout["outputs"]["sample"]
    table: dict[str, list] = {}
    for r in sc["points_table"]:
        table.setdefault(r["feature"], []).append(r)
    match = 0
    for i in range(len(sample["ids"])):
        pts = []
        for f in sc["features"]:
            idx = bisect.bisect_right(sc["bins"][f]["splits"], sample["inputs"][f][i])
            pts.append(table[f][idx]["points"])
        match += int(pts == sample["scorecard_points"][i])
    sums = all(sum(sample["scorecard_points"][i]) == sample["scorecard_score"][i] for i in range(len(sample["ids"])))
    monotone = 0
    for f in sc["features"]:
        rates = [r["event_rate"] for r in table[f] if r["count"] > 0]
        monotone += int(all(a <= b + 1e-12 for a, b in zip(rates, rates[1:])) or all(a >= b - 1e-12 for a, b in zip(rates, rates[1:])))
    return {"n": len(sample["ids"]), "match": match, "sum_ok": sums, "features": len(sc["features"]), "monotone": monotone}


def _ebm_check(models: dict, holdout: dict) -> dict:
    """Evaluate the exported additive terms on the 50 scored applicants and compare with the logits the artifact stores; and the
    monotonicity of the main-effect shape functions of the constrained inputs."""
    export = next(m for m in models["model"] if m["id"] == "P3-ebm")["details"]["export"]
    cons = next(m for m in models["model"] if m["id"] == "P4-lightgbm")["details"]["constraints"]
    sample = holdout["outputs"]["sample"]
    feats = export["features"]
    names = [f["name"] for f in feats]

    def bin_of(feature: dict, level: int, value: float) -> int:
        lv = feature["levels"][min(level, len(feature["levels"]) - 1)]
        if lv["kind"] == "nominal":
            key = str(int(value)) if float(value).is_integer() else str(value)
            return lv["categories"].get(key, len(lv["categories"]) + 1)
        return int(np.searchsorted(np.asarray(lv["cuts"]), float(value), side="right")) + 1

    gap = 0.0
    for i in range(len(sample["ids"])):
        total = export["intercept"]
        for t in export["terms"]:
            level = 0 if len(t["features"]) == 1 else 1
            idx = tuple(bin_of(feats[j], level, sample["inputs"][names[j]][i]) for j in t["features"])
            total += float(np.asarray(t["scores"])[idx])
        gap = max(gap, abs(total - sample["ebm_logit"][i]))
    constrained = mono = 0
    for t in export["terms"]:
        if len(t["features"]) == 1 and cons.get(names[t["features"][0]], 0) != 0:
            constrained += 1
            steps = np.diff(np.asarray(t["scores"], dtype=float)[1:-1]) * cons[names[t["features"][0]]]
            mono += int(steps.min() >= -1e-12)
    pairs = sum(1 for t in export["terms"] if len(t["features"]) == 2)
    return {"gap": gap, "constrained": constrained, "monotone": mono, "terms": len(export["terms"]), "pairs": pairs,
            "n": len(sample["ids"])}


def _fit_summary(models: dict) -> dict:
    by = {m["id"]: m for m in models["model"]}
    sc = by["P1-scorecard"]["details"]
    pl = by["P2b-pltr"]["details"]
    out = {
        "split": models["fit"]["split"], "inputs": len(models["fit"]["features"]),
        "sc_kept": len(sc["features"]), "sc_dropped": len(sc["dropped"]), "sc_cells": len(sc["points_table"]),
        "sc_neg": sum(1 for b in sc["coefficients"].values() if b < 0),
        "sc_intercept": sc["intercept"], "sc_factor": sc["scaling"]["factor"], "sc_offset": sc["scaling"]["offset"],
        "l1_c": by["P2a-l1"]["details"]["C"], "l1_selected": len(by["P2a-l1"]["details"]["selected"]),
        "l1_signs": by["P2a-l1"]["details"]["signs_agree_with_woe"],
        "pl_c": pl["C"], "pl_cand": pl["n_candidate_rules"], "pl_sel": len(pl["selected_rules"]),
        "pl_jm": pl["stability"]["jaccard_mean"], "pl_jmin": pl["stability"]["jaccard_min"], "pl_boot": pl["stability"]["bootstraps"],
        "pl_jacc": pl["stability"]["jaccard"], "pl_woe": pl["woe_encoded"],
        "eb_cfg": by["P3-ebm"]["parameters"], "eb_terms": len(by["P3-ebm"]["details"]["export"]["terms"]),
        "lg_rounds": by["P4-lightgbm"]["parameters"]["rounds"]["value"],
        "lg_mono": by["P4-lightgbm"]["details"]["monotonicity"]["monotone"],
        "lg_viol": max(v["max_violation"] for v in by["P4-lightgbm"]["details"]["monotonicity"]["features"].values()),
        "lg_constrained": len(by["P4-lightgbm"]["details"]["monotonicity"]["features"]),
        "lg_rows": by["P4-lightgbm"]["details"]["monotonicity"]["rows"],
        "lg_grid": len(by["P4-lightgbm"]["details"]["monotonicity"]["levels"]),
        "reason": models["fit"]["reason_stability"],
        "drop_iv": sum(1 for v in sc["dropped"].values() if v.startswith("information value")),
        "drop_sign": sum(1 for v in sc["dropped"].values() if v.startswith("wrong sign")),
        "iv_max": max(sc["iv"].items(), key=lambda kv: kv[1]),
        "lg_cal_knots": len(by["P4-lightgbm"]["calibration"]["x"]), "eb_cal_knots": len(by["P3-ebm"]["calibration"]["x"]),
    }
    if "P4-xgboost" in by:
        out["xg_knots"] = len(by["P4-xgboost"]["calibration"]["x"])
        out["xg_viol"] = max(v["max_violation"] for v in by["P4-xgboost"]["details"]["monotonicity"]["features"].values())
        out["xg_rounds"] = by["P4-xgboost"]["parameters"]["rounds"]["value"]
        out["xg_mono"] = by["P4-xgboost"]["details"]["monotonicity"]["monotone"]
    if "P5-tabpfn" in by:
        out["tp"] = by["P5-tabpfn"]["details"]
    return out


def derive() -> dict:
    """Every number the section reads, from the committed artifacts."""
    D: dict = {"c01": {}, "c02": {}, "c03": {}}
    raw: dict = {}
    for v in VARIANTS:
        raw[v] = figkit.doc(f"C01/{v}.json")
        D["c01"][v] = _portfolio(raw[v])
    models = {k: figkit.doc(f"C01/models-{k}.json") for k in ("taiwan", "german", "taiwan-small")}
    D["raw_c01"] = raw
    D["fit"] = {k: _fit_summary(m) for k, m in models.items()}
    D["points"] = _points_check(models["taiwan"], raw["holdout"])
    D["ebm"] = _ebm_check(models["taiwan"], raw["holdout"])
    D["points_table"] = next(m for m in models["taiwan"]["model"] if m["id"] == "P1-scorecard")["details"]["points_table"]
    D["sc_details"] = next(m for m in models["taiwan"]["model"] if m["id"] == "P1-scorecard")["details"]
    D["models_taiwan"] = models["taiwan"]
    # C01 reject inference (German twin)
    D["reject"] = raw["german-twin"]["outputs"]["reject_inference"]
    # C02
    c02 = {}
    for h in HORIZONS:
        doc = figkit.doc(f"C02/{h}.json")
        o = doc["outputs"]
        rungs = {r["model_id"].split("-", 1)[1]: r for r in o["rungs"]}
        chal = {c["challenger"].split("-", 1)[1]: c for c in o["challenger"]}
        c02[h] = {"counts": o["counts"], "split": o["split"], "rungs": rungs, "chal": chal,
                  "pooled": o.get("pooled"), "tests": _portfolio(doc)}
    D["c02"] = c02
    c02m = figkit.doc("C02/models-polish-horizons.json")
    D["c02_files"] = c02m["fit"]["files"]
    # C03
    c03 = {}
    for c in COHORTS:
        doc = figkit.doc(f"C03/{c}.json")
        o = doc["outputs"]
        c03[c] = {"training": o["training"], "rungs": {r["rung_id"]: r for r in o["rung_comparison"]},
                  "vintages": o["vintage_summary"]["rows"], "curves": o["vintage_curves"],
                  "models": {m["id"]: m for m in doc["model"]}, "tests": _portfolio(doc),
                  "stability": o["stability"]["rows"], "label": o["cohort"]["label"]["en"]}
    D["c03"] = c03
    return D


# ----------------------------------------------------------------------------------------------------------------------
# macros

class Macros:
    def __init__(self) -> None:
        self.items: dict[str, str] = {}

    def add(self, name: str, text: str) -> None:
        assert name.isalpha(), name
        self.items["cs" + name] = text

    def write(self, path: pathlib.Path) -> None:
        lines = ["% Generated by tables/make_credit-scoring.py from data/derived; do not edit.", ""]
        for k in sorted(self.items):
            lines.append(f"\\newcommand{{\\{k}}}{{{self.items[k]}}}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def build_macros(D: dict) -> Macros:
    M = Macros()
    # --- C01 per variant and method
    for v in VARIANTS:
        for rid, code, _ in RUNGS:
            r = D["c01"][v].get(rid)
            if not r:
                continue
            p = f"{VARIANT_CODE[v]}{code}"
            if "auc" in r:
                M.add(p + "Auc", f4(r["auc"]))
                M.add(p + "AucLo", f4(r["lo"]))
                M.add(p + "AucHi", f4(r["hi"]))
                M.add(p + "Gini", f4(2 * r["auc"] - 1))
            for key, nm, fn in (("ks", "Ks", f4), ("brier", "Brier", f4), ("ece", "Ece", f4), ("skill", "Skill", f3)):
                if key in r and r[key] is not None:
                    M.add(p + nm, fn(r[key]))
            if "dl_diff" in r:
                M.add(p + "DlDiff", f"{r['dl_diff']:+.4f}".replace("-", "$-$"))
                M.add(p + "DlP", pfmt(r["dl_p"]))
            if "hl_p" in r:
                M.add(p + "HlP", pfmt(r["hl_p"]))
            if "sp_p" in r:
                M.add(p + "SpP", pfmt(r["sp_p"]))
            if "psi" in r:
                M.add(p + "Psi", f4(r["psi"]))
                M.add(p + "PsiBench", f4(r["psi_bench"]))
        r = D["c01"][v]["P1-scorecard"]
        M.add(f"{VARIANT_CODE[v]}N", f"{r['n']:,}".replace(",", "{,}"))
        M.add(f"{VARIANT_CODE[v]}Events", f"{r['events']:,}".replace(",", "{,}"))
        M.add(f"{VARIANT_CODE[v]}Rate", pct(r["events"] / r["n"], 2))
    # gap ladder best vs scorecard on the holdout
    ho = D["c01"]["holdout"]
    best = max(CHALLENGERS, key=lambda k: ho[k]["auc"])
    M.add("HoBestAucGain", f4(ho[best]["auc"] - ho["P1-scorecard"]["auc"]))
    M.add("HoBestName", NAME[best])
    # reliability before and after calibration of the three calibrated rungs (ten quantile bins of the holdout)
    raw = D["raw_c01"]["holdout"]["outputs"]["rungs"]
    for rid in ("P3-ebm", "P4-lightgbm", "P4-xgboost"):
        for key, tag in (("reliability_raw", "Raw"), ("reliability", "Cal")):
            bins = raw[rid][key]
            n = sum(b["n"] for b in bins)
            ece = sum(b["n"] * abs(b["dr"] - b["pd"]) for b in bins) / n
            M.add(f"HoEce{CODE[rid]}{tag}", f4(ece))
    # --- fits
    for fit, code in (("taiwan", "Tw"), ("german", "Ge"), ("taiwan-small", "Sm")):
        F = D["fit"][fit]
        M.add(f"Fit{code}Train", f"{F['split']['train']['n']:,}".replace(",", "{,}"))
        M.add(f"Fit{code}Cal", f"{F['split']['calibration']['n']:,}".replace(",", "{,}"))
        M.add(f"Fit{code}Hold", f"{F['split']['holdout']['n']:,}".replace(",", "{,}"))
        M.add(f"Fit{code}Inputs", str(F["inputs"]))
        M.add(f"Fit{code}Kept", str(F["sc_kept"]))
        M.add(f"Fit{code}Dropped", str(F["sc_dropped"]))
        M.add(f"Fit{code}Cells", str(F["sc_cells"]))
        M.add(f"Fit{code}DropIv", str(F["drop_iv"]))
        M.add(f"Fit{code}DropSign", str(F["drop_sign"]))
        M.add(f"Fit{code}Neg", str(F["sc_neg"]))
        M.add(f"Fit{code}IvMax", f3(F["iv_max"][1]))
        M.add(f"Fit{code}LlSigns", "agree" if F["l1_signs"] else "disagree")
        M.add(f"Fit{code}LlC", f"{F['l1_c']:g}")
        M.add(f"Fit{code}LlSel", str(F["l1_selected"]))
        M.add(f"Fit{code}PlC", f"{F['pl_c']:g}")
        M.add(f"Fit{code}PlCand", str(F["pl_cand"]))
        M.add(f"Fit{code}PlSel", str(F["pl_sel"]))
        M.add(f"Fit{code}PlJm", f3(F["pl_jm"]))
        M.add(f"Fit{code}PlJmin", f3(F["pl_jmin"]))
        M.add(f"Fit{code}PlBoot", str(F["pl_boot"]))
        M.add(f"Fit{code}LgRounds", str(F["lg_rounds"]))
        M.add(f"Fit{code}EbTerms", str(F["eb_terms"]))
        M.add(f"Fit{code}ReasonMean", f3(F["reason"]["overlap_mean"]))
        M.add(f"Fit{code}ReasonMin", f3(F["reason"]["overlap_min"]))
        M.add(f"Fit{code}ReasonBoot", str(F["reason"]["bootstraps"]))
        M.add(f"Fit{code}ReasonRows", str(F["reason"]["rows"]))
        M.add(f"Fit{code}LgViol", f"{F['lg_viol']:g}")
        M.add(f"Fit{code}LgConstrained", str(F["lg_constrained"]))
        M.add(f"Fit{code}LgRows", str(F["lg_rows"]))
        M.add(f"Fit{code}LgGrid", str(F["lg_grid"]))
        M.add(f"Fit{code}LgKnots", str(F["lg_cal_knots"]))
        M.add(f"Fit{code}EbKnots", str(F["eb_cal_knots"]))
        if "xg_rounds" in F:
            M.add(f"Fit{code}XgRounds", str(F["xg_rounds"]))
            M.add(f"Fit{code}XgKnots", str(F["xg_knots"]))
            M.add(f"Fit{code}XgViol", f"{F['xg_viol']:g}")
    F = D["fit"]["taiwan"]
    M.add("ScFactor", f"{F['sc_factor']:.2f}")
    M.add("ScOffset", f"{F['sc_offset']:.2f}")
    M.add("ScIntercept", f"{F['sc_intercept']:.3f}")
    M.add("EbMaxBins", str(F["eb_cfg"]["max_bins"]["value"]))
    M.add("EbMaxIntBins", str(F["eb_cfg"]["max_interaction_bins"]["value"]))
    M.add("EbInteractions", str(F["eb_cfg"]["interactions"]["value"]))
    M.add("EbOuterBags", str(F["eb_cfg"]["outer_bags"]["value"]))
    for feat, tag in (("PAY_0", "PayZero"), ("LIMIT_BAL", "Limit")):
        pts = [r["points"] for r in D["points_table"] if r["feature"] == feat and r["count"] > 0]
        M.add(f"PointsSpan{tag}", str(max(pts) - min(pts)))
    M.add("HoScOverPz", f4(ho["P1-scorecard"]["auc"] - ho["P0-single"]["auc"]))
    for v in VARIANTS:
        for rid in ("P1-scorecard",):
            r = D["c01"][v][rid]
            M.add(f"{VARIANT_CODE[v]}{CODE[rid]}Half", f4((r["hi"] - r["lo"]) / 2))
    for h in HORIZONS:
        d = D["c02"][h]["rungs"]["P1-scorecard"]["discrimination"]["auc_ci"]
        M.add(f"Ctwo{HORIZON_CODE[h]}ScHalf", f4((d["hi"] - d["lo"]) / 2))
    later = [abs(v["gap"]) * 100 for c in COHORTS[2:] for v in D["c03"][c]["vintages"]]
    M.add("CthreeLaterMin", f"{min(later):.1f}")
    M.add("CthreeLaterMax", f"{max(later):.1f}")
    M.add("PointsN", str(D["points"]["n"]))
    M.add("PointsMatch", str(D["points"]["match"]))
    M.add("PointsFeatures", str(D["points"]["features"]))
    M.add("PointsMonotone", str(D["points"]["monotone"]))
    M.add("EbmGap", sci(D["ebm"]["gap"]))
    M.add("EbmConstrained", str(D["ebm"]["constrained"]))
    M.add("EbmMonotone", str(D["ebm"]["monotone"]))
    M.add("EbmPairs", str(D["ebm"]["pairs"]))
    ge = D["fit"]["german"]
    M.add("TpEstimators", str(ge["tp"]["n_estimators"]))
    # --- C02
    for h in HORIZONS:
        H = D["c02"][h]
        hc = HORIZON_CODE[h]
        M.add(f"CtwoRows{hc}", f"{H['counts']['rows']:,}".replace(",", "{,}"))
        M.add(f"CtwoEvents{hc}", f"{H['counts']['events']:,}".replace(",", "{,}"))
        M.add(f"CtwoRate{hc}", pct(H["counts"]["event_rate"], 2))
        M.add(f"CtwoHold{hc}", f"{H['split']['holdout_rows']:,}".replace(",", "{,}"))
        M.add(f"CtwoHoldEv{hc}", str(H["split"]["holdout_events"]))
        flags = 0
        for rid, r in H["rungs"].items():
            code = CODE.get(rid)
            d = r["discrimination"]
            M.add(f"Ctwo{hc}{code}Auc", f4(d["auc"]))
            M.add(f"Ctwo{hc}{code}AucLo", f4(d["auc_ci"]["lo"]))
            M.add(f"Ctwo{hc}{code}AucHi", f4(d["auc_ci"]["hi"]))
            M.add(f"Ctwo{hc}{code}Brier", f4(r["calibration"]["brier"]))
            M.add(f"Ctwo{hc}{code}Gap", f4(r["overfit"]["gap"]))
            flags += int(r["overfit"]["flag"])
        M.add(f"Ctwo{hc}Flags", str(flags))
        for rid, c in H["chal"].items():
            code = CODE[rid]
            M.add(f"Ctwo{hc}{code}Diff", f"{c['auc_diff']:+.4f}".replace("-", "$-$"))
            M.add(f"Ctwo{hc}{code}DiffLo", f"{c['auc_diff_ci']['lo']:+.4f}".replace("-", "$-$"))
            M.add(f"Ctwo{hc}{code}DiffHi", f"{c['auc_diff_ci']['hi']:+.4f}".replace("-", "$-$"))
            M.add(f"Ctwo{hc}{code}DlP", pfmt(c["delong_p_value"]))
            M.add(f"Ctwo{hc}{code}BrierDiff", f"{c['brier_diff']:+.4f}".replace("-", "$-$"))
        M.add(f"Ctwo{hc}Disagree", pct(H["chal"]["P4-lightgbm"]["grade_disagreement_share"], 1))
    M.add("CtwoFlagTotal", str(sum(sum(int(r["overfit"]["flag"]) for r in D["c02"][h]["rungs"].values()) for h in HORIZONS[:5])))
    M.add("CtwoRungTotal", str(sum(len(D["c02"][h]["rungs"]) for h in HORIZONS[:5])))
    # --- C03
    for c in COHORTS:
        C = D["c03"][c]
        cc = COHORT_CODE[c]
        t = C["training"]
        M.add(f"Cthree{cc}Loans", f"{t['n_loans']:,}".replace(",", "{,}"))
        M.add(f"Cthree{cc}Events", f"{t['n_events']:,}".replace(",", "{,}"))
        M.add(f"Cthree{cc}Last", str(t["last_fy"]))
        for rid, r in C["rungs"].items():
            if r["auc"] is None or rid not in CODE:
                continue
            code = CODE[rid]
            M.add(f"Cthree{cc}{code}Auc", f4(r["auc"]))
            M.add(f"Cthree{cc}{code}AucLo", f4(r["auc_ci_low"]))
            M.add(f"Cthree{cc}{code}AucHi", f4(r["auc_ci_high"]))
            M.add(f"Cthree{cc}{code}Brier", f4(r["brier"]))
            M.add(f"Cthree{cc}{code}Cal", f"{r['calibration_gap_5y']:+.4f}".replace("-", "$-$"))
        M.add(f"Cthree{cc}Crisis", "yes" if t["crisis_included"] else "no")
        for v in C["vintages"]:
            fy = v["fiscal_year"]
            M.add(f"CthreeV{chr(65 + fy - 2006)}Obs", pct(v["observed_5y_pd"], 2))
            M.add(f"CthreeV{chr(65 + fy - 2006)}Pred", pct(v["predicted_5y_pd"], 2))
            M.add(f"CthreeV{chr(65 + fy - 2006)}Gap", f"{100 * v['gap']:+.2f}".replace("-", "$-$"))
            M.add(f"CthreeV{chr(65 + fy - 2006)}N", f"{v['n']:,}".replace(",", "{,}"))
            M.add(f"CthreeV{chr(65 + fy - 2006)}Auc", f4(v["auc"]))
    sba = D["c03"]["fy2018-20"]["models"]["P0-constant"]["parameters"]
    M.add("CthreeFitRows", f"{int(sba['fit_rows']['value']):,}".replace(",", "{,}"))
    M.add("CthreeCalRows", f"{int(sba['calibration_rows']['value']):,}".replace(",", "{,}"))
    # --- reject inference
    R = D["reject"]
    d = R["design"]
    M.add("RjRows", str(d["n_rows"]))
    M.add("RjDev", str(d["n_dev"]))
    M.add("RjTest", str(d["n_test"]))
    M.add("RjReps", str(d["reps"]))
    M.add("RjBoot", f"{d['bootstrap']:,}".replace(",", "{,}"))
    M.add("RjAccept", pct(d["accept_share"], 0))
    M.add("RjBands", str(d["bands"]))
    M.add("RjMinAcc", str(d["min_accepted"]))
    M.add("RjPrudence", f"{d['prudence']:g}")
    M.add("RjFloor", f"{d['weight_floor']:g}")
    M.add("RjCinv", f"{d['c_inverse_penalty']:g}")
    M.add("RjHtwo", pct(d["h2_reduction"], 0))
    M.add("RjHthree", f"{d['h3_auc_gain']:g}")
    for g in R["regimes"]:
        rc = REGIME_CODE[g["id"]]
        M.add(f"Rj{rc}Kappa", f"{g['kappa']:g}")
        M.add(f"Rj{rc}Pop", pct(g["default_rate"]["population"], 1))
        M.add(f"Rj{rc}AccRate", pct(g["default_rate"]["accepted"], 1))
        M.add(f"Rj{rc}RejRate", pct(g["default_rate"]["rejected"], 1))
        for r in g["rungs"]:
            c = REJECT_CODE[r["id"]]
            p = f"Rj{rc}{c}"
            M.add(p + "Bias", f"{100 * r['bias']['mean']:+.2f}".replace("-", "$-$"))
            M.add(p + "BiasLo", f"{100 * r['bias']['lo']:+.2f}".replace("-", "$-$"))
            M.add(p + "BiasHi", f"{100 * r['bias']['hi']:+.2f}".replace("-", "$-$"))
            M.add(p + "Red", pct(r["reduction"]["value"], 1))
            M.add(p + "RedLo", pct(r["reduction"]["lo"], 1))
            M.add(p + "RedHi", pct(r["reduction"]["hi"], 1))
            M.add(p + "Auc", f4(r["auc"]["mean"]))
            M.add(p + "DAuc", f"{r['auc_vs_accepted_only']['mean']:+.4f}".replace("-", "$-$"))
            M.add(p + "DAucLo", f"{r['auc_vs_accepted_only']['lo']:+.4f}".replace("-", "$-$"))
            M.add(p + "DAucHi", f"{r['auc_vs_accepted_only']['hi']:+.4f}".replace("-", "$-$"))
            M.add(p + "Brier", f4(r["brier"]["mean"]))
            M.add(p + "Beats", pct(r["beats_share"], 0))
    for h in R["hypotheses"]:
        hid = {"H1": "Hone", "H2": "Htwo", "H3": "Hthree"}[h["id"]]
        M.add(f"Rj{hid}Holds", "holds" if h["holds"] else "does not hold")
        M.add(f"Rj{hid}Rung", REJECT_NAME[h["rung"]])
    return M


# ----------------------------------------------------------------------------------------------------------------------
# tables

def table_fit(D: dict) -> None:
    F = D["fit"]["taiwan"]
    ge = D["fit"]["german"]
    sm = D["fit"]["taiwan-small"]
    rows = [
        ["WoE scorecard", f"{F['sc_kept']} of {F['inputs']} inputs kept (information value at least 0.02, sign check); "
         f"{F['sc_cells']} points-table cells; PDO 20, reference 600 points at odds 50"],
        ["L1 logistic", f"penalty $1/C$ with $C={F['l1_c']:g}$ (grid 0.003 to 1, five-fold cross-validated log loss); "
         f"{F['l1_selected']} non-zero coefficients"],
        ["PLTR", f"$C={F['pl_c']:g}$; {F['pl_cand']} candidate rules; {F['pl_sel']} selected; "
         f"mean Jaccard {F['pl_jm']:.3f} over {F['pl_boot']} resamples"],
        ["EBM", f"{F['eb_terms']} terms ({D['ebm']['pairs']} pairwise); at most {F['eb_cfg']['max_bins']['value']} bins per main "
         f"term and {F['eb_cfg']['max_interaction_bins']['value']} per pair; {F['eb_cfg']['outer_bags']['value']} outer bags; "
         f"isotonic map with {F['eb_cal_knots']} knots"],
        ["LightGBM", f"{F['lg_rounds']} trees by early stopping; 15 leaves; learning rate 0.05; isotonic map with "
         f"{F['lg_cal_knots']} knots"],
        ["XGBoost", f"{F['xg_rounds']} trees by early stopping; depth 4; learning rate 0.05"],
    ]
    rows = [[a, b] for a, b in rows]
    rows.append(["Training slice", f"{F['split']['train']['n']:,} rows ({F['split']['train']['defaults']:,} defaults); "
                 f"calibration slice {F['split']['calibration']['n']:,}; locked holdout {F['split']['holdout']['n']:,}"])
    tbl(OUT / "credit-scoring-fit.tex", ["Method", "Fitted configuration on the card-default training slice"],
                 rows,
                 caption="Fitted configuration of each method on the training slice of the Taiwan card-default sample (C01): "
                         "the parameters chosen on training data only, the number of retained terms and the size of the slices.",
                 label="tab:cs-fit", align="lp{11cm}")


def table_points(D: dict) -> None:
    rows = []
    for feat in ("PAY_0", "LIMIT_BAL"):
        for r in D["points_table"]:
            if r["feature"] == feat and r["count"] > 0:
                rows.append([feat.replace("_", "\\_"), r["bin"].replace("inf", "$\\infty$").replace("-$\\infty$", "$-\\infty$"),
                             r["count"], r["events"], f3(r["event_rate"]), signed(r["woe"]),
                             str(r["points"]).replace("-", "$-$")])
    # the bins carry a bracket pair that LaTeX reads as text: wrap them as math-free strings
    rows = [[a, "\\texttt{" + b.replace("$\\infty$", "inf").replace("$-\\infty$", "-inf") + "}", c, d, e, f, g]
            for a, b, c, d, e, f, g in rows]
    tbl(OUT / "credit-scoring-points.tex",
                 ["Input", "Bin", "Rows", "Defaults", "Default rate", "WoE", "Points"], rows,
                 caption="Points table of the two strongest groups of the Taiwan scorecard: the September repayment status and the "
                         "credit limit, with the bin counts, default rates, weight of evidence and integer points on the training slice.",
                 label="tab:cs-points", align="llrrrrr")


def table_c01_holdout(D: dict) -> None:
    ho = D["c01"]["holdout"]
    rows = []
    for rid, _, name in RUNGS:
        if rid not in ho or rid in ("P0-constant", "P5-tabpfn"):
            continue
        r = ho[rid]
        dl = "--" if rid == "P1-scorecard" or "dl_p" not in r else f"{signed(r['dl_diff'], 4)} ({pfmt(r['dl_p'])})"
        rows.append([name, pm(r["auc"], r["lo"], r["hi"]), f3(r["ks"]), f4(r["brier"]), f4(r["ece"]), dl,
                     pfmt(r["hl_p"]) if "hl_p" in r else "--"])
    tbl(OUT / "credit-scoring-c01-holdout.tex",
                 ["Method", "AUC (95\\% CI)", "KS", "Brier", "ECE", sh("$\\Delta$AUC vs scorecard", "(DeLong $p$)"), sh("H-L", "$p$")],
                 rows, size="footnotesize",
                 caption="Discrimination and calibration of each method on the locked holdout of the Taiwan card-default sample "
                         f"({ho['P1-scorecard']['n']:,} cards, {ho['P1-scorecard']['events']:,} defaults): AUC with the DeLong "
                         "interval, Kolmogorov-Smirnov separation, Brier score, expected calibration error, the paired DeLong "
                         "difference against the scorecard and the Hosmer-Lemeshow $p$-value.",
                 label="tab:cs-c01-holdout", align="lrrrrrr")


def table_c01_variants(D: dict) -> None:
    rows = []
    for v in VARIANTS:
        r = D["c01"][v]
        cells = [VARIANT_LABEL[v]]
        for rid in ("P1-scorecard", "P2a-l1", "P2b-pltr", "P3-ebm", "P4-lightgbm"):
            cells.append(f4(r[rid]["auc"]) if rid in r else "--")
        cells.append(f4(r["P5-tabpfn"]["auc"]) if "P5-tabpfn" in r else "--")
        rows.append(cells)
    tbl(OUT / "credit-scoring-c01-variants.tex",
                 ["Variant", "Scorecard", "L1", "PLTR", "EBM", "LightGBM", "TabPFN"], rows,
                 caption="AUC of the ladder on each evaluation population of the Taiwan sample and on the German twin: the observed "
                         "holdout, two covariate shifts, a prior shift, label noise, a ladder refitted on 2,000 rows, and the "
                         "German twin, where TabPFN runs.",
                 label="tab:cs-c01-variants", align="lrrrrrr")


def table_checks(D: dict) -> None:
    rows = []
    for fit, label in (("taiwan", "Taiwan, 16,800 rows"), ("taiwan-small", "Taiwan, 2,000 rows"), ("german", "German, 560 rows")):
        F = D["fit"][fit]
        rows.append([label, f"{F['sc_neg']} of {F['sc_kept']}", f"{F['pl_jm']:.3f} / {F['pl_jmin']:.3f}",
                     f"{F['lg_viol']:g}", str(F["lg_constrained"]),
                     f"{F['reason']['overlap_mean']:.3f} / {F['reason']['overlap_min']:.3f}"])
    tbl(OUT / "credit-scoring-checks.tex",
                 ["Fit", sh("Negative WoE", "coefficients"), sh("PLTR Jaccard", "mean / min"), sh("Largest monotone", "violation"),
                  sh("Constrained", "inputs"), sh("Top-4 reason overlap", "mean / min")], rows, size="scriptsize",
                 caption="Structural checks of the fitted methods on the three fits of C01: the sign of every scorecard coefficient, "
                         "the stability of the PLTR rule set over 20 bootstrap resamples, the largest violation of the declared "
                         "monotone direction on the partial-dependence grid, and the overlap of the four principal reasons.",
                 label="tab:cs-checks", align="lrrrrr")


def table_c02(D: dict) -> None:
    rows = []
    for h in HORIZONS:
        H = D["c02"][h]
        cells = [HORIZON_LABEL[h], f"{H['split']['holdout_events']}"]
        for rid in ("P1-scorecard", "P2a-l1", "P2b-pltr", "P3-ebm", "P4-lightgbm", "P4-xgboost"):
            cells.append(f4(H["rungs"][rid]["discrimination"]["auc"]))
        rows.append(cells)
    tbl(OUT / "credit-scoring-c02-auc.tex",
                 ["Horizon", "Holdout defaults", "Scorecard", "L1", "PLTR", "EBM", "LightGBM", "XGBoost"], rows,
                 caption="AUC of each method on the locked holdout of the Polish company bankruptcy files, by forecast horizon "
                         "and for the five files pooled with a horizon indicator, with the number of bankruptcies in each holdout.",
                 label="tab:cs-c02-auc", align="lrrrrrrr")
    rows = []
    for h in HORIZONS:
        H = D["c02"][h]
        cells = [HORIZON_LABEL[h]]
        for rid in CHALLENGERS:
            c = H["chal"][rid]
            cells.append(f"{signed(c['auc_diff'], 3)}" + ("$^{*}$" if c["delong_p_value"] < 0.05 else ""))
        flags = sum(int(r["overfit"]["flag"]) for r in H["rungs"].values())
        cells.append(f"{flags} of {len(H['rungs'])}")
        rows.append(cells)
    tbl(OUT / "credit-scoring-c02-diff.tex",
                 ["Horizon", "L1", "PLTR", "EBM", "LightGBM", "XGBoost", "Overfit flags"], rows,
                 caption="Paired AUC difference of each learned method against the scorecard on the Polish bankruptcy holdouts "
                         "(positive favours the learned method; a star marks a DeLong $p$ below 0.05) and the number of the seven fitted methods "
                         "whose train-minus-holdout AUC gap exceeds the 0.05 tolerance.",
                 label="tab:cs-c02-diff", align="lrrrrrr")


def table_c03(D: dict) -> None:
    rows = []
    for c in COHORTS:
        C = D["c03"][c]
        cells = [COHORT_LABEL[c], f"{C['training']['n_events']:,}"]
        for rid in ("P1-scorecard", "P2a-l1", "P2b-pltr", "P3-ebm", "P4-lightgbm"):
            r = C["rungs"][rid]
            cells.append(pm(r["auc"], r["auc_ci_low"], r["auc_ci_high"]))
        rows.append(cells)
    tbl(OUT / "credit-scoring-c03-auc.tex",
                 ["Test cohort", sh("Training", "charge-offs"), "Scorecard", "L1", "PLTR", "EBM", "LightGBM"], rows, size="footnotesize",
                 caption="AUC with its 95\\% interval of each method on the five approval cohorts of the SBA 7(a) loans, each "
                         "scored against the 5-year charge-off outcome with a model fitted only on approval years whose 5-year "
                         "mark closed before the cohort began.",
                 label="tab:cs-c03-auc", align="lrrrrrr")
    rows = []
    for c in COHORTS:
        for v in D["c03"][c]["vintages"]:
            rows.append([str(v["fiscal_year"]), f"{v['n']:,}", pct(v["observed_5y_pd"], 2), pct(v["predicted_5y_pd"], 2),
                         signed(100 * v["gap"], 2), f4(v["auc"])])
    tbl(OUT / "credit-scoring-c03-vintage.tex",
                 ["Approval year", "Loans", "Observed 5-year PD (\\%)", "Scorecard PD (\\%)", "Gap (points)", "AUC"], rows,
                 caption="Calibration of the scorecard by approval fiscal year on the SBA 7(a) loans: the observed 5-year charge-off "
                         "rate, the mean predicted 5-year PD of the scorecard fitted for that year's cohort, the gap in percentage "
                         "points and the AUC within the year.",
                 label="tab:cs-c03-vintage", align="lrrrrr")


def table_reject(D: dict) -> None:
    R = D["reject"]
    g = next(x for x in R["regimes"] if x["id"] == "moderate")
    rows = []
    for r in g["rungs"]:
        b = r["bias"]
        red = "--" if r["id"] in ("accepted-only",) else interval(r["reduction"]["value"], r["reduction"]["lo"], r["reduction"]["hi"], 1, 100.0)
        da = r["auc_vs_accepted_only"]
        rows.append([REJECT_NAME[r["id"]], interval(b["mean"], b["lo"], b["hi"], 2, 100.0), red,
                     "--" if r["id"] == "accepted-only" else interval(da["mean"], da["lo"], da["hi"], 4),
                     f4(r["auc"]["mean"]), f4(r["brier"]["mean"])])
    tbl(OUT / "credit-scoring-reject.tex",
                 ["Treatment", sh("Level bias", "(points)"), sh("Bias reduction", "(\\%)"), sh("$\\Delta$AUC vs", "accepted only"),
                  "AUC", "Brier"], rows, size="scriptsize",
                 caption="Reject inference on the German twin under the moderate private-signal policy: level bias of the mean PD "
                         "against the default rate of the accept-all population, its reduction against the accepted-only model, "
                         "the AUC change and the Brier score, each a mean over 100 repetitions with a 95\\% bootstrap interval.",
                 label="tab:cs-reject", align="lrrrrr", wide=False)
    rows = []
    for g in R["regimes"]:
        rr = {r["id"]: r for r in g["rungs"]}
        ao, pp = rr["accepted-only"], rr["parcelling-prudent"]
        best = max((r for r in g["rungs"] if r["id"] not in ("oracle", "accepted-only")), key=lambda r: r["reduction"]["value"])
        rows.append([f"{g['kappa']:g}", pct(g["default_rate"]["accepted"], 1), signed(100 * ao["bias"]["mean"], 2),
                     f4(ao["auc"]["mean"]), REJECT_NAME[best["id"]],
                     f"{pct(best['reduction']['value'], 1)} [{pct(best['reduction']['lo'], 1)}, {pct(best['reduction']['hi'], 1)}]",
                     f"{signed(100 * pp['bias']['mean'], 2)}"])
    tbl(OUT / "credit-scoring-reject-regimes.tex",
                 ["$\\kappa$", sh("Defaulters among", "accepted (\\%)"), sh("Accepted-only", "bias (points)"), sh("Accepted-only", "AUC"),
                  sh("Best", "treatment"), sh("Reduction (\\%)", "(95\\% CI)"), sh("Prudence-2", "bias (points)")], rows,
                 size="scriptsize",
                 caption="Reject inference across the four legacy policies of the German twin, ordered by the weight $\\kappa$ of "
                         "the underwriter's private signal: the accepted book, the accepted-only bias and AUC, the treatment with the "
                         "largest bias reduction and the bias of the prudence-2 parcelling.",
                 label="tab:cs-reject-regimes", align="rrrrlrr")


def main() -> None:
    D = derive()
    M = build_macros(D)
    M.write(OUT / "credit-scoring-numbers.tex")
    table_fit(D)
    table_points(D)
    table_c01_holdout(D)
    table_c01_variants(D)
    table_checks(D)
    table_c02(D)
    table_c03(D)
    table_reject(D)
    print(f"wrote {len(M.items)} macros and 11 tables to {OUT}")


if __name__ == "__main__":
    main()
