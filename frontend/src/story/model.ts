// The numbers and the layout-free structure of the story (ADR-0082, SHOW-1). Nothing here draws and nothing here is typed in
// as a result: every count, series and verdict is read from the committed governance documents and the C11 window documents.
// What the story adds is (a) the bank's flow, a stated convention that places each inventory entry by its case (the authored
// part: which exposure, which model family and which output a case belongs to, from the entry's own exposure and regulatory-use
// basis), with every count then read from the documents; (b) the tally of exceedance days over the trailing 250 days against
// the Basel traffic light, which the tests check against the document's own maximum, final count and days per zone; (c) the
// Wilson interval of an exception rate, a stated function of two counts of the document.
import type { CaseData } from '../api/artifacts';
import { fitOf, levelOf, modelLabel, outputsOf, rollingCounts, zoneStart, type C11Outputs } from '../workbench/c11/selection';
import type { GovFindings, GovInventory, Severity } from '../workbench/governance/model';

export type Bi = { en: string; es: string };
export const bi = (en: string, es: string): Bi => ({ en, es });

export const SEVERITIES: readonly Severity[] = ['S1', 'S2', 'S3', 'S4'];
export type SevCount = Record<Severity, number>;
const zeroSev = (): SevCount => ({ S1: 0, S2: 0, S3: 0, S4: 0 });

// --- V1: the flow of the bank -------------------------------------------------------------------------------------------

export interface FlowDef {
  id: string;
  label: Bi;
  /** The label on a phone, one short line. */
  short: Bi;
}

/** What the inventory entries are exposed to. The grouping of a case is read from the entry's exposure basis
 * (`tier_block.materiality.exposure.basis`: the segment of the C07 book, the C18 risk class or the whole book). */
export const EXPOSURES: readonly FlowDef[] = [
  { id: 'retail', label: bi('Retail cards', 'Tarjetas minoristas'), short: bi('Retail', 'Minorista') },
  { id: 'corporate', label: bi('Corporate individuals', 'Corporativo individual'), short: bi('Corporate', 'Corporativo') },
  { id: 'sme', label: bi('SME and commercial groups', 'Pyme y grupos comerciales'), short: bi('SME', 'Pyme') },
  { id: 'mortgages', label: bi('Mortgages', 'Hipotecarios'), short: bi('Mortgages', 'Hipotecas') },
  { id: 'book', label: bi('The whole loan book', 'Toda la cartera de créditos'), short: bi('Loan book', 'Cartera') },
  { id: 'trading', label: bi('Trading book', 'Libro de negociación'), short: bi('Trading', 'Negociación') },
  { id: 'derivatives', label: bi('Derivatives counterparties', 'Contrapartes de derivados'), short: bi('Derivatives', 'Derivados') },
  { id: 'banking', label: bi('Banking book', 'Libro bancario'), short: bi('Banking book', 'Libro banc.') },
  { id: 'funding', label: bi('Deposits and funding', 'Depósitos y fondeo'), short: bi('Funding', 'Fondeo') },
  { id: 'operations', label: bi('Operations', 'Operaciones'), short: bi('Operations', 'Operaciones') },
  { id: 'capital', label: bi('The bank capital plan', 'El plan de capital del banco'), short: bi('Capital plan', 'Plan capital') },
  { id: 'none', label: bi('No bank balance', 'Sin balance bancario'), short: bi('No balance', 'Sin balance') },
];

