"""CT-1109: the bake is a pure function of its seed."""
from __future__ import annotations

import hashlib
from pathlib import Path

from c10_support import ONE_TYPE, SAMPLE

from pipeline.cases.c10 import CASE_C10
from pipeline.pipeline import PipelinePaths

SMALL = 0.002


def hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def bake(root: Path, seed: int) -> None:
    CASE_C10.bake(seed, PipelinePaths.from_output(root), None, SMALL, page=SAMPLE, only=ONE_TYPE, lengths=())


def test_two_bakes_with_the_same_seed_write_the_same_bytes(tmp_path: Path) -> None:
    a, b, c = tmp_path / "a", tmp_path / "b", tmp_path / "c"
    bake(a, 42)
    bake(b, 42)
    bake(c, 43)
    ha, hb, hc = hashes(a), hashes(b), hashes(c)
    assert ha == hb and len(ha) == 5            # the models, the loan type, the checksums, the sources, the manifest
    assert ha["C10/credit-cards.json"] != hc["C10/credit-cards.json"]
    assert (a / "manifests" / "C10.json").read_bytes() == (b / "manifests" / "C10.json").read_bytes()
