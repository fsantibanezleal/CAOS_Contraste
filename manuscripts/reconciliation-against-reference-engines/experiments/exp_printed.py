"""Printed-answer reconciliations: the engine recomputed beside the numbers five papers print, and the tests of the explanations
the committed artifacts give for the misses.

    python manuscripts/reconciliation-against-reference-engines/experiments/exp_printed.py [--out results_printed.json]

What it does, all from the committed documents ``data/derived/C04/published.json``, ``data/derived/C05/ldp-published.json``,
``sp-2010.json`` and ``sp-2011.json`` and the engine ``riskvalidation`` 1.1.0:

1. recomputes the printed cells of Pluto and Tasche (2005) Tables 1 to 12, Tasche (2013) Tables 5 to 9, Schuermann and Hanson
   (2004) Table 5 (the three sources whose inputs are committed) and reads Israel, Rosenthal and Wei (2001), Engelmann (2024) and
   Pluto and Tasche Tables 13 and 14 as the artifacts record them;
2. applies the digit rule, agreement within half a unit of the last printed digit, and bins every gap by its size in units of the
   last printed digit;
3. sweeps the tolerance (half, one, two and five units) to show how the share of agreeing numbers depends on the rule;
4. tests the explanation of the misses of Tables 11 and 12 (the paper scaled its own rounded bounds of Tables 4 and 8) by scaling
   the printed bounds and comparing with the print, and the explanation of the Table 4 miss at 75 % (the paper's 0.65 is the bound
   at 76.3 %);
5. recomputes the printed numbers of the Appendix of Hull and White (2012) with the engine and with a plain bisection.

Everything is deterministic: no random number is drawn.
"""
from __future__ import annotations

import argparse
import math
import pathlib
from fractions import Fraction

import numpy as np

import common as cm

from riskvalidation.ccr import cva as cv
from riskvalidation.engines import low_default as ldp
from riskvalidation.engines import pd_curve as pc
from riskvalidation.transitions import intervals

HERE = pathlib.Path(__file__).resolve().parent
SLACK = 1e-9


def decimals_of(x: float) -> int:
    """The number of decimals a printed number carries (from its shortest representation)."""
    s = repr(float(x))
    if "e" in s:
        mant, exp = s.split("e")
        return max(0, (len(mant.split(".")[1]) if "." in mant else 0) - int(exp))
    return len(s.split(".")[1].rstrip("0")) if "." in s else 0


def unit_gap(recomputed: float, printed: float, decimals: int) -> float:
    """The absolute gap in units of the last printed digit."""
    return abs(recomputed - printed) / 10.0 ** (-decimals)


