"""The c13-outputs (one per deficiency) and c13-models documents of C13 from the engine results.

Every PLA statistic, zone, exception count and test row is returned by a ``riskvalidation`` function (CT-1305); this module orders
them, counts the zones the engine returned, names them and writes the bilingual text. The aggregate desk rows are engine rows of
a named replication (the one with the median count), never a number made here.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from riskvalidation.validation import market as val

from ...core.text import number, percent
from . import generator, params
from . import measure as ms
from .params import ALPHAS, IDS, WINDOW_DAYS

MODEL_ID = "desk-risk-model"
POLICY_NOTE = "median-across-replications"


def T(en: str, es: str) -> dict[str, str]:
    return {"en": en, "es": es}


def rv_version() -> str:
    from importlib.metadata import version

    return version("riskvalidation")


NOTICE = T(
    "Synthetic data: this is generated desk P&L with a risk model whose deficiency is planted, not the book of any real desk and not "
    "evidence about any bank. The truth is known by construction, so each result is shown beside the deficiency it is meant to detect.",
    "Datos sintéticos: es un P&L de mesa generado con un modelo de riesgo cuya deficiencia está plantada, no el libro de ninguna mesa "
    "real ni evidencia sobre ningún banco. La verdad es conocida por construcción, de modo que cada resultado se muestra junto a la "
    "deficiencia que debe detectar.")

SIGN_CONVENTION = {
    "engine_convention": "return-negative", "document_convention": "positive-loss",
    "definition": T("The engine stores VaR and ES in the return convention (negative numbers at the tail level alpha); this document "
                    "stores positive loss numbers, as decimals of the desk notional. HPL and RTPL are signed P&L as decimals of the "
                    "desk notional (a loss is negative).",
                    "El motor guarda VaR y ES en la convención de retornos (números negativos al nivel alfa); este documento guarda "
                    "pérdidas positivas, como decimales del nominal de la mesa. HPL y RTPL son P&L con signo como decimales del nominal "
                    "de la mesa (una pérdida es negativa).")}

TITLE = {
    "none": T("No deficiency: the risk model is exact", "Sin deficiencia: el modelo de riesgo es exacto"),
    "missing-basis": T("Missing basis: the model leaves out the instrument basis", "Base omitida: el modelo omite la base del instrumento"),
    "stale-volatility": T("Stale volatility: the model uses the volatility of 20 days ago", "Volatilidad rezagada: el modelo usa la volatilidad de hace 20 días"),
    "wrong-correlation": T("Wrong correlation: the model overstates the factor correlation by 0.3", "Correlación errónea: el modelo sobreestima la correlación de los factores en 0,3"),
    "omitted-factor": T("Omitted factor: the model leaves out a risk factor", "Factor omitido: el modelo omite un factor de riesgo"),
    "time-misalignment": T("Time misalignment: the risk-theoretical P&L is dated one day off", "Desfase temporal: el P&L teórico por riesgo está fechado un día desfasado"),
}
SHORT = {"none": "None", "missing-basis": "Missing basis", "stale-volatility": "Stale vol", "wrong-correlation": "Wrong corr.",
         "omitted-factor": "Omitted factor", "time-misalignment": "Misaligned"}
SHORT_ES = {"none": "Ninguna", "missing-basis": "Base omitida", "stale-volatility": "Vol. rezagada", "wrong-correlation": "Correl. errónea",
            "omitted-factor": "Factor omitido", "time-misalignment": "Desfasado"}
MECHANISM = {
    "none": T("No deficiency: the risk model is exact up to the pricing noise (the size of the test).",
              "Sin deficiencia: el modelo de riesgo es exacto salvo el ruido de valoración (el tamaño del test)."),
    "missing-basis": T("The hypothetical P&L carries a basis between the traded instrument and the risk factor that the risk model leaves out.",
                       "El P&L hipotético incluye una base entre el instrumento y el factor de riesgo que el modelo de riesgo omite."),
    "stale-volatility": T("The risk model scales the day's factor shocks with the volatility of 20 days earlier, so its P&L and its VaR lag the true volatility.",
                          "El modelo de riesgo escala los choques del día con la volatilidad de 20 días antes, de modo que su P&L y su VaR rezagan la volatilidad verdadera."),
    "wrong-correlation": T("The risk model maps the market drivers to the two factors with a correlation 0.3 above the true one, so a hedged desk looks safer than it is.",
                           "El modelo de riesgo traduce los impulsores de mercado a los dos factores con una correlación 0,3 sobre la verdadera, de modo que una mesa cubierta parece más segura de lo que es."),
    "omitted-factor": T("The risk model leaves out a third risk factor the desk is exposed to.",
                        "El modelo de riesgo omite un tercer factor de riesgo al que la mesa está expuesta."),
    "time-misalignment": T("The risk-theoretical P&L is dated one day off the hypothetical P&L.",
                           "El P&L teórico por riesgo está fechado un día desfasado del P&L hipotético."),
}
TRUE_MODEL = T(
    "A two-factor spread desk (long factor 1, short factor 2) with a common stochastic volatility known at the start of the day and "
    "correlated factors; the hypothetical P&L is the exact revaluation plus a small pricing noise, so the risk model is exact when "
    "nothing is planted. A deficiency changes only the risk model (its basis, volatility input, correlation, factor set or the date "
    "of its P&L).",
    "Una mesa de spread con dos factores (largo el factor 1, corto el factor 2) con una volatilidad estocástica común conocida al "
    "inicio del día y factores correlacionados; el P&L hipotético es la revaluación exacta más un pequeño ruido de valoración, de "
    "modo que el modelo de riesgo es exacto cuando no se planta nada. Una deficiencia cambia solo el modelo de riesgo (su base, su "
    "volatilidad de entrada, su correlación, su conjunto de factores o la fecha de su P&L).")
INTENDED_NOTE = {
    "none": T("none", "ninguno"), "spearman": T("the Spearman statistic", "el estadístico de Spearman"),
    "ks": T("the Kolmogorov-Smirnov statistic", "el estadístico de Kolmogorov-Smirnov"), "either": T("either statistic", "cualquiera de los estadísticos")}


#: the planted deficiencies in Spanish, for a title (U16-R2 b06 B2: "the planted omitted factor" inside a Spanish sentence)
DEFICIENCY_ES = {"omitted-factor": "factor omitido", "wrong-correlation": "correlación errónea", "stale-volatility": "volatilidad desactualizada",
                 "time-misalignment": "desfase temporal", "missing-basis": "base faltante"}


def _p(x: float) -> str:
    """A share as a percent inside a Spanish text (96,0 %)."""
    return percent(x, 1, lang="es")


def _n(x: float) -> str:
    return number(x, 0, lang="es")


def generator_block(did: str, n: int) -> dict[str, Any]:
    return {"name": params.GENERATOR_NAME, "n_risk_factors": 3 if did == "omitted-factor" else 2, "pnl_unit": "decimal-of-desk-notional",
            "window_days": WINDOW_DAYS, "n_replications": n, "seed_base": params.seed_base(did), "seed_rule": params.SEED_RULE, "notice": NOTICE}


def known_block(did: str) -> dict[str, Any]:
    d = params.deficiency(did)
    return {"deficiency_id": did, "planted": d["planted"], "mechanism": MECHANISM[did], "parameters": [dict(p) for p in d["parameters"]],
            "intended_to_fail": d["intended"]}


def model_summary(did: str, rv: str) -> dict[str, Any]:
    rho_m = params.RHO_TRUE + (params.value(did, "correlation_error") if did == "wrong-correlation" else 0.0)
    pars = {"assumed_factor_correlation": {"value": rho_m, "unit": "correlation"},
            "modelled_risk_factors": {"value": 2.0, "unit": "count"},
            "volatility_lag": {"value": params.value(did, "vol_lag_days") if did == "stale-volatility" else 0.0, "unit": "days"},
            "pnl_dating_lag": {"value": params.value(did, "lag_days") if did == "time-misalignment" else 0.0, "unit": "days"}}
    return {"id": MODEL_ID, "family": "market-var-es", "rung": "R0",
            "title": T(f"Desk risk model: {TITLE[did]['en'].split(':')[0].lower()}", f"Modelo de riesgo de mesa: {TITLE[did]['es'].split(':')[0].lower()}"),
            "short_title": T(SHORT[did], SHORT_ES[did]), "engine": "riskvalidation.market.frtb", "engine_version": rv, "licence": "MIT",
            "calibration": None, "parameters": pars, "checkpoint_sha256": None}


def pla_block(m: ms.Measurement) -> dict[str, Any]:
    return {"thresholds": dict(params.PLA_THRESHOLDS), "spearman": ms.distribution(m.spearman), "ks": ms.distribution(m.ks),
            "zones": {"n": m.n, "overall": m.zone_counts("overall"), "spearman": m.zone_counts("spearman"), "ks": m.zone_counts("ks")}}


def desk_block(m: ms.Measurement, limits: dict[float, int]) -> list[dict[str, Any]]:
    out = []
    for a in ALPHAS:
        n_over = m.n_over_limit(a)
        out.append({"alpha": a, "basis": "HPL", "limit_exceptions": limits[a], "n_days": WINDOW_DAYS,
                    "exceptions": ms.distribution(m.exceptions[a]), "n_within_limit": m.n - n_over, "n_over_limit": n_over,
                    "share_over_limit": n_over / m.n})
    return out


def detection_block(did: str, m: ms.Measurement) -> dict[str, Any]:
    p = m.n_amber_or_red / m.n
    lo, hi = ms.wilson(m.n_amber_or_red, m.n)
    rule = T("Caught when the joint PLA zone is amber or red. Size run: the share is the false-alarm rate.",
             "Detectado cuando la zona PLA conjunta es ámbar o roja. Corrida de tamaño: la proporción es la tasa de falsa alarma.") \
        if did == "none" else T("Caught when the joint PLA zone is amber or red.", "Detectado cuando la zona PLA conjunta es ámbar o roja.")
    return {"role": "size" if did == "none" else "power", "rule": rule, "n_replications": m.n, "n_amber_or_red": m.n_amber_or_red,
            "n_red": m.n_red, "share_amber_or_red": p, "share_red": m.n_red / m.n, "mc_se": float(np.sqrt(p * (1 - p) / m.n)),
            "ci_low": lo, "ci_high": hi,
            "by_test": {"spearman_flagged": m.n_spearman_flagged, "ks_flagged": m.n_ks_flagged, "desk_backtest_flagged": m.n_desk_flagged},
            "intended_test_flagged": m.intended_flagged(params.deficiency(did)["intended"])}


def median_index(values: np.ndarray) -> int:
    """The replication at the lower median of ``values`` (ties broken by index), the one an aggregate row and the example name."""
    order = sorted(range(len(values)), key=lambda i: (float(values[i]), i))
    return order[(len(order) - 1) // 2]


def example_block(did: str, m: ms.Measurement) -> tuple[dict[str, Any], dict[str, Any]]:
    """The example replication (median Spearman) with its statistics from the engine, and the engine's PLA test row for it."""
    i = median_index(m.spearman)
    rep = generator.replicate(did, i, m.case_seed)
    row = val.pla_test(rep.hpl, rep.rtpl, model_id=MODEL_ID)
    ex = {"replication_index": i, "seed": rep.seed, "hpl": [float(x) for x in rep.hpl], "rtpl": [float(x) for x in rep.rtpl],
          "spearman": float(row.statistic), "ks": float(row.metric), "zone": getattr(row.light, "value", str(row.light))}
    d = row.to_dict()
    d["notes"] = (f"The example replication {i} of {m.n}, the one with the median Spearman statistic; seed {rep.seed}. "
                  "Statistic is Spearman, metric is KS.")
    d["extras"] = {**d["extras"], "replication_index": i, "replication_seed": rep.seed, "selection": "median-spearman"}
    return ex, d


