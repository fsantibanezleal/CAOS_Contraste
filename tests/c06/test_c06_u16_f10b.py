"""U16-F10b (fix round 4, the R3 capture review of C06, batch c07 B6): the Spanish finding titles carry no English word ("hazard",
"proxy", "backtest") and name the loss given default as the interface does (LGD, not "PDI"), on the producer's function."""
from __future__ import annotations

import re

import numpy as np

from pipeline.cases.c06.build import findings

ENGLISH = re.compile(r"\b(?:hazard|proxy|backtest|PDI)\b", re.IGNORECASE)


def _row(test_id: str, light: str, *, metric: float | None = None, p: float | None = None, segment: str | None = None) -> dict:
    return {"test_id": test_id, "model_id": "L1-dth", "segment": segment, "light": light, "metric": metric, "p_value": p, "statistic": None}


def _all() -> list[dict]:
    tests = [_row("ifrs9.lifetime_pd_backtest", "red", metric=0.0412, segment="all")]
    # the severely adverse ECL below the baseline raises F-SCENARIO-ORDER; 1,234 accounts outside the lifetime backtest raise F-SHORT-LIFE
    return findings(tests, None, np.array([2.0, 1.5, 1.0]), {}, 1234)


def test_b6_no_english_word_in_a_spanish_finding_title() -> None:
    out = _all()
    ids = {f["id"] for f in out}
    assert {"F-LIFETIME-GAP", "F-SCENARIO-ORDER", "F-LGD-PROXY", "F-PREPAYMENT", "F-SHORT-LIFE"} <= ids, ids
    for f in out:
        assert not ENGLISH.search(f["title"]["es"]), (f["id"], f["title"]["es"])


def test_b6_the_spanish_names_the_rung_and_the_lgd_as_the_interface_does() -> None:
    by = {f["id"]: f["title"] for f in _all()}
    assert "peldaño de riesgo en tiempo discreto" in by["F-LIFETIME-GAP"]["es"]
    assert "peldaño de riesgo en tiempo discreto" in by["F-SCENARIO-ORDER"]["es"]
    assert by["F-LGD-PROXY"]["es"].startswith("La LGD es una aproximación de la severidad del castigo")
    assert "riesgo de incumplimiento por causa" in by["F-PREPAYMENT"]["es"]
    assert "prueba retrospectiva de vida completa" in by["F-SHORT-LIFE"]["es"]
    assert "1.234 cuentas" in by["F-SHORT-LIFE"]["es"]


def test_the_english_titles_keep_their_wording() -> None:
    by = {f["id"]: f["title"]["en"] for f in _all()}
    assert by["F-LIFETIME-GAP"].startswith("The lifetime PD of the hazard rung misses the observed cumulative default by up to 4.1 points")
    assert by["F-LGD-PROXY"].startswith("LGD is a charge-off severity proxy with an upward bias")
