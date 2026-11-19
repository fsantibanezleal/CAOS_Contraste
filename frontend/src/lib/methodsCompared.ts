// The web side of the contract `benchmark-methods` 1.0.0 (docs/contracts/schemas/benchmark-methods.schema.json): the methods of each
// benchmark question side by side, from data/derived/benchmark/methods-compared.json (BL-113). The interfaces type what the schema
// types; the functions here are the page's model: where each question lives, how its rows group by standing, which cell is the best of
// its column, the best method per metric of the overview. Nothing is computed from the cases and nothing is typed in: every number
// and every best mark is read from the document (the standings are the document's own).
import { ArtifactUnavailable, getJSON, useArtifact, type LoadedDeclared } from '../api/artifacts';
import { loadReadiness, unavailableRow } from '../readiness/readiness';
import type { Text } from './contract.types';

export type Standing = 'established' | 'recent' | 'proposed' | 'reference';
export type CellValue = number | string | boolean;

export interface McCite {
  path: string;
  pointer: string;
  sha256: string;
}
export interface McCell {
  metric: string;
  column: string;
  value: CellValue | null;
  null_reason: Text | null;
  cited: McCite | null;
}
export interface McRow {
  id: string;
  method: Text;
  ladder_id: string | null;
  standing: Standing;
  ranked: boolean;
  note: Text | null;
  source: { text: string; url: string | null } | null;
  year: number | null;
  cells: McCell[];
}
export interface McColumn {
  id: string;
  label: Text;
}
export interface McRun {
  id: string;
  label: Text;
  protocol: Text;
  seed: { value: number; cited: McCite } | null;
  files: string[];
  columns: McColumn[];
}
export interface McMetric {
  id: string;
  label: Text;
  run_id: string;
  better: string;
  unit: Text;
  columns: string[];
}
export interface McStanding {
  metric: string;
  column: string;
  best: string[];
  value: CellValue;
  tie: boolean;
  n_ranked: number;
}
export interface McQuestion {
  id: string;
  title: Text;
  case_ids: string[];
  protocol: Text;
  runs: McRun[];
  metrics: McMetric[];
  rows: McRow[];
  absent: Array<{ method: Text; ladder_id: string | null; standing: Standing | null; reason: Text; backlog: string | null }>;
  standings: McStanding[];
  reading: Text;
  negative_results: Array<{ rows: string[]; manuscript: string; text: Text }>;
}
export interface MethodsCompared {
  schema: string;
  case_id: 'BENCHMARK-METHODS';
  schema_version: string;
  provenance: { code_version: string; documents: Array<{ path: string; sha256: string }> };
  questions: McQuestion[];
  left_out: Array<{ ladder_id: string; method: Text; reason: Text }>;
  not_built: Array<{ id: string; title: Text; reason: Text }>;
}

export const METHODS_PATH = 'benchmark/methods-compared.json';

let pending: Promise<MethodsCompared> | undefined;
/** The document, fetched once per release and shared by every section that reads it; a readiness row that lists it absent says so. */
export function loadMethodsCompared(): Promise<MethodsCompared> {
  if (!pending) {
    pending = (async () => {
      const row = unavailableRow(await loadReadiness(), METHODS_PATH);
      if (row) {
        const why = row.reason ?? { en: 'the pipeline did not write it', es: 'la cadena de cálculo no lo escribió' };
        throw new ArtifactUnavailable(METHODS_PATH, { en: `${METHODS_PATH} is not available yet: ${why.en}`, es: `${METHODS_PATH} aún no está disponible: ${why.es}` });
      }
      return getJSON<MethodsCompared>(METHODS_PATH);
    })();
    pending.catch(() => {
      pending = undefined;
    });
  }
  return pending;
}

export function useMethodsCompared(): LoadedDeclared<MethodsCompared> {
  return useArtifact<MethodsCompared>(() => loadMethodsCompared(), [], { unavailable: true });
}

// ---------------------------------------------------------------------------------------------------------------- where it lives

/** The case whose tab holds each question's section (the placement decided on 2026-11-16: the design's "Placement on the page"). */
export const QUESTION_HOME: Readonly<Record<string, string>> = {
  Q1: 'C11',
  Q2: 'C22',
  Q3: 'C13',
  Q4: 'C04',
  Q5: 'C01',
  Q6: 'C06',
  Q7: 'C08',
  Q8: 'C17',
  Q9: 'C14',
  Q10: 'C16',
  Q11: 'C20',
  Q12: 'C01',
};

const qn = (id: string) => Number(id.slice(1));
/** The questions of a case's tab, in order. */
export function questionsOf(caseId: string): string[] {
  return Object.keys(QUESTION_HOME)
    .filter((q) => QUESTION_HOME[q] === caseId)
    .sort((a, b) => qn(a) - qn(b));
}
/** The cases that hold a question, in order. */
export const METHODS_CASES: readonly string[] = [...new Set(Object.values(QUESTION_HOME))].sort();