export const FAMILIES: readonly FlowDef[] = [
  { id: 'scoring', label: bi('PD scoring', 'Puntuación de PD'), short: bi('PD scoring', 'PD') },
  { id: 'ratings', label: bi('Ratings and calibration', 'Calificaciones y calibración'), short: bi('Ratings', 'Calificación') },
  { id: 'provisions', label: bi('Provisions (IFRS 9, CMF)', 'Provisiones (IFRS 9, CMF)'), short: bi('Provisions', 'Provisiones') },
  { id: 'lgdead', label: bi('LGD and EAD', 'LGD y EAD'), short: bi('LGD, EAD', 'LGD, EAD') },
  { id: 'creditcap', label: bi('Credit capital', 'Capital de crédito'), short: bi('Credit cap.', 'Cap. crédito') },
  { id: 'market', label: bi('Market VaR and ES', 'VaR y ES de mercado'), short: bi('Market', 'Mercado') },
  { id: 'ccr', label: bi('Counterparty credit', 'Crédito de contraparte'), short: bi('Counterparty', 'Contraparte') },
  { id: 'irrbb', label: bi('Interest rate, banking book', 'Tasa de interés, libro bancario'), short: bi('IRRBB', 'IRRBB') },
  { id: 'liquidity', label: bi('Liquidity', 'Liquidez'), short: bi('Liquidity', 'Liquidez') },
  { id: 'oprisk', label: bi('Operational risk', 'Riesgo operacional'), short: bi('Op. risk', 'Riesgo op.') },
  { id: 'aggregation', label: bi('Aggregation and stress', 'Agregación y estrés'), short: bi('Aggregation', 'Agregación') },
  { id: 'ml', label: bi('ML and fairness', 'ML y equidad'), short: bi('ML, fairness', 'ML, equidad') },
  { id: 'tests', label: bi('Validation of the tests', 'Validación de las pruebas'), short: bi('Test checks', 'Pruebas') },
];

/** What the families set. */
export const OUTPUTS: readonly FlowDef[] = [
  { id: 'provisions', label: bi('Provisions', 'Provisiones'), short: bi('Provisions', 'Provisiones') },
  { id: 'capital', label: bi('Pillar 1 and ICAAP capital', 'Capital del pilar 1 y del ICAAP'), short: bi('Capital', 'Capital') },
  { id: 'liquidity', label: bi('Liquidity buffers', 'Colchones de liquidez'), short: bi('Liquidity', 'Liquidez') },
  { id: 'decisions', label: bi('Credit decisions and fair lending', 'Decisiones de crédito y equidad'), short: bi('Decisions', 'Decisiones') },
];

/** Where each case sits: its exposure and its family. Authored once, from the exposure and regulatory-use basis of the
 * inventory entries (`tier_block.materiality`); a stated convention of Contraste, never a supervisory classification. */
export const CASE_FLOW: Readonly<Record<string, { exposure: string; family: string }>> = {
  C01: { exposure: 'retail', family: 'scoring' },
  C02: { exposure: 'sme', family: 'scoring' },
  C03: { exposure: 'sme', family: 'scoring' },
  C04: { exposure: 'corporate', family: 'ratings' },
  C05: { exposure: 'corporate', family: 'ratings' },
  C06: { exposure: 'book', family: 'provisions' },
  C07: { exposure: 'book', family: 'provisions' },
  C08: { exposure: 'sme', family: 'lgdead' },
  C09: { exposure: 'retail', family: 'lgdead' },
  C10: { exposure: 'book', family: 'creditcap' },
  C11: { exposure: 'trading', family: 'market' },
  C12: { exposure: 'derivatives', family: 'ccr' },
  C13: { exposure: 'trading', family: 'market' },
  C14: { exposure: 'banking', family: 'irrbb' },
  C15: { exposure: 'banking', family: 'irrbb' },
  C16: { exposure: 'funding', family: 'liquidity' },
  C17: { exposure: 'operations', family: 'oprisk' },
  C18: { exposure: 'capital', family: 'aggregation' },
  C20: { exposure: 'retail', family: 'ml' },
  C21: { exposure: 'mortgages', family: 'ml' },
  C22: { exposure: 'none', family: 'tests' },
};

/** What each family sets, from the regulatory use of its entries (`tier_block.materiality.regulatory_use.basis`). */
export const FAMILY_SETS: Readonly<Record<string, readonly string[]>> = {
  scoring: ['capital', 'decisions'],
  ratings: ['capital'],
  provisions: ['provisions'],
  lgdead: ['capital'],
  creditcap: ['capital'],
  market: ['capital'],
  ccr: ['capital'],
  irrbb: ['capital'],
  liquidity: ['liquidity'],
  oprisk: ['capital'],
  aggregation: ['capital'],
  ml: ['decisions'],
  tests: [],
};

