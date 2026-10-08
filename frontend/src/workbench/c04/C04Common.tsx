// C04's Findings, Variants and Context groups, and the live read-outs of its rail (ADR-0017 rule 3: every section
// shows a value that moves with its controls). Replayed numbers are read from the committed artifacts; live ones come
// from engine/transitions.ts through selection.ts's hooks. Every PD names its definition, every CEREP-derived card
// names the agency's EU entity and carries ESMA's attribution, and no chart is drawn without a value to draw.
import { PlotCard, Readout, Verdict, formatNumber, pick, useShellLang, useWorkbenchState, type BiText, type Lane, type Provenance, type ReadoutItem, type ShellColorToken, type Tone } from '@fasl-work/caos-app-shell';
import { UPlotChart, type ChartSeries, type UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { useMemo } from 'react';
import { C04WriteUp } from '../../content/cases/C04';
import {
  ATTRIBUTION_FALLBACK,
  C04Results,
  GENERATOR_TEXT,
  LoadError,
  SEVERITY_TEXT,
  STATUS_TEXT,
  TRUTH_TEXT,
  atPrintedDigits,
  d4EmptyYears,
  familyDesign,
  impactValue,
  kindsOf,
  pText,
  paperAgreements,
  pctText,
  shortOf,
  sortFindings,
  testName,
  titleOf,
  useC04Variants,
  yearRanges,
  type Lang,
} from '../../content/cases/C04Results';
import { pdJeffreys, project, type Projection } from '../../engine/transitions';
import type {
  C04CycleRung,
  C04Fit,
  C04MarkovRung,
  C04MomentumRung,
  C04Performance,
  C04Simulation,
  C04ThinRung,
  C04WithdrawalsRung,
  Finding,
  ModelsArtifact,
  TestRow,
  VariantArtifact,
} from '../../lib/contract.types';
import { COMMITTED, LIGHT_TEXT } from '../../lib/policy';
import { REPLAY, provenanceOf } from '../model';
import { Pending } from '../Pending';
import {
  DEFINITION_COLOR,
  DEFINITION_HINT,
  DEFINITION_LABEL,
  DEFINITIONS,
  ESMA_DEFINITIONS,
  ESTIMATOR_LABEL,
  GRADE_AXIS,
  GRADES,
  START_LABEL,
  gradeCounts,
  isAgency,
  isFamily,
  isPublished,
  startPortfolio,
  useIntervals,
  useProjection,
  type AgencyVariant,
  type C04Sel,
  type Definition,
  type FamilyVariant,
  type PublishedVariant,
  P_FLOOR,
} from './selection';

const LIVE = 'live' as const;
/** Both languages of a string built here, readable field by field (a BiText may be a plain string). */
type Bi = { en: string; es: string };
const bi = (t: BiText): Bi => ({ en: pick(t, 'en'), es: pick(t, 'es') });
/** A string built once per language, so each number is formatted in its own language. */
const both = (f: (lang: Lang) => string): Bi => ({ en: f('en'), es: f('es') });
const sum = (a: readonly number[]) => a.reduce((s, x) => s + x, 0);
const finite = (x: number | null | undefined): x is number => x !== null && x !== undefined && Number.isFinite(x);

/** The momentum rung whose fitted hazard coefficient matches dos Reis, Pfeuffer and Smith's estimate on Moody's data
 * (design.md, the momentum variant). */
export const EMPIRICAL_ALPHA = 0.125;

export type C04Chart = Pick<UPlotChartProps, 'x' | 'y' | 'series' | 'marks'>;

/** The series that hold a value to draw; a series of nothing but gaps is left out (it would draw an empty chart). */
export function nonEmpty(series: ChartSeries[]): ChartSeries[] {
  return series.filter((s) => s.values.some(finite));
}

/** An axis of n numbered positions with half a position of room at each end (a mark's label at the last position is
 * drawn inside the plot), and a series padded to it. */
const numbered = (n: number) => [0.5, ...Array.from({ length: n }, (_, i) => i + 1), n + 0.5];
const pad = (vals: ReadonlyArray<number | null>): Array<number | null> => [null, ...vals, null];
/** The grade axis, padded: x = 1 (AAA) to 7 (CCC-C). */
const gradeAxis = (): UPlotChartProps['x'] => ({ values: numbered(GRADES.length), label: GRADE_AXIS, format: { decimals: 0 } });
const gradeMark = (g: number) => [{ x: g + 1, label: { en: GRADES[g], es: GRADES[g] } }];

const SCOPE_ES: Record<string, string> = { 'corporate, long-term, categories': 'corporativas, largo plazo, categorías' };

/** "Source: ESMA CEREP; ..." and the EU entity, for a card whose numbers come from an agency's CEREP pages (the
 * attribution is the source's own wording, kept verbatim in both languages). */
function cerepLine(v: AgencyVariant): Bi {
  const o = v.outputs;
  const att = o.attribution || ATTRIBUTION_FALLBACK;
  return {
    en: `${o.agency.name} (${o.agency.code}), ratings ${o.agency.scope}. ${att}.`,
    es: `${o.agency.name} (${o.agency.code}), calificaciones ${SCOPE_ES[o.agency.scope] ?? o.agency.scope}. ${att}.`,
  };
}

/** "S&P's", "Moody's" (a name that already ends in 's). */
const possessive = (name: string) => (/'s$/.test(name) ? name : `${name}'s`);

// ---------------------------------------------------------------------------------------------------------------------
// Findings

export type Cited =
  | { kind: 'test'; row: TestRow }
  | { kind: 'rate'; sim: C04Simulation; family: FamilyVariant }
  | { kind: 'design'; key: string }
  | { kind: 'missing' };

/** What a finding's evidence names: a test row ("test@model@segment"), a measured rate ("rate:<key>") or the block of
 * the outputs the bake computed the finding from ("design:<block>"). */
export function citedOf(v: VariantArtifact<unknown>, ref: string): Cited {
  if (ref.startsWith('design:')) return { kind: 'design', key: ref.slice(7) };
  if (ref.startsWith('rate:')) {
    if (!isFamily(v)) return { kind: 'missing' };
    const sim = v.outputs.simulations.find((s) => s.key === ref.slice(5));
    return sim ? { kind: 'rate', sim, family: v } : { kind: 'missing' };
  }
  const [testId, model, segment] = ref.split('@');
  const row = v.tests.find(
    (t) => t.test_id === testId && t.model_id === model && (segment === undefined ? t.segment === null || t.segment === 'portfolio' : t.segment === segment),
  );
  return row ? { kind: 'test', row } : { kind: 'missing' };
}

export interface EvidencePoint {
  key: string;
  finding: string;
  cited: Cited;
}

/** The outputs blocks a "design:" evidence names that the Findings view draws: those of the variants whose findings
 * cite no p-value and no measured rate (the withdrawals and thin families, the papers), so that their evidence is
 * drawn beside the findings as every other variant's is. Any other block is named in the table and drawn in its group. */
export function designDrawn(v: VariantArtifact<unknown>, key: string): boolean {
  if (isPublished(v)) return key === 'irw' || key === 'sr190' || key === 'engelmann';
  if (!isFamily(v)) return false;
  if (v.outputs.family === 'withdrawals') return key === 'rungs.pd_removed' || key === 'rungs.pd_followed';
  if (v.outputs.family === 'thin') return key === 'rungs.coverage' || key === 'rungs.overlap_jeffreys';
  return false;
}

export type EvidenceKind = 'p' | 'rate' | 'design';

/** The findings by severity, and the evidence the view draws numbered in reading order (the table's [k], the chart's
 * position or series): the cited tests' p-values where the findings cite any; else the measured rates; else the design
 * blocks the view draws. `kind` is null when nothing cited can be drawn. */
export function findingsEvidence(v: VariantArtifact<unknown>): { findings: Finding[]; points: EvidencePoint[]; kind: EvidenceKind | null } {
  const findings = sortFindings(v.findings);
  const all = findings.flatMap((f) => f.evidence.map((ref) => ({ key: `${f.id}|${ref}`, finding: f.id, cited: citedOf(v, ref) })));
  const tests = all.filter((p) => p.cited.kind === 'test' && p.cited.row.p_value !== null);
  if (tests.length) return { findings, points: tests, kind: 'p' };
  const rates = all.filter((p) => p.cited.kind === 'rate');
  if (rates.length) return { findings, points: rates, kind: 'rate' };
  const designs = all.filter((p) => p.cited.kind === 'design' && designDrawn(v, p.cited.key));
  if (designs.length) return { findings, points: designs, kind: 'design' };
  return { findings, points: [], kind: null };
}

/** A short findings table (few findings, few cited items) sits at its own height above the drawing of its evidence,
 * which fills the rest of the view; a long one scrolls in a card beside the drawing. */
export const COMPACT_ROWS = 6;
export const isCompact = (findings: readonly Finding[]) => findings.length + sum(findings.map((f) => f.evidence.length)) <= COMPACT_ROWS;

/** The lowest p-value the log axis draws (selection.P_FLOOR, the one floor of every C04 p-value chart and C01's): the
 * agencies' reference tests reach 1.9e-124 and their time homogeneity underflows to 0, and the shell 0.9.0 never draws a
 * log axis below about 1e-22 (known shell defect 31). Every p-value under the floor is drawn at it, in a series of its
 * own that says so; the table prints each one. */
export { P_FLOOR };

export interface PValueChart extends C04Chart {
  /** the cited years the finding names, at their numbers */
  marks: Array<{ x: number; label: BiText }>;
  floor: number;
  /** the p-values under the floor, the underflowed zeros among them */
  below: number;
  zeros: number;
  amber: number;
  red: number;
  policy: string;
}

/** Marks at 1-based numbers, labelled; a run of consecutive numbers shares one label ("2020-2021"), its other lines
 * bare, so neighbouring labels never print over each other. */
function runMarks(items: ReadonlyArray<{ i: number; label: string }>): Array<{ x: number; label: BiText }> {
  const sorted = [...items].sort((a, b) => a.i - b.i);
  const out: Array<{ x: number; label: BiText }> = [];
  for (let k = 0; k < sorted.length; k++) {
    if (k > 0 && sorted[k].i === sorted[k - 1].i + 1) {
      out.push({ x: sorted[k].i + 1, label: '' });
      continue;
    }
    let end = k;
    while (end + 1 < sorted.length && sorted[end + 1].i === sorted[end].i + 1) end++;
    const label = end > k ? `${sorted[k].label}-${sorted[end].label}` : sorted[k].label;
    out.push({ x: sorted[k].i + 1, label });
  }
  return out;
}

/** The years a reference finding names: the three cited reference tests (a year's matrix against the pooled one) with
 * the largest likelihood ratio per degree of freedom, as the bake ranks them (ties in citation order). */
export function namedYears(rows: ReadonlyArray<TestRow | null>): Array<{ i: number; label: string }> {
  const perDof = (r: TestRow) => (r.statistic as number) / Math.max(typeof r.extras.dof === 'number' ? r.extras.dof : 1, 1);
  return rows
    .flatMap((r, i) => (r && r.test_id === 'rating.matrix_reference' && finite(r.statistic) ? [{ i, r }] : []))
    .sort((a, b) => perDof(b.r) - perDof(a.r) || a.i - b.i)
    .slice(0, 3)
    .map(({ i, r }) => ({ i, label: String(r.segment) }));
}

/** The cited tests' p-values on a log axis against the policy's thresholds, coloured by the light they earn; those
 * under P_FLOOR are drawn at it (see P_FLOOR). The years the finding names are marked. Null when no cited test has a
 * p-value. */
export function pValueChart(points: EvidencePoint[]): PValueChart | null {
  const rows = points.map((p) => (p.cited.kind === 'test' ? p.cited.row : null));
  const ps = rows.map((r) => r?.p_value ?? null);
  if (!ps.some((p) => p !== null)) return null;
  const policyRow = rows.find((r) => r && r.alpha_amber !== null && r.alpha_red !== null);
  const amber = policyRow?.alpha_amber ?? COMMITTED.amber;
  const red = policyRow?.alpha_red ?? COMMITTED.red;
  const xs = numbered(ps.length);
  const where = (pred: (p: number) => boolean) => pad(ps.map((p) => (p !== null && pred(p) ? p : null)));
  const a = both((l) => formatNumber(amber, l, { digits: 2 }));
  const r = both((l) => formatNumber(red, l, { digits: 2 }));
  const fl = both((l) => formatNumber(P_FLOOR, l, { digits: 2 }));
  const drawn = nonEmpty([
    { label: { en: `Red: p below ${r.en}`, es: `Rojo: p bajo ${r.es}` }, values: where((p) => p >= P_FLOOR && p < red), color: '--color-bad', mode: 'points' },
    { label: { en: `Amber: p from ${r.en} to ${a.en}`, es: `Ámbar: p de ${r.es} a ${a.es}` }, values: where((p) => p >= red && p < amber), color: '--color-warn', mode: 'points' },
    { label: { en: `Green: p from ${a.en}`, es: `Verde: p desde ${a.es}` }, values: where((p) => p >= amber), color: '--color-good', mode: 'points' },
    { label: { en: `Red, p below ${fl.en}: drawn at ${fl.en}`, es: `Rojo, p bajo ${fl.es}: dibujado en ${fl.es}` }, values: where((p) => p < P_FLOOR).map((p) => (p === null ? null : P_FLOOR)), color: '--color-magenta', mode: 'points' },
  ]);
  if (!drawn.length) return null;
  return {
    x: { values: xs, label: { en: 'Cited test (the number in the table)', es: 'Prueba citada (el número de la tabla)' }, format: { decimals: 0 } },
    y: { label: { en: 'p-value (log scale)', es: 'Valor p (escala log.)' }, log: true, format: { digits: 2 } },
    series: [
      ...drawn,
      { label: { en: `Amber threshold ${a.en}`, es: `Umbral ámbar ${a.es}` }, values: xs.map(() => amber), color: '--color-warn', width: 1.2, dash: [6, 4] },
      { label: { en: `Red threshold ${r.en}`, es: `Umbral rojo ${r.es}` }, values: xs.map(() => red), color: '--color-bad', width: 1.2, dash: [2, 4] },
    ],
    marks: runMarks(namedYears(rows)),
    floor: P_FLOOR,
    below: ps.filter((p) => p !== null && p < P_FLOOR).length,
    zeros: ps.filter((p) => p === 0).length,
    amber,
    red,
    policy: policyRow?.policy_version ?? '',
  };
}

const AT5 = 'p<0.05';
const AT1 = 'p<0.01';

/** The cited measured rates at 5% with the Wilson interval of each and at 1%, against the nominal levels; the rates at
 * the empirical momentum (alpha 0.125) are marked. Null when the findings cite no rate. */
export function rateChart(points: EvidencePoint[]): C04Chart | null {
  const sims = points.map((p) => (p.cited.kind === 'rate' ? p.cited.sim : null));
  if (!sims.some(Boolean)) return null;
  const xs = numbered(sims.length);
  const at = (key: string, f: 'rate' | 'wilson_low' | 'wilson_high') => pad(sims.map((s) => s?.rates[key]?.[f] ?? null));
  const drawn = nonEmpty([
    { label: { en: 'Rate at 5%', es: 'Tasa al 5%' }, values: at(AT5, 'rate'), color: '--color-accent', mode: 'points' },
    { label: { en: 'Wilson 95% of the 5% rate, low', es: 'Wilson 95% de la tasa al 5%, inferior' }, values: at(AT5, 'wilson_low'), color: '--color-fg-subtle', mode: 'points' },
    { label: { en: 'Wilson 95% of the 5% rate, high', es: 'Wilson 95% de la tasa al 5%, superior' }, values: at(AT5, 'wilson_high'), color: '--color-fg-subtle', mode: 'points' },
    { label: { en: 'Rate at 1%', es: 'Tasa al 1%' }, values: at(AT1, 'rate'), color: '--color-magenta', mode: 'points' },
  ]);
  if (!drawn.length) return null;
  return {
    x: { values: xs, label: { en: 'Cited rate (the number in the table)', es: 'Tasa citada (el número de la tabla)' }, format: { decimals: 0 } },
    y: { label: { en: 'Rejection rate', es: 'Tasa de rechazo' }, format: { percent: true, decimals: 0 }, range: [0, 1] },
    series: [
      ...drawn,
      { label: { en: 'Nominal 5%', es: 'Nominal 5%' }, values: xs.map(() => 0.05), color: '--color-warn', width: 1.2, dash: [6, 4] },
      { label: { en: 'Nominal 1%', es: 'Nominal 1%' }, values: xs.map(() => 0.01), color: '--color-bad', width: 1.2, dash: [2, 4] },
    ],
    marks: sims.flatMap((s, i) =>
      s && s.key.includes('@alpha') && s.rung !== null && Math.abs(s.rung - EMPIRICAL_ALPHA) < 1e-12
        ? [{ x: i + 1, label: { en: `alpha ${formatNumber(EMPIRICAL_ALPHA, 'en', { digits: 3 })}, empirical`, es: `alfa ${formatNumber(EMPIRICAL_ALPHA, 'es', { digits: 3 })}, empírico` } }]
        : [],
    ),
  };
}

/** A drawing of design evidence: the chart, its card's title and what its note says. */
export interface DesignChart extends C04Chart {
  title: BiText;
  note: Bi;
}

/** "[k] " before a series label: the number of the design evidence it draws, as the table prints it. */
function tagOf(points: EvidencePoint[]): (key: string) => string {
  return (key) => {
    const i = points.findIndex((p) => p.cited.kind === 'design' && p.cited.key === key);
    return i >= 0 ? `[${i + 1}] ` : '';
  };
}

/** A performance block's bias as a share of the truth, by grade (null where the truth is zero or the bias undefined). */
export function relativeBias(p: C04Performance): Array<number | null> {
  return p.bias.map((b, g) => (finite(b) && finite(p.truth[g]) && p.truth[g] > 0 ? b / p.truth[g] : null));
}

/** The withdrawals family's cited blocks: the bias of the one-year PD over the truth, as a share of it, by grade, with
 * withdrawals removed (CEREP's transition page, D4) and followed to the year end (EBA/GL/2017/16 paragraphs 73 and 76)
 * at the strongest informative withdrawal, and removed without informativeness. */
export function withdrawalsChart(f: FamilyVariant, points: EvidencePoint[], grade: number): DesignChart | null {
  const rungs = f.outputs.rungs as C04WithdrawalsRung[];
  const top = rungs[rungs.length - 1];
  const base = rungs[0];
  if (!top || !base || top === base || !top.pd_removed || !top.pd_followed) return null;
  const tag = tagOf(points);
  const k = (r: C04WithdrawalsRung) => both((l) => formatNumber(r.value, l, { digits: 3 }));
  const kTop = k(top);
  const kBase = k(base);
  const xs = numbered(GRADES.length);
  const drawn = nonEmpty([
    {
      label: { en: `${tag('rungs.pd_removed')}Removed (${pick(DEFINITION_LABEL.d4, 'en')}), k ${kTop.en}`, es: `${tag('rungs.pd_removed')}Eliminados (${pick(DEFINITION_LABEL.d4, 'es')}), k ${kTop.es}` },
      values: pad(relativeBias(top.pd_removed)),
      color: DEFINITION_COLOR.d4,
      width: 2.4,
    },
    {
      label: { en: `${tag('rungs.pd_followed')}Followed to the year end, k ${kTop.en}`, es: `${tag('rungs.pd_followed')}Seguidos hasta el fin del año, k ${kTop.es}` },
      values: pad(relativeBias(top.pd_followed)),
      color: '--color-accent',
      width: 2.4,
    },
    {
      label: { en: `Removed, k ${kBase.en}: withdrawals not informative`, es: `Eliminados, k ${kBase.es}: retiros no informativos` },
      values: pad(relativeBias(base.pd_removed)),
      color: DEFINITION_COLOR.d4,
      width: 1.2,
      dash: [6, 4],
    },
  ]);
  if (!drawn.length) return null;
  const reps = both((l) => formatNumber(f.outputs.design.reps, l));
  return {
    title: { en: 'The cited biases by grade: withdrawals removed and followed', es: 'Los sesgos citados por grado: retiros eliminados y seguidos' },
    x: gradeAxis(),
    y: { label: { en: 'Bias of the one-year PD over the truth', es: 'Sesgo de la PD anual sobre la verdad' }, unit: { en: '% of the truth', es: '% de la verdad' }, format: { percent: true, decimals: 0 } },
    series: [...drawn, { label: { en: 'No bias', es: 'Sin sesgo' }, values: xs.map(() => 0), color: '--color-fg-subtle', width: 1, dash: [2, 4] }],
    marks: gradeMark(grade),
    note: {
      en: `The mean one-year PD over ${reps.en} repetitions minus the true PD, as a share of it, by grade: withdrawals removed from the denominator (CEREP's transition page) and each withdrawn obligor followed to the year end (EBA/GL/2017/16 paragraphs 73 and 76), at the strongest informative withdrawal (k ${kTop.en}: the withdrawal rate times 1 + k in the year before a default) and, dashed, removed with withdrawals not informative (k ${kBase.en}). The top grades' few defaults make their shares noisy; their Monte Carlo errors are in the Validation group. Marked: the rail's grade.`,
      es: `La PD anual media en ${reps.es} repeticiones menos la PD verdadera, como fracción de ella, por grado: retiros eliminados del denominador (la página de transiciones de CEREP) y cada deudor retirado seguido hasta el fin del año (párrafos 73 y 76 de EBA/GL/2017/16), con el retiro informativo más fuerte (k ${kTop.es}: la tasa de retiro por 1 + k en el año previo a un incumplimiento) y, segmentada, eliminados con retiros no informativos (k ${kBase.es}). Los pocos incumplimientos de los mejores grados hacen ruidosas sus fracciones; sus errores de Monte Carlo están en el grupo Validación. Marcado: el grado del panel.`,
    },
  };
}

