"""The C18 variant documents: the four scenario variants (``c18-outputs``), the t-copula aggregation variant (``c18-outputs-aggregation``) and the
reverse stress variant (``c18-outputs-reverse``), assembled from the engine's results.

Nothing is computed here that the engine provides: this module orders, labels and maps (``TestResult.to_dict()`` rows, ``PlanYear`` rows,
``BandRow`` rows). The only arithmetic is the one a contract states as a field: shares, sums of the four risks, ratios to RWA, the peak
deviation of a path and the sum of the losses of a year.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.stress import capital as rv_cap
from riskvalidation.validation import stress as rv_vs

from . import aggregation as agg
from . import capital as cap
from . import models, nii
from . import params as P
from . import satellites as sat
from .anchors import Anchors
from .fed import FedInputs
from .marginals import Marginal
from .scenarios import Scenario

T = P.text
NON_CREDIT_BASIS = T(
    "Expected losses of the scenario by risk and year. Credit comes from the satellite projections: the exposure of each Banco Andino class times the mean of the four "
    "quarterly rates of the year. Market has no position book in C07 or C15 and no source maps a macro path to the operational loss, so each carries its annual expected "
    "loss in every scenario and year; the stressed loss is therefore a floor. IRRBB is nil here: an EVE change is not a profit-and-loss item of the banking book and stays "
    "out of the capital path; the rate path acts on the net interest income of the PPNR row.",
    "Pérdidas esperadas del escenario por riesgo y año. El crédito sale de las proyecciones de los satélites: la exposición de cada clase de Banco Andino por el promedio de "
    "las cuatro tasas trimestrales del año. Mercado no tiene libro de posiciones en C07 ni en C15 y ninguna fuente liga una trayectoria macro con la pérdida operacional, por "
    "lo que cada uno lleva su pérdida esperada anual en todo escenario y año; la pérdida bajo tensión es por tanto un piso (suelo). IRRBB es nulo aquí: un cambio de EVE no es "
    "una partida de resultados del libro bancario y queda fuera de la trayectoria de capital; la trayectoria de tasas actúa sobre el margen financiero de la fila de PPNR.")
BACKCAST_SENTENCE = T("The stressed credit path rests on satellites that fail their own 2020 to 2025 back-cast.",
                      "La trayectoria de crédito bajo tensión descansa en satélites que fallan en su propia retroproyección de 2020 a 2025.")
#: the design limit of the non-credit losses: market and operational at their expected loss, IRRBB out of the capital path (its losses are
#: nil in the documents; U16-R3 c19 M3: the title said IRRBB was held at its expected loss)
NON_CREDIT_FINDING = T("Only credit responds to the scenario: market and operational losses are held at their expected loss and IRRBB stays outside the capital "
                       "path, so the stressed loss is a floor.",
                       "Solo el crédito responde al escenario: las pérdidas de mercado y operacional se mantienen en su pérdida esperada y el IRRBB queda fuera de la "
                       "trayectoria de capital, por lo que la pérdida bajo tensión es un piso.")


def milder_title(n: int) -> dict[str, str]:
    """The finding on the path variables milder than the crisis, singular for one (U16-R3 c19 m3: "1 path variables ... are milder")."""
    if n == 1:
        return T("1 path variable of this scenario is milder than the global financial crisis (ratio below 0.75).",
                 "1 variable de trayectoria de este escenario es más suave que la crisis financiera global (razón bajo 0,75).")
    return T(f"{n} path variables of this scenario are milder than the global financial crisis (ratio below 0.75).",
             f"{n} variables de trayectoria de este escenario son más suaves que la crisis financiera global (razón bajo 0,75).")


def _join(a: dict[str, str], b: dict[str, str]) -> dict[str, str]:
    return {k: f"{a[k]} {b[k]}" for k in a}


def plain(x: Any) -> Any:
    if isinstance(x, dict):
        return {k: plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [plain(v) for v in x]
    if isinstance(x, (np.floating, np.integer)):
        return x.item()
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.ndarray):
        return [plain(v) for v in x.tolist()]
    return x


def rows_of(results: list[Any]) -> list[dict[str, Any]]:
    return [plain(r.to_dict()) for r in results]


@dataclass
class Core:
    """Everything the variants share, computed once."""

    anchors: Anchors
    fed: FedInputs
    sats: dict[str, sat.Satellite]
    named: dict[str, dict[str, Any]]
    marginals: list[Marginal]
    band_base: Any
    band_stress: Any
    agg_base: agg.AggregationResult
    agg_stress: agg.AggregationResult
    target: cap.Target
    nii_12m: float
    stage_balances: np.ndarray
    class_lgd: dict[str, float]
    backcasts: dict[str, dict[str, Any]]
    descriptive: list[dict[str, Any]]
    space: dict[str, Any]
    engine_version: str
    model_records: list[dict[str, Any]]
    provenance_lineage: Any
    lane: dict[str, Any]
    seed: int = P.SEED
    n_draws: int = P.N_DRAWS


def envelope_models(core: Core) -> list[dict[str, Any]]:
    return [{k: v for k, v in m.items() if k != "details"} for m in core.model_records]


def ec_by_risk(core: Core) -> dict[str, float]:
    return {m.risk: m.ec for m in core.marginals}


def severity(core: Core, sc: Scenario) -> tuple[dict[str, Any], list[Any]]:
    """The severity of each path against the global financial crisis, from the Board's historic table (decision Y3)."""
    hq = core.fed.history.set_index("quarter_end")
    rows, tests = [], []
    for p in sc.block["paths"]:
        reg = p["maps_to_regressor"]
        pre = float(hq.loc["2007-12-31", reg])
        window = hq.loc[P.GFC_START: P.GFC_END, reg].to_numpy(dtype=float)
        hist_peak = float(np.max(np.abs(window - pre)))
        target = p["transposition"]["target"]["value"]
        devs = [abs(q["value"] - target) for q in p["transposed"]]
        peak = max(devs)
        stress = sc.key != "baseline"
        rows.append({"variable": p["variable"], "maps_to_regressor": reg, "unit": p["unit"], "path_peak_deviation": peak,
                     "path_peak_quarter": p["transposed"][devs.index(peak)]["date"], "history_peak_deviation": hist_peak,
                     "history_window": {"start": P.GFC_START, "end": P.GFC_END},
                     "history_source": T("The largest absolute deviation from the 2007 Q4 value inside 2008 Q1 to 2009 Q4, read from the Federal Reserve historic table "
                                         "(an agency series)."),
                     "ratio": peak / hist_peak if hist_peak else 0.0, "is_stress": stress})
        tests.append(rv_vs.scenario_severity(peak, hist_peak, stress, model_id="c18-capital-engine", segment=reg))
    block = {"reference_episode": {"name": "global-financial-crisis", "start": P.GFC_START, "end": P.GFC_END,
                                   "source": T("2008 to 2009, the episode the satellites are back-cast through and the EBA documents severity against (05 l.422)")},
             "minimum_ratio": 0.75, "rows": rows}
    return block, tests


