"""One variant of C15 (c15-outputs, ``annex1-variant``): the book of Banco Andino on the BCCh curves under RAN 21-13 Annex 1.

Every EVE, delta EVE, delta NII, shock shape, floor, offset pair, indexation charge, prioritised-bank test, simulated NII and validation
test is a ``riskvalidation`` call (ADR-0069); this module builds their inputs from the book and the fitted curves and puts their outputs in
the document. The product computes only what the contract states as a field and ``semantics.check_c15`` recomputes: the buckets where a floor
binds (a comparison), the smallest distance to a floor (a minimum of engine outputs) and the effect of the CPI surprise
(``-PN_UR x surprise / 100``, the formula of the contract: the engine has no function for it).
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
from . import curves as c15_curves
from . import targets
from .book import MID, Book, Item, t

SHOCKS = shocks.SHOCKS
PARALLEL = ("parallel-up", "parallel-down")
UR_FLOOR = -0.02
OTHER_FLOOR = 0.0
NII_BP = 300.0
MODEL_ID = "irrbb-annex1"
UNIT = "CLP millions"
CONV_NOTE = "UR amounts are CLF (UF) millions in the legs and CLP millions where the measures are added"

SIGN = {"delta_eve": "positive-is-loss", "delta_nii": "positive-is-loss", "reference": "SRP31.129; dossier 01 H.4",
        "statement": t("A positive delta EVE or delta NII is a loss; only losses are aggregated across currencies.",
                       "Un delta EVE o delta NII positivo es una pérdida; solo las pérdidas se agregan entre monedas.")}
UNITS = {"money_scale": "millions", "rate": "decimal", "compounding": "continuous", "shock": "basis-points", "bucket_midpoint": "years",
         "dates": "ISO-8601"}


def es(x: float, nd: int = 1) -> str:
    """A number in a Spanish document string: the decimal comma."""
    return f"{x:.{nd}f}".replace(".", ",")


def bank_block(seed: int, calibration_source: str) -> dict[str, Any]:
    return {"name": "Banco Andino", "synthetic": True, "seed": seed, "calibration_source": calibration_source,
            "notice": t("Banco Andino is a synthetic bank. Its balance-sheet aggregates are calibrated to the CMF system aggregates of August 2026; "
                        "the UF share, the repricing profile of each item, the deposit split and every behavioural assumption are synthetic and "
                        "stated in the document. The curves are real: the Banco Central de Chile F022 yields of the valuation date.",
                        "Banco Andino es un banco sintético. Los agregados de su balance están calibrados a los agregados del sistema de la CMF de "
                        "agosto de 2026; la proporción en UF, el perfil de reprecio de cada partida, la separación de depósitos y todo supuesto de "
                        "comportamiento son sintéticos y están declarados en el documento. Las curvas son reales: los rendimientos F022 del Banco "
                        "Central de Chile de la fecha de valoración.")}


UR_BLOCK = {"label": "UR", "code": "CLF", "treated_as_one_currency": True,
            "definition": t("All CLP-indexed (UF) flows are treated as one currency, UR (RAN 21-13 Annex 1).",
                            "Todos los flujos reajustables (UF) se tratan como una sola moneda, UR (RAN 21-13 Anexo 1).")}
OFFSET_RULE = t("When delta CLP and delta CLF have opposite signs, half of the CLP is offset against the CLF (or the reverse), floored at zero.",
                "Si los deltas CLP y CLF tienen signos opuestos, se compensa la mitad del CLP contra el CLF (o al revés), con piso en cero.")


@dataclass
class VariantResult:
    document: dict[str, Any]
    values: dict[str, float]
    fit: dict[str, Any]


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


def _wam(flows: np.ndarray) -> float:
    a = np.abs(flows)
    return float((a * MID).sum() / a.sum())


def _net_flows(items: list[Item], conv: float, shock: str, tdrr0: float) -> np.ndarray:
    """The leg's flows under a shock in CLP: the term deposits are redeemed in bucket 1 at the engine's rate, the rest of them scaled."""
    net = np.zeros(19)
    for it in items:
        v = it.flows * conv
        if it.behavioural_class == "term-deposit":
            r = rv_slotting.term_deposit_redemption_rate(shock, tdrr0)
            amount = abs(float(v.sum()))
            v = v * (1.0 - r)
            v[0] -= r * amount
        net += v
    return net


def _dyn_items(items: list[Item], conv: float, r0: np.ndarray) -> list[dict[str, Any]]:
    """The dynamic NII items of a leg: balance in CLP, current rate, spread, beta and reset months, from the item's kind (synthetic)."""
    r_short = float(r0[1])
    out = []
    for it in items:
        kind, margin = it.dyn["kind"], it.dyn["margin"]
        m = asm.MARGINS.get(margin, 0.0) if margin else 0.0
        if kind == "floating":
            spread, beta, months = m, 1.0, 0 if margin in ("cash", "interbank") else asm.REPRICE_MONTHS["floating"]
            rate0 = r_short + spread
        elif kind == "time":
            spread, beta, months = m, 1.0, asm.REPRICE_MONTHS["time"]
            rate0 = r_short + spread
        elif kind == "nmd":
            spread, beta, months = 0.0, asm.DEPOSIT_BETA, 0
            rate0 = beta * r_short
        else:
            rate0 = float(rv_curves.zero_rates_at(MID, r0, np.array([_wam(it.flows)]))[0]) + m
            spread, beta, months = rate0, 0.0, asm.REPRICE_MONTHS["fixed"]
        out.append({"item_id": it.item_id, "side": it.side, "balance": float(it.amount * conv), "rate0": float(rate0), "spread": float(spread),
                    "beta": float(beta), "reprice_months": int(months)})
    return out


