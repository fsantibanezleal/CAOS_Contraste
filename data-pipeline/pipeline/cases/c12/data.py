"""The readers of C12: the Treasury par curves through the shared reader, the zero curves and the short-rate proxy through the
engine's bootstrap, the backtest dates, and the HQM corporate spot curves (xlrd).

Nothing here estimates or prices: the bootstrap is ``riskvalidation.irrbb.curves.bootstrap_zero_curve`` and the curves are read
by ``pipeline.io.treasury``. A tenor the day does not quote is absent from its curve and listed, never filled (sizing R2).

Dates are ISO strings. A backtest date is the last par curve published on or before a month end (a weekend month end carries the
Friday), so the date a document names is a day a curve exists.
"""
from __future__ import annotations

import calendar
import datetime as dt
from pathlib import Path

import numpy as np
from riskvalidation.irrbb.curves import bootstrap_zero_curve

from ...io import treasury

#: the proxy of the short rate: the 3 month par yield (the shortest tenor the files quote from 1990 to today)
PROXY_LABEL = "3 Mo"
PROXY_YEARS = 0.25
#: the HQM maturity (years) of the scalar spread the stressed row reports: the middle of the book's tenors
SPREAD_YEARS = 5.0


def month_end(year: int, month: int) -> str:
    return dt.date(year, month, calendar.monthrange(year, month)[1]).isoformat()