/** The thin family's cited blocks: each interval's exact coverage by grade at the smallest cohort, and the overlap of
 * the Jeffreys intervals of a grade and the next at the largest, both exact by enumeration. */
export function thinChart(f: FamilyVariant, points: EvidencePoint[], grade: number): DesignChart | null {
  const rungs = f.outputs.rungs as C04ThinRung[];
  const small = rungs[0];
  const large = rungs[rungs.length - 1];
  if (!small || !large || !small.coverage) return null;
  const tag = tagOf(points);
  const cov = tag('rungs.coverage');
  const ovl = tag('rungs.overlap_jeffreys');
  const n = (r: C04ThinRung) => both((l) => formatNumber(r.value, l));
  const ns = n(small);
  const nl = n(large);
  const level = both((l) => formatNumber(small.level, l, { percent: true, decimals: 0 }));
  const xs = numbered(GRADES.length);
  const drawn = nonEmpty([
    { label: { en: `${cov}Wald coverage, ${ns.en} obligors`, es: `${cov}Cobertura de Wald, ${ns.es} deudores` }, values: pad(small.coverage.wald), color: '--color-bad', width: 2.2 },
    { label: { en: `${cov}Agresti-Coull coverage, ${ns.en} obligors`, es: `${cov}Cobertura de Agresti-Coull, ${ns.es} deudores` }, values: pad(small.coverage.agresti_coull), color: '--color-warn', width: 2.2 },
    { label: { en: `${cov}Jeffreys coverage, ${ns.en} obligors`, es: `${cov}Cobertura de Jeffreys, ${ns.es} deudores` }, values: pad(small.coverage.jeffreys), color: '--color-accent', width: 2.2 },
    {
      label: { en: `${ovl}Jeffreys intervals of the grade and the next overlap, ${nl.en} obligors`, es: `${ovl}Los intervalos de Jeffreys del grado y el siguiente se traslapan, ${nl.es} deudores` },
      values: pad(GRADES.map((_, g) => (g < GRADES.length - 1 ? (large.overlap_jeffreys[g] ?? null) : null))),
      color: '--color-magenta',
      width: 2,
      dash: [6, 4],
    },
  ]);
  if (!drawn.length) return null;
  return {
    title: { en: `Exact coverage with ${ns.en} obligors; adjacent grades' overlap with ${nl.en}`, es: `Cobertura exacta con ${ns.es} deudores; traslape de grados adyacentes con ${nl.es}` },
    x: gradeAxis(),
    y: { label: { en: 'Probability', es: 'Probabilidad' }, unit: { en: '%', es: '%' }, range: [0, 1], format: { percent: true, decimals: 0 } },
    series: [...drawn, { label: { en: `Nominal ${level.en}`, es: `Nominal ${level.es}` }, values: xs.map(() => small.level), color: '--color-fg-subtle', width: 1, dash: [2, 4] }],
    marks: gradeMark(grade),
    note: {
      en: `${cov}The probability that each ${level.en} interval holds the grade's true one-year PD with ${ns.en} obligors observed for a year, exact by enumerating the binomial counts (no Monte Carlo error); dotted, the nominal ${level.en}. ${ovl}The probability that the ${level.en} Jeffreys intervals of the grade and the next one overlap with ${nl.en} obligors a grade (CCC-C has no next grade). Marked: the rail's grade.`,
      es: `${cov}La probabilidad de que cada intervalo al ${level.es} contenga la PD anual verdadera del grado con ${ns.es} deudores observados un año, exacta enumerando los conteos binomiales (sin error de Monte Carlo); punteada, el ${level.es} nominal. ${ovl}La probabilidad de que los intervalos de Jeffreys al ${level.es} del grado y del siguiente se traslapen con ${nl.es} deudores por grado (CCC-C no tiene grado siguiente). Marcado: el grado del panel.`,
    },
  };
}

