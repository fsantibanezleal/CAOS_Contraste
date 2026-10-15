"""Synthetic raw files in the real formats of the three public sources, for the tests of a small size (ADR-0074).

Nothing here is a real observation: the French file is derived-only, so its tests read numbers drawn from a seeded generator
in the file's own layout, never a copy of the real returns. The calendars differ between the three files on purpose (a holiday
of one is a trading day of another), and the Treasury file has empty 10-year cells, so the skipped-day rule is exercised.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import numpy as np

FIRST, LAST = np.datetime64("1990-01-01"), np.datetime64("2023-12-31")


def weekdays(first=FIRST, last=LAST) -> np.ndarray:
    d = np.arange(first, last + 1, dtype="datetime64[D]")
    return d[(d.astype("datetime64[D]").view("int64") + 4) % 7 < 5]    # 1970-01-01 was a Thursday


def _holidays(days: np.ndarray, every: int, offset: int) -> np.ndarray:
    keep = np.ones(days.size, dtype=bool)
    keep[offset::every] = False
    return keep


def shocks(n: int, seed: int, scale: float) -> np.ndarray:
    """Heavy-tailed returns with volatility clusters: a slow log-volatility times Student-t(5) draws."""
    rng = np.random.default_rng(seed)
    logv = np.zeros(n)
    for i in range(1, n):
        logv[i] = 0.98 * logv[i - 1] + 0.12 * rng.standard_normal()
    t = rng.standard_t(5, n) * np.sqrt(3.0 / 5.0)
    return scale * np.exp(0.5 * logv) * t


def make_raw(root: Path, seed: int = 7) -> Path:
    days = weekdays()
    fr = days[_holidays(days, 23, 5)]
    ty = days[_holidays(days, 71, 9)]
    eu = weekdays(np.datetime64("2000-01-03"))
    # French: percent, Mkt-RF with a small drift, RF constant
    mk = shocks(fr.size, seed, 0.9) + 0.03
    rf = np.full(fr.size, 0.01)
    lines = ["This file was created by a synthetic generator for the tests; it is not Kenneth French data.", "", ",Mkt-RF,SMB,HML,RF"]
    for d, m, r in zip(fr, mk, rf, strict=True):
        lines.append(f"{str(d).replace('-', '')},{m:8.2f},{0.1:8.2f},{-0.1:8.2f},{r:8.2f}")
    lines += ["", "Copyright 2026 synthetic"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("F-F_Research_Data_Factors_daily.csv", "\n".join(lines) + "\n")
    (root / "raw" / "french").mkdir(parents=True, exist_ok=True)
    (root / "raw" / "french" / "F-F_Research_Data_Factors_daily_CSV.zip").write_bytes(buf.getvalue())
    # Treasury: percent, one file per year, descending dates, a few empty 10-year cells
    y10 = np.clip(4.5 + np.cumsum(shocks(ty.size, seed + 1, 0.04)), 0.3, 12.0)
    (root / "raw" / "treasury-par").mkdir(parents=True, exist_ok=True)
    years = ty.astype("datetime64[Y]").astype(int) + 1970
    for y in range(1990, 2024):
        idx = np.flatnonzero(years == y)[::-1]
        rows = ['Date,"3 Mo","2 Yr","10 Yr","30 Yr"']
        for k in idx:
            d = ty[k]
            cell = "" if k % 197 == 13 else f"{y10[k]:.2f}"
            mm, dd = str(d)[5:7], str(d)[8:10]
            rows.append(f"{mm}/{dd}/{y},{y10[k] - 1.0:.2f},{y10[k] - 0.4:.2f},{cell},{y10[k] + 0.3:.2f}")
        (root / "raw" / "treasury-par" / f"daily-treasury-par-{y}.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    # H.10 euro: dollars per euro from 2000-01-03, "ND" on a few days
    px = 1.05 * np.exp(np.cumsum(shocks(eu.size, seed + 2, 0.005)))
    mon = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    rows = ['<table class="pubtables"><thead><th scope=col>Date</th><th scope=col>Rate</th></thead>']
    for k, d in enumerate(eu):
        s = str(d)
        lab = f"{int(s[8:10])}-{mon[int(s[5:7]) - 1]}-{s[2:4]}"
        cell = "ND" if k % 19 == 11 else f"{px[k]:.4f}"
        rows.append(f'<tr>\n<th id="r1" headers="a1">{lab} </th>\n<td headers="a2 a1 r1">   {cell}   </td>\n</tr>')
    rows.append("</table>")
    (root / "raw" / "h10").mkdir(parents=True, exist_ok=True)
    (root / "raw" / "h10" / "dat00_eu.htm").write_text("<html><body>\n" + "\n".join(rows) + "\n</body></html>", encoding="utf-8")
    return root


def iid_t(n: int, nu: int, seed: int) -> np.ndarray:
    """Unit-variance Student-t draws with known truth: the t quantile scaled by sqrt((nu - 2) / nu)."""
    rng = np.random.default_rng(seed)
    return rng.standard_t(nu, n) * np.sqrt((nu - 2.0) / nu)
