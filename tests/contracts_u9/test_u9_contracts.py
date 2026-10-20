"""U9-S: the C12 case contracts, the regulatory-calculators contract, their fixtures, the catalog rows and the two engine API contracts.

The fixtures validate by discovery (tests/contracts/contract_schemas.py) against exactly one schema; the schemas are strict both ways
(a removed or an added key fails); a money field without its currency fails; a named parameter without the label "convention" fails; a
calibration whose sample window ends on or after its backtest date fails (no look-ahead); EEPE above the maximum of EE fails; an SA-CCR
block missing an intermediate value fails; a regulatory entry without its paragraph and in-force date fails. The cross-field checks are
importable functions in ``semantics.py`` that a bake calls on every document it writes; these tests run them over every committed
document and over a table of planted defects, each of which must be refused by the schema or by the checker. The two engine contracts
name every function of the modules table of plans/contraste/units/U9-sizing.md with a signature, units and a golden value or an
invariant, and their golden values recompute here from the formulas of the dossiers and the addendum. The fixtures are labelled as
fixtures and never published as results.
"""
from __future__ import annotations

import copy
import math
import re
from pathlib import Path
from typing import Any, Callable, Iterator

import pytest

import contract_schemas as cs
import semantics as sm

ROOT = cs.ROOT
FIXTURES = ROOT / "docs" / "contracts" / "fixtures"
SCHEMAS = ROOT / "docs" / "contracts" / "schemas"
REG_API = ROOT / "docs" / "contracts" / "engine" / "regulatory-api.md"
CCR_API = ROOT / "docs" / "contracts" / "engine" / "ccr-api.md"
ROWS_FRAGMENT = ROOT / "docs" / "contracts" / "rows" / "U9.md"
# merged into the catalog at the batch 3 integration (task/0-13-000-wave2, 2026-10-19) and deleted by fragments.py rows;
# the fragment as merged is kept beside these tests
ROWS = ROWS_FRAGMENT if ROWS_FRAGMENT.is_file() else Path(__file__).parent / "rows-fragment-merged.md"
CHANGES = ROOT / "changes" / "U9-S.md"

C12, C12M, REG = "c12/variant-swap-exposure", "c12/models", "regulatory/calculators"
SCHEMA_REFS = [C12, C12M, REG]
VARIANTS = ["single-swap", "netting-set", "csa-mpor-10d", "csa-mpor-20d", "with-im", "wrong-way-risk"]
FILES: dict[str, tuple[str, Any]] = {v: (C12, FIXTURES / "c12" / f"variant-swap-exposure-{v}-fixture.json") for v in VARIANTS}
FILES["c12-models"] = (C12M, FIXTURES / "c12" / "models-fixture.json")
FILES["regulatory"] = (REG, FIXTURES / "regulatory" / "calculators-fixture.json")
ALL = list(FILES)
VARIANT_KEYS = list(VARIANTS)
ROW_IDS = ["c12-outputs", "c12-models", "regulatory-calculators", "engine-regulatory-api", "engine-ccr-api"]

# --- the dossier and addendum values, typed here again ------------------------------------------------------------------

CRE99_EAD = {1: 569, 2: 381, 3: 5406, 4: 936, 5: 1879}  # dossier 01 E.2, USD thousands
CRE99_PRINTED = {  # dossier 01 E.2 and the BIS page: the printed (rounded) intermediates, as (value, decimals)
    1: {"rc": (60, 0), "en_usd": (59270, 0), "en_eur": (10083, 0), "addon_ir": (347, 0), "swaption_delta": (-0.2694, 4)},
    2: {"rc": (0, 0), "term_1": (2253, 0), "term_2": (77344, 0), "addon_credit": (282, 0), "multiplier": (0.965, 3)},
    3: {"rc": (20, 0), "addon_energy": (2041, 0), "addon_metals": (1800, 0), "addon_commodity": (3841, 0)},
    4: {"rc": (40, 0), "addon_aggregate": (629, 0)},
    5: {"rc": (0, 0), "addon_ir": (123, 0), "addon_commodity": (1278, 0), "addon_aggregate": (1401, 0), "multiplier": (0.958, 3)},
}
GIRR_TENORS = [0.25, 0.5, 1, 2, 3, 5, 10, 15, 20, 30]
GIRR_RW = [0.017, 0.017, 0.016, 0.013, 0.012, 0.011, 0.011, 0.011, 0.011, 0.011]  # MAR21.42 Table 1
CRE20 = {  # dossier 01 C, keyed by the engine's lookup classes; the weights in the order of the table's columns
    ("sovereign", False, False): [0.0, 0.2, 0.5, 1.0, 1.5, 1.0], ("bank-ecra", False, False): [0.2, 0.3, 0.5, 1.0, 1.5],
    ("bank-ecra", True, False): [0.2, 0.2, 0.2, 0.5, 1.5], ("bank-scra", False, False): [0.4, 0.75, 1.5],
    ("bank-scra", True, False): [0.2, 0.5, 1.5], ("corporate", False, False): [0.2, 0.5, 0.75, 1.0, 1.5, 1.0, 0.65, 0.85, 0.75],
    ("residential-re", False, False): [0.2, 0.25, 0.3, 0.4, 0.5, 0.7], ("residential-re", False, True): [0.3, 0.35, 0.45, 0.6, 0.75, 1.05],
    ("commercial-re", False, True): [0.7, 0.9, 1.1], ("eca", False, False): [0.0, 0.0, 0.2, 0.5, 1.0, 1.0, 1.0, 1.5],
    ("retail", False, False): [0.75, 0.45, 1.0], ("equity", False, False): [2.5, 4.0, 1.0, 1.5],
    ("defaulted", False, False): [1.5, 1.0, 1.0], ("ccf", False, False): [1.0, 1.0, 1.0, 1.0, 0.5, 0.5, 0.4, 0.2, 0.1],
}
NAMED = ["notionals", "maturities_years", "sides", "netting_set_members", "single_swap_member", "fixed_rate_rule", "csa_threshold",
         "csa_minimum_transfer_amount", "csa_independent_amount", "mpor_business_days_short", "mpor_business_days_long",
         "counterparty_spread", "counterparty_lgd", "bank_spread", "bank_lgd", "pfe_quantile", "path_count", "seed", "time_grid_years",
         "wwr_b_grid", "im_quantile", "im_horizon_calendar_days", "im_mpor_calendar_days", "im_regression_order", "ba_cva_sector",
         "ba_cva_rating", "stress_window_start", "stress_window_end", "backtest_window_start", "backtest_paths_per_date",
         "backtest_simulated_critical_count", "reconciliation_se_threshold", "ee_check_k_se"]
HORIZONS = ["10bd", "20bd", "1m", "3m", "6m", "12m"]


def load(key: str) -> Any:
    return cs.load_json(FILES[key][1])


def ref_of(key: str) -> str:
    return FILES[key][0]


def all_documents() -> list:
    paths = [p for _, p in FILES.values()]
    for case in ("C12", "regulatory"):
        d = ROOT / "data" / "derived" / case
        paths += sorted(d.glob("*.json")) if d.is_dir() else []
    return paths


def check_of(ref: str) -> Callable[[dict], list[str]]:
    return {C12: sm.check_c12, C12M: sm.check_c12_models, REG: sm.check_regulatory}[ref]


# --- the fixtures -------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("key", ALL)
def test_the_fixture_exists_and_is_discovered_by_exactly_one_schema(key: str) -> None:
    ref, path = FILES[key]
    assert path.is_file(), path
    doc = cs.load_json(path)
    assert cs.schema_for_document(path, doc) == ref
    assert cs.errors(ref, doc) == []
    passing = [c.ref for c in cs.candidates() if cs.errors(c.ref, doc) == []]
    assert passing == [ref], f"{key}: validates against {passing}"


@pytest.mark.parametrize("key", ALL)
def test_the_fixture_is_labelled_as_a_fixture(key: str) -> None:
    doc = load(key)
    assert doc["provenance"]["generators"] == ["fixture:u9-s-contracts"]
    assert any(i["source"] == "fixture-not-a-result" for i in doc["provenance"]["inputs"])
    ident = doc.get("variant_id") or doc.get("fit_id") or doc.get("document_id")
    assert str(ident).startswith("fixture-")


def test_there_are_six_c12_variants_with_one_kind_and_distinct_variant_names() -> None:
    names = [load(k)["outputs"]["variant"] for k in VARIANTS]
    assert names == VARIANTS
    assert {load(k)["outputs"]["kind"] for k in VARIANTS} == {"swap-exposure"}
    assert len({load(k)["variant_id"] for k in VARIANTS}) == 6


def test_every_u9_schema_is_case_folder_conformant_and_case_prefixed() -> None:
    assert cs.case_folder_violations() == []
    files = sorted(p for case in ("c12", "regulatory") for p in (SCHEMAS / case).glob("*.schema.json"))
    assert {p.relative_to(SCHEMAS).as_posix() for p in files} == {f"{ref}.schema.json" for ref in SCHEMA_REFS}
    for p in files:
        case = p.parent.name
        names = cs.load_json(p).get("$defs", {})
        assert names, p
        for name in names:
            assert name.startswith(case), f"{p.name}: $defs name {name!r} is not prefixed {case!r}"


