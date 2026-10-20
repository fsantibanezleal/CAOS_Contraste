// The run-time descriptors of the C12 documents (the outputs of a swap-exposure variant and the fit of the models
// artifact), one key per key of the c12-outputs and c12-models 1.0.0 schemas; contract.test.ts reads every committed
// document and the schema files against them in both directions. `satisfies` ties the top-level keys to the generated
// types, so a key added to a schema and not here fails `tsc`. Kept beside the instrument that reads them;
// contract.types.ts composes the variant and models descriptors from these (`variantKind`, `modelsKind`), the
// integrator's lines for the case.
import type { components } from '../../lib/contract.gen';
import type { Kind } from '../../lib/contract.types';

// A tuple of constants that mixes integers and decimals (the GIRR tenors) and a delta that is 1 or -1 are declared 'json'
// as well. A node the schema composes by a rule (a oneOf on a const: the ORE reconciliation that is either a reconciled block or a
// not-applicable one with its reason, a convention whose value is a number, a text or a list) is declared 'json': the
// schema test compares its branches, and the typed interface of contract.gen.ts reads it. Every other node is described
// key by key.

const MONEY: Kind = { object: { amount: 'number', currency: 'string' } };
const MONEY_SE: Kind = { object: { amount: 'number', currency: 'string', mc_se: 'number' } };
const PROFILE: Kind = { object: { currency: 'string', values: { array: 'number' }, mc_se: { array: 'number' } } };
const NUMS: Kind = { array: 'number' };

const SIGN: Kind = { object: { ee: 'string', ene: 'string', cva: 'string', dva: 'string', statement: 'text' } };

const UNITS: Kind = { object: { money: 'string', rate: 'string', compounding: 'string', time: 'string', mpor: 'string', dates: 'string' } };

const CONVENTION: Kind = { object: { value: 'json', unit: 'string', label: 'string' } };

const NAMED_PARAMETERS: Kind = { object: {
  notionals: CONVENTION,
  maturities_years: CONVENTION,
  sides: CONVENTION,
  netting_set_members: CONVENTION,
  single_swap_member: CONVENTION,
  fixed_rate_rule: CONVENTION,
  csa_threshold: CONVENTION,
  csa_minimum_transfer_amount: CONVENTION,
  csa_independent_amount: CONVENTION,
  mpor_business_days_short: CONVENTION,
  mpor_business_days_long: CONVENTION,
  counterparty_spread: CONVENTION,
  counterparty_lgd: CONVENTION,
  bank_spread: CONVENTION,
  bank_lgd: CONVENTION,
  pfe_quantile: CONVENTION,
  path_count: CONVENTION,
  seed: CONVENTION,
  time_grid_years: CONVENTION,
  wwr_b_grid: CONVENTION,
  im_quantile: CONVENTION,
  im_horizon_calendar_days: CONVENTION,
  im_mpor_calendar_days: CONVENTION,
  im_regression_order: CONVENTION,
  ba_cva_sector: CONVENTION,
  ba_cva_rating: CONVENTION,
  stress_window_start: CONVENTION,
  stress_window_end: CONVENTION,
  backtest_window_start: CONVENTION,
  backtest_paths_per_date: CONVENTION,
  backtest_simulated_critical_count: CONVENTION,
  reconciliation_se_threshold: CONVENTION,
  ee_check_k_se: CONVENTION,
} };

const TRADE: Kind = { object: {
  trade_id: 'string',
  notional: MONEY,
  fixed_rate: 'number',
  side: 'string',
  start_years: 'number',
  maturity_years: 'number',
  fixed_frequency_per_year: 'integer',
  floating_leg: 'string',
  label: 'string',
} };

const BOOK: Kind = { object: { netting_set_id: 'string', currency: 'string', trades: { array: TRADE } } };

const CURVE: Kind = { object: {
  curve_date: 'string',
  source: 'string',
  licence_class: 'string',
  par_yield_unit: 'string',
  zero_compounding: 'string',
  points: { array: { object: { tenor_years: 'number', par_yield: 'number', zero_rate: 'number' } } },
  tenors_present: NUMS,
  tenors_absent: NUMS,
  interpolated_silently: 'boolean',
} };

const CALIBRATION: Kind = { object: {
  backtest_date: 'string',
  model: 'string',
  estimator: 'string',
  proxy_tenor_years: 'number',
  sample_start: 'string',
  sample_end: 'string',
  n_obs: 'integer',
  history_years: 'number',
  a: 'number',
  sigma: 'number',
  a_se: 'number',
  sigma_se: 'number',
  fit_to_curve: 'string',
} };

