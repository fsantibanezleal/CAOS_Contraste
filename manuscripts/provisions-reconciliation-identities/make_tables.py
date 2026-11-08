"""Write the booktabs tables of the manuscript into ``tables/`` from ``experiments/*.json`` and the committed C06 and C07 documents.

    python manuscripts/provisions-reconciliation-identities/make_tables.py

The outcome of every hypothesis is computed here, by the predicate written next to its statement, from the experiment outputs;
the text quotes the table.
"""
from __future__ import annotations

import glob
import json
import math
import pathlib
import re
import statistics as st
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
sys.path.insert(0, str(HERE / "experiments"))
import common  # noqa: E402
import figkit  # noqa: E402

OUT = HERE / "tables"
E1, E2, E3, E4, E6 = (common.load(f) for f in ("e1_gate_power.json", "e2_tolerance_and_rounding.json", "e3_overlays.json", "e4_nonlinearity.json",
                                                "e6_identity_algebra.json"))
RUNS = [json.loads(pathlib.Path(f).read_text(encoding="utf-8")) for f in sorted(glob.glob(str(HERE / "experiments" / "e5_regimes" / "s*-x1.json")))]
LADDER = sorted((json.loads(pathlib.Path(f).read_text(encoding="utf-8")) for f in glob.glob(str(HERE / "experiments" / "e5_regimes" / "s42-x*.json"))),
                key=lambda r: r["scale"])
G = E1["grid"]
CLASSES = ("allowance-movement", "allowance-closing", "stage-reallocation", "gca-movement", "waterfall-line", "waterfall-closing", "stage-ecl",
           "line-misclassification")
CLASS_NAME = {"allowance-movement": "Allowance movement, closing kept", "allowance-closing": "Allowance closing, movements kept",
              "stage-reallocation": "Allowance moved between stages", "gca-movement": "Gross amount movement, closing kept",
              "waterfall-line": "Waterfall movement line", "waterfall-closing": "Waterfall closing line", "stage-ecl": "Model ECL of a stage",
              "line-misclassification": "Amount booked under another line"}
FAMILY_NAME = {"allowance-rollforward": "Allowance roll-forward by stage", "gca-rollforward": "Gross amount roll-forward by stage",
               "waterfall-closes": "Waterfall closes", "waterfall-equals-stage-closings": "Waterfall equals stage closings",
               "waterfall-lines-equal-movements": "Waterfall lines equal stage movements", "stage-closing-equals-ecl": "Stage closing equals ECL plus overlays"}
DETECTABLE = CLASSES[:-1]
SC = {"base": "Base", "recession": "Recession", "house-price-fall": "House price fall", "consumer-arrears-shock": "Consumer arrears shock",
      "uf-inflation-spike": "UF inflation spike", "combined-severe": "Combined severe"}
T975_9 = 2.2621571627


def num(x: int) -> str:
    return f"{x:,}"


def table(name: str, header, rows, *, caption: str, label: str, align: str | None = None, longtable: bool = False, scale: bool = True) -> None:
    def cell(v):
        if isinstance(v, str) and ("$" in v or "\\" in v):
            return v
        return figkit.tex_escape(v) if isinstance(v, str) else figkit.fmt(v)

    caption = re.sub(r"(?<!\\)%", r"\\%", caption)
    align = align or ("l" + "r" * (len(header) - 1))
    head = " & ".join(re.sub(r"(?<!\\)%", r"\\%", h) for h in header) + " \\\\"
    body = [" & ".join(cell(v) for v in r) + " \\\\" for r in rows]
    if longtable:
        lines = [f"\\begin{{longtable}}{{{align}}}", f"\\caption{{{caption}}}\\label{{{label}}}\\\\", "\\toprule", head, "\\midrule", "\\endfirsthead",
                 "\\toprule", head, "\\midrule", "\\endhead", "\\bottomrule", "\\endfoot", *body, "\\end{longtable}", ""]
    else:
        lines = ["\\begin{table}[htbp]", "\\centering", "\\small", f"\\caption{{{caption}}}", f"\\label{{{label}}}"]
        lines.append("\\begin{adjustbox}{max width=\\textwidth}" if scale else "")
        lines += [f"\\begin{{tabular}}{{{align}}}", "\\toprule", head, "\\midrule", *body, "\\bottomrule", "\\end{tabular}"]
        lines += ["\\end{adjustbox}" if scale else "", "\\end{table}", ""]
    (OUT / f"{name}.tex").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def wil(k: int, n: int, d: int = 1) -> str:
    lo, hi = common.wilson(k, n)
    return f"{num(k)}/{num(n)} [{100 * lo:.{d}f}, {100 * hi:.{d}f}]"


def agg(gate: str, mult: str, classes) -> tuple[int, int]:
    return sum(G[c][mult][gate][0] for c in classes), sum(G[c][mult][gate][1] for c in classes)


