"""scripts/compare_rebake.py passes a re-bake that only moved its version stamps and fails any other change (a number, a
document added or lost, a list that grew), on a throwaway git tree."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compare_rebake.py"
DOC = {"provenance": {"code_version": "0.10.001", "riskvalidation_version": "0.6.0", "seed": 42},
       "model": [{"engine_version": "0.6.0", "name": "rung"}], "outputs": {"var": [1.5, 2.25], "n": 3}}


def _repo(tmp: Path) -> Path:
    r = tmp / "repo"
    (r / "data" / "derived" / "C99").mkdir(parents=True)
    (r / "data" / "derived" / "C99" / "v.json").write_text(json.dumps(DOC), encoding="utf-8")
    for cmd in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "c"]):
        subprocess.run(["git", "-C", str(r), *cmd], check=True)
    return r


def _run(r: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), "C99", "--root", str(r)], capture_output=True, text=True)


def _write(r: Path, doc: dict, name: str = "v.json") -> None:
    (r / "data" / "derived" / "C99" / name).write_text(json.dumps(doc), encoding="utf-8")


def test_only_the_stamps_moved_passes(tmp_path):
    r = _repo(tmp_path)
    doc = json.loads(json.dumps(DOC))
    doc["provenance"].update(code_version="0.11.000", riskvalidation_version="0.7.0")
    doc["model"][0]["engine_version"] = "0.7.0"
    _write(r, doc)
    res = _run(r)
    assert res.returncode == 0, res.stdout


def test_a_changed_number_a_new_document_or_a_longer_list_fails(tmp_path):
    r = _repo(tmp_path)
    doc = json.loads(json.dumps(DOC))
    doc["outputs"]["var"][1] = 2.5
    doc["outputs"]["n"] = 4
    doc["provenance"]["seed"] = 7
    _write(r, doc)
    _write(r, DOC, "extra.json")
    res = _run(r)
    assert res.returncode == 1
    assert "outputs/var/1: 2.25 committed, 2.5 re-baked" in res.stdout
    assert "outputs/n: 3 committed, 4 re-baked" in res.stdout
    assert "provenance/seed: 42 committed, 7 re-baked" in res.stdout
    assert "data/derived/C99/extra.json: new, not committed" in res.stdout
    doc = json.loads(json.dumps(DOC))
    doc["outputs"]["var"].append(3.0)
    _write(r, doc)
    (r / "data" / "derived" / "C99" / "extra.json").unlink()
    res = _run(r)
    assert "outputs/var has 2 items committed and 3 re-baked" in res.stdout


def test_a_lost_document_fails(tmp_path):
    r = _repo(tmp_path)
    (r / "data" / "derived" / "C99" / "v.json").unlink()
    res = _run(r)
    assert res.returncode == 1 and "data/derived/C99/v.json: committed, not re-baked" in res.stdout
