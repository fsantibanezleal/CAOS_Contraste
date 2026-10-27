"""U16-F10e (fix round 4, the third capture review R3, batch c19): the C18 producer texts.

B2 the reverse-stress finding no longer says the loss-only baseline ends below the stack (the baseline ends at 9.42 % above 9.06 %);
B3 no English word in the Spanish (proxy, Tier 1, back-cast, Prime rate); B4 the granularity sentence writes its numbers in the
shell's forms with their unit; B5 no configuration key ``p2r`` in prose; M3 the finding on the non-credit losses says IRRBB is out of
the capital path; the rulings of 2026-10-27: no plan decision tag and no engine function name in reader text; minors m2 (a Spanish
percent with its no-break space) and m3 (the singular of one path variable)."""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pipeline.cases.c18 as pkg
from pipeline.cases.c18 import capital, documents, documents_more, marginals, nii
from pipeline.cases.c18 import params as P
from pipeline.cases.c18.spanish import SPANISH

NBSP = " "
ENGLISH_IN_SPANISH = re.compile(r"\b(proxy|Proxy|Tier 1|back-cast|Prime rate|United States rows|full allocation)\b")
DECISION_TAG = re.compile(r"\b(decisions?|decisión|decisiones) [A-Z]\d+|\((?:[A-BD-Z]\d+(?:, )?)+\)|\b[A-Z]\d+ of the U\d+|\bU\d+ sizing")
ENGINE_FUNCTION = re.compile(r"\b(irrbb\.eve_nii\.delta_nii|oprisk\.aggregate|shocks\.apply_floor)\b")


def _reader_strings() -> list[str]:
    """Every string a C18 producer passes to ``T`` / ``P.text`` (the texts a reader sees), with the Spanish table's entries."""
    out: list[str] = []
    for path in Path(pkg.__file__).parent.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and ((isinstance(node.func, ast.Name) and node.func.id in {"T", "named"})
                                               or (isinstance(node.func, ast.Attribute) and node.func.attr == "text")):
                for arg in node.args:
                    for sub in ast.walk(arg):
                        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                            out.append(sub.value)
    out += list(SPANISH) + list(SPANISH.values())
    return out


def test_b2_the_reverse_finding_says_nothing_the_baseline_contradicts() -> None:
    t = documents_more.reverse_finding_title(["real GDP growth", "unemployment rate"], ["crecimiento del PIB real", "tasa de desempleo"],
                                             (-1.131, 8.205), 8.205, 2.4e-15)
    assert "already ends below" not in t["en"] and "ya termina bajo" not in t["es"]
    assert "shifts real GDP growth by -1.13 and the unemployment rate by +8.21 points" in t["en"], t["en"]
    assert "en -1,13 y la tasa de desempleo en +8,21 puntos" in t["es"], t["es"]
    # m4: a tail probability under 0.1 percent keeps its exponent
    assert "(tail probability 2.4e-15)" in t["en"] and "(probabilidad de cola 2,4e-15)" in t["es"]


def test_b3_no_english_word_in_the_spanish_producer_texts() -> None:
    texts = [capital.CAPITAL_BASIS["es"], documents.BACKCAST_SENTENCE["es"], nii.rate_statement("Prime rate", "prime_rate")["es"],
             nii.rate_statement("10-year Treasury rate", "treasury_10y")["es"]]
    for t in texts:
        assert not ENGLISH_IN_SPANISH.search(t), t
    assert "retroproyección" in documents.BACKCAST_SENTENCE["es"]
    assert "tasa preferencial" in nii.rate_statement("Prime rate", "prime_rate")["es"]
    assert "capital de nivel 1" in capital.CAPITAL_BASIS["es"] and "aproximación" in capital.CAPITAL_BASIS["es"]
    # the English keeps its words
    assert "Tier 1 proxy" in capital.CAPITAL_BASIS["en"]


def test_b4_the_granularity_sentence_writes_numbers_the_shell_way_with_their_unit() -> None:
    lo = {"names": 400, "var": 298226.53, "es": 346948.99}
    hi = {"names": 1600, "var": 297003.6, "es": 343790.7}
    g = {"low": lo, "high": hi, "diff_var": hi["var"] - lo["var"], "diff_es": hi["es"] - lo["es"], "se_var": 2262.4, "se_es": 2863.1,
         "exceeds_two_se": False, "names_used": 400}
    t = marginals.granularity_text(g)
    assert "1.600 nombres" in t["es"] and "1,600" not in t["es"], t["es"]
    assert "VaR 298.227 y 297.004" in t["es"] and "(diferencia -1.223)" in t["es"], t["es"]
    assert "millones de CLP" in t["es"] and "CLP millions" in t["en"]
    assert "1,600 names" in t["en"] and "VaR 298,227 and 297,004" in t["en"]


def test_b5_no_configuration_key_in_prose() -> None:
    for s in _reader_strings():
        assert not re.search(r"\bp2r\b", s), s


def test_m3_the_non_credit_finding_says_irrbb_is_out_of_the_capital_path() -> None:
    t = documents.NON_CREDIT_FINDING
    assert "IRRBB" in t["en"] and "market, IRRBB and operational losses are held at their expected loss" not in t["en"]
    assert "outside the capital path" in t["en"] and "fuera de la trayectoria de capital" in t["es"]
    desc = documents_more.REVERSE_LOSS_DESCRIPTION
    assert "the other risks carry their expected loss" not in desc["en"]
    assert "market and operational risks carry their expected loss" in desc["en"]


def test_ruling_no_decision_tag_and_no_engine_function_in_reader_text() -> None:
    for s in _reader_strings():
        assert not DECISION_TAG.search(s), s
        assert not ENGINE_FUNCTION.search(s), s


def test_m2_a_spanish_percent_has_its_no_break_space() -> None:
    assert P.es(0.0736, ".2%") == f"7,36{NBSP}%"
    assert P.es(1234.5, ",.1f") == "1.234,5"


def test_m3_one_path_variable_is_singular() -> None:
    t = documents.milder_title(1)
    assert t["en"].startswith("1 path variable of this scenario is milder"), t["en"]
    assert t["es"].startswith("1 variable de trayectoria de este escenario es más suave"), t["es"]
    t2 = documents.milder_title(2)
    assert t2["en"].startswith("2 path variables of this scenario are milder")
