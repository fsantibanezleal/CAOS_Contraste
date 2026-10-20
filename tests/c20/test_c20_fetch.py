"""CT-2020: the provenance of the raw files and the missing-data behavior (a source that does not answer stops its variants)."""
from __future__ import annotations

import urllib.error
from pathlib import Path

import pytest
from c20_support import DATA, SEED

from pipeline.cases.c20 import bake, fetch


def planted(url: str) -> bytes:
    if url.endswith("SGCDataset.jsonl"):
        return (DATA / "sgcd-sample.jsonl").read_bytes()
    if url.endswith("SGCDataset_metadata.json"):
        return (DATA / "sgcd-metadata.json").read_bytes()
    if url.endswith("codebook.md"):
        return (DATA / "sgcd-codebook.md").read_bytes()
    if url.endswith("README.md"):
        return b"planted dataset card\n"
    return (DATA / "fed-sample.csv").read_bytes()


def test_the_provenance_records_match_the_files_and_the_urls_are_the_pinned_ones(tmp_path: Path) -> None:
    res = fetch.fetch(tmp_path, today="2026-10-19", download=planted, attempts=1, pause=0.0)
    assert res["unavailable"] == [] and set(res["files"]) == {fetch.SGCD_ID, fetch.FED_ID}
    sg = fetch.load_provenance(tmp_path, fetch.SGCD_ID)
    assert [r["name"] for r in sg] == ["SGCDataset.jsonl", "SGCDataset_metadata.json", "codebook.md", "README.md"]
    for r in sg:
        path = tmp_path / "raw" / fetch.SGCD_ID / r["name"]
        assert r["bytes"] == path.stat().st_size and r["sha256"] == fetch.sha256_of(path) and r["retrieved"] == "2026-10-19"
        assert r["url"].startswith("https://raw.githubusercontent.com/SantanderAI/sota-stressed-datasets/8403fa9048f7159d51a0cec5a2d9a2e9712662bd/")
    fd = fetch.load_provenance(tmp_path, fetch.FED_ID)
    assert [r["name"] for r in fd] == ["corporate-typical-risk-2025.csv", "corporate-high-risk-2025.csv", "corporate-low-risk-2025.csv"]
    assert all(r["url"].startswith("https://www.federalreserve.gov/supervisionreg/files/corporate-") for r in fd)
    assert fetch.missing_for(tmp_path) == []


def test_a_source_that_does_not_answer_names_its_variants_and_writes_nothing_for_them(tmp_path: Path) -> None:
    def down(url: str) -> bytes:
        if "SantanderAI" in url:
            raise urllib.error.URLError("planted failure")
        return planted(url)

    res = fetch.fetch(tmp_path, today="2026-10-19", download=down, attempts=1, pause=0.0)
    assert {u["source"] for u in res["unavailable"]} == {fetch.SGCD_ID} and all("SantanderAI" in u["url"] for u in res["unavailable"])
    gone = fetch.missing_for(tmp_path)
    assert [g["source"] for g in gone] == [fetch.SGCD_ID] and gone[0]["variants"] == ["sgcd-seen", "sgcd-held-out"]
    assert all(u.startswith("https://raw.githubusercontent.com/SantanderAI/") for u in gone[0]["urls"])
    with pytest.raises(FileNotFoundError, match="santanderai-sgcd"):
        fetch.load_provenance(tmp_path, fetch.SGCD_ID)
    # the bake stops the variants that need the source, names them with the URLs and writes nothing for them
    with pytest.raises(FileNotFoundError) as err:
        bake.build(SEED, tmp_path, only=("sgcd-seen", "sgcd-held-out"))
    assert "sgcd-seen" in str(err.value) and "raw.githubusercontent.com" in str(err.value)
    assert not (tmp_path / "derived").exists() and not list(tmp_path.rglob("sgcd-seen*.json"))
