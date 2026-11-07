"""Experiment 7: the dispersion of the hit count of wrapped runs and the size of the back-tests on them.

    python manuscripts/adaptive-conformal-recalibration-of-var/experiments/e7_dispersion.py

Why. The update ``a_{t+1} = clip(a_t + gamma (alpha - e_t))`` pins the running count of hits near its target (the identity of the
Theory section), so the count of a wrapped run can be less variable than a binomial count. The Kupiec and conditional coverage
p-values and the Wilson interval assume hits that are independent Bernoulli draws; applied to an under-dispersed count they accept
too easily. This script measures the effect and the size of the tests on wrapped runs whose true coverage is wrong.

Part A (from ``e5_generators.json``, no new draw). For the three models, four scenarios, two levels and the four methods of
experiment 5 (``unwrapped``, ``aci``, ``rolling``, ``tracker``): the mean hit rate over the 100 replications, its standard deviation across replications, the binomial standard deviation
``sqrt(p (1 - p) / H)`` at that mean rate for the ``H`` evaluation days of the scenario, and their ratio (a ratio below one is an
under-dispersed count). The pass rate of each is carried along.

Part B (new draws, independent of every other experiment). Independent returns ``c s t_5`` (``s`` the unit-variance factor) are
forecast by a model whose VaR is the unit-variance Student-t quantile at the working level, so the scale ratio ``c`` is the model's
error (``c`` = 1: the model is correct). Per level (1 %, 2.5 %), per ``c`` in {0.75, 1, 1.25, 1.5, 2} and per method (``unwrapped``;
``aci`` with gamma 0.005 and the band [0.001, 0.25]), ``REPS`` runs of ``H`` = 500 days. For every run the true hit probability
``p_run`` (the mean over the days of the probability that the loss exceeds the VaR at that day's working level) is known. Reported:
the mean true hit probability, the mean and standard deviation of the hit count, the binomial standard deviation of the count at
that probability, the share of runs that the engine's Kupiec test rejects, the same for the conditional coverage test, the share
that pass both, and, for the wrapped runs, the same three shares for independent Bernoulli hits drawn at the same mean true
probability (the reference an iid-based test is built for), and the share of the 95 % Wilson intervals of the hit rate that contain
the run's true hit probability. Rejecting a wrapped run whose true coverage is wrong is the power of the test; its gap to the
Bernoulli reference is the loss of power caused by the dependence of the hits that the update creates.

Seeds: ``numpy.random.default_rng([20261104, 7, level index, c index, stream])`` with stream 0 for the returns and 1 for the
Bernoulli reference; Part C uses ``[20261104, 8, window index, level index]``. Output: ``e7_dispersion.json``. A few minutes on one
core.

Part C (what the pass counts of the ten models become once the wrapped count is tested against its own null). For each stress window
length and level, ``NULL_REPS`` wrapped runs of a correctly specified model on independent returns give the distribution of the
wrapped hit count under the null. The two-sided p-value of a count is the total probability of the outcomes at most as likely as
it (the rule of the engine's exact Kupiec metric), with the binomial for an unwrapped count and the simulated wrapped null for a
wrapped one. The cells of experiment 2 (ten models, three stress windows, two levels) whose count passes this test (p at least
0.05) are counted for the unwrapped and for the wrapped runs, next to the engine's asymptotic Kupiec test on the same counts. This
is a coverage-only comparison (the independence part of the conditional coverage test is not recalibrated).

The p-values of Part B are computed by closed-form likelihood ratios (the formulas of the engine's ``kupiec_pof`` and
``christoffersen_independence``, chi-square with one and two degrees of freedom), checked against the engine on 300 runs to 1e-9
before the experiment starts (the engine's own call also hashes its input and takes 47 ms a run).
"""
from __future__ import annotations

import math
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402

NU = 5.0
H = 500
REPS = 4000
SCALES = (0.75, 1.0, 1.25, 1.5, 2.0)
HORIZON = {"no-shift": 500, "crisis-persistent": 500, "crash-decay": 100, "drift-up": 250}


