"""CT-1206, CT-1207, CT-1211, CT-1220: every number is an engine call; the collateral behaves as the contract says."""
from __future__ import annotations

import numpy as np
import pytest
from c12_support import requires_raw
from riskvalidation.ccr import collateral as col
from riskvalidation.ccr import cva as cv
from riskvalidation.ccr import exposure as ex
from riskvalidation.ccr import hw1f
from riskvalidation.regulatory import ba_cva, frtb, sa_ccr
from scipy.stats import norm

from pipeline.cases.c12 import book, credit
from pipeline.cases.c12 import exposure as xp
from pipeline.cases.c12 import variant as vt


def _inputs(doc):
    o = doc["outputs"]
    tenors = np.array([p["tenor_years"] for p in o["curve"]["points"]])
    zeros = np.array([p["zero_rate"] for p in o["curve"]["points"]])
    trades = [book.Trade(t["trade_id"], t["notional"]["amount"], t["maturity_years"], t["side"], t["fixed_rate"]) for t in o["book"]["trades"]]
    return o, tenors, zeros, trades


@requires_raw
def test_every_exposure_and_cva_number_of_a_document_equals_the_engine_call_on_its_inputs(built) -> None:
    doc = built.variants["netting-set"]
    o, tenors, zeros, trades = _inputs(doc)
    cal, npm = o["calibration_used"], o["named_parameters"]
    sim = xp.simulate(tenors, zeros, cal["a"], cal["sigma"], npm["path_count"]["value"], npm["seed"]["value"], book.swaps_of(trades),
                      {10: book.closeout_years(10), 20: book.closeout_years(20)})
    num = sim.numeraire[:, sim.index(sim.report)]
    u = xp.uncollateralised(sim, [0, 1, 2, 3])
    ee_d, _ = ex.expected_exposure(u.x, num)
    assert np.array(o["exposure"]["ee_discounted"]["values"]) == pytest.approx(ee_d, rel=1e-12)
    ee = ee_d / sim.p0(sim.report)
    assert np.array(o["exposure"]["ee"]["values"]) == pytest.approx(ee, rel=1e-12)
    assert o["exposure"]["eepe"]["amount"] == pytest.approx(ex.effective_epe(sim.report, ex.effective_ee(ee)), rel=1e-12)
    pfe, _ = ex.pfe(u.x, 0.95, seed=npm["seed"]["value"], n_bootstrap=50)
    assert np.array(o["exposure"]["pfe"]["values"]) == pytest.approx(pfe, rel=1e-12)
    cva_blk = o["cva_dva"]
    pd = np.array([b["pd_counterparty"] for b in cva_blk["buckets"]])
    assert cva_blk["cva"]["amount"] == pytest.approx(cv.cva(ee_d, pd, cva_blk["lgd"])[0], rel=1e-12)
    # the engine reproduces its contract goldens
    assert cv.cva(np.array([10.0, 20.0]), np.array([0.1, 0.1]), 0.6)[0] == pytest.approx(1.8, abs=1e-12)
    assert ex.effective_epe(np.array([0.25, 0.5, 1.0]), np.array([1.0, 3.0, 3.0])) == pytest.approx(2.5, abs=1e-12)
    assert float(hw1f.bond_b(np.array(0.0), np.array(5.0), 0.1)) == pytest.approx(3.934693, abs=5e-7)


@requires_raw
def test_the_sticky_closeout_collateral_behaves_as_the_contract_says() -> None:
    assert book.closeout_years(10) == 14 / 360 and book.closeout_years(20) == 28 / 360
    tenors, zeros = np.array([0.25, 1.0, 5.0, 10.0, 30.0]), np.array([0.03, 0.031, 0.033, 0.035, 0.036])
    trades = [book.Trade("SW-1", 1e7, 5.0, "payer", 0.033), book.Trade("SW-4", 2e6, 0.5, "receiver", 0.03)]
    swaps = book.swaps_of(trades)
    sim = xp.simulate(tenors, zeros, 0.1, 0.01, 4000, 3, swaps, {10: book.closeout_years(10), 20: book.closeout_years(20)})
    num, grid = sim.numeraire[:, sim.index(sim.report)], sim.report
    p0r = sim.p0(grid)
    unc = xp.measures(xp.uncollateralised(sim, [0, 1]).x, num, p0r, grid, None, 1)
    ee = {mp: xp.measures(xp.variation_margin(sim, [0, 1], mp, 0.0).x, num, p0r, grid, None, 1) for mp in (10, 20)}
    assert ee[10]["eepe"] < unc["eepe"] and ee[10]["eepe"] <= ee[20]["eepe"] + 3 * ee[20]["eepe_se"]    # a longer MPoR does not lower the EE
    sim0 = xp.simulate(tenors, zeros, 0.1, 0.01, 4000, 3, swaps, {10: 1e-5})
    zero = xp.variation_margin(sim0, [0, 1], 10, 0.0)
    assert float(np.max(zero.x)) < 0.05 * float(np.max(xp.uncollateralised(sim0, [0, 1]).x))      # MPoR tending to zero: no exposure
    # the credit support amount and delivery amount of ORE
    assert col.credit_support_amount(np.array([100.0]), 0.0, 30.0, 0.0)[0] == 70.0
    assert col.delivery_amount(np.array([100.0]), np.array([92.0]), np.array([0.0]), 10.0)[0] == 0.0


