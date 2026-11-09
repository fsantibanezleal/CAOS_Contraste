"""Seed-to-seed spread of the delay and of the power cost at the severities the hypothesis is judged on.

The median detection day of the rate e-process at a hit rate three times alpha sits near the 250-day window, so one run of
2,000 streams cannot place it on either side. This script repeats the engine's rate monitor (two-sided, the configuration the
hypothesis was stated for, and upper-side), the traffic light and one Kupiec reading at day 250 on ``--seeds`` independent seed
sequences of ``--reps`` streams for the hit-rate factors 3 and 4 (the severities of the hypothesis), then reports the median of
each seed, their spread, the share of seeds whose median is below 250, the median of the pooled streams with a bootstrap
interval and the pooled paired power cost.

    python manuscripts/e-process-sequential-monitors/experiments/exp_x3_seeds.py
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
import time
from importlib import metadata

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as cm  # noqa: E402

BASE_SEED = 20261104
FACTORS = (3.0, 4.0)
MONITORS = {"": {}, "_upper": {"direction": "upper"}}


def summarise(days: list[np.ndarray], tl: list[np.ndarray], shot: list[np.ndarray], rng: np.random.Generator) -> dict:
    medians = [float(np.median(d)) for d in days]
    by = [float((d <= cm.WINDOW).mean()) for d in days]
    costs = [float(s.mean() - b) for s, b in zip(shot, by)]
    pooled, pooled_tl = np.concatenate(days), np.concatenate(tl)
    diff = np.concatenate(shot).astype(float) - (pooled <= cm.WINDOW).astype(float)
    lo, hi = cm.boot_median(pooled, rng, 2000)
    return {
        "seed_medians": medians, "seed_median_mean": float(np.mean(medians)), "seed_median_sd": float(np.std(medians, ddof=1)),
        "share_of_seeds_below_window": float(np.mean(np.array(medians) < cm.WINDOW)),
        "traffic_light_seed_medians": [float(np.median(t)) for t in tl],
        "pooled_n": int(pooled.size), "pooled_median": float(np.median(pooled)), "pooled_median_ci": [lo, hi],
        "pooled_share_by_window": float((pooled <= cm.WINDOW).mean()),
        "pooled_share_below_window_strict": float((pooled < cm.WINDOW).mean()),
        "pooled_traffic_light_median": float(np.median(pooled_tl)),
        "seed_power_costs": costs, "pooled_kupiec_power": float(np.concatenate(shot).mean()),
        "pooled_power_cost": float(diff.mean()), "pooled_power_cost_se": float(diff.std(ddof=1) / math.sqrt(diff.size)),
        "seed_power_cost_mean": float(np.mean(costs)), "seed_power_cost_sd": float(np.std(costs, ddof=1)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--out", type=pathlib.Path, default=HERE / "results_x3_seeds.json")
    args = ap.parse_args()
    t0 = time.time()
    rng = np.random.default_rng(np.random.SeedSequence([BASE_SEED, 779]))
    out: dict = {"meta": {"seeds": args.seeds, "reps": args.reps, "base_seed": BASE_SEED,
                          "seed_rule": "SeedSequence([base + 1000 * k, 500 + factor tag]), k = 1..seeds",
                          "alpha": cm.ALPHA, "horizon": cm.HORIZON, "engine_version": metadata.version("riskvalidation"),
                          "script": "experiments/exp_x3_seeds.py"}, "factors": {}}
    for tag, f in enumerate(FACTORS):
        days: dict[str, list[np.ndarray]] = {k: [] for k in MONITORS}
        tl_days: list[np.ndarray] = []
        shot: list[np.ndarray] = []
        for k in range(args.seeds):
            h = cm.draw_hits(BASE_SEED + 1000 * (k + 1), 500 + tag, args.reps, rate_factor=f)
            for suffix, opts in MONITORS.items():
                days[suffix].append(cm.first_true(cm.engine_paths(h, cm.ALPHA, **opts) >= cm.CROSS))
            tl_days.append(cm.traffic_light_days(h)[0])
            c250 = h[:, : cm.WINDOW].sum(axis=1).astype(float)
            shot.append(cm.kupiec_reject(c250, np.full(args.reps, float(cm.WINDOW)), cm.ALPHA))
        for suffix in MONITORS:
            res = summarise(days[suffix], tl_days, shot, rng)
            out["factors"][f"x{f:g}{suffix}"] = res
            print(f"[x{f:g}{suffix}] pooled median {res['pooled_median']} ci {res['pooled_median_ci']}  seeds below 250: "
                  f"{res['share_of_seeds_below_window']:.2f}  cost {res['pooled_power_cost']:.4f} +- {res['pooled_power_cost_se']:.4f} "
                  f"[{time.time() - t0:.0f} s]", flush=True)
    args.out.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
