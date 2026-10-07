"""C04 on its committed artifacts (CT-403 to CT-409, CT-414, CT-415): the PD definitions, the agency statistics, the
generator families, the published answers, the attribution, the findings' evidence and the expected ranges, the
lineage, the lifetime check and the case page. Determinism is checked by recomputing one agency's outputs from the
CEREP answers in the device data root (when it holds them) and one family at a few repetitions, twice."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import numpy as np
import pytest

from pipeline.cases import c04_families, c04_published, c04_transitions as c04
from pipeline.io import cerep
from pipeline.stages.export import compact

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
DATA = os.environ.get("CONTRASTE_DATA")
CEREP_DIR = Path(DATA) / "raw" / "esma-cerep" if DATA else None
needs_cerep = pytest.mark.skipif(not (CEREP_DIR and CEREP_DIR.exists()),
                                 reason="the CEREP answers are fetched into the device data root (CONTRASTE_DATA)")
AGENCIES = {v["id"]: v["code"] for v in c04.AGENCY_VARIANTS}
FAMILIES = [f["id"] for f in c04.FAMILY_VARIANTS]


def _read(rel: str) -> dict:
    return json.loads((DERIVED / rel).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest() -> dict:
    return _read("manifests/C04.json")


@pytest.fixture(scope="module")
def variants(manifest) -> dict[str, dict]:
    return {a["variant_id"]: _read(a["path"]) for a in manifest["artifacts"] if a["role"] == "variant"}


def _close(a, b, tol=1e-9) -> bool:
    return a is None and b is None or (a is not None and b is not None and abs(a - b) <= tol * max(1.0, abs(b)))


def test_every_variant_baked(manifest, variants):
    assert set(variants) == {*AGENCIES, *FAMILIES, "published"}
    assert manifest["default_variant"] == "sp" and manifest["seed"] == 42


def test_pd_definitions(variants):
    """CT-403: D2 over tab 2's own cohort, D3 over the cohort, D4 and Keep from the transition page (none on Moody's);
    the long-run average is the mean of the yearly rates, its intervals hold the pooled rate."""
    for vid, code in AGENCIES.items():
        o = variants[vid]["outputs"]
        cohorts, pd = o["cohorts"], o["pd"]
        assert len(pd["d2"]) == len(pd["d3"]) == len(cohorts) > 0
        for k, c in enumerate(cohorts):
            for g in range(7):
                if c["defaulted"] is not None and c["defaulted_cohort"][g]:
                    assert _close(pd["d2"][k][g], c["defaulted"][g] / c["defaulted_cohort"][g], 1e-6), (vid, k, g)
                if c["events"] is not None and c["size"][g]:
                    assert _close(pd["d3"][k][g], c["events"][g] / c["size"][g], 1e-6), (vid, k, g)
        if code == "MDYGB":
            assert pd["d4"] is None and pd["keep"] is None and o["lra"].get("d4") is None
        else:
            for k, c in enumerate(cohorts):
                for g in range(7):
                    n = c["size"][g] - c["withdrawn"][g]
                    if n > 0:
                        assert _close(pd["d4"][k][g], c["counts"][g][7] / n, 1e-6), (vid, k, g)
        for d, rows in (("d2", pd["d2"]), ("d3", pd["d3"])):
            lra = o["lra"][d]
            for g in range(7):
                yearly = [r[g] for r in rows if r[g] is not None]
                if yearly:
                    assert _close(lra["rate"][g], float(np.mean(yearly)), 1e-6) and lra["cohorts"][g] == len(yearly)
                    for name in ("wald", "agresti_coull", "jeffreys"):
                        lo, hi = lra[name]["lower"][g], lra[name]["upper"][g]
                        assert 0.0 <= lo <= hi <= 1.0, (vid, d, name, g)
                    assert lra["jeffreys"]["lower"][g] <= lra["pooled_rate"][g] <= lra["jeffreys"]["upper"][g]


def test_agency_statistics(variants):
    """CT-404: the pooled matrix, its embedding, the four generators, mobility, the Markov tests and the semesters."""
    for vid, code in AGENCIES.items():
        o = variants[vid]["outputs"]
        p = np.asarray(o["pooled"]["matrix"])
        assert p.shape == (8, 8) and np.allclose(p.sum(axis=1), 1.0) and p[7, 7] == 1.0
        assert {"S", "theorem3", "exact_generator_excluded", "stochastically_monotone"} <= set(o["embedding"])
        assert o["generators"]["em"] is not None  # EM always has a generator; the others only where they exist
        for m in ("diagonal", "weighted", "jlt", "em"):
            g = o["generators"][m]
            if g is None:
                continue
            q = np.asarray(g["generator"])
            assert q.shape == (8, 8) and np.allclose(q.sum(axis=1), 0.0, atol=1e-9) and g["l1"] >= 0
            # no default category (Moody's), no PD from a generator: every grade's is null
            assert all(x is None for x in g["pd_1y"]) == (code == "MDYGB")
        if o["generators"]["jlt"] and o["generators"]["diagonal"]:
            assert o["generators"]["jlt"]["l1"] > o["generators"]["diagonal"]["l1"]
        n = len(o["cohorts"])
        assert len(o["mobility"]["svd"]) == len(o["mobility"]["trace"]) == len(o["mobility"]["labels"]) == n
        assert 0.0 <= o["homogeneity"]["annual"]["p_value"] <= 1.0
        assert len(o["homogeneity"]["reference"]) == n
        assert [e["label"] for e in o["ecb"]] == [c["label"] for c in o["cohorts"]]
        for row in o["semesters_vs_year"]:
            assert row["l1"] >= 0 and len(row["pd_annual"]) == 7


def test_generator_families(variants):
    """CT-405: every family on the EM generator of S&P's counts, its ladder and its rates with their MC errors."""
    q = np.asarray(variants["sp"]["outputs"]["generators"]["em"]["generator"])
    for fid in FAMILIES:
        o = variants[fid]["outputs"]
        assert o["kind"] == "generator" and o["family"] == fid
        assert np.allclose(np.asarray(o["generator"]["q"]), q, rtol=1e-6, atol=1e-12)
        assert o["rungs"] and (o["ladder"] is None) == (fid == "markov")
        for s in o.get("simulations") or []:
            for r in s["rates"].values():
                assert 0.0 <= r["rate"] <= 1.0 and r["n"] > 0 and r["se"] >= 0
    assert variants["thin"]["outputs"]["design"]["reps"] == 0 or variants["thin"]["outputs"]["design"].get("exact")