def part_a() -> dict:
    e5 = common.load("e5_generators.json")
    by = {}
    for r in e5["rows"]:
        by.setdefault((r["scenario"], r["model"], r["alpha"], r["method"]), []).append(r)
    rows = []
    for (s, m, a, me), rs in by.items():
        h =np.array([x["hit_rate"] for x in rs])
        p = float(h.mean())
        n = HORIZON[s]
        bsd = math.sqrt(p * (1 - p) / n)
        rows.append({"scenario": s, "model": m, "alpha": a, "method": me, "days": n, "reps": len(rs), "hit_mean": p, "hit_sd": float(h.std(ddof=1)),
                     "binom_sd": bsd, "ratio": float(h.std(ddof=1) / bsd), "pass_rate": float(np.mean([x["passes"] for x in rs]))})
    return {"rows": rows}


def _xlogy(x, y):
    from scipy.special import xlogy

    return xlogy(x, y)


def pvalues(h: np.ndarray, alpha: float) -> dict:
    """Kupiec, independence and conditional coverage p-values of every row of the boolean matrix ``h`` (NaN for the last two where
    the engine does not evaluate them: no hit, or only hits)."""
    from scipy import stats

    t = h.shape[1]
    x = h.sum(axis=1).astype(float)
    pi = x / t
    lr_pof = -2.0 * ((t - x) * np.log(1 - alpha) + x * np.log(alpha) - _xlogy(t - x, 1 - pi) - _xlogy(x, pi))
    a, b = h[:, :-1], h[:, 1:]
    n00 = ((~a) & (~b)).sum(axis=1).astype(float)
    n01 = ((~a) & b).sum(axis=1).astype(float)
    n10 = (a & (~b)).sum(axis=1).astype(float)
    n11 = (a & b).sum(axis=1).astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        p01, p11 = n01 / (n00 + n01), n11 / (n10 + n11)
        pb = (n01 + n11) / (n00 + n01 + n10 + n11)
        lr_ind = -2.0 * ((n00 + n10) * np.log1p(-pb) + (n01 + n11) * np.log(pb) - _xlogy(n00, 1 - p01) - _xlogy(n01, p01)
                         - _xlogy(n10, 1 - p11) - _xlogy(n11, p11))
    lr_ind = np.where((x > 0) & (x < t), lr_ind, np.nan)
    return {"kupiec": stats.chi2.sf(lr_pof, 1), "independence": stats.chi2.sf(lr_ind, 1), "cc": stats.chi2.sf(lr_pof + lr_ind, 2)}


