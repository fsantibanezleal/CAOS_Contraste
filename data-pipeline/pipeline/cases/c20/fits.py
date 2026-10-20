"""The ladder rungs of C20, the attributions and the effect curves, all on arrays for the engine.

The rungs are the C01 ladder (``cases/c01_ladder.py``, read and never changed). The engine imports no learning library: a rung enters it
as a callable on a float array (``Predictor``), and the attributions come from the pinned ``shap`` (TreeSHAP on the log-odds, the
LightGBM and XGBoost rungs) and reach the engine as arrays.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from ...model import gbm
from ..c01_ladder import Rung, fit_ladder
from .data import Frame

CHAMPION = "P4-lightgbm"
CHALLENGER = "P4-xgboost"


def rung_id(rung: str, frame: Frame) -> str:
    """The id of a rung fitted on a frame (a rung id is only unique within one dataset)."""
    return f"{rung}-{frame.name}"


def fit_rungs(frame: Frame, seed: int, *, with_xgboost: bool, log: Callable[[str], None] | None = None) -> dict[str, Rung]:
    """The ladder of ``cases/c01_ladder.py`` on the frame's training slice, calibrated on its calibration slice (TabPFN is not run)."""
    Xtr, ytr = frame.part("train")
    Xcal, ycal = frame.part("cal")
    return fit_ladder(Xtr, ytr, Xcal, ycal, frame.folds, features=frame.features, categorical=frame.categorical, monotone=frame.monotone,
                      seed=seed, with_xgboost=with_xgboost, with_tabpfn=False, log=log)


@dataclass
class Predictor:
    """A rung as a callable on a float array of the frame's feature columns: the PD of each row.

    A categorical feature stored as an integer code (Taiwan's EDUCATION) is read as the nearest integer code, so an input-noise array
    keeps a valid category rather than a fractional one."""

    rung: Rung
    features: tuple[str, ...]
    int_columns: tuple[str, ...] = ()
    calibrated: bool = True

    def frame(self, arr: np.ndarray) -> pd.DataFrame:
        df = pd.DataFrame(np.asarray(arr, dtype=float), columns=list(self.features))
        for c in self.int_columns:
            df[c] = np.rint(df[c]).astype(int)
        return df

    def __call__(self, arr: np.ndarray) -> np.ndarray:
        df = self.frame(arr)
        return self.rung.pd(df) if self.calibrated else self.rung.raw_pd(df)


def predictor(rung: Rung, frame: Frame) -> Predictor:
    ints = tuple(c for c in frame.categorical if np.issubdtype(frame.X[c].dtype, np.integer))
    return Predictor(rung, tuple(frame.features), ints)


def matrix(frame: Frame, ix: np.ndarray | None = None) -> np.ndarray:
    """The frame's feature columns as a float array (a categorical code stays its code)."""
    X = frame.X if ix is None else frame.X.iloc[ix]
    return X[list(frame.features)].to_numpy(dtype=float)


def shap_values(rung: Rung, X: pd.DataFrame) -> tuple[np.ndarray, float, np.ndarray]:
    """TreeSHAP on the log-odds of a boosted rung: the attributions (n, p), the base value and the model margin (n,)."""
    import shap

    model = rung.model
    if not isinstance(model, gbm.GBM):
        raise TypeError(f"{rung.id}: attributions come from TreeSHAP and this rung is not a boosted-tree rung")
    M = model.matrix(X)
    exp = shap.TreeExplainer(model.model)
    phi = np.asarray(exp.shap_values(M), dtype=float)
    if phi.ndim == 3:
        phi = phi[..., -1]
    base = np.asarray(exp.expected_value, dtype=float).reshape(-1)[-1]
    return phi, float(base), model.raw_logit(X)


def mean_abs(phi: np.ndarray) -> np.ndarray:
    return np.abs(phi).mean(axis=0)


def cutoff(pd_baseline: np.ndarray, reject_share: float) -> float:
    """The cut-off of the decision-flip Impact block (decision Q10): the PD above which the worst ``reject_share`` of the baseline
    decisions fall, held fixed under every shift. A PD at or above it is declined."""
    return float(np.quantile(np.asarray(pd_baseline, dtype=float), 1.0 - reject_share, method="inverted_cdf"))


def flip_share(pd_before: np.ndarray, pd_after: np.ndarray, cut: float) -> float:
    """The share of decisions that change between two PDs of the same records at a fixed cut-off."""
    return float(np.mean((np.asarray(pd_before) >= cut) != (np.asarray(pd_after) >= cut)))


def refit_lightgbm(frame: Frame, seed: int, rounds: int, ix: np.ndarray | None = None, codes: dict | None = None) -> gbm.GBM:
    """The P4 LightGBM rung refitted with a given seed on the training slice (or a resample ``ix`` of it), the number of rounds kept."""
    Xtr, ytr = frame.part("train")
    if ix is not None:
        Xtr, ytr = Xtr.iloc[ix], ytr[ix]
    return gbm.fit_lightgbm(Xtr, ytr, (), features=frame.features, categorical=frame.categorical, monotone=frame.monotone, seed=seed,
                            rounds=rounds, codes=codes)


def refit_xgboost(frame: Frame, seed: int, rounds: int, ix: np.ndarray | None = None, codes: dict | None = None) -> gbm.GBM:
    """The XGBoost rung refitted with a given seed and a fixed number of rounds (the rounds chosen on the first fit)."""
    import xgboost as xgb

    Xtr, ytr = frame.part("train")
    if ix is not None:
        Xtr, ytr = Xtr.iloc[ix], ytr[ix]
    cons = gbm._constraints(frame.features, frame.categorical, frame.monotone)
    params = {"objective": "binary:logistic", "eta": 0.05, "max_depth": 4, "min_child_weight": 20, "subsample": 0.9, "colsample_bytree": 0.9,
              "lambda": 1.0, "tree_method": "hist", "max_bin": 512, "monotone_constraints": "(" + ",".join(str(c) for c in cons) + ")",
              "seed": seed, "eval_metric": "logloss", "nthread": 1}
    codes = codes if codes is not None else gbm.learn_codes(Xtr, frame.categorical)
    M = gbm.encode(Xtr, list(frame.features), codes)
    booster = xgb.train(params, xgb.DMatrix(M, label=np.asarray(ytr, dtype=int)), num_boost_round=rounds)
    return gbm.GBM("xgboost", booster, list(frame.features), cons, rounds, params, codes)


def as_rung(model: gbm.GBM, template: Rung, calibration: Any) -> Rung:
    """A refitted boosted model in the shape of a rung (so it enters the same predictor); ``calibration`` is its isotonic map or None."""
    return Rung(template.id, template.rung, template.title, template.engine, template.engine_version, template.licence, model,
                calibration=calibration, parameters=template.parameters, details={})