type PaperId = 'irw' | 'sr190' | 'engelmann';
const PAPERS: PaperId[] = ['irw', 'sr190', 'engelmann'];
const PAPER_NAME: Record<PaperId, Bi> = {
  irw: { en: 'Israel, Rosenthal and Wei', es: 'Israel, Rosenthal y Wei' },
  sr190: { en: 'Schuermann and Hanson, Table 5', es: 'Schuermann y Hanson, Tabla 5' },
  engelmann: { en: 'Engelmann', es: 'Engelmann' },
};
const PAPER_COLOR: Record<PaperId, ShellColorToken> = { irw: '--color-accent', sr190: '--color-accent-2', engelmann: '--color-good' };

/** One printed value of the papers beside its recomputation and how it agrees: at the printed digits (Israel et al.'s
 * and Table 5's rows as the bake judged them, each value of a Table 5 row with its row; N dagger and Engelmann's values
 * at their stored decimals), or within the rounding of its printed entries (Engelmann's W hat). */
export interface PrintCheck {
  paper: PaperId;
  printed: number;
  recomputed: number;
  check: 'agrees' | 'differs' | 'rounding';
}

export function printChecks(p: PublishedVariant): PrintCheck[] {
  const o = p.outputs;
  const out: PrintCheck[] = [];
  const at = (paper: PaperId, printed: number, recomputed: number, agrees: boolean) => out.push({ paper, printed, recomputed, check: agrees ? 'agrees' : 'differs' });
  for (const r of o.irw.rows) at('irw', r.printed, r.recomputed, r.agrees);
  for (const r of o.sr190.rows) r.printed.forEach((x, i) => at('sr190', x, r.recomputed[i], r.agrees));
  const nd = o.sr190.n_dagger;
  nd.printed.forEach((x, i) => at('sr190', x, nd.recomputed[i], atPrintedDigits(x, nd.recomputed[i], nd.decimals[i])));
  const e = o.engelmann;
  e.w_ttc.printed.forEach((x, i) => at('engelmann', x, e.w_ttc.recomputed[i], atPrintedDigits(x, e.w_ttc.recomputed[i], e.w_ttc.decimals[i])));
  at('engelmann', e.ttc_pd.printed, e.ttc_pd.recomputed, atPrintedDigits(e.ttc_pd.printed, e.ttc_pd.recomputed, e.ttc_pd.decimals));
  for (const q of e.portfolios) {
    if (q.pd0.check === 'entry rounding') out.push({ paper: 'engelmann', printed: q.pd0.printed, recomputed: q.pd0.recomputed, check: 'rounding' });
    else at('engelmann', q.pd0.printed, q.pd0.recomputed, atPrintedDigits(q.pd0.printed, q.pd0.recomputed, q.pd0.decimals));
    if (q.extreme) at('engelmann', q.extreme.printed, q.extreme.recomputed, atPrintedDigits(q.extreme.printed, q.extreme.recomputed, q.extreme.decimals));
  }
  return out;
}

/** The papers' cited blocks: every printed value's recomputation over the print, minus one, numbered by paper, the
 * values that do not agree at the printed digits marked. A printed zero has no ratio and is left as a gap. */
export function papersChart(p: PublishedVariant, points: EvidencePoint[]): DesignChart | null {
  const checks = printChecks(p);
  if (!checks.length) return null;
  const tag = tagOf(points);
  const xs = numbered(checks.length);
  const rel = checks.map((c) => (c.printed !== 0 && finite(c.recomputed) ? c.recomputed / c.printed - 1 : null));
  const by = (pred: (c: PrintCheck) => boolean) => pad(checks.map((c, i) => (pred(c) ? rel[i] : null)));
  const span = (id: PaperId, l: Lang) => {
    const at = checks.flatMap((c, i) => (c.paper === id ? [i + 1] : []));
    return at.length ? ` (${at[0]} ${l === 'es' ? 'a' : 'to'} ${at[at.length - 1]})` : '';
  };
  const drawn = nonEmpty([
    ...PAPERS.map((id): ChartSeries => ({ label: { en: `${tag(id)}${PAPER_NAME[id].en}${span(id, 'en')}`, es: `${tag(id)}${PAPER_NAME[id].es}${span(id, 'es')}` }, values: by((c) => c.paper === id), color: PAPER_COLOR[id], mode: 'points' })),
    { label: { en: 'Does not agree at the printed digits', es: 'No concuerda a los dígitos impresos' }, values: by((c) => c.check === 'differs'), color: '--color-bad', mode: 'points' },
    { label: { en: 'Judged within the rounding of its printed entries', es: 'Juzgado dentro del redondeo de sus entradas impresas' }, values: by((c) => c.check === 'rounding'), color: '--color-warn', mode: 'points' },
  ]);
  if (!drawn.length) return null;
  const zeros = checks.filter((c) => c.printed === 0);
  const exact = zeros.every((c) => c.recomputed === 0);
  const agree = checks.filter((c) => c.check === 'agrees').length;
  const differ = checks.filter((c) => c.check === 'differs').length;
  return {
    title: { en: "The papers' printed values against their recomputation", es: 'Los valores impresos de los artículos contra su recálculo' },
    x: { values: xs, label: { en: 'Printed value, numbered by paper', es: 'Valor impreso, numerado por artículo' }, format: { decimals: 0 } },
    y: { label: { en: 'Recomputed over printed, minus one', es: 'Recalculado sobre impreso, menos uno' }, unit: { en: '%', es: '%' }, format: { percent: true, decimals: 2 } },
    series: [...drawn, { label: { en: 'Recomputed equals printed', es: 'Recalculado igual a impreso' }, values: xs.map(() => 0), color: '--color-fg-subtle', width: 1, dash: [2, 4] }],
    note: {
      en: `Every printed value of the three papers (each paper's own inputs recomputed by riskvalidation), as the recomputation over the print, minus one, in percent: 0 is exact. ${agree} of ${checks.length} agree at the printed digits; red, the ${differ} that do not; amber, Engelmann's W hat, judged within the rounding of its printed entries.${zeros.length ? ` ${zeros.length} printed zeros${exact ? ' are recomputed as exactly 0 and' : ''} have no ratio to draw.` : ''}`,
      es: `Cada valor impreso de los tres artículos (los insumos de cada artículo recalculados por riskvalidation), como el recálculo sobre lo impreso, menos uno, en porcentaje: 0 es exacto. ${agree} de ${checks.length} concuerdan a los dígitos impresos; en rojo, los ${differ} que no; en ámbar, el W hat de Engelmann, juzgado dentro del redondeo de sus entradas impresas.${zeros.length ? ` ${zeros.length} ceros impresos${exact ? ' se recalculan como exactamente 0 y' : ''} no tienen razón que dibujar.` : ''}`,
    },
  };
}

/** The drawing of a variant's design evidence, by the blocks its findings cite (see designDrawn). */
export function designChart(v: VariantArtifact<unknown>, points: EvidencePoint[], grade: number): DesignChart | null {
  if (isPublished(v)) return papersChart(v, points);
  if (!isFamily(v)) return null;
  if (v.outputs.family === 'withdrawals') return withdrawalsChart(v, points, grade);
  if (v.outputs.family === 'thin') return thinChart(v, points, grade);
  return null;
}

/** The outputs block a "design:" evidence names, and the group that draws it. */
const DESIGN_NAME: Record<string, BiText> = {
  definition_gap: { en: 'the definition gaps, pooled D4/D2 and D3/D2 by grade (Validation group)', es: 'las brechas de definición, D4/D2 y D3/D2 agrupadas por grado (grupo Validación)' },
  'cohorts.defaulted_cohort': { en: "the default-rate page's own cohort against the transition page's, year by year (Validation group)", es: 'la cohorte propia de la página de tasas de incumplimiento contra la de la página de transiciones, año a año (grupo Validación)' },
  'cohorts.counts': { en: "the transition page's counts by year, its default column (Validation group)", es: 'los conteos de la página de transiciones por año, su columna de incumplimiento (grupo Validación)' },
  embedding: { en: "the embedding diagnostics: Israel et al.'s Theorem 3 and stochastic monotonicity (Model group)", es: 'los diagnósticos de inclusión: el Teorema 3 de Israel et al. y la monotonía estocástica (grupo Modelo)' },
  generators: { en: "the generators' L1 distances to the pooled matrix (Model group)", es: 'las distancias L1 de los generadores a la matriz agrupada (grupo Modelo)' },
  lra: { en: 'the long-run averages and their Jeffreys intervals (Validation group)', es: 'los promedios de largo plazo y sus intervalos de Jeffreys (grupo Validación)' },
  pd: { en: 'the one-year PDs by cohort and grade (Validation group)', es: 'las PD anuales por cohorte y grado (grupo Validación)' },
  lifetime: { en: 'the five-year windows: observed against the chained one-year matrices (Validation group)', es: 'las ventanas de cinco años: lo observado contra las matrices anuales encadenadas (grupo Validación)' },
  ttc: { en: "the pooled matrix's TTC portfolio and the drift towards it (Impact group)", es: 'la cartera TTC de la matriz agrupada y la deriva hacia ella (grupo Impacto)' },
  'rungs.estimators': { en: "the estimators' bias and RMSE by grade (Validation group)", es: 'el sesgo y el RMSE de los estimadores por grado (grupo Validación)' },
  'rungs.estimators.zero': { en: 'the share of exactly zero PDs by estimator and grade (Validation group)', es: 'la proporción de PD exactamente cero por estimador y grado (grupo Validación)' },
  'rungs.coverage': { en: "the intervals' coverage by grade (Validation group)", es: 'la cobertura de los intervalos por grado (grupo Validación)' },
  'rungs.error_cohort_power': { en: "the Markov projections' errors against the five-year default frequency (Validation group)", es: 'los errores de las proyecciones de Markov contra la frecuencia de incumplimiento a cinco años (grupo Validación)' },
  'rungs.pd_stressed_year': { en: "the stressed year's PD against the truth (Validation group)", es: 'la PD del año estresado contra la verdad (grupo Validación)' },
  'rungs.pd_removed': { en: 'the PD with withdrawals removed against the truth (Validation group)', es: 'la PD con los retiros eliminados contra la verdad (grupo Validación)' },
  'rungs.pd_followed': { en: 'the PD with withdrawals followed (EBA paragraph 76) against the truth (Validation group)', es: 'la PD con los retiros seguidos (párrafo 76 de la EBA) contra la verdad (grupo Validación)' },
  'rungs.overlap_jeffreys': { en: "adjacent grades' Jeffreys overlap by cohort size (Validation group)", es: 'el traslape de Jeffreys de grados adyacentes por tamaño de cohorte (grupo Validación)' },
  irw: { en: "Israel et al.'s nine distances, printed against recomputed (Validation group)", es: 'las nueve distancias de Israel et al., impresas contra recalculadas (grupo Validación)' },
  sr190: { en: "Schuermann and Hanson's Table 5, printed against recomputed (Validation group)", es: 'la Tabla 5 de Schuermann y Hanson, impresa contra recalculada (grupo Validación)' },
  engelmann: { en: "Engelmann's TTC portfolio and projections, printed against recomputed (Validation group)", es: 'la cartera TTC y las proyecciones de Engelmann, impresas contra recalculadas (grupo Validación)' },
};
const designName = (key: string): BiText => DESIGN_NAME[key] ?? { en: `the outputs block ${key}`, es: `el bloque de salidas ${key}` };

