"""CT-1507: the pinned engine reproduces the contract goldens, and every number of a committed document equals the engine call on the
inputs the document carries (the checks of ``semantics.py`` recompute with their own formulas; this test recomputes with the engine)."""
from __future__ import annotations

import re

import c15_docs as d
import numpy as np
import pytest
from c15_support import ROOT, SHOCKS, VARIANT_IDS
from riskvalidation.irrbb import curves, eve_nii, shocks, simulation, slotting
from riskvalidation.validation import irrbb as vi

MID = slotting.bucket_grid().midpoints


def approx(a, b, rel=1e-9, abs_=1e-6) -> bool:
    return bool(np.isclose(a, b, rtol=rel, atol=abs_))


def test_the_engine_is_pinned_by_its_release_tag() -> None:
    req = (ROOT / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    assert re.search(r"^riskvalidation(?:\[market\])? @ git\+https://github\.com/fsantibanezleal/CAOS_RiskValidation(?:\.git)?@v\d+\.\d+\.\d+\s*$", req, re.M)


def test_the_pinned_engine_reproduces_the_contract_goldens() -> None:
    assert eve_nii.cmf_pair(30, -20) == 20 and eve_nii.cmf_pair(-20, 30) == 20 and eve_nii.cmf_pair(10, -40) == 0 and eve_nii.cmf_pair(10, 20) == 30
    assert eve_nii.indexation_charge(-200) == 5.0
    pairs = eve_nii.annex1_delta_eve(np.array([10, -20, 0, 5, -30, 40.0]), np.array([20, 30, -10, -2, 50, -15.0]))
    assert list(pairs.pairs) == [30, 20, 0, 4, 35, 32.5] and pairs.delta_eve == 35 and pairs.worst_shock == "short-up"
    nii = eve_nii.annex1_delta_nii(np.array([30, -10.0]), np.array([-20, 5.0]), -200.0)
    assert (nii.max_pair, nii.indexation_charge, nii.delta_nii, nii.worst_shock) == (20.0, 5.0, 25.0, "parallel-up")
    assert shocks.shock_size("CLP", "cmf-annex1").parallel_bp == 300 and shocks.shock_size("CLF", "cmf-annex1").short_bp == 250
    assert shocks.apply_floor(np.array([0.004]), np.array([-300.0]), -0.02)[0] == pytest.approx(-0.02)
    assert vi.cmf_annex1_goldens().light == "green" and vi.srp31_92_goldens().light == "green"
    assert curves.bootstrap_zero_curve(np.array([0.5, 1.0, 2.0]), np.full(3, 0.04))[1] == pytest.approx(2 * np.log(1.02), abs=1e-6)
    paths = np.concatenate([np.arange(1, 21), np.arange(101, 121)]).astype(float)
    assert simulation.ear_evar_mc_error(paths, paths, level=0.5, n_batches=2).ear_se == pytest.approx(50.0)


def dense(flows: list[dict]) -> np.ndarray:
    v = np.zeros(19)
    for f in flows:
        v[f["bucket"] - 1] += f["amount"]
    return v


def engine_findings(out: dict) -> list[str]:
    """Every number of a C15 outputs block compared with the engine call on the inputs the block carries."""
    bad: list[str] = []

    def need(ok: bool, what: str) -> None:
        if not ok:
            bad.append(what)

    uf = out["ur_currency"]["uf_value"]
    rates = {}
    for key, name in (("clp", "CLP"), ("ur", "UR")):
        c = out["curves"][key]
        ten = np.array([p["tenor_years"] for p in c["points"]])
        zero = curves.bootstrap_zero_curve(ten, np.array([p["observed_yield"] for p in c["points"]]), 2)
        need(np.allclose(zero, [p["zero_rate"] for p in c["points"]], rtol=0, atol=1e-12), f"{name}: bootstrap_zero_curve")
        fit = curves.fit_nelson_siegel(ten, zero)
        got = {p["name"]: p["value"] for p in c["fit"]["parameters"]}
        need(all(approx(got[k], v, 1e-9, 1e-12) for k, v in zip(("beta0", "beta1", "beta2", "tau"), (fit.beta0, fit.beta1, fit.beta2, fit.tau))),
             f"{name}: fit_nelson_siegel parameters")
        need(approx(c["fit"]["rmse_bp"], fit.rmse * 1e4, 1e-9, 1e-9), f"{name}: fit_nelson_siegel rmse")
        r0 = curves.nelson_siegel_yield(MID, fit.beta0, fit.beta1, fit.beta2, fit.tau)
        need(np.allclose(r0, c["zero_rates_at_midpoints"], rtol=0, atol=1e-12), f"{name}: nelson_siegel_yield at the midpoints")
        rates[name] = r0
    items = {leg["leg"]: leg["items"] for leg in out["legs"]}
    conv = {"CLP": 1.0, "UR": uf}
    tdrr0 = out["assumptions"]["term_deposit_redemption_rate"]["value"]
    base = {n: sum(dense(f["cash_flows"]) * conv[n] for f in items[n]) for n in items}
    sizes = {s["currency"]: shocks.shock_size(s["currency"], "cmf-annex1") for s in out["eve_shock_sizes"]}
    for s in out["eve_shock_sizes"]:
        z = sizes[s["currency"]]
        need((s["parallel_bp"], s["short_bp"], s["long_bp"], s["origin"]) == (z.parallel_bp, z.short_bp, z.long_bp, z.origin), f"shock size {s['currency']}")
    floors = {"CLP": out["floors"]["other_floor"], "UR": out["floors"]["ur_floor"]}
    state = out["offset_rule"]["state"]
    offset = state != "off"
    base_eve = {n: float(eve_nii.eve(base[n], rates[n], MID)) for n in base}
    need(approx(out["eve"]["base_eve_clp"], base_eve["CLP"]) and approx(out["eve"]["base_eve_ur"], base_eve["UR"]), "base EVE")
    d_clp, d_ur, totals = [], [], []
    for row in out["eve"]["rows"]:
        s = row["shock"]
        res = {}
        for name, key in (("CLP", "clp"), ("UR", "ur")):
            z = sizes["CLP" if name == "CLP" else "CLF"]
            shape = shocks.shock_curve(s, z.parallel_bp, z.short_bp, z.long_bp, MID)
            need(np.allclose(shape, row[key]["shape_bp"], rtol=0, atol=1e-9), f"{s}/{name}: shock_curve")
            shocked = shocks.apply_floor(rates[name], shape, floors[name])
            net = np.zeros(19)
            for f in items[name]:
                v = dense(f["cash_flows"]) * conv[name]
                if f["behavioural_class"] == "term-deposit":
                    r = slotting.term_deposit_redemption_rate(s, tdrr0)
                    amount = abs(v.sum())
                    v = v * (1.0 - r)
                    v[0] -= r * amount
                net += v
            need(np.allclose(net, row[key]["net_cash_flows"], rtol=1e-12, atol=1e-6), f"{s}/{name}: net_cash_flows")
            need(approx(row[key]["eve"], eve_nii.eve(net, shocked, MID)), f"{s}/{name}: eve")
            de = eve_nii.delta_eve(base[name], net, rates[name], shocked, MID, kao=0.0)
            need(approx(row[key]["delta_eve"], de), f"{s}/{name}: delta_eve")
            res[name] = de
        p = row["pair"]
        need(approx(p["with_offset"], eve_nii.cmf_pair(res["CLP"], res["UR"], True)) and approx(p["without_offset"], eve_nii.cmf_pair(res["CLP"], res["UR"], False)),
             f"{s}: cmf_pair")
        need(approx(p["used"], eve_nii.cmf_pair(res["CLP"], res["UR"], offset)), f"{s}: used pair")
        d_clp.append(res["CLP"])
        d_ur.append(res["UR"])
        totals.append(row["total_delta_eve"])
    a1 = eve_nii.annex1_delta_eve(np.array(d_clp), np.array(d_ur), offset)
    need(approx(out["eve"]["delta_eve"], a1.delta_eve) and out["eve"]["worst_shock"] == a1.worst_shock, "annex1_delta_eve")
    need(np.allclose(totals, a1.pairs, rtol=1e-9, atol=1e-6), "annex1_delta_eve pairs")
    n_clp, n_ur = [], []
    for row in out["nii"]["rows"]:
        bp = row["clp"]["shock_bp"]
        for name, key, acc in (("CLP", "clp", n_clp), ("UR", "ur", n_ur)):
            shocked = shocks.apply_floor(rates[name], np.full(19, bp), floors[name])
            v = eve_nii.delta_nii(base[name], rates[name], shocked, MID)
            need(approx(row[key]["delta_nii"], v), f"nii {bp}/{name}: delta_nii")
            acc.append(v)
    pn = out["indexation_charge"]["pn_ur"]
    a2 = eve_nii.annex1_delta_nii(np.array(n_clp), np.array(n_ur), pn, offset)
    need(approx(out["nii"]["max_pair"], a2.max_pair) and approx(out["nii"]["delta_nii"], a2.delta_nii) and approx(out["indexation_charge"]["charge"], a2.indexation_charge),
         "annex1_delta_nii")
    th = out["thresholds"]
    pb = eve_nii.prioritised_bank(a2.delta_nii, a1.delta_eve, th["tier1"], th["net_interest_and_indexation_margin_12m"])
    need([t["id"] for t in th["tests"]] == [t["id"] for t in pb.tests] and th["prioritised"] == pb.prioritised, "prioritised_bank")
    for got, want in zip(th["tests"], pb.tests):
        need(approx(got["ratio"], want["ratio"], 1e-6, 1e-9) and got["breached"] == want["breached"], f"prioritised_bank {got['id']}")
    for e in out["floors"]["effects"]:
        row = next(r for r in (out["eve"]["rows"] if e["measure"] == "delta-eve" else out["nii"]["rows"]) if r["shock"] == e["shock"])
        name, key = ("CLP", "clp") if e["leg"] == "CLP" else ("UR", "ur")
        if e["measure"] == "delta-eve":
            z = sizes["CLP" if name == "CLP" else "CLF"]
            shape = shocks.shock_curve(e["shock"], z.parallel_bp, z.short_bp, z.long_bp, MID)
            free = shocks.apply_floor(rates[name], shape, None)
            want = eve_nii.delta_eve(base[name], np.array(row[key]["net_cash_flows"]), rates[name], free, MID, kao=0.0)
        else:
            free = shocks.apply_floor(rates[name], np.full(19, row[key]["shock_bp"]), None)
            want = eve_nii.delta_nii(base[name], rates[name], free, MID)
        need(approx(e["delta_without_floor"], want), f"floor effect {e['leg']}/{e['shock']}")
    for leg in out["dynamic_nii"]["legs"]:
        its = leg["items"]
        arrs = (np.array([i["balance"] for i in its]), np.array([1 if i["side"] == "asset" else -1 for i in its]), np.array([i["rate0"] for i in its]),
                np.array([i["spread"] for i in its]), np.array([i["beta"] for i in its]), np.array([i["reprice_months"] for i in its]))
        for sc in leg["scenarios"]:
            res = simulation.simulate_nii(*arrs, np.array(sc["short_rate_path"]), out["dynamic_nii"]["balance_sheet_assumption"]["growth_annual"])
            need(np.allclose(res.monthly_nii, sc["monthly_nii"], rtol=1e-9, atol=1e-6) and approx(res.total, sc["total"]), f"dynamic NII {leg['leg']}/{sc['scenario']}")
    return bad


def test_every_number_of_a_document_equals_the_engine_call_on_its_inputs() -> None:
    for vid in VARIANT_IDS:
        assert engine_findings(d.variant(vid)["outputs"]) == [], vid
    assert tuple(s for s in SHOCKS) == tuple(shocks.SHOCKS)
    for vid in VARIANT_IDS:
        doc = d.variant(vid)
        by = {t["test_id"]: t for t in doc["tests"]}
        assert by["irrbb.srp31_92_goldens"]["light"] == "green" and by["irrbb.cmf_annex1_goldens"]["light"] == "green"
        sums = [t for t in doc["tests"] if t["test_id"] == "irrbb.eve_sum_of_parts"]
        assert {t["segment"] for t in sums} == {"CLP", "UR"} and all(t["light"] == "green" for t in sums)
        assert by["irrbb.nmd_parameter_stability"]["light"] == "not_evaluated" and by["irrbb.nmd_parameter_stability"]["notes"]
        # the impact block is not an exact block: its numbers carry nine significant digits
        assert doc["impact"]["delta_eve"]["value"] == pytest.approx(doc["outputs"]["eve"]["delta_eve"], rel=1e-8)
        assert doc["impact"]["delta_nii"]["value"] == pytest.approx(doc["outputs"]["nii"]["delta_nii"], rel=1e-8)


def test_the_ear_evar_of_a_document_equals_the_engine_call_on_its_inputs() -> None:
    """Rung 6 recomputed with the engine from the parameters, the seed and the curve the document carries (one variant: 100 000 paths a leg)."""
    o = d.variant("long-uf")["outputs"]
    uf = o["ur_currency"]["uf_value"]
    for e, key, name in zip(o["ear_evar"], ("clp", "ur"), ("CLP", "UR")):
        pts = o["curves"][key]["points"]
        par = {p["name"]: p["value"] for p in e["parameters"]}
        floor = o["floors"]["other_floor"] if name == "CLP" else o["floors"]["ur_floor"]
        r0 = np.array(o["curves"][key]["zero_rates_at_midpoints"])
        paths = simulation.hw1f_scenarios(np.array([p["zero_rate"] for p in pts]), np.array([p["tenor_years"] for p in pts]), par["a"], par["sigma"],
                                          e["horizon_months"], e["n_paths"], e["seed"])
        leg = next(x for x in o["dynamic_nii"]["legs"] if x["leg"] == name)
        its = leg["items"]
        arrs = (np.array([i["balance"] for i in its]), np.array([1 if i["side"] == "asset" else -1 for i in its]), np.array([i["rate0"] for i in its]),
                np.array([i["spread"] for i in its]), np.array([i["beta"] for i in its]), np.array([i["reprice_months"] for i in its]))
        nii_p = np.array([simulation.simulate_nii(*arrs, q[:e["horizon_months"]], 0.0).total for q in paths])
        conv = uf if name == "UR" else 1.0
        base = sum(dense(f["cash_flows"]) * conv for x in o["legs"] if x["leg"] == name for f in x["items"])
        eve_p = np.array([eve_nii.eve(base, shocks.apply_floor(r0, np.full(19, (q[-1] - q[0]) * 1e4), floor), MID) for q in paths])
        for lv in e["levels"]:
            got = simulation.ear_evar(nii_p, eve_p, e["base_nii"], e["base_eve"], lv["level"])
            err = simulation.ear_evar_mc_error(nii_p, eve_p, lv["level"], e["n_batches"])
            assert approx(lv["ear"], got.ear) and approx(lv["evar"], got.evar), (name, lv["level"])
            assert approx(lv["ear_se"], err.ear_se) and approx(lv["evar_se"], err.evar_se), (name, lv["level"])
