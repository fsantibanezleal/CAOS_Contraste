"""The base guards fail on what they exist to catch, and pass on what they must allow (ADR-0078: the base validates
itself). Each test builds a throwaway tree, plants the case, and runs the real script on it."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
# instantiate.py runs only in the template, whose sentinel it deletes: in a product the test has nothing to run on
TEMPLATE_ONLY = pytest.mark.skipif(not (ROOT / ".template-source").exists(),
                                   reason="instantiate runs only in the template repository (.template-source)")


def _run(script: str, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True, cwd=cwd)


def _put(root: Path, rel: str, doc) -> int:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    data = doc if isinstance(doc, str) else json.dumps(doc)
    p.write_bytes(data.encode("utf-8"))
    return p.stat().st_size


def _git_tree(tmp: Path) -> Path:
    tree = tmp / "tree"
    tree.mkdir()
    for i in range(10):
        _put(tree, f"filler{i}.txt", f"filler {i}\n")
    subprocess.run(["git", "init", "-q"], cwd=tree, check=True)
    return tree


def test_check_artifacts_reads_one_or_many_artifacts_and_the_index_files(tmp_path):
    d = tmp_path / "data" / "derived"
    n_single = _put(d, "A/trace.json", {"t": [0, 1]})
    n_v1 = _put(d, "B/v1.json", {"x": 1})
    n_v2 = _put(d, "B/v2.json", {"x": 22})
    _put(d, "contract/index.json", {"families": []})
    gate = {"lane": "live"}
    _put(d, "manifests/A.json", {"artifact": {"path": "A/trace.json", "bytes": n_single}, "lane": "live", "gate": gate})
    _put(d, "manifests/B.json", {"artifacts": [{"path": "B/v1.json", "bytes": n_v1, "lane": "live", "gate": gate},
                                               {"path": "B/v2.json", "bytes": n_v2, "lane": "live", "gate": gate}]})
    index = {"files": ["contract/index.json"], "cases": [{"case_id": "A", "manifest_path": "manifests/A.json"},
                                                         {"case_id": "B", "manifest_path": "manifests/B.json"}]}
    _put(d, "manifests/index.json", index)
    ok = _run("check_artifacts.py", str(tmp_path))
    assert ok.returncode == 0 and "2 cases, 3 artifacts" in ok.stdout, ok.stdout
    # drift in the second variant, a lane that disagrees with its gate, a declared file gone
    _put(d, "manifests/B.json", {"artifacts": [{"path": "B/v1.json", "bytes": n_v1, "lane": "live", "gate": gate},
                                               {"path": "B/v2.json", "bytes": n_v2 + 1, "lane": "precompute", "gate": gate}]})
    (d / "contract" / "index.json").unlink()
    bad = _run("check_artifacts.py", str(tmp_path))
    assert bad.returncode == 1
    assert "byte drift" in bad.stdout and "B/v2.json" in bad.stdout
    assert "lane/gate mismatch: B B/v2.json" in bad.stdout
    assert "declared by the index but missing or empty" in bad.stdout


REQ = """# Requirements: a unit not built yet

{status}

| ID | Requirement | Gate |
|---|---|---|
| UX-001 | THE unit SHALL do its job. | `tests/test_not_written_yet.py::test_its_job` |
"""


def test_doc_paths_skips_the_gates_of_planned_requirements_only(tmp_path):
    tree = _git_tree(tmp_path)
    _put(tree, "tests/test_exists.py", "def test_x():\n    pass\n")
    _put(tree, "docs/design/features/unit/requirements.md", REQ.format(status="Status: planned"))
    ok = _run("check_doc_paths.py", str(tree))
    assert ok.returncode == 0, ok.stdout
    _put(tree, "docs/design/features/unit/requirements.md", REQ.format(status="Status: live"))
    bad = _run("check_doc_paths.py", str(tree))
    assert bad.returncode == 1 and "names tests/test_not_written_yet.py" in bad.stdout
    # a planned file anywhere else is not exempt
    _put(tree, "docs/design/features/unit/requirements.md", REQ.format(status="Status: planned"))
    _put(tree, "docs/notes.md", "See `tests/test_missing.py`.\n\nStatus: planned\n")
    other = _run("check_doc_paths.py", str(tree))
    assert other.returncode == 1 and "docs/notes.md:1: names tests/test_missing.py" in other.stdout


def test_residue_marker_flags_the_placeholder_name_and_not_the_plugin_name():
    sys.path.insert(0, str(SCRIPTS))
    import check_template_residue as r

    marker = dict(r.MARKERS)["the placeholder product name"]
    assert marker.search('"name": "caos-product-frontend"')
    assert marker.search("npm run build in caos-product")
    assert marker.search('"name": "CAOS Product"')
    assert not marker.search("name: 'caos-product-html',")
    assert not marker.search('"name": "contraste-frontend"')


def test_residue_guard_scans_the_helper_scripts_and_skips_its_own_tests(tmp_path):
    tree = _git_tree(tmp_path)
    _put(tree, "scripts/precompute.ps1", "# E.g.:  ./scripts/precompute.ps1 EX02_epidemic --seed 7\n")
    _put(tree, "scripts/precompute.sh", "# the tiny teaching engine\n")
    # the guard's own tests must name the placeholder they look for
    _put(tree, "tests/test_guards.py", "assert marker.search('\"name\": \"caos-product-frontend\"')\n")
    res = _run("check_template_residue.py", str(tree))
    assert res.returncode == 1, res.stdout
    assert "scripts/precompute.ps1:1: an example case id" in res.stdout
    assert "scripts/precompute.sh:1: prose about the example engine" in res.stdout
    assert "tests/test_guards.py" not in res.stdout


@TEMPLATE_ONLY
def test_instantiate_renames_the_lockfile_and_drops_the_template_guide(tmp_path):
    copy = tmp_path / "product"
    ignore = shutil.ignore_patterns(".git", "node_modules", ".venv*", "dist", "public/data", "__pycache__",
                                    ".pytest_cache", ".ruff_cache", "gate-output")
    shutil.copytree(ROOT, copy, ignore=ignore)
    # the script resolves its root from its own location: run the COPY's script, never this repository's
    res = subprocess.run([sys.executable, str(copy / "scripts" / "instantiate.py"), "--slug", "probe", "--name", "Probe",
                          "--repo", "CAOS_Probe", "--deploy", "pages", "--visibility", "public", "--tagline-en",
                          "A probe.", "--tagline-es", "Una sonda.", "--no-run"], capture_output=True, text=True, cwd=copy)
    assert res.returncode == 0, res.stdout + res.stderr
    lock = json.loads((copy / "frontend" / "package-lock.json").read_text(encoding="utf-8"))
    assert lock["name"] == "probe-frontend" and lock["version"] == "0.1.0"
    assert lock["packages"][""]["name"] == "probe-frontend" and lock["packages"][""]["version"] == "0.1.0"
    assert "caos-product" not in (copy / "frontend" / "package-lock.json").read_text(encoding="utf-8")
    assert not (copy / "docs" / "guides" / "00_instantiate.md").exists()
    assert "00_instantiate" not in (copy / "docs" / "guides.md").read_text(encoding="utf-8")
    assert not (copy / ".template-source").exists()
