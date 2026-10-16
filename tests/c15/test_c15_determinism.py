"""CT-1513: the bake is a pure function of its seed and of the raw files; it never reads the network."""
from __future__ import annotations

import hashlib
import socket
from pathlib import Path

import pytest
from c15_support import SEED, data_root, requires_raw

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
def test_two_bakes_with_the_same_seed_write_the_same_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from pipeline.cases.c15 import bake

    def no_network(*a, **k):
        raise AssertionError("the bake opened a socket")

    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket.socket, "connect", no_network)
    a = bake.build(SEED, data_root())
    b = bake.build(SEED, data_root())
    ha, hb = written(tmp_path / "a", a), written(tmp_path / "b", b)
    assert ha == hb and len(ha) == 8            # six variants, the models document, the raw-source record
    assert a.contract == b.contract and a.values == b.values
