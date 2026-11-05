"""Builds the U9-S fixture documents (docs/contracts/fixtures/c12 and regulatory).

Run: ``python tests/contracts_u9/u9_fixtures.py``. Deterministic, standard library only. The numbers are small and round on
purpose and are fixtures, never results: every document is labelled ``fixture`` in its provenance and ids, and no number is a
Monte Carlo output. They are internally consistent: the SA-CCR, BA-CVA, CVA, EEPE, GIRR and W^2 values are computed here with the
formulas of semantics.py (dossier 01 E, D.2; dossier 05 C; the addendum), which the tests recompute.

The values of the CRE99 examples and the output floor are the printed ones of dossier 01 E.2 and C.1.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import semantics as sm  # noqa: E402
import u9_schemas as sc  # noqa: E402

ROOT = HERE.parents[1]
FIX = ROOT / "docs" / "contracts" / "fixtures"
USD = "USD"


def r(x: float, d: int = 9) -> float:
    return round(x, d)


def txt(en: str, es: str) -> dict:
    return {"en": en, "es": es}


def money(x: float) -> dict:
    return {"amount": r(x, 6), "currency": USD}


def msd(x: float, se: float) -> dict:
    return {"amount": r(x, 6), "currency": USD, "mc_se": r(se, 6)}


def prof(values: list[float], rel_se: float = 0.01) -> dict:
    return {"currency": USD, "values": [r(v, 6) for v in values], "mc_se": [r(abs(v) * rel_se, 6) for v in values]}


def write(rel: str, doc: dict) -> None:
    path = FIX / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def provenance() -> dict:
    return {
        "truth_status": "synthetic-calibrated",
        "inputs": [{"source": "fixture-not-a-result", "class": "fixture", "files": []}],
        "licence_classes": {"fixture-not-a-result": "fixture"}, "generators": ["fixture:u9-s-contracts"], "seed": 0,
        "code_version": "fixture", "riskvalidation_version": None,
    }


def lane() -> dict:
    return {"lane": "precompute", "reasons": ["fixture"]}


def test_row(test_id: str, model_id: str) -> dict:
    return {
        "test_id": test_id, "model_id": model_id, "segment": None, "statistic": None, "p_value": None, "metric": None,
        "h0": "fixture row", "alternative": "fixture row", "policy_version": "fixture", "alpha_amber": None, "alpha_red": None,
        "light": "not_evaluated", "n": None, "n_events": None, "inputs_hash": "0" * 64, "reference": "fixture, not a result",
        "notes": "fixture: the test did not run, no number stands in for it", "extras": {},
    }


def model_summary(mid: str, rung: str) -> dict:
    return {
        "id": mid, "family": "ccr", "rung": rung, "title": txt(f"Fixture model {mid}", f"Modelo de ejemplo {mid}"),
        "short_title": txt(mid, mid), "engine": "riskvalidation", "engine_version": "fixture", "licence": "MIT",
        "calibration": None, "parameters": {}, "checkpoint_sha256": None,
    }


# ------------------------------------------------------------------------------------------------ C12 building blocks

GRID = [0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0]  # the fixture's grid; the bake's is finer, the six variants share it (m14)
CURVE_DATE = "2019-12-31"
CURVE_TENORS = [0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0]
CURVE_PAR = [0.0154, 0.0155, 0.0155, 0.0158, 0.0162, 0.0169, 0.0178, 0.0186]


def rule_rate(maturity: float) -> float:
    """The fixed-rate rule: the par yield at the swap's maturity on the curve date, rounded to 10 bp (half up)."""
    par = dict(zip(CURVE_TENORS, CURVE_PAR))[maturity]
    return math.floor(par * 1000 + 0.5) / 1000


TRADES = [  # conventions (D6, decision R1); payer pays the fixed rate; the fixed rate is the rule's output
    ("SW-1", 10_000_000.0, rule_rate(10.0), "payer", 10.0),
    ("SW-2", 6_000_000.0, rule_rate(5.0), "receiver", 5.0),
    ("SW-3", 4_000_000.0, rule_rate(3.0), "payer", 3.0),
    ("SW-4", 2_000_000.0, rule_rate(0.5), "receiver", 0.5),
]
SHAPES = {"SW-1": 1.00, "SW-2": 0.50, "SW-3": 0.30, "SW-4": 0.05}  # share of the single-swap EE scale, fixture
DF = [math.exp(-0.015 * t) for t in GRID]
LGD, BANK_LGD, SPREAD, BANK_SPREAD = 0.6, 0.6, 0.0125, 0.008
WWR_GRID = [-2.0, 0.0, 1.0, 2.0, 4.0]  # decision R1: per USD million
PAR_SENS = {0.5: -1.0e6, 3.0: 1.16e7, 5.0: -2.7e7, 10.0: 8.0e7}  # s_k = dV / 0.0001 at the tenor of each swap, fixture (MAR21.19)


def conv(value, unit: str) -> dict:
    return {"value": value, "unit": unit, "label": "convention"}


def named(mpor_long: int = 20) -> dict:
    vals = {
        "notionals": conv([t[1] for t in TRADES], "USD"), "maturities_years": conv([t[4] for t in TRADES], "years"),
        "sides": conv([t[3] for t in TRADES], "payer or receiver"), "netting_set_members": conv([t[0] for t in TRADES], "trade ids"),
        "single_swap_member": conv("SW-1", "trade id"),
        "fixed_rate_rule": conv("the par yield at the swap's maturity on the curve date, rounded to 10 bp", "rule"),
        "csa_threshold": conv(0.0, "USD"), "csa_minimum_transfer_amount": conv(10_000.0, "USD"),
        "csa_independent_amount": conv(0.0, "USD"), "mpor_business_days_short": conv(10, "business days"),
        "mpor_business_days_long": conv(mpor_long, "business days"), "counterparty_spread": conv(SPREAD, "decimal per year"),
        "counterparty_lgd": conv(LGD, "decimal"), "bank_spread": conv(BANK_SPREAD, "decimal per year"),
        "bank_lgd": conv(BANK_LGD, "decimal"), "pfe_quantile": conv(0.95, "decimal"), "path_count": conv(10000, "paths"),
        "seed": conv(20260101, "integer"), "time_grid_years": conv(GRID, "years"), "wwr_b_grid": conv(WWR_GRID, "per USD million"),
        "im_quantile": conv(0.99, "decimal"), "im_horizon_calendar_days": conv(14, "calendar days (10 business days)"),
        "im_mpor_calendar_days": conv(14, "calendar days (10 business days)"), "im_regression_order": conv(2, "polynomial order"),
        "ba_cva_sector": conv("financials", "MAR50.16 Table 1 sector"), "ba_cva_rating": conv("investment-grade", "class"),
        "stress_window_start": conv("2007-01-01", "date"), "stress_window_end": conv("2009-12-31", "date"),
        "backtest_window_start": conv("2000-01", "month"), "backtest_paths_per_date": conv(2000, "paths"),
        "backtest_simulated_critical_count": conv(1000, "simulated backtests"),
        "reconciliation_se_threshold": conv(2, "combined standard errors"), "ee_check_k_se": conv(3, "standard errors"),
    }
    assert list(vals) == sc.NAMED
    return vals


def trade_block(t) -> dict:
    return {"trade_id": t[0], "notional": money(t[1]), "fixed_rate": t[2], "side": t[3], "start_years": 0.0, "maturity_years": t[4],
            "fixed_frequency_per_year": 2, "floating_leg": "USD floating leg on the single curve of the case", "label": "convention"}


def curve_block() -> dict:
    ten, par = CURVE_TENORS, CURVE_PAR
    zero = [p - 0.0001 * i for i, p in enumerate(par)]
    return {
        "curve_date": CURVE_DATE, "source": "US Treasury daily par yield curve (home.treasury.gov)", "licence_class": "mirror-allowed",
        "par_yield_unit": "decimal, bond-equivalent", "zero_compounding": "continuous",
        "points": [{"tenor_years": t, "par_yield": p, "zero_rate": r(z, 6)} for t, p, z in zip(ten, par, zero)],
        "tenors_present": ten, "tenors_absent": [r(1 / 3, 6)], "interpolated_silently": False,
    }


