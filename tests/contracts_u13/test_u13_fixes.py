"""U13-S fix round (u13-s-fixes-2026-10-19): one test group per finding F1 to F14 of the Opus review of the C18 contracts.

Each group plants the review's failing case as a document that changes one thing and shows it refused (or, for a true result the
review showed refused wrongly, accepted). The decisions of the main session (sizing "Decisions after the U13-S review", W1 to W6) are
the spec: signed charge-off rates with the identity link on RECI and RERES from 1991Q1; EC cited to dossier 04 l.652-653; the 4
percent cap on p2r; the market marginal converted by the normal quantile ratio and the square root of 250; the operational marginal
with an infinite-mean rule and bake-derived rate and asset scaling.
"""
from __future__ import annotations

import copy
import importlib
import math
from statistics import NormalDist

import pytest

import contract_schemas as cs
import test_u13_contracts as t

SC, AG, RV, MD = t.SC, t.AG, t.RV, t.MD
load, out, fit, set_at, drop_at = t.load, t.out, t.fit, t.set_at, t.drop_at
sm = t.sm


def bf():
    return importlib.import_module("build_fixtures")


def ok(ref: str, doc: dict) -> None:
    assert cs.errors(ref, doc) == [], cs.errors(ref, doc)[:3]
    assert sm().violations(doc) == [], sm().violations(doc)[:5]


def refused(ref: str, doc: dict, layer: str) -> None:
    if layer == "schema":
        assert cs.errors(ref, doc) != []
    else:
        assert cs.errors(ref, doc) == [], cs.errors(ref, doc)[:3]
        assert sm().violations(doc) != []


def r10(x: float) -> float:
    return round(x, 10)


def backcast_row(doc: dict, loan_type: str) -> dict:
    return next(r for r in doc["outputs"]["backcast"]["per_loan_type"] if r["fed_loan_type"] == loan_type)


def recompute_metrics(row: dict) -> None:
    """Rewrite a back-cast row's metrics from its quarters (the identities of the semantic checker)."""
    qs = row["quarters"]
    pred, real = [q["predicted"] for q in qs], [q["realised"] for q in qs]
    m = row["metrics"]
    m["rmse"] = r10(math.sqrt(sum((p - r) ** 2 for p, r in zip(pred, real)) / len(qs)))
    ip, ir = pred.index(max(pred)), real.index(max(real))
    m["peak_predicted"], m["peak_predicted_quarter"] = pred[ip], qs[ip]["quarter_end"]
    m["peak_realised"], m["peak_realised_quarter"] = real[ir], qs[ir]["quarter_end"]
    m["peak_timing_error_quarters"] = ip - ir


def row_of(doc: dict, test_id: str) -> dict:
    return next(r for r in doc["tests"] if r["test_id"] == test_id)


# ------------------------------------------------------------------------------------------------------------- F1


def test_f1_the_residential_back_cast_carries_the_boards_non_positive_quarters_and_validates() -> None:
    for key in t.SCENARIO_KEYS:
        doc = load(key)
        res = backcast_row(doc, "residential")
        assert sum(1 for q in res["quarters"] if q["realised"] <= 0) >= 20, "the Board's residential rate is non-positive in 23 of 24 quarters"
        ok(SC, doc)


def test_f1_plant_x3_a_true_negative_residential_rate_validates() -> None:
    doc = load("fed")
    row = backcast_row(doc, "residential")
    row["quarters"][0]["realised"] = -0.0003
    recompute_metrics(row)
    ok(SC, doc)


def test_f1_plant_x4_a_true_zero_2026_rate_validates_and_a_rate_of_one_does_not() -> None:
    doc = load("fed")
    cell = next(r for r in doc["outputs"]["backcast"]["descriptive_2026"][1]["realised_rates"] if r["fed_loan_type"] == "residential")
    assert cell["rate"] == 0.0
    ok(SC, doc)
    cell["rate"] = -0.0003
    ok(SC, doc)
    cell["rate"] = 1.0
    assert cs.errors(SC, doc) != []


