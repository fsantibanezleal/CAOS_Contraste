"""CT-2104 and CT-2113: the raw HMDA files and their provenance, and a year that does not answer."""
from __future__ import annotations

import re
import urllib.request
from pathlib import Path

from c21_support import C21, YEARS, data_root, load, planted_downloads, planted_root

from pipeline.cases.c21 import bake, fetch


def test_the_provenance_records_match_the_files_and_the_fetch_sends_no_browser_user_agent(tmp_path: Path, monkeypatch) -> None:
    out = fetch.fetch(tmp_path, today="2026-10-19", download=planted_downloads(n=300), attempts=1, pause=0.0)
    assert out["unavailable"] == [] and [fetch.year_of(r) for r in out["files"]] == list(YEARS)
    rows = fetch.load_provenance(tmp_path)
    for r in rows:
        p = tmp_path / "raw" / "hmda" / r["name"]
        assert r["bytes"] == p.stat().st_size and r["sha256"] == fetch.sha256_of(p) and r["retrieved"] == "2026-10-19"
        assert r["url"] == fetch.url(fetch.year_of(r)) and "states=DE" in r["url"] and "actions_taken=1,2,3,4,5,6,7,8" in r["url"]

    seen = []

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"x"

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: seen.append(req) or Resp())
    assert fetch._download(fetch.url(2018)) == b"x"
    assert len(seen) == 1 and dict(seen[0].header_items()) == {}                  # the client's default user agent: no header is set
    assert "Mozilla" not in Path(fetch.__file__).read_text(encoding="utf-8")

    raw = C21 / "raw-sources.txt"
    assert raw.exists(), "the bake commits data/derived/C21/raw-sources.txt"
    copy = load(raw)["sources"]["hmda"]
    assert copy["class"] == "mirror-allowed" and "UNVERIFIED" in copy["licence"]
    names = [f["name"] for f in copy["files"]]
    assert names == [fetch.file_name(y) for y in YEARS]
    for f in copy["files"]:
        assert re.fullmatch(r"[0-9a-f]{64}", f["sha256"]) and f["bytes"] > 0 and f["url"] == fetch.url(fetch.year_of(f))
    if data_root() is not None:       # on a device holding the raw files, the committed copy is the sidecar, record by record
        assert copy["files"] == fetch.load_provenance(data_root())


def test_a_year_that_does_not_answer_stops_its_pairs_and_writes_nothing_for_them(tmp_path: Path) -> None:
    out = fetch.fetch(tmp_path, today="2026-10-19", download=planted_downloads(n=300, fail=(2020,)), attempts=1, pause=0.0)
    assert [u["year"] for u in out["unavailable"]] == [2020] and out["unavailable"][0]["url"] == fetch.url(2020)
    assert not (tmp_path / "raw" / "hmda" / fetch.file_name(2020)).exists()
    ok, blocked = fetch.pairs_status(fetch.year_of(r) for r in fetch.load_provenance(tmp_path))
    assert [p[0] for p in ok] == ["2018-19", "2021-22", "2022-23", "2023-24"]
    assert [b["pair_id"] for b in blocked] == ["2019-20", "2020-21"]
    assert all(b["missing_years"] == [2020] and b["urls"] == [fetch.url(2020)] for b in blocked)
    built = bake.build(42, tmp_path)
    assert built.order == ["pair-2018-19", "pair-2021-22", "pair-2022-23", "pair-2023-24"] and set(built.variants) == set(built.order)
    assert [b["pair_id"] for b in built.blocked] == ["2019-20", "2020-21"]
    assert built.models["provenance"]["inputs"][0]["files"] and all(
        "2020" not in f["name"] for f in built.models["provenance"]["inputs"][0]["files"])    # the models rest on the years that answered


def test_a_complete_root_blocks_no_pair(tmp_path: Path) -> None:
    root = planted_root(tmp_path, n=300)
    ok, blocked = fetch.pairs_status(fetch.year_of(r) for r in fetch.load_provenance(root))
    assert len(ok) == 6 and blocked == []
