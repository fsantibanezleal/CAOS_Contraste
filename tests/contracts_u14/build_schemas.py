"""Builds the ten U14-S schema files (docs/contracts/schemas/c02, c20, c21).

Run: ``python tests/contracts_u14/build_schemas.py``. Deterministic, standard library only. Conventions of
docs/contracts/catalog.md: one folder per case, a ``case_id`` const, ``outputs.kind`` on every variant schema, case-prefixed
``$defs``, the ``variant-envelope`` composition with ``unevaluatedProperties: false``, every object closed.

Variants (decision of U14-S): C02 one schema, outputs.kind ``horizon`` (one document per horizon file 1 to 5 and the pooled one);
C20 five kinds (``shock``, ``shift``, ``seeds``, ``perturbation``, ``leakage``); C21 one schema, outputs.kind ``year-pair``.
Requirement ids (Q14): C02 CT-0201 onward, C20 CT-2001 onward, C21 CT-2101 onward.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import (  # noqa: E402
    A,
    B,
    C,
    contains_each,
    contains_pairs,
    E,
    Int,
    models_schema,
    N,
    NONNEG,
    nullable,
    Ob,
    one_of,
    R,
    S,
    TXT,
    UNIT,
    variant_schema,
)
from values import (  # noqa: E402
    ATTRIBUTE_FIELDS,
    C02_NAMES,
    C20_NAMES,
    C21_TESTS,
    CONTROL_FIELDS,
    FAIR_ATTRIBUTES,
    FAIR_TESTS,
    FHA_DISPARATE_IMPACT,
    GROUPS,
    HMDA_DATE_RULE,
    HMDA_FIELDS,
    HMDA_ID_RULE,
    HMDA_MODIFIED,
    HMDA_PLATFORM_TERMS,
    HORIZON_YEARS,
    LEGAL,
    NAMED,
    NON_GROUPS,
    PAIRS,
    QUOTES,
    SGCD_COMMIT,
    SGCD_QUOTE,
    TREATMENTS,
)

CONV = C("convention", "Every named parameter carries this label: a convention, never a regulatory threshold (06 I.6 l.1268-1270).")
EXPL = C("exploratory", "The block is exploratory and says so.")
LIGHT = E("green", "amber", "red", "not_evaluated", "error")
RUNGS = E("P0", "P1", "P2a", "P2b", "P3", "P4")


def named_params(prefix: str, names: list[str]) -> dict:
    return {
        f"{prefix}Param": Ob({
            "name": E(*NAMED),
            "value": {"anyOf": [N(), A(N(), 1), S()]},
            "unit": S(),
            "label": CONV,
            "basis": S("Where the construction comes from and how the value was proposed (decision Q8)."),
        }, "A named parameter: its value and the label convention."),
        f"{prefix}Params": contains_each(A(R(f"{prefix}Param"), desc="The named parameters of the document, each once."), "name", names),
    }


# ======================================================================================================= C02
def c02_defs() -> dict:
    d = named_params("c02", C02_NAMES)
    d["c02Ci"] = Ob({"lo": N(), "hi": N(), "level": C(0.95), "method": C("delong")}, "AUC interval, DeLong (the engine's disc_delong).")
    d["c02Counts"] = Ob({"rows": Int(1), "events": Int(0), "event_rate": UNIT, "features": Int(1),
                         "event_definition": TXT}, "Counts and event rate of the file (bankruptcy within the horizon).")
    d["c02PoolFile"] = Ob({"file": S(), "years": Int(1, 5), "rows": Int(1), "events": Int(0)})
    d["c02Pooled"] = Ob({"files": A(R("c02PoolFile"), 5, 5), "horizon_indicator": C(True), "overlap": TXT},
                        "The five files stacked with a horizon indicator (decision Q9); the firm overlap is unknown.")
    d["c02Split"] = Ob({
        "protocol": C("locked-stratified-holdout"), "seed": Int(0), "train_rows": Int(1), "calibration_rows": Int(0),
        "holdout_rows": Int(1), "holdout_events": Int(0),
        "fit_on_training_slice_only": C(True, "Binning, imputation and selection are fitted on the training slice only (04 l.1054-1059)."),
        "calibration_map_on_separate_slice": C(True), "resampling_before_calibration": C(False),
        "out_of_time_claim": C(False, "The files carry no date: no out-of-time claim."),
    })
    d["c02Roc"] = Ob({"fpr": A(UNIT, 2), "tpr": A(UNIT, 2)}, "ROC points of the holdout, in the shape of C01: false and true positive rates, same length, from (0, 0) to (1, 1).")
    d["c02Cap"] = Ob({"population": A(UNIT, 2), "defaults": A(UNIT, 2), "default_rate": UNIT},
                     "CAP points of the holdout, in the shape of C01: cumulative share of the population against the cumulative share of the defaults.")
    d["c02ReliabilityBin"] = Ob({"n": Int(1), "pd": N(exclusiveMinimum=0, exclusiveMaximum=1), "dr": UNIT, "lo": UNIT, "hi": UNIT},
                                "One decile of the reliability diagram, in the shape of C01: mean predicted PD, observed default rate and its interval.")
    d["c02Rung"] = Ob({
        "model_id": S(), "rung": RUNGS,
        "roc": R("c02Roc"), "cap": R("c02Cap"),
        "reliability": A(R("c02ReliabilityBin"), 1, 10, desc="Calibration by decile of the holdout: at most ten bins."),
        "discrimination": Ob({"auc": UNIT, "auc_ci": R("c02Ci"), "gini": N(minimum=-1, maximum=1), "ks": UNIT}),
        "calibration": Ob({"brier": UNIT, "ece": UNIT, "hosmer_lemeshow": Ob({"statistic": NONNEG, "df": Int(1), "p_value": UNIT})}),
        "overfit": Ob({"train_auc": UNIT, "holdout_auc": UNIT, "gap": N(), "tolerance": NONNEG, "flag": B}),
        "stability": Ob({"psi": NONNEG, "csi_max": NONNEG}, "Holdout against training slice (existing engine tests)."),
    })
    d["c02Challenger"] = Ob({
        "champion": S(), "challenger": S(), "auc_diff": N(), "auc_diff_ci": R("c02Ci"), "delong_p_value": UNIT,
        "brier_diff": N(), "brier_diff_ci": Ob({"lo": N(), "hi": N(), "level": C(0.95), "method": C("paired-bootstrap")}),
        "grade_disagreement_share": UNIT,
    }, "Champion and challenger: the DeLong difference and the paired bootstrap of the Brier difference (06 C.7 l.1041-1044).")
    d["c02Transfer"] = Ob({
        "label": EXPL, "reason": TXT,
        "cells": A(Ob({"rung": RUNGS, "fitted_on_years": Int(1, 5), "scored_on_years": Int(1, 5),
                       "auc": UNIT, "n": Int(1), "events": Int(0)}), 0),
    }, "Cross-file transfer: a rung fitted on file i scored on the holdout of file j. Exploratory: the firm overlap is unknown (SDD l.374). Empty for the pooled variant.")
    d["c02TermStructure"] = Ob({
        "label": EXPL, "reason": TXT,
        "points": A(Ob({"years": Int(1, 5), "cumulative_pd": N(exclusiveMinimum=0, exclusiveMaximum=1),
                        "hazard": N(exclusiveMinimum=0, exclusiveMaximum=1)}), 5, 5),
        "cumulative_nondecreasing": B,
        "source": C("engine-provisions-api from_cumulative and lifetime_pd_backtest (04 E.2 l.479-497)"),
    }, "The five file event rates read as a cumulative PD: cumulative = 1 - product of (1 - hazard). Exploratory (decision Q9).")
    d["c02ImpactDetail"] = Ob({
        "label": EXPL, "reason": TXT, "source": C("engine-provisions-api"),
        "pd_basis": S(), "lgd": Ob({"value": N(minimum=0, maximum=1), "label": C("assumption")}),
        "ecl_12m_effect": nullable(N()), "ecl_lifetime_effect": nullable(N()), "unit": S(),
        "reason_if_null": nullable(S()),
    }, "The 12-month and lifetime ECL effect of the horizon PDs (decision Q10). Exploratory.")
    d["c02Outputs"] = Ob({
        "kind": C("horizon"),
        "horizon_id": E("h1", "h2", "h3", "h4", "h5", "pooled"),
        "years": nullable(Int(1, 5), "The horizon of the file; null for the pooled variant."),
        "counts": R("c02Counts"),
        "pooled": nullable(R("c02Pooled")),
        "firm_overlap_caveat": nullable(TXT, "Required text for the pooled variant: the firm overlap across the five files is unknown (08 l.855-856)."),
        "split": R("c02Split"),
        "rungs": A(R("c02Rung"), 1),
        "challenger": A(R("c02Challenger"), 0),
        "transfer": R("c02Transfer"),
        "term_structure": R("c02TermStructure"),
        "impact_detail": R("c02ImpactDetail"),
        "parameters": R("c02Params"),
        "requirements": A(S(pattern=r"^CT-02\d\d$"), 1, desc="Requirement ids CT-0201 onward (decision Q14)."),
    }, "C02 horizon outputs: one document per horizon file (1 to 5 years) and the pooled variant. Exploratory blocks carry their label.")
    # U14 G22 (1.1.0): the block may be null (a widened type, so the mechanical floor of the contract gate sees no break); `properties`,
    # `required` and `additionalProperties` constrain an object only
    d["c02TermStructure"]["type"] = ["object", "null"]
    d["c02TermStructure"]["description"] = ("The five file event rates read as a cumulative PD: cumulative = 1 - product of (1 - hazard). Exploratory (decision Q9). "
                                            "Null, with its reason in term_structure_reason, when the points cannot form a cumulative curve (U14 G22: the horizon "
                                            "files are independent samples, not one cohort).")
    # the reason is optional in the schema (every 1.0.0 document stays valid); the checker pairs it with the block
    d["c02Outputs"]["properties"]["term_structure_reason"] = nullable(TXT, "A reason where term_structure is null, null where the block is present (checked by semantics.check_c02).")
    d["c02Fit"] = Ob({
        "files": A(Ob({"horizon_id": E("h1", "h2", "h3", "h4", "h5"), "years": Int(1, 5), "file": S(), "rows": Int(1), "events": Int(0)}), 5, 5),
        "ladder": A(Ob({"rung": RUNGS, "label": TXT, "engine": S(), "reference": S()}), 1),
        "protocol": R("c02Split"),
        "parameters": R("c02Params"),
    }, "C02 models: the five files, the ladder reused from C01 and the leakage-safe protocol.")
    return d


def horizon_rule(hid: str, years: int | None) -> dict:
    """horizon_id and years agree (m1); the pooled variant carries the pooled block and the caveat, the others none."""
    props: dict = {"years": C(years), "pooled": {"type": "object"} if years is None else {"type": "null"}}
    if years is None:
        props["firm_overlap_caveat"] = {"type": "object"}
    return {"if": {"properties": {"outputs": {"properties": {"horizon_id": {"const": hid}}, "required": ["horizon_id"]}}, "required": ["outputs"]},
            "then": {"properties": {"outputs": {"properties": props}}}}


C02_RULES = [
    *[horizon_rule(h, y) for h, y in HORIZON_YEARS.items()],
    {"properties": {"impact": {"required": ["ecl_12m_effect", "ecl_lifetime_effect"]}}},
]


# ======================================================================================================= C20
def c20_defs() -> dict:
    d = named_params("c20", C20_NAMES)
    d["c20SgcdNotice"] = Ob({
        "kind": C("dataset-card-prohibition"), "quote": C(SGCD_QUOTE), "commit": C(SGCD_COMMIT),
        "text": TXT,
    }, "The SGCD dataset card's prohibited-use sentence (U14 research addendum H4 6.5), on every variant that shows SGCD.")
    d["c20Metric"] = Ob({"auc": UNIT, "brier": UNIT, "auc_delta": N()})
    d["c20Drift"] = Ob({
        "psi_max": NONNEG, "csi_max": NONNEG, "chi2_p_value": nullable(UNIT),
        "variables": A(Ob({"name": S(), "psi": NONNEG, "csi": NONNEG, "chi2_p_value": nullable(UNIT)}), 1,
                       desc="Per variable PSI and CSI with the chi-square p-value, so the bars and the chi-square band can be drawn (engine validation.stability)."),
    })
    d["c20Quality"] = Ob({"completeness": UNIT, "consistency": nullable(UNIT)})
    d["c20ShockRow"] = Ob({
        "shock_id": E("F0", "F1", "F2", "F3", "F4", "numeric-noise"),
        "batches": A(S(pattern=r"^(S|A|T)\d+$"), 1),
        "n_records": Int(1), "n_reaching_structured_view": Int(0),
        "performance": R("c20Metric"), "drift": R("c20Drift"), "data_quality": R("c20Quality"),
        "attribution_rank_correlation": nullable(N(minimum=-1, maximum=1), "Spearman rho, the engine's ml.explanations.rank_agreement, between the mean absolute SHAP importance per feature on the clean batches and on the batches of this shock; null when a vector is constant (rank_agreement raises ValueError)."),
    }, "One shock family on the 1,000 SGCD records; n_reaching_structured_view counts the records whose json_view differs from a clean one (F1: 70 of 1,000, no other shock; addendum H4 6.4).")
    d["c20ShockShipped"] = Ob({"label": C("shipped"), "rows": A(R("c20ShockRow"), 1), "parameters_source": C(None)},
                              "The shocks as shipped in the SGCD batches: no Contraste parameters (decision C5).")
    d["c20ShockApplied"] = Ob({"label": C("contraste-applied"), "rows": A(R("c20ShockRow"), 1),
                               "parameters_source": C("SGCDataset_metadata.json, seed 42")},
                              "Contraste's own application of each shock family to json_view, with the metadata parameters and seed 42 (decision C5).")
    d["c20FairRow"] = Ob({
        "test_id": E(*FAIR_TESTS), "attribute": E(*FAIR_ATTRIBUTES), "value": nullable(N()),
        "groups": A(Ob({"group": S(), "n": Int(1), "value": nullable(N())}), 2), "light": LIGHT,
    })
    d["c20FairBattery"] = Ob({
        "label": C("labelled-fairness-battery"), "model": C("uci-taiwan"),
        "notice": TXT, "rows": contains_pairs(A(R("c20FairRow")), ("test_id", "attribute"), [(t, a) for t in FAIR_TESTS for a in FAIR_ATTRIBUTES]),
    }, "The labelled fairness battery on the Taiwan model (decision Q5): outcome-conditioned tests, a battery row set, not a compliance statement.")
    d["c20Impact"] = Ob({
        "label": C("decision-flip"),
        "cutoff": Ob({"rule": C("reject-worst-share-of-baseline-scores"), "reject_share": UNIT, "label": CONV}),
        "rows": A(Ob({"shift_id": S(), "flip_share": UNIT, "n_decisions": Int(1)}), 1),
    }, "The share of decisions that flip at the stated cut-off under each shift (decision Q10).")

    def core(kind: str, extra: dict) -> dict:
        return Ob({
            "kind": C(kind),
            "dataset_id": E("sgcd", "uci-german", "uci-taiwan", "uci-polish", "fed-2025-corporate"),
            "model_dataset": E("uci-german", "uci-taiwan", "uci-polish"),
            "sgcd_notice": nullable(R("c20SgcdNotice")),
            "parameters": R("c20Params"),
            "fairness_battery": nullable(R("c20FairBattery")),
            "impact_detail": R("c20Impact"),
            "requirements": A(S(pattern=r"^CT-20\d\d$"), 1, desc="Requirement ids CT-2001 onward (decision Q14)."),
            **extra,
        })

    d["c20Outputs"] = core("shock", {
        "dataset_id": C("sgcd"),
        "seen_or_held_out": E("seen", "held-out"),
        "model_view": C("json_view"),
        "shipped": R("c20ShockShipped"), "applied": R("c20ShockApplied"),
    })
    d["c20RealDrift"] = Ob({
        "label": C("real-drift-no-model"), "model": C(None),
        "portfolios": A(E("typical", "higher-risk", "lower-risk"), 3, 3, unique=True),
        "pairs": A(Ob({"a": S(), "b": S(), "variables": A(Ob({"name": S(), "psi": NONNEG, "csi": NONNEG, "ks": UNIT, "chi2_p_value": nullable(UNIT)}), 1)}), 1),
    }, "Reading (a) of decision Q7: the real drift between the three 200-loan Fed 2025 portfolios, no model.")
    cbpe_ids = ["calibrated-probabilities", "no-concept-drift", "no-extrapolation", "adequate-sample"]
    d["c20SyntheticShift"] = Ob({
        "label": C("synthetic-shift-fed-reference"), "reference_portfolio": E("typical", "higher-risk", "lower-risk"),
        "evaluation_set": S(),
        "shifts": A(Ob({"shift_id": S(), "score": NONNEG, "metric": R("c20Metric"), "psi": NONNEG, "flip_share": UNIT}), 1),
        "worst_subsample": Ob({"share": UNIT, "metric": R("c20Metric")}),
        "label_free": Ob({
            "conformal": Ob({
                "label": CONV, "alpha": UNIT, "target_coverage": UNIT, "coverage": UNIT, "binomial_p_value": UNIT,
                "coverage_by_window": A(Ob({"window": S(), "n": Int(1), "coverage": UNIT, "binomial_p_value": UNIT}), 1,
                                        desc="Coverage over time: one row per evaluation window (06 I.4 l.1248); alpha is a convention."),
            }),
            "cbpe": Ob({"label": C("estimate"), "estimated_auc": UNIT,
                        "assumptions": contains_each(A(Ob({"id": E(*cbpe_ids), "text": TXT})), "id", cbpe_ids)}),
        }),
    }, "Reading (b) of decision Q7: the Fed portfolios as the reference of a synthetic shift on the UCI evaluation set only.")
    d["c20OutputsShift"] = core("shift", {"real_drift": R("c20RealDrift"), "synthetic_shift": R("c20SyntheticShift")})
    d["c20SeedRow"] = Ob({
        "rung": S(), "n_seeds": Int(2),
        "auc": Ob({"mean": UNIT, "sd": NONNEG, "min": UNIT, "max": UNIT}),
        "grade_assignment_changed_share": UNIT,
        "attribution_rank_tau": Ob({"mean": N(minimum=-1, maximum=1), "min": N(minimum=-1, maximum=1)}),
        "reason_code_overlap": Ob({"top_k": C(4), "n_refits": Int(2), "mean": UNIT, "p05": UNIT}),
    })
    d["c20Ale"] = Ob({"edges": A(N(), 2), "effect": A(N(), 1)},
                     "ALE of one feature: bin edges (n_bins + 1) and the centred effect of each bin (n_bins), the engine's accumulated_local_effects.")
    d["c20Explainer"] = Ob({
        "rung": S(), "effect_reference": E("ale", "pdp"), "n_features": Int(2),
        "rank_correlation": nullable(N(minimum=-1, maximum=1), "Spearman rho between the mean absolute SHAP per feature and the range of its ALE or PDP curve (ml.explanations.rank_agreement, ml.effect_agreement)."),
        "reason_if_null": nullable(S()),
        "top_features": A(Ob({"feature": S(), "shap_importance": NONNEG, "effect_range": NONNEG, "ale": R("c20Ale")}), 1, 10),
    }, "Explainer agreement of one model: SHAP against ALE or PDP, with the ALE curves of the top features (06 C.7 l.1006-1008).")
    d["c20OutputsSeeds"] = core("seeds", {"rows": A(R("c20SeedRow"), 1), "explainer_agreement": A(R("c20Explainer"), 1)})
    d["c20OutputsPerturbation"] = core("perturbation", {
        "preset_eps": N(exclusiveMinimum=0, description="The scale at which the tolerance is tested."),
        "rows": A(Ob({"eps": N(minimum=0), "metric": R("c20Metric"), "finding": B}), 1),
    })
    d["c20Threshold"] = Ob({"value": UNIT, "label": CONV})
    d["c20OutputsLeakage"] = core("leakage", {
        "planted_feature": S(),
        "thresholds": Ob({"single_feature_auc": R("c20Threshold"), "resemblance_auc": R("c20Threshold")},
                         "The two screen limits of the policy, each a convention (ml.leakage_screen.single_feature_auc and .resemblance_auc)."),
        "screen": Ob({
            "temporal_order": Ob({"violations": Int(0)}),
            "single_feature_auc": Ob({"max_auc": UNIT, "feature": S(), "suspect": B}),
            "entity_overlap": Ob({"share": UNIT}),
            "resemblance_auc": UNIT,
        }),
        "caught": B,
        "performance": Ob({"development_auc": UNIT, "decision_time_auc": UNIT}),
    })
    d["c20Fit"] = Ob({
        "datasets": A(Ob({"id": E("sgcd", "uci-german", "uci-taiwan", "uci-polish", "fed-2025-corporate"), "rows": Int(1), "role": S()}), 1),
        "ladder": A(Ob({"rung": S(), "engine": S(), "dataset": E("uci-german", "uci-taiwan", "uci-polish")}), 1),
        "sgcd": Ob({"commit": C(SGCD_COMMIT), "seed": C(42), "notice": R("c20SgcdNotice")}),
        "parameters": R("c20Params"),
    }, "C20 models: the fitted rungs on the UCI sets, the SGCD pin and the named parameters.")
    return d


def cond_rule(field: str, const, then_type: str, else_type: str, prop: str) -> dict:
    return {"if": {"properties": {"outputs": {"properties": {field: {"const": const}}, "required": [field]}}, "required": ["outputs"]},
            "then": {"properties": {"outputs": {"properties": {prop: {"type": then_type}}}}},
            "else": {"properties": {"outputs": {"properties": {prop: {"type": else_type}}}}}}


C20_RULES = [
    cond_rule("dataset_id", "sgcd", "object", "null", "sgcd_notice"),
    cond_rule("model_dataset", "uci-taiwan", "object", "null", "fairness_battery"),
    {"properties": {"impact": {"required": ["decision_flip_share"]}}},
]


# ======================================================================================================= C21
def c21_defs() -> dict:
    d: dict = {}
    d["c21Hmda"] = E(*HMDA_FIELDS)
    d["c21Control"] = E(*CONTROL_FIELDS)
    d["c21Label"] = Ob({"en": C("no legal claim"), "es": C("sin afirmacion legal")}, "The required label, on every C21 document.")

    def statement(key: str) -> dict:
        cit, quote = QUOTES[key]
        return Ob({"citation": C(cit), "quote": C(quote), "text": TXT})

    d["c21Legal"] = Ob({
        "label": R("c21Label"),
        "regulation_b": statement("reg_b"), "fair_housing_act": statement("fha"), "procedures": statement("procedures"),
        "unconditional_rates_are": C("indicators-only"),
        "controlled_disparity_is": C("approximation-of-comparative-evidence"),
        "is_a_finding_of_violation": C(False),
    }, "No legal claim: the sentences the U14 research addendum quotes (H3 4.1 and 4.3), decision C4.")
    d["c21Group"] = Ob({"group": S(), "n": Int(1), "n_approved": Int(0), "n_denied": Int(0), "selection_rate": UNIT})
    d["c21Excluded"] = Ob({"group": S(), "n": Int(0), "reason": TXT},
                          "A non-attribute category (Joint, Not Available, Free Form Text Only): carried as its own group and excluded from the pairwise tests (decision C2).")
    d["c21Test"] = Ob({"statistic": N(), "p_value": UNIT})
    d["c21Air"] = Ob({
        "value": nullable(NONNEG, "Protected group's selection rate over the reference group's: the parity ratio, null when the reference rate is 0. It is not the four-fifths ratio, which is taken against the highest-rate group (the attribute's four_fifths block)."),
        "note": TXT,
    }, "The adverse impact ratio against the chosen reference group.")
    d["c21FourFifthsRow"] = Ob({
        "group": S(),
        "ratio_to_highest": nullable(NONNEG, "The group's selection rate over the highest group's rate; null when the highest rate is 0."),
        "flag": B,
    }, "One group against the highest-rate group; the flag is decided on the counts in exact arithmetic, never on the float ratio.")
    d["c21FourFifths"] = Ob({
        "label": C("employment benchmark"), "citation": C("29 CFR 1607.4(D)"), "threshold": C(0.8),
        "is_credit_law_threshold": C(False), "compared_with": C("highest-rate-group"),
        "decided_on": C("exact-counts"), "rule": C("flag when 5 * x_g * n_h < 4 * x_h * n_g"),
        "highest_rate_group": S("The group with the highest selection rate (the first of them in groups order on a tie)."),
        "groups": A(R("c21FourFifthsRow"), 2, desc="One row per group of the attribute, the highest-rate group included (ratio 1, no flag)."),
    }, "The four-fifths line is an employment benchmark and never a credit-law threshold (06 C.7 l.1033-1037, I.6 l.1268-1270). It compares each group with the highest-rate group (29 CFR 1607.4(D); 06 C.7 l.1034-1035), decided on the counts: a group is flagged when 5 * x_g * n_h < 4 * x_h * n_g, so exactly four-fifths is not flagged.")
    missing = {"type": "array", "items": E("credit_score"), "minItems": 1, "maxItems": 1,
               "description": "Public HMDA has no credit score: every controlled estimate names it as a missing control (decision C2)."}
    d["c21Ci"] = Ob({"lo": N(), "hi": N(), "level": C(0.95)})
    d["c21Controlled"] = Ob({
        "model": C("logistic-decision-model"), "outcome": C("approval"), "coefficient": N(), "odds_ratio": N(exclusiveMinimum=0),
        "ci": R("c21Ci"), "n": Int(1), "controls": A(R("c21Control"), 1, unique=True), "missing_controls": missing,
        "label": C("approximation of comparative evidence"),
    }, "Logistic decision model of approval on the protected attribute and the permitted underwriting controls (decision Q4).")
    d["c21RateSpread"] = Ob({
        "model": C("linear-rate-spread"), "population": C("action_taken 1 or 2"), "coefficient": N(), "ci": R("c21Ci"), "n": Int(1),
        "controls": A(R("c21Control"), 1, unique=True), "missing_controls": missing,
        "label": C("approximation of comparative evidence"), "unit": C("percentage points of rate_spread"),
    }, "Linear model of the rate spread on the same terms; the loans that carry rate_spread (action taken 1 and 2).")
    d["c21Confirmation"] = Ob({
        "fit_year": Int(2018, 2023), "confirm_year": Int(2019, 2024), "fit_coefficient": N(), "confirm_coefficient": N(),
        "same_sign": B, "size_ratio": nullable(N(), "confirm coefficient over fit coefficient; null when the fit coefficient is 0."),
    }, "Confirmation on year t+1 by sign and size (decision Q4).")

    def opt(inner: str) -> dict:
        return one_of(Ob({"estimate": nullable(R(inner)), "reason": nullable(S())}, "The estimate, or null with its reason (missing-data behavior)."),
                      {"estimate": R(inner), "reason": {"type": "null"}}, {"estimate": {"type": "null"}, "reason": S()})

    d["c21OptControlled"] = opt("c21Controlled")
    d["c21OptRateSpread"] = opt("c21RateSpread")
    d["c21OptConfirmation"] = opt("c21Confirmation")
    d["c21Contrast"] = Ob({
        "group": S(), "reference_group": S(), "n_group": Int(1), "n_reference": Int(1),
        "selection_rate_group": UNIT, "selection_rate_reference": UNIT,
        "parity_gap": N(minimum=-1, maximum=1, description="Group rate minus reference rate."),
        "parity_ratio": nullable(NONNEG),
        "adverse_impact_ratio": R("c21Air"),
        "z_test": R("c21Test"),
        "fisher_exact": Ob({"odds_ratio": nullable(NONNEG), "p_value": UNIT}),
        "controlled": R("c21OptControlled"), "rate_spread": R("c21OptRateSpread"), "confirmation": R("c21OptConfirmation"),
    })
    d["c21Attribute"] = Ob({
        "field": E(*ATTRIBUTE_FIELDS),
        "legal": Ob({"basis": E(*[b for b, _, _ in LEGAL.values()]), "ecoa": B, "fha": B, "note": TXT,
                     "theory": C("comparative-evidence-of-disparate-treatment"), "fha_disparate_impact": S()},
                    "The legal mapping of the attribute, from the addendum H3 section 5 table only."),
        "reference_group": S(),
        "groups": A(R("c21Group"), 2),
        "excluded_groups": A(R("c21Excluded"), 0),
        "four_fifths": R("c21FourFifths"),
        "contrasts": A(R("c21Contrast"), 1),
    })
    d["c21Attribute"]["oneOf"] = [
        {"properties": {
            "field": C(f),
            "legal": {"properties": {"basis": C(b), "ecoa": C(e), "fha": C(h), "fha_disparate_impact": C(FHA_DISPARATE_IMPACT[f])}},
            "reference_group": E(*GROUPS[f]),
            "groups": {"items": {"properties": {"group": E(*GROUPS[f])}}},
            "excluded_groups": {"items": {"properties": {"group": E(*NON_GROUPS[f])}}},
            "four_fifths": {"properties": {"highest_rate_group": E(*GROUPS[f]), "groups": {"items": {"properties": {"group": E(*GROUPS[f])}}}}},
            "contrasts": {"items": {"properties": {"group": E(*GROUPS[f]), "reference_group": E(*GROUPS[f])}}},
        }}
        for f, (b, e, h) in LEGAL.items()]
    d["c21Conventions"] = Ob({
        "label": CONV,
        "outcome": Ob({"approval_codes": C([1, 2]), "denial_codes": C([3]), "excluded_codes": C([4, 5, 6, 7, 8]),
                       "note": TXT}, "approval = 1 and 2, denial = 3; 4 and 5 have no decision; 6, 7 and 8 left out (decision C3)."),
        "dti_recode": Ob({"bins": A(S(), 1), "note": TXT}, "The mixed exact and binned debt-to-income field is recoded to the published bins (decision C2)."),
        "group_exclusion": TXT,
        "identifiers": Ob({"id": C(HMDA_ID_RULE), "observation_date": C(HMDA_DATE_RULE), "label": CONV, "note": TXT},
                          "Public HMDA withholds the loan identifier and the dates (addendum H1 2.5): id is the row position in the source file within its activity year, observation_date is the activity year's 12-31 (decision V3)."),
    }, "Named conventions, labelled on every result.")
    d["c21Licence"] = Ob({
        "status": C("UNVERIFIED"), "platform_terms": C(HMDA_PLATFORM_TERMS),
        "platform_terms_cover": C("the software package, not the published datasets"),
        "modified_statement": C(HMDA_MODIFIED), "note": TXT,
    }, "The HMDA data licence stays UNVERIFIED (addendum H2 3.3); the views quote the platform software terms and the CFPB statement that the public data are modified (decision C7).")
    d["c21Note"] = Ob({"field": R("c21Hmda"), "treatment": E(*TREATMENTS), "n_missing": nullable(Int(0)), "reason": TXT},
                      "A field HMDA withholds or bins in the public release: a nullable value with its reason, never a fabricated number.")
    d["c21Situation"] = Ob({
        "label": C("situation-testing"), "comparator": C("ceteris-paribus"),
        "counterfactual_test": Ob({"run": C(False), "reason": TXT},
                                  "Public HMDA gives no counterfactual dataset, so the counterfactual test is not run here (decision C6)."),
        "attribute": E(*ATTRIBUTE_FIELDS), "k": Int(1), "alpha": C(0.05), "tau": C(0),
        "distance_normalization": C("range"), "label_parameters": CONV,
        "centers": C("excluded"), "interval": C("one-sided Wald, equation (10) of arXiv 2502.01267"),
        "n_complainants": Int(0), "n_cases": Int(0), "n_significant": Int(0),
    }, "Situation testing, ceteris paribus comparator only (algorithm of the addendum H5).")
    d["c21Outputs"] = Ob({
        "kind": C("year-pair"),
        "pair_id": S(pattern=r"^20(18|19|20|21|22|23)-(19|20|21|22|23|24)$"),
        "fit_year": Int(2018, 2023), "confirm_year": Int(2019, 2024),
        "scope": Ob({"state": S(), "source": S(), "rows_fit": Int(1), "rows_confirm": Int(1)}),
        "legal": R("c21Legal"),
        "licence": R("c21Licence"),
        "conventions": R("c21Conventions"),
        "attributes": A(R("c21Attribute"), 1),
        "situation_testing": R("c21Situation"),
        "data_notes": A(R("c21Note"), 1),
        "requirements": A(S(pattern=r"^CT-21\d\d$"), 1, desc="Requirement ids CT-2101 onward (decision Q14)."),
    }, "C21 year-pair outputs: statistical disparity on public HMDA decisions, fitted on year t and confirmed on t+1. No outcome-conditioned test runs: HMDA has no outcome (08 l.180-181).")
    d["c21Outputs"]["oneOf"] = [{"properties": {"pair_id": C(pid), "fit_year": C(fy), "confirm_year": C(cy)}} for pid, (fy, cy) in PAIRS.items()]
    d["c21Fit"] = Ob({
        "fields": A(Ob({"name": R("c21Hmda"), "role": E("attribute", "control", "outcome", "reason", "pricing", "flag"),
                        "alias": nullable(S())}), 1),
        "decision_models": A(Ob({"fit_year": Int(2018, 2023), "kind": E("logistic", "linear"), "outcome": E("approval", "rate_spread"),
                                 "n": Int(1), "converged": B,
                                 "terms": A(Ob({"term": S(), "coefficient": N(), "se": NONNEG}), 1)}), 1),
        "conventions": R("c21Conventions"), "legal": R("c21Legal"), "licence": R("c21Licence"),
        "data_notes": A(R("c21Note"), 1),
    }, "C21 models: the HMDA fields used (addendum H1 names), the fitted decision models and the conventions.")
    return d


# An allowlist (m3): the eight tests a C21 document may carry. The four outcome-conditioned ids, and every near-synonym, are outside it.
C21_ALLOWLIST = {"properties": {"tests": {"items": {"properties": {"test_id": E(*C21_TESTS)}}}}}
C21_RULES = [C21_ALLOWLIST]


def main() -> None:
    d = c02_defs()
    variant_schema("c02", "variant-horizon", "horizon", "C02 horizon variant",
                   "Catalog row c02-outputs 1.1.0: one horizon file (1 to 5 years) or the pooled variant of the corporate PD case (outputs.kind horizon).",
                   "c02Outputs", d, C02_RULES)
    models_schema("c02", "C02 models", "Catalog row c02-models 1.0.0: the five Polish files, the ladder and the leakage-safe protocol.", "c02Fit", d)
    d = c20_defs()
    for ref, kind, root, cid, what in [
        ("variant-shock", "shock", "c20Outputs", "c20-outputs", "SGCD seen and held-out shocks"),
        ("variant-shift", "shift", "c20OutputsShift", "c20-outputs-shift", "the Fed portfolios read both ways (decision Q7)"),
        ("variant-seeds", "seeds", "c20OutputsSeeds", "c20-outputs-seeds", "the seed sweep"),
        ("variant-perturbation", "perturbation", "c20OutputsPerturbation", "c20-outputs-perturbation", "the perturbation grid"),
        ("variant-leakage", "leakage", "c20OutputsLeakage", "c20-outputs-leakage", "the planted leakage"),
    ]:
        variant_schema("c20", ref, kind, f"C20 {kind} variant", f"Catalog row {cid} 1.0.0: {what} (outputs.kind {kind}).", root, d, C20_RULES)
    models_schema("c20", "C20 models", "Catalog row c20-models 1.0.0: the fitted rungs, the SGCD pin and the named parameters.", "c20Fit", d)
    d = c21_defs()
    variant_schema("c21", "variant-year-pair", "year-pair", "C21 year-pair variant",
                   "Catalog row c21-outputs 1.0.0: one HMDA year pair, fitted on year t and confirmed on t+1 (outputs.kind year-pair). No legal claim.",
                   "c21Outputs", d, C21_RULES)
    models_schema("c21", "C21 models", "Catalog row c21-models 1.0.0: the HMDA fields, the fitted decision models and the conventions.", "c21Fit", d)


if __name__ == "__main__":
    main()
