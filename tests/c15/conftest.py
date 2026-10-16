"""Fixtures of the C15 tests (ADR-0074: seconds; the full bake is committed, the tests that need the raw files run where the device
data root holds them and are skipped where it does not)."""
from __future__ import annotations

import pytest
from c15_support import SEED, data_root


@pytest.fixture(scope="session")
def built():
    """The six variants and the models document, in memory, from the raw files of the device data root."""
    from pipeline.cases.c15 import bake

    return bake.build(SEED, data_root(), n_paths=2000)
