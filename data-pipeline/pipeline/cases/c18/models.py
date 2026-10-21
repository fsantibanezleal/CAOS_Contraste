"""The C18 models document (``c18-models``): the satellite fits, the factor space, the aggregation parameters, the bank anchors, the
scenario sources, the capital-engine rules and every named parameter, each with its value, basis and label (convention or case
assumption). Nothing is a result of the scenarios; it is what the scenario documents echo (``semantics.cross_violations``)."""
from __future__ import annotations

from typing import Any

from . import fetch
from . import ngfs as ngfs_reader
from . import params as P
from . import satellites as sat
from .anchors import Anchors

T = P.text
UNITS = {"money": "CLP millions", "ratio": "decimal", "dates": "ISO date; quarters as the date of the quarter end"}
BANK_NOTICE = T("Banco Andino is a synthetic bank. Its book and capital are calibrated to public aggregates (the CMF system aggregates of August 2026, "
                "the Banco Santander-Chile Form 20-F 2025 as ratios only); the satellites are fitted on United States data and applied to it, a "
                "US-calibrated adaptation; every figure is a result of the stated method and no claim about a real bank.")
EBA_NOTE = "EBA 2025 EU-wide stress test, Methodological Note, 2025-01-20"
EBA_RULES = (
    ("24", 16, "The exercise is carried out on the basis of year-end 2024 figures, and the scenarios will be applied over a period of 3 years from 2025 to 2027."),
    ("33", 18, "Static balance sheet: assets and liabilities that mature or amortise within the horizon are replaced with similar instruments; no workout or "
               "cure of S3 assets; no capital measures after the reference date."),
    ("34", 18, "The same business mix and model throughout the horizon; revenues and costs under zero growth and a stable business mix."),
    ("90", 36, "Banks are not permitted to replace S3 exposures; new S3 exposures move into the stock of S3, keeping the total exposure constant; no cures, "
               "charge-offs or write-offs within the 3-year horizon."),
    ("91", 36, "The initial residual maturity is kept constant for credit REA."),
    ("92", 37, "A constant balance sheet for impairments: replacement assets keep the credit risk characteristics and stage."),
)


def named(name: str, value: float, unit: str, label: str, basis: str, basis_es: str | None = None) -> dict[str, Any]:
    return {"name": name, "value": value, "unit": unit, "label": label, "basis": T(basis, basis_es)}


