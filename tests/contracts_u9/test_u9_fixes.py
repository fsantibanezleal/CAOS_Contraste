"""U9-S fix round (brief u9-s-fixes-2026-10-19): the two blockers, the eleven majors and the fifteen minors of the Opus review of the
C12 and regulatory contracts, as tests.

Every defect the review planted in a committed fixture and the contracts ACCEPTED is planted here again and must be refused by the
schema or by the checker a bake calls; where a rule is the checker's, the plant also names the message it expects, so a plant
refused only incidentally does not pass. The review's failing cases of B-1, B-2 and M1 to M11 and the minors that have one follow.
Independent of semantics.py where a number is checked: the formulas are written again from the dossiers and the BIS page.
"""
from __future__ import annotations

import copy
import math
import re
from pathlib import Path
from statistics import NormalDist
from typing import Any, Callable

import pytest

import contract_schemas as cs
import semantics as sm
import u9_fixtures as fx
from test_u9_contracts import C12, C12M, CCR_API, FILES, REG, REG_API, ROOT, ROWS, VARIANTS, ccr_key, load, reg_key, sections

CHANGES_FIX = ROOT / "changes" / "U9-S.md"


# --- helpers ------------------------------------------------------------------------------------------------------------


def trade_tuples(doc: dict) -> list[tuple]:
    return [(t["trade_id"], t["notional"]["amount"], t["fixed_rate"], t["side"], t["maturity_years"]) for t in doc["outputs"]["book"]["trades"]]


def rebuild_sa(doc: dict, trades: list[tuple] | None = None, mpor: Any = "keep") -> None:
    """Replace the SA-CCR block by a consistent one built from other trade terms or another MPoR, and make the BA-CVA and the
    regulatory comparison follow its EAD, so only the planted defect remains."""
    o = doc["outputs"]
    sa = o["sa_ccr"]
    new = fx.sa_block(trades or trade_tuples(doc), sa["mpor_business_days"] if mpor == "keep" else mpor,
                      sa["v"]["amount"], sa["c"]["amount"], sa["th"]["amount"], sa["mta"]["amount"], sa["nica"]["amount"])
    o["sa_ccr"] = new
    rebuild_ba(doc, ead=new["ead"]["amount"])
    rg = o["regulatory_comparison"]
    rg["sa_ccr_ead"]["amount"] = new["ead"]["amount"]
    rg["sa_ccr_over_alpha_eepe"] = new["ead"]["amount"] / rg["alpha_times_eepe"]["amount"]


def rebuild_ba(doc: dict, rw: float | None = None, ead: float | None = None) -> None:
    ba = doc["outputs"]["ba_cva"]
    cp = ba["counterparties"][0]
    if rw is not None:
        cp["risk_weight"] = rw
    if ead is not None:
        cp["ead"]["amount"] = ead
    cp["scva"] = sm.scva(cp["risk_weight"], cp["ead"]["amount"], cp["m_years"], cp["discount_factor"])
    ba["k_reduced"] = sm.k_reduced([cp["scva"]])
    ba["capital"]["amount"] = 0.65 * ba["k_reduced"]


def refused(ref: str, doc: dict, expect: str | None) -> None:
    errs = cs.errors(ref, doc)
    msgs = {C12: sm.check_c12, C12M: sm.check_c12_models, REG: sm.check_regulatory}[ref](doc)
    assert errs or msgs, "the planted defect is accepted by the schema and by the checker"
    if expect is not None:
        assert any(expect in m for m in msgs), f"no checker message names {expect!r}: {msgs[:4]} (schema: {errs[:2]})"


def not_applicable_block() -> dict:
    return copy.deepcopy(load("wrong-way-risk")["outputs"]["ore_reconciliation"])


# --- the plants the contracts accepted (review D3), c12 variants --------------------------------------------------------


def _end_mismatch(d: dict) -> None:
    tr = trade_tuples(d)
    tr[0] = (*tr[0][:4], 0.5)
    rebuild_sa(d, tr)


def _hedging_set_renamed(d: dict) -> None:
    d["outputs"]["sa_ccr"]["hedging_sets"][0]["hedging_set"] = "EUR"


def _sa_notional(d: dict) -> None:
    tr = trade_tuples(d)
    tr[0] = (tr[0][0], tr[0][1] / 2, *tr[0][2:])
    rebuild_sa(d, tr)


def _sa_mpor5(d: dict) -> None:
    rebuild_sa(d, mpor=5)


def _sa_unmargined(d: dict) -> None:
    rebuild_sa(d, mpor=None)


def _last_ee_negative(d: dict) -> None:
    d["outputs"]["exposure"]["ee"]["values"][-1] = -1.0


def _first_pfe_negative(d: dict) -> None:
    d["outputs"]["exposure"]["pfe"]["values"][0] = -1.0


def _ee_ten_times(d: dict) -> None:
    ee = d["outputs"]["exposure"]["ee"]
    ee["values"] = [v * 10 for v in ee["values"]]


def _ws_scaled(d: dict) -> None:
    g = d["outputs"]["girr"]
    g["weighted_sensitivities"] = [x * 1e4 for x in g["weighted_sensitivities"]]


def _undivided(d: dict) -> None:
    d["outputs"]["girr"]["delta_charge_undivided"]["amount"] *= 1.1


def _buckets_tripled(d: dict) -> None:
    g = d["outputs"]["girr"]
    for s in g["scenarios"]:
        s["k_b"] *= 3
    g["delta_charge"]["amount"] = max(s["k_b"] for s in g["scenarios"])
    g["delta_charge_undivided"]["amount"] = math.sqrt(2) * g["delta_charge"]["amount"]


