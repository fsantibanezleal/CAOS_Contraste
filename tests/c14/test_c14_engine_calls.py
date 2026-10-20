"""CT-1407: the pinned engine reproduces the contract goldens, and every number of a committed document equals the engine call on the
inputs the document carries (the checks of ``semantics.py`` recompute with their own formulas; this test recomputes with the engine)."""
from __future__ import annotations

import re
from functools import lru_cache

import c14_docs as d
import numpy as np
import pytest
from riskvalidation.irrbb import curves, eve_nii, shocks, simulation, slotting
from riskvalidation.validation import irrbb as vi

ROOT = d.ROOT
MID = slotting.bucket_grid().midpoints


def approx(a, b, rel=1e-9, abs_=1e-6) -> bool:
    return bool(np.isclose(a, b, rtol=rel, atol=abs_))


ENGINE_PIN = re.compile(r"^riskvalidation(?:\[market\])? @ git\+https://github\.com/fsantibanezleal/CAOS_RiskValidation(?:\.git)?@(?P<ref>\S+)\s*$", re.M)
SDD_ENGINE_ROW = re.compile(r"^\|\s*engine\s*\|\s*riskvalidation\s*\|\s*(?P<ref>[^|\s]+)\s*\|", re.M)


def engine_pin_findings(requirements: str, sdd: str) -> list[str]:
    """The engine is pinned by a release tag, or (until the tag is cut) by a full 40-hex commit that the SDD technology row names too."""
    pin = ENGINE_PIN.search(requirements)
    if pin is None:
        return ["the requirements carry no riskvalidation git pin"]
    ref = pin.group("ref")
    if re.fullmatch(r"v\d+\.\d+\.\d+", ref):
        return []
    if not re.fullmatch(r"[0-9a-f]{40}", ref):
        return [f"the pin {ref} is neither a release tag nor a full 40-hex commit"]
    row = SDD_ENGINE_ROW.search(sdd)
    if row is None or row.group("ref") != ref:
        return [f"the commit pin {ref} is not the one the SDD technology row names ({row.group('ref') if row else 'no row'})"]
    return []


