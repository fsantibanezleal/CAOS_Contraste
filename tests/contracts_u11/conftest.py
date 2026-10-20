"""The U11-S contract tests read committed JSON and markdown only: the parent conftest's sandbox fixture (which imports
the pipeline) is replaced by a no-op, and the contract helpers of tests/contracts are put on the import path."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "contracts"))

# pytest puts this folder at the front of sys.path while it loads this conftest, at the start of the run. Another suite's bare
# `import semantics` (the C14 tests import the one of tests/contracts_u10) would then find this folder's checker. The folder leaves
# the path here; pytest puts it back when it imports a test module of the folder, and these tests load their checker by its path.
_HERE = str(Path(__file__).resolve().parent)
while _HERE in sys.path:
    sys.path.remove(_HERE)


@pytest.fixture(autouse=True)
def _sandboxed_pipeline() -> None:
    return None