def desk_rows(did: str, m: ms.Measurement) -> list[dict[str, Any]]:
    """For each tail level the engine row of the replication with the median exception count, labelled as an aggregate."""
    rows = []
    for a in ALPHAS:
        i = median_index(m.exceptions[a].astype(float))
        rep = generator.replicate(did, i, m.case_seed)
        d = val.desk_backtest(rep.loss, rep.var[a], a, model_id=MODEL_ID, basis="HPL").to_dict()
        d["notes"] = (f"Aggregate over {m.n} replications: the engine row of replication {i}, the one with the median exception count "
                      f"({int(m.exceptions[a][i])}); seed {rep.seed}.")
        d["extras"] = {**d["extras"], "aggregate": POLICY_NOTE, "n_replications": m.n, "replication_index": i, "replication_seed": rep.seed}
        rows.append(d)
    return rows


def limits_from_rows(rows: list[dict[str, Any]]) -> dict[float, int]:
    return {float(r["segment"].split("=")[1]): int(r["metric"]) for r in rows}


def outputs_and_tests(did: str, m: ms.Measurement) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    example, pla_row = example_block(did, m)
    drows = desk_rows(did, m)
    limits = limits_from_rows(drows)
    desk = desk_block(m, limits)                                                   # the limits the engine rows carry, not a literal
    out = {"kind": "deficiency", "known_deficiency": known_block(did), "sign_convention": SIGN_CONVENTION, "generator": generator_block(did, m.n),
           "pnl_summary": [ms.pnl_summary("HPL", m.hpl_all), ms.pnl_summary("RTPL", m.rtpl_all)], "pla": pla_block(m), "example": example,
           "desk_backtest": desk, "detection": detection_block(did, m)}
    return out, [pla_row, *drows]


