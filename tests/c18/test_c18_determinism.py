"""CT-1819: the bake is a pure function of its seed."""
from __future__ import annotations

import hashlib
from pathlib import Path

from c18_support import SEED, SMALL_DRAWS, SMALL_PATHS, data_root, requires_raw

from pipeline.io.formats import write_json


def written(tmp: Path, built) -> dict[str, str]:
    """The bytes the bake writes for every document of a build (compact JSON), by file name."""
    out = {}
    for name, doc in {**built.variants, "models": built.models, "raw-sources": built.raw_sources}.items():
        write_json(tmp / f"{name}.json", doc)
        out[name] = hashlib.sha256((tmp / f"{name}.json").read_bytes()).hexdigest()
    return out


@requires_raw
def test_two_bakes_with_the_same_seed_write_the_same_bytes(tmp_path: Path, built) -> None:
    from pipeline.cases.c18 import bake

    b = bake.build(SEED, data_root(), n_draws=SMALL_DRAWS, n_paths=SMALL_PATHS)
    ha, hb = written(tmp_path / "a", built), written(tmp_path / "b", b)
    assert ha == hb and len(ha) == 8                 # six variants, the models document, the raw-source record
    assert built.values == b.values and built.contract == b.contract
