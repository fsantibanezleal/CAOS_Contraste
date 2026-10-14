"""The Federal Reserve charge-off reader of C10 (CT-1101, CT-1102): the Board's table of net charge-off rates, All Banks, SA.

``https://www.federalreserve.gov/releases/chargeoff/chgallsa.htm`` carries one table, quarterly from 1985:1, with the five loan
types of the case among its columns. The reader parses the page with the standard library, names every column by the
``headers`` attribute of its cells (never by position), keeps a cell that says ``n.a.`` as a missing quarter and refuses a cell
it cannot read. A rate is the table's annualised percentage divided by 100; the annual rate of a year is the mean of its four
quarterly rates and is None, with its reason, when any quarter is missing: a missing quarter is never interpolated (the
``market_series`` family of contract 1, the contract's Missing-data behaviour).
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

#: loan type of the document -> the id of the table column (the ``headers`` token before the row's date id)
COLUMNS: dict[str, str] = {
    "commercial-industrial": "CI",
    "commercial-real-estate": "RECI",
    "residential": "RERES",
    "credit-cards": "CONCC",
    "other-consumer": "CONOTH",
}
#: the column headings the page carries, kept to check that the ids still mean what the case says
HEADINGS: dict[str, str] = {
    "CI": "C&I loans", "RECI": "Commercial", "RERES": "Residential", "CONCC": "Credit cards", "CONOTH": "Other",
}
URL = "https://www.federalreserve.gov/releases/chargeoff/chgallsa.htm"
_NUMBER = re.compile(r"^-?\d+\.\d+$")
_QUARTER = re.compile(r"^(\d{4}):([1-4])$")
_UPDATED = re.compile(r"Last update:\s*([A-Z][a-z]+) (\d{1,2}), (\d{4})")
_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
           "December")


class ReaderError(ValueError):
    """The Board's page is not the table the reader knows, or a cell cannot be read."""


@dataclass(frozen=True)
class Table:
    """The charge-off table: ``series[column][i]`` is the percentage of ``quarters[i]`` (None where the Board says n.a.)."""

    quarters: tuple[str, ...]                         # "1985Q1", ascending, contiguous
    series: dict[str, tuple[float | None, ...]]
    updated: str | None                               # "YYYY-MM-DD" of the page's "Last update", when it states one
    absent: frozenset[tuple[str, str]]                # (quarter, column) cells the Board marks n.a.

    def index(self, quarter: str) -> int:
        return self.quarters.index(quarter)


