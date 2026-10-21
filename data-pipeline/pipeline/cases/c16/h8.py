"""The Federal Reserve H.8 release reader (contract family ``market_series`` through ``pipeline.io.contract``).

A release page (``https://www.federalreserve.gov/releases/h8/<YYYYMMDD>/``) holds eleven tables; the ones C16 reads are Table 6
(large domestically chartered commercial banks) and Table 8 (small ones), seasonally adjusted, billions of dollars: each has the
months of the last year and, under "Week ending", the four latest Wednesdays. The parser is the standard library's
``html.parser`` (no new dependency, U11 sizing R5). It reads what the page says and refuses what it does not: a table that is not
on the page, a title or an adjustment or a unit that is not the expected one, a line that is not in the table, a cell that is not a
number (a gap is never filled).
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from html.parser import HTMLParser

#: the table numbers C16 reads and the words their title must hold (Table 2 is all commercial banks, 4 domestically chartered)
EXPECTED_TITLES = {6: "Large Domestically Chartered", 8: "Small Domestically Chartered"}
MONTHS = {m: i for i, m in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}
_MONTH_NAMES = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6, "July": 7, "August": 8, "September": 9,
                "October": 10, "November": 11, "December": 12}


class H8Error(ValueError):
    """The page is not what the reader expects, or a value it was asked for is not on it."""


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _label(text: str) -> str:
    """A line label without its footnote marks (``Securities in bank credit  2`` is ``Securities in bank credit``)."""
    return re.sub(r"(\s+\d+(\s*,\s*\d+)*)+$", "", _clean(text))


def _number(text: str) -> float | None:
    t = text.strip().replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None


@dataclass(frozen=True)
class Table:
    """One table of a release: its number, title, unit sentence, the adjustment it states, the periods of its columns and the lines."""

    number: int
    title: str
    unit: str
    adjustment: str
    periods: tuple[str, ...]
    lines: dict[str, tuple[float | None, ...]]

    def value(self, line: str, period: str) -> float:
        if line not in self.lines:
            raise H8Error(f"Table {self.number}: the line {line!r} is not on the page (lines: {sorted(self.lines)[:6]}...)")
        if period not in self.periods:
            raise H8Error(f"Table {self.number}: the period {period} is not a column of the page (columns: {list(self.periods)})")
        v = self.lines[line][self.periods.index(period)]
        if v is None:
            raise H8Error(f"Table {self.number}: the line {line!r} has no value for {period} on the page")
        return v


@dataclass(frozen=True)
class Release:
    release_date: str
    title: str
    tables: dict[int, Table]

    def table(self, number: int) -> Table:
        if number not in self.tables:
            raise H8Error(f"Table {number} is not on the page of the release of {self.release_date} (tables: {sorted(self.tables)})")
        t = self.tables[number]
        want = EXPECTED_TITLES.get(number)
        if want is not None and want not in t.title:
            raise H8Error(f"Table {number}: the title {t.title!r} is not the expected one (it must hold {want!r})")
        return t


class _Page(HTMLParser):
    """Collects the page title, the h4 headings, the unit spans and, per table, its rows of cell texts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.tables: list[dict] = []
        self._in_title = False
        self._in_h4 = False
        self._h4 = ""
        self._in_unit = False
        self._unit = ""
        self._table: dict | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._in_thead = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "h4":
            self._in_h4, self._h4 = True, ""
        elif tag == "span" and "tableunit" in (a.get("class") or ""):
            self._in_unit, self._unit = True, ""
        elif tag == "table":
            self._table = {"heading": _clean(self._h4), "attr_title": _clean(a.get("title") or ""), "unit": _clean(self._unit),
                           "head": [], "body": []}
            self._unit = ""
        elif tag == "thead":
            self._in_thead = True
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "h4":
            self._in_h4 = False
        elif tag == "span":
            self._in_unit = False
        elif tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append(_clean("".join(self._cell)))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            (self._table["head"] if self._in_thead else self._table["body"]).append(self._row)
            self._row = None
        elif tag == "thead":
            self._in_thead = False
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_h4:
            self._h4 += data
        if self._in_unit:
            self._unit += data
        if self._cell is not None:
            self._cell.append(data + " ")


