"""One scenario variant of C16 at the valuation date, through ``riskvalidation`` (engine contract ``engine-liquidity-api`` 2.0.0).

``scenario_document`` builds the ``outputs`` block, the test rows, the impact and the findings of one of the five scenario variants
(LCR standard run-off, LiST Adverse, LiST Extreme, the 2023 fast run, HTM losses in the CBC) for a call report read up to its date.
Every ratio, run-off, haircut, CBC value, net liquidity position, survival period, cliff and score is an engine call; this module
assigns items to categories, spreads reported bands over days and writes what the engine returned (ADR-0069).
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.irrbb import curves as ecurves
from riskvalidation.irrbb import eve_nii
from riskvalidation.liquidity import cbc as ecbc
from riskvalidation.liquidity import ladder, runoff, scenarios
from riskvalidation.regulatory import lcr_nsfr
from riskvalidation.validation import liquidity as val

from ...io import treasury
from ...io.fdic import Report
from . import anchors, balance
from .assumptions import FIRST_DAY, HORIZON, relevant_days, txt  # noqa: F401  (FIRST_DAY documents the calendar)

MODEL_ID = "liquidity-ladder"
OTHER_FLOW_DAYS = 250      # relevant days in a year, over which the advances of one year or less mature uniformly (a convention)
INFLOW_CAP = 0.75
VARIANT_LABEL = {
    "lcr-standard": ("LCR standard run-off", "LCR con salidas estándar", "The Basel LCR of the call-report balance sheet over the 30-day combined stress.",
                     "El LCR de Basilea del balance del reporte de llamada bajo el estrés combinado a 30 días."),
    "list-adverse": ("LiST adverse", "LiST adverso", "ECB LiST 2019 Adverse daily compounding over the six-month horizon.",
                     "Capitalización diaria LiST 2019 Adverso del BCE a seis meses."),
    "list-extreme": ("LiST extreme", "LiST extremo", "ECB LiST 2019 Extreme daily compounding over the six-month horizon.",
                     "Capitalización diaria LiST 2019 Extremo del BCE a seis meses."),
    "fast-run": ("2023 fast run", "Corrida rápida 2023", "Daily compounding calibrated on the pre-2023 Table A.1 rows, scored on 2023.",
                 "Capitalización diaria calibrada con las filas de la Tabla A.1 anteriores a 2023, evaluada en 2023."),
    "htm-losses": ("HTM losses in CBC", "Pérdidas HTM en el CBC", "LiST Adverse with the held-to-maturity book at fair value in the CBC.",
                   "LiST Adverso con el libro mantenido al vencimiento a valor razonable en el CBC."),
}
BANK = {"name": "Silicon Valley Bank (CERT 24735), failed 2023-03-10", "cert": 24735, "aggregates": "real", "behaviour": "synthetic",
        "deposits": "synthetic",
        "notice": txt("Real FDIC call-report aggregates used as public aggregates only, with synthetic behaviour and synthetic deposits: "
                      "the case does not represent the bank and certifies no model.",
                      "Agregados reales del reporte de llamada FDIC usados solo como agregados públicos, con comportamiento y depósitos "
                      "sintéticos: el caso no representa al banco ni certifica ningún modelo.")}
UNITS = {"money_scale": "thousands", "rate": "decimal-per-day", "horizon": "days", "dates": "ISO-8601"}
LCR_STATEMENT = txt("A Basel LCR formula applied to FDIC call-report aggregates with stated assumptions and synthetic deposit behaviour: "
                    "not the bank's reported or regulatory LCR.",
                    "Una fórmula LCR de Basilea aplicada a agregados del reporte de llamada FDIC con supuestos declarados y "
                    "comportamiento sintético de depósitos: no es el LCR informado ni regulatorio del banco.")

#: the realised run the scoring reads: the run at the bank, never an apposition that makes the run the bank (R4 c20 n5)
EVENT_LABEL = txt("The deposit run of 9 and 10 March 2023 at the bank that failed on 2023-03-10",
                  "La corrida de depósitos del 9 y 10 de marzo de 2023 en el banco que quebró el 2023-03-10")


# ------------------------------------------------------------------------------------------------------ small blocks


def survival_block(nlp: np.ndarray) -> dict[str, Any]:
    """The survival period of an NLP path through the engine: a day, or "survives the horizon" with the horizon and no day."""
    sv = ladder.survival_period(np.asarray(nlp, dtype=float))
    return {"kind": "survives-horizon", "day": None, "horizon_days": sv.horizon} if sv.survives else \
        {"kind": "day", "day": int(sv.day), "horizon_days": sv.horizon}


def survival_days(s: dict[str, Any]) -> int | None:
    """The engine-test encoding of a survival block: the day, or None for "survives the horizon"."""
    return None if s["kind"] == "survives-horizon" else int(s["day"])


def hqla_block(l1: float, l2a: float, l2b: float, al1: float | None = None, al2a: float | None = None, al2b: float | None = None) -> dict[str, Any]:
    """The HQLA block through the engine. An empty stock has null Level 2 and Level 2B shares with their reason (decision X3):
    the engine returns NaN there, which is never written as a zero."""
    h = lcr_nsfr.hqla_stock(l1, l2a, l2b, al1, al2a, al2b)
    empty = not np.isfinite(h.l2_share) or not np.isfinite(h.l2b_share)
    return {"l1": h.l1, "l2a": h.l2a, "l2b": h.l2b, "adjusted_l1": l1 if al1 is None else al1, "adjusted_l2a": l2a if al2a is None else al2a,
            "adjusted_l2b": l2b if al2b is None else al2b, "adj_15": h.adj_15, "adj_40": h.adj_40, "hqla": h.hqla,
            "l2_share": None if empty else h.l2_share, "l2b_share": None if empty else h.l2b_share,
            "shares_reason": txt("The HQLA stock is empty: the Level 2 and Level 2B shares are undefined, not zero.",
                                 "El stock HQLA está vacío: las proporciones de nivel 2 y 2B no están definidas, no son cero.") if empty else None,
            "caps": {"l2_cap": 0.4, "l2b_cap": 0.15}}


def _tr(t: Any, segment: str | None = None, thresholds: dict | None = None) -> dict[str, Any]:
    """A ``TestResult`` of the engine as a document row: the model id of the ladder, the segment when the row has one."""
    t = dataclasses.replace(t, model_id=MODEL_ID, segment=segment if segment is not None else t.segment)
    return _plain(t.to_dict())


def _plain(x: Any) -> Any:
    if isinstance(x, dict):
        return {k: _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if isinstance(x, np.generic):
        return x.item()
    return x


# ------------------------------------------------------------------------------------------------------ the scenario and the CBC


def _list_segments(report: Report, uninsured_share: float | None) -> list[dict[str, Any]]:
    segs = balance.deposit_segments(report)
    if uninsured_share is not None:
        (ins, unin), = scenarios.uninsured_share_grid(segs[0]["opening"], segs[1]["opening"], [uninsured_share])
        segs[0]["opening"], segs[1]["opening"] = ins, unin
    return segs


def make_scenario(vid: str, segs: list[dict[str, Any]], conv: dict, fit: scenarios.FastRun) -> scenarios.Scenario:
    """The scenario of a path variant, composed by the engine: LiST rates by class; for the fast run the calibrated rate on the
    uninsured segment and the LiST Adverse rates on the others (a ``FastRun`` holds the concentrated uninsured class only)."""
    row = next(r for r in conv["variant_scenarios"]["rows"] if r["variant"] == vid)
    fam, phase, h = row["scenario_family"], row["phase"], row["horizon_days"]
    lst = scenarios.list_scenario("extreme" if vid == "list-extreme" else "adverse")
    if vid != "fast-run":
        return scenarios.compose_scenario(fam, phase, lst, {s["segment"]: (s["list_class"], s["opening"]) for s in segs}, h)
    rest = scenarios.compose_scenario(fam, phase, lst, {s["segment"]: (s["list_class"], s["opening"]) for s in segs if s["segment"] != "non-operational-corporate"}, h)
    corp = next(s for s in segs if s["segment"] == "non-operational-corporate")
    fast = scenarios.compose_scenario(fam, phase, fit, {corp["segment"]: ("concentrated-uninsured", corp["opening"])}, h)
    by = {s.segment_id: s for s in (*rest.segments, *fast.segments)}
    return scenarios.Scenario(fam, phase, h, tuple(by[s["segment"]] for s in segs))


def _cbc_classes(report: Report, conv: dict, basis: str, htm_multiple: float | None = None, par: bool = False) -> list[dict[str, Any]]:
    """The CBC classes at the report date: the securities by type at the carrying values (or, on the fair-value basis, at the
    whole-book loss factor), the pledged part encumbered, each haircut and its rule label from ``cbc.haircut_rule``."""
    rows = {r["class_id"]: r for r in conv["cbc_securities_mapping"]["rows"]}
    if htm_multiple is None:
        loss_factor = balance.fair_value_factor(report)
    else:
        book = report.get("SCHA") + report.get("SCAF")
        loss_factor = 1.0 + scenarios.htm_loss_grid(report.get("SCHF") - report.get("SCHA"), [htm_multiple])[0] / book
    at_fair = basis == "fair-value" or htm_multiple is not None
    out = []
    for c in balance.securities_classes(report):
        sec = c.class_id in balance.SECURITY_TYPES
        fv = c.carrying * loss_factor if (sec and at_fair) else None
        used = fv if fv is not None else c.carrying
        row = rows[c.class_id]
        if row["rule"] == "nominal-value":
            hc, rule = ecbc.haircut_rule("cash")
        elif row["rule"] == "central-bank-framework":
            hc, rule = ecbc.haircut_rule("non-equity", central_bank_eligible=True, central_bank_haircut=1.0 - row["margin"])
        else:
            hc, rule = ecbc.haircut_rule("non-equity", central_bank_eligible=True)
        if par and c.class_id in ("treasury", "mortgage-backed", "other-agency"):
            hc = 0.0
        out.append({"class_id": c.class_id, "label": c.label, "source_fields": list(c.source_fields), "carrying_value": c.carrying, "fair_value": fv,
                    "value_used": used, "encumbered": c.encumbered, "haircut": {"value": hc, "rule": rule},
                    "liquidity_value": float(ecbc.liquidity_value(used, hc, c.encumbered))})
    return out


def cbc_block(report: Report, conv: dict, basis: str, htm_multiple: float | None = None) -> dict[str, Any]:
    classes = _cbc_classes(report, conv, basis, htm_multiple)
    enc = sum(c["encumbered"] for c in classes)
    return {
        "as_of": report.report_date, "htm_valuation_basis": basis,
        "haircut_framework": {
            "label": txt("Federal Reserve discount window margins in force on 2023-03-10", "Márgenes de la ventana de descuento de la Reserva Federal vigentes el 2023-03-10"),
            "central_bank": "Federal Reserve discount window", "effective_from": "2022-03-14", "effective_to": "2023-03-12",
            "source": "https://www.frbdiscountwindow.org/generalpages/historical_margins/2022/03142022_03122023_securities_table"},
        "classes": classes,
        "pledged": {"field": "SCPLEDGE", "amount": enc, "share_of_securities": report.get("SCPLEDGE") / report.get("SC")},
        "total_liquidity_value": sum(c["liquidity_value"] for c in classes)}


# ------------------------------------------------------------------------------------------------------ the ladder


@dataclass
class Path:
    scn: scenarios.Scenario
    ladder: dict[str, Any]
    nlp: np.ndarray
    survival: dict[str, Any]
    cbc: dict[str, Any]
    cbc_total: np.ndarray
    total_out: np.ndarray
    total_in: np.ndarray


def _segment_docs(vid: str, segs: list[dict[str, Any]], scn: scenarios.Scenario, fit: scenarios.FastRun, conv: dict) -> list[dict[str, Any]]:
    sev = "Extreme" if vid == "list-extreme" else "Adverse"
    out_arr = scn.outflows()
    rates = scn.rates()
    docs = []
    for k, (s, seg) in enumerate(zip(segs, scn.segments)):
        cum = runoff.cumulative_outflow_path(rates[k])
        full = bool(np.all(rates[k] == 1.0))
        calibrated = vid == "fast-run" and s["segment"] == "non-operational-corporate"
        q = float(rates[k][0])
        if full:
            par = {"name": "first_day_outflow_share", "value": q, "unit": "share", "source_kind": "transcribed-list-2019",
                   "source": "ECB LiST 2019 methodological note para 111: sight deposits of financial customers flow out in full on the first "
                             "relevant day (foreign-office deposits mapped here, an assumption)"}
        elif calibrated:
            par = {"name": "daily_rate", "value": q, "unit": "decimal-per-day", "source_kind": "calibrated-pre-2023",
                   "source": "calibrated on the pre-2023 Table A.1 rows by the calibration rule (c16-models)"}
        else:
            what = "other retail sight deposits" if s["list_class"] == "other-retail" else "non-operational sight deposits of non-financial corporates"
            par = {"name": "daily_rate", "value": q, "unit": "decimal-per-day", "source_kind": "transcribed-list-2019",
                   "source": f"ECB LiST 2019 methodological note Table 3.3, {what}, {sev}"}
        docs.append({"segment": s["segment"], "list_class": s["list_class"], "mechanism": "full-runoff" if full else "open-maturity-compounding",
                     "opening_balance": seg.opening, "parameters": [par], "daily_rates": None if full else [float(x) for x in rates[k]],
                     "cumulative_outflow_share": [float(x) for x in cum], "outflows": [float(x) for x in out_arr[k]]})
    return docs


def _other_flows(report: Report, h: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The flows that do not run off by segment: borrowings that mature (LiST rolls secured funding off at 100 percent when it
    matures, Table 3.2; the maturity spread is synthetic) and the reverse repos that return (LiST secured lending, 100 percent)."""
    frepp, fhlb = balance.opt(report, "FREPP") or 0.0, balance.opt(report, "OTHBFH1L") or 0.0
    other = balance.opt(report, "OTBOT1L") or 0.0
    out = [
        {"component_id": "repo-borrowings-maturing", "kind": "secured-funding-maturity", "source_kind": "synthetic-stated",
         "source": "ECB LiST 2019 Table 3.2: secured funding rolls off at 100 percent when it matures (addendum L1.1); FREPP assumed overnight, so it "
                   "matures on day 1 (synthetic behaviour)", "amounts": [frepp] + [0.0] * (h - 1)},
        {"component_id": "fhlb-advances-maturing", "kind": "secured-funding-maturity", "source_kind": "synthetic-stated",
         "source": "ECB LiST 2019 Table 3.2: secured funding rolls off at 100 percent when it matures; the FHLB advances of one year or less (OTHBFH1L) "
                   f"are spread uniformly over {OTHER_FLOW_DAYS} relevant days (synthetic behaviour)", "amounts": [fhlb / OTHER_FLOW_DAYS] * h},
        {"component_id": "other-borrowings-maturing", "kind": "other-contractual-outflow", "source_kind": "synthetic-stated",
         "source": "Other borrowings of one year or less (OTBOT1L) mature at 100 percent, spread uniformly over "
                   f"{OTHER_FLOW_DAYS} relevant days (synthetic behaviour)", "amounts": [other / OTHER_FLOW_DAYS] * h}]
    frepo = balance.opt(report, "FREPO") or 0.0
    inn = [{"component_id": "reverse-repo-maturing", "kind": "inflow-secured-lending", "source_kind": "transcribed-list-2019",
            "source": "ECB LiST 2019 methodological note Table 3.2: maturing secured lending and open reverse repos flow in at 100 percent (addendum L1.2 and "
                      "L1.3, paras 114 and 115); FREPO assumed overnight, so it returns on day 1 (synthetic behaviour)", "amounts": [frepo] + [0.0] * (h - 1)}]
    return out, inn


