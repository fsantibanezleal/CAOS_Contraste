"""The contract tests read committed JSON only: they need neither the pipeline nor its numerical engines, so the
parent conftest's sandbox fixture (which imports the pipeline) is replaced by a no-op here. The parent's
session-level guard (no committed file under data/ or models/ changes during the run) still applies."""
import pytest


@pytest.fixture(autouse=True)
def _sandboxed_pipeline() -> None:
    return None
