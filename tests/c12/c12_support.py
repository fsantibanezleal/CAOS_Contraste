"""Constants and helpers shared by the C12 tests (a uniquely named module: several units ship a ``conftest`` of their own)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def _load_checker(path: Path, name: str):
    import importlib.util

    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


for _p in (HERE, ROOT / "tests" / "contracts", ROOT / "tests" / "contracts_u9"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
#: the cross-field checker of contracts_u9, loaded from its file under a name of its own: several contract folders ship a
#: ``semantics`` module, and a plain ``import semantics`` gets whichever suite loaded first in one pytest session
semantics = _load_checker(ROOT / "tests" / "contracts_u9" / "semantics.py", "semantics_contracts_u9")
SEED = 42
#: the test size: the bake at a few thousand paths and a stride of twelve months through the backtest dates (ADR-0074: local only)
SMALL = {"n_paths": 2000, "bt_paths": 500, "crit_count": 100, "ore_samples": 300, "date_stride": 12}


def _find_data_root() -> Path | None:
    cand = os.environ.get("CONTRASTE_DATA")   # the device data root by role; never a drive written here
    if cand and (Path(cand) / "raw" / "treasury-par").exists() and (Path(cand) / "raw" / "treasury-hqm").exists():
        return Path(cand)
    return None


# resolved once, at import: the suite's sandbox fixture (tests/conftest.py) removes CONTRASTE_DATA from every test's environment
_DATA_ROOT = _find_data_root()


def data_root() -> Path | None:
    return _DATA_ROOT


requires_raw = pytest.mark.skipif(data_root() is None, reason="the raw Treasury and HQM files are not in the device data root")
