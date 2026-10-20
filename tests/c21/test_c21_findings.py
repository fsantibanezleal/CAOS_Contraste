"""CT-2118 (review M4, decision G16): the findings of a C21 pair document are statistical findings about its own evidence.

The oracle here reads the contrast blocks and the test rows of the document, never the producer's rules: for each pair it derives which
contrasts show a controlled disparity that repeats, one that does not repeat, and a rate-spread disparity that repeats, and compares the
findings with that. Every title says "no legal claim" and none states a violation.
"""
from __future__ import annotations

import contract_schemas as cs
import pytest
from c21_support import VARIANTS, committed

from pipeline.cases.c21 import legal

LOGIT, OLS, RATES = "hmda-logistic-decision", "hmda-linear-rate-spread", "hmda-selection-rates"
FORBIDDEN = ("violat", "discriminat", "illegal", "unlawful", "breach", "liable")
EXPECT = {"repeats": ("F-CONTROLLED-REPEATS", "S2", "open"), "not-repeated": ("F-CONTROLLED-NOT-REPEATED", "S3", "open"),
          "rate-spread": ("F-RATE-SPREAD-REPEATS", "S3", "open")}
LIMITS = {"F-LIMIT-CREDIT-SCORE": "design:credit-score-missing", "F-LIMIT-COMPLETE-CASES": "design:complete-case-selection"}


def excludes_zero(ci: dict) -> bool:
    return ci["lo"] > 0 or ci["hi"] < 0


def rows_of(doc: dict) -> dict[str, dict]:
    return {f"{r['test_id']}@{r['model_id']}@{r['segment']}": r for r in doc["tests"]}


def oracle(doc: dict) -> dict[str, set[str]]:
    """The evidence each statistical finding must cite, from the contrast blocks and the replication rows of the document."""
    rows = rows_of(doc)
    out: dict[str, set[str]] = {"repeats": set(), "not-repeated": set(), "rate-spread": set()}
    for a in doc["outputs"]["attributes"]:
        for c in a["contrasts"]:
            seg = f"{a['field']}|{c['group']} vs {c['reference_group']}"
            est, conf = c["controlled"]["estimate"], c["confirmation"]["estimate"]
            if est is not None and conf is not None and excludes_zero(est["ci"]):
                key = "repeats" if conf["same_sign"] else "not-repeated"
                out[key] |= {f"fair.conditional_disparity@{LOGIT}@{seg}", f"fair.replication@{LOGIT}@{seg}|controlled"}
            rs = c["rate_spread"]["estimate"]
            rep = rows.get(f"fair.replication@{OLS}@{seg}|rate_spread")
            if rs is not None and rep is not None and excludes_zero(rs["ci"]) and rep["extras"]["same_sign"]:
                out["rate-spread"] |= {f"fair.rate_spread_disparity@{OLS}@{seg}", f"fair.replication@{OLS}@{seg}|rate_spread"}
    return out


def check_findings(name: str, doc: dict) -> dict[str, dict]:
    findings = {f["id"]: f for f in doc["findings"]}
    assert findings and len(findings) == len(doc["findings"]), name                       # ids are unique and the list is not empty
    rows = rows_of(doc)
    for f in doc["findings"]:
        assert cs.errors("common/finding", f) == [], (name, f["id"])
        assert "no legal claim" in f["title"]["en"] and "sin afirmacion legal" in f["title"]["es"], (name, f["id"])
        assert not any(w in f["title"]["en"].lower() or w in f["title"]["es"].lower() for w in FORBIDDEN), (name, f["id"])
        for e in f["evidence"]:
            assert e.startswith("design:") or e in rows, (name, f["id"], e)                 # test rows of this very document
    expected = oracle(doc)
    for key, (fid, severity, status) in EXPECT.items():
        if expected[key]:
            f = findings[fid]
            assert (f["severity"], f["status"]) == (severity, status), (name, fid)
            assert set(f["evidence"]) == expected[key] and len(f["evidence"]) == len(expected[key]), (name, fid)
        else:
            assert fid not in findings, (name, fid)
    for fid, ev in LIMITS.items():
        f = findings[fid]
        assert (f["severity"], f["status"], f["evidence"]) == ("S4", "accepted", [ev]), (name, fid)
    amber = [a["field"] for a in doc["outputs"]["attributes"]
             if next(r for r in doc["tests"] if r["test_id"] == "fair.demographic_parity" and r["segment"] == a["field"])["light"] != "green"]
    if amber:
        u = findings["F-UNCONDITIONAL-GAP"]
        assert (u["severity"], u["status"]) == ("S4", "open")
        assert set(u["evidence"]) == {f"fair.{t}@{RATES}@{f}" for t in ("demographic_parity", "adverse_impact") for f in amber}
        assert legal.QUOTES["procedures"][1] in u["title"]["en"] and "indicator only" in u["title"]["en"]
    else:
        assert "F-UNCONDITIONAL-GAP" not in findings
    assert len(findings) == sum(1 for v in expected.values() if v) + len(LIMITS) + (1 if amber else 0), name
    return findings


@pytest.mark.parametrize("name", VARIANTS)
def test_the_committed_findings_are_statistical_findings_with_their_own_test_evidence(name: str) -> None:
    findings = check_findings(name, committed(name))
    # the persistent controlled disparity of the Black or African American group is in the S2 finding of every pair
    seg = "derived_race|Black or African American vs White"
    f = findings["F-CONTROLLED-REPEATS"]
    assert {f"fair.conditional_disparity@{LOGIT}@{seg}", f"fair.replication@{LOGIT}@{seg}|controlled"} <= set(f["evidence"])
    assert f["severity"] == "S2" and f["status"] == "open"


def test_the_findings_of_a_planted_bake_follow_the_same_rules(built) -> None:
    for name in built.order:
        check_findings(name, built.variants[name])