def test_published_answers(variants):
    """CT-406: the three papers recomputed beside their prints; no agency matrix of theirs in the artifact."""
    o = variants["published"]["outputs"]
    rows = o["irw"]["rows"]
    assert len(rows) == 9 and sum(r["agrees"] for r in rows) == 8
    assert round(o["irw"]["jlt_from_printed_generator"], 6) == 0.116900
    assert all(r["agrees"] for r in o["sr190"]["rows"]) and o["sr190"]["defaults"] == 15 and o["sr190"]["n"] == 531
    en = o["engelmann"]
    w = en["w_ttc"]
    assert all(c04_published.prints_as(v, pr, d) for v, pr, d in zip(w["recomputed"], w["printed"], w["decimals"], strict=True))
    assert c04_published.prints_as(100 * en["ttc_pd"]["recomputed"], 100 * en["ttc_pd"]["printed"], en["ttc_pd"]["decimals"] - 2)
    checks = {p["name"]: p["pd0"]["check"] for p in en["portfolios"]}
    assert checks == {"W_init": "printed digits", "W_init 2": "printed digits", "W tilde": "printed digits",
                      "W hat": "entry rounding"}
    nd = o["sr190"]["n_dagger"]
    assert nd["printed"] == [531.0, 84.3, 45.8] and o["irw"]["series_terms"] == 16
    text = json.dumps(o)
    assert "0.9276" not in text  # the first entry of Engelmann's matrix (11): never in the artifact


def test_attribution_and_definitions(manifest, variants):
    """CT-407: every CEREP-derived variant carries ESMA's attribution and the four definitions by name (D2, D3, D4,
    Keep; D4 and Keep null on Moody's), and the case page and the write-up quote ESMA's statement on definitions."""
    for vid, code in AGENCIES.items():
        o = variants[vid]["outputs"]
        assert o["attribution"] == "Source: ESMA CEREP; tables transformed by Contraste"
        assert [i["source"] for i in variants[vid]["provenance"]["inputs"]] == ["esma-cerep"]
        assert set(o["pd"]) == {"d2", "d3", "d4", "keep"}
        assert (o["pd"]["d4"] is None) == (o["pd"]["keep"] is None) == (code == "MDYGB")
    statement = "no deterministic definition of a default event has been set up"
    assert statement in (ROOT / "docs" / "cases" / "C04.md").read_text(encoding="utf-8")
    assert statement in (ROOT / "frontend" / "src" / "workbench" / "c04" / "selection.ts").read_text(encoding="utf-8")
    assert manifest["source_details"]["esma-cerep"]["attribution"] == "Source: ESMA CEREP; tables transformed by Contraste"


