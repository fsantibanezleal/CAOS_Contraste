"""One valuation date of C14 (c14-outputs): the balance sheet slotted, the curve, the six shocks under four scenarios, the ladder,
the dynamic NII, EaR and EVaR, the out-of-sample row and the validation tests.

Every EVE, delta EVE, delta NII, shock shape, floor, outlier test, gap, duration gap, simulated NII, EaR, EVaR and Monte Carlo error
is a ``riskvalidation`` call (ADR-0069); this module builds their inputs from the call report and the Treasury curve of the date and
puts their outputs in the document. The one thing it computes itself is the list of buckets where the post-shock floor binds, a
comparison the contract states in the field (``floor_bound_buckets``) and ``semantics.check_c14`` recomputes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.irrbb import curves as rv_curves
from riskvalidation.irrbb import eve_nii, shocks, simulation
from riskvalidation.irrbb import slotting as rv_slotting
from riskvalidation.validation import irrbb as rv_val

from . import assumptions as asm
from . import fits, slotting
from .fdic import Report, realised_nii, report_at
from .slotting import Item, t
from ...io.treasury import ParCurve, curve_as_of

MID = rv_slotting.bucket_grid().midpoints
SHOCKS = shocks.SHOCKS
CURRENCY = "USD"
UNIT = "USD thousands"
CALIBRATIONS = (("2024", "behavioural"), ("2024", "contractual"), ("2016", "behavioural"), ("2016", "contractual"))
MODEL_ID = "irrbb-eve-standardised"


@dataclass
class VariantResult:
    document: dict[str, Any]
    values: dict[str, float]
    breached: bool                       # the standardised (2024, capped behavioural) outlier test
    fit: dict[str, Any]                  # the replicating fit and betas of the date, for the models document
    requests: dict[str, Any]


def quarter_of(vd: str) -> str:
    return f"{vd[:4]}-Q{(int(vd[5:7]) - 1) // 3 + 1}"


def variant_id(vd: str) -> str:
    return f"vd-{quarter_of(vd).lower()}"


def flows_list(v: np.ndarray) -> list[dict[str, Any]]:
    """The non-zero buckets of a (19,) vector as document flow rows; an item reported at zero carries one zero flow (schema minItems 1)."""
    rows = [{"bucket": k + 1, "midpoint_years": float(MID[k]), "amount": float(v[k])} for k in range(19) if v[k] != 0.0]
    return rows or [{"bucket": 1, "midpoint_years": float(MID[0]), "amount": 0.0}]


def curve_block(vd: str, curve: ParCurve) -> tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray]:
    ten, par = curve.tenors(), curve.yields()
    zero = rv_curves.bootstrap_zero_curve(ten, par, 2)
    r0 = rv_curves.zero_rates_at(ten, zero, MID)
    carried = curve.observation_date != vd
    src = ("US Treasury daily par yield curve (Daily Treasury Par Yield Curve Rates), observation date "
           f"{curve.observation_date}" + (f"; carried to {vd}, the last curve published on or before it" if carried else ""))
    block = {
        "date": vd, "source": src, "observed_kind": "par-yield", "compounding": "continuous",
        "interpolation": "par yields bootstrapped to continuously compounded zero rates (engine bootstrap_zero_curve, semiannual "
                         "bond-equivalent, simple interest up to six months); linear in tenor and flat outside the grid at the 19 midpoints",
        "missing_tenors": curve.missing_tenors(),
        "points": [{"tenor_years": float(a), "observed_yield": float(b), "zero_rate": float(c)} for a, b, c in zip(ten, par, zero)],
        "zero_rates_at_midpoints": [float(x) for x in r0],
    }
    return block, ten, zero, r0


def dynamic_items(r: Report, items: list[Item], r_short: float, beta: float) -> list[dict[str, Any]]:
    """The interest-bearing items of the dynamic NII: balance, current rate, spread and beta, reset months (non-interest items left out).

    Rates are the year-to-date interest of the report, annualised, over the balance at the date."""
    f = 12.0 / int(r.report_date[5:7])
    by = {i.item_id: i for i in items}
    y_loans = r.get("ILNDOM") * f / r.get("LNLSGR")
    y_sec = r.get("ISC") * f / r.get("SC")
    y_cash = (r.get("ICHBAL") + r.get("IFREPO")) * f / (r.get("CHBAL") + r.get("FREPO"))
    rep = asm.REPRICE_MONTHS
    out: list[dict[str, Any]] = []

    def add(item_id: str, side: str, bal: float, rate0: float, b: float, months: int) -> None:
        if bal > 0:
            out.append({"item_id": item_id, "side": side, "balance": float(bal), "rate0": float(rate0), "spread": float(rate0 - b * r_short),
                        "beta": float(b), "reprice_months": int(months)})

    add("D1", "asset", r.get("CHBAL") + r.get("FREPO"), y_cash, 1.0, 0)
    loan_3m = by["A5"].amount
    loan_312 = r.sum("LNOT3T12", "LNRS3T12")
    loan_rest = by["A5"].amount + by["A6"].amount + by["A7"].amount - loan_3m - loan_312
    add("D2", "asset", loan_3m, y_loans, 1.0, rep["floating"])
    add("D3", "asset", loan_312, y_loans, 1.0, rep["3_12m"])
    add("D4", "asset", loan_rest, y_loans, 0.0, rep["fixed"])
    sec_3m, sec_312 = r.sum("SCNM3LES", "SCPT3LES"), r.sum("SCNM3T12", "SCPT3T12")
    sec_rest = r.get("SC") - sec_3m - sec_312
    add("D5", "asset", sec_3m, y_sec, 1.0, rep["floating"])
    add("D6", "asset", sec_312, y_sec, 1.0, rep["3_12m"])
    add("D7", "asset", sec_rest, y_sec, 0.0, rep["fixed"])
    ib = r.sum("DEPIDOM", "DEPIFOR")
    add("D8", "liability", r.sum("DEPNIDOM", "DEPNIFOR"), 0.0, 0.0, 0)
    add("D9", "liability", ib, r.get("EDEP") * f / ib, beta, 0)
    add("D10", "liability", r.sum("OTHBRF", "FREPP"), r_short, 1.0, 0)
    return out


def _arrays(its: list[dict[str, Any]]) -> tuple[np.ndarray, ...]:
    return (np.array([i["balance"] for i in its]), np.array([1 if i["side"] == "asset" else -1 for i in its]),
            np.array([i["rate0"] for i in its]), np.array([i["spread"] for i in its]), np.array([i["beta"] for i in its]),
            np.array([i["reprice_months"] for i in its]))


def bake_variant(vd: str, reports: list[Report], later: list[Report], curves: dict[str, ParCurve], seed: int, n_paths: int,
                 breach_history: dict[str, bool], fit_history: dict[str, float], raw_urls: dict[str, str]) -> VariantResult:
    """One valuation date. ``reports`` and ``curves`` hold nothing after ``vd``; ``later`` is read only by the out-of-sample row."""
    if any(x.report_date > vd for x in reports) or any(d > vd for d in curves):
        raise ValueError(f"{vd}: the inputs of a valuation date hold data dated after it")
    r = report_at(reports, vd)
    quarter = quarter_of(vd)
    cblock, ten, zero, r0 = curve_block(vd, curve_as_of(curves, vd))
    items = slotting.build_items(r)
    if any(i.amount < 0 for i in items):
        raise ValueError(f"{vd}: an item amount is negative; the report identities do not hold")
    series = fits.quarterly_series(reports, curves, vd)
    nmd = fits.nmd_model(series, vd)
    beta_up = nmd["beta"]["up"]
    tier1 = r.get("RBCT1J")
    segs = slotting.nmd_segments(items)
    tot = sum(s["balance"] for s in segs)
    td_amount = sum(i.amount for i in items if i.behavioural_class == "term-deposit")
    tdrr0 = asm.TERM_DEPOSIT_REDEMPTION_RATE
    base_flows = {n: np.sum([getattr(i, n) for i in items], axis=0) for n in ("behavioural", "contractual")}
    floor = asm.FLOOR

    # ---- scenarios: the six shocks per calibration and NMD assumption (engine: shock_curve, apply_floor, eve, delta_eve, delta_nii)
    scenarios, by_cal = [], {}
    for cal, assumption in CALIBRATIONS:
        size = shocks.shock_size(CURRENCY, cal)
        base = base_flows[assumption]
        base_eve = float(eve_nii.eve(base, r0, MID))
        rows, deltas = [], []
        for s in SHOCKS:
            shape = shocks.shock_curve(s, size.parallel_bp, size.short_bp, size.long_bp, MID)
            shocked = shocks.apply_floor(r0, shape, floor)
            moved = td_amount * rv_slotting.term_deposit_redemption_rate(s, tdrr0)
            net = base.copy()
            net[0] -= moved
            net[3] += moved
            d_eve = float(eve_nii.delta_eve(base, net, r0, shocked, MID, kao=0.0))
            parallel = s in ("parallel-up", "parallel-down")
            rows.append({
                "shock": s, "shape_bp": [float(x) for x in shape],
                "floor_bound_buckets": [k + 1 for k in range(19) if r0[k] + shape[k] / 1e4 < min(floor, r0[k])],
                "net_cash_flows": [float(x) for x in net], "eve": float(eve_nii.eve(net, shocked, MID)), "kao": 0.0,
                "delta_eve": d_eve, "delta_eve_share_tier1": d_eve / tier1,
                "delta_nii": float(eve_nii.delta_nii(base, r0, shocked, MID)) if parallel else None,
                "delta_nii_reason": None if parallel else t("Delta NII is reported for the two parallel shocks only (SRP31.90).",
                                                            "El delta NII se informa solo para los dos choques paralelos (SRP31.90)."),
            })
            deltas.append(d_eve)
        measure = float(eve_nii.eve_risk_measure(np.array(deltas).reshape(6, 1)))
        o = eve_nii.outlier_test(measure, tier1)
        scenarios.append({
            "calibration": cal, "nmd_assumption": assumption,
            "nmd_treatment": "standardised-capped" if assumption == "behavioural" else "contractual-overnight",
            "shock_size": {"currency": size.currency, "parallel_bp": size.parallel_bp, "short_bp": size.short_bp, "long_bp": size.long_bp,
                           "origin": size.origin, "label": size.label, "method": size.method},
            "floor": floor, "base_eve": base_eve, "shocks": rows, "eve_risk_measure": measure,
            "worst_shock": SHOCKS[int(np.argmax(deltas))] if max(deltas) > 0 else None,
            "outlier": {"threshold_share_tier1": 0.15, "tier1": tier1, "eve_risk_measure": measure, "ratio": float(o.ratio),
                        "breached": bool(o.breached), "reference": "SRP31.82 to SRP31.83 (15 percent of Tier 1)"},
        })
        by_cal[(cal, assumption)] = scenarios[-1]
    comparison = [{"calibration": cal, "shock": s,
                   "delta_eve_behavioural": by_cal[(cal, "behavioural")]["shocks"][k]["delta_eve"],
                   "delta_eve_contractual": by_cal[(cal, "contractual")]["shocks"][k]["delta_eve"],
                   "difference": by_cal[(cal, "behavioural")]["shocks"][k]["delta_eve"] - by_cal[(cal, "contractual")]["shocks"][k]["delta_eve"]}
                  for cal in ("2024", "2016") for k, s in enumerate(SHOCKS)]

    # ---- ladder rungs 1 and 2 (engine: repricing_gap, delta_nii_gap, duration_gap)
    ladder = []
    for assumption in ("behavioural", "contractual"):
        a_flows = np.sum([getattr(i, assumption) for i in items if i.side == "asset"], axis=0)
        l_flows = -np.sum([getattr(i, assumption) for i in items if i.side == "liability"], axis=0)
        gap = eve_nii.repricing_gap(a_flows, l_flows)
        dg = eve_nii.duration_gap(a_flows, l_flows, r0, MID)
        ladder.append({
            "nmd_assumption": assumption,
            "repricing_gap": [{"bucket": k + 1, "midpoint_years": float(MID[k]), "assets": float(a_flows[k]), "liabilities": float(l_flows[k]),
                               "gap": float(gap[k])} for k in range(19)],
            "delta_nii_gap_100bp_up": float(eve_nii.delta_nii_gap(gap, MID, 100.0)),
            "duration_gap": {"asset_value": dg.asset_value, "liability_value": dg.liability_value,
                             "asset_duration_years": dg.asset_duration_years, "liability_duration_years": dg.liability_duration_years,
                             "duration_gap_years": dg.duration_gap_years, "equity_change_100bp_up": dg.equity_change_100bp_up}})

    # ---- rung 5: the dynamic NII under the base path and the two parallel shocks (engine: simulate_nii)
    r_short = float(r0[1])
    dyn_items = dynamic_items(r, items, r_short, beta_up)
    sc0 = scenarios[0]
    par = sc0["shock_size"]["parallel_bp"]
    arrs = _arrays(dyn_items)
    dyn_sc, base_total = [], None
    for name, bp in (("base", 0.0), ("parallel-up", float(par)), ("parallel-down", -float(par))):
        rate = float(shocks.apply_floor(np.array([r_short]), np.array([bp]), floor)[0])
        path = np.full(asm.HORIZON_MONTHS, rate)
        res = simulation.simulate_nii(*arrs, path, 0.0)
        base_total = res.total if base_total is None else base_total
        dyn_sc.append({"scenario": name, "shock_bp": bp, "short_rate_path": [float(x) for x in path],
                       "monthly_nii": [float(x) for x in res.monthly_nii], "total": float(res.total),
                       "delta_vs_base": float(base_total - res.total)})
    dynamic = {
        "horizon_months": asm.HORIZON_MONTHS,
        "balance_sheet_assumption": {"kind": "constant", "growth_annual": 0, "description": t(
            "Constant balance sheet: maturing and repricing flows are replaced by identical new ones. Non-interest items are left out.",
            "Balance constante: los flujos que vencen o reprecian se reemplazan por otros identicos. Las partidas sin interes se omiten.")},
        "items": dyn_items, "scenarios": dyn_sc}

    # ---- rung 6: EaR and EVaR under Hull-White one-factor scenarios (engine: hw1f_scenarios, ear_evar, ear_evar_mc_error)
    sigma = fits.sigma_3y(curves, vd)
    paths = simulation.hw1f_scenarios(zero, ten, asm.HW1F_A, sigma, asm.HORIZON_MONTHS, n_paths, seed)
    nii_p = np.array([simulation.simulate_nii(*arrs, q[:asm.HORIZON_MONTHS], 0.0).total for q in paths])
    flows_b = base_flows["behavioural"]
    eve_p = np.array([eve_nii.eve(flows_b, shocks.apply_floor(r0, np.full(19, (q[-1] - q[0]) * 1e4), floor), MID) for q in paths])
    base_nii, base_eve = dyn_sc[0]["total"], sc0["base_eve"]
    levels = []
    for lv in asm.LEVELS:
        got = simulation.ear_evar(nii_p, eve_p, base_nii, base_eve, lv)
        err = simulation.ear_evar_mc_error(nii_p, eve_p, lv, asm.N_BATCHES)
        levels.append({"level": lv, "nii_quantile": float(base_nii - got.ear), "eve_quantile": float(base_eve - got.evar),
                       "ear": float(got.ear), "evar": float(got.evar), "ear_se": float(err.ear_se), "evar_se": float(err.evar_se)})
    ear_evar = {"method": "hw1f", "n_paths": n_paths, "seed": seed, "horizon_months": asm.HORIZON_MONTHS,
                "parameters": [{"name": "a", "value": asm.HW1F_A, "unit": "per year"}, {"name": "sigma", "value": float(sigma), "unit": "per year"}],
                "base_nii": float(base_nii), "base_eve": float(base_eve), "levels": levels, "mc_error_method": "batch-means",
                "n_batches": asm.N_BATCHES}

    # ---- the out-of-sample row: the 2021-Q4 projection against the realised 2022 NII; the later dates have no realised year
    projected = dyn_sc[1]["delta_vs_base"]
    realised = None
    if vd[5:] == "12-31" and any(x.report_date == f"{int(vd[:4]) + 1}-12-31" for x in later):
        nxt = int(vd[:4]) + 1
        realised = r.get("NIM") - realised_nii(later, vd, f"{nxt}-01-01", f"{nxt}-12-31")
        oos = {"applicable": True, "projection_date": vd, "realised_period_start": f"{nxt}-01-01", "realised_period_end": f"{nxt}-12-31",
               "projected_delta_nii": projected, "realised_delta_nii": float(realised),
               "relative_error": abs(projected - realised) / abs(realised), "reason": None}
    else:
        oos = {"applicable": False, "projection_date": vd, "realised_period_start": None, "realised_period_end": None,
               "projected_delta_nii": None, "realised_delta_nii": None, "relative_error": None,
               "reason": t("No realised year follows this date in the call reports: the bank failed on 2023-03-10 and filed no later "
                           "report, so the 12-month projection cannot be compared with a realised one.",
                           "Ningun anio completo posterior a esta fecha esta en los reportes: el banco quebro el 2023-03-10 y no presento "
                           "reportes posteriores, por lo que la proyeccion a 12 meses no se compara con una realizada.")}

    # ---- the validation tests (engine: riskvalidation.validation.irrbb)
    dates = [d for d in sorted(set(breach_history) | {vd}) if d <= vd]
    breach_all = {**breach_history, vd: bool(sc0["outlier"]["breached"])}
    wam_hist = {**fit_history, vd: nmd["fit"]["weighted_average_maturity_years"]}
    item_flows = np.array([i.behavioural for i in items])
    tests = [
        rv_val.srp31_92_goldens(),
        rv_val.eve_sum_of_parts(item_flows, r0, MID, sc0["base_eve"]),
        rv_val.eve_with_without_behavioural(sc0["eve_risk_measure"], by_cal[("2024", "contractual")]["eve_risk_measure"], tier1),
        rv_val.nmd_parameter_stability(np.array([w["weights"] for w in nmd["stability"]]), np.array([m for _, m in asm.TRANCHES])),
        rv_val.behavioural_change_at_breach(np.array([wam_hist[d] for d in dates]), np.array(dates, dtype="datetime64[D]"),
                                            np.array([breach_all[d] for d in dates], dtype=bool)),
        rv_val.nii_out_of_sample(projected, realised),
    ]
    test_rows = [_plain(x.to_dict()) for x in tests]

    outputs = {
        "kind": "valuation-date", "valuation_date": vd, "quarter": quarter, "currency": CURRENCY,
        "sign_convention": SIGN, "units": UNITS, "bank": BANK,
        "data": {"call_reports": [{"report_date": r.report_date, "source": raw_urls["fdic"],
                                   "fields": sorted(k for k in r.values if k not in ("CERT", "REPDTE", "NAME", "ID"))}],
                 "data_cutoff": r.report_date, "read_up_to_valuation_date": True, "rule": RULE},
        "curve": cblock,
        "assumptions": {
            "nmd_core_share": {"value": sum(s["balance"] * s["core_share_used"] for s in segs) / tot, "unit": "share",
                               "source_kind": "regulatory-cap", "source": "balance-weighted average of the used values of nmd_segments (the SRP31 "
                               "Table 4 caps applied to the synthetic requests)"},
            "nmd_core_maturity_years": {"value": sum(s["balance"] * s["core_maturity_used_years"] for s in segs) / tot, "unit": "years",
                                        "source_kind": "regulatory-cap", "source": "balance-weighted average of the used values of nmd_segments"},
            "prepayment_cpr": _a("prepayment_cpr", asm.PREPAYMENT_CPR),
            "term_deposit_redemption_rate": _a("term_deposit_redemption_rate", tdrr0),
            "deposit_beta": {"value": beta_up, "unit": "pass-through", "source_kind": "fitted",
                             "source": f"{asm.REGISTRY['deposit_beta'].source} Up {beta_up:.4f} on {nmd['beta']['n_up']} quarters, "
                                       f"down {nmd['beta']['down']:.4f} on {nmd['beta']['n_down']}; the dynamic NII uses the up value."}},
        "nmd_segments": segs,
        "balance_sheet": {"as_of": vd, "items": [_item_doc(i) for i in items],
                          "total_assets": float(sum(i.amount for i in items if i.side == "asset")),
                          "total_liabilities": float(sum(i.amount for i in items if i.side == "liability"))},
        "ladder": ladder, "scenarios": scenarios, "dynamic_nii": dynamic, "ear_evar": ear_evar, "out_of_sample": oos,
        "behavioural_comparison": comparison}
    values = {
        "eve_ratio_2024_behavioural": sc0["outlier"]["ratio"], "eve_ratio_2024_contractual": by_cal[("2024", "contractual")]["outlier"]["ratio"],
        "nii_projection_up": projected, "deposit_beta_up": beta_up, "base_nii_over_reported": base_total / (r.get("NIM") * 12.0 / int(vd[5:7])),
    }
    return VariantResult(
        {"outputs": outputs, "tests": test_rows, "impact": _impact(outputs), "findings": _findings(outputs, test_rows), "quarter": quarter},
        values, bool(sc0["outlier"]["breached"]), nmd, {"retail_share": slotting.retail_share(r)})


def _a(name: str, value: float) -> dict[str, Any]:
    a = asm.REGISTRY[name]
    return {"value": value, "unit": a.unit, "source_kind": a.source_kind, "source": a.source}


def _item_doc(i: Item) -> dict[str, Any]:
    return {"item_id": i.item_id, "label": i.label, "side": i.side, "category": i.category, "behavioural_class": i.behavioural_class,
            "repricing_type": i.repricing_type, "source_field": i.source_field,
            "reported_amount": None if i.reported_amount is None else float(i.reported_amount), "reason_missing": i.reason_missing,
            "slotting_assumption": i.slotting_assumption, "amount": float(i.amount),
            "cash_flows": {"behavioural": flows_list(i.behavioural), "contractual": flows_list(i.contractual)}}


def _plain(x: Any) -> Any:
    if isinstance(x, dict):
        return {k: _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if isinstance(x, (np.floating, np.integer)):
        return x.item()
    if isinstance(x, np.bool_):
        return bool(x)
    return x


SIGN = {"delta_eve": "positive-is-loss", "delta_nii": "positive-is-loss", "reference": "SRP31.129; dossier 01 H.4",
        "statement": t("A positive delta EVE or delta NII is a loss; only losses are aggregated across currencies.",
                       "Un delta EVE o delta NII positivo es una perdida; solo las perdidas se agregan entre monedas.")}
UNITS = {"money_scale": "thousands", "rate": "decimal", "compounding": "continuous", "shock": "basis-points", "bucket_midpoint": "years",
         "dates": "ISO-8601"}
BANK = {"name": "Silicon Valley Bank", "cert": 24735, "aggregates": "real", "behaviour": "synthetic",
        "notice": t("The call-report aggregates are the bank's own, read from the FDIC BankFind financials. Every behavioural assumption "
                    "(deposit core share and maturity, prepayment, term-deposit redemption, the slotting of the report bands) is "
                    "synthetic and stated in the document.",
                    "Los agregados del reporte son los del banco, leidos de los estados financieros de FDIC BankFind. Todo supuesto "
                    "de comportamiento (proporcion y plazo estables de los depositos, prepago, rescate de depositos a plazo, la "
                    "distribucion de las bandas del reporte) es sintetico y esta declarado en el documento.")}
RULE = t("Call reports are read only up to the valuation date; later reports are never read for the valuation (only the out-of-sample "
         "row reads the realised year).",
         "Los reportes se leen solo hasta la fecha de valoracion; los posteriores nunca se leen para la valoracion (solo la fila fuera "
         "de muestra lee el anio realizado).")


def _impact(o: dict[str, Any]) -> dict[str, Any]:
    sc = {(s["calibration"], s["nmd_assumption"]): s for s in o["scenarios"]}
    l99 = o["ear_evar"]["levels"][1]

    def item(v: float, unit: str, en: str, es: str) -> dict[str, Any]:
        return {"value": float(v), "unit": unit, "label": t(en, es)}

    return {
        "eve_risk_measure_behavioural": item(sc[("2024", "behavioural")]["eve_risk_measure"], UNIT,
                                             "EVE risk measure, 2024 shocks, behavioural NMD", "Medida de riesgo EVE, choques 2024, NMD conductual"),
        "eve_risk_measure_contractual": item(sc[("2024", "contractual")]["eve_risk_measure"], UNIT,
                                             "EVE risk measure, 2024 shocks, contractual NMD", "Medida de riesgo EVE, choques 2024, NMD contractual"),
        "outlier_ratio_behavioural": item(sc[("2024", "behavioural")]["outlier"]["ratio"], "share of Tier 1",
                                          "EVE risk measure over Tier 1, behavioural NMD", "Medida de riesgo EVE sobre capital Tier 1, NMD conductual"),
        "outlier_ratio_contractual": item(sc[("2024", "contractual")]["outlier"]["ratio"], "share of Tier 1",
                                          "EVE risk measure over Tier 1, contractual NMD", "Medida de riesgo EVE sobre capital Tier 1, NMD contractual"),
        "ear_99": item(l99["ear"], UNIT, "EaR at 99 percent, 12 months", "EaR al 99 por ciento, 12 meses"),
        "evar_99": item(l99["evar"], UNIT, "EVaR at 99 percent, 12 months", "EVaR al 99 por ciento, 12 meses")}


def _findings(o: dict[str, Any], tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by = {x["test_id"]: x for x in tests}
    sc = {(s["calibration"], s["nmd_assumption"]): s for s in o["scenarios"]}
    beh, con = sc[("2024", "behavioural")]["outlier"], sc[("2024", "contractual")]["outlier"]
    wb = by["irrbb.eve_with_without_behavioural"]
    out = []
    sev = {"red": "S1", "amber": "S2", "green": "S4"}.get(wb["light"], "S3")
    out.append({"id": "F1", "severity": sev, "status": "open", "evidence": ["irrbb.eve_with_without_behavioural"], "title": t(
        f"The EVE risk measure is {beh['ratio'] * 100:.1f} percent of Tier 1 with the capped behavioural NMD and "
        f"{con['ratio'] * 100:.1f} percent with every non-maturity deposit overnight; the outlier threshold is 15 percent.",
        f"La medida de riesgo EVE es {beh['ratio'] * 100:.1f} por ciento del Tier 1 con NMD conductual con tope y "
        f"{con['ratio'] * 100:.1f} por ciento con todos los depositos a la vista a un dia; el umbral del test es 15 por ciento.")})
    out.append({"id": "F2", "severity": "S3", "status": "open", "evidence": ["design:retail-share-is-a-synthetic-mapping"], "title": t(
        "The split of deposits between retail and wholesale and every core share and maturity are synthetic: the call report carries none.",
        "La separacion de depositos entre minoristas y mayoristas y toda proporcion y plazo estables son sinteticos: el reporte no los trae.")})
    oos = o["out_of_sample"]
    if oos["applicable"]:
        rel = by["irrbb.nii_out_of_sample"]
        out.append({"id": "F3", "severity": {"green": "S4", "amber": "S3", "red": "S2"}.get(rel["light"], "S3"), "status": "open",
                    "evidence": ["irrbb.nii_out_of_sample"], "title": t(
            f"The 12-month change in NII projected for a +{o['scenarios'][0]['shock_size']['parallel_bp']:.0f} bp shock differs from the "
            f"realised 2022 change by {oos['relative_error'] * 100:.0f} percent; the shock is not the realised path.",
            f"El cambio a 12 meses del NII proyectado para un choque de +{o['scenarios'][0]['shock_size']['parallel_bp']:.0f} pb difiere "
            f"del cambio realizado en 2022 en {oos['relative_error'] * 100:.0f} por ciento; el choque no es la trayectoria realizada.")})
    st, ch = by["irrbb.nmd_parameter_stability"], by["irrbb.behavioural_change_at_breach"]
    if st["light"] in ("red", "amber"):
        out.append({"id": "F4", "severity": "S2" if st["light"] == "red" else "S3", "status": "open",
                    "evidence": ["irrbb.nmd_parameter_stability"], "title": t(
            f"The fitted replicating-portfolio weights move by up to {st['statistic']:.2f} between estimation windows and the weighted "
            f"average maturity by up to {st['metric']:.1f} years: the deposit duration the data support is not stable.",
            f"Los pesos de la cartera replicante ajustada se mueven hasta {st['statistic']:.2f} entre ventanas de estimacion y el plazo "
            f"promedio ponderado hasta {st['metric']:.1f} anios: la duracion de los depositos que respalda la data no es estable.")})
    if ch["light"] == "red":
        out.append({"id": "F5", "severity": "S2", "status": "open", "evidence": ["irrbb.behavioural_change_at_breach"], "title": t(
            f"The fitted weighted average maturity changed at {ch['statistic']:.0f} date(s) where the standardised outlier test was breached: "
            "a deposit-duration assumption that moves with a breach is the pattern the Federal Reserve review describes.",
            f"El plazo promedio ponderado ajustado cambio en {ch['statistic']:.0f} fecha(s) en que se supero el test de valores atipicos "
            "estandarizado: un supuesto de duracion de depositos que se mueve con un exceso es el patron que describe la revision de la Reserva Federal.")})
    return out
