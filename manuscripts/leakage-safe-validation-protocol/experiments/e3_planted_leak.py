"""E3: a leak that exists only in development, as the engine's generator plants it (the planted leak of C22).

The model score is a genuine score plus a feature that, in development, is shifted by ``s`` for defaulters and, at decision time, is
noise (``riskvalidation.generators.scores.BinormalScores`` with ``leak=s``, 150 defaulters and 4,850 survivors in each sample, the
configuration of the committed C22 leakage family). Each repetition draws the development and the current samples and applies the
detectors the engine offers: the AUC-against-development test (``disc_auc_vs_initial``, the ECB form that treats the development AUC as
known), the characteristic stability index of the leaked feature (``stability_csi``), the single-feature AUC screen
(``ml.leakage.single_feature_auc``, threshold 0.95) and the resemblance AUC between development and current features
(``ml.leakage.resemblance_auc``). The closed forms of Section ``theory`` are evaluated beside the simulated means.

    python manuscripts/leakage-safe-validation-protocol/experiments/e3_planted_leak.py --reps 500
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import sys
import time
from concurrent.futures import ProcessPoolExecutor

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np
from scipy.stats import norm

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from e1_estimator_bias import wilson  # noqa: E402

from riskvalidation.generators.scores import BinormalScores  # noqa: E402
from riskvalidation.ml.leakage import resemblance_auc, single_feature_auc  # noqa: E402
from riskvalidation.validation.discrimination import auc_with_variance, disc_auc_vs_initial  # noqa: E402
from riskvalidation.validation.stability import stability_csi  # noqa: E402

SEED = 20261109
LEVELS = (0.0, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0)
N1, N0, D = 150, 4850, 1.0


def one(job: tuple[float, int]) -> dict:
    s, r = job
    gen = BinormalScores(n_defaulters=N1, n_survivors=N0, separation=D, leak=s)
    rng = np.random.default_rng(np.random.SeedSequence([SEED, int(round(s * 100)), r]))
    d = gen.draw(rng)
    dev_auc = auc_with_variance(d["development_risk"], d["development_defaults"])[0]
    cur_auc = auc_with_variance(d["risk"], d["defaults"])[0]
    t_auc = disc_auc_vs_initial(d["auc_initial"], d["risk"], d["defaults"])
    t_csi = stability_csi(d["expected_counts"], d["actual_counts"])
    sf = single_feature_auc(d["feature_development"][:, None], d["development_defaults"])
    rs = resemblance_auc(d["feature_development"][:, None], d["feature_current"][:, None], seed=r)
    z = (rs.auc - 0.5) / math.sqrt(rs.variance) if rs.variance > 0 else 0.0
    return {"dev_auc": dev_auc, "cur_auc": cur_auc, "auc_test": bool(t_auc.p_value < 0.05), "csi_test": bool(t_csi.p_value < 0.05),
            "single_feature_auc": sf.max_auc, "single_feature_flag": bool(sf.suspect), "resemblance_auc": rs.auc,
            "resemblance_flag": bool(z > 1.644854), "psi": float(t_csi.statistic)}


def closed_forms(s: float, d: float = D, w: tuple[float, float] = (1.0, 1.0)) -> dict:
    """AUC in development and at decision time of the score w1 * genuine + w2 * feature (Proposition ``leak-auc``), and the AUC of the
    leaked feature alone."""
    w1, w2 = w
    den = math.sqrt(2.0 * (w1 * w1 + w2 * w2))
    return {"dev_auc": float(norm.cdf((w1 * d + w2 * s) / den)), "cur_auc": float(norm.cdf(w1 * d / den)),
            "feature_auc": float(norm.cdf(s / math.sqrt(2.0)))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=500)
    ap.add_argument("--workers", type=int, default=30)
    ap.add_argument("--out", default=str(HERE / "results"))
    a = ap.parse_args()
    t0 = time.time()
    jobs = [(s, r) for s in LEVELS for r in range(a.reps)]
    with ProcessPoolExecutor(a.workers) as ex:
        rows = list(ex.map(one, jobs, chunksize=20))
    res: dict = {"reps": a.reps, "seed": SEED, "n_defaulters": N1, "n_survivors": N0, "separation": D, "levels": {}}
    for s in LEVELS:
        sel = [row for (lv, _), row in zip(jobs, rows) if lv == s]
        truth = BinormalScores(n_defaulters=N1, n_survivors=N0, separation=D, leak=s).truth()
        cf = closed_forms(s)
        entry = {"closed_form": cf, "engine_truth": {k: truth[k] for k in ("auc_current", "auc_development", "feature_population_psi")}}
        for k in ("dev_auc", "cur_auc", "single_feature_auc", "resemblance_auc", "psi"):
            v = np.array([r[k] for r in sel])
            entry[k] = {"mean": float(v.mean()), "se": float(v.std(ddof=1) / math.sqrt(len(v)))}
        for k in ("auc_test", "csi_test", "single_feature_flag", "resemblance_flag"):
            kk = sum(r[k] for r in sel)
            lo, hi = wilson(kk, len(sel))
            entry[k] = {"rate": kk / len(sel), "lo": lo, "hi": hi}
        res["levels"][str(s)] = entry
    res["seconds"] = round(time.time() - t0, 1)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "e3_planted_leak.json").write_text(json.dumps(res, indent=1), encoding="utf-8", newline="\n")
    print("e3 done in", res["seconds"], "s")


if __name__ == "__main__":
    main()
