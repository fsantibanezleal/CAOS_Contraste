"""Builds the U14-S fixtures (docs/contracts/fixtures/c02, c20, c21): small, schema-valid, plainly labelled fixtures.

Run: ``python tests/contracts_u14/build_fixtures.py`` (needs scipy for the two exact tests of the C21 fixture). Every number is an
illustration of a shape, never a result: ids start with ``fixture-``, the provenance generator is ``fixture:u14-s-contracts`` and the
input source is ``fixture-not-a-result``.
"""
from __future__ import annotations

import json
import math
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from values import (  # noqa: E402
    C02_NAMES,
    C20_NAMES,
    FAIR_TESTS,
    FHA_DISPARATE_IMPACT,
    HMDA_DATE_RULE,
    HMDA_ID_RULE,
    HMDA_MODIFIED,
    HMDA_PLATFORM_TERMS,
    LEGAL,
    NAMED,
    NON_GROUPS,
    QUOTES,
    SGCD_COMMIT,
    SGCD_QUOTE,
)

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "docs" / "contracts" / "fixtures"


def t(en: str, es: str | None = None) -> dict:
    return {"en": en, "es": es or en}


PROV = {"truth_status": "synthetic-calibrated",
        "inputs": [{"source": "fixture-not-a-result", "class": "fixture", "files": []}],
        "licence_classes": {"fixture-not-a-result": "fixture"}, "generators": ["fixture:u14-s-contracts"], "seed": 0,
        "code_version": "fixture", "riskvalidation_version": None}
LANE = {"lane": "precompute", "reasons": ["fixture"]}


def test_row(test_id: str = "disc.auc", model_id: str | None = "fixture-p1") -> dict:
    return {"test_id": test_id, "model_id": model_id, "segment": None, "statistic": None, "p_value": None, "metric": None,
            "h0": "fixture row", "alternative": "fixture row", "policy_version": "fixture", "alpha_amber": None, "alpha_red": None,
            "light": "not_evaluated", "n": None, "n_events": None, "inputs_hash": "0" * 64, "reference": "fixture, not a result",
            "notes": "fixture: the test did not run, no number stands in for it", "extras": {}}


def model_summary(mid: str, rung: str) -> dict:
    return {"id": mid, "family": "ml", "rung": rung, "title": t(f"Fixture model {mid}"), "short_title": t(mid), "engine": "riskvalidation",
            "engine_version": "fixture", "licence": "MIT", "calibration": None, "parameters": {}, "checkpoint_sha256": None}


def model_record(mid: str, rung: str) -> dict:
    return {**model_summary(mid, rung), "details": {}}


def variant(case: str, vid: str, outputs: dict, impact: dict, models: list[dict], tests: list[dict]) -> dict:
    return {"schema": "contraste.case/v1", "case_id": case, "variant_id": vid, "model": models, "outputs": outputs, "tests": tests,
            "impact": impact, "findings": [], "provenance": PROV, "lane": LANE}


def models_doc(case: str, fit_id: str, fit: dict) -> dict:
    return {"schema": "contraste.models/v1", "case_id": case, "fit_id": fit_id, "model": [model_record("fixture-p1", "P1")],
            "fit": fit, "provenance": PROV, "lane": LANE}


def impact_item(value: float, unit: str, en: str) -> dict:
    return {"value": value, "unit": unit, "label": t(en)}


def params(names: list[str]) -> list[dict]:
    return [{"name": n, "value": NAMED[n][0], "unit": NAMED[n][1], "label": "convention", "basis": NAMED[n][2]} for n in names]


def write(case: str, name: str, doc: dict) -> None:
    p = FIX / case / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------------------------------- C02
def split(rows: int) -> dict:
    return {"protocol": "locked-stratified-holdout", "seed": 0, "train_rows": int(rows * 0.6), "calibration_rows": int(rows * 0.2),
            "holdout_rows": rows - int(rows * 0.6) - int(rows * 0.2), "holdout_events": 60, "fit_on_training_slice_only": True,
            "calibration_map_on_separate_slice": True, "resampling_before_calibration": False, "out_of_time_claim": False}


