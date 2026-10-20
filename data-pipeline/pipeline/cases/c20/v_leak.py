"""The planted leak: a feature built from the outcome added to the Taiwan training set, caught by the engine's leakage screen while the
model's performance collapses at decision time.

The leak is ``future_status_code``: the default flag plus Gaussian noise of 0.2 (seed 42), dated one month after the observation date. The
P4 LightGBM rung is fitted with it on the training slice and scored on the locked holdout with it (the development performance, as a leak
makes it look) and with its values replaced by a random permutation across the holdout rows (decision time: the code does not exist when the
decision is taken, so it carries nothing about the row). The engine screens the data of both models, the leaking one and the clean control:

- temporal order: the cells of the feature dates matrix dated after the observation date (the payment months April to September 2005 are
  dated at their month end, the observation date is 2005-09-30, the planted feature is dated 2005-10-31; features with no date, the limit
  and the education, are NaT and never a violation);
- the near-perfect single feature: the largest max(AUC, 1 - AUC) of one column;
- the entity overlap between the training and the holdout identifiers;
- the resemblance AUC between the development rows and the holdout rows (Taiwan has no out-of-time sample: the holdout stands in for it).

The cut points are the engine's policy values, named in the document with their label.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ...core.calibration import clip_pd, fit_isotonic
from ...io.readers import TAIWAN_BILL, TAIWAN_PAID, TAIWAN_PAY
from ...model import gbm
from ..c01_ladder import Rung
from . import battery, fits, ops
from .conv import REJECT_SHARE, impact_cutoff, parameters_block, t
from .data import Frame

LEAK = "future_status_code"
LEAK_NOISE = 0.2
OBSERVATION = np.datetime64("2005-09-30")
LEAK_DATE = np.datetime64("2005-10-31")
MONTH_ENDS = [np.datetime64(d) for d in ("2005-09-30", "2005-08-31", "2005-07-31", "2005-06-30", "2005-05-31", "2005-04-30")]


def feature_dates(features: tuple[str, ...], with_leak: bool) -> np.ndarray:
    """The date each feature's value refers to, one row of dates per feature column (the same for every row)."""
    by_name: dict[str, np.datetime64] = {}
    for cols in (TAIWAN_PAY, TAIWAN_BILL, TAIWAN_PAID):
        for c, d in zip(cols, MONTH_ENDS):
            by_name[c] = d
    nat = np.datetime64("NaT")
    row = [by_name.get(f, nat) for f in features]
    if with_leak:
        row = [*row, LEAK_DATE]
    return np.array(row, dtype="datetime64[D]")


def planted_column(y: np.ndarray, seed: int) -> np.ndarray:
    return y.astype(float) + np.random.default_rng([seed, 3]).normal(0.0, LEAK_NOISE, len(y))


def _fit_leaky(frame: Frame, Xtr: pd.DataFrame, ytr: np.ndarray, Xcal: pd.DataFrame, ycal: np.ndarray, rounds: int, seed: int):
    feats = (*frame.features, LEAK)
    mono = {**frame.monotone, LEAK: 0}
    folds = frame.folds
    model = gbm.fit_lightgbm(Xtr, ytr, folds, features=feats, categorical=frame.categorical, monotone=mono, seed=seed)
    iso = fit_isotonic(clip_pd(model.predict_pd(Xcal)), ycal)
    return model, iso


def screen(model_id: str, X: np.ndarray, y: np.ndarray, X_dev: np.ndarray, dates: np.ndarray, train_ids: list[str], test_ids: list[str],
           seed: int, names: tuple[str, ...]) -> tuple[dict[str, Any], dict[str, Any]]:
    from riskvalidation.ml import leakage as lk
    from riskvalidation.validation import ml as mlv

    temporal = lk.temporal_order_violations(np.tile(dates, (len(X), 1)), np.full(len(X), OBSERVATION, dtype="datetime64[D]"))
    single = lk.single_feature_auc(X, y, 0.95)
    overlap = lk.entity_overlap(train_ids, test_ids)
    resem = lk.resemblance_auc(X_dev, X, seed)
    res = mlv.leakage_screen(model_id, temporal, single, overlap, resem)
    block = {"temporal_order": {"violations": int(temporal)},
             "single_feature_auc": {"max_auc": float(single.max_auc), "feature": names[single.feature], "suspect": bool(single.suspect)},
             "entity_overlap": {"share": float(overlap)}, "resemblance_auc": float(resem.auc)}
    return block, ops.row(res, segment="screen")