def calibration_block(backtest: str, end: str, a: float = 0.08, sigma: float = 0.011) -> dict:
    return {
        "backtest_date": backtest, "model": "hw1f",
        "estimator": "exact AR(1) OLS on the shortest Treasury zero rate (Brigo et al., arXiv 0812.4210, equations 55 to 57)",
        "proxy_tenor_years": 0.25, "sample_start": f"{int(backtest[:4]) - 3}-01-02", "sample_end": end, "n_obs": 750,
        "history_years": 3.0, "a": a, "sigma": sigma, "a_se": 0.02, "sigma_se": 0.0005,
        "fit_to_curve": "phi(t) = f(0,t) + sigma^2 (1 - exp(-a t))^2 / (2 a^2), the QuantLib 1.44 fitting parameter",
    }


def single_ee(scale: float, maturity: float) -> list[float]:
    """The fixture EE of one swap: zero once the swap has matured."""
    return [scale * math.sqrt(t) * (1 - t / (2 * maturity)) if t < maturity else 0.0 for t in GRID]


def sa_block(trades, margined_mpor: int | None, v: float, c: float, th: float, mta: float, nica: float) -> dict:
    rows, d = [], [0.0, 0.0, 0.0]
    for tid, notional, _fx, side, mat in trades:
        sd = sm.supervisory_duration(0.0, mat)
        adj = notional * sd
        delta = 1.0 if side == "payer" else -1.0
        mf = sm.maturity_factor(mat, margined_mpor)
        bucket = sm.ir_bucket(mat)
        en = adj * delta * mf
        d["B1 B2 B3".split().index(bucket)] += en
        rows.append({"trade_id": tid, "hedging_set": USD, "start_years": 0.0, "end_years": mat, "notional": money(notional),
                     "supervisory_duration": r(sd), "adjusted_notional": money(adj), "delta": 1 if delta > 0 else -1,
                     "maturity_factor": r(mf), "bucket": bucket, "effective_notional": r(en, 6)})
    enh = sm.ir_effective_notional(*d)
    addon = 0.005 * enh
    mult = sm.multiplier(v - c, addon)
    rc = sm.rc_margined(v, c, th, mta, nica) if margined_mpor else sm.rc_unmargined(v, c)
    pfe = mult * addon
    return {
        "paragraph": "CRE52", "in_force_date": "2023-01-01", "margined": margined_mpor is not None, "v": money(v), "c": money(c),
        "th": money(th), "mta": money(mta), "nica": money(nica), "mpor_business_days": margined_mpor, "rc": money(rc),
        "trades": rows,
        "hedging_sets": [{"hedging_set": USD, "d_b1": r(d[0], 6), "d_b2": r(d[1], 6), "d_b3": r(d[2], 6), "offset": True,
                          "effective_notional": r(enh, 6), "supervisory_factor": 0.005, "addon": r(addon, 6)}],
        "addon_by_class": {"interest_rate": r(addon, 6), "fx": 0.0, "credit": 0.0, "equity": 0.0, "commodity": 0.0},
        "addon_aggregate": money(addon), "multiplier_floor": 0.05, "multiplier": r(mult), "pfe": money(pfe), "alpha": 1.4,
        "ead": money(1.4 * (rc + pfe)),
    }


def girr_block() -> dict:
    rw, corr = sc.GIRR_RW, [[x / 100 for x in row] for row in sc.GIRR_CORR]
    # s_k = (V(r + 1 bp) - V(r)) / 0.0001 at each GIRR tenor (MAR21.19): the book's four swaps sit at 0.5, 3, 5 and 10 years
    s = [PAR_SENS.get(t, 0.0) for t in sc.GIRR_TENORS]
    ws_div = [r(x * w / math.sqrt(2), 6) for x, w in zip(s, rw)]
    ks = {name: sm.sbm_bucket(ws_div, corr, name) for name in ("low", "medium", "high")}
    charge = max(r(k, 6) for k in ks.values())
    return {
        "paragraph": "MAR21.42 to MAR21.50", "in_force_date": "2023-01-01", "currency": USD, "sqrt2_division": True,
        "sqrt2_label": "convention", "sensitivities": s, "weighted_sensitivities": ws_div,
        "scenarios": [{"scenario": k, "k_b": r(ks[k], 6)} for k in ("low", "medium", "high")],
        "delta_charge": money(charge), "delta_charge_undivided": money(math.sqrt(2) * charge),
    }


def pits_for(seed: int, n: int = 6) -> list[float]:
    base = [(i + 1) / (n + 2) for i in range(n)]
    shift = [0.02, -0.03, 0.04, -0.01, 0.03, -0.02]
    return [r(min(max(b + shift[(i + seed) % 6] * 0.5, 0.01), 0.99), 6) for i, b in enumerate(base)]


def horizon_block(h: str, seed: int) -> dict:
    p = pits_for(seed)
    w2 = sm.anderson_darling_w2(p)
    crit = {"p05": 2.7, "p01": 4.3}
    return {
        "horizon": h, "n": len(p), "pits": p,
        "exceedances": [{"quantile": 0.95, "count": 0, "expected": r(len(p) * 0.05, 9)},
                        {"quantile": 0.99, "count": 0, "expected": r(len(p) * 0.01, 9)}],
        "w2": r(w2, 9), "critical_iid": {"p05": 2.492, "p01": 3.880}, "critical_simulated": crit,
        "effective_sample_size": 3.5, "reject_at_5pct": w2 > crit["p05"],
    }


def backtest_block() -> dict:
    book = [horizon_block(h, i) for i, h in enumerate(sc.HORIZONS)]
    rf = [horizon_block(h, i + 2) for i, h in enumerate(sc.HORIZONS)]
    subs = []
    for w, (a, b) in zip(sc.SUB_WINDOWS, [("2000-01-31", "2007-12-31"), ("2008-01-31", "2019-12-31"), ("2020-01-31", "2025-09-30")]):
        subs.append({"window": w, "start": a, "end": b,
                     "results": [{"horizon": h["horizon"], "n": h["n"], "w2": h["w2"]} for h in book[:2]]})
    return {
        "window_start": "2000-01", "window_end": "2025-09", "dates": ["2019-10-31", "2019-11-29", "2019-12-31"],
        "calibration_rule": "each initialisation date is calibrated on data up to that date only", "pit_rule": "(i + 1) / (N + 2)",
        "statistic": "Anderson-Darling W^2", "paths_per_date": 2000, "book_horizons": book,
        "risk_factor": {"proxy_tenor_years": 0.25, "horizons": rf}, "sub_windows": subs,
    }


def label(en: str, es: str) -> dict:
    return txt(en, es)


