"""CT-1303, CT-1308, CT-1309: independent replications by seed, the size of the test and the recomputed catch rates."""
from __future__ import annotations

import c13_invariants as invariants
import numpy as np
import pytest
from pipeline.cases.c13 import bake, generator, measure, params

NONE_MAX_AMBER_OR_RED = 0.10


def test_replications_are_independent_by_seed_and_reproduced_by_their_seed() -> None:
    pl = bake.plan(13, 1.0)
    assert invariants.independent(pl) == []
    assert [v["deficiency_id"] for v in pl["variants"]] == list(params.IDS) and all(len(v["seeds"]) == 1000 for v in pl["variants"])
    assert len({s for v in pl["variants"] for s in v["seeds"]}) == 6000
    a, b, c = generator.replicate("missing-basis", 5), generator.replicate("missing-basis", 5), generator.replicate("missing-basis", 6)
    assert np.array_equal(a.hpl, b.hpl) and np.array_equal(a.rtpl, b.rtpl) and a.seed == b.seed
    assert not np.array_equal(a.hpl, c.hpl) and a.seed != c.seed
    assert not np.array_equal(a.hpl, generator.replicate("none", 5).hpl)          # another variant, another seed range
    with pytest.raises(ValueError):
        params.seed_of("none", 1000)                                              # the next variant's range


def test_the_no_deficiency_variant_lands_green_at_its_nominal_rate(built) -> None:
    doc = built["variants"]["none"]
    assert invariants.size(doc, NONE_MAX_AMBER_OR_RED) == []
    z = doc["outputs"]["pla"]["zones"]
    assert z["overall"]["green"] >= (1 - NONE_MAX_AMBER_OR_RED) * z["n"] and z["overall"]["red"] == 0
    for row in doc["outputs"]["desk_backtest"]:
        # the exceptions of an exact model are binomial(250, alpha): the mean sits at 250 alpha and the desk stays within its limit
        assert abs(row["exceptions"]["mean"] - 250 * row["alpha"]) < 0.5 * row["alpha"] * 250 + 1.0
        assert row["share_over_limit"] <= 0.05
    assert all(built["variants"][d]["outputs"]["detection"]["share_amber_or_red"] > NONE_MAX_AMBER_OR_RED
               for d in ("missing-basis", "time-misalignment"))


def test_the_reported_catch_rates_are_recomputed_from_the_replications(built) -> None:
    n = built["plan"]["n_replications"]
    for did, doc in built["variants"].items():
        assert invariants.closure(doc) == [], did
        fresh = measure.measure(did, 13, n)
        z = doc["outputs"]["pla"]["zones"]
        assert z["overall"] == fresh.zone_counts("overall") and z["spearman"] == fresh.zone_counts("spearman")
        assert z["ks"] == fresh.zone_counts("ks"), did
        det = doc["outputs"]["detection"]
        assert det["n_amber_or_red"] == fresh.n_amber_or_red and det["by_test"]["desk_backtest_flagged"] == fresh.n_desk_flagged
        for row in doc["outputs"]["desk_backtest"]:
            assert row["n_over_limit"] == fresh.n_over_limit(row["alpha"]), (did, row["alpha"])
