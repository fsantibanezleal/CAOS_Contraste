"""CT-1011: the bake is a pure function of its seed."""
from __future__ import annotations

import hashlib
from pathlib import Path

from pipeline.cases.c09 import CASE
from pipeline.pipeline import PipelinePaths


def hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def test_two_bakes_with_the_same_seed_write_the_same_bytes(tmp_path: Path) -> None:
    a, b, c = tmp_path / "a", tmp_path / "b", tmp_path / "c"
    CASE.bake(42, PipelinePaths.from_output(a), None, 0.02)
    CASE.bake(42, PipelinePaths.from_output(b), None, 0.02)
    CASE.bake(43, PipelinePaths.from_output(c), None, 0.02)
    ha, hb, hc = hashes(a), hashes(b), hashes(c)
    assert ha == hb and len(ha) == 9           # six levels, the models, the checksums, the manifest
    assert ha["C09/level-3.json"] != hc["C09/level-3.json"]
    assert (a / "manifests" / "C09.json").read_bytes() == (b / "manifests" / "C09.json").read_bytes()
