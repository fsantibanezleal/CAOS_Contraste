"""The c09-outputs (one per acceleration level) and c09-models documents of C09 from the engine results.

Every estimate, bias, interval, test row, floor and back-test number is returned by a ``riskvalidation`` function (CT-1007); this
module orders them, names them and writes the bilingual text. A CCF is written as ``{value, flag}`` with the engine's ``range_flag``
and is never clipped (CT-1005): after a censor or floor-cap treatment the estimate lies in [0, 1] by construction.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from riskvalidation.lgd_ead import ccf, floors
from riskvalidation.lgd_ead.workout import range_flag
from riskvalidation.validation import lgd_ead as val

from ...core.text import number, percent
from . import calibration, params
from . import estimators as est
from . import models as mdl
from .params import LEVELS, PARAMS, TOLERANCE


def T(en: str, es: str) -> dict[str, str]:
    return {"en": en, "es": es}


def rv_version() -> str:
    from importlib.metadata import version

    return version("riskvalidation")


def flagged(value: float) -> dict[str, Any]:
    return {"value": float(value), "flag": str(range_flag(np.array([value]))[0])}


SHAPED_ON = "fed-2025-cards-hypothetical-portfolios"

NOTICE = T(
    "Synthetic data: these are generated revolving credit lines, not observations of any portfolio and not evidence about any bank or "
    "card issuer. Their field structure and marginals follow the Federal Reserve's 2025 hypothetical card portfolios; the CCF each "
    "level draws balances with is the generator's own parameter, so every estimate is shown beside the truth it is meant to recover. "
    "Amounts in USD.",
    "Datos sintéticos: son líneas de crédito rotativas generadas, no observaciones de ninguna cartera ni evidencia sobre ningún banco o "
    "emisor de tarjetas. Su estructura de campos y sus marginales siguen las carteras hipotéticas de tarjetas de 2025 de la Reserva "
    "Federal; el CCF con que cada nivel simula los saldos es un parámetro del propio generador, de modo que cada estimación se muestra "
    "junto a la verdad que debe recuperar. Montos en USD.")

CONVENTION = {
    "name": "eu-undrawn",
    "definition": T("CCF = (EAD - drawn at the reference date) / (limit - drawn at the reference date): the share of the undrawn amount "
                    "drawn by default.",
                    "CCF = (EAD - utilizado en la fecha de referencia) / (límite - utilizado en la fecha de referencia): la parte del "
                    "monto no utilizado que se usa al incumplir."),
    "formula": "CCF = (EAD - E(t_r)) / (L(t_r) - E(t_r))",
    "us_terms": T("The same ratio is the loan equivalent (LEQ) in US terms; Qi (2009) calls EAD over outstanding the CCF and EAD over the "
                  "limit the EADF.",
                  "La misma razón es el equivalente de crédito (LEQ) en términos de EE.UU.; Qi (2009) llama CCF a EAD sobre el saldo y "
                  "EADF a EAD sobre el límite."),
}

DESIGN_LABEL = {
    "fixed-horizon": T("Fixed horizon: 12 months before default", "Horizonte fijo: 12 meses antes del incumplimiento"),
    "cohort": T("Yearly cohort: the cohort start", "Cohorte anual: el inicio de la cohorte"),
    "variable-horizon": T("Variable horizon: quarterly reference dates in the year before default",
                          "Horizonte variable: fechas trimestrales de referencia en el año previo al incumplimiento"),
}
MODEL_TITLE = {
    "ccf-fixed-horizon-none": T("CCF at 12 months, untreated", "CCF a 12 meses, sin tratamiento"),
    "ccf-fixed-horizon-censor": T("CCF at 12 months, values outside [0, 1] censored", "CCF a 12 meses, valores fuera de [0, 1] censurados"),
    "ccf-fixed-horizon-floor-cap": T("CCF at 12 months, floored at 0 and capped at 1", "CCF a 12 meses, con piso en 0 y tope en 1"),
    "ccf-fixed-horizon-bounded-scale": T("CCF at 12 months, fractional logit on the bounded scale",
                                         "CCF a 12 meses, logit fraccional en escala acotada"),
    "ccf-cohort-floor-cap": T("CCF at the cohort start, floored and capped", "CCF al inicio de la cohorte, con piso y tope"),
    "ccf-variable-horizon-floor-cap": T("CCF at quarterly reference dates, floored and capped",
                                        "CCF en fechas trimestrales de referencia, con piso y tope"),
    "direct-ead": T("Direct EAD: fractional logit of EAD over the limit", "EAD directo: logit fraccional de EAD sobre el límite"),
    "utilisation-change": T("Utilisation change: least squares on the change in drawn share",
                            "Cambio de utilización: mínimos cuadrados sobre el cambio de la parte utilizada"),
}
MODEL_SHORT = {
    "ccf-fixed-horizon-none": "CCF 12m", "ccf-fixed-horizon-censor": "CCF 12m censor", "ccf-fixed-horizon-floor-cap": "CCF 12m floor-cap",
    "ccf-fixed-horizon-bounded-scale": "CCF 12m logit", "ccf-cohort-floor-cap": "CCF cohort", "ccf-variable-horizon-floor-cap": "CCF variable",
    "direct-ead": "Direct EAD", "utilisation-change": "Util. change",
}
MODEL_SHORT_ES = {"ccf-fixed-horizon-censor": "CCF 12m censura", "ccf-fixed-horizon-floor-cap": "CCF 12m piso y tope",
                  "ccf-fixed-horizon-bounded-scale": "CCF 12m logit acotado", "ccf-cohort-floor-cap": "CCF cohorte",
                  "ccf-variable-horizon-floor-cap": "CCF variable", "direct-ead": "EAD directo", "utilisation-change": "Cambio de uso"}

#: money and share keys written without nine-digit compaction
EXACT = frozenset({"predicted_ead", "realised_ead", "gap", "mean_ead_before", "mean_ead_after", "threshold"})


def level_text(level: int) -> dict[str, str]:
    x = LEVELS[level]
    if x["window"] == 0:
        return T("Level 0: no acceleration; the undrawn amount is drawn at a constant rate over the twelve months before default.",
                 "Nivel 0: sin aceleración; el monto no utilizado se usa a ritmo constante en los doce meses previos al incumplimiento.")
    return T(f"Level {level}: in the last {x['window']} months before default the drawing rate is {x['factor']:g} times its earlier rate.",
             f"Nivel {level}: en los últimos {x['window']} meses previos al incumplimiento el ritmo de uso es {_g(x['factor'], 'es')} veces el anterior.")


def generator_block(level: int) -> dict[str, Any]:
    x = LEVELS[level]
    return {"name": "revolving-line-generator", "shaped_on": SHAPED_ON, "true_ccf": flagged(params.known_ccf(level)),
            "acceleration_factor": float(x["factor"]), "acceleration_window_months": int(x["window"]), "notice": NOTICE}


@dataclass
class LevelData:
    """Everything the bake measured at one acceleration level."""

    level: int
    fits: dict[str, mdl.Fitted]
    bounded: dict[str, Any]                       # design -> fractional logit fit (development sample)
    est: dict[tuple[str, str, str], list[est.Estimate]]    # (design, treatment, aggregator) -> one estimate per test replication
    test: dict[str, est.Observations]             # design -> the test replications pooled
    n_dev_defaults: int
    n_test_defaults: int
    tests: list[dict[str, Any]] = field(default_factory=list)


def bias_id(design: str, treatment: str, agg: str) -> str:
    return f"ccf-{design}-{treatment}-{agg}"


def ccf_block(level: int, data: LevelData) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The ``ccf_by_design`` block and its ``lgd_ead.ccf_estimator_bias`` test rows (one per row)."""
    truth = params.known_ccf(level)
    rows, tests = [], []
    for design in est.DESIGNS:
        pooled = est.treat(data.test[design], "none")
        for treatment in est.TREATMENTS:
            for agg in est.ESTIMATORS:
                runs = data.est[(design, treatment, agg)]
                values = np.array([r.value for r in runs])
                res = val.ccf_estimator_bias(values, truth, TOLERANCE, model_id=bias_id(design, treatment, agg))
                tests.append(res.to_dict())
                estimate = float(values.mean())
                rows.append({
                    "design": design, "treatment": treatment, "estimator": agg, "estimate": flagged(estimate), "truth": flagged(truth),
                    "bias": float(ccf.ccf_bias(estimate, truth)), "rmse": float(res.extras["rmse"]), "ci_low": float(res.extras["ci_low"]),
                    "ci_high": float(res.extras["ci_high"]), "n_defaults": int(sum(r.n_facilities for r in runs)),
                    "share_below_zero": pooled.n_below_zero / pooled.n_finite, "share_above_one": pooled.n_above_one / pooled.n_finite,
                    "within_tolerance": bool(res.extras["within_tolerance"])})
    return {"tolerance": TOLERANCE, "rows": rows}, tests


