// The web side of the two contracts (data-pipeline/pipeline/io/contract.py and data-pipeline/pipeline/core/manifest.py).
// The interfaces type the app; the descriptors describe the same keys at run time, and `satisfies` ties each descriptor
// to its interface (a key added to one and not the other fails `tsc`). contract.test.ts reads every committed artifact
// against the descriptors in both directions, types included, so the pipeline cannot ship a shape the web does not
// read, and the web cannot read a key the pipeline does not write (T11, CT-004).

import type { components } from './contract.gen';
import { C06_FIT, C06_OUTPUTS } from '../workbench/c06/descriptor';
import { C07_FIT, C07_OUTPUTS } from '../workbench/c07/descriptor';
import { C03_FIT, C03_OUTPUTS } from '../workbench/c03/descriptor';
import { C08_FIT, C08_OUTPUTS } from '../workbench/c08/descriptor';
import { C09_FIT, C09_OUTPUTS } from '../workbench/c09/descriptor';
import { C10_FIT, C10_OUTPUTS_GRID, C10_OUTPUTS_LOAN_TYPE } from '../workbench/c10/descriptor';
import { C11_FIT, C11_OUTPUTS } from '../workbench/c11/descriptor';
import { C12_FIT, C12_OUTPUTS } from '../workbench/c12/descriptor';
import { C13_FIT, C13_OUTPUTS } from '../workbench/c13/descriptor';
import { C14_FIT, C14_OUTPUTS } from '../workbench/c14/descriptor';
import { C15_FIT, C15_OUTPUTS } from '../workbench/c15/descriptor';
import { C16_FIT, C16_OUTPUTS, C16_OUTPUTS_REVERSE } from '../workbench/c16/descriptor';
import { C17_FIT, C17_OUTPUTS } from '../workbench/c17/descriptor';
import { C18_FIT, C18_OUTPUTS, C18_OUTPUTS_AGGREGATION, C18_OUTPUTS_REVERSE } from '../workbench/c18/descriptor';
import { C02_FIT, C02_OUTPUTS } from '../workbench/c02/descriptor';
import { C20_FIT, C20_OUTPUTS, C20_OUTPUTS_LEAKAGE, C20_OUTPUTS_PERTURBATION, C20_OUTPUTS_SEEDS, C20_OUTPUTS_SHIFT } from '../workbench/c20/descriptor';
import { C21_FIT, C21_OUTPUTS } from '../workbench/c21/descriptor';

/** Every reader-facing string is bilingual at the source. */
export type Text = components['schemas']['common-text'];

/** A run-time description of a value: a primitive, a bilingual text, an array, an object, a map, a kind that may
 * also be null, one of several kinds, or any JSON value (only where the engine's record is open by design: the
 * `extras` of a TestResult and the internals of a model record, which the views read through typed accessors). */
export type Kind =
  | 'string'
  | 'number'
  | 'integer'
  | 'boolean'
  | 'text'
  | 'json'
  | { array: Kind }
  | { object: Record<string, Kind> }
  | { map: Kind }
  | { nullable: Kind }
  | { anyOf: Kind[] };

/** Every way `value` departs from `kind`, with its path; empty when it conforms. Booleans are not numbers. */
export function conform(value: unknown, kind: Kind, path = '$'): string[] {
  if (kind === 'string') return typeof value === 'string' ? [] : [`${path}: expected a string`];
  if (kind === 'number') return typeof value === 'number' && Number.isFinite(value) ? [] : [`${path}: expected a finite number`];
  if (kind === 'integer') return Number.isInteger(value) ? [] : [`${path}: expected an integer`];
  if (kind === 'boolean') return typeof value === 'boolean' ? [] : [`${path}: expected a boolean`];
  if (kind === 'json') return value === undefined ? [`${path}: expected a JSON value`] : [];
  if (kind === 'text') return conform(value, { object: { en: 'string', es: 'string' } }, path);
  if ('nullable' in kind) return value === null ? [] : conform(value, kind.nullable, path);
  if ('anyOf' in kind) {
    const tries = kind.anyOf.map((k) => conform(value, k, path));
    return tries.some((t) => t.length === 0) ? [] : [`${path}: matches none of ${kind.anyOf.length} kinds`];
  }
  if ('array' in kind) {
    if (!Array.isArray(value)) return [`${path}: expected an array`];
    return value.flatMap((v, i) => conform(v, kind.array, `${path}[${i}]`));
  }
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return [`${path}: expected an object`];
  const obj = value as Record<string, unknown>;
  if ('map' in kind) return Object.entries(obj).flatMap(([k, v]) => conform(v, kind.map, `${path}.${k}`));
  const want = Object.keys(kind.object);
  const out = [
    ...want.filter((k) => !(k in obj)).map((k) => `${path}.${k}: declared by the web, not written by the pipeline`),
    ...Object.keys(obj).filter((k) => !want.includes(k)).map((k) => `${path}.${k}: written by the pipeline, not declared by the web`),
  ];
  for (const k of want) if (k in obj) out.push(...conform(obj[k], kind.object[k], `${path}.${k}`));
  return out;
}

const num = 'number' as const;
const nNum = { nullable: 'number' } as const;
const nInt = { nullable: 'integer' } as const;
const nStr = { nullable: 'string' } as const;
const nums = { array: 'number' } as const;

// --- CONTRACT 2: the index, the case manifest, the models and variant artifacts ---------------------------------

export const SCHEMAS = {
  index: 'contraste.index/v1',
  manifest: 'contraste.manifest/v1',
  variant: 'contraste.case/v1',
  models: 'contraste.models/v1',
} as const;

export type TruthStatus = components['schemas']['common-provenance']['truth_status'];
export type PipelineLane = components['schemas']['common-gate-verdict']['lane'];
export type Light = components['schemas']['common-test-result']['light'];
export type Severity = components['schemas']['common-finding']['severity'];

export type CaseIndexEntry = components['schemas']['caseIndexEntry'];

export type CaseIndex = components['schemas']['common-case-index'];

export type GateVerdict = components['schemas']['common-gate-verdict'];

export type ArtifactEntry = components['schemas']['common-artifact-entry'];

export type ContractExample = components['schemas']['contractExample'];

export type ContractSummary = components['schemas']['common-contract-summary'];

export type SourceDetails = components['schemas']['common-source-details'];

export type CaseManifest = components['schemas']['common-case-manifest'];

export type Calibration = components['schemas']['modelCalibration'];

export type ModelSummary = components['schemas']['common-model-summary'];

/** A model record with its internals (points tables, shape functions, grids), in the models artifact. */
export type ModelRecord = components['schemas']['common-model-record'];

export type GradeRow = components['schemas']['c01GradeRow'];

export type ReliabilityBin = components['schemas']['c01ReliabilityBin'];

export type RungOutputs = components['schemas']['c01RungOutputs'];

/** One point of the retail risk weight, from riskvalidation, for the live port (CT-215). */
export type RetailParityPoint = components['schemas']['c01RetailParityPoint'];

export type RegimeFacts = components['schemas']['c01RegimeFacts'];

/** What C01's capital view states (CT-212, CT-214). */
export type C01Irb = components['schemas']['c01Irb'];

export type ScoredSample = components['schemas']['c01ScoredSample'];

export type GroupStat = components['schemas']['c01GroupStat'];

export type VariantOutputs = components['schemas']['c01VariantOutputs'];

export type TestRow = components['schemas']['common-test-result'];

export type ImpactItem = components['schemas']['common-impact-item'];

export type Finding = components['schemas']['common-finding'];

export type Provenance = components['schemas']['common-provenance'];

export type LaneBlock = components['schemas']['common-lane-block'];


export type FeatureMeta = components['schemas']['c01FeatureMeta'];

export type SplitPart = components['schemas']['c01SplitPart'];

export type ReasonStability = components['schemas']['c01ReasonStability'];

export type FitInfo = components['schemas']['c01FitInfo'];


/** One variant's artifact; `O` is the case's outputs (C01's by default, the other cases' below). */
export type VariantArtifact<O = VariantOutputs> = Omit<components['schemas']['common-variant-envelope'], 'outputs'> & { outputs: O };

/** One models artifact; `F` is the case's fit. */
export type ModelsArtifact<F = FitInfo> = Omit<components['schemas']['common-models-envelope'], 'fit'> & { fit: F };

export const GATE = {
  lane: 'string',
  pure_python: 'boolean',
  wheels: { array: 'string' },
  trace_bytes: 'integer',
  run_ms_budget: num,
  trace_bytes_budget: 'integer',
  reasons: { array: 'string' },
} satisfies Record<keyof GateVerdict, Kind>;

export const INDEX = {
  schema: 'string',
  engine_version: 'string',
  n_cases: 'integer',
  default_case: 'string',
  cases: {
    array: {
      object: { case_id: 'string', title: 'text', category: 'text', category_id: 'string', kind: 'string', manifest_path: 'string' } satisfies Record<
        keyof CaseIndexEntry,
        Kind
      >,
    },
  },
  files: { array: 'string' },
} satisfies Record<keyof CaseIndex, Kind>;

const ENTRY_BASE = {
  role: 'string',
  variant_id: 'string',
  title: 'text',
  short_title: 'text',
  regime: 'text',
  truth_status: 'string',
  path: 'string',
  bytes: 'integer',
  lane: 'string',
  gate: { object: GATE },
} as const;

/** A models entry carries no models_ref; a variant entry always does. */
export const MODELS_ENTRY = ENTRY_BASE satisfies Record<Exclude<keyof ArtifactEntry, 'models_ref'>, Kind>;
export const VARIANT_ENTRY = { ...ENTRY_BASE, models_ref: 'string' } satisfies Record<keyof ArtifactEntry, Kind>;

const COUNTS = { map: 'integer' } as const;

export const CONTRACT_SUMMARY = {
  family: 'string',
  counts: { object: { input: 'integer', accepted: 'integer', rejected: 'integer', flagged: 'integer', excluded: 'integer' } },
  by_rule: { object: { rejected: COUNTS, flagged: COUNTS, excluded: COUNTS } },
  ignored_columns: { array: 'string' },
  examples: {
    array: {
      object: {
        kind: 'string',
        row: 'integer',
        key: 'string',
        field: 'string',
        value: nStr,
        expected: 'string',
        policy: 'string',
        reason: 'string',
        rule: nStr,
      } satisfies Record<keyof ContractExample, Kind>,
    },
  },
} satisfies Record<keyof ContractSummary, Kind>;

