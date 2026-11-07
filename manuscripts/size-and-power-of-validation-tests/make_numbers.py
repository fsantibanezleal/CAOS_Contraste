"""Write ``tables/numbers.tex`` (one ``\\newcommand`` per number the prose quotes) and ``numbers-index.json`` (each number with
the committed document or experiment result it comes from).

    python manuscripts/size-and-power-of-validation-tests/make_numbers.py

A macro name is letters only (``\\nSims``). The text quotes a number only through one of these macros, so a new
measurement regenerates the prose numbers instead of retyping them.
"""
from __future__ import annotations

import json
import math
import pathlib
import re

import numpy as np
from scipy import stats

import analysis as A

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "tables"

M: dict[str, tuple[str, object, str]] = {}


_DIGITS = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]


def reg(name: str, value: str, raw: object, source: str) -> None:
    name = re.sub(r"\d", lambda m: _DIGITS[int(m.group())], name)
    if not re.fullmatch(r"[A-Za-z]+", name):
        raise SystemExit(f"macro name {name!r} must be letters only")
    if name in M:
        raise SystemExit(f"macro {name} registered twice")
    M[name] = (value, raw, source)


def i(x: float) -> str:
    return f"{int(round(x)):,}"


def pc(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}"


def fx(x: float, d: int = 3) -> str:
    return f"{x:.{d}f}"


def rate(doc_name: str, key: str, level: str = "p<0.05", variant_rows=None) -> dict:
    for r in A.doc(doc_name)["outputs"]["simulations"]:
        if r["key"] == key:
            return r["rates"][level]
    raise KeyError(key)


def sim(doc_name: str, key: str) -> dict:
    for r in A.doc(doc_name)["outputs"]["simulations"]:
        if r["key"] == key:
            return r
    raise KeyError(key)