def _ba_rw(d: dict) -> None:
    rebuild_ba(d, rw=0.03)


def _ba_ead_half(d: dict) -> None:
    rebuild_ba(d, ead=d["outputs"]["sa_ccr"]["ead"]["amount"] / 2)


def _ore_na(d: dict) -> None:
    d["outputs"]["ore_reconciliation"] = not_applicable_block()


def _alpha_one(d: dict) -> None:
    d["outputs"]["initial_margin"]["alpha"] = 1.0


def _dim_negative(d: dict) -> None:
    d["outputs"]["initial_margin"]["dim"]["values"][2] = -1.0


def _pit_zero(d: dict) -> None:
    d["outputs"]["backtest"]["book_horizons"][0]["pits"][0] = 0.0


def _ore_eepe(d: dict) -> None:
    d["outputs"]["ore_reconciliation"]["ore_eepe"]["amount"] *= 1.5


def _ore_cva(d: dict) -> None:
    d["outputs"]["ore_reconciliation"]["ore_cva"]["amount"] *= 1.5


def _ore_dim(d: dict) -> None:
    v = d["outputs"]["ore_reconciliation"]["ore_dim"]["values"]
    d["outputs"]["ore_reconciliation"]["ore_dim"]["values"] = [x * 2 for x in v]


def _ore_dim_on_netting(d: dict) -> None:
    d["outputs"]["ore_reconciliation"]["ore_dim"] = copy.deepcopy(load("with-im")["outputs"]["ore_reconciliation"]["ore_dim"])
    d["outputs"]["ore_reconciliation"]["dim_agreement"] = copy.deepcopy(load("with-im")["outputs"]["ore_reconciliation"]["dim_agreement"])


def _ore_dim_missing(d: dict) -> None:
    d["outputs"]["ore_reconciliation"]["ore_dim"] = None
    d["outputs"]["ore_reconciliation"]["dim_agreement"] = None


def _ore_eepe_missing(d: dict) -> None:
    del d["outputs"]["ore_reconciliation"]["ore_eepe"]


def _delta_string(d: dict) -> None:
    d["outputs"]["sa_ccr"]["trades"][0]["delta"] = "1"


def _eff_maturity(d: dict) -> None:
    d["outputs"]["regulatory_comparison"]["effective_maturity_years"] = 0.5


def _im_calendar(d: dict) -> None:
    d["outputs"]["initial_margin"]["mpor_calendar_days"] = 10


def _largest_bw(d: dict) -> None:
    d["outputs"]["wrong_way_risk"]["largest_b_w"] *= 2


def _wwr_named_grid(d: dict) -> None:
    d["outputs"]["named_parameters"]["wwr_b_grid"]["value"] = [0.0, 0.01, 0.02, 0.04]


def _pfe_peak(d: dict) -> None:
    d["outputs"]["calibration_sensitivity"][1]["pfe_peak"]["amount"] *= 2


def _sens_without_ee(d: dict) -> None:
    del d["outputs"]["calibration_sensitivity"][0]["ee"]


def _time_grid_named(d: dict) -> None:
    d["outputs"]["named_parameters"]["time_grid_years"]["value"] = [0.25, 0.5]


def _paths_per_date(d: dict) -> None:
    d["outputs"]["backtest"]["paths_per_date"] = 10


def _csa_mpor5(d: dict) -> None:
    d["outputs"]["collateral"]["csa"]["mpor_business_days"] = 5


def _ore_ee_negative(d: dict) -> None:
    d["outputs"]["ore_reconciliation"]["ore_ee"]["values"][0] = -1.0


def _spread_zero_all(d: dict) -> None:
    for b in d["outputs"]["cva_dva"]["buckets"]:
        b["spread"] = 0.0


def _girr_s_per_bp(d: dict) -> None:
    """The sensitivities as the PV01 per basis point (B-1): 10^4 smaller, the weighted values left as published."""
    g = d["outputs"]["girr"]
    g["sensitivities"] = [x * 1e-4 for x in g["sensitivities"]]


