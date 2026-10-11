#!/usr/bin/env python3
"""CT-006: the repository commits no raw rows from a derived-only, link-only or unusable source (SDD section 2.1).

Checks, on every tracked file (and every untracked one not ignored, so a tree not yet committed is checked too):
  1. raw rows may live only under data/raw/<source>/, and only for a source the registry classes mirror-allowed;
  2. no file anywhere may carry the bytes of a fetched file of a source that is not mirror-allowed (the licence
     manifest pins the SHA-256 of every fetched file, so a copy under any name is caught);
  3. every source in the licence manifest exists in the registry with the same class.

Standard library only; exit 1 on any finding. Usage: python scripts/check_data_classes.py [repo_root]
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data-pipeline" / "config" / "sources.json"
MANIFEST = ROOT / "data" / "sources" / "manifest.json"
MIRRORABLE = {"mirror-allowed"}


def files() -> list[str]:
    cmd = ["git", "ls-files", "--cached", "--others", "--exclude-standard"]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return sorted({ln.strip() for ln in out.splitlines() if ln.strip() and (ROOT / ln.strip()).is_file()})


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    tracked = files()
    if len(tracked) < 10:
        print("check_data_classes: fewer than 10 files; this is not a product tree")
        return 1
    reg = {e["id"]: e["class"] for e in json.loads(REGISTRY.read_text(encoding="utf-8"))["sources"]}
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {"sources": {}}
    findings: list[str] = []
    protected: dict[str, str] = {}
    for sid, row in manifest["sources"].items():
        if sid not in reg:
            findings.append(f"data/sources/manifest.json: {sid} is not in the source registry")
            continue
        if row.get("class") != reg[sid]:
            findings.append(f"data/sources/manifest.json: {sid} is recorded {row.get('class')}, the registry says {reg[sid]}")
        if reg[sid] not in MIRRORABLE:
            for f in row.get("files", []):
                protected[f["sha256"]] = f"{sid}/{f['name']} ({reg[sid]})"
    for rel in tracked:
        parts = rel.split("/")
        if parts[:2] == ["data", "raw"] and len(parts) > 3:
            sid = parts[2]
            if sid not in reg:
                findings.append(f"{rel}: raw data of a source the registry does not know ({sid})")
            elif reg[sid] not in MIRRORABLE:
                findings.append(f"{rel}: raw rows of {sid}, which is {reg[sid]}; only mirror-allowed rows are committed")
        if protected:
            digest = sha256(ROOT / rel)
            if digest in protected:
                findings.append(f"{rel}: carries the bytes of {protected[digest]}, which may not be committed")
    if findings:
        print("DATA CLASS CHECK FAILED:")
        for f in findings:
            print(f"  - {f}")
        return 1
    n_raw = sum(1 for r in tracked if r.startswith("data/raw/"))
    print(f"check_data_classes: OK, {len(tracked)} files, {n_raw} raw files (all mirror-allowed), "
          f"{len(protected)} protected hashes absent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
