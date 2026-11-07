"""Write ``tables/numbers.tex``: every number the prose of the manuscript quotes, as a LaTeX macro, from the experiment outputs.

    python manuscripts/adaptive-conformal-recalibration-of-var/make_numbers.py

The text never types a result: it writes ``\\hypCellsHold`` and this file defines it from ``experiments/*.json`` and from the
committed C11 documents. A macro name holds letters only (TeX), so digits are spelled in the name where needed.
"""
from __future__ import annotations

import collections
import json
import pathlib
import statistics as st
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "experiments"))
import common  # noqa: E402

E2 = common.load("e2_wrap_ladder.json")
E3 = common.load("e3_ablation.json")
E4 = common.load("e4_score_space.json")
E5 = common.load("e5_generators.json")
E6 = common.load("e6_theory.json")
CONF = common.doc("equity-2007-09")["outputs"]["conformal"]
HYP = CONF["hypothesis"]

M: dict[str, str] = {}


def put(name: str, value) -> None:
    M[name] = str(value)


def pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}"


def signed_pct(x: float, d: int = 1) -> str:
    return f"{100 * x:+.{d}f}".replace("+", "+")


def p3(x) -> str:
    return "--" if x is None else f"{x:.3f}"


LV = {0.01: "One", 0.025: "TwoHalf"}
MODEL = {"hs-250": "HsTwoFifty", "hs-500": "HsFiveHundred", "awhs": "Awhs", "dn-rolling": "DnRolling", "ewma": "Ewma", "garch-t": "GarchT",
         "gjr-t": "GjrT", "egarch-t": "EgarchT", "fhs": "Fhs", "evt-mf": "EvtMf"}
WIN = {"equity-2007-09": "EqCrisis", "equity-2020": "EqCovid", "rates-2022": "Rates", "fx-2008": "Fx", "mixed-2023": "Mixed", "calm-2004-06": "Calm"}
SCEN = {"no-shift": "Null", "crisis-persistent": "Crisis", "crash-decay": "Crash", "drift-up": "Drift"}
METH = {"unwrapped": "Unw", "aci": "Aci", "rolling": "Roll", "tracker": "Trk"}

# ---- the committed verdict (the product's own bake)
put("hypCells", HYP["n_cells"])
put("hypCellsHold", HYP["n_cells_hold"])
put("hypExtraTotal", sum(c["extra_windows"] for c in HYP["cells"]))
put("hypWorstFz", signed_pct(max(c["worst_fz0_change"] for c in HYP["cells"])))
put("hypStressDays", HYP["run"]["n_stress_days"])
ind = [x["independence_p"] for x in HYP["independence_2007_09"]]
put("indMin", p3(min(ind)))
put("indMax", p3(max(ind)))
put("indFails", sum(x["fails"] for x in HYP["independence_2007_09"]))
put("hypRefuted", "yes" if HYP["refuted"] else "no")
put("gammaDefault", "0.005")
for k, w in enumerate(common.WINDOWS):
    d = common.doc(w)["outputs"]
    put(f"nDays{WIN[w]}", d["window"]["n_forecast_days"])

# ---- reproduction
put("reproChecked", E2["reproduction"]["checked"])
put("reproEqual", E2["reproduction"]["equal"])

# ---- experiment 2: ten models, stress windows
R = [r for r in E2["rows"] if r["window"] in common.STRESS]
cells = collections.defaultdict(list)
for r in R:
    cells[(r["model"], r["alpha"])].append(r)
