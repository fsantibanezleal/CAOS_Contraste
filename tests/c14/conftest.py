"""Fixtures of the C14 tests (ADR-0074: seconds; the full bake is committed, the tests that need the raw files run where the device
data root holds them and are skipped where it does not)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
sys.path.insert(0, str(ROOT / "tests" / "contracts_u10"))
SEED = 42
SMALL_PATHS = 2000


def data_root() -> Path | None:
    for cand in (os.environ.get("CONTRASTE_DATA"), "E:/_Datos/contraste"):
        if cand and (Path(cand) / "raw" / "fdic-financials").exists() and (Path(cand) / "raw" / "treasury-par").exists():
            return Path(cand)
    return None


requires_raw = pytest.mark.skipif(data_root() is None, reason="the raw FDIC and Treasury files are not in the device data root")


@pytest.fixture(scope="session")
def built():
    """The three variants and the models document at the test size (2000 paths), in memory."""
    from pipeline.cases.c14 import bake

    return bake.build(SEED, data_root(), n_paths=SMALL_PATHS)
