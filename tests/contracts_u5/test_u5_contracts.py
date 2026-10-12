"""U5-S: the C06 and C07 case contracts, their fixtures, the catalog rows and the engine provisions API contract.

The fixtures validate by discovery (tests/contracts/contract_schemas.py) against exactly one schema; the schemas are
strict both ways (a removed or an added key fails); a PD of 0 or 1 fails at an estimate site; a money block without its
currency fails; a second kind-less variant schema for C06 fails; the engine contract names every function of the
modules table of plans/contraste/units/U5-sizing.md with a golden value or an invariant. The fixtures are labelled as
fixtures and never published as results.
"""
from __future__ import annotations

import copy
import math
import re
from typing import Any, Iterator

import pytest

import contract_schemas as cs

ROOT = cs.ROOT
FIXTURES = ROOT / "docs" / "contracts" / "fixtures"
SCHEMAS = ROOT / "docs" / "contracts" / "schemas"
API = ROOT / "docs" / "contracts" / "engine" / "provisions-api.md"
ROWS = ROOT / "docs" / "contracts" / "rows" / "U5.md"

EXPECTED = {
    "c06/models": FIXTURES / "c06" / "models-fixture.json",
    "c06/variant-reporting-date": FIXTURES / "c06" / "variant-reporting-date-fixture.json",
    "c07/models": FIXTURES / "c07" / "models-fixture.json",
    "c07/variant-three-regime": FIXTURES / "c07" / "variant-three-regime-fixture.json",
}
VARIANTS = {k: v for k, v in EXPECTED.items() if "variant" in k}


def load(ref: str) -> Any:
    return cs.load_json(EXPECTED[ref])


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
    assert doc["provenance"]["generators"] == ["fixture:u5-s-contracts"]
    assert any(i["source"] == "fixture-not-a-result" for i in doc["provenance"]["inputs"])
    key = "variant_id" if "variant" in ref else "fit_id"
    assert str(doc[key]).startswith("fixture-")


def test_every_u5_schema_is_case_folder_conformant_and_case_prefixed() -> None:
    assert cs.case_folder_violations() == []
    files = sorted(p for case in ("c06", "c07") for p in (SCHEMAS / case).glob("*.schema.json"))
    assert {p.relative_to(SCHEMAS).as_posix() for p in files} == {
        "c06/models.schema.json", "c06/variant-reporting-date.schema.json",
        "c07/models.schema.json", "c07/variant-three-regime.schema.json"}
    for p in files:
        case = p.parent.name
        for name in cs.load_json(p).get("$defs", {}):
            assert name.startswith(case), f"{p.name}: $defs name {name!r} is not prefixed {case!r}"


def test_every_u5_variant_schema_declares_its_outputs_kind() -> None:
    by_ref = {c.ref: c for c in cs.candidates()}
    assert by_ref["c06/variant-reporting-date"].consts["outputs.kind"] == "reporting-date"
    assert by_ref["c07/variant-three-regime"].consts["outputs.kind"] == "three-regime"
    assert cs.default_variants().get("C06") is None and cs.default_variants().get("C07") is None
    assert cs.default_violations() == []


def test_a_second_kind_less_c06_variant_schema_fails() -> None:
    planted = cs.Candidate.from_parts("c06/variant-planted", {"schema": "contraste.case/v1", "case_id": "C06"})
    planted2 = cs.Candidate.from_parts("c06/variant-planted2", {"schema": "contraste.case/v1", "case_id": "C06"})
    assert cs.default_violations(cs.candidates() + (planted, planted2)) != []


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
    assert checked > 100


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


PD_KEYS = {"cumulative_pd", "marginal_pd", "hazard", "pd_origination_annualised", "pd_current_annualised",
           "pd_pit", "origination_cumulative_pd", "current_cumulative_pd", "pd_weighted", "pd_at_mean_z",
           "predicted_cumulative_pd", "pd_ttc", "rho"}


