// C04's agency variants, the Markov checks (docs/design/features/c04-transitions/web.md, "Agency variants": Markov
// tests and Semesters in the Validation group, Mobility in the Model group; CT-404). Every number is replayed from the
// variant artifact as riskvalidation computed it (contract.md section 1): Anderson and Goodman's time homogeneity
// across the annual and across the semester cohorts and each annual cohort against the pooled matrix, the ECB's
// migration statistics, Jafry and Schuermann's mobility beside the speculative-grade default rate, and the product of
// each year's two semester matrices against the year's own. A p-value's light is its test row's under the committed
// policy (lib/policy), labelled as policy, never as regulation; every card names the agency's EU entity and carries
// CEREP's attribution.
//
// Layout (measured on the built site at 1280 x 800, 2026-10-07): each column holds one filling drawing and each note
// is short, the method being in the case's Context. Two charts stacked in one column under long notes left each chart
// 0 to 45 px of plot, and the per-year table under a second card showed no row at all.
import { PlotCard, formatNumber, pick, useShellLang, useWorkbenchState, type FormatOptions, type ShellColorToken } from '@fasl-work/caos-app-shell';
import { UPlotChart, type ChartSeries } from '@fasl-work/caos-app-shell/chart';
import { useMemo } from 'react';
import type { C04AgencyOutputs, C04Cohort, C04Homogeneity, Light, TestRow, Text, VariantArtifact } from '../../lib/contract.types';
import { COMMITTED, LIGHT_TEXT, LIGHT_TONE, relight } from '../../lib/policy';
import { LightCell } from '../ValidationViews';
import { REPLAY, provenanceOf } from '../model';
import { Pending } from '../Pending';
import { DEFINITION_LABEL, GRADES, N_GRADES, isAgency, type AgencyVariant, type C04Sel, type Definition } from './selection';

type Lang = 'en' | 'es';

/** The policy the lights are read under: the committed one (the C04 rail has no policy section), the thresholds the
 * test rows were evaluated with. */
const POLICY = COMMITTED;

/** The formats of the printed numbers. */
export const FMT = {
  statistic: { digits: 4 },
  dof: { decimals: 0 },
  perDof: { decimals: 1 },
  p: { digits: 2 },
  /** -log10 p: 123.7 reads 124, the policy's 1.301 reads 1.3 */
  evidence: { digits: 3 },
  index: { decimals: 3 },
  rate: { percent: true, decimals: 2 },
  count: { decimals: 0 },
  l1: { decimals: 3 },
  pd: { percent: true, digits: 3 },
} as const satisfies Record<string, FormatOptions>;

/** The smallest value these views give a log axis. uPlot 1.6.32 steps its log ticks up from the scale's floor, and on
 * an axis reaching 1e-23 or below the steps stop advancing until the array overflows (measured in Chromium: 6 to 7 s
 * frozen, then "RangeError: Invalid array length" and a blank chart; axes reaching 1e-22 and 1e-20 drew in about
 * 30 ms). A p-value can be far smaller (S&P's 2002 cohort: 1.9e-124), so p-values are drawn as -log10 p on a linear
 * axis; a PD below the floor would be left out like a zero, and the note would count it. */
export const LOG_FLOOR = 1e-20;

const fin = (x: number | null | undefined): number | null => (typeof x === 'number' && Number.isFinite(x) ? x : null);
/** A value a log axis can draw: finite and not below LOG_FLOOR. */
const onLog = (x: number | null | undefined): number | null => {
  const v = fin(x);
  return v !== null && v >= LOG_FLOOR ? v : null;
};
const sum = (a: readonly number[]) => a.reduce((s, x) => s + x, 0);
const join = (...parts: Text[]): Text => ({
  en: parts.map((p) => p.en).filter(Boolean).join(' '),
  es: parts.map((p) => p.es).filter(Boolean).join(' '),
});
const NONE: Text = { en: '', es: '' };
const upperFirst = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
/** A p-value as LightCell prints it: below the smallest double the engine returns 0, which is not zero. */
const pText = (p: number | null, lang: Lang) => (p === 0 ? '< 1E-300' : formatNumber(p, lang, FMT.p));

/** -log10 of a p-value: the orders of magnitude it lies below 1 (2 is p = 0.01). A p of 0, below the smallest double,
 * has no value, nor has a missing one. */
export function evidence(p: number | null | undefined): number | null {
  const v = fin(p);
  if (v === null || v <= 0) return null;
  return v >= 1 ? 0 : -Math.log10(v);
}

// ---------------------------------------------------------------------------------------------------------------------
// years on an axis

/** What the year axes subtract from a year: nothing, x is the calendar year. The axes write it with `grouping: false`
 * (shell 0.8.2 and later, known shell defect 30), so 2021 ticks as 2021 and never as 2,021. */
export const YEAR0 = 0;
/** The format of a year axis: whole years without a group separator. */
export const YEAR_FORMAT = { decimals: 0, grouping: false } as const;

const yearOf = (label: string): number | null => (/^\d{4}$/.test(label) ? Number(label) : null);

export function yearAxis(_years: readonly number[]): Text {
  return { en: 'Cohort year', es: 'Año de la cohorte' };
}

/** "2001, 2008 to 2009 and 2020": consecutive years joined into a run. */
function yearList(years: readonly number[], lang: Lang): string {
  const ys = [...new Set(years)].sort((a, b) => a - b);
  const runs: string[] = [];
  for (let i = 0; i < ys.length; ) {
    let j = i;
    while (j + 1 < ys.length && ys[j + 1] === ys[j] + 1) j++;
    runs.push(j > i ? `${ys[i]} ${lang === 'en' ? 'to' : 'a'} ${ys[j]}` : String(ys[i]));
    i = j + 1;
  }
  if (runs.length < 2) return runs.join('');
  return `${runs.slice(0, -1).join(', ')} ${lang === 'en' ? 'and' : 'y'} ${runs[runs.length - 1]}`;
}

type Mark = { x: number; label: Text };

/** The credit stress years of the period, marked where the cohorts reach them: the 2008 and 2009 lines share one
 * label, since a label per line would overlap. */
const STRESS = [2001, 2008, 2009, 2020];
export function stressMarks(years: readonly number[]): Mark[] {
  const has = (y: number) => years.includes(y);
  const out: Mark[] = [];
  if (has(2001)) out.push({ x: 2001 - YEAR0, label: { en: '2001', es: '2001' } });
  if (has(2008)) out.push({ x: 2008 - YEAR0, label: has(2009) ? { en: '2008 to 2009', es: '2008 a 2009' } : { en: '2008', es: '2008' } });
  if (has(2009)) out.push({ x: 2009 - YEAR0, label: has(2008) ? NONE : { en: '2009', es: '2009' } });
  if (has(2020)) out.push({ x: 2020 - YEAR0, label: { en: '2020', es: '2020' } });
  return out;
}

