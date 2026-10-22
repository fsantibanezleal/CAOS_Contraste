"""U16-F7 (b07 m3): the F5 finding of C14 counts its dates in words, in both languages (no "date(s)" pattern)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_the_breach_finding_counts_dates_with_a_plural_form():
    seen = 0
    for path in sorted((ROOT / "data" / "derived" / "C14").glob("*.json")):
        for f in json.loads(path.read_text(encoding="utf-8")).get("findings", []):
            for lang in ("en", "es"):
                assert "(s)" not in f["title"][lang], (path.name, f["id"])
            if f["id"] == "F5":
                seen += 1
                assert " dates where" in f["title"]["en"] or " date where" in f["title"]["en"]
                assert " fechas en que" in f["title"]["es"] or " fecha en que" in f["title"]["es"]
    assert seen >= 1