def sensitivity_test(core: Core) -> Any:
    """One row for the coefficients of the five satellites: a wrong sign anywhere is reported (the engine counts them, the extras name them)."""
    est, signs, names = [], [], []
    for lt, s in core.sats.items():
        for n, e in zip(s.fit.coefficient_names, s.fit.estimates, strict=True):
            est.append(e)
            signs.append(P.EXPECTED_SIGN[n])
            names.append(f"{lt}:{n}")
    t = rv_vs.sensitivity_monotonicity(est, signs, model_id=sat.MODEL_ID)
    t.extras["coefficients"] = names
    return t


def losses_block(core: Core, credit: list[float]) -> dict[str, Any]:
    el = {m.risk: (m.el if m.el is not None else 0.0) for m in core.marginals}
    rows = []
    for y, end in enumerate(P.year_ends()):
        v = {"credit": credit[y], "market": el["market"], "irrbb": 0.0, "operational": el["operational"]}
        rows.append({"year": y + 1, "period_end": end, **v, "total": float(sum(v.values()))})
    return {"scenario_losses": rows, "basis": NON_CREDIT_BASIS}


def baseline_cet1_path(core: Core, baseline_losses: list[float], baseline_nii: list[float]) -> list[float]:
    cet1, out = core.anchors.cet1_clp_m, []
    for y in range(3):
        r = rv_cap.ppnr_row(baseline_nii[y], core.named["ppnr_fee_ratio"]["value"], core.named["ppnr_cost_ratio"]["value"])
        cet1 = cet1 + r.ppnr - baseline_losses[y]
        out.append(cet1)
    return out