// ---------------------------------------------------------------------------------------------------------------------
// a chart by year that never draws an empty series

export interface YearChart {
  x: number[];
  axis: Text;
  /** every data series as the artifact gives it, before the empty ones are left out */
  all: ChartSeries[];
  /** what is drawn: the data series with a value (on a log axis, one of LOG_FLOOR or more), then the reference lines */
  series: ChartSeries[];
  /** how many drawn series hold data: 0 means nothing to draw, and the card shows a table instead */
  drawn: number;
  marks: Mark[];
}

/** A line unless a value stands alone between gaps, which uPlot draws as no line at all: then points. */
function shaped(s: ChartSeries): ChartSeries {
  if (s.mode === 'points') return s;
  const v = s.values;
  const alone = v.some((y, i) => y !== null && (i === 0 || v[i - 1] === null) && (i === v.length - 1 || v[i + 1] === null));
  return alone ? { ...s, mode: 'points' } : s;
}

function yearChart(years: readonly number[], all: ChartSeries[], lines: ChartSeries[], marks: Mark[], log = false): YearChart {
  const x = years.map((y) => y - YEAR0);
  const data = all
    .map((s) => ({ ...s, values: s.values.map((y) => (log ? onLog(y) : fin(y))) }))
    .filter((s) => s.values.some((y) => y !== null))
    .map(shaped);
  return { x, axis: yearAxis(years), all, series: data.length ? [...data, ...lines] : [], drawn: data.length, marks: data.length ? marks : [] };
}

// ---------------------------------------------------------------------------------------------------------------------
// the variant, its test rows, its entity

function agencyOf(sel: C04Sel | null): AgencyVariant | null {
  const v = sel?.data.variant as VariantArtifact<unknown> | undefined;
  return v && isAgency(v) ? v : null;
}

function rowOf(v: AgencyVariant, testId: string, segment: string): TestRow | undefined {
  return v.tests.find((t) => t.test_id === testId && t.model_id === v.outputs.agency.code && t.segment === segment);
}

const lightOf = (row: TestRow | undefined): Light => (row ? relight(row, POLICY) : 'not_evaluated');

/** The statistic a test row reports, by the form its extras name (riskvalidation chooses the form by its measured
 * size: chi-square for time homogeneity, the likelihood ratio against a reference). */
type Form = 'chi2' | 'lr';
const formOf = (row: TestRow | undefined): Form | null => (row?.extras?.form === 'chi2' ? 'chi2' : row?.extras?.form === 'lr' ? 'lr' : null);
const STAT_NAME: Record<Form, Text> = { chi2: { en: 'chi-square', es: 'chi-cuadrado' }, lr: { en: 'likelihood ratio', es: 'razón de verosimilitud' } };
/** The name with its article and, for the likelihood ratio, the abbreviation the table's header uses. */
const STAT_THE: Record<Form, Text> = { chi2: { en: 'the chi-square', es: 'el chi-cuadrado' }, lr: { en: 'the likelihood ratio (LR)', es: 'la razón de verosimilitud (RV)' } };
const STAT_SHORT: Record<Form, Text> = { chi2: { en: 'Chi-square', es: 'Chi-cuadrado' }, lr: { en: 'LR', es: 'RV' } };
/** The form every row shares, else null (the rows then say "statistic"). */
function sharedForm(forms: Array<Form | null>): Form | null {
  const s = new Set(forms);
  return s.size === 1 ? [...s][0] : null;
}
const statName = (f: Form | null): Text => (f ? STAT_NAME[f] : { en: 'statistic', es: 'estadístico' });
const statThe = (f: Form | null): Text => (f ? STAT_THE[f] : { en: 'the statistic', es: 'el estadístico' });
const statShort = (f: Form | null): Text => (f ? STAT_SHORT[f] : { en: 'Statistic', es: 'Estadístico' });

const SCOPE_ES: Record<string, string> = { 'corporate, long-term, categories': 'corporativas, largo plazo, categorías' };

/** The agency's EU entity and the attribution CEREP's licence asks for (verbatim); a table's note adds the scope of
 * the ratings, a chart's leaves it out for the drawing's height. */
function credit(o: C04AgencyOutputs, scope = false): Text {
  if (!scope) return { en: `${o.agency.name}. ${o.attribution}.`, es: `${o.agency.name}. ${o.attribution}.` };
  return {
    en: `${o.agency.name} (${o.agency.scope}). ${o.attribution}.`,
    es: `${o.agency.name} (${SCOPE_ES[o.agency.scope] ?? o.agency.scope}). ${o.attribution}.`,
  };
}

const PICK_YEAR: Text = { en: "Show this year's own matrix in the Matrix view", es: 'Mostrar la matriz propia de este año en la vista Matriz' };
const PICK_NOTE: Text = { en: 'Pick a year for its matrix.', es: 'Elija un año para ver su matriz.' };

/** A year that picks its annual cohort for the Matrix view (the selection's cohort), or plain text without one. */
function YearCell({ sel, label, cohort }: { sel: C04Sel; label: string; cohort: number }) {
  const lang = useShellLang();
  if (cohort < 0) return <td>{label}</td>;
  return (
    <td>
      <button type="button" className="ct-linkbutton" title={pick(PICK_YEAR, lang)} aria-current={sel.cohort === cohort ? 'true' : undefined} onClick={() => sel.act.setCohort(cohort)}>
        {label}
      </button>
    </td>
  );
}

/** Shown where a view of this module meets a variant that is not an agency's (the instrument mounts it on agencies). */
function NotAgency({ sel }: { sel: C04Sel }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = sel.data.variant as VariantArtifact<unknown>;
  return (
    <div className="caos-views-row" data-views="1">
      <div className="ct-col">
        <PlotCard title={{ en: 'An agency check', es: 'Una verificación de agencia' }} lane={REPLAY} provenance={provenanceOf(v.provenance.truth_status)} dataKey={stateKey}>
          <p className="ct-note" data-not-agency={v.variant_id}>
            {pick(
              {
                en: `These checks read an agency's published cohorts (CEREP); the variant ${v.variant_id} holds none.`,
                es: `Estas verificaciones leen las cohortes publicadas de una agencia (CEREP); la variante ${v.variant_id} no tiene ninguna.`,
              },
              lang,
            )}
          </p>
        </PlotCard>
      </div>
    </div>
  );
}

