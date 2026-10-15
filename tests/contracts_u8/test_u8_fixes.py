"""U8-S fixes: one test per finding F1 to F16 of review-u8-s-2026-10-13.md and per decision D1 to D3 of plans/contraste/units/U8-sizing.md
("Decisions after U8-S"). A planted defect is refused when the schema reports an error or a producer check
(tests/contracts_u8/producer_checks.py) reports a violation.
"""
from __future__ import annotations

import copy
import math
import re
from typing import Any

import pytest

import contract_schemas as cs
import market_math as mm
import producer_checks as pc
from test_u8_contracts import API, C11, C11M, C13, C13M, EXPECTED, ROOT, load, section

CHECKS = {C11: pc.c11_variant_violations, C11M: pc.c11_models_violations, C13: pc.c13_variant_violations, C13M: pc.c13_models_violations}


def refused(ref: str, doc: Any) -> bool:
    return bool(cs.errors(ref, doc)) or bool(CHECKS[ref](doc))


def committed(ref: str) -> list[tuple[str, dict]]:
    """The fixture and every committed document of the schema under data/derived/<case> (once the bakes land)."""
    case = ref.split("/")[0].upper()
    out = [("fixture", load(ref))]
    folder = ROOT / "data" / "derived" / case
    for p in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        doc = cs.load_json(p)
        try:
            if cs.schema_for_document(p, doc) == ref:
                out.append((p.name, doc))
        except cs.SelectionError:
            pass
    return out


@pytest.mark.parametrize("ref", list(CHECKS))
def test_f8_every_committed_document_passes_the_schema_and_the_producer_checks(ref: str) -> None:
    for name, doc in committed(ref):
        assert cs.errors(ref, doc) == [], name
        assert CHECKS[ref](doc) == [], name


# --- D1 / F1: the hyperparameter span -----------------------------------------------------------------------------


def test_d1_every_window_and_the_variant_use_the_d1_span() -> None:
    assert load(C11)["outputs"]["hyperparameters"]["fixed_on"] == {"start": "1995-01-01", "end": "2003-12-31"}
    for w in load(C11M)["fit"]["windows"]:
        assert w["fixed_on"] == {"start": "1995-01-01", "end": "2003-12-31"}, w["window_id"]


def test_d1_the_superseded_1995_2006_span_appears_nowhere() -> None:
    texts = [API.read_text(encoding="utf-8")]
    for ref in (C11, C11M, C13, C13M):
        texts.append((ROOT / "docs" / "contracts" / "fixtures" / ref.split("/")[0] / EXPECTED[ref].name).read_text(encoding="utf-8"))
    for p in (ROOT / "docs" / "contracts" / "schemas" / "c11").glob("*.json"):
        texts.append(p.read_text(encoding="utf-8"))
    catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")   # the U8 rows, merged at 0.11.000
    texts.append("\n".join(ln for ln in catalog.splitlines() if ln.startswith(("| c11-", "| c13-", "| engine-market-api"))))
    for t in texts:
        assert "1995-2006" not in t and "1995 to 2006" not in t
        assert not re.search(r'"fixed_on":\s*\{[^}]*2006-12-29', t, flags=re.S)
    assert "1995-01-01" in API.read_text(encoding="utf-8") and "2003-12-31" in API.read_text(encoding="utf-8")


def test_f1_the_open_item_about_the_calm_window_is_resolved_in_the_contract_text() -> None:
    text = API.read_text(encoding="utf-8")
    assert "overlaps the span 1995 to 2006" not in text
    assert "ends before 2007 and before the window they serve" not in text


# --- D2 / F2: the window dates ------------------------------------------------------------------------------------


def test_d2_the_models_fixture_carries_the_d2_dates() -> None:
    plan = {w["window_id"]: (w["start_date"], w["end_date"]) for w in load(C11M)["fit"]["windows"]}
    assert plan == pc.D2_DATES
    assert plan["fx-2008"] == ("2008-07-01", "2009-06-30")


