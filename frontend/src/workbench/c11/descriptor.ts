// The run-time descriptors of the C11 documents (outputs of a window variant, and the fit of the models artifact), one
// key per key of the c11-outputs and c11-models 1.0.0 schemas; contract.test.ts reads every committed document and the
// schema files against them in both directions. `satisfies` ties the keys to the generated types, so a key added to a
// schema and not here fails `tsc`. Kept beside the instrument that reads them; contract.types.ts composes the variant
// and models descriptors from these (`variantKind`, `modelsKind`), the integrator's lines for the case.
import type { components } from '../../lib/contract.gen';
import type { Kind } from '../../lib/contract.types';

const SIGN_CONVENTION: Kind = { object: {
  engine_convention: 'string',
  document_convention: 'string',
  definition: 'json',
} };

const LEVEL: Kind = { object: { alpha: 'number' } };

const SPAN: Kind = { object: { start: 'string', end: 'string' } };

// A block that the schema composes by a rule (a oneOf on a const: one window id with its dates, a level result with its
// zone and coupled fields, a champion with or without a reason, a Diebold-Mariano row evaluated or not) is declared
// 'json': the schema test compares the keys of the rest, and the typed interfaces of contract.gen.ts read these.

const MCS_SET: Kind = { object: {
  alpha: 'number',
  loss: 'string',
  statistic: 'string',
  confidence: 'number',
  n_bootstrap: 'integer',
  block_length: 'integer',
  members: { array: { object: { model_id: 'string', in_set: 'boolean', p_value: 'number' } } },
  n_in_set: 'integer',
} };

const ES_NULL: Kind = { object: {
  model_id: 'string',
  alpha: 'number',
  statistic: 'string',
  realised: 'number',
  critical_5pct: 'number',
  critical_0_01pct: 'number',
  n_draws: 'integer',
  p_value: 'number',
  histogram: { object: { edges: { array: 'number' }, counts: { array: 'integer' } } },
} };

export const C11_OUTPUTS: Kind = { object: {
  kind: 'string',
  window: 'json',
  sign_convention: SIGN_CONVENTION,
  levels: { array: LEVEL },
  portfolio: { object: {
    description: 'text',
    value_unit: 'string',
    currency: 'string',
    weighting: 'string',
    components: { array: { object: {
      series_id: 'string',
      label: 'text',
      source_class: 'string',
      weight: 'number',
      transform: 'string',
    } } },
  } },
  data_status: { object: {
    first_observation: 'string',
    last_observation: 'string',
    n_observed_days: 'integer',
    missing_days: { object: { count: 'integer', dates: { array: 'string' }, treatment: 'string' } },
  } },
  grid: { object: {
    scheme: 'string',
    estimation_window_days: 'integer',
    dates: { array: 'string' },
    estimation_start: { array: 'string' },
    estimation_end: { array: 'string' },
    realised_loss: 'json',
  } },
  hyperparameters: { object: {
    fixed_on: SPAN,
    tuned_on_test_window: 'boolean',
    estimation_window_days: 'integer',
    ewma_lambda: 'number',
    age_weight_lambda: 'number',
    evt_threshold_fraction: 'number',
    garch_refit_every_days: 'integer',
    caviar_n_starts: 'integer',
    gas_n_starts: 'integer',
    seed: 'integer',
    others: { array: { object: { name: 'string', value: 'number', unit: 'string' } } },
  } },
  models: { array: { object: {
    model_id: 'string',
    rung: 'string',
    eligible: 'boolean',
    failed_gates: { array: 'string' },
    by_level: { array: 'json' },
  } } },
  comparison: { object: {
    significance: 'number',
    hac_kernel: 'string',
    hac_lags: 'integer',
    champions: { array: 'json' },
    dm: { array: 'json' },
    mcs: { array: MCS_SET },
  } },
  es_backtests: { array: ES_NULL },
} } satisfies { object: Record<keyof components['schemas']['c11Outputs'], Kind> };

export const C11_FIT: Kind = { object: {
  sign_convention: SIGN_CONVENTION,
  levels: { array: LEVEL },
  windows: { array: 'json' },
  ladder: { array: 'json' },
  traffic_light: { object: {
    window_days: 'integer',
    confidence: 'number',
    reference: 'string',
    rows: { array: { object: {
      exceptions: 'integer',
      zone: 'string',
      frtb_multiplier: 'number',
      us_multiplier: 'number',
      cumulative_probability_pct: 'number',
    } } },
  } },
  es_reference: { object: {
    statistic: 'string',
    n_days: 'integer',
    alpha: 'number',
    yellow: 'number',
    red: 'number',
    status: 'text',
  } },
  scoring: { object: {
    fz0_formula: 'string',
    tick_formula: 'string',
    hac_kernel: 'string',
    mcs_confidence: 'number',
    mcs_statistic: 'string',
    selection_rule: 'text',
  } },
  eligibility_gates: { array: { object: { test_id: 'string', rule: 'text' } } },
  data_sources: { array: { object: {
    series_id: 'string',
    title: 'text',
    source_class: 'string',
    url: 'string',
    licence_note: 'text',
  } } },
} } satisfies { object: Record<keyof components['schemas']['c11Fit'], Kind> };
