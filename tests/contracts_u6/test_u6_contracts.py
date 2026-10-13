"""U6-S: the C03, C08 and C09 case contracts, their fixtures, the catalog rows and the engine LGD and EAD API contract.

The fixtures validate by discovery (tests/contracts/contract_schemas.py) against exactly one schema; the schemas are
strict both ways (a removed or an added key fails); a PD of 0 or 1 fails at a C03 estimate site; an LGD (C08) or a CCF
(C09) outside [0, 1] passes only with its flag and a flag on an in-range value fails; a money block without its
currency fails; the C08 documents carry the LGD proxy definition and bias statement; the engine contract names every
function of the modules table of plans/contraste/units/U6-sizing.md with a golden value or an invariant and its golden
values recompute here from the formulas of dossier 04 sections F and G. The fixtures are labelled as fixtures and never
published as results.
"""
from __future__ import annotations

import copy
import math
import re
from statistics import NormalDist
from typing import Any, Iterator

import pytest

import contract_schemas as cs

ROOT = cs.ROOT
FIXTURES = ROOT / "docs" / "contracts" / "fixtures"
SCHEMAS = ROOT / "docs" / "contracts" / "schemas"
API = ROOT / "docs" / "contracts" / "engine" / "lgd-ead-api.md"
ROWS = ROOT / "docs" / "contracts" / "rows" / "U6.md"

ROW_IDS = ["c03-outputs", "c03-models", "c08-outputs", "c08-models", "c09-outputs", "c09-models", "engine-lgd-ead-api"]


def catalog_rows(ids):
    """The catalog rows of these contract ids, header first (the unit's rows fragment was merged by the integrator)."""
    catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
    lines = catalog.split("## Contracts", 1)[1].split("\n## ", 1)[0].splitlines()
    head = [ln for ln in lines if ln.startswith("| id | version")]
    return head + ["|---|"] + [ln for ln in lines if ln.startswith("| ") and ln.split("|")[1].strip() in ids]

EXPECTED = {
    "c03/models": FIXTURES / "c03" / "models-fixture.json",
    "c03/variant-vintage-cohort": FIXTURES / "c03" / "variant-vintage-cohort-fixture.json",
    "c08/models": FIXTURES / "c08" / "models-fixture.json",
    "c08/variant-default-cohort": FIXTURES / "c08" / "variant-default-cohort-fixture.json",
    "c09/models": FIXTURES / "c09" / "models-fixture.json",
    "c09/variant-acceleration-level": FIXTURES / "c09" / "variant-acceleration-level-fixture.json",
}
VARIANTS = {k: v for k, v in EXPECTED.items() if "variant" in k}
KINDS = {"c03/variant-vintage-cohort": "vintage-cohort", "c08/variant-default-cohort": "default-cohort",
         "c09/variant-acceleration-level": "acceleration-level"}
C03, C08, C09 = "c03/variant-vintage-cohort", "c08/variant-default-cohort", "c09/variant-acceleration-level"
C03M, C08M, C09M = "c03/models", "c08/models", "c09/models"


def load(ref: str) -> Any:
    return cs.load_json(EXPECTED[ref])


def out(ref: str) -> dict:
    return load(ref)["outputs"]


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
    assert doc["provenance"]["generators"] == ["fixture:u6-s-contracts"]
    assert any(i["source"] == "fixture-not-a-result" for i in doc["provenance"]["inputs"])
    key = "variant_id" if "variant" in ref else "fit_id"
    assert str(doc[key]).startswith("fixture-")


def test_every_u6_schema_is_case_folder_conformant_and_case_prefixed() -> None:
    assert cs.case_folder_violations() == []
    files = sorted(p for case in ("c03", "c08", "c09") for p in (SCHEMAS / case).glob("*.schema.json"))
    assert {p.relative_to(SCHEMAS).as_posix() for p in files} == {f"{ref}.schema.json" for ref in EXPECTED}
    for p in files:
        case = p.parent.name
        for name in cs.load_json(p).get("$defs", {}):
            assert name.startswith(case), f"{p.name}: $defs name {name!r} is not prefixed {case!r}"


