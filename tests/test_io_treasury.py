"""The shared US Treasury par curve reader (``pipeline.io.treasury``) used by C11 (one tenor as a daily series) and C14 (whole
curves on valuation dates): the parser on the committed samples, the two views, their edge cases, and an exact equivalence with the
two readers it replaced (``legacy_treasury.py``, frozen) on every raw year file when the device data root is present."""
from __future__ import annotations

import datetime as dt
import os
import shutil
from pathlib import Path

import legacy_treasury as old
import numpy as np
import pytest

from pipeline.io import treasury as tr

ROOT = Path(__file__).resolve().parents[1]
C11_SAMPLE = ROOT / "tests" / "c11" / "data" / "treasury-par-1995-excerpt.csv"
C14_SAMPLES = ROOT / "tests" / "c14" / "data" / "treasury-sample"
VALUATION_DATES = ("2021-12-31", "2022-06-30", "2022-12-31")


def _raw_root() -> Path | None:
    for cand in (os.environ.get("CONTRASTE_DATA"), "E:/_Datos/contraste"):
        if cand and (Path(cand) / "raw" / "treasury-par" / "daily-treasury-par-1990.csv").exists():
            return Path(cand)
    return None


RAW = _raw_root()
requires_raw = pytest.mark.skipif(RAW is None, reason="the device data root with raw/treasury-par/ (1990 to 2023) is not present")


# ------------------------------------------------------------------------------------------------------------ the parser

def test_file_name_and_url_follow_the_publisher_pattern() -> None:
    assert tr.file_name(1995) == "daily-treasury-par-1995.csv"
    assert tr.url(1995) == old.TREASURY_URL.format(y=1995) and "daily-treasury-rates.csv/1995/all" in tr.url(1995)


def test_parse_rows_reads_the_header_the_us_dates_and_the_empty_cells() -> None:
    rows = tr.parse_rows(C11_SAMPLE.read_text(encoding="utf-8"))
    assert len(rows) == 30 and rows[0][0] == "1995-12-29" and rows[0][1]["10 Yr"] == "5.58"
    # a blank line is skipped and a short row is padded with empty cells
    assert tr.parse_rows('Date,"3 Mo","10 Yr"\n\n01/02/1990,7.83,\n01/03/1990,7.9\n') == [
        ("1990-01-02", {"3 Mo": "7.83", "10 Yr": ""}), ("1990-01-03", {"3 Mo": "7.9", "10 Yr": ""})]
    assert tr.parse_rows("") == []


def test_parse_rows_refuses_an_invalid_date() -> None:
    with pytest.raises(ValueError):
        tr.parse_rows('Date,"3 Mo"\n13/45/1990,7.83\n')


# ------------------------------------------------------------------------------------------------------- the series view

def test_series_view_reads_the_ten_year_par_yield_in_decimals() -> None:
    d, v, missing = tr.parse_tenor(C11_SAMPLE.read_text(encoding="utf-8"))
    assert len(d) == 30 and not missing
    assert d[0] == dt.date(1995, 12, 29) and abs(v[0] - 0.0558) < 1e-12


def test_series_view_lists_an_empty_cell_as_missing_and_never_fills_it() -> None:
    d, v, missing = tr.parse_tenor('Date,"3 Mo","10 Yr"\n01/04/1990,7.83,\n01/03/1990,7.9,N/A\n01/02/1990,7.8,ND\n01/05/1990,7.7,8.1\n')
    assert d == [dt.date(1990, 1, 5)] and v == [0.081]
    assert missing == ["1990-01-04", "1990-01-03", "1990-01-02"]


def test_series_view_returns_nothing_for_a_tenor_the_year_does_not_quote() -> None:
    assert tr.parse_tenor('Date,"3 Mo"\n01/02/1990,7.83\n', "10 Yr") == ([], [], [])


def test_read_tenor_orders_by_date_and_describes_every_file(tmp_path: Path) -> None:
    folder = tmp_path / "raw" / "treasury-par"
    folder.mkdir(parents=True)
    (folder / tr.file_name(1990)).write_text('Date,"10 Yr"\n01/03/1990,8.00\n01/02/1990,\n', encoding="utf-8")
    (folder / tr.file_name(1991)).write_text('Date,"10 Yr"\n01/03/1991,7.00\n', encoding="utf-8-sig")
    dates, values, missing, files = tr.read_tenor(tmp_path, 1990, 1991, "10 Yr", retrieved={tr.file_name(1990): "2026-10-14"})
    assert [str(x) for x in dates] == ["1990-01-03", "1991-01-03"] and values.tolist() == [0.08, 0.07] and missing == ("1990-01-02",)
    assert [f.name for f in files] == [tr.file_name(1990), tr.file_name(1991)]
    assert files[0].retrieved == "2026-10-14" and files[0].url == tr.url(1990) and files[0].bytes == (folder / files[0].name).stat().st_size
    assert files[0].sha256 == tr.sha256_of(folder / files[0].name) and len(files[0].sha256) == 64
    assert set(files[0].to_json()) == {"name", "url", "bytes", "sha256", "retrieved"}


