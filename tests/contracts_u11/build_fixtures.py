"""Builds the seven U11-S fixture documents (docs/contracts/fixtures/c16).

Run: ``python tests/contracts_u11/build_fixtures.py``. Deterministic, standard library only. The documents are fixtures, never
results: every one is labelled ``fixture`` in its provenance and its ids. They are internally consistent: every run-off curve,
ladder, NLP, survival period, LCR block, scoring row and reverse-stress curve is computed here from the formulas of dossier 05 E
and dossier 01 G (the test file recomputes them independently through ``semantics.py``).

The balance-sheet aggregates are the data facts the U11 sizing (R6) and the research addendum (L3, F4) read from the FDIC API for
CERT 24735 at 2022-12-31, public aggregates only; the two earlier dates of the time block, the H.8 points, the LCR inflow row
that exercises the 75 percent cap, the HQLA levels that exercise the 15 percent cap, the contractual buckets and the verification
of the generator are round fixture values, said so in their labels. The named parameters are the values U11-S proposes (Q14).
"""
from __future__ import annotations

import datetime as dt
import json
import math
import statistics
from pathlib import Path

from build_schemas import (A1_IDS, CALIBRATED_ON, CONVENTION_NAMES, LIST_CONTRACTUAL, LIST_DRAWDOWN, LIST_INFLOWS, LIST_OPEN,
                           PARAMETER_SETS, SCORED_ON, TABLE_A1, VARIANTS)

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "docs" / "contracts" / "fixtures" / "c16"
VD = "2022-12-31"
H = {"lcr-standard": 30, "list-adverse": 125, "list-extreme": 125, "fast-run": 5, "htm-losses": 125}
ZERO_HASH = "0" * 64


def r6(x: float) -> float:
    return round(x, 6)


def r10(x: float) -> float:
    return round(x, 10)


def txt(en: str, es: str) -> dict:
    return {"en": en, "es": es}


def implied(share: float, days: int) -> float:
    return 1 - (1 - share) ** (1 / days)


# ------------------------------------------------------------------------------------------------------ the data facts

FDIC = {  # thousands of USD at 2022-12-31, CERT 24735 (sizing R6 probe, addendum L3 and F4): data facts, not results
    "ASSET": 209_026_000, "DEP": 175_378_000, "DEPDOM": 161_479_000, "DEPUNA": 151_592_000, "DEPINS": 9_990_000,
    "DEPSMAMT": 4_778_000, "DEPLGAMT": 156_747_000, "SC": 117_297_000, "SCHA": 91_327_000, "SCHF": 76_168_000,
    "SCAA": 28_502_000, "SCAF": 25_976_000, "CHBAL": 12_511_000, "FREPO": 707_000, "FREPP": 524_000, "OTHBFHLB": 15_000_000,
    "LNLSNET": 73_613_000, "EQ": 15_456_000, "SCUST": 16_043_000, "SCMTGBK": 91_460_000, "SCASPNSUM": 587_000,
    "SCMUNI": 7_417_000, "SCDOMO": 708_000, "SCFORD": 1_088_000, "SCPLEDGE": 55_358_000,
}
FOREIGN = FDIC["DEP"] - FDIC["DEPDOM"]
PLEDGED_SHARE = FDIC["SCPLEDGE"] / FDIC["SC"]
FV_FACTOR = (FDIC["SCHF"] + FDIC["SCAF"]) / (FDIC["SCHA"] + FDIC["SCAF"])   # the HTM loss applied to the whole book, pro rata
HOLIDAYS = ["2023-01-02", "2023-01-16", "2023-02-20", "2023-05-29", "2023-06-19", "2023-07-04", "2023-09-04", "2023-10-09",
            "2023-11-10", "2023-11-23", "2023-12-25"]
FIRST_DAY = "2023-01-03"


def relevant_days(n: int) -> list[str]:
    d, out = dt.date.fromisoformat(FIRST_DAY), []
    while len(out) < n:
        if d.weekday() < 5 and d.isoformat() not in HOLIDAYS:
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


# ------------------------------------------------------------------------------------------------------ the conventions


def scalar(value: float, unit: str, en: str, es: str) -> dict:
    return {"value": value, "unit": unit, "status": "convention", "basis": txt(en, es)}


def grid(values: list, unit: str, en: str, es: str) -> dict:
    return {"values": values, "unit": unit, "status": "convention", "basis": txt(en, es)}


SEC_ROWS = [  # class, Federal Reserve category (M2, effective 2022-03-14 to 2023-03-12), duration bucket, margin, rule
    ("cash-and-balances", "not applicable: nominal value (LiST para 73)", "none", None, "nominal-value"),
    ("reverse-repo", "no framework row: fallback", "none", None, "fifty-percent-fallback"),
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
            {"basis": "insured", "role": "central", "lcr_category": "retail-less-stable", "list_class": "other-retail",
             "label": txt("Insured deposits (DEPINS) as retail, less stable", "Depositos asegurados (DEPINS) como minoristas menos estables")},
            {"basis": "uninsured", "role": "central", "lcr_category": "non-financial-corporate",
             "list_class": "non-operational-non-financial-corporates",
             "label": txt("Uninsured deposits (DEPUNA) as non-operational non-financial corporates",
                          "Depositos no asegurados (DEPUNA) como corporativos no financieros no operacionales")},
        ],
        "sensitivity_band": [
            {"basis": "uninsured", "role": "band", "lcr_category": "operational", "list_class": "operational",
             "label": txt("Uninsured balance as operational deposits", "Saldo no asegurado como depositos operacionales")},
            {"basis": "uninsured", "role": "band", "lcr_category": "non-financial-corporate",
             "list_class": "non-operational-non-financial-corporates",
             "label": txt("Uninsured balance as non-financial corporates", "Saldo no asegurado como corporativos no financieros")},
            {"basis": "uninsured", "role": "band", "lcr_category": "other-legal-entity",
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
                ("lcr-standard", "combined", "protracted", "basel-lcr", 30, "calendar-days"),
                ("list-adverse", "idiosyncratic", "protracted", "list-adverse", 125, "relevant-days"),
                ("list-extreme", "idiosyncratic", "protracted", "list-extreme", 125, "relevant-days"),
                ("fast-run", "idiosyncratic", "acute", "fast-run", 5, "relevant-days"),
                ("htm-losses", "idiosyncratic", "protracted", "list-adverse", 125, "relevant-days"))],
        "basis": txt("Dossier 05 E.2 asks for three families and two horizons and the SDD names none: the LCR is the combined "
                     "30-day stress, the LiST 2019 shocks are idiosyncratic only (annex slide 5), the fast run is acute (1 to 5 days).",
                     "El dossier 05 E.2 pide tres familias y dos horizontes y el SDD no nombra ninguno: el LCR es el estres combinado "
                     "a 30 dias, los choques LiST 2019 son solo idiosincraticos, la corrida rapida es aguda (1 a 5 dias)."),
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
    assert sorted(c) == sorted(CONVENTION_NAMES)
    return c


CONV = conventions()


# ------------------------------------------------------------------------------------------------------ the CBC and the ladder