def test_every_u6_variant_schema_declares_its_outputs_kind() -> None:
    by_ref = {c.ref: c for c in cs.candidates()}
    for ref, kind in KINDS.items():
        assert by_ref[ref].consts["outputs.kind"] == kind
    for case in ("C03", "C08", "C09"):
        assert cs.default_variants().get(case) is None
    assert cs.default_violations() == []


@pytest.mark.parametrize("case", ["C03", "C08", "C09"])
def test_a_second_kind_less_variant_schema_fails(case: str) -> None:
    a = cs.Candidate.from_parts(f"{case.lower()}/variant-planted", {"schema": "contraste.case/v1", "case_id": case})
    b = cs.Candidate.from_parts(f"{case.lower()}/variant-planted2", {"schema": "contraste.case/v1", "case_id": case})
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
    assert checked > 80


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
def test_a_fixture_of_one_case_does_not_validate_against_another_case(ref: str) -> None:
    doc = load(ref)
    others = [c.ref for c in cs.candidates() if c.ref != ref and c.ref.split("/")[0] in ("c03", "c08", "c09")]
    assert others
    for other in others:
        assert cs.errors(other, doc) != [], f"{ref} validates against {other}"


# --- PD at the C03 estimate sites ---------------------------------------------------------------------------------

PD_KEYS = {"predicted_cumulative_pd", "predicted_pd", "predicted_5y_pd", "pd_5y"}


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


@pytest.mark.parametrize("bad", [0, 1])
def test_a_predicted_pd_of_zero_or_one_fails_at_every_c03_estimate_site(bad: int) -> None:
    doc = load(C03)
    sites = list(pd_sites(doc, ("outputs",)))
    assert len(sites) > 20, len(sites)
    for path, _ in sites:
        mutated = copy.deepcopy(doc)
        get(mutated, path[:-1])[path[-1]] = bad
        assert cs.errors(C03, mutated) != [], f"{path} = {bad} still validates"


# --- LGD and CCF outside [0, 1] pass only with their flag ----------------------------------------------------------


def wrapper_sites(ref: str) -> list[tuple]:
    """Paths of every realised {value, flag} object of the fixture (the LGD wrapper of C08, the CCF wrapper of C09). The
    prediction sites of C08 are inside [0, 1] by construction and are tested in test_u6_fixes.py."""
    return [p for p, o in closed_objects(ref)
            if set(o) == {"value", "flag"} and p[-1] not in ("predicted", "mean_predicted", "mean_before", "mean_after")]


@pytest.mark.parametrize("ref", [C08, C09, C09M])
def test_an_out_of_range_lgd_or_ccf_passes_only_with_its_flag(ref: str) -> None:
    doc = load(ref)
    sites = wrapper_sites(ref)
    assert len(sites) >= (4 if "variant" in ref else 1), (ref, len(sites))
    for path in sites:
        if path[-1] == "estimate" and get(doc, path[:-1]).get("treatment") in ("censor", "floor-cap"):
            continue  # a treated estimate is inside [0, 1] by construction: test_u6_fixes.py::test_m12
        for value, flag, ok in [(1.25, "above-one", True), (-0.2, "below-zero", True),
                                (1.25, "in-range", False), (-0.2, "in-range", False), (0.5, "above-one", False),
                                (0.5, "below-zero", False), (1.25, "below-zero", False), (-0.2, "above-one", False),
                                (0.0, "in-range", True), (1.0, "in-range", True), (1.0, "above-one", False)]:
            m = copy.deepcopy(doc)
            get(m, path).update({"value": value, "flag": flag})
            assert (cs.errors(ref, m) == []) is ok, f"{ref} {path}: ({value}, {flag}) expected {'pass' if ok else 'fail'}"
        m = copy.deepcopy(doc)
        del get(m, path)["flag"]
        assert cs.errors(ref, m) != [], f"{ref} {path}: a value without its flag validates"
        m = copy.deepcopy(doc)
        get(m, path)["flag"] = "clipped"
        assert cs.errors(ref, m) != []


def test_the_fixtures_carry_at_least_one_flagged_out_of_range_value_each() -> None:
    for ref in (C08, C09):
        flags = [get(load(ref), p)["flag"] for p in wrapper_sites(ref)]
        assert "above-one" in flags or "below-zero" in flags, ref