export interface FlowNode extends FlowDef {
  kind: 'exposure' | 'family' | 'output';
  /** The inventory entries in the node. */
  entries: string[];
  /** The findings of those entries, by severity. */
  sev: SevCount;
  total: number;
}
export interface FlowLink {
  from: string;
  to: string;
  entries: number;
  findings: number;
}
export interface Flow {
  entries: number;
  total: number;
  sev: SevCount;
  exposures: FlowNode[];
  families: FlowNode[];
  outputs: FlowNode[];
  links: FlowLink[];
  /** The entries whose case the flow does not place (none for the committed inventory). */
  unmapped: string[];
  familyOfEntry: Map<string, string>;
}

const nodeOf = (kind: FlowNode['kind'], def: FlowDef): FlowNode => ({ ...def, kind, entries: [], sev: zeroSev(), total: 0 });

/** The flow of the bank from the two governance documents: the placing is the stated convention, every count is read. */
export function buildFlow(inv: GovInventory, fin: GovFindings): Flow {
  const exposures = EXPOSURES.map((d) => nodeOf('exposure', d));
  const families = FAMILIES.map((d) => nodeOf('family', d));
  const outputs = OUTPUTS.map((d) => nodeOf('output', d));
  const byId = new Map<string, FlowNode>([...exposures, ...families, ...outputs].map((n) => [`${n.kind}:${n.id}`, n]));
  const sevByEntry = new Map<string, SevCount>();
  for (const r of fin.rows) {
    const s = sevByEntry.get(r.entry_key) ?? zeroSev();
    s[r.severity] += 1;
    sevByEntry.set(r.entry_key, s);
  }
  const links = new Map<string, FlowLink>();
  const unmapped: string[] = [];
  const familyOfEntry = new Map<string, string>();
  const total = zeroSev();
  const bump = (key: string, entry: string, sev: SevCount, n: number) => {
    const node = byId.get(key)!;
    node.entries.push(entry);
    for (const s of SEVERITIES) node.sev[s] += sev[s];
    node.total += n;
  };
  const link = (from: string, to: string, sevN: number) => {
    const k = `${from}>${to}`;
    const l = links.get(k) ?? { from, to, entries: 0, findings: 0 };
    l.entries += 1;
    l.findings += sevN;
    links.set(k, l);
  };
  for (const e of inv.entries) {
    const place = CASE_FLOW[e.case_id];
    if (!place) {
      unmapped.push(e.key);
      continue;
    }
    const sev = sevByEntry.get(e.key) ?? zeroSev();
    const n = SEVERITIES.reduce((a, s) => a + sev[s], 0);
    for (const s of SEVERITIES) total[s] += sev[s];
    familyOfEntry.set(e.key, place.family);
    bump(`exposure:${place.exposure}`, e.key, sev, n);
    bump(`family:${place.family}`, e.key, sev, n);
    link(`exposure:${place.exposure}`, `family:${place.family}`, n);
    for (const out of FAMILY_SETS[place.family] ?? []) {
      bump(`output:${out}`, e.key, sev, n);
      link(`family:${place.family}`, `output:${out}`, n);
    }
  }
  return { entries: inv.entries.length, total: SEVERITIES.reduce((a, s) => a + total[s], 0), sev: total, exposures, families, outputs, links: [...links.values()], unmapped, familyOfEntry };
}

/** The findings of the entries in a family, the most severe first. */
export function findingsOfFamily(flow: Flow, fin: GovFindings, familyId: string): GovFindings['rows'] {
  const rows = fin.rows.filter((r) => flow.familyOfEntry.get(r.entry_key) === familyId);
  return [...rows].sort((a, b) => a.severity.localeCompare(b.severity) || a.key.localeCompare(b.key));
}

/** The three elements of a model validation in SR 11-7, and the evidence of a finding placed under one by the namespace of its
 * first test (`pd`, `market`, `stability`): a stated convention of Contraste, never a supervisory rule. */
export type Element = 'conceptual' | 'monitoring' | 'outcomes';
const ELEMENT_OF_NAMESPACE: Readonly<Record<string, Element>> = {
  design: 'conceptual', contract: 'conceptual', rate: 'conceptual', rating: 'conceptual', disc: 'conceptual', portfolio: 'conceptual', aggregation: 'conceptual',
  stability: 'monitoring', oprisk: 'monitoring', ml: 'monitoring',
  pd: 'outcomes', lgd_ead: 'outcomes', ccr: 'outcomes', market: 'outcomes', liq: 'outcomes', ifrs9: 'outcomes', stress: 'outcomes', fair: 'outcomes', irrbb: 'outcomes',
};
/** The element of an evidence id (`pd.jeffreys@P4`, `design:single-snapshot`, `rate:disc.auc_vs_initial`), or null when its
 * namespace is not placed. */