PLANTS: list[tuple[str, str, Callable[[dict], None], str | None]] = [
    ("sa-ccr trade end_years differs from the book", "single-swap", _end_mismatch, "end_years"),
    ("sa-ccr trade notional differs from the book", "netting-set", _sa_notional, "notional"),
    ("sa-ccr hedging set renamed", "single-swap", _hedging_set_renamed, "hedging sets"),
    ("csa 10d sa-ccr mpor 5", "csa-mpor-10d", _sa_mpor5, None),
    ("csa 10d sa-ccr computed unmargined", "csa-mpor-10d", _sa_unmargined, "CSA"),
    ("csa 10d sa-ccr mpor below the floor in the csa", "csa-mpor-10d", _csa_mpor5, None),
    ("csa 10d ee negative at the last point", "csa-mpor-10d", _last_ee_negative, None),
    ("pfe negative at the first point", "csa-mpor-10d", _first_pfe_negative, None),
    ("csa 10d collateralised ee ten times the uncollateralised", "csa-mpor-10d", _ee_ten_times, "collateralised EE above"),
    ("girr weighted sensitivities scaled by 1e4", "single-swap", _ws_scaled, "weighted sensitivities"),
    ("girr sensitivities per basis point, not divided by 0.0001", "single-swap", _girr_s_per_bp, "weighted sensitivities"),
    ("girr undivided charge not sqrt(2) times the divided one", "single-swap", _undivided, "undivided"),
    ("girr bucket charges tripled", "single-swap", _buckets_tripled, "bucket charge"),
    ("ba-cva risk weight 0.03 for financials", "single-swap", _ba_rw, "MAR50.16"),
    ("ba-cva ead half the sa-ccr ead", "single-swap", _ba_ead_half, "EAD"),
    ("single-swap ore not-applicable", "single-swap", _ore_na, None),
    ("netting-set ore not-applicable", "netting-set", _ore_na, None),
    ("csa 10d ore not-applicable", "csa-mpor-10d", _ore_na, None),
    ("csa 20d ore not-applicable", "csa-mpor-20d", _ore_na, None),
    ("with-im ore not-applicable", "with-im", _ore_na, None),
    ("with-im alpha 1.0 with quantile 0.99", "with-im", _alpha_one, "alpha"),
    ("with-im dim negative", "with-im", _dim_negative, None),
    ("with-im mpor in business days, not calendar days", "with-im", _im_calendar, "calendar"),
    ("pit equal to 0", "single-swap", _pit_zero, None),
    ("ore_eepe not recomputed from the ore ee", "netting-set", _ore_eepe, "ore_eepe"),
    ("ore_cva not recomputed from the ore discounted ee", "netting-set", _ore_cva, "ore_cva"),
    ("ore_eepe missing", "netting-set", _ore_eepe_missing, None),
    ("ore_dim doubled against the agreement", "with-im", _ore_dim, "ore_dim"),
    ("ore_dim on a variant without initial margin", "netting-set", _ore_dim_on_netting, None),
    ("ore_dim missing on the initial-margin variant", "with-im", _ore_dim_missing, None),
    ("ore ee negative", "netting-set", _ore_ee_negative, None),
    ("sa-ccr delta as a string", "single-swap", _delta_string, None),
    ("effective maturity below one year", "single-swap", _eff_maturity, None),
    ("wrong-way largest b w not the grid's", "wrong-way-risk", _largest_bw, "largest_b_w"),
    ("wrong-way grid differs from the named parameter", "wrong-way-risk", _wwr_named_grid, "wwr_b_grid"),
    ("sensitivity pfe_peak not the maximum of its profile", "single-swap", _pfe_peak, "pfe_peak"),
    ("sensitivity case without its ee profile", "single-swap", _sens_without_ee, None),
    ("time grid differs from the named parameter", "single-swap", _time_grid_named, "time_grid_years"),
    ("backtest paths per date differ from the named parameter", "single-swap", _paths_per_date, "paths_per_date"),
    ("zero spread at every bucket with a non-zero cva", "single-swap", _spread_zero_all, "zero spread"),
]


@pytest.mark.parametrize("name,key,mutate,expect", PLANTS, ids=[p[0] for p in PLANTS])
def test_every_accepted_plant_of_the_review_is_refused(name: str, key: str, mutate: Callable[[dict], None], expect: str | None) -> None:
    doc = copy.deepcopy(load(key))
    assert cs.errors(C12, doc) == [] and sm.check_c12(doc) == [], "the unplanted fixture is clean"
    mutate(doc)
    refused(C12, doc, expect)


def released_fragment(path: Path) -> str:
    """The unit's changelog fragment, or, once a release merged and deleted it (fragments.py changelog --apply), the text of the
    CHANGELOG that holds it, so the unit's needles are still checked where they now live."""
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return (path.parents[1] / "CHANGELOG.md").read_text(encoding="utf-8")  # the release that merged it holds its bullets


def test_the_plant_table_covers_every_accepted_row_of_the_review() -> None:
    assert len({p[0] for p in PLANTS}) == len(PLANTS) >= 40


def test_a_checker_returns_a_message_and_never_raises_on_a_schema_invalid_document() -> None:
    """m10: a PIT of 0 makes the Anderson-Darling logarithm raise; a deleted key raises KeyError; the checkers answer with a message."""
    doc = copy.deepcopy(load("single-swap"))
    _pit_zero(doc)
    assert isinstance(sm.check_c12(doc), list) and sm.check_c12(doc) != []
    del doc["outputs"]["sa_ccr"]["hedging_sets"]
    out = sm.check_c12(doc)
    assert isinstance(out, list) and out
    models = copy.deepcopy(load("c12-models"))
    del models["fit"]["calibrations"][0]["sample_end"]
    assert sm.check_c12_models(models)
    reg = copy.deepcopy(load("regulatory"))
    del reg["official_examples"][0]["trades"]
    assert sm.check_regulatory(reg)


def test_a_single_zero_spread_bucket_is_a_valid_curve_and_negative_spreads_have_a_stated_rule() -> None:
    """m11: only a curve that is zero everywhere implies a zero CVA; the document states what a negative spread becomes."""
    doc = copy.deepcopy(load("single-swap"))
    doc["outputs"]["cva_dva"]["buckets"][0]["spread"] = 0.0
    assert not any("zero spread" in m for m in sm.check_c12(doc))
    cva = load("single-swap")["outputs"]["cva_dva"]
    assert "set to zero" in cva["negative_spread_rule"] and cva["spreads_floored_at_zero"] == 0
    bad = copy.deepcopy(load("single-swap"))
    bad["outputs"]["cva_dva"]["buckets"][0]["spread"] = -0.001
    assert cs.errors(C12, bad) != []
    bad = copy.deepcopy(load("single-swap"))
    del bad["outputs"]["cva_dva"]["negative_spread_rule"]
    assert cs.errors(C12, bad) != []
    assert "negative_spread_rule" in load("c12-models")["fit"]["credit_curve"]


# --- the two blockers ---------------------------------------------------------------------------------------------------