def impact(out: dict[str, Any]) -> dict[str, Any]:
    d = out["detection"]
    desk99 = next(r for r in out["desk_backtest"] if r["alpha"] == 0.01)
    return {
        "share_caught": {"value": d["share_amber_or_red"], "unit": "share",
                         "label": T("Replications where the PLA is amber or red", "Replicaciones donde el PLA es ámbar o rojo")},
        "share_red": {"value": d["share_red"], "unit": "share", "label": T("Replications where the PLA is red", "Replicaciones donde el PLA es rojo")},
        "share_desk_over_limit_99": {"value": desk99["share_over_limit"], "unit": "share",
                                     "label": T("Replications where the desk is over its 99 percent exception limit",
                                                "Replicaciones donde la mesa supera su límite de excepciones al 99 por ciento")}}


def findings(out: dict[str, Any]) -> list[dict[str, Any]]:
    k, d = out["known_deficiency"], out["detection"]
    did = k["deficiency_id"]
    p, p_red = d["share_amber_or_red"], d["share_red"]
    desk = {r["alpha"]: r for r in out["desk_backtest"]}
    f: list[dict[str, Any]] = []
    if did == "none":
        ok = p <= 0.05
        f.append({"id": "F-SIZE", "severity": "S4" if ok else "S3", "status": "accepted" if ok else "open", "evidence": ["market.pla_test"],
                  "title": T(f"With no deficiency the PLA is amber or red in {p:.1%} of {d['n_replications']:,} replications (red in {p_red:.1%}): the false-alarm rate of the test",
                             f"Sin deficiencia el PLA es ámbar o rojo en {_p(p)} de {_n(d['n_replications'])} replicaciones (rojo en {_p(p_red)}): la tasa de falsa alarma del test")})
    else:
        sev, status = ("S4", "accepted") if p >= 0.95 else (("S3", "open") if p >= 0.5 else ("S2", "open"))
        name_es = DEFICIENCY_ES.get(did, did.replace('-', ' '))
        if p >= 0.5:
            title = T(f"The PLA catches the planted {did.replace('-', ' ')} in {p:.1%} of {d['n_replications']:,} replications "
                      f"(amber or red; red in {p_red:.1%}; 95% interval {d['ci_low']:.1%} to {d['ci_high']:.1%})",
                      f"El PLA detecta la deficiencia plantada ({name_es}) en {_p(p)} de {_n(d['n_replications'])} replicaciones "
                      f"(ámbar o rojo; rojo en {_p(p_red)}; intervalo de 95 % {_p(d['ci_low'])} a {_p(d['ci_high'])})")
        else:
            # a miss states the miss rate, then the catch rate it comes from (R2b c14 B1: "misses ... in 0.0%" read as never missing)
            title = T(f"The PLA misses the planted {did.replace('-', ' ')} in {1 - p:.1%} of {d['n_replications']:,} replications: it is amber or "
                      f"red in {p:.1%} (red in {p_red:.1%}; 95% interval {d['ci_low']:.1%} to {d['ci_high']:.1%})",
                      f"El PLA no detecta la deficiencia plantada ({name_es}) en {_p(1 - p)} de {_n(d['n_replications'])} replicaciones: es ámbar "
                      f"o rojo en {_p(p)} (rojo en {_p(p_red)}; intervalo de 95 % {_p(d['ci_low'])} a {_p(d['ci_high'])})")
        f.append({"id": "F-PLA", "severity": sev, "status": status, "evidence": ["market.pla_test"], "title": title})
        n_int = d["intended_test_flagged"]
        f.append({"id": "F-INTENDED", "severity": "S3" if n_int / d["n_replications"] >= 0.5 else "S2", "status": "open", "evidence": ["market.pla_test"],
                  "title": T(f"The statistic meant to break ({INTENDED_NOTE[k['intended_to_fail']]['en']}) flags {n_int / d['n_replications']:.1%} of the replications",
                             f"El estadístico que debía romperse ({INTENDED_NOTE[k['intended_to_fail']]['es']}) marca {_p(n_int / d['n_replications'])} de las replicaciones")})
    f.append({"id": "F-DESK", "severity": "S3" if desk[0.01]["share_over_limit"] >= 0.05 or desk[0.025]["share_over_limit"] >= 0.05 else "S4",
              "status": "open" if max(desk[0.01]["share_over_limit"], desk[0.025]["share_over_limit"]) >= 0.05 else "accepted",
              "evidence": ["market.desk_backtest"],
              "title": T(f"The desk exceeds its exception limit in {desk[0.025]['share_over_limit']:.1%} of the replications at 97.5% "
                         f"(limit {desk[0.025]['limit_exceptions']}) and {desk[0.01]['share_over_limit']:.1%} at 99% (limit {desk[0.01]['limit_exceptions']})",
                         f"La mesa supera su límite de excepciones en {_p(desk[0.025]['share_over_limit'])} de las replicaciones al 97,5 % "
                         f"(límite {desk[0.025]['limit_exceptions']}) y {_p(desk[0.01]['share_over_limit'])} al 99 % (límite {desk[0.01]['limit_exceptions']})")})
    return f


