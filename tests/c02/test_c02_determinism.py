"""CT-0212: the bake is a pure function of its inputs."""
from __future__ import annotations

from pathlib import Path

from c02_support import SEED, Paths, planted_root

from pipeline.cases.c02 import bake

SMALL = (320, 320, 320, 320, 320)


def files(folder: Path) -> dict[str, bytes]:
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}


def test_two_bakes_of_the_same_inputs_write_the_same_bytes(tmp_path: Path) -> None:
    root, man = planted_root(tmp_path / "raw", rows=SMALL, shift=-0.55)
    a, b = Paths(tmp_path / "a"), Paths(tmp_path / "b")
    ma = bake.bake_case(SEED, a, root, manifest=man, check_counts=False, strict_expect=False)
    mb = bake.bake_case(SEED, b, root, manifest=man, check_counts=False, strict_expect=False)
    fa, fb = files(a.root), files(b.root)
    assert fa == fb and ma == mb
    expected = {f"C02/{v}.json" for v in ("h1", "h2", "h3", "h4", "h5", "pooled", "models-polish-horizons")} | {"C02/SHA256SUMS.txt", "C02/raw-sources.txt", "manifests/C02.json"}
    assert expected <= set(fa)
    assert [e["variant_id"] for e in ma["artifacts"] if e["role"] == "variant"] == ["h1", "h2", "h3", "h4", "h5", "pooled"]
    # one input changed: the documents differ, so the equality above is not vacuous
    root2, man2 = planted_root(tmp_path / "raw2", rows=SMALL, seed=SEED + 1, shift=-0.55)
    c = Paths(tmp_path / "c")
    bake.bake_case(SEED, c, root2, manifest=man2, check_counts=False, strict_expect=False)
    assert files(c.root)["C02/h1.json"] != fa["C02/h1.json"]
