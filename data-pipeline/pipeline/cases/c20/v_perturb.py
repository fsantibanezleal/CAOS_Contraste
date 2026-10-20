"""The perturbation grid: the Taiwan P4 LightGBM rung against Gaussian input noise of 0.05 to 1 standard deviation (06 C.7 l.1009-1012).

The noise is added to the evaluation features only (the locked holdout, never the training slice) and is the engine's own
(``perturb_features``, the same draws at every scale, so the perturbed sets are nested). AUC and Brier are read against the scale; the
finding is the engine's: the AUC loss exceeds the tolerance at the preset scale 0.1. A categorical feature stored as an integer code is
read as the nearest integer code. The overfit gap and the weak spots (slices of the repayment status of September, where the squared
error exceeds twice the average) are read on the same model. A control curve keeps every exactly-zero cell at zero: the boosted rungs read an
exact zero as a bin of its own, so noise on a zero moves the row, and the control shows how much of the loss that accounts for. The decision-flip impact block is the share of holdout decisions that change
at the fixed cut-off under each noise scale.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from . import battery, fits, ops
from .conv import PERTURBATION_GRID, PERTURBATION_TOLERANCE, PRESET_EPS, REJECT_SHARE, WEAK_SPOT_MULTIPLE, impact_cutoff, parameters_block, t
from . import data
from .data import Frame


def zeros_kept_curve(pred: Any, X: np.ndarray, y: np.ndarray, grid: list[float], seed: int) -> Any:
    """The control of the grid: the engine's noise at each scale, with every cell that is exactly zero left at zero. The boosted rungs treat an
    exact zero as a bin of its own (the repayment status 0, a payment of 0), so additive noise on a zero moves a row to another bin; the
    control isolates that effect. The curve is built from the engine's noise and the engine's AUC routine and read by the engine's test."""
    from riskvalidation.ml import robustness as rb

    auc0, brier0 = ops.auc_brier(pred(X), y)
    auc, brier = [auc0], [brier0]
    for eps in grid:
        noisy = rb.perturb_features(X, eps, seed)
        a, b = ops.auc_brier(pred(np.where(X == 0.0, X, noisy)), y)
        auc.append(a)
        brier.append(b)
    return rb.RobustnessCurve(grid=(0.0, *grid), auc=tuple(auc), brier=tuple(brier), auc_delta=tuple(a - auc0 for a in auc))


def build(frame: Frame, rungs: dict[str, Any], seed: int) -> dict[str, Any]:
    from riskvalidation.ml import generalisation as gen
    from riskvalidation.ml import robustness as rb
    from riskvalidation.validation import ml as mlv

    rung = rungs["P4-lightgbm"]
    mid = fits.rung_id("P4-lightgbm", frame)
    pred = fits.predictor(rung, frame)
    hold = frame.hold
    data.assert_locked(frame)
    data.assert_evaluation_only(frame, hold)
    Xh, yh = fits.matrix(frame, hold), frame.y[hold]
    curve = rb.robustness_curve(pred, Xh, yh, PERTURBATION_GRID, seed)
    p0 = pred(Xh)
    cut = fits.cutoff(p0, REJECT_SHARE)
    rows, flips = [], []
    for k, eps in enumerate(curve.grid):
        rows.append({"eps": float(eps), "metric": {"auc": curve.auc[k], "brier": curve.brier[k], "auc_delta": curve.auc_delta[k]},
                     "finding": bool(rb.robustness_finding(curve, PERTURBATION_TOLERANCE, eps))})
        if eps > 0:
            flips.append({"shift_id": f"noise-{eps:g}", "flip_share": fits.flip_share(p0, pred(rb.perturb_features(Xh, eps, seed)), cut),
                          "n_decisions": int(len(hold))})
    tests = [ops.row(mlv.robustness(mid, curve, PERTURBATION_TOLERANCE, PRESET_EPS), segment=f"preset-eps-{PRESET_EPS:g}")]
    tests.append(ops.row(mlv.robustness(mid, zeros_kept_curve(pred, Xh, yh, PERTURBATION_GRID, seed), PERTURBATION_TOLERANCE, PRESET_EPS),
                         segment=f"control-zeros-kept:preset-eps-{PRESET_EPS:g}"))
    Xtr_df, ytr = frame.part("train")
    Xh_df = frame.X.iloc[hold]
    tests.append(ops.row(mlv.overfit(mid, gen.overfit_gap(ops.auc_brier(rung.pd(Xtr_df), ytr)[0], ops.auc_brier(p0, yh)[0], 0.05)),
                         segment="train-vs-holdout"))
    err = (p0 - yh) ** 2
    slices = np.clip(Xh_df["PAY_0"].to_numpy(dtype=int), -2, 8)
    spots = gen.weak_spots(err, slices, WEAK_SPOT_MULTIPLE)
    tests.append(ops.row(mlv.weak_spot(mid, spots, WEAK_SPOT_MULTIPLE, int(len(np.unique(slices)))), segment="slices-of-PAY_0"))
    # the battery at the preset noise scale: the decisions are those of the noisy inputs, the cut-off the clean one
    noisy = pred(rb.perturb_features(Xh, PRESET_EPS, seed))
    bat, bat_rows = battery.run(mid, noisy, cut, frame.X.iloc[hold], yh)
    tests.extend(bat_rows)
    outputs = {"kind": "perturbation", "dataset_id": "uci-taiwan", "model_dataset": "uci-taiwan", "sgcd_notice": None,
               "parameters": parameters_block(), "fairness_battery": bat,
               "impact_detail": {"label": "decision-flip", "cutoff": impact_cutoff(), "rows": flips},
               "requirements": ["CT-2013", "CT-2014", "CT-2016", "CT-2022"], "preset_eps": PRESET_EPS, "rows": rows}
    impact = {"decision_flip_share": {"value": max(f["flip_share"] for f in flips), "unit": "share",
                                      "label": t("Decisions that flip at the stated cut-off under input noise, largest over the scales",
                                                 "Decisiones que cambian en el punto de corte indicado con ruido de entrada, la mayor entre las escalas")}}
    return {"outputs": outputs, "tests": tests, "impact": impact, "models": [mid],
            "limits": [("noise-on-codes", t("The noise is added to every feature including the coded ones; a coded feature is read as the nearest integer code",
                                            "El ruido se suma a todas las variables, también las codificadas; una variable codificada se lee como el código entero más cercano"))]}
