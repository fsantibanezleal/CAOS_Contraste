"""U8-S: the C11 and C13 case contracts, their fixtures, the catalog rows and the engine market API contract.

The fixtures validate by discovery (tests/contracts/contract_schemas.py) against exactly one schema; the schemas are strict
both ways (a removed or an added key fails); a document without its sign convention fails; a C13 document without its
known deficiency fails; a C11 forecast dated on or before the end of its estimation window is caught by the leakage rule;
the hyperparameter span ends before the window it serves and before 2007; ES is never below VaR; a back-test that cannot
run is a not-evaluated row with its reason; the identities a document states (exceedances, FZ0 and tick-loss averages,
rolling 250-day counts and zones, Kupiec and Christoffersen statistics, Z2, Diebold-Mariano, the Spearman and KS
statistics and zones) recompute here from the formulas of dossier 05 and dossier 01 (tests/contracts_u8/market_math.py);
the engine contract names every function of the modules table of plans/contraste/units/U8-sizing.md with a golden value
or an invariant. The fixtures are labelled as fixtures and never published as results.
"""
from __future__ import annotations

import copy
import math
import re
from datetime import date
from typing import Any, Iterator

import pytest

import contract_schemas as cs
import market_math as mm
import producer_checks as pc

ROOT = cs.ROOT
FIXTURES = ROOT / "docs" / "contracts" / "fixtures"
SCHEMAS = ROOT / "docs" / "contracts" / "schemas"
API = ROOT / "docs" / "contracts" / "engine" / "market-api.md"
ROWS = ROOT / "docs" / "contracts" / "rows" / "U8.md"
CHANGES = ROOT / "changes" / "U8-S.md"

C11, C13 = "c11/variant-window", "c13/variant-deficiency"
C11M, C13M = "c11/models", "c13/models"
EXPECTED = {
    C11M: FIXTURES / "c11" / "models-fixture.json",
    C11: FIXTURES / "c11" / "variant-window-fixture.json",
    C13M: FIXTURES / "c13" / "models-fixture.json",
    C13: FIXTURES / "c13" / "variant-deficiency-fixture.json",
}
VARIANTS = {k: v for k, v in EXPECTED.items() if "variant" in k}
KINDS = {C11: "window", C13: "deficiency"}
ROW_IDS = ["c11-outputs", "c11-models", "c13-outputs", "c13-models", "engine-market-api"]


def catalog_rows(ids):
    """The catalog rows of these contract ids, header first (the unit's rows fragment was merged by the integrator at 0.11.000)."""
    catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
    lines = catalog.split("## Contracts", 1)[1].split("\n## ", 1)[0].splitlines()
    head = [ln for ln in lines if ln.startswith("| id | version")]
    return head + ["|---|"] + [ln for ln in lines if ln.startswith("| ") and ln.split("|")[1].strip() in ids]
WINDOWS = ["equity-2007-09", "equity-2020", "rates-2022", "fx-2008", "mixed-2023", "calm-2004-06"]
DEFICIENCIES = ["none", "missing-basis", "stale-volatility", "wrong-correlation", "omitted-factor", "time-misalignment"]


def load(ref: str) -> Any:
    return cs.load_json(EXPECTED[ref])


def out(ref: str) -> dict:
    return load(ref)["outputs"]


def root_of(ref: str) -> str:
    return "outputs" if "variant" in ref else "fit"


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
    assert doc["provenance"]["generators"] == ["fixture:u8-s-contracts"]
    assert any(i["source"] == "fixture-not-a-result" for i in doc["provenance"]["inputs"])
    key = "variant_id" if "variant" in ref else "fit_id"
    assert str(doc[key]).startswith("fixture-")


def test_the_fixtures_stay_small() -> None:
    for ref, path in EXPECTED.items():
        assert path.stat().st_size < 400_000, (ref, path.stat().st_size)


def test_every_u8_schema_is_case_folder_conformant_and_case_prefixed() -> None:
    assert cs.case_folder_violations() == []
    files = sorted(p for case in ("c11", "c13") for p in (SCHEMAS / case).glob("*.schema.json"))
    assert {p.relative_to(SCHEMAS).as_posix() for p in files} == {f"{ref}.schema.json" for ref in EXPECTED}
    for p in files:
        case = p.parent.name
        for name in cs.load_json(p).get("$defs", {}):
            assert name.startswith(case), f"{p.name}: $defs name {name!r} is not prefixed {case!r}"


def test_a_def_name_shared_by_two_files_of_a_case_has_one_definition() -> None:
    for case in ("c11", "c13"):
        seen: dict[str, Any] = {}
        for p in sorted((SCHEMAS / case).glob("*.schema.json")):
            for name, body in cs.load_json(p).get("$defs", {}).items():
                assert seen.setdefault(name, body) == body, f"{case}: {name} is defined twice, differently"


def test_every_u8_variant_schema_declares_its_outputs_kind() -> None:
    by_ref = {c.ref: c for c in cs.candidates()}
    for ref, kind in KINDS.items():
        assert by_ref[ref].consts["outputs.kind"] == kind
        assert by_ref[ref].consts["case_id"] == ref.split("/")[0].upper()
    for case in ("C11", "C13"):
        assert cs.default_variants().get(case) is None
    assert cs.default_violations() == []


@pytest.mark.parametrize("case", ["C11", "C13"])
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
    assert checked > 60


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
    others = [c.ref for c in cs.candidates() if c.ref != ref]
    assert others
    for other in others:
        assert cs.errors(other, doc) != [], f"{ref} validates against {other}"


# --- the sign convention is a required field ----------------------------------------------------------------------


@pytest.mark.parametrize("ref", EXPECTED)
def test_a_document_without_its_sign_convention_fails(ref: str) -> None:
    doc = load(ref)
    root = root_of(ref)
    sc = doc[root]["sign_convention"]
    assert sc["engine_convention"] == "return-negative" and sc["document_convention"] == "positive-loss"
    bad = copy.deepcopy(doc)
    del bad[root]["sign_convention"]
    assert cs.errors(ref, bad) != []
    for key in sc:
        bad = copy.deepcopy(doc)
        del bad[root]["sign_convention"][key]
        assert cs.errors(ref, bad) != [], key
    for key, wrong in (("document_convention", "return-negative"), ("engine_convention", "positive-loss")):
        bad = copy.deepcopy(doc)
        bad[root]["sign_convention"][key] = wrong
        assert cs.errors(ref, bad) != [], key
    for lang in ("en", "es"):
        bad = copy.deepcopy(doc)
        bad[root]["sign_convention"]["definition"][lang] = ""
        assert cs.errors(ref, bad) != [], f"empty definition.{lang} validates"


# --- C11: windows, leakage, hyperparameters ------------------------------------------------------------------------