def pd_sites(doc: Any, base: tuple) -> Iterator[tuple[tuple, Any]]:
    for path, obj in objects(get(doc, base), base):
        for key, val in obj.items():
            if key not in PD_KEYS:
                continue
            if isinstance(val, list):
                for i, x in enumerate(val):
                    if isinstance(x, (int, float)):
                        yield path + (key, i), x
            elif isinstance(val, (int, float)) and not isinstance(val, bool):
                yield path + (key,), val


@pytest.mark.parametrize("ref", ["c06/variant-reporting-date", "c06/models", "c07/models"])
@pytest.mark.parametrize("bad", [0, 1])
def test_a_pd_of_zero_or_one_fails_at_every_estimate_site(ref: str, bad: int) -> None:
    doc = load(ref)
    sites = list(pd_sites(doc, (root_of(ref),)))
    assert len(sites) > 10 or ref == "c07/models", (ref, len(sites))
    assert sites, ref
    for path, _ in sites:
        mutated = copy.deepcopy(doc)
        get(mutated, path[:-1])[path[-1]] = bad
        assert cs.errors(ref, mutated) != [], f"{ref}: {path} = {bad} still validates"


@pytest.mark.parametrize("ref", EXPECTED)
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


MONEY_NAMES = {"amount", "ecl", "gross_carrying_amount", "opening", "closing", "provision", "exposure",
               "total_provision", "gross_exposure", "allowance", "ecl_weighted", "ecl_at_mean_path",
               "ecl_recomputed", "ecl_frozen", "standard", "internal", "applied", "additional"}


@pytest.mark.parametrize("ref", EXPECTED)
def test_every_money_field_sits_under_a_block_that_states_its_currency(ref: str) -> None:
    doc = load(ref)
    found = 0
    for path, obj in closed_objects(ref):
        for key, val in obj.items():
            if key in MONEY_NAMES and isinstance(val, (int, float)) and not isinstance(val, bool):
                found += 1
                assert any("currency" in get(doc, path[:n]) for n in range(len(path), 0, -1)), \
                    f"{ref}: money field {'/'.join(map(str, path))}/{key} has no currency in any enclosing block"
    assert found > 0 or ref.endswith("models")


# --- identities of the fixtures (what the engine contract promises) -----------------------------------------------


def test_c06_term_structures_obey_the_identities() -> None:
    out = load("c06/variant-reporting-date")["outputs"]
    assert out["term_structures"]
    for ts in out["term_structures"]:
        h, q, f = ts["hazard"], ts["marginal_pd"], ts["cumulative_pd"]
        assert len(h) == len(q) == len(f) == len(ts["months"])
        assert ts["months"] == sorted(ts["months"])
        s_prev = 1.0
        for ht, qt, ft in zip(h, q, f):
            assert math.isclose(qt, s_prev * ht, abs_tol=1e-6)
            s_prev -= qt
            assert math.isclose(ft, 1.0 - s_prev, abs_tol=1e-6)
        assert all(b > a for a, b in zip(f, f[1:]))


def test_c06_scenario_weights_sum_to_one_and_weighted_ecl_is_the_weighted_sum() -> None:
    out = load("c06/variant-reporting-date")["outputs"]
    assert len(out["scenarios"]) >= 2
    assert math.isclose(sum(s["weight"] for s in out["scenarios"]), 1.0, abs_tol=1e-9)
    w = {s["id"]: s["weight"] for s in out["scenarios"]}
    by_stage: dict[str, float] = {}
    for r in out["ecl_by_scenario"]["rows"]:
        by_stage[r["stage"]] = by_stage.get(r["stage"], 0.0) + w[r["scenario_id"]] * r["ecl"]
    for row in out["stage_summary"]["rows"]:
        assert math.isclose(row["ecl"], by_stage[row["stage"]], abs_tol=1e-6 * max(1.0, abs(row["ecl"])))
    assert all(math.isclose(sum(p["weights"]), 1.0, abs_tol=1e-9) for p in out["weight_grid"]["points"])


