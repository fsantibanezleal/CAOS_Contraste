// The run-time descriptors of the C16 documents (outputs of a scenario variant, outputs of the reverse-stress variant, and
// the fit of the models artifact), one key per key of the c16-outputs, c16-outputs-reverse and c16-models 1.0.0 schemas;
// contract.test.ts reads every committed document and the schema files against them in both directions. `satisfies` ties
// the top-level keys to the generated types, so a key added to a schema and not here fails `tsc`. Kept beside the
// instrument that reads them; contract.types.ts composes the variant and models descriptors from these (`variantKind`,
// `modelsKind`), the integrator's lines for the case.
import type { components } from '../../lib/contract.gen';
import type { Kind } from '../../lib/contract.types';

// A node the schema composes by a rule (a oneOf on a const: a survival period that is a day or survives the horizon, a
// null with its reason beside a value, a solved or refused multiplier) is declared 'json': the schema test compares its
// branches, and the typed interface of contract.gen.ts reads it. Every other node is described key by key.

const UNITS: Kind = { object: { money_scale: 'string', rate: 'string', horizon: 'string', dates: 'string' } };

const BANK: Kind = { object: { name: 'string', cert: 'number', aggregates: 'string', behaviour: 'string', deposits: 'string', notice: 'text' } };

const VARIANT: Kind = { object: {
  id: 'string',
  label: 'text',
  description: 'text',
  scenario_family: 'string',
  phase: 'string',
  parameter_set: 'string',
  horizon_days: 'number',
  axis: 'string',
} };

const SCALAR: Kind = { object: { value: 'number', unit: 'string', status: 'string', basis: 'text' } };

const GRID: Kind = { object: { values: { array: 'number' }, unit: 'string', status: 'string', basis: 'text' } };

const MAPPING_ROW: Kind = { object: { basis: 'string', role: 'string', lcr_category: 'string', list_class: 'string', label: 'text' } };

const DEPOSIT_MAPPING: Kind = { object: { status: 'string', rows: { array: MAPPING_ROW }, sensitivity_band: { array: MAPPING_ROW }, basis: 'text' } };

const VARIANT_ROW: Kind = { object: { variant: 'string', scenario_family: 'string', phase: 'string', parameter_set: 'string', horizon_days: 'number', axis: 'string' } };

const VARIANT_SCENARIOS: Kind = { object: { status: 'string', rows: { array: VARIANT_ROW }, basis: 'text' } };

const DAY_CALENDAR: Kind = { object: {
  status: 'string',
  kind: 'string',
  first_day: 'string',
  excluded_weekdays: { array: 'string' },
  holidays: { array: 'string' },
  holiday_rule: 'string',
  basis: 'text',
} };

const SECURITY_ROW: Kind = { object: {
  class_id: 'string',
  fed_category: 'string',
  duration_bucket: 'string',
  margin: { nullable: 'number' },
  haircut: 'number',
  haircut_low: 'number',
  haircut_high: 'number',
  rule: 'string',
  source: 'string',
} };

const SECURITY_MAPPING: Kind = { object: { status: 'string', rows: { array: SECURITY_ROW }, basis: 'text' } };

const POINT: Kind = { object: { day: 'number', cumulative_share: 'number' } };

const MONETISATION: Kind = { object: {
  status: 'string',
  points: { array: POINT },
  sensitivity_band: { array: { object: { id: 'string', points: { array: POINT } } } },
  basis: 'text',
} };

const CALIBRATION_RULE: Kind = { object: { status: 'string', rule: 'string', basis: 'text' } };

const CLIFF_DAYS: Kind = { object: { status: 'string', near: 'number', far: 'number', day_basis: 'string', basis: 'text' } };

