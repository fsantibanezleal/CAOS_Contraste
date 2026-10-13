"""Readers of C06 (CT-501 to CT-503): the SBA 7(a) FOIA loan file, the Federal Reserve scenario and history tables, and
the Freddie Mac slot.

Shared by the cases that read these sources (C03, C06, C08; U6 sizing reservation R1); moved from cases/c06/readers.py.

A reader maps the publisher's layout to named columns and does nothing else: no filtering, no recoding, no imputation
(those are ``panel.prepare``, which counts every exclusion). A missing input stops the bake with the URL the file comes
from, never a made-up path. The Freddie Mac slot raises a declared absence that the bake records.

Sources: dossier 08 (CAOS_MANAGE ``wip/contraste/08-data-and-scenario-sources-2026-10-04.md``) A.6 for the SBA files and
fields, D.1 for the Federal Reserve tables.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

SBA_FOLDER = "sba-foia"
FED_FOLDER = "fed-scenarios"
SBA_BASE = "https://data.sba.gov/sites/default/files/uploaded_resources/"
FED_BASE = "https://www.federalreserve.gov/supervisionreg/files/"

#: the four 7(a) files of the quarterly FOIA release (dossier 08 A.6); the 504 files are not read
SBA_FILES = (
    "FOIA_7a_FY1991_FY1999_asof_260630.csv",
    "FOIA_7a_FY2000_FY2009_asof_260630.csv",
    "FOIA_7a_FY2010_FY2019_asof_260630.csv",
    "FOIA_7a_FY2020_Present_asof_260630.csv",
)
SBA_DICTIONARY = "7a_504_foia_data_dictionary.xlsx"
SBA_URLS = {name: SBA_BASE + name for name in (*SBA_FILES, SBA_DICTIONARY)}

FED_HISTORY = "2026_Final_Historic_Domestic.csv"
FED_BASELINE = "2026_Final_Supervisory_Baseline_Domestic.csv"
FED_SEVERE = "2026_Final_Supervisory_Severely_Adverse_Domestic.csv"
FED_FILES = (FED_HISTORY, FED_BASELINE, FED_SEVERE)
FED_URLS = {name: FED_BASE + name for name in FED_FILES}

#: the columns the bake reads from the SBA files; the borrower's name, address and identifiers are never read
SBA_COLUMNS = (
    "AsOfDate", "GrossApproval", "SBAGuaranteedApproval", "ApprovalDate", "InitialInterestRate", "TermInMonths",
    "NaicsCode", "LoanStatus", "PaidInFullDate", "ChargeOffDate", "GrossChargeOffAmount", "RevolverStatus",
)
#: the Federal Reserve columns the bake reads (the Board's own scenario variables; third-party index levels are not read)
FED_COLUMNS = ("Scenario Name", "Date", "Real GDP growth", "Unemployment rate", "Prime rate")
STATUS_CODES = ("P I F", "CHGOFF", "EXEMPT", "CANCLD", "COMMIT")

FREDDIE_REASON = "Freddie Mac: the owner's account is missing; the SBA twin is published"


class SourceUnavailable(RuntimeError):
    """An input file is not in the data root; the message names the URL it is fetched from."""


class DeclaredAbsence(RuntimeError):
    """An input the case declares and the owner has not yet provided; the bake records it and runs on the twin."""


def _raw_dir(data_root: str | Path, folder: str) -> Path:
    return Path(data_root) / "raw" / folder


def _need(path: Path, url: str) -> Path:
    if not path.exists():
        raise SourceUnavailable(f"{path.name} is not in {path.parent}; fetch it from {url} (data-pipeline/fetch.py)")
    return path


def sba_files(data_root: str | Path) -> list[Path]:
    """The SBA 7(a) files present, in name order. Every file of ``SBA_FILES`` is required, unless the folder holds a
    sample (``FOIA_7a_sample*.csv``, the committed test sample)."""
    folder = _raw_dir(data_root, SBA_FOLDER)
    sample = sorted(folder.glob("FOIA_7a_sample*.csv"))
    if sample:
        return sample
    return [_need(folder / name, SBA_URLS[name]) for name in SBA_FILES]


def read_sba(data_root: str | Path) -> pd.DataFrame:
    """One row per loan of the 7(a) files, as the publisher wrote it, with typed columns and snake_case names."""
    frames = []
    for path in sba_files(data_root):
        head = pd.read_csv(path, nrows=0)
        missing = [c for c in SBA_COLUMNS if c not in head.columns]
        if missing:
            raise ValueError(f"{path.name}: the layout changed, missing columns {missing}")
        frames.append(pd.read_csv(path, usecols=list(SBA_COLUMNS), dtype=str, keep_default_na=True))
    raw = pd.concat(frames, ignore_index=True)
    out = pd.DataFrame({
        "asof_date": pd.to_datetime(raw["AsOfDate"], errors="coerce"),
        "approval_date": pd.to_datetime(raw["ApprovalDate"], errors="coerce"),
        "gross_approval": pd.to_numeric(raw["GrossApproval"], errors="coerce"),
        "guaranteed_approval": pd.to_numeric(raw["SBAGuaranteedApproval"], errors="coerce"),
        "interest_rate_pct": pd.to_numeric(raw["InitialInterestRate"], errors="coerce"),
        "term_months": pd.to_numeric(raw["TermInMonths"], errors="coerce"),
        "naics": raw["NaicsCode"].astype("string"),
        "status": raw["LoanStatus"].astype("string").str.strip(),
        "paid_date": pd.to_datetime(raw["PaidInFullDate"], errors="coerce"),
        "chargeoff_date": pd.to_datetime(raw["ChargeOffDate"], errors="coerce"),
        "chargeoff_amount": pd.to_numeric(raw["GrossChargeOffAmount"], errors="coerce"),
        "revolver": raw["RevolverStatus"].astype("string").str.strip().eq("Y"),
    })
    unknown = sorted(set(out["status"].dropna()) - set(STATUS_CODES))
    if unknown:
        raise ValueError(f"LoanStatus codes outside the data dictionary: {unknown}")
    return out


@dataclass(frozen=True)
class FedTables:
    """The Federal Reserve 2026 tables: the quarterly history (actual) and the two supervisory scenarios (13 quarters)."""

    history: pd.DataFrame
    scenarios: Mapping[str, pd.DataFrame]
    files: tuple[str, ...]


def _quarter_end(label: str) -> pd.Timestamp:
    year, q = label.strip().split(" Q")
    return pd.Timestamp(year=int(year), month=3 * int(q), day=1) + pd.offsets.MonthEnd(0)


def _read_fed_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=lambda c: c in FED_COLUMNS)
    missing = [c for c in FED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: the layout changed, missing columns {missing}")
    df["date"] = [_quarter_end(s) for s in df["Date"]]
    df = df.rename(columns={"Scenario Name": "scenario", "Real GDP growth": "real_gdp_growth",
                            "Unemployment rate": "unemployment_rate", "Prime rate": "prime_rate"})
    return df[["scenario", "date", "real_gdp_growth", "unemployment_rate", "prime_rate"]].reset_index(drop=True)


def read_fed(data_root: str | Path) -> FedTables:
    """The history and the two scenarios, with the quarter-end date of each row. A file that is absent stops the bake
    with its URL."""
    folder = _raw_dir(data_root, FED_FOLDER)
    paths = {name: _need(folder / name, FED_URLS[name]) for name in FED_FILES}
    history = _read_fed_csv(paths[FED_HISTORY])
    baseline = _read_fed_csv(paths[FED_BASELINE])
    severe = _read_fed_csv(paths[FED_SEVERE])
    if len(baseline) != 13 or len(severe) != 13:
        raise ValueError("a Federal Reserve scenario table holds 13 quarters (dossier 08 D.1)")
    return FedTables(history=history, scenarios={"baseline": baseline, "severely-adverse": severe}, files=FED_FILES)


def read_freddie(data_root: str | Path) -> Any:
    """The Freddie Mac Single-Family Loan-Level Dataset slot (source ``freddie-mac-sflld``, derived-only, registration
    at Freddie Mac's Clarity Data Intelligence). The owner's account is missing (owner prerequisite 4), so the slot
    raises a declared absence; when the account exists this reader gets its body and the variants gain a mortgage
    source."""
    raise DeclaredAbsence(FREDDIE_REASON)


def data_files(data_root: str | Path) -> list[tuple[str, str, Path]]:
    """``(source id, file name, path)`` of every file the bake reads, for the lineage."""
    out = [("sba-foia", p.name, p) for p in sba_files(data_root)]
    folder = _raw_dir(data_root, FED_FOLDER)
    out += [("fed-stress-tests", n, _need(folder / n, FED_URLS[n])) for n in FED_FILES]
    return out
