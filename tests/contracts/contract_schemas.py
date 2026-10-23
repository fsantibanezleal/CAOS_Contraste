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
  no ``outputs.kind`` const matches only a document whose ``outputs`` carry no ``kind`` (the default variant of its
  case: exactly one candidate per ``case_id`` may be the default, so a case never blocks another);
* every schema under ``schemas/<case>/`` declares a ``case_id`` const equal to its folder name upper-cased
  (:func:`case_folder_violations`), so none becomes a catch-all for its kind;
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


def resolve_name(ref: str, instance: Any) -> str:
    """The ref (path under schemas/ without the suffix) of a schema given as a bare file name, which is what
    ``scripts/check_documents.py`` (verbatim from the template) passes: ``case-index`` -> ``common/case-index``. A name that
    several case folders share (``models``, ``variant``, ``variant-scenario``, ``variant-reverse``) resolves to the one whose
    ``case_id`` const equals the document's ``case_id`` (every schema under ``schemas/<case>/`` declares it). A ref that
    already has a folder, or an ``$id``, is returned as it is."""
    if "/" in ref or ref.startswith(BASE):
        return ref
    named = [p for p in schema_files() if p.name == f"{ref}.schema.json"]
    if len(named) > 1 and isinstance(instance, dict):
        named = [p for p in named if Candidate(p).consts.get("case_id") == instance.get("case_id")] or named
    if len(named) != 1:
        raise SelectionError(f"schema name {ref!r} resolves to {len(named)} files: {[p.relative_to(SCHEMAS).as_posix() for p in named]}")
    return named[0].relative_to(SCHEMAS).as_posix().removesuffix(".schema.json")


def errors(ref: str, instance: Any) -> list[str]:
    """Every way ``instance`` departs from the schema ``ref`` (a ref, an ``$id`` or a bare file name, see
    :func:`resolve_name`), as ``path: message``; empty when it conforms."""
    v = validator(resolve_name(ref, instance))
    found = sorted(v.iter_errors(instance), key=lambda e: [str(p) for p in e.absolute_path])
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '$'}: {e.message}" for e in found[:25]]


def component_errors(name: str, instance: Any) -> list[str]:
    """Every way ``instance`` departs from the OpenAPI component ``name`` of docs/contracts/api.openapi.json (the document is
    self-contained: its components reference one another locally); empty when it conforms."""
    api = load_json(CONTRACTS / "api.openapi.json")
    assert name in api["components"]["schemas"], f"api.openapi.json has no component {name!r}"
    v = Draft202012Validator({"$schema": DIALECT, "$ref": f"#/components/schemas/{name}", "components": api["components"]})
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

    @classmethod
    def from_parts(cls, ref: str, consts: dict[str, Any], location: str | None = None) -> "Candidate":
        """A candidate built in memory (plants in the tests); ``ref`` is its path under schemas/ without the suffix."""
        c = object.__new__(cls)
        c.path = SCHEMAS / f"{ref}.schema.json"
        c.ref, c.consts, c.location, c.abstract = ref, dict(consts), location, False
        return c

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


def default_variants(cands: tuple[Candidate, ...] | None = None) -> dict[str | None, list[str]]:
    """The variant schemas that omit the ``outputs.kind`` const, by the ``case_id`` const they declare (exactly one
    per case may; ``None`` collects those that declare no case)."""
    out: dict[str | None, list[str]] = {}
    for c in candidates() if cands is None else cands:
        if c.consts.get("schema") == "contraste.case/v1" and "outputs.kind" not in c.consts:
            out.setdefault(c.consts.get("case_id"), []).append(c.ref)
    return out


def default_violations(cands: tuple[Candidate, ...] | None = None) -> list[str]:
    """One message per case that has more than one default variant schema."""
    return [f"case {case}: more than one variant schema omits the outputs.kind const: {sorted(refs)}"
            for case, refs in default_variants(cands).items() if len(refs) > 1]


