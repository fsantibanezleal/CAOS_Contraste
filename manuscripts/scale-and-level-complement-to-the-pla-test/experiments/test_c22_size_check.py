"""Tests of the cross-check of the Christoffersen comparator against the committed C22 documents. Run from the repository root:

    python -m pytest manuscripts/scale-and-level-complement-to-the-pla-test/experiments/test_c22_size_check.py -q
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import c22_size_check as cc  # noqa: E402


def _committed() -> dict:
    doc = json.loads(cc.C22_DOC.read_text(encoding="utf-8"))
    return next(s for s in doc["outputs"]["simulations"] if s["key"] == cc.KEY)["rates"]


def test_wilson_matches_the_committed_interval():
    """The interval of this script is the one the C22 document carries for the same count."""
    r = _committed()["p<0.05"]
    lo, hi = cc.wilson(r["rejections"], r["n"])
    assert lo == pytest.approx(r["wilson_low"], abs=1e-6)
    assert hi == pytest.approx(r["wilson_high"], abs=1e-6)


def test_two_proportion_z_is_zero_for_equal_rates_and_signed():
    assert cc.two_prop_z(10, 100, 10, 100) == 0.0
    assert cc.two_prop_z(20, 100, 10, 100) > 0 > cc.two_prop_z(10, 100, 20, 100)


def test_size_is_reproducible_and_counts_every_replication():
    a = cc.size(250, 0.025, 60, np.random.default_rng(5))
    b = cc.size(250, 0.025, 60, np.random.default_rng(5))
    assert a == b
    assert a["reps"] == 60 and a["undefined"] >= 0 and a["p<0.05"]["k"] >= a["p<0.01"]["k"]


def test_rerun_agrees_with_the_committed_c22_size():
    """The committed result of the script: the engine function reproduces the C22 size on the C22 design."""
    out = json.loads((cc.HERE / "c22_size_check.json").read_text(encoding="utf-8"))
    for rule, cmp in out["c22_vs_rerun"].items():
        assert cmp["intervals_overlap"], rule
        assert abs(cmp["z"]) < 1.96, rule
        assert cmp["committed"]["k"] == _committed()[rule]["rejections"]
