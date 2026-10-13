// The run-time descriptors of the C08 documents (outputs of a default-cohort variant, and the fit of the models artifact),
// one key per key of the c08-outputs and c08-models 1.0.0 schemas; contract.test.ts reads every committed document and
// the schema files against them in both directions. `satisfies` ties the keys to the generated types, so a key added to
// a schema and not here fails `tsc`. Kept beside the instrument that reads them; contract.types.ts composes the variant
// and models descriptors from these (`variantKind`, `modelsKind`), the integrator's lines for the case.
import type { components } from '../../lib/contract.gen';
import type { Kind } from '../../lib/contract.types';

// A row or a block that the schema composes by a rule (a oneOf on a const: observed or not, in range or flagged) is
// declared 'json': the schema test compares its branches, and the typed interface of contract.gen.ts reads it.

/** A loss given default: the value as it is and its flag (a value outside [0, 1] is flagged, never clipped). */
const LGD: Kind = { anyOf: [{ object: { value: 'number', flag: 'string' } }] };

/** A predicted loss: always inside [0, 1], so its flag is the one value. */
const LGD_PREDICTION: Kind = { object: { value: 'number', flag: 'string' } };

const PROXY: Kind = { object: {
  definition: 'text',
  formula: 'string',
  source_field: 'string',
  exposure_field: 'string',
  recovery_cash_flows_available: 'boolean',
  bias_direction: 'string',
  bias_statement: 'text',
} };

const DATA_STATUS: Kind = 'json';

const TRAINING: Kind = { object: {
  cutoff_date: 'string',
  n_defaults: 'integer',
  n_open_workouts_excluded: 'integer',
  closure_rule: 'text',
} };

const WORKOUT: Kind = 'json';

const COHORT: Kind = { object: {
  id: 'string',
  label: 'text',
  first_year: 'integer',
  last_year: 'integer',
} };

const PERIOD: Kind = { object: {
  first_year: 'integer',
  last_year: 'integer',
  indicator: 'string',
  macro_source: 'string',
} };

export const C08_OUTPUTS: Kind = { object: {
  kind: 'string',
  currency: 'string',
  cohort: COHORT,
  lgd_proxy: PROXY,
  data_status: DATA_STATUS,
  training: TRAINING,
  workout: WORKOUT,
  exposure: { object: {
    currency: 'string',
    gross_charge_off_total: 'number',
    gross_approval_total: 'number',
  } },
  lgd_distribution: { object: {
    n: 'integer',
    treatment: 'string',
    bins: { array: { object: {
      lower: 'number',
      upper: 'number',
      n: 'integer',
      share: 'number',
    } } },
    mass_at_zero: { object: { n: 'integer', share: 'number' } },
    mass_at_one: { object: { n: 'integer', share: 'number' } },
    n_below_zero: 'integer',
    share_below_zero: 'number',
    n_above_one: 'integer',
    share_above_one: 'number',
    lowest: LGD,
    highest: LGD,
    mean: LGD,
    median: LGD,
  } },
  rung_comparison: { array: { object: {
    rung_id: 'string',
    r2: { nullable: 'number' },
    rmse: 'number',
    mae: 'number',
    spearman: { nullable: 'number' },
    calibration_gap: 'number',
    reason: { nullable: 'string' },
  } } },
  realised_vs_predicted: { array: { object: {
    rung_id: 'string',
    cohort_id: 'string',
    n: 'integer',
    realised: LGD,
    predicted: LGD_PREDICTION,
    ci_low: 'number',
    ci_high: 'number',
    gap: 'number',
  } } },
  calibration_by_bucket: { array: { object: {
    rung_id: 'string',
    bucket: 'integer',
    n: 'integer',
    predicted: LGD_PREDICTION,
    realised: LGD,
  } } },
  endpoint_sensitivity: { array: { object: {
    rung_id: 'string',
    epsilon: 'number',
    mean_predicted: LGD_PREDICTION,
    rmse: 'number',
  } } },
  downturn: { object: {
    period: PERIOD,
    approach: 'text',
    rows: { array: { object: {
      cohort_id: 'string',
      n: 'integer',
      long_run_lgd: LGD,
      downturn_lgd: LGD,
      add_on: 'number',
      crisis_realised_lgd: LGD,
      covered: 'boolean',
      shortfall: 'number',
    } } },
    coverage: { object: { n_cohorts: 'integer', share_covered: 'number' } },
  } },
  floors_bite: { object: {
    regime: 'string',
    rows: { array: 'json' },
    note: 'text',
  } },
} } satisfies { object: Record<keyof components['schemas']['c08Outputs'], Kind> };

export const C08_FIT: Kind = { object: {
  currency: 'string',
  lgd_proxy: PROXY,
  data_status: DATA_STATUS,
  cohorts: { array: COHORT },
  training: TRAINING,
  workout: WORKOUT,
  ladder: { array: { object: {
    rung_id: 'string',
    kind: 'string',
    covariates: { array: 'string' },
    coefficients: { array: { object: {
      name: 'string',
      estimate: 'number',
      std_error: { nullable: 'number' },
    } } },
    epsilon: { nullable: 'number' },
    training_cutoff: 'string',
    library: 'string',
    library_version: 'string',
  } } },
  downturn: { object: { approach: 'text', period: PERIOD } },
  floors: { object: {
    regime: 'string',
    cells: { array: 'json' },
    source: 'string',
  } },
} } satisfies { object: Record<keyof components['schemas']['c08Fit'], Kind> };
