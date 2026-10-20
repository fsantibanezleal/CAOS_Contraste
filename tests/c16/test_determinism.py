"""CT-1621 and CT-1623: determinism of the bake, and the sandbox re-bake of the committed documents."""
from __future__ import annotations

import hashlib
import json

from .conftest import DATA_ROOT, requires_raw
from .helpers import C16, SEED, SMALL_DRAWS, sample_inputs


def _bytes(built) -> dict[str, bytes]:
    docs = {**{k: v for k, v in built.variants.items()}, "reverse": built.reverse, "models": built.models}
    return {k: json.dumps(v, sort_keys=True, ensure_ascii=False).encode() for k, v in docs.items()}


def test_two_bakes_with_the_same_seed_write_the_same_bytes(tmp_path):
    from pipeline.cases.c16 import bake

    a = bake.build(SEED, sample_inputs(), n_draws=SMALL_DRAWS)
    b = bake.build(SEED, sample_inputs(), n_draws=SMALL_DRAWS)
    assert _bytes(a) == _bytes(b)
    c = bake.build(SEED + 1, sample_inputs(), n_draws=SMALL_DRAWS)
    # the seed reaches the generator block (its verification draws): another seed moves it and leaves the ladder alone
    assert c.models["fit"]["generator"]["verification"] != a.models["fit"]["generator"]["verification"]
    assert c.variants["list-adverse"]["outputs"] == a.variants["list-adverse"]["outputs"]
    # written to disk through the writer, twice, the files are identical
    roots = []
    for k in range(2):
        root = tmp_path / f"w{k}"
        bake.write_documents(root, a)
        roots.append(root)
    names = sorted(p.name for p in (roots[0] / "C16").iterdir())
    assert names and names == sorted(p.name for p in (roots[1] / "C16").iterdir())
    for n in names:
        assert hashlib.sha256((roots[0] / "C16" / n).read_bytes()).digest() == hashlib.sha256((roots[1] / "C16" / n).read_bytes()).digest()


@requires_raw
def test_a_sandbox_rebake_reproduces_every_committed_document(tmp_path):
    from pipeline.cases.c16 import bake

    class Paths:
        root = tmp_path / "derived"
        manifests = tmp_path / "derived" / "manifests"

    Paths.root.mkdir()
    Paths.manifests.mkdir()
    bake.bake_case(SEED, Paths, DATA_ROOT)
    produced = sorted(p.name for p in (Paths.root / "C16").iterdir())
    assert produced == sorted(p.name for p in C16.iterdir())
    for n in produced:
        assert (Paths.root / "C16" / n).read_bytes() == (C16 / n).read_bytes(), n
    assert (Paths.manifests / "C16.json").read_bytes() == (C16.parent / "manifests" / "C16.json").read_bytes()
