"""The constants of the C17 bake: the LDCE calibration targets, the synthetic bank, the grid of cells, the engine settings and the
ladder, SMA and scenario descriptions the models document carries.

Nothing here is a result: every capital, quantile, fit, ILM and test is returned by ``riskvalidation`` (CT-1709). The LDCE
statistics are derived-only (BCBS 160, Table ILD7): the four medians the calibration uses, with their source, and no other cell of
the BCBS tables.
"""
from __future__ import annotations

from typing import Any

import numpy as np

GENERATOR = "operational-loss-history-generator"
CURRENCY = "EUR"
LEVEL = 0.999
TAIL_INDICES: tuple[float, ...] = (0.6, 0.8, 0.96, 1.1)
YEARS: tuple[int, ...] = (5, 10)
THRESHOLDS_EUR: tuple[int, ...] = (10_000, 20_000)
#: the cells in the fixed order of the contract (years, then threshold)
CELLS: tuple[tuple[int, int], ...] = tuple((y, h) for y in YEARS for h in THRESHOLDS_EUR)
FLOOR_EUR = 10_000.0  # the generator draws every loss at or above the lowest collection threshold
ASSETS_EUR_BN = 50.0
LDCE_FREQUENCY_PER_BN = 0.82
LDCE_THRESHOLD_EUR = 20_000.0
#: the four LDCE medians of per-bank severity percentiles above EUR 20,000 (BCBS 160, Table ILD7), derived-only
LDCE_PERCENTILES: tuple[tuple[float, float], ...] = ((0.25, 27_632.0), (0.5, 41_916.0), (0.75, 82_608.0), (0.95, 418_400.0))
#: the calibration is accepted when no fitted log excess quantile is off by more than this (the scale is the only free parameter: a tail
#: index of 0.6 cannot reach the heavy 95th percentile of the LDCE medians, whose own fit has a tail index of 0.96, so its error is the largest)
CALIBRATION_TOLERANCE_LOG = 0.5

N_REPLICATIONS = 1000
SEED_STRIDE = 1000
#: the case seed multiplies into the first seed so that two case seeds never share a history
SEED_SCALE = 100_000

#: the engine settings of the aggregation (the models document states them)
PANJER_STEP_EUR = 1000.0  # the truth grid
TRUTH_FFT_POINTS_MAX = 1 << 22
MC_YEARS_TRUTH = 10_000_000
MC_YEARS_REPLICATION = 200_000
MC_TRUTH_SEED = 17
MC_CHUNK_YEARS = 50_000
REPLICATION_GRID_POINTS = 4096  # Panjer/FFT points of one replication; the step follows the SLA scale of the fit
FFT_PADDING = 2
SPLICE_THRESHOLD_EUR = 100_000.0  # the splice threshold of rung 3 and the tail threshold of the scenario rung (a policy parameter of the caller)
STABILITY_MULTIPLES: tuple[float, ...] = (1.0, 2.0, 4.0, 8.0)  # the tail-index profile thresholds, as multiples of the collection threshold
N_BOOTSTRAP = 100  # the scenario prior's parametric bootstrap (the engine default is 1000)
PRIOR_SEEDS = 100  # the bootstrap seed is the first of 0 .. PRIOR_SEEDS - 1 whose refits all lie inside the search bounds of the engine
SCENARIO_CELL = "y10-h20000"
RESPONSE_CELL = "y10-h20000"
#: the SMA response: a single loss added to the latest year, as multiples of the BIC
RESPONSE_MULTIPLES: tuple[float, ...] = (0.0, 0.1, 0.25, 0.5, 1.0)
EXCEEDANCE_POINTS = 14

#: the stated, synthetic business indicator of the bank: three years of components in EUR, passed through the engine's OPE25 functions
BANK: dict[str, Any] = {
    "ii": [1.5e9, 1.5e9, 1.5e9], "ie": [0.8e9, 0.8e9, 0.8e9], "iea": [45e9, 45e9, 45e9], "di": [0.1e9, 0.1e9, 0.1e9],
    "ooi": [0.1e9, 0.1e9, 0.1e9], "ooe": [0.08e9, 0.08e9, 0.08e9], "fi": [0.4e9, 0.4e9, 0.4e9], "fe": [0.3e9, 0.3e9, 0.3e9],
    "pl_tb": [0.06e9, -0.04e9, 0.05e9], "pl_bb": [-0.05e9, 0.05e9, 0.05e9],
}

