"""U11-S: the C16 case contracts, their fixtures, the ``balance_sheet`` family bump, the catalog rows and the engine liquidity API.

The fixtures validate by discovery (tests/contracts/contract_schemas.py) against exactly one schema; the schemas are strict both
ways (a removed or an added key fails); the survival period is a number only where the net liquidity position turns negative
and "survives the horizon" with the horizon otherwise; the scoring block carries both denominators of the realised outflow; the
LCR block is labelled a Basel formula on call-report aggregates and its inflows and Level 2B stay under their caps; every named
parameter (the conventions) carries the label "convention"; a call-report field is named only from the U11 research addendum or
the C14 field list; the family bump keeps the C14 and C15 balance-sheet datasets valid.

The cross-field checks are importable functions in ``semantics.py`` that the bake calls on every document it writes; these tests
run them over the fixtures and over a table of planted defects, each refused by the schema or by the checker. The engine contract
names every function of the modules table of plans/contraste/units/U11-sizing.md, and its golden values recompute here. The
fixtures are labelled as fixtures and never published as results.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Iterator

import pytest

import contract_schemas as cs


def _load_semantics():
    """The producer checker of this folder under a name of its own: several suites ship a ``semantics.py`` (C14's is loaded by the
    bare name) and one run of the whole tree must keep each suite on its own checker."""
    spec = importlib.util.spec_from_file_location("contracts_u11_semantics", Path(__file__).with_name("semantics.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["contracts_u11_semantics"] = mod
    spec.loader.exec_module(mod)
    return mod


sm = _load_semantics()

ROOT = cs.ROOT
sys.path.insert(0, str(ROOT / "data-pipeline"))
FIXTURES = ROOT / "docs" / "contracts" / "fixtures"
SCHEMAS = ROOT / "docs" / "contracts" / "schemas"
API = ROOT / "docs" / "contracts" / "engine" / "liquidity-api.md"
ROWS = ROOT / "docs" / "contracts" / "rows" / "U11.md"
CHANGES = ROOT / "changes" / "U11-S.md"

SC, RV, MD = "c16/variant-scenario", "c16/variant-reverse", "c16/models"
SCHEMA_REFS = [SC, RV, MD]
FILES = {
    "lcr-standard": (SC, FIXTURES / "c16" / "variant-scenario-lcr-standard-fixture.json"),
    "list-adverse": (SC, FIXTURES / "c16" / "variant-scenario-list-adverse-fixture.json"),
    "list-extreme": (SC, FIXTURES / "c16" / "variant-scenario-list-extreme-fixture.json"),
    "fast-run": (SC, FIXTURES / "c16" / "variant-scenario-fast-run-fixture.json"),
    "htm-losses": (SC, FIXTURES / "c16" / "variant-scenario-htm-losses-fixture.json"),
    "reverse": (RV, FIXTURES / "c16" / "variant-reverse-fixture.json"),
    "models": (MD, FIXTURES / "c16" / "models-fixture.json"),
}
SCENARIO_KEYS = ["lcr-standard", "list-adverse", "list-extreme", "fast-run", "htm-losses"]
PATH_KEYS = ["list-adverse", "list-extreme", "fast-run", "htm-losses"]
OUT_KEYS = SCENARIO_KEYS + ["reverse"]
ALL = list(FILES)
KINDS = {SC: "scenario", RV: "reverse-stress"}
ROW_IDS = ["c16-outputs", "c16-outputs-reverse", "c16-models", "engine-liquidity-api"]

# --- the values of the research record, typed here again (U11 research addendum L1 to L3; dossier 05 E; dossier 01 G) -------------

LIST_CONTRACTUAL = [  # N Table 3.2: item, baseline, adverse, extreme
    ("securities-issued", 1.0, 1.0, 1.0), ("secured-funding", 1.0, 1.0, 1.0),
    ("stable-retail", 0.0, 0.18, 0.27), ("other-retail", 0.0, 0.39, 0.48), ("operational", 0.0, 0.37, 0.50),
    ("non-operational-credit-institutions", 1.0, 1.0, 1.0), ("non-operational-other-financial", 1.0, 1.0, 1.0),
    ("non-operational-non-financial-corporates", 0.0, 0.52, 0.76), ("non-operational-others", 0.0, 0.52, 0.76),
    ("fx-swaps", 1.0, 1.0, 1.0), ("derivatives-payable", 1.0, 1.0, 1.0), ("other-cash-outflows", 1.0, 1.0, 1.0),
]
LIST_OPEN = [  # N Table 3.3: class, baseline, adverse, extreme (daily rates, decimals)
    ("open-repos", 1.0, 1.0, 1.0), ("stable-retail", 0.0, 0.00103258, 0.00161494), ("other-retail", 0.0, 0.00373218, 0.00440873),
    ("operational", 0.0, 0.00514464, 0.00750509), ("non-operational-credit-institutions", 1.0, 1.0, 1.0),
    ("non-operational-other-financial", 1.0, 1.0, 1.0), ("non-operational-non-financial-corporates", 0.0, 0.00688541, 0.01065229),
    ("non-operational-others", 0.0, 0.00688541, 0.01065229), ("other-transactions", 1.0, 1.0, 1.0),
]
LIST_INFLOWS = [  # N Table 3.2 inflows: item, baseline, adverse, extreme
    ("secured-lending", 1.0, 1.0, 1.0), ("loans-retail", 0.0, 0.0, 0.0), ("loans-non-financial-corporates", 0.0, 0.0, 0.0),
    ("loans-credit-institutions", 1.0, 1.0, 1.0), ("loans-other-financial", 1.0, 1.0, 1.0), ("loans-others", 0.0, 0.0, 0.0),
    ("fx-swaps", 1.0, 1.0, 1.0), ("derivatives-receivable", 1.0, 1.0, 1.0), ("paper-own-portfolio", 1.0, 1.0, 1.0),
    ("other-cash-inflows", 1.0, 1.0, 1.0),
]
LIST_DRAWDOWN = [("committed-credit-facilities", 0.00202704, 0.00257634), ("liquidity-facilities", 0.01443904, 0.02176434)]
TABLE_A1 = [  # d555 Table A.1, dossier 05 E.2 l.248-259: row id, bank, year, outflow share, days
    ("svb-2023", "SVB", 2023, 0.85, 2), ("first-republic-2023", "First Republic", 2023, 0.57, 90),
    ("svb-uk-2023", "SVB UK", 2023, 0.30, 1), ("credit-suisse-2023", "Credit Suisse", 2023, 0.21, 90),
    ("signature-2023", "Signature", 2023, 0.20, 1), ("icesave-2008", "Icesave", 2008, 0.20, 75),
    ("northern-rock-2007", "Northern Rock", 2007, 0.20, 4), ("wamu-2008", "WaMu", 2008, 0.10, 10),
    ("indymac-2008", "IndyMac", 2008, 0.08, 14),
]
IMPLIED = {  # recomputed 1 - (1 - F)^(1 / n), six decimals
    "svb-2023": 0.612702, "first-republic-2023": 0.009334, "svb-uk-2023": 0.3, "credit-suisse-2023": 0.002616,
    "signature-2023": 0.2, "icesave-2008": 0.002971, "northern-rock-2007": 0.054258, "wamu-2008": 0.010481,
    "indymac-2008": 0.005938,
}
CALL_REPORT_FIELDS = {  # L3 (the addendum) and the C14 FDIC_FIELDS list (cases/c14/fetch.py) and the sizing R6 probe
    "SC", "SCHA", "SCHF", "SCAA", "SCAF", "DEPUNA", "DEPINS", "DEPSMAMT", "DEPLGAMT", "CHBAL", "FREPO", "FREPP", "OTHBFHLB",
    "SCUST", "SCUS", "SCAGE", "SCASPNSUM", "SCASPNHA", "SCASPNAF", "SCSPN", "SCMTGBK", "SCGTY", "SCCOL", "SCCMOT", "SCCMPT",
    "SCRMBPI", "SCODPC", "SCODPI", "SCMUNI", "SCMUNIHA", "SCMUNIHF", "SCMUNIAA", "SCMUNIAF", "SCSNHAA", "SCSNHAF", "SCDOMO",
    "SCFORD", "SCABS", "SCRDEBT", "SCEQFV", "SCPLEDGE", "SCHTMRES", "DEP", "DEPDOM", "DEPFOR",
    "CERT", "REPDTE", "NAME", "ASSET", "LIAB", "EQ", "RBCT1J", "DEPNIDOM", "DEPIDOM", "DEPNIFOR", "DEPIFOR", "DEPSMB", "DEPLGB",
    "NTRTIME", "CD3LES", "CD3T12", "CD1T3", "CDOV3", "CD3LESS", "CD3T12S", "CD1T3S", "CDOV3S", "SCNM3LES", "SCNM3T12", "SCNM1T3",
    "SCNM3T5", "SCNM5T15", "SCNMOV15", "SCPT3LES", "SCPT3T12", "SCPT1T3", "SCPT3T5", "SCPT5T15", "SCPTOV15", "SCO3YLES",
    "SCOOV3Y", "LNLSGR", "LNLSNET", "LNATRES", "LNRS3LES", "LNRS3T12", "LNRS1T3", "LNRS3T5", "LNRS5T15", "LNRSOV15", "LNOT3LES",
    "LNOT3T12", "LNOT1T3", "LNOT3T5", "LNOT5T15", "LNOTOV15", "OTHBFH1L", "OTBFH1T3", "OTBFH3T5", "OTBFHOV5", "OTHBRF",
    "OTBOT1L", "OTBOT1T3", "OTBOT3T5", "OTBOTOV5", "SUBND", "INTINC", "EINTEXP", "NIM", "EDEP", "ISC", "ILNDOM", "ICHBAL",
    "IFREPO", "EFREPP",
}
CONVENTION_NAMES = [
    "deposit_category_mapping", "variant_scenarios", "day_calendar", "cbc_securities_mapping", "monetisation_schedule",
    "fast_run_calibration_rule", "cliff_days", "contractual_bucket_edges_days", "event_horizon_days", "uninsured_share_grid",
    "htm_loss_multiple_grid", "runoff_multiplier_grid", "reverse_target_days", "list_compounding_tolerance",
    "monotonicity_tolerance_days", "nlp_identity_tolerance", "cliff_amber_threshold", "cliff_red_threshold",
    "scoring_ratio_green", "scoring_ratio_amber", "generator_truth_se_green", "generator_truth_se_red",
    "htm_revaluation_green", "htm_revaluation_amber", "round_trip_tolerance_days", "cbc_haircut_band",
]


def load(key: str) -> Any:
    return cs.load_json(FILES[key][1])


def out(key: str) -> dict:
    return load(key)["outputs"]


def ref_of(key: str) -> str:
    return FILES[key][0]


def root_of(key: str) -> str:
    return "fit" if key == "models" else "outputs"


def errs(ref: str, doc: Any) -> list[str]:
    """Pass or fail only (is_valid short-circuits at the first error, a probe run over a large document stays fast); the first
    test of each fixture uses ``cs.errors`` for the messages."""
    return [] if cs.validator(ref).is_valid(doc) else ["invalid"]


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
    assert doc["provenance"]["generators"] == ["fixture:u11-s-contracts"]
    assert any(i["source"] == "fixture-not-a-result" for i in doc["provenance"]["inputs"])
    ident = doc["variant_id"] if "variant_id" in doc else doc["fit_id"]
    assert str(ident).startswith("fixture-")
    assert doc["provenance"]["truth_status"] in ("synthetic-known-truth", "synthetic-calibrated")


def released_fragment(path: Path) -> str:
    """The unit's changelog fragment, or, once a release merged and deleted it (fragments.py changelog --apply), the text of the
    CHANGELOG entry that holds it, so the unit's needles are still checked where they now live."""
    if path.is_file():
        return path.read_text(encoding="utf-8")
    log = (path.parents[1] / "CHANGELOG.md").read_text(encoding="utf-8")
    entries = re.split(r"(?m)^## ", log)[1:]
    return next(e for e in entries if e.startswith("[0.13.000]"))