def variant(name: str) -> dict:
    multi = name != "single-swap"
    trades = TRADES if multi else TRADES[:1]
    single = {t[0]: single_ee(40_000.0 * SHAPES[t[0]], t[4]) for t in TRADES}
    summed = [sum(single[t[0]][k] for t in trades) for k in range(len(GRID))]
    netted = [x * (0.7 if multi else 1.0) for x in summed]
    mpor = {"csa-mpor-10d": 10, "csa-mpor-20d": 20, "with-im": 10}.get(name)
    factor = {"csa-mpor-10d": 0.25, "csa-mpor-20d": 0.35, "with-im": 0.25}.get(name, 1.0)
    ee_vm = [x * factor for x in netted]
    dim = [x * 0.6 for x in ee_vm]
    ee = [max(a - b, 0.0) for a, b in zip(ee_vm, dim)] if name == "with-im" else ee_vm
    eff = sm.effective_ee(ee)
    eepe_v = sm.eepe(GRID, eff)
    ee_d = [e * df for e, df in zip(ee, DF)]
    ene = [e * 0.8 for e in ee]
    ene_d = [e * df for e, df in zip(ene, DF)]
    basis = {"with-im": "collateralised-vm-im"}.get(name, "collateralised-vm" if mpor else "uncollateralised")
    exposure = {
        "basis": basis, "time_grid_years": GRID, "ee": prof(ee), "ee_discounted": prof(ee_d), "ene": prof(ene),
        "ene_discounted": prof(ene_d), "pfe_quantile": 0.95, "pfe": prof([e * 3.0 for e in ee]), "effective_ee": prof(eff),
        "epe": msd(sum(e * (t - p) for e, t, p in zip(ee, GRID, [0.0] + GRID[:-1])) / GRID[-1], 15.0),
        "eepe": msd(eepe_v, 20.0), "eepe_horizon_years": 1.0,
        "measure_note": txt("EE and ENE are undiscounted (Basel style); the discounted profiles feed the CVA.",
                            "EE y ENE no estan descontados (estilo Basilea); los perfiles descontados alimentan el CVA."),
    }
    netting = {
        "per_trade_ee": [{"trade_id": t[0], "ee": prof(single[t[0]])} for t in trades], "sum_of_single_trade_ee": prof(summed),
        "netted_ee": prof(netted), "benefit": prof([a - b for a, b in zip(summed, netted)]),
    }
    collateral = None
    if mpor:
        collateral = {
            "csa": {"threshold": money(0.0), "minimum_transfer_amount": money(10_000.0), "independent_amount": money(0.0),
                    "mpor_business_days": mpor, "remargining_days": 1, "closeout": "sticky-date close-out grid (ORE, R3)",
                    "floor_reference": "CRE53.24: 10 business days floor, 20 for illiquid or large netting sets"},
            "uncollateralised_ee": prof(netted), "collateral_balance": prof([a - b for a, b in zip(netted, ee_vm)]),
            "limit": label("The Andersen, Pykhtin and Sokol timelines are not modelled.",
                           "No se modelan las cronologias de Andersen, Pykhtin y Sokol."),
        }
    im = None
    if name == "with-im":
        im = {"method": "ORE dynamic initial margin by regression (R2)", "labelled": "regression proxy, not SIMM", "simm_used": False,
              "quantile": 0.99, "alpha": sm.PHI_INV(0.99), "horizon_calendar_days": 14, "mpor_calendar_days": 14,
              "regression_order": 2, "dim": prof(dim),
              "ee_vm_only": prof(ee_vm),
              "limit": label("A regression proxy, never SIMM; compared with ORE's DIM on the same netting set.",
                             "Un proxy de regresion, nunca SIMM; se compara con el DIM de ORE sobre el mismo conjunto.")}
    # CVA
    buckets, tc, td = [], 0.0, 0.0
    for (t0, t1), e, n_ in zip(zip([0.0] + GRID[:-1], GRID), ee_d, ene_d):
        s0, s1 = math.exp(-SPREAD * t0 / LGD), math.exp(-SPREAD * t1 / LGD)
        b0, b1 = math.exp(-BANK_SPREAD * t0 / BANK_LGD), math.exp(-BANK_SPREAD * t1 / BANK_LGD)
        pd, pdb = s0 - s1, b0 - b1
        ct, dtm = pd * LGD * e, pdb * BANK_LGD * n_
        tc, td = tc + ct, td + dtm
        buckets.append({"t_start": t0, "t_end": t1, "spread": SPREAD, "survival": r(s1), "pd_counterparty": r(pd),
                        "pd_bank": r(pdb), "epe_discounted": r(e, 6), "ene_discounted": r(n_, 6), "cva_term": r(ct, 9),
                        "dva_term": r(dtm, 9)})
    cva = {"credit_curve_source": "synthetic-flat", "credit_curve_label": "proxy: an AAA to A market spread, a floor for lower ratings (R10)",
           "survival_formula": "S(t) = exp(-s t / LGD)",
           "negative_spread_rule": "a negative HQM-minus-Treasury spread is set to zero and counted in spreads_floored_at_zero",
           "spreads_floored_at_zero": 0, "lgd": LGD, "bank_lgd": BANK_LGD, "buckets": buckets,
           "cva": msd(sum(b["cva_term"] for b in buckets), 0.5), "dva": msd(sum(b["dva_term"] for b in buckets), 0.4),
           "bcva": money(sum(b["cva_term"] for b in buckets) - sum(b["dva_term"] for b in buckets))}
    wwr = None
    if name == "wrong-way-risk":
        grid_b = WWR_GRID
        base = cva["cva"]["amount"]
        w_max = r(max(e * 3.0 for e in ee) / 1e6, 6)  # the PFE-scale value of the book in USD million, a fixture stand-in
        wwr = {"model": "Hull and White (2012) hazard rate on the portfolio value, h(t) = exp(a(t) + b w(t))",
               "b_unit": "per USD million of portfolio value", "b_grid": grid_b, "w_max_usd_million": w_max,
               "largest_b_w": r(max(abs(b) for b in grid_b) * w_max, 6),
               "sweep": [{"b": b, "cva": msd(base * (1 + 0.1 * b), 0.5), "independent": b == 0, "a_calibration_max_error": 1e-12}
                         for b in grid_b],
               "independent_cva": money(base),
               "ore_limit": label("ORE's wrong-way example is a different model (a correlated credit LGM): no ORE reconciliation.",
                                  "El ejemplo de ORE usa otro modelo (un LGM de credito correlacionado): sin conciliacion con ORE.")}
    v, c = (80_000.0, 0.0) if mpor is None else (80_000.0, 60_000.0)
    sa = sa_block(trades, mpor, v, c, 0.0, 10_000.0, 0.0)
    ead = sa["ead"]["amount"]
    m = max(t[4] for t in trades)
    df = sm.ba_cva_df(m)
    s_cva = sm.scva(0.05, ead, m, df)
    ba = {"paragraph": "MAR50.14 to MAR50.16", "in_force_date": "2023-01-01", "imm_bank": False, "ds": 0.65, "rho": 0.5, "alpha": 1.4,
          "counterparties": [{"counterparty_id": "CPTY-1", "sector": "financials", "rating_class": "investment-grade",
                              "risk_weight": 0.05, "ead": money(ead), "m_years": m, "discount_factor": r(df), "scva": r(s_cva, 9)}],
          "k_reduced": r(sm.k_reduced([r(s_cva, 9)]), 9), "capital": money(0.65 * r(sm.k_reduced([r(s_cva, 9)]), 9)),
          "limit": label("No official numeric example is verified; the tests rest on the invariants of dossier 01 M.1.",
                         "No hay ejemplo numerico oficial verificado; las pruebas se apoyan en los invariantes.")}
    reg = {"alpha": 1.4, "alpha_paragraph": "CRE53.14", "effective_maturity_years": 3.2, "alpha_times_eepe": money(1.4 * eepe_v),
           "sa_ccr_ead": money(ead), "sa_ccr_over_alpha_eepe": r(ead / (1.4 * eepe_v)),
           "stressed": {"window_start": "2007-01-01", "window_end": "2009-12-31", "label": "convention",
                        "effective_epe": money(eepe_v * 1.3), "hqm_spread_start": 0.0063, "hqm_spread_peak": 0.0310,
                        "spread_rose": True, "paragraph": "CRE53.7 and CRE53.51"}}
    sens = []
    cal = calibration_block(CURVE_DATE, "2019-12-30")
    ee_p = prof(ee)
    pfe_p = prof([e * 3.0 for e in ee])
    for case, a, s in (("base", 0.08, 0.011), ("a-plus-1se", 0.10, 0.011), ("a-minus-1se", 0.06, 0.011),
                       ("sigma-plus-1se", 0.08, 0.0115), ("sigma-minus-1se", 0.08, 0.0105)):
        f = 1 + 20 * (s - 0.011) - 0.3 * (a - 0.08)
        ee_c = prof([v * f for v in ee_p["values"]])
        pfe_c = prof([v * f for v in pfe_p["values"]])
        sens.append({"case": case, "a": a, "sigma": s, "eepe": money(sm.eepe(GRID, sm.effective_ee(ee_c["values"]))),
                     "pfe_peak": money(max(pfe_c["values"])), "ee": ee_c, "pfe": pfe_c})
    if name != "wrong-way-risk":
        ore_ee = prof([x * 1.004 for x in ee_p["values"]])
        ore_ee_d = prof([x * 1.004 for x in ee_d])
        agree = [{"t": t, "difference": r(o - e, 6), "combined_se": r(abs(e) * 0.014 + 1e-6, 6), "within_two_se": True}
                 for t, o, e in zip(GRID, ore_ee["values"], ee_p["values"])]
        ore_eepe = sm.eepe(GRID, sm.effective_ee(ore_ee["values"]))
        ore_cva = sm.cva_from(buckets, ore_ee_d["values"], LGD)
        py_cva = cva["cva"]["amount"]

        def scalar(py: float, orev: float) -> dict:
            return {"python": r(py, 6), "ore": r(orev, 6), "difference": r(orev - py, 6), "combined_se": r(abs(py) * 0.014 + 1e-6, 6),
                    "within_two_se": True}

        ore_dim, dim_agree = None, None
        if name == "with-im":
            ore_dim = prof([x * 1.004 for x in prof(dim)["values"]])
            dim_agree = [{"t": t, "difference": r(o - e, 6), "combined_se": r(abs(e) * 0.014 + 1e-6, 6), "within_two_se": True}
                         for t, o, e in zip(GRID, ore_dim["values"], prof(dim)["values"])]
        ore = {"status": "reconciled", "ore_version": "1.8.17.0", "platform": "fixture: not an ORE run", "run_seconds": 0.0,
               "ore_ee": ore_ee, "ore_ee_discounted": ore_ee_d, "ore_eepe": money(ore_eepe), "ore_cva": money(ore_cva),
               "ore_dim": ore_dim, "agreement": agree, "eepe_agreement": scalar(exposure["eepe"]["amount"], ore_eepe),
               "cva_agreement": scalar(py_cva, ore_cva), "dim_agreement": dim_agree, "all_within_two_se": True, "reason": None}
    else:
        ore = {"status": "not-applicable", "ore_version": None, "platform": None, "run_seconds": None, "ore_ee": None,
               "ore_ee_discounted": None, "ore_eepe": None, "ore_cva": None, "ore_dim": None, "agreement": None,
               "eepe_agreement": None, "cva_agreement": None, "dim_agreement": None, "all_within_two_se": None,
               "reason": label("ORE's wrong-way example is a different model, so this variant has no reconciliation.",
                               "El ejemplo de ORE usa otro modelo, asi que esta variante no tiene conciliacion.")}
    outputs = {
        "kind": "swap-exposure", "variant": name,
        "sign_convention": {"ee": "positive-exposure-to-the-counterparty", "ene": "bank-own-exposure-reported-positive",
                            "cva": "positive-is-cost", "dva": "positive-is-benefit",
                            "statement": txt("EE is the positive exposure to the counterparty, ENE the bank's own, CVA a positive cost.",
                                             "EE es la exposicion positiva a la contraparte, ENE la propia del banco, CVA un costo positivo.")},
        "units": {"money": "amount with its ISO 4217 currency code, USD in this case", "rate": "decimal", "compounding": "continuous",
                  "time": "years-from-the-valuation-date", "mpor": "business-days", "dates": "ISO-8601"},
        "named_parameters": named(), "book": {"netting_set_id": "NS-1", "currency": USD, "trades": [trade_block(t) for t in trades]},
        "curve": curve_block(), "calibration_used": cal, "exposure": exposure, "netting_benefit": netting,
        "collateral": collateral, "initial_margin": im, "cva_dva": cva, "wrong_way_risk": wwr, "sa_ccr": sa, "ba_cva": ba,
        "regulatory_comparison": reg, "girr": girr_block(), "backtest": backtest_block(), "calibration_sensitivity": sens,
        "ore_reconciliation": ore,
    }
    return {
        "schema": "contraste.case/v1", "case_id": "C12", "variant_id": f"fixture-{name}",
        "model": [model_summary("hw1f-exposure", "hw1f")], "outputs": outputs,
        "tests": [test_row("ccr.ee_analytic_vs_simulated", "hw1f-exposure"), test_row("ccr.cva_recomputed", "hw1f-exposure")],
        "impact": {}, "findings": [], "provenance": provenance(), "lane": lane(),
    }


