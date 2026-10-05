"""Fetch a source into the device data root and record it in the licence manifest (SDD section 2.1).

Raw files never enter the repository: they are written to ``<data root>/raw/<source>/<file>``, where the data
root is the environment variable ``CONTRASTE_DATA`` or the ``--data-root`` argument, and a root inside the
repository is refused. Every file is hashed while it streams; the licence manifest
(``data/sources/manifest.json``, committed) records the URL, the retrieval date, the licence class and text, and
the SHA-256 and byte count of every file. The manifest pins each hash: a later fetch that finds other bytes fails
and names the file, unless ``refresh`` is asked for, in which case the new hash and date are recorded and the
change shows in the diff.

    python data-pipeline/fetch.py uci-taiwan uci-german [--data-root <dir>] [--refresh]
    python data-pipeline/fetch.py --all          # every source with a fetch specification
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sys
import time
import urllib.request
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from . import sources as registry

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "data" / "sources" / "manifest.json"
MANIFEST_SCHEMA = "contraste.licence-manifest/v1"
ENV_VAR = "CONTRASTE_DATA"
USER_AGENT = "Mozilla/5.0 (compatible; Contraste-pipeline/1.0; +https://github.com/fsantibanezleal/CAOS_Contraste)"
CHUNK = 1 << 20

# An opener takes a URL and yields the response body in chunks (tests pass their own).
Opener = Callable[[str], Iterator[bytes]]


class FetchError(RuntimeError):
    """A fetch could not complete, or its bytes differ from the pinned hash."""


def data_root(explicit: str | Path | None = None) -> Path:
    """The device data root: the argument, else ``CONTRASTE_DATA``. Refused when inside the repository."""
    value = explicit if explicit is not None else os.environ.get(ENV_VAR)
    if not value:
        raise FetchError(f"no data root: pass --data-root or set {ENV_VAR} (the device's data folder, outside the "
                         "repository)")
    root = Path(value).expanduser().resolve()
    repo = REPO_ROOT.resolve()
    if root == repo or repo in root.parents:
        raise FetchError(f"the data root {root} is inside the repository; raw data lives in the device data root")
    return root


def http_opener(url: str, *, retries: int = 3, timeout: float = 60.0) -> Iterator[bytes]:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (https only, checked in the registry)
                while True:
                    block = resp.read(CHUNK)
                    if not block:
                        return
                    yield block
        except OSError as exc:  # URLError and timeouts
            last = exc
            time.sleep(2.0 * (attempt + 1))
    raise FetchError(f"could not fetch {url} after {retries} attempts: {last}")


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    path = path if path is not None else MANIFEST
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema") != MANIFEST_SCHEMA:
            raise FetchError(f"{path}: schema {data.get('schema')!r}, expected {MANIFEST_SCHEMA!r}")
        return data
    return {"schema": MANIFEST_SCHEMA, "sources": {}}


def write_manifest(data: dict[str, Any], path: Path | None = None) -> None:
    path = path if path is not None else MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = {"schema": MANIFEST_SCHEMA, "sources": {k: data["sources"][k] for k in sorted(data["sources"])}}
    # bytes, so the file has LF line ends on every OS (text mode writes CRLF on Windows)
    path.write_bytes((json.dumps(ordered, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def _stream_to(dest: Path, chunks: Iterator[bytes]) -> tuple[str, int]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    digest = hashlib.sha256()
    size = 0
    with tmp.open("wb") as fh:
        for block in chunks:
            digest.update(block)
            size += len(block)
            fh.write(block)
    if size == 0:
        tmp.unlink(missing_ok=True)
        raise FetchError(f"{dest.name}: the server answered no bytes")
    return digest.hexdigest(), size


def _hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


def fetch(
    source_id: str,
    *,
    root: Path,
    refresh: bool = False,
    opener: Opener = http_opener,
    manifest_path: Path | None = None,
    today: dt.date | None = None,
    reg: dict[str, registry.Source] | None = None,
) -> dict[str, Any]:
    """Fetch (or, for a manual source, hash in place) every file of a source; return its manifest row."""
    sources = reg if reg is not None else registry.load()
    if source_id not in sources:
        raise FetchError(f"unknown source {source_id!r}")
    src = sources[source_id]
    if not src.readable:
        raise registry.LicenceError(f"{source_id} is {src.klass}: it is linked, never fetched")
    if src.fetch_kind is None:
        raise FetchError(f"{source_id} has no fetch specification yet (added by the unit that first reads it)")
    manifest = load_manifest(manifest_path)
    pinned = {f["name"]: f for f in manifest["sources"].get(source_id, {}).get("files", [])}
    stamp = (today or dt.date.today()).isoformat()
    files_out: list[dict[str, Any]] = []
    changed = False
    folder = root / "raw" / source_id
    for f in src.files:
        dest = folder / f.name
        if src.fetch_kind == "manual":
            if not dest.exists():
                raise FetchError(f"{source_id}: place {f.name} in {folder} by hand (see the registry's access note)")
            sha, size = _hash_file(dest)
        else:
            sha, size = _stream_to(dest, opener(f.url))
        old = pinned.get(f.name)
        if old is not None and old["sha256"] != sha and not refresh:
            if src.fetch_kind != "manual":
                dest.with_name(dest.name + ".part").unlink(missing_ok=True)
            raise FetchError(f"{source_id}/{f.name}: the bytes changed (pinned {old['sha256'][:12]}, now {sha[:12]}); "
                             "fetch again with --refresh to accept the new release")
        if src.fetch_kind != "manual":
            shutil.move(str(dest.with_name(dest.name + ".part")), dest)
        same = old is not None and old["sha256"] == sha
        changed = changed or not same
        files_out.append({"name": f.name, "url": f.url or src.landing, "sha256": sha, "bytes": size,
                          "retrieved": old["retrieved"] if same else stamp})
    row = {
        "name": src.name, "publisher": src.publisher, "landing": src.landing, "class": src.klass,
        "licence": src.licence, "attribution": src.attribution, "access": src.fetch_kind, "files": files_out,
    }
    if changed or manifest["sources"].get(source_id) != row:
        manifest["sources"][source_id] = row
        write_manifest(manifest, manifest_path)
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fetch", description="Fetch sources into the data root; record the licence manifest.")
    ap.add_argument("sources", nargs="*", help="source ids from data-pipeline/config/sources.json")
    ap.add_argument("--all", action="store_true", help="every source with a fetch specification")
    ap.add_argument("--data-root", help=f"the device data root (default: ${ENV_VAR})")
    ap.add_argument("--refresh", action="store_true", help="accept new bytes for a pinned file")
    args = ap.parse_args(argv)
    reg = registry.load()
    ids = [s.id for s in reg.values() if s.fetch_kind] if args.all else args.sources
    if not ids:
        ap.error("name at least one source, or --all")
    root = data_root(args.data_root)
    failed = 0
    for sid in ids:
        try:
            row = fetch(sid, root=root, refresh=args.refresh, reg=reg)
        except (FetchError, registry.LicenceError) as exc:
            print(f"FAIL {sid}: {exc}", file=sys.stderr)
            failed += 1
            continue
        for f in row["files"]:
            print(f"ok   {sid}/{f['name']}: {f['bytes']:,} bytes sha256 {f['sha256'][:16]} ({row['class']})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
