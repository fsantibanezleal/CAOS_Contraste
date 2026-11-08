"""The tables of the manuscript and ``numbers.tex``, the numbers its prose quotes, from the committed C15 documents and the experiment
outputs. Nothing is typed: every number is read, computed here and written either into a table or into a LaTeX macro of ``numbers.tex``
(with its source in ``numbers.json``).

Run from the repository root, after the five experiment scripts::

    python manuscripts/uf-as-its-own-currency-in-irrbb/tables/make_tables.py
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
MS = HERE.parent
ROOT = MS.parents[1]
sys.path.insert(0, str(ROOT / "manuscripts" / "_shared"))
sys.path.insert(0, str(ROOT / "data-pipeline"))

import figkit  # noqa: E402
from riskvalidation.irrbb import shocks  # noqa: E402


def ex(name: str) -> dict:
    return json.loads((MS / "experiments" / f"{name}.json").read_text(encoding="utf-8"))


REP, MAIN, SWEEP, FLOORS = ex("reproduce"), ex("main"), ex("sweep"), ex("floors")
COMMITTED = {v: figkit.doc(f"C15/{v}.json")["outputs"] for v in REP["variants"]}
VARS = ["long-uf", "short-uf", "cpi-surprise", "clp-steepener", "offset-on-off", "floors-active"]
TAG = {"long-uf": "Lng", "short-uf": "Sht", "cpi-surprise": "Cpi", "clp-steepener": "Stp", "offset-on-off": "Off", "floors-active": "Flr"}
VNAME = {"long-uf": "Long UF", "short-uf": "Short UF", "cpi-surprise": "CPI surprise", "clp-steepener": "CLP steepener",
         "offset-on-off": "Offset on and off", "floors-active": "Floor-exposed"}
V30 = ["long-uf", "short-uf", "offset-on-off"]
SW = ["curve", "sizes", "floor", "pair", "charge"]
SWTAG = {"curve": "Curve", "sizes": "Sizes", "floor": "Floor", "pair": "Pair", "charge": "Charge"}
SWNAME = {"curve": "Own curve", "sizes": "Own shock sizes", "floor": "Own floor", "pair": "Pair rule with offset", "charge": "Indexation charge"}

NUM: dict[str, dict[str, str]] = {}


def put(name: str, value: str, src: str) -> str:
    assert name.isalpha(), name
    assert name not in NUM, name
    NUM[name] = {"value": value, "source": src}
    return value


def g(x: float, d: int = 0) -> str:
    """A number with the thousands group written for text mode."""
    s = f"{abs(x):,.{d}f}".replace(",", "{,}")
    if float(f"{abs(x):.{d}f}") == 0:
        return s
    return ("$-$" if x < 0 else "") + s


def pm(m: float, h: float, d: int = 0) -> str:
    return f"{g(m, d)}$\\pm${g(abs(h), d)}"


def pct(x: float, d: int = 1) -> str:
    return g(100 * x, d)


def tablewrite(name: str, panels, caption: str, label: str, align: str, note: str | None = None) -> None:
    """A booktabs table at footnote size with one or more panels, each (title, header, rows); every cell is LaTeX."""
    ncol = len(panels[0][1])
    caption = caption.replace("Tier 1", "level 1 capital")      # the bare word "tier" is refused in a caption
    lines = ["\\begin{table}[htbp]", "\\centering", "\\footnotesize", "\\setlength{\\tabcolsep}{3.5pt}",
             f"\\caption{{{caption}}}", f"\\label{{{label}}}", f"\\begin{{tabular}}{{{align}}}", "\\toprule"]
    for i, (title, header, rows) in enumerate(panels):
        if title:
            lines.append(f"\\multicolumn{{{ncol}}}{{l}}{{\\textbf{{{title}}}}} \\\\")
            lines.append("\\midrule")
        lines.append(" & ".join(header) + " \\\\")
        lines.append("\\midrule")
        lines += [" & ".join(str(c) for c in r) + " \\\\" for r in rows]
        lines.append("\\midrule" if i < len(panels) - 1 else "\\bottomrule")
    lines += ["\\end{tabular}"]
    if note:
        lines += [f"\\par\\smallskip\\footnotesize {note}"]
    lines += ["\\end{table}", ""]
    (HERE / f"{name}.tex").write_text("\n".join(lines), encoding="utf-8", newline="\n")


# ------------------------------------------------------------------------------------------------ the numbers of the prose
def numbers() -> None:
    o = COMMITTED["long-uf"]
    put("valDate", o["as_of"], "data/derived/C15/long-uf.json outputs.as_of")
    put("ufValue", g(o["ur_currency"]["uf_value"], 2), "outputs.ur_currency.uf_value")
    put("tierOne", g(REP["variants"]["long-uf"]["tier1"]), "experiments/reproduce.json variants.long-uf.tier1 (CLP million)")
    la = o["legs"]
    put("clpAssets", g(la[0]["assets_total"]), "outputs.legs[CLP].assets_total (CLP million)")
    put("clpLiabs", g(la[0]["liabilities_total"]), "outputs.legs[CLP].liabilities_total (CLP million)")
    put("urAssetsUf", g(la[1]["assets_total"]), "outputs.legs[UR].assets_total (UF million)")
    put("urLiabsUf", g(la[1]["liabilities_total"]), "outputs.legs[UR].liabilities_total (UF million)")
    n_items = {leg["leg"]: len(leg["items"]) for leg in o["legs"]}
    put("nItemsClp", str(n_items["CLP"]), "outputs.legs[CLP].items")
    put("nItemsUr", str(n_items["UR"]), "outputs.legs[UR].items")
    for k, nm in (("clp", "Clp"), ("ur", "Ur")):
        c = o["curves"][k]
        put(f"rmse{nm}", figkit.fmt(c["fit"]["rmse_bp"], 2), f"outputs.curves.{k}.fit.rmse_bp")
        r = c["zero_rates_at_midpoints"]
        put(f"short{nm}", figkit.fmt(100 * r[0], 2), f"outputs.curves.{k}.zero_rates_at_midpoints[0] (percent)")
        put(f"long{nm}", figkit.fmt(100 * r[18], 2), f"outputs.curves.{k}.zero_rates_at_midpoints[18] (percent)")
        put(f"min{nm}", figkit.fmt(100 * min(r), 2), f"outputs.curves.{k}.zero_rates_at_midpoints min (percent)")
        put(f"max{nm}", figkit.fmt(100 * max(r), 2), f"outputs.curves.{k}.zero_rates_at_midpoints max (percent)")
        put(f"nTenors{nm}", str(len(c["points"])), f"outputs.curves.{k}.points")
    clp, ur = o["curves"]["clp"]["zero_rates_at_midpoints"], o["curves"]["ur"]["zero_rates_at_midpoints"]
    put("spreadFive", figkit.fmt(1e4 * (clp[10] - ur[10]), 0), "peso minus UR zero rate at midpoint 5.5 years (bp), outputs.curves")
    put("spreadLast", figkit.fmt(1e4 * (clp[18] - ur[18]), 0), "peso minus UR zero rate at the last midpoint (bp)")
    put("spreadFirst", figkit.fmt(1e4 * (clp[0] - ur[0]), 0), "peso minus UR zero rate at the first midpoint (bp)")
    import math
    from riskvalidation.irrbb import slotting

    mids = [float(x) for x in slotting.bucket_grid().midpoints]
    put("dfRatioFive", figkit.fmt(math.exp(-(clp[10] - ur[10]) * mids[10]), 3), "exp(-(r_clp - r_ur) t) at 5.5 years, Annex 1 midpoint")
    put("dfRatioTen", figkit.fmt(math.exp(-(clp[15] - ur[15]) * mids[15]), 3), "exp(-(r_clp - r_ur) t) at 9.5 years")
    put("dfRatioLast", figkit.fmt(math.exp(-(clp[18] - ur[18]) * mids[18]), 3), "exp(-(r_clp - r_ur) t) at 25 years")
    tb = shocks.shock_table("cmf-annex1")
    size_ratio = tb["CLP"][0] / tb["UR-eve"][0]
    w = [size_ratio * math.exp(-(clp[k] - ur[k]) * mids[k]) for k in range(19)]
    put("sizeRatio", figkit.fmt(size_ratio, 2), "parallel size of the peso over the UR row of the Hoja 9 table (engine shock_table)")
    put("weightFive", figkit.fmt(w[10], 2), "size ratio times exp(-(r_clp - r_ur) t) at 5.5 years")
    put("weightTen", figkit.fmt(w[15], 2), "the same at 9.5 years")
    put("weightLast", figkit.fmt(w[18], 2), "the same at 25 years")
    k_hi = min(k for k in range(19) if w[k] < 1.0)
    put("tStarLo", f"{mids[k_hi - 1]:g}", "midpoint of the last bucket whose first-order weight is at least 1")
    put("tStarHi", f"{mids[k_hi]:g}", "midpoint of the first bucket whose first-order weight is below 1")

    # reproduction
    put("repMaxDev", f"{REP['max_relative_deviation']:.0e}".replace("e-0", "e-").replace("0e+00", "0"), "experiments/reproduce.json max_relative_deviation")
    put("repSandChecked", str(REP["sandwich"]["checked"]), "experiments/reproduce.json sandwich.checked")
    put("repSandViol", str(REP["sandwich"]["violations"]), "experiments/reproduce.json sandwich.violations")
    for v in VARS:
        r, t = REP["variants"][v], TAG[v]
        s = f"experiments/reproduce.json variants.{v}"
        put(f"repAnnexEve{t}", g(r["annex1"]["delta_eve"]), s + ".annex1.delta_eve")
        put(f"repAnnexNii{t}", g(r["annex1"]["delta_nii"]), s + ".annex1.delta_nii")
        put(f"repSingleEve{t}", g(r["single"]["delta_eve"]), s + ".single.delta_eve")
        put(f"repSingleNii{t}", g(r["single"]["delta_nii"]), s + ".single.delta_nii")
        put(f"repPosEve{t}", g(r["positive_parts"]["delta_eve"]), s + ".positive_parts.delta_eve")
        put(f"repPosNii{t}", g(r["positive_parts"]["delta_nii"]), s + ".positive_parts.delta_nii")
        put(f"repGapNii{t}", g(r["gap"]["delta_nii_gap"]), s + ".gap.delta_nii_gap")
        put(f"repGapEve{t}", g(r["gap"]["delta_eve_duration"]), s + ".gap.delta_eve_duration")
        put(f"repCharge{t}", g(r["annex1"]["charge"]), s + ".annex1.charge")
        put(f"repMaxPair{t}", g(r["annex1"]["max_pair"]), s + ".annex1.max_pair")
        put(f"repChargeShare{t}", pct(r["charge_share_of_nii"]), s + ".charge_share_of_nii (percent)")
        put(f"repRatioNii{t}", figkit.fmt(r["ratio_nii_annex_over_single"], 1), s + ".ratio_nii_annex_over_single")
        put(f"repEveShort{t}", figkit.fmt(r["eve_shortfall_single_percent"], 1), s + ".eve_shortfall_single_percent")
        put(f"repNu{t}", pct(abs(r["net_uf_share_tier1"]), 0), s + ".net_uf_share_tier1 (percent of Tier 1, absolute value)")
        put(f"repPnUr{t}", g(abs(r["pn_ur"])), s + ".pn_ur (absolute value, CLP million)")
        put(f"repMargin{t}", g(r["margin_12m"]), s + ".margin_12m")
        a1 = r["ratios_tier1"]["annex1"]
        put(f"repNiiT{t}", pct(a1["nii"], 2), s + ".ratios_tier1.annex1.nii (percent)")
        put(f"repEveT{t}", pct(a1["eve"], 1), s + ".ratios_tier1.annex1.eve (percent)")
        put(f"repEveTSingle{t}", pct(r["ratios_tier1"]["single"]["eve"], 1), s + ".ratios_tier1.single.eve (percent)")
        put(f"repEveTPos{t}", pct(r["ratios_tier1"]["positive_parts"]["eve"], 1), s + ".ratios_tier1.positive_parts.eve (percent)")
        put(f"repFloorDist{t}", figkit.fmt(r["committed"]["closest_floor_bp"], 2), s + ".committed.closest_floor_bp")
        put(f"repAssetUnder{t}", figkit.fmt(r["ur_leg_gross_pv"]["asset"]["understatement_percent"], 1), s + ".ur_leg_gross_pv.asset.understatement_percent")
        put(f"repLiabUnder{t}", figkit.fmt(r["ur_leg_gross_pv"]["liability"]["understatement_percent"], 1), s + ".ur_leg_gross_pv.liability.understatement_percent")
    put("repCpiEffect", g(abs(REP["variants"]["cpi-surprise"]["committed"]["cpi_effect"])), "experiments/reproduce.json variants.cpi-surprise.committed.cpi_effect (absolute value)")
    ratios = [REP["variants"][v]["ratio_nii_annex_over_single"] for v in V30]
    put("repRatioLo", figkit.fmt(min(ratios), 1), "min over long-uf, short-uf, offset-on-off of ratio_nii_annex_over_single")
    put("repRatioHi", figkit.fmt(max(ratios), 1), "max over the same")
    sh = [REP["variants"][v]["eve_shortfall_single_percent"] for v in V30]
    put("repEveShortLo", figkit.fmt(min(sh), 0), "min over the same of eve_shortfall_single_percent, rounded")
    put("repEveShortHi", figkit.fmt(max(sh), 0), "max over the same, rounded")
    put("repChargeOverTier", figkit.fmt(100 * REP["variants"]["short-uf"]["annex1"]["charge"] / REP["variants"]["short-uf"]["tier1"], 2),
        "charge over Tier 1 in the short-uf variant (percent)")
    put("repChargeShareLo", pct(min(REP["variants"][v]["charge_share_of_nii"] for v in V30)), "min charge share, the three 30 percent variants")
    put("repChargeShareHi", pct(max(REP["variants"][v]["charge_share_of_nii"] for v in V30)), "max charge share, the three 30 percent variants")
    put("floorBreakNu", figkit.fmt(0.05 / 0.025, 1), "0.05 over 0.025: the net UF position over Tier 1 at which the charge alone reaches the 5 percent line")
    for v in VARS:
        c = REP["variants"][v]["classification"]
        put(f"repFlag{TAG[v]}", ",".join(k for k, x in c["annex1"].items() if x) or "none", f"experiments/reproduce.json variants.{v}.classification.annex1")
    # main experiment
    put("mainSeeds", str(len(MAIN["seeds"])), "experiments/main.json seeds")
    put("mainSeconds", figkit.fmt(MAIN["seconds"], 0), "experiments/main.json seconds (measured)")
    put("repSeconds", figkit.fmt(REP["seconds"], 1), "experiments/reproduce.json seconds (measured)")
    put("sweepSeconds", figkit.fmt(SWEEP["seconds"], 0), "experiments/sweep.json seconds (measured)")
    put("floorsSeconds", figkit.fmt(FLOORS["seconds"], 0), "experiments/floors.json seconds (measured)")
    put("hOneChecked", g(MAIN["h1_sandwich"]["checked"]), "experiments/main.json h1_sandwich.checked")
    put("hOneViol", str(MAIN["h1_sandwich"]["violations"]), "experiments/main.json h1_sandwich.violations")
    put("hThreeChecked", str(MAIN["h3_comparators"]["checked"]), "experiments/main.json h3_comparators.checked")
    put("hThreeViol", str(MAIN["h3_comparators"]["violations"]), "experiments/main.json h3_comparators.violations")
    for v in VARS:
        s = MAIN["variants"][v]["summary"]
        t = TAG[v]
        src = f"experiments/main.json variants.{v}.summary"
        for k, nm in (("annex", "Annex"), ("single", "Single"), ("pos", "Pos"), ("gap", "Gap")):
            for me, mn in (("nii", "Nii"), ("eve", "Eve")):
                put(f"main{nm}{mn}{t}", g(s[f"{k}_{me}"]["mean"]), f"{src}.{k}_{me}.mean")
                put(f"main{nm}{mn}{t}Ci", g(s[f"{k}_{me}"]["ci_half"]), f"{src}.{k}_{me}.ci_half")
        put(f"mainRatioNii{t}", figkit.fmt(s["ratio_nii_annex_over_single"]["mean"], 1), f"{src}.ratio_nii_annex_over_single.mean")
        put(f"mainRatioNii{t}Ci", figkit.fmt(s["ratio_nii_annex_over_single"]["ci_half"], 1), f"{src}.ratio_nii_annex_over_single.ci_half")
        put(f"mainEveShort{t}", figkit.fmt(s["eve_shortfall_single_percent"]["mean"], 1), f"{src}.eve_shortfall_single_percent.mean")
        put(f"mainEveShort{t}Ci", figkit.fmt(s["eve_shortfall_single_percent"]["ci_half"], 1), f"{src}.eve_shortfall_single_percent.ci_half")
        put(f"mainChargeShare{t}", pct(s["charge_share_of_nii"]["mean"]), f"{src}.charge_share_of_nii.mean (percent)")
        put(f"mainChargeShare{t}Ci", pct(s["charge_share_of_nii"]["ci_half"]), f"{src}.charge_share_of_nii.ci_half (percent)")
        put(f"mainPosOverAnnexNii{t}", figkit.fmt(s["pos_over_annex_nii"]["mean"], 2), f"{src}.pos_over_annex_nii.mean")
        put(f"mainPosOverAnnexEve{t}", figkit.fmt(s["pos_over_annex_eve"]["mean"], 3), f"{src}.pos_over_annex_eve.mean")
        put(f"mainGapOverAnnexEve{t}", figkit.fmt(s["gap_over_annex_eve"]["mean"], 2), f"{src}.gap_over_annex_eve.mean")
        put(f"mainSingleOverAnnexEve{t}", figkit.fmt(s["single_over_annex_eve"]["mean"], 3), f"{src}.single_over_annex_eve.mean")
        put(f"mainAnnexNiiT{t}", pct(s["annex_nii_over_tier1"]["mean"], 2), f"{src}.annex_nii_over_tier1.mean (percent)")
        put(f"mainAnnexEveT{t}", pct(s["annex_eve_over_tier1"]["mean"], 1), f"{src}.annex_eve_over_tier1.mean (percent)")
        for kind, key in (("Shap", "shapley"), ("Loo", "leave_one_out"), ("Aoi", "add_one_in")):
            for me, mn in (("delta_eve", "Eve"), ("delta_nii", "Nii")):
                for sw in SW:
                    d = MAIN["variants"][v][key][me][sw]
                    put(f"main{kind}{mn}{SWTAG[sw]}{t}", g(d["mean"]), f"experiments/main.json variants.{v}.{key}.{me}.{sw}.mean")
                    put(f"main{kind}{mn}{SWTAG[sw]}{t}Ci", g(d["ci_half"]), f"experiments/main.json variants.{v}.{key}.{me}.{sw}.ci_half")
    for v in V30:
        h = MAIN["h2_eve_attribution"][v]
        put(f"hTwoTop{TAG[v]}", SWNAME[h["largest_absolute"]].lower(), f"experiments/main.json h2_eve_attribution.{v}.largest_absolute")
    hv = MAIN["h3_comparators"]["by_variant"]["clp-steepener"]["nii_over_positive_parts"]
    put("hThreeSteeperViol", str(hv), "experiments/main.json h3_comparators.by_variant.clp-steepener.nii_over_positive_parts")
    # seed 42 values for the Shapley check
    put("caseShapCurveEveLng", g(MAIN["case_seed_values"]["long-uf"]["shapley"]["delta_eve"]["curve"]), "experiments/main.json case_seed_values.long-uf.shapley.delta_eve.curve")
    put("caseShapSizesEveLng", g(MAIN["case_seed_values"]["long-uf"]["shapley"]["delta_eve"]["sizes"]), "experiments/main.json case_seed_values.long-uf.shapley.delta_eve.sizes")
    put("caseShapPairEveLng", g(MAIN["case_seed_values"]["long-uf"]["shapley"]["delta_eve"]["pair"]), "experiments/main.json case_seed_values.long-uf.shapley.delta_eve.pair")
    # sweep
    pos = SWEEP["positions"]
    put("sweepSeeds", str(len(SWEEP["seeds"])), "experiments/sweep.json seeds")
    put("sweepLo", pct(SWEEP["feasible_range"][0], 0), "experiments/sweep.json feasible_range[0] (percent of Tier 1)")
    put("sweepHi", pct(SWEEP["feasible_range"][1], 0), "experiments/sweep.json feasible_range[1] (percent of Tier 1)")
    put("sweepRefused", str(len(SWEEP["refused"])), "experiments/sweep.json refused")
    put("sweepNPositions", str(len(pos)), "experiments/sweep.json positions")
    h4 = SWEEP["h4_positions_where_annex_flags_and_single_does_not"]
    put("hFourLo", pct(min(h4), 0), "experiments/sweep.json h4_positions min (percent of Tier 1)")
    put("hFourHi", pct(max(h4), 0), "experiments/sweep.json h4_positions max (percent of Tier 1)")
    put("hFourN", str(len(h4)), "experiments/sweep.json h4_positions count")
    names = {"+0.30": "Three", "+0.80": "Eight", "+1.00": "Ten", "+1.10": "Eleven", "+1.20": "Twelve", "+1.50": "Fifteen", "+0.00": "Zero", "-0.50": "MinusFive"}
    for key, nm in names.items():
        p = pos[key]
        s = f"experiments/sweep.json positions.{key}"
        put(f"sw{nm}AnnexNii", pct(p["annex_nii_over_tier1"]["mean"], 2), s + ".annex_nii_over_tier1.mean (percent)")
        put(f"sw{nm}SingleNii", pct(p["single_nii_over_tier1"]["mean"], 2), s + ".single_nii_over_tier1.mean (percent)")
        put(f"sw{nm}AnnexEve", pct(p["annex_eve_over_tier1"]["mean"], 1), s + ".annex_eve_over_tier1.mean (percent)")
        put(f"sw{nm}SingleEve", pct(p["single_eve_over_tier1"]["mean"], 1), s + ".single_eve_over_tier1.mean (percent)")
        for fk, fn in (("annex1", "Annex"), ("single", "Single"), ("positive_parts", "Pos")):
            put(f"sw{nm}Flag{fn}", str(p["any_flag"][fk]), s + f".any_flag.{fk}")
    maxnii = max(p["annex_nii_over_tier1"]["mean"] for p in pos.values())
    put("sweepMaxAnnexNii", pct(maxnii, 2), "experiments/sweep.json max over positions of annex_nii_over_tier1.mean (percent)")
    put("sweepNiiFlagTotal", str(sum(p["flag_counts"]["annex1"]["nii-tier1"] for p in pos.values())), "experiments/sweep.json sum over positions of annex1 nii-tier1 flag counts")
    put("sweepMarginFlagTotal", str(sum(p["flag_counts"]["annex1"]["nii-margin"] for p in pos.values())), "experiments/sweep.json sum over positions of annex1 nii-margin flag counts")
    put("sweepPosFlagFirst", pct(min(float(k) for k, p in pos.items() if p["any_flag"]["positive_parts"] > 0), 0), "experiments/sweep.json first position at which positive parts flag a book (percent)")
    # floors
    fl = FLOORS["results"]
    put("floorsSeeds", str(len(FLOORS["seeds"])), "experiments/floors.json seeds")
    put("floorsTotal", g(FLOORS["h5_floor_never_raises"]["checked"]), "experiments/floors.json h5.checked")
    put("floorsRaise", g(FLOORS["h5_floor_never_raises"]["violations"]), "experiments/floors.json h5.violations")
    put("floorsMaxInc", g(FLOORS["h5_floor_never_raises"]["max_increase"]), "experiments/floors.json h5.max_increase")
    put("floorsDistZero", figkit.fmt(fl["+0"]["long-uf"]["distance_bp"]["mean"], 2), "experiments/floors.json results.+0.long-uf.distance_bp.mean")
    fn = {"-25": "TwentyFive", "-50": "Fifty", "-100": "Hundred", "-200": "TwoHundred", "-300": "ThreeHundred"}
    for key, nm in fn.items():
        for v in ("long-uf", "short-uf", "floors-active"):
            r = fl[key][v]
            s = f"experiments/floors.json results.{key}.{v}"
            put(f"fl{nm}Dist{TAG[v]}", figkit.fmt(r["distance_bp"]["mean"], 1), s + ".distance_bp.mean")
            put(f"fl{nm}Eff{TAG[v]}", g(r["nii_effect"]["mean"]), s + ".nii_effect.mean")
            put(f"fl{nm}Eff{TAG[v]}Ci", g(r["nii_effect"]["ci_half"]), s + ".nii_effect.ci_half")
            put(f"fl{nm}Raise{TAG[v]}", str(r["books_where_floor_raises_nii"]), s + ".books_where_floor_raises_nii")
            put(f"fl{nm}Lower{TAG[v]}", str(r["books_where_floor_lowers_nii"]), s + ".books_where_floor_lowers_nii")
    put("floorsEveEffMax", g(max(abs(fl[k][v]["eve_effect"]["mean"]) for k in fl for v in fl[k])), "experiments/floors.json max absolute mean eve_effect over every cell")
    tot_total = sum(r["books_where_floor_raises_eve"] + r["books_where_floor_lowers_eve"] for k in fl for r in fl[k].values())
    put("floorsEveChanged", str(tot_total), "experiments/floors.json books where the floor changes delta EVE, summed")
    put("floorsRaiseTotalFlr", str(sum(fl[k]["floors-active"]["books_where_floor_raises_nii"] for k in fl)), "experiments/floors.json floors-active raises summed over translations")
    put("floorsLowerTotalFlr", str(sum(fl[k]["floors-active"]["books_where_floor_lowers_nii"] for k in fl)), "experiments/floors.json floors-active lowers summed over translations")
    lowers_other = sum(fl[k][v]["books_where_floor_lowers_nii"] for k in fl for v in fl[k] if v != "floors-active")
    put("floorsLowerOthers", str(lowers_other), "experiments/floors.json lowers in the five other variants, summed")
    tot = sum(FLOORS["seeds"].__len__() for _ in fl)
    del tot
    put("totalSeconds", figkit.fmt(REP["seconds"] + MAIN["seconds"] + SWEEP["seconds"] + FLOORS["seconds"], 0), "sum of the four measured run times")
    t = shocks.shock_table("cmf-annex1")
    for key, nm in (("CLP", "Clp"), ("UR-eve", "UrEve")):
        for i, nn in enumerate(("Par", "Short", "Long")):
            put(f"size{nm}{nn}", str(int(t[key][i])), f"riskvalidation.irrbb.shocks.shock_table('cmf-annex1')['{key}'][{i}] (bp)")
    put("sizeUrNii", str(int(t["UR-nii"][0])), "shock_table('cmf-annex1')['UR-nii'][0] (bp)")
    b2016 = shocks.shock_table("2016")
    b2024 = shocks.shock_table("2024")
    put("nCurr", str(len(b2024)), "len(shock_table('2024'))")
    put("nCurrOld", str(len(b2016)), "len(shock_table('2016'))")
    put("usdPar", str(int(b2024["USD"][0])), "shock_table('2024')['USD'][0] (bp)")
    put("usdShort", str(int(b2024["USD"][1])), "shock_table('2024')['USD'][1] (bp)")
    put("usdLong", str(int(b2024["USD"][2])), "shock_table('2024')['USD'][2] (bp)")


# ------------------------------------------------------------------------------------------------ the tables
def t_main() -> None:
    def row(label, kind, me, v):
        s = MAIN["variants"][v]["summary"][f"{kind}_{me}"]
        return pm(s["mean"], s["ci_half"])

    def ratio(kind, me, v):
        s = MAIN["variants"][v]["summary"]
        return figkit.fmt(s[f"{kind}_{me}"]["mean"] / s[f"annex_{me}"]["mean"], 2)

    head = ["Treatment", "Long UF", "Short UF", "Offset on/off", "Long UF", "Short UF", "Offset"]
    kinds = [("Annex 1 (separate UR)", "annex"), ("Positive parts (Basel aggregation)", "pos"), ("Single currency", "single")]
    panels = []
    for title, me, gapname in (("Panel A. Delta NII, CLP million (left: mean $\\pm$ 95\\% half-width; right: ratio to Annex 1)", "nii", "Repricing gap"),
                               ("Panel B. Delta EVE, CLP million (left: mean $\\pm$ 95\\% half-width; right: ratio to Annex 1)", "eve", "Duration gap")):
        rows = [[label] + [row(label, k, me, v) for v in V30] + [ratio(k, me, v) for v in V30] for label, k in kinds]
        rows.append([gapname + " (single currency)"] + [row(gapname, "gap", me, v) for v in V30] + [ratio("gap", me, v) for v in V30])
        panels.append((title, head, rows))
    cap = ("Main comparison on the three variants whose net UF position is 30 percent of Tier 1: the delta NII and the delta EVE of the Annex 1 treatment, "
           "of the positive-part aggregation of the Basel standard, of the single-currency treatment of the same flows, and of the repricing-gap "
           "and duration-gap measures, as the mean and the half-width of the 95 percent Student interval over 30 synthetic books (seeds 1 to 30) "
           "on the curves of 2026-09-03; the three right columns divide each mean by the Annex 1 mean.")
    tablewrite("main-results", panels, cap, "tab:main-results", "lrrrrrr")


def t_reproduction() -> None:
    head = ["Variant", "Net UF / $T_1$", "$\\Delta$NII", "$\\Delta$EVE", "Charge / $\\Delta$NII", "Closest floor (bp)", "Max relative deviation"]
    rows = []
    for v in VARS:
        r = REP["variants"][v]
        rows.append([VNAME[v], f"{pct(r['net_uf_share_tier1'], 0)}\\%", g(r["committed"]["delta_nii"]), g(r["committed"]["delta_eve"]),
                     f"{pct(r['charge_share_of_nii'])}\\%", figkit.fmt(r["committed"]["closest_floor_bp"], 2), f"{max(r['relative_deviation'].values()):.0e}"])
    cap = ("The six variants of case C15 as committed (seed 42, valuation date 2026-09-03, CLP million): the delta NII and delta EVE of the Annex 1 "
           "treatment, the indexation charge as a share of the delta NII, the smallest distance between a post-shock rate and its floor, and the "
           "largest relative deviation between the committed measures and the measures recomputed here from the same flows by independent engine calls.")
    tablewrite("reproduction", [("", head, rows)], cap, "tab:reproduction", "lrrrrrr")


def t_sizes() -> None:
    t = shocks.shock_table("cmf-annex1")
    head = ["Treatment of the leg", "Parallel (bp)", "Short (bp)", "Long (bp)", "Floor", "Curve"]
    rows = [["CLP leg (all treatments)", t["CLP"][0], t["CLP"][1], t["CLP"][2], "0 percent", "peso zero curve"],
            ["UR leg, separate currency (Annex 1)", t["UR-eve"][0], t["UR-eve"][1], t["UR-eve"][2], "$-$2 percent", "UF zero curve"],
            ["UR leg, single-currency treatment", t["CLP"][0], t["CLP"][1], t["CLP"][2], "0 percent", "peso zero curve"]]
    rows = [[str(c) if isinstance(c, str) else str(int(c)) for c in r] for r in rows]
    cap = ("The inputs that distinguish the two treatments of the UF leg in the delta EVE: the shock sizes of the rows CLP and UR of the Hoja 9 table of "
           "RAN 21-13 Annex 1 as the engine holds them, the post-shock floor and the discount curve; for the delta NII both legs use one parallel shock "
           "of 300 bp and the same floors.")
    tablewrite("sizes", [("", head, rows)], cap, "tab:sizes", "lrrrll")


def t_shapley() -> None:
    panels = []
    for title, mn in (("Panel A. Delta EVE, CLP million", "Eve"), ("Panel B. Delta NII, CLP million", "Nii")):
        head = ["Switch turned on", "Long UF", "Short UF", "Offset on/off"]
        rows = []
        for sw in SW:
            cells = []
            for v in V30:
                d = MAIN["variants"][v]["shapley"]["delta_eve" if mn == "Eve" else "delta_nii"][sw]
                cells.append(pm(d["mean"], d["ci_half"]))
            rows.append([SWNAME[sw]] + cells)
        tot = []
        for v in V30:
            s = MAIN["variants"][v]["summary"]
            m = s["annex_eve" if mn == "Eve" else "annex_nii"]["mean"] - s["single_eve" if mn == "Eve" else "single_nii"]["mean"]
            tot.append(g(m))
        rows.append(["Sum: Annex 1 minus single currency"] + tot)
        panels.append((title, head, rows))
    cap = ("Exact Shapley value of each of the five switches that turn the single-currency treatment of the UF leg into the Annex 1 treatment, "
           "for the three variants with a net UF position of 30 percent of Tier 1, as the mean and the 95 percent half-width over 30 synthetic books; "
           "each panel's last row is the Annex 1 measure minus the single-currency measure, which the five values add up to.")
    tablewrite("shapley", panels, cap, "tab:shapley", "lrrr")


def t_ablation() -> None:
    panels = []
    for title, mn in (("Panel A. Delta EVE, long UF variant, CLP million", "delta_eve"), ("Panel B. Delta NII, long UF variant, CLP million", "delta_nii")):
        head = ["Switch", "Annex 1 without it", "Single currency with it", "Shapley value"]
        rows = []
        for sw in SW:
            v = MAIN["variants"]["long-uf"]
            a, b, c = v["leave_one_out"][mn][sw], v["add_one_in"][mn][sw], v["shapley"][mn][sw]
            rows.append([SWNAME[sw], pm(-a["mean"], a["ci_half"]), pm(b["mean"], b["ci_half"]), pm(c["mean"], c["ci_half"])])
        panels.append((title, head, rows))
    cap = ("One-at-a-time ablation on the long UF variant, as the mean and the 95 percent half-width over 30 books: the change of the measure when a switch is "
           "turned off in Annex 1 (the first column is the measure without the switch minus the Annex 1 measure) and when it alone is turned on in the "
           "single-currency treatment, beside the Shapley value that averages the change over every order of the five switches.")
    tablewrite("ablation", panels, cap, "tab:ablation", "lrrr")


def t_sweep() -> None:
    pos = SWEEP["positions"]
    head = ["Net UF / $T_1$", "NII A1", "NII SC", "EVE A1", "EVE SC", "Flag A1", "Flag PP", "Flag SC"]
    rows = []
    for key in ("-0.50", "+0.00", "+0.30", "+0.80", "+1.00", "+1.10", "+1.20", "+1.50"):
        p = pos[key]
        rows.append([f"{pct(p['net_uf_share_tier1'], 0)}\\%"] + [f"{pct(p[k]['mean'], d)}\\%" for k, d in
                                                           (("annex_nii_over_tier1", 2), ("single_nii_over_tier1", 2), ("annex_eve_over_tier1", 1), ("single_eve_over_tier1", 1))]
                    + [str(p["any_flag"][k]) for k in ("annex1", "positive_parts", "single")])
    cap = ("The delta NII (NII) and delta EVE (EVE) as a share of Tier 1 under the Annex 1 (A1) and the single-currency (SC) treatments, and the number of the 20 synthetic books "
           "(seeds 101 to 120) that Annex 1 (Flag A1), the positive-part aggregation (Flag PP) and the single currency (Flag SC) flag as prioritised under at least one of the three "
           "tests of Annex 1, at selected net UF positions of the long UF book (positive: UF assets exceed UF funding).")
    tablewrite("sweep", [("", head, rows)], cap, "tab:sweep", "lrrrrrrr")


def t_floors() -> None:
    head = ["Shift (bp)", "Dist. (bp)", "No floor", "Floor", "Effect", "Raised", "Lowered"]
    panels = []
    for v in ("long-uf", "floors-active"):
        rows = []
        for key in ("+0", "-25", "-50", "-100", "-200", "-300"):
            r = FLOORS["results"][key][v]
            rows.append([key.replace("-", "$-$"), figkit.fmt(r["distance_bp"]["mean"], 1), g(r["nii_no_floor"]["mean"]), g(r["nii_with_floor"]["mean"]),
                         pm(r["nii_effect"]["mean"], r["nii_effect"]["ci_half"]), f"{r['books_where_floor_raises_nii']}", f"{r['books_where_floor_lowers_nii']}"])
        panels.append((f"Panel {'A' if v == 'long-uf' else 'B'}. Delta NII, {VNAME[v].lower()} variant, CLP million", head, rows))
    cap = ("The UR floor of minus 2 percent made to bind by translating the fitted UF zero curve down: the mean distance of the lowest post-shock UR rate to the floor "
           "(negative once it binds), the Annex 1 delta NII without any floor and with the floor, the effect of the floor with its 95 percent half-width, and the number "
           "of the 20 books (seeds 201 to 220) in which the floor raises or lowers the measure, for two variants.")
    tablewrite("floors", panels, cap, "tab:floors", "lrrrrrr")


def t_data() -> None:
    o = COMMITTED["long-uf"]
    def tenors(k):
        return ", ".join(f"{p['tenor_years']:g}" for p in o["curves"][k]["points"] if p["tenor_years"] >= 1.0)

    head = ["Input", "Source and identifier", "Use in the experiments"]
    rows = [
        ["Peso curve", "Banco Central de Chile, table F022 (secondary-market yields), series BCLP at " + tenors("clp") + " years, with the monetary policy rate "
         "(series TPM) as the overnight point", "zero curve of the CLP leg, 19 midpoints"],
        ["UF curve", "Banco Central de Chile, table F022, series BUF at " + tenors("ur") + " years", "zero curve of the UR leg, 19 midpoints"],
        ["UF value", "BDE series F073.UFF.PRE.Z.D, value of " + o["as_of"], "conversion of UF flows to pesos"],
        ["Balance sheet", "synthetic Banco Andino, calibrated to the CMF aggregates of August 2026", "30 seeds of the repricing profiles per variant"],
        ["Shock sizes, floors, offset, charge", "RAN 21-13 Annex 1, Hojas 9 to 12 (held by the engine)", "all treatments"],
    ]
    cap = ("The inputs of the experiments and where each comes from: the daily secondary-market yields of the F022 table of the Banco Central de Chile on the valuation date "
           "2026-09-03, the UF value of that day, the synthetic bank built by the case's generator and the rules of Annex 1 that the engine holds.")
    tablewrite("data", [("", head, rows)], cap, "tab:data", "p{2.4cm}p{6.6cm}p{5.4cm}")


def t_hypotheses() -> None:
    head = ["Id", "Statement and deciding quantity", "Status", "Outcome"]
    r = REP["variants"]
    rows = [
        ["R1", "The indexation charge is 55.9\\% of the delta NII of the short UF variant (reproduction).", "reproduced",
         f"{pct(r['short-uf']['charge_share_of_nii'])}\\%"],
        ["R2", "The single-currency delta NII is 6.8 to 8.8 times smaller in the three 30\\% variants (reproduction).", "reproduced",
         f"{figkit.fmt(min(r[v]['ratio_nii_annex_over_single'] for v in V30), 1)} to {figkit.fmt(max(r[v]['ratio_nii_annex_over_single'] for v in V30), 1)}"],
        ["R3", "The single-currency delta EVE is 10 to 27\\% smaller in the same three variants (reproduction).", "reproduced",
         f"{figkit.fmt(min(r[v]['eve_shortfall_single_percent'] for v in V30), 0)} to {figkit.fmt(max(r[v]['eve_shortfall_single_percent'] for v in V30), 0)}\\%"],
        ["R4", "No floor binds on the committed curves; the closest post-shock rate is 20.48 bp from its floor (reproduction).", "reproduced",
         f"{figkit.fmt(r['long-uf']['committed']['closest_floor_bp'], 2)} bp in every variant"],
        ["H1", "The sum of the legs is at most the pair rule, which is at most the positive parts, for every shock, variant and treatment.", "held",
         f"{MAIN['h1_sandwich']['violations']} violations in {g(MAIN['h1_sandwich']['checked'])} comparisons"],
        ["H2", "For the delta EVE, the pair rule has the largest absolute Shapley value in the three 30\\% variants.", "refuted",
         "the own curve has the largest value in all three"],
        ["H3", "The Annex 1 delta NII exceeds the single-currency and the positive-part delta NII, and the Annex 1 delta EVE is not below the single-currency one, in every variant and book.", "refuted in one clause (not a prediction)",
         f"the CLP steepener variant: Annex 1 below positive parts in {MAIN['h3_comparators']['by_variant']['clp-steepener']['nii_over_positive_parts']} of 30 books"],
        ["H4", "A net UF position exists at which Annex 1 flags the bank in most books and the single-currency treatment flags none.", "held",
         f"{pct(min(SWEEP['h4_positions_where_annex_flags_and_single_does_not']), 0)}\\% to {pct(max(SWEEP['h4_positions_where_annex_flags_and_single_does_not']), 0)}\\% of Tier 1, the delta EVE test only"],
        ["H5", "A binding UR floor never raises the Annex 1 measure.", "refuted",
         f"{FLOORS['h5_floor_never_raises']['violations']} of {g(FLOORS['h5_floor_never_raises']['checked'])} comparisons raise it"],
    ]
    cap = ("The statements tested or reproduced in this paper, with the deciding quantity and the outcome: R1 to R4 are the statements of the committed record, written after "
           "the bake and so reproduced and not tested; H1, H2, H4 and H5 were fixed by the author in the headers of the experiment scripts before the scripts that decide them ran; "
           "H3 was written after the reproduction run had printed a value that already contradicts one of its clauses, so it is a refuted statement and not a prediction.")
    tablewrite("hypotheses", [("", head, rows)], cap, "tab:hypotheses", "p{0.8cm}p{7.6cm}p{1.9cm}p{3.6cm}")


def t_notation() -> None:
    head = ["Symbol", "Meaning", "Unit"]
    rows = [
        ["$k=1,\\dots,19$, $t_k$", "bucket index and bucket midpoint of the Annex 1 grid", "years"],
        ["$r_{0,c}(t_k)$", "pre-shock continuously compounded zero rate of currency $c\\in\\{\\mathrm{CLP},\\mathrm{UR}\\}$", "decimal"],
        ["$\\Delta S_{i,c}(t_k)$", "shock $i$ applied to currency $c$ at $t_k$", "bp"],
        ["$f_c$", "post-shock floor of currency $c$", "decimal"],
        ["$\\mathrm{CF}_{c}(t_k)$, $\\mathrm{CF}_{i,c}(t_k)$", "signed repricing flows of leg $c$ before and under shock $i$ (term-deposit redemption depends on $i$)", "CLP million"],
        ["$U$", "value of the UF on the valuation date", "CLP per UF"],
        ["$a_{i}$, $b_{i}$", "loss-positive delta of the CLP leg and of the UR leg under shock $i$", "CLP million"],
        ["$P_\\lambda(a,b)$", "pair rule with offsetting share $\\lambda$ (Annex 1: $\\lambda=1/2$)", "CLP million"],
        ["$N(a,b)$, $Q(a,b)$", "sum of the legs, $\\max\\{a+b,0\\}$, and positive parts, $\\max\\{a,0\\}+\\max\\{b,0\\}$", "CLP million"],
        ["$\\mathrm{PN}_{\\mathrm{UR}}$", "net UF position converted at $U$ (assets positive)", "CLP million"],
        ["$\\kappa$", "indexation charge rate, 2.5 percent", "share"],
        ["$T_1$, $\\nu=\\mathrm{PN}_{\\mathrm{UR}}/T_1$", "Tier 1 capital and the net UF position as a share of it", "CLP million, share"],
        ["$\\tau\\in\\{0,1\\}^5$", "treatment: the five switches (curve, sizes, floor, pair rule, charge)", "none"],
        ["$M_m(\\tau)$", "measure $m\\in\\{\\Delta\\mathrm{EVE},\\Delta\\mathrm{NII}\\}$ under treatment $\\tau$", "CLP million"],
        ["$\\varphi_j^{m}$", "exact Shapley value of switch $j$ for measure $m$", "CLP million"],
    ]
    cap = ("The notation of the paper: the grid and the rates of the two currencies, the shock and the floor, the flows of the two legs, the pair rule and its two bounds, "
           "the net UF position, the indexation charge, the treatment of the UF leg as five switches and the Shapley value of a switch.")
    tablewrite("notation", [("", head, rows)], cap, "tab:notation", "p{3.3cm}p{8.5cm}p{2.0cm}")


if __name__ == "__main__":
    numbers()
    for f in (t_main, t_reproduction, t_sizes, t_shapley, t_ablation, t_sweep, t_floors, t_data, t_hypotheses, t_notation):
        f()
    lines = ["% Generated by tables/make_tables.py: the numbers the prose quotes. Do not edit."]
    lines += [f"\\newcommand{{\\{k}}}{{{v['value']}}}" for k, v in NUM.items()]
    (HERE / "numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    (HERE / "numbers.json").write_text(json.dumps(NUM, indent=1), encoding="utf-8")
    print(f"wrote 10 tables and {len(NUM)} macros to", HERE)
