"""Schema access for the contract tests (docs/contracts/catalog.md): every schema file under
docs/contracts/schemas/**, validated with jsonschema (Draft 2020-12) through one referencing registry, so a
``$ref`` from one schema file to another resolves to that same file, and the discovery rules that pick the schema
of a document. The schema files are the single source of every contract; no test re-declares a shape.

Adapted from CAOS_PRODUCT_TEMPLATE v0.04.000 tests/contracts/contract_schemas.py (a registry over the schema files,
``errors``), extended for a product whose schemas live in one folder per case.

Discovery (no list of files or cases anywhere; wave-2 cases add a folder and nothing else):

* a candidate is every ``*.schema.json`` under ``schemas/`` except the abstract bases (``*-envelope``) and the
  registries of sub-documents that no file of its own carries (``schemas/common`` files with no selector);
* a candidate declares selectors, read from its own root ``properties`` and through ``allOf`` / ``$ref``:
  ``schema`` (the document's ``schema`` string), ``case_id``, ``fit_id``, ``outputs.kind`` (each a ``const``),
  and optionally ``x-location`` (a glob of the repository-relative path of the file);
* a candidate matches a document when every selector it declares equals the document's value; a candidate with
  no ``outputs.kind`` const matches only a document whose ``outputs`` carry no ``kind`` (the default, and exactly
  one candidate may be the default);
* among the matches the most specific wins (one point per const matched, one more for an ``x-location``);
  zero matches or a tie is a :class:`SelectionError` naming the path.
"""
from __future__ import annotations

import fnmatch
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "docs" / "contracts"
SCHEMAS = CONTRACTS / "schemas"
DERIVED = ROOT / "data" / "derived"
BASE = "https://contraste.fasl-work.com/contracts/"
DIALECT = "https://json-schema.org/draft/2020-12/schema"


class SelectionError(Exception):
    """A document matched no schema, or two with the same specificity."""


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def schema_files() -> list[Path]:
    return sorted(SCHEMAS.rglob("*.schema.json"))


def schema_id(path: Path) -> str:
    return BASE + path.relative_to(SCHEMAS).as_posix()


@lru_cache(maxsize=None)
def registry() -> Registry:
    """Every schema file at its ``$id`` (which must equal BASE + its path under docs/contracts/schemas)."""
    resources = []
    for f in schema_files():
        doc = load_json(f)
        assert doc.get("$id") == schema_id(f), f"{f}: $id is {doc.get('$id')!r}, expected {schema_id(f)!r}"
        assert doc.get("$schema") == DIALECT, f"{f}: $schema is {doc.get('$schema')!r}"
        resources.append((doc["$id"], Resource.from_contents(doc, default_specification=DRAFT202012)))
    return Registry().with_resources(resources)


@lru_cache(maxsize=None)
def validator(ref: str) -> Draft202012Validator:
    """The validator of a schema file, given its path under docs/contracts/schemas (``common/case-index``) or its
    ``$id``. The schema itself is checked against the metaschema first."""
    sid = ref if ref.startswith(BASE) else f"{BASE}{ref}.schema.json"
    path = SCHEMAS / sid[len(BASE):]
    Draft202012Validator.check_schema(load_json(path))
    return Draft202012Validator({"$schema": DIALECT, "$ref": sid}, registry=registry())


def errors(ref: str, instance: Any) -> list[str]:
    """Every way ``instance`` departs from the schema ``ref``, as ``path: message``; empty when it conforms."""
    v = validator(ref)
    found = sorted(v.iter_errors(instance), key=lambda e: [str(p) for p in e.absolute_path])
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '$'}: {e.message}" for e in found[:25]]


# --- discovery --------------------------------------------------------------------------------------------------


