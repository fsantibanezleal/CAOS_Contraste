"""The Spanish clauses of C04's withdrawal finding say "se verifica" where the English says "holds" or "is met".

The governance text rule refuses a document whose text states an approval, a certification or a compliance, and "cumple" is on its
list (tests/contracts_u15/semantics.py); the plan's clause and refutation are results, not a compliance claim, so the Spanish words
are the ones the rule accepts. The committed document is checked as committed (no test bakes the case, ADR-0074)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCER = ROOT / "data-pipeline" / "pipeline" / "cases" / "c04_transitions.py"
CUMPLE = re.compile(r"\bcumple\b", re.I)


def test_the_producer_writes_no_cumple():
    assert CUMPLE.search(PRODUCER.read_text(encoding="utf-8")) is None


def test_the_committed_withdrawals_document_has_the_clauses_in_step_with_the_english():
    doc = json.loads((ROOT / "data" / "derived" / "C04" / "withdrawals.json").read_text(encoding="utf-8"))
    f = next(x for x in doc["findings"] if x["id"] == "F-WITHDRAW-BOUNDS")["title"]
    assert CUMPLE.search(f["es"]) is None
    assert "holds in" in f["en"] and "se verifica en" in f["es"]
    tail = f["es"].split("la refutación del plan")[1].strip()
    met = f["en"].rstrip().endswith("is met")
    assert met or f["en"].rstrip().endswith("is not met")
    assert tail == ("se verifica" if met else "no se verifica")