def test_c06_reconciliation_and_waterfall_close_with_overlays_as_separate_lines() -> None:
    out = load("c06/variant-reporting-date")["outputs"]
    wf = out["waterfall"]
    moves = sum(line["amount"] for line in wf["lines"] if line["kind"] not in ("opening", "closing"))
    opening = next(line["amount"] for line in wf["lines"] if line["kind"] == "opening")
    closing = next(line["amount"] for line in wf["lines"] if line["kind"] == "closing")
    assert math.isclose(opening + moves, closing, abs_tol=1e-6 * max(1.0, abs(closing)))
    overlay_lines = [line for line in wf["lines"] if line["kind"] == "overlay"]
    assert {line["overlay_id"] for line in overlay_lines} == {o["id"] for o in out["overlays"]}
    rec = out["reconciliation"]
    assert rec["tolerance"] == 1e-6
    for st in rec["allowance"]:
        assert math.isclose(st["opening"] + sum(m["amount"] for m in st["movements"]), st["closing"], abs_tol=1e-6)
        assert abs(st["residual"]) <= 1e-6
    for st in rec["gross_carrying_amount"]:
        assert math.isclose(st["opening"] + sum(m["amount"] for m in st["movements"]), st["closing"], abs_tol=1e-6)


def test_c06_non_linearity_golden_example() -> None:
    nl = load("c06/variant-reporting-date")["outputs"]["non_linearity"]
    assert math.isclose(nl["pd_weighted"], 0.02681, abs_tol=5e-6)
    assert math.isclose(nl["pd_at_mean_z"], 0.01800, abs_tol=5e-6)
    assert nl["pd_weighted"] > nl["pd_at_mean_z"]


def test_c07_has_the_three_regimes_and_the_gap_bridge_closes() -> None:
    out = load("c07/variant-three-regime")["outputs"]
    assert [r["regime"] for r in out["regimes"]] == ["cmf-b1", "ifrs9", "bde-annex9"]
    assert out["synthetic"] is True
    for reg in out["regimes"]:
        assert math.isclose(sum(s["provision"] for s in reg["by_segment"]), reg["total_provision"], abs_tol=1e-6)
    tot = {r["regime"]: r["total_provision"] for r in out["regimes"]}
    bridge = out["gap_bridge"]
    assert math.isclose(sum(s["amount"] for s in bridge["steps"]), tot["ifrs9"] - tot["cmf-b1"], abs_tol=1e-6)
    b1 = out["b1_detail"]
    assert b1["minimum_check"]["minimum_rate"] == 0.005
    assert b1["additional_provisions"]["amount"] >= 0


def test_c07_models_carry_every_b1_cell_with_pe_equal_pi_times_pdi() -> None:
    fit = load("c07/models")["fit"]
    n = 0
    for table in fit["b1_tables"]:
        for cell in table["cells"]:
            if cell["pdi"] is None:
                continue
            n += 1
            assert math.isclose(cell["pe"], cell["pi"] * cell["pdi"], abs_tol=5e-7), (table["table_id"], cell)
    assert n >= 16
    consumer = next(t for t in fit["b1_tables"] if t["table_id"] == "consumer-pi")
    assert len(consumer["cells"]) == 16
    assert fit["bank"]["synthetic"] is True


# --- the catalog rows ---------------------------------------------------------------------------------------------


def row_cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def test_the_rows_fragment_has_the_five_rows_in_the_catalog_columns() -> None:
    catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
    header = next(row_cells(ln) for ln in catalog.splitlines() if ln.startswith("| id | version"))
    lines = [ln for ln in ROWS.read_text(encoding="utf-8").splitlines() if ln.startswith("|")]
    rows = [row_cells(ln) for ln in lines]
    assert rows[0] == header
    data = [r for r in rows[1:] if not all(set(c) <= set(":- ") for c in r)]
    assert [r[0] for r in data] == ["c06-outputs", "c06-models", "c07-outputs", "c07-models", "engine-provisions-api"]
    for r in data:
        assert len(r) == len(header), r[0]
        d = dict(zip(header, r))
        assert d["version"] == "1.0.0"
        assert d["status"] == "active"
        assert d["provider"].startswith("fixture:")
        assert (ROOT / d["schema file"]).is_file(), d["schema file"]
        assert (ROOT / d["provider"].removeprefix("fixture:")).is_file(), d["provider"]


