"""The bring-your-own-model door (pipeline/own_sample.py): CT-012 to CT-014.

The two committed examples carry a known truth (pipeline/io/examples.py): the development sample is calibrated by
construction; the current one comes from a shifted population, keeps the ranking and under-estimates the level by a
third. The battery must find exactly that.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pipeline import own_sample
from pipeline.io import examples

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / "data" / "examples" / "scored_sample_development.csv"
CUR = ROOT / "data" / "examples" / "scored_sample_current.csv"
LEVEL = ("pd.jeffreys", "pd.binomial", "pd.spiegelhalter")


def _light(report: dict, test_id: str, segment: str = "portfolio") -> str:
    rows = [t for t in report["tests"] if t["test_id"] == test_id and t["segment"] == segment]
    assert len(rows) == 1, f"{test_id}/{segment}: {len(rows)} rows"
    return rows[0]["light"]


def test_examples_regenerate_identically(tmp_path: Path) -> None:
    """CT-012: the committed examples are a pure function of the seed."""
    for path in examples.write_examples(tmp_path):
        assert path.read_bytes() == (ROOT / "data" / "examples" / path.name).read_bytes(), path.name


def test_calibrated_sample_passes_the_level_tests() -> None:
    """CT-013: the sample calibrated by construction is green on every level test, and nothing is red."""
    report = own_sample.validate_own(DEV, model_id="dev")
    assert report["sample"]["contract"]["counts"]["accepted"] == 2000
    for test_id in LEVEL:
        assert _light(report, test_id) == "green", test_id
    assert "red" not in report["lights"]
    # without a reference, the tests that compare against the development are not run
    assert not any(t["test_id"] in ("stability.psi", "disc.auc_vs_initial", "rating.hhi") for t in report["tests"])


def test_shifted_underestimated_sample_is_found() -> None:
    """CT-013: the current sample is shifted (PSI), still ranks (AUC against the initial), and under-estimates."""
    report = own_sample.validate_own(CUR, reference=DEV, model_id="current")
    assert _light(report, "stability.psi") == "red"
    psi = next(t for t in report["tests"] if t["test_id"] == "stability.psi")
    assert psi["statistic"] < 0.10  # inside the conventional band, still detected by the benchmark
    assert _light(report, "disc.auc_vs_initial") == "green"
    for test_id in LEVEL:
        assert _light(report, test_id) == "red", test_id


def test_contract_rejects_before_the_battery(tmp_path: Path) -> None:
    """CT-014: a record outside contract 1 is rejected with its reason and never reaches the battery."""
    lines = DEV.read_text(encoding="utf-8").splitlines()
    bad = lines[1].split(",")
    bad[3] = "1.2"  # a PD outside (0, 1)
    lines[1] = ",".join(bad)
    sample = tmp_path / "with_one_bad_row.csv"
    sample.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    report = own_sample.validate_own(sample, model_id="bad-row")
    counts = report["sample"]["contract"]["counts"]
    assert counts["rejected"] == 1 and counts["accepted"] == 1999
    assert report["sample"]["battery_records"] == 1999
    example = report["sample"]["contract"]["examples"][0]
    assert example["field"] == "pd" and example["value"] == "1.2"


def test_report_never_written_inside_the_repository(tmp_path: Path) -> None:
    """CT-014: the report goes outside the repository, never into data/."""
    report = own_sample.validate_own(DEV, model_id="dev")
    with pytest.raises(own_sample.OwnSampleError):
        own_sample.write_report(report, ROOT / "data" / "derived")
    path = own_sample.write_report(report, tmp_path / "reports")
    assert path.exists() and path.parent == (tmp_path / "reports").resolve()


def test_needs_a_pd_and_both_classes(tmp_path: Path) -> None:
    no_pd = tmp_path / "no_pd.csv"
    no_pd.write_bytes(b"id,observation_date,target\nA1,2025-12-31,0\nA2,2025-12-31,1\n")
    with pytest.raises(own_sample.OwnSampleError, match="pd"):
        own_sample.validate_own(no_pd)
    one_class = tmp_path / "one_class.csv"
    one_class.write_bytes(b"id,observation_date,target,pd\nA1,2025-12-31,0,0.1\nA2,2025-12-31,0,0.2\n")
    with pytest.raises(own_sample.OwnSampleError, match="defaults and non-defaults"):
        own_sample.validate_own(one_class)
