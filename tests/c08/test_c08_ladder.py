"""CT-907: the six rungs, their range, the beta rung's epsilons and the rung that cannot be fitted."""
from __future__ import annotations

import numpy as np
import pytest
from c08_helpers import range_findings

from pipeline.cases.c08 import cutoff as C
from pipeline.cases.c08.ladder import EPSILONS, RUNGS, fit_ladder

RUNG_IDS = ["L1-ols", "L2-fractional-logit", "L3-beta", "L4-hurdle", "L5-gradient-boosted", "L6-tobit"]


@pytest.fixture(scope="module")
def fitted(tables):
    d = tables["defaults"]
    train = d.take(C.training_mask(d, "2008-12-31"))
    return fit_ladder(train.design(), train.y, "2008-12-31", 42), d.take(d.year >= 2009)


def test_each_rung_predicts_inside_zero_one_and_beta_reports_its_epsilons(fitted, docs):
    lad, test = fitted
    assert [r for r, _ in RUNGS] == RUNG_IDS and list(lad.rungs) == RUNG_IDS
    x = test.design()
    evaluated = 0
    for rid, rung in lad.rungs.items():
        if rung.evaluated:
            evaluated += 1
            p = lad.predict(rung, x)
            assert p.shape == (test.n,) and np.isfinite(p).all() and (p >= 0).all() and (p <= 1).all(), rid
        else:
            assert rung.reason and rung.fit is None and rung.booster is None
    assert evaluated >= 4 and lad.rungs["L1-ols"].evaluated and lad.rungs["L2-fractional-logit"].evaluated
    assert lad.rungs["L5-gradient-boosted"].evaluated, "catboost is pinned by the pipeline"
    assert set(lad.beta_by_epsilon) == set(EPSILONS) and len(EPSILONS) >= 2
    fits = [lad.beta_by_epsilon[e].fit.extras["epsilon"] for e in EPSILONS if lad.beta_by_epsilon[e].evaluated]
    assert fits == [e for e in EPSILONS if lad.beta_by_epsilon[e].evaluated]
    for vid, doc in docs["variants"].items():
        o = doc["outputs"]
        assert range_findings(o) == [], vid
        eps = [r["epsilon"] for r in o["endpoint_sensitivity"]]
        assert len(eps) >= 2 and eps == sorted(set(eps)) and all(0 < e < 0.5 for e in eps)
        ladder = docs["models"][f"models-{vid}"]["fit"]["ladder"]
        assert [r["rung_id"] for r in ladder] == RUNG_IDS
        compared = {r["rung_id"] for r in o["rung_comparison"]}
        for r in ladder:
            if r["rung_id"] not in compared:  # not evaluated: no coefficient, no covariate, no comparison row
                assert r["coefficients"] == [] and r["covariates"] == []
        assert next(r for r in ladder if r["kind"] == "beta")["epsilon"] == 0.001
        assert next(r for r in ladder if r["kind"] == "gradient-boosted")["library"] == "catboost"


def test_a_rung_that_cannot_be_fitted_is_reported_not_evaluated_with_its_reason(tables):
    d = tables["defaults"]
    tiny = d.take(np.arange(d.n) < 60)
    lad = fit_ladder(tiny.design(), tiny.y, "2002-12-31", 1)
    assert list(lad.rungs) == RUNG_IDS
    for rid, r in lad.rungs.items():
        assert not r.evaluated and "fewer than the 200" in r.reason and r.fit is None and r.booster is None
        with pytest.raises(ValueError, match="not evaluated"):
            lad.predict(r, tiny.design())


def test_adversarial_a_prediction_outside_zero_one_is_found(docs):
    o = docs["variants"]["dc-2009-10"]["outputs"]
    assert range_findings(o) == []
    planted = {**o, "realised_vs_predicted": [{**o["realised_vs_predicted"][0], "predicted": {"value": 1.2, "flag": "in-range"}},
                                              *o["realised_vs_predicted"][1:]]}
    assert range_findings(planted) == [f"prediction 1.2 of {o['realised_vs_predicted'][0]['rung_id']}"]