/** What a chart that has nothing to draw holds, as a table by year, so its card still shows what exists. */
function SeriesTable({ x, columns, show, name }: { x: number[]; columns: Array<Pick<ChartSeries, 'label' | 'values'>>; show: (v: number | null, lang: Lang) => string; name: string }) {
  const lang = useShellLang();
  return (
    <div className="ct-scroll">
      <table className="caos-table ct-wrap-head" data-table={name}>
        <thead>
          <tr>
            <th>{pick({ en: 'Year', es: 'Año' }, lang)}</th>
            {columns.map((s) => (
              <th key={pick(s.label, 'en')}>{pick(s.label, lang)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {x.map((xi, i) => (
            <tr key={xi} data-year={xi + YEAR0}>
              <td>{xi + YEAR0}</td>
              {columns.map((s) => (
                <td key={pick(s.label, 'en')}>{show(s.values[i] ?? null, lang)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const shows = (format: FormatOptions) => (v: number | null, lang: Lang) => formatNumber(v, lang, format);

// ---------------------------------------------------------------------------------------------------------------------
// Tests: time homogeneity, each year against the pooled matrix, the ECB's migration statistics

/** One annual cohort's tests: against the pooled matrix (outputs.homogeneity.reference), the ECB's statistics
 * (outputs.ecb), each with its test row, whose light is read under the policy. */
export interface TestYear {
  label: string;
  year: number | null;
  /** the cohort's index in outputs.cohorts (the Matrix view's cohort), -1 when it has none */
  cohort: number;
  ref: { statistic: number | null; p: number | null; dof: number | null; perDof: number | null; form: Form | null; row: TestRow | undefined; light: Light };
  z: { p: number | null; row: TestRow | undefined; light: Light };
  mwbUpper: number | null;
  mwbLower: number | null;
}

export function testYears(v: AgencyVariant): TestYear[] {
  const o = v.outputs;
  const labels = [...new Set([...o.cohorts.map((c) => c.label), ...o.homogeneity.reference.map((r) => r.label), ...o.ecb.map((e) => e.label)])];
  return labels
    .map((label) => {
      const ref = o.homogeneity.reference.find((r) => r.label === label);
      const ecb = o.ecb.find((e) => e.label === label);
      const refRow = rowOf(v, 'rating.matrix_reference', label);
      const zRow = rowOf(v, 'rating.migration_ztests', label);
      const statistic = fin(ref?.statistic);
      const dof = fin(ref?.dof);
      return {
        label,
        year: yearOf(label),
        cohort: o.cohorts.findIndex((c) => c.label === label),
        ref: { statistic, p: fin(ref?.p_value), dof, perDof: statistic !== null && dof ? statistic / dof : null, form: formOf(refRow), row: refRow, light: lightOf(refRow) },
        z: { p: fin(ecb?.ztests_p), row: zRow, light: lightOf(zRow) },
        mwbUpper: fin(ecb?.mwb_upper),
        mwbLower: fin(ecb?.mwb_lower),
      };
    })
    .sort((a, b) => (a.year ?? Number.POSITIVE_INFINITY) - (b.year ?? Number.POSITIVE_INFINITY));
}

/** The lights a p-value can take, each drawn as its own series of points, coloured by the light's tone. */
const BUCKETS = ['red', 'amber', 'green', 'other'] as const;
type Bucket = (typeof BUCKETS)[number];
const bucketOf = (l: Light): Bucket => (l === 'red' || l === 'amber' || l === 'green' ? l : 'other');
const BUCKET_LIGHT: Record<Bucket, Light> = { red: 'red', amber: 'amber', green: 'green', other: 'not_evaluated' };
const TONE_COLOR: Record<(typeof LIGHT_TONE)[Light], ShellColorToken> = { good: '--color-good', warn: '--color-warn', bad: '--color-bad', neutral: '--color-fg-subtle' };

function bucketLabel(b: Bucket, n: number, total: number): Text {
  const word = (lang: Lang) => upperFirst(pick(LIGHT_TEXT[BUCKET_LIGHT[b]], lang));
  const amber = (lang: Lang) => formatNumber(POLICY.amber, lang);
  const red = (lang: Lang) => formatNumber(POLICY.red, lang);
  if (b === 'red') return { en: `${word('en')}, p below ${red('en')}: ${n} of ${total}`, es: `${word('es')}, p bajo ${red('es')}: ${n} de ${total}` };
  if (b === 'amber') return { en: `${word('en')}, p from ${red('en')} to ${amber('en')}: ${n} of ${total}`, es: `${word('es')}, p de ${red('es')} a ${amber('es')}: ${n} de ${total}` };
  if (b === 'green') return { en: `${word('en')}, p of ${amber('en')} or more: ${n} of ${total}`, es: `${word('es')}, p de ${amber('es')} o más: ${n} de ${total}` };
  return { en: `${word('en')}: ${n} of ${total}`, es: `${word('es')}: ${n} de ${total}` };
}

/** The policy's amber and red thresholds as constant lines at their -log10 p, labelled as the policy's. */
function thresholdLines(n: number): ChartSeries[] {
  const line = (p: number, en: string, es: string, color: ShellColorToken): ChartSeries => {
    const at = evidence(p) as number;
    return {
      label: {
        en: `${en} policy threshold, p = ${formatNumber(p, 'en')} (${formatNumber(at, 'en', FMT.evidence)})`,
        es: `Umbral ${es} de la política, p = ${formatNumber(p, 'es')} (${formatNumber(at, 'es', FMT.evidence)})`,
      },
      values: Array.from({ length: n }, () => at),
      color,
      width: 1.2,
      dash: [6, 4],
    };
  };
  return [line(POLICY.amber, 'Amber', 'ámbar', '--color-warn'), line(POLICY.red, 'Red', 'rojo', '--color-bad')];
}

const UNDERFLOW: Text = { en: 'p < 1E-300', es: 'p < 1E-300' };

/** A light after "lit" (con luz): the Spanish adjective agrees with "luz". */
const LIT: Record<'red' | 'amber', Text> = { red: { en: 'red', es: 'roja' }, amber: { en: 'amber', es: 'ámbar' } };

export interface ReferenceChart extends YearChart {
  /** the y range: from 0 (p = 1) to above the largest value and the red threshold */
  range: [number, number];
}

/** Each annual cohort against the pooled matrix: -log10 p by year on a linear axis, one series of points per light,
 * the policy's thresholds as lines. A p-value the engine returns as 0 (below the smallest double) has no -log10 p:
 * its year is marked by a line instead. */
export function referenceChart(years: TestYear[]): ReferenceChart {
  const pts = years.filter((r) => r.year !== null);
  const tested = pts.filter((r) => r.ref.p !== null);
  const all: ChartSeries[] = BUCKETS.map((b) => ({
    label: bucketLabel(b, tested.filter((r) => bucketOf(r.ref.light) === b).length, tested.length),
    values: pts.map((r) => (bucketOf(r.ref.light) === b ? evidence(r.ref.p) : null)),
    color: TONE_COLOR[LIGHT_TONE[BUCKET_LIGHT[b]]],
    mode: 'points',
  }));
  const marks = pts.filter((r) => r.ref.p === 0).map((r) => ({ x: (r.year as number) - YEAR0, label: UNDERFLOW }));
  const chart = yearChart(
    pts.map((r) => r.year as number),
    all,
    thresholdLines(pts.length),
    marks,
  );
  const top = Math.max(evidence(POLICY.red) as number, ...chart.series.flatMap((s) => s.values.filter((y): y is number => y !== null)));
  return { ...chart, range: [0, top * 1.08] };
}

/** The grade whose row departs most from homogeneity: the largest statistic per degree of freedom among the test's
 * rows, in the form the row reports (its extras). */
function worstRow(row: TestRow | undefined): { grade: string; ratio: number } | null {
  const rows = row?.extras?.rows;
  const form = formOf(row);
  if (!Array.isArray(rows) || !form) return null;
  let worst: { grade: string; ratio: number } | null = null;
  for (const r of rows as Array<Record<string, unknown>>) {
    const i = r.row;
    const s = r[form];
    const d = r.dof;
    if (typeof i !== 'number' || typeof s !== 'number' || typeof d !== 'number' || d <= 0 || i < 0 || i >= N_GRADES) continue;
    if (!worst || s / d > worst.ratio) worst = { grade: GRADES[i], ratio: s / d };
  }
  return worst;
}

interface Homogeneity {
  key: 'annual' | 'semesters';
  /** the periods tested ("26 years"), and their span for the cell's title */
  label: Text;
  span: Text;
  h: C04Homogeneity | null;
  row: TestRow | undefined;
  form: Form | null;
  worst: { grade: string; ratio: number } | null;
}

function homogeneity(v: AgencyVariant): Homogeneity[] {
  const o = v.outputs;
  const periods = (cohorts: C04Cohort[], h: C04Homogeneity | null, en: string, es: string): { label: Text; span: Text } => {
    const n = fin(h?.periods) ?? cohorts.length;
    if (cohorts.length === 0) return { label: { en: `${upperFirst(en)}: none`, es: `${upperFirst(es)}: ninguno` }, span: NONE };
    const a = cohorts[0].label;
    const b = cohorts[cohorts.length - 1].label;
    return { label: { en: `${n} ${en}`, es: `${n} ${es}` }, span: { en: `${n} ${en}, ${a} to ${b}`, es: `${n} ${es}, ${a} a ${b}` } };
  };
  const annual = rowOf(v, 'rating.time_homogeneity', 'annual');
  const semesters = rowOf(v, 'rating.time_homogeneity', 'semesters');
  return [
    { key: 'annual', ...periods(o.cohorts, o.homogeneity.annual, 'years', 'años'), h: o.homogeneity.annual, row: annual, form: formOf(annual), worst: worstRow(annual) },
    { key: 'semesters', ...periods(o.semesters, o.homogeneity.semesters, 'semesters', 'semestres'), h: o.homogeneity.semesters, row: semesters, form: formOf(semesters), worst: worstRow(semesters) },
  ];
}

export function TestsView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = agencyOf(sel);
  const built = useMemo(() => {
    if (!v) return null;
    const years = testYears(v);
    return { years, ref: referenceChart(years), homog: homogeneity(v) };
  }, [v]);
  if (!sel) return <Pending />;
  if (!v || !built) return <NotAgency sel={sel} />;
  const o = v.outputs;
  const prov = provenanceOf(v.provenance.truth_status);
  const { years, ref, homog } = built;

  // the reference test: its statistic, its degrees of freedom, the years below the smallest double
  const refForm = sharedForm(years.filter((r) => r.ref.row).map((r) => r.ref.form));
  const dofs = [...new Set(years.map((r) => r.ref.dof).filter((d): d is number => d !== null))].sort((a, b) => a - b);
  const dofText = (l: Lang) => (dofs.length === 0 ? '-' : dofs.length === 1 ? formatNumber(dofs[0], l, FMT.dof) : `${formatNumber(dofs[0], l, FMT.dof)} ${l === 'en' ? 'to' : 'a'} ${formatNumber(dofs[dofs.length - 1], l, FMT.dof)}`);
  const under = years.filter((r) => r.ref.p === 0 && r.year !== null).map((r) => r.year as number);
  const refNote = ref.drawn
    ? join(
        {
          en: `-log10 p of each annual cohort's counts against the matrix pooled over its ${o.pooled.cohorts} cohorts (${pick(statName(refForm), 'en')}, ${dofText('en')} dof), withdrawals removed; each point lit under the committed policy.`,
          es: `-log10 p de los conteos de cada cohorte anual contra la matriz agrupada sobre sus ${o.pooled.cohorts} cohortes (${pick(statName(refForm), 'es')}, ${dofText('es')} gl), sin retiros; cada punto con su luz según la política comprometida.`,
        },
        under.length
          ? {
              en: `Dashed: ${yearList(under, 'en')}, p below 1E-300, the smallest number the engine represents.`,
              es: `${under.length > 1 ? 'Segmentadas' : 'Segmentada'}: ${yearList(under, 'es')}, p bajo 1E-300, el menor número que el motor representa.`,
            }
          : NONE,
        credit(o),
      )
    : join({ en: 'No cohort has a p-value to draw: the table gives what the artifact holds.', es: 'Ninguna cohorte tiene un valor p que dibujar: la tabla da lo que contiene el artefacto.' }, credit(o));

  // the table: time homogeneity, then every year's tests; the years whose ECB z-tests are lit
  const homForm = sharedForm(homog.filter((h) => h.row).map((h) => h.form));
  const zLit = (['red', 'amber'] as const)
    .map((light) => ({ light, years: years.filter((r) => r.z.light === light && r.year !== null).map((r) => r.year as number) }))
    .filter((z) => z.years.length);
  const zText = (l: Lang) =>
    zLit.length
      ? `${l === 'en' ? 'lit' : 'con luz'} ${zLit.map((z) => `${pick(LIT[z.light], l)} ${l === 'en' ? 'in' : 'en'} ${yearList(z.years, l)}`).join(l === 'en' ? ' and ' : ' y ')}`
      : l === 'en'
        ? 'lit amber or red in no year'
        : 'sin luz ámbar ni roja en ningún año';
  const tableNote = join(
    {
      en: `By year: ${pick(statThe(refForm), 'en')} per degree of freedom (dof) against the pooled matrix, 1 under the null, with its p; the family-wise p (Holm) of the ECB z-tests, ${zText('en')}; the ECB's matrix weighted bandwidths (MWB), 0 when nobody migrates. Lights: policy thresholds, not regulatory. ${PICK_NOTE.en}`,
      es: `Por año: ${pick(statThe(refForm), 'es')} por grado de libertad (gl) contra la matriz agrupada, 1 bajo la nula, con su p; el p a nivel de familia (Holm) de las pruebas z del BCE, ${zText('es')}; los anchos de banda ponderados de la matriz del BCE (MWB), 0 si nadie migra. Luces: umbrales de política, no regulatorios. ${PICK_NOTE.es}`,
    },
    credit(o),
  );

  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col">
        <PlotCard fill title={{ en: 'Each year against the pooled matrix', es: 'Cada año contra la matriz agrupada' }} lane={REPLAY} provenance={prov} dataKey={stateKey} note={refNote}>
          {ref.drawn ? (
            <UPlotChart
              height="fill"
              x={{ values: ref.x, label: ref.axis, format: YEAR_FORMAT }}
              y={{ label: { en: '-log10 p (2 is p = 0.01)', es: '-log10 p (2 es p = 0,01)' }, format: FMT.evidence, range: ref.range }}
              series={ref.series}
              marks={ref.marks}
            />
          ) : (
            <SeriesTable x={ref.x} columns={[{ label: { en: 'p-value', es: 'Valor p' }, values: years.filter((r) => r.year !== null).map((r) => r.ref.p) }]} show={pText} name="reference-p" />
          )}
        </PlotCard>
      </div>
      <div className="ct-col">
        <PlotCard fill title={{ en: "Every year's tests", es: 'Las pruebas de cada año' }} lane={REPLAY} provenance={prov} dataKey={stateKey} note={tableNote}>
          <div className="ct-stack">
            <table className="caos-table ct-wrap-head" data-table="time-homogeneity">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'The same matrix for every period?', es: '¿Una sola matriz para todos los períodos?' }, lang)}</th>
                  <th>{pick({ en: `${pick(statShort(homForm), 'en')} / dof`, es: `${pick(statShort(homForm), 'es')} / gl` }, lang)}</th>
                  <th>{pick({ en: 'p and light', es: 'p y luz' }, lang)}</th>
                  <th className="ct-wide-only">{pick({ en: 'Per dof', es: 'Por gl' }, lang)}</th>
                  <th className="ct-wide-only">{pick({ en: 'Row furthest', es: 'Fila más alejada' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {homog.map((h) => {
                  const stat = fin(h.h?.statistic);
                  const dof = fin(h.h?.dof);
                  return (
                    <tr key={h.key} data-segment={h.key}>
                      <td className="ct-text" title={pick(h.span, lang)}>
                        {pick(h.label, lang)}
                      </td>
                      <td>{stat !== null && dof !== null ? `${homForm || !h.form ? '' : `${pick(STAT_NAME[h.form], lang)} `}${formatNumber(stat, lang, FMT.statistic)} / ${formatNumber(dof, lang, FMT.dof)}` : '-'}</td>
                      <LightCell row={h.row} alphas={POLICY} />
                      <td className="ct-wide-only">{stat !== null && dof ? formatNumber(stat / dof, lang, FMT.perDof) : '-'}</td>
                      <td className="ct-wide-only">{h.worst ? `${h.worst.grade} (${formatNumber(h.worst.ratio, lang, FMT.perDof)})` : '-'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <div className="ct-scroll">
              <table className="caos-table ct-wrap-head" data-table="tests-by-year">
                <thead>
                  <tr>
                    <th>{pick({ en: 'Year', es: 'Año' }, lang)}</th>
                    <th className="ct-wide-only">{pick({ en: `${pick(statShort(refForm), 'en')} / dof`, es: `${pick(statShort(refForm), 'es')} / gl` }, lang)}</th>
                    <th>{pick({ en: 'Pooled: p', es: 'Agrupada: p' }, lang)}</th>
                    <th>{pick({ en: 'z-tests: p', es: 'Pruebas z: p' }, lang)}</th>
                    <th className="ct-wide-only">{pick({ en: 'MWB above', es: 'MWB sobre' }, lang)}</th>
                    <th className="ct-wide-only">{pick({ en: 'MWB below', es: 'MWB bajo' }, lang)}</th>
                  </tr>
                </thead>
                <tbody>
                  {years.map((r) => (
                    <tr key={r.label} data-year={r.label} className={sel.cohort !== null && r.cohort === sel.cohort ? 'ct-current' : undefined}>
                      <YearCell sel={sel} label={r.label} cohort={r.cohort} />
                      <td className="ct-wide-only">{formatNumber(r.ref.perDof, lang, FMT.perDof)}</td>
                      <LightCell row={r.ref.row} alphas={POLICY} />
                      <LightCell row={r.z.row} alphas={POLICY} />
                      <td className="ct-wide-only">{formatNumber(r.mwbUpper, lang, FMT.index)}</td>
                      <td className="ct-wide-only">{formatNumber(r.mwbLower, lang, FMT.index)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </PlotCard>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// Mobility: M_SVD and the trace index by cohort beside the speculative-grade default rate, on one axis

export interface MobilityYear {
  label: string;
  year: number | null;
  cohort: number;
  svd: number | null;
  trace: number | null;
  rate: number | null;
  /** the cohort's ratings at the start, withdrawals included */
  ratings: number | null;
}

export function mobilityYears(v: AgencyVariant): MobilityYear[] {
  const o = v.outputs;
  const m = o.mobility;
  return m.labels.map((label, i) => {
    const k = o.cohorts.findIndex((c) => c.label === label);
    return { label, year: yearOf(label), cohort: k, svd: fin(m.svd[i]), trace: fin(m.trace[i]), rate: fin(m.spec_default_rate[i]), ratings: k >= 0 ? sum(o.cohorts[k].size) : null };
  });
}

/** The definition of the speculative-grade default rate: D2 where the agency publishes its default-rate page, else D3
 * (contract.md, "mobility"). */
export const specDefinition = (o: C04AgencyOutputs): Definition => (o.pd.d2 !== null ? 'd2' : 'd3');

/** What the speculative-grade rate counts, in a clause (the definition's own words, shortened for this view). */
const SPEC_COUNTS: Partial<Record<Definition, Text>> = {
  d2: {
    en: "the ratings with at least one default event in the year, over the default-rate page's own cohort, withdrawals included",
    es: 'las calificaciones con al menos un evento de incumplimiento en el año, sobre la cohorte propia de la página de tasas de incumplimiento, con los retiros',
  },
  d3: {
    en: "every default event of the year, over the transition page's cohort",
    es: 'cada evento de incumplimiento del año, sobre la cohorte de la página de transiciones',
  },
};

/** The three series on one axis: both indices are 0 when nobody moves and at most 1, and the default rate is drawn as
 * the share of the cohort it is (0.10 is 10%), so one scale reads all three and the cursor reads them together. */
export function mobilityChart(v: AgencyVariant): { years: MobilityYear[]; definition: Definition; chart: YearChart } {
  const years = mobilityYears(v);
  const pts = years.filter((r) => r.year !== null);
  const ys = pts.map((r) => r.year as number);
  const d = specDefinition(v.outputs);
  return {
    years,
    definition: d,
    chart: yearChart(
      ys,
      [
        { label: { en: 'M_SVD (Jafry and Schuermann)', es: 'M_SVD (Jafry y Schuermann)' }, values: pts.map((r) => r.svd), color: '--color-accent', width: 2 },
        { label: { en: 'Mobility index (n - tr P)/(n - 1)', es: 'Índice de movilidad (n - tr P)/(n - 1)' }, values: pts.map((r) => r.trace), color: '--color-magenta', width: 2, dash: [6, 3] },
        {
          label: { en: `Speculative-grade default rate, ${pick(DEFINITION_LABEL[d], 'en')}`, es: `Tasa de incumplimiento de grado especulativo, ${pick(DEFINITION_LABEL[d], 'es')}` },
          values: pts.map((r) => r.rate),
          color: '--color-bad',
          width: 2,
        },
      ],
      [],
      stressMarks(ys),
    ),
  };
}

export function MobilityView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = agencyOf(sel);
  const built = useMemo(() => (v ? mobilityChart(v) : null), [v]);
  if (!sel) return <Pending />;
  if (!v || !built) return <NotAgency sel={sel} />;
  const o = v.outputs;
  const prov = provenanceOf(v.provenance.truth_status);
  const { years, definition: d, chart } = built;
  const label = DEFINITION_LABEL[d];
  const stress = (l: Lang) => yearList(STRESS.filter((y) => years.some((r) => r.year === y)), l);
  const counts = SPEC_COUNTS[d] ?? NONE;
  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col ct-share-3">
        <PlotCard
          fill
          title={{ en: "Mobility of each year's matrix and the default rate", es: 'Movilidad de la matriz de cada año y la tasa de incumplimiento' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={
            chart.drawn
              ? join(
                  {
                    en: `Each annual cohort's own matrix, withdrawals removed: Jafry and Schuermann's M_SVD (the mean singular value of P - I) and the trace index (n - tr P)/(n - 1), both 0 when nobody moves; beside them the speculative-grade default rate (BB, B and CCC-C pooled, ${pick(label, 'en')}) as a share of the cohort on the same axis (0.10 is 10%).`,
                    es: `La matriz propia de cada cohorte anual, sin retiros: la M_SVD de Jafry y Schuermann (el valor singular medio de P - I) y el índice de traza (n - tr P)/(n - 1), ambos 0 si nadie se mueve; junto a ellos la tasa de incumplimiento de grado especulativo (BB, B y CCC-C agrupados, ${pick(label, 'es')}) como fracción de la cohorte en el mismo eje (0,10 es 10%).`,
                  },
                  stress('en') ? { en: `Dashed: the stress years ${stress('en')}.`, es: `Segmentadas: los años de tensión ${stress('es')}.` } : NONE,
                  credit(o),
                )
              : join({ en: 'No cohort has an index or a default rate to draw: the table gives what the artifact holds.', es: 'Ninguna cohorte tiene un índice ni una tasa de incumplimiento que dibujar: la tabla da lo que contiene el artefacto.' }, credit(o))
          }
        >
          {chart.drawn ? (
            <UPlotChart
              height="fill"
              x={{ values: chart.x, label: chart.axis, format: YEAR_FORMAT }}
              y={{ label: { en: 'Index, or default rate as a share', es: 'Índice, o tasa de incumplimiento como fracción' }, format: { decimals: 2 } }}
              series={chart.series}
              marks={chart.marks}
            />
          ) : (
            <SeriesTable x={chart.x} columns={chart.all} show={shows(FMT.index)} name="mobility-index" />
          )}
        </PlotCard>
      </div>
      <div className="ct-col ct-share-2">
        <PlotCard
          fill
          title={{ en: 'Mobility and defaults by year', es: 'Movilidad e incumplimientos por año' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={join(
            {
              en: `The chart's numbers and each cohort's ratings at the start, withdrawals included. The default rate is ${pick(label, 'en')}: ${counts.en}. ${PICK_NOTE.en}`,
              es: `Los números del gráfico y las calificaciones de cada cohorte al inicio, con los retiros. La tasa de incumplimiento es ${pick(label, 'es')}: ${counts.es}. ${PICK_NOTE.es}`,
            },
            credit(o, true),
          )}
        >
          <div className="ct-scroll">
            <table className="caos-table ct-wrap-head" data-table="mobility">
              <thead>
                <tr>
                  <th>{pick({ en: 'Year', es: 'Año' }, lang)}</th>
                  <th>M_SVD</th>
                  <th>{pick({ en: 'Trace', es: 'Traza' }, lang)}</th>
                  <th>{pick({ en: `Default rate (${d.toUpperCase()})`, es: `Tasa de incumpl. (${d.toUpperCase()})` }, lang)}</th>
                  <th className="ct-wide-only">{pick({ en: 'Ratings', es: 'Calif.' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {years.map((r) => (
                  <tr key={r.label} data-year={r.label} className={sel.cohort !== null && r.cohort === sel.cohort ? 'ct-current' : undefined}>
                    <YearCell sel={sel} label={r.label} cohort={r.cohort} />
                    <td>{formatNumber(r.svd, lang, FMT.index)}</td>
                    <td>{formatNumber(r.trace, lang, FMT.index)}</td>
                    <td>{formatNumber(r.rate, lang, FMT.rate)}</td>
                    <td className="ct-wide-only">{formatNumber(r.ratings, lang, FMT.count)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// Semesters: each year's two semester matrices multiplied, against the year's own

export interface SemesterYear {
  year: number;
  l1: number | null;
  /** the chosen grade's PD: the default column of P_H1 P_H2, and of P_year */
  product: number | null;
  annual: number | null;
  /** the ratings at the start of each semester and of the year, withdrawals included */
  h1: number | null;
  h2: number | null;
  ratings: number | null;
}

const ratingsOf = (cohorts: C04Cohort[], label: string): number | null => {
  const c = cohorts.find((x) => x.label === label);
  return c ? sum(c.size) : null;
};

export function semesterYears(v: AgencyVariant, grade: number): SemesterYear[] {
  const o = v.outputs;
  return o.semesters_vs_year.map((r) => ({
    year: r.year,
    l1: fin(r.l1),
    product: fin(r.pd_product[grade]),
    annual: fin(r.pd_annual[grade]),
    h1: ratingsOf(o.semesters, `${r.year}H1`),
    h2: ratingsOf(o.semesters, `${r.year}H2`),
    ratings: ratingsOf(o.cohorts, String(r.year)),
  }));
}

/** Why the PD card draws what it draws: no default category in the agency's transition page (Moody's), no PD of the
 * grade defined in any year, no PD above 0 for a log axis, or a chart. */
export type SemestersCase = 'no-category' | 'undefined' | 'zero' | 'drawn';

export interface SemestersBuilt {
  grade: number;
  years: SemesterYear[];
  l1: YearChart;
  pd: YearChart;
  case: SemestersCase;
  /** years with both PDs and a default in either, and those where the product's is above or below the year's */
  pairs: number;
  above: number;
  below: number;
  /** PDs of exactly 0, which a log axis cannot draw, and positive ones below LOG_FLOOR, left out as well */
  zeroProduct: number;
  zeroAnnual: number;
  tiny: number;
  /** years whose own matrix has an empty default column in every grade */
  emptyYears: number[];
  largest: { year: number; l1: number } | null;
}

export function semestersCharts(v: AgencyVariant, grade: number): SemestersBuilt {
  const o = v.outputs;
  const g = Math.min(N_GRADES - 1, Math.max(0, Math.round(grade)));
  const years = semesterYears(v, g);
  const ys = years.map((r) => r.year);
  let largest: { year: number; l1: number } | null = null;
  for (const r of years) if (r.l1 !== null && (!largest || r.l1 > largest.l1)) largest = { year: r.year, l1: r.l1 };
  const marks: Mark[] = [];
  if (ys.includes(2020)) marks.push({ x: 2020 - YEAR0, label: largest?.year === 2020 ? { en: '2020, the largest', es: '2020, la mayor' } : { en: '2020', es: '2020' } });
  if (largest && largest.year !== 2020) marks.push({ x: largest.year - YEAR0, label: { en: 'the largest', es: 'la mayor' } });
  const gradeName = GRADES[g];
  const pairs = years.filter((r) => r.product !== null && r.annual !== null && (r.product > 0 || r.annual > 0));
  const pd = yearChart(
    ys,
    [
      { label: { en: `${gradeName}, product of the semesters`, es: `${gradeName}, producto de los semestres` }, values: years.map((r) => r.product), color: '--color-accent', mode: 'points' },
      { label: { en: `${gradeName}, the year's matrix`, es: `${gradeName}, la matriz del año` }, values: years.map((r) => r.annual), color: '--color-fg', mode: 'points' },
    ],
    [],
    [],
    true,
  );
  const defined = years.some((r) => r.product !== null || r.annual !== null);
  const kind: SemestersCase = o.pd.d4 === null ? 'no-category' : !defined ? 'undefined' : pd.drawn ? 'drawn' : 'zero';
  return {
    grade: g,
    years,
    l1: yearChart(ys, [{ label: { en: 'P(H1) P(H2) against P(year)', es: 'P(H1) P(H2) contra P(año)' }, values: years.map((r) => r.l1), color: '--color-accent', width: 2 }], [], marks),
    pd,
    case: kind,
    pairs: pairs.length,
    above: pairs.filter((r) => (r.product as number) > (r.annual as number)).length,
    below: pairs.filter((r) => (r.product as number) < (r.annual as number)).length,
    zeroProduct: years.filter((r) => r.product === 0).length,
    zeroAnnual: years.filter((r) => r.annual === 0).length,
    tiny: years.reduce((n, r) => n + [r.product, r.annual].filter((p) => p !== null && p > 0 && p < LOG_FLOOR).length, 0),
    emptyYears: o.semesters_vs_year.filter((r) => r.pd_annual.length > 0 && r.pd_annual.every((p) => p === 0)).map((r) => r.year),
    largest,
  };
}

export function SemestersView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = agencyOf(sel);
  const grade = sel?.grade ?? N_GRADES - 1;
  const built = useMemo(() => (v ? semestersCharts(v, grade) : null), [v, grade]);
  if (!sel) return <Pending />;
  if (!v || !built) return <NotAgency sel={sel} />;
  const o = v.outputs;
  const prov = provenanceOf(v.provenance.truth_status);
  const g = GRADES[built.grade];
  // the definition of the PDs compared, in this view's own words (DEFINITION_HINT speaks of every agency)
  const d4: Text = {
    en: `${pick(DEFINITION_LABEL.d4, 'en')}: the default column over the cohort less its withdrawals`,
    es: `${pick(DEFINITION_LABEL.d4, 'es')}: la columna de incumplimiento sobre la cohorte menos sus retiros`,
  };
  const marksText = (l: Lang) =>
    [
      ...(built.years.some((r) => r.year === 2020) ? [l === 'en' ? '2020, a stress year' : '2020, un año de tensión'] : []),
      ...(built.largest && built.largest.year !== 2020 ? [`${built.largest.year}, ${l === 'en' ? 'the largest distance' : 'la mayor distancia'}`] : []),
    ].join('; ');
  const l1Note = join(
    {
      en: "Each year with both semesters published: the L1 distance (the absolute differences summed over the 8 x 8 cells, at most 2 a row) between the product of the two semester matrices and the year's own matrix, withdrawals removed in all three. A Markov chain makes them agree up to sampling error (Chapman-Kolmogorov); the second semester's cohort also holds the ratings issued in the first.",
      es: 'Cada año con ambos semestres publicados: la distancia L1 (las diferencias absolutas sumadas sobre las 8 x 8 celdas, a lo más 2 por fila) entre el producto de las dos matrices semestrales y la matriz propia del año, sin retiros en las tres. Una cadena de Markov las hace coincidir salvo error muestral (Chapman-Kolmogorov); la cohorte del segundo semestre también tiene las calificaciones emitidas en el primero.',
    },
    marksText('en') ? { en: `Dashed: ${marksText('en')}.`, es: `Segmentadas: ${marksText('es')}.` } : NONE,
    credit(o),
  );
  const empty = built.emptyYears.length
    ? {
        en: `The year's default column is empty in every grade in ${yearList(built.emptyYears, 'en')}.`,
        es: `La columna de incumplimiento del año está vacía en todos los grados en ${yearList(built.emptyYears, 'es')}.`,
      }
    : NONE;
  const zeros =
    built.zeroAnnual + built.zeroProduct > 0
      ? {
          en: `PDs of 0, which a log axis cannot draw: ${built.zeroAnnual} of the year's and ${built.zeroProduct} of the product's.`,
          es: `PD de 0, que un eje logarítmico no puede dibujar: ${built.zeroAnnual} del año y ${built.zeroProduct} del producto.`,
        }
      : NONE;
  const tiny =
    built.tiny === 1
      ? { en: 'A PD below 1E-20 is left out as well (the log axis would not draw).', es: 'Una PD bajo 1E-20 también queda fuera (el eje logarítmico no se dibujaría).' }
      : built.tiny > 1
        ? { en: `${built.tiny} PDs below 1E-20 are left out as well (the log axis would not draw).`, es: `${built.tiny} PD bajo 1E-20 también quedan fuera (el eje logarítmico no se dibujaría).` }
        : NONE;
  const pdTable = (
    <div className="ct-scroll">
      <table className="caos-table ct-wrap-head" data-table="semesters-pd">
        <thead>
          <tr>
            <th>{pick({ en: 'Year', es: 'Año' }, lang)}</th>
            <th>{pick({ en: `${g}, product`, es: `${g}, producto` }, lang)}</th>
            <th>{pick({ en: `${g}, year`, es: `${g}, año` }, lang)}</th>
            <th>L1</th>
          </tr>
        </thead>
        <tbody>
          {built.years.map((r) => (
            <tr key={r.year} data-year={r.year}>
              <td>{r.year}</td>
              <td>{formatNumber(r.product, lang, FMT.pd)}</td>
              <td>{formatNumber(r.annual, lang, FMT.pd)}</td>
              <td>{formatNumber(r.l1, lang, FMT.l1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
  let pdTitle: Text = { en: `${g}: one-year PD, the semesters' product against the year`, es: `${g}: PD a un año, el producto de los semestres contra el año` };
  let pdNote: Text;
  let pdBody;
  if (built.case === 'no-category') {
    // the agency's transition page has no default category (Moody's): neither matrix has a default column
    pdTitle = { en: 'No default column: the cohorts behind each distance', es: 'Sin columna de incumplimiento: las cohortes detrás de cada distancia' };
    pdNote = join(
      {
        en: `This agency's transition page has no default category, so neither the semesters' product nor the year's matrix has a default column to give ${g}'s PD. The table gives each year's distance and the ratings at the start of each semester and of the year, withdrawals included.`,
        es: `La página de transiciones de esta agencia no tiene categoría de incumplimiento, así que ni el producto de los semestres ni la matriz del año tienen una columna de incumplimiento que dé la PD de ${g}. La tabla da la distancia de cada año y las calificaciones al inicio de cada semestre y del año, con los retiros.`,
      },
      credit(o, true),
    );
    pdBody = (
      <div className="ct-scroll">
        <table className="caos-table ct-wrap-head" data-table="semesters-cohorts">
          <thead>
            <tr>
              <th>{pick({ en: 'Year', es: 'Año' }, lang)}</th>
              <th>L1</th>
              <th>{pick({ en: 'Ratings, H1', es: 'Calif., H1' }, lang)}</th>
              <th>{pick({ en: 'Ratings, H2', es: 'Calif., H2' }, lang)}</th>
              <th>{pick({ en: 'Ratings, year', es: 'Calif., año' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {built.years.map((r) => (
              <tr key={r.year} data-year={r.year}>
                <td>{r.year}</td>
                <td>{formatNumber(r.l1, lang, FMT.l1)}</td>
                <td>{formatNumber(r.h1, lang, FMT.count)}</td>
                <td>{formatNumber(r.h2, lang, FMT.count)}</td>
                <td>{formatNumber(r.ratings, lang, FMT.count)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  } else if (built.case === 'undefined') {
    // the agency has a default category, but the grade's row is undefined in every year
    pdNote = join(
      {
        en: `No ${g} PD is defined in any year: a matrix row is undefined where the grade has no rating at the start of a period, and the product's where the first semester moves ratings into a grade without any at the start of the second. The table gives each year's distance. ${d4.en}.`,
        es: `Ninguna PD de ${g} está definida en ningún año: la fila de una matriz no está definida donde el grado no tiene calificaciones al inicio de un período, y la del producto donde el primer semestre mueve calificaciones a un grado sin ninguna al inicio del segundo. La tabla da la distancia de cada año. ${d4.es}.`,
      },
      credit(o, true),
    );
    pdBody = pdTable;
  } else if (built.case === 'zero') {
    // no defined PD of the grade a log axis can draw: every one is 0 (no rating of the grade reached the default column
    // in any year), or below LOG_FLOOR
    pdNote = join(
      built.tiny
        ? {
            en: `No ${g} PD reaches 1E-20 in any year, in the semesters' product or in the year's matrix: the log axis would not draw them, so the table gives them. ${d4.en}.`,
            es: `Ninguna PD de ${g} llega a 1E-20 en ningún año, en el producto de los semestres ni en la matriz del año: el eje logarítmico no las dibujaría, así que la tabla las da. ${d4.es}.`,
          }
        : {
            en: `No ${g} rating reached the default column in any year, in the semesters' product or in the year's matrix: a log axis has no place for a PD of 0, so the table gives them. ${d4.en}.`,
            es: `Ninguna calificación ${g} llegó a la columna de incumplimiento en ningún año, en el producto de los semestres ni en la matriz del año: un eje logarítmico no tiene lugar para una PD de 0, así que la tabla las da. ${d4.es}.`,
          },
      empty,
      credit(o, true),
    );
    pdBody = pdTable;
  } else {
    // where the product's PD is mostly above the year's, one reason the two constructions give for it, stated as a
    // possibility: the second semester's new ratings move the product too (the distance's note)
    const why = built.above > built.below;
    pdNote = join(
      {
        en: `The one-year PD in the default column of the semesters' product and of the year's matrix, ${d4.en}; percent, log scale.`,
        es: `La PD a un año en la columna de incumplimiento del producto de los semestres y de la matriz del año, ${d4.es}; porcentaje, escala logarítmica.`,
      },
      built.pairs
        ? {
            en: `The product's is above the year's in ${built.above} and below it in ${built.below} of the ${built.pairs} years with a default in either${why ? "; one possible reason: the chain keeps a default absorbing, while the year's matrix counts only the ratings still in default at its end" : ''}.`,
            es: `La del producto está sobre la del año en ${built.above} y bajo ella en ${built.below} de los ${built.pairs} años con un incumplimiento en alguna${why ? '; una razón posible: la cadena mantiene absorbente el incumplimiento, mientras la matriz del año cuenta solo las calificaciones que siguen incumplidas a su término' : ''}.`,
          }
        : NONE,
      zeros,
      tiny,
      empty,
      credit(o),
    );
    pdBody = (
      <UPlotChart
        height="fill"
        x={{ values: built.pd.x, label: built.pd.axis, format: YEAR_FORMAT }}
        y={{ label: { en: `PD of ${g} (%, log scale)`, es: `PD de ${g} (%, escala log.)` }, log: true, format: { percent: true, digits: 2 } }}
        series={built.pd.series}
      />
    );
  }
  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col">
        <PlotCard
          fill
          title={{ en: 'Two semesters against their year', es: 'Dos semestres contra su año' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={built.l1.drawn ? l1Note : join({ en: 'No year has a distance to draw: the table gives what the artifact holds.', es: 'Ningún año tiene una distancia que dibujar: la tabla da lo que contiene el artefacto.' }, credit(o))}
        >
          {built.l1.drawn ? (
            <UPlotChart
              height="fill"
              x={{ values: built.l1.x, label: built.l1.axis, format: YEAR_FORMAT }}
              y={{ label: { en: 'L1 distance (sum over the cells)', es: 'Distancia L1 (suma sobre las celdas)' }, format: { decimals: 2 } }}
              series={built.l1.series}
              marks={built.l1.marks}
            />
          ) : (
            <SeriesTable x={built.l1.x} columns={built.l1.all} show={shows(FMT.l1)} name="semesters-l1" />
          )}
        </PlotCard>
      </div>
      <div className="ct-col">
        <PlotCard fill title={pdTitle} lane={REPLAY} provenance={prov} dataKey={stateKey} note={pdNote}>
          {pdBody}
        </PlotCard>
      </div>
    </div>
  );
}
