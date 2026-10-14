// The run-time descriptors of the C17 documents (outputs of a tail-index variant, and the fit of the models artifact),
// one key per key of the c17-outputs and c17-models 1.0.0 schemas; contract.test.ts reads every committed document and
// the schema files against them in both directions. `satisfies` ties the keys to the generated types, so a key added to
// a schema and not here fails `tsc`. Kept beside the instrument that reads them; contract.types.ts composes the variant
// and models descriptors from these (`variantKind`, `modelsKind`), the integrator's lines for the case.
import type { components } from '../../lib/contract.gen';
import type { Kind } from '../../lib/contract.types';

// A node that the schema composes by a rule (a oneOf on a const: a mean present or absent with its reason, one of four
// transcribed percentile pairs, a rung id that fixes its status) is declared 'json': contract.test.ts compares the
// branches of the schema, and the typed interface of contract.gen.ts reads the node.
const num = 'number' as const;

/** Percentiles across the replications of a money quantity or a ratio: the five the contract carries, nondecreasing. */
const QUANTILES: Kind = { object: { p05: num, p25: num, median: num, p75: num, p95: num } };

/** The capital of one rung across the histories of a cell. `status` is the label the views print: UNVERIFIED stays. */
const CAPITAL: Kind = { object: {
  aggregation: 'string',
  status: 'string',
  n_defined: 'integer',
  capital_eur: QUANTILES,
  ratio_to_truth: QUANTILES,
  share_underestimating: num,
  iqr_over_truth: num,
  log_sd: num,
} };

/** A rung the bake may not have evaluated for a cell: the summary, or null with its reason. The schema composes it by a
 * rule (a oneOf on null: the summary or the reason, never both), so it is declared 'json' here and read through the typed
 * interface of contract.gen.ts, which the unit test checks against every committed document. */
const OPTIONAL_CAPITAL: Kind = 'json';

const STABILITY_ROW: Kind = { object: {
  threshold_eur: num,
  n_exceedances_median: num,
  n_fits: 'integer',
  tail_index: { object: { p05: num, median: num, p95: num } },
  share_at_least_one: num,
} };

const SMA_CELL: Kind = { object: {
  currency: 'string',
  basis: 'string',
  discretion_applied: 'string',
  bucket: 'integer',
  bic_eur: num,
  lc_eur: QUANTILES,
  ilm: QUANTILES,
  orc_eur: QUANTILES,
  orc_over_true_quantile: QUANTILES,
  note: 'text',
} };

const CELL: Kind = { object: {
  id: 'string',
  years: 'integer',
  collection_threshold_eur: num,
  currency: 'string',
  replications: { object: { seed_first: 'integer', n_replications: 'integer', n_failed: 'integer', n_losses_median: num } },
  capital: { object: {
    lda_lognormal: CAPITAL,
    lda_lognormal_truncated: CAPITAL,
    lda_splice: CAPITAL,
    sla: CAPITAL,
    sla_mean_corrected: OPTIONAL_CAPITAL,
    scenario: OPTIONAL_CAPITAL,
  } },
  aggregation_agreement: { object: { max_rel_diff_panjer_fft: num, n_compared: 'integer' } },
  threshold_stability: { array: STABILITY_ROW },
  sma: SMA_CELL,
} };

/** The BCBS 2008 LDCE targets with their source and the derived-only label. Shared by the outputs and the fit. */
const LDCE: Kind = { object: {
  currency: 'string',
  label: 'string',
  licence_class: 'string',
  source: { object: { id: 'string', title: 'string', url: 'string', date: 'string', table: 'string' } },
  threshold_eur: num,
  frequency: { object: { per_eur_bn_assets: num, iqr_low: num, iqr_high: num, statistic: 'string' } },
  severity_percentiles: { array: 'json' },
  caveat: 'text',
} };

