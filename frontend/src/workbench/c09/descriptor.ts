// The run-time descriptors of the C09 documents (outputs of an acceleration-level variant, and the fit of the models
// artifact), one key per key of the c09-outputs and c09-models 1.0.0 schemas; contract.test.ts reads every committed
// document and the schema files against them in both directions. `satisfies` ties the keys to the generated types, so a
// key added to a schema and not here fails `tsc`. Kept beside the instrument that reads them; contract.types.ts composes
// the variant and models descriptors from these (`variantKind`, `modelsKind`), the integrator's lines for the case.
import type { components } from '../../lib/contract.gen';
import type { Kind } from '../../lib/contract.types';

// A row or a block that the schema composes by a rule (a oneOf on a const: observed or not, in range or flagged) is
// declared 'json': the schema test compares its branches, and the typed interface of contract.gen.ts reads it.

/** A conversion factor: the value as it is and its flag (a value outside [0, 1] is flagged, never clipped). */
const CCF: Kind = { anyOf: [{ object: { value: 'number', flag: 'string' } }] };

const CONVENTION: Kind = { object: {
  name: 'string',
  definition: 'text',
  formula: 'string',
  us_terms: 'text',
} };

const GENERATOR: Kind = { object: {
  name: 'string',
  shaped_on: 'string',
  true_ccf: CCF,
  acceleration_factor: 'number',
  acceleration_window_months: 'integer',
  notice: 'text',
} };

const EAD_MODEL: Kind = 'json';

const SMALL_UNDRAWN: Kind = { object: {
  currency: 'string',
  threshold: 'number',
  applied: 'boolean',
  n_switched: 'integer',
  reference: 'string',
} };

const REPLICATION_SET: Kind = { object: {
  seeds: { array: 'integer' },
  n_replications: 'integer',
  n_facilities: 'integer',
  n_defaults: 'integer',
} };

export const C09_OUTPUTS: Kind = { object: {
  kind: 'string',
  level: 'integer',
  level_description: 'text',
  currency: 'string',
  convention: CONVENTION,
  generator: GENERATOR,
  replications: { object: { development: REPLICATION_SET, test: REPLICATION_SET } },
  ccf_by_design: { object: {
    tolerance: 'number',
    rows: { array: 'json' },
  } },
  ccf_distribution: { object: {
    design: 'string',
    n: 'integer',
    edges: { array: 'number' },
    counts: { array: 'integer' },
    n_below_zero: 'integer',
    n_above_one: 'integer',
  } },
  ead_models: { array: EAD_MODEL },
  ead_backtest: { object: {
    currency: 'string',
    bands: { array: 'number' },
    rows: { array: 'json' },
  } },
  ead_floor: { object: {
    currency: 'string',
    rule: 'text',
    off_balance_share: 'number',
    rows: { array: { object: {
      facility_class: 'string',
      sa_ccf: 'number',
      reference: 'string',
      n: 'integer',
      share_binding: 'number',
      mean_ead_before: 'number',
      mean_ead_after: 'number',
    } } },
  } },
  small_undrawn: SMALL_UNDRAWN,
} } satisfies { object: Record<keyof components['schemas']['c09Outputs'], Kind> };

export const C09_FIT: Kind = { object: {
  currency: 'string',
  convention: CONVENTION,
  generator: GENERATOR,
  marginals: { array: { object: {
    field: 'string',
    distribution: 'string',
    parameters: { array: { object: { name: 'string', value: 'number', unit: 'string' } } },
    source: 'string',
  } } },
  levels: { array: { object: {
    level: 'integer',
    label: 'text',
    acceleration_factor: 'number',
    acceleration_window_months: 'integer',
  } } },
  replications_plan: { object: {
    development_seeds: { array: 'integer' },
    test_seeds: { array: 'integer' },
    n_facilities: 'integer',
  } },
  designs: { array: { object: {
    design: 'string',
    horizon_months: { nullable: 'integer' },
    n_reference: { nullable: 'integer' },
    step_months: { nullable: 'integer' },
    label: 'text',
  } } },
  treatments: { array: 'string' },
  ead_models: { array: EAD_MODEL },
  small_undrawn: SMALL_UNDRAWN,
  floors: { object: {
    off_balance_share: 'number',
    reference: 'string',
    supervisory_ccfs: { array: { object: { item: 'string', ccf: 'number', reference: 'string' } } },
  } },
} } satisfies { object: Record<keyof components['schemas']['c09Fit'], Kind> };