def distribution_block(data: LevelData) -> dict[str, Any]:
    obs = data.test["fixed-horizon"]
    tr = est.treat(obs, "none")
    edges = list(PARAMS["distribution_edges"])
    counts, _ = np.histogram(tr.values, bins=edges)
    return {"design": "fixed-horizon", "n": int(tr.n_finite), "edges": edges, "counts": [int(c) for c in counts],
            "n_below_zero": int(tr.n_below_zero), "n_above_one": int(tr.n_above_one)}


def ead_blocks(data: LevelData) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], dict[str, np.ndarray]]:
    """``ead_models``, ``ead_backtest`` and the ``lgd_ead.ead_backtest_by_band`` rows, with each model's test predictions."""
    models_out, rows, tests, preds = [], [], [], {}
    for m in mdl.MODELS:
        fit = data.fits[m["id"]]
        below = above = None
        if m["kind"] == "direct-ead":
            below, above = int(fit.ead_fit.extras["n_clipped_below"]), int(fit.ead_fit.extras["n_clipped_above"])
        models_out.append({"model_id": m["id"], "kind": m["kind"], "design": m["design"], "treatment": m["treatment"],
                           "covariates": mdl.covariates(m), "n_clipped_below": below, "n_clipped_above": above})
        bt = mdl.backtest(fit, data.test[mdl.MODEL_DESIGN[m["id"]]])
        tests.append(bt["test"].to_dict())
        rows.extend(bt["rows"])
        preds[m["id"]] = bt["pred"]
    return models_out, {"currency": PARAMS["currency"], "bands": [float(x) for x in PARAMS["band_edges"]], "rows": rows}, tests, preds


