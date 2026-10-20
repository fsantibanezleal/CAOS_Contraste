"""CT-2018: the bake is a pure function of its inputs and the seed."""
from __future__ import annotations

from pathlib import Path

from c20_support import SEED, SUBSAMPLE, Paths, files

from pipeline.cases.c20 import bake


def test_two_bakes_of_the_same_inputs_and_seed_write_the_same_bytes(root, tmp_path: Path) -> None:
    a, b = Paths(tmp_path / "a"), Paths(tmp_path / "b")
    ma = bake.bake_case(SEED, a, root, max_rows=SUBSAMPLE)
    mb = bake.bake_case(SEED, b, root, max_rows=SUBSAMPLE)
    fa, fb = files(a.root), files(b.root)
    assert fa == fb and ma == mb
    assert {f"C20/{v}.json" for v in bake.VARIANTS} | {"C20/models-c20-ladder.json", "C20/SHA256SUMS.txt", "C20/raw-sources.txt", "manifests/C20.json"} <= set(fa)
    assert [e["variant_id"] for e in ma["artifacts"] if e["role"] == "variant"] == list(bake.VARIANTS)
