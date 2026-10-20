"""Fixtures of the C21 tests (ADR-0074: seconds; the full bake is committed and the planted bake runs on small synthetic files)."""
from __future__ import annotations

import pytest
from c21_support import planted_root  # noqa: F401  (puts the pipeline and the contract test folders on the path)


@pytest.fixture(scope="session")
def root(tmp_path_factory):
    """A data root of planted files for the seven years, written by the real fetch."""
    return planted_root(tmp_path_factory.mktemp("c21-root"))


@pytest.fixture(scope="session")
def built(root):
    """The six pair documents and the models document of the planted files, in memory."""
    from c21_support import SEED

    from pipeline.cases.c21 import bake

    return bake.build(SEED, root)