def floor_block(data: LevelData, preds: dict[str, np.ndarray]) -> dict[str, Any]:
    obs = data.test["fixed-horizon"]
    pred = preds["ccf-fixed-horizon-floor-cap"]
    rows = []
    for item, ref in (("unconditionally-cancellable", "CRE20.100"), ("commitments", "CRE20.98")):
        sa = floors.supervisory_ccf(item)
        fl = floors.ead_floor(obs.drawn_ref, obs.limit_ref, np.full(pred.size, sa), 0.5)
        bite = floors.apply_ead_floor(pred, fl)
        rows.append({"facility_class": item, "sa_ccf": float(sa), "reference": ref, "n": int(pred.size),
                     "share_binding": float(bite.share_binding), "mean_ead_before": float(bite.mean_before),
                     "mean_ead_after": float(bite.mean_after)})
    return {"currency": PARAMS["currency"], "rule": T("On-balance amount + 50% of the off-balance exposure at the SA CCF (CRE32.36, CRE32.64)",
                  "Monto en balance + 50 % de la exposición fuera de balance al CCF del método estandarizado (CRE32.36, CRE32.64)"),
            "off_balance_share": 0.5, "rows": rows}


def small_undrawn_block(data: LevelData) -> dict[str, Any]:
    obs = data.test["fixed-horizon"]
    switched, _ratio = ccf.small_undrawn_rule(obs.drawn_ref, obs.limit_ref, obs.ead, PARAMS["small_undrawn_threshold"])
    return {"currency": PARAMS["currency"], "threshold": float(PARAMS["small_undrawn_threshold"]), "applied": False,
            "n_switched": int(switched.sum()), "reference": "Qi (2009), OCC Economics Working Paper 2009-2"}


