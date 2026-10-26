"""The regulatory measures of the book through ``riskvalidation.regulatory``: SA-CCR (CRE52) with every intermediate, BA-CVA
reduced (MAR50.14 to MAR50.16), the FRTB GIRR delta charge (MAR21) and the effective-EPE measures of CRE53.

Nothing here computes a regulatory number: each is a call, and the product reads its fields into the document. The net
independent collateral amount of the with-IM variant is the initial margin held at the reporting date, by the definition of
CRE52.17 (see ``docs/cases/C12.md``).
"""
from __future__ import annotations

from typing import Any

import numpy as np
from riskvalidation.ccr import hw1f
from riskvalidation.ccr import swaps as sw
from riskvalidation.regulatory import ba_cva, frtb, sa_ccr

from . import book

IN_FORCE = "2023-01-01"
BA_CVA_SECTOR = "financials"
BA_CVA_IG = True
GIRR_BUMP = 1e-4


def money(x: float) -> dict[str, Any]:
    return {"amount": float(x), "currency": book.CURRENCY}


def netting_value(trades: list[book.Trade], tenors: np.ndarray, zeros: np.ndarray) -> float:
    """The value of the netting set at the valuation date on a curve, the engine's ``swap_value`` at t = 0 with the short rate
    at the fitted ``phi(0)``: the repricing identity makes it independent of a and sigma (they are fixed at nominal values)."""
    p0, forward = hw1f.curve_functions(zeros, tenors)
    a, sigma = 0.1, 0.01
    r0 = hw1f.phi(np.array(0.0), a, sigma, forward).reshape(1)
    return float(sum(sw.swap_value(t.swap(), 0.0, r0, a, sigma, p0, forward)[0] for t in trades))


def sa_ccr_block(trades: list[book.Trade], v: float, c: float, margined: bool, th: float, mta: float, nica: float,
                 mpor_business_days: int | None) -> dict[str, Any]:
    """The ``sa_ccr`` block: the trade intermediates and hedging sets of ``ir_addon`` and the netting-set EAD."""
    ir = sa_ccr.ir_addon([sa_ccr.IrTrade(book.CURRENCY, 0.0, t.maturity, t.notional, 1.0 if t.side == "payer" else -1.0)
                          for t in trades], mpor_business_days=mpor_business_days if margined else None)
    res = sa_ccr.netting_set_ead(v, c, sa_ccr.AddOnByClass(interest_rate=ir.addon), margined, th, mta, nica)
    by_id = {t.trade_id: t for t in trades}
    rows = []
    for tr, row in zip(trades, ir.trades, strict=True):
        rows.append({"trade_id": tr.trade_id, "hedging_set": row.hedging_set, "start_years": row.start, "end_years": row.end,
                     "notional": money(row.notional), "supervisory_duration": row.supervisory_duration,
                     "adjusted_notional": money(row.adjusted_notional), "delta": int(row.delta),
                     "maturity_factor": row.maturity_factor, "bucket": row.bucket, "effective_notional": row.effective_notional})
    assert len(rows) == len(by_id)
    return {"paragraph": "CRE52", "in_force_date": IN_FORCE, "margined": bool(margined), "v": money(v), "c": money(c),
            "th": money(th), "mta": money(mta), "nica": money(nica),
            "mpor_business_days": int(mpor_business_days) if margined and mpor_business_days is not None else None,
            "rc": money(res.rc), "trades": rows,
            "hedging_sets": [{"hedging_set": h.hedging_set, "d_b1": h.d_b1, "d_b2": h.d_b2, "d_b3": h.d_b3, "offset": h.offset,
                              "effective_notional": h.effective_notional, "supervisory_factor": h.supervisory_factor,
                              "addon": h.addon} for h in ir.hedging_sets],
            "addon_by_class": {"interest_rate": ir.addon, "fx": 0.0, "credit": 0.0, "equity": 0.0, "commodity": 0.0},
            "addon_aggregate": money(res.addon_aggregate), "multiplier_floor": sa_ccr.MULTIPLIER_FLOOR, "multiplier": res.multiplier,
            "pfe": money(res.pfe), "alpha": res.alpha, "ead": money(res.ead)}


