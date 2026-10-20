"""G20: contract 1, family scored_sample, dataset parameter outcome = population (features only: no outcome, no decision; a shift probe).
The producer side of contract-family 1.3.0; the declaration it exports is checked in test_documents.py."""
from __future__ import annotations

import json

import pytest

from pipeline.io import contract as c

POP = {"outcome": "population"}
ROW = {"id": "1", "observation_date": "2025-12-31"}


def test_the_outcome_parameter_declares_the_population_value() -> None:
    param = next(p for p in c.SCORED_SAMPLE.params if p.name == "outcome")
    assert param.values == ("target", "none", "population")
    assert any(r.id == "SS-POPULATION-NO-OUTCOME" for r in c.SCORED_SAMPLE.rules)
    declared = json.loads(json.dumps(c.SCORED_SAMPLE.to_json()))
    assert [r["id"] for r in declared["rules"]].count("SS-POPULATION-NO-OUTCOME") == 1


def test_a_population_sample_with_features_only_is_accepted() -> None:
    rep = c.validate("scored_sample", [ROW, {**ROW, "id": "2"}], params=POP)
    assert rep.counts()["accepted"] == 2 and rep.counts()["rejected"] == 0


@pytest.mark.parametrize("extra", [{"target": 0}, {"target": 1}, {"decision": 1}, {"decision": 0}, {"target": 0, "decision": 1}])
def test_a_population_row_with_an_outcome_or_a_decision_is_rejected_by_the_record_rule(extra: dict) -> None:
    rep = c.validate("scored_sample", [{**ROW, **extra}], params=POP)
    assert rep.accepted == [] and len(rep.rejected) == 1
    v = rep.rejected[0]["violations"][0]
    assert v["rule"] == "SS-POPULATION-NO-OUTCOME" and v["policy"] == "reject"
    assert v["expected"] == "A population sample carries neither an outcome nor a decision; its role is a shift probe."


def test_a_clean_row_beside_a_rejected_one_is_kept_and_the_rejection_names_its_row() -> None:
    rep = c.validate("scored_sample", [ROW, {**ROW, "id": "2", "target": 0}], params=POP)
    assert [r["id"] for r in rep.accepted] == ["1"] and rep.rejected[0]["row"] == 1


def test_the_other_outcome_values_behave_as_before() -> None:
    assert c.validate("scored_sample", [ROW], params={"outcome": "none"}).accepted == []          # none still requires decision
    assert c.validate("scored_sample", [ROW]).accepted == []                                      # target (default) still requires target
    assert c.validate("scored_sample", [ROW], params={"outcome": "target"}).accepted == []
    assert c.validate("scored_sample", [{**ROW, "decision": 1}], params={"outcome": "none"}).counts()["accepted"] == 1
    assert c.validate("scored_sample", [{**ROW, "target": 0}]).counts()["accepted"] == 1
    # the record rule does not touch a scored sample that carries a target or a decision
    assert c.validate("scored_sample", [{**ROW, "target": 1, "decision": 0}], params={"outcome": "none"}).counts()["accepted"] == 1


def test_an_unknown_outcome_value_is_refused() -> None:
    with pytest.raises(c.ContractError):
        c.validate("scored_sample", [ROW], params={"outcome": "populations"})