def cbc_classes(basis: str, par: bool = False) -> list[dict]:
    """The CBC at 2022-12-31: the securities by type at the carrying values the FDIC reports, pledged securities encumbered pro
    rata, the haircuts of the conventions; on the fair-value basis the HTM loss is applied to the whole book, pro rata."""
    carrying = {"cash-and-balances": FDIC["CHBAL"], "reverse-repo": FDIC["FREPO"], "treasury": FDIC["SCUST"],
                "mortgage-backed": FDIC["SCMTGBK"], "other-agency": FDIC["SCASPNSUM"], "municipal": FDIC["SCMUNI"],
                "other-debt": FDIC["SCDOMO"] + FDIC["SCFORD"]}
    fields = {"cash-and-balances": ["CHBAL"], "reverse-repo": ["FREPO"], "treasury": ["SCUST"], "mortgage-backed": ["SCMTGBK"],
              "other-agency": ["SCASPNSUM"], "municipal": ["SCMUNI"], "other-debt": ["SCDOMO", "SCFORD"]}
    labels = {"cash-and-balances": txt("Cash and balances due", "Efectivo y saldos"),
              "reverse-repo": txt("Federal funds sold and reverse repos", "Fondos federales vendidos y repos inversos"),
              "treasury": txt("Treasury securities", "Valores del Tesoro"), "mortgage-backed": txt("Mortgage-backed securities", "Valores respaldados por hipotecas"),
              "other-agency": txt("Other agency securities", "Otros valores de agencias"), "municipal": txt("Municipal securities", "Valores municipales"),
              "other-debt": txt("Other debt securities", "Otros valores de deuda")}
    rows = {r[0]: r for r in SEC_ROWS}
    out = []
    for cid in carrying:
        is_sec = cid in ("treasury", "mortgage-backed", "other-agency", "municipal", "other-debt")
        cv = float(carrying[cid])
        fv = r6(cv * FV_FACTOR) if (is_sec and basis == "fair-value") else None
        used = fv if fv is not None else cv
        enc = r6(cv * PLEDGED_SHARE) if is_sec else 0.0
        _, _, _, margin, rule = rows[cid]
        h = sec_haircut(margin, rule)
        if par and cid in ("treasury", "mortgage-backed", "other-agency"):
            h = 0.0
        out.append({"class_id": cid, "label": labels[cid], "source_fields": fields[cid], "carrying_value": cv, "fair_value": fv,
                    "value_used": used, "encumbered": enc, "haircut": {"value": h, "rule": rule},
                    "liquidity_value": r6((used - enc) * (1 - h))})
    return out


def cbc_block(basis: str) -> dict:
    classes = cbc_classes(basis)
    return {
        "as_of": VD, "htm_valuation_basis": basis,
        "haircut_framework": {
            "label": txt("Federal Reserve discount window margins in force on 2023-03-10", "Margenes de la ventana de descuento de la Reserva Federal vigentes el 2023-03-10"),
            "central_bank": "Federal Reserve discount window", "effective_from": "2022-03-14", "effective_to": "2023-03-12",
            "source": "https://www.frbdiscountwindow.org/generalpages/historical_margins/2022/03142022_03122023_securities_table"},
        "classes": classes,
        "pledged": {"field": "SCPLEDGE", "amount": r6(sum(c["encumbered"] for c in classes)), "share_of_securities": r10(PLEDGED_SHARE)},
        "total_liquidity_value": r6(sum(c["liquidity_value"] for c in classes)),
    }


def segments_for(variant: str, mult: float = 1.0, uninsured_share: float | None = None) -> list[dict]:
    """The deposit segments of the central mapping: insured to other retail, uninsured to non-operational non-financial
    corporates, foreign offices to non-operational other financial (a sight deposit of a financial customer leaves on day 1)."""
    h = H[variant]
    depins, depuna = float(FDIC["DEPINS"]), float(FDIC["DEPUNA"])
    if uninsured_share is not None:
        tot = depins + depuna
        depuna, depins = tot * uninsured_share, tot * (1 - uninsured_share)
    adverse = variant in ("list-adverse", "fast-run", "htm-losses")
    q_retail = 0.00373218 if adverse else 0.00440873
    if variant == "fast-run":
        q_nfc, kind = fast_rate(), "calibrated-pre-2023"
    else:
        q_nfc, kind = (0.00688541 if adverse else 0.01065229), "transcribed-list-2019"
    which = "Adverse" if adverse else "Extreme"
    segs = []
    for name, cls, opening, q, sk, src in (
            ("retail-insured", "other-retail", depins, q_retail, "transcribed-list-2019",
             f"ECB LiST 2019 methodological note Table 3.3, other retail sight deposits, {which}"),
            ("non-operational-corporate", "non-operational-non-financial-corporates", depuna, q_nfc, kind,
             "calibrated on the pre-2023 Table A.1 rows by the calibration rule (c16-models)" if variant == "fast-run"
             else f"ECB LiST 2019 methodological note Table 3.3, non-operational sight deposits of non-financial corporates, {which}")):
        qm = min(q * mult, 1.0)
        cum, prod = [], 1.0
        for _ in range(h):
            prod *= 1.0 - qm
            cum.append(1.0 - prod)
        outs = [r6(opening * (cum[d] - (cum[d - 1] if d else 0.0))) for d in range(h)]
        segs.append({"segment": name, "list_class": cls, "mechanism": "open-maturity-compounding", "opening_balance": r6(opening),
                     "parameters": [{"name": "daily_rate", "value": r6(qm) if kind == "calibrated-pre-2023" and name != "retail-insured"
                                     else qm, "unit": "decimal-per-day", "source_kind": sk, "source": src}],
                     "daily_rates": [qm] * h, "cumulative_outflow_share": cum, "outflows": outs})
    fo = r6(float(FOREIGN))
    segs.append({"segment": "financial", "list_class": "non-operational-other-financial", "mechanism": "full-runoff", "opening_balance": fo,
                 "parameters": [{"name": "first_day_outflow_share", "value": 1.0, "unit": "share", "source_kind": "transcribed-list-2019",
                                 "source": "ECB LiST 2019 methodological note para 111: sight deposits of financial customers flow out in "
                                           "full on the first relevant day (foreign-office deposits mapped here, an assumption)"}],
                 "daily_rates": None, "cumulative_outflow_share": [1.0] * h, "outflows": [fo] + [0.0] * (h - 1)})
    return segs


def fast_rate() -> float:
    rates = [r6(implied(s, n)) for r, _, _, s, n in TABLE_A1 if r in CALIBRATED_ON]
    return {"maximum-implied-daily-rate": max, "median-implied-daily-rate": statistics.median,
            "mean-implied-daily-rate": statistics.fmean}[CONV["fast_run_calibration_rule"]["rule"]](rates)


def path_arrays(variant: str, segs: list[dict], cbc: dict) -> dict:
    h = H[variant]
    stack = [{"class_id": c["class_id"], "liquidity_value": [r6(c["liquidity_value"] * share_at(d + 1)) for d in range(h)]}
             for c in cbc["classes"]]
    total_out = [r6(sum(s["outflows"][d] for s in segs)) for d in range(h)]
    total_in = [0.0] * h
    cbc_total = [r6(sum(c["liquidity_value"][d] for c in stack)) for d in range(h)]
    cum, run = [], 0.0
    for d in range(h):
        run += total_out[d] - total_in[d]
        cum.append(r6(run))
    nlp = [r6(cbc_total[d] - cum[d]) for d in range(h)]
    return {"axis": "relevant-days", "day_index": list(range(1, h + 1)), "dates": relevant_days(h), "segments": segs, "other_outflows": [],
            "inflows": [], "total_outflows": total_out, "total_inflows": total_in, "cbc_stack": stack, "cbc_total": cbc_total,
            "cumulative_net_outflow": cum, "nlp": nlp}


def survival_of(nlp: list[float], h: int) -> dict:
    first = next((i + 1 for i, v in enumerate(nlp) if v < 0), None)
    return {"kind": "survives-horizon", "day": None, "horizon_days": h} if first is None else {"kind": "day", "day": first, "horizon_days": h}


def path_block(variant: str, ladder: dict) -> dict:
    h = H[variant]
    nlp = ladder["nlp"]
    low = min(nlp)
    p = {"ladder": ladder, "survival": survival_of(nlp, h), "minimum_nlp": {"value": low, "day": nlp.index(low) + 1}}
    if h >= 35:
        near, far = nlp[29], nlp[34]
        p["cliff"] = {"near_day": 30, "far_day": 35, "nlp_near": near, "nlp_far": far, "total_assets": float(FDIC["ASSET"]),
                      "value": (far - near) / FDIC["ASSET"]}
        p["cliff_reason"] = None
    else:
        p["cliff"] = None
        p["cliff_reason"] = txt(f"The horizon of {h} days is shorter than the far day 35 of the cliff diagnostic.",
                                f"El horizonte de {h} dias es menor que el dia 35 del diagnostico del acantilado.")
    return p


def sp_under(variant: str, mult: float = 1.0, uninsured_share: float | None = None, basis: str | None = None) -> tuple[dict, list[float]]:
    segs = segments_for(variant, mult, uninsured_share)
    cbc = cbc_block(basis or ("fair-value" if variant == "htm-losses" else "amortised-cost"))
    lad = path_arrays(variant, segs, cbc)
    return survival_of(lad["nlp"], H[variant]), lad["nlp"]


# ------------------------------------------------------------------------------------------------------ the LCR block


