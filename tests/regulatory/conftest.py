from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def built():
    """The document in memory, built by the bake through the engine."""
    from pipeline.regulatory import bake

    return bake.build()
