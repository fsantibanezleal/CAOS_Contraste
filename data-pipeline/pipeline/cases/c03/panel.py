"""The loan panel of C03 (CT-801, CT-802): cleaning with counted exclusions, the origination attributes a model may use and the
5-year charge-off target as known at an observation date.

The file is read by the shared reader ``pipeline/io/sba.py``; this module maps it to arrays and does nothing the reader should
do. The target of a loan is a charge-off dated within 60 months of its approval. It is read at an observation date O (a
training cutoff, or the files' as-of date):

- an event: the file shows a charge-off dated on or before both the horizon end (approval plus 60 months) and O;
- a non-event: no such charge-off, and O is on or after the horizon end (the loan was observed for the whole horizon; a
  charge-off is shown as CHGOFF in the file, never as an active loan, so an active, paid or later charged-off loan is known
  not to have charged off inside the horizon);
- no outcome (censored, -1): no such charge-off and O is before the horizon end. The loan is not counted as performing; it
  is left out of every rate and every fit.

The inputs of a model are fixed at approval: the amount, the guaranteed share, the term, the sector and whether the loan is
revolving. The interest rate is not an input: the file records it only from the FY2008 approvals (51% of the rows are blank).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..c06.panel import SECTOR_NAMES, sector_index

EXIT_OPEN, EXIT_PAID, EXIT_DEFAULT = 0, 1, 2
LABEL_CENSORED = -1
HORIZON_MONTHS = 60
FEATURES = ("log10_amount", "guarantee_share", "term_months", "sector", "revolver")
CATEGORICAL = ("sector",)


def fiscal_year(dates: np.ndarray) -> np.ndarray:
    """The SBA fiscal year of a date: it starts on 1 October, so 1 October 2009 is in FY2010."""
    d = np.asarray(dates, dtype="datetime64[D]")
    year = d.astype("datetime64[Y]").astype(np.int64) + 1970
    month = d.astype("datetime64[M]").astype(np.int64) % 12 + 1
    return (year + (month >= 10)).astype(np.int64)


def horizon_end(approval: np.ndarray, months: int = HORIZON_MONTHS) -> np.ndarray:
    """The date ``months`` after each approval date (the last day of the month when the day does not exist)."""
    idx = pd.DatetimeIndex(np.asarray(approval, dtype="datetime64[D]"))
    return (idx + pd.DateOffset(months=months)).to_numpy().astype("datetime64[D]")


@dataclass(frozen=True)
class Loans:
    """The cleaned loans, one array per column, every array of length ``n``. No identifier or name is kept."""

    approval: np.ndarray          # datetime64[D]
    fy: np.ndarray                # int64, SBA fiscal year of the approval
    term: np.ndarray              # int64 months
    amount: np.ndarray            # float64 USD, gross approval
    guarantee_share: np.ndarray   # float64 in [0, 1], SBA guaranteed approval over the gross approval
    revolver: np.ndarray          # bool
    sector: np.ndarray            # object, a sector group name
    exit_kind: np.ndarray         # int64: EXIT_OPEN, EXIT_PAID, EXIT_DEFAULT (the file's final status)
    exit_date: np.ndarray         # datetime64[D], NaT while open
    horizon_end: np.ndarray       # datetime64[D], approval plus 60 months
    rate: np.ndarray              # float64 decimal annual, NaN where the file records none (not a model input)
    asof: np.datetime64           # the date the file's statuses are as of

    @property
    def n(self) -> int:
        return int(self.amount.shape[0])

    def take(self, idx) -> Loans:
        i = np.asarray(idx)
        return Loans(self.approval[i], self.fy[i], self.term[i], self.amount[i], self.guarantee_share[i], self.revolver[i],
                     self.sector[i], self.exit_kind[i], self.exit_date[i], self.horizon_end[i], self.rate[i], self.asof)


def prepare(df: pd.DataFrame) -> tuple[Loans, dict[str, int]]:
    """Clean the reader's table into ``Loans`` and count every row left out, by reason (nothing is dropped silently).

    A loan enters when it was disbursed and still has a final or active status: paid in full (PIF), charged off (CHGOFF) or
    exempt (active, the file discloses no further status). Cancelled and committed loans are out. A missing or implausible
    term, a missing or non-positive amount, a missing guaranteed amount, a charge-off with no date, a payment with no date and
    a charge-off or payment dated before the approval are data errors and are out."""
    n0 = len(df)
    reasons: dict[str, int] = {}
    keep = np.ones(n0, dtype=bool)

    def drop(mask: np.ndarray, why: str) -> None:
        nonlocal keep
        hit = keep & mask
        reasons[why] = int(hit.sum())
        keep = keep & ~mask

    status = df["status"].astype("string")
    drop(~status.isin(["P I F", "CHGOFF", "EXEMPT"]).to_numpy(dtype=bool, na_value=False), "not-disbursed-or-cancelled")
    drop(df["approval_date"].isna().to_numpy(), "no-approval-date")
    drop((~(df["term_months"] > 0)).to_numpy() | (df["term_months"] > 480).to_numpy(), "term-missing-or-implausible")
    drop((~(df["gross_approval"] > 0)).to_numpy(), "amount-missing-or-not-positive")
    drop(df["guaranteed_approval"].isna().to_numpy(), "guaranteed-amount-missing")
    co = status.eq("CHGOFF").to_numpy(dtype=bool, na_value=False)
    pif = status.eq("P I F").to_numpy(dtype=bool, na_value=False)
    drop(co & df["chargeoff_date"].isna().to_numpy(), "chargeoff-without-date")
    drop(pif & df["paid_date"].isna().to_numpy(), "paid-without-date")
    drop(co & (df["chargeoff_date"] < df["approval_date"]).to_numpy(), "chargeoff-before-approval")
    drop(pif & (df["paid_date"] < df["approval_date"]).to_numpy(), "paid-before-approval")
    d = df.loc[keep].reset_index(drop=True)
    st = d["status"].astype("string")
    is_co = st.eq("CHGOFF").to_numpy(dtype=bool, na_value=False)
    is_pif = st.eq("P I F").to_numpy(dtype=bool, na_value=False)
    exit_kind = np.where(is_co, EXIT_DEFAULT, np.where(is_pif, EXIT_PAID, EXIT_OPEN)).astype(np.int64)
    exit_date = np.full(len(d), np.datetime64("NaT", "D"), dtype="datetime64[D]")
    exit_date[is_co] = d["chargeoff_date"].to_numpy(dtype="datetime64[D]")[is_co]
    exit_date[is_pif] = d["paid_date"].to_numpy(dtype="datetime64[D]")[is_pif]
    approval = d["approval_date"].to_numpy(dtype="datetime64[D]")
    amount = d["gross_approval"].to_numpy(dtype=float)
    share = np.clip(d["guaranteed_approval"].to_numpy(dtype=float) / amount, 0.0, 1.0)
    names = np.array(SECTOR_NAMES, dtype=object)
    rate = d["interest_rate_pct"].to_numpy(dtype=float) / 100.0
    rate = np.where((rate > 0.0) & (rate < 0.5), rate, np.nan)
    asof = np.datetime64(pd.Timestamp(d["asof_date"].max()).date(), "D") if len(d) else np.datetime64("NaT", "D")
    loans = Loans(
        approval=approval, fy=fiscal_year(approval), term=d["term_months"].to_numpy(dtype=np.int64), amount=amount,
        guarantee_share=share, revolver=d["revolver"].to_numpy(dtype=bool), sector=names[sector_index(d["naics"])],
        exit_kind=exit_kind, exit_date=exit_date, horizon_end=horizon_end(approval), rate=rate, asof=asof,
    )
    counts = {"rows-read": n0, **reasons, "loans-kept": int(len(d))}
    return loans, counts


def label(loans: Loans, observed_at) -> np.ndarray:
    """The 5-year target as known at ``observed_at``: 1 an event, 0 a non-event, -1 no outcome (see the module docstring)."""
    o = np.datetime64(observed_at, "D")
    event = ((loans.exit_kind == EXIT_DEFAULT) & (loans.exit_date <= loans.horizon_end) & (loans.exit_date <= o))
    covered = o >= loans.horizon_end
    return np.where(event, 1, np.where(covered, 0, LABEL_CENSORED)).astype(np.int8)


def features(loans: Loans, idx=None) -> pd.DataFrame:
    """The model inputs of the loans at ``idx`` (all when None): origination attributes only."""
    ln = loans if idx is None else loans.take(np.asarray(idx))
    return pd.DataFrame({
        "log10_amount": np.log10(ln.amount), "guarantee_share": ln.guarantee_share, "term_months": ln.term.astype(float),
        "sector": pd.Series(ln.sector, dtype=object), "revolver": ln.revolver.astype(int),
    })[list(FEATURES)]