def rung(rung_id: str, auc: float) -> dict:
    return {"model_id": f"fixture-{rung_id.lower()}", "rung": rung_id,
            "roc": {"fpr": [0.0, 0.1, 0.3, 1.0], "tpr": [0.0, 0.4, 0.7, 1.0]},
            "cap": {"population": [0.0, 0.2, 0.5, 1.0], "defaults": [0.0, 0.5, 0.8, 1.0], "default_rate": 0.0386},
            "reliability": [{"n": 200, "pd": p, "dr": d, "lo": max(d - 0.02, 0.0), "hi": d + 0.02}
                            for p, d in ((0.01, 0.012), (0.02, 0.019), (0.04, 0.045), (0.08, 0.07), (0.2, 0.22))],
            "discrimination": {"auc": auc, "auc_ci": {"lo": auc - 0.03, "hi": auc + 0.03, "level": 0.95, "method": "delong"},
                               "gini": round(2 * auc - 1, 6), "ks": 0.4},
            "calibration": {"brier": 0.04, "ece": 0.01, "hosmer_lemeshow": {"statistic": 8.5, "df": 8, "p_value": 0.39}},
            "overfit": {"train_auc": auc + 0.02, "holdout_auc": auc, "gap": 0.02, "tolerance": 0.05, "flag": False},
            "stability": {"psi": 0.03, "csi_max": 0.05}}


def c02_outputs(horizon: str, years: int | None, rows: int, events: int) -> dict:
    pooled = horizon == "pooled"
    return {
        "kind": "horizon", "horizon_id": horizon, "years": years,
        "counts": {"rows": rows, "events": events, "event_rate": round(events / rows, 6), "features": 64,
                   "event_definition": t("Bankruptcy within the horizon (the file's class label)")},
        "pooled": ({"files": [{"file": f"fixture-{y}year", "years": y, "rows": 1000 * y, "events": 40 * y} for y in range(1, 6)],
                    "horizon_indicator": True, "overlap": t("Firm overlap across the five files is unknown")} if pooled else None),
        "firm_overlap_caveat": t("The five files may repeat firms; the overlap is unknown") if pooled else None,
        "split": split(rows),
        "rungs": [rung("P1", 0.82), rung("P4", 0.88)],
        "challenger": [{"champion": "fixture-p1", "challenger": "fixture-p4", "auc_diff": 0.06,
                        "auc_diff_ci": {"lo": 0.01, "hi": 0.11, "level": 0.95, "method": "delong"}, "delong_p_value": 0.02,
                        "brier_diff": -0.002, "brier_diff_ci": {"lo": -0.004, "hi": 0.0, "level": 0.95, "method": "paired-bootstrap"},
                        "grade_disagreement_share": 0.12}],
        "transfer": {"label": "exploratory", "reason": t("The firm overlap across files is unknown, so a transfer AUC may be inflated"),
                     "cells": [] if pooled else [{"rung": "P1", "model_id": "fixture-p1", "fitted_on_years": 1, "scored_on_years": 2, "auc": 0.78, "n": 900, "events": 40}]},
        "term_structure": None if pooled else {
            "label": "exploratory", "reason": t("Five file event rates read as a cumulative PD; the files may not draw one population"),
            "points": [{"years": y, "cumulative_pd": c, "hazard": h} for y, c, h in
                       [(1, 0.0386, 0.0386), (2, 0.0393, 0.00073), (3, 0.0471, 0.00812), (4, 0.0526, 0.00577), (5, 0.0694, 0.01773)]],
            "cumulative_nondecreasing": True,
            "source": "engine-provisions-api from_cumulative and lifetime_pd_backtest (04 E.2 l.479-497)"},
        "term_structure_reason": t("The five files are independent samples of different forecast years, not one cohort followed through time; their "
                                   "rates fall with the horizon, so no cumulative PD is read from them (fixture)") if pooled else None,
        "impact_detail": {"label": "exploratory", "reason": t("ECL effect of the horizon PDs on an illustrative exposure"),
                          "source": "engine-provisions-api", "pd_basis": t("P1 horizon PDs, fixture", "PD por horizonte de P1, fixture"),
                          "lgd": {"value": 0.45, "label": "assumption"}, "ecl_12m_effect": 1.0, "ecl_lifetime_effect": 2.5,
                          "unit": t("index, fixture", "índice, fixture"), "reason_if_null": None},
        "parameters": params(C02_NAMES), "requirements": ["CT-0201"],
    }


