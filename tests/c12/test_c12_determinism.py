"""CT-1218: the bake is a pure function of its seed."""
from __future__ import annotations

import hashlib
from pathlib import Path

from c12_support import SEED, SMALL, data_root, requires_raw

from pipeline.io.formats import write_json


def written(tmp: Path, built) -> dict[str, str]:
    """The bytes the bake writes for every document of a build (compact JSON), by file name."""
    out = {}
    for doc in built.variants.values():          # the wall-clock seconds of an ORE run are recorded and are the one field that varies
        if doc["outputs"]["ore_reconciliation"]["run_seconds"] is not None:
            doc["outputs"]["ore_reconciliation"]["run_seconds"] = 0.0
    for name, doc in {**built.variants, "models": built.models, "raw-sources": built.raw_sources}.items():
        n = write_json(tmp / f"{name}.json", doc)
        out[name] = hashlib.sha256((tmp / f"{name}.json").read_bytes()).hexdigest()
        assert n > 0
    return out


@requires_raw
def test_two_bakes_with_the_same_seed_write_the_same_bytes(tmp_path: Path, built) -> None:
    from pipeline.cases.c12 import bake

    again = bake.build(SEED, data_root(), work_dir=tmp_path / "ore-again", **SMALL)
    ha, hb = written(tmp_path / "a", built), written(tmp_path / "b", again)
    assert ha == hb and len(ha) == 8            # six variants, the models document, the raw-source record
    assert built.values == again.values and built.contract == again.contract
