"""Contraste's own guards fail on what they exist to catch: the data classes, the provenance of every artifact and the
licences of the default install (CT-003, CT-005, CT-006). Each test plants a violation in a throwaway tree and runs the
real script against it. The template's base guards are tested in tests/test_guards.py, a verbatim copy of the base
(ADR-0078), so a base release is adopted by copying the file."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def _run(script: str, root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / script), str(root)], capture_output=True, text=True)


def _tree(tmp: Path) -> Path:
    tree = tmp / "tree"
    (tree / "data-pipeline" / "config").mkdir(parents=True)
    shutil.copy(ROOT / "data-pipeline" / "config" / "sources.json", tree / "data-pipeline" / "config" / "sources.json")
    for i in range(10):
        (tree / f"file{i}.txt").write_text(f"filler {i}\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tree, check=True)
    return tree


def _manifest(tree: Path, sources: dict) -> None:
    p = tree / "data" / "sources" / "manifest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"schema": "contraste.licence-manifest/v1", "sources": sources}), encoding="utf-8")


def test_data_classes_catches_raw_rows_and_copies(tmp_path):
    tree = _tree(tmp_path)
    secret = b"loan_id|upb|ltv\n1|200000|80\n"
    _manifest(tree, {"freddie-mac-sflld": {"class": "derived-only", "files": [
        {"name": "sample_orig_2008.txt", "sha256": hashlib.sha256(secret).hexdigest(), "bytes": len(secret)}]}})
    assert _run("check_data_classes.py", tree).returncode == 0
    (tree / "data" / "raw" / "freddie-mac-sflld").mkdir(parents=True)
    (tree / "data" / "raw" / "freddie-mac-sflld" / "rows.txt").write_text("1|2|3\n", encoding="utf-8")
    (tree / "docs").mkdir()
    (tree / "docs" / "renamed-copy.bin").write_bytes(secret)
    res = _run("check_data_classes.py", tree)
    assert res.returncode == 1
    assert "raw rows of freddie-mac-sflld, which is derived-only" in res.stdout
    assert "docs/renamed-copy.bin: carries the bytes of freddie-mac-sflld/sample_orig_2008.txt" in res.stdout


def test_data_classes_catches_a_manifest_that_disagrees_with_the_registry(tmp_path):
    tree = _tree(tmp_path)
    _manifest(tree, {"uci-taiwan": {"class": "derived-only", "files": []}, "made-up": {"class": "mirror-allowed"}})
    res = _run("check_data_classes.py", tree)
    assert res.returncode == 1
    assert "uci-taiwan is recorded derived-only, the registry says mirror-allowed" in res.stdout
    assert "made-up is not in the source registry" in res.stdout


def _write(p: Path, doc: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc), encoding="utf-8")


def _provenance_tree(tmp: Path, *, inputs: list[dict], truth: str = "real-outcomes", sources: list[str]) -> Path:
    tree = _tree(tmp)
    _manifest(tree, {"uci-taiwan": {"class": "mirror-allowed", "files": [{"name": "t.zip", "sha256": "a" * 64}]}})
    d = tree / "data" / "derived"
    _write(d / "manifests" / "index.json", {"cases": [{"case_id": "C01", "manifest_path": "manifests/C01.json"}]})
    _write(d / "manifests" / "C01.json", {"case_id": "C01", "sources": sources, "artifacts": [
        {"variant_id": "holdout", "path": "C01/holdout.json", "truth_status": "real-outcomes"}]})
    _write(d / "C01" / "holdout.json", {"provenance": {
        "truth_status": truth, "inputs": inputs, "generators": [],
        "licence_classes": {i["source"]: i["class"] for i in inputs}}})
    return tree


def test_provenance_passes_when_true_and_fails_when_not(tmp_path):
    good = [{"source": "uci-taiwan", "class": "mirror-allowed", "files": [{"name": "t.zip", "sha256": "a" * 64}]}]
    ok = _provenance_tree(tmp_path / "ok", inputs=good, sources=["uci-taiwan"])
    assert _run("check_provenance.py", ok).returncode == 0, _run("check_provenance.py", ok).stdout
    bad_inputs = [
        {"source": "uci-taiwan", "class": "mirror-allowed", "files": [{"name": "t.zip", "sha256": "b" * 64}]},
        {"source": "fannie-mae-sflp", "class": "link-only", "files": [{"name": "f.zip", "sha256": "c" * 64}]},
    ]
    bad = _provenance_tree(tmp_path / "bad", inputs=bad_inputs, truth="real", sources=["uci-taiwan"])
    res = _run("check_provenance.py", bad)
    assert res.returncode == 1
    assert "truth status 'real'" in res.stdout
    assert "uci-taiwan/t.zip hash is not the one the licence manifest pins" in res.stdout
    assert "fannie-mae-sflp is link-only; the artifact may not be published" in res.stdout
    assert "the manifest names sources ['uci-taiwan'], the artifacts read ['fannie-mae-sflp', 'uci-taiwan']" in res.stdout


def test_licence_guard_catches_a_forbidden_or_unverified_requirement(tmp_path, monkeypatch):
    sys.path.insert(0, str(SCRIPTS))
    import check_licences as cl

    assert cl.FORBIDDEN.search("GPL-3.0-or-later") and cl.FORBIDDEN.search("AGPL-3.0")
    assert cl.FORBIDDEN.search("Business Source License 1.1") and cl.FORBIDDEN.search("BUSL-1.1")
    assert not cl.FORBIDDEN.search("LGPL-2.1") and not cl.FORBIDDEN.search("BSL-1.0")  # Boost is permissive
    req = tmp_path / "requirements-precompute.txt"
    req.write_text("numpy==2.4.6\nsdv==1.0  # tabular synthesis\n", encoding="utf-8")
    table = tmp_path / "licences.json"
    table.write_text(json.dumps({"python": {"numpy": {"licence": "BSD-3-Clause"},
                                            "sdv": {"licence": "Business Source License 1.1"}}}), encoding="utf-8")
    lock = tmp_path / "package-lock.json"
    lock.write_text(json.dumps({"packages": {"": {}, "node_modules/a": {"license": "MIT"},
                                             "node_modules/b": {"license": "GPL-2.0"}, "node_modules/c": {}}}),
                    encoding="utf-8")
    monkeypatch.setattr(cl, "ROOT", tmp_path)
    monkeypatch.setattr(cl, "TABLE", table)
    monkeypatch.setattr(cl, "LOCK", lock)
    monkeypatch.setattr(cl, "ROOTS", ("requirements-precompute.txt",))
    findings, n_py, n_js = cl.static_findings()
    text = "\n".join(findings)
    assert n_py == 2 and n_js == 3
    assert "sdv is licensed Business Source License 1.1" in text
    assert "node_modules/b is licensed GPL-2.0" in text and "node_modules/c declares no licence" in text
    table.write_text(json.dumps({"python": {"numpy": {"licence": "BSD-3-Clause"}}}), encoding="utf-8")
    assert any("sdv has no verified licence" in f for f in cl.static_findings()[0])


# --- the base guards (from the template release in .template-version), run on this product's copies ---