def test_f1_a_projection_of_a_non_positive_identity_segment_validates_and_a_probit_projection_does_not() -> None:
    doc = load("fed")
    res = next(p for p in doc["outputs"]["satellites"]["fed_loan_types"] if p["fed_loan_type"] == "residential")
    assert res["link"] == "identity"
    assert all(q["link_value"] == q["rate"] for q in res["quarters"])
    assert min(q["rate"] for q in res["quarters"]) <= 0.0, "the identity projection may be non-positive: net recoveries"
    ok(SC, doc)
    ci = next(p for p in doc["outputs"]["satellites"]["fed_loan_types"] if p["fed_loan_type"] == "commercial-industrial")
    assert ci["link"] == "probit"
    bad = copy.deepcopy(doc)
    q = next(p for p in bad["outputs"]["satellites"]["fed_loan_types"] if p["fed_loan_type"] == "commercial-industrial")["quarters"][0]
    q["rate"], q["link_value"] = -0.001, -0.001
    assert cs.errors(SC, bad) != [], "a probit projection needs a rate in (0, 1)"
    bad = copy.deepcopy(doc)
    next(p for p in bad["outputs"]["satellites"]["fed_loan_types"] if p["fed_loan_type"] == "commercial-industrial")["link"] = "identity"
    assert cs.errors(SC, bad) != [], "only RECI and RERES use the identity link"


def test_f1_the_models_record_each_segments_link_and_window_start() -> None:
    sats = {s["fed_loan_type"]: s for s in fit()["satellites"]}
    for ty in ("commercial-real-estate", "residential"):
        assert sats[ty]["link"] == "identity"
        assert sats[ty]["sample_window"]["start"] == "1991-03-31"
    for ty in ("commercial-industrial", "credit-cards", "other-consumer"):
        assert sats[ty]["link"] == "probit"
        assert sats[ty]["sample_window"]["start"] == "1985-03-31"
    assert sats["commercial-real-estate"]["non_positive_quarters_in_window"] == 13
    assert sats["residential"]["non_positive_quarters_in_window"] == 6
    assert sats["commercial-industrial"]["non_positive_quarters_in_window"] == 0
    assert sats["residential"]["n_obs"] == 115 and sats["commercial-industrial"]["n_obs"] == 139


@pytest.mark.parametrize("ty,index", [("commercial-real-estate", 1), ("residential", 2)])
def test_f1_a_window_that_starts_before_1991q1_for_reci_or_reres_is_refused(ty: str, index: int) -> None:
    for start in ("1985-03-31", "1990-12-31", "1990-03-31"):
        doc = set_at(load("models"), f"fit/satellites/{index}/sample_window/start", start)
        assert cs.errors(MD, doc) != [], f"{ty} window starting {start}"
    ok_doc = set_at(load("models"), f"fit/satellites/{index}/sample_window/start", "1991-03-31")
    assert cs.errors(MD, ok_doc) == []
    late = set_at(load("models"), f"fit/satellites/{index}/sample_window/start", "1991-06-30")
    assert cs.errors(MD, late) != [], "a start other than the first available quarter is a finding"
    for scenario in t.SCENARIO_KEYS:
        bad = set_at(load(scenario), f"outputs/backcast/per_loan_type/{index}/fit_window/start", "1985-03-31")
        assert cs.errors(SC, bad) != [], scenario


def test_f1_a_probit_or_logit_fit_on_a_non_positive_window_is_refused() -> None:
    for link_name in ("probit", "logit"):
        doc = load("models")
        s = doc["fit"]["satellites"][2]   # residential
        s["link"] = link_name
        assert cs.errors(MD, doc) != [], link_name
    doc = load("models")
    doc["fit"]["satellites"][0]["non_positive_quarters_in_window"] = 3     # CI with a probit link
    assert cs.errors(MD, doc) != [], "a probit fit on a window that holds a non-positive quarter"
    doc = load("models")
    doc["fit"]["satellites"][0]["link"] = "identity"
    assert cs.errors(MD, doc) != [], "CI keeps the probit link"


def test_f1_the_back_cast_link_follows_the_models_link() -> None:
    docs = {k: load(k) for k in t.ALL}
    assert sm().cross_violations(docs) == []
    assert backcast_row(docs["fed"], "residential")["link"] == "identity"
    docs["fed"]["outputs"]["backcast"]["per_loan_type"][0]["link"] = "logit"
    assert sm().cross_violations(docs) != []


