"""Calibration maps, the master scale and the reliability table (dossier 04 A.5 and C.1, dossier 06 C.3).

Every machine-learning rung gets an explicit calibration map fitted on the calibration slice, never on the
holdout; resampling is never used before calibration is measured (van den Goorbergh et al. 2022). The master scale
is geometric: grade upper bounds 1% x 1.5^k for k = 0..10, then 100%, so twelve grades from below 1% to above
57.7%. A grade's PD in the grade-level tests is the mean PD of the obligors the rung maps to it.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

PD_FLOOR = 1e-6  # PDs stay inside the open interval (0, 1) that contract 1 and the tests require
MASTER_SCALE_UPPER: tuple[float, ...] = tuple(round(0.01 * 1.5**k, 8) for k in range(11)) + (1.0,)
GRADES: tuple[str, ...] = tuple(f"G{k + 1:02d}" for k in range(len(MASTER_SCALE_UPPER)))


def clip_pd(p: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(p, dtype=float), PD_FLOOR, 1.0 - PD_FLOOR)


@dataclass
class Isotonic:
    """A monotone non-decreasing map from a rung's raw PD to a calibrated PD, fitted on the calibration slice."""

    x: np.ndarray  # thresholds (raw PD)
    y: np.ndarray  # calibrated PD at the thresholds

    def __call__(self, p: np.ndarray) -> np.ndarray:
        return clip_pd(np.interp(np.asarray(p, dtype=float), self.x, self.y))

    def record(self) -> dict:
        return {"kind": "isotonic", "fitted_on": "calibration slice", "x": self.x.tolist(), "y": self.y.tolist()}


def fit_isotonic(p_cal: np.ndarray, y_cal: np.ndarray) -> Isotonic:
    from sklearn.isotonic import IsotonicRegression

    iso = IsotonicRegression(y_min=PD_FLOOR, y_max=1.0 - PD_FLOOR, increasing=True, out_of_bounds="clip")
    iso.fit(np.asarray(p_cal, dtype=float), np.asarray(y_cal, dtype=float))
    return Isotonic(x=np.asarray(iso.X_thresholds_, dtype=float), y=np.asarray(iso.y_thresholds_, dtype=float))


def grade_of(p: np.ndarray) -> np.ndarray:
    """Index into GRADES of each PD (a PD equal to an upper bound belongs to that grade)."""
    return np.searchsorted(np.asarray(MASTER_SCALE_UPPER), np.asarray(p, dtype=float), side="left")


def grade_table(p: np.ndarray, y: np.ndarray) -> list[dict]:
    """Per grade: bounds, obligors, defaults, the mean PD and the observed default rate (empty grades included)."""
    g = grade_of(p)
    rows = []
    lo = 0.0
    for k, hi in enumerate(MASTER_SCALE_UPPER):
        m = g == k
        n = int(m.sum())
        rows.append({"grade": GRADES[k], "lo": lo, "hi": hi, "n": n, "d": int(y[m].sum()) if n else 0,
                     "pd": float(p[m].mean()) if n else None, "dr": float(y[m].mean()) if n else None})
        lo = hi
    return rows


def reliability(p: np.ndarray, y: np.ndarray, bins: int = 10) -> list[dict]:
    """Quantile bins of the predicted PD: mean predicted vs observed, with the count (the reliability diagram)."""
    p = np.asarray(p, dtype=float)
    y = np.asarray(y, dtype=int)
    order = np.argsort(p, kind="stable")
    out = []
    for chunk in np.array_split(order, bins):
        if len(chunk) == 0:
            continue
        out.append({"n": int(len(chunk)), "pd": float(p[chunk].mean()), "dr": float(y[chunk].mean()),
                    "lo": float(p[chunk].min()), "hi": float(p[chunk].max())})
    return out
