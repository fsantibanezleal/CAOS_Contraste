"""E1: the bias of the holdout estimate under each leak, against a known truth.

For every repetition a development sample is drawn and split by the product's rule (a locked stratified holdout of 30%, a
calibration slice of 20% of the rest, the remainder for training). Each model is fitted by the proposed protocol and by each leaked
variant of it (``leaklab.LEAKS``), and the holdout estimate of its AUC, Brier score and calibration error is set against the same
quantity on a large sample that no step ever read (the oracle sample): the estimate minus the oracle value is the bias of the
validation procedure for that fitted model. The 95% interval of the AUC (the engine's ECB variance) is checked for coverage of
the oracle value. Two k-fold procedures are added: preprocessing fitted inside each training fold and fitted on all development
rows before the folds (Ambroise and McLachlan 2002).

Datasets: ``synthetic`` (planted known truth, 2,500 rows, 40 inputs), ``synthetic-small`` (800 rows), ``taiwan`` (the 30,000 card
holders of C01, the oracle sample being 10,000 rows set aside per repetition) and ``product`` (the product's own optbinning scorecard
on 12 inputs, protocol against two leaks).

    python manuscripts/leakage-safe-validation-protocol/experiments/e1_estimator_bias.py --dataset synthetic --reps 300
    CONTRASTE_DATA=<data root> python .../e1_estimator_bias.py --dataset taiwan --reps 150 --cache <folder>
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

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "data-pipeline"))
import leaklab as L  # noqa: E402

BASE_SEED = {"synthetic": 20261104, "synthetic-small": 20261105, "taiwan": 20261106, "product": 20261107}
N_TOTAL = {"synthetic": 2500, "synthetic-small": 800, "taiwan": 2500, "product": 2500}
N_ORACLE = {"synthetic": 50_000, "synthetic-small": 50_000, "taiwan": 10_000, "product": 50_000}
P = {"synthetic": 40, "synthetic-small": 40, "taiwan": 20, "product": 12}
LEAKS_BY_KIND = {
    "woe": ["none", "impute_full", "bin_full", "woe_full", "screen_full", "fit_full", "select_test", "cal_test", "cal_overlap"],
    "linear": ["none", "impute_full", "scale_full", "screen_full", "fit_full", "select_test", "cal_test", "cal_overlap"],
}
_STATE: dict = {}


def cache_dir(arg: str | None) -> pathlib.Path:
    if arg:
        return pathlib.Path(arg)
    root = os.environ.get("CAOS_TEMP_ROOT")
    if not root:
        sys.exit("set CAOS_TEMP_ROOT or pass --cache <folder>: the cache never goes inside the repository")
    return pathlib.Path(root) / "contraste-leakage-safe-validation-protocol" / "cache"


def load_taiwan(cache: pathlib.Path) -> tuple[np.ndarray, np.ndarray]:
    path = cache / "taiwan.npz"
    if path.exists():
        z = np.load(path)
        return z["X"], z["y"]
    data = os.environ.get("CONTRASTE_DATA")
    if not data:
        sys.exit("set CONTRASTE_DATA to the data root that holds raw/uci-taiwan (the C01 source)")
    from pipeline.io import readers

    recs = readers.read_taiwan(pathlib.Path(data) / "raw" / "uci-taiwan" / "default+of+credit+card+clients.zip")
    cols = ["LIMIT_BAL", "EDUCATION", *readers.TAIWAN_PAY, *readers.TAIWAN_BILL, *readers.TAIWAN_PAID]
    X = np.array([[float(r[c]) for c in cols] for r in recs])
    y = np.array([int(r["target"]) for r in recs])
    cache.mkdir(parents=True, exist_ok=True)
    np.savez(path, X=X, y=y)
    return X, y


def _init(dataset: str, cache: str | None) -> None:
    _STATE["dataset"] = dataset
    if dataset == "taiwan":
        _STATE["X"], _STATE["y"] = load_taiwan(cache_dir(cache))


def draw(dataset: str, rng: np.random.Generator):
    n, no, p = N_TOTAL[dataset], N_ORACLE[dataset], P[dataset]
    if dataset == "taiwan":
        X, y = _STATE["X"], _STATE["y"]
        perm = rng.permutation(len(y))
        o, d = perm[:no], perm[no:no + n]
        return X[d], y[d], X[o], y[o]
    X, y = L.planted(n, p, rng)
    Xo, yo = L.planted(no, p, rng)
    return X, y, Xo, yo


def cv_estimate(X, y, dev, kind, pre: bool, rng, Xo, yo) -> tuple[float, float]:
    """5-fold AUC over the development rows with the preprocessing fitted inside each training fold (``pre=False``) or on all
    development rows before the folds (``pre=True``), and the mean oracle AUC of the fold models."""
    perm = rng.permutation(dev)
    folds = np.array_split(perm, 5)
    est, orc = [], []
    for k in range(5):
        va = folds[k]
        tr = np.concatenate([folds[j] for j in range(5) if j != k])
        src = dev if pre else tr
        rows = {"impute": src, "scale": src, "bin": src, "woe": src, "screen": src, "fit": tr}
        f = L.fit_model(X, y, rows, kind=kind)
        est.append(L.fast_auc(f.raw(X[va]), y[va]))
        orc.append(L.fast_auc(f.raw(Xo), yo))
    return float(np.mean(est)), float(np.mean(orc))


def run_rep(job: tuple[str, int]) -> dict:
    dataset, r = job
    rng = np.random.default_rng(np.random.SeedSequence([BASE_SEED[dataset], r]))
    X, y, Xo, yo = draw(dataset, rng)
    train, cal, hold = L.stratified_slices(y, rng)
    out: dict = {}
    for kind, leaks in LEAKS_BY_KIND.items():
        for leak in leaks:
            c = L.overlapping_calibration(cal, hold) if leak == "cal_overlap" else cal
            f = L.fit_pipeline(X, y, train, c, hold, kind=kind, leak=leak)
            est = L.score_sample(f, X[hold], y[hold], with_variance=True)
            orc = L.score_sample(f, Xo, yo)
            out[f"{kind}/{leak}"] = {"auc": est["auc"], "s2": est["s2"], "brier": est["brier"], "ece": est["ece"],
                                     "o_auc": orc["auc"], "o_brier": orc["brier"], "o_ece": orc["ece"]}
        dev = np.concatenate([train, cal])
        for pre in (False, True):
            e, o = cv_estimate(X, y, dev, kind, pre, rng, Xo, yo)
            out[f"{kind}/cv_{'pre' if pre else 'in'}"] = {"auc": e, "o_auc": o}
    return out


def run_rep_product(job: tuple[str, int]) -> dict:
    """The product's own scorecard (optbinning monotone binning, IV screen, sign check, logistic) and its isotonic map."""
    import pandas as pd
    from pipeline.core.calibration import clip_pd, fit_isotonic
    from pipeline.model import scorecard

    dataset, r = job
    rng = np.random.default_rng(np.random.SeedSequence([BASE_SEED[dataset], r]))
    X, y, Xo, yo = draw(dataset, rng)
    train, cal, hold = L.stratified_slices(y, rng)
    names = [f"x{j}" for j in range(X.shape[1])]
    df, dfo = pd.DataFrame(X, columns=names), pd.DataFrame(Xo, columns=names)
    mono = {n: 0 for n in names}

    def fit(rows):
        return scorecard.fit_scorecard(df.iloc[rows], y[rows], features=names, categorical=(), monotone=mono)

    out = {}
    sc_prot = fit(train)
    sc_full = fit(np.concatenate([train, hold]))
    for leak, sc, cal_rows in (("none", sc_prot, cal), ("fit_full", sc_full, cal), ("cal_test", sc_prot, hold)):
        iso = fit_isotonic(clip_pd(sc.predict_pd(df.iloc[cal_rows])), y[cal_rows])
        p_h, p_o = iso(clip_pd(sc.predict_pd(df.iloc[hold]))), iso(clip_pd(sc.predict_pd(dfo)))
        from riskvalidation.validation.discrimination import auc_with_variance

        auc, s2, _, _ = auc_with_variance(p_h, y[hold])
        out[f"product/{leak}"] = {"auc": auc, "s2": s2, "brier": L.brier(p_h, y[hold]), "ece": L.ece(p_h, y[hold]),
                                  "o_auc": L.fast_auc(p_o, yo), "o_brier": L.brier(p_o, yo), "o_ece": L.ece(p_o, yo)}
    return out


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def summarise(rows: list[dict]) -> dict:
    keys = rows[0].keys()
    out = {}
    for key in keys:
        a = np.array([r[key]["auc"] - r[key]["o_auc"] for r in rows])
        n = len(a)
        s = {"n": n, "auc_bias": float(a.mean()), "auc_bias_se": float(a.std(ddof=1) / math.sqrt(n)),
             "auc_rmse": float(math.sqrt(np.mean(a ** 2))), "auc_est": float(np.mean([r[key]["auc"] for r in rows])),
             "auc_oracle": float(np.mean([r[key]["o_auc"] for r in rows])), "bias_draws": [round(float(v), 5) for v in a]}
        if "s2" in rows[0][key]:
            cov = sum(abs(r[key]["auc"] - r[key]["o_auc"]) <= 1.959964 * math.sqrt(r[key]["s2"]) for r in rows)
            lo, hi = wilson(cov, n)
            s |= {"coverage": cov / n, "coverage_lo": lo, "coverage_hi": hi}
            for m in ("brier", "ece"):
                d = np.array([r[key][m] - r[key]["o_" + m] for r in rows])
                s |= {f"{m}_bias": float(d.mean()), f"{m}_bias_se": float(d.std(ddof=1) / math.sqrt(n))}
        out[key] = s
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=list(BASE_SEED), required=True)
    ap.add_argument("--reps", type=int, required=True)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--cache", default=None)
    ap.add_argument("--out", default=str(HERE / "results"))
    a = ap.parse_args()
    if a.dataset == "taiwan":
        load_taiwan(cache_dir(a.cache))
    t0 = time.time()
    fn = run_rep_product if a.dataset == "product" else run_rep
    with ProcessPoolExecutor(a.workers, initializer=_init, initargs=(a.dataset, a.cache)) as ex:
        rows = list(ex.map(fn, [(a.dataset, r) for r in range(a.reps)], chunksize=1))
    res = {"dataset": a.dataset, "reps": a.reps, "base_seed": BASE_SEED[a.dataset], "n_total": N_TOTAL[a.dataset],
           "n_oracle": N_ORACLE[a.dataset], "p": P[a.dataset], "seconds": round(time.time() - t0, 1), "summary": summarise(rows)}
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"e1_{a.dataset}.json").write_text(json.dumps(res, indent=1), encoding="utf-8", newline="\n")
    print(a.dataset, "done in", res["seconds"], "s")


if __name__ == "__main__":
    main()