def test_f1_the_stress_contract_takes_the_link_as_an_argument_and_refuses_probit_on_a_non_positive_rate() -> None:
    text = t.STRESS_API.read_text(encoding="utf-8")
    sec = t.api_sections(t.STRESS_API)
    fit_sec = sec["riskvalidation.stress.satellites.fit_satellite"]
    assert '"identity"' in fit_sec and "non-positive" in fit_sec and "net recoveries" in text
    assert "a probit or logit fit on a non-positive rate" in fit_sec.replace("\n", " ")
    assert "05 l.399" in text and "1991Q1" in text
    assert '"identity"' in sec["riskvalidation.stress.satellites.link"]
    assert '"identity"' in sec["riskvalidation.stress.satellites.inverse_link"]


# ------------------------------------------------------------------------------------------------------------- F2


def test_f2_economic_capital_cites_dossier_04_lines_652_to_653() -> None:
    text = t.AGG_API.read_text(encoding="utf-8")
    assert "04 l.652-653" in text and "Capital basis (this contract's definition" not in text
    for name in ("variant-scenario", "variant-aggregation"):
        schema = cs.load_json(t.SCHEMAS / "c18" / f"{name}.schema.json")
        basis = [v for k, v in schema["$defs"].items() if k == "c18Aggregation"][0]["properties"]["capital_basis"]["description"]
        assert "04 l.652-653" in basis


# ------------------------------------------------------------------------------------------------------------- F3


def _t_row(doc: dict, nu: float) -> dict:
    return next(r for r in doc["outputs"]["aggregation"]["band"] if r["method"] == "t-copula" and r["nu"] == nu)


def _above_sum(doc: dict) -> dict:
    total = doc["outputs"]["aggregation"]["headline"]["capital_clp_m"]
    row = _t_row(doc, 30.0)
    row["capital_clp_m"] = round(total * 1.02, 6)
    row["diversification_factor"] = r10(row["capital_clp_m"] / total)
    return doc


def test_f3_plant_s22_a_band_row_above_the_simple_sum_is_a_true_result_when_its_test_row_is_red() -> None:
    doc = _above_sum(load("fed"))
    row_of(doc, "aggregation.diversification_sign")["light"] = "red"
    ok(SC, doc)
    amber = _above_sum(load("fed"))
    row_of(amber, "aggregation.diversification_sign")["light"] = "amber"
    ok(SC, amber)


def test_f3_a_band_row_above_the_sum_with_a_green_or_unevaluated_test_row_is_refused() -> None:
    for light in ("green", "not_evaluated"):
        doc = _above_sum(load("fed"))
        row_of(doc, "aggregation.diversification_sign")["light"] = light
        refused(SC, doc, "semantic")


def test_f3_a_red_diversification_row_without_the_condition_is_refused() -> None:
    doc = load("fed")
    row_of(doc, "aggregation.diversification_sign")["light"] = "red"
    refused(SC, doc, "semantic")


def _stressed_below(doc: dict) -> dict:
    st = doc["outputs"]["correlation_stress"]["aggregation"]
    row = next(r for r in st["band"] if r["method"] == "t-copula" and r["nu"] == 30.0)
    base = next(r for r in doc["outputs"]["aggregation"]["band"] if r["method"] == "t-copula" and r["nu"] == 30.0)
    row["capital_clp_m"] = round(base["capital_clp_m"] * 0.99, 6)
    row["diversification_factor"] = r10(row["capital_clp_m"] / st["headline"]["capital_clp_m"])
    return doc


def test_f3_plant_a5_a_stressed_capital_below_the_base_is_a_true_result_when_its_test_row_is_red() -> None:
    doc = _stressed_below(load("aggregation"))
    row_of(doc, "aggregation.correlation_stress")["light"] = "red"
    ok(AG, doc)
    green = _stressed_below(load("aggregation"))
    refused(AG, green, "semantic")


def test_f3_plant_m8_a_wrong_sign_coefficient_is_valid_when_the_sensitivity_row_is_red_in_every_scenario_document() -> None:
    docs = {k: load(k) for k in t.ALL}
    t.flip_sign(docs["models"])
    assert cs.errors(MD, docs["models"]) == []
    assert sm().violations(docs["models"]) == [], "the models document alone is never refused for a sign"
    assert sm().cross_violations(docs) != [], "the validation row must report it"
    for k in t.SCENARIO_KEYS:
        row_of(docs[k], "stress.sensitivity_monotonicity")["light"] = "red"
    assert sm().cross_violations(docs) == []