def c02() -> None:
    imp = {"ecl_12m_effect": impact_item(1.0, "index", "12-month ECL effect (exploratory)"),
           "ecl_lifetime_effect": impact_item(2.5, "index", "Lifetime ECL effect (exploratory)")}
    ms = [model_summary("fixture-p1", "P1"), model_summary("fixture-p4", "P4")]
    write("c02", "variant-horizon-h1-fixture.json", variant("C02", "fixture-h1", c02_outputs("h1", 1, 7027, 271), imp, ms, [test_row()]))
    write("c02", "variant-horizon-pooled-fixture.json", variant("C02", "fixture-pooled", c02_outputs("pooled", None, 15000, 600), imp, ms, [test_row()]))
    files = [{"horizon_id": f"h{y}", "years": y, "file": f"fixture-{y}year", "rows": 1000 * y, "events": 40 * y} for y in range(1, 6)]
    write("c02", "models-fixture.json", models_doc("C02", "fixture-ladder", {
        "files": files, "ladder": [{"rung": r, "label": t(f"Fixture rung {r}"), "engine": "fixture", "reference": "04 B"} for r in ("P0", "P1", "P4")],
        "protocol": split(5000), "parameters": params(C02_NAMES)}))


# ---------------------------------------------------------------------------------------------------- C20
def metric(delta: float = -0.02) -> dict:
    return {"auc": 0.74, "brier": 0.18, "auc_delta": delta}


def battery() -> dict:
    rows = []
    for tid in FAIR_TESTS:
        for attr in ("sex", "age", "marital_status"):
            rows.append({"test_id": tid, "attribute": attr, "value": 0.03,
                         "groups": [{"group": "g1", "n": 1000, "value": 0.7}, {"group": "g2", "n": 900, "value": 0.67}], "light": "green"})
    return {"label": "labelled-fairness-battery", "model": "uci-taiwan",
            "notice": t("Fixture rows. The battery is labelled evidence on the Taiwan model, not a compliance statement"), "rows": rows}


SGCD_NOTICE = {"kind": "dataset-card-prohibition", "quote": SGCD_QUOTE, "commit": SGCD_COMMIT,
               "text": t("The SGCD dataset card forbids real-world credit scoring and production decisions about individuals")}


def core(kind: str, dataset: str, model_dataset: str) -> dict:
    return {"kind": kind, "dataset_id": dataset, "model_dataset": model_dataset,
            "sgcd_notice": SGCD_NOTICE if dataset == "sgcd" else None,
            "parameters": params(C20_NAMES),
            "fairness_battery": battery() if model_dataset == "uci-taiwan" else None,
            "impact_detail": {"label": "decision-flip",
                              "cutoff": {"rule": "reject-worst-share-of-baseline-scores", "reject_share": 0.2, "label": "convention"},
                              "rows": [{"shift_id": "fixture-shift", "flip_share": 0.07, "n_decisions": 1000}]},
            "requirements": ["CT-2001"]}


def shock_row(sid: str, batches: list[str], reach: int) -> dict:
    return {"shock_id": sid, "batches": batches, "n_records": 50, "n_reaching_structured_view": reach, "performance": metric(),
            "drift": {"psi_max": 0.08, "csi_max": 0.12, "chi2_p_value": 0.2,
                      "variables": [{"name": "annual_salary", "psi": 0.08, "csi": 0.12, "chi2_p_value": 0.2},
                                    {"name": "committed_exposure", "psi": 0.03, "csi": 0.05, "chi2_p_value": None}]}, "data_quality": {"completeness": 0.97, "consistency": None},
            "attribution_rank_correlation": 0.8}


