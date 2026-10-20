"""CT-0201, CT-0202, CT-0203: the reader, the missing-data rule and contract 1."""
from __future__ import annotations

import shutil
import zipfile

import numpy as np
import pytest
from c02_support import PLANTED_ROWS, ZIP_NAME, arff_text, make_zip, manifest_for

from pipeline.cases.c02 import conventions as cv
from pipeline.cases.c02 import reader


def test_the_reader_reads_missing_as_missing_and_refuses_a_changed_layout_or_count(planted, tmp_path) -> None:
    root, _ = planted
    h = reader.read_horizons(root / "raw" / "uci-polish" / ZIP_NAME, check_counts=False)
    assert sorted(h) == [1, 2, 3, 4, 5]
    for k, n in zip(range(1, 6), PLANTED_ROWS):
        assert h[k].rows == n + 1 and h[k].X.shape == (n + 1, 64) and list(h[k].X.columns) == list(cv.ATTRIBUTES)
        assert h[k].X.dtypes.eq(float).all() and set(np.unique(h[k].y)) <= {0, 1}
    text = arff_text(1, PLANTED_ROWS[0])
    X, y = reader.read_arff(text, "1year.arff")
    first = [c for c in text.split("@data\n")[1].splitlines()[0].split(",")]
    assert [bool(np.isnan(v)) for v in X.iloc[0]] == [c == "?" for c in first[:64]]          # ? is NaN and no other cell is
    assert X.isna().to_numpy().sum() == text.count("?") and len(y) == len(X)
    # the counts of the UCI page are enforced: the planted file is not the real one
    with pytest.raises(reader.PolishFormatError, match="the UCI page gives"):
        reader.read_horizons(root / "raw" / "uci-polish" / ZIP_NAME)
    # a changed layout is refused: an attribute renamed, a class value outside {0,1}, a member missing
    with pytest.raises(reader.PolishFormatError, match="Attr1 to Attr64"):
        reader.read_arff(text.replace("@attribute Attr7 numeric", "@attribute Ratio7 numeric"), "1year.arff")
    with pytest.raises(reader.PolishFormatError):
        reader.read_arff(text.replace("{0,1}", "{0,1,2}").replace(",0\n", ",2\n", 1), "1year.arff")
    broken = tmp_path / "broken.zip"
    with zipfile.ZipFile(root / "raw" / "uci-polish" / ZIP_NAME) as src, zipfile.ZipFile(broken, "w") as dst:
        for name in src.namelist()[:4]:
            dst.writestr(name, src.read(name))
    with pytest.raises(reader.PolishFormatError, match="5year.arff"):
        reader.read_horizons(broken, check_counts=False)


def test_an_absent_zip_runs_the_fetch_first_and_a_failed_fetch_or_a_changed_hash_stops_c02(planted, tmp_path) -> None:
    root, manifest = planted
    target = tmp_path / "root"
    calls: list[str] = []

    def fetcher(source, *, root):
        calls.append(source)
        make_zip(root / "raw" / source / ZIP_NAME)
        return {}

    path = reader.ensure_zip(target, fetcher=fetcher, manifest=manifest)
    assert calls == ["uci-polish"] and path.name == ZIP_NAME and path.is_file()
    calls.clear()
    assert reader.ensure_zip(target, fetcher=fetcher, manifest=manifest) == path and calls == []     # present: no fetch
    # the fetch does not answer: C02 stops and names the file, nothing stands in for it
    empty = tmp_path / "empty"

    def failing(source, *, root):
        raise OSError("planted: no route to the UCI landing")

    with pytest.raises(reader.PolishSourceError, match=r"polish\+companies\+bankruptcy\+data\.zip.*fetch.*failed"):
        reader.ensure_zip(empty, fetcher=failing, manifest=manifest)
    assert not (empty / "raw" / "uci-polish" / ZIP_NAME).exists()
    # one byte differs from the pinned hash
    changed = tmp_path / "changed"
    shutil.copytree(root, changed)
    z = changed / "raw" / "uci-polish" / ZIP_NAME
    z.write_bytes(z.read_bytes() + b"x")
    with pytest.raises(reader.PolishSourceError, match="pinned"):
        reader.ensure_zip(changed, fetcher=failing, manifest=manifest)
    assert manifest_for(z)["sources"]["uci-polish"]["files"][0]["sha256"] != manifest["sources"]["uci-polish"]["files"][0]["sha256"]


def test_contract_1_takes_the_identity_and_date_conventions_and_counts_missing_and_repeated_rows(planted) -> None:
    root, _ = planted
    h = reader.read_horizons(root / "raw" / "uci-polish" / ZIP_NAME, check_counts=False)
    recs = reader.contract_records(h[1])
    assert recs[0]["id"] == "h1-1" and recs[-1]["id"] == f"h1-{h[1].rows}"
    assert {r["observation_date"] for r in recs} == {"2013-12-31"} == {cv.OBSERVATION_DATE}
    assert "no out-of-time claim" in cv.OBSERVATION_DATE_NOTE["en"] and "ningún reclamo fuera del tiempo" in cv.OBSERVATION_DATE_NOTE["es"]
    report = reader.validate_contract(h)
    counts = report.counts()
    assert counts["rejected"] == 0 and counts["accepted"] == sum(x.rows for x in h.values())
    flagged = report.summary()["by_rule"]["flagged"]
    missing = sum(int(x.X.isna().to_numpy().sum()) for x in h.values())
    assert sum(v for k, v in flagged.items() if k != "C02-DUPLICATE-VECTOR") == missing           # every ? is counted as a missing flag
    assert flagged["C02-DUPLICATE-VECTOR"] == 5                                                   # the repeated first row of each file
