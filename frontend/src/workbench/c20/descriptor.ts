// The run-time descriptors of the C20 documents: the outputs of the five kinds of variant (SGCD shocks, shift probes,
// seed sweep, perturbation grid, planted leak) and the fit of the models artifact, one key per key of the c20-outputs,
// c20-outputs-shift, c20-outputs-seeds, c20-outputs-perturbation, c20-outputs-leakage and c20-models 1.0.0 schemas;
// contract.test.ts reads every committed document and the schema files against them in both directions. `satisfies`
// ties the top-level keys to the generated types, so a key added to a schema and not here fails `tsc`. Kept beside the
// instrument that reads them; contract.types.ts composes the variant and models descriptors from these (`variantKind`,
// `modelsKind`), the integrator's lines for the case. A node the schema composes by a rule (the named parameters' value,
// a null model) is declared `json`.
import type { components } from '../../lib/contract.gen';
import type { Kind } from '../../lib/contract.types';
import { PARAMS } from '../c02/descriptor';

const SGCD_NOTICE: Kind = { object: { kind: 'string', quote: 'string', commit: 'string', text: 'text' } };

const FAIR_ROW: Kind = { object: {
  test_id: 'string',
  attribute: 'string',
  value: { nullable: 'number' },
  groups: { array: { object: { group: 'string', n: 'integer', value: { nullable: 'number' } } } },
  light: 'string',
} };

const FAIR_BATTERY: Kind = { object: { label: 'string', model: 'string', notice: 'text', rows: { array: FAIR_ROW } } };

const IMPACT: Kind = { object: {
  label: 'string',
  cutoff: { object: { rule: 'string', reject_share: 'number', label: 'string' } },
  rows: { array: { object: { shift_id: 'string', flip_share: 'number', n_decisions: 'integer' } } },
} };

const METRIC: Kind = { object: { auc: 'number', brier: 'number', auc_delta: 'number' } };

const DRIFT: Kind = { object: {
  psi_max: 'number',
  csi_max: 'number',
  chi2_p_value: { nullable: 'number' },
  variables: { array: { object: { name: 'string', psi: 'number', csi: 'number', chi2_p_value: { nullable: 'number' } } } },
} };

const SHOCK_ROW: Kind = { object: {
  shock_id: 'string',
  batches: { array: 'string' },
  n_records: 'integer',
  n_reaching_structured_view: 'integer',
  performance: METRIC,
  drift: DRIFT,
  data_quality: { object: { completeness: 'number', consistency: { nullable: 'number' } } },
  attribution_rank_correlation: { nullable: 'number' },
} };

/** The keys every kind of variant shares, before its own. */
const COMMON = {
  dataset_id: 'string',
  model_dataset: 'string',
  sgcd_notice: { nullable: SGCD_NOTICE },
  parameters: PARAMS,
  fairness_battery: { nullable: FAIR_BATTERY },
  impact_detail: IMPACT,
  requirements: { array: 'string' },
} satisfies Record<string, Kind>;

export const C20_OUTPUTS = { object: {
  kind: 'string',
  ...COMMON,
  seen_or_held_out: 'string',
  model_view: 'string',
  shipped: { object: { label: 'string', rows: { array: SHOCK_ROW }, parameters_source: { nullable: 'json' } } },
  applied: { object: { label: 'string', rows: { array: SHOCK_ROW }, parameters_source: 'string' } },
} } satisfies { object: Record<keyof components['schemas']['c20Outputs'], Kind> };

const CONFORMAL: Kind = { object: {
  label: 'string',
  alpha: 'number',
  target_coverage: 'number',
  coverage: 'number',
  binomial_p_value: 'number',
  coverage_by_window: { array: { object: { window: 'string', n: 'integer', coverage: 'number', binomial_p_value: 'number' } } },
} };

const CBPE: Kind = { object: {
  label: 'string',
  estimated_auc: 'number',
  assumptions: { array: { object: { id: 'string', text: 'text' } } },
} };

export const C20_OUTPUTS_SHIFT = { object: {
  kind: 'string',
  ...COMMON,
  real_drift: { object: {
    label: 'string',
    model: { nullable: 'json' },
    portfolios: { array: 'string' },
    pairs: { array: { object: {
      a: 'string',
      b: 'string',
      variables: { array: { object: { name: 'string', psi: 'number', csi: 'number', ks: 'number', chi2_p_value: { nullable: 'number' } } } },
    } } },
  } },
  synthetic_shift: { object: {
    label: 'string',
    reference_portfolio: 'string',
    evaluation_set: 'string',
    shifts: { array: { object: { shift_id: 'string', score: 'number', metric: METRIC, psi: 'number', flip_share: 'number' } } },
    worst_subsample: { object: { share: 'number', metric: METRIC } },
    label_free: { object: { conformal: CONFORMAL, cbpe: CBPE } },
  } },
} } satisfies { object: Record<keyof components['schemas']['c20OutputsShift'], Kind> };

const ALE: Kind = { object: { edges: { array: 'number' }, effect: { array: 'number' } } };

export const C20_OUTPUTS_SEEDS = { object: {
  kind: 'string',
  ...COMMON,
  rows: { array: { object: {
    rung: 'string',
    n_seeds: 'integer',
    auc: { object: { mean: 'number', sd: 'number', min: 'number', max: 'number' } },
    grade_assignment_changed_share: 'number',
    attribution_rank_tau: { object: { mean: 'number', min: 'number' } },
    reason_code_overlap: { object: { top_k: 'integer', n_refits: 'integer', mean: 'number', p05: 'number' } },
  } } },
  explainer_agreement: { array: { object: {
    rung: 'string',
    effect_reference: 'string',
    n_features: 'integer',
    rank_correlation: { nullable: 'number' },
    reason_if_null: { nullable: 'string' },
    top_features: { array: { object: { feature: 'string', shap_importance: 'number', effect_range: 'number', ale: ALE } } },
  } } },
} } satisfies { object: Record<keyof components['schemas']['c20OutputsSeeds'], Kind> };

export const C20_OUTPUTS_PERTURBATION = { object: {
  kind: 'string',
  ...COMMON,
  preset_eps: 'number',
  rows: { array: { object: { eps: 'number', metric: METRIC, finding: 'boolean' } } },
} } satisfies { object: Record<keyof components['schemas']['c20OutputsPerturbation'], Kind> };

const THRESHOLD: Kind = { object: { value: 'number', label: 'string' } };

export const C20_OUTPUTS_LEAKAGE = { object: {
  kind: 'string',
  ...COMMON,
  planted_feature: 'string',
  thresholds: { object: { single_feature_auc: THRESHOLD, resemblance_auc: THRESHOLD } },
  screen: { object: {
    temporal_order: { object: { violations: 'integer' } },
    single_feature_auc: { object: { max_auc: 'number', feature: 'string', suspect: 'boolean' } },
    entity_overlap: { object: { share: 'number' } },
    resemblance_auc: 'number',
  } },
  caught: 'boolean',
  performance: { object: { development_auc: 'number', decision_time_auc: 'number' } },
} } satisfies { object: Record<keyof components['schemas']['c20OutputsLeakage'], Kind> };

export const C20_FIT = { object: {
  datasets: { array: { object: { id: 'string', rows: 'integer', role: 'string' } } },
  ladder: { array: { object: { rung: 'string', engine: 'string', dataset: 'string' } } },
  sgcd: { object: { commit: 'string', seed: 'integer', notice: SGCD_NOTICE } },
  parameters: PARAMS,
} } satisfies { object: Record<keyof components['schemas']['c20Fit'], Kind> };
