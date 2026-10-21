"""The reader of the EBA/ESRB 2025 macro-financial scenario workbook (``openpyxl``), the United States rows.

The workbook the EBA page links (updated 26 February 2025, after the ESRB corrigendum) holds, per country, the historical value of
2024 and the baseline and adverse values of 2025, 2026 and 2027 as annual averages. C18 keeps the adverse path of the United States
rows (the satellites are US-calibrated, decision Q6) for real GDP growth, the unemployment rate and the long-term interest rate. The
reader locates each table by its title cell and each country by its code, never by a position, and refuses a layout it does not know.
Whether the annual values are year-end levels is UNVERIFIED in the research record (F6); the bake treats them as year-end levels
(``stress.paths.annual_to_quarterly``) and says so.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import openpyxl

from . import fetch

COUNTRY = "US"
#: sheet -> (title cell text, regressor, variable name as the EBA prints it, unit)
SHEETS = {
    "GDP": ("Real GDP", "real_gdp_growth", "Real GDP growth", "percent"),
    "Unemployment": ("Unemployment rate", "unemployment_rate", "Unemployment rate", "percent"),
    "Long-term rates": ("Long-term interest rates", "treasury_10y", "Long-term interest rate", "percent"),
}
YEARS = (2025, 2026, 2027)


class EbaReaderError(ValueError):
    """The workbook is not the layout the reader knows."""


@dataclass(frozen=True)
class EbaPath:
    sheet: str
    regressor: str
    variable: str
    unit: str
    jump_off_year: int
    jump_off_value: float                 # the 2024 value (growth and unemployment: the historical value; rates: the December 2024 average)
    baseline: tuple[float, ...]           # 2025, 2026, 2027
    adverse: tuple[float, ...]            # 2025, 2026, 2027


def _find_country(rows: list[tuple], code: str, sheet: str) -> tuple:
    hits = [r for r in rows if len(r) > 2 and r[2] == code]
    if len(hits) != 1:
        raise EbaReaderError(f"{sheet}: the country code {code!r} appears {len(hits)} times, expected once")
    return hits[0]


def _floats(vals: tuple, sheet: str, what: str) -> tuple[float, ...]:
    out = []
    for v in vals:
        if not isinstance(v, (int, float)):
            raise EbaReaderError(f"{sheet}: {what} holds {v!r}, not a number")
        out.append(float(v))
    return tuple(out)


def read_workbook(path: str | Path, country: str = COUNTRY) -> dict[str, EbaPath]:
    """The three paths of ``country`` keyed by regressor. Raises ``EbaReaderError`` for any title, header or cell it does not know."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{p.name} is not in {p.parent}; fetch it from {fetch.EBA_URL} (the link on {fetch.EBA_PAGE})")
    wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
    out: dict[str, EbaPath] = {}
    try:
        for sheet, (title, regressor, variable, unit) in SHEETS.items():
            if sheet not in wb.sheetnames:
                raise EbaReaderError(f"the workbook has no sheet {sheet!r}")
            rows = list(wb[sheet].iter_rows(values_only=True))
            if not any(len(r) > 1 and r[1] == title for r in rows[:4]):
                raise EbaReaderError(f"{sheet}: the title {title!r} is not in the first rows")
            head = next((r for r in rows[:8] if any(isinstance(c, int) and c == 2024 for c in r)), None)
            if head is None:
                raise EbaReaderError(f"{sheet}: no header row with the year 2024")
            years = [c for c in head if isinstance(c, int)]
            row = _find_country(rows, country, sheet)
            if sheet == "Long-term rates":
                # columns: start average 2024, start latest 2024, baseline 2025-27, adverse 2025-27
                if years != [2024, 2024, 2025, 2026, 2027, 2025, 2026, 2027]:
                    raise EbaReaderError(f"{sheet}: the years {years} are not the known header")
                vals = _floats(row[3:11], sheet, "the row of " + country)
                jump, base, adv = vals[1], vals[2:5], vals[5:8]
            else:
                if years != [2024, 2025, 2026, 2027, 2025, 2026, 2027]:
                    raise EbaReaderError(f"{sheet}: the years {years} are not the known header")
                vals = _floats(row[3:10], sheet, "the row of " + country)
                jump, base, adv = vals[0], vals[1:4], vals[4:7]
            out[regressor] = EbaPath(sheet, regressor, variable, unit, 2024, jump, tuple(base), tuple(adv))
    finally:
        wb.close()
    return out