def weighted_average_maturity(trades: list[book.Trade]) -> float:
    return float(sum(t.notional * t.maturity for t in trades) / sum(t.notional for t in trades))


def ba_cva_block(trades: list[book.Trade], ead: float) -> dict[str, Any]:
    """The reduced BA-CVA of the netting set against one investment-grade financial counterparty. M is the notional-weighted
    average maturity of the netting set (UNVERIFIED as the reading of MAR50.15 for a bank without IMM: the paragraph was not
    re-read on the BIS page in this session, stated in the case page)."""
    m = weighted_average_maturity(trades)
    rw = ba_cva.sector_risk_weight(BA_CVA_SECTOR, BA_CVA_IG).value
    df = ba_cva.discount_factor(m, imm_bank=False)
    scva = ba_cva.scva(rw, [(m, ead)], imm_bank=False)
    k = ba_cva.k_reduced([scva])
    return {"paragraph": "MAR50.14 to MAR50.16", "in_force_date": IN_FORCE, "imm_bank": False, "ds": ba_cva.DS, "rho": ba_cva.RHO,
            "alpha": ba_cva.ALPHA,
            "counterparties": [{"counterparty_id": "CPTY-1", "sector": BA_CVA_SECTOR, "rating_class": "investment-grade",
                                "risk_weight": rw, "ead": money(ead), "m_years": m, "discount_factor": df, "scva": scva}],
            "k_reduced": k, "capital": money(ba_cva.capital(k)),
            "limit": {"en": "No official numeric example is verified; the tests rest on the invariants of dossier 01 M.1. M is the "
                            "notional-weighted average maturity of the netting set; the reading of the paragraph has not been checked again.",
                      "es": "No hay ejemplo numérico oficial verificado; las pruebas se apoyan en los invariantes. M es el vencimiento "
                            "medio ponderado por nocional del conjunto; la lectura del párrafo no se ha vuelto a comprobar."}}


def girr_sensitivities(trades: list[book.Trade], tenors: np.ndarray, zeros: np.ndarray, girr_tenors: np.ndarray) -> np.ndarray:
    """s_k = (V(r + 0.0001) - V(r)) / 0.0001 (MAR21.19): the zero curve shifted by 1 bp in a hat around tenor k that falls to
    zero at the neighbouring GIRR tenors (flat beyond the first and the last), the netting set revalued by the engine."""
    nodes = np.unique(np.concatenate([tenors, girr_tenors]))
    base = np.interp(nodes, tenors, zeros)
    v0 = netting_value(trades, nodes, base)
    out = np.empty(girr_tenors.size)
    for k in range(girr_tenors.size):
        unit = np.zeros(girr_tenors.size)
        unit[k] = 1.0
        hat = np.interp(nodes, girr_tenors, unit)
        out[k] = (netting_value(trades, nodes, base + GIRR_BUMP * hat) - v0) / GIRR_BUMP
    return out


def girr_block(trades: list[book.Trade], tenors: np.ndarray, zeros: np.ndarray) -> dict[str, Any]:
    """The GIRR delta charge of the netting set: the engine's ``girr_delta_charge`` with the weights divided by sqrt(2) (MAR21.44,
    the headline, a named convention) and the undivided charge beside it."""
    div, und = frtb.girr_parameters(True), frtb.girr_parameters(False)
    s = girr_sensitivities(trades, tenors, zeros, div.tenors)
    a, b = frtb.girr_delta_charge(s, div.tenors, div), frtb.girr_delta_charge(s, und.tenors, und)
    return {"paragraph": "MAR21.42 to MAR21.50", "in_force_date": IN_FORCE, "currency": book.CURRENCY, "sqrt2_division": True,
            "sqrt2_label": "convention", "sensitivities": [float(x) for x in s], "weighted_sensitivities": [float(x) for x in a.weighted],
            "scenarios": [{"scenario": name, "k_b": float(k)} for name, k in zip(("low", "medium", "high"), a.k_by_scenario, strict=True)],
            "delta_charge": money(a.charge), "delta_charge_undivided": money(b.charge)}
