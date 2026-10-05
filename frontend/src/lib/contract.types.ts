// The web side of the two contracts (data-pipeline/pipeline/io/contract.py and data-pipeline/pipeline/core/manifest.py).
// The interfaces type the app; the descriptors describe the same keys at run time, and `satisfies` ties each descriptor
// to its interface (a key added to one and not the other fails `tsc`). contract.test.ts reads every committed artifact
// against the descriptors in both directions, types included, so the pipeline cannot ship a shape the web does not
// read, and the web cannot read a key the pipeline does not write (T11, CT-004).

/** Every reader-facing string is bilingual at the source. */
export interface Text {
  en: string;
  es: string;
}

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

export type TruthStatus = 'real-outcomes' | 'synthetic-known-truth' | 'synthetic-calibrated' | 'published-answer';
export type PipelineLane = 'live' | 'precompute';
export type Light = 'green' | 'amber' | 'red' | 'not_evaluated' | 'error';
export type Severity = 'S1' | 'S2' | 'S3' | 'S4';

export interface CaseIndexEntry {
  case_id: string;
  title: Text;
  category: Text;
  category_id: string;
  /** Where the case's data comes from, for the case picker: observed data, a generator, or a published answer. */
  kind: 'real' | 'synthetic';
  manifest_path: string;
}

export interface CaseIndex {
  schema: string;
  engine_version: string;
  n_cases: number;
  default_case: string;
  cases: CaseIndexEntry[];
  /** Further files the site serves: the contract-1 declarations. */
  files: string[];
}

export interface GateVerdict {
  lane: PipelineLane;
  pure_python: boolean;
  wheels: string[];
  trace_bytes: number;
  run_ms_budget: number;
  trace_bytes_budget: number;
  reasons: string[];
}

export interface ArtifactEntry {
  role: 'models' | 'variant';
  variant_id: string;
  title: Text;
  /** The label a chip shows; `title` is the full name. */
  short_title: Text;
  regime: Text;
  truth_status: TruthStatus;
  /** Only on a variant entry: the path of the models artifact its rungs come from. */
  models_ref?: string;
  path: string;
  bytes: number;
  lane: PipelineLane;
  gate: GateVerdict;
}

export interface ContractExample {
  kind: 'rejected' | 'flagged' | 'excluded';
  row: number;
  key: string;
  field: string;
  value: string | null;
  expected: string;
  policy: string;
  reason: string;
  rule: string | null;
}

export interface ContractSummary {
  family: string;
  counts: { input: number; accepted: number; rejected: number; flagged: number; excluded: number };
  by_rule: { rejected: Record<string, number>; flagged: Record<string, number>; excluded: Record<string, number> };
  ignored_columns: string[];
  examples: ContractExample[];
}

export interface SourceDetails {
  name: string;
  publisher: string;
  landing: string;
  licence: string;
  class: string;
  attribution: string;
}

export interface CaseManifest {
  schema: string;
  case_id: string;
  title: Text;
  category: Text;
  question: Text;
  sources: string[];
  /** What the Context view shows of each source, from the source registry. */
  source_details: Record<string, SourceDetails>;
  seed: number;
  engine: { pipeline: string; riskvalidation: string | null };
  default_variant: string;
  artifacts: ArtifactEntry[];
  /** The contract-1 report of each source the case read, keyed by source id. */
  contract: Record<string, ContractSummary>;
  /** The checked expectation of the case: [low, high] per named result. */
  expect: Record<string, [number, number]>;
}

export interface Calibration {
  kind: string;
  fitted_on: string;
  x: number[];
  y: number[];
}

export interface ModelSummary {
  id: string;
  family: string;
  rung: string;
  title: Text;
  /** The label a chip, a column header or a chart key shows ("P2b PLTR"); `title` is the full name. */
  short_title: Text;
  engine: string;
  engine_version: string;
  licence: string;
  calibration: Calibration | null;
  parameters: Record<string, { value: number; unit: string }>;
  /** The weights' hash for a fitted model; null for a formula (C05's approaches and estimators). */
  checkpoint_sha256: string | null;
}

/** A model record with its internals (points tables, shape functions, grids), in the models artifact. */
export interface ModelRecord extends ModelSummary {
  details: unknown;
}

export interface GradeRow {
  grade: string;
  lo: number;
  hi: number;
  n: number;
  d: number;
  pd: number | null;
  dr: number | null;
}

export interface ReliabilityBin {
  n: number;
  pd: number;
  dr: number;
  lo: number;
  hi: number;
}

export interface RungOutputs {
  grades: GradeRow[];
  reliability: ReliabilityBin[];
  roc: { fpr: number[]; tpr: number[] };
  cap: { population: number[]; defaults: number[]; default_rate: number };
  distribution: { log10_pd_edges: number[]; defaulters: number[]; non_defaulters: number[] };
  cutoff: { cutoff: number[]; approval_rate: number[]; bad_rate: number[]; pd_ead: number[]; ead: number[] };
  reliability_raw: ReliabilityBin[] | null;
}

