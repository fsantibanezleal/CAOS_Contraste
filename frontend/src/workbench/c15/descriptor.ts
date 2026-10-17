// The run-time descriptors of the C15 documents (outputs of a annex1-variant variant, and the fit of the models
// artifact), one key per key of the c15-outputs 2.0.0 and c15-models 1.0.0 schemas; contract.test.ts reads every committed
// document and the schema files against them in both directions. `satisfies` ties the top-level keys to the generated
// types, so a key added to a schema and not here fails `tsc`. Kept beside the instrument that reads them;
// contract.types.ts composes the variant and models descriptors from these (`variantKind`, `modelsKind`), the
// integrator's lines for the case.
import type { components } from '../../lib/contract.gen';
import type { Kind } from '../../lib/contract.types';

// A row or a block that the schema composes by a rule (a oneOf on a const: reported or missing with its reason, a
// tabled shock size or a labelled estimate, a floor that binds or not) is declared 'json': the schema test compares its
// branches, and the typed interface of contract.gen.ts reads it. Every other node is described key by key.

const VARIANT: Kind = { object: {
  id: 'string',
  label: 'text',
  description: 'text',
  parameters: { array: { object: {
    name: 'string',
    value: 'number',
    unit: 'string',
  } } },
} };

const SIGN: Kind = { object: {
  delta_eve: 'string',
  delta_nii: 'string',
  reference: 'string',
  statement: 'text',
} };

const UNITS: Kind = { object: {
  money_scale: 'string',
  rate: 'string',
  compounding: 'string',
  shock: 'string',
  bucket_midpoint: 'string',
  dates: 'string',
} };

const BANK: Kind = { object: {
  name: 'string',
  synthetic: 'boolean',
  notice: 'text',
  seed: 'integer',
  calibration_source: 'string',
} };

const UR: Kind = { object: {
  label: 'string',
  code: 'string',
  treated_as_one_currency: 'boolean',
  definition: 'text',
  uf_value: 'number',
  uf_value_currency: 'string',
  uf_date: 'string',
  uf_source: 'string',
} };

const POINT: Kind = { object: {
  tenor_years: 'number',
  observed_yield: 'number',
  zero_rate: 'number',
} };

const CURVE: Kind = { object: {
  curve: 'string',
  month: 'string',
  date: 'string',
  source: 'string',
  series_codes: { array: 'string' },
  attribution: 'string',
  observed_kind: 'string',
  compounding: 'string',
  fit: { object: {
    model: 'string',
    parameters: { array: { object: {
      name: 'string',
      value: 'number',
      unit: 'string',
    } } },
    rmse_bp: 'number',
  } },
  points: { array: POINT },
  zero_rates_at_midpoints: { array: 'number' },
} };

const CURVES: Kind = { object: {
  clp: CURVE,
  ur: CURVE,
} };

const ASSUMPTION: Kind = { object: {
  value: 'number',
  unit: 'string',
  source_kind: 'string',
  source: 'string',
} };

const ASSUMPTIONS: Kind = { object: {
  nmd_core_share: ASSUMPTION,
  nmd_core_maturity_years: ASSUMPTION,
  prepayment_cpr: ASSUMPTION,
  term_deposit_redemption_rate: ASSUMPTION,
  deposit_beta: ASSUMPTION,
} };

const NMD_SEGMENT: Kind = 'json';

const LEG: Kind = 'json';

const SHOCK_SIZE: Kind = 'json';

const NII_SIZE: Kind = { object: {
  currency: 'string',
  parallel_bp: 'integer',
  origin: 'string',
} };

const BS_ASSUMPTION: Kind = 'json';

const DYN_ITEM: Kind = { object: {
  item_id: 'string',
  side: 'string',
  balance: 'number',
  rate0: 'number',
  spread: 'number',
  beta: 'number',
  reprice_months: 'integer',
} };

const DYN_SCENARIO: Kind = { object: {
  scenario: 'string',
  shock_bp: 'number',
  short_rate_path: { array: 'number' },
  monthly_nii: { array: 'number' },
  total: 'number',
  delta_vs_base: 'number',
} };

const DYN_SCENARIOS: Kind = { array: DYN_SCENARIO };

