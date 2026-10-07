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
  cutoff: {
    cutoff: number[];
    approval_rate: number[];
    bad_rate: number[];
    pd_ead: number[];
    ead: number[];
    /** The IRB capital (8% of the RWA) of the approved at unit LGD, by regime: retail capital is linear in the LGD. */
    capital_per_lgd: Record<string, number[]>;
    /** The same with the six-month full payers as transactors (the cards only; null for the loans). */
    capital_per_lgd_transactors: Record<string, number[]> | null;
  };
  reliability_raw: ReliabilityBin[] | null;
}

/** One point of the retail risk weight, from riskvalidation, for the live port (CT-215). */
export interface RetailParityPoint {
  regime: string;
  asset_class: string;
  revolver: boolean;
  pd: number;
  lgd: number;
  risk_weight: number;
}

export interface RegimeFacts {
  name: string;
  /** The QRRE revolvers' PD floor (null for other retail). */
  pd_floor_revolver: number | null;
  pd_floor: number;
  scaling: number;
  references: Record<string, string>;
}

/** What C01's capital view states (CT-212, CT-214). */
export interface C01Irb {
  asset_class: string;
  regimes: string[];
  by_regime: Record<string, RegimeFacts>;
  revolvers_only: boolean;
  six_month_full_payers: number | null;
  lgd_floor_basel3: number;
  lgd_floor_source: string;
  transactor_source: string;
  ead: Text;
  parity: RetailParityPoint[] | null;
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
  irb: C01Irb;
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

// --- C22, validating the validator (data-pipeline/pipeline/cases/c22_validator.py) -----------------------------------

/** One rejection rate of the harness: rejections of n repetitions, its Monte Carlo SE and Wilson interval. */
export interface C22Rate {
  rejections: number;
  n: number;
  undefined: number;
  rate: number;
  se: number;
  wilson_low: number;
  wilson_high: number;
}

/** One simulation: a registered test on one generator at one severity, its rates per rule ("p<0.05", "p<0.01", and
 * rules such as "metric>0.1"), the exact probability where one exists and whether the rate agrees with it. */
export interface C22Simulation {
  key: string;
  test_id: string;
  label: Text;
  scenario: Text;
  panel: string;
  severity: number;
  x: number;
  rates: Record<string, C22Rate>;
  exact: Record<string, number> | null;
  agrees: Record<string, boolean> | null;
  p_histogram: number[] | null;
  seed: number;
  n_rep: number;
  generator: string;
}

export interface C22Generator {
  name: string;
  config: unknown;
  truth: unknown;
}

export interface C22GoldenCell {
  table: string;
  row: string;
  column: string;
  published: number;
  measured: number;
  z: number | null;
  agrees: boolean;
}

export interface C22Golden {
  study: string;
  title: Text;
  runs_published: number;
  runs: number;
  cells: C22GoldenCell[];
  agree: number;
  total: number;
  note: Text;
}

export interface C22Curve {
  id: string;
  label: Text;
  x_label: Text;
  y_label: Text;
  x: number[];
  series: Array<{ id: string; label: Text; y: Array<number | null> }>;
}

export interface C22Outputs {
  kind: 'validator';
  family: string;
  ladder: { values: number[]; label: Text } | null;
  levels: number[];
  /** axis: the x axis of a panel whose simulations do not run along the family's ladder; measures: whether its rates are
   * the power against a planted defect or the size where the null holds */
  panels: Array<{ id: string; label: Text; axis: Text | null; measures: 'power' | 'size' }>;
  simulations: C22Simulation[];
  generators: Record<string, C22Generator>;
  golden: C22Golden[];
  exact_curves: C22Curve[];
  estimators: { auc: Record<string, number>; ece_when_right: Record<string, number> } | null;
  specimen: { severity: number };
  size_bounds: Record<string, number>;
}

/** A point of the count tests' exact rejection probability, for the live calculator's parity (CT-308). */
export interface C22Parity {
  test_id: string;
  n: number;
  pd: number;
  ratio: number;
  rho_true: number;
  rho_assumed: number | null;
  alpha: number;
  critical_count: number | null;
  probability: number;
}

export interface C22Fit {
  parity: C22Parity[];
  levels: number[];
}

const C22_RATE = {
  object: { rejections: 'integer', n: 'integer', undefined: 'integer', rate: num, se: num, wilson_low: num, wilson_high: num } satisfies Record<
    keyof C22Rate,
    Kind
  >,
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
export interface C04Cohort {
  label: string;
  begin: string;
  end: string;
  size: number[];
  counts: number[][];
  withdrawn: number[];
  defaulted: number[] | null;
  events: number[] | null;
  defaulted_cohort: number[] | null;
  tab2_gap: number | null;
}
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

export interface C04Bounds {
  lower: number[];
  upper: number[];
}
const C04_BOUNDS = { object: { lower: nums, upper: nums } satisfies Record<keyof C04Bounds, Kind> } as const;

/** The long-run average default rate by grade (EBA/GL/2017/16 paragraph 84) under one definition. */
export interface C04Lra {
  rate: number[];
  cohorts: number[];
  defaults: number[];
  n: number[];
  pooled_rate: number[];
  wald: C04Bounds;
  agresti_coull: C04Bounds;
  jeffreys: C04Bounds;
  last5: number[];
}
const C04_LRA = {
  object: {
    rate: nums,
    cohorts: ints,
    defaults: ints,
    n: ints,
    pooled_rate: nums,
    wald: C04_BOUNDS,
    agresti_coull: C04_BOUNDS,
    jeffreys: C04_BOUNDS,
    last5: nums,
  } satisfies Record<keyof C04Lra, Kind>,
} as const;

/** A generator of the pooled matrix: its rates, its L1 distance to the matrix, its PDs at one and five years (null by
 * grade where the scale has no default category, Moody's). */
export interface C04Generator {
  generator: number[][];
  valid: boolean;
  l1: number;
  pd_1y: (number | null)[];
  pd_5y: (number | null)[];
}
export interface C04EmGenerator extends C04Generator {
  iterations: number;
  converged: boolean;
  loglik: number;
}
const C04_GENERATOR_BASE = { generator: numss, valid: 'boolean', l1: num, pd_1y: nNums, pd_5y: nNums } satisfies Record<keyof C04Generator, Kind>;
const C04_GENERATOR = { nullable: { object: C04_GENERATOR_BASE } } as const;
const C04_EM_GENERATOR = {
  object: { ...C04_GENERATOR_BASE, iterations: 'integer', converged: 'boolean', loglik: num } satisfies Record<keyof C04EmGenerator, Kind>,
} as const;

export interface C04Embedding {
  S: number;
  series_converges: boolean;
  det: number;
  prod_diagonal: number;
  theorem3: { a: boolean; b: boolean; c: number[][] };
  exact_generator_excluded: boolean;
  stochastically_monotone: boolean;
  monotonicity_violations: Array<{ row: number; next_row: number; column: number; tail: number; next_tail: number }>;
}

export interface C04Homogeneity {
  statistic: number;
  p_value: number;
  dof: number;
  periods: number;
}
const C04_HOMOGENEITY = { object: { statistic: num, p_value: num, dof: 'integer', periods: 'integer' } satisfies Record<keyof C04Homogeneity, Kind> } as const;

export interface C04ReferenceTest {
  label: string;
  statistic: number;
  p_value: number;
  dof: number;
  impossible_moves: number[][];
}

/** One five-year window of the lifetime check (CT-415): the fixed cohort observed at the window's end against the
 * chained one-year projections; a value is null where the chain or the definition does not exist. */
export interface C04Lifetime {
  label: string;
  first: number;
  last: number;
  size: number[];
  observed: { default_end: (number | null)[]; withdrawn_end: number[]; cumulative_d2: number[] | null };
  projected: {
    chain_state: (number | null)[];
    chain_state_withdrawn: (number | null)[];
    chain_exclude: (number | null)[];
    pooled_power: (number | null)[];
    em: (number | null)[];
  };
}

export interface C04Irb {
  regime: string;
  asset_class: string;
  lgd: number;
  maturity: number;
  pd_floor: number;
  references: Record<string, string>;
}

export type C04Definition = 'd2' | 'd3' | 'd4' | 'keep';

export interface C04AgencyOutputs {
  kind: 'agency';
  agency: { code: string; name: string; scope: string };
  attribution: string;
  grades: string[];
  states: string[];
  cohorts: C04Cohort[];
  semesters: C04Cohort[];
  pd: Record<C04Definition, number[][] | null>;
  lra: { d2: C04Lra; d3: C04Lra; d4: C04Lra | null };
  pooled: { matrix: number[][]; matrix_state: number[][]; counts: number[][]; withdrawn: number[]; row_sizes: number[]; cohorts: number };
  embedding: C04Embedding;
  generators: {
    diagonal: C04Generator | null;
    weighted: C04Generator | null;
    jlt: C04Generator | null;
    em: C04EmGenerator;
    cohort_power: { pd_5y: (number | null)[] };
  };
  mobility: { labels: string[]; svd: number[]; trace: number[]; spec_default_rate: number[] };
  ecb: Array<{ label: string; mwb_upper: number; mwb_lower: number; ztests_p: number | null }>;
  homogeneity: { annual: C04Homogeneity; semesters: C04Homogeneity | null; reference: C04ReferenceTest[] };
  semesters_vs_year: Array<{ year: number; l1: number; pd_product: (number | null)[]; pd_annual: (number | null)[] }>;
  definition_gap: { d4_over_d2: (number | null)[] | null; d3_over_d2: (number | null)[] | null };
  lifetime: C04Lifetime[];
  origination: number[];
  irb: C04Irb;
}

const nNumGrid = { nullable: { array: nums } } as const;
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
      S: num,
      series_converges: 'boolean',
      det: num,
      prod_diagonal: num,
      theorem3: { object: { a: 'boolean', b: 'boolean', c: { array: ints } } },
      exact_generator_excluded: 'boolean',
      stochastically_monotone: 'boolean',
      monotonicity_violations: { array: { object: { row: 'integer', next_row: 'integer', column: 'integer', tail: num, next_tail: num } } },
    } satisfies Record<keyof C04Embedding, Kind>,
  },
  generators: {
    object: { diagonal: C04_GENERATOR, weighted: C04_GENERATOR, jlt: C04_GENERATOR, em: C04_EM_GENERATOR, cohort_power: { object: { pd_5y: nNums } } },
  },
  mobility: { object: { labels: { array: 'string' }, svd: nums, trace: nums, spec_default_rate: nums } },
  ecb: { array: { object: { label: 'string', mwb_upper: num, mwb_lower: num, ztests_p: nNum } } },
  homogeneity: {
    object: {
      annual: C04_HOMOGENEITY,
      semesters: { nullable: C04_HOMOGENEITY },
      reference: {
        array: {
          object: { label: 'string', statistic: num, p_value: num, dof: 'integer', impossible_moves: { array: ints } } satisfies Record<keyof C04ReferenceTest, Kind>,
        },
      },
    },
  },
  semesters_vs_year: { array: { object: { year: 'integer', l1: num, pd_product: nNums, pd_annual: nNums } } },
  definition_gap: { object: { d4_over_d2: { nullable: nNums }, d3_over_d2: { nullable: nNums } } },
  lifetime: {
    array: {
      object: {
        label: 'string',
        first: 'integer',
        last: 'integer',
        size: ints,
        observed: { object: { default_end: nNums, withdrawn_end: nums, cumulative_d2: { nullable: nums } } },
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
export interface C04Rate {
  rejections: number;
  n: number;
  undefined: number;
  rate: number;
  se: number;
  wilson_low: number;
  wilson_high: number;
}
const C04_RATE = {
  object: { rejections: 'integer', n: 'integer', undefined: 'integer', rate: num, se: num, wilson_low: num, wilson_high: num } satisfies Record<keyof C04Rate, Kind>,
} as const;

/** riskvalidation's estimator performance of a quantity by grade (Morris et al. 2019, Table 6): null by grade where
 * fewer than two repetitions are defined. */
export interface C04Performance {
  n: number[];
  truth: number[];
  mean: (number | null)[];
  bias: (number | null)[];
  bias_mcse: (number | null)[];
  empirical_se: (number | null)[];
  empirical_se_mcse: (number | null)[];
  rmse: (number | null)[];
  rmse_mcse: (number | null)[];
}
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
export interface C04ScalarPerformance {
  n: number;
  truth: number;
  mean: number;
  bias: number;
  bias_mcse: number;
  empirical_se: number;
  empirical_se_mcse: number;
  mse: number;
  mse_mcse: number;
  rmse: number;
  rmse_mcse: number;
}

export interface C04MarkovRung {
  value: null;
  seed_key: string;
  seed: number;
  level: number;
  obligor_years: number[];
  estimators: Record<'cohort' | 'duration' | 'em' | 'diagonal' | 'weighted' | 'jlt', C04Performance & { zero: C04Rate[] }>;
  em: { converged: C04Rate; iterations_mean: number; iterations_max: number };
  coverage: Record<'wald' | 'agresti_coull' | 'jeffreys' | 'bootstrap', C04Rate[]>;
  bootstrap: { method: string; estimate: string; horizon: number; n_boot: number; repetitions: number };
}
export interface C04MomentumRung {
  value: number;
  seed_key: string;
  seed: number;
  momentum: number[][] | null;
  investment_grades: number;
  coefficient: C04ScalarPerformance | null;
  pd_1y_cohort: C04Performance;
  pd_5y_frequency: C04Performance;
  pd_5y_cohort_power: C04Performance;
  pd_5y_duration: C04Performance;
  error_cohort_power: C04Performance;
  error_duration: C04Performance;
}
export interface C04CycleRung {
  value: number;
  seed_key: string;
  seed: number;
  stressed_period: number[] | null;
  pd_true_base: number[];
  pd_true_stressed: number[];
  pd_true_average: number[];
  pd_stressed_year: C04Performance;
  pd_lra: C04Performance;
  pd_pooled: C04Performance;
}
export interface C04WithdrawalsRung {
  value: number;
  seed_key: string;
  seed: number;
  withdrawal_rate: number;
  window: number;
  truncation_verified: number;
  withdrawn_obligors_mean: number;
  withdrawn_share: { n: number[]; mean: (number | null)[]; mean_mcse: (number | null)[] };
  pd_removed: C04Performance;
  pd_kept: C04Performance;
  pd_followed: C04Performance;
  pd_latent: C04Performance;
}
export interface C04ThinRung {
  value: number;
  level: number;
  expected_defaults: number[];
  coverage: Record<'wald' | 'agresti_coull' | 'jeffreys', number[]>;
  length: Record<'wald' | 'agresti_coull' | 'jeffreys', number[]>;
  overlap_jeffreys: number[];
}
export type C04Rung = C04MarkovRung | C04MomentumRung | C04CycleRung | C04WithdrawalsRung | C04ThinRung;

export interface C04Simulation {
  key: string;
  test_id: string;
  rung: number | null;
  rates: Record<string, C04Rate>;
  seed: number;
  n_rep: number;
}

export type C04Family = 'markov' | 'momentum' | 'cycle' | 'withdrawals' | 'thin';

export interface C04FamilyOutputs {
  kind: 'generator';
  family: C04Family;
  generator: { q: number[][]; pd_1y: number[]; pd_5y: number[]; obligors: number[]; source: string; one_year_matrix: number[][] };
  design: { years: number; snapshots: number[]; reps: number; seed_key: string | null };
  ladder: { name: Text; unit: string; values: number[] } | null;
  rungs: C04Rung[];
  simulations: C04Simulation[];
}

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
export interface C04Print {
  printed: number;
  recomputed: number;
  decimals: number;
}
const C04_PRINT = { object: { printed: num, recomputed: num, decimals: 'integer' } satisfies Record<keyof C04Print, Kind> } as const;
const C04_PRINTS = { object: { printed: nums, recomputed: nums, decimals: ints } } as const;

export interface C04PublishedOutputs {
  kind: 'published';
  irw: {
    rows: Array<{ matrix: string; method: string; printed: number; recomputed: number; agrees: boolean }>;
    jlt_from_printed_generator: number;
    theorem3_c: boolean[];
    series_terms: number;
  };
  sr190: {
    defaults: number;
    n: number;
    rows: Array<{ rho: number; interval: string; printed: number[]; recomputed: number[]; agrees: boolean }>;
    n_dagger: { printed: number[]; recomputed: number[]; decimals: number[] };
  };
  engelmann: {
    w_ttc: { printed: number[]; recomputed: number[]; decimals: number[] };
    ttc_pd: C04Print;
    portfolios: Array<{
      name: string;
      w0: number[];
      pd0: C04Print & { check: 'printed digits' | 'entry rounding'; note: string | null };
      extreme: (C04Print & { kind: 'min' | 'max' }) | null;
      pd_path: number[];
    }>;
    row_sum_deviation: number;
  };
}
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
            pd0: { object: { printed: num, recomputed: num, decimals: 'integer', check: 'string', note: nStr } },
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
export interface C04ProjectionPoint {
  agency: string;
  matrix: number[][];
  origination: number[];
  w0: number[];
  years: number;
  default_rate: number[];
  portfolio_last: number[];
  ttc: number[];
  ttc_default_rate: number;
}
export interface C04IntervalPoint {
  defaults: number;
  n: number;
  rho: number;
  level: number;
  wald: number[];
  agresti_coull: number[];
  jeffreys: number[];
  n_effective: number;
}
export interface C04CapitalPoint {
  pd: number;
  lgd: number;
  maturity: number;
  regime: string;
  asset_class: string;
  risk_weight: number;
}
export interface C04Fit {
  parity: { projection: C04ProjectionPoint[]; intervals: C04IntervalPoint[]; capital: C04CapitalPoint[] };
  generator: { q: number[][]; obligors: number[]; source: string };
}
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

/** The variant descriptor an artifact is read against: by its outputs' kind (C04, C05, C22) or C01's. */
export function variantKind(doc: {
  outputs?: { kind?: string };
}):
  | typeof VARIANT
  | typeof VARIANT_C04_AGENCY
  | typeof VARIANT_C04_FAMILY
  | typeof VARIANT_C04_PUBLISHED
  | typeof VARIANT_C05_SP
  | typeof VARIANT_C05_LDP
  | typeof VARIANT_C22 {
  const kind = doc.outputs?.kind;
  if (kind === 'agency') return VARIANT_C04_AGENCY;
  if (kind === 'generator') return VARIANT_C04_FAMILY;
  if (kind === 'published') return VARIANT_C04_PUBLISHED;
  return kind === 'sp-calibration' ? VARIANT_C05_SP : kind === 'ldp' ? VARIANT_C05_LDP : kind === 'validator' ? VARIANT_C22 : VARIANT;
}

/** The models descriptor an artifact is read against, by its fit. */
export function modelsKind(doc: {
  case_id?: string;
  fit_id?: string;
}): typeof MODELS | typeof MODELS_C04 | typeof MODELS_C05_SP | typeof MODELS_C05_LDP | typeof MODELS_C22 {
  if (doc.case_id === 'C04') return MODELS_C04;
  if (doc.case_id === 'C05') return doc.fit_id === 'ldp' ? MODELS_C05_LDP : MODELS_C05_SP;
  if (doc.case_id === 'C22') return MODELS_C22;
  return MODELS;
}

/** The quadrature the live most prudent bounds use, in the C05 ldp models artifact (the engine's 256 nodes). */
export interface QuadratureDetails {
  quadrature: { rule: string; nodes: number[]; weights: number[] };
}