def test_every_u11_schema_is_case_folder_conformant_and_case_prefixed() -> None:
    assert cs.case_folder_violations() == []
    files = sorted((SCHEMAS / "c16").glob("*.schema.json"))
    assert {p.relative_to(SCHEMAS).as_posix() for p in files} == {f"{ref}.schema.json" for ref in SCHEMA_REFS}
    for p in files:
        names = cs.load_json(p).get("$defs", {})
        assert names, p
        for name in names:
            assert name.startswith("c16"), f"{p.name}: $defs name {name!r} is not prefixed c16"


def test_a_def_two_files_of_the_case_share_has_one_definition() -> None:
    defs = {p.name: cs.load_json(p)["$defs"] for p in (SCHEMAS / "c16").glob("*.schema.json")}
    names = list(defs)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            for name in set(defs[a]) & set(defs[b]):
                assert defs[a][name] == defs[b][name], f"{name} differs between {a} and {b}"


def test_every_u11_variant_schema_declares_its_outputs_kind() -> None:
    by_ref = {c.ref: c for c in cs.candidates()}
    for ref, kind in KINDS.items():
        assert by_ref[ref].consts["outputs.kind"] == kind
        assert by_ref[ref].consts["case_id"] == "C16"
    assert by_ref[MD].consts["case_id"] == "C16"
    assert cs.default_variants().get("C16") is None
    assert cs.default_violations() == []


def test_the_scenario_and_reverse_documents_are_two_schemas_because_their_outputs_differ() -> None:
    a = cs.load_json(SCHEMAS / "c16" / "variant-scenario.schema.json")["$defs"]
    b = cs.load_json(SCHEMAS / "c16" / "variant-reverse.schema.json")["$defs"]
    assert "c16Path" in a and "c16Path" not in b
    assert "c16ReverseBase" in b and "c16ReverseBase" not in a


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
            assert errs(ref, bad) != [], f"{key}: removing {'/'.join(map(str, path))}/{k} still validates"
            checked += 1
    assert checked > 60