def path_for(vid: str, report: Report, conv: dict, fit: scenarios.FastRun, *, basis: str, uninsured_share: float | None = None,
             htm_multiple: float | None = None) -> Path:
    """The daily ladder of a path variant at the report date: every number an engine call."""
    segs = _list_segments(report, uninsured_share)
    scn = make_scenario(vid, segs, conv, fit)
    h = scn.horizon
    cbc = cbc_block(report, conv, basis, htm_multiple)
    classes = {c["class_id"]: (c["value_used"], c["encumbered"], c["haircut"]["value"]) for c in cbc["classes"]}
    stack = ecbc.cbc_stack(classes, [(p["day"], p["cumulative_share"]) for p in conv["monetisation_schedule"]["points"]], h)
    seg_docs = _segment_docs(vid, segs, scn, fit, conv)
    other, inn = _other_flows(report, h)
    seg_out = scn.outflows().sum(axis=0)
    total_out = seg_out + sum((np.array(f["amounts"]) for f in other), np.zeros(h))
    total_in = sum((np.array(f["amounts"]) for f in inn), np.zeros(h))
    cbc_total = sum((stack[k] for k in stack), np.zeros(h))
    nlp = ladder.net_liquidity_position(cbc_total, total_out, total_in)
    cum = np.cumsum(total_out - total_in)
    lad = {"axis": "relevant-days", "day_index": list(range(1, h + 1)), "dates": relevant_days(h), "segments": seg_docs, "other_outflows": other,
           "inflows": inn, "total_outflows": [float(x) for x in total_out], "total_inflows": [float(x) for x in total_in],
           "cbc_stack": [{"class_id": c["class_id"], "liquidity_value": [float(x) for x in stack[c["class_id"]]]} for c in cbc["classes"]],
           "cbc_total": [float(x) for x in cbc_total], "cumulative_net_outflow": [float(x) for x in cum], "nlp": [float(x) for x in nlp]}
    return Path(scn, lad, nlp, survival_block(nlp), cbc, cbc_total, total_out, total_in)


