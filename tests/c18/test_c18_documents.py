"""CT-1816 and CT-1818: the committed documents are the contracts' producer output, the manifest lists them, the raw files are recorded."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from c18_support import C18, DERIVED, data_root, semantics

from pipeline.cases.c18 import fetch
from pipeline.core.schemas import validate_document

VARIANTS = {"baseline": "baseline", "eba": "eba-2025-adverse", "fed": "fed-2026-severely-adverse", "ngfs": "ngfs-delayed-transition",
            "aggregation": "t-copula-baseline", "reverse": "reverse-stress"}


def load_set() -> dict[str, dict]:
    docs = {"models": json.loads((C18 / "models-banco-andino.json").read_text(encoding="utf-8"))}
    for key, name in VARIANTS.items():
        docs[key] = json.loads((C18 / f"{name}.json").read_text(encoding="utf-8"))
    return docs


def test_every_committed_document_validates_and_the_set_agrees() -> None:
    sem = semantics()
    docs = load_set()
    for key, doc in docs.items():
        rel = "C18/models-banco-andino.json" if key == "models" else f"C18/{VARIANTS[key]}.json"
        validate_document(f"data/derived/{rel}", doc)
        assert sem.violations(doc) == [], key
    assert sem.cross_violations(docs) == []
    man = json.loads((DERIVED / "manifests" / "C18.json").read_text(encoding="utf-8"))
    listed = {a["path"]: a for a in man["artifacts"]}
    sums = dict(line.split("  ")[::-1] for line in (C18 / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines())
    assert set(listed) == {"C18/models-banco-andino.json", *(f"C18/{n}.json" for n in VARIANTS.values())}
    for rel, entry in listed.items():
        data = (DERIVED / rel).read_bytes()
        assert entry["bytes"] == len(data) and sums[rel] == hashlib.sha256(data).hexdigest()
    assert man["default_variant"] == "fed-2026-severely-adverse" and man["case_id"] == "C18"
    assert docs["baseline"]["provenance"]["truth_status"] == "synthetic-calibrated"


def test_raw_sources_repeat_the_provenance_records(tmp_path: Path) -> None:
    raw = json.loads((C18 / "raw-sources.txt").read_text(encoding="utf-8"))
    assert raw["schema"] == "contraste.sources-manifest-rows/v1"
    assert set(raw["sources"]) >= {"fed-stress-tests", "fed-chargeoff", "bcch-bde"}
    for sid, row in raw["sources"].items():
        assert row["class"] in ("mirror-allowed", "derived-only") and row["files"], sid
        for f in row["files"]:
            assert set(f) >= {"name", "url", "bytes", "sha256", "retrieved"} and len(f["sha256"]) == 64
    fx = raw["sources"]["bcch-bde"]["files"][0]
    assert fx["name"].startswith("F072.CLP.EUR.N.O.D") and "pass" not in fx["url"] and "user" not in fx["url"]      # the series id, never the account
    if data_root() is None:
        return
    # a changed byte is refused by the loader
    folder = tmp_path / "raw" / fetch.FED_HIST_DIR
    folder.mkdir(parents=True)
    for f in raw["sources"]["fed-stress-tests"]["files"]:
        shutil.copy(Path(data_root()) / "raw" / fetch.FED_HIST_DIR / f["name"], folder / f["name"])
    (folder / fetch.PROVENANCE).write_text(json.dumps(raw["sources"]["fed-stress-tests"]["files"]), encoding="utf-8")
    assert fetch.load_provenance(tmp_path, (fetch.FED_HIST_DIR,))
    victim = folder / raw["sources"]["fed-stress-tests"]["files"][0]["name"]
    victim.write_bytes(victim.read_bytes() + b" ")
    with pytest.raises(ValueError, match="differs from its provenance record"):
        fetch.load_provenance(tmp_path, (fetch.FED_HIST_DIR,))
