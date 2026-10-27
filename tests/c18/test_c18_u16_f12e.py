"""U16-F12e (fix round 5, R4 c22 and c23): the C18 producer texts name no code function and no source variable string in reader prose
(the marginal interpolation rule, the rate the NII follows), the Spanish credit marginal keeps the clause the English states, no text says
"bake", the t copula's parameter is written as its symbol, and the reverse-stress finding gives both factors their unit and writes a
small probability with an upper-case exponent, as the views do."""
from __future__ import annotations

from pipeline.cases.c18 import documents_more as DM
from pipeline.cases.c18 import marginals, models, nii
from pipeline.cases.c18.spanish import SPANISH

NGFS = "Central bank Intervention rate (policy interest rate) ; %(combined)"


def test_c22_b4_c23_b2_the_interpolation_rule_is_said_in_words() -> None:
    rule = models.MARGINAL_INTERPOLATION
    assert "np.interp" not in rule
    assert rule.startswith("linear interpolation on the Hazen positions (i - 0.5) / n")


def test_c23_b1_the_nii_sentence_names_the_rate_never_the_source_variable() -> None:
    t = nii.rate_statement(NGFS, "prime_rate")
    for lang in ("en", "es"):
        assert "; %(combined)" not in t[lang], t[lang]
        assert "Intervention rate (policy interest rate)" not in t[lang], t[lang]
        assert "))" not in t[lang], t[lang]
    assert "the central bank intervention rate, the policy rate" in t["en"]
    assert "la tasa de intervención del banco central, la tasa de política monetaria" in t["es"]
    fed = nii.rate_statement("Prime rate", "prime_rate")
    assert "(the prime rate)" in fed["en"] and "(la tasa preferencial)" in fed["es"]


def test_c22_m1_the_spanish_credit_marginal_keeps_the_clause_of_the_english() -> None:
    g = {"low": {"names": 400, "var": 1.0, "es": 2.0}, "high": {"names": 1600, "var": 1.0, "es": 2.0}, "diff_var": 0.0, "diff_es": 0.0,
         "se_var": 1.0, "se_es": 1.0, "exceeds_two_se": False, "names_used": 400}
    t = marginals.granularity_text(g)
    assert "name by name" in t["en"]
    assert "nombre por nombre" in t["es"]


def test_c22_m4_no_text_says_bake_and_the_t_copula_parameter_is_its_symbol() -> None:
    for en, es in SPANISH.items():
        assert "bake" not in en.lower(), en
        assert "hornea" not in es.lower(), es
        assert "several nu" not in en and "varios nu" not in es, en


def test_c23_m11_the_reverse_finding_gives_both_factors_their_unit() -> None:
    t = DM.reverse_finding_title(["real GDP growth", "unemployment rate"], ["crecimiento del PIB real", "tasa de desempleo"], [-2.58, 12.42], 4.2, 2.4e-15)
    assert "by -2.58 points and the unemployment rate by +12.42 points" in t["en"], t["en"]
    assert "2.4E-15" in t["en"] and "e-15" not in t["en"]
    assert "en -2,58 puntos y la tasa de desempleo en +12,42 puntos" in t["es"], t["es"]
    assert "2,4E-15" in t["es"]