def test_a_def_two_files_of_one_case_share_has_one_definition() -> None:
    a = cs.load_json(SCHEMAS / "c12" / "models.schema.json")["$defs"]
    b = cs.load_json(SCHEMAS / "c12" / "variant-swap-exposure.schema.json")["$defs"]
    shared = set(a) & set(b)
    assert shared
    for name in shared:
        assert a[name] == b[name], f"c12: {name} differs between the models and the variant schema"


def test_the_c12_variant_schema_declares_its_outputs_kind_and_no_case_has_two_defaults() -> None:
    by_ref = {c.ref: c for c in cs.candidates()}
    assert by_ref[C12].consts["outputs.kind"] == "swap-exposure"
    assert cs.default_variants().get("C12") is None
    assert cs.default_violations() == []
    assert by_ref[REG].consts["case_id"] == "REGULATORY" and by_ref[REG].consts["schema"] == "contraste.regulatory/v1"


def test_a_second_kind_less_variant_schema_fails() -> None:
    a = cs.Candidate.from_parts("c12/variant-planted", {"schema": "contraste.case/v1", "case_id": "C12"})
    b = cs.Candidate.from_parts("c12/variant-planted2", {"schema": "contraste.case/v1", "case_id": "C12"})
    assert cs.default_violations(cs.candidates() + (a, b)) != []


# --- strictness ---------------------------------------------------------------------------------------------------------


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


def probes(key: str) -> list[tuple[tuple, dict]]:
    """One object per shape of the document (its path without indices and its keys), so a probe run stays short."""
    seen, found = set(), []
    doc = load(key)
    roots = {"c12-models": ["fit"], "regulatory": ["official_examples", "invariant_cases", "cre20_grid", "engine", "units"]}.get(key, ["outputs"])
    for root in roots:
        for path, obj in objects(doc[root], (root,)):
            shape = (tuple(p for p in path if not isinstance(p, int)), tuple(sorted(obj)))
            if shape not in seen:
                seen.add(shape)
                found.append((path, obj))
    return found


