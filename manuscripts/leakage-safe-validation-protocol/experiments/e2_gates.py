"""E2: what each gate of the protocol detects, on leaks planted in the fitting path.

``matrix``  every leak of ``leaklab.LEAKS`` on the compact pipeline, ``--reps`` data draws, the three gates (G1 transforms on the
            training slice only, G2 calibration slice disjoint from the test slice, G3 outside-information invariance) and the
            non-vacuity control; the pass rate of a gate on the protocol itself is its false-alarm complement.
``draws``   the leaks whose effect on the fit is discrete (the selection of a configuration on the holdout): the detection rate of G3
            against the number of independent perturbation draws.
``ladder``  the product's own ``fit_ladder`` (every rung of C01) under the protocol and under two faulty uses of it, with the
            comparison the product's test makes (``tests/test_leakage.py``): the fitted records of every rung before and after the
            outside information is changed.

    python manuscripts/leakage-safe-validation-protocol/experiments/e2_gates.py matrix --reps 100
"""
from __future__ import annotations

import argparse
import json
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

SEED = 20261108
N, P = 1500, 40
KINDS = {
    "woe": ["none", "impute_full", "bin_full", "woe_full", "screen_full", "fit_full", "select_test", "cal_test", "cal_overlap"],
    "linear": ["none", "impute_full", "scale_full", "screen_full", "fit_full", "select_test", "cal_test", "cal_overlap"],
}


def one(job: tuple[int, int]) -> dict:
    r, draws = job
    rng = np.random.default_rng(np.random.SeedSequence([SEED, r]))
    X, y = L.planted(N, P, rng)
    train, cal, hold = L.stratified_slices(y, rng)
    out = {}
    for kind, leaks in KINDS.items():
        for leak in leaks:
            out[f"{kind}/{leak}"] = L.gates(X, y, train, cal, hold, kind=kind, leak=leak, seed=r, draws=draws)
    return out


def matrix(reps: int, workers: int, draws: int) -> dict:
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(one, [(r, draws) for r in range(reps)], chunksize=1))
    res = {}
    for key in rows[0]:
        res[key] = {g: sum(r[key][g] for r in rows) / reps for g in ("G1", "G2", "G3", "non_vacuous", "disjoint")}
        res[key]["any_gate_fails"] = sum(not (r[key]["G1"] and r[key]["G2"] and r[key]["G3"]) for r in rows) / reps
        # the joint detection of every subset of gates: the share of draws in which at least one gate of the subset fails
        res[key]["subsets"] = {"+".join(sub): sum(not all(r[key][g] for g in sub) for r in rows) / reps
                               for sub in (("G1",), ("G2",), ("G3",), ("G1", "G2"), ("G1", "G3"), ("G2", "G3"), ("G1", "G2", "G3"))}
    return {"reps": reps, "n": N, "p": P, "seed": SEED, "g3_draws": draws, "pass_rates": res}


def draws_study(reps: int, workers: int) -> dict:
    out = {}
    for kind in ("woe", "linear"):
        jobs = [(kind, r) for r in range(reps)]
        with ProcessPoolExecutor(workers) as ex:
            rows = list(ex.map(_draw_one, jobs, chunksize=1))
        out[kind] = {str(d): float(np.mean([row[d] for row in rows])) for d in (1, 2, 3, 5)}
    return {"reps": reps, "seed": SEED, "detection_by_draws": out}


def _draw_one(job: tuple[str, int]) -> dict:
    kind, r = job
    rng = np.random.default_rng(np.random.SeedSequence([SEED, 7, r]))
    X, y = L.planted(N, P, rng)
    train, cal, hold = L.stratified_slices(y, rng)
    base = L.fit_pipeline(X, y, train, cal, hold, kind=kind, leak="select_test")
    changed = []
    for _ in range(5):
        X3, y3 = L.perturbed(X, y, hold, rng)
        f = L.fit_pipeline(X3, y3, train, cal, hold, kind=kind, leak="select_test")
        changed.append(not (L._same(base.transforms(), f.transforms()) and L._same(base.calibration(), f.calibration())))
    return {d: bool(any(changed[:d])) for d in (1, 2, 3, 5)}