def replications(plan: dict[str, Any], data: LevelData) -> dict[str, Any]:
    return {"development": {"seeds": list(plan["development_seeds"]), "n_replications": len(plan["development_seeds"]),
                            "n_facilities": plan["n_facilities"], "n_defaults": data.n_dev_defaults},
            "test": {"seeds": list(plan["test_seeds"]), "n_replications": len(plan["test_seeds"]),
                     "n_facilities": plan["n_facilities"], "n_defaults": data.n_test_defaults}}


def outputs_and_tests(plan: dict[str, Any], level: int, data: LevelData) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ccf_by, bias_tests = ccf_block(level, data)
    models_out, backtest, bt_tests, preds = ead_blocks(data)
    out = {
        "kind": "acceleration-level", "level": level, "level_description": level_text(level), "currency": PARAMS["currency"],
        "convention": CONVENTION, "generator": generator_block(level), "replications": replications(plan, data), "ccf_by_design": ccf_by,
        "ccf_distribution": distribution_block(data), "ead_models": models_out, "ead_backtest": backtest,
        "ead_floor": floor_block(data, preds), "small_undrawn": small_undrawn_block(data)}
    return out, [*bias_tests, *bt_tests]


def row_of(out: dict[str, Any], design: str, treatment: str, agg: str) -> dict[str, Any]:
    return next(r for r in out["ccf_by_design"]["rows"] if (r["design"], r["treatment"], r["estimator"]) == (design, treatment, agg))


def impact(out: dict[str, Any]) -> dict[str, Any]:
    r = {d: row_of(out, d, "none", "pooled") for d in est.DESIGNS}
    bt = [x for x in out["ead_backtest"]["rows"]]
    worst = {m: max(abs(x["relative_gap"]) for x in bt if x["model_id"] == m) for m in {x["model_id"] for x in bt}}
    imp = {
        "true_ccf": {"value": out["generator"]["true_ccf"]["value"], "unit": "share", "label": T("Known CCF of the level", "CCF conocido del nivel")},
        "ccf_bias_fixed_horizon": {"value": r["fixed-horizon"]["bias"], "unit": "share",
                                   "label": T("Fixed-horizon CCF bias (untreated, pooled)", "Sesgo del CCF a horizonte fijo (sin tratar, agrupado)")},
        "ccf_bias_cohort": {"value": r["cohort"]["bias"], "unit": "share",
                            "label": T("Cohort CCF bias (untreated, pooled)", "Sesgo del CCF de cohorte (sin tratar, agrupado)")},
        "ccf_bias_variable_horizon": {"value": r["variable-horizon"]["bias"], "unit": "share",
                                      "label": T("Variable-horizon CCF bias (untreated, pooled)",
                                                 "Sesgo del CCF a horizonte variable (sin tratar, agrupado)")},
        "ead_worst_band_gap_ccf": {"value": worst["ccf-fixed-horizon-floor-cap"], "unit": "share",
                                   "label": T("Worst band EAD gap, CCF at 12 months (floor-cap)", "Peor brecha de EAD por banda, CCF a 12 meses (piso y tope)")},
        "ead_worst_band_gap_direct": {"value": worst["direct-ead"], "unit": "share",
                                      "label": T("Worst band EAD gap, direct EAD", "Peor brecha de EAD por banda, EAD directo")}}
    return imp


def _n(x: float, decimals: int) -> str:
    """A number inside a Spanish text, as the shell writes it."""
    return number(x, decimals, lang="es")


def _g(x: float, lang: str) -> str:
    """A factor as ``:g`` writes it (2, 1.5), with the language's decimal sign."""
    for decimals in range(7):
        if round(x, decimals) == x:
            return number(x, decimals, lang=lang)
    return number(x, 6, lang=lang)


def _signed(x: float, decimals: int, lang: str) -> str:
    return ("+" if x >= 0 else "") + number(x, decimals, lang=lang)


