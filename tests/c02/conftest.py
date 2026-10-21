"""Fixtures of the C02 tests (ADR-0074: the full bake is committed; the planted bake runs on small synthetic files)."""
from __future__ import annotations

import pytest
from c02_support import SEED, planted_root  # noqa: F401  (puts the pipeline and the contract test folders on the path)


@pytest.fixture(scope="session")
def planted(tmp_path_factory):
    """(data root, licence manifest) of the planted zip."""
    return planted_root(tmp_path_factory.mktemp("c02-root"))


@pytest.fixture(scope="session")
def built(planted):
    """The six horizon documents and the models document of the planted files, in memory."""
    from pipeline.cases.c02 import bake

    root, manifest = planted
    return bake.build(SEED, root, manifest=manifest, check_counts=False)