def ladder() -> dict:
    """The three conditions of the product's tests on its own ladder, with the outside information changed as the test does."""
    import pandas as pd
    from sklearn.model_selection import RepeatedStratifiedKFold

    from pipeline.cases.c01_ladder import fit_ladder
    from pipeline.stages import split

    feats = ("risk_up", "risk_down", "segment_code", "noise")
    cat = ("segment_code",)
    mono = {"risk_up": +1, "risk_down": -1, "segment_code": 0, "noise": 0}

    def data(n=2400, seed=3):  # the planted sample of tests/test_leakage.py
        g = np.random.default_rng(seed)
        x1, x2, seg = g.normal(size=n), g.normal(size=n), g.integers(0, 4, size=n)
        eta = -1.2 + 0.9 * x1 - 0.6 * x2 + np.array([0.0, 0.3, -0.2, 0.5])[seg]
        y = (g.random(n) < 1.0 / (1.0 + np.exp(-eta))).astype(int)
        return pd.DataFrame({"risk_up": x1, "risk_down": x2, "segment_code": seg, "noise": g.normal(size=n), "target": y})

    X = data()
    y = X["target"].to_numpy()
    sp = split.stratified_split(y, seed=7)

    def run(frame, tr, ca):
        yy = frame["target"].to_numpy()
        rskf = RepeatedStratifiedKFold(n_splits=5, n_repeats=2, random_state=9)
        folds = tuple(rskf.split(np.zeros(len(tr)), yy[tr]))
        rungs = fit_ladder(frame.iloc[tr], yy[tr], frame.iloc[ca], yy[ca], folds, features=feats, categorical=cat, monotone=mono,
                           seed=11, with_xgboost=False)
        return {rid: r.record()["checkpoint_sha256"] for rid, r in rungs.items()}

    def moved(frame):
        m = frame.copy()
        g = np.random.default_rng(5)
        hold = m.index[sp.holdout]
        m.loc[hold, "target"] = g.integers(0, 2, size=len(hold))
        m.loc[hold, "risk_up"] = g.normal(size=len(hold)) * 10
        m.loc[hold, "noise"] = g.normal(5.0, 4.0, size=len(hold))
        return m

    Xm = moved(X)
    conds = {
        "protocol": (sp.train, sp.calibration),
        "fit_on_train_and_holdout": (np.sort(np.concatenate([sp.train, sp.holdout])), sp.calibration),
        "calibration_on_holdout": (sp.train, sp.holdout),
    }
    out = {}
    for name, (tr, ca) in conds.items():
        t0 = time.time()
        a, b = run(X, tr, ca), run(Xm, tr, ca)
        out[name] = {"rungs": len(a), "rungs_changed": sum(a[k] != b[k] for k in a), "calibration_disjoint_from_holdout": not (set(ca) & set(sp.holdout)),
                     "train_disjoint_from_holdout": not (set(tr) & set(sp.holdout)), "seconds": round(time.time() - t0, 1)}
        print(name, out[name], flush=True)
    return {"n": len(y), "holdout_n": int(len(sp.holdout)), "conditions": out}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["matrix", "draws", "ladder"])
    ap.add_argument("--reps", type=int, default=100)
    ap.add_argument("--workers", type=int, default=30)
    ap.add_argument("--g3-draws", type=int, default=1)
    ap.add_argument("--out", default=str(HERE / "results"))
    a = ap.parse_args()
    t0 = time.time()
    res = {"matrix": lambda: matrix(a.reps, a.workers, a.g3_draws), "draws": lambda: draws_study(a.reps, a.workers),
           "ladder": ladder}[a.mode]()
    res["seconds"] = round(time.time() - t0, 1)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"e2_{a.mode}.json").write_text(json.dumps(res, indent=1), encoding="utf-8", newline="\n")
    print(a.mode, "done in", res["seconds"], "s")


if __name__ == "__main__":
    main()
