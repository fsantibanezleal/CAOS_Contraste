"""The backtests of C06 (CT-506, CT-511): what happened after the reporting date against what the model said at it.

A model for a reporting date R is trained on what is known at R and tested on the outcomes after R, up to the date the
SBA file is as of. The observed cumulative default of a group is Kaplan-Meier from R (``statsmodels`` SurvfuncRight;
prepayment and maturity censor), the same estimator the lifetime PD test names. Every statistic that judges a model (the
gap, the Brier score, the Vasicek band, the AUC, the SICR ratio, the ECL ratio, the migration chi-square) is a
``riskvalidation`` test; this module builds their inputs from the loans and reads their rows.

Population. A lifetime backtest compares curves over 36 months, so it uses the accounts with at least 12 quarters of
contractual life left (``run.horizon_q >= 12``): the others leave the book before the last horizon and would be
censored by maturity in the observation but not in the prediction. The count left out is reported.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.provisions.staging import allocate_stages
from riskvalidation.validation import ifrs9 as rv_ifrs9
from riskvalidation.validation.discrimination import disc_auc

from .ladder import Ladder
from .neural import aalen_johansen
from .panel import EXIT_DEFAULT, EXIT_PAID, Loans
from .run import BACKTEST_Q, POLICY, RHO, DateRun

HORIZONS = (6, 12, 18, 24, 30, 36)
DECILE_HORIZONS = (12, 24, 36)
MIN_COHORT = 100
DAYS_PER_MONTH = 30.4375
RUNGS = ("L0-km", "L1-dth", "L2-cox", "L3-pch")
#: the S-4 hypothesis, written before the run (method tiers plan, section 3, S-4; the unit's operationalisation of "beside Cox")
S4_HYPOTHESIS = {
    "en": ("The PC-Hazard rung (L3) predicts better than Cox (L2) out of time: a lower integrated Brier score and a smaller mean absolute "
           "decile gap against Aalen-Johansen (mean over 12, 24 and 36 months) at more than half of the reporting dates where both "
           "are observed. Refuted when it holds at half of them or fewer. The c-index is reported beside, not part of the verdict."),
    "es": ("El peldaño PC-Hazard (L3) predice mejor que Cox (L2) fuera de tiempo: un puntaje de Brier integrado menor y una brecha "
           "absoluta media por decil menor frente a Aalen-Johansen (media a 12, 24 y 36 meses) en más de la mitad de las fechas de "
           "reporte donde ambos se observan. Se refuta cuando se cumple en la mitad o menos. El índice c se informa al lado y no "
           "entra en el veredicto."),
}


@dataclass(frozen=True)
class FollowUp:
    """The accounts of a book followed from the reporting date: months to default, exit or censoring."""

    time: np.ndarray        # (A,) months from R to the last observed moment
    event: np.ndarray       # (A,) bool: charged off within the follow-up
    horizon: float          # months from R to the date the file is as of
    cause: np.ndarray       # (A,) int: 0 still open or matured at the last moment, 1 charged off, 2 paid off (the competing exit)


def follow_up(loans: Loans, run: DateRun) -> FollowUp:
    r = run.reporting_date
    idx = run.idx
    horizon = float((loans.asof - r).astype("timedelta64[D]").astype(np.int64)) / DAYS_PER_MONTH
    kind = loans.exit_kind[idx]
    t_exit = np.where(kind != 0, (loans.exit_date[idx] - r).astype("timedelta64[D]").astype(float) / DAYS_PER_MONTH, np.inf)
    t_mat = (loans.term[idx] - run.age_m).astype(float)
    is_default = kind == EXIT_DEFAULT
    event = is_default & (t_exit <= t_mat) & (t_exit <= horizon)
    paid = (kind == EXIT_PAID) & (t_exit <= t_mat) & (t_exit <= horizon)
    time = np.minimum(np.minimum(np.where(np.isfinite(t_exit), t_exit, np.inf), t_mat), horizon)
    return FollowUp(time=np.maximum(time, 0.0), event=event, horizon=horizon, cause=np.where(event, 1, np.where(paid, 2, 0)))


def km_observed(time: np.ndarray, event: np.ndarray, horizons: tuple[int, ...], follow: float) -> tuple[np.ndarray, np.ndarray]:
    """Kaplan-Meier cumulative default at each horizon in months (NaN beyond the follow-up) and the defaults up to it."""
    from statsmodels.duration.survfunc import SurvfuncRight

    obs = np.full(len(horizons), np.nan)
    ev = np.zeros(len(horizons))
    if time.size == 0:
        return obs, ev
    sf = SurvfuncRight(time + 1e-9, event.astype(int))
    times, surv = np.asarray(sf.surv_times, float), np.asarray(sf.surv_prob, float)
    for j, k in enumerate(horizons):
        ev[j] = float((event & (time <= k)).sum())
        if k > follow + 1e-9:
            continue
        pos = np.searchsorted(times, k + 1e-9, side="right") - 1
        obs[j] = 1.0 - (surv[pos] if pos >= 0 else 1.0)
    return obs, ev


def _predicted(rung: str, run: DateRun, ladder: Ladder, mask: np.ndarray, horizons: tuple[int, ...]) -> np.ndarray:
    """(accounts in mask, horizons) cumulative PD from R for one rung."""
    h = np.asarray(horizons, dtype=float)
    if rung == "L1-dth":
        cols = [k // 3 - 1 for k in horizons]
        return run.cum12[mask][:, cols]
    age = run.age_m[mask].astype(float)
    if rung == "L0-km":
        return ladder.km.cumulative(age, h)
    stratum = _stratum(run)[mask]
    if rung == "L3-pch":
        return ladder.pch.cumulative(stratum, age, h)
    return ladder.cox.cumulative(stratum, age, h)


def _stratum(run: DateRun) -> np.ndarray:
    return run.stratum


def cohort_labels(loans: Loans, run: DateRun) -> np.ndarray:
    """The origination cohort of each account of the book: its approval year for the five most recent years present,
    ``older`` before them."""
    year = loans.approval[run.idx].astype("datetime64[Y]").astype(np.int64) + 1970
    top = int(year.max())
    return np.where(year > top - 5, year.astype(str), "older")


def clean(x: np.ndarray) -> np.ndarray:
    return np.clip(x, 1e-9, 1.0 - 1e-9)


@dataclass
class LifetimeResults:
    tests: list[dict[str, Any]]
    rows: list[dict[str, Any]]
    rung_comparison: list[dict[str, Any]]
    deciles: list[dict[str, Any]]
    eligible: int
    left_out: int


def _thin(n: int, defaults: int) -> str | None:
    if n < MIN_COHORT:
        return f"{n} accounts, fewer than the {MIN_COHORT} a cohort test needs"
    return None


def lifetime_results(loans: Loans, run: DateRun, follow: FollowUp) -> LifetimeResults:
    ladder = run.ladder
    elig = run.horizon_q >= BACKTEST_Q
    labels = cohort_labels(loans, run)
    groups: dict[str, np.ndarray] = {"all": elig}
    for lab in sorted(set(labels.tolist()) - {"older"}) + (["older"] if "older" in labels else []):
        groups[lab] = elig & (labels == lab)
    tests: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    cmp_rows: list[dict[str, Any]] = []
    status = {"L0-km": ladder.km.status, "L1-dth": ladder.dth.status, "L2-cox": ladder.cox.status, "L3-pch": ladder.pch.status}
    all_results: dict[str, Any] = {}
    for rung in RUNGS:
        if not status[rung].evaluated:
            continue
        for lab, mask in groups.items():
            n = int(mask.sum())
            reason = _thin(n, int(follow.event[mask].sum()))
            if reason is not None:
                if rung == "L1-dth":
                    for k in HORIZONS:
                        rows.append(_row(lab, k, None, None, None, None, f"cohort not evaluated: {reason}"))
                continue
            pred = clean(_predicted(rung, run, ladder, mask, HORIZONS).mean(axis=0))
            obs, ev = km_observed(follow.time[mask], follow.event[mask], HORIZONS, follow.horizon)
            res = rv_ifrs9.lifetime_pd_backtest(np.asarray(HORIZONS), pred, obs, np.full(len(HORIZONS), float(n)), ev, rho=RHO,
                                                competing_prepayment=False, model_id=rung, segment=lab)
            tests.append(res.to_dict())
            if lab == "all":
                all_results[rung] = res
            if rung == "L1-dth":
                x = res.extras
                seen = dict(zip(x.get("months", []), range(len(x.get("months", []))), strict=False))
                for j, k in enumerate(HORIZONS):
                    if k in seen:
                        i = seen[k]
                        rows.append(_row(lab, k, float(pred[j]), float(obs[j]), float(x["signed_gap"][i]), float(x["brier"][i]), None))
                    else:
                        rows.append(_row(lab, k, float(pred[j]), None, None, None,
                                         "the horizon is beyond the last date the file is as of (follow-up "
                                         f"{follow.horizon:.1f} months)"))
    # rung comparison: discrimination of the 12-month PD, integrated Brier and the 12-month gap, all from the engine
    complete = follow.event & (follow.time <= 12.0) | (follow.time >= 12.0)
    for rung in RUNGS:
        if not status[rung].evaluated:
            cmp_rows.append({"rung_id": rung, "c_index": None, "integrated_brier": None, "calibration_gap_12m": None,
                             "reason": {"en": str(status[rung].reason), "es": f"peldaño no evaluado (motivo del motor: {status[rung].reason})"}})
            continue
        res = all_results.get(rung)
        c_index, reason = None, None
        if rung == "L0-km":
            reason = {"en": "Kaplan-Meier is one pooled curve by loan age: its ranking is the age ranking, no c-index is reported",
                      "es": "Kaplan-Meier es una sola curva agrupada por antigüedad del préstamo: su orden es el orden por antigüedad y no se informa índice c"}
        else:
            m = elig & complete
            pred12 = _predicted(rung, run, ladder, m, (12,))[:, 0]
            y = (follow.event[m] & (follow.time[m] <= 12.0)).astype(int)
            if 0 < y.sum() < y.size:
                c_index = float(disc_auc(pred12, y, model_id=rung, segment="all").metric)
            else:
                reason = {"en": "no default or no survivor within 12 months among the accounts followed: the c-index is undefined",
                          "es": "ningún incumplimiento o ningún sobreviviente a 12 meses entre las cuentas seguidas: el índice c no está definido"}
        brier = gap12 = None
        if res is not None and res.extras.get("brier"):
            brier = float(np.mean(res.extras["brier"]))
            months = list(res.extras["months"])
            if 12 in months:
                gap12 = float(res.extras["signed_gap"][months.index(12)])
        elif res is None:
            reason = (reason + "; " if reason else "") + "no horizon of the backtest is observed yet"
        cmp_rows.append({"rung_id": rung, "c_index": c_index, "integrated_brier": brier, "calibration_gap_12m": gap12, "reason": reason})
    # deciles of the production rung's predicted risk
    deciles: list[dict[str, Any]] = []
    if status["L1-dth"].evaluated and elig.any():
        for k in DECILE_HORIZONS:
            pk = _predicted("L1-dth", run, ladder, elig, (k,))[:, 0]
            order = np.argsort(pk, kind="stable")
            parts = np.array_split(order, 10)
            sub_t, sub_e = follow.time[elig], follow.event[elig]
            for d, part in enumerate(parts, start=1):
                n = int(part.size)
                pred = float(np.clip(pk[part].mean(), 1e-9, 1 - 1e-9)) if n else 1e-9
                obs, _ = km_observed(sub_t[part], sub_e[part], (k,), follow.horizon)
                o = None if not np.isfinite(obs[0]) else float(obs[0])
                why = None if o is not None else "the horizon is beyond the last date the file is as of"
                if n < MIN_COHORT:
                    o, why = None, f"{n} accounts in the decile, fewer than {MIN_COHORT}"
                deciles.append({"origination_cohort": "all", "months": k, "decile": d, "n": n, "estimator": "kaplan-meier",
                                "predicted_cumulative_pd": pred, "observed_cumulative_pd": o, "reason": why})
    return LifetimeResults(tests=tests, rows=rows, rung_comparison=cmp_rows, deciles=deciles, eligible=int(elig.sum()),
                           left_out=int((~elig).sum()))


def decile_calibration_rows(rung: str, run: DateRun, follow: FollowUp) -> list[dict[str, Any]]:
    """Calibration of one rung at 12, 24 and 36 months per predicted-risk decile, on the accounts with a full 36-month life: the
    mean predicted cumulative PD against the observed one by two estimators, Kaplan-Meier (prepayment censors, the estimand of a
    cause-specific hazard) and Aalen-Johansen (prepayment competes, the cumulative incidence a book actually shows). A cell
    beyond the follow-up or thinner than ``MIN_COHORT`` accounts is null with its reason, never filled."""
    elig = run.horizon_q >= BACKTEST_Q
    rows: list[dict[str, Any]] = []
    if not elig.any():
        return rows
    sub_t, sub_e, sub_c = follow.time[elig], follow.event[elig], follow.cause[elig]
    for k in DECILE_HORIZONS:
        pk = _predicted(rung, run, run.ladder, elig, (k,))[:, 0]
        parts = np.array_split(np.argsort(pk, kind="stable"), 10)
        for d, part in enumerate(parts, start=1):
            n = int(part.size)
            pred = float(np.clip(pk[part].mean(), 1e-9, 1 - 1e-9)) if n else 1e-9
            km = aj = None
            reason = None
            if k > follow.horizon + 1e-9:
                reason = {"en": f"the {k}-month horizon is beyond the last date the file is as of (follow-up {follow.horizon:.1f} months)",
                          "es": f"el horizonte de {k} meses supera la última fecha de corte del archivo (seguimiento de {follow.horizon:.1f} meses)"}
            elif n < MIN_COHORT:
                reason = {"en": f"{n} accounts in the decile, fewer than the {MIN_COHORT} a cohort test needs",
                          "es": f"{n} cuentas en el decil, menos de las {MIN_COHORT} que necesita una prueba de cohorte"}
            else:
                km = float(km_observed(sub_t[part], sub_e[part], (k,), follow.horizon)[0][0])
                aj = float(aalen_johansen(sub_t[part], sub_c[part], np.array([float(k)]), target=1)[0])
            rows.append({"months": k, "decile": d, "n": n, "predicted_cumulative_pd": pred, "observed_kaplan_meier": km,
                         "observed_aalen_johansen": aj, "gap_kaplan_meier": None if km is None else pred - km,
                         "gap_aalen_johansen": None if aj is None else pred - aj, "reason": reason})
    return rows


def _mean_abs_gap(rows: list[dict[str, Any]], key: str) -> tuple[list[float | None], float | None]:
    per = []
    for k in DECILE_HORIZONS:
        gaps = [abs(r[key]) for r in rows if r["months"] == k and r[key] is not None]
        per.append(float(np.mean(gaps)) if gaps else None)
    seen = [g for g in per if g is not None]
    return per, (float(np.mean(seen)) if seen else None)


@dataclass
class S4Evaluation:
    """The S-4 evaluation of one reporting date: the deciles of the Cox and PC-Hazard rungs and the PC-Hazard summary."""

    deciles: dict[str, list[dict[str, Any]]]
    summary: dict[str, Any]


def s4_evaluation(run: DateRun, follow: FollowUp, life: LifetimeResults) -> S4Evaluation | None:
    """PC-Hazard beside Cox on this date: c-index, integrated Brier and the decile gap against Aalen-Johansen, and each criterion
    of ``S4_HYPOTHESIS`` as true, false or null (null: one side not observed). None when the PC-Hazard rung was not fitted."""
    if not run.ladder.pch.status.evaluated:
        return None
    deciles = {r: decile_calibration_rows(r, run, follow) for r in ("L2-cox", "L3-pch")}
    cmp = {r["rung_id"]: r for r in life.rung_comparison}
    gaps = {}
    for rung, tag in (("L3-pch", "pch"), ("L2-cox", "cox")):
        gaps[tag], gaps[f"{tag}_mean"] = _mean_abs_gap(deciles[rung], "gap_aalen_johansen")
    gaps_km = {}
    for rung, tag in (("L3-pch", "pch"), ("L2-cox", "cox")):
        gaps_km[tag], gaps_km[f"{tag}_mean"] = _mean_abs_gap(deciles[rung], "gap_kaplan_meier")

    def lower(a: float | None, b: float | None) -> bool | None:
        return None if a is None or b is None else bool(a < b)

    ibs_p, ibs_c = cmp["L3-pch"]["integrated_brier"], cmp["L2-cox"]["integrated_brier"]
    ci_p, ci_c = cmp["L3-pch"]["c_index"], cmp["L2-cox"]["c_index"]
    crit = {"lower_integrated_brier": lower(ibs_p, ibs_c), "smaller_decile_gap": lower(gaps["pch_mean"], gaps["cox_mean"]),
            "higher_c_index": lower(ci_c, ci_p)}
    both = [crit["lower_integrated_brier"], crit["smaller_decile_gap"]]
    holds = None if any(v is None for v in both) else bool(all(both))
    summary = {"comparator": "L2-cox", "hypothesis": S4_HYPOTHESIS, "eligible_accounts": life.eligible, "left_out_accounts": life.left_out,
               "defaults_followed": int(follow.event[run.horizon_q >= BACKTEST_Q].sum()), "follow_up_months": float(follow.horizon),
               "c_index": {"pch": ci_p, "cox": ci_c}, "integrated_brier": {"pch": ibs_p, "cox": ibs_c},
               "mean_abs_decile_gap_aalen_johansen": {"months": list(DECILE_HORIZONS), **gaps},
               "mean_abs_decile_gap_kaplan_meier": {"months": list(DECILE_HORIZONS), **gaps_km},
               "criteria": crit, "holds_at_date": holds}
    return S4Evaluation(deciles=deciles, summary=summary)


def s4_verdict(holds_by_date: list[bool | None]) -> dict[str, Any]:
    """The verdict on ``S4_HYPOTHESIS`` over the reporting dates: it holds when both criteria hold at more than half of the dates
    where both rungs are observed, and is refuted when it holds at half of them or fewer (a date with no observed horizon is
    counted as not evaluable, never as a failure). ``verdict`` is None when no date is evaluable."""
    evaluable = [h for h in holds_by_date if h is not None]
    n, k = len(evaluable), sum(1 for h in evaluable if h)
    return {"dates": len(holds_by_date), "evaluable": n, "holds_at": k,
            "verdict": None if n == 0 else ("holds" if 2 * k > n else "refuted")}


def _row(cohort: str, months: int, pred: float | None, obs: float | None, gap: float | None, brier: float | None,
         reason: str | None) -> dict[str, Any]:
    return {"origination_cohort": cohort, "months": months, "estimator": "kaplan-meier",
            "predicted_cumulative_pd": pred if pred is not None else 1e-9, "observed_cumulative_pd": obs, "gap": gap,
            "brier": brier, "reason": reason}


def run_sicr_effectiveness(run: DateRun, follow: FollowUp, k_months: int = 12) -> dict[str, Any]:
    """The Stage 2 flag against the default within ``k_months`` after the reporting date (engine test). The file has no
    stage between dates, so the months in Stage 2 before a default are the months to the default for an account in Stage 2
    at R (an upper bound) and no account was in Stage 2 only by the backstop (there is no delinquency data)."""
    ok = follow.horizon >= k_months
    stage = run.stage.astype(float)
    defaulted = follow.event & (follow.time <= k_months)
    months = np.where(defaulted & (stage == 2.0), follow.time, 0.0)
    res = rv_ifrs9.sicr_effectiveness(stage, defaulted, k_months, months, defaulted & (stage == 1.0), np.zeros(stage.size, dtype=bool),
                                      model_id="L1-dth")
    d = res.to_dict()
    d["extras"]["product_note"] = ("the file has no stage between reporting dates: months in Stage 2 are the months to default of "
                                   "an account in Stage 2 at the reporting date (an upper bound); a default of a Stage 1 account is "
                                   "counted as a direct move to Stage 3; no delinquency data, so no backstop-only share")
    d["extras"]["follow_up_months"] = follow.horizon
    return d if ok else _unobserved(d, k_months, follow.horizon)


def _unobserved(row: dict[str, Any], k: int, horizon: float) -> dict[str, Any]:
    row = dict(row)
    row.update({"light": "not_evaluated", "metric": None, "statistic": None,
                "notes": f"not evaluated: the {k}-month window after the reporting date is beyond the file's as-of date ({horizon:.1f} months)"})
    return row


def run_ecl_backtest(run: DateRun, loans: Loans, follow: FollowUp, horizon_months: int = 12) -> dict[str, Any]:
    """Discounted realised losses within ``horizon_months`` after R against the model's 12-month ECL for the same accounts,
    overlays excluded (engine test). The realised loss is the amount charged off (the file has no recovery), discounted at
    the account's EIR to R."""
    if follow.horizon < horizon_months:
        return _unobserved(rv_ifrs9.ecl_backtest(np.zeros(1), np.ones(1), horizon_months, model_id="L1-dth").to_dict(),
                           horizon_months, follow.horizon)
    inside = follow.event & (follow.time <= horizon_months)
    coa = loans.chargeoff_amount[run.idx]
    loss = np.where(inside, np.where(np.isfinite(coa), coa, run.gca), 0.0)
    pv = loss * (1.0 + run.eir) ** (-np.minimum(follow.time, horizon_months) / 12.0)
    ecl = run.weighted(run.ecl12)
    return rv_ifrs9.ecl_backtest(pv, ecl, horizon_months, model_id="L1-dth").to_dict()