export function elementOf(evidence: string): Element | null {
  const id = evidence.split('@')[0] ?? evidence;
  const ns = id.includes(':') ? id.split(':')[0]! : id.split('.')[0]!;
  return ELEMENT_OF_NAMESPACE[ns] ?? null;
}
export const ELEMENTS: readonly { id: Element; label: Bi }[] = [
  { id: 'conceptual', label: bi('Conceptual soundness', 'Solidez conceptual') },
  { id: 'monitoring', label: bi('Ongoing monitoring', 'Monitoreo continuo') },
  { id: 'outcomes', label: bi('Outcomes analysis', 'Análisis de resultados') },
];
export function groupByElement(rows: GovFindings['rows']): Record<Element | 'other', GovFindings['rows']> {
  const out: Record<Element | 'other', GovFindings['rows']> = { conceptual: [], monitoring: [], outcomes: [], other: [] };
  for (const r of rows) out[(r.evidence[0] ? elementOf(r.evidence[0]) : null) ?? 'other'].push(r);
  return out;
}

// --- V3 and V4: the window and the Basel traffic light -----------------------------------------------------------------------

export type Zone = 'green' | 'amber' | 'red';
export interface ZoneCuts {
  amberStart: number;
  redStart: number;
}
export const zoneOf = (exceptions: number, cuts: ZoneCuts): Zone => (exceptions >= cuts.redStart ? 'red' : exceptions >= cuts.amberStart ? 'amber' : 'green');

/** Exceptions in the trailing `window` days at each day: element i counts the days max(0, i - window + 1) to i, so it equals the
 * Basel count from day window - 1 on, and is the count of the days so far before it. */
export function trailingCounts(exceedanceDays: readonly number[], n: number, window = 250): number[] {
  const hit = new Uint8Array(n);
  for (const d of exceedanceDays) if (d >= 0 && d < n) hit[d] = 1;
  const out: number[] = [];
  let sum = 0;
  for (let i = 0; i < n; i++) {
    sum += hit[i]!;
    if (i >= window) sum -= hit[i - window]!;
    out.push(sum);
  }
  return out;
}

export interface Tally {
  max: number;
  final: number;
  green: number;
  amber: number;
  red: number;
  windows: number;
}
/** The Basel tally over the complete windows (day 249 on): the maximum, the final count and the days in each zone. */
export function tally(trailing: readonly number[], cuts: ZoneCuts, window = 250): Tally | null {
  if (trailing.length < window) return null;
  const full = trailing.slice(window - 1);
  const t: Tally = { max: 0, final: full.at(-1)!, green: 0, amber: 0, red: 0, windows: full.length };
  for (const c of full) {
    t.max = Math.max(t.max, c);
    t[zoneOf(c, cuts)] += 1;
  }
  return t;
}

export interface ModelPath {
  id: string;
  label: Bi;
  rung: string;
  var: number[];
  es: (number | null)[];
  exceedances: number[];
  /** The exceptions in the trailing 250 days (the days so far before the window is full). */
  trailing: number[];
  n: number;
  expected: number;
  eligible: boolean;
  failedGates: string[];
  /** The document's own tally of the traffic light, or null when the window is shorter than 250 days. */
  light: { max: number; final: number; zone: Zone; green: number; amber: number; red: number } | null;
  /** The tally this module computes from the exceedance days. */
  computed: Tally | null;
}

export interface WindowModel {
  windowId: string;
  title: Bi;
  alpha: number;
  n: number;
  dates: string[];
  cuts: ZoneCuts;
  /** The window has the 250 days the Basel light needs. */
  evaluated: boolean;
  models: ModelPath[];
  loss: number[] | null;
  lossReason: string | null;
  notEvaluatedReason: string | null;
}

