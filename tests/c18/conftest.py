"""Fixtures of the C18 tests (ADR-0074: seconds; the full bake is committed, the tests that need the raw files run where the device
data root holds them and are skipped where it does not)."""
from __future__ import annotations

import pytest
from c18_support import SEED, SMALL_DRAWS, SMALL_PATHS, data_root


@pytest.fixture(scope="session")
def built():
    """The variants and the models document at the test size, in memory."""
    from pipeline.cases.c18 import bake

    return bake.build(SEED, data_root(), n_draws=SMALL_DRAWS, n_paths=SMALL_PATHS)
