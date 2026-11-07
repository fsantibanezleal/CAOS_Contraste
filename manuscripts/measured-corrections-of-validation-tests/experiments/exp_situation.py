"""Experiment 3: the size and the power of the situation-testing light, one cut point against another.

The engine function ``riskvalidation.fairness.situation.situation_test`` returns, for the complainants of the protected
group, how many are significant at the one-sided level 0.05. The light reads the share of significant complainants against
an amber cut point. Each replication draws one dataset from the engine plant
``riskvalidation.fairness.plants.ThresholdBiasPlant`` (the protected group is approved below a cut-off lower by ``gap``
log-odds; gap 0 is the null), runs the ceteris-paribus test with k = 30, and records the counts. Rules evaluated on the same
draws:

  share cut c        reject when the share of significant complainants is at least c, c in (0.05, 0.075, 0.10, 0.15,
                     0.20, 0.25, 0.30); the engine's cut is 0.20, the cut of the first design 0.10
  count binomial     reject when a one-sided binomial test of the number of significant complainants against the level
                     0.05 has p < 0.05 (the rule that treats the complainants as independent)
  Bonferroni any     reject when at least one complainant is significant at the level 0.05 / n_complainants

Design
  cells        n in (400, 1000) applicants, gap in (0, 0.1, 0.2, 0.4, 0.8)
  repetitions  1,000 at gap 0 and 400 at the others; one SeedSequence([20261104, 3, n, 100 * gap, replication])

Usage: python experiments/exp_situation.py [--cache FOLDER] [--workers N] [--reps R]
Writes experiments/results/situation.json.
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402

import argparse  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

K = 30
NS = (400, 1000)
GAPS = (0.0, 0.1, 0.2, 0.4, 0.8)
CUTS = (0.05, 0.075, 0.10, 0.15, 0.20, 0.25, 0.30)
REPS_NULL, REPS_GAP = 1000, 400


def one_replication(args: tuple[int, float, int]) -> list:
    n, gap, rep = args
    from riskvalidation.fairness import plants, situation

    seed = int(np.random.SeedSequence([common.BASE_SEED, 3, n, int(round(100 * gap)), rep]).generate_state(1)[0])
    d = plants.ThresholdBiasPlant(n=n, gap=gap, seed=seed).draw_default()
    r = situation.situation_test(d["x"], d["group"], d["decision"], K)
    bonf = situation.bonferroni_alpha(common.LEVEL, r.n_complainants)
    rb = situation.situation_test(d["x"], d["group"], d["decision"], K, alpha=bonf)
    return [r.n_complainants, r.n_cases, r.n_significant, rb.n_significant]


def summarise(rows: list[list[int]]) -> dict:
    a = np.asarray(rows, dtype=float)
    reps = len(a)
    share = a[:, 2] / a[:, 0]
    rules = {f"cut_{c:g}": common.rate(int(np.sum(share >= c)), reps) for c in CUTS}
    pvals = [stats.binomtest(int(s), int(c), common.LEVEL, alternative="greater").pvalue for c, s in a[:, [0, 2]]]
    rules["count_binomial"] = common.rate(int(np.sum(np.asarray(pvals) < common.LEVEL)), reps)
    rules["bonferroni_any"] = common.rate(int(np.sum(a[:, 3] >= 1)), reps)
    mean_c = float(a[:, 0].mean())
    var_share = float(share.var(ddof=1))
    return {"reps": reps, "mean_complainants": mean_c, "mean_share": float(share.mean()), "sd_share": float(np.sqrt(var_share)),
            "q95_share": float(np.percentile(share, 95.0)), "min_share": float(share.min()),
            "design_effect": var_share * mean_c / (common.LEVEL * (1 - common.LEVEL)),
            "mean_share_cases": float((a[:, 1] / a[:, 0]).mean()), "rules": rules,
            "shares": [round(float(x), 4) for x in share]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    common.add_common_arguments(parser)
    a = parser.parse_args()
    folder = common.cache_folder(a.cache, "situation")

    def reps_of(gap: float) -> int:
        return a.reps or (REPS_NULL if gap == 0.0 else REPS_GAP)

    jobs = [(n, g, i) for n in NS for g in GAPS for i in range(reps_of(g))
            if common.load_cell(folder, f"n{n}-g{g}-r{i}") is None]
    if jobs:
        with ProcessPoolExecutor(max_workers=a.workers) as pool:
            for job, res in zip(jobs, pool.map(one_replication, jobs, chunksize=8)):
                common.save_cell(folder, f"n{job[0]}-g{job[1]}-r{job[2]}", res)
    cells = []
    for n in NS:
        for g in GAPS:
            rows = [common.load_cell(folder, f"n{n}-g{g}-r{i}") for i in range(reps_of(g))]
            cells.append({"n": n, "gap": g, **summarise(rows)})
    out = {"meta": {"experiment": "situation", "versions": common.versions(), "k": K, "base_seed": common.BASE_SEED,
                    "level": common.LEVEL}, "cells": cells}
    path = common.write_result(a.out, "situation.json", out)
    print("wrote", path.name, "cells", len(cells))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