@pytest.mark.parametrize("wid", pc.WINDOWS)
def test_f2_a_window_with_dates_other_than_d2_is_refused_in_the_models_and_the_variant(wid: str) -> None:
    for field, wrong in (("start_date", "2021-06-01"), ("end_date", "2030-01-01")):
        m = load(C11M)
        next(w for w in m["fit"]["windows"] if w["window_id"] == wid)[field] = wrong
        assert cs.errors(C11M, m) != [], (wid, field)
    v = load(C11)
    v["outputs"]["window"].update({"window_id": wid, "start_date": "2021-06-01"})
    assert cs.errors(C11, v) != [], wid


def test_f2_the_fx_2008_window_dated_2008_is_refused_and_a_correct_window_id_date_pair_is_accepted() -> None:
    v = load(C11)
    v["outputs"]["window"].update({"window_id": "fx-2008", "asset_class": "fx", "start_date": "2008-01-02", "end_date": "2008-12-31"})
    assert cs.errors(C11, v) != []
    v["outputs"]["window"].update({"start_date": "2008-07-01", "end_date": "2009-06-30"})
    assert cs.errors(C11, v) == []


def test_f2_a_window_id_with_the_wrong_asset_class_is_refused() -> None:
    v = load(C11)
    v["outputs"]["window"]["asset_class"] = "equity"
    assert cs.errors(C11, v) != []


def test_f2_six_copies_of_one_window_in_the_models_are_refused() -> None:
    m = load(C11M)
    m["fit"]["windows"] = [copy.deepcopy(m["fit"]["windows"][5]) for _ in range(6)]
    assert cs.errors(C11M, m) != []
    m = load(C11M)
    m["fit"]["windows"][0], m["fit"]["windows"][1] = m["fit"]["windows"][1], m["fit"]["windows"][0]
    assert cs.errors(C11M, m) != [], "the six windows are in the order of the SDD"


# --- D3 / F3: short windows ---------------------------------------------------------------------------------------


def test_f3_a_window_under_250_days_with_an_evaluated_traffic_light_is_refused() -> None:
    v = load(C11)
    v["outputs"]["window"].update({"window_id": "equity-2020", "asset_class": "equity", "start_date": "2020-02-03",
                                   "end_date": "2020-06-30", "n_forecast_days": 100})
    assert cs.errors(C11, v) != [], "100 forecast days with an evaluated 99 percent traffic light validates"
    for m in v["outputs"]["models"]:
        for lv in m["by_level"]:
            if lv["traffic_light"] is not None:
                lv["traffic_light"] = {"window_days": 250, "n_windows": 0, "max_rolling_exceedances": None, "final_rolling_exceedances": None,
                                       "final_zone": "not_evaluated", "days_green": None, "days_amber": None, "days_red": None,
                                       "reason": "fewer than 250 forecast days (MAR32.9 is defined on 250 observations)"}
    errs = cs.errors(C11, v)
    assert not any("traffic" in e or "final_zone" in e for e in errs), errs


def test_d3_a_window_of_250_days_or_more_with_a_not_evaluated_traffic_light_is_refused() -> None:
    v = load(C11)
    lv = v["outputs"]["models"][0]["by_level"][0]
    lv["traffic_light"] = {"window_days": 250, "n_windows": 0, "max_rolling_exceedances": None, "final_rolling_exceedances": None,
                           "final_zone": "not_evaluated", "days_green": None, "days_amber": None, "days_red": None, "reason": "x"}
    assert cs.errors(C11, v) != []


