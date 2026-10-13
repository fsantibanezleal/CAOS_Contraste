"""CT-501 to CT-503: the readers, contract 1 over what they produce, the missing inputs."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pipeline.cases.c06 import macro, panel
from pipeline.io import sba as readers
from pipeline.cases.c06.variant import loan_panel_records
from pipeline.io import contract as c1

FORBIDDEN_COLUMNS = {"BorrName", "BorrStreet", "BorrCity", "BorrZip", "LocationID", "BankName", "BankFDICNumber"}


def test_sba_reader_feeds_the_loan_panel_contract(tables, variant):
    df, counts = tables["frame"], tables["counts"]
    assert FORBIDDEN_COLUMNS.isdisjoint(df.columns), "the reader never reads a name, an address or an identifier"
    assert {"approval_date", "term_months", "gross_approval", "status", "chargeoff_date", "paid_date"} <= set(df.columns)
    # every row is either kept or counted under a reason
    left_out = sum(v for k, v in counts.items() if k not in ("rows-read", "loans-kept"))
    assert counts["rows-read"] == len(df) == counts["loans-kept"] + left_out
    assert counts["not-disbursed-or-cancelled"] == 0 or counts["not-disbursed-or-cancelled"] > 0  # present, counted
    records = loan_panel_records(tables["loans"], variant.run)
    report = c1.validate("loan_panel", records)
    assert not report.rejected and len(report.accepted) == len(records) == variant.run.a
    first = records[0]
    assert first["dpd"] == 0 and first["default_flag"] == 0 and first["account_id"].startswith("SBA")
    revolving = [r for r in records if r["revolving"] == 1]
    assert all(r["limit"] is not None and r["limit"] >= r["balance"] for r in revolving)


def test_adversarial_a_planted_bad_row_is_counted_under_its_reason(tables):
    df = tables["frame"].iloc[:50].copy()
    bad = df.iloc[:3].copy()
    bad.loc[bad.index[0], "term_months"] = 0.0
    bad.loc[bad.index[1], "status"] = "CANCLD"
    bad.loc[bad.index[2], "status"] = "CHGOFF"
    bad.loc[bad.index[2], "chargeoff_date"] = pd.NaT
    _, counts = panel.prepare(pd.concat([df, bad], ignore_index=True))
    assert counts["term-missing-or-implausible"] >= 1 and counts["not-disbursed-or-cancelled"] >= 1
    assert counts["chargeoff-without-date"] >= 1


def test_fed_reader_feeds_the_macro_path_contract(tables, variant):
    run = variant.run
    rows = macro.macro_path_records(run.history, run.paths, run.reporting_date)
    rd = str(np.datetime64(run.reporting_date, "D"))
    report = c1.validate("macro_path", rows, params={"observation_date": rd})
    assert not report.rejected and len(report.accepted) == len(rows)
    assert {r["scenario"] for r in rows} == {"history", *macro.SCENARIOS}
    assert max(r["date"] for r in rows if r["scenario"] == "history") <= rd < min(r["date"] for r in rows if r["scenario"] != "history")
    assert all(r["vintage_date"] <= rd for r in rows)


def test_adversarial_a_late_vintage_path_is_refused(variant):
    run = variant.run
    rows = macro.macro_path_records(run.history, run.paths, run.reporting_date)
    rd = str(np.datetime64(run.reporting_date, "D"))
    late = [{**rows[0], "vintage_date": "2026-02-04"}]  # the Federal Reserve 2026 release, after a 2010 reporting date
    assert c1.validate("macro_path", late, params={"observation_date": rd}).rejected


def test_a_missing_input_stops_the_bake_with_its_url(tmp_path):
    with pytest.raises(readers.SourceUnavailable, match=readers.FED_URLS[readers.FED_HISTORY].replace(".", r"\.")):
        readers.read_fed(tmp_path)
    with pytest.raises(readers.SourceUnavailable, match=readers.SBA_URLS[readers.SBA_FILES[0]].replace(".", r"\.")):
        readers.read_sba(tmp_path)
    with pytest.raises(readers.SourceUnavailable, match="data.sba.gov"):
        readers.data_files(tmp_path)


def test_the_sba_reader_refuses_a_changed_layout(tmp_path):
    folder = tmp_path / "raw" / "sba-foia"
    folder.mkdir(parents=True)
    (folder / "FOIA_7a_sample_asof_260630.csv").write_text("AsOfDate,GrossApproval\n2026-06-30,100\n", encoding="utf-8")
    with pytest.raises(ValueError, match="layout changed"):
        readers.read_sba(tmp_path)


def test_the_freddie_mac_slot_declares_its_absence(tmp_path, variant):
    with pytest.raises(readers.DeclaredAbsence, match="owner's account is missing"):
        readers.read_freddie(tmp_path)
    status = variant.document["outputs"]["data_status"]
    assert status["freddie_mac_available"] is False and status["freddie_mac_reason"] == readers.FREDDIE_REASON
    assert status["primary_source"] == "sba-7a"
    assert "not mortgages" in status["notice"]["en"]
