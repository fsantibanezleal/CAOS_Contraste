"""Experiment 6: numerical checks of the propositions of the Theory section.

    python manuscripts/adaptive-conformal-recalibration-of-var/experiments/e6_theory.py

Part A (Proposition 1, the coverage identity with clipping). On the 18 real paths of experiment 2 (HS-250, GARCH-t and FHS, three
stress windows, two levels) the identity ``a_T - a_1 = gamma sum_{k<T}(alpha - err_k) - C`` holds to rounding, where ``C`` is the
total amount the band cut off, and the deterministic bound ``|mean err - alpha| <= (|a_T - a_1| + |C|) / (gamma (T - 1))`` and its
consequence ``<= (L_max - L_min) / (gamma (T - 1)) + (n_clip / (T - 1)) max(alpha, 1 - alpha)`` hold.

Part B (Proposition 2, a coverage guarantee does not carry independence). A hit sequence of clusters of ``m`` consecutive hits
followed by ``q = m (1 - alpha) / alpha`` quiet days has frequency exactly ``alpha``; the engine's Kupiec test accepts it and its
Christoffersen independence test rejects it; the level path of the recursion on it stays inside the band when
``gamma m (1 - alpha) <= alpha - L_min``.

Part C (Propositions 3 and 4, the fixed point, the repairable scale range and the spread of the level). A model whose VaR is the
quantile of a unit-variance Student-t(5) at the working level, facing returns that are ``c`` times larger in scale, is wrapped over
independent draws (50 replications of 5,000 days per cell, seeds 20261104 + 777000 + replication). The mean working level after a
burn-in of 1,000 days is compared with ``a* = F(c q(alpha))``, the hit rate with ``alpha`` and the standard deviation of the
level with ``sqrt(gamma alpha (1 - alpha) / (2 F'(a*)))``; the scale ratio above which the band binds is ``q(L_min) / q(alpha)``.

Part D (Proposition 5, the ES carried by the working level). The ratio of the wrapped ES to the true ES at the fixed point,
``e(a*) / (c e(alpha))``, is computed for Student-t laws with 3, 5, 10 and 30 degrees of freedom; it equals one for a Pareto tail.
Output: ``e6_theory.json``.
"""
from __future__ import annotations

import math
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402

LMIN, LMAX, GAMMA = common.LEVEL_MIN, common.LEVEL_MAX, common.GAMMA


def part_a() -> dict:
    d = common.load("e2_wrap_ladder.json")
    out = []
    for key, p in sorted(d["paths"].items()):
        w, m, a = key.split("|")
        alpha = float(a)
        lev = np.array(p["levels"])
        hit = np.zeros(lev.size)
        hit[p["hit_days"]] = 1.0
        T = lev.size
        raw = lev[:-1] + GAMMA * (alpha - hit[:-1])
        cut = raw - lev[1:]                                     # signed amount the band removed on each update
        C = float(cut.sum())
        n_clip = int((np.abs(cut) > 1e-12).sum())
        identity = float(lev[-1] - lev[0] - (GAMMA * np.sum(alpha - hit[:-1]) - C))
        lhs = abs(float(hit[:-1].mean()) - alpha)
        b1 = (abs(lev[-1] - lev[0]) + abs(C)) / (GAMMA * (T - 1))
        b2 = (LMAX - LMIN) / (GAMMA * (T - 1)) + n_clip / (T - 1) * max(alpha, 1 - alpha)
        out.append({"window": w, "model": m, "alpha": alpha, "T": T, "n_clip": n_clip, "C": C, "identity_residual": identity,
                    "abs_coverage_error": lhs, "bound_exact": b1, "bound_simple": b2, "holds": bool(lhs <= b1 + 1e-12 and b1 <= b2 + 1e-12)})
    return {"rows": out, "all_hold": all(r["holds"] for r in out), "max_identity_residual": max(abs(r["identity_residual"]) for r in out)}


def part_b() -> dict:
    from riskvalidation.validation import market as vm

    rows = []
    for alpha, m, gamma in ((0.01, 2, 0.001), (0.01, 3, 0.001), (0.025, 2, 0.002), (0.025, 4, 0.002)):
        q = int(round(m * (1 - alpha) / alpha))
        period = m + q
        reps = 60
        hits = np.zeros(period * reps, dtype=int)
        for k in range(reps):
            hits[k * period:k * period + m] = 1
        lev, path = alpha, []
        for h in hits:
            path.append(lev)
            lev = min(max(lev + gamma * (alpha - h), LMIN), LMAX)
        kp = vm.kupiec_pof(hits, alpha)
        ind = vm.christoffersen_independence(hits, alpha)
        cc = vm.christoffersen_conditional_coverage(hits, alpha)
        n01 = 1.0 / q * 0 + 1.0                                    # one onset per period
        pi01, pi11 = 1.0 / (q + 0.0), (m - 1) / m
        rows.append({"alpha": alpha, "cluster": m, "quiet_days": q, "gamma": gamma, "T": int(hits.size), "frequency": float(hits.mean()),
                     "kupiec_p": float(kp.p_value), "independence_p": float(ind.p_value), "cc_p": float(cc.p_value),
                     "pi01": pi01, "pi11": pi11, "level_min": float(min(path)), "level_max": float(max(path)),
                     "in_band": bool(min(path) > LMIN and max(path) < LMAX), "gamma_m_limit": (alpha - LMIN) / (m * (1 - alpha))})
    return {"rows": rows}


