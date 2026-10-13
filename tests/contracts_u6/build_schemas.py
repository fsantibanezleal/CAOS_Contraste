"""Builds the six U6-S schema files (docs/contracts/schemas/c03, c08 and c09).

Run: ``python tests/contracts_u6/build_schemas.py``. Deterministic, standard library only. The schema files are the
contract and are committed; this script is the compact source they are written from, so a name two files of one case
share has one definition (the generator of the TypeScript types fails on a clash). Conventions of docs/contracts/catalog.md:
one folder per case, a ``case_id`` const, ``outputs.kind`` on every variant, case-prefixed ``$defs``, the
``variant-envelope`` composition with ``unevaluatedProperties: false``, every object closed, nothing optional.
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


def A(items: dict, minimum: int | None = None, desc: str | None = None) -> dict:
    d: dict = {"type": "array", "items": items}
    if minimum is not None:
        d["minItems"] = minimum
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
CUR = S("ISO 4217 code of the money fields of this block.", pattern="^[A-Z]{3}$")
DATE = S(pattern=r"^\d{4}-\d{2}-\d{2}$")
PD = N("An estimate-site PD is open: 0 < pd < 1.", exclusiveMinimum=0, exclusiveMaximum=1)
UNIT = N("A share or an observed rate in [0, 1].", minimum=0, maximum=1)
MONEY = N("Money in the `currency` of the enclosing block.")
LIGHT = E("green", "amber", "red", "not_evaluated", "error")
NAME_MAP = {
    "type": "object",
    "additionalProperties": False,
    "required": ["name", "value", "unit"],
    "properties": {"name": S(), "value": N(), "unit": S()},
}


def ranged(prefix: str, what: str) -> dict:
    """The {value, flag} wrapper of an LGD (C08) or a CCF (C09): in [0, 1] with the flag in-range, outside it only with
    the flag below-zero or above-one. The value is never clipped by the producer."""
    return {
        "description": f"A {what} with its range flag. In [0, 1] the flag is in-range; below 0 or above 1 (fees, costs, "
                       "overlimit drawings, limit changes) the value is kept and flagged, never silently clipped.",
        "oneOf": [
            Ob({"value": N(minimum=0, maximum=1), "flag": {"const": "in-range"}}),
            Ob({"value": N(exclusiveMaximum=0), "flag": {"const": "below-zero"}}),
            Ob({"value": N(exclusiveMinimum=1), "flag": {"const": "above-one"}}),
        ],
    }


def prediction(what: str) -> dict:
    """The wrapper of an estimate-site LGD (C08): inside [0, 1] by construction, so the flag is always in-range. The
    realised-LGD wrapper `ranged` keeps and flags values outside [0, 1]; a prediction never needs that."""
    return {
        "description": f"A {what} at an estimate site: always inside [0, 1] (SDD section 4: predictions inside [0, 1]), so "
                       "the flag is always in-range.",
        **Ob({"value": N(minimum=0, maximum=1), "flag": {"const": "in-range"}}),
    }


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
# common/test-result schema is outside U6-S's write scope, so the rule is composed here on the variant's `tests`; the
# integrator can move it to common/test-result as a contract bump.
NOT_EVALUATED_RULE = {
    "properties": {"tests": {"items": {
        "if": {"properties": {"light": {"const": "not_evaluated"}}, "required": ["light"]},
        "then": {"properties": {"statistic": {"type": "null"}, "p_value": {"type": "null"}, "metric": {"type": "null"},
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


# ----------------------------------------------------------------------------------------------------------- C03


def c03_defs() -> dict:
    d: dict = {}
    d["c03Cohort"] = Ob({
        "id": S(), "label": TXT,
        "first_fy": Int(1991, desc="First approval fiscal year of the test cohort (SBA fiscal years start on 1 October)."),
        "last_fy": Int(1991),
        "approval_fiscal_years": A(Int(1991), 1),
    }, "One test cohort of approval fiscal years (SDD section 5: FY2006-07, 2008-10, 2011-14, 2015-17, 2018-20).")
    d["c03Training"] = Ob({
        "first_fy": Int(1991), "last_fy": Int(1991),
        "cutoff_date": DATE,
        "n_loans": Int(0), "n_events": Int(0),
        "crisis_included": B,
        "rationale": TXT,
    }, "The training window (decision D1): strict out-of-time by approval fiscal year. It holds only approval cohorts whose "
       "5-year charge-off mark falls before the first approval date of the test cohort: last_fy <= cohort.first_fy - 6, and "
       "cutoff_date is at most 30 September of cohort.first_fy - 1. The 'trained through the crisis' claim (crisis_included) "
       "holds only for a test cohort from FY2011-14 on, whose training outcomes include the crisis-era charge-offs.")
    d["c03Target"] = Ob({
        "name": S(),
        "horizon_months": {"const": 60, "description": "Months from approval over which a charge-off counts: the 5-year target."},
        "observed_at_months": {"const": 60, "description": "The target is read for a vintage only at its 5-year mark (60 months after its last approval)."},
        "censoring": E("exempt-right-censored", "excluded"),
        "definition": TXT,
    }, "The 5-year charge-off target and how loans without an observed outcome (EXEMPT, still active) are handled.")
    d["c03DataStatus"] = Ob({
        "primary_source": S(),
        "files_as_of": DATE,
        "fiscal_year_start": S(desc="Month and day the SBA fiscal year starts (10-01)."),
        "notice": TXT,
    })
    d["c03VintageCurve"] = Ob({
        "fiscal_year": Int(1991),
        "n": Int(0),
        "gross_approval": N(minimum=0, description="Total gross approval of the vintage in the `currency` of the outputs."),
        "months": A(Int(1), 1, "Months since approval, strictly increasing."),
        "predicted_cumulative_pd": A(PD, 1),
        "observed_cumulative_pd": A(nullable(UNIT), 1, "Null where the horizon is beyond the observation cutoff."),
        "observed_until_month": Int(0, desc="Months from the last approval of the vintage to files_as_of."),
        "reason": nullable(S(), "Why the observed curve stops before the 5-year mark; null when it reaches it."),
    }, "The predicted and the observed cumulative charge-off PD of one approval-year vintage.")
    one_of(d["c03VintageCurve"],
           {"observed_until_month": Int(60), "reason": {"type": "null"}, "observed_cumulative_pd": A(UNIT, 1)},
           {"observed_until_month": Int(0, 59), "reason": S(minLength=1),
            "observed_cumulative_pd": {"type": "array", "contains": {"type": "null"}, "minContains": 1}})
    d["c03VintageRow"] = Ob({
        "fiscal_year": Int(1991),
        "n": Int(0), "n_resolved": Int(0), "n_exempt_censored": Int(0),
        "gross_approval": N(minimum=0),
        "five_year_mark_date": DATE,
        "mark_observed": B,
        "observed_5y_pd": nullable(UNIT, "Null when the vintage has not reached its 5-year mark; the reason says why."),
        "predicted_5y_pd": PD,
        "gap": nullable(N(), "Observed minus predicted at the 5-year mark; null when unobserved."),
        "brier": nullable(N(minimum=0)),
        "auc": nullable(UNIT),
        "reason": nullable(S()),
    }, "One vintage at its 5-year mark. five_year_mark_date is 30 September of fiscal_year + 5; mark_observed is true exactly "
       "when it is on or before data_status.files_as_of (a producer check). Observed: the PD, the gap and no reason. Unobserved: "
       "no PD, no gap, no brier, no auc, and the reason.")
    one_of(d["c03VintageRow"],
           {"mark_observed": {"const": True}, "observed_5y_pd": UNIT, "gap": N(), "reason": {"type": "null"}},
           {"mark_observed": {"const": False}, "observed_5y_pd": {"type": "null"}, "gap": {"type": "null"},
            "brier": {"type": "null"}, "auc": {"type": "null"}, "reason": S(minLength=1)})
    d["c03VintageSummary"] = Ob({"currency": CUR, "rows": A(R("c03VintageRow"), 1)})
    d["c03DecileRow"] = Ob({
        "decile": Int(1, 10), "n": Int(0),
        "predicted_pd": PD, "observed_pd": UNIT, "ci_low": UNIT, "ci_high": UNIT,
    })
    d["c03Calibration"] = Ob({
        "rung_id": S(),
        "scope": S(desc="The vintages pooled: those whose 5-year mark is observed."),
        "rows": A(R("c03DecileRow"), 1),
    })
    d["c03RungResult"] = Ob({
        "rung_id": S(),
        "auc": nullable(UNIT), "auc_ci_low": nullable(UNIT), "auc_ci_high": nullable(UNIT),
        "brier": nullable(N(minimum=0)),
        "calibration_gap_5y": nullable(N()),
        "reason": nullable(S()),
    })
    d["c03StabilityRow"] = Ob({"fiscal_year": Int(1991), "psi": N(minimum=0), "observed_5y_pd": nullable(UNIT)})
    d["c03Stability"] = Ob({
        "training_mean_5y_pd": UNIT,
        "psi_note": TXT,
        "rows": A(R("c03StabilityRow"), 1),
    }, "Population stability of each test vintage against the training window and its observed 5-year rate against the "
       "training mean (the crisis contrast).")
    d["c03Outputs"] = Ob({
        "kind": {"const": "vintage-cohort"},
        "currency": CUR,
        "cohort": R("c03Cohort"),
        "training": R("c03Training"),
        "target": R("c03Target"),
        "data_status": R("c03DataStatus"),
        "vintage_curves": A(R("c03VintageCurve"), 1),
        "vintage_summary": R("c03VintageSummary"),
        "calibration": R("c03Calibration"),
        "rung_comparison": A(R("c03RungResult"), 1),
        "stability": R("c03Stability"),
    }, "C03 vintage-cohort outputs (outputs.kind vintage-cohort): one test cohort of approval fiscal years. PD open (0, 1) at "
       "estimate sites; the 5-year charge-off target is observed only at each vintage's 5-year mark; a value the bake may lack "
       "is nullable with its reason; money in `currency`.")
    d["c03CohortWindow"] = Ob({
        "id": S(), "label": TXT, "first_fy": Int(1991), "last_fy": Int(1991),
        "training": R("c03Training"),
    }, "A test cohort with its own training window (decision D1): every variant trains only on approval cohorts whose 5-year "
       "mark precedes its first approval date.")
    d["c03Coefficient"] = Ob({"name": S(), "estimate": N(), "std_error": nullable(N(minimum=0))})
    d["c03Rung"] = Ob({
        "rung_id": S(),
        "kind": E("constant", "woe-scorecard", "penalised-logit", "pltr", "ebm", "monotone-gbm", "tabpfn"),
        "covariates": A(S()), "coefficients": A(R("c03Coefficient")),
        "training_cutoff": DATE, "engine": S(),
    }, "A PD rung of the existing engine ladder (docs/design/features/c01-retail-pd/design.md rungs P0 to P5), fitted on a "
       "training window; training_cutoff is that of the latest cohort window, the earlier windows' cutoffs sit in cohort_windows.")
    d["c03VintageDefinition"] = Ob({"basis": S(), "fiscal_year_start": S(), "label": TXT})
    d["c03Fit"] = Ob({
        "currency": CUR,
        "vintage_definition": R("c03VintageDefinition"),
        "target": R("c03Target"),
        "cohort_windows": A(R("c03CohortWindow"), 1),
        "ladder": A(R("c03Rung"), 1),
        "data_status": R("c03DataStatus"),
    }, "C03 models: the vintage definition, the target, the five test cohorts each with its own training window, and the PD rungs.")
    return d


# ----------------------------------------------------------------------------------------------------------- C08

# The 12 LGD floor cells of dossier 01 section A.5: id, portfolio, collateral, floor, reference. The dossier cites
# CRE32.58 to CRE32.59 jointly for the retail cells, so the split between the two paragraphs is not asserted.
FLOOR_CELLS = [
    ("corporate-unsecured", "corporate", "unsecured", 0.25, "CRE32.16"),
    ("corporate-financial", "corporate", "financial", 0.0, "CRE32.16"),
    ("corporate-receivables", "corporate", "receivables", 0.10, "CRE32.16"),
    ("corporate-real-estate", "corporate", "real-estate", 0.10, "CRE32.16"),
    ("corporate-other-physical", "corporate", "other-physical", 0.15, "CRE32.16"),
    ("retail-mortgage", "retail", "mortgage", 0.05, "CRE32.58 to CRE32.59"),
    ("retail-qrre", "retail", "qrre", 0.50, "CRE32.58 to CRE32.59"),
    ("retail-other-unsecured", "retail", "unsecured", 0.30, "CRE32.58 to CRE32.59"),
    ("retail-other-financial", "retail", "financial", 0.0, "CRE32.58 to CRE32.59"),
    ("retail-other-receivables", "retail", "receivables", 0.10, "CRE32.58 to CRE32.59"),
    ("retail-other-real-estate", "retail", "real-estate", 0.10, "CRE32.58 to CRE32.59"),
    ("retail-other-physical", "retail", "other-physical", 0.15, "CRE32.58 to CRE32.59"),
]

C08_TEXT = Ob({"en": S(minLength=1), "es": S(minLength=1)})


def c08_defs() -> dict:
    d: dict = {}
    d["c08Text"] = C08_TEXT
    d["c08Lgd"] = ranged("c08", "realised loss given default")
    d["c08LgdPrediction"] = prediction("predicted loss given default")
    d["c08Cohort"] = Ob({"id": S(), "label": TXT, "first_year": Int(1990), "last_year": Int(1990)},
                       "One default cohort by default year (SDD section 5: 2003-06, 2007-08, 2009-10, 2011-13, 2014-19, 2020-23).")
    d["c08LgdProxy"] = Ob({
        "definition": R("c08Text"),
        "formula": S("The proxy as a formula over SBA 7(a) field names.", minLength=1),
        "source_field": {"const": "GrossChargeOffAmount", "description": "The SBA 7(a) field the numerator reads."},
        "exposure_field": {"const": "GrossApproval",
                           "description": "The SBA 7(a) field the denominator reads: the gross approved amount, the only exposure "
                                          "field the file carries (decision D2)."},
        "recovery_cash_flows_available": B,
        "bias_direction": {"const": "downward", "description": "The proxy LGD is biased low (decision D2)."},
        "bias_statement": R("c08Text"),
    }, "The LGD proxy of the SBA charge-off twin and its bias, required in every C08 document: the file has no recovery "
       "cash flows, so the proxy is the gross charge-off amount over the gross approved amount (GrossApproval), not a workout "
       "LGD (dossier 08 A.6). The approved amount overstates the exposure at default of an amortising loan, so the proxy is "
       "biased low (decision D2).")

    def status(available: bool) -> dict:
        return Ob({
            "primary_source": S(),
            "freddie_mac_available": {"const": available},
            "freddie_mac_reason": S(minLength=1) if not available else {"type": "null"},
            "notice": TXT,
        })

    d["c08DataStatus"] = {
        "description": "Freddie Mac is a nullable slot: while the owner's account does not exist it is unavailable and the "
                       "reason is stated; no number stands in for it.",
        "oneOf": [status(False), status(True)],
    }
    d["c08Training"] = Ob({
        "cutoff_date": DATE, "n_defaults": Int(0), "n_open_workouts_excluded": Int(0), "closure_rule": TXT,
    }, "Out-of-time by default date; the training set holds only defaults whose workout closed before the cutoff.")
    d["c08Workout"] = Ob({
        "discount_rate_convention": E("eba-interbank-plus-5pp", "fixed", "none-proxy"),
        "discount_rate": nullable(N(minimum=0)),
        "incomplete_workouts": Ob({
            "treatment": E("excluded", "projected", "not-applicable"),
            "n_excluded": Int(0), "n_projected": Int(0),
            "reason": nullable(S()),
        }),
        "note": TXT,
    }, "How realised LGD is built: a workout LGD discounts recoveries (rate convention EBA/GL/2017/16, paragraph UNVERIFIED); "
       "the SBA twin has no cash flows, so none-proxy, no discount rate and not-applicable.")
    one_of(d["c08Workout"],
           {"discount_rate_convention": {"const": "none-proxy"}, "discount_rate": {"type": "null"},
            "incomplete_workouts": {"properties": {"treatment": {"const": "not-applicable"}}}},
           {"discount_rate_convention": E("eba-interbank-plus-5pp", "fixed"), "discount_rate": N(minimum=0),
            "incomplete_workouts": {"properties": {"treatment": E("excluded", "projected")}}})
    d["c08Exposure"] = Ob({
        "currency": CUR,
        "gross_charge_off_total": N(minimum=0),
        "gross_approval_total": N(minimum=0, description="Sum of GrossApproval over the cohort, the proxy denominator."),
    })
    d["c08Bin"] = Ob({"lower": N(minimum=0, maximum=1), "upper": N(minimum=0, maximum=1), "n": Int(0), "share": UNIT})
    d["c08Mass"] = Ob({"n": Int(0), "share": UNIT})
    d["c08Distribution"] = Ob({
        "n": Int(0),
        "treatment": {"const": "flagged-not-clipped"},
        "bins": A(R("c08Bin"), 2),
        "mass_at_zero": R("c08Mass"),
        "mass_at_one": R("c08Mass"),
        "n_below_zero": Int(0), "share_below_zero": UNIT,
        "n_above_one": Int(0), "share_above_one": UNIT,
        "lowest": R("c08Lgd"), "highest": R("c08Lgd"),
        "mean": R("c08Lgd"), "median": R("c08Lgd"),
    }, "The realised LGD distribution on [0, 1] with its masses at 0 and 1; realised values outside [0, 1] are counted and "
       "flagged, never clipped into the end bins.")
    d["c08RungResult"] = Ob({
        "rung_id": S(),
        "r2": nullable(N(maximum=1)), "rmse": N(minimum=0), "mae": N(minimum=0),
        "spearman": nullable(N(minimum=-1, maximum=1)),
        "calibration_gap": N(),
        "reason": nullable(S()),
    })
    d["c08RealisedRow"] = Ob({
        "rung_id": S(), "cohort_id": S(), "n": Int(0),
        "realised": R("c08Lgd"), "predicted": R("c08LgdPrediction"),
        "ci_low": N(), "ci_high": N(), "gap": N(),
    })
    d["c08BucketRow"] = Ob({
        "rung_id": S(), "bucket": Int(1), "n": Int(0), "predicted": R("c08LgdPrediction"), "realised": R("c08Lgd"),
    })
    d["c08EndpointRow"] = Ob({
        "rung_id": S(),
        "epsilon": N(exclusiveMinimum=0, exclusiveMaximum=0.5),
        "mean_predicted": R("c08LgdPrediction"),
        "rmse": N(minimum=0),
    })
    d["c08DownturnPeriod"] = Ob({
        "first_year": Int(1990), "last_year": Int(1990), "indicator": S(), "macro_source": S(),
    })
    d["c08DownturnRow"] = Ob({
        "cohort_id": S(), "n": Int(0),
        "long_run_lgd": R("c08Lgd"), "downturn_lgd": R("c08Lgd"),
        "add_on": N(desc="downturn_lgd minus long_run_lgd."),
        "crisis_realised_lgd": R("c08Lgd"),
        "covered": B,
        "shortfall": N(minimum=0),
    })
    d["c08DownturnCoverage"] = Ob({"n_cohorts": Int(0), "share_covered": UNIT})
    d["c08Downturn"] = Ob({
        "period": R("c08DownturnPeriod"),
        "approach": TXT,
        "rows": A(R("c08DownturnRow"), 1),
        "coverage": R("c08DownturnCoverage"),
    }, "The downturn add-on against the realised crisis losses (dossier 04 F.4: Contraste's own cohort-based add-on, an "
       "illustration, not a regulatory estimate; the EBA/GL/2019/03 wording is UNVERIFIED).")
    d["c08FloorRow"] = Ob({
        "segment_id": S(), "floor_id": S(),
        "floor": UNIT, "reference": S(minLength=1),
        "n": Int(0), "share_binding": UNIT,
        "mean_before": R("c08LgdPrediction"), "mean_after": R("c08LgdPrediction"),
        "uplift": N(minimum=0, description="mean_after minus mean_before, never negative."),
    }, "The bite of one floor cell; (floor_id, floor, reference) is one of the 12 transcribed cells.")
    one_of(d["c08FloorRow"], *[{"floor_id": {"const": i}, "floor": {"const": f}, "reference": {"const": ref}}
                               for i, _p, _c, f, ref in FLOOR_CELLS])
    d["c08FloorsBite"] = Ob({
        "regime": S(), "rows": A(R("c08FloorRow"), 1),
        "note": TXT,
    }, "How much the IRB LGD floors (Basel III final, CRE32.16, CRE32.58 to CRE32.59) bind on the estimates.")
    d["c08Outputs"] = Ob({
        "kind": {"const": "default-cohort"},
        "currency": CUR,
        "cohort": R("c08Cohort"),
        "lgd_proxy": R("c08LgdProxy"),
        "data_status": R("c08DataStatus"),
        "training": R("c08Training"),
        "workout": R("c08Workout"),
        "exposure": R("c08Exposure"),
        "lgd_distribution": R("c08Distribution"),
        "rung_comparison": A(R("c08RungResult"), 1),
        "realised_vs_predicted": A(R("c08RealisedRow"), 1),
        "calibration_by_bucket": A(R("c08BucketRow"), 1),
        "endpoint_sensitivity": A(R("c08EndpointRow"), 2, "Two epsilons at least, for the beta rungs (SDD section 4)."),
        "downturn": R("c08Downturn"),
        "floors_bite": R("c08FloorsBite"),
    }, "C08 default-cohort outputs (outputs.kind default-cohort): one test default cohort. LGD in [0, 1] with the cases outside it "
       "(fees, costs) allowed and flagged, never clipped; the LGD proxy definition and bias statement are required; money in "
       "`currency`.")
    d["c08Coefficient"] = Ob({"name": S(), "estimate": N(), "std_error": nullable(N(minimum=0))})
    d["c08RungSpec"] = Ob({
        "rung_id": S(),
        "kind": E("ols", "fractional-logit", "beta", "hurdle", "tobit", "gradient-boosted", "cure-decomposition"),
        "covariates": A(S()),
        "coefficients": A(R("c08Coefficient")),
        "epsilon": nullable(N(exclusiveMinimum=0, exclusiveMaximum=0.5), "The endpoint transformation of beta rungs; null elsewhere."),
        "training_cutoff": DATE,
        "library": S(), "library_version": S(),
    })
    d["c08FloorCell"] = Ob({
        "id": S(), "portfolio": E("corporate", "retail"),
        "collateral": E("unsecured", "financial", "receivables", "real-estate", "other-physical", "qrre", "mortgage"),
        "floor": UNIT, "reference": S(minLength=1),
    })
    one_of(d["c08FloorCell"], *[{"id": {"const": i}, "portfolio": {"const": p}, "collateral": {"const": c},
                                 "floor": {"const": f}, "reference": {"const": ref}} for i, p, c, f, ref in FLOOR_CELLS])
    d["c08Floors"] = Ob({"regime": S(), "cells": A(R("c08FloorCell"), 1), "source": S()},
                       "The LGD floor cells transcribed from dossier 01 section A.5.")
    d["c08DownturnSpec"] = Ob({"approach": TXT, "period": R("c08DownturnPeriod")})
    d["c08Fit"] = Ob({
        "currency": CUR,
        "lgd_proxy": R("c08LgdProxy"),
        "data_status": R("c08DataStatus"),
        "cohorts": A(R("c08Cohort"), 1),
        "training": R("c08Training"),
        "workout": R("c08Workout"),
        "ladder": A(R("c08RungSpec"), 1),
        "downturn": R("c08DownturnSpec"),
        "floors": R("c08Floors"),
    }, "C08 models: the LGD proxy and its bias, the default cohorts, the rungs, the downturn specification and the floor cells.")
    return d


# ----------------------------------------------------------------------------------------------------------- C09


def c09_defs() -> dict:
    d: dict = {}
    d["c09Ccf"] = ranged("c09", "credit conversion factor")
    d["c09Convention"] = Ob({
        "name": {"const": "eu-undrawn"},
        "definition": TXT,
        "formula": S(),
        "us_terms": TXT,
    }, "The CCF convention, named on every view: the EU convention, the share of the undrawn amount drawn by default "
       "(the LEQ in US terms); Qi (2009) calls EAD over outstanding the CCF.")
    d["c09Generator"] = Ob({
        "name": S(), "shaped_on": S(),
        "true_ccf": R("c09Ccf"),
        "acceleration_factor": N(minimum=0),
        "acceleration_window_months": Int(0),
        "notice": TXT,
    }, "The revolving-line generator with a known CCF; its field structure and marginals follow the Fed 2025 hypothetical card portfolios.")
    d["c09ReplicationSet"] = Ob({
        "seeds": A(Int(0), 1), "n_replications": Int(1), "n_facilities": Int(1), "n_defaults": Int(0),
    })
    d["c09Replications"] = Ob({"development": R("c09ReplicationSet"), "test": R("c09ReplicationSet")},
                             "Independent simulated development and test replications with fixed seeds, disjoint between the two sets.")
    d["c09CcfRow"] = Ob({
        "design": E("fixed-horizon", "cohort", "variable-horizon"),
        "treatment": E("none", "censor", "floor-cap", "bounded-scale"),
        "estimator": E("mean", "pooled"),
        "estimate": R("c09Ccf"), "truth": R("c09Ccf"),
        "bias": N(desc="estimate minus truth."),
        "rmse": N(minimum=0),
        "ci_low": N(), "ci_high": N(),
        "n_defaults": Int(0),
        "share_below_zero": UNIT, "share_above_one": UNIT,
        "within_tolerance": B,
    }, "One CCF estimate against the known truth. After a censor or floor-cap treatment the estimate lies inside [0, 1] and "
       "is flagged in-range; an untreated estimate may be flagged outside it.")
    one_of(d["c09CcfRow"],
           {"treatment": E("censor", "floor-cap"), "estimate": {"properties": {"flag": {"const": "in-range"}}}},
           {"treatment": E("none", "bounded-scale")})
    d["c09CcfByDesign"] = Ob({
        "tolerance": N(minimum=0, description="The error within which the known CCF counts as recovered."),
        "rows": A(R("c09CcfRow"), 1),
    })
    d["c09Distribution"] = Ob({
        "design": E("fixed-horizon", "cohort", "variable-horizon"),
        "n": Int(0),
        "edges": A(N(), 3, "Bin edges, strictly increasing, the first below 0 and the last above 1."),
        "counts": A(Int(0), 2),
        "n_below_zero": Int(0), "n_above_one": Int(0),
    }, "The estimated CCF histogram with its mass below 0 and above 1 kept.")
    d["c09EadModel"] = Ob({
        "model_id": S(),
        "kind": E("ccf-fixed-horizon", "ccf-cohort", "ccf-variable-horizon", "direct-ead", "utilisation-change"),
        "design": nullable(E("fixed-horizon", "cohort", "variable-horizon")),
        "treatment": nullable(E("none", "censor", "floor-cap", "bounded-scale")),
        "covariates": A(S()),
        "n_clipped_below": nullable(Int(0), "direct-ead only: observations whose EADF below 0 was clipped for the fit; null elsewhere."),
        "n_clipped_above": nullable(Int(0), "direct-ead only: observations whose EADF above 1 was clipped for the fit; null elsewhere."),
    }, "An EAD model of the ladder; the clipped counts of fit_direct_ead are reported here, never silently.")
    one_of(d["c09EadModel"],
           {"kind": {"const": "direct-ead"}, "n_clipped_below": Int(0), "n_clipped_above": Int(0)},
           {"kind": E("ccf-fixed-horizon", "ccf-cohort", "ccf-variable-horizon", "utilisation-change"),
            "n_clipped_below": {"type": "null"}, "n_clipped_above": {"type": "null"}})
    d["c09BacktestRow"] = Ob({
        "model_id": S(), "band_id": S(),
        "utilisation_lower": N(minimum=0), "utilisation_upper": N(minimum=0),
        "n": Int(0),
        "predicted_ead": N(description="Sum of the predicted EAD of the band. Negative only with prediction_flag outside-range."),
        "prediction_flag": E("in-range", "outside-range"),
        "realised_ead": N(minimum=0),
        "gap": N(desc="predicted_ead minus realised_ead, in currency."),
        "relative_gap": N(),
        "light": LIGHT,
    }, "One model in one utilisation band. A utilisation-change prediction is not clipped: prediction_flag is outside-range "
       "when any facility of the band has an unclipped prediction below 0 or above its limit (api predict_ead).")
    one_of(d["c09BacktestRow"],
           {"prediction_flag": {"const": "in-range"}, "predicted_ead": N(minimum=0)},
           {"prediction_flag": {"const": "outside-range"}})
    d["c09EadBacktest"] = Ob({
        "currency": CUR, "bands": A(N(), 2, "Utilisation band edges."), "rows": A(R("c09BacktestRow"), 1),
    }, "EAD back-testing in currency by utilisation band, not only the CCF.")
    d["c09FloorRow"] = Ob({
        "facility_class": S(), "sa_ccf": UNIT, "reference": S(minLength=1),
        "n": Int(0), "share_binding": UNIT,
        "mean_ead_before": N(minimum=0), "mean_ead_after": N(minimum=0),
    })
    d["c09EadFloor"] = Ob({
        "currency": CUR, "rule": S(), "off_balance_share": UNIT, "rows": A(R("c09FloorRow"), 1),
    }, "The IRB EAD floor: on-balance amount plus 50% of the off-balance exposure at the SA CCF (CRE32.36, CRE32.64).")
    d["c09SmallUndrawn"] = Ob({
        "currency": CUR, "threshold": N(minimum=0), "applied": B, "n_switched": Int(0), "reference": S(),
    }, "The small-undrawn rule of Qi (2009): below the threshold the EAD ratio replaces the unstable CCF.")
    d["c09Outputs"] = Ob({
        "kind": {"const": "acceleration-level"},
        "level": Int(0, 5, "Utilisation acceleration level, 0 (none) to 5."),
        "level_description": TXT,
        "currency": CUR,
        "convention": R("c09Convention"),
        "generator": R("c09Generator"),
        "replications": R("c09Replications"),
        "ccf_by_design": R("c09CcfByDesign"),
        "ccf_distribution": R("c09Distribution"),
        "ead_models": A(R("c09EadModel"), 1),
        "ead_backtest": R("c09EadBacktest"),
        "ead_floor": R("c09EadFloor"),
        "small_undrawn": R("c09SmallUndrawn"),
    }, "C09 acceleration-level outputs (outputs.kind acceleration-level): one utilisation acceleration level. CCF in the EU convention; "
       "values outside [0, 1] allowed and flagged; the known truth sits beside every estimate; money in `currency`.")
    d["c09Marginal"] = Ob({"field": S(), "distribution": S(), "parameters": A(NAME_MAP), "source": S()})
    d["c09Level"] = Ob({"level": Int(0, 5), "label": TXT, "acceleration_factor": N(minimum=0),
                       "acceleration_window_months": Int(0)})
    d["c09Plan"] = Ob({"development_seeds": A(Int(0), 1), "test_seeds": A(Int(0), 1), "n_facilities": Int(1)})
    d["c09Design"] = Ob({
        "design": E("fixed-horizon", "cohort", "variable-horizon"),
        "horizon_months": nullable(Int(1)), "n_reference": nullable(Int(1)), "step_months": nullable(Int(1)),
        "label": TXT,
    })
    d["c09SupervisoryCcf"] = Ob({"item": S(), "ccf": UNIT, "reference": S(minLength=1)})
    d["c09Floors"] = Ob({"off_balance_share": UNIT, "reference": S(), "supervisory_ccfs": A(R("c09SupervisoryCcf"), 1)})
    d["c09Fit"] = Ob({
        "currency": CUR,
        "convention": R("c09Convention"),
        "generator": R("c09Generator"),
        "marginals": A(R("c09Marginal"), 1),
        "levels": A(R("c09Level"), 6),
        "replications_plan": R("c09Plan"),
        "designs": A(R("c09Design"), 3),
        "treatments": A(E("none", "censor", "floor-cap", "bounded-scale"), 1),
        "ead_models": A(R("c09EadModel"), 1),
        "small_undrawn": R("c09SmallUndrawn"),
        "floors": R("c09Floors"),
    }, "C09 models: the generator with its known CCF, the marginals from the Fed 2025 hypothetical portfolios, the six acceleration "
       "levels, the reference-date designs, the treatments, the EAD models and the floors.")
    return d


def main() -> None:
    d3, d8, d9 = c03_defs(), c08_defs(), c09_defs()
    variant_schema("C03", "variant-vintage-cohort", "vintage-cohort", "C03 vintage-cohort variant",
                   "Catalog row c03-outputs 1.0.0: one test cohort of approval fiscal years of the SME PD by vintage case "
                   "(outputs.kind vintage-cohort), on the SBA 7(a) data.", "c03Outputs", d3)
    models_schema("C03", "C03 models",
                  "Catalog row c03-models 1.0.0: the C03 models artifact (vintage definition, target, training window, test cohorts, PD rungs).",
                  "c03Fit", d3)
    variant_schema("C08", "variant-default-cohort", "default-cohort", "C08 default-cohort variant",
                   "Catalog row c08-outputs 1.0.0: one default cohort of the LGD and downturn LGD case (outputs.kind default-cohort), "
                   "on the SBA charge-off twin.", "c08Outputs", d8)
    models_schema("C08", "C08 models",
                  "Catalog row c08-models 1.0.0: the C08 models artifact (LGD proxy and bias, cohorts, rungs, downturn specification, floor cells).",
                  "c08Fit", d8)
    variant_schema("C09", "variant-acceleration-level", "acceleration-level", "C09 acceleration-level variant",
                   "Catalog row c09-outputs 1.0.0: one utilisation acceleration level of the EAD and CCF case "
                   "(outputs.kind acceleration-level), on a generator with a known CCF.", "c09Outputs", d9)
    models_schema("C09", "C09 models",
                  "Catalog row c09-models 1.0.0: the C09 models artifact (generator and known CCF, marginals, levels, designs, EAD models, floors).",
                  "c09Fit", d9)


if __name__ == "__main__":
    main()