export interface ScoredSample {
  ids: string[];
  /** The observed outcome of each sampled applicant (1 = default). */
  targets: number[];
  inputs: Record<string, Array<number | string>>;
  scorecard_points: number[][];
  scorecard_score: number[];
  scorecard_pd: number[];
  ebm_logit: number[];
}

export interface GroupStat {
  n: number;
  default_rate: number;
  auc: Record<string, number>;
  /** The ROC of the champion and of every challenger within the group (51 points). */
  roc: Record<string, { fpr: number[]; tpr: number[] }>;
}

export interface VariantOutputs {
  rungs: Record<string, RungOutputs>;
  n: number;
  defaults: number;
  groups: Record<string, GroupStat>;
  sample: ScoredSample | null;
}

export interface TestRow {
  test_id: string;
  model_id: string | null;
  segment: string | null;
  statistic: number | null;
  p_value: number | null;
  metric: number | null;
  h0: string;
  alternative: string;
  policy_version: string;
  alpha_amber: number | null;
  alpha_red: number | null;
  light: Light;
  n: number | null;
  n_events: number | null;
  inputs_hash: string;
  reference: string;
  notes: string;
  extras: Record<string, unknown>;
}

export interface ImpactItem {
  value: number | null;
  unit: string;
  label: Text;
}

export interface Finding {
  id: string;
  severity: Severity;
  status: 'open' | 'accepted' | 'closed';
  evidence: string[];
  title: Text;
}

export interface Provenance {
  truth_status: TruthStatus;
  inputs: Array<{ source: string; class: string; files: Array<{ name: string; sha256: string }> }>;
  licence_classes: Record<string, string>;
  generators: string[];
  seed: number;
  code_version: string;
  riskvalidation_version: string | null;
}

export interface LaneBlock {
  lane: PipelineLane;
  reasons: string[];
}

/** One variant's artifact; `O` is the case's outputs (C01's by default, C05's two kinds below). */
export interface VariantArtifact<O = VariantOutputs> {
  schema: string;
  case_id: string;
  variant_id: string;
  model: ModelSummary[];
  outputs: O;
  tests: TestRow[];
  impact: Record<string, ImpactItem>;
  findings: Finding[];
  provenance: Provenance;
  lane: LaneBlock;
}

export interface FeatureMeta {
  name: string;
  meaning: Text;
  unit: string;
  categorical: boolean;
  monotone: number;
}

export interface SplitPart {
  n: number;
  defaults: number;
  default_rate: number;
}

export interface ReasonStability {
  bootstraps: number;
  rows: number;
  top_k: number;
  overlap_mean: number;
  overlap_min: number;
  overlap: number[];
}

export interface FitInfo {
  source: string;
  split: { train: SplitPart; calibration: SplitPart; holdout: SplitPart; folds: { k: number; repeats: number } };
  train_rows: number;
  features: FeatureMeta[];
  seed: number;
  master_scale: { grades: string[]; upper: number[] };
  reason_stability: ReasonStability | null;
}

export interface ModelsArtifact<F = FitInfo> {
  schema: string;
  case_id: string;
  fit_id: string;
  model: ModelRecord[];
  fit: F;
  provenance: Provenance;
  lane: LaneBlock;
}

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
  cutoff: { object: { cutoff: nums, approval_rate: nums, bad_rate: nums, pd_ead: nums, ead: nums } },
  reliability_raw: { nullable: RELIABILITY },
} satisfies Record<keyof RungOutputs, Kind>;

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

export interface ContractField {
  name: string;
  kind: 'str' | 'int' | 'float' | 'flag' | 'date' | 'enum';
  meaning: Text;
  unit: string;
  lo: number | null;
  hi: number | null;
  lo_open: boolean;
  hi_open: boolean;
  values: string[];
  values_param: string | null;
  required: boolean;
  on_missing: 'reject' | 'flag';
  /** The expected range in words, as a rejection states it. */
  expected: string;
}

export interface ContractRule {
  id: string;
  scope: 'record' | 'group';
  policy: 'reject' | 'flag' | 'exclude';
  field: string;
  statement: Text;
  group_by: string[];
  order_by: string | null;
}

export interface ContractParam {
  name: string;
  kind: string;
  meaning: Text;
  required: boolean;
  values: string[];
}

export interface FamilyContract {
  schema: string; // "contraste.contract/v1"
  family: string;
  title: Text;
  used_by: Text;
  fields: ContractField[];
  rules: ContractRule[];
  params: ContractParam[];
  open_fields: boolean;
  notes: Text[];
  param_checks: Text[];
}

export interface ContractIndex {
  schema: string;
  families: Array<{ family: string; title: Text; path: string }>;
}

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

export interface C05Irb {
  regime: string;
  asset_class: string;
  lgd: number;
  maturity: number;
  pd_floor: number;
  references: Record<string, string>;
}

