"""CT-1413: the bake is a pure function of its seed."""
from __future__ import annotations

import hashlib
from pathlib import Path

from c14_support import SEED, SMALL_PATHS, data_root, requires_raw

from pipeline.io.formats import write_json


def written(tmp: Path, built) -> dict[str, str]:
    """The bytes the bake writes for every document of a build (compact JSON), by file name."""
    out = {}
    for name, doc in {**built.variants, "models": built.models, "raw-sources": built.raw_sources}.items():
        n = write_json(tmp / f"{name}.json", doc)
        out[name] = hashlib.sha256((tmp / f"{name}.json").read_bytes()).hexdigest()
        assert n > 0
    return out


@requires_raw
def test_two_bakes_with_the_same_seed_write_the_same_bytes(tmp_path: Path) -> None:
    from pipeline.cases.c14 import bake

    a = bake.build(SEED, data_root(), n_paths=SMALL_PATHS)
    b = bake.build(SEED, data_root(), n_paths=SMALL_PATHS)
    ha, hb = written(tmp_path / "a", a), written(tmp_path / "b", b)
    assert ha == hb and len(ha) == 5            # three variants, the models document, the raw-source record
    assert a.contract == b.contract and a.values == b.values
