"""U16-F12e (fix round 5, R4 c21 m7 and m12): the C17 references write the authors as published (Böcker, Wüthrich), and the
exceedance read from a pmf is None past the last node of its grid, never the last value held flat (the FFT side the views draw as a
gap on the tail index 0.96 and 1.1 variants)."""
from __future__ import annotations

import numpy as np

from pipeline.cases.c17 import aggregation as ga
from pipeline.cases.c17 import params as P


def _references() -> list[str]:
    refs = [r["reference"] for r in P.LADDER] + [P.SCENARIO_SPEC["reference"]]
    return [r for r in refs if "Sprittulla" in r or "Shevchenko and" in r]


def test_m7_the_authors_keep_their_umlauts() -> None:
    refs = _references()
    assert refs, "no reference names Böcker or Wüthrich"
    for r in refs:
        assert "Bocker" not in r and "Wuthrich" not in r, r
    assert any("Böcker and Sprittulla" in r for r in refs)
    assert any("Shevchenko and Wüthrich" in r for r in refs)


def test_m12_the_exceedance_past_the_grid_is_none() -> None:
    step = 10.0
    h = np.zeros(100)
    h[:50] = 1 / 50                      # a pmf on the nodes 0 to 990
    x = np.array([5.0, 500.0, 990.0, 991.0, 5_000.0])
    out = ga.sf_within_grid(h, step, x)
    assert out[0] is not None and out[1] is not None and out[2] is not None
    assert out[3] is None and out[4] is None