const DYNAMIC_LEG: Kind = { object: {
  leg: 'string',
  items: { array: DYN_ITEM },
  scenarios: DYN_SCENARIOS,
} };

const DYNAMIC_NII: Kind = { object: {
  horizon_months: 'integer',
  balance_sheet_assumption: BS_ASSUMPTION,
  legs: { array: DYNAMIC_LEG },
} };

const EAR_EVAR_LEVEL: Kind = { object: {
  level: 'number',
  nii_quantile: 'number',
  eve_quantile: 'number',
  ear: 'number',
  evar: 'number',
  ear_se: 'number',
  evar_se: 'number',
} };

// c15-outputs 1.1.0: one EaR and EVaR block per leg, shaped like C14's, in the reporting currency
const EAR_EVAR: Kind = { object: {
  leg: 'string',
  method: 'string',
  n_paths: 'integer',
  seed: 'integer',
  horizon_months: 'integer',
  parameters: { array: { object: {
    name: 'string',
    value: 'number',
    unit: 'string',
  } } },
  base_nii: 'number',
  base_eve: 'number',
  levels: { array: EAR_EVAR_LEVEL },
  mc_error_method: 'string',
  n_batches: 'integer',
} };

const LABEL: Kind = 'text';

const FLOOR_EFFECT: Kind = { object: {
  leg: 'string',
  measure: 'string',
  shock: 'string',
  buckets_floored: 'integer',
  delta_with_floor: 'number',
  delta_without_floor: 'number',
  effect: 'number',
} };

// c15-outputs 2.0.0: where each leg stands against its floor under each shock, from the engine's shocked curves
const FLOOR_DISTANCE: Kind = { object: {
  leg: 'string',
  measure: 'string',
  shock: 'string',
  lowest_rate: 'number',
  bucket: 'integer',
  floor: 'number',
  distance_bp: 'number',
  binds: 'boolean',
} };

const FLOORS: Kind = { object: {
  ur_floor: 'number',
  other_floor: 'integer',
  rule: LABEL,
  effects: { array: FLOOR_EFFECT },
  distances: { array: FLOOR_DISTANCE },
} };

const OFFSET: Kind = { object: {
  state: 'string',
  share: 'number',
  applies_to: { array: 'string' },
  rule: LABEL,
  reference: 'string',
} };

const INDEXATION: Kind = { object: {
  rate: 'number',
  net_position_uf_units: 'number',
  pn_ur: 'number',
  abs_pn_ur: 'number',
  charge: 'number',
  formula: 'string',
  note: 'text',
} };

const CPI_SCENARIO: Kind = { nullable: { object: {
  surprise_pp: 'number',
  effect: 'number',
  formula: 'string',
} } };

const LEG_EVE: Kind = { object: {
  shape_bp: { array: 'number' },
  floor_bound_buckets: { array: 'integer' },
  net_cash_flows: { array: 'number' },
  eve: 'number',
  kao: 'number',
  delta_eve: 'number',
} };

const PAIR: Kind = { object: {
  delta_clp: 'number',
  delta_ur: 'number',
  opposite_signs: 'boolean',
  with_offset: 'number',
  without_offset: 'number',
  used: 'number',
} };

const EVE_ROW: Kind = { object: {
  shock: 'string',
  clp: LEG_EVE,
  ur: LEG_EVE,
  pair: PAIR,
  total_delta_eve: 'number',
} };

const EVE_MEASURE: Kind = { object: {
  base_eve_clp: 'number',
  base_eve_ur: 'number',
  rows: { array: EVE_ROW },
  delta_eve: 'number',
  worst_shock: { nullable: 'string' },
  delta_eve_share_tier1: 'number',
} };

const NII_LEG: Kind = { object: {
  shock_bp: 'number',
  cash_flows: { array: 'number' },
  floor_bound_buckets: { array: 'integer' },
  delta_nii: 'number',
} };

const NII_ROW: Kind = { object: {
  shock: 'string',
  clp: NII_LEG,
  ur: NII_LEG,
  pair: PAIR,
} };

