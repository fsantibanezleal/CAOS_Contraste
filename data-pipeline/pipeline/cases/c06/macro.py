"""The macro side of C06 (CT-502, CT-504): the history as known at a reporting date, the scenario paths, and the
satellite that turns a macro path into the systematic factor Z of the one-factor model.

Scenarios. The Federal Reserve publishes its 2026 baseline and severely adverse paths for 13 quarters from a 2025 Q4
jump-off (dossier 08 D.1). A reporting date before 2026 cannot use a path published in 2026 as if it were known then, so
the product transposes the SHAPE of each Fed path: the change of each variable from the Fed's jump-off quarter is added
to the last value known at the reporting date. Past the 13 quarters a scenario reverts linearly to the baseline over
``REVERSION_QUARTERS``. The third scenario, ``adverse``, is the midpoint of the two Fed shapes and is Contraste's own,
labelled so. The weights are policy parameters, not the Fed's.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ...io.sba import FedTables

MACRO_VARS = ("unemployment_rate", "real_gdp_growth", "prime_rate")
MACRO_UNITS = {"unemployment_rate": "percent", "real_gdp_growth": "percent, annualised", "prime_rate": "percent"}
#: scenario ids in the order the documents list them, with their policy weights (sum 1) and labels
SCENARIOS = ("baseline", "adverse", "severely-adverse")
SCENARIO_WEIGHTS = {"baseline": 0.60, "adverse": 0.30, "severely-adverse": 0.10}
SCENARIO_LABELS = {
    "baseline": {"en": "Baseline (Fed 2026 shape)", "es": "Base (forma Fed 2026)"},
    "adverse": {"en": "Adverse (midpoint of the Fed shapes, Contraste's own)", "es": "Adverso (punto medio de las formas Fed, propio de Contraste)"},
    "severely-adverse": {"en": "Severely adverse (Fed 2026 shape)", "es": "Severamente adverso (forma Fed 2026)"},
}
SCENARIO_SOURCES = {
    "baseline": "Federal Reserve 2026_Final_Supervisory_Baseline_Domestic.csv, shape transposed to the reporting date",
    "adverse": "midpoint of the Federal Reserve 2026 baseline and severely adverse shapes (Contraste's own scenario)",
    "severely-adverse": "Federal Reserve 2026_Final_Supervisory_Severely_Adverse_Domestic.csv, shape transposed to the reporting date",
}
REVERSION_QUARTERS = 12
UNEMPLOYMENT_FLOOR, PRIME_FLOOR = 1.0, 0.0
FED_JUMPOFF = "2025-12-31"


def quarter_number(ts: pd.Timestamp | np.datetime64) -> int:
    """The calendar quarter number (month number since 1970-01, divided by 3) of a date; the panel's time index."""
    t = pd.Timestamp(ts)
    return ((t.year - 1970) * 12 + t.month - 1) // 3