def sci(x: float, d: int = 1) -> str:
    if x == 0:
        return "$0$"
    e = int(math.floor(math.log10(abs(x))))
    return f"${x / 10 ** e:.{d}f}\\times10^{{{e}}}$"


# ---------------------------------------------------------------------------------------------------------------- hypotheses
def hypotheses() -> list[tuple[str, str, str, str, bool]]:
    """(id, statement, set when, observed, held)"""
    rows: list[tuple[str, str, str, str, bool]] = []
    thr = [E1["threshold"][c] for c in DETECTABLE]
    dev = max(max(abs(t["min_ratio"] - 1), abs(t["max_ratio"] - 1)) for t in thr)
    mis_ok = E1["threshold"]["line-misclassification"]["n_bisected"] == 0
    rows.append(("P1", "The smallest defect the test names equals the limit for every class but the misclassification.", "before the run; the notebook had measured it on one defect class",
                 f"largest deviation of the ratio from 1: {sci(dev)}; misclassification never named", dev < 1e-6 and mis_ok))
    full_ok = agg("full", "1.01", DETECTABLE)[0] == agg("full", "1.01", DETECTABLE)[1] and agg("full", "100", ("line-misclassification",))[0] == 0
    three = ("allowance-movement", "allowance-closing", "gca-movement")
    four = ("stage-reallocation", "waterfall-line", "waterfall-closing", "stage-ecl")
    cmp_ok = all(agg(g, m, three)[0] == agg(g, m, three)[1] for g in ("stage", "total") for m in ("1.01", "10", "100")) and \
        all(agg(g, m, four)[0] == 0 for g in ("stage", "total") for m in ("0.25", "0.5", "0.9", "0.99", "1.01", "1.1", "2", "10", "100"))
    rows.append(("P2", "The pooled row and the stage arithmetic detect three classes above the limit and none of the other four; the twelve identities detect all seven.",
                 "before the run", f"full {num(agg('full', '1.01', DETECTABLE)[0])}/{num(agg('full', '1.01', DETECTABLE)[1])}; stage and pooled "
                 f"{num(agg('stage', '1.01', DETECTABLE)[0])}/{num(agg('stage', '1.01', DETECTABLE)[1])}", full_ok and cmp_ok))
    lost = sorted(f for f in E1["meta"]["families"] if any(G[c]["10"][f"drop:{f}"][0] == 0 for c in DETECTABLE))
    rows.append(("P3", "Leaving out one identity family loses a class entirely for exactly two families: the gross amount roll-forward and the tie to the ECL.",
                 "before the run", f"families whose removal loses a class: {len(lost)} ({', '.join(FAMILY_NAME[f] for f in lost)})",
                 lost == ["gca-rollforward", "stage-closing-equals-ecl"]))
    cm, rs = E2["committed"], E2["resampled"]
    q1 = sum(1 for v in cm.values() if v["abs:1e-06"]) >= 1 and not any(v["rel:1e-06"] for v in cm.values()) and rs["rel:1e-06"][0] == 0
    rows.append(("Q1", "An absolute tolerance of 1e-6 units flags a clean committed table; the relative basis flags none of the six or of the 1,200 resampled books "
                       "(first part a reproduction).", "before the run; the notebook had measured the first part",
                 f"absolute flags {sum(1 for v in cm.values() if v['abs:1e-06'])} of 6 and {rs['abs:1e-06'][0]} of {num(rs['abs:1e-06'][1])}; relative flags "
                 f"{rs['rel:1e-06'][0]}", q1))
    r = E2["rounding"]
    q2 = all(r[k]["flagged"][0] == 0 for k in ("1", "10", "1000")) and r["10000"]["flagged"][0] / r["10000"]["flagged"][1] < 0.01
    rows.append(("Q2", "After rounding to 1, 10 and 1,000 units no book is flagged; at 10,000 fewer than 1% are.", "before the run",
                 f"0, 0, {r['1000']['flagged'][0]} flagged; at 10,000: {r['10000']['flagged'][0]} of {num(r['10000']['flagged'][1])}", q2))
    f5 = r["100000"]["flagged"][0] / r["100000"]["flagged"][1]
    rows.append(("Q3a", "After rounding to 100,000 units between 30% and 95% of the books are flagged.", "before the run", f"{100 * f5:.1f}%", 0.30 <= f5 <= 0.95))
    f6 = r["1e+06"]["flagged"][0] / r["1e+06"]["flagged"][1]
    rows.append(("Q3b", "After rounding to 1,000,000 units more than 99% of the books are flagged.", "before the run", f"{100 * f6:.1f}%", f6 > 0.99))
    inv = E3["invariance"]
    o1 = inv["model_changed"] + inv["total_not_model_plus_overlays"] + inv["carried_not_overlay_total"] == 0
    rows.append(("O1", "The model ECL does not depend on the overlays and the total is the model ECL plus the overlays, in 3,000 draws.", "before the run",
                 f"{inv['sets_checked']:,} overlay sets, violations {inv['model_changed'] + inv['total_not_model_plus_overlays'] + inv['carried_not_overlay_total']}", o1))
    bk = E3["placement"]["bookings"]
    rows.append(("O2", "The correct overlay booking closes every identity in 18 of 18 cases.", "before the run", f"flagged {bk['correct']['full'][0]} of {bk['correct']['full'][1]}",
                 bk["correct"]["full"][0] == 0))
    four_w = ("not-carried", "wrong-stage", "double-carried", "carried-not-in-waterfall")
    o3 = all(bk[k]["full"][0] == 18 for k in four_w) and all(bk[k][g][0] == 0 for k in four_w for g in ("stage", "total"))
    rows.append(("O3", "The twelve identities flag four wrong overlay bookings in 18 of 18 cases each; the stage arithmetic and the pooled row flag none.", "before the run",
                 "full " + ", ".join(f"{bk[k]['full'][0]}" for k in four_w) + f" of 18; stage and pooled {sum(bk[k][g][0] for k in four_w for g in ('stage', 'total'))}", o3))
    rows.append(("O4", "No method flags an overlay merged into the model ECL.", "before the run",
                 f"full {bk['merged-into-model']['full'][0]}, stage {bk['merged-into-model']['stage'][0]}, pooled {bk['merged-into-model']['total'][0]} of 18",
                 all(bk["merged-into-model"][g][0] == 0 for g in ("full", "stage", "total"))))
    sw = E4["sweep"]["classes"]
    rows.append(("N1", "No negative index among the draws whose factors all lie in the convex region (reproduction).", "before the run; the notebook had swept another seed",
                 f"{sw['convex']['negative']} of {num(sw['convex']['n'])}", sw["convex"]["negative"] == 0))
    rows.append(("N2", "No positive index among the draws whose factors all lie in the concave region, with at least 100 such draws.", "before the run",
                 f"{sw['concave']['positive']} of {num(sw['concave']['n'])}", sw["concave"]["positive"] == 0 and sw["concave"]["n"] >= 100))
    rows.append(("N3", "Both signs occur among the draws with factors on both sides of the inflection.", "before the run",
                 f"{num(sw['mixed']['positive'])} positive, {num(sw['mixed']['negative'])} negative", sw["mixed"]["positive"] > 0 and sw["mixed"]["negative"] > 0))
    so = E4["sweep"]["second_order"]
    rows.append(("N4", "The second-order formula is within 25% of the index in at least 75% of the convex draws.", "before the run",
                 f"{100 * so['within_25pct']:.1f}% of {num(so['n'])}", so["within_25pct"] >= 0.75))
    ds = E4["designs"]["designs"]
    rows.append(("R1", "Where the forecast lies two standard deviations inside the convex region the base scenario alone understates the expected PD in at least 99% of the draws.",
                 "before the run", f"{100 * ds['single']['share_negative_strong_margin']:.1f}% of {num(E4['designs']['strong_margin_draws'])}",
                 ds["single"]["share_negative_strong_margin"] >= 0.99))
    order = [ds[k]["median_abs"] for k in ("gh5", "gh3", "tertile3", "adhoc3", "single")]
    rows.append(("R2", "The median absolute error is ordered gh5 < gh3 < tertile3 < adhoc3 < single.", "before the run", "ordered as predicted" if order == sorted(order) else "not ordered",
                 order == sorted(order)))
    br = E4["designs"]["adhoc3_bias_ratio_predicted_over_measured"]
    rows.append(("R3", "The second-order bias of the three-scenario set is within 20% of the measured bias at the median.", "before the run",
                 f"median ratio {br['q50']:.3f}", abs(br["q50"] - 1) <= 0.2))
    bsum = max(r_["scenarios"][s]["bridge_residual"] for r_ in RUNS for s in r_["scenarios"])
    rows.append(("B1", "The bridge closes to within one currency unit in every seed and scenario.", "before the run", f"largest residual {sci(bsum)} over {len(RUNS) * 6} runs", bsum <= 1.0))
    green = all(s["identities"]["light"] == "green" for r_ in RUNS for s in r_["scenarios"].values())
    rows.append(("B2", "The engine's reconciliation test is green in every seed and scenario.", "before the run", "all green" if green else "a red light", green))
    below = all(r_["scenarios"][s]["ifrs9_over_b1"] < 1 for r_ in RUNS for s in r_["scenarios"] if s != "combined-severe")
    above = all(r_["scenarios"]["combined-severe"]["ifrs9_over_b1"] > 1 for r_ in RUNS)
    rows.append(("B3", "IFRS 9 is below B-1 in five scenarios and above it in the combined severe scenario, in every seed.", "before the run",
                 "five below, one above, in all seeds" if below and above else "an exception", below and above))
    bi = sum(1 for r_ in RUNS if r_["scenarios"]["base"]["totals"]["ifrs9"] > r_["scenarios"]["base"]["totals"]["bde-annex9"])
    rows.append(("B4", "IFRS 9 is above Annex 9 in the base scenario in at least 8 of 10 seeds.", "before the run", f"{bi} of {len(RUNS)}", bi >= 8))
    sd = st.stdev(r_["scenarios"]["base"]["ifrs9_over_b1"] for r_ in RUNS)
    rows.append(("B5", "The standard deviation over seeds of the base IFRS 9 over B-1 ratio is below 0.05.", "before the run", f"{sd:.3f}", sd < 0.05))
    r42 = next(r_ for r_ in RUNS if r_["seed"] == 42)
    diff = 0.0
    for sid, v in r42["scenarios"].items():
        for reg in common.doc(f"C07/{sid}.json")["outputs"]["regimes"]:
            diff = max(diff, abs(reg["total_provision"] - v["totals"][reg["regime"]]))
    rows.append(("B6", "The committed seed at the committed size reproduces every committed regime total to within one currency unit (reproduction of the committed totals).", "after the bake; the committed totals had been read",
                 f"largest difference {diff:.2f}", diff <= 1.0))
    d6 = E6["dates"]
    rows.append(("A1", "The engine's residuals equal the signed map times the perturbation for every entry of the six dates.", "before the run",
                 f"largest deviation {sci(max(v['worst_deviation_over_delta'] for v in d6.values()))} of the perturbation",
                 max(v["worst_deviation_over_delta"] for v in d6.values()) < 1e-9))
    nb = max(len(v["blind_entries"]) for v in d6.values())
    rows.append(("A2", "Exactly one entry is seen by no identity: the model ECL of the POCI stage.", "before the run", f"{nb} entries seen by no identity", sum(len(v["blind_entries"]) for v in d6.values()) == 6))
    rows.append(("A3", "The signed map has full row rank.", "before the run", f"rank {d6['2008-12']['rank']} of {d6['2008-12']['equations']} equations",
                 all(v["rank"] == v["equations"] for v in d6.values())))
    rows.append(("A4", "The largest group of entries no failing pattern distinguishes has at least 11 entries.", "before the run",
                 f"largest group {d6['2008-12']['largest_group']}", all(v["largest_group"] >= 11 for v in d6.values())))
    ex = E4["example"]
    rows.append(("C1", "The reference example gives a weighted PD of 2.68% against 1.80% at the mean factor (reproduction of the acceptance criterion).", "after the bake",
                 f"{100 * ex['pd_weighted']:.3f}% against {100 * ex['pd_at_mean_z']:.3f}%", round(100 * ex["pd_weighted"], 2) == 2.68 and round(100 * ex["pd_at_mean_z"], 2) == 1.80))
    clean_flagged = sum(1 for v in E1["clean"].values() if v["flagged"])
    rows.append(("C2", "The identities close on the tolerance basis on the six committed dates (reproduction of the acceptance criterion).", "after the bake",
                 f"{clean_flagged} of 6 flagged", clean_flagged == 0))
    ecl_pos = sum(1 for v in E4["committed"].values() if v["ecl_index"] > 0)
    rows.append(("C3", "The weighted ECL exceeds the ECL at the mean path on every committed date (stated in the product as not claimed).", "after the bake; stated in the product as not claimed",
                 f"{ecl_pos} of 6 dates above zero", ecl_pos == 6))
    return rows


