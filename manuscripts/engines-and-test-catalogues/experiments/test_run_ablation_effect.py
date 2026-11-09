"""The z of the full-size comparison of the planted loading defect is the manuscript's z: engine minus reference over its standard error.

    python -m pytest manuscripts/engines-and-test-catalogues/experiments/test_run_ablation_effect.py
"""
from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_ablation_effect as eff  # noqa: E402


def test_z_has_the_sign_of_engine_minus_reference():
    assert eff.z_difference(99.0, 1.0, 100.0, 1.0, 10) < 0 < eff.z_difference(101.0, 1.0, 100.0, 1.0, 10)


def test_z_value():
    assert math.isclose(eff.z_difference(102.0, 3.0, 100.0, 4.0, 10), 2.0 / math.sqrt(25.0 / 10.0))


def test_the_full_size_comparison_has_the_size_of_the_main_comparison():
    import json
    mc = json.loads((eff.HERE / "results_portfolio.json").read_text(encoding="utf-8"))["mc"]
    assert (eff.FS_R, eff.FS_N) == (mc["replications"], mc["scenarios_each"])
