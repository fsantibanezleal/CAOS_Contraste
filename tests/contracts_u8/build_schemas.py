"""Builds the four U8-S schema files (docs/contracts/schemas/c11 and c13).

Run: ``python tests/contracts_u8/build_schemas.py``. Deterministic, standard library only. The schema files are the
contract and are committed; this script is the compact source they are written from, so a name two files of one case
share has one definition (the generator of the TypeScript types fails on a clash). Conventions of docs/contracts/catalog.md:
one folder per case, a ``case_id`` const, ``outputs.kind`` on every variant, case-prefixed ``$defs``, the
``variant-envelope`` composition with ``unevaluatedProperties: false``, every object closed, nothing optional.

Document shapes transcribe dossier 05 sections A and B, dossier 01 D.4 (MAR32.9 Table 1, MAR32.18 to 19, MAR32.36 to 42)
and the views of plans/contraste/units/U8-sizing.md; a value a producer may lack is nullable with its reason, never a number.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "docs" / "contracts" / "schemas"
BASE = "https://contraste.fasl-work.com/contracts/"
TXT = {"$ref": "../common/text.schema.json"}


def Ob(props: dict, desc: str | None = None) -> dict:
    d: dict = {"type": "object", "additionalProperties": False, "required": list(props), "properties": props}
    if desc:
        d["description"] = desc
    return d


def A(items: dict, minimum: int | None = None, desc: str | None = None, maximum: int | None = None) -> dict:
    d: dict = {"type": "array", "items": items}
    if minimum is not None:
        d["minItems"] = minimum
    if maximum is not None:
        d["maxItems"] = maximum
    if desc:
        d["description"] = desc
    return d


def R(name: str) -> dict:
    return {"$ref": f"#/$defs/{name}"}


def nullable(x: dict, desc: str | None = None) -> dict:
    d: dict = {"anyOf": [x, {"type": "null"}]}
    if desc:
        d["description"] = desc
    return d


def S(desc: str | None = None, **kw) -> dict:
    d: dict = {"type": "string", **kw}
    if desc:
        d["description"] = desc
    return d


def Int(minimum: int | None = None, maximum: int | None = None, desc: str | None = None) -> dict:
    d: dict = {"type": "integer"}
    if minimum is not None:
        d["minimum"] = minimum
    if maximum is not None:
        d["maximum"] = maximum
    if desc:
        d["description"] = desc
    return d


def N(desc: str | None = None, **kw) -> dict:
    d: dict = {"type": "number", **kw}
    if desc:
        d["description"] = desc
    return d


def E(*values: str) -> dict:
    return {"type": "string", "enum": list(values)}


def EN(*values: float) -> dict:
    return {"type": "number", "enum": list(values)}


def C(value) -> dict:
    return {"const": value}


NULL = {"type": "null"}
B = {"type": "boolean"}
DATE = S(pattern=r"^\d{4}-\d{2}-\d{2}$")
PRE2007 = S("A date before 2007-01-01: the hyperparameters are fixed on a pre-2007 span (SDD C11).",
            pattern=r"^(19\d{2}|200[0-6])-\d{2}-\d{2}$")
UNIT = N("A share or an observed rate in [0, 1].", minimum=0, maximum=1)
PROB = N("A probability in [0, 1].", minimum=0, maximum=1)
LOSS_POS = N("A positive loss number (document convention) as a decimal of the portfolio value.", exclusiveMinimum=0)
NAME_MAP = {
    "type": "object",
    "additionalProperties": False,
    "required": ["name", "value", "unit"],
    "properties": {"name": S(), "value": N(), "unit": S()},
}
NONEMPTY = S(minLength=1)
ALPHA = EN(0.01, 0.025)


def couple(ob: dict, *groups: list[dict]) -> dict:
    """Adds independent groups of mutually exclusive alternatives to a closed object. Each alternative narrows properties
    the object already declares (so ``additionalProperties: false`` still holds); exactly one alternative of every group
    must match."""
    ob["allOf"] = [{"oneOf": [{"properties": alt} for alt in group]} for group in groups]
    return ob


def reachable(root: str, defs: dict) -> dict:
    seen: dict = {}
    todo = [root]

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "$ref" and isinstance(v, str) and v.startswith("#/$defs/"):
                    todo.append(v[len("#/$defs/"):])
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen[name] = defs[name]
        walk(defs[name])
    return {k: seen[k] for k in defs if k in seen}


# A not_evaluated test row carries no number and states its reason (engine contract, Conventions). The shared
# common/test-result schema is outside U8-S's write scope, so the rule is composed here on the variant's `tests`; the
# integrator can move it to common/test-result as a contract bump.
NOT_EVALUATED_RULE = {
    "properties": {"tests": {"items": {
        "if": {"properties": {"light": {"const": "not_evaluated"}}, "required": ["light"]},
        "then": {"properties": {"statistic": NULL, "p_value": NULL, "metric": NULL,
                                "notes": {"type": "string", "minLength": 1}}},
    }}},
}


def variant_schema(case: str, ref: str, kind: str, title: str, desc: str, root: str, defs: dict) -> None:
    doc = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{BASE}{case.lower()}/{ref}.schema.json",
        "title": title,
        "description": desc,
        "allOf": [
            {"$ref": "../common/variant-envelope.schema.json"},
            {"properties": {"case_id": {"const": case},
                            "outputs": {"$ref": f"#/$defs/{root}", "properties": {"kind": {"const": kind}}}},
             "required": ["case_id", "outputs"]},
            NOT_EVALUATED_RULE,
        ],
        "unevaluatedProperties": False,
        "$defs": reachable(root, defs),
    }
    write(case, f"{ref}.schema.json", doc)


def models_schema(case: str, title: str, desc: str, root: str, defs: dict) -> None:
    doc = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{BASE}{case.lower()}/models.schema.json",
        "title": title,
        "description": desc,
        "allOf": [
            {"$ref": "../common/models-envelope.schema.json"},
            {"properties": {"case_id": {"const": case}, "fit": {"$ref": f"#/$defs/{root}"}},
             "required": ["case_id", "fit"]},
        ],
        "unevaluatedProperties": False,
        "$defs": reachable(root, defs),
    }
    write(case, "models.schema.json", doc)


def write(case: str, name: str, doc: dict) -> None:
    path = SCHEMAS / case.lower() / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def sign_convention(prefix: str, what: str) -> dict:
    return Ob({
        "engine_convention": C("return-negative"),
        "document_convention": C("positive-loss"),
        "definition": {"allOf": [TXT, {"properties": {"en": {"minLength": 1}, "es": {"minLength": 1}}}]},
    }, f"The sign convention, a required field of every {what} document (dossier 05 A.0): the engine stores the return "
       "convention (VaR and ES negative at the tail level alpha 0.01 or 0.025, needed by the FZ0 loss) and the document stores "
       "positive loss numbers, the conversion made once at the reporting layer. The definition states both in words.")


# ---------------------------------------------------------------------------------------------------- C11

D11: dict = {}


def build_c11() -> None:
    d = D11
    d["c11SignConvention"] = sign_convention("c11", "C11")
    d["c11Level"] = Ob({"alpha": ALPHA}, "A tail level of the return convention: 0.01 (99 percent VaR, the Basel level) or 0.025 "
                                         "(97.5 percent, the FRTB ES level).")
    d["c11Window"] = Ob({
        "window_id": E("equity-2007-09", "equity-2020", "rates-2022", "fx-2008", "mixed-2023", "calm-2004-06"),
        "asset_class": E("equity", "rates", "fx", "mixed"),
        "title": TXT,
        "start_date": DATE,
        "end_date": DATE,
        "n_forecast_days": Int(1),
    }, "One of the six windows of SDD C11; the variant id is the window id.")
    d["c11Component"] = Ob({
        "series_id": S(), "label": TXT,
        "source_class": E("derived-only", "mirror-allowed"),
        "weight": N(exclusiveMinimum=0, maximum=1),
        "transform": S("How the series becomes a return of the portfolio (a log return, a duration times a yield change)."),
    }, "A component of the window's stated portfolio and the licence class of its source (dossier 08 C.5, C.2, C.8).")
    d["c11Portfolio"] = Ob({
        "description": TXT,
        "value_unit": C("decimal-of-portfolio-value"),
        "currency": S("ISO 4217 code of the portfolio.", pattern="^[A-Z]{3}$"),
        "weighting": E("constant-weights-daily-rebalanced", "buy-and-hold"),
        "components": A(R("c11Component"), 1),
    }, "The portfolio stated for the window; returns and losses are decimals of its value.")
    d["c11MissingDays"] = Ob({
        "count": Int(0),
        "dates": A(DATE),
        "treatment": C("skipped-not-filled"),
    }, "A day missing from a public series (a holiday, a gap) is skipped in the rolling window and counted here, never filled.")
    d["c11DataStatus"] = Ob({
        "first_observation": DATE, "last_observation": DATE, "n_observed_days": Int(1),
        "missing_days": R("c11MissingDays"),
    })
    d["c11Realised"] = couple(
        Ob({"status": E("included", "withheld-derived-only"),
            "loss": nullable(A(N(), 1)),
            "reason": nullable(S())},
           "The realised loss per forecast day (positive number, a decimal of the portfolio value). Withheld, with its reason, "
           "when a component of the portfolio is derived-only (dossier 08 C.5: only model outputs are committed)."),
        [{"status": C("included"), "loss": A(N(), 1), "reason": NULL},
         {"status": C("withheld-derived-only"), "loss": NULL, "reason": NONEMPTY}])
    d["c11Grid"] = Ob({
        "scheme": C("rolling"),
        "estimation_window_days": Int(1, desc="The maximum look-back, in observed days; each rung's own window is in the models document."),
        "dates": A(DATE, 1, "The forecast days, strictly increasing, missing days skipped."),
        "estimation_start": A(DATE, 1, "First day of the estimation window of each forecast day."),
        "estimation_end": A(DATE, 1, "Last day of the estimation window of each forecast day: strictly before the forecast day "
                                      "(the forecast for day t uses data to t-1; a producer check, since a date comparison is not "
                                      "a JSON Schema rule)."),
        "realised_loss": R("c11Realised"),
    }, "The forecast grid shared by every model: dates once, the estimation window of each day, the realised losses.")
    d["c11Span"] = Ob({"start": PRE2007, "end": PRE2007},
                      "The span on which the hyperparameters were fixed: it ends before 2007 and before the window it serves.")
    d["c11Hyperparameters"] = Ob({
        "fixed_on": R("c11Span"),
        "tuned_on_test_window": C(False),
        "estimation_window_days": Int(1),
        "ewma_lambda": N(exclusiveMinimum=0, exclusiveMaximum=1),
        "age_weight_lambda": N(exclusiveMinimum=0, exclusiveMaximum=1),
        "evt_threshold_fraction": N(exclusiveMinimum=0, exclusiveMaximum=1),
        "garch_refit_every_days": Int(1),
        "others": A(NAME_MAP),
    }, "The hyperparameters (window length, lambda, EVT threshold fraction) fixed on the span, never tuned on a test window.")
    d["c11TrafficLight"] = couple(
        Ob({"window_days": C(250), "n_windows": Int(0),
            "max_rolling_exceedances": nullable(Int(0)), "final_rolling_exceedances": nullable(Int(0)),
            "final_zone": E("green", "amber", "red", "not_evaluated"),
            "days_green": nullable(Int(0)), "days_amber": nullable(Int(0)), "days_red": nullable(Int(0)),
            "reason": nullable(S())},
           "The Basel traffic light at the 99 percent level over rolling 250-day windows (MAR32.9): the zone of each complete "
           "window and the days spent in each zone. With fewer than 250 forecast days it is not evaluated, with its reason."),
        [{"n_windows": Int(1), "max_rolling_exceedances": Int(0), "final_rolling_exceedances": Int(0),
          "final_zone": E("green", "amber", "red"), "days_green": Int(0), "days_amber": Int(0), "days_red": Int(0),
          "reason": NULL},
         {"final_zone": C("not_evaluated"), "max_rolling_exceedances": NULL, "final_rolling_exceedances": NULL,
          "days_green": NULL, "days_amber": NULL, "days_red": NULL, "reason": NONEMPTY}])
    d["c11LevelResult"] = couple(
        Ob({
            "alpha": ALPHA,
            "var": A(LOSS_POS, 1, "One-step VaR forecast per grid day, a positive loss."),
            "es": A(nullable(LOSS_POS), 1, "One-step ES forecast per grid day, a positive loss not below the VaR; null on a day "
                                           "the ES is undefined (conditional EVT with xi at or above 1) or for a model that forecasts no ES."),
            "es_status": E("forecast", "undefined-on-days", "not-forecast"),
            "es_undefined_days": A(Int(0), desc="Indices into the grid of the days the ES is undefined."),
            "exceedance_days": A(Int(0), desc="Indices into the grid of the days the loss exceeded the VaR."),
            "n_scored": Int(1),
            "n_exceedances": Int(0),
            "expected_exceedances": N(minimum=0, desc="alpha times n_scored."),
            "n_fz0": Int(0, desc="Days with both VaR and ES defined: the sample of the FZ0 average."),
            "fz0_mean": nullable(N(), "Average FZ0 loss (dossier 05 A.1) over the n_fz0 days; null when no day has an ES."),
            "fz0_reason": nullable(S()),
            "tick_loss_mean": N(minimum=0, desc="Average tick loss of the VaR over the n_scored days."),
            "traffic_light": nullable(R("c11TrafficLight"), "At alpha 0.01 only; null at 0.025."),
            "test_ids": A(S(pattern=r"^market\."), 1, "The test rows of this model and level (segment alpha=<alpha>)."),
        }, "One model at one tail level: its forecasts, exceedances, scores and traffic light."),
        [{"es_status": C("forecast"), "es_undefined_days": A(Int(0), maximum=0)},
         {"es_status": C("undefined-on-days"), "es_undefined_days": A(Int(0), 1)},
         {"es_status": C("not-forecast"), "es_undefined_days": A(Int(0), maximum=0)}],
        [{"fz0_mean": N(), "fz0_reason": NULL}, {"fz0_mean": NULL, "fz0_reason": NONEMPTY}],
        [{"alpha": C(0.01), "traffic_light": R("c11TrafficLight")}, {"alpha": C(0.025), "traffic_light": NULL}])
    d["c11ModelOutput"] = Ob({
        "model_id": S(),
        "rung": S(pattern=r"^R([1-9]|10)$"),
        "eligible": B,
        "failed_gates": A(S(pattern=r"^market\.")),
        "by_level": A(R("c11LevelResult"), 1),
    }, "One model of the ladder in this window; eligible when no eligibility-gate row is red (the traditional back-tests of "
       "dossier 05 'Champion selection rule').")
    d["c11Champion"] = couple(
        Ob({"alpha": ALPHA, "model_id": nullable(S()), "reason": nullable(S())},
           "The champion at a level: the lowest average FZ0 among the eligible models with a score; null, with its reason, "
           "when there is none."),
        [{"model_id": S(), "reason": NULL}, {"model_id": NULL, "reason": NONEMPTY}])
    d["c11DmRow"] = couple(
        Ob({
            "model_id": S(), "versus": S(), "alpha": ALPHA,
            "loss": E("fz0", "tick"),
            "mean_diff": nullable(N(), "Mean loss differential, model minus champion, on the common sample: negative is better."),
            "dm_statistic": nullable(N()),
            "p_value": nullable(PROB),
            "hac_lags": Int(0),
            "n_common": nullable(Int(1), "Days where every compared forecast is defined."),
            "direction": E("better", "worse", "indistinguishable", "not-evaluated"),
            "not_evaluated_reason": nullable(S()),
        }, "A Diebold-Mariano comparison of one model against the champion (dossier 05 B.6) under FZ0 or the tick loss."),
        [{"mean_diff": N(), "dm_statistic": N(), "p_value": PROB, "n_common": Int(1),
          "direction": E("better", "worse", "indistinguishable"), "not_evaluated_reason": NULL},
         {"mean_diff": NULL, "dm_statistic": NULL, "p_value": NULL, "n_common": NULL,
          "direction": C("not-evaluated"), "not_evaluated_reason": NONEMPTY}])
    d["c11McsMember"] = Ob({"model_id": S(), "in_set": B, "p_value": PROB})
    d["c11McsSet"] = Ob({
        "alpha": ALPHA,
        "loss": C("fz0"),
        "statistic": E("Tmax", "TR"),
        "confidence": N(exclusiveMinimum=0, exclusiveMaximum=1),
        "n_bootstrap": Int(1),
        "block_length": Int(1),
        "members": A(R("c11McsMember"), 1),
        "n_in_set": Int(1),
    }, "The model confidence set on FZ0 at one level (Hansen, Lunde and Nason 2011; dossier 05 B.6).")
    d["c11Comparison"] = Ob({
        "significance": N(exclusiveMinimum=0, exclusiveMaximum=1),
        "hac_kernel": C("bartlett"),
        "champions": A(R("c11Champion"), 1),
        "dm": A(R("c11DmRow")),
        "mcs": A(R("c11McsSet"), 1),
    }, "Eligibility first, then the comparative back-test of Nolde and Ziegel: DM against the champion and the MCS.")
    d["c11Histogram"] = Ob({"edges": A(N(), 2), "counts": A(Int(0), 1)})
    d["c11EsNull"] = Ob({
        "model_id": S(), "alpha": ALPHA,
        "statistic": C("Z2"),
        "realised": N(),
        "critical_5pct": N(desc="Simulated per model: Z2 at the 5 percent quantile of the null (yellow)."),
        "critical_0_01pct": N(desc="Simulated per model: Z2 at the 0.01 percent quantile of the null (red)."),
        "n_draws": Int(1),
        "p_value": PROB,
        "histogram": R("c11Histogram"),
    }, "The simulated null distribution of the Acerbi-Szekely Z2 for one model, with the realised statistic (dossier 05 B.5).")
    d["c11Outputs"] = Ob({
        "kind": C("window"),
        "window": R("c11Window"),
        "sign_convention": R("c11SignConvention"),
        "levels": A(R("c11Level"), 1),
        "portfolio": R("c11Portfolio"),
        "data_status": R("c11DataStatus"),
        "grid": R("c11Grid"),
        "hyperparameters": R("c11Hyperparameters"),
        "models": A(R("c11ModelOutput"), 1),
        "comparison": R("c11Comparison"),
        "es_backtests": A(R("c11EsNull")),
    }, "The C11 window document: market VaR and ES forecasts of the ladder, strictly rolling, and their back-tests.")

    # --- models
    d["c11WindowPlan"] = Ob({
        "window_id": E("equity-2007-09", "equity-2020", "rates-2022", "fx-2008", "mixed-2023", "calm-2004-06"),
        "asset_class": E("equity", "rates", "fx", "mixed"),
        "start_date": DATE, "end_date": DATE,
        "fixed_on": R("c11Span"),
    }, "A window and the span on which its hyperparameters were fixed (before the window starts and before 2007).")
    d["c11Parameter"] = Ob({"name": S(), "min": N(), "median": N(), "max": N(), "unit": S()},
                           "A fitted parameter across the refits of a window: minimum, median and maximum.")
    d["c11RungWindowFit"] = Ob({
        "window_id": S(), "n_refits": Int(0), "n_convergence_failures": Int(0), "parameters": A(R("c11Parameter")),
    })
    d["c11Rung"] = couple(
        Ob({
            "model_id": S(), "rung": S(pattern=r"^R([1-9]|10)$"),
            "title": TXT, "family": S(), "source": S("The primary source of the method (dossier 05 A.2)."),
            "status": E("fitted", "challenger-not-run"),
            "not_run_reason": nullable(S()),
            "innovation": E("none", "normal", "student-t", "skew-t", "gpd-tail", "empirical"),
            "estimation_window_days": nullable(Int(1)),
            "refit_every_days": nullable(Int(1)),
            "forecasts_es": B,
            "es_method": S(),
            "window_fits": A(R("c11RungWindowFit")),
        }, "A rung of the market ladder (dossier 05 'Method ladders': rungs 1 to 10; rung 10 is a challenger only)."),
        [{"status": C("fitted"), "not_run_reason": NULL},
         {"status": C("challenger-not-run"), "not_run_reason": NONEMPTY, "window_fits": A(R("c11RungWindowFit"), maximum=0)}])
    d["c11TrafficRow"] = Ob({
        "exceptions": Int(0, 10, "The number of exceptions in 250 days; 10 stands for ten or more."),
        "zone": E("green", "amber", "red"),
        "frtb_multiplier": N(desc="The backtesting-dependent multiplier m_c of MAR32.9 Table 1."),
        "us_multiplier": N(desc="The US multiplication factor of 12 CFR 217.204 Table 1 (dossier 05 B.4)."),
        "cumulative_probability_pct": N(desc="P(X <= exceptions), X ~ Bin(250, 0.01), in percent (MAR32.9 Table 1)."),
    })
    d["c11TrafficTable"] = Ob({
        "window_days": C(250), "confidence": C(0.99), "reference": S(),
        "rows": A(R("c11TrafficRow"), 11, maximum=11),
    }, "MAR32.9 Table 1 with the US factors (dossier 01 D.4, dossier 05 B.4); the reference for every traffic-light band.")
    d["c11EsReference"] = Ob({
        "statistic": C("Z2"), "n_days": C(250), "alpha": C(0.025), "yellow": C(-0.7), "red": C(-1.8), "status": TXT,
    }, "The published reference points of Acerbi and Szekely for Z2 (dossier 05 B.5): a reference, never a regulatory "
       "threshold; each model's own simulated critical values are in the outputs.")
    d["c11Scoring"] = Ob({
        "fz0_formula": S(), "tick_formula": S(), "hac_kernel": C("bartlett"),
        "mcs_confidence": N(exclusiveMinimum=0, exclusiveMaximum=1), "mcs_statistic": E("Tmax", "TR"),
        "selection_rule": TXT,
    })
    d["c11Gate"] = Ob({"test_id": S(pattern=r"^market\."), "rule": TXT},
                      "An eligibility gate: the model is ineligible when the row of this test is red at any level.")
    d["c11Source"] = Ob({
        "series_id": S(), "title": TXT, "source_class": E("derived-only", "mirror-allowed"), "url": S(), "licence_note": TXT,
    })
    d["c11Fit"] = Ob({
        "sign_convention": R("c11SignConvention"),
        "levels": A(R("c11Level"), 1),
        "windows": A(R("c11WindowPlan"), 6, maximum=6),
        "ladder": A(R("c11Rung"), 1),
        "traffic_light": R("c11TrafficTable"),
        "es_reference": R("c11EsReference"),
        "scoring": R("c11Scoring"),
        "eligibility_gates": A(R("c11Gate"), 1),
        "data_sources": A(R("c11Source"), 1),
    }, "The C11 models document: the six windows, the ladder, the bands and the reference points the views draw.")

    variant_schema("C11", "variant-window", "window", "C11 window variant",
                   "Catalog row c11-outputs 1.0.0: one window of the market VaR and ES back-testing case (outputs.kind window), "
                   "strictly rolling, on public daily series.", "c11Outputs", d)
    models_schema("C11", "C11 models",
                  "Catalog row c11-models 1.0.0: the C11 models artifact (windows and spans, the ladder with its fitted "
                  "parameters, the Basel bands, the ES reference points).", "c11Fit", d)


# ---------------------------------------------------------------------------------------------------- C13

D13: dict = {}
DEFS6 = ("none", "missing-basis", "stale-volatility", "wrong-correlation", "omitted-factor", "time-misalignment")


def build_c13() -> None:
    d = D13
    d["c13SignConvention"] = sign_convention("c13", "C13")
    d["c13Known"] = couple(
        Ob({
            "deficiency_id": E(*DEFS6),
            "planted": B,
            "mechanism": TXT,
            "parameters": A(NAME_MAP, desc="The planted severity, with units."),
            "intended_to_fail": E("none", "spearman", "ks", "either"),
        }, "The deficiency the generator planted in the desk's risk model: the known truth of the case, a required field."),
        [{"deficiency_id": C("none"), "planted": C(False), "intended_to_fail": C("none")},
         {"deficiency_id": E(*DEFS6[1:]), "planted": C(True), "intended_to_fail": E("spearman", "ks", "either")}])
    d["c13Generator"] = Ob({
        "name": S(), "n_risk_factors": Int(1),
        "pnl_unit": C("decimal-of-desk-notional"),
        "window_days": C(250),
        "n_replications": Int(1),
        "seed_base": Int(0),
        "seed_rule": C("seed_base+replication_index"),
        "notice": TXT,
    }, "The desk P&L generator with a known risk model; synthetic, labelled so on every view.")
    d["c13PnlSummary"] = Ob({
        "series": E("HPL", "RTPL"),
        "mean": N(), "sd": N(minimum=0), "skewness": N(), "excess_kurtosis": N(), "min": N(), "max": N(),
    }, "A summary of the desk's hypothetical (HPL) or risk-theoretical (RTPL) P&L, median across replications, decimals of the notional.")
    d["c13Dist"] = Ob({
        "mean": N(), "sd": N(minimum=0), "q05": N(), "q50": N(), "q95": N(), "min": N(), "max": N(),
    }, "The distribution of a statistic across the replications.")
    d["c13ZoneCounts"] = Ob({"green": Int(0), "amber": Int(0), "red": Int(0)})
    d["c13Zones"] = Ob({
        "n": Int(1), "overall": R("c13ZoneCounts"), "spearman": R("c13ZoneCounts"), "ks": R("c13ZoneCounts"),
    }, "The PLA zone counts across replications: of the joint MAR32.42 zone, of the Spearman statistic alone and of the KS statistic alone.")
    d["c13PlaThresholds"] = Ob({
        "spearman_green": C(0.8), "spearman_red": C(0.7), "ks_green": C(0.09), "ks_red": C(0.12),
        "ecdf_step": C(0.004), "window_days": C(250), "reference": C("MAR32.42"),
    }, "The zone boundaries of MAR32.42 and the ECDF step of MAR32.39 to 41 (dossier 01 D.4), transcribed.")
    d["c13Pla"] = Ob({
        "thresholds": R("c13PlaThresholds"), "spearman": R("c13Dist"), "ks": R("c13Dist"), "zones": R("c13Zones"),
    })
    d["c13Example"] = Ob({
        "replication_index": Int(0), "seed": Int(0),
        "hpl": A(N(), 250, "250 daily HPL values, decimals of the notional.", 250),
        "rtpl": A(N(), 250, "250 daily RTPL values, decimals of the notional.", 250),
        "spearman": N(minimum=-1, maximum=1), "ks": N(minimum=0, maximum=1),
        "zone": E("green", "amber", "red"),
    }, "One replication kept whole, for the rank scatter and the two ECDFs with the KS gap.")
    d["c13DeskLevel"] = couple(
        Ob({
            "alpha": ALPHA, "basis": E("APL", "HPL"),
            "limit_exceptions": Int(0), "n_days": C(250),
            "exceptions": R("c13Dist"),
            "n_within_limit": Int(0), "n_over_limit": Int(0), "share_over_limit": UNIT,
        }, "Desk back-testing at one level (MAR32.18 to 19): the exception count over 250 days against the limit "
           "(more than 12 at 99 percent or 30 at 97.5 percent moves the desk to the standardised approach)."),
        [{"alpha": C(0.01), "limit_exceptions": C(12)}, {"alpha": C(0.025), "limit_exceptions": C(30)}])
    d["c13Detection"] = Ob({
        "role": E("size", "power"),
        "rule": TXT,
        "n_replications": Int(1),
        "n_amber_or_red": Int(0), "n_red": Int(0),
        "share_amber_or_red": UNIT, "share_red": UNIT,
        "mc_se": N(minimum=0, description="The Monte Carlo standard error of share_amber_or_red."),
        "ci_low": UNIT, "ci_high": UNIT,
        "by_test": Ob({"spearman_flagged": Int(0), "ks_flagged": Int(0), "desk_backtest_flagged": Int(0)}),
        "intended_test_flagged": nullable(Int(0), "Replications where the intended test flagged the desk; null when none was planted."),
    }, "The rate at which the PLA catches the planted deficiency: its power; with no deficiency planted it is the false-alarm rate, the size.")
    d["c13Outputs"] = Ob({
        "kind": C("deficiency"),
        "known_deficiency": R("c13Known"),
        "sign_convention": R("c13SignConvention"),
        "generator": R("c13Generator"),
        "pnl_summary": A(R("c13PnlSummary"), 2, maximum=2),
        "pla": R("c13Pla"),
        "example": R("c13Example"),
        "desk_backtest": A(R("c13DeskLevel"), 2, maximum=2),
        "detection": R("c13Detection"),
    }, "The C13 deficiency document: the PLA and desk back-test of a desk whose model has one known planted deficiency.")
    d["c13Outputs"]["allOf"] = [{
        "if": {"properties": {"known_deficiency": {"properties": {"deficiency_id": {"const": "none"}}, "required": ["deficiency_id"]}},
               "required": ["known_deficiency"]},
        "then": {"properties": {"detection": {"properties": {"role": {"const": "size"}}}}},
        "else": {"properties": {"detection": {"properties": {"role": {"const": "power"}}}}},
    }]

    # --- models
    d["c13GeneratorSpec"] = Ob({
        "name": S(), "true_risk_model": TXT, "parameters": A(NAME_MAP),
        "pnl_unit": C("decimal-of-desk-notional"), "window_days": C(250), "seed_rule": C("seed_base+replication_index"),
        "notice": TXT,
    }, "The desk P&L generator with a known risk model.")
    d["c13DeficiencyPlan"] = Ob({
        "deficiency_id": E(*DEFS6), "planted": B, "mechanism": TXT, "parameters": A(NAME_MAP),
        "intended_to_fail": E("none", "spearman", "ks", "either"),
    }, "One planted deficiency and how the generator plants it.")
    d["c13DeskLimit"] = Ob({"alpha": ALPHA, "limit_exceptions": Int(0), "reference": S()})
    d["c13ReplicationPlan"] = Ob({"n_replications": Int(1), "seed_base": Int(0), "seed_rule": C("seed_base+replication_index")})
    d["c13Fit"] = Ob({
        "sign_convention": R("c13SignConvention"),
        "generator": R("c13GeneratorSpec"),
        "deficiencies": A(R("c13DeficiencyPlan"), 6, maximum=6),
        "pla_thresholds": R("c13PlaThresholds"),
        "desk_limits": A(R("c13DeskLimit"), 2, maximum=2),
        "replication_plan": R("c13ReplicationPlan"),
    }, "The C13 models document: the generator, the six deficiencies it plants, the PLA and desk limits.")

    variant_schema("C13", "variant-deficiency", "deficiency", "C13 deficiency variant",
                   "Catalog row c13-outputs 1.0.0: one planted model deficiency of the FRTB desk eligibility case "
                   "(outputs.kind deficiency), on a generator whose truth is known.", "c13Outputs", d)
    models_schema("C13", "C13 models",
                  "Catalog row c13-models 1.0.0: the C13 models artifact (generator, the six planted deficiencies, the PLA "
                  "thresholds, the desk limits).", "c13Fit", d)


if __name__ == "__main__":
    build_c11()
    build_c13()
    print("wrote", sorted(str(p.relative_to(SCHEMAS)) for p in SCHEMAS.glob("c1[13]/*.schema.json")))