/** The metrics a question's section does not print because its case tab already prints them: C11's ladder shows each model's exceedances
 * against the expected count per window, so Q1 extends it with the grouping by standing, the other scores and the tests, never repeats it. */
export const OMITTED_METRICS: Readonly<Record<string, readonly string[]>> = { Q1: ['exceed_1', 'expected_1'] };

export const STANDING_ORDER: readonly Standing[] = ['established', 'recent', 'proposed', 'reference'];
export const STANDING_LABEL: Readonly<Record<Standing, Text>> = {
  established: { en: 'Long-established', es: 'De larga data' },
  recent: { en: 'Recent published', es: 'Publicado recientemente' },
  proposed: { en: 'Proposed in this work', es: 'Propuesto en este trabajo' },
  reference: { en: 'Reference', es: 'Referencia' },
};
export const STANDING_NOTE: Readonly<Record<Standing, Text>> = {
  established: { en: 'Methods in use for years, as their sources date them.', es: 'Métodos en uso desde hace años, según la fecha de sus fuentes.' },
  recent: { en: 'Methods published recently, run here on the same protocol.', es: 'Métodos publicados recientemente, ejecutados aquí con el mismo protocolo.' },
  proposed: { en: 'Methods this product proposes, shown winning or losing.', es: 'Métodos que propone este producto, mostrados ganando o perdiendo.' },
  reference: { en: 'An oracle, a band, a baseline or the nominal count: they set the scale and are never ranked as a method.', es: 'Un oráculo, una banda, una línea base o el conteo nominal: fijan la escala y nunca se ordenan como un método.' },
};

// ---------------------------------------------------------------------------------------------------------------- the model

/** The questions of the document that no tab holds: `sections` are the section keys of the page's tabs (`methods:Q1`, ...). A question of the
 * document with no home case, or whose home tab was dropped, is listed here, so the page can never silently lose one. */
export function unplacedQuestions(doc: MethodsCompared, sections: readonly string[]): string[] {
  return doc.questions.map((q) => q.id).filter((id) => !sections.includes(`methods:${id}`) || !QUESTION_HOME[id]);
}

/** A document text in the page language, its decimals in the Spanish form (a comma) on the Spanish page: the document writes a decimal with a point in both
 * languages. A number with a zero integer part, or a fraction of other than three digits, is a decimal; "1.000" stays a thousand. */
export function localDecimals(text: string, lang: 'en' | 'es'): string {
  if (lang === 'en') return text;
  return text.replace(/(?<![\w.,])(\d+)\.(\d+)(?![\w.])/g, (m, a: string, b: string) => (a === '0' || b.length !== 3 ? `${a},${b}` : m));
}
/** The text of a bilingual document field in the page language. */
export const docText = (t: Text, lang: 'en' | 'es'): string => localDecimals(lang === 'es' ? t.es : t.en, lang);

export const isRanked = (m: McMetric) => m.better !== 'none';
export const isNumeric = (v: CellValue | null): v is number => typeof v === 'number' && Number.isFinite(v);

/** The metrics a question's section prints, in the document's order. */
export function metricsOf(q: McQuestion): McMetric[] {
  const omit = OMITTED_METRICS[q.id] ?? [];
  return q.metrics.filter((m) => !omit.includes(m.id));
}

/** The run a metric belongs to. */
export function runOf(q: McQuestion, m: McMetric): McRun {
  return q.runs.find((r) => r.id === m.run_id) ?? q.runs[0];
}

/** The label of a column of a metric (its window, scenario, vintage or level), from the run. */
export function columnLabel(q: McQuestion, m: McMetric, columnId: string): Text {
  return runOf(q, m).columns.find((c) => c.id === columnId)?.label ?? { en: columnId, es: columnId };
}

/** The columns split into pages of at most `size`, so a table never grows wide: a long one is split by window, never scrolled sideways. */
export function chunkColumns<T>(columns: readonly T[], size = 3): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < columns.length; i += size) out.push(columns.slice(i, i + size));
  return out;
}

export interface TableRow {
  row: McRow;
  /** One cell per displayed column, undefined where the row has none. */
  cells: Array<McCell | undefined>;
  /** One flag per displayed column: this row is the best (or tied for the best) of that column, by the document's standing. */
  best: boolean[];
}
export interface TableGroup {
  standing: Standing;
  rows: TableRow[];
}

/** The rows of a question that carry a cell of the metric, grouped by standing in the order of the page, with the best of each column marked
 * from the document's standings. A group with no row is dropped. */
export function tableGroups(q: McQuestion, metric: McMetric, columns: readonly string[]): TableGroup[] {
  const bestOf = new Map<string, { ids: Set<string>; value: CellValue }>();
  for (const s of q.standings) if (s.metric === metric.id) bestOf.set(s.column, { ids: new Set(s.best), value: s.value });
  const rows = q.rows.filter((r) => r.cells.some((c) => c.metric === metric.id));
  return STANDING_ORDER.map((standing) => ({
    standing,
    rows: rows
      .filter((r) => r.standing === standing)
      .map((row) => ({
        row,
        cells: columns.map((col) => row.cells.find((c) => c.metric === metric.id && c.column === col)),
        // the best of a column is the document's, and so is every cell equal to it at full precision (a tie the printed digits would hide)
        best: columns.map((col) => {
          const b = bestOf.get(col);
          const v = row.cells.find((c) => c.metric === metric.id && c.column === col)?.value;
          return !!b && (b.ids.has(row.id) || (row.ranked && v !== null && v !== undefined && v === b.value));
        }),
      })),
  })).filter((g) => g.rows.length > 0);
}

