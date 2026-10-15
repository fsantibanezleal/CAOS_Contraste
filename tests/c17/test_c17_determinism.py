"""CT-1714: the bake is deterministic."""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.cases.c17 import bake, generator
from pipeline.stages.export import write_artifact

SCALE = 0.016  # sixteen histories per cell; the lightest tail index keeps the test to a few minutes


def _bytes(tmp_path: Path, name: str, seed: int) -> dict[str, bytes]:
    root = tmp_path / name
    built = bake.build(seed, SCALE, tail_indices=(0.6,), workers=4)
    for vid, doc in built["variants"].items():
        write_artifact(root, f"C17/{vid}.json", doc, exact=bake.EXACT, engines=bake.ENGINES, run_ms=bake.RUN_MS)
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_two_bakes_with_the_same_seed_write_the_same_bytes(tmp_path):
    a, b, c = _bytes(tmp_path, "a", 42), _bytes(tmp_path, "b", 42), _bytes(tmp_path, "c", 43)
    assert list(a) == ["C17/xi-0-6.json"] and a == b
    assert c["C17/xi-0-6.json"] != a["C17/xi-0-6.json"]  # another case seed moves every replication
    doc_a, doc_c = json.loads(a["C17/xi-0-6.json"]), json.loads(c["C17/xi-0-6.json"])
    assert doc_a["provenance"]["seed"] == 42 and doc_c["provenance"]["seed"] == 43
    first = [x["replications"]["seed_first"] for x in doc_a["outputs"]["cells"]]
    assert first == [generator.cell_seeds(42, 0, k, 16)[0] for k in range(4)]
    assert not set(first) & {x["replications"]["seed_first"] for x in doc_c["outputs"]["cells"]}