def test_the_wrapper_value_and_flag_agree_in_the_fixtures() -> None:
    for ref in (C08, C09, C09M):
        for p in wrapper_sites(ref):
            w = get(load(ref), p)
            expected = "below-zero" if w["value"] < 0 else "above-one" if w["value"] > 1 else "in-range"
            assert w["flag"] == expected, (ref, p)


# --- money blocks carry their currency ----------------------------------------------------------------------------


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


MONEY_NAMES = {"gross_approval", "gross_charge_off", "gross_approval_total", "gross_charge_off_total", "ead", "predicted_ead",
               "realised_ead", "gap", "mean_ead_before", "mean_ead_after", "threshold", "total_gross_approval",
               "limit", "drawn", "undrawn", "ead_floor", "off_balance"}


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


# --- the C08 LGD proxy definition and bias statement ---------------------------------------------------------------


@pytest.mark.parametrize("ref", [C08, C08M])
def test_a_c08_document_without_the_lgd_proxy_statement_fails(ref: str) -> None:
    root = root_of(ref)
    doc = load(ref)
    proxy = doc[root]["lgd_proxy"]
    assert proxy["recovery_cash_flows_available"] is False
    assert proxy["bias_direction"] == "downward"
    for key in proxy:
        bad = copy.deepcopy(doc)
        del bad[root]["lgd_proxy"][key]
        assert cs.errors(ref, bad) != [], f"{ref}: lgd_proxy without {key} validates"
    bad = copy.deepcopy(doc)
    del bad[root]["lgd_proxy"]
    assert cs.errors(ref, bad) != []
    for text_key in ("definition", "bias_statement"):
        for lang in ("en", "es"):
            bad = copy.deepcopy(doc)
            bad[root]["lgd_proxy"][text_key][lang] = ""
            assert cs.errors(ref, bad) != [], f"empty {text_key}.{lang} validates"


def test_the_c08_proxy_states_that_the_sba_file_has_no_recovery_cash_flows() -> None:
    text = " ".join(out(C08)["lgd_proxy"]["bias_statement"].values()).lower()
    assert "recover" in text or "recuper" in text


def test_the_freddie_mac_slot_is_nullable_with_its_reason_never_a_number() -> None:
    for ref in (C08, C08M):
        doc = load(ref)
        status = doc[root_of(ref)]["data_status"]
        assert status["freddie_mac_available"] is False
        assert isinstance(status["freddie_mac_reason"], str) and status["freddie_mac_reason"]
        bad = copy.deepcopy(doc)
        bad[root_of(ref)]["data_status"]["freddie_mac_reason"] = None
        assert cs.errors(ref, bad) != [], "unavailable Freddie Mac without a reason validates"
        worse = copy.deepcopy(doc)
        worse[root_of(ref)]["data_status"]["freddie_mac_available"] = True
        assert cs.errors(ref, worse) != [], "available Freddie Mac with a reason validates"


# --- identities of the fixtures (what the engine contract promises) -----------------------------------------------


def test_c03_vintage_curves_are_monotone_and_observed_only_up_to_the_cutoff() -> None:
    o = out(C03)
    assert o["vintage_curves"]
    for vc in o["vintage_curves"]:
        n = len(vc["months"])
        assert len(vc["predicted_cumulative_pd"]) == len(vc["observed_cumulative_pd"]) == n
        assert vc["months"] == sorted(vc["months"]) and len(set(vc["months"])) == n
        assert all(b > a for a, b in zip(vc["predicted_cumulative_pd"], vc["predicted_cumulative_pd"][1:]))
        for m, x in zip(vc["months"], vc["observed_cumulative_pd"]):
            assert (x is not None) == (m <= vc["observed_until_month"]), (vc["fiscal_year"], m)
        obs = [x for x in vc["observed_cumulative_pd"] if x is not None]
        assert all(b >= a for a, b in zip(obs, obs[1:]))
        assert (vc["reason"] is None) == (vc["observed_until_month"] >= max(vc["months"]))


