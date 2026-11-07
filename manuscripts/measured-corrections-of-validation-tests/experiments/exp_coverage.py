"""Experiment 1: the size and the power of the split-conformal coverage test, binomial against Beta-Binomial.

The engine function ``riskvalidation.ml.conformal.conformal_coverage`` returns both p-values of the covered count of ``m``
test rows given a calibration window of ``n`` rows. This script measures, for each window pair, how often each p-value falls
below the level 0.05 when the calibration and the test scores are exchangeable (the size) and when the test scores are
stochastically larger (the power), with the engine's own ``split_conformal_quantile`` and ``conformal_coverage`` on seeded
draws. The covered count is the only statistic the tests read, so the variants of the ablation are evaluated on the same
counts. The size of every test is also computed exactly, by summing the Beta-Binomial law of the count over the rejection
region, with no sampling error.

Design
  size grid   n in (200, 1000, 5000), m / n in (0.1, 0.25, 0.5, 1, 2, 4, 8), scores uniform on (0, 1)
  power grid  (n, m) in ((20000, 2000), (2000, 2000), (1000, 4000)), test scores U ** (1 / b) with the shape b in
              (1, 1.02, 1.05, 1.10, 1.20); the coverage of a quantile q is q ** b, so b = 1 is the null
  repetitions 4,000 per cell, one SeedSequence([20261104, 1, cell index]) stream per cell

Usage: python experiments/exp_coverage.py [--cache FOLDER] [--workers N] [--reps R]
Writes experiments/results/coverage.json.
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402  (sets the thread environment before numpy loads)

import argparse  # noqa: E402
import math  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

REPS = 4000
SIZE_NS = (200, 1000, 5000)
SIZE_RATIOS = (0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0)
POWER_PAIRS = ((20000, 2000), (2000, 2000), (1000, 4000))
SHAPES = (1.0, 1.02, 1.05, 1.10, 1.20)
REL = 1.0 + 1e-7  # the tolerance of the minimum-likelihood rule of scipy.stats.binomtest and of the engine
TARGET = 1.0 - common.CONFORMAL_ALPHA


def cells() -> list[tuple[int, int, float]]:
    out: list[tuple[int, int, float]] = []
    for n in SIZE_NS:
        for r in SIZE_RATIOS:
            out.append((n, int(round(r * n)), 1.0))
    for n, m in POWER_PAIRS:
        for b in SHAPES:
            if (n, m, b) not in out:
                out.append((n, m, b))
    return out


def rank(n: int) -> int:
    """k = ceil((n + 1)(1 - alpha)) on the exact decimal, as the engine computes it."""
    return math.ceil((n + 1) * 9 / 10)


def min_likelihood_p(pmf: np.ndarray) -> np.ndarray:
    """For every count c, the sum of the probabilities of the counts no more likely than c (the rule of the engine)."""
    order = np.argsort(pmf, kind="stable")
    ps = pmf[order]
    cum = np.cumsum(ps)
    idx = np.searchsorted(ps, pmf * REL, side="right")
    return np.clip(cum[idx - 1], 0.0, 1.0)


def tables(n: int, m: int) -> dict[str, np.ndarray]:
    """The p-value of every count 0..m under each variant, and the exact law of the count under exchangeability."""
    c = np.arange(m + 1)
    k = rank(n)
    pmf_true = stats.betabinom.pmf(c, m, k, n + 1 - k)
    out = {
        "law": pmf_true,
        "bb": min_likelihood_p(pmf_true),
        "bin": min_likelihood_p(stats.binom.pmf(c, m, TARGET)),
    }
    cdf = np.cumsum(pmf_true)
    upper = 1.0 - np.concatenate(([0.0], cdf[:-1]))
    out["bb_eqtail"] = np.minimum(1.0, 2.0 * np.minimum(cdf, upper))
    var = m * TARGET * (1 - TARGET) * (m + n + 1) / (n + 2)
    out["z_inflated"] = 2.0 * stats.norm.sf(np.abs(c - m * TARGET) / math.sqrt(var))
    for tag, n_wrong in (("bb_n_half", max(2, n // 2)), ("bb_n_double", 2 * n)):
        kw = rank(n_wrong)
        out[tag] = min_likelihood_p(stats.betabinom.pmf(c, m, kw, n_wrong + 1 - kw))
    return out


def oracle_threshold(p_bin: np.ndarray, law: np.ndarray) -> float:
    """The largest threshold t of the binomial p-value whose exact size under the law stays at most the level."""
    values, inverse = np.unique(p_bin, return_inverse=True)
    mass = np.cumsum(np.bincount(inverse, weights=law))
    ok = np.flatnonzero(mass <= common.LEVEL)
    return float(values[ok[-1]]) if ok.size else -1.0


def exact_sizes(t: dict[str, np.ndarray], t_star: float) -> dict[str, float]:
    law = t["law"]
    out = {name: float(law[t[name] < common.LEVEL].sum()) for name in
           ("bb", "bin", "bb_eqtail", "z_inflated", "bb_n_half", "bb_n_double")}
    out["bin_oracle"] = float(law[t["bin"] <= t_star].sum()) if t_star >= 0 else 0.0
    return out


def run_cell(args: tuple[int, int, float, int, int]) -> dict:
    n, m, b, reps, index = args
    from riskvalidation.ml import conformal

    t = tables(n, m)
    t_star = oracle_threshold(t["bin"], t["law"])
    rng = np.random.default_rng(np.random.SeedSequence([common.BASE_SEED, 1, index]))
    hits = {name: 0 for name in ("bb", "bin", "bb_eqtail", "z_inflated", "bb_n_half", "bb_n_double", "bin_oracle")}
    coverage = 0.0
    mismatches = 0
    zeros = np.zeros(m, dtype=int)
    blank = np.zeros(m, dtype=bool)
    for _ in range(reps):
        q = conformal.split_conformal_quantile(rng.random(n), common.CONFORMAL_ALPHA)
        u = rng.random(m)
        scores = u if b == 1.0 else u ** (1.0 / b)
        covered = scores <= q
        res = conformal.conformal_coverage(np.column_stack([covered, blank]), zeros, common.CONFORMAL_ALPHA, n_cal=n)
        c = int(round(res.coverage * m))
        coverage += res.coverage
        if abs(res.p_value - t["bb"][c]) > 1e-9 or abs(res.p_value_binomial - t["bin"][c]) > 1e-9:
            mismatches += 1
        hits["bb"] += res.p_value < common.LEVEL
        hits["bin"] += res.p_value_binomial < common.LEVEL
        for name in ("bb_eqtail", "z_inflated", "bb_n_half", "bb_n_double"):
            hits[name] += t[name][c] < common.LEVEL
        hits["bin_oracle"] += (t["bin"][c] <= t_star) if t_star >= 0 else 0
    out = {"n": n, "m": m, "b": b, "ratio": m / n, "k": rank(n), "reps": reps, "mean_coverage": coverage / reps,
           "engine_mismatches": mismatches, "oracle_threshold": t_star,
           "rates": {name: common.rate(h, reps) for name, h in hits.items()}}
    if b == 1.0:
        out["exact"] = exact_sizes(t, t_star)
        out["normal_approx_binomial"] = float(2.0 * stats.norm.sf(1.959964 / math.sqrt(1.0 + (m - 1.0) / (n + 2.0))))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    common.add_common_arguments(parser)
    a = parser.parse_args()
    reps = a.reps or REPS
    folder = common.cache_folder(a.cache, "coverage")
    todo, done = [], {}
    for index, (n, m, b) in enumerate(cells()):
        key = f"n{n}-m{m}-b{b}-r{reps}"
        cached = common.load_cell(folder, key)
        if cached is not None:
            done[index] = cached
        else:
            todo.append((index, key, (n, m, b, reps, index)))
    if todo:
        with ProcessPoolExecutor(max_workers=a.workers) as pool:
            for (index, key, _), result in zip(todo, pool.map(run_cell, [t[2] for t in todo])):
                common.save_cell(folder, key, result)
                done[index] = result
    results = [done[i] for i in sorted(done)]
    out = {"meta": {"experiment": "coverage", "versions": common.versions(), "reps": reps, "base_seed": common.BASE_SEED,
                    "level": common.LEVEL, "conformal_alpha": common.CONFORMAL_ALPHA},
           "cells": results}
    path = common.write_result(a.out, "coverage.json", out)
    print("wrote", path.name, "cells", len(results), "engine mismatches", sum(r["engine_mismatches"] for r in results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