def models_doc() -> dict:
    cals = [calibration_block("2018-12-31", "2018-12-28", 0.07, 0.0105), calibration_block(CURVE_DATE, "2019-12-30")]
    return {
        "schema": "contraste.models/v1", "case_id": "C12", "fit_id": "fixture-hw1f-2018-2019",
        "model": [dict(model_summary("hw1f-exposure", "hw1f"), details={})],
        "fit": {
            "estimator": label("exact AR(1) OLS on the shortest Treasury zero rate (Brigo et al., arXiv 0812.4210, equations 55 to 57)",
                               "AR(1) exacto por MCO sobre la tasa cero más corta del Tesoro (Brigo et al., arXiv 0812.4210, ecuaciones "
                               "55 a 57)"),
            "calibrations": cals, "min_history_years": 3,
            "closed_forms_source": "QuantLib 1.44: hullwhite.hpp, hullwhite.cpp, jamshidianswaptionengine.cpp",
            "closed_forms_status": "formulas transcribed from the engine source; the journal derivations are UNVERIFIED as papers",
            "credit_curve": {
                "base": "US Treasury HQM corporate spot curve minus the Treasury zero curve of the same date", "label": "proxy",
                "derivation": label("HQM spot minus the Treasury zero at the same maturity; an AAA to A market average.",
                                    "Spot HQM menos el cero del Tesoro al mismo plazo; un promedio de mercado AAA a A."),
                "source_url": "https://home.treasury.gov/data/treasury-coupon-issues-and-corporate-bond-yield-curve/corporate-bond-yield-curve",
                "licence_class": "mirror-allowed with citation",
                "licence_basis": label("FRED tags the series Public Domain: Citation Requested; the Treasury-side sentence is UNVERIFIED.",
                                       "FRED etiqueta la serie como dominio publico con cita; la frase del Tesoro no esta verificada."),
                "negative_spread_rule": "a negative HQM-minus-Treasury spread is set to zero and counted, never carried as a negative spread",
                "synthetic_spread": conv(SPREAD, "decimal per year"),
            },
            "girr_parameters": {
                "paragraph": "MAR21.42 to MAR21.50, MAR21.99", "in_force_date": "2023-01-01", "tenors_years": sc.GIRR_TENORS,
                "risk_weights": sc.GIRR_RW, "correlation_percent": sc.GIRR_CORR, "same_tenor_other_curve": 0.999,
                "gamma_between_buckets": 0.5, "curvature_shock": 0.017, "sqrt2_divisor": math.sqrt(2),
                "sqrt2_applies_to": "USD, a specified currency (MAR21.44 footnote 12)",
                "vega": {"liquidity_horizon_days": 60, "risk_weight": 1.0, "correlation_alpha": 0.01,
                         "footnote_24_formula": "not transcribed (UNVERIFIED)"},
            },
            "limits": [label("Andersen, Pykhtin and Sokol timelines are not modelled.", "No se modelan las cronologias de APS."),
                       label("The Hull-White journal derivations are UNVERIFIED as papers.", "Las derivaciones originales no estan verificadas.")],
        },
        "provenance": provenance(), "lane": lane(),
    }


# ------------------------------------------------------------------------------------------------------- regulatory

K = "USD thousands"


def V(name: str, symbol: str, value, unit: str, para: str, basis: str = "transcribed") -> dict:
    return {"name": name, "symbol": symbol, "value": value, "unit": unit, "basis": basis, "paragraph": para}


def P(name: str, value: float, unit: str, rounding: str, para: str) -> dict:
    return {"name": name, "value": value, "unit": unit, "rounding": rounding, "paragraph": para}


def official(eid, calc, title, para, rng, inforce, pub, source, trades, ins, outs, published) -> dict:
    return {"id": eid, "calculator": calc, "title": title, "kind": "official-example", "paragraph": para, "paragraph_range": rng,
            "in_force_date": inforce, "published_date": pub, "source": source, "trades": trades, "inputs": ins, "outputs": outs,
            "published": published, "statement": None, "holds": None, "tolerance_relative": 1e-9}


