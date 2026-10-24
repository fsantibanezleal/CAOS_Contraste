"""The C06 documents (CT-512): one reporting date into its variant document and its models document.

The variant document is the ``c06-outputs`` contract (``docs/contracts/schemas/c06/variant-reporting-date.schema.json``),
the models document is ``c06-models``. Every PD curve, stage, ECL, allowance and test row in them comes from the engine
(see ``run`` and ``backtest``); this module arranges them, adds the bilingual labels and states the limits.

No loan row is written: the documents carry curves of means, counts, sums and a small anonymous sample of accounts
(``A0001`` and so on, with PDs and a stage, never an identifier, a name or an amount of a loan).
"""
from __future__ import annotations

from typing import Any

import numpy as np
from riskvalidation.provisions import ecl as rv_ecl
from riskvalidation.provisions import term_structure as rv_ts
from riskvalidation.provisions.overlays import Overlay
from riskvalidation.provisions.staging import allocate_stages

from ...core import text as tx
from . import backtest as bt
from .panel import SEGMENT_IDS
from .rollforward import RollForward
from .run import (CONVENTION, PERIOD_MONTHS, POLICY, RHO, DateRun, annualise)

CURRENCY = "USD"
SAMPLE_CURVES, SAMPLE_POINTS = 40, 400
SEGMENT_LABELS = {
    "term-le-60": ("Term up to 5 years", "Plazo hasta 5 años"),
    "term-61-120": ("Term 5 to 10 years", "Plazo de 5 a 10 años"),
    "term-121-240": ("Term 10 to 20 years", "Plazo de 10 a 20 años"),
    "term-gt-240": ("Term over 20 years", "Plazo de más de 20 años"),
}
RUNG_TEXT = {
    "L0-km": (("Kaplan-Meier lifetime PD", "PD de vida completa de Kaplan-Meier"), ("L0 Kaplan-Meier", "L0 Kaplan-Meier")),
    "L1-dth": (("Discrete-time hazard with macro covariates", "Hazard en tiempo discreto con covariables macro"),
               ("L1 Hazard", "L1 Riesgo en tiempo discreto")),
    "L2-cox": (("Cox proportional hazards", "Riesgos proporcionales de Cox"), ("L2 Cox", "L2 Cox")),
}
RUNG_KIND = {"L0-km": "kaplan-meier", "L1-dth": "discrete-time-hazard", "L2-cox": "cox"}
NOTICE = {
    "en": ("Small-business loans, not mortgages: the SBA 7(a) loans are the public twin of the mortgage case. Freddie Mac's data is "
           "not used (the owner's account is missing). Default is a charge-off; the file has no delinquency history, no balance "
           "and no recovery after charge-off."),
    "es": ("Préstamos a pequeñas empresas, no hipotecas: los préstamos SBA 7(a) son el gemelo público del caso hipotecario. No se "
           "usan los datos de Freddie Mac (falta la cuenta del propietario). El incumplimiento es un castigo; el archivo no tiene "
           "historia de mora, saldo ni recuperaciones tras el castigo."),
}


def t(en: str, es: str) -> dict[str, str]:
    return {"en": en, "es": es}


def iso(d: np.datetime64) -> str:
    return str(np.datetime64(d, "D"))


def variant_id(reporting_date: np.datetime64) -> str:
    s = iso(reporting_date)
    return f"rd-{s[:4]}-{s[5:7]}"


def month_label(reporting_date: np.datetime64) -> tuple[str, str, str, str]:
    s = iso(reporting_date)
    months_en = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
    months_es = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
    m = int(s[5:7]) - 1
    return months_en[m], months_es[m], s[:4], s


def policy_block() -> dict[str, Any]:
    return {"dpd_backstop": POLICY.dpd_backstop, "default_dpd": POLICY.default_dpd, "threefold_ratio": POLICY.threefold_ratio,
            "absolute_floor": POLICY.absolute_floor, "multiplier_schedule": [{"pd_origination_upper": u, "multiplier": m}
                                                                              for u, m in POLICY.multiplier_schedule],
            "low_credit_risk_pd": POLICY.low_credit_risk_pd}


def settings_block() -> dict[str, Any]:
    return {"discount_convention": CONVENTION, "eir_basis": "original", "probation_months": POLICY.probation_months,
            "low_credit_risk_exemption": POLICY.low_credit_risk_pd is not None, "sicr": policy_block()}


# ---------------------------------------------------------------------------------------------------------------------
# blocks of the variant document


