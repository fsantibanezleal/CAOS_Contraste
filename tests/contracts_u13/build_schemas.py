"""Builds the four U13-S schema files (docs/contracts/schemas/c18).

Run: ``python tests/contracts_u13/build_schemas.py``. Deterministic, standard library only. The schema files are the contract and
are committed; this script is the compact source they are written from, so a name two files of one case share has one definition
(the generator of the TypeScript types fails on a clash). Conventions of docs/contracts/catalog.md: one folder per case, a
``case_id`` const, ``outputs.kind`` on the variant, case-prefixed ``$defs``, the ``variant-envelope`` composition with
``unevaluatedProperties: false``, every object closed, nothing optional.

Scope (decision E1 of the U13 sizing, 2026-10-19): C18 only. C19 stays planned, so there is no ``schemas/c19`` folder and no C19
definition anywhere.

Variants of C18 (decision of U13-S, from SDD l.390 and decisions Q9, Q12 of the sizing):

* ``scenario`` (c18-outputs): one document per scenario, ``scenario_id`` in baseline, eba-2025-adverse, fed-2026-severely-adverse,
  ngfs-delayed-transition; the scenario paths as used, the satellite projections, the losses by risk and year, the capital plan
  (base, stress without and with mitigation), the internal capital target, the P2G proxy, the Annex 3 summary, the loss-only CET1
  path with the labelled PPNR row, the out-of-time back-cast, and the aggregation block;
* ``aggregation`` (c18-outputs-aggregation): the t-copula variant on the baseline scenario, the band over the nu set at the base
  correlation matrix and under the market-credit 0.8 stress, the copula-choice sensitivity and the Rosenberg and Schuermann
  reference run;
* ``reverse`` (c18-outputs-reverse): the failure point (CET1 at the Chilean legal minimum stack), the scenario z*, its Mahalanobis
  distance and plausibility, the loss at z*;
* ``models`` (c18-models): the satellite fits (window ending 2019, agency regressors only), the factor space, the aggregation
  parameters, the bank anchors, the scenario sources, the EBA rules of the capital engine and the named parameters.

What JSON Schema states (strictness both ways, the labels, the windows, the horizon and the confidence level) is here; what it cannot
state (an identity between numbers) is ``semantics.py``.
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


def C(value, desc: str | None = None) -> dict:
    d: dict = {"const": value}
    if desc:
        d["description"] = desc
    return d


B = {"type": "boolean"}


def one_of(ob: dict, *alternatives: dict) -> dict:
    """Adds a ``oneOf`` of coupled-field alternatives to a closed object: each alternative narrows properties the object already
    declares, so ``additionalProperties: false`` still holds."""
    ob["oneOf"] = [{"properties": a} for a in alternatives]
    return ob


def when(ob: dict, field: str, value, then: dict, otherwise: dict | None = None) -> dict:
    """``if field == value then <properties>`` (else ``<properties>``) on a closed object, narrowing declared properties."""
    ob.setdefault("allOf", []).append({
        "if": {"properties": {field: {"const": value}}, "required": [field]},
        "then": {"properties": then},
        **({"else": {"properties": otherwise}} if otherwise is not None else {}),
    })
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


def write(name: str, doc: dict) -> None:
    path = SCHEMAS / "c18" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------------------------------------- constants

RISKS = ["credit", "market", "irrbb", "operational"]
FED_TYPES = ["commercial-industrial", "commercial-real-estate", "residential", "credit-cards", "other-consumer"]
#: the Board's charge-off table columns of each type (cases/c10/fed.py COLUMNS), the series the satellites are fitted on
FED_SERIES = {"commercial-industrial": "CI", "commercial-real-estate": "RECI", "residential": "RERES", "credit-cards": "CONCC",
              "other-consumer": "CONOTH"}
CLASSES = ["commercial", "consumer", "mortgage"]
SCENARIOS = ["baseline", "eba-2025-adverse", "fed-2026-severely-adverse", "ngfs-delayed-transition"]
PROVIDERS = ["fed", "eba-esrb", "ngfs"]
#: the agency series of the Federal Reserve historic table a satellite may read (decision Q7, dossier 08 D.1): the BBB corporate yield and
#: the third-party index levels (equity, house price, CRE price, volatility) are not in the list, so a document that reads them fails
AGENCY_REGRESSORS = ["real_gdp_growth", "unemployment_rate", "cpi_inflation", "treasury_3m", "treasury_5y", "treasury_10y",
                     "mortgage_rate", "prime_rate"]
BAND_METHODS = ["lower-bound", "simple-sum", "variance-covariance", "gaussian-copula", "t-copula", "worst-case"]
PRODUCERS = {
    "credit": "credit-grouped-copula-c07-segments",
    "market": "market-c11-mixed-portfolio-scaled-to-market-rwa",
    "irrbb": "irrbb-engine-simulation-c15-curve-and-book",
    "operational": "operational-oprisk-aggregate-c17-parameters-scaled",
}
PAT_DATE = "^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$"
PAT_QEND = "^[0-9]{4}-(03-31|06-30|09-30|12-31)$"
#: a satellite fit window ends in 2019 at the latest and starts in 1985 at the earliest (the Board's charge-off table starts 1985 Q1,
#: SDD l.390: satellites fitted 1985-2019): a window that reaches 2020 or later does not match
PAT_FIT = "^(198[5-9]|199[0-9]|200[0-9]|201[0-9])-(03-31|06-30|09-30|12-31)$"
QEND = S("A quarter end as an ISO date.", pattern=PAT_QEND)
DATE = S("An ISO date.", pattern=PAT_DATE)
FIT_DATE = S("A quarter end between 1985-03-31 and 2019-12-31: the satellites are fitted on 1985-2019 only.", pattern=PAT_FIT)
LABEL = {"type": "string", "enum": ["convention", "case assumption"],
         "description": "Every named parameter is a convention or an assumption of the case, never a regulatory value."}
INFO = C("information-not-capital", "A diversified or allocated figure is information for the validator and never a capital claim (dossier 05 l.519).")
HORIZON = C(1, "One horizon for every marginal: one year (decision Q5).")
LEVEL = C(0.999, "One confidence level for every marginal: 99.9 percent, as a decimal (decision Q5).")
BASIS = C("economic-capital-var-less-el", "Capital of a risk and of an aggregate is EC = VaR(0.999, 1 year) less the expected loss, EC_q = VaR_q(L) - EL "
                                      "(dossier 04 l.652-653, BCBS 2005 explanatory note section 4.4); the expected loss is additive, so the simple sum of the "
                                      "marginals equals the comonotonic total. A marginal whose severity has an infinite mean has no expected loss: its EC is the VaR "
                                      "alone, labelled (dossier 05 l.482).")
APPROX = C("contraste-approximation", "The proxy is a Contraste approximation consistent with FAQ 24; the CMF calibration grid is not public.")
#: the identity link is the linear form of the Federal Reserve's own PD regression (dossier 05 l.399): no quarter is floored or dropped
LINKS = ["probit", "logit", "identity"]
#: the Board's table is missing RECI and RERES from 1985Q1 to 1990Q4, so their windows start at the first available quarter, 1991Q1
FIRST_QUARTER = {"commercial-industrial": "1985-03-31", "commercial-real-estate": "1991-03-31", "residential": "1991-03-31",
                 "credit-cards": "1985-03-31", "other-consumer": "1985-03-31"}
IDENTITY_TYPES = ["commercial-real-estate", "residential"]
RATE = N("A net charge-off rate as a decimal. Signed: net recoveries make a rate zero or negative (the Board's table holds both).",
         exclusiveMinimum=-1, exclusiveMaximum=1)
ADAPT = C("us-calibrated-adaptation", "The satellites are fitted on United States charge-off rates and applied to Banco Andino: a US-calibrated adaptation (decision Q6).")
UNIT_SHARE = N(minimum=0, maximum=1)
MONEY = N("Money in CLP millions.")
MONEY0 = N("Money in CLP millions, not below zero.", minimum=0)
RATIO = N("A ratio as a decimal.")
YEAR3 = Int(1, 3, "Year of the three-year planning horizon (T+1 to T+3, RAN 21-13 section II.5.3).")

ANNEX3_ROWS = [  # F7 of the U13 research addendum (CMF RAN 21-13 Annex 3, Circular 2.365): row id and the label as printed
    ("1", "Ratios de capital"), ("1.1", "PE / APR"), ("1.2", "T1 / APR"), ("1.3", "CET1 / APR"),
    ("2", "Patrimonio efectivo"), ("2.T2", "T2"), ("2.AT1", "AT1"), ("2.CET1", "CET1"), ("3", "APR"),
    ("4", "Cuantificacion del capital necesario"), ("4.1", "Riesgo de credito"), ("4.1.1", "Metodo estandar"),
    ("4.1.2", "Modelo interno"), ("4.2", "Riesgo de mercado (ME)"), ("4.3", "Riesgo operacional (ME)"),
    ("4.4", "Riesgo de concentracion"), ("4.4.1", "Individual"), ("4.4.2", "Sectorial"), ("4.4.3", "Otro tipo"),
    ("4.5", "RMLB"), ("4.6", "Riesgo estrategico"), ("4.7", "Riesgo reputacional"), ("4.8", "Otros riesgos materiales"),
    ("5", "OI"),
    ("6", "Cuantificacion del capital necesario por riesgos no cubiertos en pilar 1 (4.4+4.5+4.6+4.7+4.8)"),
    ("7", "Exigencia minima de PE, en periodo de planificacion (8%+7.1+7.2)"),
    ("7.1", "Exigencia adicional de PE por art.66 quater (banco sistemico)"),
    ("7.2", "Exigencia adicional de PE por art.66 quinquies"),
    ("8", "Cuantificacion del capital necesario por riesgos no cubiertos en pilar 1, y no exigidos por art.66 quinquies (6-7.2)"),
    ("9", "Colchones de conservacion y contra ciclico, en periodo de planificacion (art.66 bis y 66 ter)"),
    ("10.1", "Impacto en indice de capital basico de las pruebas de tension severas, sin mitigacion"),
    ("10.2", "Impacto en indice de capital basico de las pruebas de tension severas, con mitigacion"),
    ("11", "Componente d) del OI"),
    ("12", "Holgura de indice de patrimonio efectivo respecto del OI (1.1 - 5)"),
]
#: the NiGEM variable names and units of the NGFS Phase 5 runs the case reads (F8 of the addendum, copied as printed, the GDP unit has two spaces)
NGFS_VARIABLES = [
    ("Unemployment rate ; %(combined)", "Abs. difference"),
    ("Central bank Intervention rate (policy interest rate) ; %(combined)", "Abs. difference"),
    ("Long term interest rate ; %(combined)", "Abs. difference"),
    ("Gross Domestic Product (GDP)(combined)", "% difference,  2017 PPP ; US$ Bn"),
]
NGFS_BASELINE_VARIABLES = [
    ("Unemployment rate ; %", "%"), ("Central bank Intervention rate (policy interest rate) ; %", "%"),
    ("Long term interest rate ; %", "%"), ("Gross Domestic Product (GDP)", "2017 PPP ; US$ Bn"),
]


def exact_rows(item: dict, key: str, values: list, desc: str) -> dict:
    """An array holding exactly the given values of ``key``, each once (maxItems and one ``contains`` per value)."""
    arr = A(item, len(values), len(values), desc)
    arr["allOf"] = [{"contains": {"properties": {key: {"const": v}}, "required": [key]}} for v in values]
    return arr


# ---------------------------------------------------------------------------------------------------------------- defs


def link_for(ty: str) -> dict:
    """The link a Fed loan type uses: the identity on RECI and RERES (non-positive quarters), the probit or logit elsewhere."""
    return C("identity") if ty in IDENTITY_TYPES else E("probit", "logit")


def sat_alt(ty: str, series: str) -> dict:
    """A projection alternative: the type, its series, its link and, for the probit and logit, a rate in (0, 1)."""
    alt: dict = {"fed_loan_type": C(ty), "series_id": C(series), "link": link_for(ty)}
    if ty not in IDENTITY_TYPES:
        alt["quarters"] = {"items": {"properties": {"rate": {"exclusiveMinimum": 0, "exclusiveMaximum": 1}}}}
    return alt


def backcast_alt(ty: str, series: str) -> dict:
    return {"fed_loan_type": C(ty), "series_id": C(series), "link": link_for(ty),
            "fit_window": {"properties": {"start": C(FIRST_QUARTER[ty])}}}


def fit_alt(ty: str, series: str) -> dict:
    """A satellite alternative: the type, its link, the first quarter the Board publishes as the window start and, for the probit and logit,
    no non-positive quarter in the window."""
    alt: dict = {"fed_loan_type": C(ty), "series_id": C(series), "link": link_for(ty),
                 "sample_window": {"properties": {"start": C(FIRST_QUARTER[ty])}}}
    if ty not in IDENTITY_TYPES:
        alt["non_positive_quarters_in_window"] = C(0)
    return alt



def common_defs() -> dict:
    d: dict = {}
    d["c18Named"] = Ob({
        "name": S(minLength=1), "value": N(), "unit": S(minLength=1), "label": LABEL, "basis": TXT,
    }, "A named parameter: a required name, value and unit, the label convention or case assumption, and the basis it was taken from.")
    d["c18NamedSet"] = Ob({
        "name": S(minLength=1), "values": A(N(), 1), "unit": S(minLength=1), "label": LABEL, "basis": TXT,
    }, "A named parameter that is a set of values (the nu set), with the same label rule.")
    d["c18NamedMatrix"] = Ob({
        "name": S(minLength=1),
        "order": {"type": "array", "const": RISKS, "description": "The row and column order of the matrix: credit, market, irrbb, operational."},
        "matrix": A(A(N(minimum=-1, maximum=1), 4, 4), 4, 4),
        "unit": C("correlation"), "label": LABEL, "basis": TXT,
    }, "A named inter-risk correlation matrix with the same label rule; symmetry, the unit diagonal and positive semi-definiteness are checked "
       "by semantics.py (the engine's check_correlation).")
    d["c18NamedConvention"] = Ob({
        "name": S(minLength=1), "value": N(), "unit": S(minLength=1), "label": C("convention"), "basis": TXT,
    }, "A named parameter that is a convention by definition (the market level and horizon factors).")
    d["c18MarketScaling"] = Ob({
        "name": C("market_horizon_scaling"),
        "value": N("The combined multiplier: the level factor times the horizon factor.", exclusiveMinimum=0),
        "unit": S(minLength=1),
        "label": C("convention"),
        "basis": TXT,
        "source_confidence_level": C(0.99, "C11's mixed-portfolio measure is at 99 percent (docs/contracts/schemas/c11/models.schema.json)."),
        "source_horizon_days": C(1, "C11's measure is a one-day measure."),
        "trading_days_per_year": C(250),
        "level_factor": R("c18NamedConvention"),
        "horizon_factor": R("c18NamedConvention"),
    }, "The market marginal's conversion from C11's 99 percent one-day figures to 99.9 percent and one year: the normal quantile ratio z_0.999 / "
       "z_0.99 and the square root of 250, both named conventions (W4), and the combined multiplier.")
    d["c18FxDerivation"] = Ob({
        "kind": C("observed-exchange-rate"),
        "pair": C("EUR/CLP"),
        "observation_date": DATE,
        "source": C("Banco Central de Chile, Base de Datos Estadísticos, daily exchange rate of the euro in Chilean pesos",
                    "The stated public source of the rate; the series id the bake reads is recorded in source_series (not named here: UNVERIFIED)."),
        "source_url": C("https://si3.bcentral.cl/Siete/es/Siete/API"),
        "source_series": S("The BDE series id the bake read.", minLength=1),
    }, "How the rate is derived at bake time: the observed EUR to CLP rate of the as-of date.")
    d["c18AssetDerivation"] = Ob({
        "kind": C("asset-ratio"),
        "banco_andino_assets_clp_m": N("Banco Andino total assets, CLP millions, from the C15 and C07 balance sheet.", exclusiveMinimum=0),
        "c17_bank_assets_eur_m": N("The stated assets of the C17 synthetic bank, EUR millions (C17 models-generator generator.assets_eur_bn times 1000).",
                                   exclusiveMinimum=0),
        "converted_at": C("operational_conversion_rate"),
    }, "How the scaling is derived at bake time: Banco Andino's total assets over the C17 synthetic bank's stated assets, in one currency.")
    d["c18DerivedFx"] = Ob({
        "name": C("operational_conversion_rate"), "value": N(exclusiveMinimum=0), "unit": C("CLP per EUR"), "label": LABEL, "basis": TXT,
        "derivation": R("c18FxDerivation"),
    }, "The EUR to CLP rate of the as-of date, derived at bake time from a stated public source; the contract fixes no number.")
    d["c18DerivedAssets"] = Ob({
        "name": C("asset_scaling"), "value": N(exclusiveMinimum=0), "unit": C("Banco Andino assets over the assets of the C17 bank"), "label": LABEL,
        "basis": TXT, "derivation": R("c18AssetDerivation"),
    }, "The asset scaling of the C17 generator frequency, derived at bake time; the contract fixes no number.")
    d["c18Ref"] = Ob({"method": E(*BAND_METHODS), "nu": nullable(N(exclusiveMinimum=2))},
                     "A reference to a row of the band: its method and, for a t copula, its degrees of freedom.")
    d["c18Marginal"] = one_of(Ob({
        "risk": E(*RISKS),
        "horizon_years": HORIZON,
        "confidence_level": LEVEL,
        "el_clp_m": nullable(MONEY0, "The expected loss; null exactly when the severity has an infinite mean (el_status undefined)."),
        "el_status": E("finite", "undefined (infinite mean)"),
        "var_clp_m": MONEY0,
        "es_clp_m": MONEY0,
        "ec_clp_m": MONEY0,
        "ec_basis": E("var-less-el", "var-alone-infinite-mean"),
        "ec_label": nullable(TXT, "The label of an EC that is the VaR alone (an infinite-mean severity); null on the EC = VaR - EL basis."),
        "var_se_clp_m": nullable(N(minimum=0), "The Monte Carlo standard error of the VaR; null where the marginal is analytic."),
        "producer": E(*PRODUCERS.values()),
        "source_documents": A(S(minLength=1), 1, desc="The committed documents or engine calls the marginal is computed from."),
        "scaling": Ob({"statement": TXT, "parameters": A({"oneOf": [R("c18Named"), R("c18MarketScaling"), R("c18DerivedFx"), R("c18DerivedAssets")]})},
                      "How the source was scaled to Banco Andino: a statement and every scaling parameter named with its label."),
    }, "One marginal at one horizon and one confidence level (decision Q5): its expected loss, VaR, ES and EC = VaR - EL (or the VaR alone when the "
       "expected loss is undefined), its source and its scaling."),
        {"risk": C("credit"), "producer": C(PRODUCERS["credit"])},
        {"risk": C("market"), "producer": C(PRODUCERS["market"]), "scaling": {"properties": {"parameters": {"allOf": [
            {"contains": {"properties": {"name": {"const": n}}, "required": ["name"]}} for n in ("market_rwa_share", "market_horizon_scaling")]}}}},
        {"risk": C("irrbb"), "producer": C(PRODUCERS["irrbb"])},
        {"risk": C("operational"), "producer": C(PRODUCERS["operational"]), "scaling": {"properties": {"parameters": {"allOf": [
            {"contains": {"properties": {"name": {"const": n}}, "required": ["name"]}} for n in ("asset_scaling", "operational_conversion_rate")]}}}})
    when(d["c18Marginal"], "el_status", "finite", {"el_clp_m": MONEY0, "ec_basis": C("var-less-el"), "ec_label": {"type": "null"}})
    when(d["c18Marginal"], "el_status", "undefined (infinite mean)", {"risk": C("operational"), "el_clp_m": {"type": "null"},
                                                                        "ec_basis": C("var-alone-infinite-mean"), "ec_label": TXT})
    d["c18BandRow"] = when(when(Ob({
        "method": E(*BAND_METHODS),
        "nu": nullable(N(exclusiveMinimum=2), "Degrees of freedom: set for a t copula row, null otherwise."),
        "capital_clp_m": N("Money in CLP millions. Signed on the lower-bound row only: the best VaR less the sum of the expected losses can be negative "
                           "(Table 4 of the authors' paper, d = 56); every other row is not below zero."),
        "diversification_factor": N("DF = capital of the row over the simple sum of the marginals; signed on the lower-bound row only."),
        "status": E("headline-capital", "information-not-capital"),
        "label": TXT,
        "horizon_years": HORIZON,
        "confidence_level": LEVEL,
        "mc_se_clp_m": nullable(N(minimum=0)),
    }, "One rung of the dependence-uncertainty band (decision Q12). Only the simple sum is the headline capital; every other row is information."),
        "method", "simple-sum", {"status": C("headline-capital"), "nu": {"type": "null"}},
        {"status": INFO}), "method", "t-copula", {"nu": N(exclusiveMinimum=2)}, None)
    # a t row needs a nu; the other rows have none
    for m in ("lower-bound", "variance-covariance", "gaussian-copula", "worst-case"):
        when(d["c18BandRow"], "method", m, {"nu": {"type": "null"}})
    for m in ("simple-sum", "variance-covariance", "gaussian-copula", "t-copula", "worst-case"):
        when(d["c18BandRow"], "method", m, {"capital_clp_m": {"minimum": 0}, "diversification_factor": {"minimum": 0}})
    band = A(R("c18BandRow"), 6, 12, "The band: the lower bound, the simple sum, variance-covariance, Gaussian, t at every nu of the set, the worst case "
                                      "(decision Q12). The comonotonic total equals the simple sum under the EC basis and is not a seventh row.")
    band["allOf"] = [{"contains": {"properties": {"method": {"const": m}}, "required": ["method"]}} for m in BAND_METHODS]
    d["c18Band"] = band
    d["c18ModelRisk"] = Ob({
        "status": INFO,
        "label": TXT,
        "set_of_models": C("band-rows", "The set of aggregation models is the rows of the band (dossier 06 l.692-698)."),
        "reference_model": R("c18Ref"),
        "barrieu_scandolo": Ob({
            "rho_x0_clp_m": MONEY0, "rho_max_clp_m": MONEY0, "rho_min_clp_m": MONEY,
            "am": N("AM = max rho / rho(X0) - 1 (06 l.692-698)."),
            "rm": N("RM = (max rho - rho(X0)) / (max rho - min rho), in [0, 1].", minimum=0, maximum=1),
        }),
        "glasserman_xu": Ob({
            "quantity": TXT,
            "relative_entropy_budget": N(exclusiveMinimum=0),
            "theta": N(exclusiveMinimum=0),
            "baseline_clp_m": MONEY0,
            "worst_case_clp_m": MONEY0,
        }, "The worst case by reweighting the baseline sample, m = exp(theta V) / E[exp(theta V)], theta set so that the entropy budget binds (06 l.684-691)."),
    }, "The model risk measures beside the band, sensitivity information and never a capital figure (06 l.699-704).")
    d["c18Euler"] = Ob({
        "status": INFO,
        "label": TXT,
        "risk_measure": C("es"),
        "level": LEVEL,
        "horizon_years": HORIZON,
        "copula": Ob({"family": E("gaussian", "t"), "nu": nullable(N(exclusiveMinimum=2))}),
        "es_total_clp_m": MONEY0,
        "allocation": exact_rows(Ob({
            "risk": E(*RISKS), "contribution_clp_m": MONEY0, "share": UNIT_SHARE,
        }), "risk", RISKS, "ES contributions E[L_i | L >= VaR], one row per risk, in the order of the marginals."),
        "additivity": Ob({"sum_clp_m": MONEY0, "relative_error": N(minimum=0), "tolerance": N(exclusiveMinimum=0)}),
    }, "The Euler allocation of the aggregate ES, information for the validator and never a capital claim.")
    d["c18Diversification"] = Ob({
        "status": INFO,
        "label": TXT,
        "reference_row": R("c18Ref"),
        "factor": N("DF = rho(L) / sum rho(L_i) of the reference row.", minimum=0),
        "benefit": N("1 - DF."),
        "euler_benefit_by_risk": exact_rows(Ob({
            "risk": E(*RISKS), "benefit": N("1 - rho(L_i | L) / rho(L_i), on ES contributions."),
        }), "risk", RISKS, "One Euler diversification benefit per risk."),
    }, "The diversification, information for the validator and never a capital claim.")
    d["c18Aggregation"] = Ob({
        "capital_basis": BASIS,
        "horizon_years": HORIZON,
        "confidence_level": LEVEL,
        "correlation": R("c18NamedMatrix"),
        "nu_set": R("c18NamedSet"),
        "marginals": exact_rows(R("c18Marginal"), "risk", RISKS, "The four marginals in the order credit, market, irrbb, operational."),
        "headline": Ob({
            "method": C("simple-sum", "The headline capital of C18 is the simple sum (IAPE, 03 l.185-190; ECB, 01 l.846)."),
            "capital_clp_m": MONEY0,
            "label": TXT,
        }),
        "band": R("c18Band"),
        "model_risk": R("c18ModelRisk"),
        "euler": R("c18Euler"),
        "diversification": R("c18Diversification"),
    }, "The aggregation block: the simple sum as the headline, the band with the model risk measures beside it, the Euler allocation and the "
       "diversification (both information), one horizon and one confidence level, the source and scaling of every marginal.")
    d["c18Env"] = Ob({
        "name": C("Banco Andino"),
        "synthetic": C(True),
        "notice": TXT,
        "as_of": DATE,
    }, "The synthetic bank, labelled.")
    d["c18Units"] = Ob({
        "money": C("CLP millions"), "ratio": C("decimal"), "dates": C("ISO date; quarters as the date of the quarter end"),
    }, "The units of the document: money in CLP millions, ratios as decimals, quarters as ISO dates of the quarter end.")
    return d


def scenario_defs() -> dict:
    d = common_defs()
    d["c18PathPoint"] = Ob({"date": DATE, "value": N()})
    d["c18QPoint"] = Ob({"date": QEND, "value": N()})
    d["c18Path"] = Ob({
        "variable": S("The variable as the source names it (the NGFS variables carry the NiGEM names exactly).", minLength=1),
        "unit": S(minLength=1),
        "maps_to_regressor": E(*AGENCY_REGRESSORS),
        "frequency": E("quarterly", "annual"),
        "vintage_date": DATE,
        "level_rule": one_of(Ob({
            "kind": E("level", "baseline-plus-deviation", "baseline-times-percent-deviation"),
            "baseline": nullable(A(R("c18PathPoint"), 1), "The baseline levels a deviation path is added to or multiplied with (NGFS scenario runs hold deviations from the Baseline run, F8)."),
        }), {"kind": C("level"), "baseline": {"type": "null"}},
            {"kind": C("baseline-plus-deviation"), "baseline": A(R("c18PathPoint"), 1)},
            {"kind": C("baseline-times-percent-deviation"), "baseline": A(R("c18PathPoint"), 1)}),
        "source": A(R("c18PathPoint"), 1, desc="The published path as the source states it (the deviation for a deviation path)."),
        "levels": A(R("c18PathPoint"), 1, desc="The level path the transposition starts from: the source for a level path, baseline plus deviation or baseline times (1 + deviation / 100) otherwise."),
        "transposition": Ob({
            "label": C("transposed-onto-banco-andino-jump-off"),
            "rule": C("shape-onto-last-observed-then-revert-to-baseline"),
            "source_jump_off": R("c18QPoint"),
            "target": R("c18QPoint"),
            "reversion": E("to-baseline-after-published-horizon", "none-within-horizon"),
        }, "The transposition of the shape of the path onto the last observed value (decision Q6; the engine form of cases/c06/macro.py)."),
        "transposed": A(R("c18QPoint"), 12, 12, "The 12 quarters used, the three-year horizon, in the unit of the regressor the path maps to (a level path of a level regressor; the annual growth of a GDP level path)."),
    }, "One scenario path as used: the source path, its vintage and its transposition onto the Banco Andino jump-off.")
    d["c18Scenario"] = when(when(when(when(Ob({
        "scenario_id": E(*SCENARIOS),
        "title": TXT,
        "provider": E(*PROVIDERS),
        "source_document": S(minLength=1),
        "source_url": S(minLength=1),
        "vintage_date": DATE,
        "adaptation_label": ADAPT,
        "adaptation_statement": TXT,
        "paths": A(R("c18Path"), 1),
        "policy_shock_window": nullable(R("c18PolicyWindow"),
                                         "NGFS only: the three years in which the policy shock acts, transposed onto the jump-off (decision Q9, E2)."),
    }, "The scenario as used, with its source, its vintage and its label as a US-calibrated adaptation."),
        "scenario_id", "eba-2025-adverse", {"provider": C("eba-esrb"), "policy_shock_window": {"type": "null"}}),
        "scenario_id", "fed-2026-severely-adverse", {"provider": C("fed"), "policy_shock_window": {"type": "null"}}),
        "scenario_id", "baseline", {"provider": C("fed"), "policy_shock_window": {"type": "null"}}),
        "scenario_id", "ngfs-delayed-transition", {"provider": C("ngfs"), "policy_shock_window": {
            "$ref": "#/$defs/c18PolicyWindow", "properties": {"start_year": C(2031), "end_year": C(2033)}}})
    d["c18PolicyWindow"] = Ob({"start_year": Int(2025, 2100), "end_year": Int(2025, 2100), "label": TXT},
                              "The window where the NGFS policy shock acts: 2031 to 2033 for the delayed transition (F8 of the research addendum), transposed onto the jump-off.")
    d["c18CapStart"] = Ob({
        "rwa_clp_m": MONEY0,
        "rwa_by_risk": Ob({"credit": MONEY0, "market": MONEY0, "operational": MONEY0}),
        "cet1_clp_m": MONEY0, "at1_clp_m": MONEY0, "t2_clp_m": MONEY0, "pe_clp_m": MONEY0,
        "cet1_ratio": UNIT_SHARE, "pe_ratio": UNIT_SHARE,
        "basis": TXT,
    }, "Banco Andino at the jump-off: RWA (the C15 Tier 1 proxy over the 11.0 percent anchor, split by the 20-F mix) and the capital stock.")
    d["c18SatProjection"] = one_of(Ob({
        "fed_loan_type": E(*FED_TYPES),
        "series_id": E(*FED_SERIES.values()),
        "model_id": S(minLength=1),
        "link": E(*LINKS),
        "quarters": A(Ob({"quarter_end": QEND, "rate": RATE,
                          "link_value": N("g(rate): the probit or logit of the rate; the rate itself on the identity link.")}), 12, 12),
    }, "The projection of one Fed loan type over the 12 quarters of the horizon. On the probit link the rate is in (0, 1); on the identity link "
       "(RECI and RERES) it is signed and may be non-positive, read as net recoveries."),
        *[sat_alt(t, s) for t, s in FED_SERIES.items()])
    d["c18ClassProjection"] = Ob({
        "banco_andino_class": E(*CLASSES),
        "maps_from": A(E(*FED_TYPES), 1),
        "weights": A(N(minimum=0, maximum=1), 1),
        "exposure_clp_m": MONEY0,
        "label": ADAPT,
        "quarters": A(Ob({"quarter_end": QEND, "rate": N("Annualised loss rate of the class as a decimal, signed like the rates it mixes.",
                                                          exclusiveMinimum=-1, exclusiveMaximum=1)}), 12, 12),
    }, "The projection of one Banco Andino class as the weighted mix of the Fed loan types it maps from (decision Q6).")
    d["c18Satellites"] = Ob({
        "fed_loan_types": exact_rows(R("c18SatProjection"), "fed_loan_type", FED_TYPES, "One projection per Fed loan type."),
        "banco_andino_classes": exact_rows(R("c18ClassProjection"), "banco_andino_class", CLASSES, "One projection per Banco Andino class."),
    })
    d["c18YearLoss"] = Ob({
        "year": YEAR3, "period_end": QEND, "credit": MONEY0, "market": MONEY0, "irrbb": MONEY0, "operational": MONEY0, "total": MONEY0,
    })
    years3 = {"allOf": [{"contains": {"properties": {"year": {"const": y}}, "required": ["year"]}} for y in (1, 2, 3)]}

    def three(item: dict, desc: str) -> dict:
        arr = A(item, 3, 3, desc)
        arr.update(years3)
        return arr

    d["c18Losses"] = Ob({
        "scenario_losses": three(R("c18YearLoss"), "The losses of the scenario by risk and year (T+1 to T+3), in CLP millions."),
        "basis": TXT,
    })
    d["c18CapRow"] = Ob({"pct_of_rwa": RATIO, "need_clp_m": nullable(MONEY, "The estimated need; null on a tier row where the form asks for none."), "available_clp_m": MONEY},
                        "One row of a capital-planning table: the available funds as a share of RWA, the estimated need, the available funds.")
    d["c18PlanYear"] = Ob({
        "year": YEAR3, "period_end": QEND, "rwa_clp_m": MONEY0,
        "cet1": R("c18CapRow"), "at1": R("c18CapRow"), "t2": R("c18CapRow"), "pe": R("c18CapRow"),
        "requirement": Ob({"basis": E("internal-target", "legal-minimum"), "pct_of_rwa": RATIO}),
        "headroom_pct_of_rwa": RATIO,
        "deficit_clp_m": MONEY0,
    }, "One year of one case of the capital plan, as the three tables of sheet 3 of the IAPE Annex 3: percent of RWA, estimated need, available funds.")
    d["c18PlanCase"] = when(when(when(Ob({
        "case": E("base", "stress-without-mitigation", "stress-with-mitigation"),
        "years": three(R("c18PlanYear"), "T+1 to T+3."),
    }), "case", "base", {"years": {"items": {"properties": {"requirement": {"properties": {"basis": C("internal-target")}}}}}}),
        "case", "stress-without-mitigation", {"years": {"items": {"properties": {"requirement": {"properties": {"basis": C("legal-minimum")}}}}}}),
        "case", "stress-with-mitigation", {"years": {"items": {"properties": {"requirement": {"properties": {"basis": C("legal-minimum")}}}}}})
    d["c18Action"] = Ob({
        "id": S(minLength=1), "description": TXT, "label": C("case assumption"),
        "cet1_effect_clp_m": A(MONEY, 3, 3, "The effect on CET1 of each of T+1 to T+3, in CLP millions, not cumulated."),
    })
    d["c18Mitigation"] = one_of(Ob({
        "applies": B, "reason": nullable(TXT), "actions": A(R("c18Action")),
    }, "The mitigation actions of the stress with mitigation; row 10.2 of the Annex 3 is N/A when the stress leads to none."),
        {"applies": C(True), "reason": {"type": "null"}, "actions": {"minItems": 1}},
        {"applies": C(False), "reason": TXT, "actions": {"maxItems": 0}})
    d["c18CapitalPlan"] = Ob({
        "cases": exact_rows(R("c18PlanCase"), "case", ["base", "stress-without-mitigation", "stress-with-mitigation"], "The three cases of the IAPE (03 l.152-169, B.4)."),
        "mitigation": R("c18Mitigation"),
        "alternative_sources": A(Ob({"year": Int(0, 3), "source": S(minLength=1), "amount_clp_m": MONEY0, "label": C("case assumption")}),
                                 desc="Sheet 3, table C: sources of capital the bank counts usable under stress; empty when the bank counts none."),
    })
    d["c18Oi"] = Ob({
        "formula": C("OI >= 8% + c_DSIB + c_P2 + c_CCoB + c_CCyB + c_d, as percent of RWA (RAN 21-13 section I; 03 l.152-169)"),
        "horizon_years": C(3),
        "min_pe": C(0.08), "c_dsib": N(minimum=0, maximum=0.015), "c_p2": R("c18Named"), "c_ccob": C(0.025), "c_ccyb": N(minimum=0, maximum=0.025),
        "c_d": R("c18Named"),
        "oi": RATIO,
    }, "The internal capital target (objetivo interno) with its components; c_P2 and c_d are labelled assumptions of the case.")
    d["c18P2g"] = Ob({
        "label": APPROX,
        "formula": C("max over t of [(CET1/RWA)_0 - (CET1/RWA)_t severe] less the usable buffers and mitigation, floored at zero (03 l.1001-1005, FAQ 24)"),
        "peak_depletion": RATIO,
        "peak_year": YEAR3,
        "usable_buffers_and_mitigation": N(minimum=0),
        "value": N(minimum=0),
        "statement": TXT,
        "cmf_calibration_public": C(False),
    }, "The P2G proxy as a share of RWA, labelled a Contraste approximation.")
    d["c18Cell"] = one_of(Ob({
        "value": nullable(N()),
        "status": E("value", "RI", "not-to-be-filled", "not-applicable"),
    }, "A cell of the Annex 3 summary: a value, or why there is none (RI is an immaterial risk, no debera llenarse under the standardised method)."),
        {"status": C("value"), "value": N()},
        {"status": E("RI", "not-to-be-filled", "not-applicable"), "value": {"type": "null"}})
    d["c18Annex3Row"] = Ob({
        "row_id": E(*[r for r, _ in ANNEX3_ROWS]),
        "label_cmf": S("The row label as the CMF prints it (Annex 3, Circular 2.365).", minLength=1),
        "a": R("c18Cell"), "b": R("c18Cell"), "c": R("c18Cell"), "d": R("c18Cell"),
    }, "A row of the Annex 3 summary: column A percent of RWA, B the amount (CLP millions), C the legal requirement, D the internal measurement.")
    d["c18Annex3"] = Ob({
        "entity": C("Banco Andino"),
        "report_date": DATE,
        "consolidation": E("local", "global-consolidated"),
        "money_unit": C("CLP millions", "The form states thousand pesos; the document states millions throughout, as the other C18 blocks do."),
        "rows": exact_rows(R("c18Annex3Row"), "row_id", [r for r, _ in ANNEX3_ROWS], "The 34 rows of the summary, each once (F7)."),
    }, "The IAPE Annex 3 summary (12 numbered rows with their sub-rows by 4 columns) as the CMF prints it.")
    d["c18Headline"] = Ob({
        "method": C("loss-only-depletion", "CET1 at the jump-off less the cumulative stressed losses, no invented revenue (decision Q10)."),
        "statement": TXT,
        "rows": three(Ob({
            "year": YEAR3, "period_end": QEND, "cet1_start_clp_m": MONEY, "cumulative_loss_clp_m": MONEY0, "cet1_clp_m": MONEY,
            "rwa_clp_m": MONEY0, "cet1_ratio": RATIO,
        }), "The headline CET1 path, T+1 to T+3."),
        "ppnr": Ob({
            "label": C("ppnr-labelled-row", "A labelled row with revenue: not the headline."),
            "statement": TXT,
            "nii_source": C("c15-dynamic-nii"),
            "fee_ratio": R("c18Named"),
            "cost_ratio": R("c18Named"),
            "rows": three(Ob({
                "year": YEAR3, "period_end": QEND, "nii_clp_m": MONEY, "fee_income_clp_m": MONEY, "operating_cost_clp_m": MONEY0,
                "ppnr_clp_m": MONEY, "cet1_with_ppnr_clp_m": MONEY, "cet1_ratio_with_ppnr": RATIO,
            }), "PPNR = (NII + fee income) (1 - cost ratio), fee income = fee ratio x NII; CET1 adds the cumulated PPNR to the loss-only path."),
        }),
    }, "The headline CET1 path as loss-only depletion, with the PPNR row labelled.")
    d["c18Severity"] = Ob({
        "reference_episode": Ob({"name": C("global-financial-crisis"), "start": QEND, "end": QEND, "source": TXT},
                                "The history the severity of each path is read against: 2008 to 2009 (05 l.422), peaks read by the bake from the Board's historic table."),
        "minimum_ratio": N("The amber threshold of stress.scenario_severity: a stress path is at least this share of the historical peak (a policy parameter).",
                           exclusiveMinimum=0),
        "rows": A(Ob({
            "variable": S("The scenario path variable, as named in scenario.paths.", minLength=1),
            "maps_to_regressor": E(*AGENCY_REGRESSORS),
            "unit": S(minLength=1),
            "path_peak_deviation": N("max over the transposed quarters of the absolute deviation from the jump-off value (the target).", minimum=0),
            "path_peak_quarter": QEND,
            "history_peak_deviation": N("The same deviation in the reference episode.", exclusiveMinimum=0),
            "history_window": Ob({"start": QEND, "end": QEND}),
            "history_source": TXT,
            "ratio": N("path_peak_deviation / history_peak_deviation.", minimum=0),
            "is_stress": B,
        }), 1, desc="One row per scenario path variable, in the order of scenario.paths."),
    }, "The severity of each path against history (dossier 05 l.422; sizing view U13-W): the path peak, the global financial crisis peak with its quarters "
       "and source, their ratio and whether the path is a stress.")
    d["c18Backcast"] = Ob({
        "window": Ob({"start": C("2020-03-31"), "end": C("2025-12-31")}, "The out-of-time window, 2020 Q1 to 2025 Q4 (decision Q8)."),
        "per_loan_type": exact_rows(one_of(Ob({
            "fed_loan_type": E(*FED_TYPES),
            "series_id": E(*FED_SERIES.values()),
            "link": E(*LINKS),
            "fit_window": Ob({"start": FIT_DATE, "end": FIT_DATE}),
            "quarters": A(Ob({"quarter_end": QEND, "predicted": RATE, "realised": RATE}), 24, 24),
            "metrics": Ob({
                "rmse": N(minimum=0),
                "peak_predicted": RATE, "peak_predicted_quarter": QEND,
                "peak_realised": RATE, "peak_realised_quarter": QEND,
                "peak_timing_error_quarters": Int(),
            }),
        }), *[backcast_alt(t, s) for t, s in FED_SERIES.items()]), "fed_loan_type", FED_TYPES, "One back-cast per Fed loan type: the satellite fitted to 2019, predicted against realised."),
        "descriptive_2026": A(Ob({
            "quarter_end": E("2026-03-31", "2026-06-30"),
            "realised_rates": exact_rows(Ob({"fed_loan_type": E(*FED_TYPES), "rate": RATE}),
                                         "fed_loan_type", FED_TYPES, "The realised charge-off rate of each Fed loan type."),
            "label": C("rate-only-descriptive"),
            "forecast_claim": C(False),
        }), 2, 2, "2026 Q1 and Q2 as a rate-only descriptive row: no macro actuals, no forecast claim (decision Q8)."),
        "statement": TXT,
    }, "The out-of-time back-cast of the satellites.")
    d["c18Outputs"] = Ob({
        "kind": C("scenario"),
        "currency": C("CLP"),
        "units": R("c18Units"),
        "bank": R("c18Env"),
        "capital_start": R("c18CapStart"),
        "scenario": R("c18Scenario"),
        "satellites": R("c18Satellites"),
        "losses": R("c18Losses"),
        "internal_capital_target": R("c18Oi"),
        "capital_plan": R("c18CapitalPlan"),
        "p2g_proxy": R("c18P2g"),
        "annex3": R("c18Annex3"),
        "headline_cet1": R("c18Headline"),
        "severity": R("c18Severity"),
        "backcast": R("c18Backcast"),
        "aggregation": R("c18Aggregation"),
    }, "C18 outputs of one scenario variant.")
    return d


def aggregation_defs() -> dict:
    d = common_defs()
    d["c18SensRow"] = Ob({
        "nu": N(exclusiveMinimum=2), "gaussian_capital_clp_m": MONEY0, "t_capital_clp_m": MONEY0, "relative_difference": N(),
    })
    d["c18CorrStress"] = Ob({
        "pair": Ob({"a": C("market"), "b": C("credit"), "value": C(0.8, "The market-credit correlation raised to 0.8, the upper end of the published ranges (05 l.378).")}),
        "aggregation": R("c18Aggregation"),
    }, "The same aggregation under the stressed correlation matrix.")
    d["c18RsReference"] = Ob({
        "role": C("reference-not-a-gate", "Reported beside the result as a reference, never as a gate (05 l.360, l.484)."),
        "weights": Ob({"market": C(0.041), "credit": C(0.264), "operational": C(0.695)},
                      "The benchmark risk weights of a typical large bank (05 l.360): market 4.1, credit 26.4, operational 69.5 percent."),
        "correlations": Ob({"market_credit": C(0.5), "market_operational": C(0.2), "credit_operational": C(0.2)},
                           "The normal copula of the benchmark: market-credit 0.5 and market and credit with operational 0.2 (05 l.360)."),
        "published_additive_overestimate": Ob({"low": C(0.30), "high": C(0.40)}, "The additive approximation typically overestimates risk by about 30 to 40 percent (05 l.360)."),
        "case_additive_overestimate": N("Simple sum over the Gaussian copula row, less one, for this bank."),
        "within_published_range": B,
    }, "The Rosenberg and Schuermann reference.")
    d["c18AggOutputs"] = Ob({
        "kind": C("aggregation"),
        "currency": C("CLP"),
        "units": R("c18Units"),
        "bank": R("c18Env"),
        "scenario_id": C("baseline", "The t-copula variant runs the baseline scenario (decision Q12)."),
        "aggregation": R("c18Aggregation"),
        "correlation_stress": R("c18CorrStress"),
        "copula_sensitivity": A(R("c18SensRow"), 1, desc="Gaussian against t over the nu set, at the base matrix."),
        "rosenberg_schuermann": R("c18RsReference"),
    }, "C18 outputs of the t-copula aggregation variant.")
    return d


def reverse_defs() -> dict:
    d = common_defs()
    d["c18RevFactor"] = Ob({
        "id": E(*AGENCY_REGRESSORS), "label": TXT, "unit": S(minLength=1), "sd": N(exclusiveMinimum=0),
    })
    d["c18Stack"] = Ob({
        "cet1_min": C(0.045), "c_ccob": C(0.025), "c_ccyb": N(minimum=0, maximum=0.025), "c_dsib": N(minimum=0, maximum=0.015),
        "p2_cet1": R("c18Named"),
        "total": RATIO,
        "basis": C("chilean-legal-minimum-stack", "CET1/RWA >= 4.5% + 2.5% + RCC + c_DSIB + the CET1 share of c_P2 (RAN 21-13; 03 l.911-920)."),
    })
    d["c18Solution"] = Ob({
        "method": E("closed-form-linear", "scipy-optimize"),
        "z_star": A(N(), 1),
        "x_star": A(N(), 1),
        "mahalanobis_distance": N(exclusiveMinimum=0),
        "plausibility": Ob({"chi_square_df": Int(1), "tail_probability": N(exclusiveMinimum=0, maximum=1)}),
        "loss_at_z_star_clp_m": MONEY0,
        "loss_threshold_clp_m": MONEY0,
        "relative_gap": N(minimum=0),
        "tolerance": N(exclusiveMinimum=0),
    }, "The most plausible scenario that reaches the failure point and the loss at it.")
    d["c18RevOutputs"] = Ob({
        "kind": C("reverse"),
        "currency": C("CLP"),
        "units": R("c18Units"),
        "bank": R("c18Env"),
        "failure_point": Ob({
            "label": C("contraste-formulation-not-regulatory", "The formal statement is Contraste's, not regulatory text (01 l.891-894; 05 l.412)."),
            "definition": TXT,
            "stack": R("c18Stack"),
            "cet1_ratio_start": RATIO,
            "rwa_clp_m": MONEY0,
            "horizon_years": C(3),
        }, "The failure point: CET1 at the Chilean legal minimum stack at the end of the planning horizon (decision Q11)."),
        "factor_space": Ob({
            "window": Ob({"start": FIT_DATE, "end": FIT_DATE}),
            "factors": A(R("c18RevFactor"), 1),
            "covariance": A(A(N(), 1), 1),
            "label": ADAPT,
        }, "The standardised satellite regressors with their covariance from the 1985-2019 window (decision Q11)."),
        "loss_model": one_of(Ob({
            "kind": E("linear", "nonlinear"),
            "gradient_clp_m_per_unit": nullable(A(N(), 1), "The loss per unit of each factor deviation for a linear loss; null for a nonlinear one."),
            "description": TXT,
        }), {"kind": C("linear"), "gradient_clp_m_per_unit": A(N(), 1)}, {"kind": C("nonlinear"), "gradient_clp_m_per_unit": {"type": "null"}}),
        "solution": R("c18Solution"),
        "starts": A(Ob({"start_id": S(minLength=1), "converged": B, "distance": N(minimum=0), "loss_clp_m": MONEY0}), 3,
                    desc="At least three starts: no closer point is found from any of them (H.7)."),
    }, "C18 outputs of the reverse stress variant.")
    return d


def fit_defs() -> dict:
    d = common_defs()
    d["c18FitWindow"] = Ob({"start": FIT_DATE, "end": FIT_DATE},
                        "A fit window: ISO quarter ends from 1985 to 2019. A window that reaches 2020 or later does not match.")
    d["c18Coef"] = Ob({
        "name": S(minLength=1), "estimate": N(), "std_error": N(minimum=0),
        "expected_sign": E("positive", "negative", "none"),
    })
    d["c18Regressor"] = Ob({
        "name": E(*AGENCY_REGRESSORS), "lag": Int(0, 4),
        "source_series": S(minLength=1),
        "licence_class": C("agency", "Agency series only (decision Q7): the BBB corporate yield and the third-party index levels are not read."),
    })
    d["c18SatFit"] = one_of(Ob({
        "model_id": S(minLength=1),
        "fed_loan_type": E(*FED_TYPES),
        "series_id": E(*FED_SERIES.values()),
        "link": E(*LINKS),
        "sample_window": R("c18FitWindow"),
        "non_positive_quarters_in_window": Int(0, desc="The number of quarters of the fit window whose rate is zero or negative (net recoveries): a probit "
                                                        "or logit fit needs none, the identity link takes them as they are."),
        "ar_order": Int(0, 4),
        "n_obs": Int(1),
        "regressors": A(R("c18Regressor"), 1),
        "coefficients": A(R("c18Coef"), 1),
        "fit_statistics": Ob({"r_squared": N(minimum=0, maximum=1), "residual_sd": N(minimum=0)}),
        "estimation": C("ols-numpy-with-standard-errors"),
    }, "One satellite: g(DR_t) = alpha + sum phi_k g(DR_(t-k)) + sum beta_l' X_(t-l) + e, fitted by OLS (04 l.785-795); g is the probit for C&I, "
       "credit cards and other consumer, and the identity for RECI and RERES, whose windows hold non-positive quarters (the linear form of the Federal "
       "Reserve's own PD regression, 05 l.399). The window ends in 2019 at the latest and starts at the first quarter the Board publishes."),
        *[fit_alt(t, s) for t, s in FED_SERIES.items()])
    d["c18ClassMap"] = Ob({
        "banco_andino_class": E(*CLASSES),
        "fed_loan_types": A(E(*FED_TYPES), 1),
        "weights": A(N(minimum=0, maximum=1), 1),
        "label": ADAPT,
        "basis": TXT,
    })
    d["c18Factor"] = Ob({"id": E(*AGENCY_REGRESSORS), "label": TXT, "unit": S(minLength=1), "sd": N(exclusiveMinimum=0)})
    d["c18FactorSpace"] = Ob({
        "window": R("c18FitWindow"), "factors": A(R("c18Factor"), 1), "covariance": A(A(N(), 1), 1), "label": ADAPT,
    })
    d["c18Anchors"] = Ob({
        "rwa_basis": Ob({
            "tier1_proxy_clp_m": MONEY0,
            "cet1_ratio_anchor": N("The 11.0 percent anchor of the 20-F (03 l.1324), as a ratio.", exclusiveMinimum=0, exclusiveMaximum=1),
            "rwa_total_clp_m": MONEY0,
        }, "RWA = the C15 Tier 1 proxy over the CET1 ratio anchor (decision Q4)."),
        "rwa_mix": Ob({"credit": UNIT_SHARE, "market": UNIT_SHARE, "operational": UNIT_SHARE},
                      "The 20-F RWA mix as ratios only (credit 70.8, market 17.1, operational 12.0 percent, 03 l.1307-1328)."),
        "chilean_stack": Ob({
            "cet1_min": C(0.045), "c_ccob": C(0.025), "c_ccyb": N(minimum=0, maximum=0.025), "c_dsib": N(minimum=0, maximum=0.015),
            "p2r": N(minimum=0, maximum=0.04, desc="Pillar 2 requirement over RWA; the cap is 4 percent of RWA (03 l.253)."),
            "p2_cap": C(0.04),
        }, "The Chilean capital stack as ratios (03 l.913-920): 4.5, 2.5, 0.5 or 1, 0 to 1.5 percent, the Pillar 2 requirement."),
        "loan_exposures": exact_rows(Ob({"banco_andino_class": E(*CLASSES), "exposure_clp_m": MONEY0, "share": UNIT_SHARE}), "banco_andino_class", CLASSES,
                                     "The loan book by class from the C07 targets."),
        "source": TXT,
        "licence_class": C("derived-only", "The Santander Chile 20-F is derived-only until the filer's own rights are read: ratios only (decision Q4, E5)."),
        "ratios_only": C(True),
    }, "The bank anchors (decision Q4).")
    d["c18ScenarioSource"] = Ob({
        "scenario_id": E(*SCENARIOS),
        "provider": E(*PROVIDERS),
        "document": S(minLength=1), "url": S(minLength=1), "vintage_date": DATE,
        "licence_class": E("mirror-allowed", "derived-only"),
        "variables": A(Ob({"name": S(minLength=1), "unit": S()}), desc="NGFS only: the NiGEM variables read, named exactly; empty for the other sources."),
    })
    d["c18Rule"] = Ob({
        "source": C("EBA 2025 EU-wide stress test, Methodological Note, 2025-01-20"),
        "paragraph": S(minLength=1), "page": Int(1), "statement": S(minLength=1),
    })
    d["c18CapitalEngine"] = Ob({
        "balance_sheet": C("static"), "horizon_years": C(3),
        "rules": A(R("c18Rule"), 1, desc="The EBA rules the capital projection applies, by paragraph (F6 of the addendum)."),
        "reversion_quarters": N("The product convention of cases/c06/macro.py: a path reverts linearly to the baseline over this many quarters after its published horizon.", minimum=0),
    })
    d["c18NamedParameters"] = Ob({
        "nu_set": R("c18NamedSet"),
        "correlation_matrix_base": R("c18NamedMatrix"),
        "correlation_matrix_stress": R("c18NamedMatrix"),
        "ppnr_fee_ratio": R("c18Named"),
        "ppnr_cost_ratio": R("c18Named"),
        "c_p2": R("c18Named"),
        "c_d": R("c18Named"),
        "operational_conversion_rate": R("c18DerivedFx"),
        "asset_scaling": R("c18DerivedAssets"),
        "market_rwa_share": R("c18Named"),
        "market_horizon_scaling": R("c18MarketScaling"),
        "reverse_p2_cet1": R("c18Named"),
    }, "Every named parameter of the case with its value, unit and label (convention or case assumption).")
    d["c18QuantileGrid"] = Ob({
        "convention": Ob({
            "name": C("standard-normal-z-grid"),
            "z_min": C(-4.9, "The lowest standard normal quantile of the grid."), "z_max": C(4.9, "The highest standard normal quantile of the grid."),
            "z_step": C(0.005, "The step of z between two points."), "points": C(1961, "The number of points: z from -4.9 to 4.9 in steps of 0.005."),
            "unit": C("CLP millions"), "statement": TXT,
        }, "The named convention of the probability grid: p = Phi(z) for z from z_min to z_max in steps of z_step."),
        "probabilities": A(N(exclusiveMinimum=0, exclusiveMaximum=1), 1961, 1961, "Phi(z) at the grid points, ascending."),
        "marginals": exact_rows(Ob({"risk": E(*RISKS), "quantiles": A(N(), 1961, 1961, "The marginal's quantile at each probability, CLP millions, "
                                                                                  "non-decreasing.")}), "risk", RISKS,
                                "One quantile function per marginal, in the order of the band's marginals."),
    }, "The quantile function of each marginal at the grid probabilities (c18-models 2.1.0): a reader rebuilds the marginals the copulas and the "
       "bounds were run on by linear interpolation in the probability. Ascending probabilities, non-decreasing quantiles and the agreement with "
       "the marginal's VaR are checked by tests/c18/test_c18_quantile_grid.py.")
    d["c18AggParams"] = Ob({
        "ladder": A(Ob({"method": E(*BAND_METHODS), "engine_function": S(minLength=1)}), 6, 6),
        "n_draws": Int(1), "seed": Int(), "chunk_size": Int(1),
        "horizon_years": HORIZON, "confidence_level": LEVEL, "capital_basis": BASIS,
        "marginal_interpolation": S("The rule that maps a uniform draw through a marginal sample.", minLength=1),
    })
    # optional, added at 2.1.0: a 2.0.0 document (without the grid) still validates
    d["c18AggParams"]["properties"]["quantile_grid"] = R("c18QuantileGrid")
    d["c18C17Set"] = Ob({
        "document": C("C17 models-generator"),
        "variant_id": E("xi-0-6", "xi-0-8", "xi-0-96", "xi-1-1"),
        "tail_index": N("The GPD tail index xi of the severity of the variant.", exclusiveMinimum=0),
        "infinite_mean": B,
        "assets_eur_bn": N("The stated assets of the C17 synthetic bank, EUR billions.", exclusiveMinimum=0),
    }, "The C17 generator parameter set the operational marginal is recomputed from (decision Q5): the variant of the C17 models-generator document "
       "(docs/contracts/schemas/c17/models.schema.json), its tail index and whether its severity has an infinite mean (xi of 1 or more).")
    d["c18MarginalSource"] = one_of(Ob({
        "risk": E(*RISKS), "producer": E(*PRODUCERS.values()), "description": TXT, "documents": A(S(minLength=1), 1),
        "c17_parameter_set": nullable(R("c18C17Set"), "Operational only: the C17 parameter set; null for the other risks."),
    }), *[{"risk": C(r), "producer": C(p), "c17_parameter_set": R("c18C17Set") if r == "operational" else {"type": "null"}}
          for r, p in PRODUCERS.items()])
    d["c18Fit"] = Ob({
        "currency": C("CLP"),
        "units": R("c18Units"),
        "bank": R("c18Env"),
        "satellites": exact_rows(R("c18SatFit"), "fed_loan_type", FED_TYPES, "One satellite per Fed loan type."),
        "class_mapping": exact_rows(R("c18ClassMap"), "banco_andino_class", CLASSES, "One mapping per Banco Andino class."),
        "factor_space": R("c18FactorSpace"),
        "aggregation": R("c18AggParams"),
        "named_parameters": R("c18NamedParameters"),
        "bank_anchors": R("c18Anchors"),
        "marginal_sources": exact_rows(R("c18MarginalSource"), "risk", RISKS, "One source per marginal (decision Q5)."),
        "scenario_sources": A(R("c18ScenarioSource"), 4, 4),
        "capital_engine": R("c18CapitalEngine"),
    }, "C18 models: the satellite fits, the factor space, the aggregation parameters, the bank anchors, the scenario sources, the capital engine rules and the named parameters.")
    return d


# ------------------------------------------------------------------------------------------------------------ rules

TRUTH_STATUS = {"properties": {"provenance": {"properties": {"truth_status": {"const": "synthetic-calibrated"}}}},
                "required": ["provenance"]}
NOT_EVALUATED_RULE = {
    "properties": {"tests": {"items": {
        "if": {"properties": {"light": {"const": "not_evaluated"}}, "required": ["light"]},
        "then": {"properties": {"statistic": {"type": "null"}, "p_value": {"type": "null"}, "metric": {"type": "null"},
                                "notes": {"type": "string", "minLength": 1}}},
    }}},
}
#: the G.5 and H.7 test rows a document must carry (F6): a validator and the Validation tab need them, so a document without one does not validate
REQUIRED_TESTS = {
    "scenario": ["aggregation.simple_sum_and_variance_covariance", "aggregation.copula_choice_sensitivity", "aggregation.worst_case_bracket",
                 "aggregation.correlation_stress", "aggregation.diversification_sign", "aggregation.horizon_confidence_consistency",
                 "portfolio.euler_additivity", "stress.satellite_backcast", "stress.sensitivity_monotonicity", "stress.static_balance_sheet_rules",
                 "stress.scenario_severity"],
    "aggregation": ["aggregation.simple_sum_and_variance_covariance", "aggregation.copula_choice_sensitivity", "aggregation.worst_case_bracket",
                    "aggregation.correlation_stress", "aggregation.diversification_sign", "aggregation.horizon_confidence_consistency",
                    "aggregation.elliptical_mc_agreement", "aggregation.rosenberg_schuermann_reference", "portfolio.euler_additivity"],
    "reverse": ["stress.reverse_solution_check"],
}
IMPACT_KEYS = ["capital_simple_sum", "cet1_ratio_end_stress", "oi_headroom_min", "p2g_proxy"]
IMPACT_RULE = {"properties": {"impact": {"required": IMPACT_KEYS}}}


def variant_schema(ref: str, kind: str, title: str, desc: str, root: str, defs: dict) -> None:
    doc = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{BASE}c18/{ref}.schema.json",
        "title": title,
        "description": desc,
        "allOf": [
            {"$ref": "../common/variant-envelope.schema.json"},
            {"properties": {"case_id": {"const": "C18"},
                            "outputs": {"$ref": f"#/$defs/{root}", "properties": {"kind": {"const": kind}}}},
             "required": ["case_id", "outputs"]},
            NOT_EVALUATED_RULE,
            TRUTH_STATUS,
            IMPACT_RULE,
            {"properties": {"tests": {"allOf": [{"contains": {"properties": {"test_id": {"const": tid}}, "required": ["test_id"]}}
                                                for tid in REQUIRED_TESTS[kind]]}}},
        ],
        "unevaluatedProperties": False,
        "$defs": reachable(root, defs),
    }
    write(f"{ref}.schema.json", doc)


def models_schema(title: str, desc: str, root: str, defs: dict) -> None:
    doc = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{BASE}c18/models.schema.json",
        "title": title,
        "description": desc,
        "allOf": [
            {"$ref": "../common/models-envelope.schema.json"},
            {"properties": {"case_id": {"const": "C18"}, "fit": {"$ref": f"#/$defs/{root}"}},
             "required": ["case_id", "fit"]},
            TRUTH_STATUS,
        ],
        "unevaluatedProperties": False,
        "$defs": reachable(root, defs),
    }
    write("models.schema.json", doc)


def main() -> None:
    sd, ad, rd, fd = scenario_defs(), aggregation_defs(), reverse_defs(), fit_defs()
    variant_schema("variant-scenario", "scenario", "C18 scenario variant",
                   "Catalog row c18-outputs 2.0.0: one scenario of the ICAAP and IAPE capital aggregation case (outputs.kind scenario): baseline, "
                   "EBA 2025 adverse, Fed 2026 severely adverse or NGFS delayed transition, on the synthetic Banco Andino.", "c18Outputs", sd)
    variant_schema("variant-aggregation", "aggregation", "C18 t-copula aggregation variant",
                   "Catalog row c18-outputs-aggregation 2.0.0: the t-copula aggregation variant (outputs.kind aggregation), the band over the nu set at "
                   "the Rosenberg and Schuermann matrix and under the market-credit 0.8 stress.", "c18AggOutputs", ad)
    variant_schema("variant-reverse", "reverse", "C18 reverse stress variant",
                   "Catalog row c18-outputs-reverse 1.0.0: the reverse stress variant (outputs.kind reverse), the minimum Mahalanobis distance scenario "
                   "that takes CET1 to the Chilean legal minimum stack.", "c18RevOutputs", rd)
    models_schema("C18 models",
                  "Catalog row c18-models 2.1.0: the C18 models artifact (satellite fits on 1985-2019, factor space, aggregation parameters, bank "
                  "anchors, scenario sources, capital engine rules, named parameters).", "c18Fit", fd)


if __name__ == "__main__":
    main()
