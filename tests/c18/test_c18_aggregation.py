"""CT-1811 and CT-1812: the headline is the simple sum, every other figure is information; the band and the Euler allocation."""
from __future__ import annotations

import pytest
from c18_support import requires_raw

from pipeline.cases.c18 import params as P

pytestmark = requires_raw


def test_the_headline_is_the_simple_sum_and_every_other_figure_is_information(built) -> None:
    for vid in (*P.SCENARIOS.values(), P.FILE_NAMES["aggregation"]):
        if vid not in built.variants:
            continue
        a = built.variants[vid]["outputs"]["aggregation"]
        total = sum(m["ec_clp_m"] for m in a["marginals"])
        assert a["headline"]["method"] == "simple-sum" and a["headline"]["capital_clp_m"] == pytest.approx(total)
        for r in a["band"]:
            if r["method"] == "simple-sum":
                assert r["status"] == "headline-capital" and r["capital_clp_m"] == pytest.approx(total)
            else:
                assert r["status"] == "information-not-capital" and r["label"]["en"].startswith("Information, not capital")
        for blk in (a["model_risk"], a["euler"], a["diversification"]):
            assert blk["status"] == "information-not-capital"
        assert built.variants[vid]["impact"]["capital_simple_sum"]["value"] == pytest.approx(total)


def test_the_band_has_the_ladder_rows_and_the_euler_allocation_adds_up(built) -> None:
    a = built.variants[P.FILE_NAMES["aggregation"]]["outputs"]["aggregation"]
    methods = [(r["method"], r["nu"]) for r in a["band"]]
    assert methods == [("lower-bound", None), ("simple-sum", None), ("variance-covariance", None), ("gaussian-copula", None),
                       ("t-copula", 4.0), ("t-copula", 8.0), ("t-copula", 30.0), ("worst-case", None)]
    caps = {(r["method"], r["nu"]): r["capital_clp_m"] for r in a["band"]}
    middle = [v for k, v in caps.items() if k[0] not in ("lower-bound", "worst-case")]
    assert caps[("lower-bound", None)] <= min(middle) and caps[("worst-case", None)] >= max(middle)
    assert a["correlation"]["name"] == "correlation_matrix_base" and a["correlation"]["label"] == "convention"
    base = a["correlation"]["matrix"]
    assert base[0][1] == 0.5 and base[0][3] == 0.2 and base[1][3] == 0.2          # Rosenberg and Schuermann: market-credit 0.5, with operational 0.2
    stress = built.variants[P.FILE_NAMES["aggregation"]]["outputs"]["correlation_stress"]
    assert stress["pair"] == {"a": "market", "b": "credit", "value": 0.8} and stress["aggregation"]["correlation"]["matrix"][0][1] == 0.8
    e = a["euler"]
    s = sum(x["contribution_clp_m"] for x in e["allocation"])
    assert s == pytest.approx(e["es_total_clp_m"], rel=1e-9) and e["additivity"]["relative_error"] < 1e-6
    assert a["nu_set"]["label"] == "convention" and a["nu_set"]["values"] == [4.0, 8.0, 30.0]
