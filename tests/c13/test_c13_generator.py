"""CT-1301, CT-1302: the population correlation of HPL and RTPL is a closed form of the parameters and the generator reproduces
it; a replication is 250 finite days; the six variants are the SDD's."""
from __future__ import annotations

import c13_invariants as invariants
import numpy as np
from pipeline.cases.c13 import generator, params

TOLERANCE = 0.03     # sampling error of a Pearson correlation on 100,000 heavy-tailed pairs, with margin


def pooled_pearson(did: str, n: int = 400) -> float:
    reps = [generator.replicate(did, i) for i in range(n)]
    h, r = np.concatenate([x.hpl for x in reps]), np.concatenate([x.rtpl for x in reps])
    return float(np.corrcoef(h, r)[0, 1])


def test_a_large_sample_reproduces_the_known_correlation_of_every_variant() -> None:
    known = {d: generator.known_pearson(d) for d in params.IDS}
    for did in params.IDS:
        assert abs(pooled_pearson(did) - known[did]) < TOLERANCE, (did, pooled_pearson(did), known[did])
    assert known["time-misalignment"] == 0.0
    assert known["none"] > 0.99                                    # only the pricing noise separates HPL from RTPL
    assert known["missing-basis"] < known["none"] and known["omitted-factor"] < known["none"]
    assert 0.5 < known["missing-basis"] < 0.9 and 0.5 < known["omitted-factor"] < 0.9


def test_a_replication_is_250_finite_days_and_the_six_variants_are_the_sdd_ones() -> None:
    assert params.IDS == ("none", "missing-basis", "stale-volatility", "wrong-correlation", "omitted-factor", "time-misalignment")
    assert [d["planted"] for d in params.DEFICIENCIES] == [False, True, True, True, True, True]
    assert [d["intended"] for d in params.DEFICIENCIES][0] == "none"
    for did in params.IDS:
        rep = generator.replicate(did, 3)
        assert invariants.window_violations(rep.hpl, rep.rtpl, rep.var) == [], did
        assert rep.loss.shape == (250,) and np.array_equal(rep.loss, -rep.hpl)
        assert np.all(rep.var[0.025] > 0) and np.all(rep.var[0.01] > rep.var[0.025])      # 99 percent VaR lies deeper in the tail
        assert (rep.deficiency, rep.index, rep.seed) == (did, 3, params.seed_of(did, 3))