def named_parameters(anchors: Anchors, fx: Any, op_extras: dict[str, Any], mk_scaling: dict[str, float]) -> dict[str, dict[str, Any]]:
    """Every named parameter of the case; the derived ones (the rate, the asset scaling, the market scaling) from their stated sources."""
    lf, hf = mk_scaling["level_factor"], mk_scaling["horizon_factor"]
    corr_basis = "Rosenberg and Schuermann benchmark: market-credit 0.5, market and credit with operational 0.2 (05 l.360); IRRBB is treated as a market-type risk "
    corr_basis_es = "referencia de Rosenberg y Schuermann: mercado-crédito 0,5, mercado y crédito con operacional 0,2 (05 l.360); el IRRBB se trata como un riesgo de tipo mercado "
    return {
        "nu_set": {"name": "nu_set", "values": list(P.NU_SET), "unit": "degrees of freedom", "label": "convention",
                   "basis": T("Degrees of freedom of the t copula: 4, 8 and 30 (30 approaches the Gaussian copula); a convention of the case, G.5 asks for several nu (05 l.378)")},
        "correlation_matrix_base": {"name": "correlation_matrix_base", "order": P.CORR_ORDER, "matrix": P.CORR_BASE, "unit": "correlation", "label": "convention",
                                    "basis": T("The " + corr_basis + "(0.5 with credit and market, 0.2 with operational): UNVERIFIED, no dossier gives an IRRBB correlation; "
                                               "the dependence band shows what it changes (decision T2)",
                                               "La " + corr_basis_es + "(0,5 con crédito y mercado, 0,2 con operacional): NO VERIFICADO, ningún dossier da una correlación del IRRBB; "
                                               "la banda de dependencia muestra lo que cambia (decisión T2)")},
        "correlation_matrix_stress": {"name": "correlation_matrix_stress", "order": P.CORR_ORDER, "matrix": P.CORR_STRESS, "unit": "correlation",
                                      "label": "convention", "basis": T("The base matrix with market-credit raised to 0.8, the upper end of the published ranges (05 l.378)",
                                                   "La matriz base con mercado-crédito elevada a 0,8, el extremo superior de los rangos publicados (05 l.378)")},
        "ppnr_fee_ratio": named("ppnr_fee_ratio", P.PPNR_FEE, "fee income over NII", "case assumption",
                                "A stated constant ratio of the PPNR row (decision Q10, T3); not a Banco Andino or CMF figure"),
        "ppnr_cost_ratio": named("ppnr_cost_ratio", P.PPNR_COST, "operating cost over (NII + fee income)", "case assumption",
                                 "A stated constant cost-to-income ratio of the PPNR row (decision Q10, T3)"),
        "c_p2": named("c_p2", P.C_P2, "share of RWA", "case assumption",
                      "The bank's own capital for risks outside Pillar 1, at least the art. 66 quinquies requirement (03 l.152-169, decision Q4); the 4 percent cap "
                      "binds the requirement p2r, never this estimate (decision W3)"),
        "c_d": named("c_d", P.C_D, "share of RWA", "case assumption", "The voluntary stress buffer, component d of the internal target (03 l.152-169, decision Q4)"),
        "operational_conversion_rate": {
            **named("operational_conversion_rate", fx.value, "CLP per EUR", "case assumption",
                    "Derived at bake time: the observed EUR to CLP rate of the as-of date from the Banco Central de Chile (decision Q5, W5)"),
            "derivation": {"kind": "observed-exchange-rate", "pair": "EUR/CLP", "observation_date": fx.observation_date,
                           "source": "Banco Central de Chile, Base de Datos Estadísticos, daily exchange rate of the euro in Chilean pesos",
                           "source_url": "https://si3.bcentral.cl/Siete/es/Siete/API", "source_series": fx.series_id}},
        "asset_scaling": {
            **named("asset_scaling", op_extras["asset_scaling"], "Banco Andino assets over the assets of the C17 bank", "case assumption",
                    "Derived at bake time: Banco Andino's total assets (the C15 Tier 1 proxy over its equity-over-assets calibration target) over the C17 synthetic "
                    "bank's stated assets, converted at the rate (decision Q5, W5)"),
            "derivation": {"kind": "asset-ratio", "banco_andino_assets_clp_m": anchors.total_assets_clp_m,
                           "c17_bank_assets_eur_m": anchors.c17_generator["assets_eur_bn"] * 1000.0, "converted_at": "operational_conversion_rate"}},
        "market_rwa_share": named("market_rwa_share", anchors.rwa_mix["market"], "share of RWA", "case assumption",
                                  "The market share of the 20-F RWA mix, as a ratio (decision Q5, Q4); C11's mixed-portfolio VaR and ES are scaled to the market "
                                  "RWA it gives, taken as the position value"),
        "market_horizon_scaling": {
            **named("market_horizon_scaling", mk_scaling["value"], "multiplier on C11's 99 percent one-day measure", "convention",
                    "From C11's 99 percent one-day figures to 99.9 percent and one year: the normal quantile ratio z_0.999 / z_0.99 times the square root of 250, "
                    "both named conventions (W4)",
                    "Desde las cifras a un día al 99 por ciento de C11 hasta 99,9 por ciento y un año: la razón de cuantiles normales z_0,999 / z_0,99 por la raíz cuadrada de 250, "
                    "ambas convenciones nombradas (W4)"),
            "source_confidence_level": P.SOURCE_LEVEL, "source_horizon_days": 1, "trading_days_per_year": P.TRADING_DAYS,
            "level_factor": named("market_level_factor", lf, "ratio of normal quantiles z_0.999 / z_0.99", "convention",
                                  "The normal quantile ratio that moves C11's 99 percent measure to 99.9 percent: a convention of the case",
                                  "La razón de cuantiles normales que lleva la medida de C11 de 99 por ciento a 99,9 por ciento: una convención del caso"),
            "horizon_factor": named("market_horizon_factor", hf, "multiplier on a one-day measure, sqrt(250)", "convention",
                                    "Square-root-of-time scaling from one day to one year with 250 trading days: a convention of the case")},
        "reverse_p2_cet1": named("reverse_p2_cet1", P.REVERSE_P2_CET1, "share of RWA", "case assumption",
                                 "The CET1 share of the Pillar 2 requirement in the legal minimum stack (03 G.4: at most 4 percent in total, composition set bank by bank)"),
    }


