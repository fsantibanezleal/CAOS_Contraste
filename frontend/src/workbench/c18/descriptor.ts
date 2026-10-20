// The run-time descriptors of the C18 documents (outputs of a scenario variant, of the t-copula aggregation variant and of
// the reverse-stress variant, and the fit of the models artifact), one key per key of the c18-outputs,
// c18-outputs-aggregation, c18-outputs-reverse and c18-models 1.0.0 schemas. The fixtures under docs/contracts/fixtures/c18
// are read against them in both directions by c18.test.tsx, and contract.test.ts reads the committed documents and the schema
// files against them once the bake writes them. `satisfies` ties the top-level keys to the generated types, so a key added to
// a schema and not here fails `tsc`. Kept beside the instrument that reads them; contract.types.ts composes the variant and
// models descriptors from these (`variantKind`, `modelsKind`), the integrator's lines for the case.
//
// A node the schema composes by a rule (a oneOf on a const: a marginal by its risk, the cell of Annex 3 by its status, a
// mitigation that applies or does not, a level rule by its kind) is declared 'json': the schema test compares its branches,
// and the typed interface of contract.gen.ts reads it. Every other node is described key by key.
import type { components } from '../../lib/contract.gen';
import type { Kind } from '../../lib/contract.types';

const BANK: Kind = { object: {
  name: 'string',
  synthetic: 'boolean',
  notice: 'text',
  as_of: 'string',
} };

const FACTORS: Kind = { array: { object: {
  id: 'string',
  label: 'text',
  unit: 'string',
  sd: 'number',
} } };

const NAMED: Kind = { object: {
  name: 'string',
  value: 'number',
  unit: 'string',
  label: 'string',
  basis: 'text',
} };

const NAMED_SET: Kind = { object: {
  name: 'string',
  values: { array: 'number' },
  unit: 'string',
  label: 'string',
  basis: 'text',
} };

const BARRIEU_SCANDOLO: Kind = { object: {
  rho_x0_clp_m: 'number',
  rho_max_clp_m: 'number',
  rho_min_clp_m: 'number',
  am: 'number',
  rm: 'number',
} };

const GLASSERMAN_XU: Kind = { object: {
  quantity: 'text',
  relative_entropy_budget: 'number',
  theta: 'number',
  baseline_clp_m: 'number',
  worst_case_clp_m: 'number',
} };

const MATRIX: Kind = { object: {
  name: 'string',
  order: 'json',
  matrix: { array: { array: 'number' } },
  unit: 'string',
  label: 'string',
  basis: 'text',
} };

const FACTOR_SPACE: Kind = { object: {
  window: { object: {
    start: 'string',
    end: 'string',
  } },
  factors: FACTORS,
  covariance: { array: { array: 'number' } },
  label: 'string',
} };

const BAND: Kind = { array: { object: {
  method: 'string',
  nu: { nullable: 'number' },
  capital_clp_m: 'number',
  diversification_factor: 'number',
  status: 'string',
  label: 'text',
  horizon_years: 'number',
  confidence_level: 'number',
  mc_se_clp_m: { nullable: 'number' },
} } };

const MODEL_RISK: Kind = { object: {
  status: 'string',
  label: 'text',
  set_of_models: 'string',
  reference_model: { object: {
    method: 'string',
    nu: { nullable: 'number' },
  } },
  barrieu_scandolo: BARRIEU_SCANDOLO,
  glasserman_xu: GLASSERMAN_XU,
} };

const DIVERSIFICATION: Kind = { object: {
  status: 'string',
  label: 'text',
  reference_row: { object: {
    method: 'string',
    nu: { nullable: 'number' },
  } },
  factor: 'number',
  benefit: 'number',
  euler_benefit_by_risk: { array: { object: {
    risk: 'string',
    benefit: 'number',
  } } },
} };

const EULER: Kind = { object: {
  status: 'string',
  label: 'text',
  risk_measure: 'string',
  level: 'number',
  horizon_years: 'number',
  copula: { object: {
    family: 'string',
    nu: { nullable: 'number' },
  } },
  es_total_clp_m: 'number',
  allocation: { array: { object: {
    risk: 'string',
    contribution_clp_m: 'number',
    share: 'number',
  } } },
  additivity: { object: {
    sum_clp_m: 'number',
    relative_error: 'number',
    tolerance: 'number',
  } },
} };

