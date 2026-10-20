// The run-time descriptors of the C21 documents (outputs of a year-pair variant, and the fit of the models artifact), one
// key per key of the c21-outputs and c21-models 2.0.0 schemas; contract.test.ts reads every committed document and the
// schema files against them in both directions. `satisfies` ties the top-level keys to the generated types, so a key
// added to a schema and not here fails `tsc`. Kept beside the instrument that reads them; contract.types.ts composes the
// variant and models descriptors from these (`variantKind`, `modelsKind`), the integrator's lines for the case.
//
// The outputs schema is a oneOf over the six year pairs (pair_id with its two years) and each attribute a oneOf over the
// four protected attributes (their group names): the schema walker has no descriptor form for a union of objects, so the
// variant descriptor declares `outputs` as `json`, and the key-by-key description is `C21_OUTPUTS_SHAPE`, which the
// consumer test reads every committed outputs document against, in both directions.
import type { components } from '../../lib/contract.gen';
import type { Kind } from '../../lib/contract.types';

const CI: Kind = { object: { lo: 'number', hi: 'number', level: 'number' } };

const LEGAL_SENTENCE: Kind = { object: { citation: 'string', quote: 'string', text: 'text' } };

const LEGAL: Kind = { object: {
  label: 'text',
  regulation_b: LEGAL_SENTENCE,
  fair_housing_act: LEGAL_SENTENCE,
  procedures: LEGAL_SENTENCE,
  unconditional_rates_are: 'string',
  controlled_disparity_is: 'string',
  is_a_finding_of_violation: 'boolean',
} };

const LICENCE: Kind = { object: { status: 'string', platform_terms: 'string', platform_terms_cover: 'string', modified_statement: 'string', note: 'text' } };

const CONVENTIONS: Kind = { object: {
  label: 'string',
  // the three code lists are tuples of constants (prefixItems), which the schema walker reads as open
  outcome: { object: { approval_codes: 'json', denial_codes: 'json', excluded_codes: 'json', note: 'text' } },
  dti_recode: { object: { bins: { array: 'string' }, note: 'text' } },
  group_exclusion: 'text',
  identifiers: { object: { id: 'string', observation_date: 'string', label: 'string', note: 'text' } },
} };

const NOTE: Kind = { object: { field: 'string', treatment: 'string', n_missing: { nullable: 'integer' }, reason: 'text' } };

const CONTROLLED: Kind = { object: {
  model: 'string',
  outcome: 'string',
  coefficient: 'number',
  odds_ratio: 'number',
  ci: CI,
  n: 'integer',
  controls: { array: 'string' },
  missing_controls: { array: 'string' },
  label: 'string',
} };

const RATE_SPREAD: Kind = { object: {
  model: 'string',
  population: 'string',
  coefficient: 'number',
  ci: CI,
  n: 'integer',
  controls: { array: 'string' },
  missing_controls: { array: 'string' },
  label: 'string',
  unit: 'string',
} };

const CONFIRMATION: Kind = { object: {
  fit_year: 'integer',
  confirm_year: 'integer',
  fit_coefficient: 'number',
  confirm_coefficient: 'number',
  same_sign: 'boolean',
  size_ratio: { nullable: 'number' },
} };

const CONTRAST: Kind = { object: {
  group: 'string',
  reference_group: 'string',
  n_group: 'integer',
  n_reference: 'integer',
  selection_rate_group: 'number',
  selection_rate_reference: 'number',
  parity_gap: 'number',
  parity_ratio: { nullable: 'number' },
  adverse_impact_ratio: { object: { value: { nullable: 'number' }, note: 'text' } },
  z_test: { object: { statistic: 'number', p_value: 'number' } },
  fisher_exact: { object: { odds_ratio: { nullable: 'number' }, p_value: 'number' } },
  controlled: { object: { estimate: { nullable: CONTROLLED }, reason: { nullable: 'string' } } },
  rate_spread: { object: { estimate: { nullable: RATE_SPREAD }, reason: { nullable: 'string' } } },
  confirmation: { object: { estimate: { nullable: CONFIRMATION }, reason: { nullable: 'string' } } },
} };

const ATTRIBUTE: Kind = { object: {
  field: 'string',
  legal: { object: { basis: 'string', ecoa: 'boolean', fha: 'boolean', note: 'text', theory: 'string', fha_disparate_impact: 'string' } },
  reference_group: 'string',
  groups: { array: { object: { group: 'string', n: 'integer', n_approved: 'integer', n_denied: 'integer', selection_rate: 'number' } } },
  excluded_groups: { array: { object: { group: 'string', n: 'integer', reason: 'text' } } },
  four_fifths: { object: {
    label: 'string',
    citation: 'string',
    threshold: 'number',
    is_credit_law_threshold: 'boolean',
    compared_with: 'string',
    decided_on: 'string',
    rule: 'string',
    highest_rate_group: 'string',
    groups: { array: { object: { group: 'string', ratio_to_highest: { nullable: 'number' }, flag: 'boolean' } } },
  } },
  contrasts: { array: CONTRAST },
} };

const SITUATION: Kind = { object: {
  label: 'string',
  comparator: 'string',
  counterfactual_test: { object: { run: 'boolean', reason: 'text' } },
  attribute: 'string',
  k: 'integer',
  alpha: 'number',
  tau: 'number',
  distance_normalization: 'string',
  label_parameters: 'string',
  centers: 'string',
  interval: 'string',
  n_complainants: 'integer',
  n_cases: 'integer',
  n_significant: 'integer',
} };

/** The key-by-key description of a year-pair outputs document (read by the consumer test; the schema walker cannot hold the oneOf). */
export const C21_OUTPUTS_SHAPE = { object: {
  kind: 'string',
  pair_id: 'string',
  fit_year: 'integer',
  confirm_year: 'integer',
  scope: { object: { state: 'string', source: 'string', rows_fit: 'integer', rows_confirm: 'integer' } },
  legal: LEGAL,
  licence: LICENCE,
  conventions: CONVENTIONS,
  attributes: { array: ATTRIBUTE },
  situation_testing: SITUATION,
  data_notes: { array: NOTE },
  requirements: { array: 'string' },
} } satisfies { object: Record<keyof components['schemas']['c21Outputs'], Kind> };

/** The outputs node of the variant descriptor: a oneOf over the year pairs, so `json` (see the head of the file). */
export const C21_OUTPUTS: Kind = 'json';

export const C21_FIT = { object: {
  fields: { array: { object: { name: 'string', role: 'string', alias: { nullable: 'string' } } } },
  decision_models: { array: { object: {
    fit_year: 'integer',
    kind: 'string',
    outcome: 'string',
    n: 'integer',
    converged: 'boolean',
    terms: { array: { object: { term: 'string', coefficient: 'number', se: 'number' } } },
  } } },
  conventions: CONVENTIONS,
  legal: LEGAL,
  licence: LICENCE,
  data_notes: { array: NOTE },
} } satisfies { object: Record<keyof components['schemas']['c21Fit'], Kind> };
