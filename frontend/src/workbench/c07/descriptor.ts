// The run-time descriptors of the C07 documents (outputs of a three-regime variant, and the fit of the models
// artifact), one key per key of the c07-outputs and c07-models 1.0.0 schemas; contract.test.ts reads every committed
// document and the schema files against them in both directions. `satisfies` ties the keys to the generated types, so a
// key added to a schema and not here fails `tsc`. Kept beside the instrument that reads them; contract.types.ts composes
// the variant and models descriptors from these (`variantKind`, `modelsKind`).
import type { components } from '../../lib/contract.gen';
import type { Kind } from '../../lib/contract.types';

export const C07_OUTPUTS: Kind = { object: {
  kind: 'string',
  scenario_id: 'string',
  currency: 'string',
  synthetic: 'boolean',
  notice: 'text',
  scenario: { object: {
    description: 'text',
    shocks: { array: { object: {
      driver: 'string',
      unit: 'string',
      value: 'number',
    } } },
  } },
  portfolio: { object: {
    currency: 'string',
    segments: { array: { object: {
      segment_id: 'string',
      label: 'text',
      accounts: 'integer',
      gross_exposure: 'number',
    } } },
  } },
  regimes: { array: { object: {
    regime: 'string',
    label: 'text',
    currency: 'string',
    total_provision: 'number',
    coverage_rate: 'number',
    by_segment: { array: { object: {
      segment_id: 'string',
      provision: 'number',
      coverage_rate: 'number',
    } } },
    by_category: { array: { object: {
      category_id: 'string',
      label: 'text',
      exposure: 'number',
      provision: 'number',
    } } },
    status: 'string',
    unallocated_lines: { array: { object: {
      id: 'string',
      kind: 'string',
      label: 'text',
      amount: 'number',
    } } },
  } } },
  comparison: { object: {
    currency: 'string',
    rows: { array: { object: {
      segment_id: 'string',
      cmf_b1_provision: 'number',
      ifrs9_provision: 'number',
      bde_annex9_provision: 'number',
      gap_ifrs9_minus_b1: 'number',
      gap_bde_minus_b1: 'number',
    } } },
    unallocated: { object: {
      cmf_b1_provision: 'number',
      ifrs9_provision: 'number',
      bde_annex9_provision: 'number',
      gap_ifrs9_minus_b1: 'number',
      gap_bde_minus_b1: 'number',
    } },
  } },
  gap_bridge: { object: {
    currency: 'string',
    from_regime: 'string',
    to_regime: 'string',
    steps: { array: { object: {
      id: 'string',
      label: 'text',
      amount: 'number',
    } } },
  } },
  b1_detail: { object: {
    currency: 'string',
    minimum_check: { object: {
      minimum_rate: 'number',
      normal_portfolio_exposure: 'number',
      normal_portfolio_provision_before_minimum: 'number',
      minimum_amount: 'number',
      binding: 'boolean',
      top_up: 'number',
    } },
    group_max_rule: { array: { object: {
      segment_id: 'string',
      standard: 'number',
      internal: { nullable: 'number' },
      applied: 'number',
      method: 'string',
      internal_reason: { nullable: 'text' },
    } } },
    additional_provisions: { object: {
      amount: 'number',
      rationale: 'text',
      policy_min: 'number',
      policy_max: 'number',
    } },
    individual: { object: {
      normal_substandard_provision: 'number',
      default_provision: 'number',
    } },
    booked_total: 'number',
  } },
  ifrs9_detail: { object: {
    currency: 'string',
    stage_summary: { array: { object: {
      stage: 'string',
      accounts: 'integer',
      gross_carrying_amount: 'number',
      ecl: 'number',
      coverage: 'number',
    } } },
    overlays_total: 'number',
    measure: 'string',
    weighted_components: { array: { object: {
      scenario_id: 'string',
      weight: 'number',
      z: 'number',
      single_scenario_ecl: 'number',
    } } },
    overlays: { array: { object: {
      id: 'string',
      label: 'text',
      segment_id: { nullable: 'string' },
      stage: { nullable: 'string' },
      amount: 'number',
    } } },
  } },
  bde_detail: { object: {
    currency: 'string',
    categories: { array: { object: {
      category: 'string',
      mapped_stage: 'string',
      exposure: 'number',
      provision: 'number',
      coverage_rate: 'number',
    } } },
    method: 'string',
  } },
  delta_vs_base: { nullable: { object: {
    currency: 'string',
    cmf_b1_delta: 'number',
    ifrs9_delta: 'number',
    bde_annex9_delta: 'number',
  } } },
} } satisfies { object: Record<keyof components['schemas']['c07Outputs'], Kind> };

export const C07_FIT: Kind = { object: {
  currency: 'string',
  bank: { object: {
    name: 'string',
    synthetic: 'boolean',
    notice: 'text',
    seed: 'integer',
    calibration_source: { anyOf: ['string', 'text'] },
  } },
  calibration_targets: { array: { object: {
    metric: 'string',
    unit: 'string',
    target: 'number',
    achieved: 'number',
    source: { anyOf: ['string', 'text'] },
    as_of: 'string',
  } } },
  segments: { array: { object: {
    id: 'string',
    label: 'text',
    accounts: 'integer',
    gross_exposure: 'number',
    b1_portfolio: 'string',
    bde_segment: 'string',
    bde_segment_label: 'text',
  } } },
  b1_tables: { array: { object: {
    table_id: 'string',
    portfolio: 'string',
    source: 'text',
    cells: { array: { object: {
      row: 'string',
      column: 'string',
      pi: 'number',
      pdi: { nullable: 'number' },
      pe: { nullable: 'number' },
    } } },
  } } },
  b1_default_categories: { array: { object: {
    category: 'string',
    tpe_upper: { nullable: 'number' },
    provision_rate: 'number',
  } } },
  ifrs9: { object: {
    pd_ladder_rung: 'string',
    discount_convention: 'string',
    segments: { array: { object: {
      segment_id: 'string',
      pd_ttc: 'number',
      rho: 'number',
      lgd: 'number',
    } } },
    weighting_scenarios: { array: { object: {
      id: 'string',
      label: 'text',
      weight: 'number',
      z_offset: 'number',
    } } },
    eir_basis: 'string',
    staging_policy: { object: {
      dpd_backstop: 'integer',
      default_dpd: 'integer',
      threefold_ratio: 'number',
      absolute_floor: 'number',
      probation_months: 'integer',
      low_credit_risk_pd: { nullable: 'number' },
      multiplier_schedule: { array: { object: {
        pd_origination_upper: 'number',
        multiplier: 'number',
      } } },
      source: 'string',
    } },
  } },
  bde: { object: {
    normal_coverage: { array: { object: {
      segment: 'string',
      normal: 'number',
      special_watch: 'number',
    } } },
    doubtful_bucket_labels: { array: 'string' },
    doubtful_bucket_upper_days: { array: { nullable: 'integer' } },
    doubtful_coverage: { array: { object: {
      segment: 'string',
      by_bucket: { array: 'number' },
    } } },
  } },
  scenarios: { array: { object: {
    id: 'string',
    label: 'text',
    shocks: { array: { object: {
      driver: 'string',
      unit: 'string',
      value: 'number',
    } } },
    z_shift: 'number',
  } } },
} } satisfies { object: Record<keyof components['schemas']['c07Fit'], Kind> };