def test_findings_and_ranges(manifest, variants):
    """CT-408: every finding's evidence is in its artifact; the declared ranges are in the manifest."""
    for vid, v in variants.items():
        tests = {t["test_id"] for t in v["tests"]} | {f"{t['test_id']}@{t['model_id']}" for t in v["tests"]} | {
            f"{t['test_id']}@{t['model_id']}@{t['segment']}" for t in v["tests"]}
        rates = {f"rate:{s['key']}" for s in v["outputs"].get("simulations") or []}
        for f in v["findings"]:
            assert f["evidence"], (vid, f["id"])
            for e in f["evidence"]:
                assert e in tests or e in rates or e.startswith(("design:", "contract:")), (vid, f["id"], e)
    assert manifest["expect"] and set(manifest["expect"]) == set(c04.EXPECT)


def test_lineage_and_determinism(manifest, variants):
    """CT-409: the truth status of every kind; a family recomputed twice at a few repetitions is identical."""
    for vid, v in variants.items():
        want = "real-outcomes" if vid in AGENCIES else "published-answer" if vid == "published" else "synthetic-known-truth"
        assert v["provenance"]["truth_status"] == want and v["provenance"]["seed"] == manifest["seed"]
    q = np.asarray(variants["markov"]["outputs"]["generator"]["q"])
    obligors = variants["markov"]["outputs"]["generator"]["obligors"]
    a = c04_families.family_outputs("cycle", q, obligors, 42, reps=4)
    b = c04_families.family_outputs("cycle", q, obligors, 42, reps=4)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


@needs_cerep
def test_agency_outputs_reproduce_from_the_answers(variants):
    """CT-409: S&P's outputs recomputed from the cached CEREP answers equal the committed artifact."""
    got = cerep.read_agency(Path(DATA), "STPGB", c04.YEARS, c04.SEMESTER_YEARS, windows=c04.WINDOWS)
    out, _ = c04._agency("STPGB", got)
    committed = variants["sp"]["outputs"]
    mine = compact(json.loads(json.dumps(out)), exact=c04.EXACT)
    for key in ("cohorts", "pd", "lra", "pooled", "generators", "homogeneity", "lifetime"):
        assert mine[key] == committed[key], key


def test_lifetime_check(variants):
    """CT-415: every five-year window with data, observed beside the chained projections, by grade."""
    for vid, code in AGENCIES.items():
        rows = variants[vid]["outputs"]["lifetime"]
        assert rows, vid
        for r in rows:
            assert r["last"] - r["first"] == 4 and re.fullmatch(r"\d{4}-\d{4}", r["label"])
            obs, proj = r["observed"], r["projected"]
            assert len(obs["default_end"]) == len(proj["chain_state"]) == 7
            if code != "MDYGB":
                for g in range(7):
                    if r["size"][g] and obs["default_end"][g] is not None:
                        assert 0.0 <= obs["default_end"][g] <= 1.0
                    if r["size"][g] and proj["chain_state"][g] is not None:
                        assert 0.0 <= proj["chain_state"][g] <= 1.0


def test_case_page():
    """CT-414: the case page is complete (no pending section), linked from the case index, and cites its sources."""
    page = (ROOT / "docs" / "cases" / "C04.md").read_text(encoding="utf-8")
    assert "TODO" not in page and "pending" not in page.lower()
    for heading in ("## Why this case exists", "## Formalisation", "## Expected results", "## What the bake found",
                    "## Validation anchor", "## Notes"):
        assert heading in page, heading
    for cite in ("10.1111/1467-9965.00114", "Staff Report 190", "2401.08892", "ESMA65-8-10634", "EBA/GL/2017/16"):
        assert cite in page, cite
    assert "(C04.md)" in (ROOT / "docs" / "cases" / "README.md").read_text(encoding="utf-8")
