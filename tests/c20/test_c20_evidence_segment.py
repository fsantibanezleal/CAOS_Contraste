"""U16-R3 c20 M2: a finding cites a test row of no model by its segment (``test@-@segment``), and the artifact check accepts it."""
from __future__ import annotations

from pipeline.cases.c20.ops import evidence_id


def test_a_row_of_no_model_is_cited_by_its_segment() -> None:
    row = {"test_id": "stability.chi2", "model_id": None, "segment": "typical>higher-risk:interest_rate"}
    assert evidence_id(row) == "stability.chi2@-@typical>higher-risk:interest_rate"


def test_a_row_with_a_model_keeps_its_form() -> None:
    assert evidence_id({"test_id": "ml.overfit", "model_id": "P4-lightgbm-polish", "segment": "train-vs-holdout"}) == "ml.overfit@P4-lightgbm-polish@train-vs-holdout"
    assert evidence_id({"test_id": "ml.overfit", "model_id": None, "segment": None}) == "ml.overfit"
