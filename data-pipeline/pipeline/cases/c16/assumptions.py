"""The named parameters and the mapping tables of C16: every one a convention, labelled so, with its value and its basis (the
conventions block of every document, ``c16-outputs``, ``c16-outputs-reverse`` and ``c16-models``).

Real aggregates, synthetic behaviour: the call-report items are real; the deposit-category mapping, the monetisation schedule, the
securities duration buckets, the day calendar, the grids, the target of the reverse stress, the tolerances and the lights are
conventions the sources do not give (U11 sizing Q13 and Q14, proposed by U11-S and approved in its review). Nothing here is a
regulatory threshold. The values below are those of the S contract (``docs/contracts/schemas/c16``): a document whose conventions
differ fails its schema.
"""
from __future__ import annotations

import datetime as dt

LCR_PHASE = "lcr-30-day"
VARIANT_IDS = ("lcr-standard", "list-adverse", "list-extreme", "fast-run", "htm-losses")
HORIZON = {"lcr-standard": 30, "list-adverse": 125, "list-extreme": 125, "fast-run": 5, "htm-losses": 125}
FIRST_DAY = "2023-01-03"


def r6(x: float) -> float:
    return round(x, 6)


def txt(en: str, es: str) -> dict:
    return {"en": en, "es": es}



HOLIDAYS = ["2023-01-02", "2023-01-16", "2023-02-20", "2023-05-29", "2023-06-19", "2023-07-04", "2023-09-04", "2023-10-09",
            "2023-11-10", "2023-11-23", "2023-12-25"]
FIRST_DAY = "2023-01-03"


def relevant_days(n: int) -> list[str]:
    """The first ``n`` relevant days of the ladder: the US business days from the day after the valuation date (the convention
    ``day_calendar``; the LiST rates are on the 2019 TARGET2 calendar, A2)."""
    d, out = dt.date.fromisoformat(FIRST_DAY), []
    while len(out) < n:
        if d.weekday() < 5 and d.isoformat() not in HOLIDAYS:
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def scalar(value: float, unit: str, en: str, es: str) -> dict:
    return {"value": value, "unit": unit, "status": "convention", "basis": txt(en, es)}


def grid(values: list, unit: str, en: str, es: str) -> dict:
    return {"values": values, "unit": unit, "status": "convention", "basis": txt(en, es)}


SEC_ROWS = [  # class, Federal Reserve category (M2, effective 2022-03-14 to 2023-03-12), duration bucket, margin, rule
    ("cash-and-balances", "not applicable: nominal value (LiST para 73)", "none", None, "nominal-value"),
    ("treasury", "U.S. Treasuries and fully guaranteed agencies: Bills, Notes, Bonds", ">3-5", 0.98, "central-bank-framework"),
    ("mortgage-backed", "Agency backed mortgages: pass-throughs, CMOs, commercial MBS", ">5-10", 0.96, "central-bank-framework"),
    ("other-agency", "Government Sponsored Enterprises: Bills, Notes, Bonds", ">3-5", 0.97, "central-bank-framework"),
    ("municipal", "Municipal bonds: AAA-BBB USD", ">5-10", 0.95, "central-bank-framework"),
    ("other-debt", "no framework row: fallback", "none", None, "fifty-percent-fallback"),
]
BAND = 0.05
SCHEDULE = [(1, 0.5), (2, 0.8), (3, 1.0)]


def share_at(day: int, points: list = SCHEDULE) -> float:
    s = 0.0
    for d, v in points:
        if d <= day:
            s = v
    return s


def sec_haircut(margin: float | None, rule: str) -> float:
    if rule == "nominal-value":
        return 0.0
    return r6(1 - margin) if margin is not None else 0.5