const CONVENTIONS: Kind = { object: {
  deposit_category_mapping: DEPOSIT_MAPPING,
  variant_scenarios: VARIANT_SCENARIOS,
  day_calendar: DAY_CALENDAR,
  cbc_securities_mapping: SECURITY_MAPPING,
  monetisation_schedule: MONETISATION,
  fast_run_calibration_rule: CALIBRATION_RULE,
  cliff_days: CLIFF_DAYS,
  contractual_bucket_edges_days: GRID,
  event_horizon_days: SCALAR,
  uninsured_share_grid: GRID,
  htm_loss_multiple_grid: GRID,
  runoff_multiplier_grid: GRID,
  reverse_target_days: SCALAR,
  list_compounding_tolerance: SCALAR,
  monotonicity_tolerance_days: SCALAR,
  nlp_identity_tolerance: SCALAR,
  cliff_amber_threshold: SCALAR,
  cliff_red_threshold: SCALAR,
  scoring_ratio_green: SCALAR,
  scoring_ratio_amber: SCALAR,
  generator_truth_se_green: SCALAR,
  generator_truth_se_red: SCALAR,
  htm_revaluation_green: SCALAR,
  htm_revaluation_amber: SCALAR,
  round_trip_tolerance_days: SCALAR,
  cbc_haircut_band: SCALAR,
} };

const DATA: Kind = { object: {
  call_reports: { array: { object: { report_date: 'string', source: 'string', fields: { array: 'string' } } } },
  data_cutoff: 'string',
  read_up_to_valuation_date: 'boolean',
  rule: 'text',
} };

const AGGREGATE: Kind = { nullable: { object: {
  source: 'string',
  series: { array: { object: {
    series_id: 'string',
    label: 'text',
    unit: 'string',
    points: { array: { object: { date: 'string', value: 'number' } } },
  } } },
} } };

const DEPOSITS: Kind = { object: {
  dep: 'number',
  depdom: 'number',
  depuna: 'number',
  depins: 'number',
  depsmamt: 'number',
  deplgamt: 'number',
  denominators: { object: { insured_uninsured: 'string', total: 'string' } },
  uninsured_share_of_dep: 'number',
  uninsured_share_of_depdom: 'number',
  size_threshold: { object: { value: 'number', unit: 'string', source: 'string' } },
} };

// an item either carries its reported amount or the reason it is missing
const ITEM: Kind = 'json';

const BALANCE_SHEET: Kind = { object: {
  as_of: 'string',
  items: { array: ITEM },
  total_assets: 'number',
  deposits: DEPOSITS,
  assumptions: { array: { object: { assumption_id: 'string', statement: 'text', behaviour: 'string', applies_to: 'string' } } },
} };

const CBC_CLASS: Kind = { object: {
  class_id: 'string',
  label: 'text',
  source_fields: { array: 'string' },
  carrying_value: 'number',
  fair_value: { nullable: 'number' },
  value_used: 'number',
  encumbered: 'number',
  haircut: { object: { value: 'number', rule: 'string' } },
  liquidity_value: 'number',
} };

const CBC: Kind = { object: {
  as_of: 'string',
  htm_valuation_basis: 'string',
  haircut_framework: { object: { label: 'text', central_bank: 'string', effective_from: 'string', effective_to: 'string', source: 'string' } },
  classes: { array: CBC_CLASS },
  pledged: { object: { field: 'string', amount: 'number', share_of_securities: 'number' } },
  total_liquidity_value: 'number',
} };

const CONTRACTUAL_LADDER: Kind = { object: {
  buckets: { array: { object: { from_day: 'number', to_day: { nullable: 'number' }, inflows: 'number', outflows: 'number', gap: 'number', cumulative_gap: 'number' } } },
  reference: 'string',
} };

// the daily path: a ladder, the survival period (a day or the horizon), the minimum NLP and the cliff or its reason
const PATH: Kind = 'json';

const HQLA: Kind = { object: {
  l1: 'number',
  l2a: 'number',
  l2b: 'number',
  adjusted_l1: 'number',
  adjusted_l2a: 'number',
  adjusted_l2b: 'number',
  adj_15: 'number',
  adj_40: 'number',
  hqla: 'number',
  // null together with their reason when the HQLA stock is empty (c16-outputs 2.0.0, U11 decision X6)
  l2_share: { nullable: 'number' },
  l2b_share: { nullable: 'number' },
  shares_reason: { nullable: 'text' },
  caps: { object: { l2_cap: 'number', l2b_cap: 'number' } },
} };