def test_d3_the_producer_check_requires_not_evaluated_under_250_grid_days() -> None:
    v = load(C11)
    n = 100
    o = v["outputs"]
    o["grid"]["dates"] = o["grid"]["dates"][:n]
    o["grid"]["estimation_start"] = o["grid"]["estimation_start"][:n]
    o["grid"]["estimation_end"] = o["grid"]["estimation_end"][:n]
    o["grid"]["realised_loss"]["loss"] = o["grid"]["realised_loss"]["loss"][:n]
    o["window"]["n_forecast_days"] = n
    for m in o["models"]:
        for lv in m["by_level"]:
            for k in ("var", "es"):
                lv[k] = lv[k][:n]
    assert any("D3" in x for x in pc.c11_variant_violations(v))


# --- F4: the sample ES ---------------------------------------------------------------------------------------------


def a0_tail_integral(returns: list[float], alpha: float) -> float:
    """(1/alpha) integral_0^alpha F^-1(u) du of the empirical quantile function, summed over its steps of width 1/N."""
    s, n = sorted(returns), len(returns)
    total = 0.0
    for i, r in enumerate(s):
        lo, hi = i / n, min((i + 1) / n, alpha)
        if hi > lo:
            total += r * (hi - lo)
    return total / alpha


def test_f4_the_sample_es_is_the_a0_tail_integral_when_alpha_n_is_not_an_integer() -> None:
    r = [-0.001 * i for i in range(1, 101)]
    for alpha in (0.05, 0.025, 0.01, 0.0125):
        var, es = mm.sample_var_es(r, alpha)
        assert math.isclose(es, a0_tail_integral(r, alpha), abs_tol=1e-12), alpha
    assert mm.sample_var_es(r, 0.025) == pytest.approx((-0.098, -0.0992), abs=1e-12)
    # HS-250: alpha N is 2.5 and 6.25, not integers
    r2 = [(-1) ** i * 0.0001 * (i + 1) for i in range(250)]
    for alpha in (0.01, 0.025):
        assert math.isclose(mm.sample_var_es(r2, alpha)[1], a0_tail_integral(r2, alpha), abs_tol=1e-12)


def test_f4_the_contract_states_the_fractional_atom_and_the_golden() -> None:
    body = section("conventions", "var_es_from_sample")
    assert "alpha N - (k - 1)" in body or "alpha * N - (k - 1)" in body
    assert "-0.0992" in body and "-0.098" in body
    assert "mean of the k\n  smallest" not in body


# --- F5: the KS boundary ------------------------------------------------------------------------------------------


def test_f5_a_30_step_gap_is_exactly_0_12_and_amber() -> None:
    hpl = [float(i) for i in range(250)]
    rtpl = [x + 29.5 for x in hpl]
    ks = mm.ks_statistic(hpl, rtpl)
    assert ks == 0.12 and not ks > 0.12
    assert mm.pla_zone(1.0, ks) == "amber"
    gaps = {a: mm.ks_statistic([float(i) for i in range(250)], [float(i) + a + 0.5 for i in range(250)]) for a in range(0, 60)}
    for a, k in gaps.items():
        assert k == (a + 1) / 250 if a + 1 <= 250 else True
    assert (mm.pla_zone(1.0, gaps[29]), mm.pla_zone(1.0, gaps[30])) == ("amber", "red")


def test_f5_the_contract_defines_ks_on_integer_counts() -> None:
    body = section("frtb", "pla_ks")
    assert "integer" in body and "/ 250" in body and "0.12000000000000002" in body
    assert "30-step" in body or "30 steps" in body


# --- F6: the traffic-light table is constant ----------------------------------------------------------------------


@pytest.mark.parametrize("row,field,value", [(5, "frtb_multiplier", 1.60), (4, "cumulative_probability_pct", 90.00), (5, "zone", "green"),
                                             (10, "us_multiplier", 3.00), (0, "exceptions", 1)])
def test_f6_a_changed_mar32_9_row_is_refused(row: int, field: str, value: Any) -> None:
    m = load(C11M)
    m["fit"]["traffic_light"]["rows"][row][field] = value
    assert cs.errors(C11M, m) != []


