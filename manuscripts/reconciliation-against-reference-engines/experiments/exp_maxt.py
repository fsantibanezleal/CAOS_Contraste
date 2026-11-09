"""A dependence-aware simultaneous bound for the exposure reconciliation: the maximum-T rule, against the rules of ``exp_criterion.py``.

    python manuscripts/reconciliation-against-reference-engines/experiments/exp_maxt.py [--reps 400] [--workers 12]
        [--out results_maxt.json]

The refinement of the manuscript bounds the 35 standardised differences with the Sidak constant, which is exact only for
independent comparisons and conservative for the strongly dependent dates of one simulation. The published answer to simultaneous
inference on correlated statistics is the single-step maximum-T bound (Westfall and Young 1993; Hothorn, Bretz and Westfall 2008):
the critical value is the 95 % point of the largest absolute value of a Gaussian vector with the covariance of the statistics.

This script repeats the paired runs of ``exp_criterion.py`` with the same seeds (the engine under test has seed 1,000,000 + 2r, the
reference 1,000,000 + 2r + 1) on the null and on four planted conditions (volatility +2 % and +5 %, mean reversion +50 %, the
measure error), for the single swap and the netting set, and keeps for each cell the largest of the 35 absolute standardised
differences with the product's errors and with pair-aware errors, and for the null the whole vector of 35. Two rules are added to
the two it reproduces for checking (the product's rule and the pair-aware rule at the bound 3.18):

* maxT: the largest |z| of the product's errors against the 95 % point of max |N(0, S)|, S the covariance of the 35 differences
  under the null;
* pair+maxT: the same for the pair-aware errors.

S is estimated on the null repetitions of the other half of the repetitions (even repetitions are judged with the covariance of the
odd ones and the reverse), so no repetition is judged with a bound that it helped to set. The covariance comes from repetitions of the
engine against itself, which a validation function can run as pilots; it is not estimated from the single pair of runs of a
reconciliation, and the manuscript says so. The 95 % point is taken from 400,000 Gaussian draws with seed 20261107.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import pathlib
import time

import numpy as np

import common as cm
import exp_criterion as ec

HERE = pathlib.Path(__file__).resolve().parent
KEEP = ("null", "sigma+2%", "sigma+5%", "a+50%", "measure")
CONDS = [c for c in ec.CONDITIONS if c[0] in KEEP]
GAUSS_DRAWS = 400_000
GAUSS_SEED = 20261107


def repetition(r: int) -> dict:
    """The paired runs of repetition r of ``exp_criterion.repetition`` on the conditions kept; returns the 35 statistics."""
    if not ec._STATE:
        ec._init()
    inp, surv = ec._STATE["inp"], ec._STATE["surv"]
    report = inp.report
    pd = surv[:-1] - surv[1:]
    seed_a, seed_b = 1_000_000 + 2 * r, 1_000_000 + 2 * r + 1
    sim_b = inp.simulate(seed_b, n_paths=10_000)
    ref = {v: ec.summarise(sim_b, ec.MEMBERS[v], report, pd) for v in ec.VARIANTS}
    del sim_b
    out: dict = {"r": r, "cells": {}}
    sim_null = None
    for name, spec in CONDS:
        if "measure" in spec:
            sim = sim_null
        else:
            sim = inp.simulate(seed_a, n_paths=inp.paths, a=None if "a" not in spec else inp.a * spec["a"],
                               sigma=None if "sigma" not in spec else inp.sigma * spec["sigma"])
            if name == "null":
                sim_null = sim
        for v in ec.VARIANTS:
            a = ec.summarise(sim, ec.MEMBERS[v], report, pd)
            if "measure" in spec:
                from riskvalidation.ccr import exposure as ex

                ee_wrong = a["ee"] * a["p0r"]
                eepe_wrong = float(ex.effective_epe(report, ex.effective_ee(ee_wrong)))
                a = {**a, "ee": ee_wrong, "se": a["se"] * a["p0r"], "se_pair": a["se_pair"] * a["p0r"], "eepe": eepe_wrong,
                     "eepe_se": a["eepe_se"] * eepe_wrong / a["eepe"]}
            c = ec.compare(a, ref[v])
            vec = np.concatenate([c["z"], [c["ze"], c["zc"]]])
            vec_pair = np.concatenate([c["z_pair"], [c["ze_pair"], c["zc_pair"]]])
            cell = {"max": float(np.abs(vec).max()), "max_pair": float(np.abs(vec_pair).max())}
            if name == "null":
                cell["z35"] = [round(float(x), 5) for x in vec]
                cell["z35_pair"] = [round(float(x), 5) for x in vec_pair]
            out["cells"][f"{v}|{name}"] = cell
        if name != "null" and "measure" not in spec:
            del sim
    return out


def max_t_bound(sample: np.ndarray, level: float = 0.95) -> float:
    """The ``level`` point of max |N(0, S)| with S the covariance of the rows of ``sample`` (repetitions x statistics)."""
    cov = np.cov(sample, rowvar=False)
    rng = np.random.default_rng(GAUSS_SEED)
    draws = rng.multivariate_normal(np.zeros(cov.shape[0]), cov, size=GAUSS_DRAWS, method="eigh")
    return float(np.quantile(np.abs(draws).max(axis=1), level))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=400)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--out", default=str(HERE / "results_maxt.json"))
    args = ap.parse_args()
    t0 = time.perf_counter()
    with cf.ProcessPoolExecutor(max_workers=args.workers) as pool:
        reps = list(pool.map(repetition, range(args.reps), chunksize=1))
    seconds = time.perf_counter() - t0
    R = len(reps)
    parity = np.arange(R) % 2
    crit = json_load(HERE / "results_criterion.json")
    bounds: dict = {}
    table: dict = {}
    for v in ec.VARIANTS:
        null = {kind: np.array([r["cells"][f"{v}|null"][key] for r in reps]) for kind, key in (("product", "z35"), ("pair", "z35_pair"))}
        # the bound for the repetitions of one parity comes from the null repetitions of the other parity
        c_for = {kind: {p: max_t_bound(null[kind][parity != p]) for p in (0, 1)} for kind in null}
        bounds[v] = {kind: {"even_judged_with_odd": c_for[kind][0], "odd_judged_with_even": c_for[kind][1]} for kind in null}
        for name, _ in CONDS:
            key = f"{v}|{name}"
            mx = np.array([r["cells"][key]["max"] for r in reps])
            mp = np.array([r["cells"][key]["max_pair"] for r in reps])
            bp = np.array([c_for["product"][int(p)] for p in parity])
            bq = np.array([c_for["pair"][int(p)] for p in parity])
            decisions = {"product": mx > 2.0, "pair+sidak": mp > ec.C_SIDAK, "maxT": mx > bp, "pair+maxT": mp > bq}
            cell = {}
            for rule, flag in decisions.items():
                k = int(flag.sum())
                lo, hi = cm.wilson(k, R)
                cell[rule] = {"rejected": k, "rate": k / R, "lo": lo, "hi": hi}
            table[key] = cell
    # the product's rule and the pair-aware rule at 3.18 are decided in exp_criterion.py: the repeat must agree with it exactly
    reproduces = all(table[k][rule]["rejected"] == crit["table"][k][rule]["rejected"] for k in table for rule in ("product", "pair+sidak"))
    out = {"reps": R, "seed_base": 1_000_000, "conditions": [c[0] for c in CONDS], "variants": list(ec.VARIANTS), "rules": ["product", "pair+sidak", "maxT", "pair+maxT"],
           "gaussian_draws": GAUSS_DRAWS, "gaussian_seed": GAUSS_SEED, "bounds": bounds, "table": table,
           "reproduces_criterion_counts": bool(reproduces), "seconds": seconds}
    cm.write(pathlib.Path(args.out), out)
    for key, cell in table.items():
        print(key.ljust(26), "  ".join(f"{rule}:{cell[rule]['rate']:.3f}" for rule in out["rules"]))
    print("bounds", {v: {k: [round(x, 3) for x in b.values()] for k, b in bounds[v].items()} for v in bounds})
    print("reproduces the committed counts of the product's rule and the pair-aware rule:", reproduces, f"{seconds:.0f}s")


def json_load(path: pathlib.Path) -> dict:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
