"""Builds the four U5-S fixture documents (docs/contracts/fixtures/c06 and c07).

Run: ``python tests/contracts_u5/build_fixtures.py``. Deterministic, standard library only. The numbers are round
and small on purpose; they satisfy the identities the engine contract promises (docs/contracts/engine/provisions-api.md)
but are fixtures, never results: every document is labelled ``fixture`` in its provenance and its ids.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "docs" / "contracts" / "fixtures"
N = NormalDist()


def r(x: float, d: int = 9) -> float:
    return round(x, d)


def txt(en: str, es: str) -> dict:
    return {"en": en, "es": es}


def envelope_common(truth: str) -> dict:
    return {
        "provenance": {
            "truth_status": truth,
            "inputs": [{"source": "fixture-not-a-result", "class": "fixture", "files": []}],
            "licence_classes": {"fixture-not-a-result": "fixture"},
            "generators": ["fixture:u5-s-contracts"],
            "seed": 0,
            "code_version": "fixture",
            "riskvalidation_version": None,
        },
        "lane": {"lane": "precompute", "reasons": ["fixture"]},
    }


def test_row(test_id: str, model_id: str) -> dict:
    return {
        "test_id": test_id, "model_id": model_id, "segment": None, "statistic": 0.0, "p_value": None,
        "metric": 0.0, "h0": "fixture row", "alternative": "fixture row", "policy_version": "fixture",
        "alpha_amber": None, "alpha_red": None, "light": "not_evaluated", "n": None, "n_events": None,
        "inputs_hash": "0" * 64, "reference": "fixture, not a result", "notes": "fixture", "extras": {},
    }


def model_summary(mid: str, rung: str) -> dict:
    return {
        "id": mid, "family": "lifetime-pd", "rung": rung,
        "title": txt(f"Fixture model {mid}", f"Modelo de ejemplo {mid}"),
        "short_title": txt(mid, mid), "engine": "riskvalidation", "engine_version": "fixture",
        "licence": "MIT", "calibration": None, "parameters": {}, "checkpoint_sha256": None,
    }


def model_record(mid: str, rung: str) -> dict:
    d = model_summary(mid, rung)
    d["details"] = {}
    return d


# ------------------------------------------------------------------------------------------------------- C06

PD_TTC = {"s1": 0.02, "s2": 0.04}
RHO = 0.12
SCEN = [("up", 1.0, 0.25), ("base", 0.0, 0.50), ("down", -2.0, 0.25)]
PERIODS = 8  # quarters
PERIOD_M = 3


def pit(ttc: float, z: float, rho: float = RHO) -> float:
    return N.cdf((N.inv_cdf(ttc) - math.sqrt(rho) * z) / math.sqrt(1 - rho))


def survival_from_pd(pd_year: float) -> list[float]:
    h = 1 - (1 - pd_year) ** 0.25
    return [(1 - h) ** t for t in range(1, PERIODS + 1)]


def structure(surv: list[float]) -> dict:
    prev, h, q, f = 1.0, [], [], []
    for s in surv:
        h.append(r(1 - s / prev))
        q.append(r(prev - s))
        f.append(r(1 - s))
        prev = s
    return {"months": [PERIOD_M * (i + 1) for i in range(PERIODS)], "hazard": h, "marginal_pd": q, "cumulative_pd": f}


def ecl(q: list[float], lgd: float, ead: float, eir: float, periods: int) -> float:
    return sum(q[t] * lgd * ead * (1 + eir) ** (-((t + 0.5) * PERIOD_M / 12)) for t in range(periods))


def decile_rows(cur1: list[float]) -> list[dict]:
    """Calibration per predicted-risk decile at 12, 24 and 36 months: 36 months is beyond the observation cutoff."""
    rows = []
    for months in (12, 24, 36):
        for decile in range(1, 11):
            base = cur1[3] if months == 12 else cur1[7]
            pred = base * (0.4 + 0.2 * (decile - 1)) * (1.0 if months < 36 else 1.4)
            observed = r(pred * (0.9 + 0.02 * decile)) if months < 36 else None
            rows.append({"origination_cohort": "all", "months": months, "decile": decile, "n": 100 * decile,
                         "estimator": "aalen-johansen", "predicted_cumulative_pd": r(pred),
                         "observed_cumulative_pd": observed,
                         "reason": None if observed is not None else "fixture: horizon beyond the observation cutoff"})
    return rows


def build_c06() -> tuple[dict, dict]:
    seg_curves: dict[tuple[str, str], list[float]] = {}
    for seg, ttc in PD_TTC.items():
        for sid, z, _ in SCEN:
            seg_curves[(seg, sid)] = survival_from_pd(pit(ttc, z))
        w = [sum(wt * seg_curves[(seg, sid)][t] for sid, _, wt in SCEN) for t in range(PERIODS)]
        seg_curves[(seg, "weighted")] = w
    term = []
    for seg in PD_TTC:
        for sid in [s[0] for s in SCEN] + ["weighted"]:
            term.append({"scenario_id": sid, "segment_id": seg, **structure(seg_curves[(seg, sid)])})

    def qs(seg: str, sid: str) -> list[float]:
        t = next(x for x in term if x["segment_id"] == seg and x["scenario_id"] == sid)
        return t["marginal_pd"]

    accounts = [
        ("A1", "s1", "stage1", 100000.0, 0.06, 0.40, 4),
        ("A2", "s1", "stage2", 80000.0, 0.07, 0.45, 8),
        ("A3", "s2", "stage3", 50000.0, 0.08, 0.50, 0),
    ]
    rows, stage_ecl = [], {}
    for sid, _, _ in SCEN:
        for acc, seg, stage, gca, eir, lgd, per in accounts:
            if stage == "stage3":
                e = gca - 30000.0 / (1 + eir)
            else:
                e = ecl(qs(seg, sid), lgd, gca, eir, per)
            e = round(e, 2)
            rows.append({"scenario_id": sid, "stage": stage, "ecl": e})
            stage_ecl.setdefault(stage, {})[sid] = e
    w = {sid: wt for sid, _, wt in SCEN}
    weighted = {st: round(sum(w[s] * v for s, v in per.items()), 6) for st, per in stage_ecl.items()}
    gcas = {a[2]: a[3] for a in accounts}
    overlay_amount = 1500.0
    model_total = round(sum(weighted.values()), 2)
    closing = round(model_total + overlay_amount, 2)

    # per-stage movements of the allowance roll-forward (35H); the waterfall lines are their sums
    alloc = {
        "originations": [600.0, 200.0, 0.0],
        "transfer-1-2": [-400.0, 1600.0, 0.0],
        "transfer-2-3": [0.0, -4000.0, 18000.0],
        "transfer-2-1": [200.0, -300.0, 0.0],
        "remeasurement": [0.0, 0.0, 0.0],  # the plug of each stage, set below from its opening and closing
        "macro-update": [500.0, 300.0, 100.0],
        "write-off": [0.0, 0.0, -6000.0],
        "unwinding": [0.0, 0.0, 600.0],
    }
    stages = ["stage1", "stage2", "stage3"]
    closing_by_stage = {s: round(weighted[s], 2) for s in stages}
    closing_by_stage["stage1"] = round(closing_by_stage["stage1"] + overlay_amount, 2)
    # Non-negative openings with coverage below 100 per cent of the opening gross carrying amount (only POCI may be negative).
    opening_by_stage = {"stage1": round(0.8 * closing_by_stage["stage1"], 2), "stage2": 3000.0, "stage3": 6000.0}
    rec_allow = []
    for i, s in enumerate(stages):
        others = sum(v[i] for k, v in alloc.items() if k != "remeasurement") + (overlay_amount if s == "stage1" else 0.0)
        alloc["remeasurement"][i] = round(closing_by_stage[s] - opening_by_stage[s] - others, 2)
        moves = [{"line_id": k, "amount": v[i]} for k, v in alloc.items()]
        if s == "stage1":
            moves.append({"line_id": "overlay-OVL-RATES", "amount": overlay_amount})
        opening = opening_by_stage[s]
        rec_allow.append({"stage": s, "opening": opening, "movements": moves, "closing": closing_by_stage[s],
                          "residual": r(closing_by_stage[s] - (opening + sum(m["amount"] for m in moves)))})
    gca_alloc = {"originations": [20000.0, 0.0, 0.0], "transfer-1-2": [-80000.0, 80000.0, 0.0],
                 "transfer-2-3": [0.0, -50000.0, 50000.0], "repayments": [-5000.0, -2000.0, 0.0],
                 "write-off": [0.0, 0.0, -10000.0]}
    rec_gca = []
    for i, s in enumerate(stages):
        moves = [{"line_id": k, "amount": v[i]} for k, v in gca_alloc.items()]
        opening = gcas[s] - sum(m["amount"] for m in moves)
        rec_gca.append({"stage": s, "opening": opening, "movements": moves, "closing": gcas[s],
                        "residual": r(gcas[s] - (opening + sum(m["amount"] for m in moves)))})
    wf_lines = [{"id": "opening", "kind": "opening", "label": txt("Opening allowance", "Cobertura inicial"),
                 "amount": round(sum(x["opening"] for x in rec_allow), 2), "stage": None, "overlay_id": None}]
    labels = {
        "originations": ("Originations", "Originaciones"), "transfer-1-2": ("Transfer 1 to 2", "Traspaso 1 a 2"),
        "transfer-2-3": ("Transfer 2 to 3", "Traspaso 2 a 3"), "transfer-2-1": ("Transfer 2 to 1", "Traspaso 2 a 1"),
        "remeasurement": ("Parameter remeasurement", "Remedicion de parametros"),
        "macro-update": ("Macro scenario update", "Actualizacion de escenarios"),
        "write-off": ("Write-offs", "Castigos"), "unwinding": ("Unwinding of the discount", "Devengo del descuento"),
    }
    for k, v in alloc.items():
        wf_lines.append({"id": k, "kind": k, "label": txt(*labels[k]), "amount": round(sum(v), 2), "stage": None,
                         "overlay_id": None})
    wf_lines.insert(7, {"id": "overlay-OVL-RATES", "kind": "overlay",
                        "label": txt("Overlay: rates shock (expert)", "Ajuste: shock de tasas (experto)"),
                        "amount": overlay_amount, "stage": "stage1", "overlay_id": "OVL-RATES"})
    wf_lines.append({"id": "closing", "kind": "closing", "label": txt("Closing allowance", "Cobertura final"),
                     "amount": closing, "stage": None, "overlay_id": None})

    # non-linearity at the same scenarios: PD, and ECL at the weighted-average factor
    zbar = sum(wt * z for _, z, wt in SCEN)
    pd_w = sum(wt * pit(0.02, z) for _, z, wt in SCEN)
    mean_curve = {seg: survival_from_pd(pit(ttc, zbar)) for seg, ttc in PD_TTC.items()}
    ecl_mean = 0.0
    for acc, seg, stage, gca, eir, lgd, per in accounts:
        if stage == "stage3":
            ecl_mean += gca - 30000.0 / (1 + eir)
        else:
            sv = mean_curve[seg]
            q = [(1.0 if t == 0 else sv[t - 1]) - sv[t] for t in range(PERIODS)]
            ecl_mean += ecl(q, lgd, gca, eir, per)
    grid = []
    for wu in (0.0, 0.25, 0.5, 0.75, 1.0):
        for wd in (0.0, 0.25, 0.5, 0.75, 1.0):
            wb = round(1 - wu - wd, 6)
            if wb < -1e-9:
                continue
            ww = [wu, max(wb, 0.0), wd]
            rec = sum(ww[i] * sum(stage_ecl[s][SCEN[i][0]] for s in stages) for i in range(3))
            frz = sum(ww[i] * sum(stage_ecl[s][SCEN[i][0]] for s in stages) for i in range(3))
            s2 = min(0.5, 0.2 + 0.2 * wd)
            grid.append({"weights": ww, "ecl_recomputed": round(rec * (1 + 0.02 * wd), 2), "ecl_frozen": round(frz, 2),
                         "stage2_ratio_recomputed": r(s2, 4), "stage2_ratio_frozen": 0.2})
    grid = [g for g in grid if math.isclose(sum(g["weights"]), 1.0, abs_tol=1e-9)]
    months = [PERIOD_M * (i + 1) for i in range(PERIODS)]
    orig = structure(survival_from_pd(0.02))["cumulative_pd"]
    cur1 = next(x for x in term if x["segment_id"] == "s1" and x["scenario_id"] == "weighted")["cumulative_pd"]
    out = {
        "kind": "reporting-date",
        "reporting_date": "2020-06-30",
        "currency": "USD",
        "period_months": PERIOD_M,
        "horizon": {"stage1_months": 12, "lifetime_cap_months": 24},
        "settings": {
            "discount_convention": "mid-period", "eir_basis": "original", "probation_months": 6,
            "low_credit_risk_exemption": False,
            "sicr": {"dpd_backstop": 30, "default_dpd": 90, "low_credit_risk_pd": None, "threefold_ratio": 3.0,
                     "absolute_floor": 0.005,
                     "multiplier_schedule": [{"pd_origination_upper": 0.01, "multiplier": 4.0},
                                             {"pd_origination_upper": 0.05, "multiplier": 2.5},
                                             {"pd_origination_upper": 0.5, "multiplier": 1.5}]},
        },
        "data_status": {
            "primary_source": "sba-7a", "freddie_mac_available": False,
            "freddie_mac_reason": txt("fixture: no Freddie Mac registration, the SBA 7(a) public twin carries this variant",
                                      "ejemplo: sin registro de Freddie Mac, el gemelo público de la SBA 7(a) lleva esta variante"),
            "notice": txt("Fixture, not a result. Round numbers for three accounts.",
                          "Ejemplo, no es un resultado. Numeros redondos para tres cuentas."),
        },
        "scenarios": [{"id": sid, "label": txt(sid.capitalize(), sid.capitalize()), "weight": wt, "z_mean": z}
                      for sid, z, wt in SCEN],
        "term_structures": term,
        "account_curves": [
            {"account_id": "A1", "segment_id": "s1", "stage": "stage1", "months": months,
             "origination_cumulative_pd": orig, "current_cumulative_pd": cur1},
            {"account_id": "A2", "segment_id": "s1", "stage": "stage2", "months": months,
             "origination_cumulative_pd": orig, "current_cumulative_pd": cur1},
        ],
        "sicr_points": [
            {"account_id": "A1", "segment_id": "s1", "stage": "stage1", "pd_origination_annualised": 0.02,
             "pd_current_annualised": 0.025, "trigger": "none"},
            {"account_id": "A2", "segment_id": "s1", "stage": "stage2", "pd_origination_annualised": 0.02,
             "pd_current_annualised": 0.07, "trigger": "threefold"},
        ],
        "stage_flows": {"from_date": "2019-12-31", "to_date": "2020-06-30", "currency": "USD", "flows": [
            {"source": "stage1", "target": "stage1", "accounts": 1, "gross_carrying_amount": 100000.0},
            {"source": "stage1", "target": "stage2", "accounts": 1, "gross_carrying_amount": 80000.0},
            {"source": "stage2", "target": "stage3", "accounts": 1, "gross_carrying_amount": 50000.0}]},
        "stage_summary": {"currency": "USD", "rows": [
            {"stage": s, "accounts": 1, "gross_carrying_amount": gcas[s], "ecl": weighted[s],
             "coverage": r(weighted[s] / gcas[s], 6)} for s in stages]},
        "ecl_by_scenario": {"currency": "USD", "rows": rows},
        "weight_grid": {"currency": "USD", "scenario_ids": [s[0] for s in SCEN], "points": grid},
        "non_linearity": {
            "currency": "USD", "parameters": {"pd_ttc": 0.02, "rho": RHO}, "mean_z": zbar,
            "pd_weighted": r(pd_w), "pd_at_mean_z": r(pit(0.02, zbar)),
            "ecl_weighted": model_total, "ecl_at_mean_path": round(ecl_mean, 2),
            "index": r(model_total / ecl_mean - 1, 6),
            "z_curve": [{"z": float(z), "pd_pit": r(pit(0.02, z))} for z in range(-3, 4)],
            "scenario_points": [{"scenario_id": sid, "z": z, "weight": wt, "pd_pit": r(pit(0.02, z))}
                                for sid, z, wt in SCEN],
        },
        "waterfall": {"currency": "USD", "lines": wf_lines},
        "overlays": [{"id": "OVL-RATES", "currency": "USD",
                      "rationale": txt("Interest-rate shock on floating-rate borrowers, not in the satellite",
                                       "Shock de tasas sobre deudores a tasa variable, fuera del satelite"),
                      "method": "expert", "target": "pd", "segment_id": "s1", "stage": "stage1", "amount": overlay_amount,
                      "staging_effect": "none", "review_date": "2020-12-31"}],
        "reconciliation": {"currency": "USD", "tolerance": 1e-6, "allowance": rec_allow,
                           "gross_carrying_amount": rec_gca},
        "lifetime_backtest": {"rows": [
            {"origination_cohort": "all", "estimator": "aalen-johansen", "months": m,
             "predicted_cumulative_pd": cur1[i],
             "observed_cumulative_pd": obs, "gap": None if obs is None else r(obs - cur1[i]),
             "brier": None if obs is None else 0.01,
             "reason": None if obs is not None else "fixture: horizon beyond the observation cutoff"}
            for i, (m, obs) in enumerate(zip(months, [0.004, 0.009, 0.013, 0.018] + [None] * 4))]},
        "decile_calibration": {"rung_id": "L1-dth", "rows": decile_rows(cur1)},
        "rung_comparison": [
            {"rung_id": "L0-km", "c_index": None, "integrated_brier": 0.02, "calibration_gap_12m": 0.001,
             "reason": txt("fixture: Kaplan-Meier has no covariates, no c-index", "ejemplo: Kaplan-Meier no tiene covariables, no hay índice c")},
            {"rung_id": "L1-dth", "c_index": 0.7, "integrated_brier": 0.018, "calibration_gap_12m": 0.0005,
             "reason": None},
            {"rung_id": "L2-cox", "c_index": 0.72, "integrated_brier": 0.017, "calibration_gap_12m": -0.0003,
             "reason": None},
        ],
    }
    variant = {
        "schema": "contraste.case/v1", "case_id": "C06", "variant_id": "fixture-2020-06",
        "model": [model_summary("L1-dth", "discrete-time-hazard")],
        "outputs": out,
        "tests": [test_row("ifrs9.reconciliation_identities", "L1-dth")],
        "impact": {f"ecl_{s}": {"value": weighted[s], "unit": "USD",
                                "label": txt(f"ECL {s}", f"ECL {s}")} for s in stages},
        "findings": [],
        **envelope_common("real-outcomes"),
    }
    models = {
        "schema": "contraste.models/v1", "case_id": "C06", "fit_id": "fixture-sba-7a",
        "model": [model_record("L1-dth", "discrete-time-hazard")],
        "fit": {
            "currency": "USD",
            "segments": [{"id": s, "label": txt(f"Segment {s}", f"Segmento {s}"), "pd_ttc": PD_TTC[s],
                          "accounts": 2} for s in PD_TTC],
            "scenario_definitions": [
                {"id": sid, "label": txt(sid.capitalize(), sid.capitalize()), "weight": wt,
                 "source": "fixture: illustrative, not the Fed 2026 paths",
                 "z_path": [{"months": 12, "z": z}, {"months": 24, "z": z / 2}],
                 "macro": [{"variable": "unemployment", "unit": "percent", "months": [12, 24],
                            "values": [4.0 - z, 4.0 - z / 2]}]}
                for sid, z, wt in SCEN],
            "pit": {"rho": RHO, "method": "one-factor Vasicek, z extracted from default rates",
                    "z_hat": [{"period": "2019-12-31", "z": 0.2}, {"period": "2020-06-30", "z": -0.4}],
                    "satellite": {"intercept": 0.0, "ar1": 0.6,
                                  "coefficients": [{"name": "unemployment", "value": -0.1}]}},
            "ladder": [
                {"rung_id": "L0-km", "kind": "kaplan-meier", "covariates": [], "macro_covariates": [],
                 "competing_prepayment": False, "training_cutoff": "2019-12-31", "coefficients": [],
                 "baseline": {"months": months, "cumulative_pd": orig}},
                {"rung_id": "L1-dth", "kind": "discrete-time-hazard", "covariates": ["ltv", "age"],
                 "macro_covariates": ["unemployment"], "competing_prepayment": True,
                 "training_cutoff": "2019-12-31",
                 "coefficients": [{"name": "ltv", "estimate": 0.8, "std_error": 0.1},
                                  {"name": "unemployment", "estimate": 0.3, "std_error": None}],
                 "baseline": {"months": months, "cumulative_pd": cur1}},
            ],
            "lgd": {"kind": "workout", "discounting": "original EIR",
                    "segments": [{"segment_id": "s1", "lgd": 0.4, "basis": "fixture"},
                                 {"segment_id": "s2", "lgd": 0.5, "basis": "fixture"}]},
            "ead": {"amortising": True, "ccf_revolving": None,
                    "reason": "fixture: term loans only, no revolving facility"},
            "staging_policy": {"dpd_backstop": 30, "default_dpd": 90, "threefold_ratio": 3.0, "absolute_floor": 0.005,
                               "probation_months": 6, "low_credit_risk_pd": None,
                               "multiplier_schedule": [{"pd_origination_upper": 0.01, "multiplier": 4.0},
                                                       {"pd_origination_upper": 0.05, "multiplier": 2.5},
                                                       {"pd_origination_upper": 0.5, "multiplier": 1.5}],
                               "source": "fixture: Contraste policy parameters, not IFRS 9 requirements"},
        },
        **envelope_common("real-outcomes"),
    }
    return variant, models


# ------------------------------------------------------------------------------------------------------- C07

SCENARIOS = [
    ("base", "Base", "Base", []),
    ("recession", "Recession", "Recesion", [("gdp-growth", "percentage points", -3.0),
                                            ("unemployment", "percentage points", 4.0)]),
    ("consumer-arrears-shock", "Consumer arrears shock", "Shock de mora de consumo",
     [("consumer-arrears", "percentage points", 3.0)]),
    ("house-price-fall", "House price fall", "Caida del precio de viviendas", [("house-prices", "percent", -15.0)]),
    ("uf-inflation-spike", "UF inflation spike", "Alza de inflacion UF", [("uf-inflation", "percentage points", 4.0)]),
    ("combined-severe", "Combined severe", "Severo combinado", [("gdp-growth", "percentage points", -5.0),
                                                                ("unemployment", "percentage points", 6.0),
                                                                ("house-prices", "percent", -25.0)]),
]


def pct(x: float) -> float:
    return round(x / 100.0, 10)


def b1_tables() -> list[dict]:
    mort = {
        "pvg<=40": ([1.0916, 21.3407, 46.0536, 75.1614, 100], [0.0225, 0.0441, 0.0482, 0.0482, 0.0537],
                    [0.0002, 0.0094, 0.0222, 0.0362, 0.0537]),
        "40<pvg<=80": ([1.9158, 27.4332, 52.0824, 78.9511, 100], [2.1955, 2.8233, 2.9192, 2.9192, 3.0413],
                       [0.0421, 0.7745, 1.5204, 2.3047, 3.0413]),
        "80<pvg<=90": ([2.5150, 27.9300, 52.5800, 79.6952, 100], [21.5527, 21.6600, 21.9200, 22.1331, 22.2310],
                       [0.5421, 6.0496, 11.5255, 17.6390, 22.2310]),
        "pvg>90": ([2.7400, 28.4300, 53.0800, 80.3677, 100], [27.2000, 29.0300, 29.5900, 30.1558, 30.2436],
                   [0.7453, 8.2532, 15.7064, 24.2355, 30.2436]),
    }
    cols = ["0", "1-29", "30-59", "60-89", "default"]
    mcells = []
    for row, (pi, pdi, pe) in mort.items():
        for c, a, b, e in zip(cols, pi, pdi, pe):
            mcells.append({"row": row, "column": c, "pi": pct(a), "pdi": pct(b), "pe": pct(e)})
    indiv = [("A1", 0.04, 90.0, 0.036), ("A2", 0.10, 82.5, 0.0825), ("A3", 0.25, 87.5, 0.21875),
             ("A4", 2.00, 87.5, 1.75), ("A5", 4.75, 90.0, 4.275), ("A6", 10.00, 90.0, 9.0),
             ("B1", 15.00, 92.5, 13.875), ("B2", 22.00, 92.5, 20.35), ("B3", 33.00, 97.5, 32.175),
             ("B4", 45.00, 97.5, 43.875)]
    icells = [{"row": c, "column": "category", "pi": pct(a), "pdi": pct(b), "pe": pct(e)} for c, a, b, e in indiv]
    cons = {
        "0-7": [3.3, 14.6, 6.6, 19.8], "8-30": [20.4, 41.6, 30.6, 48.5],
        "31-60": [50.2, 63.0, 65.1, 66.3], "61-89": [62.6, 81.7, 72.3, 86.9],
    }
    ccols = ["mortgage-no-arrears", "mortgage-arrears", "no-mortgage-no-arrears", "no-mortgage-arrears"]
    ccells = [{"row": row, "column": c, "pi": pct(v), "pdi": None, "pe": None}
              for row, vals in cons.items() for c, v in zip(ccols, vals)]
    def src(tail: str) -> dict:
        return txt("CMF CNCB Chapter B-1, dossier 03 section " + tail, "CMF CNCB Capítulo B-1, dossier 03 sección " + tail)
    return [
        {"table_id": "mortgage-pe", "portfolio": "residential-mortgage", "source": src("D.5 (3.1.1)"), "cells": mcells},
        {"table_id": "individual-categories", "portfolio": "commercial-individual", "source": src("D.3 (2.1)"),
         "cells": icells},
        {"table_id": "consumer-pi", "portfolio": "consumer", "source": src("D.5 (3.1.3)"), "cells": ccells},
    ]


STATUS = {"cmf-b1": "statutory-chile-loans", "ifrs9": "comparison-measure",
          "bde-annex9": "spanish-gaap-alternative-solutions"}
Z_SHIFT = {"base": 0.0, "recession": -1.5, "consumer-arrears-shock": -0.5, "house-price-fall": -0.6,
           "uf-inflation-spike": -0.4, "combined-severe": -2.5}


def build_c07() -> tuple[dict, dict]:
    cur = "CLP"
    seg = [("mortgage", "residential-mortgage", "Residential mortgages", "Hipotecario vivienda", 60e9, 300000,
            "B.1.1 Vivienda habitual, LTV <= 80%"),
           ("consumer", "consumer", "Consumer", "Consumo", 20e9, 900000, "B.2 Credito al consumo"),
           ("commercial-group", "commercial-group", "Commercial (group)", "Comercial grupal", 10e9, 40000,
            "A.2.2 Pymes"),
           ("commercial-individual", "commercial-individual", "Commercial (individual)", "Comercial individual",
            30e9, 1200, "A.2.1 Grandes empresas")]
    cmf = [480e6, 1.4e9, 400e6, 600e6]
    ifrs = [540e6, 1.2e9, 360e6, 900e6]   # model ECL by segment, excluding the overlay
    bde = [420e6, 1.5e9, 330e6, 720e6]
    top_up, overlay_amt, additional = 25e6, 20e6, 60e6
    tot = {"cmf-b1": sum(cmf) + top_up, "ifrs9": sum(ifrs) + overlay_amt, "bde-annex9": sum(bde)}
    unalloc = {
        "cmf-b1": [{"id": "minimum-top-up", "kind": "minimum-top-up",
                    "label": txt("Minimum 0.50% top-up on the individual normal portfolio",
                                 "Complemento del minimo 0,50% en la cartera normal individual"), "amount": top_up}],
        "ifrs9": [{"id": "overlay-OVL-HOUSING", "kind": "overlay",
                   "label": txt("Overlay: house price outlook (expert)", "Ajuste: perspectiva de precios de viviendas (experto)"),
                   "amount": overlay_amt}],
        "bde-annex9": []}
    bde_codes = {"mortgage": "B.1.1", "consumer": "B.2", "commercial-group": "A.2.2", "commercial-individual": "A.2.1"}
    expo = [s[4] for s in seg]
    total_expo = sum(expo)

    def regime(key: str, label: tuple, vals: list[float], cats: list[tuple]) -> dict:
        return {"regime": key, "label": txt(*label), "status": STATUS[key], "currency": cur,
                "total_provision": tot[key], "unallocated_lines": unalloc[key],
                "coverage_rate": r(tot[key] / total_expo, 8),
                "by_segment": [{"segment_id": s[0], "provision": v, "coverage_rate": r(v / s[4], 8)}
                               for s, v in zip(seg, vals)],
                "by_category": [{"category_id": c, "label": txt(*lab), "exposure": e, "provision": p}
                                for c, lab, e, p in cats]}

    regimes = [
        regime("cmf-b1", ("CMF CNCB B-1", "CMF CNCB B-1"), cmf, [
            ("group", ("Group assessment", "Evaluacion grupal"), 90e9, 2.28e9),
            ("individual-normal-substandard", ("Individual, normal and substandard", "Individual, normal y subestandar"),
             29e9, 500e6),
            ("individual-default", ("Individual, default", "Individual, incumplimiento"), 1e9, 100e6)]),
        regime("ifrs9", ("IFRS 9", "IFRS 9"), ifrs, [
            ("stage1", ("Stage 1", "Etapa 1"), 105e9, 800e6), ("stage2", ("Stage 2", "Etapa 2"), 12e9, 1.2e9),
            ("stage3", ("Stage 3", "Etapa 3"), 3e9, 1.0e9)]),
        regime("bde-annex9", ("BdE Annex 9", "BdE Anexo 9"), bde, [
            ("normal", ("Normal risk", "Riesgo normal"), 108e9, 900e6),
            ("normal-special-watch", ("Normal, special watch", "Normal en vigilancia especial"), 9e9, 1.17e9),
            ("doubtful", ("Doubtful", "Dudoso"), 3e9, 900e6)]),
    ]
    out = {
        "kind": "three-regime", "scenario_id": "base", "currency": cur, "synthetic": True,
        "notice": txt("Fixture, not a result. Synthetic bank, round numbers; no statement about any bank. The IFRS 9 column is a "
                      "comparison measure, not the provision Chilean banks book on loans (CMF B-1).",
                      "Ejemplo, no es un resultado. Banco sintetico, numeros redondos; sin afirmacion sobre ningun banco. La "
                      "columna IFRS 9 es una medida de comparacion, no la provision que los bancos chilenos constituyen sobre "
                      "los creditos (CMF B-1)."),
        "scenario": {"description": txt("Base scenario: no shock.", "Escenario base: sin shock."), "shocks": []},
        "portfolio": {"currency": cur, "segments": [
            {"segment_id": s[0], "label": txt(s[2], s[3]), "accounts": s[5], "gross_exposure": s[4]} for s in seg]},
        "regimes": regimes,
        "comparison": {"currency": cur, "rows": [
            {"segment_id": s[0], "cmf_b1_provision": a, "ifrs9_provision": b, "bde_annex9_provision": c,
             "gap_ifrs9_minus_b1": b - a, "gap_bde_minus_b1": c - a} for s, a, b, c in zip(seg, cmf, ifrs, bde)],
            "unallocated": {"cmf_b1_provision": top_up, "ifrs9_provision": overlay_amt, "bde_annex9_provision": 0.0,
                            "gap_ifrs9_minus_b1": overlay_amt - top_up, "gap_bde_minus_b1": -top_up}},
        "gap_bridge": {"currency": cur, "from_regime": "cmf-b1", "to_regime": "ifrs9", "steps": [
            {"id": "lifetime-horizon", "label": txt("Lifetime loss on Stage 2", "Perdida a vida sobre Etapa 2"),
             "amount": 90e6},
            {"id": "forward-looking", "label": txt("Forward-looking scenarios", "Escenarios prospectivos"),
             "amount": 60e6},
            {"id": "discounting", "label": txt("Discounting at the EIR", "Descuento a la TIE"), "amount": -30e6},
            {"id": "b1-minimum-top-up", "label": txt("B-1 minimum top-up, not in IFRS 9",
                                                    "Complemento del minimo B-1, fuera de IFRS 9"),
             "amount": -top_up},
            {"id": "ifrs9-overlays", "label": txt("IFRS 9 overlays", "Ajustes IFRS 9"), "amount": overlay_amt}]},
        "b1_detail": {
            "currency": cur,
            "minimum_check": {"minimum_rate": 0.005, "normal_portfolio_exposure": 25e9,
                              "normal_portfolio_provision_before_minimum": 100e6, "minimum_amount": 125e6,
                              "binding": True, "top_up": 25e6},
            "group_max_rule": [{"segment_id": s[0], "standard": a, "internal": a * 0.9, "internal_reason": None,
                                "applied": a, "method": "max"} for s, a in zip(seg[:3], cmf[:3])],
            "booked_total": tot["cmf-b1"] + additional,
            "additional_provisions": {"amount": additional, "rationale": txt("Counter-cyclical, board policy",
                                                                       "Contraciclica, politica del directorio"),
                                      "policy_min": 0.0, "policy_max": 120e6},
            "individual": {"normal_substandard_provision": 500e6, "default_provision": 100e6}},
        "ifrs9_detail": {"currency": cur, "measure": "probability-weighted-ecl", "stage_summary": [
            {"stage": "stage1", "accounts": 1000000, "gross_carrying_amount": 105e9, "ecl": 800e6,
             "coverage": r(800e6 / 105e9, 8)},
            {"stage": "stage2", "accounts": 200000, "gross_carrying_amount": 12e9, "ecl": 1.2e9,
             "coverage": r(1.2e9 / 12e9, 8)},
            {"stage": "stage3", "accounts": 41200, "gross_carrying_amount": 3e9, "ecl": 1.0e9,
             "coverage": r(1.0e9 / 3e9, 8)}],
            "weighted_components": [
                {"scenario_id": sid, "weight": w, "z": z, "single_scenario_ecl": e}
                for sid, w, z, e in [("upside", 0.25, 1.0, 2.5e9), ("central", 0.5, 0.0, 2.85e9),
                                     ("downside", 0.25, -2.0, 3.8e9)]],
            "overlays": [{"id": "OVL-HOUSING", "label": unalloc["ifrs9"][0]["label"], "segment_id": "mortgage",
                          "stage": "stage2", "amount": overlay_amt}],
            "overlays_total": overlay_amt},
        "bde_detail": {"currency": cur, "categories": [
            {"category": "normal", "mapped_stage": "stage1", "exposure": 108e9, "provision": 900e6,
             "coverage_rate": r(900e6 / 108e9, 8)},
            {"category": "normal-special-watch", "mapped_stage": "stage2", "exposure": 9e9, "provision": 1.17e9,
             "coverage_rate": r(1.17e9 / 9e9, 8)},
            {"category": "doubtful", "mapped_stage": "stage3", "exposure": 3e9, "provision": 900e6,
             "coverage_rate": 0.3}], "method": "alternative-solutions"},
        "delta_vs_base": None,
    }
    variant = {
        "schema": "contraste.case/v1", "case_id": "C07", "variant_id": "fixture-base",
        "model": [model_summary("R3-trilogy", "three-regime")],
        "outputs": out,
        "tests": [test_row("ifrs9.reconciliation_identities", "R3-trilogy")],
        "impact": {"provision_cmf_b1": {"value": tot["cmf-b1"], "unit": "CLP", "label": txt("CMF B-1", "CMF B-1")},
                   "provision_ifrs9": {"value": tot["ifrs9"], "unit": "CLP", "label": txt("IFRS 9", "IFRS 9")},
                   "provision_bde": {"value": tot["bde-annex9"], "unit": "CLP", "label": txt("BdE Annex 9", "BdE Anexo 9")}},
        "findings": [],
        **envelope_common("synthetic-calibrated"),
    }
    models = {
        "schema": "contraste.models/v1", "case_id": "C07", "fit_id": "fixture-banco-andino",
        "model": [model_record("R3-trilogy", "three-regime")],
        "fit": {
            "currency": cur,
            "bank": {"name": "Banco Andino", "synthetic": True,
                     "notice": txt("Synthetic bank calibrated to public aggregates; fixture values.",
                                   "Banco sintetico calibrado a agregados publicos; valores de ejemplo."),
                     "seed": 0, "calibration_source": "fixture, not a CMF figure"},
            "calibration_targets": [
                {"metric": "consumer share of loans", "unit": "share", "target": 0.17, "achieved": 0.167,
                 "source": "fixture value, not a CMF figure", "as_of": "2026-06-30"}],
            "segments": [{"id": s[0], "label": txt(s[2], s[3]), "accounts": s[5], "gross_exposure": s[4],
                          "b1_portfolio": s[1], "bde_segment": bde_codes[s[0]],
                          "bde_segment_label": txt(s[6].split(" ", 1)[1], s[6].split(" ", 1)[1])} for s in seg],
            "b1_tables": b1_tables(),
            "b1_default_categories": [
                {"category": "C1", "tpe_upper": 0.03, "provision_rate": 0.02},
                {"category": "C2", "tpe_upper": 0.20, "provision_rate": 0.10},
                {"category": "C3", "tpe_upper": 0.30, "provision_rate": 0.25},
                {"category": "C4", "tpe_upper": 0.50, "provision_rate": 0.40},
                {"category": "C5", "tpe_upper": 0.80, "provision_rate": 0.65},
                {"category": "C6", "tpe_upper": None, "provision_rate": 0.90}],
            "ifrs9": {"pd_ladder_rung": "L1-dth", "discount_convention": "mid-period", "eir_basis": "original",
                      "weighting_scenarios": [
                          {"id": "upside", "label": txt("Upside", "Favorable"), "weight": 0.25, "z_offset": 1.0},
                          {"id": "central", "label": txt("Central", "Central"), "weight": 0.5, "z_offset": 0.0},
                          {"id": "downside", "label": txt("Downside", "Adverso"), "weight": 0.25, "z_offset": -2.0}],
                      "staging_policy": {
                          "dpd_backstop": 30, "default_dpd": 90, "threefold_ratio": 3.0, "absolute_floor": 0.005,
                          "probation_months": 6, "low_credit_risk_pd": None,
                          "multiplier_schedule": [{"pd_origination_upper": 0.01, "multiplier": 4.0},
                                                  {"pd_origination_upper": 0.05, "multiplier": 2.5},
                                                  {"pd_origination_upper": 0.5, "multiplier": 1.5}],
                          "source": "fixture: Contraste policy parameters, not IFRS 9 requirements"},
                      "segments": [{"segment_id": s[0], "pd_ttc": 0.02, "rho": 0.12, "lgd": 0.4} for s in seg]},
            "bde": {
                "normal_coverage": [{"segment": "B.1.1", "normal": 0.007, "special_watch": 0.18},
                                    {"segment": "B.2", "normal": 0.018, "special_watch": 0.202},
                                    {"segment": "A.2.2", "normal": 0.011, "special_watch": 0.178},
                                    {"segment": "A.2.1", "normal": 0.006, "special_watch": 0.096}],
                "doubtful_bucket_labels": [">90d-6m", "6-9m", "9-12m", "12-15m", "15-18m", "18-21m", ">21m"],
                "doubtful_bucket_upper_days": [183, 274, 365, 457, 548, 639, None],
                "doubtful_coverage": [
                    {"segment": "B.1.1", "by_bucket": [0.45, 0.50, 0.65, 0.70, 0.85, 0.95, 1.0]},
                    {"segment": "B.2", "by_bucket": [0.55, 0.65, 0.80, 0.85, 0.95, 1.0, 1.0]},
                    {"segment": "A.2.2", "by_bucket": [0.65, 0.70, 0.75, 0.85, 0.90, 0.95, 1.0]},
                    {"segment": "A.2.1", "by_bucket": [0.55, 0.65, 0.75, 0.90, 0.95, 1.0, 1.0]}]},
            "scenarios": [{"id": sid, "label": txt(en, es), "z_shift": Z_SHIFT[sid],
                           "shocks": [{"driver": d, "unit": u, "value": v} for d, u, v in sh]}
                          for sid, en, es, sh in SCENARIOS],
        },
        **envelope_common("synthetic-calibrated"),
    }
    return variant, models


def dump(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    v6, m6 = build_c06()
    v7, m7 = build_c07()
    dump(FIX / "c06" / "variant-reporting-date-fixture.json", v6)
    dump(FIX / "c06" / "models-fixture.json", m6)
    dump(FIX / "c07" / "variant-three-regime-fixture.json", v7)
    dump(FIX / "c07" / "models-fixture.json", m7)


if __name__ == "__main__":
    main()