def lcr_block(central_category: str = "non-financial-corporate", detail: bool = True) -> dict:
    l1, l2a, l2b = 20_000_000.0, 8_000_000.0, 12_000_000.0   # fixture levels chosen to exercise the 15 percent cap
    adj15 = max(l2b - 15 / 85 * (l1 + l2a), l2b - 15 / 60 * l1, 0.0)
    adj40 = max(l2a + l2b - adj15 - 2 / 3 * l1, 0.0)
    hqla = l1 + l2a + l2b - adj15 - adj40

    def block(category: str) -> tuple[list[dict], list[dict]]:
        rate = {"operational": 0.25, "non-financial-corporate": 0.40, "other-legal-entity": 1.00}[category]
        ref = {"operational": "LCR99: operational deposits 25 percent", "non-financial-corporate": "LCR99: non-financial corporates 40 percent",
               "other-legal-entity": "LCR99: other legal entity customers 100 percent"}[category]
        outs = [("retail_less_stable", float(FDIC["DEPINS"]), 0.10, "LCR99: retail less stable deposits 10 percent"),
                (category.replace("-", "_"), float(FDIC["DEPUNA"]), rate, ref),
                ("other_legal_entity", float(FOREIGN), 1.00, "LCR99: other legal entity customers 100 percent (foreign-office deposits, an assumption)"),
                ("secured_other", float(FDIC["FREPP"]), 1.00, "LCR99: all other secured funding 100 percent")]
        ins = [("secured_lending_other", float(FDIC["FREPO"]), 1.00, "LCR99: maturing secured lending on other collateral 100 percent"),
               ("retail_and_nonfinancial_wholesale", 120_000_000.0, 0.50,
                "LCR99: retail and non-financial wholesale inflows 50 percent; fixture row, the balance is above the call-report loan book on purpose to exercise the 75 percent cap")]
        return ([{"category": c, "balance": r6(b), "rate": r, "amount": r6(b * r), "reference": f} for c, b, r, f in outs],
                [{"category": c, "balance": r6(b), "rate": r, "amount": r6(b * r), "reference": f} for c, b, r, f in ins])

    def ratio_for(category: str) -> float:
        o, i = block(category)
        to, ti = sum(x["amount"] for x in o), sum(x["amount"] for x in i)
        return hqla / (to - min(ti, 0.75 * to))

    outs, ins = block(central_category)
    to, ti = r6(sum(x["amount"] for x in outs)), r6(sum(x["amount"] for x in ins))
    counted = r6(min(ti, 0.75 * to))
    net = r6(to - counted)
    return {
        "label": "basel-formula-on-call-report-aggregates", "reported_or_regulatory": False,
        "statement": txt("A Basel LCR formula applied to FDIC call-report aggregates with stated assumptions and synthetic deposit "
                         "behaviour: not the bank's reported or regulatory LCR.",
                         "Una formula LCR de Basilea aplicada a agregados del reporte de llamada FDIC con supuestos declarados y "
                         "comportamiento sintetico de depositos: no es el LCR informado ni regulatorio del banco."),
        "hqla": {"l1": r6(l1), "l2a": r6(l2a), "l2b": r6(l2b), "adjusted_l1": r6(l1), "adjusted_l2a": r6(l2a), "adjusted_l2b": r6(l2b),
                 "adj_15": r6(adj15), "adj_40": r6(adj40), "hqla": r6(l1 + l2a + l2b - r6(adj15) - r6(adj40)),
                 "l2_share": r10((l2a + l2b - r6(adj15) - r6(adj40)) / (l1 + l2a + l2b - r6(adj15) - r6(adj40))),
                 "l2b_share": r10((l2b - r6(adj15)) / (l1 + l2a + l2b - r6(adj15) - r6(adj40))),
                 "caps": {"l2_cap": 0.4, "l2b_cap": 0.15}},
        "outflows": outs, "total_outflows": to, "inflows": ins, "total_inflows": ti, "inflow_cap": 0.75, "inflows_counted": counted,
        "net_outflows": net, "ratio": r10((l1 + l2a + l2b - r6(adj15) - r6(adj40)) / net),
        "mapping_sensitivity": [{"mapping_id": "central", "lcr_category": "non-financial-corporate", "ratio": r10(ratio_for("non-financial-corporate"))},
                                {"mapping_id": "band-operational", "lcr_category": "operational", "ratio": r10(ratio_for("operational"))},
                                {"mapping_id": "band-other-legal-entity", "lcr_category": "other-legal-entity", "ratio": r10(ratio_for("other-legal-entity"))}],
        "below_100_note": txt("A ratio below 100 percent under stress is not a breach: the institution is expected to monitor its decline "
                              "(ECB ILAAP guide, dossier 01 J.3).",
                              "Una razon bajo 100 por ciento bajo estres no es un incumplimiento: se espera monitorear su caida."),
    }


# ------------------------------------------------------------------------------------------------------ the other blocks


def deposits(dep: int, depdom: int, depuna: int, depins: int, depsm: int, deplg: int) -> dict:
    return {"dep": float(dep), "depdom": float(depdom), "depuna": float(depuna), "depins": float(depins), "depsmamt": float(depsm),
            "deplgamt": float(deplg), "denominators": {"insured_uninsured": "DEPDOM", "total": "DEP"},
            "uninsured_share_of_dep": r10(depuna / dep), "uninsured_share_of_depdom": r10(depuna / depdom),
            "size_threshold": {"value": 250000, "unit": "USD", "source": "FDIC BankFind definitions (addendum L3.1): the 250,000 USD threshold applies at 2022-12-31"}}


def item(iid: str, en: str, es: str, side: str, cat: str, field: str, reported, reason, assumption: str, amount: float,
         lc=None, rd=None, ins=None, fv=None) -> dict:
    return {"item_id": iid, "label": txt(en, es), "side": side, "category": cat, "source_field": field,
            "reported_amount": None if reported is None else float(reported), "reason_missing": reason, "assumption": assumption,
            "amount": float(amount), "liquidity_class": lc, "residual_days": rd, "insured": ins,
            "fair_value": None if fv is None else float(fv)}


