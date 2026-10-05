"""Licence lineage and provenance (SDD sections 2.2 and 6, oracle 6).

Every artifact carries the list of its inputs (each source with its licence class and the hashes of the files read)
and its truth status. The export stage builds the lineage from the licence manifest and calls
``assert_publishable`` before writing anything: an input from a link-only or unusable source refuses the artifact,
naming the source. The ``provenance`` block an artifact carries is written from the same object, so what the
artifact claims and what was checked cannot differ.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..io import fetch as fetching
from ..io import sources as registry

TRUTH_STATUSES = ("real-outcomes", "synthetic-known-truth", "synthetic-calibrated", "published-answer")
PUBLISHABLE = registry.READABLE


@dataclass(frozen=True)
class Input:
    source_id: str
    klass: str
    files: tuple[tuple[str, str], ...]  # (file name, sha256)

    def to_json(self) -> dict[str, Any]:
        return {"source": self.source_id, "class": self.klass,
                "files": [{"name": n, "sha256": h} for n, h in self.files]}


@dataclass(frozen=True)
class Lineage:
    case_id: str
    truth_status: str
    inputs: tuple[Input, ...]
    seed: int
    code_version: str
    riskvalidation_version: str | None = None
    generators: tuple[str, ...] = field(default=())  # Contraste-owned generators used (no third-party licence)

    def classes(self) -> dict[str, str]:
        return {i.source_id: i.klass for i in self.inputs}

    def provenance(self) -> dict[str, Any]:
        return {
            "truth_status": self.truth_status,
            "inputs": [i.to_json() for i in self.inputs],
            "licence_classes": self.classes(),
            "generators": list(self.generators),
            "seed": self.seed,
            "code_version": self.code_version,
            "riskvalidation_version": self.riskvalidation_version,
        }


def build(
    case_id: str,
    *,
    sources: list[str] | tuple[str, ...],
    truth_status: str,
    seed: int,
    code_version: str,
    riskvalidation_version: str | None = None,
    generators: tuple[str, ...] = (),
    manifest: dict[str, Any] | None = None,
    reg: dict[str, registry.Source] | None = None,
) -> Lineage:
    """Resolve each source's class from the registry and its file hashes from the licence manifest."""
    if truth_status not in TRUTH_STATUSES:
        raise ValueError(f"{case_id}: truth status {truth_status!r} is not one of {list(TRUTH_STATUSES)}")
    if not sources and not generators:
        raise ValueError(f"{case_id}: an artifact derives from at least one source or generator")
    sreg = reg if reg is not None else registry.load()
    man = manifest if manifest is not None else fetching.load_manifest()
    inputs = []
    for sid in sources:
        if sid not in sreg:
            raise registry.LicenceError(f"{case_id}: unknown source {sid!r}")
        row = man["sources"].get(sid)
        files = tuple((f["name"], f["sha256"]) for f in row["files"]) if row else ()
        inputs.append(Input(sid, sreg[sid].klass, files))
    return Lineage(case_id, truth_status, tuple(inputs), seed, code_version, riskvalidation_version, tuple(generators))


def assert_publishable(lineage: Lineage) -> None:
    """Refuse an artifact whose lineage includes a link-only or unusable source, or an input never fetched."""
    for inp in lineage.inputs:
        if inp.klass not in PUBLISHABLE:
            raise registry.LicenceError(
                f"{lineage.case_id}: refused, the input {inp.source_id} is {inp.klass} (it may be linked, never "
                "published)")
        if not inp.files:
            raise registry.LicenceError(
                f"{lineage.case_id}: refused, the input {inp.source_id} is not in the licence manifest (fetch it with "
                "data-pipeline/fetch.py first, so its bytes are hashed and its licence recorded)")
