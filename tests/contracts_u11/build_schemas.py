"""Builds the three U11-S schema files (docs/contracts/schemas/c16).

Run: ``python tests/contracts_u11/build_schemas.py``. Deterministic, standard library only. The schema files are the contract and
are committed; this script is the compact source they are written from, so a name two files of the case share has one definition
(the generator of the TypeScript types fails on a clash). Conventions of docs/contracts/catalog.md: one folder per case, a
``case_id`` const, ``outputs.kind`` on every variant, case-prefixed ``$defs``, the ``variant-envelope`` composition with
``unevaluatedProperties: false``, every object closed, nothing optional (a value the bake may lack is nullable with its reason).

Transcribed from the U11 research addendum (L1 the ECB LiST 2019 tables, L3 the FDIC field names, L4 the Federal Reserve margins),
dossier 05 E (the ladder, Table A.1 rows), dossier 01 G (the LCR caps) and the sizing decisions Q1 to Q14 and A1 to A6 of
plans/contraste/units/U11-sizing.md. Every named parameter (a convention, Q13 and Q14) is a required field with its value and the
label "convention", never "regulatory".
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "docs" / "contracts" / "schemas"
BASE = "https://contraste.fasl-work.com/contracts/"
TXT = {"$ref": "../common/text.schema.json"}

VARIANTS = ["lcr-standard", "list-adverse", "list-extreme", "fast-run", "htm-losses"]
SEGMENTS = ["retail-insured", "retail-uninsured", "operational", "non-operational-corporate", "financial"]
LIST_CLASSES = ["stable-retail", "other-retail", "operational", "non-operational-credit-institutions",
                "non-operational-other-financial", "non-operational-non-financial-corporates", "non-operational-others"]
LCR_CATEGORIES = ["retail_stable", "retail_less_stable", "operational", "non_financial_corporate", "other_legal_entity"]   # the engine keys
CBC_CLASSES = ["cash-and-balances", "treasury", "mortgage-backed", "other-agency", "municipal", "other-debt"]
HAIRCUT_RULES = ["nominal-value", "central-bank-framework", "lcr-haircut-hqla", "fifty-percent-fallback", "ecb-equity-table",
                 "ecb-non-equity-hqla"]
PHASES = ["acute", "protracted"]
LCR_PHASE = "lcr-30-day"   # the 30-calendar-day stress of LCR20.2: outside the acute (1 to 5 days) and protracted (6 to 12 months) wording of 05 l.277
PARAMETER_SETS = ["basel-lcr", "list-adverse", "list-extreme", "fast-run"]
SOURCE_KINDS = ["transcribed-list-2019", "transcribed-basel-lcr", "calibrated-pre-2023", "convention", "synthetic-stated",
                "scenario-input"]
DURATION_BUCKETS = ["0-1", ">1-3", ">3-5", ">5-10", ">10", "none"]

# The LCR rows of a document are the keys of the engine tables (liquidity-api.md, transcribed from dossier 01 G.1: LCR20, LCR40, LCR99):
# the rate of a row is the table rate; trade finance is a caller-supplied rate within 0 to 0.05 (national discretion), never a default.
LCR_OUTFLOW_RATES: dict[str, float] = {
    "retail_stable_insurance_criteria": 0.03, "retail_stable": 0.05, "retail_less_stable": 0.1, "retail_term_gt_30d": 0.0,
    "small_business_stable": 0.05, "small_business_less_stable": 0.1, "operational": 0.25, "operational_insured_portion": 0.05,
    "cooperative_network": 0.25, "non_financial_corporate": 0.4, "non_financial_corporate_fully_insured": 0.2,
    "other_legal_entity": 1.0, "secured_central_bank": 0.0, "secured_level1": 0.0, "secured_level2a": 0.15,
    "secured_sovereign_mdb_pse": 0.25, "secured_level2b_rmbs": 0.25, "secured_other_level2b": 0.5, "secured_other": 1.0,
    "non_level1_collateral_valuation": 0.2, "undrawn_retail_small_business": 0.05,
    "undrawn_credit_non_financial_corporate": 0.1, "undrawn_liquidity_non_financial_corporate": 0.3,
    "undrawn_credit_supervised_bank": 0.4, "undrawn_liquidity_supervised_bank": 0.4, "undrawn_credit_other_fi": 0.4,
    "undrawn_liquidity_other_fi": 1.0, "undrawn_other_legal_entity": 1.0, "net_derivative_outflow": 1.0,
    "other_contractual_outflow": 1.0,
}
LCR_INFLOW_RATES: dict[str, float] = {
    "secured_lending_level1": 0.0, "secured_lending_level2a": 0.15, "secured_lending_level2b_rmbs": 0.25,
    "secured_lending_other_level2b": 0.5, "secured_lending_other": 1.0, "margin_lending_other_collateral": 0.5,
    "facilities_granted_to_bank": 0.0, "operational_deposits_at_other_institutions": 0.0,
    "retail_and_nonfinancial_wholesale": 0.5, "financial_institutions_and_central_banks": 1.0, "net_derivative_inflow": 1.0,
}
LCR_OUTFLOW_KEYS = list(LCR_OUTFLOW_RATES) + ["trade_finance"]
LCR_INFLOW_KEYS = list(LCR_INFLOW_RATES)

# The call-report field names a document may name: the U11 research addendum L3 and L3.2, and the C14 field list (cases/c14/fetch.py).
CALL_REPORT_FIELDS = sorted({
    "SC", "SCHA", "SCHF", "SCAA", "SCAF", "DEPUNA", "DEPINS", "DEPSMAMT", "DEPLGAMT", "CHBAL", "FREPO", "FREPP", "OTHBFHLB",
    "SCUST", "SCUS", "SCAGE", "SCASPNSUM", "SCASPNHA", "SCASPNAF", "SCSPN", "SCMTGBK", "SCGTY", "SCCOL", "SCCMOT", "SCMUNI",
    "SCDOMO", "SCFORD", "SCRDEBT", "SCEQFV", "SCPLEDGE", "SCHTMRES", "DEP", "DEPDOM", "DEPFOR", "ASSET", "LIAB", "EQ", "RBCT1J",
    "LNLSNET", "CERT", "REPDTE", "NAME",
    # the maturity-band and other fields the ladder reads (U11-P integration item 5; the list of cases/c16/fetch.py FDIC_FIELDS)
    "DEPNIDOM", "DEPIDOM", "DEPNIFOR", "DEPIFOR", "DEPSMB", "DEPLGB", "NTRTIME", "CD3LES", "CD3T12", "CD1T3", "CDOV3", "CD3LESS",
    "CD3T12S", "CD1T3S", "CDOV3S", "SCNM3LES", "SCNM3T12", "SCNM1T3", "SCNM3T5", "SCNM5T15", "SCNMOV15", "SCPT3LES", "SCPT3T12",
    "SCPT1T3", "SCPT3T5", "SCPT5T15", "SCPTOV15", "SCO3YLES", "SCOOV3Y", "LNLSGR", "LNATRES", "LNRS3LES", "LNRS3T12", "LNRS1T3",
    "LNRS3T5", "LNRS5T15", "LNRSOV15", "LNOT3LES", "LNOT3T12", "LNOT1T3", "LNOT3T5", "LNOT5T15", "LNOTOV15", "OTHBFH1L", "OTBFH1T3",
    "OTBFH3T5", "OTBFHOV5", "OTHBRF", "OTBOT1L", "OTBOT1T3", "OTBOT3T5", "OTBOTOV5", "SUBND",
})

LIST_CONTRACTUAL = [  # N Table 3.2 (addendum L1.1): item, baseline, adverse, extreme
    ("securities-issued", 1.0, 1.0, 1.0), ("secured-funding", 1.0, 1.0, 1.0),
    ("stable-retail", 0.0, 0.18, 0.27), ("other-retail", 0.0, 0.39, 0.48), ("operational", 0.0, 0.37, 0.50),
    ("non-operational-credit-institutions", 1.0, 1.0, 1.0), ("non-operational-other-financial", 1.0, 1.0, 1.0),
    ("non-operational-non-financial-corporates", 0.0, 0.52, 0.76), ("non-operational-others", 0.0, 0.52, 0.76),
    ("fx-swaps", 1.0, 1.0, 1.0), ("derivatives-payable", 1.0, 1.0, 1.0), ("other-cash-outflows", 1.0, 1.0, 1.0),
]
LIST_OPEN = [  # N Table 3.3 (addendum L1.3): class, baseline, adverse, extreme, daily rates as decimals
    ("open-repos", 1.0, 1.0, 1.0), ("stable-retail", 0.0, 0.00103258, 0.00161494), ("other-retail", 0.0, 0.00373218, 0.00440873),
    ("operational", 0.0, 0.00514464, 0.00750509), ("non-operational-credit-institutions", 1.0, 1.0, 1.0),
    ("non-operational-other-financial", 1.0, 1.0, 1.0), ("non-operational-non-financial-corporates", 0.0, 0.00688541, 0.01065229),
    ("non-operational-others", 0.0, 0.00688541, 0.01065229), ("other-transactions", 1.0, 1.0, 1.0),
]
LIST_INFLOWS = [  # N Table 3.2 inflows (addendum L1.2)
    ("secured-lending", 1.0, 1.0, 1.0), ("loans-retail", 0.0, 0.0, 0.0), ("loans-non-financial-corporates", 0.0, 0.0, 0.0),
    ("loans-credit-institutions", 1.0, 1.0, 1.0), ("loans-other-financial", 1.0, 1.0, 1.0), ("loans-others", 0.0, 0.0, 0.0),
    ("fx-swaps", 1.0, 1.0, 1.0), ("derivatives-receivable", 1.0, 1.0, 1.0), ("paper-own-portfolio", 1.0, 1.0, 1.0),
    ("other-cash-inflows", 1.0, 1.0, 1.0),
]
LIST_DRAWDOWN = [("committed-credit-facilities", 0.00202704, 0.00257634), ("liquidity-facilities", 0.01443904, 0.02176434)]
TABLE_A1 = [  # d555 Table A.1 (addendum L2.1; dossier 05 E.2): row id, bank, year, outflow share, days
    ("svb-2023", "SVB", 2023, 0.85, 2), ("first-republic-2023", "First Republic", 2023, 0.57, 90),
    ("svb-uk-2023", "SVB UK", 2023, 0.30, 1), ("credit-suisse-2023", "Credit Suisse", 2023, 0.21, 90),
    ("signature-2023", "Signature", 2023, 0.20, 1), ("icesave-2008", "Icesave", 2008, 0.20, 75),
    ("northern-rock-2007", "Northern Rock", 2007, 0.20, 4), ("wamu-2008", "WaMu", 2008, 0.10, 10),
    ("indymac-2008", "IndyMac", 2008, 0.08, 14),
]
GOLDENS = [  # the compounding goldens of the models document: id, daily rate, days, label (only the Adverse 125 days is printed, 05 l.237)
    ("stable-retail-adverse", 0.00103258, 125, "dossier-05-line-237"), ("stable-retail-extreme", 0.00161494, 125, "recomputed"),
    ("other-retail-adverse", 0.00373218, 125, "recomputed"), ("non-operational-nfc-adverse-2-days", 0.00688541, 2, "recomputed"),
    ("committed-credit-facilities-adverse-63-days", 0.00202704, 63, "recomputed"),
]
A1_IDS = [r[0] for r in TABLE_A1]
CALIBRATED_ON = ["icesave-2008", "northern-rock-2007", "wamu-2008", "indymac-2008"]
SCORED_ON = ["svb-2023", "first-republic-2023", "svb-uk-2023", "credit-suisse-2023", "signature-2023"]

CONVENTION_NAMES = [
    "deposit_category_mapping", "variant_scenarios", "day_calendar", "cbc_securities_mapping", "monetisation_schedule",
    "fast_run_calibration_rule", "cliff_days", "contractual_bucket_edges_days", "event_horizon_days", "uninsured_share_grid",
    "htm_loss_multiple_grid", "runoff_multiplier_grid", "reverse_target_days", "list_compounding_tolerance",
    "monotonicity_tolerance_days", "nlp_identity_tolerance", "cliff_amber_threshold", "cliff_red_threshold",
    "scoring_ratio_green", "scoring_ratio_amber", "generator_truth_se_green", "generator_truth_se_red",
    "htm_revaluation_green", "htm_revaluation_amber", "round_trip_tolerance_days", "cbc_haircut_band",
]
SCALARS = {n for n in CONVENTION_NAMES if n in (
    "event_horizon_days", "reverse_target_days", "list_compounding_tolerance", "monotonicity_tolerance_days", "nlp_identity_tolerance",
    "cliff_amber_threshold", "cliff_red_threshold", "scoring_ratio_green", "scoring_ratio_amber", "generator_truth_se_green",
    "generator_truth_se_red", "htm_revaluation_green", "htm_revaluation_amber", "round_trip_tolerance_days", "cbc_haircut_band")}
GRIDS = {"contractual_bucket_edges_days", "uninsured_share_grid", "htm_loss_multiple_grid", "runoff_multiplier_grid"}


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


def C(value) -> dict:
    return {"const": value}


B = {"type": "boolean"}
CUR = S("ISO 4217 code of the money fields of this document.", pattern="^[A-Z]{3}$")
DATE = S(pattern=r"^\d{4}-\d{2}-\d{2}$")
UNIT = N("A share or a rate in [0, 1].", minimum=0, maximum=1)
MONEY = N("Money in USD thousands as the call report gives it (the document's `currency` and `units.money_scale`).")
LIGHT3 = E("green", "amber", "red")
CALLFIELD = E(*CALL_REPORT_FIELDS)
LIQ_CLASS = E("level_1", "level_2a", "level_2b", "non_hqla")
LABEL = R("c16Label")

NOT_EVALUATED_RULE = {
    "properties": {"tests": {"items": {
        "if": {"properties": {"light": {"const": "not_evaluated"}}, "required": ["light"]},
        "then": {"properties": {"statistic": {"type": "null"}, "p_value": {"type": "null"}, "metric": {"type": "null"},
                                "notes": {"type": "string", "minLength": 1}}},
    }}},
}
LIQ_IDS_RULE = {"properties": {"tests": {"items": {"properties": {"test_id": {"type": "string", "pattern": r"^liq\."}}}}}}


def one_of(ob: dict, *alternatives: dict) -> dict:
    ob["oneOf"] = [{"properties": a} for a in alternatives]
    return ob


def pin(name: str, **consts) -> dict:
    """An element of an ordered array: the def with some properties fixed to constants."""
    return {"$ref": f"#/$defs/{name}", "properties": {k: ({"const": v} if not isinstance(v, dict) else v) for k, v in consts.items()}}


def ordered(items: list, desc: str | None = None) -> dict:
    d: dict = {"type": "array", "prefixItems": items, "items": False, "minItems": len(items), "maxItems": len(items)}
    if desc:
        d["description"] = desc
    return d


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


def write(name: str, doc: dict) -> None:
    path = SCHEMAS / "c16" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def variant_schema(ref: str, kind: str, title: str, desc: str, root: str, defs: dict, impact: list[str]) -> None:
    write(f"{ref}.schema.json", {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{BASE}c16/{ref}.schema.json",
        "title": title,
        "description": desc,
        "allOf": [
            {"$ref": "../common/variant-envelope.schema.json"},
            {"properties": {"case_id": {"const": "C16"},
                            "outputs": {"$ref": f"#/$defs/{root}", "properties": {"kind": {"const": kind}}}},
             "required": ["case_id", "outputs"]},
            NOT_EVALUATED_RULE,
            LIQ_IDS_RULE,
            {"properties": {"impact": {"required": impact}}},
        ],
        "unevaluatedProperties": False,
        "$defs": reachable(root, defs),
    })


def models_schema(title: str, desc: str, root: str, defs: dict) -> None:
    write("models.schema.json", {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{BASE}c16/models.schema.json",
        "title": title,
        "description": desc,
        "allOf": [
            {"$ref": "../common/models-envelope.schema.json"},
            {"properties": {"case_id": {"const": "C16"}, "fit": {"$ref": f"#/$defs/{root}"}}, "required": ["case_id", "fit"]},
        ],
        "unevaluatedProperties": False,
        "$defs": reachable(root, defs),
    })


# ------------------------------------------------------------------------------------------------------ shared blocks


def conventions(d: dict) -> None:
    status = C("convention")
    d["c16Scalar"] = Ob({"value": N(), "unit": S(minLength=1), "status": status, "basis": TXT},
                        "A named scalar parameter: its value, its unit and the label \"convention\" (never \"regulatory\"); the "
                        "basis says where the proposed value comes from (Q14: proposed by U11-S, approved by the main session).")
    d["c16Grid"] = Ob({"values": A(N(), 2), "unit": S(minLength=1), "status": status, "basis": TXT},
                      "A named grid: its values in increasing order, its unit and the label \"convention\".")
    d["c16MappingRow"] = Ob({
        "basis": E("insured", "uninsured"), "role": E("central", "band"), "lcr_category": E(*LCR_CATEGORIES),
        "list_class": E(*LIST_CLASSES), "label": TXT,
    }, "One mapping of a call-report deposit balance (insured or uninsured, DEPINS and DEPUNA) to an LCR category and a LiST class.")
    d["c16DepositMapping"] = Ob({
        "status": status,
        "rows": ordered([pin("c16MappingRow", basis="insured", role="central"), pin("c16MappingRow", basis="uninsured", role="central")],
                        "The central mapping: insured to a retail class, uninsured to one class."),
        "sensitivity_band": A(pin("c16MappingRow", basis="uninsured", role="band"), 3,
                              desc="The classes the uninsured balance may plausibly belong to (Q13): operational, non-financial "
                                   "corporate, other legal entity; the LCR variant reports its ratio under each."),
        "basis": TXT,
    }, "The deposit-category mapping with its sensitivity band (Q13): the call report carries no customer type, so every mapping is "
       "an assumption and a convention.")
    d["c16VariantRow"] = Ob({
        "variant": E(*VARIANTS), "scenario_family": E("idiosyncratic", "market-wide", "combined"), "phase": E(*PHASES, LCR_PHASE),
        "parameter_set": E(*PARAMETER_SETS), "horizon_days": Int(1), "axis": E("relevant-days", "calendar-days"),
    }, "The scenario family, phase, parameter set and horizon of one variant (dossier 05 E.2 and E.5); the LCR variant's phase is "
       "lcr-30-day, the 30-calendar-day stress of LCR20.2, and no other variant takes it.")
    d["c16VariantScenarios"] = Ob({
        "status": status, "rows": ordered([pin("c16VariantRow", variant=v, phase=C(LCR_PHASE) if v == "lcr-standard" else E(*PHASES)) for v in VARIANTS]),
        "basis": TXT,
    }, "The mapping of each variant to a scenario family and phase (Q14), in the order of the five scenario variants.")
    d["c16DayCalendar"] = Ob({
        "status": status, "kind": C("us-business-days"), "first_day": DATE, "excluded_weekdays": A(E("saturday", "sunday"), 2, 2),
        "holidays": A(DATE), "holiday_rule": S(minLength=1), "basis": TXT,
    }, "The ladder's day calendar (A2): US business days from the day after the valuation date. The LiST rates are defined on the "
       "2019 TARGET2 relevant-day calendar, so every LiST cumulative figure says which calendar it is on.")
    d["c16SecurityRow"] = Ob({
        "class_id": E(*CBC_CLASSES), "fed_category": S(minLength=1), "duration_bucket": E(*DURATION_BUCKETS),
        "margin": nullable(UNIT), "haircut": UNIT, "haircut_low": UNIT, "haircut_high": UNIT, "rule": E(*HAIRCUT_RULES),
        "source": S(minLength=1),
    }, "The central bank framework row a securities class takes (A3, A4): the Federal Reserve discount window margin in force on "
       "2023-03-10, the duration bucket a convention, the haircut 1 - margin and its sensitivity band; a class the framework does "
       "not cover has a null margin and the fallback rule (LCR haircut if HQLA, else 50 percent).")
    d["c16SecurityMapping"] = Ob({"status": status, "rows": A(R("c16SecurityRow"), 1), "basis": TXT},
                                 "The securities classes of the CBC with their haircut rows (A3, A4).")
    d["c16Point"] = Ob({"day": Int(1), "cumulative_share": UNIT})
    d["c16Monetisation"] = Ob({
        "status": status, "points": A(R("c16Point"), 1),
        "sensitivity_band": A(Ob({"id": S(minLength=1), "points": A(R("c16Point"), 1)}), 1), "basis": TXT,
    }, "The monetisation schedule of the CBC (Q6): the cumulative share of its liquidity value usable by day, with its band.")
    d["c16CalibrationRule"] = Ob({
        "status": status, "rule": E("maximum-implied-daily-rate", "median-implied-daily-rate", "mean-implied-daily-rate"),
        "basis": TXT,
    }, "How the fast-run daily rate is taken from the implied daily rates of the pre-2023 Table A.1 rows (the dossiers give no method).")
    d["c16CliffDays"] = Ob({
        "status": status, "near": C(30), "far": C(35), "day_basis": E("relevant-days", "calendar-days"), "basis": TXT,
    }, "The two days of the cliff diagnostic (NLP(35) - NLP(30)) / TA (05 E.1); whether they count calendar or relevant days is "
       "UNVERIFIED in the LiST note, so the basis is a convention.")
    special = {"deposit_category_mapping": "c16DepositMapping", "variant_scenarios": "c16VariantScenarios",
               "day_calendar": "c16DayCalendar", "cbc_securities_mapping": "c16SecurityMapping",
               "monetisation_schedule": "c16Monetisation", "fast_run_calibration_rule": "c16CalibrationRule",
               "cliff_days": "c16CliffDays"}
    props: dict = {}
    for name in CONVENTION_NAMES:
        props[name] = R("c16Scalar" if name in SCALARS else "c16Grid" if name in GRIDS else special[name])
    d["c16Conventions"] = Ob(props, "Every named parameter of the case (Q13, Q14): the deposit mapping with its band, the variant "
                                    "scenarios, the day calendar, the CBC haircut rows and monetisation schedule, the calibration "
                                    "rule, the cliff days, the grids, the reverse-stress target, the tolerances and the lights of "
                                    "the tests. Each carries the label \"convention\"; none is a regulatory threshold. The same in "
                                    "every document of one bake.")


def common() -> dict:
    d: dict = {}
    d["c16Label"] = Ob({"en": S(minLength=1), "es": S(minLength=1)}, "A non-empty bilingual label (an empty string is not a label).")
    d["c16Units"] = Ob({
        "money_scale": C("thousands"), "rate": C("decimal-per-day"), "horizon": C("days"), "dates": C("ISO-8601"),
    }, "Units of every number: money in USD thousands as the FDIC call report gives it, rates as decimals per relevant day, horizons "
       "in days, dates ISO.")
    d["c16Bank"] = Ob({
        "name": S(minLength=1), "cert": Int(1), "aggregates": C("real"), "behaviour": C("synthetic"), "deposits": C("synthetic"),
        "notice": TXT,
    }, "The bank of the case: real FDIC call-report aggregates used as public aggregates only, with synthetic behaviour and synthetic "
       "deposits from the depositor generator (SDD section 5: real event, synthetic deposits). The case does not represent the bank.")
    d["c16Survival"] = one_of(Ob({
        "kind": E("day", "survives-horizon"), "day": nullable(Int(1)), "horizon_days": Int(1),
    }, "The survival period: the first day on which the NLP turns negative (a number of days), or \"survives the horizon\" with the "
       "horizon and no number (05 E.1, U11 sizing). The day is at most the horizon."),
        {"kind": C("day"), "day": {"type": "integer"}}, {"kind": C("survives-horizon"), "day": {"type": "null"}})
    d["c16Anchor"] = Ob({
        "label": TXT, "source": S(minLength=1), "outflow_share": UNIT, "days": Int(1), "implied_daily_rate": UNIT,
        "forecast_claim": C(False),
    }, "The SVB observation as a labelled anchor row (Q4): the Table A.1 outflow share and days with the daily rate they imply, "
       "1 - (1 - share)^(1 / days); never a forecast.")
    conventions(d)
    return d


# ------------------------------------------------------------------------------------------------------ scenario outputs


def scenario_defs() -> dict:
    d = common()
    d["c16Variant"] = Ob({
        "id": E(*VARIANTS), "label": TXT, "description": TXT, "scenario_family": E("idiosyncratic", "market-wide", "combined"),
        "phase": E(*PHASES, LCR_PHASE), "parameter_set": E(*PARAMETER_SETS), "horizon_days": Int(1),
        "axis": E("relevant-days", "calendar-days"),
    }, "The variant of the SDD (section 5), with its scenario family, phase, parameter set and horizon (the conventions' "
       "variant_scenarios row of the same variant).")
    d["c16Report"] = Ob({"report_date": DATE, "source": S(minLength=1), "fields": A(CALLFIELD, 1)},
                        "One FDIC call-report quarter read for the case and the financials fields taken from it.")
    d["c16Data"] = Ob({
        "call_reports": A(R("c16Report"), 1), "data_cutoff": DATE, "read_up_to_valuation_date": C(True), "rule": LABEL,
    }, "The call reports read for the valuation date. Never one dated after it: data_cutoff is the latest report date read and is on "
       "or before the valuation date (a producer check; a false flag fails).")
    d["c16Series"] = Ob({
        "series_id": S(minLength=1), "label": TXT, "unit": S(minLength=1), "points": A(Ob({"date": DATE, "value": N()}), 1),
    }, "One H.8 weekly series with its unit.")
    d["c16Aggregate"] = Ob({"source": S(minLength=1), "series": A(R("c16Series"), 1)},
                           "The Federal Reserve H.8 aggregate deposit record of the run weeks (large and small banks).")
    d["c16Item"] = one_of(Ob({
        "item_id": S(minLength=1), "label": TXT, "side": E("asset", "liability"),
        "category": E("cash", "reverse-repo", "securities-htm", "securities-afs", "loans", "other-assets", "deposits-insured",
                      "deposits-uninsured", "deposits-foreign-office", "repo-borrowings", "fhlb-advances", "other-liabilities",
                      "equity"),
        "source_field": CALLFIELD, "reported_amount": nullable(N()), "reason_missing": nullable(LABEL),
        "assumption": S(minLength=1), "amount": N(minimum=0),
        "liquidity_class": nullable(LIQ_CLASS), "residual_days": nullable(Int(0)), "insured": nullable(B), "fair_value": nullable(N()),
    }, "One balance-sheet item taken from the call report, with the family fields liquidity_class, residual_days, insured and "
       "fair_value (null where they do not apply). A call-report item the FDIC financials lack has reported_amount null with its "
       "reason and the assumption that replaces it, never a fabricated number; a reported item has no reason."),
        {"reported_amount": {"type": "number"}, "reason_missing": {"type": "null"}},
        {"reported_amount": {"type": "null"}, "reason_missing": LABEL})
    d["c16Deposits"] = Ob({
        "dep": MONEY, "depdom": MONEY, "depuna": MONEY, "depins": MONEY, "depsmamt": MONEY, "deplgamt": MONEY,
        "denominators": Ob({"insured_uninsured": C("DEPDOM"), "total": C("DEP")}),
        "uninsured_share_of_dep": UNIT, "uninsured_share_of_depdom": UNIT,
        "size_threshold": Ob({"value": C(250000), "unit": C("USD"), "source": S(minLength=1)}),
    }, "The deposit fields (A5): DEPUNA and DEPINS cover domestic offices and their matching denominator is DEPDOM, while DEP "
       "includes foreign offices; both denominators are stated wherever the uninsured share appears. DEPSMAMT and DEPLGAMT are on "
       "the 250,000 USD threshold at 2022-12-31 by the FDIC's own definition. The FDIC names no call-report schedule or line.")
    d["c16Assumption"] = Ob({
        "assumption_id": S(minLength=1), "statement": TXT, "behaviour": C("synthetic"), "applies_to": S(minLength=1),
    }, "One assumption of the case, stated as synthetic behaviour on real aggregates.")
    d["c16BalanceSheet"] = Ob({
        "as_of": DATE, "items": A(R("c16Item"), 1), "total_assets": MONEY, "deposits": R("c16Deposits"),
        "assumptions": A(R("c16Assumption"), 1),
    }, "The balance sheet at the valuation date with its call-report source items and every assumption stated as synthetic behaviour.")
    d["c16RunoffParam"] = Ob({
        "name": S(minLength=1), "value": N(), "unit": S(minLength=1), "source_kind": E(*SOURCE_KINDS), "source": S(minLength=1),
    }, "A run-off parameter with its unit and its source: a transcribed LiST 2019 or Basel value, a pre-2023 calibration, a "
       "stated synthetic value or a convention.")
    d["c16Segment"] = one_of(Ob({
        "segment": E(*SEGMENTS), "list_class": E(*LIST_CLASSES),
        "mechanism": E("open-maturity-compounding", "contractual-maturity-rolloff", "full-runoff", "constant-stock"),
        "opening_balance": MONEY, "parameters": A(R("c16RunoffParam"), 1),
        "daily_rates": nullable(A(UNIT, 1)), "cumulative_outflow_share": A(UNIT, 1), "outflows": A(MONEY, 1),
    }, "The run-off curve of one deposit segment over the ladder: the opening balance, the daily rates (open-maturity compounding "
       "only), the cumulative outflow share and the outflow of each day. For compounding, cumulative = 1 - prod(1 - q_d) (05 E.1)."),
        {"mechanism": C("open-maturity-compounding"), "daily_rates": {"type": "array"}},
        {"mechanism": E("contractual-maturity-rolloff", "full-runoff", "constant-stock"), "daily_rates": {"type": "null"}})
    d["c16Flow"] = Ob({
        "component_id": S(minLength=1),
        "kind": E("committed-line-drawdown", "collateral-call", "secured-funding-maturity", "derivative-payable",
                  "other-contractual-outflow", "inflow-secured-lending", "inflow-loans", "inflow-other"),
        "source_kind": E(*SOURCE_KINDS), "source": S(minLength=1), "amounts": A(MONEY, 1),
    }, "A non-deposit outflow or an inflow of the ladder by day; a collateral call has no numeric LiST parameter and is a labelled "
       "scenario input (A1).")
    d["c16CbcStack"] = Ob({"class_id": E(*CBC_CLASSES), "liquidity_value": A(MONEY, 1)},
                          "The liquidity value of one CBC class available on each day of the ladder.")
    d["c16Ladder"] = Ob({
        "axis": E("relevant-days", "calendar-days"), "day_index": A(Int(1), 1), "dates": A(DATE, 1),
        "segments": A(R("c16Segment"), 1), "other_outflows": A(R("c16Flow")), "inflows": A(R("c16Flow")),
        "total_outflows": A(MONEY, 1), "total_inflows": A(MONEY, 1), "cbc_stack": A(R("c16CbcStack"), 1), "cbc_total": A(MONEY, 1),
        "cumulative_net_outflow": A(MONEY, 1), "nlp": A(MONEY, 1),
    }, "The daily ladder, columnar: every array has one value per day of the horizon. NLP(t) = CBC(t) minus the sum over s up to t "
       "of the outflows O(s) minus the inflows I(s) (05 E.1).")
    d["c16Cliff"] = Ob({
        "near_day": C(30), "far_day": C(35), "nlp_near": MONEY, "nlp_far": MONEY, "total_assets": N(exclusiveMinimum=0),
        "value": N(),
    }, "The cliff effect (NLP(35) - NLP(30)) / TA, a diagnostic of LCR window optimisation (05 E.1).")
    d["c16Path"] = one_of(Ob({
        "ladder": R("c16Ladder"), "survival": R("c16Survival"),
        "minimum_nlp": Ob({"value": MONEY, "day": Int(1)}), "cliff": nullable(R("c16Cliff")), "cliff_reason": nullable(LABEL),
    }, "The daily path of a variant: the ladder, the survival period, the minimum NLP and the cliff diagnostic (null with its reason "
       "when the horizon is shorter than 35 days)."),
        {"cliff": {"type": "object"}, "cliff_reason": {"type": "null"}}, {"cliff": {"type": "null"}, "cliff_reason": LABEL})
    d["c16CbcClass"] = Ob({
        "class_id": E(*CBC_CLASSES), "label": TXT, "source_fields": A(CALLFIELD, 1), "carrying_value": MONEY,
        "fair_value": nullable(MONEY), "value_used": MONEY, "encumbered": MONEY,
        "haircut": Ob({"value": UNIT, "rule": E(*HAIRCUT_RULES)}), "liquidity_value": MONEY,
    }, "One class of the CBC: liquidity value = (value used minus the encumbered part) x (1 - haircut), the haircut returned with its "
       "rule label (05 E.1 l.238; the Federal Reserve margins of A4).")
    d["c16Cbc"] = Ob({
        "as_of": DATE, "htm_valuation_basis": E("amortised-cost", "fair-value"),
        "haircut_framework": Ob({"label": TXT, "central_bank": C("Federal Reserve discount window"), "effective_from": DATE,
                                 "effective_to": DATE, "source": S(minLength=1)}),
        "classes": A(R("c16CbcClass"), 1),
        "pledged": Ob({"field": C("SCPLEDGE"), "amount": MONEY, "share_of_securities": UNIT}),
        "total_liquidity_value": MONEY,
    }, "The counterbalancing capacity at the valuation date: the securities split by type at the carrying values the FDIC reports, "
       "pledged securities encumbered (LiST para 63), and the held-to-maturity book at amortised cost, or at fair value in the HTM "
       "variant.")
    d["c16LcrOutflowRow"] = Ob({"category": E(*LCR_OUTFLOW_KEYS), "balance": MONEY, "rate": UNIT, "amount": MONEY,
                                "reference": S(minLength=1)},
                               "One LCR outflow category (a key of LCR_OUTFLOW_RATES, or trade_finance): the balance, its rate (the table "
                               "rate; trade finance a caller-supplied rate within 0 to 0.05) and the amount, with the Basel paragraph.")
    d["c16LcrInflowRow"] = Ob({"category": E(*LCR_INFLOW_KEYS), "balance": MONEY, "rate": UNIT, "amount": MONEY,
                               "reference": S(minLength=1)},
                              "One LCR inflow category (a key of LCR_INFLOW_RATES): the balance, its table rate and the amount, with the "
                              "Basel paragraph.")
    d["c16MappingSensitivity"] = Ob({
        "mapping_id": S(minLength=1), "lcr_category": E(*LCR_CATEGORIES), "uninsured_outflow": MONEY, "total_outflows": MONEY,
        "inflows_counted": MONEY, "net_outflows": MONEY, "ratio": N(minimum=0),
    }, "The LCR under one mapping of the uninsured balance (Q13): the outflow of the uninsured balance under that category, the total "
       "outflows, the counted inflows, the net outflows and the ratio recomputable from them and the HQLA.")
    d["c16Hqla"] = Ob({
        "l1": MONEY, "l2a": MONEY, "l2b": MONEY, "adjusted_l1": MONEY, "adjusted_l2a": MONEY, "adjusted_l2b": MONEY,
        "adj_15": MONEY, "adj_40": MONEY, "hqla": MONEY, "l2_share": nullable(UNIT), "l2b_share": nullable(UNIT),
        "shares_reason": nullable(LABEL),
        "caps": Ob({"l2_cap": C(0.4), "l2b_cap": C(0.15)}),
    }, "HQLA by level after the caps: HQLA = L1 + L2A + L2B - Adj15 - Adj40 (LCR30.38) with the adjustments of LCR30.39. The Level 2 "
       "and Level 2B shares are over the HQLA stock: where the stock is empty they are undefined and are null together with their "
       "reason in shares_reason (never zero); where they are numbers, shares_reason is null (U11 decision X6). The pairing is a "
       "cross-field rule the producer checker holds (semantics.check_document), as the product's other cross-field rules.")
    d["c16Lcr"] = Ob({
        "label": C("basel-formula-on-call-report-aggregates"), "reported_or_regulatory": C(False), "statement": TXT,
        "hqla": R("c16Hqla"), "outflows": A(R("c16LcrOutflowRow"), 1), "total_outflows": MONEY, "inflows": A(R("c16LcrInflowRow")),
        "total_inflows": MONEY, "inflow_cap": C(0.75), "inflows_counted": MONEY, "net_outflows": MONEY, "ratio": N(minimum=0),
        "mapping_sensitivity": A(R("c16MappingSensitivity"), 3),
        "below_100_note": TXT,
    }, "The LCR block: a Basel formula applied to call-report aggregates with stated assumptions, never the bank's reported or "
       "regulatory LCR (the label and the false flag are required). Inflows counted are at most 75 percent of outflows (LCR40.1) "
       "and Level 2B at most 15 percent of HQLA. A ratio below 100 percent under stress is not a breach (01 J.3).")
    d["c16Revaluation"] = one_of(Ob({
        "status": E("evaluated", "not_evaluated"), "engine_ref": C("engine-irrbb-api"), "curve_source": S(minLength=1),
        "curve_date": nullable(DATE), "model_fair_value": nullable(N()), "reported_fair_value": N(), "difference": nullable(N()),
        "relative_difference": nullable(N(minimum=0)), "reason": nullable(LABEL),
    }, "The HTM revaluation validation row (Q11): the book revalued from its maturity profile under the Treasury curve through the "
       "engine's irrbb curves, against the reported fair value; null with its reason when the revaluation did not run."),
        {"status": C("evaluated"), "curve_date": {"type": "string"}, "model_fair_value": {"type": "number"},
         "difference": {"type": "number"}, "relative_difference": {"type": "number"}, "reason": {"type": "null"}},
        {"status": C("not_evaluated"), "curve_date": {"type": "null"}, "model_fair_value": {"type": "null"},
         "difference": {"type": "null"}, "relative_difference": {"type": "null"}, "reason": LABEL})
    d["c16Htm"] = Ob({
        "reported": Ob({"htm_amortised_cost": MONEY, "htm_fair_value": MONEY, "htm_unrealised": MONEY, "afs_amortised_cost": MONEY,
                        "afs_fair_value": MONEY, "afs_unrealised": MONEY}),
        "application": Ob({"method": E("whole-book", "pro-rata-by-type"), "statement": TXT}),
        "cbc_without_loss": MONEY, "cbc_with_loss": MONEY, "cbc_removed": MONEY,
        "btfp_par": Ob({"label": TXT, "announced": C("2023-03-12"), "cbc_at_par": MONEY, "uplift": MONEY}),
        "revaluation": R("c16Revaluation"),
    }, "The HTM losses in the CBC: the reported amortised cost and fair value (SCHA, SCHF, SCAA, SCAF), the loss applied to the book as "
       "a whole or pro rata by type (never a reported by-type loss), the CBC with and without it, the labelled counterfactual under "
       "the Bank Term Funding Program's par valuation (announced after the run) and the revaluation validation row.")
    d["c16Denominator"] = Ob({
        "id": E("board-stated-share", "call-report-dep"), "label": TXT, "denominator_amount": nullable(MONEY),
        "realised_amount": nullable(MONEY), "realised_share": UNIT, "source": S(minLength=1), "modelled_share": N(minimum=0),
        "compared_at": E("event-horizon", "model-horizon"), "shortfall": N(), "ratio": N(minimum=0), "light": LIGHT3,
    }, "The realised outflow against one denominator, and the model's share compared with it: shortfall = realised minus modelled, "
       "ratio = modelled over realised, the light by the conventions scoring_ratio_green and scoring_ratio_amber.")
    d["c16Modelled"] = Ob({"horizon_days": Int(1), "amount": MONEY, "share_of_model_base": UNIT},
                          "The model's cumulative outflow at a horizon and its share of the model's deposit base.")
    d["c16ModelledOutflow"] = one_of(Ob({
        "at_event_horizon": nullable(R("c16Modelled")), "at_event_horizon_reason": nullable(LABEL), "at_model_horizon": R("c16Modelled"),
    }, "The model's cumulative outflow at the event horizon (null with its reason for the LCR, which defines a 30-day aggregate and "
       "no daily path) and at the model's own horizon."),
        {"at_event_horizon": {"type": "object"}, "at_event_horizon_reason": {"type": "null"}},
        {"at_event_horizon": {"type": "null"}, "at_event_horizon_reason": LABEL})
    d["c16A1Score"] = one_of(Ob({
        "row_id": E(*A1_IDS), "bank": S(minLength=1), "year": Int(1900), "horizon_days": Int(1), "observed_share": UNIT,
        "modelled_share": nullable(N(minimum=0)), "error": nullable(N()), "role": E("calibration", "scored", "reference"),
        "reason": nullable(LABEL),
    }, "A Table A.1 row against the model's cumulative outflow at the row's horizon; the role says whether the fast run was "
       "calibrated on it (pre-2023), scored on it (2023) or only shows it as a reference point. A row whose horizon is beyond the "
       "model's ladder (or a variant without a daily path) has a null share with its reason."),
        {"modelled_share": {"type": "number"}, "error": {"type": "number"}, "reason": {"type": "null"}},
        {"modelled_share": {"type": "null"}, "error": {"type": "null"}, "reason": LABEL})
    d["c16Scoring"] = Ob({
        "event": Ob({"label": TXT, "event_date": C("2023-03-10"), "horizon_days": Int(1), "source": S(minLength=1)}),
        "model_deposit_base": MONEY, "modelled_outflow": R("c16ModelledOutflow"),
        "denominators": ordered([
            {"$ref": "#/$defs/c16Denominator", "properties": {"id": C("board-stated-share"), "denominator_amount": {"type": "null"},
                                                                 "realised_amount": {"type": "null"}}},
            {"$ref": "#/$defs/c16Denominator", "properties": {"id": C("call-report-dep"), "denominator_amount": {"type": "number"},
                                                                 "realised_amount": {"type": "number"}}}],
            "The two denominators of the realised outflow (Q4): the Board's roughly 85 percent of the deposit base, and over 40 plus "
            "100 billion USD against the call report's DEP."),
        "svb_anchor": {"$ref": "#/$defs/c16Anchor", "properties": {"outflow_share": C(0.85), "days": C(2)}},
        "table_a1_scoring": ordered([pin("c16A1Score", row_id=r, bank=b, year=y, horizon_days=n, observed_share=s)
                                     for r, b, y, s, n in TABLE_A1]),
    }, "The March 2023 scoring block: the model's cumulative outflow against the realised outflow with both denominators, the SVB "
       "observation as a labelled anchor row and the Table A.1 rows. Calibrated on pre-2023 data and scored on 2023 (Q4).")
    d["c16TimePoint"] = Ob({
        "as_of": DATE, "report_date": DATE, "deposits": R("c16Deposits"), "htm_unrealised_loss": MONEY,
        "cbc_amortised_basis": MONEY, "cbc_fair_value_basis": MONEY, "survival": nullable(R("c16Survival")),
        "lcr_ratio": nullable(N(minimum=0)),
    }, "One earlier call-report date of the time block (Q7): the deposits, the HTM unrealised loss, the CBC on both bases and the "
       "survival period as the HTM losses grew (null where the variant defines no daily path).")
    d["c16ContractualBucket"] = Ob({
        "from_day": Int(0), "to_day": nullable(Int(1)), "inflows": MONEY, "outflows": MONEY, "gap": MONEY, "cumulative_gap": MONEY,
    }, "One contractual maturity bucket: from_day exclusive to to_day inclusive (null: open-ended), gap = inflows - outflows.")
    d["c16ContractualLadder"] = Ob({
        "buckets": A(R("c16ContractualBucket"), 1), "reference": S(minLength=1),
    }, "The static contractual maturity ladder with gaps and cumulative gaps (05 E.5 rung 1; the SRP50 contractual maturity "
       "mismatch tool, 01 G.3), on the buckets of the conventions' contractual_bucket_edges_days.")

    d["c16ShareSensitivity"] = Ob({"share": UNIT, "survival": R("c16Survival")},
                                  "The survival period when the uninsured share of the domestic deposits is `share` (05 E.5 rung 4).")
    d["c16HtmSensitivity"] = Ob({
        "multiple": N(minimum=0), "unrealised_loss": MONEY, "cbc": MONEY, "survival": R("c16Survival"),
    }, "The HTM unrealised loss at `multiple` times the reported loss (05 E.5 rung 4, l.278): the loss, the CBC under it and the survival "
       "period; 1 is the reported loss and 0 no loss.")
    d["c16Sensitivities"] = Ob({
        "uninsured_share": nullable(A(R("c16ShareSensitivity"), 2)), "uninsured_share_reason": nullable(LABEL),
        "htm_loss": nullable(A(R("c16HtmSensitivity"), 2)), "htm_loss_reason": nullable(LABEL),
    }, "The two sensitivities the survival-horizon views draw: the survival period against the uninsured share, ordered as the "
       "conventions' uninsured_share_grid, and the survival period and CBC against the HTM unrealised-loss multiple, ordered as the "
       "htm_loss_multiple_grid. Each is null with its reason where the variant has no daily path (the LCR).")

    def alt(vid: str, parameter_set: dict, path: bool, lcr: bool, htm: bool, basis: str) -> dict:
        return {
            "variant": {"properties": {"id": C(vid), "parameter_set": parameter_set,
                                       "phase": C(LCR_PHASE) if vid == "lcr-standard" else E(*PHASES),
                                       "axis": C("calendar-days" if vid == "lcr-standard" else "relevant-days")}, "required": ["id"]},
            "sensitivities": {"properties": {
                "uninsured_share": {"type": "array"} if path else {"type": "null"},
                "uninsured_share_reason": {"type": "null"} if path else LABEL,
                "htm_loss": {"type": "array"} if path else {"type": "null"},
                "htm_loss_reason": {"type": "null"} if path else LABEL}},
            "path": R("c16Path") if path else {"type": "null"}, "path_reason": {"type": "null"} if path else LABEL,
            "lcr": R("c16Lcr") if lcr else {"type": "null"}, "lcr_reason": {"type": "null"} if lcr else LABEL,
            "htm": R("c16Htm") if htm else {"type": "null"}, "htm_reason": {"type": "null"} if htm else LABEL,
            "cbc": {"properties": {"htm_valuation_basis": C(basis)}, "required": ["htm_valuation_basis"]},
            "scoring": {"properties": {"modelled_outflow": {"properties": {"at_event_horizon": {"type": "null"} if not path
                                                                          else {"type": "object"}}}}},
        }

    root = Ob({
        "kind": C("scenario"), "valuation_date": C("2022-12-31"), "currency": {**CUR, "const": "USD"}, "units": R("c16Units"),
        "bank": R("c16Bank"), "variant": R("c16Variant"), "conventions": R("c16Conventions"), "data": R("c16Data"),
        "aggregate_record": nullable(R("c16Aggregate")), "aggregate_record_reason": nullable(LABEL),
        "balance_sheet": R("c16BalanceSheet"), "cbc": R("c16Cbc"), "contractual_ladder": R("c16ContractualLadder"),
        "path": nullable(R("c16Path")), "path_reason": nullable(LABEL), "lcr": nullable(R("c16Lcr")),
        "lcr_reason": nullable(LABEL), "htm": nullable(R("c16Htm")), "htm_reason": nullable(LABEL), "scoring": R("c16Scoring"),
        "sensitivities": R("c16Sensitivities"),
        "time_block": ordered([pin("c16TimePoint", as_of="2021-12-31"), pin("c16TimePoint", as_of="2022-06-30")],
                              "The 2021-12-31 and 2022-06-30 call-report dates, in this order."),
    }, "C16 scenario outputs (outputs.kind scenario): one of the five scenario variants of the liquidity stress case at the last call "
       "report before the run, 2022-12-31, with the time block for two earlier dates. Money is in USD thousands. A Basel formula on "
       "call-report aggregates with synthetic behaviour and synthetic deposits: nothing here is the bank's reported or regulatory "
       "figure, certifies a model or claims compliance.")
    root["allOf"] = [
        {"if": {"properties": {"variant": {"properties": {"id": C(vid)}, "required": ["id"]}}, "required": ["variant"]},
         "then": {"properties": alt(vid, ps, path, lcr, htm, basis)}}
        for vid, ps, path, lcr, htm, basis in (
            ("lcr-standard", C("basel-lcr"), False, True, False, "amortised-cost"),
            ("list-adverse", C("list-adverse"), True, False, False, "amortised-cost"),
            ("list-extreme", C("list-extreme"), True, False, False, "amortised-cost"),
            ("fast-run", C("fast-run"), True, False, False, "amortised-cost"),
            ("htm-losses", E("list-adverse", "list-extreme", "fast-run"), True, False, True, "fair-value"))]
    d["c16Outputs"] = root
    # the blocks each variant carries are pinned by if/then on variant.id (a plain object root, so the TypeScript descriptor is one shape)
    return d


# ------------------------------------------------------------------------------------------------------ reverse stress


def reverse_defs() -> dict:
    d = common()
    d["c16CurvePoint"] = Ob({"multiplier": N(minimum=1), "survival": R("c16Survival")},
                            "One point of SP(m): the run-off multiplier and the survival period under it.")
    d["c16Solved"] = one_of(Ob({
        "status": E("solved", "refused"), "multiplier": nullable(N(minimum=1)), "survival_at_multiplier": nullable(Int(1)),
        "target_days": Int(1), "round_trip_error": nullable(N()), "refusal_reason": nullable(LABEL),
    }, "The solved multiplier: the threshold m*, the smallest m at which the survival period first falls to or below the target "
       "(05 E.5 rung 5; engine-liquidity-api 1.2.0), by bracketing on the monotone SP(m); the round trip is the threshold property "
       "(the survival at m* is at most the target, below it when SP(m) steps past the target, and every cheaper point survives longer "
       "than the target); a target that is not bracketed is refused with the reason."),
        {"status": C("solved"), "multiplier": {"type": "number"}, "survival_at_multiplier": {"type": "integer"},
         "round_trip_error": {"type": "number"}, "refusal_reason": {"type": "null"}},
        {"status": C("refused"), "multiplier": {"type": "null"}, "survival_at_multiplier": {"type": "null"},
         "round_trip_error": {"type": "null"}, "refusal_reason": LABEL})
    d["c16ReverseBase"] = Ob({
        "base_id": E("list-adverse", "list-extreme", "fast-run"), "parameter_set": E("list-adverse", "list-extreme", "fast-run"),
        "label": TXT, "base_survival": R("c16Survival"),
        "max_rate_below_one": N("The largest daily rate of the base scenario that is below 1 (a rate already at 1 stays at 1).",
                                exclusiveMinimum=0, exclusiveMaximum=1),
        "max_multiplier": N(exclusiveMinimum=1), "curve": A(R("c16CurvePoint"), 2), "solved": R("c16Solved"),
    }, "The reverse stress of one base scenario (Q9): the multiplier applied to every segment's daily rate, capped so that each rate "
       "stays below 1 (max_multiplier = 1 / max_rate_below_one), the SP(m) curve and the solved multiplier.")
    d["c16ReverseOutputs"] = Ob({
        "kind": C("reverse-stress"), "valuation_date": C("2022-12-31"), "currency": {**CUR, "const": "USD"}, "units": R("c16Units"),
        "bank": R("c16Bank"), "conventions": R("c16Conventions"),
        "target": Ob({"days": Int(1), "statement": TXT}),
        "cap_rule": Ob({"each_rate_below_one": C(True), "statement": TXT}),
        "bases": ordered([pin("c16ReverseBase", base_id=b, parameter_set=b) for b in ("list-adverse", "list-extreme", "fast-run")]),
    }, "C16 reverse-stress outputs (outputs.kind reverse-stress): the run-off multiplier at which the survival period falls to the "
       "target, per base scenario (LiST Adverse, LiST Extreme, the fast run).")
    return d


# ------------------------------------------------------------------------------------------------------ models


def models_defs() -> dict:
    d = common()
    d["c16ListRow"] = Ob({"item": S(minLength=1), "baseline": N(minimum=0), "adverse": N(minimum=0), "extreme": N(minimum=0)},
                         "A LiST 2019 rate row (Baseline, Adverse, Extreme): a roll-off rate on a maturing flow or a daily "
                         "compounding rate on the stock, as decimals.")
    d["c16DrawdownRow"] = Ob({"item": S(minLength=1), "adverse": N(minimum=0), "extreme": N(minimum=0)},
                             "A committed-facility daily drawdown rate on the undrawn stock for three months (N paras 119 to 126).")
    d["c16ResultsAnnex"] = Ob({
        "n_banks": C(103), "median_survival_days": Ob({"adverse": C(176), "extreme": C(122)}), "unit": C("days"),
        "sources": Ob({"annex": C("ECB LiST 2019 results annex"), "n_banks_slide": C(9), "median_slides": ordered([C(15)]),
                       "dossier": C("dossier 05 E.1 line 240")}),
        "statement": TXT,
    }, "The LiST 2019 results annex as constants (the markers of the survival views): 103 banks and the median reported survival "
       "period under the Adverse (176 days) and the Extreme (122 days) shock; annex slide 9 gives the bank count and slide 15 the "
       "medians (addendum L1; dossier 05 E.1 line 240). Reference points, not model results.")
    d["c16ListParameters"] = Ob({
        "source": S(minLength=1), "attribution": S(minLength=1),
        "contractual_outflows": ordered([pin("c16ListRow", item=i, baseline=b, adverse=a, extreme=e) for i, b, a, e in LIST_CONTRACTUAL]),
        "open_maturity_daily": ordered([pin("c16ListRow", item=i, baseline=b, adverse=a, extreme=e) for i, b, a, e in LIST_OPEN]),
        "contractual_inflows": ordered([pin("c16ListRow", item=i, baseline=b, adverse=a, extreme=e) for i, b, a, e in LIST_INFLOWS]),
        "committed_drawdown": ordered([{"$ref": "#/$defs/c16DrawdownRow", "properties": {"item": C(i), "adverse": C(a), "extreme": C(e)}}
                                       for i, a, e in LIST_DRAWDOWN]),
        "relevant_days_six_months": C(125), "relevant_days_three_months": C(63), "calendar_note": TXT,
        "results_annex": R("c16ResultsAnnex"),
    }, "The ECB LiST 2019 parameters as transcribed data (U11 research addendum L1; the rates are the note's own, on the 2019 TARGET2 "
       "relevant-day calendar): Table 3.2 for the contractual items, Table 3.3 for the open-maturity daily rates, the drawdown rates "
       "of the committed facilities. Collateral calls have no numeric parameter and are a scenario input.")
    d["c16Golden"] = Ob({
        "id": S(minLength=1), "daily_rate": UNIT, "days": Int(1), "cumulative_outflow": UNIT,
        "label": E("dossier-05-line-237", "recomputed"),
    }, "A compounding golden: 1 - (1 - q)^n, labelled whether the dossier prints it or this contract recomputed it.")
    d["c16A1Row"] = Ob({"row_id": E(*A1_IDS), "bank": S(minLength=1), "year": Int(1900), "outflow_share": UNIT, "days": Int(1)},
                       "A Table A.1 row: the deposit outflow share over the number of days.")
    d["c16TableA1"] = Ob({
        "source": S(minLength=1), "attribution": S(minLength=1),
        "rows": ordered([pin("c16A1Row", row_id=r, bank=b, year=y, outflow_share=s, days=n) for r, b, y, s, n in TABLE_A1]),
        "lcr_range": Ob({"label": C("LCR deposit outflow rates"), "low": C(0.03), "high": C(0.40), "days": C(30)}),
    }, "BCBS d555 Box A Table A.1 transcribed as data (one table, within the BIS limited-extract terms, addendum L2.1; footnote (a): "
       "SVB outflows include the expected outflows of management for 10 March, First Republic excludes 30 bn USD placed by banks).")
    d["c16ImpliedRate"] = Ob({"row_id": E(*A1_IDS), "implied_daily_rate": UNIT},
                             "The daily rate a Table A.1 row implies, 1 - (1 - share)^(1 / days).")
    d["c16Calibration"] = Ob({
        "split": Ob({"calibrated_on": ordered([C(r) for r in CALIBRATED_ON]), "scored_on": ordered([C(r) for r in SCORED_ON])}),
        "implied_daily_rates": ordered([pin("c16ImpliedRate", row_id=r) for r in CALIBRATED_ON]),
        "fitted_daily_rate": Ob({"value": UNIT, "unit": C("decimal-per-day"), "source_kind": C("calibrated-pre-2023"),
                                 "source": S(minLength=1)}),
        "anchor": {"$ref": "#/$defs/c16Anchor", "properties": {"outflow_share": C(0.85), "days": C(2)}}, "statement": TXT,
    }, "The pre-2023 calibration of the fast run (Q4): the daily rate taken from the pre-2023 Table A.1 rows by the calibration "
       "rule, never from the 2023 rows, which are scored; the SVB observation is a labelled anchor, not a forecast.")
    d["c16GeneratorSegment"] = Ob({
        "segment": E(*SEGMENTS), "share_of_deposits": UNIT, "calm_daily_hazard": UNIT, "stress_daily_hazard": UNIT,
        "p_enter_stress": UNIT, "p_exit_stress": UNIT, "basis": TXT,
    }, "One depositor segment of the generator: its share of the call-report deposits and the withdrawal hazard in the calm and the "
       "stress state, with the transition probabilities per day.")
    d["c16Generator"] = Ob({
        "config": Ob({"truth_status": C("synthetic-known-truth"), "seed": Int(0), "n_depositors": Int(1), "horizon_days": Int(1),
                      "segments": A(R("c16GeneratorSegment"), 1)}),
        "truth": A(Ob({"segment": E(*SEGMENTS), "horizon_days": Int(1), "true_outflow_rate": UNIT}), 1),
        "verification": Ob({"n_draws": Int(1), "max_abs_error": N(minimum=0), "mc_standard_error": N(minimum=0), "within_error": B}),
    }, "The depositor generator with known truth (08 G.2): its configuration, the exact outflow rate by segment and horizon, and the "
       "verification that a large draw reproduces the truth within Monte Carlo error.")
    d["c16SourceNote"] = Ob({
        "source_id": S(minLength=1), "publisher": S(minLength=1), "licence_class": E("mirror-allowed", "derived-only", "link-only",
                                                                                      "unusable"),
        "licence_basis": E("notice-read", "unverified"), "statement": TXT,
    }, "The licence class of a source with the basis of the reading (A6): a reading of the publisher's notice, not legal advice.")
    d["c16ParameterSet"] = Ob({"set_id": E(*PARAMETER_SETS), "source": S(minLength=1), "source_kind": E(*SOURCE_KINDS)},
                              "One run-off parameter set and where it comes from.")
    d["c16Fit"] = Ob({
        "currency": {**CUR, "const": "USD"}, "units": R("c16Units"), "bank": R("c16Bank"), "conventions": R("c16Conventions"),
        "parameter_sets": ordered([pin("c16ParameterSet", set_id=s) for s in PARAMETER_SETS]),
        "list_parameters": R("c16ListParameters"), "list_goldens": ordered([pin("c16Golden", id=i, daily_rate=q, days=n, label=lab) for i, q, n, lab in GOLDENS]), "table_a1": R("c16TableA1"),
        "calibration": R("c16Calibration"), "generator": R("c16Generator"), "sources": A(R("c16SourceNote"), 5),
    }, "C16 models: the run-off parameter sets with their sources (the LiST 2019 tables as data, Table A.1 as data), the pre-2023 "
       "calibration, the generator's parameters and truth, the named parameters (conventions) and the licence class of every source.")
    return d


def main() -> None:
    variant_schema("variant-scenario", "scenario", "C16 scenario variant",
                   "Catalog row c16-outputs 1.0.0: one of the five scenario variants of the liquidity stress case (LCR standard "
                   "run-off, LiST adverse, LiST extreme, 2023 fast run, HTM losses in CBC) at 2022-12-31 (outputs.kind scenario).",
                   "c16Outputs", scenario_defs(), ["lcr", "survival_days"])
    variant_schema("variant-reverse", "reverse-stress", "C16 reverse-stress variant",
                   "Catalog row c16-outputs-reverse 1.0.0: the reverse liquidity stress of the liquidity case, per base scenario "
                   "(outputs.kind reverse-stress).", "c16ReverseOutputs", reverse_defs(),
                   ["multiplier_list_adverse", "multiplier_list_extreme", "multiplier_fast_run"])
    models_schema("C16 models",
                  "Catalog row c16-models 1.0.0: the C16 models artifact (the run-off parameter sets with their sources, the pre-2023 "
                  "calibration, the generator parameters and truth, the named parameters).", "c16Fit", models_defs())


if __name__ == "__main__":
    main()