# --- the engine provisions API contract ---------------------------------------------------------------------------

MODULES = {
    "term_structure": ["TermStructure", "from_hazard", "from_marginal", "from_cumulative", "forward_pd", "annualise_pd",
                       "competing_risks", "ttc_to_pit", "implied_z", "weighted_pit_pd", "gauss_hermite_pit_pd"],
    "staging": ["StagingPolicy", "sicr_quantitative", "allocate_stages", "apply_cure_probation", "collective_transfer"],
    "ecl": ["discount_factors", "ecl_scenario", "probability_weighted_ecl", "stage3_ecl", "poci_allowance",
            "simplified_matrix_ecl", "commitment_ead", "non_linearity_index", "weight_sensitivity",
            "portfolio_allowance"],
    "overlays": ["Overlay", "overlay_lines", "overlay_share", "total_allowance"],
    "reconciliation": ["allowance_rollforward", "gca_rollforward", "check_identities"],
    "validation.ifrs9": ["lifetime_pd_backtest", "sicr_effectiveness", "sicr_threshold_stability",
                         "stage_migration_backtest", "ecl_backtest", "scenario_sensitivity", "nonlinearity_test",
                         "overlay_diagnostics", "reconciliation_identities"],
    "local_cl": ["b1_individual_category", "b1_individual_provision", "b1_default_provision", "b1_mortgage_pe",
                 "b1_leasing_pe", "b1_student_loan_pe", "b1_commercial_pe", "b1_consumer_pe", "b1_group_provision",
                 "b1_minimum_normal_check", "b1_group_max_rule", "b1_additional_provisions"],
    "local_es": ["annex9_uncovered_amount", "annex9_normal_coverage", "annex9_doubtful_coverage",
                 "annex9_category_to_stage", "annex9_coverage"],
}


def prefix_of(module: str) -> str:
    return "riskvalidation.validation.ifrs9" if module == "validation.ifrs9" else f"riskvalidation.provisions.{module}"


def api_sections() -> dict[str, str]:
    text = API.read_text(encoding="utf-8")
    parts = re.split(r"^### `([^`]+)`\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


def test_the_engine_contract_exists_with_its_version() -> None:
    text = API.read_text(encoding="utf-8")
    assert "engine-provisions-api" in text and "1.0.0" in text
    assert "common/test-result" in text


def test_the_engine_contract_covers_every_module_of_the_sizing_table() -> None:
    text = API.read_text(encoding="utf-8")
    for module in ("provisions/term_structure.py", "provisions/staging.py", "provisions/ecl.py",
                   "provisions/overlays.py", "provisions/reconciliation.py", "validation/ifrs9.py",
                   "provisions/local_cl.py", "provisions/local_es.py"):
        assert f"`riskvalidation/{module}`" in text, module


@pytest.mark.parametrize("module", MODULES)
def test_every_function_has_a_signature_and_a_golden_value_or_an_invariant(module: str) -> None:
    sections = api_sections()
    for name in MODULES[module]:
        key = f"{prefix_of(module)}.{name}"
        assert key in sections, f"{key} has no section"
        body = sections[key]
        assert "```python" in body, key
        assert re.search(r"^- (Golden|Invariants):", body, flags=re.M), f"{key}: no golden value or invariant"
        assert re.search(r"^- Units:", body, flags=re.M), f"{key}: no units line"


def test_the_engine_contract_carries_the_dossier_goldens() -> None:
    text = API.read_text(encoding="utf-8")
    for golden in ("2.681", "1.800", "0.526", "1.429", "7.342", "0.50%", "16 cells", "1e-6"):
        assert golden in text, golden
    for test_id in ("ifrs9.lifetime_pd_backtest", "ifrs9.sicr_effectiveness", "ifrs9.ecl_backtest",
                    "ifrs9.reconciliation_identities"):
        assert test_id in text, test_id


def test_the_engine_contract_has_no_function_outside_the_table() -> None:
    declared = {f"{prefix_of(m)}.{n}" for m, names in MODULES.items() for n in names}
    assert set(api_sections()) == declared