#: the scenario points: the loss is the true severity quantile of the exceedance frequency, rounded to two significant figures (an
#: expert gives round numbers). The frequencies are the expected events a year at or above the loss; eight points between four a year
#: and one in two and a half years keep every point at or above two events over five years (the engine refuses fewer than one)
#: and condition the least squares fit of the tail well enough for the bootstrap refits to stay inside the search bounds.
SCENARIOS: tuple[dict[str, Any], ...] = (
    {"scenario_id": "S1", "kind": "percentile", "frequency": 4.0, "label": {"en": "Loss four times a year", "es": "Pérdida cuatro veces al año"}},
    {"scenario_id": "S2", "kind": "percentile", "frequency": 3.0, "label": {"en": "Loss three times a year", "es": "Pérdida tres veces al año"}},
    {"scenario_id": "S3", "kind": "percentile", "frequency": 2.0, "label": {"en": "Loss twice a year", "es": "Pérdida dos veces al año"}},
    {"scenario_id": "S4", "kind": "percentile", "frequency": 1.5, "label": {"en": "Loss three times in two years", "es": "Pérdida tres veces cada dos años"}},
    {"scenario_id": "S5", "kind": "percentile", "frequency": 1.0, "label": {"en": "Loss once a year", "es": "Pérdida una vez al año"}},
    {"scenario_id": "S6", "kind": "individual", "frequency": 0.75,
     "label": {"en": "Named event: outage of the core platform", "es": "Evento nombrado: caída de la plataforma central"}},
    {"scenario_id": "S7", "kind": "percentile", "frequency": 0.5, "label": {"en": "Loss once in two years", "es": "Pérdida una vez cada dos años"}},
    {"scenario_id": "S8", "kind": "individual", "frequency": 0.4,
     "label": {"en": "Named event: large external fraud", "es": "Evento nombrado: fraude externo grande"}},
)

#: Basel level 1 event types and the Basel II business lines the generator labels each loss with (contract 1, loss_events)
EVENT_TYPES: tuple[str, ...] = (
    "internal_fraud", "external_fraud", "employment_practices_and_workplace_safety", "clients_products_and_business_practices",
    "damage_to_physical_assets", "business_disruption_and_system_failures", "execution_delivery_and_process_management")
EVENT_WEIGHTS = np.array([0.04, 0.30, 0.03, 0.20, 0.02, 0.06, 0.35])
BUSINESS_LINES: tuple[str, ...] = (
    "corporate_finance", "trading_and_sales", "retail_banking", "commercial_banking", "payment_and_settlement", "agency_services",
    "asset_management", "retail_brokerage")
LINE_WEIGHTS = np.array([0.02, 0.08, 0.40, 0.18, 0.12, 0.06, 0.06, 0.08])
FIRST_YEAR = 2014  # the first accounting year of every history

LDCE_TARGETS: dict[str, Any] = {'currency': 'EUR',
 'label': 'derived-only',
 'licence_class': 'derived-only',
 'source': {'id': 'bcbs160',
            'title': 'Results from the 2008 Loss Data Collection Exercise for Operational Risk',
            'url': 'https://www.bis.org/publ/bcbs160.htm',
            'date': '2009-07-28',
            'table': 'ILD7'},
 'threshold_eur': 20000,
 'frequency': {'per_eur_bn_assets': 0.82,
               'iqr_low': 0.36,
               'iqr_high': 1.66,
               'statistic': 'median across banks of the losses of EUR 20,000 or more per year per EUR billion of consolidated assets'},
 'severity_percentiles': [{'p': 0.25, 'loss_eur': 27632},
                          {'p': 0.5, 'loss_eur': 41916},
                          {'p': 0.75, 'loss_eur': 82608},
                          {'p': 0.95, 'loss_eur': 418400}],
 'caveat': {'en': 'Medians of per-bank percentiles are not the percentiles of any one bank; the statistics calibrate a synthetic bank and '
                  'describe no real one.',
            'es': 'Las medianas de percentiles por banco no son los percentiles de ningun banco; las estadisticas calibran un banco '
                  'sintetico y no describen a uno real.'}}

