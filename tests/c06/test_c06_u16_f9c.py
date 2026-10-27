"""U16-F9c (fix round 3, R2b c07 minors): the C06 finding titles name the figure they quote and read it whole; the scenario-order
finding says what the test it cites measures (it reads the non-linearity of the ECL, not the order of the scenarios)."""
from __future__ import annotations

import numpy as np

from pipeline.cases.c06.build import findings


def _row(test_id: str, light: str, *, metric: float | None = None, p: float | None = None) -> dict:
    return {"test_id": test_id, "model_id": "L1-dth", "segment": None, "light": light, "metric": metric, "p_value": p, "statistic": None}


def _titles(tests: list[dict], ecl: list[float]) -> dict[str, dict[str, str]]:
    return {f["id"]: f["title"] for f in findings(tests, None, np.array(ecl), {}, 0)}


def test_a_p_value_of_zero_reads_below_the_smallest_shown() -> None:
    """'(p 0)' read as a p-value of exactly zero; the engine returns 0.0 for a chi-square far in the tail."""
    t = _titles([_row("ifrs9.stage_migration_backtest", "red", p=0.0)], [1.0, 2.0])["F-MIGRATION-red"]
    assert "(p 0)" not in t["en"] and "(p 0)" not in t["es"]
    assert "p below 0.0001" in t["en"]
    assert "p menor que 0,0001" in t["es"]


def test_a_metric_is_named_by_what_it_measures() -> None:
    """'(metric 2)' and '(métrica 0,0713)' said nothing of the quantity: the Stage 2 over Stage 1 default rate, realised over ECL."""
    got = _titles([_row("ifrs9.sicr_effectiveness", "amber", metric=1.99507527), _row("ifrs9.ecl_backtest", "red", metric=0.07126186)], [1.0, 2.0])
    sicr, ecl = got["F-SICR-amber"], got["F-ECL-BACKTEST-red"]
    for t in (sicr, ecl):
        assert "(metric " not in t["en"] and "(métrica " not in t["es"], t
    # four significant digits since U16-R4 c07 N-m2 (an amber ratio of 1.9951 read as the green bar of 2)
    assert "Stage 2 default rate 1.995 times the Stage 1 one" in sicr["en"]
    assert "tasa de incumplimiento de la Etapa 2 de 1,995 veces la de la Etapa 1" in sicr["es"]
    assert "realised losses 0.07126 times the ECL" in ecl["en"]
    assert "pérdidas realizadas de 0,07126 veces la PCE" in ecl["es"]


def test_a_test_not_evaluated_is_said_in_words() -> None:
    """'not_evaluated (not evaluated)' printed the light's id beside its words (the raw-id scan, rd-2019-12)."""
    t = _titles([_row("ifrs9.sicr_effectiveness", "not_evaluated")], [1.0, 2.0])["F-SICR-not_evaluated"]
    assert "not_evaluated" not in t["en"] and "not_evaluated" not in t["es"]
    assert t["en"].endswith(": not evaluated")


def test_the_scenario_order_finding_says_what_its_test_reads() -> None:
    """R2b c07: the finding cites ifrs9.scenario_sensitivity, green, without saying that test reads the non-linearity index."""
    t = _titles([], [2.0, 1.5, 1.0])["F-SCENARIO-ORDER"]
    assert "non-linearity" in t["en"] and "not the order of the scenarios" in t["en"]
    assert "no linealidad" in t["es"] and "no el orden de los escenarios" in t["es"]
