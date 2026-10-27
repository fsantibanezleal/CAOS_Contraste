"""U16-F12e (fix round 5, R4 c26 and c27): the C22 producer texts follow their committed numbers.

c26 B1 the F-PSI-RULE title states the 0.10 rule's false-alarm rate and the benchmark's rate against its bound, never that the benchmark
"controls the error" when its rate exceeds its bound; c26 n3 the decay and migration titles state their rates; c27 m1 a title rounds half
up as the views do; c27 m5 an engine study text groups its thousands in English and gives a Spanish percent its no-break space; c27 m13
a study label after a test name that ends in a parenthesis does not nest a second one; c27 n4 the convergence impact label says whether
this run is above its bound."""
from __future__ import annotations

from types import SimpleNamespace

import pipeline.cases.c22_studies as studies
import pipeline.cases.c22_validator as validator

NBSP = " "


def test_c26_b1_the_psi_rule_title_follows_its_numbers() -> None:
    # null.json: the 0.10 rule fires in 84.975 % of the samples; the benchmark rejects 6.975 % at 5 % against a bound of 6.06 %
    t = validator.psi_rule_title(0.84975, 0.06975, False)
    assert "controls the error" not in t["en"] and "controla el error" not in t["es"]
    assert f"85.0{NBSP}%" in t["en"] and f"85,0{NBSP}%" in t["es"]
    assert f"7.0{NBSP}%" in t["en"] and f"7,0{NBSP}%" in t["es"]
    assert "above its bound" in t["en"] and "sobre su cota" in t["es"]
    within = validator.psi_rule_title(0.84975, 0.05, True)
    assert "within its bound" in within["en"] and "dentro de su cota" in within["es"]


def test_c26_n3_the_decay_and_migration_titles_state_their_rates() -> None:
    d = validator.decay_title(0.2545)
    assert "rarely" not in d["en"] and "rara vez" not in d["es"]
    assert f"25.5{NBSP}%" in d["en"] and f"25,5{NBSP}%" in d["es"]
    m = validator.migration_title(0.555)
    assert "half the time" not in m["en"] and "la mitad de las veces" not in m["es"]
    assert f"44.5{NBSP}%" in m["en"] and f"44,5{NBSP}%" in m["es"]


def test_c27_m1_a_title_rounds_half_up_as_the_views_do() -> None:
    assert validator._pct(0.01325, 2) == {"en": f"1.33{NBSP}%", "es": f"1,33{NBSP}%"}
    assert validator._pct(0.04725, 2) == {"en": f"4.73{NBSP}%", "es": f"4,73{NBSP}%"}


def test_c27_m5_an_engine_study_text_groups_its_thousands_and_spaces_a_spanish_percent() -> None:
    s = SimpleNamespace(label="2000 days at 10%", null_text="independent hits at 5%", alternative_text="1500 days at 5%")
    t = studies.study_texts(s, 0)
    assert t["label"] == {"en": "2,000 days at 10%", "es": f"2.000 días al 10{NBSP}%"}
    assert t["alternative"]["en"] == "1,500 days at 5%"
    assert t["null"]["es"] == f"excedencias independientes al 5{NBSP}%"


def test_c27_m13_no_nested_parenthesis_after_a_test_name() -> None:
    s = SimpleNamespace(label="60 years at the 95% level", null_text=None, alternative_text="60 years at the 95% level")
    t = studies.row_label("portfolio.tail_backtest", s, 0, 2)
    assert t["en"] == "Tail back-test (LHP quantile), 60 years at the 95% level"
    assert ") (" not in t["es"]


def test_c27_n4_the_convergence_label_says_whether_this_run_is_above_its_bound() -> None:
    t = validator.mc_convergence_label({"exceeds": False, "bound": 0.01486})
    assert "documented excess)" not in t["en"]
    assert "within its bound" in t["en"] and "dentro de su cota" in t["es"]
