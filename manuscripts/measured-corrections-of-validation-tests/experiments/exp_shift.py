"""Experiment 2: the size and the power of the worst-subsample resilience test, fixed cut points against a development-only
permutation reference.

Each replication draws one development sample and one evaluation sample from the engine plant
``riskvalidation.ml.plants.CovariateShiftPlant`` (a quarter of the evaluation rows shifted by ``shift`` standard
deviations on the first covariate; shift 0 is the null), scores every evaluation row by its resemblance to the development
rows (``shift_score_rank``), takes the worst quarter, and reads the AUC drop of that subsample with five rules, all on the
same draw:

  fixed cut 0.05, fixed cut 0.10   reject when the raw drop exceeds the cut (the practice the research describes)
  variance z rule                  reject when the one-sided z test of AUC(rest) - AUC(worst subsample), with the
                                   engine's ``auc_with_variance`` for each part, has p < 0.05
  permutation reference            reject when the p-value of ``shift_development_reference`` is below 0.05, read with the
                                   first R of the 199 draws for R in (19, 39, 99, 199)

The draws of a reference with R permutations are the first R draws of the reference with 199 (one random stream), so the
four values of R come from one run.

Design
  cells        evaluation size in (125, 250, 500, 1000) with development 2x as large, shift in (0, 2); plus shifts (1, 3)
               at evaluation 500; share of the worst subsample 0.25
  repetitions  400 per cell; one SeedSequence([20261104, 2, evaluation size, 10 * shift, replication]) per replication

Usage: python experiments/exp_shift.py [--cache FOLDER] [--workers N] [--reps R]
Writes experiments/results/shift.json.
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402

import argparse  # noqa: E402
import time  # noqa: E402
import math  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

REPS = 400
SHARE = 0.25
DRAWS = 199
DRAW_GRID = (19, 39, 99, 199)
CUTS = (0.05, 0.10)
EVAL_SIZES = (125, 250, 500, 1000)
CELLS = [(e, s) for e in EVAL_SIZES for s in (0.0, 2.0)] + [(500, 1.0), (500, 3.0)]


def one_replication(args: tuple[int, float, int]) -> dict:
    n_eval, shift, rep = args
    from riskvalidation.ml import plants, robustness
    from riskvalidation.validation.discrimination import auc_with_variance

    seeds = np.random.SeedSequence([common.BASE_SEED, 2, n_eval, int(round(10 * shift)), rep]).generate_state(3)
    n_dev = 2 * n_eval
    plant = plants.CovariateShiftPlant(n=n_dev, shift=shift, features=[0], seed=int(seeds[0]))
    d = plant.sample()
    x_eval, y_eval = d["X_eval"][:n_eval], d["y_eval"][:n_eval]
    score = robustness.shift_score_rank(d["X_dev"], x_eval, seed=int(seeds[1]))
    try:
        ref = robustness.shift_development_reference(
            plant.predict, d["X_dev"], d["y_dev"], x_eval, y_eval, score, SHARE, DRAWS, seed=int(seeds[2]))
    except robustness.SingleClassSubsampleError:
        return {"skipped": True}
    p = np.asarray(plant.predict(x_eval), dtype=float)
    m = math.ceil(SHARE * n_eval)
    worst = np.argsort(-score, kind="stable")[:m]
    rest = np.setdiff1d(np.arange(n_eval), worst)
    auc_w, var_w = auc_with_variance(p[worst], y_eval[worst])[:2]
    auc_r, var_r = auc_with_variance(p[rest], y_eval[rest])[:2]
    z = (auc_r - auc_w) / math.sqrt(var_r + var_w)
    nulls = np.asarray(ref.null_drops)
    p_by_draws = {}
    for r in DRAW_GRID:
        head = nulls[:r]
        p_by_draws[str(r)] = float((1 + np.sum(head >= ref.observed_drop)) / (len(head) + 1))
    return {"skipped": False, "drop": float(ref.observed_drop), "z_p": float(stats.norm.sf(z)),
            "p": p_by_draws, "undefined": int(ref.n_undefined), "null_mean": float(nulls.mean()),
            "null_p95": float(np.percentile(nulls, 95.0)), "enough": bool(ref.enough_development)}


def summarise(rows: list[dict]) -> dict:
    ok = [r for r in rows if not r["skipped"]]
    n = len(ok)
    drops = np.array([r["drop"] for r in ok])
    rules = {f"fixed_{c:.2f}": common.rate(int(np.sum(drops > c)), n) for c in CUTS}
    rules["z_rule"] = common.rate(sum(r["z_p"] < common.LEVEL for r in ok), n)
    for r in DRAW_GRID:
        rules[f"perm_{r}"] = common.rate(sum(x["p"][str(r)] < common.LEVEL for x in ok), n)
    return {"n": n, "skipped": len(rows) - n, "undefined_draws": int(sum(r["undefined"] for r in ok)),
            "mean_drop": float(drops.mean()), "sd_drop": float(drops.std(ddof=1)),
            "q95_drop": float(np.percentile(drops, 95.0)), "mean_null_mean": float(np.mean([r["null_mean"] for r in ok])),
            "rules": rules, "drops": [round(float(x), 4) for x in drops]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    common.add_common_arguments(parser)
    a = parser.parse_args()
    reps = a.reps or REPS
    folder = common.cache_folder(a.cache, "shift")
    jobs = [(e, s, i) for e, s in CELLS for i in range(reps)
            if common.load_cell(folder, f"e{e}-s{s}-r{i}") is None]
    if jobs:
        started = time.perf_counter()
        with ProcessPoolExecutor(max_workers=a.workers) as pool:
            for job, res in zip(jobs, pool.map(one_replication, jobs, chunksize=4)):
                common.save_cell(folder, f"e{job[0]}-s{job[1]}-r{job[2]}", res)
        if len(jobs) == len(CELLS) * reps:  # a cold run: every replication was computed here
            common.record_timing(a.out, "shift", time.perf_counter() - started, a.workers, len(jobs))
    cells = []
    for e, s in CELLS:
        rows = [common.load_cell(folder, f"e{e}-s{s}-r{i}") for i in range(reps)]
        cells.append({"n_eval": e, "n_dev": 2 * e, "shift": s, **summarise(rows)})
    out = {"meta": {"experiment": "shift", "versions": common.versions(), "reps": reps, "share": SHARE,
                    "draws": DRAWS, "base_seed": common.BASE_SEED, "level": common.LEVEL}, "cells": cells}
    path = common.write_result(a.out, "shift.json", out)
    print("wrote", path.name, "cells", len(cells))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
