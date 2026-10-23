"""U16-F6b (the second fix round, the producers U16-F6 left): the Spanish texts the producers of C01, C04, C05 and C07 write
carry the shell's es-CL number forms (``pipeline.core.text``: a decimal comma, a thousands point, a no-break space before %),
and their English texts keep their wording.

The committed documents are checked by ``tests/test_u16_f6_documents.py``; these tests check the producers themselves, so a
text that a bake has not reached yet (a variant's regime, a label of a family that has no finding) is held too.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data-pipeline"))
from f3_spanish_text import leaks  # noqa: E402
from pipeline.cases import c01_retail_pd, c04_families, c04_published, c04_transitions, c05_ldp_calibration  # noqa: E402
from pipeline.cases.c07 import book  # noqa: E402

NBSP = " "
GLUED = re.compile(r"\d%")


def test_c04_percent_writes_the_english_unchanged_and_the_spanish_as_the_shell():
    assert c04_transitions._pct(0.012345) == ("1.23%", f"1,23{NBSP}%")
    assert c04_transitions._pct(0.98, 0) == ("98%", f"98{NBSP}%")
    assert c04_transitions._pct(12.3456, 1) == ("1234.6%", f"1.234,6{NBSP}%")


def test_c04_signed_percent_keeps_its_sign_in_spanish():
    assert c04_transitions._signed_pct(-0.34) == f"-34{NBSP}%"
    assert c04_transitions._signed_pct(0.12) == f"+12{NBSP}%"
    assert c04_transitions._signed_pct(-0.001) == f"+0{NBSP}%"  # no negative zero, as the shell writes it


def test_c04_number_and_count_in_spanish():
    assert c04_transitions._num(0.1169, 6) == ("0.116900", "0,116900")
    assert c04_transitions._num(1234.5, 1) == ("1234.5", "1.234,5")
    assert c04_transitions._miles(2000) == "2.000"


def test_c05_spanish_number_is_the_shell_form():
    assert c05_ldp_calibration._es(12.345, 1) == "12,3"
    assert c05_ldp_calibration._es(1234.5, 1) == "1.234,5"


def test_c01_variant_texts_have_no_glued_percent_in_spanish():
    for v in c01_retail_pd.VARIANTS:
        for key in ("title", "short", "regime"):
            assert not GLUED.search(v[key]["es"]), (v["id"], key, v[key]["es"])
    noise = next(v for v in c01_retail_pd.VARIANTS if v["id"] == "label-noise")
    assert noise["title"] == {"en": "Label noise 5%", "es": f"Ruido de etiqueta 5{NBSP}%"}


@pytest.mark.parametrize("family", ["momentum", "cycle", "withdrawals", "thin"])
def test_c04_ladder_names_carry_no_english_number_form(family):
    name = c04_families.LADDERS[family]["name"]
    assert leaks(name["en"], name["es"]) == []


def test_c04_ladder_name_of_withdrawals_keeps_its_english():
    name = c04_families.LADDERS["withdrawals"]["name"]
    assert name["en"] == "Informative withdrawal k: 6% a year, times 1 + k in the year before default"
    assert f"6{NBSP}% al año" in name["es"]


def test_c04_engelmann_note_carries_no_english_number_form():
    note = c04_published.ENTRY_ROUNDING["W hat"]
    assert leaks(note["en"], note["es"]) == []
    assert "1.0945% against the printed 1.093%" in note["en"]


def test_c07_segment_labels_carry_no_english_number_form():
    seen = 0
    for seg in book.SEGMENTS:
        for key in ("label", "bde_label"):
            if key in seg:
                seen += 1
                assert leaks(seg[key]["en"], seg[key]["es"]) == [], seg[key]
    assert seen >= 4