d = pc.d
leakage_violations = pc.leakage_violations
span_violations = pc.span_violations


def test_the_fixture_has_no_leakage_and_a_valid_span() -> None:
    o = out(C11)
    assert leakage_violations(o) == []
    assert span_violations(o) == []
    assert o["hyperparameters"]["tuned_on_test_window"] is False


@pytest.mark.parametrize("shift", ["equal", "after"])
def test_a_forecast_on_or_before_the_end_of_its_estimation_window_is_caught(shift: str) -> None:
    doc = load(C11)
    g = doc["outputs"]["grid"]
    g["estimation_end"][10] = g["dates"][10] if shift == "equal" else g["dates"][11]
    assert cs.errors(C11, doc) == []  # a date comparison is not a JSON Schema rule: the producer check catches it
    assert leakage_violations(doc["outputs"]) != []


def test_an_estimation_window_that_starts_after_it_ends_is_caught() -> None:
    doc = load(C11)
    g = doc["outputs"]["grid"]
    g["estimation_start"][3] = g["dates"][3]
    assert leakage_violations(doc["outputs"]) != []


def test_a_span_that_is_not_the_d1_span_is_caught_by_the_schema_and_the_producer_check() -> None:
    """Decision D1 (review F1): 1995-01-01 to 2003-12-31 for every window; a span overlapping the calm 2004-06 test window
    (the superseded 1995-2006 span, or 2004-2006) is refused."""
    o = copy.deepcopy(out(C11))
    assert o["hyperparameters"]["fixed_on"] == {"start": "1995-01-01", "end": "2003-12-31"}
    for start, end in (("1995-01-03", "2006-12-29"), ("2004-01-02", "2006-12-29"), ("1995-01-01", "2007-01-01"),
                       ("1995-01-01", "2004-01-02"), ("1995-01-02", "2003-12-31")):
        doc = load(C11)
        doc["outputs"]["hyperparameters"]["fixed_on"] = {"start": start, "end": end}
        assert cs.errors(C11, doc) != [], (start, end)
        assert span_violations(doc["outputs"]) != [], (start, end)
    doc = load(C11)
    doc["outputs"]["hyperparameters"]["tuned_on_test_window"] = True
    assert cs.errors(C11, doc) != []
    mdoc = load(C11M)
    mdoc["fit"]["windows"][5]["fixed_on"]["end"] = "2005-06-30"
    assert cs.errors(C11M, mdoc) != [] and pc.c11_models_violations(mdoc) != []


def c11_variant_documents() -> list[tuple[str, dict]]:
    """The fixture and every committed C11 variant document (data/derived/C11, once the bake lands): the producer-side
    checks below are the ones U8-P1's documents must pass, so they run on whatever is committed."""
    docs = [("fixture", load(C11))]
    for path in sorted((ROOT / "data" / "derived" / "C11").glob("*.json")) if (ROOT / "data" / "derived" / "C11").is_dir() else []:
        doc = cs.load_json(path)
        if doc.get("schema") == "contraste.case/v1" and doc.get("case_id") == "C11":
            docs.append((path.name, doc))
    return docs


def test_every_committed_c11_document_obeys_the_producer_checks() -> None:
    for name, doc in c11_variant_documents():
        assert pc.c11_variant_violations(doc) == [], name


def test_the_window_ids_are_the_six_of_the_sdd() -> None:
    plan = load(C11M)["fit"]["windows"]
    assert [w["window_id"] for w in plan] == WINDOWS
    for w in plan:
        assert d(w["fixed_on"]["end"]) < d(w["start_date"]) and d(w["fixed_on"]["end"]) < date(2007, 1, 1)
        assert d(w["start_date"]) <= d(w["end_date"])
    assert out(C11)["window"]["window_id"] in WINDOWS
    doc = load(C11)
    doc["outputs"]["window"]["window_id"] = "equity-2024"
    assert cs.errors(C11, doc) != []
    assert load(C11)["variant_id"] == "fixture-" + out(C11)["window"]["window_id"]


def test_the_asset_class_matches_the_window_in_the_models_plan() -> None:
    plan = {w["window_id"]: w for w in load(C11M)["fit"]["windows"]}
    assert plan[out(C11)["window"]["window_id"]]["asset_class"] == out(C11)["window"]["asset_class"]
    assert {w["asset_class"] for w in plan.values()} == {"equity", "rates", "fx", "mixed"}


def test_a_day_missing_from_a_public_series_is_skipped_and_counted_never_filled() -> None:
    o = out(C11)
    miss = o["data_status"]["missing_days"]
    assert miss["treatment"] == "skipped-not-filled"
    assert miss["count"] == len(miss["dates"]) and miss["count"] > 0
    grid = set(o["grid"]["dates"])
    assert not grid & set(miss["dates"]), "a missing day is in the forecast grid"
    doc = load(C11)
    doc["outputs"]["data_status"]["missing_days"]["treatment"] = "forward-filled"
    assert cs.errors(C11, doc) != []


def test_the_derived_only_rule_withholds_the_realised_series() -> None:
    """Dossier 08 C.5: the Kenneth French returns are derived-only, so a document with a derived-only component commits
    forecasts and test statistics but not the realised series; a mirror-allowed portfolio may carry it."""
    o = out(C11)
    derived = any(c["source_class"] == "derived-only" for c in o["portfolio"]["components"])
    realised = o["grid"]["realised_loss"]
    assert realised["status"] == ("withheld-derived-only" if derived else "included")
    plant = copy.deepcopy(load(C11))
    plant["outputs"]["grid"]["realised_loss"] = {"status": "withheld-derived-only", "loss": None, "reason": ""}
    assert cs.errors(C11, plant) != [], "a withheld series without its reason validates"
    plant = copy.deepcopy(load(C11))
    plant["outputs"]["grid"]["realised_loss"] = {"status": "included", "loss": None, "reason": None}
    assert cs.errors(C11, plant) != []


def test_the_portfolio_weights_sum_to_one() -> None:
    comps = out(C11)["portfolio"]["components"]
    assert math.isclose(sum(c["weight"] for c in comps), 1.0, abs_tol=1e-9)


# --- C11: forecasts, exceedances and scores recompute --------------------------------------------------------------


def level_results() -> Iterator[tuple[dict, dict]]:
    for m in out(C11)["models"]:
        for lv in m["by_level"]:
            yield m, lv