export const C17_OUTPUTS: Kind = { object: {
  kind: 'string',
  currency: 'string',
  tail_index: num,
  infinite_mean: 'boolean',
  truth: { object: {
    label: 'string',
    currency: 'string',
    frequency: { object: { law: 'string', lambda_per_year: num, counted_above_eur: num } },
    severity: { object: { law: 'string', location_eur: num, scale_eur: num, tail_index: num } },
    annual_loss_quantile: { object: {
      level: num,
      value_eur: num,
      method: 'string',
      grid_step_eur: num,
      mc_check: { object: { n_years: 'integer', seed: 'integer', value_eur: num, standard_error_eur: num, agrees: 'boolean' } },
    } },
    annual_loss_mean: 'json',
    notice: 'text',
  } },
  calibration: { object: {
    targets: LDCE,
    fit: { object: { tail_index: num, scale_eur: num, fitted_quantiles_eur: { array: num }, max_abs_log_error: num, method: 'string' } },
  } },
  bank: { object: {
    currency: 'string',
    synthetic: 'boolean',
    label: 'text',
    assets_eur: num,
    business_indicator: { object: { ildc_eur: num, sc_eur: num, fc_eur: num, bi_eur: num } },
    bic_eur: num,
    bucket: 'integer',
    notice: 'text',
  } },
  cells: { array: CELL },
  exceedance: { object: {
    currency: 'string',
    grid_eur: { array: num },
    monte_carlo: { object: { n_years: 'integer', seed: 'integer', exceedance: { array: num } } },
    panjer: { object: { step_eur: num, exceedance: { array: num } } },
    fft: { object: { n_points: 'integer', padding_factor: 'integer', tilt: num, exceedance: { array: num } } },
    quantile_999_eur: { object: { monte_carlo: num, panjer: num, fft: num, sla: num } },
  } },
  sma_response: { object: {
    currency: 'string',
    cell_id: 'string',
    seed: 'integer',
    bic_eur: num,
    rows: { array: { object: { added_loss_eur: num, lc_eur: num, ilm: num, orc_eur: num, lda_capital_eur: num } } },
  } },
  scenario_influence: { object: {
    prior_kind: 'string',
    currency: 'string',
    cell_id: 'string',
    seed: 'integer',
    level: num,
    method: 'string',
    base_capital_eur: num,
    scenarios: { array: { object: {
      scenario_id: 'string',
      label: 'text',
      kind: 'string',
      loss_eur: num,
      exceedance_frequency_per_year: num,
      capital_without_eur: num,
      influence: num,
    } } },
    reference: 'string',
  } },
} } satisfies { object: Record<keyof components['schemas']['c17Outputs'], Kind> };

export const C17_FIT: Kind = { object: {
  currency: 'string',
  generator: { object: {
    name: 'string',
    shaped_on: 'string',
    assets_eur_bn: num,
    frequency_law: 'string',
    severity_law: 'string',
    generator_floor_eur: num,
    notice: 'text',
  } },
  calibration: LDCE,
  variants: { array: 'json' },
  grid: { object: {
    years: 'json',
    collection_thresholds_eur: 'json',
    n_replications_per_cell: 'integer',
    seed_base: 'integer',
    seed_stride: 'integer',
  } },
  ladder: { array: 'json' },
  aggregation: { object: {
    level: num,
    panjer_step_eur: num,
    panjer_points: 'integer',
    fft_points: 'integer',
    fft_padding_factor: 'integer',
    fft_tilt: num,
    mc_years_truth: 'integer',
    mc_years_replication: 'integer',
  } },
  sma: { object: {
    currency: 'string',
    buckets: { array: 'json' },
    loss_multiple: 'integer',
    loss_window_years: 'integer',
    minimum_years: 'integer',
    ilm_exponent: num,
    rwa_factor: num,
    discretions: { array: { object: { id: 'string', description: 'text', reference: 'string' } } },
    golden: { object: { bi_eur: num, bic_eur: num, reference: 'string' } },
    reference: 'string',
  } },
  scenarios: { object: {
    methods: { array: 'string' },
    prior: { object: { kind: 'string', restricted: 'boolean', interval_level: num, mapping: 'string' } },
    reference: 'string',
  } },
} } satisfies { object: Record<keyof components['schemas']['c17Fit'], Kind> };