def test_f6_the_table_has_exactly_eleven_rows_and_fixed_window_and_confidence() -> None:
    m = load(C11M)
    m["fit"]["traffic_light"]["rows"].pop()
    assert cs.errors(C11M, m) != []
    m = load(C11M)
    m["fit"]["traffic_light"]["confidence"] = 0.975
    assert cs.errors(C11M, m) != []


# --- F7: the C13 models document ----------------------------------------------------------------------------------


def test_f7_c13_models_deficiency_plans_are_coupled_and_ordered() -> None:
    m = load(C13M)
    m["fit"]["deficiencies"][1]["planted"] = False
    assert cs.errors(C13M, m) != []
    m = load(C13M)
    for p in m["fit"]["deficiencies"]:
        p.update({"deficiency_id": "none", "planted": False, "intended_to_fail": "none"})
    assert cs.errors(C13M, m) != []
    m = load(C13M)
    m["fit"]["deficiencies"][0]["intended_to_fail"] = "ks"
    assert cs.errors(C13M, m) != []
    m = load(C13M)
    m["fit"]["deficiencies"][1], m["fit"]["deficiencies"][2] = m["fit"]["deficiencies"][2], m["fit"]["deficiencies"][1]
    assert cs.errors(C13M, m) != []


@pytest.mark.parametrize("alpha,limit", [(0.01, 13), (0.025, 31), (0.01, 30)])
def test_f7_a_desk_limit_that_is_not_the_mar32_18_limit_is_refused(alpha: float, limit: int) -> None:
    m = load(C13M)
    m["fit"]["desk_limits"][0 if alpha == 0.025 else 1].update({"alpha": alpha, "limit_exceptions": limit})
    assert cs.errors(C13M, m) != []


# --- F8: identities on every document -----------------------------------------------------------------------------


def _mut(ref: str, fn) -> dict:
    doc = load(ref)
    fn(doc)
    return doc


F8_PLANTS = [
    (C11, lambda d: d["outputs"]["models"][0]["by_level"][0].update(es_status="not-forecast")),
    (C11, lambda d: d["outputs"]["models"][1]["by_level"][0].update(es_status="not-forecast")),
    (C11, lambda d: d["outputs"]["models"][0]["by_level"][0].update(var=d["outputs"]["models"][0]["by_level"][0]["var"][:-1])),
    (C11, lambda d: d["outputs"]["models"][0]["by_level"][0]["traffic_light"].update(final_zone="green", final_rolling_exceedances=12)),
    (C11, lambda d: d["outputs"]["models"][0].update(eligible=True)),
    (C11, lambda d: d["outputs"]["models"][1].update(failed_gates=["market.kupiec_pof"])),
    (C11, lambda d: d["outputs"]["models"][1]["by_level"][0].update(n_exceedances=99)),
    (C11, lambda d: d["outputs"]["grid"]["realised_loss"]["loss"].__setitem__(3, 0.5)),
    (C11, lambda d: d["outputs"]["data_status"]["missing_days"].update(count=1)),
    (C13, lambda d: d["outputs"]["example"].update(zone="green")),
    (C13, lambda d: d["outputs"]["pla"]["zones"]["overall"].update(green=1)),
    (C13, lambda d: d["outputs"]["desk_backtest"][0].update(n_over_limit=50)),
    (C13, lambda d: d["outputs"]["detection"].update(n_red=1)),
]


@pytest.mark.parametrize("i", range(len(F8_PLANTS)))
def test_f8_a_contradicting_document_is_refused(i: int) -> None:
    ref, fn = F8_PLANTS[i]
    assert refused(ref, _mut(ref, fn)), i


def test_f8_the_models_documents_run_their_checks() -> None:
    assert pc.c11_models_violations(load(C11M)) == [] and pc.c13_models_violations(load(C13M)) == []
    m = load(C11M)
    m["fit"]["windows"][2]["start_date"] = "2022-01-04"
    assert pc.c11_models_violations(m) != []


