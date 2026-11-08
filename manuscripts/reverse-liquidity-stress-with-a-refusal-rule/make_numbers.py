"""Write ``tables/numbers.tex``: one macro per number quoted in the prose, each preceded by a comment naming its source.

    python manuscripts/reverse-liquidity-stress-with-a-refusal-rule/make_numbers.py

The numbers come from ``experiments/results_*.json`` and from the committed documents of ``data/derived/C16``; none is typed. The module
also exposes ``reg`` and ``NUM`` so that ``make_tables.py`` registers the numbers it prints in a table through the same path.
"""
from __future__ import annotations

import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE / "experiments"
ROOT = HERE.parents[1]

NUM: list[tuple[str, str, str]] = []


def load(name: str) -> dict:
    return json.loads((EXP / name).read_text(encoding="utf-8"))


def reg(name: str, value: str, source: str) -> str:
    NUM.append((name, value, source))
    return value


def pc(x: float, d: int = 1) -> str:
    return f"{100.0 * x:.{d}f}"


def ci(r: dict, d: int = 1) -> str:
    return f"{pc(r['rate'], d)} ({pc(r['lo'], d)} to {pc(r['hi'], d)})"


def build() -> None:
    C = load("results_reverse_c16.json")
    K = load("results_corpus.json")
    T = load("results_theory.json")
    M = json.loads((ROOT / "data" / "derived" / "C16" / "models-svb-liquidity.json").read_text(encoding="utf-8"))["fit"]
    a, e, f = C["bases"]["list-adverse"], C["bases"]["list-extreme"], C["bases"]["fast-run"]
    L = C["labelled_run"]
    s = "results_reverse_c16.json"
    reg("mAdv", f"{a['engine']['multiplier']:.6f}", f"{s} bases.list-adverse.engine.multiplier")
    reg("mExt", f"{e['engine']['multiplier']:.6f}", f"{s} bases.list-extreme.engine.multiplier")
    reg("spAdv", str(a["base_sp"]), f"{s} bases.list-adverse.base_sp")
    reg("spExt", str(e["base_sp"]), f"{s} bases.list-extreme.base_sp")
    reg("capAdv", f"{a['cap']:.1f}", f"{s} bases.list-adverse.cap")
    reg("capExt", f"{e['cap']:.1f}", f"{s} bases.list-extreme.cap")
    reg("capFast", f"{f['cap']:.2f}", f"{s} bases.fast-run.cap")
    reg("evalsSolve", str(a["engine"]["evals"]), f"{s} bases.list-adverse.engine.evals")
    reg("timeAdvMs", f"{a['time_us_median'] / 1000:.1f}", f"{s} bases.list-adverse.time_us_median")
    reg("timeExtMs", f"{e['time_us_median'] / 1000:.1f}", f"{s} bases.list-extreme.time_us_median")
    reg("hypAdv", f"{a['hyperbolic_rule']['value']:.3f}", f"{s} bases.list-adverse.hyperbolic_rule.value")
    reg("hypExt", f"{e['hyperbolic_rule']['value']:.3f}", f"{s} bases.list-extreme.hyperbolic_rule.value")
    reg("hypAdvErr", pc(a["hyperbolic_rule"]["rel_error"]), f"{s} bases.list-adverse.hyperbolic_rule.rel_error x 100")
    reg("hypExtErr", pc(e["hyperbolic_rule"]["rel_error"]), f"{s} bases.list-extreme.hyperbolic_rule.rel_error x 100")
    reg("rawAdv", f"{a['raw_capacity_multiplier']:.6f}", f"{s} bases.list-adverse.raw_capacity_multiplier")
    reg("rawExt", f"{e['raw_capacity_multiplier']:.6f}", f"{s} bases.list-extreme.raw_capacity_multiplier")
    reg("rawAdvPct", pc(a["raw_capacity_multiplier"] / a["engine"]["multiplier"] - 1.0), f"{s} raw over engine, adverse, percent")
    d = C["derivative"]
    reg("elastAdv", f"{d['list-adverse']['elasticity']:.2f}", f"{s} derivative.list-adverse.elasticity")
    reg("derivRelAdv", f"{100 * d['list-adverse']['rel_difference']:.4f}", f"{s} derivative.list-adverse.rel_difference x 100")
    reg("derivRelExt", f"{100 * d['list-extreme']['rel_difference']:.4f}", f"{s} derivative.list-extreme.rel_difference x 100")
    reg("capTzero", f"{d['list-adverse']['capacity_at_t0'] / 1e6:.1f}", f"{s} derivative.list-adverse.capacity_at_t0 / 1e6 (USD billion; money in thousands)")
    reg("dayZeroAdv", str(d["list-adverse"]["t0_day"]), f"{s} derivative.list-adverse.t0_day")
    ba = C["band"]["list-adverse"]
    be = C["band"]["list-extreme"]
    one = {r["factor"]: r for r in ba["one_at_a_time"]}
    reg("hcLowAdv", f"{one['haircut low']['multiplier']:.6f}", f"{s} band.list-adverse.one_at_a_time haircut low")
    reg("hcHighAdv", f"{one['haircut high']['multiplier']:.6f}", f"{s} band.list-adverse.one_at_a_time haircut high")
    reg("hcLowAdvPct", pc(one["haircut low"]["multiplier"] / a["engine"]["multiplier"] - 1.0), f"{s} haircut low over central, percent")
    reg("hcHighAdvPct", pc(1.0 - one["haircut high"]["multiplier"] / a["engine"]["multiplier"]), f"{s} haircut high under central, percent")
    reg("jointMinAdv", f"{ba['joint_min']:.6f}", f"{s} band.list-adverse.joint_min")
    reg("jointMaxAdv", f"{ba['joint_max']:.6f}", f"{s} band.list-adverse.joint_max")
    reg("jointDevAdv", pc(ba["joint_max_rel_deviation"]), f"{s} band.list-adverse.joint_max_rel_deviation x 100")
    reg("slowSpAdv", str([r for r in ba["one_at_a_time"] if r["factor"] == "monetisation slow"][0]["reason"].split("of ")[1].split(" days")[0]),
        f"{s} band.list-adverse monetisation slow refusal")
    reg("slowSpExt", str([r for r in be["one_at_a_time"] if r["factor"] == "monetisation slow"][0]["reason"].split("of ")[1].split(" days")[0]),
        f"{s} band.list-extreme monetisation slow refusal")
    reg("jointSolvedAdv", str(sum(1 for r in ba["haircut_x_monetisation"] if r["multiplier"] is not None)), f"{s} band.list-adverse solved combinations of 9")
    mapa = {r["mapping"]: r for r in ba["mapping"]}
    reg("opAdv", f"{mapa['operational deposits']['multiplier']:.6f}", f"{s} band.list-adverse.mapping operational")
    reg("opSpAdv", str(mapa["operational deposits"]["base_sp"]), f"{s} band.list-adverse.mapping operational base_sp")
    reg("legalSp", str(mapa["other legal entities"]["base_sp"]), f"{s} band.list-adverse.mapping other legal entities base_sp")
    ua = ba["uninsured_share"]
    reg("uninsLowAdv", f"{ua[0]['multiplier']:.3f}", f"{s} band.list-adverse.uninsured_share[0]")
    reg("uninsHighAdv", f"{ua[-1]['multiplier']:.3f}", f"{s} band.list-adverse.uninsured_share[-1]")
    reg("tMaxAdv", str(ba["by_target_solved_up_to"]), f"{s} band.list-adverse.by_target_solved_up_to")
    reg("tMaxExt", str(be["by_target_solved_up_to"]), f"{s} band.list-extreme.by_target_solved_up_to")
    reg("svbModel", f"{L['svb_modelled_2d']:.4f}", f"{s} labelled_run.svb_modelled_2d")
    reg("svbRatio", f"{L['svb_ratio_2d']:.3f}", f"{s} labelled_run.svb_ratio_2d")
    rows = {r["bank"]: r for r in L["rows"]}
    reg("ukModel", f"{rows['SVB UK']['modelled']:.4f}", f"{s} labelled_run.rows SVB UK modelled")
    reg("ukRatio", f"{rows['SVB UK']['ratio']:.3f}", f"{s} labelled_run.rows SVB UK ratio")
    reg("sigRatio", f"{rows['Signature']['ratio']:.3f}", f"{s} labelled_run.rows Signature ratio")
    reg("nrModel", f"{rows['Northern Rock']['modelled']:.4f}", f"{s} labelled_run.rows Northern Rock modelled")
    reg("nrRatio", f"{rows['Northern Rock']['ratio']:.3f}", f"{s} labelled_run.rows Northern Rock ratio")
    reg("depRatio", f"{L['denominators'][1]['ratio']:.3f}", f"{s} labelled_run.denominators call-report-dep ratio")
    reg("depShare", f"{L['denominators'][1]['realised_share']:.3f}", f"{s} labelled_run.denominators call-report-dep realised_share")
    rl = {r["rule"]: r for r in L["rules"]}
    reg("rateMax", f"{rl['maximum-implied-daily-rate']['rate']:.6f}", f"{s} labelled_run.rules max")
    reg("rateMed", f"{rl['median-implied-daily-rate']['rate']:.6f}", f"{s} labelled_run.rules median")
    reg("rateMean", f"{rl['mean-implied-daily-rate']['rate']:.6f}", f"{s} labelled_run.rules mean")
    reg("medRatio", f"{rl['median-implied-daily-rate']['ratio_2d']:.3f}", f"{s} labelled_run.rules median ratio")
    reg("meanRatio", f"{rl['mean-implied-daily-rate']['ratio_2d']:.3f}", f"{s} labelled_run.rules mean ratio")
    loo = {r["left_out"]: r["rate"] for r in L["leave_one_out"]}
    reg("looNr", f"{loo['Northern Rock']:.6f}", f"{s} labelled_run.leave_one_out Northern Rock")
    reg("mSvb", f"{L['multiplier_of_labelled_run']:.2f}", f"{s} labelled_run.multiplier_of_labelled_run")
    reg("mTwo", f"{L['reverse_by_target']['2']['multiplier']:.6f}", f"{s} labelled_run.reverse_by_target.2.multiplier")
    reg("mFour", f"{L['reverse_by_target']['4']['multiplier']:.5f}", f"{s} labelled_run.reverse_by_target.4.multiplier")
    reg("spBelowTwo", str(L["reverse_by_target"]["2"]["sp_just_below"]), f"{s} labelled_run.reverse_by_target.2.sp_just_below")
    reg("ratioLab", f"{L['ratio_labelled_to_reverse_t2']:.2f}", f"{s} labelled_run.ratio_labelled_to_reverse_t2")
    reg("svbAdvTotal", f"{L['opening_total'] / 1e6:.1f}", f"{s} labelled_run.opening_total / 1e6 (USD billion)")
    t = "results_theory.json"
    reg("thMonoCmp", f"{T['monotone_in_multiplier']['comparisons']:,}", f"{t} monotone_in_multiplier.comparisons")
    reg("thMonoBanks", f"{T['monotone_in_multiplier']['banks']:,}", f"{t} monotone_in_multiplier.banks")
    cf = T["closed_form_single_segment"]
    reg("thCfN", f"{cf['instances']:,}", f"{t} closed_form_single_segment.instances")
    reg("thCfSolved", f"{cf['solved']:,}", f"{t} closed_form_single_segment.solved")
    reg("thCfMax", f"{cf['max_abs_difference'] * 1e6:.4f}", f"{t} closed_form_single_segment.max_abs_difference x 1e6")
    reg("thCfMed", f"{cf['median_abs_difference'] * 1e6:.3f}", f"{t} closed_form_single_segment.median_abs_difference x 1e6")
    reg("thHypN", f"{cf['hyperbolic_instances']:,}", f"{t} closed_form_single_segment.hyperbolic_instances")
    reg("thHypMed", pc(cf["hyperbolic_relative_error_median"]), f"{t} hyperbolic_relative_error_median x 100")
    reg("thHypQninety", pc(cf["hyperbolic_relative_error_q90"]), f"{t} hyperbolic_relative_error_q90 x 100")
    reg("thTgtPairs", f"{T['monotone_in_target']['pairs']:,}", f"{t} monotone_in_target.pairs")
    reg("thCapPairs", f"{T['monotone_in_capacity']['pairs']:,}", f"{t} monotone_in_capacity.pairs")
    er = T["exact_round_trip"]
    reg("thErN", f"{er['solved_flat_no_inflow']:,}", f"{t} exact_round_trip.solved_flat_no_inflow")
    reg("thErMarginMin", f"{er['margin_min']:.0f}", f"{t} exact_round_trip.margin_min")
    # the corpus
    k = "results_corpus.json"
    dsg = K["design"]
    reg("kInst", f"{dsg['instances']:,}", f"{k} design.instances")
    reg("kBanks", f"{dsg['banks_per_seed'] * len(dsg['seeds']):,}", f"{k} design banks_per_seed x seeds")
    reg("kRefused", f"{dsg['instances'] - dsg['solved']:,}", f"{k} design.instances - design.solved")
    reg("kSolved", f"{dsg['solved']:,}", f"{k} design.solved")
    reg("kHor", f"{dsg['refused_horizon']:,}", f"{k} design.refused_horizon")
    reg("kBase", f"{dsg['refused_base']:,}", f"{k} design.refused_base")
    reg("kUnr", f"{dsg['refused_unreachable']:,}", f"{k} design.refused_unreachable")
    reg("kFlat", f"{dsg['solved_flat_no_inflow']:,}", f"{k} design.solved_flat_no_inflow")
    reg("kGrow", f"{dsg['solved_growing']:,}", f"{k} design.solved_growing")
    reg("kWallMin", f"{dsg['wall_seconds_total'] / 60:.0f}", f"{k} design.wall_seconds_total / 60")
    reg("kWallSec", f"{dsg['wall_seconds_total']:,.1f}", f"{k} design.wall_seconds_total")
    reg("kProc", K["platform"]["processor"] or K["platform"]["machine"], f"{k} platform.processor")
    reg("kPy", K["platform"]["python"], f"{k} platform.python")
    mm = K["methods"]
    for key, nm in (("proposed", "P"), ("grid_case", "G"), ("grid_fine", "F"), ("brent_sp", "B"), ("bisect_no_refusal", "N"), ("uncapped", "U"),
                    ("nearest", "R"), ("raw_capacity", "W")):
        x = mm[key]
        reg(f"k{nm}False", ci(x["false_answer_on_refused"]), f"{k} methods.{key}.false_answer_on_refused")
        reg(f"k{nm}FalseK", f"{x['false_answer_on_refused']['k']:,}", f"{k} methods.{key}.false_answer_on_refused.k")
        reg(f"k{nm}Miss", ci(x["miss_on_solved"]), f"{k} methods.{key}.miss_on_solved")
        reg(f"k{nm}MissK", f"{x['miss_on_solved']['k']:,}", f"{k} methods.{key}.miss_on_solved.k")
        reg(f"k{nm}Thr", ci(x["threshold_property_on_solved"]), f"{k} methods.{key}.threshold_property_on_solved")
        reg(f"k{nm}Beyond", ci(x["answered_beyond_cap"]), f"{k} methods.{key}.answered_beyond_cap")
        reg(f"k{nm}Err", f"{x['abs_rel_error_median']['est']:.2e}", f"{k} methods.{key}.abs_rel_error_median")
        reg(f"k{nm}ErrPc", pc(x["abs_rel_error_median"]["est"]), f"{k} methods.{key}.abs_rel_error_median x 100")
        reg(f"k{nm}ErrQ", f"{x['abs_rel_error_q95']['est']:.3f}", f"{k} methods.{key}.abs_rel_error_q95")
        reg(f"k{nm}Evals", f"{x['evals_mean_solved']:.1f}", f"{k} methods.{key}.evals_mean_solved")
        reg(f"k{nm}Time", f"{x['time_us_median'] / 1000:.2f}", f"{k} methods.{key}.time_us_median / 1000 (ms)")
        reg(f"k{nm}PerEval", f"{x['time_us_median'] / x['evals_mean_solved'] / 1000:.2f}", f"{k} methods.{key}.time_us_median / evals_mean_solved / 1000 (ms)")
    reg("kHOneDis", str(K["H1"]["disagreements"]), f"{k} H1.disagreements")
    reg("kHTwoMin", f"{K['H2']['diff_min'] * 1e6:.3f}", f"{k} H2.diff_min x 1e6")
    reg("kHTwoMax", f"{K['H2']['diff_max'] * 1e6:.3f}", f"{k} H2.diff_max x 1e6")
    reg("kHThreeMono", ci(K["H3"]["monotone"]), f"{k} H3.monotone")
    reg("kHThreeGrow", ci(K["H3"]["growing"]), f"{k} H3.growing")
    reg("kHThreeGapNine", f"{K['H3']['gap_days_growing_quantiles']['0.9']:.0f}", f"{k} H3.gap quantile 0.9")
    reg("kHThreeGapFifty", f"{K['H3']['gap_days_growing_quantiles']['0.5']:.0f}", f"{k} H3.gap quantile 0.5")
    reg("kHThreeGapMax", f"{K['H3']['gap_days_growing_quantiles']['1.0']:.0f}", f"{k} H3.gap max")
    reg("kHFour", ci(K["H4"]), f"{k} H4")
    reg("kHFourMed", pc(K["H4"]["overshoot_quantiles"]["0.5"]), f"{k} H4.overshoot median x 100")
    reg("kHFourQ", pc(K["H4"]["overshoot_quantiles"]["0.9"]), f"{k} H4.overshoot q90 x 100")
    reg("kHFive", pc(K["H5"]["rate_of_all_solved"]), f"{k} H5.rate_of_all_solved x 100")
    reg("kHSix", ci(K["H6"]), f"{k} H6")
    reg("kHSixMed", pc(K["H6"]["relative_error_quantiles"]["0.5"]), f"{k} H6 median x 100")
    reg("kRawFlows", pc(K["raw_capacity_on_flows"]["median_abs_rel_error"]), f"{k} raw_capacity_on_flows.median_abs_rel_error x 100")
    reg("kRawFlowsN", f"{K['raw_capacity_on_flows']['n']:,}", f"{k} raw_capacity_on_flows.n")
    reg("kMzeroMed", f"{K['m0_quantiles']['0.5']:.2f}", f"{k} m0_quantiles 0.5")
    reg("kMzeroLo", f"{K['m0_quantiles']['0.05']:.2f}", f"{k} m0_quantiles 0.05")
    reg("kMzeroHi", f"{K['m0_quantiles']['0.95']:.1f}", f"{k} m0_quantiles 0.95")
    # the spread over the five corpora and the bootstrap intervals of the median error
    reg("kHSixSd", pc(K["H6"]["sd_over_corpora"]), f"{k} H6.sd_over_corpora x 100")
    reg("kHSixHalf", pc((K["H6"]["hi"] - K["H6"]["lo"]) / 2.0), f"{k} H6 Wilson half-width x 100")
    reg("kHFourSd", pc(K["H4"]["sd_over_corpora"]), f"{k} H4.sd_over_corpora x 100")
    reg("kHFourAll", pc(K["H4"]["k"] / dsg["solved"]), f"{k} H4.k / design.solved x 100")
    reg("kHFourAns", f"{K['H4']['answered_solved']:,}", f"{k} H4.answered_solved")
    reg("kGFalseSd", pc(mm["grid_case"]["false_answer_on_refused"]["sd_over_corpora"]), f"{k} methods.grid_case.false_answer_on_refused.sd_over_corpora x 100")
    reg("kGFalseHalf", pc((mm["grid_case"]["false_answer_on_refused"]["hi"] - mm["grid_case"]["false_answer_on_refused"]["lo"]) / 2.0, 2), f"{k} methods.grid_case.false_answer_on_refused Wilson half-width x 100")
    reg("kGErrLo", pc(mm["grid_case"]["abs_rel_error_median"]["lo"]), f"{k} methods.grid_case.abs_rel_error_median.lo x 100")
    reg("kGErrHi", pc(mm["grid_case"]["abs_rel_error_median"]["hi"]), f"{k} methods.grid_case.abs_rel_error_median.hi x 100")
    # the order of the predictions and the runs, from experiments/record_order.py
    ft = load("file_times.json")["files"]
    reg("tOrdHyp", ft["hypotheses.json"]["clock"], "file_times.json hypotheses.json clock")
    reg("tOrdC", ft["results_reverse_c16.json"]["clock"], "file_times.json results_reverse_c16.json clock")
    reg("tOrdT", ft["results_theory.json"]["clock"], "file_times.json results_theory.json clock")
    reg("tOrdK", ft["results_corpus.json"]["clock"], "file_times.json results_corpus.json clock")
    # the slow-schedule corner of the joint band
    lowslow = [r for r in ba["haircut_x_monetisation"] if r["haircut"] == "low" and r["monetisation"] == "slow"][0]
    reg("lowSlowM", f"{lowslow['multiplier']:.6f}", f"{s} band.list-adverse.haircut_x_monetisation low/slow multiplier")
    reg("lowSlowSp", str(lowslow["sp_at"]), f"{s} band.list-adverse.haircut_x_monetisation low/slow sp_at")
    reg("lowSlowBelow", str(lowslow["sp_just_below"]), f"{s} band.list-adverse.haircut_x_monetisation low/slow sp_just_below")
    reg("lowSlowGap", str(30 - lowslow["sp_at"]), f"{s} target 30 minus low/slow sp_at")
    reg("spAtTwo", str(L["reverse_by_target"]["2"]["sp_at"]), f"{s} labelled_run.reverse_by_target.2.sp_at")
    # numerical checks of the propositions
    reg("thMonoViol", str(T["monotone_in_multiplier"]["violations"]), f"{t} monotone_in_multiplier.violations")
    reg("thMonoLarge", f"{T['monotone_in_multiplier']['largest_increase']:.1e}", f"{t} monotone_in_multiplier.largest_increase")
    reg("thCfMism", str(cf["condition_mismatches"]), f"{t} closed_form_single_segment.condition_mismatches")
    reg("thCfRefused", f"{cf['refused']:,}", f"{t} closed_form_single_segment.refused")
    reg("thCfBelow", str(cf["engine_below_closed_form"]), f"{t} closed_form_single_segment.engine_below_closed_form")
    reg("thCfBoundViol", str(cf["multiplier_bound_violations"]), f"{t} closed_form_single_segment.multiplier_bound_violations")
    reg("thHypViol", str(cf["hyperbolic_bound_violations"]), f"{t} closed_form_single_segment.hyperbolic_bound_violations")
    reg("thTgtBanks", f"{T['monotone_in_target']['banks']:,}", f"{t} monotone_in_target.banks")
    reg("thTgtViol", str(T["monotone_in_target"]["violations"]), f"{t} monotone_in_target.violations")
    reg("thCapBanks", f"{T['monotone_in_capacity']['banks']:,}", f"{t} monotone_in_capacity.banks")
    reg("thCapViol", str(T["monotone_in_capacity"]["violations"]), f"{t} monotone_in_capacity.violations")
    reg("thErExact", f"{er['exact']:,}", f"{t} exact_round_trip.exact")
    reg("thErCond", f"{er['condition_holds']:,}", f"{t} exact_round_trip.condition_holds")
    reg("thErViol", str(er["violations_of_the_proposition"]), f"{t} exact_round_trip.violations_of_the_proposition")
    reg("thErMarginMed", f"{er['margin_median']:,.0f}", f"{t} exact_round_trip.margin_median")
    reg("thSeed", str(T["seed"]), f"{t} seed")


def write() -> None:
    build()
    lines = ["% Generated by make_numbers.py and make_tables.py: one macro per number of the prose; the comment names its source."]
    seen = set()
    for name, value, source in NUM:
        if name in seen:
            continue
        seen.add(name)
        lines.append(f"% {source}")
        lines.append(f"\\newcommand{{\\{name}}}{{{value}}}")
    (HERE / "tables").mkdir(exist_ok=True)
    (HERE / "tables" / "numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote tables/numbers.tex with {len(seen)} macros")


if __name__ == "__main__":
    write()