def quarter_end(q: int) -> pd.Timestamp:
    return pd.Timestamp(year=1970 + (q * 3) // 12, month=(q * 3) % 12 + 3, day=1) + pd.offsets.MonthEnd(0)


@dataclass(frozen=True)
class History:
    """The quarterly macro history up to the quarter containing the reporting date: ``values[k]`` is the quarter
    ``first + k``."""

    first: int
    values: np.ndarray  # (n, 3) in MACRO_VARS order

    @property
    def last(self) -> int:
        return self.first + self.values.shape[0] - 1

    def at(self, q: int) -> np.ndarray:
        return self.values[q - self.first]

    def window(self, q_from: int, q_to: int) -> np.ndarray:
        return self.values[q_from - self.first: q_to - self.first + 1]


def history_known(fed: FedTables, reporting_date: np.datetime64) -> History:
    """The Fed history rows whose quarter ended on or before the reporting date (CT-504). The values are the 2026
    release, revised: real-time vintages are not published in these files (a stated limit)."""
    r = pd.Timestamp(np.datetime64(reporting_date, "D"))
    h = fed.history[fed.history["date"] <= r].sort_values("date")
    if h.empty:
        raise ValueError(f"no macro history on or before {r.date()}")
    q = np.array([quarter_number(d) for d in h["date"]])
    if np.any(np.diff(q) != 1):
        raise ValueError("the Federal Reserve history has a gap in its quarters")
    vals = h[list(MACRO_VARS)].to_numpy(dtype=float)
    if not np.all(np.isfinite(vals)):
        raise ValueError("the Federal Reserve history has a missing value in a variable the case reads")
    return History(first=int(q[0]), values=vals)


def _fed_shape(fed: FedTables, name: str) -> np.ndarray:
    jump = fed.history[fed.history["date"] == pd.Timestamp(FED_JUMPOFF)]
    if len(jump) != 1:
        raise ValueError(f"the Federal Reserve history has no {FED_JUMPOFF} jump-off row")
    j = jump[list(MACRO_VARS)].to_numpy(dtype=float)[0]
    return fed.scenarios[name][list(MACRO_VARS)].to_numpy(dtype=float) - j


def scenario_paths(fed: FedTables, history: History, n_quarters: int) -> dict[str, np.ndarray]:
    """The three scenario macro paths for quarters 1 to ``n_quarters`` after the reporting date: ``(n_quarters, 3)``."""
    base_shape, sev_shape = _fed_shape(fed, "baseline"), _fed_shape(fed, "severely-adverse")
    shapes = {"baseline": base_shape, "adverse": 0.5 * (base_shape + sev_shape), "severely-adverse": sev_shape}
    last = history.at(history.last)
    out: dict[str, np.ndarray] = {}
    base_tail = last + shapes["baseline"][-1]
    for name in SCENARIOS:
        shape = shapes[name]
        path = np.empty((n_quarters, len(MACRO_VARS)))
        k13 = last + shape[-1]
        for k in range(1, n_quarters + 1):
            if k <= shape.shape[0]:
                path[k - 1] = last + shape[k - 1]
            else:
                w = min(1.0, (k - shape.shape[0]) / REVERSION_QUARTERS)
                path[k - 1] = k13 + w * (base_tail - k13)
        path[:, 0] = np.maximum(path[:, 0], UNEMPLOYMENT_FLOOR)
        path[:, 2] = np.maximum(path[:, 2], PRIME_FLOOR)
        out[name] = path
    return out


def weighted_mean_path(paths: dict[str, np.ndarray], weights: dict[str, float] | None = None) -> np.ndarray:
    w = weights or SCENARIO_WEIGHTS
    return sum(w[n] * paths[n] for n in SCENARIOS)


def lagged_for_hazard(history: History, path: np.ndarray) -> np.ndarray:
    """The macro values the hazard of quarters 1..T reads: one quarter of lag, so quarter t reads the value of t-1 (the
    last known value for t = 1): ``[m_R, path_1, ..., path_{T-1}]``."""
    return np.vstack([history.at(history.last)[None, :], path[:-1]])


@dataclass(frozen=True)
class Scaler:
    mean: np.ndarray
    std: np.ndarray

    def apply(self, values: np.ndarray) -> np.ndarray:
        return (values - self.mean) / self.std


def fit_scaler(values: np.ndarray) -> Scaler:
    std = values.std(axis=0)
    return Scaler(mean=values.mean(axis=0), std=np.where(std > 1e-9, std, 1.0))


@dataclass(frozen=True)
class Satellite:
    """The reduced form of the hazard rung in factor space: z = intercept + sum_k beta_k m_k over the macro values the
    hazard reads, fitted by ordinary least squares on the scenario factor paths. ``ar1`` is 0: the rung has no lag of its
    own factor."""

    intercept: float
    ar1: float
    coefficients: dict[str, float]
    n_obs: int
    r_squared: float


def fit_reduced_form(z: np.ndarray, macro: np.ndarray) -> Satellite:
    """``z`` (n,) the systematic factor the scenario default rates imply and ``macro`` (n, 3) the macro values the
    hazard read for the same quarters."""
    import statsmodels.api as sm

    vary = [j for j in range(macro.shape[1]) if np.ptp(macro[:, j]) > 1e-9]  # a column the scenarios never move carries no effect
    res = sm.OLS(z, np.column_stack([np.ones(len(z)), macro[:, vary]])).fit()
    b = np.asarray(res.params, dtype=float)
    coef = {v: 0.0 for v in MACRO_VARS}
    for k, j in enumerate(vary):
        coef[MACRO_VARS[j]] = float(b[1 + k])
    return Satellite(intercept=float(b[0]), ar1=0.0, coefficients=coef, n_obs=int(len(z)), r_squared=float(res.rsquared))


def macro_path_records(history: History, paths: dict[str, np.ndarray], reporting_date: np.datetime64) -> list[dict]:
    """The macro path contract rows (family ``macro_path``: scenario, date, variable, value, unit, vintage_date) the
    model of ``reporting_date`` stands on: the history as known and the transposed scenario paths. ``vintage_date`` is
    the reporting date, the date at which the model has these values; the history values themselves are the 2026
    release."""
    r = str(np.datetime64(reporting_date, "D"))
    rows: list[dict] = []
    for k in range(history.values.shape[0]):
        d = quarter_end(history.first + k).date().isoformat()
        for j, v in enumerate(MACRO_VARS):
            rows.append({"scenario": "history", "date": d, "variable": v, "value": float(history.values[k, j]),
                         "unit": MACRO_UNITS[v], "vintage_date": r})
    for name, path in paths.items():
        for k in range(path.shape[0]):
            d = quarter_end(history.last + 1 + k).date().isoformat()
            for j, v in enumerate(MACRO_VARS):
                rows.append({"scenario": name, "date": d, "variable": v, "value": float(path[k, j]),
                             "unit": MACRO_UNITS[v], "vintage_date": r})
    return rows
