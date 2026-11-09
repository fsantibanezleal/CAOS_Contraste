"""Experiment 2: the wrapper on every level-parametric model of the ladder, in the six real windows.

    python manuscripts/adaptive-conformal-recalibration-of-var/experiments/e2_wrap_ladder.py \
        --workers 28 --cache $CAOS_TEMP_ROOT/contraste-adaptive-conformal/cache

Runs the engine's adaptive conformal wrapper (``riskvalidation.market.conformal``, gamma 0.005, band 0.001 to 0.25, fixed
before any run) around the ten ladder models that answer a VaR and an ES at any tail level (historical simulation 250 and 500
days, age-weighted historical simulation, delta-normal, EWMA, GARCH-t, GJR-t, EGARCH-t, filtered historical simulation,
conditional EVT), with the C11 pipeline's own forecasting code (same slice, same refit schedule, same hyperparameters as the
committed ladder) on the raw series in the device data root. Eight ladder models are not wrapped: the Cornish-Fisher model and
the two CAViaR models without the ES step forecast a VaR only (the wrapper needs the ES, and FZ0 is undefined without it), and
ES-CAViaR, the three GAS-FZ models and the quantile network are fitted for one level and cannot be asked at another without a
refit.

Checks and outputs
- the three models committed in ``data/derived/C11`` (HS-250, GARCH-t, FHS) are reproduced: the unwrapped hit days equal the
  committed ladder's, and the wrapped hit counts, Kupiec and conditional coverage p-values and FZ0 equal the committed rows;
- per window, model and level: scores of the unwrapped and wrapped sequences (engine ``forecast_scores``), the relative FZ0
  change with a 95 % interval from a moving-block bootstrap of the paired daily FZ0 difference (blocks of 10 days, 2,000
  draws, seed 20261104 + a fixed integer per row), Wilson intervals of the hit rates, the days the level sat at the band edge.
Output: ``e2_wrap_ladder.json`` (aggregates only; the French series is derived-only and none of its returns is written).
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402

MODELS = ("hs-250", "hs-500", "awhs", "dn-rolling", "ewma", "garch-t", "gjr-t", "egarch-t", "fhs", "evt-mf")
common.patch_forecaster()


def close(a, b, tol: float = 1e-6) -> bool:
    """Equal within ``tol``, or both absent (a test the engine did not evaluate)."""
    return (a is None and b is None) or (a is not None and b is not None and abs(a - b) < tol)


def r9(x: np.ndarray) -> np.ndarray:
    return np.array([float(f"{v:.9g}") for v in x])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--cache", required=True, help="folder of the cached wrapped runs (temp root)")
    ap.add_argument("--returns-cache", default=None, help="optional .npz (temp root) that keeps the parsed returns")
    ap.add_argument("--models", default=",".join(MODELS))
    a = ap.parse_args()
    from pipeline.cases.c11 import bake, conformal as cf, forecast as fc

    models = tuple(a.models.split(","))
    t0 = time.perf_counter()
    hp, series = common.hyper()
    data = common.window_data(series, pathlib.Path(a.returns_cache) if a.returns_cache else None)
    runs = cf.wrap_windows({w: (data[w][0], data[w][1]) for w in common.WINDOWS}, hp, pathlib.Path(a.cache), bake.ENGINE_PIN, models,
                           workers=a.workers)
    print(f"wrapped runs ready in {time.perf_counter() - t0:.0f}s", flush=True)

    rows, repro, paths = [], [], {}
    for wi, w in enumerate(common.WINDOWS):
        y, idx = data[w]
        loss = common.loss_of(y, idx)
        committed = common.doc(w)["outputs"]
        ladder = {m["model_id"]: m for m in committed["models"]}
        crow = {(r["model_id"], r["alpha"]): r for r in committed["conformal"]["rows"]}
        for mi, m in enumerate(models):
            run = runs[w][m]
            for ai, alpha in enumerate(common.LEVELS):
                wr, pl = run.wrapped[alpha], run.plain[alpha]
                var_w, es_w = r9(-wr.var), r9(-wr.es)
                var_u, es_u = r9(-pl.var), r9(-pl.es)
                su = common.scores(loss, var_u, es_u, alpha)
                sw = common.scores(loss, var_w, es_w, alpha)
                seed = common.SEED_BOOT + 1000 * wi + 100 * mi + ai
                pc = common.paired_change(loss, var_u, es_u, var_w, es_w, alpha, seed)
                lo_u, hi_u = common.wilson(su["n_hits"], su["n"])
                lo_w, hi_w = common.wilson(sw["n_hits"], sw["n"])
                lv = ladder[m]["by_level"][ai]
                same_hits = [int(i) for i in np.flatnonzero(loss > var_u)] == lv["exceedance_days"]
                rows.append({"window": w, "model": m, "alpha": alpha, "n_days": int(loss.size), "unwrapped": su, "wrapped": sw,
                             "hit_ci_unwrapped": [lo_u, hi_u], "hit_ci_wrapped": [lo_w, hi_w], **pc,
                             "n_clipped": int(wr.n_clipped), "n_fallback_days": int(run.n_fallback_days),
                             "level_min": float(wr.levels.min()), "level_mean": float(wr.levels.mean()),
                             "level_max": float(wr.levels.max()), "level_last": float(wr.levels[-1]),
                             "unwrapped_hits_equal_ladder": bool(same_hits)})
                if (w in common.STRESS) and m in common.WRAPPED3:
                    paths[f"{w}|{m}|{alpha}"] = {"levels": [round(float(v), 6) for v in wr.levels],
                                                 "hit_days": [int(i) for i in np.flatnonzero(wr.hits)],
                                                 "plain_hit_days": [int(i) for i in np.flatnonzero(pl.hits)]}
                if m in common.WRAPPED3:
                    c = crow[(m, alpha)]
                    ok = (c["wrapped"]["n_exceedances"] == sw["n_hits"] and c["unwrapped"]["n_exceedances"] == su["n_hits"]
                          and close(c["wrapped"]["kupiec_p"], sw["kupiec_p"]) and close(c["wrapped"]["conditional_coverage_p"], sw["cc_p"])
                          and close(c["wrapped"]["independence_p"], sw["independence_p"])
                          and close(c["wrapped"]["fz0_mean"], sw["fz0_mean"]) and close(c["unwrapped"]["fz0_mean"], su["fz0_mean"])
                          and close(c["fz0_change"], pc["fz0_change"]))
                    repro.append({"window": w, "model": m, "alpha": alpha, "equals_committed": bool(ok)})
        print(f"window {w} done at {time.perf_counter() - t0:.0f}s", flush=True)

    out = {"models": list(models), "gamma": common.GAMMA, "level_band": [common.LEVEL_MIN, common.LEVEL_MAX],
           "bootstrap": {"block": common.BLOCK, "reps": common.BOOT_REPS, "seed_base": common.SEED_BOOT},
           "reproduction": {"checked": len(repro), "equal": int(sum(r["equals_committed"] for r in repro)), "rows": repro},
           "unwrapped_equals_ladder": bool(all(r["unwrapped_hits_equal_ladder"] for r in rows)),
           "rows": rows, "paths": paths, "seconds": round(time.perf_counter() - t0)}
    p = common.dump(out, "e2_wrap_ladder.json")
    print(f"wrote {p}; reproduced {out['reproduction']['equal']} of {out['reproduction']['checked']} committed rows; "
          f"unwrapped = ladder: {out['unwrapped_equals_ladder']}")
    return 0 if out["reproduction"]["equal"] == out["reproduction"]["checked"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
