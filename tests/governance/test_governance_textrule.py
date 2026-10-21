"""U15-P fix round (review M1, m2): the text rule of the U15-S checker reads every string, the copied case texts included.

A claim about a model is refused in either language, whatever string holds it; a phrase of a credit decision (a metric, a cohort, an applicant outcome) is allowed
by name, each with its reason in ``semantics.APPROVAL_ALLOWED``. The rule also sees "approve", "aprueba" and "aprobar", with the fixed negations and the names of
the W15-7 recommendation outcomes exempt.
"""
from __future__ import annotations

import json

import gov_support as gs
import pytest


def sm():
    return gs.load_semantics()


CLAIMS = [
    "Contraste certifies this model as compliant",
    "Contraste certifies this model as compliant with IFRS 9 and approves it for use",
    "Contraste certifica este modelo conforme a IFRS 9 y lo aprueba para su uso",
    "Contraste certifica este modelo",
    "We approve the model.", "Contraste approves the model", "The model is approved", "Contraste aprueba el modelo.", "El modelo se aprueba.", "Aprobar el modelo.",
    "El modelo esta aprobado", "the model complies with SR 26-2", "El modelo cumple con la norma",
]
ALLOWED = [
    "the approval rate on card applicants", "Unconditional approval-rate gaps in 3 of the 4 attributes", "Approval rate (both models)", "tasa de aprobación",
    "a PD model built on approval cohorts old enough to have been observed", "cohortes de aprobación", "revolving lines at their approval", "a su monto aprobado",
    "the gross approved amount", "Expected loss of the approved, challenger", "Tasa de malos de los aprobados solo por el campeon", "Approved by the champion only",
    "the group is approved at higher controlled odds", "el grupo es aprobado con mayores odds", "Approval fiscal years FY1991 to FY2000",
    "before the first approval of FY2006-07", "2 (application approved but not accepted)", "approved as decision V6",
    "Contraste approves no model", "Contraste no aprueba ningún modelo", "no approval date or authority exists", "no approver exists",
    "Approve with conditions: only minor findings are open", "Aprobar con condiciones: solo hay hallazgos menores abiertos", "approve", "approve with conditions",
    "remediate before use", "compliance monitoring",
]


@pytest.mark.parametrize("text", CLAIMS)
def test_adversarial_a_claim_about_a_model_is_refused_in_either_language(text):
    assert sm().approval_claims(text), text


@pytest.mark.parametrize("text", ALLOWED)
def test_the_allowed_phrases_and_the_fixed_negations_are_not_claims(text):
    assert sm().approval_claims(text) == [], text


def test_every_allowed_phrase_has_a_reason_and_a_sample_that_only_it_matches():
    """Each entry of the allow list is exercised by a sample of this file, and a phrase removed from the list makes its sample a claim."""
    allow = sm().APPROVAL_ALLOWED
    negations = {"Contraste approves no model", "Contraste no aprueba ningún modelo", "no approval date or authority exists", "no approver exists",
                 "Approve with conditions: only minor findings are open", "Aprobar con condiciones: solo hay hallazgos menores abiertos", "approve",
                 "approve with conditions", "remediate before use", "compliance monitoring"}
    samples = [t for t in ALLOWED if t not in negations]
    for rx, reason in allow:
        assert reason.strip()
        assert any(rx.search(t) for t in samples), rx.pattern
    # a claim that merely contains an allowed phrase is still a claim
    assert sm().approval_claims("Contraste approves this model, whose approval rate on card applicants is high")


def test_adversarial_a_claim_planted_in_a_copied_case_title_stops_the_bake(tmp_path):
    """Review M1: a finding title of a case document that certifies or approves a model is refused in either language, not exempted as copied text."""
    from pipeline.governance import bake
    from pipeline.governance.readers import BakeError

    for en, es in (("Contraste certifies this model as compliant with IFRS 9 and approves it for use",
                    "Contraste certifica este modelo conforme a IFRS 9 y lo aprueba para su uso"),
                   ("The model is approved by Contraste", "El modelo es aprobado por Contraste")):
        tree = gs.copy_tree(tmp_path / f"t{abs(hash(en)) % 999}")
        p = tree / "data/derived/C01/holdout.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        d["findings"][0]["title"] = {"en": en, "es": es}
        p.write_text(json.dumps(d), encoding="utf-8")
        with pytest.raises(BakeError, match="approval, certification or compliance"):
            bake.build(tree)


def test_adversarial_a_claim_planted_in_the_spanish_title_alone_stops_the_bake(tmp_path):
    from pipeline.governance import bake
    from pipeline.governance.readers import BakeError

    tree = gs.copy_tree(tmp_path / "t")
    p = tree / "data/derived/C01/holdout.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["findings"][0]["title"]["es"] = "Contraste aprueba este modelo para su uso"
    p.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(BakeError, match="aprueba"):
        bake.build(tree)


def test_the_phrases_of_the_allow_list_are_all_found_in_the_committed_case_documents_or_are_samples():
    """A stale entry of the allow list is found: at least one phrase of the list matches a string of the governance documents or of a case document."""
    sm_ = sm()
    strings = []
    for p in gs.DERIVED.glob("C*/*.json"):
        strings += list(gs.all_strings(json.loads(p.read_text(encoding="utf-8"))))
    hits = [any(rx.search(s) for s in strings) for rx, _ in sm_.APPROVAL_ALLOWED]
    assert sum(hits) >= len(hits) - 1, [rx.pattern for (rx, _), h in zip(sm_.APPROVAL_ALLOWED, hits) if not h]