def c20() -> None:
    imp = {"decision_flip_share": impact_item(0.07, "share", "Decisions that flip at the stated cut-off")}
    ms = [model_summary("fixture-p1", "P1")]

    def doc(kind: str, ds: str, md: str, extra: dict, vid: str) -> dict:
        return variant("C20", vid, {**core(kind, ds, md), **extra}, imp, ms, [test_row("stability.psi")])

    shock = {"seen_or_held_out": "seen", "model_view": "json_view",
             "shipped": {"label": "shipped", "rows": [shock_row("F1", ["T1", "T2", "T3"], 10), shock_row("F2", ["T1", "T2", "T3"], 0)],
                         "parameters_source": None},
             "applied": {"label": "contraste-applied", "rows": [shock_row("F1", ["A1"], 10)], "parameters_source": "SGCDataset_metadata.json, seed 42"}}
    write("c20", "variant-shock-fixture.json", doc("shock", "sgcd", "uci-german", shock, "fixture-sgcd-seen"))
    variables = [{"name": "committed_exposure", "psi": 0.2, "csi": 0.25, "ks": 0.18, "chi2_p_value": 0.01}]
    shift = {"real_drift": {"label": "real-drift-no-model", "model": None, "portfolios": ["typical", "higher-risk", "lower-risk"],
                            "pairs": [{"a": "typical", "b": "higher-risk", "variables": variables}]},
             "synthetic_shift": {"label": "synthetic-shift-fed-reference", "reference_portfolio": "higher-risk", "evaluation_set": "fixture-uci-polish-holdout",
                                 "shifts": [{"shift_id": "fixture-shift", "score": 0.3, "metric": metric(), "psi": 0.15, "flip_share": 0.07}],
                                 "worst_subsample": {"share": 0.1, "metric": metric(-0.08)},
                                 "label_free": {"conformal": {"label": "convention", "alpha": 0.1, "target_coverage": 0.9, "coverage": 0.86, "binomial_p_value": 0.03,
                                                             "coverage_by_window": [{"window": "fixture-w1", "n": 500, "coverage": 0.9, "binomial_p_value": 0.9},
                                                                                    {"window": "fixture-w2", "n": 500, "coverage": 0.82, "binomial_p_value": 0.001}]},
                                                "cbpe": {"label": "estimate", "estimated_auc": 0.71, "assumptions": [
                                                    {"id": i, "text": t(i)} for i in ("calibrated-probabilities", "no-concept-drift", "no-extrapolation", "adequate-sample")]}}}}
    write("c20", "variant-shift-fixture.json", doc("shift", "fed-2025-corporate", "uci-polish", shift, "fixture-fed-shift"))
    seeds = {"rows": [{"rung": "P4", "n_seeds": 20, "auc": {"mean": 0.77, "sd": 0.004, "min": 0.76, "max": 0.78},
                       "grade_assignment_changed_share": 0.1, "attribution_rank_tau": {"mean": 0.9, "min": 0.8},
                       "reason_code_overlap": {"top_k": 4, "n_refits": 100, "mean": 0.85, "p05": 0.7}}],
             "explainer_agreement": [{"rung": "P4", "effect_reference": "ale", "n_features": 23, "rank_correlation": 0.82, "reason_if_null": None,
                                      "top_features": [{"feature": "PAY_0", "shap_importance": 0.41, "effect_range": 0.22,
                                                        "ale": {"edges": [-2.0, 0.0, 1.0, 2.0], "effect": [-0.05, 0.02, 0.09]}}]}]}
    write("c20", "variant-seeds-fixture.json", doc("seeds", "uci-taiwan", "uci-taiwan", seeds, "fixture-seeds"))
    pert = {"preset_eps": 0.1, "rows": [{"eps": e, "metric": metric(-0.01 * e), "finding": False} for e in (0.05, 0.1, 0.25)]}
    write("c20", "variant-perturbation-fixture.json", doc("perturbation", "uci-taiwan", "uci-taiwan", pert, "fixture-perturbation"))
    leak = {"planted_feature": "fixture_leak",
            "thresholds": {"single_feature_auc": {"value": 0.95, "label": "convention"}, "resemblance_auc": {"value": 0.7, "label": "convention"}},
            "screen": {"temporal_order": {"violations": 0},
                                                           "single_feature_auc": {"max_auc": 0.99, "feature": "fixture_leak", "suspect": True},
                                                           "entity_overlap": {"share": 0.0}, "resemblance_auc": 0.55},
            "caught": True, "performance": {"development_auc": 0.99, "decision_time_auc": 0.75}}
    write("c20", "variant-leakage-fixture.json", doc("leakage", "uci-taiwan", "uci-taiwan", leak, "fixture-leakage"))
    write("c20", "models-fixture.json", models_doc("C20", "fixture-ladder", {
        "datasets": [{"id": "sgcd", "rows": 1000, "role": "shock evaluation"}, {"id": "uci-taiwan", "rows": 30000, "role": "fit"}],
        "ladder": [{"rung": "P4", "engine": "fixture", "dataset": "uci-taiwan"}],
        "sgcd": {"commit": SGCD_COMMIT, "seed": 42, "notice": SGCD_NOTICE}, "parameters": params(C20_NAMES)}))


# ---------------------------------------------------------------------------------------------------- C21
def two_prop(a: int, na: int, b: int, nb: int) -> tuple[float, float, float, float]:
    from scipy import stats
    p1, p2 = a / na, b / nb
    pp = (a + b) / (na + nb)
    z = (p1 - p2) / math.sqrt(pp * (1 - pp) * (1 / na + 1 / nb))
    pz = math.erfc(abs(z) / math.sqrt(2))
    odds, pf = stats.fisher_exact([[a, na - a], [b, nb - b]])
    return z, pz, float(odds), float(pf)