def test_c03_the_five_year_target_is_read_only_at_each_vintages_five_year_mark() -> None:
    o = out(C03)
    rows = {r["fiscal_year"]: r for r in o["vintage_summary"]["rows"]}
    assert o["target"]["horizon_months"] == 60 and o["target"]["observed_at_months"] == 60
    for vc in o["vintage_curves"]:
        row = rows[vc["fiscal_year"]]
        assert row["mark_observed"] == (vc["observed_until_month"] >= 60)
        i60 = vc["months"].index(60)
        assert math.isclose(row["predicted_5y_pd"], vc["predicted_cumulative_pd"][i60], abs_tol=1e-9)
        if vc["observed_until_month"] >= 60:
            assert math.isclose(row["observed_5y_pd"], vc["observed_cumulative_pd"][i60], abs_tol=1e-9)
            assert row["reason"] is None
        else:
            assert row["observed_5y_pd"] is None and row["reason"]
    assert any(r["observed_5y_pd"] is None for r in rows.values()), "the fixture shows an unobserved 5-year mark"


def test_c03_the_cohort_and_the_training_window_do_not_overlap() -> None:
    o = out(C03)
    assert o["training"]["last_fy"] <= o["cohort"]["first_fy"] - 6  # decision D1: the 5-year mark precedes the first approval
    assert o["cohort"]["first_fy"] <= o["cohort"]["last_fy"]
    assert sorted(r["fiscal_year"] for r in o["vintage_summary"]["rows"]) == list(
        range(o["cohort"]["first_fy"], o["cohort"]["last_fy"] + 1))


def test_c08_the_distribution_counts_close_and_the_masses_are_the_end_bins() -> None:
    o = out(C08)
    d = o["lgd_distribution"]
    inside = sum(b["n"] for b in d["bins"])
    assert inside + d["n_below_zero"] + d["n_above_one"] == d["n"]
    assert math.isclose(sum(b["share"] for b in d["bins"]) + d["share_below_zero"] + d["share_above_one"], 1.0,
                        abs_tol=1e-6)
    assert d["mass_at_zero"]["n"] <= d["bins"][0]["n"] and d["mass_at_one"]["n"] <= d["bins"][-1]["n"]
    edges = [(b["lower"], b["upper"]) for b in d["bins"]]
    assert edges[0][0] == 0.0 and edges[-1][1] == 1.0
    assert all(a[1] == b[0] for a, b in zip(edges, edges[1:]))
    assert d["treatment"] == "flagged-not-clipped"


def test_c08_the_downturn_add_on_is_downturn_minus_long_run_and_coverage_counts_the_covered() -> None:
    o = out(C08)
    rows = o["downturn"]["rows"]
    assert rows
    for r in rows:
        assert math.isclose(r["add_on"], r["downturn_lgd"]["value"] - r["long_run_lgd"]["value"], abs_tol=1e-9)
        assert r["covered"] == (r["downturn_lgd"]["value"] >= r["crisis_realised_lgd"]["value"] - 1e-12)
    cov = o["downturn"]["coverage"]
    assert cov["n_cohorts"] == len(rows)
    assert math.isclose(cov["share_covered"], sum(r["covered"] for r in rows) / len(rows), abs_tol=1e-9)


def test_c08_the_floor_bite_is_the_floored_mean_minus_the_unfloored_mean_and_never_negative() -> None:
    for r in out(C08)["floors_bite"]["rows"]:
        assert r["floor"] >= 0 and r["reference"]
        assert math.isclose(r["uplift"], r["mean_after"]["value"] - r["mean_before"]["value"], abs_tol=1e-9)
        assert r["uplift"] >= -1e-12
        assert r["mean_after"]["value"] >= r["floor"] - 1e-12 or r["share_binding"] < 1.0


def test_c08_the_models_floor_cells_are_the_transcribed_dossier_cells() -> None:
    cells = {c["id"]: c["floor"] for c in load(C08M)["fit"]["floors"]["cells"]}
    assert cells == {"corporate-unsecured": 0.25, "corporate-financial": 0.0, "corporate-receivables": 0.10,
                     "corporate-real-estate": 0.10, "corporate-other-physical": 0.15, "retail-mortgage": 0.05,
                     "retail-qrre": 0.50, "retail-other-unsecured": 0.30, "retail-other-financial": 0.0,
                     "retail-other-receivables": 0.10, "retail-other-real-estate": 0.10,
                     "retail-other-physical": 0.15}


