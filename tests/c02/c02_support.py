"""Constants and helpers shared by the C02 tests (a uniquely named module: several units ship a ``conftest`` of their own).

The planted files are test inputs and never a result: a generator writes five ARFF members in the layout of the UCI files (64 numeric
attributes, ``?`` for missing, the class {0,1}) with a known logistic rule, so a test can say what the bake must produce. The tests that
read the committed documents run on the real bake.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (HERE, ROOT / "tests" / "contracts", ROOT / "data-pipeline"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
DERIVED = ROOT / "data" / "derived"
C02 = DERIVED / "C02"
SEED = 42
VARIANTS = ("h1", "h2", "h3", "h4", "h5", "pooled")
MODELS = "models-polish-horizons"
ZIP_NAME = "polish+companies+bankruptcy+data.zip"
PLANTED_ROWS = (420, 480, 500, 460, 400)


def load_module(path: Path, name: str):
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


def arff_text(year: int, n: int, seed: int = SEED, *, signal: float = 1.2, duplicate: bool = True, shift: float = -0.35) -> str:
    """One planted member: logistic in Attr1, Attr2 and Attr3, about 12 percent events, missing cells, one repeated row."""
    rng = np.random.default_rng(seed * 100 + year)
    Z = rng.normal(size=(n, 64)) * np.exp(rng.normal(0, 0.3, 64))
    z = -1.7 + signal * Z[:, 0] - 0.8 * Z[:, 1] + 0.5 * Z[:, 2] + shift * (year - 3)
    y = (rng.random(n) < 1 / (1 + np.exp(-z))).astype(int)
    miss = rng.random((n, 64)) < 0.01
    miss[:, 36] = rng.random(n) < 0.40          # Attr37 is heavily missing in the real files
    miss[:, 4] = rng.random(n) < 0.08           # Attr5 over the 5 percent indicator line
    lines = ["@relation 'planted'", ""] + [f"@attribute Attr{k} numeric" for k in range(1, 65)] + ["@attribute class {0,1}", "", "@data"]
    rows = []
    for i in range(n):
        cells = ["?" if miss[i, j] else f"{Z[i, j]:.5f}" for j in range(64)]
        rows.append(",".join(cells) + f",{y[i]}")
    if duplicate:
        rows.append(rows[0])
    return "\n".join(lines + rows) + "\n"


def make_zip(path: Path, rows: tuple[int, ...] = PLANTED_ROWS, seed: int = SEED, **kw: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        for k, n in enumerate(rows, start=1):
            z.writestr(zipfile.ZipInfo(f"{k}year.arff", date_time=(2026, 10, 20, 0, 0, 0)), arff_text(k, n, seed, **kw))
    return path


def manifest_for(zip_path: Path) -> dict[str, Any]:
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    return {"schema": "contraste.licence-manifest/v1", "sources": {"uci-polish": {"files": [
        {"name": ZIP_NAME, "url": "planted", "sha256": digest, "bytes": zip_path.stat().st_size, "retrieved": "2026-10-20"}]}}}


def planted_root(tmp: Path, rows: tuple[int, ...] = PLANTED_ROWS, seed: int = SEED, **kw: Any) -> tuple[Path, dict[str, Any]]:
    zp = make_zip(tmp / "raw" / "uci-polish" / ZIP_NAME, rows, seed, **kw)
    return tmp, manifest_for(zp)


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
    return load(C02 / f"{name}.json")


def all_documents() -> dict[str, dict[str, Any]]:
    return {**{v: committed(v) for v in VARIANTS}, MODELS: committed(MODELS)}


def listing_problems(folder: Path, manifest: dict[str, Any]) -> list[str]:
    """Every document is in the manifest with its size and in SHA256SUMS with its digest."""
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
    if sums.get("C02/raw-sources.txt") != sha(folder / "raw-sources.txt"):
        out.append("raw-sources.txt: the digest of SHA256SUMS.txt does not match the file")
    return out