def path_block(p: Path, conv: dict, total_assets: float) -> dict[str, Any]:
    low, day = ladder.minimum_nlp(p.nlp)
    h = len(p.nlp)
    near, far = conv["cliff_days"]["near"], conv["cliff_days"]["far"]
    blk = {"ladder": p.ladder, "survival": p.survival, "minimum_nlp": {"value": float(low), "day": int(day)}}
    if h >= far:
        blk["cliff"] = {"near_day": near, "far_day": far, "nlp_near": float(p.nlp[near - 1]), "nlp_far": float(p.nlp[far - 1]),
                        "total_assets": total_assets, "value": float(ladder.cliff_effect(p.nlp, total_assets, near, far))}
        blk["cliff_reason"] = None
    else:
        blk["cliff"] = None
        blk["cliff_reason"] = txt(f"The horizon of {h} days is shorter than the far day {far} of the cliff diagnostic.",
                                  f"El horizonte de {h} días es menor que el día {far} del diagnóstico del acantilado.")
    return blk


# ------------------------------------------------------------------------------------------------------ the LCR


def lcr_block(report: Report, conv: dict) -> dict[str, Any]:
    """The Basel LCR over the call-report aggregates under the named mapping, with the sensitivity band, through the engine."""
    inp = balance.lcr_balances(report, balance.fair_value_factor(report))
    # the securities enter at fair value less the encumbered part, after the Basel haircut of their level
    after = {lvl: float(ecbc.liquidity_value(v, lcr_nsfr.HQLA_HAIRCUTS[lvl])) for lvl, v in inp["levels"].items() if lvl in lcr_nsfr.HQLA_HAIRCUTS}
    hq = hqla_block(after["level_1"], after["level_2a"], 0.0)   # no asset of the mapping is Level 2B
    out = lcr_nsfr.lcr_outflows(inp["outflows"])
    inn = lcr_nsfr.lcr_inflows(inp["inflows"])
    net = lcr_nsfr.net_cash_outflows(out.total, inn.total, INFLOW_CAP)
    ratio = lcr_nsfr.lcr_ratio(hq["hqla"], net.net)

    def rows(res: Any) -> list[dict[str, Any]]:
        return [{"category": r.key, "balance": r.balance, "rate": r.rate, "amount": r.amount, "reference": r.reference} for r in res.rows]

    central_cat = next(r for r in conv["deposit_category_mapping"]["rows"] if r["basis"] == "uninsured")["lcr_category"]

    def figures(mapping_id: str, category: str) -> dict[str, Any]:
        bal = dict(inp["outflows"])
        bal["non_financial_corporate"] -= inp["uninsured"]
        bal[category] = bal.get(category, 0.0) + inp["uninsured"]
        o = lcr_nsfr.lcr_outflows(bal)
        unin = inp["uninsured"] * lcr_nsfr.LCR_OUTFLOW_RATES[category]
        n = lcr_nsfr.net_cash_outflows(o.total, inn.total, INFLOW_CAP)
        return {"mapping_id": mapping_id, "lcr_category": category, "uninsured_outflow": unin, "total_outflows": o.total,
                "inflows_counted": n.inflows_counted, "net_outflows": n.net, "ratio": lcr_nsfr.lcr_ratio(hq["hqla"], n.net)}

    band = [figures("central", central_cat), figures("band-operational", "operational"), figures("band-other-legal-entity", "other_legal_entity")]
    return {"label": "basel-formula-on-call-report-aggregates", "reported_or_regulatory": False, "statement": LCR_STATEMENT, "hqla": hq,
            "outflows": rows(out), "total_outflows": out.total, "inflows": rows(inn), "total_inflows": inn.total, "inflow_cap": INFLOW_CAP,
            "inflows_counted": net.inflows_counted, "net_outflows": net.net, "ratio": ratio, "mapping_sensitivity": band,
            "below_100_note": txt("A ratio below 100 percent under stress is not a breach: the institution is expected to monitor its decline "
                                  "(ECB ILAAP guide, dossier 01 J.3).",
                                  "Una razón bajo 100 por ciento bajo estrés no es un incumplimiento: se espera que la entidad monitoree su "
                                  "caída (guía ILAAP del BCE, dossier 01 J.3).")}