def test_the_engine_is_pinned_by_its_release_tag_or_by_the_commit_the_sdd_names() -> None:
    req = (ROOT / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    sdd = (ROOT / "docs" / "design" / "SDD.md").read_text(encoding="utf-8")
    assert engine_pin_findings(req, sdd) == []


def test_the_pin_check_refuses_a_planted_mismatch() -> None:
    sha, other = "25e9538faf10bfdbcde03c5adccffd8e86ec275c", "a52888e3d2b9a3331646d6fa831525e8283118b1"
    line = "riskvalidation[market] @ git+https://github.com/fsantibanezleal/CAOS_RiskValidation.git@{}\n"
    row = "| engine | riskvalidation | {} | the validation tests | none |\n"
    assert engine_pin_findings(line.format(sha), row.format(sha)) == []
    assert engine_pin_findings(line.format("v0.07.000"), row.format("v0.07.000")) == []
    assert engine_pin_findings(line.format(sha), row.format(other)) != []          # the SDD row names another commit
    assert engine_pin_findings(line.format(sha), "") != []                          # no SDD row
    assert engine_pin_findings(line.format(sha[:7]), row.format(sha[:7])) != []     # an abbreviated commit
    assert engine_pin_findings(line.format("main"), row.format("main")) != []        # a branch
    assert engine_pin_findings("riskvalidation==0.7.0\n", row.format(sha)) != []    # no git pin


def test_the_pinned_engine_reproduces_the_contract_goldens() -> None:
    flows = np.zeros(19)
    flows[3], flows[8], flows[15] = 100.0, -30.0, -70.0
    r = np.full(19, 0.02)
    assert eve_nii.eve(flows, r, MID) == pytest.approx(12.828783, abs=5e-7)
    size = shocks.shock_size("USD", "2024")
    assert (size.parallel_bp, size.short_bp, size.long_bp, size.origin) == (200, 300, 225, "srp31-table-2024")
    want = {"parallel-up": -10.666989, "parallel-down": 12.828783, "steepener": -8.944982, "flattener": 6.076550,
            "short-up": -1.625807, "short-down": 1.702071}
    for s, w in want.items():
        shape = shocks.shock_curve(s, 200, 300, 225, MID)
        assert eve_nii.delta_eve(flows, flows, r, shocks.apply_floor(r, shape, None), MID) == pytest.approx(w, abs=5e-7)
    assert eve_nii.eve_risk_measure(np.array([[3, -1], [2, 4], [-5, -2], [0, 0], [0, 0], [0, 0]], dtype=float)) == 6.0
    paths = np.concatenate([np.arange(1, 21), np.arange(101, 121)]).astype(float)
    assert simulation.ear_evar_mc_error(paths, paths, level=0.5, n_batches=2).ear_se == pytest.approx(50.0)
    assert vi.srp31_92_goldens().light == "green"
    assert curves.bootstrap_zero_curve(np.array([0.5, 1.0, 2.0]), np.full(3, 0.04))[1] == pytest.approx(2 * np.log(1.02), abs=1e-6)


def engine_findings(out: dict, ear: bool = True) -> list[str]:
    """Every number of a C14 outputs block compared with the engine call on the inputs the block carries."""
    bad: list[str] = []

    def need(ok: bool, what: str) -> None:
        if not ok:
            bad.append(what)

    points = out["curve"]["points"]
    ten = np.array([p["tenor_years"] for p in points])
    zero = curves.bootstrap_zero_curve(ten, np.array([p["observed_yield"] for p in points]), 2)
    need(np.allclose(zero, [p["zero_rate"] for p in points], rtol=0, atol=1e-12), "np.allclose(zero, [p['zero_rate'] for p in points]")
    r0 = curves.zero_rates_at(ten, zero, MID)
    need(np.allclose(r0, out["curve"]["zero_rates_at_midpoints"], rtol=0, atol=1e-12), "np.allclose(r0, out['curve']['zero_rates_at_midpoi")
    items = out["balance_sheet"]["items"]
    for sc in out["scenarios"]:
        flows = np.zeros(19)
        for it in items:
            for f in it["cash_flows"][sc["nmd_assumption"]]:
                flows[f["bucket"] - 1] += f["amount"]
        td = sum(i["amount"] for i in items if i["behavioural_class"] == "term-deposit")
        size = shocks.shock_size("USD", sc["calibration"])
        need((sc["shock_size"]["parallel_bp"], sc["shock_size"]["short_bp"], sc["shock_size"]["long_bp"]) == (size.parallel_bp, size.short_bp, size.long_bp), "(sc['shock_size']['parallel_bp'], sc['shock_size']")
        need(approx(sc["base_eve"], eve_nii.eve(flows, r0, MID)), "approx(sc['base_eve'], eve_nii.eve(flows, r0, MID)")
        deltas = []
        for row in sc["shocks"]:
            shape = shocks.shock_curve(row["shock"], size.parallel_bp, size.short_bp, size.long_bp, MID)
            need(np.allclose(shape, row["shape_bp"], rtol=0, atol=1e-9), "np.allclose(shape, row['shape_bp'], rtol=0, atol=1")
            shocked = shocks.apply_floor(r0, shape, sc["floor"])
            moved = td * slotting.term_deposit_redemption_rate(row["shock"], out["assumptions"]["term_deposit_redemption_rate"]["value"])
            net = flows.copy()
            net[0] -= moved
            net[3] += moved
            need(np.allclose(net, row["net_cash_flows"], rtol=1e-12, atol=1e-6), "np.allclose(net, row['net_cash_flows'], rtol=1e-12")
            need(approx(row["eve"], eve_nii.eve(net, shocked, MID)), "approx(row['eve'], eve_nii.eve(net, shocked, MID))")
            need(approx(row["delta_eve"], eve_nii.delta_eve(flows, net, r0, shocked, MID, kao=row["kao"])), "approx(row['delta_eve'], eve_nii.delta_eve(flows, ")
            if row["delta_nii"] is not None:
                need(approx(row["delta_nii"], eve_nii.delta_nii(flows, r0, shocked, MID)), "approx(row['delta_nii'], eve_nii.delta_nii(flows, ")
            deltas.append(row["delta_eve"])
        measure = eve_nii.eve_risk_measure(np.array(deltas).reshape(6, 1))
        need(approx(sc["eve_risk_measure"], measure), "approx(sc['eve_risk_measure'], measure)")
        o = eve_nii.outlier_test(measure, sc["outlier"]["tier1"])
        need(approx(sc["outlier"]["ratio"], o.ratio) and sc["outlier"]["breached"] == o.breached, "approx(sc['outlier']['ratio'], o.ratio) and sc['ou")
    dyn = out["dynamic_nii"]
    its = dyn["items"]
    for scn in dyn["scenarios"]:
        p = simulation.simulate_nii(np.array([i["balance"] for i in its]), np.array([1 if i["side"] == "asset" else -1 for i in its]),
                                    np.array([i["rate0"] for i in its]), np.array([i["spread"] for i in its]),
                                    np.array([i["beta"] for i in its]), np.array([i["reprice_months"] for i in its]),
                                    np.array(scn["short_rate_path"]), dyn["balance_sheet_assumption"]["growth_annual"])
        need(np.allclose(p.monthly_nii, scn["monthly_nii"], rtol=1e-12, atol=1e-6) and approx(p.total, scn["total"]), "np.allclose(p.monthly_nii, scn['monthly_nii'], rto")
    if ear:
        ee = out["ear_evar"]
        nii, eve_p = simulated(out["valuation_date"], out)
        for lv in ee["levels"]:
            got = simulation.ear_evar(nii, eve_p, ee["base_nii"], ee["base_eve"], lv["level"])
            err = simulation.ear_evar_mc_error(nii, eve_p, lv["level"], ee["n_batches"])
            need(approx(lv["ear"], got.ear) and approx(lv["evar"], got.evar), f"ear or evar at {lv['level']} differs from the engine")
            need(approx(lv["ear_se"], err.ear_se) and approx(lv["evar_se"], err.evar_se), f"a Monte Carlo error at {lv['level']} differs from the engine")
    return bad


@lru_cache(maxsize=None)
def _sim_cache(date: str, key: str) -> tuple[np.ndarray, np.ndarray]:
    out = _OUT[key]
    points = out["curve"]["points"]
    ten = np.array([p["tenor_years"] for p in points])
    zero = curves.bootstrap_zero_curve(ten, np.array([p["observed_yield"] for p in points]), 2)
    r0 = curves.zero_rates_at(ten, zero, MID)
    its = out["dynamic_nii"]["items"]
    ee = out["ear_evar"]
    par = {p["name"]: p["value"] for p in ee["parameters"]}
    paths = simulation.hw1f_scenarios(zero, ten, par["a"], par["sigma"], ee["horizon_months"], ee["n_paths"], ee["seed"])
    arrs = (np.array([i["balance"] for i in its]), np.array([1 if i["side"] == "asset" else -1 for i in its]),
            np.array([i["rate0"] for i in its]), np.array([i["spread"] for i in its]), np.array([i["beta"] for i in its]),
            np.array([i["reprice_months"] for i in its]))
    nii = np.array([simulation.simulate_nii(*arrs, q[:ee["horizon_months"]], 0.0).total for q in paths])
    flows = np.zeros(19)
    for it in out["balance_sheet"]["items"]:
        for f in it["cash_flows"]["behavioural"]:
            flows[f["bucket"] - 1] += f["amount"]
    floor = out["scenarios"][0]["floor"]
    eve_p = np.array([eve_nii.eve(flows, shocks.apply_floor(r0, np.full(19, (q[-1] - q[0]) * 1e4), floor), MID) for q in paths])
    return nii, eve_p


_OUT: dict[str, dict] = {}


def simulated(date: str, out: dict) -> tuple[np.ndarray, np.ndarray]:
    """The simulated NII and EVE paths of a document's inputs, once per valuation date (the simulation is the slow part)."""
    _OUT[date] = out
    return _sim_cache(date, date)


@pytest.mark.parametrize("vid", d.VARIANTS)
def test_every_number_of_a_document_equals_the_engine_call_on_its_inputs(vid: str) -> None:
    # the 100 000-path re-simulation (tens of seconds) runs for one date; the others are held by check_document and the byte-identical re-bake
    assert engine_findings(d.variant(vid)["outputs"], ear=vid == "vd-2021-q4") == []
