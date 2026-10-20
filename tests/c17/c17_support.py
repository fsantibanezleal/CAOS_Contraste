"""Constants and the document loader of the C17 tests, under a module name of their own (BL-084: a helper imported as
`conftest` resolves to another case's conftest when several case folders run in one pytest session)."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DERIVED = ROOT / "data" / "derived"
DOCS = ("xi-0-6", "xi-0-8", "xi-0-96", "xi-1-1")


def load(rel: str) -> dict:
    return json.loads((DERIVED / rel).read_text(encoding="utf-8"))
