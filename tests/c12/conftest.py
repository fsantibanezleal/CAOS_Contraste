"""Fixtures of the C12 tests: one small build in memory (ORE included), shared by the session."""
from __future__ import annotations

from pathlib import Path

import pytest
from c12_support import SEED, SMALL, data_root


@pytest.fixture(scope="session")
def built(tmp_path_factory: pytest.TempPathFactory):
    """The six variants and the models document at the test size, in memory; ORE's runs go to a temporary folder."""
    from pipeline.cases.c12 import bake

    work = tmp_path_factory.mktemp("c12-ore")
    return bake.build(SEED, data_root(), work_dir=Path(work), **SMALL)
