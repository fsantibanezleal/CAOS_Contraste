"""Fixtures of the C13 tests (ADR-0074: seconds, a small replication count; the full bake is committed, never run in CI)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tests" / "contracts_u8"))   # producer_checks and market_math of the reviewed contracts
SCALE = 0.05                                               # 50 replications per variant
SEED = 13


@pytest.fixture(scope="session")
def built():
    """The six variant documents and the models document at the test size, in memory."""
    from pipeline.cases.c13 import bake

    return bake.build(SEED, SCALE)
