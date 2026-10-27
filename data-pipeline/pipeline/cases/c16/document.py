"""The scenario documents of C16: the assembly of one variant's ``outputs``, test rows, impact and findings at the valuation date.

The numbers come from ``variant`` (engine calls); this module orders them in the ``c16-outputs`` contract
(``docs/contracts/schemas/c16/variant-scenario.schema.json``): the balance sheet, the CBC, the contractual ladder, the daily path or
the LCR, the HTM block, the scoring, the sensitivities and the time block, and the ``riskvalidation`` test rows of the variant.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.liquidity import ladder, scenarios
from riskvalidation.validation import liquidity as val

from ...core.text import number
from ...io import treasury
from ...io.fdic import Report
from . import balance
from .assumptions import txt
from .variant import (BANK, UNITS, VARIANT_LABEL, Path, _impact_survival, _tr, cbc_block, htm_block, lcr_block, path_block, path_for, scoring_block,
                      survival_days)

DATA_FIELDS = ["ASSET", "CHBAL", "DEP", "DEPDOM", "DEPFOR", "DEPINS", "DEPLGAMT", "DEPSMAMT", "DEPUNA", "EQ", "FREPO", "FREPP", "LNLSNET",
               "OTHBFHLB", "SC", "SCAA", "SCAF", "SCASPNSUM", "SCDOMO", "SCFORD", "SCHA", "SCHF", "SCMTGBK", "SCMUNI", "SCPLEDGE", "SCUST"]
TIME_FIELDS = ["DEP", "DEPDOM", "DEPINS", "DEPUNA", "SCAA", "SCAF", "SCHA", "SCHF"]
TIME_DATES = ("2021-12-31", "2022-06-30")
FDIC_SOURCE = "https://api.fdic.gov/banks/financials (CERT 24735, REPDTE {date})"
H8_SERIES = {"large-domestic-deposits": ("h8-deposits-large-domestic", "Deposits, large domestically chartered banks", "Depósitos, bancos grandes domésticos"),
             "small-domestic-deposits": ("h8-deposits-small-domestic", "Deposits, small domestically chartered banks", "Depósitos, bancos pequeños domésticos")}


#: the back-test segments in words (a finding title never prints a slug): English, Spanish
SEGMENT_NAME = {"board-stated-share": ("board-stated share", "proporción declarada por la Junta"),
                "call-report-dep": ("call-report deposits", "depósitos del reporte")}


def _segment_name(segment: str | None) -> tuple[str, str]:
    """The words of a back-test segment in both languages; a segment without words keeps its id."""
    return SEGMENT_NAME.get(segment or "", (str(segment), str(segment)))


def basis_of(vid: str) -> str:
    return "fair-value" if vid == "htm-losses" else "amortised-cost"


def sensitivities(vid: str, report: Report, conv: dict, fit: scenarios.FastRun) -> dict[str, Any]:
    """The survival period against the uninsured share and the survival period and CBC against the HTM loss multiple, on the grids
    of the conventions (05 E.5 rung 4); null with its reason where the variant has no daily path."""
    if vid == "lcr-standard":
        why = txt("The LCR defines a 30-day aggregate ratio and no daily path, so there is no survival period to put against this grid.",
                  "El LCR define una razón agregada a 30 días sin trayectoria diaria: no hay periodo de supervivencia para esta grilla.")
        return {"uninsured_share": None, "uninsured_share_reason": why, "htm_loss": None, "htm_loss_reason": why}
    shares = conv["uninsured_share_grid"]["values"]
    mults = conv["htm_loss_multiple_grid"]["values"]
    losses = scenarios.htm_loss_grid(report.get("SCHF") - report.get("SCHA"), mults)
    return {
        "uninsured_share": [{"share": s, "survival": path_for(vid, report, conv, fit, basis=basis_of(vid), uninsured_share=s).survival} for s in shares],
        "uninsured_share_reason": None,
        "htm_loss": [{"multiple": m, "unrealised_loss": loss, "cbc": cbc_block(report, conv, "fair-value", m)["total_liquidity_value"],
                      "survival": path_for(vid, report, conv, fit, basis="fair-value", htm_multiple=m).survival} for m, loss in zip(mults, losses)],
        "htm_loss_reason": None}


def time_point(vid: str, rep: Report, conv: dict, fit: scenarios.FastRun) -> dict[str, Any]:
    """One earlier date of the time block, read from the reports up to that date: the deposits, the HTM loss, the CBC on both bases,
    the survival period (or the LCR) as the HTM losses grew."""
    surv = None if vid == "lcr-standard" else path_for(vid, rep, conv, fit, basis=basis_of(vid)).survival
    return {"as_of": rep.report_date, "report_date": rep.report_date, "deposits": balance.deposits_block(rep),
            "htm_unrealised_loss": rep.get("SCHF") - rep.get("SCHA"),
            "cbc_amortised_basis": cbc_block(rep, conv, "amortised-cost")["total_liquidity_value"],
            "cbc_fair_value_basis": cbc_block(rep, conv, "fair-value")["total_liquidity_value"],
            "survival": surv, "lcr_ratio": lcr_block(rep, conv)["ratio"] if vid == "lcr-standard" else None}


def model_summary(ev: str, rung: str = "behavioural-ladder", details: bool = False) -> dict[str, Any]:
    m = {"id": "liquidity-ladder", "family": "liquidity", "rung": rung,
         "title": txt("Liquidity ladder: run-off curves, counterbalancing capacity, net liquidity position and survival period",
                      "Escalera de liquidez: curvas de salida, capacidad de contrapeso, posición neta de liquidez y periodo de supervivencia"),
         "short_title": txt("Liquidity ladder", "Escalera de liquidez"), "engine": "riskvalidation", "engine_version": ev, "licence": "MIT",
         "calibration": None, "parameters": {}, "checkpoint_sha256": None}
    if details:
        m["details"] = {}
    return m


#: the tests other than the run-off back-tests that raise a finding when red or amber, in words (frontend/src/workbench/names/tests.ts)
OTHER_FINDING_NAMES: dict[str, tuple[str, str]] = {
    "liq.cliff_effect_diagnostic": ("The cliff-effect diagnostic", "El diagnóstico del efecto acantilado"),
    "liq.htm_revaluation_vs_reported": ("The HTM revaluation against the reported fair value", "La revaluación HTM contra el valor razonable reportado"),
    "liq.htm_loss_effect": ("The effect of the HTM unrealised loss on the CBC", "El efecto de la pérdida no realizada HTM en el CBC"),
    "liq.nlp_identity": ("The NLP identity on the ladder", "La identidad de la NLP en la escalera"),
    "liq.list_compounding_golden": ("The LiST compounding example", "El ejemplo de composición de LiST"),
    "liq.cbc_haircut_rules": ("The CBC haircut rules", "Las reglas de recorte del CBC"),
    "liq.uninsured_share_sensitivity": ("The sensitivity to the uninsured share", "La sensibilidad a la parte no asegurada"),
    "liq.survival_monotone_in_severity": ("The survival period against the severity", "El periodo de supervivencia frente a la severidad"),
    "liq.runoff_vs_generator_truth": ("The run-off against the generator truth", "La salida de depósitos contra la verdad del generador"),
}


def finding(fid: str, sev: str, tests: list[str], en: str, es: str) -> dict[str, Any]:
    return {"id": fid, "severity": sev, "status": "open", "evidence": tests, "title": txt(en, es)}


@dataclass
class Shared:
    """What a scenario document takes from outside the call report: the conventions, the fast-run parameter set, the Treasury curves
    up to the date, the H.8 record, the generator's verification rows, the engine version."""
    conv: dict[str, Any]
    fit: scenarios.FastRun
    curves: dict[str, treasury.ParCurve]
    h8: dict[str, list[tuple[str, float]]] | None
    h8_reason: str | None
    generator: dict[str, Any] | None
    engine_version: str
    survivals: dict[str, dict[str, Any]] | None = None