export interface C05IrbPoint {
  regime: string;
  asset_class: string;
  pd: number;
  lgd: number;
  maturity: number;
  risk_weight: number;
}

export interface C05Approach {
  curve: number[];
  /** The approach's own forecast of the unconditional PD. */
  pd: number;
  /** The PD its curve implies under the observed forecast profile. */
  pd_under_profile1: number;
  accuracy_ratio: number;
  constants: Record<string, number>;
}

export interface C05GoldenCell {
  grade: string;
  printed: number;
  ours: number;
  gap: number;
}

export interface C05SpGolden {
  table5: C05GoldenCell[];
  table6: C05GoldenCell[];
  table7: Record<string, C05GoldenCell[]>;
  table7_p_values: Array<{ approach: string; printed_pct: number; ours_pct: number; mc_se_pct: number }>;
  table8: Array<{ approach: string; printed_pct: number; ours_pct: number; printed_p_value: string }>;
  table9_2009: Array<{ grade: string; printed: number; ours: number }>;
  max_gap_table7_pct_beyond_relative: number;
  tolerances: Record<string, string>;
}

export interface C05SpOutputs {
  kind: 'sp-calibration';
  year: number;
  grades: string[];
  profile0: number[];
  profile1: number[];
  default_rate0: number[];
  default_rate1: number[];
  default_profile0: number[];
  pd0: number;
  pd1: number;
  ar0: number;
  ar1: number;
  qmm0: { curve: number[]; alpha: number; beta: number; scores: number[]; start: number[]; pd: number };
  approaches: Record<string, C05Approach>;
  case3_profile_tests: Record<string, { statistic: number; dof: number; p_value: number }>;
  golden: C05SpGolden;
  parity: { calibration: { pd_grid: number[]; curves: Record<string, Record<string, number[]>> }; irb: C05IrbPoint[] };
  irb: C05Irb;
  n_obligors: number;
  n_defaults: number;
}

export interface C05Scaled {
  pd: number[];
  k: number;
  target: number;
}

export interface C05Bounds {
  independent: number[][];
  correlated: number[][];
  scaled_upper_bound: C05Scaled[];
  scaled_upper_bound_correlated: C05Scaled[];
  scaled_central_tendency: C05Scaled[];
}

export interface C05CoverageRow {
  gamma: number;
  coverage: number;
  se: number;
  ratio_q25: number;
  ratio_median: number;
  ratio_q75: number;
}

export interface C05KnownTruth {
  years: number;
  coverage: Record<string, Record<string, C05CoverageRow[]>>;
  tests: Record<string, Record<string, { reject_5: number; reject_1: number }>>;
  patterns: number;
  overdispersion: { variance_simulated: number; variance_model: number; variance_independent: number; rho_moment_estimate: number };
  total_defaults_histogram: number[];
  total_defaults_tail: number;
  share_of_defaults_by_grade: number[];
}

export interface C05LdpGoldenCell {
  table: number;
  row: string;
  gamma: number;
  printed: number;
  ours: number;
  gap: number;
}

export interface C05LdpOutputs {
  kind: 'ldp';
  grades: string[];
  obligors: number[];
  defaults: number[];
  gammas: number[];
  expert_pd: number[];
  true_pd: number[] | null;
  rho: number;
  bounds: C05Bounds;
  irb: C05Irb;
  parity: {
    bounds: { obligors: number[]; points: Array<{ defaults: number[]; gamma: number; rho: number; pd: number[]; scaled_upper_bound: number[] }> };
    irb: C05IrbPoint[];
  };
  known_truth: C05KnownTruth | null;
  golden: { cells: C05LdpGoldenCell[]; notes: Record<string, string> } | null;
  generated_year: { index: number; factor: number } | null;
}

export interface C05SpFit {
  estimation_year: number;
  targets: { pd: number; accuracy_ratio: number };
}

export interface C05LdpFit {
  obligors: number[];
  expert_pd: number[];
}

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

/** The variant descriptor an artifact is read against: by its outputs' kind (C05) or C01's. */
export function variantKind(doc: { outputs?: { kind?: string } }): typeof VARIANT | typeof VARIANT_C05_SP | typeof VARIANT_C05_LDP {
  const kind = doc.outputs?.kind;
  return kind === 'sp-calibration' ? VARIANT_C05_SP : kind === 'ldp' ? VARIANT_C05_LDP : VARIANT;
}

/** The models descriptor an artifact is read against, by its fit. */
export function modelsKind(doc: { case_id?: string; fit_id?: string }): typeof MODELS | typeof MODELS_C05_SP | typeof MODELS_C05_LDP {
  if (doc.case_id === 'C05') return doc.fit_id === 'ldp' ? MODELS_C05_LDP : MODELS_C05_SP;
  return MODELS;
}

/** The quadrature the live most prudent bounds use, in the C05 ldp models artifact (the engine's 256 nodes). */
export interface QuadratureDetails {
  quadrature: { rule: string; nodes: number[]; weights: number[] };
}