def invariant(eid, calc, title, para, rng, inforce, pub, source, ins, outs, en, es) -> dict:
    return {"id": eid, "calculator": calc, "title": title, "kind": "invariant", "paragraph": para, "paragraph_range": rng,
            "in_force_date": inforce, "published_date": pub, "source": source, "trades": [], "inputs": ins, "outputs": outs,
            "published": [], "statement": txt(en, es), "holds": True, "tolerance_relative": 1e-9}


def T(trade_id: str, nature: str, para: str, terms: list[tuple]) -> dict:
    """terms: (name, value, unit, paragraph)."""
    return {"trade_id": trade_id, "nature": nature, "paragraph": para,
            "terms": [V(n, n, v, u, pp) for n, v, u, pp in terms]}


def ir_trade(tid, nature, ccy, notional, start, end, position, mv, para, spara, extra=()):
    return T(tid, nature, para, [
        ("asset_class", "interest-rate", "text", para), ("currency", ccy, "ISO 4217", para), ("notional", notional, K, para),
        ("start_years", start, "years", spara), ("end_years", end, "years", spara), ("position", position, "text", para),
        ("option_type", "none", "text", para), ("market_value", mv, K, para), *extra])


def credit_trade(tid, nature, entity, kind, rating, ccy, notional, end, position, mv, para):
    return T(tid, nature, para, [
        ("asset_class", "credit", "text", para), ("entity", entity, "text", para), ("reference_kind", kind, "text", para),
        ("rating", rating, "text", para), ("currency", ccy, "ISO 4217", para), ("notional", notional, K, para),
        ("start_years", 0, "years", "CRE99.47"), ("end_years", end, "years", para), ("position", position, "text", para),
        ("market_value", mv, K, para)])


def com_trade(tid, nature, hs, ctype, notional, maturity, position, mv, para):
    return T(tid, nature, para, [
        ("asset_class", "commodity", "text", para), ("hedging_set", hs, "text", "CRE99.67"), ("commodity_type", ctype, "text", "CRE99.68"),
        ("notional", notional, K, para), ("adjusted_notional", notional, K, "CRE99.64"), ("maturity_years", maturity, "years", para),
        ("position", position, "text", para), ("market_value", mv, K, para)])


def ns1_trades(prefix: str = "") -> list[dict]:
    return [
        ir_trade(prefix + "T1", "Interest rate swap", "USD", 10000, 0, 10, "pay-fixed-receive-floating", 30, "CRE99.22", "CRE99.29"),
        ir_trade(prefix + "T2", "Interest rate swap", "USD", 10000, 0, 4, "pay-floating-receive-fixed", -20, "CRE99.22", "CRE99.29"),
        {**ir_trade(prefix + "T3", "European swaption (1 into 10 years)", "EUR", 5000, 1, 11, "pay-floating-receive-fixed", 50,
                    "CRE99.22", "CRE99.29"),
         "terms": [v for v in ir_trade(prefix + "T3", "", "EUR", 5000, 1, 11, "pay-floating-receive-fixed", 50, "CRE99.22",
                                       "CRE99.29")["terms"] if v["name"] != "option_type"] + [
             V("option_type", "option_type", "bought-put", "text", "CRE99.31"), V("option_price", "P", 0.06, "decimal", "CRE99.31"),
             V("option_strike", "K", 0.05, "decimal", "CRE99.31"), V("option_volatility", "sigma", 0.5, "decimal", "CRE99.31"),
             V("option_expiry_years", "T", 1, "years", "CRE99.31")]},
    ]


def ns2_trades(prefix: str = "") -> list[dict]:
    return [
        credit_trade(prefix + "T1", "Single-name CDS", "Firm A", "single-name", "AA", "USD", 10000, 3, "protection-buyer", 20, "CRE99.41"),
        credit_trade(prefix + "T2", "Single-name CDS", "Firm B", "single-name", "BBB", "EUR", 10000, 6, "protection-seller", -40, "CRE99.41"),
        credit_trade(prefix + "T3", "CDS index", "CDX.IG 5y", "index", "IG", "USD", 10000, 5, "protection-buyer", 0, "CRE99.41"),
    ]


def ns3_trades(prefix: str = "") -> list[dict]:
    return [
        com_trade(prefix + "T1", "Forward, WTI crude oil", "energy", "crude-oil", 10000, 0.75, "long", -50, "CRE99.59"),
        com_trade(prefix + "T2", "Forward, Brent crude oil", "energy", "crude-oil", 20000, 2, "short", -30, "CRE99.59"),
        com_trade(prefix + "T3", "Forward, silver", "metals", "silver", 10000, 5, "long", 100, "CRE99.59"),
    ]


def sa_outputs(trades: list[dict], c, mpor, th, mta, nica, names: list[str], paras: dict) -> list[dict]:
    got = sm.sa_ccr_from_trades(trades, c, mpor, th, mta, nica)
    unit = {"maturity_factor": "unitless", "multiplier": "unitless", "swaption_delta": "unitless"}
    return [V(n, n, got[n], unit.get(n, K), paras.get(n, "CRE52.25"), "recomputed") for n in names]


