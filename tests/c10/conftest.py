"""Fixtures of the C10 tests (ADR-0074: seconds, a committed sample of the Board's page, a small ladder; the full bake is run
locally and committed, never run in CI)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tests" / "contracts_u7"))
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
from c10_support import SAMPLE, SCALE, SEED, TYPES  # noqa: E402


@pytest.fixture(scope="session")
def table():
    from pipeline.cases.c10 import fed

    return fed.read_table(SAMPLE)


@pytest.fixture(scope="session")
def raw():
    from pipeline.cases.c10 import fed

    return fed.raw_record(SAMPLE)


@pytest.fixture(scope="session")
def built(table, raw):
    """The five loan-type documents, the two grids and the models document at the test size, in memory."""
    from pipeline.cases.c10 import bake

    return bake.build(SEED, SCALE, table, raw, only=TYPES, lengths=(22, 40))
