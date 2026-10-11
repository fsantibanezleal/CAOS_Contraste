"""The source registry and the fetcher: CT-008 to CT-011."""
from __future__ import annotations

import datetime as dt
import hashlib
import json

import pytest

from pipeline.io import fetch as f
from pipeline.io import sources as s


def _reg(**over):
    base = {"id": "toy-source", "name": "Toy", "publisher": "Test", "landing": "https://example.org/toy",
            "licence": "CC BY 4.0, verbatim fragment", "class": "mirror-allowed", "access": "direct download",
            "cases": ["C01"], "unverified": [],
            "fetch": {"kind": "http", "files": [{"name": "toy.csv", "url": "https://example.org/toy.csv"}]}}
    base.update(over)
    return base


def _write(tmp_path, *entries):
    p = tmp_path / "sources.json"
    p.write_text(json.dumps({"schema": s.SCHEMA, "sources": list(entries)}), encoding="utf-8")
    return p


def _opener(payload: bytes):
    def opener(url: str):
        yield payload[: len(payload) // 2]
        yield payload[len(payload) // 2:]
    return opener


def test_registry_classes_valid(tmp_path):
    reg = s.load()
    assert len(reg) >= 49
    assert {src.klass for src in reg.values()} == set(s.CLASSES)
    for src in reg.values():
        assert src.licence.strip(), src.id
        if not src.readable:
            assert src.cases == (), f"{src.id} is {src.klass} and must not be read by a case"
    # a malformed registry is refused, naming every problem
    bad = _write(tmp_path, _reg(**{"class": "public"}), _reg(id="Bad Id", licence=""),
                 _reg(id="linked", **{"class": "link-only"}))
    with pytest.raises(s.RegistryError) as exc:
        s.load(bad)
    msg = str(exc.value)
    assert "class 'public'" in msg and "lower-case words" in msg and "licence fragment is empty" in msg
    assert "linked: a link-only source is linked, never read" in msg
    # a case may read only what the registry lets it read
    reg = s.load()
    assert [x.id for x in s.assert_case_inputs("C01", ["uci-taiwan", "uci-german"], reg)] == ["uci-taiwan", "uci-german"]
    with pytest.raises(s.LicenceError, match="link-only"):
        s.assert_case_inputs("C06", ["fannie-mae-sflp"], reg)
    with pytest.raises(s.LicenceError, match="unusable"):
        s.assert_case_inputs("C01", ["kaggle-home-credit"], reg)
    with pytest.raises(s.LicenceError, match="does not list C02"):
        s.assert_case_inputs("C02", ["uci-taiwan"], reg)


def test_fetch_writes_manifest_row(tmp_path):
    reg = s.load(_write(tmp_path, _reg()))
    payload = b"id,target\n1,0\n2,1\n"
    man = tmp_path / "manifest.json"
    row = f.fetch("toy-source", root=tmp_path / "data", opener=_opener(payload), manifest_path=man,
                  today=dt.date(2026, 10, 5), reg=reg)
    stored = tmp_path / "data" / "raw" / "toy-source" / "toy.csv"
    assert stored.read_bytes() == payload and not stored.with_name("toy.csv.part").exists()
    assert row["files"] == [{"name": "toy.csv", "url": "https://example.org/toy.csv",
                             "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload),
                             "retrieved": "2026-10-05"}]
    doc = json.loads(man.read_text(encoding="utf-8"))
    assert doc["schema"] == f.MANIFEST_SCHEMA
    entry = doc["sources"]["toy-source"]
    assert entry["class"] == "mirror-allowed" and entry["licence"] == "CC BY 4.0, verbatim fragment"
    # the same bytes again: the row and its retrieval date are unchanged
    again = f.fetch("toy-source", root=tmp_path / "data", opener=_opener(payload), manifest_path=man,
                    today=dt.date(2026, 12, 1), reg=reg)
    assert again["files"][0]["retrieved"] == "2026-10-05"


def test_fetch_refuses_what_may_not_be_read(tmp_path):
    reg = s.load(_write(tmp_path, _reg(), _reg(id="no-spec", fetch=None)))
    with pytest.raises(f.FetchError, match="no fetch specification"):
        f.fetch("no-spec", root=tmp_path, opener=_opener(b"x"), manifest_path=tmp_path / "m.json", reg=reg)
    with pytest.raises(s.LicenceError, match="never fetched"):
        f.fetch("kaggle-home-credit", root=tmp_path, opener=_opener(b"x"), manifest_path=tmp_path / "m.json")
    with pytest.raises(f.FetchError, match="no bytes"):
        f.fetch("toy-source", root=tmp_path / "d", opener=_opener(b""), manifest_path=tmp_path / "m.json", reg=reg)


def test_data_root_outside_repository(tmp_path, monkeypatch):
    with pytest.raises(f.FetchError, match="no data root"):
        f.data_root(None)
    with pytest.raises(f.FetchError, match="inside the repository"):
        f.data_root(f.REPO_ROOT / "data" / "raw")
    with pytest.raises(f.FetchError, match="inside the repository"):
        f.data_root(f.REPO_ROOT)
    monkeypatch.setenv(f.ENV_VAR, str(tmp_path / "vault"))
    assert f.data_root(None) == (tmp_path / "vault").resolve()
    assert f.data_root(tmp_path / "other") == (tmp_path / "other").resolve()


def test_hash_drift_fails(tmp_path):
    reg = s.load(_write(tmp_path, _reg()))
    man = tmp_path / "manifest.json"
    root = tmp_path / "data"
    f.fetch("toy-source", root=root, opener=_opener(b"release one"), manifest_path=man,
            today=dt.date(2026, 10, 5), reg=reg)
    with pytest.raises(f.FetchError, match="the bytes changed"):
        f.fetch("toy-source", root=root, opener=_opener(b"release two"), manifest_path=man, reg=reg)
    # the pinned file and the manifest are untouched by the refused fetch
    assert (root / "raw" / "toy-source" / "toy.csv").read_bytes() == b"release one"
    assert json.loads(man.read_text(encoding="utf-8"))["sources"]["toy-source"]["files"][0]["sha256"] == \
        hashlib.sha256(b"release one").hexdigest()
    row = f.fetch("toy-source", root=root, opener=_opener(b"release two"), manifest_path=man, refresh=True,
                  today=dt.date(2026, 11, 1), reg=reg)
    assert row["files"][0]["sha256"] == hashlib.sha256(b"release two").hexdigest()
    assert row["files"][0]["retrieved"] == "2026-11-01"


def test_manual_source_is_hashed_in_place(tmp_path):
    reg = s.load(_write(tmp_path, _reg(id="by-hand", fetch={"kind": "manual", "files": [{"name": "panel.txt"}]})))
    man = tmp_path / "m.json"
    with pytest.raises(f.FetchError, match="place panel.txt"):
        f.fetch("by-hand", root=tmp_path / "data", manifest_path=man, reg=reg)
    target = tmp_path / "data" / "raw" / "by-hand" / "panel.txt"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"placed by hand")
    row = f.fetch("by-hand", root=tmp_path / "data", manifest_path=man, reg=reg)
    assert row["files"][0]["sha256"] == hashlib.sha256(b"placed by hand").hexdigest()
    assert row["files"][0]["url"] == "https://example.org/toy"


def test_the_committed_manifest_matches_the_registry():
    """Every source in the committed licence manifest exists in the registry with the same class and licence."""
    reg = s.load()
    man = json.loads((f.REPO_ROOT / "data" / "sources" / "manifest.json").read_text(encoding="utf-8"))
    assert man["schema"] == f.MANIFEST_SCHEMA
    for sid, row in man["sources"].items():
        assert sid in reg, sid
        assert row["class"] == reg[sid].klass and row["licence"] == reg[sid].licence, sid
        assert row["files"] and all(len(x["sha256"]) == 64 and x["bytes"] > 0 for x in row["files"]), sid