def _by_stage(stage: np.ndarray, e12: np.ndarray, e_life: np.ndarray, overlays=()) -> Any:
    return rv_ecl.portfolio_allowance(stage, e12, e_life, np.zeros(stage.size), overlays=overlays)


def term_structure_rows(run: DateRun) -> list[dict[str, Any]]:
    rows = []
    max_h = [int(run.horizon_q[run.segment == g].max()) if (run.segment == g).any() else 0 for g in range(4)]
    labels = (*run.scenario_ids, "weighted")
    for s, sid in enumerate(labels):
        for g, seg in enumerate(SEGMENT_IDS):
            h = max_h[g]
            if h < 2:
                continue
            months = PERIOD_MONTHS * np.arange(1, h + 1)
            ts = rv_ts.from_cumulative(np.clip(run.seg_curves[s, g, :h], 1e-12, 1 - 1e-12), months)
            rows.append({"scenario_id": sid, "segment_id": seg, "months": months.tolist(), "hazard": ts.hazard.tolist(),
                         "marginal_pd": ts.marginal.tolist(), "cumulative_pd": ts.cumulative.tolist()})
    return rows


def _sample(run: DateRun, n: int, seed: int, mask: np.ndarray | None = None) -> np.ndarray:
    rng = np.random.default_rng([seed, int(run.reporting_date.astype("datetime64[D]").astype(np.int64))])
    pool = np.flatnonzero(mask if mask is not None else np.ones(run.a, dtype=bool))
    if pool.size <= n:
        return pool
    return np.sort(rng.choice(pool, size=n, replace=False))


