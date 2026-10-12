"""The loan panel of C06 (CT-501, CT-504, CT-505): cleaning with counted exclusions, the book at a reporting date and the
observation of each loan as known at that date.

The cutoff rule (no look-ahead, CT-504): at a reporting date R a model sees only the loans approved on or before R, and
of each loan only what happened on or before R. A charge-off after R is a loan still open at R; a payment in full after R
is a loan still open at R. A loan with no exit by R is censored at R (or at its maturity), never counted as performing to
its term (CT-505). Whether a loan is in the book at R is a fact of R and is read from its own exit dates.

Ages are whole months (the month number difference, less one when the day of the later date is earlier), the time scale
is the loan's age in quarters.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

EXIT_OPEN, EXIT_PAID, EXIT_DEFAULT, EXIT_MATURED = 0, 1, 2, 3

#: loan size bands by gross approval in USD (fixed policy thresholds, not fitted)
SIZE_EDGES = (50_000.0, 150_000.0, 350_000.0)
#: term bands in months: up to 5 years, 10 years, 20 years, longer
TERM_EDGES = (60, 120, 240)
SEGMENT_IDS = ("term-le-60", "term-61-120", "term-121-240", "term-gt-240")
#: sector groups by the first two digits of the NAICS code
SECTOR_GROUPS: dict[str, tuple[str, ...]] = {
    "agriculture": ("11",),
    "mining-utilities-construction": ("21", "22", "23"),
    "manufacturing": ("31", "32", "33"),
    "wholesale": ("42",),
    "retail": ("44", "45"),
    "transport": ("48", "49"),
    "information-finance-professional": ("51", "52", "53", "54", "55", "56"),
    "education-health": ("61", "62"),
    "arts-recreation": ("71",),
    "accommodation-food": ("72",),
    "other-services": ("81",),
    "other-unknown": (),
}
SECTOR_NAMES = tuple(SECTOR_GROUPS)
_SECTOR_OF = {code: k for k, codes in enumerate(SECTOR_GROUPS.values()) for code in codes}
N_STRATA = 4 * 4 * len(SECTOR_NAMES) * 2


def month_number(d: np.ndarray) -> np.ndarray:
    """Months since 1970-01 of a datetime64 array."""
    return d.astype("datetime64[M]").astype(np.int64)


def day_of_month(d: np.ndarray) -> np.ndarray:
    return (d.astype("datetime64[D]") - d.astype("datetime64[M]").astype("datetime64[D]")).astype(np.int64) + 1


def months_between(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Whole months from date ``a`` to date ``b`` (arrays of datetime64, or one of them a scalar datetime64)."""
    a = np.asarray(a, dtype="datetime64[D]")
    b = np.asarray(b, dtype="datetime64[D]")
    return (month_number(b) - month_number(a) - (day_of_month(b) < day_of_month(a))).astype(np.int64)


@dataclass(frozen=True)
class Loans:
    """The cleaned loans, one array per column, every array of length ``n``. No identifier or name is kept."""

    approval: np.ndarray       # datetime64[D]
    term: np.ndarray           # int64 months
    amount: np.ndarray         # float64 USD, gross approval
    revolver: np.ndarray       # bool
    rate: np.ndarray           # float64 decimal annual, NaN when the file records none
    sector: np.ndarray         # int64 index into SECTOR_NAMES
    exit_kind: np.ndarray      # int64: EXIT_OPEN, EXIT_PAID, EXIT_DEFAULT (the file's final status)
    exit_date: np.ndarray      # datetime64[D], NaT while open
    chargeoff_amount: np.ndarray  # float64 USD, NaN unless a default
    asof: np.datetime64        # the date the file's statuses are as of

    @property
    def n(self) -> int:
        return int(self.amount.shape[0])

    @property
    def size_band(self) -> np.ndarray:
        return np.searchsorted(np.asarray(SIZE_EDGES), self.amount, side="right").astype(np.int64)

    @property
    def term_band(self) -> np.ndarray:
        return np.searchsorted(np.asarray(TERM_EDGES), self.term, side="left").astype(np.int64)

    @property
    def stratum(self) -> np.ndarray:
        """One code per (size band, term band, sector, revolver); the covariates of the Cox and hazard rungs."""
        return ((self.size_band * 4 + self.term_band) * len(SECTOR_NAMES) + self.sector) * 2 + self.revolver.astype(np.int64)

    @property
    def origination_quarter(self) -> np.ndarray:
        """Calendar quarter number (month number // 3) of the approval."""
        return month_number(self.approval) // 3


