"""Read the committed CONTRACT-2 documents (index, manifests, artifacts) as they are. Read-only, path-traversal guarded.

Nothing here knows a product's manifest shape beyond contract 2's two forms: one artifact (`artifact: {path}` at the
manifest's top level) or several (`artifacts: [{path, ...}]`, one per variant). The documents are served unchanged;
their shapes are checked by scripts/check_artifacts.py and the web's contract test, never re-declared here.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import REPO_ROOT, Settings


def _derived() -> Path:
    return (REPO_ROOT / Settings().data_dir).resolve()


def _read(rel: str) -> Any | None:
    """A committed JSON document under the derived root, or None (missing, not JSON, or outside the root)."""
    root = _derived()
    p = (root / rel).resolve()
    if p.suffix != ".json" or (p != root and root not in p.parents) or not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def load_index() -> dict:
    return _read("manifests/index.json") or {"cases": []}


def load_manifest(case_id: str) -> dict | None:
    if "/" in case_id or "\\" in case_id or case_id.startswith("."):
        return None
    return _read(f"manifests/{case_id}.json")


def artifact_paths(manifest: dict) -> list[str]:
    """The artifact paths a manifest names, in either form of contract 2."""
    if isinstance(manifest.get("artifacts"), list):
        return [a["path"] for a in manifest["artifacts"] if isinstance(a, dict) and "path" in a]
    single = manifest.get("artifact")
    return [single["path"]] if isinstance(single, dict) and "path" in single else []


def load_artifact(rel: str) -> Any | None:
    return _read(rel)
