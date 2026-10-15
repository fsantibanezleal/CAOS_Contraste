"""The US Treasury daily par yield curve reader, shared by C11 and C14 (U8 and U10 sizing reservation R2); moved from
``cases/c11/readers.py`` and ``cases/c14/treasury.py``.

The Treasury publishes one CSV per year, ``daily-treasury-par-<year>.csv``: one row per business day, the par yields (percent,
bond-equivalent) at the tenors quoted that day, an empty cell for a tenor the day lacks (the 4 month bill exists from 2022-10-19,
the 2 month from 2018-10-16). Mirror-allowed (17 U.S.C. 105). A year file is parsed in one place (:func:`parse_rows`); the two
views are functions over the parsed rows:

- the **series view** (C11): one tenor as a daily series, :func:`parse_tenor` and :func:`read_tenor`. A day whose cell is empty
  is **missing**: listed, never filled.
- the **curve view** (C14): whole curves, :func:`read_par`, :func:`curve_as_of` (the last curve published on or before a date,
  never a later one, so a weekend quarter end carries the previous business day) and :func:`history_up_to`.

A raw file is described by its URL, size, SHA-256 and retrieval date (:class:`RawFile`); a file that is not in the data root raises
:class:`DeclaredAbsence` naming the URL it is fetched from.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np

TREASURY_DIR = "treasury-par"
_URL = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{y}/all"
        "?type=daily_treasury_yield_curve&field_tdr_date_value={y}&_format=csv")
_FILE = "daily-treasury-par-{y}.csv"
#: a cell the publisher leaves without a value
EMPTY_CELLS = ("", "N/A", "ND")

#: the column labels of the file and their tenors in years (the standard grid; a day may lack some)
TENORS: tuple[tuple[str, float], ...] = (
    ("1 Mo", 1 / 12), ("2 Mo", 2 / 12), ("3 Mo", 3 / 12), ("4 Mo", 4 / 12), ("6 Mo", 6 / 12), ("1 Yr", 1.0), ("2 Yr", 2.0),
    ("3 Yr", 3.0), ("5 Yr", 5.0), ("7 Yr", 7.0), ("10 Yr", 10.0), ("20 Yr", 20.0), ("30 Yr", 30.0),
)
TENOR_YEARS = {label: round(t, 6) for label, t in TENORS}


class DeclaredAbsence(FileNotFoundError):
    """A raw file is not in the data root: the message names the URL it is fetched from."""


def url(year: int) -> str:
    return _URL.format(y=year)


def file_name(year: int) -> str:
    return _FILE.format(y=year)


# ------------------------------------------------------------------------------------------------------------ raw files

@dataclass(frozen=True)
class RawFile:
    name: str
    url: str
    bytes: int
    sha256: str
    retrieved: str

    def to_json(self) -> dict:
        return {"name": self.name, "url": self.url, "bytes": self.bytes, "sha256": self.sha256, "retrieved": self.retrieved}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def describe(path: Path, source_url: str, retrieved_hint: str | None = None) -> RawFile:
    """The provenance of a raw file: size and hash are measured on the bytes, the date is the one the fetch recorded or, for a
    file fetched by another unit, the file's modification date."""
    when = retrieved_hint or dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).date().isoformat()
    return RawFile(path.name, source_url, path.stat().st_size, sha256_of(path), when)


def need(path: Path, source_url: str, fetch_hint: str = "") -> Path:
    """``path`` when it exists, else the declared absence naming the URL (and the command that fetches it, when given)."""
    if not path.exists():
        how = f" ({fetch_hint})" if fetch_hint else ""
        raise DeclaredAbsence(f"{path} is not in the data root; fetch it from {source_url}{how}")
    return path


# ---------------------------------------------------------------------------------------------------------- the parser

def parse_rows(text: str) -> list[tuple[str, dict[str, str]]]:
    """The rows of one year's CSV: ``(ISO date, {column label: cell text})``, in file order.

    The header names the columns (quotes and spaces removed); a blank line is skipped; a row shorter than the header is padded with
    empty cells; the date is the US ``MM/DD/YYYY`` and an invalid one is refused."""
    lines = [r for r in csv.reader(text.splitlines()) if any(c.strip() for c in r)]
    if not lines:
        return []
    head = [c.strip() for c in lines[0]]
    out: list[tuple[str, dict[str, str]]] = []
    for r in lines[1:]:
        cells = [c.strip() for c in r]
        day = dt.datetime.strptime(cells[0], "%m/%d/%Y").date().isoformat()
        out.append((day, {label: (cells[k] if k < len(cells) else "") for k, label in enumerate(head) if k > 0}))
    return out