export const MANIFEST = {
  schema: 'string',
  case_id: 'string',
  title: 'text',
  category: 'text',
  question: 'text',
  sources: { array: 'string' },
  source_details: {
    map: {
      object: { name: 'string', publisher: 'string', landing: 'string', licence: 'string', class: 'string', attribution: 'string' } satisfies Record<
        keyof SourceDetails,
        Kind
      >,
    },
  },
  seed: 'integer',
  engine: { object: { pipeline: 'string', riskvalidation: nStr } },
  default_variant: 'string',
  // entries are checked one by one by their role (models or variant) in the test
  artifacts: { array: 'json' },
  contract: { map: { object: CONTRACT_SUMMARY } },
  expect: { map: nums },
} satisfies Record<keyof CaseManifest, Kind>;

export const MODEL_SUMMARY = {
  id: 'string',
  family: 'string',
  rung: 'string',
  title: 'text',
  short_title: 'text',
  engine: 'string',
  engine_version: 'string',
  licence: 'string',
  calibration: {
    nullable: { object: { kind: 'string', fitted_on: 'string', x: nums, y: nums } satisfies Record<keyof Calibration, Kind> },
  },
  parameters: { map: { object: { value: num, unit: 'string' } } },
  checkpoint_sha256: nStr,
} satisfies Record<keyof ModelSummary, Kind>;

export const MODEL_RECORD = { ...MODEL_SUMMARY, details: 'json' } satisfies Record<keyof ModelRecord, Kind>;

const RELIABILITY = { array: { object: { n: 'integer', pd: num, dr: num, lo: num, hi: num } satisfies Record<keyof ReliabilityBin, Kind> } };

export const RUNG_OUTPUTS = {
  grades: {
    array: {
      object: { grade: 'string', lo: num, hi: num, n: 'integer', d: 'integer', pd: nNum, dr: nNum } satisfies Record<keyof GradeRow, Kind>,
    },
  },
  reliability: RELIABILITY,
  roc: { object: { fpr: nums, tpr: nums } },
  cap: { object: { population: nums, defaults: nums, default_rate: num } },
  distribution: { object: { log10_pd_edges: nums, defaulters: { array: 'integer' }, non_defaulters: { array: 'integer' } } },
  cutoff: {
    object: {
      cutoff: nums,
      approval_rate: nums,
      bad_rate: nums,
      pd_ead: nums,
      ead: nums,
      capital_per_lgd: { map: nums },
      capital_per_lgd_transactors: { nullable: { map: nums } },
    } satisfies Record<keyof RungOutputs['cutoff'], Kind>,
  },
  reliability_raw: { nullable: RELIABILITY },
} satisfies Record<keyof RungOutputs, Kind>;

export const C01_IRB = {
  asset_class: 'string',
  regimes: { array: 'string' },
  by_regime: {
    map: {
      object: { name: 'string', pd_floor_revolver: nNum, pd_floor: num, scaling: num, references: { map: 'string' } } satisfies Record<
        keyof RegimeFacts,
        Kind
      >,
    },
  },
  revolvers_only: 'boolean',
  six_month_full_payers: nInt,
  lgd_floor_basel3: num,
  lgd_floor_source: 'string',
  transactor_source: 'string',
  ead: 'text',
  parity: {
    nullable: {
      array: {
        object: { regime: 'string', asset_class: 'string', revolver: 'boolean', pd: num, lgd: num, risk_weight: num } satisfies Record<
          keyof RetailParityPoint,
          Kind
        >,
      },
    },
  },
} satisfies Record<keyof C01Irb, Kind>;

export const SAMPLE = {
  ids: { array: 'string' },
  targets: { array: 'integer' },
  inputs: { map: { array: { anyOf: ['number', 'string'] } } },
  scorecard_points: { array: { array: 'integer' } },
  scorecard_score: { array: 'integer' },
  scorecard_pd: nums,
  ebm_logit: nums,
} satisfies Record<keyof ScoredSample, Kind>;

export const VARIANT_OUTPUTS = {
  rungs: { map: { object: RUNG_OUTPUTS } },
  n: 'integer',
  defaults: 'integer',
  groups: {
    map: { object: { n: 'integer', default_rate: num, auc: { map: num }, roc: { map: { object: { fpr: nums, tpr: nums } } } } satisfies Record<keyof GroupStat, Kind> },
  },
  sample: { nullable: { object: SAMPLE } },
  irb: { object: C01_IRB },
} satisfies Record<keyof VariantOutputs, Kind>;

export const TEST_ROW = {
  test_id: 'string',
  model_id: nStr,
  segment: nStr,
  statistic: nNum,
  p_value: nNum,
  metric: nNum,
  h0: 'string',
  alternative: 'string',
  policy_version: 'string',
  alpha_amber: nNum,
  alpha_red: nNum,
  light: 'string',
  n: nInt,
  n_events: nInt,
  inputs_hash: 'string',
  reference: 'string',
  notes: 'string',
  extras: { map: 'json' },
} satisfies Record<keyof TestRow, Kind>;

export const PROVENANCE = {
  truth_status: 'string',
  inputs: {
    array: { object: { source: 'string', class: 'string', files: { array: { object: { name: 'string', sha256: 'string' } } } } },
  },
  licence_classes: { map: 'string' },
  generators: { array: 'string' },
  seed: 'integer',
  code_version: 'string',
  riskvalidation_version: nStr,
} satisfies Record<keyof Provenance, Kind>;

const LANE_BLOCK = { lane: 'string', reasons: { array: 'string' } } satisfies Record<keyof LaneBlock, Kind>;

export const VARIANT = {
  schema: 'string',
  case_id: 'string',
  variant_id: 'string',
  model: { array: { object: MODEL_SUMMARY } },
  outputs: { object: VARIANT_OUTPUTS },
  tests: { array: { object: TEST_ROW } },
  impact: { map: { object: { value: nNum, unit: 'string', label: 'text' } satisfies Record<keyof ImpactItem, Kind> } },
  findings: {
    array: {
      object: { id: 'string', severity: 'string', status: 'string', evidence: { array: 'string' }, title: 'text' } satisfies Record<
        keyof Finding,
        Kind
      >,
    },
  },
  provenance: { object: PROVENANCE },
  lane: { object: LANE_BLOCK },
} satisfies Record<keyof VariantArtifact, Kind>;

const SPLIT_PART = { object: { n: 'integer', defaults: 'integer', default_rate: num } satisfies Record<keyof SplitPart, Kind> };

export const FIT = {
  source: 'string',
  split: { object: { train: SPLIT_PART, calibration: SPLIT_PART, holdout: SPLIT_PART, folds: { object: { k: 'integer', repeats: 'integer' } } } },
  train_rows: 'integer',
  features: {
    array: {
      object: { name: 'string', meaning: 'text', unit: 'string', categorical: 'boolean', monotone: 'integer' } satisfies Record<
        keyof FeatureMeta,
        Kind
      >,
    },
  },
  seed: 'integer',
  master_scale: { object: { grades: { array: 'string' }, upper: nums } },
  reason_stability: {
    nullable: {
      object: {
        bootstraps: 'integer',
        rows: 'integer',
        top_k: 'integer',
        overlap_mean: num,
        overlap_min: num,
        overlap: nums,
      } satisfies Record<keyof ReasonStability, Kind>,
    },
  },
} satisfies Record<keyof FitInfo, Kind>;

export const MODELS = {
  schema: 'string',
  case_id: 'string',
  fit_id: 'string',
  model: { array: { object: MODEL_RECORD } },
  fit: { object: FIT },
  provenance: { object: PROVENANCE },
  lane: { object: LANE_BLOCK },
} satisfies Record<keyof ModelsArtifact, Kind>;

// --- rung internals the views read (typed accessors over ModelRecord.details) -----------------------------------

export interface PointsRow {
  feature: string;
  row: number;
  bin: string;
  count: number;
  events: number;
  event_rate: number | null;
  woe: number;
  iv: number;
  points_raw: number;
  points: number;
}

export interface ScorecardDetails {
  intercept: number;
  coefficients: Record<string, number>;
  features: string[];
  dropped: Record<string, string>;
  iv: Record<string, number>;
  scaling: { pdo: number; odds_ref: number; score_ref: number; factor: number; offset: number };
  points_table: PointsRow[];
  /** Each characteristic's bins as numbers: splits for a numerical one, category sets for a categorical one. */
  bins: Record<string, { kind: 'numerical'; splits: number[] } | { kind: 'categorical'; categories: string[][] }>;
}

export const POINTS_ROW = {
  feature: 'string',
  row: 'integer',
  bin: 'string',
  count: 'integer',
  events: 'integer',
  event_rate: nNum,
  woe: num,
  iv: num,
  points_raw: num,
  points: 'integer',
} satisfies Record<keyof PointsRow, Kind>;

const NUMERICAL_BINS: Kind = { object: { kind: 'string', splits: nums } };
const CATEGORICAL_BINS: Kind = { object: { kind: 'string', categories: { array: { array: 'string' } } } };

export const SCORECARD_DETAILS = {
  intercept: num,
  coefficients: { map: num },
  features: { array: 'string' },
  dropped: { map: 'string' },
  iv: { map: num },
  scaling: { object: { pdo: num, odds_ref: num, score_ref: num, factor: num, offset: num } },
  points_table: { array: { object: POINTS_ROW } },
  bins: { map: { anyOf: [NUMERICAL_BINS, CATEGORICAL_BINS] } },
} satisfies Record<keyof ScorecardDetails, Kind>;

export interface EbmLevel {
  kind: 'nominal' | 'continuous';
  categories?: Record<string, number>;
  cuts?: number[];
}

export interface EbmExport {
  intercept: number;
  features: Array<{ name: string; levels: EbmLevel[] }>;
  terms: Array<{ name: string; features: number[]; scores: unknown; shape: number[] }>;
  config: Record<string, number>;
}

export const EBM_EXPORT = {
  intercept: num,
  features: { array: { object: { name: 'string', levels: { array: 'json' } } } },
  terms: { array: { object: { name: 'string', features: { array: 'integer' }, scores: 'json', shape: { array: 'integer' } } } },
  config: { map: num },
} satisfies Record<keyof EbmExport, Kind>;

export interface MonotonicityFeature {
  direction: number;
  grid: number[];
  pdp: number[];
  max_violation: number;
}