def write_hypotheses() -> None:
    """Two tables from the same rows: the predictions with when they were set (Experimental design) and the outcomes (Results).

    A row set after the bake is a reproduction of a result the committed documents already held, not a prediction; it is counted apart.
    """
    rows = hypotheses()

    def repro(r) -> bool:
        return r[2].startswith("after the bake")

    preds = [r for r in rows if not repro(r)]
    reps = [r for r in rows if repro(r)]
    held = sum(1 for r in preds if r[4])
    rep_ok = sum(1 for r in reps if r[4])
    table("hypotheses", ["ID", "Statement", "Set"], [[i, st, w] for i, st, w, o, ok in rows], align="lp{7.6cm}p{4.4cm}", longtable=True, label="tab:hypotheses",
          caption=f"The {len(rows)} statements tested by the experiments, each stated in the header of its script, with when it was set relative to the run. "
                  f"The {len(preds)} rows not marked after the bake are predictions; the {len(reps)} marked after the bake are reproductions of results that the "
                  "committed documents already held, and they are not counted as predictions.")
    body = [[i, o, ("reproduced" if ok else "contradicted") if repro((i, st, w, o, ok)) else ("held" if ok else "refuted")] for i, st, w, o, ok in rows]
    table("outcomes", ["ID", "Observed", "Outcome"], body, align="lp{9.2cm}l", longtable=True, label="tab:outcomes",
          caption=f"The value observed for each statement and the outcome computed from the experiment output: {held} held and {len(preds) - held} refuted of the "
                  f"{len(preds)} predictions; {rep_ok} reproduced and {len(reps) - rep_ok} contradicted of the {len(reps)} reproductions.")
    refs = ", ".join(r[0] for r in preds if not r[4])
    contra = ", ".join(r[0] for r in reps if not r[4])
    (OUT / "hypotheses-count.tex").write_text(
        f"\\newcommand{{\\hypRows}}{{{len(rows)}}}\n"
        f"\\newcommand{{\\hypTotal}}{{{len(preds)}}}\n"
        f"\\newcommand{{\\hypHeld}}{{{held}}}\n"
        f"\\newcommand{{\\hypRefuted}}{{{len(preds) - held}}}\n"
        f"\\newcommand{{\\hypRefutedList}}{{{refs}}}\n"
        f"\\newcommand{{\\hypReproTotal}}{{{len(reps)}}}\n"
        f"\\newcommand{{\\hypReproHeld}}{{{rep_ok}}}\n"
        f"\\newcommand{{\\hypReproContradicted}}{{{len(reps) - rep_ok}}}\n"
        f"\\newcommand{{\\hypReproContradictedList}}{{{contra}}}\n",
        encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------------------------------------------- main results
def write_main() -> None:
    f_k, f_n = agg("full", "1.01", DETECTABLE)
    s_k, s_n = agg("stage", "1.01", DETECTABLE)
    t_k, t_n = agg("total", "1.01", DETECTABLE)
    b_f, b_n = agg("full", "0.99", tuple(G))
    b_s, _ = agg("stage", "0.99", tuple(G))
    b_t, _ = agg("total", "0.99", tuple(G))
    thr = [E1["threshold"][c] for c in DETECTABLE]
    dev = max(max(abs(t["min_ratio"] - 1), abs(t["max_ratio"] - 1)) for t in thr)
    cm, rs = E2["committed"], E2["resampled"]
    bk = E3["placement"]["bookings"]
    wrong = ("not-carried", "wrong-stage", "double-carried", "carried-not-in-waterfall")
    ow = {g: sum(bk[k][g][0] for k in wrong) for g in ("full", "stage", "total")}
    on = sum(bk[k]["full"][1] for k in wrong)
    sw = E4["sweep"]["classes"]
    ds = E4["designs"]["designs"]

    def med(k: str) -> str:
        d = ds[k]
        x, lo, hi = d["median_abs"], d["median_abs_ci"][0], d["median_abs_ci"][1]
        if x < 1e-3:
            return f"{sci(100 * x)}\\% [{sci(100 * lo)}, {sci(100 * hi)}]"
        return f"{100 * x:.2f}\\% [{100 * lo:.2f}, {100 * hi:.2f}]"

    def ratio(sid: str) -> str:
        v = [r["scenarios"][sid]["ifrs9_over_b1"] for r in RUNS]
        m, sd = st.mean(v), st.stdev(v)
        h = T975_9 * sd / math.sqrt(len(v))
        return f"{m:.3f} [{m - h:.3f}, {m + h:.3f}]"

    rows = [
        ["Detection above the limit (1.01 times), seven defect classes, 600 cases each", f"{wil(f_k, f_n)}", f"stage {wil(s_k, s_n)}; pooled {wil(t_k, t_n)}", "Wilson 95% interval, percent"],
        ["Detection below the limit (0.99 times), eight classes", f"{wil(b_f, b_n)}", f"stage {num(b_s)}/{num(b_n)}; pooled {num(b_t)}/{num(b_n)}", "Wilson 95% interval, percent"],
        ["Smallest defect named, as a multiple of the limit, 120 bisections per class", f"1 within {sci(dev)}", "not applicable (no comparator names a size)", "largest deviation over 840 bisections"],
        ["Clean committed tables flagged (six dates)", f"{sum(1 for v in cm.values() if v['rel:1e-06'])}/6 (relative 1e-6)", f"{sum(1 for v in cm.values() if v['abs:1e-06'])}/6 (absolute 1e-6)", "count, no sampling"],
        ["Clean resampled books flagged (1,200)", wil(*rs["rel:1e-06"]), f"absolute 1e-6: {wil(*rs['abs:1e-06'])}", "Wilson 95% interval, percent"],
        ["Wrong overlay bookings detected (four kinds, 18 cases each)", f"{ow['full']}/{on}", f"stage {ow['stage']}/{on}; pooled {ow['total']}/{on}", "count over the full enumeration"],
        ["Negative index among draws in the convex region", f"{num(sw['convex']['negative'])}/{num(sw['convex']['n'])}", "unqualified statement fails in "
         f"{num(sw['concave']['negative'] + sw['mixed']['negative'])}/{num(E4['sweep']['draws'])} draws", "count over the sweep"],
        ["Median absolute error of the expected PD, base scenario alone", "not applicable", f"{med('single')}", "bootstrap 95% interval"],
        ["Median absolute error, three scenarios at one standard deviation, 25/50/25", "not applicable", f"{med('adhoc3')}", "bootstrap 95% interval"],
        ["Median absolute error, three equal-probability tertile scenarios", "not applicable", f"{med('tertile3')}", "bootstrap 95% interval"],
        ["Median absolute error, three-point Gauss--Hermite scenarios", "not applicable", f"{med('gh3')}", "bootstrap 95% interval"],
        ["IFRS 9 over B-1, base scenario, ten seeds", ratio("base"), "B-1 is the reference (1)", "mean and 95\\% $t$ interval"],
        ["IFRS 9 over B-1, combined severe scenario, ten seeds", ratio("combined-severe"), "B-1 is the reference (1)", "mean and 95\\% $t$ interval"],
        ["Largest bridge residual, 60 runs (currency units)", sci(max(r["scenarios"][s]["bridge_residual"] for r in RUNS for s in r["scenarios"])), "not applicable", "maximum, no sampling"],
    ]
    table("main-results", ["Measurement", "Proposed protocol", "Comparator", "Uncertainty"], rows, align="p{5.4cm}p{3.3cm}p{4.0cm}p{3.0cm}", label="tab:main-results",
          caption="Main comparison of the proposed protocol with the comparators run on the same data: detection of planted defects by the twelve identities, the stage "
                  "arithmetic and the pooled row; false alarms on clean tables by tolerance basis; overlay bookings; the non-linearity of the weighted PD; the error of short "
                  "scenario sets against the full distribution of the factor; and the three regimes of the synthetic bank over ten seeds. Intervals as stated in the last column.")


# ---------------------------------------------------------------------------------------------------------------- others
def write_data() -> None:
    rows = []
    for d in common.DATES:
        a = common.doc(f"C06/rd-{d}.json")["outputs"]
        e1 = E1["clean"][d]
        s2 = a["stage_summary"]["rows"]
        gross = sum(r["gross_carrying_amount"] for r in s2)
        rows.append([d, f"{gross / 1e9:.1f}", f"{e1['limit']:,.0f}", f"{100 * s2[1]['gross_carrying_amount'] / gross:.1f}\\%", f"{sum(r['accounts'] for r in s2):,}",
                     sci(e1["max_residual"])])
    table("data", ["Date", "Gross amount G (USD bn)", "Limit $10^{-6}G$ (USD)", "Stage 2 share", "Loans", "Largest residual (USD)"], rows, align="lrrrrr", label="tab:data",
          caption="The six committed reporting dates of the SBA 7(a) loan book: the gross carrying amount G, the limit of the test on the engine's tolerance basis, the share "
                  "of the gross amount in Stage 2, the number of loans in the staged book and the largest residual of the twelve identities on the committed tables.")


def write_placement() -> None:
    bk = E3["placement"]["bookings"]
    name = {"correct": "Correct booking (stage 1 row, waterfall line, both closings)", "not-carried": "Waterfall only, stage rows untouched",
            "wrong-stage": "Carried in the stage 2 row, waterfall line at portfolio level", "double-carried": "Carried in stage 1 and stage 2 rows, one waterfall line",
            "carried-not-in-waterfall": "Carried in the stage 1 row, no waterfall line", "merged-into-model": "Added to the model ECL under the remeasurement line"}
    rows = [[name[k], f"{v['full'][0]}/{v['full'][1]}", f"{v['stage'][0]}/{v['stage'][1]}", f"{v['total'][0]}/{v['total'][1]}",
             f"{v['identities_flagged_min']}" if v["identities_flagged_min"] == v["identities_flagged_max"] else f"{v['identities_flagged_min']}--{v['identities_flagged_max']}"]
            for k, v in bk.items()]
    table("placement", ["Booking of an overlay", "Twelve identities", "Stage arithmetic", "Pooled row", "Identities failing"], rows, align="p{6.6cm}rrrr", label="tab:placement",
          caption="Six ways to book an overlay of 2%, 10% and 25% of the allowance on each of the six committed dates (18 cases per row): cases flagged by the twelve identities, by the "
                  "two roll-forwards of each stage alone and by one pooled row, and the number of identities that fail when the booking is flagged.")


def write_rounding() -> None:
    r = E2["rounding"]
    rows = []
    for key, label in (("1", "1"), ("10", "10"), ("1000", "1,000"), ("10000", "10,000"), ("100000", "100,000"), ("1e+06", "1,000,000")):
        k, n = r[key]["flagged"]
        lo, hi = common.wilson(k, n)
        rows.append([label, f"{k:,}/{n:,}", f"{100 * k / n:.1f} [{100 * lo:.1f}, {100 * hi:.1f}]", f"{r[key]['ratio_q50']:.3f}", f"{r[key]['ratio_q99']:.3f}", f"{r[key]['ratio_max']:.2f}"])
    table("rounding", ["Rounded to (units)", "Flagged", "Percent [Wilson 95%]", "Median", "99th percentile", "Maximum"], rows, align="lrrrrr", label="tab:rounding",
          caption="False alarms of the test on 1,200 clean resampled books after every stored number is rounded independently to the stated unit: books flagged, and the largest "
                  "residual of a book as a multiple of the limit (median, 99th percentile and maximum over the books; a value above 1 is a flag).")


def write_designs() -> None:
    d = E4["designs"]["designs"]
    nm = {"single": "Base scenario alone", "adhoc3": "Three scenarios at one standard deviation, 25/50/25", "tertile3": "Three equal-probability tertile means",
          "gh3": "Three-point Gauss--Hermite", "gh5": "Five-point Gauss--Hermite"}
    rows = []
    for k in ("single", "adhoc3", "tertile3", "gh3", "gh5"):
        q = d[k]["quantiles"]
        rows.append([nm[k], f"{100 * q['q05']:+.3g}", f"{100 * q['q50']:+.3g}", f"{100 * q['q95']:+.3g}", f"{100 * d[k]['share_abs_above_5pct']:.1f}\\%",
                     f"{100 * d[k]['share_negative_strong_margin']:.1f}\\%"])
    table("designs", ["Scenario set", "5th pct (\\%)", "Median (\\%)", "95th pct (\\%)", "$|$error$|>5\\%$", "Understated (convex margin)"], rows, align="p{5.2cm}rrrrr", label="tab:designs",
          caption="Relative error of the expected PD of five scenario sets against the 64-node Gauss--Hermite expectation under a normal factor, over 5,000 draws of the PD, the "
                  "correlation and the forecast mean and spread: quantiles of the signed error in percent, the share of draws with absolute error above 5%, and the share "
                  "understated among the draws whose forecast lies two standard deviations inside the convex region.")


def write_committed() -> None:
    rows = []
    for dte, v in E4["committed"].items():
        rows.append([dte, f"{v['zstar']:.2f}", f"{v['z_min']:.2f}", f"{v['z_max']:.2f}", f"{v['pd_index_committed']:.5f}", f"{v['ecl_index']:+.5f}",
                     f"{100 * v['stage2_ratio_committed']:.1f}\\%", f"{v['stage2_gap']:.5f}"])
    table("committed-nonlinearity", ["Date", "Inflection $z^*$", "Lowest $z$", "Highest $z$", "PD-level index", "ECL-level index", "Stage 2 share",
                                     "Stage 2 gap"], rows, align="lrrrrrrr", label="tab:committed-nonlinearity",
          caption="The six committed C06 dates: the inflection of the conditional PD, the lowest and highest scenario factor, the PD-level index recomputed by the engine from the "
                  "committed scenario factors (equal to the committed value), the committed ECL-level index, the Stage 2 share of the gross amount and the gap between the "
                  "Stage 2 ratio under recomputed and frozen staging at the grid weights nearest to the committed ones.")


def write_regimes() -> None:
    rows = []
    for sid, label in SC.items():
        a = common.doc(f"C07/{sid}.json")["outputs"]
        tot = {r["regime"]: r["total_provision"] for r in a["regimes"]}
        i9 = [r["scenarios"][sid]["ifrs9_over_b1"] for r in RUNS]
        bd = [r["scenarios"][sid]["bde_over_b1"] for r in RUNS]
        m, sd = st.mean(i9), st.stdev(i9)
        h = T975_9 * sd / math.sqrt(len(i9))
        mb, sb = st.mean(bd), st.stdev(bd)
        hb = T975_9 * sb / math.sqrt(len(bd))
        rows.append([label, f"{tot['cmf-b1'] / 1e9:.1f}", f"{tot['ifrs9'] / 1e9:.1f}", f"{tot['bde-annex9'] / 1e9:.1f}", f"{tot['ifrs9'] / tot['cmf-b1']:.3f}",
                     f"{m:.3f} [{m - h:.3f}, {m + h:.3f}]", f"{mb:.3f} [{mb - hb:.3f}, {mb + hb:.3f}]"])
    table("regimes", ["Scenario", "B-1 (CLP bn)", "IFRS 9 (CLP bn)", "Annex 9 (CLP bn)", "IFRS 9/B-1", "IFRS 9/B-1, ten seeds", "Annex 9/B-1, ten seeds"], rows,
          align="lrrrrrr", label="tab:regimes",
          caption="The three provisioning regimes on the synthetic Banco Andino in six scenarios: the committed totals (seed 42, full size), their ratio, and the mean over ten seeds at "
                  "full size of the IFRS 9 and Annex 9 totals over the B-1 total with the 95% $t$ interval of the mean in brackets.")


def write_ladder() -> None:
    rows = []
    for r in LADDER:
        s = r["scenarios"]
        rows.append([f"{r['scale']:g}", f"{r['n_accounts']:,}", f"{s['base']['ifrs9_over_b1']:.3f}", f"{s['recession']['ifrs9_over_b1']:.3f}",
                     f"{s['combined-severe']['ifrs9_over_b1']:.3f}", f"{max(v['bridge_residual'] for v in s.values()):.1e}", f"{r['seconds']:.0f}"])
    table("ladder", ["Size factor", "Accounts", "Base", "Recession", "Combined severe", "Bridge residual", "Seconds"], rows, align="rrrrrrr", label="tab:ladder",
          caption="The IFRS 9 total over the B-1 total of the synthetic bank at seed 42 for six sizes of the generated book (the size factor scales every portfolio's account "
                  "count), with the largest bridge residual over the six scenarios in currency units and the measured time of one build of the six scenarios.")


def write_ablation() -> None:
    rows = []
    for fam in E1["meta"]["families"]:
        row = [FAMILY_NAME[fam]]
        for c in DETECTABLE:
            k, n = G[c]["10"][f"drop:{fam}"]
            row.append("0" if k == 0 else ("all" if k == n else f"{100 * k / n:.0f}\\%"))
        row.append(str(sum(1 for c in DETECTABLE if G[c]["10"][f"drop:{fam}"][0] == 0)))
        rows.append(row)
    row = ["None left out (twelve identities)"] + ["all" for _ in DETECTABLE] + ["0"]
    rows.append(row)
    short = ["Alw. mov.", "Alw. clos.", "Realloc.", "GCA mov.", "WF line", "WF clos.", "Stage ECL"]
    table("ablation", ["Identity family left out", *short, "Classes lost"], rows, align="p{4.6cm}rrrrrrrr", label="tab:ablation",
          caption="Ablation of the twelve identities by family: share of the 600 cases of each defect class (defect of ten times the limit) that the remaining identities still flag when one family is left "
                  "out; the last column counts the classes that no remaining identity detects.")
    # the other components: what removing each one costs
    cm, rs = E2["committed"], E2["resampled"]
    sw = E4["sweep"]["classes"]
    comp = [
        ["Relative tolerance basis replaced by an absolute tolerance of 1e-6 units", "false alarms on clean books", f"{wil(*rs['rel:1e-06'])}", f"{wil(*rs['abs:1e-06'])}"],
        ["Cross identities removed (stage arithmetic only)", "detection above the limit, seven classes", wil(*agg("full", "1.01", DETECTABLE)), wil(*agg("stage", "1.01", DETECTABLE))],
        ["Separate overlay line replaced by a merge into the model ECL", "wrong bookings of the overlay detected", "72/72 (four kinds)", "not applicable: no line to test"],
        ["Convex-region qualifier dropped from the non-linearity statement", "draws that contradict the statement", f"0/{num(sw['convex']['n'])} (qualified)",
         f"{num(sw['concave']['negative'] + sw['mixed']['negative'])}/{num(E4['sweep']['draws'])} (unqualified)"],
        ["Probability-weighted scenarios replaced by the base scenario alone", "median absolute error of the expected PD", f"{100 * E4['designs']['designs']['gh3']['median_abs']:.4f}\\% (three-point)",
         f"{100 * E4['designs']['designs']['single']['median_abs']:.2f}\\%"],
    ]
    table("ablation-components", ["Component removed", "Measure", "With the component", "Without it"], comp, align="p{4.8cm}p{3.6cm}p{3.4cm}p{3.4cm}",
          label="tab:ablation-components",
          caption="Ablation of the other components of the protocol, each measured on the experiment that exercises it: the tolerance basis, the cross identities, the separate overlay "
                  "line, the region qualifier of the non-linearity statement and the weighting of scenarios, with the value of the measure with and without the component.")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for fn in (write_hypotheses, write_main, write_data, write_placement, write_rounding, write_designs, write_committed, write_regimes, write_ladder, write_ablation):
        fn()
    print("wrote", sorted(p.name for p in OUT.glob("*.tex")))


if __name__ == "__main__":
    main()
