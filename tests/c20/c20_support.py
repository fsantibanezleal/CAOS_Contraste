"""Constants and helpers shared by the C20 tests (a uniquely named module: several units ship a ``conftest`` of their own).

The reader and convention tests run on small committed samples of the sources (``tests/c20/data/``: 15 SGCD records, the SGCD metadata and
codebook, 10 Fed loans), which are test inputs and never a result. The tests that bake need the raw files of the device data root
(``CONTRASTE_DATA``) and are skipped where it is absent; they run on a stratified subsample of Taiwan and Polish (``max_rows``) so that they
take about a minute. The tests that read the committed documents run on the real bake.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (HERE, ROOT / "tests" / "contracts", ROOT / "data-pipeline"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
DATA = HERE / "data"
DERIVED = ROOT / "data" / "derived"
C20 = DERIVED / "C20"
SEED = 42
VARIANTS = ("sgcd-seen", "sgcd-held-out", "fed-shift", "seed-sweep", "perturbation-grid", "leakage-planted")
SGCD_VARIANTS = ("sgcd-seen", "sgcd-held-out")
TAIWAN_VARIANTS = ("seed-sweep", "perturbation-grid", "leakage-planted")
MODELS = "models-c20-ladder"
MANIFEST = DERIVED / "manifests" / "C20.json"
SUBSAMPLE = 1500
PROHIBITED = ("It is provided for research and benchmarking only and must not be used for real-world credit scoring or any production "
              "decision-making about individuals.")


def load_module(path: Path, name: str):
    """A helper of another suite, loaded under a name of its own (several contract suites ship a ``semantics`` module)."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def semantics():
    return load_module(ROOT / "tests" / "contracts_u14" / "semantics.py", "u14_semantics")


def values():
    return load_module(ROOT / "tests" / "contracts_u14" / "values.py", "u14_values")


def _find_data_root() -> Path | None:
    cand = os.environ.get("CONTRASTE_DATA")  # the device data root by role; never a drive written here
    need = ("uci-taiwan", "uci-polish", "santanderai-sgcd", "fed-stress-tests")
    if cand and all((Path(cand) / "raw" / s).exists() for s in need):
        return Path(cand)
    return None


# resolved once, at import: the suite's sandbox fixture (tests/conftest.py) removes CONTRASTE_DATA from every test's environment
_DATA_ROOT = _find_data_root()


def data_root() -> Path | None:
    return _DATA_ROOT


class Paths:
    """The output roots a bake writes to (a temporary directory, never the repository)."""

    def __init__(self, root: Path) -> None:
        self.root = root / "derived"
        self.manifests = self.root / "manifests"
        self.manifests.mkdir(parents=True, exist_ok=True)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def committed(name: str) -> dict[str, Any]:
    return load(C20 / f"{name}.json")


def all_documents() -> dict[str, dict[str, Any]]:
    return {**{v: committed(v) for v in VARIANTS}, MODELS: committed(MODELS)}


def listing_problems(folder: Path, manifest: dict[str, Any]) -> list[str]:
    """The listing check of a baked folder: every document is in the manifest with its size and in SHA256SUMS with its digest."""
    out: list[str] = []
    sums = dict(reversed(line.split("  ", 1)) for line in (folder / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines())
    for e in manifest["artifacts"]:
        path = folder.parent / e["path"]
        if not path.exists():
            out.append(f"{e['path']}: listed and absent")
            continue
        if path.stat().st_size != e["bytes"]:
            out.append(f"{e['path']}: {path.stat().st_size} bytes, the manifest says {e['bytes']}")
        if sums.get(e["path"]) != sha(path):
            out.append(f"{e['path']}: the digest of SHA256SUMS.txt does not match the file")
    raw = folder / "raw-sources.txt"
    if sums.get("C20/raw-sources.txt") != sha(raw):
        out.append("raw-sources.txt: the digest of SHA256SUMS.txt does not match the file")
    return out


def files(folder: Path) -> dict[str, bytes]:
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}