def test_the_forecast_arrays_align_with_the_grid_and_es_is_never_below_var() -> None:
    o = out(C11)
    n = len(o["grid"]["dates"])
    assert n == o["window"]["n_forecast_days"] <= o["data_status"]["n_observed_days"]
    assert o["grid"]["realised_loss"]["loss"] is None or len(o["grid"]["realised_loss"]["loss"]) == n
    for m, lv in level_results():
        assert len(lv["var"]) == len(lv["es"]) == n, m["model_id"]
        assert all(v > 0 for v in lv["var"])
        for v, e in zip(lv["var"], lv["es"]):
            if e is not None:
                assert e >= v, f"{m['model_id']} alpha {lv['alpha']}: ES {e} below VaR {v}"


def test_es_below_var_is_caught() -> None:
    doc = copy.deepcopy(load(C11))
    lv = doc["outputs"]["models"][0]["by_level"][0]
    lv["es"][5] = lv["var"][5] * 0.5
    assert pc.c11_variant_violations(doc) != [], "the producer check does not report ES below VaR"
    assert any("ES below VaR" in x for x in pc.c11_variant_violations(doc))


def test_the_es_status_matches_the_null_pattern() -> None:
    seen = set()
    for m, lv in level_results():
        nulls = [i for i, e in enumerate(lv["es"]) if e is None]
        status = lv["es_status"]
        seen.add(status)
        if status == "forecast":
            assert nulls == [] and lv["es_undefined_days"] == []
        elif status == "undefined-on-days":
            assert nulls == lv["es_undefined_days"] != []
        else:
            assert status == "not-forecast" and len(nulls) == len(lv["es"]) and lv["es_undefined_days"] == []
    assert seen == {"forecast", "undefined-on-days", "not-forecast"}, "the fixture covers the three ES states"


def test_the_levels_are_the_declared_ones_and_the_expected_exceedances_are_alpha_times_n() -> None:
    o = out(C11)
    alphas = [lv["alpha"] for lv in o["levels"]]
    assert alphas == [0.01, 0.025]
    n = len(o["grid"]["dates"])
    for m, lv in level_results():
        assert lv["alpha"] in alphas
        assert lv["n_scored"] == n
        assert math.isclose(lv["expected_exceedances"], lv["alpha"] * n, abs_tol=1e-9)
        assert lv["n_exceedances"] == len(lv["exceedance_days"]) == len(set(lv["exceedance_days"]))
        assert lv["exceedance_days"] == sorted(lv["exceedance_days"])
        assert all(0 <= i < n for i in lv["exceedance_days"])


def test_the_exceedances_the_scores_and_the_ftest_inputs_recompute_from_the_realised_series() -> None:
    o = out(C11)
    loss = o["grid"]["realised_loss"]["loss"]
    assert loss is not None, "the C11 fixture is a mirror-allowed window with its realised series included"
    for m, lv in level_results():
        a = lv["alpha"]
        exc = [i for i, (l_, v) in enumerate(zip(loss, lv["var"])) if l_ > v]
        assert exc == lv["exceedance_days"], (m["model_id"], a)
        tick = sum(mm.tick_loss(l_, v, a) for l_, v in zip(loss, lv["var"])) / len(loss)
        assert math.isclose(tick, lv["tick_loss_mean"], abs_tol=1e-8), (m["model_id"], a)
        fz = [mm.fz0_loss(l_, v, e, a) for l_, v, e in zip(loss, lv["var"], lv["es"]) if e is not None]
        assert lv["n_fz0"] == len(fz)
        if fz:
            assert math.isclose(sum(fz) / len(fz), lv["fz0_mean"], abs_tol=1e-8), (m["model_id"], a)
            assert lv["fz0_reason"] is None
        else:
            assert lv["fz0_mean"] is None and lv["fz0_reason"]


def test_the_tick_loss_is_nonnegative_and_the_fz0_average_is_finite() -> None:
    for _, lv in level_results():
        assert lv["tick_loss_mean"] >= 0
        if lv["fz0_mean"] is not None:
            assert math.isfinite(lv["fz0_mean"])


def test_the_rolling_250_day_count_and_the_zone_recompute_at_one_percent_and_are_null_at_2_5() -> None:
    o = out(C11)
    n = len(o["grid"]["dates"])
    assert n >= 250
    zones = set()
    for m, lv in level_results():
        tl = lv["traffic_light"]
        if lv["alpha"] != 0.01:
            assert tl is None
            continue
        flags = [1 if i in set(lv["exceedance_days"]) else 0 for i in range(n)]
        counts = mm.rolling_counts(flags, 250)
        assert tl["window_days"] == 250 and tl["n_windows"] == len(counts) == n - 249
        assert tl["max_rolling_exceedances"] == max(counts)
        assert tl["final_zone"] == mm.traffic_zone(counts[-1]) and tl["final_rolling_exceedances"] == counts[-1]
        zs = [mm.traffic_zone(c) for c in counts]
        assert (tl["days_green"], tl["days_amber"], tl["days_red"]) == (zs.count("green"), zs.count("amber"), zs.count("red"))
        zones.add(tl["final_zone"])
    assert len(zones) >= 2, "the fixture shows more than one zone"


def test_a_window_shorter_than_250_days_has_a_not_evaluated_traffic_light_with_its_reason() -> None:
    doc = load(C11)
    doc["outputs"]["window"].update({"window_id": "equity-2020", "asset_class": "equity", "start_date": "2020-02-03",
                                     "end_date": "2020-06-30", "n_forecast_days": 100})
    for m in doc["outputs"]["models"]:
        for lv in m["by_level"]:
            if lv["traffic_light"] is not None:
                lv["traffic_light"] = {"window_days": 250, "n_windows": 0, "max_rolling_exceedances": None,
                                       "final_rolling_exceedances": None, "final_zone": "not_evaluated", "days_green": None,
                                       "days_amber": None, "days_red": None, "reason": "fewer than 250 forecast days"}
    assert cs.errors(C11, doc) == []
    lv = doc["outputs"]["models"][0]["by_level"][0]
    lv["traffic_light"]["reason"] = None
    assert cs.errors(C11, doc) != [], "a not-evaluated zone without its reason validates"
    lv["traffic_light"].update({"reason": "fewer than 250 forecast days", "max_rolling_exceedances": 3})
    assert cs.errors(C11, doc) != [], "a not-evaluated zone with a number validates"


# --- C11: the tests rows --------------------------------------------------------------------------------------------

ES_TESTS = {"market.acerbi_szekely", "market.du_escanciano_unconditional", "market.du_escanciano_conditional",
            "market.mcneil_frey_residual_test"}


def rows(test_id: str, model_id: str, alpha: float) -> list[dict]:
    return [t for t in load(C11)["tests"] if t["test_id"] == test_id and t["model_id"] == model_id
            and t["segment"] == f"alpha={alpha}"]


