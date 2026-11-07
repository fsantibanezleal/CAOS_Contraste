"""The size and power of the exposure reconciliation rule, measured with the engine against a second run of the engine.

    python manuscripts/reconciliation-against-reference-engines/experiments/exp_criterion.py [--reps 300] [--workers 10]
        [--out results_criterion.json]

The product accepts the Hull-White exposure against ORE when the difference of the two expected-exposure profiles is within two
combined Monte Carlo standard errors at each of the 33 report dates and the EEPE and the CVA are within two combined errors
(``pipeline.cases.c12.reconcile.block``). The rule has a size (the probability of rejecting two runs of the same model) and a
power (the probability of rejecting a model with a defect), neither of which the committed reconciliation measures. This
script measures both, with the reference engine replaced by a second, independently seeded run of the engine at ORE's sample
count, so the truth is known: no difference in the null, a planted defect otherwise.

Per repetition r (r = 0 to reps - 1): the reference B is a Hull-White run of 10,000 paths (the antithetic pairs of the
engine) with seed 1,000,000 + 2r + 1 at the calibrated parameters; the engine A is a run of 20,000 paths (the committed path
count) with seed 1,000,000 + 2r under each condition: the calibrated parameters (null), the volatility raised by 2, 5 and 10 %,
the mean reversion raised by 50 and 100 %, and the measure error that reports the discounted expected exposure where the
forward-measure one is meant (the convexity gap that the document's measure note describes; the EEPE follows from the wrong profile, the CVA does not). Both variants of the
uncollateralised book are read from the same runs: the single swap (SW-1) and the netting set (four swaps).

Rules compared, each a decision per repetition and condition (reject = the reconciliation fails):

* product: all 33 |z| <= 2 and |z_EEPE| <= 2 and |z_CVA| <= 2 (standard errors treating paths as independent);
* dates: the 33 |z| <= 2 alone;  eepe and cva: the scalar |z| <= 2 alone;
* sidak: the product rule at the bound c = 3.18 that keeps the family size at 5 % for 35 independent comparisons;
* pair: the product rule with pair-aware standard errors (the pairs i and i + P/2 averaged before the variance is taken);
* pair+sidak: both changes;
* fixed 1 %, 2 % and 5 %: a tolerance on max_k |difference_k| / peak EE without any standard error.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import math
import pathlib
import time

import numpy as np

import common as cm

HERE = pathlib.Path(__file__).resolve().parent
LGD = 0.6
C_SIDAK = 3.1816376084204343        # exp_committed.sidak_bound(35)
CONDITIONS = [("null", {}), ("sigma+2%", {"sigma": 1.02}), ("sigma+5%", {"sigma": 1.05}), ("sigma+10%", {"sigma": 1.10}),
              ("a+50%", {"a": 1.5}), ("a+100%", {"a": 2.0}), ("measure", {"measure": True})]
VARIANTS = ("single-swap", "netting-set")
MEMBERS = {"single-swap": [0], "netting-set": [0, 1, 2, 3]}

_STATE: dict = {}


def _init() -> None:
    inp = cm.C12Inputs("netting-set")
    doc = cm.derived("C12/netting-set.json")["outputs"]["cva_dva"]["buckets"]
    surv = np.concatenate([[1.0], [b["survival"] for b in doc]])
    _STATE["inp"] = inp
    _STATE["surv"] = surv


def summarise(sim, members: list[int], report: np.ndarray, pd: np.ndarray) -> dict:
    """The expected exposure, its two standard errors, the EEPE with its batch error, and the CVA with its two errors."""
    from pipeline.cases.c12 import exposure as xp

    e = xp.uncollateralised(sim, members)
    num = sim.numeraire[:, sim.index(report)]
    p0r = np.asarray(sim.p0(report), dtype=float)
    mx = xp.measures(e.x, num, p0r, report, None, 0)
    pos = e.x / num                                     # discounted positive exposure paths
    half = pos.shape[0] // 2
    pair = 0.5 * (pos[:half] + pos[half:])
    se_pair = pair.std(axis=0, ddof=1) / math.sqrt(half) / p0r
    cva_paths = LGD * (pos @ pd)
    cva_pair = 0.5 * (cva_paths[:half] + cva_paths[half:])
    return {"ee": mx["ee"], "se": mx["ee_se"], "se_pair": se_pair, "eepe": float(mx["eepe"]), "eepe_se": float(mx["eepe_se"]),
            "cva": float(cva_paths.mean()), "cva_se": float(cva_paths.std(ddof=1) / math.sqrt(cva_paths.size)),
            "cva_se_pair": float(cva_pair.std(ddof=1) / math.sqrt(half)), "p0r": p0r}


def compare(a: dict, b: dict) -> dict:
    """The decision statistics of one comparison (b is the reference, as ORE is in the product): z = (B - A) / combined error."""
    out = {}
    for tag, sa, sb in (("", a["se"], b["se"]), ("_pair", a["se_pair"], b["se_pair"])):
        comb = np.hypot(sa, sb)
        z = (b["ee"] - a["ee"]) / comb
        ze = (b["eepe"] - a["eepe"]) / math.hypot(a["eepe_se"], b["eepe_se"])
        cs_a, cs_b = (a["cva_se"], b["cva_se"]) if tag == "" else (a["cva_se_pair"], b["cva_se_pair"])
        zc = (b["cva"] - a["cva"]) / math.hypot(cs_a, cs_b)
        out["z" + tag] = z
        out["ze" + tag], out["zc" + tag] = ze, zc
    peak = float(np.max(b["ee"]))
    out["max_rel_diff"] = float(np.max(np.abs(b["ee"] - a["ee"])) / peak)
    out["eepe_rel_diff"] = float((b["eepe"] - a["eepe"]) / b["eepe"])
    out["cva_rel_diff"] = float((b["cva"] - a["cva"]) / b["cva"])
    return out


def decisions(c: dict) -> dict[str, bool]:
    """True = the rule rejects the agreement."""
    zd, ze, zc = np.abs(c["z"]), abs(c["ze"]), abs(c["zc"])
    zdp, zep, zcp = np.abs(c["z_pair"]), abs(c["ze_pair"]), abs(c["zc_pair"])
    prod = bool(zd.max() > 2 or ze > 2 or zc > 2)
    return {"product": prod, "dates": bool(zd.max() > 2), "eepe": bool(ze > 2), "cva": bool(zc > 2),
            "sidak": bool(zd.max() > C_SIDAK or ze > C_SIDAK or zc > C_SIDAK),
            "pair": bool(zdp.max() > 2 or zep > 2 or zcp > 2),
            "pair+sidak": bool(zdp.max() > C_SIDAK or zep > C_SIDAK or zcp > C_SIDAK),
            "fixed 1%": bool(c["max_rel_diff"] > 0.01), "fixed 2%": bool(c["max_rel_diff"] > 0.02), "fixed 5%": bool(c["max_rel_diff"] > 0.05)}


def repetition(r: int) -> dict:
    if not _STATE:
        _init()
    inp, surv = _STATE["inp"], _STATE["surv"]
    report = inp.report
    pd = surv[:-1] - surv[1:]
    seed_a, seed_b = 1_000_000 + 2 * r, 1_000_000 + 2 * r + 1
    sim_b = inp.simulate(seed_b, n_paths=10_000)
    ref = {v: summarise(sim_b, MEMBERS[v], report, pd) for v in VARIANTS}
    del sim_b
    result: dict = {"r": r, "cells": {}}
    sim_null = None
    for name, spec in CONDITIONS:
        if "measure" in spec:
            sim = sim_null
        else:
            sim = inp.simulate(seed_a, n_paths=inp.paths, a=None if "a" not in spec else inp.a * spec["a"],
                               sigma=None if "sigma" not in spec else inp.sigma * spec["sigma"])
            if name == "null":
                sim_null = sim
        for v in VARIANTS:
            a = summarise(sim, MEMBERS[v], report, pd)
            if "measure" in spec:                        # the discounted EE where the forward-measure EE is meant
                from riskvalidation.ccr import exposure as ex

                ee_wrong = a["ee"] * a["p0r"]
                eepe_wrong = float(ex.effective_epe(report, ex.effective_ee(ee_wrong)))
                a = {**a, "ee": ee_wrong, "se": a["se"] * a["p0r"], "se_pair": a["se_pair"] * a["p0r"], "eepe": eepe_wrong,
                     "eepe_se": a["eepe_se"] * eepe_wrong / a["eepe"]}
            c = compare(a, ref[v])
            result["cells"][f"{v}|{name}"] = {"decisions": decisions(c), "max_abs_z": float(np.abs(c["z"]).max()), "max_abs_z_pair": float(np.abs(c["z_pair"]).max()),
                                              "ze": float(c["ze"]), "zc": float(c["zc"]), "max_rel_diff": c["max_rel_diff"], "eepe_rel_diff": c["eepe_rel_diff"],
                                              "cva_rel_diff": c["cva_rel_diff"],
                                              "z": [round(float(x), 4) for x in c["z"]] if name == "null" else None,
                                              "z_pair": [round(float(x), 4) for x in c["z_pair"]] if name == "null" else None}
        if name != "null" and "measure" not in spec:
            del sim
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=300)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--out", default=str(HERE / "results_criterion.json"))
    args = ap.parse_args()
    t0 = time.perf_counter()
    with cf.ProcessPoolExecutor(max_workers=args.workers) as pool:
        reps = list(pool.map(repetition, range(args.reps), chunksize=1))
    seconds = time.perf_counter() - t0
    rules = list(reps[0]["cells"]["single-swap|null"]["decisions"])
    table = {}
    for v in VARIANTS:
        for name, _ in CONDITIONS:
            key = f"{v}|{name}"
            cell = {}
            for rule in rules:
                k = sum(r["cells"][key]["decisions"][rule] for r in reps)
                lo, hi = cm.wilson(k, len(reps))
                cell[rule] = {"rejected": k, "rate": k / len(reps), "lo": lo, "hi": hi}
            cell["median_max_abs_z"] = float(np.median([r["cells"][key]["max_abs_z"] for r in reps]))
            cell["median_max_abs_z_pair"] = float(np.median([r["cells"][key]["max_abs_z_pair"] for r in reps]))
            cell["median_max_rel_diff"] = float(np.median([r["cells"][key]["max_rel_diff"] for r in reps]))
            cell["mean_eepe_rel_diff"] = float(np.mean([r["cells"][key]["eepe_rel_diff"] for r in reps]))
            table[key] = cell
    # the calibration of the standard error under the null: the standard deviation of z over repetitions at each date
    calib = {}
    for v in VARIANTS:
        key = f"{v}|null"
        z = np.array([r["cells"][key]["z"] for r in reps])
        zp = np.array([r["cells"][key]["z_pair"] for r in reps])
        active = np.abs(z).sum(axis=0) > 0
        calib[v] = {"sd_z_by_date": [round(float(x), 3) for x in z.std(axis=0, ddof=1)], "sd_z_pair_by_date": [round(float(x), 3) for x in zp.std(axis=0, ddof=1)],
                    "mean_z_by_date": [round(float(x), 3) for x in z.mean(axis=0)], "median_sd_z": float(np.median(z.std(axis=0, ddof=1)[active])),
                    "median_sd_z_pair": float(np.median(zp.std(axis=0, ddof=1)[active])), "z_null": z.round(3).tolist()[:150],
                    "mean_ze": float(np.mean([r["cells"][key]["ze"] for r in reps])), "sd_ze": float(np.std([r["cells"][key]["ze"] for r in reps], ddof=1)),
                    "mean_zc": float(np.mean([r["cells"][key]["zc"] for r in reps])), "sd_zc": float(np.std([r["cells"][key]["zc"] for r in reps], ddof=1))}
    out = {"reps": args.reps, "seed_base": 1_000_000, "paths_a": cm.C12Inputs("netting-set").paths, "paths_b": 10_000, "bound": 2.0, "sidak_bound": C_SIDAK,
           "conditions": [c[0] for c in CONDITIONS], "variants": list(VARIANTS), "rules": rules, "table": table, "calibration": calib, "seconds": seconds}
    cm.write(pathlib.Path(args.out), out)
    for key, cell in table.items():
        print(key.ljust(26), "  ".join(f"{rule}:{cell[rule]['rate']:.3f}" for rule in rules))
    print("sd z", {v: (calib[v]["median_sd_z"], calib[v]["median_sd_z_pair"]) for v in VARIANTS}, f"{seconds:.0f}s")


if __name__ == "__main__":
    main()