@requires_raw
def test_the_regulatory_numbers_equal_the_engine_calls_on_the_documents_inputs(built) -> None:
    for name in ("netting-set", "csa-mpor-10d", "with-im"):
        o, tenors, zeros, trades = _inputs(built.variants[name])
        sa = o["sa_ccr"]
        ir = sa_ccr.ir_addon([sa_ccr.IrTrade("USD", 0.0, t.maturity, t.notional, 1.0 if t.side == "payer" else -1.0) for t in trades],
                             sa["mpor_business_days"])
        res = sa_ccr.netting_set_ead(sa["v"]["amount"], sa["c"]["amount"], sa_ccr.AddOnByClass(interest_rate=ir.addon), sa["margined"],
                                     sa["th"]["amount"], sa["mta"]["amount"], sa["nica"]["amount"])
        assert sa["ead"]["amount"] == pytest.approx(res.ead, rel=1e-12) and sa["multiplier"] == pytest.approx(res.multiplier, rel=1e-12)
        cp = o["ba_cva"]["counterparties"][0]
        scva = ba_cva.scva(cp["risk_weight"], [(cp["m_years"], sa["ead"]["amount"])])
        assert o["ba_cva"]["capital"]["amount"] == pytest.approx(ba_cva.capital(ba_cva.k_reduced([scva])), rel=1e-12)
        g = o["girr"]
        div, und = frtb.girr_parameters(True), frtb.girr_parameters(False)
        s = np.array(g["sensitivities"])
        assert g["delta_charge"]["amount"] == pytest.approx(frtb.girr_delta_charge(s, div.tenors, div).charge, rel=1e-12)
        assert g["delta_charge_undivided"]["amount"] == pytest.approx(frtb.girr_delta_charge(s, und.tenors, und).charge, rel=1e-12)
        assert g["delta_charge_undivided"]["amount"] == pytest.approx(np.sqrt(2) * g["delta_charge"]["amount"], rel=1e-9)
        assert o["regulatory_comparison"]["alpha_times_eepe"]["amount"] == pytest.approx(1.4 * o["exposure"]["eepe"]["amount"], rel=1e-12)
    assert float(norm.ppf(0.99)) == pytest.approx(2.326348, abs=5e-7)


@requires_raw
def test_an_undefined_effective_maturity_stops_the_document_with_its_reason() -> None:
    zeros = np.full(5, 0.03)
    tenors = np.array([0.25, 1.0, 5.0, 10.0, 30.0])
    trade = book.Trade("SW-1", 1e6, 2.0, "payer", 0.03)
    sim = xp.simulate(tenors, zeros, 0.1, 0.01, 200, 1, book.swaps_of([trade]), {10: book.closeout_years(10), 20: book.closeout_years(20)})
    c = vt.core(sim, vt.Spec("single-swap", (0,), None), 1, light=True)
    with pytest.raises(ValueError, match="zero over the first year"):
        ex.effective_maturity(sim.report, np.zeros(sim.report.size), np.zeros(sim.report.size), sim.p0(sim.report))
    ctx = {"trades": [trade], "credit_curve": credit.flat_curve(0.0125, sim.report), "tenors": tenors, "zeros": zeros,
           "stress": {"start": "2007-01-01", "end": "2009-12-31", "spread_start": 0.0, "spread_peak": 0.01},
           "curve_block": {}, "calibration_used": {}, "named": {}}
    c.mx["eff"] = np.zeros(sim.report.size)
    c.mx["ee"] = np.zeros(sim.report.size)
    with pytest.raises(vt.BakeError, match="undefined"):
        vt.outputs(c, ctx, 0.0, [], {}, {}, 1)
