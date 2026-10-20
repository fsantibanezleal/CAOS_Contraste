"""CT-1809 and CT-1810: the four marginals at one year and 99.9 percent."""
from __future__ import annotations

import dataclasses
from statistics import NormalDist

import pytest
from c18_support import requires_raw

from pipeline.cases.c18 import anchors as anc
from pipeline.cases.c18 import marginals

pytestmark = requires_raw


def test_every_marginal_is_one_year_999_and_ec_is_var_less_el(built) -> None:
    core = built.results["core"]
    assert [m.risk for m in core.marginals] == ["credit", "market", "irrbb", "operational"]
    doc = built.variants["baseline"]["outputs"]["aggregation"]
    assert doc["horizon_years"] == 1 and doc["confidence_level"] == 0.999
    for m, blk in zip(core.marginals, doc["marginals"], strict=True):
        assert (blk["horizon_years"], blk["confidence_level"]) == (1, 0.999)
        assert blk["ec_basis"] == "var-less-el" and blk["ec_clp_m"] == pytest.approx(blk["var_clp_m"] - blk["el_clp_m"])
        assert blk["es_clp_m"] >= blk["var_clp_m"]
    credit = core.marginals[0]
    # the engine's expected_loss on the six segments (the names of a group carry the segment's exposure)
    assert credit.el == pytest.approx(sum(s.exposure_clp_m * s.pd * s.lgd for s in core.anchors.segments))
    # the engine's estimators read the market quantile grid back to the scaled C11 figures
    mk = core.marginals[1]
    assert mk.var == pytest.approx(mk.extras["target_var"], rel=1e-2) and mk.es == pytest.approx(mk.extras["target_es"], rel=8e-2)   # the test grid has 20,000 points; the bake uses 10^6
    assert mk.el == 0.0


def test_market_scaling_conventions_and_the_operational_marginal(built) -> None:
    core = built.results["core"]
    nd = NormalDist()
    sc = marginals.market_scaling()
    assert sc["level_factor"] == pytest.approx(nd.inv_cdf(0.999) / nd.inv_cdf(0.99))
    assert sc["horizon_factor"] == pytest.approx(250 ** 0.5) and sc["value"] == pytest.approx(sc["level_factor"] * sc["horizon_factor"], rel=1e-9)
    named = core.named["market_horizon_scaling"]
    assert named["label"] == "convention" and named["level_factor"]["label"] == "convention" and named["horizon_factor"]["label"] == "convention"
    mk = core.marginals[1]
    assert mk.extras["target_var"] == pytest.approx(mk.extras["c11"]["var"] * sc["value"] * core.anchors.rwa_by_risk["market"])
    op = core.marginals[3]
    assert op.extras["tail_index"] == 0.8 and not op.extras["infinite_mean"] and op.el is not None and op.es > op.var
    assert op.extras["missing_mass"] <= 1e-6
    # an infinite-mean severity is refused (the engine has no expected shortfall for it)
    a = anc.load_anchors()
    inf = dataclasses.replace(a, c17=dict(a.c17, tail_index=1.1, infinite_mean=True))
    with pytest.raises(ValueError, match="infinite-mean"):
        marginals.operational(inf, 1076.06, n_points=1 << 14)
