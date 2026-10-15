"""CT-1105: the illustrative portfolio is constructed, labelled illustrative and carries the fitted PD."""
from __future__ import annotations

import pytest
from c10_invariants import label_findings

from pipeline.cases.c10 import params as P
from pipeline.cases.c10 import portfolios


def test_the_illustrative_portfolio_is_labelled_and_carries_the_fitted_pd(built) -> None:
    for lt in P.LOAN_TYPES:
        portfolios.check_shape(lt["id"])
        if lt["id"] not in built["variants"]:
            continue
        doc = built["variants"][lt["id"]]
        assert label_findings(doc) == [], lt["id"]
        o = doc["outputs"]
        p, cal = o["portfolio"], o["portfolio"]["calibration"]
        ead = sum(g["n_names"] * g["ead_each"] for g in p["groups"])
        assert ead == P.TOTAL_EAD == p["total_ead"]
        weighted = sum(g["n_names"] * g["ead_each"] * g["pd"] for g in p["groups"]) / ead
        assert weighted == pytest.approx(cal["pd"], rel=1e-12) and cal["pd"] == o["fit"]["maximum_likelihood"]["pd"]["estimate"]
        assert all(g["lgd"] == P.LGD and g["loading"] ** 2 == pytest.approx(cal["rho"], rel=1e-12) for g in p["groups"])
        assert {g["id"] for g in p["groups"]} == {"g-large", "g-mid", "g-small"} and p["currency"] == "USD"
    text = " ".join(portfolios.NOTICE.values()).lower()
    assert "illustrative" in text and "never a bank" in text and "nunca la de un banco" in text


def test_a_shape_that_does_not_add_up_is_refused(monkeypatch) -> None:
    monkeypatch.setitem(P.PORTFOLIO_SHAPE, "residential", ((50, 400_000.0), (200, 200_000.0), (2000, 21_111.0)))
    with pytest.raises(portfolios.PortfolioError):
        portfolios.groups("residential", 0.01, 0.1)
