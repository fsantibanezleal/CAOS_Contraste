"""P0, the anchors of every comparison (dossier 04, PD ladder): the constant PD (the training default rate) and the
single-variable benchmark (the default rate of each bin of the strongest variable, read from the scorecard's own
binning of it, fitted on the training slice)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..core.calibration import clip_pd


@dataclass
class Constant:
    pd_value: float

    def predict_pd(self, X: pd.DataFrame) -> np.ndarray:
        return np.full(len(X), self.pd_value)

    def record(self) -> dict:
        return {"pd": self.pd_value}


@dataclass
class SingleVariable:
    feature: str
    binning: object
    event_rates: np.ndarray  # per binning-table row, from the training slice

    def predict_pd(self, X: pd.DataFrame) -> np.ndarray:
        idx = np.asarray(self.binning.transform(X[self.feature].to_numpy(), metric="indices"), dtype=int)
        return clip_pd(self.event_rates[idx])

    def record(self) -> dict:
        table = self.binning.binning_table.build().drop(index="Totals")
        return {"feature": self.feature, "bins": [str(b) for b in table["Bin"]],
                "event_rates": [float(r) for r in self.event_rates]}


def fit_constant(y: np.ndarray) -> Constant:
    return Constant(float(np.mean(y)))


def fit_single_variable(scorecard, y_train: np.ndarray) -> SingleVariable:
    """The variable with the largest information value, with its bins' training default rates."""
    feature = max(scorecard.features, key=lambda f: scorecard.iv[f])
    ob = scorecard.binnings[feature]
    table = ob.binning_table.build().drop(index="Totals")
    rates = np.array([float(r) if c else float(np.mean(y_train)) for r, c in zip(table["Event rate"], table["Count"])])
    return SingleVariable(feature, ob, rates)
