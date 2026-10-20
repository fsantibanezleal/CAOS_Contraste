"""CT-1601 to CT-1604: the readers of C16 on the committed samples (the FDIC wide span, the H.8 release page, the raw-file
provenance)."""
from __future__ import annotations

import json

import pytest

from .helpers import DATA, sample_reports


def test_the_wide_span_reader_returns_no_report_after_the_valuation_date():
    from pipeline.cases.c16 import fetch
    from pipeline.io import fdic

    assert fetch.FIRST_REPDTE == "20091231" and fetch.LAST_REPDTE == "20221231"
    reports = sample_reports()
    assert [r.report_date for r in reports] == ["2021-12-31", "2022-06-30", "2022-09-30", "2022-12-31"]
    for vd in ("2021-12-31", "2022-06-30", "2022-12-30"):
        known = fdic.up_to(reports, vd)
        assert known and all(r.report_date <= vd for r in known)
        assert max(r.report_date for r in known) <= vd
    assert [r.report_date for r in fdic.up_to(reports, "2022-06-30")] == ["2021-12-31", "2022-06-30"]
    assert fdic.report_at(reports, "2022-06-30").get("DEP") > 0
    with pytest.raises(ValueError, match="no call report dated 2022-03-31"):
        fdic.report_at(reports, "2022-03-31")
    # the bake's own restriction drops every report and curve dated after the date
    from pipeline.cases.c16 import bake

    from .helpers import sample_inputs

    cut = bake.restrict(sample_inputs(), "2022-06-30")
    assert max(r.report_date for r in cut.reports) == "2022-06-30" and max(cut.curves) <= "2022-06-30"


def test_the_h8_parser_reads_the_deposit_lines_of_the_large_and_small_banks():
    from pipeline.cases.c16 import h8

    from .helpers import h8_release

    rel = h8_release()
    assert rel.release_date == "2023-03-17" and sorted(rel.tables) == [6, 8]
    large, small = rel.tables[6], rel.tables[8]
    assert large.adjustment == "seasonally-adjusted" and "billions of dollars" in large.unit
    assert "Large Domestically Chartered" in large.title and "Small Domestically Chartered" in small.title
    assert h8.weekly_series(rel, 6, "Deposits") == [
        ("2023-02-15", 10778.1), ("2023-02-22", 10766.6), ("2023-03-01", 10765.9), ("2023-03-08", 10693.5)]
    assert h8.weekly_series(rel, 8, "Deposits")[-1] == ("2023-03-08", 5498.8)
    assert h8.weekly_series(rel, 6, "Large time deposits")[-1] == ("2023-03-08", 469.2)
    assert h8.weekly_series(rel, 6, "Other deposits")[0] == ("2023-02-15", 10340.4)
    # the monthly columns come with their month, the year read from the column head
    assert large.value("Deposits", "2023-02") == 10778.6
    # a release of January labels December weeks with the previous year
    assert h8.week_dates(["Dec 21", "Dec 28", "Jan 04", "Jan 11"], "2023-01-13") == [
        "2022-12-21", "2022-12-28", "2023-01-04", "2023-01-11"]


def test_the_h8_parser_refuses_a_page_without_the_expected_table():
    from pipeline.cases.c16 import h8

    text = (DATA / "h8-sample-20230317.html").read_text(encoding="utf-8")
    rel = h8.parse_release(text, "2023-03-17")
    with pytest.raises(h8.H8Error, match="Table 7"):
        h8.weekly_series(rel, 7, "Deposits")
    with pytest.raises(h8.H8Error, match="Nonexistent line"):
        h8.weekly_series(rel, 6, "Nonexistent line")
    with pytest.raises(h8.H8Error, match="no table"):
        h8.parse_release("<html><body><p>The page moved.</p></body></html>", "2023-03-17")
    # a cell that is not a number is a gap, never filled: the requested week refuses
    broken = text.replace("10,693.5", "n.a.", 1)
    rel2 = h8.parse_release(broken, "2023-03-17")
    with pytest.raises(h8.H8Error, match="2023-03-08"):
        h8.weekly_series(rel2, 6, "Deposits")
    # a page of another series is refused by its title
    with pytest.raises(h8.H8Error, match="title"):
        h8.parse_release(text.replace("Large Domestically Chartered", "Foreign"), "2023-03-17").table(6)


def test_the_raw_files_match_their_provenance_records_and_the_fetch_never_touches_the_c14_file(tmp_path):
    from pipeline.cases.c14 import fetch as c14
    from pipeline.cases.c16 import fetch

    assert fetch.fdic_name() != c14.fdic_name() and fetch.PROVENANCE != c14.PROVENANCE
    assert "20091231" in fetch.fdic_url() and "CERT:24735" in fetch.fdic_url().replace("%3A", ":")
    raw = tmp_path / "raw"
    (raw / fetch.FDIC_DIR).mkdir(parents=True)
    (raw / fetch.TREASURY_DIR).mkdir(parents=True)
    c14_file = raw / fetch.FDIC_DIR / c14.fdic_name()
    c14_file.write_bytes(b'{"c14": "must stay"}')
    c14_sidecar = raw / fetch.FDIC_DIR / c14.PROVENANCE
    c14_sidecar.write_text("[]", encoding="utf-8")
    (raw / fetch.TREASURY_DIR / "daily-treasury-par-2022.csv").write_text("Date\n", encoding="utf-8")
    (raw / fetch.TREASURY_DIR / c14.PROVENANCE).write_text(json.dumps([fetch.describe(
        raw / fetch.TREASURY_DIR / "daily-treasury-par-2022.csv", "https://example.test/t", "2026-10-19")]), encoding="utf-8")
    before = (c14_file.read_bytes(), c14_sidecar.read_bytes())

    def fake(url: str, timeout: float = 90.0) -> bytes:
        return b"<html>" + url.encode() + b"</html>" if "federalreserve" in url else json.dumps({"data": [], "url": url}).encode()

    rows = fetch.fetch(tmp_path, today="2026-10-19", download=fake, releases=("20230317",))
    assert (c14_file.read_bytes(), c14_sidecar.read_bytes()) == before
    assert {r["name"] for r in rows[fetch.FDIC_DIR]} == {fetch.fdic_name()}
    assert [r["name"] for r in rows[fetch.H8_DIR]] == ["h8-20230317.html"]
    prov = fetch.load_provenance(tmp_path)
    for folder in (fetch.FDIC_DIR, fetch.H8_DIR, fetch.TREASURY_DIR):
        for r in prov[folder]:
            assert set(r) >= {"name", "url", "bytes", "sha256", "retrieved"} and len(r["sha256"]) == 64
    # one byte of a raw file changes: the loader refuses it
    target = raw / fetch.H8_DIR / "h8-20230317.html"
    target.write_bytes(target.read_bytes().replace(b"<html>", b"<HTML>"))
    with pytest.raises(ValueError, match="differs from its provenance record"):
        fetch.load_provenance(tmp_path)