def balance_sheet() -> dict:
    d = FDIC
    other_assets = d["ASSET"] - (d["CHBAL"] + d["FREPO"] + d["SCHA"] + d["SCAF"] + d["LNLSNET"])
    other_liab = d["ASSET"] - d["DEP"] - d["FREPP"] - d["OTHBFHLB"] - d["EQ"]
    items = [
        item("cash", "Cash and balances due from depository institutions", "Efectivo y saldos en instituciones", "asset", "cash", "CHBAL",
             d["CHBAL"], None, "Reported by the FDIC financials, taken as reserves at nominal value.", d["CHBAL"], "level_1", 0, None, d["CHBAL"]),
        item("reverse-repo", "Federal funds sold and reverse repurchase agreements", "Fondos federales vendidos y repos inversos", "asset", "reverse-repo",
             "FREPO", d["FREPO"], None, "Reported; an asset (addendum L3.1); assumed overnight, synthetic behaviour.", d["FREPO"], "non_hqla", 1, None, d["FREPO"]),
        item("securities-htm", "Securities held to maturity (amortised cost)", "Valores mantenidos al vencimiento (costo amortizado)", "asset",
             "securities-htm", "SCHA", d["SCHA"], None, "Reported at amortised cost; fair value from SCHF.", d["SCHA"], None, None, None, d["SCHF"]),
        item("securities-afs", "Securities available for sale (fair value)", "Valores disponibles para la venta (valor razonable)", "asset",
             "securities-afs", "SCAF", d["SCAF"], None, "Reported at fair value.", d["SCAF"], None, None, None, d["SCAF"]),
        item("loans", "Net loans and leases", "Prestamos y arrendamientos netos", "asset", "loans", "LNLSNET", d["LNLSNET"], None,
             "Reported; not counted in the CBC.", d["LNLSNET"], "non_hqla", None, None, None),
        item("other-assets", "Other assets", "Otros activos", "asset", "other-assets", "ASSET", None,
             txt("No single FDIC item: derived as ASSET minus the items above.", "No hay una partida FDIC unica: derivada como ASSET menos las partidas anteriores."),
             "Total assets less the listed asset items, synthetic aggregation.", other_assets, "non_hqla", None, None, None),
        item("deposits-insured", "Estimated insured deposits (domestic offices)", "Depositos asegurados estimados (oficinas domesticas)", "liability",
             "deposits-insured", "DEPINS", d["DEPINS"], None, "Reported; mapped to other retail sight deposits.", d["DEPINS"], None, 0, True, None),
        item("deposits-uninsured", "Estimated uninsured deposits (domestic offices)", "Depositos no asegurados estimados (oficinas domesticas)", "liability",
             "deposits-uninsured", "DEPUNA", d["DEPUNA"], None, "Reported estimate; mapped to non-operational non-financial corporates.", d["DEPUNA"],
             None, 0, False, None),
        item("deposits-foreign", "Foreign-office deposits", "Depositos en oficinas extranjeras", "liability", "deposits-foreign-office", "DEPFOR", None,
             txt("DEPFOR was not read: taken as DEP minus DEPDOM.", "DEPFOR no se leyo: tomado como DEP menos DEPDOM."),
             "Foreign-office deposits mapped to non-operational other financial customers, synthetic behaviour.", FOREIGN, None, 0, None, None),
        item("repo-borrowings", "Federal funds purchased and repurchase agreements", "Fondos federales comprados y repos", "liability", "repo-borrowings",
             "FREPP", d["FREPP"], None, "Reported; a liability (addendum L3.1).", d["FREPP"], None, 1, None, None),
        item("fhlb", "FHLB advances", "Anticipos FHLB", "liability", "fhlb-advances", "OTHBFHLB", d["OTHBFHLB"], None,
             "Reported; maturity profile not modelled.", d["OTHBFHLB"], None, None, None, None),
        item("other-liabilities", "Other liabilities", "Otros pasivos", "liability", "other-liabilities", "LIAB", None,
             txt("No single FDIC item: derived as ASSET minus deposits, repos, FHLB advances and equity.", "Derivada como ASSET menos depositos, repos, anticipos FHLB y patrimonio."),
             "Residual liabilities, synthetic aggregation.", other_liab, None, None, None, None),
        item("equity", "Total equity capital", "Capital patrimonial total", "liability", "equity", "EQ", d["EQ"], None, "Reported.", d["EQ"], None, None, None, None),
    ]
    return {
        "as_of": VD, "items": items, "total_assets": float(d["ASSET"]),
        "deposits": deposits(d["DEP"], d["DEPDOM"], d["DEPUNA"], d["DEPINS"], d["DEPSMAMT"], d["DEPLGAMT"]),
        "assumptions": [
            {"assumption_id": "deposit-mapping", "behaviour": "synthetic", "applies_to": "deposits",
             "statement": txt("Deposits are mapped to LiST classes by the named mapping table of the conventions: insured to other retail, "
                              "uninsured to non-operational non-financial corporates, foreign offices to non-operational other financial.",
                              "Los depositos se mapean a clases LiST por la tabla de mapeo nombrada de las convenciones.")},
            {"assumption_id": "pledged-pro-rata", "behaviour": "synthetic", "applies_to": "securities",
             "statement": txt("Pledged securities (SCPLEDGE) are encumbered pro rata across the securities types and leave the CBC.",
                              "Los valores pignorados (SCPLEDGE) se gravan a prorrata entre los tipos y salen del CBC.")},
            {"assumption_id": "no-committed-lines", "behaviour": "synthetic", "applies_to": "off-balance-sheet",
             "statement": txt("The FDIC financials read give no undrawn commitments: no drawdown and no collateral call is modelled (a scenario input of zero, labelled).",
                              "Los estados FDIC leidos no dan compromisos no girados: no se modela giro ni llamada de colateral.")},
        ],
    }


def data_block() -> dict:
    fields = ["ASSET", "DEP", "DEPDOM", "DEPUNA", "DEPINS", "DEPSMAMT", "DEPLGAMT", "SC", "SCHA", "SCHF", "SCAA", "SCAF", "CHBAL", "FREPO", "FREPP",
              "OTHBFHLB", "LNLSNET", "EQ", "SCUST", "SCMTGBK", "SCASPNSUM", "SCMUNI", "SCDOMO", "SCFORD", "SCPLEDGE"]
    src = "https://api.fdic.gov/banks/financials (CERT 24735; fixture: not read by this document)"
    return {"call_reports": [{"report_date": "2022-12-31", "source": src, "fields": fields},
                             {"report_date": "2022-06-30", "source": src, "fields": ["DEP", "DEPDOM", "DEPUNA", "DEPINS", "SCHA", "SCHF", "SCAA", "SCAF"]},
                             {"report_date": "2021-12-31", "source": src, "fields": ["DEP", "DEPDOM", "DEPUNA", "DEPINS", "SCHA", "SCHF", "SCAA", "SCAF"]}],
            "data_cutoff": "2022-12-31", "read_up_to_valuation_date": True,
            "rule": txt("No call report dated after the valuation date is read.", "No se lee ningun reporte de llamada posterior a la fecha de valoracion.")}


def htm_numbers() -> dict:
    d = FDIC
    return {"htm_amortised_cost": float(d["SCHA"]), "htm_fair_value": float(d["SCHF"]), "htm_unrealised": float(d["SCHF"] - d["SCHA"]),
            "afs_amortised_cost": float(d["SCAA"]), "afs_fair_value": float(d["SCAF"]), "afs_unrealised": float(d["SCAF"] - d["SCAA"])}


def htm_block() -> dict:
    without, with_ = cbc_block("amortised-cost")["total_liquidity_value"], cbc_block("fair-value")["total_liquidity_value"]
    par = r6(sum(c["liquidity_value"] for c in cbc_classes("amortised-cost", par=True)))
    model_fv = 76_500_000.0
    rep_fv, unreal = float(FDIC["SCHF"]), float(FDIC["SCHF"] - FDIC["SCHA"])
    return {
        "reported": htm_numbers(),
        "application": {"method": "whole-book", "statement": txt(
            "The held-to-maturity fair-value loss (SCHF minus SCHA) is applied to the securities book as a whole, pro rata by type: a "
            "stated assumption, never a reported by-type loss (A3).", "La perdida a valor razonable HTM se aplica al libro completo, a prorrata por tipo.")},
        "cbc_without_loss": without, "cbc_with_loss": with_, "cbc_removed": r6(without - with_),
        "btfp_par": {"label": txt("Counterfactual: Bank Term Funding Program par valuation, announced 2023-03-12 after the run; par is proxied by the carrying value",
                                  "Contrafactual: valoracion a la par del BTFP, anunciada el 2023-03-12 tras la corrida"),
                     "announced": "2023-03-12", "cbc_at_par": par, "uplift": r6(par - without)},
        "revaluation": {"status": "evaluated", "engine_ref": "engine-irrbb-api", "curve_source": "US Treasury par yield curve of 2022-12-30 (fixture: not read)",
                        "curve_date": "2022-12-30", "model_fair_value": model_fv, "reported_fair_value": rep_fv,
                        "difference": r6(model_fv - rep_fv), "relative_difference": r10(abs(model_fv - rep_fv) / abs(unreal)), "reason": None}}


# ------------------------------------------------------------------------------------------------------ the scoring block


def light_of(ratio: float) -> str:
    return "green" if ratio >= 0.8 else "amber" if ratio >= 0.5 else "red"


def anchor() -> dict:
    return {"label": txt("Labelled anchor, not a forecast: SVB's observed 85 percent in 2 days (Table A.1) and the daily rate it implies",
                         "Ancla rotulada, no un pronostico: el 85 por ciento en 2 dias observado en SVB y la tasa diaria implicita"),
            "source": "BCBS d555 Box A Table A.1 (SVB 2023); Federal Reserve review of SVB supervision, 2023-04-28",
            "outflow_share": 0.85, "days": 2, "implied_daily_rate": r6(implied(0.85, 2)), "forecast_claim": False}


def modelled(segs: list[dict], horizon: int) -> float:
    return r6(sum(sum(s["outflows"][:horizon]) for s in segs))


