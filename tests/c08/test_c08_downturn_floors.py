"""CT-911 and CT-912: the downturn add-on over the downturn cohorts only, and the floors' bite."""
from __future__ import annotations

import copy
import json

import numpy as np
from c08_helpers import COMMITTED, addon_findings, floor_findings
from riskvalidation.lgd_ead.downturn import coverage_shortfall

from pipeline.cases.c08 import build as bd
from pipeline.cases.c08 import downturn as dn
from pipeline.cases.c08.panel import COHORTS


def test_the_add_on_uses_only_the_downturn_cohorts(tables, annual):
    d = tables["defaults"]
    plan = dn.plan(d, annual)
    y = d.y
    mean = {cid: float(y[(d.year >= lo) & (d.year <= hi)].mean()) for cid, lo, hi in COHORTS}
    n = {cid: int(((d.year >= lo) & (d.year <= hi)).sum()) for cid, lo, hi in COHORTS}
    assert plan.downturn_cohorts and "2009-10" in plan.downturn_cohorts
    first, last = plan.period["first_year"], plan.period["last_year"]
    assert first <= 2009 and last >= 2010
    # a downturn cohort has at least half of its default years inside the downturn period
    for cid, lo, hi in COHORTS:
        inside = sum(1 for yr in range(lo, hi + 1) if first <= yr <= last and yr in plan.flagged_years)
        assert (2 * inside >= hi - lo + 1) == (cid in plan.downturn_cohorts), cid
    long_run = sum(mean[c] * n[c] for c in mean) / sum(n.values())
    down = sum(mean[c] * n[c] for c in plan.downturn_cohorts) / sum(n[c] for c in plan.downturn_cohorts)
    assert abs(plan.long_run - long_run) < 1e-12 and abs(plan.downturn - down) < 1e-12
    assert [r["cohort_id"] for r in plan.rows] == plan.downturn_cohorts
    for r in plan.rows:
        assert abs(r["add_on"] - (r["downturn_lgd"]["value"] - r["long_run_lgd"]["value"])) < 1e-12
        assert r["crisis_realised_lgd"]["value"] == mean[r["cohort_id"]] and r["n"] == n[r["cohort_id"]]
        covered, shortfall = coverage_shortfall(down, mean[r["cohort_id"]])
        assert (r["covered"], r["shortfall"]) == (covered, shortfall)
    assert plan.coverage == {"n_cohorts": len(plan.rows), "share_covered": sum(r["covered"] for r in plan.rows) / len(plan.rows)}
    assert len(plan.tests) == len(plan.rows) and all(t["test_id"] == "lgd_ead.downturn_coverage" for t in plan.tests)
    assert "annual charge-off rate" in plan.period["indicator"] and "no macro path" in plan.period["macro_source"]


def test_the_downturn_block_is_the_same_in_every_variant_and_committed_rows_follow_the_period(docs):
    blocks = [json.dumps(doc["outputs"]["downturn"], sort_keys=True) for doc in docs["variants"].values()]
    assert len(set(blocks)) == 1
    for vid, doc in docs["variants"].items():
        flagged = {r["cohort_id"] for r in doc["outputs"]["downturn"]["rows"]}
        assert addon_findings(doc["outputs"]["downturn"], flagged) == []
        assert docs["models"][f"models-{vid}"]["fit"]["downturn"]["period"] == doc["outputs"]["downturn"]["period"]
    manifest = json.loads((COMMITTED / "manifests" / "C08.json").read_text(encoding="utf-8"))
    for a in (x for x in manifest["artifacts"] if x["role"] == "variant"):
        down = json.loads((COMMITTED / a["path"]).read_text(encoding="utf-8"))["outputs"]["downturn"]
        p = down["period"]
        for r in down["rows"]:
            lo, hi = next((x, y) for c, x, y in COHORTS if c == r["cohort_id"])
            years = range(lo, hi + 1)
            assert 2 * sum(1 for yr in years if p["first_year"] <= yr <= p["last_year"]) >= len(years), "a cohort outside the downturn period"
        assert addon_findings(down, {r["cohort_id"] for r in down["rows"]}) == []


def test_adversarial_an_add_on_over_a_non_downturn_cohort_is_found(docs):
    down = copy.deepcopy(docs["variants"]["dc-2009-10"]["outputs"]["downturn"])
    names = {r["cohort_id"] for r in down["rows"]}
    assert addon_findings(down, names) == []
    extra = {**down["rows"][0], "cohort_id": "2014-19"}
    assert addon_findings({**down, "rows": [*down["rows"], extra]}, names) == ["row 2014-19 is not a downturn cohort"]
    broken = {**down["rows"][0], "add_on": down["rows"][0]["add_on"] + 0.2}
    assert addon_findings({**down, "rows": [broken]}, names) == [f"add-on of {broken['cohort_id']}"]


def test_the_floor_bite_is_the_engines_and_the_segments_map_to_the_cells(docs):
    ids = [s[0] for s in bd.SEGMENTS]
    assert bd.segment_of(np.array([True, False, False, False, False]), np.array([300, 300, 240, 100, 60])).tolist() == [0, 3, 3, 2, 1]
    assert bd.segment_of(np.array([False, False]), np.array([239, 85])).tolist() == [2, 2]
    assert bd.segment_of(np.array([False]), np.array([84])).tolist() == [1]
    cells = {c["id"] for c in bd.floor_cells_block()}
    assert len(cells) == 12 and all(s[1] in cells for s in bd.SEGMENTS)
    for vid, doc in docs["variants"].items():
        fb = doc["outputs"]["floors_bite"]
        assert fb["regime"] == "basel-iii-final" and fb["rows"]
        assert floor_findings(fb["rows"]) == [], vid
        assert [r["segment_id"] for r in fb["rows"]] == [i for i in ids if i in {r["segment_id"] for r in fb["rows"]}]
        assert "inferred" in fb["note"]["en"]
        for r in fb["rows"]:
            assert 0.0 <= r["share_binding"] <= 1.0 and r["uplift"] >= 0.0
            if r["share_binding"] == 0.0:
                assert r["uplift"] == 0.0
        models = docs["models"][f"models-{vid}"]["fit"]["floors"]
        assert models["cells"] == bd.floor_cells_block() and models["regime"] == "basel-iii-final"


def test_adversarial_a_negative_uplift_is_found(docs):
    rows = copy.deepcopy(docs["variants"]["dc-2009-10"]["outputs"]["floors_bite"]["rows"])
    assert floor_findings(rows) == []
    rows[0]["mean_after"] = {"value": rows[0]["mean_before"]["value"] - 0.02, "flag": "in-range"}
    found = floor_findings(rows)
    assert f"{rows[0]['segment_id']}: a negative uplift" in found
    other = copy.deepcopy(docs["variants"]["dc-2009-10"]["outputs"]["floors_bite"]["rows"])
    other[0]["floor"] = 0.3
    assert f"{other[0]['segment_id']}: not one of the 12 cells" in floor_findings(other)