def test_a_missing_raw_file_raises_the_declared_absence_with_its_url(tmp_path: Path) -> None:
    with pytest.raises(tr.DeclaredAbsence) as e:
        tr.read_tenor(tmp_path, 1995, 1995, "10 Yr")
    assert "daily-treasury-rates.csv/1995" in str(e.value) and isinstance(e.value, FileNotFoundError)


# --------------------------------------------------------------------------------------------------------- the curve view

def test_curve_as_of_never_reads_a_later_day_and_lists_missing_tenors() -> None:
    curves = tr.read_par(C14_SAMPLES)
    assert tr.curve_as_of(curves, "2021-12-31").observation_date == "2021-12-31"
    sat = tr.curve_as_of(curves, "2022-12-31")                    # a Saturday: the Friday curve is in force
    assert sat.observation_date == "2022-12-30" and abs(sat.par["3 Mo"] - 0.0442) < 1e-12
    with pytest.raises(ValueError, match="no Treasury curve"):
        tr.curve_as_of(curves, "2020-12-31")
    assert tr.curve_as_of(curves, "2021-12-31").missing_tenors() == [0.333333]
    assert tr.curve_as_of(curves, "2022-12-30").missing_tenors() == []
    assert len(tr.curve_as_of(curves, "2021-12-31").tenors()) == 12


def test_history_up_to_holds_no_curve_after_the_date() -> None:
    curves = tr.read_par(C14_SAMPLES)
    for date in VALUATION_DATES:
        hist = tr.history_up_to(curves, date)
        assert hist and all(c.observation_date <= date for c in hist)
        assert [c.observation_date for c in hist] == sorted(c.observation_date for c in hist)
        assert tr.curve_as_of(curves, date) is hist[-1]


def test_read_par_refuses_a_repeated_date_and_an_empty_folder(tmp_path: Path) -> None:
    shutil.copytree(C14_SAMPLES, tmp_path / "t")
    g = tmp_path / "t" / "daily-treasury-par-2021.csv"
    g.write_text(g.read_text(encoding="utf-8") + g.read_text(encoding="utf-8").splitlines()[1] + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="repeated"):
        tr.read_par(tmp_path / "t")
    (tmp_path / "empty").mkdir()
    with pytest.raises(FileNotFoundError, match="no daily-treasury-par"):
        tr.read_par(tmp_path / "empty")


def test_quarter_ends() -> None:
    assert tr.quarter_ends("2021-09-30", "2022-06-30") == ["2021-09-30", "2021-12-31", "2022-03-31", "2022-06-30"]


def test_no_case_package_keeps_its_own_treasury_reader() -> None:
    cases = ROOT / "data-pipeline" / "pipeline" / "cases"
    assert not (cases / "c14" / "treasury.py").exists()
    assert "def parse_treasury" not in (cases / "c11" / "readers.py").read_text(encoding="utf-8")


# --------------------------------------------------------------------------------------------- equivalence on the samples

def test_series_view_equals_the_legacy_reader_on_the_sample() -> None:
    text = C11_SAMPLE.read_text(encoding="utf-8")
    for tenor in ("10 Yr", "3 Mo", "30 Yr", "2 Mo"):
        assert tr.parse_tenor(text, tenor) == old.parse_treasury(text, tenor)


def test_curve_view_equals_the_legacy_reader_on_the_sample() -> None:
    new, was = tr.read_par(C14_SAMPLES), old.read_par(C14_SAMPLES)
    assert list(new) == list(was)
    for day in was:
        assert new[day].observation_date == was[day].observation_date and new[day].par == was[day].par


# ---------------------------------------------------------------------------------- equivalence on every raw year file

@requires_raw
def test_series_view_is_identical_to_the_legacy_reader_on_every_year_file_1990_to_2023() -> None:
    compared = 0
    side = {n: v.get("retrieved") for n, v in old._sidecar(RAW / "raw" / "treasury-par").items()}
    for tenor, _ in tr.TENORS:
        o_dates, o_values, o_missing, o_files = old.read_treasury(RAW, 1990, 2023, tenor)
        dates, values, missing, files = tr.read_tenor(RAW, 1990, 2023, tenor, retrieved=side)
        assert np.array_equal(dates, o_dates) and dates.dtype == o_dates.dtype
        assert values.tobytes() == o_values.tobytes() and missing == o_missing
        assert [f.to_json() for f in files] == list(o_files)
        compared += dates.size + len(missing)
    print(f"series view: {compared} rows compared over {len(tr.TENORS)} tenors")
    assert compared > 50_000


@requires_raw
def test_curve_view_is_identical_to_the_legacy_reader_on_every_year_file_1990_to_2023() -> None:
    folder = RAW / "raw" / "treasury-par"
    new, was = tr.read_par(folder), old.read_par(folder)
    assert list(new) == list(was) and len(was) > 8000
    for day in was:
        assert new[day].par == was[day].par
    for date in (*VALUATION_DATES, "2008-09-15", "2023-12-31"):
        assert tr.curve_as_of(new, date).par == old.curve_as_of(was, date).par
        assert [c.observation_date for c in tr.history_up_to(new, date)] == [c.observation_date for c in old.history_up_to(was, date)]
        assert all(c.observation_date <= date for c in tr.history_up_to(new, date))
    print(f"curve view: {len(was)} curves compared")
