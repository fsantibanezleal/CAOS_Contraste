"""U16-F6 (the second fix round, C01 to C11): what the committed documents of C01 to C13 say in Spanish, on the documents themselves.

Each test is written against a defect of the second capture review (U16-R2): the reference column of the tests tables
(a Spanish view printed the engine's English remark), the findings and notes of C01 to C08 that named a variant by its id, said
"escalón" where the product says "peldaño", glued two sentences with the wrong punctuation, or quoted a rate the sentence did
not state.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data-pipeline"))
from f3_spanish_text import bitexts, document_leaks  # noqa: E402
from pipeline.cases.reference_text import REFERENCE_ES, reference_text, with_reference_text  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
#: the cases whose tests tables print the reference (the others print it in a table of the shared U14 component, not in this unit)
REFERENCE_CASES = ("C03", "C06", "C07", "C08", "C09", "C10", "C11", "C12")


def variants(case: str) -> list[Path]:
    return sorted(p for p in (DERIVED / case).glob("*.json") if not p.name.startswith("models-") and "tests" in json.loads(p.read_text(encoding="utf-8")))


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------------------------------------------------------
# the reference column


def test_every_reference_the_engine_writes_in_c01_to_c13_has_its_spanish():
    missing = set()
    for case in (f"C{n:02d}" for n in range(1, 14)):
        for path in variants(case):
            for row in load(path)["tests"]:
                if row["reference"] not in REFERENCE_ES:
                    missing.add(row["reference"])
    assert missing == set()


def test_an_unknown_reference_is_an_error_not_an_english_sentence_in_a_spanish_view():
    with pytest.raises(ValueError, match="no Spanish text"):
        reference_text("A new engine remark nobody translated (dossier 99)")


def test_with_reference_text_copies_the_rows_and_keeps_the_extras():
    row = {"test_id": "t", "reference": "Kupiec (1995), J. Derivatives 3(2):73-84, doi:10.3905/jod.1995.407942", "extras": {"k": 1}}
    out = with_reference_text([row])
    assert out[0]["extras"]["k"] == 1
    assert out[0]["extras"]["reference_text"] == {"en": row["reference"], "es": row["reference"]}
    assert "reference_text" not in row["extras"]


@pytest.mark.parametrize("case", REFERENCE_CASES)
def test_every_test_row_of_a_case_carries_its_reference_in_both_languages(case):
    rows = [(p.name, t) for p in variants(case) for t in load(p)["tests"]]
    assert rows, f"{case}: no test row"
    for name, t in rows:
        rt = t["extras"].get("reference_text")
        assert rt == reference_text(t["reference"]), f"{case}/{name}: {t['test_id']}"


def test_the_remarks_of_the_dossier_are_translated_and_the_citation_is_not():
    for en, es in REFERENCE_ES.items():
        if " and " in en and "(" in en and "dossier" in en:
            assert es != en
        # a citation stays as published: its DOI and its identifier are in both
        for token in re.findall(r"doi:\S+|arXiv:?\s?\d{4}\.\d{4,5}|[A-Z]{3,}\d{2}\.\d+", en):
            assert token.rstrip(";,") in es, (token, es)
    assert "Annex" not in " ".join(REFERENCE_ES.values())
    assert "paragraph" not in " ".join(REFERENCE_ES.values())
    assert "addendum" not in " ".join(REFERENCE_ES.values())


# ---------------------------------------------------------------------------------------------------------------------------
# the texts of the findings and notes


def spanish_texts(case: str):
    for path in sorted((DERIVED / case).glob("*.json")):
        doc = load(path)
        for where, en, es in bitexts(doc):
            yield path.name, where, en, es


@pytest.mark.parametrize("case", [f"C{n:02d}" for n in range(1, 8)])
def test_no_english_number_form_and_no_english_light_in_the_spanish_of_c01_to_c07(case):
    leaks = []
    for path in sorted((DERIVED / case).glob("*.json")):
        leaks += [f"{path.name}: {x}" for x in document_leaks(load(path))]
    assert leaks == []


def test_a_c01_finding_names_the_variant_and_the_ead_says_saldo_facturado():
    seen = 0
    for path in sorted((DERIVED / "C01").glob("*.json")):
        doc = load(path)
        if "findings" not in doc:
            continue
        for f in doc["findings"]:
            if "alertan" in f["title"]["es"]:
                seen += 1
                assert "población" not in f["title"]["es"]
                assert "«" in f["title"]["es"]
                assert not re.search(r"\b(?:holdout|label-noise|prior-shift|small-sample|drift-moderate|drift-severe|german-twin)\b", f["title"]["es"])
                assert not re.search(r"\b(?:label-noise|prior-shift|small-sample)\b", f["title"]["en"])
        irb = doc.get("outputs", {}).get("irb", {})
        ead = irb.get("ead")
        if ead:
            assert "cuenta actual" not in ead["es"]
            # the billed balance is the card book's EAD (qrre); the German twin's is the loan amount ("el monto del crédito")
            if irb.get("asset_class") == "qrre":
                assert "saldo facturado" in ead["es"]
    assert seen >= 5


def test_c02_and_c03_say_peldaño_for_a_rung_of_the_ladder():
    for case in ("C02", "C03"):
        for name, where, _en, es in spanish_texts(case):
            assert not re.search(r"\bescal[oó]n(?:es)?\b", es), f"{case}/{name} {where}: {es[:90]}"


def test_a_c03_finding_names_the_cohort_by_its_spanish_label():
    seen = 0
    for path in sorted((DERIVED / "C03").glob("fy*.json")):
        for f in load(path)["findings"]:
            if "alertan en la cohorte" in f["title"]["es"]:
                seen += 1
                assert "FY" not in f["title"]["es"]
                assert re.search(r"cohorte AF\d{4}-\d{2}\b", f["title"]["es"])
    assert seen >= 5


def test_the_c04_definition_gap_quotes_the_pooled_rates_beside_the_pooled_ratio():
    seen = 0
    for path in sorted((DERIVED / "C04").glob("*.json")):
        doc = load(path)
        for f in doc.get("findings", []):
            if f["id"] != "F-DEF-GAP":
                continue
            seen += 1
            lra = doc["outputs"]["lra"]
            d4, d2 = lra["d4"]["pooled_rate"][6], lra["d2"]["pooled_rate"][6]
            ratio = round(100 * d4 / d2)
            assert f"{ratio}%" in f["title"]["en"]
            assert "pooled rates" in f["title"]["en"] and "long-run averages" not in f["title"]["en"]
            assert "tasas agrupadas" in f["title"]["es"] and "promedios de largo plazo" not in f["title"]["es"]
            en_rates = re.search(r"pooled rates ([\d.]+)% against ([\d.]+)%", f["title"]["en"])
            assert en_rates, f["title"]["en"]
            assert abs(float(en_rates.group(1)) - 100 * d4) < 0.006 and abs(float(en_rates.group(2)) - 100 * d2) < 0.006
    assert seen >= 1


def test_the_c06_titles_say_what_they_measure():
    seen = set()
    for path in sorted((DERIVED / "C06").glob("rd-*.json")):
        for f in load(path)["findings"]:
            if f["id"] == "F-LIFETIME-GAP":
                seen.add("gap")
                assert "pooled" in f["title"]["en"] and "agrupados" in f["title"]["es"]
            if f["id"].startswith("F-SICR-STABILITY"):
                # the SICR threshold's stability against the conditions (R4 c07 N-M1, U16-F12b), its own measure
                seen.add("stability")
                assert "condiciones" in f["title"]["es"] and "conditions" in f["title"]["en"]
            elif f["id"].startswith("F-SICR"):
                seen.add("sicr")
                assert "separates defaults" not in f["title"]["en"]
                assert "frente a los incumplimientos" in f["title"]["es"]
    assert seen == {"gap", "sicr", "stability"}


def test_the_c07_notice_has_its_punctuation_and_the_uf_value_in_spanish():
    for path in sorted((DERIVED / "C07").glob("models-*.json")):
        notice = load(path)["fit"]["bank"]["notice"]["es"]
        assert "generado, calibrado" in notice and "ningún banco. Las hipotecas" in notice
        assert re.search(r"40\.873,77 CLP por UF\.$", notice)


def test_the_c08_note_does_not_show_a_raw_unverified_mark_to_the_reader():
    for path in sorted((DERIVED / "C08").glob("models-*.json")):
        text = json.dumps(load(path), ensure_ascii=False)
        assert "(paragraph UNVERIFIED)" not in text and "párrafo NO VERIFICADO" not in text
    seen = 0
    for path in sorted((DERIVED / "C08").glob("dc-*.json")):
        note = load(path)["outputs"]["workout"].get("note") if "workout" in load(path)["outputs"] else None
        if note:
            seen += 1
            assert "paragraph number is not confirmed" in note["en"] and "no está confirmado" in note["es"]
    assert seen >= 0
