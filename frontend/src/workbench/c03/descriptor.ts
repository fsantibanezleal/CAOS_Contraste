// The run-time descriptors of the C03 documents (outputs of a vintage-cohort variant, and the fit of the models artifact),
// one key per key of the c03-outputs and c03-models 1.0.0 schemas; contract.test.ts reads every committed document and
// the schema files against them in both directions. `satisfies` ties the keys to the generated types, so a key added to
// a schema and not here fails `tsc`. Kept beside the instrument that reads them; contract.types.ts composes the variant
// and models descriptors from these (`variantKind`, `modelsKind`), the integrator's lines for the case.
import type { components } from '../../lib/contract.gen';
import type { Kind } from '../../lib/contract.types';

// A row or a block that the schema composes by a rule (a oneOf on a const: observed or not, in range or flagged) is
// declared 'json': the schema test compares its branches, and the typed interface of contract.gen.ts reads it.

const TRAINING: Kind = { object: {
  first_fy: 'integer',
  last_fy: 'integer',
  cutoff_date: 'string',
  n_loans: 'integer',
  n_events: 'integer',
  crisis_included: 'boolean',
  rationale: 'text',
} };

const TARGET: Kind = { object: {
  name: 'string',
  horizon_months: 'integer',
  observed_at_months: 'integer',
  censoring: 'string',
  definition: 'text',
} };

const DATA_STATUS: Kind = { object: {
  primary_source: 'string',
  files_as_of: 'string',
  fiscal_year_start: 'string',
  notice: 'text',
} };

// BS-15 (unit D15): the e-process of a cohort under one combination of its vintages
const SEQ_PATH: Kind = { object: {
  log_e: { array: { nullable: 'number' } },
  rejection_month: { nullable: 'integer' },
  anytime_p_value: 'number',
  max_log_e: 'number',
} };

export const C03_OUTPUTS: Kind = { object: {
  kind: 'string',
  currency: 'string',
  cohort: { object: {
    id: 'string',
    label: 'text',
    first_fy: 'integer',
    last_fy: 'integer',
    approval_fiscal_years: { array: 'integer' },
  } },
  training: TRAINING,
  target: TARGET,
  data_status: DATA_STATUS,
  vintage_curves: { array: 'json' },
  vintage_summary: { object: {
    currency: 'string',
    rows: { array: 'json' },
  } },
  calibration: { object: {
    rung_id: 'string',
    scope: 'text',
    rows: { array: { object: {
      decile: 'integer',
      n: 'integer',
      predicted_pd: 'number',
      observed_pd: 'number',
      ci_low: 'number',
      ci_high: 'number',
    } } },
  } },
  rung_comparison: { array: { object: {
    rung_id: 'string',
    auc: { nullable: 'number' },
    auc_ci_low: { nullable: 'number' },
    auc_ci_high: { nullable: 'number' },
    brier: { nullable: 'number' },
    calibration_gap_5y: { nullable: 'number' },
    reason: { nullable: 'string' },
  } } },
  stability: { object: {
    training_mean_5y_pd: 'number',
    psi_note: 'text',
    rows: { array: { object: {
      fiscal_year: 'integer',
      psi: 'number',
      observed_5y_pd: { nullable: 'number' },
    } } },
  } },
  sequential: { object: {
    engine: 'string',
    engine_version: 'string',
    alpha_level: 'number',
    threshold: 'number',
    direction: 'string',
    headline: 'string',
    months: { array: 'integer' },
    vintages: { array: { object: {
      fiscal_year: 'integer',
      n: 'integer',
      months_observed: 'integer',
      defaults: 'integer',
      predicted_defaults: 'number',
      rejection_month: { nullable: 'integer' },
      max_log_e: { nullable: 'number' },
      log_e: { array: { nullable: 'number' } },
      five_year_light: { nullable: 'string' },
      months_before_the_mark: { nullable: 'integer' },
    } } },
    average: SEQ_PATH,
    product: SEQ_PATH,
    reading: 'text',
    limits: 'text',
  } },
} } satisfies { object: Record<keyof components['schemas']['c03Outputs'], Kind> };

export const C03_FIT: Kind = { object: {
  currency: 'string',
  vintage_definition: { object: {
    basis: 'string',
    fiscal_year_start: 'string',
    label: 'text',
  } },
  target: TARGET,
  cohort_windows: { array: { object: {
    id: 'string',
    label: 'text',
    first_fy: 'integer',
    last_fy: 'integer',
    training: TRAINING,
  } } },
  ladder: { array: { object: {
    rung_id: 'string',
    kind: 'string',
    covariates: { array: 'string' },
    coefficients: { array: { object: {
      name: 'string',
      estimate: 'number',
      std_error: { nullable: 'number' },
    } } },
    training_cutoff: 'string',
    engine: 'string',
  } } },
  data_status: DATA_STATUS,
} } satisfies { object: Record<keyof components['schemas']['c03Fit'], Kind> };
