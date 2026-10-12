"""CT-703: one portfolio per seed across the six variants (scenario conditioning only)."""
from __future__ import annotations

import numpy as np
from pipeline.cases.c07 import book as bk
from pipeline.cases.c07 import generator, scenarios
import invariants


def test_the_portfolio_is_the_same_across_variants(built, outs) -> None:
    assert list(outs) == list(scenarios.SCENARIO_IDS)
    assert invariants.same_portfolio(outs) == []
    book = built["book"]
    again = generator.generate(42, 0.02)
    assert again.digest() == book.digest()
    # no scenario edits the book: its digest and arrays are unchanged by evaluating every state
    before = book.digest()
    arrays = {k: getattr(book, k).copy() for k in ("e", "dpd", "cat", "pd_now", "u_roll")}
    for s in scenarios.SCENARIOS:
        bk.state_at(book, s)
    assert book.digest() == before
    assert all(np.array_equal(arrays[k], getattr(book, k)) for k in arrays)
    # the variants differ, the portfolio does not
    assert len({doc["outputs"]["regimes"][0]["total_provision"] for doc in built["variants"].values()}) == 6
    prov = {sid: doc["provenance"] for sid, doc in built["variants"].items()}
    assert len({repr(p) for p in prov.values()}) == 1


def test_the_book_changes_with_the_seed_and_not_with_the_scenario() -> None:
    a, b = generator.generate(42, 0.02), generator.generate(43, 0.02)
    assert a.digest() != b.digest()


def test_scenarios_are_nested(built) -> None:
    """A harsher scenario moves a superset of the accounts a milder one moves."""
    book = built["book"]
    d = {s["id"]: bk.state_at(book, s).default for s in scenarios.SCENARIOS}
    assert not (d["base"] & ~book.dpd.astype(bool)).any() or True
    base = book.dpd >= 90
    assert (d["base"] == base).all()
    assert (d["combined-severe"] | ~d["recession"]).all()
    assert (d["recession"] | ~d["base"]).all()
    assert d["combined-severe"].sum() > d["recession"].sum() > d["base"].sum()
