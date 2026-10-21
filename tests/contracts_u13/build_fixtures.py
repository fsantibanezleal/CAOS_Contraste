"""Builds the seven U13-S fixture documents (docs/contracts/fixtures/c18).

Run: ``python tests/contracts_u13/build_fixtures.py``. Deterministic, standard library only. The numbers are round, small and internally
consistent (the identities the contract promises: EC = VaR - EL, the simple sum as the headline, sqrt(EC' R EC), the Euler sums, the
loss-only CET1 path, the plan rows, the Annex 3 identities, the closed form of the reverse stress) but they are fixtures, never results:
every document is labelled ``fixture`` in its provenance and its ids, and no value comes from running the engine or a bake. The
scenario values are made up in the shape of the published paths; where the research record gives a number (the NGFS NiGEM deviations of
the delayed transition, F8) it is used, and the NGFS baseline GDP levels after 2030 are fixture values.

The data shapes are the real ones (fix round u13-s-fixes-2026-10-19): the net charge-off rates are signed, the residential and commercial
real estate fit windows start 1991Q1 (the Board's table is missing both series from 1985Q1 to 1990Q4) and use the identity link, and the
residential back-cast holds the Board's 23 non-positive quarters out of 24 (its realised values are transcribed from the table, an agency
series, as the shape; every other number is a fixture value).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "docs" / "contracts" / "fixtures" / "c18"
ND = NormalDist()
RISKS = ["credit", "market", "irrbb", "operational"]
FED = [("commercial-industrial", "CI"), ("commercial-real-estate", "RECI"), ("residential", "RERES"), ("credit-cards", "CONCC"),
       ("other-consumer", "CONOTH")]
CLASSES = ["commercial", "consumer", "mortgage"]
AS_OF = "2026-08-31"
JUMP = "2025-12-31"
QUARTERS = [f"{2026 + (k // 4)}-{('03-31', '06-30', '09-30', '12-31')[k % 4]}" for k in range(12)]
YEAR_ENDS = ["2026-12-31", "2027-12-31", "2028-12-31"]
FIT_START, FIT_END = "1985-03-31", "2019-12-31"
IDENTITY = ("commercial-real-estate", "residential")
TYPE_START = {"commercial-industrial": "1985-03-31", "commercial-real-estate": "1991-03-31", "residential": "1991-03-31",
              "credit-cards": "1985-03-31", "other-consumer": "1985-03-31"}
NON_POSITIVE = {"commercial-industrial": 0, "commercial-real-estate": 13, "residential": 6, "credit-cards": 0, "other-consumer": 0}
#: RERES 2020Q1 to 2025Q4 as the Board's table prints it (percent, annualised), the shape of the residential back-cast
RERES_REALISED_PCT = [-0.03, 0.0, 0.0, -0.03, -0.04, -0.04, -0.04, -0.02, -0.03, -0.02, -0.02, -0.02, -0.01, 0.01, -0.0, -0.0, -0.0, -0.01,
                      -0.01, -0.0, -0.0, -0.0, -0.0, -0.0]
SCEN_ID = {"baseline": "baseline", "eba": "eba-2025-adverse", "fed": "fed-2026-severely-adverse", "ngfs": "ngfs-delayed-transition"}


def txt(en: str, es: str | None = None) -> dict:
    return {"en": en, "es": es or f"{en} (es)"}


def r6(x: float) -> float:
    return round(x, 6)


def r10(x: float) -> float:
    return round(x, 10)


def write(name: str, doc: dict) -> None:
    FIX.mkdir(parents=True, exist_ok=True)
    with (FIX / name).open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------------------------------------ the envelope pieces


def provenance() -> dict:
    return {
        "truth_status": "synthetic-calibrated",
        "inputs": [{"source": "fixture-not-a-result", "class": "fixture", "files": []}],
        "licence_classes": {"fixture-not-a-result": "fixture"},
        "generators": ["fixture:u13-s-contracts"],
        "seed": 0, "code_version": "fixture", "riskvalidation_version": None,
    }


LANE = {"lane": "precompute", "reasons": ["fixture"]}


def test_row(test_id: str, model_id: str) -> dict:
    return {
        "test_id": test_id, "model_id": model_id, "segment": None, "statistic": None, "p_value": None, "metric": None,
        "h0": "fixture row", "alternative": "fixture row", "policy_version": "fixture", "alpha_amber": None, "alpha_red": None,
        "light": "not_evaluated", "n": None, "n_events": None, "inputs_hash": "0" * 64, "reference": "fixture, not a result",
        "notes": "fixture: the test did not run, no number stands in for it", "extras": {},
    }


def model_summary(mid: str, family: str, rung: str) -> dict:
    return {
        "id": mid, "family": family, "rung": rung, "title": txt(f"Fixture model {mid}", f"Modelo de ejemplo {mid}"),
        "short_title": txt(mid, mid), "engine": "riskvalidation", "engine_version": "fixture", "licence": "MIT",
        "calibration": None, "parameters": {}, "checkpoint_sha256": None,
    }


def model_record(mid: str, family: str, rung: str) -> dict:
    d = model_summary(mid, family, rung)
    d["details"] = {}
    return d


MODEL_IDS = [("c18-satellites-us-calibrated", "stress", "satellite-probit-ols"), ("c18-aggregation-ladder", "aggregation", "simple-sum-headline"),
             ("c18-capital-engine", "stress", "capital-engine-static")]


def impact_item(value: float, unit: str, label: str) -> dict:
    return {"value": value, "unit": unit, "label": txt(label)}


def envelope(variant_id: str, outputs: dict, tests: list[str], impact: dict) -> dict:
    return {
        "schema": "contraste.case/v1", "case_id": "C18", "variant_id": variant_id,
        "model": [model_summary(*m) for m in MODEL_IDS],
        "outputs": outputs,
        "tests": [test_row(t, "c18-aggregation-ladder") for t in tests],
        "impact": impact,
        "findings": [{"id": "fixture-finding-1", "severity": "S4", "status": "open", "evidence": ["fixture"],
                      "title": txt("Fixture finding, not a result")}],
        "provenance": provenance(), "lane": LANE,
    }


# ------------------------------------------------------------------------------------------------ the bank and the named parameters

RWA = 20_000_000.0
CET1_0, AT1_0, T2_0 = 2_200_000.0, 250_000.0, 500_000.0
SANTANDER = {"rwa": 41_715_467, "credit": 29_551_588, "market": 7_143_966}   # ratios only enter the documents (03 l.1324)
MIX_CREDIT = round(SANTANDER["credit"] / SANTANDER["rwa"], 6)
MIX_MARKET = round(SANTANDER["market"] / SANTANDER["rwa"], 6)
MIX = {"credit": MIX_CREDIT, "market": MIX_MARKET, "operational": r10(1.0 - MIX_CREDIT - MIX_MARKET)}
STACK = {"c_ccob": 0.025, "c_ccyb": 0.005, "c_dsib": 0.015, "p2r": 0.00125}
SHARES = {"commercial": 0.5404703620, "consumer": 0.1139433702, "mortgage": 0.3455862677}
LOANS = 14_000_000.0
EXPOSURE = {c: r6(LOANS * s) for c, s in SHARES.items()}
CLASS_MAP = {"commercial": (["commercial-industrial", "commercial-real-estate"], [0.6, 0.4]),
             "consumer": (["credit-cards", "other-consumer"], [0.5, 0.5]),
             "mortgage": (["residential"], [1.0])}
RISK_ORDER = RISKS
CORR_BASE = [[1.0, 0.5, 0.5, 0.2], [0.5, 1.0, 0.5, 0.2], [0.5, 0.5, 1.0, 0.2], [0.2, 0.2, 0.2, 1.0]]
CORR_STRESS = [[1.0, 0.8, 0.5, 0.2], [0.8, 1.0, 0.5, 0.2], [0.5, 0.5, 1.0, 0.2], [0.2, 0.2, 0.2, 1.0]]
NU_SET = [4.0, 8.0, 30.0]
FX_RATE = 1000.0                      # fixture value: the bake reads the observed EUR to CLP rate of the as-of date
BANCO_ASSETS = 40_000_000.0           # fixture value, CLP millions
C17_ASSETS_EUR_M = 50_000.0           # C17 models-generator generator.assets_eur_bn = 50.0
LEVEL_FACTOR = r10(ND.inv_cdf(0.999) / ND.inv_cdf(0.99))
HORIZON_FACTOR = r10(math.sqrt(250))
FEE, COST = 0.25, 0.55


def named(name: str, value: float, unit: str, label: str, basis_en: str) -> dict:
    return {"name": name, "value": value, "unit": unit, "label": label, "basis": txt(basis_en)}


def named_set(name: str, values: list[float], unit: str, label: str, basis_en: str) -> dict:
    return {"name": name, "values": values, "unit": unit, "label": label, "basis": txt(basis_en)}


def named_matrix(name: str, matrix: list[list[float]], label: str, basis_en: str) -> dict:
    return {"name": name, "order": RISKS, "matrix": matrix, "unit": "correlation", "label": label, "basis": txt(basis_en)}


NAMED = {
    "nu_set": named_set("nu_set", NU_SET, "degrees of freedom", "convention",
                        "Degrees of freedom of the t copula: 4, 8 and 30 (30 approaches the Gaussian copula); a convention of the case, G.5 asks for several nu (05 l.378)"),
    "correlation_matrix_base": named_matrix("correlation_matrix_base", CORR_BASE, "convention",
                                            "The Rosenberg and Schuermann benchmark: market-credit 0.5, market and credit with operational 0.2 (05 l.360); IRRBB is treated as a market-type risk (0.5 with credit and market, 0.2 with operational): UNVERIFIED, no dossier gives an IRRBB correlation"),
    "correlation_matrix_stress": named_matrix("correlation_matrix_stress", CORR_STRESS, "convention",
                                              "The base matrix with market-credit raised to 0.8, the upper end of the published ranges (05 l.378)"),
    "ppnr_fee_ratio": named("ppnr_fee_ratio", FEE, "fee income over NII", "case assumption", "A stated constant ratio of the PPNR row (decision Q10); not a Banco Andino or CMF figure"),
    "ppnr_cost_ratio": named("ppnr_cost_ratio", COST, "operating cost over (NII + fee income)", "case assumption", "A stated constant cost-to-income ratio of the PPNR row (decision Q10)"),
    "c_p2": named("c_p2", 0.01, "share of RWA", "case assumption", "The bank's own capital for risks outside Pillar 1, at least the art. 66 quinquies requirement (03 l.152-169, decision Q4)"),
    "c_d": named("c_d", 0.01, "share of RWA", "case assumption", "The voluntary stress buffer, component d of the internal target (03 l.152-169, decision Q4)"),
    "operational_conversion_rate": {
        **named("operational_conversion_rate", FX_RATE, "CLP per EUR", "case assumption",
                "Derived at bake time: the EUR to CLP rate of the as-of date from the Banco Central de Chile (decision Q5, W5); this value is a fixture value"),
        "derivation": {"kind": "observed-exchange-rate", "pair": "EUR/CLP", "observation_date": AS_OF,
                       "source": "Banco Central de Chile, Base de Datos Estadísticos, daily exchange rate of the euro in Chilean pesos",
                       "source_url": "https://si3.bcentral.cl/Siete/es/Siete/API", "source_series": "fixture-series-id"}},
    "asset_scaling": {
        **named("asset_scaling", r10(BANCO_ASSETS / (C17_ASSETS_EUR_M * FX_RATE)), "Banco Andino assets over the assets of the C17 bank", "case assumption",
                "Derived at bake time: Banco Andino's total assets over the C17 synthetic bank's stated assets, converted at the rate (decision Q5, W5); "
                "this value is a fixture value"),
        "derivation": {"kind": "asset-ratio", "banco_andino_assets_clp_m": BANCO_ASSETS, "c17_bank_assets_eur_m": C17_ASSETS_EUR_M,
                       "converted_at": "operational_conversion_rate"}},
    "market_rwa_share": named("market_rwa_share", MIX["market"], "share of RWA", "case assumption",
                              "The market share of the 20-F RWA mix, as a ratio (decision Q5, Q4); C11's mixed-portfolio VaR and ES are scaled to it"),
    "market_horizon_scaling": {
        **named("market_horizon_scaling", r10(LEVEL_FACTOR * HORIZON_FACTOR), "multiplier on C11's 99 percent one-day measure", "convention",
                "From C11's 99 percent one-day figures to 99.9 percent and one year: the normal quantile ratio z_0.999 / z_0.99 times the square root of 250, "
                "both named conventions (W4)"),
        "source_confidence_level": 0.99, "source_horizon_days": 1, "trading_days_per_year": 250,
        "level_factor": named("market_level_factor", LEVEL_FACTOR, "ratio of normal quantiles z_0.999 / z_0.99", "convention",
                              "The normal quantile ratio that moves C11's 99 percent measure to 99.9 percent: a convention of the case"),
        "horizon_factor": named("market_horizon_factor", HORIZON_FACTOR, "multiplier on a one-day measure, sqrt(250)", "convention",
                                "Square-root-of-time scaling from one day to one year with 250 trading days: a convention of the case"),
    },
    "reverse_p2_cet1": named("reverse_p2_cet1", 0.000625, "share of RWA", "case assumption",
                             "The CET1 share of the Pillar 2 requirement in the legal minimum stack (03 G.4: at most 4 percent in total, composition set bank by bank)"),
}


def cap_start() -> dict:
    return {
        "rwa_clp_m": RWA,
        "rwa_by_risk": {k: r6(RWA * MIX[k]) for k in ("credit", "market", "operational")},
        "cet1_clp_m": CET1_0, "at1_clp_m": AT1_0, "t2_clp_m": T2_0, "pe_clp_m": CET1_0 + AT1_0 + T2_0,
        "cet1_ratio": r10(CET1_0 / RWA), "pe_ratio": r10((CET1_0 + AT1_0 + T2_0) / RWA),
        "basis": txt("RWA is the C15 Tier 1 proxy over the 11.0 percent anchor, split by the 20-F mix; the capital stock is the proxy (decision Q4). Fixture values."),
    }


def fix_rwa_by_risk(c: dict) -> dict:
    parts = c["rwa_by_risk"]
    parts["operational"] = r6(RWA - parts["credit"] - parts["market"])
    return c


# ------------------------------------------------------------------------------------------------ the scenarios

PROFILE = {
    "baseline": [0.0] * 12,
    "eba": [0.1, 0.25, 0.45, 0.65, 0.85, 0.9, 0.85, 0.75, 0.65, 0.55, 0.45, 0.4],
    "fed": [0.15, 0.4, 0.7, 0.95, 1.0, 0.95, 0.85, 0.75, 0.65, 0.55, 0.5, 0.45],
    "ngfs": [0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.65, 0.7, 0.7],
}
BASE_RATE = {"commercial-industrial": 0.005, "commercial-real-estate": 0.003, "residential": 0.002, "credit-cards": 0.04, "other-consumer": 0.02}
#: the identity-link segments: the projected rate is linear in the severity profile and the residential baseline is a net recovery
IDENTITY_LEVEL = {"commercial-real-estate": (0.003, 0.004), "residential": (-0.0002, 0.0012)}
SENS = {"commercial-industrial": 1.6, "commercial-real-estate": 2.0, "residential": 1.5, "credit-cards": 0.9, "other-consumer": 1.0}
MARKET_LOSS = {"baseline": [3000.0] * 3, "eba": [60000.0, 30000.0, 20000.0], "fed": [110000.0, 50000.0, 30000.0], "ngfs": [30000.0, 45000.0, 40000.0]}
IRRBB_LOSS = {"baseline": [2000.0] * 3, "eba": [25000.0, 30000.0, 28000.0], "fed": [30000.0, 40000.0, 35000.0], "ngfs": [12000.0, 20000.0, 22000.0]}
OP_LOSS = {"baseline": [22000.0] * 3, "eba": [28000.0, 30000.0, 30000.0], "fed": [30000.0, 34000.0, 34000.0], "ngfs": [24000.0, 26000.0, 26000.0]}
SCALE = {"baseline": (1.0, 1.0, 1.0), "eba": (1.25, 1.1, 1.15), "fed": (1.40, 1.3, 1.25), "ngfs": (1.18, 1.1, 1.20)}   # credit, market, irrbb
NII_BASE = 660_000.0


def rates(key: str) -> dict[str, list[float]]:
    return {t: [r10(IDENTITY_LEVEL[t][0] + IDENTITY_LEVEL[t][1] * s) if t in IDENTITY else r10(BASE_RATE[t] * math.exp(SENS[t] * s))
               for s in PROFILE[key]] for t, _ in FED}


def class_rates(key: str) -> dict[str, list[float]]:
    fr = rates(key)
    out = {}
    for c in CLASSES:
        types, w = CLASS_MAP[c]
        out[c] = [r10(sum(wi * fr[t][k] for wi, t in zip(w, types))) for k in range(12)]
    return out


def credit_losses(key: str) -> list[float]:
    cr = class_rates(key)
    return [r6(sum(EXPOSURE[c] * sum(cr[c][4 * y:4 * y + 4]) / 4 for c in CLASSES)) for y in range(3)]


def satellites_block(key: str) -> dict:
    fr, cr = rates(key), class_rates(key)
    return {
        "fed_loan_types": [{
            "fed_loan_type": t, "series_id": sid, "model_id": f"c18-satellite-{t}", "link": "identity" if t in IDENTITY else "probit",
            "quarters": [{"quarter_end": QUARTERS[k], "rate": fr[t][k], "link_value": fr[t][k] if t in IDENTITY else r10(ND.inv_cdf(fr[t][k]))}
                         for k in range(12)],
        } for t, sid in FED],
        "banco_andino_classes": [{
            "banco_andino_class": c, "maps_from": CLASS_MAP[c][0], "weights": CLASS_MAP[c][1], "exposure_clp_m": EXPOSURE[c],
            "label": "us-calibrated-adaptation",
            "quarters": [{"quarter_end": QUARTERS[k], "rate": cr[c][k]} for k in range(12)],
        } for c in CLASSES],
    }


def losses_block(key: str) -> dict:
    cl = credit_losses(key)
    scale_c, scale_m, scale_i = SCALE[key]
    rows = []
    for y in range(3):
        vals = {"credit": cl[y], "market": MARKET_LOSS[key][y], "irrbb": IRRBB_LOSS[key][y], "operational": OP_LOSS[key][y]}
        rows.append({"year": y + 1, "period_end": YEAR_ENDS[y], **vals, "total": r6(sum(vals.values()))})
    return {"scenario_losses": rows,
            "basis": txt("Expected losses of the scenario by risk and year: credit from the satellite projections times the book of each class, the other risks "
                         "from the marginal scaling of the variant. Fixture values.")}


def fed_path(var: str, unit: str, regressor: str, jump: float, shape: list[float], sign: float, amp: float, scenario: str) -> dict:
    s13 = shape
    pts = [{"date": q, "value": round(jump + sign * amp * s13[k], 3)} for k, q in enumerate(QUARTERS + ["2027-03-31"])]
    return {
        "variable": var, "unit": unit, "maps_to_regressor": regressor, "frequency": "quarterly", "vintage_date": "2026-02-04",
        "level_rule": {"kind": "level", "baseline": None},
        "source": pts, "levels": json.loads(json.dumps(pts)),
        "transposition": {
            "label": "transposed-onto-banco-andino-jump-off", "rule": "shape-onto-last-observed-then-revert-to-baseline",
            "source_jump_off": {"date": JUMP, "value": jump}, "target": {"date": JUMP, "value": jump},
            "reversion": "none-within-horizon",
        },
        "transposed": [{"date": QUARTERS[k], "value": round(jump + (pts[k]["value"] - jump), 3)} for k in range(12)],
    }


FED_SHAPE13 = [0.15, 0.4, 0.7, 0.95, 1.0, 0.95, 0.85, 0.75, 0.65, 0.55, 0.5, 0.45, 0.4]
BASE_SHAPE13 = [0.0] * 13


def fed_scenario(key: str) -> dict:
    sev = key == "fed"
    shape = FED_SHAPE13 if sev else [0.02 * k for k in range(1, 14)]
    paths = [
        fed_path("unemployment_rate", "percent", "unemployment_rate", 4.5, shape, 1.0, 5.5 if sev else 1.0, key),
        fed_path("real_gdp_growth", "percent, annualised", "real_gdp_growth", 2.0, shape, -1.0, 7.0 if sev else 0.5, key),
        fed_path("prime_rate", "percent", "prime_rate", 7.5, shape, -1.0, 4.0 if sev else 0.5, key),
    ]
    return {
        "scenario_id": SCEN_ID[key],
        "title": txt("Federal Reserve 2026 severely adverse" if sev else "Baseline (Federal Reserve 2026 shape)",
                     "Severamente adverso de la Reserva Federal 2026" if sev else "Base (forma Reserva Federal 2026)"),
        "provider": "fed",
        "source_document": "2026_Final_Supervisory_Severely_Adverse_Domestic.csv" if sev else "2026_Final_Supervisory_Baseline_Domestic.csv",
        "source_url": "https://www.federalreserve.gov/supervisionreg/files/2026_Final_Supervisory_Severely_Adverse_Domestic.csv" if sev
        else "https://www.federalreserve.gov/supervisionreg/files/2026_Final_Supervisory_Baseline_Domestic.csv",
        "vintage_date": "2026-02-04",
        "adaptation_label": "us-calibrated-adaptation",
        "adaptation_statement": txt("The path is a United States path transposed onto the last observed value; the satellites are fitted on United States charge-off rates and applied to Banco Andino."),
        "paths": paths,
        "policy_shock_window": None,
    }


def annual_join(levels: list[float], jump_level: float, target: float) -> list[float]:
    out, prev = [], jump_level
    for lv in levels:
        for k in range(1, 5):
            out.append(round(target + (prev + (lv - prev) * k / 4 - jump_level), 8))
        prev = lv
    return out


def eba_path(var: str, unit: str, regressor: str, jump: float, levels: list[float], target: float) -> dict:
    pts = [{"date": f"{2025 + i}-12-31", "value": v} for i, v in enumerate(levels)]
    vals = annual_join(levels, jump, target)
    return {
        "variable": var, "unit": unit, "maps_to_regressor": regressor, "frequency": "annual", "vintage_date": "2025-02-26",
        "level_rule": {"kind": "level", "baseline": None},
        "source": pts, "levels": json.loads(json.dumps(pts)),
        "transposition": {
            "label": "transposed-onto-banco-andino-jump-off", "rule": "shape-onto-last-observed-then-revert-to-baseline",
            "source_jump_off": {"date": "2024-12-31", "value": jump}, "target": {"date": JUMP, "value": target},
            "reversion": "none-within-horizon",
        },
        "transposed": [{"date": QUARTERS[k], "value": vals[k]} for k in range(12)],
    }


def eba_scenario() -> dict:
    return {
        "scenario_id": "eba-2025-adverse",
        "title": txt("EBA and ESRB 2025 adverse scenario", "Escenario adverso EBA y ESRB 2025"),
        "provider": "eba-esrb",
        "source_document": "2025 EU-wide stress test - Macro financial scenario (updated 26 February 2025)",
        "source_url": "https://www.eba.europa.eu/sites/default/files/2025-03/d0668400-aed7-40d7-b668-1f77eb24b934/2025%20EU-wide%20stress%20test%20-%20Macro%20financial%20scenario%20%28updated%2026%20February%202025%29-incl%20disclaimer%20for%20EBA%20%285%29.xlsx",
        "vintage_date": "2025-02-26",
        "adaptation_label": "us-calibrated-adaptation",
        "adaptation_statement": txt("A country-year path for 2025 to 2027 from year-end 2024, transposed onto the United States last observed value; the satellites are US-calibrated."),
        "paths": [
            eba_path("Real GDP growth", "percent", "real_gdp_growth", 1.2, [-1.5, -2.0, 0.5], 2.0),
            eba_path("Unemployment rate", "percent", "unemployment_rate", 6.0, [7.0, 8.5, 8.0], 4.5),
            eba_path("Long-term interest rate", "percent", "treasury_10y", 2.6, [3.0, 3.8, 3.5], 4.1),
        ],
        "policy_shock_window": None,
    }


NGFS_BASE = {
    "Unemployment rate ; %(combined)": ("Abs. difference", "baseline-plus-deviation", [4.442, 4.494, 4.537], [0.106, 0.408, 0.324], (4.377, -0.047), "unemployment_rate", 4.5),
    "Central bank Intervention rate (policy interest rate) ; %(combined)": ("Abs. difference", "baseline-plus-deviation", [3.25, 3.25, 3.25], [0.03, -0.57, -0.603], (3.25, 0.0), "prime_rate", 7.5),
    "Long term interest rate ; %(combined)": ("Abs. difference", "baseline-plus-deviation", [3.27, 3.262, 3.26], [-0.023, 0.043, 0.157], (3.282, 0.0), "treasury_10y", 4.1),
    "Gross Domestic Product (GDP)(combined)": ("% difference,  2017 PPP ; US$ Bn", "baseline-times-percent-deviation", [26000.0, 26500.0, 27000.0], [-4.239, -5.251, -5.558], (25481.079, -3.378), "real_gdp_growth", 2.0),
}


def ngfs_path(name: str) -> dict:
    unit, kind, base, dev, (b0, d0), regressor, target = NGFS_BASE[name]
    years = ["2031-12-31", "2032-12-31", "2033-12-31"]
    src = [{"date": y, "value": v} for y, v in zip(years, dev)]
    bl = [{"date": y, "value": v} for y, v in zip(years, base)]
    if kind == "baseline-plus-deviation":
        levels = [r10(b + d) for b, d in zip(base, dev)]
        jump_level = r10(b0 + d0)
        transposed = annual_join(levels, jump_level, target)
    else:
        levels = [r10(b * (1 + d / 100)) for b, d in zip(base, dev)]
        jump_level = r10(b0 * (1 + d0 / 100))
        growth, prev = [], jump_level
        for lv in levels:
            growth.append(round((lv / prev - 1) * 100, 4))
            prev = lv
        transposed = [round(g, 4) for g in growth for _ in range(4)]
    return {
        "variable": name, "unit": unit, "maps_to_regressor": regressor, "frequency": "annual", "vintage_date": "2024-11-01",
        "level_rule": {"kind": kind, "baseline": bl},
        "source": src, "levels": [{"date": y, "value": v} for y, v in zip(years, levels)],
        "transposition": {
            "label": "transposed-onto-banco-andino-jump-off", "rule": "shape-onto-last-observed-then-revert-to-baseline",
            "source_jump_off": {"date": "2030-12-31", "value": jump_level}, "target": {"date": JUMP, "value": target},
            "reversion": "none-within-horizon",
        },
        "transposed": [{"date": QUARTERS[k], "value": transposed[k]} for k in range(12)],
    }


def ngfs_scenario() -> dict:
    return {
        "scenario_id": "ngfs-delayed-transition",
        "title": txt("NGFS Phase 5 delayed transition (disorderly)", "Transicion tardia NGFS fase 5 (desordenada)"),
        "provider": "ngfs",
        "source_document": "NGFS Phase V, NiGEM NGFS v1.24.2 runs, read through the IIASA Scenario Explorer (IXSE_NGFS_PHASE_5)",
        "source_url": "https://data.ene.iiasa.ac.at/ngfs",
        "vintage_date": "2024-11-01",
        "adaptation_label": "us-calibrated-adaptation",
        "adaptation_statement": txt("The United States NiGEM deviations of the three years in which the policy shock acts, transposed onto the last observed value; the satellites are US-calibrated."),
        "paths": [ngfs_path(n) for n in NGFS_BASE],
        "policy_shock_window": {"start_year": 2031, "end_year": 2033,
                                "label": txt("The policy shock acts in 2031 to 2033: zero deviation through 2030 and the first deviation in 2031 (F8 of the research addendum)")},
    }


def scenario_block(key: str) -> dict:
    return {"baseline": lambda: fed_scenario("baseline"), "fed": lambda: fed_scenario("fed"), "eba": eba_scenario, "ngfs": ngfs_scenario}[key]()


# ------------------------------------------------------------------------------------------------ the aggregation block


def marginals(key: str, op_infinite: bool = False) -> list[dict]:
    sc, sm, si = SCALE[key]
    base = {
        "credit": (140_000.0, 1_190_000.0, 1_300_000.0, sc), "market": (5_000.0, 225_000.0, 262_000.0, sm),
        "irrbb": (2_000.0, 182_000.0, 210_000.0, si), "operational": (20_000.0, 280_000.0, 345_000.0, 1.0),
    }
    producer = {"credit": "credit-grouped-copula-c07-segments", "market": "market-c11-mixed-portfolio-scaled-to-market-rwa",
                "irrbb": "irrbb-engine-simulation-c15-curve-and-book", "operational": "operational-oprisk-aggregate-c17-parameters-scaled"}
    docs = {"credit": ["c07-outputs", "riskvalidation.portfolio.portfolio.portfolio_from_groups"],
            "market": ["c11-outputs mixed-2023", "market share of RWA from the 20-F mix (ratio)"],
            "irrbb": ["c15-outputs", "riskvalidation.irrbb.simulation.ear_evar"],
            "operational": ["c17-models generator parameters", "riskvalidation.oprisk.aggregate"]}
    scal = {"credit": [], "irrbb": [],
            "market": [NAMED["market_rwa_share"], NAMED["market_horizon_scaling"]],
            "operational": [NAMED["asset_scaling"], NAMED["operational_conversion_rate"]]}
    stmt = {"credit": "No scaling: the grouped copula runs on the C07 segments of Banco Andino.",
            "irrbb": "No scaling: the engine simulation runs on the C15 curve and book of Banco Andino.",
            "market": "C11's mixed-portfolio VaR and ES scaled to the market share of RWA, with the horizon scaling stated as an assumption.",
            "operational": "The C17 generator frequency scaled by assets, the loss distribution recomputed through oprisk.aggregate and converted at a stated rate."}
    out = []
    for r in RISKS:
        el, var, es, f = base[r]
        el, var, es = round(el * f, 2), round(var * f, 2), round(es * f, 2)
        undefined = op_infinite and r == "operational"
        out.append({
            "risk": r, "horizon_years": 1, "confidence_level": 0.999, "el_clp_m": None if undefined else el,
            "el_status": "undefined (infinite mean)" if undefined else "finite", "var_clp_m": var, "es_clp_m": es,
            "ec_clp_m": var if undefined else r6(var - el),
            "ec_basis": "var-alone-infinite-mean" if undefined else "var-less-el",
            "ec_label": txt("The severity has an infinite mean (xi of 1 or more): the expected loss is undefined, so the EC is the VaR alone (05 l.482)")
            if undefined else None,
            "var_se_clp_m": None if r in ("irrbb",) else round(var * 0.002, 2),
            "producer": producer[r], "source_documents": docs[r],
            "scaling": {"statement": txt(stmt[r]), "parameters": scal[r]},
        })
    return out


def varcov(ec: list[float], r: list[list[float]]) -> float:
    return math.sqrt(sum(ec[i] * r[i][j] * ec[j] for i in range(4) for j in range(4)))


def aggregation_block(key: str, corr: list[list[float]], corr_named: dict, lift: float = 1.0, op_infinite: bool = False) -> dict:
    marg = marginals(key, op_infinite)
    ec = [m["ec_clp_m"] for m in marg]
    total = r6(sum(ec))
    vc = r6(varcov(ec, corr))
    gauss = r6(vc * 1.03)
    lower, worst = r6(0.62 * total), r6(1.18 * total)
    tfac = {4.0: 1.07, 8.0: 1.035, 30.0: 1.01}

    def row(method: str, nu: float | None, cap: float) -> dict:
        return {
            "method": method, "nu": nu, "capital_clp_m": cap, "diversification_factor": r10(cap / total),
            "status": "headline-capital" if method == "simple-sum" else "information-not-capital",
            "label": txt("Headline capital: the simple sum of the four marginals" if method == "simple-sum"
                         else "Information, not capital: a diversified or bound figure shown for the validator"),
            "horizon_years": 1, "confidence_level": 0.999,
            "mc_se_clp_m": round(cap * 0.003, 2) if method in ("gaussian-copula", "t-copula") else None,
        }

    band = [row("lower-bound", None, lower), row("simple-sum", None, total), row("variance-covariance", None, vc), row("gaussian-copula", None, gauss)]
    band += [row("t-copula", nu, r6(gauss * tfac[nu])) for nu in NU_SET] + [row("worst-case", None, worst)]
    caps = [r["capital_clp_m"] for r in band]
    hi, lo = max(caps), min(caps)
    x0 = gauss
    es_sum = sum(m["es_clp_m"] for m in marg)
    es_total = round(0.93 * es_sum * (gauss / (vc * 1.03)) * (lift), 2)
    weights = [1.0, 0.8, 0.7, 0.9]
    raw = [m["es_clp_m"] * w for m, w in zip(marg, weights)]
    contrib = [round(es_total * x / sum(raw), 2) for x in raw[:3]]
    contrib.append(round(es_total - sum(contrib), 2))
    s = sum(contrib)
    return {
        "capital_basis": "economic-capital-var-less-el", "horizon_years": 1, "confidence_level": 0.999,
        "correlation": corr_named, "nu_set": NAMED["nu_set"], "marginals": marg,
        "headline": {"method": "simple-sum", "capital_clp_m": total,
                     "label": txt("The headline capital of C18 is the simple sum: the IAPE adds up the capital needed for each risk and the ECB does not recognise inter-risk diversification in the SREP")},
        "band": band,
        "model_risk": {
            "status": "information-not-capital",
            "label": txt("Information, not capital: model risk measures are sensitivity information for the validator"),
            "set_of_models": "band-rows", "reference_model": {"method": "gaussian-copula", "nu": None},
            "barrieu_scandolo": {"rho_x0_clp_m": x0, "rho_max_clp_m": hi, "rho_min_clp_m": lo, "am": r10(hi / x0 - 1), "rm": r10((hi - x0) / (hi - lo))},
            "glasserman_xu": {"quantity": txt("Expected loss of the aggregate in the 99.9 percent tail under the Gaussian copula"),
                              "relative_entropy_budget": 0.05, "theta": 0.8, "baseline_clp_m": es_total, "worst_case_clp_m": round(es_total * 1.12, 2)},
        },
        "euler": {
            "status": "information-not-capital",
            "label": txt("Information, not capital: an allocation of the aggregate expected shortfall shown for the validator"),
            "risk_measure": "es", "level": 0.999, "horizon_years": 1, "copula": {"family": "gaussian", "nu": None},
            "es_total_clp_m": es_total,
            "allocation": [{"risk": r, "contribution_clp_m": c, "share": r10(c / es_total)} for r, c in zip(RISKS, contrib)],
            "additivity": {"sum_clp_m": s, "relative_error": abs(s - es_total) / es_total, "tolerance": 1e-6},
        },
        "diversification": {
            "status": "information-not-capital",
            "label": txt("Information, not capital: the diversification of the Gaussian copula row against the simple sum"),
            "reference_row": {"method": "gaussian-copula", "nu": None},
            "factor": r10(gauss / total), "benefit": r10(1 - gauss / total),
            "euler_benefit_by_risk": [{"risk": r, "benefit": r10(1 - c / m["es_clp_m"])} for r, c, m in zip(RISKS, contrib, marg)],
        },
    }


# ------------------------------------------------------------------------------------------------ capital, plan, annex, back-cast


def nii_rows(key: str) -> list[float]:
    return [round(NII_BASE * (1 - 0.10 * sum(PROFILE[key][4 * y:4 * y + 4]) / 4), 2) for y in range(3)]


def headline_block(key: str) -> tuple[dict, list[float], list[float]]:
    losses = [y["total"] for y in losses_block(key)["scenario_losses"]]
    cum, rows, prev, path = 0.0, [], CET1_0, []
    for y in range(3):
        cum = r6(cum + losses[y])
        cet1 = r6(CET1_0 - cum)
        rows.append({"year": y + 1, "period_end": YEAR_ENDS[y], "cet1_start_clp_m": prev, "cumulative_loss_clp_m": cum, "cet1_clp_m": cet1,
                     "rwa_clp_m": RWA, "cet1_ratio": r10(cet1 / RWA)})
        prev = cet1
        path.append(cet1)
    nii = nii_rows(key)
    prow, cumppnr, ppnr_list = [], 0.0, []
    for y in range(3):
        fee = round(FEE * nii[y], 6)
        cost = round(COST * (nii[y] + fee), 6)
        ppnr = r6(nii[y] + fee - cost)
        cumppnr = r6(cumppnr + ppnr)
        ppnr_list.append(ppnr)
        with_ = r6(path[y] + cumppnr)
        prow.append({"year": y + 1, "period_end": YEAR_ENDS[y], "nii_clp_m": nii[y], "fee_income_clp_m": fee, "operating_cost_clp_m": cost,
                     "ppnr_clp_m": ppnr, "cet1_with_ppnr_clp_m": with_, "cet1_ratio_with_ppnr": r10(with_ / RWA)})
    block = {
        "method": "loss-only-depletion",
        "statement": txt("CET1 at the jump-off less the cumulative stressed losses; no revenue is invented. The row with PPNR is labelled and is not the headline."),
        "rows": rows,
        "ppnr": {"label": "ppnr-labelled-row", "statement": txt("PPNR from the C15 dynamic NII plus a stated fee ratio and cost ratio, both assumptions of the case."),
                 "nii_source": "c15-dynamic-nii", "fee_ratio": NAMED["ppnr_fee_ratio"], "cost_ratio": NAMED["ppnr_cost_ratio"], "rows": prow},
    }
    return block, path, ppnr_list


OI = 0.08 + 0.015 + 0.01 + 0.025 + 0.005 + 0.01
LEGAL = 0.08 + 0.015 + 0.00125
ACTIONS = [
    {"id": "capital-increase", "description": txt("A CET1 capital increase in years 2 and 3"), "label": "case assumption", "cet1_effect_clp_m": [0.0, 100_000.0, 100_000.0]},
    {"id": "cost-reduction-programme", "description": txt("A cost reduction programme that retains earnings"), "label": "case assumption", "cet1_effect_clp_m": [20_000.0, 40_000.0, 40_000.0]},
]


def cap_row(available: float, need: float | None) -> dict:
    return {"pct_of_rwa": r10(available / RWA), "need_clp_m": need, "available_clp_m": available}


def plan_year(y: int, cet1: float, basis: str, req: float) -> dict:
    pe = r6(cet1 + AT1_0 + T2_0)
    need = r6(req * RWA)
    return {
        "year": y + 1, "period_end": YEAR_ENDS[y], "rwa_clp_m": RWA,
        "cet1": cap_row(cet1, None), "at1": cap_row(AT1_0, None), "t2": cap_row(T2_0, None), "pe": cap_row(pe, need),
        "requirement": {"basis": basis, "pct_of_rwa": req},
        "headroom_pct_of_rwa": r10(pe / RWA - req), "deficit_clp_m": r6(max(0.0, need - pe)),
    }


def baseline_cet1_path() -> list[float]:
    _, _, ppnr = headline_block("baseline")
    losses = [y["total"] for y in losses_block("baseline")["scenario_losses"]]
    out, cet1 = [], CET1_0
    for y in range(3):
        cet1 = r6(cet1 + ppnr[y] - losses[y])
        out.append(cet1)
    return out


def plan_block(key: str, path: list[float]) -> dict:
    applies = key != "baseline"
    cum, running = [], 0.0
    for k in range(3):
        running += sum(a["cet1_effect_clp_m"][k] for a in ACTIONS) if applies else 0.0
        cum.append(running)
    base = baseline_cet1_path()
    return {
        "cases": [
            {"case": "base", "years": [plan_year(y, base[y], "internal-target", OI) for y in range(3)]},
            {"case": "stress-without-mitigation", "years": [plan_year(y, path[y], "legal-minimum", LEGAL) for y in range(3)]},
            {"case": "stress-with-mitigation", "years": [plan_year(y, r6(path[y] + cum[y]), "legal-minimum", LEGAL) for y in range(3)]},
        ],
        "mitigation": ({"applies": True, "reason": None, "actions": ACTIONS} if applies else
                       {"applies": False, "reason": txt("The baseline scenario leaves no deficit against the legal minimum, so no mitigation action is taken"), "actions": []}),
        "alternative_sources": [],
    }


def oi_block() -> dict:
    return {
        "formula": "OI >= 8% + c_DSIB + c_P2 + c_CCoB + c_CCyB + c_d, as percent of RWA (RAN 21-13 section I; 03 l.152-169)",
        "horizon_years": 3, "min_pe": 0.08, "c_dsib": STACK["c_dsib"], "c_p2": NAMED["c_p2"], "c_ccob": STACK["c_ccob"], "c_ccyb": STACK["c_ccyb"],
        "c_d": NAMED["c_d"], "oi": r10(OI),
    }


def p2g_block(path: list[float]) -> dict:
    dep = [r10(CET1_0 / RWA - c / RWA) for c in path]
    peak = max(dep)
    usable = 0.02
    return {
        "label": "contraste-approximation",
        "formula": "max over t of [(CET1/RWA)_0 - (CET1/RWA)_t severe] less the usable buffers and mitigation, floored at zero (03 l.1001-1005, FAQ 24)",
        "peak_depletion": peak, "peak_year": dep.index(peak) + 1, "usable_buffers_and_mitigation": usable, "value": r10(max(0.0, peak - usable)),
        "statement": txt("A Contraste approximation consistent with FAQ 24: the CMF calibration grid is not public and this is not a P2G requirement."),
        "cmf_calibration_public": False,
    }


NA = {"value": None, "status": "not-applicable"}
RI = {"value": None, "status": "RI"}
NTF = {"value": None, "status": "not-to-be-filled"}


def v(x: float) -> dict:
    return {"value": x, "status": "value"}


def annex3_block(key: str, path: list[float], plan: dict, ec: dict) -> dict:
    cs_ = cap_start()
    ratio = r10(CET1_0 / RWA)
    pe_ratio = r10((CET1_0 + AT1_0 + T2_0) / RWA)
    rwa_by = cs_["rwa_by_risk"]
    rows = {
        "1": (NA, NA, NA, NA),
        "1.1": (v(pe_ratio), v(CET1_0 + AT1_0 + T2_0), NA, NA),
        "1.2": (v(r10((CET1_0 + AT1_0) / RWA)), v(CET1_0 + AT1_0), NA, NA),
        "1.3": (v(ratio), v(CET1_0), NA, NA),
        "2": (v(pe_ratio), v(CET1_0 + AT1_0 + T2_0), NA, NA),
        "2.T2": (v(r10(T2_0 / RWA)), v(T2_0), NA, NA),
        "2.AT1": (v(r10(AT1_0 / RWA)), v(AT1_0), NA, NA),
        "2.CET1": (v(ratio), v(CET1_0), NA, NA),
        "3": (v(1.0), v(RWA), NA, NA),
        "4": (NA, NA, v(r6(0.08 * RWA)), NA),
        "4.1": (NA, NA, v(r6(0.08 * rwa_by["credit"])), NA),
        "4.1.1": (NA, NA, v(r6(0.08 * rwa_by["credit"])), NA),
        "4.1.2": (NA, NA, NA, v(ec["credit"])),
        "4.2": (NA, NA, v(r6(0.08 * rwa_by["market"])), NTF),
        "4.3": (NA, NA, v(r6(0.08 * rwa_by["operational"])), NTF),
        "4.4": (NA, NA, NA, NA), "4.4.1": (NA, NA, NA, RI), "4.4.2": (NA, NA, NA, RI), "4.4.3": (NA, NA, NA, RI),
        "4.5": (NA, NA, NA, v(ec["irrbb"])), "4.6": (NA, NA, NA, RI), "4.7": (NA, NA, NA, RI), "4.8": (NA, NA, NA, RI),
        "5": (v(r10(OI)), v(r6(OI * RWA)), NA, NA),
        "6": (v(r10(ec["irrbb"] / RWA)), v(ec["irrbb"]), NA, NA),
        "7": (v(r10(LEGAL)), v(r6(LEGAL * RWA)), NA, NA),
        "7.1": (v(STACK["c_dsib"]), v(r6(STACK["c_dsib"] * RWA)), NA, NA),
        "7.2": (v(STACK["p2r"]), v(r6(STACK["p2r"] * RWA)), NA, NA),
        "8": (v(r10(ec["irrbb"] / RWA - STACK["p2r"])), v(r6(ec["irrbb"] - STACK["p2r"] * RWA)), NA, NA),
        "9": (v(r10(STACK["c_ccob"] + STACK["c_ccyb"])), v(r6((STACK["c_ccob"] + STACK["c_ccyb"]) * RWA)), NA, NA),
    }
    plan_cases = {c["case"]: c for c in plan["cases"]}
    for rid, case in (("10.1", "stress-without-mitigation"), ("10.2", "stress-with-mitigation")):
        impact = r10(max(ratio - y["cet1"]["pct_of_rwa"] for y in plan_cases[case]["years"]))
        rows[rid] = (NA if (rid == "10.2" and not plan["mitigation"]["applies"]) else v(impact), NA, NA, NA)
    rows["11"] = (v(0.01), v(r6(0.01 * RWA)), NA, NA)
    rows["12"] = (v(r10(pe_ratio - r10(OI))), v(r6((pe_ratio - r10(OI)) * RWA)), NA, NA)
    out = []
    for rid, label in ANNEX3:
        a, b, c, d = rows[rid]
        out.append({"row_id": rid, "label_cmf": label, "a": a, "b": b, "c": c, "d": d})
    return {"entity": "Banco Andino", "report_date": AS_OF, "consolidation": "local", "money_unit": "CLP millions", "rows": out}


ANNEX3 = [
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


def backcast_block() -> dict:
    qs = [f"{2020 + k // 4}-{('03-31', '06-30', '09-30', '12-31')[k % 4]}" for k in range(24)]
    per = []
    for t, sid in FED:
        base = BASE_RATE[t]
        realised = [r10(base * (1 + 0.8 * math.exp(-((k - 3) ** 2) / 8))) for k in range(24)]
        predicted = [r10(base * (1 + 0.6 * math.exp(-((k - 4) ** 2) / 10))) for k in range(24)]
        if t == "commercial-real-estate":
            realised[10] = 0.0          # the Board's 2022 Q2 value: a net recovery
        if t == "residential":
            realised = [r10(v / 100.0) for v in RERES_REALISED_PCT]
            predicted = [r10(-0.0002 + 0.0004 * math.exp(-((k - 4) ** 2) / 10)) for k in range(24)]
        rmse = math.sqrt(sum((p - r) ** 2 for p, r in zip(predicted, realised)) / 24)
        ip, ir = predicted.index(max(predicted)), realised.index(max(realised))
        per.append({
            "fed_loan_type": t, "series_id": sid, "link": "identity" if t in IDENTITY else "probit",
            "fit_window": {"start": TYPE_START[t], "end": FIT_END},
            "quarters": [{"quarter_end": q, "predicted": p, "realised": r} for q, p, r in zip(qs, predicted, realised)],
            "metrics": {"rmse": r10(rmse), "peak_predicted": predicted[ip], "peak_predicted_quarter": qs[ip], "peak_realised": realised[ir],
                        "peak_realised_quarter": qs[ir], "peak_timing_error_quarters": ip - ir},
        })
    return {
        "window": {"start": "2020-03-31", "end": "2025-12-31"},
        "per_loan_type": per,
        "descriptive_2026": [{"quarter_end": q, "realised_rates": [{"fed_loan_type": t, "rate": 0.0 if t == "residential" else r10(BASE_RATE[t] * 1.1)}
                                                                  for t, _ in FED],
                              "label": "rate-only-descriptive", "forecast_claim": False} for q in ("2026-03-31", "2026-06-30")],
        "statement": txt("Satellites fitted on 1985 to 2019, predicted against the realised charge-off rates of 2020 Q1 to 2025 Q4; 2026 Q1 and Q2 are shown as realised rates only, with no forecast claim."),
    }


# ------------------------------------------------------------------------------------------------ the documents

IMPACT_LABELS = {
    "capital_simple_sum": ("CLP millions", "Headline capital: the simple sum of the four marginals"),
    "cet1_ratio_end_stress": ("share of RWA", "CET1 ratio at the end of year 3 under the stress without mitigation"),
    "oi_headroom_min": ("share of RWA", "Smallest headroom of the PE ratio over the internal target in the stress without mitigation"),
    "p2g_proxy": ("share of RWA", "P2G proxy, a Contraste approximation"),
}
SCENARIO_TESTS = ["aggregation.simple_sum_and_variance_covariance", "aggregation.copula_choice_sensitivity", "aggregation.worst_case_bracket",
                  "aggregation.correlation_stress", "aggregation.diversification_sign", "aggregation.horizon_confidence_consistency",
                  "portfolio.euler_additivity", "stress.satellite_backcast", "stress.sensitivity_monotonicity", "stress.static_balance_sheet_rules",
                  "stress.scenario_severity"]


#: the global financial crisis peaks of the severity block: fixture values (the bake reads the Board's historic table)
GFC_PEAK = {"unemployment_rate": 5.5, "real_gdp_growth": 6.0, "prime_rate": 4.0, "treasury_10y": 2.0}


def severity_block(key: str, scenario: dict) -> dict:
    rows = []
    for p in scenario["paths"]:
        target = p["transposition"]["target"]["value"]
        devs = [abs(q["value"] - target) for q in p["transposed"]]
        peak = max(devs)
        hist = GFC_PEAK[p["maps_to_regressor"]]
        rows.append({
            "variable": p["variable"], "maps_to_regressor": p["maps_to_regressor"], "unit": p["unit"], "path_peak_deviation": r10(peak),
            "path_peak_quarter": p["transposed"][devs.index(peak)]["date"], "history_peak_deviation": hist,
            "history_window": {"start": "2008-03-31", "end": "2009-12-31"},
            "history_source": txt("Fixture value: the bake reads the peak deviation of the global financial crisis from the Board's historic table"),
            "ratio": r10(peak / hist), "is_stress": key != "baseline",
        })
    return {
        "reference_episode": {"name": "global-financial-crisis", "start": "2008-03-31", "end": "2009-12-31",
                              "source": txt("2008 to 2009, the episode the satellites are back-cast through and the EBA documents severity against (05 l.422)")},
        "minimum_ratio": 0.75, "rows": rows,
    }


def env_block() -> dict:
    return {"name": "Banco Andino", "synthetic": True, "as_of": AS_OF,
            "notice": txt("Banco Andino is a synthetic bank. Its book and capital are calibrated to public aggregates; every figure here is a fixture and no result.")}


UNITS = {"money": "CLP millions", "ratio": "decimal", "dates": "ISO date; quarters as the date of the quarter end"}


def scenario_doc(key: str, op_infinite: bool = False) -> dict:
    head, path, _ = headline_block(key)
    agg = aggregation_block(key, CORR_BASE, NAMED["correlation_matrix_base"], op_infinite=op_infinite)
    plan = plan_block(key, path)
    ec = {m["risk"]: m["ec_clp_m"] for m in agg["marginals"]}
    cs_ = fix_rwa_by_risk(cap_start())
    outputs = {
        "kind": "scenario", "currency": "CLP", "units": UNITS, "bank": env_block(), "capital_start": cs_,
        "scenario": scenario_block(key), "satellites": satellites_block(key), "losses": losses_block(key),
        "internal_capital_target": oi_block(), "capital_plan": plan, "p2g_proxy": p2g_block(path),
        "annex3": annex3_block(key, path, plan, ec), "headline_cet1": head, "severity": severity_block(key, scenario_block(key)),
        "backcast": backcast_block(), "aggregation": agg,
    }
    sw = plan["cases"][1]["years"]
    impact = {
        "capital_simple_sum": agg["headline"]["capital_clp_m"], "cet1_ratio_end_stress": sw[2]["cet1"]["pct_of_rwa"],
        "oi_headroom_min": r10(min(y["pe"]["pct_of_rwa"] for y in sw) - r10(OI)), "p2g_proxy": outputs["p2g_proxy"]["value"],
    }
    return envelope(f"fixture-{SCEN_ID[key]}", outputs, SCENARIO_TESTS, {k: impact_item(impact[k], *IMPACT_LABELS[k]) for k in IMPACT_LABELS})


def aggregation_doc(op_infinite: bool = False) -> dict:
    base = aggregation_block("baseline", CORR_BASE, NAMED["correlation_matrix_base"], op_infinite=op_infinite)
    ec = [m["ec_clp_m"] for m in base["marginals"]]
    lift = varcov(ec, CORR_STRESS) / varcov(ec, CORR_BASE)
    stress = aggregation_block("baseline", CORR_STRESS, NAMED["correlation_matrix_stress"], lift, op_infinite=op_infinite)
    gauss = next(r for r in base["band"] if r["method"] == "gaussian-copula")["capital_clp_m"]
    total = base["headline"]["capital_clp_m"]
    sens = []
    for nu in NU_SET:
        t = next(r for r in base["band"] if r["method"] == "t-copula" and r["nu"] == nu)["capital_clp_m"]
        sens.append({"nu": nu, "gaussian_capital_clp_m": gauss, "t_capital_clp_m": t, "relative_difference": r10(t / gauss - 1)})
    over = total / gauss - 1
    outputs = {
        "kind": "aggregation", "currency": "CLP", "units": UNITS, "bank": env_block(), "scenario_id": "baseline", "aggregation": base,
        "correlation_stress": {"pair": {"a": "market", "b": "credit", "value": 0.8}, "aggregation": stress},
        "copula_sensitivity": sens,
        "rosenberg_schuermann": {
            "role": "reference-not-a-gate",
            "weights": {"market": 0.041, "credit": 0.264, "operational": 0.695},
            "correlations": {"market_credit": 0.5, "market_operational": 0.2, "credit_operational": 0.2},
            "published_additive_overestimate": {"low": 0.30, "high": 0.40},
            "case_additive_overestimate": r10(over), "within_published_range": 0.30 <= over <= 0.40,
        },
    }
    tests = ["aggregation.simple_sum_and_variance_covariance", "aggregation.copula_choice_sensitivity", "aggregation.worst_case_bracket",
             "aggregation.correlation_stress", "aggregation.diversification_sign", "aggregation.horizon_confidence_consistency",
             "aggregation.elliptical_mc_agreement", "aggregation.rosenberg_schuermann_reference", "portfolio.euler_additivity"]
    impact = {
        "capital_simple_sum": impact_item(total, "CLP millions", "Headline capital: the simple sum of the four marginals"),
        "cet1_ratio_end_stress": impact_item(r10(CET1_0 / RWA), "share of RWA", "CET1 ratio at the jump-off (this variant runs the baseline, not a stress)"),
        "oi_headroom_min": impact_item(r10((CET1_0 + AT1_0 + T2_0) / RWA - r10(OI)), "share of RWA", "Headroom of the PE ratio over the internal target at the jump-off"),
        "p2g_proxy": impact_item(0.0, "share of RWA", "Not computed in this variant (it runs the aggregation only)"),
    }
    return envelope("fixture-t-copula-aggregation", outputs, tests, impact)


def reverse_doc() -> dict:
    sd = [2.1, 1.5]
    cov = [[4.41, -1.89], [-1.89, 2.25]]
    g = [-60_000.0, 110_000.0]
    total = r10(0.045 + 0.025 + 0.005 + 0.015 + 0.000625)
    start = r10(CET1_0 / RWA)
    l = r6((start - total) * RWA)
    sg = [sum(cov[i][j] * g[j] for j in range(2)) for i in range(2)]
    gsg = sum(g[i] * sg[i] for i in range(2))
    x = [r10(sg[i] * l / gsg) for i in range(2)]
    z = [r10(x[i] / sd[i]) for i in range(2)]
    dist = l / math.sqrt(gsg)
    tail = math.exp(-dist * dist / 2)
    loss = r6(sum(gi * xi for gi, xi in zip(g, x)))
    outputs = {
        "kind": "reverse", "currency": "CLP", "units": UNITS, "bank": env_block(),
        "failure_point": {
            "label": "contraste-formulation-not-regulatory",
            "definition": txt("CET1 over RWA reaches the Chilean legal minimum stack at the end of the three-year planning horizon: the formal statement is Contraste's, not regulatory text."),
            "stack": {"cet1_min": 0.045, "c_ccob": 0.025, "c_ccyb": 0.005, "c_dsib": 0.015, "p2_cet1": NAMED["reverse_p2_cet1"], "total": total,
                      "basis": "chilean-legal-minimum-stack"},
            "cet1_ratio_start": start, "rwa_clp_m": RWA, "horizon_years": 3,
        },
        "factor_space": {
            "window": {"start": FIT_START, "end": FIT_END},
            "factors": [{"id": "real_gdp_growth", "label": txt("Real GDP growth", "Crecimiento del PIB real"), "unit": "percentage points", "sd": sd[0]},
                        {"id": "unemployment_rate", "label": txt("Unemployment rate", "Tasa de desempleo"), "unit": "percentage points", "sd": sd[1]}],
            "covariance": cov, "label": "us-calibrated-adaptation",
        },
        "loss_model": {"kind": "linear", "gradient_clp_m_per_unit": g,
                       "description": txt("A linear loss in the factor deviations from the baseline: CLP millions per percentage point")},
        "solution": {
            "method": "closed-form-linear", "z_star": z, "x_star": x, "mahalanobis_distance": r10(dist),
            "plausibility": {"chi_square_df": 2, "tail_probability": r10(tail)},
            "loss_at_z_star_clp_m": loss, "loss_threshold_clp_m": l,
            "relative_gap": r10(abs(loss - l) / l), "tolerance": 1e-6,
        },
        "starts": [{"start_id": f"start-{k}", "converged": True, "distance": r10(dist * (1 + k * 1e-8)), "loss_clp_m": loss} for k in range(4)],
    }
    impact = {
        "capital_simple_sum": impact_item(0.0, "CLP millions", "Not computed in this variant (reverse stress)"),
        "cet1_ratio_end_stress": impact_item(total, "share of RWA", "CET1 ratio at the failure point: the legal minimum stack"),
        "oi_headroom_min": impact_item(0.0, "share of RWA", "Not computed in this variant"),
        "p2g_proxy": impact_item(0.0, "share of RWA", "Not computed in this variant"),
    }
    return envelope("fixture-reverse-stress", outputs, ["stress.reverse_solution_check"], impact)


def quantile_grid_fixture() -> dict:
    """The c18-models 3.0.0 quantile grid in the fixture's shape: 1,961 probabilities Phi(z), z = -4.9 to 4.9 in steps of 0.005, and a made-up
    smooth, increasing quantile function per marginal (a fixture value, never a result of a bake)."""
    zs = [k * 0.005 for k in range(-980, 981)]
    probs = [ND.cdf(z) for z in zs]
    scale = {"credit": 40_000.0, "market": 30_000.0, "irrbb": 12_000.0, "operational": 6_000.0}
    return {
        "convention": {"name": "standard-normal-z-grid", "z_min": -4.9, "z_max": 4.9, "z_step": 0.005, "points": 1961, "unit": "CLP millions",
                       "statement": txt("The probabilities are Phi(z) for z from -4.9 to 4.9 in steps of 0.005 (a fixture of the convention).")},
        "probabilities": probs,
        "marginals": [{"risk": r, "quantiles": [r6(scale[r] * math.exp(0.5 * z)) for z in zs]} for r in RISKS]}


def models_doc(op_infinite: bool = False) -> dict:
    sats = []
    for t, sid in FED:
        ident = t in IDENTITY
        sats.append({
            "model_id": f"c18-satellite-{t}", "fed_loan_type": t, "series_id": sid, "link": "identity" if ident else "probit",
            "sample_window": {"start": TYPE_START[t], "end": FIT_END}, "non_positive_quarters_in_window": NON_POSITIVE[t],
            "ar_order": 1, "n_obs": 115 if ident else 139,
            "regressors": [
                {"name": "real_gdp_growth", "lag": 0, "source_series": "Federal Reserve historic table, real GDP growth (agency series)", "licence_class": "agency"},
                {"name": "unemployment_rate", "lag": 1, "source_series": "Federal Reserve historic table, unemployment rate (agency series)", "licence_class": "agency"},
            ],
            "coefficients": [
                {"name": "intercept", "estimate": 0.0004 if ident else -0.9, "std_error": 0.0001 if ident else 0.12, "expected_sign": "none"},
                {"name": "ar_1", "estimate": 0.82, "std_error": 0.04, "expected_sign": "positive"},
                {"name": "real_gdp_growth_lag0", "estimate": -0.0004 if ident else -0.045, "std_error": 0.0001 if ident else 0.011, "expected_sign": "negative"},
                {"name": "unemployment_rate_lag1", "estimate": 0.0003 if ident else 0.06, "std_error": 0.0001 if ident else 0.02, "expected_sign": "positive"},
            ],
            "fit_statistics": {"r_squared": 0.78, "residual_sd": 0.21},
            "estimation": "ols-numpy-with-standard-errors",
        })
    fit = {
        "currency": "CLP", "units": UNITS, "bank": env_block(), "satellites": sats,
        "class_mapping": [{"banco_andino_class": c, "fed_loan_types": CLASS_MAP[c][0], "weights": CLASS_MAP[c][1], "label": "us-calibrated-adaptation",
                           "basis": txt("Mortgage to residential, consumer to credit cards and other consumer, commercial to C&I and CRE (decision Q6); the weights are fixtures")}
                          for c in CLASSES],
        "factor_space": {"window": {"start": FIT_START, "end": FIT_END},
                         "factors": [{"id": "real_gdp_growth", "label": txt("Real GDP growth", "Crecimiento del PIB real"), "unit": "percentage points", "sd": 2.1},
                                     {"id": "unemployment_rate", "label": txt("Unemployment rate", "Tasa de desempleo"), "unit": "percentage points", "sd": 1.5}],
                         "covariance": [[4.41, -1.89], [-1.89, 2.25]], "label": "us-calibrated-adaptation"},
        "aggregation": {
            "ladder": [{"method": "lower-bound", "engine_function": "aggregation.bounds.worst_var_bounds"},
                       {"method": "simple-sum", "engine_function": "aggregation.simple.simple_sum"},
                       {"method": "variance-covariance", "engine_function": "aggregation.simple.variance_covariance"},
                       {"method": "gaussian-copula", "engine_function": "aggregation.copulas.copula_aggregate"},
                       {"method": "t-copula", "engine_function": "aggregation.copulas.copula_aggregate"},
                       {"method": "worst-case", "engine_function": "aggregation.bounds.worst_var_bounds"}],
            "n_draws": 1_000_000, "seed": 18, "chunk_size": 100_000, "horizon_years": 1, "confidence_level": 0.999,
            "capital_basis": "economic-capital-var-less-el",
            "marginal_interpolation": "np.interp on the Hazen positions (i - 0.5) / n of the sorted sample, clamped at the ends",
            "quantile_grid": quantile_grid_fixture(),
        },
        "named_parameters": NAMED,
        "bank_anchors": {
            "rwa_basis": {"tier1_proxy_clp_m": CET1_0, "cet1_ratio_anchor": 0.11, "rwa_total_clp_m": RWA},
            "rwa_mix": MIX,
            "chilean_stack": {"cet1_min": 0.045, "c_ccob": STACK["c_ccob"], "c_ccyb": STACK["c_ccyb"], "c_dsib": STACK["c_dsib"], "p2r": STACK["p2r"], "p2_cap": 0.04},
            "loan_exposures": [{"banco_andino_class": c, "exposure_clp_m": EXPOSURE[c], "share": r10(EXPOSURE[c] / sum(EXPOSURE.values()))} for c in CLASSES],
            "source": txt("Ratios only, computed from the Banco Santander-Chile Form 20-F 2025 (SEC EDGAR), cited as the source; the absolute figures are not carried (decision Q4, E5)."),
            "licence_class": "derived-only", "ratios_only": True,
        },
        "marginal_sources": [
            {"risk": "credit", "producer": "credit-grouped-copula-c07-segments", "description": txt("The engine's grouped copula on the C07 segments of Banco Andino"), "documents": ["c07-outputs"], "c17_parameter_set": None},
            {"risk": "market", "producer": "market-c11-mixed-portfolio-scaled-to-market-rwa", "description": txt("C11's mixed-portfolio VaR and ES scaled to the market share of RWA"), "documents": ["c11-outputs mixed-2023"], "c17_parameter_set": None},
            {"risk": "irrbb", "producer": "irrbb-engine-simulation-c15-curve-and-book", "description": txt("The engine's EaR and EVaR simulation on C15's curve and book"), "documents": ["c15-outputs"], "c17_parameter_set": None},
            {"risk": "operational", "producer": "operational-oprisk-aggregate-c17-parameters-scaled",
             "description": txt("oprisk.aggregate on the C17 generator parameters scaled by assets and converted at the observed rate"), "documents": ["c17-models"],
             "c17_parameter_set": {"document": "C17 models-generator", "variant_id": "xi-1-1" if op_infinite else "xi-0-8",
                                   "tail_index": 1.1 if op_infinite else 0.8, "infinite_mean": op_infinite, "assets_eur_bn": 50.0}},
        ],
        "scenario_sources": [
            {"scenario_id": "baseline", "provider": "fed", "document": "2026_Final_Supervisory_Baseline_Domestic.csv", "url": "https://www.federalreserve.gov/supervisionreg/files/2026_Final_Supervisory_Baseline_Domestic.csv",
             "vintage_date": "2026-02-04", "licence_class": "mirror-allowed", "variables": []},
            {"scenario_id": "eba-2025-adverse", "provider": "eba-esrb", "document": scenario_block("eba")["source_document"], "url": scenario_block("eba")["source_url"],
             "vintage_date": "2025-02-26", "licence_class": "mirror-allowed", "variables": []},
            {"scenario_id": "fed-2026-severely-adverse", "provider": "fed", "document": "2026_Final_Supervisory_Severely_Adverse_Domestic.csv",
             "url": "https://www.federalreserve.gov/supervisionreg/files/2026_Final_Supervisory_Severely_Adverse_Domestic.csv", "vintage_date": "2026-02-04",
             "licence_class": "mirror-allowed", "variables": []},
            {"scenario_id": "ngfs-delayed-transition", "provider": "ngfs", "document": scenario_block("ngfs")["source_document"], "url": "https://data.ene.iiasa.ac.at/ngfs",
             "vintage_date": "2024-11-01", "licence_class": "derived-only",
             "variables": [{"name": n, "unit": NGFS_BASE[n][0]} for n in NGFS_BASE]},
        ],
        "capital_engine": {
            "balance_sheet": "static", "horizon_years": 3,
            "rules": [
                {"source": "EBA 2025 EU-wide stress test, Methodological Note, 2025-01-20", "paragraph": "24", "page": 16,
                 "statement": "The exercise is carried out on the basis of year-end 2024 figures, and the scenarios will be applied over a period of 3 years from 2025 to 2027."},
                {"source": "EBA 2025 EU-wide stress test, Methodological Note, 2025-01-20", "paragraph": "33", "page": 18,
                 "statement": "Static balance sheet: assets and liabilities that mature or amortise within the horizon are replaced with similar instruments; no workout or cure of S3 assets; no capital measures after the reference date."},
                {"source": "EBA 2025 EU-wide stress test, Methodological Note, 2025-01-20", "paragraph": "34", "page": 18,
                 "statement": "The same business mix and model throughout the horizon; revenues and costs under zero growth and a stable business mix."},
                {"source": "EBA 2025 EU-wide stress test, Methodological Note, 2025-01-20", "paragraph": "90", "page": 36,
                 "statement": "Banks are not permitted to replace S3 exposures; new S3 exposures move into the stock of S3, keeping the total exposure constant; no cures, charge-offs or write-offs within the 3-year horizon."},
                {"source": "EBA 2025 EU-wide stress test, Methodological Note, 2025-01-20", "paragraph": "91", "page": 36,
                 "statement": "The initial residual maturity is kept constant for credit REA."},
                {"source": "EBA 2025 EU-wide stress test, Methodological Note, 2025-01-20", "paragraph": "92", "page": 37,
                 "statement": "A constant balance sheet for impairments: replacement assets keep the credit risk characteristics and stage."},
            ],
            "reversion_quarters": 12.0,
        },
    }
    return {
        "schema": "contraste.models/v1", "case_id": "C18", "fit_id": "fixture-banco-andino",
        "model": [model_record(*m) for m in MODEL_IDS], "fit": fit, "provenance": provenance(), "lane": LANE,
    }


def main() -> None:
    for key in ("baseline", "eba", "fed", "ngfs"):
        write(f"variant-scenario-{SCEN_ID[key]}-fixture.json", scenario_doc(key))
    write("variant-aggregation-fixture.json", aggregation_doc())
    write("variant-reverse-fixture.json", reverse_doc())
    write("models-fixture.json", models_doc())


if __name__ == "__main__":
    main()
