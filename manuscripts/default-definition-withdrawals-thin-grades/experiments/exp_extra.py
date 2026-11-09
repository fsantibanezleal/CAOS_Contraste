"""Experiment 5: the comparisons that the review of the manuscript asked for, on the draws of Experiment 2.

Two measurements, both on the generator and the seeds of ``exp_withdrawals.py`` so that each reads the very datasets
the main experiment read:

A. The duration estimator of Lando and Skodeberg (``riskvalidation.transitions.estimators.duration_generator``), which
   treats a withdrawal as a censoring of the continuous-time path, on the observed paths at every level of k of the
   extension (1,000 repetitions each, seed ``bs4:withdrawals:informative=<k>``). Its one-year PD by grade is the default
   column of the matrix exponential of the fitted generator, as the case's Markov family reads it. The relative bias and
   the share of repetitions with a zero PD are reported next to those of the cohort treatments.

B. The transition tests of the engine that Experiment 2 did not run, at k = 0, 9 and 19 over 1,000 repetitions on the
   seed ``bs4:tests:informative=<k>`` of Experiment 2: the test of the Markov order, the momentum test and the
   monotonicity z-tests of the migration matrix. The matrix weighted bandwidth (``rating.mwb``) is a descriptive metric
   with no decision rule and is not run.

Run from the repository root::

    python manuscripts/default-definition-withdrawals-thin-grades/experiments/exp_extra.py

It writes ``experiments/extra.json`` and takes a few minutes (the sizes are printed while it runs).
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import numpy as np
from scipy.linalg import expm

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "manuscripts" / "_shared"))
sys.path.insert(0, str(ROOT / "data-pipeline"))
sys.path.insert(0, str(HERE))

import figkit  # noqa: E402
import exp_withdrawals as ew  # noqa: E402
from pipeline.cases import c04_families as fam  # noqa: E402
from riskvalidation.transitions.estimators import duration_generator  # noqa: E402

M = fam.M
D = fam.D
LADDER = ew.NEW_LADDER
REPS = ew.NEW_REPS
TEST_LADDER = ew.TEST_LADDER
TEST_REPS = ew.TEST_REPS


def _feed_counts_first(d: dict) -> dict:
    """The pooled counts of the five annual steps, the matrix the monotonicity z-tests read."""
    counts = sum(np.asarray(s["counts"], dtype=float) for s in d["steps"])
    return {"counts": counts}


def main() -> None:
    t0 = time.time()
    wd = figkit.doc("C04/withdrawals.json")["outputs"]
    q = np.array(wd["generator"]["q"])
    obligors = list(wd["generator"]["obligors"])
    truth = np.array(fam._pd(fam._paths(q, obligors)), dtype=float)
    result: dict = {"case_seed": ew.CASE_SEED, "grades": ew.GRADES, "truth_pd": truth.tolist(), "reps": REPS}

    # A: the duration estimator with withdrawals as censoring
    rungs = []
    for k in LADDER:
        seed = ew.seed_for(f"bs4:withdrawals:informative={k:g}")
        gen = fam._paths(q, obligors, withdrawal_rate=fam.WITHDRAWAL_RATE, informative=k, window=fam.WINDOW)
        est = np.empty((REPS, D))
        for i, child in enumerate(fam._children(seed, REPS)):
            obs = gen.draw(np.random.default_rng(child))
            est[i] = expm(duration_generator(obs["segments"], M)["generator"])[:D, D]
        rungs.append({"k": k, "seed": seed, "reps": REPS, "duration": ew.summarise(est, truth)})
        print(f"A k={k:g} done ({time.time() - t0:.0f}s)", flush=True)
    result["duration"] = rungs

    # B: the transition tests that Experiment 2 did not run
    tests = [("rating.markov_order", fam._feed_triplets), ("rating.momentum", fam._feed_paths),
             ("rating.migration_ztests", _feed_counts_first)]
    rows = []
    for k in TEST_LADDER:
        gen = fam._paths(q, obligors, withdrawal_rate=fam.WITHDRAWAL_RATE, informative=k, window=fam.WINDOW)
        seed = ew.seed_for(f"bs4:tests:informative={k:g}")
        rows += fam._simulations(gen, tests, seed=seed, reps=TEST_REPS, rung=k, label=f"k{k:g}")
        print(f"B k={k:g} done ({time.time() - t0:.0f}s)", flush=True)
    result["tests"] = rows
    result["seconds"] = round(time.time() - t0, 1)
    (HERE / "extra.json").write_text(json.dumps(result, indent=1), encoding="utf-8", newline="\n")
    print("written", flush=True)


if __name__ == "__main__":
    main()