const EXPOSURE: Kind = { object: {
  basis: 'string',
  time_grid_years: NUMS,
  ee: PROFILE,
  ee_discounted: PROFILE,
  ene: PROFILE,
  ene_discounted: PROFILE,
  pfe_quantile: 'number',
  pfe: PROFILE,
  effective_ee: PROFILE,
  epe: MONEY_SE,
  eepe: MONEY_SE,
  eepe_horizon_years: 'number',
  measure_note: 'text',
} };

const NETTING_BENEFIT: Kind = { object: {
  per_trade_ee: { array: { object: { trade_id: 'string', ee: PROFILE } } },
  sum_of_single_trade_ee: PROFILE,
  netted_ee: PROFILE,
  benefit: PROFILE,
} };

const CSA: Kind = { object: {
  threshold: MONEY,
  minimum_transfer_amount: MONEY,
  independent_amount: MONEY,
  mpor_business_days: 'integer',
  remargining_days: 'integer',
  closeout: 'string',
  floor_reference: 'string',
} };

const COLLATERAL: Kind = { nullable: { object: { csa: CSA, uncollateralised_ee: PROFILE, collateral_balance: PROFILE, limit: 'text' } } };

const IM: Kind = { nullable: { object: {
  method: 'string',
  labelled: 'string',
  simm_used: 'boolean',
  quantile: 'number',
  alpha: 'number',
  horizon_calendar_days: 'integer',
  mpor_calendar_days: 'integer',
  regression_order: 'integer',
  dim: PROFILE,
  ee_vm_only: PROFILE,
  limit: 'text',
} } };

const CVA_BUCKET: Kind = { object: {
  t_start: 'number',
  t_end: 'number',
  spread: 'number',
  survival: 'number',
  pd_counterparty: 'number',
  pd_bank: 'number',
  epe_discounted: 'number',
  ene_discounted: 'number',
  cva_term: 'number',
  dva_term: 'number',
} };

const CVA: Kind = { object: {
  credit_curve_source: 'string',
  credit_curve_label: 'string',
  survival_formula: 'string',
  negative_spread_rule: 'string',
  spreads_floored_at_zero: 'integer',
  lgd: 'number',
  bank_lgd: 'number',
  buckets: { array: CVA_BUCKET },
  cva: MONEY_SE,
  dva: MONEY_SE,
  bcva: MONEY,
} };

const WWR: Kind = { nullable: { object: {
  model: 'string',
  b_unit: 'string',
  b_grid: NUMS,
  w_max_usd_million: 'number',
  largest_b_w: 'number',
  sweep: { array: { object: { b: 'number', cva: MONEY_SE, independent: 'boolean', a_calibration_max_error: 'number' } } },
  independent_cva: MONEY,
  ore_limit: 'text',
} } };

const SA_TRADE: Kind = { object: {
  trade_id: 'string',
  hedging_set: 'string',
  start_years: 'number',
  end_years: 'number',
  notional: MONEY,
  supervisory_duration: 'number',
  adjusted_notional: MONEY,
  delta: 'json',
  maturity_factor: 'number',
  bucket: 'string',
  effective_notional: 'number',
} };

const SA_HEDGING_SET: Kind = { object: {
  hedging_set: 'string',
  d_b1: 'number',
  d_b2: 'number',
  d_b3: 'number',
  offset: 'boolean',
  effective_notional: 'number',
  supervisory_factor: 'number',
  addon: 'number',
} };

const SA_CCR: Kind = { object: {
  paragraph: 'string',
  in_force_date: 'string',
  margined: 'boolean',
  v: MONEY,
  c: MONEY,
  th: MONEY,
  mta: MONEY,
  nica: MONEY,
  mpor_business_days: { nullable: 'integer' },
  rc: MONEY,
  trades: { array: SA_TRADE },
  hedging_sets: { array: SA_HEDGING_SET },
  addon_by_class: { object: { interest_rate: 'number', fx: 'number', credit: 'number', equity: 'number', commodity: 'number' } },
  addon_aggregate: MONEY,
  multiplier_floor: 'number',
  multiplier: 'number',
  pfe: MONEY,
  alpha: 'number',
  ead: MONEY,
} };

const BA_CVA: Kind = { object: {
  paragraph: 'string',
  in_force_date: 'string',
  imm_bank: 'boolean',
  ds: 'number',
  rho: 'number',
  alpha: 'number',
  counterparties: { array: { object: {
    counterparty_id: 'string',
    sector: 'string',
    rating_class: 'string',
    risk_weight: 'number',
    ead: MONEY,
    m_years: 'number',
    discount_factor: 'number',
    scva: 'number',
  } } },
  k_reduced: 'number',
  capital: MONEY,
  limit: 'text',
} };

