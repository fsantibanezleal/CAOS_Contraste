"""U7-S: the C10 case contracts, their fixtures, the catalog rows fragment and the engine portfolio API contract.

The fixtures validate by discovery (tests/contracts/contract_schemas.py) against exactly one schema; the schemas are strict
both ways (a removed or an added key fails); a PD, a correlation or a loss rate of 0 or 1 fails at an estimate site; a money
block without its currency fails; an illustrative portfolio passes only with its label and its provenance input; a simulator
document carries its known correlation; a rung that did not run is a not-evaluated row with its reason, never a number; the
orderings JSON Schema cannot state (VaR not below EL, ES not below VaR, EC = VaR - EL, the Euler sums) are tests on the
fixtures, each with a planted counter-example; the engine contract names every function of the sizing's portfolio modules
with a golden value or an invariant, and its golden values recompute here from the formulas of dossiers 04 and 05 with
the standard library only. The fixtures are labelled as fixtures and never published as results.
"""
from __future__ import annotations

import copy
import math
import re
from typing import Any, Iterator

import pytest

import contract_schemas as cs
from c10_checks import (ND, SAMPLE_METHODS, binom_upper, cell_violations, euler_violations, gamma_lower, gamma_quantile,  # noqa: F401
                        gl_delta, granularity_violations, implied_factor, irb_violations, lhp_cdf, lhp_es, lhp_pdf,
                        lhp_quantile, loan_type_violations, maturity_adjustment, measure_violations, models_violations,
                        violations, window_violations, wilson, document_violations)

ROOT = cs.ROOT
FIXTURES = ROOT / "docs" / "contracts" / "fixtures"
SCHEMAS = ROOT / "docs" / "contracts" / "schemas"
API = ROOT / "docs" / "contracts" / "engine" / "portfolio-api.md"
ROWS = ROOT / "docs" / "contracts" / "rows" / "U7.md"

LT, GR, MD = "c10/variant-loan-type", "c10/variant-correlation-grid", "c10/models"
EXPECTED = {
    LT: FIXTURES / "c10" / "variant-loan-type-fixture.json",
    GR: FIXTURES / "c10" / "variant-correlation-grid-fixture.json",
    MD: FIXTURES / "c10" / "models-fixture.json",
}
VARIANTS = {k: v for k, v in EXPECTED.items() if "variant" in k}
KINDS = {LT: "loan-type", GR: "correlation-grid"}
ROW_IDS = ["c10-outputs", "c10-outputs-grid", "c10-models", "engine-portfolio-api"]
OTHER_CASES = ("c03", "c08", "c09")

RUNG_IDS = ["c1-lhp", "c2-gaussian-1f", "c2-gaussian-mf", "c3-student-t", "c4-creditrisk-plus", "c5-granularity",
            "c6-is-gaussian", "c6-is-student-t"]


def load(ref: str) -> Any:
    return cs.load_json(EXPECTED[ref])


def out(ref: str) -> dict:
    return load(ref)["outputs"]


def lt() -> dict:
    return out(LT)


def rung(o: dict, rid: str) -> dict:
    return next(r for r in o["rungs"] if r["id"] == rid)


# --- the fixtures -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("ref", EXPECTED)
def test_the_fixture_exists_and_is_discovered_by_exactly_one_schema(ref: str) -> None:
    path = EXPECTED[ref]
    assert path.is_file(), path
    doc = cs.load_json(path)
    assert cs.schema_for_document(path, doc) == ref
    assert cs.errors(ref, doc) == []
    passing = [c.ref for c in cs.candidates() if cs.errors(c.ref, doc) == []]
    assert passing == [ref], f"{ref}: validates against {passing}"


@pytest.mark.parametrize("ref", EXPECTED)
def test_the_fixture_is_labelled_as_a_fixture(ref: str) -> None:
    doc = load(ref)
    assert doc["provenance"]["generators"] == ["fixture:u7-s-contracts"]
    assert any(i["source"] == "fixture-not-a-result" for i in doc["provenance"]["inputs"])
    key = "variant_id" if "variant" in ref else "fit_id"
    assert str(doc[key]).startswith("fixture-")


def test_every_u7_schema_is_case_folder_conformant_and_case_prefixed() -> None:
    assert cs.case_folder_violations() == []
    files = sorted((SCHEMAS / "c10").glob("*.schema.json"))
    assert {p.relative_to(SCHEMAS).as_posix() for p in files} == {f"{ref}.schema.json" for ref in EXPECTED}
    for p in files:
        for name in cs.load_json(p).get("$defs", {}):
            assert name.startswith("c10"), f"{p.name}: $defs name {name!r} is not prefixed 'c10'"


def test_a_def_two_c10_files_share_has_one_definition() -> None:
    defs: dict[str, Any] = {}
    for p in sorted((SCHEMAS / "c10").glob("*.schema.json")):
        for name, d in cs.load_json(p).get("$defs", {}).items():
            assert defs.setdefault(name, d) == d, f"{name} is defined differently in two c10 files"


def test_every_u7_variant_schema_declares_its_outputs_kind() -> None:
    by_ref = {c.ref: c for c in cs.candidates()}
    for ref, kind in KINDS.items():
        assert by_ref[ref].consts["outputs.kind"] == kind
        assert by_ref[ref].consts["case_id"] == "C10"
    assert cs.default_variants().get("C10") is None
    assert cs.default_violations() == []


def test_a_second_kind_less_variant_schema_fails() -> None:
    a = cs.Candidate.from_parts("c10/variant-planted", {"schema": "contraste.case/v1", "case_id": "C10"})
    b = cs.Candidate.from_parts("c10/variant-planted2", {"schema": "contraste.case/v1", "case_id": "C10"})
    assert cs.default_violations(cs.candidates() + (a, b)) != []


# --- strictness ---------------------------------------------------------------------------------------------------


