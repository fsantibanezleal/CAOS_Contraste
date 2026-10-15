"""CT-1106, CT-1107: the ladder keeps its orderings, a rung that did not run carries no number, the Euler contributions add up and
the granularity matches the paper."""
from __future__ import annotations

import pytest
from c10_invariants import schema_findings, violations

from pipeline.cases.c10 import params as P

RUNGS = ["c1-lhp", "c2-gaussian-1f", "c2-gaussian-mf", "c3-student-t", "c4-creditrisk-plus", "c5-granularity", "c6-is-gaussian",
         "c6-is-student-t"]


def loan_docs(built):
    return [(lt["id"], built["variants"][lt["id"]]) for lt in P.LOAN_TYPES if lt["id"] in built["variants"]]


def test_the_ladder_keeps_its_orderings_and_a_rung_that_did_not_run_carries_no_number(built) -> None:
    for vid, doc in loan_docs(built):
        assert schema_findings(f"data/derived/C10/{vid}.json", doc) == [], vid
        assert violations(doc) == [], (vid, violations(doc))
        rungs = doc["outputs"]["rungs"]
        assert [r["id"] for r in rungs] == RUNGS
        for r in rungs:
            if r["id"] == "c6-is-student-t":
                assert (r["evaluated"], r["estimator"], r["measures"], r["distribution"], r["diagnostics"]) == (False, "none", None, None, [])
                assert r["reason"] and r["simulation"] is None
                continue
            assert r["evaluated"] and r["reason"] is None
            for m in r["measures"]:
                assert m["var"] >= m["el"] and (m["es"] is None or m["es"] >= m["var"])
                assert m["ec"] == pytest.approx(m["var"] - m["el"], abs=1e-6 * m["var"])
            if r["estimator"] == "monte-carlo":
                n_names = doc["outputs"]["portfolio"]["n_names"]
                assert r["simulation"]["chunk_size"] * n_names * 8 <= P.CHUNK_BYTES + 8 * n_names
                # a batch-means error may be zero for a VaR on the loss lattice, never negative or missing
                assert all(m["var_se"] >= 0 and m["es_se"] > 0 for m in r["measures"])
        by = {r["id"]: r for r in rungs}
        # the importance-sampling rung lies within the combined Monte Carlo errors of the plain one at both levels
        for a, b in zip(by["c6-is-gaussian"]["measures"], by["c2-gaussian-1f"]["measures"], strict=True):
            for k in ("var", "es"):
                se = (a[f"{k}_se"] ** 2 + b[f"{k}_se"] ** 2) ** 0.5
                step = min(g["ead_each"] * g["lgd"] for g in doc["outputs"]["portfolio"]["groups"]) if k == "var" else 0.0
                assert abs(a[k] - b[k]) <= 4.0 * se + step, (vid, k, a[k], b[k], se)
        assert "effective_sample_share" in {d["name"] for d in by["c6-is-gaussian"]["diagnostics"]}
        assert by["c5-granularity"]["measures"][1]["var"] > by["c1-lhp"]["measures"][1]["var"]
        assert by["c5-granularity"]["measures"][0]["es"] is None and by["c5-granularity"]["measures"][0]["es_reason"]


def test_the_euler_contributions_add_up_and_the_granularity_matches_the_paper(built) -> None:
    for vid, doc in loan_docs(built):
        o = doc["outputs"]
        assert [e["rung_method"] for e in o["euler"]] == ["gaussian-copula-one-factor", "gaussian-copula-multi-factor", "student-t-copula"]
        for e in o["euler"]:
            for lv in e["levels"]:
                assert {r["group_id"] for r in lv["rows"]} == {g["id"] for g in o["portfolio"]["groups"]}
                assert sum(r["rc_es"] for r in lv["rows"]) == pytest.approx(lv["es_total"], rel=lv["es_sum_tolerance"])
                assert sum(r["rc_var"] for r in lv["rows"]) == pytest.approx(lv["var_total"], rel=lv["var_sum_tolerance"])
        one = o["euler"][0]
        assert all(lv["anchor"] is not None and lv["anchor"]["method"] == "asrf-asymptotic" for lv in one["levels"])
        assert all(lv["anchor"] is None and lv["anchor_reason"] for e in o["euler"][1:] for lv in e["levels"])
        g = o["granularity"]
        top = next(x for x in g["levels"] if x["q"] == 0.999)
        assert g["xi"] == 0.25 and abs(top["delta"] - 4.83) < 0.005 and g["k_source"] == "irb-regulatory-correlation" and g["k_star"] > 0
        assert top["ga_money"] == pytest.approx(top["ga"] * o["portfolio"]["total_ead"], rel=1e-9)
        rows = g["by_n_names"]
        assert all(r["ga"] * r["n_names"] == pytest.approx(rows[0]["ga"] * rows[0]["n_names"], rel=1e-9) for r in rows)
        assert all((r["truth_ga"] is None) != (r["truth_reason"] is None) for r in rows)
        tests = {(t["test_id"], t["model_id"], t["segment"]): t for t in doc["tests"]}
        assert len([k for k in tests if k[0] == "portfolio.euler_additivity"]) == 12
        assert all(t["light"] in ("green", "amber", "red") for t in doc["tests"] if t["test_id"] == "portfolio.euler_additivity")
        assert ("portfolio.mc_convergence", "m-gaussian-1f", "lhp-like-99.9") in tests
        assert ("portfolio.crp_recursion_vs_mc", "m-creditrisk-plus", None) in tests
        assert ("portfolio.tail_backtest", "m-lhp", None) in tests
