"""U16-F7 (b09 m9): a finding that counts one red row says 'fila roja', not '1 filas rojas'."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_the_row_count_of_a_finding_agrees_in_number():
    seen = 0
    for path in sorted((ROOT / "data" / "derived" / "C20").glob("*.json")):
        for f in json.loads(path.read_text(encoding="utf-8")).get("findings", []):
            es = f["title"]["es"]
            assert not re.search(r"(?<![\d.,])1 filas rojas", es), (path.name, es)
            seen += bool(re.search(r"(?<![\d.,])1 fila roja", es))
    assert seen >= 1
