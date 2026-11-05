"""U16-I (BL-082): ``engine-liquidity-api`` 2.0.0 against the engine it describes (``riskvalidation`` 1.0.0). The contract text names the same
dataclass fields as the installed engine, states the break (the stress-chain probabilities move to ``DepositorConfig``) and marks the input
checks internal; the engine behaves as the contract says."""
from __future__ import annotations

import ast
import dataclasses
import re
from pathlib import Path

import pytest

API = Path(__file__).resolve().parents[2] / "docs" / "contracts" / "engine" / "liquidity-api.md"


def _text() -> str:
    return API.read_text(encoding="utf-8")


def _deposit_block() -> str:
    return _text().split("### `riskvalidation.liquidity.deposits.DepositorConfig`", 1)[1].split("### `riskvalidation.liquidity.deposits.DepositorGenerator`", 1)[0]


def _documented_fields() -> dict[str, list[str]]:
    code = re.search(r"```python\n(.*?)```", _deposit_block(), flags=re.S).group(1)
    out: dict[str, list[str]] = {}
    for node in ast.parse(code).body:
        if isinstance(node, ast.ClassDef):
            out[node.name] = [n.target.id for n in node.body if isinstance(n, ast.AnnAssign)]
    return out


def test_the_contract_is_at_2_0_0_and_its_history_states_the_break() -> None:
    assert _text().startswith("# Engine liquidity API contract: `engine-liquidity-api` 2.0.0")
    head = _text().split("## Conventions", 1)[0]
    assert "2.0.0" in head and "BL-082" in head


def test_the_documented_dataclass_fields_are_the_engines() -> None:
    from riskvalidation.liquidity import deposits

    doc = _documented_fields()
    for name in ("DepositorSegment", "DepositorConfig"):
        assert doc[name] == [f.name for f in dataclasses.fields(getattr(deposits, name))], name
    assert doc["DepositorSegment"] == ["segment", "share_of_deposits", "calm_daily_hazard", "stress_daily_hazard"]
    assert doc["DepositorConfig"] == ["segments", "n_depositors", "horizon_days", "p_enter_stress", "p_exit_stress"]


def test_the_agreement_invariant_is_gone_and_the_validation_is_stated() -> None:
    body = _deposit_block()
    assert "must be equal across the segments" not in body and "segments disagree" not in body
    assert re.search(r"`p_enter_stress`.*`p_exit_stress`.*\[0, 1\]", body, flags=re.S)
    assert "TypeError" in body and "BL-082" in body


def test_the_serialised_configuration_carries_the_probabilities_at_configuration_level() -> None:
    from riskvalidation.liquidity.deposits import DepositorConfig, DepositorGenerator, DepositorSegment

    cfg = DepositorConfig((DepositorSegment("retail-insured", 1.0, 0.001, 0.01),), 10, 5, 0.01, 0.05)
    params = DepositorGenerator(cfg).config()["parameters"]
    assert params["p_enter_stress"] == 0.01 and params["p_exit_stress"] == 0.05
    assert all("p_enter_stress" not in s and "p_exit_stress" not in s for s in params["segments"])
    assert "parameters.p_enter_stress" in _deposit_block()


def test_the_engine_refuses_the_old_form_and_a_probability_that_is_not_a_unit_number() -> None:
    from riskvalidation.liquidity.deposits import DepositorConfig, DepositorSegment

    with pytest.raises(TypeError):
        DepositorSegment("retail-insured", 1.0, 0.001, 0.01, 0.01, 0.05)
    seg = (DepositorSegment("retail-insured", 1.0, 0.001, 0.01),)
    for bad in (1.5, -0.1, "0.01", True, [0.1]):
        with pytest.raises(ValueError, match="p_enter_stress"):
            DepositorConfig(seg, 10, 5, bad, 0.05)


def test_the_four_input_checks_are_marked_internal_and_outside_the_promise() -> None:
    section = _text().split("## Module `riskvalidation/liquidity/_checks.py`", 1)[1].split("\n## Module ", 1)[0]
    intro = section.split("###", 1)[0]
    assert "internal" in intro.lower() and "not part of the 2.0.0 promise" in intro


def test_the_chain_golden_still_recomputes_on_the_engine_with_the_probabilities_on_the_configuration() -> None:
    from riskvalidation.liquidity.deposits import DepositorConfig, DepositorGenerator, DepositorSegment

    cfg = DepositorConfig((DepositorSegment("retail-insured", 1.0, 0.001, 0.01),), 10, 3, 1.0, 0.0)
    truth = DepositorGenerator(cfg).truth()["outflow_rate"]["retail-insured"]
    assert [round(float(x), 7) for x in truth] == [0.001, 0.01099, 0.0208801]
