"""Test sandbox (T8 of the 2026-10-04 base requirements).

Tests must never write the committed scientific artifacts. Until 2026-10-04 the template's own manifest test
called the pipeline without an output root and rewrote a committed manifest with its seed (7) and its metrics, so
the manifest recorded a test run rather than the release bake. Two defences:

1. every test runs with the pipeline's canonical roots (DERIVED, MANIFESTS, MODELS) pointed at a temporary
   directory, so a call that forgets ``output_root`` writes into the sandbox, never the repository;
2. the session fails if any file under data/ or models/ changed during the run. It snapshots filesystem metadata,
   then checks only files whose metadata or Git state changed against the starting bytes or index object. A test that
   rewrites an artifact byte-for-byte does not look like scientific data corruption.
"""
from __future__ import annotations

import os

for _var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):  # D16-18: the pipeline's pinned thread count, before numpy loads
    os.environ[_var] = "4"

import hashlib  # noqa: E402
import pathlib  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402

import pytest  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

GUARDED = (ROOT / "data", ROOT / "models")


def _snapshot() -> tuple[
    dict[str, tuple[int, int, int]], dict[str, str], dict[str, str], set[str]
]:
    # Stat the trees rather than reading every multi-megabyte trace twice. For a real checkout,
    # Git supplies index object IDs for clean files and hashes for pre-existing dirty files.
    # The copied, non-git adversarial fixture is small, so hash it directly.
    stats: dict[str, tuple[int, int, int]] = {}
    for base in GUARDED:
        if not base.exists():
            continue
        for f in sorted(base.rglob("*")):
            if f.is_file():
                stat = f.stat()
                stats[f.relative_to(ROOT).as_posix()] = (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", "data", "models"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    dirty_bytes: dict[str, str] = {}
    dirty_paths: set[str] = set()
    index_oids: dict[str, str] = {}
    if status.returncode == 0:
        for entry in status.stdout.split(b"\0"):
            if len(entry) < 4:
                continue
            relative = entry[3:].decode("utf-8", errors="surrogateescape")
            dirty_paths.add(relative)
            path = ROOT / pathlib.PurePosixPath(relative)
            if path.is_file():
                dirty_bytes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        indexed = subprocess.run(
            ["git", "ls-files", "--stage", "-z", "--", "data", "models"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        if indexed.returncode == 0:
            for entry in indexed.stdout.split(b"\0"):
                if b"\t" not in entry:
                    continue
                metadata, raw_path = entry.split(b"\t", 1)
                fields = metadata.split()
                if len(fields) == 3 and fields[2] == b"0":
                    index_oids[raw_path.decode("utf-8", errors="surrogateescape")] = fields[1].decode("ascii")
    else:
        dirty_bytes = {
            key: hashlib.sha256((ROOT / pathlib.PurePosixPath(key)).read_bytes()).hexdigest()
            for key in stats
        }
    return stats, dirty_bytes, index_oids, dirty_paths


def pytest_collectstart(collector: pytest.Collector) -> None:
    """Each tests/contracts_u* suite imports its own helpers by plain name (`import semantics`, `import
    build_fixtures`), and several suites ship a helper of the same name. Python caches the first module of a name, so in
    one run a later suite would get an earlier suite's helper. Before a suite's module is collected, drop any cached
    helper of the same name loaded from another suite's folder, and put this suite's folder first on the path."""
    _own_suite_helpers(getattr(collector, "path", None))


def pytest_runtest_setup(item: pytest.Item) -> None:
    """The same before each test runs: a suite that imports a helper lazily, inside a test, gets its own helper even
    after a later suite was collected."""
    _own_suite_helpers(getattr(item, "path", None))


def _own_suite_helpers(path: object) -> None:
    if path is None:
        return
    folder = pathlib.Path(str(path))
    folder = folder.parent if folder.suffix == ".py" else folder
    if not folder.name.startswith("contracts_u"):
        return
    own = {p.stem for p in folder.glob("*.py")}
    for name in [n for n in list(sys.modules) if n in own]:
        loaded = getattr(sys.modules[name], "__file__", None)
        if loaded and pathlib.Path(loaded).resolve().parent != folder.resolve():
            del sys.modules[name]
    if str(folder) in sys.path:
        sys.path.remove(str(folder))
    sys.path.insert(0, str(folder))


def pytest_sessionstart(session: pytest.Session) -> None:
    session.config._caos_artifacts = _snapshot()  # type: ignore[attr-defined]


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    before = getattr(session.config, "_caos_artifacts", None)
    if before is None:
        return
    after = _snapshot()
    before_stats, before_bytes, index_oids, before_dirty = before
    after_stats, _, _, after_dirty = after
    candidates = {
        k for k in before_stats.keys() | after_stats.keys() | before_dirty | after_dirty
        if before_stats.get(k) != after_stats.get(k) or k in before_dirty or k in after_dirty
    }
    changed: list[str] = []
    for key in sorted(candidates):
        path = ROOT / pathlib.PurePosixPath(key)
        if not path.is_file():
            changed.append(key)
        elif key in before_bytes:
            if hashlib.sha256(path.read_bytes()).hexdigest() != before_bytes[key]:
                changed.append(key)
        elif key in index_oids:
            current = subprocess.run(
                ["git", "hash-object", "--no-filters", "--", key],
                cwd=ROOT,
                capture_output=True,
                check=False,
                text=True,
            )
            if current.returncode != 0 or current.stdout.strip() != index_oids[key]:
                changed.append(key)
        elif key in before_stats:
            # Non-Git fixtures hash all files at session start (stored in before_bytes).
            changed.append(key)
        else:
            changed.append(key)
    if changed:
        listing = "\n  ".join(changed[:20])
        print(f"\nERROR: the test run changed committed artifacts (tests write only to tmp_path):\n  {listing}")
        session.exitstatus = 1


@pytest.fixture(autouse=True)
def _sandboxed_pipeline(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    from pipeline import pipeline
    from pipeline.io import fetch

    root = tmp_path / "sandbox-derived"
    monkeypatch.setattr(pipeline, "DERIVED", root)
    monkeypatch.setattr(pipeline, "MANIFESTS", root / "manifests")
    monkeypatch.setattr(pipeline, "MODELS", tmp_path / "sandbox-models")
    # the licence manifest is committed evidence too: a fetch that forgets manifest_path writes the sandbox
    monkeypatch.setattr(fetch, "MANIFEST", tmp_path / "sandbox-sources" / "manifest.json")
    # and no test reads or writes the device data root by accident
    monkeypatch.delenv(fetch.ENV_VAR, raising=False)
    return root
