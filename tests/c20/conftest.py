"""Fixtures of the C20 tests (ADR-0074: no bake in CI; the baking tests need the device data root and are skipped without it)."""
from __future__ import annotations

import pytest
from c20_support import ROOT, data_root


@pytest.fixture(scope="session")
def root():
    r = data_root()
    if r is None:
        pytest.skip("the device data root with the C20 raw files is not available (CONTRASTE_DATA)")
    return r


@pytest.fixture(autouse=True)
def _real_licence_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    """The suite-wide sandbox points the licence manifest at an empty file so that no test writes the committed one. The baking tests only
    read it (the pinned bytes of the UCI files), so they read the committed one; a write would still go through ``manifest_path``."""
    from pipeline.io import fetch

    monkeypatch.setattr(fetch, "MANIFEST", ROOT / "data" / "sources" / "manifest.json")
