"""E4: a random split inside the training window against the declared out-of-time cohort, on the SBA 7(a) loans of C03.

For each of the five test cohorts the product fits its ladder on the training window the protocol declares (approval fiscal years
whose 5-year outcome is observed before the cohort starts, ``pipeline.cases.c03.fit.fit_window``, seed 42 as the committed bake).
Two estimates of the same fitted models are then compared: (i) the random-split estimate a team would report without the declared
split, a random sample of the window's own loans that the fit and the calibration did not use, and (ii) the out-of-time estimate on the
cohort's vintages at their 5-year mark. The AUC and the level of the PD (observed minus predicted 5-year rate) are reported for every
rung. The run reproduces the committed C03 documents for the out-of-time column, which the script checks.

    CONTRASTE_DATA=<data root> python manuscripts/leakage-safe-validation-protocol/experiments/e4_out_of_time.py
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import time
from concurrent.futures import ProcessPoolExecutor

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "2")

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))
sys.path.insert(0, str(HERE))
import leaklab as L  # noqa: E402

SEED = 42
HOLD_N = 60_000


def one(idx: int) -> dict:
    from pipeline.cases.c03 import fit as fitting
    from pipeline.cases.c03 import panel, windows
    from pipeline.io import sba
    from pipeline.stages import split

    data = os.environ.get("CONTRASTE_DATA")
    if not data:
        sys.exit("set CONTRASTE_DATA to the data root that holds raw/sba-foia (the C03 source)")
    cohort = windows.COHORTS[idx]
    window = windows.training_window(cohort)
    windows.check_window(cohort, window)
    t0 = time.time()
    loans, _ = panel.prepare(sba.read_sba(pathlib.Path(data)))
    wf = fitting.fit_window(loans, window, SEED)
    # the random-split sample: loans of the window that neither the fit nor the calibration used
    pidx, y = fitting.training_data(loans, window)
    n = len(pidx)
    pos = np.arange(n)
    fit_pos = split.subsample(pos, y, min(fitting.FIT_N, int(0.7 * n)), seed=SEED)
    rest = np.setdiff1d(pos, fit_pos)
    cal_pos = rest if fitting.CAL_N >= len(rest) else split.subsample(rest, y, fitting.CAL_N, seed=SEED + 1)
    hold_pos = np.setdiff1d(rest, cal_pos)
    rng = np.random.default_rng(SEED + 7)
    hold_pos = np.sort(rng.choice(hold_pos, size=min(HOLD_N, len(hold_pos)), replace=False))
    Xh, yh = panel.features(loans, pidx[hold_pos]), y[hold_pos].astype(int)
    # the out-of-time sample: the cohort's vintages whose 5-year mark has passed
    asof = str(loans.asof)
    ln = loans.take(np.flatnonzero(np.isin(loans.fy, cohort.fiscal_years)))
    yo = panel.label(ln, asof)
    seen = np.isin(ln.fy, [fy for fy in cohort.fiscal_years if windows.mark_observed(fy, asof)]) & (yo != panel.LABEL_CENSORED)
    Xo, yo = panel.features(ln).loc[seen].reset_index(drop=True), yo[seen].astype(int)
    out = {"cohort": cohort.name, "id": cohort.id, "window": [window.first_fy, window.last_fy], "cutoff": window.cutoff, "window_loans": n,
           "fit_rows": int(len(fit_pos)), "cal_rows": int(len(cal_pos)), "random_holdout_rows": int(len(hold_pos)),
           "oot_rows": int(len(yo)), "random_rate": float(yh.mean()), "oot_rate": float(yo.mean()), "rungs": {}}
    for rid, rung in wf.rungs.items():
        ph, po = rung.pd(Xh), rung.pd(Xo)
        out["rungs"][rid] = {
            "random_auc": L.fast_auc(ph, yh) if rid != "P0-constant" else 0.5, "oot_auc": L.fast_auc(po, yo) if rid != "P0-constant" else 0.5,
            "random_gap": float(yh.mean() - ph.mean()), "oot_gap": float(yo.mean() - po.mean()),
            "random_brier": L.brier(ph, yh), "oot_brier": L.brier(po, yo), "random_pred": float(ph.mean()), "oot_pred": float(po.mean())}
    out["seconds"] = round(time.time() - t0, 1)
    print(cohort.name, out["seconds"], "s", flush=True)
    return out


def main() -> None:
    from pipeline.cases.c03 import windows

    with ProcessPoolExecutor(len(windows.COHORTS)) as ex:
        rows = list(ex.map(one, range(len(windows.COHORTS))))
    # the reproduction check: the out-of-time scorecard AUC against the committed document of each cohort
    check = {}
    for row in rows:
        doc = json.loads((ROOT / "data" / "derived" / "C03" / f"{row['id']}.json").read_text(encoding="utf-8"))
        sc = next(r for r in doc["outputs"]["rung_comparison"] if r["rung_id"] == "P1-scorecard")
        check[row["cohort"]] = {"committed_scorecard_auc": sc["auc"], "run_scorecard_auc": row["rungs"]["P1-scorecard"]["oot_auc"],
                                "committed_gap_5y": sc["calibration_gap_5y"], "run_gap": row["rungs"]["P1-scorecard"]["oot_gap"]}
    res = {"seed": SEED, "random_holdout_cap": HOLD_N, "cohorts": rows, "reproduction": check}
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "e4_out_of_time.json").write_text(json.dumps(res, indent=1), encoding="utf-8", newline="\n")
    print("e4 done")


if __name__ == "__main__":
    main()
