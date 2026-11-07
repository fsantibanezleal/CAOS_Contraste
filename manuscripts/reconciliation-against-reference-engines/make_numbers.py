"""Write ``numbers.tex``: one LaTeX macro for every number the prose quotes, each read from a committed experiment output.

    python manuscripts/reconciliation-against-reference-engines/make_numbers.py

The prose never types a result: it calls a macro (``\\nPrintedAgree``). The script writes ``numbers.tex`` and, beside the outputs,
``experiments/numbers-manifest.json`` listing every macro with its value and the source file and key it was read from, so that
every number of the manuscript can be traced to the output that holds it. Macro names hold letters only (TeX). A percentage macro
prints the number without the percent sign; a scientific macro prints ``5.7\\times10^{-12}`` for use inside a math environment.
"""
from __future__ import annotations

import json
import math
import pathlib
import statistics

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE / "experiments"
DERIVED = HERE.parents[1] / "data" / "derived"
REG: dict[str, tuple[str, str]] = {}


def load(name: str) -> dict:
    return json.loads((EXP / name).read_text(encoding="utf-8"))


def sci(x: float, d: int = 1) -> str:
    if x == 0:
        return "0"
    m, e = f"{x:.{d}e}".split("e")
    return f"{m}\\times10^{{{int(e)}}}"


def put(name: str, value, src: str, fmt: str = "i") -> None:
    """fmt: i integer with thousands separators, f0..f5 fixed decimals, s scientific, p1 percent of a fraction (1 decimal),
    p0 percent of a fraction (no decimal), t text as given."""
    if fmt == "t":
        text = str(value)
    elif fmt == "i":
        text = f"{int(round(value)):,}".replace(",", "{,}")
    elif fmt[0] == "f":
        text = f"{value:.{int(fmt[1:])}f}"
    elif fmt == "s":
        text = sci(value)
    elif fmt == "p1":
        text = f"{100 * value:.1f}"
    elif fmt == "p0":
        text = f"{100 * value:.0f}"
    else:
        raise ValueError(fmt)
    assert name not in REG, name
    REG[name] = (text, src)


def held(flag: bool) -> str:
    return "held" if flag else "not held"