def model_summaries(ev: str) -> list[dict[str, Any]]:
    def rec(mid: str, family: str, rung: str, en: str, es: str, params: dict[str, tuple[float, str]]) -> dict[str, Any]:
        return {"id": mid, "family": family, "rung": rung, "title": T(en, es), "short_title": T(en.split(",")[0], es.split(",")[0]), "engine": "riskvalidation",
                "engine_version": ev, "licence": "MIT", "calibration": None, "parameters": {k: {"value": v, "unit": u} for k, (v, u) in params.items()},
                "checkpoint_sha256": None}

    return [
        rec(sat.MODEL_ID, "stress", "satellite-probit-ols", "Macro satellites of the net charge-off rates, OLS on 1985 to 2019",
            "Satélites macro de las tasas de castigo netas, MCO sobre 1985 a 2019", {"ar_order": (float(P.AR_ORDER), "lags"), "fit_end_year": (2019.0, "year")}),
        rec("c18-aggregation-ladder", "aggregation", "simple-sum-headline", "Aggregation ladder, the simple sum as the headline",
            "Escalera de agregación, la suma simple como cifra principal", {"level": (P.LEVEL, "probability"), "horizon": (float(P.HORIZON_YEARS), "years")}),
        rec("c18-capital-engine", "stress", "capital-engine-static", "Capital engine on a static balance sheet",
            "Motor de capital sobre balance estático", {"horizon": (3.0, "years")}),
    ]


