"""Experiment 3: what the checks of the measurement itself can and cannot see.

Part A (exact, no simulation): the probability that the one-sided size bound flags a test whose true size is exactly its
level, for the repetition numbers of the measurement, and the probability that at least one of the 21 tests at two levels is
flagged (independence across tests and levels is assumed only for the family-wise figure, and stated as such).

Part B (exact): the probability that the agreement check ``|rate - exact| <= 3.29 SE`` fails when the generator that draws the
data is wrong, i.e. when the PD that produces the defaults is the nominal PD times a factor and the exact probability is
that of the nominal PD. The count of rejections is binomial with the exact rejection probability of the wrong generator, so
the probability is a sum of binomial terms (the exact rejection probabilities are the engine's ``rejection_probability``).

Part C (simulation): the same planted fault run through the engine's ``simulate`` in 200 independent blocks of 4,000
repetitions, with the share of blocks the agreement check flags, to confirm Part B.

    python manuscripts/size-and-power-of-validation-tests/experiments/exp_instrument.py

Writes ``results/instrument.json``.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import stats

import common
from riskvalidation.generators import DefaultCounts, feed_cell
from riskvalidation.harness import agrees, rejection_probability, simulate, size_bound
from riskvalidation.harness.rates import Rate

Z_BOUND = float(stats.norm.ppf(0.999))
Z_AGREE = 3.29


def flag_probability(alpha: float, n_rep: int) -> float:
    """P(K/n > bound) for K ~ Bin(n, alpha): the chance that a test of true size alpha is flagged as oversized."""
    bound = alpha + Z_BOUND * math.sqrt(alpha * (1 - alpha) / n_rep)
    kmin = math.floor(bound * n_rep) + 1          # smallest count whose rate exceeds the bound
    return float(stats.binom.sf(kmin - 1, n_rep, alpha))


def agreement_failure_probability(p_true: float, p_nominal: float, n_rep: int) -> float:
    """P(|K/n - p_nominal| > 3.29 sqrt(p_nominal (1 - p_nominal) / n)) for K ~ Bin(n, p_true)."""
    half = Z_AGREE * math.sqrt(p_nominal * (1 - p_nominal) / n_rep)
    lo, hi = (p_nominal - half) * n_rep, (p_nominal + half) * n_rep
    inside = stats.binom.cdf(math.floor(hi), n_rep, p_true) - stats.binom.cdf(math.ceil(lo) - 1, n_rep, p_true)
    return float(1.0 - inside)


def main() -> int:
    out: dict = {"engine": "riskvalidation 1.1.0", "z_bound": Z_BOUND, "z_agree": Z_AGREE}
    # Part A
    flag = {}
    for n in (1000, 2000, 4000, 20000):
        flag[str(n)] = {f"{a:g}": flag_probability(a, n) for a in (0.05, 0.01)}
    out["flag_probability"] = flag
    per_test = {n: 1 - (1 - flag[n]["0.05"]) * (1 - flag[n]["0.01"]) for n in flag}
    out["flag_probability_per_test"] = per_test
    out["flag_probability_family_21"] = {n: 1 - (1 - per_test[n]) ** 21 for n in per_test}
    # Part B
    test_levels = [("pd.binomial", 0.05), ("pd.binomial", 0.01), ("pd.jeffreys", 0.05), ("pd.jeffreys", 0.01)]
    factors = [1.0, 1.02, 1.05, 1.10, 1.25]
    pb = []
    for test, alpha in test_levels:
        p_nominal = rejection_probability(test, 1000, 0.01, alpha, pd_true=0.01, rho_true=0.0)["probability"]
        for f in factors:
            p_wrong = rejection_probability(test, 1000, 0.01, alpha, pd_true=0.01 * f, rho_true=0.0)["probability"]
            pb.append({"test": test, "level": alpha, "factor": f, "p_nominal": p_nominal, "p_wrong": p_wrong,
                       "failure_probability": agreement_failure_probability(p_wrong, p_nominal, 4000)})
    out["agreement_failure"] = pb
    # Part C
    blocks = 200
    sim_rows = []
    p_nominal = rejection_probability("pd.binomial", 1000, 0.01, 0.05, pd_true=0.01, rho_true=0.0)["probability"]
    for f in (1.0, 1.05, 1.10):
        gen = DefaultCounts(1000, 0.01 * f, pd_forecast=0.01)
        flagged = 0
        rates = []
        for b in range(blocks):
            seed = int(np.random.SeedSequence([20261108, int(round(f * 100)), b]).generate_state(1)[0])
            sim = simulate("pd.binomial", gen, n_rep=4000, seed=seed, feed=feed_cell())
            r: Rate = sim.rates["p<0.05"]
            rates.append(r.rate)
            flagged += not agrees(r, p_nominal)
        sim_rows.append({"factor": f, "blocks": blocks, "flagged": flagged, "share_flagged": flagged / blocks,
                         "mean_rate": float(np.mean(rates)), "p_nominal": p_nominal})
    out["agreement_simulated"] = sim_rows
    common.write_json("instrument.json", out)
    print("flag probability per test at 4000:", per_test["4000"], "family of 21:", out["flag_probability_family_21"]["4000"])
    for r in pb:
        if r["test"] == "pd.binomial" and r["level"] == 0.05:
            print("binomial 5%: factor", r["factor"], "failure", round(r["failure_probability"], 4))
    for r in sim_rows:
        print("simulated", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
