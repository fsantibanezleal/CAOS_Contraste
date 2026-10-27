"""U16-F12b (fix round 5, the R4 capture review of C06, batches c07 N-M1 and c08 N1, N2, the ruling 4 of 2026-10-27): every red test
row of a C06 document is cited by an open finding of the case, on the producer's function: the SICR threshold stability test has a
finding of its own, and the lifetime gap cites every red cohort row of the hazard rung, not only the pooled one."""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pytest

from pipeline.cases.c06.build import findings

ROOT = Path(__file__).resolve().parents[2]
DERIVED = ROOT / "data" / "derived" / "C06"
ENGLISH = re.compile(r"\b(?:hazard|threshold|loosen\w*|periods?|backtest|times)\b", re.IGNORECASE)


def _key(tr: dict) -> str:
    k = tr["test_id"]
    if tr.get("model_id"):
        k += "@" + tr["model_id"]
        if tr.get("segment"):
            k += "@" + tr["segment"]
    return k


def _row(test_id: str, light: str, *, metric: float | None = None, segment: str | None = None, extras: dict | None = None) -> dict:
    return {"test_id": test_id, "model_id": "L1-dth", "segment": segment, "light": light, "metric": metric, "p_value": None,
            "statistic": None, "extras": extras or {}}


def _stability(light: str, count: int, periods: int = 2) -> dict:
    return _row("ifrs9.sicr_threshold_stability", light, metric=float(count), extras={"loosening_periods": list(range(1, count + 1)), "periods": periods})


def _run(tests: list[dict], adverse_below_base: bool = False) -> list[dict]:
    """The producer's findings; ``adverse_below_base`` replays a date whose severely adverse ECL is below the baseline one."""
    return findings(tests, None, np.array([2.0, 1.5, 1.0] if adverse_below_base else [1.0, 1.5, 2.0]), {}, 0)


def test_n1_a_red_sicr_threshold_stability_row_has_an_open_s2_finding_that_cites_it() -> None:
    row = _stability("red", 1)
    by = {f["id"]: f for f in _run([row])}
    f = by.get("F-SICR-STABILITY-red")
    assert f is not None, sorted(by)
    assert (f["severity"], f["status"], f["evidence"]) == ("S2", "open", [_key(row)])
    assert f["title"]["en"] == ("The SICR threshold against worsening conditions: red (the threshold loosened while conditions worsened "
                                "in 1 of the 2 reporting periods)")
    assert f["title"]["es"] == ("El umbral de SICR frente al empeoramiento de las condiciones: rojo (el umbral se relajó mientras las "
                                "condiciones empeoraban en 1 de los 2 períodos de reporte)")
    assert not ENGLISH.search(f["title"]["es"]), f["title"]["es"]


def test_n1_an_amber_row_is_s3_a_green_row_raises_none_and_a_row_not_evaluated_is_s4() -> None:
    assert {f["id"]: f["severity"] for f in _run([_stability("amber", 1, periods=4)])}["F-SICR-STABILITY-amber"] == "S3"
    assert not [f for f in _run([_stability("green", 0)]) if f["id"].startswith("F-SICR-STABILITY")]
    ne = _row("ifrs9.sicr_threshold_stability", "not_evaluated")
    got = {f["id"]: f for f in _run([ne])}["F-SICR-STABILITY-not_evaluated"]
    assert (got["severity"], got["evidence"]) == ("S4", [_key(ne)])
    assert got["title"]["es"].endswith(": no evaluada")


def test_n2_the_lifetime_gap_cites_every_red_cohort_row_of_the_hazard_rung() -> None:
    pooled = _row("ifrs9.lifetime_pd_backtest", "red", metric=0.194, segment="all")
    cohorts = [_row("ifrs9.lifetime_pd_backtest", "red", metric=0.2146, segment="2018"),
               _row("ifrs9.lifetime_pd_backtest", "red", metric=0.1661, segment="2020")]
    green = _row("ifrs9.lifetime_pd_backtest", "green", metric=0.01, segment="2015")
    other = {**_row("ifrs9.lifetime_pd_backtest", "red", metric=0.3, segment="2018"), "model_id": "L0-km"}
    gap = {f["id"]: f for f in _run([pooled, *cohorts, green, other])}["F-LIFETIME-GAP"]
    assert gap["evidence"] == [_key(pooled), *(_key(c) for c in cohorts)]
    # the title keeps its pooled figure and wording (the evidence lines carry the cohorts)
    assert gap["title"]["en"].startswith("The lifetime PD of the hazard rung misses the observed cumulative default by up to 19.4 points")


def test_n_m2_the_sicr_effectiveness_ratio_keeps_four_significant_digits_so_an_amber_never_reads_as_the_green_bar() -> None:
    f = [x for x in _run([_row("ifrs9.sicr_effectiveness", "amber", metric=1.9951)]) if x["id"].startswith("F-SICR-")][0]
    assert "1.995 times" in f["title"]["en"], f["title"]["en"]
    assert "1,995 veces" in f["title"]["es"], f["title"]["es"]


@pytest.mark.parametrize("path", sorted(DERIVED.glob("rd-*.json")), ids=lambda p: p.stem)
def test_ruling_4_every_red_row_of_a_committed_document_is_cited_by_an_open_finding_of_the_producer(path: Path) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    tests = doc["tests"]
    order = any(f["id"] == "F-SCENARIO-ORDER" for f in doc["findings"])
    cited = {k for f in _run(tests, order) if f["status"] == "open" for k in f["evidence"]}
    red = [_key(t) for t in tests if t["light"] == "red"]
    assert [k for k in red if k not in cited] == []


def test_n5_the_roll_forward_spells_remeasurement_one_way() -> None:
    from pipeline.cases.c06 import rollforward

    assert rollforward.LABELS["remeasurement"] == ("Remeasurement", "Remedición")