const LCR_ROW: Kind = { object: { category: 'string', balance: 'number', rate: 'number', amount: 'number', reference: 'string' } };

const LCR: Kind = { object: {
  label: 'string',
  reported_or_regulatory: 'boolean',
  statement: 'text',
  hqla: HQLA,
  outflows: { array: LCR_ROW },
  total_outflows: 'number',
  inflows: { array: LCR_ROW },
  total_inflows: 'number',
  inflow_cap: 'number',
  inflows_counted: 'number',
  net_outflows: 'number',
  ratio: 'number',
  mapping_sensitivity: { array: { object: { mapping_id: 'string', lcr_category: 'string', uninsured_outflow: 'number', total_outflows: 'number', inflows_counted: 'number', net_outflows: 'number', ratio: 'number' } } },
  below_100_note: 'text',
} };

// the HTM losses: reported, applied, the CBC with and without the loss, the labelled par counterfactual, the revaluation row
const HTM: Kind = { nullable: 'json' };

const ANCHOR: Kind = { object: { label: 'text', source: 'string', outflow_share: 'number', days: 'number', implied_daily_rate: 'number', forecast_claim: 'boolean' } };

const SCORING: Kind = { object: {
  event: { object: { label: 'text', event_date: 'string', horizon_days: 'number', source: 'string' } },
  model_deposit_base: 'number',
  modelled_outflow: 'json',
  // the two denominators are pinned by id (a tuple): the Board's carries no amount (null), the call report's carries both
  denominators: { array: { anyOf: [
    { object: { id: 'string', label: 'text', denominator_amount: { nullable: 'json' }, realised_amount: { nullable: 'json' }, realised_share: 'number', source: 'string', modelled_share: 'number', compared_at: 'string', shortfall: 'number', ratio: 'number', light: 'string' } },
    { object: { id: 'string', label: 'text', denominator_amount: 'number', realised_amount: 'number', realised_share: 'number', source: 'string', modelled_share: 'number', compared_at: 'string', shortfall: 'number', ratio: 'number', light: 'string' } },
  ] } },
  svb_anchor: ANCHOR,
  table_a1_scoring: { array: 'json' },
} };

const SENSITIVITIES: Kind = { object: {
  uninsured_share: { nullable: { array: { object: { share: 'number', survival: 'json' } } } },
  uninsured_share_reason: { nullable: 'text' },
  htm_loss: { nullable: { array: { object: { multiple: 'number', unrealised_loss: 'number', cbc: 'number', survival: 'json' } } } },
  htm_loss_reason: { nullable: 'text' },
} };

const TIME_POINT: Kind = { object: {
  as_of: 'string',
  report_date: 'string',
  deposits: DEPOSITS,
  htm_unrealised_loss: 'number',
  cbc_amortised_basis: 'number',
  cbc_fair_value_basis: 'number',
  survival: { nullable: 'json' },
  lcr_ratio: { nullable: 'number' },
} };

export const C16_OUTPUTS = { object: {
  kind: 'string',
  valuation_date: 'string',
  currency: 'string',
  units: UNITS,
  bank: BANK,
  variant: VARIANT,
  conventions: CONVENTIONS,
  data: DATA,
  aggregate_record: AGGREGATE,
  aggregate_record_reason: { nullable: 'text' },
  balance_sheet: BALANCE_SHEET,
  cbc: CBC,
  contractual_ladder: CONTRACTUAL_LADDER,
  path: { nullable: PATH },
  path_reason: { nullable: 'text' },
  lcr: { nullable: LCR },
  lcr_reason: { nullable: 'text' },
  htm: HTM,
  htm_reason: { nullable: 'text' },
  scoring: SCORING,
  sensitivities: SENSITIVITIES,
  time_block: { array: TIME_POINT },
} } satisfies { object: Record<keyof components['schemas']['c16Outputs'], Kind> };