# --- F9: the variant id carries the truth -------------------------------------------------------------------------


def test_f9_a_variant_id_that_names_another_deficiency_or_window_is_refused() -> None:
    d13 = load(C13)
    d13["outputs"]["known_deficiency"].update(deficiency_id="stale-volatility", intended_to_fail="ks")
    assert refused(C13, d13)
    d11 = load(C11)
    d11["variant_id"] = "fixture-equity-2020"
    assert refused(C11, d11)


# --- F10 to F13, F15: the contract text and fields -------------------------------------------------------------


def test_f10_the_fhs_residual_is_demeaned() -> None:
    body = section("historical", "filtered_hs_var_es")
    assert "(r_t - mu_t) / sigma_t" in body and "z_t = r_t / sigma_t" not in body


def test_f11_the_dm_lag_rule_is_stated_and_recorded_in_the_comparison() -> None:
    body = section("scoring", "diebold_mariano")
    assert "lags = 0" in body and "one-step" in body and "UNVERIFIED" in body
    cmp = load(C11)["outputs"]["comparison"]
    assert cmp["hac_lags"] == 0 and all(r["hac_lags"] == cmp["hac_lags"] for r in cmp["dm"])
    bad = load(C11)
    del bad["outputs"]["comparison"]["hac_lags"]
    assert cs.errors(C11, bad) != []
    bad = load(C11)
    bad["outputs"]["comparison"]["dm"][0]["hac_lags"] = 5
    assert refused(C11, bad)


def test_f12_the_mcneil_frey_test_has_an_alpha_argument_and_a_numeric_golden() -> None:
    body = section("validation.market", "mcneil_frey_residual_test")
    assert "alpha: float" in body
    assert "0.00009999" in body and "1/(n_boot + 1)" in body


def test_f13_the_du_escanciano_conditional_light_names_the_zero_spread_case() -> None:
    body = section("validation.market", "du_escanciano_conditional")
    light = next(ln for ln in body.splitlines() if ln.startswith("- Light:"))
    assert "zero spread" in light


def test_f14_the_contract_makes_the_producer_checks_an_acceptance_check_of_the_bakes() -> None:
    text = API.read_text(encoding="utf-8")
    assert "pytest tests/contracts_u8" in text and "ADR-0074" in text


def test_f15_the_caviar_and_gas_starts_and_the_seed_are_required_hyperparameters() -> None:
    h = load(C11)["outputs"]["hyperparameters"]
    for key in ("caviar_n_starts", "gas_n_starts", "seed"):
        assert isinstance(h[key], int)
        bad = load(C11)
        del bad["outputs"]["hyperparameters"][key]
        assert cs.errors(C11, bad) != [], key


def test_f16_the_es_below_var_test_calls_a_check() -> None:
    src = (ROOT / "tests" / "contracts_u8" / "test_u8_contracts.py").read_text(encoding="utf-8")
    body = src[src.index("def test_es_below_var_is_caught"):]
    body = body[: body.index("\n\n\n")]
    assert "c11_variant_violations" in body


# --- D4: the calm window is the control window, asset class mixed ------------------------------------------------


@pytest.mark.parametrize("cls", ["equity", "rates", "fx"])
def test_d4_a_calm_window_of_another_class_is_refused_in_the_models_and_the_variant(cls: str) -> None:
    m = load(C11M)
    calm = next(w for w in m["fit"]["windows"] if w["window_id"] == "calm-2004-06")
    assert calm["asset_class"] == "mixed"
    calm["asset_class"] = cls
    assert cs.errors(C11M, m) != []
    v = load(C11)
    v["outputs"]["window"].update({"window_id": "calm-2004-06", "asset_class": cls, "start_date": "2004-01-02", "end_date": "2006-12-29"})
    assert cs.errors(C11, v) != []
    v["outputs"]["window"]["asset_class"] = "mixed"
    assert cs.errors(C11, v) == []
