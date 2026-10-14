"""CT-1101, CT-1102: the Federal Reserve reader and the annual rate (on the committed sample of the Board's page)."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest
from conftest import SAMPLE

from pipeline.cases.c10 import documents as docs
from pipeline.cases.c10 import fed

RAW_PAGE = Path("E:/_Datos/contraste/raw/fed-chargeoff/chgallsa.htm")


def test_the_reader_names_columns_by_header_id_and_keeps_missing_quarters_missing(table, raw) -> None:
    assert table.quarters[0] == "1985Q1" and table.quarters[-1] == "2013Q4" and len(table.quarters) == 116
    assert set(table.series) == set(fed.COLUMNS.values())
    i = table.index("1985Q1")
    # the sample's first row, read from the page: C&I 1.28, credit cards 1.90, other consumer 0.51 (percent, annualised)
    assert (table.series["CI"][i], table.series["CONCC"][i], table.series["CONOTH"][i]) == (1.28, 1.90, 0.51)
    # residential and commercial real estate are n.a. from 1985Q1 to 1990Q4, and numbers from 1991Q1
    for col in ("RERES", "RECI"):
        assert all(table.series[col][table.index(f"{y}Q{k}")] is None for y in range(1985, 1991) for k in range(1, 5))
        assert table.series[col][table.index("1991Q1")] is not None
        assert {(q, col) for q in table.quarters if table.series[col][table.index(q)] is None} == {(q, c) for q, c in table.absent if c == col}
    assert table.updated == "2026-08-25"
    assert raw["bytes"] == SAMPLE.stat().st_size and raw["sha256"] == hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
    assert fed.COLUMNS == {"commercial-industrial": "CI", "commercial-real-estate": "RECI", "residential": "RERES",
                           "credit-cards": "CONCC", "other-consumer": "CONOTH"}


@pytest.mark.skipif(not RAW_PAGE.exists(), reason="the saved Board page is on the device data root only")
def test_the_sample_rows_are_the_saved_pages_rows(table) -> None:
    full = fed.read_table(RAW_PAGE)
    for col, values in table.series.items():
        assert values == full.series[col][: len(values)], col
    assert fed.window_digest(table, 1985, 2012) == fed.window_digest(full, 1985, 2012)


def test_the_annual_rate_is_the_mean_of_four_quarters_and_a_partial_year_is_null_with_its_reason(table, tmp_path: Path) -> None:
    rows = fed.annual_rates(table, "commercial-industrial", 1985, 2012)
    assert [r.year for r in rows] == list(range(1985, 2013))
    i = table.index("1985Q1")
    quarters = [table.series["CI"][i + k] / 100.0 for k in range(4)]
    assert rows[0].n_quarters == 4 and rows[0].rate == pytest.approx(sum(quarters) / 4, abs=1e-15) and rows[0].reason is None
    assert all(0.0 < r.rate < 1.0 for r in rows)
    res = fed.annual_rates(table, "residential", 1985, 2012)
    for r in res[:6]:
        assert r.rate is None and r.n_quarters == 0 and len(r.missing) == 4 and "never interpolated" in r.reason
    assert all(r.rate is not None for r in res[6:])
    # the Board's table may also lack a whole row: plant a page without 1990:3 and the year has three quarters and no rate
    text = SAMPLE.read_text(encoding="latin-1")
    row = re.search(r"<tr>\s*<th id=\"date\d+\">1990:3</th>.*?</tr>", text, re.S)
    assert row is not None
    page = tmp_path / "gap.htm"
    page.write_text(text.replace(row.group(0), ""), encoding="latin-1")
    gap = fed.annual_rates(fed.read_table(page), "commercial-industrial", 1985, 2012)
    y90 = next(r for r in gap if r.year == 1990)
    assert y90.rate is None and y90.n_quarters == 3 and y90.missing == ("1990Q3",) and "never interpolated" in y90.reason
    # the document lists one missing-quarter entry per year that lacks a quarter, in the order of the years
    entries = docs.missing_quarters(table, "residential", res)
    assert [e["quarter"][:4] for e in entries] == [str(r.year) for r in res if r.n_quarters < 4] == [str(y) for y in range(1985, 1991)]
    assert all(e["reason"] for e in entries)
