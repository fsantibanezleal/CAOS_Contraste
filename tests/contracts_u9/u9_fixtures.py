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

GRID = [0.25, 0.5, 1.0, 2.0, 3.0, 5.0]
CURVE_DATE = "2019-12-31"
TRADES = [  # conventions (D6); payer pays the fixed rate
    ("SW-1", 10_000_000.0, 0.040, "payer", 5.0),
    ("SW-2", 6_000_000.0, 0.038, "receiver", 3.0),
    ("SW-3", 4_000_000.0, 0.042, "payer", 5.0),
]
SHAPES = {"SW-1": 1.00, "SW-2": 0.55, "SW-3": 0.45}  # share of the single-swap EE scale, fixture
DF = [math.exp(-0.015 * t) for t in GRID]
LGD, BANK_LGD, SPREAD, BANK_SPREAD = 0.6, 0.6, 0.012, 0.008


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
        "seed": conv(20260101, "integer"), "wwr_b_grid": conv([0.0, 0.01, 0.02, 0.04], "per USD million"),
        "im_quantile": conv(0.99, "decimal"), "im_horizon_days": conv(10, "days"), "im_regression_order": conv(2, "polynomial order"),
        "ba_cva_sector": conv("financials", "MAR50.16 Table 1 sector"), "ba_cva_rating": conv("investment-grade", "class"),
        "stress_window_start": conv("2007-01-01", "date"), "stress_window_end": conv("2009-12-31", "date"),
        "backtest_window_start": conv("2000-01", "month"),
    }
    assert list(vals) == sc.NAMED
    return vals


def trade_block(t) -> dict:
    return {"trade_id": t[0], "notional": money(t[1]), "fixed_rate": t[2], "side": t[3], "start_years": 0.0, "maturity_years": t[4],
            "fixed_frequency_per_year": 2, "floating_leg": "USD floating leg on the single curve of the case", "label": "convention"}


def curve_block() -> dict:
    ten = [0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0]
    par = [0.0154, 0.0155, 0.0155, 0.0158, 0.0162, 0.0169, 0.0178, 0.0186]
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


def single_ee(scale: float = 40_000.0) -> list[float]:
    return [scale * math.sqrt(t) * (1 - t / 6.0) for t in GRID]


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
                     "supervisory_duration": r(sd), "adjusted_notional": money(adj), "delta": "1" if delta > 0 else "-1",
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
    s = [0, 120.0, 260.0, 540.0, -310.0, 880.0, 0.0, 0.0, 0.0, 0.0]  # PV01 in USD per bp at each tenor, fixture
    ws_div = [x * w / math.sqrt(2) for x, w in zip(s, rw)]
    ws = [x * w for x, w in zip(s, rw)]
    ks = {name: sm.sbm_bucket(ws_div, corr, name) for name in ("low", "medium", "high")}
    ku = max(sm.sbm_bucket(ws, corr, name) for name in ("low", "medium", "high"))
    return {
        "paragraph": "MAR21.42 to MAR21.50", "in_force_date": "2023-01-01", "currency": USD, "sqrt2_division": True,
        "sqrt2_label": "convention", "sensitivities_per_bp": s, "weighted_sensitivities": [r(x, 9) for x in ws_div],
        "scenarios": [{"scenario": k, "k_b": r(ks[k], 9)} for k in ("low", "medium", "high")],
        "delta_charge": money(max(ks.values())), "delta_charge_undivided": money(ku),
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
        "statistic": "Anderson-Darling W^2", "paths_per_date": 10000, "book_horizons": book,
        "risk_factor": {"proxy_tenor_years": 0.25, "horizons": rf}, "sub_windows": subs,
    }


def label(en: str, es: str) -> dict:
    return txt(en, es)


