// CONTRACT 2 mirror (the web side of data-pipeline/pipeline/core/{trace.py, manifest.py}). The interfaces type the
// app; the descriptors below describe the same keys at run time, and `satisfies` ties each descriptor to its
// interface (a key added to one and not the other fails `tsc`). contract.test.ts reads the committed artifacts
// against the descriptors in both directions, types included, so the pipeline cannot ship a shape the web does not
// read, and the web cannot read a key the pipeline does not write (T11).

/** Every reader-facing string is bilingual at the source. */
export interface Text {
  en: string;
  es: string;
}

export interface TraceSummary {
  peak_I: number;
  t_peak: number;
  attack_rate: number;
}

export interface Trace {
  schema: string; // "example.trace/v1"
  case_id: string;
  t: number[];
  S: number[];
  I: number[];
  R: number[];
  summary: TraceSummary;
}

export interface ArtifactRef {
  path: string;
  format: string;
  trace_schema: string;
  bytes: number;
}

export interface GateVerdict {
  lane: string;
  pure_python: boolean;
  wheels: string[];
  trace_bytes: number;
  run_ms_budget: number;
  trace_bytes_budget: number;
  reasons: string[];
}

export interface CaseParams {
  beta: number;
  gamma: number;
  N: number;
  I0: number;
  days: number;
}

export interface CaseManifest {
  schema: string; // "example.manifest/v3"
  case_id: string;
  title: Text;
  category: Text;
  real_or_synthetic: string;
  expected_band: Text;
  engine: { package: string; version: string; model: string };
  params: CaseParams;
  seed: number;
  artifact: ArtifactRef;
  lane: 'live' | 'precompute';
  gate: GateVerdict;
  flags: Array<Record<string, string>>;
  metrics: Record<string, number>;
  /** The checked expectation of the case: [low, high] per result metric (peak_I, t_peak, attack_rate). */
  expect: Record<string, [number, number]>;
}

export interface CaseIndexEntry {
  case_id: string;
  title: Text;
  category: Text;
  manifest_path: string;
}

export interface CaseIndex {
  schema: string; // "example.index/v2"
  engine_version: string;
  n_cases: number;
  default_case: string;
  cases: CaseIndexEntry[];
}

export const SCHEMAS = { trace: 'example.trace/v1', manifest: 'example.manifest/v3', index: 'example.index/v2' } as const;

/** A run-time description of a value: a primitive, a bilingual text, an array of a kind, an object, or a map. */
export type Kind =
  | 'string'
  | 'number'
  | 'integer'
  | 'boolean'
  | 'text'
  | { array: Kind }
  | { object: Record<string, Kind> }
  | { map: Kind };

export const TRACE_SUMMARY = { peak_I: 'number', t_peak: 'number', attack_rate: 'number' } satisfies Record<keyof TraceSummary, Kind>;

export const TRACE = {
  schema: 'string',
  case_id: 'string',
  t: { array: 'number' },
  S: { array: 'number' },
  I: { array: 'number' },
  R: { array: 'number' },
  summary: { object: TRACE_SUMMARY },
} satisfies Record<keyof Trace, Kind>;

export const MANIFEST = {
  schema: 'string',
  case_id: 'string',
  title: 'text',
  category: 'text',
  real_or_synthetic: 'string',
  expected_band: 'text',
  engine: { object: { package: 'string', version: 'string', model: 'string' } },
  params: { object: { beta: 'number', gamma: 'number', N: 'number', I0: 'number', days: 'integer' } satisfies Record<keyof CaseParams, Kind> },
  seed: 'integer',
  artifact: { object: { path: 'string', format: 'string', trace_schema: 'string', bytes: 'integer' } satisfies Record<keyof ArtifactRef, Kind> },
  lane: 'string',
  gate: {
    object: {
      lane: 'string',
      pure_python: 'boolean',
      wheels: { array: 'string' },
      trace_bytes: 'integer',
      run_ms_budget: 'number',
      trace_bytes_budget: 'integer',
      reasons: { array: 'string' },
    } satisfies Record<keyof GateVerdict, Kind>,
  },
  flags: { array: { map: 'string' } },
  metrics: { map: 'number' },
  expect: { map: { array: 'number' } },
} satisfies Record<keyof CaseManifest, Kind>;

export const INDEX = {
  schema: 'string',
  engine_version: 'string',
  n_cases: 'integer',
  default_case: 'string',
  cases: { array: { object: { case_id: 'string', title: 'text', category: 'text', manifest_path: 'string' } satisfies Record<keyof CaseIndexEntry, Kind> } },
} satisfies Record<keyof CaseIndex, Kind>;

/** Every way `value` departs from `kind`, with its path; empty when it conforms. Booleans are not numbers. */
export function conform(value: unknown, kind: Kind, path = '$'): string[] {
  if (kind === 'string') return typeof value === 'string' ? [] : [`${path}: expected a string`];
  if (kind === 'number') return typeof value === 'number' && Number.isFinite(value) ? [] : [`${path}: expected a finite number`];
  if (kind === 'integer') return Number.isInteger(value) ? [] : [`${path}: expected an integer`];
  if (kind === 'boolean') return typeof value === 'boolean' ? [] : [`${path}: expected a boolean`];
  if (kind === 'text') return conform(value, { object: { en: 'string', es: 'string' } }, path);
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
