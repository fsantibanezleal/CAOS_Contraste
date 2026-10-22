"""Plants for the catalog-driven document guard (0.09.000, requirement CT-030): scripts/check_documents.py reads the catalog's
`documents` column, so the defects it must catch are planted in a copy of the real repository and the real guard is run."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from planting import guard, make_tree, set_cell

INPUTS = ("scripts/check_documents.py", "scripts/check_contracts.py", "tests/contracts/contract_schemas.py", "docs/contracts", "data", "data-pipeline/config", "models")
CATALOG = "docs/contracts/catalog.md"
DOCUMENTS_COLUMN = 5  # id, version, owner, schema file, example, documents


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    return make_tree(tmp_path / "repo", *INPUTS)


def test_the_slim_tree_passes_the_guard_it_stands_for(tree: Path) -> None:
    r = guard(tree, "check_documents.py", ok_marker="documents:")
    assert r.returncode == 0, r.stdout


def test_an_invalid_committed_document_fails(tree: Path) -> None:
    path = tree / "data/derived/C04/sp.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    del doc["case_id"]
    path.write_text(json.dumps(doc), encoding="utf-8")
    r = guard(tree, "check_documents.py")
    assert r.returncode == 1 and "data/derived/C04/sp.json: [variant-agency]" in r.stdout, r.stdout


def test_a_document_left_out_of_every_row_is_a_hole(tree: Path) -> None:
    (tree / "data/derived/C04/extra.json").write_text("{}", encoding="utf-8")
    (tree / "models/other.json").write_text("{}", encoding="utf-8")
    r = guard(tree, "check_documents.py")
    assert r.returncode == 1, r.stdout
    assert "data/derived/C04/extra.json: covered by no row" in r.stdout
    assert "models/other.json: covered by no row" in r.stdout


def test_a_glob_narrowed_so_a_document_is_left_out_is_a_hole(tree: Path) -> None:
    set_cell(tree, CATALOG, "c04-agency", DOCUMENTS_COLUMN, "data/derived/C04/sp.json, data/derived/C04/fitch.json")
    r = guard(tree, "check_documents.py")
    assert r.returncode == 1 and "data/derived/C04/moodys.json: covered by no row" in r.stdout, r.stdout


def test_two_rows_claiming_one_file_fail(tree: Path) -> None:
    set_cell(tree, CATALOG, "readiness", DOCUMENTS_COLUMN, "data/derived/readiness.json, data/derived/manifests/index.json")
    r = guard(tree, "check_documents.py")
    assert r.returncode == 1, r.stdout
    assert "data/derived/manifests/index.json" in r.stdout and "more than one row" in r.stdout
    assert "case-index" in r.stdout and "readiness" in r.stdout