def test_f3_the_checker_no_longer_holds_the_three_refusals() -> None:
    src = (t.THIS.parent / "semantics.py").read_text(encoding="utf-8")
    assert "a diversification benefit with the wrong sign" not in src
    assert "falls when a correlation is raised" not in src
    assert "has not its expected sign" not in src


# ------------------------------------------------------------------------------------------------------------- F4


def test_f4_the_cap_of_four_percent_is_on_p2r_and_a_c_p2_above_it_is_a_true_result() -> None:
    doc = load("models")
    doc["fit"]["named_parameters"]["c_p2"]["value"] = 0.05
    ok(MD, doc)
    bad = load("models")
    bad["fit"]["bank_anchors"]["chilean_stack"]["p2r"] = 0.05
    assert cs.errors(MD, bad) != []
    sec = t.api_sections(t.STRESS_API)["riskvalidation.stress.capital.internal_capital_target"].replace("\n", " ")
    assert "`p2r` above the 4 percent cap" in sec
    assert "`c_p2` has no cap" in sec
    assert "`c_p2` above the 4 percent cap" not in sec


# ------------------------------------------------------------------------------------------------------------- F5


def test_f5_every_scenario_document_carries_the_severity_block_one_row_per_path_variable() -> None:
    for key in t.SCENARIO_KEYS:
        doc = load(key)
        sev = doc["outputs"]["severity"]
        paths = doc["outputs"]["scenario"]["paths"]
        assert [r["variable"] for r in sev["rows"]] == [p["variable"] for p in paths]
        assert all(r["is_stress"] == (key != "baseline") for r in sev["rows"])
        for field in ("peak", "reference_episode"):
            pass
        assert cs.errors(SC, drop_at(copy.deepcopy(doc), "outputs/severity")) != []
        for field in ("path_peak_deviation", "history_peak_deviation", "history_window", "history_source", "ratio", "is_stress", "path_peak_quarter"):
            assert cs.errors(SC, drop_at(copy.deepcopy(doc), f"outputs/severity/rows/0/{field}")) != [], field
        ok(SC, doc)


def test_f5_the_severity_figures_are_recomputed_from_the_transposed_path() -> None:
    doc = load("fed")
    doc["outputs"]["severity"]["rows"][0]["ratio"] += 0.1
    refused(SC, doc, "semantic")
    doc = load("fed")
    doc["outputs"]["severity"]["rows"][0]["path_peak_deviation"] += 0.5
    refused(SC, doc, "semantic")
    doc = load("fed")
    doc["outputs"]["severity"]["rows"][1]["is_stress"] = False
    refused(SC, doc, "semantic")
    doc = load("fed")
    doc["outputs"]["severity"]["rows"] = doc["outputs"]["severity"]["rows"][:2]
    refused(SC, doc, "semantic")
    doc = load("fed")
    doc["outputs"]["severity"]["rows"][0]["history_peak_deviation"] = 0.0
    assert cs.errors(SC, doc) != []


# ------------------------------------------------------------------------------------------------------------- F6

REQUIRED = {
    SC: t.__dict__["SCENARIO_KEYS"] and None,
}


def _required(ref: str) -> list[str]:
    mod = bf()
    if ref == SC:
        return list(mod.SCENARIO_TESTS)
    if ref == AG:
        return ["aggregation.simple_sum_and_variance_covariance", "aggregation.copula_choice_sensitivity", "aggregation.worst_case_bracket",
                "aggregation.correlation_stress", "aggregation.diversification_sign", "aggregation.horizon_confidence_consistency",
                "aggregation.elliptical_mc_agreement", "aggregation.rosenberg_schuermann_reference", "portfolio.euler_additivity"]
    return ["stress.reverse_solution_check"]


