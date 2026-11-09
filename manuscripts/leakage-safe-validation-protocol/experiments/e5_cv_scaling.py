"""E5: how the bias of k-fold validation with preprocessing outside the folds scales with the sample size and the number of inputs.

The same planted data and the same pipeline as E1, five-fold cross-validation with the binning, the WoE, the association screen and the
imputation fitted either inside each training fold or on all development rows before the folds (Ambroise and McLachlan 2002). The bias is
the cross-validated AUC minus the mean oracle AUC of the fold models. A log-log regression of the bias of the outside variant on the number
of development rows gives the exponent reported as a stated conjecture (Section ``theory``).

    python manuscripts/leakage-safe-validation-protocol/experiments/e5_cv_scaling.py --reps 100
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import sys
from concurrent.futures import ProcessPoolExecutor

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import leaklab as L  # noqa: E402
from e1_estimator_bias import cv_estimate  # noqa: E402

SEED = 20261111
GRID = [(n, 40) for n in (400, 800, 1600, 3200, 6400)] + [(1600, p) for p in (10, 20, 80, 160)]
N_ORACLE = 20_000


def one(job: tuple[int, int, int]) -> dict:
    n, p, r = job
    rng = np.random.default_rng(np.random.SeedSequence([SEED, n, p, r]))
    X, y = L.planted(n, p, rng)
    Xo, yo = L.planted(N_ORACLE, p, rng)
    dev = np.arange(n)
    out = {}
    for pre in (False, True):
        e, o = cv_estimate(X, y, dev, "woe", pre, rng, Xo, yo)
        out["outside" if pre else "inside"] = e - o
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=100)
    ap.add_argument("--workers", type=int, default=30)
    a = ap.parse_args()
    jobs = [(n, p, r) for n, p in GRID for r in range(a.reps)]
    with ProcessPoolExecutor(a.workers) as ex:
        rows = list(ex.map(one, jobs, chunksize=4))
    cells = []
    for n, p in GRID:
        sel = [row for (nn, pp, _), row in zip(jobs, rows) if (nn, pp) == (n, p)]
        cell = {"n": n, "p": p}
        for k in ("inside", "outside"):
            v = np.array([s[k] for s in sel])
            cell[k] = {"bias": float(v.mean()), "se": float(v.std(ddof=1) / math.sqrt(len(v)))}
        cells.append(cell)
    # log-log fit of the outside bias on n at p = 40 (weights: inverse variance of the log bias)
    ns = np.array([c["n"] for c in cells if c["p"] == 40 and c["n"] != 1600] + [1600])
    sel = sorted([c for c in cells if c["p"] == 40], key=lambda c: c["n"])
    x = np.log([c["n"] for c in sel])
    y = np.log([c["outside"]["bias"] for c in sel])
    w = np.array([(c["outside"]["bias"] / c["outside"]["se"]) ** 2 for c in sel])
    X = np.column_stack([np.ones_like(x), x])
    W = np.diag(w)
    cov = np.linalg.inv(X.T @ W @ X)
    beta = cov @ X.T @ W @ y
    res = {"seed": SEED, "reps": a.reps, "oracle_rows": N_ORACLE, "cells": cells,
           "loglog_fit_p40": {"exponent": float(beta[1]), "exponent_se": float(math.sqrt(cov[1, 1])), "intercept": float(beta[0])}}
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "e5_cv_scaling.json").write_text(json.dumps(res, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps(res["loglog_fit_p40"]))
    for c in cells:
        print(c["n"], c["p"], round(c["inside"]["bias"], 4), round(c["outside"]["bias"], 4))


if __name__ == "__main__":
    main()