def scoring_block(variant: str, segs: list[dict], lcr: dict | None) -> dict:
    h = H[variant]
    base = r6(sum(s["opening_balance"] for s in segs))
    dep = float(FDIC["DEP"])
    if variant == "lcr-standard":
        amount = r6(sum(x["amount"] for x in lcr["outflows"][:3]))
        at_model = {"horizon_days": h, "amount": amount, "share_of_model_base": r10(amount / base)}
        modelled_out = {"at_event_horizon": None, "at_event_horizon_reason": txt(
            "The LCR defines one 30-day aggregate and no daily path, so no outflow exists at the 2-day event horizon: the comparison is at the model's own horizon.",
            "El LCR define un agregado a 30 dias sin trayectoria diaria: la comparacion es en el horizonte propio del modelo."), "at_model_horizon": at_model}
        chosen_share, chosen_amount, compared = at_model["share_of_model_base"], amount, "model-horizon"
    else:
        amount_ev = modelled(segs, 2)
        at_model = {"horizon_days": h, "amount": modelled(segs, h), "share_of_model_base": r10(modelled(segs, h) / base)}
        at_event = {"horizon_days": 2, "amount": amount_ev, "share_of_model_base": r10(amount_ev / base)}
        modelled_out = {"at_event_horizon": at_event, "at_event_horizon_reason": None, "at_model_horizon": at_model}
        chosen_share, chosen_amount, compared = at_event["share_of_model_base"], amount_ev, "event-horizon"
    call_share = r10(140_000_000.0 / dep)
    den = []
    for did, label, d_amt, r_amt, r_share, m_share, src in (
            ("board-stated-share", txt("Board review: roughly 85 percent of the deposit base", "Revision de la Junta: cerca de 85 por ciento de la base de depositos"),
             None, None, 0.85, chosen_share, "Federal Reserve, Review of the Federal Reserve's Supervision and Regulation of SVB, 2023-04-28"),
            ("call-report-dep", txt("Over 40 plus 100 billion USD against the call report's DEP", "Mas de 40 mas 100 mil millones de USD contra el DEP del reporte de llamada"),
             dep, 140_000_000.0, call_share, r10(chosen_amount / dep), "Federal Reserve review (the amounts) and FDIC call report 2022-12-31 (DEP)")):
        ratio = r10(m_share / r_share)
        den.append({"id": did, "label": label, "denominator_amount": d_amt, "realised_amount": r_amt, "realised_share": r_share, "source": src,
                    "modelled_share": m_share, "compared_at": compared, "shortfall": r10(r_share - m_share), "ratio": ratio, "light": light_of(ratio)})
    rows = []
    for rid, bank, year, share, days in TABLE_A1:
        role = ("calibration" if year < 2023 else "scored") if variant == "fast-run" else "reference"
        if variant == "lcr-standard" or days > h:
            rows.append({"row_id": rid, "bank": bank, "year": year, "horizon_days": days, "observed_share": share, "modelled_share": None, "error": None,
                         "role": role, "reason": txt("The horizon of this row is beyond the model's ladder (or the variant has no daily path).",
                                                     "El horizonte de esta fila excede la escalera del modelo (o la variante no tiene trayectoria diaria).")})
        else:
            ms = r10(modelled(segs, days) / base)
            rows.append({"row_id": rid, "bank": bank, "year": year, "horizon_days": days, "observed_share": share, "modelled_share": ms,
                         "error": r10(share - ms), "role": role, "reason": None})
    return {"event": {"label": txt("The deposit run of 9 and 10 March 2023, the bank that failed on 2023-03-10", "La corrida de depositos del 9 y 10 de marzo de 2023"),
                      "event_date": "2023-03-10", "horizon_days": 2, "source": "Federal Reserve review of SVB supervision, 2023-04-28"},
            "model_deposit_base": base, "modelled_outflow": modelled_out, "denominators": den, "svb_anchor": anchor(), "table_a1_scoring": rows}


def time_block(variant: str, survival_values: tuple) -> list[dict]:
    h = H[variant]
    out = []
    for as_of, dep, depdom, depuna, depins, loss, a_cbc, f_cbc, surv in (
            ("2021-12-31", 200_000_000, 180_000_000, 140_000_000, 10_000_000, -975_000.0, 90_000_000.0, 89_000_000.0, survival_values[0]),
            ("2022-06-30", 190_000_000, 170_000_000, 150_000_000, 10_000_000, -11_239_000.0, 80_000_000.0, 70_000_000.0, survival_values[1])):
        out.append({"as_of": as_of, "report_date": as_of,
                    "deposits": deposits(dep, depdom, depuna, depins, round(depdom * 0.03), depdom - round(depdom * 0.03)),
                    "htm_unrealised_loss": loss, "cbc_amortised_basis": a_cbc, "cbc_fair_value_basis": f_cbc,
                    "survival": None if surv is None else ({"kind": "survives-horizon", "day": None, "horizon_days": h} if surv == 0
                                                           else {"kind": "day", "day": surv, "horizon_days": h}),
                    "lcr_ratio": 2.5 if variant == "lcr-standard" and as_of == "2021-12-31" else (1.9 if variant == "lcr-standard" else None)})
    return out


# ------------------------------------------------------------------------------------------------------ envelope helpers


def model_summary(mid: str, rung: str, with_details: bool = False) -> dict:
    m = {"id": mid, "family": "liquidity", "rung": rung, "title": txt(f"Fixture model {mid}", f"Modelo de ejemplo {mid}"),
         "short_title": txt(mid, mid), "engine": "riskvalidation", "engine_version": "fixture", "licence": "MIT", "calibration": None,
         "parameters": {}, "checkpoint_sha256": None}
    if with_details:
        m["details"] = {}
    return m


def provenance(truth: str) -> dict:
    return {"truth_status": truth, "inputs": [{"source": "fixture-not-a-result", "class": "fixture", "files": []}],
            "licence_classes": {"fixture-not-a-result": "fixture"}, "generators": ["fixture:u11-s-contracts"], "seed": 0,
            "code_version": "fixture", "riskvalidation_version": None}


def tr(test_id: str, segment, statistic, metric, light: str, n, h0: str, alt: str, reference: str, notes: str, thresholds: dict) -> dict:
    ne = light == "not_evaluated"
    return {"test_id": test_id, "model_id": "liquidity-ladder", "segment": segment, "statistic": None if ne else statistic, "p_value": None,
            "metric": None if ne else metric, "h0": h0, "alternative": alt, "policy_version": "contraste-liquidity-battery-1.0.0",
            "alpha_amber": None, "alpha_red": None, "light": light, "n": n, "n_events": None, "inputs_hash": ZERO_HASH,
            "reference": reference, "notes": notes, "extras": {"thresholds": thresholds, "fixture": True}}


def golden_row() -> dict:
    f = 1 - (1 - 0.00103258) ** 125
    return tr("liq.list_compounding_golden", None, r10(abs(f - 0.121148)), r10(f), "green", 125, "the compounding reproduces the LiST example",
              "it does not", "dossier 05 E.1 line 237: 1 - (1 - 0.00103258)^125 = 0.121148", "fixture row: the golden of the example",
              {"tolerance": 5e-7})


def finding(fid: str, sev: str, tests: list[str], en: str, es: str) -> dict:
    return {"id": fid, "severity": sev, "status": "open", "evidence": tests, "title": txt(en, es)}


def impact_survival(sv: dict | None, h: int, reason: str | None = None) -> dict:
    if sv is None:
        return {"value": None, "unit": "relevant days", "label": txt(reason or "No daily path.", "Sin trayectoria diaria.")}
    if sv["kind"] == "survives-horizon":
        return {"value": None, "unit": "relevant days", "label": txt(f"Survival period: survives the {h}-day horizon", f"Periodo de supervivencia: sobrevive el horizonte de {h} dias")}
    return {"value": float(sv["day"]), "unit": "relevant days", "label": txt("Survival period (first day the NLP is negative)", "Periodo de supervivencia (primer dia con NLP negativo)")}