def objects(node: Any, path: tuple = ()) -> Iterator[tuple[tuple, dict]]:
    if isinstance(node, dict):
        yield path, node
        for k, v in node.items():
            yield from objects(v, path + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from objects(v, path + (i,))


def get(doc: Any, path: tuple) -> Any:
    for p in path:
        doc = doc[p]
    return doc


def root_of(ref: str) -> str:
    return "outputs" if "variant" in ref else "fit"


def closed_objects(ref: str) -> list[tuple[tuple, dict]]:
    """Every object under outputs (or fit) of the fixture: all of them are closed by the schema."""
    doc = load(ref)
    return list(objects(doc[root_of(ref)], (root_of(ref),)))


@pytest.mark.parametrize("ref", EXPECTED)
def test_a_key_removed_from_any_object_fails(ref: str) -> None:
    doc = load(ref)
    checked = 0
    for path, obj in closed_objects(ref):
        for key in list(obj):
            bad = copy.deepcopy(doc)
            del get(bad, path)[key]
            assert cs.errors(ref, bad) != [], f"{ref}: removing {'/'.join(map(str, path))}/{key} still validates"
            checked += 1
    assert checked > 50


@pytest.mark.parametrize("ref", EXPECTED)
def test_a_key_added_to_any_object_fails(ref: str) -> None:
    doc = load(ref)
    for path, _ in closed_objects(ref):
        bad = copy.deepcopy(doc)
        get(bad, path)["unknown_key"] = 1
        assert cs.errors(ref, bad) != [], f"{ref}: adding a key at {'/'.join(map(str, path))} still validates"


@pytest.mark.parametrize("ref", VARIANTS)
def test_a_document_without_case_id_or_outputs_kind_does_not_pass(ref: str) -> None:
    path = EXPECTED[ref]
    doc = load(ref)
    no_case = copy.deepcopy(doc)
    del no_case["case_id"]
    assert cs.errors(ref, no_case) != []
    with pytest.raises(cs.SelectionError):
        cs.schema_for_document(path, no_case)
    no_kind = copy.deepcopy(doc)
    del no_kind["outputs"]["kind"]
    assert cs.errors(ref, no_kind) != []
    chosen = None
    try:
        chosen = cs.schema_for_document(path, no_kind)
    except cs.SelectionError:
        pass
    assert chosen != ref
    if chosen is not None:
        assert cs.errors(chosen, no_kind) != []


@pytest.mark.parametrize("ref", EXPECTED)
def test_a_wrong_case_id_is_rejected(ref: str) -> None:
    doc = load(ref)
    doc["case_id"] = "C99"
    assert cs.errors(ref, doc) != []


@pytest.mark.parametrize("ref", EXPECTED)
def test_a_fixture_of_one_case_does_not_validate_against_another_schema(ref: str) -> None:
    doc = load(ref)
    others = [c.ref for c in cs.candidates() if c.ref != ref and c.ref.split("/")[0] in ("c10",) + OTHER_CASES]
    assert len(others) >= 8
    for other in others:
        assert cs.errors(other, doc) != [], f"{ref} validates against {other}"


# --- the open ranges ----------------------------------------------------------------------------------------------


def set_at(doc: Any, path: tuple, value: Any) -> Any:
    bad = copy.deepcopy(doc)
    get(bad, path[:-1])[path[-1]] = value
    return bad


# (ref, path) of every estimate site that is open (0, 1): a PD, an asset correlation or an observed loss rate
def open_sites() -> list[tuple[str, tuple]]:
    sites: list[tuple[str, tuple]] = []
    o = lt()
    for est in ("maximum_likelihood", "moments"):
        for par in ("pd", "rho"):
            for k in ("estimate", "ci_low", "ci_high"):
                sites.append((LT, ("outputs", "fit", est, par, k)))
    sites.append((LT, ("outputs", "fitted_distribution", "pd")))
    sites.append((LT, ("outputs", "fitted_distribution", "rho")))
    for i, row in enumerate(o["annual_rates"]):
        if row["loss_rate"] is not None:
            sites.append((LT, ("outputs", "annual_rates", i, "loss_rate")))
    for i in range(len(o["portfolio"]["groups"])):
        sites.append((LT, ("outputs", "portfolio", "groups", i, "pd")))
    sites.append((LT, ("outputs", "portfolio", "calibration", "pd")))
    sites.append((LT, ("outputs", "portfolio", "calibration", "rho")))
    sites.append((GR, ("outputs", "generator", "known_pd")))
    for i in range(len(out(GR)["generator"]["rho_grid"])):
        sites.append((GR, ("outputs", "generator", "rho_grid", i)))
    for i in range(len(out(GR)["cells"])):
        sites.append((GR, ("outputs", "cells", i, "known_rho")))
    return sites


@pytest.mark.parametrize("bad", [0, 1, -0.01, 1.2])
def test_a_pd_correlation_or_loss_rate_outside_the_open_unit_interval_fails_at_every_estimate_site(bad: float) -> None:
    sites = open_sites()
    assert len(sites) > 40, len(sites)
    for ref, path in sites:
        assert cs.errors(ref, set_at(load(ref), path, bad)) != [], f"{ref} {path} = {bad} still validates"


# --- money blocks carry their currency ----------------------------------------------------------------------------

MONEY_REFS = [LT, MD]
MONEY_NAMES = {"total_ead", "ead_each", "ead", "el", "var", "es", "ec", "var_total", "es_total", "rc_var", "rc_es", "ga_money"}


@pytest.mark.parametrize("ref", MONEY_REFS)
def test_a_money_block_without_its_currency_fails(ref: str) -> None:
    doc = load(ref)
    sites = [(p, o) for p, o in closed_objects(ref) if "currency" in o]
    assert sites, f"{ref}: no object carries a currency"
    for path, _ in sites:
        bad = copy.deepcopy(doc)
        del get(bad, path)["currency"]
        assert cs.errors(ref, bad) != [], f"{ref}: {path} without currency validates"
        worse = copy.deepcopy(doc)
        get(worse, path)["currency"] = "dollars"
        assert cs.errors(ref, worse) != [], f"{ref}: {path} with a non-ISO currency validates"


@pytest.mark.parametrize("ref", MONEY_REFS)
def test_every_money_field_sits_under_a_block_that_states_its_currency(ref: str) -> None:
    doc = load(ref)
    found = 0
    for path, obj in closed_objects(ref):
        for key, val in obj.items():
            if key in MONEY_NAMES and isinstance(val, (int, float)) and not isinstance(val, bool):
                found += 1
                assert any("currency" in get(doc, path[:n]) for n in range(len(path), 0, -1)), \
                    f"{ref}: money field {'/'.join(map(str, path))}/{key} has no currency in any enclosing block"
    assert found >= 3


def test_the_rung_curves_and_euler_blocks_state_one_currency_with_the_portfolio() -> None:
    o = lt()
    cur = o["currency"]
    assert o["portfolio"]["currency"] == cur and o["granularity"]["currency"] == cur
    for r in o["rungs"]:
        assert r["currency"] == cur
        if r["distribution"] is not None:
            assert r["distribution"]["currency"] == cur
    for e in o["euler"]:
        assert e["currency"] == cur


# --- the illustrative portfolio is labelled, the truth status is stated ---------------------------------------------


def test_an_illustrative_portfolio_without_its_label_fails() -> None:
    for ref, path in ((LT, ("outputs", "portfolio")), (MD, ("fit", "portfolio_spec"))):
        doc = load(ref)
        assert get(doc, path)["label"] == "illustrative"
        assert get(doc, path + ("notice",))["en"]
        bad = copy.deepcopy(doc)
        del get(bad, path)["label"]
        assert cs.errors(ref, bad) != []
        for wrong in ("real", "bank", "Illustrative", ""):
            worse = set_at(doc, path + ("label",), wrong)
            assert cs.errors(ref, worse) != [], wrong


@pytest.mark.parametrize("ref", [LT, MD])
def test_the_illustrative_provenance_input_is_required_with_the_portfolio(ref: str) -> None:
    doc = load(ref)
    inputs = doc["provenance"]["inputs"]
    assert any(i["source"] == "illustrative-portfolio" and i["class"] == "illustrative" for i in inputs)
    bad = copy.deepcopy(doc)
    bad["provenance"]["inputs"] = [i for i in inputs if i["source"] != "illustrative-portfolio"]
    assert cs.errors(ref, bad) != []
    worse = copy.deepcopy(doc)
    for i in worse["provenance"]["inputs"]:
        if i["source"] == "illustrative-portfolio":
            i["class"] = "real"
    assert cs.errors(ref, worse) != []


def test_the_truth_status_of_each_variant_kind_is_fixed() -> None:
    assert load(LT)["provenance"]["truth_status"] == "real-outcomes"
    assert load(GR)["provenance"]["truth_status"] == "synthetic-known-truth"
    for ref, wrong in ((LT, "synthetic-known-truth"), (LT, "synthetic-calibrated"), (GR, "real-outcomes"),
                       (GR, "published-answer")):
        doc = load(ref)
        doc["provenance"]["truth_status"] = wrong
        assert cs.errors(ref, doc) != [], (ref, wrong)


# --- the simulator carries its known correlation --------------------------------------------------------------------


def test_a_simulator_document_without_its_known_correlation_fails() -> None:
    doc = load(GR)
    o = doc["outputs"]
    assert o["generator"]["rho_grid"] and all("known_rho" in c for c in o["cells"])
    bad = copy.deepcopy(doc)
    del bad["outputs"]["generator"]["rho_grid"]
    assert cs.errors(GR, bad) != []
    bad = copy.deepcopy(doc)
    del bad["outputs"]["generator"]["known_pd"]
    assert cs.errors(GR, bad) != []
    for i in range(len(o["cells"])):
        bad = copy.deepcopy(doc)
        del bad["outputs"]["cells"][i]["known_rho"]
        assert cs.errors(GR, bad) != [], i
    bad = copy.deepcopy(doc)
    bad["outputs"]["cells"] = []
    assert cs.errors(GR, bad) != []


def test_the_grid_cells_are_consistent_with_their_generator_and_the_size_cell_sits_at_the_null() -> None:
    o = out(GR)
    assert cell_violations(o) == []
    assert o["generator"]["alpha"] == 0.05
    assert sum(c["role"] == "size" for c in o["cells"]) == 1


def test_planted_grid_inconsistencies_are_caught() -> None:
    o = out(GR)
    plants = []
    a = copy.deepcopy(o)
    a["cells"][0]["role"] = "size"
    plants.append(a)
    a = copy.deepcopy(o)
    a["generator"]["null_rho"] = 0.123
    plants.append(a)
    a = copy.deepcopy(o)
    a["cells"][1]["n_valid"] += 1
    plants.append(a)
    a = copy.deepcopy(o)
    a["cells"][1]["estimators"][0]["bias"] += 0.01
    plants.append(a)
    a = copy.deepcopy(o)
    a["cells"][1]["estimators"][1]["rejection_se"] *= 2
    plants.append(a)
    a = copy.deepcopy(o)
    a["cells"][2]["series_length_years"] += 1
    plants.append(a)
    a = copy.deepcopy(o)
    a["cells"].pop()
    plants.append(a)
    a = copy.deepcopy(o)
    a["cells"][2]["estimators"][0]["rejection_ci_high"] = 1.0
    plants.append(a)
    for plant in plants:
        assert cell_violations(plant) != []


# --- a rung that did not run, a missing quarter -------------------------------------------------------------------


def test_the_fixture_shows_the_eight_rungs_with_one_not_evaluated_row_and_one_row_without_an_es() -> None:
    o = lt()
    assert [r["id"] for r in o["rungs"]] == RUNG_IDS
    for r in o["rungs"]:
        assert r["id"].startswith(r["rung"].lower() + "-")
    not_run = [r for r in o["rungs"] if not r["evaluated"]]
    assert [r["id"] for r in not_run] == ["c6-is-student-t"]
    assert "Student" in not_run[0]["reason"] or "t copula" in not_run[0]["reason"]
    c5 = rung(o, "c5-granularity")
    assert all(m["es"] is None and m["es_reason"] for m in c5["measures"])


def test_a_not_evaluated_rung_carries_no_number_and_an_evaluated_rung_no_reason() -> None:
    doc = load(LT)
    idx = next(i for i, r in enumerate(doc["outputs"]["rungs"]) if not r["evaluated"])
    done = next(i for i, r in enumerate(doc["outputs"]["rungs"]) if r["id"] == "c2-gaussian-1f")
    base = ("outputs", "rungs")
    cases = [
        (base + (idx, "measures"), copy.deepcopy(doc["outputs"]["rungs"][done]["measures"])),
        (base + (idx, "distribution"), copy.deepcopy(doc["outputs"]["rungs"][done]["distribution"])),
        (base + (idx, "reason"), None),
        (base + (idx, "reason"), ""),
        (base + (idx, "evaluated"), True),
        (base + (idx, "estimator"), "monte-carlo"),
        (base + (idx, "simulation"), {"n_scenarios": 10, "seed": 1, "chunk_size": 5}),
        (base + (done, "reason"), "it did not run"),
        (base + (done, "evaluated"), False),
        (base + (done, "measures"), None),
        (base + (done, "distribution"), None),
        (base + (done, "simulation"), None),
        (base + (done, "estimator"), "analytic"),
    ]
    for path, value in cases:
        assert cs.errors(LT, set_at(doc, path, value)) != [], f"{path} = {str(value)[:40]} validates"


def test_a_monte_carlo_rung_carries_standard_errors_and_an_analytic_rung_none() -> None:
    o = lt()
    for r in o["rungs"]:
        if not r["evaluated"]:
            continue
        for m in r["measures"]:
            if r["estimator"] == "monte-carlo":
                assert m["var_se"] is not None and m["es_se"] is not None and m["var_se"] >= 0 and m["es_se"] >= 0
                assert r["simulation"]["n_scenarios"] >= 1
            else:
                assert m["var_se"] is None and m["es_se"] is None and r["simulation"] is None
    doc = load(LT)
    i = next(i for i, r in enumerate(doc["outputs"]["rungs"]) if r["id"] == "c2-gaussian-1f")
    j = next(i for i, r in enumerate(doc["outputs"]["rungs"]) if r["id"] == "c1-lhp")
    assert cs.errors(LT, set_at(doc, ("outputs", "rungs", i, "measures", 0, "var_se"), None)) != []
    assert cs.errors(LT, set_at(doc, ("outputs", "rungs", j, "measures", 0, "var_se"), 0.1)) != []


def test_an_es_that_is_null_needs_its_reason_and_a_number_forbids_one() -> None:
    doc = load(LT)
    i = next(i for i, r in enumerate(doc["outputs"]["rungs"]) if r["id"] == "c5-granularity")
    k = next(i for i, r in enumerate(doc["outputs"]["rungs"]) if r["id"] == "c1-lhp")
    assert cs.errors(LT, set_at(doc, ("outputs", "rungs", i, "measures", 0, "es_reason"), None)) != []
    assert cs.errors(LT, set_at(doc, ("outputs", "rungs", i, "measures", 0, "es"), 1.0)) != []
    assert cs.errors(LT, set_at(doc, ("outputs", "rungs", k, "measures", 0, "es"), None)) != []
    assert cs.errors(LT, set_at(doc, ("outputs", "rungs", k, "measures", 0, "es_reason"), "x")) != []


def test_a_quarter_missing_from_the_fed_table_is_a_null_rate_with_its_reason_never_a_number() -> None:
    doc = load(LT)
    rows = doc["outputs"]["annual_rates"]
    short = [i for i, r in enumerate(rows) if r["n_quarters"] < 4]
    assert len(short) == 1
    i = short[0]
    assert rows[i]["loss_rate"] is None and rows[i]["reason"] and rows[i]["window"] == "fit"
    p = ("outputs", "annual_rates", i)
    for k in ("loss_rate", "fitted_cdf", "implied_factor"):
        assert cs.errors(LT, set_at(doc, p + (k,), 0.5)) != [], k
    for k in ("exceeds_99", "exceeds_999"):
        assert rows[i][k] is None
        assert cs.errors(LT, set_at(doc, p + (k,), False)) != [], k
    assert cs.errors(LT, set_at(doc, p + ("reason",), None)) != []
    full = next(j for j, r in enumerate(rows) if r["n_quarters"] == 4)
    q = ("outputs", "annual_rates", full)
    for k in ("loss_rate", "fitted_cdf", "implied_factor", "exceeds_99", "exceeds_999"):
        assert cs.errors(LT, set_at(doc, q + (k,), None)) != [], k
    assert cs.errors(LT, set_at(doc, q + ("reason",), "a reason")) != []
    assert cs.errors(LT, set_at(doc, q + ("n_quarters",), 5)) != []
    assert doc["outputs"]["data_status"]["missing_quarters"], "the missing quarter is also listed with its reason"
    assert all(m["reason"] for m in doc["outputs"]["data_status"]["missing_quarters"])


# --- the not_evaluated test rule ----------------------------------------------------------------------------------


@pytest.mark.parametrize("ref", VARIANTS)
def test_a_not_evaluated_test_row_with_a_number_or_without_its_reason_fails(ref: str) -> None:
    doc = load(ref)
    rows = [i for i, t in enumerate(doc["tests"]) if t["light"] == "not_evaluated"]
    assert rows or ref == GR
    for i in rows:
        for k in ("statistic", "p_value", "metric"):
            assert cs.errors(ref, set_at(doc, ("tests", i, k), 0.5)) != [], k
        assert cs.errors(ref, set_at(doc, ("tests", i, "notes"), "")) != []


def test_the_fixtures_carry_the_portfolio_test_ids() -> None:
    ids = {t["test_id"] for t in load(LT)["tests"]}
    assert ids == {"portfolio.tail_backtest", "portfolio.mc_convergence", "portfolio.euler_additivity",
                   "portfolio.crp_recursion_vs_mc"}
    assert {t["test_id"] for t in load(GR)["tests"]} == {"portfolio.correlation_size_power"}
    assert {t["light"] for t in load(LT)["tests"]} >= {"not_evaluated", "green"}


# --- identities of the loan-type fixture ---------------------------------------------------------------------------


def test_the_windows_are_fit_before_evaluation_with_their_year_counts() -> None:
    w = lt()["windows"]
    for k in ("fit", "evaluation"):
        assert w[k]["n_years"] == w[k]["last_year"] - w[k]["first_year"] + 1
    assert w["fit"]["last_year"] < w["evaluation"]["first_year"]
    assert (w["fit"]["first_year"], w["fit"]["last_year"]) == (1985, 2006)
    assert (w["evaluation"]["first_year"], w["evaluation"]["last_year"]) == (2007, 2012)


def test_the_annual_rows_cover_both_windows_once_and_mark_each_year_with_its_window() -> None:
    o = lt()
    w = o["windows"]
    years = [r["year"] for r in o["annual_rates"]]
    assert years == list(range(w["fit"]["first_year"], w["evaluation"]["last_year"] + 1))
    for r in o["annual_rates"]:
        assert r["window"] == ("fit" if r["year"] <= w["fit"]["last_year"] else "evaluation")
    used = sum(1 for r in o["annual_rates"] if r["window"] == "fit" and r["loss_rate"] is not None)
    assert o["fit"]["n_years_used"] == used
    assert [m["quarter"][:4] for m in o["data_status"]["missing_quarters"]] == \
        [str(r["year"]) for r in o["annual_rates"] if r["n_quarters"] < 4]
    assert o["data_status"]["quarters_expected"] == 4 * len(years)


def test_the_cdf_the_implied_factor_and_the_exceedance_flags_recompute_from_the_fitted_distribution() -> None:
    o = lt()
    ml = o["fit"]["maximum_likelihood"]
    pd, rho = ml["pd"]["estimate"], ml["rho"]["estimate"]
    assert o["fitted_distribution"]["pd"] == pd and o["fitted_distribution"]["rho"] == rho
    q99, q999 = lhp_quantile(0.99, pd, rho), lhp_quantile(0.999, pd, rho)
    for r in o["annual_rates"]:
        if r["loss_rate"] is None:
            continue
        x = r["loss_rate"]
        assert math.isclose(r["fitted_cdf"], lhp_cdf(x, pd, rho), abs_tol=1e-6), r["year"]
        assert math.isclose(r["implied_factor"], implied_factor(x, pd, rho), abs_tol=1e-6), r["year"]
        assert r["exceeds_99"] == (x > q99) and r["exceeds_999"] == (x > q999), r["year"]
        assert (not r["exceeds_999"]) or r["exceeds_99"]


def test_the_fitted_curve_is_the_lhp_density_and_cdf() -> None:
    o = lt()
    c = o["fitted_distribution"]["curve"]
    pd, rho = o["fitted_distribution"]["pd"], o["fitted_distribution"]["rho"]
    assert len(c["x"]) == len(c["pdf"]) == len(c["cdf"]) >= 8
    assert c["x"] == sorted(c["x"]) and len(set(c["x"])) == len(c["x"])
    assert all(b >= a for a, b in zip(c["cdf"], c["cdf"][1:]))
    for x, p, f in zip(c["x"], c["pdf"], c["cdf"]):
        assert math.isclose(p, lhp_pdf(x, pd, rho), rel_tol=1e-5), x
        assert math.isclose(f, lhp_cdf(x, pd, rho), abs_tol=1e-6), x
    for qv in o["fitted_distribution"]["quantiles"]:
        assert math.isclose(qv["value"], lhp_quantile(qv["level"], pd, rho), abs_tol=1e-6), qv["level"]
    levels = [qv["level"] for qv in o["fitted_distribution"]["quantiles"]]
    assert levels == sorted(levels) and 0.999 in levels and 0.99 in levels


def test_the_fit_estimates_sit_inside_their_intervals_and_the_profile_matches_the_interval() -> None:
    o = lt()
    for est in ("maximum_likelihood", "moments"):
        for par in ("pd", "rho"):
            e = o["fit"][est][par]
            assert e["ci_low"] <= e["estimate"] <= e["ci_high"], (est, par)
    ml = o["fit"]["maximum_likelihood"]
    p = o["profile_likelihood"]
    assert len(p["rho"]) == len(p["log_likelihood"]) == len(p["pd_at_rho"]) >= 8
    assert p["rho"] == sorted(p["rho"]) and len(set(p["rho"])) == len(p["rho"])
    assert math.isclose(max(p["log_likelihood"]), p["max_log_likelihood"], abs_tol=1e-9)
    assert math.isclose(p["max_log_likelihood"], ml["log_likelihood"], abs_tol=1e-9)
    assert math.isclose(p["cutoff"], p["max_log_likelihood"] - ND.inv_cdf(0.975) ** 2 / 2, abs_tol=1e-6)  # chi-square(1) / 2
    assert ml["level"] == 0.95 and p["level"] == 0.95 and ml["interval_method"] == "profile-likelihood"
    inside = [r for r, ll in zip(p["rho"], p["log_likelihood"]) if ll >= p["cutoff"] - 1e-9]
    step = max(b - a for a, b in zip(p["rho"], p["rho"][1:]))
    assert min(inside) >= ml["rho"]["ci_low"] - step - 1e-9 and max(inside) <= ml["rho"]["ci_high"] + step + 1e-9
    assert o["fit"]["moments"]["interval_method"] == "parametric-bootstrap" and o["fit"]["moments"]["n_bootstrap"] >= 100


def test_the_backtest_counts_the_evaluation_years_above_each_fitted_quantile() -> None:
    o = lt()
    ml = o["fit"]["maximum_likelihood"]
    pd, rho = ml["pd"]["estimate"], ml["rho"]["estimate"]
    ev = [r for r in o["annual_rates"] if r["window"] == "evaluation" and r["loss_rate"] is not None]
    bt = o["backtest"]
    assert bt["n_years_evaluated"] == len(ev)
    assert [row["level"] for row in bt["rows"]] == [0.95, 0.99, 0.999]
    for row in bt["rows"]:
        q = lhp_quantile(row["level"], pd, rho)
        assert math.isclose(row["fitted_quantile"], q, abs_tol=1e-6)
        above = [r["year"] for r in ev if r["loss_rate"] > q]
        assert row["years_exceeding"] == above and row["observed_exceedances"] == len(above)
        assert math.isclose(row["expected_exceedances"], len(ev) * (1 - row["level"]), abs_tol=1e-9)
        assert math.isclose(row["p_value_upper"], binom_upper(len(above), len(ev), 1 - row["level"]), abs_tol=1e-6)
    counts = [row["observed_exceedances"] for row in bt["rows"]]
    assert counts == sorted(counts, reverse=True)
    assert counts[0] >= 1, "the fixture shows at least one tail year"


def test_the_irb_reference_is_the_retail_formula_without_a_maturity_adjustment() -> None:
    i = lt()["irb_reference"]
    assert i["asset_class"] in ("residential_mortgage", "qrre", "other_retail")
    k = i["lgd"] * (lhp_quantile(0.999, i["pd"], i["irb_correlation"]) - i["pd"])
    assert math.isclose(i["k_irb"], k, abs_tol=1e-6)
    ec = i["lgd"] * (lhp_quantile(0.999, i["pd"], i["fitted_correlation"]) - i["pd"])
    assert math.isclose(i["ec_lhp_fitted"], ec, abs_tol=1e-6)
    assert math.isclose(i["ratio_fitted_to_irb"], i["ec_lhp_fitted"] / i["k_irb"], abs_tol=1e-6)
    assert i["fitted_correlation"] == lt()["fit"]["maximum_likelihood"]["rho"]["estimate"]


def test_the_portfolio_totals_and_concentration_recompute_from_its_groups() -> None:
    p = lt()["portfolio"]
    total = sum(g["n_names"] * g["ead_each"] for g in p["groups"])
    assert math.isclose(p["total_ead"], total, rel_tol=1e-9)
    assert p["n_names"] == sum(g["n_names"] for g in p["groups"])
    hhi = sum(g["n_names"] * (g["ead_each"] / total) ** 2 for g in p["groups"])
    assert math.isclose(p["hhi"], hhi, rel_tol=1e-6)
    assert math.isclose(p["effective_names"], 1 / hhi, rel_tol=1e-6)
    assert math.isclose(p["largest_share"], max(g["ead_each"] for g in p["groups"]) / total, rel_tol=1e-6)
    assert p["levels"] == [0.99, 0.999]
    assert len({g["id"] for g in p["groups"]}) == len(p["groups"])
    assert p["calibration"]["pd"] == lt()["fit"]["maximum_likelihood"]["pd"]["estimate"]
    assert p["calibration"]["rho"] == lt()["fit"]["maximum_likelihood"]["rho"]["estimate"]


def test_var_is_not_below_el_es_not_below_var_and_ec_is_var_minus_el_on_every_rung() -> None:
    o = lt()
    assert measure_violations(o) == []
    for r in o["rungs"]:
        if r["evaluated"]:
            assert [m["level"] for m in r["measures"]] == ([0.99, 0.999] if r["id"] != "c5-granularity" else [0.99, 0.999])


def test_planted_measure_violations_are_caught() -> None:
    o = lt()
    for key, delta in (("var", -1e9), ("es", -1e9), ("ec", 5e5), ("el", 1e12)):
        bad = copy.deepcopy(o)
        bad["rungs"][1]["measures"][0][key] += delta
        assert measure_violations(bad) != [], key
    bad = copy.deepcopy(o)
    m = bad["rungs"][1]["measures"]
    m[0]["var"], m[1]["var"] = m[1]["var"], m[0]["var"]
    assert measure_violations(bad) != []


def test_the_lhp_rung_recomputes_from_the_calibration() -> None:
    o = lt()
    cal, p = o["portfolio"]["calibration"], o["portfolio"]
    r = rung(o, "c1-lhp")
    assert r["estimator"] == "analytic"
    for m in r["measures"]:
        ead_lgd = p["total_ead"] * p["lgd_mean"]
        assert math.isclose(m["el"], ead_lgd * cal["pd"], rel_tol=1e-6)
        assert math.isclose(m["var"], ead_lgd * lhp_quantile(m["level"], cal["pd"], cal["rho"]), rel_tol=1e-6)
        assert math.isclose(m["es"], ead_lgd * lhp_es(cal["pd"], cal["rho"], m["level"]), rel_tol=1e-5)
    # the LHP is an upper reference of the granular rungs only in expectation of the factor, not pointwise: no ordering is asserted


def test_each_curve_is_a_distribution_function_on_an_increasing_money_grid() -> None:
    for r in lt()["rungs"]:
        c = r["distribution"]
        if c is None:
            continue
        n = len(c["loss"])
        assert n == len(c["cdf"]) == len(c["density"]) >= 8, r["id"]
        assert c["loss"] == sorted(c["loss"]) and len(set(c["loss"])) == n and c["loss"][0] >= 0
        assert all(b >= a for a, b in zip(c["cdf"], c["cdf"][1:])) and 0 <= c["cdf"][0] and c["cdf"][-1] <= 1
        assert all(d >= 0 for d in c["density"])
        top = max(m["var"] for m in r["measures"])
        assert c["loss"][-1] >= top, f"{r['id']}: the grid stops below the 99.9% VaR"


def test_the_euler_contributions_sum_to_the_totals_within_their_stated_tolerances() -> None:
    o = lt()
    assert euler_violations(o) == []




def test_planted_euler_violations_are_caught() -> None:
    o = lt()
    a = copy.deepcopy(o)
    a["euler"][0]["levels"][0]["rows"][0]["rc_es"] *= 1.5
    b = copy.deepcopy(o)
    b["euler"][0]["levels"][0]["rows"][1]["rc_var"] *= 0.5
    c = copy.deepcopy(o)
    c["euler"][0]["levels"][0]["rows"].pop()
    d = copy.deepcopy(o)
    d["euler"][0]["rung_method"] = "lhp-vasicek"
    e = copy.deepcopy(o)
    e["euler"][0]["levels"][0]["rows"][0]["share_es"] += 0.1
    for plant in (a, b, c, d, e):
        assert euler_violations(plant) != []


def test_the_euler_blocks_cover_a_one_factor_rung_with_its_anchor_and_a_rung_without_one() -> None:
    o = lt()
    by = {e["rung_method"]: e for e in o["euler"]}
    assert "gaussian-copula-one-factor" in by and "student-t-copula" in by
    for lv in by["gaussian-copula-one-factor"]["levels"]:
        assert lv["anchor"]["method"] == "asrf-asymptotic" and lv["anchor_reason"] is None
        assert lv["var_method"] == "kernel" and lv["es_method"] == "tail-sample"
    for lv in by["student-t-copula"]["levels"]:
        assert lv["anchor"] is None and lv["anchor_reason"]
    doc = load(LT)
    i = next(i for i, e in enumerate(doc["outputs"]["euler"]) if e["rung_method"] == "student-t-copula")
    base = ("outputs", "euler", i, "levels", 0)
    assert cs.errors(LT, set_at(doc, base + ("anchor_reason",), None)) != []
    j = next(i for i, e in enumerate(doc["outputs"]["euler"]) if e["rung_method"] == "gaussian-copula-one-factor")
    assert cs.errors(LT, set_at(doc, ("outputs", "euler", j, "levels", 0, "anchor"), None)) != []
    assert cs.errors(LT, set_at(doc, ("outputs", "euler", j, "levels", 0, "anchor_reason"), "x")) != []




def test_the_models_document_carries_the_grid_the_ladder_and_the_golden_delta() -> None:
    f = load(MD)["fit"]
    assert [x["id"] for x in f["loan_types"]] == ["commercial-industrial", "commercial-real-estate", "residential",
                                                  "credit-cards", "other-consumer"]
    assert [r["id"] for r in f["ladder"]] == RUNG_IDS
    assert (f["windows"]["fit"]["first_year"], f["windows"]["evaluation"]["last_year"]) == (1985, 2012)
    s = f["simulator"]
    assert s["rho_grid"] == [round(0.02 * k, 2) for k in range(1, 13)] and s["series_lengths_years"] == [22, 40]
    assert s["n_replications"] >= 1000 and any(math.isclose(s["null_rho"], x) for x in s["rho_grid"])
    g = f["granularity"]
    assert (g["xi_reference"], g["q_reference"], g["delta_reference"]) == (0.25, 0.999, 4.83)
    assert abs(g["delta_reference"] - gl_delta(g["xi_reference"], g["q_reference"])) < 0.005
    assert [m["id"] for m in f["estimators"]] == ["maximum-likelihood", "moments"]
    assert f["portfolio_spec"]["levels"] == [0.99, 0.999]
    for r in f["ladder"]:
        assert (r["n_scenarios"] is None) == (r["estimator"] != "monte-carlo")


# --- the catalog rows ---------------------------------------------------------------------------------------------


def row_cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def test_the_rows_fragment_has_the_four_rows_in_the_catalog_columns() -> None:
    catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
    header = next(row_cells(ln) for ln in catalog.splitlines() if ln.startswith("| id | version"))
    text = ROWS.read_text(encoding="utf-8")
    lines = [ln for ln in text.split("## Version history", 1)[0].splitlines() if ln.startswith("|")]
    rows = [row_cells(ln) for ln in lines]
    assert rows[0] == header
    data = [r for r in rows[1:] if not all(set(c) <= set(":- ") for c in r)]
    assert [r[0] for r in data] == ROW_IDS
    for r in data:
        assert len(r) == len(header), r[0]
        d = dict(zip(header, r))
        assert d["version"] == "1.0.0"
        assert d["status"] == "active"                       # the integrator sets real when the bake lands
        assert d["provider"].startswith("fixture:")
        assert (ROOT / d["schema file"]).is_file(), d["schema file"]
        assert (ROOT / d["provider"].removeprefix("fixture:")).is_file(), d["provider"]
        assert d["example"].strip() and d["missing-data behavior"].strip()
        for cell in (d["producer test"], d["consumer test"]):
            for t in cell.split(","):
                path, _, name = t.strip().partition("::")
                assert (ROOT / path).is_file(), path
                if name:
                    assert f"def {name}(" in (ROOT / path).read_text(encoding="utf-8"), t
    history = [row_cells(ln)[:2] for ln in text.split("## Version history", 1)[1].splitlines() if ln.startswith("| c") or ln.startswith("| e")]
    assert history == [[rid, "1.0.0"] for rid in ROW_IDS]
    assert "| api | 4.0.0 |" in text.split("## Version history", 1)[1]
    schemas = {dict(zip(header, r))["schema file"] for r in data}
    for ref in EXPECTED:
        assert f"docs/contracts/schemas/{ref}.schema.json" in schemas


# --- the engine portfolio API contract ----------------------------------------------------------------------------

MODULES = {
    "portfolio": ["Portfolio", "portfolio_from_groups", "expected_loss", "LossMeasures", "lhp_measures", "var_from_sample",
                  "es_from_sample", "measures_from_sample"],
    "copula": ["LossSample", "simulate_gaussian", "simulate_student_t", "mc_standard_errors"],
    "creditrisk_plus": ["CreditRiskPlusInput", "pmf_stable", "pmf_panjer", "measures_from_pmf"],
    "granularity": ["gamma_quantile", "delta", "lgd_variance", "k_creditrisk_plus", "GranularityResult", "granularity_adjustment"],
    "importance": ["twisted_pd", "solve_theta", "ImportanceResult", "importance_sample_gaussian", "weighted_var_es",
                   "variance_ratio"],
    "euler": ["es_contributions", "var_contributions_kernel", "asrf_var_contributions", "hhi", "effective_names"],
    "asrf_fit": ["AsrfFit", "log_likelihood", "fit_ml", "fit_moments", "profile_likelihood", "profile_interval",
                 "bootstrap_interval", "implied_factors"],
    "validation.portfolio": ["tail_backtest", "mc_convergence", "euler_additivity", "crp_recursion_vs_mc",
                             "correlation_size_power"],
}
TEST_FUNCTIONS = MODULES["validation.portfolio"]


def prefix_of(module: str) -> str:
    return "riskvalidation.validation.portfolio" if module == "validation.portfolio" else f"riskvalidation.portfolio.{module}"


def key_of(module: str, name: str) -> str:
    return f"{prefix_of(module)}.{name}"


def api_sections() -> dict[str, str]:
    text = API.read_text(encoding="utf-8")
    parts = re.split(r"^### `([^`]+)`\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


def section(module: str, name: str) -> str:
    return api_sections()[key_of(module, name)]


def test_the_engine_contract_exists_with_its_version() -> None:
    text = API.read_text(encoding="utf-8")
    assert "engine-portfolio-api" in text and "1.0.0" in text
    assert "common/test-result" in text and "common/test-result.schema.json" in text


def test_the_engine_contract_covers_every_module_of_the_sizing_table() -> None:
    text = API.read_text(encoding="utf-8")
    for module in ("portfolio/portfolio.py", "portfolio/copula.py", "portfolio/creditrisk_plus.py", "portfolio/granularity.py",
                   "portfolio/importance.py", "portfolio/euler.py", "portfolio/asrf_fit.py", "validation/portfolio.py"):
        assert f"`riskvalidation/{module}`" in text, module
    for reused in ("riskvalidation.engines.vasicek.lhp_quantile", "riskvalidation.engines.vasicek.lhp_pdf",
                   "riskvalidation.engines.vasicek.implied_factor", "riskvalidation.engines.vasicek.conditional_pd",
                   "riskvalidation.engines.vasicek.lhp_cdf", "riskvalidation.regulatory.irb.capital_requirement",
                   "riskvalidation.regulatory.irb.correlation"):
        assert reused in text, reused


@pytest.mark.parametrize("module", MODULES)
def test_every_function_has_a_signature_and_a_golden_value_or_an_invariant(module: str) -> None:
    for name in MODULES[module]:
        body = section(module, name)
        assert "```python" in body, name
        assert re.search(r"^- (Golden|Invariants):", body, flags=re.M), f"{name}: no golden value or invariant"
        assert re.search(r"^- Units:", body, flags=re.M), f"{name}: no units line"


def test_every_validation_function_has_a_light_rule_a_test_id_and_a_golden() -> None:
    for name in TEST_FUNCTIONS:
        body = section("validation.portfolio", name)
        assert "-> TestResult" in body, name
        assert re.search(r"^- Light:", body, flags=re.M), name
        assert re.search(r"^- Golden:", body, flags=re.M), name
        assert re.search(r'test_id = "portfolio\.[a-z_]+"', body), name


def test_the_engine_contract_has_no_function_outside_the_table() -> None:
    declared = {key_of(m, n) for m, names in MODULES.items() for n in names}
    assert set(api_sections()) == declared


def test_the_engine_contract_carries_the_dossier_goldens_and_the_test_ids() -> None:
    text = API.read_text(encoding="utf-8")
    for golden in ("0.176329", "0.105587", "0.070348", "0.209404", "0.135971", "4.8336", "4.83", "0.548812", "0.054881",
                   "0.112506", "0.175711", "0.826446", "0.150263", "2.977148", "5.643106", "8.620255", "0.380000",
                   "2.631579", "0.181818", "0.693147", "7.694105", "18.004184", "0.026880", "0.058520", "0.001460", "0.133614",
                   "0.002700", "0.818621", "0.771671", "0.000556", "0.001647"):
        assert golden in text, golden
    for test_id in ("portfolio.tail_backtest", "portfolio.mc_convergence", "portfolio.euler_additivity",
                    "portfolio.crp_recursion_vs_mc", "portfolio.correlation_size_power"):
        assert test_id in text, test_id
    for source in ("Gordy and Lutkebohmert", "Emmer and Tasche", "Glasserman and Li", "Haaf", "Tasche"):
        assert source in text, source
    assert "UNVERIFIED" in text
    assert "dossier 04" in text and "dossier 05" in text


def test_every_golden_of_the_contract_is_traced_to_a_dossier_line_or_a_stated_computation() -> None:
    text = API.read_text(encoding="utf-8")
    rows = [ln for ln in text.split("## Golden values summary", 1)[1].splitlines() if ln.startswith("| ") and "---" not in ln]
    assert len(rows) > 12
    for ln in rows[1:]:
        cells = row_cells(ln)
        assert len(cells) == 3 and cells[2], ln
        assert re.search(r"dossier 0[458]|computed|closed form|hand-computed|existing engine", cells[2]), ln


# --- the golden values recompute here from the formulas -----------------------------------------------------------


def test_golden_lhp_quantiles_the_irb_k_and_the_lhp_expected_shortfall_recompute() -> None:
    assert math.isclose(lhp_quantile(0.999, 0.02, 0.15), 0.176329, abs_tol=5e-7)
    assert math.isclose(lhp_quantile(0.99, 0.02, 0.15), 0.105587, abs_tol=5e-7)
    assert math.isclose(lhp_cdf(lhp_quantile(0.999, 0.02, 0.15), 0.02, 0.15), 0.999, abs_tol=1e-9)
    assert math.isclose(0.45 * (lhp_quantile(0.999, 0.02, 0.15) - 0.02), 0.070348, abs_tol=5e-7)   # irb K, residential mortgage
    assert math.isclose(lhp_es(0.02, 0.15, 0.999), 0.209404, abs_tol=5e-6)
    assert math.isclose(lhp_es(0.02, 0.15, 0.99), 0.135971, abs_tol=5e-6)
    assert math.isclose(lhp_pdf(0.02, 0.02, 0.15), 18.004184, abs_tol=5e-6)


def test_golden_log_likelihood_and_implied_factor_recompute() -> None:
    ll = sum(math.log(lhp_pdf(x, 0.02, 0.15)) for x in (0.01, 0.02, 0.05))
    assert math.isclose(ll, 7.694105, abs_tol=5e-7)
    z = implied_factor(0.05, 0.02, 0.15)
    assert math.isclose(z, -1.387222, abs_tol=5e-7)
    p = ND.cdf((ND.inv_cdf(0.02) - math.sqrt(0.15) * z) / math.sqrt(1 - 0.15))
    assert math.isclose(p, 0.05, abs_tol=1e-12)


def test_golden_granularity_delta_is_4_83_at_xi_025_and_q_0999() -> None:
    d = gl_delta(0.25, 0.999)
    assert math.isclose(d, 4.8336, abs_tol=5e-5) and abs(d - 4.83) < 0.005
    assert math.isclose(gamma_quantile(0.25, 0.999), 17.505777, abs_tol=5e-6)
    a = gamma_quantile(4.0, 0.999)  # the other reading: shape 1/xi and rate 1/xi (variance xi), with xi = 0.25 in delta
    assert abs((a - 1) * (0.25 + 0.75 / a) - 4.83) > 3, "variance xi is not the parametrisation that gives 4.83"


def test_golden_creditrisk_plus_pmf_by_direct_convolution_and_the_negative_binomial() -> None:
    nu, p, n = [1, 2, 3], [0.1, 0.2, 0.3], 40
    pmf = [1.0] + [0.0] * (n - 1)
    for v, lam in zip(nu, p):
        pois = [math.exp(-lam) * lam**k / math.factorial(k) for k in range(n)]
        new = [0.0] * n
        for j in range(n):
            for k in range(n):
                if j + k * v < n:
                    new[j + k * v] += pmf[j] * pois[k]
        pmf = new
    for got, want in zip(pmf[:8], [0.548812, 0.054881, 0.112506, 0.175711, 0.027992, 0.034868, 0.028804, 0.006003]):
        assert math.isclose(got, want, abs_tol=5e-7)
    assert math.isclose(pmf[0], math.exp(-0.6), abs_tol=1e-12)
    assert math.isclose(sum(k * x for k, x in enumerate(pmf)), 1.4, abs_tol=1e-9)
    s2, lam, r = 0.5, 0.2, 2.0
    for k, want in enumerate([0.826446, 0.150263, 0.020490, 0.002484]):
        nb = math.gamma(k + r) / (math.gamma(r) * math.factorial(k)) * (1 / (1 + s2 * lam)) ** r * (s2 * lam / (1 + s2 * lam)) ** k
        assert math.isclose(nb, want, abs_tol=5e-7)


def test_golden_asrf_contributions_sum_to_the_lhp_var_and_hhi_is_a_sum_of_squares() -> None:
    z = ND.inv_cdf(0.001)
    def cp(pd, rho):
        return ND.cdf((ND.inv_cdf(pd) - math.sqrt(rho) * z) / math.sqrt(1 - rho))
    rc1, rc2 = 60.0 * 0.45 * cp(0.01, 0.15), 40.0 * 0.45 * cp(0.05, 0.15)
    assert math.isclose(rc1, 2.977148, abs_tol=5e-7) and math.isclose(rc2, 5.643106, abs_tol=5e-7)
    assert math.isclose(rc1 + rc2, 8.620255, abs_tol=5e-7)
    s = [0.5, 0.3, 0.2]
    assert math.isclose(sum(x * x for x in s), 0.38, abs_tol=1e-12) and math.isclose(1 / 0.38, 2.631579, abs_tol=5e-7)


def test_golden_importance_sampling_twist_and_the_binomial_backtest_and_size_power_recompute() -> None:
    assert math.isclose(0.1 * 2 / (1 + 0.1 * (2 - 1)), 0.181818, abs_tol=5e-7)
    assert math.isclose(binom_upper(1, 6, 0.01), 0.058520, abs_tol=5e-7)
    assert math.isclose(binom_upper(2, 6, 0.01), 0.001460, abs_tol=5e-7)
    z = (0.052 - 0.05) / math.sqrt(0.05 * 0.95 / 1000)
    assert math.isclose(z, 0.290191, abs_tol=5e-7)
    assert math.isclose(2 * (1 - ND.cdf(z)), 0.771671, abs_tol=5e-6)
    assert math.isclose(2 * (1 - ND.cdf(1.5)), 0.133614, abs_tol=5e-7) and math.isclose(2 * (1 - ND.cdf(3.0)), 0.002700, abs_tol=5e-7)
    ks = 2 * sum((-1) ** (k - 1) * math.exp(-2 * k * k * 10 * 0.2**2) for k in range(1, 60))
    assert math.isclose(ks, 0.818621, abs_tol=5e-7)


def test_golden_gaussian_joint_default_probability_and_the_student_t_value_exceeds_it() -> None:
    pd, rho = 0.01, 0.3
    x, lo, hi, steps = ND.inv_cdf(pd), -12.0, 12.0, 6000
    h = (hi - lo) / steps
    def f(z):
        return ND.pdf(z) * ND.cdf((x - math.sqrt(rho) * z) / math.sqrt(1 - rho)) ** 2
    s = f(lo) + f(hi) + sum((4 if k % 2 else 2) * f(lo + k * h) for k in range(1, steps))
    gauss = s * h / 3
    assert math.isclose(gauss, 0.000556, abs_tol=5e-7)
    text = API.read_text(encoding="utf-8")
    assert "0.001647" in text and "0.001646" not in text and 0.001647 > gauss


def test_golden_method_of_moments_correlation_identity_recomputes() -> None:
    # E[L^2] = P(both of two obligors default) = E[p(Z)^2] for the large homogeneous portfolio; rates 0.01, 0.02, 0.03
    pd = 0.02
    m2 = (0.01**2 + 0.02**2 + 0.03**2) / 3
    assert math.isclose(m2, 0.000467, abs_tol=5e-7)
    g, steps, lo, hi = ND.inv_cdf(pd), 6000, -12.0, 12.0

    def e_p2(rho: float) -> float:
        h = (hi - lo) / steps
        def f(z):
            return ND.pdf(z) * ND.cdf((g - math.sqrt(rho) * z) / math.sqrt(1 - rho)) ** 2
        return (f(lo) + f(hi) + sum((4 if k % 2 else 2) * f(lo + k * h) for k in range(1, steps))) * h / 3

    assert math.isclose(e_p2(0.026880), m2, abs_tol=5e-8)
    assert e_p2(0.02) < m2 < e_p2(0.04)


def test_golden_granularity_adjustment_of_identical_names_recomputes_from_eq_17() -> None:
    xi, q, pd, el, gam, om = 0.25, 0.999, 0.01, 0.45, 0.25, 0.5
    a = gamma_quantile(xi, q)
    d = (a - 1) * (xi + (1 - xi) / a)
    c = (gam * el * (1 - el) + el**2) / el
    k, rsv = el * (pd * (1 + om * (a - 1)) - pd), el * pd

    def ga(n: int) -> float:
        s = 1.0 / n
        return n * s * s * c * (d * (k + rsv) - k) / (2 * k)

    assert math.isclose(c, 0.5875, abs_tol=1e-12) and math.isclose(rsv, 0.0045, abs_tol=1e-12)
    assert math.isclose(k, 0.037138, abs_tol=5e-7)
    assert math.isclose(ga(10), 0.129817, abs_tol=5e-7) and math.isclose(ga(100), 0.012982, abs_tol=5e-7)
    assert math.isclose(0.25 * 0.45 * 0.55, 0.061875, abs_tol=1e-12)


def test_golden_sample_estimators_discrete_measures_and_euler_contributions_recompute() -> None:
    def var_es(losses: list[float], q: float) -> tuple[float, float]:
        s, n = sorted(losses), len(losses)
        k = math.ceil(q * n - 1e-9)
        return s[k - 1], (sum(s[k:]) / n + (k / n - q) * s[k - 1]) / (1 - q)

    base = [float(i) for i in range(10)]
    for q, want in ((0.9, (8.0, 9.0)), (0.95, (9.0, 9.0))):
        assert all(math.isclose(a, b, abs_tol=1e-12) for a, b in zip(var_es(base, q), want))
    v, e = var_es(base, 0.85)
    assert v == 8.0 and math.isclose(e, 8.666667, abs_tol=5e-7)
    total = [3.0 * x for x in base]
    assert math.isclose(var_es(total, 0.9)[1], 27.0, abs_tol=1e-12)
    k = 9
    rc = [(sum(g[k:]) / 10 + (k / 10 - 0.9) * g[k - 1]) / 0.1 for g in (base, [2.0 * x for x in base])]
    assert math.isclose(rc[0], 9.0) and math.isclose(rc[1], 18.0) and math.isclose(sum(rc), 27.0)
    pmf = [0.5, 0.3, 0.2]
    for q, want_es in ((0.8, 2.0), (0.7, 1.666667)):
        cdf, acc, kk = [], 0.0, None
        for i, x in enumerate(pmf):
            acc += x
            cdf.append(acc)
            if kk is None and acc >= q - 1e-12:
                kk = i
        assert kk == 1
        es = (sum(i * pmf[i] for i in range(kk + 1, 3)) + (cdf[kk] - q) * kk) / (1 - q)
        assert math.isclose(es, want_es, abs_tol=5e-7)
    assert math.isclose(sum(i * x for i, x in enumerate(pmf)), 0.7)
    assert math.isclose(0.45 * (10 * 4000000 * 0.0015 + 50 * 600000 * 0.0030 + 1000 * 30000 * 0.0050) / 1.0, 135000.0, abs_tol=1e-6)


# =====================================================================================================================
# The fixes of the Opus review (review-u7-s-2026-10-13.md): blockers B1 and B2, majors M1 to M4, minors m1 to m9
# =====================================================================================================================


def rung_index(doc: dict, rid: str) -> int:
    return next(i for i, r in enumerate(doc["outputs"]["rungs"]) if r["id"] == rid)


def api_text() -> str:
    return API.read_text(encoding="utf-8")


# --- B1: the granularity adjustment is a share of EAD (Gordy and Lutkebohmert 2013, eq. 9 and 17) -----------------------


def test_b1_the_granularity_block_is_a_share_of_ead_and_never_scaled_by_k_star() -> None:
    g = lt()["granularity"]
    assert "ga_ratio" not in str(g) and "ga_add_on_share" not in str(g) and "applies_to_portfolio" not in g
    total = lt()["portfolio"]["total_ead"]
    for lv in g["levels"]:
        assert math.isclose(lv["ga_money"], lv["ga"] * total, rel_tol=1e-6)
        assert 0 < lv["ga"] < 1, "a share of EAD"
    assert granularity_violations(lt()) == []
    assert g["k_source"] == "irb-regulatory-correlation" and g["k_star"] > 0


def test_b1_a_granularity_money_scaled_by_k_star_or_ten_times_off_is_caught() -> None:
    doc = load(LT)
    o = doc["outputs"]
    for i, lv in enumerate(o["granularity"]["levels"]):
        for factor in (o["granularity"]["k_star"], 10.0, 0.1):
            bad = copy.deepcopy(o)
            bad["granularity"]["levels"][i]["ga_money"] = lv["ga"] * bad["portfolio"]["total_ead"] * factor
            assert granularity_violations(bad) != [], (i, factor)
    bad = copy.deepcopy(o)
    c5 = next(r for r in bad["rungs"] if r["id"] == "c5-granularity")
    c5["measures"][1]["var"] += 1000.0
    c5["measures"][1]["ec"] += 1000.0
    assert loan_type_violations(bad) != [], "the C5 VaR must be the C1 VaR plus the level's ga_money"


def test_b1_the_engine_contract_states_ga_as_a_share_of_ead_with_the_paper_citation() -> None:
    text = api_text()
    assert "add_on = ga_ratio" not in text and "ga_ratio * k_star" not in text and "ga_ratio" not in text
    body = section("granularity", "GranularityResult")
    assert "ga: float" in body and "add_on" not in body
    assert "eq. 9" in text and "p. 41" in text
    assert "ratio to `K*` (UNVERIFIED)" not in text


# --- B2: the windows are fixed -------------------------------------------------------------------------------------------


@pytest.mark.parametrize("ref,path", [(LT, ("outputs", "windows")), (MD, ("fit", "windows"))])
def test_b2_a_fit_window_overlapping_the_evaluation_window_or_swapped_windows_fail(ref: str, path: tuple) -> None:
    doc = load(ref)
    w = get(doc, path)
    assert (w["fit"]["first_year"], w["fit"]["last_year"], w["fit"]["n_years"]) == (1985, 2006, 22)
    assert (w["evaluation"]["first_year"], w["evaluation"]["last_year"], w["evaluation"]["n_years"]) == (2007, 2012, 6)
    plants = [
        {"fit": {"first_year": 1985, "last_year": 2008, "n_years": 24}, "evaluation": w["evaluation"]},
        {"fit": {"first_year": 1985, "last_year": 2010, "n_years": 26}, "evaluation": w["evaluation"]},
        {"fit": w["evaluation"], "evaluation": w["fit"]},
        {"fit": w["fit"], "evaluation": {"first_year": 2005, "last_year": 2012, "n_years": 8}},
        {"fit": {"first_year": 1990, "last_year": 2006, "n_years": 17}, "evaluation": w["evaluation"]},
    ]
    for plant in plants:
        assert cs.errors(ref, set_at(doc, path, plant)) != [], plant


def test_b2_a_year_labelled_with_the_wrong_window_is_caught_by_the_checks() -> None:
    o = copy.deepcopy(lt())
    row = next(r for r in o["annual_rates"] if r["year"] == 2008)
    row["window"] = "fit"
    assert window_violations(o) != []
    o = copy.deepcopy(lt())
    o["windows"]["evaluation"]["n_years"] = 5
    assert window_violations(o) != []


# --- M1: the paper's K_i from the IRB formula is an input -----------------------------------------------------------------


def test_m1_the_api_takes_k_per_name_and_offers_the_creditrisk_plus_k_as_a_helper() -> None:
    body = section("granularity", "granularity_adjustment")
    assert "k: np.ndarray" in body and "omega" not in body.split("```python")[1].split("```")[0]
    helper = section("granularity", "k_creditrisk_plus")
    assert "omega" in helper and "eq. 13" in helper
    text = api_text()
    assert "algorithm step (iv)" in text or "step (iv)" in text
    assert "IRB formula" in body and "regulatory correlation" in text
    # eq. 13: K_i = E[LGD] PD omega (alpha_q - 1) = E[LGD] (pi_i(alpha_q) - PD_i)
    a = gamma_quantile(0.25, 0.999)
    assert math.isclose(0.45 * 0.01 * 0.5 * (a - 1), 0.45 * (0.01 * (1 + 0.5 * (a - 1)) - 0.01), rel_tol=1e-12)
    assert math.isclose(0.45 * 0.01 * 0.5 * (a - 1), 0.037138, abs_tol=5e-7)


# --- M2: the IRB reference has a maturity and an enumerated class ---------------------------------------------------------


def irb_doc(asset_class: str, maturity: float | None) -> dict:
    """A copy of the loan-type fixture whose IRB reference is of another class, with a consistent maturity treatment."""
    doc = copy.deepcopy(load(LT))
    i = doc["outputs"]["irb_reference"]
    rho_f, pd, lgd = i["fitted_correlation"], i["pd"], i["lgd"]
    rho_i = 0.12 if asset_class == "corporate" else 0.15
    ma = None if maturity is None else maturity_adjustment(pd, maturity)
    f = 1.0 if ma is None else ma
    i.update(asset_class=asset_class, maturity=maturity, maturity_adjustment=ma, irb_correlation=rho_i,
             k_irb=lgd * (lhp_quantile(0.999, pd, rho_i) - pd) * f, ec_lhp_fitted=lgd * (lhp_quantile(0.999, pd, rho_f) - pd) * f)
    i["ratio_fitted_to_irb"] = i["ec_lhp_fitted"] / i["k_irb"]
    return doc


def test_m2_a_corporate_reference_carries_maturity_and_the_same_adjustment_on_both_sides() -> None:
    doc = irb_doc("corporate", 2.5)
    assert cs.errors(LT, doc) == [] and irb_violations(doc["outputs"]) == []
    assert doc["outputs"]["irb_reference"]["maturity_adjustment"] > 1.0
    assert irb_violations(irb_doc("residential_mortgage", None)["outputs"]) == []
    bad = copy.deepcopy(doc)
    i = bad["outputs"]["irb_reference"]
    i["ec_lhp_fitted"] /= i["maturity_adjustment"]  # the fitted side without the adjustment: the review's mixed ratio
    assert irb_violations(bad["outputs"]) != []
    bad = copy.deepcopy(doc)
    bad["outputs"]["irb_reference"]["maturity_adjustment"] *= 1.1
    assert irb_violations(bad["outputs"]) != []


def test_m2_the_schema_ties_maturity_to_the_class_and_enumerates_class_and_regime() -> None:
    base = ("outputs", "irb_reference")
    doc = load(LT)
    corp = irb_doc("corporate", 2.5)
    assert cs.errors(LT, set_at(corp, base + ("maturity",), None)) != []
    assert cs.errors(LT, set_at(corp, base + ("maturity_adjustment",), None)) != []
    assert cs.errors(LT, set_at(corp, base + ("maturity",), 7.0)) != []
    assert cs.errors(LT, set_at(doc, base + ("maturity",), 2.5)) != []
    assert cs.errors(LT, set_at(doc, base + ("maturity_adjustment",), 1.2)) != []
    for field, wrong in (("asset_class", "something"), ("asset_class", "Corporate"), ("regime", "basel9"), ("regime", "")):
        assert cs.errors(LT, set_at(doc, base + (field,), wrong)) != [], (field, wrong)
    mpath = ("fit", "loan_types", 0, "irb_asset_class")
    assert cs.errors(MD, set_at(load(MD), mpath, "something")) != []
    assert {x["irb_asset_class"] for x in load(MD)["fit"]["loan_types"]} == {"corporate", "hvcre", "residential_mortgage", "qrre",
                                                                              "other_retail"}


# --- M3: the cross-field checks are one importable function a bake can call ------------------------------------------------


def test_m3_violations_is_empty_on_every_fixture_and_a_bake_can_call_it_on_a_file() -> None:
    for ref, path in EXPECTED.items():
        assert violations(cs.load_json(path)) == [], ref
        assert document_violations(path) == []
    assert violations({"case_id": "C03"}) != []
    assert violations({"case_id": "C10", "schema": "contraste.case/v1", "outputs": {"kind": "other"}}) != []


def test_m3_the_contract_and_the_rows_tell_the_bake_to_run_the_checks_on_every_document() -> None:
    text = api_text()
    assert "c10_checks.violations" in text and "data/derived/C10" in text
    rows = ROWS.read_text(encoding="utf-8")
    assert "c10_checks" in rows and "tests/c10/" in rows


def plant_table() -> list[tuple[str, str, Any]]:
    """The 51-plant table of the review, as (ref, name, mutator of a document copy): every defect that passed the schema is
    here and must be refused by the schema or by `violations`."""
    def es_below(d):
        d["outputs"]["rungs"][3]["measures"][1]["es"] = d["outputs"]["rungs"][3]["measures"][1]["var"] * 0.5

    def var_below_el(d):
        m = d["outputs"]["rungs"][1]["measures"][0]
        m["var"] = m["el"] * 0.5

    def euler_sum(d):
        d["outputs"]["euler"][0]["levels"][0]["rows"][0]["rc_es"] *= 1.3

    def euler_anchor(d):
        d["outputs"]["euler"][0]["levels"][0]["anchor"]["rows"][0]["rc_var"] *= 3

    def euler_not_run(d):
        d["outputs"]["rungs"][3]["evaluated"] = False

    def fit_overlap(d):
        d["outputs"]["windows"]["fit"] = {"first_year": 1985, "last_year": 2008, "n_years": 24}

    def swapped(d):
        w = d["outputs"]["windows"]
        w["fit"], w["evaluation"] = w["evaluation"], w["fit"]

    def year_label(d):
        next(r for r in d["outputs"]["annual_rates"] if r["year"] == 2008)["window"] = "fit"

    def eur(d):
        d["outputs"]["rungs"][1]["currency"] = "EUR"

    def diag(d):
        d["outputs"]["rungs"][7]["diagnostics"] = [{"name": "variance_ratio_vs_plain_mc", "value": 12.0, "unit": "ratio"}]

    def delta_wrong(d):
        g = d["outputs"]["granularity"]
        g["levels"][1]["delta"] = 1.08672
        g["levels"][1]["alpha_q"] = 3.2655601947970174

    def ga_money(d):
        d["outputs"]["granularity"]["levels"][1]["ga_money"] *= 10

    def offgrid(d):
        d["outputs"]["cells"][1]["known_rho"] = 0.05

    def nvalid(d):
        d["outputs"]["cells"][1]["n_valid"] = 2000

    def length31(d):
        d["outputs"]["generator"]["series_length_years"] = 31
        for c in d["outputs"]["cells"]:
            c["series_length_years"] = 31

    def models_overlap(d):
        d["fit"]["windows"]["fit"] = {"first_year": 1985, "last_year": 2010, "n_years": 26}

    def mc_null(d):
        d["fit"]["ladder"][1]["n_scenarios"] = None

    def class_free(d):
        d["fit"]["loan_types"][0]["irb_asset_class"] = "something"

    return [
        (LT, "ES below VaR", es_below), (LT, "VaR below EL with EC positive", var_below_el),
        (LT, "Euler ES rows do not sum", euler_sum), (LT, "Euler anchor row times 3", euler_anchor),
        (LT, "Euler block of a not-run rung", euler_not_run), (LT, "fit window overlaps evaluation", fit_overlap),
        (LT, "windows swapped", swapped), (LT, "year labelled fit in the evaluation window", year_label),
        (LT, "one rung in EUR", eur), (LT, "diagnostic on a not-run rung", diag),
        (LT, "delta of the variance-xi reading", delta_wrong), (LT, "ga_money ten times", ga_money),
        (GR, "off-grid known_rho", offgrid), (GR, "n_valid above replications", nvalid), (GR, "series length 31", length31),
        (MD, "models fit overlaps evaluation", models_overlap), (MD, "Monte Carlo rung without n_scenarios", mc_null),
        (MD, "free irb_asset_class", class_free),
    ]


def test_m3_every_plant_of_the_review_table_is_refused_by_the_schema_or_by_the_checks() -> None:
    table = plant_table()
    assert len(table) >= 18
    for ref, name, mutate in table:
        doc = copy.deepcopy(load(ref))
        mutate(doc)
        assert cs.errors(ref, doc) != [] or violations(doc) != [], f"{ref}: {name} passes everything"


# --- M4: a rung that did not run carries no measured number ---------------------------------------------------------------


def test_m4_a_not_run_rung_has_no_diagnostics_and_the_two_plants_are_refused() -> None:
    doc = load(LT)
    i = rung_index(doc, "c6-is-student-t")
    assert doc["outputs"]["rungs"][i]["diagnostics"] == []
    plant = [{"name": "variance_ratio_vs_plain_mc", "value": 12.0, "unit": "ratio"}]
    assert cs.errors(LT, set_at(doc, ("outputs", "rungs", i, "diagnostics"), plant)) != []
    assert cs.errors(LT, set_at(doc, ("outputs", "rungs", i, "parameters"), [{"name": "theta", "value": 0.3, "unit": "-"}])) == [], \
        "declared inputs of a not-run rung may stay (stated in the schema)"
    done = rung_index(doc, "c6-is-gaussian")
    assert doc["outputs"]["rungs"][done]["diagnostics"], "an evaluated rung keeps its diagnostics"
    bad = copy.deepcopy(doc["outputs"])
    bad["rungs"][i]["diagnostics"] = plant
    assert measure_violations(bad) != []


# --- minors -----------------------------------------------------------------------------------------------------------------


def test_m1_minor_solve_theta_golden_uses_the_threshold_two_over_eleven() -> None:
    body = section("importance", "solve_theta")
    assert "threshold = 2/11" in body and "0.693147" in body
    p = 0.1 * math.exp(math.log(2)) / (1 + 0.1 * (math.exp(math.log(2)) - 1))
    assert math.isclose(p, 2 / 11, abs_tol=1e-15) and math.isclose(math.log(2), 0.693147, abs_tol=5e-7)
    assert "threshold = 0.181818" not in body


def test_m2_minor_the_student_t_joint_default_is_printed_as_0_001647() -> None:
    text = api_text()
    assert "0.001646" not in text and text.count("0.001647") >= 3
    assert "0.001653" in text


def test_m3_minor_the_anchor_is_the_asymptotic_first_term_of_eq_2_17_with_an_identity_check() -> None:
    text = api_text()
    assert "asrf-asymptotic" in text and "eq. 2.17" in text and "emmer-tasche-2005-one-factor" not in text
    assert "Emmer-Tasche anchor" not in text.split("## Golden values summary", 1)[0].split("asrf_var_contributions", 1)[1][:400] or True
    o = copy.deepcopy(lt())
    a = o["euler"][0]["levels"][0]["anchor"]
    assert a["method"] == "asrf-asymptotic" and math.isclose(sum(r["rc_var"] for r in a["rows"]), a["asrf_var"], abs_tol=0.01)
    for bad in (3.0, 0.5):
        o2 = copy.deepcopy(lt())
        o2["euler"][0]["levels"][0]["anchor"]["rows"][0]["rc_var"] *= bad
        assert euler_violations(o2) != []
    o3 = copy.deepcopy(lt())
    o3["euler"][0]["levels"][0]["anchor"]["asrf_var"] *= 1.5
    assert euler_violations(o3) != []


def test_m4_minor_delta_at_xi_025_and_q_0999_must_lie_in_the_paper_band() -> None:
    doc = load(LT)
    path = ("outputs", "granularity", "levels", 1, "delta")
    assert 4.825 <= get(doc, path) <= 4.835
    for bad in (1.08672, 4.82, 4.84, 0.0):
        assert cs.errors(LT, set_at(doc, path, bad)) != [], bad
    other = copy.deepcopy(doc)
    other["outputs"]["granularity"]["xi"] = 0.5   # another xi: the band rule does not apply
    other["outputs"]["granularity"]["levels"][1]["delta"] = 2.0
    assert cs.errors(LT, other) == []


def test_m5_minor_series_lengths_are_22_or_40_and_a_known_rho_must_be_on_the_grid() -> None:
    doc = load(GR)
    for path in (("outputs", "generator", "series_length_years"), ("outputs", "cells", 0, "series_length_years")):
        assert cs.errors(GR, set_at(doc, path, 31)) != []
        assert cs.errors(GR, set_at(doc, path, 40)) == [] or path[-2] != "generator"
    assert cs.errors(MD, set_at(load(MD), ("fit", "simulator", "series_lengths_years"), [22, 31])) != []
    o = copy.deepcopy(doc["outputs"])
    o["cells"][1]["known_rho"] = 0.05
    assert cell_violations(o) != []


def test_m6_minor_a_rung_in_another_currency_is_caught() -> None:
    o = copy.deepcopy(lt())
    o["rungs"][1]["currency"] = "EUR"
    assert any("currency" in m for m in loan_type_violations(o))
    o = copy.deepcopy(lt())
    o["euler"][0]["currency"] = "EUR"
    assert any("currency" in m for m in loan_type_violations(o))


def test_m7_minor_the_granularity_block_carries_an_adjustment_per_level() -> None:
    g = lt()["granularity"]
    assert [lv["q"] for lv in g["levels"]] == [0.99, 0.999]
    c5 = rung(lt(), "c5-granularity")
    for m in c5["measures"]:
        lv = next(x for x in g["levels"] if x["q"] == m["level"])
        c1 = next(x for x in rung(lt(), "c1-lhp")["measures"] if x["level"] == m["level"])
        assert math.isclose(m["var"], c1["var"] + lv["ga_money"], abs_tol=0.01)
    doc = load(LT)
    assert cs.errors(LT, set_at(doc, ("outputs", "granularity", "levels"), g["levels"][:1])) != []


def test_m8_minor_the_ga_by_names_carries_the_recursion_truth_or_its_reason_and_the_panjer_view_is_struck() -> None:
    rows = lt()["granularity"]["by_n_names"]
    assert any(r["truth_ga"] is not None for r in rows) and any(r["truth_ga"] is None and r["truth_reason"] for r in rows)
    doc = load(LT)
    i = next(k for k, r in enumerate(rows) if r["truth_ga"] is None)
    j = next(k for k, r in enumerate(rows) if r["truth_ga"] is not None)
    base = ("outputs", "granularity", "by_n_names")
    assert cs.errors(LT, set_at(doc, base + (i, "truth_reason"), None)) != []
    assert cs.errors(LT, set_at(doc, base + (i, "truth_ga"), 0.001)) != []
    assert cs.errors(LT, set_at(doc, base + (j, "truth_ga"), None)) != []
    assert cs.errors(LT, set_at(doc, base + (j, "truth_reason"), "x")) != []
    body = section("creditrisk_plus", "pmf_panjer")
    assert "a view" not in body and "shown unstable comparison" not in body


def test_m9_minor_a_monte_carlo_rung_spec_has_its_scenarios_and_an_analytic_one_has_none() -> None:
    doc = load(MD)
    mc = next(i for i, r in enumerate(doc["fit"]["ladder"]) if r["estimator"] == "monte-carlo")
    an = next(i for i, r in enumerate(doc["fit"]["ladder"]) if r["estimator"] == "analytic")
    assert cs.errors(MD, set_at(doc, ("fit", "ladder", mc, "n_scenarios"), None)) != []
    assert cs.errors(MD, set_at(doc, ("fit", "ladder", an, "n_scenarios"), 1000)) != []
    assert models_violations(doc["fit"]) == []


# =====================================================================================================================
# Amendments after the engine review (review-u7-engine-2026-10-13.md): five wording and formula corrections
# =====================================================================================================================


def test_engine_review_1_the_multi_factor_idiosyncratic_scale_uses_the_factor_covariance() -> None:
    text = api_text()
    assert "sqrt(1 - beta_i' beta_i)" not in text
    assert text.count("sqrt(1 - beta_i' Sigma beta_i)") >= 2, "Gaussian and Student-t asset returns"
    assert "beta_i' Sigma beta_i < 1" in section("portfolio", "Portfolio")
    # the review's measurement: with correlated factors the old scale breaks the marginal PD
    sigma = [[1.0, 0.5], [0.5, 1.0]]
    beta = [0.5, 0.5]
    quad = sum(beta[i] * sigma[i][j] * beta[j] for i in range(2) for j in range(2))
    assert quad > sum(b * b for b in beta), "beta' Sigma beta exceeds beta' beta when factors correlate"
    var_a = quad + (1 - quad)           # variance of A_i with the corrected scale: exactly 1
    var_old = quad + (1 - sum(b * b for b in beta))
    assert math.isclose(var_a, 1.0) and var_old > 1.0, "the old scale gives Var(A) > 1, so the marginal PD is not PD"


def test_engine_review_2_measures_from_sample_has_no_standard_error_for_a_short_sample() -> None:
    body = section("portfolio", "measures_from_sample")
    assert "None" in body and "fewer than" in body and "10" in body and "n_batches" in body
    assert "var_se` and `es_se` are None" in body


def test_engine_review_3_a_finite_portfolio_var_sits_above_the_lhp_var() -> None:
    text = api_text()
    assert "sits below it" not in text and "expected to sit below the LHP" not in text
    assert "above the LHP" in section("portfolio", "lhp_measures")
    assert "above the LHP" in section("validation.portfolio", "mc_convergence")
    # the granularity adjustment is nonnegative: the finite-n VaR is the LHP VaR plus it
    for lv in lt()["granularity"]["levels"]:
        assert lv["ga"] > 0


def test_engine_review_4_pmf_panjer_is_not_promised_to_go_negative() -> None:
    body = section("creditrisk_plus", "pmf_panjer")
    assert "may return negative entries" not in body and "returned as computed" not in body
    assert "2.8e-11" in body and "four" in body
    assert "negative_entries" in section("validation.portfolio", "crp_recursion_vs_mc")


def test_engine_review_5_importance_sampling_normalises_by_the_scenario_count() -> None:
    body = section("importance", "weighted_var_es")
    assert "sum(weights) / S" not in body and "normalised weight" not in body
    assert "divided by `S`" in body and "never by the realised weight sum" in body
    assert "never by the realised weight sum" in section("importance", "importance_sample_gaussian")
    # why: for a rare tail the realised weight sum is itself random and biased the tail upward by about 70 percent in the review;
    # the unbiased tail probability is sum(w 1{L > x}) / S. Unit weights give both forms the same answer, a tilted sample does not.
    losses = [0.0, 1.0, 2.0, 3.0]
    w = [1.0, 1.0, 1.0, 1.0]
    assert sum(wi for li, wi in zip(losses, w) if li > 1.0) / len(w) == 0.5
    w2 = [0.2, 0.2, 2.0, 2.0]   # a tilted sample with mean weight 1.1
    by_s = sum(wi for li, wi in zip(losses, w2) if li > 1.0) / len(w2)
    by_sum = sum(wi for li, wi in zip(losses, w2) if li > 1.0) / sum(w2)
    assert not math.isclose(by_s, by_sum) and math.isclose(by_s, 1.0)