@pytest.mark.parametrize("key", ["baseline", "fed", "aggregation", "reverse"])
def test_f6_a_document_without_a_required_test_row_is_refused(key: str) -> None:
    ref = t.FILES[key][0]
    ids = _required(ref)
    assert len(ids) >= 1
    for test_id in ids:
        doc = load(key)
        doc["tests"] = [r for r in doc["tests"] if r["test_id"] != test_id]
        assert cs.errors(ref, doc) != [], f"{key}: {test_id} is optional"
    for key2 in ("baseline", "eba", "fed", "ngfs"):
        doc = load(key2)
        doc["tests"] = []
        assert cs.errors(SC, doc) != [], "X2: an empty tests array"


# ------------------------------------------------------------------------------------------------------------- F7


def test_f7_the_market_marginal_converts_the_level_and_the_horizon_by_two_named_conventions() -> None:
    z = NormalDist()
    level = z.inv_cdf(0.999) / z.inv_cdf(0.99)
    named = fit()["named_parameters"]["market_horizon_scaling"]
    assert named["label"] == "convention"
    assert named["level_factor"]["label"] == "convention" and named["horizon_factor"]["label"] == "convention"
    assert named["level_factor"]["value"] == pytest.approx(level, abs=1e-9)
    assert named["horizon_factor"]["value"] == pytest.approx(math.sqrt(250), abs=1e-9)
    assert named["value"] == pytest.approx(level * math.sqrt(250), abs=1e-8)
    assert (named["source_confidence_level"], named["source_horizon_days"], named["trading_days_per_year"]) == (0.99, 1, 250)
    market = out("baseline")["aggregation"]["marginals"][1]
    assert market["scaling"]["parameters"][1] == named
    doc = load("models")
    for field in ("level_factor", "horizon_factor", "source_confidence_level", "source_horizon_days", "trading_days_per_year"):
        assert cs.errors(MD, drop_at(copy.deepcopy(doc), f"fit/named_parameters/market_horizon_scaling/{field}")) != [], field
    bad = set_at(copy.deepcopy(doc), "fit/named_parameters/market_horizon_scaling/level_factor/label", "case assumption")
    assert cs.errors(MD, bad) != [], "both factors are conventions"
    ok(MD, doc)


@pytest.mark.parametrize("path,value", [
    ("fit/named_parameters/market_horizon_scaling/level_factor/value", 1.0),
    ("fit/named_parameters/market_horizon_scaling/horizon_factor/value", 15.8114),
    ("fit/named_parameters/market_horizon_scaling/value", 15.8114),
])
def test_f7_a_factor_that_is_not_the_stated_convention_is_refused(path: str, value: float) -> None:
    refused(MD, set_at(load("models"), path, value), "semantic")


def test_f7_a_market_marginal_without_its_conversion_is_refused() -> None:
    doc = load("baseline")
    m = doc["outputs"]["aggregation"]["marginals"][1]
    m["scaling"]["parameters"] = m["scaling"]["parameters"][:1]
    assert cs.errors(SC, doc) != []


# ------------------------------------------------------------------------------------------------------------- F8


def test_f8_the_models_name_the_c17_parameter_set_of_the_operational_marginal() -> None:
    src = {m["risk"]: m for m in fit()["marginal_sources"]}
    op = src["operational"]["c17_parameter_set"]
    assert op["document"] == "C17 models-generator" and op["variant_id"] in ("xi-0-6", "xi-0-8", "xi-0-96", "xi-1-1")
    assert op["assets_eur_bn"] == 50.0
    for r in ("credit", "market", "irrbb"):
        assert src[r]["c17_parameter_set"] is None
    doc = load("models")
    i = [m["risk"] for m in doc["fit"]["marginal_sources"]].index("operational")
    assert cs.errors(MD, set_at(copy.deepcopy(doc), f"fit/marginal_sources/{i}/c17_parameter_set", None)) != []
    bad = set_at(copy.deepcopy(doc), f"fit/marginal_sources/{i}/c17_parameter_set/tail_index", 1.1)
    refused(MD, bad, "semantic")


