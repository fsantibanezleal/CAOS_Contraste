"""Constants and helpers shared by the C18 tests (a uniquely named module: several units ship a ``conftest`` of their own)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (HERE, ROOT / "tests" / "contracts", ROOT / "data-pipeline"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
SEED = 42
SMALL_DRAWS = 20_000
SMALL_PATHS = 2_000
DERIVED = ROOT / "data" / "derived"
C18 = DERIVED / "C18"
NEEDED = ("fed-scenarios", "fed-chargeoff", "bcch-f072-eur")


def _find_data_root() -> Path | None:
    cand = os.environ.get("CONTRASTE_DATA")          # the device data root by role; never a drive written here
    if cand and all((Path(cand) / "raw" / f).exists() for f in NEEDED):
        return Path(cand)
    return None


# resolved once, at import: the suite's sandbox fixture (tests/conftest.py) removes CONTRASTE_DATA from every test's environment
_DATA_ROOT = _find_data_root()


def data_root() -> Path | None:
    return _DATA_ROOT


requires_raw = pytest.mark.skipif(data_root() is None, reason="the raw Federal Reserve and BCCh files are not in the device data root")


def semantics():
    from pipeline.cases.c18 import bake

    return bake._semantics()
