"""CT-2101, CT-2102, CT-2103, CT-2105: the HMDA reader and its conventions."""
from __future__ import annotations

from pathlib import Path

import pytest
from c21_support import API_HEADER, make_year, write_file

from pipeline.cases.c21 import legal, reader

SNAPSHOT_HEADER = [reader.canonical(c) for c in API_HEADER]


def test_the_reader_maps_both_spellings_and_reads_missing_markers_as_missing(tmp_path: Path) -> None:
    rows = make_year(2019, 300)
    api = reader.read_year(_file(tmp_path / "api.csv", 2019, rows), 2019)
    snap = reader.read_year(_file(tmp_path / "snap.csv", 2019, rows, SNAPSHOT_HEADER), 2019)
    assert api.rows == snap.rows and api.action_counts == snap.action_counts      # the two spellings read the same
    assert reader.canonical("loan_to_value_ratio") == "combined_loan_to_value_ratio"
    assert reader.canonical("co-applicant_sex") == "co_applicant_sex" and reader.canonical("derived_msa-md") == "derived_msa_md"
    assert reader.number("NA", "x") is None and reader.number("Exempt", "x") is None and reader.number("", "x") is None
    assert reader.number("12.5", "x") == 12.5 and reader.number("-3", "x") == -3.0           # a negative income is a number, not missing
    assert reader.dti_bin("NA", "x") is None and reader.dti_bin("Exempt", "x") is None and reader.dti_bin("", "x") is None
    # no missing marker becomes a number: the rate spread of an excluded code is missing, a stated one is a float
    assert all(r["rate_spread"] is None or isinstance(r["rate_spread"], float) for r in api.rows)
    assert any(r["rate_spread"] is None for r in api.rows) and any(r["dti_bin"] is None for r in api.rows)
    assert {r["dti_bin"] for r in api.rows if r["dti_bin"] is not None} == set(range(6))
    with pytest.raises(reader.HmdaFormatError, match="not a number"):
        reader.number("1,5", "x")


def test_the_decision_convention_counts_codes_4_to_8_apart_and_labels_itself(tmp_path: Path) -> None:
    rows = make_year(2020, 400)
    y = reader.read_year(_file(tmp_path / "f.csv", 2020, rows), 2020)
    by_code = {c: sum(1 for r in rows if r[6] == str(c)) for c in range(1, 9)}
    assert y.action_counts == {c: n for c, n in by_code.items() if n} and y.n_file_rows == len(rows)
    assert len(y.rows) == by_code[1] + by_code[2] + by_code[3]                 # codes 4 to 8 never become a decision row
    assert {r["action_taken"] for r in y.rows} == {1, 2, 3}
    assert all(r["decision"] == (1 if r["action_taken"] in (1, 2) else 0) for r in y.rows)
    assert y.n_left_out() == sum(by_code[c] for c in range(4, 9))
    conv = legal.conventions_block()
    assert conv["label"] == "convention"
    assert conv["outcome"] == {**conv["outcome"], "approval_codes": [1, 2], "denial_codes": [3], "excluded_codes": [4, 5, 6, 7, 8]}


def test_the_identity_convention_and_contract_1_with_outcome_none(tmp_path: Path) -> None:
    y = reader.read_year(_file(tmp_path / "f.csv", 2021, make_year(2021, 300)), 2021)
    recs = reader.contract_records(y)
    assert recs[0]["id"] == f"2021-{y.rows[0]['row']}" and all(r["observation_date"] == "2021-12-31" for r in recs)
    assert len({r["id"] for r in recs}) == len(recs)
    rep = reader.validate_contract([y])
    assert rep.counts()["rejected"] == 0 and rep.counts()["accepted"] == len(y.rows)
    assert {"id", "observation_date", "decision"} <= set(rep.accepted[0]) and rep.accepted[0]["target"] is None
    conv = legal.conventions_block()["identifiers"]
    assert conv["id"] == "<activity_year>-<row>" and conv["observation_date"] == "<activity_year>-12-31" and conv["label"] == "convention"


def test_non_attribute_categories_are_excluded_groups_and_dti_is_recoded_to_the_published_bins(tmp_path: Path) -> None:
    for f in legal.ATTRIBUTES:
        assert not set(legal.GROUPS[f]) & set(legal.NON_GROUPS[f])
    assert {"Joint", "Free Form Text Only", "Race Not Available"} == set(legal.NON_GROUPS["derived_race"])
    assert {"Joint", "Sex Not Available"} == set(legal.NON_GROUPS["derived_sex"])
    assert {"Joint", "Free Form Text Only", "Ethnicity Not Available"} == set(legal.NON_GROUPS["derived_ethnicity"])
    assert "8888" in legal.NON_GROUPS["applicant_age"]
    assert legal.DTI_BINS == ("<20%", "20%-<30%", "30%-<36%", "36%-49%", "50%-60%", ">60%")
    got = {s: reader.dti_bin(s, "x") for s in ("<20%", "20%-<30%", "30%-<36%", "36", "42", "49", "50%-60%", ">60%")}
    assert got == {"<20%": 0, "20%-<30%": 1, "30%-<36%": 2, "36": 3, "42": 3, "49": 3, "50%-60%": 4, ">60%": 5}
    with pytest.raises(reader.HmdaFormatError):
        reader.dti_bin("abc", "x")


SAMPLE = Path(__file__).resolve().parent / "data" / "sample-synthetic-api-2019.csv"


def test_the_committed_synthetic_sample_reads_to_its_known_counts() -> None:
    """tests/c21/data/sample-synthetic-api-2019.csv: 56 synthetic rows (planted, never HMDA) in the Data Browser spelling."""
    y = reader.read_year(SAMPLE, 2019)
    assert (y.n_file_rows, len(y.rows)) == (56, 50) and y.action_counts == {1: 28, 2: 3, 3: 19, 4: 1, 6: 1, 7: 4}
    assert sum(r["decision"] for r in y.rows) == 31 and sum(1 for r in y.rows if r["dti_bin"] is None) == 4
    assert y.rows[0]["row"] == 1 and y.rows[0]["derived_race"] == "Native Hawaiian or Other Pacific Islander" and y.rows[0]["income"] == 104.0
    assert reader.validate_contract([y]).counts() == {"input": 50, "accepted": 50, "rejected": 0, "flagged": 0, "excluded": 0}


def _file(path: Path, year: int, rows: list[list[str]], header: list[str] | None = None) -> Path:
    write_file(path, rows, header)
    return path
