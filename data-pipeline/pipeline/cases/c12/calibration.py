"""The HW1F calibration at a date: ``a`` and ``sigma`` from the exact AR(1) regression on the 3 month zero rate (decision B6),
through ``riskvalidation.ccr.hw1f.calibrate_ar1``, on the observations strictly before the date.

The window starts at the first observation of the data (1 January 1990 files) and ends the day before the date: an expanding
window, at least three years (CRE53.51) for every backtest date. A rolling window of five or ten years was measured first and
refused: on those windows the regression is not mean-reverting (b >= 1) at a third of the dates, and the engine raises there.
The fit to the curve of the date is the engine's ``phi``; nothing here estimates.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.ccr.hw1f import Ar1Fit, calibrate_ar1

from . import data

ESTIMATOR = "exact AR(1) OLS on the shortest Treasury zero rate (Brigo et al., arXiv 0812.4210, equations 55 to 57)"
#: the estimator as the views print it, in both languages (R3 c13 BL4: the Spanish Context printed the English sentence); every
#: calibration record keeps the English ``ESTIMATOR`` as its schema constant
ESTIMATOR_TEXT = {"en": ESTIMATOR,
                  "es": "AR(1) exacto por MCO sobre la tasa cero más corta del Tesoro (Brigo et al., arXiv 0812.4210, ecuaciones 55 a 57)"}
FIT_TO_CURVE = "phi(t) = f(0,t) + sigma^2 (1 - exp(-a t))^2 / (2 a^2), the QuantLib 1.44 fitting parameter"
DAYS_PER_YEAR = 365.25


@dataclass(frozen=True)
class Series:
    """The short-rate proxy: dates (ISO) and the 3 month zero rates."""

    dates: list[str]
    values: np.ndarray

    def window(self, start: str | None, before: str) -> tuple[list[str], np.ndarray]:
        """The observations from ``start`` (inclusive; the first observation when None) to the day before ``before``."""
        lo = 0 if start is None else int(np.searchsorted(self.dates, start, side="left"))
        hi = int(np.searchsorted(self.dates, before, side="left"))
        return self.dates[lo:hi], self.values[lo:hi]


def series_of(curves: data.Curves) -> Series:
    dates, values, _ = curves.proxy_series()
    return Series(dates, values)


def fit_at(series: Series, date: str, start: str | None = None, min_years: float = 3.0) -> Ar1Fit:
    """The AR(1) fit on the observations from ``start`` (default: the first) up to the day before ``date``. ``min_years`` is
    the engine's floor on the span of the sample (CRE53.51: three years)."""
    d, v = series.window(start, date)
    return calibrate_ar1(d, v, before=date, min_years=min_years)


def record(fit: Ar1Fit, backtest_date: str) -> dict[str, Any]:
    """The calibration record of the c12 schemas (``c12Calibration``)."""
    span = (dt.date.fromisoformat(fit.sample_end) - dt.date.fromisoformat(fit.sample_start)).days / DAYS_PER_YEAR
    return {"backtest_date": backtest_date, "model": "hw1f", "estimator": ESTIMATOR, "proxy_tenor_years": data.PROXY_YEARS,
            "sample_start": fit.sample_start, "sample_end": fit.sample_end, "n_obs": fit.n_obs,
            "history_years": math.floor(span * 100) / 100, "a": fit.a, "sigma": fit.sigma, "a_se": fit.a_se,
            "sigma_se": fit.sigma_se, "fit_to_curve": FIT_TO_CURVE}