export interface GbmDetails {
  engine: string;
  rounds: number;
  constraints: Record<string, number>;
  categorical_codes: Record<string, Record<string, number>>;
  params: Record<string, unknown>;
  monotonicity: { rows: number; features: Record<string, MonotonicityFeature>; monotone: boolean };
}

// --- CONTRACT 1: the ingestion families (data/derived/contract/) -------------------------------------------------

export type ContractField = components['schemas']['contractField'];

export type ContractRule = components['schemas']['contractRule'];

export type ContractParam = components['schemas']['contractParam'];

export type FamilyContract = components['schemas']['common-contract-family'];

export type ContractIndex = components['schemas']['common-contract-index'];

export const CONTRACT_SCHEMA = 'contraste.contract/v1';

export const CONTRACT_FIELD = {
  name: 'string',
  kind: 'string',
  meaning: 'text',
  unit: 'string',
  lo: nNum,
  hi: nNum,
  lo_open: 'boolean',
  hi_open: 'boolean',
  values: { array: 'string' },
  values_param: nStr,
  required: 'boolean',
  on_missing: 'string',
  expected: 'string',
} satisfies Record<keyof ContractField, Kind>;

export const CONTRACT_RULE = {
  id: 'string',
  scope: 'string',
  policy: 'string',
  field: 'string',
  statement: 'text',
  group_by: { array: 'string' },
  order_by: nStr,
} satisfies Record<keyof ContractRule, Kind>;

export const CONTRACT_PARAM = {
  name: 'string',
  kind: 'string',
  meaning: 'text',
  required: 'boolean',
  values: { array: 'string' },
} satisfies Record<keyof ContractParam, Kind>;

export const FAMILY_CONTRACT = {
  schema: 'string',
  family: 'string',
  title: 'text',
  used_by: 'text',
  fields: { array: { object: CONTRACT_FIELD } },
  rules: { array: { object: CONTRACT_RULE } },
  params: { array: { object: CONTRACT_PARAM } },
  open_fields: 'boolean',
  notes: { array: 'text' },
  param_checks: { array: 'text' },
} satisfies Record<keyof FamilyContract, Kind>;

export const CONTRACT_INDEX = {
  schema: 'string',
  families: { array: { object: { family: 'string', title: 'text', path: 'string' } } },
} satisfies Record<keyof ContractIndex, Kind>;

// --- C05, low-default portfolios and PD calibration (data-pipeline/pipeline/cases/c05_ldp_calibration.py) --------

export type C05Irb = components['schemas']['c05Irb'];

export type C05IrbPoint = components['schemas']['c05IrbPoint'];

export type C05Approach = components['schemas']['c05Approach'];

export type C05GoldenCell = components['schemas']['c05GoldenCell'];

export type C05SpGolden = components['schemas']['c05SpGolden'];

export type C05SpOutputs = components['schemas']['c05SpOutputs'];

export type C05Scaled = components['schemas']['c05Scaled'];

export type C05Bounds = components['schemas']['c05Bounds'];

export type C05CoverageRow = components['schemas']['c05CoverageRow'];

export type C05KnownTruth = components['schemas']['c05KnownTruth'];

export type C05LdpGoldenCell = components['schemas']['c05LdpGoldenCell'];

export type C05LdpOutputs = components['schemas']['c05LdpOutputs'];

export type C05SpFit = components['schemas']['c05SpFit'];

export type C05LdpFit = components['schemas']['c05LdpFit'];

const C05_IRB = {
  regime: 'string',
  asset_class: 'string',
  lgd: num,
  maturity: num,
  pd_floor: num,
  references: { map: 'string' },
} satisfies Record<keyof C05Irb, Kind>;

const C05_IRB_POINTS = {
  array: {
    object: { regime: 'string', asset_class: 'string', pd: num, lgd: num, maturity: num, risk_weight: num } satisfies Record<keyof C05IrbPoint, Kind>,
  },
} as const;

const C05_CELLS = {
  array: { object: { grade: 'string', printed: num, ours: num, gap: num } satisfies Record<keyof C05GoldenCell, Kind> },
} as const;

export const C05_SP_OUTPUTS = {
  kind: 'string',
  year: 'integer',
  grades: { array: 'string' },
  profile0: nums,
  profile1: nums,
  default_rate0: nums,
  default_rate1: nums,
  default_profile0: nums,
  pd0: num,
  pd1: num,
  ar0: num,
  ar1: num,
  qmm0: { object: { curve: nums, alpha: num, beta: num, scores: nums, start: nums, pd: num } },
  approaches: {
    map: {
      object: { curve: nums, pd: num, pd_under_profile1: num, accuracy_ratio: num, constants: { map: num } } satisfies Record<keyof C05Approach, Kind>,
    },
  },
  case3_profile_tests: { map: { object: { statistic: num, dof: 'integer', p_value: num } } },
  golden: {
    object: {
      table5: C05_CELLS,
      table6: C05_CELLS,
      table7: { map: C05_CELLS },
      table7_p_values: { array: { object: { approach: 'string', printed_pct: num, ours_pct: num, mc_se_pct: num } } },
      table8: { array: { object: { approach: 'string', printed_pct: num, ours_pct: num, printed_p_value: 'string' } } },
      table9_2009: { array: { object: { grade: 'string', printed: num, ours: num } } },
      max_gap_table7_pct_beyond_relative: num,
      tolerances: { map: 'string' },
    } satisfies Record<keyof C05SpGolden, Kind>,
  },
  parity: { object: { calibration: { object: { pd_grid: nums, curves: { map: { map: nums } } } }, irb: C05_IRB_POINTS } },
  irb: { object: C05_IRB },
  n_obligors: 'integer',
  n_defaults: 'integer',
} satisfies Record<keyof C05SpOutputs, Kind>;

const C05_SCALED = { array: { object: { pd: nums, k: num, target: num } satisfies Record<keyof C05Scaled, Kind> } } as const;
const C05_COVERAGE_ROWS = {
  array: {
    object: { gamma: num, coverage: num, se: num, ratio_q25: num, ratio_median: num, ratio_q75: num } satisfies Record<keyof C05CoverageRow, Kind>,
  },
} as const;

export const C05_LDP_OUTPUTS = {
  kind: 'string',
  grades: { array: 'string' },
  obligors: { array: 'integer' },
  defaults: { array: 'integer' },
  gammas: nums,
  expert_pd: nums,
  true_pd: { nullable: nums },
  rho: num,
  bounds: {
    object: {
      independent: { array: nums },
      correlated: { array: nums },
      scaled_upper_bound: C05_SCALED,
      scaled_upper_bound_correlated: C05_SCALED,
      scaled_central_tendency: C05_SCALED,
    } satisfies Record<keyof C05Bounds, Kind>,
  },
  irb: { object: C05_IRB },
  parity: {
    object: {
      bounds: {
        object: {
          obligors: { array: 'integer' },
          points: { array: { object: { defaults: { array: 'integer' }, gamma: num, rho: num, pd: nums, scaled_upper_bound: nums } } },
        },
      },
      irb: C05_IRB_POINTS,
    },
  },
  known_truth: {
    nullable: {
      object: {
        years: 'integer',
        coverage: { map: { map: C05_COVERAGE_ROWS } },
        tests: { map: { map: { object: { reject_5: num, reject_1: num } } } },
        patterns: 'integer',
        overdispersion: { object: { variance_simulated: num, variance_model: num, variance_independent: num, rho_moment_estimate: num } },
        total_defaults_histogram: { array: 'integer' },
        total_defaults_tail: 'integer',
        share_of_defaults_by_grade: nums,
      } satisfies Record<keyof C05KnownTruth, Kind>,
    },
  },
  golden: {
    nullable: {
      object: {
        cells: {
          array: {
            object: { table: 'integer', row: 'string', gamma: num, printed: num, ours: num, gap: num } satisfies Record<keyof C05LdpGoldenCell, Kind>,
          },
        },
        notes: { map: 'string' },
      },
    },
  },
  generated_year: { nullable: { object: { index: 'integer', factor: num } } },
} satisfies Record<keyof C05LdpOutputs, Kind>;

export const VARIANT_C05_SP = { ...VARIANT, outputs: { object: C05_SP_OUTPUTS } } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C05_LDP = { ...VARIANT, outputs: { object: C05_LDP_OUTPUTS } } satisfies Record<keyof VariantArtifact, Kind>;

export const MODELS_C05_SP = {
  ...MODELS,
  fit: { object: { estimation_year: 'integer', targets: { object: { pd: num, accuracy_ratio: num } } } satisfies Record<keyof C05SpFit, Kind> },
} satisfies Record<keyof ModelsArtifact, Kind>;
export const MODELS_C05_LDP = {
  ...MODELS,
  fit: { object: { obligors: { array: 'integer' }, expert_pd: nums } satisfies Record<keyof C05LdpFit, Kind> },
} satisfies Record<keyof ModelsArtifact, Kind>;

// --- C22, validating the validator (data-pipeline/pipeline/cases/c22_validator.py) -----------------------------------

/** One rejection rate of the harness: rejections of n repetitions, its Monte Carlo SE and Wilson interval. */
export type C22Rate = components['schemas']['c22Rate'];

/** One simulation: a registered test on one generator at one severity, its rates per rule ("p<0.05", "p<0.01", and
 * rules such as "metric>0.1"), the exact probability where one exists and whether the rate agrees with it. */
export type C22Simulation = components['schemas']['c22Simulation'];

export type C22Generator = components['schemas']['c22Generator'];

export type C22GoldenCell = components['schemas']['c22GoldenCell'];

export type C22Golden = components['schemas']['c22Golden'];

export type C22Curve = components['schemas']['c22Curve'];

export type C22Outputs = components['schemas']['c22Outputs'];

/** A point of the count tests' exact rejection probability, for the live calculator's parity (CT-308). */
export type C22Parity = components['schemas']['c22Parity'];

export type C22Fit = components['schemas']['c22Fit'];

/** The engine's named study behind a simulation of a test outside the five credit families (U16-P2); null for the credit
 * families' simulations. */
export type C22Study = components['schemas']['c22Study'];

/** A size above its bound that the engine documents on its own page. */
export type C22Excess = components['schemas']['c22Excess'];

/** One named study of the engine, as the models artifact records it. */
export type C22StudyRecord = components['schemas']['c22StudyRecord'];

