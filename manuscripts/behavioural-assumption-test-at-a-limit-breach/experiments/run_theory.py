"""Experiment 4: numerical checks of the propositions of the Theory section.

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/behavioural-assumption-test-at-a-limit-breach/experiments/run_theory.py

(a) the false-flag probability ``1 - C(n-k, m) / C(n, m)`` of the proposed test when the breach dates are placed uniformly among the dates, against a
simulation of placements; (b) the same probability ``E[1 - (1-lambda)^m]`` for the changes of the stated regime of Experiment 2, with the number ``m`` of breach
dates drawn from the seeds of that experiment, against the false-flag rates that experiment measured; (c) the one-sided Fisher p-value of change against breach
equals the permutation p-value of the proposed statistic, by enumeration of the placements; (d) the closed forms of the tolerance rule on Gaussian changes (the
calibrated tolerance, the false-flag rate and the power) against simulation; (e) the closed form again under three further seeds on the cell that departs most; (f) the finite-sample validity of the conformal tolerance over 500 repeated
calibrations. Writes ``results_theory.json``.
"""
from __future__ import annotations

import itertools
import json
import math
import pathlib

import numpy as np
from scipy import stats

import core
import run_stated

HERE = pathlib.Path(__file__).resolve().parent
SEED = 5521


def check_hypergeometric() -> dict:
    rng = np.random.default_rng([SEED, 1])
    rows = []
    n = core.T_DEFAULT - 1
    for k in (1, 2, 3, 5):
        for m in (1, 2, 4, 6):
            reps = 100_000
            hit = 0
            for _ in range(reps):
                chg = np.zeros(n, dtype=bool)
                chg[rng.choice(n, k, replace=False)] = True
                brk = np.zeros(n, dtype=bool)
                brk[rng.choice(n, m, replace=False)] = True
                hit += bool((chg & brk).any())
            p_sim, lo, hi = core.wilson(hit, reps)
            rows.append({"n": n, "k": k, "m": m, "formula": core.p_coincidence_hypergeometric(n, k, m), "simulated": p_sim, "lo": lo, "hi": hi})
    ok = all(r["lo"] - 1e-12 <= r["formula"] <= r["hi"] + 1e-12 for r in rows)
    return {"rows": rows, "formula_inside_interval": ok, "reps": 100_000}


def check_bernoulli_against_experiment_2() -> dict:
    """The predicted false-flag rate of the proposed test on the stated regime, ``E_m[1 - (1 - lam)^m]``, with the ``m`` of the very histories of Experiment 2."""
    res2 = json.loads((HERE / "results_stated.json").read_text(encoding="utf-8"))
    rows = []
    cell = 0
    for cellinfo in res2["cells"]:
        lam, prev, pi_m = cellinfo["lam"], cellinfo["prevalence"], cellinfo["pi_m"]
        ms = []
        for blk in range(run_stated.BLOCKS):
            for i in range(res2["per_block"]):
                rng = np.random.default_rng([run_stated.SEED, cell, blk, i])
                b = core.breach_chain(rng, core.T_DEFAULT, prev)
                ms.append(int(b[1:].sum()))
        pred = float(np.mean([1.0 - (1.0 - lam) ** m for m in ms]))
        obs = cellinfo["rates"]["null"]["engine"]
        rows.append({"lam": lam, "prevalence": prev, "pi_m": pi_m, "predicted": pred, "observed": obs["rate"], "lo": obs["lo"], "hi": obs["hi"],
                     "abs_diff": abs(pred - obs["rate"]), "mean_m": float(np.mean(ms))})
        cell += 1
    return {"rows": rows, "max_abs_diff": max(r["abs_diff"] for r in rows)}


def check_bernoulli_extra_seeds() -> dict:
    """The cell of Experiment 2 whose measured false-flag rate lies furthest from the closed form, replicated under three further seeds of 10,000 histories."""
    lam, prev = 0.05, 0.5
    rows = []
    for seed in (1, 2, 3):
        hit, pred = 0, []
        for i in range(10_000):
            rng = np.random.default_rng([seed, i])
            b = core.breach_chain(rng, core.T_DEFAULT, prev)
            draws = core.stated_draws(rng, core.T_DEFAULT, lam)
            hit += core.closed_form_count(core.stated_history(draws, None), b) > 0
            pred.append(1.0 - (1.0 - lam) ** int(b[1:].sum()))
        p, lo, hi = core.wilson(hit, 10_000)
        rows.append({"seed": seed, "observed": p, "lo": lo, "hi": hi, "predicted": float(np.mean(pred))})
    return {"lam": lam, "prevalence": prev, "rows": rows}


