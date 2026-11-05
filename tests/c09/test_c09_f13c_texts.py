"""U16-F13c (the R5 sweep of the R4 c12 n7 class on C09): the English findings write a percent as the shell does, with a no-break space
before the sign ("22.3 %"), as the Spanish ones do; never Python's "22.3%". Tested on the producer's function over the committed outputs
of every level, never by re-baking."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from pipeline.cases.c09 import documents
from pipeline.core.text import NBSP

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("n", range(6))
def test_every_english_finding_writes_its_percents_with_the_shell_space(n):
    out = json.loads((ROOT / "data" / "derived" / "C09" / f"level-{n}.json").read_text(encoding="utf-8"))["outputs"]
    titles = [f["title"] for f in documents.findings(out, 0.1)]
    assert any("%" in t["en"] for t in titles)
    for t in titles:
        assert not re.search(r"\d%", t["en"]), t["en"]
        assert not re.search(r"\d%", t["es"]), t["es"]
    treatment = next(f["title"]["en"] for f in documents.findings(out, 0.1) if f["id"] == "F-TREATMENT")
    assert re.search(rf"\d\.\d{NBSP}% of the CCFs lie above 1", treatment), treatment
