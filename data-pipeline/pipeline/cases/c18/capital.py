"""The capital engine of the IAPE on a static balance sheet (EBA 2025 rules), through ``riskvalidation.stress.capital``.

The headline CET1 path is the **loss-only depletion**: CET1 at the jump-off less the cumulative stressed losses, no invented revenue
(decision Q10); a labelled row adds PPNR (the C15 twelve-month net interest margin held constant, plus a stated fee ratio and cost ratio,
both case assumptions). The internal capital target OI, the Chilean legal minimum, the capital plan of the three cases, the P2G proxy
(a Contraste approximation) and the 34 rows of the Annex 3 summary are the engine's. The 4 percent cap binds the art. 66 quinquies
requirement ``p2r``, never the bank's own estimate ``c_p2`` (decision W3). No mitigation action is assumed: the sources name none and the
EBA static balance sheet forbids capital measures after the reference date (para 33), so row 10.2 is N/A.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.stress import capital as rv_cap
from riskvalidation.validation import stress as rv_vs

from . import params as P
from .anchors import Anchors

T = P.text


@dataclass(frozen=True)
class Target:
    rv: rv_cap.InternalTarget
    legal_minimum: float
    block: dict[str, Any]


def internal_target(named: dict[str, dict[str, Any]], anchors: Anchors) -> Target:
    st = anchors.stack
    t = rv_cap.internal_capital_target(st["c_dsib"], named["c_p2"]["value"], st["c_ccob"], st["c_ccyb"], named["c_d"]["value"], st["p2r"])
    legal = t.min_pe + t.c_dsib + st["p2r"]
    block = {"formula": "OI >= 8% + c_DSIB + c_P2 + c_CCoB + c_CCyB + c_d, as percent of RWA (RAN 21-13 section I; 03 l.152-169)", "horizon_years": 3,
             "min_pe": t.min_pe, "c_dsib": t.c_dsib, "c_p2": named["c_p2"], "c_ccob": t.c_ccob, "c_ccyb": t.c_ccyb, "c_d": named["c_d"], "oi": t.oi}
    return Target(t, legal, block)


def capital_start(anchors: Anchors) -> dict[str, Any]:
    return {"rwa_clp_m": anchors.rwa_clp_m, "rwa_by_risk": anchors.rwa_by_risk, "cet1_clp_m": anchors.cet1_clp_m, "at1_clp_m": anchors.at1_clp_m,
            "t2_clp_m": anchors.t2_clp_m, "pe_clp_m": anchors.cet1_clp_m + anchors.at1_clp_m + anchors.t2_clp_m,
            "cet1_ratio": anchors.cet1_clp_m / anchors.rwa_clp_m,
            "pe_ratio": (anchors.cet1_clp_m + anchors.at1_clp_m + anchors.t2_clp_m) / anchors.rwa_clp_m,
            "basis": T("RWA is the C15 Tier 1 proxy over the 11.0 percent CET1 anchor, split by the mix of the Banco Santander-Chile Form 20-F 2025 (ratios only, "
                       "derived-only); CET1 is the proxy. The PE ratio is the 20-F effective equity over its RWA (a ratio). UNVERIFIED assumption: no source splits the part "
                       "above CET1 between AT1 and T2, so it is carried as T2 and AT1 is nil; no CET1 figure depends on it, and it makes Tier 1 equal to CET1, the conservative "
                       "Tier 1 (decisions Q4 and Z12).",
                       "El APR es el proxy de Tier 1 de C15 sobre el ancla de CET1 de 11,0 por ciento, repartido según la mezcla del Formulario 20-F 2025 de Banco Santander-Chile "
                       "(solo razones, solo derivado); el CET1 es el proxy. La razón de PE es el patrimonio efectivo del 20-F sobre sus APR (una razón). Supuesto NO VERIFICADO "
                       "(UNVERIFIED): ninguna fuente reparte la parte sobre el CET1 entre AT1 y T2, por lo que se lleva como T2 y el AT1 es nulo; ninguna cifra de CET1 depende de "
                       "ello y deja el Tier 1 igual al CET1, el Tier 1 conservador (decisiones Q4 y Z12).")}


def cap_row(available: float, rwa: float, need: float | None = None) -> dict[str, Any]:
    return {"pct_of_rwa": available / rwa, "need_clp_m": need, "available_clp_m": available}


def plan_cases(plan: dict[str, tuple[rv_cap.PlanYear, ...]], oi: float, legal: float) -> list[dict[str, Any]]:
    cases = []
    ends = P.year_ends()
    for case in rv_cap.PLAN_CASES:
        years = []
        for y in plan[case]:
            need = y.requirement_pct * y.rwa
            years.append({"year": y.year, "period_end": ends[y.year - 1], "rwa_clp_m": y.rwa, "cet1": cap_row(y.cet1, y.rwa), "at1": cap_row(y.at1, y.rwa),
                          "t2": cap_row(y.t2, y.rwa), "pe": cap_row(y.pe, y.rwa, need),
                          "requirement": {"basis": "internal-target" if case == "base" else "legal-minimum", "pct_of_rwa": y.requirement_pct},
                          "headroom_pct_of_rwa": y.headroom_pct, "deficit_clp_m": y.deficit})
        cases.append({"case": case, "years": years})
    return cases


def ppnr_block(path: np.ndarray, nii: list[float], named: dict[str, dict[str, Any]], rwa: float, statement: dict[str, str]) -> tuple[dict[str, Any], list[float]]:
    rows, cum, ppnrs = [], 0.0, []
    for y, ends in enumerate(P.year_ends()):
        r = rv_cap.ppnr_row(nii[y], named["ppnr_fee_ratio"]["value"], named["ppnr_cost_ratio"]["value"])
        cum += r.ppnr
        ppnrs.append(r.ppnr)
        with_ = float(path[y]) + cum
        rows.append({"year": y + 1, "period_end": ends, "nii_clp_m": r.nii, "fee_income_clp_m": r.fee_income, "operating_cost_clp_m": r.operating_cost,
                     "ppnr_clp_m": r.ppnr, "cet1_with_ppnr_clp_m": with_, "cet1_ratio_with_ppnr": with_ / rwa})
    block = {"label": "ppnr-labelled-row", "statement": statement, "nii_source": "c15-dynamic-nii", "fee_ratio": named["ppnr_fee_ratio"],
             "cost_ratio": named["ppnr_cost_ratio"], "rows": rows}
    return block, ppnrs


def headline_rows(cet1_0: float, losses: list[float], rwa: float) -> tuple[list[dict[str, Any]], np.ndarray]:
    path = rv_cap.cet1_path_loss_only(cet1_0, losses)
    rows, prev, cum = [], cet1_0, 0.0
    for y, ends in enumerate(P.year_ends()):
        cum += losses[y]
        rows.append({"year": y + 1, "period_end": ends, "cet1_start_clp_m": prev, "cumulative_loss_clp_m": cum, "cet1_clp_m": float(path[y]),
                     "rwa_clp_m": rwa, "cet1_ratio": float(path[y]) / rwa})
        prev = float(path[y])
    return rows, path


def mitigation_block() -> dict[str, Any]:
    return {"applies": False,
            "reason": T("No mitigation action is assumed: the sources name none and the EBA static balance sheet rules forbid capital measures taken after the "
                        "reference date (para 33), so the stress with mitigation equals the stress without it and row 10.2 of the Annex 3 is N/A.",
                        "No se supone ninguna acción de mitigación: las fuentes no nombran ninguna y las reglas de balance estático de la EBA prohíben las medidas de capital "
                        "tomadas después de la fecha de referencia (párrafo 33), por lo que la tensión con mitigación es igual a la tensión sin ella y la fila 10.2 del Anexo 3 "
                        "es N/A."),
            "actions": []}


def p2g_block(cet1_ratio_0: float, severe_ratios: list[float], target: Target) -> dict[str, Any]:
    usable = target.rv.c_ccob + target.rv.c_ccyb + target.rv.c_d
    value = rv_cap.p2g_proxy(cet1_ratio_0, severe_ratios, usable)
    dep = [cet1_ratio_0 - r for r in severe_ratios]
    peak = max(dep)
    return {"label": "contraste-approximation",
            "formula": "max over t of [(CET1/RWA)_0 - (CET1/RWA)_t severe] less the usable buffers and mitigation, floored at zero (03 l.1001-1005, FAQ 24)",
            "peak_depletion": peak, "peak_year": dep.index(peak) + 1, "usable_buffers_and_mitigation": usable, "value": value,
            "statement": T("A Contraste approximation consistent with FAQ 24: the CMF calibration grid is not public and this is not a P2G requirement. The usable "
                           "buffers are the conservation and countercyclical buffers and the voluntary stress buffer c_d; no mitigation is assumed."),
            "cmf_calibration_public": False}


def annex3(anchors: Anchors, target: Target, plan: dict[str, tuple[rv_cap.PlanYear, ...]], ec: dict[str, float]) -> dict[str, Any]:
    rows = rv_cap.annex3_summary(
        {"cet1": anchors.cet1_clp_m, "at1": anchors.at1_clp_m, "t2": anchors.t2_clp_m}, target.rv, anchors.rwa_by_risk,
        {"credit": ec["credit"], "concentration_individual": None, "concentration_sectoral": None, "concentration_other": None, "irrbb": ec["irrbb"],
         "strategic": None, "reputational": None, "other": None}, plan, False)
    return {"entity": "Banco Andino", "report_date": P.AS_OF, "consolidation": "local", "money_unit": "CLP millions", "rows": list(rows)}


def static_balance_test(stage_balances: np.ndarray, flows: np.ndarray) -> Any:
    balances = rv_cap.eba_static_balance_sheet(stage_balances, flows)
    # the engine's tolerance is absolute (money): 1e-9 of the book, which is the floating-point scale of a total of millions
    return rv_vs.static_balance_sheet_rules(balances, tolerance=1e-9 * float(np.sum(stage_balances)), model_id="c18-capital-engine")
