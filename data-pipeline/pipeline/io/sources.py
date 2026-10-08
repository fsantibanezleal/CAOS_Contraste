"""The source registry: every data and scenario source, its licence and its redistribution class (SDD section 2.1).

``data-pipeline/config/sources.json`` is transcribed from research dossier 08 (the master matrix). This module
loads it, checks it, and answers the one question the pipeline must never get wrong: may this case read this
source, and may an artifact derived from it be published?
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REGISTRY = Path(__file__).resolve().parents[2] / "config" / "sources.json"
SCHEMA = "contraste.sources/v1"

CLASSES = ("mirror-allowed", "derived-only", "link-only", "unusable")
#: the classes whose data a case may read as an input
READABLE = ("mirror-allowed", "derived-only")
#: the classes whose raw rows may be committed to the repository
MIRRORABLE = ("mirror-allowed",)

_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_CASE = re.compile(r"^C\d{2}$")
_REQUIRED = ("id", "name", "publisher", "landing", "licence", "class", "access", "cases", "unverified")


class LicenceError(ValueError):
    """A source's licence class forbids the use asked of it."""


class RegistryError(ValueError):
    """The registry itself is malformed."""


@dataclass(frozen=True)
class FetchFile:
    name: str
    url: str


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    publisher: str
    landing: str
    licence: str
    klass: str
    access: str
    cases: tuple[str, ...]
    unverified: tuple[str, ...]
    attribution: str = ""
    fetch_kind: str | None = None  # "http", "manual" or "cerep" (pipeline.io.cerep: a paced JSON interface)
    files: tuple[FetchFile, ...] = ()
    plan: dict[str, Any] | None = None  # a cerep fetch's query plan

    @property
    def readable(self) -> bool:
        return self.klass in READABLE

    @property
    def mirrorable(self) -> bool:
        return self.klass in MIRRORABLE


def _check_entry(e: dict[str, Any]) -> list[str]:
    sid = e.get("id", "?")
    out = [f"{sid}: missing {k!r}" for k in _REQUIRED if k not in e]
    if out:
        return out
    if not _ID.match(e["id"]):
        out.append(f"{sid}: the id is lower-case words joined by hyphens")
    if e["class"] not in CLASSES:
        out.append(f"{sid}: class {e['class']!r} is not one of {list(CLASSES)}")
    if not isinstance(e["licence"], str) or len(e["licence"].strip()) < 8:
        out.append(f"{sid}: the licence fragment is empty (quote the publisher's words)")
    if not str(e["landing"]).startswith(("http://", "https://")):
        out.append(f"{sid}: the landing page is not a URL")
    cases = e["cases"]
    if not isinstance(cases, list) or not all(isinstance(c, str) and _CASE.match(c) for c in cases):
        out.append(f"{sid}: cases is a list of case ids C01 to C99")
    elif cases and e["class"] not in READABLE:
        out.append(f"{sid}: a {e['class']} source is linked, never read; it cannot list cases {cases}")
    if not isinstance(e["unverified"], list):
        out.append(f"{sid}: unverified is a list of open questions")
    if "UNVERIFIED" in e["licence"] and not e["unverified"] and e["class"] in READABLE:
        out.append(f"{sid}: the licence is marked UNVERIFIED; name the open question in 'unverified'")
    fetch = e.get("fetch")
    if fetch is not None and fetch.get("kind") == "cerep":
        from . import cerep

        if e["class"] not in READABLE:
            out.append(f"{sid}: a {e['class']} source has no fetch specification")
        if not str(fetch.get("plan", {}).get("endpoint", cerep.ENDPOINT)).startswith("https://"):
            out.append(f"{sid}: a cerep fetch names an https endpoint")
        out.extend(f"{sid}: {p}" for p in cerep.check_plan(fetch.get("plan")))
    elif fetch is not None:
        if fetch.get("kind") not in ("http", "manual"):
            out.append(f"{sid}: fetch kind is http, manual or cerep")
        if e["class"] not in READABLE:
            out.append(f"{sid}: a {e['class']} source has no fetch specification")
        files = fetch.get("files") or []
        if not files:
            out.append(f"{sid}: a fetch specification names its files")
        for f in files:
            if not f.get("name") or "/" in f["name"] or "\\" in f["name"]:
                out.append(f"{sid}: a fetched file has a plain name")
            if fetch.get("kind") == "http" and not str(f.get("url", "")).startswith("https://"):
                out.append(f"{sid}: an http fetch names an https URL for {f.get('name')}")
    return out


def load(path: Path | None = None) -> dict[str, Source]:
    """Load and check the registry; raise RegistryError listing every problem."""
    raw = json.loads((path or REGISTRY).read_text(encoding="utf-8"))
    problems: list[str] = []
    if raw.get("schema") != SCHEMA:
        problems.append(f"schema is {raw.get('schema')!r}, expected {SCHEMA!r}")
    entries = raw.get("sources") or []
    seen: set[str] = set()
    for e in entries:
        problems.extend(_check_entry(e))
        if e.get("id") in seen:
            problems.append(f"{e.get('id')}: declared twice")
        seen.add(e.get("id"))
    if problems:
        raise RegistryError("source registry: " + "; ".join(problems))
    out: dict[str, Source] = {}
    for e in entries:
        fetch = e.get("fetch") or {}
        files = tuple(FetchFile(f["name"], f.get("url", "")) for f in fetch.get("files") or ())
        if fetch.get("kind") == "cerep":
            from . import cerep

            base = fetch["plan"].get("endpoint", cerep.ENDPOINT)
            files = (FetchFile(cerep.FILTERS_FILE, base + "filters"),) + tuple(
                FetchFile(q.name, base + f"searchStatistics/{q.tab}") for q in cerep.plan_queries(fetch["plan"]))
        out[e["id"]] = Source(
            id=e["id"], name=e["name"], publisher=e["publisher"], landing=e["landing"], licence=e["licence"],
            klass=e["class"], access=e["access"], cases=tuple(e["cases"]), unverified=tuple(e["unverified"]),
            attribution=e.get("attribution", ""), fetch_kind=fetch.get("kind"), files=files,
            plan=fetch.get("plan") if fetch.get("kind") == "cerep" else None,
        )
    return out


def assert_case_inputs(case_id: str, source_ids: list[str] | tuple[str, ...], registry: dict[str, Source] | None = None) -> list[Source]:
    """Refuse a case that reads a source it may not read, or that the registry does not list it under."""
    reg = registry if registry is not None else load()
    out = []
    for sid in source_ids:
        if sid not in reg:
            raise LicenceError(f"{case_id}: unknown source {sid!r}")
        src = reg[sid]
        if not src.readable:
            raise LicenceError(f"{case_id}: {sid} is {src.klass}; it may be linked, never read")
        if case_id not in src.cases:
            raise LicenceError(f"{case_id}: {sid} does not list {case_id} among its cases (update the registry first)")
        out.append(src)
    return out