def test_c09_bias_is_estimate_minus_truth_and_the_truth_is_one_per_level() -> None:
    o = out(C09)
    assert 0 <= o["level"] <= 5
    for r in o["ccf_by_design"]["rows"]:
        assert math.isclose(r["bias"], r["estimate"]["value"] - r["truth"]["value"], abs_tol=1e-9)
        assert math.isclose(r["truth"]["value"], o["generator"]["true_ccf"]["value"], abs_tol=1e-12)
        assert r["ci_low"] <= r["estimate"]["value"] <= r["ci_high"]
        assert r["within_tolerance"] == (abs(r["bias"]) <= o["ccf_by_design"]["tolerance"])
    designs = {r["design"] for r in o["ccf_by_design"]["rows"]}
    assert designs == {"fixed-horizon", "cohort", "variable-horizon"}


def test_c09_the_ead_backtest_gap_is_predicted_minus_realised_by_contiguous_bands() -> None:
    bt = out(C09)["ead_backtest"]
    rows = bt["rows"]
    for r in rows:
        assert math.isclose(r["gap"], r["predicted_ead"] - r["realised_ead"], abs_tol=1e-6)
        assert math.isclose(r["relative_gap"], r["gap"] / r["realised_ead"], abs_tol=1e-6)
    by_model: dict[str, list[dict]] = {}
    for r in rows:
        by_model.setdefault(r["model_id"], []).append(r)
    assert len(by_model) >= 2
    for rs in by_model.values():
        assert rs[0]["utilisation_lower"] == 0.0
        assert all(a["utilisation_upper"] == b["utilisation_lower"] for a, b in zip(rs, rs[1:]))


def test_c09_the_development_and_test_replications_are_independent() -> None:
    reps = out(C09)["replications"]
    assert reps["development"]["seeds"] and reps["test"]["seeds"]
    assert not set(reps["development"]["seeds"]) & set(reps["test"]["seeds"])
    assert len(reps["development"]["seeds"]) == reps["development"]["n_replications"]
    assert len(reps["test"]["seeds"]) == reps["test"]["n_replications"]


def test_c09_the_ccf_histogram_keeps_the_mass_below_zero_and_above_one() -> None:
    h = out(C09)["ccf_distribution"]
    assert sum(h["counts"]) == h["n"]
    assert len(h["counts"]) == len(h["edges"]) - 1
    assert h["edges"] == sorted(h["edges"]) and h["edges"][0] < 0 and h["edges"][-1] > 1
    below = sum(c for c, hi in zip(h["counts"], h["edges"][1:]) if hi <= 0)
    above = sum(c for c, lo in zip(h["counts"], h["edges"]) if lo >= 1)
    assert below == h["n_below_zero"] and above == h["n_above_one"]


def test_c09_the_convention_is_named_in_the_document() -> None:
    o = out(C09)
    assert o["convention"]["name"] == "eu-undrawn"
    assert "undrawn" in o["convention"]["definition"]["en"].lower()
    assert load(C09M)["fit"]["convention"]["name"] == "eu-undrawn"


# --- the catalog rows ---------------------------------------------------------------------------------------------