n_cells = len(cells)
gain = {k: sum(common.passes(x["wrapped"]) for x in v) - sum(common.passes(x["unwrapped"]) for x in v) for k, v in cells.items()}
worst = {k: max(x["fz0_change"] for x in v) for k, v in cells.items()}
hold = {k: gain[k] >= 1 and worst[k] <= 0.05 for k in cells}
put("tenCells", n_cells)
put("tenCellsHold", sum(hold.values()))
put("tenCellsGain", sum(g >= 1 for g in gain.values()))
put("tenCellsNoLoss", sum(g >= 0 for g in gain.values()))
put("tenModels", len(E2["models"]))
put("tenPassUnw", sum(common.passes(r["unwrapped"]) for r in R))
put("tenPassAci", sum(common.passes(r["wrapped"]) for r in R))
put("tenRuns", len(R))
put("tenWorstFz", signed_pct(max(worst.values())))
put("tenBestFz", signed_pct(min(r["fz0_change"] for r in R)))
put("tenIndFailAci", sum(1 for r in R if r["wrapped"]["independence_p"] is not None and r["wrapped"]["independence_p"] < 0.05))
put("tenIndFailUnw", sum(1 for r in R if r["unwrapped"]["independence_p"] is not None and r["unwrapped"]["independence_p"] < 0.05))
put("tenIndFailAciAll", sum(1 for r in E2["rows"] if r["wrapped"]["independence_p"] is not None and r["wrapped"]["independence_p"] < 0.05))
put("tenIndFailUnwAll", sum(1 for r in E2["rows"] if r["unwrapped"]["independence_p"] is not None and r["unwrapped"]["independence_p"] < 0.05))
put("tenIndRunsAll", len(E2["rows"]))
put("tenHitDevUnw", f"{100 * st.mean(abs(r['unwrapped']['hit_rate'] - r['alpha']) for r in R):.2f}")
put("tenHitDevAci", f"{100 * st.mean(abs(r['wrapped']['hit_rate'] - r['alpha']) for r in R):.2f}")
put("tenMeanFz", signed_pct(st.mean(r["fz0_change"] for r in R)))
put("tenMeanZtwoUnw", f"{st.mean(r['unwrapped']['z2'] for r in R):.2f}")
put("tenMeanZtwoAci", f"{st.mean(r['wrapped']['z2'] for r in R):.2f}")
fail = [k for k, g in gain.items() if g < 1]
put("tenNoGainCells", ", ".join(f"{k[0]} at {pct(k[1])}\\%" for k in fail) if fail else "none")
put("tenClipTotal", sum(r["n_clipped"] for r in R))
put("tenClipMax", max(r["n_clipped"] for r in R))
put("tenFallback", sum(r["n_fallback_days"] for r in E2["rows"]))
for (m, a), v in cells.items():
    put(f"gain{MODEL[m]}{LV[a]}", gain[(m, a)])
    put(f"worstFz{MODEL[m]}{LV[a]}", signed_pct(worst[(m, a)]))
for r in R:
    k = f"{MODEL[r['model']]}{LV[r['alpha']]}{WIN[r['window']]}"
    put(f"hitU{k}", r["unwrapped"]["n_hits"])
    put(f"hitW{k}", r["wrapped"]["n_hits"])
    put(f"fzChg{k}", signed_pct(r["fz0_change"]))
    put(f"fzLo{k}", signed_pct(r["ci95"][0]))
    put(f"fzHi{k}", signed_pct(r["ci95"][1]))
    put(f"kupU{k}", p3(r["unwrapped"]["kupiec_p"]))
    put(f"kupW{k}", p3(r["wrapped"]["kupiec_p"]))
    put(f"ccU{k}", p3(r["unwrapped"]["cc_p"]))
    put(f"ccW{k}", p3(r["wrapped"]["cc_p"]))
    put(f"indW{k}", p3(r["wrapped"]["independence_p"]))
    put(f"indU{k}", p3(r["unwrapped"]["independence_p"]))
    put(f"clip{k}", r["n_clipped"])

# ---- the ladder as a whole (unwrapped, all eighteen) from experiment 4
U = {(r["window"], r["model"], r["alpha"]): r for r in E4["rows"] if r["method"] == "unwrapped"}
for w in common.STRESS:
    for a in common.LEVELS:
        pas = {m: U[(w, m, a)]["passes"] for (ww, m, aa) in U if ww == w and aa == a}
        wr = {(r["model"]): common.passes(r["wrapped"]) for r in E2["rows"] if r["window"] == w and r["alpha"] == a}
        three = {m: (wr[m] if m in common.WRAPPED3 else p) for m, p in pas.items()}
        ten = {m: (wr[m] if m in wr else p) for m, p in pas.items()}
        put(f"ladU{WIN[w]}{LV[a]}", sum(pas.values()))
        put(f"ladThree{WIN[w]}{LV[a]}", sum(three.values()))
        put(f"ladTen{WIN[w]}{LV[a]}", sum(ten.values()))
