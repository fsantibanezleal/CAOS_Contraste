"""Fixtures of the C09 tests (ADR-0074: seconds, a small plan; the full bake is committed, never run in CI)."""
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
    """The six level documents and the models document at the test size, in memory."""
    from pipeline.cases.c09 import bake

    return bake.build(SEED, SCALE)


@pytest.fixture(scope="session")
def outs(built):
    return {vid: doc["outputs"] for vid, doc in built["variants"].items()}