@pytest.mark.parametrize("key", ALL)
def test_a_key_added_to_any_object_fails(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    for path, _ in probes(key):
        bad = copy.deepcopy(doc)
        get(bad, path)["unknown_key"] = 1
        assert errs(ref, bad) != [], f"{key}: adding a key at {'/'.join(map(str, path))} still validates"


@pytest.mark.parametrize("key", OUT_KEYS)
def test_a_document_without_case_id_or_outputs_kind_does_not_pass(key: str) -> None:
    ref, path, doc = ref_of(key), FILES[key][1], load(key)
    no_case = copy.deepcopy(doc)
    del no_case["case_id"]
    assert errs(ref, no_case) != []
    with pytest.raises(cs.SelectionError):
        cs.schema_for_document(path, no_case)
    no_kind = copy.deepcopy(doc)
    del no_kind["outputs"]["kind"]
    assert errs(ref, no_kind) != []
    chosen = None
    try:
        chosen = cs.schema_for_document(path, no_kind)
    except cs.SelectionError:
        pass
    assert chosen != ref
    if chosen is not None:
        assert errs(chosen, no_kind) != []


@pytest.mark.parametrize("key", ALL)
def test_a_wrong_case_id_is_rejected_and_no_fixture_validates_against_another_schema(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    bad = copy.deepcopy(doc)
    bad["case_id"] = "C99"
    assert errs(ref, bad) != []
    others = [c.ref for c in cs.candidates() if c.ref != ref]
    assert others
    for other in others:
        assert errs(other, doc) != [], f"{key} validates against {other}"


# --- units: money in USD thousands, rates per day, horizons in days -------------------------------------------------------


@pytest.mark.parametrize("key", OUT_KEYS + ["models"])
def test_a_money_block_without_its_currency_or_units_fails(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    root = root_of(key)
    for name in ("currency", "units"):
        bad = copy.deepcopy(doc)
        del bad[root][name]
        assert errs(ref, bad) != [], f"{key}: {root} without {name} validates"
    wrong = copy.deepcopy(doc)
    wrong[root]["units"]["money_scale"] = "units"
    assert errs(ref, wrong) != []
    worse = copy.deepcopy(doc)
    worse[root]["currency"] = "dollars"
    assert errs(ref, worse) != []
    assert doc[root]["currency"] == "USD" and doc[root]["units"]["money_scale"] == "thousands"
    assert doc[root]["units"]["rate"] == "decimal-per-day" and doc[root]["units"]["horizon"] == "days"


@pytest.mark.parametrize("key", OUT_KEYS)
def test_every_impact_item_states_its_unit_and_the_two_required_items_exist(key: str) -> None:
    doc = load(key)
    required = {"lcr", "survival_days"} if key != "reverse" else {"multiplier_list_adverse", "multiplier_list_extreme",
                                                                    "multiplier_fast_run"}
    assert required <= set(doc["impact"])
    for name, item in doc["impact"].items():
        assert item["unit"].strip(), name
    bad = copy.deepcopy(doc)
    del bad["impact"][sorted(required)[0]]
    assert errs(ref_of(key), bad) != []


# --- the survival period -------------------------------------------------------------------------------------------------


def survivals(doc: dict) -> list[tuple[str, dict]]:
    found = []
    o = doc["outputs"]
    if o["kind"] == "scenario":
        if o["path"] is not None:
            found.append(("path.survival", o["path"]["survival"]))
        found += [(f"time_block.{i}", t["survival"]) for i, t in enumerate(o["time_block"]) if t["survival"] is not None]
    else:
        for b in o["bases"]:
            found.append((b["base_id"] + ".base", b["base_survival"]))
            found += [(f"{b['base_id']}.curve.{i}", p["survival"]) for i, p in enumerate(b["curve"])]
    return found


@pytest.mark.parametrize("key", PATH_KEYS + ["reverse"])
def test_a_survival_period_that_is_a_number_where_the_bank_survives_the_horizon_fails(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    sites = [s for _, s in survivals(doc) if s["kind"] == "survives-horizon"]
    days = [s for _, s in survivals(doc) if s["kind"] == "day"]
    assert days, f"{key}: no fixture survival is a day"
    assert sites or key != "fast-run"
    for s in days:
        assert isinstance(s["day"], int) and s["day"] >= 1 and s["horizon_days"] >= s["day"]
    # a number on a "survives the horizon" record, and "survives the horizon" with no horizon, both fail
    for path, s in survivals(doc):
        bad = copy.deepcopy(doc)
        target = _survival_at(bad, path)
        if s["kind"] == "survives-horizon":
            target["day"] = 10
            assert errs(ref, bad) != [], f"{key}: {path} survives the horizon with a day"
        else:
            target["day"] = None
            assert errs(ref, bad) != [], f"{key}: {path} is a day with a null number"
        worse = copy.deepcopy(doc)
        del _survival_at(worse, path)["horizon_days"]
        assert errs(ref, worse) != []


def _survival_at(doc: dict, path: str) -> dict:
    o = doc["outputs"]
    if path == "path.survival":
        return o["path"]["survival"]
    if path.startswith("time_block."):
        return o["time_block"][int(path.split(".")[1])]["survival"]
    base_id, rest = path.split(".", 1)
    b = next(x for x in o["bases"] if x["base_id"] == base_id)
    return b["base_survival"] if rest == "base" else b["curve"][int(rest.split(".")[1])]["survival"]


def test_the_checker_flags_a_day_where_the_nlp_never_turns_negative_and_a_survival_where_it_does() -> None:
    doc = load("fast-run")
    nlp = doc["outputs"]["path"]["ladder"]["nlp"]
    assert min(nlp) >= 0 and doc["outputs"]["path"]["survival"]["kind"] == "survives-horizon"
    bad = copy.deepcopy(doc)
    bad["outputs"]["path"]["survival"] = {"kind": "day", "day": 4, "horizon_days": len(nlp)}
    assert any("survival" in m for m in sm.check_document(bad))
    lst = load("list-adverse")
    p = lst["outputs"]["path"]
    first = next(i + 1 for i, v in enumerate(p["ladder"]["nlp"]) if v < 0)
    assert p["survival"] == {"kind": "day", "day": first, "horizon_days": len(p["ladder"]["nlp"])}
    worse = copy.deepcopy(lst)
    worse["outputs"]["path"]["survival"] = {"kind": "survives-horizon", "day": None, "horizon_days": len(p["ladder"]["nlp"])}
    assert any("survival" in m for m in sm.check_document(worse))
    wrong_day = copy.deepcopy(lst)
    wrong_day["outputs"]["path"]["survival"]["day"] = first + 1
    assert any("survival" in m for m in sm.check_document(wrong_day))


def test_the_fixtures_show_both_survival_outcomes_and_the_impact_item_follows_them() -> None:
    kinds = {k: load(k)["outputs"]["path"]["survival"]["kind"] for k in PATH_KEYS}
    assert set(kinds.values()) == {"day", "survives-horizon"}
    for key in PATH_KEYS:
        o = load(key)
        s = o["outputs"]["path"]["survival"]
        value = o["impact"]["survival_days"]["value"]
        assert (value is None) == (s["kind"] == "survives-horizon")
        assert value is None or value == s["day"]
    lcr = load("lcr-standard")["outputs"]
    assert lcr["path"] is None and lcr["path_reason"]["en"]
    assert load("lcr-standard")["impact"]["survival_days"]["value"] is None


# --- the scoring block: both denominators, the anchor, the Table A.1 rows ---------------------------------------------------


@pytest.mark.parametrize("key", SCENARIO_KEYS)
def test_a_scoring_block_without_both_denominators_fails(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    den = doc["outputs"]["scoring"]["denominators"]
    assert [d["id"] for d in den] == ["board-stated-share", "call-report-dep"]
    assert den[0]["denominator_amount"] is None and den[1]["denominator_amount"] > 0
    for drop in (0, 1):
        bad = copy.deepcopy(doc)
        del bad["outputs"]["scoring"]["denominators"][drop]
        assert errs(ref, bad) != []
    swapped = copy.deepcopy(doc)
    swapped["outputs"]["scoring"]["denominators"].reverse()
    assert errs(ref, swapped) != []
    del_key = copy.deepcopy(doc)
    del del_key["outputs"]["scoring"]["denominators"]
    assert errs(ref, del_key) != []


@pytest.mark.parametrize("key", SCENARIO_KEYS)
def test_the_scoring_block_recomputes_and_the_anchor_is_labelled_not_a_forecast(key: str) -> None:
    doc = load(key)
    assert sm.check_document(doc) == []
    sc = doc["outputs"]["scoring"]
    anchor = sc["svb_anchor"]
    assert anchor["forecast_claim"] is False and anchor["outflow_share"] == 0.85 and anchor["days"] == 2
    assert abs(anchor["implied_daily_rate"] - 0.612702) < 5e-7
    den = sc["denominators"][1]
    assert abs(den["realised_share"] - den["realised_amount"] / den["denominator_amount"]) < 1e-9
    assert den["realised_amount"] == 140000000
    rows = sc["table_a1_scoring"]
    assert [(r["row_id"], r["observed_share"], r["horizon_days"]) for r in rows] == [(t[0], t[3], t[4]) for t in TABLE_A1]
    roles = {r["row_id"]: r["role"] for r in rows}
    if key == "fast-run":
        assert {v for k, v in roles.items() if k.endswith("2023")} == {"scored"}
        assert {v for k, v in roles.items() if not k.endswith("2023")} == {"calibration"}
    else:
        assert set(roles.values()) == {"reference"}


def test_the_lcr_variant_compares_at_its_own_horizon_and_says_why() -> None:
    sc = load("lcr-standard")["outputs"]["scoring"]
    assert sc["modelled_outflow"]["at_event_horizon"] is None and sc["modelled_outflow"]["at_event_horizon_reason"]["en"]
    assert {d["compared_at"] for d in sc["denominators"]} == {"model-horizon"}
    for key in PATH_KEYS:
        s = load(key)["outputs"]["scoring"]
        assert s["modelled_outflow"]["at_event_horizon"]["horizon_days"] == 2
        assert {d["compared_at"] for d in s["denominators"]} == {"event-horizon"}


# --- the LCR block --------------------------------------------------------------------------------------------------------


def test_the_lcr_block_is_labelled_a_basel_formula_on_call_report_aggregates() -> None:
    ref, doc = SC, load("lcr-standard")
    lcr = doc["outputs"]["lcr"]
    assert lcr["label"] == "basel-formula-on-call-report-aggregates" and lcr["reported_or_regulatory"] is False
    for mutate in (lambda d: d["outputs"]["lcr"].update(label="reported-lcr"),
                   lambda d: d["outputs"]["lcr"].update(reported_or_regulatory=True),
                   lambda d: d["outputs"]["lcr"].pop("label"),
                   lambda d: d["outputs"]["lcr"].pop("reported_or_regulatory"),
                   lambda d: d["outputs"]["lcr"].pop("statement")):
        bad = copy.deepcopy(doc)
        mutate(bad)
        assert errs(ref, bad) != []


def test_the_lcr_inflows_never_exceed_the_cap_and_level_2b_never_exceeds_its_cap() -> None:
    doc = load("lcr-standard")
    lcr = doc["outputs"]["lcr"]
    assert lcr["inflow_cap"] == 0.75 and lcr["hqla"]["caps"] == {"l2_cap": 0.4, "l2b_cap": 0.15}
    assert lcr["inflows_counted"] <= 0.75 * lcr["total_outflows"] + 1e-9
    assert lcr["hqla"]["l2b_share"] <= 0.15 + 1e-12 and lcr["hqla"]["l2_share"] <= 0.4 + 1e-12
    assert lcr["total_inflows"] > 0.75 * lcr["total_outflows"], "the fixture exercises the inflow cap"
    assert lcr["hqla"]["adj_15"] > 0, "the fixture exercises the 15 percent cap"
    assert sm.check_document(doc) == []
    over = copy.deepcopy(doc)
    over["outputs"]["lcr"]["inflows_counted"] = lcr["total_inflows"]
    assert any("inflow" in m for m in sm.check_document(over))
    over_b = copy.deepcopy(doc)
    h = over_b["outputs"]["lcr"]["hqla"]
    h["adj_15"] = 0.0
    h["hqla"] = h["l1"] + h["l2a"] + h["l2b"]
    h["l2b_share"] = h["l2b"] / h["hqla"]
    assert any("level 2B" in m or "Level 2B" in m for m in sm.check_document(over_b))
    wrong_ratio = copy.deepcopy(doc)
    wrong_ratio["outputs"]["lcr"]["ratio"] = 9.99
    assert any("ratio" in m for m in sm.check_document(wrong_ratio))


@pytest.mark.parametrize("key", SCENARIO_KEYS)
def test_each_variant_carries_exactly_the_blocks_it_runs(key: str) -> None:
    ref, doc = SC, load(key)
    o = doc["outputs"]
    assert (o["lcr"] is not None) == (key == "lcr-standard") and (o["lcr"] is None) == (o["lcr_reason"] is not None)
    assert (o["path"] is not None) == (key != "lcr-standard") and (o["path"] is None) == (o["path_reason"] is not None)
    assert (o["htm"] is not None) == (key == "htm-losses") and (o["htm"] is None) == (o["htm_reason"] is not None)
    assert o["cbc"]["htm_valuation_basis"] == ("fair-value" if key == "htm-losses" else "amortised-cost")
    for mutate in (lambda d: d["outputs"].update(lcr=None, lcr_reason=None) if key == "lcr-standard"
                   else d["outputs"].update(lcr=load("lcr-standard")["outputs"]["lcr"], lcr_reason=None),
                   lambda d: d["outputs"]["cbc"].update(htm_valuation_basis="fair-value" if key != "htm-losses" else "amortised-cost"),
                   lambda d: d["outputs"]["variant"].update(parameter_set="fast-run" if key != "fast-run" else "list-adverse")
                   if key != "htm-losses" else d["outputs"]["variant"].update(id="list-adverse")):
        bad = copy.deepcopy(doc)
        mutate(bad)
        assert errs(ref, bad) != [] or sm.check_document(bad) != []


def test_the_htm_variant_carries_the_loss_the_par_counterfactual_and_the_revaluation_row() -> None:
    h = load("htm-losses")["outputs"]["htm"]
    r = h["reported"]
    assert abs(r["htm_unrealised"] - (r["htm_fair_value"] - r["htm_amortised_cost"])) < 1e-6
    assert r["htm_unrealised"] < 0 and abs(h["cbc_removed"] - (h["cbc_without_loss"] - h["cbc_with_loss"])) < 1e-6
    assert h["btfp_par"]["announced"] == "2023-03-12" and h["btfp_par"]["cbc_at_par"] >= h["cbc_without_loss"]
    assert h["revaluation"]["status"] in ("evaluated", "not_evaluated")
    assert h["revaluation"]["engine_ref"] == "engine-irrbb-api"
    assert any(t["test_id"] == "liq.htm_revaluation_vs_reported" for t in load("htm-losses")["tests"])
    assert sm.check_document(load("htm-losses")) == []


# --- named parameters carry the label "convention" ----------------------------------------------------------------------------


@pytest.mark.parametrize("key", OUT_KEYS + ["models"])
def test_every_named_parameter_is_required_with_its_value_and_the_convention_label(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    conv = doc[root_of(key)]["conventions"]
    assert sorted(conv) == sorted(CONVENTION_NAMES)
    for name in CONVENTION_NAMES:
        assert conv[name]["status"] == "convention", name
        bad = copy.deepcopy(doc)
        del bad[root_of(key)]["conventions"][name]
        assert errs(ref, bad) != [], f"{key}: {name} removed validates"
        no_label = copy.deepcopy(doc)
        del no_label[root_of(key)]["conventions"][name]["status"]
        assert errs(ref, no_label) != [], f"{key}: {name} without its label validates"
        regulatory = copy.deepcopy(doc)
        regulatory[root_of(key)]["conventions"][name]["status"] = "regulatory"
        assert errs(ref, regulatory) != [], f"{key}: {name} labelled regulatory validates"
    for name in CONVENTION_NAMES:
        c = conv[name]
        if "value" in c:
            assert isinstance(c["value"], (int, float)) and c["unit"].strip(), name
        if "values" in c:
            assert len(c["values"]) >= 2 and c["unit"].strip(), name


def test_the_conventions_are_the_same_in_every_document_of_the_bake() -> None:
    first = load("models")["fit"]["conventions"]
    for key in OUT_KEYS:
        assert out(key)["conventions"] == first, key
    assert sm.check_conventions_agree([load(k) for k in ALL]) == []
    bad = [load(k) for k in ALL]
    bad[0]["outputs"]["conventions"]["reverse_target_days"]["value"] = 31
    assert sm.check_conventions_agree(bad) != []


def test_the_proposed_values_follow_the_dossier_examples() -> None:
    c = load("models")["fit"]["conventions"]
    assert c["reverse_target_days"]["value"] == 30 and c["reverse_target_days"]["unit"] == "days"
    assert c["cliff_days"]["near"] == 30 and c["cliff_days"]["far"] == 35
    assert c["event_horizon_days"]["value"] == 2
    assert c["list_compounding_tolerance"]["value"] == 5e-7
    assert c["scoring_ratio_green"]["value"] > c["scoring_ratio_amber"]["value"] > 0
    assert c["generator_truth_se_green"]["value"] < c["generator_truth_se_red"]["value"]
    assert c["htm_revaluation_green"]["value"] < c["htm_revaluation_amber"]["value"]
    assert c["cliff_red_threshold"]["value"] < c["cliff_amber_threshold"]["value"] < 0
    assert c["runoff_multiplier_grid"]["values"][0] == 1.0
    rows = c["variant_scenarios"]["rows"]
    assert [r["variant"] for r in rows] == SCENARIO_KEYS
    m = c["deposit_category_mapping"]
    assert {r["role"] for r in m["rows"]} == {"central"} and {r["role"] for r in m["sensitivity_band"]} == {"band"}
    assert {"operational", "non_financial_corporate", "other_legal_entity"} <= {r["lcr_category"] for r in m["sensitivity_band"]}


# --- call-report field names ----------------------------------------------------------------------------------------------


def test_every_call_report_field_name_is_in_the_addendum_or_in_the_c14_list() -> None:
    schema = cs.load_json(SCHEMAS / "c16" / "variant-scenario.schema.json")
    found: set[str] = set()
    for _, obj in objects(schema["$defs"]):
        if "enum" in obj and set(obj["enum"]) & {"DEPUNA", "SCHA"}:
            found |= set(obj["enum"])
    assert found, "no call-report enum in the schema"
    assert found <= CALL_REPORT_FIELDS, sorted(found - CALL_REPORT_FIELDS)
    assert {"DEPUNA", "DEPINS", "DEPSMAMT", "DEPLGAMT", "SCHA", "SCHF", "SCAA", "SCAF", "SCPLEDGE"} <= found


@pytest.mark.parametrize("key", SCENARIO_KEYS)
def test_a_call_report_field_outside_the_record_fails_and_every_fixture_field_is_in_it(key: str) -> None:
    ref, doc = SC, load(key)
    bs = doc["outputs"]["balance_sheet"]
    used = {i["source_field"] for i in bs["items"]} | {f for r in doc["outputs"]["data"]["call_reports"] for f in r["fields"]}
    used |= {f for c in doc["outputs"]["cbc"]["classes"] for f in c["source_fields"]}
    assert used <= CALL_REPORT_FIELDS
    for mutate in (lambda d: d["outputs"]["balance_sheet"]["items"][0].update(source_field="SCHEDULE_RC_O"),
                   lambda d: d["outputs"]["data"]["call_reports"][0]["fields"].append("RCON2200"),
                   lambda d: d["outputs"]["cbc"]["classes"][0]["source_fields"].append("LCRFIELD")):
        bad = copy.deepcopy(doc)
        mutate(bad)
        assert errs(ref, bad) != []


@pytest.mark.parametrize("key", SCENARIO_KEYS)
def test_a_call_report_item_the_financials_lack_is_null_with_its_reason_and_the_replacing_assumption(key: str) -> None:
    ref, doc = SC, load(key)
    items = doc["outputs"]["balance_sheet"]["items"]
    missing = [i for i in items if i["reported_amount"] is None]
    assert missing, "the fixture exercises a missing item"
    for i in missing:
        assert i["reason_missing"]["en"] and i["assumption"].strip() and i["amount"] >= 0
    for i in items:
        assert (i["reported_amount"] is None) == (i["reason_missing"] is not None)
    both = copy.deepcopy(doc)
    both["outputs"]["balance_sheet"]["items"][items.index(missing[0])]["reason_missing"] = None
    assert errs(ref, both) != []
    deposits = doc["outputs"]["balance_sheet"]["deposits"]
    assert deposits["size_threshold"]["value"] == 250000 and deposits["size_threshold"]["unit"] == "USD"
    assert deposits["denominators"] == {"insured_uninsured": "DEPDOM", "total": "DEP"}


# --- TestResult rows ------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("key", OUT_KEYS)
def test_test_rows_carry_liq_ids_and_a_not_evaluated_row_has_no_number(key: str) -> None:
    ref, doc = ref_of(key), load(key)
    assert doc["tests"], key
    assert all(t["test_id"].startswith("liq.") for t in doc["tests"])
    bad = copy.deepcopy(doc)
    bad["tests"][0]["test_id"] = "irrbb.srp31_92_goldens"
    assert errs(ref, bad) != []
    for t in doc["tests"]:
        if t["light"] == "not_evaluated":
            assert t["statistic"] is None and t["p_value"] is None and t["metric"] is None and t["notes"].strip()
    ne = copy.deepcopy(doc)
    ne["tests"][0].update(light="not_evaluated", statistic=1.0, notes="x")
    assert errs(ref, ne) != []


def test_every_test_id_of_the_engine_contract_appears_in_a_fixture() -> None:
    ids = {t["test_id"] for k in OUT_KEYS for t in load(k)["tests"]}
    assert ids <= {"liq." + n for n in TEST_FUNCTIONS}
    assert len(ids) >= 6


# --- the time block and the reverse stress ------------------------------------------------------------------------------------


@pytest.mark.parametrize("key", SCENARIO_KEYS)
def test_the_time_block_is_the_two_earlier_dates_in_order(key: str) -> None:
    ref, doc = SC, load(key)
    tb = doc["outputs"]["time_block"]
    assert [t["as_of"] for t in tb] == ["2021-12-31", "2022-06-30"]
    assert doc["outputs"]["valuation_date"] == "2022-12-31"
    swapped = copy.deepcopy(doc)
    swapped["outputs"]["time_block"].reverse()
    assert errs(ref, swapped) != []
    for t in tb:
        assert t["htm_unrealised_loss"] <= 0


def test_the_reverse_document_has_the_three_bases_the_curve_the_cap_and_a_round_trip() -> None:
    doc = load("reverse")
    o = doc["outputs"]
    assert [b["base_id"] for b in o["bases"]] == ["list-adverse", "list-extreme", "fast-run"]
    assert o["target"]["days"] == o["conventions"]["reverse_target_days"]["value"] == 30
    assert o["cap_rule"]["each_rate_below_one"] is True
    for b in o["bases"]:
        ms = [p["multiplier"] for p in b["curve"]]
        assert ms == sorted(ms) and ms[0] == 1.0 and ms[-1] <= b["max_multiplier"] + 1e-12
        assert b["solved"]["status"] in ("solved", "refused")
    assert {b["solved"]["status"] for b in o["bases"]} == {"solved", "refused"}
    assert sm.check_document(doc) == []
    bad = copy.deepcopy(doc)
    solved = next(b for b in bad["outputs"]["bases"] if b["solved"]["status"] == "solved")
    solved["solved"]["survival_at_multiplier"] = 99
    assert any("round trip" in m or "survival_at_multiplier" in m for m in sm.check_document(bad))
    nonmono = copy.deepcopy(doc)
    nonmono["outputs"]["bases"][0]["curve"][-1]["survival"] = {"kind": "survives-horizon", "day": None, "horizon_days": 125}
    assert any("monotone" in m for m in sm.check_document(nonmono))


# --- the models document -------------------------------------------------------------------------------------------------------


def test_the_models_carry_the_transcribed_list_tables_the_table_a1_rows_and_the_split() -> None:
    fit = load("models")["fit"]
    lp = fit["list_parameters"]
    assert [(r["item"], r["baseline"], r["adverse"], r["extreme"]) for r in lp["contractual_outflows"]] == LIST_CONTRACTUAL
    assert [(r["item"], r["baseline"], r["adverse"], r["extreme"]) for r in lp["open_maturity_daily"]] == LIST_OPEN
    assert [(r["item"], r["baseline"], r["adverse"], r["extreme"]) for r in lp["contractual_inflows"]] == LIST_INFLOWS
    assert [(r["item"], r["adverse"], r["extreme"]) for r in lp["committed_drawdown"]] == LIST_DRAWDOWN
    assert lp["relevant_days_six_months"] == 125 and lp["relevant_days_three_months"] == 63
    assert [(r["row_id"], r["bank"], r["year"], r["outflow_share"], r["days"]) for r in fit["table_a1"]["rows"]] == TABLE_A1
    assert fit["table_a1"]["lcr_range"] == {"label": "LCR deposit outflow rates", "low": 0.03, "high": 0.40, "days": 30}
    cal = fit["calibration"]
    assert [r["row_id"] for r in cal["implied_daily_rates"]] == ["icesave-2008", "northern-rock-2007", "wamu-2008", "indymac-2008"]
    for r in cal["implied_daily_rates"]:
        assert abs(r["implied_daily_rate"] - IMPLIED[r["row_id"]]) < 5e-7
    assert cal["split"]["calibrated_on"] == ["icesave-2008", "northern-rock-2007", "wamu-2008", "indymac-2008"]
    assert cal["split"]["scored_on"] == ["svb-2023", "first-republic-2023", "svb-uk-2023", "credit-suisse-2023", "signature-2023"]
    assert cal["fitted_daily_rate"]["source_kind"] == "calibrated-pre-2023"
    assert sm.check_document(load("models")) == []


def test_the_list_goldens_of_the_models_recompute_and_the_table_values_are_the_dossier_ones() -> None:
    fit = load("models")["fit"]
    by_id = {g["id"]: g for g in fit["list_goldens"]}
    assert abs(by_id["stable-retail-adverse"]["cumulative_outflow"] - 0.121148) < 5e-7
    assert abs(by_id["stable-retail-extreme"]["cumulative_outflow"] - 0.182930) < 5e-7
    for g in fit["list_goldens"]:
        assert abs(g["cumulative_outflow"] - (1 - (1 - g["daily_rate"]) ** g["days"])) < 5e-7, g["id"]
    bad = load("models")
    bad["fit"]["list_goldens"][0]["cumulative_outflow"] = 0.5
    assert any("golden" in m for m in sm.check_document(bad))
    assert 1 - (1 - 0.00103258) ** 125 == pytest.approx(0.121148, abs=5e-7)


def test_a_transcribed_list_or_table_a1_value_that_differs_fails() -> None:
    doc = load("models")
    for mutate in (lambda d: d["fit"]["list_parameters"]["open_maturity_daily"][1].update(adverse=0.001),
                   lambda d: d["fit"]["list_parameters"]["contractual_outflows"][7].update(extreme=0.75),
                   lambda d: d["fit"]["table_a1"]["rows"][0].update(outflow_share=0.8),
                   lambda d: d["fit"]["table_a1"]["rows"][5].update(days=74),
                   lambda d: d["fit"]["list_parameters"].update(relevant_days_six_months=126)):
        bad = copy.deepcopy(doc)
        mutate(bad)
        assert errs(MD, bad) != []


def test_the_generator_truth_and_its_verification_are_stated() -> None:
    g = load("models")["fit"]["generator"]
    assert g["config"]["truth_status"] == "synthetic-known-truth" and g["config"]["seed"] >= 0
    assert abs(sum(s["share_of_deposits"] for s in g["config"]["segments"]) - 1.0) < 1e-9
    assert g["truth"] and g["verification"]["within_error"] is True
    assert g["verification"]["max_abs_error"] <= 3 * g["verification"]["mc_standard_error"] + 1e-12


def test_every_source_carries_its_licence_class_and_the_reading_is_not_legal_advice() -> None:
    srcs = load("models")["fit"]["sources"]
    ids = {s["source_id"] for s in srcs}
    assert {"fdic-bankfind", "fed-h8", "fed-svb-review", "bcbs-d555-table-a1", "ecb-list-2019"} <= ids
    by = {s["source_id"]: s for s in srcs}
    assert by["bcbs-d555-table-a1"]["licence_class"] == "mirror-allowed" and by["ecb-list-2019"]["licence_class"] == "mirror-allowed"
    for s in srcs:
        assert s["licence_class"] in ("mirror-allowed", "derived-only", "link-only", "unusable")
        assert "not legal advice" in s["statement"]["en"]


# --- the semantic checker --------------------------------------------------------------------------------------------------------


def all_documents() -> list[Path]:
    paths = [p for _, p in FILES.values()]
    base = ROOT / "data" / "derived" / "C16"
    return paths + (sorted(base.glob("*.json")) if base.is_dir() else [])


@pytest.mark.parametrize("path", all_documents(), ids=lambda p: p.name)
def test_the_semantic_checker_is_clean_on_every_committed_c16_document(path: Path) -> None:
    doc = cs.load_json(path)
    if doc.get("case_id") == "C16":
        assert sm.check_document(doc) == []


def test_the_checker_is_an_importable_function_a_bake_calls() -> None:
    for name in ("check_document", "check_scenario", "check_reverse", "check_models", "check_conventions_agree"):
        assert callable(getattr(sm, name)), name
    assert sm.check_document({"case_id": "C16", "outputs": {"kind": "unknown"}}) != []


def _plants() -> list[tuple[str, str, Callable[[dict], None]]]:
    plants: list[tuple[str, str, Callable[[dict], None]]] = []
    for key in PATH_KEYS:
        plants += [
            (f"{key}: a cbc total that is not the stack sum", key, lambda d: d["outputs"]["path"]["ladder"]["cbc_total"].__setitem__(3, 1.0)),
            (f"{key}: an nlp that breaks the identity", key, lambda d: d["outputs"]["path"]["ladder"]["nlp"].__setitem__(0, 7.0)),
            (f"{key}: a cumulative net outflow that is not the running sum", key,
             lambda d: d["outputs"]["path"]["ladder"]["cumulative_net_outflow"].__setitem__(1, -1.0)),
            (f"{key}: total outflows that are not the sum", key, lambda d: d["outputs"]["path"]["ladder"]["total_outflows"].__setitem__(0, 1.0)),
            (f"{key}: a segment cumulative that is not 1 - prod(1 - q)", key,
             lambda d: d["outputs"]["path"]["ladder"]["segments"][0]["cumulative_outflow_share"].__setitem__(1, 0.9)),
            (f"{key}: a ladder shorter than the horizon", key, lambda d: d["outputs"]["path"]["ladder"]["nlp"].pop()),
            (f"{key}: a minimum nlp that is not the minimum", key, lambda d: d["outputs"]["path"]["minimum_nlp"].update(value=-1.0)),
            (f"{key}: an impact survival that disagrees", key, lambda d: d["impact"]["survival_days"].update(value=3)),
            (f"{key}: a modelled share that is not the ladder's", key,
             lambda d: d["outputs"]["scoring"]["denominators"][0].update(modelled_share=0.9999)),
            (f"{key}: a conventions block that differs from the variant mapping", key,
             lambda d: d["outputs"]["variant"].update(horizon_days=d["outputs"]["variant"]["horizon_days"] + 1)),
        ]
    plants += [
        ("htm: a cbc removed that is not the difference", "htm-losses", lambda d: d["outputs"]["htm"].update(cbc_removed=1.0)),
        ("htm: a cbc class liquidity value that breaks the haircut", "htm-losses",
         lambda d: d["outputs"]["cbc"]["classes"][2].update(liquidity_value=1.0)),
        ("htm: a cbc total that is not the class sum", "htm-losses", lambda d: d["outputs"]["cbc"].update(total_liquidity_value=1.0)),
        ("lcr: outflow rows that do not sum", "lcr-standard", lambda d: d["outputs"]["lcr"].update(total_outflows=1.0)),
        ("lcr: a net outflow that is not outflows minus counted inflows", "lcr-standard",
         lambda d: d["outputs"]["lcr"].update(net_outflows=1.0)),
        ("lcr: a hqla that is not l1 + l2a + l2b - adjustments", "lcr-standard", lambda d: d["outputs"]["lcr"]["hqla"].update(hqla=1.0)),
        ("scoring: a realised share that is not the amount over the denominator", "list-adverse",
         lambda d: d["outputs"]["scoring"]["denominators"][1].update(realised_share=0.5)),
        ("scoring: a ratio that is not modelled over realised", "list-adverse",
         lambda d: d["outputs"]["scoring"]["denominators"][1].update(ratio=3.0)),
        ("scoring: a light that breaks the convention", "list-adverse",
         lambda d: d["outputs"]["scoring"]["denominators"][1].update(light="green")),
        ("scoring: an anchor claiming a forecast", "list-adverse", lambda d: d["outputs"]["scoring"]["svb_anchor"].update(forecast_claim=True)),
        ("scoring: an anchor rate that is not implied", "list-adverse", lambda d: d["outputs"]["scoring"]["svb_anchor"].update(implied_daily_rate=0.5)),
        ("deposits: an uninsured share that is not DEPUNA over DEPDOM", "list-adverse",
         lambda d: d["outputs"]["balance_sheet"]["deposits"].update(uninsured_share_of_depdom=0.5)),
        ("deposits: segments that are not the mapped balances", "list-adverse",
         lambda d: d["outputs"]["path"]["ladder"]["segments"][0].update(opening_balance=1.0)),
        ("data: a report dated after the valuation date", "list-adverse",
         lambda d: d["outputs"]["data"]["call_reports"][-1].update(report_date="2023-03-31")),
        ("data: a false dating flag", "list-adverse", lambda d: d["outputs"]["data"].update(read_up_to_valuation_date=False)),
        ("reverse: a solved multiplier beyond its cap", "reverse", lambda d: d["outputs"]["bases"][0]["solved"].update(multiplier=1e6)),
        ("reverse: a cap flag that is false", "reverse", lambda d: d["outputs"]["cap_rule"].update(each_rate_below_one=False)),
        ("reverse: a target that differs from the convention", "reverse", lambda d: d["outputs"]["target"].update(days=31)),
        ("reverse: a refusal without its reason", "reverse",
         lambda d: next(b for b in d["outputs"]["bases"] if b["solved"]["status"] == "refused")["solved"].update(refusal_reason=None)),
        ("models: a calibration rate that is not implied", "models", lambda d: d["fit"]["calibration"]["implied_daily_rates"][0].update(implied_daily_rate=0.5)),
        ("models: a fitted rate that is not the rule's", "models", lambda d: d["fit"]["calibration"]["fitted_daily_rate"].update(value=0.5)),
        ("models: generator shares that do not sum to one", "models", lambda d: d["fit"]["generator"]["config"]["segments"][0].update(share_of_deposits=0.9)),
    ]
    return plants


PLANTS = _plants()


def test_the_plant_table_has_no_duplicate_names_per_document_and_is_large() -> None:
    names = [(n, k) for n, k, _ in PLANTS]
    assert len(names) == len(set(names)) and len(names) >= 45


@pytest.mark.parametrize("name,key,mutate", PLANTS, ids=[f"{k}:{n}" for n, k, _ in PLANTS])
def test_a_planted_defect_is_refused_by_the_schema_or_the_checker(name: str, key: str, mutate: Callable[[dict], None]) -> None:
    doc = load(key)
    bad = copy.deepcopy(doc)
    mutate(bad)
    assert bad != doc
    assert errs(ref_of(key), bad) != [] or sm.check_document(bad) != [], name


@pytest.mark.parametrize("key", PATH_KEYS)
def test_the_ladder_identities_hold_in_every_fixture_and_the_cliff_is_null_with_its_reason_when_the_horizon_is_short(key: str) -> None:
    p = load(key)["outputs"]["path"]
    lad = p["ladder"]
    h = len(lad["day_index"])
    assert lad["day_index"] == list(range(1, h + 1)) and len(lad["dates"]) == h
    running = 0.0
    for d in range(h):
        running += lad["total_outflows"][d] - lad["total_inflows"][d]
        assert math.isclose(lad["cumulative_net_outflow"][d], running, abs_tol=1e-3)
        assert math.isclose(lad["nlp"][d], lad["cbc_total"][d] - running, abs_tol=1e-3)
    if h < 35:
        assert p["cliff"] is None and p["cliff_reason"]["en"]
    else:
        c = p["cliff"]
        assert math.isclose(c["value"], (lad["nlp"][34] - lad["nlp"][29]) / c["total_assets"], abs_tol=1e-9)
        assert p["cliff_reason"] is None


# --- the balance_sheet family bump ---------------------------------------------------------------------------------------------


OLD_FIELDS = ["as_of", "item", "currency", "amount", "repricing_bucket", "behavioural_class", "core_share", "core_avg_maturity_years"]
NEW_FIELDS = {"liquidity_class": "enum", "residual_days": "int", "insured": "flag", "fair_value": "float"}


def test_the_balance_sheet_family_gained_four_optional_liquidity_fields_and_kept_the_old_ones() -> None:
    from pipeline.io import contract as c

    fam = c.FAMILIES["balance_sheet"]
    names = [f.name for f in fam.fields]
    assert names[:len(OLD_FIELDS)] == OLD_FIELDS
    assert names[len(OLD_FIELDS):] == list(NEW_FIELDS)
    for f in fam.fields[len(OLD_FIELDS):]:
        assert f.kind == NEW_FIELDS[f.name] and f.required is False
    assert [f.required for f in fam.fields[:6]] == [True] * 6
    assert fam.field("liquidity_class").values == ("level_1", "level_2a", "level_2b", "non_hqla")
    assert fam.field("residual_days").lo == 0.0 and fam.field("fair_value").unit == "currency"
    assert fam.field("residual_days").unit == "days"


def test_a_c14_and_a_c15_balance_sheet_dataset_still_validates_unchanged_and_a_liquidity_row_validates() -> None:
    from pipeline.io import contract as c

    c14 = [{"as_of": "2022-12-31", "item": "Transactional deposits", "currency": "USD", "amount": -5.0e9, "repricing_bucket": "ON",
            "behavioural_class": "nmd_retail_transactional", "core_share": 0.9, "core_avg_maturity_years": 4.0},
           {"as_of": "2022-12-31", "item": "Securities HTM", "currency": "USD", "amount": 2.0e9, "repricing_bucket": "5Y-6Y",
            "behavioural_class": "contractual"}]
    c15 = [{"as_of": "2024-06-30", "item": "Mortgage UF", "currency": "CLF", "amount": 1.0e6, "repricing_bucket": "20Y+",
            "behavioural_class": "prepayable_fixed_rate_loan"},
           {"as_of": "2024-06-30", "item": "Time deposits", "currency": "CLP", "amount": -2.0e9, "repricing_bucket": "3M-6M",
            "behavioural_class": "redeemable_term_deposit"}]
    for rows in (c14, c15):
        rep = c.validate("balance_sheet", rows)
        assert len(rep.accepted) == len(rows) and not rep.rejected and not rep.flagged
    liq = [{**c14[1], "liquidity_class": "level_1", "residual_days": 90, "insured": 0, "fair_value": 1.9e9},
           {**c14[0], "liquidity_class": "non_hqla", "residual_days": 0, "insured": 1, "fair_value": -5.0e9}]
    rep = c.validate("balance_sheet", liq)
    assert len(rep.accepted) == 2 and not rep.rejected
    bad = c.validate("balance_sheet", [{**c14[1], "liquidity_class": "level_3"}, {**c14[1], "residual_days": -1},
                                       {**c14[1], "insured": 2}, {**c14[1], "fair_value": "n/a"}])
    assert len(bad.rejected) == 4 and not bad.accepted


def test_the_exported_balance_sheet_declaration_is_regenerated_from_the_family_and_still_valid() -> None:
    from pipeline.io import contract as c

    path = ROOT / "data" / "derived" / "contract" / "balance_sheet.json"
    on_disk = cs.load_json(path)
    assert on_disk == json.loads(json.dumps(c.FAMILIES["balance_sheet"].to_json()))
    assert errs("common/contract-family", on_disk) == []
    assert [f["name"] for f in on_disk["fields"]][-4:] == list(NEW_FIELDS)
    assert all(f["required"] is False for f in on_disk["fields"][-4:])
    assert (ROOT / "data" / "derived" / "contract" / "index.json").is_file()


def test_the_other_families_are_untouched_by_the_bump() -> None:
    for name in ("curve", "loan_panel", "loss_events", "macro_path", "market_series", "rating_history", "scored_sample"):
        on_disk = cs.load_json(ROOT / "data" / "derived" / "contract" / f"{name}.json")
        assert on_disk["family"] == name
    from pipeline.io import contract as c

    for name, fam in c.FAMILIES.items():
        assert cs.load_json(ROOT / "data" / "derived" / "contract" / f"{name}.json") == json.loads(json.dumps(fam.to_json())), name


# --- the rows fragment and the changelog fragment -----------------------------------------------------------------------------


def row_cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def fragment_rows() -> dict[str, list[str]]:
    # merged at the batch 3 integration (task/0-13-000-wave2, 2026-10-19): the fragment is gone and the rows live in
    # the catalog's Contracts table; read the fragment while it exists, the catalog after
    if ROWS.is_file():
        text = ROWS.read_text(encoding="utf-8")
    else:
        catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
        text = catalog.split("## Contracts", 1)[1].split("\n## ", 1)[0]
    header = next(ln for ln in text.splitlines() if ln.startswith("| id | version"))
    assert row_cells(header) == ["id", "version", "owner", "schema file", "example", "producer test", "consumer test",
                                 "missing-data behavior", "provider", "model io", "swap test", "status"]
    lines = text.splitlines()
    table = []
    for ln in lines[lines.index(header) + 2:]:
        if not ln.startswith("|"):
            break
        table.append(ln)
    return {row_cells(ln)[0]: row_cells(ln) for ln in table if row_cells(ln)[0] in ROW_IDS}


def test_the_rows_fragment_has_the_four_rows_in_the_catalog_columns_and_every_cited_test_exists() -> None:
    rows = fragment_rows()
    assert sorted(rows) == sorted(ROW_IDS)
    me = Path(__file__).read_text(encoding="utf-8")
    for rid, cells in rows.items():
        # engine-liquidity-api 1.1.0 after U11-E (additive: the `scored` keyword of fast_run_scenario), at the batch 3 integration
        assert cells[1] == {"engine-liquidity-api": "1.2.0", "c16-outputs-reverse": "1.0.1", "c16-outputs": "2.1.0"}.get(rid, "1.0.0") and cells[11] == ("active" if rid.startswith("engine-") else "real")  # the case rows are real since C16 merged
        assert cells[8].startswith("fixture:docs/contracts/fixtures/c16/") or cells[8].startswith("fixture:docs/contracts/engine/")
        for cell in (cells[5], cells[6], cells[10]):
            for ref in cell.split(", "):
                path, _, name = ref.partition("::")
                assert (ROOT / path).is_file(), (rid, ref)
                if path.endswith("test_u11_contracts.py"):
                    assert f"def {name}(" in me, (rid, ref)
        assert ("U11-S" in cells[2]) if rid.startswith("engine-") else cells[2] == "data-pipeline/pipeline/cases/c16/"
    assert rows["c16-outputs"][3] == "docs/contracts/schemas/c16/variant-scenario.schema.json"
    assert rows["c16-outputs-reverse"][3] == "docs/contracts/schemas/c16/variant-reverse.schema.json"
    assert rows["c16-models"][3] == "docs/contracts/schemas/c16/models.schema.json"
    assert rows["engine-liquidity-api"][3] == "docs/contracts/engine/liquidity-api.md"
    for rid in ("c16-outputs", "c16-outputs-reverse", "c16-models"):
        assert (ROOT / rows[rid][4]).is_file()


def test_the_rows_fragment_carries_no_row_already_in_the_catalog_and_names_the_family_bump_for_the_integrator() -> None:
    catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
    if ROWS.is_file():
        existing = {row_cells(ln)[0] for ln in catalog.splitlines() if ln.startswith("| ")}
        for rid in ROW_IDS:
            assert rid not in existing, rid
        text = ROWS.read_text(encoding="utf-8")
        assert "contract-family" in text and "1.1.0" in text and "integrator" in text
    else:
        # merged at the batch 3 integration: each row is in the Contracts table exactly once, and the integrator moved
        # the contract-family row (at least 1.1.0, the balance_sheet bump) and recorded it in History
        contracts = catalog.split("## Contracts", 1)[1].split("\n## ", 1)[0]
        ids = [ln.split("|")[1].strip() for ln in contracts.splitlines() if ln.startswith("| ")]
        assert all(ids.count(i) == 1 for i in ROW_IDS), [i for i in ROW_IDS if ids.count(i) != 1]
        family = next(row_cells(ln) for ln in contracts.splitlines() if ln.startswith("| contract-family |"))
        assert tuple(int(x) for x in family[1].split(".")) >= (1, 1, 0), family[1]
        assert "| contract-family | 1.1.0 |" in catalog
    assert "missing" in fragment_rows()["c16-outputs"][7] or "partial" in fragment_rows()["c16-outputs"][7]


def test_the_changelog_fragment_holds_bullet_lines_only_and_names_the_bump() -> None:
    text = released_fragment(CHANGES)
    if CHANGES.is_file():  # the format rule binds the fragment; after the release its bullets sit in the CHANGELOG entry
        lines = [ln for ln in text.splitlines() if ln.strip()]
        assert lines and lines[0].startswith("- ")
        for ln in lines:
            assert ln.startswith("- ") or ln.startswith("  "), ln
            assert not ln.startswith("#")
    for needle in ("c16-outputs", "c16-models", "engine-liquidity-api", "contract-family", "balance_sheet", "liquidity_class"):
        assert needle in text, needle
    assert chr(0x2014) not in text and chr(0x2192) not in text


# --- the engine liquidity API contract ---------------------------------------------------------------------------------------------

MODULES = {
    "liquidity._checks": ["check_nonnegative_stock", "check_unit_share", "check_weights_sum_to_one", "check_increasing_grid"],
    "liquidity.runoff": ["cumulative_outflow_constant", "cumulative_outflow_path", "daily_rate_from_cumulative",
                         "contractual_rolloff", "financial_no_rollover"],
    "liquidity.cbc": ["haircut_rule", "liquidity_value", "monetisation_capacity", "cbc_stack", "cbc_with_htm_loss"],
    "liquidity.ladder": ["contractual_gaps", "behavioural_outflows", "net_liquidity_position", "survival_period", "minimum_nlp",
                         "cliff_effect"],
    "liquidity.scenarios": ["list_scenario", "compose_scenario", "fast_run_scenario", "anchor_from_observation",
                            "uninsured_share_grid", "htm_loss_grid"],
    "liquidity.reverse": ["survival_vs_multiplier", "solve_multiplier"],
    "liquidity.deposits": ["DepositorConfig", "DepositorGenerator"],
    "regulatory.lcr_nsfr": ["hqla_stock", "lcr_outflows", "lcr_inflows", "net_cash_outflows", "lcr_ratio", "nsfr_asf", "nsfr_rsf",
                            "nsfr_ratio"],
    "validation.liquidity": ["list_compounding_golden", "survival_monotone_in_severity", "cbc_haircut_rules", "nlp_identity",
                             "runoff_adequacy_back_test", "runoff_vs_generator_truth", "cliff_effect_diagnostic", "htm_loss_effect",
                             "uninsured_share_sensitivity", "reverse_stress_round_trip", "htm_revaluation_vs_reported"],
}
TEST_FUNCTIONS = MODULES["validation.liquidity"]
FILE_OF = {"liquidity._checks": "liquidity/_checks.py", "liquidity.runoff": "liquidity/runoff.py", "liquidity.cbc": "liquidity/cbc.py",
           "liquidity.ladder": "liquidity/ladder.py", "liquidity.scenarios": "liquidity/scenarios.py",
           "liquidity.reverse": "liquidity/reverse.py", "liquidity.deposits": "liquidity/deposits.py",
           "regulatory.lcr_nsfr": "regulatory/lcr_nsfr.py", "validation.liquidity": "validation/liquidity.py"}


def key_of(module: str, name: str) -> str:
    return f"riskvalidation.{module}.{name}"


def api_sections() -> dict[str, str]:
    text = API.read_text(encoding="utf-8")
    parts = re.split(r"^### `([^`]+)`\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


def section(module: str, name: str) -> str:
    return api_sections()[key_of(module, name)]


def test_the_engine_contract_exists_with_its_version() -> None:
    text = API.read_text(encoding="utf-8")
    assert "engine-liquidity-api" in text and "1.0.0" in text
    assert "common/test-result" in text and "TestResult" in text


def test_the_engine_contract_covers_every_module_of_the_sizing_table_lcr_nsfr_included() -> None:
    text = API.read_text(encoding="utf-8")
    for module in ("liquidity/_checks.py", "liquidity/runoff.py", "liquidity/cbc.py", "liquidity/ladder.py", "liquidity/scenarios.py",
                   "liquidity/reverse.py", "liquidity/deposits.py", "regulatory/lcr_nsfr.py", "validation/liquidity.py"):
        assert f"## Module `riskvalidation/{module}`" in text, module
    assert set(FILE_OF.values()) == {m for m in re.findall(r"## Module `riskvalidation/([^`]+)`", text)}


@pytest.mark.parametrize("module", MODULES)
def test_every_function_has_a_signature_units_and_a_golden_value_or_an_invariant(module: str) -> None:
    for name in MODULES[module]:
        body = section(module, name)
        assert "```python" in body, name
        assert re.search(r"^- (Golden|Invariants):", body, flags=re.M), f"{name}: no golden value or invariant"
        assert re.search(r"^- Units:", body, flags=re.M), f"{name}: no units line"


def test_every_validation_function_has_a_light_rule_a_test_id_and_a_golden() -> None:
    for name in TEST_FUNCTIONS:
        body = section("validation.liquidity", name)
        assert "-> TestResult" in body, name
        assert re.search(r"^- Light:", body, flags=re.M), name
        assert re.search(r"^- Golden:", body, flags=re.M), name
        assert f'test_id = "liq.{name}"' in body, name


def test_the_engine_contract_has_no_function_outside_the_table() -> None:
    declared = {key_of(m, n) for m, names in MODULES.items() for n in names}
    assert set(api_sections()) == declared


def test_the_engine_contract_carries_the_dossier_goldens_labelled() -> None:
    text = API.read_text(encoding="utf-8")
    for golden in ("0.121148", "0.00103258", "0.182930", "0.612702", "0.009334", "0.054258", "0.002971", "0.010481", "0.005938",
                   "0.002616", "15/85", "two-thirds", "0.75", "0.40"):
        assert golden in text, golden
    assert "recomputed" in text and "(05 line 237)" in text
    for cell in ("LCR30.38", "LCR30.39", "LCR40.1", "LCR20.4", "NSF20.2", "LCR30.43", "LCR30.45", "SRP50", "LCR99", "NSF99"):
        assert cell in text, cell
    assert "No official LCR or NSFR worked example" in text and "UNVERIFIED" in text
    for test_id in TEST_FUNCTIONS:
        assert f"liq.{test_id}" in text, test_id
    for name in ("LIST_PARAMETERS", "TABLE_A1", "LCR_OUTFLOW_RATES", "LCR_INFLOW_RATES", "NSFR_ASF_FACTORS", "NSFR_RSF_FACTORS"):
        assert name in text, name


def test_the_lcr_and_nsfr_rate_tables_of_the_contract_are_the_dossier_ones() -> None:
    text = API.read_text(encoding="utf-8")
    for row in ("| retail_stable | 0.05 |", "| retail_less_stable | 0.10 |", "| operational | 0.25 |", "| non_financial_corporate | 0.40 |",
                "| other_legal_entity | 1.00 |", "| secured_level2a | 0.15 |", "| undrawn_liquidity_other_fi | 1.00 |",
                "| level_2a | 0.15 |", "| level_2b_rmbs | 0.25 |", "| stable_retail_deposits | 0.95 |",
                "| less_stable_retail_deposits | 0.90 |", "| unencumbered_level_2b | 0.50 |", "| other_assets | 1.00 |"):
        assert row in text, row


def test_every_contract_function_of_the_sizing_is_named_by_its_own_module_and_the_liquidity_data_is_listed() -> None:
    text = API.read_text(encoding="utf-8")
    assert "riskvalidation/liquidity/_checks.py" in text
    for fn in ("anchor_from_observation", "solve_multiplier", "DepositorGenerator"):
        assert fn in text


# --- the goldens recompute --------------------------------------------------------------------------------------------------------


def F(q: float, n: int) -> float:
    return 1 - (1 - q) ** n


def test_golden_list_compounding_values_recompute() -> None:
    assert F(0.00103258, 125) == pytest.approx(0.121148, abs=5e-7)
    assert F(0.00161494, 125) == pytest.approx(0.182930, abs=5e-7)
    adverse = {name: adv for name, _, adv, _ in LIST_OPEN}
    assert F(adverse["other-retail"], 125) == pytest.approx(0.373368, abs=5e-7)
    assert F(adverse["non-operational-non-financial-corporates"], 2) == pytest.approx(0.013723, abs=5e-7)
    assert F(0.00202704, 63) == pytest.approx(0.12, abs=5e-7) and F(0.02176434, 63) == pytest.approx(0.75, abs=5e-7)


def test_golden_table_a1_implied_daily_rates_recompute() -> None:
    for row_id, _, _, share, days in TABLE_A1:
        assert 1 - (1 - share) ** (1 / days) == pytest.approx(IMPLIED[row_id], abs=5e-7), row_id
    assert 0.85 == pytest.approx(F(IMPLIED["svb-2023"], 2), abs=1e-6)


def test_golden_lcr_cap_formulas_on_a_constructed_balance_sheet() -> None:
    l1, l2a, l2b = 100.0, 20.0, 30.0
    adj15 = max(l2b - 15 / 85 * (l1 + l2a), l2b - 15 / 60 * l1, 0.0)
    adj40 = max(l2a + l2b - adj15 - 2 / 3 * l1, 0.0)
    hqla = l1 + l2a + l2b - adj15 - adj40
    assert adj15 == pytest.approx(8.823529, abs=5e-7) and adj40 == 0.0
    assert (l2b - adj15) / hqla == pytest.approx(0.15, abs=1e-12)
    # inflows never offset more than 75 percent of outflows; a level 1 plus stable retail balance sheet has a closed form
    out, inflow = 100.0, 90.0
    assert out - min(inflow, 0.75 * out) == 25.0
    assert 100.0 / (0.05 * 1000.0) == 2.0


def test_the_engine_contract_goldens_of_the_hand_ladder_recompute() -> None:
    cbc, outs, ins = [100.0, 100.0, 100.0, 100.0], [30.0, 40.0, 50.0, 60.0], [0.0, 10.0, 0.0, 0.0]
    nlp, running = [], 0.0
    for c, o, i in zip(cbc, outs, ins):
        running += o - i
        nlp.append(c - running)
    assert nlp == [70.0, 40.0, -10.0, -70.0]
    first = next(d + 1 for d, v in enumerate(nlp) if v < 0)
    assert first == 3
    text = API.read_text(encoding="utf-8")
    assert "[70.0, 40.0, -10.0, -70.0]" in text


# --- the production-path helper --------------------------------------------------------------------------------------------------

def test_the_build_scripts_regenerate_the_committed_schemas_and_fixtures_byte_for_byte(tmp_path: Path) -> None:
    here = Path(__file__).resolve().parent
    before = {p: p.read_bytes() for p in list((SCHEMAS / "c16").glob("*.json")) + list((FIXTURES / "c16").glob("*.json"))}
    assert before
    for script in ("build_schemas.py", "build_fixtures.py"):
        done = subprocess.run([sys.executable, str(here / script)], capture_output=True, text=True, cwd=str(ROOT), check=False,
                              env={**os.environ, "PYTHONUTF8": "1"})
        assert done.returncode == 0, done.stderr
    after = {p: p.read_bytes() for p in before}
    assert after == before
