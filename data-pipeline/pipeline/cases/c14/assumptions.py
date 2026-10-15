"""The behavioural assumptions of C14, each a named field with its value, unit, source kind and source.

Real aggregates, synthetic behaviour (design.md): the call-report items are real; every assumption below is either an SRP31
regulatory cap, a quantity fitted on the report history and the Treasury curves up to the valuation date, or a value Contraste
states (``synthetic-stated``) because the call report does not carry it. ``check_registry`` is the gate: a missing unit or source,
a kind that differs from the expected one, or a synthetic value whose source does not say so, is a finding.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SOURCE_KINDS = ("regulatory-cap", "fitted", "synthetic-stated")


@dataclass(frozen=True)
class Assumption:
    value: Any
    unit: str
    source_kind: str
    source: str


@dataclass(frozen=True)
class Request:
    """The core share and the average core maturity (years) asked for one NMD category."""

    share: float
    maturity: float


#: SRP31 Table 4: cap on the core share and on the average maturity (years) of the core, per category
CAPS: dict[str, tuple[float, float]] = {
    "retail-transactional": (0.9, 5.0), "retail-non-transactional": (0.7, 4.5), "wholesale": (0.5, 4.0),
}
#: the requests stand above every cap on purpose: the standardised treatment cuts them and says so (``cap_applied``)
REQUESTS: dict[str, Request] = {
    "retail-transactional": Request(0.95, 6.0), "retail-non-transactional": Request(0.75, 5.0), "wholesale": Request(0.60, 5.0),
}
#: upper edges, years, of the bands the report leaves open above
OPEN_EDGES: dict[str, float] = {
    "over_15y": 30.0, "over_5y_borrowing": 15.0, "mbs_average_life_over_3y": 15.0, "over_3y_time_deposit": 5.0,
}
PREPAYMENT_CPR = 0.08
TERM_DEPOSIT_REDEMPTION_RATE = 0.05
HW1F_A = 0.10
FLOOR = 0.0
HORIZON_MONTHS = 12
LEVELS = (0.95, 0.99)
N_PATHS = 100_000
N_BATCHES = 20
#: months between resets of the dynamic NII items
REPRICE_MONTHS = {"floating": 2, "3_12m": 8, "fixed": 120}
#: the pass-through windows and tranche maturities of the fits
FIT_QUARTERS = 16
STABILITY_STRIDE_QUARTERS = 4
STABILITY_WINDOWS = 3
TRANCHES = (("3 Mo", 0.25), ("1 Yr", 1.0), ("2 Yr", 2.0), ("3 Yr", 3.0), ("5 Yr", 5.0), ("7 Yr", 7.0), ("10 Yr", 10.0))
SIGMA_YEARS = 3

REGISTRY: dict[str, Assumption] = {
    "nmd_core_share": Assumption(None, "share", "regulatory-cap",
        "Requested by Contraste (synthetic) above each SRP31 Table 4 cap; the standardised treatment uses the cap (nmd_split with "
        "enforce_caps) and the segment says cap_applied."),
    "nmd_core_maturity_years": Assumption(None, "years", "regulatory-cap",
        "Requested by Contraste (synthetic) above each SRP31 Table 4 cap; the standardised treatment uses the cap."),
    "prepayment_cpr": Assumption(PREPAYMENT_CPR, "per year", "synthetic-stated",
        "Stated by Contraste (synthetic): the call report has no loan-level prepayment history. Applied to the amortising mortgage items "
        "(residential loans repricing beyond three months, mortgage-backed securities) in the behavioural flows; the SRP31.119 "
        "multipliers are tabled in the models document, not applied per shock."),
    "term_deposit_redemption_rate": Assumption(TERM_DEPOSIT_REDEMPTION_RATE, "share of the term deposit", "synthetic-stated",
        "Stated by Contraste (synthetic): the baseline early-redemption rate TDRR0 of SRP31.125, scaled by the Table 6 multiplier "
        "of each shock."),
    "deposit_beta": Assumption(None, "pass-through", "fitted",
        "Fitted per valuation date on the quarterly cost of deposits (deposit interest expense over average deposits) against the "
        "3-month Treasury par yield, last 16 quarters up to the date, slope through the origin on the quarters with a rising "
        "market rate (up) and a falling one (down)."),
    "open_band_edges": Assumption(OPEN_EDGES, "years", "synthetic-stated",
        "Upper edges of the bands the report leaves open above, stated by Contraste (synthetic): over 15 years to 30, over 5 years "
        "of borrowings to 15, mortgage securities with an average life over 3 years to 15, time deposits over 3 years to 5."),
    "band_spread": Assumption("uniform", "in time", "synthetic-stated",
        "Each band of the call report is spread uniformly over the buckets it overlaps (synthetic): the report gives no finer profile."),
    "amortisation": Assumption("linear", "in time", "synthetic-stated",
        "Mortgage pass-through securities, other mortgage-backed securities and closed-end residential loans amortise linearly to zero over "
        "their remaining maturity, the maturity uniform in its band (synthetic): their notional repricing cash flows are spread to the "
        "maturity, not placed at it. Bullet items (non-mortgage debt, commercial loans, borrowings, time deposits) sit at their maturity."),
    "hw1f_a": Assumption(HW1F_A, "per year", "synthetic-stated",
        "Mean reversion of the Hull-White one-factor scenarios, stated by Contraste (synthetic); the volatility is fitted."),
    "hw1f_sigma": Assumption(None, "per year", "fitted",
        "Annualised standard deviation of the daily changes of the 3-month Treasury par yield over the three years up to the "
        "valuation date."),
    "retail_share": Assumption(None, "share of the non-time deposits", "synthetic-stated",
        "The deposit accounts of 250 000 USD or less (FDIC DEPSMAMT less the time deposits of that size) stand for retail customers "
        "and the rest for wholesale: a synthetic mapping, because the call report has no customer-type split."),
    "reprice_months": Assumption(REPRICE_MONTHS, "months", "synthetic-stated",
        "Months between resets of the dynamic NII items (synthetic): 2 for the band of 3 months or less, 8 for 3 to 12 months, "
        "beyond the horizon for the rest."),
    "borrowing_rate": Assumption("short rate", "rate", "synthetic-stated",
        "Borrowings are priced at the short market rate with a pass-through of one (synthetic): the report holds no cost by "
        "instrument."),
}
#: the kind each assumption must have
EXPECTED_KIND = {k: v.source_kind for k, v in REGISTRY.items()}


def check_registry(reg: dict[str, Assumption]) -> list[str]:
    """Findings: a missing name, unit or source, a kind other than the expected one, a synthetic value not said synthetic."""
    found: list[str] = []
    for name, kind in EXPECTED_KIND.items():
        a = reg.get(name)
        if a is None:
            found.append(f"{name}: missing")
            continue
        if not a.unit.strip() or not a.source.strip():
            found.append(f"{name}: no unit or no source")
        if a.source_kind not in SOURCE_KINDS or a.source_kind != kind:
            found.append(f"{name}: source kind {a.source_kind!r}, expected {kind!r}")
        if kind in ("synthetic-stated",) and "synthetic" not in a.source.lower():
            found.append(f"{name}: stated synthetic but the source does not say so")
    return found