def regulatory_doc() -> dict:
    src = "BIS CRE99.20 to CRE99.97 (trade inputs) and dossier 01 E.2 (printed intermediates)"
    u, pub = "2023-01-01", "2020-06-05"
    para = {"rc": "CRE52.10", "multiplier": "CRE52.23", "addon_aggregate": "CRE52.25", "pfe": "CRE52.20", "ead": "CRE52.1",
            "en_usd": "CRE52.57", "en_eur": "CRE52.57", "addon_usd": "CRE52.57", "addon_eur": "CRE52.57", "addon_ir": "CRE52.57",
            "swaption_delta": "CRE52.38", "term_1": "CRE52.61", "term_2": "CRE52.61", "addon_credit": "CRE52.61",
            "addon_energy": "CRE52.70", "addon_metals": "CRE52.70", "addon_commodity": "CRE52.70", "maturity_factor": "CRE52.52"}
    n4 = ns1_trades("NS1-") + ns2_trades("NS2-")
    n5 = ns1_trades("NS1-") + ns3_trades("NS3-")
    for t, para4 in ((n4, "CRE99.77"), (n5, "CRE99.80")):
        for tr in t:
            tr["paragraph"] = para4

    def out(trades, c, mpor, th, mta, nica, names):
        return sa_outputs(trades, c, mpor, th, mta, nica, names, para)

    ex = [
        official("cre99-netting-set-1", "sa-ccr", txt("CRE99 netting set 1: interest rate swaps and a swaption, unmargined",
                                                      "CRE99 conjunto 1: swaps de tasa y una swaption, sin margen"),
                 "CRE52.1", "CRE52.10 to CRE52.57", u, pub, src, ns1_trades(),
                 [V("v", "V", 60, K, "CRE99.24"), V("c", "C", 0, K, "CRE99.23")],
                 out(ns1_trades(), 0, None, 0, 0, 0, ["rc", "en_usd", "en_eur", "addon_usd", "addon_eur", "addon_ir", "addon_aggregate",
                                                      "swaption_delta", "multiplier", "pfe", "ead"]),
                 [P("rc", 60, K, "nearest integer", "CRE52.10"), P("en_usd", 59270, K, "nearest integer", "CRE52.57"),
                  P("en_eur", 10083, K, "nearest integer", "CRE52.57"), P("addon_ir", 347, K, "nearest integer", "CRE52.57"),
                  P("addon_aggregate", 347, K, "nearest integer", "CRE52.25"),
                  P("swaption_delta", -0.2694, "unitless", "4 decimal places", "CRE99.32"),
                  P("multiplier", 1.0, "unitless", "none", "CRE52.23"), P("ead", 569, K, "nearest integer", "CRE52.1")]),
        official("cre99-netting-set-2", "sa-ccr", txt("CRE99 netting set 2: credit derivatives, unmargined", "CRE99 conjunto 2: derivados de credito, sin margen"),
                 "CRE52.1", "CRE52.61 to CRE52.65", u, pub, src, ns2_trades(),
                 [V("v", "V", -20, K, "CRE99.43"), V("c", "C", 0, K, "CRE99.42")],
                 out(ns2_trades(), 0, None, 0, 0, 0, ["rc", "term_1", "term_2", "addon_credit", "addon_aggregate", "multiplier", "pfe", "ead"]),
                 [P("rc", 0, K, "nearest integer", "CRE52.10"), P("term_1", 2253, K, "nearest integer", "CRE52.61"),
                  P("term_2", 77344, K, "nearest integer", "CRE52.61"), P("addon_credit", 282, K, "nearest integer", "CRE52.61"),
                  P("addon_aggregate", 282, K, "nearest integer", "CRE52.25"),
                  P("multiplier", 0.965, "unitless", "3 decimal places", "CRE52.23"), P("ead", 381, K, "nearest integer", "CRE52.1")]),
        official("cre99-netting-set-3", "sa-ccr", txt("CRE99 netting set 3: commodity forwards and swaps", "CRE99 conjunto 3: forwards y swaps de commodities"),
                 "CRE52.1", "CRE52.70 to CRE52.71", u, pub, src, ns3_trades(),
                 [V("v", "V", 20, K, "CRE99.60"), V("c", "C", 0, K, "CRE99.60")],
                 out(ns3_trades(), 0, None, 0, 0, 0, ["rc", "addon_energy", "addon_metals", "addon_commodity", "addon_aggregate",
                                                      "multiplier", "pfe", "ead"]),
                 [P("rc", 20, K, "nearest integer", "CRE52.10"), P("addon_energy", 2041, K, "nearest integer", "CRE52.70"),
                  P("addon_metals", 1800, K, "nearest integer", "CRE52.70"), P("addon_commodity", 3841, K, "nearest integer", "CRE52.70"),
                  P("addon_aggregate", 3841, K, "nearest integer", "CRE52.25"), P("multiplier", 1.0, "unitless", "none", "CRE52.23"),
                  P("ead", 5406, K, "nearest integer", "CRE52.1")]),
        official("cre99-netting-set-4", "sa-ccr", txt("CRE99 netting set 4: netting sets 1 and 2 combined", "CRE99 conjunto 4: conjuntos 1 y 2 combinados"),
                 "CRE52.1", "CRE52.24 to CRE52.25", u, pub, src, n4,
                 [V("v", "V", 40, K, "CRE99.77"), V("c", "C", 0, K, "CRE99.77")],
                 out(n4, 0, None, 0, 0, 0, ["rc", "addon_ir", "addon_credit", "addon_aggregate", "multiplier", "pfe", "ead"]),
                 [P("rc", 40, K, "nearest integer", "CRE52.10"), P("addon_ir", 347, K, "nearest integer", "CRE52.57"),
                  P("addon_credit", 282, K, "nearest integer", "CRE52.61"), P("addon_aggregate", 629, K, "nearest integer", "CRE52.25"),
                  P("multiplier", 1.0, "unitless", "none", "CRE52.23"), P("ead", 936, K, "nearest integer", "CRE52.1")]),
        official("cre99-netting-set-5", "sa-ccr", txt("CRE99 netting set 5: margined interest rate and commodity", "CRE99 conjunto 5: tasas y commodities con margen"),
                 "CRE52.1", "CRE52.18 to CRE52.52", u, pub, src, n5,
                 [V("v", "V", 80, K, "CRE99.82"), V("c", "C", 200, K, "CRE99.80"), V("th", "TH", 0, K, "CRE99.80"),
                  V("mta", "MTA", 5, K, "CRE99.80"), V("nica", "NICA", 150, K, "CRE99.82"),
                  V("margin_frequency_business_days", "N", 5, "business days", "CRE99.83"),
                  V("mpor_business_days", "MPOR", 14, "business days", "CRE99.83")],
                 out(n5, 200, 14, 0, 5, 150, ["rc", "maturity_factor", "addon_ir", "addon_commodity", "addon_aggregate", "multiplier",
                                              "pfe", "ead"]),
                 [P("rc", 0, K, "nearest integer", "CRE52.18"), P("addon_ir", 123, K, "nearest integer", "CRE52.57"),
                  P("addon_commodity", 1278, K, "nearest integer", "CRE52.70"), P("addon_aggregate", 1401, K, "nearest integer", "CRE52.25"),
                  P("multiplier", 0.958, "unitless", "3 decimal places", "CRE52.23"), P("ead", 1879, K, "nearest integer", "CRE52.1")]),
        official("rbc20-13-output-floor", "output-floor", txt("RBC20.13 output floor", "RBC20.13 piso de salida"), "RBC20.4",
                 "RBC20.4 and RBC20.11 to RBC20.13", u, "2020-11-26", "dossier 01 C.1 and M.1", [],
                 [V("rwa_nominated", "RWA", 76, "index points", "RBC20.13"), V("rwa_sa_only", "RWA_SA", 140, "index points", "RBC20.13"),
                  V("floor_factor", "f", 0.725, "decimal", "RBC90.1")],
                 [V("rwa_floored", "RWA_floor", 101.5, "index points", "RBC20.4")], [P("rwa_floored", 101.5, "index points", "none", "RBC20.13")]),
        official("rbc20-13-output-floor-capped", "output-floor", txt("RBC20.13 output floor with the RBC90.2 cap", "RBC20.13 piso con el tope RBC90.2"),
                 "RBC90.2", "RBC90.1 to RBC90.2", u, "2020-03-27", "dossier 01 C.1 and M.1", [],
                 [V("rwa_nominated", "RWA", 76, "index points", "RBC20.13"), V("rwa_sa_only", "RWA_SA", 140, "index points", "RBC20.13"),
                  V("floor_factor", "f", 0.725, "decimal", "RBC90.1"), V("cap_share", "cap", 0.25, "decimal of pre-floor RWA", "RBC90.2")],
                 [V("rwa_floored", "RWA_floor", 95, "index points", "RBC90.2")], [P("rwa_floored", 95, "index points", "none", "RBC90.2")]),
    ]
    inv = invariants(u)
    return {
        "schema": "contraste.regulatory/v1", "case_id": "REGULATORY", "document_id": "fixture-regulatory-calculators",
        "engine": {"name": "riskvalidation", "version": "fixture"},
        "units": {"money": "as stated per value (USD thousands for CRE99, index points for RBC20.13)", "rate": "decimal", "dates": "ISO-8601"},
        "official_examples": ex, "invariant_cases": inv, "output_floor_phase_in": phase_in(), "parameter_tables": parameter_tables(),
        "cre20_grid": cre20_grid(), "provenance": provenance(), "lane": lane(),
    }


