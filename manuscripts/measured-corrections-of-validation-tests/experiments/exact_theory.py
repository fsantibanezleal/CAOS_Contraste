"""The exact (sampling-free) quantities of the manuscript: the size and the power of the coverage tests by summation of the
Beta-Binomial law, the variance ratio behind the size inflation of the binomial test, and the granularity of a permutation
p-value. Nothing here is simulated, so none of it carries a Monte Carlo error; ``exp_coverage.py`` measures the same sizes
by simulation with the engine's own functions and the two agree within the standard errors.

Under exchangeability with continuous scores, the covered count of m test rows given n calibration rows is
Beta-Binomial(m, k, n + 1 - k), k = ceil((n + 1)(1 - alpha)). The exact size of a test that rejects on a set of counts is the
mass of that set. Under the shape-b drift of ``exp_coverage.py`` the coverage of the set is V ** b with V ~ Beta(k, n + 1 - k),
so the exact power is the expectation over V of a binomial mass, taken here by the midpoint rule on 2,000 quantiles of V.

Usage: python experiments/exact_theory.py [--out FOLDER]
Writes experiments/results/exact.json.
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402

import argparse  # noqa: E402
import math  # noqa: E402

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from exp_coverage import TARGET, min_likelihood_p, oracle_threshold, rank, tables  # noqa: E402

SIZE_NS = (200, 1000, 5000)
RATIOS = [0.05 * 2 ** (i / 2) for i in range(0, 17)]  # 0.05 to 12.8
POWER_PAIRS = ((2000, 2000), (1000, 4000), (20000, 2000))
SHAPES = [1.0 + 0.02 * i for i in range(0, 16)]
NODES = 2000


def size_curves() -> list[dict]:
    out = []
    for n in SIZE_NS:
        for r in RATIOS:
            m = max(2, int(round(r * n)))
            t = tables(n, m)
            law = t["law"]
            k = rank(n)
            # the test of rank k read against a calibration whose true rank is one higher (an off-by-one quantile)
            c = np.arange(m + 1)
            law_off = stats.betabinom.pmf(c, m, k + 1, n - k)
            out.append({
                "n": n, "m": m, "ratio": m / n,
                "bin": float(law[t["bin"] < common.LEVEL].sum()),
                "bb": float(law[t["bb"] < common.LEVEL].sum()),
                "normal_approx_bin": float(2.0 * stats.norm.sf(1.959964 / math.sqrt(1.0 + (m - 1.0) / (n + 2.0)))),
                "bb_rank_plus_one": float(law_off[t["bb"] < common.LEVEL].sum()),
                "bin_rank_plus_one": float(law_off[t["bin"] < common.LEVEL].sum()),
            })
    return out


def variance_ratio() -> dict:
    worst, rows = 0.0, []
    for n, m in ((200, 50), (200, 800), (1000, 1000), (1000, 4000), (5000, 40000)):
        k = rank(n)
        c = np.arange(m + 1)
        pmf = stats.betabinom.pmf(c, m, k, n + 1 - k)
        mean = float((c * pmf).sum())
        var = float(((c - mean) ** 2 * pmf).sum())
        mu = k / (n + 1.0)
        binom_var = m * mu * (1 - mu)
        closed = (m + n + 1.0) / (n + 2.0)
        err = abs(var / binom_var - closed)
        worst = max(worst, err)
        rows.append({"n": n, "m": m, "ratio_exact": var / binom_var, "ratio_closed_form": closed})
    return {"rows": rows, "max_abs_error": worst}


def power_curves() -> list[dict]:
    out = []
    u = (np.arange(NODES) + 0.5) / NODES
    for n, m in POWER_PAIRS:
        k = rank(n)
        t = tables(n, m)
        c = np.arange(m + 1)
        t_star = oracle_threshold(t["bin"], t["law"])
        masks = {"bb": t["bb"] < common.LEVEL, "bin": t["bin"] < common.LEVEL, "bin_oracle": t["bin"] <= t_star,
                 "bb_eqtail": t["bb_eqtail"] < common.LEVEL}
        v = stats.beta.ppf(u, k, n + 1 - k)
        for b in SHAPES:
            cov = v ** b
            pm = stats.binom.pmf(c[None, :], m, cov[:, None])
            out.append({"n": n, "m": m, "b": b, "mean_coverage": float(cov.mean()),
                        "power": {name: float((pm @ mask.astype(float)).mean()) for name, mask in masks.items()}})
    return out


def granularity() -> list[dict]:
    rows = []
    for r in (19, 39, 99, 199):
        smallest = 1.0 / (r + 1)
        # the largest number of null draws at or above the observed drop that still gives p < 0.05
        allowed = max(-1, -(-(r + 1) // 20) - 2)  # ceil((R + 1) / 20) - 2 in integers (0.05 * 40 is not exactly 2)
        rows.append({"draws": r, "smallest_p": smallest, "can_reject_below_0.05": smallest < common.LEVEL,
                     "max_null_draws_above_observed": allowed})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=pathlib.Path, default=common.RESULTS)
    a = parser.parse_args()
    out = {"meta": {"experiment": "exact", "versions": common.versions(), "level": common.LEVEL,
                    "conformal_alpha": common.CONFORMAL_ALPHA, "nodes": NODES, "target": TARGET},
           "size_curves": size_curves(), "variance_ratio": variance_ratio(), "power_curves": power_curves(),
           "granularity": granularity()}
    path = common.write_result(a.out, "exact.json", out)
    print("wrote", path.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