def models_document(plan: dict[str, Any], rv: str) -> dict[str, Any]:
    n = plan["n_replications"]
    deficiencies = [{"deficiency_id": d["id"], "planted": d["planted"], "mechanism": MECHANISM[d["id"]],
                     "parameters": [dict(p) for p in d["parameters"]], "intended_to_fail": d["intended"]} for d in params.DEFICIENCIES]
    fit = {
        "sign_convention": SIGN_CONVENTION,
        "generator": {"name": params.GENERATOR_NAME, "true_risk_model": TRUE_MODEL, "parameters": params.generator_parameters(),
                      "pnl_unit": "decimal-of-desk-notional", "window_days": WINDOW_DAYS, "seed_rule": params.SEED_RULE, "notice": NOTICE},
        "deficiencies": deficiencies, "pla_thresholds": dict(params.PLA_THRESHOLDS),
        "desk_limits": [{"alpha": a, "limit_exceptions": l, "reference": "MAR32.18 to MAR32.19"} for a, l in plan["limits"].items()],
        "replication_plan": {"n_replications": n, "seed_base": params.seed_base("none"), "seed_rule": params.SEED_RULE}}
    record = {**model_summary("none", rv), "id": MODEL_ID, "title": T("Desk risk model (the model under test)", "Modelo de riesgo de mesa (el modelo bajo prueba)"),
              "short_title": T("Desk risk model", "Modelo de riesgo de mesa"),
              "details": {"variants": [{"deficiency_id": d, "seed_base": params.seed_base(d)} for d in IDS]}}
    return {"fit_id": "generator", "model": [record], "fit": fit}
