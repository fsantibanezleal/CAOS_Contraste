#!/usr/bin/env python3
"""CT-003: every committed artifact carries its provenance, and that provenance is true (SDD sections 2.2 and 6).

For every variant artifact the index reaches (index, then each case manifest's ``artifacts``):
  1. the artifact has a ``provenance`` block with a truth status from the declared set, and that truth status is
     the one its manifest entry states;
  2. every input names its source and licence class; the class is the registry's, and it is publishable
     (mirror-allowed or derived-only);
  3. every input file hash is the one the licence manifest pins for that source;
  4. the manifest's ``sources`` are exactly the artifacts' inputs, so the Context view cannot list a source the
     artifacts did not read, or omit one they did.

Standard library only; exit 1 on any finding. Usage: python scripts/check_provenance.py [repo_root]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
REGISTRY = ROOT / "data-pipeline" / "config" / "sources.json"
LICENCE_MANIFEST = ROOT / "data" / "sources" / "manifest.json"
TRUTH = {"real-outcomes", "synthetic-known-truth", "synthetic-calibrated", "published-answer"}
PUBLISHABLE = {"mirror-allowed", "derived-only"}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    index_path = DERIVED / "manifests" / "index.json"
    if not index_path.exists():
        print("check_provenance: no index; run the pipeline first")
        return 1
    reg = {e["id"]: e["class"] for e in read(REGISTRY)["sources"]}
    pinned = {sid: {f["name"]: f["sha256"] for f in row["files"]} for sid, row in read(LICENCE_MANIFEST)["sources"].items()}
    findings: list[str] = []
    n_art = 0
    for entry in read(index_path).get("cases", []):
        man = read(DERIVED / entry["manifest_path"])
        cid = man.get("case_id", entry.get("case_id"))
        arts = man.get("artifacts")
        if not isinstance(arts, list) or not arts:
            findings.append(f"{cid}: the manifest lists no variant artifacts")
            continue
        read_sources: set[str] = set()
        for a in arts:
            n_art += 1
            where = f"{cid}/{a.get('variant_id')}"
            art = read(DERIVED / a["path"])
            prov = art.get("provenance")
            if not isinstance(prov, dict):
                findings.append(f"{where}: no provenance block")
                continue
            if prov.get("truth_status") not in TRUTH:
                findings.append(f"{where}: truth status {prov.get('truth_status')!r} is not one of {sorted(TRUTH)}")
            if a.get("truth_status") != prov.get("truth_status"):
                findings.append(f"{where}: the manifest says {a.get('truth_status')!r}, the artifact {prov.get('truth_status')!r}")
            if not prov.get("inputs") and not prov.get("generators"):
                findings.append(f"{where}: derives from no source and no generator")
            for inp in prov.get("inputs", []):
                sid = inp.get("source")
                read_sources.add(sid)
                if sid not in reg:
                    findings.append(f"{where}: input {sid!r} is not in the source registry")
                    continue
                if inp.get("class") != reg[sid]:
                    findings.append(f"{where}: input {sid} is recorded {inp.get('class')}, the registry says {reg[sid]}")
                if reg[sid] not in PUBLISHABLE:
                    findings.append(f"{where}: input {sid} is {reg[sid]}; the artifact may not be published")
                if (prov.get("licence_classes") or {}).get(sid) != reg[sid]:
                    findings.append(f"{where}: licence_classes does not state {sid} as {reg[sid]}")
                for f in inp.get("files", []):
                    if pinned.get(sid, {}).get(f.get("name")) != f.get("sha256"):
                        findings.append(f"{where}: {sid}/{f.get('name')} hash is not the one the licence manifest pins")
                if not inp.get("files"):
                    findings.append(f"{where}: input {sid} names no file hashes")
        if set(man.get("sources", [])) != read_sources:
            findings.append(f"{cid}: the manifest names sources {sorted(man.get('sources', []))}, the artifacts read "
                            f"{sorted(read_sources)}")
    if findings:
        print("PROVENANCE CHECK FAILED:")
        for f in findings:
            print(f"  - {f}")
        return 1
    print(f"check_provenance: OK, {n_art} artifacts carry true provenance")
    return 0


if __name__ == "__main__":
    sys.exit(main())
