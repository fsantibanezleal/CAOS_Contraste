"""VaR-hit experiment: the e-process monitors against the fixed-window tests, the group-sequential and change-detection
rules calibrated to the same size, and the published e-backtest, on the engine's generator of known truth.

Streams: ``riskvalidation.generators.VarHits`` (release 1.1.0), VaR level alpha = 1 %, horizon 1,000 days, ``--reps`` streams
per scenario (default 2,000), one seed sequence ``[seed, tag]`` per scenario. Scenarios: the null; a hit rate multiplied
by 1.5, 2, 3, 4, 6 and 10; clustered hits at the right rate with P(hit after a hit) = 0.1, 0.2 and 0.4.

Every rule is read every day and a series is rejected at the first day the rule fires. The rules:

- engine monitors: ``e_rate`` (two-sided mixture), ``e_rate_upper`` (the one-sided mixture a supervisor reads),
  ``e_cluster``, ``e_battery`` (their average), ``e_sprt3`` (one alternative, a hit rate three times alpha);
- written here: ``e_wwz`` (the e-backtest of Wang, Wang and Ziegel, 2022), ``e_beta`` (uniform-prior Bayes factor);
- fixed-window tests read every day: ``kupiec_trailing`` (last 250 days, from day 250), ``kupiec_cumulative`` (all days
  so far, from day 50), ``traffic_light`` (Basel zone of the last 250 days), ``independence_trailing``;
- same-size comparators: ``kupiec_sidak`` (cumulative Kupiec at the Sidak per-look level of 951 looks),
  ``kupiec_calibrated`` (cumulative Kupiec with a constant critical value set by simulation to a size of 5 % over the
  1,000 days), ``cusum_calibrated`` (Page's CUSUM against a hit rate of 3 alpha, threshold set the same way). The critical
  values come from ``--calibration-reps`` null streams (default 20,000) drawn with a seed sequence of their own.

A second output, ``results_size_horizon.json``, follows 2,000 null streams for 5,000 days to show how the share of
rejected correct models grows with the horizon for each rule.

    python manuscripts/e-process-sequential-monitors/experiments/exp_hits.py
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

SEED = 20261104
SCENARIOS: list[tuple[str, str, dict[str, float]]] = [
    ("null", "null", {}),
    ("rate-x1.5", "rate", {"rate_factor": 1.5}),
    ("rate-x2", "rate", {"rate_factor": 2.0}),
    ("rate-x3", "rate", {"rate_factor": 3.0}),
    ("rate-x4", "rate", {"rate_factor": 4.0}),
    ("rate-x6", "rate", {"rate_factor": 6.0}),
    ("rate-x10", "rate", {"rate_factor": 10.0}),
    ("cluster-0.1", "cluster", {"cluster": 0.1}),
    ("cluster-0.2", "cluster", {"cluster": 0.2}),
    ("cluster-0.4", "cluster", {"cluster": 0.4}),
]
CAL_TAG = 900
HORIZON_TAG = 950


def run_methods(h: np.ndarray, cv: dict[str, float], rng: np.random.Generator) -> dict[str, dict]:
    p = cm.ALPHA
    looks = h.shape[1] - cm.FIRST_LOOK + 1
    lr = cm.cumulative_lr(h, p)
    c = np.cumsum(h, axis=1).astype(float)
    t = np.arange(1, h.shape[1] + 1, dtype=float)
    from scipy import stats

    days: dict[str, np.ndarray] = {
        "e_rate": cm.first_true(cm.engine_paths(h, p) >= cm.CROSS),
        "e_rate_upper": cm.first_true(cm.engine_paths(h, p, direction="upper") >= cm.CROSS),
        "e_cluster": cm.first_true(cm.engine_cluster_paths(h, p) >= cm.CROSS),
        "e_battery": cm.first_true(cm.engine_battery_paths(h, p) >= cm.CROSS),
        "e_sprt3": cm.first_true(cm.engine_paths(h, p, multipliers=[3.0]) >= cm.CROSS),
        "e_wwz": cm.first_true(cm.wwz_log_e(h, p) >= cm.CROSS),
        "e_beta": cm.first_true(cm.beta_mixture_log_e(h, p) >= cm.CROSS),
        "kupiec_trailing": cm.first_true(cm.trailing_kupiec(h, p)),
        "kupiec_cumulative": cm.first_true(stats.chi2.sf(lr, 1) < cm.LEVEL, cm.FIRST_LOOK - 1),
        "kupiec_sidak": cm.first_true(stats.chi2.sf(lr, 1) < cm.sidak_level(looks), cm.FIRST_LOOK - 1),
        "kupiec_calibrated": cm.first_true(lr > cv["kupiec_cumulative"], cm.FIRST_LOOK - 1),
        "cusum_calibrated": cm.first_true(cm.cusum_paths(h, p, 3.0) > cv["cusum_m3"]),
        "traffic_light": cm.traffic_light_days(h)[0],
        "independence_trailing": cm.first_true(cm.independence_reject(h)),
    }
    out = {name: cm.summarise(d, cm.WINDOW, rng) for name, d in days.items()}
    one_shot = cm.kupiec_reject(c[:, cm.WINDOW - 1], np.full(h.shape[0], float(cm.WINDOW)), p)
    out["kupiec_one_shot"] = {"n": int(h.shape[0]), "ever": float(one_shot.mean()),
                              "ever_ci": list(cm.wilson(int(one_shot.sum()), h.shape[0]))}
    del t
    n = h.shape[0]
    for name in ("e_rate", "e_rate_upper", "e_wwz"):
        diff = one_shot.astype(float) - (days[name] <= cm.WINDOW).astype(float)
        out[name]["power_cost_vs_one_shot"] = {"mean": float(diff.mean()), "se": float(diff.std(ddof=1) / math.sqrt(n))}
    return out


def calibration(seed: int, reps: int, chunk: int = 4000) -> dict[str, float]:
    lr_max, cs_max = [], []
    for k in range(math.ceil(reps / chunk)):
        n = min(chunk, reps - k * chunk)
        h = cm.draw_hits(seed, CAL_TAG + k, n)
        a, b = cm.max_statistics(h, cm.ALPHA)
        lr_max.append(a)
        cs_max.append(b)
    return cm.critical_values(np.concatenate(lr_max), np.concatenate(cs_max))


def size_horizon(seed: int, reps: int, horizon: int, cv: dict[str, float], rng: np.random.Generator) -> dict:
    from scipy import stats

    p = cm.ALPHA
    h = cm.draw_hits(seed, HORIZON_TAG, reps, t=horizon)
    lr = cm.cumulative_lr(h, p)
    days: dict[str, np.ndarray] = {
        "e_rate": cm.first_true(cm.engine_paths(h, p) >= cm.CROSS),
        "e_wwz": cm.first_true(cm.wwz_log_e(h, p) >= cm.CROSS),
        "e_beta": cm.first_true(cm.beta_mixture_log_e(h, p) >= cm.CROSS),
        "kupiec_cumulative": cm.first_true(stats.chi2.sf(lr, 1) < cm.LEVEL, cm.FIRST_LOOK - 1),
        "kupiec_trailing": cm.first_true(cm.trailing_kupiec(h, p)),
        "traffic_light": cm.traffic_light_days(h)[0],
        "kupiec_calibrated": cm.first_true(lr > cv["kupiec_cumulative"], cm.FIRST_LOOK - 1),
        "cusum_calibrated": cm.first_true(cm.cusum_paths(h, p, 3.0) > cv["cusum_m3"]),
    }
    grid = [d for d in (10, 25, 50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000) if d <= horizon]
    grid += list(range(1250, horizon + 1, 250))
    curves = {}
    for name, d in days.items():
        k = [int((d <= g).sum()) for g in grid]
        curves[name] = {"share": [x / reps for x in k], "ci": [list(cm.wilson(x, reps)) for x in k]}
    del rng
    return {"meta": {"reps": reps, "horizon": horizon, "alpha": cm.ALPHA, "seed": seed, "tag": HORIZON_TAG},
            "days": grid, "curves": curves}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--calibration-reps", type=int, default=20000)
    ap.add_argument("--horizon-reps", type=int, default=2000)
    ap.add_argument("--horizon", type=int, default=5000)
    ap.add_argument("--out", type=pathlib.Path, default=HERE / "results_hits.json")
    ap.add_argument("--out-horizon", type=pathlib.Path, default=HERE / "results_size_horizon.json")
    args = ap.parse_args()
    t0 = time.time()
    cv = calibration(args.seed, args.calibration_reps)
    print(f"calibrated {cv} in {time.time() - t0:.0f} s", flush=True)
    rng = np.random.default_rng(np.random.SeedSequence([args.seed, 777]))
    result: dict = {"meta": {"seed": args.seed, "reps": args.reps, "horizon": cm.HORIZON, "alpha": cm.ALPHA,
                             "window": cm.WINDOW, "level": cm.LEVEL, "first_look": cm.FIRST_LOOK,
                             "calibration_reps": args.calibration_reps, "critical_values": cv,
                             "engine_version": metadata.version("riskvalidation"),
                             "bootstrap_resamples": 2000, "script": "experiments/exp_hits.py"},
                    "scenarios": {}}
    for tag, (sid, kind, kw) in enumerate(SCENARIOS):
        h = cm.draw_hits(args.seed, tag, args.reps, **kw)
        methods = run_methods(h, cv, rng)
        result["scenarios"][sid] = {"kind": kind, "params": kw, "tag": tag, "mean_hits": float(h.sum(axis=1).mean()),
                                    "methods": methods}
        m = methods
        print(f"[{sid}] e_rate ever {m['e_rate']['ever']:.3f} med {m['e_rate']['median_day']}  kupiec_trailing "
              f"{m['kupiec_trailing']['ever']:.3f}  tl {m['traffic_light']['ever']:.3f} med {m['traffic_light']['median_day']}"
              f"  [{time.time() - t0:.0f} s]", flush=True)
    result["meta"]["traffic_light_first_non_green_count"] = cm.traffic_light_days(np.zeros((1, 300), dtype=bool))[1]
    args.out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    sh = size_horizon(args.seed, args.horizon_reps, args.horizon, cv, rng)
    args.out_horizon.write_text(json.dumps(sh, indent=1), encoding="utf-8")
    print(f"done in {time.time() - t0:.0f} s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