function segmentText(segment: string | null, lang: Lang): string {
  if (segment === null || segment === 'portfolio') return '';
  if (segment === 'annual') return lang === 'es' ? ', entre las cohortes anuales' : ', across the annual cohorts';
  if (segment === 'semesters') return lang === 'es' ? ', entre los semestres' : ', across the semesters';
  return lang === 'es' ? `, cohorte ${segment}` : `, cohort ${segment}`;
}

/** The symbol of each family's ladder, as its name defines it (the thin family's ladder is a count, named in full). */
const RUNG_SYMBOL: Partial<Record<string, Bi>> = {
  momentum: { en: 'alpha', es: 'alfa' },
  cycle: { en: 'k', es: 'k' },
  withdrawals: { en: 'k', es: 'k' },
};

/** Where a measured rate sits on its family's ladder, in words. */
export function rungText(f: FamilyVariant, s: C04Simulation, lang: Lang): string {
  const tail = s.key.split('@')[1] ?? '';
  if (tail === 'form-chi2') return lang === 'es' ? 'forma chi-cuadrado, cadena de Markov' : 'chi-square form, Markov chain';
  if (tail === 'form-lr') return lang === 'es' ? 'forma de razón de verosimilitud, cadena de Markov' : 'likelihood ratio form, Markov chain';
  const ladder = f.outputs.ladder;
  if (s.rung === null || !ladder) return lang === 'es' ? 'cadena de Markov, su tamaño' : 'Markov chain, its size';
  const empirical = f.outputs.family === 'momentum' && Math.abs(s.rung - EMPIRICAL_ALPHA) < 1e-12;
  // the ladder's symbol and value ("k = 9"); a ladder without one, "<its name>: <value>": a long name never reads as if
  // the value were part of it (the names, with what each symbol means, are in the family's design)
  const symbol = RUNG_SYMBOL[f.outputs.family];
  const head = symbol ? `${pick(symbol, lang)} = ` : `${pick(ladder.name, lang)}: `;
  return `${head}${formatNumber(s.rung, lang, { digits: 4 })}${empirical ? (lang === 'es' ? ' (la fuerza empírica)' : ' (the empirical strength)') : ''}`;
}

function evidenceText(c: Cited, ref: string, k: number | undefined, lang: Lang): string {
  const n = k ? `[${k}] ` : '';
  if (c.kind === 'design') return `${n}${lang === 'es' ? 'Calculado en el horneado desde ' : 'Computed in the bake from '}${pick(designName(c.key), lang)}`;
  if (c.kind === 'missing') return `${ref} (${lang === 'es' ? 'no está en el artefacto' : 'not in the artifact'})`;
  if (c.kind === 'test') {
    const t = c.row;
    const value = t.p_value !== null ? pText(lang, t.p_value) : `${formatNumber(t.metric ?? t.statistic, lang, { digits: 4 })}`;
    return `${n}${pick(testName(t.test_id), lang)}${segmentText(t.segment, lang)}: ${value}, ${pick(LIGHT_TEXT[t.light], lang)}`;
  }
  const s = c.sim;
  const r5 = s.rates[AT5];
  const r1 = s.rates[AT1];
  const head = `${n}${pick(testName(s.test_id), lang)}, ${rungText(c.family, s, lang)}`;
  if (!r5) return head;
  return lang === 'es'
    ? `${head}: ${pctText('es', r5.rate)} al 5% (EE ${pctText('es', r5.se)}), Wilson 95% ${pctText('es', r5.wilson_low)} a ${pctText('es', r5.wilson_high)}; ${pctText('es', r1?.rate)} al 1%; ${formatNumber(s.n_rep, 'es')} repeticiones`
    : `${head}: ${pctText('en', r5.rate)} at 5% (SE ${pctText('en', r5.se)}), Wilson 95% ${pctText('en', r5.wilson_low)} to ${pctText('en', r5.wilson_high)}; ${pctText('en', r1?.rate)} at 1%; ${formatNumber(s.n_rep, 'en')} repetitions`;
}

/** What the variant's numbers rest on, for the findings' notes. */
function sourceOf(v: VariantArtifact<unknown>): Bi {
  if (isAgency(v)) return cerepLine(v);
  if (isFamily(v)) {
    return {
      en: `Known truth: rating paths drawn from ${GENERATOR_TEXT.en}. ${ATTRIBUTION_FALLBACK}.`,
      es: `Verdad conocida: trayectorias de calificación generadas desde ${GENERATOR_TEXT.es}. ${ATTRIBUTION_FALLBACK}.`,
    };
  }
  return { en: "The papers' printed values against their recomputation.", es: 'Los valores impresos de los artículos contra su recálculo.' };
}

/** What the Findings view draws beside (or under) its table: the card's title, the chart and its note. */
export interface FindingsDrawing {
  title: BiText;
  chart: C04Chart;
  note: Bi;
}

export function findingsDrawing(v: VariantArtifact<unknown>, ev: ReturnType<typeof findingsEvidence>, grade: number): FindingsDrawing | null {
  const src = sourceOf(v);
  if (ev.kind === 'p') {
    const pc = pValueChart(ev.points);
    if (!pc) return null;
    const below = both((l) =>
      pc.below
        ? l === 'es'
          ? ` ${pc.below === 1 ? 'Un valor p queda' : `${pc.below} valores p quedan`} por debajo de ${formatNumber(pc.floor, 'es', { digits: 2 })} (${pc.zeros === 1 && pc.below === 1 ? 'es 0' : `${pc.zeros} de ellos son 0`} en doble precisión, por debajo de aproximadamente 1e-300): el eje termina en ${formatNumber(pc.floor, 'es', { digits: 2 })}, donde se dibujan; la tabla da cada uno.`
          : ` ${pc.below === 1 ? 'One p-value lies' : `${pc.below} p-values lie`} below ${formatNumber(pc.floor, 'en', { digits: 2 })} (${pc.zeros === 1 && pc.below === 1 ? 'it is 0' : `${pc.zeros} of them 0`} in double precision, under about 1e-300): the axis stops at ${formatNumber(pc.floor, 'en', { digits: 2 })}, where they are drawn; the table gives each one.`
        : '',
    );
    return {
      title: { en: 'The cited tests against the policy', es: 'Las pruebas citadas contra la política' },
      chart: pc,
      note: {
        en: `The p-value of each cited test, numbered as in the table, on a log scale against the committed policy's thresholds (${pc.policy}: amber below ${formatNumber(pc.amber, 'en', { digits: 2 })}, red below ${formatNumber(pc.red, 'en', { digits: 2 })}; a policy, not a regulation). Red points are the cohorts and periods the test rejects.${pc.marks.length ? ' Marked: the years the finding names, where the year\'s migrations depart most from the pooled matrix (the likelihood ratio per degree of freedom).' : ''}${below.en} ${src.en}`,
        es: `El valor p de cada prueba citada, numerada como en la tabla, en escala logarítmica contra los umbrales de la política comprometida (${pc.policy}: ámbar bajo ${formatNumber(pc.amber, 'es', { digits: 2 })}, rojo bajo ${formatNumber(pc.red, 'es', { digits: 2 })}; una política, no una regulación). Los puntos rojos son las cohortes y períodos que la prueba rechaza.${pc.marks.length ? ' Marcados: los años que nombra el hallazgo, donde las migraciones del año se apartan más de la matriz agrupada (la razón de verosimilitud por grado de libertad).' : ''}${below.es} ${src.es}`,
      },
    };
  }
  if (ev.kind === 'rate') {
    const rc = rateChart(ev.points);
    if (!rc) return null;
    return {
      title: { en: 'The cited rates against the nominal levels', es: 'Las tasas citadas contra los niveles nominales' },
      chart: rc,
      note: {
        en: `Each cited rate, numbered as in the table: the share of repetitions in which the test rejects at 5% with its 95% Wilson interval, and at 1%, against the nominal levels (dashed 5%, dotted 1%). Under a true null the rate is the test's size; under the family's defect, its power.${rc.marks?.length ? ' Marked: the rates at the empirical momentum strength (alpha 0.125).' : ''} ${src.en}`,
        es: `Cada tasa citada, numerada como en la tabla: la fracción de repeticiones en que la prueba rechaza al 5% con su intervalo de Wilson al 95%, y al 1%, contra los niveles nominales (segmentada 5%, punteada 1%). Con una nula verdadera la tasa es el tamaño de la prueba; con el defecto de la familia, su potencia.${rc.marks?.length ? ' Marcadas: las tasas con la fuerza empírica del momentum (alfa 0,125).' : ''} ${src.es}`,
      },
    };
  }
  if (ev.kind === 'design') {
    const dc = designChart(v, ev.points, grade);
    if (!dc) return null;
    const { title, note, ...chart } = dc;
    return { title, chart, note: { en: `${note.en} ${src.en}`, es: `${note.es} ${src.es}` } };
  }
  return null;
}

