"""M15 T6 second fix: three literals the constant baseline had to carry are rewritten against their one source.

- C20: a subsample run (the tests) records the declared range of each observable and never compares it with a stand-in interval
  of its own; the release bake still checks the declared ranges.
- C02 and C21: the expected range of a result is chosen by an explicit prefix and an unknown key raises (no fallback to one range).
- C15 page: the EIVE threshold the executive brief reads is the model's own threshold, not a copy.

M15 T6 third fix (review F2 and F6): no planted or subsample run compares its results with an interval the case did not declare.
The C02 planted run (the same defect class as the C20 stand-in) records the declared ranges and compares none; the guards below
refuse ANY fixed interval in those paths and assert what `expectations.check` is called with.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

from pipeline.cases.c02 import bake as c02
from pipeline.cases.c15 import models as c15_models
from pipeline.cases.c15 import page as c15_page
from pipeline.cases.c20 import bake as c20
from pipeline.cases.c21 import bake as c21
from pipeline.core import expect as expectations

PIPELINE = Path(__file__).resolve().parents[1] / "data-pipeline" / "pipeline"
sys.path.insert(0, str(Path(__file__).resolve().parent / "c02"))  # c02_support: the planted files of the C02 tests


def _literals(path: Path) -> set[float]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {float(n.value) for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)}


def _is_number(node: ast.AST) -> bool:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        node = node.operand
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool)


def _fixed_intervals(path: Path, functions: set[str]) -> list[str]:
    """Every literal pair of numbers (a tuple or list of two) written inside the named functions: a fixed interval of any size."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in functions):
        for n in ast.walk(fn):
            if isinstance(n, (ast.Tuple, ast.List)) and len(n.elts) == 2 and all(_is_number(e) for e in n.elts):
                found.append(f"{path.name}:{n.lineno} {fn.name}")
    return found


@pytest.mark.parametrize("case,functions", [("c02", {"bake_case", "expect_ranges"}), ("c10", {"bake_case"}),
                                            ("c20", {"bake_case", "expected_ranges"})])
def test_no_bake_path_writes_a_fixed_interval_of_its_own(case, functions):
    """F6: any literal interval in the bake path (not only the old magnitudes) is refused; the ranges come from the case's EXPECT."""
    assert not _fixed_intervals(PIPELINE / "cases" / case / "bake.py", functions)


def test_c20_has_no_standin_interval_in_its_bake():
    assert not {1e9, -1e9} & _literals(PIPELINE / "cases" / "c20" / "bake.py")


class _CheckSpy:
    """Replaces `expectations.check`, recording the ranges each call is given (the call itself still judges)."""

    def __init__(self, monkeypatch):
        self.calls: list[dict] = []
        real = expectations.check

        def spy(case_id, expect, values):
            self.calls.append(dict(expect))
            return real(case_id, expect, values)

        monkeypatch.setattr(expectations, "check", spy)

    def only_declared(self, declared):
        return all(all(k in declared and tuple(r) == tuple(declared[k]) for k, r in call.items()) for call in self.calls)


def test_c02_planted_run_records_the_declared_ranges_and_compares_none(tmp_path, monkeypatch):
    from c02_support import SEED, Paths, planted_root

    spy = _CheckSpy(monkeypatch)
    root, man = planted_root(tmp_path / "raw", rows=(320, 320, 320, 320, 320), shift=-0.55)
    manifest = c02.bake_case(SEED, Paths(tmp_path / "out"), root, manifest=man, check_counts=False, strict_expect=False)
    assert spy.calls == [], "a planted run compares nothing"
    declared = c02.expect_ranges(manifest["expect"])
    assert manifest["expect"] == {k: [float(lo), float(hi)] for k, (lo, hi) in sorted(declared.items())}


def test_c02_strict_run_checks_only_the_declared_ranges(monkeypatch):
    spy = _CheckSpy(monkeypatch)
    values = {"event_rate_h1": 0.05, "auc_P1_h1": 0.8, "overfit_gap_P1_h1": 0.1}
    declared = c02.expect_ranges(values)
    assert expectations.check("C02", declared, values)
    assert spy.only_declared(declared)
    assert not spy.only_declared({k: (-1.0, 1.0) for k in values})


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

def test_c20_subsample_compares_nothing_and_a_release_run_compares_only_the_declared_ranges(monkeypatch):
    spy = _CheckSpy(monkeypatch)
    values = {k: (lo + hi) / 2 for k, (lo, hi) in c20.EXPECT.items()}
    c20.expected_ranges({**values, "auc_holdout_taiwan_P4-lightgbm": 0.5}, 1200)
    assert spy.calls == []
    c20.expected_ranges(values, None)
    assert len(spy.calls) == 1 and spy.only_declared(c20.EXPECT)


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
