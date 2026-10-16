"""Builds the seven U10-S fixture documents (docs/contracts/fixtures/c14 and c15).

Run: ``python tests/contracts_u10/build_fixtures.py``. Deterministic, standard library only. The numbers are round and small
on purpose and are fixtures, never results: every document is labelled ``fixture`` in its provenance and its ids. They are
internally consistent: every EVE, delta EVE, delta NII, pair and charge is computed here from the formulas of dossier 01 H and
dossier 03 F.2 (the test file recomputes them independently).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from build_schemas import CCY21, GAMMA, MIDPOINTS, SHOCKS, T2016, T2024, UMULT

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "docs" / "contracts" / "fixtures"

BUCKET_LABELS = ["Overnight", "O/N to 1M", "1M to 3M", "3M to 6M", "6M to 9M", "9M to 1Y", "1Y to 1.5Y", "1.5Y to 2Y", "2Y to 3Y",
                 "3Y to 4Y", "4Y to 5Y", "5Y to 6Y", "6Y to 7Y", "7Y to 8Y", "8Y to 9Y", "9Y to 10Y", "10Y to 15Y", "15Y to 20Y",
                 "Over 20Y"]
BUCKET_LABELS_ES = ["A la vista", "Hasta 1M", "1M a 3M", "3M a 6M", "6M a 9M", "9M a 1A", "1A a 1,5A", "1,5A a 2A", "2A a 3A",
                    "3A a 4A", "4A a 5A", "5A a 6A", "6A a 7A", "7A a 8A", "8A a 9A", "9A a 10A", "10A a 15A", "15A a 20A",
                    "Mas de 20A"]


def r(x: float, d: int = 6) -> float:
    return round(x, d)


def txt(en: str, es: str) -> dict:
    return {"en": en, "es": es}


def shape(shock: str, par: float, short: float, long: float) -> list[float]:
    s = [short * math.exp(-t / 4) for t in MIDPOINTS]
    lg = [long * (1 - math.exp(-t / 4)) for t in MIDPOINTS]
    return {
        "parallel-up": [par] * 19, "parallel-down": [-par] * 19, "short-up": s, "short-down": [-x for x in s],
        "steepener": [-0.65 * abs(a) + 0.9 * abs(b) for a, b in zip(s, lg)],
        "flattener": [0.8 * abs(a) - 0.6 * abs(b) for a, b in zip(s, lg)],
    }[shock]


def post(r0: float, d_bp: float, floor: float | None) -> float:
    x = r0 + d_bp / 1e4
    return x if floor is None else max(x, min(floor, r0))


def eve_of(cf: list[float], rates: list[float]) -> float:
    return sum(c * math.exp(-x * t) for c, x, t in zip(cf, rates, MIDPOINTS))


def interp(points: list[tuple[float, float]], t: float) -> float:
    if t <= points[0][0]:
        return points[0][1]
    for (a, ya), (b, yb) in zip(points, points[1:]):
        if t <= b:
            return ya + (yb - ya) * (t - a) / (b - a)
    return points[-1][1]


def fl(bucket: int, amount: float) -> dict:
    return {"bucket": bucket, "midpoint_years": MIDPOINTS[bucket - 1], "amount": r(amount)}


def dense(flows: list[dict]) -> list[float]:
    v = [0.0] * 19
    for f in flows:
        v[f["bucket"] - 1] += f["amount"]
    return v


def two_point(amount: float, target: float) -> list[tuple[int, float]]:
    """Slots an amount in the two buckets around ``target`` years so its weighted average maturity is ``target``."""
    for i in range(18):
        lo, hi = MIDPOINTS[i], MIDPOINTS[i + 1]
        if lo <= target <= hi:
            w = (hi - target) / (hi - lo)
            return [(i + 1, amount * w), (i + 2, amount * (1 - w))]
    raise ValueError(target)


def reset_rate(it: dict, path: list[float], m: int) -> float:
    """Rate of an item in the projected month m (0-based): the engine contract's simulate_nii."""
    k = it["reprice_months"]
    if k == 0:
        return it["spread"] + it["beta"] * path[m]
    if m < k:
        return it["rate0"]
    return it["spread"] + it["beta"] * path[(m // k) * k]


def simulate_nii(items: list[dict], path: list[float], growth: float = 0.0) -> list[float]:
    return [sum((1 if it["side"] == "asset" else -1) * it["balance"] * (1 + growth) ** (m / 12) * reset_rate(it, path, m) / 12
                for it in items) for m in range(len(path))]


def dyn_block(items: list[dict], r_short: float, par_bp: float, floor: float, horizon: int) -> list[dict]:
    """The three scenarios of a dynamic NII block: base (flat short rate), parallel-up and parallel-down."""
    out, base_total = [], None
    for name, bp in (("base", 0.0), ("parallel-up", par_bp), ("parallel-down", -par_bp)):
        x = post(r_short, bp, floor)
        path = [r(x, 9)] * horizon
        monthly = simulate_nii(items, path)
        total = sum(monthly)
        base_total = total if base_total is None else base_total
        out.append({"scenario": name, "shock_bp": bp, "short_rate_path": path, "monthly_nii": [r(v) for v in monthly],
                    "total": r(total), "delta_vs_base": r(base_total - total)})
    return out


def fixture_envelope(truth: str = "synthetic-calibrated") -> dict:
    return {
        "provenance": {
            "truth_status": truth,
            "inputs": [{"source": "fixture-not-a-result", "class": "fixture", "files": []}],
            "licence_classes": {"fixture-not-a-result": "fixture"},
            "generators": ["fixture:u10-s-contracts"],
            "seed": 0, "code_version": "fixture", "riskvalidation_version": None,
        },
        "lane": {"lane": "precompute", "reasons": ["fixture"]},
    }


def test_row(test_id: str, model_id: str) -> dict:
    return {
        "test_id": test_id, "model_id": model_id, "segment": None, "statistic": None, "p_value": None, "metric": None,
        "h0": "fixture row", "alternative": "fixture row", "policy_version": "fixture", "alpha_amber": None,
        "alpha_red": None, "light": "not_evaluated", "n": None, "n_events": None, "inputs_hash": "0" * 64,
        "reference": "fixture, not a result", "notes": "fixture: the test did not run, no number stands in for it", "extras": {},
    }


def model_summary(mid: str, rung: str) -> dict:
    return {
        "id": mid, "family": "irrbb", "rung": rung, "title": txt(f"Fixture model {mid}", f"Modelo de ejemplo {mid}"),
        "short_title": txt(mid, mid), "engine": "riskvalidation", "engine_version": "fixture", "licence": "MIT",
        "calibration": None, "parameters": {}, "checkpoint_sha256": None,
    }


def model_record(mid: str, rung: str) -> dict:
    d = model_summary(mid, rung)
    d["details"] = {}
    return d


def sign_convention() -> dict:
    return {
        "delta_eve": "positive-is-loss", "delta_nii": "positive-is-loss", "reference": "SRP31.129; dossier 01 H.4",
        "statement": txt("A positive delta EVE or delta NII is a loss; only losses are aggregated across currencies.",
                         "Un delta EVE o delta NII positivo es una perdida; solo las perdidas se agregan entre monedas."),
    }


def units(scale: str) -> dict:
    return {"money_scale": scale, "rate": "decimal", "compounding": "continuous", "shock": "basis-points",
            "bucket_midpoint": "years", "dates": "ISO-8601"}


def buckets() -> list[dict]:
    return [{"bucket": i + 1, "label": txt(BUCKET_LABELS[i], BUCKET_LABELS_ES[i]), "midpoint_years": MIDPOINTS[i]} for i in range(19)]


def assumption(value: float, unit: str, kind: str, source: str) -> dict:
    return {"value": r(value, 9), "unit": unit, "source_kind": kind, "source": source}


def nmd_flows(amount: float, core_share: float, core_maturity: float, behavioural: bool) -> list[dict]:
    """Liability NMD flows (negative): contractual, all overnight; behavioural, the non-core share overnight and the core share
    in two buckets whose weighted average maturity is the core maturity."""
    if not behavioural:
        return [fl(1, -amount)]
    out = [fl(1, -amount * (1 - core_share))]
    for b, a in two_point(amount * core_share, core_maturity):
        out.append(fl(b, -a))
    return out


def merge_flows(flows: list[dict]) -> list[dict]:
    acc: dict[int, float] = {}
    for f in flows:
        acc[f["bucket"]] = acc.get(f["bucket"], 0.0) + f["amount"]
    return [fl(b, a) for b, a in sorted(acc.items()) if abs(a) > 1e-9]


def write(rel: str, doc: dict) -> None:
    path = FIX / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def shock_size(currency: str, table: dict, origin: str) -> dict:
    i = CCY21.index(currency)
    return {"currency": currency, "parallel_bp": table["parallel"][i], "short_bp": table["short"][i], "long_bp": table["long"][i],
            "origin": origin, "label": None, "method": None}


# ------------------------------------------------------------------------------------------------------- C14

C14_SPECS = {
    "2021-Q4": dict(
        date="2021-12-31", reports=["2021-09-30", "2021-12-31"], scale=0.85, floor=0.0, missing_tenors=[1 / 3],
        par=[(1 / 12, 0.0005), (0.25, 0.0006), (0.5, 0.0019), (1, 0.0039), (2, 0.0073), (3, 0.0096), (5, 0.0126), (7, 0.0144),
             (10, 0.0152), (20, 0.0194), (30, 0.0190)],
        seg=dict(wholesale=(0.40, 3.0, "synthetic-stated"), rt=(0.90, 5.0, "regulatory-cap"), rnt=(0.65, 4.0, "fitted")),
        cpr=0.04, tdrr=0.05, beta=0.30),
    "2022-Q4": dict(
        date="2022-12-31", reports=["2022-09-30", "2022-12-31"], scale=1.0, floor=0.0, missing_tenors=[1 / 3],
        par=[(1 / 12, 0.0415), (0.25, 0.0434), (0.5, 0.0476), (1, 0.0473), (2, 0.0441), (3, 0.0422), (5, 0.0399), (7, 0.0394),
             (10, 0.0388), (20, 0.0414), (30, 0.0397)],
        seg=dict(wholesale=(0.40, 3.0, "synthetic-stated"), rt=(0.90, 5.0, "regulatory-cap"), rnt=(0.75, 4.0, "fitted")),
        cpr=0.04, tdrr=0.05, beta=0.45),
}
SEG_CAT = {"wholesale": "wholesale", "rt": "retail-transactional", "rnt": "retail-non-transactional"}
SEG_CAP = {"wholesale": (0.5, 4.0), "rt": (0.9, 5.0), "rnt": (0.7, 4.5)}
SEG_CLASS = {"wholesale": "nmd-wholesale", "rt": "nmd-retail-transactional", "rnt": "nmd-retail-non-transactional"}
TENORS_C14 = [p for p in C14_SPECS["2022-Q4"]["par"]]


def c14_outputs(quarter: str) -> tuple[dict, dict]:
    sp = C14_SPECS[quarter]
    s = sp["scale"]
    r0 = [r(interp(sp["par"], t), 9) for t in MIDPOINTS]
    seg_balance = {"wholesale": 110e6 * s, "rt": 25e6 * s, "rnt": 20e6 * s}
    segments, used = [], {}
    for k in ("wholesale", "rt", "rnt"):
        share, mat, kind = sp["seg"][k]
        cs, cm = SEG_CAP[k]
        used[k] = (min(share, cs), min(mat, cm))
        segments.append({
            "category": SEG_CAT[k], "balance": r(seg_balance[k]), "requested_core_share": share, "core_share_cap": cs,
            "core_share_used": used[k][0], "requested_core_maturity_years": mat, "core_maturity_cap_years": cm,
            "core_maturity_used_years": used[k][1], "cap_applied": share > cs or mat > cm, "source_kind": kind,
            "source": {"regulatory-cap": "SRP31 Table 4 cap taken as the assumption",
                       "fitted": "fixture value standing for a fitted replicating portfolio",
                       "synthetic-stated": "fixture value, synthetic behaviour stated"}[kind],
        })
    items: list[dict] = []

    def add(item_id, en, es, side, category, bclass, rtype, fld, amount, flows, reported=True, reason=None, slotting="reported-repricing-profile"):
        cf = merge_flows(flows)
        items.append({
            "item_id": item_id, "label": txt(en, es), "side": side, "category": category, "behavioural_class": bclass,
            "repricing_type": rtype, "source_field": f"fixture:{fld}",
            "reported_amount": r(amount) if reported else None, "reason_missing": reason,
            "slotting_assumption": slotting, "amount": r(amount), "cash_flows": {"behavioural": cf, "contractual": cf},
        })

    add("A1", "Cash and balances", "Efectivo y saldos", "asset", "cash", "none", "floating", "cash-and-balances", 8e6 * s, [fl(1, 8e6 * s)])
    add("A2", "Securities held to maturity", "Valores mantenidos al vencimiento", "asset", "securities-htm", "none", "fixed",
        "securities-htm", 90e6 * s, [fl(9, 20e6 * s), fl(13, 30e6 * s), fl(16, 25e6 * s), fl(17, 15e6 * s)])
    add("A3", "Securities available for sale", "Valores disponibles para la venta", "asset", "securities-afs", "none", "fixed",
        "securities-afs", 25e6 * s, [fl(8, 10e6 * s), fl(11, 15e6 * s)])
    add("A4", "Floating-rate loans", "Prestamos a tasa variable", "asset", "loans-floating", "none", "floating", "loans-floating",
        35e6 * s, [fl(3, 20e6 * s), fl(5, 15e6 * s)])
    add("A5", "Fixed-rate loans", "Prestamos a tasa fija", "asset", "loans-fixed", "none", "fixed", "loans-fixed", 20e6 * s,
        [fl(7, 6e6 * s), fl(9, 8e6 * s), fl(12, 6e6 * s)])
    nmd_defs = [("L1", "wholesale", "Corporate operating deposits", "Depositos operativos de empresas", "deposits-transactional", True),
                ("L2", "rt", "Retail transactional deposits", "Depositos minoristas transaccionales", "deposits-transactional", True),
                ("L3", "rnt", "Retail non-transactional deposits", "Depositos minoristas no transaccionales",
                 "deposits-non-transactional", False)]
    for iid, k, en, es, cat, rep in nmd_defs:
        share, mat = used[k]
        cf_b = nmd_flows(seg_balance[k], share, mat, True)
        cf_c = nmd_flows(seg_balance[k], share, mat, False)
        add(iid, en, es, "liability", cat, SEG_CLASS[k], "non-maturity", f"deposits-{k}", seg_balance[k], cf_b, reported=rep,
            reason=None if rep else txt("The FDIC financials do not split non-transaction deposits between retail and wholesale.",
                                        "Los estados financieros de la FDIC no separan los depositos sin transaccion entre minoristas y mayoristas."),
            slotting="reported-repricing-profile" if rep else "split-of-total-non-transaction-deposits-assumed")
        items[-1]["cash_flows"] = {"behavioural": merge_flows(cf_b), "contractual": merge_flows(cf_c)}
    add("L4", "Time deposits", "Depositos a plazo", "liability", "deposits-time", "term-deposit", "fixed", "deposits-time",
        12e6 * s, [fl(4, -12e6 * s)])
    add("L5", "Borrowings", "Obligaciones", "liability", "borrowings", "none", "fixed", "borrowings", 10e6 * s,
        [fl(6, -4e6 * s), fl(12, -6e6 * s)])
    td_amount = 12e6 * s
    total_nmd = sum(seg_balance.values())
    wavg_share = sum(seg_balance[k] * used[k][0] for k in seg_balance) / total_nmd
    wavg_mat = sum(seg_balance[k] * used[k][1] for k in seg_balance) / total_nmd
    assumptions = {
        "nmd_core_share": assumption(wavg_share, "share", "fitted", "balance-weighted average of the used values of nmd_segments"),
        "nmd_core_maturity_years": assumption(wavg_mat, "years", "fitted", "balance-weighted average of the used values of nmd_segments"),
        "prepayment_cpr": assumption(sp["cpr"], "per year", "synthetic-stated",
                                     "fixture value; no item of this fixture carries the prepayable-loan class"),
        "term_deposit_redemption_rate": assumption(sp["tdrr"], "share of the term deposit", "synthetic-stated", "fixture value"),
        "deposit_beta": assumption(sp["beta"], "pass-through", "fitted", "fixture value standing for the models document fit"),
    }
    base = {n: [0.0] * 19 for n in ("behavioural", "contractual")}
    for it in items:
        for n in base:
            for b, v in enumerate(dense(it["cash_flows"][n])):
                base[n][b] += v
    td_bucket = 4
    kao_by_shock = {"parallel-down": 2500.0, "short-down": 1200.0}
    scenarios, measures = [], {}
    for cal, table, origin in (("2024", T2024, "srp31-table-2024"), ("2016", T2016, "srp31-table-2016")):
        size = shock_size("USD", table, origin)
        for n in ("behavioural", "contractual"):
            b0 = base[n]
            base_eve = eve_of(b0, r0)
            shocks = []
            for idx, shock in enumerate(SHOCKS):
                sh = shape(shock, size["parallel_bp"], size["short_bp"], size["long_bp"])
                flows = list(b0)
                moved = td_amount * min(1.0, UMULT[idx] * sp["tdrr"])
                flows[0] -= moved
                flows[td_bucket - 1] += moved
                rates = [post(a, d, sp["floor"]) for a, d in zip(r0, sh)]
                bound = [k + 1 for k in range(19) if r0[k] + sh[k] / 1e4 < min(sp["floor"], r0[k])]
                eve = eve_of(flows, rates)
                kao = kao_by_shock.get(shock, 0.0)
                delta = base_eve - eve + kao
                row = {"shock": shock, "shape_bp": [r(x, 9) for x in sh], "floor_bound_buckets": bound,
                       "net_cash_flows": [r(x) for x in flows], "eve": r(eve), "kao": r(kao), "delta_eve": r(delta),
                       "delta_eve_share_tier1": 0.0, "delta_nii": None, "delta_nii_reason": None, "_raw": delta}
                if shock in ("parallel-up", "parallel-down"):
                    row["delta_nii"] = r(sum(b0[k] * (r0[k] - rates[k]) * (1 - MIDPOINTS[k]) for k in range(6)))
                else:
                    row["delta_nii_reason"] = txt("Delta NII is reported for the two parallel shocks only (SRP31.90).",
                                                  "El delta NII se informa solo para los dos choques paralelos (SRP31.90).")
                shocks.append(row)
            measure = max([0.0] + [x["_raw"] for x in shocks])
            measures[(cal, n)] = measure
            scenarios.append({"calibration": cal, "nmd_assumption": n,
                              "nmd_treatment": "standardised-capped" if n == "behavioural" else "contractual-overnight",
                              "shock_size": size, "floor": sp["floor"],
                              "base_eve": r(base_eve), "shocks": shocks, "eve_risk_measure": r(measure),
                              "worst_shock": max(shocks, key=lambda x: x["_raw"])["shock"] if measure > 0 else None,
                              "outlier": None})
    m_beh, m_con = measures[("2024", "behavioural")], measures[("2024", "contractual")]
    assert 0 < m_beh < m_con, (quarter, m_beh, m_con)
    tier1 = round(((m_beh + m_con) / 2) / 0.15, -3)
    for sc in scenarios:
        for x in sc["shocks"]:
            x["delta_eve_share_tier1"] = r(x["_raw"] / tier1, 12)
            del x["_raw"]
        measure = sc["eve_risk_measure"]
        ratio = measure / tier1
        sc["outlier"] = {"threshold_share_tier1": 0.15, "tier1": r(tier1), "eve_risk_measure": measure, "ratio": r(ratio, 9),
                         "breached": ratio > 0.15, "reference": "SRP31.82 to SRP31.83 (15 percent of Tier 1)"}
    assert any(sc["outlier"]["breached"] for sc in scenarios) and not all(sc["outlier"]["breached"] for sc in scenarios)
    by = {(sc["calibration"], sc["nmd_assumption"]): {x["shock"]: x["delta_eve"] for x in sc["shocks"]} for sc in scenarios}
    comparison = [{"calibration": cal, "shock": sh, "delta_eve_behavioural": by[(cal, "behavioural")][sh],
                   "delta_eve_contractual": by[(cal, "contractual")][sh],
                   "difference": r(by[(cal, "behavioural")][sh] - by[(cal, "contractual")][sh])}
                  for cal in ("2024", "2016") for sh in SHOCKS]
    ladder = []
    for n in ("behavioural", "contractual"):
        assets, liabs = [0.0] * 19, [0.0] * 19
        for it in items:
            for b, v in enumerate(dense(it["cash_flows"][n])):
                if it["side"] == "asset":
                    assets[b] += v
                else:
                    liabs[b] += -v
        pv_a = sum(assets[k] * math.exp(-r0[k] * MIDPOINTS[k]) for k in range(19))
        pv_l = sum(liabs[k] * math.exp(-r0[k] * MIDPOINTS[k]) for k in range(19))
        d_a = sum(MIDPOINTS[k] * assets[k] * math.exp(-r0[k] * MIDPOINTS[k]) for k in range(19)) / pv_a
        d_l = sum(MIDPOINTS[k] * liabs[k] * math.exp(-r0[k] * MIDPOINTS[k]) for k in range(19)) / pv_l
        dgap = d_a - pv_l / pv_a * d_l
        ladder.append({
            "nmd_assumption": n,
            "repricing_gap": [{"bucket": k + 1, "midpoint_years": MIDPOINTS[k], "assets": r(assets[k]), "liabilities": r(liabs[k]),
                               "gap": r(assets[k] - liabs[k])} for k in range(19)],
            "delta_nii_gap_100bp_up": r(-sum((assets[k] - liabs[k]) * 0.01 * (1 - MIDPOINTS[k]) for k in range(6))),
            "duration_gap": {"asset_value": r(pv_a), "liability_value": r(pv_l), "asset_duration_years": r(d_a, 9),
                             "liability_duration_years": r(d_l, 9), "duration_gap_years": r(dgap, 9),
                             "equity_change_100bp_up": r(-dgap * pv_a * 0.01)},
        })
    pts = [{"tenor_years": r(t, 6), "observed_yield": y, "zero_rate": y} for t, y in sp["par"]]
    r1 = r0[1]
    dyn_items = [
        {"item_id": "D1", "side": "asset", "balance": r(35e6 * s), "rate0": r(r1 + 0.02, 9), "spread": 0.02, "beta": 1.0, "reprice_months": 0},
        {"item_id": "D2", "side": "asset", "balance": r(115e6 * s), "rate0": 0.03, "spread": 0.03, "beta": 1.0, "reprice_months": 60},
        {"item_id": "D3", "side": "asset", "balance": r(8e6 * s), "rate0": r(r1, 9), "spread": 0.0, "beta": 1.0, "reprice_months": 0},
        {"item_id": "D4", "side": "liability", "balance": r(155e6 * s), "rate0": r(sp["beta"] * r1, 9), "spread": 0.0,
         "beta": sp["beta"], "reprice_months": 0},
        {"item_id": "D5", "side": "liability", "balance": r(12e6 * s), "rate0": r(r1, 9), "spread": 0.0, "beta": 1.0, "reprice_months": 6},
        {"item_id": "D6", "side": "liability", "balance": r(10e6 * s), "rate0": r(r1 + 0.001, 9), "spread": 0.001, "beta": 1.0,
         "reprice_months": 12},
    ]
    dyn = {"horizon_months": 12,
           "balance_sheet_assumption": {"kind": "constant", "growth_annual": 0,
                                        "description": txt("Constant balance sheet: maturing and repricing flows are replaced by identical new ones.",
                                                           "Balance constante: los flujos que vencen o reprecian se reemplazan por otros identicos.")},
           "items": dyn_items, "scenarios": dyn_block(dyn_items, r1, 200, sp["floor"], 12)}
    base_nii = dyn["scenarios"][0]["total"]
    base_eve24 = next(x for x in scenarios if x["calibration"] == "2024" and x["nmd_assumption"] == "behavioural")["base_eve"]
    lv = []
    for level, fn, fe in ((0.95, 0.07, 0.10), (0.99, 0.10, 0.15)):
        nq, eq = r(base_nii - fn * abs(base_nii)), r(base_eve24 - fe * abs(base_eve24))
        lv.append({"level": level, "nii_quantile": nq, "eve_quantile": eq, "ear": r(base_nii - nq), "evar": r(base_eve24 - eq),
                   "ear_se": r(abs(base_nii - nq) * 0.01), "evar_se": r(abs(base_eve24 - eq) * 0.01)})
    ear_evar = {"method": "hw1f", "n_paths": 10000, "seed": 0, "horizon_months": 12,
                "parameters": [{"name": "a", "value": 0.1, "unit": "per year"}, {"name": "sigma", "value": 0.01, "unit": "per year"}],
                "base_nii": base_nii, "base_eve": base_eve24, "levels": lv,
                "mc_error_method": "batch-means", "n_batches": 20}
    if quarter == "2021-Q4":
        proj = dyn["scenarios"][1]["delta_vs_base"]
        real = r(proj * 1.12)
        oos = {"applicable": True, "projection_date": sp["date"], "realised_period_start": "2022-01-01",
               "realised_period_end": "2022-12-31", "projected_delta_nii": proj, "realised_delta_nii": real,
               "relative_error": r(abs(proj - real) / abs(real), 9), "reason": None}
    else:
        oos = {"applicable": False, "projection_date": sp["date"], "realised_period_start": None, "realised_period_end": None,
               "projected_delta_nii": None, "realised_delta_nii": None, "relative_error": None,
               "reason": txt("No call report dated after this valuation date is read, so no realised period exists.",
                             "No se lee ningun reporte posterior a esta fecha de valoracion, asi que no hay periodo realizado.")}
    outputs = {
        "kind": "valuation-date", "valuation_date": sp["date"], "quarter": quarter, "currency": "USD",
        "sign_convention": sign_convention(), "units": units("thousands"),
        "bank": {"name": "Silicon Valley Bank (fixture values)", "cert": 24735, "aggregates": "real", "behaviour": "synthetic",
                 "notice": txt("Fixture, not a result. Round numbers for the contract; the bake reads the FDIC financials.",
                               "Ejemplo, no es un resultado. Numeros redondos para el contrato; el proceso lee los estados de la FDIC.")},
        "data": {"call_reports": [{"report_date": d, "source": "fixture: FDIC BankFind financials (not read)",
                                   "fields": ["fixture:total-assets", "fixture:deposits"]} for d in sp["reports"]],
                 "data_cutoff": sp["reports"][-1], "read_up_to_valuation_date": True,
                 "rule": txt("Call reports are read only up to the valuation date; later reports are never read.",
                             "Los reportes se leen solo hasta la fecha de valoracion; nunca los posteriores.")},
        "curve": {"date": sp["date"], "source": "fixture: US Treasury daily par yield curve (values are fixtures)",
                  "observed_kind": "par-yield", "compounding": "continuous",
                  "interpolation": "linear in tenor, flat outside the grid (fixture); zero rate set equal to the par yield",
                  "missing_tenors": [r(t, 6) for t in sp["missing_tenors"]], "points": pts, "zero_rates_at_midpoints": r0},
        "assumptions": assumptions, "nmd_segments": segments,
        "balance_sheet": {"as_of": sp["date"], "items": items,
                          "total_assets": r(sum(i["amount"] for i in items if i["side"] == "asset")),
                          "total_liabilities": r(sum(i["amount"] for i in items if i["side"] == "liability"))},
        "ladder": ladder, "scenarios": scenarios, "dynamic_nii": dyn, "ear_evar": ear_evar, "out_of_sample": oos,
        "behavioural_comparison": comparison,
    }
    sc24b = next(x for x in scenarios if x["calibration"] == "2024" and x["nmd_assumption"] == "behavioural")
    sc24c = next(x for x in scenarios if x["calibration"] == "2024" and x["nmd_assumption"] == "contractual")
    doc = {
        "schema": "contraste.case/v1", "case_id": "C14", "variant_id": f"fixture-{quarter.lower()}",
        "model": [model_summary("irrbb-eve-standardised", "standardised-eve")], "outputs": outputs,
        "tests": [test_row("irrbb.eve_with_without_behavioural", "irrbb-eve-standardised"),
                  test_row("irrbb.srp31_92_goldens", "irrbb-eve-standardised")],
        "impact": {
            "eve_risk_measure_behavioural": {"value": sc24b["eve_risk_measure"], "unit": "USD thousands",
                                             "label": txt("EVE risk measure, 2024 shocks, behavioural NMD",
                                                          "Medida de riesgo EVE, choques 2024, NMD conductual")},
            "eve_risk_measure_contractual": {"value": sc24c["eve_risk_measure"], "unit": "USD thousands",
                                             "label": txt("EVE risk measure, 2024 shocks, contractual NMD",
                                                          "Medida de riesgo EVE, choques 2024, NMD contractual")},
        },
        "findings": [], **fixture_envelope(),
    }
    return doc, {"tier1": tier1}


def c14_models() -> dict:
    tables = [
        {"calibration": "2024", "source": "SRP31.90 Table 2 (in force 2026-01-01; d578 recalibration, dossier 01 H.3)",
         "data_window": "January 2000 to December 2023", "percentile": "99.9th percentile of local rolling six-month average absolute changes",
         "rounding_bp": 25, "rows": [{"currency": c, "parallel_bp": T2024["parallel"][i], "short_bp": T2024["short"][i],
                                      "long_bp": T2024["long"][i]} for i, c in enumerate(CCY21)]},
        {"calibration": "2016", "source": "BCBS d368 Annex 2 Table 1 (dossier 01 H.3)", "data_window": "2000 to 2015",
         "percentile": "99th percentile of global factors", "rounding_bp": 50,
         "rows": [{"currency": c, "parallel_bp": T2016["parallel"][i], "short_bp": T2016["short"][i], "long_bp": T2016["long"][i]}
                  for i, c in enumerate(CCY21)]},
    ]
    models = []
    wins = [("2018-01-01", "2020-12-31"), ("2019-01-01", "2021-12-31")]
    tr = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0]
    weights = {"wholesale": [0.45, 0.25, 0.15, 0.10, 0.05, 0.0], "retail-transactional": [0.10, 0.15, 0.20, 0.35, 0.15, 0.05],
               "retail-non-transactional": [0.20, 0.20, 0.25, 0.25, 0.10, 0.0]}
    for date in ("2021-12-31", "2022-12-31"):
        for cat in ("wholesale", "retail-transactional", "retail-non-transactional"):
            w = weights[cat]
            wam = sum(a * m / 2 for a, m in zip(w, tr))
            shifted = [round(max(0.0, a + (0.02 if i == 0 else -0.02 if i == 1 else 0.0)), 4) for i, a in enumerate(w)]
            shifted[-1] = round(1.0 - sum(shifted[:-1]), 4)
            models.append({
                "valuation_date": date, "category": cat,
                "tranches": [{"maturity_years": m, "weight": a} for m, a in zip(tr, w)], "weights_sum": r(sum(w), 9),
                "weighted_average_maturity_years": r(wam, 9),
                "margin_volatility": None if cat == "wholesale" and date == "2021-12-31" else 0.0012,
                "margin_volatility_reason": txt("The window holds too few margin observations for the fit.",
                                                "La ventana tiene muy pocas observaciones de margen para el ajuste.")
                if cat == "wholesale" and date == "2021-12-31" else None,
                "deposit_beta": {"up": 0.30 if date == "2021-12-31" else 0.45, "down": 0.25 if date == "2021-12-31" else 0.35,
                                 "source_kind": "fitted", "source": "fixture value standing for a fit"},
                "stability": [{"window_start": a, "window_end": b, "weights": ww,
                               "weighted_average_maturity_years": r(sum(x * m / 2 for x, m in zip(ww, tr)), 9)}
                              for (a, b), ww in zip(wins, (w, shifted))],
            })
    changes = [
        {"parameter": "core share, retail non-transactional", "category": "retail-non-transactional", "from_date": "2021-12-31",
         "to_date": "2022-12-31", "from_value": 0.65, "to_value": 0.75, "unit": "share", "limit_breach_in_window": True,
         "flagged": True, "note": txt("The core share rose in a window that holds a limit breach.", "La proporcion estable subio en una ventana con exceso de limite.")},
        {"parameter": "core maturity, wholesale", "category": "wholesale", "from_date": "2021-12-31", "to_date": "2022-12-31",
         "from_value": 3.0, "to_value": 3.0, "unit": "years", "limit_breach_in_window": True, "flagged": False,
         "note": txt("Unchanged.", "Sin cambio.")},
        {"parameter": "core share, wholesale", "category": "wholesale", "from_date": "2021-12-31", "to_date": "2022-12-31",
         "from_value": 0.35, "to_value": 0.40, "unit": "share", "limit_breach_in_window": False, "flagged": False,
         "note": txt("Changed in a window without a limit breach.", "Cambio en una ventana sin exceso de limite.")},
    ]
    return {
        "schema": "contraste.models/v1", "case_id": "C14", "fit_id": "fixture-svb-2021-2022",
        "model": [model_record("irrbb-eve-standardised", "standardised-eve")],
        "fit": {
            "currency": "USD", "sign_convention": sign_convention(), "units": units("thousands"),
            "bank": {"name": "Silicon Valley Bank (fixture values)", "cert": 24735, "aggregates": "real", "behaviour": "synthetic",
                     "notice": txt("Fixture, not a result.", "Ejemplo, no es un resultado.")},
            "buckets": buckets(), "shock_tables": tables,
            "applied_sizes": [shock_size("USD", T2024, "srp31-table-2024"), shock_size("USD", T2016, "srp31-table-2016")],
            "shock_shape": {"x": 4, "steepener_short": -0.65, "steepener_long": 0.9, "flattener_short": 0.8, "flattener_long": -0.6,
                            "short_form": "exp(-t_k / x)", "long_form": "1 - exp(-t_k / x)", "reference": "SRP31.91 to SRP31.92"},
            "nmd_caps": [{"category": c, "core_share_cap": a, "core_maturity_cap_years": b, "reference": "SRP31 Table 4 (SRP31.107 to SRP31.112)"}
                         for c, (a, b) in (("retail-transactional", (0.9, 5.0)), ("retail-non-transactional", (0.7, 4.5)),
                                           ("wholesale", (0.5, 4.0)))],
            "multipliers": {"prepayment_gamma": [{"shock": s, "gamma": g} for s, g in zip(SHOCKS, GAMMA)],
                            "term_deposit_u": [{"shock": s, "u": u} for s, u in zip(SHOCKS, UMULT)],
                            "reference": "SRP31.119 Table 5 and SRP31.125 Table 6"},
            "nmd_models": models, "nmd_parameter_changes": changes,
            "outlier": {"threshold_share_tier1": 0.15, "reference": "SRP31.82 to SRP31.83"},
        },
        **fixture_envelope(),
    }


# ------------------------------------------------------------------------------------------------------- C15

UF_VALUE = 39000.0


def ns(m: float, b0: float, b1: float, b2: float, tau: float) -> float:
    x = m / tau
    f = (1 - math.exp(-x)) / x if x > 1e-9 else 1.0
    return b0 + b1 * f + b2 * (f - math.exp(-x))


def cmf_pair(clp: float, clf: float) -> float:
    if clp * clf >= 0:
        return max(clp, 0.0) + max(clf, 0.0)
    return max(0.5 * clp + clf, 0.0) if clp <= 0 else max(clp + 0.5 * clf, 0.0)


C15_PARAMS = {"CLP": (0.048, -0.020, 0.006, 2.5), "UR": (0.022, -0.018, 0.004, 2.0)}
C15_VARIANTS = {
    "long-uf": dict(state="on", cpi=None, label=("Long UF", "UF largo"),
                    desc=("A net long UF book funded partly in CLP.", "Libro con posicion neta larga en UF financiada en parte en CLP."),
                    clp_assets=[("loans-floating", [(3, 800e3), (4, 900e3), (5, 800e3)]), ("loans-fixed", [(7, 400e3), (9, 400e3), (11, 400e3)]),
                                ("securities", [(10, 500e3), (13, 500e3)]), ("cash", [(1, 400e3)])],
                    clp_liabs=[("deposits-time", [(3, 1500e3), (4, 1000e3)]), ("borrowings", [(6, 300e3), (12, 500e3)])],
                    nmd=2200e3, ur_assets=[("loans-uf", [(11, 5.0), (13, 8.0), (15, 9.0), (16, 8.0)]), ("securities", [(9, 2.0), (12, 2.0)])],
                    ur_liabs=[("deposits-time", [(4, 4.0), (7, 6.0)]), ("borrowings", [(13, 8.0)])]),
    "offset-on-off": dict(state="compared", cpi=None, label=("CLP/CLF offset on and off", "Compensacion CLP/CLF activada y desactivada"),
                          desc=("Long CLP funding against long UF assets, so the two legs move in opposite directions.",
                                "Fondeo largo en CLP contra activos largos en UF: los dos tramos se mueven en sentido contrario."),
                          clp_assets=[("loans-floating", [(3, 700e3), (4, 800e3)]), ("securities", [(9, 300e3)]), ("cash", [(1, 300e3)])],
                          clp_liabs=[("deposits-time", [(11, 1000e3), (13, 1000e3)]), ("borrowings", [(14, 600e3)])],
                          nmd=1000e3, ur_assets=[("loans-uf", [(11, 6.0), (13, 9.0), (15, 9.0), (16, 8.0)]), ("securities", [(9, 3.0)])],
                          ur_liabs=[("deposits-time", [(4, 3.0), (7, 3.0)])]),
    "cpi-surprise": dict(state="on", cpi=2.5, nmd_req=0.95, label=("CPI surprise +2.5 pp", "Sorpresa de IPC +2,5 pp"),
                         desc=("The long UF book under a 2.5 percentage point inflation surprise.",
                               "El libro largo en UF ante una sorpresa de inflacion de 2,5 puntos porcentuales."),
                         clp_assets=[("loans-floating", [(3, 800e3), (4, 900e3), (5, 800e3)]), ("loans-fixed", [(7, 400e3), (9, 400e3), (11, 400e3)]),
                                     ("securities", [(10, 500e3), (13, 500e3)]), ("cash", [(1, 400e3)])],
                         clp_liabs=[("deposits-time", [(3, 1500e3), (4, 1000e3)]), ("borrowings", [(6, 300e3), (12, 500e3)])],
                         nmd=2200e3, ur_assets=[("loans-uf", [(11, 5.0), (13, 8.0), (15, 9.0), (16, 8.0)]), ("securities", [(9, 2.0), (12, 2.0)])],
                         ur_liabs=[("deposits-time", [(4, 4.0), (7, 6.0)]), ("borrowings", [(13, 8.0)])]),
}


def c15_curve(kind: str) -> dict:
    b0, b1, b2, tau = C15_PARAMS[kind]
    obs = [2.0, 10.0] if kind == "UR" else [5.0, 10.0]
    codes = (["F022.BUF.TIS.AN02.UF.Z.D", "F022.BUF.TIS.AN10.UF.Z.D"] if kind == "UR" else ["F022.BCLP.TIS.AN05.NO.Z.D"])
    return {
        "curve": kind, "month": "2026-06", "date": "2026-06-30", "source": "fixture: BCCh BDE F022 sovereign yields (values are fixtures)",
        "series_codes": codes,
        "attribution": "Source: Banco Central de Chile (BDE), series " + ", ".join(codes) + ". The fitted zero curve is an adaptation "
                       "by Contraste and is its sole responsibility (BCCh terms). Fixture, not a result.",
        "observed_kind": "secondary-market-yield", "compounding": "continuous",
        "fit": {"model": "nelson-siegel", "parameters": [{"name": n, "value": v, "unit": u} for n, v, u in
                                                          (("beta0", b0, "decimal"), ("beta1", b1, "decimal"), ("beta2", b2, "decimal"),
                                                           ("tau", tau, "years"))], "rmse_bp": 0.0},
        "points": [{"tenor_years": t, "observed_yield": r(ns(t, b0, b1, b2, tau), 9), "zero_rate": r(ns(t, b0, b1, b2, tau), 9)}
                   for t in obs],
        "zero_rates_at_midpoints": [r(ns(m, b0, b1, b2, tau), 9) for m in MIDPOINTS],
    }


def c15_outputs(vid: str) -> dict:
    sp = C15_VARIANTS[vid]
    rates = {"CLP": c15_curve("CLP")["zero_rates_at_midpoints"], "UR": c15_curve("UR")["zero_rates_at_midpoints"]}
    floors = {"CLP": 0.0, "UR": -0.02}
    # segments: one retail-operational NMD segment on the CLP leg
    req = sp.get("nmd_req", 0.80)
    share_used = min(req, 0.9)
    seg = {"category": "retail-operational", "balance": r(sp["nmd"]), "requested_core_share": req, "core_share_cap": 0.9,
           "core_share_used": share_used, "requested_core_maturity_years": 4.5, "core_maturity_cap_years": 5.0,
           "core_maturity_used_years": 4.5, "cap_applied": req > 0.9,
           "source_kind": "synthetic-stated", "source": "fixture value, synthetic behaviour stated"}
    assumptions = {
        "nmd_core_share": assumption(share_used, "share", "synthetic-stated", "balance-weighted average of the used values of nmd_segments"),
        "nmd_core_maturity_years": assumption(4.5, "years", "synthetic-stated", "balance-weighted average of the used values of nmd_segments"),
        "prepayment_cpr": assumption(0.06, "per year", "synthetic-stated", "fixture value; no item carries the prepayable-loan class"),
        "term_deposit_redemption_rate": assumption(0.05, "share of the term deposit", "synthetic-stated", "fixture value"),
        "deposit_beta": assumption(0.40, "pass-through", "synthetic-stated", "fixture value"),
    }
    # NB: with one segment the weighted averages equal the segment values
    legs = []
    base = {}
    for leg, cur, assets, liabs in (("CLP", "CLP", sp["clp_assets"], sp["clp_liabs"]), ("UR", "CLF", sp["ur_assets"], sp["ur_liabs"])):
        items = []
        n = 0

        def push(side, cat, bclass, flows, src):
            nonlocal n
            n += 1
            sign = 1 if side == "asset" else -1
            cf = merge_flows([fl(b, sign * a) for b, a in flows])
            items.append({"item_id": f"{leg}{n}", "label": txt(f"{leg} {cat}", f"{leg} {cat}"), "side": side, "category": cat,
                          "behavioural_class": bclass, "source": src, "amount": r(sum(a for _, a in flows)), "cash_flows": cf})

        for cat, flows in assets:
            push("asset", cat, "none", flows, "synthetic, calibrated to CMF aggregates (fixture)")
        for cat, flows in liabs:
            push("liability", cat, "term-deposit" if cat == "deposits-time" else "none", flows, "synthetic, calibrated to CMF aggregates (fixture)")
        if leg == "CLP":
            cf = merge_flows(nmd_flows(sp["nmd"], share_used, 4.5, True))
            items.append({"item_id": "CLP-NMD", "label": txt("CLP current accounts", "Cuentas corrientes en CLP"), "side": "liability",
                          "category": "deposits-nmd", "behavioural_class": "nmd-retail-operational",
                          "source": "synthetic, calibrated to CMF aggregates (fixture)", "amount": r(sp["nmd"]), "cash_flows": cf})
        net = sum((1 if i["side"] == "asset" else -1) * i["amount"] for i in items)
        legs.append({"leg": leg, "currency": cur, "items": items,
                     "assets_total": r(sum(i["amount"] for i in items if i["side"] == "asset")),
                     "liabilities_total": r(sum(i["amount"] for i in items if i["side"] == "liability")), "net_position": r(net)})
        conv = UF_VALUE if leg == "UR" else 1.0
        base[leg] = [v * conv for v in dense([f for i in items for f in i["cash_flows"]])]
    eve_sizes = [
        {"currency": "CLP", "parallel_bp": 300, "short_bp": 400, "long_bp": 200, "origin": "cmf-annex1", "label": None, "method": None},
        {"currency": "CLF", "parallel_bp": 200, "short_bp": 250, "long_bp": 150, "origin": "cmf-annex1", "label": None, "method": None},
    ]
    nii_sizes = [{"currency": "CLP", "parallel_bp": 300, "origin": "cmf-annex1"}, {"currency": "CLF", "parallel_bp": 300, "origin": "cmf-annex1"}]
    state = sp["state"]
    base_eve = {n: eve_of(base[n], rates[n]) for n in base}
    floor_effects = []
    eve_rows = []
    for shock in SHOCKS:
        res = {}
        for leg, sz in (("CLP", eve_sizes[0]), ("UR", eve_sizes[1])):
            sh = shape(shock, sz["parallel_bp"], sz["short_bp"], sz["long_bp"])
            rr = [post(a, d, floors[leg]) for a, d in zip(rates[leg], sh)]
            bound = [k + 1 for k in range(19) if rates[leg][k] + sh[k] / 1e4 < min(floors[leg], rates[leg][k])]
            eve = eve_of(base[leg], rr)
            delta = base_eve[leg] - eve
            res[leg] = {"shape_bp": [r(x, 9) for x in sh], "floor_bound_buckets": bound, "net_cash_flows": [r(x) for x in base[leg]],
                        "eve": r(eve), "kao": 0.0, "delta_eve": r(delta)}
            if bound:
                nofloor = [rates[leg][k] + sh[k] / 1e4 for k in range(19)]
                wo = base_eve[leg] - eve_of(base[leg], nofloor)
                floor_effects.append({"leg": leg, "measure": "delta-eve", "shock": shock, "buckets_floored": len(bound),
                                      "delta_with_floor": r(delta), "delta_without_floor": r(wo), "effect": r(r(delta) - r(wo))})
        d_clp, d_ur = res["CLP"]["delta_eve"], res["UR"]["delta_eve"]
        w, wo = cmf_pair(d_clp, d_ur), max(d_clp, 0) + max(d_ur, 0)
        used = wo if state == "off" else w
        eve_rows.append({"shock": shock, "clp": res["CLP"], "ur": res["UR"],
                         "pair": {"delta_clp": d_clp, "delta_ur": d_ur, "opposite_signs": d_clp * d_ur < 0, "with_offset": r(w),
                                  "without_offset": r(wo), "used": r(used)},
                         "total_delta_eve": r(used)})
    nii_rows = []
    for shock, sign in (("parallel-up", 1), ("parallel-down", -1)):
        res = {}
        for leg in ("CLP", "UR"):
            bp = sign * 300
            rr = [post(rates[leg][k], bp, floors[leg]) for k in range(6)]
            bound = [k + 1 for k in range(6) if rates[leg][k] + bp / 1e4 < min(floors[leg], rates[leg][k])]
            delta = sum(base[leg][k] * (rates[leg][k] - rr[k]) * (1 - MIDPOINTS[k]) for k in range(6))
            res[leg] = {"shock_bp": float(bp), "cash_flows": [r(x) for x in base[leg][:6]], "floor_bound_buckets": bound,
                        "delta_nii": r(delta)}
            if bound:
                wo = sum(base[leg][k] * (-bp / 1e4) * (1 - MIDPOINTS[k]) for k in range(6))
                floor_effects.append({"leg": leg, "measure": "delta-nii", "shock": shock, "buckets_floored": len(bound),
                                      "delta_with_floor": r(delta), "delta_without_floor": r(wo), "effect": r(r(delta) - r(wo))})
        d_clp, d_ur = res["CLP"]["delta_nii"], res["UR"]["delta_nii"]
        w, wo = cmf_pair(d_clp, d_ur), max(d_clp, 0) + max(d_ur, 0)
        used = wo if state == "off" else w
        nii_rows.append({"shock": shock, "clp": res["CLP"], "ur": res["UR"],
                         "pair": {"delta_clp": d_clp, "delta_ur": d_ur, "opposite_signs": d_clp * d_ur < 0, "with_offset": r(w),
                                  "without_offset": r(wo), "used": r(used)}})
    totals = [x["total_delta_eve"] for x in eve_rows]
    delta_eve = max(totals)
    assert delta_eve > 0, vid
    pairs = [x["pair"]["used"] for x in nii_rows]
    pn_uf = legs[1]["net_position"]
    pn = pn_uf * UF_VALUE
    charge = 0.025 * abs(pn)
    delta_nii = max(pairs) + charge
    tier1 = round(delta_eve / 0.10, -3)
    margin = round(delta_nii / 0.12, -3)
    tests = []
    for tid, meas, bse, thr in (("nii-tier1", delta_nii, tier1, 0.05), ("eve-tier1", delta_eve, tier1, 0.15),
                                ("nii-margin", delta_nii, margin, 0.18)):
        ratio = meas / bse
        tests.append({"id": tid, "measure": r(meas), "base": r(bse), "ratio": r(ratio, 9), "threshold": thr, "breached": ratio > thr})
    if state == "compared":
        assert any(x["pair"]["opposite_signs"] for x in eve_rows + nii_rows), "no opposite-sign shock in the compared fixture"
        assert any(abs(x["pair"]["with_offset"] - x["pair"]["without_offset"]) > 1e-6 for x in eve_rows + nii_rows)
    cpi = None
    if sp["cpi"] is not None:
        cpi = {"surprise_pp": sp["cpi"], "effect": r(-pn * sp["cpi"] / 100), "formula": "effect = -pn_ur x surprise_pp / 100 (loss-positive)"}
    dyn_legs = []
    for leg_name, leg in (("CLP", legs[0]), ("UR", legs[1])):
        conv = UF_VALUE if leg_name == "UR" else 1.0
        a_tot, l_tot = leg["assets_total"] * conv, leg["liabilities_total"] * conv
        r1 = rates[leg_name][1]
        beta = 0.4 if leg_name == "CLP" else 0.2
        its = [
            {"item_id": f"{leg_name}-D1", "side": "asset", "balance": r(0.4 * a_tot), "rate0": r(r1 + 0.02, 9), "spread": 0.02, "beta": 1.0, "reprice_months": 0},
            {"item_id": f"{leg_name}-D2", "side": "asset", "balance": r(0.6 * a_tot), "rate0": 0.04, "spread": 0.04, "beta": 1.0, "reprice_months": 60},
            {"item_id": f"{leg_name}-D3", "side": "liability", "balance": r(0.5 * l_tot), "rate0": r(beta * r1, 9), "spread": 0.0, "beta": beta, "reprice_months": 0},
            {"item_id": f"{leg_name}-D4", "side": "liability", "balance": r(0.5 * l_tot), "rate0": r(r1, 9), "spread": 0.0, "beta": 1.0, "reprice_months": 12},
        ]
        dyn_legs.append({"leg": leg_name, "items": its, "scenarios": dyn_block(its, r1, 300, floors[leg_name], 12)})
    ear15 = []
    for dl in dyn_legs:
        b_nii, b_eve = dl["scenarios"][0]["total"], base_eve["CLP" if dl["leg"] == "CLP" else "UR"]
        lv = []
        for level, fn, fe in ((0.95, 0.07, 0.10), (0.99, 0.10, 0.15)):
            nq, eq = r(b_nii - fn * abs(b_nii)), r(b_eve - fe * abs(b_eve))
            lv.append({"level": level, "nii_quantile": nq, "eve_quantile": eq, "ear": r(b_nii - nq), "evar": r(b_eve - eq),
                       "ear_se": r(abs(b_nii - nq) * 0.01), "evar_se": r(abs(b_eve - eq) * 0.01)})
        ear15.append({"leg": dl["leg"], "method": "hw1f", "n_paths": 10000, "seed": 0, "horizon_months": 12,
                      "parameters": [{"name": "a", "value": 0.1, "unit": "per year"}, {"name": "sigma", "value": 0.01, "unit": "per year"}],
                      "base_nii": b_nii, "base_eve": r(b_eve), "levels": lv, "mc_error_method": "batch-means", "n_batches": 20})
    dyn15 = {"horizon_months": 12,
             "balance_sheet_assumption": {"kind": "constant", "growth_annual": 0,
                                          "description": txt("Constant balance sheet: maturing and repricing flows are replaced by identical new ones.",
                                                             "Balance constante: los flujos que vencen o reprecian se reemplazan por otros identicos.")},
             "legs": dyn_legs}
    outputs = {
        "kind": "annex1-variant",
        "variant": {"id": vid, "label": txt(*sp["label"]), "description": txt(*sp["desc"]),
                    "parameters": [{"name": "net_uf_position", "value": r(pn_uf, 6), "unit": "millions CLF"}]},
        "as_of": "2026-06-30", "balance_sheet_month": "2026-06", "curves_month": "2026-06", "reporting_currency": "CLP",
        "sign_convention": sign_convention(), "units": units("millions"),
        "bank": {"name": "Banco Andino", "synthetic": True,
                 "notice": txt("Synthetic bank calibrated to public aggregates; fixture values.",
                               "Banco sintetico calibrado a agregados publicos; valores de ejemplo."),
                 "seed": 0, "calibration_source": "fixture, not a CMF figure"},
        "ur_currency": {"label": "UR", "code": "CLF", "treated_as_one_currency": True,
                        "definition": txt("All CLP-indexed (UF) flows are treated as one currency, UR (RAN 21-13 Annex 1).",
                                          "Todos los flujos reajustables (UF) se tratan como una sola moneda, UR (RAN 21-13 Anexo 1)."),
                        "uf_value": UF_VALUE, "uf_value_currency": "CLP", "uf_date": "2026-06-30",
                        "uf_source": "fixture value, not the BCCh UF"},
        "curves": {"clp": c15_curve("CLP"), "ur": c15_curve("UR")}, "assumptions": assumptions, "nmd_segments": [seg],
        "legs": legs, "eve_shock_sizes": eve_sizes, "nii_shock_sizes": nii_sizes, "dynamic_nii": dyn15, "ear_evar": ear15,
        "floors": {"ur_floor": -0.02, "other_floor": 0.0,
                   "rule": txt("Post-shock rates are floored at -2 percent for UR and at 0 percent for CLP. The fixture also keeps a rate that is already below its floor at its pre-shock value, for both floors; whether Annex 1 applies that clause to the UR floor is UNVERIFIED.",
                               "Las tasas post choque tienen piso de -2 por ciento para UR y 0 por ciento para CLP. El ejemplo tambien mantiene en su valor previo una tasa que ya esta bajo su piso, en ambos pisos; que el Anexo 1 aplique esa clausula al piso UR no esta verificado."),
                   "effects": floor_effects},
        "offset_rule": {"state": state, "share": 0.5, "applies_to": ["CLP", "CLF"],
                        "rule": txt("When delta CLP and delta CLF have opposite signs, half of the CLP is offset against the CLF (or the reverse), floored at zero.",
                                    "Si los deltas CLP y CLF tienen signos opuestos, se compensa la mitad del CLP contra el CLF (o al reves), con piso en cero."),
                        "reference": "RAN 21-13 Annex 1 Hojas 10 to 12 (dossier 03 F.2)"},
        "indexation_charge": {"rate": 0.025, "net_position_uf_units": r(pn_uf, 6), "pn_ur": r(pn), "abs_pn_ur": r(abs(pn)),
                              "charge": r(charge), "formula": "charge = 0.025 x |PN_UR|, PN_UR = net UF position x UF value",
                              "note": txt("The standardised indexation (reajustabilidad) charge, an implied 2.5 percent inflation surprise.",
                                          "El cargo estandar por reajustabilidad, equivalente a una sorpresa de inflacion de 2,5 por ciento.")},
        "cpi_scenario": cpi,
        "eve": {"base_eve_clp": r(base_eve["CLP"]), "base_eve_ur": r(base_eve["UR"]), "rows": eve_rows, "delta_eve": r(delta_eve),
                "worst_shock": SHOCKS[totals.index(delta_eve)], "delta_eve_share_tier1": r(delta_eve / tier1, 9)},
        "nii": {"rows": nii_rows, "max_pair": r(max(pairs)), "indexation_charge": r(charge), "delta_nii": r(delta_nii),
                "worst_shock": ["parallel-up", "parallel-down"][pairs.index(max(pairs))] if max(pairs) > 0 else None,
                "delta_nii_share_tier1": r(delta_nii / tier1, 9)},
        "thresholds": {"tier1": r(tier1), "net_interest_and_indexation_margin_12m": r(margin), "tests": tests,
                       "prioritised": any(t["breached"] for t in tests), "reference": "RAN 21-13 Annex 1 (banco priorizado, dossier 03 F.2)"},
    }
    return {
        "schema": "contraste.case/v1", "case_id": "C15", "variant_id": f"fixture-{vid}",
        "model": [model_summary("irrbb-annex1", "cmf-annex1")], "outputs": outputs,
        "tests": [test_row("irrbb.cmf_annex1_goldens", "irrbb-annex1")],
        "impact": {"delta_eve": {"value": r(delta_eve), "unit": "CLP millions", "label": txt("Delta EVE, Annex 1", "Delta EVE, Anexo 1")},
                   "delta_nii": {"value": r(delta_nii), "unit": "CLP millions",
                                 "label": txt("Delta NII with the indexation charge", "Delta NII con el cargo por reajustabilidad")}},
        "findings": [], **fixture_envelope(),
    }


def c15_models() -> dict:
    return {
        "schema": "contraste.models/v1", "case_id": "C15", "fit_id": "fixture-banco-andino-2026-06",
        "model": [model_record("irrbb-annex1", "cmf-annex1")],
        "fit": {
            "reporting_currency": "CLP", "sign_convention": sign_convention(), "units": units("millions"),
            "bank": {"name": "Banco Andino", "synthetic": True,
                     "notice": txt("Synthetic bank calibrated to public aggregates; fixture values.",
                                   "Banco sintetico calibrado a agregados publicos; valores de ejemplo."),
                     "seed": 0, "calibration_source": "fixture, not a CMF figure"},
            "buckets": buckets(),
            "annex1_table": [{"basket": "canasta-1", "parallel_bp": 200, "short_bp": 300, "long_bp": 150},
                             {"basket": "canasta-2", "parallel_bp": 400, "short_bp": 500, "long_bp": 300},
                             {"basket": "CLP", "parallel_bp": 300, "short_bp": 400, "long_bp": 200},
                             {"basket": "UR-nii", "parallel_bp": 300, "short_bp": None, "long_bp": None},
                             {"basket": "UR-eve", "parallel_bp": 200, "short_bp": 250, "long_bp": 150}],
            "eve_shock_sizes": [
                {"currency": "CLP", "parallel_bp": 300, "short_bp": 400, "long_bp": 200, "origin": "cmf-annex1", "label": None, "method": None},
                {"currency": "CLF", "parallel_bp": 200, "short_bp": 250, "long_bp": 150, "origin": "cmf-annex1", "label": None, "method": None}],
            "floors": {"ur_floor": -0.02, "other_floor": 0.0, "reference": "RAN 21-13 Annex 1 Hoja 9 (dossier 03 F.2)"},
            "prioritised_thresholds": [{"id": "nii-tier1", "threshold": 0.05, "base": "Tier 1 capital"},
                                       {"id": "eve-tier1", "threshold": 0.15, "base": "Tier 1 capital"},
                                       {"id": "nii-margin", "threshold": 0.18, "base": "12-month cumulative net interest and indexation margin"}],
            "offset_share": 0.5, "indexation_rate": 0.025,
            "multipliers": {"prepayment_gamma": [{"shock": s, "gamma": g} for s, g in zip(SHOCKS, GAMMA)],
                            "term_deposit_u": [{"shock": s, "u": u} for s, u in zip(SHOCKS, UMULT)],
                            "reference": "RAN 21-13 Annex 1 (dossier 03 F.2)"},
            "nmd_caps": [{"category": c, "core_share_cap": a, "core_maturity_cap_years": b, "reference": "RAN 21-13 Annex 1 (dossier 03 F.2)"}
                         for c, (a, b) in (("retail-operational", (0.9, 5.0)), ("retail-non-operational", (0.7, 4.5)),
                                           ("wholesale", (0.5, 4.0)))],
            "curve_models": [
                {"curve": k, "month": "2026-06", "series_codes": c15_curve(k)["series_codes"], "model": "nelson-siegel",
                 "parameters": c15_curve(k)["fit"]["parameters"], "rmse_bp": 0.0, "attribution": c15_curve(k)["attribution"]}
                for k in ("CLP", "UR")],
            "calibration_targets": [{"metric": "UF share of loans", "unit": "share", "target": 0.60, "achieved": 0.58,
                                     "source": "fixture value, not a CMF figure", "as_of": "2026-06-30"}],
            "nmd_models": [{
                "valuation_date": "2026-06-30", "category": "retail-operational",
                "tranches": [{"maturity_years": m, "weight": w} for m, w in ((1.0, 0.2), (3.0, 0.3), (5.0, 0.3), (10.0, 0.2))],
                "weights_sum": 1.0, "weighted_average_maturity_years": r(sum(m * w / 2 for m, w in ((1.0, 0.2), (3.0, 0.3), (5.0, 0.3), (10.0, 0.2))), 9),
                "margin_volatility": 0.0011, "margin_volatility_reason": None,
                "deposit_beta": {"up": 0.40, "down": 0.30, "source_kind": "synthetic-stated", "source": "fixture value"},
                "stability": [{"window_start": "2021-01-01", "window_end": "2025-12-31", "weights": [0.2, 0.3, 0.3, 0.2],
                               "weighted_average_maturity_years": 2.3}]}],
            "prepayment": {"model": "psa", "cpr_base": 0.06, "psa_percent": 100.0, "source_kind": "synthetic-stated",
                           "source": "fixture value: the 100 percent PSA curve"},
        },
        **fixture_envelope(),
    }


def main() -> None:
    for q in C14_SPECS:
        doc, _ = c14_outputs(q)
        write(f"c14/variant-valuation-date-{q.lower()}-fixture.json", doc)
    write("c14/models-fixture.json", c14_models())
    for vid in C15_VARIANTS:
        write(f"c15/variant-annex1-variant-{vid}-fixture.json", c15_outputs(vid))
    write("c15/models-fixture.json", c15_models())


if __name__ == "__main__":
    main()
