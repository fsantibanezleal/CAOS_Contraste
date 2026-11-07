"""A rerun reproduces the reference only when every layer detects the same defects; a difference is reported, never averaged away.

    python -m pytest manuscripts/engines-and-test-catalogues/experiments/test_compare_ablation_runs.py
"""
from __future__ import annotations

import copy
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import compare_ablation_runs as cmp  # noqa: E402


def doc(rows):
    return {"baseline_false_alarms": {k: False for k in "ABCDE"}, "after_restore": {k: False for k in "ABCDE"}, "retries": [],
            "mutants": [{"id": i, "detected_by": {k: k in det for k in "ABCDE"}} for i, det in rows]}


def test_identical_matrices_reproduce():
    a = doc([("m01", "B"), ("m02", "A")])
    out = cmp.compare(a, [copy.deepcopy(a)])
    assert out["reproduced"] == out["reruns"] == 1 and out["per_run"][1]["differences"] == {}


def test_a_changed_cell_is_a_difference():
    a = doc([("m01", "B"), ("m02", "A")])
    b = doc([("m01", "B"), ("m02", "AC")])
    out = cmp.compare(a, [b])
    assert out["reproduced"] == 0 and out["per_run"][1]["differences"] == {"m02": ["A", "AC"]}


def test_a_false_alarm_in_a_rerun_is_not_a_reproduction():
    a = doc([("m01", "B")])
    b = doc([("m01", "B")])
    b["after_restore"]["C"] = True
    assert cmp.compare(a, [b])["reproduced"] == 0