def check_against_engine(n: int = 300) -> float:
    """Largest absolute difference between the closed forms and the engine on ``n`` random hit rows (the run stops above 1e-9)."""
    from riskvalidation.validation import market as vm

    rng = np.random.default_rng([common.SEED_BOOT, 7, 99])
    worst = 0.0
    for alpha in common.LEVELS:
        h = rng.random((n // 2, H)) < alpha * rng.uniform(0.5, 2.5, size=(n // 2, 1))
        pv = pvalues(h, alpha)
        for i, row in enumerate(h):
            k = vm.kupiec_pof(row.astype(int), alpha).p_value
            c = vm.christoffersen_conditional_coverage(row.astype(int), alpha).p_value
            worst = max(worst, abs(k - pv["kupiec"][i]))
            if c is not None and c == c:
                worst = max(worst, abs(c - pv["cc"][i]))
            elif not np.isnan(pv["cc"][i]):
                raise RuntimeError("the engine does not evaluate a row that the closed form evaluates")
    if worst > 1e-9:
        raise RuntimeError(f"closed-form tests differ from the engine by {worst}")
    return worst


def _rates(h: np.ndarray, alpha: float) -> dict:
    pv = pvalues(h, alpha)
    ok = ~np.isnan(pv["cc"])
    n = h.shape[0]
    return {"kupiec_reject": float(np.sum(ok & (pv["kupiec"] < common.PASS_P)) / n), "cc_reject": float(np.sum(ok & (pv["cc"] < common.PASS_P)) / n),
            "pass": float(np.sum(ok & (pv["kupiec"] >= common.PASS_P) & (pv["cc"] >= common.PASS_P)) / n), "undefined": float(np.mean(~ok))}


def part_b() -> dict:
    from scipy import stats

    s = math.sqrt((NU - 2) / NU)
    qf = lambda a: s * stats.t.ppf(a, NU)                          # noqa: E731  unit-variance quantile (return convention)
    Ff = lambda x: stats.t.cdf(x / s, NU)                          # noqa: E731
    rows = []
    for li, alpha in enumerate(common.LEVELS):
        for ci, c in enumerate(SCALES):
            rng = np.random.default_rng([common.SEED_BOOT, 7, li, ci, 0])
            y = c * s * rng.standard_t(NU, size=(REPS, H))
            ref_rng = np.random.default_rng([common.SEED_BOOT, 7, li, ci, 1])
            for method in ("unwrapped", "aci"):
                lev = np.full(REPS, alpha)
                hits = np.empty((REPS, H), dtype=bool)
                p_day = np.empty((REPS, H))
                for t in range(H):
                    v = qf(lev)
                    hits[:, t] = y[:, t] < v
                    p_day[:, t] = Ff(v / c)
                    if method == "aci":
                        lev = np.clip(lev + common.GAMMA * (alpha - hits[:, t]), common.LEVEL_MIN, common.LEVEL_MAX)
                p_run = p_day.mean(axis=1)
                cnt = hits.sum(axis=1)
                p_mean = float(p_run.mean())
                bsd = math.sqrt(H * p_mean * (1 - p_mean))
                lo_hi = np.array([common.wilson(int(k), H) for k in cnt])
                row = {"alpha": alpha, "scale": c, "method": method, "reps": REPS, "days": H, "true_hit_prob": p_mean,
                       "count_mean": float(cnt.mean()), "count_sd": float(cnt.std(ddof=1)), "binom_count_sd": bsd,
                       "sd_ratio": float(cnt.std(ddof=1) / bsd), "tests": _rates(hits, alpha),
                       "wilson_contains_truth": float(np.mean((lo_hi[:, 0] <= p_run) & (p_run <= lo_hi[:, 1])))}
                if method == "aci":
                    ref = ref_rng.random((REPS, H)) < p_mean
                    row["bernoulli_reference"] = {"count_sd": float(ref.sum(axis=1).std(ddof=1)), "tests": _rates(ref, alpha)}
                rows.append(row)
    return {"rows": rows, "scales": list(SCALES), "reps": REPS, "days": H}


NULL_REPS = 40000


def wrapped_null_counts(n_days: int, alpha: float, wi: int, li: int) -> np.ndarray:
    """Hit counts of ``NULL_REPS`` wrapped runs of a correct model on independent returns, ``n_days`` days."""
    from scipy import stats

    s = math.sqrt((NU - 2) / NU)
    rng = np.random.default_rng([common.SEED_BOOT, 8, wi, li])
    lev = np.full(NULL_REPS, alpha)
    cnt = np.zeros(NULL_REPS, dtype=int)
    for _ in range(n_days):
        v = s * stats.t.ppf(lev, NU)
        hit = s * rng.standard_t(NU, size=NULL_REPS) < v
        cnt += hit
        lev = np.clip(lev + common.GAMMA * (alpha - hit), common.LEVEL_MIN, common.LEVEL_MAX)
    return cnt


def two_sided(pmf: np.ndarray, k: int) -> float:
    """Total probability of the outcomes at most as likely as ``k`` (the rule of the engine's exact Kupiec metric)."""
    return float(min(1.0, pmf[pmf <= pmf[k] * (1.0 + 1e-7)].sum()))


def part_c() -> dict:
    from scipy import stats

    rows = [r for r in common.load("e2_wrap_ladder.json")["rows"] if r["window"] in common.STRESS]
    nulls, info = {}, {}
    for wi, w in enumerate(common.STRESS):
        n_days = next(r["n_days"] for r in rows if r["window"] == w)
        for li, alpha in enumerate(common.LEVELS):
            c = wrapped_null_counts(n_days, alpha, wi, li)
            nulls[(w, alpha)] = np.bincount(c, minlength=n_days + 1) / c.size
            info[f"{w}|{alpha}"] = {"n_days": n_days, "null_count_mean": float(c.mean()), "null_count_sd": float(c.std(ddof=1)),
                                    "binom_count_sd": math.sqrt(n_days * alpha * (1 - alpha))}
    out = {"cells": len(rows), "null_reps": NULL_REPS, "null": info, "unwrapped_exact": 0, "wrapped_exact_binomial": 0, "wrapped_calibrated": 0,
           "unwrapped_asymptotic_kupiec": 0, "wrapped_asymptotic_kupiec": 0, "flips": []}
    for r in rows:
        w, a, n = r["window"], r["alpha"], r["n_days"]
        pb = stats.binom.pmf(np.arange(n + 1), n, a)
        ku, kw = r["unwrapped"]["n_hits"], r["wrapped"]["n_hits"]
        pu, pw, pc = two_sided(pb, ku), two_sided(pb, kw), two_sided(nulls[(w, a)], kw)
        out["unwrapped_exact"] += pu >= common.PASS_P
        out["wrapped_exact_binomial"] += pw >= common.PASS_P
        out["wrapped_calibrated"] += pc >= common.PASS_P
        out["unwrapped_asymptotic_kupiec"] += r["unwrapped"]["kupiec_p"] >= common.PASS_P
        out["wrapped_asymptotic_kupiec"] += r["wrapped"]["kupiec_p"] >= common.PASS_P
        if (pw >= common.PASS_P) != (pc >= common.PASS_P):
            out["flips"].append({"window": w, "model": r["model"], "alpha": a, "hits": kw, "p_binomial": pw, "p_calibrated": pc})
        if r["model"] in common.WRAPPED3:
            h = out.setdefault("h1", {"cells": 0, "unwrapped_exact": 0, "wrapped_calibrated": 0, "gain_cells": 0, "gain_cells_calibrated": 0, "gain": {}})
            h["cells"] += 1
            h["unwrapped_exact"] += pu >= common.PASS_P
            h["wrapped_calibrated"] += pc >= common.PASS_P
            g = h["gain"].setdefault(f"{r['model']}|{a}", [0, 0, 0])      # windows passed: unwrapped (asymptotic), wrapped (asymptotic), calibrated-gain
            g[0] += common.passes(r["unwrapped"])
            g[1] += common.passes(r["wrapped"])
            g[2] += (pc >= common.PASS_P) - (pu >= common.PASS_P)
    # H1 counts a cell (model, level) when the wrapped model passes in at least one more stress window; the calibrated version counts
    # the windows passed by the coverage-only calibrated test (unwrapped: exact binomial; wrapped: its own null), the score condition unchanged
    out["h1"]["gain_cells"] = sum(1 for g in out["h1"]["gain"].values() if g[1] - g[0] >= 1)
    out["h1"]["gain_cells_calibrated"] = sum(1 for g in out["h1"]["gain"].values() if g[2] >= 1)
    return out


def main() -> int:
    t0 = time.perf_counter()
    print(f"closed-form tests agree with the engine to {check_against_engine():.1e}", flush=True)
    a = part_a()
    print(f"part A done at {time.perf_counter() - t0:.0f}s", flush=True)
    b = part_b()
    print(f"part B done at {time.perf_counter() - t0:.0f}s", flush=True)
    c = part_c()
    p = common.dump({"A": a, "B": b, "C": c, "seed_base": common.SEED_BOOT, "seconds": round(time.perf_counter() - t0)}, "e7_dispersion.json")
    print("wrote", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