VARIANT_LABEL = {
    "lcr-standard": ("LCR standard run-off", "LCR con salidas estandar", "The Basel LCR of the call-report balance sheet over the 30-day combined stress.",
                     "El LCR de Basilea del balance del reporte de llamada bajo el estres combinado a 30 dias."),
    "list-adverse": ("LiST adverse", "LiST adverso", "ECB LiST 2019 Adverse daily compounding over the six-month horizon.",
                     "Capitalizacion diaria LiST 2019 Adverso del BCE a seis meses."),
    "list-extreme": ("LiST extreme", "LiST extremo", "ECB LiST 2019 Extreme daily compounding over the six-month horizon.",
                     "Capitalizacion diaria LiST 2019 Extremo del BCE a seis meses."),
    "fast-run": ("2023 fast run", "Corrida rapida 2023", "Daily compounding calibrated on the pre-2023 Table A.1 rows, scored on 2023.",
                 "Capitalizacion diaria calibrada con las filas de la Tabla A.1 anteriores a 2023, evaluada en 2023."),
    "htm-losses": ("HTM losses in CBC", "Perdidas HTM en el CBC", "LiST Adverse with the held-to-maturity book at fair value in the CBC.",
                   "LiST Adverso con el libro mantenido al vencimiento a valor razonable en el CBC."),
}


# ------------------------------------------------------------------------------------------------------ the documents


def scenario_doc(variant: str) -> dict:
    h = H[variant]
    row = next(r for r in CONV["variant_scenarios"]["rows"] if r["variant"] == variant)
    basis = "fair-value" if variant == "htm-losses" else "amortised-cost"
    cbc = cbc_block(basis)
    segs = segments_for(variant)
    if variant == "lcr-standard":
        # the LCR defines no daily path: the deposit segments of the central mapping carry the 30-day LCR rates as full roll-offs
        segs = []
        lcr = lcr_block()
        path = None
        for name, cls, bal, rate_row in (("retail-insured", "other-retail", float(FDIC["DEPINS"]), lcr["outflows"][0]),
                                         ("non-operational-corporate", "non-operational-non-financial-corporates", float(FDIC["DEPUNA"]), lcr["outflows"][1]),
                                         ("financial", "non-operational-other-financial", float(FOREIGN), lcr["outflows"][2])):
            segs.append({"segment": name, "balance": bal, "rate": rate_row["rate"]})
        seg_for_scoring = [{"opening_balance": s["balance"], "outflows": [r6(s["balance"] * s["rate"])]} for s in segs]
        sc = scoring_block(variant, seg_for_scoring, lcr)
        survival = None
    else:
        lcr = None
        lad = path_arrays(variant, segs, cbc)
        path = path_block(variant, lad)
        survival = path["survival"]
        sc = scoring_block(variant, segs, None)
    surv_tb = {"lcr-standard": (None, None), "list-adverse": (0, 90), "list-extreme": (0, 70), "fast-run": (0, 3), "htm-losses": (0, 80)}[variant]
    htm = htm_block() if variant == "htm-losses" else None
    reasons = {
        "path": txt("The LCR is a 30-day aggregate ratio: its formula gives no daily path, so no ladder, survival period or cliff is stated.",
                    "El LCR es una razon agregada a 30 dias: su formula no da trayectoria diaria."),
        "lcr": txt("This variant runs the run-off ladder, not the LCR formula.", "Esta variante corre la escalera de salidas, no la formula del LCR."),
        "htm": txt("Only the HTM variant takes the held-to-maturity book at fair value.", "Solo la variante HTM toma el libro a valor razonable.")}
    o = {
        "kind": "scenario", "valuation_date": VD, "currency": "USD",
        "units": {"money_scale": "thousands", "rate": "decimal-per-day", "horizon": "days", "dates": "ISO-8601"},
        "bank": {"name": "Silicon Valley Bank (CERT 24735), failed 2023-03-10", "cert": 24735, "aggregates": "real", "behaviour": "synthetic",
                 "deposits": "synthetic",
                 "notice": txt("Real FDIC call-report aggregates used as public aggregates only, with synthetic behaviour and synthetic deposits: "
                               "the case does not represent the bank and certifies no model.",
                               "Agregados reales del reporte de llamada FDIC usados solo como agregados publicos, con comportamiento y depositos "
                               "sinteticos: el caso no representa al banco ni certifica ningun modelo.")},
        "variant": {"id": variant, "label": txt(*VARIANT_LABEL[variant][:2]), "description": txt(VARIANT_LABEL[variant][2], VARIANT_LABEL[variant][3]),
                    "scenario_family": row["scenario_family"], "phase": row["phase"], "parameter_set": row["parameter_set"],
                    "horizon_days": h, "axis": row["axis"]},
        "conventions": CONV, "data": data_block(),
        "aggregate_record": None, "aggregate_record_reason": None, "balance_sheet": balance_sheet(), "cbc": cbc,
        "contractual_ladder": contractual_ladder(),
        "path": path, "path_reason": reasons["path"] if path is None else None,
        "lcr": lcr, "lcr_reason": reasons["lcr"] if lcr is None else None,
        "htm": htm, "htm_reason": reasons["htm"] if htm is None else None,
        "scoring": sc, "time_block": time_block(variant, surv_tb),
    }
    if variant == "list-adverse":
        o["aggregate_record"] = {"source": "Federal Reserve H.8 release tables (fixture values, not read)", "series": [
            {"series_id": "h8-deposits-large-domestic", "label": txt("Deposits, large domestically chartered banks (fixture)", "Depositos, bancos grandes domesticos (ejemplo)"),
             "unit": "USD billions, seasonally adjusted (fixture)", "points": [{"date": "2023-03-01", "value": 100.0}, {"date": "2023-03-08", "value": 99.0},
                                                                              {"date": "2023-03-15", "value": 95.0}]}]}
    else:
        o["aggregate_record_reason"] = txt("Fixture: the H.8 release tables are not read; the aggregate record is omitted with this statement.",
                                           "Ejemplo: las tablas H.8 no se leen; el registro agregado se omite con esta declaracion.")
    tests, findings = [golden_row()], []
    tests.append(tr("liq.cbc_haircut_rules", None, 0.0, 7.0, "green", 7, "the haircut rules are applied exactly", "a rule deviates",
                    "dossier 05 E.1 line 238 (ECB LiST note para 74)", "fixture row", {"tolerance": 1e-12}))
    for d in sc["denominators"]:
        tests.append(tr("liq.runoff_adequacy_back_test", d["id"], d["ratio"], d["shortfall"], d["light"], 1, "the modelled outflow reaches the realised outflow",
                        "the model under-states the run", "dossier 08 E.3 lines 566-568; Q5", f"fixture row: compared at the {d['compared_at']}",
                        {"ratio_green": 0.8, "ratio_amber": 0.5}))
        if d["light"] != "green":
            findings.append(finding(f"F-liq-adequacy-{d['id']}", "S2" if d["light"] == "red" else "S3", ["liq.runoff_adequacy_back_test"],
                                    f"The modelled outflow is {d['ratio']:.3f} of the realised outflow ({d['id']})",
                                    f"La salida modelada es {d['ratio']:.3f} de la realizada ({d['id']})"))
    if path is not None:
        tests.append(tr("liq.nlp_identity", None, 0.0, 0.0, "green", h, "NLP = CBC - cumulative net outflow", "the identity breaks",
                        "dossier 05 E.1 line 234", "fixture row", {"tolerance": 1e-6}))
        c = path["cliff"]
        if c is None:
            tests.append(tr("liq.cliff_effect_diagnostic", None, None, None, "not_evaluated", None, "no cliff", "a cliff", "dossier 05 E.1 line 236",
                            f"fixture: the horizon of {h} days is shorter than day 35", {"amber": -0.01, "red": -0.03}))
        else:
            v = c["value"]
            tests.append(tr("liq.cliff_effect_diagnostic", None, v, c["nlp_far"] - c["nlp_near"], "green" if v >= -0.01 else "amber" if v >= -0.03 else "red", h,
                            "no cliff", "a cliff", "dossier 05 E.1 line 236", "fixture row", {"amber": -0.01, "red": -0.03}))
    if variant == "list-adverse":
        shares = CONV["uninsured_share_grid"]["values"]
        sps = [sp_under("list-adverse", 1.0, s)[0] for s in shares]
        keys = [math.inf if s["kind"] == "survives-horizon" else s["day"] for s in sps]
        inv = sum(1 for a, b in zip(keys, keys[1:]) if b > a)
        tests.append(tr("liq.uninsured_share_sensitivity", None, float(inv), float(len(shares)), "green" if inv == 0 else "red", len(shares),
                        "the survival period does not lengthen with the uninsured share", "it lengthens", "dossier 05 E.5 rung 4",
                        "fixture row: the survival period under each share of the grid", {"tolerance_days": 0}))
    if variant == "list-extreme":
        a, _ = sp_under("list-adverse")
        e = survival_of(segments_nlp("list-extreme"), 125)
        ka = a["day"] if a["kind"] == "day" else math.inf
        ke = e["day"] if e["kind"] == "day" else math.inf
        tests.append(tr("liq.survival_monotone_in_severity", None, 0.0 if ke <= ka else 1.0, float(ka if ka != math.inf else 125), "green" if ke <= ka else "red", 2,
                        "the survival period does not lengthen with severity", "it lengthens", "dossier 05 E.5", "fixture row: Adverse then Extreme", {"tolerance_days": 0}))
    if variant == "fast-run":
        tests.append(tr("liq.runoff_vs_generator_truth", "non-operational-corporate", 1.1, 0.0004, "green", 5,
                        "the model's rate equals the generator's truth", "it differs", "dossier 08 G.2 line 698", "fixture row",
                        {"se_green": 2.0, "se_red": 3.0}))
    if variant == "htm-losses":
        h_ = htm
        tests.append(tr("liq.htm_loss_effect", None, h_["cbc_removed"], h_["cbc_removed"] / h_["cbc_without_loss"], "green", 1,
                        "the unrealised loss reduces the CBC and does not lengthen survival", "it does not", "dossier 05 E.2 line 263 and E.5",
                        "fixture row", {"tolerance": 0.0}))
        rv = h_["revaluation"]
        tests.append(tr("liq.htm_revaluation_vs_reported", None, rv["relative_difference"], rv["difference"], "green", 1,
                        "the revalued HTM book matches the reported fair value", "it differs", "U11 sizing decision Q11", "fixture row",
                        {"green": 0.05, "amber": 0.15}))
    doc = {
        "schema": "contraste.case/v1", "case_id": "C16", "variant_id": f"fixture-{variant}", "model": [model_summary("liquidity-ladder", "behavioural-ladder")],
        "outputs": o, "tests": tests,
        "impact": {"lcr": {"value": lcr["ratio"] if lcr else None, "unit": "ratio", "label": txt("LCR, a Basel formula on call-report aggregates", "LCR, una formula de Basilea sobre agregados del reporte de llamada")}
                   if lcr else {"value": None, "unit": "ratio", "label": txt("No LCR in this variant", "Sin LCR en esta variante")},
                   "survival_days": impact_survival(survival, h, "The LCR formula gives no daily path, so no survival period.")},
        "findings": findings, "provenance": provenance("synthetic-calibrated"), "lane": {"lane": "precompute", "reasons": ["fixture"]},
    }
    return doc


