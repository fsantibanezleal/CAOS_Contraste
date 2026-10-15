"""FROZEN legacy copies of the two Treasury readers as they were before they moved to ``pipeline.io.treasury`` (commit a55aa1d:
``cases/c11/readers.py`` ``parse_treasury``/``read_treasury`` and ``cases/c14/treasury.py``). They exist only so the equivalence
test can compare the shared reader with the code it replaced, exactly. Never import this module from the pipeline.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

TREASURY_URL = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{y}/all"
                "?type=daily_treasury_yield_curve&field_tdr_date_value={y}&_format=csv")
TREASURY_FILE = "daily-treasury-par-{y}.csv"
SIDECAR = "c11-provenance.json"


class DeclaredAbsence(FileNotFoundError):
    pass


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _sidecar(folder):
    p = folder / SIDECAR
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _describe(path, url, retrieved_hint):
    when = retrieved_hint or dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).date().isoformat()
    return {"name": path.name, "url": url, "bytes": path.stat().st_size, "sha256": sha256_of(path), "retrieved": when}


def _need(path, url):
    if not path.exists():
        raise DeclaredAbsence(f"{path} is not in the data root; fetch it from {url} (python data-pipeline/pipeline/cases/c11/run.py fetch)")
    return path


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


def read_treasury(data_root, first_year=1990, last_year=2023, tenor="10 Yr"):
    folder = Path(data_root) / "raw" / "treasury-par"
    side = _sidecar(folder)
    dates: list[dt.date] = []
    values: list[float] = []
    missing: list[str] = []
    files = []
    for y in range(first_year, last_year + 1):
        path = _need(folder / TREASURY_FILE.format(y=y), TREASURY_URL.format(y=y))
        d, v, m = parse_treasury(path.read_text(encoding="utf-8-sig"), tenor)
        dates += d
        values += v
        missing += m
        files.append(_describe(path, TREASURY_URL.format(y=y), side.get(path.name, {}).get("retrieved")))
    order = np.argsort(np.array(dates, dtype="datetime64[D]"), kind="stable")
    return (np.array(dates, dtype="datetime64[D]")[order], np.array(values, dtype=float)[order], tuple(sorted(missing)), tuple(files))


#: the column labels of the file and their tenors in years (the standard grid; a day may lack some)
TENORS: tuple[tuple[str, float], ...] = (
    ("1 Mo", 1 / 12), ("2 Mo", 2 / 12), ("3 Mo", 3 / 12), ("4 Mo", 4 / 12), ("6 Mo", 6 / 12), ("1 Yr", 1.0), ("2 Yr", 2.0),
    ("3 Yr", 3.0), ("5 Yr", 5.0), ("7 Yr", 7.0), ("10 Yr", 10.0), ("20 Yr", 20.0), ("30 Yr", 30.0),
)
TENOR_YEARS = {label: round(t, 6) for label, t in TENORS}


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


def _iso(us: str) -> str:
    m, d, y = us.split("/")
    return f"{y}-{int(m):02d}-{int(d):02d}"


def read_par(raw_dir: str | Path) -> dict[str, ParCurve]:
    """Every published day of every yearly file in the folder, keyed by ISO date."""
    out: dict[str, ParCurve] = {}
    for f in sorted(Path(raw_dir).glob("daily-treasury-par-*.csv")):
        with open(f, newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                par = {}
                for label, _ in TENORS:
                    v = (row.get(label) or "").strip()
                    if v:
                        par[label] = float(v) / 100.0
                day = _iso(row["Date"])
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