# ----------------------------------------------------------------------------------------------- the series view (C11)

def parse_tenor(text: str, tenor: str = "10 Yr") -> tuple[list[dt.date], list[float], list[str]]:
    """Dates, the par yield of ``tenor`` (decimals) and the dates whose cell is empty, from one year's CSV; nothing when the
    tenor is not quoted that year (the grid changes over time)."""
    rows = parse_rows(text)
    if not rows or tenor not in rows[0][1]:
        return [], [], []
    dates: list[dt.date] = []
    values: list[float] = []
    missing: list[str] = []
    for day, cells in rows:
        cell = cells[tenor]
        if cell in EMPTY_CELLS:
            missing.append(day)
            continue
        dates.append(dt.date.fromisoformat(day))
        values.append(float(cell) / 100.0)
    return dates, values, missing


def read_tenor(data_root: str | Path, first_year: int = 1990, last_year: int = 2023, tenor: str = "10 Yr", *,
               retrieved: Mapping[str, str | None] | None = None, fetch_hint: str = ""
               ) -> tuple[np.ndarray, np.ndarray, tuple[str, ...], tuple[RawFile, ...]]:
    """One tenor over the yearly files in ``<data root>/raw/treasury-par/``: dates ascending (``datetime64[D]``), the yields
    (decimals), the missing dates (sorted) and the description of every file.

    ``retrieved`` maps a file name to the retrieval date a fetch recorded; a file without one carries its modification date."""
    folder = Path(data_root) / "raw" / TREASURY_DIR
    dates: list[dt.date] = []
    values: list[float] = []
    missing: list[str] = []
    files: list[RawFile] = []
    for y in range(first_year, last_year + 1):
        path = need(folder / file_name(y), url(y), fetch_hint)
        d, v, m = parse_tenor(path.read_text(encoding="utf-8-sig"), tenor)
        dates += d
        values += v
        missing += m
        files.append(describe(path, url(y), (retrieved or {}).get(path.name)))
    stamps = np.array(dates, dtype="datetime64[D]")
    order = np.argsort(stamps, kind="stable")
    return stamps[order], np.array(values, dtype=float)[order], tuple(sorted(missing)), tuple(files)


# ----------------------------------------------------------------------------------------------- the curve view (C14)

@dataclass(frozen=True)
class ParCurve:
    """The par yields (decimals) of one published day; ``observation_date`` ISO."""

    observation_date: str
    par: dict[str, float]            # label -> decimal, only the tenors present

    def tenors(self) -> np.ndarray:
        return np.array([TENOR_YEARS[label] for label, _ in TENORS if label in self.par])

    def yields(self) -> np.ndarray:
        return np.array([self.par[label] for label, _ in TENORS if label in self.par])

    def missing_tenors(self) -> list[float]:
        return [TENOR_YEARS[label] for label, _ in TENORS if label not in self.par]


def read_par(raw_dir: str | Path) -> dict[str, ParCurve]:
    """Every published day of every yearly file in the folder, keyed by ISO date."""
    out: dict[str, ParCurve] = {}
    for f in sorted(Path(raw_dir).glob("daily-treasury-par-*.csv")):
        for day, cells in parse_rows(f.read_text(encoding="utf-8-sig")):
            par = {label: float(cells[label]) / 100.0 for label, _ in TENORS if cells.get(label)}
            if day in out:
                raise ValueError(f"{f}: the date {day} is repeated")
            out[day] = ParCurve(day, par)
    if not out:
        raise FileNotFoundError(f"{raw_dir}: no daily-treasury-par-*.csv file")
    return out


def curve_as_of(curves: dict[str, ParCurve], date: str) -> ParCurve:
    """The last curve published on or before ``date`` (never a later one)."""
    known = [d for d in curves if d <= date]
    if not known:
        raise ValueError(f"no Treasury curve published on or before {date}")
    return curves[max(known)]


def history_up_to(curves: dict[str, ParCurve], date: str) -> list[ParCurve]:
    """Every curve published on or before ``date``, in date order."""
    return [curves[d] for d in sorted(curves) if d <= date]


def quarter_ends(first: str, last: str) -> list[str]:
    """The calendar quarter ends from ``first`` to ``last`` (both quarter ends, ISO), inclusive."""
    y, m = int(first[:4]), int(first[5:7])
    y1, m1 = int(last[:4]), int(last[5:7])
    out = []
    while (y, m) <= (y1, m1):
        nxt = dt.date(y + (m // 12), m % 12 + 1, 1)
        out.append((nxt - dt.timedelta(days=1)).isoformat())
        m += 3
        if m > 12:
            m -= 12
            y += 1
    return out