def invariants(u: str) -> list[dict]:
    c = "constructed"
    out: list[dict] = []
    out.append(invariant(
        "ba-cva-rho-one", "ba-cva", txt("BA-CVA reduced with rho = 1 gives the sum of SCVA", "BA-CVA reducido con rho = 1 da la suma de SCVA"),
        "MAR50.14", "MAR50.14 to MAR50.16", u, "2020-07-08", "dossier 01 E.1 and M.1 (inputs constructed by the fixture)",
        [V("scva_1", "SCVA_1", 10, "USD", "MAR50.15", c), V("scva_2", "SCVA_2", 20, "USD", "MAR50.15", c), V("rho", "rho", 1.0, "decimal", "MAR50.14", c)],
        [V("k_reduced", "K_reduced", 30, "USD", "MAR50.14", "recomputed")],
        "With rho = 1 the reduced capital base K_reduced equals the sum of the SCVA.",
        "Con rho = 1 la base K_reduced es igual a la suma de los SCVA."))
    out.append(invariant(
        "ba-cva-hedges-floor", "ba-cva", txt("Hedges never take K_full below beta K_reduced", "Las coberturas nunca bajan K_full de beta K_reduced"),
        "MAR50.20", "MAR50.20 to MAR50.25", u, "2020-07-08", "dossier 01 E.1 and M.1 (inputs constructed by the fixture)",
        [V("k_reduced", "K_reduced", 30, "USD", "MAR50.14", c), V("k_hedged", "K_hedged", 0, "USD", "MAR50.21", c), V("beta", "beta", 0.25, "decimal", "MAR50.20")],
        [V("k_full", "K_full", 7.5, "USD", "MAR50.20", "recomputed")],
        "K_full = beta K_reduced + (1 - beta) K_hedged is at least beta K_reduced.",
        "K_full = beta K_reduced + (1 - beta) K_hedged es al menos beta K_reduced."))
    out.append(invariant(
        "sbm-low-and-high-scenarios", "frtb-sbm", txt("SBM correlation scenarios", "Escenarios de correlacion SBM"), "MAR21.6",
        "MAR21.6 to MAR21.7", u, "2026-03-23", "dossier 01 D.2 and M.1 (input constructed by the fixture)",
        [V("rho", "rho", 0.5, "decimal", "MAR21.6", c)],
        [V("rho_low", "rho_low", 0.375, "decimal", "MAR21.6", "recomputed"), V("rho_medium", "rho_medium", 0.5, "decimal", "MAR21.6", "recomputed"),
         V("rho_high", "rho_high", 0.625, "decimal", "MAR21.6", "recomputed")],
        "The low scenario uses max(2 rho - 1, 0.75 rho) and the high scenario min(1.25 rho, 1); the SBM result is the maximum of the three.",
        "El escenario bajo usa max(2 rho - 1, 0.75 rho) y el alto min(1.25 rho, 1); el resultado SBM es el maximo de los tres."))
    out.append(sbm_case(
        "sbm-bucket-and-cross-bucket-aggregation", txt("SBM aggregation: within bucket, across buckets, maximum over the scenarios",
                                                       "Agregacion SBM: dentro del bucket, entre buckets y maximo de los escenarios"),
        [10.0, -4.0, 6.0], [1, .5, .2, .5, 1, .5, .2, .5, 1], [5.0, 3.0], [1, .5, .5, 1], 0.5, u,
        "Two buckets with their within-bucket correlations and gamma 0.5: the bucket charge K_b of MAR21.4 under each of the three "
        "scenarios of MAR21.6, the cross-bucket charge and the maximum over the scenarios (MAR21.7).",
        "Dos buckets con sus correlaciones internas y gamma 0.5: el cargo K_b de MAR21.4 bajo cada escenario de MAR21.6, el cargo entre "
        "buckets y el maximo de los escenarios (MAR21.7)."))
    out.append(sbm_case(
        "sbm-cross-bucket-fallback", txt("SBM cross-bucket fallback of MAR21.4(5)(b)", "Respaldo entre buckets de MAR21.4(5)(b)"),
        [10.0, 10.0], [1, .5, .5, 1], [-10.0, -10.0], [1, .5, .5, 1], 0.8, u,
        "Two buckets of opposite sign and gamma 0.8: under the medium and high scenarios the radicand is negative and S_b is "
        "replaced by max(min(sum WS, K_b), -K_b) (MAR21.4(5)(b)); under the low scenario the plain path applies.",
        "Dos buckets de signo opuesto y gamma 0.8: bajo los escenarios medio y alto el radicando es negativo y S_b se reemplaza por "
        "max(min(sum WS, K_b), -K_b) (MAR21.4(5)(b)); bajo el bajo se aplica la via simple."))
    out.append(invariant(
        "cascade-all-lh-ten", "frtb-liquidity-cascade", txt("Cascade with every LH equal to 10", "Cascada con todos los LH iguales a 10"), "MAR33.4",
        "MAR33.4 and MAR33.12", u, "2020-06-05", "dossier 01 D.3 and M.1 (input constructed by the fixture)",
        [V("es_t_p", "ES_T(P)", 10, "USD", "MAR33.4", c), V("t", "T", 10, "days", "MAR33.4"), V("lh_1", "LH_1", 10, "days", "MAR33.4")],
        [V("es", "ES", 10, "USD", "MAR33.4", "recomputed")],
        "If every risk factor has a liquidity horizon of 10 days the cascade returns ES_T(P); it is monotone in LH.",
        "Si todo factor tiene horizonte de liquidez de 10 dias la cascada devuelve ES_T(P); es monotona en LH."))
    es = sm.liquidity_cascade(10.0, [6.0], [10.0, 20.0], 10.0)
    out.append(invariant(
        "cascade-two-horizons", "frtb-liquidity-cascade", txt("Cascade with a second liquidity horizon", "Cascada con un segundo horizonte de liquidez"),
        "MAR33.4", "MAR33.4 Table 1 and MAR33.12", u, "2020-06-05", "dossier 01 D.3 and M.1 (inputs constructed by the fixture)",
        [V("es_t_p", "ES_T(P)", 10, "USD", "MAR33.4", c), V("es_t_p_2", "ES_T(P, 2)", 6, "USD", "MAR33.4", c), V("t", "T", 10, "days", "MAR33.4"),
         V("lh_1", "LH_1", 10, "days", "MAR33.4"), V("lh_2", "LH_2", 20, "days", "MAR33.4")],
        [V("es", "ES", es, "USD", "MAR33.4", "recomputed")],
        "ES = sqrt(ES_T(P)^2 + (ES_T(P, 2) sqrt((LH_2 - LH_1) / T))^2) = sqrt(100 + 36 x 1) = 11.661904; it is at least ES_T(P).",
        "ES = sqrt(ES_T(P)^2 + (ES_T(P, 2) sqrt((LH_2 - LH_1) / T))^2) = sqrt(100 + 36 x 1) = 11.661904; es al menos ES_T(P)."))
    return out


def sbm_case(eid, title, ws1, rho1, ws2, rho2, gamma, u, en, es) -> dict:
    c = "constructed"
    ws, rhos = [ws1, ws2], [rho1, rho2]
    ins = [V("ws_1", "WS_1", ws1, "USD", "MAR21.4", c), V("rho_1", "rho_1", [float(x) for x in rho1], "decimal", "MAR21.4", c),
           V("ws_2", "WS_2", ws2, "USD", "MAR21.4", c), V("rho_2", "rho_2", [float(x) for x in rho2], "decimal", "MAR21.4", c),
           V("gamma", "gamma", gamma, "decimal", "MAR21.4", c)]
    outs = []
    charges = {}
    for scn in ("low", "medium", "high"):
        kb = [sm.sbm_bucket(w, [r_[i * len(w):(i + 1) * len(w)] for i in range(len(w))], scn) for w, r_ in zip(ws, rhos)]
        cross, fb = sm.sbm_cross(kb, [sum(w) for w in ws], gamma, scn)
        charges[scn] = cross
        outs += [V(f"k_b{b + 1}_{scn}", f"K_b{b + 1}", k, "USD", "MAR21.4", "recomputed") for b, k in enumerate(kb)]
        outs += [V(f"cross_bucket_{scn}", "SBM_scenario", cross, "USD", "MAR21.4", "recomputed"),
                 V(f"fallback_{scn}", "fallback", float(fb), "flag", "MAR21.4", "recomputed")]
    outs.append(V("sbm_charge", "SBM", max(charges.values()), "USD", "MAR21.7", "recomputed"))
    return invariant(eid, "frtb-sbm", title, "MAR21.4", "MAR21.4 to MAR21.7", u, "2026-03-23",
                     "dossier 01 D.2 and M.1 (inputs constructed by the fixture)", ins, outs, en, es)


def phase_in() -> list[dict]:
    return [{"year": y, "effective_from": f"{y}-01-01", "factor": f, "table": "RBC90.1 Table 1", "paragraph": "RBC90.1",
             "in_force_date": "2023-01-01"} for y, f in sm.PHASE_IN.items()]