def _consts(doc: Any, base: Path, seen: frozenset[Path] = frozenset()) -> dict[str, Any]:
    """The selectors a schema declares at its root: ``const`` values of ``schema``, ``case_id``, ``fit_id`` and
    ``outputs.kind``, looked up in ``properties``, in every ``allOf`` member and through relative ``$ref`` files."""
    out: dict[str, Any] = {}
    if not isinstance(doc, dict):
        return out
    props = doc.get("properties", {})
    for key in ("schema", "case_id", "fit_id"):
        if isinstance(props.get(key), dict) and "const" in props[key]:
            out[key] = props[key]["const"]
    kind = props.get("outputs", {}).get("properties", {}).get("kind", {}) if isinstance(props.get("outputs"), dict) else {}
    if isinstance(kind, dict) and "const" in kind:
        out["outputs.kind"] = kind["const"]
    for member in doc.get("allOf", []):
        if isinstance(member, dict) and "$ref" in member and not member["$ref"].startswith("#"):
            target = (base.parent / member["$ref"].split("#")[0]).resolve()
            if target not in seen and target.is_file():
                out.update(_consts(load_json(target), target, seen | {target}))
        else:
            out.update(_consts(member, base, seen))
    return out


class Candidate:
    def __init__(self, path: Path) -> None:
        doc = load_json(path)
        self.path = path
        self.ref = path.relative_to(SCHEMAS).as_posix().removesuffix(".schema.json")
        self.consts = _consts(doc, path, frozenset({path.resolve()}))
        self.location: str | None = doc.get("x-location")
        self.abstract = path.name.endswith("-envelope.schema.json")

    @property
    def selectable(self) -> bool:
        return not self.abstract and bool(self.consts.get("schema") or self.location)

    def score(self, relpath: str, doc: Any) -> int | None:
        """None when the candidate does not match the document, else its specificity."""
        points = 0
        if self.location is not None:
            if not fnmatch.fnmatchcase(relpath, self.location):
                return None
            points += 1 + (0 if any(ch in self.location for ch in "*?[") else 1)
        d = doc if isinstance(doc, dict) else {}
        for key in ("schema", "case_id", "fit_id"):
            if key in self.consts:
                if d.get(key) != self.consts[key]:
                    return None
                points += 1
        outputs = d.get("outputs")
        doc_kind = outputs.get("kind") if isinstance(outputs, dict) else None
        if "outputs.kind" in self.consts:
            if doc_kind != self.consts["outputs.kind"]:
                return None
            points += 1
        elif self.consts.get("schema") == "contraste.case/v1" and doc_kind is not None:
            return None  # the default variant schema takes only documents whose outputs carry no kind
        return points


@lru_cache(maxsize=None)
def candidates() -> tuple[Candidate, ...]:
    return tuple(c for c in (Candidate(p) for p in schema_files()) if c.selectable)


def default_variants() -> list[str]:
    """The variant schemas that omit the ``outputs.kind`` const (exactly one may)."""
    return [c.ref for c in candidates() if c.consts.get("schema") == "contraste.case/v1" and "outputs.kind" not in c.consts]


def schema_for_document(path: Path, doc: Any) -> str:
    """The schema ref (``common/case-index``) of the document at ``path`` (any path under the repository)."""
    defaults = default_variants()
    if len(defaults) > 1:
        raise SelectionError(f"more than one variant schema omits the outputs.kind const: {defaults}")
    relpath = path.resolve().relative_to(ROOT).as_posix()
    scored = [(c.score(relpath, doc), c.ref) for c in candidates()]
    scored = [(s, ref) for s, ref in scored if s is not None]
    if not scored:
        raise SelectionError(f"{relpath}: matches no schema")
    best = max(s for s, _ in scored)
    top = sorted(ref for s, ref in scored if s == best)
    if len(top) > 1:
        raise SelectionError(f"{relpath}: matches {len(top)} schemas equally: {top}")
    return top[0]


def committed_documents() -> list[Path]:
    """Every document the contracts cover: all of data/derived plus the three registries."""
    docs = sorted(p for p in DERIVED.rglob("*.json"))
    docs += [ROOT / "data-pipeline" / "config" / "sources.json", ROOT / "data-pipeline" / "config" / "licences.json",
             ROOT / "data" / "sources" / "manifest.json"]
    return docs