const AGGREGATION: Kind = { object: {
  capital_basis: 'string',
  horizon_years: 'number',
  confidence_level: 'number',
  correlation: MATRIX,
  nu_set: NAMED_SET,
  marginals: { array: 'json' },
  headline: { object: {
    method: 'string',
    capital_clp_m: 'number',
    label: 'text',
  } },
  band: BAND,
  model_risk: MODEL_RISK,
  euler: EULER,
  diversification: DIVERSIFICATION,
} };

export const C18_OUTPUTS = { object: {
  kind: 'string',
  currency: 'string',
  units: { object: {
    money: 'string',
    ratio: 'string',
    dates: 'string',
  } },
  bank: BANK,
  capital_start: { object: {
    rwa_clp_m: 'number',
    rwa_by_risk: { object: {
      credit: 'number',
      market: 'number',
      operational: 'number',
    } },
    cet1_clp_m: 'number',
    at1_clp_m: 'number',
    t2_clp_m: 'number',
    pe_clp_m: 'number',
    cet1_ratio: 'number',
    pe_ratio: 'number',
    basis: 'text',
  } },
  scenario: { object: {
    scenario_id: 'string',
    title: 'text',
    provider: 'string',
    source_document: 'string',
    source_url: 'string',
    vintage_date: 'string',
    adaptation_label: 'string',
    adaptation_statement: 'text',
    paths: { array: { object: {
      variable: 'string',
      unit: 'string',
      maps_to_regressor: 'string',
      frequency: 'string',
      vintage_date: 'string',
      level_rule: 'json',
      source: { array: { object: {
        date: 'string',
        value: 'number',
      } } },
      levels: { array: { object: {
        date: 'string',
        value: 'number',
      } } },
      transposition: { object: {
        label: 'string',
        rule: 'string',
        source_jump_off: { object: {
          date: 'string',
          value: 'number',
        } },
        target: { object: {
          date: 'string',
          value: 'number',
        } },
        reversion: 'string',
      } },
      transposed: { array: { object: {
        date: 'string',
        value: 'number',
      } } },
    } } },
    policy_shock_window: { nullable: { object: {
      start_year: 'number',
      end_year: 'number',
      label: 'text',
    } } },
  } },
  satellites: { object: {
    fed_loan_types: { array: 'json' },
    banco_andino_classes: { array: { object: {
      banco_andino_class: 'string',
      maps_from: { array: 'string' },
      weights: { array: 'number' },
      exposure_clp_m: 'number',
      label: 'string',
      quarters: { array: { object: {
        quarter_end: 'string',
        rate: 'number',
      } } },
    } } },
  } },
  losses: { object: {
    scenario_losses: { array: { object: {
      year: 'number',
      period_end: 'string',
      credit: 'number',
      market: 'number',
      irrbb: 'number',
      operational: 'number',
      total: 'number',
    } } },
    basis: 'text',
  } },
  internal_capital_target: { object: {
    formula: 'string',
    horizon_years: 'number',
    min_pe: 'number',
    c_dsib: 'number',
    c_p2: NAMED,
    c_ccob: 'number',
    c_ccyb: 'number',
    c_d: NAMED,
    oi: 'number',
  } },
  capital_plan: { object: {
    cases: { array: { object: {
      case: 'string',
      years: { array: { object: {
        year: 'number',
        period_end: 'string',
        rwa_clp_m: 'number',
        cet1: { object: {
          pct_of_rwa: 'number',
          need_clp_m: { nullable: 'number' },
          available_clp_m: 'number',
        } },
        at1: { object: {
          pct_of_rwa: 'number',
          need_clp_m: { nullable: 'number' },
          available_clp_m: 'number',
        } },
        t2: { object: {
          pct_of_rwa: 'number',
          need_clp_m: { nullable: 'number' },
          available_clp_m: 'number',
        } },
        pe: { object: {
          pct_of_rwa: 'number',
          need_clp_m: { nullable: 'number' },
          available_clp_m: 'number',
        } },
        requirement: { object: {
          basis: 'string',
          pct_of_rwa: 'number',
        } },
        headroom_pct_of_rwa: 'number',
        deficit_clp_m: 'number',
      } } },
    } } },
    mitigation: 'json',
    alternative_sources: { array: { object: {
      year: 'number',
      source: 'string',
      amount_clp_m: 'number',
      label: 'string',
    } } },
  } },
  p2g_proxy: { object: {
    label: 'string',
    formula: 'string',
    peak_depletion: 'number',
    peak_year: 'number',
    usable_buffers_and_mitigation: 'number',
    value: 'number',
    statement: 'text',
    cmf_calibration_public: 'boolean',
  } },
  annex3: { object: {
    entity: 'string',
    report_date: 'string',
    consolidation: 'string',
    money_unit: 'string',
    rows: { array: { object: {
      row_id: 'string',
      label_cmf: 'string',
      a: 'json',
      b: 'json',
      c: 'json',
      d: 'json',
    } } },
  } },
  headline_cet1: { object: {
    method: 'string',
    statement: 'text',
    rows: { array: { object: {
      year: 'number',
      period_end: 'string',
      cet1_start_clp_m: 'number',
      cumulative_loss_clp_m: 'number',
      cet1_clp_m: 'number',
      rwa_clp_m: 'number',
      cet1_ratio: 'number',
    } } },
    ppnr: { object: {
      label: 'string',
      statement: 'text',
      nii_source: 'string',
      fee_ratio: NAMED,
      cost_ratio: NAMED,
      rows: { array: { object: {
        year: 'number',
        period_end: 'string',
        nii_clp_m: 'number',
        fee_income_clp_m: 'number',
        operating_cost_clp_m: 'number',
        ppnr_clp_m: 'number',
        cet1_with_ppnr_clp_m: 'number',
        cet1_ratio_with_ppnr: 'number',
      } } },
    } },
  } },
  severity: { object: {
    reference_episode: { object: {
      name: 'string',
      start: 'string',
      end: 'string',
      source: 'text',
    } },
    minimum_ratio: 'number',
    rows: { array: { object: {
      variable: 'string',
      maps_to_regressor: 'string',
      unit: 'string',
      path_peak_deviation: 'number',
      path_peak_quarter: 'string',
      history_peak_deviation: 'number',
      history_window: { object: {
        start: 'string',
        end: 'string',
      } },
      history_source: 'text',
      ratio: 'number',
      is_stress: 'boolean',
    } } },
  } },
  backcast: { object: {
    window: { object: {
      start: 'string',
      end: 'string',
    } },
    per_loan_type: { array: 'json' },
    descriptive_2026: { array: { object: {
      quarter_end: 'string',
      realised_rates: { array: { object: {
        fed_loan_type: 'string',
        rate: 'number',
      } } },
      label: 'string',
      forecast_claim: 'boolean',
    } } },
    statement: 'text',
  } },
  aggregation: AGGREGATION,
} } satisfies { object: Record<keyof components['schemas']['c18Outputs'], Kind> };