def aggregate_record(sh: Shared) -> tuple[dict | None, dict | None]:
    if sh.h8 is None:
        return None, txt(f"The H.8 release tables are not read: {sh.h8_reason or 'not available'}. The aggregate record is omitted with this statement.",
                         "Las tablas H.8 no se leen: el registro agregado se omite con esta declaración.")
    series = [{"series_id": sid, "label": txt(en, es), "unit": "USD billions, seasonally adjusted, weekly (Wednesday level)",
               "points": [{"date": d, "value": v} for d, v in sh.h8[key]]} for key, (sid, en, es) in H8_SERIES.items()]
    return {"source": "Federal Reserve H.8 release tables, Tables 6 and 8 (https://www.federalreserve.gov/releases/h8/): weekly levels of the large and the "
                      "small domestically chartered commercial banks, the latest release vintage of each week; the observed record of the weeks "
                      "around the run, never an input of a valuation", "series": series}, None


def contractual_block(report: Report, conv: dict) -> dict[str, Any]:
    edges = conv["contractual_bucket_edges_days"]["values"]
    inn, out = balance.contractual_flows(report, edges)
    gap, cum = ladder.contractual_gaps(np.array(inn), np.array(out))
    uppers, lowers = [*edges, None], [0, *edges]
    return {"buckets": [{"from_day": lo, "to_day": hi, "inflows": float(i), "outflows": float(o), "gap": float(g), "cumulative_gap": float(c)}
                        for lo, hi, i, o, g, c in zip(lowers, uppers, inn, out, gap, cum)],
            "reference": "dossier 05 E.5 rung 1; SRP50 contractual maturity mismatch (01 G.3 lines 642-643); the bands of the call report spread "
                         "uniformly over the days they cover (items without a contractual maturity are left out)"}


