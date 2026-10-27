"""Builds the four U10-S schema files (docs/contracts/schemas/c14 and c15).

Run: ``python tests/contracts_u10/build_schemas.py``. Deterministic, standard library only. The schema files are the
contract and are committed; this script is the compact source they are written from, so a name two files of one case
share has one definition (the generator of the TypeScript types fails on a clash). Conventions of docs/contracts/catalog.md:
one folder per case, a ``case_id`` const, ``outputs.kind`` on every variant, case-prefixed ``$defs``, the
``variant-envelope`` composition with ``unevaluatedProperties: false``, every object closed, nothing optional.

Transcribed from dossier 01 H (the 19 midpoints of SRP31.96 Table 3, the six shocks, the 21 currencies, Table 4 caps),
dossier 03 F.2 (the UR currency, the CMF table, the offset rule, the indexation charge, the thresholds) and dossier 05 D.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "docs" / "contracts" / "schemas"
BASE = "https://contraste.fasl-work.com/contracts/"
TXT = {"$ref": "../common/text.schema.json"}


def STR_OR_TXT(what: str, version: str) -> dict:
    """A reader text that a view prints in both languages: bilingual from ``version`` (U16-F10d, the third capture review R3); a
    document baked before it carries the English string alone and stays valid until its case is re-baked."""
    return {"anyOf": [S(minLength=1), TXT],
            "description": f"{what}: a bilingual text from {version}; the English string alone in a document baked before it."}

SHOCKS = ["parallel-up", "parallel-down", "steepener", "flattener", "short-up", "short-down"]
MIDPOINTS = [0.0028, 0.0417, 0.1667, 0.375, 0.625, 0.875, 1.25, 1.75, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 12.5, 17.5, 25.0]
CCY21 = ["ARS", "AUD", "BRL", "CAD", "CHF", "CNY", "EUR", "GBP", "HKD", "IDR", "INR", "JPY", "KRW", "MXN", "RUB", "SAR", "SEK",
         "SGD", "TRY", "USD", "ZAR"]
C14_CATS = [("retail-transactional", 0.9, 5.0), ("retail-non-transactional", 0.7, 4.5), ("wholesale", 0.5, 4.0)]
C15_CATS = [("retail-operational", 0.9, 5.0), ("retail-non-operational", 0.7, 4.5), ("wholesale", 0.5, 4.0)]


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
CUR = S("ISO 4217 code of the money fields of this block.", pattern="^[A-Z]{3}$")
DATE = S(pattern=r"^\d{4}-\d{2}-\d{2}$")
MONTH = S(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
UNIT = N("A share or an observed rate in [0, 1].", minimum=0, maximum=1)
MONEY = N("Money in the `currency` (C15: the `reporting_currency`) of the enclosing block.")
RATE = N("A rate as a decimal.")
BUCKET = Int(1, 19, "Bucket of the 19 of SRP31.96 Table 3, 1 (overnight) to 19 (over 20 years).")
MID = {"type": "number", "enum": MIDPOINTS, "description": "Bucket midpoint in years: one of the 19 of SRP31.96 Table 3."}
SOURCE_KIND = E("regulatory-cap", "fitted", "synthetic-stated")
NAME_MAP = Ob({"name": S(), "value": N(), "unit": S()})
SHOCK = E(*SHOCKS)
DENSE_RATES = A(N(), 19, 19, "One value per bucket, bucket 1 first.")
DENSE_MONEY = A(MONEY, 19, 19, "One value per bucket, bucket 1 first; net notional repricing cash flows, assets positive, liabilities negative.")
LIGHT = E("green", "amber", "red", "not_evaluated", "error")

NOT_EVALUATED_RULE = {
    "properties": {"tests": {"items": {
        "if": {"properties": {"light": {"const": "not_evaluated"}}, "required": ["light"]},
        "then": {"properties": {"statistic": {"type": "null"}, "p_value": {"type": "null"}, "metric": {"type": "null"},
                                "notes": {"type": "string", "minLength": 1}}},
    }}},
}


def one_of(ob: dict, *alternatives: dict) -> dict:
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


T2024 = {  # dossier 01 H.3, SRP31.90 Table 2 (in force 2026-01-01)
    "parallel": [400, 350, 400, 200, 175, 225, 225, 275, 225, 400, 325, 100, 225, 400, 400, 275, 275, 175, 400, 200, 325],
    "short": [500, 425, 500, 275, 250, 300, 350, 425, 375, 500, 475, 100, 350, 500, 500, 375, 425, 250, 500, 300, 500],
    "long": [300, 300, 300, 175, 200, 150, 200, 250, 200, 300, 225, 100, 225, 200, 300, 250, 200, 225, 300, 225, 300],
}
T2016 = {  # dossier 01 H.3, d368 Annex 2 Table 1
    "parallel": [400, 300, 400, 200, 100, 250, 200, 250, 200, 400, 400, 100, 300, 400, 400, 200, 200, 150, 400, 200, 400],
    "short": [500, 450, 500, 300, 150, 300, 250, 300, 250, 500, 500, 100, 400, 500, 500, 300, 300, 200, 500, 300, 500],
    "long": [300, 200, 300, 150, 100, 150, 100, 150, 100, 350, 300, 100, 200, 300, 300, 150, 150, 100, 300, 150, 300],
}
GAMMA = [0.8, 1.2, 0.8, 1.2, 0.8, 1.2]   # SRP31.119 Table 5, in the order of SHOCKS
UMULT = [1.2, 0.8, 0.8, 1.2, 1.2, 0.8]   # SRP31.125 Table 6, in the order of SHOCKS
CMF_TABLE = [("canasta-1", 200, 300, 150), ("canasta-2", 400, 500, 300), ("CLP", 300, 400, 200), ("UR-nii", 300, None, None),
             ("UR-eve", 200, 250, 150)]


def pin(name: str, **consts) -> dict:
    """An element of an ordered array: the def with some properties fixed to constants."""
    return {"$ref": f"#/$defs/{name}", "properties": {k: {"const": v} for k, v in consts.items()}}


def ordered(items: list, desc: str | None = None) -> dict:
    """An array of exactly these elements in this order (prefixItems, nothing beyond)."""
    d: dict = {"type": "array", "prefixItems": items, "items": False, "minItems": len(items), "maxItems": len(items)}
    if desc:
        d["description"] = desc
    return d


def with_pairs(ob: dict) -> dict:
    """Pins the pairing of a ``bucket`` with its SRP31.96 Table 3 midpoint (a bucket with another bucket's midpoint fails)."""
    return one_of(ob, *[{"bucket": C(k + 1), "midpoint_years": C(m)} for k, m in enumerate(MIDPOINTS)])


def write(case: str, name: str, doc: dict) -> None:
    path = SCHEMAS / case.lower() / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def variant_schema(case: str, ref: str, kind: str, title: str, desc: str, root: str, defs: dict) -> None:
    write(case, f"{ref}.schema.json", {
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
    })


def models_schema(case: str, title: str, desc: str, root: str, defs: dict) -> None:
    write(case, "models.schema.json", {
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
    })


# ------------------------------------------------------------------------------------------- shared IRRBB blocks


def common(p: str, cats: list, ndigits_note: str) -> dict:
    """The blocks C14 and C15 share, with the case prefix ``p`` (a name two files of one case share has one definition)."""
    d: dict = {}
    d[p + "Label"] = Ob({"en": S(minLength=1), "es": S(minLength=1)},
                        "A non-empty bilingual label (an empty string is not a label).")
    d[p + "Sign"] = Ob({
        "delta_eve": C("positive-is-loss"), "delta_nii": C("positive-is-loss"),
        "reference": S(minLength=1), "statement": TXT,
    }, "Sign convention, stated in the document: a positive delta EVE or delta NII is a loss (SRP31.129; dossier 01 H.4).")
    d[p + "Units"] = Ob({
        "money_scale": E("units", "thousands", "millions"), "rate": C("decimal"), "compounding": C("continuous"),
        "shock": C("basis-points"), "bucket_midpoint": C("years"), "dates": C("ISO-8601"),
    }, "Units of every number: money in the stated scale of its currency, rates as decimals discounted continuously "
       "(SRP31.129), shocks in basis points, bucket midpoints in years, dates ISO.")
    d[p + "Assumption"] = Ob({
        "value": N(), "unit": S(minLength=1), "source_kind": SOURCE_KIND, "source": S(minLength=1),
    }, "A behavioural assumption as a named field: its value, its unit and where it comes from (the regulatory cap, a fit, or "
       "a stated synthetic value), so a view can show the result with and without it.")
    d[p + "Assumptions"] = Ob({
        "nmd_core_share": R(p + "Assumption"), "nmd_core_maturity_years": R(p + "Assumption"),
        "prepayment_cpr": R(p + "Assumption"), "term_deposit_redemption_rate": R(p + "Assumption"),
        "deposit_beta": R(p + "Assumption"),
    }, "The five behavioural assumptions. nmd_core_share and nmd_core_maturity_years are the balance-weighted averages of "
       "nmd_segments.")
    d[p + "Flow"] = with_pairs(Ob({"bucket": BUCKET, "midpoint_years": MID, "amount": MONEY},
                                  "A net notional repricing cash flow in one bucket (assets positive, liabilities negative)."))
    alts = []
    for name, share_cap, mat_cap in cats:
        for sflag in ("within-cap", "above-cap"):
            for mflag in ("within-cap", "above-cap"):
                applied = sflag == "above-cap" or mflag == "above-cap"
                alts.append({
                    "category": C(name), "core_share_cap": C(share_cap), "core_maturity_cap_years": C(mat_cap),
                    "requested_core_share": N(minimum=0, maximum=share_cap) if sflag == "within-cap"
                    else N(exclusiveMinimum=share_cap, maximum=1),
                    "requested_core_maturity_years": N(minimum=0, maximum=mat_cap) if mflag == "within-cap"
                    else N(exclusiveMinimum=mat_cap),
                    "core_share_used": N(minimum=0, maximum=share_cap) if sflag == "within-cap" else C(share_cap),
                    "core_maturity_used_years": N(minimum=0, maximum=mat_cap) if mflag == "within-cap" else C(mat_cap),
                    "cap_applied": C(applied),
                })
    d[p + "NmdSegment"] = one_of(Ob({
        "category": E(*[c[0] for c in cats]),
        "balance": MONEY,
        "requested_core_share": UNIT, "core_share_cap": UNIT, "core_share_used": UNIT,
        "requested_core_maturity_years": N(minimum=0), "core_maturity_cap_years": N(minimum=0),
        "core_maturity_used_years": N(minimum=0),
        "cap_applied": B,
        "source_kind": SOURCE_KIND, "source": S(minLength=1),
    }, "A non-maturity deposit segment: the requested core share and maturity, the SRP31 Table 4 cap, the value used and "
       "cap_applied (D2 of the U10 sizing). A request above its cap validates only with cap_applied true and the used value "
       "at the cap; a request within the caps has cap_applied false and the used value equal to the request (a producer check). "
       "The standardised EVE uses the used values."), *alts)
    sizes = []
    for origin, table in (("srp31-table-2024", T2024), ("srp31-table-2016", T2016)):
        for i, ccy in enumerate(CCY21):
            sizes.append({"origin": C(origin), "currency": C(ccy), "parallel_bp": C(table["parallel"][i]),
                          "short_bp": C(table["short"][i]), "long_bp": C(table["long"][i]),
                          "label": {"type": "null"}, "method": {"type": "null"}})
    for ccy, (par, sh, lg) in (("CLP", (300, 400, 200)), ("CLF", (200, 250, 150))):
        sizes.append({"origin": C("cmf-annex1"), "currency": C(ccy), "parallel_bp": C(par), "short_bp": C(sh), "long_bp": C(lg),
                      "label": {"type": "null"}, "method": {"type": "null"}})
    sizes.append({"origin": C("contraste-estimate"), "currency": {"not": {"enum": CCY21}},
                  "label": R(p + "Label"), "method": S(minLength=1)})
    d[p + "ShockSize"] = one_of(Ob({
        "currency": CUR, "parallel_bp": N(minimum=0), "short_bp": N(minimum=0), "long_bp": N(minimum=0),
        "origin": E("srp31-table-2024", "srp31-table-2016", "cmf-annex1", "contraste-estimate"),
        "label": nullable(R(p + "Label")), "method": nullable(S(minLength=1)),
    }, "The shock sizes applied to a currency, in basis points. A tabled size is exactly the table's (SRP31.90 Table 2, d368 "
       "Annex 2 Table 1, RAN 21-13 Annex 1 Hoja 9); a currency without an entry in the BCBS table (CLP is in neither) passes "
       "only labelled as a Contraste estimate with its method, never as a regulatory parameter (dossier 01 H.3), and a tabled "
       "currency cannot be relabelled as an estimate."), *sizes)
    d[p + "Outlier"] = Ob({
        "threshold_share_tier1": C(0.15), "tier1": N("Money in the `currency` of the enclosing block.", exclusiveMinimum=0), "eve_risk_measure": N("Money in the `currency` of the enclosing block.", minimum=0), "ratio": N(minimum=0), "breached": B,
        "reference": S(minLength=1),
    }, "The outlier test: the EVE risk measure against 15 percent of Tier 1 capital (SRP31.82 to SRP31.83).")
    d[p + "Tranche"] = Ob({"maturity_years": N(exclusiveMinimum=0), "weight": UNIT},
                          "A rolling tranche of the replicating portfolio and its weight.")
    d[p + "Window"] = Ob({
        "window_start": DATE, "window_end": DATE, "weights": A(UNIT, 1), "weighted_average_maturity_years": N(minimum=0),
    }, "The weights re-estimated on one estimation window, in the order of the tranches (stability across windows).")
    d[p + "DepositBeta"] = Ob({
        "up": N(minimum=0), "down": N(minimum=0), "source_kind": SOURCE_KIND, "source": S(minLength=1),
    }, "Deposit beta (pass-through of the market rate to the client rate), asymmetric in the direction of the move.")
    d[p + "NmdModel"] = Ob({
        "valuation_date": DATE, "category": E(*[c[0] for c in cats]),
        "tranches": A(R(p + "Tranche"), 1), "weights_sum": N(), "weighted_average_maturity_years": N(minimum=0),
        "margin_volatility": nullable(N(minimum=0)), "margin_volatility_reason": nullable(R(p + "Label")),
        "deposit_beta": R(p + "DepositBeta"), "stability": A(R(p + "Window"), 1),
    }, "The static replicating portfolio of one NMD category at one valuation date (dossier 05 D.3). The weighted average "
       "maturity of a rolling tranche of maturity m is m / 2 (BCBS 368 footnote 38). A margin volatility the fit lacks is "
       "null with its reason.")
    one_of(d[p + "NmdModel"],
           {"margin_volatility": {"type": "number"}, "margin_volatility_reason": {"type": "null"}},
           {"margin_volatility": {"type": "null"}, "margin_volatility_reason": R(p + "Label")})
    d[p + "BucketDef"] = with_pairs(Ob({"bucket": BUCKET, "label": TXT, "midpoint_years": MID},
                                       "One of the 19 time buckets of SRP31.96 Table 3."))
    d[p + "NmdCap"] = Ob({
        "category": E(*[c[0] for c in cats]), "core_share_cap": UNIT, "core_maturity_cap_years": N(minimum=0),
        "reference": S(minLength=1),
    }, "SRP31 Table 4 cap of a category.")
    d[p + "Gamma"] = Ob({"shock": SHOCK, "gamma": N(minimum=0)}, "SRP31.119 Table 5 prepayment multiplier of a shock.")
    d[p + "UMult"] = Ob({"shock": SHOCK, "u": N(minimum=0)}, "SRP31.125 Table 6 term-deposit early redemption multiplier of a shock.")
    d[p + "Multipliers"] = Ob({
        "prepayment_gamma": ordered([pin(p + "Gamma", shock=sh, gamma=g) for sh, g in zip(SHOCKS, GAMMA)]),
        "term_deposit_u": ordered([pin(p + "UMult", shock=sh, u=u) for sh, u in zip(SHOCKS, UMULT)]), "reference": S(minLength=1),
    }, "The scenario multipliers of the prepayment rate and the term-deposit redemption rate, in the order of the six shocks.")
    d[p + "NmdCaps"] = ordered([pin(p + "NmdCap", category=c, core_share_cap=a, core_maturity_cap_years=b) for c, a, b in cats],
                               "The three SRP31 Table 4 caps, exactly the table's.")
    d[p + "DynItem"] = Ob({
        "item_id": S(minLength=1), "side": E("asset", "liability"), "balance": N(minimum=0), "rate0": N(), "spread": N(),
        "beta": N(minimum=0), "reprice_months": Int(0),
    }, "One item of the dynamic NII projection (the inputs of simulate_nii): a reset rate is spread + beta x r_t; reprice_months 0 "
       "reprices every month, k >= 1 keeps rate0 until month k and resets every k months.")
    d[p + "DynScenario"] = Ob({
        "scenario": E("base", "parallel-up", "parallel-down"), "shock_bp": N(),
        "short_rate_path": A(N(), 12, 36, "Annual short rate of each projected month, after the floor."),
        "monthly_nii": A(N(), 12, 36, "NII of each projected month, money."), "total": MONEY, "delta_vs_base": MONEY,
    }, "The projected NII under the base path or one parallel shock; delta_vs_base = base total minus this total (loss-positive).")
    d[p + "DynScenarios"] = ordered([pin(p + "DynScenario", scenario=sc) for sc in ("base", "parallel-up", "parallel-down")],
                                    "base, parallel-up, parallel-down, in that order.")
    d[p + "BsAssumption"] = one_of(Ob({
        "kind": E("constant", "growth"), "growth_annual": N(), "description": R(p + "Label"),
    }, "The balance-sheet assumption of the projection: a constant balance sheet (maturing or repricing flows replaced by "
       "identical new ones, DIS70.5) or an annual growth."),
        {"kind": C("constant"), "growth_annual": C(0)}, {"kind": C("growth")})
    return d


# ----------------------------------------------------------------------------------------------------------- C14


def c14_defs() -> dict:
    p = "c14"
    d = common(p, C14_CATS, "")
    d["c14Bank"] = Ob({
        "name": S(minLength=1), "cert": Int(1), "aggregates": C("real"), "behaviour": C("synthetic"), "notice": TXT,
    }, "The bank of the case (real FDIC aggregates, synthetic behaviour: SDD section 5).")
    d["c14Report"] = Ob({"report_date": DATE, "source": STR_OR_TXT("The provenance of the financials file", "c14-outputs 2.0.0"),
                         "fields": A(S(minLength=1), 1)},
                        "One FDIC call-report quarter read for the case and the financials fields taken from it.")
    d["c14Data"] = Ob({
        "call_reports": A(R("c14Report"), 1), "data_cutoff": DATE, "read_up_to_valuation_date": C(True), "rule": R("c14Label"),
    }, "The call reports read for the valuation date. Never one dated after it: data_cutoff is the latest report date read and "
       "is on or before the valuation date (a producer test checks the dates; a false flag fails).")
    d["c14Point"] = Ob({"tenor_years": N(exclusiveMinimum=0), "observed_yield": N(), "zero_rate": N()},
                       "One tenor of the curve: the observed par yield and the continuously compounded zero rate.")
    d["c14Curve"] = Ob({
        "date": DATE, "source": S(minLength=1), "observed_kind": C("par-yield"), "compounding": C("continuous"),
        "interpolation": S(minLength=1), "missing_tenors": A(N(exclusiveMinimum=0)),
        "points": A(R("c14Point"), 2), "zero_rates_at_midpoints": A(N(), 19, 19, "Zero rate at each bucket midpoint, bucket 1 first."),
    }, "The US Treasury par yield curve of the valuation date, bootstrapped to continuously compounded zero rates and read at "
       "the 19 midpoints. Tenors the date lacks are listed, never filled silently (dossier 08 C.2).")
    d["c14Item"] = one_of(Ob({
        "item_id": S(minLength=1), "label": TXT, "side": E("asset", "liability"),
        "category": E("cash", "securities-htm", "securities-afs", "loans-fixed", "loans-floating", "other-assets",
                      "deposits-transactional", "deposits-non-transactional", "deposits-time", "borrowings", "other-liabilities"),
        "behavioural_class": E("none", "nmd-retail-transactional", "nmd-retail-non-transactional", "nmd-wholesale",
                               "term-deposit", "prepayable-loan"),
        "repricing_type": E("fixed", "floating", "non-maturity"),
        "source_field": S(minLength=1),
        "reported_amount": nullable(MONEY), "reason_missing": nullable(R("c14Label")),
        "slotting_assumption": STR_OR_TXT("The slotting assumption of the item", "c14-outputs 2.0.0"), "amount": N(minimum=0),
        "cash_flows": Ob({"behavioural": A(R("c14Flow"), 1), "contractual": A(R("c14Flow"), 1)}),
    }, "One balance-sheet item slotted into the buckets. A call-report item the FDIC financials lack has reported_amount null "
       "with its reason and the slotting assumption that replaces it, never a fabricated number; a reported item has no reason. "
       "cash_flows under behavioural and contractual (every NMD in the overnight bucket) are net notional flows."),
        {"reported_amount": {"type": "number"}, "reason_missing": {"type": "null"}},
        {"reported_amount": {"type": "null"}, "reason_missing": R("c14Label")})
    d["c14BalanceSheet"] = Ob({
        "as_of": DATE, "items": A(R("c14Item"), 1), "total_assets": MONEY, "total_liabilities": MONEY,
    }, "The slotted balance sheet of the valuation date.")
    d["c14GapRow"] = Ob({"bucket": BUCKET, "midpoint_years": MID, "assets": MONEY, "liabilities": MONEY, "gap": MONEY},
                        "Repricing gap of one bucket: assets, liabilities and their difference (dossier 05 D.1).")
    d["c14DurationGap"] = Ob({
        "asset_value": MONEY, "liability_value": MONEY, "asset_duration_years": N(minimum=0),
        "liability_duration_years": N(minimum=0), "duration_gap_years": N(), "equity_change_100bp_up": MONEY,
    }, "Duration gap DGAP = D_A - (L / A) D_L and the first-order change in equity for +100 bp, -DGAP x A x 0.01 (dossier 05 D.2).")
    d["c14Ladder"] = Ob({
        "nmd_assumption": E("behavioural", "contractual"),
        "repricing_gap": ordered([pin("c14GapRow", bucket=k + 1, midpoint_years=m) for k, m in enumerate(MIDPOINTS)]), "delta_nii_gap_100bp_up": MONEY, "duration_gap": R("c14DurationGap"),
    }, "Rungs 1 and 2 of the IRRBB ladder under one NMD assumption. delta_nii_gap_100bp_up is loss-positive: "
       "-sum over t_k < 1 of G_k x 0.01 x (1 - t_k).")
    d["c14ShockResult"] = one_of(Ob({
        "shock": SHOCK,
        "shape_bp": A(N(), 19, 19, "Shock in basis points at each bucket midpoint before the floor."),
        "floor_bound_buckets": A(BUCKET, desc="Buckets where the post-shock floor binds."),
        "net_cash_flows": DENSE_MONEY,
        "eve": MONEY, "kao": MONEY, "delta_eve": MONEY, "delta_eve_share_tier1": N(),
        "delta_nii": nullable(MONEY), "delta_nii_reason": nullable(R("c14Label")),
    }, "The result of one prescribed shock: net_cash_flows are the scenario cash flows (the term-deposit redemption multiplier "
       "of SRP31.125 moves cash flows), eve = sum CF x exp(-R t), delta_eve = EVE_0 - EVE_i + KAO (positive is a loss). "
       "delta_nii exists for the two parallel shocks only (SRP31.90) and is null with its reason otherwise."),
        {"shock": E("parallel-up", "parallel-down"), "delta_nii": {"type": "number"}, "delta_nii_reason": {"type": "null"}},
        {"shock": E("steepener", "flattener", "short-up", "short-down"), "delta_nii": {"type": "null"},
         "delta_nii_reason": R("c14Label")})
    d["c14DynamicNii"] = Ob({
        "horizon_months": Int(12, 36), "balance_sheet_assumption": R("c14BsAssumption"), "items": A(R("c14DynItem"), 1),
        "scenarios": R("c14DynScenarios"),
    }, "Ladder rung 5 (dossier 05 D.6): the monthly NII over 12 to 36 months under the base path and the two parallel shocks of the "
       "2024 calibration, run-off replaced under the stated balance-sheet assumption, deposit betas in the items. Every path and "
       "monthly NII has horizon_months values.")
    d["c14EarEvarLevel"] = Ob({
        "level": N(exclusiveMinimum=0, exclusiveMaximum=1), "nii_quantile": MONEY, "eve_quantile": MONEY, "ear": MONEY, "evar": MONEY,
        "ear_se": N("Monte Carlo standard error of ear, money (engine ear_evar_mc_error).", minimum=0),
        "evar_se": N("Monte Carlo standard error of evar, money (engine ear_evar_mc_error).", minimum=0),
    }, "EaR and EVaR at one confidence level: ear = base NII minus the (1 - level) quantile of the NII paths, evar likewise for EVE "
       "(loss-positive; engine ear_evar).")
    d["c14EarEvar"] = Ob({
        "method": E("hw1f", "dns"), "n_paths": Int(2), "seed": Int(0), "horizon_months": Int(12, 36),
        "parameters": A(NAME_MAP, 1), "base_nii": MONEY, "base_eve": MONEY,
        "levels": ordered([pin("c14EarEvarLevel", level=0.95), pin("c14EarEvarLevel", level=0.99)], "The 95 and 99 percent levels."),
        "mc_error_method": C("batch-means"), "n_batches": Int(2),
    }, "Ladder rung 6 (dossier 05 D.5 and D.6): the distribution summary of NII and EVE under Hull-White one-factor or dynamic "
       "Nelson-Siegel scenario Monte Carlo, with the number of paths, the seed and, at each level, the Monte Carlo standard error of EaR and EVaR by batch means over n_batches contiguous batches of paths.")
    d["c14OutOfSample"] = one_of(Ob({
        "applicable": B, "projection_date": DATE, "realised_period_start": nullable(DATE), "realised_period_end": nullable(DATE),
        "projected_delta_nii": nullable(MONEY), "realised_delta_nii": nullable(MONEY), "relative_error": nullable(N(minimum=0)),
        "reason": nullable(R("c14Label")),
    }, "The out-of-sample row: the NII projection of this valuation date against the NII realised in the following period (the 2022 "
       "hiking cycle for 2021-Q4), read from call reports dated after the valuation date and used only here, never as an input. "
       "Not applicable (null with its reason) when no later period is read."),
        {"applicable": C(True), "realised_period_start": {"type": "string"}, "realised_period_end": {"type": "string"},
         "projected_delta_nii": {"type": "number"}, "realised_delta_nii": {"type": "number"}, "relative_error": {"type": "number"},
         "reason": {"type": "null"}},
        {"applicable": C(False), "realised_period_start": {"type": "null"}, "realised_period_end": {"type": "null"},
         "projected_delta_nii": {"type": "null"}, "realised_delta_nii": {"type": "null"}, "relative_error": {"type": "null"},
         "reason": R("c14Label")})
    d["c14Scenario"] = Ob({
        "calibration": E("2024", "2016"), "nmd_assumption": E("behavioural", "contractual"),
        "nmd_treatment": E("standardised-capped", "contractual-overnight"),
        "shock_size": R("c14ShockSize"), "floor": nullable(N(maximum=0), "Post-shock floor, not above zero (SRP31.93); null: none."),
        "base_eve": MONEY,
        "shocks": ordered([pin("c14ShockResult", shock=sh) for sh in SHOCKS], "The six shocks in the order of SHOCKS."),
        "eve_risk_measure": N("Money in the `currency` of the enclosing block.", minimum=0), "worst_shock": nullable(SHOCK), "outlier": R("c14Outlier"),
    }, "nmd_treatment says what the behavioural flows use: the capped used values of nmd_segments (standardised-capped) or every NMD in "
       "the overnight bucket (contractual-overnight). One calibration of the shock sizes under one NMD assumption: the six shocks in the order parallel-up, parallel-down, "
       "steepener, flattener, short-up, short-down, the EVE risk measure (the maximum over the six of the positive losses, "
       "SRP31.129) and its outlier test.")
    d["c14Comparison"] = Ob({
        "calibration": E("2024", "2016"), "shock": SHOCK,
        "delta_eve_behavioural": MONEY, "delta_eve_contractual": MONEY, "difference": MONEY,
    }, "Delta EVE with and without the behavioural NMD assumptions, always reported (dossier 05 D.7); difference = behavioural "
       "minus contractual.")
    d["c14Outputs"] = Ob({
        "kind": C("valuation-date"), "valuation_date": DATE, "quarter": S(pattern=r"^\d{4}-Q[1-4]$"), "currency": {**CUR, "const": "USD"},
        "sign_convention": R("c14Sign"), "units": R("c14Units"), "bank": R("c14Bank"), "data": R("c14Data"),
        "curve": R("c14Curve"), "assumptions": R("c14Assumptions"), "nmd_segments": A(R("c14NmdSegment"), 1),
        "balance_sheet": R("c14BalanceSheet"),
        "ladder": ordered([pin("c14Ladder", nmd_assumption="behavioural"), pin("c14Ladder", nmd_assumption="contractual")]),
        "scenarios": ordered([
            {"$ref": "#/$defs/c14Scenario", "properties": {
                "calibration": C(cal), "nmd_assumption": C(nmd), "nmd_treatment": C(treat),
                "shock_size": {"properties": {"origin": C(org), "currency": C("USD")}, "required": ["origin", "currency"]}}}
            for cal, org in (("2024", "srp31-table-2024"), ("2016", "srp31-table-2016"))
            for nmd, treat in (("behavioural", "standardised-capped"), ("contractual", "contractual-overnight"))],
            "2024 and 2016 calibrations, each with and without behavioural NMD, in this order."),
        "dynamic_nii": R("c14DynamicNii"), "ear_evar": R("c14EarEvar"), "out_of_sample": R("c14OutOfSample"),
        "behavioural_comparison": ordered([pin("c14Comparison", calibration=cal, shock=sh) for cal in ("2024", "2016") for sh in SHOCKS]),
    }, "C14 valuation-date outputs (outputs.kind valuation-date): IRRBB on a USD balance sheet at one valuation date, the six "
       "shocks of SRP31.90 in two calibrations and with and without behavioural NMD. The variant is the valuation date (the "
       "call reports are dated); the calibration and the NMD assumption are rows inside it so a view toggles them on one "
       "balance sheet.")
    # models
    d["c14ShockRow"] = Ob({"currency": E(*CCY21), "parallel_bp": N(minimum=0), "short_bp": N(minimum=0), "long_bp": N(minimum=0)})
    d["c14ShockTable"] = Ob({
        "calibration": E("2024", "2016"), "source": S(minLength=1), "data_window": S(minLength=1), "percentile": S(minLength=1),
        "rounding_bp": Int(1), "rows": A(R("c14ShockRow"), 21, 21),
    }, "A BCBS shock-size table transcribed as data, the 21 currencies in table order.")
    d["c14ShockShape"] = Ob({
        "x": C(4), "steepener_short": C(-0.65), "steepener_long": C(0.9), "flattener_short": C(0.8), "flattener_long": C(-0.6),
        "short_form": C("exp(-t_k / x)"), "long_form": C("1 - exp(-t_k / x)"),
        "reference": STR_OR_TXT("The reference of the shock shapes", "c14-models 2.0.0"),
    }, "The six shock shapes of SRP31.91 to SRP31.92 with x = 4.")
    d["c14OutlierRule"] = Ob({"threshold_share_tier1": C(0.15), "reference": S(minLength=1)})
    d["c14ParamChange"] = Ob({
        "parameter": S(minLength=1), "category": E(*[c[0] for c in C14_CATS]), "from_date": DATE, "to_date": DATE,
        "from_value": N(), "to_value": N(), "unit": S(minLength=1), "limit_breach_in_window": B, "flagged": B, "note": TXT,
    }, "A change of a behavioural parameter between two valuation dates; flagged when it changed in a window that holds a limit "
       "breach (dossier 05 D.7: the SVB lesson).")
    d["c14Fit"] = Ob({
        "currency": {**CUR, "const": "USD"}, "sign_convention": R("c14Sign"), "units": R("c14Units"), "bank": R("c14Bank"),
        "buckets": ordered([pin("c14BucketDef", bucket=k + 1, midpoint_years=m) for k, m in enumerate(MIDPOINTS)]),
        "shock_tables": ordered([
            {"$ref": "#/$defs/c14ShockTable", "properties": {"calibration": C(cal), "rounding_bp": C(rb), "rows": C([
                {"currency": c, "parallel_bp": t["parallel"][i], "short_bp": t["short"][i], "long_bp": t["long"][i]}
                for i, c in enumerate(CCY21)])}}
            for cal, rb, t in (("2024", 25, T2024), ("2016", 50, T2016))]),
        "applied_sizes": ordered([pin("c14ShockSize", origin="srp31-table-2024", currency="USD"),
                                  pin("c14ShockSize", origin="srp31-table-2016", currency="USD")]), "shock_shape": R("c14ShockShape"),
        "nmd_caps": R("c14NmdCaps"), "multipliers": R("c14Multipliers"),
        "nmd_models": A(R("c14NmdModel"), 1), "nmd_parameter_changes": A(R("c14ParamChange"), 1),
        "outlier": R("c14OutlierRule"),
    }, "C14 models: the 19 buckets, the 2024 and 2016 shock tables as data, the shock shapes, the NMD caps and multipliers, "
       "the replicating portfolios with their stability across windows, the deposit betas and the parameter-change flags.")
    return d


# ----------------------------------------------------------------------------------------------------------- C15


def c15_defs() -> dict:
    p = "c15"
    d = common(p, C15_CATS, "")
    d["c15Bank"] = Ob({
        "name": S(minLength=1), "synthetic": C(True), "notice": TXT, "seed": Int(0), "calibration_source": S(minLength=1),
    }, "The synthetic Banco Andino, calibrated to CMF aggregates (U5's calibration); fixtures say so.")
    d["c15Ur"] = Ob({
        "label": C("UR"), "code": C("CLF"), "treated_as_one_currency": C(True), "definition": TXT,
        "uf_value": N(exclusiveMinimum=0), "uf_value_currency": C("CLP"), "uf_date": DATE, "uf_source": S(minLength=1),
    }, "The UR currency of RAN 21-13 Annex 1: all CLP-indexed flows are treated as one currency (CLF, UF-indexed). UF amounts "
       "are CLF; uf_value is the CLP value of one UF on uf_date.")
    d["c15Variant"] = Ob({
        "id": E("long-uf", "short-uf", "cpi-surprise", "clp-steepener", "offset-on-off", "floors-active"),
        "label": TXT, "description": TXT, "parameters": A(NAME_MAP),
    }, "The SDD variant of the case (section 5): one document per variant.")
    d["c15Point"] = Ob({"tenor_years": N(exclusiveMinimum=0), "observed_yield": N(), "zero_rate": N()},
                       "One tenor: the observed BCCh yield and the fitted continuously compounded zero rate.")
    d["c15Curve"] = Ob({
        "curve": E("CLP", "UR"), "month": MONTH, "date": DATE, "source": S(minLength=1), "series_codes": A(S(minLength=1), 1),
        "attribution": S(minLength=1), "observed_kind": C("secondary-market-yield"), "compounding": C("continuous"),
        "fit": Ob({"model": E("nelson-siegel", "svensson"), "parameters": A(NAME_MAP, 1), "rmse_bp": N(minimum=0)}),
        "points": A(R("c15Point"), 1), "zero_rates_at_midpoints": A(N(), 19, 19, "Zero rate at each bucket midpoint, bucket 1 first."),
    }, "A BCCh F022 sovereign curve (CLP or UF) of the stated month, fitted to a zero curve and labelled as an adaptation: the "
       "attribution names the Banco Central de Chile as the owner of the source and the fit as Contraste's (BCCh terms, dossier "
       "08 C.7). A currency with fewer than four published secondary-market tenors (the engine's Nelson-Siegel fit needs four points) takes "
       "the Banco Central's monetary policy rate (F022.TPM.TIN.D001.NO.Z.D, the overnight rate) as an extra point at 1/360 year; it is a "
       "policy rate and not a yield, it is listed in series_codes, and the source says so. Only the CLP curve has such an anchor.")
    d["c15Curves"] = Ob({"clp": R("c15Curve"), "ur": R("c15Curve")})
    d["c15Item"] = Ob({
        "item_id": S(minLength=1), "label": TXT, "side": E("asset", "liability"),
        "category": E("cash", "securities", "loans-fixed", "loans-floating", "loans-uf", "deposits-nmd", "deposits-time",
                      "borrowings", "other"),
        "behavioural_class": E("none", "nmd-retail-operational", "nmd-retail-non-operational", "nmd-wholesale", "term-deposit",
                               "prepayable-loan"),
        "source": S(minLength=1), "amount": N(minimum=0), "cash_flows": A(R("c15Flow"), 1),
    }, "One synthetic Banco Andino item in the currency of its leg, slotted into the buckets (the Annex 1 NMD caps applied).")
    d["c15Leg"] = one_of(Ob({
        "leg": E("CLP", "UR"), "currency": E("CLP", "CLF"), "items": A(R("c15Item"), 1),
        "assets_total": MONEY, "liabilities_total": MONEY, "net_position": MONEY,
    }, "One leg of the banking book in the currency of the leg (CLF for the UR leg): net_position = assets minus liabilities. "
       "The CLP leg is in CLP and the UR leg is in CLF."),
        {"leg": C("CLP"), "currency": C("CLP")}, {"leg": C("UR"), "currency": C("CLF")})
    d["c15NiiSize"] = Ob({"currency": E("CLP", "CLF"), "parallel_bp": C(300), "origin": C("cmf-annex1")},
                         "The delta NII shock of Annex 1 Hoja 9: one parallel size, 300 bp for CLP and CLF.")
    d["c15LegEve"] = Ob({
        "shape_bp": A(N(), 19, 19, "Shock in basis points at each bucket midpoint before the floor."),
        "floor_bound_buckets": A(BUCKET), "net_cash_flows": DENSE_MONEY,
        "eve": MONEY, "kao": MONEY, "delta_eve": MONEY,
    }, "One leg under one shock, in the reporting currency (the UR leg converted at the UF value).")
    d["c15Pair"] = Ob({
        "delta_clp": MONEY, "delta_ur": MONEY, "opposite_signs": B, "with_offset": MONEY, "without_offset": MONEY, "used": MONEY,
    }, "The CLP and CLF pair. with_offset applies the 50 percent offsetting rule when the two have opposite signs; "
       "without_offset is the sum of the positive parts; used is the one the offset_rule state selects.")
    d["c15EveRow"] = Ob({
        "shock": SHOCK, "clp": R("c15LegEve"), "ur": R("c15LegEve"), "pair": R("c15Pair"), "total_delta_eve": MONEY,
    })
    d["c15EveMeasure"] = Ob({
        "base_eve_clp": MONEY, "base_eve_ur": MONEY, "rows": ordered([pin("c15EveRow", shock=sh) for sh in SHOCKS]),
        "delta_eve": MONEY, "worst_shock": nullable(SHOCK), "delta_eve_share_tier1": N(),
    }, "Annex 1 delta EVE: the maximum over the six shocks of the pair total (there is no other currency in this book).")
    d["c15NiiLeg"] = Ob({
        "shock_bp": N(), "cash_flows": A(MONEY, 6, 6, "Net repricing cash flows of the buckets with t_k < 1, in the reporting currency."),
        "floor_bound_buckets": A(BUCKET), "delta_nii": MONEY,
    }, "One leg under one parallel shock: delta NII = sum over the first six buckets of CF x (r0 - ri) x (1 - t_k).")
    d["c15NiiRow"] = Ob({
        "shock": E("parallel-up", "parallel-down"), "clp": R("c15NiiLeg"), "ur": R("c15NiiLeg"), "pair": R("c15Pair"),
    })
    d["c15NiiMeasure"] = Ob({
        "rows": ordered([pin("c15NiiRow", shock="parallel-up"), pin("c15NiiRow", shock="parallel-down")]), "max_pair": MONEY, "indexation_charge": MONEY, "delta_nii": MONEY,
        "worst_shock": nullable(E("parallel-up", "parallel-down")), "delta_nii_share_tier1": N(),
    }, "Annex 1 delta NII = the maximum over the two parallel shocks of the pair, plus the indexation charge.")
    d["c15FloorEffect"] = Ob({
        "leg": E("CLP", "UR"), "measure": E("delta-eve", "delta-nii"), "shock": SHOCK, "buckets_floored": Int(1),
        "delta_with_floor": MONEY, "delta_without_floor": MONEY, "effect": MONEY,
    }, "The effect of a binding post-shock floor on a leg's measure: with minus without.")
    d["c15FloorDistance"] = Ob({
        "leg": E("CLP", "UR"), "measure": E("delta-eve", "delta-nii"), "shock": SHOCK, "lowest_rate": N(), "bucket": Int(1, 19), "floor": N(),
        "distance_bp": N(), "binds": B,
    }, "The lowest post-shock rate of a leg under one shock (over the 19 bucket midpoints for the delta EVE, the first six for the delta NII), the "
       "bucket where it is, the floor of the leg and the distance between them in basis points (lowest_rate minus floor, times 10 000); binds is true "
       "exactly when the distance is at most zero. The rates are those of the engine's shocked curves before the floor is applied.")
    d["c15Floors"] = Ob({
        "ur_floor": C(-0.02), "other_floor": C(0.0), "rule": R("c15Label"), "effects": A(R("c15FloorEffect")),
        "distances": A(R("c15FloorDistance"), 16, 16, "One row per leg (CLP then UR) and per shock the floors apply to: the six delta EVE shocks "
                       "in the order of SHOCKS, then parallel-up and parallel-down for the delta NII. effects is non-empty exactly when a row binds."),
    }, "Annex 1 post-shock floors: -2 percent for UR rates, 0 percent for other currencies (or the pre-shock rate if lower), where each leg stands "
       "against them (distances) and the effect of every floor that binds (effects).")
    d["c15Offset"] = Ob({
        "state": E("on", "off", "compared"), "share": C(0.5), "applies_to": A(E("CLP", "CLF"), 2, 2), "rule": R("c15Label"),
        "reference": S(minLength=1),
    }, "The state of the CLP and CLF offset rule: on, off, or compared (both are in every pair; the rule applies in used).")
    d["c15Indexation"] = Ob({
        "rate": C(0.025), "net_position_uf_units": N(), "pn_ur": MONEY, "abs_pn_ur": MONEY, "charge": MONEY,
        "formula": STR_OR_TXT("The formula of the charge, with symbols and a legend", "c15-outputs 3.0.0"), "note": TXT,
    }, "The standardised indexation (reajustabilidad) charge: 2.5 percent of the absolute net UF position PN_UR (an implied "
       "2.5 percent inflation surprise). pn_ur = net UF position x uf_value, assets positive.")
    d["c15CpiScenario"] = nullable(Ob({
        "surprise_pp": N(), "effect": MONEY, "formula": STR_OR_TXT("The formula of the effect, with symbols and a legend", "c15-outputs 3.0.0"),
    }, "A CPI surprise applied to the net UF position, loss-positive: effect = -pn_ur x surprise_pp / 100."),
        "Null when the variant applies no CPI surprise.")
    d["c15ThresholdTest"] = Ob({
        "id": E("nii-tier1", "eve-tier1", "nii-margin"), "measure": MONEY, "base": MONEY, "ratio": N(),
        "threshold": N(minimum=0), "breached": B,
    }, "One prioritised-bank test of Annex 1: delta NII over Tier 1 (5 percent), delta EVE over Tier 1 (15 percent), delta NII over "
       "the 12-month net interest and indexation margin (18 percent).")
    d["c15Thresholds"] = Ob({
        "tier1": MONEY, "net_interest_and_indexation_margin_12m": MONEY, "tests": ordered([pin("c15ThresholdTest", id=i, threshold=t) for i, t in (("nii-tier1", 0.05), ("eve-tier1", 0.15), ("nii-margin", 0.18))]),
        "prioritised": B, "reference": STR_OR_TXT("The reference of the prioritised-bank tests", "c15-outputs 3.0.0"),
    }, "The banco priorizado tests; prioritised is true when any test is breached.")
    d["c15DynamicLeg"] = Ob({"leg": E("CLP", "UR"), "items": A(R("c15DynItem"), 1), "scenarios": R("c15DynScenarios")},
                            "The dynamic NII of one leg; balances and NII are in the reporting currency (the UR leg converted at the UF value).")
    d["c15EarEvarLevel"] = Ob({
        "level": N(exclusiveMinimum=0, exclusiveMaximum=1), "nii_quantile": MONEY, "eve_quantile": MONEY, "ear": MONEY, "evar": MONEY,
        "ear_se": N("Monte Carlo standard error of ear, money (engine ear_evar_mc_error).", minimum=0),
        "evar_se": N("Monte Carlo standard error of evar, money (engine ear_evar_mc_error).", minimum=0),
    }, "EaR and EVaR at one confidence level: ear = base NII minus the (1 - level) quantile of the NII paths, evar likewise for EVE "
       "(loss-positive; engine ear_evar).")
    d["c15EarEvar"] = Ob({
        "leg": E("CLP", "UR"), "method": E("hw1f", "dns"), "n_paths": Int(2), "seed": Int(0), "horizon_months": Int(12, 36),
        "parameters": A(NAME_MAP, 1), "base_nii": MONEY, "base_eve": MONEY,
        "levels": ordered([pin("c15EarEvarLevel", level=0.95), pin("c15EarEvarLevel", level=0.99)], "The 95 and 99 percent levels."),
        "mc_error_method": C("batch-means"), "n_batches": Int(2),
    }, "Ladder rung 6 (dossier 05 D.5 and D.6) for one leg: the distribution summary of the leg's NII and EVE under Hull-White one-factor "
       "or dynamic Nelson-Siegel scenario Monte Carlo, in the reporting currency (the UR leg converted at the UF value), with the number of "
       "paths, the seed and, at each level, the Monte Carlo standard error of EaR and EVaR by batch means over n_batches contiguous batches. "
       "base_nii is the base total of the leg's dynamic NII and base_eve the leg's base EVE.")
    d["c15DynamicNii"] = Ob({
        "horizon_months": Int(12, 36), "balance_sheet_assumption": R("c15BsAssumption"),
        "legs": ordered([pin("c15DynamicLeg", leg="CLP"), pin("c15DynamicLeg", leg="UR")]),
    }, "Ladder rung 5 for the CLP and UR legs (dossier 05 D.6). The EaR and EVaR of each leg are in ear_evar.")
    d["c15Outputs"] = Ob({
        "kind": C("annex1-variant"), "variant": R("c15Variant"), "as_of": DATE, "balance_sheet_month": MONTH, "calibration_month": MONTH,
        "curves_month": MONTH, "reporting_currency": {**CUR, "const": "CLP"},
        "sign_convention": R("c15Sign"), "units": R("c15Units"), "bank": R("c15Bank"), "ur_currency": R("c15Ur"),
        "curves": R("c15Curves"), "assumptions": R("c15Assumptions"), "nmd_segments": A(R("c15NmdSegment"), 1),
        "legs": ordered([pin("c15Leg", leg="CLP"), pin("c15Leg", leg="UR")], "The CLP leg and the UR leg, in that order."),
        "eve_shock_sizes": ordered([pin("c15ShockSize", currency="CLP", origin="cmf-annex1"), pin("c15ShockSize", currency="CLF", origin="cmf-annex1")]),
        "nii_shock_sizes": ordered([pin("c15NiiSize", currency="CLP"), pin("c15NiiSize", currency="CLF")]),
        "dynamic_nii": R("c15DynamicNii"),
        "ear_evar": ordered([pin("c15EarEvar", leg="CLP"), pin("c15EarEvar", leg="UR")], "The EaR and EVaR of the CLP leg and the UR leg, in that order."),
        "floors": R("c15Floors"), "offset_rule": R("c15Offset"), "indexation_charge": R("c15Indexation"),
        "cpi_scenario": R("c15CpiScenario"), "eve": R("c15EveMeasure"), "nii": R("c15NiiMeasure"), "thresholds": R("c15Thresholds"),
    }, "C15 annex1-variant outputs (outputs.kind annex1-variant): IRRBB on a CLP and UF balance sheet under RAN 21-13 Annex 1 for "
       "one SDD variant, balance sheet and curves as of one stated month. Money is in the reporting currency CLP; the UR leg is "
       "converted at the stated UF value.")
    # models
    d["c15TableRow"] = Ob({
        "basket": E("canasta-1", "canasta-2", "CLP", "UR-nii", "UR-eve"), "parallel_bp": N(minimum=0),
        "short_bp": nullable(N(minimum=0)), "long_bp": nullable(N(minimum=0)),
    }, "A row of the Annex 1 Hoja 9 shock table; '-' in the source is null.")
    d["c15FloorRule"] = Ob({"ur_floor": C(-0.02), "other_floor": C(0.0), "reference": S(minLength=1)})
    d["c15ThresholdRule"] = Ob({"id": E("nii-tier1", "eve-tier1", "nii-margin"), "threshold": N(minimum=0), "base": S(minLength=1)})
    d["c15CurveModel"] = Ob({
        "curve": E("CLP", "UR"), "month": MONTH, "series_codes": A(S(minLength=1), 1), "model": E("nelson-siegel", "svensson"),
        "parameters": A(NAME_MAP, 1), "rmse_bp": N(minimum=0), "attribution": S(minLength=1),
    }, "The curve fit of one BCCh series family (labelled as an adaptation).")
    d["c15Target"] = Ob({
        "metric": S(minLength=1), "unit": S(minLength=1), "target": N(), "achieved": N(), "source": S(minLength=1), "as_of": DATE,
    })
    d["c15Prepayment"] = Ob({
        "model": E("cpr-constant", "psa"), "cpr_base": UNIT, "psa_percent": nullable(N(minimum=0)),
        "source_kind": SOURCE_KIND, "source": S(minLength=1),
    }, "The base prepayment behaviour (CPR, or a PSA multiple of the 100 percent PSA curve).")
    d["c15Fit"] = Ob({
        "reporting_currency": {**CUR, "const": "CLP"}, "sign_convention": R("c15Sign"), "units": R("c15Units"), "bank": R("c15Bank"),
        "buckets": ordered([pin("c15BucketDef", bucket=k + 1, midpoint_years=m) for k, m in enumerate(MIDPOINTS)]),
        "annex1_table": ordered([{"$ref": "#/$defs/c15TableRow", "properties": {"basket": C(b), "parallel_bp": C(pa), "short_bp": C(sh), "long_bp": C(lg)}}
                                 for b, pa, sh, lg in CMF_TABLE]),
        "eve_shock_sizes": ordered([pin("c15ShockSize", currency="CLP", origin="cmf-annex1"), pin("c15ShockSize", currency="CLF", origin="cmf-annex1")]), "floors": R("c15FloorRule"),
        "prioritised_thresholds": ordered([pin("c15ThresholdRule", id=i, threshold=t) for i, t in (("nii-tier1", 0.05), ("eve-tier1", 0.15), ("nii-margin", 0.18))]), "offset_share": C(0.5), "indexation_rate": C(0.025),
        "multipliers": R("c15Multipliers"), "nmd_caps": R("c15NmdCaps"),
        "curve_models": A(R("c15CurveModel"), 2, 2), "calibration_targets": A(R("c15Target"), 1),
        "nmd_models": A(R("c15NmdModel"), 1), "prepayment": R("c15Prepayment"),
    }, "C15 models: the 19 buckets, the CMF Annex 1 table, floors and thresholds as data, the offset share and the indexation "
       "rate, the BCCh curve fits, the Banco Andino calibration targets and the behavioural fits.")
    return d


def main() -> None:
    d14, d15 = c14_defs(), c15_defs()
    variant_schema("C14", "variant-valuation-date", "valuation-date", "C14 valuation-date variant",
                   "Catalog row c14-outputs 1.0.0: one valuation date of the IRRBB case on a USD balance sheet (outputs.kind "
                   "valuation-date), real FDIC aggregates and synthetic behaviour.", "c14Outputs", d14)
    models_schema("C14", "C14 models",
                  "Catalog row c14-models 1.0.0: the C14 models artifact (buckets, the 2024 and 2016 shock tables, shapes, NMD "
                  "caps, multipliers, replicating portfolios, parameter-change flags).", "c14Fit", d14)
    variant_schema("C15", "variant-annex1-variant", "annex1-variant", "C15 annex1-variant variant",
                   "Catalog row c15-outputs 2.0.0: one SDD variant of the IRRBB case on a CLP and UF balance sheet under RAN "
                   "21-13 Annex 1 (outputs.kind annex1-variant).", "c15Outputs", d15)
    models_schema("C15", "C15 models",
                  "Catalog row c15-models 1.0.0: the C15 models artifact (buckets, the CMF Annex 1 table, floors, thresholds, "
                  "curve fits, calibration targets, behavioural fits).", "c15Fit", d15)


if __name__ == "__main__":
    main()