def case_folder_violations(cands: tuple[Candidate, ...] | None = None) -> list[str]:
    """Schemas under ``schemas/<case>/`` (any folder but ``common``) without a ``case_id`` const equal to the folder
    name upper-cased."""
    if cands is None:
        cands = tuple(Candidate(p) for p in schema_files())
    out = []
    for c in cands:
        folder = c.ref.split("/")[0]
        if folder != "common" and c.consts.get("case_id") != folder.upper():
            out.append(f"{c.ref}: case_id const is {c.consts.get('case_id')!r}, expected {folder.upper()!r}")
    return out


def schema_for_document(path: Path, doc: Any, cands: tuple[Candidate, ...] | None = None) -> str:
    """The schema ref (``common/case-index``) of the document at ``path`` (any path under the repository)."""
    cands = candidates() if cands is None else cands
    bad = default_violations(cands)
    if bad:
        raise SelectionError("; ".join(bad))
    relpath = path.resolve().relative_to(ROOT).as_posix()
    scored = [(c.score(relpath, doc), c.ref) for c in cands]
    scored = [(s, ref) for s, ref in scored if s is not None]
    if not scored:
        raise SelectionError(f"{relpath}: matches no schema")
    best = max(s for s, _ in scored)
    top = sorted(ref for s, ref in scored if s == best)
    if len(top) > 1:
        raise SelectionError(f"{relpath}: matches {len(top)} schemas equally: {top}")
    return top[0]


# --- schemas that may have no committed document ---------------------------------------------------------------


def catalog_rows() -> list[dict[str, str]]:
    """The rows of the catalog's first table with a ``schema file`` and a ``status`` column."""
    rows, header = [], None
    for line in (CONTRACTS / "catalog.md").read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            if header and rows:
                break
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = cells if "schema file" in cells and "status" in cells else None
        elif not all(set(c) <= set(":- ") for c in cells):
            rows.append(dict(zip(header, cells)))
    return rows


def latest_history_version(contract_id: str) -> str:
    """The newest version the catalog's History table records for a contract (its rows carry a date in the third column)."""
    versions = []
    for line in (CONTRACTS / "catalog.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) > 2 and cells[0] == contract_id and len(cells[2]) == 10 and cells[2][4] == "-" and cells[2][7] == "-":
            versions.append(cells[1])
    if not versions:
        raise LookupError(f"no History row for {contract_id}")
    return max(versions, key=lambda v: tuple(int(x) for x in v.split(".")))


def exempt_from_documents(rows: list[dict[str, str]], fixtures: list[Path]) -> set[str]:
    """Schemas allowed to have no committed document under data/ or the registries: those whose catalog row is
    ``active`` (served by a provider) and those that a document under docs/contracts/fixtures/ covers."""
    out = {r["schema file"].removeprefix("docs/contracts/schemas/").removesuffix(".schema.json")
           for r in rows if r.get("status", "").lower() == "active" and r["schema file"].startswith("docs/contracts/schemas/")}
    for f in fixtures:
        out.add(schema_for_document(f, load_json(f)))
    return out


def fixture_documents() -> list[Path]:
    return sorted((CONTRACTS / "fixtures").rglob("*.json"))


def unused_schemas(chosen: set[str], selectable: set[str], exempt: set[str]) -> list[str]:
    """Selectable schemas that no document selects and that nothing exempts."""
    return sorted(selectable - chosen - exempt)


def committed_documents() -> list[Path]:
    """Every document the contracts cover: all of data/derived, the fixtures under docs/contracts/fixtures and the
    three registries."""
    docs = sorted(p for p in DERIVED.rglob("*.json")) + fixture_documents()
    docs += [ROOT / "data-pipeline" / "config" / "sources.json", ROOT / "data-pipeline" / "config" / "licences.json",
             ROOT / "data" / "sources" / "manifest.json"]
    return docs