def main() -> None:
    pr, rt, cf, cm_, cr, pa, tm = (load(f"results_{n}.json") for n in ("printed", "routes", "closedforms", "committed", "criterion", "pairs", "transition_matrix"))
    net, sin, csa = (load(f"results_ore_{v}.json") for v in ("netting-set", "single-swap", "csa-mpor-10d"))
    s42 = {v: load(f"results_ore_seed42_{v}.json")["replicates"][0] for v in ("single-swap", "netting-set", "csa-mpor-10d", "csa-mpor-20d")}
    rtimes = load("run-times.json")

    # ------------------------------------------------------------------ printed answers
    t = pr["totals"]
    put("nPrintedN", t["n"], "results_printed.json:totals.n")
    put("nPrintedAgree", t["agree"], "results_printed.json:totals.agree")
    put("nPrintedShare", t["agree"] / t["n"], "results_printed.json:totals", "p1")
    put("nPrintedRecN", t["recomputed_n"], "results_printed.json:totals.recomputed_n")
    put("nPrintedRecAgree", t["recomputed_agree"], "results_printed.json:totals.recomputed_agree")
    put("nPrintedReadN", t["read_n"], "results_printed.json:totals.read_n")
    put("nPrintedReadAgree", t["read_agree"], "results_printed.json:totals.read_agree")
    put("nMissTotal", pr["n_misses"], "results_printed.json:n_misses")
    put("nSddN", pr["sdd_statement"]["n"], "results_printed.json:sdd_statement.n")
    put("nSddAgree", pr["sdd_statement"]["agree"], "results_printed.json:sdd_statement.agree")
    put("nWithoutN", pr["without_tasche_tables_8_and_9"]["n"], "results_printed.json:without_tasche_tables_8_and_9.n")
    put("nWithoutAgree", pr["without_tasche_tables_8_and_9"]["agree"], "results_printed.json:without_tasche_tables_8_and_9.agree")
    for name, key in (("nBinHalf", "half"), ("nBinOne", "to_one"), ("nBinTwo", "to_two"), ("nBinBeyond", "beyond_two")):
        put(name, pr["unit_gap_bins"][key], f"results_printed.json:unit_gap_bins.{key}")
    for name, units in (("nAgreeOneUnit", 1.0), ("nAgreeTwoUnits", 2.0), ("nAgreeFiveUnits", 5.0)):
        put(name, next(x["agree"] for x in pr["tolerance_sweep"] if x["units"] == units), f"results_printed.json:tolerance_sweep[{units}]")
    g = pr["by_group"]
    put("nTableNineMaxUnits", g["Tasche (2013), Table 9, 2009"]["max_unit_gap"], "results_printed.json:by_group.Tasche Table 9", "f1")
    put("nTableSixMaxUnits", g["Tasche (2013), Table 6"]["max_unit_gap"], "results_printed.json:by_group.Tasche Table 6", "f1")
    put("nTwelveMaxUnits", g["Pluto and Tasche (2005), Table 12"]["max_unit_gap"], "results_printed.json:by_group.Pluto Table 12", "f1")
    put("nTfourteenAgree", g["Pluto and Tasche (2005), Tables 13 and 14"]["agree"], "results_printed.json:by_group.Tables 13 and 14.agree")
    put("nTfourteenN", g["Pluto and Tasche (2005), Tables 13 and 14"]["n"], "results_printed.json:by_group.Tables 13 and 14.n")
    put("nSHN", g["Schuermann and Hanson (2004), Table 5"]["n"], "results_printed.json:by_group.Schuermann and Hanson.n")
    ex = pr["explain_scaled"]
    n_cells = sum(x["cells"] for x in ex.values())
    exact = sum(x["agree_with_exact_bounds"] for x in ex.values())
    printed = sum(x["agree_with_printed_bounds"] for x in ex.values())
    put("nScaledN", n_cells, "results_printed.json:explain_scaled")
    put("nScaledExact", exact, "results_printed.json:explain_scaled")
    put("nScaledPrinted", printed, "results_printed.json:explain_scaled")
    put("nScaledLeft", n_cells - printed, "results_printed.json:explain_scaled")
    put("nScaledGapsExact", n_cells - exact, "results_printed.json:explain_scaled")
    put("nScaledGapsResolved", printed - exact, "results_printed.json:explain_scaled")
    put("nScaledGapsLeft", n_cells - printed, "results_printed.json:explain_scaled")
    lv = pr["table4_level"]
    put("nFourAtSeventyFive", lv["bound_at_0_75"], "results_printed.json:table4_level", "f3")
    put("nFourAtSeventySixThree", lv["bound_at_0_763"], "results_printed.json:table4_level", "f3")
    put("nFourLevelLow", lv["level_range_printing_0_65"][0], "results_printed.json:table4_level", "f4")
    put("nFourLevelHigh", lv["level_range_printing_0_65"][1], "results_printed.json:table4_level", "f4")
    c = pr["miss_categories"]
    tested = c["rounded printed inputs (tested)"] + c["confidence level of the print (tested)"]
    rec = c["documented tolerance (recorded)"] + c["print at or above the exact bound (recorded)"] + c["Monte Carlo print (recorded)"] + c["printed generator (recorded)"]
    put("nMissTested", tested, "results_printed.json:miss_categories")
    put("nMissRecorded", rec, "results_printed.json:miss_categories")
    put("nMissTol", c["documented tolerance (recorded)"], "results_printed.json:miss_categories")
    put("nMissAbove", c["print at or above the exact bound (recorded)"], "results_printed.json:miss_categories")
    put("nMissMC", c["Monte Carlo print (recorded)"], "results_printed.json:miss_categories")
    put("nMissNoneIn", c.get("no explanation; within one unit", 0), "results_printed.json:miss_categories")
    put("nMissNoneOut", c.get("no explanation; beyond one unit", 0), "results_printed.json:miss_categories")
    put("nMissNone", c.get("no explanation; within one unit", 0) + c.get("no explanation; beyond one unit", 0), "results_printed.json:miss_categories")
    put("nMissNoneMax", max(u["unit_gap"] for u in pr["unexplained"]), "results_printed.json:unexplained", "f1")
    ww = pr["wrong_way_appendix"]
    put("nWWAgree", ww["agree"], "results_printed.json:wrong_way_appendix.agree")
    put("nWWN", ww["n"], "results_printed.json:wrong_way_appendix.n")
    put("nWWAtwo", ww["recomputed_a"][1], "results_printed.json:wrong_way_appendix.recomputed_a", "f5")
    put("nWWAtwoUnits", next(x["unit_gap"] for x in ww["cells"] if x["key"] == "a2"), "results_printed.json:wrong_way_appendix.cells", "f2")
    put("nWWBisection", max(ww["bisection_gap_a1"], ww["bisection_gap_a2"]), "results_printed.json:wrong_way_appendix", "s")

    # ------------------------------------------------------------------ routes
    p1 = rt["part1"]
    put("nGridCases", p1["grid_cases"], "results_routes.json:part1.grid_cases")
    put("nGridJeffMax", p1["jeffreys_max_gap"], "results_routes.json:part1.jeffreys_max_gap", "s")
    put("nGridBinMax", p1["binomial_max_gap"], "results_routes.json:part1.binomial_max_gap", "s")
    put("nGridWithin", p1["within_tol_grid"], "results_routes.json:part1.within_tol_grid")
    put("nRandomCases", p1["random_cases"], "results_routes.json:part1.random_cases")
    put("nRandomJeffMax", p1["random_jeffreys_max_gap"], "results_routes.json:part1.random_jeffreys_max_gap", "s")
    put("nRandomBinMax", p1["random_binomial_max_gap"], "results_routes.json:part1.random_binomial_max_gap", "s")
    put("nRandomWithin", p1["random_within_tol"], "results_routes.json:part1.random_within_tol")
    put("nRandomComparisons", p1["random_comparisons"], "results_routes.json:part1.random_comparisons")
    put("nSameCallGap", max(p1["same_call_max_gap_jeffreys"], p1["same_call_max_gap_binomial"]), "results_routes.json:part1.same_call_max_gap_*", "f0")
    put("nTailGap", rt["defect_tail_convention"]["C3_binomial"], "results_routes.json:defect_tail_convention.C3_binomial", "f3")
    put("nEpsNineGap", next(r["C3_binomial"] for r in rt["defect_relative"] if r["eps"] == 1e-9), "results_routes.json:defect_relative[1e-9].C3_binomial", "s")
    rel, tail = rt["defect_relative"], rt["defect_tail_convention"]
    put("nPlantedDefects", 1 + len(rel), "results_routes.json:defect_*")
    put("nPlantedCone", int(tail["flag"]["C1_binomial"]) + sum(r["flag"]["C1_binomial"] for r in rel), "results_routes.json:defect_*.flag.C1_binomial")
    put("nPlantedCtwo", int(tail["flag"]["C2_binomial"]) + sum(r["flag"]["C2_binomial"] for r in rel), "results_routes.json:defect_*.flag.C2_binomial")
    put("nPlantedCthree", int(tail["flag"]["C3_binomial"]) + sum(r["flag"]["C3_binomial"] for r in rel), "results_routes.json:defect_*.flag.C3_binomial")

    # ------------------------------------------------------------------ closed forms
    p2, p3 = cf["part2"], cf["part3"]
    put("nClosedCases", p2["cases"], "results_closedforms.json:part2.cases")
    put("nClosedWithin", p2["within_gate"], "results_closedforms.json:part2.within_gate")
    put("nClosedMedian", p2["median_relative_difference"], "results_closedforms.json:part2.median_relative_difference", "s")
    put("nClosedMax", p2["max_relative_difference"], "results_closedforms.json:part2.max_relative_difference", "s")
    w = p2["worst"][0]
    put("nClosedWorstAbs", abs(w["engine"] - w["quantlib"]), "results_closedforms.json:part2.worst[0]", "s")
    put("nClosedWorstPrice", w["quantlib"], "results_closedforms.json:part2.worst[0].quantlib", "f1")
    put("nClosedWorstShare", 100 * w["quantlib"] / 1_000_000.0, "results_closedforms.json:part2.worst[0].quantlib / notional", "f4")
    put("nSwaptionPayer", cf["part1"]["swaption_payer"]["relative_difference"], "results_closedforms.json:part1.swaption_payer", "s")
    put("nSwaptionReceiver", cf["part1"]["swaption_receiver"]["relative_difference"], "results_closedforms.json:part1.swaption_receiver", "s")
    put("nElasticitySwaption", p3["elasticity_swaption"], "results_closedforms.json:part3.elasticity_swaption", "f2")
    put("nElasticityBond", p3["elasticity_bond_call"], "results_closedforms.json:part3.elasticity_bond_call", "f3")
    put("nElasticityRatio", p3["elasticity_swaption"] / p3["elasticity_bond_call"], "results_closedforms.json:part3", "f0")
    put("nDetectSwaption", p3["smallest_detected_sigma_error_swaption"], "results_closedforms.json:part3", "s")
    put("nDetectBond", p3["smallest_detected_sigma_error_bond_call"], "results_closedforms.json:part3", "s")
    put("nBondAtMillionth", next(x["bond_call_relative_difference"] for x in p3["plants"] if x["delta"] == 1e-6), "results_closedforms.json:part3.plants[1e-6]", "s")

    # ------------------------------------------------------------------ transition matrix
    put("nTMVersion", tm["transitionMatrix"], "results_transition_matrix.json", "t")
    put("nTMPanels", tm["panels"], "results_transition_matrix.json:panels")
    put("nTMElements", tm["elements_compared"], "results_transition_matrix.json:elements_compared")
    put("nTMMaxDiff", max(tm["state_period_max_abs_diff"], tm["state_pooled_max_abs_diff"], tm["exclude_period_max_abs_diff"], tm["exclude_pooled_max_abs_diff"]), "results_transition_matrix.json", "s")
    ld = tm["last_record_double_count"]
    put("nTMDoubleMin", ld["min_gap_without_sentinel"], "results_transition_matrix.json:last_record_double_count", "f4")
    put("nTMDoubleMax", ld["max_gap_without_sentinel"], "results_transition_matrix.json:last_record_double_count", "f4")
    put("nTMDoubleFixed", ld["max_gap_after_correction"], "results_transition_matrix.json:last_record_double_count", "s")
    put("nTMAJPackage", tm["aalen_johansen"]["package"], "results_transition_matrix.json:aalen_johansen", "f4")
    put("nTMAJEngine", tm["aalen_johansen"]["engine"], "results_transition_matrix.json:aalen_johansen", "f4")

    # ------------------------------------------------------------------ the committed ORE documents
    v = cm_["variants"]
    put("nSingleMaxZ", v["single-swap"]["max_abs_z"], "results_committed.json:variants.single-swap", "f2")
    put("nNettingMaxZ", v["netting-set"]["max_abs_z"], "results_committed.json:variants.netting-set", "f2")
    for pre, key in (("Single", "single-swap"), ("Netting", "netting-set")):
        put(f"n{pre}EepeZ", v[key]["eepe"]["z"], f"results_committed.json:variants.{key}.eepe.z", "f2")
        put(f"n{pre}CvaZ", v[key]["cva"]["z"], f"results_committed.json:variants.{key}.cva.z", "f2")
        put(f"n{pre}Equivalence", v[key]["eepe"]["equivalence_margin_rel"], f"results_committed.json:variants.{key}.eepe", "p1")
        put(f"n{pre}Detectable", v[key]["eepe"]["min_detectable_rel_80"], f"results_committed.json:variants.{key}.eepe", "p1")
    for pre, key in (("CsaTen", "csa-mpor-10d"), ("CsaTwenty", "csa-mpor-20d")):
        put(f"n{pre}Beyond", v[key]["n_beyond_two"], f"results_committed.json:variants.{key}.n_beyond_two")
        put(f"n{pre}MaxZ", v[key]["max_abs_z"], f"results_committed.json:variants.{key}.max_abs_z", "f2")
        put(f"n{pre}CvaZ", v[key]["cva"]["z"], f"results_committed.json:variants.{key}.cva.z", "f2")
        put(f"n{pre}MtaZ", v[key]["mta0_max_z"], f"results_committed.json:variants.{key}.mta0_max_z", "f2")
    im = v["with-im"]
    put("nImBeyond", im["n_beyond_two"], "results_committed.json:variants.with-im.n_beyond_two")
    put("nImMaxZ", im["max_abs_z"], "results_committed.json:variants.with-im.max_abs_z", "f2")
    put("nImRatio", im["dim"]["mean_ratio_ore_over_python"], "results_committed.json:variants.with-im.dim", "f2")
    put("nImDimBeyond", im["dim"]["n_beyond_two"], "results_committed.json:variants.with-im.dim")
    put("nImDimMaxZ", im["dim"]["max_abs_z"], "results_committed.json:variants.with-im.dim", "f1")
    put("nRebuildGap", max(x["max_abs_ee_gap"] for x in cm_["rebuild"].values()), "results_committed.json:rebuild", "s")
    put("nOreSecondsCommitted", json.loads((DERIVED / "C12" / "netting-set.json").read_text(encoding="utf-8"))["outputs"]["ore_reconciliation"]["run_seconds"],
        "data/derived/C12/netting-set.json:outputs.ore_reconciliation.run_seconds", "f0")
    put("nMtaShareTen", 1 - v["csa-mpor-10d"]["mta0_max_z"] / v["csa-mpor-10d"]["max_abs_z"], "results_committed.json", "p0")
    put("nMtaShareTwenty", 1 - v["csa-mpor-20d"]["mta0_max_z"] / v["csa-mpor-20d"]["max_abs_z"], "results_committed.json", "p0")

    # ------------------------------------------------------------------ repeated runs against ORE
    for pre, d in (("Net", net), ("Sin", sin), ("Csa", csa)):
        s = d["summary"]
        put(f"nRepl{pre}N", s["reps"], f"results_ore_{d['summary']['variant']}.json:summary.reps")
        put(f"nRepl{pre}Pass", s["passed_product_rule"], f"results_ore_{d['summary']['variant']}.json:summary.passed_product_rule")
        put(f"nRepl{pre}Lo", s["pass_lo"], f"results_ore_{d['summary']['variant']}.json:summary.pass_lo", "p0")
        put(f"nRepl{pre}Hi", s["pass_hi"], f"results_ore_{d['summary']['variant']}.json:summary.pass_hi", "p0")
        put(f"nRepl{pre}MeanZ", s["mean_of_mean_z"], f"results_ore_{d['summary']['variant']}.json:summary.mean_of_mean_z", "f2")
        put(f"nRepl{pre}MeanZPair", s["mean_of_mean_z_pair"], f"results_ore_{d['summary']['variant']}.json:summary.mean_of_mean_z_pair", "f2")
    cs = csa["summary"]
    put("nReplCsaFail", cs["reps"] - cs["passed_product_rule"], "results_ore_csa-mpor-10d.json:summary")
    put("nReplCsaMaxZ", statistics.mean(r["max_abs_z"] for r in csa["replicates"]), "results_ore_csa-mpor-10d.json:replicates.max_abs_z", "f1")
    put("nReplCsaCvaZ", statistics.mean(r["z_cva"] for r in csa["replicates"]), "results_ore_csa-mpor-10d.json:replicates.z_cva", "f1")
    put("nSeedFortyTwoNetting", s42["netting-set"]["max_abs_z"], "results_ore_seed42_netting-set.json:replicates[0].max_abs_z", "f2")
    gap42 = 0.0
    for k, rep in s42.items():
        agr = json.loads((DERIVED / "C12" / f"{k}.json").read_text(encoding="utf-8"))["outputs"]["ore_reconciliation"]["agreement"]
        gap42 = max(gap42, max(abs(a - b["difference"] / b["combined_se"]) for a, b in zip(rep["z"], agr, strict=True)))
    put("nSeedFortyTwoGap", gap42, "results_ore_seed42_*.json:replicates[0].z against data/derived/C12/*.json:ore_reconciliation.agreement", "f3")
    put("nOreRepsNet", net["summary"]["reps"], "results_ore_netting-set.json:summary.reps")
    put("nOreRepsCsa", cs["reps"], "results_ore_csa-mpor-10d.json:summary.reps")
    put("nOrePairRho", statistics.mean(r["pair_correlation_ore_mean"] for r in net["replicates"]), "results_ore_netting-set.json:replicates.pair_correlation_ore_mean", "f2")
    put("nPyPairRho", statistics.mean(r["pair_correlation_python_mean"] for r in net["replicates"]), "results_ore_netting-set.json:replicates.pair_correlation_python_mean", "f2")
    put("nSdPairOre", statistics.median(net["summary"]["sd_z_pair_by_date"]), "results_ore_netting-set.json:summary.sd_z_pair_by_date", "f2")
    ok = {}
    for k, d in (("Net", net), ("Sin", sin)):
        s = d["summary"]
        ok[k] = {"r1": all(abs(x) <= 0.5 for x in s["mean_z_by_date"]) and abs(s["mean_of_mean_z"]) <= 0.25,
                 "r2": statistics.median(s["sd_z_by_date"]) < 0.8 and 0.8 <= statistics.median(s["sd_z_pair_by_date"]) <= 1.2,
                 "r3": s["pass_rate"] >= 0.5}
    put("nPredRone", held(ok["Net"]["r1"] and ok["Sin"]["r1"]), "predictions.md R1 against results_ore_*.json", "t")
    put("nPredRtwo", held(ok["Net"]["r2"] and ok["Sin"]["r2"]), "predictions.md R2 against results_ore_*.json", "t")
    put("nPredRthree", held(ok["Net"]["r3"] and ok["Sin"]["r3"]), "predictions.md R3 against results_ore_*.json", "t")
    put("nPredRfour", held(cs["passed_product_rule"] == 0 and statistics.mean(r["max_abs_z"] for r in csa["replicates"]) > 5), "predictions.md R4", "t")
    put("nPredRfive", held(sum(r["z_cva"] < -5 for r in csa["replicates"]) >= 7), "predictions.md R5", "t")

    # ------------------------------------------------------------------ calibration, size and power
    put("nCritReps", cr["reps"], "results_criterion.json:reps")
    put("nCritPathsA", cr["paths_a"], "results_criterion.json:paths_a")
    put("nCritPathsB", cr["paths_b"], "results_criterion.json:paths_b")
    cs_, cn_ = cr["calibration"]["single-swap"], cr["calibration"]["netting-set"]
    put("nSdSingle", cs_["median_sd_z"], "results_criterion.json:calibration.single-swap.median_sd_z", "f2")
    put("nSdNetting", cn_["median_sd_z"], "results_criterion.json:calibration.netting-set.median_sd_z", "f2")
    put("nSdSinglePair", cs_["median_sd_z_pair"], "results_criterion.json:calibration.single-swap.median_sd_z_pair", "f2")
    put("nSdNettingPair", cn_["median_sd_z_pair"], "results_criterion.json:calibration.netting-set.median_sd_z_pair", "f2")
    put("nSdFirst", cn_["sd_z_by_date"][0], "results_criterion.json:calibration.netting-set.sd_z_by_date[0]", "f2")
    put("nSdLast", cn_["sd_z_by_date"][-1], "results_criterion.json:calibration.netting-set.sd_z_by_date[-1]", "f2")
    put("nOverstateLast", 1.0 / cn_["sd_z_by_date"][-1], "results_criterion.json:calibration.netting-set.sd_z_by_date[-1]", "f1")
    put("nSdCvaSingle", cs_["sd_zc"], "results_criterion.json:calibration.single-swap.sd_zc", "f2")
    put("nSdCvaNetting", cn_["sd_zc"], "results_criterion.json:calibration.netting-set.sd_zc", "f2")
    put("nSdEepeSingle", cs_["sd_ze"], "results_criterion.json:calibration.single-swap.sd_ze", "f2")
    put("nSdEepeNetting", cn_["sd_ze"], "results_criterion.json:calibration.netting-set.sd_ze", "f2")
    put("nRhoFirst", pa["netting-set"]["rho_by_date"][0], "results_pairs.json:netting-set.rho_by_date[0]", "f2")
    put("nRhoLast", pa["netting-set"]["rho_by_date"][-1], "results_pairs.json:netting-set.rho_by_date[-1]", "f2")
    put("nRhoCva", pa["netting-set"]["rho_cva"], "results_pairs.json:netting-set.rho_cva", "f2")
    meas = np.array(cn_["sd_z_by_date"])
    pred = np.array(pa["netting-set"]["predicted_sd_z_by_date"])
    put("nSdDeviation", float(np.mean(np.abs(meas - pred))), "results_criterion.json vs results_pairs.json: mean |measured - predicted| sd of z", "f3")
    put("nPairReps", pa["reps"], "results_pairs.json:reps")
    T = cr["table"]
    for name, key, rule in (("nSizeProdSingle", "single-swap|null", "product"), ("nSizeProdNetting", "netting-set|null", "product"), ("nSizePairNetting", "netting-set|null", "pair"),
                            ("nSizeSidakNetting", "netting-set|null", "sidak"), ("nSizeRefineSingle", "single-swap|null", "pair+sidak"),
                            ("nSizeRefineNetting", "netting-set|null", "pair+sidak"), ("nSizeDatesNetting", "netting-set|null", "dates"),
                            ("nSizeEepeNetting", "netting-set|null", "eepe"), ("nSizeFixedOneNetting", "netting-set|null", "fixed 1%"),
                            ("nPowerProdSigmaTwo", "netting-set|sigma+2%", "product"), ("nPowerRefineSigmaTwo", "netting-set|sigma+2%", "pair+sidak"),
                            ("nPowerSidakSigmaTwo", "netting-set|sigma+2%", "sidak"), ("nPowerPairSigmaTwo", "netting-set|sigma+2%", "pair"),
                            ("nPowerDatesSigmaTwo", "netting-set|sigma+2%", "dates"), ("nPowerEepeSigmaTwo", "netting-set|sigma+2%", "eepe"),
                            ("nPowerCvaSigmaTwo", "netting-set|sigma+2%", "cva"), ("nPowerFixedTwoSigmaTwo", "netting-set|sigma+2%", "fixed 2%")):
        put(name, T[key][rule]["rate"], f"results_criterion.json:table.{key}.{rule}.rate", "p1")
    put("nMeasureEepeMiss", 1.0 - T["netting-set|measure"]["eepe"]["rate"], "results_criterion.json:table.netting-set|measure.eepe.rate", "p0")

    # ------------------------------------------------------------------ run times
    sec = rtimes["seconds"]
    for name, key in (("nTimePrinted", "exp_printed.py"), ("nTimeRoutes", "exp_routes.py"), ("nTimeClosed", "exp_closedforms.py"), ("nTimeCommitted", "exp_committed.py"),
                      ("nTimePairs", "exp_pairs.py"), ("nTimeCriterion", "exp_criterion.py"), ("nTimeOreNet", "exp_ore_replicates.py netting-set"),
                      ("nTimeOreSingle", "exp_ore_replicates.py single-swap"), ("nTimeOreCsa", "exp_ore_replicates.py csa-mpor-10d"), ("nTimeTM", "exp_transition_matrix.py")):
        put(name, sec[key], f"run-times.json:seconds.{key}", "i")
    put("nWorkers", rtimes["criterion_workers"], "run-times.json:criterion_workers")
    put("nHardware", f"{rtimes['logical_processors']} logical processors, {rtimes['platform']}", "run-times.json:platform", "t")
    put("nOreSecondsMean", statistics.mean([net["summary"]["mean_ore_seconds"], sin["summary"]["mean_ore_seconds"]]), "results_ore_*.json:summary.mean_ore_seconds", "f0")

    lines = ["% Written by make_numbers.py from experiments/results_*.json; do not edit.\n"]
    for name, (text, _) in sorted(REG.items()):
        lines.append(f"\\newcommand{{\\{name}}}{{{text}}}\n")
    (HERE / "numbers.tex").write_text("".join(lines), encoding="utf-8", newline="\n")
    (EXP / "numbers-manifest.json").write_text(json.dumps({k: {"value": v[0], "source": v[1]} for k, v in sorted(REG.items())}, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(REG)} macros written")


if __name__ == "__main__":
    main()