def static_flows(core: Core, class_rates: dict[str, np.ndarray]) -> np.ndarray:
    """The new stage 3 exposure of each quarter: the quarterly charge-off amount over the LGD of the class (the exposure that defaulted)."""
    exp = core.anchors.class_exposure_clp_m
    return np.array([sum(exp[c] * max(float(class_rates[c][q]), 0.0) / 4.0 / core.class_lgd[c] for c in P.CLASSES) for q in range(P.HORIZON_QUARTERS)])


def findings_scenario(core: Core, sc: Scenario, doc_outputs: dict[str, Any], tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    a = doc_outputs["aggregation"]
    total = a["headline"]["capital_clp_m"]
    gauss = next(r for r in a["band"] if r["method"] == "gaussian-copula")["capital_clp_m"]
    out.append({"id": "headline-simple-sum", "severity": "S4", "status": "open", "evidence": ["aggregation.simple_sum_and_variance_covariance"],
                "title": _join(T(f"The headline capital is the simple sum, CLP {total:,.0f} million; the Gaussian copula figure, {1 - gauss / total:.1%} lower, is information and not capital.",
                                 f"El capital principal es la suma simple, CLP {P.es(total, ',.0f')} millones; la cifra de la cópula gaussiana, {P.es(1 - gauss / total, '.1%')} menor, es información y no capital."),
                           BACKCAST_SENTENCE)})
    plan = {c["case"]: c for c in doc_outputs["capital_plan"]["cases"]}
    sw = plan["stress-without-mitigation"]["years"]
    oi = doc_outputs["internal_capital_target"]["oi"]
    worst = min(sw, key=lambda y: y["pe"]["pct_of_rwa"] - oi)
    head = worst["pe"]["pct_of_rwa"] - oi
    if head < 0:
        out.append({"id": "internal-target-not-held", "severity": "S2", "status": "open", "evidence": ["design:outputs.capital_plan"],
                    "title": T(f"Under this scenario the PE ratio falls to {worst['pe']['pct_of_rwa']:.2%} of RWA in year {worst['year']}, {-head:.2%} of RWA below the internal "
                               f"target of {oi:.2%}.", f"Bajo este escenario la razón de PE cae a {P.es(worst['pe']['pct_of_rwa'], '.2%')} de los APR en el año {worst['year']}, "
                               f"{P.es(-head, '.2%')} de los APR bajo el objetivo interno de {P.es(oi, '.2%')}.")})
    else:
        out.append({"id": "internal-target-held", "severity": "S4", "status": "open", "evidence": ["design:outputs.capital_plan"],
                    "title": T(f"Under this scenario the PE ratio stays {head:.2%} of RWA above the internal target of {oi:.2%} at its lowest, in year {worst['year']}.",
                               f"Bajo este escenario la razón de PE se mantiene {P.es(head, '.2%')} de los APR sobre el objetivo interno de {P.es(oi, '.2%')} en su punto más bajo, el año {worst['year']}.")})
    stack = rv_cap.chilean_cet1_stack(core.anchors.stack["c_ccyb"], core.anchors.stack["c_dsib"], core.named["reverse_p2_cet1"]["value"])
    low = min(sw, key=lambda y: y["cet1"]["pct_of_rwa"])
    if low["cet1"]["pct_of_rwa"] < stack:
        out.append({"id": "cet1-stack-breached", "severity": "S1", "status": "open", "evidence": ["design:outputs.headline_cet1"],
                    "title": T(f"On the loss-only path CET1 falls to {low['cet1']['pct_of_rwa']:.2%} of RWA in year {low['year']}, below the Chilean legal minimum stack of {stack:.2%}; "
                               "the labelled PPNR row, which credits earnings, is shown beside it.",
                               f"En la trayectoria solo de pérdidas el CET1 cae a {P.es(low['cet1']['pct_of_rwa'], '.2%')} de los APR en el año {low['year']}, bajo el mínimo legal de {P.es(stack, '.2%')}; "
                               "la fila rotulada de PPNR, que acredita utilidades, se muestra al lado.")})
    deficit = [y for y in sw if y["deficit_clp_m"] > 0]
    if deficit:
        d = max(deficit, key=lambda y: y["deficit_clp_m"])
        out.append({"id": "legal-minimum-breached", "severity": "S1", "status": "open", "evidence": ["design:outputs.capital_plan"],
                    "title": T(f"The stress path leaves a deficit of CLP {d['deficit_clp_m']:,.0f} million against the legal minimum of PE in year {d['year']}.",
                               f"La trayectoria de tensión deja un déficit de CLP {P.es(d['deficit_clp_m'], ',.0f')} millones frente al mínimo legal de PE en el año {d['year']}.")})
    sens = next(t for t in tests if t["test_id"] == "stress.sensitivity_monotonicity")
    if sens["light"] in ("red", "amber"):
        out.append({"id": "satellite-sign", "severity": "S3", "status": "open", "evidence": ["stress.sensitivity_monotonicity"],
                    "title": T(f"{int(sens['statistic'])} satellite coefficients have the opposite of the expected sign: the stress maps through them with that caveat.",
                               f"{int(sens['statistic'])} coeficientes de los satélites tienen el signo contrario al esperado: la tensión pasa por ellos con esa salvedad.")})
    bad = [t for t in tests if t["test_id"] == "stress.satellite_backcast" and t["light"] in ("red", "amber")]
    if bad:
        out.append({"id": "satellite-backcast", "severity": "S3", "status": "open", "evidence": ["stress.satellite_backcast"],
                    "title": T(f"{len(bad)} of the 5 satellites do not back-cast the 2020 to 2025 peak within the thresholds (size or timing).",
                               f"{len(bad)} de los 5 satélites no reproducen el pico de 2020 a 2025 dentro de los umbrales (tamaño u oportunidad).")})
    mild = [t for t in tests if t["test_id"] == "stress.scenario_severity" and t["light"] == "amber"]
    if mild and sc.key != "baseline":
        out.append({"id": "scenario-milder-than-gfc", "severity": "S3", "status": "open", "evidence": ["stress.scenario_severity"],
                    "title": milder_title(len(mild))})
    out.append({"id": "non-credit-losses-at-expected-loss", "severity": "S3", "status": "open", "evidence": ["design:non-credit-losses-at-expected-loss"],
                "title": NON_CREDIT_FINDING})
    return out


def scenario_document(core: Core, sc: Scenario, baseline_totals: list[float] | None, baseline_nii: list[float] | None) -> dict[str, Any]:
    """One scenario variant: the document outputs, tests, impact and findings (the envelope is added by the bake)."""
    a = core.anchors
    proj = sat.project_all(core.sats, sc.transposed)
    crates = sat.class_rates(proj)
    credit = sat.credit_losses(crates, a.class_exposure_clp_m)
    losses = losses_block(core, credit)
    totals = [r["total"] for r in losses["scenario_losses"]]
    head_rows, path = cap.headline_rows(a.cet1_clp_m, totals, a.rwa_clp_m)
    reg, variable = nii.rate_of(sc.transposed, sc.block["paths"])
    jump = next(p["transposition"]["target"]["value"] for p in sc.block["paths"] if p["maps_to_regressor"] == reg)
    shifts = nii.yearly_shifts_bp(sc.transposed, reg, jump)
    nii_years = nii.nii_by_year(a, shifts)
    ppnr, ppnr_list = cap.ppnr_block(path, nii_years, core.named, a.rwa_clp_m, nii.rate_statement(variable, reg))
    base_losses = totals if sc.key == "baseline" else baseline_totals
    base_nii = nii_years if sc.key == "baseline" else baseline_nii
    if base_losses is None or base_nii is None:
        raise ValueError("the baseline scenario is baked first: the base case of every variant is built on its losses and its PPNR")
    plan = rv_cap.capital_plan(a.rwa_clp_m, a.cet1_clp_m, a.at1_clp_m, a.t2_clp_m, baseline_cet1_path(core, base_losses, base_nii), totals, [0.0, 0.0, 0.0],
                               core.target.rv.oi, core.target.legal_minimum)
    plan_doc = {"cases": cap.plan_cases(plan, core.target.rv.oi, core.target.legal_minimum), "mitigation": cap.mitigation_block(), "alternative_sources": []}
    severe = [y.cet1 / y.rwa for y in plan["stress-without-mitigation"]]
    p2g = cap.p2g_block(a.cet1_clp_m / a.rwa_clp_m, severe, core.target)
    sev_block, sev_tests = severity(core, sc)
    outputs = {
        "kind": "scenario", "currency": "CLP", "units": {"money": "CLP millions", "ratio": "decimal", "dates": "ISO date; quarters as the date of the quarter end"},
        "bank": {"name": "Banco Andino", "synthetic": True, "as_of": P.AS_OF, "notice": models.BANK_NOTICE},
        "capital_start": cap.capital_start(a), "scenario": sc.block, "satellites": sat.blocks(core.sats, proj, a.class_exposure_clp_m), "losses": losses,
        "internal_capital_target": core.target.block, "capital_plan": plan_doc, "p2g_proxy": p2g, "annex3": cap.annex3(a, core.target, plan, ec_by_risk(core)),
        "headline_cet1": {"method": "loss-only-depletion",
                          "statement": _join(T("CET1 at the jump-off less the cumulative stressed losses; no revenue is invented. The row with PPNR is labelled and is not the headline."),
                                             BACKCAST_SENTENCE),
                          "rows": head_rows, "ppnr": ppnr},
        "severity": sev_block,
        "backcast": {"window": {"start": P.BACKCAST_START, "end": P.BACKCAST_END}, "per_loan_type": [{k: v for k, v in core.backcasts[lt].items() if k != "_test"} for lt in P.FED_TYPES],
                     "descriptive_2026": core.descriptive,
                     "statement": T("Satellites fitted on 1985 to 2019 (1991 to 2019 for the two real estate segments), run from 2019 Q4 on the realised regressors of 2020 Q1 to 2025 Q4 "
                                    "and compared with the realised net charge-off rates; 2026 Q1 and Q2 are shown as realised rates only, with no forecast claim.")},
        "aggregation": core.agg_base.block}
    flows = static_flows(core, crates)
    tests = (agg.band_tests(core.marginals, core.named["correlation_matrix_base"]["matrix"], core.band_base, core.band_stress, core.agg_base.tests[0]))
    rows = rows_of(tests)
    rows += rows_of([sensitivity_test(core)] +[core.backcasts[lt]["_test"] for lt in P.FED_TYPES] + [cap.static_balance_test(core.stage_balances, flows)] + sev_tests)
    sw = plan["stress-without-mitigation"]
    impact = {
        "capital_simple_sum": {"value": core.agg_base.block["headline"]["capital_clp_m"], "unit": "CLP millions",
                               "label": T("Headline capital: the simple sum of the four marginals")},
        "cet1_ratio_end_stress": {"value": sw[-1].cet1 / sw[-1].rwa, "unit": "share of RWA", "label": T("CET1 ratio at the end of year 3 under the stress without mitigation")},
        "oi_headroom_min": {"value": min(y.pe_pct for y in sw) - core.target.rv.oi, "unit": "share of RWA",
                            "label": T("Smallest headroom of the PE ratio over the internal target in the stress without mitigation")},
        "p2g_proxy": {"value": p2g["value"], "unit": "share of RWA", "label": T("P2G proxy, a Contraste approximation")}}
    return {"outputs": plain(outputs), "tests": rows, "impact": impact, "findings": findings_scenario(core, sc, plain(outputs), rows), "credit_losses": credit,
            "total_losses": totals, "nii": nii_years, "ppnr": ppnr_list, "rate": variable, "cet1_path": [float(x) for x in path]}
