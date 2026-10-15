"""scripts/compare_rebake.py passes a re-bake that only moved its version stamps and fails any other change (a number, a
document added or lost, a list that grew), on a throwaway git tree."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compare_rebake.py"
DOC = {"provenance": {"code_version": "stamp-before", "riskvalidation_version": "0.6.0", "seed": 42},
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
    doc["provenance"].update(code_version="stamp-after", riskvalidation_version="0.7.0")
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


def test_the_documents_own_size_may_move_by_the_stamps_byte_change_and_by_nothing_else(tmp_path):
    """The lane gate records the document's size (`trace_bytes`); a shorter engine stamp shrinks it by exactly the bytes it lost."""
    doc = json.loads(json.dumps(DOC))
    doc["provenance"]["riskvalidation_version"] = "0.6.0@344ec9a"
    doc["model"][0]["engine_version"] = "0.6.0@344ec9a"
    doc["lane"] = {"reasons": ["pure python", "trace_bytes 1000 > 262144"], "trace_bytes": 1000}
    r = tmp_path / "repo"
    (r / "data" / "derived" / "C99").mkdir(parents=True)
    (r / "data" / "derived" / "C99" / "v.json").write_text(json.dumps(doc), encoding="utf-8")
    for cmd in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "c"]):
        subprocess.run(["git", "-C", str(r), *cmd], check=True)
    rebaked = json.loads(json.dumps(doc))
    rebaked["provenance"]["riskvalidation_version"] = "0.7.0"          # 8 bytes shorter
    rebaked["model"][0]["engine_version"] = "0.7.0"                     # 8 bytes shorter
    rebaked["lane"] = {"reasons": ["pure python", "trace_bytes 984 > 262144"], "trace_bytes": 984}
    _write(r, rebaked)
    assert _run(r).returncode == 0, _run(r).stdout
    rebaked["lane"] = {"reasons": ["pure python", "trace_bytes 990 > 262144"], "trace_bytes": 990}
    _write(r, rebaked)
    res = _run(r)
    assert res.returncode == 1
    assert "lane/reasons/1: 'trace_bytes 1000 > 262144' committed, 'trace_bytes 990 > 262144' re-baked" in res.stdout
    assert "lane/trace_bytes: 1000 committed, 990 re-baked" in res.stdout
