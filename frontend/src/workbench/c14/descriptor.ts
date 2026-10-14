// The run-time descriptors of the C14 documents (outputs of a valuation-date variant, and the fit of the models
// artifact), one key per key of the c14-outputs and c14-models 1.0.0 schemas; contract.test.ts reads every committed
// document and the schema files against them in both directions. `satisfies` ties the top-level keys to the generated
// types, so a key added to a schema and not here fails `tsc`. Kept beside the instrument that reads them;
// contract.types.ts composes the variant and models descriptors from these (`variantKind`, `modelsKind`), the
// integrator's lines for the case.
import type { components } from '../../lib/contract.gen';
import type { Kind } from '../../lib/contract.types';

// A row or a block that the schema composes by a rule (a oneOf on a const: reported or missing with its reason, a
// tabled shock size or a labelled estimate, a floor that binds or not) is declared 'json': the schema test compares its
// branches, and the typed interface of contract.gen.ts reads it. Every other node is described key by key.

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
  cert: 'integer',
  aggregates: 'string',
  behaviour: 'string',
  notice: 'text',
} };

const REPORT: Kind = { object: {
  report_date: 'string',
  source: 'string',
  fields: { array: 'string' },
} };

const LABEL: Kind = 'text';

const DATA: Kind = { object: {
  call_reports: { array: REPORT },
  data_cutoff: 'string',
  read_up_to_valuation_date: 'boolean',
  rule: LABEL,
} };

const POINT: Kind = { object: {
  tenor_years: 'number',
  observed_yield: 'number',
  zero_rate: 'number',
} };

const CURVE: Kind = { object: {
  date: 'string',
  source: 'string',
  observed_kind: 'string',
  compounding: 'string',
  interpolation: 'string',
  missing_tenors: { array: 'number' },
  points: { array: POINT },
  zero_rates_at_midpoints: { array: 'number' },
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

const ITEM: Kind = 'json';

const BALANCE_SHEET: Kind = { object: {
  as_of: 'string',
  items: { array: ITEM },
  total_assets: 'number',
  total_liabilities: 'number',
} };

const GAP_ROW: Kind = 'json';

const DURATION_GAP: Kind = { object: {
  asset_value: 'number',
  liability_value: 'number',
  asset_duration_years: 'number',
  liability_duration_years: 'number',
  duration_gap_years: 'number',
  equity_change_100bp_up: 'number',
} };

const LADDER: Kind = { object: {
  nmd_assumption: 'string',
  repricing_gap: { array: GAP_ROW },
  delta_nii_gap_100bp_up: 'number',
  duration_gap: DURATION_GAP,
} };

const SHOCK_SIZE: Kind = 'json';

const SHOCK_RESULT: Kind = 'json';

const OUTLIER: Kind = { object: {
  threshold_share_tier1: 'number',
  tier1: 'number',
  eve_risk_measure: 'number',
  ratio: 'number',
  breached: 'boolean',
  reference: 'string',
} };

const SCENARIO: Kind = { object: {
  calibration: 'string',
  nmd_assumption: 'string',
  nmd_treatment: 'string',
  shock_size: SHOCK_SIZE,
  floor: { nullable: 'number' },
  base_eve: 'number',
  shocks: { array: SHOCK_RESULT },
  eve_risk_measure: 'number',
  worst_shock: { nullable: 'string' },
  outlier: OUTLIER,
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

const DYNAMIC_NII: Kind = { object: {
  horizon_months: 'integer',
  balance_sheet_assumption: BS_ASSUMPTION,
  items: { array: DYN_ITEM },
  scenarios: DYN_SCENARIOS,
} };

const EAR_EVAR_LEVEL: Kind = { object: {
  level: 'number',
  nii_quantile: 'number',
  eve_quantile: 'number',
  ear: 'number',
  evar: 'number',
} };

const EAR_EVAR: Kind = { object: {
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
  monte_carlo_error: { object: {
    ear: 'number',
    evar: 'number',
  } },
} };

const OUT_OF_SAMPLE: Kind = 'json';

const COMPARISON: Kind = { object: {
  calibration: 'string',
  shock: 'string',
  delta_eve_behavioural: 'number',
  delta_eve_contractual: 'number',
  difference: 'number',
} };

const BUCKET_DEF: Kind = 'json';

const SHOCK_TABLE: Kind = { object: {
  calibration: 'string',
  source: 'string',
  data_window: 'string',
  percentile: 'string',
  rounding_bp: 'integer',
  rows: 'json',
} };

const SHOCK_SHAPE: Kind = { object: {
  x: 'integer',
  steepener_short: 'number',
  steepener_long: 'number',
  flattener_short: 'number',
  flattener_long: 'number',
  short_form: 'string',
  long_form: 'string',
  reference: 'string',
} };

const NMD_CAP: Kind = 'json';

const NMD_CAPS: Kind = { array: NMD_CAP };

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

const NMD_MODEL: Kind = 'json';

const PARAM_CHANGE: Kind = { object: {
  parameter: 'string',
  category: 'string',
  from_date: 'string',
  to_date: 'string',
  from_value: 'number',
  to_value: 'number',
  unit: 'string',
  limit_breach_in_window: 'boolean',
  flagged: 'boolean',
  note: 'text',
} };

const OUTLIER_RULE: Kind = { object: {
  threshold_share_tier1: 'number',
  reference: 'string',
} };

export const C14_OUTPUTS = { object: {
  kind: 'string',
  valuation_date: 'string',
  quarter: 'string',
  currency: 'string',
  sign_convention: SIGN,
  units: UNITS,
  bank: BANK,
  data: DATA,
  curve: CURVE,
  assumptions: ASSUMPTIONS,
  nmd_segments: { array: NMD_SEGMENT },
  balance_sheet: BALANCE_SHEET,
  ladder: { array: LADDER },
  scenarios: { array: SCENARIO },
  dynamic_nii: DYNAMIC_NII,
  ear_evar: EAR_EVAR,
  out_of_sample: OUT_OF_SAMPLE,
  behavioural_comparison: { array: COMPARISON },
} } satisfies { object: Record<keyof components['schemas']['c14Outputs'], Kind> };

export const C14_FIT = { object: {
  currency: 'string',
  sign_convention: SIGN,
  units: UNITS,
  bank: BANK,
  buckets: { array: BUCKET_DEF },
  shock_tables: { array: SHOCK_TABLE },
  applied_sizes: { array: SHOCK_SIZE },
  shock_shape: SHOCK_SHAPE,
  nmd_caps: NMD_CAPS,
  multipliers: MULTIPLIERS,
  nmd_models: { array: NMD_MODEL },
  nmd_parameter_changes: { array: PARAM_CHANGE },
  outlier: OUTLIER_RULE,
} } satisfies { object: Record<keyof components['schemas']['c14Fit'], Kind> };
