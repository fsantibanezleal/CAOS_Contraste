"""U16-F10c (R3 batch c09, C08): the producer texts a Spanish view prints say "aproximación", never the English "proxy"; no
internal decision id is printed in reader text (the 2026-10-27 ruling on raw ids); a finding on one uncovered cohort names
"the cohort", not "the cohorts". Tested on the producer's functions and constants, never by re-baking."""
from __future__ import annotations

import re

import pytest

from pipeline.cases.c08 import build as bd
from pipeline.cases.c08 import downturn, variant

PROXY = re.compile(r"\bproxy\b", re.I)
DECISION = re.compile(r"\(decisi[oó]n [A-Z]\d+\)")


def _texts():
    proxy = bd.lgd_proxy_block()
    return {
        "notice": bd.NOTICE,
        "definition": proxy["definition"],
        "bias": proxy["bias_statement"],
        "workout note": bd.workout_block()["note"],
        "approach": downturn.APPROACH,
    }


@pytest.mark.parametrize("name", ["notice", "definition", "bias", "workout note", "approach"])
def test_the_spanish_texts_say_aproximacion_not_proxy(name):
    text = _texts()[name]
    assert not PROXY.search(text["es"]), text["es"]


def test_no_internal_decision_id_in_the_bias_statement():
    bias = bd.lgd_proxy_block()["bias_statement"]
    for lang in ("en", "es"):
        assert not DECISION.search(bias[lang]), bias[lang]
    assert bias["en"].endswith("The stated direction is the denominator effect.")
    assert bias["es"].endswith("La dirección declarada es el efecto del denominador.")


class _Down:
    def __init__(self, ids):
        self.rows = [{"cohort_id": i, "covered": False, "shortfall": 0.0014} for i in ids]


def test_one_uncovered_cohort_is_named_in_the_singular():
    # U16-F12c (R4 c10 n3): the title states the shortfall (and the coverage test, when one is given)
    f = variant._findings({"light": "green", "metric": None}, "L1-ols", "all", _Down(["2009-10"]), [])[0]
    assert f["title"]["en"] == "The downturn LGD falls short of the realised loss of the cohort 2009-10 by 0.14 points"
    assert f["title"]["es"] == "La LGD de recesión queda bajo la pérdida realizada de la cohorte 2009-10 por 0,14 puntos"


def test_two_uncovered_cohorts_keep_the_plural():
    f = variant._findings({"light": "green", "metric": None}, "L1-ols", "all", _Down(["2007-08", "2009-10"]), [])[0]
    assert "of the cohorts 2007-08 and 2009-10" in f["title"]["en"]
    assert "de las cohortes 2007-08 y 2009-10" in f["title"]["es"]


def test_the_calibration_finding_says_aproximada_in_spanish():
    f = variant._findings({"light": "red", "metric": 0.033}, "L2-fractional-logit", "all", _Down([]), [])[0]
    assert not PROXY.search(f["title"]["es"]), f["title"]["es"]
    assert "la LGD aproximada realizada de la cohorte en 3,3 puntos" in f["title"]["es"]
