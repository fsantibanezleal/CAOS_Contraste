"""The behavioural and structural assumptions of C15, each a named field with its value, unit, source kind and source.

Real curves, synthetic bank (design.md): the BCCh yields are real; Banco Andino is a synthetic bank whose balance-sheet aggregates are
calibrated to the CMF system aggregates (``targets.py``) and whose every other quantity (the UF share of each portfolio, the repricing
profile of an item, the deposit split, the NMD requests, the prepayment and redemption rates, the deposit beta) is stated here as
``synthetic-stated``, never presented as a CMF figure. ``check_registry`` is the gate: a missing unit or source, a kind that differs
from the expected one, or a synthetic value whose source does not say so, is a finding.
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


#: SRP31 Table 4, in the category names of RAN 21-13 Annex 1: cap on the core share and on the average maturity (years) of the core
CAPS: dict[str, tuple[float, float]] = {
    "retail-operational": (0.9, 5.0), "retail-non-operational": (0.7, 4.5), "wholesale": (0.5, 4.0),
}
#: stated requests: two stand above their cap on purpose (the standardised treatment cuts them and says so), one sits within it
REQUESTS: dict[str, Request] = {
    "retail-operational": Request(0.95, 5.5), "retail-non-operational": Request(0.70, 4.0), "wholesale": Request(0.60, 4.5),
}
CATEGORY_CLASS = {"retail-operational": "nmd-retail-operational", "retail-non-operational": "nmd-retail-non-operational",
                  "wholesale": "nmd-wholesale"}

# structure of the synthetic book (shares are of the quantity named; every one is a synthetic stated value)
CASH_SHARE_OF_ASSETS = 0.04
UF_SHARE = {"commercial": 0.15, "mortgage": 0.85, "securities": 0.35, "time_deposits": 0.35}
COMMERCIAL_FLOATING_SHARE = 0.60
NMD_SHARE_OF_DEPOSITS = 0.40
NMD_SEGMENT_SHARE = {"retail-operational": 0.30, "retail-non-operational": 0.25, "wholesale": 0.45}
PREPAYMENT_CPR = 0.05
TERM_DEPOSIT_REDEMPTION_RATE = 0.05
DEPOSIT_BETA = 0.40
JITTER = 0.15
HORIZON_MONTHS = 12
#: the Hull-White one-factor scenarios of the EaR and EVaR: mean reversion and volatility per leg (synthetic; no rate history of a month is
#: long enough to fit them, and nothing dated after the valuation date may be read)
HW1F_A = 0.10
HW1F_SIGMA = {"CLP": 0.0100, "UR": 0.0060}
LEVELS = (0.95, 0.99)
N_PATHS = 100_000
N_BATCHES = 20
#: months between resets of the dynamic NII items by kind (synthetic)
REPRICE_MONTHS = {"floating": 3, "time": 6, "fixed": 120}
#: margins over the short rate or the curve of the dynamic NII items (synthetic, per annum)
MARGINS = {"cash": -0.0050, "interbank": 0.0010, "commercial_floating": 0.0200, "commercial_fixed": 0.0250, "consumer": 0.0900,
           "mortgage": 0.0150, "securities": 0.0030, "time_deposit": -0.0020, "bond": 0.0080}

REGISTRY: dict[str, Assumption] = {
    "nmd_core_share": Assumption(None, "share", "regulatory-cap",
        "Requested by Contraste (synthetic) per category; the standardised treatment uses min(request, SRP31 Table 4 cap) (nmd_split with "
        "enforce_caps) and the segment says cap_applied."),
    "nmd_core_maturity_years": Assumption(None, "years", "regulatory-cap",
        "Requested by Contraste (synthetic) per category; the standardised treatment uses min(request, cap)."),
    "prepayment_cpr": Assumption(PREPAYMENT_CPR, "per year", "synthetic-stated",
        "Stated by Contraste (synthetic): the CMF aggregates carry no prepayment history. The residential mortgage items carry the "
        "prepayable-loan class; the SRP31.119 multipliers are tabled in the models document and, as in C14, not applied per shock (the "
        "definition of the outstanding notional of SRP31.121 is UNVERIFIED in the engine contract)."),
    "term_deposit_redemption_rate": Assumption(TERM_DEPOSIT_REDEMPTION_RATE, "share of the term deposit", "synthetic-stated",
        "Stated by Contraste (synthetic): the baseline early-redemption rate TDRR0 of SRP31.125, scaled by the Table 6 multiplier of each shock "
        "through the engine's term-deposit redemption function."),
    "deposit_beta": Assumption(DEPOSIT_BETA, "pass-through", "synthetic-stated",
        "Stated by Contraste (synthetic): one pass-through of the short rate to the rate paid on non-maturity deposits, used by the dynamic NII. "
        "No deposit-rate history exists for a synthetic bank, so no beta is fitted."),
    "item_profiles": Assumption("repricing profiles", "years by bucket", "synthetic-stated",
        "The CMF aggregates carry no maturity or repricing profile. Each item of the book has a repricing profile stated by Contraste "
        "(synthetic): the times (years) and weights over which it slots into the 19 buckets, perturbed per item by a seeded log-normal factor "
        f"of {JITTER} and renormalised, so that two seeds give two banks of the same size."),
    "currency_split": Assumption(UF_SHARE, "share of the portfolio", "synthetic-stated",
        "The UF-indexed share of each portfolio (commercial, mortgage, securities, time deposits) is stated by Contraste (synthetic): the CMF "
        "report used here does not split the aggregates by currency or indexation. Consumer loans and non-maturity deposits are in pesos."),
    "deposit_split": Assumption({"nmd_share": NMD_SHARE_OF_DEPOSITS, "segments": NMD_SEGMENT_SHARE}, "share of deposits", "synthetic-stated",
        "The split of deposits into non-maturity and term deposits, and of the non-maturity deposits into the three Annex 1 categories, is "
        "stated by Contraste (synthetic): the CMF report gives total deposits only."),
    "tier1_proxy": Assumption("equity (patrimonio)", "CLP million", "synthetic-stated",
        "Tier 1 is taken equal to the equity (patrimonio) of the CMF system aggregate scaled to the book, a synthetic proxy (the regulatory "
        "Tier 1 is below the equity); the book's assets less its liabilities equal it, the borrowings being the balancing item (synthetic)."),
    "reprice_months": Assumption(REPRICE_MONTHS, "months", "synthetic-stated",
        "Months between resets of the dynamic NII items (synthetic): 3 for floating items, 6 for term deposits, beyond the horizon for fixed "
        "items; margins over the short rate or the curve are stated per kind (synthetic). The UR leg carries the real rate only: the "
        "indexation income is outside the dynamic NII, which understates the net interest and indexation margin of the thresholds."),
    "hw1f_a": Assumption(HW1F_A, "per year", "synthetic-stated",
        "Mean reversion of the Hull-White one-factor scenarios of the EaR and EVaR, stated by Contraste (synthetic)."),
    "hw1f_sigma": Assumption(HW1F_SIGMA, "per year", "synthetic-stated",
        "Annual volatility of the short rate of each leg in the Hull-White one-factor scenarios (1.00 percent for the pesos leg, 0.60 percent for the "
        "UF leg), stated by Contraste (synthetic): the Banco Central's yields are read only up to the valuation date, and the days of the month "
        "before it are too few to estimate a volatility. The EaR is the base NII less the (1 - level) quantile of the 12-month NII of the paths; "
        "the EVE of a path is the base flows under a parallel shift equal to the change of its short rate over the horizon."),
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
        if kind == "synthetic-stated" and "synthetic" not in a.source.lower():
            found.append(f"{name}: stated synthetic but the source does not say so")
    return found