const C22_RATE = {
  object: { rejections: 'integer', n: 'integer', undefined: 'integer', rate: num, se: num, wilson_low: num, wilson_high: num } satisfies Record<
    keyof C22Rate,
    Kind
  >,
} as const;

const C22_STUDY = {
  object: {
    index: 'integer',
    label: 'text',
    rule: 'string',
    rule_label: 'string',
    arm: 'string',
    text: 'text',
    departure: 'string',
    excess: {
      nullable: {
        object: { page: 'string', repository: 'string', level: num, measured: num, bound: num, excess: num, exceeds: 'boolean', engine: 'text' } satisfies Record<
          keyof C22Excess,
          Kind
        >,
      },
    },
  } satisfies Record<keyof C22Study, Kind>,
} as const;

export const C22_OUTPUTS = {
  kind: 'string',
  family: 'string',
  ladder: { nullable: { object: { values: nums, label: 'text' } } },
  levels: nums,
  panels: { array: { object: { id: 'string', label: 'text', axis: { nullable: 'text' }, measures: 'string' } } },
  simulations: {
    array: {
      object: {
        key: 'string',
        test_id: 'string',
        label: 'text',
        scenario: 'text',
        panel: 'string',
        severity: 'integer',
        x: num,
        rates: { map: C22_RATE },
        exact: { nullable: { map: num } },
        agrees: { nullable: { map: 'boolean' } },
        p_histogram: { nullable: { array: 'integer' } },
        seed: 'integer',
        n_rep: 'integer',
        generator: 'string',
        study: { nullable: C22_STUDY },
      } satisfies Record<keyof C22Simulation, Kind>,
    },
  },
  generators: { map: { object: { name: 'string', config: 'json', truth: 'json' } satisfies Record<keyof C22Generator, Kind> } },
  golden: {
    array: {
      object: {
        study: 'string',
        title: 'text',
        runs_published: 'integer',
        runs: 'integer',
        cells: {
          array: {
            object: { table: 'string', row: 'string', column: 'string', published: num, measured: num, z: nNum, agrees: 'boolean' } satisfies Record<
              keyof C22GoldenCell,
              Kind
            >,
          },
        },
        agree: 'integer',
        total: 'integer',
        note: 'text',
      } satisfies Record<keyof C22Golden, Kind>,
    },
  },
  exact_curves: {
    array: {
      object: {
        id: 'string',
        label: 'text',
        x_label: 'text',
        y_label: 'text',
        x: nums,
        series: { array: { object: { id: 'string', label: 'text', y: { array: { nullable: 'number' } } } } },
      } satisfies Record<keyof C22Curve, Kind>,
    },
  },
  estimators: { nullable: { object: { auc: { map: num }, ece_when_right: { map: num } } } },
  specimen: { object: { severity: 'integer' } },
  size_bounds: { map: num },
} satisfies Record<keyof C22Outputs, Kind>;

export const VARIANT_C22 = { ...VARIANT, outputs: { object: C22_OUTPUTS } } satisfies Record<keyof VariantArtifact, Kind>;

export const MODELS_C22 = {
  ...MODELS,
  fit: {
    object: {
      parity: {
        array: {
          object: {
            test_id: 'string',
            n: 'integer',
            pd: num,
            ratio: num,
            rho_true: num,
            rho_assumed: nNum,
            alpha: num,
            critical_count: nInt,
            probability: num,
          } satisfies Record<keyof C22Parity, Kind>,
        },
      },
      levels: nums,
      studies: {
        array: {
          object: {
            test_id: 'string',
            index: 'integer',
            label: 'text',
            rule: 'string',
            null_generator: 'string',
            alternative_generator: 'string',
            pipeline: { nullable: 'string' },
            test_kwargs: 'json',
            engine_n_rep: 'integer',
            engine_power_n_rep: nInt,
            engine_seed: 'integer',
            engine_power_seed: 'integer',
          } satisfies Record<keyof C22StudyRecord, Kind>,
        },
      },
    } satisfies Record<keyof C22Fit, Kind>,
  },
} satisfies Record<keyof ModelsArtifact, Kind>;

// --- C04, rating transitions and TTC PD by grade (data-pipeline/pipeline/cases/c04_transitions.py; contract in ------
// docs/design/features/c04-transitions/contract.md, sections 1 to 4) -------------------------------------------------

const nNums = { array: nNum } as const;
const numss = { array: nums } as const;
const ints = { array: 'integer' } as const;

/** One CEREP cohort on the common scale: tab 4's counts (seven grades by seven grades and default), withdrawals and
 * sizes; tab 2's defaulted ratings over its own cohort; tab 3's events. Semester cohorts have no tab 2 or tab 3. */
export type C04Cohort = components['schemas']['c04Cohort'];
const C04_COHORT = {
  object: {
    label: 'string',
    begin: 'string',
    end: 'string',
    size: ints,
    counts: { array: ints },
    withdrawn: ints,
    defaulted: { nullable: ints },
    events: { nullable: ints },
    defaulted_cohort: { nullable: ints },
    tab2_gap: nNum,
  } satisfies Record<keyof C04Cohort, Kind>,
} as const;

/** None for a grade without ratings, and for tab 3's events where they outnumber the cohort. */
export type C04Bounds = components['schemas']['c04Bounds'];
const C04_BOUNDS = { object: { lower: nNums, upper: nNums } satisfies Record<keyof C04Bounds, Kind> } as const;

/** The long-run average default rate by grade (EBA/GL/2017/16 paragraph 84) under one definition. */
export type C04Lra = components['schemas']['c04Lra'];
const C04_LRA = {
  object: {
    rate: nNums,
    cohorts: ints,
    defaults: ints,
    n: ints,
    pooled_rate: nNums,
    wald: C04_BOUNDS,
    agresti_coull: C04_BOUNDS,
    jeffreys: C04_BOUNDS,
    last5: nNums,
  } satisfies Record<keyof C04Lra, Kind>,
} as const;

/** A generator of the pooled matrix: its rates, its L1 distance to the matrix, its PDs at one and five years (null by
 * grade where the scale has no default category, Moody's). */
export type C04Generator = components['schemas']['c04Generator'];
export type C04EmGenerator = components['schemas']['c04EmGenerator'];
const C04_GENERATOR_BASE = { generator: numss, valid: 'boolean', l1: nNum, pd_1y: nNums, pd_5y: nNums } satisfies Record<keyof C04Generator, Kind>;
const C04_GENERATOR = { nullable: { object: C04_GENERATOR_BASE } } as const;
const C04_EM_GENERATOR = {
  object: { ...C04_GENERATOR_BASE, iterations: 'integer', converged: 'boolean', loglik: nNum } satisfies Record<keyof C04EmGenerator, Kind>,
} as const;

export type C04Embedding = components['schemas']['c04Embedding'];

export type C04Homogeneity = components['schemas']['c04Homogeneity'];
const C04_HOMOGENEITY = { object: { statistic: nNum, p_value: nNum, dof: 'integer', periods: 'integer' } satisfies Record<keyof C04Homogeneity, Kind> } as const;

export type C04ReferenceTest = components['schemas']['c04ReferenceTest'];

/** One five-year window of the lifetime check (CT-415): the fixed cohort observed at the window's end against the
 * chained one-year projections; a value is null where the chain or the definition does not exist. */
export type C04Lifetime = components['schemas']['c04Lifetime'];

export type C04Irb = components['schemas']['c04Irb'];

export type C04Definition = 'd2' | 'd3' | 'd4' | 'keep';

export type C04AgencyOutputs = components['schemas']['c04AgencyOutputs'];

const nNumGrid = { nullable: { array: nNums } } as const;
export const C04_AGENCY_OUTPUTS = {
  kind: 'string',
  agency: { object: { code: 'string', name: 'string', scope: 'string' } },
  attribution: 'string',
  grades: { array: 'string' },
  states: { array: 'string' },
  cohorts: { array: C04_COHORT },
  semesters: { array: C04_COHORT },
  pd: { object: { d2: nNumGrid, d3: nNumGrid, d4: nNumGrid, keep: nNumGrid } satisfies Record<C04Definition, Kind> },
  lra: { object: { d2: C04_LRA, d3: C04_LRA, d4: { nullable: C04_LRA } } },
  pooled: {
    object: { matrix: numss, matrix_state: numss, counts: { array: ints }, withdrawn: ints, row_sizes: ints, cohorts: 'integer' },
  },
  embedding: {
    object: {
      S: nNum,
      series_converges: 'boolean',
      det: nNum,
      prod_diagonal: nNum,
      theorem3: { object: { a: 'boolean', b: 'boolean', c: { array: ints } } },
      exact_generator_excluded: 'boolean',
      stochastically_monotone: 'boolean',
      monotonicity_violations: { array: { object: { row: 'integer', next_row: 'integer', column: 'integer', tail: nNum, next_tail: nNum } } },
    } satisfies Record<keyof C04Embedding, Kind>,
  },
  generators: {
    object: { diagonal: C04_GENERATOR, weighted: C04_GENERATOR, jlt: C04_GENERATOR, em: C04_EM_GENERATOR, cohort_power: { object: { pd_5y: nNums } } },
  },
  mobility: { object: { labels: { array: 'string' }, svd: nNums, trace: nNums, spec_default_rate: nNums } },
  ecb: { array: { object: { label: 'string', mwb_upper: nNum, mwb_lower: nNum, ztests_p: nNum } } },
  homogeneity: {
    object: {
      annual: C04_HOMOGENEITY,
      semesters: { nullable: C04_HOMOGENEITY },
      reference: {
        array: {
          object: { label: 'string', statistic: nNum, p_value: nNum, dof: 'integer', impossible_moves: { array: ints } } satisfies Record<keyof C04ReferenceTest, Kind>,
        },
      },
    },
  },
  semesters_vs_year: { array: { object: { year: 'integer', l1: nNum, pd_product: nNums, pd_annual: nNums } } },
  definition_gap: { object: { d4_over_d2: { nullable: nNums }, d3_over_d2: { nullable: nNums } } },
  lifetime: {
    array: {
      object: {
        label: 'string',
        first: 'integer',
        last: 'integer',
        size: ints,
        observed: { object: { default_end: nNums, withdrawn_end: nNums, cumulative_d2: { nullable: nNums } } },
        projected: { object: { chain_state: nNums, chain_state_withdrawn: nNums, chain_exclude: nNums, pooled_power: nNums, em: nNums } },
      } satisfies Record<keyof C04Lifetime, Kind>,
    },
  },
  origination: nums,
  irb: {
    object: { regime: 'string', asset_class: 'string', lgd: num, maturity: num, pd_floor: num, references: { map: 'string' } } satisfies Record<keyof C04Irb, Kind>,
  },
} satisfies Record<keyof C04AgencyOutputs, Kind>;

