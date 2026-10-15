"""CT-601, CT-602, CT-614: the readers of the three public series, the skipped-day rule and the derived-only rule."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest

from pipeline.cases.c11 import portfolio as pf
from pipeline.cases.c11 import readers
from pipeline.io import contract as c1
from pipeline.io import treasury

DATA = Path(__file__).resolve().parent / "data"
ROOT = Path(__file__).resolve().parents[2]
FRENCH_SIGNATURES = ("Mkt-RF,SMB,HML",)       # the header of the raw file; its file name is provenance, not data


def test_treasury_reader_reads_the_ten_year_par_yield():
    d, v, missing = treasury.parse_tenor((DATA / "treasury-par-1995-excerpt.csv").read_text(encoding="utf-8"))
    assert len(d) == 30 and not missing
    assert d[0] == dt.date(1995, 12, 29) and abs(v[0] - 0.0558) < 1e-12      # 5.58 percent in decimals
    assert treasury.parse_tenor('Date,"3 Mo"\n01/02/1990,7.83\n', "10 Yr") == ([], [], [])   # a tenor not quoted that year


def test_h10_reader_marks_nd_as_missing_and_reads_two_digit_years():
    d, v, missing = readers.parse_h10((DATA / "h10-eu-excerpt.htm").read_text(encoding="utf-8"))
    assert missing == ["2000-01-17"] and len(d) == 23 and all(x.year == 2000 for x in d)
    assert dt.date(2000, 1, 17) not in d and all(0.9 < x < 1.2 for x in v)


def test_french_reader_market_return_is_excess_plus_riskfree():
    text = (",Mkt-RF,SMB,HML,RF\n20080102,   -1.50,    0.10,   -0.10,    0.02\n20080103,  -99.99, 0.1, 0.1, 0.02\n"
            "20080104,    2.00,0.1,0.1,0.01\n\nCopyright\n")
    d, v, missing = readers.parse_french(text)
    assert d == [dt.date(2008, 1, 2), dt.date(2008, 1, 4)]
    assert np.allclose(v, [(-1.5 + 0.02) / 100, (2.0 + 0.01) / 100]) and missing == ["2008-01-03"]


def test_the_three_series_pass_contract_one(series):
    assert set(series) == {"french-daily", "treasury-par", "h10-fx"}
    for sid, s in series.items():
        rep = c1.validate("market_series", s.contract_rows())
        assert rep.ok and not rep.rejected, (sid, rep.counts())
        assert np.all(np.diff(s.dates.astype("int64")) > 0), "dates strictly increase"
        assert s.files and all(len(f.sha256) == 64 and f.bytes > 0 and f.url.startswith("https://") for f in s.files)
    assert series["h10-fx"].dates[0] == np.datetime64("2000-01-03")


def test_fetch_records_url_size_hash_and_date(tmp_path):
    calls = []

    def opener(url: str) -> bytes:
        calls.append(url)
        return b'Date,"10 Yr"\n01/02/1990,7.94\n' if "treasury" in url else b"x" * 10

    files = readers.fetch(tmp_path, first_year=1990, last_year=1991, opener=opener, today="2026-10-14")
    assert len(files) == 4 and len(calls) == 4
    t90 = next(f for f in files if f.name == "daily-treasury-par-1990.csv")
    assert t90.url.endswith("field_tdr_date_value=1990&_format=csv") and t90.retrieved == "2026-10-14"
    assert t90.sha256 == hashlib.sha256((tmp_path / "raw" / "treasury-par" / t90.name).read_bytes()).hexdigest()
    side = json.loads((tmp_path / "raw" / "treasury-par" / readers.SIDECAR).read_text(encoding="utf-8"))
    assert side[t90.name]["url"] == t90.url
    readers.fetch(tmp_path, first_year=1990, last_year=1991, opener=opener)         # nothing is fetched twice
    assert len(calls) == 4


def test_adversarial_an_absent_raw_file_names_its_url(tmp_path):
    with pytest.raises(readers.DeclaredAbsence) as e:
        readers.read_french(tmp_path)
    assert readers.FRENCH_URL in str(e.value)
    with pytest.raises(readers.DeclaredAbsence) as e:
        readers.read_treasury(tmp_path, 1995, 1995)
    assert "daily-treasury-rates.csv/1995" in str(e.value)


def test_adversarial_a_missing_day_is_counted_and_never_filled(series):
    s = series["treasury-par"]
    assert s.missing, "the synthetic Treasury file has empty 10-year cells"
    assert np.datetime64(s.missing[0]) not in s.dates                     # skipped, not filled
    p = pf.build("mixed-2023", series)
    eur = series["h10-fx"]
    day = next(m for m in p.missing if m in eur.missing)
    assert np.datetime64(day) not in p.dates and day in p.missing          # a day a component lacks is skipped and counted
    k = int(np.searchsorted(p.dates, np.datetime64(day)))
    assert p.returns[k] != 0.0                                             # the next return spans the gap, it is not zero-filled
    assert not (set(map(str, p.dates)) & set(p.missing))


def test_adversarial_no_raw_french_data_is_committed(tmp_path):
    def scan(folders) -> list[str]:
        found = []
        for folder in folders:
            for p in Path(folder).rglob("*"):
                if p.is_file() and p.suffix.lower() in {".json", ".csv", ".txt", ".zip", ".md", ".htm"}:
                    if p.suffix.lower() == ".zip" or any(sig.encode() in p.read_bytes() for sig in FRENCH_SIGNATURES):
                        found.append(str(p))
        return found

    assert scan([ROOT / "data", ROOT / "models", ROOT / "docs" / "cases", ROOT / "docs" / "design" / "features" / "c11"]) == []
    planted = tmp_path / "data" / "derived"
    planted.mkdir(parents=True)
    with zipfile.ZipFile(planted / "F-F_Research_Data_Factors_daily_CSV.zip", "w") as z:
        z.writestr("x.csv", ",Mkt-RF,SMB,HML,RF\n")
    assert scan([tmp_path / "data"]) != []