put("ladModels", len({m for (_, m, _) in U}))
put("ladPassAllU", sum(r["passes"] for (w, m, a), r in U.items() if w in common.STRESS))
put("ladCellsAll", sum(1 for (w, m, a) in U if w in common.STRESS))

# ---- experiment 4: the comparators, pooled over the stress windows
def pooled(method: str, models: set[str] | None):
    rows = [r for r in E4["rows"] if r["method"] == method and r["window"] in common.STRESS and (models is None or r["model"] in models)]
    return rows


TEN = set(E2["models"])
for meth, tag in (("unwrapped", "Unw"), ("rolling", "Roll"), ("tracker", "Trk"), ("tracker-eta-0.01", "TrkSmall"), ("tracker-eta-0.2", "TrkLarge")):
    for scope, models in (("Ten", TEN), ("All", None)):
        rows = pooled(meth, models)
        put(f"cmp{tag}{scope}Pass", sum(r["passes"] for r in rows))
        put(f"cmp{tag}{scope}N", len(rows))
        put(f"cmp{tag}{scope}Ind", sum(1 for r in rows if r["scores"]["independence_p"] is not None and r["scores"]["independence_p"] < 0.05))
        put(f"cmp{tag}{scope}Dev", f"{100 * st.mean(abs(r['scores']['hit_rate'] - r['alpha']) for r in rows):.2f}")
        fz = [r["fz0_change"] for r in rows if "fz0_change" in r]
        if fz:
            put(f"cmp{tag}{scope}Fz", signed_pct(st.mean(fz)))
            put(f"cmp{tag}{scope}FzWorst", signed_pct(max(fz)))
            put(f"cmp{tag}{scope}FzOver", sum(1 for x in fz if x > 0.05))
            put(f"cmp{tag}{scope}FzN", len(fz))
rows = pooled("rolling", None)
put("cmpAllNoEs", sum(1 for r in rows if not r["has_es"]))
put("eqnRollWindow", E4["constants"]["window"])

# ---- experiment 3: ablation
V = collections.defaultdict(list)
for r in E3["rows"]:
    if r["window"] in common.STRESS:
        V[r["variant"]].append(r)
for v, rs in V.items():
    tag = "".join(c for c in v.title() if c.isalpha()) if v[0].isalpha() else v
    tag = {"off": "Off", "full": "Full", "gamma-0.001": "GammaA", "gamma-0.0025": "GammaB", "gamma-0.01": "GammaC", "gamma-0.02": "GammaD",
           "gamma-0.05": "GammaE", "band-wide": "BandWide", "band-narrow": "BandNarrow", "es-ratio": "EsRatio", "es-target": "EsTarget"}[v]
    put(f"abl{tag}Pass", sum(r["passes"] for r in rs))
    put(f"abl{tag}N", len(rs))
    put(f"abl{tag}Ind", sum(1 for r in rs if r["scores"]["independence_p"] is not None and r["scores"]["independence_p"] < 0.05))
    put(f"abl{tag}Dev", f"{100 * st.mean(abs(r['scores']['hit_rate'] - r['alpha']) for r in rs):.2f}")
    fz = [r["fz0_change"] for r in rs if r["fz0_change"] is not None]
    put(f"abl{tag}Fz", signed_pct(st.mean(fz)) if fz else "0.0")
    put(f"abl{tag}FzWorst", signed_pct(max(fz)) if fz else "0.0")
    put(f"abl{tag}Ztwo", f"{st.mean(r['scores']['z2'] for r in rs):.2f}")
    put(f"abl{tag}Clip", sum(r["n_clipped"] for r in rs))

# ---- experiment 5: generators
G = collections.defaultdict(list)
for r in E5["rows"]:
    G[(r["scenario"], r["model"], r["alpha"], r["method"])].append(r)