def week_dates(labels: list[str], release_date: str) -> list[str]:
    """The ISO dates of the week-ending labels (``Feb 15``) of a release: the year is the release's, or the year before for a
    label later in the year than the release date (a January release lists December weeks)."""
    rel = dt.date.fromisoformat(release_date)
    out = []
    for lab in labels:
        m = re.fullmatch(r"([A-Z][a-z]{2})\s+(\d{1,2})", _clean(lab))
        if m is None or m.group(1) not in MONTHS:
            raise H8Error(f"week label {lab!r} is not 'Mon DD'")
        d = dt.date(rel.year, MONTHS[m.group(1)], int(m.group(2)))
        out.append((d if d <= rel else dt.date(rel.year - 1, d.month, d.day)).isoformat())
    return out


def _page_date(title: str) -> str | None:
    m = re.search(r"H\.8\s*-\s*([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})", _clean(title))
    if m is None or m.group(1) not in _MONTH_NAMES:
        return None
    return dt.date(int(m.group(3)), _MONTH_NAMES[m.group(1)], int(m.group(2))).isoformat()


def parse_release(text: str, release_date: str) -> Release:
    """Every table of a release page that has the layout of the levels tables (a header with the months and the week-ending
    columns, then numbered lines). Refuses a page with no table and a page that is the release of another date."""
    page = _Page()
    page.feed(text)
    page.close()
    said = _page_date(page.title)
    if said is not None and said != release_date:
        raise H8Error(f"the page is the release of {said}, not {release_date}")
    tables: dict[int, Table] = {}
    for t in page.tables:
        m = re.match(r"Table (\d+)\.", t["attr_title"] or t["heading"])
        if m is None or len(t["head"]) < 2:
            continue
        number = int(m.group(1))
        head1, head2 = t["head"][0], t["head"][1]
        months = [c for c in head1 if re.fullmatch(r"\d{4} [A-Z][a-z]{2}", c)]
        if "Week ending" not in head1 or not months or not head2:
            continue
        periods = [f"{c[:4]}-{MONTHS[c[5:]]:02d}" for c in months] + week_dates(head2, release_date)
        lines: dict[str, tuple[float | None, ...]] = {}
        for row in t["body"]:
            if len(row) < 3 or not row[0].isdigit():
                continue
            vals = tuple(_number(c) for c in row[2:])
            if len(vals) != len(periods):
                raise H8Error(f"Table {number}: the line {row[1]!r} has {len(vals)} values for {len(periods)} columns")
            lines.setdefault(_label(row[1]), vals)
        unit = t["unit"]
        adj = ("not-seasonally-adjusted" if re.search(r"not seasonally adjusted", unit, re.I)
               else "seasonally-adjusted" if re.search(r"seasonally adjusted", unit, re.I) else "unstated")
        tables[number] = Table(number, re.sub(r"^Table \d+\.\s*", "", t["attr_title"] or t["heading"]), unit, adj, tuple(periods), lines)
    if not tables:
        raise H8Error(f"the page of the release of {release_date} has no table of levels with a week-ending header")
    return Release(release_date, _clean(page.title), tables)


def weekly_series(release: Release, number: int, line: str) -> list[tuple[str, float]]:
    """The weekly values (Wednesday ISO date, billions of dollars, seasonally adjusted) of a line of a table. Refuses a table or
    line that is not on the page, a title, adjustment or unit that is not the expected one, and a week without a number."""
    t = release.table(number)
    if t.adjustment != "seasonally-adjusted":
        raise H8Error(f"Table {number}: expected seasonally adjusted data, the page says {t.unit!r}")
    if "billions of dollars" not in t.unit:
        raise H8Error(f"Table {number}: expected billions of dollars, the page says {t.unit!r}")
    weeks = [p for p in t.periods if len(p) == 10]
    return [(w, t.value(line, w)) for w in weeks]