def test_b1_the_girr_sensitivity_is_the_change_for_one_basis_point_divided_by_0_0001() -> None:
    schema = cs.load_json(ROOT / "docs" / "contracts" / "schemas" / "c12" / "variant-swap-exposure.schema.json")
    girr = schema["$defs"]["c12GirrCharge"]
    assert "sensitivities" in girr["properties"] and "sensitivities_per_bp" not in girr["properties"]
    assert "0.0001" in girr["properties"]["sensitivities"]["description"]
    text = REG_API.read_text(encoding="utf-8")
    assert "DIVIDED BY 0.0001" in text and "sbm_delta_charge" not in text
    for k in VARIANTS:
        g = load(k)["outputs"]["girr"]
        rw = [0.017, 0.017, 0.016, 0.013, 0.012, 0.011, 0.011, 0.011, 0.011, 0.011]
        assert g["weighted_sensitivities"] == pytest.approx([s * w / math.sqrt(2) for s, w in zip(g["sensitivities"], rw)], rel=1e-6, abs=1e-5)
        # the 10-year swap of 10M USD: DV01 of about 8,000 USD per bp is s = 8.0e7, weighted 0.011 x 8.0e7 / sqrt(2)
        assert max(g["sensitivities"]) == 8.0e7 and g["delta_charge"]["amount"] > 4.5e5


def test_b1_the_charge_is_recomputed_from_the_sensitivities_with_the_table_2_matrix() -> None:
    corr = [[x / 100 for x in row] for row in sm.GIRR_CORR]
    g = copy.deepcopy(load("netting-set")["outputs"]["girr"])
    ws = g["weighted_sensitivities"]
    for sc in g["scenarios"]:
        total = 0.0
        for k, a in enumerate(ws):
            for l, b in enumerate(ws):
                rho = corr[k][l]
                if k != l:
                    rho = rho if sc["scenario"] == "medium" else (min(1.25 * rho, 1) if sc["scenario"] == "high" else max(2 * rho - 1, 0.75 * rho))
                total += a * a if k == l else rho * a * b
        assert sc["k_b"] == pytest.approx(math.sqrt(max(total, 0)), rel=1e-6)
    assert g["delta_charge_undivided"]["amount"] == pytest.approx(math.sqrt(2) * g["delta_charge"]["amount"], rel=1e-9)


def test_b2_ore_reconciles_every_variant_but_the_wrong_way_one_and_a_failed_run_stops_the_bake() -> None:
    for v in VARIANTS:
        ore = load(v)["outputs"]["ore_reconciliation"]
        assert ore["status"] == ("not-applicable" if v == "wrong-way-risk" else "reconciled"), v
    rows = ROWS.read_text(encoding="utf-8")
    assert "stops the bake" in rows and "never published as not-applicable" in rows
    assert "csa-mpor-10d" in rows or "both CSA variants" in rows


# --- the majors ---------------------------------------------------------------------------------------------------------


def test_m1_entity_aggregate_takes_a_correlation_per_entity() -> None:
    text = REG_API.read_text(encoding="utf-8")
    assert "def entity_aggregate(addons: list[float], rhos: list[float]) -> float" in text
    a = [105.86193791695607, -279.91632166374467, 168.11140486573225]  # CRE99.52 to CRE99.54, unrounded
    rho = [0.5, 0.5, 0.8]
    sys_term = sum(r * x for r, x in zip(rho, a)) ** 2
    idio = sum((1 - r * r) * x * x for r, x in zip(rho, a))
    assert (sys_term, idio) == (pytest.approx(2252.635, abs=5e-4), pytest.approx(77344.043, abs=5e-4))
    assert sm.entity_aggregate(a, rho) == pytest.approx(math.sqrt(sys_term + idio), rel=1e-12) == pytest.approx(282.128832, abs=5e-7)
    assert sm.entity_aggregate(a, [0.5] * 3) != pytest.approx(sm.entity_aggregate(a, rho), rel=1e-3)  # one scalar rho cannot give it
    with pytest.raises(ValueError):
        sm.entity_aggregate(a, [0.5, 0.5])


def test_m2_the_multiplier_golden_is_0_965208() -> None:
    text = REG_API.read_text(encoding="utf-8")
    assert "0.965208" in text and "0.965205" not in text
    assert 0.05 + 0.95 * math.exp(-20 / (1.9 * 282.128832)) == pytest.approx(0.965208, abs=5e-7)


def test_m3_bond_a_at_zero_is_p_times_exp_b_f_not_p() -> None:
    body = sections(CCR_API)[ccr_key("hw1f", "bond_a")]
    assert "exp(B(0, T) f(0, 0))" in body and "`A(0, T) = P(0, T)` exactly" not in body
    a, f, big_t = 0.1, 0.03, 5.0
    b = (1 - math.exp(-a * big_t)) / a
    p0 = math.exp(-f * big_t)
    assert p0 * math.exp(b * f) == pytest.approx(0.968546, abs=5e-7) and p0 != pytest.approx(p0 * math.exp(b * f), rel=1e-3)
    assert p0 * math.exp(b * f) * math.exp(-b * f) == pytest.approx(p0, rel=1e-12)  # bond_price at r = phi(0) reprices P(0, T)


