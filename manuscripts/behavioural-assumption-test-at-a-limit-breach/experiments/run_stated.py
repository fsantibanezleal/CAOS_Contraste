"""Experiment 2: a stated behavioural parameter, with an assumption change planted at breach dates.

    python manuscripts/behavioural-assumption-test-at-a-limit-breach/experiments/run_stated.py [--per-block 800]

A history of 12 quarters has a breach chain (stationary prevalence ``p``, persistence 0.8), a stated parameter with changes that have nothing to do with
the breach (a rate ``lam`` per quarter), and, in the alternative arm, a lengthening at each breach date with probability ``pi_m`` (at least one). Both arms share
the breach chain and the innocent changes (paired). Every history has at least one breach after its first date. 5 blocks of ``--per-block`` histories per
cell; the seeds are ``[SEED, cell, block, history]``. Writes ``results_stated.json``.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import pathlib

import numpy as np

import core

HERE = pathlib.Path(__file__).resolve().parent
SEED = 7101
BLOCKS = 5
LAMS = (0.05, 0.10, 0.20)
PREVS = (0.10, 0.25, 0.50)
PI_M = 0.5
SWEEP_PI = (0.25, 0.5, 1.0)
BASE = (0.10, 0.25)
STATED_DETECTORS = ("engine", "any_change", "fisher", "mannwhitney", "welch")


def run_cell(cell: int, lam: float, prev: float, pi_m: float, per_block: int) -> dict:
    flags = {arm: {d: [0] * BLOCKS for d in STATED_DETECTORS} for arm in ("null", "alt")}
    raw = {arm: {d: [] for d in ("engine", "fisher", "mannwhitney", "welch", "any_change")} for arm in ("null", "alt")}
    n_breach, coincide_null = [], 0
    for blk in range(BLOCKS):
        for i in range(per_block):
            rng = np.random.default_rng([SEED, cell, blk, i])
            b = core.breach_chain(rng, core.T_DEFAULT, prev)
            draws = core.stated_draws(rng, core.T_DEFAULT, lam)
            plant = core.plant_dates(rng, b, pi_m)
            n_breach.append(int(b[1:].sum()))
            for arm, th in (("null", core.stated_history(draws, None)), ("alt", core.stated_history(draws, plant))):
                sc = core.scores(th, b)
                for d in STATED_DETECTORS:
                    flags[arm][d][blk] += int(core.flag(sc, d))
                raw[arm]["engine"].append(sc["engine_count"])
                raw[arm]["any_change"].append(sc["any_change"])
                for d in ("fisher", "mannwhitney", "welch"):
                    raw[arm][d].append(-sc[d + "_p"])
    n = per_block * BLOCKS
    out = {"lam": lam, "prevalence": prev, "pi_m": pi_m, "n_per_arm": n, "blocks": BLOCKS, "mean_breach_dates": float(np.mean(n_breach)), "rates": {}}
    rng = np.random.default_rng([SEED, cell, 999])
    for arm in ("null", "alt"):
        out["rates"][arm] = {}
        for d in STATED_DETECTORS:
            k = sum(flags[arm][d])
            p, lo, hi = core.wilson(k, n)
            per = [x / per_block for x in flags[arm][d]]
            out["rates"][arm][d] = {"k": k, "rate": p, "lo": lo, "hi": hi, "block_sd": float(np.std(per, ddof=1))}
    out["auc"] = {}
    for d in ("engine", "fisher", "mannwhitney", "welch", "any_change"):
        a, lo, hi = core.auc_ci(np.array(raw["null"][d]), np.array(raw["alt"][d]), rng)
        out["auc"][d] = {"auc": a, "lo": lo, "hi": hi}
    return out


def _job(args):
    return run_cell(*args)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-block", type=int, default=800)
    ap.add_argument("--workers", type=int, default=10)
    args = ap.parse_args()
    jobs = []
    cid = 0
    for lam in LAMS:
        for prev in PREVS:
            jobs.append((cid, lam, prev, PI_M, args.per_block))
            cid += 1
    for pi_m in SWEEP_PI:
        if pi_m != PI_M:
            jobs.append((cid, BASE[0], BASE[1], pi_m, args.per_block))
            cid += 1
    with mp.Pool(args.workers) as pool:
        cells = pool.map(_job, jobs)
    res = {"seed": SEED, "T": core.T_DEFAULT, "alpha": core.ALPHA, "per_block": args.per_block, "stay": 0.8, "cells": cells}
    (HERE / "results_stated.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("wrote results_stated.json,", len(cells), "cells")


if __name__ == "__main__":
    main()