def test_every_test_id_of_a_level_result_has_a_row_of_that_model_and_level() -> None:
    for m, lv in level_results():
        assert lv["test_ids"], (m["model_id"], lv["alpha"])
        for tid in lv["test_ids"]:
            assert tid.startswith("market.")
            assert len(rows(tid, m["model_id"], lv["alpha"])) == 1, (tid, m["model_id"], lv["alpha"])
    tests = load(C11)["tests"]
    listed = {(t, m["model_id"], lv["alpha"]) for m, lv in level_results() for t in lv["test_ids"]}
    for t in tests:
        a = float(t["segment"].split("=")[1])
        assert (t["test_id"], t["model_id"], a) in listed, f"a row no level result lists: {t['test_id']} {t['model_id']}"


def test_the_kupiec_and_christoffersen_rows_recompute_from_the_exceedance_days() -> None:
    n = len(out(C11)["grid"]["dates"])
    for m, lv in level_results():
        a = lv["alpha"]
        flags = [1 if i in set(lv["exceedance_days"]) else 0 for i in range(n)]
        x = sum(flags)
        (k,) = rows("market.kupiec_pof", m["model_id"], a)
        assert k["n"] == n and k["n_events"] == x
        assert math.isclose(k["statistic"], mm.kupiec_lr(n, x, a), abs_tol=1e-6)
        assert math.isclose(k["p_value"], mm.chi2_sf(k["statistic"], 1), abs_tol=1e-6)
        assert math.isclose(k["metric"], mm.kupiec_exact_p(n, x, a), abs_tol=1e-6)
        assert k["extras"]["p_value_exact_basis"] == "binomial-minlike"
        (i_,) = rows("market.christoffersen_independence", m["model_id"], a)
        (cc,) = rows("market.christoffersen_conditional_coverage", m["model_id"], a)
        lr_ind = mm.christoffersen_ind_lr(flags)
        assert math.isclose(i_["statistic"], lr_ind, abs_tol=1e-6)
        assert math.isclose(i_["p_value"], mm.chi2_sf(lr_ind, 1), abs_tol=1e-6)
        assert math.isclose(cc["statistic"], k["statistic"] + lr_ind, abs_tol=1e-6)
        assert math.isclose(cc["p_value"], mm.chi2_sf(cc["statistic"], 2), abs_tol=1e-6)


def test_the_light_follows_the_stated_alphas() -> None:
    for t in load(C11)["tests"]:
        if t["light"] == "not_evaluated":
            continue
        want = "red" if t["p_value"] < t["alpha_red"] else "amber" if t["p_value"] < t["alpha_amber"] else "green"
        assert t["light"] == want, (t["test_id"], t["model_id"], t["segment"])


def test_a_back_test_that_cannot_run_is_a_not_evaluated_row_with_its_reason_never_a_number() -> None:
    tests = load(C11)["tests"]
    ne = [t for t in tests if t["light"] == "not_evaluated"]
    assert ne
    for t in ne:
        assert t["statistic"] is None and t["p_value"] is None and t["metric"] is None
        assert t["notes"], t["test_id"]
    # an ES back-test of a model whose ES is undefined on some day, or never forecast, is such a row
    for m, lv in level_results():
        if lv["es_status"] != "forecast":
            for tid in lv["test_ids"]:
                if tid in ES_TESTS:
                    (row,) = rows(tid, m["model_id"], lv["alpha"])
                    assert row["light"] == "not_evaluated", (tid, m["model_id"])
    # the duration test with fewer than two exceedances cannot run
    for m, lv in level_results():
        if "market.duration_test" in lv["test_ids"] and lv["n_exceedances"] < 2:
            (row,) = rows("market.duration_test", m["model_id"], lv["alpha"])
            assert row["light"] == "not_evaluated" and row["notes"]
    assert any(t["test_id"] == "market.duration_test" and t["light"] == "not_evaluated" for t in tests)
    assert any(t["test_id"] == "market.acerbi_szekely" and t["light"] == "not_evaluated" for t in tests)


@pytest.mark.parametrize("ref", [C11, C13])
@pytest.mark.parametrize("field,value", [("statistic", 1.5), ("p_value", 0.5), ("metric", 0.1)])
def test_a_not_evaluated_row_with_a_number_is_refused(ref: str, field: str, value: float) -> None:
    doc = load(ref)
    doc["tests"][0].update({"light": "not_evaluated", "statistic": None, "p_value": None, "metric": None, "notes": "x"})
    assert cs.errors(ref, doc) == []
    doc["tests"][0][field] = value
    assert cs.errors(ref, doc) != []
    doc["tests"][0][field] = None
    doc["tests"][0]["notes"] = ""
    assert cs.errors(ref, doc) != [], "a not-evaluated row without its reason validates"


def test_z2_recomputes_from_the_realised_series_and_the_es_forecasts() -> None:
    o = out(C11)
    loss = o["grid"]["realised_loss"]["loss"]
    checked = 0
    for m, lv in level_results():
        rs = rows("market.acerbi_szekely", m["model_id"], lv["alpha"])
        if not rs or rs[0]["light"] == "not_evaluated":
            continue
        z = mm.z2(loss, lv["var"], lv["es"], lv["alpha"])
        assert math.isclose(rs[0]["statistic"], z, abs_tol=1e-6), m["model_id"]
        assert rs[0]["extras"]["statistic_name"] == "Z2"
        nulls = [e for e in o["es_backtests"] if e["model_id"] == m["model_id"] and e["alpha"] == lv["alpha"]]
        assert len(nulls) == 1 and math.isclose(nulls[0]["realised"], z, abs_tol=1e-6)
        checked += 1
    assert checked >= 2


def test_the_es_null_distributions_are_consistent() -> None:
    o = out(C11)
    for e in o["es_backtests"]:
        h = e["histogram"]
        assert len(h["counts"]) == len(h["edges"]) - 1 and sum(h["counts"]) == e["n_draws"]
        assert h["edges"] == sorted(h["edges"])
        assert e["critical_0_01pct"] <= e["critical_5pct"], "the red critical value lies below the yellow one"
        assert e["statistic"] == "Z2"
    ref = load(C11M)["fit"]["es_reference"]
    assert ref["yellow"] == -0.70 and ref["red"] == -1.8 and ref["n_days"] == 250 and ref["alpha"] == 0.025
    assert ref["statistic"] == "Z2"


# --- C11: the comparison --------------------------------------------------------------------------------------------


def test_the_eligibility_gates_are_the_red_rows_of_the_gate_tests() -> None:
    gates = [g["test_id"] for g in load(C11M)["fit"]["eligibility_gates"]]
    assert "market.kupiec_pof" in gates and "market.christoffersen_conditional_coverage" in gates
    for m in out(C11)["models"]:
        failed = set()
        for lv in m["by_level"]:
            for tid in gates:
                for r in rows(tid, m["model_id"], lv["alpha"]):
                    if r["light"] == "red":
                        failed.add(tid)
        assert set(m["failed_gates"]) == failed, m["model_id"]
        assert m["eligible"] == (not failed), m["model_id"]
    assert any(not m["eligible"] for m in out(C11)["models"]) and any(m["eligible"] for m in out(C11)["models"])