def test_m4_the_trade_level_cre99_path_is_exact_and_the_printed_path_keeps_one_unit() -> None:
    text = REG_API.read_text(encoding="utf-8")
    flat = " ".join(text.split())
    assert "EXACTLY after rounding" in flat and "one-unit tolerance stays only" in flat
    ex = {e["id"]: e for e in load("regulatory")["official_examples"]}
    for i, ead in {1: 569, 2: 381, 3: 5406, 4: 936, 5: 1879}.items():
        e = ex[f"cre99-netting-set-{i}"]
        pub = {p["name"]: p for p in e["published"]}
        got = sm.sa_ccr_from_trades(e["trades"], next(v["value"] for v in e["inputs"] if v["name"] == "c"),
                                    next((v["value"] for v in e["inputs"] if v["name"] == "mpor_business_days"), None),
                                    *[next((v["value"] for v in e["inputs"] if v["name"] == n), 0.0) for n in ("th", "mta", "nica")])
        assert math.floor(got["ead"] + 0.5) == ead == pub["ead"]["value"]
    # NS3 of 5,405.1 (an aggregate of 3,840.8) rounds to 5,405, not the published 5,406: refused
    d = copy.deepcopy(load("regulatory"))
    e3 = next(e for e in d["official_examples"] if e["id"] == "cre99-netting-set-3")
    next(v for v in e3["outputs"] if v["name"] == "addon_aggregate")["value"] = 3840.8
    next(v for v in e3["outputs"] if v["name"] == "ead")["value"] = 1.4 * (20 + 3840.8)
    assert any("recomputes" in m for m in sm.check_regulatory(d))


def test_m5_swap_value_between_resets_takes_the_last_fixing_and_the_analytic_ee_is_on_reset_dates() -> None:
    body = sections(CCR_API)[ccr_key("swaps", "swap_value")]
    assert "last_fixing: np.ndarray | None = None" in body and "STRICTLY BETWEEN" in body and "raises `ValueError`" in body
    assert 2 * math.sinh(0.0075) == pytest.approx(0.01500014, abs=5e-9) and "0.01500014" in body
    assert "RESET dates only" in sections(CCR_API)[ccr_key("exposure", "analytic_ee_single_swap")]
    assert "last_fixing" in sections(CCR_API)[ccr_key("swaps", "swap_values_on_grid")]


def test_m6_an_engine_function_simulates_the_critical_values_and_the_effective_sample_size() -> None:
    secs = sections(CCR_API)
    for name in ("simulate_pit_critical_values", "effective_sample_size"):
        body = secs[ccr_key("validation.ccr", name)]
        assert "```python" in body and re.search(r"^- Units:", body, flags=re.M) and re.search(r"^- (Golden|Invariants):", body, flags=re.M)
    assert "CriticalValues" in secs["riskvalidation.validation.ccr.CriticalValues"]
    none_rule = secs[ccr_key("validation.ccr", "pit_exposure_backtest")]
    assert "`critical_simulated` is `None`" in none_rule and "not_evaluated" in none_rule
    z = [1.0, 0.0, -1.0, 0.0]
    rho1 = sum(a * b for a, b in zip(z, z[1:])) / sum(a * a for a in z)
    assert rho1 == 0 and 4 / (1 + 2 * (1 - 1 / 2) * rho1) == 4  # the golden of effective_sample_size


def test_m7_the_ore_block_carries_eepe_cva_and_dim_with_their_agreements() -> None:
    for v in VARIANTS[:-1]:
        o = load(v)["outputs"]
        ore = o["ore_reconciliation"]
        grid = o["exposure"]["time_grid_years"]
        assert ore["ore_eepe"]["amount"] == pytest.approx(sm.eepe(grid, sm.effective_ee(ore["ore_ee"]["values"])), rel=1e-9)
        assert ore["ore_cva"]["amount"] == pytest.approx(sum(b["pd_counterparty"] * o["cva_dva"]["lgd"] * e for b, e in
                                                           zip(o["cva_dva"]["buckets"], ore["ore_ee_discounted"]["values"])), rel=1e-6)
        for key in ("eepe_agreement", "cva_agreement"):
            a = ore[key]
            assert a["difference"] == pytest.approx(a["ore"] - a["python"], abs=2e-6) and a["within_two_se"] is True
        assert (ore["ore_dim"] is not None) == (v == "with-im") and (ore["dim_agreement"] is not None) == (v == "with-im")


def test_m8_the_cross_field_checks_listed_by_the_review_exist() -> None:
    d = load("csa-mpor-10d")
    sa = d["outputs"]["sa_ccr"]
    assert sa["margined"] is True and sa["mpor_business_days"] == d["outputs"]["collateral"]["csa"]["mpor_business_days"] >= 10
    assert load("netting-set")["outputs"]["sa_ccr"]["margined"] is False and load("netting-set")["outputs"]["sa_ccr"]["mpor_business_days"] is None
    im = load("with-im")["outputs"]["initial_margin"]
    assert im["alpha"] == pytest.approx(NormalDist().inv_cdf(0.99), rel=1e-9) and (im["horizon_calendar_days"], im["mpor_calendar_days"]) == (14, 14)
    assert load("csa-mpor-20d")["outputs"]["collateral"]["csa"]["mpor_business_days"] == 20
    schema = cs.load_json(ROOT / "docs" / "contracts" / "schemas" / "c12" / "variant-swap-exposure.schema.json")["$defs"]
    assert schema["c12NonNegProfile"]["properties"]["values"]["items"]["minimum"] == 0
    for name in ("ee", "ee_discounted", "ene", "ene_discounted", "pfe", "effective_ee"):
        assert schema["c12Exposure"]["properties"][name] == {"$ref": "#/$defs/c12NonNegProfile"}


