"""Adversarial validation of the guards (0.05.000): each test copies the repository's files into a temporary tree,
plants one defect, runs the real guard as a subprocess and asserts exit 1 (or 2 where the guard says so) with the
expected message; the clean copy of every guard exits 0. Nothing here edits the repository itself.

A guard that never ran cannot pass: the helper `guard` asserts the script exists in the copy, that the process
returned an exit code and that it printed, and the clean-copy tests assert the guard's own OK line."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from planting import edit, guard

CLEAN = {
    "check_sdd.py": "check_sdd: OK",
    "check_tech_matrix.py": "check_tech_matrix: OK",
    "check_contract_versions.py": "check_contract_versions: OK",
    "check_readiness.py": "readiness: current",
}
CATALOG = "docs/contracts/catalog.md"


def test_every_guard_passes_on_the_clean_copy(repo: Path) -> None:
    for script, marker in CLEAN.items():
        r = guard(repo, script, ok_marker=marker)
        assert r.returncode == 0 and marker in r.stdout, f"{script}: {r.stdout}"
    r = guard(repo, "check_contracts.py", CATALOG, "--repo-root", ".")
    assert r.returncode == 0 and "OK:" in r.stdout, r.stdout
    r = guard(repo, "check_skeleton.py", CATALOG)
    assert r.returncode == 0 and "every boundary is real" in r.stdout, r.stdout


# ---------------------------------------------------------------- check_sdd

def test_sdd_a_validation_table_that_omits_one_requirement(repo: Path) -> None:
    path = repo / "docs/design/features/contracts/validation.md"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    kept = [ln for ln in lines if not ln.startswith("| CT-014 ")]
    assert len(kept) == len(lines) - 1
    path.write_text("".join(kept), encoding="utf-8")
    r = guard(repo, "check_sdd.py")
    assert r.returncode == 1 and "CT-014" in r.stdout and "no validation row" in r.stdout, r.stdout


def test_sdd_a_research_basis_with_two_sources(repo: Path) -> None:
    sdd = repo / "docs/design/SDD.md"
    text = sdd.read_text(encoding="utf-8")
    start = text.index("## Research basis")
    end = text.index("## Sizing and contracts")
    two = ("## Research basis\n\n- Altman 1968, https://doi.org/10.1111/j.1540-6261.1968.tb00843.x\n"
           "- Merton 1974, https://doi.org/10.1111/j.1540-6261.1974.tb03058.x\n\nUNVERIFIED: none\n\n")
    sdd.write_text(text[:start] + two + text[end:], encoding="utf-8")
    r = guard(repo, "check_sdd.py")
    assert r.returncode == 1 and "cites 2 sources" in r.stdout, r.stdout


EXEC = "content/executive.json"
PUBLIC = "frontend/public"


def _load(repo: Path) -> dict:
    return json.loads((repo / EXEC).read_text(encoding="utf-8"))


def _save(repo: Path, data: dict) -> None:
    (repo / EXEC).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_sdd_the_executive_brief_removed(repo: Path) -> None:
    sdd = repo / "docs/design/SDD.md"
    text = sdd.read_text(encoding="utf-8")
    sdd.write_text(text[:text.index("## Executive brief")] + text[text.index("## Research basis"):], encoding="utf-8")
    r = guard(repo, "check_sdd.py")
    assert r.returncode == 1 and "Executive brief" in r.stdout and "06_executive-brief.md" in r.stdout, r.stdout


def test_sdd_the_executive_brief_moved_to_the_end(repo: Path) -> None:
    sdd = repo / "docs/design/SDD.md"
    text = sdd.read_text(encoding="utf-8")
    a, b = text.index("## Executive brief"), text.index("## Research basis")
    sdd.write_text(text[:a] + text[b:] + "\n" + text[a:b], encoding="utf-8")
    r = guard(repo, "check_sdd.py")
    assert r.returncode == 1 and "right after" in r.stdout, r.stdout


def test_executive_view_the_data_file_removed_or_broken(repo: Path) -> None:
    data = _load(repo)
    del data["pain"]["bearers"][1]["cost"]
    data["invented_field"] = "x"
    _save(repo, data)
    r = guard(repo, "check_sdd.py")
    assert r.returncode == 1 and "pain.bearers[1].cost" in r.stdout and "invented_field" in r.stdout, r.stdout
    (repo / EXEC).unlink()
    r = guard(repo, "check_sdd.py")
    assert r.returncode == 1 and EXEC in r.stdout and "missing" in r.stdout, r.stdout


def test_executive_view_without_the_installed_schema(repo: Path) -> None:
    shutil.rmtree(repo / "frontend" / "node_modules")
    r = guard(repo, "check_sdd.py")
    assert r.returncode == 1 and "npm ci" in r.stdout, r.stdout


def test_executive_view_a_missing_or_blank_illustration(repo: Path) -> None:
    data = _load(repo)
    for name, ill in data["illustrations"].items():
        copy = repo / PUBLIC / ill["file"]
        keep = copy.read_bytes()
        copy.unlink()
        r = guard(repo, "check_sdd.py")
        assert r.returncode == 1 and f"illustrations.{name}.file" in r.stdout, r.stdout
        copy.write_bytes(b"<svg xmlns='http://www.w3.org/2000/svg'><title>x</title></svg>")
        r = guard(repo, "check_sdd.py")
        assert r.returncode == 1 and f"illustrations.{name}.file" in r.stdout and "viewBox" in r.stdout, r.stdout
        copy.write_bytes(keep)


def test_executive_view_a_figure_without_its_source_link(repo: Path) -> None:
    data = _load(repo)
    gone = data["headline_figures"][0]["source"]
    data["sources"] = [s for s in data["sources"] if s["id"] != gone]
    _save(repo, data)
    r = guard(repo, "check_sdd.py")
    assert r.returncode == 1 and "headline_figures[0].source" in r.stdout and "not the id of any source" in r.stdout, r.stdout
    data = _load(repo)
    data["sources"].append({"id": "orphan", "title": {"en": "A report nobody cites", "es": "Un informe que nadie cita"}, "url": "https://example.org/r"})
    _save(repo, data)
    r = guard(repo, "check_sdd.py")
    assert r.returncode == 1 and "orphan" in r.stdout and "cited by no" in r.stdout, r.stdout
    data = _load(repo)
    data["sources"][0]["url"] = "http://example.org/insecure"
    _save(repo, data)
    r = guard(repo, "check_sdd.py")
    assert r.returncode == 1 and "sources[0].url" in r.stdout, r.stdout


def test_executive_view_a_pitch_a_client_or_an_unowned_action(repo: Path) -> None:
    data = _load(repo)
    data["proposal"]["actions"][0]["action"]["en"] = "Buy the product now."
    data["proposal"]["actions"][1]["owner"] = {"en": "A role nobody has", "es": "Un rol que nadie tiene"}
    _save(repo, data)
    r = guard(repo, "check_sdd.py")
    assert r.returncode == 1 and "proposal.actions[0].action.en" in r.stdout and "proposal.actions[1].owner" in r.stdout, r.stdout


# ---------------------------------------------------------------- check_contract_versions

# ---------------------------------------------------------------- check_tech_matrix

def test_tech_matrix_a_pin_changed_in_requirements_but_not_in_the_sdd(repo: Path) -> None:
    edit(repo, "data-pipeline/requirements.txt", "numpy==2.4.6", "numpy==2.4.7")
    r = guard(repo, "check_tech_matrix.py")
    assert r.returncode == 1 and "numpy" in r.stdout and "2.4.7" in r.stdout and "2.4.6" in r.stdout, r.stdout


def test_tech_matrix_a_package_json_range_that_the_lock_does_not_resolve(repo: Path) -> None:
    edit(repo, "frontend/package-lock.json", '"node_modules/zustand"', '"node_modules/zustand-gone"')
    r = guard(repo, "check_tech_matrix.py")
    assert r.returncode == 1 and "zustand" in r.stdout and "unpinned" in r.stdout, r.stdout


# ---------------------------------------------------------------- check_contracts, check_readiness, check_skeleton

def test_readiness_a_catalog_edited_without_recomputing_the_document(repo: Path) -> None:
    edit(repo, CATALOG, "Phase 2 of contract-first parallel delivery", "Phase 2 of the contract-first parallel delivery")
    r = guard(repo, "check_readiness.py")
    assert r.returncode == 1 and "readiness: stale" in r.stdout and "python data-pipeline/run.py readiness" in r.stdout, r.stdout

