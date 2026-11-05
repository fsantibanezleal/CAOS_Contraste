"""The stated portfolio of each window and its daily returns on a common calendar (SDD C11, decisions D2 and D4).

A portfolio is a set of constant weights, rebalanced daily, over up to three public series:

- ``french-daily``: the US equity market, the simple daily return of the French file (derived-only);
- ``treasury-par``: a long position in the 10-year US Treasury par bond, whose daily return is minus its modified duration
  (at the previous day's yield) times the yield change, in decimals (carry and convexity are left out and said so);
- ``h10-fx``: a long position in the euro against the dollar, the simple return of US dollars per euro.

The calendar of a window is the set of days on which **every** component is observed. A day on which one component is missing
and another is observed is skipped and counted, never filled (contract ``contract-family-market_series``); the return of the
day after a skipped day is the return between the two observed days, taken from the levels of each component (the French
returns are accumulated into an index to make that possible).

No function of this module looks at a forecast day: it builds returns from the levels it is given, and the rolling scheme
(``forecast``) decides what each forecast may see.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .constants import PORTFOLIO_OF, WINDOW_BY_ID, Window
from .readers import Series

COMPONENT_META = {
    "french-daily": ("derived-only", "simple-daily-return-of-the-us-equity-market (Mkt-RF plus RF)",
                     ("US equity market (Kenneth French)", "Mercado accionario de EE. UU. (Kenneth French)")),
    "treasury-par": ("mirror-allowed", "negative-modified-duration-times-yield-change",
                     ("10-year US Treasury par bond", "Bono par del Tesoro de EE. UU. a 10 años")),
    "h10-fx": ("mirror-allowed", "simple-return-of-us-dollars-per-euro",
               ("Euro against the US dollar (Federal Reserve H.10)", "Euro frente al dólar de EE. UU. (H.10 de la Reserva Federal)")),
}


def modified_duration_par(y: np.ndarray, years: float = 10.0) -> np.ndarray:
    """Modified duration of a par bond of ``years`` years with semiannual coupons at yield ``y`` (decimal):
    ``(1 - (1 + y/2)^(-2 years)) / y``; the limit ``years`` as ``y`` goes to 0 is used below 1e-6."""
    y = np.asarray(y, dtype=float)
    small = np.abs(y) < 1e-6
    safe = np.where(small, 1.0, y)
    return np.where(small, years, (1.0 - (1.0 + safe / 2.0) ** (-2.0 * years)) / safe)


@dataclass(frozen=True)
class Portfolio:
    window: Window
    dates: np.ndarray            # datetime64[D], the calendar of the returns (every component observed)
    returns: np.ndarray          # simple daily portfolio returns aligned with ``dates``
    weights: dict[str, float]
    components: tuple[Series, ...]
    missing: tuple[str, ...]     # skipped days in the observed range, counted
    first_observation: np.datetime64

    @property
    def derived_only(self) -> bool:
        return any(COMPONENT_META[s.series_id][0] == "derived-only" for s in self.components)


def _levels(s: Series) -> np.ndarray:
    """The level used to difference over a skipped day: an index for the French returns, the rate or the price otherwise."""
    if s.series_id == "french-daily":
        return np.cumprod(1.0 + s.values)
    return s.values


def _interval_return(s: Series, lev: np.ndarray, pos_prev: np.ndarray, pos: np.ndarray) -> np.ndarray:
    if s.series_id == "french-daily":
        return lev[pos] / lev[pos_prev] - 1.0
    if s.series_id == "treasury-par":
        return -modified_duration_par(lev[pos_prev]) * (lev[pos] - lev[pos_prev])
    return lev[pos] / lev[pos_prev] - 1.0


def build(window_id: str, series: dict[str, Series]) -> Portfolio:
    """The portfolio of a window over the series it needs, on the common calendar of those series."""
    return build_for(WINDOW_BY_ID[window_id], series)


def build_for(w: Window, series: dict[str, Series]) -> Portfolio:
    window_id = w.window_id
    weights = PORTFOLIO_OF[w.asset_class]
    comps = tuple(series[k] for k in weights)
    common = comps[0].dates
    for s in comps[1:]:
        common = np.intersect1d(common, s.dates)
    if common.size < 2:
        raise ValueError(f"{window_id}: the components share fewer than two observed days")
    cal = common[1:]
    total = np.zeros(cal.size)
    for s in comps:
        lev = _levels(s)
        pos = np.searchsorted(s.dates, common)
        total += weights[s.series_id] * _interval_return(s, lev, pos[:-1], pos[1:])
    union = comps[0].dates
    for s in comps[1:]:
        union = np.union1d(union, s.dates)
    skipped = {str(d) for d in np.setdiff1d(union, common)}
    gaps = {m for s in comps for m in s.missing}
    return Portfolio(w, cal, total, dict(weights), comps, tuple(sorted(skipped | gaps)), common[0])


def forecast_positions(p: Portfolio, limit: int | None = None) -> np.ndarray:
    """Positions in ``p.dates`` of the forecast days: the observed days from the window start to its end, inclusive.
    ``limit`` keeps the first days only (tests of a small size; the bake never passes it)."""
    start, end = np.datetime64(p.window.start, "D"), np.datetime64(p.window.end, "D")
    idx = np.flatnonzero((p.dates >= start) & (p.dates <= end))
    if idx.size == 0:
        raise ValueError(f"{p.window.window_id}: no observed day between {p.window.start} and {p.window.end}")
    return idx if limit is None else idx[:limit]
