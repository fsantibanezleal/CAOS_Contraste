"""The c07-models and c07-outputs documents of C07 from the book and the engine results.

Every regime number is read from a ``b1``, ``ifrs9`` or ``bde`` result (the engine's); this module orders, sums rounded
amounts and labels them. Money is CLP, rounded to the centavo before it is summed so that every identity of the contract
holds to the unit on the written values (the totals are the sums of the written parts).
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np
from riskvalidation.provisions import ecl as ecl_mod
from riskvalidation.provisions import local_cl as cl
from riskvalidation.provisions import local_es as es

from ...core import text as tx
from . import b1, bde, ifrs9
from . import book as bk
from . import scenarios as sc
from . import sources as src
from .book import PARAMS, SEGMENTS, SEG_IDS, Book

CURRENCY = src.CURRENCY
GENERATOR = PARAMS["generator_version"]


def T(en: str, es_: str) -> dict[str, str]:
    return {"en": en, "es": es_}


def m(x: float) -> float:
    return round(float(x), 2)


NOTICE = T(
    "Synthetic data: Banco Andino is a generated bank calibrated to public CMF system aggregates, not a real bank and not "
    "evidence about any bank. CMF B-1 is the statutory provision Chilean banks book on loans; the IFRS 9 column is a comparison "
    "measure, not the provision Chilean banks book on loans (CNCB A-2 N 5 leaves loans to B-1); BdE Annex 9 is the Spanish GAAP "
    "alternative solution. Amounts in CLP.",
    "Datos sintéticos: Banco Andino es un banco generado, calibrado a agregados públicos del sistema de la CMF; no es un banco real "
    "ni evidencia sobre ningún banco. CMF B-1 es la provisión estatutaria que los bancos chilenos constituyen sobre colocaciones; la "
    "columna IFRS 9 es una medida de comparación, no la provisión que los bancos chilenos constituyen sobre colocaciones (CNCB A-2 N 5 "
    "deja las colocaciones a B-1); el Anejo 9 del BdE es la solución alternativa del PGC español. Montos en CLP.")

REGIME_LABEL = {
    "cmf-b1": T("CMF B-1 (statutory, Chile)", "CMF B-1 (estatutaria, Chile)"),
    "ifrs9": T("IFRS 9 (probability-weighted ECL, comparison)", "IFRS 9 (ECL ponderada por probabilidad, comparación)"),
    "bde-annex9": T("BdE Annex 9 (Spain)", "BdE Anejo 9 (España)"),
}
STAGE_LABEL = {"stage1": T("Stage 1", "Etapa 1"), "stage2": T("Stage 2", "Etapa 2"), "stage3": T("Stage 3", "Etapa 3")}
BDE_LABEL = {"normal": T("Normal", "Normal"), "normal-special-watch": T("Normal, special watch", "Normal en vigilancia especial"),
             "doubtful": T("Doubtful (arrears)", "Dudoso (morosidad)")}

#: money keys written to the centavo, never compacted to nine digits
EXACT = frozenset({
    "provision", "total_provision", "amount", "gross_exposure", "exposure", "ecl", "gross_carrying_amount",
    "single_scenario_ecl", "standard", "internal", "applied", "normal_portfolio_exposure",
    "normal_portfolio_provision_before_minimum", "minimum_amount", "top_up", "booked_total", "cmf_b1_provision",
    "ifrs9_provision", "bde_annex9_provision", "gap_ifrs9_minus_b1", "gap_bde_minus_b1", "cmf_b1_delta", "ifrs9_delta",
    "bde_annex9_delta", "policy_min", "policy_max", "overlays_total", "normal_substandard_provision", "default_provision",
    "value"})


def rv_version() -> str:
    from importlib.metadata import version

    return version("riskvalidation")


# --- evaluation ----------------------------------------------------------------------------------------------------------


def evaluate(book: Book, scenario: dict[str, Any]) -> dict[str, Any]:
    state = bk.state_at(book, scenario)
    res_b1 = b1.provisions(book, state)
    return {"scenario": scenario, "state": state, "b1": res_b1, "mc": b1.minimum_check(book, state, res_b1),
            "bde": bde.coverage(book, state), "ifrs": ifrs9.run(book, state)}


def segment_sum(book: Book, values: np.ndarray, seg_id: str) -> float:
    return float(values[book.seg == SEG_IDS.index(seg_id)].sum())


# --- the three-regime variant --------------------------------------------------------------------------------------------


def additional_provisions(book: Book) -> dict[str, Any]:
    total = float(book.e.sum())
    amount = cl.b1_additional_provisions(m(0.0005 * total), 0.0, m(0.0025 * total))
    return {"amount": m(amount), "rationale": T(
        "Counter-cyclical general provisions under board policy (B-1 N 9): 0.05 per cent of gross exposure inside a policy range of "
        "0 to 0.25 per cent; assumption of the case. Their own line, outside the comparable total and never used to cover model "
        "deficiencies.",
        "Provisiones generales contracíclicas según política del directorio (B-1 N 9): 0,05 % de la exposición bruta dentro de un "
        "rango de política de 0 a 0,25 %; supuesto del caso. Línea propia, fuera del total comparable y nunca para cubrir deficiencias "
        "del modelo."), "policy_min": 0.0, "policy_max": m(0.0025 * total)}


def _b1_categories(book: Book, ev: dict[str, Any]) -> list[dict[str, Any]]:
    st, res = ev["state"], ev["b1"]
    out: list[dict[str, Any]] = []
    group = np.isin(book.seg, [bk.SEG_IDS.index(i) for i in SEG_IDS if i != "commercial-individual"])
    buckets = np.array([bk.dpd_bucket(int(d)) for d in st.dpd], dtype=object)
    for bucket, label in (("0", T("Group, current", "Grupal, al día")), ("1-29", T("Group, 1 to 29 days", "Grupal, 1 a 29 días")),
                          ("30-59", T("Group, 30 to 59 days", "Grupal, 30 a 59 días")),
                          ("60-89", T("Group, 60 to 89 days", "Grupal, 60 a 89 días")), ("default", T("Group, default", "Grupal, incumplimiento"))):
        mk = group & (buckets == bucket)
        out.append({"category_id": f"group-{bucket}", "label": label, "exposure": m(book.e[mk].sum()), "provision": m(res.provision[mk].sum())})
    ind = book.seg == b1.INDIVIDUAL_ID
    for k, lab in enumerate(b1.CAT_LABELS):
        mk = ind & ~st.default & (st.cat == k)
        out.append({"category_id": lab, "label": T(f"Individual {lab}", f"Individual {lab}"), "exposure": m(book.e[mk].sum()),
                    "provision": m(res.provision[mk].sum())})
    for lab in ("C1", "C2", "C3", "C4", "C5", "C6"):
        mk = ind & st.default & (res.category == lab)
        out.append({"category_id": lab, "label": T(f"Individual {lab}", f"Individual {lab}"), "exposure": m(book.e[mk].sum()),
                    "provision": m(res.provision[mk].sum())})
    return out


def variant_outputs(book: Book, ev: dict[str, Any], base_ev: dict[str, Any], overlays: tuple, rollup: dict[str, Any]) -> dict[str, Any]:
    scen = ev["scenario"]
    res_b1, mc, bd, ifr = ev["b1"], ev["mc"], ev["bde"], ev["ifrs"]
    gross = {s: m(segment_sum(book, book.e, s)) for s in SEG_IDS}
    total_gross = m(sum(gross.values()))
    # --- B-1
    group_ids = [s for s in SEG_IDS if s != "commercial-individual"]
    max_rule, b1_seg = [], {}
    for s in group_ids:
        standard = m(segment_sum(book, res_b1.provision, s))
        applied, method = cl.b1_group_max_rule(standard, None)
        max_rule.append({"segment_id": s, "standard": standard, "internal": None, "applied": m(applied), "method": method,
                         "internal_reason": T("Banco Andino has no internal method: the standard method applies (B-1 N 3); the CMF "
                                             "August 2026 report states that no institution uses internal methods for provisions",
                                             "Banco Andino no tiene método interno: se aplica el método estándar (B-1 N 3); el informe de la CMF "
                                             "de agosto de 2026 indica que ninguna institución usa métodos internos para las provisiones")})
        b1_seg[s] = m(applied)
    b1_seg["commercial-individual"] = m(segment_sum(book, res_b1.provision, "commercial-individual"))
    top_up = m(mc.top_up)
    b1_total = m(sum(b1_seg.values()) + top_up)
    add = additional_provisions(book)
    b1_regime = {
        "regime": "cmf-b1", "label": REGIME_LABEL["cmf-b1"], "currency": CURRENCY, "total_provision": b1_total,
        "coverage_rate": b1_total / total_gross,
        "by_segment": [{"segment_id": s, "provision": b1_seg[s], "coverage_rate": b1_seg[s] / gross[s]} for s in SEG_IDS],
        "by_category": _b1_categories(book, ev), "status": "statutory-chile-loans",
        "unallocated_lines": [{"id": "minimum-top-up", "kind": "minimum-top-up", "amount": top_up, "label": T(
            "Top-up to the 0.50% minimum on the individually assessed normal portfolio",
            "Complemento al mínimo de 0,50 % de la cartera normal de evaluación individual")}]}
    # --- IFRS 9
    ecl_acc = ifrs9.account_ecl(ifr)
    f_seg = {s: m(segment_sum(book, ecl_acc, s)) for s in SEG_IDS}
    allowance = ifrs9.allowance(ifr, overlays)
    comps = []
    for k, w in enumerate(sc.WEIGHTING):
        comps.append({"scenario_id": w["id"], "weight": w["weight"], "z": float(ifr.z[k]),
                      "single_scenario_ecl": m(ifrs9.allowance(ifr, k=k).model_total)})
    gca = ifrs9.stage_gca(ifr, book)
    stage_summary = []
    for s in ("stage1", "stage2", "stage3"):
        n, g = gca[s]
        e_s = m(allowance.by_stage[s])
        stage_summary.append({"stage": s, "accounts": n, "gross_carrying_amount": m(g), "ecl": e_s, "coverage": (e_s / g) if g else 0.0})
    stage_summary.append({"stage": "poci", "accounts": 0, "gross_carrying_amount": 0.0, "ecl": 0.0, "coverage": 0.0})
    ov_lines = [{"id": f"overlay-{o.id}", "kind": "overlay", "amount": m(o.amount), "label": T(o.rationale_en, o.rationale_es)} for o in overlays]
    ov_total = m(sum(x["amount"] for x in ov_lines))
    ifrs_total = m(sum(f_seg.values()) + ov_total)
    ifrs_regime = {
        "regime": "ifrs9", "label": REGIME_LABEL["ifrs9"], "currency": CURRENCY, "total_provision": ifrs_total,
        "coverage_rate": ifrs_total / total_gross,
        "by_segment": [{"segment_id": s, "provision": f_seg[s], "coverage_rate": f_seg[s] / gross[s]} for s in SEG_IDS],
        "by_category": [{"category_id": r["stage"], "label": STAGE_LABEL[r["stage"]], "exposure": r["gross_carrying_amount"],
                         "provision": r["ecl"]} for r in stage_summary if r["stage"] != "poci"],
        "status": "comparison-measure", "unallocated_lines": ov_lines}
    # --- Annex 9
    bde_seg = {s: m(segment_sum(book, bd.provision, s)) for s in SEG_IDS}
    bde_total = m(sum(bde_seg.values()))
    cats = []
    for c in ("normal", "normal-special-watch", "doubtful"):
        mk = bd.category == c
        exp, pr = m(book.e[mk].sum()), m(bd.provision[mk].sum())
        cats.append({"category": c, "mapped_stage": es.annex9_category_to_stage(c), "exposure": exp, "provision": pr,
                     "coverage_rate": pr / exp if exp else 0.0})
    bde_regime = {
        "regime": "bde-annex9", "label": REGIME_LABEL["bde-annex9"], "currency": CURRENCY, "total_provision": bde_total,
        "coverage_rate": bde_total / total_gross,
        "by_segment": [{"segment_id": s, "provision": bde_seg[s], "coverage_rate": bde_seg[s] / gross[s]} for s in SEG_IDS],
        "by_category": [{"category_id": c["category"], "label": BDE_LABEL[c["category"]], "exposure": c["exposure"],
                         "provision": c["provision"]} for c in cats],
        "status": "spanish-gaap-alternative-solutions", "unallocated_lines": []}
    # --- comparison and bridge
    rows = []
    for s in SEG_IDS:
        rows.append({"segment_id": s, "cmf_b1_provision": b1_seg[s], "ifrs9_provision": f_seg[s], "bde_annex9_provision": bde_seg[s],
                     "gap_ifrs9_minus_b1": m(f_seg[s] - b1_seg[s]), "gap_bde_minus_b1": m(bde_seg[s] - b1_seg[s])})
    comparison = {"currency": CURRENCY, "rows": rows, "unallocated": {
        "cmf_b1_provision": top_up, "ifrs9_provision": ov_total, "bde_annex9_provision": 0.0,
        "gap_ifrs9_minus_b1": m(ov_total - top_up), "gap_bde_minus_b1": m(0.0 - top_up)}}
    bridge = _bridge(ifr, ifrs_total, b1_total, top_up, ov_total, b1_seg)
    delta = None
    if scen["id"] != "base":
        bt = base_ev["_totals"]
        delta = {"currency": CURRENCY, "cmf_b1_delta": m(b1_total - bt["cmf-b1"]), "ifrs9_delta": m(ifrs_total - bt["ifrs9"]),
                 "bde_annex9_delta": m(bde_total - bt["bde-annex9"])}
    normal_exp = m(book.e[res_b1.normal_mask].sum())
    normal_prov = m(res_b1.provision[res_b1.normal_mask].sum())
    ev["_totals"] = {"cmf-b1": b1_total, "ifrs9": ifrs_total, "bde-annex9": bde_total}
    return {
        "kind": "three-regime", "scenario_id": scen["id"], "currency": CURRENCY, "synthetic": True, "notice": NOTICE,
        "scenario": {"description": scen["description"], "shocks": [{"driver": d, "unit": u, "value": v} for d, u, v in scen["shocks"]]},
        "portfolio": {"currency": CURRENCY, "segments": [
            {"segment_id": s["id"], "label": s["label"], "accounts": int((book.seg == i).sum()), "gross_exposure": gross[s["id"]]}
            for i, s in enumerate(SEGMENTS)]},
        "regimes": [b1_regime, ifrs_regime, bde_regime], "comparison": comparison, "gap_bridge": bridge,
        "b1_detail": {"currency": CURRENCY, "minimum_check": {
            "minimum_rate": mc.minimum_rate, "normal_portfolio_exposure": normal_exp,
            "normal_portfolio_provision_before_minimum": normal_prov, "minimum_amount": m(mc.minimum_amount),
            "binding": bool(mc.binding), "top_up": top_up},
            "group_max_rule": max_rule, "additional_provisions": add,
            "individual": {"normal_substandard_provision": m(res_b1.individual_normal_substandard),
                           "default_provision": m(res_b1.individual_default)},
            "booked_total": m(b1_total + add["amount"])},
        "ifrs9_detail": {"currency": CURRENCY, "stage_summary": stage_summary, "overlays_total": ov_total,
                         "measure": "probability-weighted-ecl", "weighted_components": comps, "overlays": [
                             {"id": o.id, "label": T(o.rationale_en, o.rationale_es), "segment_id": o.segment_id, "stage": o.stage,
                              "amount": m(o.amount)} for o in overlays]},
        "bde_detail": {"currency": CURRENCY, "categories": cats, "method": "alternative-solutions"},
        "delta_vs_base": delta}


def _bridge(ifr: ifrs9.Ifrs9Result, ifrs_total: float, b1_total: float, top_up: float, ov_total: float,
            b1_seg: dict[str, float]) -> dict[str, Any]:
    """Exhaustive steps from the B-1 comparable total to the IFRS 9 total. Each intermediate measure is the engine's
    ``portfolio_allowance`` on the same accounts and stages; the steps are differences of that ladder:
    B-1 model provisions, the IFRS 9 12-month ECL of every non-defaulted account at the central scenario undiscounted (the
    measurement basis: statutory matrices against the bank's PD, LGD and recoveries), the staged ECL (Stage 2 at lifetime), the
    probability-weighted staged ECL (the non-linearity of the scenarios), the discounted one (the model ECL), then the minimum
    top-up (in B-1 only) and the overlays (in IFRS 9 only)."""
    c = int(np.argmin(np.abs(np.array([s["z_offset"] for s in sc.WEIGHTING]))))
    stage_a = np.where(ifr.stage == 3, 3, 1)
    a = ecl_mod.portfolio_allowance(stage_a, ifr.e12_u[c], ifr.life_u[c], ifr.s3_u).model_total
    b = ecl_mod.portfolio_allowance(ifr.stage, ifr.e12_u[c], ifr.life_u[c], ifr.s3_u).model_total
    w = ecl_mod.probability_weighted_ecl
    cc = ecl_mod.portfolio_allowance(ifr.stage, w(ifr.e12_u, ifr.weights), w(ifr.life_u, ifr.weights), ifr.s3_u).model_total
    d = ecl_mod.portfolio_allowance(ifr.stage, w(ifr.e12, ifr.weights), w(ifr.life, ifr.weights), ifr.s3).model_total
    b1_model = sum(b1_seg.values())
    steps = {
        "lifetime-horizon": m(b - a), "forward-looking": m(cc - b), "discounting": m(d - cc),
        "b1-minimum-top-up": m(-top_up) + 0.0, "ifrs9-overlays": m(ov_total)}
    gap = m(ifrs_total - b1_total)
    steps_measure = m(gap - sum(steps.values()))      # the first step closes the bridge to the centavo
    if abs(steps_measure - (a - b1_model)) > 1.0:
        raise ValueError(f"the bridge is not exhaustive: measurement step {steps_measure:,.2f} against {a - b1_model:,.2f}")
    label = {
        "measurement-basis": T("Measurement basis: bank PD, LGD and recoveries against the B-1 matrices (12-month, central, undiscounted)",
                               "Base de medición: PD, LGD y recuperaciones del banco frente a las matrices B-1 (12 meses, central, sin descuento)"),
        "lifetime-horizon": T("Lifetime loss on Stage 2 accounts", "Pérdida a vida sobre cuentas de Etapa 2"),
        "forward-looking": T("Probability weighting of the scenarios", "Ponderación de escenarios por probabilidad"),
        "discounting": T("Discounting at the original EIR", "Descuento a la TIE original"),
        "b1-minimum-top-up": T("B-1 minimum top-up, not in IFRS 9", "Complemento del mínimo B-1, fuera de IFRS 9"),
        "ifrs9-overlays": T("IFRS 9 overlays", "Ajustes posmodelo IFRS 9")}
    ordered = [("measurement-basis", steps_measure)] + [(k, steps[k]) for k in (
        "lifetime-horizon", "forward-looking", "discounting", "b1-minimum-top-up", "ifrs9-overlays")]
    return {"currency": CURRENCY, "from_regime": "cmf-b1", "to_regime": "ifrs9",
            "steps": [{"id": k, "label": label[k], "amount": v} for k, v in ordered]}


# --- tests, findings, impact, models -----------------------------------------------------------------------------------


def findings(out: dict[str, Any], rows: list[dict[str, Any]], model_ids: dict[str, str]) -> list[dict[str, Any]]:
    reg = {r["regime"]: r for r in out["regimes"]}
    b1t, f9, bd = reg["cmf-b1"]["total_provision"], reg["ifrs9"]["total_provision"], reg["bde-annex9"]["total_provision"]
    ratio = f9 / b1t
    sev = "S2" if abs(ratio - 1.0) > 0.25 else "S3"
    mid = model_ids["ifrs9"]
    byt = {(r["test_id"]): r for r in rows if r["segment"] is None}
    f: list[dict[str, Any]] = [{
        "id": "F-GAP", "severity": sev, "status": "open", "evidence": [f"ifrs9.scenario_sensitivity@{mid}"],
        "title": T(f"On one portfolio the IFRS 9 total is {ratio:.0%} of the CMF B-1 total (gap {(f9 - b1t) / 1e9:,.1f} CLP bn) and "
                   f"BdE Annex 9 is {bd / b1t:.0%}",
                   f"Sobre una misma cartera el total IFRS 9 es {tx.percent(ratio, 0, lang='es')} del total CMF B-1 "
                   f"(brecha {tx.number((f9 - b1t) / 1e9, 1, lang='es')} mil millones CLP) "
                   f"y el Anejo 9 del BdE es {tx.percent(bd / b1t, 0, lang='es')}")}]
    nl = byt["ifrs9.scenario_sensitivity"]
    f.append({"id": "F-NONLINEARITY", "severity": "S3" if nl["light"] == "green" else "S2", "status": "open",
              "evidence": [f"ifrs9.scenario_sensitivity@{mid}"],
              "title": T(f"The weighted ECL exceeds the ECL at the mean scenario path by {nl['metric']:.1%}",
                         f"La ECL ponderada supera a la ECL en la trayectoria media de escenarios en {tx.percent(nl['metric'], 1, lang='es')}")})
    ov = byt["ifrs9.overlay_diagnostics"]
    f.append({"id": "F-OVERLAY", "severity": "S4" if ov["light"] == "green" else "S3", "status": "accepted" if ov["light"] == "green" else "open",
              "evidence": [f"ifrs9.overlay_diagnostics@{mid}"],
              "title": T(f"Overlays are {ov['metric']:.2%} of the IFRS 9 allowance, each a separate line",
                         f"Los ajustes posmodelo son {tx.percent(ov['metric'], 2, lang='es')} de la provisión IFRS 9, cada uno en una línea separada")})
    mc = out["b1_detail"]["minimum_check"]
    f.append({"id": "F-MINIMUM", "severity": "S4", "status": "accepted", "evidence": ["design:b1-minimum-normal-individual"],
              "title": T("The 0.50% minimum on the individually assessed normal portfolio is "
                         + ("binding" if mc["binding"] else "not binding") + f" (top-up {mc['top_up'] / 1e6:,.1f} CLP million)",
                         "El mínimo de 0,50 % de la cartera normal de evaluación individual "
                         + ("es vinculante" if mc["binding"] else "no es vinculante") + f" (complemento {tx.number(mc['top_up'] / 1e6, 1, lang='es')} millones CLP)")})
    bt = byt["ifrs9.ecl_backtest"]
    if bt["light"] in ("amber", "red"):
        f.append({"id": "F-ECL-BACKTEST", "severity": "S3" if bt["light"] == "amber" else "S2", "status": "open",
                  "evidence": [f"ifrs9.ecl_backtest@{mid}"],
                  "title": T(f"The 12-month ECL against the generator's own realised losses: ratio {bt['metric']:.2f} ({bt['light']})",
                             f"La ECL a 12 meses frente a las pérdidas realizadas del propio generador: razón {tx.number(bt['metric'], 2, lang='es')} ({tx.light(bt['light'], 'es')})")})
    sc_ = byt["ifrs9.sicr_effectiveness"]
    if sc_["light"] in ("amber", "red"):
        f.append({"id": "F-SICR", "severity": "S3" if sc_["light"] == "amber" else "S2", "status": "open",
                  "evidence": [f"ifrs9.sicr_effectiveness@{mid}"],
                  "title": T(f"Stage 2 defaults {sc_['metric']:.1f} times as often as Stage 1 in the generator's realised outcomes, but "
                             f"{sc_['extras']['share_stage3_direct_from_stage1']:.0%} of Stage 3 entries come directly from Stage 1 ({sc_['light']})",
                             f"La Etapa 2 incumple {tx.number(sc_['metric'], 1, lang='es')} veces más que la Etapa 1 en los resultados realizados del generador, pero "
                             f"el {tx.percent(sc_['extras']['share_stage3_direct_from_stage1'], 0, lang='es')} de las entradas a Etapa 3 viene directo de la Etapa 1 "
                             f"({tx.light(sc_['light'], 'es')})")})
    return f


def impact(out: dict[str, Any]) -> dict[str, Any]:
    reg = {r["regime"]: r for r in out["regimes"]}
    b1t, f9, bd = (reg[k]["total_provision"] for k in ("cmf-b1", "ifrs9", "bde-annex9"))
    unit = CURRENCY
    return {
        "provision_cmf_b1": {"value": b1t, "unit": unit, "label": T("CMF B-1 comparable total", "Total comparable CMF B-1")},
        "provision_ifrs9": {"value": f9, "unit": unit, "label": T("IFRS 9 probability-weighted ECL plus overlays",
                                                                  "IFRS 9 ECL ponderada por probabilidad más ajustes")},
        "provision_bde": {"value": bd, "unit": unit, "label": T("BdE Annex 9", "BdE Anejo 9")},
        "gap_ifrs9_minus_b1": {"value": m(f9 - b1t), "unit": unit, "label": T("IFRS 9 minus CMF B-1", "IFRS 9 menos CMF B-1")},
        "ifrs9_over_b1": {"value": f9 / b1t, "unit": "ratio", "label": T("IFRS 9 over CMF B-1", "IFRS 9 sobre CMF B-1")},
        "b1_booked_total": {"value": out["b1_detail"]["booked_total"], "unit": unit,
                            "label": T("B-1 booked total with additional provisions", "Total B-1 constituido con provisiones adicionales")}}


def model_summaries(out: dict[str, Any], rv: str, scen: dict[str, Any]) -> list[dict[str, Any]]:
    P = {"unit": "CLP"}
    mc = out["b1_detail"]["minimum_check"]
    reg = {r["regime"]: r for r in out["regimes"]}
    return [
        {"id": "B1-standard", "family": "statutory-provision", "rung": "cmf-b1", "title": T("CMF CNCB B-1 standard methods", "Métodos estándar CMF CNCB B-1"),
         "short_title": T("CMF B-1", "CMF B-1"), "engine": "riskvalidation.provisions.local_cl", "engine_version": rv, "licence": "MIT",
         "calibration": None, "checkpoint_sha256": None,
         "parameters": {"minimum_rate": {"value": mc["minimum_rate"], "unit": "share"},
                        "additional_provisions": {"value": out["b1_detail"]["additional_provisions"]["amount"], **P},
                        "total_provision": {"value": reg["cmf-b1"]["total_provision"], **P}}},
        {"id": "IFRS9-ecl", "family": "ecl", "rung": ifrs9.PD_LADDER_RUNG, "title": T("IFRS 9 probability-weighted ECL", "ECL IFRS 9 ponderada por probabilidad"),
         "short_title": T("IFRS 9", "IFRS 9"), "engine": "riskvalidation.provisions.ecl", "engine_version": rv, "licence": "MIT",
         "calibration": None, "checkpoint_sha256": None,
         "parameters": {"z_shift": {"value": scen["z_shift"], "unit": "standard deviations"},
                        "overlays_total": {"value": out["ifrs9_detail"]["overlays_total"], **P},
                        "total_provision": {"value": reg["ifrs9"]["total_provision"], **P}}},
        {"id": "BDE-annex9", "family": "statutory-provision", "rung": "bde-annex9", "title": T("BdE Circular 4/2017 Annex 9 alternative solutions", "Soluciones alternativas del Anejo 9 de la Circular 4/2017 del BdE"),
         "short_title": T("BdE Annex 9", "BdE Anejo 9"), "engine": "riskvalidation.provisions.local_es", "engine_version": rv, "licence": "MIT",
         "calibration": None, "checkpoint_sha256": None,
         "parameters": {"collateral_haircut": {"value": PARAMS["haircut"], "unit": "share"},
                        "total_provision": {"value": reg["bde-annex9"]["total_provision"], **P}}}]


# --- the models document ------------------------------------------------------------------------------------------------


def parameter_hash() -> str:
    blob = json.dumps({"params": PARAMS, "targets": src.TARGETS, "weighting": sc.WEIGHTING, "policy": ifrs9.STAGING_POLICY,
                       "scenarios": [(s["id"], s["z_shift"], s["hpi"], s["channels"], s["shocks"]) for s in sc.SCENARIOS]},
                      sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def b1_tables() -> list[dict[str, Any]]:
    """Every B-1 table the case uses, cell by cell, read through the engine (decimals; PE = PI x PDI to the table rounding)."""
    mort = []
    for row, pvg in (("pvg<=40", 0.30), ("40<pvg<=80", 0.60), ("80<pvg<=90", 0.85), ("pvg>90", 0.95)):
        for col in ("0", "1-29", "30-59", "60-89", "default"):
            pi, pdi, pe = cl.b1_mortgage_pe(pvg, col)
            mort.append({"row": row, "column": col, "pi": pi, "pdi": pdi, "pe": pe})
    cons = []
    for row, dpd in (("0-7", 3), ("8-30", 20), ("31-60", 45), ("61-89", 70)):
        for col, (mt, ar) in (("mortgage-no-arrears", (True, False)), ("mortgage-arrears", (True, True)),
                              ("no-mortgage-no-arrears", (False, False)), ("no-mortgage-arrears", (False, True))):
            pi = cl.b1_consumer_pe(dpd, mt, ar, "instalment")[0]
            cons.append({"row": row, "column": col, "pi": pi, "pdi": None, "pe": None})
    ind = []
    for lab in b1.CAT_LABELS:
        pi, pdi, pe = cl.b1_individual_category(lab)
        ind.append({"row": lab, "column": "category", "pi": pi, "pdi": pdi, "pe": pe})
    com = []
    for row in ("0", "1-29", "30-59", "60-89", "default"):
        for col, ptvg in (("no-guarantee", None), ("ptvg<=60", 0.5), ("60<ptvg<=75", 0.7), ("75<ptvg<=90", 0.85), ("ptvg>90", 0.95)):
            pi, pdi, pe = cl.b1_commercial_pe(row, ptvg)
            com.append({"row": row, "column": col, "pi": pi, "pdi": pdi, "pe": pe})
    def src_(section: str, extra_en: str = "", extra_es: str = "", d: str = "D.5") -> dict[str, str]:
        return T(f"CMF CNCB Chapter B-1 (Circular 2.346), dossier 03 section {d}; read through riskvalidation.provisions.local_cl ({section}){extra_en}",
                 f"CMF CNCB Capítulo B-1 (Circular 2.346), dossier 03 sección {d}; leído con riskvalidation.provisions.local_cl ({section}){extra_es}")

    return [
        {"table_id": "mortgage-pe", "portfolio": "residential-mortgage", "source": src_("3.1.1"), "cells": mort},
        {"table_id": "consumer-pi", "portfolio": "consumer",
         "source": src_("3.1.3", "; the PDI by product is in the B-1 model record", "; la PDI por producto está en el registro del modelo B-1"), "cells": cons},
        {"table_id": "individual-categories", "portfolio": "commercial-individual", "source": src_("2.1", d="D.3"), "cells": ind},
        {"table_id": "commercial-generic-pe", "portfolio": "commercial-group", "source": src_("3.1.2 c"), "cells": com}]


def default_categories() -> list[dict[str, Any]]:
    return [{"category": c, "tpe_upper": u, "provision_rate": p} for c, u, p in cl._DEFAULT_BUCKETS]


def bde_block() -> dict[str, Any]:
    labels = [">90d-6m", "6-9m", "9-12m", "12-15m", "15-18m", "18-21m", ">21m"]
    reps = [120, 200, 300, 400, 500, 600, 700]
    codes = sorted({s["bde"] for s in SEGMENTS})
    return {"normal_coverage": [{"segment": c, "normal": es.annex9_normal_coverage(c, "normal"),
                                 "special_watch": es.annex9_normal_coverage(c, "normal-special-watch")} for c in codes],
            "doubtful_bucket_labels": labels, "doubtful_bucket_upper_days": [183, 274, 365, 457, 548, 639, None],
            "doubtful_coverage": [{"segment": c, "by_bucket": [es.annex9_doubtful_coverage(c, d) for d in reps]} for c in codes]}


def achieved_targets(book: Book, base_ev: dict[str, Any]) -> list[dict[str, Any]]:
    """Each target with the value the base state of the book reaches (B-1 comparable provisions: group applied plus
    individual plus the minimum top-up)."""
    prov = base_ev["b1"].provision
    classes = {k: book.klass == i for i, k in enumerate(bk.CLASSES)}
    tot = float(book.e.sum())
    dpd = base_ev["state"].dpd
    top_up = float(base_ev["mc"].top_up)
    ach: dict[str, float] = {}
    for k, mk in classes.items():
        ach[f"loan mix: {k}"] = float(book.e[mk].sum()) / tot
        extra = top_up if k == "commercial" else 0.0
        ach[f"provision index: {k}"] = (float(prov[mk].sum()) + extra) / float(book.e[mk].sum())
        ach[f"90-day delinquency: {k}"] = float(book.e[mk & (dpd >= 90)].sum()) / float(book.e[mk].sum())
    ach["provision index: total"] = (float(prov.sum()) + top_up) / tot
    ach["90-day delinquency: total"] = float(book.e[dpd >= 90].sum()) / tot
    cons = classes["consumer"]
    ach["consumer product split: instalment loans"] = float(book.e[book.seg == SEG_IDS.index("consumer-instalment")].sum()) / float(book.e[cons].sum())
    return [{"metric": t["metric"], "unit": t["unit"], "target": t["value"], "achieved": ach[t["metric"]],
             "source": src.source_text(t), "as_of": t["as_of"]} for t in src.TARGETS]


def models_document(book: Book, base_ev: dict[str, Any], overlays: tuple, rv: str) -> dict[str, Any]:
    ifr = base_ev["ifrs"]
    seg_rows, ifrs_seg = [], []
    for i, s in enumerate(SEGMENTS):
        mk = book.seg == i
        seg_rows.append({"id": s["id"], "label": s["label"], "accounts": int(mk.sum()), "gross_exposure": m(book.e[mk].sum()),
                         "b1_portfolio": s["b1"], "bde_segment": s["bde"], "bde_segment_label": s["bde_label"]})
        w = book.e[mk]
        ifrs_seg.append({"segment_id": s["id"], "pd_ttc": float(np.clip(np.average(book.pd_now[mk], weights=w), 1e-4, 0.9)),
                         "rho": s["rho"], "lgd": float(np.clip(np.average(ifr.lgd[mk], weights=w), 0.0, 1.0))})
    notice = T(
        "Synthetic: Banco Andino is a generated bank, calibrated to public CMF system aggregates (parameters and hash in the generator "
        "model record); its rows are not observations of any bank. UF-indexed mortgages are converted to CLP at the SII value of "
        f"{src.UF_DATE}: {src.UF_VALUE:,.2f} CLP per UF.",
        "Sintético: Banco Andino es un banco generado, calibrado a agregados públicos del sistema de la CMF (parámetros y hash en el "
        "registro del modelo generador); sus filas no son observaciones de ningún banco. Las hipotecas indexadas a UF se convierten a CLP "
        f"al valor del SII del {src.UF_DATE}: {tx.number(src.UF_VALUE, 2, lang='es')} CLP por UF.")
    fit = {
        "currency": CURRENCY,
        "bank": {"name": "Banco Andino", "synthetic": True, "notice": notice, "seed": int(book.seed),
                 "calibration_source": f"CMF Informe del Desempeno del Sistema Bancario y Cooperativas, {src.AS_OF[:7]} "
                                       f"({src.PUBLICATIONS['cmf-informe-2026-08']['url']}), public web publication (the CMF Bancos API key is "
                                       f"absent); generator {GENERATOR}; parameters sha256 {parameter_hash()}"},
        "calibration_targets": achieved_targets(book, base_ev), "segments": seg_rows, "b1_tables": b1_tables(),
        "b1_default_categories": default_categories(),
        "ifrs9": {"pd_ladder_rung": ifrs9.PD_LADDER_RUNG, "discount_convention": ifrs9.CONVENTION, "segments": ifrs_seg,
                  "weighting_scenarios": [{"id": w["id"], "label": w["label"], "weight": w["weight"], "z_offset": w["z_offset"]}
                                          for w in sc.WEIGHTING],
                  "eir_basis": "original", "staging_policy": ifrs9.STAGING_POLICY},
        "bde": bde_block(),
        "scenarios": [{"id": s["id"], "label": s["label"], "z_shift": s["z_shift"],
                       "shocks": [{"driver": d, "unit": u, "value": v} for d, u, v in s["shocks"]]} for s in sc.SCENARIOS]}
    details_gen = {"generator_version": GENERATOR, "parameters": PARAMS, "parameters_sha256": parameter_hash(), "tier_share": book.meta.get("tier_share"),
                   "portfolio_sha256": book.digest(), "scale": book.scale, "uf": {"value": src.UF_VALUE, "date": src.UF_DATE,
                   "source": src.PUBLICATIONS["sii-uf-2026"]["url"], "sha256": src.PUBLICATIONS["sii-uf-2026"]["sha256"]},
                   "publications": src.PUBLICATIONS, "tolerance": {"target": src.TOLERANCE, "total": src.TOLERANCE_TOTAL},
                   "assumptions": ASSUMPTIONS}
    models = [
        {"id": "G0-banco-andino", "family": "synthetic-generator", "rung": "calibrated", "title": T("Banco Andino synthetic generator", "Generador sintético de Banco Andino"),
         "short_title": T("Generator", "Generador"), "engine": "none", "engine_version": GENERATOR, "licence": "MIT", "calibration": None,
         "checkpoint_sha256": None, "parameters": {"seed": {"value": int(book.seed), "unit": "seed"},
                                                   "accounts": {"value": int(book.n), "unit": "accounts"},
                                                   "total_exposure": {"value": m(book.e.sum()), "unit": "CLP"}}, "details": details_gen},
        {"id": "B1-standard", "family": "statutory-provision", "rung": "cmf-b1", "title": T("CMF CNCB B-1 standard methods", "Métodos estándar CMF CNCB B-1"),
         "short_title": T("CMF B-1", "CMF B-1"), "engine": "riskvalidation.provisions.local_cl", "engine_version": rv, "licence": "MIT",
         "calibration": None, "checkpoint_sha256": None, "parameters": {"minimum_rate": {"value": 0.005, "unit": "share"}},
         "details": {"consumer_pdi": {"with-mortgage": {"leasing-auto": cl.b1_consumer_pe(3, True, False, "leasing-auto")[1],
                                                        "instalment": cl.b1_consumer_pe(3, True, False, "instalment")[1],
                                                        "cards-lines-other": cl.b1_consumer_pe(3, True, False, "cards-lines-other")[1]},
                                      "no-mortgage": {"leasing-auto": cl.b1_consumer_pe(3, False, False, "leasing-auto")[1],
                                                      "instalment": cl.b1_consumer_pe(3, False, False, "instalment")[1],
                                                      "cards-lines-other": cl.b1_consumer_pe(3, False, False, "cards-lines-other")[1]}},
                     "individual_assessment_haircut": PARAMS["haircut"], "overlays_in_b1": False}},
        {"id": "IFRS9-ecl", "family": "ecl", "rung": ifrs9.PD_LADDER_RUNG, "title": T("IFRS 9 probability-weighted ECL", "ECL IFRS 9 ponderada por probabilidad"),
         "short_title": T("IFRS 9", "IFRS 9"), "engine": "riskvalidation.provisions.ecl", "engine_version": rv, "licence": "MIT", "calibration": None,
         "checkpoint_sha256": None, "parameters": {"half_life_quarters": {"value": ifrs9.HALF_LIFE_QUARTERS, "unit": "quarters"}},
         "details": {"overlays": [{"id": o.id, "segment_id": o.segment_id, "stage": o.stage, "amount": m(o.amount), "method": o.method,
                                   "rationale": T(o.rationale_en, o.rationale_es), "review_date": o.review_date} for o in overlays],
                     "weighting_basis": sc.WEIGHTING_BASIS}},
        {"id": "BDE-annex9", "family": "statutory-provision", "rung": "bde-annex9", "title": T("BdE Circular 4/2017 Annex 9 alternative solutions", "Soluciones alternativas del Anejo 9 de la Circular 4/2017 del BdE"),
         "short_title": T("BdE Annex 9", "BdE Anejo 9"), "engine": "riskvalidation.provisions.local_es", "engine_version": rv, "licence": "MIT",
         "calibration": None, "checkpoint_sha256": None, "parameters": {"collateral_haircut": {"value": PARAMS["haircut"], "unit": "share"}},
         "details": {"limitation": "Circular 4/2017 point numbers as of Circular 6/2021; whether they shifted after Circular 1/2025 is UNVERIFIED; "
                                   "the collateral haircut table is not transcribed, so the case applies a stated haircut"}}]
    return {"fit_id": "banco-andino", "model": models, "fit": fit}


ASSUMPTIONS = {
    "total_exposure": "assumption of the case: Banco Andino holds 6.0 trillion CLP of loans (about 1.3 per cent of the system)",
    "commercial_split": "assumption of the case, UNVERIFIED on a CMF primary source: 60 per cent of the commercial book is assessed "
                        "individually, 40 per cent in groups",
    "arrears_ratio": "assumption of the case: exposure 1 to 89 days past due is 1.2 times the 90-day ratio",
    "flow_factor": "assumption of the case: the annual default rate is half the 90-day stock ratio",
    "tiers": "assumption of the case: one high-risk tier per portfolio (LTV above 80 per cent, arrears in the system, no guarantee, "
             "categories A5 to B4), its share solved so that the B-1 provision index equals the CMF index",
    "eir": "assumption of the case, order of magnitude only: mortgages 8%, consumer instalment 20%, cards 30%, commercial group 12%, "
           "individual 8%",
    "asset_correlation": "assumption of the case in the ranges of Basel CRE31: mortgages 0.15, consumer instalment 0.10, cards 0.04, "
                         "commercial group 0.12, individual 0.20",
    "recoveries": "assumption of the case: recovered share = 80 per cent of the collateral appraisal plus a case-specific extra; "
                  "cash flows at 12 and 24 months, discounted at the EIR",
    "weighting": "dossier 02 B.4: factors +1, 0 and -2 with weights 25, 50 and 25 per cent",
}
