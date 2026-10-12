"""CT-711: the six scenarios and the basis of every magnitude."""
from __future__ import annotations

import pytest
from pipeline.cases.c07 import scenarios as sc


def test_every_scenario_magnitude_has_a_source_or_an_assumption_label() -> None:
    sc.validate_scenarios()
    assert sc.SCENARIO_IDS == ("base", "recession", "consumer-arrears-shock", "house-price-fall", "uf-inflation-spike", "combined-severe")
    for s in sc.SCENARIOS:
        if s["shocks"]:
            assert sc.ASSUMPTION in s["description"]["en"], s["id"]
            assert "supuesto del caso" in s["description"]["es"], s["id"]
        assert set(s["description"]) == {"en", "es"} and set(s["label"]) == {"en", "es"}
    assert sc.scenario("base")["z_shift"] == 0.0
    shifts = [sc.scenario(i)["z_shift"] for i in ("recession", "combined-severe")]
    assert shifts[1] < shifts[0] < 0
    assert sum(w["weight"] for w in sc.WEIGHTING) == pytest.approx(1.0, abs=1e-12) and len(sc.WEIGHTING) >= 2


def test_the_models_document_carries_the_six_scenarios_and_the_weights(built) -> None:
    fit = built["models"]["fit"]
    assert [s["id"] for s in fit["scenarios"]] == list(sc.SCENARIO_IDS)
    assert [w["id"] for w in fit["ifrs9"]["weighting_scenarios"]] == ["upside", "central", "downside"]
    assert [w["z_offset"] for w in fit["ifrs9"]["weighting_scenarios"]] == [1.0, 0.0, -2.0]
    assert fit["ifrs9"]["eir_basis"] == "original" and fit["ifrs9"]["discount_convention"] == "mid-period"
