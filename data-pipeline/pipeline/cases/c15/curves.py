"""The C15 curves: the choice of the BCCh series, the valuation date, and the zero curves fitted by ``riskvalidation.irrbb.curves``.

The F022 table of the BDE publishes the secondary-market yields of Central Bank and Treasury bonds: pesos (BCLP: 1, 2, 5 and 10 years)
and UF (BUF: 1, 2, 5, 10, 20 and 30 years). A series with no value in the stated month is left out with its reason. The **valuation date**
is the last business day of the month on which every chosen series has a value; the whole month stays in the raw files, and nothing dated
after the valuation date enters a fit (``Series.values(up_to=...)``, tested).

Each curve is fitted in two engine calls, never by the product: ``bootstrap_zero_curve`` turns the observed yields into continuously
compounded zero rates at the pillars (the yields are read as semiannual bond-equivalent par yields, which UNVERIFIED against the BCCh
methodology note), then ``fit_nelson_siegel`` fits one Nelson-Siegel curve to those zero rates, and ``nelson_siegel_yield`` evaluates it at the 19
bucket midpoints. The engine's fit needs four points. The UF curve has four (2, 5, 10 and 30 years); the pesos curve has three (2, 5 and
10 years), so the monetary policy rate (F022.TPM.TIN.D001.NO.Z.D), the Central Bank's overnight rate, is added as a fourth point at one day.
That point is not a secondary-market yield and is stated as such in the document (an open question of the unit report); a pesos curve with
four published tenors would not use it. A currency with fewer than three published tenors is refused, never filled.
"""
from __future__ import annotations

import calendar
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from riskvalidation.irrbb import curves as rv_curves
from riskvalidation.irrbb import slotting as rv_slotting

from ...io import bcch

ANCHOR_CODE = "F022.TPM.TIN.D001.NO.Z.D"
ANCHOR_TENOR = 1.0 / 360.0
UF_CODE = "F073.UFF.PRE.Z.D"
#: the anchor each curve may use (only the pesos curve: the policy rate is in pesos)
ANCHORS = {"CLP": ANCHOR_CODE}
MIN_TENORS = 3
ENGINE_MIN_POINTS = 4
COUPON_FREQUENCY = 2
MID = rv_slotting.bucket_grid().midpoints
CURVE_KEY = {"CLP": "clp", "UR": "ur"}
LABEL = {"CLP": "pesos (CLP)", "UR": "UF-indexed (UR)"}


class BlockedCurve(ValueError):
    """The month's BCCh data cannot give a curve: a currency has too few tenors, there is no common day, or the fit has no fourth point."""


@dataclass(frozen=True)
class Chosen:
    code: str
    curve: str                   # CLP or UR
    tenor_years: float
    kind: str                    # yield (secondary-market) or anchor (policy rate)
    title_es: str
    title_en: str
    note: str = ""


@dataclass(frozen=True)
class Excluded:
    code: str
    curve: str
    tenor_years: float
    reason: str


@dataclass(frozen=True)
class Selection:
    month: str
    first: str
    last: str
    valuation_date: str
    chosen: tuple[Chosen, ...]
    excluded: tuple[Excluded, ...]


@dataclass(frozen=True)
class RawSet:
    series: dict[str, bcch.Series]
    infos: list[bcch.SeriesInfo]
    files: list[dict[str, Any]]


@dataclass(frozen=True)
class CurveFit:
    block: dict[str, Any]
    rates: np.ndarray            # (19,) zero rates at the bucket midpoints
    fit: rv_curves.NelsonSiegelFit


def month_bounds(month: str) -> tuple[str, str]:
    y, m = int(month[:4]), int(month[5:7])
    return f"{month}-01", f"{month}-{calendar.monthrange(y, m)[1]:02d}"


def load_raw(data_root: str | Path) -> RawSet:
    """The raw BCCh files of the device data root, each verified against its provenance record."""
    series, infos, files = bcch.read_raw(data_root)
    return RawSet(series, infos, files)


def select(series: Mapping[str, bcch.Series], infos: Sequence[bcch.SeriesInfo], month: str) -> Selection:
    """The chosen series and the valuation date of ``month`` (``YYYY-MM``); refuses what cannot make a curve."""
    first, last = month_bounds(month)
    by_info = {i.series_id: i for i in infos}
    chosen: list[Chosen] = []
    excluded: list[Excluded] = []
    for y in bcch.yield_series(infos):
        s = series.get(y.series_id)
        has = [d for d in (s.values() if s else {}) if first <= d <= last]
        if not has:
            seen = by_info[y.series_id].last_observation
            excluded.append(Excluded(y.series_id, y.curve, y.tenor_years,
                                     f"no observation in {month}: the BCCh lists its last observation on {seen}"))
            continue
        chosen.append(Chosen(y.series_id, y.curve, y.tenor_years, "yield", s.title_es, s.title_en))
    for curve in ("CLP", "UR"):
        n = sum(1 for c in chosen if c.curve == curve)
        if n < MIN_TENORS:
            raise BlockedCurve(f"{curve}: {n} tenors with a value in {month}, fewer than {MIN_TENORS}; the curve is not made up")
        if n < ENGINE_MIN_POINTS:
            code = ANCHORS.get(curve)
            s = series.get(code) if code else None
            if s is None or not any(first <= d <= last for d in s.values()):
                raise BlockedCurve(f"{curve}: {n} tenors and no anchor with a value in {month}; the engine's Nelson-Siegel fit needs "
                                   f"{ENGINE_MIN_POINTS} points")
            chosen.append(Chosen(code, curve, ANCHOR_TENOR, "anchor", s.title_es, s.title_en,
                                 "Monetary policy rate of the Banco Central, its overnight rate: a policy rate, not a secondary-market yield; "
                                 "the short anchor that gives the engine's Nelson-Siegel fit its fourth point (a Contraste choice)."))
    uf = series.get(UF_CODE)
    needed = [series[c.code] for c in chosen] + ([uf] if uf is not None else [])
    if uf is None:
        raise BlockedCurve(f"{UF_CODE}: the UF value is not in the raw files")
    vd = bcch.last_common_date(needed, first, last)
    if vd is None:
        raise BlockedCurve(f"no business day of {month} on which every chosen series has a value")
    order = {"CLP": 0, "UR": 1}
    chosen.sort(key=lambda c: (order[c.curve], c.tenor_years))
    excluded.sort(key=lambda e: (order[e.curve], e.tenor_years))
    return Selection(month, first, last, vd, tuple(chosen), tuple(excluded))


