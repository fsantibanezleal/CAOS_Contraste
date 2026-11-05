"""Builds the six U6-S fixture documents (docs/contracts/fixtures/c03, c08 and c09).

Run: ``python tests/contracts_u6/build_fixtures.py``. Deterministic, standard library only. The numbers are round and
small on purpose; they satisfy the identities the engine contract promises (docs/contracts/engine/lgd-ead-api.md) but are
fixtures, never results: every document is labelled ``fixture`` in its provenance and its ids.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "docs" / "contracts" / "fixtures"


def r(x: float, d: int = 9) -> float:
    return round(x, d)


def txt(en: str, es: str) -> dict:
    return {"en": en, "es": es}


def flagged(v: float) -> dict:
    return {"value": v, "flag": "below-zero" if v < 0 else "above-one" if v > 1 else "in-range"}


def envelope_common(truth: str) -> dict:
    return {
        "provenance": {
            "truth_status": truth,
            "inputs": [{"source": "fixture-not-a-result", "class": "fixture", "files": []}],
            "licence_classes": {"fixture-not-a-result": "fixture"},
            "generators": ["fixture:u6-s-contracts"],
            "seed": 0,
            "code_version": "fixture",
            "riskvalidation_version": None,
        },
        "lane": {"lane": "precompute", "reasons": ["fixture"]},
    }


def test_row(test_id: str, model_id: str, reason: str) -> dict:
    """A not_evaluated row: statistic, p_value and metric are null and the reason sits in notes (never a placeholder number)."""
    return {
        "test_id": test_id, "model_id": model_id, "segment": None, "statistic": None, "p_value": None,
        "metric": None, "h0": "fixture row", "alternative": "fixture row", "policy_version": "fixture",
        "alpha_amber": None, "alpha_red": None, "light": "not_evaluated", "n": None, "n_events": None,
        "inputs_hash": "0" * 64, "reference": "fixture, not a result", "notes": reason, "extras": {},
    }


def model_summary(mid: str, family: str, rung: str) -> dict:
    return {
        "id": mid, "family": family, "rung": rung,
        "title": txt(f"Fixture model {mid}", f"Modelo de ejemplo {mid}"),
        "short_title": txt(mid, mid), "engine": "riskvalidation", "engine_version": "fixture",
        "licence": "MIT", "calibration": None, "parameters": {}, "checkpoint_sha256": None,
    }


def model_record(mid: str, family: str, rung: str) -> dict:
    d = model_summary(mid, family, rung)
    d["details"] = {}
    return d


NE = "fixture: the test did not run, no number stands in for it"
FIXTURE_NOTICE = txt("Fixture, not a result. Round numbers for the contract.",
                     "Ejemplo, no es un resultado. Numeros redondos para el contrato.")


# ------------------------------------------------------------------------------------------------------- C03

C03_TARGET = {
    "name": "charged-off-within-60-months", "horizon_months": 60, "observed_at_months": 60,
    "censoring": "exempt-right-censored",
    "definition": txt("A loan counts as an event when it is charged off within 60 months of approval; the target of a vintage is "
                      "read only at its 5-year mark. EXEMPT (active) loans are right-censored.",
                      "Un credito es evento si se castiga dentro de 60 meses desde la aprobacion; el objetivo de una cosecha se "
                      "lee solo en su marca de 5 anos. Los creditos EXEMPT (vigentes) son censurados por la derecha."),
}
C03_TRAINING = {
    "first_fy": 1991, "last_fy": 2012, "cutoff_date": "2017-09-30", "n_loans": 600000, "n_events": 54000,
    "crisis_included": True,
    "rationale": txt("Fixture: trained on vintages whose 5-year mark closed before the cutoff, so the crisis defaults are in the "
                     "training outcomes.",
                     "Ejemplo: entrenado con cosechas cuya marca de 5 anos cerro antes del corte, de modo que los incumplimientos "
                     "de la crisis estan en los resultados de entrenamiento."),
}
C03_STATUS = {
    "primary_source": "sba-7a", "files_as_of": "2024-06-30", "fiscal_year_start": "10-01",
    "notice": txt("Fixture, not a result. The as-of date is a fixture value so that two vintages show an unobserved 5-year mark.",
                  "Ejemplo, no es un resultado. La fecha de corte es un valor de ejemplo para que dos cosechas muestren una marca de 5 anos no observada."),
}
C03_MONTHS = [12, 24, 36, 48, 60]
C03_VINTAGES = [
    # fiscal_year, n, resolved, gross approval, predicted, observed (None = unobserved), observed_until_month
    (2018, 24000, 22800, 5.1e9, [0.012, 0.031, 0.052, 0.071, 0.087], [0.010, 0.027, 0.049, 0.074, 0.092], 69),
    (2019, 25000, 22000, 5.6e9, [0.011, 0.029, 0.050, 0.068, 0.083], [0.009, 0.026, 0.047, 0.066, None], 57),
    (2020, 21000, 15000, 4.4e9, [0.010, 0.027, 0.046, 0.063, 0.077], [0.006, 0.018, 0.033, None, None], 45),
]


C03_WINDOWS = [("fy2006-07", 2006, 2007), ("fy2008-10", 2008, 2010), ("fy2011-14", 2011, 2014), ("fy2015-17", 2015, 2017),
               ("fy2018-20", 2018, 2020)]


def window(wid: str, first_fy: int, last_fy: int) -> dict:
    """A test cohort with its training window (decision D1): training stops at the last approval year whose 5-year charge-off
    mark precedes the first approval date of the cohort, last_fy = first_fy - 6; the crisis outcomes (the 2007-2010
    charge-offs) enter the training only from the FY2011-14 cohort on."""
    t_last = first_fy - 6
    return {
        "id": wid, "label": txt(f"FY{first_fy}-{str(last_fy)[2:]}", f"AF{first_fy}-{str(last_fy)[2:]}"),
        "first_fy": first_fy, "last_fy": last_fy,
        "training": {
            "first_fy": 1991, "last_fy": t_last, "cutoff_date": f"{t_last + 5}-09-30",
            "n_loans": 40000 * (t_last - 1990), "n_events": 3600 * (t_last - 1990),
            "crisis_included": t_last + 5 >= 2008,
            "rationale": txt(f"Fixture: vintages up to FY{t_last}, whose 5-year mark closes on {t_last + 5}-09-30, before the first "
                             f"approval of FY{first_fy}.",
                             f"Ejemplo: cosechas hasta AF{t_last}, cuya marca de 5 anos cierra el {t_last + 5}-09-30, antes de la "
                             f"primera aprobacion de AF{first_fy}."),
        },
    }


# BS-15 (D15): the e-process block of the fixture cohort, built once by pipeline.cases.c03.sequential.build on the fixture curves
C03_SEQUENTIAL = {'engine': 'riskvalidation.validation.sequential',
 'engine_version': '1.1.0',
 'alpha_level': 0.05,
 'threshold': 20.0,
 'direction': 'upper',
 'headline': 'average',
 'months': [12, 24, 36, 48, 60],
 'vintages': [{'fiscal_year': 2018,
               'n': 24000,
               'months_observed': 60,
               'defaults': 2208,
               'predicted_defaults': 2088.0,
               'rejection_month': None,
               'max_log_e': -15.059944,
               'log_e': [-15.49052, -31.402648, -35.364041, -17.300215, -15.059944],
               'five_year_light': None,
               'months_before_the_mark': None},
              {'fiscal_year': 2019,
               'n': 25000,
               'months_observed': 48,
               'defaults': 1650,
               'predicted_defaults': 1700.0,
               'rejection_month': None,
               'max_log_e': -15.616559,
               'log_e': [-15.616559, -27.347714, -35.908006, -38.801113, None],
               'five_year_light': None,
               'months_before_the_mark': None},
              {'fiscal_year': 2020,
               'n': 21000,
               'months_observed': 36,
               'defaults': 693,
               'predicted_defaults': 966.0,
               'rejection_month': None,
               'max_log_e': -20.511167,
               'log_e': [-20.511167, -44.844727, -66.200079, None, None],
               'five_year_light': None,
               'months_before_the_mark': None}],
 'average': {'log_e': [-15.953518, -28.429139, -36.004948, -18.398828, -16.158556],
             'rejection_month': None,
             'anytime_p_value': 1.0,
             'max_log_e': -15.953518},
 'product': {'log_e': [-51.618246, -103.595089, -137.472126, -122.301407, -120.061136],
             'rejection_month': None,
             'anytime_p_value': 1.0,
             'max_log_e': -51.618246},
 'reading': {'en': 'Read at every age, the e-process never reaches 20 for this cohort: the largest log value of the average is -16.0 (20 is log '
                   '3.0). Over the observed ages the cohort has 4,551 charge-offs against 4,754 predicted, so a monitor looking for under-prediction '
                   'has little to say. 0 of 3 vintages reject on their own.',
             'es': 'Leído en cada edad, el proceso e nunca llega a 20 para esta cohorte: el mayor valor logarítmico del promedio es -16,0 (20 es log '
                   '3,0). En las edades observadas la cohorte tiene 4.551 castigos contra 4.754 predichos, así que un monitor que busca '
                   'subestimación tiene poco que decir. 0 de 3 cosechas rechazan por sí solas.'},
 'limits': {'en': 'The null is a binomial with no asset correlation, like the binomial row beside it, so a rejection can also reflect the '
                  "correlation of the vintage's loans. The vintages of a cohort share the economy: the average is the valid combination, the product "
                  'assumes they are independent. A cohort has two to three vintages: this is an illustration on the committed curves, not a measure '
                  'of power. Loans observed for less than the age without a charge-off count as non-events, as in the curves.',
            'es': 'La nula es una binomial sin correlación de activos, como la fila binomial vecina, así que un rechazo puede reflejar también la '
                  'correlación de los créditos de la cosecha. Las cosechas de una cohorte comparten la economía: el promedio es la combinación '
                  'válida, el producto supone que son independientes. Una cohorte tiene de dos a tres cosechas: es una ilustración sobre las curvas '
                  'versionadas, no una medida de potencia. Los créditos observados menos que la edad sin castigo cuentan como no eventos, igual que '
                  'en las curvas.'}}


def build_c03() -> tuple[dict, dict]:
    curves, rows, stab = [], [], []
    for fy, n, resolved, gross, pred, obs, until in C03_VINTAGES:
        full = until >= max(C03_MONTHS)
        reason = None if full else "fixture: the 5-year mark of this vintage is beyond the observation cutoff (as-of 2024-06-30)"
        curves.append({"fiscal_year": fy, "n": n, "gross_approval": gross, "months": C03_MONTHS,
                       "predicted_cumulative_pd": pred, "observed_cumulative_pd": obs, "observed_until_month": until,
                       "reason": reason})
        o5 = obs[-1]
        rows.append({"fiscal_year": fy, "n": n, "n_resolved": resolved, "n_exempt_censored": n - resolved,
                     "gross_approval": gross, "five_year_mark_date": f"{fy + 5}-09-30", "mark_observed": o5 is not None,
                     "observed_5y_pd": o5, "predicted_5y_pd": pred[-1],
                     "gap": None if o5 is None else r(o5 - pred[-1]), "brier": None if o5 is None else 0.07,
                     "auc": None if o5 is None else 0.71, "reason": reason if o5 is None else None})
        stab.append({"fiscal_year": fy, "psi": 0.04 + 0.01 * (fy - 2018), "observed_5y_pd": o5})
    deciles = []
    for d in range(1, 11):
        p = 0.01 * d + 0.002 * d * d / 10
        o = r(p * (0.95 + 0.01 * d))
        deciles.append({"decile": d, "n": 1000, "predicted_pd": r(p), "observed_pd": o,
                        "ci_low": r(max(0.0, o - 0.012)), "ci_high": r(min(1.0, o + 0.012))})
    out = {
        "kind": "vintage-cohort",
        "currency": "USD",
        "cohort": {"id": "fy2018-20", "label": txt("FY2018-20", "AF2018-20"), "first_fy": 2018, "last_fy": 2020,
                   "approval_fiscal_years": [2018, 2019, 2020]},
        "training": C03_TRAINING,
        "target": C03_TARGET,
        "data_status": C03_STATUS,
        "vintage_curves": curves,
        "vintage_summary": {"currency": "USD", "rows": rows},
        "calibration": {"rung_id": "P1-woe-scorecard", "scope": txt("vintages with an observed 5-year mark", "cosechas con marca de 5 años observada"), "rows": deciles},
        "rung_comparison": [
            {"rung_id": "P1-woe-scorecard", "auc": 0.71, "auc_ci_low": 0.69, "auc_ci_high": 0.73, "brier": 0.07,
             "calibration_gap_5y": 0.005, "reason": None},
            {"rung_id": "P4-monotone-gbm", "auc": 0.74, "auc_ci_low": 0.72, "auc_ci_high": 0.76, "brier": 0.068,
             "calibration_gap_5y": -0.004, "reason": None},
            {"rung_id": "P2-penalised-logit", "auc": None, "auc_ci_low": None, "auc_ci_high": None, "brier": None,
             "calibration_gap_5y": None, "reason": "fixture: the rung is not fitted on this cohort"},
        ],
        "stability": {"training_mean_5y_pd": 0.09, "psi_note": txt("Fixture PSI values; 0.10 and 0.25 are conventions, not limits.",
                                                                    "Valores PSI de ejemplo; 0,10 y 0,25 son convenciones, no limites."),
                      "rows": stab},
        "sequential": C03_SEQUENTIAL,
    }
    variant = {
        "schema": "contraste.case/v1", "case_id": "C03", "variant_id": "fixture-fy2018-20",
        "model": [model_summary("P1-woe-scorecard", "credit-scoring", "woe-scorecard")],
        "outputs": out,
        "tests": [test_row("pd.vintage_calibration", "P1-woe-scorecard", NE)],
        "impact": {"observed_5y_pd_fy2018": {"value": 0.092, "unit": "share", "label": txt("Observed 5-year PD, FY2018", "PD observada a 5 anos, AF2018")}},
        "findings": [],
        **envelope_common("real-outcomes"),
    }
    models = {
        "schema": "contraste.models/v1", "case_id": "C03", "fit_id": "fixture-sba-7a",
        "model": [model_record("P1-woe-scorecard", "credit-scoring", "woe-scorecard")],
        "fit": {
            "currency": "USD",
            "vintage_definition": {"basis": "approval fiscal year", "fiscal_year_start": "10-01",
                                   "label": txt("SBA fiscal year, 1 October to 30 September", "Ano fiscal SBA, 1 de octubre a 30 de septiembre")},
            "target": C03_TARGET,
            "cohort_windows": [window(i, a, b) for i, a, b in C03_WINDOWS],
            "ladder": [
                {"rung_id": "P1-woe-scorecard", "kind": "woe-scorecard", "covariates": ["term_months", "naics_sector"],
                 "coefficients": [{"name": "term_months", "estimate": -0.2, "std_error": 0.02},
                                  {"name": "intercept", "estimate": -2.1, "std_error": None}],
                 "training_cutoff": "2017-09-30", "engine": "riskvalidation"},
                {"rung_id": "P4-monotone-gbm", "kind": "monotone-gbm", "covariates": ["term_months", "naics_sector"],
                 "coefficients": [], "training_cutoff": "2017-09-30", "engine": "riskvalidation"}],
            "data_status": C03_STATUS,
        },
        **envelope_common("real-outcomes"),
    }
    return variant, models


# ------------------------------------------------------------------------------------------------------- C08

C08_PROXY = {
    "definition": txt("LGD proxy = gross charge-off amount over the gross approved amount (SBA 7(a) fields GrossChargeOffAmount and "
                      "GrossApproval, the only exposure field the file carries). It is a proxy, not a workout LGD.",
                      "Proxy de LGD = monto bruto castigado sobre el monto bruto aprobado (campos SBA 7(a) GrossChargeOffAmount y "
                      "GrossApproval, el unico campo de exposicion del archivo). Es un proxy, no una LGD de recuperacion."),
    "formula": "GrossChargeOffAmount / GrossApproval",
    "source_field": "GrossChargeOffAmount",
    "exposure_field": "GrossApproval",
    "recovery_cash_flows_available": False,
    "bias_direction": "downward",
    "bias_statement": txt("The proxy is biased low: the approved amount overstates the exposure at default of an amortising loan, "
                          "so the denominator is too large. A second effect pushes the other way: the SBA 7(a) public file has no "
                          "recovery cash flows after charge-off, so the proxy ignores recoveries and costs and overstates the loss "
                          "net of recoveries; it can also exceed 1 when capitalised interest or fees are charged off. The stated "
                          "direction is the denominator effect (decision D2).",
                          "El proxy tiene sesgo a la baja: el monto aprobado sobreestima la exposicion al incumplimiento de un credito "
                          "que se amortiza, de modo que el denominador es demasiado grande. Un segundo efecto va en sentido contrario: "
                          "el archivo publico SBA 7(a) no tiene flujos de recuperacion posteriores al castigo, de modo que el proxy "
                          "ignora recuperaciones y costos y sobreestima la perdida neta de recuperaciones; tambien puede superar 1 si "
                          "se castigan intereses capitalizados o comisiones. La direccion declarada es el efecto del denominador "
                          "(decision D2)."),
}
C08_STATUS = {
    "primary_source": "sba-7a-chargeoff-twin", "freddie_mac_available": False,
    "freddie_mac_reason": "fixture: the owner's Freddie Mac registration does not exist yet; the SBA charge-off twin carries this case",
    "notice": txt("Fixture, not a result. The Freddie Mac slot stays empty until the account exists; no number stands in for it.",
                  "Ejemplo, no es un resultado. El espacio de Freddie Mac queda vacio hasta que exista la cuenta; ningun numero lo reemplaza."),
}
C08_TRAINING = {
    "cutoff_date": "2008-12-31", "n_defaults": 12000, "n_open_workouts_excluded": 1500,
    "closure_rule": txt("Only defaults whose charge-off closed before the cutoff enter the training set; later default cohorts are the tests.",
                        "Solo entran al entrenamiento los incumplimientos cuyo castigo cerro antes del corte; las cohortes posteriores son de prueba."),
}
C08_WORKOUT = {
    "discount_rate_convention": "none-proxy", "discount_rate": None,
    "incomplete_workouts": {"treatment": "not-applicable", "n_excluded": 0, "n_projected": 0,
                            "reason": "fixture: the SBA file has no workout cash flows to discount or to project"},
    "note": txt("No discounting applies to a charge-off proxy; a workout LGD would use the EBA/GL/2017/16 rate (paragraph UNVERIFIED).",
                "No se descuenta un proxy de castigo; una LGD de recuperacion usaria la tasa de EBA/GL/2017/16 (parrafo NO VERIFICADO)."),
}
C08_COHORTS = [("2003-06", 2003, 2006), ("2007-08", 2007, 2008), ("2009-10", 2009, 2010), ("2011-13", 2011, 2013),
               ("2014-19", 2014, 2019), ("2020-23", 2020, 2023)]
C08_PERIOD = {"first_year": 2007, "last_year": 2010, "indicator": "unemployment rate (fixture path)",
              "macro_source": "fixture: a constructed path, not BLS data"}


def build_c08() -> tuple[dict, dict]:
    n = 4000
    counts = [300, 80, 90, 100, 130, 160, 230, 330, 560]
    counts.append(3952 - sum(counts))
    below, above = 8, 40
    bins = [{"lower": r(i / 10, 1), "upper": r((i + 1) / 10, 1), "n": c, "share": r(c / n, 6)} for i, c in enumerate(counts)]
    dist = {
        "n": n, "treatment": "flagged-not-clipped", "bins": bins,
        "mass_at_zero": {"n": 220, "share": r(220 / n, 6)}, "mass_at_one": {"n": 1500, "share": r(1500 / n, 6)},
        "n_below_zero": below, "share_below_zero": r(below / n, 6), "n_above_one": above, "share_above_one": r(above / n, 6),
        "lowest": flagged(-0.05), "highest": flagged(1.12), "mean": flagged(0.64), "median": flagged(0.78),
    }
    rungs = ["L1-ols", "L2-fractional-logit", "L3-beta"]
    rv = []
    for rung, offs in zip(rungs[:2], (0.03, 0.01)):
        for cid, real in (("2003-06", 0.52), ("2007-08", 0.68), ("2009-10", 0.74)):
            pred = r(real - offs * (1 if cid != "2009-10" else 3), 6)
            rv.append({"rung_id": rung, "cohort_id": cid, "n": 4000, "realised": flagged(real), "predicted": flagged(pred),
                       "ci_low": r(real - 0.02, 6), "ci_high": r(real + 0.02, 6), "gap": r(real - pred, 6)})
    buckets = [{"rung_id": "L2-fractional-logit", "bucket": b, "n": 800, "predicted": flagged(p), "realised": flagged(o)}
               for b, p, o in ((1, 0.35, 0.33), (2, 0.55, 0.57), (3, 0.68, 0.70), (4, 0.80, 0.78), (5, 0.93, 0.95))]
    ds_rows = []
    for cid, n_c, real_dt in (("2007-08", 5000, 0.68), ("2009-10", 4000, 0.74)):
        long_run, down = 0.55, 0.70
        covered = down >= real_dt
        ds_rows.append({"cohort_id": cid, "n": n_c, "long_run_lgd": flagged(long_run), "downturn_lgd": flagged(down),
                        "add_on": r(down - long_run, 9), "crisis_realised_lgd": flagged(real_dt), "covered": covered,
                        "shortfall": 0.0 if covered else r(real_dt - down, 9)})
    floors = [
        {"segment_id": "sme-unsecured", "floor_id": "corporate-unsecured", "floor": 0.25, "reference": "CRE32.16", "n": 2400,
         "share_binding": 0.12, "mean_before": flagged(0.62), "mean_after": flagged(0.63), "uplift": r(0.63 - 0.62, 9)},
        {"segment_id": "sme-real-estate", "floor_id": "corporate-real-estate", "floor": 0.10, "reference": "CRE32.16", "n": 1600,
         "share_binding": 0.03, "mean_before": flagged(0.41), "mean_after": flagged(0.415), "uplift": r(0.415 - 0.41, 9)},
    ]
    out = {
        "kind": "default-cohort", "currency": "USD",
        "cohort": {"id": "2009-10", "label": txt("Defaults 2009-10", "Incumplimientos 2009-10"), "first_year": 2009, "last_year": 2010},
        "lgd_proxy": C08_PROXY, "data_status": C08_STATUS, "training": C08_TRAINING, "workout": C08_WORKOUT,
        "exposure": {"currency": "USD", "gross_charge_off_total": 2.8e8, "gross_approval_total": 4.0e8},
        "lgd_distribution": dist,
        "rung_comparison": [
            {"rung_id": "L1-ols", "r2": 0.12, "rmse": 0.31, "mae": 0.26, "spearman": 0.35, "calibration_gap": -0.09, "reason": None},
            {"rung_id": "L2-fractional-logit", "r2": 0.15, "rmse": 0.30, "mae": 0.25, "spearman": 0.38, "calibration_gap": -0.03, "reason": None},
            {"rung_id": "L3-beta", "r2": None, "rmse": 0.30, "mae": 0.25, "spearman": None, "calibration_gap": -0.04,
             "reason": "fixture: the beta rung depends on the endpoint transformation, see endpoint_sensitivity"},
        ],
        "realised_vs_predicted": rv,
        "calibration_by_bucket": buckets,
        "endpoint_sensitivity": [
            {"rung_id": "L3-beta", "epsilon": eps, "mean_predicted": flagged(mp), "rmse": rm}
            for eps, mp, rm in ((0.0001, 0.60, 0.31), (0.001, 0.62, 0.30), (0.01, 0.66, 0.30))],
        "downturn": {"period": C08_PERIOD,
                     "approach": txt("Cohort-based add-on: the default-weighted mean LGD in the downturn years minus the long-run mean. "
                                     "An illustration, not a regulatory estimate.",
                                     "Ajuste por cohortes: la LGD media ponderada por incumplimientos en los anos de crisis menos la media de largo plazo. "
                                     "Una ilustracion, no una estimacion regulatoria."),
                     "rows": ds_rows, "coverage": {"n_cohorts": 2, "share_covered": 0.5}},
        "floors_bite": {"regime": "basel-iii-final", "rows": floors,
                        "note": txt("Fixture floors from dossier 01 A.5; the bite is the mean uplift they cause.",
                                    "Pisos de ejemplo del dossier 01 A.5; el efecto es el alza media que causan.")},
    }
    variant = {
        "schema": "contraste.case/v1", "case_id": "C08", "variant_id": "fixture-2009-10",
        "model": [model_summary("L2-fractional-logit", "lgd-ead", "fractional-logit")],
        "outputs": out,
        "tests": [test_row("lgd_ead.lgd_calibration_by_segment", "L2-fractional-logit", NE)],
        "impact": {"mean_lgd_proxy": {"value": 0.64, "unit": "share", "label": txt("Mean LGD proxy", "LGD proxy media")}},
        "findings": [],
        **envelope_common("real-outcomes"),
    }
    cells = [
        ("corporate-unsecured", "corporate", "unsecured", 0.25, "CRE32.16"),
        ("corporate-financial", "corporate", "financial", 0.0, "CRE32.16"),
        ("corporate-receivables", "corporate", "receivables", 0.10, "CRE32.16"),
        ("corporate-real-estate", "corporate", "real-estate", 0.10, "CRE32.16"),
        ("corporate-other-physical", "corporate", "other-physical", 0.15, "CRE32.16"),
        ("retail-mortgage", "retail", "mortgage", 0.05, "CRE32.58 to CRE32.59"),
        ("retail-qrre", "retail", "qrre", 0.50, "CRE32.58 to CRE32.59"),
        ("retail-other-unsecured", "retail", "unsecured", 0.30, "CRE32.58 to CRE32.59"),
        ("retail-other-financial", "retail", "financial", 0.0, "CRE32.58 to CRE32.59"),
        ("retail-other-receivables", "retail", "receivables", 0.10, "CRE32.58 to CRE32.59"),
        ("retail-other-real-estate", "retail", "real-estate", 0.10, "CRE32.58 to CRE32.59"),
        ("retail-other-physical", "retail", "other-physical", 0.15, "CRE32.58 to CRE32.59"),
    ]
    models = {
        "schema": "contraste.models/v1", "case_id": "C08", "fit_id": "fixture-sba-chargeoff-twin",
        "model": [model_record("L2-fractional-logit", "lgd-ead", "fractional-logit")],
        "fit": {
            "currency": "USD", "lgd_proxy": C08_PROXY, "data_status": C08_STATUS,
            "cohorts": [{"id": i, "label": txt(f"Defaults {i}", f"Incumplimientos {i}"), "first_year": a, "last_year": b}
                        for i, a, b in C08_COHORTS],
            "training": C08_TRAINING, "workout": C08_WORKOUT,
            "ladder": [
                {"rung_id": "L1-ols", "kind": "ols", "covariates": ["term_months", "naics_sector"],
                 "coefficients": [{"name": "term_months", "estimate": 0.001, "std_error": 0.0002}], "epsilon": None,
                 "training_cutoff": "2008-12-31", "library": "numpy", "library_version": "fixture"},
                {"rung_id": "L2-fractional-logit", "kind": "fractional-logit", "covariates": ["term_months", "naics_sector"],
                 "coefficients": [{"name": "term_months", "estimate": 0.004, "std_error": 0.001}], "epsilon": None,
                 "training_cutoff": "2008-12-31", "library": "statsmodels", "library_version": "fixture"},
                {"rung_id": "L3-beta", "kind": "beta", "covariates": ["term_months"], "coefficients": [], "epsilon": 0.001,
                 "training_cutoff": "2008-12-31", "library": "statsmodels", "library_version": "fixture"},
                {"rung_id": "L5-gradient-boosted", "kind": "gradient-boosted", "covariates": ["term_months", "naics_sector"],
                 "coefficients": [], "epsilon": None, "training_cutoff": "2008-12-31", "library": "catboost",
                 "library_version": "fixture"},
                {"rung_id": "L7-random-forest", "kind": "random-forest", "covariates": ["term_months", "naics_sector"],
                 "coefficients": [], "epsilon": None, "training_cutoff": "2008-12-31", "library": "scikit-learn",
                 "library_version": "fixture"}],
            "downturn": {"approach": txt("Cohort-based add-on over the downturn years of a supplied macro path.",
                                         "Ajuste por cohortes sobre los anos de crisis de una trayectoria macro entregada."),
                         "period": C08_PERIOD},
            "floors": {"regime": "basel-iii-final",
                       "source": "dossier 01 section A.5 (CRE32.16, CRE32.58 to CRE32.59); the collateral order of the retail secured "
                                 "floors (financial, receivables, real estate, other physical) is read as the corporate order, UNVERIFIED",
                       "cells": [{"id": i, "portfolio": p, "collateral": c, "floor": f, "reference": ref} for i, p, c, f, ref in cells]},
        },
        **envelope_common("real-outcomes"),
    }
    return variant, models


# ------------------------------------------------------------------------------------------------------- C09

C09_CONVENTION = {
    "name": "eu-undrawn",
    "definition": txt("CCF = (EAD - drawn at the reference date) / (limit - drawn at the reference date): the share of the undrawn "
                      "amount drawn by default.",
                      "CCF = (EAD - utilizado en la fecha de referencia) / (limite - utilizado en la fecha de referencia): la parte del "
                      "monto no utilizado que se usa al incumplir."),
    "formula": "CCF = (EAD - E(t_r)) / (L(t_r) - E(t_r))",
    "us_terms": txt("The same ratio is the loan equivalent (LEQ) in US terms; Qi (2009) calls EAD over outstanding the CCF and "
                    "EAD over the limit the EADF.",
                    "La misma razon es el equivalente de credito (LEQ) en terminos de EE.UU.; Qi (2009) llama CCF a EAD sobre el "
                    "saldo y EADF a EAD sobre el limite."),
}
C09_TRUTH = flagged(0.60)
C09_GENERATOR = {
    "name": "revolving-line-generator", "shaped_on": "fed-2025-cards-hypothetical-portfolios",
    "true_ccf": C09_TRUTH, "acceleration_factor": 3.0, "acceleration_window_months": 6,
    "notice": txt("Fixture, not a result. The truth is the CCF the generator draws balances with.",
                  "Ejemplo, no es un resultado. La verdad es el CCF con que el generador simula los saldos."),
}
C09_DESIGNS = ("fixed-horizon", "cohort", "variable-horizon")
C09_SMALL = {"currency": "USD", "threshold": 50.0, "applied": True, "n_switched": 120, "reference": "Qi (2009), OCC Economics Working Paper 2009-2"}
def _clip(m: dict) -> dict:
    return {"n_clipped_below": None, "n_clipped_above": None, **m}


C09_MODELS = [_clip(m) for m in [
    {"model_id": "m-fixed", "kind": "ccf-fixed-horizon", "design": "fixed-horizon", "treatment": "floor-cap", "covariates": ["utilisation"]},
    {"model_id": "m-cohort", "kind": "ccf-cohort", "design": "cohort", "treatment": "floor-cap", "covariates": ["utilisation"]},
    {"model_id": "m-variable", "kind": "ccf-variable-horizon", "design": "variable-horizon", "treatment": "bounded-scale",
     "covariates": ["utilisation"]},
    {"model_id": "m-direct", "kind": "direct-ead", "design": None, "treatment": None, "covariates": ["utilisation", "limit"],
     "n_clipped_below": 12, "n_clipped_above": 31},
    {"model_id": "m-utilisation", "kind": "utilisation-change", "design": None, "treatment": None, "covariates": ["utilisation"]},
]]


def build_c09() -> tuple[dict, dict]:
    spec = [  # design, treatment, estimate, ci_low, ci_high, below, above
        ("fixed-horizon", "none", 1.04, 0.97, 1.11, 0.08, 0.31),
        ("fixed-horizon", "floor-cap", 0.83, 0.80, 0.86, 0.0, 0.0),
        ("cohort", "none", 0.93, 0.88, 0.98, 0.06, 0.22),
        ("cohort", "bounded-scale", 0.64, 0.61, 0.67, 0.0, 0.0),
        ("variable-horizon", "none", 0.86, 0.82, 0.90, 0.05, 0.17),
        ("variable-horizon", "floor-cap", 0.74, 0.71, 0.77, 0.0, 0.0),
        ("variable-horizon", "bounded-scale", 0.66, 0.62, 0.70, 0.0, 0.0),
    ]
    tol = 0.05
    rows = []
    for design, treat, est, lo, hi, b, a in spec:
        bias = r(est - 0.60, 9)
        rows.append({"design": design, "treatment": treat, "estimator": "mean", "estimate": flagged(est), "truth": C09_TRUTH,
                     "bias": bias, "rmse": r(abs(bias) + 0.05, 6), "ci_low": lo, "ci_high": hi, "n_defaults": 2000,
                     "share_below_zero": b, "share_above_one": a, "within_tolerance": abs(bias) <= tol})
    edges = [-0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]
    counts = [40, 90, 180, 200, 260, 330, 260, 140]
    band_edges = [0.0, 0.25, 0.5, 0.75, 1.0]
    bt = []
    for mid, scale in (("m-fixed", 1.06), ("m-direct", 0.98)):
        for i in range(4):
            real = 40000 * (i + 1)
            pred = round(real * (scale if i < 2 else 2 - scale))
            bt.append({"model_id": mid, "band_id": f"u{i + 1}", "utilisation_lower": band_edges[i],
                       "utilisation_upper": band_edges[i + 1], "n": 500, "predicted_ead": float(pred), "prediction_flag": "in-range",
                       "realised_ead": float(real), "gap": float(pred - real), "relative_gap": r((pred - real) / real, 9),
                       "light": "green" if abs(pred - real) / real < 0.05 else "amber"})
    out = {
        "kind": "acceleration-level", "level": 5,
        "level_description": txt("Level 5: utilisation accelerates most steeply in the months before default.",
                                 "Nivel 5: la utilizacion se acelera con mayor fuerza en los meses previos al incumplimiento."),
        "currency": "USD", "convention": C09_CONVENTION, "generator": C09_GENERATOR,
        "replications": {
            "development": {"seeds": [101, 102, 103, 104], "n_replications": 4, "n_facilities": 50000, "n_defaults": 2000},
            "test": {"seeds": [201, 202, 203, 204], "n_replications": 4, "n_facilities": 50000, "n_defaults": 2000}},
        "ccf_by_design": {"tolerance": tol, "rows": rows},
        "ccf_distribution": {"design": "fixed-horizon", "n": sum(counts), "edges": edges, "counts": counts,
                             "n_below_zero": counts[0] + counts[1], "n_above_one": counts[6] + counts[7]},
        "ead_models": C09_MODELS,
        "ead_backtest": {"currency": "USD", "bands": band_edges, "rows": bt},
        "ead_floor": {"currency": "USD", "rule": "on-balance amount + 50% of the off-balance exposure at the SA CCF (CRE32.36, CRE32.64)",
                      "off_balance_share": 0.5,
                      "rows": [{"facility_class": "revolving-commitment", "sa_ccf": 0.40, "reference": "CRE20.98", "n": 1200,
                                "share_binding": 0.18, "mean_ead_before": 640.0, "mean_ead_after": 668.0},
                               {"facility_class": "unconditionally-cancellable", "sa_ccf": 0.10, "reference": "CRE20.100", "n": 800,
                                "share_binding": 0.05, "mean_ead_before": 410.0, "mean_ead_after": 412.0}]},
        "small_undrawn": C09_SMALL,
    }
    variant = {
        "schema": "contraste.case/v1", "case_id": "C09", "variant_id": "fixture-level-5",
        "model": [model_summary("m-fixed", "lgd-ead", "ccf-fixed-horizon")],
        "outputs": out,
        "tests": [test_row("lgd_ead.ccf_estimator_bias", "m-fixed", NE), test_row("lgd_ead.ead_backtest_by_band", "m-fixed", NE)],
        "impact": {"ccf_bias_fixed_horizon": {"value": 0.23, "unit": "share", "label": txt("Fixed-horizon CCF bias", "Sesgo del CCF a horizonte fijo")}},
        "findings": [],
        **envelope_common("synthetic-known-truth"),
    }
    marginals = [
        {"field": "credit_limit", "distribution": "lognormal",
         "parameters": [{"name": "mu", "value": 8.5, "unit": "ln USD"}, {"name": "sigma", "value": 0.7, "unit": "ln USD"}],
         "source": "fixture values; the bake reads the Fed 2025 cards-*-2025.csv files"},
        {"field": "utilisation_at_reference", "distribution": "beta",
         "parameters": [{"name": "alpha", "value": 1.2, "unit": "-"}, {"name": "beta", "value": 2.4, "unit": "-"}],
         "source": "fixture values; the bake reads the Fed 2025 cards-*-2025.csv files"},
    ]
    levels = [{"level": k, "label": txt(f"Level {k}", f"Nivel {k}"), "acceleration_factor": f, "acceleration_window_months": 0 if k == 0 else 6}
              for k, f in enumerate((1.0, 1.25, 1.5, 2.0, 2.5, 3.0))]
    models = {
        "schema": "contraste.models/v1", "case_id": "C09", "fit_id": "fixture-generator",
        "model": [model_record("m-fixed", "lgd-ead", "ccf-fixed-horizon")],
        "fit": {
            "currency": "USD", "convention": C09_CONVENTION, "generator": C09_GENERATOR, "marginals": marginals, "levels": levels,
            "replications_plan": {"development_seeds": [101, 102, 103, 104], "test_seeds": [201, 202, 203, 204], "n_facilities": 50000},
            "designs": [
                {"design": "fixed-horizon", "horizon_months": 12, "n_reference": 1, "step_months": None,
                 "label": txt("Fixed horizon: 12 months before default", "Horizonte fijo: 12 meses antes del incumplimiento")},
                {"design": "cohort", "horizon_months": None, "n_reference": 1, "step_months": 12,
                 "label": txt("Yearly cohort: the cohort start", "Cohorte anual: el inicio de la cohorte")},
                {"design": "variable-horizon", "horizon_months": 12, "n_reference": 4, "step_months": 3,
                 "label": txt("Variable horizon: quarterly reference dates in the year before default",
                              "Horizonte variable: fechas trimestrales de referencia en el ano previo al incumplimiento")}],
            "treatments": ["none", "censor", "floor-cap", "bounded-scale"],
            "ead_models": C09_MODELS,
            "small_undrawn": C09_SMALL,
            "floors": {"off_balance_share": 0.5, "reference": "CRE32.36, CRE32.64, CRE32.33; dossier 01 section A.5",
                       "supervisory_ccfs": [
                           {"item": "direct-credit-substitutes", "ccf": 1.0, "reference": "CRE20.94 to CRE20.101"},
                           {"item": "nifs-rufs-transaction-related-contingents", "ccf": 0.5, "reference": "CRE20.94 to CRE20.101"},
                           {"item": "commitments", "ccf": 0.4, "reference": "CRE20.98"},
                           {"item": "short-term-self-liquidating-trade-letters-of-credit", "ccf": 0.2, "reference": "CRE20.94 to CRE20.101"},
                           {"item": "unconditionally-cancellable", "ccf": 0.1, "reference": "CRE20.100"}]},
        },
        **envelope_common("synthetic-known-truth"),
    }
    return variant, models


def dump(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    for case, build, kind in (("c03", build_c03, "vintage-cohort"), ("c08", build_c08, "default-cohort"),
                              ("c09", build_c09, "acceleration-level")):
        variant, models = build()
        dump(FIX / case / f"variant-{kind}-fixture.json", variant)
        dump(FIX / case / "models-fixture.json", models)


if __name__ == "__main__":
    main()