def test_the_champion_is_the_lowest_fz0_among_the_eligible_with_a_score() -> None:
    o = out(C11)
    for ch in o["comparison"]["champions"]:
        cands = []
        for m in o["models"]:
            if not m["eligible"]:
                continue
            lv = next(x for x in m["by_level"] if x["alpha"] == ch["alpha"])
            if lv["fz0_mean"] is not None:
                cands.append((lv["fz0_mean"], m["model_id"]))
        if cands:
            assert ch["model_id"] == min(cands)[1] and ch["reason"] is None
        else:
            assert ch["model_id"] is None and ch["reason"]
    assert {c["alpha"] for c in o["comparison"]["champions"]} == {0.01, 0.025}
    bad = load(C11)
    bad["outputs"]["comparison"]["champions"][0].update({"model_id": None, "reason": None})
    assert cs.errors(C11, bad) != [], "no champion without a reason validates"


def common_sample(o: dict, alpha: float, ids: list[str], loss_kind: str) -> list[int]:
    n = len(o["grid"]["dates"])
    idx = list(range(n))
    if loss_kind == "fz0":
        for mid in ids:
            lv = next(x for m in o["models"] if m["model_id"] == mid for x in m["by_level"] if x["alpha"] == alpha)
            idx = [i for i in idx if lv["es"][i] is not None]
    return idx


def test_the_diebold_mariano_rows_recompute_on_the_common_sample() -> None:
    o = out(C11)
    loss = o["grid"]["realised_loss"]["loss"]
    cmp = o["comparison"]
    assert cmp["significance"] == 0.05 and cmp["hac_kernel"] == "bartlett"
    champ = {c["alpha"]: c["model_id"] for c in cmp["champions"]}
    seen_ne = False
    for r in cmp["dm"]:
        a = r["alpha"]
        assert r["versus"] == champ[a] and r["model_id"] != champ[a]
        if r["not_evaluated_reason"] is not None:
            seen_ne = True
            assert r["dm_statistic"] is None and r["p_value"] is None and r["mean_diff"] is None and r["n_common"] is None
            continue
        ids = [r["model_id"], r["versus"]]
        idx = common_sample(o, a, ids, r["loss"])
        assert r["n_common"] == len(idx)
        lv = {mid: next(x for m in o["models"] if m["model_id"] == mid for x in m["by_level"] if x["alpha"] == a) for mid in ids}
        if r["loss"] == "fz0":
            ls = {mid: [mm.fz0_loss(loss[i], lv[mid]["var"][i], lv[mid]["es"][i], a) for i in idx] for mid in ids}
        else:
            ls = {mid: [mm.tick_loss(loss[i], lv[mid]["var"][i], a) for i in idx] for mid in ids}
        diff = [x - y for x, y in zip(ls[ids[0]], ls[ids[1]])]
        assert math.isclose(r["mean_diff"], sum(diff) / len(diff), abs_tol=1e-8)
        z = mm.dm_statistic(diff, r["hac_lags"])
        assert math.isclose(r["dm_statistic"], z, abs_tol=1e-5), (r["model_id"], a, r["loss"])
        assert math.isclose(r["p_value"], mm.two_sided_p(z), abs_tol=1e-5)
        want = "indistinguishable" if r["p_value"] >= cmp["significance"] else ("better" if r["mean_diff"] < 0 else "worse")
        assert r["direction"] == want
    assert seen_ne, "the fixture shows a Diebold-Mariano row that cannot be computed"


def test_a_diebold_mariano_row_has_a_statistic_xor_a_reason() -> None:
    doc = load(C11)
    row = next(r for r in doc["outputs"]["comparison"]["dm"] if r["not_evaluated_reason"] is None)
    row["not_evaluated_reason"] = "x"
    assert cs.errors(C11, doc) != []
    doc = load(C11)
    row = next(r for r in doc["outputs"]["comparison"]["dm"] if r["not_evaluated_reason"] is not None)
    row["not_evaluated_reason"] = None
    assert cs.errors(C11, doc) != []


def test_the_model_confidence_set_counts_its_members() -> None:
    o = out(C11)
    assert o["comparison"]["mcs"]
    for s in o["comparison"]["mcs"]:
        assert s["n_in_set"] == sum(1 for m in s["members"] if m["in_set"]) >= 1
        assert s["confidence"] == 0.90 and s["statistic"] in ("Tmax", "TR") and s["loss"] == "fz0"
        for m in s["members"]:
            assert 0 <= m["p_value"] <= 1
            assert m["in_set"] == (m["p_value"] >= 1 - s["confidence"]), "membership is p >= 1 - confidence"
        scored = {m["model_id"] for mod in o["models"] for m in [mod]
                  if any(x["alpha"] == s["alpha"] and x["fz0_mean"] is not None for x in mod["by_level"])}
        assert {m["model_id"] for m in s["members"]} <= scored, "an MCS lists a model with no FZ0 score"


# --- C11 models -----------------------------------------------------------------------------------------------------


def test_the_c11_models_ladder_and_the_variant_models_agree() -> None:
    fit = load(C11M)["fit"]
    ladder = {r["model_id"]: r for r in fit["ladder"]}
    for m in out(C11)["models"]:
        assert m["model_id"] in ladder, m["model_id"]
        assert ladder[m["model_id"]]["rung"] == m["rung"]
    assert {m["id"] for m in load(C11)["model"]} == {m["model_id"] for m in out(C11)["models"]}
    statuses = {r["status"] for r in fit["ladder"]}
    assert statuses == {"fitted", "challenger-not-run"}
    for r in fit["ladder"]:
        assert (r["not_run_reason"] is None) == (r["status"] == "fitted")
        assert r["forecasts_es"] == (r["model_id"] != "caviar-sav")


def test_the_traffic_light_table_is_the_transcribed_mar32_9_table() -> None:
    t = load(C11M)["fit"]["traffic_light"]
    assert t["window_days"] == 250 and t["confidence"] == 0.99
    assert [r["exceptions"] for r in t["rows"]] == list(range(11))
    assert [r["frtb_multiplier"] for r in t["rows"]] == mm.FRTB_MULTIPLIER
    assert [r["us_multiplier"] for r in t["rows"]] == mm.US_MULTIPLIER
    assert [r["zone"] for r in t["rows"]] == [mm.traffic_zone(i) for i in range(11)]
    for r in t["rows"]:
        assert math.isclose(r["cumulative_probability_pct"], 100 * mm.binom_cdf(r["exceptions"], 250, 0.01), abs_tol=0.005)
    assert [r["cumulative_probability_pct"] for r in t["rows"]] == [8.11, 28.58, 54.32, 75.81, 89.22, 95.88, 98.63, 99.60,
                                                                    99.89, 99.97, 99.99]