def agrees(recomputed: float, printed: float, decimals: int, mult: float = 0.5) -> bool:
    return bool(abs(recomputed - printed) <= mult * 10.0 ** (-decimals) + SLACK)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "results_printed.json"))
    args = ap.parse_args()

    ldp_doc = cm.derived("C05/ldp-published.json")["outputs"]
    pub = cm.derived("C04/published.json")["outputs"]
    tasche = {y: cm.derived(f"C05/sp-{y}.json")["outputs"] for y in (2010, 2011)}

    # records: (source, key, printed, recomputed, decimals, kind)
    recs: list[tuple[str, str, float, float, int, str]] = []

    # ------------------------------------------------------------------ Pluto and Tasche 2005, Tables 1 to 12
    obligors, few, zero = tuple(ldp_doc["obligors"]), tuple(ldp_doc["defaults"]), (0, 0, 0)
    gammas, rho = ldp_doc["gammas"], ldp_doc["rho"]
    ours: dict[tuple, float] = {}
    scaled_tables = ((9, 0.0, "central_tendency"), (10, rho, "central_tendency"), (11, 0.0, "upper_bound"), (12, rho, "upper_bound"))
    for g in gammas:
        iz, i_f = ldp.most_prudent_pd(obligors, zero, g)["pd"], ldp.most_prudent_pd(obligors, few, g)["pd"]
        cz, cf = ldp.most_prudent_pd(obligors, zero, g, rho)["pd"], ldp.most_prudent_pd(obligors, few, g, rho)["pd"]
        for j, row in enumerate(("pa", "pb", "pc")):
            ours[(1 + j, row, g)], ours[(4 + j, row, g)] = 100 * iz[j], 100 * i_f[j]
            ours[(7, row, g)], ours[(8, row, g)] = 100 * cz[j], 100 * cf[j]
        for table, r, target in scaled_tables:
            sc = ldp.most_prudent_pd_scaled(obligors, few, g, r, target=target)
            ours[(table, "k", g)] = sc["k"]
            for j, row in enumerate(("pa", "pb", "pc")):
                ours[(table, row + ",scaled", g)] = 100 * sc["pd"][j]
    cells12 = [c for c in ldp_doc["golden"]["cells"] if c["table"] <= 12]
    printed12 = {(c["table"], c["row"], c["gamma"]): c["printed"] for c in cells12}
    assert len(printed12) == len(ours) == 168
    for k in sorted(printed12, key=str):
        recs.append(("Pluto and Tasche (2005), Tables 1 to 12", f"T{k[0]} {k[1]} g={k[2]}", printed12[k], ours[k], 2, "recomputed"))

    # ------------------------------------------------------------------ Tasche 2013
    base = tasche[2010]
    survival0 = np.array(base["profile0"]) * (1 - np.array(base["default_rate0"]))
    survival0 = survival0 / survival0.sum()
    start = pc.qmm(base["profile0"], base["pd0"], base["ar0"], survival_profile=list(survival0))
    curve0 = np.array(start["pd_curve"])
    g0 = base["golden"]
    pairs = [("Tasche (2013), Table 5", 100 * curve0, [c["printed"] for c in g0["table5"]], 3),
             ("Tasche (2013), Table 6", 100 * np.array(pc.implied_default_profile(curve0, base["profile0"])), [c["printed"] for c in g0["table6"]], 4),
             ("Tasche (2013), Table 9, 2009", np.array(pc.likelihood_ratio(curve0, start["pd"])), [c["printed"] for c in g0["table9_2009"]], 2)]
    for name, o, p, d in pairs:
        for i, (oo, pp) in enumerate(zip(o, p, strict=True)):
            recs.append((name, f"grade {i + 1}", float(pp), float(oo), d, "recomputed"))
    for year, o in tasche.items():
        p1, pd1, pd0 = o["profile1"], o["pd1"], start["pd"]
        dp0 = pc.implied_default_profile(curve0, o["profile0"])
        sv0 = pc.implied_survival_profile(curve0, o["profile0"])
        case1 = {"A1-idp": pc.invariant_default_profile(o["default_profile0"], p1, pd1), "A2-iar": pc.invariant_accuracy_ratio(p1, pd1, o["ar0"]),
                 "A3-spd": pc.scaled_pds(curve0, p1, pd1), "A4-slr": pc.scaled_likelihood_ratio(curve0, pd0, p1, pd1)}
        for a, r in case1.items():
            for i, (oo, pp) in enumerate(zip(100 * np.array(r["pd_curve"]), [c["printed"] for c in o["golden"]["table7"][a]], strict=True)):
                recs.append((f"Tasche (2013), Table 7, {year}", f"{a} grade {i + 1}", float(pp), float(oo), 4, "recomputed"))
        ls = pc.invariant_conditional_profiles(dp0, sv0, p1, fit="least_squares")
        lc = pc.invariant_conditional_profiles(dp0, sv0, p1, fit="least_chi2")
        unchanged = pc.invariant_pd_curve(curve0, p1)["pd_curve"]
        rk = pc.invariant_likelihood_ratio(curve0, pd0, profile_1=p1)
        case3 = [pc.unconditional_pd(unchanged, p1), ls["pd"], lc["pd"], rk["pd"]]
        for i, (oo, c) in enumerate(zip(100 * np.array(case3), o["golden"]["table8"], strict=True)):
            recs.append((f"Tasche (2013), Table 8, {year}", f"case {i + 1}", float(c["printed_pct"]), float(oo), 2, "recomputed"))

    # ------------------------------------------------------------------ Schuermann and Hanson 2004
    sr = pub["sr190"]
    for row in sr["rows"]:
        fn = intervals.pd_wald if row["interval"] == "wald" else intervals.pd_agresti_coull
        res = fn(sr["defaults"], sr["n"], level=0.95, rho=row["rho"])
        for key, p in zip(("lower", "upper", "length"), row["printed"], strict=True):
            recs.append(("Schuermann and Hanson (2004), Table 5", f"{row['interval']} rho={row['rho']} {key}", float(p), float(res[key]), 6, "recomputed"))

    # ------------------------------------------------------------------ read as recorded
    for r in pub["irw"]["rows"]:
        recs.append(("Israel, Rosenthal and Wei (2001), L1 distances", f"{r['matrix']} {r['method']}", r["printed"], r["recomputed"],
                     decimals_of(r["printed"]), "read"))
    eng = pub["engelmann"]
    for i, (p, r, d) in enumerate(zip(eng["w_ttc"]["printed"], eng["w_ttc"]["recomputed"], eng["w_ttc"]["decimals"], strict=True)):
        recs.append(("Engelmann (2024), TTC portfolio and PDs", f"w_ttc {i}", p, r, int(d), "read"))
    recs.append(("Engelmann (2024), TTC portfolio and PDs", "ttc_pd", eng["ttc_pd"]["printed"], eng["ttc_pd"]["recomputed"], int(eng["ttc_pd"]["decimals"]), "read"))
    for q in eng["portfolios"]:
        if q["pd0"]["check"] == "printed digits":
            recs.append(("Engelmann (2024), TTC portfolio and PDs", q["name"], q["pd0"]["printed"], q["pd0"]["recomputed"], int(q["pd0"]["decimals"]), "read"))
    for c in ldp_doc["golden"]["cells"]:
        if c["table"] >= 13:
            recs.append(("Pluto and Tasche (2005), Tables 13 and 14", f"T{c['table']} {c['row']} g={c['gamma']}", c["printed"], c["ours"], 2, "read"))

    # ------------------------------------------------------------------ the tally
    sources: list[dict] = []
    for name in dict.fromkeys(r[0] for r in recs):
        rows = [r for r in recs if r[0] == name]
        ug = [unit_gap(r[3], r[2], r[4]) for r in rows]
        sources.append({"source": name, "kind": rows[0][5], "n": len(rows), "agree": sum(agrees(r[3], r[2], r[4]) for r in rows),
                        "max_unit_gap": max(ug), "max_abs_gap": max(abs(r[3] - r[2]) for r in rows)})
    total = sum(s["n"] for s in sources)
    agree_total = sum(s["agree"] for s in sources)
    rec_n = sum(s["n"] for s in sources if s["kind"] == "recomputed")
    rec_agree = sum(s["agree"] for s in sources if s["kind"] == "recomputed")

    # the notebook counts the Table 13 and 14 cells by the artifact's rounded gap: reproduce the tally of the SDD
    # (413 numbers, 296 agreeing) under the hypothesis that it leaves out Tables 8 and 9 of Tasche (2013)
    leave = {"Tasche (2013), Table 9, 2009", "Tasche (2013), Table 8, 2010", "Tasche (2013), Table 8, 2011"}
    sdd_n = sum(s["n"] for s in sources if s["source"] not in leave)
    sdd_agree = sum(s["agree"] for s in sources if s["source"] not in leave)

    bins = {"half": 0, "to_one": 0, "to_two": 0, "beyond_two": 0}
    bins_rec = dict(bins)
    for r in recs:
        u = unit_gap(r[3], r[2], r[4])
        k = "half" if u <= 0.5 + SLACK * 10.0 ** r[4] else "to_one" if u <= 1.0 + 1e-6 else "to_two" if u <= 2.0 + 1e-6 else "beyond_two"
        bins[k] += 1
        if r[5] == "recomputed":
            bins_rec[k] += 1
    sweep = [{"units": m, "agree": sum(agrees(r[3], r[2], r[4], m) for r in recs), "agree_recomputed": sum(agrees(r[3], r[2], r[4], m) for r in recs if r[5] == "recomputed")}
             for m in (0.5, 1.0, 2.0, 5.0)]

    # the misses of the recomputed sources, listed with their gap in units
    misses = [{"source": r[0], "key": r[1], "printed": r[2], "recomputed": r[3], "decimals": r[4], "unit_gap": unit_gap(r[3], r[2], r[4])}
              for r in recs if r[5] == "recomputed" and not agrees(r[3], r[2], r[4])]
    misses.sort(key=lambda m: -m["unit_gap"])

    # ------------------------------------------------------------------ the explanation of Tables 9 to 12 (scaled bounds)
    def printed_row(table: int, row: str, g: float) -> float:
        return printed12[(table, row, g)]

    explain = {}
    for table, src_table, kind in ((9, 4, "central_tendency"), (10, 8, "central_tendency"), (11, 4, "upper_bound"), (12, 8, "upper_bound")):
        n_cell = agree_exact = agree_printed = 0
        worst_exact = worst_printed = 0.0
        for g in gammas:
            if src_table == 4:   # the uncorrelated bounds are printed grade by grade in Tables 4, 5 and 6
                raw_printed = [printed_row(4 + j, r, g) / 100.0 for j, r in enumerate(("pa", "pb", "pc"))]
            else:                # the correlated bounds of the three grades are the rows of Table 8
                raw_printed = [printed_row(8, r, g) / 100.0 for r in ("pa", "pb", "pc")]
            level = (sum(few) / sum(obligors)) if kind == "central_tendency" else raw_printed[0]
            sc = ldp.scale_bounds(raw_printed, obligors, level)
            cells = [("k", sc["k"])] + [(r + ",scaled", 100 * sc["pd"][j]) for j, r in enumerate(("pa", "pb", "pc"))]
            for row, val in cells:
                p = printed_row(table, row, g)
                n_cell += 1
                agree_exact += agrees(ours[(table, row, g)], p, 2)
                agree_printed += agrees(val, p, 2)
                worst_exact = max(worst_exact, unit_gap(ours[(table, row, g)], p, 2))
                worst_printed = max(worst_printed, unit_gap(val, p, 2))
        explain[f"table{table}"] = {"cells": n_cell, "agree_with_exact_bounds": agree_exact, "agree_with_printed_bounds": agree_printed,
                                    "worst_unit_gap_exact": worst_exact, "worst_unit_gap_printed": worst_printed}

    # Table 4 at 75 %: the bound at 76.3 %
    at763 = ldp.most_prudent_pd(obligors, few, 0.763)["pd"][0] * 100
    at75 = ldp.most_prudent_pd(obligors, few, 0.75)["pd"][0] * 100
    # a search for the level whose bound prints 0.65: the smallest and largest level whose rounded bound is 0.65
    lo = next(g for g in np.arange(0.74, 0.80, 0.0001) if round(ldp.most_prudent_pd(obligors, few, float(g))["pd"][0] * 100, 2) == 0.65)
    hi = max(g for g in np.arange(0.74, 0.80, 0.0001) if round(ldp.most_prudent_pd(obligors, few, float(g))["pd"][0] * 100, 2) == 0.65)

    # ------------------------------------------------------------------ Hull and White (2012), Appendix
    w = np.array([[100.0, 100.0], [200.0, 300.0], [300.0, 400.0]])
    target = np.exp(-0.01 * np.array([0.5, 1.0]) / (1.0 - 0.0))
    dt = np.array([0.5, 0.5])
    a, h = cv.wwr_calibrate_a(w, target, dt, 0.01)

    def bisect_a(col, cum, b, tgt, dtk):
        lo_, hi_ = -40.0, 10.0
        for _ in range(300):
            mid = 0.5 * (lo_ + hi_)
            avg = sum(math.exp(-(c + math.exp(mid + b * x) * dtk)) for x, c in zip(col, cum, strict=True)) / len(col)
            lo_, hi_ = (mid, hi_) if avg > tgt else (lo_, mid)
        return 0.5 * (lo_ + hi_)

    a1 = bisect_a(w[:, 0], [0.0] * 3, 0.01, target[0], 0.5)
    cum1 = [float(x) * 0.5 for x in h[:, 0]]
    a2 = bisect_a(w[:, 1], cum1, 0.01, target[1], 0.5)
    printed_ww = [("a1", -6.9128, a[0], 4), ("a2", -7.8509, a[1], 4)]
    printed_ww += [(f"h1[{i}]", p, h[i, 0], 5) for i, p in enumerate((0.00270, 0.00735, 0.01998))]
    printed_ww += [(f"h2[{i}]", p, h[i, 1], 5) for i, p in enumerate((0.00106, 0.00782, 0.02126))]
    b2 = cv.b_from_two_points(3.0, 0.05, 20.0, 0.10)
    printed_ww.append(("b from two points", 0.0408, b2, 4))
    wrong_way = {"cells": [{"key": k, "printed": p, "recomputed": float(r), "decimals": d, "unit_gap": unit_gap(float(r), p, d), "agrees": agrees(float(r), p, d)}
                           for k, p, r, d in printed_ww],
                 "bisection_gap_a1": float(abs(a[0] - a1)), "bisection_gap_a2": float(abs(a[1] - a2)),
                 "recomputed_a": [float(a[0]), float(a[1])],
                 "max_calibration_error": float(np.max(np.abs(np.exp(-np.cumsum(h * dt[None, :], axis=1)).mean(axis=0) - target)))}
    wrong_way["n"] = len(printed_ww)
    wrong_way["agree"] = sum(c["agrees"] for c in wrong_way["cells"])

    # ------------------------------------------------------------------ the explanation of every miss
    rounded_ok: set[tuple] = set()      # Pluto-Tasche cells of Tables 9 to 12 that miss with the exact bounds and agree with the printed ones
    for table, src_table, kind in ((9, 4, "central_tendency"), (10, 8, "central_tendency"), (11, 4, "upper_bound"), (12, 8, "upper_bound")):
        for g in gammas:
            if src_table == 4:
                raw_printed = [printed_row(4 + j, r, g) / 100.0 for j, r in enumerate(("pa", "pb", "pc"))]
            else:
                raw_printed = [printed_row(8, r, g) / 100.0 for r in ("pa", "pb", "pc")]
            level = (sum(few) / sum(obligors)) if kind == "central_tendency" else raw_printed[0]
            sc = ldp.scale_bounds(raw_printed, obligors, level)
            for row, val in [("k", sc["k"])] + [(r + ",scaled", 100 * sc["pd"][j]) for j, r in enumerate(("pa", "pb", "pc"))]:
                if not agrees(ours[(table, row, g)], printed_row(table, row, g), 2) and agrees(val, printed_row(table, row, g), 2):
                    rounded_ok.add((table, row, g))
    tol_formula = {"Tasche (2013), Table 5": lambda pr: 0.001 + 1e-9, "Tasche (2013), Table 6": lambda pr: 1e-4 + 1e-4 * pr + 1e-9,
                   "Tasche (2013), Table 9, 2009": lambda pr: 0.005 + 0.002 * pr}

    def category(rec: tuple) -> str:
        src, key, pr, rc, dec, kind = rec
        if src.startswith("Pluto and Tasche (2005), Tables 1 to 12"):
            table = int(key[1:].split()[0])
            row = key.split()[1]
            g = float(key.split("g=")[1])
            if (table, row, g) in rounded_ok:
                return "rounded printed inputs (tested)"
            if table == 4 and abs(g - 0.75) < 1e-9:
                return "confidence level of the print (tested)"
            if table == 8 and pr >= rc - 1e-9 and unit_gap(rc, pr, dec) <= 1.0 + 1e-6:
                return "print at or above the exact bound (recorded)"
            return "no explanation; within one unit" if unit_gap(rc, pr, dec) <= 1.0 + 1e-6 else "no explanation; beyond one unit"
        if src.startswith("Pluto and Tasche (2005), Tables 13"):
            return "Monte Carlo print (recorded)"
        if src.startswith("Israel"):
            return "printed generator (recorded)"
        if src.startswith("Tasche (2013), Table 7") or src.startswith("Tasche (2013), Table 8"):
            tol = 1e-4 + 1e-4 * pr if "Table 7" in src else 0.01
            return "documented tolerance (recorded)" if abs(rc - pr) <= tol + 1e-9 else "no explanation; beyond one unit"
        for name, f in tol_formula.items():
            if src.startswith(name):
                return "documented tolerance (recorded)" if abs(rc - pr) <= f(pr) else "no explanation; beyond one unit"
        return "no explanation; beyond one unit"

    miss_all = [r for r in recs if not agrees(r[3], r[2], r[4])]
    cats: dict[str, int] = {}
    for r in miss_all:
        cats[category(r)] = cats.get(category(r), 0) + 1
    by_group: dict[str, dict] = {}
    for r in recs:
        grp = r[0] if not r[0].startswith("Pluto and Tasche (2005), Tables 1 to") else f"Pluto and Tasche (2005), Table {r[1].split()[0][1:]}"
        e = by_group.setdefault(grp, {"n": 0, "agree": 0, "max_unit_gap": 0.0})
        e["n"] += 1
        e["agree"] += agrees(r[3], r[2], r[4])
        e["max_unit_gap"] = max(e["max_unit_gap"], unit_gap(r[3], r[2], r[4]))

    unexplained = [{"source": r[0], "key": r[1], "printed": r[2], "recomputed": r[3], "decimals": r[4], "unit_gap": unit_gap(r[3], r[2], r[4])}
                   for r in miss_all if category(r).startswith("no explanation")]
    unit_gaps: dict[str, list[float]] = {}
    for r in recs:
        unit_gaps.setdefault(r[0], []).append(round(unit_gap(r[3], r[2], r[4]), 4))

    out = {"unexplained": unexplained, "unit_gaps": unit_gaps, "engine": __import__("importlib.metadata", fromlist=["version"]).version("riskvalidation"), "sources": sources,
           "totals": {"n": total, "agree": agree_total, "recomputed_n": rec_n, "recomputed_agree": rec_agree,
                      "read_n": total - rec_n, "read_agree": agree_total - rec_agree},
           "sdd_statement": {"n": 413, "agree": 296}, "without_tasche_tables_8_and_9": {"n": sdd_n, "agree": sdd_agree},
           "unit_gap_bins": bins, "unit_gap_bins_recomputed": bins_rec, "tolerance_sweep": sweep, "misses": [{"source": r[0], "key": r[1], "printed": r[2], "recomputed": r[3], "decimals": r[4], "unit_gap": unit_gap(r[3], r[2], r[4]), "explanation": category(r)}
                      for r in sorted(miss_all, key=lambda r: -unit_gap(r[3], r[2], r[4]))], "n_misses_recomputed": len(misses),
           "explain_scaled": explain, "miss_categories": cats, "n_misses": len(miss_all), "by_group": by_group,
           "table4_level": {"bound_at_0_75": at75, "bound_at_0_763": at763, "level_range_printing_0_65": [float(lo), float(hi)]},
           "wrong_way_appendix": wrong_way}
    cm.write(pathlib.Path(args.out), out)
    print(f"{total} printed numbers, {agree_total} agree to the printed digit ({rec_n} recomputed, {rec_agree} agree)")
    for s in sources:
        print(f"  {s['source']:50s} {s['kind']:10s} {s['n']:4d} {s['agree']:4d} max {s['max_unit_gap']:.2f} units")
    print("bins", bins, "without T8,T9:", sdd_n, sdd_agree)
    print("sweep", sweep)
    print("explain", explain)
    print("T4", at75, at763, lo, hi)
    print("ww", wrong_way["agree"], wrong_way["n"], [c for c in wrong_way["cells"] if not c["agrees"]])


if __name__ == "__main__":
    main()
