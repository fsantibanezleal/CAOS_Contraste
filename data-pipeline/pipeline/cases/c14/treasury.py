"""The US Treasury daily par yield curve reader (contract family ``curve``).

The yearly CSV files hold one row per business day with the par yields (percent, bond-equivalent) at the tenors the Treasury
published that day. ``curve_as_of`` returns the last curve published on or before a date, so a quarter end that falls on a
weekend carries the previous business day's curve; it never reads a later one. A tenor the day lacks (the 4 month bill exists
from 2022-10-19, the 2 month from 2018-10-16) is listed, never filled.

R2 of the U10 sizing: this reader is shared with the C11 bake (U8-P1); the integrator moves it to ``pipeline/io/treasury.py``
when both units need it.
"""
from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass
from pathlib import Path

import numpy as np

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