def test_the_models_hyperparameter_values_are_not_tuned_on_a_test_window() -> None:
    for w in load(C11M)["fit"]["windows"]:
        assert d(w["fixed_on"]["end"]) < d(w["start_date"])


def test_the_derived_only_sources_are_named_in_the_models_document() -> None:
    srcs = {s["series_id"]: s for s in load(C11M)["fit"]["data_sources"]}
    assert srcs["french-daily"]["source_class"] == "derived-only"
    assert srcs["treasury-par"]["source_class"] == "mirror-allowed" and srcs["h10-fx"]["source_class"] == "mirror-allowed"
    comps = {c["series_id"] for c in out(C11)["portfolio"]["components"]}
    assert comps <= set(srcs)
    for c in out(C11)["portfolio"]["components"]:
        assert c["source_class"] == srcs[c["series_id"]]["source_class"]


# --- C13: the known deficiency, PLA and the desk back-test -------------------------------------------------------------


def test_a_c13_document_without_its_known_deficiency_fails() -> None:
    doc = load(C13)
    k = doc["outputs"]["known_deficiency"]
    for key in k:
        bad = copy.deepcopy(doc)
        del bad["outputs"]["known_deficiency"][key]
        assert cs.errors(C13, bad) != [], key
    bad = copy.deepcopy(doc)
    del bad["outputs"]["known_deficiency"]
    assert cs.errors(C13, bad) != []
    bad = copy.deepcopy(doc)
    bad["outputs"]["known_deficiency"]["deficiency_id"] = "unknown-defect"
    assert cs.errors(C13, bad) != []


@pytest.mark.parametrize("dfid", DEFICIENCIES)
def test_each_of_the_six_deficiencies_validates_with_its_coupled_fields(dfid: str) -> None:
    doc = load(C13)
    k = doc["outputs"]["known_deficiency"]
    k["deficiency_id"] = dfid
    k["planted"] = dfid != "none"
    k["intended_to_fail"] = "none" if dfid == "none" else "spearman"
    doc["outputs"]["detection"]["role"] = "size" if dfid == "none" else "power"
    assert cs.errors(C13, doc) == [], cs.errors(C13, doc)
    # the coupling is enforced: a planted flag, an intended test or a role that disagrees with the id fails
    for field, wrong in (("planted", dfid == "none"), ("intended_to_fail", "spearman" if dfid == "none" else "none")):
        bad = copy.deepcopy(doc)
        bad["outputs"]["known_deficiency"][field] = wrong
        assert cs.errors(C13, bad) != [], (dfid, field)
    bad = copy.deepcopy(doc)
    bad["outputs"]["detection"]["role"] = "power" if dfid == "none" else "size"
    assert cs.errors(C13, bad) != [], (dfid, "role")


def test_the_c13_models_plan_lists_exactly_the_six_deficiencies() -> None:
    fit = load(C13M)["fit"]
    assert [p["deficiency_id"] for p in fit["deficiencies"]] == DEFICIENCIES
    assert [p["planted"] for p in fit["deficiencies"]] == [False] + [True] * 5
    assert out(C13)["known_deficiency"]["deficiency_id"] in DEFICIENCIES
    assert load(C13)["variant_id"] == "fixture-" + out(C13)["known_deficiency"]["deficiency_id"]


def test_the_pla_thresholds_are_the_transcribed_mar32_42_values() -> None:
    for th in (out(C13)["pla"]["thresholds"], load(C13M)["fit"]["pla_thresholds"]):
        assert (th["spearman_green"], th["spearman_red"], th["ks_green"], th["ks_red"]) == (0.80, 0.70, 0.09, 0.12)
        assert th["ecdf_step"] == 0.004 and th["window_days"] == 250 and th["reference"] == "MAR32.42"


def test_the_example_replication_recomputes_its_spearman_ks_and_zone() -> None:
    ex = out(C13)["example"]
    assert len(ex["hpl"]) == len(ex["rtpl"]) == 250
    rho = mm.spearman(ex["hpl"], ex["rtpl"])
    ks = mm.ks_statistic(ex["hpl"], ex["rtpl"])
    assert math.isclose(ex["spearman"], rho, abs_tol=1e-6)
    assert math.isclose(ex["ks"], ks, abs_tol=1e-6)
    assert ex["zone"] == mm.pla_zone(rho, ks)
    bad = load(C13)
    bad["outputs"]["example"]["hpl"] = bad["outputs"]["example"]["hpl"][:-1]
    assert cs.errors(C13, bad) != [], "249 observations validate"


def test_the_zone_counts_close_on_the_replications() -> None:
    o = out(C13)
    n = o["generator"]["n_replications"]
    z = o["pla"]["zones"]
    assert z["n"] == n
    for key in ("overall", "spearman", "ks"):
        assert z[key]["green"] + z[key]["amber"] + z[key]["red"] == n, key
    for dk in o["desk_backtest"]:
        assert dk["n_within_limit"] + dk["n_over_limit"] == n
        assert math.isclose(dk["share_over_limit"], dk["n_over_limit"] / n, abs_tol=1e-9)
    det = o["detection"]
    assert det["n_replications"] == n
    assert det["n_amber_or_red"] == z["overall"]["amber"] + z["overall"]["red"] and det["n_red"] == z["overall"]["red"]
    assert math.isclose(det["share_amber_or_red"], det["n_amber_or_red"] / n, abs_tol=1e-9)
    assert math.isclose(det["share_red"], det["n_red"] / n, abs_tol=1e-9)
    se = math.sqrt(det["share_amber_or_red"] * (1 - det["share_amber_or_red"]) / n)
    assert math.isclose(det["mc_se"], se, abs_tol=1e-6)
    assert det["ci_low"] <= det["share_amber_or_red"] <= det["ci_high"]


def test_the_joint_zone_counts_are_consistent_with_the_single_statistic_counts() -> None:
    """MAR32.42: red when either statistic is red, green only when both are green."""
    z = out(C13)["pla"]["zones"]
    assert z["overall"]["red"] >= max(z["spearman"]["red"], z["ks"]["red"])
    assert z["overall"]["green"] <= min(z["spearman"]["green"], z["ks"]["green"])
    for key in ("spearman", "ks"):
        dist = out(C13)["pla"][key]
        assert dist["min"] <= dist["q05"] <= dist["q50"] <= dist["q95"] <= dist["max"]
    for dk in out(C13)["desk_backtest"]:
        e = dk["exceptions"]
        assert e["min"] <= e["q05"] <= e["q50"] <= e["q95"] <= e["max"]


