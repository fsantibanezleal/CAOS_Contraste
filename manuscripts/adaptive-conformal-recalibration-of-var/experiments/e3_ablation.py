"""Experiment 3: what each component of the wrapper contributes (ablation), in the six real windows.

    python manuscripts/adaptive-conformal-recalibration-of-var/experiments/e3_ablation.py \
        --workers 28 --returns-cache $CAOS_TEMP_ROOT/contraste-adaptive-conformal/windows.npz

Components of the proposed wrapper (the engine's ``riskvalidation.market.conformal.aci_var_es`` around the C11 pipeline's own
forecaster of the model): the step ``gamma`` of the level update, the clipping band of the working level, and the ES that
accompanies the recalibrated VaR. Each variant changes one component of the full wrapper and keeps the rest:

- ``full``: gamma 0.005, band [0.001, 0.25], ES = the model's tail mean at the working level;
- ``gamma-*``: gamma in {0.001, 0.0025, 0.01, 0.02, 0.05};
- ``band-wide``: band [1e-5, 0.5], the nearest the engine allows to the unclipped recursion of Gibbs and Candes;
- ``band-narrow``: band [alpha/2, 2 alpha];
- ``es-ratio``: the VaR at the working level and the ES that keeps the model's own ES/VaR ratio at the target level;
- ``es-target``: the VaR at the working level and the model's ES at the target level (not recalibrated), set to the VaR when it
  would lie above it;
- ``off``: gamma = 0, the model unwrapped.

Models: HS-250, GARCH-t and filtered historical simulation (the three of the hypothesis), levels 1 % and 2.5 %, six windows.
Output: ``e3_ablation.json`` (scores of every cell; no return of the derived-only series is written).
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402

common.patch_forecaster()

VARIANTS = {
    "off": dict(gamma=0.0),
    "full": dict(gamma=0.005),
    "gamma-0.001": dict(gamma=0.001),
    "gamma-0.0025": dict(gamma=0.0025),
    "gamma-0.01": dict(gamma=0.01),
    "gamma-0.02": dict(gamma=0.02),
    "gamma-0.05": dict(gamma=0.05),
    "band-wide": dict(gamma=0.005, band=(1e-5, 0.5)),
    "band-narrow": dict(gamma=0.005, band="narrow"),
    "es-ratio": dict(gamma=0.005, es="ratio"),
    "es-target": dict(gamma=0.005, es="target"),
}


def r9(x):
    return np.array([float(f"{v:.9g}") for v in x])


def _task(args):
    window, model_id, y, idx, hp = args
    from pipeline.cases.c11 import conformal as cf, forecast as fc
    from riskvalidation.market import conformal as rv

    first, last = int(idx[0]), int(idx[-1])
    series = np.asarray(y, float)[: last + 1]
    loss = common.loss_of(y, idx)
    forecaster, _ = cf._forecaster(fc.SPEC_BY_ID[model_id], series, first, hp)
    out = []
    for alpha in common.LEVELS:
        for name, v in VARIANTS.items():
            lo, hi = v.get("band", (common.LEVEL_MIN, common.LEVEL_MAX)) if v.get("band") != "narrow" else (alpha / 2, 2 * alpha)
            f = forecaster
            if v.get("es") in ("ratio", "target"):
                mode = v["es"]

                def f(t, level, mode=mode, base=forecaster, a=alpha):
                    var, es = base(t, level)
                    v0, e0 = base(t, a)
                    if mode == "ratio":
                        return var, min(var * (e0 / v0), var)
                    return var, min(e0, var)
            r = rv.aci_var_es(series, f, alpha, v["gamma"], first, lo, hi)
            s = common.scores(loss, r9(-r.var), r9(-r.es), alpha)
            out.append({"window": window, "model": model_id, "alpha": alpha, "variant": name, "scores": s,
                        "n_clipped": int(r.n_clipped), "level_min": float(r.levels.min()), "level_max": float(r.levels.max()),
                        "passes": common.passes(s)})
    base = {(o["alpha"]): o for o in out if o["variant"] == "off"}
    for o in out:
        o["fz0_change"] = common.fz0_change(o["scores"], base[o["alpha"]]["scores"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--returns-cache", default=None)
    a = ap.parse_args()
    t0 = time.perf_counter()
    hp, series = common.hyper()
    data = common.window_data(series, pathlib.Path(a.returns_cache) if a.returns_cache else None)
    tasks = [(w, m, data[w][0], data[w][1], hp) for w in common.WINDOWS for m in common.WRAPPED3]
    tasks.sort(key=lambda t: -t[3].size)
    import os

    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[var] = "1"
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        for part in pool.map(_task, tasks):
            rows += part
            print(f"  {part[0]['window']} {part[0]['model']} at {time.perf_counter() - t0:.0f}s", flush=True)
    p = common.dump({"variants": VARIANTS, "gamma_default": common.GAMMA, "rows": rows, "seconds": round(time.perf_counter() - t0)},
                    "e3_ablation.json")
    print("wrote", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
