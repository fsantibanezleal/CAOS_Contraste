"""The readers of the committed documents the governance bake reads.

Every path the bake reads goes through a ``Reader``, which records it with the sha256 of its bytes with line endings normalised to LF (a Windows
checkout hashes as a Linux one). A case document that is absent, unreadable or not what its manifest says stops the bake with the file named:
the bake never publishes a partial inventory. The case documents are read-only here (R3 of the U15 sizing): nothing in this module writes.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
CHANGELOG = "CHANGELOG.md"
INDEX = "data/derived/manifests/index.json"
RELEASE = re.compile(r"(?m)^## \[(\d\.\d\d\.\d\d\d)\], (\d{4}-\d\d-\d\d)$")


class BakeError(ValueError):
    """The bake cannot read what it needs: nothing is written (the message names the file)."""


def sha256_lf(raw: bytes) -> str:
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


class Reader:
    """Reads files under a repository root and remembers each path with its sha256."""

    def __init__(self, root: Path | str = REPO_ROOT) -> None:
        self.root = Path(root)
        self.reads: dict[str, str] = {}

    def exists(self, rel: str) -> bool:
        return (self.root / rel).is_file()

    def _bytes(self, rel: str) -> bytes:
        path = self.root / rel
        if not path.is_file():
            raise BakeError(f"{rel}: the file is absent (the bake reads the committed documents and publishes nothing without it)")
        raw = path.read_bytes()
        self.reads[rel] = sha256_lf(raw)
        return raw

    def text(self, rel: str) -> str:
        return self._bytes(rel).decode("utf-8")

    def json(self, rel: str) -> Any:
        raw = self._bytes(rel)
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BakeError(f"{rel}: the document is not valid JSON ({exc})") from exc

    def documents_read(self) -> list[dict[str, Any]]:
        """Every path read with its sha256, sorted by path (the order is the same in every run)."""
        return [{"path": p, "sha256": h, "ref": None} for p, h in sorted(self.reads.items())]


def release_dates(reader: Reader) -> dict[str, str]:
    """Release version to date, from the headings ``## [X.XX.XXX], YYYY-MM-DD`` of CHANGELOG.md (A D1 A34, R4: a committed date)."""
    dates = dict(RELEASE.findall(reader.text(CHANGELOG).replace(chr(13) + chr(10), chr(10))))
    if not dates:
        raise BakeError(f"{CHANGELOG}: no release heading '## [X.XX.XXX], YYYY-MM-DD' was found")
    return dates


def newest_release(dates: dict[str, str]) -> tuple[str, str]:
    """The newest release heading: the as-of date of W15-13 (the maximum date, the later version on a tie)."""
    return max(((d, v) for v, d in dates.items()))[::-1]


@dataclass(frozen=True)
class ModelsDoc:
    path: str
    fit_id: str
    doc: dict[str, Any]


@dataclass(frozen=True)
class VariantDoc:
    path: str
    variant_id: str
    doc: dict[str, Any]


@dataclass
class Case:
    case_id: str
    manifest_path: str
    manifest: dict[str, Any]
    models: dict[str, ModelsDoc] = field(default_factory=dict)       # fit id -> models document
    variants: dict[str, VariantDoc] = field(default_factory=dict)    # variant id -> variant document (in the manifest's order)


def read_corpus(reader: Reader) -> tuple[dict[str, Case], list[dict[str, str]]]:
    """(the built cases, the planned ones as ``{case_id, reason}``).

    The case index names every case. A case with a manifest is built: its manifest's ``artifacts`` name its models documents (role ``models``) and
    its variant documents (role ``variant``), each of which must exist and carry the case and the id the manifest states. A case with neither a
    manifest nor a folder under ``data/derived`` is planned. A manifest absent for a case whose folder exists, or an artifact absent, stops the bake.
    """
    index = reader.json(INDEX)
    cases: dict[str, Case] = {}
    planned: list[dict[str, str]] = []
    for entry in index["cases"]:
        cid = entry["case_id"]
        rel = f"data/derived/{entry['manifest_path']}"
        if not reader.exists(rel):
            if (reader.root / "data" / "derived" / cid).exists():
                raise BakeError(f"{rel}: the manifest of the built case {cid} is absent (its folder data/derived/{cid} exists)")
            planned.append({"case_id": cid, "reason": "planned: no committed document or models record exists"})
            continue
        manifest = reader.json(rel)
        if manifest.get("case_id") != cid:
            raise BakeError(f"{rel}: the manifest states case {manifest.get('case_id')!r}, the case index {cid!r}")
        case = Case(cid, rel, manifest)
        for art in manifest["artifacts"]:
            doc_rel = f"data/derived/{art['path']}"
            doc = reader.json(doc_rel)
            if doc.get("case_id") != cid:
                raise BakeError(f"{doc_rel}: the document states case {doc.get('case_id')!r}, its manifest {cid}")
            if art["role"] == "models":
                fit = doc.get("fit_id")
                if not fit:
                    raise BakeError(f"{doc_rel}: the models document states no fit_id")
                case.models[fit] = ModelsDoc(doc_rel, fit, doc)
            elif art["role"] == "variant":
                if doc.get("variant_id") != art["variant_id"]:
                    raise BakeError(f"{doc_rel}: the document states variant {doc.get('variant_id')!r}, its manifest {art['variant_id']!r}")
                case.variants[art["variant_id"]] = VariantDoc(doc_rel, art["variant_id"], doc)
            else:
                raise BakeError(f"{rel}: the artifact {art['path']} has the role {art['role']!r}, which the bake does not know")
        if not case.models:
            raise BakeError(f"{rel}: the manifest names no models document, so the case has no fit to inventory")
        cases[cid] = case
    return cases, planned


def resolve(doc: Any, pointer: str) -> Any:
    """The value at a JSON pointer (``/a/0/b``); raises BakeError when it does not exist."""
    node = doc
    for raw in [p for p in pointer.split("/")[1:]]:
        key = raw.replace("~1", "/").replace("~0", "~")
        try:
            node = node[int(key)] if isinstance(node, list) else node[key]
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise BakeError(f"the pointer {pointer!r} does not exist") from exc
    return node
