"""CT-1817: the Missing data paragraph of the sizing."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from c18_support import DERIVED, SEED, SMALL_DRAWS, SMALL_PATHS, data_root, requires_raw

from pipeline.cases.c18 import anchors, bake, fetch


def _root(tmp: Path, folders: tuple[str, ...]) -> Path:
    for f in folders:
        shutil.copytree(Path(data_root()) / "raw" / f, tmp / "raw" / f)
    return tmp


@requires_raw
def test_a_missing_optional_source_skips_its_variant_and_a_missing_required_one_stops_the_case(tmp_path: Path) -> None:
    # no NGFS runs and no EBA workbook: the other four variants are written and the two skipped ones name their URL
    root = _root(tmp_path / "a", (fetch.FED_HIST_DIR, fetch.CHARGEOFF_DIR, fetch.FX_DIR))
    b = bake.build(SEED, root, n_draws=SMALL_DRAWS, n_paths=SMALL_PATHS)
    assert set(b.skipped) == {"eba", "ngfs"}
    assert fetch.EBA_URL in b.skipped["eba"] and "IXSE_NGFS_PHASE_5" not in b.skipped["ngfs"] and fetch.NGFS_BASE in b.skipped["ngfs"]
    assert set(b.variants) == {"baseline", "fed-2026-severely-adverse", "t-copula-baseline", "reverse-stress"}
    # an absent Federal Reserve table stops C18 whole, naming the URL
    with pytest.raises(FileNotFoundError) as exc:
        bake.build(SEED, _root(tmp_path / "b", (fetch.CHARGEOFF_DIR, fetch.FX_DIR)), n_draws=SMALL_DRAWS, n_paths=SMALL_PATHS)
    assert "fed-scenarios" in str(exc.value) or "provenance" in str(exc.value)
    # an absent EUR to CLP series stops C18 whole
    with pytest.raises(FileNotFoundError):
        bake.build(SEED, _root(tmp_path / "c", (fetch.FED_HIST_DIR, fetch.CHARGEOFF_DIR)), n_draws=SMALL_DRAWS, n_paths=SMALL_PATHS)
    # a missing committed document of C07, C15 or C17 stops C18 whole
    needed = ("C07/base.json", "C07/models-banco-andino.json", "manifests/C15.json", "C15/long-uf.json", "C15/models-banco-andino-2026-09.json",
              "C17/models-generator.json", "C11/mixed-2023.json")
    for doc in needed[:3] + needed[4:6]:
        derived = tmp_path / "derived" / doc.replace("/", "_")
        for rel in needed:
            (derived / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(DERIVED / rel, derived / rel)
        anchors.load_anchors(derived)                                  # complete: it loads
        (derived / doc).unlink()
        with pytest.raises(anchors.MissingDocument, match=doc.split("/")[-1]):
            anchors.load_anchors(derived)
    with pytest.raises(FileNotFoundError):
        bake.build(SEED, None)