# ------------------------------------------------------------------------------------------------------ HTM


def htm_revaluation(report: Report, curves: dict[str, treasury.ParCurve], valuation_date: str) -> dict[str, Any]:
    """The held-to-maturity book revalued from the maturity profile under the Treasury curve (decision Q11): each maturity band of the
    report is a par bond of the band midpoint at the par curve one year before the valuation date, priced on the curve of the date
    through ``riskvalidation.irrbb`` (bootstrapped zero curve, present value); the profile of the whole securities book is applied to
    the amortised cost of the held-to-maturity book. Not evaluated, with its reason, when a curve is absent."""
    reported, cost = report.get("SCHF"), report.get("SCHA")
    base = {"engine_ref": "engine-irrbb-api", "reported_fair_value": reported}
    ref_date = f"{int(valuation_date[:4]) - 1}{valuation_date[4:]}"
    known = sorted(d for d in curves if d <= valuation_date)
    older = sorted(d for d in curves if d <= ref_date)
    if not known or not older:
        reason = txt("No Treasury par curve is available on or before the valuation date or the date one year before it.",
                     "No hay curva de rendimientos del Tesoro a la fecha de valoración ni un año antes.")
        return {"status": "not_evaluated", "curve_source": "US Treasury par yield curve (not read)", "curve_date": None, "model_fair_value": None,
                "difference": None, "relative_difference": None, "reason": reason, **base}
    now, then = curves[known[-1]], curves[older[-1]]
    profile = balance.maturity_profile(report)
    total = sum(a for _, a in profile)

    def price(par: treasury.ParCurve, ref: treasury.ParCurve, t: float) -> float:
        cpn = float(np.interp(t, ref.tenors(), ref.yields()))
        times = np.array([*np.arange(0.5, t, 0.5), t]) if t > 0.5 else np.array([t])
        cf = np.full(times.size, cpn / 2.0 * (1.0 if t > 0.5 else 0.0) * 100.0)
        cf[-1] += 100.0
        zero = ecurves.bootstrap_zero_curve(par.tenors(), par.yields())
        return eve_nii.eve(cf, ecurves.zero_rates_at(par.tenors(), zero, times), times) / 100.0

    model = sum(a / total * price(now, then, t) for t, a in profile) * cost
    diff = model - reported
    rel = abs(diff) / abs(reported - cost) if reported != cost else None
    if rel is None:
        return {"status": "not_evaluated", "curve_source": f"US Treasury par yield curve of {known[-1]}", "curve_date": None, "model_fair_value": None,
                "difference": None, "relative_difference": None,
                "reason": txt("The reported unrealised loss is zero, so a relative difference is undefined.", "La pérdida no realizada informada es cero."), **base}
    return {"status": "evaluated", "curve_source": f"US Treasury par yield curve of {known[-1]} priced against the par curve of {older[-1]} "
            "(a par bond per maturity band of the securities book, the profile applied to the held-to-maturity amortised cost)",
            "curve_date": known[-1], "model_fair_value": model, "difference": diff, "relative_difference": rel, "reason": None, **base}