def test_f8_an_infinite_mean_operational_marginal_reports_el_undefined_and_ec_is_the_var() -> None:
    mod = bf()
    docs = {k: mod.scenario_doc(k, op_infinite=True) for k in ("baseline", "eba", "fed", "ngfs")}
    docs["aggregation"] = mod.aggregation_doc(op_infinite=True)
    docs["reverse"] = load("reverse")
    docs["models"] = mod.models_doc(op_infinite=True)
    op = docs["fed"]["outputs"]["aggregation"]["marginals"][3]
    assert op["el_clp_m"] is None and op["el_status"] == "undefined (infinite mean)"
    assert op["ec_clp_m"] == op["var_clp_m"] and op["ec_basis"] == "var-alone-infinite-mean" and op["ec_label"] is not None
    for k in ("baseline", "eba", "fed", "ngfs"):
        ok(SC, docs[k])
    ok(AG, docs["aggregation"])
    ok(MD, docs["models"])
    assert sm().cross_violations(docs) == []
    # an EC computed with an infinite expected loss is refused
    bad = copy.deepcopy(docs["fed"])
    m = bad["outputs"]["aggregation"]["marginals"][3]
    m["el_clp_m"], m["el_status"], m["ec_basis"], m["ec_label"] = 20000.0, "finite", "var-less-el", None
    m["ec_clp_m"] = round(m["var_clp_m"] - 20000.0, 6)
    d2 = {**docs, "fed": bad}
    assert cs.errors(SC, bad) == [] and sm().cross_violations(d2) != [], "a finite EL on an infinite-mean severity"
    bad = copy.deepcopy(docs["fed"])
    bad["outputs"]["aggregation"]["marginals"][3]["ec_clp_m"] -= 100.0
    refused(SC, bad, "semantic")
    bad = copy.deepcopy(docs["fed"])
    bad["outputs"]["aggregation"]["marginals"][3]["ec_label"] = None
    assert cs.errors(SC, bad) != []
    bad = copy.deepcopy(docs["fed"])
    bad["outputs"]["aggregation"]["marginals"][3]["el_clp_m"] = 1.0
    assert cs.errors(SC, bad) != [], "undefined means no number"
    bad = copy.deepcopy(docs["fed"])
    m = bad["outputs"]["aggregation"]["marginals"][0]
    m["el_clp_m"], m["el_status"], m["ec_basis"], m["ec_label"] = None, "undefined (infinite mean)", "var-alone-infinite-mean", m["scaling"]["statement"]
    assert cs.errors(SC, bad) != [], "only the operational marginal can have an infinite mean"
    bad = copy.deepcopy(docs["fed"])
    bad["outputs"]["aggregation"]["marginals"][0]["el_clp_m"] = None
    assert cs.errors(SC, bad) != [], "a finite status needs its number"


def test_f8_a_finite_mean_set_cannot_carry_an_undefined_el_and_xi_one_or_more_must() -> None:
    docs = {k: load(k) for k in t.ALL}
    assert docs["fed"]["outputs"]["aggregation"]["marginals"][3]["el_status"] == "finite"
    docs["models"]["fit"]["marginal_sources"][3]["c17_parameter_set"].update({"variant_id": "xi-1-1", "tail_index": 1.1, "infinite_mean": True})
    assert sm().violations(docs["models"]) == []
    assert sm().cross_violations(docs) != [], "the documents still hold a finite EL on an infinite-mean set"
    bad = load("models")
    bad["fit"]["marginal_sources"][3]["c17_parameter_set"].update({"tail_index": 1.1})
    refused(MD, bad, "semantic")


def test_f8_the_conversion_rate_and_the_asset_scaling_are_derived_at_bake_time() -> None:
    named = fit()["named_parameters"]
    fx, assets = named["operational_conversion_rate"], named["asset_scaling"]
    assert fx["derivation"]["kind"] == "observed-exchange-rate" and fx["derivation"]["pair"] == "EUR/CLP"
    assert "Banco Central de Chile" in fx["derivation"]["source"] and fx["derivation"]["source_url"].startswith("https://si3.bcentral.cl")
    assert fx["derivation"]["observation_date"] <= fit()["bank"]["as_of"]
    assert assets["derivation"]["kind"] == "asset-ratio"
    d = assets["derivation"]
    assert assets["value"] == pytest.approx(d["banco_andino_assets_clp_m"] / (d["c17_bank_assets_eur_m"] * fx["value"]), rel=1e-6)
    assert d["c17_bank_assets_eur_m"] == 50_000.0
    doc = load("models")
    for path in ("operational_conversion_rate/derivation", "asset_scaling/derivation", "operational_conversion_rate/derivation/observation_date",
                 "asset_scaling/derivation/banco_andino_assets_clp_m"):
        assert cs.errors(MD, drop_at(copy.deepcopy(doc), f"fit/named_parameters/{path}")) != [], path
    refused(MD, set_at(load("models"), "fit/named_parameters/operational_conversion_rate/derivation/observation_date", "2027-01-01"), "semantic")
    refused(MD, set_at(load("models"), "fit/named_parameters/asset_scaling/value", 0.5), "semantic")
    refused(MD, set_at(load("models"), "fit/named_parameters/operational_conversion_rate/value", -1.0), "schema")


