// The run-time descriptors of the C06 documents (outputs of a reporting-date variant, and the fit of the models
// artifact), one key per key of the c06-outputs and c06-models 1.0.0 schemas; contract.test.ts reads every committed
// document and the schema files against them in both directions. `satisfies` ties the keys to the generated types, so a
// key added to a schema and not here fails `tsc`. Kept beside the instrument that reads them; contract.types.ts composes
// the variant and models descriptors from these (`variantKind`, `modelsKind`).
import type { components } from '../../lib/contract.gen';
import type { Kind } from '../../lib/contract.types';

export const C06_OUTPUTS: Kind = { object: {
  kind: 'string',
  reporting_date: 'string',
  currency: 'string',
  period_months: 'integer',
  horizon: { object: {
    stage1_months: 'integer',
    lifetime_cap_months: 'integer',
  } },
  settings: { object: {
    discount_convention: 'string',
    eir_basis: 'string',
    probation_months: 'integer',
    low_credit_risk_exemption: 'boolean',
    sicr: { object: {
      dpd_backstop: 'integer',
      threefold_ratio: 'number',
      absolute_floor: 'number',
      multiplier_schedule: { array: { object: {
        pd_origination_upper: 'number',
        multiplier: 'number',
      } } },
      default_dpd: 'integer',
      low_credit_risk_pd: { nullable: 'number' },
    } },
  } },
  data_status: { object: {
    primary_source: 'string',
    freddie_mac_available: 'boolean',
    freddie_mac_reason: { nullable: 'string' },
    notice: 'text',
  } },
  scenarios: { array: { object: {
    id: 'string',
    label: 'text',
    weight: 'number',
    z_mean: 'number',
  } } },
  term_structures: { array: { object: {
    scenario_id: 'string',
    segment_id: 'string',
    months: { array: 'integer' },
    hazard: { array: 'number' },
    marginal_pd: { array: 'number' },
    cumulative_pd: { array: 'number' },
  } } },
  account_curves: { array: { object: {
    account_id: 'string',
    segment_id: 'string',
    stage: 'string',
    months: { array: 'integer' },
    origination_cumulative_pd: { array: 'number' },
    current_cumulative_pd: { array: 'number' },
  } } },
  sicr_points: { array: { object: {
    account_id: 'string',
    segment_id: 'string',
    stage: 'string',
    pd_origination_annualised: 'number',
    pd_current_annualised: 'number',
    trigger: 'string',
  } } },
  stage_flows: { object: {
    from_date: 'string',
    to_date: 'string',
    currency: 'string',
    flows: { array: { object: {
      source: 'string',
      target: 'string',
      accounts: 'integer',
      gross_carrying_amount: 'number',
    } } },
  } },
  stage_summary: { object: {
    currency: 'string',
    rows: { array: { object: {
      stage: 'string',
      accounts: 'integer',
      gross_carrying_amount: 'number',
      ecl: 'number',
      coverage: 'number',
    } } },
  } },
  ecl_by_scenario: { object: {
    currency: 'string',
    rows: { array: { object: {
      scenario_id: 'string',
      stage: 'string',
      ecl: 'number',
    } } },
  } },
  weight_grid: { object: {
    currency: 'string',
    scenario_ids: { array: 'string' },
    points: { array: { object: {
      weights: { array: 'number' },
      ecl_recomputed: 'number',
      ecl_frozen: 'number',
      stage2_ratio_recomputed: 'number',
      stage2_ratio_frozen: 'number',
    } } },
  } },
  non_linearity: { object: {
    currency: 'string',
    parameters: { object: {
      pd_ttc: 'number',
      rho: 'number',
    } },
    mean_z: 'number',
    pd_weighted: 'number',
    pd_at_mean_z: 'number',
    ecl_weighted: 'number',
    ecl_at_mean_path: 'number',
    index: 'number',
    z_curve: { array: { object: {
      z: 'number',
      pd_pit: 'number',
    } } },
    scenario_points: { array: { object: {
      scenario_id: 'string',
      z: 'number',
      weight: 'number',
      pd_pit: 'number',
    } } },
  } },
  waterfall: { object: {
    currency: 'string',
    lines: { array: { object: {
      id: 'string',
      kind: 'string',
      label: 'text',
      amount: 'number',
      stage: { nullable: 'string' },
      overlay_id: { nullable: 'string' },
    } } },
  } },
  overlays: { array: { object: {
    id: 'string',
    currency: 'string',
    rationale: 'text',
    method: 'string',
    target: 'string',
    segment_id: { nullable: 'string' },
    stage: { nullable: 'string' },
    amount: 'number',
    staging_effect: 'string',
    review_date: 'string',
  } } },
  reconciliation: { object: {
    currency: 'string',
    tolerance: 'number',
    allowance: { array: { object: {
      stage: 'string',
      opening: 'number',
      movements: { array: { object: {
        line_id: 'string',
        amount: 'number',
      } } },
      closing: 'number',
      residual: 'number',
    } } },
    gross_carrying_amount: { array: { object: {
      stage: 'string',
      opening: 'number',
      movements: { array: { object: {
        line_id: 'string',
        amount: 'number',
      } } },
      closing: 'number',
      residual: 'number',
    } } },
  } },
  lifetime_backtest: { object: {
    rows: { array: { object: {
      origination_cohort: 'string',
      months: 'integer',
      estimator: 'string',
      predicted_cumulative_pd: 'number',
      observed_cumulative_pd: { nullable: 'number' },
      gap: { nullable: 'number' },
      brier: { nullable: 'number' },
      reason: { nullable: 'string' },
    } } },
  } },
  rung_comparison: { array: { object: {
    rung_id: 'string',
    c_index: { nullable: 'number' },
    integrated_brier: { nullable: 'number' },
    calibration_gap_12m: { nullable: 'number' },
    reason: { nullable: 'string' },
  } } },
  decile_calibration: { object: {
    rung_id: 'string',
    rows: { array: { object: {
      origination_cohort: 'string',
      months: 'integer',
      decile: 'integer',
      n: 'integer',
      estimator: 'string',
      predicted_cumulative_pd: 'number',
      observed_cumulative_pd: { nullable: 'number' },
      reason: { nullable: 'string' },
    } } },
  } },
} } satisfies { object: Record<keyof components['schemas']['c06Outputs'], Kind> };