DEFAULT_SPEC = {
    "derived_sex": ([("Male", 880, 1000), ("Female", 480, 600)], "Male"),
    "derived_race": ([("White", 880, 1000), ("Asian", 920, 1000), ("Black or African American", 420, 600)], "White"),
    "derived_ethnicity": ([("Not Hispanic or Latino", 880, 1000), ("Hispanic or Latino", 480, 600)], "Not Hispanic or Latino"),
    "applicant_age": ([("35-44", 880, 1000), ("25-34", 480, 600)], "35-44"),
}


def four_fifths(spec: list[tuple[str, int, int]]) -> dict:
    """The four-fifths block of one attribute: each group against the highest-rate group, decided on the counts (exact arithmetic)."""
    top = max(spec, key=lambda g: Fraction(g[1], g[2]))  # the first group of the highest rate on a tie
    rows = []
    for name, x, n in spec:
        ratio = None if top[1] == 0 else float(Fraction(x, n) / Fraction(top[1], top[2]))
        rows.append({"group": name, "ratio_to_highest": ratio, "flag": 5 * x * top[2] < 4 * top[1] * n})
    return {"label": "employment benchmark", "citation": "29 CFR 1607.4(D)", "threshold": 0.8, "is_credit_law_threshold": False,
            "compared_with": "highest-rate-group", "decided_on": "exact-counts", "rule": "flag when 5 * x_g * n_h < 4 * x_h * n_g",
            "highest_rate_group": top[0], "groups": rows}


def c21_attribute(field: str, spec: list[tuple[str, int, int]] | None = None, reference: str | None = None) -> dict:
    """One attribute from (group, approved, n) counts; a contrast per group against the reference group (default: the first)."""
    if spec is None:
        spec, reference = DEFAULT_SPEC[field]
    reference = reference or spec[0][0]
    counts = {g: (x, n) for g, x, n in spec}
    ref_a, ref_n = counts[reference]
    basis, ecoa, fha = LEGAL[field]
    r_r = ref_a / ref_n
    ci = {"lo": -0.9, "hi": -0.1, "level": 0.95}
    controls = ["debt_to_income_ratio", "combined_loan_to_value_ratio", "income", "loan_amount", "property_value", "loan_type"]
    contrasts = []
    for grp_name, g_a, g_n in spec:
        if grp_name == reference:
            continue
        z, pz, odds, pf = two_prop(g_a, g_n, ref_a, ref_n)
        r_g = g_a / g_n
        ratio = None if ref_a == 0 else r_g / r_r
        contrasts.append({
            "group": grp_name, "reference_group": reference, "n_group": g_n, "n_reference": ref_n,
            "selection_rate_group": r_g, "selection_rate_reference": r_r, "parity_gap": r_g - r_r, "parity_ratio": ratio,
            "adverse_impact_ratio": {"value": ratio, "note": t("The adverse impact ratio against the chosen reference group")},
            "z_test": {"statistic": z, "p_value": pz}, "fisher_exact": {"odds_ratio": odds, "p_value": pf},
            "controlled": {"estimate": {"model": "logistic-decision-model", "outcome": "approval", "coefficient": -0.5, "odds_ratio": math.exp(-0.5),
                                        "ci": ci, "n": g_n + ref_n, "controls": controls, "missing_controls": ["credit_score"],
                                        "label": "approximation of comparative evidence"}, "reason": None},
            "rate_spread": {"estimate": {"model": "linear-rate-spread", "population": "action_taken 1 or 2", "coefficient": 0.1,
                                         "ci": {"lo": 0.02, "hi": 0.18, "level": 0.95}, "n": 1200, "controls": controls,
                                         "missing_controls": ["credit_score"], "label": "approximation of comparative evidence",
                                         "unit": "percentage points of rate_spread"}, "reason": None},
            "confirmation": {"estimate": {"fit_year": 2018, "confirm_year": 2019, "fit_coefficient": -0.5, "confirm_coefficient": -0.4,
                                          "same_sign": True, "size_ratio": 0.8}, "reason": None},
        })
    return {
        "field": field,
        "legal": {"basis": basis, "ecoa": ecoa, "fha": fha, "theory": "comparative-evidence-of-disparate-treatment",
                  "fha_disparate_impact": FHA_DISPARATE_IMPACT[field],
                  "note": t("Mapping taken from the research addendum H3 section 5; no legal claim")},
        "reference_group": reference,
        "groups": [{"group": g, "n": n, "n_approved": x, "n_denied": n - x, "selection_rate": x / n} for g, x, n in spec],
        "excluded_groups": [{"group": NON_GROUPS[field][0], "n": 50, "reason": t("Not a protected group: carried as its own group, excluded from the pairwise tests")}],
        "four_fifths": four_fifths(spec),
        "contrasts": contrasts,
    }