def test_f8_the_aggregation_contract_states_the_infinite_mean_rule() -> None:
    text = t.AGG_API.read_text(encoding="utf-8").replace("\n", " ")
    assert "undefined (infinite mean)" in text and "05 l.482" in text and "EC is the VaR alone" in text
    assert "z_0.999 / z_0.99" in text and "sqrt(250)" in text


# ------------------------------------------------------------------------------------------------------------- F9 to F14


def test_f9_the_api_row_says_which_version_the_integration_branch_bumps_to() -> None:
    text = t.ROWS.read_text(encoding="utf-8")
    line = next(ln for ln in text.splitlines() if ln.startswith("| api |"))
    assert "6.1.0" in line and "task/0-13-000-wave2" in line and "6.0.0" in line and "next minor" not in line


def test_f10_a_baseline_scenario_served_by_another_provider_than_the_fed_is_refused() -> None:
    for provider in ("eba-esrb", "ngfs"):
        assert cs.errors(SC, set_at(load("baseline"), "outputs/scenario/provider", provider)) != [], provider
    assert cs.errors(SC, load("baseline")) == []


@pytest.mark.parametrize("start,end", [(2030, 2032), (2031, 2034), (2032, 2034), (2031, 2036)])
def test_f11_the_ngfs_policy_window_is_2031_to_2033(start: int, end: int) -> None:
    doc = load("ngfs")
    doc["outputs"]["scenario"]["policy_shock_window"].update({"start_year": start, "end_year": end})
    assert cs.errors(SC, doc) != []


def test_f12_the_ngfs_gdp_transposition_is_the_growth_of_the_level_path_and_is_checked() -> None:
    doc = load("ngfs")
    gdp = next(i for i, p in enumerate(doc["outputs"]["scenario"]["paths"]) if p["level_rule"]["kind"] == "baseline-times-percent-deviation")
    for k in (0, 5, 11):
        bad = copy.deepcopy(doc)
        bad["outputs"]["scenario"]["paths"][gdp]["transposed"][k]["value"] = 9.9
        refused(SC, bad, "semantic")
    text = t.STRESS_API.read_text(encoding="utf-8").replace("\n", " ")
    assert "level_y / level_(y-1) - 1" in text


def test_f13_a_negative_lower_bound_is_a_signed_capital_and_a_negative_other_row_is_not() -> None:
    doc = load("fed")
    agg = doc["outputs"]["aggregation"]
    total = agg["headline"]["capital_clp_m"]
    low = next(r for r in agg["band"] if r["method"] == "lower-bound")
    low["capital_clp_m"] = -1000.0
    low["diversification_factor"] = r10(-1000.0 / total)
    mr = agg["model_risk"]["barrieu_scandolo"]
    mr["rho_min_clp_m"] = -1000.0
    hi, x0 = mr["rho_max_clp_m"], mr["rho_x0_clp_m"]
    mr["rm"] = r10((hi - x0) / (hi + 1000.0))
    ok(SC, doc)
    bad = load("fed")
    row = next(r for r in bad["outputs"]["aggregation"]["band"] if r["method"] == "variance-covariance")
    row["capital_clp_m"] = -5.0
    assert cs.errors(SC, bad) != []
    text = t.AGG_API.read_text(encoding="utf-8").replace("\n", " ")
    assert "signed" in text and "may be negative" in text


def test_f14_the_band_invariant_names_its_rows_and_says_reported_not_enforced() -> None:
    sec = t.api_sections(t.AGG_API)["riskvalidation.aggregation.band.Band"].replace("\n", " ")
    assert "reported, not enforced" in sec
    assert "variance-covariance, Gaussian and t rows" in sec
    assert "the diversified rows are `<= headline`" not in sec