put("genReps", E5["reps"])
put("genCalm", E5["calm_days"])
for (s, m, a, me), rs in G.items():
    k = f"{SCEN[s]}{MODEL[m]}{LV[a]}{METH[me]}"
    put(f"genPass{k}", f"{st.mean(x['passes'] for x in rs):.2f}")
    put(f"genHit{k}", f"{100 * st.mean(x['hit_rate'] for x in rs):.2f}")
    put(f"genErr{k}", f"{st.mean(x['log_var_err'] for x in rs):.3f}")
    fz = [x["fz0_change"] for x in rs if x["fz0_change"] is not None]
    if fz:
        put(f"genFz{k}", signed_pct(st.median(fz)))
shift = [s for s in E5["scenarios"] if s != "no-shift"]
ok_a = all(st.mean(x["passes"] for x in G[(s, m, a, "aci")]) > st.mean(x["passes"] for x in G[(s, m, a, "unwrapped")])
           for s in shift for m in common.WRAPPED3 for a in common.LEVELS)
for _me in ("unwrapped", "aci"):
    _rs = G[("crisis-persistent", "hs-250", 0.01, _me)]
    _lo, _hi = common.wilson(sum(x["passes"] for x in _rs), len(_rs))
    put(f"genCiLo{METH[_me]}", f"{_lo:.2f}")
    put(f"genCiHi{METH[_me]}", f"{_hi:.2f}")
put("genPredA", "held" if ok_a else "did not hold")
put("genPredANum", sum(st.mean(x["passes"] for x in G[(s, m, a, "aci")]) > st.mean(x["passes"] for x in G[(s, m, a, "unwrapped")])
                       for s in shift for m in common.WRAPPED3 for a in common.LEVELS))
put("genPredADen", len(shift) * 3 * 2)
b_diff = [st.mean(x["passes"] for x in G[("no-shift", m, a, "aci")]) - st.mean(x["passes"] for x in G[("no-shift", m, a, "unwrapped")])
          for m in common.WRAPPED3 for a in common.LEVELS]
put("genPredBDiffMax", f"{max(b_diff):.2f}")
put("genPredBDiffMin", f"{min(b_diff):.2f}")
put("genPredBWithin", sum(abs(d) <= 0.05 for d in b_diff))
b_fz = [abs(st.median([x["fz0_change"] for x in G[("no-shift", m, a, "aci")]])) for m in common.WRAPPED3 for a in common.LEVELS]
put("genPredBFzMax", pct(max(b_fz)))
c_ok = sum(abs(st.mean(x["hit_rate"] for x in G[(s, m, a, "aci")]) - a) < abs(st.mean(x["hit_rate"] for x in G[(s, m, a, "unwrapped")]) - a)
           for s in shift for m in common.WRAPPED3 for a in common.LEVELS)
put("genPredCNum", c_ok)
e_ok = sum(st.mean(x["log_var_err"] for x in G[(s, "hs-250", a, "aci")]) < st.mean(x["log_var_err"] for x in G[(s, "hs-250", a, "unwrapped")])
           for s in shift for a in common.LEVELS)
put("genPredENum", e_ok)
put("genPredEDen", len(shift) * 2)
worse = [(s, m, a) for s in E5["scenarios"] for m in ("garch-t", "fhs") for a in common.LEVELS
         if st.mean(x["log_var_err"] for x in G[(s, m, a, "aci")]) > st.mean(x["log_var_err"] for x in G[(s, m, a, "unwrapped")])]
put("genErrWorseCells", len(worse))
put("genErrWorseDen", len(E5["scenarios"]) * 4)
low = min(((st.mean(x["passes"] for x in G[(s, m, a, "aci")]), s, m, a) for s in shift for m in common.WRAPPED3 for a in common.LEVELS))
put("genLowestAciPass", f"{low[0]:.2f}")
put("genLowestAciScen", low[1])
ind_drop = max(st.mean(x["independence_ok"] for x in G[(s, m, a, "unwrapped")]) - st.mean(x["independence_ok"] for x in G[(s, m, a, "aci")])
               for s in E5["scenarios"] for m in common.WRAPPED3 for a in common.LEVELS)
