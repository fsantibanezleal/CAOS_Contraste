"""The leakage-safe preprocessing of C02 (dossier 04 l.1054-1059, rule 2): imputation and the missing indicators are fitted on the
training slice only and applied unchanged to the calibration slice, the holdout and every other file.

A ratio missing in the file is filled with the median of the training slice; a ratio with at least ``MISSING_INDICATOR_SHARE`` of
missing values in the training slice also gets a 0/1 indicator column (``<Attr>_missing``), because a statement that lacks a ratio is
information available at the observation date. The medians and the indicator list are the fitted state and are recorded.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import conventions as cv


@dataclass(frozen=True)
class Preprocessor:
    features: tuple[str, ...]
    medians: dict[str, float]
    indicators: tuple[str, ...]
    extra: tuple[str, ...] = ()

    @property
    def columns(self) -> tuple[str, ...]:
        return (*self.features, *(f"{a}_missing" for a in self.indicators), *self.extra)

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=X.index)
        for f in self.features:
            out[f] = X[f].astype(float).fillna(self.medians[f]).to_numpy()
        for a in self.indicators:
            out[f"{a}_missing"] = X[a].isna().astype(float).to_numpy()
        for e in self.extra:
            out[e] = X[e].astype(float).to_numpy()
        return out

    def record(self) -> dict:
        return {"features": list(self.features), "medians": self.medians, "indicators": list(self.indicators), "extra": list(self.extra),
                "share": cv.MISSING_INDICATOR_SHARE}


def fit_preprocessor(X_train: pd.DataFrame, extra: tuple[str, ...] = ()) -> Preprocessor:
    """Fitted on ``X_train`` only. ``extra`` are columns passed through (the horizon indicator of the pooled variant)."""
    feats = tuple(a for a in cv.ATTRIBUTES)
    med = {f: float(np.nanmedian(X_train[f].to_numpy(dtype=float))) if X_train[f].notna().any() else 0.0 for f in feats}
    share = X_train[list(feats)].isna().mean()
    ind = tuple(f for f in feats if share[f] >= cv.MISSING_INDICATOR_SHARE)
    return Preprocessor(feats, med, ind, extra)