export const C06_FIT: Kind = { object: {
  currency: 'string',
  segments: { array: { object: {
    id: 'string',
    label: 'text',
    pd_ttc: 'number',
    accounts: 'integer',
  } } },
  scenario_definitions: { array: { object: {
    id: 'string',
    label: 'text',
    weight: 'number',
    source: 'string',
    z_path: { array: { object: {
      months: 'integer',
      z: 'number',
    } } },
    macro: { array: { object: {
      variable: 'string',
      unit: 'string',
      months: { array: 'integer' },
      values: { array: 'number' },
    } } },
  } } },
  pit: { object: {
    rho: 'number',
    method: 'string',
    z_hat: { array: { object: {
      period: 'string',
      z: 'number',
    } } },
    satellite: { object: {
      intercept: 'number',
      ar1: 'number',
      coefficients: { array: { object: {
        name: 'string',
        value: 'number',
      } } },
    } },
  } },
  ladder: { array: { object: {
    rung_id: 'string',
    kind: 'string',
    covariates: { array: 'string' },
    macro_covariates: { array: 'string' },
    competing_prepayment: 'boolean',
    training_cutoff: 'string',
    coefficients: { array: { object: {
      name: 'string',
      estimate: 'number',
      std_error: { nullable: 'number' },
    } } },
    baseline: { object: {
      months: { array: 'integer' },
      cumulative_pd: { array: 'number' },
    } },
  } } },
  lgd: { object: {
    kind: 'string',
    discounting: 'string',
    segments: { array: { object: {
      segment_id: 'string',
      lgd: 'number',
      basis: 'string',
    } } },
  } },
  ead: { object: {
    amortising: 'boolean',
    ccf_revolving: { nullable: 'number' },
    reason: { nullable: 'string' },
  } },
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
} } satisfies { object: Record<keyof components['schemas']['c06Fit'], Kind> };