def add_months(date: str, k: int) -> str:
    """The month end ``k`` months after the month of ``date`` (backtest dates sit on month ends)."""
    d = dt.date.fromisoformat(date)
    idx = d.year * 12 + (d.month - 1) + k
    return month_end(idx // 12, idx % 12 + 1)


def months_between(first: str, last: str) -> list[str]:
    """The month ends from the month of ``first`` to the month of ``last`` (``YYYY-MM`` or ISO dates), inclusive."""
    y0, m0 = int(first[:4]), int(first[5:7])
    y1, m1 = int(last[:4]), int(last[5:7])
    out = []
    while (y0, m0) <= (y1, m1):
        out.append(month_end(y0, m0))
        y0, m0 = (y0 + 1, 1) if m0 == 12 else (y0, m0 + 1)
    return out


class Curves:
    """The Treasury par curves of the data root, with the lookups the bake needs."""

    def __init__(self, curves: dict[str, treasury.ParCurve]) -> None:
        self.by_date = curves
        self.dates = sorted(curves)
        self.last = self.dates[-1]

    def as_of(self, date: str) -> treasury.ParCurve:
        """The last curve published on or before ``date`` (never a later one)."""
        return treasury.curve_as_of(self.by_date, date)

    def zero(self, date: str) -> tuple[np.ndarray, np.ndarray, treasury.ParCurve]:
        """``(tenors, continuously compounded zero rates, the par curve)`` of the curve published on or before ``date``."""
        par = self.as_of(date)
        tenors = par.tenors()
        return tenors, bootstrap_zero_curve(tenors, par.yields()), par

    def proxy_series(self) -> tuple[list[str], np.ndarray, list[str]]:
        """``(dates, proxy zero rates, missing dates)``: the zero rate of the 3 month tenor on every day it is quoted, from the
        engine's bootstrap (a single money-market tenor reads as simple interest); a day without the tenor is listed."""
        dates, values, missing = [], [], []
        for d in self.dates:
            y = self.by_date[d].par.get(PROXY_LABEL)
            if y is None:
                missing.append(d)
                continue
            dates.append(d)
            values.append(float(bootstrap_zero_curve(np.array([PROXY_YEARS]), np.array([y]))[0]))
        return dates, np.array(values), missing

    def backtest_dates(self, first_month: str, last_realised: str) -> list[str]:
        """The published curve date of every month end from ``first_month`` to the last month whose 12 month horizon is observed
        (its realised curve is published on or before ``last_realised``)."""
        out = []
        for me in months_between(first_month, last_realised):
            if horizon_date(me, "12m") > self.last:
                break
            d = self.as_of(me)
            out.append(d.observation_date)
        return out


def read_curves(data_root: str | Path) -> Curves:
    return Curves(treasury.read_par(Path(data_root) / "raw" / treasury.TREASURY_DIR))


#: the six horizons of decision S1: business days as calendar days (10 business days are 14 calendar days, 20 are 28), then months
HORIZONS = ("10bd", "20bd", "1m", "3m", "6m", "12m")
#: the model time of each horizon in years on the 30/360 axis the case uses (months over 12, calendar days over 360)
HORIZON_YEARS = {"10bd": 14 / 360, "20bd": 28 / 360, "1m": 1 / 12, "3m": 0.25, "6m": 0.5, "12m": 1.0}
HORIZON_DAYS = {"10bd": 14, "20bd": 28}
HORIZON_MONTHS = {"1m": 1, "3m": 3, "6m": 6, "12m": 12}


def horizon_date(date: str, horizon: str) -> str:
    """The calendar date a horizon from a backtest date ends on: 14 or 28 days, or the month end 1, 3, 6 or 12 months later."""
    if horizon in HORIZON_DAYS:
        return (dt.date.fromisoformat(date) + dt.timedelta(days=HORIZON_DAYS[horizon])).isoformat()
    return add_months(date, HORIZON_MONTHS[horizon])


# ------------------------------------------------------------------------------------------------------------------- HQM

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def read_hqm(paths: list[Path]) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """The HQM end-of-month spot curves: ``{"YYYY-MM": (maturities in years, spot rates in decimals)}`` from the xls blocks.

    Each sheet has the year in the header row above the month names, the maturities (0.5 to 100 years) in the first column, and
    one column per month; a month without values (a block that runs past today) is skipped. The spot rate is the Treasury's
    discount spot rate, semiannually compounded (Girola, The XRM Yield Curve Methodology, 2024, equation 5.7a); the caller
    converts it."""
    import xlrd

    out: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for path in paths:
        sh = xlrd.open_workbook(str(path)).sheet_by_index(0)
        head = next(r for r in range(sh.nrows) if sh.cell_value(r, 0) == "Maturity")
        first = head + 2
        year = ""
        cols: dict[int, str] = {}
        for c in range(2, sh.ncols):
            y = sh.cell_value(head - 1, c)
            year = str(int(float(y))) if y not in ("", None) else year
            m = sh.cell_value(head, c)
            if m in _MONTHS:
                cols[c] = f"{year}-{_MONTHS.index(m) + 1:02d}"
        rows = [r for r in range(first, sh.nrows) if isinstance(sh.cell_value(r, 0), float)]
        mats = np.array([sh.cell_value(r, 0) for r in rows])
        for c, key in cols.items():
            vals = [sh.cell_value(r, c) for r in rows]
            if all(isinstance(v, float) for v in vals):
                out[key] = (mats, np.array(vals) / 100.0)
    return out


def semiannual_to_continuous(rate: np.ndarray) -> np.ndarray:
    """A semiannually compounded rate as the continuously compounded one: ``2 ln(1 + r / 2)``."""
    return 2.0 * np.log1p(np.asarray(rate, dtype=float) / 2.0)


def hqm_spread(hqm: tuple[np.ndarray, np.ndarray], tenors: np.ndarray, zero: np.ndarray, at: np.ndarray) -> np.ndarray:
    """The HQM spot rate minus the Treasury zero rate, both continuously compounded, at the maturities ``at``: the HQM curve
    is read on its half-year grid, the Treasury zero curve is interpolated linearly in tenor with flat extrapolation (the
    engine's curve rule), and the spread below the first HQM maturity (0.5 years) is that of 0.5 years (flat). A negative
    spread is returned as it is: the caller floors it at zero and counts it (decision B10)."""
    mats, spot = hqm
    hqm_c = semiannual_to_continuous(spot)
    z_at_mats = np.interp(mats, tenors, zero)
    spread_on_grid = hqm_c - z_at_mats
    return np.interp(np.asarray(at, dtype=float), mats, spread_on_grid)
