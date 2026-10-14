"""U10-S: the C14 and C15 case contracts, their fixtures, the catalog rows and the engine IRRBB API contract.

The fixtures validate by discovery (tests/contracts/contract_schemas.py) against exactly one schema; the schemas are strict
both ways (a removed or an added key fails); the order of the six shocks, of the four C14 scenarios, of the 19 buckets with
their midpoints, the shock sizes, the tables of the models documents and the thresholds are fixed by the schemas; an NMD
position above its SRP31 Table 4 cap validates only with cap_applied true and the used value at the cap; a shock size for a
currency without a table entry passes only labelled as a Contraste estimate; a money block without its currency fails.

The cross-field checks (the dating rule, the recomputation of every EVE, delta NII, pair, offset, charge and threshold) are
importable functions in ``semantics.py`` that a bake calls on every document it writes; these tests run them over every
committed document (the fixtures and data/derived/C14, C15) and over a table of planted defects, each of which must be
refused by the schema or by the checker. The engine contract names every function of the modules table of
plans/contraste/units/U10-sizing.md with a signature, units and a golden value or an invariant, and its golden values
recompute here. The fixtures are labelled as fixtures and never published as results.
"""
from __future__ import annotations

import copy
import math
import random
import re
from typing import Any, Callable, Iterator

import pytest
from jsonschema import Draft202012Validator

import contract_schemas as cs
import semantics as sm

shape, post_rate, eve_of, dense, close = sm.shape_bp, sm.post_rate, sm.eve_of, sm.dense, sm.close

ROOT = cs.ROOT
FIXTURES = ROOT / "docs" / "contracts" / "fixtures"
SCHEMAS = ROOT / "docs" / "contracts" / "schemas"
API = ROOT / "docs" / "contracts" / "engine" / "irrbb-api.md"
ROWS = ROOT / "docs" / "contracts" / "rows" / "U10.md"

C14, C15 = "c14/variant-valuation-date", "c15/variant-annex1-variant"
C14M, C15M = "c14/models", "c15/models"
SCHEMA_REFS = [C14, C14M, C15, C15M]
FILES = {
    "c14-2021-q4": (C14, FIXTURES / "c14" / "variant-valuation-date-2021-q4-fixture.json"),
    "c14-2022-q4": (C14, FIXTURES / "c14" / "variant-valuation-date-2022-q4-fixture.json"),
    "c14-models": (C14M, FIXTURES / "c14" / "models-fixture.json"),
    "c15-long-uf": (C15, FIXTURES / "c15" / "variant-annex1-variant-long-uf-fixture.json"),
    "c15-offset-on-off": (C15, FIXTURES / "c15" / "variant-annex1-variant-offset-on-off-fixture.json"),
    "c15-cpi-surprise": (C15, FIXTURES / "c15" / "variant-annex1-variant-cpi-surprise-fixture.json"),
    "c15-models": (C15M, FIXTURES / "c15" / "models-fixture.json"),
}
KINDS = {C14: "valuation-date", C15: "annex1-variant"}
ROW_IDS = ["c14-outputs", "c14-models", "c15-outputs", "c15-models", "engine-irrbb-api"]

# --- the dossier values, typed here again (dossier 01 H.2 to H.4, dossier 03 F.2, dossier 05 D) -------------------------

SHOCKS = ["parallel-up", "parallel-down", "steepener", "flattener", "short-up", "short-down"]
MIDPOINTS = [0.0028, 0.0417, 0.1667, 0.375, 0.625, 0.875, 1.25, 1.75, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 12.5, 17.5, 25.0]
CCY21 = ["ARS", "AUD", "BRL", "CAD", "CHF", "CNY", "EUR", "GBP", "HKD", "IDR", "INR", "JPY", "KRW", "MXN", "RUB", "SAR", "SEK",
         "SGD", "TRY", "USD", "ZAR"]
T2024 = {  # dossier 01 H.3, SRP31.90 Table 2: parallel, short, long
    "parallel": [400, 350, 400, 200, 175, 225, 225, 275, 225, 400, 325, 100, 225, 400, 400, 275, 275, 175, 400, 200, 325],
    "short": [500, 425, 500, 275, 250, 300, 350, 425, 375, 500, 475, 100, 350, 500, 500, 375, 425, 250, 500, 300, 500],
    "long": [300, 300, 300, 175, 200, 150, 200, 250, 200, 300, 225, 100, 225, 200, 300, 250, 200, 225, 300, 225, 300],
}
T2016 = {  # dossier 01 H.3, d368 Annex 2 Table 1
    "parallel": [400, 300, 400, 200, 100, 250, 200, 250, 200, 400, 400, 100, 300, 400, 400, 200, 200, 150, 400, 200, 400],
    "short": [500, 450, 500, 300, 150, 300, 250, 300, 250, 500, 500, 100, 400, 500, 500, 300, 300, 200, 500, 300, 500],
    "long": [300, 200, 300, 150, 100, 150, 100, 150, 100, 350, 300, 100, 200, 300, 300, 150, 150, 100, 300, 150, 300],
}
GAMMA = [0.8, 1.2, 0.8, 1.2, 0.8, 1.2]   # SRP31.119 Table 5, in the order of SHOCKS
U = [1.2, 0.8, 0.8, 1.2, 1.2, 0.8]       # SRP31.125 Table 6, in the order of SHOCKS
CAPS = {"retail-transactional": (0.9, 5.0), "retail-non-transactional": (0.7, 4.5), "wholesale": (0.5, 4.0)}
CAPS15 = {"retail-operational": (0.9, 5.0), "retail-non-operational": (0.7, 4.5), "wholesale": (0.5, 4.0)}
CMF_ROWS = {  # dossier 03 F.2 Hoja 9: parallel, short, long (None is "-")
    "canasta-1": (200, 300, 150), "canasta-2": (400, 500, 300), "CLP": (300, 400, 200),
    "UR-nii": (300, None, None), "UR-eve": (200, 250, 150),
}


def load(key: str) -> Any:
    return cs.load_json(FILES[key][1])


def out(key: str) -> dict:
    return load(key)["outputs"]


def fit(key: str) -> dict:
    return load(key)["fit"]


C14_OUT = ["c14-2021-q4", "c14-2022-q4"]
C15_OUT = ["c15-long-uf", "c15-offset-on-off", "c15-cpi-surprise"]
ALL = list(FILES)
VARIANT_KEYS = C14_OUT + C15_OUT
MODEL_KEYS = ["c14-models", "c15-models"]


def ref_of(key: str) -> str:
    return FILES[key][0]


def all_documents() -> list:
    """Every C14 and C15 document the contracts cover: the fixtures and the baked documents under data/derived/C14 and C15."""
    paths = [p for _, p in FILES.values()]
    for case in ("C14", "C15"):
        paths += sorted((ROOT / "data" / "derived" / case).glob("*.json")) if (ROOT / "data" / "derived" / case).is_dir() else []
    return paths


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
    assert doc["provenance"]["generators"] == ["fixture:u10-s-contracts"]
    assert any(i["source"] == "fixture-not-a-result" for i in doc["provenance"]["inputs"])
    ident = doc["variant_id"] if "variant_id" in doc else doc["fit_id"]
    assert str(ident).startswith("fixture-")


def test_every_u10_schema_is_case_folder_conformant_and_case_prefixed() -> None:
    assert cs.case_folder_violations() == []
    files = sorted(p for case in ("c14", "c15") for p in (SCHEMAS / case).glob("*.schema.json"))
    assert {p.relative_to(SCHEMAS).as_posix() for p in files} == {f"{ref}.schema.json" for ref in SCHEMA_REFS}
    for p in files:
        case = p.parent.name
        names = cs.load_json(p).get("$defs", {})
        assert names, p
        for name in names:
            assert name.startswith(case), f"{p.name}: $defs name {name!r} is not prefixed {case!r}"


def test_a_def_two_files_of_one_case_share_has_one_definition() -> None:
    for case in ("c14", "c15"):
        a = cs.load_json(SCHEMAS / case / "models.schema.json")["$defs"]
        b = cs.load_json(next((SCHEMAS / case).glob("variant-*.schema.json")))["$defs"]
        for name in set(a) & set(b):
            assert a[name] == b[name], f"{case}: {name} differs between the models and the variant schema"


def test_every_u10_variant_schema_declares_its_outputs_kind() -> None:
    by_ref = {c.ref: c for c in cs.candidates()}
    for ref, kind in KINDS.items():
        assert by_ref[ref].consts["outputs.kind"] == kind
    for case in ("C14", "C15"):
        assert cs.default_variants().get(case) is None
    assert cs.default_violations() == []


@pytest.mark.parametrize("case", ["C14", "C15"])
def test_a_second_kind_less_variant_schema_fails(case: str) -> None:
    a = cs.Candidate.from_parts(f"{case.lower()}/variant-planted", {"schema": "contraste.case/v1", "case_id": case})
    b = cs.Candidate.from_parts(f"{case.lower()}/variant-planted2", {"schema": "contraste.case/v1", "case_id": case})
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


def root_of(key: str) -> str:
    return "outputs" if key in VARIANT_KEYS else "fit"


def closed_objects(key: str) -> list[tuple[tuple, dict]]:
    doc = load(key)
    return list(objects(doc[root_of(key)], (root_of(key),)))


