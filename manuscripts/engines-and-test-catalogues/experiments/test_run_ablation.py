"""Measurement contract of ``run_ablation.run_layers``: a layer detects a defect only when its checks report it.

An exception that is not a failed check (a ``MemoryError``, an import error) is a failed run: it is retried, and when it persists it is
raised as ``LayerRunError`` and never recorded as a detection.

    python -m pytest manuscripts/engines-and-test-catalogues/experiments/test_run_ablation.py
"""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_ablation as ab  # noqa: E402


def layers(**fns):
    return {k: (k, fn) for k, fn in fns.items()}


def test_a_failed_check_is_a_detection():
    out = ab.run_layers(layers(A=lambda: [True, False], B=lambda: [True, True]))
    assert out == {"A": True, "B": False}
    assert ab.RAISED == {}


def test_an_unrelated_exception_is_not_a_detection():
    def boom():
        raise MemoryError("the machine is out of memory")

    with pytest.raises(ab.LayerRunError) as err:
        ab.run_layers(layers(A=lambda: [True], C=boom), retries=1, pause=0.0)
    assert "C" in str(err.value) and "MemoryError" in str(err.value)


def test_a_transient_exception_is_retried_and_the_retry_decides():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise MemoryError("transient")
        return [True]

    out = ab.run_layers(layers(C=flaky), retries=1, pause=0.0)
    assert out == {"C": False}  # the retry passed its checks: not a detection
    assert calls["n"] == 2
    assert ab.RETRIED == {"C": "MemoryError"}


def test_a_retry_that_fails_its_check_is_a_detection():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise ImportError("transient")
        return [False]

    assert ab.run_layers(layers(C=flaky), retries=1, pause=0.0) == {"C": True}


def test_the_released_engine_must_pass_every_layer():
    with pytest.raises(ab.LayerRunError):
        ab.require_clean("baseline", {"A": False, "B": True})
    ab.require_clean("baseline", {"A": False, "B": False})
