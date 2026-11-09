"""The source string of C06's staging policy says what the file lacks, not a claim about its dates.

The technical report's review found the clause "the reporting dates are a year apart" false (the reporting dates of the file are the
quarter ends the samples are drawn at); the string says "the file has no cure dates" and nothing about the dates. The committed
documents are checked as committed (no test bakes the case, ADR-0074)."""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.cases.c06 import models, run

ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILES = (ROOT / "data-pipeline" / "pipeline" / "cases" / "c06" / "models.py", ROOT / "data-pipeline" / "pipeline" / "cases" / "c06" / "run.py")
EXPECTED_TAIL = "no probation (the file has no cure dates)"


def test_the_producer_and_its_comment_have_no_dates_clause():
    for p in SOURCE_FILES:
        text = " ".join(p.read_text(encoding="utf-8").split())
        assert "a year apart" not in text and "reporting dates are" not in text, p.name


def test_the_source_string_the_producer_writes_ends_on_the_cure_dates_clause():
    text = " ".join(Path(models.__file__).read_text(encoding="utf-8").split())
    assert EXPECTED_TAIL + '"' in text.replace('" "', "")
    assert run.POLICY.probation_months == 0


def test_every_committed_c06_models_document_carries_the_new_source_string():
    docs = sorted((ROOT / "data" / "derived" / "C06").glob("models-*.json"))
    assert docs
    for p in docs:
        source = json.loads(p.read_text(encoding="utf-8"))["fit"]["staging_policy"]["source"]
        assert source.endswith(EXPECTED_TAIL + ")") or source.endswith(EXPECTED_TAIL), p.name
        assert "year apart" not in source and "dates are" not in source, p.name