def parameter_tables() -> list[dict]:
    u = "2023-01-01"
    t52 = [{"key": k, "parameter": n, "value": v, "unit": "decimal"}
           for k, row in sm.CRE52_72.items() for n, v in zip(("supervisory_factor", "correlation", "option_volatility"), row) if v is not None]
    t50 = [{"key": k, "parameter": n, "value": v, "unit": "decimal"}
           for k, row in sm.BA_CVA_RW.items() for n, v in zip(("risk_weight_investment_grade", "risk_weight_high_yield_or_not_rated"), row)]
    t33_12 = [{"key": k, "parameter": "liquidity_horizon_days", "value": v, "unit": "days"} for k, v in sm.MAR33_12.items()]
    t33_4 = [{"key": k, "parameter": "liquidity_horizon_days", "value": v, "unit": "days"} for k, v in sm.MAR33_4.items()]
    return [
        {"id": "cre52-72-table-2", "title": txt("SA-CCR supervisory parameters", "Parametros supervisores SA-CCR"), "calculator": "sa-ccr",
         "table": "CRE52.72 Table 2", "paragraph": "CRE52.72", "in_force_date": u, "source": "dossier 01 E.2", "rows": t52},
        {"id": "mar50-16-table-1", "title": txt("BA-CVA counterparty risk weights", "Ponderadores de contraparte BA-CVA"), "calculator": "ba-cva",
         "table": "MAR50.16 Table 1", "paragraph": "MAR50.16", "in_force_date": u, "source": "dossier 01 E.1", "rows": t50},
        {"id": "mar33-12-table-2", "title": txt("Liquidity horizons by risk factor", "Horizontes de liquidez por factor de riesgo"),
         "calculator": "frtb-liquidity-cascade", "table": "MAR33.12 Table 2", "paragraph": "MAR33.12", "in_force_date": u,
         "source": "dossier 01 D.3 (the row commodity volatility, 60 or 120 days, is ambiguous there and not transcribed)", "rows": t33_12},
        {"id": "mar33-4-table-1", "title": txt("Liquidity horizons of the cascade", "Horizontes de liquidez de la cascada"),
         "calculator": "frtb-liquidity-cascade", "table": "MAR33.4 Table 1", "paragraph": "MAR33.4", "in_force_date": u,
         "source": "dossier 01 D.3", "rows": t33_4},
    ]


def cre20_grid() -> list[dict]:
    grid: list[dict] = []
    u = "2023-01-01"

    def g(cls, key, band, rw, table, para, short=False, cf=False, cw=None):
        grid.append({"exposure_class": cls, "key": key, "band": band, "short_term": short, "cash_flow_dependent": cf,
                     "counterparty_weight": cw, "risk_weight": rw, "table": table, "paragraph": para, "in_force_date": u})

    ratings = ["AAA to AA-", "A+ to A-", "BBB+ to BBB-", "BB+ to B-", "below B-", "unrated"]
    for key, rw in zip(ratings, [0.0, 0.2, 0.5, 1.0, 1.5, 1.0]):
        g("sovereign", key, key, rw, "CRE20 Table 1", "CRE20.7")
    for score, rw in zip(range(8), [0.0, 0.0, 0.2, 0.5, 1.0, 1.0, 1.0, 1.5]):
        g("eca", str(score), f"score {score}", rw, "CRE20 Table 2", "CRE20.9")
    for key, rw in zip(ratings[:5], [0.2, 0.3, 0.5, 1.0, 1.5]):
        g("bank-ecra", key, key, rw, "CRE20 Table 6", "CRE20.18")
    for key, rw in zip(ratings[:5], [0.2, 0.2, 0.2, 0.5, 1.5]):
        g("bank-ecra", key, key, rw, "CRE20 Table 6", "CRE20.18", short=True)
    for key, rw, rws in zip(["A", "B", "C"], [0.4, 0.75, 1.5], [0.2, 0.5, 1.5]):
        g("bank-scra", key, f"Grade {key}", rw, "CRE20 Table 7", "CRE20.21")
        g("bank-scra", key, f"Grade {key}", rws, "CRE20 Table 7", "CRE20.21", short=True)
    for key, band, rw in zip(["AAA to AA-", "A+ to A-", "BBB+ to BBB-", "BB+ to BB-", "below BB-", "unrated"],
                             ["AAA to AA-", "A+ to A-", "BBB+ to BBB-", "BB+ to BB-", "below BB-", "unrated"], [0.2, 0.5, 0.75, 1.0, 1.5, 1.0]):
        g("corporate", key, band, rw, "CRE20 Table 10", "CRE20.43")
    g("corporate", "investment-grade-unrated", "investment grade where ratings are not allowed", 0.65, "CRE20.44 and CRE20.46", "CRE20.44")
    g("corporate", "sme-unrated", "unrated SME", 0.85, "CRE20.47", "CRE20.47")
    g("corporate", "regulatory-retail-sme", "regulatory retail SME", 0.75, "CRE20.47", "CRE20.47")
    bands = [("0.5", "ltv <= 50%"), ("0.6", "50% < ltv <= 60%"), ("0.8", "60% < ltv <= 80%"), ("0.9", "80% < ltv <= 90%"),
             ("1.0", "90% < ltv <= 100%"), ("1.5", "ltv > 100%")]
    for (key, band), rw in zip(bands, [0.2, 0.25, 0.3, 0.4, 0.5, 0.7]):
        g("residential-re", key, band, rw, "CRE20 Table 11", "CRE20.82")
    for (key, band), rw in zip(bands, [0.3, 0.35, 0.45, 0.6, 0.75, 1.05]):
        g("residential-re", key, band, rw, "CRE20 Table 12", "CRE20.84", cf=True)
    for cw in (0.2, 1.0):
        g("commercial-re", "0.6", "ltv <= 60%", min(0.6, cw), "CRE20 Table 13", "CRE20.85", cw=cw)
        g("commercial-re", "1.0", "ltv > 60%", cw, "CRE20 Table 13", "CRE20.85", cw=cw)
    for (key, band), rw in zip([("0.6", "ltv <= 60%"), ("0.8", "60% < ltv <= 80%"), ("1.0", "ltv > 80%")], [0.7, 0.9, 1.1]):
        g("commercial-re", key, band, rw, "CRE20 Table 14", "CRE20.87", cf=True)
    for key, band, rw in [("regulatory", "regulatory retail", 0.75), ("transactor", "transactors", 0.45), ("other", "other retail", 1.0)]:
        g("retail", key, band, rw, "CRE20.68", "CRE20.68")
    for key, band, rw in [("equity", "equity", 2.5), ("speculative-unlisted", "speculative unlisted equity", 4.0),
                          ("legislated-programme", "legislated programmes", 1.0), ("subordinated-debt", "subordinated debt", 1.5)]:
        g("equity", key, band, rw, "CRE20.57 to CRE20.60", "CRE20.57")
    for key, band, rw in [("provision-below-20pct", "specific provisions below 20%", 1.5),
                          ("provision-at-least-20pct", "specific provisions at least 20%", 1.0),
                          ("residential-non-cash-flow-dependent", "residential not cash-flow dependent", 1.0)]:
        g("defaulted", key, band, rw, "CRE20.104 to CRE20.107", "CRE20.104")
    for key, rw in [("direct-credit-substitute", 1.0), ("repo", 1.0), ("securities-lending", 1.0), ("forward-purchase", 1.0),
                    ("nif-ruf", 0.5), ("transaction-related-contingent", 0.5), ("commitment", 0.4), ("trade-letter-of-credit", 0.2),
                    ("unconditionally-cancellable", 0.1)]:
        g("ccf", key, key, rw, "CRE20.94 to CRE20.101", "CRE20.94")
    g("currency-mismatch", "multiplier", "multiplier on the unhedged weight", 1.5, "CRE20.92", "CRE20.92")
    g("currency-mismatch", "cap", "cap on the adjusted weight", 1.5, "CRE20.92", "CRE20.92")
    return grid


def main() -> None:
    for name in sc.VARIANTS:
        write(f"c12/variant-swap-exposure-{name}-fixture.json", variant(name))
    write("c12/models-fixture.json", models_doc())
    write("regulatory/calculators-fixture.json", regulatory_doc())


if __name__ == "__main__":
    main()
