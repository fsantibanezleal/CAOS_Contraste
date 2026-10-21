"""CT-2115: the bake is a pure function of its inputs."""
from __future__ import annotations

from pathlib import Path

from c21_support import SEED, Paths, planted_root

from pipeline.cases.c21 import bake


def files(folder: Path) -> dict[str, bytes]:
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}


def test_two_bakes_of_the_same_inputs_write_the_same_bytes(tmp_path: Path) -> None:
    root = planted_root(tmp_path / "raw", years=(2018, 2019, 2020), n=900)
    a, b = Paths(tmp_path / "a"), Paths(tmp_path / "b")
    ma = bake.bake_case(SEED, a, root)
    mb = bake.bake_case(SEED, b, root)
    fa, fb = files(a.root), files(b.root)
    assert fa == fb and ma == mb
    assert {"C21/pair-2018-19.json", "C21/pair-2019-20.json", "C21/models-hmda-de-2018-2023.json", "C21/SHA256SUMS.txt",
            "C21/raw-sources.txt", "manifests/C21.json"} <= set(fa)
    assert [e["variant_id"] for e in ma["artifacts"] if e["role"] == "variant"] == ["pair-2018-19", "pair-2019-20"]    # the others are blocked