/** A harness rate: rejections (or hits) over n repetitions with its Monte Carlo SE and Wilson interval. */
export type C04Rate = components['schemas']['c04Rate'];
const C04_RATE = {
  object: { rejections: 'integer', n: 'integer', undefined: 'integer', rate: num, se: num, wilson_low: num, wilson_high: num } satisfies Record<keyof C04Rate, Kind>,
} as const;

/** riskvalidation's estimator performance of a quantity by grade (Morris et al. 2019, Table 6): null by grade where
 * fewer than two repetitions are defined. */
export type C04Performance = components['schemas']['c04Performance'];
const C04_PERFORMANCE_BASE = {
  n: ints,
  truth: nums,
  mean: nNums,
  bias: nNums,
  bias_mcse: nNums,
  empirical_se: nNums,
  empirical_se_mcse: nNums,
  rmse: nNums,
  rmse_mcse: nNums,
} satisfies Record<keyof C04Performance, Kind>;
const C04_PERFORMANCE = { object: C04_PERFORMANCE_BASE } as const;

/** The same for one quantity per repetition (the momentum hazard's fitted coefficient). */
export type C04ScalarPerformance = components['schemas']['c04ScalarPerformance'];

export type C04MarkovRung = components['schemas']['c04MarkovRung'];
export type C04MomentumRung = components['schemas']['c04MomentumRung'];
export type C04CycleRung = components['schemas']['c04CycleRung'];
export type C04WithdrawalsRung = components['schemas']['c04WithdrawalsRung'];
export type C04ThinRung = components['schemas']['c04ThinRung'];
export type C04Rung = C04MarkovRung | C04MomentumRung | C04CycleRung | C04WithdrawalsRung | C04ThinRung;

export type C04Simulation = components['schemas']['c04Simulation'];

export type C04Family = components['schemas']['c04FamilyOutputs']['family'];

export type C04FamilyOutputs = components['schemas']['c04FamilyOutputs'];

const C04_RATES = { array: C04_RATE } as const;
const C04_THREE = (k: Kind) => ({ object: { wald: k, agresti_coull: k, jeffreys: k } }) as const;
const C04_MARKOV_RUNG = {
  object: {
    value: { nullable: num },
    seed_key: 'string',
    seed: 'integer',
    level: num,
    obligor_years: nums,
    estimators: { map: { object: { ...C04_PERFORMANCE_BASE, zero: C04_RATES } } },
    em: { object: { converged: C04_RATE, iterations_mean: num, iterations_max: 'integer' } },
    coverage: { object: { wald: C04_RATES, agresti_coull: C04_RATES, jeffreys: C04_RATES, bootstrap: C04_RATES } },
    bootstrap: { object: { method: 'string', estimate: 'string', horizon: num, n_boot: 'integer', repetitions: 'integer' } },
  } satisfies Record<keyof C04MarkovRung, Kind>,
} as const;
const C04_MOMENTUM_RUNG = {
  object: {
    value: num,
    seed_key: 'string',
    seed: 'integer',
    momentum: { nullable: numss },
    investment_grades: 'integer',
    coefficient: {
      nullable: {
        object: {
          n: 'integer',
          truth: num,
          mean: num,
          bias: num,
          bias_mcse: num,
          empirical_se: num,
          empirical_se_mcse: num,
          mse: num,
          mse_mcse: num,
          rmse: num,
          rmse_mcse: num,
        } satisfies Record<keyof C04ScalarPerformance, Kind>,
      },
    },
    pd_1y_cohort: C04_PERFORMANCE,
    pd_5y_frequency: C04_PERFORMANCE,
    pd_5y_cohort_power: C04_PERFORMANCE,
    pd_5y_duration: C04_PERFORMANCE,
    error_cohort_power: C04_PERFORMANCE,
    error_duration: C04_PERFORMANCE,
  } satisfies Record<keyof C04MomentumRung, Kind>,
} as const;
const C04_CYCLE_RUNG = {
  object: {
    value: num,
    seed_key: 'string',
    seed: 'integer',
    stressed_period: { nullable: nums },
    pd_true_base: nums,
    pd_true_stressed: nums,
    pd_true_average: nums,
    pd_stressed_year: C04_PERFORMANCE,
    pd_lra: C04_PERFORMANCE,
    pd_pooled: C04_PERFORMANCE,
  } satisfies Record<keyof C04CycleRung, Kind>,
} as const;
const C04_WITHDRAWALS_RUNG = {
  object: {
    value: num,
    seed_key: 'string',
    seed: 'integer',
    withdrawal_rate: num,
    window: num,
    truncation_verified: 'integer',
    withdrawn_obligors_mean: num,
    withdrawn_share: { object: { n: ints, mean: nNums, mean_mcse: nNums } },
    pd_removed: C04_PERFORMANCE,
    pd_kept: C04_PERFORMANCE,
    pd_followed: C04_PERFORMANCE,
    pd_latent: C04_PERFORMANCE,
  } satisfies Record<keyof C04WithdrawalsRung, Kind>,
} as const;
const C04_THIN_RUNG = {
  object: {
    value: 'integer',
    level: num,
    expected_defaults: nums,
    coverage: C04_THREE(nums),
    length: C04_THREE(nums),
    overlap_jeffreys: nums,
  } satisfies Record<keyof C04ThinRung, Kind>,
} as const;

export const C04_FAMILY_OUTPUTS = {
  kind: 'string',
  family: 'string',
  generator: { object: { q: numss, pd_1y: nums, pd_5y: nums, obligors: ints, source: 'string', one_year_matrix: numss } },
  design: { object: { years: 'integer', snapshots: nums, reps: 'integer', seed_key: nStr } },
  ladder: { nullable: { object: { name: 'text', unit: 'string', values: nums } } },
  rungs: { array: { anyOf: [C04_MARKOV_RUNG, C04_MOMENTUM_RUNG, C04_CYCLE_RUNG, C04_WITHDRAWALS_RUNG, C04_THIN_RUNG] } },
  simulations: {
    array: {
      object: { key: 'string', test_id: 'string', rung: nNum, rates: { map: C04_RATE }, seed: 'integer', n_rep: 'integer' } satisfies Record<keyof C04Simulation, Kind>,
    },
  },
} satisfies Record<keyof C04FamilyOutputs, Kind>;

/** A printed value beside its recomputation; the bake stops unless they agree (contract section 3). */
export type C04Print = components['schemas']['c04Print'];
const C04_PRINT = { object: { printed: num, recomputed: num, decimals: 'integer' } satisfies Record<keyof C04Print, Kind> } as const;
const C04_PRINTS = { object: { printed: nums, recomputed: nums, decimals: ints } } as const;

export type C04PublishedOutputs = components['schemas']['c04PublishedOutputs'];
export const C04_PUBLISHED_OUTPUTS = {
  kind: 'string',
  irw: {
    object: {
      rows: { array: { object: { matrix: 'string', method: 'string', printed: num, recomputed: num, agrees: 'boolean' } } },
      jlt_from_printed_generator: num,
      theorem3_c: { array: 'boolean' },
      series_terms: 'integer',
    },
  },
  sr190: {
    object: {
      defaults: 'integer',
      n: 'integer',
      rows: { array: { object: { rho: num, interval: 'string', printed: nums, recomputed: nums, agrees: 'boolean' } } },
      n_dagger: C04_PRINTS,
    },
  },
  engelmann: {
    object: {
      w_ttc: C04_PRINTS,
      ttc_pd: C04_PRINT,
      portfolios: {
        array: {
          object: {
            name: 'string',
            w0: nums,
            pd0: { object: { printed: num, recomputed: num, decimals: 'integer', check: 'string', note: { nullable: 'text' } } },
            extreme: { nullable: { object: { kind: 'string', printed: num, recomputed: num, decimals: 'integer' } } },
            pd_path: nums,
          },
        },
      },
      row_sum_deviation: num,
    },
  },
} satisfies Record<keyof C04PublishedOutputs, Kind>;

export const VARIANT_C04_AGENCY = { ...VARIANT, outputs: { object: C04_AGENCY_OUTPUTS } } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C04_FAMILY = { ...VARIANT, outputs: { object: C04_FAMILY_OUTPUTS } } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C04_PUBLISHED = { ...VARIANT, outputs: { object: C04_PUBLISHED_OUTPUTS } } satisfies Record<keyof VariantArtifact, Kind>;

/** The live parity of C04's models artifact (contract section 4), and the families' generator. */
export type C04ProjectionPoint = components['schemas']['c04ProjectionPoint'];
export type C04IntervalPoint = components['schemas']['c04IntervalPoint'];
export type C04CapitalPoint = components['schemas']['c04CapitalPoint'];
export type C04Fit = components['schemas']['c04Fit'];
export const MODELS_C04 = {
  ...MODELS,
  fit: {
    object: {
      parity: {
        object: {
          projection: {
            array: {
              object: {
                agency: 'string',
                matrix: numss,
                origination: nums,
                w0: nums,
                years: 'integer',
                default_rate: nums,
                portfolio_last: nums,
                ttc: nums,
                ttc_default_rate: num,
              } satisfies Record<keyof C04ProjectionPoint, Kind>,
            },
          },
          intervals: {
            array: {
              object: {
                defaults: 'integer',
                n: 'integer',
                rho: num,
                level: num,
                wald: nums,
                agresti_coull: nums,
                jeffreys: nums,
                n_effective: num,
              } satisfies Record<keyof C04IntervalPoint, Kind>,
            },
          },
          capital: {
            array: {
              object: { pd: num, lgd: num, maturity: num, regime: 'string', asset_class: 'string', risk_weight: num } satisfies Record<keyof C04CapitalPoint, Kind>,
            },
          },
        },
      },
      generator: { object: { q: numss, obligors: ints, source: 'string' } },
    } satisfies Record<keyof C04Fit, Kind>,
  },
} satisfies Record<keyof ModelsArtifact, Kind>;

