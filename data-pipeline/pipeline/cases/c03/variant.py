"""One variant of C03: a test cohort of approval fiscal years, baked into its ``vintage-cohort`` document (CT-802 to CT-810).

The champion rung (the WoE scorecard) gives the vintage curves, the vintage rows, the calibration deciles and the stability rows;
every rung is compared on the pooled vintages whose 5-year mark is observed; the validation rows are the engine's
(``evaluate``). A vintage whose mark is not observed at the observation date carries no observed 5-year value: null, with the
reason, in its row, its curve and its stability row. A cohort with no observed mark at all has nothing to calibrate against and
is refused, never filled.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ...core import text as tx
from ..c01_ladder import SHORT_TITLES
from ..c06.panel import months_between
from . import evaluate, fit, models, panel, windows
from .fit import MONTHS, WindowFit

CURRENCY = "USD"
CHAMPION = "P1-scorecard"
PRIMARY_SOURCE = "sba-7a"
CRISIS_TEXT = ("December 2007 to June 2009", "diciembre de 2007 a junio de 2009")
#: (finding family, tests, severity when a test is red, when amber). The level of the PD (is the average right) weighs more than
#: its fit across the range, which at thousands of loans rejects for deviations too small to matter.
SEVERITY: tuple[tuple[str, str, tuple[str, ...], str, str], ...] = (
    ("calibration level", "nivel de calibración", ("pd.jeffreys", "pd.binomial", "pd.binomial_vasicek"), "S2", "S3"),
    ("calibration fit", "ajuste de calibración", ("pd.hosmer_lemeshow", "pd.spiegelhalter"), "S3", "S4"),
    ("stability", "estabilidad", ("stability.psi",), "S2", "S3"),
    ("discrimination", "discriminación", ("disc.auc_vs_initial",), "S2", "S3"),
)


def t(en: str, es: str) -> dict[str, str]:
    return {"en": en, "es": es}


@dataclass
class CohortResult:
    variant_id: str
    cohort: windows.Cohort
    document: dict[str, Any]          # the variant document without provenance and lane (the case adds them)
    values: dict[str, float]          # the scalars the expected ranges judge
    fit: WindowFit
    crisis_events: int
    window_counts: dict[str, int]


def target_block() -> dict[str, Any]:
    return {
        "name": "charged-off-within-60-months", "horizon_months": 60, "observed_at_months": 60, "censoring": "exempt-right-censored",
        "definition": t(
            "A loan is an event when the file shows it charged off within 60 months of approval, on or before the observation date. "
            "The target of a vintage is read only at its 5-year mark (30 September of the fiscal year plus 5). A loan observed for "
            "the whole 60 months without a charge-off, paid in full, charged off later or still active, is a non-event: the file "
            "shows a charge-off as CHGOFF, never as an active loan. A loan observed for less than 60 months and not charged off "
            "(EXEMPT, active) is right-censored: it has no outcome, is counted apart and is never counted as performing.",
            "Un crédito es evento cuando el archivo lo muestra castigado dentro de los 60 meses desde la aprobación, hasta la fecha "
            "de observación. El objetivo de una cosecha se lee solo en su marca de 5 años (30 de septiembre del año fiscal más 5). "
            "Un crédito observado los 60 meses completos sin castigo, pagado, castigado después o aún vigente, es un no evento: el "
            "archivo muestra un castigo como CHGOFF, nunca como crédito vigente. Un crédito observado menos de 60 meses y sin "
            "castigo (EXEMPT, vigente) es censurado por la derecha: no tiene resultado, se cuenta aparte y nunca se cuenta como "
            "vigente sano."),
    }


def data_status_block(observed_at: str) -> dict[str, Any]:
    return {
        "primary_source": PRIMARY_SOURCE, "files_as_of": observed_at, "fiscal_year_start": "10-01",
        "notice": t(
            "The SBA 7(a) loans are loans to small businesses made by lenders under a federal guarantee program, not the SME book of a "
            "bank: the file has no delinquency history, no balance and no rating, and the sample is not a bank's portfolio. The "
            "interest rate is recorded only from the FY2008 approvals and is not a model input.",
            "Los créditos SBA 7(a) son créditos a pequeñas empresas otorgados por prestamistas bajo un programa federal de garantía, "
            "no la cartera pyme de un banco: el archivo no tiene historia de mora, saldo ni calificación, y la muestra no es la cartera "
            "de un banco. La tasa de interés se registra solo desde las aprobaciones del año fiscal 2008 y no es una entrada del modelo."),
    }


def training_block(cohort: windows.Cohort, wf: WindowFit, crisis: int) -> dict[str, Any]:
    w = wf.window
    mark = windows.five_year_mark(w.last_fy)
    en = (f"Approval fiscal years FY{w.first_fy} to FY{w.last_fy}: the 5-year mark of FY{w.last_fy} closes on {mark}, before the first "
          f"approval of {cohort.name} on {cohort.first_fy - 1}-10-01. {tx.number(wf.n_loans, lang='en')} loans with a known 5-year outcome and "
          f"{tx.number(wf.n_events, lang='en')} charge-offs; the rungs were fitted on a stratified sample of {tx.number(wf.fit_rows, lang='en')} of them. ")
    es = (f"Años fiscales de aprobación AF{w.first_fy} a AF{w.last_fy}: la marca de 5 años de AF{w.last_fy} cierra el {mark}, antes de la "
          f"primera aprobación de AF{cohort.first_fy}-{str(cohort.last_fy)[2:]} el {cohort.first_fy - 1}-10-01. {tx.number(wf.n_loans, lang='es')} créditos "
          f"con resultado a 5 años conocido y {tx.number(wf.n_events, lang='es')} castigos; los peldaños se ajustaron con una muestra estratificada de "
          f"{tx.number(wf.fit_rows, lang='es')} de ellos. ")
    if crisis > 0:
        en += (f"The window holds {tx.number(crisis, lang='en')} charge-offs dated in the recession ({CRISIS_TEXT[0]}): the model is trained through "
               "the crisis.")
        es += (f"La ventana contiene {tx.number(crisis, lang='es')} castigos fechados en la recesión ({CRISIS_TEXT[1]}): el modelo se entrena a través "
               "de la crisis.")
    else:
        en += "The window closes before the recession (December 2007): the model has seen no outcome of the crisis."
        es += "La ventana cierra antes de la recesión (diciembre de 2007): el modelo no ha visto ningún resultado de la crisis."
    return {"first_fy": w.first_fy, "last_fy": w.last_fy, "cutoff_date": w.cutoff, "n_loans": wf.n_loans, "n_events": wf.n_events,
            "crisis_included": crisis > 0, "rationale": t(en, es)}


def cohort_block(cohort: windows.Cohort) -> dict[str, Any]:
    return {"id": cohort.id, "label": t(cohort.name, f"AF{cohort.first_fy}-{str(cohort.last_fy)[2:]}"), "first_fy": cohort.first_fy,
            "last_fy": cohort.last_fy, "approval_fiscal_years": list(cohort.fiscal_years)}


def _unobserved_reason(fy: int, observed_at: str, until: int) -> str:
    return (f"the 5-year mark of FY{fy} is {windows.five_year_mark(fy)}, after the files' as-of date {observed_at}: the vintage has been "
            f"observed for {until} of 60 months")


def _deciles(p: np.ndarray, y: np.ndarray) -> list[dict[str, Any]]:
    order = np.argsort(p, kind="stable")
    rows = []
    for k, part in enumerate(np.array_split(order, min(10, len(order)))):
        n, d = int(len(part)), int(y[part].sum())
        pred = float(p[part].mean())
        lo, hi = evaluate.jeffreys_interval(n, d, pred)
        rows.append({"decile": k + 1, "n": n, "predicted_pd": pred, "observed_pd": d / n, "ci_low": lo, "ci_high": hi})
    return rows


def _findings(tests: list[dict[str, Any]], wf: WindowFit, cohort: windows.Cohort, crisis: int, champion: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for rung in dict.fromkeys((champion, "P4-lightgbm")):
        if rung not in wf.rungs:
            continue
        for family, family_es, ids, on_red, on_amber in SEVERITY:
            hit = [r for r in tests if r["model_id"] == rung and r["test_id"] in ids and r["light"] in ("red", "amber")
                   and r["segment"] == evaluate.PORTFOLIO]
            if not hit:
                continue
            sev = on_red if any(r["light"] == "red" for r in hit) else on_amber
            tag = "".join(w[0] for w in family.split()).upper()
            out.append({"id": f"F-{tag}-{rung}", "severity": sev, "status": "open", "evidence": sorted({f"{r['test_id']}@{rung}" for r in hit}),
                        # the rung by its short title and no test id: the evidence names each test (U16-R2b c04 B2)
                        "title": t(f"{SHORT_TITLES.get(rung, {'en': rung})['en']}: {family} tests flag the {cohort.name} cohort",
                                   f"{SHORT_TITLES.get(rung, {'es': rung})['es']}: las pruebas de {family_es} alertan en la cohorte AF{cohort.first_fy}-{str(cohort.last_fy)[2:]}")})
    if crisis == 0:
        out.append({"id": "F-CRISIS", "severity": "S2", "status": "open", "evidence": ["design:training-window-before-the-crisis"],
                    "title": t("The window closes before the 2007-09 recession: the rungs have seen no crisis outcome",
                               "La ventana cierra antes de la recesión de 2007-09: los peldaños no han visto ningún resultado de la crisis")})
    out.append({"id": "F-DATA", "severity": "S3", "status": "accepted", "evidence": ["design:sba-7a-is-not-a-bank-book"],
                "title": t("SBA 7(a) small-business loans under a federal guarantee, not a bank's SME book; no delinquency, balance or rating",
                           "Créditos a pequeñas empresas SBA 7(a) bajo garantía federal, no la cartera pyme de un banco; sin mora, saldo ni calificación")})
    out.append({"id": "F-CENSOR", "severity": "S4", "status": "accepted", "evidence": ["design:right-censoring"],
                "title": t("Loans observed for less than 60 months without a charge-off carry no outcome and are counted apart",
                           "Los créditos observados menos de 60 meses sin castigo no tienen resultado y se cuentan aparte")})
    return out


def bake_cohort(loans: panel.Loans, cohort: windows.Cohort, seed: int, *, observed_at=None, fit: WindowFit | None = None,
                log=None) -> CohortResult:
    from . import fit as fitting

    o = str(np.datetime64(observed_at if observed_at is not None else loans.asof, "D"))
    window = windows.training_window(cohort)
    windows.check_window(cohort, window)
    marks = {fy: windows.mark_observed(fy, o) for fy in cohort.fiscal_years}
    if not any(marks.values()):
        raise ValueError(f"{cohort.id}: no vintage of the cohort has reached its 5-year mark at {o} "
                         f"(the first is {windows.five_year_mark(cohort.first_fy)}): nothing to calibrate against")
    wf = fit if fit is not None else fitting.fit_window(loans, window, seed, log=log)
    if wf.window != window:
        raise ValueError(f"{cohort.id}: the fit was made on {wf.window}, not on the window {window}")
    crisis = windows.crisis_events(loans, window)
    ln = loans.take(np.flatnonzero(np.isin(loans.fy, cohort.fiscal_years)))
    X = panel.features(ln)
    y = panel.label(ln, o)
    pds = {rid: r.pd(X) for rid, r in wf.rungs.items()}
    champion = CHAMPION if CHAMPION in wf.rungs else "P0-constant"
    pc = pds[champion]
    pd_ref = wf.rungs[champion].pd(wf.X_fit)
    observed_end = np.datetime64(o)

    curves, rows, stability = [], [], []
    for fy in cohort.fiscal_years:
        m = ln.fy == fy
        n = int(m.sum())
        known = m & (y != panel.LABEL_CENSORED)
        n_res = int(known.sum())
        mean_p = float(pc[m].mean())
        until = max(0, int(months_between(np.datetime64(f"{fy}-09-30"), observed_end)))
        reason = None if marks[fy] else _unobserved_reason(fy, o, until)
        predicted = [mean_p * wf.timing[mm] for mm in MONTHS]
        observed = []
        for mm in MONTHS:
            if mm <= until:
                inside = ((ln.exit_kind[m] == panel.EXIT_DEFAULT) & (ln.exit_date[m] <= panel.horizon_end(ln.approval[m], mm))
                          & (ln.exit_date[m] <= observed_end))
                observed.append(float(inside.sum()) / n)
            else:
                observed.append(None)
        gross = float(ln.amount[m].sum())
        curves.append({"fiscal_year": fy, "n": n, "gross_approval": gross, "months": list(MONTHS), "predicted_cumulative_pd": predicted,
                       "observed_cumulative_pd": observed, "observed_until_month": until, "reason": reason})
        row = {"fiscal_year": fy, "n": n, "n_resolved": n_res, "n_exempt_censored": n - n_res, "gross_approval": gross,
               "five_year_mark_date": windows.five_year_mark(fy), "mark_observed": marks[fy], "observed_5y_pd": None,
               "predicted_5y_pd": predicted[-1], "gap": None, "brier": None, "auc": None, "reason": reason}
        if marks[fy]:
            if n_res != n:
                raise ValueError(f"FY{fy}: {n - n_res} loans of an observed vintage have no outcome")
            yk, pk = y[known].astype(int), pc[known]
            row["observed_5y_pd"] = float(yk.mean())
            row["gap"] = float(yk.mean()) - predicted[-1]
            row["brier"] = evaluate.brier(pk, yk)
            a = evaluate.auc(pk, yk)
            row["auc"] = a["auc"] if a else None
        rows.append(row)
        stability.append({"fiscal_year": fy, "psi": evaluate.psi(pd_ref, pc[m], model_id=champion, segment=f"fy{fy}")["metric"],
                          "observed_5y_pd": row["observed_5y_pd"]})

    # the pooled evaluation set: the loans of the vintages whose mark is observed (every one has an outcome)
    pool = np.isin(ln.fy, [fy for fy, ok in marks.items() if ok]) & (y != panel.LABEL_CENSORED)
    y_eval = y[pool].astype(int)
    pd_eval = {rid: p[pool] for rid, p in pds.items()}
    comparison = []
    for rid in fit_order(wf):
        if rid in wf.rungs:
            a = evaluate.auc(pd_eval[rid], y_eval)
            comparison.append({"rung_id": rid, "auc": a["auc"] if a else None, "auc_ci_low": a["low"] if a else None,
                               "auc_ci_high": a["high"] if a else None, "brier": evaluate.brier(pd_eval[rid], y_eval),
                               "calibration_gap_5y": float(y_eval.mean() - pd_eval[rid].mean()), "reason": None})
        else:
            comparison.append({"rung_id": rid, "auc": None, "auc_ci_low": None, "auc_ci_high": None, "brier": None,
                               "calibration_gap_5y": None, "reason": wf.not_evaluated[rid]})
    pooled_years = [fy for fy, ok in marks.items() if ok]
    scope = t(f"vintages with an observed 5-year mark: FY{pooled_years[0]}" + (f" to FY{pooled_years[-1]}" if len(pooled_years) > 1 else ""),
              f"cosechas con marca de 5 años observada: AF{pooled_years[0]}" + (f" a AF{pooled_years[-1]}" if len(pooled_years) > 1 else ""))
    calibration = {"rung_id": champion, "scope": scope, "rows": _deciles(pd_eval[champion], y_eval)}

    tests: list[dict[str, Any]] = []
    for rid, rung in wf.rungs.items():
        tests += evaluate.engine_rows(rid, pd_eval[rid], y_eval, pd_train=rung.pd(wf.X_fit), pd_cal=rung.pd(wf.X_cal), y_cal=wf.y_cal,
                                      champion_pd=None if rid == champion else pd_eval[champion])
    for fy in cohort.fiscal_years:
        if marks[fy]:
            sel = (ln.fy == fy) & (y != panel.LABEL_CENSORED)
            tests += evaluate.vintage_rows(champion, fy, pc[sel], y[sel].astype(int))
        else:
            tests.append(evaluate.not_evaluated("pd.jeffreys", champion, f"fy{fy}", _unobserved_reason(
                fy, o, max(0, int(months_between(np.datetime64(f"{fy}-09-30"), observed_end))))))

    # a loan observed for the whole horizon and still active is a non-event: how many, so the reader can judge the censoring rule
    active_alive = pool & (ln.exit_kind == panel.EXIT_OPEN)
    observed_rate = float(y_eval.mean())
    predicted_rate = float(pd_eval[champion].mean())
    training_rate = wf.n_events / wf.n_loans
    champ_auc = next(c["auc"] for c in comparison if c["rung_id"] == champion)
    impact = {
        "observed_5y_pd": {"value": observed_rate, "unit": "share", "label": t(f"Observed 5-year PD, {cohort.name}", f"PD observada a 5 años, {cohort.name}")},
        "predicted_5y_pd": {"value": predicted_rate, "unit": "share", "label": t(f"Predicted 5-year PD, {champion}", f"PD predicha a 5 años, {champion}")},
        "calibration_gap_5y": {"value": observed_rate - predicted_rate, "unit": "share", "label": t("Observed minus predicted 5-year PD", "PD a 5 años observada menos predicha")},
        "training_event_rate": {"value": training_rate, "unit": "share", "label": t("5-year charge-off rate of the training window", "Tasa de castigo a 5 años de la ventana de entrenamiento")},
        "champion_auc": {"value": champ_auc, "unit": "auc", "label": t(f"AUC of {champion} on the cohort", f"AUC de {champion} en la cohorte")},
        "active_nonevent_share": {"value": float(active_alive.sum()) / max(1, int(pool.sum())), "unit": "share",
                                  "label": t("Share of the evaluated loans still active after 60 months (counted as non-events)",
                                             "Parte de los créditos evaluados aún vigentes tras 60 meses (contados como no eventos)")},
    }
    outputs = {
        "kind": "vintage-cohort", "currency": CURRENCY, "cohort": cohort_block(cohort), "training": training_block(cohort, wf, crisis),
        "target": target_block(), "data_status": data_status_block(o), "vintage_curves": curves,
        "vintage_summary": {"currency": CURRENCY, "rows": rows}, "calibration": calibration, "rung_comparison": comparison,
        "stability": {"training_mean_5y_pd": training_rate, "rows": stability,
                      "psi_note": t("PSI of the champion's PD distribution in each vintage against the training rows (ten bins on the training "
                                    "quantiles); 0.10 and 0.25 are conventions, not limits. The observed 5-year PD against the training mean is "
                                    "the crisis contrast.",
                                    "PSI de la distribución de PD del campeón en cada cosecha contra las filas de entrenamiento (diez tramos sobre "
                                    "los cuantiles de entrenamiento); 0,10 y 0,25 son convenciones, no límites. La PD observada a 5 años contra "
                                    "la media de entrenamiento es el contraste de la crisis.")},
    }
    document = {"model": models.model_summaries(wf), "outputs": outputs, "tests": tests, "impact": impact,
                "findings": _findings(tests, wf, cohort, crisis, champion)}
    values = {f"observed_5y_pd@{cohort.id}": observed_rate, f"training_event_rate@{cohort.id}": training_rate,
              f"champion_auc@{cohort.id}": float(champ_auc)}
    return CohortResult(variant_id=cohort.id, cohort=cohort, document=document, values=values, fit=wf, crisis_events=crisis,
                        window_counts={"n_loans": wf.n_loans, "n_events": wf.n_events, "n_censored": wf.n_censored})


def fit_order(wf: WindowFit) -> list[str]:
    """The rungs in ladder order, those not fitted and the absent challenger last."""
    return [*fit.RUNG_KINDS, fit.TABPFN_ID]
