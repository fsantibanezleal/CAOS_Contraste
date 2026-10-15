"""Constants and helpers shared by the C14 tests (a uniquely named module: several units ship a ``conftest`` of their own)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (HERE, ROOT / "tests" / "contracts", ROOT / "tests" / "contracts_u10"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
SEED = 42
SMALL_PATHS = 2000


def data_root() -> Path | None:
    for cand in (os.environ.get("CONTRASTE_DATA"),):   # the device data root by role; never a drive written here
        if cand and (Path(cand) / "raw" / "fdic-financials").exists() and (Path(cand) / "raw" / "treasury-par").exists():
            return Path(cand)
    return None


requires_raw = pytest.mark.skipif(data_root() is None, reason="the raw FDIC and Treasury files are not in the device data root")
