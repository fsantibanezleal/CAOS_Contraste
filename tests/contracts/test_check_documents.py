"""scripts/check_documents.py validates every committed document against its schema file with jsonschema alone (the one
CI step that holds a constraint the generated TypeScript types do not encode: a ``pattern``, a ``minItems``). It passes
on the repository and fails, naming each error, on a drifted copy."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from contract_schemas import ROOT

SCRIPT = ROOT / "scripts" / "check_documents.py"


def run(root: Path | None = None) -> subprocess.CompletedProcess:
    args = [str(root)] if root else []
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=ROOT)


@pytest.fixture()
def copy(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    shutil.copytree(ROOT / "data", r / "data")
    shutil.copytree(ROOT / "models", r / "models")
    shutil.copytree(ROOT / "data-pipeline" / "config", r / "data-pipeline" / "config")  # the registries of the sources and licences rows
    shutil.copytree(ROOT / "docs" / "contracts" / "fixtures", r / "docs" / "contracts" / "fixtures")
    shutil.copytree(ROOT / "docs" / "contracts" / "examples", r / "docs" / "contracts" / "examples")
    shutil.copy2(ROOT / "docs" / "contracts" / "catalog.md", r / "docs" / "contracts" / "catalog.md")  # the guard reads its rows
    return r


def edit(path: Path, change) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    change(doc)
    path.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")


def test_the_repository_is_valid():
    p = run()
    assert p.returncode == 0, p.stdout + p.stderr
    assert "documents:" in p.stdout and "valid" in p.stdout


def test_a_copy_is_valid(copy):
    p = run(copy)
    assert p.returncode == 0, p.stdout + p.stderr


def test_adversarial_a_pattern_violation_fails(copy):
    # a depends_on ref must be <case>/<file>.json, manifests/<case>.json or pipeline.cases.<module> (the schema's pattern)
    edit(copy / "data" / "derived" / "manifests" / "C04.json",
         lambda m: m["depends_on"].append({"kind": "document", "ref": "C04/../C05/sp.json", "reason": {"en": "x", "es": "x"}}))
    p = run(copy)
    assert p.returncode == 1, p.stdout + p.stderr
    assert "manifests/C04.json" in p.stdout and "depends_on/" in p.stdout and "/ref" in p.stdout


def test_a_min_items_violation_fails(copy):
    # the readiness holds one row per catalog row: an empty list violates minItems
    edit(copy / "data" / "derived" / "readiness.json", lambda d: d.update(contracts=[]))
    p = run(copy)
    assert p.returncode == 1, p.stdout + p.stderr
    assert "readiness.json" in p.stdout


def test_the_provider_tree_and_the_examples_are_checked(copy):
    # the product keeps no document in the provider tree today: the test puts a copy of a manifest there, broken, and breaks the
    # example of the test-result row (the one example the catalog keeps under docs/contracts/examples/)
    twin = copy / "docs" / "contracts" / "fixtures" / "data" / "derived" / "manifests" / "C04.json"
    twin.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(copy / "data" / "derived" / "manifests" / "C04.json", twin)
    assert run(copy).returncode == 0, "the provider-tree twin of a valid manifest is valid under the same globs"
    edit(twin, lambda m: m.update(schema="contraste.manifest/v9"))
    edit(copy / "docs" / "contracts" / "examples" / "common.test-result.json", lambda d: d.update(light="blue"))
    p = run(copy)
    assert p.returncode == 1, p.stdout + p.stderr
    assert "fixtures/data/derived/manifests/C04.json" in p.stdout and "common.test-result.json" in p.stdout


def test_a_document_that_is_not_json_fails(copy):
    (copy / "data" / "derived" / "C04" / "sp.json").write_text("{not json", encoding="utf-8")
    p = run(copy)
    assert p.returncode == 1, p.stdout + p.stderr
    assert "C04/sp.json" in p.stdout


def test_an_absent_index_fails(copy):
    (copy / "data" / "derived" / "manifests" / "index.json").unlink()
    assert run(copy).returncode == 1


def test_a_declared_partial_bake_is_valid(copy):
    # an absent document is check_artifacts.py's business (it has the readiness to tell declared from undeclared)
    (copy / "data" / "derived" / "C04" / "sp.json").unlink()
    assert run(copy).returncode == 0


# ---------------------------------------------------------------- 0.09.000: the catalog's `documents` column drives the guard
# A product takes scripts/check_documents.py verbatim; what it validates is the catalog's `documents` cells (globs relative to
# the repository root, `!` excludes, `path#Component` for an OpenAPI row, `-` for none). These tests run the guard, copied as a
# product would copy it, on a tree whose catalog names other documents than the template's.
HEADER = "| id | schema file | example | documents | missing-data behavior |\n|---|---|---|---|---|\n"
BASE = "https://contraste.fasl-work.com/contracts/"
DIALECT = "https://json-schema.org/draft/2020-12/schema"
BLAST = {"$schema": DIALECT, "$id": BASE + "blast-record.schema.json", "type": "object", "required": ["site", "burden"], "additionalProperties": False,
         "properties": {"site": {"type": "string", "pattern": "^S[0-9]+$"}, "burden": {"type": "number", "minimum": 0}}}
CASE = {"$schema": DIALECT, "$id": BASE + "case-artifact.schema.json", "type": "object", "required": ["case", "points"], "additionalProperties": False,
        "properties": {"case": {"type": "string"}, "points": {"type": "array", "minItems": 1, "items": {"type": "number"}}}}


def write_json(path: Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


def product(tmp_path: Path, rows: list[str]) -> Path:
    """A repository that is not the template: its own schemas and catalog rows, the guard copied in verbatim."""
    r = tmp_path / "product"
    for rel in ("scripts/check_documents.py", "scripts/check_contracts.py", "tests/contracts/contract_schemas.py",
                "docs/contracts/api.openapi.json"):
        (r / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, r / rel)
    shutil.copytree(ROOT / "docs" / "contracts" / "schemas", r / "docs" / "contracts" / "schemas")
    write_json(r / "docs/contracts/schemas/blast-record.schema.json", BLAST)
    write_json(r / "docs/contracts/schemas/case-artifact.schema.json", CASE)
    (r / "docs/contracts/catalog.md").write_text("# Catalog\n\n## Contracts\n\n" + HEADER + "\n".join(rows) + "\n", encoding="utf-8")
    return r


def blast_row(documents: str = "data/derived/blasts/*.json", missing: str = "partial: a blast file is absent") -> str:
    return (f"| blast-record | docs/contracts/schemas/blast-record.schema.json | docs/contracts/examples/blast-record.json | "
            f"{documents} | {missing} |")


def case_row(documents: str = "data/derived/*/case.json") -> str:
    return (f"| case-artifact | docs/contracts/schemas/case-artifact.schema.json | - | {documents} | "
            f"partial: an artifact is absent |")


def run_in(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(root / "scripts" / "check_documents.py"), str(root)],
                          capture_output=True, text=True, cwd=root)


def test_a_product_with_other_documents_is_validated_with_no_code_change(tmp_path):
    r = product(tmp_path, [blast_row(), case_row()])
    write_json(r / "data/derived/blasts/b1.json", {"site": "S1", "burden": 3.5})
    write_json(r / "data/derived/blasts/b2.json", {"site": "S2", "burden": 0})
    write_json(r / "data/derived/CASE1/case.json", {"case": "c", "points": [1, 2]})
    write_json(r / "docs/contracts/examples/blast-record.json", {"site": "S9", "burden": 1})
    p = run_in(r)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "documents: 4 valid" in p.stdout


def test_an_invalid_document_fails_with_its_path_and_schema(tmp_path):
    r = product(tmp_path, [blast_row(), case_row()])
    write_json(r / "data/derived/blasts/b1.json", {"site": "bad", "burden": 3.5})
    write_json(r / "data/derived/CASE1/case.json", {"case": "c", "points": []})
    p = run_in(r)
    assert p.returncode == 1, p.stdout + p.stderr
    assert "documents: INVALID" in p.stdout
    assert "data/derived/blasts/b1.json: [blast-record]" in p.stdout and "site" in p.stdout
    assert "data/derived/CASE1/case.json: [case-artifact]" in p.stdout and "points" in p.stdout


def test_a_file_matched_by_two_rows_fails(tmp_path):
    r = product(tmp_path, [blast_row("data/derived/blasts/*.json"), case_row("data/derived/blasts/*.json")])
    write_json(r / "data/derived/blasts/b1.json", {"site": "S1", "burden": 3.5})
    p = run_in(r)
    assert p.returncode == 1, p.stdout + p.stderr
    assert "data/derived/blasts/b1.json" in p.stdout and "blast-record" in p.stdout and "case-artifact" in p.stdout
    assert "more than one row" in p.stdout


def test_an_exclusion_glob_leaves_the_file_to_its_own_row(tmp_path):
    r = product(tmp_path, [blast_row("data/derived/*/*.json, !data/derived/*/case.json"), case_row()])
    write_json(r / "data/derived/CASE1/case.json", {"case": "c", "points": [1]})
    write_json(r / "data/derived/CASE1/b.json", {"site": "S1", "burden": 1})
    p = run_in(r)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "documents: 2 valid" in p.stdout


def test_an_openapi_row_validates_against_its_component(tmp_path):
    api = ("| api | docs/contracts/api.openapi.json | docs/contracts/examples/api-not-found.json | "
           "docs/contracts/examples/api-not-found.json#NotFoundBody | missing: the API answers 404 |")
    r = product(tmp_path, [api])
    write_json(r / "docs/contracts/examples/api-not-found.json", {"detail": "no such case"})
    p = run_in(r)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "documents: 1 valid" in p.stdout  # the example cell names the same file: one document, counted once
    edit(r / "docs/contracts/examples/api-not-found.json", lambda d: d.update(state="gone"))
    p = run_in(r)
    assert p.returncode == 1 and "api-not-found.json: [NotFoundBody]" in p.stdout, p.stdout


def test_the_provider_tree_takes_the_same_globs(tmp_path):
    r = product(tmp_path, [blast_row(), case_row()])
    fx = r / "docs/contracts/fixtures"
    write_json(fx / "data/derived/blasts/f1.json", {"site": "S1", "burden": 1})
    write_json(fx / "data/derived/CASE1/case.json", {"case": "c", "points": [1]})
    assert "documents: 2 valid" in run_in(r).stdout
    write_json(fx / "data/derived/blasts/f1.json", {"site": "S1", "burden": -1})
    p = run_in(r)
    assert p.returncode == 1 and "docs/contracts/fixtures/data/derived/blasts/f1.json: [blast-record]" in p.stdout, p.stdout


def test_a_dash_row_validates_nothing_but_its_example(tmp_path):
    r = product(tmp_path, [blast_row("-")])
    write_json(r / "docs/contracts/examples/blast-record.json", {"site": "bad", "burden": 1})
    p = run_in(r)
    assert p.returncode == 1 and "docs/contracts/examples/blast-record.json: [blast-record]" in p.stdout, p.stdout


def test_a_document_no_row_covers_fails(tmp_path):
    r = product(tmp_path, [blast_row(), case_row()])
    write_json(r / "data/derived/blasts/b1.json", {"site": "S1", "burden": 1})
    write_json(r / "data/derived/extra/stray.json", {"anything": True})
    write_json(r / "models/orphan.json", {"anything": True})
    p = run_in(r)
    assert p.returncode == 1, p.stdout + p.stderr
    assert "data/derived/extra/stray.json: covered by no row" in p.stdout
    assert "models/orphan.json: covered by no row" in p.stdout


def test_an_absent_single_path_document_of_a_missing_row_is_reported(tmp_path):
    r = product(tmp_path, [blast_row("data/derived/index.json", missing="missing: no inventory"), case_row()])
    p = run_in(r)
    assert p.returncode == 1 and "data/derived/index.json: absent" in p.stdout, p.stdout
    assert run_in(product(tmp_path / "two", [blast_row(), case_row()])).returncode == 0  # a partial row's glob may match nothing


def test_a_catalog_without_the_column_fails_naming_it(tmp_path):
    r = product(tmp_path, [])
    (r / "docs/contracts/catalog.md").write_text(
        "## Contracts\n\n| id | schema file | example |\n|---|---|---|\n| blast-record | docs/contracts/schemas/blast-record.schema.json | - |\n",
        encoding="utf-8")
    p = run_in(r)
    assert p.returncode == 1 and "documents" in p.stdout and re.search(r"template \d\.\d\d\.\d{3}", p.stdout), p.stdout


def test_the_guard_names_no_document_of_the_product():
    src = SCRIPT.read_text(encoding="utf-8")
    text = (ROOT / "docs/contracts/catalog.md").read_text(encoding="utf-8")
    table = text.split("\n## Contracts\n")[1].split("\n## ")[0]
    ids = re.findall(r"^\| ([a-z][a-z0-9-]*) \| \d", table, re.M)
    assert len(ids) >= 80, ids
    named = [i for i in ids if re.search(rf"(?<![A-Za-z0-9_-]){re.escape(i)}(?![A-Za-z0-9_-])", src)]
    assert named == [], f"check_documents.py names the contract(s) {named}: it must read the catalog"
    for name in ("NotFoundBody", "UnavailableBody", "surrogate", "manifest", "trace", "params", "blast-record"):
        assert name not in src, f"check_documents.py names {name!r}"