def _side(bias: float, decimals: int = 3) -> tuple[str, str]:
    """The distance of an estimate from the known CCF, in words. Where the title prints the estimate and the known value at three
    decimals, the distance takes four, so the printed difference agrees with the printed pair (R4 c11 m2: "0.752 against the known
    0.754, 0.001 below")."""
    en, es = number(abs(bias), decimals, lang="en"), number(abs(bias), decimals, lang="es")
    return (f"{en} below", f"{es} por debajo") if bias < 0 else (f"{en} above", f"{es} por encima")


def findings(out: dict[str, Any], first_month: float) -> list[dict[str, Any]]:
    """The findings of a level. ``first_month`` is the share of the test defaulters that defaulted in the first month of their
    cohort (the cohort design's excluded defaulters, ``Observations.n_excluded``), which the outputs do not carry."""
    truth = out["generator"]["true_ccf"]["value"]
    lvl = out["level"]
    fx = row_of(out, "fixed-horizon", "none", "mean")
    fp = row_of(out, "fixed-horizon", "none", "pooled")
    co = row_of(out, "cohort", "none", "pooled")
    va = row_of(out, "variable-horizon", "none", "pooled")
    fc = row_of(out, "fixed-horizon", "floor-cap", "mean")
    dm = next(m for m in out["ead_models"] if m["kind"] == "direct-ead")
    n_def = out["replications"]["test"]["n_defaults"]
    undefined = 1.0 - fx["n_defaults"] / n_def
    excluded = 1.0 - co["n_defaults"] / n_def
    f: list[dict[str, Any]] = []
    ok = fx["within_tolerance"]
    f.append({"id": "F-FIXED", "severity": "S4" if ok else "S2", "status": "accepted" if ok else "open",
              "evidence": ["lgd_ead.ccf_estimator_bias@" + bias_id("fixed-horizon", "none", "mean")],
              "title": T(f"At level {lvl} the fixed-horizon mean CCF is {fx['estimate']['value']:.3f} against the known {truth:.3f}, "
                         f"{_side(fx['bias'], 4)[0]} (tolerance {out['ccf_by_design']['tolerance']:.2f})",
                         f"En el nivel {lvl} el CCF medio a horizonte fijo es {_n(fx['estimate']['value'], 3)} frente al conocido {_n(truth, 3)}, "
                         f"{_side(fx['bias'], 4)[1]} (tolerancia {_n(out['ccf_by_design']['tolerance'], 2)})")})
    ok_p = fp["within_tolerance"]
    f.append({"id": "F-POOLED", "severity": "S4" if ok_p else "S3", "status": "accepted" if ok_p else "open",
              "evidence": ["lgd_ead.ccf_estimator_bias@" + bias_id("fixed-horizon", "none", "pooled")],
              "title": T(f"The pooled (ratio of sums) fixed-horizon CCF is {fp['estimate']['value']:.3f}, {_side(fp['bias'])[0]} the known value, "
                         "because the lines with most undrawn amount draw least",
                         f"El CCF agrupado (razón de sumas) a horizonte fijo es {_n(fp['estimate']['value'], 3)}, {_side(fp['bias'])[1]} del valor "
                         "conocido, porque las líneas con más monto no utilizado son las que menos usan")})
    f.append({"id": "F-HORIZON", "severity": "S2" if abs(co["bias"]) > 2 * TOLERANCE else "S3", "status": "open",
              "evidence": ["lgd_ead.ccf_estimator_bias@" + bias_id("cohort", "none", "pooled"),
                           "lgd_ead.ccf_estimator_bias@" + bias_id("variable-horizon", "none", "pooled")],
              "title": T(f"The cohort design reads the CCF {_side(co['bias'])[0]} and the variable-horizon design {_side(va['bias'])[0]} the known "
                         f"{truth:.3f}: a reference date nearer the default leaves less undrawn amount to be drawn",
                         f"El diseño de cohorte lee el CCF {_side(co['bias'])[1]} y el de horizonte variable {_side(va['bias'])[1]} del "
                         f"{_n(truth, 3)} conocido: una fecha de referencia más cercana al incumplimiento deja menos monto por usar")})
    f.append({"id": "F-TREATMENT", "severity": "S3", "status": "open",
              "evidence": ["lgd_ead.ccf_estimator_bias@" + bias_id("fixed-horizon", "floor-cap", "mean")],
              "title": T(f"Flooring at 0 and capping at 1 moves the fixed-horizon mean CCF to {fc['estimate']['value']:.3f} "
                         f"({fc['bias']:+.4f} against the known {truth:.3f}); {fx['share_above_one']:.1%} of the CCFs lie above 1 and "
                         f"{fx['share_below_zero']:.1%} below 0",
                         f"Poner piso en 0 y tope en 1 lleva el CCF medio a horizonte fijo a {_n(fc['estimate']['value'], 3)} "
                         f"({_signed(fc['bias'], 4, 'es')} frente al conocido {_n(truth, 3)}); {percent(fx['share_above_one'], 1, lang='es')} de los CCF están sobre 1 y "
                         f"{percent(fx['share_below_zero'], 1, lang='es')} bajo 0")})
    f.append({"id": "F-UNDEFINED", "severity": "S3", "status": "accepted", "evidence": ["design:undrawn-not-positive-is-undefined"],
              # the cohort design leaves out a first-month default (no reference date before it) and a line with no undrawn amount at
              # the cohort start: `excluded` is both, `first_month` the first only (R2b c10 B2: 30.7 % was called the first-month share)
              "title": T(f"{undefined:.1%} of the defaulters have no CCF at the fixed horizon (fully drawn or over their limit); in the cohort "
                         f"design {excluded:.1%} have none, {first_month:.1%} because they defaulted in the first month of their cohort; all are "
                         "left out of the estimates and counted",
                         f"{percent(undefined, 1, lang='es')} de los incumplidores no tiene CCF a horizonte fijo (línea totalmente usada o sobre su límite); "
                         f"en el diseño de cohorte {percent(excluded, 1, lang='es')} no lo tiene, {percent(first_month, 1, lang='es')} porque incumplió en "
                         "el primer mes de su cohorte; todos quedan fuera de las estimaciones y se cuentan")})
    f.append({"id": "F-DIRECT", "severity": "S3", "status": "open", "evidence": ["lgd_ead.ead_backtest_by_band@direct-ead"],
              "title": T(f"The direct EAD model clips {dm['n_clipped_above']:,} development lines whose EAD exceeds their limit, so it cannot "
                         "predict the exposure of an overlimit line",
                         f"El modelo de EAD directo recorta {number(dm['n_clipped_above'], 0, lang='es')} líneas de desarrollo cuya EAD supera su límite, por lo "
                         "que no puede predecir la exposición de una línea sobre su límite")})
    return f


