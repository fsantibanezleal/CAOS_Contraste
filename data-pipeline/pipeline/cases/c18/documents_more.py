"""The t-copula aggregation variant (``c18-outputs-aggregation``) and the reverse stress variant (``c18-outputs-reverse``) of C18."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from . import aggregation as agg
from . import models
from . import params as P
from . import reverse as rev
from .documents import Core, plain, rows_of

T = P.text
UNITS = {"money": "CLP millions", "ratio": "decimal", "dates": "ISO date; quarters as the date of the quarter end"}


def _bank() -> dict[str, Any]:
    return {"name": "Banco Andino", "synthetic": True, "as_of": P.AS_OF, "notice": models.BANK_NOTICE}


def aggregation_document(core: Core) -> dict[str, Any]:
    """The baseline scenario's aggregation with the t copula at the nu set, the market-credit 0.8 stress and the references."""
    base, stress = core.agg_base, core.agg_stress
    corr = core.named["correlation_matrix_base"]["matrix"]
    tests = agg.band_tests(core.marginals, corr, core.band_base, core.band_stress, base.tests[0])
    ell = agg.elliptical_check(core.marginals, corr, core.n_draws, core.seed + 7)
    rs_test, rs_block = agg.rosenberg_schuermann(core.band_base, core.marginals)
    outputs = {
        "kind": "aggregation", "currency": "CLP", "units": UNITS, "bank": _bank(), "scenario_id": P.SCENARIOS["baseline"], "aggregation": base.block,
        "correlation_stress": {"pair": {"a": "market", "b": "credit", "value": 0.8}, "aggregation": stress.block},
        "copula_sensitivity": agg.copula_sensitivity(core.band_base), "rosenberg_schuermann": rs_block}
    rows = rows_of([*tests, ell, rs_test])
    a = core.anchors
    total = base.block["headline"]["capital_clp_m"]
    impact = {
        "capital_simple_sum": {"value": total, "unit": "CLP millions", "label": T("Headline capital: the simple sum of the four marginals")},
        "cet1_ratio_end_stress": {"value": a.cet1_clp_m / a.rwa_clp_m, "unit": "share of RWA",
                                  "label": T("CET1 ratio at the jump-off (this variant runs the baseline aggregation, not a stress)")},
        "oi_headroom_min": {"value": (a.cet1_clp_m + a.at1_clp_m + a.t2_clp_m) / a.rwa_clp_m - core.target.rv.oi, "unit": "share of RWA",
                            "label": T("Headroom of the PE ratio over the internal target at the jump-off")},
        "p2g_proxy": {"value": None, "unit": "share of RWA", "label": T("Not computed in this variant (it runs the aggregation only)")}}
    band = {r["method"] if r["method"] != "t-copula" else f"t-{r['nu']}": r["capital_clp_m"] for r in base.block["band"]}
    gauss, worst, lower = band["gaussian-copula"], band["worst-case"], band["lower-bound"]
    am = base.block["model_risk"]["barrieu_scandolo"]["am"]
    over = rs_block["case_additive_overestimate"]
    findings = [
        {"id": "headline-simple-sum", "severity": "S4", "status": "open", "evidence": ["aggregation.simple_sum_and_variance_covariance"],
         "title": T(f"The headline capital is the simple sum, CLP {total:,.0f} million. The dependence band runs from CLP {lower:,.0f} million (best case) to CLP {worst:,.0f} "
                    f"million (worst case); the Gaussian copula figure is {1 - gauss / total:.1%} below the sum and is information, not capital.",
                    f"El capital principal es la suma simple, CLP {P.es(total, ',.0f')} millones. La banda de dependencia va de CLP {P.es(lower, ',.0f')} millones (mejor caso) a CLP {P.es(worst, ',.0f')} "
                    f"millones (peor caso); la cifra de la cópula gaussiana está {P.es(1 - gauss / total, '.1%')} bajo la suma y es información, no capital.")},
        {"id": "model-risk", "severity": "S3", "status": "open", "evidence": ["aggregation.copula_choice_sensitivity"],
         "title": T(f"The aggregation model moves the figure by up to {am:.1%} over the Gaussian copula (the Barrieu and Scandolo add-on): sensitivity information for the "
                    "validator, never capital.",
                    f"El modelo de agregación mueve la cifra hasta {P.es(am, '.1%')} sobre la cópula gaussiana (el recargo de Barrieu y Scandolo): información de sensibilidad para el "
                    "validador, nunca capital.")},
        {"id": "rosenberg-schuermann-reference", "severity": "S4", "status": "open", "evidence": ["aggregation.rosenberg_schuermann_reference"],
         "title": T(f"The additive approximation exceeds the Gaussian copula figure by {over:.1%}; the published range of 30 to 40 percent is a reference and no gate.",
                    f"La aproximación aditiva excede la cifra de la cópula gaussiana en {P.es(over, '.1%')}; el rango publicado de 30 a 40 por ciento es una referencia y no una barrera.")}]
    return {"outputs": plain(outputs), "tests": rows, "impact": impact, "findings": findings}


