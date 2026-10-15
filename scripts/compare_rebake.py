#!/usr/bin/env python3
"""A canonical re-bake changes nothing but its version stamps (the release check after an engine or product bump).

For every JSON document of data/derived/<CASE>/ the working tree is compared with the committed one (git HEAD, or the
revision given by --rev), ignoring only the version stamps: provenance.code_version, provenance.riskvalidation_version
and every engine_version. The document's own size, recorded by the lane gate as `trace_bytes` (a field, or a lane reason
"trace_bytes N > LIMIT"), follows the stamps' length: it may change by exactly the byte change of the document's stamps
and by nothing else. Any other difference, a document only on one side or a length change is a finding.

Standard library only; exit 1 on any finding, 2 on a usage error.
Usage: python scripts/compare_rebake.py C13 C14 [--rev HEAD] [--root <repo>]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

STAMPS = {("provenance", "code_version"), ("provenance", "riskvalidation_version")}
TRACE = re.compile(r"^trace_bytes (\d+) > (\d+)$")


def stamp_bytes(doc, path: tuple = ()) -> int:
    """The UTF-8 bytes the version stamps take in a document (their values only)."""
    if isinstance(doc, dict):
        return sum(len(json.dumps(v, ensure_ascii=False).encode("utf-8")) if ((path + (k,))[-2:] in STAMPS or k == "engine_version")
                   else stamp_bytes(v, path + (k,)) for k, v in doc.items())
    if isinstance(doc, list):
        return sum(stamp_bytes(v, path + (i,)) for i, v in enumerate(doc))
    return 0


def diff(a, b, path: tuple = (), size_delta: int = 0) -> list[str]:
    if path[-2:] in STAMPS or (path and path[-1] == "engine_version"):
        return []
    # the document's own size: it moves with the stamps' length, and only by that
    if path and path[-1] == "trace_bytes" and isinstance(a, int) and isinstance(b, int) and b - a == size_delta:
        return []
    if isinstance(a, str) and isinstance(b, str) and TRACE.match(a) and TRACE.match(b):
        (na, la), (nb, lb) = TRACE.match(a).groups(), TRACE.match(b).groups()
        if la == lb and int(nb) - int(na) == size_delta:
            return []
    where = "/".join(map(str, path)) or "(document)"
    if isinstance(a, dict) and isinstance(b, dict):
        out: list[str] = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                if (path + (k,))[-2:] not in STAMPS and k != "engine_version":
                    out.append(f"{'/'.join(map(str, path + (k,)))} is on one side only")
                continue
            out += diff(a[k], b[k], path + (k,), size_delta)
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{where} has {len(a)} items committed and {len(b)} re-baked"]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, path + (i,), size_delta)
        return out
    return [] if a == b else [f"{where}: {a!r} committed, {b!r} re-baked"[:240]]


def committed(root: Path, rev: str, rel: str) -> str | None:
    res = subprocess.run(["git", "-C", str(root), "show", f"{rev}:{rel}"], capture_output=True, text=True, encoding="utf-8")
    return res.stdout if res.returncode == 0 else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cases", nargs="+")
    ap.add_argument("--rev", default="HEAD")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args(argv)
    root = Path(args.root)
    findings: list[str] = []
    n = 0
    for case in args.cases:
        folder = root / "data" / "derived" / case
        if not folder.is_dir():
            findings.append(f"{case}: no data/derived/{case}/ folder")
            continue
        listed = subprocess.run(["git", "-C", str(root), "ls-tree", "--name-only", args.rev, f"data/derived/{case}/"],
                                capture_output=True, text=True, encoding="utf-8").stdout.split()
        names = {Path(p).name for p in listed if p.endswith(".json")} | {p.name for p in folder.glob("*.json")}
        for name in sorted(names):
            rel = f"data/derived/{case}/{name}"
            n += 1
            old = committed(root, args.rev, rel)
            new = (root / rel).read_text(encoding="utf-8") if (root / rel).exists() else None
            if old is None or new is None:
                findings.append(f"{rel}: {'new, not committed' if old is None else 'committed, not re-baked'}")
                continue
            before, after = json.loads(old), json.loads(new)
            findings += [f"{rel}: {d}" for d in diff(before, after, size_delta=stamp_bytes(after) - stamp_bytes(before))]
    if findings:
        print("REBAKE CHANGED MORE THAN ITS STAMPS:")
        for f in findings:
            print(f"  - {f}")
        return 1
    print(f"compare_rebake: OK, {n} documents of {', '.join(args.cases)} equal their committed versions but for the stamps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
