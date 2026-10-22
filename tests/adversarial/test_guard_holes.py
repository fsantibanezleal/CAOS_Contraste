"""The holes an adversarial review found in the spec-area guards (0.05.000), one plant each: a defect planted in a copy of
the repository's real files, the real guard run on it, exit 1 and the message that names the defect expected. The ids
(S-1a, C-3, T-8, B-1 ...) are the rows of the review's refutation table
(CAOS_MANAGE wip/product-template/review-0-05-000-guards-2026-10-11.md, D2).

Each plant copies only the inputs its guard reads (`make_tree`), so the suite stays cheap; every plant asserts the guard
printed, so a guard that never ran cannot pass."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from planting import add_schema, edit, git_commit, guard, make_tree, set_cell

SDD_INPUTS = ("scripts/*.py", "docs/design", "tests", "data", "frontend/src/**/*.test.ts", "frontend/src/**/*.test.tsx", "frontend/scripts",
              "requirements*.txt", "data-pipeline/requirements.txt", "content", "frontend/public/executive")
TECH_INPUTS = ("scripts/check_tech_matrix.py", "docs/design/SDD.md", "requirements*.txt", "data-pipeline/requirements.txt",
               "notebooks/requirements.txt", "pyproject.toml", "frontend/package.json", "frontend/package-lock.json", "data-pipeline/requirements*.txt")
VERSIONS_INPUTS = ("scripts/*.py", "docs/contracts")
BUDGET_INPUTS = ("scripts/check_ci_budget.py", ".github", "requirements-precompute.txt")

FEATURES = "docs/design/features"
WORKBENCH = f"{FEATURES}/workbench/requirements.md"
WORKBENCH_VALIDATION = f"{FEATURES}/workbench/validation.md"
SDD = "docs/design/SDD.md"
GHOST_PY = "tests/adversarial/test_ghosts.py"
GHOST_TS = "frontend/src/ghost.test.ts"


@pytest.fixture
def sdd_repo(tmp_path: Path) -> Path:
    return add_schema(make_tree(tmp_path / "repo", *SDD_INPUTS))


def gate(repo: Path, cell: str, *, rid: str = "EX-001", rel: str = WORKBENCH) -> None:
    set_cell(repo, rel, rid, 2, cell)


def sdd(repo: Path):
    return guard(repo, "check_sdd.py")


def test_the_slim_tree_passes_the_guard_it_stands_for(sdd_repo: Path) -> None:
    r = guard(sdd_repo, "check_sdd.py", ok_marker="check_sdd: OK")
    assert r.returncode == 0, r.stdout


# ---------------------------------------------------------------- check_sdd: a name that is not a test (F-S1)

PY_GHOSTS = {
    "S-1a a def inside a string": ('DOC = """\ndef test_ghost():\n    pass\n"""\n', "test_ghost"),
    "S-1a a def in a comment": ("# def test_ghost():\n#     pass\n", "test_ghost"),
    "S-1i a nested def": ("def helper():\n    def test_ghost():\n        pass\n", "test_ghost"),
    "S-3a a skipped test": ("import pytest\n\n\n@pytest.mark.skip\ndef test_ghost():\n    assert False\n", "test_ghost"),
    "S-3a skip with a reason": ('import pytest\n\n\n@pytest.mark.skip(reason="later")\ndef test_ghost():\n    assert False\n', "test_ghost"),
    "S-3a skipif(True)": ('import pytest\n\n\n@pytest.mark.skipif(True, reason="never")\ndef test_ghost():\n    assert False\n', "test_ghost"),
    "S-3a a skipped class": ("import pytest\n\n\n@pytest.mark.skip\nclass TestGhost:\n    def test_ghost(self):\n        assert False\n", "test_ghost"),
    "S-3a pytestmark skip": ("import pytest\n\npytestmark = pytest.mark.skip\n\n\ndef test_ghost():\n    assert False\n", "test_ghost"),
    "S-3a a module-level skip": ('import pytest\n\npytest.skip("x", allow_module_level=True)\n\n\ndef test_ghost():\n    assert False\n', "test_ghost"),
}


TS_GHOSTS = {
    "S-1b a // comment": "// it('adversarial: ghost', () => {})\n",
    "S-1c a block comment": "/* it('adversarial: ghost', () => {}) */\n",
    "S-1c a string": "const DOC = \"test('adversarial: ghost', () => {})\";\n",
    "S-1c a template string": "const DOC = `\nit('adversarial: ghost', () => {})\n`;\n",
    "S-1f inside another body": "it('real one', () => { const s = \"it('adversarial: ghost'\"; expect(s).toBe(s) })\n",
    "S-1f a test nested in a test": "it('real one', () => {\n  it('adversarial: ghost', () => {})\n})\n",
    "S-3b it.skip": "it.skip('adversarial: ghost', () => {})\n",
    "S-3b it.todo": "it.todo('adversarial: ghost')\n",
    "S-3c a skip option": "it('adversarial: ghost', { skip: true }, () => {})\n",
    "S-3c a describe block": "describe('adversarial: ghost', () => {})\n",
}


# ---------------------------------------------------------------- check_sdd: a path that is not a test (F-S2)

# ---------------------------------------------------------------- check_sdd: validation rows (F-S7)

# ---------------------------------------------------------------- check_sdd: rows that vanish (F-S3)

def _requirements(repo: Path) -> str:
    return (repo / WORKBENCH).read_bytes().decode("utf-8")


def _row(repo: Path, rid: str) -> str:
    return next(ln for ln in _requirements(repo).split("\n") if ln.startswith(f"| {rid} "))


# ---------------------------------------------------------------- check_sdd: statuses and folders (F-S4)

def test_sdd_s6e_a_feature_folder_without_requirements(sdd_repo: Path) -> None:
    folder = sdd_repo / FEATURES / "newfeat"
    folder.mkdir()
    (folder / "spec.md").write_text("a spec with no requirements\n", encoding="utf-8")
    (folder / "validation.md").write_text("nothing\n", encoding="utf-8")
    r = sdd(sdd_repo)
    assert r.returncode == 1 and "newfeat" in r.stdout and "requirements.md" in r.stdout, r.stdout


# ---------------------------------------------------------------- check_sdd: the SDD itself (F-S5, F-S6)

def _sdd_text(repo: Path) -> str:
    return (repo / SDD).read_bytes().decode("utf-8")


def _section(text: str, name: str) -> tuple[int, int]:
    a = text.index(f"## {name}\n")
    b = text.find("\n## ", a + 1)
    return a, (len(text) if b == -1 else b + 1)


def test_sdd_s7e_headings_only_inside_a_code_fence(sdd_repo: Path) -> None:
    text = _sdd_text(sdd_repo)
    a, _ = _section(text, "Problem and non-goals")
    b, _ = _section(text, "Research basis")
    names = ("Problem and non-goals", "Executive brief", "Sizing and contracts", "Technology and versions", "Lanes",
             "Method ladder", "Cases", "Oracles", "Deploy driver", "Risks and kill criteria", "ADR fit")
    fence = "```\n" + "".join(f"## {n}\n" for n in names) + "```\n\n"
    # the real sections other than the research basis and the resources are removed, their headings kept only in a fence
    keep = ("Research basis", "Resources")
    body = "".join(text[slice(*_section(text, k))] for k in keep)
    (sdd_repo / SDD).write_bytes((text[:a] + fence + body).encode("utf-8"))
    r = sdd(sdd_repo)
    assert r.returncode == 1 and "Lanes" in r.stdout and "no section" in r.stdout, r.stdout


def test_sdd_s7a_one_heading_for_ten_sections_and_empty_bodies(sdd_repo: Path) -> None:
    text = _sdd_text(sdd_repo)
    research = text[slice(*_section(text, "Research basis"))]
    resources = text[slice(*_section(text, "Resources"))]
    names = ("Problem and non-goals", "Sizing and contracts", "Technology and versions", "Lanes", "Method ladder", "Cases",
             "Oracles", "Deploy driver", "Risks and kill criteria", "ADR fit")
    (sdd_repo / SDD).write_bytes((f"# SDD\n\n{resources}\n## {', '.join(names)}\n\nnothing\n\n{research}").encode("utf-8"))
    r = sdd(sdd_repo)
    assert r.returncode == 1 and "Lanes" in r.stdout, r.stdout


def test_sdd_a_section_with_no_body_and_one_out_of_order(sdd_repo: Path) -> None:
    text = _sdd_text(sdd_repo)
    a, b = _section(text, "Lanes")
    (sdd_repo / SDD).write_bytes((text[:a] + "## Lanes\n\n" + text[b:]).encode("utf-8"))
    r = sdd(sdd_repo)
    assert r.returncode == 1 and "Lanes" in r.stdout and "empty" in r.stdout, r.stdout


def _research(repo: Path, body: str) -> None:
    text = _sdd_text(repo)
    a, b = _section(text, "Research basis")
    (repo / SDD).write_bytes((text[:a] + "## Research basis\n\n" + body + "\n" + text[b:]).encode("utf-8"))


def test_sdd_sr1_placeholder_urls_and_unverified_inside_a_sentence(sdd_repo: Path) -> None:
    _research(sdd_repo, "- http://a.example\n- http://b.example\n- http://c.example\nNothing here is UNVERIFIED-free.\n")
    r = sdd(sdd_repo)
    assert r.returncode == 1 and "research basis" in r.stdout.lower(), r.stdout


def test_sdd_sr2_one_work_cited_three_ways(sdd_repo: Path) -> None:
    doi = "10.1098/rspa.1927.0118"
    _research(sdd_repo, f"- {doi}\n- https://doi.org/{doi}\n- http://doi.org/{doi}\n\nUNVERIFIED: none\n")
    r = sdd(sdd_repo)
    assert r.returncode == 1 and "cites 1 source" in r.stdout, r.stdout


def test_sdd_sr_unverified_must_start_a_line(sdd_repo: Path) -> None:
    text = _sdd_text(sdd_repo)
    assert "\nUNVERIFIED:" in text
    (sdd_repo / SDD).write_bytes(text.replace("\nUNVERIFIED:", "\nStill, nothing is UNVERIFIED:", 1).encode("utf-8"))
    r = sdd(sdd_repo)
    assert r.returncode == 1 and "UNVERIFIED" in r.stdout, r.stdout


def test_sdd_sres_placeholder_cells_and_one_row_for_four_stages(sdd_repo: Path) -> None:
    text = _sdd_text(sdd_repo)
    a, b = _section(text, "Resources")
    table = ("## Resources\n\n| stage | memory | disk | time | where it runs |\n|---|---|---|---|---|\n"
             "| bake, tests, build, deploy | - | ? | TODO | unknown |\n\n")
    (sdd_repo / SDD).write_bytes((text[:a] + table + text[b:]).encode("utf-8"))
    r = sdd(sdd_repo)
    assert r.returncode == 1 and "Resources" in r.stdout, r.stdout


# ---------------------------------------------------------------- check_contract_versions (F-C1, F-C2, F-C3)

TRACE = "docs/contracts/schemas/trace.schema.json"
CATALOG = "docs/contracts/catalog.md"
LOCK = "docs/contracts/versions.lock.json"


@pytest.fixture
def versions_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = make_tree(tmp_path / "repo", *VERSIONS_INPUTS)
    return repo, git_commit(repo)


def _schema(repo: Path) -> dict:
    return json.loads((repo / TRACE).read_text(encoding="utf-8"))


def _write_schema(repo: Path, doc: dict) -> None:
    (repo / TRACE).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")


def _bump(repo: Path, new: str, kind: str) -> None:
    edit(repo, CATALOG, "| trace | 1.0.0 |", f"| trace | {new} |")
    anchor = "| surrogate-model | 1.0.0 | 2026-10-11 |"  # the History row after trace's own: the new row goes between
    edit(repo, CATALOG, anchor, f"| trace | {new} | 2026-10-12 | planted | {kind} |\n{anchor}")
    guard(repo, "check_contract_versions.py", "--update")  # writes the lock, then reports: exit 1 when the History kind is wrong


def test_versions_the_base_is_the_branchs_own_unmodified_state(versions_repo) -> None:
    repo, base = versions_repo
    r = guard(repo, "check_contract_versions.py", "--base", base, ok_marker="check_contract_versions: OK")
    assert r.returncode == 0, r.stdout


def test_versions_a_base_that_cannot_be_resolved_never_passes_silently(versions_repo) -> None:
    repo, _ = versions_repo
    r = guard(repo, "check_contract_versions.py", "--base", "origin/nowhere")
    assert r.returncode == 1 and "fetch-depth: 0" in r.stdout, r.stdout


# ---------------------------------------------------------------- check_tech_matrix (F-T1 to F-T5)

@pytest.fixture
def tech_repo(tmp_path: Path) -> Path:
    return make_tree(tmp_path / "repo", *TECH_INPUTS)


def _tech(repo: Path):
    return guard(repo, "check_tech_matrix.py")


def test_tech_the_slim_tree_passes(tech_repo: Path) -> None:
    r = guard(tech_repo, "check_tech_matrix.py", ok_marker="check_tech_matrix: OK")
    assert r.returncode == 0, r.stdout


def test_tech_t1b_a_pin_added_only_in_requirements_api(tech_repo: Path) -> None:
    api = tech_repo / "requirements-api.txt"
    api.write_text(api.read_text(encoding="utf-8") + "uvicorn[standard]==0.54.0\nfastapi==0.144.0\n", encoding="utf-8")
    r = _tech(tech_repo)
    assert r.returncode == 1 and "uvicorn" in r.stdout and "fastapi" in r.stdout, r.stdout


def test_tech_t3_a_range_in_package_json_that_the_lock_does_not_record(tech_repo: Path) -> None:
    edit(tech_repo, "frontend/package.json", '"react": "^19.3.0"', '"react": "^19.0.0"')
    r = _tech(tech_repo)
    assert r.returncode == 1 and "react" in r.stdout, r.stdout


def test_tech_t3b_a_greater_than_range(tech_repo: Path) -> None:
    edit(tech_repo, "frontend/package.json", '"vite": "^8.3.2"', '"vite": ">=8.0.0"')
    r = _tech(tech_repo)
    assert r.returncode == 1 and "vite" in r.stdout, r.stdout


def test_tech_t3c_an_x_range_that_the_sdd_repeats(tech_repo: Path) -> None:
    edit(tech_repo, "frontend/package.json", '"react": "^19.3.0"', '"react": "19.x"')
    edit(tech_repo, SDD, "| react | 19.3.0 |", "| react | 19.x |")
    r = _tech(tech_repo)
    assert r.returncode == 1 and "react" in r.stdout, r.stdout


def test_tech_t8_a_range_the_lock_does_not_satisfy(tech_repo: Path) -> None:
    edit(tech_repo, "frontend/package.json", '"vite": "^8.3.2"', '"vite": "^9.0.0"')
    r = _tech(tech_repo)
    assert r.returncode == 1 and "vite" in r.stdout, r.stdout


def test_tech_a_lock_whose_version_does_not_satisfy_its_own_spec(tech_repo: Path) -> None:
    lock = tech_repo / "frontend/package-lock.json"
    doc = json.loads(lock.read_text(encoding="utf-8"))
    doc["packages"][""]["devDependencies"]["vite"] = "^9.0.0"
    lock.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    edit(tech_repo, "frontend/package.json", '"vite": "^8.3.2"', '"vite": "^9.0.0"')
    r = _tech(tech_repo)
    assert r.returncode == 1 and "vite" in r.stdout and "8.3.2" in r.stdout, r.stdout


def test_tech_t4_a_dependency_in_optional_dependencies(tech_repo: Path) -> None:
    pkg = tech_repo / "frontend/package.json"
    doc = json.loads(pkg.read_text(encoding="utf-8"))
    doc["optionalDependencies"] = {"left-pad": "^1.3.0"}
    pkg.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    r = _tech(tech_repo)
    assert r.returncode == 1 and "left-pad" in r.stdout, r.stdout


def test_tech_t5b_the_same_package_pinned_twice_with_different_versions(tech_repo: Path) -> None:
    path = tech_repo / "requirements-precompute.txt"
    path.write_text("numpy==2.4.7\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
    r = _tech(tech_repo)
    assert r.returncode == 1 and "numpy" in r.stdout and "2.4.7" in r.stdout, r.stdout


def test_tech_t6_an_editable_unpinned_requirement(tech_repo: Path) -> None:
    path = tech_repo / "requirements-dev.txt"
    path.write_text(path.read_text(encoding="utf-8") + "-e git+https://github.com/example/unpinned.git#egg=unpinned\n", encoding="utf-8")
    r = _tech(tech_repo)
    assert r.returncode == 1 and "unpinned" in r.stdout, r.stdout


def test_tech_t7_a_wildcard_pin(tech_repo: Path) -> None:
    edit(tech_repo, "data-pipeline/requirements.txt", "numpy==2.4.6", "numpy==2.*")
    edit(tech_repo, SDD, "| numpy | 2.4.6 |", "| numpy | 2.* |")
    r = _tech(tech_repo)
    assert r.returncode == 1 and "numpy" in r.stdout, r.stdout


# ---------------------------------------------------------------- check_ci_budget (F-B1)

@pytest.fixture
def budget_repo(tmp_path: Path) -> Path:
    return make_tree(tmp_path / "repo", *BUDGET_INPUTS)


ALLOWED = "pip install pytest==9.1.1 && python -m pytest tests/adversarial -q"


def _step(repo: Path, command: str) -> None:
    edit(repo, ".github/workflows/ci.yml", f"run: {ALLOWED}", command)


def test_ci_budget_the_allowance_itself_passes(budget_repo: Path) -> None:
    r = guard(budget_repo, "check_ci_budget.py", ok_marker="ci budget: OK")
    assert r.returncode == 0, r.stdout


# ---------------------------------------------------------------- the CRLF test must prove the copy was hashed (F-A1)

# ================================================================ the re-review of 0.05.000 (rows of its D3), one plant each
# CAOS_MANAGE wip/product-template/rereview-0-05-000-2026-10-12.md. The plants edit the real SDD and the real workflow.

def _replace_line(repo: Path, rel: str, prefix: str, new: str) -> None:
    """Replace the whole line that starts with ``prefix``; fails when there is none (a plant that plants nothing)."""
    path = repo / rel
    lines = path.read_bytes().decode("utf-8").split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    assert len(hits) == 1, f"{rel}: {len(hits)} lines start with {prefix!r}"
    lines[hits[0]] = new
    path.write_bytes("\n".join(lines).encode("utf-8"))


def _brief_span(text: str) -> tuple[int, int]:
    """The brief section: from its heading to the next level-2 heading."""
    return _section(text, "Executive brief")


def test_sdd_rereview_m3b_a_brief_after_resources_when_the_headings_are_numbered(sdd_repo: Path) -> None:
    text = _sdd_text(sdd_repo)
    a, b = _brief_span(text)
    brief = text[a:b]
    text = text[:a] + text[b:]
    at = text.index("## Lanes\n")
    text = text[:at] + brief + text[at:]
    text = text.replace("## Problem and non-goals", "## 1. Problem and non-goals", 1)
    (sdd_repo / SDD).write_bytes(text.encode("utf-8"))
    r = sdd(sdd_repo)
    assert r.returncode == 1 and "right after" in r.stdout, r.stdout


def test_sdd_rereview_xs2_numbered_headings_in_place_pass(sdd_repo: Path) -> None:
    text = _sdd_text(sdd_repo)
    text = text.replace("## Problem and non-goals", "## 1. Problem and non-goals", 1).replace("## Executive brief", "## 2. Executive brief", 1)
    (sdd_repo / SDD).write_bytes(text.encode("utf-8"))
    r = sdd(sdd_repo)
    assert r.returncode == 0, r.stdout


def test_sdd_rereview_m3d_the_brief_inside_a_tilde_fence_with_a_backtick_line(sdd_repo: Path) -> None:
    text = _sdd_text(sdd_repo)
    a, b = _brief_span(text)
    (sdd_repo / SDD).write_bytes((text[:a] + "~~~\n```\n" + text[a:b] + "```\n~~~\n\n" + text[b:]).encode("utf-8"))
    r = sdd(sdd_repo)
    assert r.returncode == 1, r.stdout


# ---- a validation gate that skips for lack of a tool is not a gate that ran (Q1, S-3d), and the name is a prefix (M9c)

CONDITIONAL_GATE = "`tests/adversarial/test_requirements_refuted.py::test_a_build_without_the_routes_or_the_theme_script_fails`"
RUNNING_GATE = "`tests/adversarial/test_guard_holes.py::test_the_slim_tree_passes_the_guard_it_stands_for`"


# ---- check_ci_budget: what YAML reads is what is judged (M10a-d)