def test_m9_the_regulatory_document_is_part_of_the_documents_the_checker_runs_over() -> None:
    src = (ROOT / "tests" / "contracts_u9" / "test_u9_contracts.py").read_text(encoding="utf-8")
    assert '("C12", "regulatory")' in src
    assert "regulatory" in {p.parent.name for _, p in FILES.values() if "regulatory" in str(p)}


def test_m10_the_regulatory_document_carries_the_blocks_the_regulation_page_draws() -> None:
    doc = load("regulatory")
    assert {r["year"]: r["factor"] for r in doc["output_floor_phase_in"]} == {2023: 0.50, 2024: 0.55, 2025: 0.60, 2026: 0.65, 2027: 0.70, 2028: 0.725}
    assert all(r["paragraph"] == "RBC90.1" and r["in_force_date"] == "2023-01-01" for r in doc["output_floor_phase_in"])
    tables = {t["id"]: t for t in doc["parameter_tables"]}
    assert set(tables) == {"cre52-72-table-2", "mar50-16-table-1", "mar33-12-table-2", "mar33-4-table-1"}
    for t in tables.values():
        assert re.match(r"^(CRE|MAR)\d+\.\d+$", t["paragraph"]) and t["in_force_date"] == "2023-01-01" and t["rows"]
    rows50 = {(r["key"], r["parameter"]): r["value"] for r in tables["mar50-16-table-1"]["rows"]}
    assert rows50[("financials", "risk_weight_investment_grade")] == 0.05 and rows50[("technology-telecoms", "risk_weight_high_yield_or_not_rated")] == 0.055
    rows52 = {(r["key"], r["parameter"]): r["value"] for r in tables["cre52-72-table-2"]["rows"]}
    assert rows52[("credit-single-name-BBB", "supervisory_factor")] == 0.0054 and rows52[("commodity-electricity", "supervisory_factor")] == 0.40
    assert {(r["key"]): r["value"] for r in tables["mar33-4-table-1"]["rows"]} == {"j1": 10, "j2": 20, "j3": 40, "j4": 60, "j5": 120}
    inv = {e["id"] for e in doc["invariant_cases"]}
    assert {"sbm-bucket-and-cross-bucket-aggregation", "sbm-cross-bucket-fallback", "cascade-two-horizons"} <= inv
    casc = next(e for e in doc["invariant_cases"] if e["id"] == "cascade-two-horizons")
    assert next(v["value"] for v in casc["outputs"] if v["name"] == "es") == pytest.approx(math.sqrt(100 + 36 * 1), rel=1e-12)
    fb = next(e for e in doc["invariant_cases"] if e["id"] == "sbm-cross-bucket-fallback")
    flags = {v["name"]: v["value"] for v in fb["outputs"] if v["name"].startswith("fallback_")}
    assert flags == {"fallback_low": 0.0, "fallback_medium": 1.0, "fallback_high": 1.0}  # both the plain and the fallback path
    classes = {g["exposure_class"] for g in doc["cre20_grid"]}
    assert classes == {"sovereign", "eca", "bank-ecra", "bank-scra", "corporate", "retail", "equity", "residential-re", "commercial-re",
                       "defaulted", "ccf", "currency-mismatch"}
    assert any(g["table"] == "CRE20 Table 13" for g in doc["cre20_grid"]) and any(g["table"] == "CRE20 Table 2" for g in doc["cre20_grid"])
    strings = [v for e in doc["official_examples"] for t in e["trades"] for v in t["terms"] if isinstance(v["value"], str)]
    assert {v["name"] for v in strings} >= {"currency", "position", "option_type", "asset_class", "entity"}
    bad = copy.deepcopy(doc)
    bad["official_examples"][0]["inputs"][0]["value"] = {"x": 1}
    assert cs.errors(REG, bad) != []
    bad = copy.deepcopy(doc)
    del bad["official_examples"][0]["trades"][0]["paragraph"]
    assert cs.errors(REG, bad) != []


def test_m11_the_models_document_refuses_a_short_window_and_too_few_observations() -> None:
    doc = copy.deepcopy(load("c12-models"))
    doc["fit"]["calibrations"][0]["sample_start"] = "2018-06-01"  # a window of seven months, history_years still says 3
    refused(C12M, doc, "history_years")
    doc = copy.deepcopy(load("c12-models"))
    doc["fit"]["calibrations"][1]["n_obs"] = 2
    refused(C12M, doc, "n_obs")
    doc = copy.deepcopy(load("c12-models"))
    doc["fit"]["calibrations"][1]["history_years"] = 2.0
    assert cs.errors(C12M, doc) != []


def test_the_models_document_refuses_a_short_window_and_too_few_observations() -> None:
    test_m11_the_models_document_refuses_a_short_window_and_too_few_observations()


# --- the regulatory plants (review D3) ----------------------------------------------------------------------------------


def _ex(d: dict, eid: str) -> dict:
    return next(e for e in d["official_examples"] + d["invariant_cases"] if e["id"] == eid)


def _out(d: dict, eid: str, name: str, group: str = "outputs") -> dict:
    return next(v for v in _ex(d, eid)[group] if v["name"] == name)


def _set_out(eid: str, name: str, value: float) -> Callable[[dict], None]:
    def f(d: dict) -> None:
        _out(d, eid, name)["value"] = value
    return f


def _grid_cell(d: dict) -> None:
    next(g for g in d["cre20_grid"] if g["exposure_class"] == "sovereign" and g["key"] == "AAA to AA-")["risk_weight"] = 0.35


def _grid_class(d: dict) -> None:
    d["cre20_grid"][0]["exposure_class"] = "sovereigns"