/** The window document of a loaded C11 variant at a tail level, or null when the variant is not a window. */
export function windowModel(data: CaseData | null, alpha = 0.01): WindowModel | null {
  const o = outputsOf(data ? { data } : null);
  if (!data || !o) return null;
  const fit = fitOf({ data });
  const cuts: ZoneCuts = { amberStart: zoneStart(fit, 'amber') ?? 5, redStart: zoneStart(fit, 'red') ?? 10 };
  const n = o.grid.dates.length;
  const models: ModelPath[] = [];
  let notEvaluatedReason: string | null = null;
  for (const m of o.models) {
    const lv = levelOf(o, m.model_id, alpha);
    if (!lv) continue;
    const trailing = trailingCounts(lv.exceedance_days, n);
    const tl = lv.traffic_light;
    const evaluated = tl && tl.final_zone !== 'not_evaluated' && tl.max_rolling_exceedances != null;
    if (tl && !evaluated && tl.reason) notEvaluatedReason = tl.reason;
    models.push({
      id: m.model_id,
      label: modelLabel({ data }, m.model_id),
      rung: m.rung,
      var: lv.var,
      es: lv.es,
      exceedances: lv.exceedance_days,
      trailing,
      n: lv.n_scored,
      expected: lv.expected_exceedances,
      eligible: m.eligible,
      failedGates: m.failed_gates,
      light: evaluated && tl ? { max: tl.max_rolling_exceedances!, final: tl.final_rolling_exceedances!, zone: tl.final_zone as Zone, green: tl.days_green!, amber: tl.days_amber!, red: tl.days_red! } : null,
      computed: tally(trailing, cuts),
    });
  }
  const loss = o.grid.realised_loss.status === 'included' ? o.grid.realised_loss.loss : null;
  const w = o.window;
  return {
    windowId: w.window_id,
    title: w.title,
    alpha,
    n,
    dates: o.grid.dates,
    cuts,
    evaluated: n >= 250,
    models,
    loss,
    lossReason: o.grid.realised_loss.reason ?? null,
    notEvaluatedReason,
  };
}

/** The day the cursor opens on: the first day the model's trailing count peaks (the worst of the window), else the last day. */
export function defaultCursor(path: ModelPath | undefined, n: number): number {
  if (!path || path.exceedances.length === 0) return Math.max(0, n - 1);
  let best = 0;
  path.trailing.forEach((c, i) => {
    if (c > path.trailing[best]!) best = i;
  });
  return best;
}

/** The cursor clamped to the window (the selector of the windows changes the number of days). */
export const clampCursor = (cursor: number | null, n: number, fallback: number): number => Math.max(0, Math.min(n - 1, cursor == null || !Number.isFinite(cursor) ? fallback : Math.round(cursor)));

/** The days the model sits outside the green zone: the first and last day of its yellow or red zone, or null. */
export function stressSpan(path: ModelPath, cuts: ZoneCuts): [number, number] | null {
  let a = -1;
  let b = -1;
  path.trailing.forEach((c, i) => {
    if (zoneOf(c, cuts) !== 'green') {
      if (a < 0) a = i;
      b = i;
    }
  });
  return a < 0 ? null : [a, b];
}

/** The lowest and highest VaR across the models on each day: the band the ladder spans. */
export function varEnvelope(models: readonly ModelPath[], n: number): { lo: number[]; hi: number[] } {
  const lo = new Array<number>(n).fill(Infinity);
  const hi = new Array<number>(n).fill(-Infinity);
  for (const m of models) {
    for (let i = 0; i < n; i++) {
      const v = m.var[i];
      if (v == null || !Number.isFinite(v)) continue;
      if (v < lo[i]!) lo[i] = v;
      if (v > hi[i]!) hi[i] = v;
    }
  }
  return { lo, hi };
}

// --- V5: the recalibration --------------------------------------------------------------------------------------------------

export interface Recalibrated {
  modelId: string;
  label: Bi;
  var: number[];
  es: number[];
  workingLevel: number[];
  exceedances: number[];
  trailing: number[];
  rawExceptions: number;
  wrappedExceptions: number;
  expected: number;
  rawKupiec: number | null;
  wrappedKupiec: number | null;
  gamma: number;
  tally: Tally | null;
}

export const wrappedModels = (o: C11Outputs | null): string[] => o?.conformal?.method.wrapped_models ?? [];

