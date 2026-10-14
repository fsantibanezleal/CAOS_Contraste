"""The readers of the three public daily series of C11 and their fetch (dossier 08 C.2, C.5, C.8).

- Kenneth French, daily Fama/French factors (``F-F_Research_Data_Factors_daily_CSV.zip``): the US market return is the
  excess return plus the risk-free rate, in percent. **Derived-only** (dossier 08 C.5): the raw file stays in the device
  data root and only model outputs are committed.
- US Treasury daily par yield curve, one CSV per year: the 10-year par yield, in percent. Mirror-allowed (17 U.S.C. 105).
- Federal Reserve H.10, historical rates for the euro (US dollars per euro, from 2000-01-03): "ND" marks a day without
  a rate. Mirror-allowed (the Board's public-domain statement).

A reader returns a :class:`Series` of the observed days only. A day whose row exists and whose value is absent ("ND", an
empty cell, the -99.99 of the French file) is **missing**: it is counted in ``Series.missing`` and never filled
(SDD C11, contract ``contract-family-market_series``). Every raw file is described by its URL, size, SHA-256 and
retrieval date (:class:`RawFile`).

Raw files live in ``<data root>/raw/french/``, ``raw/treasury-par/`` and ``raw/h10/``; a data root inside the repository
is refused by :func:`pipeline.io.fetch.data_root`.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import re
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

USER_AGENT = "Mozilla/5.0 (compatible; Contraste-pipeline/1.0; +https://github.com/fsantibanezleal/CAOS_Contraste)"
FRENCH_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_daily_CSV.zip"
FRENCH_FILE = "F-F_Research_Data_Factors_daily_CSV.zip"
TREASURY_URL = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{y}/all"
                "?type=daily_treasury_yield_curve&field_tdr_date_value={y}&_format=csv")
TREASURY_FILE = "daily-treasury-par-{y}.csv"
H10_URL = "https://www.federalreserve.gov/releases/h10/hist/dat00_eu.htm"
H10_FILE = "dat00_eu.htm"
SIDECAR = "c11-provenance.json"
MISSING_FRENCH = (-99.99, -999.0)
MONTHS = {m: i + 1 for i, m in enumerate(("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"))}

Opener = Callable[[str], bytes]


class DeclaredAbsence(FileNotFoundError):
    """A raw file is not in the data root: the message names the URL it is fetched from."""


@dataclass(frozen=True)
class RawFile:
    name: str
    url: str
    bytes: int
    sha256: str
    retrieved: str

    def to_json(self) -> dict:
        return {"name": self.name, "url": self.url, "bytes": self.bytes, "sha256": self.sha256, "retrieved": self.retrieved}


@dataclass(frozen=True)
class Series:
    """The observed days of one public series: ``dates`` ascending, ``values`` aligned, ``missing`` the dates with a row and no value."""

    series_id: str
    unit: str                      # "return" (simple daily), "rate" (decimal level) or "level"
    dates: np.ndarray              # datetime64[D]
    values: np.ndarray             # float64
    missing: tuple[str, ...] = ()
    files: tuple[RawFile, ...] = field(default=())

    def __len__(self) -> int:
        return int(self.dates.size)

    def contract_rows(self) -> list[dict]:
        return [{"date": str(d), "series_id": self.series_id, "value": float(v), "unit": self.unit}
                for d, v in zip(self.dates, self.values, strict=True)]


# ------------------------------------------------------------------------------------------------------------------- fetch

def http_get(url: str, *, retries: int = 3, timeout: float = 90.0) -> bytes:
    import time

    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (https only)
                return resp.read()
        except OSError as exc:
            last = exc
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"could not fetch {url} after {retries} attempts: {last}")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _sidecar(folder: Path) -> dict:
    p = folder / SIDECAR
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _describe(path: Path, url: str, retrieved_hint: str | None) -> RawFile:
    """The provenance of a raw file: size and hash are measured on the bytes, the date is the one the fetch recorded or, for a
    file fetched by another unit, the file's modification date."""
    when = retrieved_hint or dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).date().isoformat()
    return RawFile(path.name, url, path.stat().st_size, sha256_of(path), when)


def fetch(data_root: str | Path, *, first_year: int = 1990, last_year: int = 2023, opener: Opener = http_get,
          refresh: bool = False, today: str | None = None) -> list[RawFile]:
    """Download what is missing into ``<data root>/raw``: the French zip, the Treasury CSV of each year and the H.10 euro page.

    A file already present is kept (the bake pins its hash, not the URL); ``refresh`` fetches it again. Each file is written
    to a temporary name and renamed, so a stopped fetch never leaves a half file, and one sidecar per folder records URL,
    size, hash and date of what this function fetched."""
    root = Path(data_root) / "raw"
    when = today or dt.date.today().isoformat()
    plan: list[tuple[Path, str]] = [(root / "french" / FRENCH_FILE, FRENCH_URL), (root / "h10" / H10_FILE, H10_URL)]
    plan += [(root / "treasury-par" / TREASURY_FILE.format(y=y), TREASURY_URL.format(y=y)) for y in range(first_year, last_year + 1)]
    out: list[RawFile] = []
    for path, url in plan:
        path.parent.mkdir(parents=True, exist_ok=True)
        if refresh or not path.exists() or path.stat().st_size == 0:
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_bytes(opener(url))
            tmp.replace(path)
            side = _sidecar(path.parent)
            side[path.name] = {"url": url, "retrieved": when}
            (path.parent / SIDECAR).write_text(json.dumps(side, indent=1, sort_keys=True), encoding="utf-8")
        out.append(_describe(path, url, _sidecar(path.parent).get(path.name, {}).get("retrieved")))
    return out