CONVENTIONS = {"label": "convention",
               "outcome": {"approval_codes": [1, 2], "denial_codes": [3], "excluded_codes": [4, 5, 6, 7, 8],
                           "note": t("approval = originated or approved not accepted, denial = denied; the rest have no decision")},
               "dti_recode": {"bins": ["<20%", "20%-<30%", "30%-<36%", "36", "50%-60%", ">60%"],
                              "note": t("The mixed exact and binned field is recoded to the published bins")},
               "group_exclusion": t("Joint, Not Available and Free Form Text Only categories are excluded from the pairwise tests"),
               "identifiers": {"id": HMDA_ID_RULE, "observation_date": HMDA_DATE_RULE, "label": "convention",
                               "note": t("Public HMDA withholds the loan identifier and the dates: id is the row position within the activity year, the date is the activity year's last day")}}
LICENCE = {"status": "UNVERIFIED", "platform_terms": HMDA_PLATFORM_TERMS, "platform_terms_cover": "the software package, not the published datasets",
           "modified_statement": HMDA_MODIFIED, "note": t("The HMDA data licence sentence is UNVERIFIED; the views quote the platform software terms and the CFPB statement")}
NOTES = [{"field": "debt_to_income_ratio", "treatment": "binned", "n_missing": None, "reason": t("Binned outside 36 to 49 percent in the public release")},
         {"field": "loan_amount", "treatment": "rounded", "n_missing": None, "reason": t("Rounded to the midpoint of a $10,000 interval")}]


def c21_legal() -> dict:
    def s(k: str) -> dict:
        return {"citation": QUOTES[k][0], "quote": QUOTES[k][1], "text": t(QUOTES[k][1])}
    return {"label": {"en": "no legal claim", "es": "sin afirmación legal"}, "regulation_b": s("reg_b"), "fair_housing_act": s("fha"),
            "procedures": s("procedures"), "unconditional_rates_are": "indicators-only",
            "controlled_disparity_is": "approximation-of-comparative-evidence", "is_a_finding_of_violation": False}


def c21() -> None:
    out = {"kind": "year-pair", "pair_id": "2018-19", "fit_year": 2018, "confirm_year": 2019,
           "scope": {"state": "fixture-state", "source": "fixture-not-a-result", "rows_fit": 2000, "rows_confirm": 2100},
           "legal": c21_legal(), "licence": LICENCE, "conventions": CONVENTIONS, "attributes": [c21_attribute("derived_sex"), c21_attribute("derived_race")],
           "situation_testing": {"label": "situation-testing", "comparator": "ceteris-paribus",
                                 "counterfactual_test": {"run": False, "reason": t("Public HMDA gives no counterfactual dataset")},
                                 "attribute": "derived_sex", "k": 30, "alpha": 0.05, "tau": 0, "distance_normalization": "range", "label_parameters": "convention", "centers": "excluded",
                                 "interval": "one-sided Wald, equation (10) of arXiv 2502.01267", "n_complainants": 600, "n_cases": 80, "n_significant": 20},
           "data_notes": NOTES, "requirements": ["CT-2101"]}
    write("c21", "variant-year-pair-fixture.json",
          variant("C21", "fixture-2018-19", out, {}, [model_summary("fixture-p1", "P1")], [test_row("fair.demographic_parity")]))
    write("c21", "models-fixture.json", models_doc("C21", "fixture-2018", {
        "fields": [{"name": "action_taken", "role": "outcome", "alias": None}, {"name": "derived_sex", "role": "attribute", "alias": None},
                   {"name": "combined_loan_to_value_ratio", "role": "control", "alias": "loan_to_value_ratio"}],
        "decision_models": [{"fit_year": 2018, "kind": "logistic", "outcome": "approval", "n": 2000, "converged": True,
                             "terms": [{"term": "derived_sex=Female", "coefficient": -0.5, "se": 0.2}]}],
        "conventions": CONVENTIONS, "legal": c21_legal(), "licence": LICENCE, "data_notes": NOTES}))


if __name__ == "__main__":
    c02()
    c20()
    c21()