def _grid_inforce(d: dict) -> None:
    d["cre20_grid"][0]["in_force_date"] = "1999-01-01"


def _entry_inforce(d: dict) -> None:
    _ex(d, "cre99-netting-set-2")["in_force_date"] = "1999-01-01"


def _para(d: dict) -> None:
    d["official_examples"][0]["paragraph"] = "CRE52foo"


def _trade_term(eid: str, trade: int, name: str, value: Any) -> Callable[[dict], None]:
    def f(d: dict) -> None:
        next(v for v in _ex(d, eid)["trades"][trade]["terms"] if v["name"] == name)["value"] = value
    return f


def _drop_trade(d: dict) -> None:
    _ex(d, "cre99-netting-set-4")["trades"].pop()


def _no_trades(d: dict) -> None:
    _ex(d, "cre99-netting-set-2")["trades"] = []


def _published(eid: str, name: str, value: float) -> Callable[[dict], None]:
    def f(d: dict) -> None:
        next(p for p in _ex(d, eid)["published"] if p["name"] == name)["value"] = value
    return f


def _phase_in(d: dict) -> None:
    d["output_floor_phase_in"][2]["factor"] = 0.65


def _table_value(tid: str, key: str, value: float) -> Callable[[dict], None]:
    def f(d: dict) -> None:
        next(r for t in d["parameter_tables"] if t["id"] == tid for r in t["rows"] if r["key"] == key)["value"] = value
    return f


REG_PLANTS: list[tuple[str, Callable[[dict], None], str | None]] = [
    ("ns3 aggregate 3,840.8", _set_out("cre99-netting-set-3", "addon_aggregate", 3840.8), "addon_aggregate"),
    ("ns3 energy add-on 2,000", _set_out("cre99-netting-set-3", "addon_energy", 2000.0), "addon_energy"),
    ("ns5 maturity factor 0.3", _set_out("cre99-netting-set-5", "maturity_factor", 0.3), "maturity_factor"),
    ("ns2 term_1 9,000", _set_out("cre99-netting-set-2", "term_1", 9000.0), "term_1"),
    ("ns4 aggregate 628.6", _set_out("cre99-netting-set-4", "addon_aggregate", 628.6), "addon_aggregate"),
    ("ns2 multiplier 0.965205", _set_out("cre99-netting-set-2", "multiplier", 0.965205), "multiplier"),
    ("ns3 published ead 5,405", _published("cre99-netting-set-3", "ead", 5405), "rounds to"),
    ("ns1 published ead 570", _published("cre99-netting-set-1", "ead", 570), "rounds to"),
    ("cre20 sovereign AAA weight 0.35", _grid_cell, "cre20 grid"),
    ("cre20 exposure class misspelt", _grid_class, None),
    ("cre20 row in-force date 1999", _grid_inforce, "in-force"),
    ("cre99 entry in-force date 1999", _entry_inforce, "in-force"),
    ("paragraph CRE52foo", _para, None),
    ("cascade output 12 with holds true", _set_out("cascade-two-horizons", "es", 12.0), "cascade"),
    ("cascade with every lh ten, output 9", _set_out("cascade-all-lh-ten", "es", 9.0), "cascade"),
    ("sbm rho_low 0.25", _set_out("sbm-low-and-high-scenarios", "rho_low", 0.25), "rho_low"),
    ("sbm cross-bucket charge altered", _set_out("sbm-bucket-and-cross-bucket-aggregation", "cross_bucket_medium", 17.0), "cross-bucket"),
    ("sbm bucket charge altered", _set_out("sbm-bucket-and-cross-bucket-aggregation", "k_b1_low", 12.0), "bucket 1 charge"),
    ("sbm fallback flag altered", _set_out("sbm-cross-bucket-fallback", "fallback_medium", 0.0), "fallback"),
    ("sbm charge not the maximum", _set_out("sbm-bucket-and-cross-bucket-aggregation", "sbm_charge", 15.0), "maximum"),
    ("ba-cva k_full 5", _set_out("ba-cva-hedges-floor", "k_full", 5.0), "K_full"),
    ("ba-cva k_reduced 29", _set_out("ba-cva-rho-one", "k_reduced", 29.0), "BA-CVA"),
    ("ns3 trade notional 10,400", _trade_term("cre99-netting-set-3", 0, "notional", 10400), "CRE99.64"),
    ("ns3 adjusted notional altered", _trade_term("cre99-netting-set-3", 0, "adjusted_notional", 9000), "recomputes"),
    ("ns1 trade 10 years becomes 9", _trade_term("cre99-netting-set-1", 0, "end_years", 9), "recomputes"),
    ("ns1 trade position flipped", _trade_term("cre99-netting-set-1", 0, "position", "pay-floating-receive-fixed"), "recomputes"),
    ("ns1 swaption strike 5.5 percent", _trade_term("cre99-netting-set-1", 2, "option_strike", 0.055), "recomputes"),
    ("ns2 firm A rating AAA", _trade_term("cre99-netting-set-2", 0, "rating", "BBB"), "recomputes"),
    ("ns2 trade market value changed", _trade_term("cre99-netting-set-2", 0, "market_value", 120), "V is not"),
    ("ns4 loses a trade", _drop_trade, "recomputes"),
    ("ns2 without its trades", _no_trades, "carries its trades"),
    ("output floor phase-in 2025 altered", _phase_in, "phase_in"),
    ("cre52.72 table value altered", _table_value("cre52-72-table-2", "credit-single-name-BBB", 0.0055), "parameter table"),
    ("mar50.16 table value altered", _table_value("mar50-16-table-1", "financials", 0.06), "parameter table"),
    ("mar33.12 table value altered", _table_value("mar33-12-table-2", "fx-volatility", 20), "parameter table"),
]