def build(frame: Frame, rungs: dict[str, Any], seed: int) -> dict[str, Any]:
    from riskvalidation.ml import policy as pol

    Xtr_df, ytr = frame.part("train")
    Xcal_df, ycal = frame.part("cal")
    Xh_df, yh = frame.part("hold")
    # the planted column, in every slice (the leak lives in the data, as a leaking extract would)
    leak = planted_column(frame.y, seed)
    Xl = frame.X.copy()
    Xl[LEAK] = leak
    Xtr, Xcal, Xh = Xl.iloc[frame.train], Xl.iloc[frame.cal], Xl.iloc[frame.hold]
    base = rungs["P4-lightgbm"]
    model, iso = _fit_leaky(frame, Xtr, ytr, Xcal, ycal, base.model.rounds, seed)
    leaky = Rung("P4-lightgbm", "P4", base.title, base.engine, base.engine_version, base.licence, model, calibration=iso, parameters=base.parameters)
    feats = (*frame.features, LEAK)
    mid_leaky = f"P4-lightgbm-{frame.name}-planted-leak"
    mid_clean = fits.rung_id("P4-lightgbm", frame)
    dev_auc = ops.auc_brier(leaky.pd(Xh), yh)[0]
    permuted = Xh.copy()
    permuted[LEAK] = np.random.default_rng([seed, 4]).permutation(permuted[LEAK].to_numpy())
    p_dec = leaky.pd(permuted)
    dec_auc = ops.auc_brier(p_dec, yh)[0]
    # the screens
    ids = frame.X["id"].astype(str).to_numpy()
    train_ids, test_ids = list(ids[frame.train]), list(ids[frame.hold])
    X_dev_leak = Xl.iloc[frame.dev_index()][list(feats)].to_numpy(dtype=float)
    X_h_leak = Xh[list(feats)].to_numpy(dtype=float)
    planted_block, planted_row = screen(mid_leaky, X_h_leak, yh, X_dev_leak, feature_dates(frame.features, True), train_ids, test_ids, seed, feats)
    X_dev_clean = frame.X.iloc[frame.dev_index()][list(frame.features)].to_numpy(dtype=float)
    X_h_clean = fits.matrix(frame, frame.hold)
    _, control_row = screen(mid_clean, X_h_clean, yh, X_dev_clean, feature_dates(frame.features, False), train_ids, test_ids, seed, frame.features)
    policy = pol.ml_policy()
    single_limit = round(float(policy.threshold("ml.leakage_screen.single_feature_auc").amber), 2)
    resem_limit = round(float(policy.threshold("ml.leakage_screen.resemblance_auc").amber), 2)
    caught = bool(planted_block["single_feature_auc"]["suspect"] or planted_block["temporal_order"]["violations"] > 0
                  or planted_block["entity_overlap"]["share"] > 0 or planted_block["resemblance_auc"] > resem_limit)
    # the decisions at decision time and the fairness battery on them
    cut = fits.cutoff(leaky.pd(Xh), REJECT_SHARE)
    bat, bat_rows = battery.run(mid_leaky, p_dec, cut, Xh_df, yh)
    flips = [{"shift_id": "decision-time-leak-unavailable", "flip_share": fits.flip_share(leaky.pd(Xh), p_dec, cut), "n_decisions": int(len(yh))}]
    outputs = {"kind": "leakage", "dataset_id": "uci-taiwan", "model_dataset": "uci-taiwan", "sgcd_notice": None, "parameters": parameters_block(),
               "fairness_battery": bat, "impact_detail": {"label": "decision-flip", "cutoff": impact_cutoff(), "rows": flips},
               "requirements": ["CT-2015", "CT-2016", "CT-2022"], "planted_feature": LEAK,
               "thresholds": {"single_feature_auc": {"value": single_limit, "label": "convention"},
                              "resemblance_auc": {"value": resem_limit, "label": "convention"}},
               "screen": planted_block, "caught": caught, "performance": {"development_auc": dev_auc, "decision_time_auc": dec_auc}}
    impact = {"decision_flip_share": {"value": flips[0]["flip_share"], "unit": "share",
                                      "label": t("Decisions that flip at the stated cut-off when the leaking feature is unavailable at decision time",
                                                 "Decisiones que cambian en el punto de corte indicado cuando la variable filtrada no está disponible al decidir")}}
    return {"outputs": outputs, "tests": [planted_row, control_row, *bat_rows], "impact": impact, "models": [mid_leaky, mid_clean],
            "leaky": leaky, "limits": [("holdout-not-out-of-time", t("Taiwan has no out-of-time sample: the locked holdout stands in for it in the resemblance screen",
                                                                  "Taiwan no tiene una muestra fuera de tiempo: la muestra reservada la reemplaza en la prueba de semejanza")),
                                      ("planted-not-found", t("The leak is planted by construction, so the screen is shown catching a known leak; it does not show that a real extract has none",
                                                             "La fuga se planta por construcción, de modo que la prueba se muestra detectando una fuga conocida; no muestra que una extracción real no tenga ninguna"))]}