put("genIndDropMax", f"{ind_drop:.2f}")
mx = max(abs(st.median([x["fz0_change"] for x in G[(s, m, a, "aci")]])) for s in E5["scenarios"] for m in common.WRAPPED3 for a in common.LEVELS)
mxs = max(st.median([x["fz0_change"] for x in G[(s, m, a, "aci")]]) for s in E5["scenarios"] for m in common.WRAPPED3 for a in common.LEVELS)
put("genFzAbsMax", pct(mx))
put("genFzPosMax", signed_pct(mxs))

# ---- experiment 6: theory
A = E6["A"]
put("thA", len(A["rows"]))
put("thAHold", sum(r["holds"] for r in A["rows"]))
put("thAResidual", f"{A['max_identity_residual']:.1e}".replace("e-", "\\times 10^{-") + "}")
put("thAMaxErr", f"{100 * max(r['abs_coverage_error'] for r in A['rows']):.2f}")
put("thAMeanSimple", f"{100 * st.mean(r['bound_simple'] for r in A['rows']):.1f}")
put("thAMeanBound", f"{100 * st.mean(r['bound_exact'] for r in A['rows']):.1f}")
for r in E6["B"]["rows"]:
    k = f"{LV[r['alpha']]}{r['cluster']}".replace("1", "I").replace("2", "Two").replace("3", "Three").replace("4", "Four")
    put(f"thBKup{k}", f"{r['kupiec_p']:.3f}")
    put(f"thBInd{k}", f"{r['independence_p']:.1e}")
    put(f"thBT{k}", r["T"])
    put(f"thBQuiet{k}", r["quiet_days"])
    put(f"thBGamma{k}", r["gamma"])
for r in E6["C"]["rows"]:
    if r["scale_ratio"] in (1.5,):
        k = LV[r["alpha"]]
        put(f"thCAstar{k}", f"{r['a_star']:.4f}")
        put(f"thCMean{k}", f"{r['level_mean']:.4f}")
        put(f"thCHit{k}", f"{100 * r['hit_rate']:.2f}")
        put(f"thCSd{k}", f"{r['level_sd']:.4f}")
        put(f"thCSdPred{k}", f"{r['level_sd_pred']:.4f}")
    if r["scale_ratio"] == 1.0:
        k = LV[r["alpha"]]
        put(f"thCHitUnit{k}", f"{100 * r['hit_rate']:.2f}")
        put(f"thCMeanUnit{k}", f"{r['level_mean']:.4f}")
    put(f"thCCmax{LV[r['alpha']]}", f"{r['c_max']:.2f}")
put("thCIdGap", f"{max(r['identity_gap'] for r in E6['C']['rows']):.1e}")
for r in E6["C"]["rows"]:
    if r["scale_ratio"] == 1.5:
        k = LV[r["alpha"]]
        put(f"thCExcess{k}", f"{100 * (r['hit_rate'] - r['alpha']):.2f}")
        put(f"thCCut{k}", f"{100 * r['cut_over_gamma']:.2f}")
rat = [r["level_sd"] / r["level_sd_pred"] for r in E6["C"]["rows"] if r["in_band"] and r["scale_ratio"] > 1]
put("thCSdRatioMin", f"{min(rat):.2f}")
put("thCSdRatioMax", f"{max(rat):.2f}")
for r in E6["D"]["rows"]:
    if r["scale_ratio"] == 2.0 and r["alpha"] == 0.01:
        put("thDRatioNu" + {3: "Three", 5: "Five", 10: "Ten", 30: "Thirty"}[int(r["nu"])], f"{r['es_ratio']:.3f}")
put("seedBase", common.SEED_BOOT)

out = HERE / "tables" / "numbers.tex"
out.parent.mkdir(parents=True, exist_ok=True)
lines = ["% Generated by make_numbers.py from experiments/*.json; do not edit."]
for k in sorted(M):
    lines.append(f"\\newcommand{{\\{k}}}{{{M[k]}}}")
out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print(f"wrote {out} with {len(M)} macros")
