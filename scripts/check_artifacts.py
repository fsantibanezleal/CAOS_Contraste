"""Validate CONTRACT 2 on disk (the pipeline -> web artifact contract): the index references every case; each
manifest exists; each artifact it names exists, is non-empty, and its byte size matches the manifest; each lane
matches its gate verdict. A manifest names one artifact (`artifact: {path, bytes}`, the lane and gate at the
manifest's top level) or several (`artifacts: [{path, bytes, lane, gate, ...}]`, one per variant baked apart, each
with its own lane and gate). Stdlib only (runs in CI WITHOUT installing the package). Exit non-zero on any drift.

An index entry whose manifest is absent (a case of the plan not built yet, or a partial bake) is accepted only when
data/derived/readiness.json is current (recomputed here from the catalog and the repository, stdlib only) and lists
that path in the ``missing`` of a ``partial`` row; any other absent file still fails.

Used by scripts/smoke.* and by .github/workflows/ci.yml, the mechanical guard that a product can't regress to
serving artifacts that don't match their manifests.
Usage: python scripts/check_artifacts.py [repo_root]"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data-pipeline"))
DERIVED = ROOT / "data" / "derived"
MANIFESTS = DERIVED / "manifests"


def artifacts_of(m: dict) -> list[dict]:
    """The artifact entries a manifest names, each with the lane and gate it is judged by."""
    if isinstance(m.get("artifacts"), list):
        return [dict(a) for a in m["artifacts"]]
    if isinstance(m.get("artifact"), dict):
        return [{**m["artifact"], "lane": m.get("lane"), "gate": m.get("gate", {})}]
    return []


def declared_absent() -> tuple[set[str], str | None]:
    """The paths the readiness declares absent in a partial row, and why it cannot be trusted (None when it can):
    the committed document must exist and equal the one recomputed from the catalog and the repository."""
    from pipeline.core import readiness

    path = DERIVED / "readiness.json"
    if not path.is_file():
        return set(), f"{path} is absent, so no absent manifest is declared"
    try:
        fresh = readiness.compute(repo_root=ROOT, derived_root=DERIVED)
    except (ValueError, OSError) as exc:
        return set(), f"the readiness cannot be recomputed: {exc}"
    if path.read_bytes() != readiness.to_bytes(fresh):
        return set(), "data/derived/readiness.json is not current (python data-pipeline/run.py readiness)"
    return {m for e in fresh["contracts"] if e["state"] == "partial" for m in e["missing"]}, None


def main() -> int:
    idx_path = MANIFESTS / "index.json"
    if not idx_path.exists():
        print(f"FAIL: missing {idx_path} (run scripts/precompute.sh first)")
        return 1
    index = json.loads(idx_path.read_text(encoding="utf-8"))
    errs: list[str] = []
    n_art = 0
    n_declared = 0
    absent: tuple[set[str], str | None] | None = None
    for rel in index.get("files", []) or []:
        f = DERIVED / rel
        if not f.is_file() or f.stat().st_size == 0:
            errs.append(f"declared by the index but missing or empty: {f}")
    for entry in index.get("cases", []):
        mp = DERIVED / entry["manifest_path"]
        if not mp.exists():
            if absent is None:
                absent = declared_absent()
            if entry["manifest_path"] in absent[0]:
                n_declared += 1
            elif absent[1]:
                errs.append(f"missing manifest: {mp} ({absent[1]})")
            else:
                errs.append(f"missing manifest: {mp} (the readiness does not declare it absent)")
            continue
        m = json.loads(mp.read_text(encoding="utf-8"))
        arts = artifacts_of(m)
        if not arts:
            errs.append(f"{entry['case_id']}: the manifest names no artifact (artifact or artifacts)")
        for a in arts:
            n_art += 1
            art = DERIVED / a["path"]
            if not art.exists():
                errs.append(f"missing artifact: {art}")
                continue
            size = art.stat().st_size
            if size != a.get("bytes"):
                errs.append(f"byte drift {art}: manifest={a.get('bytes')} disk={size}")
            if size == 0:
                errs.append(f"empty artifact: {art}")
            if (a.get("gate") or {}).get("lane") != a.get("lane"):
                errs.append(f"lane/gate mismatch: {entry['case_id']} {a['path']}")
    if errs:
        print("CONTRACT 2 DRIFT:")
        for e in errs:
            print("  -", e)
        return 1
    note = f", {n_declared} declared absent by the readiness" if n_declared else ""
    print(f"CONTRACT 2 OK: {len(index.get('cases', []))} cases{note}, {n_art} artifacts, manifests <-> artifacts consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