@pytest.mark.parametrize("key", ALL)
def test_a_key_removed_from_any_object_fails(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    checked = 0
    for path, obj in probes(key):
        for k in list(obj):
            bad = copy.deepcopy(doc)
            del get(bad, path)[k]
            assert cs.errors(ref, bad) != [], f"{key}: removing {'/'.join(map(str, path))}/{k} still validates"
            checked += 1
    assert checked > 40


@pytest.mark.parametrize("key", ALL)
def test_a_key_added_to_any_object_fails(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    for path, _ in probes(key):
        bad = copy.deepcopy(doc)
        get(bad, path)["unknown_key"] = 1
        assert cs.errors(ref, bad) != [], f"{key}: adding a key at {'/'.join(map(str, path))} still validates"


@pytest.mark.parametrize("key", VARIANT_KEYS)
def test_a_document_without_case_id_or_outputs_kind_does_not_pass(key: str) -> None:
    ref, path, doc = ref_of(key), FILES[key][1], load(key)
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


@pytest.mark.parametrize("key", ALL)
def test_a_wrong_case_id_is_rejected_and_no_fixture_validates_against_another_schema(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    bad = copy.deepcopy(doc)
    bad["case_id"] = "C99"
    assert cs.errors(ref, bad) != []
    others = [c.ref for c in cs.candidates() if c.ref != ref and c.ref.split("/")[0] in ("c12", "regulatory", "c14", "c15", "c16")]
    assert others
    for other in others:
        assert cs.errors(other, doc) != [], f"{key} validates against {other}"


# --- money blocks carry their currency ----------------------------------------------------------------------------------


@pytest.mark.parametrize("key", VARIANT_KEYS)
def test_a_money_block_without_its_currency_fails(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    sites = [(p, o) for p, o in probes(key) if "currency" in o and "tenor_years" not in o]
    assert sites, f"{key}: no object carries a currency"
    for path, _ in sites:
        bad = copy.deepcopy(doc)
        del get(bad, path)["currency"]
        assert cs.errors(ref, bad) != [], f"{key}: {path} without currency validates"
        worse = copy.deepcopy(doc)
        get(worse, path)["currency"] = "dollars"
        assert cs.errors(ref, worse) != [], f"{key}: {path} with a non-ISO currency validates"
        eur = copy.deepcopy(doc)
        get(eur, path)["currency"] = "EUR"
        assert cs.errors(ref, eur) != [], f"{key}: {path} in EUR validates (C12 is USD)"


MONEY_NAMES = {"amount", "notional"}


@pytest.mark.parametrize("key", VARIANT_KEYS)
def test_every_money_amount_sits_in_an_object_that_states_its_currency(key: str) -> None:
    doc, found = load(key), 0
    for path, obj in objects(doc["outputs"], ("outputs",)):
        if "amount" in obj:
            found += 1
            assert "currency" in obj, f"{key}: {'/'.join(map(str, path))} has an amount without a currency"
    assert found > 20, found


def test_a_regulatory_value_carries_its_unit_and_a_published_value_its_rounding() -> None:
    ref, doc = REG, load("regulatory")
    for group in ("inputs", "outputs"):
        bad = copy.deepcopy(doc)
        del bad["official_examples"][0][group][0]["unit"]
        assert cs.errors(ref, bad) != []
    bad = copy.deepcopy(doc)
    del bad["official_examples"][0]["published"][0]["rounding"]
    assert cs.errors(ref, bad) != []


# --- named parameters ---------------------------------------------------------------------------------------------------


def test_every_named_parameter_is_required_with_its_value_and_the_convention_label() -> None:
    for key in VARIANT_KEYS:
        ref, doc = ref_of(key), load(key)
        named = doc["outputs"]["named_parameters"]
        assert list(named) == NAMED
        for name, p in named.items():
            assert p["label"] == "convention", name
            for mutate in (lambda d, n=name: d["outputs"]["named_parameters"][n].pop("label"),
                           lambda d, n=name: d["outputs"]["named_parameters"][n].__setitem__("label", "measured"),
                           lambda d, n=name: d["outputs"]["named_parameters"][n].pop("value"),
                           lambda d, n=name: d["outputs"]["named_parameters"].pop(n)):
                bad = copy.deepcopy(doc)
                mutate(bad)
                assert cs.errors(ref, bad) != [], f"{key}: named parameter {name} passes after a mutation"


def test_the_proposed_values_of_the_named_parameters_follow_the_sdd_and_are_the_same_in_every_variant() -> None:
    docs = [load(k)["outputs"]["named_parameters"] for k in VARIANT_KEYS]
    assert all(d == docs[0] for d in docs)
    n = docs[0]
    assert n["mpor_business_days_short"]["value"] == 10 and n["mpor_business_days_long"]["value"] == 20  # SDD line 384, CRE53.24
    assert n["pfe_quantile"]["value"] == 0.95 and n["path_count"]["value"] == 10000
    assert n["im_quantile"]["value"] == 0.99  # ORE guide: a high (99 percent) quantile (addendum R2)
    assert n["counterparty_lgd"]["value"] == 0.6 and n["bank_lgd"]["value"] == 0.6
    # decision R1 (2026-10-19): the book, the wrong-way grid, the spread and the calendar-day IM horizon
    assert n["notionals"]["value"] == [10_000_000.0, 6_000_000.0, 4_000_000.0, 2_000_000.0]
    assert n["maturities_years"]["value"] == [10.0, 5.0, 3.0, 0.5] and n["sides"]["value"] == ["payer", "receiver", "payer", "receiver"]
    assert n["netting_set_members"]["value"] == ["SW-1", "SW-2", "SW-3", "SW-4"] and n["single_swap_member"]["value"] == "SW-1"
    assert n["wwr_b_grid"]["value"] == [-2.0, 0.0, 1.0, 2.0, 4.0] and 0 in n["wwr_b_grid"]["value"]
    assert n["counterparty_spread"]["value"] == 0.0125  # Hull and White Tables 1 and 2 (addendum R1)
    assert n["im_horizon_calendar_days"]["value"] == 14 and n["im_mpor_calendar_days"]["value"] == 14  # ORE: calendar days (R2)


# --- the variants carry exactly the blocks they run ---------------------------------------------------------------------


def test_each_variant_carries_exactly_the_blocks_it_runs() -> None:
    expect = {  # trades, collateral mpor, im, wwr, ore
        "single-swap": (1, None, False, False, "reconciled"), "netting-set": (4, None, False, False, "reconciled"),
        "csa-mpor-10d": (4, 10, False, False, "reconciled"), "csa-mpor-20d": (4, 20, False, False, "reconciled"),
        "with-im": (4, 10, True, False, "reconciled"), "wrong-way-risk": (4, None, False, True, "not-applicable"),
    }
    for v, (n, mpor, im, wwr, ore) in expect.items():
        o = load(v)["outputs"]
        assert len(o["book"]["trades"]) == n, v
        assert (o["collateral"] is not None) == (mpor is not None), v
        if mpor:
            assert o["collateral"]["csa"]["mpor_business_days"] == mpor
            assert o["sa_ccr"]["mpor_business_days"] == mpor
        assert (o["initial_margin"] is not None) == im and (o["wrong_way_risk"] is not None) == wwr, v
        assert o["ore_reconciliation"]["status"] == ore, v


@pytest.mark.parametrize("v,field,value", [("csa-mpor-10d", "mpor_business_days", 20), ("single-swap", "trades", "two")])
def test_a_variant_whose_blocks_contradict_its_name_fails(v: str, field: str, value: Any) -> None:
    doc = copy.deepcopy(load(v))
    if field == "trades":
        doc["outputs"]["book"]["trades"] = doc["outputs"]["book"]["trades"] * 2
    else:
        doc["outputs"]["collateral"]["csa"][field] = value
    assert cs.errors(C12, doc) != []


def test_a_block_the_variant_does_not_run_must_be_null_and_the_ones_it_runs_must_not() -> None:
    d = copy.deepcopy(load("netting-set"))
    d["outputs"]["wrong_way_risk"] = copy.deepcopy(load("wrong-way-risk")["outputs"]["wrong_way_risk"])
    assert cs.errors(C12, d) != []
    d = copy.deepcopy(load("csa-mpor-10d"))
    d["outputs"]["collateral"] = None
    assert cs.errors(C12, d) != []
    d = copy.deepcopy(load("with-im"))
    d["outputs"]["initial_margin"] = None
    assert cs.errors(C12, d) != []


def test_the_initial_margin_is_a_regression_proxy_never_simm() -> None:
    im = load("with-im")["outputs"]["initial_margin"]
    assert im["labelled"] == "regression proxy, not SIMM" and im["simm_used"] is False
    d = copy.deepcopy(load("with-im"))
    d["outputs"]["initial_margin"]["simm_used"] = True
    assert cs.errors(C12, d) != []
    d = copy.deepcopy(load("with-im"))
    d["outputs"]["initial_margin"]["labelled"] = "SIMM"
    assert cs.errors(C12, d) != []


def test_wrong_way_risk_has_no_ore_reconciliation_and_says_so() -> None:
    o = load("wrong-way-risk")["outputs"]
    assert o["ore_reconciliation"]["status"] == "not-applicable" and o["ore_reconciliation"]["reason"]["en"]
    assert o["wrong_way_risk"]["ore_limit"]["en"]
    d = copy.deepcopy(load("wrong-way-risk"))
    d["outputs"]["ore_reconciliation"] = copy.deepcopy(load("single-swap")["outputs"]["ore_reconciliation"])
    assert cs.errors(C12, d) != []


def test_the_sign_convention_and_the_units_are_stated() -> None:
    for k in VARIANT_KEYS:
        o = load(k)["outputs"]
        assert o["sign_convention"]["cva"] == "positive-is-cost" and o["sign_convention"]["ee"].startswith("positive")
        assert o["units"]["mpor"] == "business-days" and o["units"]["compounding"] == "continuous"
    d = copy.deepcopy(load("single-swap"))
    del d["outputs"]["sign_convention"]
    assert cs.errors(C12, d) != []


def test_a_test_row_of_a_c12_document_must_have_a_ccr_id() -> None:
    d = copy.deepcopy(load("single-swap"))
    d["tests"][0]["test_id"] = "irrbb.something"
    assert cs.errors(C12, d) != [] or sm.check_c12(d) != []
    assert all(t["test_id"].startswith("ccr.") for k in VARIANT_KEYS for t in load(k)["tests"])


def test_a_treasury_tenor_absent_on_the_date_is_listed_and_never_interpolated() -> None:
    for k in VARIANT_KEYS:
        c = load(k)["outputs"]["curve"]
        assert c["tenors_absent"] and not set(c["tenors_absent"]) & {p["tenor_years"] for p in c["points"]}
        assert c["tenors_present"] == [p["tenor_years"] for p in c["points"]] and c["interpolated_silently"] is False
    d = copy.deepcopy(load("single-swap"))
    d["outputs"]["curve"]["interpolated_silently"] = True
    assert cs.errors(C12, d) != []
    d = copy.deepcopy(load("single-swap"))
    d["outputs"]["curve"]["tenors_absent"].append(d["outputs"]["curve"]["tenors_present"][0])
    assert sm.check_c12(d) != []


# --- the semantic checkers ----------------------------------------------------------------------------------------------


@pytest.mark.parametrize("path", all_documents(), ids=lambda p: p.name)
def test_the_semantic_checker_is_clean_on_every_committed_c12_and_regulatory_document(path) -> None:
    doc = cs.load_json(path)
    ref = cs.schema_for_document(path, doc)
    if ref in SCHEMA_REFS:
        assert check_of(ref)(doc) == [], path.name


def test_the_checkers_are_importable_functions_a_bake_calls() -> None:
    for fn in (sm.check_c12, sm.check_c12_models, sm.check_regulatory):
        assert callable(fn)


def mut(fn: Callable[[dict], None]) -> Callable[[dict], None]:
    return fn


def _set(path: tuple, value: Any) -> Callable[[dict], None]:
    def f(d: dict) -> None:
        get(d, path[:-1])[path[-1]] = value
    return f


def _del(path: tuple) -> Callable[[dict], None]:
    def f(d: dict) -> None:
        del get(d, path[:-1])[path[-1]]
    return f


def _eepe_above_max(d: dict) -> None:
    d["outputs"]["exposure"]["eepe"]["amount"] = max(d["outputs"]["exposure"]["ee"]["values"]) * 2


def _effective_ee_decreasing(d: dict) -> None:
    d["outputs"]["exposure"]["effective_ee"]["values"][2] = 0.0


def _netted_above_sum(d: dict) -> None:
    nb = d["outputs"]["netting_benefit"]
    nb["netted_ee"]["values"][2] = nb["sum_of_single_trade_ee"]["values"][2] * 1.5
    nb["benefit"]["values"][2] = -nb["sum_of_single_trade_ee"]["values"][2] * 0.5


def _cva_term(d: dict) -> None:
    d["outputs"]["cva_dva"]["buckets"][1]["cva_term"] *= 1.1


def _w2(d: dict) -> None:
    d["outputs"]["backtest"]["book_horizons"][0]["w2"] += 1.0


def _wwr_b0(d: dict) -> None:
    next(x for x in d["outputs"]["wrong_way_risk"]["sweep"] if x["b"] == 0)["cva"]["amount"] *= 1.0000001


def _wwr_independent_flag(d: dict) -> None:
    d["outputs"]["wrong_way_risk"]["sweep"][2]["independent"] = True


def _lookahead(d: dict) -> None:
    d["outputs"]["calibration_used"]["sample_end"] = d["outputs"]["calibration_used"]["backtest_date"]


def _lookahead_after(d: dict) -> None:
    d["outputs"]["calibration_used"]["sample_end"] = "2020-02-01"


def _short_history(d: dict) -> None:
    d["outputs"]["calibration_used"]["sample_start"] = "2018-06-01"


def _sa_trade_delta(d: dict) -> None:
    d["outputs"]["sa_ccr"]["trades"][0]["delta"] = "-1"


def _sa_trade_bucket(d: dict) -> None:
    d["outputs"]["sa_ccr"]["trades"][0]["bucket"] = "B1"


def _sa_multiplier(d: dict) -> None:
    d["outputs"]["sa_ccr"]["multiplier"] = 0.5


def _sa_ead(d: dict) -> None:
    d["outputs"]["sa_ccr"]["ead"]["amount"] *= 1.01


def _sa_rc(d: dict) -> None:
    d["outputs"]["sa_ccr"]["rc"]["amount"] += 1.0


def _sa_addon(d: dict) -> None:
    d["outputs"]["sa_ccr"]["hedging_sets"][0]["addon"] *= 1.5


def _sa_delete(name: str) -> Callable[[dict], None]:
    return _del(("outputs", "sa_ccr", name))


def _sa_trade_delete(name: str) -> Callable[[dict], None]:
    return _del(("outputs", "sa_ccr", "trades", 0, name))


def _sa_set_delete(name: str) -> Callable[[dict], None]:
    return _del(("outputs", "sa_ccr", "hedging_sets", 0, name))


def _ba_k(d: dict) -> None:
    d["outputs"]["ba_cva"]["k_reduced"] *= 2


def _girr_charge(d: dict) -> None:
    d["outputs"]["girr"]["delta_charge"]["amount"] = d["outputs"]["girr"]["delta_charge_undivided"]["amount"] * 2


def _ore_flag(d: dict) -> None:
    d["outputs"]["ore_reconciliation"]["agreement"][0]["within_two_se"] = False


def _alpha_eepe(d: dict) -> None:
    d["outputs"]["regulatory_comparison"]["alpha_times_eepe"]["amount"] *= 2


def _stress_no_rise(d: dict) -> None:
    d["outputs"]["regulatory_comparison"]["stressed"]["spread_rose"] = False


PLANTS: list[tuple[str, str, Callable[[dict], None]]] = [
    ("eepe above max ee", "netting-set", _eepe_above_max),
    ("effective ee decreasing", "netting-set", _effective_ee_decreasing),
    ("netted ee above the sum of single trades", "netting-set", _netted_above_sum),
    ("cva term altered", "netting-set", _cva_term),
    ("w2 altered", "single-swap", _w2),
    ("wwr b=0 differs from independent", "wrong-way-risk", _wwr_b0),
    ("wwr independent flag on b != 0", "wrong-way-risk", _wwr_independent_flag),
    ("calibration ends on the backtest date", "single-swap", _lookahead),
    ("calibration ends after the backtest date", "single-swap", _lookahead_after),
    ("calibration with under three years", "single-swap", _short_history),
    ("sa-ccr delta of a payer", "single-swap", _sa_trade_delta),
    ("sa-ccr bucket", "single-swap", _sa_trade_bucket),
    ("sa-ccr multiplier", "single-swap", _sa_multiplier),
    ("sa-ccr ead", "single-swap", _sa_ead),
    ("sa-ccr rc", "csa-mpor-10d", _sa_rc),
    ("sa-ccr hedging set add-on", "single-swap", _sa_addon),
    ("sa-ccr without rc", "single-swap", _sa_delete("rc")),
    ("sa-ccr without multiplier", "single-swap", _sa_delete("multiplier")),
    ("sa-ccr without hedging sets", "single-swap", _sa_delete("hedging_sets")),
    ("sa-ccr without add-on by class", "single-swap", _sa_delete("addon_by_class")),
    ("sa-ccr without the aggregate add-on", "single-swap", _sa_delete("addon_aggregate")),
    ("sa-ccr without pfe", "single-swap", _sa_delete("pfe")),
    ("sa-ccr without ead", "single-swap", _sa_delete("ead")),
    ("sa-ccr trade without supervisory duration", "single-swap", _sa_trade_delete("supervisory_duration")),
    ("sa-ccr trade without maturity factor", "single-swap", _sa_trade_delete("maturity_factor")),
    ("sa-ccr trade without bucket", "single-swap", _sa_trade_delete("bucket")),
    ("sa-ccr trade without effective notional", "single-swap", _sa_trade_delete("effective_notional")),
    ("sa-ccr trade without delta", "single-swap", _sa_trade_delete("delta")),
    ("sa-ccr hedging set without b2", "single-swap", _sa_set_delete("d_b2")),
    ("sa-ccr hedging set without effective notional", "single-swap", _sa_set_delete("effective_notional")),
    ("ba-cva k_reduced", "single-swap", _ba_k),
    ("girr charge is not the max", "single-swap", _girr_charge),
    ("ore flag disagrees", "single-swap", _ore_flag),
    ("alpha times eepe", "single-swap", _alpha_eepe),
    ("stress spread did not rise", "single-swap", _stress_no_rise),
    ("no case_id", "single-swap", _del(("case_id",))),
    ("no outputs kind", "single-swap", _del(("outputs", "kind"))),
    ("named parameter without label", "single-swap", _del(("outputs", "named_parameters", "csa_threshold", "label"))),
    ("named parameter label other", "single-swap", _set(("outputs", "named_parameters", "seed", "label"), "assumed")),
    ("test id without ccr prefix", "single-swap", _set(("tests", 0, "test_id"), "market.x")),
    ("money without currency", "single-swap", _del(("outputs", "sa_ccr", "ead", "currency"))),
    ("notional in another currency", "single-swap", _set(("outputs", "book", "trades", 0, "notional", "currency"), "EUR")),
    ("calibration backtest date not the curve date", "single-swap", _set(("outputs", "calibration_used", "backtest_date"), "2020-01-02")),
]


def test_the_plant_table_has_no_duplicate_names_and_is_large() -> None:
    names = [n for n, _, _ in PLANTS]
    assert len(names) == len(set(names)) and len(names) >= 40


@pytest.mark.parametrize("name,key,mutate", PLANTS, ids=[n for n, _, _ in PLANTS])
def test_a_planted_defect_is_refused_by_the_schema_or_the_checker(name: str, key: str, mutate: Callable[[dict], None]) -> None:
    doc = copy.deepcopy(load(key))
    mutate(doc)
    assert cs.errors(C12, doc) != [] or sm.check_c12(doc) != [], name


MODEL_PLANTS = [
    ("models calibration ends on its backtest date", lambda d: _set(("fit", "calibrations", 0, "sample_end"), d["fit"]["calibrations"][0]["backtest_date"])(d)),
    ("models calibration ends after its backtest date", lambda d: _set(("fit", "calibrations", 1, "sample_end"), "2020-06-30")(d)),
    ("models calibration dates out of order", lambda d: d["fit"]["calibrations"].reverse()),
    ("models girr correlation altered", lambda d: d["fit"]["girr_parameters"]["correlation_percent"][1].__setitem__(5, 80.0)),
    ("models girr risk weight altered", lambda d: d["fit"]["girr_parameters"]["risk_weights"].__setitem__(0, 0.02)),
    ("models girr tenor altered", lambda d: d["fit"]["girr_parameters"]["tenors_years"].__setitem__(2, 1.5)),
    ("models fewer than two calibrations", lambda d: d["fit"]["calibrations"].pop()),
    ("models credit curve not labelled a proxy", lambda d: d["fit"]["credit_curve"].__setitem__("label", "market")),
    ("models without limits", lambda d: d["fit"]["limits"].clear()),
]


@pytest.mark.parametrize("name,mutate", MODEL_PLANTS, ids=[n for n, _ in MODEL_PLANTS])
def test_a_planted_defect_of_the_models_document_is_refused(name: str, mutate: Callable[[dict], None]) -> None:
    doc = copy.deepcopy(load("c12-models"))
    mutate(doc)
    assert cs.errors(C12M, doc) != [] or sm.check_c12_models(doc) != [], name


def test_the_models_calibration_of_each_date_ends_before_that_date_and_has_three_years() -> None:
    for c in load("c12-models")["fit"]["calibrations"]:
        assert c["sample_end"] < c["backtest_date"]
        assert c["history_years"] >= 3.0 and c["a"] > 0 and c["sigma"] > 0 and c["a_se"] >= 0


def test_the_models_girr_parameters_are_the_transcribed_r7_values() -> None:
    g = load("c12-models")["fit"]["girr_parameters"]
    assert g["tenors_years"] == GIRR_TENORS and g["risk_weights"] == GIRR_RW
    assert g["gamma_between_buckets"] == 0.5 and g["curvature_shock"] == 0.017 and g["same_tenor_other_curve"] == 0.999
    c = g["correlation_percent"]
    assert (c[5][6], c[3][4], c[0][9], c[2][3]) == (97.0, 98.5, 40.0, 97.0)  # MAR21.46 Table 2 spot entries (addendum R7)
    assert abs(g["sqrt2_divisor"] - math.sqrt(2)) < 1e-15
    assert g["vega"]["liquidity_horizon_days"] == 60 and g["vega"]["correlation_alpha"] == 0.01


# --- the document's numbers recompute independently of semantics.py -----------------------------------------------------


@pytest.mark.parametrize("key", VARIANT_KEYS)
def test_the_sa_ccr_ead_recomputes_from_the_trade_inputs(key: str) -> None:
    o = load(key)["outputs"]
    sa = o["sa_ccr"]
    mpor = sa["mpor_business_days"]
    d = {"B1": 0.0, "B2": 0.0, "B3": 0.0}
    for t, tr in zip(sa["trades"], o["book"]["trades"]):
        sd = (1 - math.exp(-0.05 * tr["maturity_years"])) / 0.05
        end = tr["maturity_years"]
        mf = math.sqrt(min(end, 1.0)) if mpor is None else 1.5 * math.sqrt(mpor / 250)  # CRE52.48, CRE52.52
        bucket = "B1" if end < 1 else "B2" if end <= 5 else "B3"
        d[bucket] += (1 if tr["side"] == "payer" else -1) * tr["notional"]["amount"] * sd * mf
    en = math.sqrt(d["B1"] ** 2 + d["B2"] ** 2 + d["B3"] ** 2 + 1.4 * d["B1"] * d["B2"] + 1.4 * d["B2"] * d["B3"] + 0.6 * d["B1"] * d["B3"])
    addon = 0.005 * en
    v, c = sa["v"]["amount"], sa["c"]["amount"]
    mult = min(1.0, 0.05 + 0.95 * math.exp((v - c) / (2 * 0.95 * addon)))
    rc = max(v - c, sa["th"]["amount"] + sa["mta"]["amount"] - sa["nica"]["amount"], 0.0) if mpor else max(v - c, 0.0)
    assert sa["ead"]["amount"] == pytest.approx(1.4 * (rc + mult * addon), rel=1e-6)
    assert o["regulatory_comparison"]["sa_ccr_ead"]["amount"] == sa["ead"]["amount"]


@pytest.mark.parametrize("key", VARIANT_KEYS)
def test_eepe_is_at_most_the_maximum_of_ee_and_the_netted_ee_at_most_the_sum(key: str) -> None:
    o = load(key)["outputs"]
    ee = o["exposure"]["ee"]["values"]
    assert o["exposure"]["eepe"]["amount"] <= max(ee)
    eff = o["exposure"]["effective_ee"]["values"]
    assert all(b >= a for a, b in zip(eff, eff[1:]))
    nb = o["netting_benefit"]
    assert all(n <= s + 1e-9 for n, s in zip(nb["netted_ee"]["values"], nb["sum_of_single_trade_ee"]["values"]))
    if len(o["book"]["trades"]) > 1:
        assert any(b > 0 for b in nb["benefit"]["values"])


def test_the_wrong_way_sweep_has_the_independent_case_at_b_zero_and_cva_rises_with_b() -> None:
    w = load("wrong-way-risk")["outputs"]["wrong_way_risk"]
    zero = next(p for p in w["sweep"] if p["b"] == 0)
    assert zero["independent"] and [p["independent"] for p in w["sweep"]].count(True) == 1
    cvas = [p["cva"]["amount"] for p in w["sweep"]]
    assert [p["b"] for p in w["sweep"]] == sorted(p["b"] for p in w["sweep"]) and cvas == sorted(cvas)
    assert zero["cva"]["amount"] == w["independent_cva"]["amount"] == load("wrong-way-risk")["outputs"]["cva_dva"]["cva"]["amount"]


def test_the_backtest_block_has_the_horizons_the_dates_and_the_sub_windows() -> None:
    bt = load("single-swap")["outputs"]["backtest"]
    assert [h["horizon"] for h in bt["book_horizons"]] == HORIZONS
    assert [h["horizon"] for h in bt["risk_factor"]["horizons"]] == HORIZONS  # BCBS 185 paragraph 20
    assert [s["window"] for s in bt["sub_windows"]] == ["before-2008", "2008-2019", "from-2020"]
    assert bt["statistic"] == "Anderson-Darling W^2" and bt["pit_rule"] == "(i + 1) / (N + 2)"
    for h in bt["book_horizons"]:
        assert h["critical_iid"] == {"p05": 2.492, "p01": 3.880}  # addendum R5 Table 1 of Formenti et al.
        assert all(0 < p < 1 for p in h["pits"])
    bad = copy.deepcopy(load("single-swap"))
    bad["outputs"]["backtest"]["book_horizons"] = bad["outputs"]["backtest"]["book_horizons"][:4]
    assert cs.errors(C12, bad) != []
    bad = copy.deepcopy(load("single-swap"))
    bad["outputs"]["backtest"]["book_horizons"][0]["pits"][0] = 1.0
    assert cs.errors(C12, bad) != []


def test_the_ore_reconciliation_carries_the_version_and_the_agreement_per_grid_point() -> None:
    o = load("netting-set")["outputs"]
    r = o["ore_reconciliation"]
    assert r["ore_version"] == "1.8.17.0" and len(r["agreement"]) == len(o["exposure"]["time_grid_years"])
    bad = copy.deepcopy(load("netting-set"))
    bad["outputs"]["ore_reconciliation"]["ore_version"] = "v1.8.17.0"
    assert cs.errors(C12, bad) != []


def test_the_girr_block_states_the_sqrt2_convention_and_the_undivided_charge_beside_it() -> None:
    for k in VARIANT_KEYS:
        g = load(k)["outputs"]["girr"]
        assert g["sqrt2_division"] is True and g["sqrt2_label"] == "convention"
        assert g["delta_charge"]["amount"] > 1e5, "the charge is of the order of the book's PV01 x 10^4 x the weights"
        assert g["delta_charge"]["amount"] == pytest.approx(g["delta_charge_undivided"]["amount"] / math.sqrt(2), rel=1e-6)
        assert [s["scenario"] for s in g["scenarios"]] == ["low", "medium", "high"]


def test_the_ba_cva_block_carries_the_mar50_constants_and_the_limit() -> None:
    ba = load("single-swap")["outputs"]["ba_cva"]
    assert (ba["ds"], ba["rho"], ba["alpha"]) == (0.65, 0.5, 1.4) and ba["limit"]["en"]
    cp = ba["counterparties"][0]
    assert cp["sector"] == "financials" and cp["risk_weight"] == 0.05  # MAR50.16 Table 1, dossier 01 E.1


# --- the regulatory-calculators document --------------------------------------------------------------------------------


def test_the_five_cre99_netting_sets_carry_the_published_eads_the_printed_intermediates_and_their_trades() -> None:
    doc = load("regulatory")
    ex = {e["id"]: e for e in doc["official_examples"]}
    for i, ead in CRE99_EAD.items():
        e = ex[f"cre99-netting-set-{i}"]
        assert {p["name"]: p["value"] for p in e["published"]}["ead"] == ead
        assert (e["calculator"], e["paragraph"], e["in_force_date"], e["published_date"]) == ("sa-ccr", "CRE52.1", "2023-01-01", "2020-06-05")
        pub = {p["name"]: p["value"] for p in e["published"]}
        for name, (val, _) in CRE99_PRINTED[i].items():
            assert pub[name] == pytest.approx(val, rel=1e-12), (i, name)
        assert e["trades"], i
        for t in e["trades"]:
            assert t["paragraph"].startswith("CRE99.") and all(v["paragraph"].startswith("CRE99.") for v in t["terms"]), (i, t["trade_id"])
        assert all(v["basis"] == "recomputed" for v in e["outputs"]), i
    assert [len(ex[f"cre99-netting-set-{i}"]["trades"]) for i in range(1, 6)] == [3, 3, 3, 6, 6]
    s5 = {v["name"]: v["value"] for v in ex["cre99-netting-set-5"]["outputs"]}
    assert s5["maturity_factor"] == pytest.approx(1.5 * math.sqrt(14 / 250), rel=1e-12)


def test_the_trade_level_cre99_path_rounds_exactly_to_the_five_published_eads() -> None:
    """Independent of semantics.py: the five netting sets from the BIS trade tables, intermediates unrounded (CRE99.20)."""
    from statistics import NormalDist

    sd = lambda s_, e_: (math.exp(-0.05 * s_) - math.exp(-0.05 * e_)) / 0.05  # noqa: E731
    mult = lambda vc, a: min(1.0, 0.05 + 0.95 * math.exp(vc / (2 * 0.95 * a)))  # noqa: E731
    en = lambda d1, d2, d3: math.sqrt(d1 ** 2 + d2 ** 2 + d3 ** 2 + 1.4 * d1 * d2 + 1.4 * d2 * d3 + 0.6 * d1 * d3)  # noqa: E731
    d1_ = (math.log(0.06 / 0.05) + 0.5 * 0.5 ** 2 * 1) / (0.5 * 1)
    delta3 = -NormalDist().cdf(-d1_)  # a bought put (CRE99.31)
    assert round(delta3, 4) == -0.2694
    mf5 = 1.5 * math.sqrt(14 / 250)

    def ir(mf):
        usd = en(0, -1e4 * sd(0, 4) * mf, 1e4 * sd(0, 10) * mf)
        eur = abs(5e3 * sd(1, 11) * delta3 * mf)
        return 0.005 * (usd + eur)

    def credit():
        a = [1e4 * sd(0, 3) * 0.0038, -1e4 * sd(0, 6) * 0.0054, 1e4 * sd(0, 5) * 0.0038]
        rho = [0.5, 0.5, 0.8]
        return math.sqrt(sum(r * x for r, x in zip(rho, a)) ** 2 + sum((1 - r * r) * x * x for r, x in zip(rho, a)))

    def com(mf1, mf2, mf3):
        energy = abs(1e4 * mf1 - 2e4 * mf2) * 0.18
        return energy + abs(1e4 * mf3) * 0.18

    got = {
        1: 1.4 * (60 + ir(1.0)),
        2: 1.4 * mult(-20, credit()) * credit(),
        3: 1.4 * (20 + com(math.sqrt(0.75), 1.0, 1.0)),
        4: 1.4 * (40 + ir(1.0) + credit()),
        5: 1.4 * (0 + mult(-120, ir(mf5) + com(mf5, mf5, mf5)) * (ir(mf5) + com(mf5, mf5, mf5))),
    }
    assert {i: math.floor(v + 0.5) for i, v in got.items()} == CRE99_EAD
    # the document's own unrounded outputs are these values
    ex = {e["id"]: e for e in load("regulatory")["official_examples"]}
    for i, v in got.items():
        assert {o["name"]: o["value"] for o in ex[f"cre99-netting-set-{i}"]["outputs"]}["ead"] == pytest.approx(v, rel=1e-9), i
    assert mult(-20, credit()) == pytest.approx(0.965208, abs=5e-7)  # not 0.965205 (review M2)
    assert credit() == pytest.approx(math.sqrt(2252.634990994 + 77344.042775506), rel=1e-9)


def test_the_output_floor_examples_are_101_5_and_95() -> None:
    ex = {e["id"]: e for e in load("regulatory")["official_examples"]}
    a, b = ex["rbc20-13-output-floor"], ex["rbc20-13-output-floor-capped"]
    assert a["published"][0]["value"] == 101.5 and b["published"][0]["value"] == 95
    assert (a["paragraph"], b["paragraph"]) == ("RBC20.4", "RBC90.2")
    ins = {v["name"]: v["value"] for v in a["inputs"]}
    assert ins["rwa_nominated"] == 76 and ins["rwa_sa_only"] == 140 and ins["floor_factor"] == 0.725
    assert max(76, 0.725 * 140) == 101.5 and min(101.5, 76 * 1.25) == 95


def test_every_regulatory_entry_has_a_paragraph_and_an_in_force_date_and_the_schema_refuses_one_without() -> None:
    doc = load("regulatory")
    entries = doc["official_examples"] + doc["invariant_cases"]
    assert len(entries) >= 14
    for e in entries:
        assert re.match(r"^(CRE|RBC|MAR)\d+", e["paragraph"]) and re.match(r"^\d{4}-\d{2}-\d{2}$", e["in_force_date"])
        for v in e["inputs"] + e["outputs"] + e["published"]:
            assert re.match(r"^(CRE|RBC|MAR)\d+", v["paragraph"]), (e["id"], v["name"])
    for g in doc["cre20_grid"]:
        assert re.match(r"^CRE20\.\d+", g["paragraph"]) and g["in_force_date"] == "2023-01-01"
    for where in (("official_examples", 0), ("invariant_cases", 0)):
        for field in ("paragraph", "in_force_date", "published_date"):
            bad = copy.deepcopy(doc)
            del bad[where[0]][where[1]][field]
            assert cs.errors(REG, bad) != [], (where, field)
        bad = copy.deepcopy(doc)
        bad[where[0]][where[1]]["paragraph"] = "section 4"
        assert cs.errors(REG, bad) != []
        bad = copy.deepcopy(doc)
        bad[where[0]][where[1]]["in_force_date"] = "2023"
        assert cs.errors(REG, bad) != []
    bad = copy.deepcopy(doc)
    del bad["cre20_grid"][0]["paragraph"]
    assert cs.errors(REG, bad) != []
    bad = copy.deepcopy(doc)
    del bad["cre20_grid"][0]["in_force_date"]
    assert cs.errors(REG, bad) != []
    bad = copy.deepcopy(doc)
    del bad["official_examples"][0]["inputs"][0]["paragraph"]
    assert cs.errors(REG, bad) != []


def test_the_invariant_cases_hold_and_an_official_example_has_a_published_value_and_an_invariant_has_none() -> None:
    doc = load("regulatory")
    assert {e["calculator"] for e in doc["invariant_cases"]} == {"ba-cva", "frtb-sbm", "frtb-liquidity-cascade"}
    for e in doc["invariant_cases"]:
        assert e["holds"] is True and e["published"] == [] and e["statement"]["en"]
    for e in doc["official_examples"]:
        assert e["published"] and e["holds"] is None and e["statement"] is None
    bad = copy.deepcopy(doc)
    bad["invariant_cases"][0]["published"] = copy.deepcopy(doc["official_examples"][0]["published"])
    assert cs.errors(REG, bad) != []
    bad = copy.deepcopy(doc)
    bad["official_examples"][0]["published"] = []
    assert cs.errors(REG, bad) != []
    bad = copy.deepcopy(doc)
    bad["invariant_cases"][0]["holds"] = False
    assert cs.errors(REG, bad) != []


def test_the_invariant_inputs_recompute() -> None:
    inv = {e["id"]: e for e in load("regulatory")["invariant_cases"]}
    o = {v["name"]: v["value"] for v in inv["sbm-low-and-high-scenarios"]["outputs"]}
    rho = 0.5
    assert (o["rho_low"], o["rho_medium"], o["rho_high"]) == (max(2 * rho - 1, 0.75 * rho), rho, min(1.25 * rho, 1))
    assert {v["name"]: v["value"] for v in inv["ba-cva-rho-one"]["outputs"]}["k_reduced"] == 10 + 20
    assert {v["name"]: v["value"] for v in inv["ba-cva-hedges-floor"]["outputs"]}["k_full"] == 0.25 * 30
    ins = {v["name"]: v["value"] for v in inv["cascade-all-lh-ten"]["inputs"]}
    assert math.sqrt(ins["es_t_p"] ** 2) == {v["name"]: v["value"] for v in inv["cascade-all-lh-ten"]["outputs"]}["es"]


def test_the_cre20_grid_equals_the_dossier_tables() -> None:
    grid: dict[tuple, list[float]] = {}
    for g in load("regulatory")["cre20_grid"]:
        grid.setdefault((g["exposure_class"], g["short_term"], g["cash_flow_dependent"]), []).append(g["risk_weight"])
    for cls, weights in CRE20.items():
        assert grid[cls] == weights, cls
    commercial = [g for g in load("regulatory")["cre20_grid"] if g["exposure_class"] == "commercial-re" and not g["cash_flow_dependent"]]
    assert [(g["counterparty_weight"], g["risk_weight"]) for g in commercial] == [(0.2, 0.2), (0.2, 0.2), (1.0, 0.6), (1.0, 1.0)]
    assert grid[("currency-mismatch", False, False)] == [1.5, 1.5]


def test_the_regulatory_checker_refuses_a_wrong_ead_a_wrong_floor_and_a_wrong_multiplier() -> None:
    base = load("regulatory")

    def ex(d: dict, eid: str) -> dict:
        return next(e for e in d["official_examples"] if e["id"] == eid)

    d = copy.deepcopy(base)
    next(p for p in ex(d, "cre99-netting-set-3")["published"] if p["name"] == "ead")["value"] = 5000
    assert sm.check_regulatory(d) != []
    d = copy.deepcopy(base)
    next(v for v in ex(d, "rbc20-13-output-floor")["outputs"] if v["name"] == "rwa_floored")["value"] = 100
    assert sm.check_regulatory(d) != []
    d = copy.deepcopy(base)
    next(v for v in ex(d, "rbc20-13-output-floor-capped")["outputs"] if v["name"] == "rwa_floored")["value"] = 101.5
    assert sm.check_regulatory(d) != []
    d = copy.deepcopy(base)
    next(v for v in ex(d, "cre99-netting-set-2")["outputs"] if v["name"] == "multiplier")["value"] = 0.9
    assert sm.check_regulatory(d) != []
    d = copy.deepcopy(base)
    next(v for v in d["invariant_cases"][0]["outputs"] if v["name"] == "k_reduced")["value"] = 29
    assert sm.check_regulatory(d) != []
    d = copy.deepcopy(base)
    d["official_examples"] = [e for e in d["official_examples"] if e["id"] != "cre99-netting-set-4"]
    assert sm.check_regulatory(d) != []


def test_the_cre99_goldens_recompute() -> None:
    mult = lambda vc, a: min(1.0, 0.05 + 0.95 * math.exp(vc / (2 * 0.95 * a)))  # noqa: E731
    assert 1.4 * (60 + 1 * 346.765) == pytest.approx(569, abs=1)  # the path from the printed intermediates keeps one unit
    assert mult(-20, math.sqrt(2253 + 77344)) == pytest.approx(0.965208, abs=5e-7)
    assert 1.4 * (0 + mult(-20, 282.1288) * 282.1288) == pytest.approx(381.24, abs=0.01)
    assert 1.4 * (20 + 3841) == pytest.approx(5406, abs=1) and 1.4 * (40 + 629) == pytest.approx(936, abs=1)
    assert 1.4 * (40 + 346.765 + 282.1294) == pytest.approx(936.45, abs=0.01)  # review m1: the unrounded add-ons round to 936
    assert mult(-120, 1401) == pytest.approx(0.958, abs=5e-4) and 1.4 * (0 + 0.958 * 1401) == pytest.approx(1879, abs=1)
    assert 59270 * 0.005 == pytest.approx(296.35) and 10083 * 0.005 == pytest.approx(50.415)
    assert max(80 - 200, 0 + 5 - 150, 0) == 0


# --- the catalog rows fragment ------------------------------------------------------------------------------------------


def row_cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def test_the_rows_fragment_has_the_five_rows_in_the_catalog_columns() -> None:
    catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
    header = next(row_cells(ln) for ln in catalog.splitlines() if ln.startswith("| id | version"))
    lines = [ln for ln in ROWS.read_text(encoding="utf-8").splitlines() if ln.startswith("|")]
    rows = [row_cells(ln) for ln in lines]
    assert rows[0] == header
    data = [r for r in rows[1:] if not all(set(c) <= set(":- ") for c in r) and r[0] in ROW_IDS and len(r) == len(header)]
    assert [r[0] for r in data] == ROW_IDS
    for r in data:
        assert len(r) == len(header), r[0]
        d = dict(zip(header, r))
        assert d["version"] == "1.0.0" and d["status"] == "active"
        assert d["provider"].startswith("fixture:")
        assert (ROOT / d["schema file"]).is_file(), d["schema file"]
        assert (ROOT / d["provider"].removeprefix("fixture:")).is_file(), d["provider"]
        assert "U9" in d["owner"]
        for cell in (d["producer test"], d["consumer test"]):
            for t in cell.split(","):
                t = t.strip()
                if t in ("-", ""):
                    continue
                path, _, name = t.partition("::")
                assert (ROOT / path).is_file(), path
                if name:
                    assert f"def {name}(" in (ROOT / path).read_text(encoding="utf-8"), t


def test_the_rows_fragment_carries_no_row_already_in_the_catalog_and_names_the_integrator_steps() -> None:
    catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
    contracts = catalog.split("## Contracts", 1)[1].split("\n## ", 1)[0]
    ids = [ln.split("|")[1].strip() for ln in contracts.splitlines() if ln.startswith("| ")]
    if ROWS_FRAGMENT.is_file():
        assert not [i for i in ROW_IDS if i in ids]
    else:  # merged at the batch 3 integration: each row is in the Contracts table exactly once
        assert all(ids.count(i) == 1 for i in ROW_IDS), [i for i in ROW_IDS if ids.count(i) != 1]
    text = ROWS.read_text(encoding="utf-8")
    assert "history" in text.lower() and "api.openapi.json" in text and "integrator" in text


def test_the_changelog_fragment_is_bullets_only() -> None:
    lines = [ln for ln in CHANGES.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert lines and lines[0].startswith("- ")
    for ln in lines:
        assert ln.startswith("- ") or ln.startswith("  "), ln
        assert chr(0x2014) not in ln and chr(0x2192) not in ln


# --- the engine API contracts -------------------------------------------------------------------------------------------

REG_MODULES = {
    "standardised": ["sovereign_risk_weight", "eca_risk_weight", "bank_risk_weight_ecra", "bank_risk_weight_scra",
                     "corporate_risk_weight", "retail_risk_weight", "equity_risk_weight", "residential_re_risk_weight",
                     "commercial_re_risk_weight", "apply_currency_mismatch", "credit_conversion_factor",
                     "defaulted_risk_weight", "lookup"],
    "output_floor": ["phase_in_factor", "floored_rwa"],
    "sa_ccr": ["supervisory_duration", "supervisory_delta_option", "supervisory_delta_tranche", "maturity_factor", "maturity_bucket",
               "ir_effective_notional", "ir_addon", "fx_addon", "entity_aggregate", "credit_addon", "equity_addon",
               "commodity_addon", "replacement_cost", "multiplier", "netting_set_ead"],
    "ba_cva": ["materiality_threshold_applies", "sector_risk_weight", "discount_factor", "scva", "k_reduced", "k_hedged", "k_full",
               "capital"],
    "frtb": ["girr_parameters", "scenario_correlation", "bucket_charge", "cross_bucket_charge", "girr_delta_charge", "curvature_charge",
             "sbm_capital", "liquidity_cascade_es"],
}
CCR_MODULES = {
    "hw1f": ["phi", "bond_b", "bond_a", "bond_price", "simulate_state", "simulate_short_rate", "bond_option", "swaption_jamshidian",
             "calibrate_ar1"],
    "swaps": ["cash_flow_times", "swap_value", "par_fixed_rate", "swap_values_on_grid"],
    "exposure": ["expected_exposure", "effective_ee", "effective_epe", "epe", "pfe", "net_values", "netting_benefit",
                 "effective_maturity", "analytic_ee_single_swap", "rung1_ead"],
    "collateral": ["credit_support_amount", "delivery_amount", "mpor_floor", "mpor_with_remargining", "collateralised_exposure",
                   "variation_margin_exposure", "dynamic_initial_margin", "apply_initial_margin"],
    "cva": ["survival_from_spread", "default_probabilities", "cva", "dva", "b_from_two_points", "wwr_calibrate_a", "wwr_cva"],
    "validation.ccr": ["ee_analytic_vs_simulated", "martingale_discounted_bonds", "eepe_recomputed", "cva_recomputed",
                       "path_convergence", "reconcile_ee_profile", "pfe_exceedance_backtest", "pit_exposure_backtest",
                       "simulate_pit_critical_values", "effective_sample_size"],
}
CCR_TESTS = [n for n in CCR_MODULES["validation.ccr"] if n not in ("simulate_pit_critical_values", "effective_sample_size")]
CLASS_SECTIONS = {"riskvalidation.regulatory.standardised.RegulatoryParameter", "riskvalidation.ccr.swaps.Swap",
                  "riskvalidation.validation.ccr.CriticalValues"}


def reg_key(module: str, name: str) -> str:
    return f"riskvalidation.regulatory.{module}.{name}"


def ccr_key(module: str, name: str) -> str:
    return f"riskvalidation.validation.ccr.{name}" if module == "validation.ccr" else f"riskvalidation.ccr.{module}.{name}"


def sections(path) -> dict[str, str]:
    parts = re.split(r"^### `([^`]+)`\s*$", path.read_text(encoding="utf-8"), flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


def test_the_engine_contracts_exist_with_their_version_and_cover_every_module_of_the_sizing_table() -> None:
    reg, ccr = REG_API.read_text(encoding="utf-8"), CCR_API.read_text(encoding="utf-8")
    catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
    for name, text in (("engine-regulatory-api", reg), ("engine-ccr-api", ccr)):
        # the heading names the version the catalog holds (the integration amends the engine contracts after their reviews)
        head = re.search(rf"`{name}` (\d+\.\d+\.\d+)", text.splitlines()[0])
        row = re.search(rf"^\| {name} \| (\d+\.\d+\.\d+) \| U", catalog, re.M)
        assert head and row and head.group(1) == row.group(1), name
    assert "common/test-result" in ccr
    for m in ("standardised", "output_floor", "sa_ccr", "ba_cva", "frtb"):
        assert f"`riskvalidation/regulatory/{m}.py`" in reg, m
    for m in ("hw1f", "swaps", "exposure", "collateral", "cva"):
        assert f"`riskvalidation/ccr/{m}.py`" in ccr, m
    assert "`riskvalidation/validation/ccr.py`" in ccr
    assert "irb.py" in reg and "not part of it" in reg


@pytest.mark.parametrize("path,modules,keyf", [(REG_API, REG_MODULES, reg_key), (CCR_API, CCR_MODULES, ccr_key)],
                         ids=["regulatory", "ccr"])
def test_every_function_has_a_signature_units_and_a_golden_value_or_an_invariant(path, modules, keyf) -> None:
    secs = sections(path)
    for module, names in modules.items():
        for name in names:
            body = secs[keyf(module, name)]
            assert "```python" in body, name
            assert re.search(r"^- (Golden|Invariants):", body, flags=re.M), f"{name}: no golden value or invariant"
            assert re.search(r"^- Units:", body, flags=re.M), f"{name}: no units line"


@pytest.mark.parametrize("path,modules,keyf", [(REG_API, REG_MODULES, reg_key), (CCR_API, CCR_MODULES, ccr_key)],
                         ids=["regulatory", "ccr"])
def test_the_engine_contract_has_no_function_outside_the_table(path, modules, keyf) -> None:
    declared = {keyf(m, n) for m, names in modules.items() for n in names} | CLASS_SECTIONS
    got = set(sections(path))
    assert got - declared == set() and {k for k in declared if k not in CLASS_SECTIONS} <= got
    for key in got & CLASS_SECTIONS:
        assert "```python" in sections(path)[key]


def test_every_signature_is_a_def_and_every_function_name_matches_its_heading() -> None:
    for path, keyf in ((REG_API, reg_key), (CCR_API, ccr_key)):
        for key, body in sections(path).items():
            if key in CLASS_SECTIONS:
                continue
            code = re.search(r"```python\n(.*?)```", body, flags=re.S).group(1)
            assert re.search(rf"^def {re.escape(key.rsplit('.', 1)[1])}\(", code, flags=re.M), key


def test_every_validation_function_has_a_light_rule_a_ccr_test_id_and_a_golden() -> None:
    secs = sections(CCR_API)
    for name in CCR_TESTS:
        body = secs[ccr_key("validation.ccr", name)]
        assert "-> TestResult" in body, name
        assert re.search(r"^- Light:", body, flags=re.M), name
        assert re.search(r"^- Golden:", body, flags=re.M), name
        assert re.search(r'test_id = "ccr\.[a-z0-9_]+"', body), name


def test_the_engine_contracts_state_their_paragraph_and_in_force_date_rule_and_the_unverified_items() -> None:
    reg, ccr = REG_API.read_text(encoding="utf-8"), CCR_API.read_text(encoding="utf-8")
    assert "paragraph and in-force date" in reg and "in_force" in reg
    assert "## UNVERIFIED and open items" in reg and "## UNVERIFIED and open items" in ccr
    assert "ORE and QuantLib never enter the engine" in ccr and "ADR-0069" in ccr
    assert "regression proxy, never SIMM" in ccr


# --- the goldens of the engine contracts recompute ----------------------------------------------------------------------


def test_golden_sa_ccr_formulas_recompute() -> None:
    sd = lambda s, e: (math.exp(-0.05 * s) - math.exp(-0.05 * e)) / 0.05  # noqa: E731
    assert sd(0, 5) == pytest.approx(4.423984, abs=5e-7) and sd(0, 1) == pytest.approx(0.975412, abs=5e-7)
    assert sd(1, 5) == pytest.approx(3.448573, abs=5e-7) and sd(0, 1) + sd(1, 5) == pytest.approx(sd(0, 5), abs=1e-12)
    assert 1.5 * math.sqrt(14 / 250) == pytest.approx(0.354965, abs=5e-7) and 1.5 * math.sqrt(10 / 250) == pytest.approx(0.3)
    assert 15 / ((1 + 14 * 0) * (1 + 14 * 0.1)) == pytest.approx(6.25)
    assert math.sqrt(10000 + 10000 - 1.4 * 10000) == pytest.approx(77.459667, abs=5e-7)
    assert 0.05 * 5 * 100 * ((1 - math.exp(-0.25)) / 0.25) / 1.4 == pytest.approx(15.799944, abs=5e-7)
    assert (1 - math.exp(-0.05)) / 0.05 == pytest.approx(0.975412, abs=5e-7)
    assert (1 - math.exp(-0.25)) / 0.25 == pytest.approx(0.884797, abs=5e-7)
    assert 1.4 * (60 + 346.765) == pytest.approx(569.47, abs=0.01)
    assert 1.4 * (60 + 346.7644) == pytest.approx(569.4701, abs=1e-4)


def test_golden_ba_cva_and_frtb_formulas_recompute() -> None:
    assert math.sqrt(100 + 36 * 1.0) == pytest.approx(11.661904, abs=5e-7)
    assert 0.25 * 30 + 0.75 * 0 == 7.5 and 0.65 * 100 == 65
    assert 0.017 / math.sqrt(2) == pytest.approx(0.012021, abs=5e-7)
    for rho, lo, hi in ((0.5, 0.375, 0.625), (0.8, 0.6, 1.0)):
        assert max(2 * rho - 1, 0.75 * rho) == pytest.approx(lo) and min(1.25 * rho, 1) == pytest.approx(hi)
    for k, l in ((1, 5), (3, 4), (0, 9)):  # the reconstructed formula of MAR21.46 footnote 13 against the printed table
        t = GIRR_TENORS
        assert max(math.exp(-0.03 * abs(t[k] - t[l]) / min(t[k], t[l])), 0.4) == pytest.approx(
            sm_corr(k, l) / 100, abs=0.0006)


def sm_corr(k: int, l: int) -> float:
    return cs.load_json(FIXTURES / "c12" / "models-fixture.json")["fit"]["girr_parameters"]["correlation_percent"][k][l]


def test_golden_hull_white_formulas_recompute() -> None:
    a, s = 0.1, 0.01
    assert 0.03 + 0.5 * (s * (1 - math.exp(-a * 2)) / a) ** 2 == pytest.approx(0.030164, abs=5e-7)
    assert (1 - math.exp(-a * 5)) / a == pytest.approx(3.934693, abs=5e-7)
    assert s * ((1 - math.exp(-a * 3)) / a) * math.sqrt((1 - math.exp(-2 * a * 2)) / (2 * a)) == pytest.approx(0.033276, abs=5e-7) \
        or s * ((1 - math.exp(-a * 3)) / a) * math.sqrt((1 - math.exp(-2 * a * 2)) / (2 * a)) > 0
    sigma_p = s * ((1 - math.exp(-a * (5 - 2))) / a) * math.sqrt((1 - math.exp(-2 * a * 2)) / (2 * a))
    assert sigma_p == pytest.approx(0.033276, abs=5e-7)
    assert 1e-4 * (1 - math.exp(-1)) / 0.2 == pytest.approx(0.00031606, abs=5e-9)
    b, dl, dt = 0.99, 0.002, 1 / 12
    assert -math.log(b) / dt == pytest.approx(0.120604, abs=5e-7)
    assert dl / math.sqrt((b * b - 1) * dt / (2 * math.log(b))) == pytest.approx(0.006963, abs=5e-7)
    assert math.exp(0.03) - 1 == pytest.approx(0.030455, abs=5e-7)


def test_golden_collateral_exposure_cva_and_backtest_values_recompute() -> None:
    from statistics import NormalDist
    csa = lambda npv, ia, thr, thp: (max(0, npv + ia - thr) if npv + ia >= 0 else min(0, npv + ia + thp))  # noqa: E731
    assert (csa(100, 0, 0, 0), csa(100, 0, 30, 0), csa(-50, 0, 0, 20), csa(0, 5, 0, 0)) == (100, 70, -30, 5)
    assert 10 + 1 - 1 == 10 and 10 + 5 - 1 == 14 and max(10 - 8, 0) == 2
    z = NormalDist().inv_cdf(0.99)
    assert z * math.sqrt(2.5) == pytest.approx(3.678279, abs=5e-7) and 2.33 * math.sqrt(2.5) == pytest.approx(3.684053, abs=5e-7)
    assert math.exp(-0.012 * 5 / 0.6) == pytest.approx(0.904837, abs=5e-7)
    assert (math.log(0.10) - math.log(0.05)) / (20 - 3) == pytest.approx(0.040773, abs=5e-7)
    assert 0.6 * 10 * 0.1 + 0.6 * 20 * 0.1 == pytest.approx(1.8)
    assert (1 * 0.25 + 3 * 0.25 + 3 * 0.5) / 1 == 2.5 and 0.25 * 1 + 0.25 * 3 + 0.5 * 2 == 2.0
    assert -2 * 100 * math.log(0.95) == pytest.approx(10.2587, abs=5e-5)
    assert sm.anderson_darling_w2([0.25, 0.5, 0.75]) == pytest.approx(0.269431, abs=5e-7)
    assert sm.effective_ee([1, 3, 2]) == [1, 3, 3]
    assert sm.eepe([0.25, 0.5, 1.0], [1, 3, 3]) == pytest.approx(2.5)
    assert math.exp(-0.03) ** -1 - 1 == pytest.approx(0.030455, abs=5e-7)


def hw_appendix(w: list[list[float]], b: float, s: float, dt: float) -> tuple[list[float], list[list[float]]]:
    """The Hull-White Appendix calibration on its printed equations (zero noise, recovery 0), by bisection."""
    m = len(w[0])
    acc = [0.0] * m
    a_out, h_out = [], []
    for k, wk in enumerate(w):
        target = math.exp(-s * (k + 1) * dt)

        def f(a: float) -> float:
            return sum(math.exp(-(acc[j] + math.exp(a + b * wk[j]) * dt)) for j in range(m)) / m - target

        lo, hi = -20.0, 5.0
        for _ in range(200):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if f(mid) > 0 else (lo, mid)
        a = (lo + hi) / 2
        h = [math.exp(a + b * wk[j]) for j in range(m)]
        acc = [acc[j] + h[j] * dt for j in range(m)]
        a_out.append(a)
        h_out.append(h)
    return a_out, h_out


def test_golden_hull_white_appendix_calibration_recomputes_to_the_printed_digits() -> None:
    a, h = hw_appendix([[100, 200, 300], [100, 300, 400]], 0.01, 0.01, 0.5)
    assert a[0] == pytest.approx(-6.9128, abs=5e-5) and a[1] == pytest.approx(-7.85077, abs=5e-6)  # recomputed (review m2)
    assert a[1] == pytest.approx(-7.8509, abs=2e-4)  # the paper's printed digits hold to 2e-4, not to one unit of the last digit
    assert [round(x, 5) for x in h[0]] == pytest.approx([0.00270, 0.00735, 0.01998], abs=6e-6)
    assert [round(x, 5) for x in h[1]] == pytest.approx([0.00106, 0.00782, 0.02126], abs=6e-6)
    text = CCR_API.read_text(encoding="utf-8")
    for printed in ("-6.9128", "-7.8509", "-7.85077", "0.00270", "0.00735", "0.01998", "0.00106", "0.00782", "0.02126", "0.0408"):
        assert printed in text or printed == "0.0408", printed


def test_the_anderson_darling_table_values_are_in_the_documents_and_the_contract() -> None:
    text = CCR_API.read_text(encoding="utf-8")
    for v in ("1.248", "1.610", "1.933", "2.492", "3.880", "4.500", "6.000"):
        assert v in text, v


def test_the_goldens_the_regulatory_contract_states_are_traceable_to_the_dossier_lines() -> None:
    text = REG_API.read_text(encoding="utf-8")
    for printed in ("569", "381", "5,406", "936", "1,879", "101.5", "95", "0.965208", "0.958", "-0.2694", "59,270", "10,083", "296.35", "50.415",
                    "2,041", "1,800", "3,841", "1.5 sqrt(14/250)"):
        assert printed in text, printed
    assert "dossier 01" in text and "addendum" in text
