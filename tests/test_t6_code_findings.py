"""M15 T6 second fix: three literals the constant baseline had to carry are rewritten against their one source.

- C20: a subsample run (the tests) records the declared range of each observable and never compares it with a stand-in interval
  of its own; the release bake still checks the declared ranges.
- C02 and C21: the expected range of a result is chosen by an explicit prefix and an unknown key raises (no fallback to one range).
- C15 page: the EIVE threshold the executive brief reads is the model's own threshold, not a copy.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from pipeline.cases.c02 import bake as c02
from pipeline.cases.c15 import models as c15_models
from pipeline.cases.c15 import page as c15_page
from pipeline.cases.c20 import bake as c20
from pipeline.cases.c21 import bake as c21
from pipeline.core import expect as expectations

PIPELINE = Path(__file__).resolve().parents[1] / "data-pipeline" / "pipeline"


def _literals(path: Path) -> set[float]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {float(n.value) for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)}


def test_c20_has_no_standin_interval_in_its_bake():
    assert not {1e9, -1e9} & _literals(PIPELINE / "cases" / "c20" / "bake.py")


def test_c20_release_bake_checks_the_declared_ranges():
    values = {k: (lo + hi) / 2 for k, (lo, hi) in c20.EXPECT.items()}
    ranges = c20.expected_ranges(values, None)
    assert ranges == {k: [float(lo), float(hi)] for k, (lo, hi) in c20.EXPECT.items()}
    values["auc_holdout_taiwan_P4-lightgbm"] = 0.5
    with pytest.raises(expectations.ExpectationError):
        c20.expected_ranges(values, None)


def test_c20_subsample_records_the_declared_ranges_not_a_standin():
    values = {k: (lo + hi) / 2 for k, (lo, hi) in c20.EXPECT.items()}
    values["auc_holdout_taiwan_P4-lightgbm"] = 0.5  # a subsample may sit outside the release range; it is not the release bake
    ranges = c20.expected_ranges(values, 1200)
    assert ranges == {k: [float(lo), float(hi)] for k, (lo, hi) in c20.EXPECT.items()}
    assert all(abs(x) < 1e6 for r in ranges.values() for x in r)


def test_c20_only_declared_keys_carry_a_range():
    ranges = c20.expected_ranges({"some_other_value": 3.0, "leak_caught": 1.0}, 1200)
    assert set(ranges) == {"leak_caught"}


@pytest.mark.parametrize("module,known", [
    (c02, {"event_rate_h1": c02.EXPECT_RATE, "auc_P1_h1": c02.EXPECT_AUC, "overfit_gap_P1_h1": c02.EXPECT_GAP}),
    (c21, {"approval_rate_2022": c21.EXPECT_APPROVAL, "black_over_white_parity_ratio_2022": c21.EXPECT_PARITY}),
])
def test_expected_range_of_each_known_prefix(module, known):
    assert module.expect_ranges({k: 0.0 for k in known}) == known


@pytest.mark.parametrize("module", [c02, c21])
def test_an_unknown_result_has_no_range_and_raises(module):
    with pytest.raises(expectations.ExpectationError, match="no expected range"):
        module.expect_ranges({"a_new_result": 0.4})


def test_c15_page_threshold_is_the_models_threshold(monkeypatch):
    models_value = {i: th for i, th, _ in c15_models.THRESHOLDS}["eve-tier1"]
    assert c15_page.eve_threshold() == models_value
    monkeypatch.setattr(c15_models, "THRESHOLDS", (("eve-tier1", 0.3, "Tier 1 capital"),))
    assert c15_page.eve_threshold() == 0.3


def test_c15_page_repeats_no_threshold_literal():
    assert 0.15 not in _literals(PIPELINE / "cases" / "c15" / "page.py")