def stage_migration(run0: DateRun, run1: DateRun) -> dict[str, Any]:
    """Predicted against observed stage transitions of the accounts of the opening book that were neither repaid nor
    matured (engine test). The prediction is the opening model's: each account's 12-month PD for the move to Stage 3 and,
    for the rest, the stage its projected annualised PDs give one year on (the same policy)."""
    ok = np.isfinite(run0.proj_cur_ann) & np.isfinite(run0.proj_orig_ann)
    a = run0.a
    proj = allocate_stages(np.where(ok, run0.proj_orig_ann, 0.01), np.where(ok, run0.proj_cur_ann, 0.01), np.zeros(a, dtype=np.int64),
                           np.zeros(a, dtype=bool), np.zeros(a, dtype=bool), np.zeros(a, dtype=bool), POLICY).stage
    kinds = run1.obs.end_kind[run0.idx]
    used = ok & ~((kinds == EXIT_PAID) | (kinds == 3))
    in1 = np.isin(run0.idx, run1.idx, assume_unique=True)
    order = np.argsort(run1.idx)
    pos = order[np.clip(np.searchsorted(run1.idx[order], run0.idx), 0, run1.a - 1)]
    to_state = np.where(kinds == EXIT_DEFAULT, 3, np.where(in1, run1.stage[pos], 0))
    pred = np.zeros((3, 3))
    obs = np.zeros((3, 3), dtype=np.int64)
    for s in (1, 2):
        m = used & (run0.stage == s)
        if not m.any():
            continue
        pd = np.clip(run0.pd12[m], 0.0, 1.0)
        pred[s - 1, 2] = pd.mean()
        pred[s - 1, 1] = ((1 - pd) * (proj[m] == 2)).mean()
        pred[s - 1, 0] = ((1 - pd) * (proj[m] == 1)).mean()
        for t in (1, 2, 3):
            obs[s - 1, t - 1] = int(((to_state == t) & m).sum())
    pred[2, 2] = 1.0
    pred[pred.sum(axis=1) == 0.0] = [1.0, 0.0, 0.0]
    return rv_ifrs9.stage_migration_backtest(pred / pred.sum(axis=1, keepdims=True), obs, model_id="L1-dth").to_dict()
