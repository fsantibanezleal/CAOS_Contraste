"""Fixtures of the C14 tests (ADR-0074: seconds; the full bake is committed, the tests that need the raw files run where the device
data root holds them and are skipped where it does not)."""
from __future__ import annotations

import pytest
from c14_support import SEED, SMALL_PATHS, data_root


@pytest.fixture(scope="session")
def built():
    """The three variants and the models document at the test size (2000 paths), in memory."""
    from pipeline.cases.c14 import bake

    return bake.build(SEED, data_root(), n_paths=SMALL_PATHS)