def part_c() -> dict:
    from scipy import stats

    nu = 5.0
    s = math.sqrt((nu - 2) / nu)
    qf = lambda a: s * stats.t.ppf(a, nu)                           # noqa: E731  unit-variance quantile
    Ff = lambda x: stats.t.cdf(x / s, nu)                           # noqa: E731
    ff = lambda x: stats.t.pdf(x / s, nu) / s                       # noqa: E731
    rows = []
    for alpha in common.LEVELS:
        for c in (1.0, 1.25, 1.5, 1.75, 2.0, 3.0):
            a_star = float(Ff(c * qf(alpha)))
            cmax = float(qf(LMIN) / qf(alpha))
            in_band = bool(LMIN < a_star < LMAX)
            # F(a) = P(hit | level a) = Ff(qf(a) / c); slope at the fixed point (a* = Ff(c qf(alpha)) gives qf(a*) = c qf(alpha))
            slope = float(ff(qf(alpha)) / (c * ff(c * qf(alpha)))) if in_band else float("nan")
            sd_pred = math.sqrt(GAMMA * alpha * (1 - alpha) / (2 * slope)) if in_band else float("nan")
            means, sds, hit_rates, clip, gaps, cuts = [], [], [], [], [], []
            for k in range(50):
                rng = np.random.default_rng(common.SEED_BOOT + 777000 + k)
                y = c * s * rng.standard_t(nu, size=5000)
                lev = alpha
                lv = np.empty(y.size)
                hit = np.empty(y.size)
                nclip = 0
                cut_sum = 0.0
                for t in range(y.size):
                    lv[t] = lev
                    hit[t] = y[t] < qf(lev)
                    raw = lev + GAMMA * (alpha - hit[t])
                    lev = min(max(raw, LMIN), LMAX)
                    nclip += lev != raw
                    cut_sum += raw - lev
                means.append(lv[1000:].mean())
                sds.append(lv[1000:].std())
                hit_rates.append(hit[1000:].mean())
                clip.append(nclip / y.size)
                gaps.append(abs((hit.mean() - alpha) - (alpha - lev - cut_sum) / (GAMMA * y.size)))
                cuts.append(-cut_sum / (GAMMA * y.size))
            rows.append({"alpha": alpha, "scale_ratio": c, "a_star": a_star, "c_max": cmax, "in_band": in_band, "slope": slope,
                         "level_mean": float(np.mean(means)), "level_mean_se": float(np.std(means, ddof=1) / math.sqrt(len(means))),
                         "level_sd": float(np.mean(sds)), "level_sd_pred": sd_pred, "hit_rate": float(np.mean(hit_rates)),
                         "hit_rate_se": float(np.std(hit_rates, ddof=1) / math.sqrt(len(hit_rates))), "clipped_share": float(np.mean(clip)), "cut_over_gamma": float(np.mean(cuts)),
                         "identity_gap": float(np.max(gaps))})
    return {"nu": nu, "reps": 50, "days": 5000, "burn_in": 1000, "rows": rows}


def part_d() -> dict:
    from scipy import stats

    rows = []
    for nu in (3.0, 5.0, 10.0, 30.0):
        s = math.sqrt((nu - 2) / nu)

        def q(a):
            return s * stats.t.ppf(a, nu)

        def e(a):
            t = stats.t.ppf(a, nu)
            return s * (-stats.t.pdf(t, nu) / a * (nu + t * t) / (nu - 1))
        for alpha in common.LEVELS:
            for c in (1.5, 2.0):
                a_star = float(stats.t.cdf(c * stats.t.ppf(alpha, nu), nu))
                rows.append({"nu": nu, "alpha": alpha, "scale_ratio": c, "a_star": a_star,
                             "es_ratio": float(e(a_star) / (c * e(alpha))), "es_over_var_target": float(e(alpha) / q(alpha)),
                             "es_over_var_fixed_point": float(e(a_star) / q(a_star))})
    return {"rows": rows}


def main() -> int:
    out = {"A": part_a(), "B": part_b(), "C": part_c(), "D": part_d()}
    p = common.dump(out, "e6_theory.json")
    print("wrote", p, "| part A all hold:", out["A"]["all_hold"], "max identity residual", out["A"]["max_identity_residual"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
