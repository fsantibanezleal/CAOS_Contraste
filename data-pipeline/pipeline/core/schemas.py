"""Validate a document against its schema before it is written (docs/contracts/catalog.md, the single source of every
contract). The schema files, their registry and the discovery rule that picks a document's schema live in
``tests/contracts/contract_schemas.py``; this module loads that one implementation, never a copy, so the producer
refuses exactly what the producer tests reject. It needs ``jsonschema`` (requirements-dev.txt), which the offline lane
installs next to the pipeline's pins."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
_TESTS = REPO_ROOT / "tests" / "contracts"


class SchemaViolation(ValueError):
    """A document about to be written does not conform to its schema."""


def _cs():
    if str(_TESTS) not in sys.path:
        sys.path.insert(0, str(_TESTS))
    try:
        import contract_schemas
    except ModuleNotFoundError as exc:  # jsonschema or referencing
        raise RuntimeError(f"validating against the schemas needs jsonschema ({exc}); "
                           "pip install -r requirements-dev.txt") from exc
    return contract_schemas


def validate_document(rel: str, doc: Any) -> str:
    """Check ``doc``, destined for the repository-relative path ``rel`` (``data/derived/C01/holdout.json``), against
    the schema discovery selects for it. Return the schema's ref; raise :class:`SchemaViolation` naming the path and
    the first validation error otherwise (also when no schema, or more than one, matches)."""
    cs = _cs()
    try:
        ref = cs.schema_for_document(REPO_ROOT / rel, doc)
    except cs.SelectionError as exc:
        raise SchemaViolation(f"{rel}: {exc}") from exc
    found = cs.errors(ref, doc)
    if found:
        raise SchemaViolation(f"{rel}: does not conform to {ref}: {found[0]}")
    return ref