const REGULATORY: Kind = { object: {
  alpha: 'number',
  alpha_paragraph: 'string',
  effective_maturity_years: 'number',
  alpha_times_eepe: MONEY,
  sa_ccr_ead: MONEY,
  sa_ccr_over_alpha_eepe: 'number',
  stressed: { object: {
    window_start: 'string',
    window_end: 'string',
    label: 'string',
    effective_epe: MONEY,
    hqm_spread_start: 'number',
    hqm_spread_peak: 'number',
    spread_rose: 'boolean',
    paragraph: 'string',
  } },
} };

const GIRR: Kind = { object: {
  paragraph: 'string',
  in_force_date: 'string',
  currency: 'string',
  sqrt2_division: 'boolean',
  sqrt2_label: 'string',
  sensitivities: NUMS,
  weighted_sensitivities: NUMS,
  scenarios: { array: { object: { scenario: 'string', k_b: 'number' } } },
  delta_charge: MONEY,
  delta_charge_undivided: MONEY,
} };

const EXCEEDANCE: Kind = { object: { quantile: 'number', count: 'integer', expected: 'number' } };

const HORIZON: Kind = { object: {
  horizon: 'string',
  n: 'integer',
  pits: NUMS,
  exceedances: { array: EXCEEDANCE },
  w2: 'number',
  critical_iid: { object: { p05: 'number', p01: 'number' } },
  critical_simulated: { object: { p05: 'number', p01: 'number' } },
  effective_sample_size: 'number',
  reject_at_5pct: 'boolean',
} };

const BACKTEST: Kind = { object: {
  window_start: 'string',
  window_end: 'string',
  dates: { array: 'string' },
  calibration_rule: 'string',
  pit_rule: 'string',
  statistic: 'string',
  paths_per_date: 'integer',
  book_horizons: { array: HORIZON },
  risk_factor: { object: { proxy_tenor_years: 'number', horizons: { array: HORIZON } } },
  sub_windows: { array: { object: {
    window: 'string',
    start: 'string',
    end: 'string',
    results: { array: { object: { horizon: 'string', n: 'integer', w2: 'number' } } },
  } } },
} };

const SENSITIVITY: Kind = { object: {
  case: 'string',
  a: 'number',
  sigma: 'number',
  eepe: MONEY,
  pfe_peak: MONEY,
  ee: PROFILE,
  pfe: PROFILE,
} };

// The reconciliation is a reconciled block (every variant but the wrong-way one) or a not-applicable one with its reason.
const ORE: Kind = 'json';

export const C12_OUTPUTS = { object: {
  kind: 'string',
  variant: 'string',
  sign_convention: SIGN,
  units: UNITS,
  named_parameters: NAMED_PARAMETERS,
  book: BOOK,
  curve: CURVE,
  calibration_used: CALIBRATION,
  exposure: EXPOSURE,
  netting_benefit: NETTING_BENEFIT,
  collateral: COLLATERAL,
  initial_margin: IM,
  cva_dva: CVA,
  wrong_way_risk: WWR,
  sa_ccr: SA_CCR,
  ba_cva: BA_CVA,
  regulatory_comparison: REGULATORY,
  girr: GIRR,
  backtest: BACKTEST,
  calibration_sensitivity: { array: SENSITIVITY },
  ore_reconciliation: ORE,
} } satisfies { object: Record<keyof components['schemas']['c12Outputs'], Kind> };

const GIRR_PARAMETERS: Kind = { object: {
  paragraph: 'string',
  in_force_date: 'string',
  tenors_years: 'json',
  risk_weights: NUMS,
  correlation_percent: { array: NUMS },
  same_tenor_other_curve: 'number',
  gamma_between_buckets: 'number',
  curvature_shock: 'number',
  sqrt2_divisor: 'number',
  sqrt2_applies_to: 'string',
  vega: { object: { liquidity_horizon_days: 'integer', risk_weight: 'number', correlation_alpha: 'number', footnote_24_formula: 'string' } },
} };

const CREDIT_CURVE: Kind = { object: {
  base: 'string',
  label: 'string',
  derivation: 'text',
  source_url: 'string',
  licence_class: 'string',
  licence_basis: 'text',
  negative_spread_rule: 'string',
  synthetic_spread: CONVENTION,
} };

export const C12_FIT = { object: {
  estimator: 'string',
  calibrations: { array: CALIBRATION },
  min_history_years: 'integer',
  closed_forms_source: 'string',
  closed_forms_status: 'string',
  credit_curve: CREDIT_CURVE,
  girr_parameters: GIRR_PARAMETERS,
  limits: { array: 'text' },
} } satisfies { object: Record<keyof components['schemas']['c12Fit'], Kind> };