const REVERSE_BASE: Kind = { object: {
  base_id: 'string',
  parameter_set: 'string',
  label: 'text',
  base_survival: 'json',
  max_rate_below_one: 'number',
  max_multiplier: 'number',
  curve: { array: { object: { multiplier: 'number', survival: 'json' } } },
  solved: 'json',
} };

export const C16_OUTPUTS_REVERSE = { object: {
  kind: 'string',
  valuation_date: 'string',
  currency: 'string',
  units: UNITS,
  bank: BANK,
  conventions: CONVENTIONS,
  target: { object: { days: 'number', statement: 'text' } },
  cap_rule: { object: { each_rate_below_one: 'boolean', statement: 'text' } },
  bases: { array: REVERSE_BASE },
} } satisfies { object: Record<keyof components['schemas']['c16ReverseOutputs'], Kind> };

const LIST_ROW: Kind = { object: { item: 'string', baseline: 'number', adverse: 'number', extreme: 'number' } };

const LIST_PARAMETERS: Kind = { object: {
  source: 'string',
  attribution: 'string',
  // the rows of a table are pinned to their own item and rate constants by the schema (a tuple): a union of one shape
  contractual_outflows: { array: { anyOf: [LIST_ROW] } },
  open_maturity_daily: { array: { anyOf: [LIST_ROW] } },
  contractual_inflows: { array: LIST_ROW },
  committed_drawdown: { array: { object: { item: 'string', adverse: 'number', extreme: 'number' } } },
  relevant_days_six_months: 'number',
  relevant_days_three_months: 'number',
  calendar_note: 'text',
  results_annex: { object: {
    n_banks: 'number',
    median_survival_days: { object: { adverse: 'number', extreme: 'number' } },
    unit: 'string',
    sources: { object: { annex: 'string', n_banks_slide: 'number', median_slides: { array: 'number' }, dossier: 'string' } },
    statement: 'text',
  } },
} };

const GENERATOR_SEGMENT: Kind = { object: {
  segment: 'string',
  share_of_deposits: 'number',
  calm_daily_hazard: 'number',
  stress_daily_hazard: 'number',
  p_enter_stress: 'number',
  p_exit_stress: 'number',
  basis: 'text',
} };

export const C16_FIT = { object: {
  currency: 'string',
  units: UNITS,
  bank: BANK,
  conventions: CONVENTIONS,
  parameter_sets: { array: { object: { set_id: 'string', source: 'string', source_kind: 'string' } } },
  list_parameters: LIST_PARAMETERS,
  list_goldens: { array: { object: { id: 'string', daily_rate: 'number', days: 'number', cumulative_outflow: 'number', label: 'string' } } },
  table_a1: { object: {
    source: 'string',
    attribution: 'string',
    rows: { array: { object: { row_id: 'string', bank: 'string', year: 'number', outflow_share: 'number', days: 'number' } } },
    lcr_range: { object: { label: 'string', low: 'number', high: 'number', days: 'number' } },
  } },
  calibration: { object: {
    split: { object: { calibrated_on: { array: 'string' }, scored_on: { array: 'string' } } },
    implied_daily_rates: { array: { object: { row_id: 'string', implied_daily_rate: 'number' } } },
    fitted_daily_rate: { object: { value: 'number', unit: 'string', source_kind: 'string', source: 'string' } },
    anchor: ANCHOR,
    statement: 'text',
  } },
  generator: { object: {
    config: { object: { truth_status: 'string', seed: 'number', n_depositors: 'number', horizon_days: 'number', segments: { array: GENERATOR_SEGMENT } } },
    truth: { array: { object: { segment: 'string', horizon_days: 'number', true_outflow_rate: 'number' } } },
    verification: { object: { n_draws: 'number', max_abs_error: 'number', mc_standard_error: 'number', within_error: 'boolean' } },
  } },
  sources: { array: { object: { source_id: 'string', publisher: 'string', licence_class: 'string', licence_basis: 'string', statement: 'text' } } },
} } satisfies { object: Record<keyof components['schemas']['c16Fit'], Kind> };