def variant(name: str) -> dict:
    multi = name != "single-swap"
    trades = TRADES if multi else TRADES[:1]
    single = {t[0]: single_ee(40_000.0 * SHAPES[t[0]]) for t in TRADES}
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
              "quantile": 0.99, "alpha": 2.33, "horizon_days": 10, "mpor_days": 10, "regression_order": 2, "dim": prof(dim),
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
           "survival_formula": "S(t) = exp(-s t / LGD)", "lgd": LGD, "bank_lgd": BANK_LGD, "buckets": buckets,
           "cva": msd(sum(b["cva_term"] for b in buckets), 0.5), "dva": msd(sum(b["dva_term"] for b in buckets), 0.4),
           "bcva": money(sum(b["cva_term"] for b in buckets) - sum(b["dva_term"] for b in buckets))}
    wwr = None
    if name == "wrong-way-risk":
        grid_b = [0.0, 0.01, 0.02, 0.04]
        base = cva["cva"]["amount"]
        wwr = {"model": "Hull and White (2012) hazard rate on the portfolio value, h(t) = exp(a(t) + b w(t))",
               "b_unit": "per USD million of portfolio value", "b_grid": grid_b,
               "sweep": [{"b": b, "cva": msd(base * (1 + 12 * b), 0.5), "independent": b == 0, "a_calibration_max_error": 1e-12}
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
    for case, a, s in (("base", 0.08, 0.011), ("a-plus-1se", 0.10, 0.011), ("a-minus-1se", 0.06, 0.011),
                       ("sigma-plus-1se", 0.08, 0.0115), ("sigma-minus-1se", 0.08, 0.0105)):
        sens.append({"case": case, "a": a, "sigma": s, "eepe": money(eepe_v * (1 + 20 * (s - 0.011) - 0.3 * (a - 0.08))),
                     "pfe_peak": money(max(e * 3.0 for e in ee) * (1 + 20 * (s - 0.011)))})
    if name in ("single-swap", "netting-set"):
        ore_vals = [x * 1.004 for x in ee]
        agree = [{"t": t, "difference": r(o - e, 6), "combined_se": r(abs(e) * 0.014, 6), "within_two_se": True}
                 for t, o, e in zip(GRID, ore_vals, ee)]
        ore = {"status": "reconciled", "ore_version": "1.8.17.0", "platform": "fixture: not an ORE run", "run_seconds": 0.0,
               "ore_ee": prof(ore_vals), "agreement": agree, "all_within_two_se": True, "reason": None}
    else:
        why = ("ORE's wrong-way example is a different model, so this variant has no reconciliation."
               if name == "wrong-way-risk" else "The ORE run covers the single swap and the netting set only (U9-P1).")
        ore = {"status": "not-applicable", "ore_version": None, "platform": None, "run_seconds": None, "ore_ee": None,
               "agreement": None, "all_within_two_se": None,
               "reason": label(why, "ORE se ejecuta sobre el swap unico y el conjunto de neteo (U9-P1).")}
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
        "tests": [test_row("ccr.ee_analytic_vs_simulated", "hw1f-exposure"), test_row("ccr.cva_recomputed_from_ee", "hw1f-exposure")],
        "impact": {}, "findings": [], "provenance": provenance(), "lane": lane(),
    }


def models_doc() -> dict:
    cals = [calibration_block("2018-12-31", "2018-12-28", 0.07, 0.0105), calibration_block(CURVE_DATE, "2019-12-30")]
    return {
        "schema": "contraste.models/v1", "case_id": "C12", "fit_id": "fixture-hw1f-2018-2019",
        "model": [dict(model_summary("hw1f-exposure", "hw1f"), details={})],
        "fit": {
            "estimator": "exact AR(1) OLS on the shortest Treasury zero rate (Brigo et al., arXiv 0812.4210, equations 55 to 57)",
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


def V(name: str, symbol: str, value: float, unit: str, para: str) -> dict:
    return {"name": name, "symbol": symbol, "value": value, "unit": unit, "paragraph": para}


def P(name: str, value: float, unit: str, rounding: str, para: str) -> dict:
    return {"name": name, "value": value, "unit": unit, "rounding": rounding, "paragraph": para}


def official(eid, calc, title, para, rng, inforce, pub, source, ins, outs, published) -> dict:
    return {"id": eid, "calculator": calc, "title": title, "kind": "official-example", "paragraph": para, "paragraph_range": rng,
            "in_force_date": inforce, "published_date": pub, "source": source, "inputs": ins, "outputs": outs,
            "published": published, "statement": None, "holds": None, "tolerance_relative": 1e-9}


def invariant(eid, calc, title, para, rng, inforce, pub, source, ins, outs, en, es) -> dict:
    return {"id": eid, "calculator": calc, "title": title, "kind": "invariant", "paragraph": para, "paragraph_range": rng,
            "in_force_date": inforce, "published_date": pub, "source": source, "inputs": ins, "outputs": outs, "published": [],
            "statement": txt(en, es), "holds": True, "tolerance_relative": 1e-9}


def regulatory_doc() -> dict:
    K = "USD thousands"
    src = "dossier 01 E.2 (CRE99.20 to CRE99.97)"
    u, pub = "2023-01-01", "2020-06-05"
    ex = [
        official("cre99-netting-set-1", "sa-ccr", txt("CRE99 netting set 1: interest rate swaps and a swaption, unmargined",
                                                      "CRE99 conjunto 1: swaps de tasa y una swaption, sin margen"),
                 "CRE52.1", "CRE52.10 to CRE52.57", u, pub, src,
                 [V("v_trade_1", "V1", 30, K, "CRE99.20"), V("v_trade_2", "V2", -20, K, "CRE99.20"), V("v_trade_3", "V3", 50, K, "CRE99.20"),
                  V("c", "C", 0, K, "CRE52.10")],
                 [V("rc", "RC", 60, K, "CRE52.10"), V("en_usd", "EN_USD", 59270, K, "CRE52.57"), V("en_eur", "EN_EUR", 10083, K, "CRE52.57"),
                  V("addon_usd", "AddOn_USD", 296.35, K, "CRE52.57"), V("addon_eur", "AddOn_EUR", 50.415, K, "CRE52.57"),
                  V("addon_ir", "AddOn_IR", 346.765, K, "CRE52.57"), V("addon_aggregate", "AddOn", 346.765, K, "CRE52.25"),
                  V("swaption_delta", "delta", -0.2694, "unitless", "CRE52.38"), V("multiplier", "multiplier", 1.0, "unitless", "CRE52.23")],
                 [P("ead", 569, K, "nearest integer", "CRE52.1"), P("addon_ir", 347, K, "nearest integer", "CRE52.57")]),
        official("cre99-netting-set-2", "sa-ccr", txt("CRE99 netting set 2: credit derivatives, unmargined", "CRE99 conjunto 2: derivados de credito, sin margen"),
                 "CRE52.1", "CRE52.61 to CRE52.65", u, pub, src,
                 [V("v_minus_c", "V-C", -20, K, "CRE52.23")],
                 [V("rc", "RC", 0, K, "CRE52.10"), V("term_1", "term 1", 2253, K, "CRE52.61"), V("term_2", "term 2", 77344, K, "CRE52.61"),
                  V("addon_credit", "AddOn_credit", 282, K, "CRE52.61"), V("addon_aggregate", "AddOn", 282, K, "CRE52.25"),
                  V("multiplier", "multiplier", 0.965, "unitless", "CRE52.23")],
                 [P("ead", 381, K, "nearest integer", "CRE52.1")]),
        official("cre99-netting-set-3", "sa-ccr", txt("CRE99 netting set 3: commodity forwards and swaps", "CRE99 conjunto 3: forwards y swaps de commodities"),
                 "CRE52.1", "CRE52.70 to CRE52.71", u, pub, src, [V("c", "C", 0, K, "CRE52.10")],
                 [V("rc", "RC", 20, K, "CRE52.10"), V("addon_energy", "AddOn_energy", 2041, K, "CRE52.70"),
                  V("addon_metals", "AddOn_metals", 1800, K, "CRE52.70"), V("addon_aggregate", "AddOn", 3841, K, "CRE52.25"),
                  V("multiplier", "multiplier", 1.0, "unitless", "CRE52.23")], [P("ead", 5406, K, "nearest integer", "CRE52.1")]),
        official("cre99-netting-set-4", "sa-ccr", txt("CRE99 netting set 4: netting sets 1 and 2 combined", "CRE99 conjunto 4: conjuntos 1 y 2 combinados"),
                 "CRE52.1", "CRE52.24 to CRE52.25", u, pub, src, [V("c", "C", 0, K, "CRE52.10")],
                 [V("rc", "RC", 40, K, "CRE52.10"), V("addon_aggregate", "AddOn", 629, K, "CRE52.25"), V("multiplier", "multiplier", 1.0, "unitless", "CRE52.23")],
                 [P("ead", 936, K, "nearest integer", "CRE52.1")]),
        official("cre99-netting-set-5", "sa-ccr", txt("CRE99 netting set 5: margined interest rate and commodity", "CRE99 conjunto 5: tasas y commodities con margen"),
                 "CRE52.1", "CRE52.18 to CRE52.52", u, pub, src,
                 [V("v", "V", 80, K, "CRE52.18"), V("c", "C", 200, K, "CRE52.18"), V("th", "TH", 0, K, "CRE52.18"),
                  V("mta", "MTA", 5, K, "CRE52.18"), V("nica", "NICA", 150, K, "CRE52.18"), V("v_minus_c", "V-C", -120, K, "CRE52.23"),
                  V("mpor_business_days", "MPOR", 14, "business days", "CRE52.52")],
                 [V("rc", "RC", 0, K, "CRE52.18"), V("maturity_factor", "MF", 1.5 * math.sqrt(14 / 250), "unitless", "CRE52.52"),
                  V("addon_ir", "AddOn_IR", 123, K, "CRE52.57"), V("addon_commodity", "AddOn_commodity", 1278, K, "CRE52.70"),
                  V("addon_aggregate", "AddOn", 1401, K, "CRE52.25"), V("multiplier", "multiplier", 0.958, "unitless", "CRE52.23")],
                 [P("ead", 1879, K, "nearest integer", "CRE52.1")]),
        official("rbc20-13-output-floor", "output-floor", txt("RBC20.13 output floor", "RBC20.13 piso de salida"), "RBC20.4",
                 "RBC20.4 and RBC20.11 to RBC20.13", u, "2020-11-26", "dossier 01 C.1 and M.1",
                 [V("rwa_nominated", "RWA", 76, "index points", "RBC20.13"), V("rwa_sa_only", "RWA_SA", 140, "index points", "RBC20.13"),
                  V("floor_factor", "f", 0.725, "decimal", "RBC90.1")],
                 [V("rwa_floored", "RWA_floor", 101.5, "index points", "RBC20.4")], [P("rwa_floored", 101.5, "index points", "none", "RBC20.13")]),
        official("rbc20-13-output-floor-capped", "output-floor", txt("RBC20.13 output floor with the RBC90.2 cap", "RBC20.13 piso con el tope RBC90.2"),
                 "RBC90.2", "RBC90.1 to RBC90.2", u, "2020-03-27", "dossier 01 C.1 and M.1",
                 [V("rwa_nominated", "RWA", 76, "index points", "RBC20.13"), V("rwa_sa_only", "RWA_SA", 140, "index points", "RBC20.13"),
                  V("floor_factor", "f", 0.725, "decimal", "RBC90.1"), V("cap_share", "cap", 0.25, "decimal of pre-floor RWA", "RBC90.2")],
                 [V("rwa_floored", "RWA_floor", 95, "index points", "RBC90.2")], [P("rwa_floored", 95, "index points", "none", "RBC90.2")]),
    ]
    inv = [
        invariant("ba-cva-rho-one", "ba-cva", txt("BA-CVA reduced with rho = 1 gives the sum of SCVA", "BA-CVA reducido con rho = 1 da la suma de SCVA"),
                  "MAR50.14", "MAR50.14 to MAR50.16", u, "2020-07-08", "dossier 01 E.1 and M.1 (inputs constructed by the fixture)",
                  [V("scva_1", "SCVA_1", 10, "USD", "MAR50.15"), V("scva_2", "SCVA_2", 20, "USD", "MAR50.15"), V("rho", "rho", 1.0, "decimal", "MAR50.14")],
                  [V("k_reduced", "K_reduced", 30, "USD", "MAR50.14")],
                  "With rho = 1 the reduced capital base K_reduced equals the sum of the SCVA.",
                  "Con rho = 1 la base K_reduced es igual a la suma de los SCVA."),
        invariant("ba-cva-hedges-floor", "ba-cva", txt("Hedges never take K_full below beta K_reduced", "Las coberturas nunca bajan K_full de beta K_reduced"),
                  "MAR50.20", "MAR50.20 to MAR50.25", u, "2020-07-08", "dossier 01 E.1 and M.1 (inputs constructed by the fixture)",
                  [V("k_reduced", "K_reduced", 30, "USD", "MAR50.14"), V("k_hedged", "K_hedged", 0, "USD", "MAR50.21"), V("beta", "beta", 0.25, "decimal", "MAR50.20")],
                  [V("k_full", "K_full", 7.5, "USD", "MAR50.20")],
                  "K_full = beta K_reduced + (1 - beta) K_hedged is at least beta K_reduced.",
                  "K_full = beta K_reduced + (1 - beta) K_hedged es al menos beta K_reduced."),
        invariant("sbm-low-and-high-scenarios", "frtb-sbm", txt("SBM correlation scenarios", "Escenarios de correlacion SBM"), "MAR21.6",
                  "MAR21.6 to MAR21.7", u, "2026-03-23", "dossier 01 D.2 and M.1 (input constructed by the fixture)",
                  [V("rho", "rho", 0.5, "decimal", "MAR21.6")],
                  [V("rho_low", "rho_low", 0.375, "decimal", "MAR21.6"), V("rho_medium", "rho_medium", 0.5, "decimal", "MAR21.6"),
                   V("rho_high", "rho_high", 0.625, "decimal", "MAR21.6")],
                  "The low scenario uses max(2 rho - 1, 0.75 rho) and the high scenario min(1.25 rho, 1); the SBM result is the maximum of the three.",
                  "El escenario bajo usa max(2 rho - 1, 0.75 rho) y el alto min(1.25 rho, 1); el resultado SBM es el maximo de los tres."),
        invariant("cascade-all-lh-ten", "frtb-liquidity-cascade", txt("Cascade with every LH equal to 10", "Cascada con todos los LH iguales a 10"), "MAR33.4",
                  "MAR33.4 and MAR33.12", u, "2020-06-05", "dossier 01 D.3 and M.1 (input constructed by the fixture)",
                  [V("es_t_p", "ES_T(P)", 10, "USD", "MAR33.4"), V("t", "T", 10, "days", "MAR33.4"), V("lh_1", "LH_1", 10, "days", "MAR33.4")],
                  [V("es", "ES", 10, "USD", "MAR33.4")],
                  "If every risk factor has a liquidity horizon of 10 days the cascade returns ES_T(P); it is monotone in LH.",
                  "Si todo factor tiene horizonte de liquidez de 10 dias la cascada devuelve ES_T(P); es monotona en LH."),
    ]
    grid = []

    def g(cls, key, rw, table, para, pub_in=u):
        grid.append({"exposure_class": cls, "key": key, "risk_weight": rw, "table": table, "paragraph": para, "in_force_date": pub_in})

    for key, rw in zip(["AAA to AA-", "A+ to A-", "BBB+ to BBB-", "BB+ to B-", "below B-", "unrated"], [0.0, 0.2, 0.5, 1.0, 1.5, 1.0]):
        g("sovereigns and central banks", key, rw, "CRE20 Table 1", "CRE20.7")
    for key, rw in zip(["AAA to AA-", "A+ to A-", "BBB+ to BBB-", "BB+ to B-", "below B-"], [0.2, 0.3, 0.5, 1.0, 1.5]):
        g("banks ECRA", key, rw, "CRE20 Table 6", "CRE20.18")
    for key, rw in zip(["AAA to AA-", "A+ to A-", "BBB+ to BBB-", "BB+ to B-", "below B-"], [0.2, 0.2, 0.2, 0.5, 1.5]):
        g("banks ECRA short-term", key, rw, "CRE20 Table 6", "CRE20.18")
    for key, rw in zip(["Grade A", "Grade B", "Grade C"], [0.4, 0.75, 1.5]):
        g("banks SCRA", key, rw, "CRE20 Table 7", "CRE20.21")
    for key, rw in zip(["AAA to AA-", "A+ to A-", "BBB+ to BBB-", "BB+ to BB-", "below BB-", "unrated"], [0.2, 0.5, 0.75, 1.0, 1.5, 1.0]):
        g("corporates", key, rw, "CRE20 Table 10", "CRE20.43")
    for key, rw in zip(["ltv<=50", "50<ltv<=60", "60<ltv<=80", "80<ltv<=90", "90<ltv<=100", "ltv>100"], [0.2, 0.25, 0.3, 0.4, 0.5, 0.7]):
        g("residential real estate, not cash-flow dependent", key, rw, "CRE20 Table 11", "CRE20.82")
    for key, rw in zip(["ltv<=50", "50<ltv<=60", "60<ltv<=80", "80<ltv<=90", "90<ltv<=100", "ltv>100"], [0.3, 0.35, 0.45, 0.6, 0.75, 1.05]):
        g("residential real estate, cash-flow dependent", key, rw, "CRE20 Table 12", "CRE20.84")
    for key, rw in zip(["ltv<=60", "60<ltv<=80", "ltv>80"], [0.7, 0.9, 1.1]):
        g("commercial real estate, cash-flow dependent", key, rw, "CRE20 Table 14", "CRE20.87")
    for key, rw in [("regulatory retail", 0.75), ("transactors", 0.45), ("other retail", 1.0)]:
        g("retail", key, rw, "CRE20.68", "CRE20.68")
    for key, rw in [("equity", 2.5), ("speculative unlisted equity", 4.0), ("subordinated debt", 1.5)]:
        g("equity and subordinated debt", key, rw, "CRE20.57 to CRE20.60", "CRE20.57")
    return {
        "schema": "contraste.regulatory/v1", "case_id": "REGULATORY", "document_id": "fixture-regulatory-calculators",
        "engine": {"name": "riskvalidation", "version": "fixture"},
        "units": {"money": "as stated per value (USD thousands for CRE99, index points for RBC20.13)", "rate": "decimal", "dates": "ISO-8601"},
        "official_examples": ex, "invariant_cases": inv, "cre20_grid": grid, "provenance": provenance(), "lane": lane(),
    }


def main() -> None:
    for name in sc.VARIANTS:
        write(f"c12/variant-swap-exposure-{name}-fixture.json", variant(name))
    write("c12/models-fixture.json", models_doc())
    write("regulatory/calculators-fixture.json", regulatory_doc())


if __name__ == "__main__":
    main()