def _arrays(its: list[dict[str, Any]]) -> tuple[np.ndarray, ...]:
    return (np.array([i["balance"] for i in its]), np.array([1 if i["side"] == "asset" else -1 for i in its]),
            np.array([i["rate0"] for i in its]), np.array([i["spread"] for i in its]), np.array([i["beta"] for i in its]),
            np.array([i["reprice_months"] for i in its]))


def _bound(r0: np.ndarray, shape: np.ndarray, floor: float, n: int = 19) -> list[int]:
    """The buckets where the post-shock rate would fall below its floor (a comparison the contract states in the field)."""
    return [k + 1 for k in range(n) if r0[k] + shape[k] / 1e4 < min(floor, r0[k])]


def bake_variant(vid: str, book: Book, fits: dict[str, c15_curves.CurveFit], sel: c15_curves.Selection, uf_source: str,
                 calibration_source: str, raw_urls: dict[str, str], seed: int = 42, n_paths: int | None = None) -> VariantResult:
    spec, uf = book.spec, book.uf_value
    if spec.id != vid:
        raise ValueError(f"{vid}: the book is the one of {spec.id}")
    vd = sel.valuation_date
    r0 = {"CLP": fits["CLP"].rates, "UR": fits["UR"].rates}
    floors = {"CLP": OTHER_FLOOR, "UR": UR_FLOOR}
    conv = {"CLP": 1.0, "UR": uf}
    items = {n: book.legs[n].items for n in ("CLP", "UR")}
    tdrr0 = asm.TERM_DEPOSIT_REDEMPTION_RATE
    offset = spec.offset_state != "off"
    base = {n: sum(it.flows * conv[n] for it in items[n]) for n in items}
    base_eve = {n: float(eve_nii.eve(base[n], r0[n], MID)) for n in items}
    sizes = {"CLP": shocks.shock_size("CLP", "cmf-annex1"), "UR": shocks.shock_size("CLF", "cmf-annex1")}
    table = shocks.shock_table("cmf-annex1")
    tier1 = book.tier1
    pn_ur = book.net_uf_position * uf

    # ---- the six shocks on EVE (engine: shock_curve, apply_floor, eve, delta_eve, cmf_pair, annex1_delta_eve)
    eve_rows, d_clp, d_ur = [], [], []
    for s in SHOCKS:
        legs, delta = {}, {}
        for n in ("CLP", "UR"):
            z = sizes[n]
            shape = shocks.shock_curve(s, z.parallel_bp, z.short_bp, z.long_bp, MID)
            shocked = shocks.apply_floor(r0[n], shape, floors[n])
            net = _net_flows(items[n], conv[n], s, tdrr0)
            delta[n] = float(eve_nii.delta_eve(base[n], net, r0[n], shocked, MID, kao=0.0))
            legs[n] = {"shape_bp": [float(x) for x in shape], "floor_bound_buckets": _bound(r0[n], shape, floors[n]),
                       "net_cash_flows": [float(x) for x in net], "eve": float(eve_nii.eve(net, shocked, MID)), "kao": 0.0, "delta_eve": delta[n]}
        with_o, without_o = (float(eve_nii.cmf_pair(delta["CLP"], delta["UR"], o)) for o in (True, False))
        used = with_o if offset else without_o
        eve_rows.append({"shock": s, "clp": legs["CLP"], "ur": legs["UR"],
                         "pair": {"delta_clp": delta["CLP"], "delta_ur": delta["UR"], "opposite_signs": bool(delta["CLP"] * delta["UR"] < 0),
                                  "with_offset": with_o, "without_offset": without_o, "used": used}, "total_delta_eve": used})
        d_clp.append(delta["CLP"])
        d_ur.append(delta["UR"])
    a1 = eve_nii.annex1_delta_eve(np.array(d_clp), np.array(d_ur), offset)
    eve_block = {"base_eve_clp": base_eve["CLP"], "base_eve_ur": base_eve["UR"], "rows": eve_rows, "delta_eve": float(a1.delta_eve),
                 "worst_shock": a1.worst_shock, "delta_eve_share_tier1": float(a1.delta_eve) / tier1}

    # ---- the 300 bp parallel shocks on NII (engine: apply_floor, delta_nii, cmf_pair, annex1_delta_nii)
    nii_rows, n_clp, n_ur = [], [], []
    for s, bp in (("parallel-up", NII_BP), ("parallel-down", -NII_BP)):
        legs, delta = {}, {}
        for n in ("CLP", "UR"):
            shocked = shocks.apply_floor(r0[n], np.full(19, bp), floors[n])
            delta[n] = float(eve_nii.delta_nii(base[n], r0[n], shocked, MID))
            legs[n] = {"shock_bp": bp, "cash_flows": [float(x) for x in base[n][:6]], "floor_bound_buckets": _bound(r0[n], np.full(19, bp), floors[n], 6),
                       "delta_nii": delta[n]}
        with_o, without_o = (float(eve_nii.cmf_pair(delta["CLP"], delta["UR"], o)) for o in (True, False))
        nii_rows.append({"shock": s, "clp": legs["CLP"], "ur": legs["UR"],
                         "pair": {"delta_clp": delta["CLP"], "delta_ur": delta["UR"], "opposite_signs": bool(delta["CLP"] * delta["UR"] < 0),
                                  "with_offset": with_o, "without_offset": without_o, "used": with_o if offset else without_o}})
        n_clp.append(delta["CLP"])
        n_ur.append(delta["UR"])
    a2 = eve_nii.annex1_delta_nii(np.array(n_clp), np.array(n_ur), pn_ur, offset)
    nii_block = {"rows": nii_rows, "max_pair": float(a2.max_pair), "indexation_charge": float(a2.indexation_charge), "delta_nii": float(a2.delta_nii),
                 "worst_shock": a2.worst_shock, "delta_nii_share_tier1": float(a2.delta_nii) / tier1}

    # ---- the floors: where they bind, their effect, and the smallest distance to them (engine: apply_floor without a floor)
    effects = []
    for row in eve_rows:
        for n, key in (("CLP", "clp"), ("UR", "ur")):
            bound = row[key]["floor_bound_buckets"]
            if bound:
                z = sizes[n]
                free = shocks.apply_floor(r0[n], shocks.shock_curve(row["shock"], z.parallel_bp, z.short_bp, z.long_bp, MID), None)
                without = float(eve_nii.delta_eve(base[n], np.array(row[key]["net_cash_flows"]), r0[n], free, MID, kao=0.0))
                effects.append({"leg": n, "measure": "delta-eve", "shock": row["shock"], "buckets_floored": len(bound),
                                "delta_with_floor": row[key]["delta_eve"], "delta_without_floor": without, "effect": row[key]["delta_eve"] - without})
    for row in nii_rows:
        for n, key in (("CLP", "clp"), ("UR", "ur")):
            bound = row[key]["floor_bound_buckets"]
            if bound:
                free = shocks.apply_floor(r0[n], np.full(19, row[key]["shock_bp"]), None)
                without = float(eve_nii.delta_nii(base[n], r0[n], free, MID))
                effects.append({"leg": n, "measure": "delta-nii", "shock": row["shock"], "buckets_floored": len(bound),
                                "delta_with_floor": row[key]["delta_nii"], "delta_without_floor": without, "effect": row[key]["delta_nii"] - without})
    # the distance of each leg and shock to its floor: the lowest post-shock rate of the engine's shocked curve (before the floor) and its bucket
    distances: list[dict[str, Any]] = []
    for n, key in (("CLP", "clp"), ("UR", "ur")):
        for measure, rows, m_buckets in (("delta-eve", eve_rows, 19), ("delta-nii", nii_rows, 6)):
            for row in rows:
                shape = np.array(row[key]["shape_bp"]) if measure == "delta-eve" else np.full(19, row[key]["shock_bp"])
                free = shocks.apply_floor(r0[n], shape, None)[:m_buckets]
                k = int(np.argmin(free))
                gap = (float(free[k]) - floors[n]) * 1e4
                distances.append({"leg": n, "measure": measure, "shock": row["shock"], "lowest_rate": float(free[k]), "bucket": k + 1,
                                  "floor": floors[n], "distance_bp": gap, "binds": bool(gap <= 0.0)})
    low = min(distances, key=lambda d: d["distance_bp"])
    dist = low["distance_bp"]
    where = f"{low['leg']}, {'delta EVE' if low['measure'] == 'delta-eve' else 'delta NII'}, {low['shock']}"
    n_bound = sum(1 for d in distances if d["binds"])
    floors_block = {
        "ur_floor": UR_FLOOR, "other_floor": OTHER_FLOOR, "effects": effects, "distances": distances,
        "rule": t("Post-shock rates are floored at -2 percent for UR and at 0 percent for CLP (RAN 21-13 Annex 1); the engine's apply_floor also keeps "
                  "a rate that is already below its floor at its pre-shock value, a reading that is UNVERIFIED for the UR floor. The smallest distance "
                  f"between a post-shock rate and its floor is {dist:.2f} bp ({where}); the floors bind in {n_bound} shock and leg combination"
                  f"{'' if n_bound == 1 else 's'}.",
                  "Las tasas posteriores al choque tienen piso de -2 por ciento para la UR y 0 por ciento para el CLP (RAN 21-13 Anexo 1); apply_floor "
                  "del motor también mantiene en su valor previo una tasa que ya está bajo su piso, lectura que no está verificada para el piso UR. "
                  f"La menor distancia entre una tasa posterior al choque y su piso es {es(dist, 2)} pb ({where}); los pisos actúan en {n_bound} "
                  f"combinación{'' if n_bound == 1 else 'es'} de choque y tramo.")}

    # ---- the indexation charge and the CPI surprise
    ic = float(eve_nii.indexation_charge(pn_ur))
    indexation = {"rate": 0.025, "net_position_uf_units": float(book.net_uf_position), "pn_ur": float(pn_ur), "abs_pn_ur": float(abs(pn_ur)), "charge": ic,
                  "formula": "charge = 0.025 x |PN_UR|, PN_UR = net UF position x UF value",
                  "note": t("The standardised indexation (reajustabilidad) charge, an implied 2.5 percent inflation surprise on the net UF position, "
                            "added once to the largest pair of the delta NII.",
                            "El cargo estándar por reajustabilidad, equivalente a una sorpresa de inflación de 2,5 por ciento sobre la posición neta en "
                            "UF, se suma una vez al mayor par del delta NII.")}
    cpi = None
    if spec.cpi_surprise_pp is not None:
        cpi = {"surprise_pp": float(spec.cpi_surprise_pp), "effect": float(-pn_ur * spec.cpi_surprise_pp / 100.0),
               "formula": "effect = -pn_ur x surprise_pp / 100 (loss-positive)"}

    # ---- the dynamic NII of both legs under the base path and the two parallel shocks (engine: simulate_nii)
    dyn_legs = []
    for n in ("CLP", "UR"):
        its = _dyn_items(items[n], conv[n], r0[n])
        arrs = _arrays(its)
        r_short = float(r0[n][1])
        scen, first = [], None
        for name, bp in (("base", 0.0), ("parallel-up", NII_BP), ("parallel-down", -NII_BP)):
            rate = float(shocks.apply_floor(np.array([r_short]), np.array([bp]), floors[n])[0])
            path = np.full(asm.HORIZON_MONTHS, rate)
            res = simulation.simulate_nii(*arrs, path, 0.0)
            first = res.total if first is None else first
            scen.append({"scenario": name, "shock_bp": bp, "short_rate_path": [float(x) for x in path],
                         "monthly_nii": [float(x) for x in res.monthly_nii], "total": float(res.total), "delta_vs_base": float(first - res.total)})
        dyn_legs.append({"leg": n, "items": its, "scenarios": scen})
    dynamic = {"horizon_months": asm.HORIZON_MONTHS,
               "balance_sheet_assumption": {"kind": "constant", "growth_annual": 0, "description": t(
                   "Constant balance sheet: maturing and repricing flows are replaced by identical new ones. The UR leg carries the real rate only "
                   "(balances in CLP million at the UF value); the indexation income is outside it.",
                   "Balance constante: los flujos que vencen o reprecian se reemplazan por otros idénticos. El tramo UR lleva solo la tasa real "
                   "(saldos en millones de CLP al valor de la UF); el ingreso por reajuste queda fuera.")},
               "legs": dyn_legs}
    n_paths = asm.N_PATHS if n_paths is None else n_paths
    ear_legs = []
    for dl in dyn_legs:                     # rung 6: EaR and EVaR of each leg under Hull-White one-factor scenarios
        n = dl["leg"]
        paths = simulation.hw1f_scenarios(r0[n], MID, asm.HW1F_A,
                                          asm.HW1F_SIGMA[n], asm.HORIZON_MONTHS, n_paths, seed)
        arrs = _arrays(dl["items"])
        nii_p = np.array([simulation.simulate_nii(*arrs, q[:asm.HORIZON_MONTHS], 0.0).total for q in paths])
        eve_p = np.array([eve_nii.eve(base[n], shocks.apply_floor(r0[n], np.full(19, (q[-1] - q[0]) * 1e4), floors[n]), MID) for q in paths])
        b_nii, b_eve = dl["scenarios"][0]["total"], base_eve[n]
        levels = []
        for lv in asm.LEVELS:
            got = simulation.ear_evar(nii_p, eve_p, b_nii, b_eve, lv)
            err = simulation.ear_evar_mc_error(nii_p, eve_p, lv, asm.N_BATCHES)
            levels.append({"level": lv, "nii_quantile": float(b_nii - got.ear), "eve_quantile": float(b_eve - got.evar), "ear": float(got.ear),
                           "evar": float(got.evar), "ear_se": float(err.ear_se), "evar_se": float(err.evar_se)})
        ear_legs.append({"leg": n, "method": "hw1f", "n_paths": n_paths, "seed": seed, "horizon_months": asm.HORIZON_MONTHS,
                         "parameters": [{"name": "a", "value": asm.HW1F_A, "unit": "per year"},
                                        {"name": "sigma", "value": asm.HW1F_SIGMA[n], "unit": "per year"}],
                         "base_nii": float(b_nii), "base_eve": float(b_eve), "levels": levels, "mc_error_method": "batch-means",
                         "n_batches": asm.N_BATCHES})
    margin_12m = float(sum(leg["scenarios"][0]["total"] for leg in dyn_legs))

    # ---- the prioritised-bank tests (engine: prioritised_bank)
    pb = eve_nii.prioritised_bank(a2.delta_nii, a1.delta_eve, tier1, margin_12m)
    thresholds = {"tier1": float(tier1), "net_interest_and_indexation_margin_12m": margin_12m,
                  "tests": [{k: _plain(v) for k, v in x.items()} for x in pb.tests], "prioritised": bool(pb.prioritised),
                  "reference": "RAN 21-13 Annex 1 (banco priorizado, dossier 03 F.2)"}

    # ---- the validation tests (engine: riskvalidation.validation.irrbb)
    rows = []
    for tr in (rv_val.srp31_92_goldens(), rv_val.cmf_annex1_goldens()):
        rows.append(_plain(tr.to_dict()))
    for n in ("CLP", "UR"):
        flows = np.array([it.flows * conv[n] for it in items[n]])
        d = _plain(rv_val.eve_sum_of_parts(flows, r0[n], MID, base_eve[n]).to_dict())
        d["segment"] = n
        rows.append(d)
    w = np.array([book.replicating["wholesale"]["weights"]])
    d = _plain(rv_val.nmd_parameter_stability(w, np.array(book.replicating["wholesale"]["maturities"])).to_dict())
    d["segment"] = "wholesale"
    rows.append(d)

    parameters = [{"name": k, "value": float(v), "unit": _unit(k)} for k, v in spec.params.items()]
    outputs = {
        "kind": "annex1-variant",
        "variant": {"id": spec.id, "label": spec.label, "description": spec.description, "parameters": parameters},
        "as_of": vd, "balance_sheet_month": sel.month, "calibration_month": targets.AS_OF[:7], "curves_month": sel.month, "reporting_currency": "CLP", "sign_convention": SIGN, "units": UNITS,
        "bank": bank_block(book.seed, calibration_source),
        "ur_currency": {**UR_BLOCK, "uf_value": float(uf), "uf_value_currency": "CLP", "uf_date": vd, "uf_source": uf_source},
        "curves": {"clp": fits["CLP"].block, "ur": fits["UR"].block},
        "assumptions": book.assumptions_doc(), "nmd_segments": book.segments_doc(),
        "legs": [{"leg": n, "currency": book.legs[n].currency, "items": book.items_doc(n), "assets_total": float(book.legs[n].assets_total),
                  "liabilities_total": float(book.legs[n].liabilities_total), "net_position": float(book.legs[n].net_position)} for n in ("CLP", "UR")],
        "eve_shock_sizes": [_size(sizes["CLP"]), _size(sizes["UR"])],
        "nii_shock_sizes": [{"currency": "CLP", "parallel_bp": int(table["CLP"][0]), "origin": "cmf-annex1"},
                            {"currency": "CLF", "parallel_bp": int(table["UR-nii"][0]), "origin": "cmf-annex1"}],
        "dynamic_nii": dynamic, "ear_evar": ear_legs, "floors": floors_block,
        "offset_rule": {"state": spec.offset_state, "share": 0.5, "applies_to": ["CLP", "CLF"], "rule": OFFSET_RULE,
                        "reference": "RAN 21-13 Annex 1 Hojas 10 to 12 (dossier 03 F.2)"},
        "indexation_charge": indexation, "cpi_scenario": cpi, "eve": eve_block, "nii": nii_block, "thresholds": thresholds}
    values = {f"delta_eve_over_tier1_{vid.replace('-', '_')}": eve_block["delta_eve_share_tier1"],
              f"delta_nii_over_tier1_{vid.replace('-', '_')}": nii_block["delta_nii_share_tier1"]}
    doc = {"outputs": outputs, "tests": rows, "impact": _impact(outputs), "findings": _findings(outputs, thresholds, dist, where, effects)}
    return VariantResult(doc, values, {"book": book.replicating})


