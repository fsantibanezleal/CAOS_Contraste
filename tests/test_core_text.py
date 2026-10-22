"""pipeline.core.text writes numbers and light names as the web shell does (en-US and es-CL, Intl.NumberFormat)."""
from __future__ import annotations

import pytest

from pipeline.core import text as t


@pytest.mark.parametrize(("x", "d", "en", "es"), [
    (1234.5, 1, "1,234.5", "1.234,5"),
    (49856, 0, "49,856", "49.856"),
    (1120, 0, "1,120", "1.120"),          # es-CL groups from four digits, as the shell does
    (4500000, 0, "4,500,000", "4.500.000"),
    (3.3, 1, "3.3", "3,3"),
    (0.0694, 4, "0.0694", "0,0694"),
    (-2.5, 1, "-2.5", "-2,5"),
    (-0.04, 1, "0.0", "0,0"),             # no negative zero
    (7, 2, "7.00", "7,00"),
])
def test_numbers_in_both_languages(x, d, en, es):
    assert t.number(x, d, lang="en") == en
    assert t.number(x, d, lang="es") == es
    assert t.bi_number(x, d) == {"en": en, "es": es}


def test_a_year_is_written_without_grouping():
    assert t.number(2009, 0, lang="en", grouping=False) == "2009"
    assert t.number(2009, 0, lang="es", grouping=False) == "2009"
    assert t.number(2009, 0, lang="es") == "2.009"


def test_percent_takes_the_no_break_space_of_the_shell():
    assert t.percent(0.139, 1, lang="en") == "13.9 %"
    assert t.percent(0.139, 1, lang="es") == "13,9 %"
    assert t.bi_percent(0.96, 1) == {"en": "96.0 %", "es": "96,0 %"}


def test_light_words():
    assert [t.light(x, "es") for x in ("green", "amber", "red", "not_evaluated")] == ["verde", "ámbar", "rojo", "no evaluada"]
    assert t.light("amber", "en") == "amber"
    with pytest.raises(ValueError):
        t.light("purple", "es")


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), True, "1"])
def test_refuses_what_is_not_a_finite_number(bad):
    with pytest.raises(ValueError):
        t.number(bad, 1, lang="es")


def test_refuses_an_unknown_language():
    with pytest.raises(ValueError):
        t.number(1, 0, lang="fr")