def segments_nlp(variant: str) -> list[float]:
    return sp_under(variant)[1]


def contractual_ladder() -> dict:
    rows = [(0, 1, 15_000_000.0, 150_000_000.0), (1, 7, 2_000_000.0, 8_000_000.0), (7, 30, 6_000_000.0, 5_000_000.0), (30, 90, 12_000_000.0, 4_000_000.0),
            (90, 180, 15_000_000.0, 3_000_000.0), (180, 365, 18_000_000.0, 2_000_000.0), (365, None, 80_000_000.0, 3_378_000.0)]
    out, cum = [], 0.0
    for lo, hi, i, o in rows:
        cum += i - o
        out.append({"from_day": lo, "to_day": hi, "inflows": i, "outflows": o, "gap": r6(i - o), "cumulative_gap": r6(cum)})
    return {"buckets": out, "reference": "dossier 05 E.5 rung 1; SRP50 contractual maturity mismatch (01 G.3 lines 642-643); fixture values"}


def solve_multiplier(variant: str, target: int) -> float | None:
    segs0 = segments_for(variant)
    qmax = max(s["daily_rates"][0] for s in segs0 if s["daily_rates"])
    cap = 1.0 / qmax
    lo, hi = 1.0, cap * 0.999999

    def sp(m: float) -> float:
        s, _ = sp_under(variant, m)
        return math.inf if s["kind"] == "survives-horizon" else s["day"]

    if sp(lo) <= target or sp(hi) > target:
        return None
    for _ in range(80):
        mid = (lo + hi) / 2
        if sp(mid) <= target:
            hi = mid
        else:
            lo = mid
    m = math.ceil(hi * 1e6) / 1e6
    return m if sp(m) == target else None


def reverse_doc() -> dict:
    target = CONV["reverse_target_days"]["value"]
    bases = []
    for variant in ("list-adverse", "list-extreme", "fast-run"):
        segs0 = segments_for(variant)
        qmax = max(s["daily_rates"][0] for s in segs0 if s["daily_rates"])
        cap = 1.0 / qmax
        grid_ms = [m for m in CONV["runoff_multiplier_grid"]["values"] if m <= cap]
        curve = [{"multiplier": m, "survival": sp_under(variant, m)[0]} for m in grid_ms]
        h = H[variant]
        m_star = solve_multiplier(variant, target) if target < h else None
        if m_star is None:
            solved = {"status": "refused", "multiplier": None, "survival_at_multiplier": None, "target_days": target, "round_trip_error": None,
                      "refusal_reason": txt(f"The target of {target} days is not below the {h}-day horizon of the ladder, so a survival period under it "
                                            "cannot be separated from surviving the horizon: no bracket exists.",
                                            f"El objetivo de {target} dias no es menor que el horizonte de {h} dias: no existe un intervalo.")}
        else:
            s, _ = sp_under(variant, m_star)
            solved = {"status": "solved", "multiplier": m_star, "survival_at_multiplier": s["day"], "target_days": target,
                      "round_trip_error": float(s["day"] - target), "refusal_reason": None}
        bases.append({"base_id": variant, "parameter_set": variant if variant != "fast-run" else "fast-run",
                      "label": txt(VARIANT_LABEL[variant][0], VARIANT_LABEL[variant][1]), "base_survival": curve[0]["survival"],
                      "max_multiplier": r6(cap), "curve": curve, "solved": solved})
    o = {"kind": "reverse-stress", "valuation_date": VD, "currency": "USD",
         "units": {"money_scale": "thousands", "rate": "decimal-per-day", "horizon": "days", "dates": "ISO-8601"},
         "bank": scenario_doc("list-adverse")["outputs"]["bank"], "conventions": CONV,
         "target": {"days": target, "statement": txt("The run-off multiplier at which the survival period first falls to 30 days (dossier 05 E.5 rung 5).",
                                                     "El multiplicador de salidas con el que el periodo de supervivencia cae por primera vez a 30 dias.")},
         "cap_rule": {"each_rate_below_one": True, "statement": txt("The multiplier scales every deposit segment's daily rate and is capped so that each rate stays below 1; a rate already at 1 stays.",
                                                                    "El multiplicador escala la tasa diaria de cada segmento y se limita para que cada tasa quede bajo 1.")},
         "bases": bases}
    tests = []
    for b in bases:
        s = b["solved"]
        if s["status"] == "solved":
            tests.append(tr("liq.reverse_stress_round_trip", b["base_id"], abs(s["survival_at_multiplier"] - target), s["multiplier"], "green", 1,
                            "the solved multiplier returns the target", "it does not", "dossier 05 E.5 line 279", "fixture row", {"tolerance_days": 0}))
        else:
            tests.append(tr("liq.reverse_stress_round_trip", b["base_id"], None, None, "not_evaluated", None, "the solved multiplier returns the target", "it does not",
                            "dossier 05 E.5 line 279", "fixture: the target is not bracketed, the multiplier is refused with its reason", {"tolerance_days": 0}))
    tests.append(tr("liq.survival_monotone_in_severity", None, 0.0, float(len(bases)), "green", len(bases), "SP(m) does not lengthen with the multiplier",
                    "it lengthens", "dossier 05 E.5", "fixture row", {"tolerance_days": 0}))

    def mi(b: dict, label: str) -> dict:
        s = b["solved"]
        return {"value": s["multiplier"], "unit": "multiple of the daily rates", "label": txt(label, label)}

    return {"schema": "contraste.case/v1", "case_id": "C16", "variant_id": "fixture-reverse", "model": [model_summary("liquidity-ladder", "reverse-stress")],
            "outputs": o, "tests": tests,
            "impact": {"multiplier_list_adverse": mi(bases[0], "Reverse-stress multiplier, LiST Adverse"),
                       "multiplier_list_extreme": mi(bases[1], "Reverse-stress multiplier, LiST Extreme"),
                       "multiplier_fast_run": mi(bases[2], "Reverse-stress multiplier, fast run (refused)")},
            "findings": [], "provenance": provenance("synthetic-calibrated"), "lane": {"lane": "precompute", "reasons": ["fixture"]}}


