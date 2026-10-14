"""CT-1108: the correlation grid carries the known correlation, covers the contract's grid and draws independent seeded replications."""
from __future__ import annotations

import math

import numpy as np
import pytest
from c10_invariants import schema_findings, violations

from pipeline.cases.c10 import params as P
from pipeline.cases.c10 import simulator


def test_the_grid_carries_the_known_correlation_and_the_replications_are_independent(built) -> None:
    # the contract's grid: 0.02 to 0.24 by 0.02, series of 22 and 40 years, the null correlation on the grid
    assert P.RHO_GRID == tuple(round(0.02 * k, 2) for k in range(1, 13)) and P.SERIES_LENGTHS == (22, 40)
    assert any(math.isclose(P.NULL_RHO, r) for r in P.RHO_GRID) and P.ALPHA == 0.05 and P.KNOWN_PD == 0.02
    for years in (22, 40):
        doc = built["variants"][f"grid-{years}"]
        assert schema_findings(f"data/derived/C10/grid-{years}.json", doc) == [] and violations(doc) == []
        o = doc["outputs"]
        assert doc["provenance"]["truth_status"] == "synthetic-known-truth" and doc["provenance"]["inputs"] == []
        assert o["generator"]["series_length_years"] == years and o["generator"]["known_pd"] == P.KNOWN_PD
        assert [c["known_rho"] for c in o["cells"]] == o["generator"]["rho_grid"]
        for c in o["cells"]:
            assert c["series_length_years"] == years and c["n_replications"] == o["generator"]["n_replications"]
            assert c["role"] == ("size" if math.isclose(c["known_rho"], P.NULL_RHO) else "power")
            assert [e["estimator"] for e in c["estimators"]] == ["maximum-likelihood", "moments"]
        assert len([t for t in doc["tests"] if t["test_id"] == "portfolio.correlation_size_power"]) == 2 * len(o["cells"])
    # independent replications: one stream each, distinct across replication, rho, length and seed; one is reproduced by its seed
    seen = set()
    for i_rho in range(len(P.RHO_GRID)):
        for i_len in range(2):
            for rep in range(50):
                seen.add(simulator.replication_entropy(P.SIM_SEED, i_rho, i_len, rep))
    assert len(seen) == 12 * 2 * 50
    e0, e1 = simulator.replication_entropy(7001, 3, 0, 0), simulator.replication_entropy(7001, 3, 0, 1)
    a = simulator.draw_rates(0.02, 0.12, 22, e0)
    assert np.array_equal(a, simulator.draw_rates(0.02, 0.12, 22, e0)) and not np.array_equal(a, simulator.draw_rates(0.02, 0.12, 22, e1))
    assert a.shape == (22,) and np.all((a > 0) & (a < 1))
    # the same cell is the same whatever the number of processes that computed it
    one = simulator.run_cell(0.12, 22, 5, 0, 8, workers=1, n_boot=100)
    two = simulator.run_cell(0.12, 22, 5, 0, 8, workers=2, n_boot=100)
    assert one == two and len(one) == 8


@pytest.mark.parametrize("rho", [0.04, 0.2])
def test_the_estimates_recover_a_large_known_truth(rho) -> None:
    """On a long series the maximum-likelihood correlation sits near the known one (the simulator draws what it says it draws)."""
    from riskvalidation.portfolio import asrf_fit

    rates = simulator.draw_rates(P.KNOWN_PD, rho, 4000, simulator.replication_entropy(1, 0, 0, 0))
    fit = asrf_fit.fit_ml(rates)
    assert fit.rho == pytest.approx(rho, rel=0.15) and fit.pd == pytest.approx(P.KNOWN_PD, rel=0.1)
