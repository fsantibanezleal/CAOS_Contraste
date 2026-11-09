"""Numerical checks of the propositions of the Theory section, each against the quantity the proposition states.

1. ``detection``: the probability that the outside-information gate (G3) changes a quantile-binning edge when ``m`` outside rows are sent
   beyond the training range, simulated with the pipeline's own edge function, against the exact expression of Proposition 2.
2. ``max_bound``: the expected excess of the best of K noisy estimates over the truth, simulated for independent and for correlated
   estimates, against the bound sigma * sqrt(2 ln K) of Proposition 3.
3. ``leak_auc``: the closed forms of Proposition 4 against the committed C22 truth (the engine generator's exact values) at every
   leak level of the committed family.
4. ``psi``: the second-order form of Proposition 5 against the exact decile PSI the engine reports as the generator's truth.

    python manuscripts/leakage-safe-validation-protocol/experiments/theory_checks.py
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

import numpy as np
from scipy.special import comb, ndtr
from scipy.stats import norm

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import leaklab as L  # noqa: E402

from riskvalidation.generators.scores import DECILES, BinormalScores  # noqa: E402

SEED = 20261110


def detection(trials: int = 40_000, n_train: int = 1050, n_out: int = 450) -> dict:
    rng = np.random.default_rng(SEED)
    N = n_train + n_out
    out = {}
    h = (N - 1) * 0.9
    k = int(math.floor(h)) + 2  # the 1-based rank of the upper bracket of the 90% edge under linear interpolation
    for m in (1, 2, 3, 5, 10):
        changed = 0
        for _ in range(trials // 4):
            x = rng.normal(size=(N, 1))
            base = L._edges(x[:, :], 10)[0]
            moved = x.copy()
            rows = n_train + rng.choice(n_out, size=m, replace=False)
            moved[rows] = x.max() + 10.0
            changed += not np.array_equal(base, L._edges(moved, 10)[0])
        p = changed / (trials // 4)
        exact = 1.0 - comb(N - k, m) / comb(N, m)
        approx = 1.0 - 0.1 ** m
        out[str(m)] = {"simulated": p, "exact": float(exact), "approx": approx, "se": math.sqrt(p * (1 - p) / (trials // 4))}
    return {"n_train": n_train, "n_out": n_out, "trials": trials // 4, "by_m": out}


def max_bound(trials: int = 200_000) -> dict:
    rng = np.random.default_rng(SEED + 1)
    out = {}
    for K in (2, 4, 8, 16, 64):
        row = {"bound": float(math.sqrt(2.0 * math.log(K)))}
        for rho in (0.0, 0.5, 0.9):
            z = rng.normal(size=(trials // 10, 1)) * math.sqrt(rho) + rng.normal(size=(trials // 10, K)) * math.sqrt(1 - rho)
            row[f"rho={rho}"] = float(z.max(axis=1).mean())
        out[str(K)] = row
    return {"in_units_of_sigma": out}


def leak_auc() -> dict:
    out = {}
    for s in (0.0, 0.25, 0.5, 1.0, 1.5, 2.0):
        truth = BinormalScores(n_defaulters=150, n_survivors=4850, separation=1.0, leak=s).truth()
        den = math.sqrt(2.0 * 2.0)
        out[str(s)] = {"engine_dev": truth["auc_development"], "formula_dev": float(norm.cdf((1.0 + s) / den)),
                       "engine_cur": truth["auc_current"], "formula_cur": float(norm.cdf(1.0 / den)),
                       "clean": truth["auc_genuine_current"], "formula_clean": float(norm.cdf(1.0 / math.sqrt(2.0)))}
    # the committed document holds the same truth for the leak levels it ran
    doc = json.loads((ROOT / "data" / "derived" / "C22" / "leakage.json").read_text(encoding="utf-8"))
    out["committed"] = {k: {"dev": v["truth"]["auc_development"], "cur": v["truth"]["auc_current"]}
                        for k, v in doc["outputs"]["generators"].items() if k.startswith("binormal-150-leak")}
    # the optimal development weights w proportional to (d, s): the development AUC maximum and the decision-time loss
    opt = {}
    for s in (0.5, 1.0, 2.0):
        d = 1.0
        opt[str(s)] = {"dev": float(norm.cdf(math.sqrt(d * d + s * s) / math.sqrt(2.0))),
                       "cur": float(norm.cdf(d * d / math.sqrt(2.0 * (d * d + s * s)))), "clean": float(norm.cdf(d / math.sqrt(2.0)))}
    out["optimal_weights"] = opt
    return out


def psi() -> dict:
    out = {}
    pi = 150 / 5000
    edges = np.concatenate([[-np.inf], DECILES, [np.inf]])
    p = np.diff(ndtr(edges))
    for s in (0.25, 0.5, 1.0, 1.5, 2.0, 3.0):
        truth = BinormalScores(n_defaulters=150, n_survivors=4850, separation=1.0, leak=s).truth()
        r = np.diff(ndtr(edges - s))
        chi2_binned = float(np.sum((r - p) ** 2 / p))
        out[str(s)] = {"engine_psi": truth["feature_population_psi"], "binned_chi2_form": pi * pi * chi2_binned,
                       "continuous_form": pi * pi * (math.exp(s * s) - 1.0)}
    out["null_expectation_10_bins"] = 9 * (1 / 5000 + 1 / 5000)
    return out


def main() -> None:
    res = {"seed": SEED, "detection": detection(), "max_bound": max_bound(), "leak_auc": leak_auc(), "psi": psi()}
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "theory_checks.json").write_text(json.dumps(res, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps(res["detection"]["by_m"], indent=0)[:600])
    print(json.dumps(res["psi"], indent=0)[:700])


if __name__ == "__main__":
    main()
