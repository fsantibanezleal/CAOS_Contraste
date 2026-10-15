"""Fixtures of the C11 tests: synthetic raw files in the real formats (``sim.py``), read once per session, and the tiny
hyperparameters of a test bake. No test bakes the real data (ADR-0074)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "data-pipeline"))
sys.path.insert(0, str(ROOT / "tests" / "contracts_u8"))
sys.path.insert(0, str(HERE))

import sim  # noqa: E402


@pytest.fixture(scope="session")
def data_root(tmp_path_factory):
    return sim.make_raw(tmp_path_factory.mktemp("c11-raw"))


@pytest.fixture(scope="session")
def series(data_root):
    from pipeline.cases.c11 import bake as _case

    return _case.load_series(data_root)


@pytest.fixture(scope="session")
def tiny():
    """The hyperparameters of a test bake: short windows and few starts so the ladder runs in seconds. The values are the
    machinery of a small run, not the fixed hyperparameters of the real bake."""
    from pipeline.cases.c11.forecast import Hyper

    return Hyper(estimation_window_days=500, ewma_lambda=0.94, age_weight_lambda=0.98, evt_threshold_fraction=0.10,
                 garch_refit_every_days=10, caviar_refit_every_days=100, gas_refit_every_days=100, caviar_n_starts=2, gas_n_starts=2,
                 seed=42)