def conventions() -> dict:
    c: dict = {}
    c["deposit_category_mapping"] = {
        "status": "convention",
        "rows": [
            {"basis": "insured", "role": "central", "lcr_category": "retail_less_stable", "list_class": "other-retail",
             "label": txt("Insured deposits (DEPINS) as retail, less stable", "Depositos asegurados (DEPINS) como minoristas menos estables")},
            {"basis": "uninsured", "role": "central", "lcr_category": "non_financial_corporate",
             "list_class": "non-operational-non-financial-corporates",
             "label": txt("Uninsured deposits (DEPUNA) as non-operational non-financial corporates",
                          "Depositos no asegurados (DEPUNA) como corporativos no financieros no operacionales")},
        ],
        "sensitivity_band": [
            {"basis": "uninsured", "role": "band", "lcr_category": "operational", "list_class": "operational",
             "label": txt("Uninsured balance as operational deposits", "Saldo no asegurado como depositos operacionales")},
            {"basis": "uninsured", "role": "band", "lcr_category": "non_financial_corporate",
             "list_class": "non-operational-non-financial-corporates",
             "label": txt("Uninsured balance as non-financial corporates", "Saldo no asegurado como corporativos no financieros")},
            {"basis": "uninsured", "role": "band", "lcr_category": "other_legal_entity",
             "list_class": "non-operational-other-financial",
             "label": txt("Uninsured balance as other legal entities", "Saldo no asegurado como otras personas juridicas")},
        ],
        "basis": txt("The call report carries no customer type: the mapping is an assumption, proposed by U11-S from dossier 05 E.5 "
                     "and 01 G.1 (Q13); the band is the dossier's plausible classes. A convention, never a regulatory classification.",
                     "El reporte de llamada no trae tipo de cliente: el mapeo es un supuesto propuesto por U11-S (Q13). "
                     "Una convencion, nunca una clasificacion regulatoria."),
    }
    c["variant_scenarios"] = {
        "status": "convention",
        "rows": [
            {"variant": v, "scenario_family": fam, "phase": ph, "parameter_set": ps, "horizon_days": n, "axis": ax}
            for v, fam, ph, ps, n, ax in (
                ("lcr-standard", "combined", "lcr-30-day", "basel-lcr", 30, "calendar-days"),
                ("list-adverse", "idiosyncratic", "protracted", "list-adverse", 125, "relevant-days"),
                ("list-extreme", "idiosyncratic", "protracted", "list-extreme", 125, "relevant-days"),
                ("fast-run", "idiosyncratic", "acute", "fast-run", 5, "relevant-days"),
                ("htm-losses", "idiosyncratic", "protracted", "list-adverse", 125, "relevant-days"))],
        "basis": txt("Dossier 05 E.2 asks for three families and two horizons and the SDD names none: the LCR is the combined "
                     "stress over 30 calendar days (LCR20.2), a phase of its own, lcr-30-day, outside the acute (1 to 5 days) and "
                     "protracted (6 to 12 months) wording of 05 l.277; the LiST 2019 shocks are idiosyncratic only (annex slide 5) and "
                     "protracted; the fast run is acute.",
                     "El dossier 05 E.2 pide tres familias y dos horizontes y el SDD no nombra ninguno: el LCR es el estres combinado "
                     "a 30 dias corridos (LCR20.2), una fase propia, lcr-30-day, fuera de lo agudo (1 a 5 dias) y lo prolongado "
                     "(6 a 12 meses) del dossier 05 l.277; los choques LiST 2019 son solo idiosincraticos y prolongados; la corrida "
                     "rapida es aguda."),
    }
    c["day_calendar"] = {
        "status": "convention", "kind": "us-business-days", "first_day": FIRST_DAY, "excluded_weekdays": ["saturday", "sunday"],
        "holidays": HOLIDAYS,
        "holiday_rule": "2023 US federal holidays as observed on weekdays (a proposed convention, not read from a source)",
        "basis": txt("The LiST rates are defined on the 2019 TARGET2 relevant-day calendar (A2); the ladder of the 2022-12-31 balance "
                     "sheet runs on US business days from the day after the valuation date.",
                     "Las tasas LiST se definen sobre el calendario TARGET2 de 2019 (A2); la escalera corre sobre dias habiles de "
                     "EE.UU. desde el dia siguiente a la fecha de valoracion."),
    }
    c["cbc_securities_mapping"] = {
        "status": "convention",
        "rows": [{"class_id": cid, "fed_category": cat, "duration_bucket": bucket, "margin": margin,
                  "haircut": sec_haircut(margin, rule), "haircut_low": max(0.0, r6(sec_haircut(margin, rule) - BAND)),
                  "haircut_high": min(1.0, r6(sec_haircut(margin, rule) + BAND)), "rule": rule,
                  "source": "Federal Reserve discount window securities margins effective 2022-03-14 to 2023-03-12 (addendum L4)"
                  if rule == "central-bank-framework" else "ECB LiST 2019 methodological note para 74 (addendum L1.6)"}
                 for cid, cat, bucket, margin, rule in SEC_ROWS],
        "basis": txt("The securities book split by type at the FDIC carrying values (A3); the duration bucket is an assumption "
                     "(the call report gives maturity buckets, not durations); a class with no framework row takes the fallback.",
                     "El libro de valores por tipo a valores contables FDIC (A3); el tramo de duracion es un supuesto; una clase "
                     "sin fila del marco toma el respaldo."),
    }
    c["monetisation_schedule"] = {
        "status": "convention", "points": [{"day": d, "cumulative_share": s} for d, s in SCHEDULE],
        "sensitivity_band": [
            {"id": "immediate", "points": [{"day": 1, "cumulative_share": 1.0}]},
            {"id": "slow", "points": [{"day": 1, "cumulative_share": 0.25}, {"day": 5, "cumulative_share": 0.6},
                                      {"day": 10, "cumulative_share": 1.0}]}],
        "basis": txt("Dossier 05 E.5 names the monetisation capacity per day with no value (Q6): a step schedule of the share of the "
                     "liquidity value usable by day, with an immediate and a slow bound.",
                     "El dossier 05 E.5 nombra la capacidad de monetizacion por dia sin valor (Q6): un calendario escalonado con "
                     "cotas inmediata y lenta."),
    }
    c["fast_run_calibration_rule"] = {
        "status": "convention", "rule": "maximum-implied-daily-rate",
        "basis": txt("The dossiers give no calibration method (Q4): the fast run takes the fastest implied daily rate of the pre-2023 "
                     "Table A.1 rows, a severe-scenario choice.",
                     "Los dossiers no dan metodo de calibracion (Q4): la corrida rapida toma la mayor tasa diaria implicita de las "
                     "filas de la Tabla A.1 anteriores a 2023."),
    }
    c["cliff_days"] = {
        "status": "convention", "near": 30, "far": 35, "day_basis": "relevant-days",
        "basis": txt("The days of the cliff diagnostic are 30 and 35 (05 E.1); the LiST note does not say whether they count calendar "
                     "or relevant days (UNVERIFIED), so the basis is a convention.",
                     "Los dias del diagnostico son 30 y 35 (05 E.1); la nota LiST no dice si son corridos o habiles (SIN VERIFICAR)."),
    }
    c["contractual_bucket_edges_days"] = grid([1, 7, 30, 90, 180, 365], "days",
        "Upper edges of the contractual maturity buckets, a convention (SRP50 names no buckets for the mismatch tool).",
        "Bordes superiores de los tramos de vencimiento contractual, una convencion.")
    c["event_horizon_days"] = scalar(2, "days", "The event horizon of the March 2023 run: SVB's 85 percent in 2 days (05 E.2, Table A.1).",
                                     "El horizonte del evento de marzo 2023: 85 por ciento de SVB en 2 dias (05 E.2, Tabla A.1).")
    c["uninsured_share_grid"] = grid([0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95], "share of domestic deposits",
        "The grid of the uninsured share for the sensitivity of the survival period (05 E.5 rung 4).",
        "La grilla de la proporcion no asegurada para la sensibilidad del periodo de supervivencia.")
    c["htm_loss_multiple_grid"] = grid([0.0, 0.5, 1.0, 1.5, 2.0], "multiple of the reported HTM unrealised loss",
        "The grid of the HTM unrealised loss for the sensitivity (05 E.5 rung 4); 1 is the reported loss.",
        "La grilla de la perdida no realizada HTM para la sensibilidad; 1 es la perdida informada.")
    c["runoff_multiplier_grid"] = grid([1.0, 1.25, 1.5, 2.0, 3.0, 5.0, 8.0, 13.0, 21.0, 34.0, 55.0, 89.0, 144.0], "multiple of the daily rates",
        "The grid of the reverse-stress multiplier; a point beyond a scenario's cap (every rate below 1) is omitted from its curve.",
        "La grilla del multiplicador del estres inverso; un punto sobre el tope del escenario se omite de su curva.")
    c["reverse_target_days"] = scalar(30, "days", "The dossier's example target of the reverse stress (05 E.5 rung 5).",
                                      "El objetivo de ejemplo del dossier para el estres inverso (05 E.5).")
    c["list_compounding_tolerance"] = scalar(5e-7, "share, absolute",
        "A golden stated to six decimals holds to 5e-7 (the engine contract's rule).",
        "Un valor dorado a seis decimales se cumple a 5e-7.")
    c["monotonicity_tolerance_days"] = scalar(0, "days", "The survival period must not lengthen as severity rises: no tolerance.",
                                              "El periodo de supervivencia no debe alargarse al subir la severidad: sin tolerancia.")
    c["nlp_identity_tolerance"] = scalar(1e-6, "USD thousands", "The NLP identity of 05 E.1 holds to the rounding of six decimals.",
                                         "La identidad del NLP se cumple al redondeo de seis decimales.")
    c["cliff_amber_threshold"] = scalar(-0.01, "share of total assets",
        "The dossier defines the cliff diagnostic and no limit (05 E.1): amber below minus 1 percent of total assets.",
        "El dossier define el diagnostico y ningun limite: ambar bajo menos 1 por ciento de los activos.")
    c["cliff_red_threshold"] = scalar(-0.03, "share of total assets", "Red below minus 3 percent of total assets (a convention).",
                                      "Rojo bajo menos 3 por ciento de los activos (una convencion).")
    c["scoring_ratio_green"] = scalar(0.8, "modelled over realised cumulative outflow",
        "Green when the model reaches 80 percent of the realised outflow at the event horizon (Q5, a descriptive score).",
        "Verde cuando el modelo alcanza 80 por ciento de la salida realizada en el horizonte del evento.")
    c["scoring_ratio_amber"] = scalar(0.5, "modelled over realised cumulative outflow",
        "Amber from 50 percent of the realised outflow; red below.", "Ambar desde 50 por ciento de la salida realizada; rojo bajo ello.")
    c["generator_truth_se_green"] = scalar(2.0, "Monte Carlo standard errors",
        "Green when the model's rate is within 2 Monte Carlo standard errors of the generator's truth (Q5).",
        "Verde cuando la tasa del modelo esta a menos de 2 errores estandar Monte Carlo de la verdad del generador.")
    c["generator_truth_se_red"] = scalar(3.0, "Monte Carlo standard errors", "Red beyond 3 Monte Carlo standard errors.",
                                         "Rojo sobre 3 errores estandar Monte Carlo.")
    c["htm_revaluation_green"] = scalar(0.05, "share of the reported unrealised loss",
        "Green when the revalued HTM book is within 5 percent of the reported unrealised loss (Q11).",
        "Verde cuando el libro HTM revaluado esta a menos de 5 por ciento de la perdida no realizada informada.")
    c["htm_revaluation_amber"] = scalar(0.15, "share of the reported unrealised loss", "Amber within 15 percent; red beyond.",
                                        "Ambar a menos de 15 por ciento; rojo sobre ello.")
    c["round_trip_tolerance_days"] = scalar(0, "days", "The solved multiplier must return the target survival period exactly.",
                                            "El multiplicador resuelto debe devolver exactamente el periodo objetivo.")
    c["cbc_haircut_band"] = scalar(BAND, "share, added to and taken from each haircut",
        "The width of the sensitivity band of the central bank haircuts (Q6, A4).",
        "El ancho de la banda de sensibilidad de los recortes del banco central.")
    return c


def deposit_category_mapping() -> dict:
    return conventions()["deposit_category_mapping"]


def monetisation_points(conv: dict) -> list[tuple[int, float]]:
    return [(p["day"], p["cumulative_share"]) for p in conv["monetisation_schedule"]["points"]]