def account_curves(run: DateRun, seed: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[int, str]]:
    stage_name = {1: "stage1", 2: "stage2", 3: "stage3"}
    elig = np.isfinite(run.cum12[:, 0]) & np.all(np.diff(run.cum12, axis=1) > 0, axis=1) & np.all(np.diff(run.cum12_orig, axis=1) > 0, axis=1)
    s2 = _sample(run, SAMPLE_CURVES // 4, seed + 1, elig & (run.stage == 2))
    s1 = _sample(run, SAMPLE_CURVES - s2.size, seed + 2, elig & (run.stage == 1))
    pick = np.sort(np.concatenate([s1, s2]))
    months = (PERIOD_MONTHS * np.arange(1, bt.BACKTEST_Q + 1)).tolist()
    curves = [{"account_id": f"A{k + 1:04d}", "segment_id": SEGMENT_IDS[int(run.segment[i])], "stage": stage_name[int(run.stage[i])],
               "months": months, "origination_cumulative_pd": run.cum12_orig[i].tolist(), "current_cumulative_pd": run.cum12[i].tolist()}
              for k, i in enumerate(pick)]
    pts = _sample(run, SAMPLE_POINTS, seed + 3)
    points = [{"account_id": f"P{k + 1:04d}", "segment_id": SEGMENT_IDS[int(run.segment[i])], "stage": stage_name[int(run.stage[i])],
               "pd_origination_annualised": float(run.pd_orig_ann[i]), "pd_current_annualised": float(run.pd_cur_ann[i]),
               "trigger": str(run.stage_result.trigger[i])} for k, i in enumerate(pts)]
    return curves, points, stage_name


def weight_grid(run: DateRun) -> dict[str, Any]:
    ids = list(run.scenario_ids)
    s = len(ids)
    stage0 = run.stage.astype(np.int64)
    base_total = np.array([_by_stage(stage0, run.ecl12[k], run.ecl_life[k]).model_total for k in range(s)])
    h_years = run.horizon_q * PERIOD_MONTHS / 12.0
    points = []
    steps = 4
    for i in range(steps + 1):
        for j in range(steps + 1 - i):
            w = np.array([i, j, steps - i - j], dtype=float) / steps
            frozen = float(rv_ecl.probability_weighted_ecl(base_total, w))
            e12 = rv_ecl.probability_weighted_ecl(run.ecl12, w)
            el = rv_ecl.probability_weighted_ecl(run.ecl_life, w)
            pd_cur = annualise(np.tensordot(w, run.f_h, axes=(0, 0)), h_years)
            st = allocate_stages(run.pd_orig_ann, pd_cur, np.zeros(run.a, dtype=np.int64), np.zeros(run.a, dtype=bool),
                                 np.zeros(run.a, dtype=bool), np.zeros(run.a, dtype=bool), POLICY).stage.astype(np.int64)
            recomputed = _by_stage(st, e12, el).model_total
            gtot = float(run.gca.sum())
            points.append({"weights": w.tolist(), "ecl_recomputed": float(recomputed), "ecl_frozen": frozen,
                           "stage2_ratio_recomputed": float(run.gca[st == 2].sum() / gtot),
                           "stage2_ratio_frozen": float(run.gca[stage0 == 2].sum() / gtot)})
    return {"currency": CURRENCY, "scenario_ids": ids, "points": points}


def z_means(run: DateRun) -> np.ndarray:
    return np.array([float(np.mean(run.z_paths[s][:4])) for s in run.scenario_ids])


def non_linearity_block(run: DateRun, model_total: float, ecl_at_mean_path: float) -> dict[str, Any]:
    zm = z_means(run)
    w = run.weights
    mean_z = float(np.dot(w, zm))
    pd_w = rv_ts.weighted_pit_pd(run.pd_ttc, RHO, zm, w)
    pd_m = float(rv_ts.ttc_to_pit(np.array([run.pd_ttc]), RHO, np.array([mean_z]))[0])
    zs = np.arange(-3.0, 3.01, 1.0)
    curve = rv_ts.ttc_to_pit(np.full(zs.size, run.pd_ttc), RHO, zs)
    pts = rv_ts.ttc_to_pit(np.full(zm.size, run.pd_ttc), RHO, zm)
    return {"currency": CURRENCY, "parameters": {"pd_ttc": run.pd_ttc, "rho": RHO}, "mean_z": mean_z, "pd_weighted": float(pd_w),
            "pd_at_mean_z": pd_m, "ecl_weighted": float(model_total), "ecl_at_mean_path": float(ecl_at_mean_path),
            "index": float(rv_ecl.non_linearity_index(model_total, ecl_at_mean_path)),
            "z_curve": [{"z": float(z), "pd_pit": float(p)} for z, p in zip(zs, curve, strict=True)],
            "scenario_points": [{"scenario_id": sid, "z": float(z), "weight": float(wt), "pd_pit": float(p)}
                                for sid, z, wt, p in zip(run.scenario_ids, zm, w, pts, strict=True)]}


def rollforward_blocks(rf: RollForward, overlays: list[Overlay]) -> tuple[dict[str, Any], dict[str, Any]]:
    def row(r) -> dict[str, Any]:
        return {"stage": r.stage, "opening": r.opening, "movements": [{"line_id": k, "amount": v} for k, v in r.movements],
                "closing": r.closing, "residual": r.residual}

    recon = {"currency": CURRENCY, "tolerance": 1e-06, "allowance": [row(r) for r in rf.allowance],
             "gross_carrying_amount": [row(r) for r in rf.gca]}
    wf = {"currency": CURRENCY, "lines": rf.waterfall}
    return recon, wf


def overlay_rows(overlays: list[Overlay]) -> list[dict[str, Any]]:
    return [{"id": o.id, "currency": o.currency, "rationale": t(o.rationale_en, o.rationale_es), "method": o.method, "target": o.target,
             "segment_id": o.segment_id, "stage": o.stage, "amount": o.amount, "staging_effect": o.staging_effect,
             "review_date": o.review_date} for o in overlays]


def scenario_direction(run: DateRun) -> int:
    """+1 when the weighted macro path worsens (the unemployment rate over the next four quarters above its current
    value), -1 when it improves, 0 otherwise."""
    now = run.history.at(run.history.last)[0]
    ahead = float(np.mean(run.macro_mean_path[:4, 0]))
    return 1 if ahead > now + 0.1 else -1 if ahead < now - 0.1 else 0


def implied_multiplier(run: DateRun) -> float:
    """The policy multiplier in force, averaged over the book by gross carrying amount: the schedule read at each
    account's origination PD."""
    uppers = np.array([u for u, _ in POLICY.multiplier_schedule])
    mult = np.array([m for _, m in POLICY.multiplier_schedule])
    k = np.minimum(np.searchsorted(uppers, run.pd_orig_ann, side="left"), len(mult) - 1)
    return float(np.average(mult[k], weights=run.gca))


# ---------------------------------------------------------------------------------------------------------------------
# the findings


def _g3(x: float) -> str:
    """``x`` to three significant digits with the Spanish decimal comma (the English side writes ``{x:.3g}``)."""
    return f"{x:.3g}".replace(".", ",")


def findings(tests: list[dict[str, Any]], run: DateRun, ecl_by_scen_total: np.ndarray, stage_summary: dict[str, Any],
             lifetime_left_out: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def key(tr: dict[str, Any]) -> str:
        k = tr["test_id"]
        if tr.get("model_id"):
            k += "@" + tr["model_id"]
            if tr.get("segment"):
                k += "@" + tr["segment"]
        return k

    def add(fid, sev, status, ev, en, es):
        out.append({"id": fid, "severity": sev, "status": status, "evidence": ev, "title": t(en, es)})

    by = {}
    for tr in tests:
        by.setdefault(tr["test_id"], []).append(tr)
    lb = [r for r in by.get("ifrs9.lifetime_pd_backtest", []) if r["model_id"] == "L1-dth" and r["segment"] == "all"]
    if lb and lb[0]["light"] in ("amber", "red") and lb[0]["metric"] is not None:
        add("F-LIFETIME-GAP", "S2" if lb[0]["light"] == "red" else "S3", "open", [key(lb[0])],
            f"The lifetime PD of the hazard rung misses the observed cumulative default by up to {100 * lb[0]['metric']:.1f} points over all loans pooled ({lb[0]['light']})",
            f"La PD de vida completa del hazard se aparta del incumplimiento acumulado observado hasta {tx.number(100 * lb[0]['metric'], 1, lang='es')} puntos con todos los préstamos agrupados ({tx.light(lb[0]['light'], 'es')})")
    for tid, fid, en, es in (
        ("ifrs9.sicr_effectiveness", "F-SICR", "The Stage 2 flag against defaults and performing loans", "La marca de Etapa 2 frente a los incumplimientos y los préstamos sanos"),
        ("ifrs9.ecl_backtest", "F-ECL-BACKTEST", "The 12-month ECL against the losses realised after the date", "La PCE a 12 meses frente a las pérdidas realizadas después de la fecha"),
        ("ifrs9.stage_migration_backtest", "F-MIGRATION", "The predicted stage migration against the observed one", "La migración de etapas prevista frente a la observada"),
    ):
        r = by.get(tid, [None])[0]
        if r is not None and r["light"] in ("amber", "red", "not_evaluated"):
            sev = "S2" if r["light"] == "red" else "S3"
            val = "not evaluated" if r["light"] == "not_evaluated" else f"metric {r['metric']:.3g}" if r["metric"] is not None else f"p {r['p_value']:.3g}"
            val_es = ("no evaluada" if r["light"] == "not_evaluated" else f"métrica {_g3(r['metric'])}" if r["metric"] is not None
                      else f"p {_g3(r['p_value'])}")
            add(f"{fid}-{r['light']}", sev if r["light"] != "not_evaluated" else "S4", "open", [key(r)],
                f"{en}: {r['light']} ({val})", f"{es}: {tx.light(r['light'], 'es')} ({val_es})" if r["light"] != "not_evaluated" else f"{es}: no evaluada")
    if ecl_by_scen_total[-1] < ecl_by_scen_total[0]:
        add("F-SCENARIO-ORDER", "S2", "open", ["ifrs9.scenario_sensitivity@L1-dth"],
            "The severely adverse scenario gives a lower ECL than the baseline: the hazard's macro sensitivities have the wrong sign at this date",
            "El escenario severamente adverso da una PCE menor que el base: las sensibilidades macro del hazard tienen el signo equivocado en esta fecha")
    rec = by.get("ifrs9.reconciliation_identities", [None])[0]
    if rec is not None and rec["light"] != "green":
        add("F-RECONCILIATION", "S1", "open", [key(rec)], "A reconciliation identity does not close", "Una identidad de la conciliación no cierra")
    add("F-NO-DELINQUENCY", "S4", "accepted", ["design:sba-no-delinquency-data"],
        "The SBA file has no delinquency, forbearance or watch-list history: only the quantitative SICR test can move a loan to Stage 2, and Stage 3 holds no balance at a date",
        "El archivo SBA no tiene historia de mora, refinanciación ni lista de vigilancia: solo la prueba cuantitativa de SICR puede pasar un préstamo a Etapa 2, y la Etapa 3 no tiene saldo en una fecha")
    add("F-LGD-PROXY", "S4", "accepted", ["design:sba-chargeoff-lgd-proxy"],
        "LGD is a charge-off severity proxy with an upward bias (the file has no recovery after the charge-off) and the ECL is before the SBA guarantee",
        "La PDI es un proxy de severidad del castigo con sesgo al alza (el archivo no tiene recuperaciones tras el castigo) y la PCE es antes de la garantía SBA")
    add("F-EAD-MODEL", "S4", "accepted", ["design:sba-modelled-balance"],
        "The balance is modelled (a level-payment annuity at the EIR; revolving lines at their approval): the file has no balance",
        "El saldo es modelado (una anualidad de cuota nivelada a la TIE; líneas rotativas a su monto aprobado): el archivo no tiene saldo")
    add("F-PREPAYMENT", "S4", "accepted", ["design:prepayment-as-censoring"],
        "Prepayment is treated as censoring: the lifetime PD is the cause-specific default hazard and carries no prepayment attrition",
        "El prepago se trata como censura: la PD de vida completa es el hazard de incumplimiento por causa y no incluye atrición por prepago")
    if lifetime_left_out:
        add("F-SHORT-LIFE", "S4", "accepted", ["design:backtest-population"],
            f"{lifetime_left_out:,} accounts with less than 33 months of contractual life left are outside the lifetime backtest",
            f"{tx.number(lifetime_left_out, 0, lang='es')} cuentas con menos de 33 meses de vida contractual quedan fuera del backtest de vida completa")
    return out


def impact_block(by_stage: dict[str, float], gca: float, overlay_total: float, nl_index: float, stage2_share: float,
                 realised_ratio: float | None) -> dict[str, Any]:
    def item(value, unit, en, es):
        return {"value": value, "unit": unit, "label": t(en, es)}

    total = float(sum(by_stage.values()))
    out = {
        "ecl_total": item(total, "USD", "Model ECL, probability-weighted", "PCE del modelo, ponderada por probabilidad"),
        "ecl_stage1": item(by_stage["stage1"], "USD", "ECL Stage 1 (12 months)", "PCE Etapa 1 (12 meses)"),
        "ecl_stage2": item(by_stage["stage2"], "USD", "ECL Stage 2 (lifetime)", "PCE Etapa 2 (toda la vida)"),
        "ecl_stage3": item(by_stage["stage3"], "USD", "ECL Stage 3", "PCE Etapa 3"),
        "coverage": item(total / gca if gca > 0 else None, "ratio", "Model ECL over the gross carrying amount", "PCE del modelo sobre el valor en libros bruto"),
        "stage2_share": item(stage2_share, "ratio", "Stage 2 share of the gross carrying amount", "Participación de la Etapa 2 en el valor en libros bruto"),
        "overlay_total": item(overlay_total, "USD", "Overlays, separate lines", "Ajustes posteriores, líneas separadas"),
        "nl_index": item(nl_index, "ratio", "Non-linearity of the ECL in the scenarios", "No linealidad de la PCE en los escenarios"),
    }
    if realised_ratio is not None:
        out["ecl_backtest_ratio"] = item(realised_ratio, "ratio", "Realised 12-month losses over the 12-month ECL", "Pérdidas realizadas a 12 meses sobre la PCE a 12 meses")
    return out


#: what a reader should see, declared per reporting date before the committed bake and checked by it (the bake fails naming a
#: result outside its range). The bases are in docs/cases/C06.md: the accounts are the book of the date (the SBA loans open at it,
#: about 250 to 310 thousand); the coverage is the model ECL over the gross carrying amount; the Stage 2 share is of the gross
#: carrying amount.
EXPECT: dict[str, tuple[float, float]] = {
    "accounts@2006-12-31": (295_000, 315_000), "coverage@2006-12-31": (0.007, 0.013), "stage2_share@2006-12-31": (0.0, 0.01),
    "accounts@2008-12-31": (300_000, 322_000), "coverage@2008-12-31": (0.014, 0.024), "stage2_share@2008-12-31": (0.0, 0.03),
    "accounts@2010-12-31": (270_000, 290_000), "coverage@2010-12-31": (0.048, 0.080), "stage2_share@2010-12-31": (0.45, 0.68),
    "accounts@2019-12-31": (262_000, 282_000), "coverage@2019-12-31": (0.0043, 0.0075), "stage2_share@2019-12-31": (0.0, 0.01),
    "accounts@2020-06-30": (259_000, 278_000), "coverage@2020-06-30": (0.15, 0.25), "stage2_share@2020-06-30": (0.90, 1.0),
    "accounts@2023-06-30": (243_000, 260_000), "coverage@2023-06-30": (0.005, 0.0085), "stage2_share@2023-06-30": (0.0, 0.01),
}
