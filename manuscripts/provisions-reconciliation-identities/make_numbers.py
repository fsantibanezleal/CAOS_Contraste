"""Write ``tables/numbers.tex``: every number the prose of the manuscript quotes, as a LaTeX macro, from the experiment outputs.

    python manuscripts/provisions-reconciliation-identities/make_numbers.py

The text never types a result: it writes ``\\eoneCases`` and this file defines it from ``experiments/*.json`` and from the
committed C06 and C07 documents. A macro name holds letters only (TeX), so digits are spelled in the name where needed.
"""
from __future__ import annotations

import glob
import json
import math
import pathlib
import statistics as st
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "experiments"))
import common  # noqa: E402

E1 = common.load("e1_gate_power.json")
E2 = common.load("e2_tolerance_and_rounding.json")
E3 = common.load("e3_overlays.json")
E4 = common.load("e4_nonlinearity.json")
E6 = common.load("e6_identity_algebra.json")
RUNS = [json.loads(pathlib.Path(f).read_text(encoding="utf-8")) for f in sorted(glob.glob(str(HERE / "experiments" / "e5_regimes" / "s*-x1.json")))]
LADDER = {r["scale"]: r for r in (json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
                                  for f in sorted(glob.glob(str(HERE / "experiments" / "e5_regimes" / "s42-x*.json"))))}
M: dict[str, str] = {}


DIGITS = {"0": "Zero", "1": "One", "2": "Two", "3": "Three", "4": "Four", "5": "Five", "6": "Six", "7": "Seven", "8": "Eight", "9": "Nine"}


def put(name: str, value) -> None:
    M["".join(DIGITS.get(ch, ch) for ch in name)] = str(value)


def num(x: int) -> str:
    return f"{x:,}"


def pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}\\%"


def sci(x: float, d: int = 1) -> str:
    if x == 0:
        return "$0$"
    e = int(math.floor(math.log10(abs(x))))
    return f"${x / 10 ** e:.{d}f}\\times10^{{{e}}}$"


def frac(k: int, n: int) -> str:
    return f"{num(k)} of {num(n)}"


# the t quantile 0.975 with nine degrees of freedom (ten seeds)
T975_9 = 2.2621571627
DETECTABLE = ("allowance-movement", "allowance-closing", "stage-reallocation", "gca-movement", "waterfall-line", "waterfall-closing", "stage-ecl")

# ---- E1
g = E1["grid"]
put("eoneReps", E1["meta"]["reps"])
put("eoneCases", num(E1["meta"]["reps"] * len(E1["meta"]["dates"])))
put("eoneClasses", len(g))
put("eoneBisected", num(E1["threshold"]["allowance-movement"]["n_bisected"]))
dev = max(max(abs(v["min_ratio"] - 1), abs(v["max_ratio"] - 1)) for v in E1["threshold"].values() if v["min_ratio"] is not None)
put("eoneThrDev", sci(dev))
put("eoneSeconds", f"{E1['meta']['seconds']:.0f}")


def agg(gate: str, mult: str, classes) -> tuple[int, int]:
    return sum(g[c][mult][gate][0] for c in classes), sum(g[c][mult][gate][1] for c in classes)


for gate, key in (("full", "Full"), ("stage", "Stage"), ("total", "Total")):
    k, n = agg(gate, "1.01", DETECTABLE)
    put(f"eoneAbove{key}K", num(k))
    put(f"eoneAbove{key}N", num(n))
    k, n = agg(gate, "0.99", tuple(g))
    put(f"eoneBelow{key}K", num(k))
    put(f"eoneBelow{key}N", num(n))
k, n = agg("full", "100", ("line-misclassification",))
put("eoneMisK", num(k))
put("eoneMisN", num(n))
put("eoneCleanRel", sci(max(v["max_residual"] / v["gross"] for v in E1["clean"].values())))
put("eoneCleanLimitLow", num(round(min(v["limit"] for v in E1["clean"].values()))))
put("eoneCleanLimitHigh", num(round(max(v["limit"] for v in E1["clean"].values()))))
put("eoneGrossLow", f"{min(v['gross'] for v in E1['clean'].values()) / 1e9:.1f}")
put("eoneGrossHigh", f"{max(v['gross'] for v in E1['clean'].values()) / 1e9:.1f}")
# the families whose removal loses a class entirely, at ten times the limit
lost: dict[str, list[str]] = {}
for fam in E1["meta"]["families"]:
    lost[fam] = [c for c in DETECTABLE if g[c]["10"][f"drop:{fam}"][0] == 0]
put("eoneFamiliesLost", sum(1 for v in lost.values() if v))
ids = E1["identities_flagged_at_10x"]
put("eoneIdsMax", max(v[1] for k, v in ids.items() if k != "line-misclassification"))
for k, v in ids.items():
    put("eoneIds" + "".join(w.capitalize() for w in k.split("-")), v[1])

