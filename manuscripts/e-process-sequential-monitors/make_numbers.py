"""Write ``numbers.tex``: one LaTeX macro for every number the prose quotes, each read from a committed experiment output.

    python manuscripts/e-process-sequential-monitors/make_numbers.py

The prose never types a result: it calls a macro (``\\nNullSizeE``). The script writes ``numbers.tex`` and, beside it,
``experiments/numbers-manifest.json`` listing every macro with its value, its source file and key path, and the committed
document it was read from, so that every number of the manuscript can be traced to the output that holds it. The macros of
percentages print the number without the percent sign. Macro names hold letters only (TeX).
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
import figkit  # noqa: E402

EXP = HERE / "experiments"


def load(name: str) -> dict:
    return json.loads((EXP / name).read_text(encoding="utf-8"))


H, SH, X3, AB, PC, C11, C03, TH, MT, PDC = (load(f"results_{n}.json") for n in
                                            ("hits", "size_horizon", "x3_seeds", "ablation", "pd_correlation", "c11", "c03", "theory", "matched",
                                             "pd_comparators"))
C22 = json.loads((figkit.DERIVED / "C22" / "other-families.json").read_text(encoding="utf-8"))["outputs"]["sequential"]

REG: dict[str, tuple[str, str]] = {}


def put(name: str, value: float | int | str, src: str, d: int | None = None, pct: bool = False, thousands: bool = False) -> None:
    if isinstance(value, str):
        text = value
    elif pct:
        text = f"{100 * value:.{d if d is not None else 1}f}"
    elif d is not None:
        text = f"{value:,.{d}f}" if thousands else f"{value:.{d}f}"
    else:
        text = f"{value:,.0f}" if thousands else f"{value:.0f}"
    assert name not in REG, name
    REG[name] = (text, src)


def hs(sid: str, key: str, field: str):
    return H["scenarios"][sid]["methods"][key][field]


def hsrc(sid: str, key: str, field: str) -> str:
    return f"results_hits.json:scenarios.{sid}.methods.{key}.{field}"


def pct_hits(name: str, sid: str, key: str, field: str = "ever", d: int = 1) -> None:
    put(name, hs(sid, key, field), hsrc(sid, key, field), d, pct=True)


def med_hits(name: str, sid: str, key: str) -> None:
    v = hs(sid, key, "median_day")
    put(name, "beyond the horizon" if v is None else f"{v:.0f}", hsrc(sid, key, "median_day"))


def ci_hits(name: str, sid: str, key: str, field: str = "median_ci") -> None:
    lo, hi = hs(sid, key, field)
    put(name + "Lo", "--" if lo is None else f"{lo:.0f}", hsrc(sid, key, field) + "[0]")
    put(name + "Hi", "--" if hi is None else f"{hi:.0f}", hsrc(sid, key, field) + "[1]")


def yw(year: int) -> str:
    """A year as letters, because a TeX macro name holds no digit."""
    names = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    return "".join(names[int(c)] for c in str(year))


def build() -> None:
    m = H["meta"]
    put("Reps", m["reps"], "results_hits.json:meta.reps", thousands=True)
    put("CalibrationReps", m["calibration_reps"], "results_hits.json:meta.calibration_reps", thousands=True)
    put("Seed", m["seed"], "results_hits.json:meta.seed")
    put("KupCalCritical", m["critical_values"]["kupiec_cumulative"], "results_hits.json:meta.critical_values.kupiec_cumulative", 2)
    put("CusumCritical", m["critical_values"]["cusum_m3"], "results_hits.json:meta.critical_values.cusum_m3", 2)
    n = m["reps"]
    put("Bound", 0.05 + 3 * math.sqrt(0.05 * 0.95 / n), "derived: 0.05 + 3 sqrt(0.05 * 0.95 / reps)", 1, pct=True)
    put("TLCount", m["traffic_light_first_non_green_count"], "results_hits.json:meta.traffic_light_first_non_green_count")

    # size on correct models
    for nm, key in (("E", "e_rate"), ("EUp", "e_rate_upper"), ("Cluster", "e_cluster"), ("Battery", "e_battery"), ("Sprt", "e_sprt3"),
                    ("Wwz", "e_wwz"), ("Beta", "e_beta"), ("KupTrail", "kupiec_trailing"), ("KupCum", "kupiec_cumulative"),
                    ("Light", "traffic_light"), ("Indep", "independence_trailing"), ("KupSidak", "kupiec_sidak"),
                    ("KupCal", "kupiec_calibrated"), ("Cusum", "cusum_calibrated")):
        pct_hits(f"NullSize{nm}", "null", key)
    lo, hi = hs("null", "e_rate", "ever_ci")
    put("NullSizeELo", lo, hsrc("null", "e_rate", "ever_ci") + "[0]", 1, pct=True)
    put("NullSizeEHi", hi, hsrc("null", "e_rate", "ever_ci") + "[1]", 1, pct=True)
    pct_hits("NullByE", "null", "e_rate", "by", 2)
    pct_hits("NullByEUp", "null", "e_rate_upper", "by", 2)
    put("KupOneShotNull", hs("null", "kupiec_one_shot", "ever"), hsrc("null", "kupiec_one_shot", "ever"), 1, pct=True)

    # severity ladder
    for tag, sid in (("OneFive", "rate-x1.5"), ("Two", "rate-x2"), ("Three", "rate-x3"), ("Four", "rate-x4"), ("Six", "rate-x6"), ("Ten", "rate-x10")):
        for nm, key in (("E", "e_rate"), ("EUp", "e_rate_upper"), ("Sprt", "e_sprt3"), ("Wwz", "e_wwz"), ("Beta", "e_beta"), ("Battery", "e_battery"),
                        ("KupTrail", "kupiec_trailing"), ("KupCum", "kupiec_cumulative"), ("Light", "traffic_light"), ("KupSidak", "kupiec_sidak"),
                        ("KupCal", "kupiec_calibrated"), ("Cusum", "cusum_calibrated")):
            pct_hits(f"By{tag}{nm}", sid, key, "by")
            med_hits(f"Med{tag}{nm}", sid, key)
            pct_hits(f"Ever{tag}{nm}", sid, key, "ever")
        ci_hits(f"Med{tag}E", sid, "e_rate")
        put(f"Shot{tag}", hs(sid, "kupiec_one_shot", "ever"), hsrc(sid, "kupiec_one_shot", "ever"), 1, pct=True)
    for tag, sid in (("Three", "rate-x3"), ("Four", "rate-x4")):
        for key, nm in (("e_rate", "E"), ("e_rate_upper", "EUp"), ("e_wwz", "Wwz")):
            c = hs(sid, key, "power_cost_vs_one_shot")
            put(f"Cost{tag}{nm}", c["mean"], hsrc(sid, key, "power_cost_vs_one_shot") + ".mean", 1, pct=True)
            put(f"Cost{tag}{nm}Se", c["se"], hsrc(sid, key, "power_cost_vs_one_shot") + ".se", 1, pct=True)

    for tag, sid in (("Three", "rate-x3"), ("Four", "rate-x4")):
        # the gap of the two medians as they are printed, so that the text reads "237 against 130" and "107 days"
        gap = int(f"{hs(sid, 'e_wwz', 'median_day'):.0f}") - int(f"{hs(sid, 'e_rate', 'median_day'):.0f}")
        put(f"Gap{tag}Wwz", gap, f"derived: printed {hsrc(sid, 'e_wwz', 'median_day')} - printed {hsrc(sid, 'e_rate', 'median_day')}", 0)

    # clustering
    for tag, sid in (("OneTenth", "cluster-0.1"), ("TwoTenth", "cluster-0.2"), ("FourTenth", "cluster-0.4")):
        for nm, key in (("Cluster", "e_cluster"), ("Battery", "e_battery"), ("E", "e_rate"), ("Indep", "independence_trailing"),
                        ("KupTrail", "kupiec_trailing"), ("Light", "traffic_light"), ("KupCal", "kupiec_calibrated"), ("KupCum", "kupiec_cumulative")):
            pct_hits(f"Clu{tag}{nm}", sid, key, "ever")
        med_hits(f"CluMed{tag}Cluster", sid, "e_cluster")
        med_hits(f"CluMed{tag}Indep", sid, "independence_trailing")
        med_hits(f"CluMed{tag}Battery", sid, "e_battery")
        med_hits(f"CluMed{tag}Light", sid, "traffic_light")

    # seeds
    for pre, tag, name in (("Seeds", "Three", "x3"), ("Seeds", "Four", "x4"), ("SeedsUp", "Three", "x3_upper"), ("SeedsUp", "Four", "x4_upper")):
        f = X3["factors"][name]
        s = f"results_x3_seeds.json:factors.{name}."
        put(f"{pre}{tag}Med", f["pooled_median"], s + "pooled_median", 0)
        put(f"{pre}{tag}MedLo", f["pooled_median_ci"][0], s + "pooled_median_ci[0]", 0)
        put(f"{pre}{tag}MedHi", f["pooled_median_ci"][1], s + "pooled_median_ci[1]", 0)
        put(f"{pre}{tag}SeedMean", f["seed_median_mean"], s + "seed_median_mean", 1)
        put(f"{pre}{tag}SeedSd", f["seed_median_sd"], s + "seed_median_sd", 1)
        put(f"{pre}{tag}Below", f["share_of_seeds_below_window"], s + "share_of_seeds_below_window", 0, pct=True)
        put(f"{pre}{tag}Cost", f["pooled_power_cost"], s + "pooled_power_cost", 1, pct=True)
        put(f"{pre}{tag}CostSe", f["pooled_power_cost_se"], s + "pooled_power_cost_se", 2, pct=True)
        put(f"{pre}{tag}Light", f["pooled_traffic_light_median"], s + "pooled_traffic_light_median", 0)
        put(f"{pre}{tag}Kupiec", f["pooled_kupiec_power"], s + "pooled_kupiec_power", 1, pct=True)
        put(f"{pre}{tag}ByWindow", f["pooled_share_by_window"], s + "pooled_share_by_window", 1, pct=True)
        put(f"{pre}{tag}Strict", f["pooled_share_below_window_strict"], s + "pooled_share_below_window_strict", 1, pct=True)
    put("SeedsCount", X3["meta"]["seeds"], "results_x3_seeds.json:meta.seeds")
    put("SeedsPooledN", X3["factors"]["x3"]["pooled_n"], "results_x3_seeds.json:factors.x3.pooled_n", thousands=True)

    # committed C22 document (seed 42)
    cm = C22["hits"]
    def cs(sid: str, key: str):
        return next(s for s in cm["scenarios"] if s["id"] == sid)[key]
    put("CommittedReps", cm["reps"], "data/derived/C22/other-families.json:outputs.sequential.hits.reps", thousands=True)
    put("CommittedSeed", C22["seed"], "data/derived/C22/other-families.json:outputs.sequential.seed")
    put("CommittedNullE", cs("null", "e_rate")["ever"], "data/derived/C22/other-families.json:...null.e_rate.ever", 1, pct=True)
    put("CommittedMedThree", cs("rate-x3", "e_rate")["median_day"], "data/derived/C22/other-families.json:...rate-x3.e_rate.median_day", 0)
    put("CommittedMedFour", cs("rate-x4", "e_rate")["median_day"], "data/derived/C22/other-families.json:...rate-x4.e_rate.median_day", 0)
    put("CommittedCluMedFourTenthLight", cs("cluster-0.4", "traffic_light")["median_day"],
        "data/derived/C22/other-families.json:...cluster-0.4.traffic_light.median_day", 0)
    cc = cs("rate-x3", "kupiec_one_shot_power") - cs("rate-x3", "e_rate")["by"]
    put("CommittedCostThree", cc, "derived: kupiec_one_shot_power - e_rate.by, rate-x3, committed document", 1, pct=True)
    cc4 = cs("rate-x4", "kupiec_one_shot_power") - cs("rate-x4", "e_rate")["by"]
    put("CommittedCostFour", cc4, "derived: kupiec_one_shot_power - e_rate.by, rate-x4, committed document", 1, pct=True)

    # size over the horizon
    last = SH["days"][-1]
    put("HorizonDays", last, "results_size_horizon.json:days[-1]", thousands=True)
    put("HorizonReps", SH["meta"]["reps"], "results_size_horizon.json:meta.reps", thousands=True)
    for nm, key in (("E", "e_rate"), ("Wwz", "e_wwz"), ("Beta", "e_beta"), ("KupCum", "kupiec_cumulative"), ("KupTrail", "kupiec_trailing"),
                    ("Light", "traffic_light"), ("KupCal", "kupiec_calibrated"), ("Cusum", "cusum_calibrated")):
        c = SH["curves"][key]["share"]
        put(f"HorizonEnd{nm}", c[-1], f"results_size_horizon.json:curves.{key}.share[-1]", 1, pct=True)
        i1000 = SH["days"].index(1000)
        put(f"HorizonThousand{nm}", c[i1000], f"results_size_horizon.json:curves.{key}.share[day 1000]", 1, pct=True)
        i250 = SH["days"].index(250)
        put(f"HorizonWindow{nm}", c[i250], f"results_size_horizon.json:curves.{key}.share[day 250]", 1, pct=True)

    # exact size and power at day 250
    sm = TH["size_matched_power"]
    put("ExactKupSize", sm["kupiec_size"], "results_theory.json:size_matched_power.kupiec_size", 1, pct=True)
    put("ExactKupUpperSize", sm["kupiec_upper_size"], "results_theory.json:size_matched_power.kupiec_upper_size", 2, pct=True)
    put("ExactKupMinCount", sm["kupiec_smallest_rejecting_count"], "results_theory.json:size_matched_power.kupiec_smallest_rejecting_count")
    put("ExactESize", sm["e_process_size_by_window"], "results_theory.json:size_matched_power.e_process_size_by_window", 2, pct=True)
    put("ExactESizeMc", TH["meta"]["e_process_size_monte_carlo"], "results_theory.json:meta.e_process_size_monte_carlo", 2, pct=True)
    sp = TH["exact_spending"]
    put("ExactEUpSize", sp["rate_upper"]["by_250"], "results_theory.json:exact_spending.rate_upper.by_250", 2, pct=True)
    put("ExactEThousand", sp["rate_two_sided"]["by_1000"], "results_theory.json:exact_spending.rate_two_sided.by_1000", 2, pct=True)
    put("ExactSingleThreeSize", sm["single_3_size_by_window"], "results_theory.json:size_matched_power.single_3_size_by_window", 2, pct=True)
    put("ExactSingleThreeNp", sm["single_3_np_power_at_3"], "results_theory.json:size_matched_power.single_3_np_power_at_3", 1, pct=True)
    os_ = TH["one_shot_sizes"]
    put("ExactOneShotKup", os_["kupiec"], "results_theory.json:one_shot_sizes.kupiec", 2, pct=True)
    put("ExactOneShotLight", os_["traffic_light"], "results_theory.json:one_shot_sizes.traffic_light", 2, pct=True)
    put("ProductRejectDayTen", TH["product_counterexample"]["hits_rate_times_cluster"]["reject_probability_by_day_10"],
        "results_theory.json:product_counterexample.hits_rate_times_cluster.reject_probability_by_day_10", 1, pct=True)
    # the single alternative matched to the severity, at every severity of the ladder
    for tag, f in (("OneFive", "x1.5"), ("Two", "x2"), ("Three", "x3"), ("Four", "x4"), ("Six", "x6"), ("Ten", "x10")):
        r = MT["factors"][f]
        v = r["median_day"]
        put(f"Matched{tag}Med", "beyond the horizon" if v is None else f"{v:.0f}", f"results_matched.json:factors.{f}.median_day")
        lo, hi = r["median_ci"]
        put(f"Matched{tag}MedLo", "--" if lo is None else f"{lo:.0f}", f"results_matched.json:factors.{f}.median_ci[0]")
        put(f"Matched{tag}MedHi", "--" if hi is None else f"{hi:.0f}", f"results_matched.json:factors.{f}.median_ci[1]")
        put(f"Matched{tag}By", r["by"], f"results_matched.json:factors.{f}.by", 1, pct=True)
    for tag, f in (("OneFive", "x1.5"), ("Two", "x2"), ("Three", "x3"), ("Four", "x4"), ("Six", "x6")):
        r = sm["factors"][f]
        put(f"Exact{tag}Kup", r["kupiec_power"], f"results_theory.json:size_matched_power.factors.{f}.kupiec_power", 1, pct=True)
        put(f"Exact{tag}KupUp", r["kupiec_upper_power"], f"results_theory.json:size_matched_power.factors.{f}.kupiec_upper_power", 1, pct=True)
        put(f"Exact{tag}NpE", r["np_power_at_e_process_size"], f"results_theory.json:size_matched_power.factors.{f}.np_power_at_e_process_size", 1, pct=True)
        put(f"Exact{tag}NpEUp", r["np_power_at_upper_size"], f"results_theory.json:size_matched_power.factors.{f}.np_power_at_upper_size", 1, pct=True)
        put(f"Exact{tag}NpKup", r["np_power_at_kupiec_size"], f"results_theory.json:size_matched_power.factors.{f}.np_power_at_kupiec_size", 1, pct=True)
        put(f"Exact{tag}NpFive", r["np_power_at_five_percent"], f"results_theory.json:size_matched_power.factors.{f}.np_power_at_five_percent", 1, pct=True)

    # theory: null expectation and the product
    ne = TH["null_expectation"]
    worst = max(v["max_abs_departure_from_one"] for v in ne["processes"].values())
    put("EnumWorst", f"{worst:.1e}".replace("e-", "\\times 10^{-") + "}", "results_theory.json:null_expectation.processes.*.max_abs_departure_from_one")
    put("EnumSequences", ne["sequences"], "results_theory.json:null_expectation.sequences", thousands=True)
    put("ProductMax", TH["product_counterexample"]["hits_rate_times_cluster"]["max_expectation"],
        "results_theory.json:product_counterexample.hits_rate_times_cluster.max_expectation", 0)
    put("ProductPdProduct", TH["product_counterexample"]["pd_two_identical_grades"]["expectation_product"],
        "results_theory.json:product_counterexample.pd_two_identical_grades.expectation_product", 2)
    put("ProductPdAverage", TH["product_counterexample"]["pd_two_identical_grades"]["expectation_average"],
        "results_theory.json:product_counterexample.pd_two_identical_grades.expectation_average", 2)
    for r in TH["kl"]["rows"]:
        tag = {1.5: "OneFive", 2.0: "Two", 3.0: "Three", 4.0: "Four", 6.0: "Six", 10.0: "Ten"}[r["factor"]]
        s = f"results_theory.json:kl.rows[factor={r['factor']}]."
        put(f"Kl{tag}", 1000 * r["kl_vs_null"], s + "kl_vs_null (x1000)", 2)
        put(f"KlSprt{tag}", r["sprt_time"], s + "sprt_time", 0)
        put(f"KlMix{tag}", r["mixture_time_bound"], s + "mixture_time_bound", 0)
    quiet = -math.log((1 - 0.03) / (1 - 0.01))
    gain = math.log(3.0)
    need = next(k for k in range(1, 251) if k * gain - (250 - k) * quiet >= math.log(20))
    put("SingleQuietCost", quiet, "derived: -ln((1 - 3 alpha) / (1 - alpha)) at alpha = 0.01", 2)
    put("SingleHitGain", gain, "derived: ln 3", 1)
    put("SingleHitsNeeded", need, "derived: least k with k ln 3 - (250 - k) quiet >= ln 20")
    put("LogTwenty", math.log(20), "derived: ln 20", 2)
    put("LogEight", math.log(8), "derived: ln 8", 2)

    # ablation
    g = AB["hits_grid"]
    for vid, nm in (("full", "Full"), ("upper", "Upper"), ("upper-low", "UpperLow"), ("upper-high", "UpperHigh"), ("single-1.5", "SingleOneFive"),
                    ("single-2", "SingleTwo"), ("single-3", "SingleThree"), ("single-4", "SingleFour"), ("single-10", "SingleTen")):
        put(f"AbNull{nm}", g["null"][vid]["ever"], f"results_ablation.json:hits_grid.null.{vid}.ever", 1, pct=True)
        for sid, tag in (("rate-x2", "Two"), ("rate-x3", "Three"), ("rate-x4", "Four"), ("rate-x6", "Six")):
            put(f"AbBy{tag}{nm}", g[sid][vid]["by"], f"results_ablation.json:hits_grid.{sid}.{vid}.by", 1, pct=True)
            v = g[sid][vid]["median_day"]
            put(f"AbMed{tag}{nm}", "beyond the horizon" if v is None else f"{v:.0f}", f"results_ablation.json:hits_grid.{sid}.{vid}.median_day")
            put(f"AbEver{tag}{nm}", g[sid][vid]["ever"], f"results_ablation.json:hits_grid.{sid}.{vid}.ever", 1, pct=True)
    b = AB["hits_battery"]
    for vid, nm in (("rate", "Rate"), ("cluster", "Cluster"), ("average", "Average"), ("union", "Union"), ("product", "Product")):
        for sid, tag in (("null", "Null"), ("rate-x3", "Three"), ("cluster-0.2", "ClTwo"), ("cluster-0.4", "ClFour")):
            put(f"AbBat{tag}{nm}", b[sid][vid]["ever"], f"results_ablation.json:hits_battery.{sid}.{vid}.ever", 1, pct=True)
    pdb = AB["pd_combine"]
    for sid, tag in (("all-x1", "One"), ("all-x1.05", "OneZeroFive"), ("all-x1.1", "OneOne"), ("all-x1.25", "OneTwoFive"), ("grade5-x1.3", "Grade")):
        for vid, nm in (("product", "Prod"), ("product-upper", "ProdUp"), ("average", "Avg"), ("average-upper", "AvgUp"),
                        ("average-upper-coarse", "Coarse"), ("average-upper-single-1.25", "Single"),
                        ("chi2-one-shot-year-10", "ChiOne"), ("chi2-every-year", "ChiEvery")):
            put(f"Pd{tag}{nm}", pdb[sid][vid]["ever"], f"results_ablation.json:pd_combine.{sid}.{vid}.ever", 1, pct=True)
    put("PdReps", AB["meta"]["pd_reps"], "results_ablation.json:meta.pd_reps", thousands=True)
    for sid, tag in (("all-x1.1", "OneOne"), ("all-x1.25", "OneTwoFive")):
        v = pdb[sid]["average-upper"]["median_year_among_detected"]
        put(f"PdMedYear{tag}", "--" if v is None else f"{v:.0f}", f"results_ablation.json:pd_combine.{sid}.average-upper.median_year_among_detected")

    # asset correlation
    for r in PC["rows"]:
        tag = {0.0: "Zero", 0.03: "ZeroThree", 0.12: "OneTwo", 0.24: "TwoFour"}[r["rho"]]
        for key, nm in (("e_product", "Prod"), ("e_average", "Avg"), ("e_average_upper", "AvgUp"), ("chi2_one_shot_year_10", "ChiOne"),
                        ("chi2_every_year", "ChiEvery")):
            put(f"Rho{tag}{nm}", r[key]["ever"], f"results_pd_correlation.json:rows[rho={r['rho']}].{key}.ever", 1, pct=True)
    put("RhoReps", PC["meta"]["reps"], "results_pd_correlation.json:meta.reps", thousands=True)

    # the product's own PD tests and the chi-square rule of equal size, on the same histories
    rule_tag = {"binomial": "Bin", "jeffreys": "Jef", "vasicek_assumed": "VasAssumed", "vasicek_true": "VasTrue"}
    for r in PDC["correlation"]:
        tag = {0.0: "Zero", 0.03: "ZeroThree", 0.12: "OneTwo", 0.24: "TwoFour"}[r["rho"]]
        for k, nm in rule_tag.items():
            for rd, rn in (("every_year", "Every"), ("once", "Once")):
                put(f"Pdc{tag}{nm}{rn}", r[k][rd]["ever"], f"results_pd_comparators.json:correlation[rho={r['rho']}].{k}.{rd}.ever", 1, pct=True)
        put(f"Pdc{tag}ChiSim", r["chi2_sim"]["ever"], f"results_pd_comparators.json:correlation[rho={r['rho']}].chi2_sim.ever", 1, pct=True)
        put(f"Pdc{tag}ChiMatched", r["chi2_matched"]["ever"], f"results_pd_comparators.json:correlation[rho={r['rho']}].chi2_matched.ever", 1, pct=True)
    eq = PDC["equal_size_chi2"]
    put("PdcMatchedSize", eq["matched_size"], "results_pd_comparators.json:equal_size_chi2.matched_size (the average e-process size, results_ablation.json)", 1, pct=True)
    put("PdcCalReps", PDC["meta"]["calibration_reps"], "results_pd_comparators.json:meta.calibration_reps", thousands=True)
    put("PdcAssumedRho", PDC["meta"]["assumed_rho"], "results_pd_comparators.json:meta.assumed_rho", 2)
    put("PdcBonferroniEvery", PDC["meta"]["bonferroni_every_year"], "results_pd_comparators.json:meta.bonferroni_every_year", 3)
    for sid, tag in (("all-x1", "One"), ("all-x1.05", "OneZeroFive"), ("all-x1.1", "OneOne"), ("all-x1.25", "OneTwoFive"), ("grade5-x1.3", "Grade")):
        v = eq["scenarios"][sid]
        for k, nm in (("chi2_sim", "ChiSim"), ("chi2_matched", "ChiMatched")):
            put(f"Pdc{tag}{nm}", v[k]["ever"], f"results_pd_comparators.json:equal_size_chi2.scenarios.{sid}.{k}.ever", 1, pct=True)
            put(f"Pdc{tag}{nm}By", v[k]["by3"], f"results_pd_comparators.json:equal_size_chi2.scenarios.{sid}.{k}.by3", 1, pct=True)
            my = v[k]["median_year_among_detected"]
            put(f"Pdc{tag}{nm}Year", "--" if my is None else f"{my:.0f}", f"results_pd_comparators.json:equal_size_chi2.scenarios.{sid}.{k}.median_year_among_detected")
        for k, nm in rule_tag.items():
            if k in v:
                put(f"Pdc{tag}{nm}Every", v[k]["every_year"]["ever"], f"results_pd_comparators.json:equal_size_chi2.scenarios.{sid}.{k}.every_year.ever", 1, pct=True)
                put(f"Pdc{tag}{nm}Once", v[k]["once"]["ever"], f"results_pd_comparators.json:equal_size_chi2.scenarios.{sid}.{k}.once.ever", 1, pct=True)
        pa = AB["pd_combine"][sid]["average"]
        put(f"Pdc{tag}AvgBy", pa["by3"], f"results_ablation.json:pd_combine.{sid}.average.by3", 1, pct=True)
        my = pa["median_year_among_detected"]
        put(f"Pdc{tag}AvgYear", "--" if my is None else f"{my:.0f}", f"results_ablation.json:pd_combine.{sid}.average.median_year_among_detected")

    # real data
    for w, tag in (("calm-2004-06", "Calm"), ("equity-2007-09", "Equity"), ("fx-2008", "Fx"), ("equity-2020", "Covid"), ("rates-2022", "Rates"),
                   ("mixed-2023", "Mixed")):
        wd = C11["windows"][w]
        put(f"CElevenDays{tag}", wd["n_days"], f"results_c11.json:windows.{w}.n_days")
        for lvl, lt in (("0.01", "Ninety"), ("0.025", "Seventy")):
            s = wd["levels"][lvl]["summary"]
            for key, nm in (("e_rate", "E"), ("e_rate_upper", "EUp"), ("e_wwz", "Wwz"), ("kupiec_end", "KupEnd"), ("kupiec_cumulative", "KupCum"),
                            ("kupiec_sidak", "KupSidak"), ("kupiec_trailing", "KupTrail"), ("traffic_light", "Light")):
                put(f"CEleven{tag}{lt}{nm}Flag", s[key]["flagged"], f"results_c11.json:windows.{w}.levels.{lvl}.summary.{key}.flagged")
                v = s[key]["median_day"]
                put(f"CEleven{tag}{lt}{nm}Med", "--" if v is None else f"{v:.0f}", f"results_c11.json:windows.{w}.levels.{lvl}.summary.{key}.median_day")
                fd = s[key]["first_day"]
                put(f"CEleven{tag}{lt}{nm}First", "--" if fd is None else f"{fd:.0f}", f"results_c11.json:windows.{w}.levels.{lvl}.summary.{key}.first_day")
            o = s["overlap"]
            for key in ("e_only_vs_kupiec_end", "kupiec_end_only_vs_e", "light_missed_by_e", "e_before_kupiec_end", "e_and_kupiec_end", "e_and_light"):
                put(f"CEleven{tag}{lt}{''.join(p.capitalize() for p in key.split('_'))}", o[key], f"results_c11.json:windows.{w}.levels.{lvl}.summary.overlap.{key}")
            for key, nm in (("median_e_day_among_light_flagged", "LightE"), ("median_light_day", "LightDay")):
                v = o[key]
                txt = "--" if v is None else ("never" if not math.isfinite(v) else f"{v:.0f}")
                put(f"CEleven{tag}{lt}{nm}", txt, f"results_c11.json:windows.{w}.levels.{lvl}.summary.overlap.{key}")
    put("CElevenModels", C11["windows"]["equity-2007-09"]["levels"]["0.01"]["summary"]["n_models"], "results_c11.json:windows.equity-2007-09.levels.0.01.summary.n_models")

    # C03
    for stem, tag in (("fy2006-07", "A"), ("fy2008-10", "B"), ("fy2011-14", "C"), ("fy2015-17", "D"), ("fy2018-20", "E")):
        c = C03["cohorts"][stem]
        a, p = c["average"]["rejection_month"], c["product"]["rejection_month"]
        put(f"CThreeAvg{tag}", "never" if a is None else str(a), f"results_c03.json:cohorts.{stem}.average.rejection_month")
        put(f"CThreeProd{tag}", "never" if p is None else str(p), f"results_c03.json:cohorts.{stem}.product.rejection_month")
        put(f"CThreeMax{tag}", c["average"]["max_log_e"], f"results_c03.json:cohorts.{stem}.average.max_log_e", 1, thousands=True)
        for v in c["vintages"]:
            put(f"CThreeD{yw(v['fiscal_year'])}", v["defaults"], f"results_c03.json:cohorts.{stem}.vintages[{v['fiscal_year']}].defaults", thousands=True)
            put(f"CThreeP{yw(v['fiscal_year'])}", v["predicted_defaults"], f"results_c03.json:cohorts.{stem}.vintages[{v['fiscal_year']}].predicted_defaults", thousands=True)
            put(f"CThreeV{yw(v['fiscal_year'])}", v["max_log_e"], f"results_c03.json:cohorts.{stem}.vintages[{v['fiscal_year']}].max_log_e", 1)
            put(f"CThreeRej{yw(v['fiscal_year'])}", "never" if v["rejection_month"] is None else str(v["rejection_month"]),
                f"results_c03.json:cohorts.{stem}.vintages[{v['fiscal_year']}].rejection_month")
            put(f"CThreeN{yw(v['fiscal_year'])}", v["n"], f"results_c03.json:cohorts.{stem}.vintages[{v['fiscal_year']}].n", thousands=True)
    put("CThreeRebuilt", sum(c["recomputed_equals_committed"] for c in C03["cohorts"].values()), "results_c03.json:cohorts.*.recomputed_equals_committed")


def run_times() -> None:
    """The wall time of each experiment script and the interpreter, from ``experiments/run-times.json`` (written by run_all.py)."""
    path = EXP / "run-times.json"
    if not path.exists():
        print("WARNING: experiments/run-times.json is missing; run experiments/run_all.py before the final build", file=sys.stderr)
        rt = {"seconds": {}, "total_seconds": float("nan"), "python": "NA"}
    else:
        rt = json.loads(path.read_text(encoding="utf-8"))
    secs = rt["seconds"]
    for name, script in (("Hits", "exp_hits.py"), ("Ablation", "exp_ablation.py"), ("Seeds", "exp_x3_seeds.py"), ("Pd", "exp_pd_correlation.py"),
                         ("CEleven", "exp_c11.py"), ("CThree", "exp_c03.py"), ("Theory", "exp_theory.py"), ("Matched", "exp_matched.py"),
                         ("PdComparators", "exp_pd_comparators.py")):
        v = secs.get(script)
        put(f"Run{name}", "NA" if v is None else f"{v:,.0f}", f"run-times.json:seconds.{script}")
    tot = rt["total_seconds"]
    put("RunTotal", "NA" if tot != tot else f"{tot:,.0f}", "run-times.json:total_seconds")
    put("PythonVersion", rt["python"], "run-times.json:python")


def main() -> None:
    build()
    run_times()
    lines = ["% Generated by make_numbers.py from experiments/results_*.json: every number the prose quotes. Do not edit."]
    for name, (text, _) in REG.items():
        lines.append(f"\\newcommand{{\\n{name}}}{{{text}}}")
    (HERE / "numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    manifest = {f"n{name}": {"value": text, "source": src} for name, (text, src) in REG.items()}
    (EXP / "numbers-manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"{len(REG)} macros written")


if __name__ == "__main__":
    main()
