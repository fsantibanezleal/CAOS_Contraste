"""Experiment 2: how stable is the size verdict of one 4,000-repetition cell?

Each of the 21 null cells is measured again in BLOCKS independent blocks of 4,000 repetitions, every block with a seed
derived from ``SeedSequence([ENTROPY, test index, block index])``, so no block shares a stream with the committed cell or
with another block. Per block the counts of rejections at 5% and 1% are kept, in total and per slice of 1,000
repetitions, which is what the ablation of the repetition number reads (``make_numbers.py``).

    python manuscripts/size-and-power-of-validation-tests/experiments/exp_seed_replication.py [--blocks 50]

Writes ``results/seed_replication.json`` (about 100 kB). The run takes a few minutes on 24 worker processes.
"""
from __future__ import annotations

import argparse
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

import common
import scenarios

ENTROPY = 20261107
N_REP = 4000


def seed_of(test_index: int, block: int) -> int:
    return int(np.random.SeedSequence([ENTROPY, test_index, block]).generate_state(1)[0])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", type=int, default=50)
    ap.add_argument("--workers", type=int, default=24)
    a = ap.parse_args()
    scs = scenarios.credit_null_scenarios()
    scenarios.check_against_document(scs)
    jobs = [(s.key, seed_of(i, b), N_REP) for i, s in enumerate(scs) for b in range(a.blocks)]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        runs = list(pool.map(common.run_cell, *zip(*jobs), chunksize=4))
    by_key: dict[str, list[dict]] = {s.key: [] for s in scs}
    for r in runs:
        by_key[r["key"]].append({k: r[k] for k in ("seed", "undefined", "k0.05", "k0.01", "slices0.05", "slices0.01")})
    common.write_json("seed_replication.json", {
        "engine": "riskvalidation 1.1.0", "entropy": ENTROPY, "blocks": a.blocks, "n_rep": N_REP, "slice": common.SLICE,
        "seconds": round(time.time() - t0, 1), "cells": by_key})
    print(f"{len(runs)} blocks of {N_REP} repetitions in {time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