// --- C06 and C07 (U5-W): the descriptors live beside the instruments that read them -----------------------------------
export const VARIANT_C06 = { ...VARIANT, outputs: C06_OUTPUTS } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C07 = { ...VARIANT, outputs: C07_OUTPUTS } satisfies Record<keyof VariantArtifact, Kind>;
// The partial-key oneOf rows of the U6 variant schemas (vintage rows, CCF rows, floor cells, EAD models) have no descriptor
// form, so each case declares those nodes `json` and its `tests` open (the descriptor files say which).
export const VARIANT_C03 = { ...VARIANT, outputs: C03_OUTPUTS, tests: 'json' as Kind } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C08 = { ...VARIANT, outputs: C08_OUTPUTS, tests: 'json' as Kind } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C09 = { ...VARIANT, outputs: C09_OUTPUTS, tests: 'json' as Kind } satisfies Record<keyof VariantArtifact, Kind>;
export const MODELS_C03 = { ...MODELS, fit: C03_FIT } satisfies Record<keyof ModelsArtifact, Kind>;
export const MODELS_C08 = { ...MODELS, fit: C08_FIT } satisfies Record<keyof ModelsArtifact, Kind>;
export const MODELS_C09 = { ...MODELS, fit: C09_FIT } satisfies Record<keyof ModelsArtifact, Kind>;
export const MODELS_C06 = { ...MODELS, fit: C06_FIT } satisfies Record<keyof ModelsArtifact, Kind>;
export const MODELS_C07 = { ...MODELS, fit: C07_FIT } satisfies Record<keyof ModelsArtifact, Kind>;
// --- wave 2 batch 2 (U7, U8, U10, U12 views): the C10 and C17 schemas narrow provenance.truth_status in an allOf branch; their
// documents carry the full provenance block, so the descriptor declares all of it; the others open their tests ----
export const VARIANT_C10_LOAN_TYPE = { ...VARIANT, outputs: C10_OUTPUTS_LOAN_TYPE, tests: 'json' as Kind, provenance: { object: PROVENANCE } } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C10_GRID = { ...VARIANT, outputs: C10_OUTPUTS_GRID, tests: 'json' as Kind, provenance: { object: PROVENANCE } } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C11 = { ...VARIANT, outputs: C11_OUTPUTS, tests: 'json' as Kind } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C12 = { ...VARIANT, outputs: C12_OUTPUTS, tests: 'json' as Kind } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C13 = { ...VARIANT, outputs: C13_OUTPUTS, tests: 'json' as Kind } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C14 = { ...VARIANT, outputs: C14_OUTPUTS, tests: 'json' as Kind } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C15 = { ...VARIANT, outputs: C15_OUTPUTS, tests: 'json' as Kind } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C16_SCENARIO = { ...VARIANT, outputs: C16_OUTPUTS, tests: 'json' as Kind } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C16_REVERSE = { ...VARIANT, outputs: C16_OUTPUTS_REVERSE, tests: 'json' as Kind } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C17 = { ...VARIANT, outputs: C17_OUTPUTS, tests: 'json' as Kind, provenance: { object: PROVENANCE } } satisfies Record<keyof VariantArtifact, Kind>;
// C18 (U13-W): its scenario variants carry outputs.kind 'scenario' like C16's, so variantKind reads the document's case_id first
export const VARIANT_C18_SCENARIO = { ...VARIANT, outputs: C18_OUTPUTS, tests: 'json' as Kind, provenance: { object: PROVENANCE } } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C18_AGGREGATION = { ...VARIANT, outputs: C18_OUTPUTS_AGGREGATION, tests: 'json' as Kind, provenance: { object: PROVENANCE } } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C18_REVERSE = { ...VARIANT, outputs: C18_OUTPUTS_REVERSE, tests: 'json' as Kind, provenance: { object: PROVENANCE } } satisfies Record<keyof VariantArtifact, Kind>;
export const MODELS_C10 = { ...MODELS, fit: C10_FIT, provenance: { object: PROVENANCE } } satisfies Record<keyof ModelsArtifact, Kind>;
export const MODELS_C11 = { ...MODELS, fit: C11_FIT } satisfies Record<keyof ModelsArtifact, Kind>;
export const MODELS_C12 = { ...MODELS, fit: C12_FIT } satisfies Record<keyof ModelsArtifact, Kind>;
export const MODELS_C13 = { ...MODELS, fit: C13_FIT } satisfies Record<keyof ModelsArtifact, Kind>;
export const MODELS_C14 = { ...MODELS, fit: C14_FIT } satisfies Record<keyof ModelsArtifact, Kind>;
export const MODELS_C15 = { ...MODELS, fit: C15_FIT } satisfies Record<keyof ModelsArtifact, Kind>;
export const MODELS_C16 = { ...MODELS, fit: C16_FIT } satisfies Record<keyof ModelsArtifact, Kind>;
export const MODELS_C18 = { ...MODELS, fit: C18_FIT, provenance: { object: PROVENANCE } } satisfies Record<keyof ModelsArtifact, Kind>;
// --- wave 2 batch 3 (U14-W views): C02, C20 and C21; the C21 outputs are a oneOf over the year pairs, so `json` (its descriptor head says why) ---
export const VARIANT_C02 = { ...VARIANT, outputs: C02_OUTPUTS, tests: 'json' as Kind } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C20_SHOCK = { ...VARIANT, outputs: C20_OUTPUTS, tests: 'json' as Kind } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C20_SHIFT = { ...VARIANT, outputs: C20_OUTPUTS_SHIFT, tests: 'json' as Kind } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C20_SEEDS = { ...VARIANT, outputs: C20_OUTPUTS_SEEDS, tests: 'json' as Kind } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C20_PERTURBATION = { ...VARIANT, outputs: C20_OUTPUTS_PERTURBATION, tests: 'json' as Kind } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C20_LEAKAGE = { ...VARIANT, outputs: C20_OUTPUTS_LEAKAGE, tests: 'json' as Kind } satisfies Record<keyof VariantArtifact, Kind>;
export const VARIANT_C21 = { ...VARIANT, outputs: C21_OUTPUTS, tests: 'json' as Kind } satisfies Record<keyof VariantArtifact, Kind>;
export const MODELS_C02 = { ...MODELS, fit: C02_FIT } satisfies Record<keyof ModelsArtifact, Kind>;
export const MODELS_C20 = { ...MODELS, fit: C20_FIT } satisfies Record<keyof ModelsArtifact, Kind>;
export const MODELS_C21 = { ...MODELS, fit: C21_FIT } satisfies Record<keyof ModelsArtifact, Kind>;
export const MODELS_C17 = { ...MODELS, fit: C17_FIT, provenance: { object: PROVENANCE } } satisfies Record<keyof ModelsArtifact, Kind>;

/** The variant descriptor an artifact is read against: by its outputs' kind (C04, C05, C06, C07, C22) or C01's. */
export function variantKind(doc: {
  case_id?: string;
  outputs?: { kind?: string };
}):
  | typeof VARIANT
  | typeof VARIANT_C04_AGENCY
  | typeof VARIANT_C04_FAMILY
  | typeof VARIANT_C04_PUBLISHED
  | typeof VARIANT_C05_SP
  | typeof VARIANT_C05_LDP
  | typeof VARIANT_C06
  | typeof VARIANT_C07
  | typeof VARIANT_C03
  | typeof VARIANT_C08
  | typeof VARIANT_C09
  | typeof VARIANT_C10_LOAN_TYPE
  | typeof VARIANT_C10_GRID
  | typeof VARIANT_C11
  | typeof VARIANT_C12
  | typeof VARIANT_C13
  | typeof VARIANT_C14
  | typeof VARIANT_C15
  | typeof VARIANT_C16_SCENARIO
  | typeof VARIANT_C16_REVERSE
  | typeof VARIANT_C17
  | typeof VARIANT_C18_SCENARIO
  | typeof VARIANT_C18_AGGREGATION
  | typeof VARIANT_C18_REVERSE
  | typeof VARIANT_C02
  | typeof VARIANT_C20_SHOCK
  | typeof VARIANT_C20_SHIFT
  | typeof VARIANT_C20_SEEDS
  | typeof VARIANT_C20_PERTURBATION
  | typeof VARIANT_C20_LEAKAGE
  | typeof VARIANT_C21
  | typeof VARIANT_C22 {
  const kind = doc.outputs?.kind;
  if (doc.case_id === 'C18') return kind === 'aggregation' ? VARIANT_C18_AGGREGATION : kind === 'reverse' ? VARIANT_C18_REVERSE : VARIANT_C18_SCENARIO;
  if (kind === 'agency') return VARIANT_C04_AGENCY;
  if (kind === 'generator') return VARIANT_C04_FAMILY;
  if (kind === 'published') return VARIANT_C04_PUBLISHED;
  if (kind === 'reporting-date') return VARIANT_C06;
  if (kind === 'three-regime') return VARIANT_C07;
  if (kind === 'vintage-cohort') return VARIANT_C03;
  if (kind === 'default-cohort') return VARIANT_C08;
  if (kind === 'acceleration-level') return VARIANT_C09;
  if (kind === 'loan-type') return VARIANT_C10_LOAN_TYPE;
  if (kind === 'correlation-grid') return VARIANT_C10_GRID;
  if (kind === 'window') return VARIANT_C11;
  if (kind === 'swap-exposure') return VARIANT_C12;
  if (kind === 'deficiency') return VARIANT_C13;
  if (kind === 'valuation-date') return VARIANT_C14;
  if (kind === 'annex1-variant') return VARIANT_C15;
  if (kind === 'scenario') return VARIANT_C16_SCENARIO;
  if (kind === 'reverse-stress') return VARIANT_C16_REVERSE;
  if (kind === 'tail-index') return VARIANT_C17;
  if (kind === 'horizon') return VARIANT_C02;
  if (kind === 'shock') return VARIANT_C20_SHOCK;
  if (kind === 'shift') return VARIANT_C20_SHIFT;
  if (kind === 'seeds') return VARIANT_C20_SEEDS;
  if (kind === 'perturbation') return VARIANT_C20_PERTURBATION;
  if (kind === 'leakage') return VARIANT_C20_LEAKAGE;
  if (kind === 'year-pair') return VARIANT_C21;
  return kind === 'sp-calibration' ? VARIANT_C05_SP : kind === 'ldp' ? VARIANT_C05_LDP : kind === 'validator' ? VARIANT_C22 : VARIANT;
}

