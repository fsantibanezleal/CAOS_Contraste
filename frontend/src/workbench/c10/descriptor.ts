// The run-time descriptors of the C10 documents (outputs of a loan-type variant, outputs of a correlation-grid variant,
// and the fit of the models artifact), one key per key of the c10-outputs, c10-outputs-grid and c10-models 1.0.0
// schemas; contract.test.ts reads every committed document and the schema files against them in both directions.
// `satisfies` ties the keys to the generated types, so a key added to a schema and not here fails `tsc`. Kept beside
// the instrument that reads them; contract.types.ts composes the variant and models descriptors from these
// (`variantKind`, `modelsKind`), the integrator's lines for the case.
import type { components } from '../../lib/contract.gen';
import type { Kind } from '../../lib/contract.types';

// A row that the schema composes by a rule (a oneOf on a null and a value: a year with or without a rate, a rung that ran
// or did not, a retail class with or without a maturity) is declared 'json': the schema test compares its branches, and
// the typed interface of contract.gen.ts reads it, as the U6 descriptors do for their partial-key rows.

const WINDOWS: Kind = { object: {
  fit: { object: { first_year: 'integer', last_year: 'integer', n_years: 'integer' } },
  evaluation: { object: { first_year: 'integer', last_year: 'integer', n_years: 'integer' } },
} };

const PD_INTERVAL: Kind = { object: { estimate: 'number', ci_low: 'number', ci_high: 'number' } };

const GROUP: Kind = { object: {
  id: 'string',
  label: 'text',
  n_names: 'integer',
  ead_each: 'number',
  pd: 'number',
  lgd: 'number',
  loading: 'number',
  sector: 'string',
} };

const LEVELS: Kind = 'json';

const ANNUAL_RATE: Kind = 'json';
const RUNG: Kind = 'json';
const EULER_LEVEL: Kind = 'json';
const IRB_REFERENCE: Kind = 'json';
const GA_ROW: Kind = 'json';
const RUNG_SPEC: Kind = 'json';

export const C10_OUTPUTS_LOAN_TYPE: Kind = { object: {
  kind: 'string',
  loan_type: 'string',
  label: 'text',
  currency: 'string',
  loss_rate_definition: 'text',
  windows: WINDOWS,
  data_status: { object: {
    source: 'string',
    table: 'string',
    series: 'string',
    seasonal_adjustment: 'string',
    bank_scope: 'string',
    files_as_of: 'string',
    quarters_expected: 'integer',
    missing_quarters: { array: { object: { quarter: 'string', reason: 'string' } } },
    notice: 'text',
  } },
  annual_rates: { array: ANNUAL_RATE },
  fit: { object: {
    n_years_used: 'integer',
    maximum_likelihood: { object: {
      pd: PD_INTERVAL,
      rho: PD_INTERVAL,
      log_likelihood: 'number',
      converged: 'boolean',
      interval_method: 'string',
      level: 'number',
    } },
    moments: { object: {
      pd: PD_INTERVAL,
      rho: PD_INTERVAL,
      interval_method: 'string',
      n_bootstrap: 'integer',
      level: 'number',
    } },
  } },
  profile_likelihood: { object: {
    level: 'number',
    rho: { array: 'number' },
    log_likelihood: { array: 'number' },
    pd_at_rho: { array: 'number' },
    max_log_likelihood: 'number',
    cutoff: 'number',
  } },
  fitted_distribution: { object: {
    pd: 'number',
    rho: 'number',
    curve: { object: { x: { array: 'number' }, pdf: { array: 'number' }, cdf: { array: 'number' } } },
    quantiles: { array: { object: { level: 'number', value: 'number' } } },
  } },
  backtest: { object: {
    n_years_evaluated: 'integer',
    rows: { array: { object: {
      level: 'number',
      fitted_quantile: 'number',
      expected_exceedances: 'number',
      observed_exceedances: 'integer',
      years_exceeding: { array: 'integer' },
      p_value_upper: 'number',
      light: 'string',
    } } },
  } },
  irb_reference: IRB_REFERENCE,
  portfolio: { object: {
    label: 'string',
    notice: 'text',
    currency: 'string',
    n_names: 'integer',
    total_ead: 'number',
    groups: { array: GROUP },
    lgd_mean: 'number',
    lgd_gamma: 'number',
    levels: LEVELS,
    horizon_years: 'integer',
    calibration: { object: { pd: 'number', rho: 'number', source: 'string' } },
    hhi: 'number',
    effective_names: 'number',
    largest_share: 'number',
  } },
  rungs: { array: RUNG },
  granularity: { object: {
    currency: 'string',
    xi: 'number',
    gamma: 'number',
    k_source: 'string',
    k_star: 'number',
    delta_reference: 'number',
    delta_reference_source: 'string',
    levels: { array: { object: { q: 'number', alpha_q: 'number', delta: 'number', ga: 'number', ga_money: 'number' } } },
    by_n_names_level: 'number',
    by_n_names: { array: GA_ROW },
  } },
  euler: { array: { object: {
    rung_method: 'string',
    currency: 'string',
    levels: { array: EULER_LEVEL },
  } } },
} } satisfies { object: Record<keyof components['schemas']['c10LoanTypeOutputs'], Kind> };

export const C10_OUTPUTS_GRID: Kind = { object: {
  kind: 'string',
  label: 'text',
  generator: { object: {
    name: 'string',
    shaped_on: 'string',
    known_pd: 'number',
    rho_grid: { array: 'number' },
    series_length_years: 'integer',
    n_replications: 'integer',
    null_rho: 'number',
    alpha: 'number',
    seed: 'integer',
    notice: 'text',
  } },
  size_power_definition: 'text',
  cells: { array: { object: {
    known_rho: 'number',
    series_length_years: 'integer',
    n_replications: 'integer',
    n_valid: 'integer',
    n_failed: 'integer',
    role: 'string',
    estimators: { array: { object: {
      estimator: 'string',
      mean_estimate: 'number',
      bias: 'number',
      rmse: 'number',
      coverage: 'number',
      rejection_rate: 'number',
      rejection_se: 'number',
      rejection_ci_low: 'number',
      rejection_ci_high: 'number',
    } } },
  } } },
} } satisfies { object: Record<keyof components['schemas']['c10GridOutputs'], Kind> };

export const C10_FIT: Kind = { object: {
  currency: 'string',
  windows: WINDOWS,
  loan_types: { array: { object: {
    id: 'string',
    label: 'text',
    table_column: 'string',
    irb_asset_class: 'string',
    irb_reference: 'string',
  } } },
  estimators: { array: { object: {
    id: 'string',
    label: 'text',
    engine_function: 'string',
    interval_method: 'string',
    reference: 'string',
  } } },
  ladder: { array: RUNG_SPEC },
  portfolio_spec: { object: {
    label: 'string',
    notice: 'text',
    currency: 'string',
    groups: { array: GROUP },
    lgd_mean: 'number',
    lgd_gamma: 'number',
    levels: LEVELS,
    horizon_years: 'integer',
  } },
  granularity: { object: {
    xi: 'number',
    gamma: 'number',
    k_source: 'string',
    xi_reference: 'number',
    q_reference: 'number',
    delta_reference: 'number',
    reference: 'string',
  } },
  simulator: { object: {
    known_pd: 'number',
    rho_grid: { array: 'number' },
    series_lengths_years: { array: 'integer' },
    n_replications: 'integer',
    null_rho: 'number',
    alpha: 'number',
    seed: 'integer',
  } },
} } satisfies { object: Record<keyof components['schemas']['c10ModelsFit'], Kind> };