def reverse_document(core: Core, loss_fn: Callable[[np.ndarray], float]) -> dict[str, Any]:
    """The minimum Mahalanobis distance scenario that takes CET1 to the Chilean legal minimum stack on the labelled PPNR path (decision Z10).

    The loss of the function is the three-year loss net of the cumulative PPNR of the baseline: CET1 at the jump-off plus the cumulative PPNR less the cumulative
    losses reaches the stack when that net loss equals the headroom of CET1 over the stack at the jump-off."""
    a = core.anchors
    stack = rev.failure_stack(a, core.named["reverse_p2_cet1"])
    start_ratio = a.cet1_clp_m / a.rwa_clp_m
    threshold = (start_ratio - stack["total"]) * a.rwa_clp_m
    space = core.space
    net_zero = float(loss_fn(np.zeros(len(space["factors"]))))
    rev.check_baseline(net_zero, threshold)
    best, each, test, p = rev.solve(loss_fn, space, threshold)
    desc = T("The three-year loss of Banco Andino net of the cumulative PPNR of the baseline scenario, when real GDP growth and the unemployment rate are both shifted for the "
             "twelve quarters by the same deviation from the Federal Reserve baseline path: CET1 at the jump-off plus the cumulative PPNR less the cumulative losses reaches the "
             "legal minimum stack when this net loss equals the headroom of CET1 over the stack. The satellites give the credit loss and the other risks carry their expected "
             "loss. The basis is the labelled PPNR row and rests on its assumptions (the fee and cost ratios); the headline CET1 path is the loss-only one. The loss is nonlinear "
             "through the probit link.",
             "La pérdida de tres años de Banco Andino neta del PPNR acumulado del escenario base, cuando el crecimiento del PIB real y la tasa de desempleo se desplazan juntos en "
             "los doce trimestres por la misma desviación respecto de la trayectoria base de la Reserva Federal: el CET1 de partida más el PPNR acumulado menos las pérdidas "
             "acumuladas llega al mínimo legal cuando esta pérdida neta iguala la holgura del CET1 sobre ese mínimo. Los satélites dan la pérdida de crédito y los demás riesgos "
             "llevan su pérdida esperada. La base es la fila rotulada de PPNR y descansa en sus supuestos (las razones de comisiones y de costos); la trayectoria principal de "
             "CET1 es la de solo pérdidas. La pérdida es no lineal por el enlace probit.")
    outputs = {
        "kind": "reverse", "currency": "CLP", "units": UNITS, "bank": _bank(),
        "failure_point": {"label": "contraste-formulation-not-regulatory",
                          "definition": T("CET1 over RWA reaches the Chilean legal minimum stack at the end of the three-year planning horizon on the labelled PPNR path (CET1 at the "
                                          "jump-off plus the cumulative PPNR less the cumulative losses): the formal statement is Contraste's, not regulatory text, and it rests on "
                                          "the assumptions of the PPNR row.",
                                          "El CET1 sobre APR llega al mínimo legal chileno al final del horizonte de planificación de tres años en la trayectoria rotulada de PPNR "
                                          "(CET1 de partida más PPNR acumulado menos pérdidas acumuladas): el enunciado formal es de Contraste, no texto regulatorio, y descansa en "
                                          "los supuestos de la fila de PPNR."),
                          "stack": stack, "cet1_ratio_start": start_ratio, "rwa_clp_m": a.rwa_clp_m, "horizon_years": 3},
        "factor_space": space, **rev.blocks(best, each, p, threshold, space, desc)}
    impact = {
        "capital_simple_sum": {"value": core.agg_base.block["headline"]["capital_clp_m"], "unit": "CLP millions",
                               "label": T("Headline capital: the simple sum of the four marginals")},
        "cet1_ratio_end_stress": {"value": stack["total"], "unit": "share of RWA", "label": T("CET1 ratio at the failure point: the legal minimum stack")},
        "oi_headroom_min": {"value": None, "unit": "share of RWA", "label": T("Not computed in this variant")},
        "p2g_proxy": {"value": None, "unit": "share of RWA", "label": T("Not computed in this variant")}}
    # each factor by its label, lower case inside the sentence (the R2b review c19: the title printed real_gdp_growth); the
    # articles of the sentence are those of these two factors, so another factor space stops the bake here
    assert [f["id"] for f in space["factors"]] == ["real_gdp_growth", "unemployment_rate"], space["factors"]
    names = [f["label"]["en"][0].lower() + f["label"]["en"][1:] for f in space["factors"]]
    names_es = [f["label"]["es"][0].lower() + f["label"]["es"][1:] for f in space["factors"]]
    x = best.x_star
    findings = [{"id": "reverse-scenario", "severity": "S3", "status": "open", "evidence": ["stress.reverse_solution_check"],
                 "title": T(f"On the labelled PPNR path, the most plausible scenario that takes CET1 to the legal minimum stack shifts {names[0]} by {x[0]:+.2f} and the {names[1]} by "
                            f"{x[1]:+.2f} points, a Mahalanobis distance of {best.distance:.2f} (tail probability {p:.1%}); the loss-only baseline already ends below the stack.",
                            f"En la trayectoria rotulada de PPNR, el escenario más plausible que lleva el CET1 al mínimo legal desplaza el {names_es[0]} en {P.es(x[0], '+.2f')} y la {names_es[1]} en "
                            f"{P.es(x[1], '+.2f')} puntos, a una distancia de Mahalanobis de {P.es(best.distance, '.2f')} (probabilidad de cola {P.es(p, '.1%')}); la base de solo pérdidas ya termina bajo el mínimo.")}]
    return {"outputs": plain(outputs), "tests": rows_of([test]), "impact": impact, "findings": findings, "solution": best, "plausibility": p,
            "net_loss_at_zero": net_zero}
