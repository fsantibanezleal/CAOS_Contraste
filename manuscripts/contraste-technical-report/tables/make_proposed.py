"""Tables and numbers of the section on the product's own contributions (sections/17-proposed.tex).

Every table and every number macro is computed from the committed documents of ``data/derived`` (cases C01, C03, C04, C11, C12,
C13, C15, C16, C17, C18, C22) and, for the sequential monitor on the C11 windows, from the installed engine ``riskvalidation``
1.1.0 applied to the committed exceedance days. The values that only the design document states (the SDD section on the
contributions beyond the practice) are the constants of ``SDD`` below, each with its line, so that no number of the section
is typed in the LaTeX. Output: ``tables/proposed-*.tex`` and ``tables/proposed-numbers.tex``.

Run from the repository root::

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/tables/make_proposed.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

OUT = HERE
EIGHT = ["null", "miscalibration", "clustering", "drift", "discrimination-decay", "leakage", "broken-monotonicity", "concentration"]
VARIANTS = ["none", "missing-basis", "stale-volatility", "wrong-correlation", "omitted-factor", "time-misalignment"]
VLABEL = {"none": "no deficiency", "missing-basis": "missing basis", "stale-volatility": "stale volatility",
          "wrong-correlation": "wrong correlation", "omitted-factor": "omitted factor", "time-misalignment": "time misalignment"}
WINDOWS = ["equity-2007-09", "fx-2008", "equity-2020", "rates-2022", "calm-2004-06", "mixed-2023"]
STRESS = ["equity-2007-09", "equity-2020", "rates-2022"]
MODEL_LABEL = {"hs-250": "HS-250", "garch-t": "GARCH-t", "fhs": "FHS"}

#: Values that the design document states and the committed artifacts do not recompute here (SDD = docs/design/SDD.md).
SDD = {
    "oneRegCerepLong": ("26.64", "SDD.md section on contributions beyond the practice, the entry on the default definition"),
    "oneRegTransLong": ("8.61", "same entry"),
    "fourRwBefore": ("58.0", "same entry"),
    "fourRwAfter": ("47.5", "same entry"),
    "twoPrinted": ("413", "SDD.md, the entry on reconciliations"),
    "twoReproduced": ("296", "same entry"),
    "twoGridCases": ("36", "same entry"),
    "sevenSingleLow": ("6.8", "SDD.md, the entry on the UF"),
    "sevenSingleHigh": ("8.8", "same entry"),
    "sevenEveLow": ("10", "same entry"),
    "sevenEveHigh": ("27", "same entry"),
    "eightRedDates": ("2", "SDD.md, the entry on the behavioural test"),
    "tenBinomLow": ("0.1587", "SDD.md, the entry on the batch 3 corrections"),
    "tenBinomHigh": ("0.3893", "same entry"),
    "tenBetaBin": ("0.044", "same entry"),
    "tenFixedFive": ("0.2000", "same entry"),
    "tenFixedTen": ("0.0833", "same entry"),
    "tenPerm": ("0.0667", "same entry"),
    "tenCutTenth": ("0.0850", "same entry"),
    "tenCutFifth": ("0.0150", "same entry"),
    "elevenSvb": ("0.1708", "SDD.md, the entry on reverse liquidity stress"),
    "twelveRedRows": ("92", "SDD.md, the entry on the instability of the operational-risk capital"),
    "twelveInfLow": ("27", "same entry"),
    "twelveInfHigh": ("34", "same entry"),
    "twelveFiniteLow": ("9", "same entry"),
    "twelveFiniteHigh": ("27", "same entry"),
    "fiveWeighted": ("2.68", "SDD.md ladder row on the IFRS 9 engine"),
    "fiveAverage": ("1.80", "same row"),
}


def D(rel: str):
    d = figkit.doc(rel)
    return d.get("outputs") or d


def pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}"


def wilson_str(r: dict) -> str:
    return f"{pct(r['rate'])} ({pct(r['ci_low'])} to {pct(r['ci_high'])})"


def yn(b: bool) -> str:
    return "yes" if b else "no"


# ----------------------------------------------------------------------------------------------------------------- data
def load() -> dict:
    A: dict = {}
    # BS-1: the measurement of C22
    rows, fam = [], {}
    for f in EIGHT:
        o = D(f"C22/{f}.json")
        sims = [s for s in o["simulations"] if not s.get("study")]
        fam[f] = sims
        rows += sims
        if f == "null":
            A["size_bounds"] = o["size_bounds"]
            seen, tests = set(), []
            for s in sims:
                if s["test_id"] not in seen:
                    seen.add(s["test_id"])
                    tests.append(s)
            A["size_tests"] = tests
    A["c22_family"] = fam
    A["c22_rows"] = rows
    leak = D("C22/leakage.json")["simulations"]
    A["leak"] = {(s["test_id"], s["severity"]): s["rates"]["p<0.05"] for s in leak}
    # BS-2: the reconciliation with ORE
    A["ore"] = {}
    for v in ["single-swap", "netting-set", "csa-mpor-10d", "csa-mpor-20d", "with-im"]:
        A["ore"][v] = D(f"C12/{v}.json")["ore_reconciliation"]
    # BS-4
    w = D("C04/withdrawals.json")
    A["wd"] = w
    A["thin"] = D("C04/thin.json")
    # BS-7, BS-9, BS-11, BS-12
    A["short_uf"] = D("C15/short-uf.json")
    A["long_uf"] = D("C15/long-uf.json")
    A["band"] = D("C18/baseline.json")["aggregation"]["band"]
    A["rev"] = D("C16/reverse-stress.json")
    A["c17"] = {x: D(f"C17/{x}.json") for x in ["xi-0-6", "xi-0-8", "xi-0-96", "xi-1-1"]}
    # BS-13
    A["c13"] = {v: D(f"C13/{v}.json") for v in VARIANTS}
    # BS-14
    A["sp"] = D("C04/sp.json")
    # BS-15
    A["seq"] = D("C22/other-families.json")["sequential"]
    A["c03"] = {x: D(f"C03/{x}.json") for x in ["fy2006-07", "fy2008-10", "fy2011-14", "fy2015-17", "fy2018-20"]}
    A["c11"] = {x: D(f"C11/{x}.json") for x in WINDOWS}
    return A


# ------------------------------------------------------------------------------------------------- sequential on C11
def c11_eprocess(A: dict) -> list[dict]:
    """The rate e-process of the engine (``var_hit_eprocess``, defaults) on the committed exceedance days of every model, per
    window, against the Basel traffic light (first day on which the trailing 250 days hold 5 or more exceptions)."""
    from riskvalidation.validation.sequential import var_hit_eprocess

    out = []
    for wid in WINDOWS:
        doc = A["c11"][wid]
        n = doc["window"]["n_forecast_days"]
        rec = {"window": wid, "days": n, "models": 0, "light": 0, "eproc": 0, "e_days": [], "l_days": [], "both": 0}
        for m in doc["models"]:
            lv = [x for x in m["by_level"] if abs(x["alpha"] - 0.01) < 1e-12]
            if not lv:
                continue
            ex = lv[0]["exceedance_days"]
            assert all(0 <= d < n for d in ex), (wid, m["model_id"])
            hits = np.zeros(n, dtype=int)
            hits[ex] = 1
            rec["models"] += 1
            res = var_hit_eprocess(hits, 0.01)
            e_day = res.rejection_time if res.rejected else None
            csum = np.concatenate([[0], np.cumsum(hits)])
            l_day = None
            for t in range(250, n + 1):
                if csum[t] - csum[t - 250] >= 5:
                    l_day = t
                    break
            if e_day is not None:
                rec["eproc"] += 1
                rec["e_days"].append(e_day)
            if l_day is not None:
                rec["light"] += 1
                rec["l_days"].append(l_day)
            if e_day is not None and l_day is not None:
                rec["both"] += 1
        out.append(rec)
    return out


def med(xs):
    return float(np.median(xs)) if xs else None


# --------------------------------------------------------------------------------------------------------------- build
def build() -> dict:
    A = load()
    N: dict[str, str] = {}

    def put(k, v):
        N[k] = str(v)

    # ---- BS-1
    rows = A["c22_rows"]
    put("oneSims", len(rows))
    put("oneReps", f"{sum(s['n_rep'] for s in rows):,}")
    put("oneRates", sum(len(s["rates"]) for s in rows))
    put("oneExact", sum(1 for s in rows if s.get("exact")))
    put("oneGens", len({s["generator"] for s in rows if s.get("generator")}))
    put("oneFamilies", len(EIGHT))
    tests = A["size_tests"]
    b05 = A["size_bounds"]["p<0.05"]
    put("oneTests", len(tests))
    put("oneBound", f"{100 * b05:.2f}")
    over = [s for s in tests if s["rates"]["p<0.05"]["rate"] > b05]
    put("oneOver", len(over))
    put("oneOverName", figkit.tex_escape(over[0]["test_id"]) if over else "none")
    put("oneOverRate", pct(over[0]["rates"]["p<0.05"]["rate"], 2) if over else "0")
    put("oneNullReps", f"{tests[0]['n_rep']:,}")
    lk = A["leak"]
    put("oneLeakAucOne", pct(lk[("disc.auc_vs_initial", 1)]["rate"], 1))
    put("oneLeakAucTwo", pct(lk[("disc.auc_vs_initial", 2)]["rate"], 1))
    put("oneLeakCsiFive", pct(lk[("stability.csi", 5)]["rate"], 1))
    put("oneLeakCsiOne", pct(lk[("stability.csi", 1)]["rate"], 1))
    put("oneLeakReps", f"{lk[('disc.auc_vs_initial', 1)]['n']:,}")
    # ---- BS-2
    for v, key in [("single-swap", "Single"), ("netting-set", "Netting"), ("csa-mpor-10d", "CsaTen"), ("csa-mpor-20d", "CsaTwenty"),
                   ("with-im", "Im")]:
        r = A["ore"][v]
        ag = r["agreement"]
        put(f"two{key}Dates", len(ag))
        put(f"two{key}Out", sum(1 for x in ag if not x["within_two_se"]))
        put(f"two{key}Max", f"{max(abs(x['difference']) / x['combined_se'] for x in ag):.1f}")
        put(f"two{key}Eepe", f"{abs(r['eepe_agreement']['difference']) / r['eepe_agreement']['combined_se']:.2f}")
        put(f"two{key}Cva", f"{abs(r['cva_agreement']['difference']) / r['cva_agreement']['combined_se']:.2f}")
    put("twoOreVersion", A["ore"]["single-swap"]["ore_version"])
    put("twoOreSamples", "10,000")
    # ---- BS-4
    wd = A["wd"]
    r9 = [r for r in wd["rungs"] if r["value"] == 9.0][0]
    ib = 5  # grade B
    tr = r9["pd_latent"]["truth"][ib] if "truth" in r9["pd_latent"] else None
    truth = wd["rungs"][0]["pd_removed"]["truth"][ib]
    put("fourTruthB", pct(truth, 2))
    for k, nm in [("pd_removed", "Removed"), ("pd_kept", "Kept"), ("pd_followed", "Followed")]:
        put(f"four{nm}B", f"{100 * (r9[k]['mean'][ib] - truth) / truth:.0f}")
    r0 = wd["rungs"][0]
    put("fourRemovedZero", f"{100 * (r0['pd_removed']['mean'][ib] - truth) / truth:+.0f}")
    thin = A["thin"]["rungs"][0]
    put("fourThinN", thin["value"])
    put("fourWaldAaa", pct(thin["coverage"]["wald"][0], 2))
    put("fourJeffAaa", pct(thin["coverage"]["jeffreys"][0], 1))
    # ---- BS-7
    su = A["short_uf"]
    put("sevenCharge", f"{su['indexation_charge']['charge']:,.1f}")
    put("sevenShare", pct(su["indexation_charge"]["charge"] / su["nii"]["delta_nii"], 1))
    put("sevenFloorBp", f"{min(d['distance_bp'] for d in su['floors']['distances'] if d['leg'] != 'CLP'):.2f}")
    # ---- BS-9
    band = A["band"]
    sums = {(r["method"], r["nu"]): r["capital_clp_m"] for r in band}
    put("nineSum", f"{sums[('simple-sum', None)]:,.0f}")
    put("nineLower", f"{sums[('lower-bound', None)]:,.0f}")
    put("nineWorst", f"{sums[('worst-case', None)]:,.0f}")
    put("nineGauss", f"{sums[('gaussian-copula', None)]:,.0f}")
    put("nineVc", f"{sums[('variance-covariance', None)]:,.0f}")
    put("nineTfour", f"{sums[('t-copula', 4.0)]:,.0f}")
    put("nineRows", len(band))
    put("nineWorstRatio", f"{sums[('worst-case', None)] / sums[('simple-sum', None)]:.2f}")
    put("nineGaussRatio", f"{sums[('gaussian-copula', None)] / sums[('simple-sum', None)]:.2f}")
    # ---- BS-11
    for b in A["rev"]["bases"]:
        s = b["solved"]
        key = {"list-adverse": "Adverse", "list-extreme": "Extreme", "fast-run": "Fast"}[b["base_id"]]
        put(f"eleven{key}", f"{s['multiplier']:.6f}" if s["status"] == "solved" else "refused")
        put(f"eleven{key}Day", b["base_survival"]["day"] if b["base_survival"]["day"] else b["base_survival"]["horizon_days"])
    put("elevenTarget", A["rev"]["target"]["days"])
    put("elevenCapAdverse", f"{[b for b in A['rev']['bases'] if b['base_id'] == 'list-adverse'][0]['max_multiplier']:.1f}")
    # ---- BS-12
    cells = []
    for tag, doc in A["c17"].items():
        for c in doc["cells"]:
            cells.append((doc["tail_index"], c))
    iqr = [c["capital"]["lda_splice"]["iqr_over_truth"] for _, c in cells if c["capital"]["lda_splice"]]
    put("twelveCells", len(cells))
    put("twelveHistories", f"{sum(c['replications']['n_replications'] for _, c in cells):,}")
    put("twelveIqrMin", f"{min(iqr):.2f}")
    put("twelveIqrMax", f"{max(iqr):.2f}")
    # ---- BS-13
    c13 = A["c13"]
    stale = c13["stale-volatility"]["pla_complement"]
    h = stale["hypothesis"]
    put("thirteenN", stale["n_replications"])
    put("thirteenNull", f"{stale['calibration']['n_null']:,}")
    put("thirteenWindow", stale["window_days"])
    put("thirteenPower", wilson_str(h["measured_power"]))
    put("thirteenPowerRate", pct(h["measured_power"]["rate"]))
    put("thirteenHeld", pct(h["held_out_size"]["rate"]))
    put("thirteenHeldCi", f"{pct(h['held_out_size']['ci_low'], 2)} to {pct(h['held_out_size']['ci_high'], 2)}")
    put("thirteenPla", pct(h["pla_power"]["rate"]))
    put("thirteenThresholdPower", pct(h["power_threshold"], 0))
    put("thirteenRefuted", pct(h["refuted_below"], 0))
    put("thirteenSize", pct(h["size_limit"], 0))
    thr = stale["calibration"]["thresholds_family"]
    put("thirteenWaldCut", f"{thr['wald']:.3f}")
    put("thirteenAbsCut", f"{thr['spearman_abs']:.4f}")
    put("thirteenRollCut", f"{thr['spearman_roll']:.4f}")
    thr1 = stale["calibration"]["thresholds_per_statistic"]
    put("thirteenWaldCutOne", f"{thr1['wald']:.3f}")
    put("thirteenAbsCutOne", f"{thr1['spearman_abs']:.4f}")
    put("thirteenRollCutOne", f"{thr1['spearman_roll']:.4f}")
    put("thirteenKsFlag", stale["against_ks"]["ks_flagged"])
    put("thirteenWaldFlag", stale["against_ks"]["wald_flagged"])
    put("thirteenMisalignRoll", pct(c13["time-misalignment"]["pla_complement"]["flags"]["per_statistic"]["spearman_roll"]["rate"]))
    put("thirteenMisalignPla", pct(c13["time-misalignment"]["detection"]["share_amber_or_red"], 1))
    put("thirteenWrongRoll", pct(c13["wrong-correlation"]["pla_complement"]["flags"]["per_statistic"]["spearman_roll"]["rate"]))
    put("thirteenWrongPla", pct(c13["wrong-correlation"]["detection"]["share_amber_or_red"], 1))
    put("thirteenNullUnion", pct(c13["none"]["pla_complement"]["flags"]["family"]["any"]["rate"]))
    put("thirteenMissingWald", pct(c13["missing-basis"]["pla_complement"]["flags"]["per_statistic"]["wald"]["rate"]))
    put("thirteenMissingPla", pct(c13["missing-basis"]["detection"]["share_amber_or_red"], 1))
    put("thirteenMissingAbs", pct(c13["missing-basis"]["pla_complement"]["flags"]["per_statistic"]["spearman_abs"]["rate"]))
    lag = {x["lag_days"]: x for x in stale["lag_ladder"]}
    for L_ in (5, 10, 20, 40):
        put(f"thirteenLag{ {5: 'Five', 10: 'Ten', 20: 'Twenty', 40: 'Forty'}[L_] }", pct(lag[L_]["per_statistic"]["spearman_roll"]["rate"]))
        put(f"thirteenLagPla{ {5: 'Five', 10: 'Ten', 20: 'Twenty', 40: 'Forty'}[L_] }", pct(lag[L_]["pla_amber_or_red"]["rate"]))
    th = c13["none"]["pla"]["thresholds"]
    put("thirteenSpGreen", f"{th['spearman_green']}")
    put("thirteenSpRed", f"{th['spearman_red']}")
    put("thirteenKsGreen", f"{th['ks_green']}")
    put("thirteenKsRed", f"{th['ks_red']}")
    put("thirteenPlaDays", th["window_days"])
    kd = c13["stale-volatility"]["known_deficiency"]["parameters"][0]
    put("thirteenVolLag", f"{kd['value']:.0f}")
    put("thirteenFactors", c13["stale-volatility"]["generator"]["n_risk_factors"])
    put("thirteenNullSeeds", len(stale["calibration"]["null_case_seeds"]))
    put("thirteenNullBlock", f"{stale['calibration']['n_per_block']:,}")
    put("thirteenSeedBase", c13["stale-volatility"]["generator"]["seed_base"])
    # ---- BS-14
    bv = wd["bounds_verdict"]
    put("fourteenExitRate", pct(wd["rungs"][0]["withdrawal_rate"], 0))
    put("fourteenYears", wd["design"]["years"])
    cov = {}
    for r in bv["rows"]:
        cov[(r["design"], r["informative"], r["treatment"])] = r
    put("fourteenReps", bv["reps"])
    put("fourteenAnchoredOne", pct(cov[("first_year", 1.0, "anchored")]["value"]))
    put("fourteenAnchoredThree", pct(cov[("first_year", 3.0, "anchored")]["value"]))
    put("fourteenAnchoredNine", pct(cov[("first_year", 9.0, "anchored")]["value"]))
    put("fourteenIndustryNine", pct(cov[("first_year", 9.0, "industry")]["value"]))
    put("fourteenIndustryPooled", pct(cov[("pooled", 9.0, "industry")]["value"]))
    put("fourteenUnfollowedPooled", pct(cov[("pooled", 9.0, "unfollowed")]["value"]))
    put("fourteenFollowedPooled", pct(cov[("pooled", 9.0, "followed")]["value"]))
    put("fourteenIndustryTen", pct(cov[("first_year_x10", 9.0, "industry")]["value"]))
    put("fourteenUnfollowedTen", pct(cov[("first_year_x10", 9.0, "unfollowed")]["value"]))
    put("fourteenCoverTarget", pct(bv["rows"][0]["threshold"], 0))
    put("fourteenExistingTarget", pct([r for r in bv["rows"] if r["id"] == "existing-coverage"][0]["threshold"], 0))
    grades = {g["grade"]: g for g in A["sp"]["withdrawal_bounds"]["grades"]}
    ccc = grades["CCC-C"]
    put("fourteenCccK", f"{ccc['pooled']['k']:.1f}")
    put("fourteenCccLow", f"{ccc['pooled']['k_low']:.1f}")
    put("fourteenCccHigh", f"{ccc['pooled']['k_high']:.1f}")
    put("fourteenCccShare", pct(ccc["stability"]["share_cohorts_containing_pooled_k"], 0))
    put("fourteenStability", pct(A["sp"]["withdrawal_bounds"]["stability_share"], 0))
    put("fourteenBK", f"{grades['B']['pooled']['k']:.1f}")
    put("fourteenBShare", pct(grades["B"]["stability"]["share_cohorts_containing_pooled_k"], 0))
    put("fourteenBTruth", pct(truth, 2))
    # ---- BS-15
    seq = A["seq"]
    sc = {s["id"]: s for s in seq["hits"]["scenarios"]}
    put("fifteenThreshold", f"{seq['method']['threshold']:.0f}")
    put("fifteenAlpha", pct(seq["method"]["alpha_level"], 0))
    put("fifteenReps", f"{seq['hits']['reps']:,}")
    put("fifteenHorizon", f"{seq['hits']['horizon']:,}")
    put("fifteenWindow", seq["hits"]["window"])
    put("fifteenENull", pct(sc["null"]["e_rate"]["ever"]))
    put("fifteenKupTrail", pct(sc["null"]["kupiec_trailing"]["ever"]))
    put("fifteenKupCum", pct(sc["null"]["kupiec_cumulative"]["ever"]))
    put("fifteenLightNull", pct(sc["null"]["traffic_light"]["ever"]))
    put("fifteenXThreeDay", f"{sc['rate-x3']['e_rate']['median_day']:.0f}")
    put("fifteenXFourDay", f"{sc['rate-x4']['e_rate']['median_day']:.0f}")
    put("fifteenXThreeKupDay", f"{sc['rate-x3']['kupiec_cumulative']['median_day']:.0f}")
    put("fifteenXFourKupDay", f"{sc['rate-x4']['kupiec_cumulative']['median_day']:.0f}")
    put("fifteenLightDay", f"{sc['rate-x3']['traffic_light']['median_day']:.0f}")
    hyp = {x["id"]: x for x in seq["hypotheses"]}
    vals = {x["id"]: x["value"] for h_ in seq["hypotheses"] for x in h_["values"]}
    put("fifteenCostThree", f"{100 * vals['x3_power_cost']:.1f}")
    put("fifteenCostFour", f"{100 * vals['x4_power_cost']:.1f}")
    put("fifteenBound", pct(vals["bound"]))
    put("fifteenHeld", "H1 and H2 held" if hyp["H1"]["holds"] and hyp["H2"]["holds"] else "see table")
    pdg = {s["id"]: s for s in seq["pd_grades"]["scenarios"]}
    put("fifteenPdNullProduct", pct(pdg["pd-x1"]["e_product"]["ever"]))
    put("fifteenPdNullAverage", pct(pdg["pd-x1"]["e_average"]["ever"]))
    put("fifteenPdNullChi", pct(pdg["pd-x1"]["chi2_every_year"]["ever"]))
    put("fifteenPdTenProduct", pct(pdg["pd-x1.1"]["e_product"]["ever"]))
    put("fifteenPdTenAverage", pct(pdg["pd-x1.1"]["e_average"]["ever"]))
    put("fifteenPdFiveAverage", pct(pdg["pd-x1.05"]["e_average"]["ever"]))
    put("fifteenPdFiveChi", pct(pdg["pd-x1.05"]["chi2_one_shot_power"]))
    put("fifteenPdYears", seq["pd_grades"]["years"])
    c11e = c11_eprocess(A)
    A["c11e"] = c11e
    byw = {r["window"]: r for r in c11e}
    put("fifteenCeSevenFlag", byw["equity-2007-09"]["eproc"])
    put("fifteenCeSevenLight", byw["equity-2007-09"]["light"])
    put("fifteenCeSevenModels", byw["equity-2007-09"]["models"])
    put("fifteenCeSevenDay", f"{med(byw['equity-2007-09']['e_days']):.0f}")
    put("fifteenCeFxFlag", byw["fx-2008"]["eproc"])
    put("fifteenCeFxLight", byw["fx-2008"]["light"])
    put("fifteenCeFxDay", f"{med(byw['fx-2008']['e_days']):.0f}")
    put("fifteenCeFxLightDay", f"{med(byw['fx-2008']['l_days']):.0f}")
    c03rej = []
    for tag, d in A["c03"].items():
        sq = d["sequential"]
        c03rej.append((tag, sq["average"]["rejection_month"], sq["average"]["max_log_e"]))
    put("fifteenCzeroRejected", sum(1 for _, m, _ in c03rej if m is not None))
    put("fifteenCzeroCohorts", len(c03rej))
    # ---- BS-16
    cf = A["c11"]["equity-2007-09"]["conformal"]
    hy = cf["hypothesis"]
    put("sixteenGamma", f"{cf['method']['gamma']}")
    put("sixteenBandLow", f"{cf['method']['level_min']}")
    put("sixteenBandHigh", f"{cf['method']['level_max']}")
    put("sixteenCells", hy["n_cells"])
    put("sixteenCellsHold", hy["n_cells_hold"])
    put("sixteenFzTol", pct(hy["run"]["fz0_tolerance"], 0))
    put("sixteenStressDays", hy["run"]["n_stress_days"])
    put("sixteenRuns", hy["run"]["n_runs"])
    extra = sum(c["extra_windows"] for c in hy["cells"])
    put("sixteenExtra", extra)
    worst = max(c["worst_fz0_change"] for c in hy["cells"])
    put("sixteenWorstFz", pct(worst, 1))
    ind = [x["independence_p"] for x in hy["independence_2007_09"]]
    put("sixteenIndMin", f"{min(ind):.3f}")
    put("sixteenIndFails", sum(1 for x in hy["independence_2007_09"] if x["fails"]))
    r_hs = [r for r in cf["rows"] if r["model_id"] == "hs-250" and abs(r["alpha"] - 0.01) < 1e-12][0]
    put("sixteenHsHitUn", f"{r_hs['unwrapped']['hit_rate']:.3f}")
    put("sixteenHsHitWr", f"{r_hs['wrapped']['hit_rate']:.3f}")
    put("sixteenHsFz", pct(r_hs["fz0_change"], 1))
    put("sixteenHsClipped", r_hs["n_clipped"])
    put("sixteenHsKupUn", f"{r_hs['unwrapped']['kupiec_p']:.1e}")
    put("sixteenHsKupWr", f"{r_hs['wrapped']['kupiec_p']:.3f}")
    rows20 = [r for r in A["c11"]["equity-2020"]["conformal"]["rows"] if r["model_id"] == "hs-250" and abs(r["alpha"] - 0.01) < 1e-12][0]
    put("sixteenTwentyHsFz", pct(rows20["fz0_change"], 1))
    put("sixteenTwentyHsPassWr", yn(rows20["wrapped"]["passes_coverage"]))
    # ---- BS-5 and BS-6 (read here from the committed provisions and portfolio documents)
    c06 = D("C06/rd-2008-12.json")
    nl = c06["non_linearity"]
    put("fiveTolerance", "10^{-%d}" % round(-np.log10(c06["reconciliation"]["tolerance"])))
    put("fiveMaxResidual", f"{max(abs(a['residual']) for a in c06['reconciliation']['allowance']):.1e}")
    put("fivePdWeighted", f"{100 * nl['pd_weighted']:.3f}")
    put("fivePdMean", f"{100 * nl['pd_at_mean_z']:.3f}")
    put("fiveEclWeighted", f"{nl['ecl_weighted'] / 1e6:,.1f}")
    put("fiveEclMean", f"{nl['ecl_at_mean_path'] / 1e6:,.1f}")
    put("fiveIndex", f"{100 * nl['index']:.2f}")
    put("fiveRho", f"{nl['parameters']['rho']}")
    c07 = D("C07/base.json")
    reg = {r["regime"]: r for r in c07["regimes"]}
    put("fiveCmf", f"{reg['cmf-b1']['total_provision'] / 1e9:,.1f}")
    put("fiveIfrs", f"{reg['ifrs9']['total_provision'] / 1e9:,.1f}")
    put("fiveBde", f"{reg['bde-annex9']['total_provision'] / 1e9:,.1f}")
    put("fiveCmfCov", pct(reg["cmf-b1"]["coverage_rate"], 2))
    put("fiveIfrsCov", pct(reg["ifrs9"]["coverage_rate"], 2))
    put("fiveBdeCov", pct(reg["bde-annex9"]["coverage_rate"], 2))
    put("fiveScenarios", len([x for x in ["base", "combined-severe", "consumer-arrears-shock", "house-price-fall", "recession", "uf-inflation-spike"]]))
    steps = {x["id"]: x["amount"] for x in c07["gap_bridge"]["steps"]}
    put("fiveBridgeBasis", f"{steps['measurement-basis'] / 1e9:,.1f}")
    put("fiveBridgeLife", f"{steps['lifetime-horizon'] / 1e9:,.1f}")
    put("fiveBridgeForward", f"{steps['forward-looking'] / 1e9:,.1f}")
    put("fiveBridgeDisc", f"{steps['discounting'] / 1e9:,.1f}")
    put("fiveBridgeOverlay", f"{steps['ifrs9-overlays'] / 1e9:,.1f}")
    gap = [x for x in A["sp"]["definition_gap"]["d4_over_d2"] if x is not None]
    put("fourGapMin", pct(min(gap), 0))
    put("fourGapMax", pct(max(gap), 0))
    g22 = D("C10/grid-22.json")
    c0 = g22["cells"][0]
    est = {e["estimator"]: e for e in c0["estimators"]}
    put("sixRhoKnown", c0["known_rho"])
    put("sixYears", c0["series_length_years"])
    put("sixReps", c0["n_replications"])
    put("sixMlBias", f"{est['maximum-likelihood']['bias']:.4f}")
    put("sixMlRmse", f"{est['maximum-likelihood']['rmse']:.4f}")
    put("sixMlCov", pct(est["maximum-likelihood"]["coverage"], 1))
    put("sixMomCov", pct(est["moments"]["coverage"], 1))
    put("sixMomRmse", f"{est['moments']['rmse']:.4f}")
    put("sixPd", g22["generator"]["known_pd"])
    # SDD constants
    for k, (v, _) in SDD.items():
        put(k, v)
    A["N"] = N
    return A


# --------------------------------------------------------------------------------------------------------------- write
def write_numbers(N: dict) -> None:
    lines = ["% Generated by tables/make_proposed.py from data/derived; do not edit.", ""]
    for k, v in sorted(N.items()):
        lines.append(f"\\newcommand{{\\px{k[0].upper() + k[1:]}}}{{{v}}}")
    (OUT / "proposed-numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_tables(A: dict) -> None:
    # --- summary of the twelve measurements
    N = A["N"]
    T = OUT
    figkit.table(T / "proposed-summary.tex", ["Method", "Case", "Quantity measured", "Value"], [
        ["Size and power of the tests", "C22", "tests of the null family within the one-sided size bound at 5\\%",
         f"{len(A['size_tests']) - int(N['oneOver'])} of {N['oneTests']}"],
        ["Reconciliation with ORE", "C12", "single swap, dates within two combined standard errors",
         f"{int(N['twoSingleDates']) - int(N['twoSingleOut'])} of {N['twoSingleDates']}"],
        ["Reconciliation with ORE", "C12", "CSA with 10 days, dates within two combined standard errors",
         f"{int(N['twoCsaTenDates']) - int(N['twoCsaTenOut'])} of {N['twoCsaTenDates']}"],
        ["Informative withdrawals", "C04", "relative error of the B probability of default, withdrawals removed, k = 9 (\\%)",
         N["fourRemovedB"]],
        ["Thin grades", "C04", "coverage of the Wald interval for the first grade at 50 obligors (\\%)", N["fourWaldAaa"]],
        ["UF as its own currency", "C15", "indexation charge over the change in net interest income, short-UF variant (\\%)",
         N["sevenShare"]],
        ["Dependence band", "C18", "worst-case capital over the simple sum", N["nineWorstRatio"]],
        ["Reverse liquidity stress", "C16", "run-off multiplier at the 30-day target, adverse base", N["elevenAdverse"]],
        ["Reverse liquidity stress", "C16", "fast-run base", N["elevenFast"]],
        ["Operational-risk instability", "C17", "interquartile range over the truth, splice rung, range over the cells",
         f"{N['twelveIqrMin']} to {N['twelveIqrMax']}"],
    ], caption="The headline quantity of each measurement, protocol and reconciliation of this section, read from the committed "
               "documents of the case named in the second column; the sections of each method give the design and the full results.",
        label="tab:proposed-summary", align="lllr")

    # --- reconciliation with ORE
    ore_rows = []
    nm = {"single-swap": "Single swap", "netting-set": "Four-swap netting set", "csa-mpor-10d": "CSA, 10 days",
          "csa-mpor-20d": "CSA, 20 days", "with-im": "CSA with initial margin"}
    for v, r in A["ore"].items():
        ag = r["agreement"]
        out = sum(1 for x in ag if not x["within_two_se"])
        ore_rows.append([nm[v], f"{len(ag) - out} of {len(ag)}", f"{max(abs(x['difference']) / x['combined_se'] for x in ag):.1f}",
                         f"{abs(r['eepe_agreement']['difference']) / r['eepe_agreement']['combined_se']:.2f}",
                         f"{abs(r['cva_agreement']['difference']) / r['cva_agreement']['combined_se']:.2f}"])
    figkit.table(T / "proposed-ore.tex", ["Variant", "Dates within 2 SE", "Largest EE gap (SE)", "EEPE gap (SE)", "CVA gap (SE)"], ore_rows,
                 caption="Agreement of the engine's exposure profile with the Open Source Risk Engine on case C12: the number of the "
                         "33 report dates at which the expected exposure lies within two combined Monte Carlo standard errors, and the "
                         "largest gap of the profile, of the effective expected positive exposure and of the credit valuation adjustment, "
                         "each in combined standard errors.", label="tab:proposed-ore", align="lrrrr")

    # --- BS-13
    rows = []
    for v in VARIANTS:
        d = A["c13"][v]
        ps = d["pla_complement"]["flags"]["per_statistic"]
        fam = d["pla_complement"]["flags"]["family"]["any"]
        rows.append([VLABEL[v], pct(d["detection"]["share_amber_or_red"]), pct(ps["wald"]["rate"]), pct(ps["spearman_abs"]["rate"]),
                     pct(ps["spearman_roll"]["rate"]), wilson_str(fam)])
    figkit.table(T / "proposed-pla.tex", ["Variant", "Regulatory zone", "Wald", "Absolute Spearman", "Rolling Spearman", "Union at 1\\% (95\\% interval)"],
                 rows, caption="Share of the 1,000 replications of each C13 variant flagged, in percent: by the regulatory attribution test (amber or "
                               "red), by each of the three statistics of the complement at 1\\% per statistic, and by their union at a family size of "
                               "1\\% with its Wilson interval.", label="tab:proposed-pla", align="lrrrrr")
    lag = {x["lag_days"]: x for x in A["c13"]["stale-volatility"]["pla_complement"]["lag_ladder"]}
    rows = [[f"{L}", pct(lag[L]["pla_amber_or_red"]["rate"]), pct(lag[L]["per_statistic"]["wald"]["rate"]),
             pct(lag[L]["per_statistic"]["spearman_abs"]["rate"]), pct(lag[L]["per_statistic"]["spearman_roll"]["rate"]),
             pct(lag[L]["family_any"]["rate"])] for L in (5, 10, 20, 40)]
    figkit.table(T / "proposed-lag.tex", ["Lag (days)", "Regulatory zone", "Wald", "Absolute Spearman", "Rolling Spearman", "Union (family 1\\%)"], rows,
                 caption="Share of 1,000 replications flagged, in percent, when the risk model scales the day's shocks with a volatility that is "
                         "5, 10, 20 and 40 days old: the regulatory attribution test and the statistics of the complement.",
                 label="tab:proposed-lag", align="rrrrrr")

    # --- BS-14
    bv = A["wd"]["bounds_verdict"]["rows"]
    cov = {(r["design"], r["informative"], r["treatment"]): r for r in bv}
    dl = {"first_year": "first-year cohort", "pooled": "five cohorts pooled", "first_year_x10": "first year, ten times the cohort"}
    rows = []
    for dsg in ["first_year", "pooled", "first_year_x10"]:
        for k in (1.0, 3.0, 9.0):
            cells = []
            for tr in ["industry", "unfollowed", "followed", "anchored"]:
                r = cov.get((dsg, k, tr))
                cells.append("--" if r is None else f"{pct(r['value'])} $\\pm$ {100 * 1.96 * r['mcse']:.1f}")
            if all(c == "--" for c in cells):
                continue
            rows.append([dl[dsg], f"{k:.0f}"] + cells)
    figkit.table(T / "proposed-anchored.tex", ["Design", "Informativeness $k$", "Industry", "Unfollowed", "Followed", "Anchored"], rows,
                 caption="Coverage in percent, with a 95\\% Monte Carlo half-width, of the true one-year probability of default of the B grade by the "
                         "interval of each treatment of rating withdrawals over 200 repetitions of the rating-path generator; a dash marks a "
                         "design and informativeness that the evaluation did not run.", label="tab:proposed-anchored", align="llrrrr")
    sp = A["sp"]["withdrawal_bounds"]["grades"]
    rows = []
    for g in sp:
        p = g["pooled"]
        if p.get("k") is None:
            continue
        rows.append([g["grade"], f"{p['k']:.1f}", f"{p['k_low']:.1f} to {p['k_high']:.1f}", g["stability"]["usable_cohorts"],
                     g["stability"]["cohorts_containing_pooled_k"], yn(g["stability"]["stable"])])
    figkit.table(T / "proposed-realk.tex", ["Grade", "Pooled $k$", "Band", "Usable cohorts", "Cohorts containing it", "Stable"], rows,
                 caption="The anchored odds multiplier of withdrawal in the year of default, by grade, from the 26 annual cohorts of the S\\&P "
                         "transition and default pages of case C04: the pooled value, its band, and the number of cohorts whose band contains "
                         "the pooled value.", label="tab:proposed-realk", align="lrrrrr")

    # --- BS-15
    seq = A["seq"]
    rows = []
    lbl = {"null": "right model", "rate-x2": "rate 2 times", "rate-x3": "rate 3 times", "rate-x4": "rate 4 times",
           "cluster-0.1": "clustering 0.1", "cluster-0.2": "clustering 0.2", "cluster-0.4": "clustering 0.4"}

    def md(x):
        return "--" if x is None else f"{x:.0f}"
    for s in seq["hits"]["scenarios"]:
        rows.append([lbl[s["id"]], pct(s["e_rate"]["ever"]), md(s["e_rate"]["median_day"]), pct(s["kupiec_trailing"]["ever"]),
                     pct(s["kupiec_cumulative"]["ever"]), md(s["kupiec_cumulative"]["median_day"]), pct(s["traffic_light"]["ever"]),
                     md(s["traffic_light"]["median_day"])])
    figkit.table(T / "proposed-sequential.tex", ["Scenario", "E-process ever", "day", "Kupiec trailing ever", "Kupiec cumulative ever", "day", "Light ever", "day"],
                 rows, caption="Share of 2,000 simulated 1,000-day series in which each reading of the 99\\% VaR back-test rejects at some day "
                               "(in percent) and the median first day of rejection (a dash when fewer than half reject), for the e-process, "
                               "the Kupiec test on the trailing 250 days and on all days so far, and the traffic light.",
                 label="tab:proposed-sequential", align="lrrrrrrr", wide=True)
    rows = []
    for s in seq["pd_grades"]["scenarios"]:
        rows.append([f"{s['factor'] if 'factor' in s else s['id']}", pct(s["e_product"]["ever"]), pct(s["e_average"]["ever"]),
                     pct(s["chi2_one_shot_power"]), pct(s["chi2_every_year"]["ever"])])
    figkit.table(T / "proposed-pdgrades.tex", ["PD factor", "E-process, product", "E-process, average", "Chi-square at year 10", "Chi-square every year"], rows,
                 caption="Share of 2,000 simulated ten-year histories of five rating grades in which each monitor rejects the predicted default "
                         "probabilities, in percent, when every grade's probability is multiplied by the factor of the first column.",
                 label="tab:proposed-pdgrades", align="rrrrr")
    rows = []
    for r in A["c11e"]:
        rows.append([r["window"], r["days"], r["models"], r["light"], r["eproc"], md(med(r["l_days"])), md(med(r["e_days"]))])
    figkit.table(T / "proposed-c11e.tex", ["Window", "Days", "Models", "Light flags", "E-process flags", "Light median day", "E-process median day"], rows,
                 caption="The e-process of the engine applied to the committed exceedance days of every model of the C11 ladder at the 99\\% level, "
                         "against the traffic light: the number of models each flags and the median first day on which each flags a model.",
                 label="tab:proposed-c11e", align="lrrrrrr")

    # --- BS-16
    rows = []
    for w in STRESS:
        for r in A["c11"][w]["conformal"]["rows"]:
            u, wr = r["unwrapped"], r["wrapped"]
            rows.append([w, MODEL_LABEL[r["model_id"]], f"{100 * r['alpha']:g}\\%", f"{u['hit_rate']:.3f}", f"{wr['hit_rate']:.3f}",
                         yn(u["passes_coverage"]), yn(wr["passes_coverage"]), f"{100 * r['fz0_change']:+.1f}"])
    figkit.table(T / "proposed-conformal.tex", ["Window", "Model", "Level", "Hit rate", "Wrapped", "Pass", "Wrapped", "FZ0 change (\\%)"], rows,
                 caption="Adaptive conformal recalibration of three models on the three stress windows of C11: the hit rate of each model without "
                         "and with the wrapper, whether Kupiec and conditional coverage both pass at 5\\%, and the relative change of the mean FZ0 "
                         "loss (negative is an improvement).", label="tab:proposed-conformal", align="llrrrllr")
    rows = []
    for c in A["c11"]["equity-2007-09"]["conformal"]["hypothesis"]["cells"]:
        rows.append([MODEL_LABEL[c["model_id"]], f"{100 * c['alpha']:g}\\%", c["windows_passed_unwrapped"], c["windows_passed_wrapped"],
                     c["extra_windows"], f"{100 * c['worst_fz0_change']:+.1f}", yn(c["holds"])])
    figkit.table(T / "proposed-conformal-cells.tex", ["Model", "Level", "Windows passed", "Windows passed wrapped", "Extra windows", "Worst FZ0 change (\\%)", "Holds"],
                 rows, caption="The six cells of the evaluation of the conformal wrapper: for each model and tail level, the stress windows passed "
                               "without and with the wrapper, the gain, the worst change of the mean FZ0 loss in any stress window, and whether the "
                               "criterion holds in the cell.", label="tab:proposed-conformal-cells", align="lrrrrrl")


def fit_width(path: pathlib.Path) -> None:
    """Scale a table down to the text width when it is wider (a no-op for a table that fits)."""
    s = path.read_text(encoding="utf-8")
    if "resizebox" in s:
        return
    s = s.replace("\\begin{tabular}", "\\resizebox{\\ifdim\\width>\\linewidth\\linewidth\\else\\width\\fi}{!}{%\n\\begin{tabular}", 1)
    s = s.replace("\\end{tabular}", "\\end{tabular}}", 1)
    path.write_text(s, encoding="utf-8", newline="\n")


def main() -> None:
    A = build()
    write_numbers(A["N"])
    write_tables(A)
    for p in OUT.glob("proposed-*.tex"):
        if p.name != "proposed-numbers.tex":
            fit_width(p)
    print("numbers:", len(A["N"]), "tables written to", OUT)


if __name__ == "__main__":
    main()
