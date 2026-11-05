"""Plants for C22's other families (CT-301, CT-314 to CT-316): a defect planted in a copy of the committed documents, the
predicate of the gate run on the copy, clean on the committed copy, red on the plant. The named gates of
docs/design/features/c22-validator/validation.md."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from test_c22_all_families import CREDIT, excess_gaps, null_gaps, other_gaps
from test_c22_credit_baseline import BASELINE, credit_test_ids, credit_view, digest

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"


def _doc(variant: str) -> dict:
    return json.loads((DERIVED / "C22" / f"{variant}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def registered() -> set[str]:
    import riskvalidation.validation  # noqa: F401  (registers every test)
    from riskvalidation.core.registry import catalogue

    return {s.test_id for s in catalogue() if s.decision == "p_value"}


@pytest.fixture(scope="module")
def other_ids(registered) -> set[str]:
    from riskvalidation.core.registry import catalogue

    return {s.test_id for s in catalogue() if s.decision == "p_value" and s.family not in CREDIT}


def test_adversarial_a_registered_test_of_another_family_without_its_size_is_found(registered):
    """CT-301: the clean null variant has no gap; a test of the market family removed from it, a size run of 100 repetitions
    and a rate whose Monte Carlo SE is not sqrt(p(1-p)/n) are each found."""
    doc = _doc("null")
    assert null_gaps(doc, registered) == []
    gone = copy.deepcopy(doc)
    gone["outputs"]["simulations"] = [s for s in gone["outputs"]["simulations"] if s["test_id"] != "market.kupiec_pof"]
    assert any("market.kupiec_pof" in g for g in null_gaps(gone, registered))
    short = copy.deepcopy(doc)
    next(s for s in short["outputs"]["simulations"] if s["test_id"] == "fair.fisher_exact")["n_rep"] = 100
    assert any("fair.fisher_exact" in g and "100 repetitions" in g for g in null_gaps(short, registered))
    se = copy.deepcopy(doc)
    next(s for s in se["outputs"]["simulations"] if s["test_id"] == "ccr.pfe_exceedance_backtest")["rates"]["p<0.05"]["se"] *= 2
    assert any("Monte Carlo SE" in g for g in null_gaps(se, registered))


def test_adversarial_a_study_with_one_point_or_a_shared_seed_is_found(other_ids):
    """CT-314: the clean other-families variant has no gap; a study missing its alternative point, a test missing from the
    variant, 1,000 repetitions and two simulations on one seed are each found."""
    doc = _doc("other-families")
    assert other_gaps(doc, other_ids) == []
    one = copy.deepcopy(doc)
    one["outputs"]["simulations"] = [s for s in one["outputs"]["simulations"] if s["key"] != "ml.conformal_coverage@d1"]
    assert any("ml.conformal_coverage" in g for g in other_gaps(one, other_ids))
    gone = copy.deepcopy(doc)
    gone["outputs"]["simulations"] = [s for s in gone["outputs"]["simulations"] if s["test_id"] != "fair.two_proportion_z"]
    assert any("fair.two_proportion_z: no study" in g for g in other_gaps(gone, other_ids))
    half = copy.deepcopy(doc)
    half["outputs"]["simulations"][0]["n_rep"] = 1000
    assert other_gaps(half, other_ids)
    shared = copy.deepcopy(doc)
    shared["outputs"]["simulations"][1]["seed"] = shared["outputs"]["simulations"][0]["seed"]
    assert any("share a seed" in g for g in other_gaps(shared, other_ids))


def test_adversarial_a_changed_credit_family_number_is_found():
    """CT-315: the credit view of each committed variant equals its baseline digest; one moved rejection count, a changed seed
    and a dropped simulation are each found."""
    ids = credit_test_ids()
    for variant in ("null", "drift", "clustering"):
        assert digest(credit_view(_doc(variant), ids)) == BASELINE[variant]
    doc = _doc("clustering")
    base = digest(credit_view(doc, ids))
    moved = copy.deepcopy(doc)
    moved["outputs"]["simulations"][3]["rates"]["p<0.05"]["rejections"] += 1
    assert digest(credit_view(moved, ids)) != base
    dropped = copy.deepcopy(doc)
    dropped["outputs"]["simulations"].pop()
    assert digest(credit_view(dropped, ids)) != base
    seeded = copy.deepcopy(doc)
    seeded["outputs"]["simulations"][0]["seed"] += 1
    assert digest(credit_view(seeded, ids)) != base


def test_adversarial_a_hidden_documented_excess_or_an_unflagged_excess_is_found():
    """CT-316: the clean null variant shows the engine's documented excess and flags every other one; a hidden excess block, a
    wrong engine page, an excess that is not the measured one and an oversized test without a finding are each found."""
    doc = _doc("null")
    assert excess_gaps(doc) == []
    hidden = copy.deepcopy(doc)
    mc = next(s for s in hidden["outputs"]["simulations"] if s["test_id"] == "portfolio.mc_convergence")
    mc["study"]["excess"] = None
    assert any("not shown" in g for g in excess_gaps(hidden))
    page = copy.deepcopy(doc)
    next(s for s in page["outputs"]["simulations"] if s["test_id"] == "portfolio.mc_convergence")["study"]["excess"]["page"] = "docs/x.md"
    assert any("engine page" in g for g in excess_gaps(page))
    lie = copy.deepcopy(doc)
    next(s for s in lie["outputs"]["simulations"] if s["test_id"] == "portfolio.mc_convergence")["study"]["excess"]["measured"] = 0.0001
    assert any("not the measured one" in g for g in excess_gaps(lie))
    over = copy.deepcopy(doc)
    row = next(s for s in over["outputs"]["simulations"] if s["test_id"] == "ccr.pfe_exceedance_backtest")
    row["rates"]["p<0.05"]["rate"] = 0.2
    over["findings"] = [f for f in over["findings"] if f["id"] != "F-OTHER-SIZE"]
    assert any("ccr.pfe_exceedance_backtest" in g for g in excess_gaps(over))
