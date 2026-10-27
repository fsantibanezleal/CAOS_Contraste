"""U16-R2b c14 B1: a planted deficiency the PLA misses is stated by its miss rate. The title said "The PLA misses the planted stale
volatility in 0.0% of 1,000 replications" when the PLA caught it in 0 % of them, so it missed in 100 %: the sentence said the
opposite of the result."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from pipeline.cases.c13 import documents

ROOT = Path(__file__).resolve().parents[2]


def _outputs() -> dict:
    doc = json.loads((ROOT / "data" / "derived" / "C13" / "stale-volatility.json").read_text(encoding="utf-8"))
    return copy.deepcopy(doc["outputs"])


def _pla(out: dict) -> dict:
    return next(f for f in documents.findings(out) if f["id"] == "F-PLA")


def test_a_miss_states_the_miss_rate_then_the_catch_rate() -> None:
    out = _outputs()
    out["detection"]["share_amber_or_red"] = 0.0
    out["detection"]["share_red"] = 0.0
    t = _pla(out)["title"]
    assert "misses" in t["en"] and "in 100.0\u00a0% of" in t["en"] and "amber or red in 0.0\u00a0%" in t["en"]
    assert "no detecta" in t["es"] and "en 100,0" in t["es"]


def test_a_catch_states_the_catch_rate() -> None:
    out = _outputs()
    out["detection"]["share_amber_or_red"] = 0.97
    t = _pla(out)["title"]
    assert t["en"].startswith("The PLA catches") and "in 97.0\u00a0% of" in t["en"]