export const C18_OUTPUTS_AGGREGATION = { object: {
  kind: 'string',
  currency: 'string',
  units: { object: {
    money: 'string',
    ratio: 'string',
    dates: 'string',
  } },
  bank: BANK,
  scenario_id: 'string',
  aggregation: AGGREGATION,
  correlation_stress: { object: {
    pair: { object: {
      a: 'string',
      b: 'string',
      value: 'number',
    } },
    aggregation: AGGREGATION,
  } },
  copula_sensitivity: { array: { object: {
    nu: 'number',
    gaussian_capital_clp_m: 'number',
    t_capital_clp_m: 'number',
    relative_difference: 'number',
  } } },
  rosenberg_schuermann: { object: {
    role: 'string',
    weights: { object: {
      market: 'number',
      credit: 'number',
      operational: 'number',
    } },
    correlations: { object: {
      market_credit: 'number',
      market_operational: 'number',
      credit_operational: 'number',
    } },
    published_additive_overestimate: { object: {
      low: 'number',
      high: 'number',
    } },
    case_additive_overestimate: 'number',
    within_published_range: 'boolean',
  } },
} } satisfies { object: Record<keyof components['schemas']['c18AggOutputs'], Kind> };

export const C18_OUTPUTS_REVERSE = { object: {
  kind: 'string',
  currency: 'string',
  units: { object: {
    money: 'string',
    ratio: 'string',
    dates: 'string',
  } },
  bank: BANK,
  failure_point: { object: {
    label: 'string',
    definition: 'text',
    stack: { object: {
      cet1_min: 'number',
      c_ccob: 'number',
      c_ccyb: 'number',
      c_dsib: 'number',
      p2_cet1: NAMED,
      total: 'number',
      basis: 'string',
    } },
    cet1_ratio_start: 'number',
    rwa_clp_m: 'number',
    horizon_years: 'number',
  } },
  factor_space: FACTOR_SPACE,
  loss_model: 'json',
  solution: { object: {
    method: 'string',
    z_star: { array: 'number' },
    x_star: { array: 'number' },
    mahalanobis_distance: 'number',
    plausibility: { object: {
      chi_square_df: 'number',
      tail_probability: 'number',
    } },
    loss_at_z_star_clp_m: 'number',
    loss_threshold_clp_m: 'number',
    relative_gap: 'number',
    tolerance: 'number',
  } },
  starts: { array: { object: {
    start_id: 'string',
    converged: 'boolean',
    distance: 'number',
    loss_clp_m: 'number',
  } } },
} } satisfies { object: Record<keyof components['schemas']['c18RevOutputs'], Kind> };

