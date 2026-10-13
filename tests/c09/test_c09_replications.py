"""CT-903: independent development and test replications, fixed by seed."""
from __future__ import annotations

import c09_invariants as invariants
import numpy as np
from pipeline.cases.c09 import bake, generator


def test_development_and_test_replications_are_independent_by_seed(built) -> None:
    plan = bake.plan(42, 0.02)
    assert invariants.independent(plan) == []
    dev = generator.generate(plan["development_seeds"][0], 0, plan["n_facilities"])
    dev2 = generator.generate(plan["development_seeds"][1], 0, plan["n_facilities"])
    test = generator.generate(plan["test_seeds"][0], 0, plan["n_facilities"])
    again = generator.generate(plan["development_seeds"][0], 0, plan["n_facilities"])
    assert np.array_equal(dev.ead, again.ead) and np.array_equal(dev.limit, again.limit)       # one seed, one replication
    for other in (dev2, test):
        assert dev.ead.shape != other.ead.shape or not np.array_equal(dev.ead, other.ead)
        assert dev.limit.shape != other.limit.shape or not np.array_equal(dev.limit, other.limit)
    fit = built["models"]["fit"]["replications_plan"]
    assert fit["development_seeds"] == plan["development_seeds"] and fit["test_seeds"] == plan["test_seeds"]
    assert invariants.independent(fit) == []
    for doc in built["variants"].values():
        r = doc["outputs"]["replications"]
        assert r["development"]["seeds"] == plan["development_seeds"] and r["test"]["seeds"] == plan["test_seeds"]
        assert r["development"]["n_replications"] == len(plan["development_seeds"])
    assert bake.plan(43, 0.02)["test_seeds"] != plan["test_seeds"]
