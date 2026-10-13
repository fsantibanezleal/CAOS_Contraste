"""Builds the two U12-S schema files (docs/contracts/schemas/c17).

Run: ``python tests/contracts_u12/build_schemas.py``. Deterministic, standard library only. The schema files are the
contract and are committed; this script is the compact source they are written from, so a name two files of one case share
has one definition (the generator of the TypeScript types fails on a clash). Conventions of docs/contracts/catalog.md: one
folder per case, a ``case_id`` const, ``outputs.kind`` on the variant, case-prefixed ``$defs``, the ``variant-envelope``
composition with ``unevaluatedProperties: false``, every object closed, nothing optional.

Variants of C17 (decision of U12-S): one variant per tail index (0.6, 0.8, 0.96, 1.1), ``outputs.kind`` ``tail-index``. The
16 cells of the SDD (5 or 10 years x tail index x collection threshold 10,000 or 20,000) are the 4 tail-index variants x 4
cells (years x threshold) inside each. Why: the tail index decides the methodological status of a document (a tail index of 1
or more has no mean, so mean-based quantities are null with a reason), it is the axis the views answer ("how unstable as the
tail index nears 1"), and a cell carries replication summaries (percentiles over 1,000 independent histories), never the
histories, so a variant stays a few tens of kilobytes. Years and threshold are rows because the views compare 5 against 10
years and 10,000 against 20,000 side by side on one true distribution.
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


def A(items: dict, minimum: int | None = None, maximum: int | None = None, desc: str | None = None) -> dict:
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


B = {"type": "boolean"}
CUR = {"const": "EUR", "description": "ISO 4217 code of the money fields of this block: C17 is in EUR throughout (the LDCE calibration is in EUR)."}
UNIT = N("A share in [0, 1].", minimum=0, maximum=1)
POS = N(exclusiveMinimum=0)
MONEY = N("Money in EUR (the `currency` of the enclosing block).", minimum=0)
LEVEL = {"const": 0.999, "description": "The quantile level of C17: the 99.9 percent annual loss quantile, as a decimal."}


def one_of(ob: dict, *alternatives: dict) -> dict:
    """Adds a ``oneOf`` of coupled-field alternatives to a closed object: each alternative narrows properties the object
    already declares, so ``additionalProperties: false`` still holds."""
    ob["oneOf"] = [{"properties": a} for a in alternatives]
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
# common/test-result schema is outside U12-S's write scope, so the rule is composed here on the variant's `tests`.
NOT_EVALUATED_RULE = {
    "properties": {"tests": {"items": {
        "if": {"properties": {"light": {"const": "not_evaluated"}}, "required": ["light"]},
        "then": {"properties": {"statistic": {"type": "null"}, "p_value": {"type": "null"}, "metric": {"type": "null"},
                                "notes": {"type": "string", "minLength": 1}}},
    }}},
}
TRUTH_STATUS = {"properties": {"provenance": {"properties": {"truth_status": {"const": "synthetic-known-truth"}}}},
                "required": ["provenance"]}

# The tail index of 1 or more has no mean (dossier 05 F.4, Degen 2010; Chavez-Demoulin et al. 2006): the flag, the true mean
# and the mean-corrected single loss approximation follow the tail index exactly.
INFINITE_MEAN_RULE = {
    "if": {"properties": {"outputs": {"properties": {"tail_index": {"minimum": 1}}, "required": ["tail_index"]}}, "required": ["outputs"]},
    "then": {"properties": {"outputs": {
        "properties": {
            "infinite_mean": {"const": True},
            "truth": {"properties": {"annual_loss_mean": {"properties": {"value_eur": {"type": "null"}, "reason": {"type": "string", "minLength": 1}}}}},
            "cells": {"items": {"properties": {"capital": {"properties": {"sla_mean_corrected": {"properties": {
                "summary": {"type": "null"}, "reason": {"type": "string", "minLength": 1}}}}}}}},
        }}}},
    "else": {"properties": {"outputs": {
        "properties": {
            "infinite_mean": {"const": False},
            "truth": {"properties": {"annual_loss_mean": {"properties": {"value_eur": {"type": "number"}, "reason": {"type": "null"}}}}},
        }}}},
}


def variant_schema(ref: str, kind: str, title: str, desc: str, root: str, defs: dict) -> None:
    doc = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{BASE}c17/{ref}.schema.json",
        "title": title,
        "description": desc,
        "allOf": [
            {"$ref": "../common/variant-envelope.schema.json"},
            {"properties": {"case_id": {"const": "C17"},
                            "outputs": {"$ref": f"#/$defs/{root}", "properties": {"kind": {"const": kind}}}},
             "required": ["case_id", "outputs"]},
            NOT_EVALUATED_RULE,
            TRUTH_STATUS,
            INFINITE_MEAN_RULE,
        ],
        "unevaluatedProperties": False,
        "$defs": reachable(root, defs),
    }
    write(f"{ref}.schema.json", doc)


def models_schema(title: str, desc: str, root: str, defs: dict) -> None:
    doc = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{BASE}c17/models.schema.json",
        "title": title,
        "description": desc,
        "allOf": [
            {"$ref": "../common/models-envelope.schema.json"},
            {"properties": {"case_id": {"const": "C17"}, "fit": {"$ref": f"#/$defs/{root}"}},
             "required": ["case_id", "fit"]},
            TRUTH_STATUS,
        ],
        "unevaluatedProperties": False,
        "$defs": reachable(root, defs),
    }
    write("models.schema.json", doc)


def write(name: str, doc: dict) -> None:
    path = SCHEMAS / "c17" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------------------------------------- C17

# The LDCE median percentiles of the severity of losses of EUR 20,000 or more (BCBS 160, Table ILD7; dossier 05 F.6),
# transcribed: a document that drifts from them fails.
LDCE_PERCENTILES = [(0.25, 27632), (0.5, 41916), (0.75, 82608), (0.95, 418400)]
# OPE25.7 Table 1 (dossier 01 section F), EUR.
BIC_COEFFICIENTS = [(1e9, 0.12), (30e9, 0.15), (None, 0.18)]


def c17_defs() -> dict:
    d: dict = {}
    d["c17Quantiles"] = Ob({"p05": N(), "p25": N(), "median": N(), "p75": N(), "p95": N()},
                           "Percentiles across the independent replications (linear interpolation), nondecreasing in the order "
                           "listed; the replications themselves are never in a document.")
    d["c17MoneyQuantiles"] = Ob({k: MONEY for k in ("p05", "p25", "median", "p75", "p95")},
                                "Percentiles across the replications of a money quantity, in EUR, nondecreasing.")
    d["c17RatioQuantiles"] = Ob({k: N(minimum=0) for k in ("p05", "p25", "median", "p75", "p95")},
                                "Percentiles across the replications of a ratio to the true 99.9 percent annual loss quantile.")
    d["c17IlmQuantiles"] = Ob({k: POS for k in ("p05", "p25", "median", "p75", "p95")},
                              "Percentiles across the replications of the internal loss multiplier (OPE25.8).")
    d["c17Band"] = Ob({"p05": N(), "median": N(), "p95": N()})

    # --- the truth
    d["c17Truth"] = Ob({
        "label": {"const": "synthetic-known-truth"},
        "currency": CUR,
        "frequency": Ob({
            "law": {"const": "poisson"},
            "lambda_per_year": POS,
            "counted_above_eur": MONEY,
        }, "The generator's true annual frequency: Poisson, losses per year at or above `counted_above_eur` (the generator floor, "
           "equal to the severity location)."),
        "severity": Ob({
            "law": {"const": "gpd"},
            "location_eur": MONEY,
            "scale_eur": POS,
            "tail_index": POS,
        }, "The generator's true severity: a generalised Pareto distribution with the tail index of the variant, starting at "
           "`location_eur` (the generator floor, no loss is generated below it). Threshold-stable: the loss above any higher "
           "collection threshold is again a GPD with the same tail index."),
        "annual_loss_quantile": Ob({
            "level": LEVEL,
            "value_eur": POS,
            "method": E("panjer", "fft"),
            "grid_step_eur": POS,
            "mc_check": Ob({
                "n_years": Int(1), "seed": Int(0),
                "value_eur": POS, "standard_error_eur": POS,
                "agrees": {"type": "boolean", "description": "True when the Monte Carlo value is within 3 standard errors of the value."},
            }),
        }, "The true 99.9 percent quantile of the annual loss of the generating process (all generated losses at or above the "
           "generator floor, whatever the collection threshold): computed once by Panjer or FFT on a fine grid and checked by "
           "Monte Carlo."),
        "annual_loss_mean": one_of(Ob({
            "value_eur": nullable(POS, "Null exactly when the tail index is 1 or more: the mean is infinite."),
            "reason": nullable(S(minLength=1), "Why the mean is absent; null when it is given."),
        }), {"value_eur": POS, "reason": {"type": "null"}}, {"value_eur": {"type": "null"}, "reason": S(minLength=1)}),
        "notice": TXT,
    }, "The generator's true parameters and the true 99.9 percent annual loss quantile, labelled synthetic-known-truth. "
       "Required in every C17 document: nothing is scored without them.")

    # --- the LDCE calibration (derived-only)
    d["c17Ldce"] = Ob({
        "currency": CUR,
        "label": {"const": "derived-only"},
        "licence_class": {"const": "derived-only"},
        "source": Ob({
            "id": {"const": "bcbs160"},
            "title": S(minLength=1),
            "url": {"const": "https://www.bis.org/publ/bcbs160.htm"},
            "date": {"const": "2009-07-28"},
            "table": S(minLength=1),
        }, "BCBS, Results from the 2008 Loss Data Collection Exercise for Operational Risk (BCBS 160)."),
        "threshold_eur": {"const": 20000, "description": "The LDCE statistics are of losses of EUR 20,000 or more."},
        "frequency": Ob({
            "per_eur_bn_assets": {"const": 0.82},
            "iqr_low": {"const": 0.36},
            "iqr_high": {"const": 1.66},
            "statistic": S(minLength=1),
        }, "The median bank's frequency of losses of EUR 20,000 or more per year per EUR billion of consolidated assets."),
        "severity_percentiles": {
            "type": "array",
            "description": "Median across banks of each bank's percentile of the severity (losses of EUR 20,000 or more, Table ILD7), "
                           "transcribed and locked: the four pairs, each once; the documents carry only the statistics the "
                           "calibration uses, never a reproduction of the BCBS tables.",
            "minItems": 4, "maxItems": 4, "uniqueItems": True,
            "items": one_of(Ob({"p": N(exclusiveMinimum=0, exclusiveMaximum=1), "loss_eur": POS}),
                            *[{"p": {"const": p}, "loss_eur": {"const": v}} for p, v in LDCE_PERCENTILES]),
        },
        "caveat": TXT,
    }, "The BCBS 2008 LDCE calibration targets with their source and the derived-only label (SDD section 5).")
    d["c17CalibrationFit"] = Ob({
        "tail_index": POS,
        "scale_eur": POS,
        "fitted_quantiles_eur": A(POS, 4, 4, "The generator's severity quantiles at the four LDCE percentiles, increasing."),
        "max_abs_log_error": N(minimum=0, description="Largest |ln(fitted / target)| over the four percentiles."),
        "method": S(minLength=1),
    }, "The generator's scale fitted to the four LDCE percentiles at the variant's tail index (least squares on the log quantiles).")
    d["c17Calibration"] = Ob({"targets": R("c17Ldce"), "fit": R("c17CalibrationFit")})

    # --- the synthetic bank
    d["c17Bi"] = Ob({"ildc_eur": MONEY, "sc_eur": MONEY, "fc_eur": MONEY, "bi_eur": MONEY},
                    "The business indicator BI = ILDC + SC + FC (OPE25.4) of the synthetic bank, three-year averages.")
    d["c17Bank"] = Ob({
        "currency": CUR,
        "synthetic": {"const": True},
        "label": TXT,
        "assets_eur": POS,
        "business_indicator": R("c17Bi"),
        "bic_eur": MONEY,
        "bucket": Int(1, 3),
        "notice": TXT,
    }, "The synthetic bank of stated size whose losses the generator draws and whose business indicator feeds the SMA; "
       "never a real bank.")

    # --- capital summaries
    def capital(status: dict) -> dict:
        return Ob({
            "aggregation": E("monte-carlo", "panjer", "fft", "closed-form"),
            "status": status,
            "n_defined": Int(2, desc="Replications with a defined value (a failed fit, or a fit with an infinite mean for a mean-based form, is not counted)."),
            "capital_eur": R("c17MoneyQuantiles"),
            "ratio_to_truth": R("c17RatioQuantiles"),
            "share_underestimating": UNIT,
            "iqr_over_truth": N(minimum=0),
            "log_sd": N(minimum=0, description="Standard deviation across the replications of ln(capital / true quantile)."),
        }, "The 99.9 percent capital of one rung across the independent histories of a cell: percentiles, the ratio to the true "
           "quantile (bias), the share of histories that underestimate it and the dispersion.")
    d["c17Capital"] = capital(E("verified", "UNVERIFIED"))
    d["c17CapitalUnverified"] = capital({"const": "UNVERIFIED"})
    d["c17MeanCorrectedSla"] = one_of(Ob({
        "summary": nullable(R("c17CapitalUnverified")),
        "reason": nullable(S(minLength=1)),
    }, "The mean-corrected single loss approximation F^-1(1 - (1 - alpha) / lambda) + lambda E[X], labelled UNVERIFIED until it is "
       "checked against Bocker and Sprittulla (2006) or Degen (2010). Null with its reason when the tail index is 1 or more (no mean)."),
        {"summary": R("c17CapitalUnverified"), "reason": {"type": "null"}}, {"summary": {"type": "null"}, "reason": S(minLength=1)})
    d["c17OptionalCapital"] = one_of(Ob({
        "summary": nullable(R("c17Capital")),
        "reason": nullable(S(minLength=1)),
    }, "A rung the bake may not have evaluated for a cell: the summary, or null with its reason."),
        {"summary": R("c17Capital"), "reason": {"type": "null"}}, {"summary": {"type": "null"}, "reason": S(minLength=1)})
    d["c17CapitalByRung"] = Ob({
        "lda_lognormal": R("c17Capital"),
        "lda_lognormal_truncated": R("c17Capital"),
        "lda_splice": R("c17Capital"),
        "sla": R("c17Capital"),
        "sla_mean_corrected": R("c17MeanCorrectedSla"),
        "scenario": R("c17OptionalCapital"),
    }, "The ladder of dossier 05: rung 1 the Poisson-lognormal LDA fitted ignoring the collection threshold (the biased "
       "baseline), rung 2 the truncated severity with the frequency rescaled, rung 3 the lognormal body and GPD tail splice, "
       "rung 4 the aggregation by Panjer or FFT (the `aggregation` of each), rung 5 the single loss approximation with "
       "(UNVERIFIED) and without the mean correction, rung 6 the scenario combination.")
    d["c17Replications"] = Ob({
        "seed_first": Int(0, desc="Replication i uses the seed seed_first + i; the ranges are disjoint between cells and variants."),
        "n_replications": Int(2),
        "n_failed": Int(0, desc="Histories whose fit failed to converge; they are counted, never dropped silently."),
        "n_losses_median": N(minimum=0, description="Median number of recorded losses per history."),
    }, "Independent simulated loss histories: the seeds, the count and the failures. The histories are not in the document.")
    d["c17Agreement"] = Ob({
        "max_rel_diff_panjer_fft": N(minimum=0), "n_compared": Int(1),
    }, "Largest relative difference of the 99.9 percent capital between the Panjer and the FFT aggregation of the same fit.")
    d["c17StabilityRow"] = Ob({
        "threshold_eur": MONEY,
        "n_exceedances_median": N(minimum=0),
        "n_fits": Int(0),
        "tail_index": R("c17Band"),
        "share_at_least_one": UNIT,
    }, "The fitted GPD tail index above one threshold across the replications; share_at_least_one is the share of fits with an "
       "infinite-mean tail index.")
    d["c17SmaCell"] = one_of(Ob({
        "currency": CUR,
        "basis": E("bic-times-ilm", "bic-only"),
        "reason": nullable(S(minLength=1), "Why capital is BIC only; null on the full basis."),
        "discretion_applied": E("none", "bucket-1-ilm-one", "national-ilm-one", "transitional-bic-only"),
        "bucket": Int(1, 3),
        "bic_eur": MONEY,
        "lc_eur": nullable(R("c17MoneyQuantiles"), "LC = 15 x the average annual loss over the available years (OPE25.8); null on the BIC-only basis."),
        "ilm": nullable(R("c17IlmQuantiles"), "ILM = ln(e - 1 + (LC / BIC)^0.8) (OPE25.8); null on the BIC-only basis."),
        "orc_eur": R("c17MoneyQuantiles"),
        "orc_over_true_quantile": R("c17RatioQuantiles"),
        "note": TXT,
    }, "The SMA capital of the synthetic bank on the same histories as the LDA of the cell, with the discretion applied as a "
       "named field (OPE25.10, OPE25.11, OPE25.15). ORC = BIC x ILM (OPE25.2). The SMA is not calibrated to the 99.9 percent "
       "quantile of any bank: the ratio to the true quantile is a comparison, not a claim of equivalence."),
        {"basis": {"const": "bic-times-ilm"}, "reason": {"type": "null"},
         "discretion_applied": E("none", "bucket-1-ilm-one", "national-ilm-one"),
         "lc_eur": R("c17MoneyQuantiles"), "ilm": R("c17IlmQuantiles")},
        {"basis": {"const": "bic-only"}, "reason": S(minLength=1), "discretion_applied": {"const": "transitional-bic-only"},
         "lc_eur": {"type": "null"}, "ilm": {"type": "null"}})
    d["c17SmaCell"]["if"] = {"properties": {"discretion_applied": {"const": "bucket-1-ilm-one"}}, "required": ["discretion_applied"]}
    d["c17SmaCell"]["then"] = {"properties": {"bucket": {"const": 1}}}
    d["c17Cell"] = Ob({
        "id": S(minLength=1),
        "years": Int(0, 10, "Years of recorded losses in each history (5 or 10 in the grid; under 5 the SMA is BIC only, OPE25.15)."),
        "collection_threshold_eur": {"enum": [10000, 20000], "description": "The collection threshold: losses below it are not recorded."},
        "currency": CUR,
        "replications": R("c17Replications"),
        "capital": R("c17CapitalByRung"),
        "aggregation_agreement": R("c17Agreement"),
        "threshold_stability": A(R("c17StabilityRow"), 1),
        "sma": R("c17SmaCell"),
    }, "One cell of the grid (years x collection threshold) of a tail-index variant, as replication summaries.")
    d["c17Cell"]["if"] = {"properties": {"years": {"maximum": 4}}, "required": ["years"]}
    d["c17Cell"]["then"] = {"properties": {"sma": {"properties": {"basis": {"const": "bic-only"}}}}}
    d["c17Cell"]["else"] = {"properties": {"sma": {"properties": {"basis": {"const": "bic-times-ilm"}}}}}

    # --- the true aggregate loss distribution computed three ways
    d["c17Exceedance"] = Ob({
        "currency": CUR,
        "grid_eur": A(POS, 3, desc="Loss grid, strictly increasing, log-spaced."),
        "monte_carlo": Ob({"n_years": Int(1), "seed": Int(0), "exceedance": A(UNIT, 3)}),
        "panjer": Ob({"step_eur": POS, "exceedance": A(UNIT, 3)}),
        "fft": Ob({"n_points": Int(2), "padding_factor": Int(1), "tilt": N(minimum=0), "exceedance": A(UNIT, 3)}),
        "quantile_999_eur": Ob({"monte_carlo": POS, "panjer": POS, "fft": POS, "sla": POS}),
    }, "P(annual loss > x) of the true distribution on one grid by Monte Carlo, Panjer and FFT, with the 99.9 percent quantile "
       "of each and of the single loss approximation (the marker).")
    d["c17SmaResponseRow"] = Ob({"added_loss_eur": MONEY, "lc_eur": MONEY, "ilm": POS, "orc_eur": MONEY})
    d["c17SmaResponse"] = Ob({
        "currency": CUR, "cell_id": S(minLength=1), "seed": Int(0), "bic_eur": MONEY,
        "rows": A(R("c17SmaResponseRow"), 3),
    }, "The ILM and the capital of one history as a single large loss of growing size is added to its latest year.")
    d["c17Scenario"] = Ob({
        "scenario_id": S(minLength=1), "label": TXT,
        "kind": E("percentile", "individual"),
        "loss_eur": POS,
        "exceedance_frequency_per_year": POS,
        "capital_without_eur": MONEY,
        "influence": N(description="(base capital - capital without the point) / base capital."),
    })
    d["c17ScenarioInfluence"] = Ob({
        "currency": CUR, "cell_id": S(minLength=1), "seed": Int(0), "level": LEVEL,
        "method": E("pseudo-observations", "body-tail", "bayesian-credibility"),
        "base_capital_eur": POS,
        "scenarios": A(R("c17Scenario"), 1),
        "reference": S(minLength=1),
    }, "The 99.9 percent capital's sensitivity to each scenario point of one history (the scenario influence).")

    d["c17Outputs"] = Ob({
        "kind": {"const": "tail-index"},
        "currency": CUR,
        "tail_index": POS,
        "infinite_mean": {"type": "boolean", "description": "True exactly when the tail index is 1 or more: the mean is infinite, "
                                                           "no mean-based quantity is computed and the mean-corrected SLA is absent."},
        "truth": R("c17Truth"),
        "calibration": R("c17Calibration"),
        "bank": R("c17Bank"),
        "cells": A(R("c17Cell"), 4, 4, "The grid in fixed order: 5 years then 10 years, each at collection threshold 10,000 then 20,000."),
        "exceedance": R("c17Exceedance"),
        "sma_response": R("c17SmaResponse"),
        "scenario_influence": R("c17ScenarioInfluence"),
    }, "C17 tail-index outputs (outputs.kind tail-index): one tail index of the generator of operational loss histories for a "
       "synthetic bank, calibrated to the BCBS 2008 LDCE quantiles, whose true annual loss distribution is known; the four cells "
       "of 5 or 10 years and a collection threshold of 10,000 or 20,000 as replication summaries; money in EUR.")

    # --- the models document
    d["c17VariantTruth"] = one_of(Ob({
        "variant_id": S(minLength=1),
        "tail_index": POS,
        "infinite_mean": B,
        "lambda_per_year": POS,
        "location_eur": MONEY,
        "scale_eur": POS,
        "true_quantile_999_eur": POS,
        "true_mean_eur": nullable(POS),
        "true_mean_reason": nullable(S(minLength=1)),
    }, "The true parameters and the true 99.9 percent annual loss quantile of one variant."),
        {"infinite_mean": {"const": False}, "true_mean_eur": POS, "true_mean_reason": {"type": "null"}},
        {"infinite_mean": {"const": True}, "true_mean_eur": {"type": "null"}, "true_mean_reason": S(minLength=1)})
    d["c17VariantTruth"]["if"] = {"properties": {"tail_index": {"minimum": 1}}, "required": ["tail_index"]}
    d["c17VariantTruth"]["then"] = {"properties": {"infinite_mean": {"const": True}}}
    d["c17VariantTruth"]["else"] = {"properties": {"infinite_mean": {"const": False}}}
    d["c17Generator"] = Ob({
        "name": S(minLength=1),
        "shaped_on": {"const": "bcbs160-ldce-2008"},
        "assets_eur_bn": POS,
        "frequency_law": {"const": "poisson"},
        "severity_law": {"const": "gpd"},
        "generator_floor_eur": MONEY,
        "notice": TXT,
    }, "The generator of annual operational loss histories for a synthetic bank; its true annual loss distribution is known.")
    d["c17Grid"] = Ob({
        "years": {"const": [5, 10]},
        "collection_thresholds_eur": {"const": [10000, 20000]},
        "n_replications_per_cell": Int(2),
        "seed_base": Int(0),
        "seed_stride": Int(1, desc="Cell k of variant v uses seed_first = seed_base + (4 v + k) x seed_stride."),
    })
    d["c17Rung"] = one_of(Ob({
        "rung_id": E("lda-lognormal", "lda-lognormal-truncated", "lda-splice", "sla", "sla-mean-corrected", "scenario"),
        "label": TXT,
        "severity_law": E("lognormal", "lognormal-truncated", "lognormal-gpd-splice", "gpd", "none"),
        "truncated": B,
        "aggregation": E("monte-carlo", "panjer", "fft", "closed-form"),
        "status": E("verified", "UNVERIFIED"),
        "reference": S(minLength=1),
    }, "A rung of the operational risk ladder of dossier 05."),
        {"rung_id": E("lda-lognormal", "lda-lognormal-truncated", "lda-splice", "sla", "scenario"), "status": {"const": "verified"}},
        {"rung_id": {"const": "sla-mean-corrected"}, "status": {"const": "UNVERIFIED"}})
    d["c17Aggregation"] = Ob({
        "level": LEVEL,
        "panjer_step_eur": POS, "panjer_points": Int(2),
        "fft_points": Int(2), "fft_padding_factor": Int(1), "fft_tilt": N(minimum=0),
        "mc_years_truth": Int(1), "mc_years_replication": Int(1),
    }, "How the aggregate loss is computed: the Panjer grid, the FFT size and padding, and the Monte Carlo years.")
    d["c17BicBucket"] = Ob({"bucket": Int(1, 3), "upper_eur": nullable(POS), "coefficient": N(exclusiveMinimum=0, maximum=1)})
    d["c17Discretion"] = Ob({"id": E("bucket-1-ilm-one", "national-ilm-one", "transitional-bic-only"), "description": TXT,
                             "reference": S(minLength=1)})
    d["c17SmaSpec"] = Ob({
        "currency": CUR,
        "buckets": {
            "type": "array", "minItems": 3, "maxItems": 3, "uniqueItems": True,
            "description": "OPE25.7 Table 1, transcribed and locked: 12% to EUR 1bn, 15% from 1bn to 30bn, 18% above.",
            "items": one_of(R("c17BicBucket"), *[{"bucket": {"const": i + 1}, "upper_eur": {"const": up}, "coefficient": {"const": c}}
                                                 for i, (up, c) in enumerate(BIC_COEFFICIENTS)]),
        },
        "loss_multiple": {"const": 15},
        "loss_window_years": {"const": 10},
        "minimum_years": {"const": 5},
        "ilm_exponent": {"const": 0.8},
        "rwa_factor": {"const": 12.5},
        "discretions": A(R("c17Discretion"), 3, 3),
        "golden": Ob({"bi_eur": {"const": 35e9}, "bic_eur": {"const": 5.37e9}, "reference": {"const": "OPE25.7 footnote 2"}}),
        "reference": S(minLength=1),
    }, "The OPE25 standardised approach as specified (dossier 01 section F), with its golden value.")
    d["c17ScenarioSpec"] = Ob({
        "methods": A(E("pseudo-observations", "body-tail", "bayesian-credibility"), 3, 3),
        "reference": S(minLength=1),
    })
    d["c17Fit"] = Ob({
        "currency": CUR,
        "generator": R("c17Generator"),
        "calibration": R("c17Ldce"),
        "variants": A(R("c17VariantTruth"), 4, 4, "One row per tail index in increasing order: 0.6, 0.8, 0.96, 1.1."),
        "grid": R("c17Grid"),
        "ladder": A(R("c17Rung"), 6, 6),
        "aggregation": R("c17Aggregation"),
        "sma": R("c17SmaSpec"),
        "scenarios": R("c17ScenarioSpec"),
    }, "C17 models: the generator, the LDCE calibration targets, the true parameters and quantile of every variant, the grid and "
       "its seeds, the ladder, the aggregation settings, the OPE25 specification and the scenario methods.")
    return d


def main() -> None:
    d = c17_defs()
    variant_schema("variant-tail-index", "tail-index", "C17 tail-index variant",
                   "Catalog row c17-outputs 1.0.0: one tail index of the operational risk case (outputs.kind tail-index), LDA against SMA "
                   "on a generator of operational loss histories with a known true annual loss distribution.", "c17Outputs", d)
    models_schema("C17 models",
                  "Catalog row c17-models 1.0.0: the C17 models artifact (generator, LDCE calibration targets, true parameters of every "
                  "variant, grid, ladder, aggregation, OPE25 specification).", "c17Fit", d)


if __name__ == "__main__":
    main()