def _value_on(series: Mapping[str, bcch.Series], code: str, day: str) -> float:
    """The value of a series on ``day`` read with nothing dated after it; a missing value is refused, never filled."""
    got = series[code].values(up_to=day) if code in series else {}
    if day not in got:
        raise BlockedCurve(f"{code}: no value on {day}")
    return got[day]


def fit_curve(sel: Selection, series: Mapping[str, bcch.Series], curve: str) -> CurveFit:
    """The zero curve of one currency on the valuation date, from the engine's bootstrap and Nelson-Siegel fit."""
    pillars = [c for c in sel.chosen if c.curve == curve]
    ten = np.array([c.tenor_years for c in pillars])
    par = np.array([_value_on(series, c.code, sel.valuation_date) / 100.0 for c in pillars])
    zero = rv_curves.bootstrap_zero_curve(ten, par, COUPON_FREQUENCY)
    fit = rv_curves.fit_nelson_siegel(ten, zero)
    rates = rv_curves.nelson_siegel_yield(MID, fit.beta0, fit.beta1, fit.beta2, fit.tau)
    codes = sorted(c.code for c in pillars)
    yields = [c for c in pillars if c.kind == "yield"]
    anchored = len(yields) != len(pillars)
    tenors = ", ".join(f"{c.tenor_years:g}" for c in yields)
    source = (f"Banco Central de Chile, BDE table F022, secondary-market yields of Central Bank and Treasury bonds, {LABEL[curve]}, tenors "
              f"{tenors} years, observation date {sel.valuation_date}. The yields are read as semiannual bond-equivalent par yields and "
              "bootstrapped to continuously compounded zero rates with riskvalidation.irrbb.curves.bootstrap_zero_curve (frequency 2, simple "
              "interest up to six months, par yields interpolated linearly between pillars); one Nelson-Siegel curve is then fitted to the zero "
              "rates with fit_nelson_siegel (least squares for beta0, beta1 and beta2 on a tau grid of 0.25 to 10 years in steps of 0.25) and "
              "evaluated at the 19 bucket midpoints with nelson_siegel_yield.")
    if anchored:
        source += (f" The BCCh publishes {len(yields)} pesos tenors and the engine's fit needs four points, so the monetary policy rate "
                   f"({ANCHOR_CODE}), the Central Bank's overnight rate, is the fourth point at 1/360 year: a policy rate, not a "
                   "secondary-market yield (a Contraste choice, stated as an open question).")
    attribution = (f"Source: Banco Central de Chile (BDE), series {', '.join(codes)}. The fitted zero curve is an adaptation by Contraste of "
                   "the Banco Central de Chile's data and is its sole responsibility (BCCh terms).")
    block = {
        "curve": curve, "month": sel.month, "date": sel.valuation_date, "source": source, "series_codes": codes, "attribution": attribution,
        "observed_kind": "secondary-market-yield", "compounding": "continuous",
        "fit": {"model": "nelson-siegel",
                "parameters": [{"name": "beta0", "value": float(fit.beta0), "unit": "decimal"}, {"name": "beta1", "value": float(fit.beta1), "unit": "decimal"},
                               {"name": "beta2", "value": float(fit.beta2), "unit": "decimal"}, {"name": "tau", "value": float(fit.tau), "unit": "years"}],
                "rmse_bp": float(fit.rmse * 1e4)},
        "points": [{"tenor_years": float(t), "observed_yield": float(p), "zero_rate": float(z)} for t, p, z in zip(ten, par, zero)],
        "zero_rates_at_midpoints": [float(x) for x in rates],
    }
    return CurveFit(block, rates, fit)


def uf_value(sel: Selection, series: Mapping[str, bcch.Series]) -> tuple[float, str]:
    """The UF value (CLP per UF) of the valuation date and its source line."""
    v = _value_on(series, UF_CODE, sel.valuation_date)
    return v, f"Banco Central de Chile, BDE series {UF_CODE} (Unidad de fomento), value of {sel.valuation_date}"