class _Rows(HTMLParser):
    """Collect, for the first table after the 'All Banks, SA' heading, the heading cells and the data rows."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.h3 = ""
        self.h5 = ""
        self._tag = ""
        self._table = 0           # 0 before the table, 1 inside it, 2 after it
        self._row: list[tuple[str, dict[str, str], str]] = []
        self._cell: list[str] | None = None
        self._attrs: dict[str, str] = {}
        self._cell_tag = ""
        self.rows: list[list[tuple[str, dict[str, str], str]]] = []
        self.headings: dict[str, str] = {}
        self._seen_h5 = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        self._tag = tag
        if tag == "table" and self._table == 0 and "statistics" in a.get("class", "") and self._seen_h5:
            self._table = 1
        elif self._table == 1 and tag in ("th", "td"):
            self._cell, self._attrs, self._cell_tag = [], a, tag
        elif self._table == 1 and tag == "tr":
            self._row = []

    def handle_endtag(self, tag: str) -> None:
        if self._table == 1 and tag in ("th", "td") and self._cell is not None:
            text = re.sub(r"\s+", " ", "".join(self._cell).replace("\xa0", " ")).strip()
            self._row.append((tag, self._attrs, text))
            if tag == "th" and self._attrs.get("id") and not self._attrs["id"].startswith("date"):
                self.headings[self._attrs["id"]] = text
            self._cell = None
        elif self._table == 1 and tag == "tr":
            if any(t == "th" and a.get("id", "").startswith("date") for t, a, _ in self._row):
                self.rows.append(self._row)
            self._row = []
        elif self._table == 1 and tag == "table":
            self._table = 2

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)
        elif self._tag == "h3" and not self._table:
            self.h3 += data
        elif self._tag == "h5" and not self._table:
            self.h5 += data
            self._seen_h5 = True


def read_table(path: str | Path) -> Table:
    """Parse the saved page. Raises ``ReaderError`` for any structure or cell the reader does not know."""
    raw = Path(path).read_bytes().decode("latin-1")
    p = _Rows()
    p.feed(raw)
    if "Charge-Off Rates" not in p.h3 or "All Banks, SA" not in p.h5 or not p.rows:
        raise ReaderError(f"{path}: the page does not hold the 'Charge-Off Rates, All Banks, SA' table")
    for col, word in HEADINGS.items():
        if word not in p.headings.get(col, ""):
            raise ReaderError(f"{path}: column {col} is headed {p.headings.get(col)!r}, not {word!r}")
    cells: dict[str, dict[str, str]] = {}
    for row in p.rows:
        q = next(t for tag, a, t in row if tag == "th" and a.get("id", "").startswith("date"))
        m = _QUARTER.match(q)
        if m is None:
            raise ReaderError(f"{path}: row label {q!r} is not a quarter")
        label = f"{m.group(1)}Q{m.group(2)}"
        if label in cells:
            raise ReaderError(f"{path}: the quarter {label} appears twice")
        cells[label] = {a["headers"].split()[-2]: t for tag, a, t in row if tag == "td" and "headers" in a}
    quarters = sorted(cells)
    first, last = quarters[0], quarters[-1]
    every = [f"{y}Q{k}" for y in range(int(first[:4]), int(last[:4]) + 1) for k in range(1, 5)]
    every = every[every.index(first): every.index(last) + 1]
    series: dict[str, list[float | None]] = {c: [] for c in COLUMNS.values()}
    absent: set[tuple[str, str]] = set()
    for q in every:
        row = cells.get(q)
        for col in COLUMNS.values():
            if row is None:
                series[col].append(None)             # the Board has no row for the quarter: missing, never filled
                absent.add((q, col))
                continue
            text = row.get(col)
            if text is None:
                raise ReaderError(f"{path}: the quarter {q} has no cell for column {col}")
            if text == "n.a.":
                series[col].append(None)
                absent.add((q, col))
            elif _NUMBER.match(text):
                series[col].append(float(text))
            else:
                raise ReaderError(f"{path}: the quarter {q} column {col} holds {text!r}, neither a rate nor n.a.")
    um = _UPDATED.search(re.sub(r"<[^>]+>", " ", raw))
    updated = f"{um.group(3)}-{_MONTHS.index(um.group(1)) + 1:02d}-{int(um.group(2)):02d}" if um else None
    return Table(tuple(every), {c: tuple(v) for c, v in series.items()}, updated, frozenset(absent))


def raw_record(path: str | Path) -> dict[str, object]:
    """Name, size and SHA-256 of the saved page (what the provenance carries)."""
    b = Path(path).read_bytes()
    return {"name": Path(path).name, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}


def window_digest(table: Table, first_year: int, last_year: int) -> str:
    """SHA-256 of the five series over the years the case uses, one ``quarter,column,text`` line per cell.

    The saved page carries a per-request script token, so two fetches of the same data differ in their bytes; this digest is
    of the numbers alone and is the same for both. It changes only if the Board revises the history the case uses."""
    lines = []
    for q in table.quarters:
        if not first_year <= int(q[:4]) <= last_year:
            continue
        for col in sorted(COLUMNS.values()):
            v = table.series[col][table.index(q)]
            lines.append(f"{q},{col},{'n.a.' if v is None else format(v, '.2f')}")
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AnnualRate:
    year: int
    n_quarters: int                    # quarters of the year the table has a rate for
    rate: float | None                 # decimal per year, the mean of the four quarterly rates; None unless n_quarters is 4
    reason: str | None
    missing: tuple[str, ...]           # the quarters of the year the table lacks


def annual_rates(table: Table, loan_type: str, first_year: int, last_year: int) -> list[AnnualRate]:
    """One row per year: the mean of the four quarterly rates (percent divided by 100), or None with the reason."""
    col = COLUMNS[loan_type]
    out: list[AnnualRate] = []
    for year in range(first_year, last_year + 1):
        qs = [f"{year}Q{k}" for k in range(1, 5)]
        if not all(q in table.quarters for q in qs):
            raise ReaderError(f"{loan_type}: the table does not reach every quarter of {year}")
        vals = [table.series[col][table.index(q)] for q in qs]
        missing = tuple(q for q, v in zip(qs, vals, strict=True) if v is None)
        if missing:
            why = (f"the Board's table marks {', '.join(missing)} as n.a. for {HEADINGS[col]}"
                   if all((q, col) in table.absent for q in missing) else f"{', '.join(missing)} missing")
            out.append(AnnualRate(year, 4 - len(missing), None,
                                  f"{why}; the annual rate is null, never interpolated", missing))
            continue
        # the table states hundredths of a percent: add them as integers so that the mean carries no rounding noise
        rate = sum(round(v * 100) for v in vals if v is not None) / 40000.0
        if not 0.0 < rate < 1.0:
            out.append(AnnualRate(year, 4, None, f"the annual rate {rate:.6f} is outside (0, 1); the Vasicek model has no "
                                                 "value there, so the year carries no rate", ()))
            continue
        out.append(AnnualRate(year, 4, rate, None, ()))
    return out