def check_fisher_is_permutation() -> dict:
    """Over random histories the one-sided Fisher p-value of change against breach equals the exact permutation p-value of the proposed statistic."""
    rng = np.random.default_rng([SEED, 3])
    worst = 0.0
    n_hist = 2000
    for _ in range(n_hist):
        t = int(rng.integers(5, 10))
        n = t - 1
        theta = np.concatenate([[4.0], 4.0 + np.cumsum((rng.random(n) < rng.uniform(0.2, 0.8)) * rng.uniform(0.1, 1.0, n))])
        m = int(rng.integers(1, n))
        brk = np.zeros(n, dtype=bool)
        brk[rng.choice(n, m, replace=False)] = True
        b = np.concatenate([[False], brk])
        chg = np.diff(theta) != 0
        obs = int((chg & brk).sum())
        counts = [int((chg & np.isin(np.arange(n), sub)).sum()) for sub in itertools.combinations(range(n), m)]
        perm_p = float(np.mean([c >= obs for c in counts]))
        tab = [[obs, int((chg & ~brk).sum())], [int((~chg & brk).sum()), int((~chg & ~brk).sum())]]
        fisher_p = float(stats.fisher_exact(tab, alternative="greater")[1])
        worst = max(worst, abs(perm_p - fisher_p))
        assert core.closed_form_count(theta, b) == obs
    return {"histories": n_hist, "max_abs_difference": worst}


def tolerance_closed_forms() -> dict:
    """Gaussian changes ``N(0, s^2)`` at ``n`` dates, ``m`` of them breach dates; one planted shift ``mu`` at one breach date. The closed forms of the tolerance
    rule ``peak > delta`` against simulation."""
    rng = np.random.default_rng([SEED, 4])
    n, alpha, reps = core.T_DEFAULT - 1, core.ALPHA, 200_000
    out = []
    for m in (1, 3, 6):
        q0 = 1.0 - (1.0 - alpha) ** (1.0 / m)         # per-date exceedance for a family-wise size alpha
        delta = float(stats.norm.ppf(1.0 - q0 / 2.0))   # in units of the standard deviation of a change
        row = {"m": m, "delta_over_sigma": delta, "points": []}
        null = np.abs(rng.standard_normal((reps, m))).max(axis=1) > delta
        p, lo, hi = core.wilson(int(null.sum()), reps)
        row["null_formula"], row["null_simulated"], row["null_lo"], row["null_hi"] = alpha, p, lo, hi
        for mu in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0):
            q_mu = float(1.0 - stats.norm.cdf(delta - mu) + stats.norm.cdf(-delta - mu))
            formula = 1.0 - (1.0 - q0) ** (m - 1) * (1.0 - q_mu)
            x = np.abs(rng.standard_normal((reps, m)))
            x[:, 0] = np.abs(mu + rng.standard_normal(reps))
            sim = float((x.max(axis=1) > delta).mean())
            row["points"].append({"mu_over_sigma": mu, "formula": formula, "simulated": sim})
        out.append(row)
    return {"rows": out, "reps": reps, "alpha": alpha}


def conformal_validity() -> dict:
    """500 independent calibrations of 1,000 null histories each, every one evaluated on 20,000 fresh null histories of the same law (Gaussian peaks over ``m`` = 3)."""
    rng = np.random.default_rng([SEED, 5])
    n_cal, n_test, calibrations, alpha = 1000, 20_000, 500, core.ALPHA
    rates = []
    for _ in range(calibrations):
        cal = np.abs(rng.standard_normal((n_cal, 3))).max(axis=1)
        thr = core.conformal_threshold(cal, alpha)
        test = np.abs(rng.standard_normal((n_test, 3))).max(axis=1)
        rates.append(float((test > thr).mean()))
    k = math.ceil((n_cal + 1) * (1.0 - alpha))
    return {"n_cal": n_cal, "n_test": n_test, "calibrations": calibrations, "alpha": alpha, "rates": rates, "mean_rate": float(np.mean(rates)),
            "q025": float(np.quantile(rates, 0.025)), "q975": float(np.quantile(rates, 0.975)), "max_rate": float(np.max(rates)),
            "theoretical_mean": 1.0 - k / (n_cal + 1), "share_above_alpha": float(np.mean(np.array(rates) > alpha))}


def main() -> None:
    res = {"seed": SEED, "hypergeometric": check_hypergeometric(), "bernoulli_vs_experiment_2": check_bernoulli_against_experiment_2(),
           "bernoulli_extra_seeds": check_bernoulli_extra_seeds(),
           "fisher_is_permutation": check_fisher_is_permutation(), "tolerance_closed_forms": tolerance_closed_forms(), "conformal": conformal_validity()}
    (HERE / "results_theory.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("hypergeometric inside interval:", res["hypergeometric"]["formula_inside_interval"], "| bernoulli max diff:", round(res["bernoulli_vs_experiment_2"]["max_abs_diff"], 4),
          "| fisher=permutation max diff:", res["fisher_is_permutation"]["max_abs_difference"], "| conformal mean:", round(res["conformal"]["mean_rate"], 4))


if __name__ == "__main__":
    main()