def row_cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def test_the_rows_fragment_has_the_seven_rows_in_the_catalog_columns() -> None:
    catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
    header = next(row_cells(ln) for ln in catalog.splitlines() if ln.startswith("| id | version"))
    lines = [ln for ln in catalog_rows(ROW_IDS) if ln.startswith("|")]
    rows = [row_cells(ln) for ln in lines]
    assert rows[0] == header
    data = [r for r in rows[1:] if not all(set(c) <= set(":- ") for c in r)]
    assert [r[0] for r in data] == ["c03-outputs", "c03-models", "c08-outputs", "c08-models", "c09-outputs", "c09-models",
                                    "engine-lgd-ead-api"]
    for r in data:
        assert len(r) == len(header), r[0]
        d = dict(zip(header, r))
        assert d["version"] == "1.0.0"
        # the producers are built (U5 in 0.08.000, U6 in 0.10.000): each row is real, with a committed example
        assert d["status"] == "real"
        assert (ROOT / d["example"]).is_file(), d["example"]
        assert d["provider"].startswith("fixture:")
        assert (ROOT / d["schema file"]).is_file(), d["schema file"]
        assert (ROOT / d["provider"].removeprefix("fixture:")).is_file(), d["provider"]
        assert (ROOT / d["example"]).is_file(), d["example"]
        for cell in (d["producer test"], d["consumer test"]):
            for t in cell.split(","):
                path, _, name = t.strip().partition("::")
                assert (ROOT / path).is_file(), path
                if name:
                    assert f"def {name}(" in (ROOT / path).read_text(encoding="utf-8"), t


# --- the engine LGD and EAD API contract --------------------------------------------------------------------------

MODULES = {
    "workout": ["eba_discount_rate", "workout_lgd", "range_flag", "ResolvedWorkouts", "resolve_incomplete", "closed_before",
                "LgdDistribution", "lgd_distribution"],
    "lgd_models": ["endpoint_transform", "LgdFit", "fit_ols", "fit_fractional_logit", "fit_beta", "fit_hurdle", "fit_tobit",
                   "cure_decomposition", "predict_lgd"],
    "downturn": ["identify_downturn", "DownturnResult", "downturn_add_on", "coverage_shortfall"],
    "ccf": ["reference_indices", "ccf_observations", "aggregate_ccf", "TreatedCcf", "treat_ccf", "ead_from_ccf", "to_us_terms",
            "small_undrawn_rule", "EadFit", "fit_direct_ead", "fit_utilisation_change", "predict_ead", "ccf_bias"],
    "floors": ["lgd_floor", "apply_lgd_floor", "supervisory_ccf", "ead_floor", "apply_ead_floor", "FloorBite"],
    "validation.lgd_ead": ["lgd_calibration_by_segment", "lgd_calibration_over_time", "lgd_discrimination",
                           "downturn_coverage", "ead_backtest_by_band", "ccf_estimator_bias"],
}
TEST_FUNCTIONS = MODULES["validation.lgd_ead"]


def prefix_of(module: str) -> str:
    return "riskvalidation.validation.lgd_ead" if module == "validation.lgd_ead" else f"riskvalidation.lgd_ead.{module}"


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
    assert "engine-lgd-ead-api" in text and "1.0.0" in text
    assert "common/test-result" in text


def test_the_engine_contract_covers_every_module_of_the_sizing_table() -> None:
    text = API.read_text(encoding="utf-8")
    for module in ("lgd_ead/workout.py", "lgd_ead/lgd_models.py", "lgd_ead/downturn.py", "lgd_ead/ccf.py",
                   "lgd_ead/floors.py", "validation/lgd_ead.py"):
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
        body = section("validation.lgd_ead", name)
        assert "-> TestResult" in body, name
        assert re.search(r"^- Light:", body, flags=re.M), name
        assert re.search(r"^- Golden:", body, flags=re.M), name
        assert re.search(r'test_id = "lgd_ead\.[a-z_]+"', body), name


def test_the_engine_contract_has_no_function_outside_the_table() -> None:
    declared = {key_of(m, n) for m, names in MODULES.items() for n in names}
    assert set(api_sections()) == declared


# --- the golden values of the engine contract recompute here from the formulas ------------------------------------


def test_the_engine_contract_carries_the_dossier_goldens() -> None:
    text = API.read_text(encoding="utf-8")
    for golden in ("0.479339", "1.136364", "-0.090909", "2.197225", "1.098612", "0.827586", "0.787234", "0.780634",
                   "0.266667", "0.36", "680", "0.0825", "3.464102", "0.074180", "0.435"):
        assert golden in text, golden
    for cell in ("CRE32.16", "CRE32.58", "CRE32.59", "CRE32.36", "CRE32.64", "CRE32.33", "CRE20.98", "CRE20.100"):
        assert cell in text, cell
    for test_id in ("lgd_ead.lgd_calibration_by_segment", "lgd_ead.lgd_calibration_over_time", "lgd_ead.lgd_discrimination",
                    "lgd_ead.downturn_coverage", "lgd_ead.ead_backtest_by_band", "lgd_ead.ccf_estimator_bias"):
        assert test_id in text, test_id
    assert "UNVERIFIED" in text