def test_the_detection_counts_by_test_follow_the_zone_counts_and_the_intended_test() -> None:
    o = out(C13)
    z, det = o["pla"]["zones"], o["detection"]
    assert det["by_test"]["spearman_flagged"] == z["spearman"]["amber"] + z["spearman"]["red"]
    assert det["by_test"]["ks_flagged"] == z["ks"]["amber"] + z["ks"]["red"]
    desk99 = next(dk for dk in o["desk_backtest"] if dk["alpha"] == 0.01)
    assert det["by_test"]["desk_backtest_flagged"] == desk99["n_over_limit"]
    want = {"spearman": det["by_test"]["spearman_flagged"], "ks": det["by_test"]["ks_flagged"], "either": det["n_amber_or_red"],
            "none": None}[o["known_deficiency"]["intended_to_fail"]]
    assert det["intended_test_flagged"] == want


def test_the_c13_test_rows_follow_the_example_and_the_desk_limits() -> None:
    doc = load(C13)
    ex = doc["outputs"]["example"]
    (pla,) = [t for t in doc["tests"] if t["test_id"] == "market.pla_test"]
    assert pla["statistic"] == ex["spearman"] and pla["metric"] == ex["ks"] and pla["light"] == ex["zone"] and pla["n"] == 250
    for t in doc["tests"]:
        if t["test_id"] == "market.desk_backtest":
            limit = {"alpha=0.025": 30, "alpha=0.01": 12}[t["segment"]]
            assert t["metric"] == limit and t["light"] == ("green" if t["statistic"] <= limit else "red")


def test_the_desk_back_test_levels_and_limits_are_the_mar32_18_limits() -> None:
    dks = out(C13)["desk_backtest"]
    assert {(dk["alpha"], dk["limit_exceptions"]) for dk in dks} == {(0.025, 30), (0.01, 12)}
    assert all(dk["n_days"] == 250 for dk in dks)
    bad = load(C13)
    bad["outputs"]["desk_backtest"][0]["limit_exceptions"] = 13
    assert cs.errors(C13, bad) != [], "a desk limit that is not the MAR32.18 limit validates"


def test_the_c13_fixture_is_synthetic_known_truth() -> None:
    assert load(C13)["provenance"]["truth_status"] == "synthetic-known-truth"
    assert load(C13M)["provenance"]["truth_status"] == "synthetic-known-truth"
    assert load(C11)["provenance"]["truth_status"] == "real-outcomes"
    assert out(C13)["generator"]["seed_rule"] == "seed_base+replication_index"
    assert out(C13)["generator"]["notice"]["en"]


# --- the catalog rows -----------------------------------------------------------------------------------------------


def row_cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def test_the_rows_fragment_has_the_five_rows_in_the_catalog_columns() -> None:
    catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
    header = next(row_cells(ln) for ln in catalog.splitlines() if ln.startswith("| id | version"))
    lines = [ln for ln in catalog_rows(ROW_IDS) if ln.startswith("|")]
    rows_ = [row_cells(ln) for ln in lines]
    assert rows_[0] == header
    data = [r for r in rows_[1:] if not all(set(c) <= set(":- ") for c in r)]
    assert [r[0] for r in data] == ROW_IDS
    for r in data:
        assert len(r) == len(header), r[0]
        dd = dict(zip(header, r))
        assert dd["version"] == "1.0.0"
        assert dd["status"] == "real"                        # the integrator set real when the bakes landed (0.11.000)
        assert dd["provider"].startswith("fixture:")
        assert (ROOT / dd["schema file"]).is_file(), dd["schema file"]
        assert (ROOT / dd["provider"].removeprefix("fixture:")).is_file(), dd["provider"]
        assert (ROOT / dd["example"]).is_file(), dd["example"]
        for cell in (dd["producer test"], dd["consumer test"]):
            for t in cell.split(","):
                path, _, name = t.strip().partition("::")
                assert (ROOT / path).is_file(), path
                if name:
                    assert f"def {name}(" in (ROOT / path).read_text(encoding="utf-8"), t


def test_the_changes_fragment_is_bullets_only() -> None:
    # merged by the integrator into the 0.11.000 entry of the CHANGELOG (fragments.py changelog refuses anything but bullets)
    assert not CHANGES.exists()
    entry = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").split("## [0.11.000]", 1)[1].split("\n## [", 1)[0]
    lines = [ln for ln in entry.splitlines()[1:] if ln.strip()]
    bullets = lines[1:]                                       # the first line is the entry's summary sentence
    assert bullets and bullets[0].startswith("- ")
    for ln in bullets:
        assert ln.startswith("- ") or ln.startswith("  "), ln
        assert not ln.startswith("#")
    assert "C11" in entry and "C13" in entry


# --- the engine market API contract ---------------------------------------------------------------------------------

MODULES = {
    "conventions": ["to_loss_numbers", "from_loss_numbers", "var_es_from_sample", "var_es_from_distribution"],
    "historical": ["age_weights", "historical_var_es", "age_weighted_var_es", "filtered_hs_var_es", "volatility_updated_hs_var_es"],
    "parametric": ["delta_normal_var_es", "cornish_fisher_var", "ewma_variance", "ewma_effective_days", "ewma_var_es"],
    "garch": ["GarchFit", "fit_garch", "garch_var_es_forecast"],
    "evt": ["GpdFit", "fit_gpd", "evt_var_es", "conditional_evt_forecast", "threshold_stability"],
    "caviar": ["CaviarFit", "fit_caviar", "caviar_var_forecast", "caviar_es_forecast", "dynamic_quantile_statistic"],
    "gas_fz": ["GasFzFit", "fit_gas_fz", "gas_fz_forecast", "fit_hybrid_garch_fz"],
    "scoring": ["fz0_loss", "tick_loss", "mean_scores", "diebold_mariano", "model_confidence_set"],
    "frtb": ["binomial_cumulative_probability", "traffic_light_zone", "mar32_multiplier", "desk_exception_limit",
             "desk_exceptions", "pla_spearman", "pla_ks", "pla_zone"],
    "validation.market": ["kupiec_pof", "christoffersen_independence", "christoffersen_conditional_coverage", "duration_test",
                          "basel_traffic_light", "acerbi_szekely", "du_escanciano_unconditional", "du_escanciano_conditional",
                          "mcneil_frey_residual_test", "dynamic_quantile_test", "pla_test", "desk_backtest"],
}
TEST_FUNCTIONS = MODULES["validation.market"]
DATACLASSES = {"GarchFit", "GpdFit", "CaviarFit", "GasFzFit"}


