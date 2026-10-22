"""The battery of one rung on the holdout of one document, the challenger table and the transfer block, all through ``riskvalidation``.

Every statistic is the engine's: AUC with its DeLong interval (``disc_auc``), KS, Hosmer-Lemeshow, Brier, ECE with its bins, the
Jeffreys and binomial level tests, the PSI of the PD and the CSI of each input against the training slice, the overfit gap, the DeLong
difference against the champion, the paired Brier bootstrap and the grade disagreement. What this module adds is the evaluation design
(which arrays each call reads) and the curves the views draw. The ROC and CAP points are geometry (scikit-learn's ``roc_curve``, which
handles the ties of a calibration step function), not a statistic.

A descriptive engine row (AUC, KS, Brier, ECE) has no light: its figure is the rung's entry in ``outputs`` and the row is not copied to
``tests``, because the contract refuses a ``not_evaluated`` row that carries a number.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.stats import norm

from ...core.calibration import MASTER_SCALE_UPPER
from ...stages import evaluate
from . import conventions as cv
from .fits import Fit

PORTFOLIO = evaluate.PORTFOLIO
LEVEL = 0.95
TIE = 1e-12   # two bins whose mean PDs differ by no more than this hold the same step of a calibration map


def _imports():
    from riskvalidation.harness.rates import wilson_interval
    from riskvalidation.ml import challenger as ch
    from riskvalidation.ml import generalisation as gen
    from riskvalidation.validation import calibration as cal
    from riskvalidation.validation import discrimination as disc
    from riskvalidation.validation import ml
    from riskvalidation.validation import stability as st

    return wilson_interval, ch, gen, cal, disc, ml, st


def keep(row: dict[str, Any]) -> bool:
    """A test row is kept when it has a light, or when it is `not_evaluated` with no number (the contract's missing-data rule)."""
    if row["light"] != "not_evaluated":
        return True
    return row["statistic"] is None and row["p_value"] is None and row["metric"] is None and bool(row["notes"])


def curves(p: np.ndarray, y: np.ndarray, points: int = 101) -> tuple[dict[str, list[float]], dict[str, Any]]:
    """ROC and CAP of the holdout, riskier first, ties joined by a straight line, decimated to about ``points`` points."""
    from sklearn.metrics import roc_curve

    y = np.asarray(y, dtype=int)
    fpr, tpr, _ = roc_curve(y, p, drop_intermediate=False)
    n_pos, n_neg = int(y.sum()), int(len(y) - y.sum())
    pop = (tpr * n_pos + fpr * n_neg) / len(y)
    rx, ry = evaluate._decimate(fpr, tpr, points)
    cx, cy = evaluate._decimate(pop, tpr, points)
    return {"fpr": rx, "tpr": ry}, {"population": cx, "defaults": cy, "default_rate": float(y.mean())}


def reliability_bins(ece_row: dict[str, Any]) -> list[dict[str, Any]]:
    """The reliability diagram from the engine's ECE bins: bins with the same mean PD are merged (a calibration map is a step function,
    and the contract wants strictly increasing PDs), the interval of the observed rate is the Wilson interval of the engine."""
    wilson, *_ = _imports()
    merged: list[list[float]] = []                       # n, defaults, pd
    for b in ece_row["extras"]["bins"]:
        d = round(b["default_rate"] * b["n"])
        if merged and b["mean_pd"] - merged[-1][2] <= TIE:
            pd_sum = merged[-1][2] * merged[-1][0] + b["mean_pd"] * b["n"]      # the n-weighted mean PD of the merged bins
            merged[-1][0] += b["n"]
            merged[-1][1] += d
            merged[-1][2] = pd_sum / merged[-1][0]
        else:
            merged.append([b["n"], d, b["mean_pd"]])
    out = []
    for n, d, pdv in merged:
        lo, hi = wilson(int(d), int(n))
        dr = d / n
        out.append({"n": int(n), "pd": float(pdv), "dr": float(dr), "lo": float(min(lo, dr)), "hi": float(max(hi, dr))})
    return out


def csi_max_and_rows(fit: Fit) -> tuple[float, list[dict[str, Any]]]:
    """The CSI of every input against the training slice (one row per input, no model): the rows and the largest value."""
    rows = [r for r in evaluate.csi_rows(fit.Xtr, fit.Xhold, list(fit.pp.columns), ()) if keep(r)]
    vals = [r["metric"] if r["metric"] is not None else r["statistic"] for r in rows]
    return float(max(vals)), rows


def _value(row: dict[str, Any]) -> float:
    return float(row["metric"] if row["metric"] is not None else row["statistic"])


def rung_result(fit: Fit, rid: str, model_id: str, csi_max: float) -> tuple[dict[str, Any], list[dict[str, Any]], np.ndarray]:
    """The rung entry of ``outputs.rungs``, its test rows and its holdout PDs."""
    _, _, gen, cal, disc, ml, st = _imports()
    rung = fit.rungs[rid]
    p, ptr, y, ytr = rung.pd(fit.Xhold), rung.pd(fit.Xtr), fit.yhold, fit.ytr
    kw = {"model_id": model_id, "segment": PORTFOLIO}
    auc = disc.disc_auc(p, y, **kw)
    ks = disc.disc_ks(p, y, **kw)
    hl = cal.pd_hosmer_lemeshow(y, p, fitted=False, **kw)
    brier = cal.pd_brier(y, p, **kw)
    ece = cal.pd_ece(y, p, **kw)
    n, d, mean_pd = int(len(y)), int(y.sum()), float(np.mean(p))
    jeffreys = cal.pd_jeffreys(n, d, mean_pd, **kw)
    binomial = cal.pd_binomial(n, d, mean_pd, **kw)
    edges = st.quantile_edges(ptr, 10)
    psi = st.stability_psi(st.bin_counts(ptr, edges), st.bin_counts(p, edges), **kw)
    train_auc = disc.disc_auc(ptr, ytr, model_id=model_id, segment="training").metric
    og = gen.overfit_gap(train_auc, auc.metric, cv.OVERFIT_TOLERANCE)
    overfit = ml.overfit(model_id, og)
    overfit_row = overfit.to_dict()
    overfit_row["segment"] = PORTFOLIO
    roc, cap = curves(p, y)
    block = {
        "model_id": model_id, "rung": cv.RUNG_CODE[rid], "roc": roc, "cap": cap, "reliability": reliability_bins(ece.to_dict()),
        "discrimination": {"auc": auc.metric, "auc_ci": {"lo": auc.extras["ci95_low"], "hi": auc.extras["ci95_high"], "level": LEVEL,
                                                          "method": "delong"}, "gini": auc.extras["gini"], "ks": ks.metric},
        "calibration": {"brier": brier.metric, "ece": ece.metric,
                        "hosmer_lemeshow": {"statistic": hl.statistic, "df": int(hl.extras["dof"]), "p_value": hl.p_value}},
        "overfit": {"train_auc": train_auc, "holdout_auc": auc.metric, "gap": og.gap, "tolerance": og.tolerance, "flag": og.flag},
        "stability": {"psi": _value(psi.to_dict()), "csi_max": csi_max}}
    rows = [r for r in (hl.to_dict(), jeffreys.to_dict(), binomial.to_dict(), psi.to_dict(), overfit_row) if keep(r)]
    return block, rows, p


def challenger_table(fit: Fit, hid: str, pds: dict[str, np.ndarray], seed: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Each learned rung against the P1 scorecard: the DeLong difference (the interval from the engine's variance), the paired Brier
    bootstrap and the grade disagreement; plus the engine rows of the two tests."""
    _, ch, _, _, disc, ml, _ = _imports()
    champ_id = f"{hid}-{cv.CHAMPION}"
    champ, y = pds[cv.CHAMPION], fit.yhold
    z = float(norm.ppf(0.5 + LEVEL / 2))
    edges = np.array(MASTER_SCALE_UPPER[:-1])
    table, rows = [], []
    for rid in cv.CHALLENGERS:
        mid = f"{hid}-{rid}"
        p = pds[rid]
        dl = disc.disc_delong(p, champ, y, model_id=mid, segment=PORTFOLIO)
        diff = dl.extras["difference"]
        half = z * math.sqrt(dl.extras["variance"])
        pb = ch.paired_brier_bootstrap(champ, p, y, cv.N_BOOT, seed + cv.BOOT_SEED_OFFSET)
        brier_row = ml.challenger_brier(mid, pb).to_dict()
        brier_row["segment"] = PORTFOLIO
        table.append({
            "champion": champ_id, "challenger": mid, "auc_diff": diff,
            "auc_diff_ci": {"lo": diff - half, "hi": diff + half, "level": LEVEL, "method": "delong"}, "delong_p_value": dl.p_value,
            "brier_diff": pb.diff, "brier_diff_ci": {"lo": pb.lo, "hi": pb.hi, "level": LEVEL, "method": "paired-bootstrap"},
            "grade_disagreement_share": ch.grade_disagreement(champ, p, edges, cv.GRADE_NOTCHES)})
        rows += [r for r in (dl.to_dict(), brier_row) if keep(r)]
    return table, rows


def transfer_block(fits: dict[str, Fit], fit: Fit) -> dict[str, Any]:
    """The rungs fitted on this document's file, scored on the locked holdout of each file (exploratory). The pooled variant has none."""
    _, _, _, _, disc, _, _ = _imports()
    cells: list[dict[str, Any]] = []
    if fit.years is not None:
        for rid in cv.TRANSFER_RUNGS:
            for j in range(1, 6):
                g = fits[f"h{j}"]
                p = fit.rungs[rid].pd(fit.pp.transform(g.X.iloc[g.sp.holdout]))
                cells.append({"rung": cv.RUNG_CODE[rid], "model_id": rid, "fitted_on_years": fit.years, "scored_on_years": j,
                              "auc": disc.disc_auc(p, g.yhold).metric, "n": int(len(g.yhold)), "events": int(g.yhold.sum())})
    return {"label": "exploratory", "reason": cv.TRANSFER_REASON, "cells": cells}
