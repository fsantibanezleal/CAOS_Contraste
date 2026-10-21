"""The fits of one valuation date, on the call-report history and the Treasury curves up to it (never later).

The client rate of the non-maturity deposits is the quarterly cost of the bank's deposits (deposit interest expense over the
average deposits, annualised): the call report carries no cost by customer type, so one series stands for all the non-maturity
deposits and the fit is filed under the dominant category. The tranche yields are the quarter-end Treasury par yields at the
tranche maturities (a simplification of the rolling tranche's yield). The replicating portfolio, its weighted average maturity and
its margin volatility are the engine's; the pass-through slopes are least squares through the origin on the quarters in which the
market rate rose (``up``) and fell (``down``).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.irrbb import behavioural as rv_beh

from . import assumptions as asm
from ...io.fdic import Report
from ...io.treasury import ParCurve, curve_as_of


@dataclass(frozen=True)
class Series:
    """Aligned quarterly series ending at the valuation date (oldest first)."""

    dates: list[str]
    client_rate: np.ndarray                 # (T,) decimals, annualised
    market_3m: np.ndarray                   # (T,) decimals
    tranche_yields: np.ndarray              # (T, J)


def quarterly_series(reports: list[Report], curves: dict[str, ParCurve], vd: str) -> Series:
    """The quarterly cost of deposits and the Treasury yields at each quarter end up to ``vd`` (reports and curves up to it only)."""
    known = [r for r in reports if r.report_date <= vd]
    dates, rate = [], []
    for i in range(1, len(known)):
        cur, prev = known[i], known[i - 1]
        ytd = cur.get("EDEP")
        q_interest = ytd if cur.report_date[5:7] == "03" else ytd - prev.get("EDEP")
        avg = 0.5 * (cur.get("DEP") + prev.get("DEP"))
        dates.append(cur.report_date)
        rate.append(4.0 * q_interest / avg)
    tr = np.array([[curve_as_of(curves, d).par[label] for label, _ in asm.TRANCHES] for d in dates])
    m3 = np.array([curve_as_of(curves, d).par["3 Mo"] for d in dates])
    return Series(dates, np.array(rate), m3, tr)


def deposit_beta(s: Series, n: int = asm.FIT_QUARTERS) -> dict[str, Any]:
    """Pass-through of the market rate to the deposit cost over the last ``n`` quarters: slope through the origin, per direction."""
    dm = np.diff(s.market_3m[-(n + 1):])
    dc = np.diff(s.client_rate[-(n + 1):])
    out = {}
    for name, mask in (("up", dm > 0), ("down", dm < 0)):
        if mask.sum() < 3 or float(np.sum(dm[mask] ** 2)) == 0.0:
            raise ValueError(f"the {name} pass-through needs at least 3 quarters of {name} moves in the window")
        out[name] = float(np.clip(np.sum(dm[mask] * dc[mask]) / np.sum(dm[mask] ** 2), 0.0, 1.0))
        out[f"n_{name}"] = int(mask.sum())
    return out


def replicating_fit(s: Series, end: int, n: int = asm.FIT_QUARTERS) -> dict[str, Any]:
    """The engine's replicating portfolio on the ``n`` quarters ending at index ``end`` (inclusive) of the series."""
    lo = end + 1 - n
    if lo < 0:
        raise ValueError("the series is too short for the estimation window")
    mats = np.array([m for _, m in asm.TRANCHES])
    rp = rv_beh.replicating_portfolio(s.client_rate[lo:end + 1], s.tranche_yields[lo:end + 1], mats)
    return {"window_start": s.dates[lo], "window_end": s.dates[end], "weights": [float(w) for w in rp.weights],
            "weighted_average_maturity_years": float(rv_beh.weighted_average_maturity(mats, rp.weights)),
            "margin_volatility": None if rp.margin_volatility is None else float(rp.margin_volatility)}


def nmd_model(s: Series, vd: str) -> dict[str, Any]:
    """The fit of one valuation date and its stability windows (ending at the date, one year before and two years before)."""
    end = len(s.dates) - 1
    if s.dates[end] != vd:
        raise ValueError(f"the series ends at {s.dates[end]}, not at the valuation date {vd}")
    wins = [replicating_fit(s, end - asm.STABILITY_STRIDE_QUARTERS * k) for k in range(asm.STABILITY_WINDOWS - 1, -1, -1)]
    return {"fit": wins[-1], "stability": wins, "beta": deposit_beta(s)}


def sigma_3y(curves: dict[str, ParCurve], vd: str) -> float:
    """Annualised standard deviation of the daily changes of the 3-month par yield over the three years up to ``vd``."""
    start = f"{int(vd[:4]) - asm.SIGMA_YEARS}{vd[4:]}"
    days = sorted(d for d in curves if start < d <= vd)
    y = np.array([curves[d].par["3 Mo"] for d in days])
    sd = float(np.std(np.diff(y), ddof=1) * np.sqrt(252.0))
    if not sd > 0.0:
        raise ValueError("the 3-month yield did not move in the calibration window")
    return sd