/** The models descriptor an artifact is read against, by its fit. */
export function modelsKind(doc: {
  case_id?: string;
  fit_id?: string;
}): typeof MODELS | typeof MODELS_C04 | typeof MODELS_C05_SP | typeof MODELS_C05_LDP | typeof MODELS_C06 | typeof MODELS_C07 | typeof MODELS_C03 | typeof MODELS_C08 | typeof MODELS_C09 | typeof MODELS_C10 | typeof MODELS_C11 | typeof MODELS_C12 | typeof MODELS_C13 | typeof MODELS_C14 | typeof MODELS_C15 | typeof MODELS_C16 | typeof MODELS_C17 | typeof MODELS_C18 | typeof MODELS_C02 | typeof MODELS_C20 | typeof MODELS_C21 | typeof MODELS_C22 {
  if (doc.case_id === 'C04') return MODELS_C04;
  if (doc.case_id === 'C05') return doc.fit_id === 'ldp' ? MODELS_C05_LDP : MODELS_C05_SP;
  if (doc.case_id === 'C06') return MODELS_C06;
  if (doc.case_id === 'C07') return MODELS_C07;
  if (doc.case_id === 'C03') return MODELS_C03;
  if (doc.case_id === 'C08') return MODELS_C08;
  if (doc.case_id === 'C09') return MODELS_C09;
  if (doc.case_id === 'C10') return MODELS_C10;
  if (doc.case_id === 'C11') return MODELS_C11;
  if (doc.case_id === 'C12') return MODELS_C12;
  if (doc.case_id === 'C13') return MODELS_C13;
  if (doc.case_id === 'C14') return MODELS_C14;
  if (doc.case_id === 'C15') return MODELS_C15;
  if (doc.case_id === 'C16') return MODELS_C16;
  if (doc.case_id === 'C17') return MODELS_C17;
  if (doc.case_id === 'C18') return MODELS_C18;
  if (doc.case_id === 'C02') return MODELS_C02;
  if (doc.case_id === 'C20') return MODELS_C20;
  if (doc.case_id === 'C21') return MODELS_C21;
  if (doc.case_id === 'C22') return MODELS_C22;
  return MODELS;
}

/** The quadrature the live most prudent bounds use, in the C05 ldp models artifact (the engine's 256 nodes). */
export interface QuadratureDetails {
  quadrature: { rule: string; nodes: number[]; weights: number[] };
}

// --- the governance documents (U15; docs/contracts/schemas/governance/): the web's view of the four documents the
// governance bake writes. Every descriptor is checked against its schema file in contract.test.ts, and against the
// reviewed fixtures in workbench/governance/governance.test.ts.