def _unit(name: str) -> str:
    from .book import PARAM_UNITS

    return PARAM_UNITS[name]


def _size(z: shocks.ShockSize) -> dict[str, Any]:
    return {"currency": z.currency, "parallel_bp": z.parallel_bp, "short_bp": z.short_bp, "long_bp": z.long_bp, "origin": z.origin,
            "label": z.label, "method": z.method}


def _impact(o: dict[str, Any]) -> dict[str, Any]:
    return {"delta_eve": {"value": float(o["eve"]["delta_eve"]), "unit": UNIT, "label": t("Delta EVE, Annex 1", "Delta EVE, Anexo 1")},
            "delta_nii": {"value": float(o["nii"]["delta_nii"]), "unit": UNIT,
                          "label": t("Delta NII with the indexation charge", "Delta NII con el cargo por reajustabilidad")}}


def _findings(o: dict[str, Any], th: dict[str, Any], dist: float, where: str, effects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by = {x["id"]: x for x in th["tests"]}
    e, n = by["eve-tier1"], by["nii-tier1"]
    sev = "S2" if th["prioritised"] else "S3"
    out = [{"id": "F1", "severity": sev, "status": "open", "evidence": ["design:annex1-prioritised-bank-tests"], "title": t(
        f"Delta EVE is {e['ratio'] * 100:.1f} percent of Tier 1 (threshold 15 percent) and delta NII with the indexation charge is "
        f"{n['ratio'] * 100:.1f} percent (threshold 5 percent); the bank is {'prioritised' if th['prioritised'] else 'not prioritised'} under the Annex 1 tests.",
        f"El delta EVE es {es(e['ratio'] * 100)} por ciento del Tier 1 (umbral 15 por ciento) y el delta NII con el cargo por reajustabilidad es "
        f"{es(n['ratio'] * 100)} por ciento (umbral 5 por ciento); el banco {'es priorizado' if th['prioritised'] else 'no es priorizado'} según los tests del Anexo 1.")}]
    ic, d_nii = o["indexation_charge"]["charge"], o["nii"]["delta_nii"]
    out.append({"id": "F2", "severity": "S3", "status": "open", "evidence": ["design:indexation-charge-is-a-standard-add-on"], "title": t(
        f"The standard indexation charge is {ic / d_nii * 100:.0f} percent of the delta NII: it depends on the size of the net UF position, not on the rate "
        "shock, and no hedge is modelled.",
        f"El cargo estándar por reajustabilidad es {es(ic / d_nii * 100, 0)} por ciento del delta NII: depende del tamaño de la posición neta en UF y no "
        "del choque de tasas, y no se modela ninguna cobertura.")})
    if effects:
        out.append({"id": "F3", "severity": "S3", "status": "open", "evidence": ["irrbb.cmf_annex1_goldens"], "title": t(
            f"The post-shock floors bind in {len(effects)} combinations of shock and leg and change the measures; the smallest distance to a floor elsewhere is "
            f"{dist:.1f} bp.",
            f"Los pisos posteriores al choque actúan en {len(effects)} combinaciones de choque y tramo y modifican las medidas; la menor distancia a un piso "
            f"en el resto es {es(dist)} pb.")})
    else:
        out.append({"id": "F3", "severity": "S4", "status": "open", "evidence": ["irrbb.cmf_annex1_goldens"], "title": t(
            f"No post-shock floor binds on the curves of the valuation date: the smallest distance to a floor is {dist:.1f} bp ({where}); the floors would "
            "matter only at lower rates.",
            f"Ningún piso posterior al choque actúa sobre las curvas de la fecha de valoración: la menor distancia a un piso es {es(dist)} pb ({where}); los "
            "pisos importarían solo con tasas más bajas.")})
    out.append({"id": "F4", "severity": "S3", "status": "open", "evidence": ["design:clp-curve-fourth-point"], "title": t(
        "The pesos curve has three published tenors and the engine's Nelson-Siegel fit needs four: the monetary policy rate is its overnight point, a "
        "policy rate and not a secondary-market yield.",
        "La curva en pesos tiene tres plazos publicados y el ajuste Nelson-Siegel del motor necesita cuatro: la tasa de política monetaria es su punto "
        "a un día, una tasa de política y no un rendimiento de mercado secundario.")})
    return out
