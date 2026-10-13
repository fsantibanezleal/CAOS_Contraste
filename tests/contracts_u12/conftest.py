"""The U12-S contract tests read committed JSON and markdown only: the parent conftest's sandbox fixture (which imports
the pipeline) is replaced by a no-op, and the contract helpers of tests/contracts are put on the import path."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "contracts"))


@pytest.fixture(autouse=True)
def _sandboxed_pipeline() -> None:
    return None