def models_doc() -> dict:
    rates = [{"row_id": r, "implied_daily_rate": r6(implied(s, n))} for r, _, _, s, n in TABLE_A1 if r in CALIBRATED_ON]
    order = {r: i for i, r in enumerate(CALIBRATED_ON)}
    rates.sort(key=lambda x: order[x["row_id"]])
    gold = [("stable-retail-adverse", 0.00103258, 125, "dossier-05-line-237"), ("stable-retail-extreme", 0.00161494, 125, "recomputed"),
            ("other-retail-adverse", 0.00373218, 125, "recomputed"), ("non-operational-nfc-adverse-2-days", 0.00688541, 2, "recomputed"),
            ("committed-credit-facilities-adverse-63-days", 0.00202704, 63, "recomputed")]
    fit = {
        "currency": "USD", "units": {"money_scale": "thousands", "rate": "decimal-per-day", "horizon": "days", "dates": "ISO-8601"},
        "bank": scenario_doc("list-adverse")["outputs"]["bank"], "conventions": CONV,
        "parameter_sets": [
            {"set_id": "basel-lcr", "source": "riskvalidation.regulatory.lcr_nsfr (BCBS LCR20, LCR30, LCR40, LCR99, in force 2019-12-15)", "source_kind": "transcribed-basel-lcr"},
            {"set_id": "list-adverse", "source": "ECB LiST 2019 methodological note, Tables 3.2 and 3.3, Adverse", "source_kind": "transcribed-list-2019"},
            {"set_id": "list-extreme", "source": "ECB LiST 2019 methodological note, Tables 3.2 and 3.3, Extreme", "source_kind": "transcribed-list-2019"},
            {"set_id": "fast-run", "source": "calibrated on the pre-2023 Table A.1 rows by the calibration rule", "source_kind": "calibrated-pre-2023"}],
        "list_parameters": {
            "source": "ECB LiST 2019 methodological note, February 2019, Tables 3.2 and 3.3 and paras 119 to 126",
            "attribution": "European Central Bank, cited as the source; the figures are the note's own and any recomputed figure is labelled recomputed",
            "contractual_outflows": [{"item": i, "baseline": b, "adverse": a, "extreme": e} for i, b, a, e in LIST_CONTRACTUAL],
            "open_maturity_daily": [{"item": i, "baseline": b, "adverse": a, "extreme": e} for i, b, a, e in LIST_OPEN],
            "contractual_inflows": [{"item": i, "baseline": b, "adverse": a, "extreme": e} for i, b, a, e in LIST_INFLOWS],
            "committed_drawdown": [{"item": i, "adverse": a, "extreme": e} for i, a, e in LIST_DRAWDOWN],
            "relevant_days_six_months": 125, "relevant_days_three_months": 63,
            "calendar_note": txt("The rates are defined on the 2019 TARGET2 relevant-day calendar (125 relevant days in six months); the C16 ladder runs on the US business-day convention.",
                                 "Las tasas se definen sobre el calendario TARGET2 de 2019 (125 dias en seis meses); la escalera de C16 usa dias habiles de EE.UU.")},
        "list_goldens": [{"id": i, "daily_rate": q, "days": n, "cumulative_outflow": r10(1 - (1 - q) ** n), "label": lab} for i, q, n, lab in gold],
        "table_a1": {"source": "BCBS, Report on the 2023 banking turmoil (d555), Box A, Table A.1",
                     "attribution": "Bank for International Settlements, source cited; one table within the limited-extract terms (addendum L2.1)",
                     "rows": [{"row_id": r, "bank": b, "year": y, "outflow_share": s, "days": n} for r, b, y, s, n in TABLE_A1],
                     "lcr_range": {"label": "LCR deposit outflow rates", "low": 0.03, "high": 0.40, "days": 30}},
        "calibration": {"split": {"calibrated_on": CALIBRATED_ON, "scored_on": SCORED_ON}, "implied_daily_rates": rates,
                        "fitted_daily_rate": {"value": fast_rate(), "unit": "decimal-per-day", "source_kind": "calibrated-pre-2023",
                                              "source": "maximum of the implied daily rates of the pre-2023 Table A.1 rows (the calibration rule)"},
                        "anchor": anchor(),
                        "statement": txt("Calibrated on pre-2023 rows, scored on the 2023 rows; the SVB observation is a labelled anchor, not a forecast.",
                                         "Calibrado con filas anteriores a 2023, evaluado en las filas de 2023; la observacion de SVB es un ancla rotulada.")},
        "generator": {"config": {"truth_status": "synthetic-known-truth", "seed": 0, "n_depositors": 100000, "horizon_days": 125, "segments": [
            {"segment": "retail-insured", "share_of_deposits": 0.057, "calm_daily_hazard": 0.0001, "stress_daily_hazard": 0.00373218, "p_enter_stress": 0.01, "p_exit_stress": 0.05,
             "basis": txt("Fixture: the share of DEPINS in the deposit base", "Ejemplo: la proporcion de DEPINS")},
            {"segment": "non-operational-corporate", "share_of_deposits": 0.864, "calm_daily_hazard": 0.0002, "stress_daily_hazard": 0.00688541, "p_enter_stress": 0.01, "p_exit_stress": 0.05,
             "basis": txt("Fixture: the share of DEPUNA in the deposit base", "Ejemplo: la proporcion de DEPUNA")},
            {"segment": "financial", "share_of_deposits": 0.079, "calm_daily_hazard": 0.001, "stress_daily_hazard": 0.5, "p_enter_stress": 0.01, "p_exit_stress": 0.05,
             "basis": txt("Fixture: the foreign-office share", "Ejemplo: la proporcion de oficinas extranjeras")}]},
            "truth": [{"segment": "non-operational-corporate", "horizon_days": 2, "true_outflow_rate": 0.0083}, {"segment": "non-operational-corporate", "horizon_days": 5, "true_outflow_rate": 0.0197},
                      {"segment": "retail-insured", "horizon_days": 2, "true_outflow_rate": 0.0048}],
            "verification": {"n_draws": 1000, "max_abs_error": 0.0004, "mc_standard_error": 0.0003, "within_error": True}},
        "sources": [
            {"source_id": sid, "publisher": pub, "licence_class": cls, "licence_basis": basis_,
             "statement": txt(st, st)} for sid, pub, cls, basis_, st in (
                ("fdic-bankfind", "FDIC", "mirror-allowed", "unverified", "Presumed US government public data; the licence sentence is UNVERIFIED. A reading of the situation, not legal advice."),
                ("fed-h8", "Federal Reserve Board", "mirror-allowed", "notice-read", "Board public-domain statement. A reading of the notice, not legal advice."),
                ("fed-svb-review", "Federal Reserve Board", "mirror-allowed", "notice-read", "Board public-domain statement. A reading of the notice, not legal advice."),
                ("bcbs-d555-table-a1", "Bank for International Settlements", "mirror-allowed", "notice-read",
                 "Table A.1 enters as constants with the source stated, within the BIS limited-extract terms; the rest of d555 is derived-only. A reading of the notice, not legal advice."),
                ("ecb-list-2019", "European Central Bank", "mirror-allowed", "notice-read",
                 "Parameters used with the ECB cited, the text accurate and any modification stated. A reading of the notice, not legal advice."))],
    }
    return {"schema": "contraste.models/v1", "case_id": "C16", "fit_id": "fixture-liquidity", "model": [model_summary("liquidity-ladder", "behavioural-ladder", True)],
            "fit": fit, "provenance": provenance("synthetic-known-truth"), "lane": {"lane": "precompute", "reasons": ["fixture"]}}


def write(name: str, doc: dict) -> None:
    FIX.mkdir(parents=True, exist_ok=True)
    with (FIX / name).open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    for v in ("lcr-standard", "list-adverse", "list-extreme", "fast-run", "htm-losses"):
        write(f"variant-scenario-{v}-fixture.json", scenario_doc(v))
    write("variant-reverse-fixture.json", reverse_doc())
    write("models-fixture.json", models_doc())


if __name__ == "__main__":
    main()