def model_summaries(level: int, data: LevelData, rv: str) -> list[dict[str, Any]]:
    out = []
    for m in mdl.MODELS:
        fit = data.fits[m["id"]]
        pars: dict[str, Any] = {}
        if fit.ccf is not None:
            pars["ccf"] = {"value": fit.ccf, "unit": "share"}
        else:
            src = fit.logit if fit.logit is not None else fit.ead_fit
            for name, coef in zip(src.names, src.coefficients, strict=True):
                pars[f"coef_{name}"] = {"value": float(coef), "unit": "logit" if m["kind"] != "utilisation-change" else "share of limit"}
        out.append({"id": m["id"], "family": "lgd-ead", "rung": m["kind"], "title": MODEL_TITLE[m["id"]], "short_title": T(MODEL_SHORT[m["id"]], MODEL_SHORT_ES.get(m["id"], MODEL_SHORT[m["id"]])),
                    "engine": "riskvalidation.lgd_ead.ccf", "engine_version": rv, "licence": "MIT", "calibration": None,
                    "parameters": pars, "checkpoint_sha256": None})
    return out


def level_regime(level: int) -> dict[str, str]:
    return level_text(level)


# --- the models document ----------------------------------------------------------------------------------------------


def models_document(plan: dict[str, Any], data: dict[int, LevelData], rv: str) -> dict[str, Any]:
    base = data[0]
    direct_fit = base.fits["direct-ead"].ead_fit
    ead_models = []
    for m in mdl.MODELS:
        below = above = None
        if m["kind"] == "direct-ead":
            below, above = int(direct_fit.extras["n_clipped_below"]), int(direct_fit.extras["n_clipped_above"])
        ead_models.append({"model_id": m["id"], "kind": m["kind"], "design": m["design"], "treatment": m["treatment"],
                           "covariates": mdl.covariates(m), "n_clipped_below": below, "n_clipped_above": above})
    levels = [{"level": x["level"],
               "label": T(f"Level {x['level']}: factor {x['factor']:g}, window {x['window']} months, known CCF {params.known_ccf(x['level']):.4f}",
                          f"Nivel {x['level']}: factor {_g(x['factor'], 'es')}, ventana de {x['window']} meses, CCF conocido {number(params.known_ccf(x['level']), 4, lang='es')}"),
               "acceleration_factor": float(x["factor"]), "acceleration_window_months": int(x["window"])} for x in LEVELS]
    gen = generator_block(0)
    fit = {
        "currency": PARAMS["currency"], "convention": CONVENTION, "generator": gen, "marginals": calibration.marginals(), "levels": levels,
        "replications_plan": {"development_seeds": list(plan["development_seeds"]), "test_seeds": list(plan["test_seeds"]),
                              "n_facilities": plan["n_facilities"]},
        "designs": [
            {"design": "fixed-horizon", "horizon_months": 12, "n_reference": 1, "step_months": None, "label": DESIGN_LABEL["fixed-horizon"]},
            {"design": "cohort", "horizon_months": None, "n_reference": 1, "step_months": 12, "label": DESIGN_LABEL["cohort"]},
            {"design": "variable-horizon", "horizon_months": 12, "n_reference": 4, "step_months": 3, "label": DESIGN_LABEL["variable-horizon"]}],
        "treatments": list(est.TREATMENTS), "ead_models": ead_models, "small_undrawn": small_undrawn_block(base),
        "floors": {"off_balance_share": 0.5, "reference": "CRE32.36, CRE32.64, CRE32.33; dossier 01 section A.5",
                   "supervisory_ccfs": [
                       {"item": item, "ccf": float(floors.supervisory_ccf(item)), "reference": ref} for item, ref in (
                           ("direct-credit-substitutes", "CRE20.94 to CRE20.101"),
                           ("nifs-rufs-transaction-related-contingents", "CRE20.94 to CRE20.101"),
                           ("commitments", "CRE20.98"),
                           ("short-term-self-liquidating-trade-letters-of-credit", "CRE20.94 to CRE20.101"),
                           ("unconditionally-cancellable", "CRE20.100"))]}}
    records = []
    for m in mdl.MODELS:
        fit0 = base.fits[m["id"]]
        by_level = []
        for lv, d in sorted(data.items()):
            f = d.fits[m["id"]]
            if f.ccf is not None:
                by_level.append({"level": lv, "ccf": f.ccf})
            else:
                src = f.logit if f.logit is not None else f.ead_fit
                entry: dict[str, Any] = {"level": lv, "names": list(src.names), "coefficients": [float(c) for c in src.coefficients]}
                if f.ead_fit is not None and m["kind"] == "direct-ead":
                    entry["n_clipped_below"] = int(f.ead_fit.extras["n_clipped_below"])
                    entry["n_clipped_above"] = int(f.ead_fit.extras["n_clipped_above"])
                entry["fitted_on_every"] = f.thin
                by_level.append(entry)
        pars = model_summaries(0, base, rv)[[x["id"] for x in mdl.MODELS].index(m["id"])]
        records.append({**pars, "details": {"design": m["design"], "treatment": m["treatment"],
                                            "aggregator": mdl.CCF_ESTIMATOR if fit0.ccf is not None else None,
                                            "fitted_on": "the development replications of each level, pooled", "by_level": by_level}})
    return {"fit_id": "generator", "model": records, "fit": fit}
