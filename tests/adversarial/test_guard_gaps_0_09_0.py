"""Plants for four gaps of the verbatim guards found while releasing 0.09.000 (requirements WB-016 to WB-019):

- a tracked file with no suffix is scanned by the content-standards guard (an em-dash in `scripts/.template_residue_allow` passed);
- a committed document that is not JSON (a model file, a table) is left to its row's contract test, which the row must name;
- the technology-matrix guard reads an npm alias `npm:<package>@<version>`;
- no file a product takes verbatim names the owner. The personal name is refused; the GitHub handle `fsantibanezleal` is the
  repositories' owner identifier (it stands in source URLs, for example `scripts/check_contracts.py`) and stays allowed."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
from planting import ROOT, edit, git_commit, guard, make_tree, set_cell

DASH = "\u2014"

# ---------------------------------------------------------------- content standards: files with no suffix (WB-016)


@pytest.fixture
def standards(tmp_path: Path) -> Path:
    return make_tree(tmp_path / "repo", "scripts/check_content_standards.py", "scripts/.template_residue_allow", "VERSION")


def track(repo: Path) -> None:
    if not (repo / ".git").exists():
        git_commit(repo)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)


def test_the_real_suffixless_files_of_the_template_pass_the_guard(standards: Path) -> None:
    track(standards)
    r = guard(standards, "check_content_standards.py", ok_marker="check_content_standards: OK")
    assert r.returncode == 0, r.stdout


@pytest.mark.parametrize("rel", ["NOTICE", "scripts/.hidden_allow", "deploy/TARGET"])
def test_an_em_dash_in_a_tracked_file_with_no_suffix_fails(standards: Path, rel: str) -> None:
    path = standards / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# justified {DASH} it exists for the rare collision\n", encoding="utf-8")
    track(standards)
    r = guard(standards, "check_content_standards.py")
    assert r.returncode == 1 and f"{rel}:1:" in r.stdout and "em-dash" in r.stdout, r.stdout


def test_a_suffixless_file_that_is_not_text_is_not_read(standards: Path) -> None:
    (standards / "blob").write_bytes(b"\xff\xfe\x00" + DASH.encode("utf-8") + b"\x80")
    track(standards)
    r = guard(standards, "check_content_standards.py", ok_marker="check_content_standards: OK")
    assert r.returncode == 0, r.stdout


def test_the_residue_allow_file_of_the_template_has_no_em_dash() -> None:
    assert DASH not in (ROOT / "scripts" / ".template_residue_allow").read_text(encoding="utf-8")


# ---------------------------------------------------------------- documents that are not JSON (WB-017)

DOC_INPUTS = ("scripts/check_documents.py", "scripts/check_contracts.py", "tests/contracts/contract_schemas.py", "docs/contracts", "data", "data-pipeline/config", "models")
CATALOG = "docs/contracts/catalog.md"
DOCUMENTS, PRODUCER, CONSUMER = 5, 6, 7  # the columns of the test-result row, whose documents cell is "-"


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    return make_tree(tmp_path / "repo", *DOC_INPUTS)


def declare_binary(repo: Path, glob: str, rel: str, payload: bytes) -> None:
    set_cell(repo, CATALOG, "test-result", DOCUMENTS, glob)
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)


def test_a_declared_onnx_file_passes_when_its_row_names_a_test(docs: Path) -> None:
    declare_binary(docs, "models/*.onnx", "models/net.onnx", b"\x08\x07onnx\x00\xff\xfe")
    r = guard(docs, "check_documents.py")
    assert r.returncode == 0 and "documents:" in r.stdout and "not JSON" in r.stdout and "models/net.onnx" in r.stdout, r.stdout


def test_a_declared_onnx_file_fails_when_its_row_names_no_test(docs: Path) -> None:
    declare_binary(docs, "models/*.onnx", "models/net.onnx", b"\x08\x07onnx\x00\xff\xfe")
    set_cell(docs, CATALOG, "test-result", PRODUCER, "-")
    set_cell(docs, CATALOG, "test-result", CONSUMER, "")
    r = guard(docs, "check_documents.py")
    assert r.returncode == 1 and "models/net.onnx" in r.stdout and "test-result" in r.stdout and "producer test" in r.stdout, r.stdout


def test_a_declared_csv_table_passes_with_a_test_and_fails_without_one(docs: Path) -> None:
    declare_binary(docs, "data/tables/*.csv", "data/tables/rates.csv", b"a,b\n1,2\n")
    assert guard(docs, "check_documents.py").returncode == 0
    set_cell(docs, CATALOG, "test-result", PRODUCER, "-")
    set_cell(docs, CATALOG, "test-result", CONSUMER, "-")
    r = guard(docs, "check_documents.py")
    assert r.returncode == 1 and "data/tables/rates.csv" in r.stdout, r.stdout


def test_a_json_document_is_still_validated_against_its_schema(docs: Path) -> None:
    path = docs / "data/derived/C04/sp.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    del doc["case_id"]
    path.write_text(json.dumps(doc), encoding="utf-8")
    r = guard(docs, "check_documents.py")
    assert r.returncode == 1 and "[variant-agency]" in r.stdout, r.stdout


def test_a_json_file_with_a_json_suffix_that_is_not_json_still_fails(docs: Path) -> None:
    (docs / "data/derived/C04/sp.json").write_text("not json at all", encoding="utf-8")
    r = guard(docs, "check_documents.py")
    assert r.returncode == 1 and "not readable as JSON" in r.stdout, r.stdout


# ---------------------------------------------------------------- npm aliases in the technology matrix (WB-018)

TECH_INPUTS = ("scripts/check_tech_matrix.py", "docs/design/SDD.md", "requirements*.txt", "data-pipeline/requirements.txt", "notebooks/requirements.txt",
               "pyproject.toml", "frontend/package.json", "frontend/package-lock.json", "data-pipeline/requirements*.txt")
ALIAS = "zz-typescript5"
SPEC = "npm:typescript@5.9.3"


@pytest.fixture
def tech(tmp_path: Path) -> Path:
    return make_tree(tmp_path / "repo", *TECH_INPUTS)


def add_alias(repo: Path, spec: str, locked: str = "5.9.3", in_table: bool = True) -> None:
    pkg = repo / "frontend/package.json"
    doc = json.loads(pkg.read_text(encoding="utf-8"))
    doc.setdefault("devDependencies", {})[ALIAS] = spec
    pkg.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    lock_path = repo / "frontend/package-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["packages"][""].setdefault("devDependencies", {})[ALIAS] = spec
    lock["packages"][f"node_modules/{ALIAS}"] = {"name": "typescript", "version": locked, "dev": True}
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    if in_table:
        sdd = repo / "docs/design/SDD.md"
        text = sdd.read_text(encoding="utf-8")
        row = next(ln for ln in text.splitlines() if ln.startswith("| shell |"))
        sdd.write_text(text.replace(row, f"{row}\n| compiler alias | {ALIAS} | {locked} | the TypeScript 5 compiler API the contract generator needs | none |"), encoding="utf-8")


def test_an_exact_alias_listed_in_the_table_passes(tech: Path) -> None:
    add_alias(tech, SPEC)
    r = guard(tech, "check_tech_matrix.py", ok_marker="check_tech_matrix: OK")
    assert r.returncode == 0, r.stdout


def test_an_alias_with_a_range_fails(tech: Path) -> None:
    add_alias(tech, "npm:typescript@^5.9.3")
    r = guard(tech, "check_tech_matrix.py")
    assert r.returncode == 1 and ALIAS in r.stdout and "exact" in r.stdout, r.stdout


def test_an_alias_missing_from_the_table_fails(tech: Path) -> None:
    add_alias(tech, SPEC, in_table=False)
    r = guard(tech, "check_tech_matrix.py")
    assert r.returncode == 1 and ALIAS in r.stdout and "absent from the SDD technology table" in r.stdout, r.stdout


def test_an_alias_whose_lock_holds_another_version_fails(tech: Path) -> None:
    add_alias(tech, SPEC, locked="5.9.2")
    r = guard(tech, "check_tech_matrix.py")
    assert r.returncode == 1 and ALIAS in r.stdout and "5.9.2" in r.stdout, r.stdout


def test_an_alias_whose_table_row_gives_another_version_fails(tech: Path) -> None:
    add_alias(tech, SPEC)
    edit(tech, "docs/design/SDD.md", f"| {ALIAS} | 5.9.3 |", f"| {ALIAS} | 5.9.2 |")
    r = guard(tech, "check_tech_matrix.py")
    assert r.returncode == 1 and ALIAS in r.stdout and "5.9.2" in r.stdout, r.stdout


# ---------------------------------------------------------------- the owner's name in the verbatim files (WB-019)

# the personal name as a word; the GitHub handle `fsantibanezleal` in a source URL is a repository address, not the name
OWNER = re.compile(r"\b(?:Felipe|Santib[aá][nñ]ez)\b", re.I)


VERBATIM = ("scripts/check_contracts.py", "scripts/check_documents.py", "scripts/check_base_integrity.py", "tests/adversarial/conftest.py",
            "tests/adversarial/planting.py")


def verbatim_files() -> list[str]:
    """The files this product takes verbatim from the template and that carry no product content (the template's guide lists
    them in 'Files a product takes verbatim', a document the product does not keep)."""
    return sorted(VERBATIM)


def test_no_file_a_product_takes_verbatim_names_the_owner() -> None:
    named = {f: [m.group(0) for m in OWNER.finditer((ROOT / f).read_text(encoding="utf-8"))] for f in verbatim_files()}
    assert not any(named.values()), {f: v for f, v in named.items() if v}


def test_adversarial_the_owner_check_sees_a_name_in_a_comment(tmp_path: Path) -> None:
    probe = tmp_path / "probe.py"
    probe.write_text("# the rule (Felipe, 2026-10-13)\n", encoding="utf-8")
    assert OWNER.search(probe.read_text(encoding="utf-8"))