def htm_block(report: Report, conv: dict, curves: dict[str, treasury.ParCurve], valuation_date: str) -> dict[str, Any]:
    """The HTM block: the reported numbers, the CBC with and without the loss (``cbc.cbc_with_htm_loss`` per class), the Bank Term Funding
    Program par counterfactual and the revaluation row."""
    amortised = _cbc_classes(report, conv, "amortised-cost")
    fair = _cbc_classes(report, conv, "fair-value")
    par = _cbc_classes(report, conv, "amortised-cost", par=True)
    without = with_loss = 0.0
    for a, f in zip(amortised, fair):
        if a["class_id"] in balance.SECURITY_TYPES:
            res = ecbc.cbc_with_htm_loss(a["carrying_value"], f["fair_value"], a["encumbered"], a["haircut"]["value"])
            without += res.cbc_without_loss
            with_loss += res.cbc_with_loss
        else:
            without += a["liquidity_value"]
            with_loss += f["liquidity_value"]
    at_par = sum(c["liquidity_value"] for c in par)
    rep = {"htm_amortised_cost": report.get("SCHA"), "htm_fair_value": report.get("SCHF"), "htm_unrealised": report.get("SCHF") - report.get("SCHA"),
           "afs_amortised_cost": report.get("SCAA"), "afs_fair_value": report.get("SCAF"), "afs_unrealised": report.get("SCAF") - report.get("SCAA")}
    return {"reported": rep,
            "application": {"method": "whole-book", "statement": txt(
                "The held-to-maturity fair-value loss (SCHF minus SCHA) is applied to the securities book as a whole, pro rata by type: a stated "
                "assumption, never a reported by-type loss.",
                "La pérdida a valor razonable del libro mantenido hasta el vencimiento (SCHF menos SCHA) se aplica al libro de valores completo, "
                "a prorrata por tipo: un supuesto declarado, nunca una pérdida por tipo informada.")},
            "cbc_without_loss": without, "cbc_with_loss": with_loss, "cbc_removed": without - with_loss,
            "btfp_par": {"label": txt("Counterfactual: Bank Term Funding Program par valuation, announced 2023-03-12 after the run; par is proxied by the carrying value",
                                      "Contrafactual: valoración a la par del Bank Term Funding Program (BTFP), anunciada el 2023-03-12 tras la "
                                      "corrida; la par se aproxima por el valor contable"),
                         "announced": "2023-03-12", "cbc_at_par": at_par, "uplift": at_par - without},
            "revaluation": htm_revaluation(report, curves, valuation_date)}


