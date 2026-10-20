"""CT-1201, CT-1202, CT-1203, CT-1205: the readers, the dates, the HQM spread and the calibration (they read the device data root)."""
from __future__ import annotations

import json

import c12_docs as d
import numpy as np
import pytest
from c12_support import data_root, requires_raw

from pipeline.cases.c12 import bake, calibration, credit, data, fetch
from pipeline.io import treasury


@requires_raw
def test_the_raw_files_match_their_provenance_records_and_the_committed_copy() -> None:
    prov = fetch.load_provenance(data_root())
    assert [r["name"] for r in prov[fetch.HQM_DIR]] == list(fetch.HQM_FILES)
    years = [int(r["name"].split("-")[-1].split(".")[0]) for r in prov[fetch.TREASURY_DIR]]
    assert years == list(range(1990, years[-1] + 1))
    for folder, rows in prov.items():
        for r in rows:
            f = data_root() / "raw" / folder / r["name"]
            assert treasury.sha256_of(f) == r["sha256"] and f.stat().st_size == r["bytes"], r["name"]
            assert r["url"].startswith("https://home.treasury.gov/") and r["retrieved"] >= "2026-10-01"
    committed = d.C12 / "raw-sources.txt"
    if committed.exists():
        rows = json.loads(committed.read_text(encoding="utf-8"))["sources"]
        assert rows["treasury-par-curve"]["files"] == prov[fetch.TREASURY_DIR] and rows["treasury-hqm"]["files"] == prov[fetch.HQM_DIR]


@requires_raw
def test_backtest_dates_are_published_curves_and_each_horizon_is_observed() -> None:
    curves = data.read_curves(data_root())
    dates = curves.backtest_dates("2000-01", curves.last)
    assert dates[0].startswith("2000-01") and dates == sorted(set(dates)) and all(x in curves.by_date for x in dates)
    assert len(dates) == len(data.months_between("2000-01", dates[-1]))
    assert data.horizon_date(dates[-1], "12m") <= curves.last < data.horizon_date(data.add_months(dates[-1], 1), "12m")
    for day in dates[::25] + dates[-3:]:
        for h in data.HORIZONS:
            assert curves.as_of(data.horizon_date(day, h)).observation_date > day, (day, h)
    assert data.horizon_date("2025-09-30", "10bd") == "2025-10-14" and data.horizon_date("2025-09-30", "20bd") == "2025-10-28"
    assert data.horizon_date("2025-01-31", "1m") == "2025-02-28"


def test_the_hqm_spread_is_hqm_minus_treasury_floored_at_zero_and_a_missing_month_is_declared() -> None:
    tenors, zeros = np.array([0.5, 1.0, 5.0, 10.0]), np.array([0.03, 0.03, 0.03, 0.03])
    mats = np.array([0.5, 1.0, 5.0, 10.0])
    hqm = (mats, np.array([0.04, 0.04, 0.025, 0.04]))                 # semiannual spot rates in decimals
    s = data.hqm_spread(hqm, tenors, zeros, mats)
    assert s[0] == pytest.approx(2 * np.log1p(0.02) - 0.03, abs=1e-15) and s[2] < 0.0
    cur = credit.hqm_curve(hqm, tenors, zeros, np.array([0.5, 1.0, 5.0, 10.0]))
    assert cur.floored == 1 and float(cur.spreads.min()) == 0.0 and cur.source == "hqm-minus-treasury"
    # a month the HQM files lack stops the stressed row and names the URL
    curves = type("C", (), {"zero": lambda self, me: (tenors, zeros, None)})()
    series = calibration.Series([], np.zeros(0))
    with pytest.raises((treasury.DeclaredAbsence, ValueError), match="corporate-bond-yield-curve|observations"):
        bake._stress(curves, series, {}, "2007-01-01", "2009-12-31")


@requires_raw
def test_a_calibration_uses_only_observations_before_its_date() -> None:
    curves = data.read_curves(data_root())
    ser = calibration.series_of(curves)
    day = "2013-06-28"
    fit = calibration.fit_at(ser, day)
    assert fit.sample_end < day and fit.sample_start == "1990-01-02" and fit.n_obs > 12 * 3
    cut = np.searchsorted(ser.dates, day)
    shifted = calibration.Series(list(ser.dates), ser.values.copy())
    shifted.values[cut:] += 0.05           # everything on or after the date moves
    again = calibration.fit_at(shifted, day)
    assert (again.a, again.sigma, again.n_obs, again.sample_end) == (fit.a, fit.sigma, fit.n_obs, fit.sample_end)
    rec = calibration.record(fit, day)
    assert rec["history_years"] >= 3 and rec["sample_end"] < rec["backtest_date"]
    with pytest.raises(ValueError, match="CRE53.51"):
        calibration.fit_at(ser, "1992-06-30")             # under three years of history