export const C18_FIT = { object: {
  currency: 'string',
  units: { object: {
    money: 'string',
    ratio: 'string',
    dates: 'string',
  } },
  bank: BANK,
  satellites: { array: 'json' },
  class_mapping: { array: { object: {
    banco_andino_class: 'string',
    fed_loan_types: { array: 'string' },
    weights: { array: 'number' },
    label: 'string',
    basis: 'text',
  } } },
  factor_space: FACTOR_SPACE,
  aggregation: { object: {
    ladder: { array: { object: {
      method: 'string',
      engine_function: 'string',
    } } },
    n_draws: 'number',
    seed: 'number',
    chunk_size: 'number',
    horizon_years: 'number',
    confidence_level: 'number',
    capital_basis: 'string',
    marginal_interpolation: 'string',
  } },
  named_parameters: { object: {
    nu_set: NAMED_SET,
    correlation_matrix_base: MATRIX,
    correlation_matrix_stress: MATRIX,
    ppnr_fee_ratio: NAMED,
    ppnr_cost_ratio: NAMED,
    c_p2: NAMED,
    c_d: NAMED,
    operational_conversion_rate: { object: {
      name: 'string',
      value: 'number',
      unit: 'string',
      label: 'string',
      basis: 'text',
      derivation: { object: {
        kind: 'string',
        pair: 'string',
        observation_date: 'string',
        source: 'string',
        source_url: 'string',
        source_series: 'string',
      } },
    } },
    asset_scaling: { object: {
      name: 'string',
      value: 'number',
      unit: 'string',
      label: 'string',
      basis: 'text',
      derivation: { object: {
        kind: 'string',
        banco_andino_assets_clp_m: 'number',
        c17_bank_assets_eur_m: 'number',
        converted_at: 'string',
      } },
    } },
    market_rwa_share: NAMED,
    market_horizon_scaling: { object: {
      name: 'string',
      value: 'number',
      unit: 'string',
      label: 'string',
      basis: 'text',
      source_confidence_level: 'number',
      source_horizon_days: 'number',
      trading_days_per_year: 'number',
      level_factor: NAMED,
      horizon_factor: NAMED,
    } },
    reverse_p2_cet1: NAMED,
  } },
  bank_anchors: { object: {
    rwa_basis: { object: {
      tier1_proxy_clp_m: 'number',
      cet1_ratio_anchor: 'number',
      rwa_total_clp_m: 'number',
    } },
    rwa_mix: { object: {
      credit: 'number',
      market: 'number',
      operational: 'number',
    } },
    chilean_stack: { object: {
      cet1_min: 'number',
      c_ccob: 'number',
      c_ccyb: 'number',
      c_dsib: 'number',
      p2r: 'number',
      p2_cap: 'number',
    } },
    loan_exposures: { array: { object: {
      banco_andino_class: 'string',
      exposure_clp_m: 'number',
      share: 'number',
    } } },
    source: 'text',
    licence_class: 'string',
    ratios_only: 'boolean',
  } },
  marginal_sources: { array: 'json' },
  scenario_sources: { array: { object: {
    scenario_id: 'string',
    provider: 'string',
    document: 'string',
    url: 'string',
    vintage_date: 'string',
    licence_class: 'string',
    variables: { array: { object: {
      name: 'string',
      unit: 'string',
    } } },
  } } },
  capital_engine: { object: {
    balance_sheet: 'string',
    horizon_years: 'number',
    rules: { array: { object: {
      source: 'string',
      paragraph: 'string',
      page: 'number',
      statement: 'string',
    } } },
    reversion_quarters: 'number',
  } },
} } satisfies { object: Record<keyof components['schemas']['c18Fit'], Kind> };