const ATTRIBUTE_IDS = Array.from({ length: 40 }, (_, i) => `A${String(i + 1).padStart(2, '0')}`);
const GOV_DATE: Kind = 'string';
const GOV_AS_OF_BASIS: Record<string, Kind> = { "label": 'string', "basis": 'text' };
const GOV_SHA256: Kind = 'string';
const GOV_PROVENANCE: Record<string, Kind> = { "code_version": 'string', "riskvalidation_version": 'string', "generators": { array: 'string' }, "documents_read": { array: { object: { "path": 'string', "sha256": GOV_SHA256, "ref": { nullable: 'string' } } } } };
const GOV_TIER: Kind = 'integer';
const GOV_INV_CONVENTIONS: Record<string, Kind> = { "exposure_band_cuts": { object: { "label": 'string', "basis": 'string', "cuts": { array: 'number' } } }, "regulatory_use_grades": { object: { "label": 'string', "basis": 'string', "graded": { object: { "reported_figure": 'integer', "feeding_parameter": 'integer', "compliance_monitoring": 'integer', "none": 'integer' } }, "literal": { object: { "feeds_capital_provisioning_or_reporting": 'integer', "compliance_monitoring": 'integer', "none": 'integer' } } } }, "complexity_rounding": { object: { "label": 'string', "basis": 'string', "rule": 'string' } }, "frequency": { object: { "label": 'string', "basis": 'string', "tiers": { array: { object: { "tier": GOV_TIER, "review_kind": 'string', "review_months": 'integer', "revalidation_months": { nullable: 'integer' }, "monitoring_months": { nullable: 'integer' }, "null_reason": { nullable: 'text' } } } } } }, "adopted_reading": { object: { "label": 'string', "basis": 'string', "reading": 'string' } } };
const GOV_INV_ENGINE_NODE: Record<string, Kind> = { "key": 'string', "version": 'string', "basis": 'string' };
const GOV_INV_ATTR: Record<string, Kind> = { "value": 'json', "status": 'string', "basis": 'string' };
const GOV_INV_ATTRIBUTES: Record<string, Kind> = { ...Object.fromEntries(ATTRIBUTE_IDS.map((id) => [id, { object: GOV_INV_ATTR }])) };
const GOV_INV_VARIANT: Record<string, Kind> = { "variant_id": 'string', "basis": 'string' };
const GOV_TAG: Kind = 'string';
const GOV_INV_COMPONENT: Record<string, Kind> = { "key": 'string', "model_id": 'string', "role": 'string', "role_tag": GOV_TAG, "role_basis": 'string', "family": { nullable: 'string' }, "rung": { nullable: 'string' }, "title": { nullable: 'text' } };
const GOV_INV_SCOPE_ANSWERS: Record<string, Kind> = { "applies_theory": 'boolean', "output_is_estimate": 'boolean', "deterministic": 'boolean', "generative_or_agentic": 'boolean' };
const GOV_INV_SCOPE_PROFILE: Record<string, Kind> = { "profile": 'string', "in_scope": 'boolean', "rationale": 'text' };
const GOV_INV_SCOPE: Record<string, Kind> = { "answers": { object: GOV_INV_SCOPE_ANSWERS }, "profiles": { array: { object: GOV_INV_SCOPE_PROFILE } }, "basis": 'string' };
const GOV_INV_EXPOSURE: Record<string, Kind> = { "share": { nullable: 'number' }, "band": 'integer', "tag": GOV_TAG, "basis": 'string' };
const GOV_INV_REG_USE: Record<string, Kind> = { "literal": 'integer', "graded": 'integer', "tag": GOV_TAG, "basis": 'string' };
const GOV_INV_DECISION: Record<string, Kind> = { "score": 'integer', "tag": GOV_TAG, "basis": 'string' };
const GOV_INV_MATERIALITY: Record<string, Kind> = { "exposure": { object: GOV_INV_EXPOSURE }, "regulatory_use": { object: GOV_INV_REG_USE }, "decision_criticality": { object: GOV_INV_DECISION }, "m": { object: { "literal": 'integer', "graded": 'integer' } } };
const GOV_INV_FACTOR: Record<string, Kind> = { "id": 'string', "name": 'string', "score": { nullable: 'integer' }, "tag": GOV_TAG, "basis": 'string' };
const GOV_INV_COMPLEXITY: Record<string, Kind> = { "factors": { array: { object: GOV_INV_FACTOR } }, "scored": 'integer', "sum": 'integer', "mean": 'number', "c": { object: { "mean": 'integer', "maximum": 'integer' } } };
const GOV_INV_OVERRIDE: Record<string, Kind> = { "to_tier": GOV_TIER, "rationale": 'string', "approver": 'string' };
const GOV_INV_SENSITIVITY: Record<string, Kind> = { "reading": 'string', "regulatory_use": 'string', "complexity": 'string', "m": 'integer', "c": 'integer', "tier": GOV_TIER };
const GOV_INV_TIER: Record<string, Kind> = { "materiality": { object: GOV_INV_MATERIALITY }, "complexity": { object: GOV_INV_COMPLEXITY }, "adopted_reading": 'string', "computed_tier": GOV_TIER, "override": { nullable: { object: GOV_INV_OVERRIDE } }, "tier": GOV_TIER, "tier_sensitivity": { array: { object: GOV_INV_SENSITIVITY } } };
const GOV_INV_TRANSITION: Record<string, Kind> = { "from": 'string', "to": 'string', "date": GOV_DATE, "basis": 'string' };
const GOV_INV_EXCEPTION: Record<string, Kind> = { "type": 'string', "approver": 'string', "expiry": GOV_DATE, "reason": 'text' };
const GOV_INV_LIFECYCLE: Record<string, Kind> = { "state": 'string', "basis": 'string', "transitions": { array: { object: GOV_INV_TRANSITION } }, "exception": { nullable: { object: GOV_INV_EXCEPTION } } };
const GOV_INV_LAST: Record<string, Kind> = { "date": GOV_DATE, "type": 'string', "basis": 'string' };
const GOV_INV_SCHEDULE: Record<string, Kind> = { "profile": 'string', "review_kind": 'string', "last_validation": { object: GOV_INV_LAST }, "next_review": GOV_DATE, "next_full_revalidation": { nullable: GOV_DATE }, "next_monitoring": { nullable: GOV_DATE }, "null_reason": { nullable: 'text' } };
const GOV_INV_GRAPH: Record<string, Kind> = { "depth": 'integer', "fan_in": 'integer', "fan_out": 'integer' };
const GOV_INV_MAP: Record<string, Kind> = { "generation": 'integer', "x": 'number', "y": 'number' };
const GOV_INV_ENTRY: Record<string, Kind> = { "key": 'string', "case_id": 'string', "fit_id": 'string', "title": 'text', "attributes": { object: GOV_INV_ATTRIBUTES }, "variants": { array: { object: GOV_INV_VARIANT } }, "components": { array: { object: GOV_INV_COMPONENT } }, "scope": { object: GOV_INV_SCOPE }, "tier_block": { object: GOV_INV_TIER }, "lifecycle": { object: GOV_INV_LIFECYCLE }, "schedule": { object: GOV_INV_SCHEDULE }, "graph": { object: GOV_INV_GRAPH }, "map": { object: GOV_INV_MAP } };
const GOV_INV_EDGE: Record<string, Kind> = { "upstream": 'string', "downstream": 'string', "kind": 'string', "stated_source": 'string' };
const GOV_INV_RELATED: Record<string, Kind> = { "a": 'string', "b": 'string', "kind": 'string', "source": 'string' };
const GOV_INV_EXCLUDED: Record<string, Kind> = { "case_id": 'string', "variant_id": { nullable: 'string' }, "reason": 'text' };
const GOV_INV_ATTR_COUNT: Record<string, Kind> = { "present": 'integer', "derivable": 'integer', "convention": 'integer', "not_applicable": 'integer', "missing": 'integer' };
const GOV_INV_COMPLETENESS: Record<string, Kind> = { "entries": 'integer', "attributes": { object: { ...Object.fromEntries(ATTRIBUTE_IDS.map((id) => [id, { object: GOV_INV_ATTR_COUNT }])) } } };
const GOV_INV_TIER_COUNTS: Record<string, Kind> = { "reading": 'string', "counts": { array: 'integer' } };
const GOV_SEVERITY: Kind = 'string';
const GOV_ECB_F: Kind = 'string';
const GOV_GOV_FINDING: Record<string, Kind> = { "id": 'string', "severity": GOV_SEVERITY, "ecb_f": GOV_ECB_F, "status": 'string', "title": 'text', "description": 'text', "basis": 'string' };
const GOV_FND_CONVENTIONS: Record<string, Kind> = { "deadline_days": { object: { "label": 'string', "basis": 'string', "rows": { array: { object: { "severity": GOV_SEVERITY, "days": { array: 'integer' } } } } } }, "severity_scale": { object: { "label": 'string', "basis": 'string', "rows": { array: { object: { "severity": GOV_SEVERITY, "ecb_f": GOV_ECB_F } } } } }, "status_map": { object: { "label": 'string', "basis": 'string', "rows": { array: { object: { "product": 'string', "register": 'string' } } } } } };
const GOV_FND_ANCHOR: Record<string, Kind> = { "metric": 'string', "test_id": 'string', "model_id": 'string', "segment": { nullable: 'string' }, "value": 'number', "unit": 'string', "basis": 'string' };
const GOV_FND_RISK: Record<string, Kind> = { "approver": 'string', "approver_reason": 'text', "expiry": { nullable: 'json' }, "expiry_reason": 'text' };
const GOV_FND_ROW: Record<string, Kind> = { "key": 'string', "case_id": 'string', "variant_id": 'string', "id": 'string', "entry_key": 'string', "title": 'text', "severity": GOV_SEVERITY, "ecb_f": GOV_ECB_F, "product_status": 'string', "status": 'string', "evidence": { array: 'string' }, "anchor": { nullable: { object: GOV_FND_ANCHOR } }, "anchor_reason": { nullable: 'text' }, "rwea_share": { nullable: 'number' }, "rwea_share_reason": { nullable: 'text' }, "owner_role": 'string', "tier": GOV_TIER, "raised": GOV_DATE, "deadline_days": 'integer', "due": GOV_DATE, "ageing_days": 'integer', "overdue": 'boolean', "remediation": { nullable: 'text' }, "remediation_reason": { nullable: 'text' }, "risk_acceptance": { nullable: { object: GOV_FND_RISK } } };
const GOV_FND_BY_SEVERITY: Record<string, Kind> = { "S1": 'integer', "S2": 'integer', "S3": 'integer', "S4": 'integer' };
const GOV_FND_BY_STATUS: Record<string, Kind> = { "open": 'integer', "action_plan_agreed": 'integer', "in_progress": 'integer', "submitted_for_closure": 'integer', "validated_closed": 'integer', "overdue": 'integer', "risk_accepted": 'integer' };
const GOV_FND_CASE_COUNT: Record<string, Kind> = { "case_id": 'string', "total": 'integer', "by_severity": { object: GOV_FND_BY_SEVERITY }, "by_status": { object: GOV_FND_BY_STATUS }, "overdue": 'integer' };
const GOV_FND_COUNTS: Record<string, Kind> = { "total": 'integer', "by_severity": { object: GOV_FND_BY_SEVERITY }, "by_status": { object: GOV_FND_BY_STATUS }, "overdue": 'integer', "by_case": { array: { object: GOV_FND_CASE_COUNT } } };
const GOV_REP_COUNTS: Record<string, Kind> = { "green": 'integer', "amber": 'integer', "red": 'integer', "not_evaluated": 'integer', "error": 'integer' };
const GOV_REP_INPUT: Record<string, Kind> = { "ref": 'string', "kind": 'string' };
const GOV_REP_POLICY: Record<string, Kind> = { "label": 'string', "kind": { nullable: 'string' }, "kind_reason": { nullable: 'string' }, "direction": { nullable: 'string' }, "direction_reason": { nullable: 'string' }, "alpha_amber": { nullable: 'number' }, "alpha_red": { nullable: 'number' }, "parameters": { map: { anyOf: ['number', 'string'] } }, "version": { nullable: 'string' }, "source": 'string', "reason": { nullable: 'string' } };
const GOV_REP_OUTCOME_ROW: Record<string, Kind> = { "test_id": 'string', "model_id": { nullable: 'string' }, "segment": { nullable: 'string' }, "family": 'string', "statistic": { nullable: 'number' }, "p_value": { nullable: 'number' }, "metric": { nullable: 'number' }, "light": 'string', "h0": 'string', "reference": 'string', "policy": { object: GOV_REP_POLICY } };
const GOV_REP_BLOCK: Kind = { anyOf: [{ object: { "kind": 'string', "text": 'text' } }, { object: { "kind": 'string', "items": { array: 'text' } } }, { object: { "kind": 'string', "caption": 'text', "columns": { array: 'text' }, "rows": { array: { array: { nullable: { anyOf: ['string', 'number', 'boolean'] } } } } } }, { object: { "kind": 'string', "variant_id": 'string', "rows": { array: { object: GOV_REP_OUTCOME_ROW } } } }] };
const GOV_REP_MISSING: Record<string, Kind> = { "element": 'text', "reason": 'text' };
/** Sections 2 to 10 and 12 share one shape; 1 adds the opinion level and 11 the opinion. */
const GOV_REP_SECTION: Record<string, Kind> = { "number": 'integer', "key": 'string', "title": 'text', "status": 'string', "inputs": { array: { object: GOV_REP_INPUT } }, "absent_reason": { nullable: 'text' }, "blocks": { array: GOV_REP_BLOCK }, "missing": { array: { object: GOV_REP_MISSING } } };
const GOV_REP_SECTION1: Record<string, Kind> = { ...GOV_REP_SECTION, "opinion_level": 'integer' };
const GOV_REP_OPEN_FINDING: Record<string, Kind> = { "key": 'string', "severity": GOV_SEVERITY, "rwea_share": { nullable: 'number' } };
const GOV_REP_OPINION: Record<string, Kind> = { "level": 'integer', "level_label": 'text', "rule": { object: { "id": 'string', "text": 'text' } }, "rwea_cut_points_applied": 'boolean', "open_findings": { array: { object: GOV_REP_OPEN_FINDING } }, "recommendation": { object: { "outcome": 'string', "text": 'text' } }, "label": 'text' };
const GOV_REP_SECTION11: Record<string, Kind> = { ...GOV_REP_SECTION, "opinion": { object: GOV_REP_OPINION } };
const GOV_APP_THRESHOLD: Record<string, Kind> = { "label": 'string', "basis": 'string', "direction": 'string', "green_limit": 'number', "amber_limit": 'number' };
const GOV_APP_METRIC: Record<string, Kind> = { "id": 'string', "name": 'text', "kind": 'string', "value": { nullable: 'number' }, "unit": 'string', "numerator": { nullable: 'number' }, "denominator": { nullable: 'number' }, "register_rows": { nullable: 'integer' }, "reason": { nullable: 'text' }, "threshold": { object: GOV_APP_THRESHOLD }, "light": 'string' };
export const GOVERNANCE_INVENTORY = {
  "schema": 'string',
  "case_id": 'string',
  "governance_id": 'string',
  "schema_version": 'string',
  "as_of": GOV_DATE,
  "as_of_basis": { object: GOV_AS_OF_BASIS },
  "provenance": { object: GOV_PROVENANCE },
  "conventions": { object: GOV_INV_CONVENTIONS },
  "engine_node": { object: GOV_INV_ENGINE_NODE },
  "entries": { array: { object: GOV_INV_ENTRY } },
  "edges": { array: { object: GOV_INV_EDGE } },
  "related": { array: { object: GOV_INV_RELATED } },
  "excluded": { array: { object: GOV_INV_EXCLUDED } },
  "completeness": { object: GOV_INV_COMPLETENESS },
  "tier_counts": { array: { object: GOV_INV_TIER_COUNTS } },
  "governance_findings": { array: { object: GOV_GOV_FINDING } },
} satisfies Record<keyof components['schemas']['governance-governance-inventory'], Kind>;

export const GOVERNANCE_FINDINGS = {
  "schema": 'string',
  "case_id": 'string',
  "governance_id": 'string',
  "schema_version": 'string',
  "as_of": GOV_DATE,
  "as_of_basis": { object: GOV_AS_OF_BASIS },
  "provenance": { object: GOV_PROVENANCE },
  "conventions": { object: GOV_FND_CONVENTIONS },
  "rows": { array: { object: GOV_FND_ROW } },
  "counts": { object: GOV_FND_COUNTS },
} satisfies Record<keyof components['schemas']['governance-governance-findings'], Kind>;

export const GOVERNANCE_REPORT = {
  "schema": 'string',
  "case_id": 'string',
  "governance_id": 'string',
  "schema_version": 'string',
  "as_of": GOV_DATE,
  "as_of_basis": { object: GOV_AS_OF_BASIS },
  "provenance": { object: GOV_PROVENANCE },
  "entry_key": 'string',
  "title": 'text',
  "tier": GOV_TIER,
  "test_counts": { object: GOV_REP_COUNTS },
  "sections": { array: { anyOf: [{ object: GOV_REP_SECTION1 }, { object: GOV_REP_SECTION }, { object: GOV_REP_SECTION11 }] } },
} satisfies Record<keyof components['schemas']['governance-governance-report'], Kind>;

export const GOVERNANCE_APPETITE = {
  "schema": 'string',
  "case_id": 'string',
  "governance_id": 'string',
  "schema_version": 'string',
  "as_of": GOV_DATE,
  "as_of_basis": { object: GOV_AS_OF_BASIS },
  "provenance": { object: GOV_PROVENANCE },
  "population": { object: { "entries": 'integer', "findings": 'integer', "distinct_findings": 'integer', "tier1_entries": 'integer' } },
  "metrics": { array: { object: GOV_APP_METRIC } },
} satisfies Record<keyof components['schemas']['governance-governance-appetite'], Kind>;