def probes(key: str) -> list[tuple[tuple, dict]]:
    """One object per shape of the document (its path without indices and its keys), so a probe run stays short."""
    seen, found = set(), []
    for path, obj in closed_objects(key):
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
    assert checked > 60


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
def test_a_wrong_case_id_is_rejected_and_no_fixture_validates_against_another_case(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    bad = copy.deepcopy(doc)
    bad["case_id"] = "C99"
    assert cs.errors(ref, bad) != []
    others = [c.ref for c in cs.candidates() if c.ref != ref and c.ref.split("/")[0] in ("c14", "c15")]
    assert others
    for other in others:
        assert cs.errors(other, doc) != [], f"{key} validates against {other}"


# --- money blocks carry their currency ----------------------------------------------------------------------------------


@pytest.mark.parametrize("key", ALL)
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


MONEY_NAMES = {"amount", "balance", "assets", "liabilities", "gap", "asset_value", "liability_value", "equity_change_100bp_up",
               "total_assets", "total_liabilities", "base_eve", "eve", "kao", "delta_eve", "delta_nii", "eve_risk_measure",
               "tier1", "reported_amount", "difference", "delta_eve_behavioural", "delta_eve_contractual", "assets_total",
               "liabilities_total", "net_position", "delta_clp", "delta_ur", "with_offset", "without_offset", "used",
               "total_delta_eve", "max_pair", "charge", "pn_ur", "abs_pn_ur", "effect", "delta_with_floor",
               "delta_without_floor", "base_eve_clp", "base_eve_ur", "measure", "net_interest_and_indexation_margin_12m",
               "delta_nii_gap_100bp_up", "total", "delta_vs_base", "base_nii", "nii_quantile", "eve_quantile", "ear", "evar",
               "projected_delta_nii", "realised_delta_nii"}


@pytest.mark.parametrize("key", VARIANT_KEYS)
def test_every_money_field_sits_under_a_block_that_states_its_currency(key: str) -> None:
    doc = load(key)
    found = 0
    for path, obj in closed_objects(key):
        for k, val in obj.items():
            if k in MONEY_NAMES and isinstance(val, (int, float)) and not isinstance(val, bool):
                found += 1
                assert any("currency" in get(doc, path[:n]) or "reporting_currency" in get(doc, path[:n])
                           for n in range(len(path), 0, -1)), f"{key}: money field {'/'.join(map(str, path))}/{k} has no currency"
    assert found > 40, found


@pytest.mark.parametrize("key", ["c14-2022-q4", "c14-models"])
def test_the_c14_currency_is_usd_and_the_c15_reporting_currency_is_clp(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    bad = copy.deepcopy(doc)
    bad[root_of(key)]["currency"] = "CLP"
    assert cs.errors(ref, bad) != []
    for k in C15_OUT + ["c15-models"]:
        ref15, d15 = ref_of(k), load(k)
        d15[root_of(k)]["reporting_currency"] = "USD"
        assert cs.errors(ref15, d15) != []


# --- the 19 buckets -----------------------------------------------------------------------------------------------------


def bucket_sites(key: str) -> list[tuple]:
    return [p for p, o in closed_objects(key) if {"bucket", "midpoint_years"} <= set(o)]


@pytest.mark.parametrize("key", VARIANT_KEYS + ["c14-models", "c15-models"])
def test_a_bucket_outside_the_nineteen_fails(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    sites = bucket_sites(key)
    assert len(sites) >= 10, (key, len(sites))
    for path in sites[:: max(1, len(sites) // 25)]:
        for field, bad_value in (("bucket", 0), ("bucket", 20), ("bucket", 1.5), ("midpoint_years", 3.0), ("midpoint_years", 0.0)):
            bad = copy.deepcopy(doc)
            get(bad, path)[field] = bad_value
            assert cs.errors(ref, bad) != [], f"{key} {path}: {field}={bad_value} still validates"


@pytest.mark.parametrize("key", VARIANT_KEYS + ["c14-models", "c15-models"])
def test_a_bucket_paired_with_another_buckets_midpoint_fails(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    sites = bucket_sites(key)
    for path in sites[:: max(1, len(sites) // 25)]:
        o = get(doc, path)
        other = MIDPOINTS[o["bucket"] % 19]          # the midpoint of the next bucket (a valid midpoint, the wrong pairing)
        bad = copy.deepcopy(doc)
        get(bad, path)["midpoint_years"] = other
        assert cs.errors(ref, bad) != [], f"{key} {path}: bucket {o['bucket']} with midpoint {other} validates"


@pytest.mark.parametrize("key", VARIANT_KEYS)
def test_a_dense_bucket_array_of_the_wrong_length_fails(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    dense_sites = [p for p, o in closed_objects(key) for k, v in o.items()
                   if isinstance(v, list) and len(v) == 19 and all(isinstance(x, (int, float)) for x in v)
                   and k not in ("weights", "floor_bound_buckets")]
    assert dense_sites
    for path in {tuple(p) for p in dense_sites}:
        obj = get(doc, path)
        for k, v in obj.items():
            if isinstance(v, list) and len(v) == 19 and all(isinstance(x, (int, float)) for x in v) and k != "floor_bound_buckets":
                for n in (18, 20):
                    bad = copy.deepcopy(doc)
                    get(bad, path)[k] = (v + [0.0])[:n] if n == 20 else v[:18]
                    assert cs.errors(ref, bad) != [], f"{key}: {k} of length {n} validates"


def test_the_bucket_midpoints_pair_with_their_bucket_in_every_fixture() -> None:
    for key in ALL:
        for path in bucket_sites(key):
            o = get(load(key), path)
            assert o["midpoint_years"] == MIDPOINTS[o["bucket"] - 1], (key, path)
    for key in MODEL_KEYS:
        buckets = fit(key)["buckets"]
        assert [b["bucket"] for b in buckets] == list(range(1, 20))
        assert [b["midpoint_years"] for b in buckets] == MIDPOINTS


# --- NMD caps: requested, cap, used and cap_applied (D2 of the U10 sizing) -----------------------------------------------


def nmd_sites(key: str) -> list[tuple]:
    return [p for p, o in closed_objects(key) if "requested_core_share" in o]


@pytest.mark.parametrize("key", C14_OUT + C15_OUT)
def test_an_nmd_position_above_its_cap_validates_only_with_cap_applied_and_the_used_value_at_the_cap(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    caps = CAPS if key in C14_OUT else CAPS15
    sites = nmd_sites(key)
    assert sites
    for path in sites:
        seg = get(doc, path)
        cap_share, cap_mat = caps[seg["category"]]
        assert seg["core_share_cap"] == cap_share and seg["core_maturity_cap_years"] == cap_mat
        cases = [  # requested share, used share, requested maturity, used maturity, cap_applied, valid
            (cap_share + 0.05, cap_share, 1.0, 1.0, True, True),
            (cap_share + 0.05, cap_share, 1.0, 1.0, False, False),      # above the cap, cap_applied false
            (cap_share + 0.05, cap_share + 0.05, 1.0, 1.0, True, False),  # above the cap, used not at the cap
            (cap_share, cap_share, 1.0, 1.0, False, True),
            (cap_share, cap_share, 1.0, 1.0, True, False),              # at the cap, cap_applied true
            (cap_share - 0.1, cap_share - 0.1, 1.0, 1.0, True, False),  # within the cap, cap_applied true
            (cap_share - 0.1, cap_share - 0.1, cap_mat + 1.0, cap_mat, True, True),
            (cap_share - 0.1, cap_share - 0.1, cap_mat + 1.0, cap_mat, False, False),
            (cap_share - 0.1, cap_share - 0.1, cap_mat + 1.0, cap_mat + 1.0, True, False),
            (cap_share - 0.1, cap_share - 0.1, cap_mat, cap_mat, False, True),
        ]
        for rs, us, rm, um, applied, ok in cases:
            m = copy.deepcopy(doc)
            get(m, path).update({"requested_core_share": rs, "core_share_used": us, "requested_core_maturity_years": rm,
                                 "core_maturity_used_years": um, "cap_applied": applied})
            assert (cs.errors(ref, m) == []) is ok, f"{key} {path}: {(rs, us, rm, um, applied)} expected {'pass' if ok else 'fail'}"
        m = copy.deepcopy(doc)
        get(m, path)["core_share_cap"] = 0.99
        assert cs.errors(ref, m) != [], "a cap other than the SRP31 Table 4 cap validates"


def test_the_used_value_equals_min_of_request_and_cap_in_every_fixture_and_one_fixture_applies_a_cap() -> None:
    applied = 0
    for key in C14_OUT + C15_OUT:
        for path in nmd_sites(key):
            s = get(load(key), path)
            assert s["core_share_used"] == min(s["requested_core_share"], s["core_share_cap"])
            assert s["core_maturity_used_years"] == min(s["requested_core_maturity_years"], s["core_maturity_cap_years"])
            applied += s["cap_applied"]
    assert applied >= 2, "the cap_applied path is not on a fixture for both cases"


@pytest.mark.parametrize("key", C14_OUT + C15_OUT)
def test_the_named_assumptions_carry_a_value_and_a_source(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    names = ["nmd_core_share", "nmd_core_maturity_years", "prepayment_cpr", "term_deposit_redemption_rate", "deposit_beta"]
    a = out(key)["assumptions"]
    assert list(a) == names
    for n in names:
        assert a[n]["source_kind"] in ("regulatory-cap", "fitted", "synthetic-stated")
        assert a[n]["source"]
        for dropped in ("value", "unit", "source_kind", "source"):
            bad = copy.deepcopy(doc)
            del bad["outputs"]["assumptions"][n][dropped]
            assert cs.errors(ref, bad) != []
        bad = copy.deepcopy(doc)
        bad["outputs"]["assumptions"][n]["source_kind"] = "guess"
        assert cs.errors(ref, bad) != []


# --- shock sizes: a currency without a table entry is a labelled Contraste estimate -----------------------------------


def def_errors(schema_ref: str, name: str, obj: Any) -> list[str]:
    sid = f"{cs.BASE}{schema_ref}.schema.json#/$defs/{name}"
    v = Draft202012Validator({"$schema": cs.DIALECT, "$ref": sid}, registry=cs.registry())
    return [e.message for e in v.iter_errors(obj)]


@pytest.mark.parametrize("schema_ref,name", [(C14, "c14ShockSize"), (C14M, "c14ShockSize"), (C15, "c15ShockSize"), (C15M, "c15ShockSize")])
def test_a_shock_size_for_an_untabled_currency_passes_only_labelled_as_a_contraste_estimate(schema_ref: str, name: str) -> None:
    label = {"en": "Contraste estimate, not a regulatory parameter", "es": "Estimacion de Contraste, no es un parametro regulatorio"}
    base = {"currency": "CLP", "parallel_bp": 250.0, "short_bp": 350.0, "long_bp": 150.0, "origin": "contraste-estimate",
            "label": label, "method": "SRP98.56 to SRP98.63 on BCCh yields"}
    assert def_errors(schema_ref, name, base) == []
    for patch, why in (({"label": None}, "an unlabelled estimate"), ({"method": None}, "an estimate without its method"),
                       ({"origin": "srp31-table-2024", "label": None, "method": None}, "CLP under the 2024 table"),
                       ({"origin": "srp31-table-2016", "label": None, "method": None}, "CLP under the 2016 table"),
                       ({"currency": "USD"}, "a tabled currency relabelled as an estimate"),
                       ({"currency": "EUR"}, "a tabled currency relabelled as an estimate")):
        assert def_errors(schema_ref, name, {**base, **patch}) != [], why
    usd = {"currency": "USD", "parallel_bp": 200, "short_bp": 300, "long_bp": 225, "origin": "srp31-table-2024", "label": None, "method": None}
    assert def_errors(schema_ref, name, usd) == []
    for patch, why in (({"parallel_bp": 999}, "a changed table value"), ({"origin": "srp31-table-2016"}, "the 2016 origin on the 2024 values"),
                       ({"label": label}, "a tabled size carrying a label"), ({"currency": "CLP"}, "CLP under a BCBS table")):
        assert def_errors(schema_ref, name, {**usd, **patch}) != [], why
    for i, ccy in enumerate(CCY21):
        for origin, table in (("srp31-table-2024", T2024), ("srp31-table-2016", T2016)):
            ok = {"currency": ccy, "parallel_bp": table["parallel"][i], "short_bp": table["short"][i], "long_bp": table["long"][i],
                  "origin": origin, "label": None, "method": None}
            assert def_errors(schema_ref, name, ok) == [], (ccy, origin)
    for ccy, vals in (("CLP", (300, 400, 200)), ("CLF", (200, 250, 150))):
        ok = {"currency": ccy, "parallel_bp": vals[0], "short_bp": vals[1], "long_bp": vals[2], "origin": "cmf-annex1", "label": None, "method": None}
        assert def_errors(schema_ref, name, ok) == []
        assert def_errors(schema_ref, name, {**ok, "parallel_bp": vals[0] + 50}) != []
    assert def_errors(schema_ref, name, {**usd, "currency": "EUR", "origin": "cmf-annex1"}) != []


# --- the semantic checker: importable, clean on every document, and the planted defects -----------------------------------


@pytest.mark.parametrize("path", all_documents(), ids=lambda p: p.name)
def test_the_semantic_checker_is_clean_on_every_committed_c14_and_c15_document(path) -> None:
    doc = cs.load_json(path)
    ref = cs.schema_for_document(path, doc)
    assert cs.errors(ref, doc) == []
    assert sm.check_document(doc) == []


def test_the_checker_is_an_importable_function_a_bake_calls() -> None:
    assert callable(sm.check_document) and callable(sm.dating_violations)
    assert sm.check_document({"case_id": "C03"}) != []
    late = load("c14-2022-q4")
    late["outputs"]["data"]["call_reports"].append({"report_date": "2023-03-31", "source": "x", "fields": ["ASSET"]})
    assert any("after the valuation date" in m for m in sm.dating_violations(late))
    assert sm.check_document(late) != []


def refused(key: str, doc: dict) -> bool:
    """Refused as a bake would refuse it: the schema first, then the checker (a crash of the checker is a refusal)."""
    if cs.errors(ref_of(key), doc):
        return True
    try:
        return sm.check_document(doc) != []
    except (KeyError, IndexError, TypeError, ZeroDivisionError, StopIteration, ValueError):
        return True


def _swap(doc: dict, path: tuple, i: int, j: int) -> None:
    arr = get(doc, path)
    arr[i], arr[j] = arr[j], arr[i]


def _offset_row(o: dict) -> dict:
    return next(r for r in o["eve"]["rows"] + o["nii"]["rows"] if r["pair"]["opposite_signs"])


def _c14_set(path: tuple, value: Any) -> Callable[[dict], None]:
    def f(d: dict) -> None:
        get(d, path[:-1])[path[-1]] = value
    return f


def _plants() -> list[tuple[str, str, Callable[[dict], None]]]:
    o14 = ("outputs",)
    sc0 = o14 + ("scenarios", 0)
    p: list[tuple[str, str, Callable[[dict], None]]] = []
    A = p.append
    # --- C14 variant
    A(("call report dated after the valuation date", "c14-2022-q4", lambda d: (
        d["outputs"]["data"]["call_reports"].append({"report_date": "2023-03-31", "source": "x", "fields": ["ASSET"]}),
        d["outputs"]["data"].update({"data_cutoff": "2023-03-31"}))))
    A(("curve dated after the valuation date", "c14-2022-q4", _c14_set(o14 + ("curve", "date"), "2023-01-31")))
    A(("balance sheet dated after the valuation date", "c14-2022-q4", _c14_set(o14 + ("balance_sheet", "as_of"), "2023-01-31")))
    A(("read_up_to_valuation_date false", "c14-2022-q4", _c14_set(o14 + ("data", "read_up_to_valuation_date"), False)))
    A(("currency CLP on the USD case", "c14-2022-q4", _c14_set(o14 + ("currency",), "CLP")))
    A(("USD 2024 parallel 999 bp", "c14-2022-q4", _c14_set(sc0 + ("shock_size", "parallel_bp"), 999)))
    A(("calibration 2024 carrying the 2016 size", "c14-2022-q4", lambda d: d["outputs"]["scenarios"][0].update(
        {"shock_size": copy.deepcopy(d["outputs"]["scenarios"][2]["shock_size"])})))
    A(("tabled USD relabelled as a Contraste estimate", "c14-2022-q4", lambda d: d["outputs"]["scenarios"][0]["shock_size"].update(
        {"origin": "contraste-estimate", "label": {"en": "estimate", "es": "estimacion"}, "method": "x"})))
    A(("steepener and flattener rows swapped", "c14-2022-q4", lambda d: _swap(d, sc0 + ("shocks",), 2, 3)))
    A(("flattener replaced by a second steepener", "c14-2022-q4", lambda d: d["outputs"]["scenarios"][0]["shocks"].__setitem__(
        3, copy.deepcopy(d["outputs"]["scenarios"][0]["shocks"][2]))))
    A(("four scenarios all 2024 behavioural", "c14-2022-q4", lambda d: [d["outputs"]["scenarios"].__setitem__(
        i, copy.deepcopy(d["outputs"]["scenarios"][0])) for i in (1, 2, 3)]))
    A(("scenario order changed", "c14-2022-q4", lambda d: _swap(d, o14 + ("scenarios",), 0, 1)))
    A(("behavioural scenario with the contractual treatment", "c14-2022-q4", _c14_set(sc0 + ("nmd_treatment",), "contractual-overnight")))
    A(("a flow's bucket with the wrong midpoint", "c14-2022-q4", _c14_set(
        o14 + ("balance_sheet", "items", 0, "cash_flows", "behavioural", 0, "midpoint_years"), 3.5)))
    A(("19 repricing-gap rows all bucket 1", "c14-2022-q4", lambda d: [r.update({"bucket": 1, "midpoint_years": 0.0028})
                                                                      for r in d["outputs"]["ladder"][0]["repricing_gap"]]))
    A(("a bucket 20 in a repricing-gap row", "c14-2022-q4", _c14_set(o14 + ("ladder", 0, "repricing_gap", 0, "bucket"), 20)))
    A(("outlier breached inverted", "c14-2022-q4", lambda d: d["outputs"]["scenarios"][1]["outlier"].update(
        {"breached": not d["outputs"]["scenarios"][1]["outlier"]["breached"]})))
    A(("negative EVE risk measure", "c14-2022-q4", _c14_set(sc0 + ("eve_risk_measure",), -1.0)))
    A(("EVE risk measure not the maximum", "c14-2022-q4", lambda d: d["outputs"]["scenarios"][0].update(
        {"eve_risk_measure": d["outputs"]["scenarios"][0]["eve_risk_measure"] * 0.5})))
    A(("a delta EVE changed", "c14-2022-q4", lambda d: d["outputs"]["scenarios"][0]["shocks"][0].update(
        {"delta_eve": d["outputs"]["scenarios"][0]["shocks"][0]["delta_eve"] + 1000.0})))
    A(("a delta NII changed", "c14-2022-q4", lambda d: d["outputs"]["scenarios"][0]["shocks"][0].update(
        {"delta_nii": d["outputs"]["scenarios"][0]["shocks"][0]["delta_nii"] + 1000.0})))
    A(("delta NII on the steepener", "c14-2022-q4", _c14_set(sc0 + ("shocks", 2, "delta_nii"), 1.0)))
    A(("post-shock floor +1 percent", "c14-2022-q4", _c14_set(sc0 + ("floor",), 0.01)))
    A(("NMD above its cap with cap_applied false", "c14-2022-q4", _c14_set(o14 + ("nmd_segments", 2, "cap_applied"), False)))
    A(("NMD above its cap with the used value not at the cap", "c14-2022-q4", _c14_set(o14 + ("nmd_segments", 2, "core_share_used"), 0.75)))
    A(("NMD within the cap with cap_applied true", "c14-2021-q4", _c14_set(o14 + ("nmd_segments", 2, "cap_applied"), True)))
    A(("NMD used value not min(request, cap)", "c14-2021-q4", _c14_set(o14 + ("nmd_segments", 0, "core_share_used"), 0.3)))
    A(("NMD cash flows not slotted at the used share", "c14-2022-q4", lambda d: d["outputs"]["balance_sheet"]["items"][7]["cash_flows"][
        "behavioural"].__setitem__(0, {**d["outputs"]["balance_sheet"]["items"][7]["cash_flows"]["behavioural"][0], "amount": -1.0})))
    A(("assumption not the weighted average of the used values", "c14-2022-q4", _c14_set(o14 + ("assumptions", "nmd_core_share", "value"), 0.5)))
    for blk in ("dynamic_nii", "ear_evar", "out_of_sample"):
        A((f"{blk} removed", "c14-2022-q4", lambda d, b=blk: d["outputs"].pop(b)))
    A(("dynamic NII monthly value changed", "c14-2022-q4", lambda d: d["outputs"]["dynamic_nii"]["scenarios"][1]["monthly_nii"].__setitem__(0, 1.0)))
    A(("dynamic NII path shorter than the horizon", "c14-2022-q4", lambda d: d["outputs"]["dynamic_nii"].update({"horizon_months": 24})))
    A(("dynamic NII total changed", "c14-2022-q4", lambda d: d["outputs"]["dynamic_nii"]["scenarios"][2].update({"total": 5.0})))
    A(("EaR not base minus quantile", "c14-2022-q4", lambda d: d["outputs"]["ear_evar"]["levels"][0].update({"ear": 1.0})))
    A(("EaR 99 below 95", "c14-2022-q4", lambda d: d["outputs"]["ear_evar"].update({"levels": [d["outputs"]["ear_evar"]["levels"][1], d["outputs"]["ear_evar"]["levels"][0]]})))
    A(("EaR levels with a third level", "c14-2022-q4", lambda d: d["outputs"]["ear_evar"]["levels"].append(copy.deepcopy(d["outputs"]["ear_evar"]["levels"][0]))))
    A(("out-of-sample period inside the data window", "c14-2021-q4", _c14_set(o14 + ("out_of_sample", "realised_period_start"), "2021-06-01")))
    A(("out-of-sample relative error changed", "c14-2021-q4", _c14_set(o14 + ("out_of_sample", "relative_error"), 0.9)))
    A(("out-of-sample not applicable without a reason", "c14-2022-q4", _c14_set(o14 + ("out_of_sample", "reason"), None)))
    A(("behavioural comparison difference changed", "c14-2022-q4", _c14_set(o14 + ("behavioural_comparison", 0, "difference"), 5.0)))
    A(("behavioural comparison rows reordered", "c14-2022-q4", lambda d: _swap(d, o14 + ("behavioural_comparison",), 0, 1)))
    A(("a missing item with no reason", "c14-2022-q4", _c14_set(o14 + ("balance_sheet", "items", 7, "reason_missing"), None)))
    # --- C14 models
    A(("bucket 1 and 2 midpoints swapped", "c14-models", lambda d: (d["fit"]["buckets"][0].update({"midpoint_years": 0.0417}),
                                                                   d["fit"]["buckets"][1].update({"midpoint_years": 0.0028}))))
    A(("a 2024 shock-table cell changed", "c14-models", _c14_set(("fit", "shock_tables", 0, "rows", 19, "long_bp"), 250)))
    A(("a 2016 shock-table cell changed", "c14-models", _c14_set(("fit", "shock_tables", 1, "rows", 4, "parallel_bp"), 150)))
    A(("wholesale NMD cap 0.6", "c14-models", _c14_set(("fit", "nmd_caps", 2, "core_share_cap"), 0.6)))
    A(("gamma of parallel-up 1.2", "c14-models", _c14_set(("fit", "multipliers", "prepayment_gamma", 0, "gamma"), 1.2)))
    A(("u of parallel-down 1.2", "c14-models", _c14_set(("fit", "multipliers", "term_deposit_u", 1, "u"), 1.2)))
    A(("shock shape x = 5", "c14-models", _c14_set(("fit", "shock_shape", "x"), 5)))
    A(("weighted average maturity not sum w m / 2", "c14-models", _c14_set(("fit", "nmd_models", 0, "weighted_average_maturity_years"), 2.0)))
    A(("a parameter change flagged without a breach", "c14-models", _c14_set(("fit", "nmd_parameter_changes", 2, "flagged"), True)))
    A(("applied size CLP under a BCBS table", "c14-models", lambda d: d["fit"]["applied_sizes"][0].update({"currency": "CLP"})))
    # --- C15 variant
    A(("indexation charge zeroed and left out of delta NII", "c15-long-uf", lambda d: (
        d["outputs"]["indexation_charge"].update({"charge": 0.0}), d["outputs"]["nii"].update(
            {"indexation_charge": 0.0, "delta_nii": d["outputs"]["nii"]["max_pair"]}))))
    A(("delta NII equal to the max pair with the charge block intact", "c15-long-uf", lambda d: d["outputs"]["nii"].update(
        {"delta_nii": d["outputs"]["nii"]["max_pair"]})))
    A(("indexation charge not 2.5 percent of |PN_UR|", "c15-long-uf", lambda d: d["outputs"]["indexation_charge"].update({"charge": 1.0})))
    A(("indexation rate 0.03", "c15-long-uf", _c14_set(o14 + ("indexation_charge", "rate"), 0.03)))
    A(("indexation block removed", "c15-long-uf", lambda d: d["outputs"].pop("indexation_charge")))
    A(("UR leg removed", "c15-long-uf", lambda d: d["outputs"]["legs"].pop(1)))
    A(("UR leg relabelled CLP", "c15-long-uf", _c14_set(o14 + ("legs", 1, "leg"), "CLP")))
    A(("dynamic NII removed", "c15-long-uf", lambda d: d["outputs"].pop("dynamic_nii")))
    A(("C15 dynamic NII legs reordered", "c15-long-uf", lambda d: _swap(d, o14 + ("dynamic_nii", "legs"), 0, 1)))
    A(("C15 dynamic NII monthly value changed", "c15-long-uf", lambda d: d["outputs"]["dynamic_nii"]["legs"][0]["scenarios"][1]["monthly_nii"].__setitem__(0, 1.0)))
    A(("CLP Annex 1 parallel 250", "c15-long-uf", _c14_set(o14 + ("eve_shock_sizes", 0, "parallel_bp"), 250)))
    A(("CLF delta NII size 200", "c15-long-uf", _c14_set(o14 + ("nii_shock_sizes", 1, "parallel_bp"), 200)))
    A(("EUR under cmf-annex1", "c15-long-uf", lambda d: d["outputs"]["eve_shock_sizes"][0].update({"currency": "EUR"})))
    A(("offset state off while used is the offset value", "c15-offset-on-off", _c14_set(o14 + ("offset_rule", "state"), "off")))
    A(("with_offset equal to without_offset on an opposite-sign pair", "c15-offset-on-off", lambda d: _offset_row(d["outputs"])["pair"].update(
        {"with_offset": _offset_row(d["outputs"])["pair"]["without_offset"]})))
    A(("opposite_signs flag wrong", "c15-offset-on-off", lambda d: _offset_row(d["outputs"])["pair"].update({"opposite_signs": False})))
    A(("offset share 0.6", "c15-offset-on-off", _c14_set(o14 + ("offset_rule", "share"), 0.6)))
    A(("eve-tier1 threshold 0.20", "c15-long-uf", _c14_set(o14 + ("thresholds", "tests", 1, "threshold"), 0.20)))
    A(("thresholds reordered", "c15-long-uf", lambda d: _swap(d, o14 + ("thresholds", "tests"), 0, 1)))
    A(("breached flag inverted", "c15-long-uf", lambda d: d["outputs"]["thresholds"]["tests"][0].update(
        {"breached": not d["outputs"]["thresholds"]["tests"][0]["breached"]})))
    A(("prioritised not any breached", "c15-long-uf", lambda d: d["outputs"]["thresholds"].update(
        {"prioritised": not d["outputs"]["thresholds"]["prioritised"]})))
    A(("reporting currency USD", "c15-long-uf", _c14_set(o14 + ("reporting_currency",), "USD")))
    A(("EVE rows parallel-up and parallel-down swapped", "c15-long-uf", lambda d: _swap(d, o14 + ("eve", "rows"), 0, 1)))
    A(("NII rows swapped", "c15-long-uf", lambda d: _swap(d, o14 + ("nii", "rows"), 0, 1)))
    A(("a delta EVE changed", "c15-long-uf", lambda d: d["outputs"]["eve"]["rows"][2]["clp"].update(
        {"delta_eve": d["outputs"]["eve"]["rows"][2]["clp"]["delta_eve"] + 1e6})))
    A(("NMD above its cap with cap_applied false", "c15-cpi-surprise", _c14_set(o14 + ("nmd_segments", 0, "cap_applied"), False)))
    A(("NMD used value above the cap", "c15-cpi-surprise", _c14_set(o14 + ("nmd_segments", 0, "core_share_used"), 0.95)))
    A(("UR floor -3 percent", "c15-long-uf", _c14_set(o14 + ("floors", "ur_floor"), -0.03)))
    A(("curves of another month", "c15-long-uf", _c14_set(o14 + ("curves", "ur", "month"), "2026-05")))
    A(("CPI effect changed", "c15-cpi-surprise", lambda d: d["outputs"]["cpi_scenario"].update({"effect": 1.0})))
    A(("a curve null", "c15-long-uf", _c14_set(o14 + ("curves", "ur"), None)))
    # --- C15 models
    A(("Annex 1 CLP parallel 250", "c15-models", _c14_set(("fit", "annex1_table", 2, "parallel_bp"), 250)))
    A(("Annex 1 table rows reordered", "c15-models", lambda d: _swap(d, ("fit", "annex1_table"), 0, 1)))
    A(("nii-margin threshold 0.25", "c15-models", _c14_set(("fit", "prioritised_thresholds", 2, "threshold"), 0.25)))
    A(("retail-operational maturity cap 7 years", "c15-models", _c14_set(("fit", "nmd_caps", 0, "core_maturity_cap_years"), 7.0)))
    A(("UR floor -1 percent", "c15-models", _c14_set(("fit", "floors", "ur_floor"), -0.01)))
    A(("indexation rate 0.03", "c15-models", _c14_set(("fit", "indexation_rate"), 0.03)))
    A(("offset share 0.6", "c15-models", _c14_set(("fit", "offset_share"), 0.6)))
    A(("weighted average maturity of a window not sum w m / 2", "c15-models", _c14_set(("fit", "nmd_models", 0, "stability", 0, "weighted_average_maturity_years"), 2.5)))
    A(("CLP size under a BCBS table", "c15-models", lambda d: d["fit"]["eve_shock_sizes"][0].update({"origin": "srp31-table-2024"})))
    return p


PLANTS = _plants()


def test_the_plant_table_has_no_duplicate_names_per_document_and_is_large() -> None:
    names = [(k, n) for n, k, _ in PLANTS]
    assert len(names) == len(set(names)) and len(PLANTS) >= 80


@pytest.mark.parametrize("name,key,mutate", PLANTS, ids=[f"{k}:{n}" for n, k, _ in PLANTS])
def test_a_planted_defect_is_refused_by_the_schema_or_the_checker(name: str, key: str, mutate: Callable[[dict], None]) -> None:
    doc = load(key)
    assert not refused(key, doc), f"{key}: the unmodified document is refused"
    mutate(doc)
    assert refused(key, doc), f"{key}: planted defect '{name}' validates and passes the checker"


def test_shocks_out_of_order_and_a_c15_delta_nii_without_the_charge_and_a_c14_without_the_dynamic_blocks_are_refused() -> None:
    names = {n for n, _, _ in PLANTS}
    for n in ("steepener and flattener rows swapped", "EVE rows parallel-up and parallel-down swapped",
              "indexation charge zeroed and left out of delta NII", "delta NII equal to the max pair with the charge block intact",
              "dynamic_nii removed", "ear_evar removed", "out_of_sample removed"):
        assert n in names


@pytest.mark.parametrize("key", C14_OUT)
def test_c14_no_call_report_is_dated_after_the_valuation_date(key: str) -> None:
    doc = load(key)
    assert sm.dating_violations(doc) == []
    assert doc["outputs"]["data"]["read_up_to_valuation_date"] is True
    late = copy.deepcopy(doc)
    late["outputs"]["data"]["call_reports"].append({"report_date": "2099-12-31", "source": "x", "fields": ["ASSET"]})
    late["outputs"]["data"]["data_cutoff"] = "2099-12-31"
    assert any("after the valuation date" in m for m in sm.dating_violations(late))
    flag = copy.deepcopy(doc)
    flag["outputs"]["data"]["read_up_to_valuation_date"] = False
    assert cs.errors(C14, flag) != []


def test_c14_the_two_fixtures_are_two_valuation_dates_and_the_out_of_sample_row_is_on_2021_q4() -> None:
    assert {out(k)["valuation_date"] for k in C14_OUT} == {"2021-12-31", "2022-12-31"}
    assert out("c14-2021-q4")["out_of_sample"]["applicable"] is True
    assert out("c14-2021-q4")["out_of_sample"]["realised_period_start"] > "2021-12-31"
    assert out("c14-2022-q4")["out_of_sample"]["applicable"] is False


def test_c14_the_behavioural_assumptions_pass_the_outlier_test_that_the_contractual_ones_breach() -> None:
    for key in C14_OUT:
        flags = {(s["calibration"], s["nmd_assumption"]): s["outlier"]["breached"] for s in out(key)["scenarios"]}
        assert flags[("2024", "contractual")] is True and flags[("2024", "behavioural")] is False


def test_c14_a_floor_binds_in_at_least_one_fixture_and_the_automatic_option_addon_is_exercised() -> None:
    assert any(s["floor_bound_buckets"] for k in C14_OUT for sc in out(k)["scenarios"] for s in sc["shocks"]), "no floor binds"
    assert any(s["kao"] != 0 for k in C14_OUT for sc in out(k)["scenarios"] for s in sc["shocks"])


def test_c14_models_carry_the_transcribed_shock_tables_the_multipliers_and_the_caps() -> None:
    f = fit("c14-models")
    tables = {t["calibration"]: t for t in f["shock_tables"]}
    assert set(tables) == {"2024", "2016"}
    for cal, want in (("2024", T2024), ("2016", T2016)):
        rows = tables[cal]["rows"]
        assert [r["currency"] for r in rows] == CCY21
        for k in ("parallel", "short", "long"):
            assert [r[f"{k}_bp"] for r in rows] == want[k], (cal, k)
    assert [(g["shock"], g["gamma"]) for g in f["multipliers"]["prepayment_gamma"]] == list(zip(SHOCKS, GAMMA))
    assert [(g["shock"], g["u"]) for g in f["multipliers"]["term_deposit_u"]] == list(zip(SHOCKS, U))
    assert {c["category"]: (c["core_share_cap"], c["core_maturity_cap_years"]) for c in f["nmd_caps"]} == CAPS
    sh = f["shock_shape"]
    assert (sh["x"], sh["steepener_short"], sh["steepener_long"], sh["flattener_short"], sh["flattener_long"]) == (4, -0.65, 0.9, 0.8, -0.6)
    assert f["outlier"]["threshold_share_tier1"] == 0.15


def test_c14_a_behavioural_parameter_change_that_coincides_with_a_limit_breach_is_flagged() -> None:
    changes = fit("c14-models")["nmd_parameter_changes"]
    assert any(c["flagged"] for c in changes) and any(not c["flagged"] for c in changes)


@pytest.mark.parametrize("key", C15_OUT)
def test_c15_the_ur_currency_the_offset_state_and_the_indexation_charge_are_required(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    for field in ("ur_currency", "offset_rule", "indexation_charge", "floors", "thresholds", "curves", "legs", "cpi_scenario", "dynamic_nii"):
        bad = copy.deepcopy(doc)
        del bad["outputs"][field]
        assert cs.errors(ref, bad) != [], f"{key}: a document without {field} validates"
    o = out(key)
    assert o["ur_currency"]["code"] == "CLF" and o["ur_currency"]["label"] == "UR" and o["ur_currency"]["treated_as_one_currency"] is True
    assert o["offset_rule"]["state"] in ("on", "off", "compared") and o["offset_rule"]["share"] == 0.5
    assert o["indexation_charge"]["rate"] == 0.025
    for blk, fields in (("ur_currency", ("code", "label", "treated_as_one_currency", "uf_value", "uf_date")),
                        ("offset_rule", ("state", "share", "rule")), ("indexation_charge", ("rate", "pn_ur", "charge"))):
        for field in fields:
            bad = copy.deepcopy(doc)
            del bad["outputs"][blk][field]
            assert cs.errors(ref, bad) != []
    bad = copy.deepcopy(doc)
    bad["outputs"]["offset_rule"]["state"] = "maybe"
    assert cs.errors(ref, bad) != []
    assert [leg["leg"] for leg in o["legs"]] == ["CLP", "UR"] and [leg["currency"] for leg in o["legs"]] == ["CLP", "CLF"]


def cmf_pair(clp: float, clf: float) -> float:
    return sm.cmf_pair(clp, clf, True)


@pytest.mark.parametrize("clp,clf,want", [(10.0, 20.0, 30.0), (-10.0, -20.0, 0.0), (30.0, -20.0, 20.0), (-20.0, 30.0, 20.0),
                                          (10.0, -40.0, 0.0), (-40.0, 10.0, 0.0), (0.0, 25.0, 25.0), (25.0, 0.0, 25.0)])
def test_the_cmf_offset_rule_golden_values_on_both_signs(clp: float, clf: float, want: float) -> None:
    assert cmf_pair(clp, clf) == want
    assert f"| {clp:g} | {clf:g} | {want:g} |" in API.read_text(encoding="utf-8"), (clp, clf, want)


def test_c15_the_variants_and_months_are_the_sdd_ones_and_one_fixture_is_compared_with_opposite_signs() -> None:
    schema = cs.load_json(SCHEMAS / "c15" / "variant-annex1-variant.schema.json")
    assert schema["$defs"]["c15Variant"]["properties"]["id"]["enum"] == ["long-uf", "short-uf", "cpi-surprise", "clp-steepener", "offset-on-off", "floors-active"]
    assert {out(k)["variant"]["id"] for k in C15_OUT} == {"long-uf", "offset-on-off", "cpi-surprise"}
    o = out("c15-offset-on-off")
    assert o["offset_rule"]["state"] == "compared"
    assert any(r["pair"]["opposite_signs"] and r["pair"]["with_offset"] != r["pair"]["without_offset"] for r in o["eve"]["rows"] + o["nii"]["rows"])
    assert [out(k)["cpi_scenario"] is not None for k in C15_OUT] == [False, False, True]


def test_c15_floors_bind_and_the_dynamic_nii_has_both_legs() -> None:
    assert any(out(k)["floors"]["effects"] for k in C15_OUT)
    for k in C15_OUT:
        assert [lg["leg"] for lg in out(k)["dynamic_nii"]["legs"]] == ["CLP", "UR"]


def test_c15_the_models_carry_the_annex1_table_the_floors_and_the_thresholds_as_transcribed() -> None:
    f = fit("c15-models")
    rows = {r["basket"]: (r["parallel_bp"], r["short_bp"], r["long_bp"]) for r in f["annex1_table"]}
    assert rows == CMF_ROWS
    assert (f["floors"]["ur_floor"], f["floors"]["other_floor"]) == (-0.02, 0.0)
    assert {t["id"]: t["threshold"] for t in f["prioritised_thresholds"]} == {"nii-tier1": 0.05, "eve-tier1": 0.15, "nii-margin": 0.18}
    assert f["offset_share"] == 0.5 and f["indexation_rate"] == 0.025
    assert [(g["shock"], g["gamma"]) for g in f["multipliers"]["prepayment_gamma"]] == list(zip(SHOCKS, GAMMA))
    assert [(g["shock"], g["u"]) for g in f["multipliers"]["term_deposit_u"]] == list(zip(SHOCKS, U))
    assert {c["category"]: (c["core_share_cap"], c["core_maturity_cap_years"]) for c in f["nmd_caps"]} == CAPS15
    assert {c["curve"] for c in f["curve_models"]} == {"CLP", "UR"}


# --- the catalog rows ---------------------------------------------------------------------------------------------------


def row_cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def test_the_rows_fragment_has_the_five_rows_in_the_catalog_columns() -> None:
    catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
    header = next(row_cells(ln) for ln in catalog.splitlines() if ln.startswith("| id | version"))
    lines = [ln for ln in ROWS.read_text(encoding="utf-8").splitlines() if ln.startswith("|")]
    rows = [row_cells(ln) for ln in lines]
    assert rows[0] == header
    data = [r for r in rows[1:] if not all(set(c) <= set(":- ") for c in r)]
    assert [r[0] for r in data] == ROW_IDS
    for r in data:
        assert len(r) == len(header), r[0]
        d = dict(zip(header, r))
        assert d["version"] == ("1.1.0" if d["id"] == "engine-irrbb-api" else "1.0.0")
        assert d["status"] == "active"
        assert d["provider"].startswith("fixture:")
        assert (ROOT / d["schema file"]).is_file(), d["schema file"]
        assert (ROOT / d["provider"].removeprefix("fixture:")).is_file(), d["provider"]
        assert (ROOT / d["example"]).is_file(), d["example"]
        assert "U10-S" in d["owner"]
        for cell in (d["producer test"], d["consumer test"]):
            for t in cell.split(","):
                path, _, name = t.strip().partition("::")
                assert (ROOT / path).is_file(), path
                if name:
                    assert f"def {name}(" in (ROOT / path).read_text(encoding="utf-8"), t


def test_the_rows_fragment_carries_no_row_already_in_the_catalog() -> None:
    catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
    ids = {ln.split("|")[1].strip() for ln in catalog.splitlines() if ln.startswith("| ")}
    assert not (ids & set(ROW_IDS))


# --- the engine IRRBB API contract --------------------------------------------------------------------------------------

MODULES = {
    "curves": ["bootstrap_zero_curve", "zero_rates_at", "discount_factors", "nelson_siegel_yield", "svensson_yield",
               "fit_nelson_siegel", "fit_svensson", "dns_loadings", "dns_yield", "fit_dns_factors", "forecast_dns_factors"],
    "shocks": ["shock_scalars", "shock_curve", "shock_table", "shock_size", "apply_floor", "eu_floor"],
    "slotting": ["bucket_grid", "bucket_of", "slot_cash_flows", "nmd_split", "prepayment_cpr", "smm_from_cpr", "cpr_from_smm",
                 "psa_cpr", "term_deposit_redemption_rate"],
    "eve_nii": ["repricing_gap", "delta_nii_gap", "duration_gap", "eve", "delta_eve", "eve_risk_measure", "delta_nii",
                "automatic_option_addon", "cmf_pair", "annex1_delta_nii", "annex1_delta_eve", "indexation_charge", "outlier_test",
                "prioritised_bank"],
    "behavioural": ["replicating_portfolio", "weighted_average_maturity", "deposit_beta_passthrough", "prepayment_logit",
                    "fit_prepayment_logit"],
    "simulation": ["simulate_nii", "hw1f_scenarios", "dns_scenarios", "ear_evar", "ear_evar_mc_error"],
    "validation.irrbb": ["srp31_92_goldens", "cmf_annex1_goldens", "eve_sum_of_parts", "nmd_parameter_stability",
                         "eve_with_without_behavioural", "behavioural_change_at_breach", "nii_out_of_sample"],
}
TEST_FUNCTIONS = MODULES["validation.irrbb"]


def prefix_of(module: str) -> str:
    return "riskvalidation.validation.irrbb" if module == "validation.irrbb" else f"riskvalidation.irrbb.{module}"


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
    assert "engine-irrbb-api" in text and "1.0.0" in text
    assert "common/test-result" in text


def test_the_engine_contract_covers_every_module_of_the_sizing_table() -> None:
    text = API.read_text(encoding="utf-8")
    for module in ("irrbb/curves.py", "irrbb/shocks.py", "irrbb/slotting.py", "irrbb/eve_nii.py", "irrbb/behavioural.py",
                   "irrbb/simulation.py", "validation/irrbb.py"):
        assert f"`riskvalidation/{module}`" in text, module


@pytest.mark.parametrize("module", MODULES)
def test_every_function_has_a_signature_and_a_golden_value_or_an_invariant(module: str) -> None:
    for name in MODULES[module]:
        body = section(module, name)
        assert "```python" in body, name
        assert re.search(r"^- (Golden|Invariants):", body, flags=re.M), f"{name}: no golden value or invariant"
        assert re.search(r"^- Units:", body, flags=re.M), f"{name}: no units line"


def test_every_validation_function_has_a_light_rule_a_test_id_and_a_golden() -> None:
    for name in TEST_FUNCTIONS:
        body = section("validation.irrbb", name)
        assert "-> TestResult" in body, name
        assert re.search(r"^- Light:", body, flags=re.M), name
        assert re.search(r"^- Golden:", body, flags=re.M), name
        assert re.search(r'test_id = "irrbb\.[a-z0-9_]+"', body), name


def test_the_engine_contract_has_no_function_outside_the_table() -> None:
    declared = {key_of(m, n) for m, names in MODULES.items() for n in names}
    assert set(api_sections()) == declared


def test_the_engine_contract_carries_the_dossier_goldens() -> None:
    text = API.read_text(encoding="utf-8")
    for golden in ("0.417", "+41.7", "+25.4", "-1.6", "0.0028", "0.0417", "0.1667", "25.0", "0.0609", "0.298384", "29.446",
                   "0.2", "6.0", "0.005143", "2.5"):
        assert golden in text, golden
    for cell in ("SRP31.92", "SRP31.96", "SRP31.90", "SRP31.119", "SRP31.125", "SRP31.129", "SRP31.93", "SRP31.121", "SRP31.126",
                 "SRP31.127", "SRP98.56"):
        assert cell in text, cell
    for test_id in ("irrbb.srp31_92_goldens", "irrbb.cmf_annex1_goldens", "irrbb.eve_sum_of_parts", "irrbb.nmd_parameter_stability",
                    "irrbb.eve_with_without_behavioural", "irrbb.behavioural_change_at_breach", "irrbb.nii_out_of_sample"):
        assert test_id in text, test_id
    assert "UNVERIFIED" in text
    # the 2024 and 2016 tables and the CMF table, as data, in the contract
    for row in (T2024["parallel"], T2024["short"], T2024["long"], T2016["parallel"], T2016["short"], T2016["long"]):
        assert " | ".join(str(x) for x in row) in text, row
    for basket, (p, s, lg) in CMF_ROWS.items():
        assert f"| {basket} | {p} | {s if s is not None else '-'} | {lg if lg is not None else '-'} |" in text, basket
    assert "| 0.8 | 1.2 | 0.8 | 1.2 | 0.8 | 1.2 |" in text and "| 1.2 | 0.8 | 0.8 | 1.2 | 1.2 | 0.8 |" in text


def test_golden_srp31_92_values_recompute() -> None:
    a = math.exp(-3.5 / 4)
    assert math.isclose(a, 0.417, abs_tol=5e-4)
    assert math.isclose(100 * a, 41.7, abs_tol=5e-2)
    assert math.isclose(-0.65 * 100 * a + 0.9 * 100 * (1 - a), 25.4, abs_tol=5e-2)
    assert math.isclose(0.8 * 100 * a - 0.6 * 100 * (1 - a), -1.6, abs_tol=5e-2)
    assert len(MIDPOINTS) == 19 and MIDPOINTS[-1] == 25.0


def test_golden_psa_curve_and_smm_recompute() -> None:
    def psa(m: int, pct: float = 100.0) -> float:
        return pct / 100 * min(0.002 * m, 0.06)
    assert psa(1) == 0.002 and math.isclose(psa(30), 0.06, abs_tol=1e-12) and math.isclose(psa(60), 0.06, abs_tol=1e-12)
    assert math.isclose(psa(20, 150.0), 0.06, abs_tol=1e-12)
    smm = 1 - (1 - 0.06) ** (1 / 12)
    assert math.isclose(smm, 0.005143, abs_tol=5e-7)
    assert math.isclose(1 - (1 - smm) ** 12, 0.06, abs_tol=1e-12)


def test_golden_diebold_li_decay_and_curvature_loading_recompute() -> None:
    lam = 0.0609

    def curvature(m: float) -> float:
        x = lam * m
        return (1 - math.exp(-x)) / x - math.exp(-x)
    assert math.isclose(curvature(30), 0.298384, abs_tol=5e-7)
    best = max(range(1, 100000), key=lambda i: curvature(i / 1000))
    assert math.isclose(best / 1000, 29.446, abs_tol=2e-3)     # the maximiser is 29.446 months, the 30 of the paper is rounded
    assert curvature(30) > curvature(25) and curvature(30) > curvature(40)
    assert math.isclose(curvature(best / 1000), 0.298426, abs_tol=5e-7)


def test_golden_three_bucket_eve_recomputes_for_every_shock() -> None:
    """The contract's hand-computed balance sheet: net flows +100 at 0.375 y, -30 at 2.5 y, -70 at 9.5 y on a flat 2 percent
    continuously compounded curve, USD 2024 sizes, no floor."""
    text = API.read_text(encoding="utf-8")
    cf = {3: 100.0, 8: -30.0, 15: -70.0}
    flows = [cf.get(k, 0.0) for k in range(19)]
    r0 = [0.02] * 19
    base = eve_of(flows, r0)
    assert f"{base:.6f}" in text
    for shock in SHOCKS:
        sh = shape(shock, 200, 300, 225)
        delta = base - eve_of(flows, [post_rate(a, d, None) for a, d in zip(r0, sh)])
        assert f"| {shock} | {delta:.6f} |" in text, (shock, f"{delta:.6f}")


def test_golden_curve_floor_and_gap_values_recompute() -> None:
    def ns(m: float, b0: float, b1: float, b2: float, tau: float) -> float:
        x = m / tau
        f = (1 - math.exp(-x)) / x
        return b0 + b1 * f + b2 * (f - math.exp(-x))
    assert math.isclose(ns(1, 0.05, -0.02, 0.01, 2.0), 0.036065, abs_tol=5e-7)
    assert math.isclose(ns(1e-9, 0.05, -0.02, 0.01, 2.0), 0.03, abs_tol=1e-7)
    assert math.isclose(ns(1e9, 0.05, -0.02, 0.01, 2.0), 0.05, abs_tol=1e-7)
    assert math.isclose(2 * math.log(1.02), 0.039605, abs_tol=5e-7)
    assert math.isclose(math.exp(-0.02 * 2.5), 0.951229, abs_tol=5e-7)
    lam = 0.0609
    for m, slope, curv in ((30, 0.459280, 0.298384), (12, 0.709464, 0.227941), (60, 0.266588, 0.240701)):
        x = lam * m
        assert math.isclose((1 - math.exp(-x)) / x, slope, abs_tol=5e-7)
        assert math.isclose((1 - math.exp(-x)) / x - math.exp(-x), curv, abs_tol=5e-7)
    x = lam * 30
    assert math.isclose(0.05 - 0.02 * (1 - math.exp(-x)) / x + 0.01 * ((1 - math.exp(-x)) / x - math.exp(-x)), 0.043798, abs_tol=5e-7)
    assert post_rate(0.004, -300, 0.0) == 0.0 and post_rate(-0.001, -300, 0.0) == -0.001 and post_rate(0.004, -300, -0.02) == -0.02
    assert [round(-0.015 + 0.0003 * t, 12) for t in (0, 10)] == [-0.015, -0.012] and -0.015 + 0.0003 * 50 == 0.0
    # duration gap golden: asset 100 at 2 y, liability 80 at 1 y, zero rates
    assert math.isclose(2 - 80 / 100 * 1, 1.2, abs_tol=1e-12) and math.isclose(-1.2 * 100 * 0.01, -1.2, abs_tol=1e-12)
    assert math.isclose(-(100 * 0.01 * (1 - 0.1667)), -0.8333, abs_tol=5e-5)
    assert math.isclose(100 * (0.03 - 0.06) * (1 - 0.625), -1.125, abs_tol=1e-12)
    assert 100 * 0.05 - 100 * 0.015 == 3.5 and math.isclose(100 * 0.06 - 100 * 0.02, 4.0, abs_tol=1e-12)
    assert abs(sorted(range(1, 101))[0] + 0.99 * (2 - 1) - 1.99) < 1e-12


def test_golden_annex1_totals_recompute() -> None:
    eve_clp, eve_ur = [10, -20, 0, 5, -30, 40], [20, 30, -10, -2, 50, -15]
    pairs = [cmf_pair(a, b) for a, b in zip(eve_clp, eve_ur)]
    assert pairs == [30, 20, 0, 4, 35, 32.5] and max(pairs) == 35 and SHOCKS[pairs.index(35)] == "short-up"
    assert [cmf_pair(30, -20), cmf_pair(-10, 5)] == [20, 0] and 20 + 0.025 * 200 == 25
    # eve_risk_measure golden and the outlier and prioritised goldens
    rows = [[3, -1], [2, 4], [-5, -2]]
    assert max(max(0, sum(x for x in row if x > 0)) for row in rows) == 6
    assert 16 / 100 > 0.15 and not (15 / 100 > 0.15)
    ratios = (6 / 100, 10 / 100, 6 / 40)
    assert (ratios[0] > 0.05, ratios[1] > 0.15, ratios[2] > 0.18) == (True, False, False)


# --- the Opus review of U10-S (review-u10-s-2026-10-13.md): one test per finding and per decision --------------------------


def _solve(a: list, b: list) -> list:
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[piv] = m[piv], m[c]
        for r in range(n):
            if r != c:
                f = m[r][c] / m[c][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    return [m[i][n] / m[i][i] for i in range(n)]


def _logit_fit(xs: list, ys: list) -> tuple[list, list]:
    b = [0.0, 0.0, 0.0]
    for _ in range(30):
        g, h = [0.0] * 3, [[0.0] * 3 for _ in range(3)]
        for x, y in zip(xs, ys):
            p = 1 / (1 + math.exp(-sum(bi * xi for bi, xi in zip(b, x))))
            w = p * (1 - p)
            for i in range(3):
                g[i] += (y - p) * x[i]
                for j in range(3):
                    h[i][j] += w * x[i] * x[j]
        step = _solve(h, g)
        b = [bi + si for bi, si in zip(b, step)]
        if max(abs(si) for si in step) < 1e-10:
            break
    se = []
    for i in range(3):
        e = [1.0 if j == i else 0.0 for j in range(3)]
        se.append(math.sqrt(_solve(h, e)[i]))
    return b, se


def test_b1_weighted_average_maturity_golden_is_2_3_and_one_tranche_of_five_years_is_2_5() -> None:
    assert math.isclose(sum(w * m / 2 for w, m in zip([0.2, 0.3, 0.3, 0.2], [1, 3, 5, 10])), 2.3, abs_tol=1e-12)
    assert 1.0 * 5 / 2 == 2.5
    body = api_sections()["riskvalidation.irrbb.behavioural.weighted_average_maturity"]
    assert "(0.2 + 0.9 + 1.5 + 2.0) / 2 = 2.3" in body and "weights `[0.2, 0.3, 0.3, 0.2]` on `[1, 3, 5, 10]` give `2.5`" not in body
    for key in ("c14-models", "c15-models"):
        assert sm.check_document(load(key)) == []


def test_b2_eve_sum_of_parts_golden_is_green_under_the_default_tolerance_with_the_exact_whole() -> None:
    cf = {3: 100.0, 8: -30.0, 15: -70.0}
    rates = [0.02] * 19
    whole = eve_of([cf.get(k, 0.0) for k in range(19)], rates)
    parts = sum(eve_of([v if k == b else 0.0 for k in range(19)], rates) for b, v in cf.items())
    assert abs(parts - whole) / abs(whole) < 1e-12
    rounded = 12.828783
    assert abs(parts - rounded) / abs(rounded) > 1e-9, "the rounded value would be red under the default tolerance"
    assert abs(parts - rounded) / abs(rounded) < 1e-6
    text = API.read_text(encoding="utf-8")
    assert "12.8287834" in text and "`rel_tol = 1e-9`" in text and "2.9e-8" in text and "only with `rel_tol = 1e-6`" in text


def test_m1_bootstrap_golden_is_pinned_to_multiples_of_the_coupon_period() -> None:
    assert math.isclose(2 * math.log(1.02), 0.039605, abs_tol=5e-7)
    assert math.isclose(12 * math.log(1 + 0.04 / 12), 0.039933, abs_tol=5e-7)
    assert math.isclose(math.log(1 + 0.04 * 0.25) / 0.25, 0.039801, abs_tol=5e-7)
    body = api_sections()["riskvalidation.irrbb.curves.bootstrap_zero_curve"]
    assert "multiple of `1 / frequency`" in body and "tenors `0.5, 1, 2, 5, 10`" in body and "0.039933" in body
    assert "at every tenor." not in body


def test_m2_fit_prepayment_logit_states_its_design_and_recovers_within_three_standard_errors() -> None:
    rng = random.Random(0)
    n, truth = 20000, [-2.0, 20.0, 0.01]
    xs, ys = [], []
    for _ in range(n):
        x = [1.0, rng.uniform(-0.10, 0.10), rng.uniform(0, 360)]
        p = 1 / (1 + math.exp(-sum(t * v for t, v in zip(truth, x))))
        xs.append(x)
        ys.append(1.0 if rng.random() < p else 0.0)
    b, se = _logit_fit(xs, ys)
    assert 0.2 < se[1] < 0.6, se
    assert all(abs(bi - t) <= 3 * s for bi, t, s in zip(b, truth, se)), (b, se)
    body = api_sections()["riskvalidation.irrbb.behavioural.fit_prepayment_logit"]
    for needle in ("Uniform(-0.10, 0.10)", "Uniform(0, 360)", "N = 20000", "3 of its own standard errors", "std_err"):
        assert needle in body, needle


def test_the_diebold_li_maximum_is_29_446_not_29_447() -> None:
    def f(x: float) -> float:
        return (1 - math.exp(-x)) / x - math.exp(-x)
    lo, hi = 1.0, 3.0
    for _ in range(200):          # golden-section search for the maximiser of the curvature loading
        a, b = lo + (hi - lo) * 0.382, lo + (hi - lo) * 0.618
        lo, hi = (lo, b) if f(a) > f(b) else (a, hi)
    assert math.isclose(lo, 1.7932821, abs_tol=1e-6) and math.isclose(lo / 0.0609, 29.446, abs_tol=5e-4)
    text = API.read_text(encoding="utf-8")
    assert "29.447" not in text and "29.446" in text


def test_the_minor_findings_are_in_the_contract_text() -> None:
    text = API.read_text(encoding="utf-8")
    assert "`0.25, 0.5, ..., 10.0` in steps of `0.25`, which contains `2.0`" in text          # the default tau grid
    assert "the midpoint of `(0, 1/360]` is 0.0014" in text                                   # the overnight edge
    assert "a tabled currency relabelled as an estimate" in text                              # shock_size
    assert "with `m = 0` for the first month" in text and "at `0.04` in every month" in text   # simulate_nii
    assert "worked example of RAN 21-13 Annex 1 Hoja 10" in text                              # cmf_annex1_goldens
    assert "UNVERIFIED" in api_sections()["riskvalidation.irrbb.shocks.apply_floor"]
    for key in C15_OUT:
        rule = out(key)["floors"]["rule"]["en"]
        assert "UNVERIFIED" in rule, "the floors.rule text must not state the UR pre-shock reading as fact"


def test_d2_the_nmd_slotting_of_the_engine_contract_returns_the_document_fields() -> None:
    body = api_sections()["riskvalidation.irrbb.slotting.nmd_split"]
    for field in ("requested_core_share", "core_share_cap", "core_share_used", "requested_core_maturity_years",
                  "core_maturity_cap_years", "core_maturity_used_years", "cap_applied"):
        assert field in body, field
    assert "share_flag" not in body and "capped: bool" not in body
    assert (1 - min(0.6, 0.5)) * 100 == 50 and (1 - 0.6) * 100 == 40     # the contract's wholesale golden


def test_d1_every_c14_document_carries_the_dynamic_nii_the_ear_evar_and_the_out_of_sample_blocks_and_c15_the_dynamic_nii() -> None:
    for key in C14_OUT:
        o = out(key)
        assert [s["scenario"] for s in o["dynamic_nii"]["scenarios"]] == ["base", "parallel-up", "parallel-down"]
        assert 12 <= o["dynamic_nii"]["horizon_months"] <= 36
        assert [lv["level"] for lv in o["ear_evar"]["levels"]] == [0.95, 0.99]
        assert o["ear_evar"]["n_paths"] > 1 and "seed" in o["ear_evar"] and o["ear_evar"]["levels"][0]["ear_se"] >= 0
        assert o["dynamic_nii"]["balance_sheet_assumption"]["kind"] in ("constant", "growth")
    for key in C15_OUT:
        assert "ear_evar" not in out(key) and len(out(key)["dynamic_nii"]["legs"]) == 2


def test_the_simulate_nii_and_ear_evar_goldens_of_the_contract_recompute() -> None:
    asset = {"item_id": "a", "side": "asset", "balance": 100.0, "rate0": 0.05, "spread": 0.02, "beta": 1.0, "reprice_months": 0}
    liab = {"item_id": "l", "side": "liability", "balance": 100.0, "rate0": 0.015, "spread": 0.0, "beta": 0.5, "reprice_months": 0}
    assert math.isclose(sum(sm.simulate_nii([asset, liab], [0.03] * 12)), 3.5, abs_tol=1e-12)
    assert math.isclose(sum(sm.simulate_nii([asset, liab], [0.04] * 12)), 4.0, abs_tol=1e-12)
    fixed = {**asset, "reprice_months": 60, "rate0": 0.05}
    assert math.isclose(sum(sm.simulate_nii([fixed], [0.03] * 12)), sum(sm.simulate_nii([fixed], [0.09] * 12)), abs_tol=1e-12)
    q = 1 + 0.01 * 99                  # linear-interpolated quantile of 1..100 at 0.01
    assert math.isclose(q, 1.99, abs_tol=1e-12) and math.isclose(60 - q, 58.01, abs_tol=1e-12)


def test_f8_the_rows_fragment_says_the_api_version_bump_is_the_integrators() -> None:
    assert "integrator" in ROWS.read_text(encoding="utf-8").split("-->")[0]
    assert "check_contract_versions" in ROWS.read_text(encoding="utf-8").split("-->")[0]


# --- follow-up after the engine review (review-u10-engine-2026-10-13.md): one test per amendment ---------------------------


def _quantile(xs: list, p: float) -> float:
    s = sorted(xs)
    pos = p * (len(s) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (pos - lo) * (s[hi] - s[lo])


def _batch_means_se(paths: list, level: float, n_batches: int) -> float:
    size = len(paths) // n_batches
    qs = [_quantile(paths[i * size:(i + 1) * size], 1 - level) for i in range(n_batches)]
    mean = sum(qs) / n_batches
    sd = math.sqrt(sum((q - mean) ** 2 for q in qs) / (n_batches - 1))
    return sd / math.sqrt(n_batches)


def test_amend1_the_contract_has_the_monte_carlo_error_function_with_exact_and_closed_form_goldens() -> None:
    key = "riskvalidation.irrbb.simulation.ear_evar_mc_error"
    assert key in api_sections()
    body = api_sections()[key]
    for needle in ("batch means", "n_batches", "-> EarEvarMcError", "nii_quantile_se", "eve_quantile_se", "ear_se", "evar_se",
                   "0.037332", "0.021132", "50.0"):
        assert needle in body, needle
    assert "ear_evar_mc_error" in API.read_text(encoding="utf-8").split("## How the documents use the engine")[1].split("## Tables")[0]
    # the exact golden: 2 batches of 20, medians 10.5 and 110.5, SE = sd / sqrt(2) = (100 / sqrt(2)) / sqrt(2) = 50
    paths = [float(i) for i in range(1, 21)] + [float(i) for i in range(101, 121)]
    assert math.isclose(_batch_means_se(paths, 0.5, 2), 50.0, abs_tol=1e-12)
    # the closed form for i.i.d. N(0, 1) paths: sqrt(p (1 - p) / P) / phi(z_p), P = 10000
    from statistics import NormalDist
    for level, want in ((0.99, 0.037332), (0.95, 0.021132)):
        p = 1 - level
        z = NormalDist().inv_cdf(p)
        phi = math.exp(-z * z / 2) / math.sqrt(2 * math.pi)
        assert math.isclose(math.sqrt(p * (1 - p) / 10000) / phi, want, abs_tol=5e-7)
    # the batch estimator agrees with the closed form on a seeded normal sample (loose: 20 batches carry about 16 percent noise)
    rng = random.Random(0)
    sample = [rng.gauss(0, 1) for _ in range(100000)]
    est = _batch_means_se(sample, 0.99, 20)
    closed = math.sqrt(0.01 * 0.99 / 100000) / (math.exp(-(2.3263478740408408 ** 2) / 2) / math.sqrt(2 * math.pi))
    assert 0.5 * closed < est < 1.5 * closed, (est, closed)


@pytest.mark.parametrize("key", C14_OUT)
def test_amend1_each_ear_evar_level_carries_its_monte_carlo_standard_errors(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    ee = out(key)["ear_evar"]
    assert "monte_carlo_error" not in ee and ee["mc_error_method"] == "batch-means" and ee["n_batches"] >= 2
    for i, lv in enumerate(ee["levels"]):
        assert lv["ear_se"] >= 0 and lv["evar_se"] >= 0
        for f in ("ear_se", "evar_se"):
            bad = copy.deepcopy(doc)
            del bad["outputs"]["ear_evar"]["levels"][i][f]
            assert cs.errors(ref, bad) != [], f"a level without {f} validates"
            bad = copy.deepcopy(doc)
            bad["outputs"]["ear_evar"]["levels"][i][f] = -1.0
            assert cs.errors(ref, bad) != [], f"a negative {f} validates"
    bad = copy.deepcopy(doc)
    bad["outputs"]["ear_evar"]["n_batches"] = 1
    assert cs.errors(ref, bad) != []
    assert sm.check_document(doc) == []
    zero = copy.deepcopy(doc)
    zero["outputs"]["ear_evar"]["levels"][0]["ear_se"] = 1e12
    assert sm.check_document(zero) != [], "a standard error larger than the quantile spread is refused"


def test_amend2_eve_risk_measure_takes_exactly_the_six_shock_rows_and_refuses_a_transposed_matrix() -> None:
    body = api_sections()["riskvalidation.irrbb.eve_nii.eve_risk_measure"]
    assert "(6, C)" in body and "refuses" in body and "transposed" in body and "ValueError" in body
    rows = [[3, -1], [2, 4], [-5, -2], [0, 0], [0, 0], [0, 0]]
    assert max(max(0, sum(x for x in row if x > 0)) for row in rows) == 6
    assert "[[3, -1], [2, 4], [-5, -2], [0, 0], [0, 0], [0, 0]]" in body and "[[3, -1], [2, 4], [-5, -2]]`" not in body
    transposed = list(zip(*rows))
    assert len(transposed) == 2 and len(transposed) != 6          # (C, S) = (2, 6): the first axis is not the six shocks
    assert max(max(0, sum(x for x in row if x > 0)) for row in transposed) == 5   # the silent wrong number the refusal prevents


def test_amend3_the_annex1_goldens_are_checked_at_the_printed_precision_of_hoja_10() -> None:
    body = api_sections()["riskvalidation.validation.irrbb.cmf_annex1_goldens"]
    assert "exact to `1e-12`, except the two Hoja 10 values" in body and "tolerance_printed" in body and "5e-4" in body and "5e-2" in body
    assert "equality to `1e-12`, red otherwise" not in body
    a = math.exp(-3.5 / 4)
    assert abs(a - 0.417) > 1e-12 and abs(a - 0.417) <= 5e-4                    # 1.4e-4: exact to 1e-12 can never be met
    assert abs(100 * a - 41.7) > 1e-12 and abs(100 * a - 41.7) <= 5e-2


def test_amend_the_engine_contract_is_version_1_1_0_and_its_row_says_so() -> None:
    assert "1.1.0" in API.read_text(encoding="utf-8").split("\n", 1)[0]
    rows = [ln for ln in ROWS.read_text(encoding="utf-8").splitlines() if ln.startswith("| engine-irrbb-api")]
    assert rows and rows[0].split(" | ")[1] == "1.1.0"
