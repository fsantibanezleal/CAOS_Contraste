"""Fixtures of the C07 tests (ADR-0074: seconds, a small portfolio; no bake in CI)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[1]
SCALE = 0.02
SEED = 42


@pytest.fixture(scope="session")
def built():
    """The six variants and the models document at the test size, in memory."""
    from pipeline.cases.c07 import bake

    return bake.build(SEED, SCALE)


@pytest.fixture(scope="session")
def outs(built):
    return {sid: doc["outputs"] for sid, doc in built["variants"].items()}