/** The adaptive conformal recalibration of a model at a level, read from the conformal block of the window document. */
export function recalibration(data: CaseData | null, modelId: string, alpha = 0.01): Recalibrated | null {
  const o = outputsOf(data ? { data } : null);
  const row = o?.conformal?.rows.find((r) => r.model_id === modelId && r.alpha === alpha);
  if (!data || !o || !o.conformal || !row) return null;
  const n = o.grid.dates.length;
  const trailing = trailingCounts(row.series.exceedance_days, n);
  const fit = fitOf({ data });
  const cuts: ZoneCuts = { amberStart: zoneStart(fit, 'amber') ?? 5, redStart: zoneStart(fit, 'red') ?? 10 };
  return {
    modelId,
    label: modelLabel({ data }, modelId),
    var: row.series.var,
    es: row.series.es,
    workingLevel: row.series.working_level,
    exceedances: row.series.exceedance_days,
    trailing,
    rawExceptions: row.unwrapped.n_exceedances,
    wrappedExceptions: row.wrapped.n_exceedances,
    expected: row.wrapped.expected_exceedances,
    rawKupiec: row.unwrapped.kupiec_p,
    wrappedKupiec: row.wrapped.kupiec_p,
    gamma: o.conformal.method.gamma,
    tally: tally(trailing, cuts),
  };
}

// --- V6: the decision -------------------------------------------------------------------------------------------------------

/** The Wilson score interval of k exceptions in n days (z = 1.96 for 95%), a function of two counts of the document. */
export function wilson(k: number, n: number, z = 1.959964): [number, number] {
  if (n <= 0) return [0, 1];
  const p = k / n;
  const d = 1 + (z * z) / n;
  const centre = (p + (z * z) / (2 * n)) / d;
  const half = (z / d) * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n));
  return [Math.max(0, centre - half), Math.min(1, centre + half)];
}

export interface DecisionRow {
  id: string;
  label: Bi;
  exceptions: number;
  expected: number;
  n: number;
  rate: number;
  lo: number;
  hi: number;
  eligible: boolean;
  failedGates: string[];
  esP: number | null;
  esLight: string | null;
  /** In the model confidence set, or null when the window has no set. */
  inSet: boolean | null;
}
export interface Decision {
  rows: DecisionRow[];
  total: number;
  eligible: number;
  /** The members of the confidence set, or null when the window carries none. */
  setSize: number | null;
  confidence: number | null;
  champion: string | null;
  championReason: string | null;
}

export function decision(data: CaseData | null, w: WindowModel | null, alpha = 0.01): Decision | null {
  const o = outputsOf(data ? { data } : null);
  if (!data || !o || !w) return null;
  const mcs = o.comparison.mcs.find((s) => s.alpha === alpha) ?? null;
  const champ = o.comparison.champions.find((c) => c.alpha === alpha) ?? null;
  const rows = w.models.map((m): DecisionRow => {
    const [lo, hi] = wilson(m.exceedances.length, m.n);
    const es = o.es_backtests.find((e) => e.model_id === m.id && e.alpha === alpha) ?? null;
    const member = mcs?.members.find((x) => x.model_id === m.id) ?? null;
    return {
      id: m.id,
      label: m.label,
      exceptions: m.exceedances.length,
      expected: m.expected,
      n: m.n,
      rate: m.n ? m.exceedances.length / m.n : 0,
      lo,
      hi,
      eligible: m.eligible,
      failedGates: m.failedGates,
      esP: es?.p_value ?? null,
      esLight: null,
      inSet: mcs ? (member ? member.in_set : false) : null,
    };
  });
  return {
    rows,
    total: rows.length,
    eligible: rows.filter((r) => r.eligible).length,
    setSize: mcs ? rows.filter((r) => r.inSet).length : null,
    confidence: mcs?.confidence ?? null,
    champion: champ?.model_id ?? null,
    championReason: champ?.reason ?? null,
  };
}

/** The model and the window the story opens on: the first rung of the ladder in the 2007 to 2009 crisis. */
export const DEFAULT_MODEL = 'hs-250';
export const DEFAULT_WINDOW = 'equity-2007-09';
export { rollingCounts };