def decode_stratum(code: np.ndarray) -> dict[str, np.ndarray]:
    code = np.asarray(code, dtype=np.int64)
    revolver = code % 2
    rest = code // 2
    sector = rest % len(SECTOR_NAMES)
    rest = rest // len(SECTOR_NAMES)
    return {"size": rest // 4, "term": rest % 4, "sector": sector, "revolver": revolver}


def sector_index(naics: pd.Series) -> np.ndarray:
    two = naics.astype("string").str.strip().str[:2].fillna("")
    other = len(SECTOR_NAMES) - 1
    return np.array([_SECTOR_OF.get(s, other) for s in two.to_numpy(dtype=object)], dtype=np.int64)


def prepare(df: pd.DataFrame) -> tuple[Loans, dict[str, int]]:
    """Clean the reader's table into ``Loans`` and count every row left out, by reason (nothing is dropped silently).

    A loan enters when it was disbursed and still has a final or active status: paid in full (PIF), charged off
    (CHGOFF) or exempt (active, the file discloses no further status). Cancelled and committed loans are out. A charge-off
    or payment date before the approval date, a missing or non-positive term or amount, and a charge-off with no date are
    data errors and are out."""
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
    nat = np.datetime64("NaT", "D")
    exit_date = np.full(len(d), nat, dtype="datetime64[D]")
    exit_date[is_co] = d["chargeoff_date"].to_numpy(dtype="datetime64[D]")[is_co]
    exit_date[is_pif] = d["paid_date"].to_numpy(dtype="datetime64[D]")[is_pif]
    rate = d["interest_rate_pct"].to_numpy(dtype=float) / 100.0
    rate = np.where((rate > 0.0) & (rate < 0.5), rate, np.nan)
    coa = np.where(is_co, d["chargeoff_amount"].to_numpy(dtype=float), np.nan)
    asof = np.datetime64(pd.Timestamp(d["asof_date"].max()).date(), "D") if len(d) else np.datetime64("NaT", "D")
    loans = Loans(
        approval=d["approval_date"].to_numpy(dtype="datetime64[D]"),
        term=d["term_months"].to_numpy(dtype=np.int64),
        amount=d["gross_approval"].to_numpy(dtype=float),
        revolver=d["revolver"].to_numpy(dtype=bool),
        rate=rate, sector=sector_index(d["naics"]), exit_kind=exit_kind, exit_date=exit_date, chargeoff_amount=coa,
        asof=asof,
    )
    counts = {"rows-read": n0, **reasons, "loans-kept": int(len(d))}
    return loans, counts


@dataclass(frozen=True)
class Observation:
    """Each loan as known at the reporting date ``reporting_date`` (CT-504): its age at its last observed moment and how
    that moment ended."""

    reporting_date: np.datetime64
    selected: np.ndarray      # bool: approved on or before the reporting date
    age_months: np.ndarray    # int64: age at the end of observation (the age at default, payment, maturity or R)
    end_kind: np.ndarray      # int64: EXIT_OPEN (censored at R), EXIT_PAID, EXIT_DEFAULT, EXIT_MATURED
    age_at_reporting: np.ndarray  # int64: age at R for the selected loans (0 otherwise)

    @property
    def event(self) -> np.ndarray:
        return self.selected & (self.end_kind == EXIT_DEFAULT)

    @property
    def in_book(self) -> np.ndarray:
        """Open at R: approved, no default or payment on or before R, and not past maturity."""
        return self.selected & (self.end_kind == EXIT_OPEN)


def observe(loans: Loans, reporting_date: np.datetime64) -> Observation:
    """The loans as known at ``reporting_date``: only dates on or before it are read (CT-504). The later part of a loan's
    life is censored, whatever the file says about it."""
    r = np.datetime64(reporting_date, "D")
    selected = loans.approval <= r
    age_r = np.where(selected, months_between(loans.approval, np.full(loans.n, r)), 0)
    known_default = selected & (loans.exit_kind == EXIT_DEFAULT) & (loans.exit_date <= r)
    known_paid = selected & (loans.exit_kind == EXIT_PAID) & (loans.exit_date <= r)
    matured = selected & ~known_default & ~known_paid & (loans.term <= age_r)
    end_kind = np.full(loans.n, EXIT_OPEN, dtype=np.int64)
    end_kind[matured] = EXIT_MATURED
    end_kind[known_paid] = EXIT_PAID
    end_kind[known_default] = EXIT_DEFAULT
    age = np.minimum(age_r, loans.term)
    safe_exit = np.where(np.isnat(loans.exit_date), r, loans.exit_date)
    age_exit = months_between(loans.approval, safe_exit)
    age = np.where(known_default | known_paid, age_exit, age)
    age = np.where(selected, np.maximum(age, 0), 0)
    return Observation(reporting_date=r, selected=selected, age_months=age.astype(np.int64), end_kind=end_kind,
                       age_at_reporting=age_r.astype(np.int64))


def balance_fraction(age_months: np.ndarray, term_months: np.ndarray, eir: np.ndarray, revolver: np.ndarray) -> np.ndarray:
    """The modelled outstanding share of the gross approval after ``age_months``: a level-payment annuity at the loan's
    EIR over its term; a revolving line is carried at its full approval. The file has no balance, so this is a model,
    labelled as one wherever it is shown."""
    age = np.asarray(age_months, dtype=float)
    term = np.maximum(np.asarray(term_months, dtype=float), 1.0)
    r = np.asarray(eir, dtype=float) / 12.0
    age = np.clip(age, 0.0, term)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        grow_t = np.power(1.0 + r, term)
        grow_k = np.power(1.0 + r, age)
        annuity = (grow_t - grow_k) / (grow_t - 1.0)
    linear = 1.0 - age / term
    frac = np.where(r > 1e-12, annuity, linear)
    frac = np.where(np.isfinite(frac), frac, linear)
    return np.where(np.asarray(revolver, dtype=bool), 1.0, np.clip(frac, 0.0, 1.0))
