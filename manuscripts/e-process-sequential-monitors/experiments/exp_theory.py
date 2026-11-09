"""The numbers the Theory section reads: exact enumerations and closed forms, computed from the engine and from ``scipy``.

1. ``null_expectation``: the exact null expectation of every e-process at every time ``t`` by full enumeration of the
   2^T hit sequences (T = 12, alpha = 0.2), for the engine's rate monitor (two-sided, upper, lower), the clustering monitor,
   their average, and the two e-processes written in this folder. The maximum absolute departure from 1 is the check that
   the processes are e-processes to floating-point accuracy.
2. ``product_counterexample``: the same enumeration for the product of the rate and the clustering monitors read on one
   stream (T = 10, alpha = 0.2), and for the engine's PD monitor of two grades with identical defaults combined by product
   and by average (one step, three obligors per grade, PD 0.3): the product has an expectation above 1, the average has 1.
3. ``kl``: the Kullback-Leibler divergence of a Bernoulli(m alpha) hit stream from the null for the severities of the
   experiments, the growth rate of the matched single alternative, and of the mixture's best alternative (Proposition on
   the growth rate), and the implied time to reach the threshold ``log 20``.
4. ``size_matched_power``: at the horizon of one reading (250 days, alpha = 1 %), the exact size and power of the Kupiec test
   (its rejection region under the null, by enumeration of the Binomial(250, alpha) counts), the exact randomised
   Neyman-Pearson power at the size of the Kupiec test and at the size the e-process spends by day 250 (read from
   ``results_hits.json``), which bounds every test of that size, the e-process included.
5. ``exact_spending``: the exact null probability that the rate monitor (two-sided and upper) and the single alternative at
   three times alpha have rejected by day 250 and by day 1,000, by dynamic programming over (t, S_t) (the process depends on
   the stream only through them); it replaces the Monte Carlo share of 2,000 streams as the size the power bound is taken at.
6. ``one_shot_sizes``: the exact size at day 250 of the Kupiec test and of the traffic light (the binomial tails).

    python manuscripts/e-process-sequential-monitors/experiments/exp_theory.py
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import pathlib
import sys
from importlib import metadata

import numpy as np
from scipy import stats

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as cm  # noqa: E402

GRID = (0.25, 0.5, 1.5, 2.0, 3.0, 4.0, 6.0, 10.0)
FACTORS = (1.5, 2.0, 3.0, 4.0, 6.0, 10.0)


def bern_kl(p: float, q: float) -> float:
    """KL(Bernoulli(p) || Bernoulli(q)) in nats."""
    return p * math.log(p / q) + (1 - p) * math.log((1 - p) / (1 - q))


def enumerate_hits(t: int) -> np.ndarray:
    return np.array(list(itertools.product([0, 1], repeat=t)), dtype=bool)


def null_probs(h: np.ndarray, p: float) -> np.ndarray:
    k = h.sum(axis=1)
    return p ** k * (1 - p) ** (h.shape[1] - k)


def null_expectation() -> dict:
    alpha, t = 0.2, 12
    h = enumerate_hits(t)
    pr = null_probs(h, alpha)
    paths = {
        "rate_two_sided": cm.engine_paths(h, alpha), "rate_upper": cm.engine_paths(h, alpha, direction="upper"),
        "rate_lower": cm.engine_paths(h, alpha, direction="lower"), "cluster": cm.engine_cluster_paths(h, alpha),
        "battery_average": cm.engine_battery_paths(h, alpha), "wwz_grel": cm.wwz_log_e(h, alpha),
        "beta_mixture": cm.beta_mixture_log_e(h, alpha),
    }
    out = {}
    for name, lp in paths.items():
        e = pr @ np.exp(lp)
        out[name] = {"max_abs_departure_from_one": float(np.abs(e - 1.0).max()), "expectation_at_t12": float(e[-1])}
    return {"alpha": alpha, "T": t, "sequences": int(h.shape[0]), "processes": out}


def product_counterexample() -> dict:
    from riskvalidation.validation.sequential import pd_grade_eprocess

    alpha, t = 0.2, 10
    h = enumerate_hits(t)
    pr = null_probs(h, alpha)
    prod = np.exp(cm.engine_paths(h, alpha) + cm.engine_cluster_paths(h, alpha))
    e_prod = pr @ prod
    # two grades with identical defaults (perfect dependence), one step, three obligors per grade, PD 0.3
    n_obl, p = 3, 0.3
    probs = stats.binom.pmf(np.arange(n_obl + 1), n_obl, p)
    res = {}
    for combine in ("product", "average"):
        vals = []
        for d in range(n_obl + 1):
            r = pd_grade_eprocess(np.array([[d, d]], dtype=float), np.full((1, 2), float(n_obl)), np.array([p, p]), combine=combine)
            vals.append(float(np.exp(r.log_e[-1])))
        res[combine] = float(probs @ np.array(vals))
    ever = (cm.engine_paths(h, alpha) + cm.engine_cluster_paths(h, alpha) >= cm.CROSS).any(axis=1)
    return {"hits_rate_times_cluster": {"alpha": alpha, "T": t, "expectation_by_t": [float(x) for x in e_prod],
                                         "max_expectation": float(e_prod.max()),
                                         "reject_probability_by_day_10": float(pr @ ever)},
            "pd_two_identical_grades": {"obligors": n_obl, "pd": p, "expectation_product": res["product"],
                                        "expectation_average": res["average"]}}


def kl_block() -> dict:
    alpha = cm.ALPHA
    thr = math.log(1 / cm.LEVEL)
    k = len(GRID)
    rows = []
    for f in FACTORS:
        p = f * alpha
        kl = bern_kl(p, alpha)
        # growth rate of the mixture: its best alternative j has per-day log growth KL(p||alpha) - KL(p||p_j)
        gaps = [(m, kl - bern_kl(p, m * alpha)) for m in GRID if m * alpha < 1.0]
        m_best, g_best = max(gaps, key=lambda x: x[1])
        rows.append({"factor": f, "hit_rate": p, "kl_vs_null": kl, "best_alternative": m_best, "mixture_growth": g_best,
                     "sprt_time": thr / kl, "mixture_time_bound": (thr + math.log(k)) / g_best,
                     "mixture_time_no_penalty": thr / g_best})
    return {"alpha": alpha, "threshold_log": thr, "grid": list(GRID), "rows": rows}


def exact_spending() -> dict:
    """Exact null rejection probability by day 250 and by day 1,000 of the engine's rate monitors and of the single alternative."""
    out = {}
    for name, kw in (("rate_two_sided", {}), ("rate_upper", {"direction": "upper"}), ("single_3", {"multipliers": [3.0]})):
        r = cm.exact_rejection_probability(cm.ALPHA, cm.HORIZON, cm.engine_multipliers(cm.ALPHA, **kw))
        out[name] = {"multipliers": cm.engine_multipliers(cm.ALPHA, **kw), "by_250": r[cm.WINDOW - 1], "by_1000": r[-1]}
    return out