# ------------------------------------------------------------------------------------------------------ scoring


def _anchor() -> dict[str, Any]:
    a = scenarios.anchor_from_observation(anchors.BOARD_SHARE, anchors.EVENT_HORIZON_DAYS)
    return {"label": txt("Labelled anchor, not a forecast: SVB's observed 85 percent in 2 days (Table A.1) and the daily rate it implies",
                         "Ancla rotulada, no un pronóstico: el 85 por ciento en 2 días observado en SVB y la tasa diaria implícita"),
            "source": anchors.ANCHOR_SOURCE, "outflow_share": a["outflow_share"], "days": a["days"], "implied_daily_rate": a["implied_daily_rate"],
            "forecast_claim": False}


def scoring_block(vid: str, conv: dict, deposits: dict[str, Any], segs: list[dict[str, Any]], lad: dict[str, Any] | None,
                  lcr: dict[str, Any] | None) -> tuple[dict[str, Any], list[Any]]:
    """The March 2023 scoring: the model's cumulative outflow against the realised outflow with both denominators, the anchor row and the
    Table A.1 rows by role. Every light is the engine's ``runoff_adequacy_back_test`` on the named parameters."""
    h = conv["variant_scenarios"]["rows"][[r["variant"] for r in conv["variant_scenarios"]["rows"]].index(vid)]["horizon_days"]
    base = sum(s["opening"] for s in segs)
    dep = deposits["dep"]
    ev = conv["event_horizon_days"]["value"]

    def modelled(days: int) -> float:
        return float(sum(sum(s["outflows"][:days]) for s in lad["segments"]))

    if lad is None:
        amount = sum(r["amount"] for r in lcr["outflows"][:3])
        at_model = {"horizon_days": h, "amount": amount, "share_of_model_base": amount / base}
        mo = {"at_event_horizon": None, "at_event_horizon_reason": txt(
            "The LCR defines one 30-day aggregate and no daily path, so no outflow exists at the 2-day event horizon: the comparison is at the model's own horizon.",
            "El LCR define un agregado a 30 días y ninguna trayectoria diaria, así que no existe salida en el horizonte del evento de 2 días: "
            "la comparación es en el horizonte propio del modelo."), "at_model_horizon": at_model}
        chosen_amount, chosen_share, compared = amount, at_model["share_of_model_base"], "model-horizon"
    else:
        a_ev, a_h = modelled(ev), modelled(h)
        at_event = {"horizon_days": ev, "amount": a_ev, "share_of_model_base": a_ev / base}
        mo = {"at_event_horizon": at_event, "at_event_horizon_reason": None,
              "at_model_horizon": {"horizon_days": h, "amount": a_h, "share_of_model_base": a_h / base}}
        chosen_amount, chosen_share, compared = a_ev, at_event["share_of_model_base"], "event-horizon"
    green, amber = conv["scoring_ratio_green"]["value"], conv["scoring_ratio_amber"]["value"]
    tests, den = [], []
    for did, label, d_amt, r_amt, r_share, m_share, src in (
            ("board-stated-share", txt("Board review: roughly 85 percent of the deposit base", "Revisión de la Junta: cerca de 85 por ciento de la base de depósitos"),
             None, None, anchors.BOARD_SHARE, chosen_share, anchors.REVIEW_SOURCE),
            ("call-report-dep", txt("Over 40 plus 100 billion USD against the call report's DEP", "Más de 40 más 100 mil millones de USD contra el DEP del reporte de llamada"),
             dep, anchors.EVENT_AMOUNT, anchors.EVENT_AMOUNT / dep, chosen_amount / dep,
             f"{anchors.REVIEW_SOURCE} (the amounts) and the FDIC call report of the valuation date (DEP)")):
        t = val.runoff_adequacy_back_test(m_share, r_share, green, amber, compared, did)
        tests.append(t)
        den.append({"id": did, "label": label, "denominator_amount": d_amt, "realised_amount": r_amt, "realised_share": r_share, "source": src,
                    "modelled_share": m_share, "compared_at": compared, "shortfall": float(t.metric), "ratio": float(t.statistic), "light": t.light.value})
    rows = []
    for r in runoff.TABLE_A1:
        role = ("calibration" if r.year < 2023 else "scored") if vid == "fast-run" else "reference"
        if lad is None or r.days > h:
            rows.append({"row_id": r.row_id, "bank": r.bank, "year": r.year, "horizon_days": r.days, "observed_share": r.outflow_share, "modelled_share": None,
                         "error": None, "role": role, "reason": (
                             txt("The variant has no daily path (the LCR is a 30-day aggregate), so no row is modelled.",
                                 "La variante no tiene trayectoria diaria (el LCR es un agregado a 30 días), así que ninguna fila se modela.")
                             if lad is None else
                             txt("The horizon of this row is beyond the model's ladder.", "El horizonte de esta fila excede la escalera del modelo."))})
        else:
            ms = modelled(r.days) / base
            rows.append({"row_id": r.row_id, "bank": r.bank, "year": r.year, "horizon_days": r.days, "observed_share": r.outflow_share, "modelled_share": ms,
                         "error": r.outflow_share - ms, "role": role, "reason": None})
    blk = {"event": {"label": EVENT_LABEL,
                     "event_date": anchors.EVENT_DATE, "horizon_days": ev, "source": anchors.REVIEW_SOURCE},
           "model_deposit_base": base, "modelled_outflow": mo, "denominators": den, "svb_anchor": _anchor(), "table_a1_scoring": rows}
    return blk, tests


def _impact_survival(sv: dict[str, Any] | None, h: int) -> dict[str, Any]:
    if sv is None:
        return {"value": None, "unit": "relevant days", "label": txt("The LCR formula gives no daily path, so no survival period.",
                                                                     "La fórmula del LCR no da trayectoria diaria, así que no hay periodo de supervivencia.")}
    if sv["kind"] == "survives-horizon":
        return {"value": None, "unit": "relevant days",
                "label": txt(f"Survival period: survives the {h}-day horizon", f"Periodo de supervivencia: sobrevive el horizonte de {h} días")}
    return {"value": float(sv["day"]), "unit": "relevant days",
            "label": txt("Survival period (first day the NLP is negative)", "Periodo de supervivencia (primer día con NLP negativo)")}
