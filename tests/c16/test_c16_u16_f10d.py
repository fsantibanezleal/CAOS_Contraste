"""U16-F10d (fix round 4, R3 c17): the C16 producer texts, read on the documents the bake writes from the committed samples. No
bilingual text carries a coordination tag of the unit sizing ("(Q13)", "(A3)", "(Q6, A4)", "decision Q5") or a brief id ("U11-S"),
no Spanish text carries an English word of the 2026-10-27 ruling ("roll-off", "hazard", "test de estrés"), and the Spanish says what
the English says (M1: the Spanish of fourteen statements dropped the mapping, the rates and the reasons); B2, B5, M1, n2, n4, n7."""
from __future__ import annotations

import re

from pipeline.cases.c16 import assumptions

TAG = re.compile(r"\((?:decision |decisión )?[QAX]\d+(?:, ?[QAX]\d+)*\)|\b(?:decision|decisión) [QAX]\d+\b|\(Q\d+,|\bU\d+-[A-Z]\b")
RULED_ES = re.compile(r"\b(roll-off|hazard|backtest\w*|test de estrés|proxy|shock|offline|golden)\b", re.IGNORECASE)
ENGLISH_IN_ES = re.compile(r"\b(the|of|and|stress|rate|with|from)\b")
#: the pairs whose Spanish is naturally shorter than its English (a label of a few words), reviewed one by one
SHORT_OK = {
    "Cash and balances due from depository institutions",
    "Deposits, large domestically chartered banks",
    "Deposits, small domestically chartered banks",
}


def _pairs(o, p=""):
    if isinstance(o, dict):
        if set(o) == {"en", "es"} and all(isinstance(v, str) for v in o.values()):
            yield p, o
        for k, v in o.items():
            yield from _pairs(v, f"{p}/{k}")
    elif isinstance(o, list):
        for v in o:
            yield from _pairs(v, p + "[]")


def _all_pairs(built):
    docs = [*built.variants.values(), built.models, built.reverse]
    seen: dict[str, tuple[str, dict]] = {}
    for d in docs:
        for p, o in _pairs(d):
            seen.setdefault(o["en"], (p, o))
    return list(seen.values())


def test_b5_q1_no_bilingual_text_carries_a_coordination_tag_or_a_brief_id(built) -> None:
    found = [(p, lang, m.group(0)) for p, o in _all_pairs(built) for lang in ("en", "es") for m in TAG.finditer(o[lang])]
    assert found == []


def test_b2_no_spanish_text_carries_an_english_word_of_the_ruling(built) -> None:
    found = [(p, m.group(0), o["es"][:90]) for p, o in _all_pairs(built) for m in RULED_ES.finditer(o["es"])]
    assert found == []
    english = [(p, o["es"][:90]) for p, o in _all_pairs(built) if len(ENGLISH_IN_ES.findall(o["es"])) >= 2]
    assert english == []


def test_m1_the_spanish_says_what_the_english_says(built) -> None:
    """M1: a Spanish text under 80 percent of its English (over 40 characters) dropped content; the reviewed short labels stay."""
    short = [(p, len(o["en"]), len(o["es"]), o["en"][:70]) for p, o in _all_pairs(built)
             if len(o["en"]) > 40 and len(o["es"]) < 0.8 * len(o["en"]) and o["en"] not in SHORT_OK]
    assert short == []


def test_the_deposit_mapping_basis_names_no_brief_and_states_the_band_in_both_languages() -> None:
    basis = assumptions.conventions()["deposit_category_mapping"]["basis"]
    assert basis["en"] == ("The call report carries no customer type: the mapping is an assumption of the case design, from dossier 05 E.5 "
                           "and 01 G.1; the band is the dossier's plausible classes. A convention, never a regulatory classification.")
    assert basis["es"] == ("El reporte de llamada no trae tipo de cliente: el mapeo es un supuesto del diseño del caso, a partir del dossier "
                           "05 E.5 y 01 G.1; la banda son las clases plausibles del dossier. Una convención, nunca una clasificación "
                           "regulatoria.")


def test_n7_the_tolerance_basis_says_golden_value() -> None:
    basis = assumptions.conventions()["list_compounding_tolerance"]["basis"]
    assert basis["en"].startswith("A golden value stated to six decimals")
