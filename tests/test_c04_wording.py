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
    # the two clauses of the pre-registered rule, in order: "so the clause holds|fails" and "así que la cláusula se verifica|falla"
    en_clauses = re.findall(r"so the clause (holds|fails)", f["en"])
    es_clauses = re.findall(r"así que la cláusula (se verifica|falla)", f["es"])
    assert len(en_clauses) == len(es_clauses) == 2
    assert [c == "holds" for c in en_clauses] == [c == "se verifica" for c in es_clauses]
    # the refutation and the verdict on the hypothesis, said the same way in both languages
    en = re.search(r"The plan's refutation (is met|is not met): the hypothesis is (refuted|not refuted)$", f["en"].rstrip())
    es = re.search(r"La refutación del plan (se verifica|no se verifica): la hipótesis (queda refutada|no queda refutada)$", f["es"].rstrip())
    assert en and es, (f["en"][-120:], f["es"][-120:])
    assert (en.group(1) == "is met") == (es.group(1) == "se verifica") == (en.group(2) == "refuted") == (es.group(2) == "queda refutada")


def test_adversarial_a_spanish_clause_out_of_step_with_the_english_is_caught():
    """The same reading on a planted pair: the English says the clause holds and the Spanish says it fails."""
    en = "x, so the clause holds. y, so the clause fails. The plan's refutation is met: the hypothesis is refuted"
    es = "x, así que la cláusula falla. y, así que la cláusula falla. La refutación del plan se verifica: la hipótesis queda refutada"
    en_clauses = re.findall(r"so the clause (holds|fails)", en)
    es_clauses = re.findall(r"así que la cláusula (se verifica|falla)", es)
    assert [c == "holds" for c in en_clauses] != [c == "se verifica" for c in es_clauses]
    assert CUMPLE.search("así que la cláusula se cumple") is not None
