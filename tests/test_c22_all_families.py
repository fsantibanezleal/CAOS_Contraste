"""U16-P2 (BL-091, BL-075): C22 measures the size and the power of every registered p-value test, all families.

These tests read the committed artifacts (the bake runs once, outside the tests): the `null` variant holds every p-value
test the installed engine registers, at 4,000 repetitions and both levels; the `other-families` variant holds the
power of the 21 tests outside the five credit families against the engine's stated alternatives; the documented excess
of the engine is shown with its measured excess; the schema refuses a test id it does not know."""
from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
_CONTRACT_TESTS = str(ROOT / "tests" / "contracts")
if _CONTRACT_TESTS not in sys.path:
    sys.path.insert(0, _CONTRACT_TESTS)
import contract_schemas as cs  # noqa: E402

from pipeline.cases import c22_validator as c22  # noqa: E402

DERIVED = ROOT / "data" / "derived"
CREDIT = frozenset({"discrimination", "pd-calibration", "rating-system", "stability", "transitions"})
RULES = ("p", "p_le", "red", "alarm")
EXCESS_PAGE = "docs/portfolio/07_validation-tests.md"


def _read(rel: str) -> dict:
    return json.loads((DERIVED / rel).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest() -> dict:
    return _read("manifests/C22.json")


@pytest.fixture(scope="module")
def variants(manifest) -> dict[str, dict]:
    return {a["variant_id"]: _read(a["path"]) for a in manifest["artifacts"] if a["role"] == "variant"}


@pytest.fixture(scope="module")
def registered() -> dict[str, str]:
    """Every p-value test the installed engine registers, with its family: no family filter."""
    import riskvalidation.validation  # noqa: F401  (registers every test)
    from riskvalidation.core.registry import catalogue

    return {s.test_id: s.family for s in catalogue() if s.decision == "p_value"}


@pytest.fixture(scope="module")
def other_ids(registered) -> set[str]:
    return {t for t, f in registered.items() if f not in CREDIT}


def null_gaps(doc: dict, registered: set[str]) -> list[str]:
    """What is missing from the null variant (CT-301): a registered test, repetitions, a level, a histogram, a Monte Carlo SE."""
    o = doc["outputs"]
    gaps: list[str] = []
    measured = {s["test_id"] for s in o["simulations"] if s["key"].split("#")[0].endswith("@null")}
    gaps += [f"{t}: no size measurement" for t in sorted(registered - measured)]
    gaps += [f"{t}: not a registered p-value test" for t in sorted(measured - registered)]
    for s in o["simulations"]:
        if s["n_rep"] < 4000:
            gaps.append(f"{s['key']}: {s['n_rep']} repetitions")
        if not s["p_histogram"] or len(s["p_histogram"]) != 20:
            gaps.append(f"{s['key']}: no p-value histogram")
        for rule in c22.RULES:
            r = s["rates"].get(rule)
            if r is None:
                gaps.append(f"{s['key']}: no rate at {rule}")
            elif r["n"] != s["n_rep"] or not r["wilson_low"] <= r["rate"] <= r["wilson_high"] or r["undefined"]:
                gaps.append(f"{s['key']}: inconsistent rate at {rule}")
            elif abs(r["se"] - math.sqrt(r["rate"] * (1 - r["rate"]) / r["n"])) > 1e-6 * max(r["se"], 1e-9) + 1e-12:
                gaps.append(f"{s['key']}: Monte Carlo SE at {rule} is not sqrt(p(1-p)/n)")
    return gaps


def other_gaps(doc: dict, other_ids: set[str]) -> list[str]:
    """What is wrong with the other-families variant (CT-314): two points per study, 2,000 repetitions, one seed each."""
    o = doc["outputs"]
    gaps: list[str] = []
    points: dict[tuple, dict[int, dict]] = {}
    for s in o["simulations"]:
        points.setdefault((s["test_id"], s["study"]["index"] if s["study"] else -1), {})[s["severity"]] = s
    gaps += [f"{t}: no study" for t in sorted(other_ids - {k[0] for k in points})]
    for key, pair in points.items():
        if set(pair) != {0, 1}:
            gaps.append(f"{key}: points {sorted(pair)} instead of 0 and 1")
            continue
        if pair[0]["study"]["arm"] != "null" or pair[1]["study"]["arm"] != "alternative":
            gaps.append(f"{key}: the arms are not the null and the alternative")
        for s in pair.values():
            if s["n_rep"] != 2000 or s["study"]["departure"] != "two-point":
                gaps.append(f"{s['key']}: {s['n_rep']} repetitions, departure {s['study']['departure']}")
            if s["seed"] != c22._seed(doc["provenance"]["seed"], f"other-families:{s['key']}"):
                gaps.append(f"{s['key']}: seed not derived from the case seed")
    seeds = [s["seed"] for s in o["simulations"]]
    if len(set(seeds)) != len(seeds):
        gaps.append("two simulations share a seed")
    return gaps


def excess_gaps(doc: dict) -> list[str]:
    """The engine's documented excess is shown with its measure and page, and an undocumented one is a finding (CT-316)."""
    o = doc["outputs"]
    gaps: list[str] = []
    mc = next((s for s in o["simulations"] if s["test_id"] == "portfolio.mc_convergence"), None)
    if mc is None or not (mc["study"] or {}).get("excess"):
        gaps.append("portfolio.mc_convergence: the engine's documented excess is not shown")
    else:
        ex = mc["study"]["excess"]
        if ex["page"] != EXCESS_PAGE or not ex["engine"]["en"] or not ex["engine"]["es"]:
            gaps.append("portfolio.mc_convergence: the engine page is not named")
        if abs(ex["measured"] - mc["rates"]["p<0.01"]["rate"]) > 1e-9 or abs(ex["excess"] - (ex["measured"] - ex["bound"])) > 1e-6:
            gaps.append("portfolio.mc_convergence: the shown excess is not the measured one")
    findings = {f["id"]: f for f in doc["findings"]}
    for s in o["simulations"]:
        if not s.get("study") or s["study"].get("excess"):
            continue
        over = [a for a in c22.LEVELS if s["rates"][f"p<{a:g}"]["rate"] > o["size_bounds"][f"p<{a:g}"]]
        f = findings.get("F-OTHER-SIZE")
        if over and not (f and f["status"] == "open" and f"rate:{s['key']}" in f["evidence"]):
            gaps.append(f"{s['key']}: exceeds its bound at {over} without an open finding")
    return gaps


def test_the_catalogue_and_the_null_variant_agree_without_a_family_filter(variants, registered):
    """CT-301: every registered p-value test of the installed engine is in the null variant, and nothing else is."""
    assert null_gaps(variants["null"], set(registered)) == []
    assert len(registered) == 42 and len({t for t, f in registered.items() if f not in CREDIT}) == 21


def test_the_null_rows_of_the_other_families_carry_the_credit_fields(variants, other_ids):
    """The 25 studies of the 21 tests carry what the credit tests carry, and the study block that names the engine's study."""
    null = variants["null"]["outputs"]
    rows = [s for s in null["simulations"] if s["test_id"] in other_ids]
    assert len(rows) == 25 and {s["test_id"] for s in rows} == other_ids
    for s in rows:
        st = s["study"]
        assert st["arm"] == "null" and st["departure"] == "null" and st["rule"] in RULES and st["rule_label"] in s["rates"]
        assert st["text"]["en"] and st["text"]["es"] and st["label"]["en"] and st["label"]["es"]
        assert s["panel"] in {p["id"] for p in null["panels"]}
        assert s["seed"] == c22._seed(variants["null"]["provenance"]["seed"], f"null:{s['key']}")
    assert all(s["study"] is None for s in null["simulations"] if s["test_id"] not in other_ids)
    assert null["size_bounds"]["p<0.05"] == pytest.approx(c22.size_bound(0.05, 4000))


def test_the_null_panels_say_size_and_cover_the_new_families(variants):
    null = variants["null"]["outputs"]
    assert {p["measures"] for p in null["panels"]} == {"size"}
    ids = {p["id"] for p in null["panels"]}
    assert {"calibration", "discrimination", "stability", "rating", "transitions", "settings"} <= ids
    assert {"ccr", "ifrs9", "lgd-ead", "market-var", "market-es", "portfolio-credit", "fairness", "ml"} <= ids


def test_the_documented_excess_is_shown_with_its_measure_and_its_engine_page(variants):
    """The engine's DOCUMENTED_EXCESS (portfolio.mc_convergence) is not hidden: its row carries the measured size, the bound,
    the excess and the engine page that states it; no other row of the other families carries one."""
    rows = [s for s in variants["null"]["outputs"]["simulations"] if s.get("study")]
    flagged = [s for s in rows if s["study"].get("excess")]
    assert [s["test_id"] for s in flagged] == ["portfolio.mc_convergence"]
    ex = flagged[0]["study"]["excess"]
    assert ex["page"] == EXCESS_PAGE and ex["repository"] == "fsantibanezleal/CAOS_RiskValidation"
    assert ex["level"] == 0.01 and ex["bound"] == pytest.approx(c22.size_bound(0.01, flagged[0]["n_rep"]))
    assert ex["measured"] == flagged[0]["rates"]["p<0.01"]["rate"]
    assert ex["excess"] == pytest.approx(ex["measured"] - ex["bound"])
    assert ex["exceeds"] == (ex["measured"] > ex["bound"])
    assert ex["engine"]["en"] and ex["engine"]["es"]
    findings = {f["id"]: f for f in variants["null"]["findings"]}
    assert "rate:portfolio.mc_convergence@null" in findings["F-OTHER-MC-EXCESS"]["evidence"]


def test_no_new_test_exceeds_its_bound_without_a_finding(variants):
    """A measured excess of a test the engine does not document is a finding that stays open, never a pass."""
    assert excess_gaps(variants["null"]) == []


def test_the_other_families_variant_holds_two_points_per_study(variants, manifest, other_ids):
    """The power of the 21 tests against their stated alternatives: no Study exposes its departure as a parameter, so each
    is measured at two points, the null (severity 0) and the stated alternative (severity 1), 2,000 repetitions each."""
    assert "other-families" in variants
    entry = next(a for a in manifest["artifacts"] if a["variant_id"] == "other-families")
    assert entry["role"] == "variant" and entry["truth_status"] == "synthetic-known-truth"
    doc = variants["other-families"]
    o = doc["outputs"]
    assert o["family"] == "other-families" and o["ladder"]["values"] == [0, 1]
    assert doc["tests"] == [] and doc["findings"] and doc["impact"]
    assert {p["measures"] for p in o["panels"]} == {"power"}
    assert other_gaps(doc, other_ids) == []
    assert len(o["simulations"]) == 50 and {s["test_id"] for s in o["simulations"]} == other_ids
    for s in o["simulations"]:
        assert s["scenario"]["en"] and s["scenario"]["es"]
    assert o["size_bounds"]["p<0.05"] == pytest.approx(c22.size_bound(0.05, 2000))


def test_the_power_of_each_study_is_above_its_size(variants):
    """The stated alternative is detectable: the rate at the alternative exceeds the rate at the null for every study."""
    o = variants["other-families"]["outputs"]
    pairs: dict[tuple, dict[int, dict]] = {}
    for s in o["simulations"]:
        pairs.setdefault((s["test_id"], s["study"]["index"]), {})[s["severity"]] = s
    assert len(pairs) == 25
    for key, p in pairs.items():
        assert p[1]["rates"]["p<0.05"]["rate"] > p[0]["rates"]["p<0.05"]["rate"], key


def test_findings_and_impact_of_the_new_variant_cite_their_rates(variants):
    keys = {f"rate:{s['key']}" for s in variants["other-families"]["outputs"]["simulations"]}
    for f in variants["other-families"]["findings"]:
        assert f["evidence"] and all(e in keys for e in f["evidence"]), f["id"]
    assert all(k.startswith("other_") for k in variants["other-families"]["impact"])


def test_the_spanish_texts_carry_their_accents(variants):
    es = [s["scenario"]["es"] for v in variants.values() for s in v["outputs"]["simulations"] if s.get("study")]
    assert len(es) == 75
    accents = "áéíóúñ"
    assert any(c in t for t in es for c in accents)
    assert not any(" - " in t or chr(0x2014) in t or chr(0x2192) in t for t in es)
    # an accented word is never written without its accent
    assert not any(w in t for t in es for w in ("estimacion", "perdida", " anos", "dias "))


def test_the_schema_refuses_an_unknown_test_id_family_and_study(variants):
    """The test ids, the families and the panels are closed enums of the schema (c22-variant 2.0.0)."""
    for variant in ("null", "other-families"):
        doc = variants[variant]
        assert cs.errors("c22/variant", doc) == [], variant
        bad = copy.deepcopy(doc)
        bad["outputs"]["simulations"][0]["test_id"] = "pd.not_a_registered_test"
        assert any("pd.not_a_registered_test" in e or "is not one of" in e for e in cs.errors("c22/variant", bad))
        bad = copy.deepcopy(doc)
        bad["outputs"]["family"] = "not-a-family"
        assert cs.errors("c22/variant", bad)
        bad = copy.deepcopy(doc)
        bad["outputs"]["panels"][0]["id"] = "not-a-panel"
        assert cs.errors("c22/variant", bad)
    bad = copy.deepcopy(variants["null"])
    study_row = next(s for s in bad["outputs"]["simulations"] if s.get("study"))
    study_row["study"]["rule"] = "z"
    assert cs.errors("c22/variant", bad)
    bad = copy.deepcopy(variants["null"])
    next(s for s in bad["outputs"]["simulations"] if s.get("study"))["study"]["surprise"] = 1
    assert cs.errors("c22/variant", bad)


def test_the_models_artifact_names_the_engine_studies(manifest):
    """c22-models 2.0.0: the generators of the 21 tests and the engine's 25 named studies, with their fixed arguments."""
    models = _read(next(a["path"] for a in manifest["artifacts"] if a["role"] == "models"))
    assert cs.errors("c22/models", models) == []
    fit = models["fit"]
    assert len(fit["studies"]) == 25
    assert len({s["test_id"] for s in fit["studies"]}) == 21
    classes = {m["details"]["class"] for m in models["model"] if m["family"] == "generator"}
    assert {"PfeSeries", "StageTransitions", "LgdCalibration", "DownturnLgd", "EsResiduals", "LhpLossRates", "McQuantile",
            "CreditRiskPlusSample", "VarHits", "EsLosses", "PitSeries", "ThresholdBiasPlant", "CovariateShiftPlant",
            "ExchangeabilityBreakPlant"} <= classes
    bad = copy.deepcopy(models)
    bad["fit"]["studies"][0]["test_id"] = "no.such_test"
    assert cs.errors("c22/models", bad)
    bad = copy.deepcopy(models)
    bad["fit"]["parity"][0]["test_id"] = "stability.ks"
    assert cs.errors("c22/models", bad)


def test_the_expected_ranges_of_the_new_values_hold(manifest):
    expect = manifest["expect"]
    assert set(expect) == set(c22.EXPECT)
    assert any(k.startswith("other_") for k in expect)
    for k, (lo, hi) in c22.EXPECT.items():
        assert expect[k] == [lo, hi]
    assert np.isfinite([x for r in c22.EXPECT.values() for x in r]).all()
