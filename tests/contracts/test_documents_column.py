"""The catalog's ``documents`` column against the product's own schema discovery (U16-W2).

``scripts/check_documents.py`` (verbatim from the template) validates a document against the schema file of the row that governs
it, named by file name only; the product's tests select a schema by what the document declares (``schema``, ``case_id``,
``outputs.kind``). The two must agree: a row's globs may not hand a document to a schema the discovery would not choose. The
bare-name resolution of ``contract_schemas.resolve_name`` and ``component_errors`` are tested here too."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import check_documents as cd  # noqa: E402
import contract_schemas as cs  # noqa: E402
from check_contracts import parse_catalog, split_documents  # noqa: E402

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def governed() -> dict[Path, str]:
    """Every file a catalog row's documents cell governs, with the schema ref the guard validates it against."""
    _, rows = parse_catalog((ROOT / cd.CATALOG_REL).read_text(encoding="utf-8"))
    out: dict[Path, str] = {}
    for row in rows:
        for path in cd.row_files(ROOT, split_documents(row.get("documents", ""))):
            doc = json.loads(path.read_text(encoding="utf-8"))
            out[path] = cs.resolve_name(cd.schema_name(row["schema file"]), doc)
    return out


def test_every_governed_document_gets_the_schema_the_discovery_selects() -> None:
    mine = governed()
    assert len(mine) > 200, "the documents column governs the baked documents"
    wrong = [f"{p.relative_to(ROOT).as_posix()}: the row gives {ref}, the discovery {cs.schema_for_document(p, json.loads(p.read_text(encoding='utf-8')))}"
             for p, ref in mine.items()
             if p.is_relative_to(ROOT / "data" / "derived") and ref != cs.schema_for_document(p, json.loads(p.read_text(encoding="utf-8")))]
    assert not wrong, wrong[:10]


def test_every_baked_document_is_governed_by_exactly_one_row() -> None:
    _, rows = parse_catalog((ROOT / cd.CATALOG_REL).read_text(encoding="utf-8"))
    claims: dict[Path, list[str]] = {}
    for row in rows:
        for path in cd.row_files(ROOT, split_documents(row.get("documents", ""))):
            claims.setdefault(path, []).append(row["id"])
    assert {p: r for p, r in claims.items() if len(r) > 1} == {}
    holes = [p.relative_to(ROOT).as_posix() for p in cd.hole_files(ROOT) if p not in claims]
    assert holes == []


def test_a_bare_name_shared_by_several_case_folders_resolves_through_the_case_id() -> None:
    assert cs.resolve_name("models", {"case_id": "C06"}) == "c06/models"
    assert cs.resolve_name("variant", {"case_id": "C22"}) == "c22/variant"
    assert cs.resolve_name("case-index", {}) == "common/case-index"
    assert cs.resolve_name("common/case-index", {}) == "common/case-index"


def test_a_bare_name_that_stays_ambiguous_or_unknown_is_refused() -> None:
    with pytest.raises(cs.SelectionError):
        cs.resolve_name("models", {"case_id": "C99"})
    with pytest.raises(cs.SelectionError):
        cs.resolve_name("no-such-schema", {})


def test_a_document_of_another_case_fails_the_schema_of_its_row() -> None:
    doc = json.loads((ROOT / "data/derived/C06/models-rd-2008-12.json").read_text(encoding="utf-8"))
    assert cs.errors("models", doc) == []
    doc["case_id"] = "C08"
    assert cs.errors("models", doc), "a C08 models document is held to the C08 schema, so a C06 body departs from it"


def test_component_errors_validates_against_an_openapi_component() -> None:
    api = json.loads((ROOT / "docs/contracts/api.openapi.json").read_text(encoding="utf-8"))
    name = next(n for n, c in api["components"]["schemas"].items() if c.get("type") == "object" and c.get("required"))
    assert cs.component_errors(name, {}), "an empty object departs from a component that requires properties"
    with pytest.raises(AssertionError):
        cs.component_errors("NoSuchComponent", {})