# ---- E2
cm = E2["committed"]
put("etwoAbsCommittedK", sum(1 for v in cm.values() if v["abs:1e-06"]))
put("etwoRelCommittedK", sum(1 for v in cm.values() if v["rel:1e-06"]))
rs = E2["resampled"]
n = rs["rel:1e-06"][1]
put("etwoResN", num(n))
put("etwoAbsResK", num(rs["abs:1e-06"][0]))
lo, hi = common.wilson(*rs["abs:1e-06"])
put("etwoAbsResPct", pct(rs["abs:1e-06"][0] / n))
put("etwoAbsResLo", pct(lo))
put("etwoAbsResHi", pct(hi))
put("etwoRelResK", num(rs["rel:1e-06"][0]))
put("etwoAbsCentK", num(rs["abs:0.01"][0]))
put("etwoRelMaxResid", sci(E2["resampled_relative_residual"]["max"]))
names = {"1": "Unit", "10": "Ten", "1000": "Thousand", "10000": "TenThousand", "100000": "HundredThousand", "1e+06": "Million"}
for key, name in names.items():
    r = E2["rounding"][key]
    k, nn = r["flagged"]
    lo, hi = common.wilson(k, nn)
    put(f"etwoRound{name}K", num(k))
    put(f"etwoRound{name}Pct", pct(k / nn))
    put(f"etwoRound{name}Lo", pct(lo))
    put(f"etwoRound{name}Hi", pct(hi))
    put(f"etwoRound{name}Median", f"{r['ratio_q50']:.2f}")
    put(f"etwoRound{name}Max", f"{r['ratio_max']:.1f}")
put("etwoReps", E2["meta"]["reps"])
mill = E2["rounding"]["1e+06"]["by_date"]
put("etwoMillionUnflagged", num(E2["rounding"]["1e+06"]["flagged"][1] - E2["rounding"]["1e+06"]["flagged"][0]))
put("etwoMillionUnflaggedDates", ", ".join(f"{d} ({E2['meta']['reps'] - v})" for d, v in mill.items() if v < E2["meta"]["reps"]))
hund = E2["rounding"]["100000"]["by_date"]
put("etwoHundredLow", pct(min(hund.values()) / E2["meta"]["reps"], 0))
put("etwoHundredHigh", pct(max(hund.values()) / E2["meta"]["reps"], 0))

# ---- E3
inv = E3["invariance"]
put("ethreeDraws", num(inv["draws"]))
put("ethreeSets", num(inv["sets_checked"]))
put("ethreeViolations", inv["model_changed"] + inv["total_not_model_plus_overlays"] + inv["carried_not_overlay_total"])
c07 = E3["c07_base"]
put("ethreeSevenShare", pct(c07["overlay_share_of_allowance"], 2))
put("ethreeSevenMerge", pct(c07["merge_overstates_model_ecl_by"], 2))
put("ethreeSevenOverlay", f"{c07['overlay_total'] / 1e6:,.1f}")
put("ethreeSevenAllowance", f"{c07['allowance'] / 1e6:,.1f}")
put("ethreeSevenCount", c07["n_overlays"])
put("ethreeCases", E3["placement"]["cases_per_booking"])
for k, v in E3["placement"]["bookings"].items():
    put("ethreeIds" + "".join(w.capitalize() for w in k.split("-")), v["identities_flagged_max"])
put("ethreeMergeAtQuarter", pct(0.25 / 0.75, 0))

# ---- E4
sw = E4["sweep"]
cl = sw["classes"]
put("efourDraws", num(sw["draws"]))
for k, name in (("convex", "Convex"), ("concave", "Concave"), ("mixed", "Mixed")):
    put(f"efour{name}N", num(cl[k]["n"]))
    put(f"efour{name}Neg", num(cl[k]["negative"]))
    put(f"efour{name}Pos", num(cl[k]["positive"]))
    put(f"efour{name}Red", num(cl[k]["red"]))
