"""CT-1401, CT-1402, CT-1403: the readers apply the dating rule, list missing tenors and carry the provenance of the raw files."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import ROOT, data_root, requires_raw

from pipeline.cases.c14 import fdic, treasury

DATA = Path(__file__).resolve().parent / "data"


def reports() -> list[fdic.Report]:
    return fdic.read_financials(DATA / "sample-financials.json", 24735)


def test_reports_up_to_a_date_never_include_a_later_one() -> None:
    rs = reports()
    assert [r.report_date for r in rs] == ["2021-09-30", "2021-12-31", "2022-03-31", "2022-12-31"]
    assert [r.report_date for r in fdic.up_to(rs, "2021-12-31")] == ["2021-09-30", "2021-12-31"]
    assert fdic.report_at(rs, "2021-12-31").get("ASSET") == 208581000
    with pytest.raises(ValueError, match="no call report dated 2022-01-31"):
        fdic.report_at(rs, "2022-01-31")
    with pytest.raises(ValueError, match="does not start after"):
        fdic.realised_nii(rs, "2021-12-31", "2021-01-01", "2021-12-31")
    with pytest.raises(ValueError, match="full calendar year"):
        fdic.realised_nii(rs, "2021-12-31", "2022-01-01", "2022-03-31")
    assert fdic.realised_nii(rs, "2021-12-31", "2022-01-01", "2022-12-31") == 4584000
    with pytest.raises(fdic.MissingField):
        fdic.Report("2021-12-31", {"ASSET": None}).get("ASSET")


def test_treasury_curve_as_of_never_reads_a_later_day_and_lists_missing_tenors() -> None:
    curves = treasury.read_par(DATA / "treasury-sample")
    assert treasury.curve_as_of(curves, "2021-12-31").observation_date == "2021-12-31"
    # 2022-12-31 is a Saturday: the curve in force is Friday 2022-12-30, not a later day
    sat = treasury.curve_as_of(curves, "2022-12-31")
    assert sat.observation_date == "2022-12-30" and abs(sat.par["3 Mo"] - 0.0442) < 1e-12
    assert treasury.curve_as_of(curves, "2022-12-29").observation_date == "2022-12-29"
    with pytest.raises(ValueError, match="no Treasury curve"):
        treasury.curve_as_of(curves, "2020-12-31")
    # the 4 month bill exists from 2022-10-19: the 2021 and mid-2022 days list it, 2022-12-30 does not
    assert treasury.curve_as_of(curves, "2021-12-31").missing_tenors() == [0.333333]
    assert treasury.curve_as_of(curves, "2022-06-30").missing_tenors() == [0.333333]
    assert treasury.curve_as_of(curves, "2022-12-30").missing_tenors() == []
    assert len(treasury.curve_as_of(curves, "2021-12-31").tenors()) == 12
    assert treasury.quarter_ends("2021-09-30", "2022-06-30") == ["2021-09-30", "2021-12-31", "2022-03-31", "2022-06-30"]


@requires_raw
def test_the_raw_files_match_their_provenance_records_and_the_committed_copy() -> None:
    from pipeline.cases.c14 import fetch

    prov = fetch.load_provenance(data_root())
    assert set(prov) == {fetch.FDIC_DIR, fetch.TREASURY_DIR}
    for rows in prov.values():
        for r in rows:
            assert r["url"].startswith("https://") and r["bytes"] > 0 and len(r["sha256"]) == 64 and r["retrieved"][:2] == "20"
    committed = json.loads((ROOT / "data" / "derived" / "C14" / "raw-sources.txt").read_text(encoding="utf-8"))
    assert {k: v["files"] for k, v in committed["sources"].items()} == {"fdic-bankfind": prov[fetch.FDIC_DIR],
                                                                       "treasury-par-curve": prov[fetch.TREASURY_DIR]}
