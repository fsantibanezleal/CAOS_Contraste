"""Experiment 4: two published online recalibrations in score space, applied to all eighteen models of the ladder.

    python manuscripts/adaptive-conformal-recalibration-of-var/experiments/e4_score_space.py \
        --returns-cache $CAOS_TEMP_ROOT/contraste-adaptive-conformal/windows.npz

The wrapper of the manuscript acts on the tail level of the model (it asks the model for another quantile), so it needs a
model that answers at any level. The two comparators below act on the model's finished VaR and need nothing else, so they run
on the committed forecasts of every ladder model, including the five fitted for one level and the three that give a VaR only.
With the positive loss ``L_t`` and the model's VaR ``V_t`` (and ES ``E_t``) at the target level ``alpha``, the score is
``s_t = L_t / V_t`` and a hit is ``s_t > 1``. A corrected VaR is ``theta_t V_t`` and a corrected ES ``theta_t E_t``.

- ``rolling``: rolling split-conformal scale (Vovk et al. 2005; Lei et al. 2018; the window form of Barber et al. 2023). ``theta_t``
  is the ``ceil((n+1)(1-alpha))``-th smallest of the last ``n <= 250`` scores of the window (1 while that rank exceeds ``n``),
  clipped to ``[0.25, 4]``.
- ``tracker``: the quantile tracker, the proportional term of conformal PID control (Angelopoulos, Candes and Tibshirani 2023),
  ``theta_{t+1} = max(theta_t + eta (1{s_t > theta_t} - alpha), 0.25)``, ``theta_1 = 1``, ``eta = 0.05`` fixed before the run;
  ``eta`` in {0.01, 0.2} is reported as a sensitivity.

Each row carries the engine scores (``forecast_scores``), the relative FZ0 change against the unwrapped model with a
moving-block bootstrap 95 % interval (blocks of 10 days, 2,000 draws), and the clipping count. Output: ``e4_score_space.json``.
"""
from __future__ import annotations

import argparse
import math
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402

W_ROLL = 250
THETA_MIN, THETA_MAX = 0.25, 4.0
ETA = 0.05
ETA_SENS = (0.01, 0.2)


def r9(x):
    return np.array([float(f"{v:.9g}") for v in x])


def rolling_scale(score: np.ndarray, alpha: float) -> np.ndarray:
    """``theta_t`` of every day from the scores before it (a day with too few scores keeps 1)."""
    n_days = score.size
    theta = np.ones(n_days)
    for t in range(n_days):
        lo = max(0, t - W_ROLL)
        past = score[lo:t]
        n = past.size
        k = math.ceil((n + 1) * (1.0 - alpha))
        if n > 0 and k <= n:
            theta[t] = min(max(np.sort(past)[k - 1], THETA_MIN), THETA_MAX)
    return theta


def tracker_scale(score: np.ndarray, alpha: float, eta: float) -> tuple[np.ndarray, int]:
    theta = np.ones(score.size)
    clipped = 0
    cur = 1.0
    for t in range(score.size):
        theta[t] = cur
        raw = cur + eta * (float(score[t] > cur) - alpha)
        cur = max(raw, THETA_MIN)
        clipped += raw < THETA_MIN
    return theta, int(clipped)


def paired(loss, var_u, es_u, var_c, es_c, alpha, seed, reps=2000, block=10):
    fu = common.fz0_days(loss, var_u, es_u, alpha)
    fc = common.fz0_days(loss, var_c, es_c, alpha)
    rng = np.random.default_rng(seed)
    n = fu.size
    nb = int(math.ceil(n / block))
    starts = rng.integers(0, n, size=(reps, nb))
    idx = ((starts[:, :, None] + np.arange(block)[None, None, :]) % n).reshape(reps, -1)[:, :n]
    rel = (fc[idx].mean(axis=1) - fu[idx].mean(axis=1)) / np.abs(fu[idx].mean(axis=1))
    lo, hi = common.ci95(rel)
    return {"fz0_change": float((fc.mean() - fu.mean()) / abs(fu.mean())), "ci95": [lo, hi]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--returns-cache", default=None)
    a = ap.parse_args()
    t0 = time.perf_counter()
    data = common.window_data(None, pathlib.Path(a.returns_cache) if a.returns_cache else None)
    rows = []
    for wi, w in enumerate(common.WINDOWS):
        y, idx = data[w]
        loss = common.loss_of(y, idx)
        models = common.doc(w)["outputs"]["models"]
        for mi, m in enumerate(models):
            for ai, bl in enumerate(m["by_level"]):
                alpha = bl["alpha"]
                var = np.array(bl["var"], float)
                has_es = all(v is not None for v in bl["es"])
                es = np.array(bl["es"], float) if has_es else np.full(var.size, np.nan)
                score = loss / var
                variants = {"unwrapped": (np.ones(var.size), 0), "rolling": (rolling_scale(score, alpha), 0)}
                for eta in (ETA, *ETA_SENS):
                    th, nclip = tracker_scale(score, alpha, eta)
                    variants["tracker" if eta == ETA else f"tracker-eta-{eta}"] = (th, nclip)
                base = None
                for name, (th, nclip) in variants.items():
                    v, e = r9(th * var), (r9(th * es) if has_es else es)
                    if has_es:
                        e = np.maximum(e, v)               # positive-loss convention: ES at least the VaR (rounding only), as in e5
                        s = common.scores(loss, v, e, alpha)
                    else:
                        from riskvalidation.validation import market as vm

                        fl = (loss > v).astype(int)
                        kp, ind, cc = vm.kupiec_pof(fl, alpha), vm.christoffersen_independence(fl, alpha), vm.christoffersen_conditional_coverage(fl, alpha)
                        pv = lambda r: None if r.p_value is None or r.p_value != r.p_value else float(r.p_value)  # noqa: E731
                        s = {"n": int(loss.size), "n_hits": int(fl.sum()), "hit_rate": float(fl.mean()), "kupiec_p": pv(kp),
                             "independence_p": pv(ind), "cc_p": pv(cc), "fz0_mean": None, "z2": None}
                    row = {"window": w, "model": m["model_id"], "alpha": alpha, "method": name, "has_es": has_es, "scores": s,
                           "theta_min": float(th.min()), "theta_mean": float(th.mean()), "theta_max": float(th.max()), "n_clipped": nclip,
                           "passes": common.passes(s)}
                    if name == "unwrapped":
                        base = (v, e)
                    elif has_es:
                        row.update(paired(loss, base[0], base[1], v, e, alpha, common.SEED_BOOT + 5000 + 1000 * wi + 100 * mi + ai))
                    rows.append(row)
        print(f"window {w} done at {time.perf_counter() - t0:.0f}s", flush=True)
    p = common.dump({"constants": {"window": W_ROLL, "theta_band": [THETA_MIN, THETA_MAX], "eta": ETA, "eta_sensitivity": list(ETA_SENS),
                                   "bootstrap": {"block": 10, "reps": 2000, "seed_base": common.SEED_BOOT + 5000}},
                     "rows": rows, "seconds": round(time.perf_counter() - t0)}, "e4_score_space.json")
    print("wrote", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