put("efourConvexMin", sci(cl["convex"]["min"]))
put("efourConcaveMax", sci(cl["concave"]["max"]))
put("efourConcaveMin", f"{cl['concave']['min']:.3f}")
put("efourMixedMin", f"{cl['mixed']['min']:.3f}")
put("efourMixedMax", f"{cl['mixed']['max']:.2f}")
put("efourGhErr", sci(sw["gauss_hermite_error_max"]))
so = sw["second_order"]
put("efourSecondN", num(so["n"]))
put("efourSecondWithin", pct(so["within_25pct"]))
put("efourSecondQFive", f"{so['ratio_q05']:.2f}")
put("efourSecondQFifty", f"{so['ratio_q50']:.3f}")
put("efourSecondQNinetyFive", f"{so['ratio_q95']:.2f}")
ds = E4["designs"]
put("efourDesignDraws", num(ds["draws"]))
put("efourStrong", num(ds["strong_margin_draws"]))
for key, name in (("single", "Single"), ("adhoc3", "Adhoc"), ("tertile3", "Tertile"), ("gh3", "GhThree"), ("gh5", "GhFive")):
    d = ds["designs"][key]
    def p_(x: float) -> str:
        return sci(100 * x, 1) + "\\%" if x < 1e-3 else pct(x, 2)

    put(f"efour{name}Med", p_(d["median_abs"]))
    put(f"efour{name}MedLo", p_(d["median_abs_ci"][0]))
    put(f"efour{name}MedHi", p_(d["median_abs_ci"][1]))
    put(f"efour{name}Five", pct(d["share_abs_above_5pct"], 1))
    put(f"efour{name}Under", pct(d["share_negative_strong_margin"], 1))
    put(f"efour{name}QFive", pct(d["quantiles"]["q05"], 2))
    put(f"efour{name}QNinetyFive", pct(d["quantiles"]["q95"], 2))
br = ds["adhoc3_bias_ratio_predicted_over_measured"]
put("efourBiasMedian", f"{br['q50']:.3f}")
put("efourBiasWithin", pct(br["within_20pct"]))
cmt = E4["committed"]
pdi = [v["pd_index_committed"] for v in cmt.values()]
put("efourPdLow", f"{min(pdi):.5f}")
put("efourPdHigh", f"{max(pdi):.5f}")
put("efourZstarLow", f"{min(v['zstar'] for v in cmt.values()):.2f}")
put("efourZstarHigh", f"{max(v['zstar'] for v in cmt.values()):.2f}")
put("efourZminHigh", f"{max(v['z_min'] for v in cmt.values()):.2f}")
put("efourZminLow", f"{min(v['z_min'] for v in cmt.values()):.2f}")
put("efourPdAgree", sci(max(v["pd_index_agreement"] for v in cmt.values()), 0))
put("efourEclTen", f"{cmt['2010-12']['ecl_index']:.5f}")
put("efourGapTen", f"{cmt['2010-12']['stage2_gap']:.4f}")
put("efourGapOther", f"{max(v['stage2_gap'] for k, v in cmt.items() if k != '2010-12'):.5f}")
put("efourTenShare", pct(cmt["2010-12"]["stage2_ratio_committed"], 1))
put("efourEclPositive", sum(1 for v in cmt.values() if v["ecl_index"] > 0))
put("efourSeconds", f"{E4['meta']['seconds']:.0f}")
put("etwoSeconds", f"{E2['meta']['seconds']:.1f}")
put("ethreeSeconds", f"{E3['meta']['seconds']:.1f}")

# ---- E5
SC = {"base": "Base", "recession": "Recession", "house-price-fall": "House", "consumer-arrears-shock": "Consumer",
      "uf-inflation-spike": "Uf", "combined-severe": "Combined"}
put("efiveSeeds", len(RUNS))
put("efiveAccounts", num(RUNS[0]["n_accounts"]))
secs = [r["seconds"] for r in RUNS]
put("efiveSecLow", f"{min(secs):.0f}")
put("efiveSecHigh", f"{max(secs):.0f}")
bridge = max(r["scenarios"][s]["bridge_residual"] for r in RUNS for s in r["scenarios"])
put("efiveBridgeMax", sci(bridge))
put("efiveSegMax", sci(max(r["scenarios"][s]["segment_sum_residual"] for r in RUNS for s in r["scenarios"])))
put("efiveBookedMax", sci(max(r["scenarios"][s]["booked_b1_residual"] for r in RUNS for s in r["scenarios"])))
put("efiveGreen", num(sum(1 for r in RUNS for s in r["scenarios"].values() if s["identities"]["light"] == "green")))
put("efiveCells", num(sum(len(r["scenarios"]) for r in RUNS)))
for sid, name in SC.items():
    v = [r["scenarios"][sid]["ifrs9_over_b1"] for r in RUNS]
    m, sd = st.mean(v), st.stdev(v)
    h = T975_9 * sd / math.sqrt(len(v))
    put(f"efive{name}Mean", f"{m:.3f}")
    put(f"efive{name}Sd", f"{sd:.3f}")
    put(f"efive{name}Lo", f"{m - h:.3f}")
    put(f"efive{name}Hi", f"{m + h:.3f}")
    put(f"efive{name}Min", f"{min(v):.3f}")
    put(f"efive{name}Max", f"{max(v):.3f}")
    b = [r["scenarios"][sid]["bde_over_b1"] for r in RUNS]
    put(f"efive{name}BdeMean", f"{st.mean(b):.3f}")
    put(f"efive{name}BdeSd", f"{st.stdev(b):.3f}")
