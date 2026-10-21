"""The governance suite: the bake is built once per session over the committed documents (seconds), and the helpers sit on the import path.

The parent conftest points the pipeline's canonical roots at a temporary directory for every test; the governance bake reads the repository's
committed documents through its own root (``readers.REPO_ROOT``) and writes only where a test tells it to.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))


@pytest.fixture(scope="session")
def baked():
    """The bake in memory: ``Baked`` with the inventory, the findings, the appetite, the reports, the manifest and the page block."""
    from pipeline.governance import bake

    return bake.build()