@pytest.mark.parametrize("name,mutate,expect", REG_PLANTS, ids=[p[0] for p in REG_PLANTS])
def test_every_planted_regulatory_defect_is_refused(name: str, mutate: Callable[[dict], None], expect: str | None) -> None:
    doc = copy.deepcopy(load("regulatory"))
    assert cs.errors(REG, doc) == [] and sm.check_regulatory(doc) == []
    mutate(doc)
    refused(REG, doc, expect)


# --- the variants together (m14), the rows (m12), the texts (m1, m2, m3, m4, m8, m15) ----------------------------------------


def test_m14_the_six_variants_share_one_time_grid_and_the_checker_says_when_they_do_not() -> None:
    docs = [load(v) for v in VARIANTS]
    assert sm.check_c12_variants({"documents": docs}) == []
    assert len({tuple(d["outputs"]["exposure"]["time_grid_years"]) for d in docs}) == 1
    grid = docs[0]["outputs"]["named_parameters"]["time_grid_years"]["value"]
    assert grid == docs[0]["outputs"]["exposure"]["time_grid_years"] and grid[-1] == 10.0  # to the 10-year swap
    bad = copy.deepcopy(docs)
    bad[3]["outputs"]["exposure"]["time_grid_years"] = bad[3]["outputs"]["exposure"]["time_grid_years"][:-1]
    assert any("time grid" in m for m in sm.check_c12_variants({"documents": bad}))


def test_m12_the_consumer_test_column_names_consumer_side_tests_only() -> None:
    lines = [ln for ln in ROWS.read_text(encoding="utf-8").splitlines()
             if (ln.startswith("| c12") or ln.startswith("| reg") or ln.startswith("| engine")) and ln.count("|") > 8]
    assert len(lines) == 5
    for ln in lines:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        consumer = cells[6]
        assert "tests/contracts_u9/" not in consumer, f"{cells[0]}: a producer-side test in the consumer column"
        assert consumer == "-" or (ROOT / consumer.split("::")[0]).is_file(), cells[0]
    assert any("frontend/src/lib/contract.test.ts" in ln for ln in lines)


def test_m1_m2_the_printed_values_are_exact_text_corrections() -> None:
    reg = REG_API.read_text(encoding="utf-8")
    assert "936.6 (936)" not in reg and "628.893" in reg and "936.45" in reg
    assert "MAR21.101" in reg.split("## UNVERIFIED and open items")[1] and "single-currency" in reg.split("## UNVERIFIED and open items")[1]


def test_m2_the_hull_white_a2_golden_is_stated_at_the_recomputed_value() -> None:
    body = sections(CCR_API)[ccr_key("cva", "wwr_calibrate_a")]
    assert "-7.85077" in body and "5e-6" in body and "2e-4" in body and "one unit of the last printed digit for `h`" in body


def test_m3_one_test_id_for_the_cva_check() -> None:
    assert "cva_recomputed_from_ee" not in CCR_API.read_text(encoding="utf-8")
    for v in VARIANTS:
        ids = [t["test_id"] for t in load(v)["tests"]]
        assert "ccr.cva_recomputed" in ids and "ccr.cva_recomputed_from_ee" not in ids


def test_m4_pfe_takes_a_seed() -> None:
    body = sections(CCR_API)[ccr_key("exposure", "pfe")]
    assert "seed: int = 0" in body and "default_rng(seed)" in body


def test_m8_the_function_renames_of_the_review() -> None:
    reg = sections(REG_API)
    assert reg_key("standardised", "apply_currency_mismatch") in reg and reg_key("standardised", "currency_mismatch_multiplier") not in reg
    assert reg_key("frtb", "girr_delta_charge") in reg and reg_key("frtb", "sbm_delta_charge") not in reg
    assert reg_key("frtb", "cross_bucket_charge") in reg and reg_key("frtb", "cross_bucket") not in reg
    assert "riskvalidation.regulatory.standardised.RegulatoryParameter" in reg and "riskvalidation.regulatory.standardised.RiskWeight" not in reg
    assert "RiskWeight = RegulatoryParameter" in reg["riskvalidation.regulatory.standardised.RegulatoryParameter"]
    assert "thin wrapper of `riskvalidation.regulatory.sa_ccr.netting_set_ead`" in sections(CCR_API)[ccr_key("exposure", "rung1_ead")]
    assert "adjusted" in reg[reg_key("standardised", "apply_currency_mismatch")].lower()


def test_m9_the_im_horizon_and_the_mpor_are_stated_in_calendar_days() -> None:
    body = sections(CCR_API)[ccr_key("collateral", "dynamic_initial_margin")]
    assert "horizon_calendar_days: int, mpor_calendar_days: int" in body and "14 calendar days" in body
    im = load("with-im")["outputs"]["initial_margin"]
    assert "horizon_days" not in im and "mpor_days" not in im
    assert im["mpor_calendar_days"] == round(1.4 * 10) and round(1.4 * 20) == 28


def test_the_changelog_fragment_names_the_fix_round() -> None:
    text = released_fragment(CHANGES_FIX)
    assert "fix round" in text and "MAR21.19" in text and chr(0x2014) not in text and chr(0x2192) not in text
    if CHANGES_FIX.is_file():  # the format rule binds the fragment; after the release its bullets sit in the CHANGELOG entry
        assert all(ln.startswith("- ") or ln.startswith("  ") for ln in text.splitlines() if ln.strip())
