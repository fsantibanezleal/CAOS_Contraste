"""Experiment 4: the situation-testing light on a second planted design, to measure whether a cut point carries over from one
data-generating process to another.

Experiment 3 (``exp_situation.py``) draws the decisions from the engine plant ``ThresholdBiasPlant``: the decision is a
deterministic function of a risk index that is correlated with the attributes the test matches on. This script draws them
from the design of the engine's own size-and-power suite (``tests/fairness/test_fairness_size_power.py``, class
``SituationPlant``): two attributes independent and uniform on (0, 10), a protected group of share 0.4, and a negative
decision with probability 0.25 for the others and 0.25 + ``bias`` for the protected group, independent of the attributes. The
class lives in the engine's test folder and is not importable, so it is restated here with the same draws.

The same rules as experiment 3 are read on the same replications: the share of significant complainants against the cut
points, the binomial test of the count and the Bonferroni rule.

Design
  cells        n in (400, 1000) applicants, bias in (0, 0.1, 0.2, 0.4)
  repetitions  2,000 at bias 0 and 400 at the others; one SeedSequence([20261104, 4, n, 100 * bias, replication])
  neighbours   k = 30 (ceteris paribus, range normalisation, level 0.05), as in experiment 3

Usage: python experiments/exp_situation_indep.py [--cache FOLDER] [--workers N] [--reps R]
Writes experiments/results/situation_indep.json.
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402

import argparse  # noqa: E402
import time  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402

import numpy as np  # noqa: E402

import exp_situation  # noqa: E402

K = exp_situation.K
NS = (400, 1000)
BIASES = (0.0, 0.1, 0.2, 0.4)
REPS_NULL, REPS_BIAS = 2000, 400
PROTECTED_SHARE = 0.4
BASE_NEGATIVE = 0.25


def draw(n: int, bias: float, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The draws of the engine's ``SituationPlant``: group, attributes and decision in the same order of random calls."""
    group = (rng.random(n) < PROTECTED_SHARE).astype(int)
    x = rng.uniform(0.0, 10.0, (n, 2))
    p_negative = BASE_NEGATIVE + np.where(group == 1, bias, 0.0)
    decision = (rng.random(n) >= p_negative).astype(int)
    return x, group, decision


def one_replication(args: tuple[int, float, int]) -> list:
    n, bias, rep = args
    from riskvalidation.fairness import situation

    rng = np.random.default_rng(np.random.SeedSequence([common.BASE_SEED, 4, n, int(round(100 * bias)), rep]))
    x, group, decision = draw(n, bias, rng)
    r = situation.situation_test(x, group, decision, K)
    bonf = situation.bonferroni_alpha(common.LEVEL, r.n_complainants)
    rb = situation.situation_test(x, group, decision, K, alpha=bonf)
    return [r.n_complainants, r.n_cases, r.n_significant, rb.n_significant]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    common.add_common_arguments(parser)
    a = parser.parse_args()
    folder = common.cache_folder(a.cache, "situation_indep")

    def reps_of(bias: float) -> int:
        return a.reps or (REPS_NULL if bias == 0.0 else REPS_BIAS)

    jobs = [(n, b, i) for n in NS for b in BIASES for i in range(reps_of(b))
            if common.load_cell(folder, f"n{n}-b{b}-r{i}") is None]
    if jobs:
        started = time.perf_counter()
        with ProcessPoolExecutor(max_workers=a.workers) as pool:
            for job, res in zip(jobs, pool.map(one_replication, jobs, chunksize=8)):
                common.save_cell(folder, f"n{job[0]}-b{job[1]}-r{job[2]}", res)
        if len(jobs) == sum(reps_of(b) for n in NS for b in BIASES):  # a cold run: every replication was computed here
            common.record_timing(a.out, "situation_indep", time.perf_counter() - started, a.workers, len(jobs))
    cells = []
    for n in NS:
        for b in BIASES:
            rows = [common.load_cell(folder, f"n{n}-b{b}-r{i}") for i in range(reps_of(b))]
            cells.append({"n": n, "bias": b, **exp_situation.summarise(rows)})
    out = {"meta": {"experiment": "situation_indep", "versions": common.versions(), "k": K, "base_seed": common.BASE_SEED,
                    "level": common.LEVEL}, "cells": cells}
    path = common.write_result(a.out, "situation_indep.json", out)
    print("wrote", path.name, "cells", len(cells))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