export function C04FindingsView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = sel?.data.variant as VariantArtifact<unknown> | undefined;
  const ev = useMemo(() => (v ? findingsEvidence(v) : null), [v]);
  const grade = sel?.grade ?? 0;
  const drawing = useMemo(() => (v && ev ? findingsDrawing(v, ev, grade) : null), [v, ev, grade]);
  if (!sel || !v || !ev) return <Pending />;
  const prov = provenanceOf(v.provenance.truth_status);
  const number = new Map(ev.points.map((p, i) => [p.key, i + 1]));
  const open = ev.findings.filter((f) => f.status === 'open');
  const worst = open[0]?.severity ?? null;
  const tone: Tone = worst === 'S1' || worst === 'S2' ? 'bad' : worst === 'S3' ? 'warn' : 'good';
  const src = sourceOf(v);
  // a short table at its own height over the drawing; a long one scrolls in a card beside it; no drawing, the table alone
  const compact = Boolean(drawing) && isCompact(ev.findings);
  const fill = !compact;
  const where: Bi = !drawing
    ? {
        en: "This variant's findings cite only such blocks, drawn in the Model and Validation groups: there is no p-value or rate to draw here. ",
        es: 'Los hallazgos de esta variante citan solo esos bloques, dibujados en los grupos Modelo y Validación: aquí no hay valor p ni tasa que dibujar. ',
      }
    : compact
      ? { en: 'The numbered evidence is drawn below. ', es: 'La evidencia numerada se dibuja abajo. ' }
      : { en: 'The numbered evidence is drawn beside. ', es: 'La evidencia numerada se dibuja al lado. ' };
  const rows = (
    <table className="caos-table" data-table="findings">
      <thead>
        <tr>
          <th>{pick({ en: 'Severity', es: 'Severidad' }, lang)}</th>
          <th className="ct-text">{pick({ en: 'Finding and its evidence', es: 'Hallazgo y su evidencia' }, lang)}</th>
          <th className="ct-wide-only">{pick({ en: 'Status', es: 'Estado' }, lang)}</th>
        </tr>
      </thead>
      <tbody>
        {ev.findings.map((f) => (
          <tr key={f.id} data-finding={f.id} data-severity={f.severity}>
            <td>{pick(SEVERITY_TEXT[f.severity] ?? { en: f.severity, es: f.severity }, lang)}</td>
            <td className="ct-text">
              {pick(f.title, lang)}
              <ul className="ct-evidence">
                {f.evidence.map((ref) => {
                  const c = citedOf(v, ref);
                  return (
                    <li key={ref} data-evidence={c.kind}>
                      {evidenceText(c, ref, number.get(`${f.id}|${ref}`), lang)}
                    </li>
                  );
                })}
              </ul>
            </td>
            <td className="ct-wide-only">{pick(STATUS_TEXT[f.status] ?? { en: f.status, es: f.status }, lang)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
  const table = (
    <PlotCard
      fill={fill}
      title={{ en: 'What the validation found', es: 'Lo que encontró la validación' }}
      lane={REPLAY}
      provenance={prov}
      dataKey={stateKey}
      note={{
        en: `Each finding cites the test rows behind it (their p-value and light under the committed policy), the measured rates (with their Monte Carlo SE and Wilson interval) or the block of the outputs the bake computed it from. ${where.en}${src.en}`,
        es: `Cada hallazgo cita las filas de prueba que lo respaldan (su valor p y su luz con la política comprometida), las tasas medidas (con su EE de Monte Carlo e intervalo de Wilson) o el bloque de salidas desde el que el horneado lo calculó. ${where.es}${src.es}`,
      }}
    >
      <div className={fill ? 'ct-stack' : 'ct-stack-natural'}>
        <Verdict
          compact
          title={{ en: 'Most severe open finding', es: 'Hallazgo abierto más severo' }}
          tone={tone}
          verdict={
            worst
              ? {
                  en: `${pick(SEVERITY_TEXT[worst] ?? worst, 'en')}; ${open.length} open of ${ev.findings.length}`,
                  es: `${pick(SEVERITY_TEXT[worst] ?? worst, 'es')}; ${open.length} abiertos de ${ev.findings.length}`,
                }
              : { en: `No open finding (${ev.findings.length} in all)`, es: `Ningún hallazgo abierto (${ev.findings.length} en total)` }
          }
        />
        {fill ? <div className="ct-scroll">{rows}</div> : rows}
      </div>
    </PlotCard>
  );
  if (!drawing) {
    return (
      <div className="caos-views-row" data-views="1">
        <div className="ct-col">{table}</div>
      </div>
    );
  }
  const chartCard = (
    <PlotCard fill title={drawing.title} lane={REPLAY} provenance={prov} dataKey={stateKey} note={drawing.note}>
      <UPlotChart height="fill" x={drawing.chart.x} y={drawing.chart.y} series={drawing.chart.series} marks={drawing.chart.marks} />
    </PlotCard>
  );
  if (compact) {
    return (
      <div className="caos-views-row" data-views="1" data-layout="stacked">
        <div className="ct-col">
          {table}
          {chartCard}
        </div>
      </div>
    );
  }
  return (
    <div className="caos-views-row" data-views="2" data-layout="beside">
      <div className="ct-col ct-findings-table">{table}</div>
      <div className="ct-col ct-findings-chart">{chartCard}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// Variants

const AGENCY_DASH: Array<number[] | undefined> = [undefined, [8, 4], [2, 3]];
const DASH_TEXT: Bi[] = [
  { en: 'solid', es: 'continuo' },
  { en: 'long dashes', es: 'segmentos largos' },
  { en: 'short dashes', es: 'segmentos cortos' },
];

/** The agencies' long-run average PD by grade under D2 and D4 on a log axis (colour: the definition, dash: the
 * agency), each agency's TTC default rate as a level, and the rail's grade marked. A zero average (no default in any
 * year) has no place on a log axis and is left as a gap. The grade axis is padded half a grade at each end. Null when
 * no agency has a positive average to draw. */
export function agencyLraChart(agencies: AgencyVariant[], short: (id: string) => BiText, grade: number | null): C04Chart | null {
  const x = numbered(GRADES.length);
  const lines: ChartSeries[] = [];
  agencies.forEach((a, i) => {
    const s = short(a.variant_id);
    for (const d of ['d2', 'd4'] as const) {
      const lra = a.outputs.lra[d];
      if (!lra) continue;
      lines.push({
        label: { en: `${pick(s, 'en')}, ${pick(DEFINITION_LABEL[d], 'en')}`, es: `${pick(s, 'es')}, ${pick(DEFINITION_LABEL[d], 'es')}` },
        values: pad(lra.rate.map((r) => (finite(r) && r > 0 ? r : null))),
        color: DEFINITION_COLOR[d],
        width: 2,
        dash: AGENCY_DASH[i % AGENCY_DASH.length],
      });
    }
  });
  const drawn = nonEmpty(lines);
  if (!drawn.length) return null;
  const ttc: ChartSeries[] = agencies.flatMap((a, i) => {
    const t = a.impact.ttc_default_rate?.value;
    if (!finite(t) || t <= 0) return [];
    const s = short(a.variant_id);
    return [
      {
        label: { en: `${pick(s, 'en')}, TTC default rate ${pctText('en', t)}`, es: `${pick(s, 'es')}, tasa TTC de incumplimiento ${pctText('es', t)}` },
        values: x.map(() => t),
        color: '--color-fg-subtle',
        width: 1.2,
        dash: AGENCY_DASH[i % AGENCY_DASH.length],
      },
    ];
  });
  return {
    x: { values: x, label: GRADE_AXIS, format: { decimals: 0 } },
    y: { label: { en: 'Long-run average one-year PD (log scale)', es: 'PD anual promedio de largo plazo (escala log.)' }, log: true, format: { percent: true, digits: 2 } },
    series: [...drawn, ...ttc],
    marks: grade === null ? undefined : gradeMark(grade),
  };
}

/** A variants row: a click anywhere on it loads the variant (the name in it is a button, so the keyboard reaches the
 * row too: the button's click reaches the row); the open variant's row is marked. */
export function pickRow(id: string, current: string, onPick: (id: string) => void) {
  return { 'data-variant': id, className: id === current ? 'ct-current' : undefined, onClick: () => onPick(id) };
}

const NONE: BiText = { en: 'none', es: 'no hay' };

/** The agencies table's note: what each column holds at the rail's grade, the definition gaps the table leaves out
 * (pooled D3/D2), the agencies without a default category and the years whose default column is empty, the entities
 * and ESMA's attribution. */
export function agenciesNote(agencies: AgencyVariant[], short: (id: string) => BiText, g: number): Bi {
  const name = (a: AgencyVariant, l: Lang) => pick(short(a.variant_id), l);
  const ratio = (x: number | null | undefined, l: Lang) => (finite(x) ? formatNumber(x, l, { digits: 3 }) : l === 'es' ? 'no definida' : 'undefined');
  const d3 = (l: Lang) => agencies.map((a) => `${name(a, l)} ${ratio(a.outputs.definition_gap.d3_over_d2?.[g], l)}`).join(l === 'es' ? '; ' : ', ');
  const noCategory = agencies.filter((a) => d4EmptyYears(a) === null);
  const empty = agencies.flatMap((a) => {
    const e = d4EmptyYears(a);
    return e && e.years.length ? [{ a, e }] : [];
  });
  const entities = agencies.map((a) => a.outputs.agency.name).join('; ');
  const attribution = agencies[0]?.outputs.attribution || ATTRIBUTION_FALLBACK;
  const grade = GRADES[g];
  return {
    en: `${grade}: the long-run average PD under D2 (the default-rate page) and D4 (the transition page's default column), their pooled ratio, and the TTC default rate of each agency's pooled matrix (Engelmann 2024). Pooled D3/D2 at ${grade}: ${d3('en')} (a ratio over no D2 default is undefined).${noCategory
      .map((a) => ` ${possessive(name(a, 'en'))} transition page has no default category: no D4 and no TTC rate.`)
      .join('')}${empty
      .map(({ a, e }) => ` ${possessive(name(a, 'en'))} default column is empty in the years ${yearRanges(e.years, 'en')}, while its default page counts ${formatNumber(e.defaulted, 'en')} rated defaulters in those years.`)
      .join('')} ${entities}. ${attribution}. Pick a row to load the agency.`,
    es: `${grade}: la PD promedio de largo plazo con D2 (la página de tasas de incumplimiento) y D4 (la columna de incumplimiento de la página de transiciones), su razón agrupada, y la tasa TTC de incumplimiento de la matriz agrupada de cada agencia (Engelmann 2024). D3/D2 agrupada en ${grade}: ${d3('es')} (una razón sobre ningún incumplimiento D2 no está definida).${noCategory
      .map((a) => ` La página de transiciones de ${name(a, 'es')} no tiene categoría de incumplimiento: no hay D4 ni tasa TTC.`)
      .join('')}${empty
      .map(({ a, e }) => ` La columna de incumplimiento de ${name(a, 'es')} está vacía en los años ${yearRanges(e.years, 'es')}, mientras su página de incumplimientos cuenta ${formatNumber(e.defaulted, 'es')} calificaciones incumplidas en esos años.`)
      .join('')} ${entities}. ${attribution}. Elija una fila para cargar la agencia.`,
  };
}

function VariantsBody({ sel, variants, onPick }: { sel: C04Sel; variants: VariantArtifact<unknown>[]; onPick: (id: string) => void }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const m = sel.data.manifest;
  const { agencies, families, published } = kindsOf(variants);
  const current = (sel.data.variant as VariantArtifact<unknown>).variant_id;
  const g = sel.grade;
  const gName = GRADES[g];
  const short = (id: string) => shortOf(m, id);
  const chart = agencyLraChart(agencies, short, g);
  const row = (id: string) => pickRow(id, current, onPick);
  const pickButton = (label: BiText, title: string) => (
    <button type="button" className="ct-linkbutton" title={title}>
      {pick(label, lang)}
    </button>
  );
  const ratio = (x: number | null | undefined) => (finite(x) ? formatNumber(x, lang, { digits: 3 }) : pick(NONE, lang));
  const attribution = agencies[0]?.outputs.attribution || ATTRIBUTION_FALLBACK;
  const entities = agencies.map((a) => a.outputs.agency.name).join('; ');
  const agencyProv: Provenance = provenanceOf(agencies[0]?.provenance.truth_status ?? 'real-outcomes');
  const familyProv: Provenance = provenanceOf(families[0]?.provenance.truth_status ?? 'synthetic-known-truth');
  const dashes = (l: Lang) => agencies.map((a, i) => `${pick(short(a.variant_id), l)} ${DASH_TEXT[i % DASH_TEXT.length][l]}`).join(', ');
  const agenciesCard = (
    <PlotCard
      title={{ en: `The agencies, ${gName}`, es: `Las agencias, ${gName}` }}
      lane={REPLAY}
      provenance={agencyProv}
      dataKey={stateKey}
      note={agenciesNote(agencies, short, g)}
    >
      <table className="caos-table ct-wrap-head" data-table="variants-agencies">
        <thead>
          <tr>
            <th className="ct-text">{pick({ en: 'Agency', es: 'Agencia' }, lang)}</th>
            <th>{`${gName}, D2`}</th>
            <th>{`${gName}, D4`}</th>
            <th>D4/D2</th>
            <th>{pick({ en: 'TTC rate', es: 'Tasa TTC' }, lang)}</th>
          </tr>
        </thead>
        <tbody>
          {agencies.map((a) => {
            const o = a.outputs;
            const ttc = a.impact.ttc_default_rate?.value ?? null;
            return (
              <tr key={a.variant_id} {...row(a.variant_id)}>
                <td className="ct-text">{pickButton(short(a.variant_id), o.agency.name)}</td>
                <td data-cell="d2">{pctText(lang, o.lra.d2.rate[g])}</td>
                <td data-cell="d4">{o.lra.d4 ? pctText(lang, o.lra.d4.rate[g]) : pick(NONE, lang)}</td>
                <td data-cell="d4-over-d2">{o.definition_gap.d4_over_d2 ? ratio(o.definition_gap.d4_over_d2[g]) : pick(NONE, lang)}</td>
                <td data-cell="ttc">{finite(ttc) ? pctText(lang, ttc) : pick(NONE, lang)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </PlotCard>
  );
  const publishedCard = published ? (
    <PlotCard
      title={{ en: 'The published answers', es: 'Las respuestas publicadas' }}
      lane={REPLAY}
      provenance={provenanceOf(published.provenance.truth_status)}
      dataKey={stateKey}
      note={{ en: "Each paper's printed values against their recomputation from its own inputs. Pick a row to load the papers.", es: 'Los valores impresos de cada artículo contra su recálculo desde sus propios insumos. Elija una fila para cargar los artículos.' }}
    >
      <table className="caos-table ct-wrap-head" data-table="variants-published">
        <thead>
          <tr>
            <th className="ct-text">{pick({ en: 'Paper', es: 'Artículo' }, lang)}</th>
            <th>{pick({ en: 'At the printed digits', es: 'A los dígitos impresos' }, lang)}</th>
          </tr>
        </thead>
        <tbody>
          {paperAgreements(published).map((p) => (
            <tr key={p.id} {...row(published.variant_id)} data-paper={p.id}>
              <td className="ct-text">{pickButton(p.name, pick(p.detail, lang))}</td>
              <td data-cell="agree">{lang === 'es' ? `${p.agree} de ${p.total}` : `${p.agree} of ${p.total}`}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </PlotCard>
  ) : null;
  const familiesCard = (
    <PlotCard
      fill
      title={{ en: 'The generator families', es: 'Las familias generadoras' }}
      lane={REPLAY}
      provenance={familyProv}
      dataKey={stateKey}
      note={{
        en: `Each family's headline measurements as its artifact states them, against a known truth: rating paths drawn from ${GENERATOR_TEXT.en} (${attribution}). The design is on each name. Pick a row to load the family.`,
        es: `Las mediciones principales de cada familia como las declara su artefacto, contra una verdad conocida: trayectorias de calificación generadas desde ${GENERATOR_TEXT.es} (${attribution}). El diseño está en cada nombre. Elija una fila para cargar la familia.`,
      }}
    >
      <div className="ct-scroll">
        <table className="caos-table ct-wrap-head" data-table="variants-families">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Family', es: 'Familia' }, lang)}</th>
              <th className="ct-text">{pick({ en: 'Measured', es: 'Medido' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {families.map((f) => (
              <tr key={f.variant_id} {...row(f.variant_id)}>
                <td className="ct-text">{pickButton(short(f.variant_id), `${pick(titleOf(m, f.variant_id), lang)}: ${familyDesign(f, lang)}`)}</td>
                <td className="ct-text" data-cell="measured">
                  {Object.values(f.impact)
                    .map((it) => `${pick(it.label, lang)}: ${impactValue(it, lang)}`)
                    .join('; ')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </PlotCard>
  );
  const chartCard = chart ? (
    <PlotCard
      fill
      title={{ en: 'Long-run average PD by grade, D2 and D4', es: 'PD promedio de largo plazo por grado, D2 y D4' }}
      lane={REPLAY}
      provenance={agencyProv}
      dataKey={stateKey}
      note={{
        en: `The mean of the yearly one-year PDs over the cohorts where the grade has ratings (EBA/GL/2017/16 paragraph 84), percent a year on a log scale; colour the definition, dash the agency (${dashes('en')}); a zero average has no point. Grey: each agency's TTC default rate. Marked: the rail's grade. ${pick(ESMA_DEFINITIONS, 'en')} ${entities}. ${attribution}.`,
        es: `La media de las PD anuales sobre las cohortes donde el grado tiene calificaciones (párrafo 84 de EBA/GL/2017/16), porcentaje al año en escala logarítmica; color la definición, trazo la agencia (${dashes('es')}); un promedio cero no tiene punto. Gris: la tasa TTC de incumplimiento de cada agencia. Marcado: el grado del panel. ${pick(ESMA_DEFINITIONS, 'es')} ${entities}. ${attribution}.`,
      }}
    >
      <UPlotChart height="fill" x={chart.x} y={chart.y} series={chart.series} marks={chart.marks} />
    </PlotCard>
  ) : null;
  // the two short tables side by side at their own height; under them, the chart and the families' table fill the rest
  return (
    <>
      <div className="ct-row" data-row="variants-tables">
        <div className="ct-share-3">{agenciesCard}</div>
        {publishedCard && <div className="ct-share-2">{publishedCard}</div>}
      </div>
      <div className="caos-views-row" data-views={chartCard ? '2' : '1'}>
        {chartCard && <div className="ct-col ct-share-3">{chartCard}</div>}
        <div className="ct-col ct-share-2">{familiesCard}</div>
      </div>
    </>
  );
}

export function C04VariantsView({ sel, onPick }: { sel: C04Sel | null; onPick: (id: string) => void }) {
  const all = useC04Variants(sel?.data.manifest);
  if (!sel) return <Pending />;
  if (all.state === 'loading') return <Pending label={{ en: 'Loading the variants', es: 'Cargando las variantes' }} />;
  if (all.state === 'error') return <LoadError error={all.error} />;
  return <VariantsBody sel={sel} variants={all.data} onPick={onPick} />;
}

// ---------------------------------------------------------------------------------------------------------------------
// Context

const CLASS_TEXT: Record<string, BiText> = {
  'mirror-allowed': { en: 'mirror-allowed: the tables may be redistributed with the attribution', es: 'espejo permitido: las tablas pueden redistribuirse con la atribución' },
  'derived-only': { en: 'derived-only: the PDF stays in the data root; only results are published', es: 'solo derivados: el PDF queda en la raíz de datos; solo se publican resultados' },
};

const TRUTH_MEANS: Record<string, BiText> = {
  'real-outcomes': { en: "the agency's own statistics as ESMA publishes them: no truth to compare with", es: 'las estadísticas de la propia agencia como las publica ESMA: sin verdad con que comparar' },
  'synthetic-known-truth': { en: 'paths drawn from a known chain: every error is measured against the truth', es: 'trayectorias generadas desde una cadena conocida: cada error se mide contra la verdad' },
  'published-answer': { en: "the papers' printed numbers, each recomputed from the paper's own inputs", es: 'los números impresos de los artículos, cada uno recalculado desde los insumos del propio artículo' },
};

export function C04ContextView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  if (!sel) return <Pending />;
  const m = sel.data.manifest;
  const v = sel.data.variant as VariantArtifact<unknown>;
  const prov = provenanceOf(v.provenance.truth_status);
  const fit = (sel.data.models as unknown as ModelsArtifact<C04Fit>).fit;
  const gen = fit?.generator;
  const entries = m.artifacts.filter((a) => a.role === 'variant');
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard title={{ en: 'The case', es: 'El caso' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        <p className="ct-note" data-statement="esma">
          {pick(ESMA_DEFINITIONS, lang)}
        </p>
        <table className="caos-table" data-table="definitions">
          <thead>
            <tr>
              <th className="caos-col-text">{pick({ en: 'Definition', es: 'Definición' }, lang)}</th>
              <th className="caos-col-text">{pick({ en: 'What it counts', es: 'Lo que cuenta' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {DEFINITIONS.map((d) => (
              <tr key={d} data-definition={d}>
                <td className="caos-col-text">{pick(DEFINITION_LABEL[d], lang)}</td>
                <td className="caos-col-text">{pick(DEFINITION_HINT[d], lang)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <table className="caos-table" data-sources={m.sources.join(' ')}>
          <thead>
            <tr>
              <th className="caos-col-text">{pick({ en: 'Source', es: 'Fuente' }, lang)}</th>
              <th className="caos-col-text">{pick({ en: 'Licence and class', es: 'Licencia y clase' }, lang)}</th>
              <th className="caos-col-text">{pick({ en: 'Attribution', es: 'Atribución' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {m.sources.map((id) => {
              const s = m.source_details[id];
              if (!s) return null;
              return (
                <tr key={id} data-licence-class={s.class} data-source={id}>
                  <td className="caos-col-text">
                    <a href={s.landing} target="_blank" rel="noreferrer">
                      {s.name}
                    </a>
                    {` (${s.publisher})`}
                  </td>
                  <td className="caos-col-text">
                    {s.licence} <em>({pick(CLASS_TEXT[s.class] ?? { en: s.class, es: s.class }, lang)})</em>
                  </td>
                  <td className="caos-col-text">{s.attribution}</td>
                </tr>
              );
            })}
            <tr data-licence-class="generator">
              <td className="caos-col-text">{pick({ en: "riskvalidation's RatingPaths generator (Contraste's own)", es: 'Generador RatingPaths de riskvalidation (de Contraste)' }, lang)}</td>
              <td className="caos-col-text">{pick({ en: 'MIT; its generator is derived from mirror-allowed CEREP counts', es: 'MIT; su generador se deriva de conteos de CEREP con espejo permitido' }, lang)}</td>
              <td className="caos-col-text">
                {gen
                  ? lang === 'es'
                    ? `Trayectorias generadas desde ${GENERATOR_TEXT.es}; cohortes de ${gen.obligors.map((n) => formatNumber(n, 'es')).join('; ')} deudores por grado. ${ATTRIBUTION_FALLBACK}.`
                    : `Paths drawn from ${GENERATOR_TEXT.en}; cohorts of ${gen.obligors.map((n) => formatNumber(n, 'en')).join(', ')} obligors by grade. ${ATTRIBUTION_FALLBACK}.`
                  : ATTRIBUTION_FALLBACK}
              </td>
            </tr>
          </tbody>
        </table>
        <table className="caos-table" data-table="truth">
          <thead>
            <tr>
              <th className="caos-col-text">{pick({ en: 'Variant', es: 'Variante' }, lang)}</th>
              <th className="caos-col-text">{pick({ en: 'Truth status', es: 'Estado de verdad' }, lang)}</th>
              <th className="caos-col-text">{pick({ en: 'What it rests on', es: 'En qué se apoya' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr key={e.variant_id} data-variant={e.variant_id} data-truth={e.truth_status} className={e.variant_id === v.variant_id ? 'ct-current' : undefined}>
                <td className="caos-col-text">
                  <strong>{pick(e.short_title, lang)}</strong>: {pick(e.title, lang)}
                </td>
                <td className="caos-col-text">{pick(TRUTH_TEXT[e.truth_status] ?? { en: e.truth_status, es: e.truth_status }, lang)}</td>
                <td className="caos-col-text">{pick(TRUTH_MEANS[e.truth_status] ?? { en: e.truth_status, es: e.truth_status }, lang)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="ct-note">
          {pick(
            {
              en: `Truth status of this variant: ${v.provenance.truth_status}. The CEREP reader checks each page against the others (the grades' rows against the cohort, the three pages' cohorts year by year) and the paper readers check what they read against the print, refusing the bake otherwise. Pipeline ${m.engine.pipeline}, riskvalidation ${m.engine.riskvalidation ?? ''}.`,
              es: `Estado de verdad de esta variante: ${v.provenance.truth_status}. El lector de CEREP verifica cada página contra las demás (las filas de los grados contra la cohorte, las cohortes de las tres páginas año a año) y los lectores de artículos verifican lo leído contra la impresión, y si no, rechazan el horneado. Pipeline ${m.engine.pipeline}, riskvalidation ${m.engine.riskvalidation ?? ''}.`,
            },
            lang,
          )}
        </p>
      </PlotCard>
      <PlotCard title={{ en: 'The case in depth', es: 'El caso en profundidad' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <div className="ct-prose">
          <C04WriteUp />
          <C04Results manifest={m} />
        </div>
      </PlotCard>
    </div>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// The rail's read-outs: each title one line of the rail and each item one line (label and value), at most three items
// where the section's question allows (the rail fits 1280 x 800 without scrolling, ADR-0071 rule 6), the rest of what
// a value means in its hint.

interface Reading {
  title: BiText;
  lane: Lane;
  provenance: Provenance;
  items: ReadoutItem[];
}

const pctFormat = { percent: true, digits: 3 } as const;
const PP: BiText = { en: 'pp', es: 'pp' };
/** A difference of two probabilities in percentage points. */
const pp = (x: number | null | undefined): number | null => (finite(x) ? x * 100 : null);
const ppItem = (label: BiText, value: number | null, hint?: BiText): ReadoutItem => ({ label, value, unit: PP, format: { digits: 3 }, hint });
const ppText = (x: number | null | undefined) => both((l) => `${formatNumber(pp(x), l, { digits: 3 })}\u00a0pp`);

/** The definition as the rail's chip names it. */
const DEFINITION_SHORT: Record<Definition, Bi> = {
  d2: { en: 'D2', es: 'D2' },
  d3: { en: 'D3', es: 'D3' },
  d4: { en: 'D4', es: 'D4' },
  keep: { en: 'Keep', es: 'Con retiros' },
};

/** An agency's grade under the rail's definition: the long-run average with its 95% Jeffreys interval, over the
 * cohorts the title counts. The interval is the artifact's, on the counts pooled over the cohorts, so it belongs to
 * the pooled rate, which its hint gives (the mean of the yearly rates can lie outside it: Fitch's CCC-C). Keep (the
 * transition page's defaults over the whole cohort, withdrawals in the denominator) is computed here from the yearly
 * rates and the pooled counts, so it is live. */
export function agencyReading(sel: C04Sel, v: AgencyVariant): Reading {
  const o = v.outputs;
  const g = sel.grade;
  const def = sel.definition;
  const label = bi(DEFINITION_LABEL[def]);
  let lra: number | null = null;
  let pooled: number | null = null;
  let lo: number | null = null;
  let hi: number | null = null;
  let cohorts: number | null = null;
  let lane: Lane = REPLAY;
  if (def === 'keep') {
    lane = LIVE;
    if (o.pd.keep) {
      const vals = o.pd.keep.map((row) => row[g]).filter(finite);
      lra = vals.length ? sum(vals) / vals.length : null;
      cohorts = vals.length;
    }
    const c = gradeCounts(v, 'keep', g);
    try {
      const j = c ? pdJeffreys(c.defaults, c.n, { level: 0.95 }) : null;
      pooled = j?.estimate ?? null;
      lo = j?.lower ?? null;
      hi = j?.upper ?? null;
    } catch {
      pooled = lo = hi = null;
    }
  } else {
    const block = o.lra[def];
    lra = block?.rate[g] ?? null;
    pooled = block?.pooled_rate[g] ?? null;
    lo = block?.jeffreys.lower[g] ?? null;
    hi = block?.jeffreys.upper[g] ?? null;
    cohorts = block ? block.cohorts[g] : null;
  }
  const d = DEFINITION_SHORT[def];
  const n = cohorts === null ? null : both((l) => `${formatNumber(cohorts, l)} ${l === 'es' ? 'cohortes' : 'cohorts'}`);
  const cerep = cerepLine(v);
  const pooledText = both((l) => formatNumber(pooled, l, pctFormat));
  const interval: BiText | undefined =
    finite(lo) && finite(hi)
      ? { en: `${formatNumber(lo, 'en', pctFormat)} to ${formatNumber(hi, 'en', pctFormat)}`, es: `${formatNumber(lo, 'es', pctFormat)} a ${formatNumber(hi, 'es', pctFormat)}` }
      : undefined;
  return {
    title: { en: `${GRADES[g]}, ${d.en}${n ? `, ${n.en}` : ''}`, es: `${GRADES[g]}, ${d.es}${n ? `, ${n.es}` : ''}` },
    lane,
    provenance: provenanceOf(v.provenance.truth_status),
    items: [
      {
        label: { en: 'Long-run average PD', es: 'PD de largo plazo' },
        value: lra,
        unitless: true,
        format: pctFormat,
        hint: {
          en: `The mean of the yearly one-year PDs over the annual cohorts in which the grade has ratings (EBA/GL/2017/16 paragraph 84), under ${label.en}: ${pick(DEFINITION_HINT[def], 'en')} ${cerep.en}`,
          es: `La media de las PD anuales sobre las cohortes anuales en que el grado tiene calificaciones (párrafo 84 de EBA/GL/2017/16), con ${label.es}: ${pick(DEFINITION_HINT[def], 'es')} ${cerep.es}`,
        },
      },
      {
        label: { en: 'Jeffreys 95%', es: 'Jeffreys 95%' },
        ...(interval ? { text: interval } : { value: null }),
        unitless: true,
        hint: {
          en: `The 95% Jeffreys interval of the pooled rate, ${pooledText.en}: the defaults over the ratings pooled across the cohorts.`,
          es: `El intervalo de Jeffreys al 95% de la tasa agrupada, ${pooledText.es}: los incumplimientos sobre las calificaciones agrupadas de las cohortes.`,
        },
      },
    ],
  };
}

/** A family's grade: the true one-year PD and the bias of the family's estimate, at the rail's estimator (Markov), the
 * empirical momentum rung, or the family's strongest rung (cycle, withdrawals); the thin family's exact coverage at its
 * smallest cohort. Biases are differences of probabilities, in percentage points; their Monte Carlo errors are in the
 * hints. */
export function familyReading(sel: C04Sel, v: FamilyVariant): Reading {
  const o = v.outputs;
  const g = sel.grade;
  const name = GRADES[g];
  const provenance = provenanceOf(v.provenance.truth_status);
  const truthItem = (hint?: Bi): ReadoutItem => ({
    label: { en: 'True one-year PD', es: 'PD anual verdadera' },
    value: o.generator.pd_1y[g] ?? null,
    unitless: true,
    format: pctFormat,
    hint: {
      en: `The default column of exp(Q), Q ${GENERATOR_TEXT.en}.${hint ? ` ${hint.en}` : ''}`,
      es: `La columna de incumplimiento de exp(Q), Q ${GENERATOR_TEXT.es}.${hint ? ` ${hint.es}` : ''}`,
    },
  });
  const num = (x: number | null | undefined, digits = 4): Bi => both((l) => formatNumber(x ?? null, l, { digits }));
  const reps = both((l) => formatNumber(o.design.reps, l));
  if (o.family === 'markov') {
    const est = (o.rungs as C04MarkovRung[])[0]?.estimators[sel.estimator];
    const e = bi(ESTIMATOR_LABEL[sel.estimator]);
    const se = ppText(est?.bias_mcse[g]);
    const rmse = ppText(est?.rmse[g]);
    return {
      title: { en: `${name}, ${e.en}`, es: `${name}, ${e.es}` },
      lane: REPLAY,
      provenance,
      items: [
        truthItem(),
        ppItem({ en: 'Bias', es: 'Sesgo' }, pp(est?.bias[g]), {
          en: `${e.en}: the mean estimate minus the truth over ${num(est?.n[g]).en} repetitions, in percentage points; Monte Carlo SE ${se.en}, RMSE ${rmse.en}.`,
          es: `${e.es}: la estimación media menos la verdad en ${num(est?.n[g]).es} repeticiones, en puntos porcentuales; EE de Monte Carlo ${se.es}, RMSE ${rmse.es}.`,
        }),
      ],
    };
  }
  if (o.family === 'momentum') {
    const rungs = o.rungs as C04MomentumRung[];
    const r = rungs.find((x) => Math.abs(x.value - EMPIRICAL_ALPHA) < 1e-12) ?? rungs[rungs.length - 1];
    const a = num(r?.value);
    const se = ppText(r?.pd_1y_cohort.bias_mcse[g]);
    return {
      title: { en: `${name}, alpha ${a.en}`, es: `${name}, alfa ${a.es}` },
      lane: REPLAY,
      provenance,
      items: [
        truthItem(),
        ppItem({ en: 'Cohort PD bias', es: 'Sesgo de cohortes' }, pp(r?.pd_1y_cohort.bias[g]), {
          en: `The one-year cohort PD over ${reps.en} repetitions minus the plain chain's, in percentage points (Monte Carlo SE ${se.en}): momentum raises the defaults of recently downgraded obligors.`,
          es: `La PD anual de cohortes en ${reps.es} repeticiones menos la de la cadena simple, en puntos porcentuales (EE de Monte Carlo ${se.es}): el momentum eleva los incumplimientos de los deudores recién rebajados.`,
        }),
      ],
    };
  }
  if (o.family === 'cycle') {
    const rungs = o.rungs as C04CycleRung[];
    const r = rungs[rungs.length - 1];
    const k = num(r?.value, 3);
    const stressed = both((l) => formatNumber(r?.pd_true_stressed[g] ?? null, l, pctFormat));
    return {
      title: { en: `${name}, downgrades times ${k.en}`, es: `${name}, rebajas por ${k.es}` },
      lane: REPLAY,
      provenance,
      items: [
        truthItem({ en: 'The stable chain, outside the stressed year.', es: 'La cadena estable, fuera del año estresado.' }),
        ppItem({ en: 'Stressed-year bias', es: 'Sesgo año estresado' }, pp(r?.pd_stressed_year.bias[g]), {
          en: `The stressed year's cohort PD minus its true PD (${stressed.en}: downgrade rates times ${k.en} in the third year), in percentage points; Monte Carlo SE ${ppText(r?.pd_stressed_year.bias_mcse[g]).en}.`,
          es: `La PD de cohortes del año estresado menos su PD verdadera (${stressed.es}: tasas de rebaja por ${k.es} en el tercer año), en puntos porcentuales; EE de Monte Carlo ${ppText(r?.pd_stressed_year.bias_mcse[g]).es}.`,
        }),
        ppItem({ en: 'Long-run bias', es: 'Sesgo largo plazo' }, pp(r?.pd_lra.bias[g]), {
          en: `The mean of the five yearly cohort PDs (EBA/GL/2017/16 paragraph 84) minus the true five-year average, in percentage points; Monte Carlo SE ${ppText(r?.pd_lra.bias_mcse[g]).en}.`,
          es: `La media de las cinco PD anuales de cohortes (párrafo 84 de EBA/GL/2017/16) menos el promedio verdadero de cinco años, en puntos porcentuales; EE de Monte Carlo ${ppText(r?.pd_lra.bias_mcse[g]).es}.`,
        }),
      ],
    };
  }
  if (o.family === 'withdrawals') {
    const rungs = o.rungs as C04WithdrawalsRung[];
    const r = rungs[rungs.length - 1];
    const k = num(r?.value, 3);
    return {
      title: { en: `${name}, withdrawal k ${k.en}`, es: `${name}, retiro k ${k.es}` },
      lane: REPLAY,
      provenance,
      items: [
        truthItem(),
        ppItem({ en: 'Bias, removed', es: 'Sesgo, eliminados' }, pp(r?.pd_removed.bias[g]), {
          en: `Withdrawals removed from the denominator, as CEREP's transition page does (${pick(DEFINITION_LABEL.d4, 'en')}), at informative withdrawal k ${k.en}, in percentage points; Monte Carlo SE ${ppText(r?.pd_removed.bias_mcse[g]).en}.`,
          es: `Retiros eliminados del denominador, como en la página de transiciones de CEREP (${pick(DEFINITION_LABEL.d4, 'es')}), con retiro informativo k ${k.es}, en puntos porcentuales; EE de Monte Carlo ${ppText(r?.pd_removed.bias_mcse[g]).es}.`,
        }),
        ppItem({ en: 'Bias, followed', es: 'Sesgo, seguidos' }, pp(r?.pd_followed.bias[g]), {
          en: `Each withdrawn obligor followed to the end of the year (EBA/GL/2017/16 paragraphs 73 and 76), in percentage points; Monte Carlo SE ${ppText(r?.pd_followed.bias_mcse[g]).en}.`,
          es: `Cada deudor retirado seguido hasta el fin del año (párrafos 73 y 76 de EBA/GL/2017/16), en puntos porcentuales; EE de Monte Carlo ${ppText(r?.pd_followed.bias_mcse[g]).es}.`,
        }),
      ],
    };
  }
  const r = (o.rungs as C04ThinRung[])[0];
  const n = both((l) => formatNumber(r?.value ?? null, l, { decimals: 0 }));
  const expected = both((l) => formatNumber(r?.expected_defaults[g] ?? null, l, { digits: 3 }));
  return {
    title: { en: `${name}, ${n.en} obligors`, es: `${name}, ${n.es} deudores` },
    lane: REPLAY,
    provenance,
    items: [
      truthItem({ en: `${expected.en} defaults expected in a year among ${n.en} obligors.`, es: `${expected.es} incumplimientos esperados en un año entre ${n.es} deudores.` }),
      { label: { en: 'Wald coverage', es: 'Cobertura de Wald' }, value: r?.coverage.wald[g] ?? null, unitless: true, format: { percent: true, decimals: 1 }, hint: { en: 'Exact, by enumeration of the defaults, at 95%.', es: 'Exacta, por enumeración de los incumplimientos, al 95%.' } },
      { label: { en: 'Jeffreys coverage', es: 'Cobertura de Jeffreys' }, value: r?.coverage.jeffreys[g] ?? null, unitless: true, format: { percent: true, decimals: 1 }, hint: { en: 'Exact, by enumeration of the defaults, at 95%.', es: 'Exacta, por enumeración de los incumplimientos, al 95%.' } },
    ],
  };
}

/** The published variant has no grade scale: the reading is Schuermann and Hanson's Table 5 cell. */
function publishedReading(v: PublishedVariant): Reading {
  const s = v.outputs.sr190;
  return {
    title: { en: "Schuermann and Hanson's Table 5", es: 'La Tabla 5 de Schuermann y Hanson' },
    lane: REPLAY,
    provenance: provenanceOf(v.provenance.truth_status),
    items: [
      { label: { en: 'Defaults', es: 'Incumplimientos' }, value: s.defaults, unit: { en: 'defaults', es: 'incumplimientos' }, format: { decimals: 0 }, hint: { en: 'The count that gives every printed bound; the paper does not print it.', es: 'El conteo que da cada cota impresa; el artículo no lo imprime.' } },
      { label: { en: 'Obligors', es: 'Deudores' }, value: s.n, unit: { en: 'obligors', es: 'deudores' }, format: { decimals: 0 } },
      { label: { en: 'Observed rate', es: 'Tasa observada' }, value: s.n > 0 ? s.defaults / s.n : null, unitless: true, format: pctFormat },
    ],
  };
}

function gradeReading(sel: C04Sel | null): Reading {
  const v = sel?.data.variant as VariantArtifact<unknown> | undefined;
  if (sel && v && isAgency(v)) return agencyReading(sel, v);
  if (sel && v && isFamily(v)) return familyReading(sel, v);
  if (sel && v && isPublished(v)) return publishedReading(v);
  return {
    title: { en: 'The grade', es: 'El grado' },
    lane: REPLAY,
    provenance: provenanceOf(v?.provenance.truth_status),
    items: [{ label: { en: 'Long-run average PD', es: 'PD de largo plazo' }, value: null, unitless: true }],
  };
}

/** The rail's grade section: the grade's PD under the definition (agency) or against the truth (family). */
export function GradeReadout({ sel }: { sel: C04Sel | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const r = gradeReading(sel);
  return <Readout title={r.title} lane={r.lane} provenance={r.provenance} dataKey={stateKey} items={r.items} />;
}

/** The largest gap of a path of default rates to a level, signed, with its year (1 is the first). */
export function largestGap(path: readonly number[], level: number): { gap: number; year: number } | null {
  let best: { gap: number; year: number } | null = null;
  for (let i = 0; i < path.length; i++) {
    const x = path[i];
    if (!finite(x)) continue;
    const gap = x - level;
    if (best === null || Math.abs(gap) > Math.abs(best.gap)) best = { gap, year: i + 1 };
  }
  return best;
}

/** The grades a speculative-grade share sums: BB, B and CCC-C. */
const SPECULATIVE = [4, 5, 6];
/** A portfolio's speculative-grade share (BB to CCC-C) of its balance. */
export const speculativeShare = (w: readonly number[] | undefined): number | null => (w ? sum(SPECULATIVE.map((k) => w[k] ?? 0)) : null);

/** The composition projection of an agency whose transition page has no default category (Moody's): the same
 * propagation as the Drift view's, which never defaults, so the portfolio only migrates between grades. Null on any
 * other variant, or where the port refuses the matrix. */
export function useComposition(sel: C04Sel | null): Projection | null {
  return useMemo(() => {
    const v = sel?.data.variant as VariantArtifact<unknown> | undefined;
    if (!sel || !v || !isAgency(v)) return null;
    const o = v.outputs;
    if (o.pooled.matrix.slice(0, GRADES.length).some((row) => row[GRADES.length] > 0)) return null;
    try {
      return project(o.pooled.matrix, startPortfolio(sel.start, o.origination), o.origination, sel.horizon);
    } catch {
      return null;
    }
  }, [sel]);
}

/** The rail's projection section: the TTC default rate of the live chain, the first year's and the horizon's
 * projected default rate from the chosen start, and the largest gap of the path to the TTC rate. On an agency without
 * a default category (Moody's) the portfolio never defaults: the read-out follows its composition instead, the
 * speculative-grade share after one year and at the horizon and the L1 distance to the matrix's long-run mix. */
export function ProjectionReadout({ sel }: { sel: C04Sel | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const live = useProjection(sel);
  const composition = useComposition(sel);
  const v = sel?.data.variant as VariantArtifact<unknown> | undefined;
  const prov = provenanceOf(v?.provenance.truth_status);
  const h = sel?.horizon ?? 20;
  const yearItems = (ttc: number | null, path: readonly number[], hint: BiText): ReadoutItem[] => {
    const gap = ttc === null ? null : largestGap(path, ttc);
    return [
      { label: { en: 'TTC rate', es: 'Tasa TTC' }, value: ttc, unitless: true, format: pctFormat, hint },
      { label: { en: 'Year 1', es: 'Año 1' }, value: path[0] ?? null, unitless: true, format: pctFormat, hint: { en: 'The projected default rate of the first year.', es: 'La tasa de incumplimiento proyectada del primer año.' } },
      { label: { en: `Year ${h}`, es: `Año ${h}` }, value: path[h - 1] ?? null, unitless: true, format: pctFormat, hint: { en: "The projected default rate of the horizon's year.", es: 'La tasa de incumplimiento proyectada del año del horizonte.' } },
      ppItem(
        { en: 'Largest gap', es: 'Mayor brecha' },
        gap ? gap.gap * 100 : null,
        gap
          ? { en: `In year ${gap.year}: the projected rate minus the TTC rate, in percentage points, with no stress at all.`, es: `En el año ${gap.year}: la tasa proyectada menos la tasa TTC, en puntos porcentuales, sin estrés alguno.` }
          : undefined,
      ),
    ];
  };
  if (v && isPublished(v)) {
    const e = v.outputs.engelmann;
    const q = e.portfolios[0];
    return (
      <Readout
        title={{ en: `Engelmann, ${q?.name ?? ''}`, es: `Engelmann, ${q?.name ?? ''}` }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        items={yearItems(e.ttc_pd.recomputed, (q?.pd_path ?? []).slice(0, h), { en: "Engelmann's TTC PD, recomputed from his printed matrix.", es: 'La PD TTC de Engelmann, recalculada desde su matriz impresa.' })}
      />
    );
  }
  const start = sel ? bi(START_LABEL[sel.start]) : null;
  const title: BiText = start ? { en: `${start.en}, ${h} years`, es: `${start.es}, ${h} años` } : { en: 'The projection', es: 'La proyección' };
  if (live && 'projection' in live) {
    const p = live.projection;
    const chain: Bi =
      v && isAgency(v)
        ? { en: `The pooled matrix of ${v.outputs.agency.name}, withdrawals removed. `, es: `La matriz agrupada de ${v.outputs.agency.name}, sin retiros. ` }
        : { en: "The generator's true one-year matrix. ", es: 'La matriz anual verdadera del generador. ' };
    return (
      <Readout
        title={title}
        lane={LIVE}
        provenance={prov}
        dataKey={stateKey}
        items={yearItems(p.ttc.defaultRate, p.defaultRate, {
          en: `${chain.en}The default rate of the matrix's own through-the-cycle portfolio (Engelmann 2024, equation 10), the one every starting portfolio drifts to.`,
          es: `${chain.es}La tasa de incumplimiento de la propia cartera a lo largo del ciclo de la matriz (Engelmann 2024, ecuación 10), hacia la que deriva toda cartera inicial.`,
        })}
      />
    );
  }
  if (composition && v && isAgency(v)) {
    const p = composition;
    const H = p.portfolio.length - 1;
    const none: Bi = {
      en: `${possessive(v.outputs.agency.name)} transition page has no default category: the portfolio never defaults, so it has no default rate to project; it only migrates between grades under the pooled matrix.`,
      es: `La página de transiciones de ${v.outputs.agency.name} no tiene categoría de incumplimiento: la cartera nunca incumple, así que no tiene tasa de incumplimiento que proyectar; solo migra entre grados con la matriz agrupada.`,
    };
    return (
      <Readout
        title={title}
        lane={LIVE}
        provenance={prov}
        dataKey={stateKey}
        items={[
          {
            label: { en: 'Speculative, 1 year', es: 'Especulativa, 1 año' },
            value: speculativeShare(p.portfolio[1]),
            unitless: true,
            format: pctFormat,
            hint: { en: `The share of the balance in BB, B and CCC-C after one year. ${none.en}`, es: `La fracción del saldo en BB, B y CCC-C tras un año. ${none.es}` },
          },
          {
            label: { en: `Speculative, ${H} years`, es: `Especulativa, ${H} años` },
            value: speculativeShare(p.portfolio[H]),
            unitless: true,
            format: pctFormat,
            hint: { en: "The share of the balance in BB, B and CCC-C at the horizon's end.", es: 'La fracción del saldo en BB, B y CCC-C al final del horizonte.' },
          },
          {
            label: { en: 'L1 to the long run', es: 'L1 al largo plazo' },
            value: p.ttc.converged ? (p.distanceToTtc[H] ?? null) : null,
            unitless: true,
            format: { digits: 3 },
            hint: {
              en: "The L1 distance of the horizon's mix to the matrix's own long-run mix, to which the portfolio drifts with nothing leaving it (0 to 2).",
              es: 'La distancia L1 de la mezcla del horizonte a la mezcla de largo plazo de la propia matriz, hacia la que deriva la cartera sin que nada salga de ella (0 a 2).',
            },
          },
        ]}
      />
    );
  }
  const why: BiText =
    live && 'error' in live
      ? live.error
      : { en: 'No live chain on this variant: a transition page without a default category never defaults.', es: 'Sin cadena en vivo en esta variante: una página de transiciones sin categoría de incumplimiento nunca incumple.' };
  return (
    <Readout
      title={title}
      lane={LIVE}
      provenance={prov}
      dataKey={stateKey}
      items={[
        { label: { en: 'TTC rate', es: 'Tasa TTC' }, value: null, unitless: true, hint: why },
        { label: { en: 'Year 1', es: 'Año 1' }, value: null, unitless: true },
        { label: { en: `Year ${h}`, es: `Año ${h}` }, value: null, unitless: true },
      ]}
    />
  );
}

/** The rail's interval section: for the chosen grade's pooled counts (the published variant's Table 5 cell, which
 * has no grade), the effective number of obligors at the rail's correlation (Schuermann and Hanson (3.4)) and the
 * widths of the three intervals at the rail's level. */
export function IntervalReadout({ sel }: { sel: C04Sel | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const rows = useIntervals(sel);
  const v = sel?.data.variant as VariantArtifact<unknown> | undefined;
  const pub = v && isPublished(v) ? v : null;
  // the published variant's counts are Table 5's cell, the same for every grade
  const r = sel ? (pub ? rows[0] : rows.find((x) => x.grade === sel.grade)) : undefined;
  const level = sel?.level ?? 0.95;
  const lvl = both((l) => formatNumber(level, l, { percent: true, decimals: 0 }));
  const unit: Bi = v && isAgency(v) ? { en: 'ratings', es: 'calificaciones' } : v && isFamily(v) ? { en: 'obligor-years', es: 'deudor-años' } : { en: 'obligors', es: 'deudores' };
  const def = v && isAgency(v) && sel ? bi(DEFINITION_LABEL[sel.definition]) : null;
  const rho = both((l) => formatNumber(sel?.rho ?? 0, l, { percent: true, decimals: 2 }));
  const title: BiText = pub
    ? { en: `Table 5, ${pub.outputs.sr190.defaults} of ${formatNumber(pub.outputs.sr190.n, 'en')}, ${lvl.en}`, es: `Tabla 5, ${pub.outputs.sr190.defaults} de ${formatNumber(pub.outputs.sr190.n, 'es')}, ${lvl.es}` }
    : { en: `${GRADES[sel?.grade ?? 0] ?? ''}, ${lvl.en} intervals`, es: `${GRADES[sel?.grade ?? 0] ?? ''}, intervalos al ${lvl.es}` };
  const cell: Bi = pub ? { en: "Schuermann and Hanson's Table 5 cell, no grade: ", es: 'La celda de la Tabla 5 de Schuermann y Hanson, sin grado: ' } : { en: '', es: '' };
  const counts: BiText = r
    ? {
        en: `${cell.en}${formatNumber(r.defaults, 'en')} defaults among ${formatNumber(r.n, 'en')} ${unit.en}${def ? ` (${def.en})` : ''} at a correlation of ${rho.en}: N† = N / (1 + (N - 1) rho), Schuermann and Hanson (3.4).`,
        es: `${cell.es}${formatNumber(r.defaults, 'es')} incumplimientos entre ${formatNumber(r.n, 'es')} ${unit.es}${def ? ` (${def.es})` : ''} con una correlación de ${rho.es}: N† = N / (1 + (N - 1) rho), Schuermann y Hanson (3.4).`,
      }
    : { en: 'The definition gives this grade no counts.', es: 'La definición no da conteos a este grado.' };
  const width = (x: number | undefined) => (finite(x) ? x * 100 : null);
  return (
    <Readout
      title={title}
      lane={LIVE}
      provenance={provenanceOf(v?.provenance.truth_status)}
      dataKey={stateKey}
      items={[
        { label: { en: 'Effective N', es: 'N efectivo' }, value: r?.nEffective ?? null, unit, format: { digits: 4 }, hint: counts },
        ppItem({ en: 'Wald width', es: 'Ancho de Wald' }, width(r?.wald.length), { en: 'Upper bound minus lower bound, in percentage points of PD; N† in place of N.', es: 'Cota superior menos cota inferior, en puntos porcentuales de PD; N† en lugar de N.' }),
        ppItem({ en: 'Agresti-Coull width', es: 'Ancho de Agresti-Coull' }, width(r?.agrestiCoull.length), { en: 'Upper bound minus lower bound, in percentage points of PD; N† in place of N.', es: 'Cota superior menos cota inferior, en puntos porcentuales de PD; N† en lugar de N.' }),
        ppItem({ en: 'Jeffreys width', es: 'Ancho de Jeffreys' }, width(r?.jeffreys.length), { en: 'No correlation correction: the posterior of independent trials.', es: 'Sin corrección por correlación: la posterior de ensayos independientes.' }),
      ]}
    />
  );
}