/** The significant digits a column prints with: the default (4), or the fewest that separate the best cell from every cell that differs from it
 * at full precision, so two cells printing alike never hide which one is the best. */
export function columnDigits(values: ReadonlyArray<{ value: number; best: boolean }>, base = 4): number {
  const best = values.filter((v) => v.best);
  if (!best.length) return base;
  for (let d = base; d <= 15; d++) {
    const printed = new Set(best.map((b) => b.value.toPrecision(d)));
    if (values.every((v) => v.best || !printed.has(v.value.toPrecision(d)))) return d;
  }
  return 15;
}
/** The digits of each displayed column of a table. */
export function columnPrecision(groups: readonly TableGroup[], columnCount: number): number[] {
  return Array.from({ length: columnCount }, (_, i) =>
    columnDigits(groups.flatMap((g) => g.rows.flatMap((r) => (isNumeric(r.cells[i]?.value ?? null) ? [{ value: r.cells[i]!.value as number, best: r.best[i] }] : [])))),
  );
}

export interface BarPoint {
  id: string;
  standing: Standing;
  method: Text;
  value: number;
  best: boolean;
}
/** The bars of one metric at one column: every row with a number there, in the table's order. */
export function barPoints(q: McQuestion, metric: McMetric, column: string): BarPoint[] {
  return tableGroups(q, metric, [column]).flatMap((g) =>
    g.rows.flatMap((r) => {
      const v = r.cells[0]?.value;
      return isNumeric(v ?? null) ? [{ id: r.row.id, standing: g.standing, method: r.row.method, value: v as number, best: r.best[0] }] : [];
    }),
  );
}

/** The metric the section opens on: the first ranked one with numbers, else the first. */
export function defaultMetric(q: McQuestion): McMetric {
  const ms = metricsOf(q);
  return ms.find((m) => isRanked(m) && q.rows.some((r) => r.cells.some((c) => c.metric === m.id && isNumeric(c.value)))) ?? ms[0];
}

export interface Winner {
  row_id: string;
  method: Text;
  standing: Standing;
  /** The columns of the metric where it is the best (a tie counts for each method tied). */
  wins: number;
  of: number;
}
export interface MetricBest {
  metric: McMetric;
  winners: Winner[];
  /** A method proposed in this work is among the winners of the metric. */
  proposedBest: boolean;
}
/** The best method of each ranked metric, by the document's standings: the method best on the most columns, every method tied on that count
 * named (the rule the document's own reading states). */
export function bestPerMetric(q: McQuestion): MetricBest[] {
  const rowOf = new Map(q.rows.map((r) => [r.id, r]));
  return metricsOf(q)
    .filter(isRanked)
    .flatMap((metric) => {
      const st = q.standings.filter((s) => s.metric === metric.id);
      if (!st.length) return [];
      const count = new Map<string, number>();
      for (const s of st) for (const id of s.best) count.set(id, (count.get(id) ?? 0) + 1);
      const top = Math.max(...count.values());
      const winners = [...count.entries()]
        .filter(([, n]) => n === top)
        .flatMap(([id, n]) => {
          const row = rowOf.get(id);
          return row ? [{ row_id: id, method: row.method, standing: row.standing, wins: n, of: st.length }] : [];
        });
      return [{ metric, winners, proposedBest: winners.some((w) => w.standing === 'proposed') }];
    });
}

export interface OverviewRow {
  question: McQuestion;
  home: string;
  /** The first sentence of the protocol. */
  protocol: Text;
  best: MetricBest[];
  /** The question has a method proposed in this work. */
  hasProposed: boolean;
  /** The ranked metrics where a method proposed in this work is the best, and the ranked metrics. */
  proposedWins: number;
  ranked: number;
}

/** A protocol in one line: its first sentence. */
export function firstSentence(text: string): string {
  const m = text.match(/^.*?[.;](?=\s|$)/s);
  return (m ? m[0] : text).replace(/[;]$/, '.').trim();
}

export function overviewRows(doc: MethodsCompared): OverviewRow[] {
  return doc.questions.map((question) => {
    const best = bestPerMetric(question);
    return {
      question,
      home: QUESTION_HOME[question.id] ?? question.case_ids[0],
      protocol: { en: firstSentence(question.protocol.en), es: firstSentence(question.protocol.es) },
      best,
      hasProposed: question.rows.some((r) => r.standing === 'proposed'),
      proposedWins: best.filter((b) => b.proposedBest).length,
      ranked: best.length,
    };
  });
}
