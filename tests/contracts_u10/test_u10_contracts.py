"""U10-S: the C14 and C15 case contracts, their fixtures, the catalog rows and the engine IRRBB API contract.

The fixtures validate by discovery (tests/contracts/contract_schemas.py) against exactly one schema; the schemas are strict
both ways (a removed or an added key fails); a bucket outside the 19 of SRP31.96 Table 3 fails; an NMD core share or
maturity above its SRP31 Table 4 cap passes only with its flag; a shock size for a currency without a table entry passes
only labelled as a Contraste estimate; a money block without its currency fails; the standardised EVE risk measure is the
maximum over the six shocks of the aggregated positive losses and every number of a fixture recomputes here from the
formulas of dossier 01 H and dossier 03 F.2, written independently of the fixture builder; a C14 document never reads a
call report dated after its valuation date; a C15 document carries the UR currency, the offset rule state and the
indexation charge; the engine contract names every function of the modules table of plans/contraste/units/U10-sizing.md
with a signature, units and a golden value or an invariant, and its golden values recompute here. The fixtures are labelled
as fixtures and never published as results.
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


@pytest.mark.parametrize("key", ALL)
def test_a_key_removed_from_any_object_fails(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    checked, seen = 0, set()
    for path, obj in closed_objects(key):
        shape = (tuple(p for p in path if not isinstance(p, int)), tuple(sorted(obj)))
        if shape in seen:  # one probe per object shape keeps the run short; every shape of the document is probed
            continue
        seen.add(shape)
        for k in list(obj):
            bad = copy.deepcopy(doc)
            del get(bad, path)[k]
            assert cs.errors(ref, bad) != [], f"{key}: removing {'/'.join(map(str, path))}/{k} still validates"
            checked += 1
    assert checked > 60


@pytest.mark.parametrize("key", ALL)
def test_a_key_added_to_any_object_fails(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    seen = set()
    for path, obj in closed_objects(key):
        shape = (tuple(p for p in path if not isinstance(p, int)), tuple(sorted(obj)))
        if shape in seen:
            continue
        seen.add(shape)
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
    sites = [(p, o) for p, o in closed_objects(key) if "currency" in o and "tenor_years" not in o]
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
               "delta_nii_gap_100bp_up"}


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


@pytest.mark.parametrize("key", VARIANT_KEYS)
def test_a_dense_bucket_array_of_the_wrong_length_fails(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    dense = [p for p, o in closed_objects(key) for k, v in o.items()
             if isinstance(v, list) and len(v) == 19 and all(isinstance(x, (int, float)) for x in v) and k not in ("weights", "floor_bound_buckets")]
    assert dense
    for path in {tuple(p) for p in dense}:
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


# --- NMD caps, with their flags -----------------------------------------------------------------------------------------


def nmd_sites(key: str) -> list[tuple]:
    return [p for p, o in closed_objects(key) if "core_share" in o and "core_share_cap" in o]


@pytest.mark.parametrize("key", C14_OUT + C15_OUT)
def test_an_nmd_core_share_or_maturity_above_its_cap_passes_only_with_its_flag(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    caps = CAPS if key in C14_OUT else CAPS15
    sites = nmd_sites(key)
    assert sites
    for path in sites:
        seg = get(doc, path)
        cap_share, cap_mat = caps[seg["category"]]
        assert seg["core_share_cap"] == cap_share and seg["core_maturity_cap_years"] == cap_mat
        for value, flag, ok in [(cap_share + 0.05, "above-cap", True), (cap_share + 0.05, "within-cap", False),
                                (cap_share, "within-cap", True), (cap_share, "above-cap", False),
                                (cap_share - 0.1, "above-cap", False), (cap_share - 0.1, "within-cap", True)]:
            m = copy.deepcopy(doc)
            get(m, path).update({"core_share": value, "core_share_flag": flag})
            assert (cs.errors(ref, m) == []) is ok, f"{key} {path}: core_share ({value}, {flag}) expected {'pass' if ok else 'fail'}"
        for value, flag, ok in [(cap_mat + 1.0, "above-cap", True), (cap_mat + 1.0, "within-cap", False),
                                (cap_mat, "within-cap", True), (cap_mat - 1.0, "above-cap", False)]:
            m = copy.deepcopy(doc)
            get(m, path).update({"core_maturity_years": value, "maturity_flag": flag})
            assert (cs.errors(ref, m) == []) is ok, f"{key} {path}: maturity ({value}, {flag}) expected {'pass' if ok else 'fail'}"
        m = copy.deepcopy(doc)
        get(m, path)["core_share_cap"] = 0.99
        assert cs.errors(ref, m) != [], "a cap other than the SRP31 Table 4 cap validates"


def test_the_flags_agree_with_the_values_in_every_fixture_and_one_fixture_is_flagged() -> None:
    flagged = 0
    for key in C14_OUT + C15_OUT:
        for path in nmd_sites(key):
            s = get(load(key), path)
            assert s["core_share_flag"] == ("above-cap" if s["core_share"] > s["core_share_cap"] else "within-cap")
            assert s["maturity_flag"] == ("above-cap" if s["core_maturity_years"] > s["core_maturity_cap_years"] else "within-cap")
            flagged += s["core_share_flag"] == "above-cap" or s["maturity_flag"] == "above-cap"
    assert flagged >= 1, "no fixture carries a flagged cap exceedance, so the flag path is untested on a document"


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
    segs = out(key)["nmd_segments"]
    total = sum(s["balance"] for s in segs)
    assert math.isclose(a["nmd_core_share"]["value"], sum(s["balance"] * s["core_share"] for s in segs) / total, abs_tol=1e-9)
    assert math.isclose(a["nmd_core_maturity_years"]["value"], sum(s["balance"] * s["core_maturity_years"] for s in segs) / total,
                        abs_tol=1e-9)


# --- shock sizes: a currency without a table entry is a labelled Contraste estimate -----------------------------------


def shock_size_sites(key: str) -> list[tuple]:
    return [p for p, o in closed_objects(key) if {"parallel_bp", "origin", "label", "method"} <= set(o)]


@pytest.mark.parametrize("key", ["c14-2022-q4", "c14-models", "c15-long-uf", "c15-models"])
def test_a_shock_size_for_an_untabled_currency_passes_only_labelled_as_a_contraste_estimate(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    sites = shock_size_sites(key)
    assert sites
    label = {"en": "Contraste estimate, not a regulatory parameter", "es": "Estimacion de Contraste, no es un parametro regulatorio"}
    for path in sites:
        m = copy.deepcopy(doc)
        get(m, path).update({"currency": "CLP", "origin": "srp31-table-2024", "label": None, "method": None})
        assert cs.errors(ref, m) != [], f"{key} {path}: CLP under a BCBS table validates"
        m = copy.deepcopy(doc)
        get(m, path).update({"currency": "CLP", "origin": "srp31-table-2016", "label": None, "method": None})
        assert cs.errors(ref, m) != []
        m = copy.deepcopy(doc)
        get(m, path).update({"currency": "CLP", "origin": "contraste-estimate", "label": None, "method": "SRP98.56 to SRP98.63"})
        assert cs.errors(ref, m) != [], "an unlabelled estimate validates"
        m = copy.deepcopy(doc)
        get(m, path).update({"currency": "CLP", "origin": "contraste-estimate", "label": label, "method": None})
        assert cs.errors(ref, m) != [], "an estimate without its method validates"
        m = copy.deepcopy(doc)
        get(m, path).update({"currency": "CLP", "origin": "contraste-estimate", "label": label, "method": "SRP98.56 to SRP98.63"})
        assert cs.errors(ref, m) == [], cs.errors(ref, m)
        m = copy.deepcopy(doc)
        get(m, path).update({"label": label})
        if get(doc, path)["origin"] != "contraste-estimate":
            assert cs.errors(ref, m) != [], "a tabled size carrying an estimate label validates"


# --- the shock calculus (written here independently of the fixture builder) -------------------------------------------


def shape(shock: str, par: float, short: float, long: float) -> list[float]:
    s = [short * math.exp(-t / 4) for t in MIDPOINTS]
    lg = [long * (1 - math.exp(-t / 4)) for t in MIDPOINTS]
    return {
        "parallel-up": [par] * 19, "parallel-down": [-par] * 19,
        "short-up": s, "short-down": [-x for x in s],
        "steepener": [-0.65 * abs(a) + 0.9 * abs(b) for a, b in zip(s, lg)],
        "flattener": [0.8 * abs(a) - 0.6 * abs(b) for a, b in zip(s, lg)],
    }[shock]


def post_rate(r0: float, d_bp: float, floor: float | None) -> float:
    r = r0 + d_bp / 1e4
    return r if floor is None else max(r, min(floor, r0))


def eve_of(cf: list[float], rates: list[float]) -> float:
    return sum(c * math.exp(-r * t) for c, r, t in zip(cf, rates, MIDPOINTS))


def close(a: float, b: float, rel: float = 1e-9, tol: float = 5e-3) -> bool:
    return math.isclose(a, b, rel_tol=rel, abs_tol=tol)


def dense(flows: list[dict]) -> list[float]:
    v = [0.0] * 19
    for f in flows:
        v[f["bucket"] - 1] += f["amount"]
    return v


@pytest.mark.parametrize("key", C14_OUT)
def test_c14_the_shock_shapes_recompute_from_the_size_table_and_the_floor_flags_the_bound_buckets(key: str) -> None:
    o = out(key)
    r0 = o["curve"]["zero_rates_at_midpoints"]
    assert len(o["scenarios"]) == 4
    assert {(s["calibration"], s["nmd_assumption"]) for s in o["scenarios"]} == {
        (c, n) for c in ("2024", "2016") for n in ("behavioural", "contractual")}
    for sc in o["scenarios"]:
        sz = sc["shock_size"]
        table = T2024 if sc["calibration"] == "2024" else T2016
        i = CCY21.index("USD")
        assert (sz["parallel_bp"], sz["short_bp"], sz["long_bp"]) == (table["parallel"][i], table["short"][i], table["long"][i])
        assert sz["origin"] == ("srp31-table-2024" if sc["calibration"] == "2024" else "srp31-table-2016")
        assert [s["shock"] for s in sc["shocks"]] == SHOCKS
        for s in sc["shocks"]:
            for got, want in zip(s["shape_bp"], shape(s["shock"], sz["parallel_bp"], sz["short_bp"], sz["long_bp"])):
                assert math.isclose(got, want, abs_tol=5e-6), (key, s["shock"])
            bound = [k + 1 for k in range(19) if r0[k] + s["shape_bp"][k] / 1e4 < (min(sc["floor"], r0[k]) if sc["floor"] is not None else -9)]
            assert s["floor_bound_buckets"] == bound, (key, s["shock"])


def test_c14_a_floor_binds_in_at_least_one_fixture() -> None:
    assert any(s["floor_bound_buckets"] for k in C14_OUT for sc in out(k)["scenarios"] for s in sc["shocks"]), "no floor binds"


@pytest.mark.parametrize("key", C14_OUT)
def test_c14_every_eve_and_delta_eve_recomputes_and_the_risk_measure_is_the_max_of_the_positive_losses(key: str) -> None:
    o = out(key)
    r0 = o["curve"]["zero_rates_at_midpoints"]
    flows = {n: [0.0] * 19 for n in ("behavioural", "contractual")}
    for item in o["balance_sheet"]["items"]:
        for n in flows:
            for b, v in enumerate(dense(item["cash_flows"][n])):
                flows[n][b] += v
    for sc in o["scenarios"]:
        base = flows[sc["nmd_assumption"]]
        assert close(sc["base_eve"], eve_of(base, r0))
        losses = []
        for s in sc["shocks"]:
            rates = [post_rate(a, d, sc["floor"]) for a, d in zip(r0, s["shape_bp"])]
            assert close(s["eve"], eve_of(s["net_cash_flows"], rates)), (key, sc["calibration"], s["shock"])
            assert close(s["delta_eve"], sc["base_eve"] - s["eve"] + s["kao"]), (key, s["shock"])
            assert close(s["delta_eve_share_tier1"] * sc["outlier"]["tier1"], s["delta_eve"], tol=1e-2)
            losses.append(max(0.0, s["delta_eve"]))
        assert close(sc["eve_risk_measure"], max(losses))
        if max(losses) > 0:
            worst = max(sc["shocks"], key=lambda s: s["delta_eve"])["shock"]
            assert sc["worst_shock"] == worst
        else:
            assert sc["worst_shock"] is None
    assert any(s["kao"] != 0 for sc in o["scenarios"] for s in sc["shocks"]), "no fixture exercises the automatic-option add-on"


@pytest.mark.parametrize("key", C14_OUT)
def test_c14_delta_nii_is_the_one_year_gap_formula_for_the_two_parallel_shocks_only(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    o = out(key)
    r0 = o["curve"]["zero_rates_at_midpoints"]
    for sc_i, sc in enumerate(o["scenarios"]):
        base = [0.0] * 19
        for item in o["balance_sheet"]["items"]:
            for b, v in enumerate(dense(item["cash_flows"][sc["nmd_assumption"]])):
                base[b] += v
        for s_i, s in enumerate(sc["shocks"]):
            if s["shock"] in ("parallel-up", "parallel-down"):
                assert s["delta_nii"] is not None and s["delta_nii_reason"] is None
                want = sum(base[k] * (r0[k] - post_rate(r0[k], s["shape_bp"][k], sc["floor"])) * (1 - MIDPOINTS[k]) for k in range(6))
                assert close(s["delta_nii"], want), (key, sc["calibration"], s["shock"])
            else:
                assert s["delta_nii"] is None and s["delta_nii_reason"]["en"]
            bad = copy.deepcopy(doc)
            site = bad["outputs"]["scenarios"][sc_i]["shocks"][s_i]
            if s["shock"] in ("parallel-up", "parallel-down"):
                site["delta_nii"], site["delta_nii_reason"] = None, {"en": "x", "es": "x"}
            else:
                site["delta_nii"], site["delta_nii_reason"] = 1.0, None
            assert cs.errors(ref, bad) != [], "delta_nii present or absent against the shock kind validates"


@pytest.mark.parametrize("key", C14_OUT)
def test_c14_the_term_deposit_redemption_overlay_moves_the_redeemed_share_to_the_first_bucket(key: str) -> None:
    o = out(key)
    rate0 = o["assumptions"]["term_deposit_redemption_rate"]["value"]
    td = [i for i in o["balance_sheet"]["items"] if i["behavioural_class"] == "term-deposit"]
    assert td
    amount = sum(i["amount"] for i in td)
    for sc in o["scenarios"]:
        base = [0.0] * 19
        for item in o["balance_sheet"]["items"]:
            for b, v in enumerate(dense(item["cash_flows"][sc["nmd_assumption"]])):
                base[b] += v
        for s, u in zip(sc["shocks"], U):
            moved = amount * min(1.0, u * rate0)
            assert close(s["net_cash_flows"][0] - base[0], -moved), (key, s["shock"])
            assert close(sum(s["net_cash_flows"]), sum(base)), "the overlay changes the total"


@pytest.mark.parametrize("key", C14_OUT)
def test_c14_the_outlier_test_is_fifteen_percent_of_tier_one_and_the_behavioural_comparison_closes(key: str) -> None:
    o = out(key)
    for sc in o["scenarios"]:
        ot = sc["outlier"]
        assert ot["threshold_share_tier1"] == 0.15
        assert close(ot["eve_risk_measure"], sc["eve_risk_measure"])
        assert math.isclose(ot["ratio"], ot["eve_risk_measure"] / ot["tier1"], rel_tol=1e-6, abs_tol=1e-9)
        assert ot["breached"] == (ot["ratio"] > 0.15)
    by = {(s["calibration"], s["nmd_assumption"]): {x["shock"]: x["delta_eve"] for x in s["shocks"]} for s in o["scenarios"]}
    rows = o["behavioural_comparison"]
    assert len(rows) == 12 and {(r["calibration"], r["shock"]) for r in rows} == {(c, s) for c in ("2024", "2016") for s in SHOCKS}
    for r in rows:
        assert close(r["delta_eve_behavioural"], by[(r["calibration"], "behavioural")][r["shock"]])
        assert close(r["delta_eve_contractual"], by[(r["calibration"], "contractual")][r["shock"]])
        assert close(r["difference"], r["delta_eve_behavioural"] - r["delta_eve_contractual"])
    # the SVB lesson on the fixture: the behavioural assumptions pass the outlier test that the contractual ones breach
    flags = {(s["calibration"], s["nmd_assumption"]): s["outlier"]["breached"] for s in o["scenarios"]}
    assert flags[("2024", "contractual")] is True and flags[("2024", "behavioural")] is False


# --- C14 dating: the call reports are read only up to the valuation date -----------------------------------------------


def dating_violations(doc: dict) -> list[str]:
    o = doc["outputs"]
    v = o["valuation_date"]
    found = [f"call report {r['report_date']} is after the valuation date {v}" for r in o["data"]["call_reports"] if r["report_date"] > v]
    if o["data"]["data_cutoff"] > v:
        found.append(f"data cutoff {o['data']['data_cutoff']} is after the valuation date {v}")
    if o["data"]["call_reports"] and o["data"]["data_cutoff"] != max(r["report_date"] for r in o["data"]["call_reports"]):
        found.append("the data cutoff is not the latest call report date")
    if o["curve"]["date"] != v:
        found.append(f"the curve date {o['curve']['date']} is not the valuation date {v}")
    if o["balance_sheet"]["as_of"] != v:
        found.append(f"the balance sheet is as of {o['balance_sheet']['as_of']}, not the valuation date {v}")
    return found


def validate_document(ref: str, doc: dict) -> list[str]:
    """Schema errors plus the dating rule: what the producer test of the C14 rows runs on a document."""
    return cs.errors(ref, doc) + (dating_violations(doc) if ref == C14 else [])


@pytest.mark.parametrize("key", C14_OUT)
def test_c14_no_call_report_is_dated_after_the_valuation_date(key: str) -> None:
    doc = load(key)
    assert dating_violations(doc) == []
    assert doc["outputs"]["data"]["read_up_to_valuation_date"] is True
    assert doc["variant_id"].endswith(doc["outputs"]["quarter"].lower())
    late = copy.deepcopy(doc)
    late["outputs"]["data"]["call_reports"].append({"report_date": "2099-12-31", "source": "x", "fields": ["ASSET"]})
    late["outputs"]["data"]["data_cutoff"] = "2099-12-31"
    assert validate_document(C14, late) != []
    assert any("after the valuation date" in m for m in dating_violations(late))
    flag = copy.deepcopy(doc)
    flag["outputs"]["data"]["read_up_to_valuation_date"] = False
    assert cs.errors(C14, flag) != []
    curve = copy.deepcopy(doc)
    curve["outputs"]["curve"]["date"] = "2099-12-31"
    assert validate_document(C14, curve) != []


def test_c14_the_two_fixtures_are_two_valuation_dates() -> None:
    dates = {out(k)["valuation_date"] for k in C14_OUT}
    assert dates == {"2021-12-31", "2022-12-31"}
    assert {out(k)["quarter"] for k in C14_OUT} == {"2021-Q4", "2022-Q4"}


# --- a call-report item the FDIC financials lack is nullable with its reason and the slotting assumption ---------------


@pytest.mark.parametrize("key", C14_OUT)
def test_c14_a_missing_call_report_item_is_null_with_its_reason_and_the_slotting_assumption(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    items = out(key)["balance_sheet"]["items"]
    missing = [(i, it) for i, it in enumerate(items) if it["reported_amount"] is None]
    present = [(i, it) for i, it in enumerate(items) if it["reported_amount"] is not None]
    assert missing and present
    for i, it in missing:
        assert it["reason_missing"]["en"] and it["slotting_assumption"]
        bad = copy.deepcopy(doc)
        bad["outputs"]["balance_sheet"]["items"][i]["reason_missing"] = None
        assert cs.errors(ref, bad) != [], "a null item without its reason validates"
        bad = copy.deepcopy(doc)
        bad["outputs"]["balance_sheet"]["items"][i]["slotting_assumption"] = ""
        assert cs.errors(ref, bad) != [], "a null item without its slotting assumption validates"
    for i, it in present:
        assert it["reason_missing"] is None
        bad = copy.deepcopy(doc)
        bad["outputs"]["balance_sheet"]["items"][i]["reason_missing"] = {"en": "x", "es": "x"}
        assert cs.errors(ref, bad) != [], "a reported item that also states a reason validates"
    for i, it in enumerate(items):
        side = 1.0 if it["side"] == "asset" else -1.0
        for n in ("behavioural", "contractual"):
            assert close(sum(dense(it["cash_flows"][n])), side * it["amount"]), (it["item_id"], n)
    bs = out(key)["balance_sheet"]
    assert close(bs["total_assets"], sum(i["amount"] for i in items if i["side"] == "asset"))
    assert close(bs["total_liabilities"], sum(i["amount"] for i in items if i["side"] == "liability"))


@pytest.mark.parametrize("key", C14_OUT)
def test_c14_the_ladder_rungs_recompute(key: str) -> None:
    o = out(key)
    r0 = o["curve"]["zero_rates_at_midpoints"]
    for lad in o["ladder"]:
        n = lad["nmd_assumption"]
        gap = [0.0] * 19
        assets = [0.0] * 19
        liabs = [0.0] * 19
        for it in o["balance_sheet"]["items"]:
            for b, v in enumerate(dense(it["cash_flows"][n])):
                if it["side"] == "asset":
                    assets[b] += v
                else:
                    liabs[b] += -v
        assert [r["bucket"] for r in lad["repricing_gap"]] == list(range(1, 20))
        for b, r in enumerate(lad["repricing_gap"]):
            assert close(r["assets"], assets[b]) and close(r["liabilities"], liabs[b]) and close(r["gap"], assets[b] - liabs[b])
        # D.1: dNII ~ sum over t_k < 1 of G_k * dr * (1 - t_k), dr = +100 bp; the document is loss-positive
        want = -sum((assets[k] - liabs[k]) * 0.01 * (1 - MIDPOINTS[k]) for k in range(6))
        assert close(lad["delta_nii_gap_100bp_up"], want)
        dg = lad["duration_gap"]
        assert math.isclose(dg["duration_gap_years"], dg["asset_duration_years"] - dg["liability_value"] / dg["asset_value"]
                            * dg["liability_duration_years"], abs_tol=1e-6)
        assert close(dg["equity_change_100bp_up"], -dg["duration_gap_years"] * dg["asset_value"] * 0.01)
    assert {lad["nmd_assumption"] for lad in o["ladder"]} == {"behavioural", "contractual"}


# --- the C14 models document -------------------------------------------------------------------------------------------


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


def test_c14_the_replicating_portfolios_sum_to_one_and_report_their_weighted_maturity() -> None:
    f = fit("c14-models")
    assert f["nmd_models"]
    for m in f["nmd_models"]:
        w = [t["weight"] for t in m["tranches"]]
        assert all(x >= 0 for x in w) and math.isclose(sum(w), 1.0, abs_tol=1e-9) and math.isclose(m["weights_sum"], 1.0, abs_tol=1e-9)
        # rolling tranche reinvested evenly over its life: a tranche of maturity m has weighted average maturity m / 2
        # (BCBS 368 footnote 38: one sixtieth reinvested monthly in a five-year fixed is 2.5 years)
        assert math.isclose(m["weighted_average_maturity_years"], sum(t["weight"] * t["maturity_years"] / 2 for t in m["tranches"]),
                            abs_tol=1e-6)
        for win in m["stability"]:
            assert len(win["weights"]) == len(m["tranches"]) and math.isclose(sum(win["weights"]), 1.0, abs_tol=1e-9)
            assert win["window_start"] < win["window_end"]


def test_c14_a_behavioural_parameter_change_that_coincides_with_a_limit_breach_is_flagged() -> None:
    f = fit("c14-models")
    changes = f["nmd_parameter_changes"]
    assert changes and any(c["flagged"] for c in changes) and any(not c["flagged"] for c in changes)
    for c in changes:
        assert c["from_date"] < c["to_date"]
        assert c["flagged"] == (c["from_value"] != c["to_value"] and c["limit_breach_in_window"]), c


# --- C15: the UR currency, the offset rule state and the indexation charge ----------------------------------------------


@pytest.mark.parametrize("key", C15_OUT)
def test_c15_the_ur_currency_the_offset_state_and_the_indexation_charge_are_required(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    for field in ("ur_currency", "offset_rule", "indexation_charge", "floors", "thresholds", "curves", "legs", "cpi_scenario"):
        bad = copy.deepcopy(doc)
        del bad["outputs"][field]
        assert cs.errors(ref, bad) != [], f"{key}: a document without {field} validates"
    o = out(key)
    assert o["ur_currency"]["code"] == "CLF" and o["ur_currency"]["label"] == "UR" and o["ur_currency"]["treated_as_one_currency"] is True
    assert o["offset_rule"]["state"] in ("on", "off", "compared") and o["offset_rule"]["share"] == 0.5
    assert o["indexation_charge"]["rate"] == 0.025
    for field in ("code", "label", "treated_as_one_currency", "uf_value", "uf_date"):
        bad = copy.deepcopy(doc)
        del bad["outputs"]["ur_currency"][field]
        assert cs.errors(ref, bad) != []
    for field in ("state", "share", "rule"):
        bad = copy.deepcopy(doc)
        del bad["outputs"]["offset_rule"][field]
        assert cs.errors(ref, bad) != []
    for field in ("rate", "pn_ur", "charge"):
        bad = copy.deepcopy(doc)
        del bad["outputs"]["indexation_charge"][field]
        assert cs.errors(ref, bad) != []
    # the UR leg: dropping it, or relabelling it as CLP, fails
    bad = copy.deepcopy(doc)
    bad["outputs"]["legs"] = [leg for leg in bad["outputs"]["legs"] if leg["leg"] != "UR"]
    assert cs.errors(ref, bad) != []
    for relabel in ("CLP",):
        bad = copy.deepcopy(doc)
        for leg in bad["outputs"]["legs"]:
            leg["leg"] = relabel
        assert cs.errors(ref, bad) != [], "two CLP legs and no UR leg validate"
    bad = copy.deepcopy(doc)
    bad["outputs"]["legs"][1]["currency"] = "CLP"
    assert cs.errors(ref, bad) != [], "a UR leg in CLP validates"
    assert [leg["leg"] for leg in o["legs"]] == ["CLP", "UR"] and [leg["currency"] for leg in o["legs"]] == ["CLP", "CLF"]
    bad = copy.deepcopy(doc)
    bad["outputs"]["offset_rule"]["state"] = "maybe"
    assert cs.errors(ref, bad) != []
    bad = copy.deepcopy(doc)
    bad["outputs"]["indexation_charge"]["rate"] = 0.03
    assert cs.errors(ref, bad) != []


def cmf_pair(clp: float, clf: float) -> float:
    """dossier 03 F.2: the CLP and CLF pair with the 50 percent offset when the two have opposite signs."""
    if clp * clf >= 0:
        return max(clp, 0.0) + max(clf, 0.0)
    return max(0.5 * clp + clf, 0.0) if clp <= 0 else max(clp + 0.5 * clf, 0.0)


@pytest.mark.parametrize("clp,clf,want", [(10.0, 20.0, 30.0), (-10.0, -20.0, 0.0), (30.0, -20.0, 20.0), (-20.0, 30.0, 20.0),
                                          (10.0, -40.0, 0.0), (-40.0, 10.0, 0.0), (0.0, 25.0, 25.0), (25.0, 0.0, 25.0)])
def test_the_cmf_offset_rule_golden_values_on_both_signs(clp: float, clf: float, want: float) -> None:
    assert cmf_pair(clp, clf) == want
    assert f"| {clp:g} | {clf:g} | {want:g} |" in API.read_text(encoding="utf-8"), (clp, clf, want)


def c15_rates(o: dict, leg: str) -> list[float]:
    return o["curves"]["clp" if leg == "CLP" else "ur"]["zero_rates_at_midpoints"]


def c15_floor(o: dict, leg: str) -> float:
    return o["floors"]["ur_floor"] if leg == "UR" else o["floors"]["other_floor"]


@pytest.mark.parametrize("key", C15_OUT)
def test_c15_the_pair_offset_the_eve_and_the_indexation_charge_recompute(key: str) -> None:
    o = out(key)
    uf = o["ur_currency"]["uf_value"]
    legs = {leg["leg"]: leg for leg in o["legs"]}
    state = o["offset_rule"]["state"]
    base = {}
    for name, leg in legs.items():
        conv = uf if name == "UR" else 1.0
        base[name] = [v * conv for v in dense([f for it in leg["items"] for f in it["cash_flows"]])]
        r0 = c15_rates(o, name)
        assert close(o["eve"]["base_eve_clp" if name == "CLP" else "base_eve_ur"], eve_of(base[name], r0))
        side_total = sum((1 if it["side"] == "asset" else -1) * it["amount"] for it in leg["items"])
        assert close(leg["net_position"], side_total)
    assert [r["shock"] for r in o["eve"]["rows"]] == SHOCKS
    totals = []
    for row in o["eve"]["rows"]:
        deltas = {}
        for name, res in (("CLP", row["clp"]), ("UR", row["ur"])):
            sz = {s["currency"]: s for s in o["eve_shock_sizes"]}["CLP" if name == "CLP" else "CLF"]
            r0 = c15_rates(o, name)
            want_shape = shape(row["shock"], sz["parallel_bp"], sz["short_bp"], sz["long_bp"])
            for got, w in zip(res["shape_bp"], want_shape):
                assert math.isclose(got, w, abs_tol=5e-6)
            rates = [post_rate(a, d, c15_floor(o, name)) for a, d in zip(r0, res["shape_bp"])]
            assert close(res["eve"], eve_of(res["net_cash_flows"], rates)), (key, row["shock"], name)
            base_eve = o["eve"]["base_eve_clp" if name == "CLP" else "base_eve_ur"]
            assert close(res["delta_eve"], base_eve - res["eve"] + res["kao"]), (key, row["shock"], name)
            deltas[name] = res["delta_eve"]
        pair = row["pair"]
        assert close(pair["delta_clp"], deltas["CLP"]) and close(pair["delta_ur"], deltas["UR"])
        assert pair["opposite_signs"] == (deltas["CLP"] * deltas["UR"] < 0)
        assert close(pair["with_offset"], cmf_pair(deltas["CLP"], deltas["UR"]))
        assert close(pair["without_offset"], max(deltas["CLP"], 0) + max(deltas["UR"], 0))
        assert close(pair["used"], pair["without_offset"] if state == "off" else pair["with_offset"])
        assert close(row["total_delta_eve"], pair["used"])
        totals.append(row["total_delta_eve"])
    assert close(o["eve"]["delta_eve"], max(totals))
    assert o["eve"]["worst_shock"] == SHOCKS[totals.index(max(totals))]
    # the indexation charge: 2.5 percent of the absolute net UF position, in the reporting currency
    ic = o["indexation_charge"]
    assert close(ic["pn_ur"], legs["UR"]["net_position"] * uf)
    assert close(ic["abs_pn_ur"], abs(ic["pn_ur"])) and close(ic["charge"], 0.025 * abs(ic["pn_ur"]))
    assert math.isclose(ic["net_position_uf_units"] * uf, ic["pn_ur"], rel_tol=1e-9, abs_tol=1e-3)
    if state == "compared":
        assert any(r["pair"]["opposite_signs"] for r in o["eve"]["rows"] + o["nii"]["rows"]), \
            "the compared fixture has no shock where the two legs have opposite signs"
        assert any(not close(r["pair"]["with_offset"], r["pair"]["without_offset"]) for r in o["eve"]["rows"] + o["nii"]["rows"])


@pytest.mark.parametrize("key", C15_OUT)
def test_c15_delta_nii_is_the_max_pair_plus_the_indexation_charge(key: str) -> None:
    o = out(key)
    uf = o["ur_currency"]["uf_value"]
    legs = {leg["leg"]: leg for leg in o["legs"]}
    base = {n: [v * (uf if n == "UR" else 1.0) for v in dense([f for it in legs[n]["items"] for f in it["cash_flows"]])] for n in legs}
    assert [r["shock"] for r in o["nii"]["rows"]] == ["parallel-up", "parallel-down"]
    sizes = {s["currency"]: s["parallel_bp"] for s in o["nii_shock_sizes"]}
    assert sizes == {"CLP": 300, "CLF": 300}
    pairs = []
    for row in o["nii"]["rows"]:
        d = {}
        for name, res in (("CLP", row["clp"]), ("UR", row["ur"])):
            sign = 1 if row["shock"] == "parallel-up" else -1
            assert res["shock_bp"] == sign * 300
            r0 = c15_rates(o, name)
            want = sum(base[name][k] * (r0[k] - post_rate(r0[k], res["shock_bp"], c15_floor(o, name))) * (1 - MIDPOINTS[k])
                       for k in range(6))
            assert close(res["delta_nii"], want), (key, row["shock"], name)
            assert len(res["cash_flows"]) == 6 and all(close(a, b) for a, b in zip(res["cash_flows"], base[name][:6]))
            d[name] = res["delta_nii"]
        p = row["pair"]
        assert close(p["with_offset"], cmf_pair(d["CLP"], d["UR"])) and close(p["without_offset"], max(d["CLP"], 0) + max(d["UR"], 0))
        assert close(p["used"], p["without_offset"] if o["offset_rule"]["state"] == "off" else p["with_offset"])
        pairs.append(p["used"])
    n = o["nii"]
    assert close(n["max_pair"], max(pairs))
    assert close(n["indexation_charge"], o["indexation_charge"]["charge"])
    assert close(n["delta_nii"], n["max_pair"] + n["indexation_charge"])


@pytest.mark.parametrize("key", C15_OUT)
def test_c15_the_floor_effects_recompute_and_the_prioritised_bank_tests_follow_the_thresholds(key: str) -> None:
    o = out(key)
    fl = o["floors"]
    assert (fl["ur_floor"], fl["other_floor"]) == (-0.02, 0.0)
    uf = o["ur_currency"]["uf_value"]
    legs = {leg["leg"]: leg for leg in o["legs"]}
    for e in fl["effects"]:
        assert close(e["effect"], e["delta_with_floor"] - e["delta_without_floor"])
        assert e["buckets_floored"] >= 1
        name = e["leg"]
        row = next(r for r in (o["eve"]["rows"] if e["measure"] == "delta-eve" else o["nii"]["rows"]) if r["shock"] == e["shock"])
        res = row["clp"] if name == "CLP" else row["ur"]
        r0 = c15_rates(o, name)
        if e["measure"] == "delta-eve":
            nofloor = [r0[k] + res["shape_bp"][k] / 1e4 for k in range(19)]
            base_eve = o["eve"]["base_eve_clp" if name == "CLP" else "base_eve_ur"]
            assert close(e["delta_with_floor"], res["delta_eve"])
            assert close(e["delta_without_floor"], base_eve - eve_of(res["net_cash_flows"], nofloor) + res["kao"])
            assert e["buckets_floored"] == len(res["floor_bound_buckets"])
        else:
            conv = uf if name == "UR" else 1.0
            base = [v * conv for v in dense([f for it in legs[name]["items"] for f in it["cash_flows"]])]
            assert close(e["delta_with_floor"], res["delta_nii"])
            assert close(e["delta_without_floor"], sum(base[k] * (-res["shock_bp"] / 1e4) * (1 - MIDPOINTS[k]) for k in range(6)))
    th = o["thresholds"]
    got = {t["id"]: t for t in th["tests"]}
    assert {i: (t["threshold"]) for i, t in got.items()} == {"nii-tier1": 0.05, "eve-tier1": 0.15, "nii-margin": 0.18}
    assert close(got["nii-tier1"]["measure"], o["nii"]["delta_nii"]) and close(got["eve-tier1"]["measure"], o["eve"]["delta_eve"])
    assert close(got["nii-tier1"]["base"], th["tier1"]) and close(got["eve-tier1"]["base"], th["tier1"])
    assert close(got["nii-margin"]["base"], th["net_interest_and_indexation_margin_12m"])
    for t in got.values():
        assert math.isclose(t["ratio"], t["measure"] / t["base"], rel_tol=1e-6)
        assert t["breached"] == (t["ratio"] > t["threshold"])
    assert th["prioritised"] == any(t["breached"] for t in got.values())


def test_c15_the_floors_active_variant_exists_and_the_variant_ids_are_the_sdd_ones() -> None:
    ref = cs.load_json(SCHEMAS / "c15" / "variant-annex1-variant.schema.json")
    ids = ref["$defs"]["c15Variant"]["properties"]["id"]["enum"]
    assert ids == ["long-uf", "short-uf", "cpi-surprise", "clp-steepener", "offset-on-off", "floors-active"]
    assert {out(k)["variant"]["id"] for k in C15_OUT} == {"long-uf", "offset-on-off", "cpi-surprise"}
    for k in C15_OUT:
        doc = load(k)
        assert doc["variant_id"] == "fixture-" + out(k)["variant"]["id"]
        assert out(k)["balance_sheet_month"] == out(k)["curves_month"] == out(k)["as_of"][:7]
        assert out(k)["curves"]["clp"]["month"] == out(k)["curves"]["ur"]["month"] == out(k)["curves_month"]


@pytest.mark.parametrize("key", C15_OUT)
def test_c15_the_cpi_surprise_effect_and_the_curves_are_required_and_attributed(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    o = out(key)
    cpi = o["cpi_scenario"]
    if cpi is not None:
        # loss-positive: a net UF asset gains from an inflation surprise
        assert close(cpi["effect"], -o["indexation_charge"]["pn_ur"] * cpi["surprise_pp"] / 100)
    for c in ("clp", "ur"):
        assert "Banco Central de Chile" in o["curves"][c]["attribution"] and "adaptation" in o["curves"][c]["attribution"]
        bad = copy.deepcopy(doc)
        bad["outputs"]["curves"][c] = None
        assert cs.errors(ref, bad) != [], "a null curve validates: the C15 curves are required"


def test_c15_one_fixture_applies_a_cpi_surprise_and_the_others_do_not() -> None:
    assert [out(k)["cpi_scenario"] is not None for k in C15_OUT] == [False, False, True]


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
    assert len(f["curve_models"]) == 2 and {c["curve"] for c in f["curve_models"]} == {"CLP", "UR"}
    for m in f["nmd_models"]:
        assert math.isclose(sum(t["weight"] for t in m["tranches"]), 1.0, abs_tol=1e-9)


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
        assert d["version"] == "1.0.0"
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
    "simulation": ["simulate_nii", "hw1f_scenarios", "dns_scenarios", "ear_evar"],
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
    for golden in ("0.417", "+41.7", "+25.4", "-1.6", "0.0028", "0.0417", "0.1667", "25.0", "0.0609", "0.298384", "29.447",
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
    assert math.isclose(best / 1000, 29.447, abs_tol=2e-3)     # the maximiser is 29.447 months, the 30 of the paper is rounded
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
