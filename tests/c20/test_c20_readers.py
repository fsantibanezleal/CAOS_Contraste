"""CT-2001, CT-2006, CT-2025: the readers on committed samples of their sources."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import numpy as np
from c20_support import DATA

from pipeline.cases import c01_features as feat
from pipeline.cases.c20 import fed, polish, sgcd
from pipeline.io import contract as c1
from pipeline.io.readers import GERMAN_OBSERVATION_DATE


def sample() -> sgcd.Dataset:
    return sgcd.read_dataset(DATA / "sgcd-sample.jsonl", DATA / "sgcd-metadata.json")


def test_the_sgcd_reader_keeps_the_null_as_missing_and_maps_the_conventions() -> None:
    ds = sample()
    assert len(ds.records) == 15 and ds.metadata["seed"] == 42 and ds.metadata["version"] == "SGCD-v0.1"
    nulls = [r for r in ds.records if any(v is None for v in r.view.values())]
    assert [r.id for r in nulls] == ["SGCD-0251", "SGCD-0280"] and all(r.shock == "F1" for r in nulls)
    # a null stays a missing value, never a code; an F1 record can keep every code in the structured view (58 of 128 shipped F1 records)
    assert any(r.shock == "F1" and not any(v is None for v in r.view.values()) for r in ds.records)
    rows = sgcd.contract_records(ds.records)
    assert [r["id"] for r in rows] == [r.id for r in ds.records]
    for rec, row in zip(ds.records, rows):
        assert row["target"] == (1 if rec.label == 0 else 0)                  # label 0 is Bad, the default
        assert row["observation_date"] == GERMAN_OBSERVATION_DATE and row["protected_attr"] in ("male", "female")
        assert set(sgcd.FIELD_MAP.values()) <= set(row) and not {"age", "foreign_worker", "personal_status_sex"} & set(row)
    assert all(row[dst] is None for rec, row in zip(ds.records, rows) for src, dst in sgcd.FIELD_MAP.items() if rec.view[src] is None)
    report = c1.validate("scored_sample", rows, extra_fields=feat.GERMAN_FIELDS)
    assert report.counts()["accepted"] == 15 and report.counts()["rejected"] == 0 and report.counts()["flagged"] == 2
    assert [a["id"] for a in report.accepted] == [r.id for r in ds.records]
    assert sgcd.feature_names() == feat.GERMAN_FEATURES and set(sgcd.FIELD_MAP.values()) == set(feat.GERMAN_FEATURES)


def test_the_sgcd_text_view_is_read_for_the_consistency_of_the_f4_fields() -> None:
    ds = sample()
    book = sgcd.read_codebook(DATA / "sgcd-codebook.md")
    f4 = [r for r in ds.records if r.shock == "F4"]
    clean = [r for r in ds.records if r.shock == "F0" and not r.cosmetic]
    a, b = sgcd.consistency_pairs(clean, book)
    assert a == b and len(a) == 5 * len(clean)                                 # a clean record states what its structured view holds
    a4, b4 = sgcd.consistency_pairs(f4, book)
    assert len(a4) > 0 and sum(1 for u, w in zip(a4, b4) if u != w) >= 1       # the contradiction is read from the two views
    f2 = [r for r in ds.records if r.shock == "F2"]
    a2, b2 = sgcd.consistency_pairs(f2, book)
    assert all(u == w for u, w in zip(a2, b2))                                 # a coded or vague wording is not a contradiction


def test_the_fed_reader_reads_na_as_missing_and_the_rating_on_its_scale() -> None:
    p = fed.read_portfolio(DATA / "fed-sample.csv", "typical", expected_rows=10)
    assert p.n == 10 and p.name == "typical"
    assert p.n_missing["term"] == 3 and p.n_missing["interest_rate"] == 0 and np.isnan(p["term"]).sum() == 3
    assert set(p["rating"]) <= set(float(k + 1) for k in range(len(fed.RATING_SCALE)))
    assert p["rating"][0] == float(fed.RATING_SCALE.index("BB") + 1)
    assert p["committed_exposure_amt"][0] == 618000.0 and p["utilized_exposure_amt"][0] == 0.0
    assert fed.PORTFOLIOS == ("typical", "higher-risk", "lower-risk") and len(fed.VARIABLES) == 12


def test_the_polish_reader_maps_missing_values_and_the_target(tmp_path: Path) -> None:
    z = polish_zip(tmp_path / "pl.zip", [(["1.5"] * 63 + ["?"], "0"), (["2.5"] * 64, "1")])
    rows = polish.read_polish(z)
    assert [r["id"] for r in rows] == ["PL3-00001", "PL3-00002"] and [r["target"] for r in rows] == [0, 1]
    assert rows[0]["Attr64"] is None and rows[0]["Attr1"] == 1.5 and rows[1]["Attr64"] == 2.5
    assert rows[0]["observation_date"] == polish.OBSERVATION_DATE == "2013-12-31"
    report = c1.validate("scored_sample", rows, extra_fields=polish.FIELDS)
    assert report.counts()["accepted"] == 2 and report.counts()["flagged"] == 1


def polish_zip(path: Path, rows: list[tuple[list[str], str]]) -> Path:
    head = "@relation x\n" + "".join(f"@attribute Attr{k} numeric\n" for k in range(1, 65)) + "@attribute class {0,1}\n@data\n"
    body = "".join(",".join([*vals, cls]) + "\n" for vals, cls in rows)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(polish.MEMBER, head + body)
    path.write_bytes(buf.getvalue())
    return path