def prefix_of(module: str) -> str:
    return "riskvalidation.validation.market" if module == "validation.market" else f"riskvalidation.market.{module}"


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
    assert "engine-market-api" in text and "1.0.0" in text
    assert "common/test-result" in text and "positive loss" in text and "return convention" in text


def test_the_engine_contract_covers_every_module_of_the_sizing_table() -> None:
    text = API.read_text(encoding="utf-8")
    for module in ("market/conventions.py", "market/historical.py", "market/parametric.py", "market/garch.py", "market/evt.py",
                   "market/caviar.py", "market/gas_fz.py", "market/scoring.py", "market/frtb.py", "validation/market.py"):
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
        body = section("validation.market", name)
        assert "-> TestResult" in body, name
        assert re.search(r"^- Light:", body, flags=re.M), name
        assert re.search(r"^- Golden:", body, flags=re.M), name
        assert f'test_id = "market.{name}"' in body, name


def test_the_engine_contract_has_no_function_outside_the_table() -> None:
    declared = {key_of(m, n) for m, names in MODULES.items() for n in names}
    assert set(api_sections()) == declared


def test_the_fixture_test_ids_are_functions_of_the_engine_contract() -> None:
    ids = {t["test_id"] for ref in (C11, C13) for t in load(ref)["tests"]}
    assert ids
    for tid in ids:
        assert tid.startswith("market.") and tid.removeprefix("market.") in TEST_FUNCTIONS, tid


def test_the_engine_contract_carries_the_dossier_goldens_and_marks_what_is_unverified() -> None:
    text = API.read_text(encoding="utf-8")
    for golden in ("8.11", "28.58", "54.32", "75.81", "89.22", "95.88", "98.63", "99.60", "99.89", "99.97", "99.99",
                   "3.841", "5.991", "74.4", "151.2", "0.80", "0.70", "0.09", "0.12", "0.004", "-0.70", "-1.8",
                   "1.50", "1.70", "1.76", "1.83", "1.88", "1.92", "2.00"):
        assert golden in text, golden
    for cell in ("MAR32.9", "MAR32.18", "MAR32.42", "MAR32.36", "MAR32.39", "arXiv 1707.05108", "McNeil and Frey"):
        assert cell in text, cell
    for tid in TEST_FUNCTIONS:
        assert f"market.{tid}" in text, tid
    assert text.count("UNVERIFIED") >= 5
    for decision in ("D-1", "D-2"):
        assert decision in text


def test_every_dossier_line_a_golden_cites_is_named() -> None:
    text = API.read_text(encoding="utf-8")
    for ref in ("dossier 05", "dossier 01", "dossier 08", "A.0", "A.1", "A.2", "B.1", "B.2", "B.3", "B.4", "B.5", "B.6", "D.4"):
        assert ref in text, ref


# --- the golden values of the engine contract recompute here from the formulas -----------------------------------------


def test_golden_mar32_9_cumulative_probabilities_recompute() -> None:
    want = [8.11, 28.58, 54.32, 75.81, 89.22, 95.88, 98.63, 99.60, 99.89, 99.97, 99.99]
    got = [100 * mm.binom_cdf(k, 250, 0.01) for k in range(11)]
    for g, w in zip(got, want):
        assert math.isclose(g, w, abs_tol=0.005), (g, w)


def test_golden_amber_starts_at_95_and_red_at_99_99_percent() -> None:
    cum = [mm.binom_cdf(k, 250, 0.01) for k in range(15)]
    assert min(k for k, c in enumerate(cum) if c >= 0.95) == 5
    assert min(k for k, c in enumerate(cum) if c >= 0.9999 - 5e-5) == 10


def test_golden_chi_square_critical_values() -> None:
    assert math.isclose(mm.chi2_ppf(0.95, 1), 3.841, abs_tol=5e-4)
    assert math.isclose(mm.chi2_ppf(0.95, 2), 5.991, abs_tol=5e-4)


def test_golden_ewma_effective_days() -> None:
    assert round(mm.ewma_effective_days(0.94, 0.01), 1) == 74.4 and int(mm.ewma_effective_days(0.94, 0.01)) == 74
    assert round(mm.ewma_effective_days(0.97, 0.01), 1) == 151.2 and int(mm.ewma_effective_days(0.97, 0.01)) == 151


def test_golden_fz0_is_the_fz_class_with_g1_zero_and_g2_minus_one_over_x() -> None:
    for y, v, e, a in [(-0.03, -0.02, -0.025, 0.01), (0.01, -0.02, -0.03, 0.025), (-0.05, -0.04, -0.05, 0.025),
                       (-0.001, -0.02, -0.02, 0.01)]:
        general = mm.fz_general(y, v, e, a, g1=lambda x: 0.0, g2=lambda x: -1.0 / x, cal_g2=lambda x: -math.log(-x))
        assert math.isclose(general, mm.fz0_return(y, v, e, a), abs_tol=1e-12)
        assert math.isclose(mm.fz0_loss(-y, -v, -e, a), mm.fz0_return(y, v, e, a), abs_tol=1e-12)


def test_golden_fz0_values_stated_in_the_contract_recompute() -> None:
    text = API.read_text(encoding="utf-8")
    cases = [(-0.03, -0.02, -0.025, 0.01), (0.01, -0.02, -0.03, 0.025)]
    for y, v, e, a in cases:
        val = mm.fz0_return(y, v, e, a)
        assert f"{val:.6f}" in text, (y, v, e, a, f"{val:.6f}")


def test_golden_pla_zone_boundaries() -> None:
    assert mm.pla_zone(0.81, 0.08) == "green" and mm.pla_zone(0.80, 0.05) == "amber" and mm.pla_zone(0.85, 0.09) == "amber"
    assert mm.pla_zone(0.69, 0.05) == "red" and mm.pla_zone(0.70, 0.05) == "amber" and mm.pla_zone(0.95, 0.121) == "red"
    assert mm.pla_zone(0.95, 0.12) == "amber"


def test_golden_kupiec_and_normal_values_stated_in_the_contract_recompute() -> None:
    text = API.read_text(encoding="utf-8")
    lr = mm.kupiec_lr(250, 5, 0.01)
    assert f"{lr:.6f}" in text
    var, es = mm.normal_var_es_loss(0.0, 1.0, 0.01)
    assert f"{var:.6f}" in text and f"{es:.6f}" in text
    z = mm.ND.inv_cdf(0.01)
    assert f"{mm.cornish_fisher_z(z, -0.5, 1.0):.6f}" in text
    w = mm.age_weights(0.98, 100)
    assert math.isclose(sum(w), 1.0, abs_tol=1e-12) and f"{w[0]:.6f}" in text
    assert f"{0.025 * (1 / 3 - 0.025 / 4):.10f}" in text  # Var(H_t) of Du-Escanciano at alpha 0.025
