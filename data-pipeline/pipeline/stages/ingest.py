"""Stage ingest: read a fetched source from the device data root and pass it through contract 1.

The registry decides whether the case may read the source at all; the licence manifest says which file the bytes
are (a file whose hash differs from the pinned one is refused, since the artifacts would no longer derive from what
the manifest records); the reader maps the publisher's layout; contract 1 accepts, rejects, flags or excludes.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from ..io import fetch as fetching
from ..io import sources as registry
from ..io.contract import ContractReport, Field, Rule, validate


class IngestError(RuntimeError):
    """The raw file is missing, or is not the file the licence manifest pins."""


def raw_file(source_id: str, name: str, data_root: Path, manifest: dict | None = None) -> Path:
    path = Path(data_root) / "raw" / source_id / name
    if not path.is_file():
        raise IngestError(f"{path} is missing: fetch it with data-pipeline/fetch.py {source_id} --data-root <root>")
    man = manifest if manifest is not None else fetching.load_manifest()
    pinned = {f["name"]: f["sha256"] for f in man["sources"].get(source_id, {}).get("files", [])}
    if name not in pinned:
        raise IngestError(f"{source_id}/{name} is not in the licence manifest; fetch it first")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != pinned[name]:
        raise IngestError(f"{source_id}/{name}: the bytes on disk ({digest[:12]}) are not the pinned ones "
                          f"({pinned[name][:12]}); fetch again")
    return path


def ingest(
    case_id: str,
    source_id: str,
    file_name: str,
    reader: Callable[[Path], list[dict[str, Any]]],
    *,
    data_root: Path,
    family: str,
    extra_fields: Sequence[Field] = (),
    extra_rules: Sequence[Rule] = (),
    params: dict | None = None,
) -> tuple[pd.DataFrame, ContractReport]:
    """The accepted records as a frame, in input order, and the contract-1 report."""
    registry.assert_case_inputs(case_id, [source_id])
    records = reader(raw_file(source_id, file_name, data_root))
    report = validate(family, records, params=params, extra_fields=extra_fields, extra_rules=extra_rules)
    if not report.accepted:
        raise IngestError(f"{case_id}: contract 1 accepted no record of {source_id}")
    return pd.DataFrame(report.accepted), report