LADDER: list[dict[str, Any]] = [{'rung_id': 'lda-lognormal',
  'label': {'en': 'Poisson-lognormal LDA ignoring the collection threshold', 'es': 'El LDA Poisson-lognormal que ignora el umbral'},
  'severity_law': 'lognormal',
  'truncated': False,
  'aggregation': 'monte-carlo',
  'status': 'verified',
  'reference': 'dossier 05 F.2, rung 1'},
 {'rung_id': 'lda-lognormal-truncated',
  'label': {'en': 'Truncated lognormal above the threshold, frequency rescaled', 'es': 'Lognormal truncada sobre el umbral'},
  'severity_law': 'lognormal-truncated',
  'truncated': True,
  'aggregation': 'panjer',
  'status': 'verified',
  'reference': 'dossier 05 F.2, rung 2; Mignola and Ugoccioni (2007)'},
 {'rung_id': 'lda-splice',
  'label': {'en': 'Lognormal body and GPD tail splice', 'es': 'Empalme de cuerpo lognormal y cola GPD'},
  'severity_law': 'lognormal-gpd-splice',
  'truncated': True,
  'aggregation': 'fft',
  'status': 'verified',
  'reference': 'dossier 05 F.2, rung 3'},
 {'rung_id': 'sla',
  'label': {'en': 'Single loss approximation', 'es': 'Aproximacion de una perdida'},
  'severity_law': 'gpd',
  'truncated': True,
  'aggregation': 'closed-form',
  'status': 'verified',
  'reference': 'dossier 05 F.4, Shevchenko eq. 70'},
 {'rung_id': 'sla-mean-corrected',
  'label': {'en': 'Single loss approximation with the mean correction', 'es': 'Aproximacion de una perdida con correccion por media'},
  'severity_law': 'gpd',
  'truncated': True,
  'aggregation': 'closed-form',
  'status': 'UNVERIFIED',
  'reference': 'dossier 05 F.4: the form is not checked against Bocker and Sprittulla (2006) or Degen (2010)'},
 {'rung_id': 'scenario',
  'label': {'en': 'Scenario combination by Bayesian credibility', 'es': 'Combinacion de escenarios por credibilidad bayesiana'},
  'severity_law': 'lognormal-gpd-splice',
  'truncated': True,
  'aggregation': 'panjer',
  'status': 'verified',
  'reference': 'dossier 05 F.5, Shevchenko and Wuthrich (2006)'}]

SMA_SPEC: dict[str, Any] = {'currency': 'EUR',
 'buckets': [{'bucket': 1, 'upper_eur': 1000000000.0, 'coefficient': 0.12},
             {'bucket': 2, 'upper_eur': 30000000000.0, 'coefficient': 0.15},
             {'bucket': 3, 'upper_eur': None, 'coefficient': 0.18}],
 'loss_multiple': 15,
 'loss_window_years': 10,
 'minimum_years': 5,
 'ilm_exponent': 0.8,
 'rwa_factor': 12.5,
 'discretions': [{'id': 'bucket-1-ilm-one',
                  'description': {'en': 'Bucket 1 banks have ILM = 1 unless national discretion includes their losses.',
                                  'es': 'Los bancos del tramo 1 tienen ILM = 1 salvo que la discrecion nacional incluya sus perdidas.'},
                  'reference': 'OPE25.11'},
                 {'id': 'national-ilm-one',
                  'description': {'en': 'Supervisors may set ILM = 1 for every bank of the jurisdiction; disclosure stays.',
                                  'es': 'Los supervisores pueden fijar ILM = 1 para todos los bancos de la jurisdiccion; la divulgacion se '
                                        'mantiene.'},
                  'reference': 'OPE25.11'},
                 {'id': 'transitional-bic-only',
                  'description': {'en': 'Under 5 years of loss data (10 are required, 5 are the transitional minimum) capital is the BIC '
                                        'only.',
                                  'es': 'Con menos de 5 anos de datos de perdida (se piden 10, 5 es el minimo transitorio) el capital es '
                                        'solo el BIC.'},
                  'reference': 'OPE25.10, OPE25.15'}],
 'golden': {'bi_eur': 35000000000.0, 'bic_eur': 5370000000.0, 'reference': 'OPE25.7 footnote 2'},
 'reference': 'dossier 01 section F (OPE25, in force 2023-01-01, published 2024-07-05)'}

SCENARIO_SPEC: dict[str, Any] = {'methods': ['pseudo-observations', 'body-tail', 'bayesian-credibility'],
 'prior': {'kind': 'unrestricted-gamma-on-pareto-shape',
           'restricted': False,
           'interval_level': 0.9,
           'mapping': 'GPD fitted to the scenario points by least squares on the log excess quantiles; alpha_s = 1 / xi_s is the prior '
                      'mean and the parametric-bootstrap 90 percent interval of alpha_s the expert interval; the Gamma shape and rate '
                      'solve the mean and the interval mass (decision D4); the scenario frequencies are redrawn as Poisson over the years of '
                      'the history (decision D6); the bootstrap seed is the first of 0 to 99 whose 100 refits all lie inside the search '
                      'bounds of the engine'},
 'reference': 'dossier 05 F.5; Shevchenko and Wuthrich (2006), J. Operational Risk 1(3):3-26'}
