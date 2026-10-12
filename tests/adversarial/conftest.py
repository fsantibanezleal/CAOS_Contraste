"""Fixtures of the adversarial tests (CF-D, after template 0.05.000): a throwaway copy of the repository's committed
files, one planted defect, and the real gate run as a subprocess on the copy.

Nothing here writes outside a temporary directory, and nothing reads a raw data file: every plant edits a committed
artifact or a source file of the copy. The root conftest's autouse fixture imports the pipeline, so it is replaced by a
no-op here (the copy's own tests import the pipeline in their own process)."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKIP = shutil.ignore_patterns("node_modules", "dist", "gate-output", "__pycache__", ".venv*", ".git", ".pytest_cache",
                              ".ruff_cache", "*.pyc", "build", "adversarial")
COPIED = ("scripts", "docs", "data", "data-pipeline", "models", "frontend", "tests", "deploy", "app", "manifests")
FILES = ("VERSION", "product.json", "CHANGELOG.md", "requirements-precompute.txt", "requirements-dev.txt",
         "requirements-api.txt", "pyproject.toml")


@pytest.fixture(autouse=True)
def _sandboxed_pipeline() -> None:
    """Overrides tests/conftest.py: these tests import nothing of the pipeline."""
    return None


@pytest.fixture(scope="session")
def base_copy(tmp_path_factory: pytest.TempPathFactory) -> Path:
    base = tmp_path_factory.mktemp("repo-base")
    for name in COPIED:
        if (ROOT / name).exists():
            shutil.copytree(ROOT / name, base / name, ignore=SKIP)
    for name in FILES:
        if (ROOT / name).exists():
            shutil.copy2(ROOT / name, base / name)
    return base


@pytest.fixture
def repo(base_copy: Path, tmp_path: Path) -> Path:
    """A fresh copy of the repository's committed files, to plant one defect in."""
    dest = tmp_path / "repo"
    shutil.copytree(base_copy, dest)
    return dest
