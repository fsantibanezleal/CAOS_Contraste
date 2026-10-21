"""U15-P: the text of the governance documents and of docs/governance.md. Contraste approves no model, so no string states an approval, a
certification or a compliance (SDD non-goal 1, 06 I.6), in either language; a convention is labelled `convention` and never called regulatory;
every Spanish text carries its accents and eñes and holds no English.
"""
from __future__ import annotations

import re

import gov_support as gs
import pytest


def everything(baked):
    yield "inventory", baked.inventory
    yield "findings", baked.findings
    yield "appetite", baked.appetite
    for k, r in baked.reports.items():
        yield f"report {k}", r


def test_no_string_states_an_approval_a_certification_or_a_compliance_in_either_language(baked):
    sm = gs.load_semantics()
    from pipeline.governance import bake
    from pipeline.governance.readers import Reader, read_corpus

    copied = bake._copied_texts(read_corpus(Reader())[0])  # the case documents' own words ('approval cohorts', 'approval rate') are not Contraste's statement
    for name, doc in everything(baked):
        for s in gs.all_strings(doc):
            if s not in copied:
                assert sm.approval_claims(s) == [], (name, s[:120])
    for s in (gs.PAGE.read_text(encoding="utf-8"), baked.page_block):
        for line in s.splitlines():
            assert sm.approval_claims(line) == [], line[:120]


def test_no_convention_is_called_regulatory_and_every_label_is_convention(baked):
    sm = gs.load_semantics()
    for name, doc in everything(baked):
        assert sm.convention_violations(doc) == [], name
        for obj in sm.convention_dicts(doc):
            if "basis" in obj:  # a convention table; a policy label of a test row is a name, not a convention
                assert obj["label"] == "convention", (name, obj["label"])
        for s in gs.all_strings(doc):
            assert sm.regulatory_claims(s) == [], (name, s[:120])
    for line in baked.page_block.splitlines():
        assert sm.regulatory_claims(line) == [], line[:120]


ENGLISH = re.compile(r"\b(the|and|of|with|for|are|is|from|which|that|this|only|exists?|not|per|has|have|rule|finding|findings|model)\b", re.I)
#: unaccented spellings the bake must have restored: a singular -cion/-sion word, the n written for the eñe, and the unaccented words of the restoration table
#: (a plural -ciones has no accent, so it is not searched for)
_RESTORED = __import__("importlib").import_module("pipeline.governance.spanish").WORDS
UNACCENTED = re.compile(r"(?<![\w.@/])(\w+(?:cion|sion)|diseno\w*|peldano\w*|pequeno\w*|" + "|".join(sorted(_RESTORED, key=len, reverse=True)) + r")(?![\w(@/])", re.I)
#: correct without an accent
ALLOWED = {"version", "versiones", "decision", "dia", "dias"} - {"version", "decision", "dia", "dias"}


def es_texts(baked):
    """The Spanish texts the governance documents author (a text copied verbatim from a case document is the case's own, and is not rewritten)."""
    copied = gs.copied_texts()
    for name, doc in everything(baked):
        for pair in gs.bilingual_pairs(doc):
            if pair["es"] not in copied:
                yield name, pair


def test_every_spanish_text_carries_its_accents_and_enyes(baked):
    bad = []
    for name, pair in es_texts(baked):
        for m in UNACCENTED.finditer(pair["es"]):
            word = m.group(0).lower()
            if word in ALLOWED or word.endswith("ssion"):
                continue
            bad.append((name, word, pair["es"][:100]))
    assert bad == [], bad[:10]


def test_no_english_appears_in_a_spanish_field(baked):
    bad = []
    allowed_phrase = re.compile(r"(Contraste|riskvalidation|ECB F|W15-\d+|SDD|IFRS 9|PMA|RWEA)")
    for name, pair in es_texts(baked):
        es = allowed_phrase.sub(" ", pair["es"])
        # a quoted identifier (a test id, a status, a key) is not prose
        es = re.sub(r"\b\w+(?:-\w+)+\b|`[^`]*`|\b[a-z0-9_.-]+@[\w.@-]+\b|\b\w+_\w+\b|\(risk_accepted\)", " ", es)
        found = ENGLISH.findall(es)
        if found:
            bad.append((name, found[:4], pair["es"][:110]))
    assert bad == [], bad[:8]


def test_the_restoration_table_leaves_a_text_that_is_already_accented_unchanged():
    from pipeline.governance import spanish

    for text in ("Descripción del modelo y uso previsto", "diseño de las pruebas", "los peldaños de la escalera", "Opinión global", "Año 2026"):
        assert spanish.restore(text) == text
    assert spanish.restore("Descripcion del modelo y uso previsto") == "Descripción del modelo y uso previsto"
    assert spanish.restore("las alternativas de diseno") == "las alternativas de diseño"
    assert spanish.restore("los peldanos de la escalera") == "los peldaños de la escalera"
    assert spanish.restore("Opinion global") == "Opinión global"
    # an ambiguous word is decided by its phrase, not by the word: 'esta' with a following adjective is a verb, before a noun a demonstrative
    assert spanish.restore("la independencia no esta establecida") == "la independencia no está establecida"
    assert spanish.restore("esta entrada tiene un hallazgo") == "esta entrada tiene un hallazgo"


def test_the_accented_text_is_utf8_nfc(baked):
    import unicodedata

    for name, pair in es_texts(baked):
        assert unicodedata.normalize("NFC", pair["es"]) == pair["es"], name


def test_adversarial_an_unaccented_spanish_text_is_found_by_the_check_and_restored_by_the_table():
    """The accent check must be able to fail: planted unaccented texts are found, and the restoration table repairs them."""
    from pipeline.governance import spanish

    planted = "Descripcion del modelo: el diseno de la implementacion y la politica de los peldanos"
    assert {m.group(0).lower() for m in UNACCENTED.finditer(planted)} >= {"descripcion", "diseno", "implementacion", "politica", "peldanos"}
    fixed = spanish.restore(planted)
    assert not list(UNACCENTED.finditer(fixed)) and "diseño" in fixed and "peldaños" in fixed
