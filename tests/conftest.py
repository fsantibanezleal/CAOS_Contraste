"""Test sandbox (T8 of the 2026-10-04 base requirements).

Tests must never write the committed scientific artifacts. Until 2026-10-04 this template's own manifest test
called the pipeline without an output root and rewrote data/derived/manifests/EX02_epidemic.json with its seed
(7) and its metrics, so the committed manifest recorded a test run rather than the release bake. Two defences:

1. every test runs with the pipeline's canonical roots (DERIVED, MANIFESTS, MODELS) pointed at a temporary
   directory, so a call that forgets ``output_root`` writes into the sandbox, never the repository;
2. the session fails if any file under data/ or models/ changed during the run (compared by content hash, so it
   holds whatever the working tree held before the run).
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

GUARDED = (ROOT / "data", ROOT / "models")


def _snapshot() -> dict[str, str]:
    out: dict[str, str] = {}
    for base in GUARDED:
        if not base.exists():
            continue
        for f in sorted(base.rglob("*")):
            if f.is_file():
                out[f.relative_to(ROOT).as_posix()] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


def pytest_sessionstart(session: pytest.Session) -> None:
    session.config._caos_artifacts = _snapshot()  # type: ignore[attr-defined]


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    before = getattr(session.config, "_caos_artifacts", None)
    if before is None:
        return
    after = _snapshot()
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    if changed:
        listing = "\n  ".join(changed[:20])
        print(f"\nERROR: the test run changed committed artifacts (tests write only to tmp_path):\n  {listing}")
        session.exitstatus = 1


@pytest.fixture(autouse=True)
def _sandboxed_pipeline(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    from pipeline import pipeline

    root = tmp_path / "sandbox-derived"
    monkeypatch.setattr(pipeline, "DERIVED", root)
    monkeypatch.setattr(pipeline, "MANIFESTS", root / "manifests")
    monkeypatch.setattr(pipeline, "MODELS", tmp_path / "sandbox-models")
    return root
