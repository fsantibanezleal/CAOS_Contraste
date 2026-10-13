"""The charge-off panel of C08 (CT-901 to CT-905): cleaning with counted exclusions, the LGD proxy, the default cohorts and
the covariates known at the charge-off.

The SBA 7(a) public file has no recovery cash flows (dossier 08 A.6), so the realised LGD of a charged-off loan is a
proxy (decision D2 of the U6 sizing): the gross charge-off amount over the gross approved amount, ``GrossChargeOffAmount``
over ``GrossApproval``. The approved amount overstates the exposure at default of an amortising loan, so the proxy is
biased low. The proxy can lie outside [0, 1] (capitalised interest and fees charged off; a charge-off above the approval):
such a value is kept and flagged by the engine's ``range_flag``, never clipped. A ratio above ``MAX_RATIO`` is a unit error
of ``GrossApproval`` (a loan approved for 75 dollars and charged off for 683,194) and is left out by a counted exclusion.

The only dates of a loan are the approval and the charge-off, so the charge-off date plays two roles: the default date that
assigns the cohort and the closing date of the workout (``cutoff.training_mask``).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..c06.panel import SECTOR_NAMES, sector_index

#: the default cohorts by charge-off year (SDD section 5, case C08), in order
COHORTS: tuple[tuple[str, int, int], ...] = (
    ("2003-06", 2003, 2006), ("2007-08", 2007, 2008), ("2009-10", 2009, 2010),
    ("2011-13", 2011, 2013), ("2014-19", 2014, 2019), ("2020-23", 2020, 2023),
)
#: a charge-off more than ten times the approval is a unit error of the approved amount, not a fee or an interest charge
MAX_RATIO = 10.0
#: the first and last year of a cohort: a charge-off dated after the last cohort belongs to none and is counted
LAST_COHORT_YEAR = COHORTS[-1][2]
#: the seasoning ratio (months from approval to charge-off over the term) is capped here as a feature (never an LGD)
SEASONING_CAP = 1.5
CONTINUOUS = ("log_amount", "log_term", "guaranteed_share", "seasoning_share")
#: the sector dummies: every sector group but the last ("other-unknown"), the reference
SECTOR_DUMMIES = SECTOR_NAMES[:-1]
FEATURE_NAMES = (*CONTINUOUS, "revolver", *(f"sector_{s}" for s in SECTOR_DUMMIES))


def lgd_proxy(chargeoff_amount: np.ndarray, gross_approval: np.ndarray) -> np.ndarray:
    """The proxy LGD: ``GrossChargeOffAmount / GrossApproval``. Not clipped."""
    return np.asarray(chargeoff_amount, dtype=float) / np.asarray(gross_approval, dtype=float)


def cohort_of_year(year: int) -> str | None:
    for cid, lo, hi in COHORTS:
        if lo <= year <= hi:
            return cid
    return None


def cohort_bounds(cohort_id: str) -> tuple[int, int]:
    for cid, lo, hi in COHORTS:
        if cid == cohort_id:
            return lo, hi
    raise KeyError(f"unknown C08 cohort {cohort_id!r}; known: {[c[0] for c in COHORTS]}")


@dataclass(frozen=True)
class Defaults:
    """The cleaned charge-offs, one array per column, every array of length ``n``. No identifier or name is kept."""

    chargeoff_date: np.ndarray    # datetime64[D]
    approval_date: np.ndarray     # datetime64[D]
    year: np.ndarray              # int64, the charge-off (default) year
    gross_approval: np.ndarray    # float64 USD
    chargeoff_amount: np.ndarray  # float64 USD, GrossChargeOffAmount
    term: np.ndarray              # int64 months
    revolver: np.ndarray          # bool
    sector: np.ndarray            # int64 index into the c06 SECTOR_NAMES
    guaranteed_share: np.ndarray  # float64 in [0, 1]: SBAGuaranteedApproval over GrossApproval, known at approval
    seasoning_share: np.ndarray   # float64: months from approval to charge-off over the term, capped
    rate: np.ndarray              # float64 decimal annual initial rate, NaN when the file records none (contract check only)

    @property
    def n(self) -> int:
        return int(self.gross_approval.shape[0])

    @property
    def y(self) -> np.ndarray:
        """The proxy LGD of every default, as it is (outside [0, 1] where it is)."""
        return lgd_proxy(self.chargeoff_amount, self.gross_approval)

    def take(self, mask: np.ndarray) -> Defaults:
        return Defaults(**{f: getattr(self, f)[mask] for f in self.__dataclass_fields__})

    def design(self) -> np.ndarray:
        """The covariates (no intercept), columns ``FEATURE_NAMES``: log approval, log term, guarantee share and seasoning
        (continuous, standardised by the ladder with its training moments), the revolving flag and the sector dummies."""
        cols = [np.log(self.gross_approval), np.log(self.term.astype(float)), self.guaranteed_share, self.seasoning_share,
                self.revolver.astype(float)]
        cols += [(self.sector == k).astype(float) for k in range(len(SECTOR_DUMMIES))]
        return np.column_stack(cols).astype(float)


def _months_between(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    ma = a.astype("datetime64[M]").astype(np.int64)
    mb = b.astype("datetime64[M]").astype(np.int64)
    return mb - ma


def prepare(df: pd.DataFrame) -> tuple[Defaults, dict[str, int]]:
    """Clean the reader's table into ``Defaults`` and count every charge-off left out, by reason (nothing is dropped
    silently). The rows that are not charge-offs are not defaults and are not counted as exclusions."""
    co = df[df["status"].astype("string").eq("CHGOFF").fillna(False).to_numpy(dtype=bool)].reset_index(drop=True)
    n0 = len(co)
    reasons: dict[str, int] = {}
    keep = np.ones(n0, dtype=bool)

    def drop(mask: np.ndarray, why: str) -> None:
        nonlocal keep
        mask = np.asarray(mask, dtype=bool)
        hit = keep & mask
        reasons[why] = int(hit.sum())
        keep = keep & ~mask

    gross = co["gross_approval"].to_numpy(dtype=float)
    amount = co["chargeoff_amount"].to_numpy(dtype=float)
    guar = co["guaranteed_approval"].to_numpy(dtype=float)
    term = co["term_months"].to_numpy(dtype=float)
    cdate = co["chargeoff_date"]
    adate = co["approval_date"]
    drop(cdate.isna().to_numpy(), "no-chargeoff-date")
    drop(adate.isna().to_numpy(), "no-approval-date")
    drop(~(term > 0) | (term > 480), "term-missing-or-implausible")
    drop(~(gross > 0), "approval-amount-missing-or-not-positive")
    drop(~(amount >= 0), "chargeoff-amount-missing-or-negative")
    drop(~((guar >= 0) & (guar <= gross * (1.0 + 1e-9))), "guarantee-missing-or-outside-the-approval")
    drop((cdate < adate).to_numpy(), "chargeoff-before-approval")
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = amount / gross
    drop(~(ratio <= MAX_RATIO), "proxy-ratio-above-ten")
    year_all = cdate.dt.year.to_numpy(dtype="float64", na_value=np.nan)
    drop(~(year_all <= LAST_COHORT_YEAR), "chargeoff-after-the-last-cohort")
    d = co.loc[keep].reset_index(drop=True)
    cdt = d["chargeoff_date"].to_numpy(dtype="datetime64[D]")
    adt = d["approval_date"].to_numpy(dtype="datetime64[D]")
    t = d["term_months"].to_numpy(dtype=float)
    season = np.minimum(np.maximum(_months_between(adt, cdt), 0) / np.maximum(t, 1.0), SEASONING_CAP)
    g = d["gross_approval"].to_numpy(dtype=float)
    rate = d["interest_rate_pct"].to_numpy(dtype=float) / 100.0
    out = Defaults(
        chargeoff_date=cdt, approval_date=adt, year=cdt.astype("datetime64[Y]").astype(np.int64) + 1970,
        gross_approval=g, chargeoff_amount=d["chargeoff_amount"].to_numpy(dtype=float), term=t.astype(np.int64),
        revolver=d["revolver"].to_numpy(dtype=bool), sector=sector_index(d["naics"]),
        guaranteed_share=np.minimum(d["guaranteed_approval"].to_numpy(dtype=float) / g, 1.0), seasoning_share=season,
        rate=np.where((rate > 0.0) & (rate < 0.5), rate, np.nan))
    counts = {"charge-offs-read": n0, **reasons, "defaults-kept": int(len(d))}
    return out, counts


@dataclass(frozen=True)
class AnnualRate:
    """The annual charge-off rate of the SBA book, the downturn indicator: charge-offs of a calendar year over the loans
    open at its start (approved before it, not yet charged off or paid)."""

    years: np.ndarray       # int64, strictly increasing
    at_risk: np.ndarray     # int64 loans open on 1 January
    chargeoffs: np.ndarray  # int64
    rate: np.ndarray        # float64 decimal per year


def annual_rate(df: pd.DataFrame, first_year: int = 1993, last_year: int = LAST_COHORT_YEAR) -> AnnualRate:
    """The charge-off rate of each year from ``first_year`` to ``last_year`` (the first years of the file hold too few
    open loans to read a rate). The loans are the disbursed ones: paid in full, charged off or active (exempt)."""
    status = df["status"].astype("string")
    ok = status.isin(["P I F", "CHGOFF", "EXEMPT"]).to_numpy(dtype=bool, na_value=False) & df["approval_date"].notna().to_numpy()
    d = df.loc[ok]
    appr = d["approval_date"].dt.year.to_numpy(dtype=np.int64)
    s = d["status"].astype("string").to_numpy()
    exit_dt = np.where(s == "CHGOFF", d["chargeoff_date"], d["paid_date"])
    exit_year = pd.to_datetime(pd.Series(exit_dt)).dt.year.to_numpy(dtype="float64", na_value=np.nan)
    exit_year = np.where((exit_year < appr) | np.isnan(exit_year), np.inf, exit_year)  # an exit before the approval is ignored
    is_co = (s == "CHGOFF") & np.isfinite(exit_year)
    years = np.arange(first_year, last_year + 1, dtype=np.int64)
    at_risk = np.array([int(((appr < y) & (exit_year >= y)).sum()) for y in years], dtype=np.int64)
    cos = np.array([int((is_co & (exit_year == y) & (appr < y)).sum()) for y in years], dtype=np.int64)
    with np.errstate(invalid="ignore", divide="ignore"):
        rate = np.where(at_risk > 0, cos / np.maximum(at_risk, 1), np.nan)
    return AnnualRate(years=years, at_risk=at_risk, chargeoffs=cos, rate=rate)
