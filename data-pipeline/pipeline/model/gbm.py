"""P4, monotone gradient boosting with an explicit calibration map (dossier 04 B.1 and the PD ladder).

LightGBM with ``monotone_constraints`` on every feature with a declared direction (method "advanced", the less
over-constraining one in the LightGBM documentation), the number of rounds chosen by early stopping on the training
folds; XGBoost with the same constraints as the engine cross-check (``tree_method="hist"`` with ``max_bin=512``,
since the XGBoost documentation warns that constraints can wipe out split candidates at the default binning). The
isotonic calibration map is fitted on the calibration slice. Three checks ride along:

- monotonicity on the partial-dependence grid: individual conditional expectation curves of the raw score, on 200
  training records and a grid of up to 30 quantiles of each constrained feature, never move against the declared
  direction (CT-110);
- reason codes: the four features with the largest risk-raising SHAP contributions (TreeSHAP, log-odds scale;
  Lundberg et al. 2020), the Regulation B practice of at most four principal reasons (dossier 04 J.1, J.2);
- reason-code stability: the mean overlap of the top four reasons between the model and 10 models refitted on
  bootstrap resamples of the training slice, for the same 200 holdout records.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

LGB_PARAMS = {
    "objective": "binary", "learning_rate": 0.05, "num_leaves": 15, "min_child_samples": 100,
    "feature_fraction": 0.9, "bagging_fraction": 0.9, "bagging_freq": 1, "lambda_l2": 1.0,
    "monotone_constraints_method": "advanced", "deterministic": True, "force_row_wise": True, "verbose": -1,
}
MAX_ROUNDS = 2000
EARLY_STOP = 50


@dataclass
class GBM:
    engine: str
    model: Any
    features: list[str]
    constraints: list[int]
    rounds: int
    params: dict = field(default_factory=dict)
    #: integer codes of each categorical feature, learned on the training slice (an unseen category is missing)
    codes: dict = field(default_factory=dict)

    def matrix(self, X: pd.DataFrame) -> np.ndarray:
        return encode(X, self.features, self.codes)

    def raw_logit(self, X: pd.DataFrame) -> np.ndarray:
        if self.engine == "lightgbm":
            return np.asarray(self.model.predict(self.matrix(X), raw_score=True), dtype=float)
        import xgboost as xgb

        return np.asarray(self.model.predict(xgb.DMatrix(self.matrix(X)), output_margin=True), dtype=float)

    def predict_pd(self, X: pd.DataFrame) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-self.raw_logit(X)))


def learn_codes(X: pd.DataFrame, categorical) -> dict[str, dict[str, int]]:
    return {f: {c: k for k, c in enumerate(sorted({str(v) for v in X[f]}))} for f in categorical}


def encode(X: pd.DataFrame, features, codes: dict[str, dict[str, int]]) -> np.ndarray:
    cols = []
    for f in features:
        if f in codes:
            cols.append(np.array([codes[f].get(str(v), np.nan) for v in X[f]], dtype=float))
        else:
            cols.append(X[f].to_numpy(dtype=float))
    return np.column_stack(cols)


def _constraints(features, categorical, monotone) -> list[int]:
    return [0 if f in categorical else int(monotone.get(f, 0)) for f in features]


def fit_lightgbm(X: pd.DataFrame, y: np.ndarray, folds, *, features, categorical, monotone, seed: int,
                 rounds: int | None = None, codes: dict | None = None) -> GBM:
    import lightgbm as lgb

    cons = _constraints(features, categorical, monotone)
    params = {**LGB_PARAMS, "monotone_constraints": cons, "seed": seed}
    codes = codes if codes is not None else learn_codes(X, categorical)
    M = encode(X, list(features), codes)
    y = np.asarray(y, dtype=int)
    if rounds is None:
        ds = lgb.Dataset(M, y, free_raw_data=False)
        cv = lgb.cv(params, ds, num_boost_round=MAX_ROUNDS, folds=list(folds), stratified=False,
                    callbacks=[lgb.early_stopping(EARLY_STOP, verbose=False)])
        rounds = len(next(iter(cv.values())))
    booster = lgb.train(params, lgb.Dataset(M, y), num_boost_round=rounds)
    return GBM("lightgbm", booster, list(features), cons, rounds, params, codes)


def fit_xgboost(X: pd.DataFrame, y: np.ndarray, folds, *, features, categorical, monotone, seed: int) -> GBM:
    import xgboost as xgb

    cons = _constraints(features, categorical, monotone)
    params = {"objective": "binary:logistic", "eta": 0.05, "max_depth": 4, "min_child_weight": 20,
              "subsample": 0.9, "colsample_bytree": 0.9, "lambda": 1.0, "tree_method": "hist", "max_bin": 512,
              "monotone_constraints": "(" + ",".join(str(c) for c in cons) + ")", "seed": seed,
              "eval_metric": "logloss", "nthread": 1}
    codes = learn_codes(X, categorical)
    M = encode(X, list(features), codes)
    y = np.asarray(y, dtype=int)
    cv = xgb.cv(params, xgb.DMatrix(M, label=y), num_boost_round=MAX_ROUNDS, folds=list(folds),
                early_stopping_rounds=EARLY_STOP, verbose_eval=False)
    rounds = len(cv)
    booster = xgb.train(params, xgb.DMatrix(M, label=y), num_boost_round=rounds)
    return GBM("xgboost", booster, list(features), cons, rounds, params, codes)


def monotonicity(gbm: GBM, X_ref: pd.DataFrame, *, seed: int, n_rows: int = 200, grid: int = 30) -> dict:
    """ICE curves of the raw logit along each constrained feature; the largest move against its direction."""
    rng = np.random.default_rng(seed)
    rows = X_ref.iloc[rng.choice(len(X_ref), size=min(n_rows, len(X_ref)), replace=False)]
    out: dict[str, Any] = {"rows": int(len(rows)), "features": {}}
    levels = np.linspace(0.0, 1.0, grid)
    out["levels"] = levels.tolist()
    for f, c in zip(gbm.features, gbm.constraints):
        if c == 0:
            continue
        # the grid is the feature's quantiles at fixed levels, repeats kept, so every feature's partial dependence
        # shares one axis (the quantile level) in the views
        values = np.quantile(X_ref[f].to_numpy(dtype=float), levels)
        curves = np.empty((len(rows), len(values)))
        for k, v in enumerate(values):
            probe = rows.copy()
            probe[f] = v
            curves[:, k] = gbm.raw_logit(probe)
        steps = np.diff(curves, axis=1) * c  # positive is the declared direction
        worst = float(-steps.min()) if steps.size else 0.0
        out["features"][f] = {"direction": c, "grid": values.tolist(),
                              "pdp": curves.mean(axis=0).tolist(), "max_violation": max(worst, 0.0) + 0.0}
    out["monotone"] = all(v["max_violation"] <= 1e-12 for v in out["features"].values())
    return out


def reason_codes(gbm: GBM, X: pd.DataFrame, k: int = 4) -> tuple[np.ndarray, np.ndarray]:
    """TreeSHAP contributions on the log-odds scale and, per record, the k features that raise the risk most."""
    import shap

    phi = np.asarray(shap.TreeExplainer(gbm.model).shap_values(gbm.matrix(X)), dtype=float)
    if phi.ndim == 3:  # some versions return one array per class
        phi = phi[..., -1]
    top = np.argsort(-phi, axis=1)[:, :k]
    return phi, top


def reason_stability(gbm: GBM, X_train: pd.DataFrame, y_train: np.ndarray, X_rows: pd.DataFrame, *,
                     categorical, monotone, seed: int, n_boot: int = 10) -> dict:
    _, base = reason_codes(gbm, X_rows)
    rng = np.random.default_rng(seed)
    overlaps = []
    for b in range(n_boot):
        ix = rng.integers(0, len(y_train), len(y_train))
        refit = fit_lightgbm(X_train.iloc[ix], np.asarray(y_train)[ix], (), features=gbm.features,
                             categorical=categorical, monotone=monotone, seed=seed + b + 1, rounds=gbm.rounds,
                             codes=gbm.codes)
        _, top = reason_codes(refit, X_rows)
        overlaps.append(np.mean([len(set(a) & set(t)) / 4.0 for a, t in zip(base, top)]))
    return {"bootstraps": n_boot, "rows": int(len(X_rows)), "top_k": 4,
            "overlap_mean": float(np.mean(overlaps)), "overlap_min": float(np.min(overlaps)),
            "overlap": [float(o) for o in overlaps]}


def record(gbm: GBM) -> dict:
    keep = {k: v for k, v in gbm.params.items() if k not in ("verbose",)}
    return {"engine": gbm.engine, "rounds": gbm.rounds, "constraints": dict(zip(gbm.features, gbm.constraints)),
            "categorical_codes": gbm.codes,
            "params": {k: (v if isinstance(v, (int, float, str, bool)) else str(v)) for k, v in keep.items()}}
