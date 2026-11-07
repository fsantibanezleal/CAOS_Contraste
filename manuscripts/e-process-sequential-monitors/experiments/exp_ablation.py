"""Ablation of the proposed monitors: what each component contributes.

Three blocks, each from the engine's monitors and generators (release 1.1.0), ``--reps`` series per scenario (default
2,000 for the VaR hits, 1,000 for the PD books), one seed sequence ``[seed, tag]`` per scenario.

``hits_grid``: the hit-rate monitor with its mixture grid taken apart: the full two-sided grid (0.25, 0.5, 1.5, 2, 3, 4, 6, 10
times alpha), the upper half, the upper half cut to its lower and to its upper alternatives, and each single alternative
(the likelihood-ratio martingale of one hit rate). Scenarios: the null and hit rates 2, 3, 4 and 6 times alpha.

``hits_battery``: the rate monitor, the clustering monitor, their average (the engine's battery), their product (not an
e-process when the two read the same stream: its size is measured) and the union of the two at a threshold of 40 each.
Scenarios: the null, hit rates 3 and 4 times alpha, clustering 0.2 and 0.4 at the right rate.

``pd_combine``: the PD monitor of five grades (predicted PD 0.5, 1, 2, 5 and 10 %, 2,000 obligors per grade and year, ten
years) with the grades combined by product or by average, two-sided or upper, the full 16-point grid or a four-point
grid, on the generator ``DefaultCounts`` with every PD scaled by 1, 1.05, 1.1 and 1.25 and with only the 10 % grade scaled by 1.3.

    python manuscripts/e-process-sequential-monitors/experiments/exp_ablation.py
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from importlib import metadata

import numpy as np
from scipy import stats

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as cm  # noqa: E402

SEED = 20261104
GRID_VARIANTS: list[tuple[str, dict]] = [
    ("full", {}),
    ("upper", {"direction": "upper"}),
    ("upper-low", {"multipliers": [1.5, 2.0, 3.0, 4.0]}),
    ("upper-high", {"multipliers": [3.0, 4.0, 6.0, 10.0]}),
    ("single-1.5", {"multipliers": [1.5]}),
    ("single-2", {"multipliers": [2.0]}),
    ("single-3", {"multipliers": [3.0]}),
    ("single-4", {"multipliers": [4.0]}),
    ("single-10", {"multipliers": [10.0]}),
]
GRID_SCENARIOS: list[tuple[str, dict]] = [
    ("null", {}), ("rate-x2", {"rate_factor": 2.0}), ("rate-x3", {"rate_factor": 3.0}),
    ("rate-x4", {"rate_factor": 4.0}), ("rate-x6", {"rate_factor": 6.0}),
]
BATTERY_SCENARIOS: list[tuple[str, dict]] = [
    ("null", {}), ("rate-x3", {"rate_factor": 3.0}), ("rate-x4", {"rate_factor": 4.0}),
    ("cluster-0.2", {"cluster": 0.2}), ("cluster-0.4", {"cluster": 0.4}),
]
PD_BOOK = (0.005, 0.01, 0.02, 0.05, 0.10)
N_OBL, YEARS = 2000, 10
PD_SCENARIOS: list[tuple[str, np.ndarray]] = [
    ("all-x1", np.ones(5)), ("all-x1.05", np.full(5, 1.05)), ("all-x1.1", np.full(5, 1.10)),
    ("all-x1.25", np.full(5, 1.25)), ("grade5-x1.3", np.array([1, 1, 1, 1, 1.3])),
]
PD_VARIANTS: list[tuple[str, dict]] = [
    ("product", {"combine": "product"}),
    ("product-upper", {"combine": "product", "direction": "upper"}),
    ("average", {"combine": "average"}),
    ("average-upper", {"combine": "average", "direction": "upper"}),
    ("average-upper-coarse", {"combine": "average", "direction": "upper", "multipliers": [1.1, 1.25, 1.5, 2.0]}),
    ("average-upper-single-1.25", {"combine": "average", "direction": "upper", "multipliers": [1.25]}),
]


def hits_blocks(seed: int, reps: int, rng: np.random.Generator) -> tuple[dict, dict]:
    from riskvalidation.validation.sequential import var_hit_clustering_eprocess, var_hit_eprocess

    grid: dict = {}
    for tag, (sid, kw) in enumerate(GRID_SCENARIOS):
        h = cm.draw_hits(seed, 100 + tag, reps, **kw)
        grid[sid] = {vid: cm.summarise(cm.first_true(cm.engine_paths(h, cm.ALPHA, **opts) >= cm.CROSS), cm.WINDOW, rng)
                     for vid, opts in GRID_VARIANTS}
    battery: dict = {}
    thr40 = np.log(40.0)
    for tag, (sid, kw) in enumerate(BATTERY_SCENARIOS):
        h = cm.draw_hits(seed, 200 + tag, reps, **kw)
        rate, clus = cm.engine_paths(h, cm.ALPHA), cm.engine_cluster_paths(h, cm.ALPHA)
        paths = {
            "rate": rate, "cluster": clus,
            "average": np.logaddexp(rate, clus) - np.log(2.0),
            "product": rate + clus,
        }
        days = {k: cm.first_true(v >= cm.CROSS) for k, v in paths.items()}
        days["union"] = cm.first_true((rate >= thr40) | (clus >= thr40))
        battery[sid] = {k: cm.summarise(v, cm.WINDOW, rng) for k, v in days.items()}
    del var_hit_clustering_eprocess, var_hit_eprocess
    return grid, battery


def pd_block(seed: int, reps: int) -> dict:
    from riskvalidation.generators import DefaultCounts
    from riskvalidation.validation.sequential import detection_time, pd_grade_eprocess

    pd = np.array(PD_BOOK)
    n = np.full((YEARS, pd.size), float(N_OBL))
    out: dict = {}
    for tag, (sid, factor) in enumerate(PD_SCENARIOS):
        gen = DefaultCounts(obligors=np.full((YEARS, pd.size), N_OBL), pd_true=np.minimum(np.tile(pd * factor, (YEARS, 1)), 0.999),
                            pd_forecast=np.tile(pd, (YEARS, 1)), rho=0.0)
        rng = np.random.default_rng(np.random.SeedSequence([seed, 300 + tag]))
        draws = [gen.draw(rng)["d"].astype(float) for _ in range(reps)]
        row: dict = {}
        for vid, opts in PD_VARIANTS:
            t = np.array([detection_time(pd_grade_eprocess(d, n, pd, **opts).log_e) or np.inf for d in draws])
            fin = np.isfinite(t)
            k_ever, k_by = int(fin.sum()), int((t <= 3).sum())
            row[vid] = {"n": reps, "ever": k_ever / reps, "ever_ci": list(cm.wilson(k_ever, reps)),
                        "by3": k_by / reps, "by3_ci": list(cm.wilson(k_by, reps)),
                        "median_year": float(np.median(t)) if np.isfinite(np.median(t)) else None,
                        "median_year_among_detected": float(np.median(t[fin])) if fin.any() else None}
        cum_d = np.cumsum(np.array(draws), axis=1)
        cum_n = np.cumsum(np.broadcast_to(n, cum_d.shape), axis=1)
        chi2 = (((cum_d - cum_n * pd) ** 2) / (cum_n * pd * (1 - pd))).sum(axis=2)
        rej = stats.chi2.sf(chi2, pd.size) < cm.LEVEL
        for vid, mask in (("chi2-one-shot-year-10", rej[:, -1]), ("chi2-every-year", rej.any(axis=1))):
            k = int(mask.sum())
            row[vid] = {"n": reps, "ever": k / reps, "ever_ci": list(cm.wilson(k, reps))}
        row["chi2-by-year-3"] = {"n": reps, "ever": float(rej[:, :3].any(axis=1).mean())}
        out[sid] = row
        print(f"[pd {sid}] " + "  ".join(f"{v}={row[v]['ever']:.3f}" for v, _ in PD_VARIANTS), flush=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--pd-reps", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", type=pathlib.Path, default=HERE / "results_ablation.json")
    args = ap.parse_args()
    t0 = time.time()
    rng = np.random.default_rng(np.random.SeedSequence([args.seed, 778]))
    grid, battery = hits_blocks(args.seed, args.reps, rng)
    print(f"hits blocks done [{time.time() - t0:.0f} s]", flush=True)
    pdb = pd_block(args.seed, args.pd_reps)
    result = {"meta": {"seed": args.seed, "reps": args.reps, "pd_reps": args.pd_reps, "alpha": cm.ALPHA,
                       "horizon": cm.HORIZON, "pd_book": list(PD_BOOK), "obligors": N_OBL, "years": YEARS,
                       "engine_version": metadata.version("riskvalidation"), "script": "experiments/exp_ablation.py"},
              "hits_grid": grid, "hits_battery": battery, "pd_combine": pdb}
    args.out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(f"done in {time.time() - t0:.0f} s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