def _need(path: Path, url: str) -> Path:
    if not path.exists():
        raise DeclaredAbsence(f"{path} is not in the data root; fetch it from {url} (python data-pipeline/pipeline/cases/c11/run.py fetch)")
    return path


# ------------------------------------------------------------------------------------------------------------------- French

def parse_french(text: str) -> tuple[list[dt.date], list[float], list[str]]:
    """Dates, market returns (decimals) and missing dates from the text of the French daily factors file.

    The market return is ``Mkt-RF + RF`` (percent). Only lines that start with an eight-digit date are data."""
    dates: list[dt.date] = []
    values: list[float] = []
    missing: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^\s*(\d{8})\s*,(.*)$", line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).split(",")]
        d = dt.datetime.strptime(m.group(1), "%Y%m%d").date()
        try:
            mkt_rf, rf = float(cells[0]), float(cells[3])
        except (ValueError, IndexError):
            missing.append(d.isoformat())
            continue
        if mkt_rf in MISSING_FRENCH or rf in MISSING_FRENCH:
            missing.append(d.isoformat())
            continue
        dates.append(d)
        values.append((mkt_rf + rf) / 100.0)
    return dates, values, missing


def read_french(data_root: str | Path) -> Series:
    path = _need(Path(data_root) / "raw" / "french" / FRENCH_FILE, FRENCH_URL)
    with zipfile.ZipFile(path) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        text = z.read(name).decode("latin-1")
    d, v, miss = parse_french(text)
    return Series("french-daily", "return", np.array(d, dtype="datetime64[D]"), np.array(v, dtype=float), tuple(miss),
                  (_describe(path, FRENCH_URL, _sidecar(path.parent).get(path.name, {}).get("retrieved")),))


# ------------------------------------------------------------------------------------------------------------------- Treasury

def parse_treasury(text: str, tenor: str = "10 Yr") -> tuple[list[dt.date], list[float], list[str]]:
    """Dates, the par yield of ``tenor`` (decimals) and the dates whose cell is empty, from one year's CSV."""
    rows = [r for r in io.StringIO(text).read().splitlines() if r.strip()]
    head = [c.strip().strip('"') for c in re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', rows[0])]
    if tenor not in head:
        return [], [], []   # the tenor is not quoted that year (the grid changes over time)
    k = head.index(tenor)
    dates: list[dt.date] = []
    values: list[float] = []
    missing: list[str] = []
    for r in rows[1:]:
        cells = [c.strip().strip('"') for c in re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', r)]
        d = dt.datetime.strptime(cells[0], "%m/%d/%Y").date()
        cell = cells[k] if k < len(cells) else ""
        if cell in ("", "N/A", "ND"):
            missing.append(d.isoformat())
            continue
        dates.append(d)
        values.append(float(cell) / 100.0)
    return dates, values, missing


def read_treasury(data_root: str | Path, first_year: int = 1990, last_year: int = 2023, tenor: str = "10 Yr") -> Series:
    folder = Path(data_root) / "raw" / "treasury-par"
    side = _sidecar(folder)
    dates: list[dt.date] = []
    values: list[float] = []
    missing: list[str] = []
    files: list[RawFile] = []
    for y in range(first_year, last_year + 1):
        path = _need(folder / TREASURY_FILE.format(y=y), TREASURY_URL.format(y=y))
        d, v, m = parse_treasury(path.read_text(encoding="utf-8-sig"), tenor)
        dates += d
        values += v
        missing += m
        files.append(_describe(path, TREASURY_URL.format(y=y), side.get(path.name, {}).get("retrieved")))
    order = np.argsort(np.array(dates, dtype="datetime64[D]"), kind="stable")
    return Series("treasury-par", "rate", np.array(dates, dtype="datetime64[D]")[order], np.array(values, dtype=float)[order],
                  tuple(sorted(missing)), tuple(files))


# ------------------------------------------------------------------------------------------------------------------- H.10

def parse_h10(html: str) -> tuple[list[dt.date], list[float], list[str]]:
    """Dates, rates and the dates marked "ND", from the table of an H.10 historical page (two-digit years, 2000 onward)."""
    pairs = re.findall(r'<th[^>]*headers="a1"[^>]*>\s*([^<]+?)\s*</th>\s*<td[^>]*>\s*([^<]*?)\s*</td>', html, flags=re.S)
    dates: list[dt.date] = []
    values: list[float] = []
    missing: list[str] = []
    for lab, cell in pairs:
        m = re.match(r"^(\d{1,2})-([A-Z]{3})-(\d{2})$", lab.strip())
        if not m:
            continue
        d = dt.date(2000 + int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
        if cell in ("", "ND", "NA"):
            missing.append(d.isoformat())
            continue
        dates.append(d)
        values.append(float(cell))
    return dates, values, missing


def read_h10(data_root: str | Path) -> Series:
    path = _need(Path(data_root) / "raw" / "h10" / H10_FILE, H10_URL)
    d, v, m = parse_h10(path.read_text(encoding="utf-8"))
    return Series("h10-fx", "level", np.array(d, dtype="datetime64[D]"), np.array(v, dtype=float), tuple(m),
                  (_describe(path, H10_URL, _sidecar(path.parent).get(path.name, {}).get("retrieved")),))