def fit_block(anchors: Anchors, sats: dict[str, sat.Satellite], space: dict[str, Any], named_p: dict[str, Any], credit_description: dict[str, str], n_draws: int = P.N_DRAWS,
              seed: int = P.SEED) -> dict[str, Any]:
    exp = [{"banco_andino_class": c, "exposure_clp_m": anchors.class_exposure_clp_m[c], "share": anchors.class_exposure_clp_m[c] / anchors.loans_clp_m}
           for c in P.CLASSES]
    return {
        "currency": "CLP", "units": UNITS, "bank": {"name": "Banco Andino", "synthetic": True, "as_of": P.AS_OF, "notice": BANK_NOTICE},
        "satellites": [sat.record(s) for s in sats.values()],
        "class_mapping": [{"banco_andino_class": c, "fed_loan_types": list(P.CLASS_MAP[c][0]), "weights": list(P.CLASS_MAP[c][1]), "label": "us-calibrated-adaptation",
                           "basis": T("Mortgage to residential, consumer to credit cards and other consumer, commercial to C&I and commercial real estate (decision Q6); "
                                      "the weights are the case's mapping of Banco Andino's classes to Fed loan types, an adaptation and no estimate")} for c in P.CLASSES],
        "factor_space": space,
        "aggregation": {
            "ladder": [{"method": "lower-bound", "engine_function": "aggregation.bounds.worst_var_bounds"},
                       {"method": "simple-sum", "engine_function": "aggregation.simple.simple_sum"},
                       {"method": "variance-covariance", "engine_function": "aggregation.simple.variance_covariance"},
                       {"method": "gaussian-copula", "engine_function": "aggregation.copulas.copula_aggregate"},
                       {"method": "t-copula", "engine_function": "aggregation.copulas.copula_aggregate"},
                       {"method": "worst-case", "engine_function": "aggregation.bounds.worst_var_bounds"}],
            "n_draws": n_draws, "seed": seed, "chunk_size": P.CHUNK, "horizon_years": P.HORIZON_YEARS, "confidence_level": P.LEVEL,
            "capital_basis": "economic-capital-var-less-el",
            "marginal_interpolation": "np.interp on the Hazen positions (i - 0.5) / n of the sorted sample, clamped at the ends"},
        "named_parameters": named_p,
        "bank_anchors": {
            "rwa_basis": {"tier1_proxy_clp_m": anchors.tier1_clp_m, "cet1_ratio_anchor": P.CMF_ANCHOR_CET1, "rwa_total_clp_m": anchors.rwa_clp_m},
            "rwa_mix": anchors.rwa_mix, "chilean_stack": anchors.stack, "loan_exposures": exp,
            "source": T("Ratios only, computed from the Banco Santander-Chile Form 20-F 2025 (SEC EDGAR), cited as the source; the absolute figures are not carried "
                        "(decision Q4, E5)."),
            "licence_class": "derived-only", "ratios_only": True},
        "marginal_sources": [
            {"risk": "credit", "producer": "credit-grouped-copula-c07-segments", "description": credit_description,
             "documents": ["c07-outputs"], "c17_parameter_set": None},
            {"risk": "market", "producer": "market-c11-mixed-portfolio-scaled-to-market-rwa",
             "description": T("C11's mixed-portfolio VaR and ES scaled to the market share of RWA"), "documents": ["c11-outputs mixed-2023"], "c17_parameter_set": None},
            {"risk": "irrbb", "producer": "irrbb-engine-simulation-c15-curve-and-book",
             "description": T("The engine's Hull-White simulation on C15's curve and book"), "documents": ["c15-outputs"], "c17_parameter_set": None},
            {"risk": "operational", "producer": "operational-oprisk-aggregate-c17-parameters-scaled",
             "description": T("oprisk.aggregate on the C17 generator parameters scaled by assets and converted at the observed rate"), "documents": ["c17-models"],
             "c17_parameter_set": {"document": "C17 models-generator", "variant_id": anchors.c17["variant_id"], "tail_index": anchors.c17["tail_index"],
                                   "infinite_mean": bool(anchors.c17["infinite_mean"]), "assets_eur_bn": anchors.c17_generator["assets_eur_bn"]}}],
        "scenario_sources": [
            {"scenario_id": P.SCENARIOS["baseline"], "provider": "fed", "document": "2026_Final_Supervisory_Baseline_Domestic.csv",
             "url": "https://www.federalreserve.gov/supervisionreg/files/2026_Final_Supervisory_Baseline_Domestic.csv", "vintage_date": "2026-02-04",
             "licence_class": "mirror-allowed", "variables": []},
            {"scenario_id": P.SCENARIOS["eba"], "provider": "eba-esrb",
             "document": "2025 EU-wide stress test - Macro financial scenario (updated 26 February 2025), United States rows", "url": fetch.EBA_URL,
             "vintage_date": fetch.EBA_VINTAGE, "licence_class": "mirror-allowed", "variables": []},
            {"scenario_id": P.SCENARIOS["fed"], "provider": "fed", "document": "2026_Final_Supervisory_Severely_Adverse_Domestic.csv",
             "url": "https://www.federalreserve.gov/supervisionreg/files/2026_Final_Supervisory_Severely_Adverse_Domestic.csv", "vintage_date": "2026-02-04",
             "licence_class": "mirror-allowed", "variables": []},
            {"scenario_id": P.SCENARIOS["ngfs"], "provider": "ngfs",
             "document": "NGFS Phase V, NiGEM NGFS v1.24.2 runs, read through the IIASA Scenario Explorer (IXSE_NGFS_PHASE_5)", "url": fetch.NGFS_UI,
             "vintage_date": fetch.NGFS_VINTAGE, "licence_class": "derived-only", "variables": [{"name": n, "unit": u} for n, u, *_ in ngfs_reader.VARIABLES]}],
        "capital_engine": {"balance_sheet": "static", "horizon_years": 3, "rules": [{"source": EBA_NOTE, "paragraph": p, "page": pg, "statement": s}
                                                                                       for p, pg, s in EBA_RULES],
                           "reversion_quarters": float(P.REVERSION_QUARTERS)}}