base_ifrs_over_bde = [r["scenarios"]["base"]["totals"]["ifrs9"] / r["scenarios"]["base"]["totals"]["bde-annex9"] for r in RUNS]
put("efiveIfrsAboveBde", sum(1 for x in base_ifrs_over_bde if x > 1))
put("efiveIfrsOverBdeLow", f"{min(base_ifrs_over_bde):.3f}")
put("efiveIfrsOverBdeHigh", f"{max(base_ifrs_over_bde):.3f}")
below = all(r["scenarios"][s]["ifrs9_over_b1"] < 1 for r in RUNS for s in r["scenarios"] if s != "combined-severe")
above = all(r["scenarios"]["combined-severe"]["ifrs9_over_b1"] > 1 for r in RUNS)
put("efiveOrder", "in every seed" if (below and above) else "not in every seed")
r42 = next(r for r in RUNS if r["seed"] == 42)
diff = 0.0
for sid, v in r42["scenarios"].items():
    d = common.doc(f"C07/{sid}.json")["outputs"]
    for reg in d["regimes"]:
        diff = max(diff, abs(reg["total_provision"] - v["totals"][reg["regime"]]))
put("efiveCommittedDiff", f"{diff:.2f}")
for sid, name in SC.items():
    d = common.doc(f"C07/{sid}.json")["outputs"]
    tot = {r["regime"]: r["total_provision"] for r in d["regimes"]}
    put(f"efiveCommitted{name}B", f"{tot['cmf-b1'] / 1e9:.1f}")
    put(f"efiveCommitted{name}I", f"{tot['ifrs9'] / 1e9:.1f}")
    put(f"efiveCommitted{name}A", f"{tot['bde-annex9'] / 1e9:.1f}")
    put(f"efiveCommitted{name}Ratio", f"{tot['ifrs9'] / tot['cmf-b1']:.3f}")
lad = LADDER
put("efiveLadderLowScale", f"{min(lad):g}")
put("efiveLadderLowBase", f"{lad[min(lad)]['scenarios']['base']['ifrs9_over_b1']:.3f}")
put("efiveLadderLowAccounts", num(lad[min(lad)]["n_accounts"]))
put("efiveLadderHighBase", f"{lad[1.0]['scenarios']['base']['ifrs9_over_b1']:.3f}")
put("efiveLadderLowSevere", f"{lad[min(lad)]['scenarios']['combined-severe']['ifrs9_over_b1']:.3f}")
put("efiveLadderHighSevere", f"{lad[1.0]['scenarios']['combined-severe']['ifrs9_over_b1']:.3f}")
put("efiveLadderSevereAbove", sum(1 for r in lad.values() if r["scenarios"]["combined-severe"]["ifrs9_over_b1"] > 1))
put("efiveLadderCount", len(lad))
put("efiveNlBase", f"{st.mean(r['scenarios']['base']['scenario_sensitivity_nl'] for r in RUNS):.3f}")
put("efiveNlBaseLow", f"{min(r['scenarios']['base']['scenario_sensitivity_nl'] for r in RUNS):.3f}")
put("efiveNlBaseHigh", f"{max(r['scenarios']['base']['scenario_sensitivity_nl'] for r in RUNS):.3f}")
steps = {}
for r in RUNS:
    for sid in ("base", "combined-severe"):
        for k, v in r["scenarios"][sid]["bridge_steps"].items():
            steps.setdefault((sid, k), []).append(v)
for (sid, k), v in steps.items():
    key = "".join(p.capitalize() for p in k.replace("-", " ").split())
    put(f"efiveStep{SC[sid]}{key}", f"{st.mean(v) / 1e9:.1f}")

# ---- E6
d6 = E6["dates"]["2008-12"]
put("esixEntries", d6["entries"])
put("esixEquations", d6["equations"])
put("esixIdentities", d6["engine_identities"])
put("esixRank", d6["rank"])
put("esixKernel", d6["kernel_dimension"])
put("esixBlind", len(d6["blind_entries"]))
put("esixPatterns", d6["distinct_patterns"])
put("esixLargest", d6["largest_group"])
put("esixWorst", sci(max(v["worst_deviation_over_delta"] for v in E6["dates"].values())))
hist = d6["seen_by_histogram"]
put("esixSeenOne", hist.get("1", 0))
put("esixSeenTwo", hist.get("2", 0))
put("esixSeenThree", hist.get("3", 0))

out = ["% Every number the text quotes, written by make_numbers.py from experiments/*.json and the committed C06 and C07 documents.\n"]
out += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in sorted(M.items())]
(HERE / "tables").mkdir(exist_ok=True)
(HERE / "tables" / "numbers.tex").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print(f"wrote tables/numbers.tex with {len(M)} macros")