def one_shot_sizes(n: int, alpha: float) -> dict:
    """Exact size at day ``n`` of the Kupiec test (two-sided) and of the traffic light (non-green count)."""
    ks = np.arange(n + 1)
    pm0 = stats.binom.pmf(ks, n, alpha)
    kup = float(pm0[stats.chi2.sf(cm.kupiec_lr(ks.astype(float), np.full(n + 1, float(n)), alpha), 1) < cm.LEVEL].sum())
    k_min = cm.traffic_light_days(np.zeros((1, n + 50), dtype=bool), window=n)[1]
    return {"n": n, "alpha": alpha, "kupiec": kup, "traffic_light": float(stats.binom.sf(k_min - 1, n, alpha)),
            "traffic_light_first_non_green_count": int(k_min)}


def exact_size_power(n: int, alpha: float, factors: tuple[float, ...], e_size_by_window: float, single3_size: float, upper_size: float) -> dict:
    ks = np.arange(n + 1)
    pm0 = stats.binom.pmf(ks, n, alpha)
    lr = cm.kupiec_lr(ks.astype(float), np.full(n + 1, float(n)), alpha)
    kup_region = stats.chi2.sf(lr, 1) < cm.LEVEL
    kup_size = float(pm0[kup_region].sum())
    # upper-tail region of the Kupiec test (the back-test cares about too many hits)
    upper_region = kup_region & (ks > n * alpha)
    out: dict = {"n": n, "alpha": alpha, "kupiec_size": kup_size, "kupiec_upper_size": float(pm0[upper_region].sum()),
                 "kupiec_smallest_rejecting_count": int(ks[upper_region].min()), "e_process_size_by_window": e_size_by_window,
                 "single_3_size_by_window": single3_size, "e_process_upper_size_by_window": upper_size, "factors": {}}

    def np_power(p1: float, size: float) -> float:
        """Randomised Neyman-Pearson power of the most powerful test of Bin(n, alpha) against Bin(n, p1) at ``size``."""
        pm1 = stats.binom.pmf(ks, n, p1)
        order = np.argsort(-(pm1 / np.maximum(pm0, 1e-300)))
        spent, power = 0.0, 0.0
        for k in order:
            take = min(1.0, (size - spent) / pm0[k]) if pm0[k] > 0 else 1.0
            if take <= 0:
                break
            spent += take * pm0[k]
            power += take * pm1[k]
            if spent >= size - 1e-15:
                break
        return float(power)

    for f in factors:
        p1 = f * alpha
        pm1 = stats.binom.pmf(ks, n, p1)
        out["factors"][f"x{f:g}"] = {
            "kupiec_power": float(pm1[kup_region].sum()),
            "kupiec_upper_power": float(pm1[upper_region].sum()),
            "np_power_at_kupiec_size": np_power(p1, kup_size),
            "np_power_at_e_process_size": np_power(p1, e_size_by_window),
            "np_power_at_five_percent": np_power(p1, cm.LEVEL),
            "np_power_at_single_3_size": np_power(p1, single3_size),
            "np_power_at_upper_size": np_power(p1, upper_size),
        }
    out["single_3_np_power_at_3"] = out["factors"]["x3"]["np_power_at_single_3_size"]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hits", type=pathlib.Path, default=HERE / "results_hits.json")
    ap.add_argument("--out", type=pathlib.Path, default=HERE / "results_theory.json")
    args = ap.parse_args()
    hits = json.loads(args.hits.read_text(encoding="utf-8"))
    e_size_mc = hits["scenarios"]["null"]["methods"]["e_rate"]["by"]
    spending = exact_spending()
    e_size_250 = spending["rate_two_sided"]["by_250"]
    result = {
        "meta": {"engine_version": metadata.version("riskvalidation"), "script": "experiments/exp_theory.py",
                 "e_process_size_source": "exact_spending.rate_two_sided.by_250 (dynamic programming)",
                 "e_process_size_monte_carlo": e_size_mc, "e_process_size_monte_carlo_source": "results_hits.json scenarios.null.methods.e_rate.by"},
        "null_expectation": null_expectation(),
        "product_counterexample": product_counterexample(),
        "kl": kl_block(),
        "exact_spending": spending,
        "one_shot_sizes": one_shot_sizes(cm.WINDOW, cm.ALPHA),
        "size_matched_power": exact_size_power(cm.WINDOW, cm.ALPHA, FACTORS, e_size_250, spending["single_3"]["by_250"], spending["rate_upper"]["by_250"]),
    }
    args.out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    ne = result["null_expectation"]["processes"]
    print({k: v["max_abs_departure_from_one"] for k, v in ne.items()})
    print(result["product_counterexample"])
    print(result["size_matched_power"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