def scenario_document(vid: str, report: Report, earlier: list[Report], sh: Shared) -> dict[str, Any]:
    """``outputs``, ``tests``, ``impact`` and ``findings`` of one scenario variant at the report date."""
    conv, fit = sh.conv, sh.fit
    vd = report.report_date
    row = next(r for r in conv["variant_scenarios"]["rows"] if r["variant"] == vid)
    h = row["horizon_days"]
    sheet = balance.balance_sheet(report)
    deposits = sheet["deposits"]
    segs = balance.deposit_segments(report)
    path = lcr = htm = None
    p: Path | None = None
    if vid == "lcr-standard":
        lcr = lcr_block(report, conv)
    else:
        p = path_for(vid, report, conv, fit, basis=basis_of(vid))
        path = path_block(p, conv, sheet["total_assets"])
    if vid == "htm-losses":
        htm = htm_block(report, conv, sh.curves, vd)
    scoring, adequacy = scoring_block(vid, conv, deposits, segs, p.ladder if p else None, lcr)
    agg, agg_reason = aggregate_record(sh)
    data = {"call_reports": [{"report_date": vd, "source": FDIC_SOURCE.format(date=vd), "fields": DATA_FIELDS},
                             *({"report_date": r.report_date, "source": FDIC_SOURCE.format(date=r.report_date), "fields": TIME_FIELDS} for r in earlier)],
            "data_cutoff": vd, "read_up_to_valuation_date": True,
            "rule": txt("No call report dated after the valuation date is read.", "No se lee ningún reporte de llamada posterior a la fecha de valoración.")}
    reasons = {"path": txt("The LCR is a 30-day aggregate ratio: its formula gives no daily path, so no ladder, survival period or cliff is stated.",
                           "El LCR es una razón agregada a 30 días: su fórmula no da trayectoria diaria, así que no se declara escalera, "
                           "periodo de supervivencia ni acantilado."),
               "lcr": txt("This variant runs the run-off ladder, not the LCR formula.", "Esta variante corre la escalera de salidas, no la fórmula del LCR."),
               "htm": txt("Only the HTM variant takes the held-to-maturity book at fair value.", "Solo la variante HTM toma el libro mantenido hasta el vencimiento a valor razonable.")}
    o = {"kind": "scenario", "valuation_date": vd, "currency": "USD", "units": UNITS, "bank": BANK,
         "variant": {"id": vid, "label": txt(*VARIANT_LABEL[vid][:2]), "description": txt(*VARIANT_LABEL[vid][2:]), "scenario_family": row["scenario_family"],
                     "phase": row["phase"], "parameter_set": row["parameter_set"], "horizon_days": h, "axis": row["axis"]},
         "conventions": conv, "data": data, "aggregate_record": agg, "aggregate_record_reason": agg_reason, "balance_sheet": sheet,
         "cbc": cbc_block(report, conv, basis_of(vid)), "contractual_ladder": contractual_block(report, conv),
         "path": path, "path_reason": reasons["path"] if path is None else None,
         "lcr": lcr, "lcr_reason": reasons["lcr"] if lcr is None else None, "htm": htm, "htm_reason": reasons["htm"] if htm is None else None,
         "scoring": scoring, "sensitivities": sensitivities(vid, report, conv, fit),
         "time_block": [time_point(vid, r, conv, fit) for r in earlier]}
    tests = [_tr(val.list_compounding_golden(tol=conv["list_compounding_tolerance"]["value"])), _tr(val.cbc_haircut_rules())]
    tests += [_tr(t, segment=t.segment) for t in adequacy]
    findings = []
    for t in adequacy:
        if t.light.value != "green":
            findings.append(finding(f"F-liq-adequacy-{t.segment}", "S2" if t.light.value == "red" else "S3", ["liq.runoff_adequacy_back_test"],
                                    f"The modelled outflow is {number(t.statistic, 3, lang='en')} of the realised outflow ({_segment_name(t.segment)[0]})",
                                    f"La salida modelada es {number(t.statistic, 3, lang='es')} de la realizada ({_segment_name(t.segment)[1]})"))
    if p is not None:
        tests.append(_tr(val.nlp_identity(p.cbc_total, p.total_out, p.total_in, p.nlp, conv["nlp_identity_tolerance"]["value"])))
        tests.append(_tr(val.cliff_effect_diagnostic(p.nlp, sheet["total_assets"], conv["cliff_days"]["near"], conv["cliff_days"]["far"],
                                                     conv["cliff_amber_threshold"]["value"], conv["cliff_red_threshold"]["value"])))
    if vid == "list-adverse":
        sens = o["sensitivities"]["uninsured_share"]
        tests.append(_tr(val.uninsured_share_sensitivity([x["share"] for x in sens], [survival_days(x["survival"]) for x in sens],
                                                         conv["monotonicity_tolerance_days"]["value"])))
    if vid == "list-extreme" and sh.survivals is not None:
        tests.append(_tr(val.survival_monotone_in_severity([survival_days(sh.survivals["list-adverse"]), survival_days(p.survival)],
                                                           conv["monotonicity_tolerance_days"]["value"])))
    if vid == "fast-run" and sh.generator is not None:
        g = sh.generator
        tests.append(_tr(val.runoff_vs_generator_truth(g["estimated"], g["truth"], g["se"], conv["generator_truth_se_green"]["value"],
                                                       conv["generator_truth_se_red"]["value"])))
    if htm is not None:
        base = path_for(vid, report, conv, fit, basis="amortised-cost").survival
        tests.append(_tr(val.htm_loss_effect(htm["cbc_without_loss"], htm["cbc_with_loss"], survival_days(base), survival_days(p.survival))))
        rv = htm["revaluation"]
        tests.append(_tr(val.htm_revaluation_vs_reported(rv["model_fair_value"], htm["reported"]["htm_fair_value"], htm["reported"]["htm_amortised_cost"],
                                                         conv["htm_revaluation_green"]["value"], conv["htm_revaluation_amber"]["value"])))
    # every other red or amber test raises a finding too (R2b c17 M2: the red HTM revaluation and the amber cliffs raised none)
    for t in tests:
        tid = t["test_id"]
        if tid in OTHER_FINDING_NAMES and t["light"] in ("red", "amber") and not any(f["evidence"] == [tid] for f in findings):
            name_en, name_es = OTHER_FINDING_NAMES[tid]
            red = t["light"] == "red"
            findings.append(finding(f"F-liq-{tid.split('.')[-1].replace('_', '-')}", "S2" if red else "S3", [tid],
                                    f"{name_en} is {'red' if red else 'amber'} in this variant",
                                    f"{name_es} está en {'rojo' if red else 'ámbar'} en esta variante"))
    impact = {"lcr": {"value": lcr["ratio"], "unit": "ratio", "label": txt("LCR, a Basel formula on call-report aggregates", "LCR, una fórmula de Basilea sobre agregados del reporte de llamada")}
              if lcr else {"value": None, "unit": "ratio", "label": txt("No LCR in this variant", "Sin LCR en esta variante")},
              "survival_days": _impact_survival(p.survival if p else None, h)}
    return {"outputs": o, "tests": tests, "impact": impact, "findings": findings, "path": p}
