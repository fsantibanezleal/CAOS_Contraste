"""Experiment 1: do the committed counts reproduce from the committed configuration and seed?

Every one of the 21 null cells of ``data/derived/C22/null.json`` is run again with the engine's ``simulate`` on the
generator rebuilt in ``scenarios.py``, with the seed and the number of repetitions the document records. The counts of
rejections at 5% and 1% must equal the committed ones exactly (a repetition depends on the seed and its index only).

    python manuscripts/size-and-power-of-validation-tests/experiments/exp_reproduce.py

Writes ``results/reproduce.json``.
"""
from __future__ import annotations

import argparse
import time
from concurrent.futures import ProcessPoolExecutor

import common
import scenarios


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    scs = scenarios.credit_null_scenarios()
    scenarios.check_against_document(scs)
    rows = {r["key"]: r for r in scenarios.committed_null()["outputs"]["simulations"]}
    jobs = [(s.key, rows[s.key]["seed"], rows[s.key]["n_rep"]) for s in scs]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=min(len(jobs), a.workers)) as pool:
        runs = list(pool.map(common.run_cell, *zip(*jobs)))
    out = []
    for run in runs:
        c = rows[run["key"]]["rates"]
        out.append({
            "key": run["key"], "seed": run["seed"], "n_rep": run["n_rep"],
            "k05": run["k0.05"], "k01": run["k0.01"],
            "committed_k05": c["p<0.05"]["rejections"], "committed_k01": c["p<0.01"]["rejections"],
            "equal": run["k0.05"] == c["p<0.05"]["rejections"] and run["k0.01"] == c["p<0.01"]["rejections"]
                     and run["undefined"] == c["p<0.05"]["undefined"],
        })
    common.write_json("reproduce.json", {"engine": "riskvalidation 1.1.0", "seconds": round(time.time() - t0, 1),
                                         "cells": out, "equal": sum(o["equal"] for o in out), "total": len(out)})
    print(f"{sum(o['equal'] for o in out)} of {len(out)} cells reproduce exactly in {time.time() - t0:.0f} s")
    for o in out:
        if not o["equal"]:
            print("DIFFERS:", o)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