const NII_MEASURE: Kind = { object: {
  rows: { array: NII_ROW },
  max_pair: 'number',
  indexation_charge: 'number',
  delta_nii: 'number',
  worst_shock: { nullable: 'string' },
  delta_nii_share_tier1: 'number',
} };

const THRESHOLD_TEST: Kind = { object: {
  id: 'string',
  measure: 'number',
  base: 'number',
  ratio: 'number',
  threshold: 'number',
  breached: 'boolean',
} };

const THRESHOLDS: Kind = { object: {
  tier1: 'number',
  net_interest_and_indexation_margin_12m: 'number',
  tests: { array: THRESHOLD_TEST },
  prioritised: 'boolean',
  reference: 'string',
} };

const BUCKET_DEF: Kind = 'json';

const TABLE_ROW: Kind = 'json';

const FLOOR_RULE: Kind = { object: {
  ur_floor: 'number',
  other_floor: 'integer',
  reference: 'string',
} };

const THRESHOLD_RULE: Kind = { object: {
  id: 'string',
  threshold: 'number',
  base: 'string',
} };

const GAMMA: Kind = { object: {
  shock: 'string',
  gamma: 'number',
} };

const UMULT: Kind = { object: {
  shock: 'string',
  u: 'number',
} };

const MULTIPLIERS: Kind = { object: {
  prepayment_gamma: { array: GAMMA },
  term_deposit_u: { array: UMULT },
  reference: 'string',
} };

const NMD_CAP: Kind = 'json';

const NMD_CAPS: Kind = { array: NMD_CAP };

const CURVE_MODEL: Kind = { object: {
  curve: 'string',
  month: 'string',
  series_codes: { array: 'string' },
  model: 'string',
  parameters: { array: { object: {
    name: 'string',
    value: 'number',
    unit: 'string',
  } } },
  rmse_bp: 'number',
  attribution: 'string',
} };

const TARGET: Kind = { object: {
  metric: 'string',
  unit: 'string',
  target: 'number',
  achieved: 'number',
  source: 'string',
  as_of: 'string',
} };

const NMD_MODEL: Kind = 'json';

const PREPAYMENT: Kind = { object: {
  model: 'string',
  cpr_base: 'number',
  psa_percent: { nullable: 'number' },
  source_kind: 'string',
  source: 'string',
} };

export const C15_OUTPUTS = { object: {
  kind: 'string',
  variant: VARIANT,
  as_of: 'string',
  balance_sheet_month: 'string',
  calibration_month: 'string',
  curves_month: 'string',
  reporting_currency: 'string',
  sign_convention: SIGN,
  units: UNITS,
  bank: BANK,
  ur_currency: UR,
  curves: CURVES,
  assumptions: ASSUMPTIONS,
  nmd_segments: { array: NMD_SEGMENT },
  legs: { array: LEG },
  eve_shock_sizes: { array: SHOCK_SIZE },
  nii_shock_sizes: { array: NII_SIZE },
  dynamic_nii: DYNAMIC_NII,
  ear_evar: { array: EAR_EVAR },
  floors: FLOORS,
  offset_rule: OFFSET,
  indexation_charge: INDEXATION,
  cpi_scenario: CPI_SCENARIO,
  eve: EVE_MEASURE,
  nii: NII_MEASURE,
  thresholds: THRESHOLDS,
} } satisfies { object: Record<keyof components['schemas']['c15Outputs'], Kind> };

export const C15_FIT = { object: {
  reporting_currency: 'string',
  sign_convention: SIGN,
  units: UNITS,
  bank: BANK,
  buckets: { array: BUCKET_DEF },
  annex1_table: { array: TABLE_ROW },
  eve_shock_sizes: { array: SHOCK_SIZE },
  floors: FLOOR_RULE,
  prioritised_thresholds: { array: THRESHOLD_RULE },
  offset_share: 'number',
  indexation_rate: 'number',
  multipliers: MULTIPLIERS,
  nmd_caps: NMD_CAPS,
  curve_models: { array: CURVE_MODEL },
  calibration_targets: { array: TARGET },
  nmd_models: { array: NMD_MODEL },
  prepayment: PREPAYMENT,
} } satisfies { object: Record<keyof components['schemas']['c15Fit'], Kind> };
