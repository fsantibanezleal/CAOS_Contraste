// The run-time descriptors of the C02 documents (outputs of a horizon variant, and the fit of the models artifact), one
// key per key of the c02-outputs 1.1.0 and c02-models 1.0.0 schemas; contract.test.ts reads every committed document and the
// schema files against them in both directions. `satisfies` ties the top-level keys to the generated types, so a key
// added to a schema and not here fails `tsc`. Kept beside the instrument that reads them; contract.types.ts composes the
// variant and models descriptors from these (`variantKind`, `modelsKind`), the integrator's lines for the case. The
// named-parameter node is exported: C20 declares the same one.
import type { components } from '../../lib/contract.gen';
import type { Kind } from '../../lib/contract.types';

/** A named parameter: its value (a number, a list of numbers or a name, so the node is `json`), unit, label and basis. */
export const PARAM: Kind = { object: {
  name: 'string',
  value: 'json',
  unit: 'string',
  label: 'string',
  basis: 'string',
} };

export const PARAMS: Kind = { array: PARAM };

const CI: Kind = { object: { lo: 'number', hi: 'number', level: 'number', method: 'string' } };

const COUNTS: Kind = { object: {
  rows: 'integer',
  events: 'integer',
  event_rate: 'number',
  features: 'integer',
  event_definition: 'text',
} };

const POOL_FILE: Kind = { object: { file: 'string', years: 'integer', rows: 'integer', events: 'integer' } };

const POOLED: Kind = { object: { files: { array: POOL_FILE }, horizon_indicator: 'boolean', overlap: 'text' } };

export const SPLIT: Kind = { object: {
  protocol: 'string',
  seed: 'integer',
  train_rows: 'integer',
  calibration_rows: 'integer',
  holdout_rows: 'integer',
  holdout_events: 'integer',
  fit_on_training_slice_only: 'boolean',
  calibration_map_on_separate_slice: 'boolean',
  resampling_before_calibration: 'boolean',
  out_of_time_claim: 'boolean',
} };

const RUNG: Kind = { object: {
  model_id: 'string',
  rung: 'string',
  roc: { object: { fpr: { array: 'number' }, tpr: { array: 'number' } } },
  cap: { object: { population: { array: 'number' }, defaults: { array: 'number' }, default_rate: 'number' } },
  reliability: { array: { object: { n: 'integer', pd: 'number', dr: 'number', lo: 'number', hi: 'number' } } },
  discrimination: { object: { auc: 'number', auc_ci: CI, gini: 'number', ks: 'number' } },
  calibration: { object: {
    brier: 'number',
    ece: 'number',
    hosmer_lemeshow: { object: { statistic: 'number', df: 'integer', p_value: 'number' } },
  } },
  overfit: { object: { train_auc: 'number', holdout_auc: 'number', gap: 'number', tolerance: 'number', flag: 'boolean' } },
  stability: { object: { psi: 'number', csi_max: 'number' } },
} };

const CHALLENGER: Kind = { object: {
  champion: 'string',
  challenger: 'string',
  auc_diff: 'number',
  auc_diff_ci: CI,
  delong_p_value: 'number',
  brier_diff: 'number',
  brier_diff_ci: { object: { lo: 'number', hi: 'number', level: 'number', method: 'string' } },
  grade_disagreement_share: 'number',
} };

const TRANSFER: Kind = { object: {
  label: 'string',
  reason: 'text',
  cells: { array: { object: { rung: 'string', model_id: 'string', fitted_on_years: 'integer', scored_on_years: 'integer', auc: 'number', n: 'integer', events: 'integer' } } },
} };

const TERM: Kind = { object: {
  label: 'string',
  reason: 'text',
  points: { array: { object: { years: 'integer', cumulative_pd: 'number', hazard: 'number' } } },
  cumulative_nondecreasing: 'boolean',
  source: 'string',
} };

const IMPACT: Kind = { object: {
  label: 'string',
  reason: 'text',
  source: 'string',
  pd_basis: 'text',
  lgd: { object: { value: 'number', label: 'string' } },
  ecl_12m_effect: { nullable: 'number' },
  ecl_lifetime_effect: { nullable: 'number' },
  unit: 'text',
  reason_if_null: { nullable: 'text' },
} };

export const C02_OUTPUTS = { object: {
  kind: 'string',
  horizon_id: 'string',
  years: { nullable: 'integer' },
  counts: COUNTS,
  pooled: { nullable: POOLED },
  firm_overlap_caveat: { nullable: 'text' },
  split: SPLIT,
  rungs: { array: RUNG },
  challenger: { array: CHALLENGER },
  transfer: TRANSFER,
  term_structure: { nullable: TERM },
  term_structure_reason: { nullable: 'text' },
  impact_detail: IMPACT,
  parameters: PARAMS,
  requirements: { array: 'string' },
} } satisfies { object: Record<keyof components['schemas']['c02Outputs'], Kind> };

export const C02_FIT = { object: {
  files: { array: { object: { horizon_id: 'string', years: 'integer', file: 'string', rows: 'integer', events: 'integer' } } },
  ladder: { array: { object: { rung: 'string', label: 'text', engine: 'string', reference: 'string' } } },
  protocol: SPLIT,
  parameters: PARAMS,
} } satisfies { object: Record<keyof components['schemas']['c02Fit'], Kind> };