def build() -> None:
    S = f"data/derived/C22/"
    tot = A.totals()
    reg("nSims", i(tot["sims"]), tot["sims"], "sum of simulations without a study block over the eight credit variants of data/derived/C22")
    reg("nReps", i(tot["reps"]), tot["reps"], "sum of n_rep over the same simulations")
    reg("nRates", i(tot["rates"]), tot["rates"], "sum of len(rates) over the same simulations")
    reg("nExactRows", i(tot["exact_rows"]), tot["exact_rows"], "simulations with an exact block")
    reg("nGens", i(tot["generators"]), tot["generators"], "distinct (variant, generator) pairs of the same simulations")
    reg("nFamilies", "8", 8, "the null family and seven defect families")
    reg("nTests", "21", len(A.TEST_ORDER), "keys ending @null in null.json without a study block")
    reg("nPowerTests", str(len(A.HAS_POWER)), len(A.HAS_POWER), "tests with a power curve on a panel that measures power")
    reg("nTransition", "4", 4, "tests of the transitions panel")
    reg("nNullReps", "4,000", 4000, "n_rep of every @null simulation")
    reg("nPowerReps", "2,000", 2000, "n_rep of the power and clustering simulations")
    fam = {f["variant"]: f for f in A.families_of_defects()}
    for v, name in (("null", "Null"), ("miscalibration", "Miscal"), ("clustering", "Cluster"), ("drift", "Drift"),
                    ("discrimination-decay", "Decay"), ("leakage", "Leak"), ("broken-monotonicity", "Broken"),
                    ("concentration", "Conc")):
        reg(f"fSims{name}", i(fam[v]["sims"]), fam[v]["sims"], f"{v}.json simulations without a study")
        reg(f"fReps{name}", i(fam[v]["reps"]), fam[v]["reps"], f"{v}.json sum of n_rep")
        reg(f"fGens{name}", i(fam[v]["generators"]), fam[v]["generators"], f"{v}.json distinct generators")
    pairs = A.exact_comparisons()
    reg("nExactCmp", str(len(pairs)), len(pairs), "47 rows with an exact block at two levels")
    nondeg = [p for p in pairs if not p["degenerate"]]
    reg("nExactNondeg", str(len(nondeg)), len(nondeg), "exact comparisons with exact probability between 0.005 and 0.995")
    reg("nAgree", str(sum(p["agrees"] for p in pairs)), sum(p["agrees"] for p in pairs), "agrees flags of the committed rows")
    cal = A.standard_error_calibration()
    reg("zMaxAbs", fx(cal["max_abs"], 2), cal["max_abs"], "max |z| over the non-degenerate exact comparisons")
    reg("zSd", fx(cal["sd"], 2), cal["sd"], "sd of z over the non-degenerate exact comparisons")
    reg("zMean", fx(cal["mean"], 2).replace("-0.00", "0.00"), cal["mean"], "mean of z over the non-degenerate exact comparisons")

    # ---- size
    size = {r["test"]: r for r in A.size_table()}
    cv = A.committed_verdict_vs_pooled()
    nh = sum(r["pool_definition"] for r in cv)
    reg("nHold", str(nh), nh, "the definition of holding a size applied to the pool of the 50 blocks (200,000 repetitions): exact value, else Wilson lower limit not above the level")
    reg("nNotHold", str(21 - nh), 21 - nh, "21 minus the above")
    nhr = sum(r["cell_rule"] for r in cv)
    reg("nHoldCellRule", str(nhr), nhr, "Algorithm 1 (holds()) of the 21 @null rows of the committed cells (4,000 repetitions)")
    reg("nNotHoldCellRule", str(21 - nhr), 21 - nhr, "21 minus the above")
    nhd = sum(r["cell_definition"] for r in cv)
    reg("nHoldCellDef", str(nhd), nhd, "the definition applied to the committed cells")
    reg("nNotHoldCellDef", str(21 - nhd), 21 - nhd, "21 minus the above")
    nhp = sum(r["pool_rule"] for r in cv)
    reg("nHoldPoolRule", str(nhp), nhp, "Algorithm 1 applied to the pool of the 50 blocks")
    reg("nNotHoldPoolRule", str(21 - nhp), 21 - nhp, "21 minus the above")
    reg("boundFivePool", pc(A.bound(0.05, 200000), 2), A.bound(0.05, 200000), "Algorithm 1 bound at 200,000 repetitions, level 5%")
    reg("boundOnePool", pc(A.bound(0.01, 200000), 2), A.bound(0.01, 200000), "same, level 1%")
    for R, nm in ((4000, "Four"), (200000, "TwoHundredK")):
        reg(f"detIntFive{nm}", pc(A.interval_detectable(0.05, R), 2), 0, f"excess over 5% that puts the Wilson interval wholly above the level with probability 0.8, R={R}")
        reg(f"detIntOne{nm}", pc(A.interval_detectable(0.01, R), 2), 0, f"same over 1%, R={R}")
        reg(f"flagInt{nm}", pc(A.interval_flag_probability(0.05, 0.05, R) + A.interval_flag_probability(0.01, 0.01, R), 1), 0,
            f"P(interval wholly above the level at 5% or 1%) of one test of size equal to its level (sum of the two levels), R={R}")
    reg("intRateFiveFour", pc(A.interval_kmin(0.05, 4000) / 4000, 2), 0, "smallest rate at 5% whose Wilson interval lies wholly above the level, R=4000")
    reg("intRateFiveTwoHundredK", pc(A.interval_kmin(0.05, 200000) / 200000, 2), 0, "same, R=200000")
    reg("expFalseAboveExt", fx(25 * (A.interval_flag_probability(0.05, 0.05, 4000) + A.interval_flag_probability(0.01, 0.01, 4000)), 1), 0,
        "expected number of the 25 studies of the extension with an interval wholly above the level if every study had exactly its level")
    reg("expFalseAbove", fx(21 * (A.interval_flag_probability(0.05, 0.05, 200000) + A.interval_flag_probability(0.01, 0.01, 200000)), 1), 0,
        "expected number of the 21 tests whose interval at 200,000 repetitions lies wholly above the level if every test had exactly its level")
    reg("boundFive", pc(A.bound(0.05, 4000), 2), A.bound(0.05, 4000), "alpha + z_0.999 sqrt(alpha(1-alpha)/4000)")
    reg("boundOne", pc(A.bound(0.01, 4000), 2), A.bound(0.01, 4000), "same at alpha 0.01")
    reg("boundFiveBig", pc(A.bound(0.05, 20000), 2), A.bound(0.05, 20000), "same at 20,000 repetitions")
    j = size["pd.jeffreys"]
    reg("jeffExactOne", pc(j["exact"]["p<0.01"], 2), j["exact"]["p<0.01"], "null.json pd.jeffreys@null exact p<0.01")
    reg("jeffExactFive", pc(j["exact"]["p<0.05"], 2), j["exact"]["p<0.05"], "null.json pd.jeffreys@null exact p<0.05")
    reg("jeffSimOne", pc(j["p<0.01"]["rate"], 2), j["p<0.01"]["rate"], "null.json pd.jeffreys@null rate p<0.01")
    reg("jeffSimFive", pc(j["p<0.05"]["rate"], 2), j["p<0.05"]["rate"], "null.json pd.jeffreys@null rate p<0.05")
    b = size["pd.binomial"]
    reg("binExactFive", pc(b["exact"]["p<0.05"], 2), b["exact"]["p<0.05"], "null.json pd.binomial@null exact")
    reg("binExactOne", pc(b["exact"]["p<0.01"], 2), b["exact"]["p<0.01"], "null.json pd.binomial@null exact")
    reg("binSimFive", pc(b["p<0.05"]["rate"], 2), b["p<0.05"]["rate"], "null.json pd.binomial@null rate")
    n = size["pd.normal_multiperiod"]
    reg("normFive", pc(n["p<0.05"]["rate"], 2), n["p<0.05"]["rate"], "null.json pd.normal_multiperiod@null")
    reg("normOne", pc(n["p<0.01"]["rate"], 2), n["p<0.01"]["rate"], "null.json pd.normal_multiperiod@null")
    reg("normLoFive", pc(n["p<0.05"]["lo"], 2), n["p<0.05"]["lo"], "Wilson low")
    reg("normHiFive", pc(n["p<0.05"]["hi"], 2), n["p<0.05"]["hi"], "Wilson high")
    reg("migFive", pc(size["rating.migration_ztests"]["p<0.05"]["rate"], 2), size["rating.migration_ztests"]["p<0.05"]["rate"], "null.json")
    reg("hhiFive", pc(size["rating.hhi"]["p<0.05"]["rate"], 1), size["rating.hhi"]["p<0.05"]["rate"], "null.json")
    reg("momFive", pc(size["rating.momentum"]["p<0.05"]["rate"], 2), size["rating.momentum"]["p<0.05"]["rate"], "null.json")
    reg("matFive", pc(size["rating.matrix_reference"]["p<0.05"]["rate"], 2), size["rating.matrix_reference"]["p<0.05"]["rate"], "null.json")
    reg("ordFive", pc(size["rating.markov_order"]["p<0.05"]["rate"], 2), size["rating.markov_order"]["p<0.05"]["rate"], "null.json")
    reg("timeFive", pc(size["rating.time_homogeneity"]["p<0.05"]["rate"], 2), size["rating.time_homogeneity"]["p<0.05"]["rate"], "null.json")
    reg("ordLoFive", pc(size["rating.markov_order"]["p<0.05"]["lo"], 2), 0, "committed cell Wilson low at 5%")
    reg("ordHiFive", pc(size["rating.markov_order"]["p<0.05"]["hi"], 2), 0, "committed cell Wilson high at 5%")
    reg("ordOne", pc(size["rating.markov_order"]["p<0.01"]["rate"], 2), 0, "committed cell rate at 1%")
    reg("ordLoOne", pc(size["rating.markov_order"]["p<0.01"]["lo"], 2), 0, "committed cell Wilson low at 1%")
    reg("ordHiOne", pc(size["rating.markov_order"]["p<0.01"]["hi"], 2), 0, "committed cell Wilson high at 1%")
    reg("ordTwentyK", pc(rate("null", "rating.markov_order@null-20000")["rate"], 2),
        rate("null", "rating.markov_order@null-20000")["rate"], "null.json rating.markov_order@null-20000")
    reg("ordTwentyKLo", pc(rate("null", "rating.markov_order@null-20000")["wilson_low"], 2), 0, "same, Wilson low")
    reg("ordTwentyKHi", pc(rate("null", "rating.markov_order@null-20000")["wilson_high"], 2), 0, "same, Wilson high")
    reg("aucNullFive", pc(size["disc.auc_vs_initial"]["p<0.05"]["rate"], 2), 0, "null.json")
    reg("profileFive", pc(size["pd.default_profile"]["p<0.05"]["rate"], 2), 0, "null.json")
    reg("hlFive", pc(size["pd.hosmer_lemeshow"]["p<0.05"]["rate"], 2), 0, "null.json")
    reg("hlOne", pc(size["pd.hosmer_lemeshow"]["p<0.01"]["rate"], 2), 0, "null.json")
    reg("chiGradesFive", pc(size["pd.chi2_grades"]["p<0.05"]["rate"], 2), 0, "null.json")
    reg("markovBoundMargin", pc(A.bound(0.05, 4000) - size["rating.markov_order"]["p<0.05"]["rate"], 2), 0, "bound minus rate")
    # settings
    st = {r["key"]: r for r in A.settings_rows()}
    reg("hlFitted", pc(st["pd.hosmer_lemeshow@fitted"]["p<0.05"]["rate"], 1), 0, "null.json pd.hosmer_lemeshow@fitted")
    reg("hlFittedOne", pc(st["pd.hosmer_lemeshow@fitted"]["p<0.01"]["rate"], 1), 0, "same")
    reg("hlDofTheory", pc(A.hl_dof_oversize(10), 1), A.hl_dof_oversize(10), "P(chi2_10 > chi2_{8,0.95})")
    reg("tlUpper", pc(st["pd.traffic_lights@upper"]["p<0.05"]["rate"], 2), 0, "null.json pd.traffic_lights@upper")
    reg("tlUpperExact", pc(st["pd.traffic_lights@upper"]["exact"]["p<0.05"], 2), 0, "same, exact")
    reg("tlLowerExact", pc(size["pd.traffic_lights"]["exact"]["p<0.05"], 2), 0, "null.json pd.traffic_lights@null exact")
    reg("chiThin", pc(st["pd.chi2_grades@thin"]["p<0.05"]["rate"], 2), 0, "null.json pd.chi2_grades@thin")
    reg("chiThinOne", pc(st["pd.chi2_grades@thin"]["p<0.01"]["rate"], 2), 0, "same")
    reg("aucDevOne", pc(st["disc.auc_vs_initial@dev1"]["p<0.05"]["rate"], 1), 0, "null.json disc.auc_vs_initial@dev1")
    reg("aucDevOneExt", pc(st["disc.auc_vs_initial@dev1-extended"]["p<0.05"]["rate"], 1), 0, "same, extended form")
    reg("aucDevTheory", pc(A.auc_known_vs_estimated_size(1.0), 1), 0, "P(Z > 1.645/sqrt(1+1/m)), m=1")
    reg("aucDevTheoryFour", pc(A.auc_known_vs_estimated_size(4.0), 1), 0, "m=4")
    reg("aucDevTheorySixteen", pc(A.auc_known_vs_estimated_size(16.0), 1), 0, "m=16")
    reg("psiHundred", pc(st["stability.psi@n100"]["metric>0.1"]["rate"], 1), 0, "null.json stability.psi@n100 rule metric>0.1")
    reg("psiHundredTwentyFive", pc(st["stability.psi@n100"]["metric>0.25"]["rate"], 1), 0, "same, rule metric>0.25")
    reg("psiHundredBench", pc(st["stability.psi@n100"]["p<0.05"]["rate"], 1), 0, "same, benchmark p<0.05")
    reg("psiTheoryHundred", pc(A.psi_fixed_band_false_alarm(100, 0.10), 1), 0, "chi2_9 sf(0.10*100/2)")
    reg("psiTheoryHundredTF", pc(A.psi_fixed_band_false_alarm(100, 0.25), 1), 0, "chi2_9 sf(0.25*100/2)")
    reg("psiTheoryFourHundred", pc(A.psi_fixed_band_false_alarm(400, 0.10), 1), 0, "chi2_9 sf(0.10*400/2)")
    reg("psiCrit", fx(0.0, 0), 0, "placeholder replaced below")
    del M["psiCrit"]

    # ---- miscalibration, clustering
    def mis(key: str, level: str = "p<0.05") -> dict:
        return rate("miscalibration", key, level)

    rows = {(r["test_id"], r["generator"]): r for r in A.credit_rows("miscalibration")}
    mc = A.curves("miscalibration")
    def at(v: str, test: str, panel: str, x: float) -> dict:
        for r in A.curves(v, "power" if v != "clustering" else "size")[(test, panel)]:
            if abs(r["x"] - x) < 1e-9:
                return r
        raise KeyError((v, test, panel, x))
    for name, test, panel, x in (("binK125", "pd.binomial", "portfolio", 1.25), ("jeffK125", "pd.jeffreys", "portfolio", 1.25),
                                 ("hlK125", "pd.hosmer_lemeshow", "obligors", 1.25), ("spiK125", "pd.spiegelhalter", "obligors", 1.25),
                                 ("chiK125", "pd.chi2_grades", "grades", 1.25), ("normK125", "pd.normal_multiperiod", "years", 1.25),
                                 ("tlK125", "pd.traffic_lights", "years", 1.25), ("vasK125", "pd.binomial_vasicek", "portfolio", 1.25),
                                 ("binK15", "pd.binomial", "portfolio", 1.5), ("vasK15", "pd.binomial_vasicek", "portfolio", 1.5),
                                 ("vasK3", "pd.binomial_vasicek", "portfolio", 3.0), ("profK3", "pd.default_profile", "grades", 3.0),
                                 ("binK11", "pd.binomial", "portfolio", 1.1), ("spiK11", "pd.spiegelhalter", "obligors", 1.1),
                                 ("hlK11", "pd.hosmer_lemeshow", "obligors", 1.1), ("chiK11", "pd.chi2_grades", "grades", 1.1)):
        r = at("miscalibration", test, panel, x)
        reg(name, pc(r["rates"]["p<0.05"]["rate"], 1), r["rates"]["p<0.05"]["rate"], f"miscalibration.json {test} {panel} x={x}")
    r = at("miscalibration", "pd.binomial_vasicek", "portfolio", 3.0)
    reg("vasK3Exact", pc(r["exact"]["p<0.05"], 1), 0, "miscalibration.json pd.binomial_vasicek portfolio x=3 exact")
    r = at("miscalibration", "pd.binomial", "portfolio", 1.25)
    reg("binK125Exact", pc(r["exact"]["p<0.05"], 1), 0, "miscalibration.json pd.binomial x=1.25 exact")
    for name, test, x in (("binRho2", "pd.binomial", 0.02), ("binRho5", "pd.binomial", 0.05), ("binRho10", "pd.binomial", 0.10)):
        r = at("clustering", test, "portfolio", x)
        reg(name, pc(r["rates"]["p<0.05"]["rate"], 1), 0, f"clustering.json {test} portfolio x={x}")
        reg(name + "Exact", pc(r["exact"]["p<0.05"], 1), 0, "same, exact")
    for name, test, panel, x in (("chiRho2", "pd.chi2_grades", "grades", 0.02), ("chiRho10", "pd.chi2_grades", "grades", 0.10),
                                 ("hlRho2", "pd.hosmer_lemeshow", "obligors", 0.02), ("hlRho20", "pd.hosmer_lemeshow", "obligors", 0.20),
                                 ("spiRho5", "pd.spiegelhalter", "obligors", 0.05), ("normRho5", "pd.normal_multiperiod", "years", 0.05),
                                 ("normRho20", "pd.normal_multiperiod", "years", 0.20), ("vasRho10", "pd.binomial_vasicek", "portfolio", 0.10),
                                 ("vasRho20", "pd.binomial_vasicek", "portfolio", 0.20), ("tlRho5", "pd.traffic_lights", "years", 0.05)):
        r = at("clustering", test, panel, x)
        reg(name, pc(r["rates"]["p<0.05"]["rate"], 1), 0, f"clustering.json {test} {panel} x={x}")
    r = at("clustering", "pd.normal_multiperiod", "years", 0.0)
    reg("normRhoZero", pc(r["rates"]["p<0.05"]["rate"], 1), 0, "clustering.json pd.normal_multiperiod years x=0")
    r = at("clustering", "pd.binomial_vasicek", "portfolio", 0.20)
    reg("vasRho20Exact", pc(r["exact"]["p<0.05"], 1), 0, "same, exact")
    # ---- drift
    for name, test, x, rule in (("psiBench02", "stability.psi", 0.2, "p<0.05"), ("psiBench01", "stability.psi", 0.1, "p<0.05"),
                                ("psiBand01At02", "stability.psi", 0.2, "metric>0.1"), ("psiBand025At02", "stability.psi", 0.2, "metric>0.25"),
                                ("psiBand01At03", "stability.psi", 0.3, "metric>0.1"), ("psiBand025At05", "stability.psi", 0.5, "metric>0.25"),
                                ("chiDrift02", "stability.chi2", 0.2, "p<0.05"), ("ksDrift02", "stability.ks", 0.2, "p<0.05"),
                                ("ksDrift01", "stability.ks", 0.1, "p<0.05")):
        r = at("drift", test, "stability", x)
        reg(name, pc(r["rates"][rule]["rate"], 1), 0, f"drift.json {test} x={x} {rule}")
    for name, test, x in (("hlDrift05", "pd.hosmer_lemeshow", 0.5), ("spiDrift05", "pd.spiegelhalter", 0.5)):
        rr = A.curves("drift", "size")[(test, "calibration")]
        r = next(q for q in rr if abs(q["x"] - x) < 1e-9)
        reg(name, pc(r["rates"]["p<0.05"]["rate"], 1), 0, f"drift.json {test} calibration x={x}")
    # ---- discrimination
    for name, test, panel, x in (("ecbDrop02", "disc.auc_vs_initial", "ecb", 0.02), ("ecbDrop05", "disc.auc_vs_initial", "ecb", 0.05),
                                 ("ecbDrop08", "disc.auc_vs_initial", "ecb", 0.08), ("delDrop05", "disc.delong", "delong", 0.05),
                                 ("delDrop02", "disc.delong", "delong", 0.02)):
        r = at("discrimination-decay", test, panel, x)
        reg(name, pc(r["rates"]["p<0.05"]["rate"], 1), 0, f"discrimination-decay.json {test} {panel} x={x}")
    imp = A.doc("discrimination-decay")["impact"]
    reg("ecbDropAtPower", fx(imp["ecb_drop80"]["value"], 3), 0, "discrimination-decay.json impact.ecb_drop80")
    reg("delDropAtPower", fx(imp["delong_drop80"]["value"], 3), 0, "discrimination-decay.json impact.delong_drop80")
    for name, test, panel, x in (("leakAuc025", "disc.auc_vs_initial", "auc", 0.25), ("leakCsi025", "stability.csi", "feature", 0.25),
                                 ("leakCsi1", "stability.csi", "feature", 1.0), ("leakCsi2", "stability.csi", "feature", 2.0),
                                 ("leakAuc05", "disc.auc_vs_initial", "auc", 0.5)):
        r = at("leakage", test, panel, x)
        reg(name, pc(r["rates"]["p<0.05"]["rate"], 1), 0, f"leakage.json {test} {panel} x={x}")
    # ---- rating
    for name, test, panel, x in (("migR15n500", "rating.migration_ztests", "migration-500", 1.5), ("migR2n500", "rating.migration_ztests", "migration-500", 2.0),
                                 ("migR3n500", "rating.migration_ztests", "migration-500", 3.0), ("migR2n2000", "rating.migration_ztests", "migration-2000", 2.0),
                                 ("migR15n2000", "rating.migration_ztests", "migration-2000", 1.5),
                                 ("hhiPower", "rating.hhi", "ecb", 0.5), ("chiCount005", "stability.chi2", "counts", 0.05),
                                 ("chiCount002", "stability.chi2", "counts", 0.02), ("swapProfile", "pd.default_profile", "curve", 1.0),
                                 ("swapChi", "pd.chi2_grades", "curve", 1.0)):
        r = at("broken-monotonicity" if name.startswith(("mig", "swap")) else "concentration", test, panel, x)
        reg(name, pc(r["rates"]["p<0.05"]["rate"], 1), 0, f"{test} {panel} x={x}")
    peak = max(math.sqrt(9) * (c - 0.6) / (c * math.sqrt(0.5 + c * c)) for c in np.linspace(0.01, 3.0, 300001))
    reg("hhiPeak", fx(peak, 2), peak, "max over c of sqrt(K-1)(c-CV0)/(c sqrt(0.5+c^2)), K=10, CV0=0.6")
    reg("hhiAllIn", fx(math.sqrt(9) * (3 - 0.6) / (3 * math.sqrt(9.5)), 2), 0, "same at c = sqrt(K-1)")
    reg("hhiAllInP", fx(float(stats.norm.sf(math.sqrt(9) * (3 - 0.6) / (3 * math.sqrt(9.5)))), 2), 0, "upper normal tail of the all-in statistic")
    reg("zCrit", fx(float(stats.norm.ppf(0.95)), 3), 0, "norm.ppf(0.95)")
    # ---- s80
    s80 = {t: A.severity_at_power(A.main_curve(t)) for t in A.HAS_POWER}
    nreach = sum(1 for v in s80.values() if v["x"] is not None)
    reg("nReach", str(nreach), nreach, "main curves whose rate reaches 0.8 on the ladder")
    reg("nNoReach", str(len(A.HAS_POWER) - nreach), len(A.HAS_POWER) - nreach, "main curves that do not")
    for name, t, d in (("sPsi", "stability.psi", 3), ("sChiStab", "stability.chi2", 3), ("sKs", "stability.ks", 3), ("sMig", "rating.migration_ztests", 2)):
        reg(name, fx(s80[t]["x"], d), s80[t]["x"], f"severity at 80% power, {t}")
    for name, t in (("sBin", "pd.binomial"), ("sJeff", "pd.jeffreys"), ("sChi", "pd.chi2_grades"), ("sHl", "pd.hosmer_lemeshow"),
                    ("sSpi", "pd.spiegelhalter"), ("sNorm", "pd.normal_multiperiod"), ("sTl", "pd.traffic_lights")):
        v = s80[t]
        reg(name, fx(v["x"], 2), v["x"], f"severity at 80% power, {t}")
    # ---- monotonicity
    mono = A.monotonicity()
    reg("nMonoPairs", str(mono["pairs"]), mono["pairs"], "adjacent ladder pairs of the power panels, two levels")
    reg("nMonoViol", str(mono["violations"]), mono["violations"], "falls larger than 3.29 combined SE")
    # ---- reproductions
    rep = {r["variant"]: r for r in A.reproductions()}
    reg("wpAgree", str(rep["clustering"]["agree"]), 0, "clustering.json golden")
    reg("wpTotal", str(rep["clustering"]["total"]), 0, "same")
    reg("wpRuns", i(rep["clustering"]["runs"]), 0, "same")
    reg("ynAgree", str(rep["drift"]["agree"]), 0, "drift.json golden")
    reg("ynTotal", str(rep["drift"]["total"]), 0, "same")
    reg("ynRuns", i(rep["drift"]["runs"]), 0, "same")
    reg("ynMeanZ", fx(rep["drift"]["mean_z_interior"], 2), 0, "mean z of the cells strictly between 0 and 1")
    reg("ynInterior", str(rep["drift"]["interior"]), 0, "cells with a published rate strictly between 0 and 1")
    reg("demlerRuns", i(rep["leakage"]["runs"]), 0, "leakage.json golden")
    dm = A.doc("leakage")["outputs"]["golden"][0]["cells"][0]
    reg("demlerMeasured", pc(dm["measured"], 1), 0, "leakage.json golden measured")
    reg("demlerPublished", pc(dm["published"], 1), 0, "leakage.json golden published")
    wp = rep["clustering"]["disagreeing"][0]
    reg("wpOffPub", pc(wp["published"], 1), 0, "the one WP14 cell that disagrees")
    reg("wpOffMeas", pc(wp["measured"], 1), 0, "same, measured")
    # ---- intervals
    iv = A.interval_on_exact_rows()
    for key, nm in (("Wald", "Wald"), ("Wilson", "Wilson"), ("Agresti--Coull", "AC"), ("Clopper--Pearson", "CP"), ("Jeffreys", "Jef")):
        reg(f"iv{nm}All", str(iv[key]["all"]), 0, "exact value inside the 95% interval, all 94 comparisons")
        reg(f"iv{nm}Nd", str(iv[key]["nondegenerate"]), 0, "same, the 63 non-degenerate comparisons")
    grid = A.interval_coverage_grid(4000)
    for key, nm in (("Wald", "Wald"), ("Wilson", "Wilson"), ("Agresti--Coull", "AC"), ("Clopper--Pearson", "CP"), ("Jeffreys", "Jef")):
        for p, tag in (("0.001", "Thousandth"), ("0.01", "One"), ("0.05", "Five")):
            reg(f"cov{nm}{tag}", pc(grid[key][p], 1), grid[key][p], f"exact coverage of the {key} interval, R=4000, p={p}")
    # ---- instrument
    ins = A.result("instrument.json")
    reg("flagFive", pc(ins["flag_probability"]["4000"]["0.05"], 2), 0, "instrument.json flag_probability 4000 0.05")
    reg("flagOne", pc(ins["flag_probability"]["4000"]["0.01"], 2), 0, "same 0.01")
    reg("flagTest", pc(ins["flag_probability_per_test"]["4000"], 2), 0, "per test, both levels")
    reg("flagFamily", pc(ins["flag_probability_family_21"]["4000"], 1), 0, "21 tests, independence assumed")
    reg("flagThousand", pc(ins["flag_probability_per_test"]["1000"], 2), 0, "per test at R=1000")
    reg("flagTwentyK", pc(ins["flag_probability_per_test"]["20000"], 2), 0, "per test at R=20000")
    for R, nm in ((1000, "Thousand"), (2000, "TwoK"), (4000, "Four"), (20000, "TwentyK"), (200000, "TwoHundredK")):
        reg(f"detFive{nm}", pc(detectable(0.05, R), 2), 0, f"smallest excess over 5% detected with probability 0.8, R={R}")
        reg(f"detOne{nm}", pc(detectable(0.01, R), 2), 0, f"same over 1%, R={R}")
    af = {(a["test"], a["level"], a["factor"]): a for a in ins["agreement_failure"]}
    for f, nm in ((1.0, "One"), (1.02, "TwoPercent"), (1.05, "FivePercent"), (1.10, "TenPercent")):
        reg(f"agFail{nm}", pc(af[("pd.binomial", 0.05, f)]["failure_probability"], 1), 0, f"instrument.json agreement_failure binomial 5% factor {f}")
    sm = {a["factor"]: a for a in ins["agreement_simulated"]}
    reg("agSimFive", pc(sm[1.05]["share_flagged"], 1), 0, "instrument.json agreement_simulated factor 1.05")
    reg("agSimTen", pc(sm[1.10]["share_flagged"], 0), 0, "same factor 1.10")
    reg("agSimNone", pc(sm[1.0]["share_flagged"], 1), 0, "same factor 1.00")
    reg("agBlocks", str(sm[1.05]["blocks"]), 0, "blocks per factor")
    reg("agMeanRateFive", pc(sm[1.05]["mean_rate"], 2), 0, "mean simulated binomial rate at 5% when the generator's PD is 5% too high")
    reg("hhiWilsonHi", pc(A.wilson(0, 4000)[1], 2), 0, "upper Wilson limit of a rate of 0 in 4,000 repetitions")
    # jeffreys at 1% detection by one cell
    kmin = math.floor(A.bound(0.01, 4000) * 4000) + 1
    reg("jeffDetect", pc(float(stats.binom.sf(kmin - 1, 4000, j["exact"]["p<0.01"])), 1), 0, "P(rate > bound) at R=4000 with true size = exact Jeffreys size at 1%")
    reg("jeffDetectInt", pc(A.interval_flag_probability(j["exact"]["p<0.01"], 0.01, 4000), 1), 0,
        "P(Wilson interval wholly above 1%) in one cell of 4,000 repetitions with true size = exact Jeffreys size at 1%")
    # ---- reproduction of the committed cells, seeds
    rp = A.result("reproduce.json")
    reg("nReproduced", str(rp["equal"]), 0, "reproduce.json")
    reg("nReproTotal", str(rp["total"]), 0, "reproduce.json")
    # ---- seed replication
    rs = A.seed_replication()
    reg("seedMinutes", str(round(A.result("seed_replication.json")["seconds"] / 60)), 0, "seed_replication.json seconds / 60")
    reg("reproSeconds", str(round(rp["seconds"])), 0, "reproduce.json seconds")
    reg("instrMinutes", f"{ins['seconds'] / 60:.1f}", 0, "instrument.json seconds / 60 (the third experiment, one process)")
    reg("nBlocks", str(rs["blocks"]), 0, "seed_replication.json")
    reg("nRepsPooled", i(rs["blocks"] * rs["n_rep"]), 0, "blocks times repetitions")
    ratios = []
    for t in A.TEST_ORDER:
        for lv in A.LEVELS:
            q = rs["tests"][t][lv]
            if q["se_binomial"] > 0:
                ratios.append(q["sd_blocks"] / q["se_binomial"])
    reg("sdRatioMean", fx(float(np.mean(ratios)), 2), 0, "mean over tests and levels of sd of block rates over sqrt(p(1-p)/4000)")
    reg("sdRatioMin", fx(float(np.min(ratios)), 2), 0, "min of the same")
    reg("sdRatioMax", fx(float(np.max(ratios)), 2), 0, "max of the same")
    grp = A.groups_by_pooled()
    reg("nWithin", str(len(grp["within"])), 0, "tests whose pooled rate is at most the level at both levels")
    reg("nOver", str(len(grp["over"])), 0, "tests whose pooled Wilson lower limit exceeds the level at one level")
    reg("nNeither", str(len(grp["neither"])), 0, "the others")
    nag = sum(r["agree_definition"] for r in cv)
    reg("nVerdictAgree", str(nag), 0, "judgement of the committed cell equals the judgement of the pool, both by the definition")
    reg("nVerdictDisagree", str(21 - nag), 0, "21 minus the above")
    nagr = sum(r["agree_rule"] for r in cv)
    reg("nVerdictAgreeRule", str(nagr), 0, "the same by Algorithm 1 at both sizes")
    reg("nVerdictDisagreeRule", str(21 - nagr), 0, "21 minus the above")
    missed = [r["test"] for r in cv if r["cell_definition"] and not r["pool_definition"]]
    reg("nMissedByCell", str(len(missed)), 0, "tests that the definition places above the level on the pool and that the committed cell does not show: " + ", ".join(missed))
    only_def = [r["test"] for r in cv if r["pool_rule"] and not r["pool_definition"]]
    reg("nPoolDefOnly", str(len(only_def)), 0, "tests that the definition places above the level on the pool and Algorithm 1 does not: " + ", ".join(only_def))
    # the excess of a test is read at the level(s) at which its pooled Wilson interval lies above the level
    pooled_over_exc = {t: max(rs["tests"][t][lv]["pooled"] - A.ALPHA[lv] for lv in A.LEVELS if rs["tests"][t][lv]["pooled_lo"] > A.ALPHA[lv])
                       for t in grp["over"]}
    small = [t for t in grp["over"] if t not in ("pd.jeffreys", "pd.normal_multiperiod")]
    reg("smallExcMax", pc(max(pooled_over_exc[t] for t in small), 2), 0, "largest pooled excess, at the level where the pooled interval is above it, among the over tests other than Jeffreys and normal")
    reg("smallExcMin", pc(min(pooled_over_exc[t] for t in small), 2), 0, "smallest pooled excess among them")
    reg("nSmallOver", str(len(small)), 0, "over tests other than Jeffreys and normal")
    for t, nm in (("stability.psi", "Psi"), ("pd.hosmer_lemeshow", "Hl"), ("pd.spiegelhalter", "Spi"), ("rating.markov_order", "Ord"),
                  ("pd.chi2_grades", "Chi"), ("disc.delong", "Del")):
        reg(f"pooled{nm}", pc(rs["tests"][t]["p<0.05"]["pooled"], 2), 0, f"pooled rate at 5%, {t}, 200,000 repetitions")
    reg("pooledCsi", pc(rs["tests"]["stability.csi"]["p<0.05"]["pooled"], 2), 0, "pooled rate at 5%, stability.csi")
    reg("pooledHlOne", pc(rs["tests"]["pd.hosmer_lemeshow"]["p<0.01"]["pooled"], 2), 0, "pooled rate at 1% Hosmer-Lemeshow")
    reg("pooledNorm", pc(rs["tests"]["pd.normal_multiperiod"]["p<0.05"]["pooled"], 2), 0, "pooled normal at 5%")
    reg("pooledNormLo", pc(rs["tests"]["pd.normal_multiperiod"]["p<0.05"]["pooled_lo"], 2), 0, "Wilson low of the pooled normal rate at 5%")
    reg("pooledNormHi", pc(rs["tests"]["pd.normal_multiperiod"]["p<0.05"]["pooled_hi"], 2), 0, "Wilson high of the pooled normal rate at 5%")
    reg("pooledDelLo", pc(rs["tests"]["disc.delong"]["p<0.05"]["pooled_lo"], 3), 0, "Wilson low of the pooled DeLong rate at 5%")
    reg("pooledCsiLoOne", pc(rs["tests"]["stability.csi"]["p<0.01"]["pooled_lo"], 3), 0, "Wilson low of the pooled characteristic stability index rate at 1%")
    reg("pooledCsiOne", pc(rs["tests"]["stability.csi"]["p<0.01"]["pooled"], 2), 0, "pooled rate at 1%, stability.csi")
    reg("pooledJeffOne", pc(rs["tests"]["pd.jeffreys"]["p<0.01"]["pooled"], 2), 0, "pooled Jeffreys at 1%")
    reg("pooledBinOne", pc(rs["tests"]["pd.binomial"]["p<0.01"]["pooled"], 2), 0, "pooled binomial at 1%")
    reg("pooledMigFive", pc(rs["tests"]["rating.migration_ztests"]["p<0.05"]["pooled"], 2), 0, "pooled migration at 5%")
    reg("pooledAucFive", pc(rs["tests"]["disc.auc_vs_initial"]["p<0.05"]["pooled"], 2), 0, "pooled AUC test at 5%")
    reg("pooledProfFive", pc(rs["tests"]["pd.default_profile"]["p<0.05"]["pooled"], 2), 0, "pooled default profile at 5%")
    reg("pooledTlFive", pc(rs["tests"]["pd.traffic_lights"]["p<0.05"]["pooled"], 2), 0, "pooled traffic lights at 5%")
    fl = A.flag_rates_by_repetitions()
    for R, nm in (("1000", "Thousand"), ("2000", "TwoK"), ("4000", "Four"), ("20000", "TwentyK")):
        reg(f"flWithinBound{nm}", pc(fl[R]["within_bound"], 2), 0, f"share of cells of {R} repetitions flagged by the bound rule, tests within the level")
        reg(f"flWithinNaive{nm}", pc(fl[R]["within_naive"], 1), 0, "same by the naive rule")
        reg(f"flWithinInt{nm}", pc(fl[R]["within_interval"], 2), 0, "same by the interval rule (the definition)")
        reg(f"flOverInt{nm}", pc(fl[R]["over_interval"], 1), 0, "same for the tests above the level by the interval rule")
        reg(f"flOverBound{nm}", pc(fl[R]["over_bound"], 1), 0, "same for the tests above the level")
        reg(f"flOverNaive{nm}", pc(fl[R]["over_naive"], 1), 0, "same by the naive rule")
    # ---- extension
    ext = A.extension_table()
    reg("nStudies", str(len(ext)), 0, "studies of the null variant with a study block")
    reg("nExtTests", str(len({e['test'] for e in ext})), 0, "distinct tests among them")
    tests_hold, tests_rule = {}, {}
    for e in ext:
        tests_hold[e["test"]] = tests_hold.get(e["test"], True) and e["holds_definition"]
        tests_rule[e["test"]] = tests_rule.get(e["test"], True) and e["holds"]
    reg("nExtHold", str(sum(tests_hold.values())), 0, "tests all of whose studies hold their size by the definition (4,000 repetitions)")
    reg("nExtNotHold", str(len(tests_hold) - sum(tests_hold.values())), 0, "the others")
    reg("nStudiesHold", str(sum(e["holds_definition"] for e in ext)), 0, "studies that hold their size by the definition")
    reg("nStudiesNotHold", str(len(ext) - sum(e["holds_definition"] for e in ext)), 0, "the others")
    reg("nExtHoldRule", str(sum(tests_rule.values())), 0, "tests all of whose studies hold their size by Algorithm 1")
    reg("nStudiesHoldRule", str(sum(e["holds"] for e in ext)), 0, "studies that hold their size by Algorithm 1")
    pw = sorted(e["power5"] for e in ext)
    reg("extPowMin", pc(pw[0], 0), 0, "weakest power at 5% of the 25 studies")
    reg("extPowMax", pc(pw[-1], 0), 0, "strongest")
    reg("extPowMed", pc(float(np.median(pw)), 1), 0, "median")
    reg("extAboveBar", str(sum(1 for x in pw if x >= 0.8)), 0, "studies with power at least 0.8")
    reg("extBelowHalf", str(sum(1 for x in pw if x < 0.5)), 0, "studies with power below 0.5")
    for e in ext:
        if e["test"] == "lgd_ead.lgd_calibration_over_time":
            reg("lgdTimeOne", pc(e["size1"], 2), 0, "LGD calibration over time, size at 1%")
        if e["test"] == "portfolio.mc_convergence":
            reg("mcConvFive", pc(e["size5"], 2), 0, "Monte Carlo quantile convergence, size at 5%")
        if e["test"] == "market.du_escanciano_unconditional":
            reg("duUncondFive", pc(e["size5"], 2), 0, "Du-Escanciano unconditional, size at 5%")
    bad = [e for e in ext if not e["holds"]]       # the two that Algorithm 1 flags
    for e in bad:
        if e["test"] == "market.christoffersen_independence":
            reg("chrIndFive", pc(e["size5"], 1), 0, "Christoffersen independence size at 5%")
            reg("chrIndOne", pc(e["size1"], 2), 0, "at 1%")
        if e["test"] == "market.christoffersen_conditional_coverage":
            reg("chrCcFive", pc(e["size5"], 1), 0, "Christoffersen conditional coverage size at 5%")
    # estimators
    est = A.doc("null")["outputs"]["estimators"]["auc"]
    reg("aucCover", pc(est["coverage"], 1), 0, "null.json estimators.auc.coverage")
    reg("aucCoverMcse", pc(est["coverage_mcse"], 1), 0, "null.json estimators.auc.coverage_mcse")
    reg("aucSeRel", fx(est["model_se_relative_error_pct"], 2), 0, "null.json estimators.auc.model_se_relative_error_pct")
    # quantiles
    cons5 = [t for t, r in size.items() if r["p<0.05"]["hi"] < 0.05]
    reg("nConsFive", str(len(cons5)), 0, "credit-family tests whose Wilson interval at 5% lies wholly below 5%")
    ext_cons = [r for r in A.doc("null")["outputs"]["simulations"] if r.get("study") and r["rates"]["p<0.05"]["wilson_high"] < 0.05]
    reg("nExtCons", str(len(ext_cons)), 0, "studies of the extension whose Wilson interval at 5% lies wholly below 5%")
    fg = ins["flag_probability"]["4000"]
    reg("flagUnion", pc(21 * (fg["0.05"] + fg["0.01"]), 1), 0, "21 tests times the sum of the two exact flag probabilities at R=4000")
    reg("binLimitRhoFive", pc(A.binomial_size_limit(0.01, 0.05), 1), 0, "Phi(Phi^-1(pi)(1 - sqrt(1-rho))/sqrt(rho)), pi=0.01, rho=0.05")
    reg("binLimitRhoTen", pc(A.binomial_size_limit(0.01, 0.10), 1), 0, "same, rho=0.10")
    for n, nm in ((1000, "Thousand"), (10000, "TenK"), (100000, "HundredK")):
        reg(f"binNRhoTen{nm}", pc(A.binomial_size(n, 0.01, 0.10, 0.05), 1), 0, f"independent recomputation, N={n}, rho=0.10, alpha=0.05")
    reg("hhiKMinSix", str(A.hhi_min_grades(0.6)), 0, "smallest K with sqrt(K-1) g(c0) >= 1.645, c0=0.6")
    reg("hhiKMinThree", str(A.hhi_min_grades(0.3)), 0, "same, c0=0.3")
    rb = A.reconcile_binomial()
    reg("nBinRecon", str(rb["n"]), 0, "exact rejection probabilities of the binomial test recomputed without the engine")
    mant, exp = f"{rb['max_abs']:.1e}".split("e")
    reg("binReconMax", rf"{mant}\times10^{{{int(exp)}}}", rb["max_abs"], "largest absolute difference, independent recomputation against the committed exact value")
    reg("zBound", fx(A.Z_BOUND, 3), A.Z_BOUND, "norm.ppf(0.999)")
    reg("zAgree", "3.29", 3.29, "constant of the agreement check (norm.ppf(0.9995) rounded)")


def detectable(alpha: float, R: int, power: float = 0.8) -> float:
    b = A.bound(alpha, R)
    kmin = math.floor(b * R) + 1
    lo, hi = alpha, alpha + 0.2
    for _ in range(80):
        mid = (lo + hi) / 2
        if stats.binom.sf(kmin - 1, R, mid) >= power:
            hi = mid
        else:
            lo = mid
    return hi - alpha


def main() -> int:
    build()
    OUT.mkdir(exist_ok=True)
    lines = ["% Written by make_numbers.py from data/derived/C22 and experiments/results. Do not edit.", ""]
    for name, (val, _raw, _src) in M.items():
        lines.append(f"\\newcommand{{\\{name}}}{{{val}}}")
    (OUT / "numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    (HERE / "numbers-index.json").write_text(json.dumps({k: {"value": v[0], "source": v[2]} for k, v in M.items()}, indent=1) + "\n",
                                             encoding="utf-8", newline="\n")
    print(f"{len(M)} numbers written to tables/numbers.tex")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
