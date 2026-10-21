"""The synthetic USD swap book of decision R1 and the named parameters of C12 (decision D6).

Every value here is a convention: the sources give none of it, so each carries its value, its unit and the label "convention"
in the documents. The book is the 10 year payer of 10M USD (the single swap) and, with it, a 5 year receiver of 6M, a 3 year
payer of 4M and a 0.5 year receiver of 2M (the netting set); the fixed rate of a swap is the par yield at its maturity on the
curve date, rounded to 10 bp.

Times are years on the 30/360 axis of the case (months over 12, calendar days over 360), the same axis ORE uses with the
30/360 day counter; the MPoR is stated in business days and the close-out offset is its calendar-day equivalent (10 business days
are 14 calendar days, 20 are 28), as ORE counts it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.ccr.swaps import Swap

from ...io import treasury

CURRENCY = "USD"
FLOATING_LEG = "USD floating leg on the single curve of the case"
FIXED_FREQUENCY = 2
RATE_ROUND = 0.001   # 10 bp

#: trade id, notional (USD), maturity (years), side
TRADES: tuple[tuple[str, float, float, str], ...] = (
    ("SW-1", 10_000_000.0, 10.0, "payer"),
    ("SW-2", 6_000_000.0, 5.0, "receiver"),
    ("SW-3", 4_000_000.0, 3.0, "payer"),
    ("SW-4", 2_000_000.0, 0.5, "receiver"),
)
SINGLE_MEMBER = "SW-1"
PAR_LABEL = {0.5: "6 Mo", 3.0: "3 Yr", 5.0: "5 Yr", 10.0: "10 Yr"}

#: the report grid: monthly to one year, quarterly to three years, half-yearly to nine and a half years (33 points; the swaps reset
#: on the half-years, so every reset is on it; the book ends at ten years, where every exposure is zero)
GRID: tuple[float, ...] = tuple([k / 12 for k in range(1, 13)] + [1.0 + 0.25 * k for k in range(1, 9)]
                                + [3.0 + 0.5 * k for k in range(1, 14)])
#: the close-out offset of each CSA variant in years: the calendar-day equivalent of the MPoR on the 30/360 axis
MPOR_BD = {"short": 10, "long": 20}
MPOR_CALENDAR_DAYS = {10: 14, 20: 28}


def closeout_years(mpor_business_days: int) -> float:
    return MPOR_CALENDAR_DAYS[mpor_business_days] / 360.0


# ---------------------------------------------------------------------------------------------------- named parameters

PATH_COUNT = 20_000
BACKTEST_PATHS = 4_000
CRITICAL_COUNT = 1_000
STRESS_WINDOW = ("2007-01-01", "2009-12-31")
BACKTEST_START = "2000-01"
PFE_QUANTILE = 0.95
IM_QUANTILE = 0.99
WWR_B_GRID = [-2.0, 0.0, 1.0, 2.0, 4.0]
CSA = {"threshold": 0.0, "mta": 10_000.0, "independent_amount": 0.0, "remargining_days": 1}


def _c(value: Any, unit: str) -> dict[str, Any]:
    return {"value": value, "unit": unit, "label": "convention"}


def named_parameters(seed: int, path_count: int = PATH_COUNT, backtest_paths: int = BACKTEST_PATHS,
                     critical_count: int = CRITICAL_COUNT) -> dict[str, Any]:
    """The 33 named parameters of the document, each with the label "convention"."""
    return {
        "notionals": _c([t[1] for t in TRADES], "USD"),
        "maturities_years": _c([t[2] for t in TRADES], "years"),
        "sides": _c([t[3] for t in TRADES], "payer or receiver"),
        "netting_set_members": _c([t[0] for t in TRADES], "trade ids"),
        "single_swap_member": _c(SINGLE_MEMBER, "trade id"),
        "fixed_rate_rule": _c("the par yield at the swap's maturity on the curve date, rounded to 10 bp", "rule"),
        "csa_threshold": _c(CSA["threshold"], "USD"),
        "csa_minimum_transfer_amount": _c(CSA["mta"], "USD"),
        "csa_independent_amount": _c(CSA["independent_amount"], "USD"),
        "mpor_business_days_short": _c(MPOR_BD["short"], "business days"),
        "mpor_business_days_long": _c(MPOR_BD["long"], "business days"),
        "counterparty_spread": _c(0.0125, "decimal per year"),
        "counterparty_lgd": _c(0.6, "decimal"),
        "bank_spread": _c(0.008, "decimal per year"),
        "bank_lgd": _c(0.6, "decimal"),
        "pfe_quantile": _c(PFE_QUANTILE, "decimal"),
        "path_count": _c(path_count, "paths"),
        "seed": _c(int(seed), "integer"),
        "time_grid_years": _c(list(GRID), "years"),
        "wwr_b_grid": _c(list(WWR_B_GRID), "per USD million"),
        "im_quantile": _c(IM_QUANTILE, "decimal"),
        "im_horizon_calendar_days": _c(14, "calendar days (10 business days)"),
        "im_mpor_calendar_days": _c(14, "calendar days (10 business days)"),
        "im_regression_order": _c(2, "polynomial order"),
        "ba_cva_sector": _c("financials", "MAR50.16 Table 1 sector"),
        "ba_cva_rating": _c("investment-grade", "class"),
        "stress_window_start": _c(STRESS_WINDOW[0], "date"),
        "stress_window_end": _c(STRESS_WINDOW[1], "date"),
        "backtest_window_start": _c(BACKTEST_START, "month"),
        "backtest_paths_per_date": _c(backtest_paths, "paths"),
        "backtest_simulated_critical_count": _c(critical_count, "simulated backtests"),
        "reconciliation_se_threshold": _c(2, "combined standard errors"),
        "ee_check_k_se": _c(3, "standard errors"),
    }


# --------------------------------------------------------------------------------------------------------- the trades


@dataclass(frozen=True)
class Trade:
    trade_id: str
    notional: float
    maturity: float
    side: str
    fixed_rate: float

    def swap(self) -> Swap:
        return Swap(self.trade_id, self.notional, self.fixed_rate, self.side == "payer", 0.0, self.maturity, FIXED_FREQUENCY)

    def document(self) -> dict[str, Any]:
        return {"trade_id": self.trade_id, "notional": {"amount": self.notional, "currency": CURRENCY},
                "fixed_rate": self.fixed_rate, "side": self.side, "start_years": 0.0, "maturity_years": self.maturity,
                "fixed_frequency_per_year": FIXED_FREQUENCY, "floating_leg": FLOATING_LEG, "label": "convention"}


def trades_at(par: treasury.ParCurve, members: tuple[str, ...] | None = None) -> list[Trade]:
    """The book on a curve: each fixed rate is the par yield of the swap's maturity, rounded to 10 bp. A maturity the curve does
    not quote raises (never filled)."""
    out = []
    for tid, notional, maturity, side in TRADES:
        if members is not None and tid not in members:
            continue
        label = PAR_LABEL[maturity]
        if label not in par.par:
            raise ValueError(f"{par.observation_date}: the {label} par yield is not quoted, so the fixed rate of {tid} is undefined")
        out.append(Trade(tid, notional, maturity, side, float(np.round(par.par[label] / RATE_ROUND) * RATE_ROUND)))
    return out


def book_document(trades: list[Trade], netting_set_id: str) -> dict[str, Any]:
    return {"netting_set_id": netting_set_id, "currency": CURRENCY, "trades": [t.document() for t in trades]}


def swaps_of(trades: list[Trade]) -> list[Swap]:
    return [t.swap() for t in trades]
