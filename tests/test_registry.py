"""The case registry: 22 cases discovered or declared, built cases override planned ones, a duplicate id fails with
both paths, the regenerated index validates against ``common/case-index``, and export refuses an invalid document."""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "contracts"))

from contract_schemas import errors  # noqa: E402
from pipeline import cases as cases_pkg  # noqa: E402
from pipeline import registry  # noqa: E402
from pipeline.stages import export  # noqa: E402

BUILT = ["C01", "C04", "C05", "C06", "C07", "C22"]
ALL = [f"C{n:02d}" for n in range(1, 23)]
PLANNED = [c for c in ALL if c not in BUILT]
UNITS = {"C03": "U6", "C08": "U6", "C09": "U6", "C10": "U7", "C11": "U8", "C13": "U8",
         "C12": "U9", "C14": "U10", "C15": "U10", "C16": "U11", "C17": "U12", "C18": "U13", "C19": "U13",
         "C02": "U14", "C20": "U14", "C21": "U14"}


def test_the_built_cases_are_discovered_in_id_order():
    assert [c.id for c in cases_pkg.CASES] == BUILT
    assert all(callable(getattr(c, "bake", None)) for c in cases_pkg.CASES)


def test_all_22_cases_are_listed_built_or_declared_planned():
    assert [c.id for c in registry.list_cases()] == ALL
    assert [c.id for c in registry.built_cases()] == BUILT
    assert [c.id for c in registry.planned_cases()] == PLANNED
    for c in registry.planned_cases():
        assert registry.get_case(c.id) == c
        assert not hasattr(c, "bake"), "a planned case has nothing to bake"


def test_planned_entries_are_complete_and_bilingual():
    raw = json.loads(registry.PLANNED_PATH.read_text(encoding="utf-8"))
    assert [e["case_id"] for e in raw] == sorted(PLANNED)
    for e in raw:
        assert set(e) == {"case_id", "title", "category_id", "kind", "unit", "question"}, e["case_id"]
        assert e["unit"] == UNITS[e["case_id"]], e["case_id"]
        assert e["kind"] in ("real", "synthetic")
        assert e["category_id"] in registry.CATEGORIES
        for key in ("title", "question"):
            assert set(e[key]) == {"en", "es"} and all(e[key].values()), (e["case_id"], key)
        assert e["question"]["en"].endswith("?") and e["question"]["es"].startswith("¿")


def test_a_built_case_overrides_its_planned_entry(tmp_path, monkeypatch):
    planned = [{"case_id": "C01", "title": {"en": "x", "es": "x"}, "category_id": "credit-scoring", "kind": "real",
                "unit": "U1", "question": {"en": "q?", "es": "¿q?"}}]
    path = tmp_path / "planned_cases.json"
    path.write_text(json.dumps(planned), encoding="utf-8")
    monkeypatch.setattr(registry, "PLANNED_PATH", path)
    assert [c.id for c in registry.planned_cases()] == []  # C01 is built, the stale entry is ignored
    assert registry.stale_planned_ids() == ["C01"]
    assert registry.get_case("C01").title["en"] != "x"


def test_a_stale_planned_entry_is_a_warning_not_an_error():
    # nothing in the committed file is stale today; the registry reports the ids instead of raising
    assert registry.stale_planned_ids() == []


def _package(tmp_path: Path, name: str, files: dict[str, str]) -> None:
    pkg = tmp_path / name
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    for fname, body in files.items():
        target = pkg / fname
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(textwrap.dedent(body), encoding="utf-8")
    sys.path.insert(0, str(tmp_path))


CASE_BODY = """
    class _C:
        id = "{id}"
        def bake(self, **kw): return {{}}
    CASE = _C()
"""


def test_discovery_takes_modules_and_packages_in_id_order(tmp_path, monkeypatch):
    _package(tmp_path, "fakecases_ok", {
        "c31_beta.py": CASE_BODY.format(id="C31"),
        "c30/__init__.py": CASE_BODY.format(id="C30"),
        "c31_helper.py": "X = 1\n",            # a helper without CASE is not a case
        "other.py": CASE_BODY.format(id="C99"),  # a name that is not c<NN> is never read
    })
    monkeypatch.syspath_prepend(str(tmp_path))
    found = cases_pkg.discover(tmp_path / "fakecases_ok", "fakecases_ok")
    assert [c.id for c in found] == ["C30", "C31"]


def test_two_modules_with_the_same_id_fail_with_both_paths(tmp_path, monkeypatch):
    _package(tmp_path, "fakecases_dup", {"c40_a.py": CASE_BODY.format(id="C40"),
                                         "c40_b.py": CASE_BODY.format(id="C40")})
    monkeypatch.syspath_prepend(str(tmp_path))
    with pytest.raises(ValueError) as exc:
        cases_pkg.discover(tmp_path / "fakecases_dup", "fakecases_dup")
    msg = str(exc.value)
    assert "C40" in msg and "c40_a.py" in msg and "c40_b.py" in msg


def test_a_case_whose_id_disagrees_with_its_module_name_fails(tmp_path, monkeypatch):
    _package(tmp_path, "fakecases_name", {"c50_x.py": CASE_BODY.format(id="C51")})
    monkeypatch.syspath_prepend(str(tmp_path))
    with pytest.raises(ValueError, match="c50_x"):
        cases_pkg.discover(tmp_path / "fakecases_name", "fakecases_name")


def test_the_index_lists_22_cases_and_validates_against_the_schema():
    entries = registry.index_entries()
    assert [e["case_id"] for e in entries] == ALL
    assert all(e["manifest_path"] == f"manifests/{e['case_id']}.json" for e in entries)
    from pipeline.core.manifest import build_index

    doc = build_index(entries, registry.default_case(), ["contract/index.json"])
    assert errors("common/case-index", doc) == []
    assert doc["n_cases"] == 22


def test_the_committed_index_is_current_and_valid():
    committed = json.loads((ROOT / "data" / "derived" / "manifests" / "index.json").read_text(encoding="utf-8"))
    assert errors("common/case-index", committed) == []
    assert [e["case_id"] for e in committed["cases"]] == ALL
    from pipeline import pipeline

    fresh = pipeline.index_document()
    assert fresh == committed


def test_planned_cases_have_no_bake():
    from pipeline import pipeline

    with pytest.raises(registry.PlannedCaseError, match="C02"):
        pipeline.precompute("C02")


def test_export_refuses_an_invalid_document_and_writes_nothing(tmp_path):
    bad = {"schema": "contraste.case/v1", "case_id": "C01", "variant_id": "holdout"}  # nearly everything missing
    with pytest.raises(ValueError) as exc:
        export.write_artifact(tmp_path, "C01/holdout.json", bad, engines=set(), run_ms=1.0)
    assert "C01/holdout.json" in str(exc.value)
    assert not (tmp_path / "C01" / "holdout.json").exists()


def test_export_accepts_a_committed_document(tmp_path):
    doc = json.loads((ROOT / "data" / "derived" / "C22" / "null.json").read_text(encoding="utf-8"))
    entry = export.write_artifact(tmp_path, "C22/null.json", doc, engines=set(), run_ms=1.0)
    assert (tmp_path / "C22" / "null.json").is_file() and entry["path"] == "C22/null.json"