def disc(x: float, t: float, r: float) -> float:
    return x * (1 + r) ** (-t)


def test_golden_workout_lgd_recomputes() -> None:
    pv = disc(40 - 10, 1, 0.10) + disc(30, 2, 0.10)
    assert math.isclose(1 - pv / 100, 0.479339, abs_tol=5e-7)
    assert math.isclose(1 - disc(5 - 20, 1, 0.10) / 100, 1.136364, abs_tol=5e-7)
    assert math.isclose(1 - disc(120, 1, 0.10) / 100, -0.090909, abs_tol=5e-7)
    assert math.isclose(0.0325 + 0.05, 0.0825, abs_tol=1e-12)


def test_golden_fractional_logit_is_the_logit_of_the_group_means() -> None:
    # saturated one-dummy model: the Bernoulli quasi-score X'(y - mu) = 0 gives mu = the group mean in each group
    y0, y1 = [0.0, 0.5], [0.5, 1.0]
    b0 = math.log((sum(y0) / 2) / (1 - sum(y0) / 2))
    b1 = math.log((sum(y1) / 2) / (1 - sum(y1) / 2)) - b0
    assert math.isclose(b0, -1.098612, abs_tol=5e-7) and math.isclose(b1, 2.197225, abs_tol=5e-7)


def test_golden_ccf_under_each_reference_date_design_recomputes() -> None:
    drawn = {9: 420.0, 12: 500.0, 15: 560.0, 18: 640.0}
    limit, ead = 1000.0, 900.0
    ccf = {m: (ead - e) / (limit - e) for m, e in drawn.items()}
    assert math.isclose(ccf[9], 0.827586, abs_tol=5e-7)      # fixed horizon: t_d = 21, t_r = 9
    assert math.isclose(ccf[12], 0.8, abs_tol=1e-12)          # cohort: the calendar year starts at month 12
    mean = sum(ccf.values()) / 4
    pooled = sum(ead - e for e in drawn.values()) / sum(limit - e for e in drawn.values())
    assert math.isclose(mean, 0.780634, abs_tol=5e-7) and math.isclose(pooled, 0.787234, abs_tol=5e-7)


def test_golden_ccf_treatments_recompute() -> None:
    x = [-0.1, 0.0, 0.2, 0.6, 1.3]
    inside = [v for v in x if 0 <= v <= 1]
    assert math.isclose(sum(x) / 5, 0.4, abs_tol=1e-12)
    assert math.isclose(sum(inside) / len(inside), 0.266667, abs_tol=5e-7)
    assert math.isclose(sum(min(1.0, max(0.0, v)) for v in x) / 5, 0.36, abs_tol=1e-12)


def test_golden_floors_and_the_ead_floor_recompute() -> None:
    assert 600 + 0.5 * 0.40 * (1000 - 600) == 680.0
    assert max(650.0, 680.0) == 680.0 and max(0.20, 0.25) == 0.25


def test_golden_calibration_t_statistic_and_its_closed_form_p_value_recompute() -> None:
    d = [0.1, 0.2, 0.3]
    mean = sum(d) / 3
    sd = math.sqrt(sum((x - mean) ** 2 for x in d) / 2)
    t = mean / (sd / math.sqrt(3))
    assert math.isclose(t, 3.464102, abs_tol=5e-7)
    assert math.isclose(1 - t / math.sqrt(t * t + 2), 0.074180, abs_tol=5e-7)  # two-sided p for 2 degrees of freedom


def test_golden_cure_decomposition_and_hurdle_recompute() -> None:
    assert math.isclose(0.3 * 0.05 + 0.7 * 0.6, 0.435, abs_tol=1e-12)
    assert math.isclose(0.75 * 0.4, 0.3, abs_tol=1e-12)
    assert NormalDist().cdf(0.0) == 0.5
