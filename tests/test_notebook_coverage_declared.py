"""The ladder methods a topic declares it teaches (``notebooks/methods-taught/<topic>.json``) count in the notebook coverage
map only when the id is a ladder row and the notebook exists in both trees at level 2 or higher
(``scripts/build_notebook_coverage.py``, ``methods_taught``)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _builder():
    spec = importlib.util.spec_from_file_location("build_notebook_coverage", ROOT / "scripts" / "build_notebook_coverage.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


NBS = {
    "14-topic/02-level-two.ipynb": {"caos": {"level": 2}, "code": ""},
    "14-topic/01-level-one.ipynb": {"caos": {"level": 1}, "code": ""},
}
LADDER = ["M-1", "M-28"]


def _run(tmp_path, monkeypatch, doc):
    builder = _builder()
    folder = tmp_path / "methods-taught"
    folder.mkdir()
    (folder / "14-topic.json").write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setattr(builder, "TAUGHT", folder)
    return builder.methods_taught(NBS, LADDER)


def test_a_level_two_declaration_counts(tmp_path, monkeypatch):
    taught, problems = _run(tmp_path, monkeypatch, {"M-28": ["14-topic/02-level-two.ipynb"]})
    assert taught == {"M-28": ["14-topic/02-level-two.ipynb"]}
    assert problems == []


def test_a_level_one_notebook_does_not_count(tmp_path, monkeypatch):
    taught, problems = _run(tmp_path, monkeypatch, {"M-28": ["14-topic/01-level-one.ipynb"]})
    assert taught == {}
    assert any("level 1" in p for p in problems)


def test_an_id_outside_the_ladder_is_refused(tmp_path, monkeypatch):
    taught, problems = _run(tmp_path, monkeypatch, {"M-99": ["14-topic/02-level-two.ipynb"]})
    assert taught == {}
    assert any("not a row" in p for p in problems)


def test_a_missing_or_foreign_notebook_is_refused(tmp_path, monkeypatch):
    taught, problems = _run(tmp_path, monkeypatch, {"M-1": ["14-topic/09-absent.ipynb", "13-other/02-x.ipynb"]})
    assert taught == {}
    assert any("not in both trees" in p for p in problems)
    assert any("outside the topic" in p for p in problems)
