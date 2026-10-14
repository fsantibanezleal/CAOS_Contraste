// The run-time descriptors of the C13 documents (outputs of a deficiency variant, and the fit of the models artifact),
// one key per key of the c13-outputs and c13-models 1.0.0 schemas; contract.test.ts reads every committed document and
// the schema files against them in both directions. `satisfies` ties the keys to the generated types, so a key added to
// a schema and not here fails `tsc`. Kept beside the instrument that reads them; contract.types.ts composes the variant
// and models descriptors from these (`variantKind`, `modelsKind`), the integrator's lines for the case.
import type { components } from '../../lib/contract.gen';
import type { Kind } from '../../lib/contract.types';

const SIGN_CONVENTION: Kind = { object: {
  engine_convention: 'string',
  document_convention: 'string',
  definition: 'json',
} };

const PARAMETERS: Kind = { array: { object: { name: 'string', value: 'number', unit: 'string' } } };

const PLA_THRESHOLDS: Kind = { object: {
  spearman_green: 'number',
  spearman_red: 'number',
  ks_green: 'number',
  ks_red: 'number',
  ecdf_step: 'number',
  window_days: 'integer',
  reference: 'string',
} };

const DIST: Kind = { object: {
  mean: 'number',
  sd: 'number',
  q05: 'number',
  q50: 'number',
  q95: 'number',
  min: 'number',
  max: 'number',
} };

const ZONE_COUNTS: Kind = { object: { green: 'integer', amber: 'integer', red: 'integer' } };

// A block that the schema composes by a rule (a oneOf on a const: no deficiency is planted false and intended to fail none,
// a planted one is planted true; a desk limit is 12 at 99 percent and 30 at 97.5) is declared 'json': the typed interfaces
// of contract.gen.ts read these.

export const C13_OUTPUTS: Kind = { object: {
  kind: 'string',
  known_deficiency: 'json',
  sign_convention: SIGN_CONVENTION,
  generator: { object: {
    name: 'string',
    n_risk_factors: 'integer',
    pnl_unit: 'string',
    window_days: 'integer',
    n_replications: 'integer',
    seed_base: 'integer',
    seed_rule: 'string',
    notice: 'text',
  } },
  pnl_summary: { array: { object: {
    series: 'string',
    mean: 'number',
    sd: 'number',
    skewness: 'number',
    excess_kurtosis: 'number',
    min: 'number',
    max: 'number',
  } } },
  pla: { object: {
    thresholds: PLA_THRESHOLDS,
    spearman: DIST,
    ks: DIST,
    zones: { object: { n: 'integer', overall: ZONE_COUNTS, spearman: ZONE_COUNTS, ks: ZONE_COUNTS } },
  } },
  example: { object: {
    replication_index: 'integer',
    seed: 'integer',
    hpl: { array: 'number' },
    rtpl: { array: 'number' },
    spearman: 'number',
    ks: 'number',
    zone: 'string',
  } },
  desk_backtest: { array: 'json' },
  detection: { object: {
    role: 'string',
    rule: 'text',
    n_replications: 'integer',
    n_amber_or_red: 'integer',
    n_red: 'integer',
    share_amber_or_red: 'number',
    share_red: 'number',
    mc_se: 'number',
    ci_low: 'number',
    ci_high: 'number',
    by_test: { object: { spearman_flagged: 'integer', ks_flagged: 'integer', desk_backtest_flagged: 'integer' } },
    intended_test_flagged: { nullable: 'integer' },
  } },
} } satisfies { object: Record<keyof components['schemas']['c13Outputs'], Kind> };

export const C13_FIT: Kind = { object: {
  sign_convention: SIGN_CONVENTION,
  generator: { object: {
    name: 'string',
    true_risk_model: 'text',
    parameters: PARAMETERS,
    pnl_unit: 'string',
    window_days: 'integer',
    seed_rule: 'string',
    notice: 'text',
  } },
  deficiencies: { array: 'json' },
  pla_thresholds: PLA_THRESHOLDS,
  desk_limits: { array: 'json' },
  replication_plan: { object: { n_replications: 'integer', seed_base: 'integer', seed_rule: 'string' } },
} } satisfies { object: Record<keyof components['schemas']['c13Fit'], Kind> };
