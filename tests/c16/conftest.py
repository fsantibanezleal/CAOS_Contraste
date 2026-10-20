"""Fixtures of the C16 tests (ADR-0074: seconds; the full bake is committed, the tests that need the raw files run where the device
data root holds them and are skipped where it does not). The unit tests run on the committed samples in ``tests/c16/data``."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))


def _find_data_root() -> Path | None:
    cand = os.environ.get("CONTRASTE_DATA")   # the device data root by role; never a drive written here
    if cand and all((Path(cand) / "raw" / d).exists() for d in ("fdic-financials", "treasury-par", "fed-h8")):
        return Path(cand)
    return None


# resolved once, at import: the suite's sandbox fixture (tests/conftest.py) removes CONTRASTE_DATA from every test's environment
DATA_ROOT = _find_data_root()
requires_raw = pytest.mark.skipif(DATA_ROOT is None, reason="the raw FDIC, H.8 and Treasury files are not in the device data root")


@pytest.fixture(scope="session")
def built():
    """The seven documents of the committed samples at the test size, in memory."""
    from .helpers import built_sample

    return built_sample(True)
