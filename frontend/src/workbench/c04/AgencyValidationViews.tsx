// C04's agency variants, the Validation group's PD views (web.md "Agency variants"; CT-403, CT-407, CT-415): the
// long-run average PD by grade under each of CEREP's default definitions with its intervals (PD by grade), the chosen
// grade's one-year PD cohort by cohort under each definition (By year), how far the definitions sit apart and the
// cohorts behind the gap (Definitions), and each five-year window as its cohort lived it against the chained one-year
// matrices (Lifetime). A tall screen draws under the two short tables what a short one has no room for: the rail's
// definition's three intervals by grade (PD by grade) and the withdrawn shares lived and chained (Lifetime), so a short
// table never sits alone in a tall card (ADR-0071 rule 8, the gate's stage fill). Every number is the pipeline's, read
// from the agency's artifact: these views select, average and format. Two exceptions, both for Keep, whose long-run
// average block the bake leaves out (LRA_KEYS is d2, d3, d4): its average is the mean of its yearly rates, the
// arithmetic the pipeline applies to the others (the tests reproduce the baked averages with it), and its intervals are
// the live ports of engine/transitions.ts, held to riskvalidation by the parity points. A card that shows only Keep's
// numbers declares the live lane; a card that shows them beside the artifact's says which are computed in the browser.
import { PlotCard, ViewsRow, formatNumber, pick, useShellLang, useStageSize, useWorkbenchState, type BiText, type ShellColorToken } from '@fasl-work/caos-app-shell';
import { UPlotChart, type ChartSeries } from '@fasl-work/caos-app-shell/chart';
import { useCallback, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { pdAgrestiCoull, pdJeffreys, pdWald } from '../../engine/transitions';
import type { C04AgencyOutputs, C04Bounds, C04Cohort, C04Lifetime, C04Lra, VariantArtifact } from '../../lib/contract.types';
import { REPLAY, provenanceOf } from '../model';
import { Pending } from '../Pending';
import {
  DEFINITIONS,
  DEFINITION_COLOR,
  DEFINITION_HINT,
  DEFINITION_LABEL,
  ESMA_DEFINITIONS,
  GRADES,
  GRADE_AXIS,
  N_GRADES,
  definitionsOf,
  gradeCounts,
  isAgency,
  type AgencyVariant,
  type C04Sel,
  type Definition,
  cerepPdSource,
  cerepSource,
} from './selection';

type Lang = 'en' | 'es';
type Grid = (number | null)[][];

const LIVE = 'live' as const;
/** The level of every interval these views print: the bake's (c04_agency.LEVEL). */
const LEVEL = 0.95;
/** Paragraph 86's comparison: the most recent five cohorts. */
const RECENT = 5;

const t = (l: Lang, en: string, es: string): string => (l === 'en' ? en : es);
/** A text built once per language. */
const bi = (f: (l: Lang) => string): BiText => ({ en: f('en'), es: f('es') });
/** A finite number, or null: the artifact writes null where a value is undefined (a grade without ratings). */
const num = (x: unknown): number | null => (typeof x === 'number' && Number.isFinite(x) ? x : null);
const sum = (a: readonly number[]): number => a.reduce((s, x) => s + x, 0);

/** A share in percent without its sign (the column header carries it), three significant digits; "-" where undefined. */
const pc = (l: Lang, x: unknown): string => {
  const v = num(x);
  return v === null ? '-' : formatNumber(v * 100, l, { digits: 3 });
};
/** A share in percent with its sign, for prose. */
const pcs = (l: Lang, x: unknown): string => {
  const v = num(x);
  return v === null ? '-' : formatNumber(v, l, { percent: true, digits: 3 });
};
/** A count, every digit. */
const count = (l: Lang, x: unknown): string => {
  const v = num(x);
  return v === null ? '-' : formatNumber(v, l, { decimals: 0 });
};
/** An interval in percent: [lower, upper] in English, [lower; upper] in Spanish (its decimal comma). */
const span = (l: Lang, lower: number | null, upper: number | null): string =>
  lower === null || upper === null ? '-' : l === 'en' ? `[${pc(l, lower)}, ${pc(l, upper)}]` : `[${pc(l, lower)}; ${pc(l, upper)}]`;
/** A list in prose: "a, b and c" / "a, b y c". */
const list = (l: Lang, items: string[]): string =>
  items.length <= 1 ? (items[0] ?? '') : `${items.slice(0, -1).join(', ')} ${t(l, 'and', 'y')} ${items[items.length - 1]}`;
const capital = (s: string): string => s.charAt(0).toUpperCase() + s.slice(1);
/** Years as runs, each with its preposition: "from 2006 to 2014", "in 2003 and from 2006 to 2008" (Spanish "de 2006 a
 * 2014", "en 2003 y de 2006 a 2008"). */
export function inYears(l: Lang, years: number[]): string {
  const sorted = [...years].sort((a, b) => a - b);
  const runs: Array<[number, number]> = [];
  for (const y of sorted) {
    const last = runs[runs.length - 1];
    if (last && y === last[1] + 1) last[1] = y;
    else runs.push([y, y]);
  }
  return list(
    l,
    runs.map(([a, b]) => (a === b ? t(l, `in ${a}`, `en ${a}`) : t(l, `from ${a} to ${b}`, `de ${a} a ${b}`))),
  );
}

/** The short code a key or a sentence names a definition by. */
const CODE: Record<Definition, BiText> = { d2: 'D2', d3: 'D3', d4: 'D4', keep: { en: 'Keep', es: 'Con retiros' } };

function agencyOf(sel: C04Sel | null): AgencyVariant | null {
  const v = sel?.data.variant as VariantArtifact<unknown> | undefined;
  return v && isAgency(v) ? v : null;
}

/** The agency's chip name in the rail (S&P, Moody's, Fitch), its code where the manifest has none. */
function agencyName(sel: C04Sel, v: AgencyVariant): BiText {
  return sel.data.manifest.artifacts.find((a) => a.variant_id === v.variant_id)?.short_title ?? v.outputs.agency.code;
}

const yearOf = (c: C04Cohort): number => Number(c.begin.slice(0, 4));

/** The agency's EU entity, its scope and period, and CEREP's attribution (selection.cerepSource, CT-407). */
export const sourceText = (o: C04AgencyOutputs, l: Lang): string => cerepSource(o, l);
/** ESMA's statement, then the source: the close of a card that shows a PD or sets definitions side by side. */
const pdSource = (o: C04AgencyOutputs, l: Lang): string => ` ${cerepPdSource(o, l)}`;

/** One definition's yearly rates, cohorts (oldest first) by grades, as the artifact holds them; null where undefined. */
function yearly(o: C04AgencyOutputs, d: Definition): Grid | null {
  const grid = o.pd[d];
  return grid ? grid.map((row) => row.map(num)) : null;
}

/** The long-run average of one grade's yearly rates (EBA/GL/2017/16 paragraph 84) over the cohorts where the rate is
 * defined, how many entered it, and the mean of the last five of them (paragraph 86): c04_agency._lra's arithmetic. */
export function averageOfYears(rates: readonly (readonly (number | null)[])[], g: number): { rate: number | null; cohorts: number; last5: number | null } {
  const s = rates.map((row) => num(row[g])).filter((x): x is number => x !== null);
  if (s.length === 0) return { rate: null, cohorts: 0, last5: null };
  const mean = (a: number[]) => sum(a) / a.length;
  return { rate: mean(s), cohorts: s.length, last5: mean(s.slice(-RECENT)) };
}

/** The baked long-run average block of a definition: D2, D3 and D4 (null on Moody's); Keep has none. */
function baked(o: C04AgencyOutputs, d: Definition): C04Lra | null {
  return d === 'keep' ? null : (o.lra[d] ?? null);
}

/** The rail's definition where the agency's pages give it, else D2 (Moody's has no D4 or Keep). */
function definitionFor(o: C04AgencyOutputs, d: Definition | undefined): Definition {
  return d && definitionsOf(o).includes(d) ? d : 'd2';
}

// ---------------------------------------------------------------------------------------------------------------------
// Layout helpers: the columns a table's card holds, and the room an axis gives a mark's label

/**
 * How many of a table's optional columns its scroll box holds without scrolling sideways, the columns ranked in the
 * order a narrow card gives them up (the last first). Every one at first, and on the server; in the browser, one fewer
 * while the table is wider than its box, measured again from every column whenever the box's width or the table's
 * content changes. The card decides, not the viewport: at 1600 x 900 a card of two fifths of the row is 473 px wide,
 * at 2560 x 1440 it is 843 px. The box's own width never depends on the table (it scrolls), so the count only falls
 * for a given width and content, and settles.
 */
export function useFitColumns(optional: number, content: string): { ref: (el: HTMLDivElement | null) => void; shown: number } {
  const [measure, size] = useStageSize();
  const box = useRef<HTMLDivElement | null>(null);
  const key = `${content}|${size.width}`;
  const [fit, setFit] = useState<{ key: string; shown: number }>({ key: '', shown: optional });
  const shown = fit.key === key ? Math.min(fit.shown, optional) : optional;
  useLayoutEffect(() => {
    const el = box.current;
    if (!el || size.width === 0) return;
    if (el.scrollWidth > el.clientWidth + 1 && shown > 0) setFit({ key, shown: shown - 1 });
    else if (fit.key !== key) setFit({ key, shown });
  });
  const ref = useCallback(
    (el: HTMLDivElement | null) => {
      box.current = el;
      measure(el);
    },
    [measure],
  );
  return { ref, shown };
}

/**
 * A chart's x values over categories. The shell (0.8 and later) draws a mark's label inside the plot on the side of its
 * line where it fits, so no axis needs room for one, and every x is a category the hover read-out can name. `pad` is the
 * identity, kept so the views place series the same way.
 */
export function axisFor(xs: readonly number[], _marks: ReadonlyArray<{ x: number; label: BiText }>): { x: number[]; pad: (values: (number | null)[]) => (number | null)[] } {
  return { x: [...xs], pad: (values) => [...values] };
}

/** The grades on an axis: AAA to CCC-C as 1 to 7. */
const GRADE_POSITIONS = GRADES.map((_, g) => g + 1);

// ---------------------------------------------------------------------------------------------------------------------
// PD by grade: the long-run average under every definition, its intervals, the last five cohorts

export interface Bounds {
  lower: number | null;
  upper: number | null;
}
export interface PdRow {
  grade: number;
  /** the long-run average: the mean of the yearly rates over the cohorts where the grade has ratings */
  rate: number | null;
  cohorts: number;
  /** the pooled counts the intervals rest on */
  defaults: number | null;
  n: number | null;
  pooled: number | null;
  wald: Bounds;
  agrestiCoull: Bounds;
  jeffreys: Bounds;
  last5: number | null;
}

const NONE: Bounds = { lower: null, upper: null };
const boundsAt = (b: C04Bounds, g: number): Bounds => ({ lower: num(b.lower[g]), upper: num(b.upper[g]) });

/** Wald, Agresti-Coull and Jeffreys at 95% on pooled counts, from the live ports; null where the port refuses them. */
function liveIntervals(defaults: number, n: number): { wald: Bounds; agrestiCoull: Bounds; jeffreys: Bounds } | null {
  try {
    const w = pdWald(defaults, n, { level: LEVEL });
    const a = pdAgrestiCoull(defaults, n, { level: LEVEL });
    const j = pdJeffreys(defaults, n, { level: LEVEL });
    return { wald: { lower: w.lower, upper: w.upper }, agrestiCoull: { lower: a.lower, upper: a.upper }, jeffreys: { lower: j.lower, upper: j.upper } };
  } catch {
    return null;
  }
}

/** A definition's long-run average block by grade: the artifact's for D2, D3 and D4 (replay); for Keep, which the bake
 * leaves out, the mean of its yearly rates, its pooled counts (the transition page's defaults over the whole cohorts,
 * gradeCounts) and the three intervals from the live ports (live). */
export function pdTable(v: AgencyVariant, d: Definition): { rows: PdRow[]; live: boolean } {
  const o = v.outputs;
  const l = baked(o, d);
  if (l) {
    return {
      live: false,
      rows: GRADES.map((_, g) => ({
        grade: g,
        rate: num(l.rate[g]),
        cohorts: l.cohorts[g] ?? 0,
        defaults: num(l.defaults[g]),
        n: num(l.n[g]),
        pooled: num(l.pooled_rate[g]),
        wald: boundsAt(l.wald, g),
        agrestiCoull: boundsAt(l.agresti_coull, g),
        jeffreys: boundsAt(l.jeffreys, g),
        last5: num(l.last5[g]),
      })),
    };
  }
  const rates = d === 'keep' ? yearly(o, 'keep') : null;
  if (!rates) return { rows: [], live: false };
  return {
    live: true,
    rows: GRADES.map((_, g) => {
      const avg = averageOfYears(rates, g);
      const c = gradeCounts(v, 'keep', g);
      const iv = c ? liveIntervals(c.defaults, c.n) : null;
      return {
        grade: g,
        rate: avg.rate,
        cohorts: avg.cohorts,
        defaults: c ? c.defaults : null,
        n: c ? c.n : null,
        pooled: c ? c.defaults / c.n : null,
        wald: iv?.wald ?? NONE,
        agrestiCoull: iv?.agrestiCoull ?? NONE,
        jeffreys: iv?.jeffreys ?? NONE,
        last5: avg.last5,
      };
    }),
  };
}

/** The grades whose long-run average (the mean of the yearly rates) lies outside the Jeffreys interval of the pooled
 * rate: the interval bounds defaults over n, not the average. */
export function outsideRows(rows: PdRow[]): PdRow[] {
  return rows.filter((r) => r.rate !== null && r.jeffreys.lower !== null && r.jeffreys.upper !== null && (r.rate < r.jeffreys.lower || r.rate > r.jeffreys.upper));
}

export interface PdChart {
  series: ChartSeries[];
  /** the grades whose long-run average is 0 under some definition (a log axis has no 0), with those definitions */
  zeroRates: Array<{ grade: number; defs: Definition[] }>;
  zeroLast5: number;
  zeroLower: number;
}

/** The PD by grade chart: under every definition of the agency, the long-run average (solid, the rail's definition
 * thicker); for the rail's definition only, what its intervals belong to: the pooled rate (points, defaults over n) inside
 * its Jeffreys 95% bounds (dashed), and the mean of the last five cohorts (rings, paragraph 86). The intervals bound the
 * pooled rate, not the average of the yearly rates, so they are drawn with the rate they bound. A value of 0 has no place
 * on the log axis: it is counted for the note and left out; a series with nothing left is not drawn. */
export function pdByGradeChart(v: AgencyVariant, chosen: Definition): PdChart {
  const o = v.outputs;
  const series: ChartSeries[] = [];
  const zero = new Map<number, Definition[]>();
  let zeroLast5 = 0;
  let zeroLower = 0;
  const positive = (x: number | null) => (x !== null && x > 0 ? x : null);
  for (const d of definitionsOf(o)) {
    const l = baked(o, d);
    const rates = l ? null : yearly(o, d);
    const avg = rates ? GRADES.map((_, g) => averageOfYears(rates, g)) : null;
    const rate = l ? l.rate.map(num) : (avg ?? []).map((a) => a.rate);
    rate.forEach((x, g) => {
      if (x === 0) zero.set(g, [...(zero.get(g) ?? []), d]);
    });
    series.push({ label: DEFINITION_LABEL[d], values: rate.map(positive), color: DEFINITION_COLOR[d], width: d === chosen ? 2.8 : 1.6 });
  }
  const rows = pdTable(v, chosen).rows;
  if (rows.length) {
    const color = DEFINITION_COLOR[chosen];
    const code = (lg: Lang) => pick(CODE[chosen], lg);
    const lower = rows.map((r) => r.jeffreys.lower);
    const last5 = rows.map((r) => r.last5);
    zeroLower = lower.filter((x) => x === 0).length;
    zeroLast5 = last5.filter((x) => x === 0).length;
    series.push(
      { label: bi((lg) => `${code(lg)}: ${t(lg, 'pooled rate, defaults / n', 'tasa agrupada, incumplimientos / n')}`), values: rows.map((r) => positive(r.pooled)), color, mode: 'points' },
      { label: bi((lg) => `${code(lg)}: ${t(lg, 'Jeffreys 95% of the pooled rate, upper', 'Jeffreys 95% de la tasa agrupada, superior')}`), values: rows.map((r) => positive(r.jeffreys.upper)), color, width: 1.2, dash: [5, 4] },
      { label: bi((lg) => `${code(lg)}: ${t(lg, 'Jeffreys 95% of the pooled rate, lower', 'Jeffreys 95% de la tasa agrupada, inferior')}`), values: lower.map(positive), color, width: 1.2, dash: [5, 4] },
      { label: bi((lg) => `${code(lg)}: ${t(lg, 'last five cohorts', 'últimas cinco cohortes')}`), values: last5.map(positive), color: '--color-fg-subtle', mode: 'points' },
    );
  }
  return {
    series: series.filter((s) => s.values.some((x) => x !== null)),
    zeroRates: [...zero.entries()].sort((a, b) => a[0] - b[0]).map(([grade, defs]) => ({ grade, defs })),
    zeroLast5,
    zeroLower,
  };
}

/** The three intervals in the colours and strokes the Impact group's Intervals view draws them with (LiveViews). */
const METHODS: Array<{ key: 'wald' | 'agrestiCoull' | 'jeffreys'; name: string; color: ShellColorToken }> = [
  { key: 'wald', name: 'Wald', color: '--color-warn' },
  { key: 'agrestiCoull', name: 'Agresti-Coull', color: '--color-magenta' },
  { key: 'jeffreys', name: 'Jeffreys', color: '--color-accent' },
];

export interface IntervalsChart {
  series: ChartSeries[];
  /** the values of 0 among the drawn quantities (a log axis has no 0), and the grades that hold them */
  zeros: number;
  zeroGrades: number[];
}

/** The rail's definition by grade on a log axis: the pooled rate (points, defaults over n) inside its three 95%
 * intervals, upper bound solid and lower dashed, and the long-run average of the yearly rates as a line, which the
 * intervals do not bound. A value of 0 is counted for the note and left out. */
export function intervalsChart(rows: PdRow[]): IntervalsChart {
  const raw: ChartSeries[] = [
    { label: { en: 'Long-run average', es: 'Promedio de largo plazo' }, values: rows.map((r) => r.rate), color: '--color-good', width: 2 },
    { label: { en: 'Pooled, defaults / n', es: 'Agrupada, incumplimientos / n' }, values: rows.map((r) => r.pooled), color: '--color-fg', mode: 'points' },
    ...METHODS.flatMap((m): ChartSeries[] => [
      { label: { en: `${m.name} 95%, upper`, es: `${m.name} 95%, superior` }, values: rows.map((r) => r[m.key].upper), color: m.color, width: 2 },
      { label: { en: `${m.name} 95%, lower`, es: `${m.name} 95%, inferior` }, values: rows.map((r) => r[m.key].lower), color: m.color, width: 1.4, dash: [5, 4] },
    ]),
  ];
  const zeroGrades = new Set<number>();
  let zeros = 0;
  for (const s of raw) {
    s.values.forEach((x, i) => {
      if (x === 0) {
        zeros += 1;
        zeroGrades.add(rows[i].grade);
      }
    });
  }
  const series = raw
    .map((s) => ({ ...s, values: s.values.map((x) => (x !== null && x > 0 ? x : null)) }))
    .filter((s) => s.values.some((x) => x !== null));
  return { series, zeros, zeroGrades: [...zeroGrades].sort((a, b) => a - b) };
}

/** The PD table's optional columns, in the order a narrow card gives them up (the last first): the other two
 * intervals, the pooled rate, the cohorts, the last five cohorts' mean. Grade, the average, the pooled counts and the
 * Jeffreys interval are always shown. */
const PD_OPTIONAL = ['wald', 'agresti-coull', 'pooled', 'cohorts', 'last5'] as const;
type PdOptional = (typeof PD_OPTIONAL)[number];

/** The rows of the PD by grade table. */
function PdRows({ rows, sel, show }: { rows: PdRow[]; sel: C04Sel; show: (c: PdOptional) => boolean }) {
  const lang = useShellLang();
  return (
    <>
      {rows.map((r) => (
        <tr key={r.grade} data-grade={GRADES[r.grade]} className={r.grade === sel.grade ? 'ct-current' : undefined}>
          <td>
            <button type="button" className="ct-linkbutton" aria-pressed={r.grade === sel.grade} onClick={() => sel.act.setGrade(r.grade)}>
              {GRADES[r.grade]}
            </button>
          </td>
          <td data-col="rate">{pc(lang, r.rate)}</td>
          <td data-col="counts">{r.defaults === null || r.n === null ? '-' : `${count(lang, r.defaults)} / ${count(lang, r.n)}`}</td>
          {show('pooled') && (
            <td data-col="pooled" className="ct-wide-only">
              {pc(lang, r.pooled)}
            </td>
          )}
          <td data-col="jeffreys">{span(lang, r.jeffreys.lower, r.jeffreys.upper)}</td>
          {show('wald') && (
            <td data-col="wald" className="ct-wide-only">
              {span(lang, r.wald.lower, r.wald.upper)}
            </td>
          )}
          {show('agresti-coull') && (
            <td data-col="agresti-coull" className="ct-wide-only">
              {span(lang, r.agrestiCoull.lower, r.agrestiCoull.upper)}
            </td>
          )}
          {show('cohorts') && (
            <td data-col="cohorts" className="ct-wide-only">
              {count(lang, r.cohorts)}
            </td>
          )}
          {show('last5') && (
            <td data-col="last5" className="ct-wide-only">
              {pc(lang, r.last5)}
            </td>
          )}
        </tr>
      ))}
    </>
  );
}

function PdTableHead({ show }: { show: (c: PdOptional) => boolean }) {
  const lang = useShellLang();
  return (
    <thead>
      <tr>
        <th className="ct-text">{pick({ en: 'Grade', es: 'Grado' }, lang)}</th>
        <th>{pick({ en: 'Average, %', es: 'Promedio, %' }, lang)}</th>
        <th>{pick({ en: 'Defaults / n', es: 'Incumpl. / n' }, lang)}</th>
        {show('pooled') && <th className="ct-wide-only">{pick({ en: 'Pooled, %', es: 'Agrupada, %' }, lang)}</th>}
        <th>{pick({ en: 'Jeffreys 95%, %', es: 'Jeffreys 95%, %' }, lang)}</th>
        {show('wald') && <th className="ct-wide-only">{pick({ en: 'Wald 95%, %', es: 'Wald 95%, %' }, lang)}</th>}
        {show('agresti-coull') && <th className="ct-wide-only">{pick({ en: 'Agresti-Coull 95%, %', es: 'Agresti-Coull 95%, %' }, lang)}</th>}
        {show('cohorts') && <th className="ct-wide-only">{pick({ en: 'Cohorts', es: 'Cohortes' }, lang)}</th>}
        {show('last5') && <th className="ct-wide-only">{pick({ en: 'Last five, %', es: 'Últimas cinco, %' }, lang)}</th>}
      </tr>
    </thead>
  );
}

/** The long-run average by grade under every definition of the agency, on a log axis, with the Jeffreys interval of
 * the pooled counts and the last five cohorts' mean; beside it, the rail's definition grade by grade with its three
 * intervals, and on a tall screen the same three drawn by grade (EBA/GL/2017/16 paragraphs 84 and 86; Schuermann and
 * Hanson 2004). */
export function PdByGradeView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = agencyOf(sel);
  const d = v ? definitionFor(v.outputs, sel?.definition) : 'd2';
  const chart = useMemo(() => (v ? pdByGradeChart(v, d) : null), [v, d]);
  const table = useMemo(() => (v ? pdTable(v, d) : null), [v, d]);
  const intervals = useMemo(() => (table ? intervalsChart(table.rows) : null), [table]);
  const fit = useFitColumns(PD_OPTIONAL.length, `${lang}|${v?.variant_id ?? ''}|${d}`);
  if (!sel) return <Pending />;
  if (!v || !chart || !table || !intervals) return <NotAgency sel={sel} />;
  const o = v.outputs;
  const prov = provenanceOf(v.provenance.truth_status);
  const name = agencyName(sel, v);
  const defs = definitionsOf(o);
  const hasKeep = defs.includes('keep');
  const show = (c: PdOptional) => PD_OPTIONAL.indexOf(c) < fit.shown;
  const cohortCounts = [...new Set(table.rows.map((r) => r.cohorts))];
  const outside = outsideRows(table.rows);
  const gradeAxis = axisFor(GRADE_POSITIONS, [{ x: sel.grade + 1, label: GRADES[sel.grade] }]);
  const zeros = (l: Lang): string => {
    // the grades whose average is 0, grouped by the definitions under which it is: "AAA, AA and A under D4 and Keep"
    const groups = new Map<string, { grades: string[]; defs: Definition[] }>();
    for (const z of chart.zeroRates) {
      const key = z.defs.join(',');
      const grp = groups.get(key) ?? { grades: [], defs: z.defs };
      grp.grades.push(GRADES[z.grade]);
      groups.set(key, grp);
    }
    const parts: string[] = [];
    for (const grp of groups.values()) {
      const defsText = list(l, grp.defs.map((x) => pick(CODE[x], l)));
      parts.push(t(l, `the long-run average of ${list(l, grp.grades)} under ${defsText}`, `el promedio de largo plazo de ${list(l, grp.grades)} bajo ${defsText}`));
    }
    if (chart.zeroLast5) parts.push(t(l, `${chart.zeroLast5} means of the last five cohorts`, `${chart.zeroLast5} medias de las últimas cinco cohortes`));
    if (chart.zeroLower) parts.push(t(l, `${chart.zeroLower} lower bounds of a grade without a default`, `${chart.zeroLower} cotas inferiores de un grado sin incumplimientos`));
    return parts.length
      ? t(l, ` A 0 cannot sit on a log axis and is left out (the table prints it): ${list(l, parts)}.`, ` Un 0 no cabe en un eje logarítmico y se omite (la tabla lo imprime): ${list(l, parts)}.`)
      : '';
  };
  const chartNote = bi(
    (l) =>
      t(
        l,
        `Log scale, shares of the cohort. Lines: the long-run average under each definition (EBA/GL/2017/16 paragraph 84, the mean of the yearly rates over the cohorts where the grade has ratings), the rail's (${pick(CODE[d], l)}) thicker. For ${pick(CODE[d], l)} only: its pooled rate (points, defaults over n) inside its Jeffreys 95% interval (dashed), which bounds the pooled rate and not the average, and the mean of its last five cohorts (grey points, paragraph 86). Marked: the rail's grade.${hasKeep ? " Keep's average and its last five cohorts' mean, which the artifact does not bake, are the means of its yearly rates, computed in your browser, and so are its pooled counts and interval." : ''}`,
        `Escala logarítmica, fracciones de la cohorte. Líneas: el promedio de largo plazo bajo cada definición (EBA/GL/2017/16 párrafo 84, la media de las tasas anuales sobre las cohortes donde el grado tiene calificaciones), la del panel (${pick(CODE[d], l)}) más gruesa. Solo para ${pick(CODE[d], l)}: su tasa agrupada (puntos, incumplimientos sobre n) dentro de su intervalo de Jeffreys al 95% (segmentado), que acota la tasa agrupada y no el promedio, y la media de sus últimas cinco cohortes (puntos grises, párrafo 86). Marcado: el grado del panel.${hasKeep ? ' El promedio de Con retiros y la media de sus últimas cinco cohortes, que el artefacto no trae, son medias de sus tasas anuales calculadas en su navegador, y también lo son sus conteos agrupados y su intervalo.' : ''}`,
      ) +
      zeros(l) +
      pdSource(o, l),
  );
  const outsideText = (l: Lang): string =>
    outside.length
      ? t(
          l,
          ` The intervals bound the pooled rate (defaults over n), not the average of the yearly rates: ${list(l, outside.map((r) => `${GRADES[r.grade]}'s average, ${pcs(l, r.rate)}, lies outside ${span(l, r.jeffreys.lower, r.jeffreys.upper)}\u00a0%`))}.`,
          ` Los intervalos acotan la tasa agrupada (incumplimientos sobre n), no el promedio de las tasas anuales: ${list(l, outside.map((r) => `el promedio de ${GRADES[r.grade]}, ${pcs(l, r.rate)}, queda fuera de ${span(l, r.jeffreys.lower, r.jeffreys.upper)}\u00a0%`))}.`,
        )
      : t(l, ' Every average lies inside the Jeffreys interval of its pooled rate.', ' Cada promedio queda dentro del intervalo de Jeffreys de su tasa agrupada.');
  const keepText = (l: Lang): string =>
    table.live
      ? t(
          l,
          " Keep has no long-run average block in the artifact (the bake has D2, D3 and D4): its average is the mean of its yearly rates, its pooled counts are the transition page's defaults over the whole cohorts, and its intervals are computed in your browser by the ports held to riskvalidation.",
          ' Con retiros no tiene bloque de promedio de largo plazo en el artefacto (el horneado trae D2, D3 y D4): su promedio es la media de sus tasas anuales, sus conteos agrupados son los incumplimientos de la página de transiciones sobre las cohortes completas, y sus intervalos se calculan en su navegador con los puertos contrastados con riskvalidation.',
        )
      : '';
  const tableNote = bi((l) => {
    const cohorts =
      cohortCounts.length === 1
        ? t(l, `each grade's average is over ${cohortCounts[0]} cohorts`, `el promedio de cada grado es sobre ${cohortCounts[0]} cohortes`)
        : t(l, 'each grade over the cohorts where it has ratings', 'cada grado sobre las cohortes donde tiene calificaciones');
    const fallback =
      sel.definition !== d
        ? t(l, ` The transition page of ${pick(name, l)} has no default category, so ${pick(CODE[sel.definition], l)} does not exist for it: the table shows D2.`, ` La página de transiciones de ${pick(name, l)} no tiene categoría de incumplimiento, así que ${pick(CODE[sel.definition], l)} no existe para ella: la tabla muestra D2.`)
        : '';
    return (
      t(
        l,
        `In percent of the cohort (${cohorts}): the long-run average, the pooled defaults over n and the Jeffreys 95% interval of the pooled rate (Schuermann and Hanson 2004); more columns where the card has room. A grade's name picks it; the Definitions view says what each definition counts.`,
        `En porcentaje de la cohorte (${cohorts}): el promedio de largo plazo, los incumplimientos agrupados sobre n y el intervalo de Jeffreys al 95% de la tasa agrupada (Schuermann y Hanson 2004); más columnas donde la tarjeta tiene espacio. El nombre de un grado lo elige; la vista Definiciones dice qué cuenta cada definición.`,
      ) +
      outsideText(l) +
      fallback +
      keepText(l) +
      pdSource(o, l)
    );
  });
  const intervalsNote = bi((l) => {
    const zeroText = intervals.zeros
      ? t(
          l,
          ` A 0 cannot sit on the log axis and is left out (the table prints it): ${intervals.zeros} values, in ${list(l, intervals.zeroGrades.map((g) => GRADES[g]))}.`,
          ` Un 0 no cabe en el eje logarítmico y se omite (la tabla lo imprime): ${intervals.zeros} valores, en ${list(l, intervals.zeroGrades.map((g) => GRADES[g]))}.`,
        )
      : '';
    return (
      t(
        l,
        `${pick(DEFINITION_LABEL[d], l)} by grade, in shares of the pooled cohort on a log scale: the pooled rate (points, defaults over n) inside its three 95% intervals (Schuermann and Hanson 2004), Wald, Agresti-Coull and Jeffreys, upper bound solid and lower dashed; the line is the long-run average of the yearly rates, which the intervals do not bound. Marked: the rail's grade.`,
        `${pick(DEFINITION_LABEL[d], l)} por grado, en fracciones de la cohorte agrupada en escala logarítmica: la tasa agrupada (puntos, incumplimientos sobre n) dentro de sus tres intervalos al 95% (Schuermann y Hanson 2004), Wald, Agresti-Coull y Jeffreys, cota superior continua e inferior segmentada; la línea es el promedio de largo plazo de las tasas anuales, que los intervalos no acotan. Marcado: el grado del panel.`,
      ) +
      zeroText +
      outsideText(l) +
      keepText(l) +
      pdSource(o, l)
    );
  });
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={bi((l) => t(l, `${pick(name, l)}: long-run average PD by grade, every definition`, `${pick(name, l)}: PD promedio de largo plazo por grado, cada definición`))}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={chartNote}
      >
        {chart.series.length ? (
          <UPlotChart
            height="fill"
            x={{ values: gradeAxis.x, label: GRADE_AXIS, format: { decimals: 0 } }}
            y={{ label: { en: 'One-year PD (log scale)', es: 'PD anual (escala log.)' }, log: true, format: { percent: true, digits: 2 } }}
            series={chart.series.map((s) => ({ ...s, values: gradeAxis.pad(s.values) }))}
            marks={[{ x: sel.grade + 1, label: GRADES[sel.grade] }]}
          />
        ) : (
          <p className="ct-note">{pick({ en: 'Every long-run average is 0 or undefined: nothing can sit on a log axis; the table beside prints them.', es: 'Todo promedio de largo plazo es 0 o indefinido: nada cabe en un eje logarítmico; la tabla al lado los imprime.' }, lang)}</p>
        )}
      </PlotCard>
      <>
        <PlotCard
          fill
          title={bi((l) => t(l, `${pick(DEFINITION_LABEL[d], l)}, by grade`, `${pick(DEFINITION_LABEL[d], l)}, por grado`))}
          lane={table.live ? LIVE : REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={tableNote}
        >
          <div className="ct-scroll" ref={fit.ref}>
            <table className="caos-table ct-wrap-head" data-table="lra" data-definition={d}>
              <PdTableHead show={show} />
              <tbody>
                <PdRows rows={table.rows} sel={sel} show={show} />
              </tbody>
            </table>
          </div>
        </PlotCard>
        <div className="ct-tall-only">
          <PlotCard
            fill
            title={bi((l) => t(l, `${pick(DEFINITION_LABEL[d], l)}: the three 95% intervals by grade`, `${pick(DEFINITION_LABEL[d], l)}: los tres intervalos al 95% por grado`))}
            lane={table.live ? LIVE : REPLAY}
            provenance={prov}
            dataKey={stateKey}
            note={intervalsNote}
          >
            {intervals.series.length ? (
              <UPlotChart
                height="fill"
                x={{ values: gradeAxis.x, label: GRADE_AXIS, format: { decimals: 0 } }}
                y={{ label: { en: 'Pooled PD and its bounds (log scale)', es: 'PD agrupada y sus cotas (escala log.)' }, log: true, format: { percent: true, digits: 2 } }}
                series={intervals.series.map((s) => ({ ...s, values: gradeAxis.pad(s.values) }))}
                marks={[{ x: sel.grade + 1, label: GRADES[sel.grade] }]}
              />
            ) : (
              <p className="ct-note">{pick({ en: 'No pooled rate or bound of this definition is above 0: nothing can sit on a log axis; the table above prints them.', es: 'Ninguna tasa agrupada ni cota de esta definición es mayor que 0: nada cabe en un eje logarítmico; la tabla de arriba las imprime.' }, lang)}</p>
            )}
          </PlotCard>
        </div>
      </>
    </ViewsRow>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// By year: the chosen grade's one-year PD cohort by cohort under every definition

export interface ByYear {
  years: number[];
  /** what the x axis subtracts from a year: 0, x is the calendar year (written without a group separator) */
  base: number;
  x: number[];
  defs: Definition[];
  /** each definition's rate of the grade by cohort (null where undefined) */
  values: Partial<Record<Definition, (number | null)[]>>;
  series: ChartSeries[];
  /** the cohorts (indices) where the definitions differ most, oldest first */
  widest: number[];
  spreads: Array<{ spread: number; hi: Definition | null; lo: Definition | null }>;
  /** the marked years on the chart: a run of consecutive years under one label ("2019-2020"), its other lines bare */
  marks: Array<{ x: number; label: string }>;
  top: number;
}

/** How far the definitions sit apart in each cohort at grade g (the largest rate less the smallest, with which
 * definitions they are), and the up-to-three cohorts where the gap is widest (and above 0), oldest first. */
export function widestYears(o: C04AgencyOutputs, g: number, n = 3): { spreads: ByYear['spreads']; widest: number[] } {
  const defs = definitionsOf(o);
  const grids = defs.map((d) => yearly(o, d));
  const spreads = o.cohorts.map((_, k) => {
    let hi: Definition | null = null;
    let lo: Definition | null = null;
    let max = -Infinity;
    let min = Infinity;
    for (let i = 0; i < defs.length; i++) {
      const x = grids[i]?.[k]?.[g] ?? null;
      if (x === null) continue;
      if (x > max) {
        max = x;
        hi = defs[i];
      }
      if (x < min) {
        min = x;
        lo = defs[i];
      }
    }
    return hi !== null && lo !== null && hi !== lo ? { spread: max - min, hi, lo } : { spread: 0, hi: null, lo: null };
  });
  const widest = spreads
    .map((s, k) => ({ k, s: s.spread }))
    .filter((e) => e.s > 0)
    .sort((a, b) => b.s - a.s || a.k - b.k)
    .slice(0, n)
    .map((e) => e.k)
    .sort((a, b) => a - b);
  return { spreads, widest };
}

/** The chosen grade's one-year rate by annual cohort under each definition the agency has (the rail's thicker), on a
 * linear axis (a year without a default is a real 0); x is the cohort's calendar year. */
export function byYear(o: C04AgencyOutputs, g: number, chosen: Definition): ByYear {
  const years = o.cohorts.map(yearOf);
  const base = 0;
  const defs = definitionsOf(o);
  const values: ByYear['values'] = {};
  const series: ChartSeries[] = [];
  for (const d of defs) {
    const grid = yearly(o, d);
    if (!grid) continue;
    const vals = grid.map((row) => row[g] ?? null);
    values[d] = vals;
    series.push({ label: DEFINITION_LABEL[d], values: vals, color: DEFINITION_COLOR[d], width: d === chosen ? 2.8 : 1.6 });
  }
  const drawn = series.filter((s) => s.values.some((x) => x !== null));
  const all = drawn.flatMap((s) => s.values.filter((x): x is number => x !== null));
  const { spreads, widest } = widestYears(o, g);
  const x = years.map((y) => y - base);
  const marks: ByYear['marks'] = [];
  for (let i = 0; i < widest.length; i++) {
    const k = widest[i];
    if (i > 0 && k === widest[i - 1] + 1) {
      marks.push({ x: x[k], label: '' });
      continue;
    }
    let end = i;
    while (end + 1 < widest.length && widest[end + 1] === widest[end] + 1) end++;
    marks.push({ x: x[k], label: end > i ? `${years[k]}-${years[widest[end]]}` : String(years[k]) });
  }
  return { years, base, x, defs, values, series: drawn, widest, spreads, marks, top: all.length ? Math.max(...all) : 0 };
}

/** The annual cohorts whose transition page counts no rating in default at the year's end in any grade while the
 * default-rate page counts rated defaulters (Fitch's 2006 to 2014): D4 and Keep read 0 there by the page, not by the
 * obligors. Only where the agency's pages have a default category. */
export function emptyDefaultYears(o: C04AgencyOutputs): Array<{ year: number; defaulted: number }> {
  if (o.pd.d4 === null) return [];
  return o.cohorts
    .filter((c) => c.counts.every((row) => (row[N_GRADES] ?? 0) === 0) && sum(c.defaulted ?? []) > 0)
    .map((c) => ({ year: yearOf(c), defaulted: sum(c.defaulted ?? []) }));
}

function emptyYearsText(l: Lang, years: Array<{ year: number; defaulted: number }>): string {
  if (!years.length) return '';
  const n = sum(years.map((y) => y.defaulted));
  return t(
    l,
    ` ${capital(inYears(l, years.map((y) => y.year)))} the transition page counts no rating in default at the year's end in any grade, while the default-rate page counts ${count(l, n)} rated defaulters: D4 and Keep read 0 there because of the page, not the obligors.`,
    ` ${capital(inYears(l, years.map((y) => y.year)))} la página de transiciones no cuenta ninguna calificación en incumplimiento al cierre del año en ningún grado, mientras la página de tasas de incumplimiento cuenta ${count(l, n)} calificaciones incumplidas: D4 y Con retiros dan 0 allí por la página, no por los deudores.`,
  );
}

/** The By year table's optional columns, in the order a narrow card gives them up (the last first). */
const YEAR_OPTIONAL = ['tab2-cohort', 'defaulted', 'withdrawn'] as const;
type YearOptional = (typeof YEAR_OPTIONAL)[number];

/** The chosen grade's one-year PD under every definition over the annual cohorts, the years where the definitions
 * differ most marked; beside it, the cohort's size and each definition's rate year by year. */
export function ByYearView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = agencyOf(sel);
  const g = sel?.grade ?? N_GRADES - 1;
  const d = v ? definitionFor(v.outputs, sel?.definition) : 'd2';
  const data = useMemo(() => (v ? byYear(v.outputs, g, d) : null), [v, g, d]);
  const fit = useFitColumns(YEAR_OPTIONAL.length, `${lang}|${v?.variant_id ?? ''}|${g}`);
  if (!sel) return <Pending />;
  if (!v || !data) return <NotAgency sel={sel} />;
  const o = v.outputs;
  const prov = provenanceOf(v.provenance.truth_status);
  const name = agencyName(sel, v);
  const grade = GRADES[g];
  const marked = new Set(data.widest);
  const show = (c: YearOptional) => YEAR_OPTIONAL.indexOf(c) < fit.shown;
  const allZero = data.series.length > 0 && data.series.every((s) => s.values.every((x) => x === null || x === 0));
  const empty = emptyDefaultYears(o);
  const axis = axisFor(data.x, data.marks);
  const widestText = (l: Lang): string => {
    if (allZero) return t(l, ` No rating in ${grade} defaulted in any cohort under any definition: every rate is 0.`, ` Ninguna calificación en ${grade} incumplió en ninguna cohorte bajo ninguna definición: toda tasa es 0.`);
    if (!data.widest.length) return t(l, ` The definitions agree in every cohort at ${grade}.`, ` Las definiciones coinciden en cada cohorte en ${grade}.`);
    const items = data.widest.map((k) => {
      const s = data.spreads[k];
      const hi = s.hi ? data.values[s.hi]?.[k] : null;
      const lo = s.lo ? data.values[s.lo]?.[k] : null;
      return t(l, `${data.years[k]} (${pick(CODE[s.hi as Definition], l)} ${pcs(l, hi)} against ${pick(CODE[s.lo as Definition], l)} ${pcs(l, lo)})`, `${data.years[k]} (${pick(CODE[s.hi as Definition], l)} ${pcs(l, hi)} contra ${pick(CODE[s.lo as Definition], l)} ${pcs(l, lo)})`);
    });
    return t(l, ` Marked: the years where the definitions differ most at ${grade}, ${list(l, items)}.`, ` Marcados: los años donde las definiciones más difieren en ${grade}, ${list(l, items)}.`);
  };
  const chartNote = bi(
    (l) =>
      t(
        l,
        `The one-year default rate of each annual cohort's ${grade} ratings, as a share of the cohort, under each definition; the rail's definition (${pick(CODE[d], l)}) thicker. A year without a default is a 0 on the line.`,
        `La tasa de incumplimiento anual de las calificaciones ${grade} de cada cohorte anual, como fracción de la cohorte, bajo cada definición; la definición del panel (${pick(CODE[d], l)}) más gruesa. Un año sin incumplimientos es un 0 en la línea.`,
      ) +
      widestText(l) +
      emptyYearsText(l, empty) +
      pdSource(o, l),
  );
  const hasD4 = data.defs.includes('d4');
  const tableNote = bi(
    (l) =>
      t(
        l,
        `The ratings in ${grade} at each cohort's start (tab 4's row) and each definition's one-year rate in percent of the cohort; where the card has room, tab 2's own cohort (D2's denominator), its rated defaulters and the withdrawals${hasD4 ? ' (D4 removes them from its denominator)' : ''}.${data.widest.length ? ' Highlighted: the years marked on the chart.' : ''}`,
        `Las calificaciones en ${grade} al inicio de cada cohorte (la fila de la pestaña 4) y la tasa anual de cada definición en porcentaje de la cohorte; donde la tarjeta tiene espacio, la cohorte propia de la pestaña 2 (el denominador de D2), sus calificaciones incumplidas y los retiros${hasD4 ? ' (D4 los quita de su denominador)' : ''}.${data.widest.length ? ' Destacados: los años marcados en el gráfico.' : ''}`,
      ) + pdSource(o, l),
  );
  const xLabel: BiText = { en: 'Cohort year', es: 'Año de la cohorte' };
  const yearTable = (
    <div className="ct-scroll" ref={fit.ref}>
      <table className="caos-table ct-wrap-head" data-table="by-year" data-grade={grade}>
        <thead>
          <tr>
            <th>{pick({ en: 'Year', es: 'Año' }, lang)}</th>
            <th>{pick({ en: 'Ratings', es: 'Calif.' }, lang)}</th>
            {data.defs.map((x) => (
              <th key={x}>{`${pick(CODE[x], lang)}, %`}</th>
            ))}
            {show('tab2-cohort') && <th className="ct-wide-only">{pick({ en: 'Tab 2 cohort', es: 'Cohorte pestaña 2' }, lang)}</th>}
            {show('defaulted') && <th className="ct-wide-only">{pick({ en: 'Rated defaulters', es: 'Calif. incumplidas' }, lang)}</th>}
            {show('withdrawn') && <th className="ct-wide-only">{pick({ en: 'Withdrawn', es: 'Retiradas' }, lang)}</th>}
          </tr>
        </thead>
        <tbody>
          {o.cohorts.map((c, k) => (
            <tr key={c.label} data-year={c.label} className={marked.has(k) ? 'ct-current' : undefined}>
              <td>{c.label}</td>
              <td data-col="size">{count(lang, c.size[g])}</td>
              {data.defs.map((x) => (
                <td key={x} data-col={x}>
                  {pc(lang, data.values[x]?.[k] ?? null)}
                </td>
              ))}
              {show('tab2-cohort') && (
                <td className="ct-wide-only" data-col="tab2-cohort">
                  {count(lang, c.defaulted_cohort ? c.defaulted_cohort[g] : null)}
                </td>
              )}
              {show('defaulted') && (
                <td className="ct-wide-only" data-col="defaulted">
                  {count(lang, c.defaulted ? c.defaulted[g] : null)}
                </td>
              )}
              {show('withdrawn') && (
                <td className="ct-wide-only" data-col="withdrawn">
                  {count(lang, c.withdrawn[g])}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={bi((l) => t(l, `${pick(name, l)} ${grade}: one-year PD by cohort, every definition`, `${pick(name, l)} ${grade}: PD anual por cohorte, cada definición`))}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={chartNote}
      >
        {data.series.length ? (
          <UPlotChart
            height="fill"
            x={{ values: axis.x, label: xLabel, format: { decimals: 0, grouping: false } }}
            y={{ label: { en: 'One-year default rate', es: 'Tasa de incumplimiento anual' }, format: { percent: true, digits: 2 }, range: [0, data.top > 0 ? data.top * 1.08 : 0.01] }}
            series={data.series.map((s) => ({ ...s, values: axis.pad(s.values) }))}
            marks={data.marks}
          />
        ) : (
          <p className="ct-note">{pick({ en: `No definition has a rate for ${grade} in any cohort: the table beside lists the cohorts.`, es: `Ninguna definición tiene tasa para ${grade} en ninguna cohorte: la tabla al lado lista las cohortes.` }, lang)}</p>
        )}
      </PlotCard>
      <PlotCard
        fill
        title={bi((l) => t(l, `${grade}, cohort by cohort`, `${grade}, cohorte por cohorte`))}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={tableNote}
      >
        {yearTable}
      </PlotCard>
    </ViewsRow>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// Definitions: the pooled ratios to D2, what each definition counts, and the cohorts the two pages disagree on

/** The pooled ratios D4 over D2 and D3 over D2 by grade (definition_gap), each where the agency has it and some grade
 * has a value. */
export function gapSeries(o: C04AgencyOutputs): ChartSeries[] {
  const out: ChartSeries[] = [];
  const add = (key: 'd4' | 'd3', vals: (number | null)[] | null) => {
    const values = (vals ?? []).map(num);
    if (values.some((x) => x !== null)) {
      out.push({ label: bi((l) => t(l, `${pick(CODE[key], l)} over D2`, `${pick(CODE[key], l)} sobre D2`)), values, color: DEFINITION_COLOR[key], width: 2.2 });
    }
  };
  add('d4', o.definition_gap.d4_over_d2);
  add('d3', o.definition_gap.d3_over_d2);
  return out;
}

export interface CohortGap {
  k: number;
  label: string;
  /** the grades where tab 2's cohort differs from tab 4's row: tab 2's count, tab 4's */
  cells: Array<{ grade: number; tab2: number; tab4: number }>;
  /** tab 2's ratings less tab 4's, summed over the grades */
  extra: number;
  /** the signed relative gap of the CEREP label whose cohort differs most (the reader's tab2_gap) */
  gap: number | null;
}

/** The annual cohorts where the default-rate page's cohort (defaulted_cohort) differs from the transition page's rows
 * (size) in some grade, oldest first. */
export function cohortGaps(o: C04AgencyOutputs): CohortGap[] {
  const out: CohortGap[] = [];
  o.cohorts.forEach((c, k) => {
    const dc = c.defaulted_cohort;
    if (!dc) return;
    const cells = GRADES.map((_, g) => ({ grade: g, tab2: dc[g], tab4: c.size[g] })).filter((x) => x.tab2 !== x.tab4);
    if (cells.length) out.push({ k, label: c.label, cells, extra: sum(cells.map((x) => x.tab2 - x.tab4)), gap: num(c.tab2_gap) });
  });
  return out;
}

/** A definition's pooled rate at grade g: the baked block's, or Keep's (D4's pooled defaults over the whole cohorts,
 * computed here from the artifact's counts); null where the agency's pages do not give the definition. */
export function pooledAt(v: AgencyVariant, x: Definition, g: number): number | null {
  const o = v.outputs;
  if (!definitionsOf(o).includes(x)) return null;
  const l = baked(o, x);
  if (l) return num(l.pooled_rate[g]);
  const c = gradeCounts(v, x, g);
  return c ? c.defaults / c.n : null;
}

/** A definition's pooled rate over D2's at grade g, as the artifact gives it (definition_gap): D2 over itself is 1
 * where D2's pooled rate is above 0 and undefined where it is 0 (0 over 0); Keep has no ratio in the artifact. */
export function ratioAt(o: C04AgencyOutputs, x: Definition, g: number): number | null {
  if (x === 'd2') {
    const p = num(o.lra.d2?.pooled_rate[g]);
    return p !== null && p > 0 ? 1 : null;
  }
  if (x === 'd3') return o.definition_gap.d3_over_d2 ? num(o.definition_gap.d3_over_d2[g]) : null;
  if (x === 'd4') return o.definition_gap.d4_over_d2 ? num(o.definition_gap.d4_over_d2[g]) : null;
  return null;
}

/** CEREP's definitions side by side: the pooled ratios to D2 by grade, what each definition counts with ESMA's
 * statement, and the years where the default-rate page divides by another cohort than the transition page. */
export function DefinitionsView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = agencyOf(sel);
  const series = useMemo(() => (v ? gapSeries(v.outputs) : []), [v]);
  const gaps = useMemo(() => (v ? cohortGaps(v.outputs) : []), [v]);
  if (!sel) return <Pending />;
  if (!v) return <NotAgency sel={sel} />;
  const o = v.outputs;
  const prov = provenanceOf(v.provenance.truth_status);
  const name = agencyName(sel, v);
  const g = sel.grade;
  const grade = GRADES[g];
  const defs = definitionsOf(o);
  const sameEvents = o.cohorts.every((c) => c.events !== null && c.defaulted !== null && c.events.every((e, i) => e === c.defaulted?.[i]));
  const d4 = o.definition_gap.d4_over_d2;
  const d4At = ratioAt(o, 'd4', g);
  const d2Zero = num(o.lra.d2?.pooled_rate[g]) === 0;
  const ratios = series.flatMap((s) => s.values.filter((x): x is number => x !== null));
  const top = Math.max(1.15, ...ratios.map((r) => r * 1.1));
  const cells = gaps.flatMap((x) => x.cells.map((c) => ({ ...c, label: x.label })));
  const worst = cells.length ? cells.reduce((a, b) => ((b.tab2 - b.tab4) / b.tab4 > (a.tab2 - a.tab4) / a.tab4 ? b : a)) : null;
  const larger = cells.filter((c) => c.tab2 > c.tab4).length;
  const atGrade = gaps.filter((x) => x.cells.some((c) => c.grade === g)).length;
  const axis = axisFor(GRADE_POSITIONS, [{ x: g + 1, label: grade }]);
  const chartNote = bi((l) => {
    const d3Text = sameEvents
      ? t(
          l,
          " Tab 3's default events equal tab 2's rated defaulters in every cohort, so D3 over D2 is tab 2's pooled cohort over tab 4's: above 1 where the default-rate page counts more ratings (the cohorts beside).",
          ' Los eventos de incumplimiento de la pestaña 3 igualan a las calificaciones incumplidas de la pestaña 2 en cada cohorte, así que D3 sobre D2 es la cohorte agrupada de la pestaña 2 sobre la de la pestaña 4: mayor que 1 donde la página de tasas de incumplimiento cuenta más calificaciones (las cohortes al lado).',
        )
      : t(l, ' D3 counts every default event, which can exceed the rated defaulters.', ' D3 cuenta cada evento de incumplimiento, que puede superar a las calificaciones incumplidas.');
    const d4Text = !d4
      ? t(l, ` The transition page of ${pick(name, l)} has no default category: there is no D4.`, ` La página de transiciones de ${pick(name, l)} no tiene categoría de incumplimiento: no hay D4.`)
      : d4At === null
        ? d2Zero
          ? t(l, ` At ${grade} D4 over D2 is not defined: D2's pooled rate is 0.`, ` En ${grade} D4 sobre D2 no está definida: la tasa agrupada de D2 es 0.`)
          : t(l, ` At ${grade} the artifact gives no ratio of D4 to D2.`, ` En ${grade} el artefacto no da razón de D4 a D2.`)
        : t(
            l,
            ` At ${grade} the transition page's default column holds ${pcs(l, d4At)} of D2's pooled rate: a rating that defaulted and was withdrawn or re-rated by the year's end is not in it.`,
            ` En ${grade} la columna de incumplimiento de la página de transiciones retiene el ${pcs(l, d4At)} de la tasa agrupada de D2: una calificación que incumplió y fue retirada o recalificada antes del cierre del año no está en ella.`,
          );
    return (
      t(
        l,
        "Each definition's default rate over D2's by grade, both pooled over the cohorts where both are defined (a ratio); dotted, 1: the same share. Marked: the rail's grade.",
        'La tasa de incumplimiento de cada definición sobre la de D2 por grado, ambas agrupadas sobre las cohortes donde las dos están definidas (una razón); punteada, 1: la misma fracción. Marcado: el grado del panel.',
      ) +
      d3Text +
      d4Text +
      pdSource(o, l)
    );
  });
  const gapNote = bi((l) => {
    const allLarger = larger === cells.length;
    const upTo = worst
      ? t(
          l,
          `, by up to ${pcs(l, (worst.tab2 - worst.tab4) / worst.tab4)} (${GRADES[worst.grade]} in ${worst.label}: ${count(l, worst.tab2)} against ${count(l, worst.tab4)})`,
          `, hasta en un ${pcs(l, (worst.tab2 - worst.tab4) / worst.tab4)} (${GRADES[worst.grade]} en ${worst.label}: ${count(l, worst.tab2)} contra ${count(l, worst.tab4)})`,
        )
      : '';
    const head = gaps.length
      ? allLarger
        ? t(
            l,
            `${gaps.length} of ${o.cohorts.length} annual cohorts: tab 2's cohort, D2's denominator, is larger than tab 4's rows in some grade${upTo}.`,
            `${gaps.length} de ${o.cohorts.length} cohortes anuales: la cohorte de la pestaña 2, el denominador de D2, es mayor que las filas de la pestaña 4 en algún grado${upTo}.`,
          )
        : t(
            l,
            `${gaps.length} of ${o.cohorts.length} annual cohorts: tab 2's cohort, D2's denominator, differs from tab 4's rows in some grade, tab 2's the larger in ${larger} of the ${cells.length} cells.`,
            `${gaps.length} de ${o.cohorts.length} cohortes anuales: la cohorte de la pestaña 2, el denominador de D2, difiere de las filas de la pestaña 4 en algún grado, la de la pestaña 2 mayor en ${larger} de las ${cells.length} celdas.`,
          )
      : t(l, 'In every annual cohort the two pages count the same ratings in every grade.', 'En cada cohorte anual las dos páginas cuentan las mismas calificaciones en cada grado.');
    const highlight = atGrade
      ? t(l, ` Highlighted: the ${atGrade} years where ${grade} differs.`, ` Destacados: los ${atGrade} años en que ${grade} difiere.`)
      : gaps.length
        ? t(l, ` No year differs at ${grade}.`, ` Ningún año difiere en ${grade}.`)
        : '';
    return (
      head +
      t(
        l,
        ' Extra ratings: tab 2\'s less tab 4\'s, over the grades. Last column: the relative gap of the CEREP label (a category such as CC within CCC-C) that differs most. ESMA states no reason.',
        ' Calificaciones de más: las de la pestaña 2 menos las de la pestaña 4, sobre los grados. Última columna: la diferencia relativa de la etiqueta de CEREP (una categoría como CC dentro de CCC-C) que más difiere. ESMA no da la razón.',
      ) +
      highlight +
      ` ${sourceText(o, l)}`
    );
  });
  const hasKeep = defs.includes('keep');
  const definitionsNote = bi(
    (l) =>
      t(
        l,
        `CEREP's help file (ESMA65-8-10634), the sections that define the default counts. At ${grade}: each definition's pooled rate, in percent, and its ratio to D2's (the chart's).${hasKeep ? " Keep's pooled rate, which the artifact does not bake, is D4's pooled defaults over the whole cohorts, computed in your browser; the artifact gives it no ratio." : ''}`,
        `El archivo de ayuda de CEREP (ESMA65-8-10634), las secciones que definen los conteos de incumplimiento. En ${grade}: la tasa agrupada de cada definición, en porcentaje, y su razón a la de D2 (la del gráfico).${hasKeep ? ' La tasa agrupada de Con retiros, que el artefacto no trae, son los incumplimientos agrupados de D4 sobre las cohortes completas, calculada en su navegador; el artefacto no le da razón.' : ''}`,
        // ESMA's statement heads this card (data-esma): the note closes with the entity and the source alone
      ) + ` ${sourceText(o, l)}`,
  );
  return (
    <ViewsRow shares={[2, 3]}>
      <PlotCard
        fill
        title={bi((l) => t(l, `${pick(name, l)}: each definition's pooled rate over D2's`, `${pick(name, l)}: la tasa agrupada de cada definición sobre la de D2`))}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={chartNote}
      >
        {series.length ? (
          <UPlotChart
            height="fill"
            x={{ values: axis.x, label: GRADE_AXIS, format: { decimals: 0 } }}
            y={{ label: { en: 'Ratio to D2', es: 'Razón a D2' }, format: { decimals: 2 }, range: [0, top] }}
            series={[
              ...series.map((s) => ({ ...s, values: axis.pad(s.values) })),
              { label: { en: 'Same share as D2 (1)', es: 'Misma fracción que D2 (1)' }, values: axis.pad(GRADE_POSITIONS.map(() => 1)), color: '--color-fg-subtle' as ShellColorToken, width: 1, dash: [2, 4] },
            ]}
            marks={[{ x: g + 1, label: grade }]}
          />
        ) : (
          <p className="ct-note">{pick({ en: 'No pooled ratio to D2 is defined for this agency: the table beside lists what each definition counts.', es: 'Ninguna razón agrupada respecto de D2 está definida para esta agencia: la tabla al lado lista qué cuenta cada definición.' }, lang)}</p>
        )}
      </PlotCard>
      <>
        <PlotCard fill title={{ en: 'What each definition counts', es: 'Qué cuenta cada definición' }} lane={REPLAY} provenance={prov} dataKey={stateKey} note={definitionsNote}>
          <div className="ct-scroll">
            <p className="ct-note" data-esma="definitions">{pick(ESMA_DEFINITIONS, lang)}</p>
            <table className="caos-table ct-wrap-head" data-table="definitions">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Definition', es: 'Definición' }, lang)}</th>
                  <th>{pick({ en: `Pooled at ${grade}, %`, es: `Agrupada en ${grade}, %` }, lang)}</th>
                  <th>{pick({ en: 'Over D2', es: 'Sobre D2' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {DEFINITIONS.flatMap((x) => {
                  const has = defs.includes(x);
                  const r = has ? ratioAt(o, x, g) : null;
                  const current = x === sel.definition ? 'ct-current' : undefined;
                  // the definition's numbers on one row, what it counts on the row under it, across the table
                  return [
                    <tr key={x} data-definition={x} className={current}>
                      <td className="ct-text">
                        <strong>{pick(DEFINITION_LABEL[x], lang)}</strong>
                      </td>
                      <td data-col="pooled">{has ? pc(lang, pooledAt(v, x, g)) : pick({ en: 'not on these pages', es: 'no está en estas páginas' }, lang)}</td>
                      <td data-col="ratio">{r === null ? '-' : formatNumber(r, lang, { decimals: 3 })}</td>
                    </tr>,
                    <tr key={`${x}-hint`} data-hint={x} className={current}>
                      <td className="ct-text" colSpan={3}>
                        {pick(DEFINITION_HINT[x], lang)}
                      </td>
                    </tr>,
                  ];
                })}
              </tbody>
            </table>
          </div>
        </PlotCard>
        <PlotCard
          fill
          title={{ en: "Where tab 2's cohort differs from tab 4's", es: 'Dónde la cohorte de la pestaña 2 difiere de la pestaña 4' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={gapNote}
        >
          <div className="ct-scroll">
            <table className="caos-table ct-wrap-head" data-table="tab2-cohorts">
              <thead>
                <tr>
                  <th>{pick({ en: 'Year', es: 'Año' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Grades: tab 2 against tab 4', es: 'Grados: pestaña 2 contra pestaña 4' }, lang)}</th>
                  <th className="ct-wide-only">{pick({ en: 'Extra ratings', es: 'Calif. de más' }, lang)}</th>
                  <th>{pick({ en: 'Largest label gap, %', es: 'Mayor brecha de etiqueta, %' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {gaps.length ? (
                  gaps.map((x) => (
                    <tr key={x.label} data-year={x.label} className={x.cells.some((c) => c.grade === g) ? 'ct-current' : undefined}>
                      <td>{x.label}</td>
                      <td className="ct-text" data-col="cells">
                        {x.cells.map((c) => `${GRADES[c.grade]} ${count(lang, c.tab2)} ${pick({ en: 'against', es: 'contra' }, lang)} ${count(lang, c.tab4)}`).join('; ')}
                      </td>
                      <td className="ct-wide-only" data-col="extra">
                        {count(lang, x.extra)}
                      </td>
                      <td data-col="gap">{x.gap === null ? '-' : `${x.gap > 0 ? '+' : ''}${pc(lang, x.gap)}`}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td>-</td>
                    <td className="ct-text">{pick({ en: 'none', es: 'ninguna' }, lang)}</td>
                    <td className="ct-wide-only">-</td>
                    <td>-</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </>
    </ViewsRow>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// Lifetime (CT-415): each five-year window as its cohort lived it, against the chained one-year matrices

type LifetimeKey = 'cumulative_d2' | 'default_end' | 'chain_state' | 'chain_exclude' | 'pooled_power' | 'em';
const PROJECTIONS: LifetimeKey[] = ['chain_state', 'chain_exclude', 'pooled_power', 'em'];

interface LifetimeSpec {
  key: LifetimeKey;
  observed: boolean;
  label: BiText;
  /** the table's row label: the same share, named short enough for a narrow column */
  short: BiText;
  color: ShellColorToken;
  width?: number;
  dash?: number[];
}

/** The six shares of the lifetime check, in the chart's order and look: what the cohort lived as points, what one-year
 * matrices project as lines (the chained ones by their withdrawal treatment's definition colour: Keep's for the state,
 * D4's for the removal; EM in the estimators' EM colour). */
function lifetimeSpecs(years: number | null): LifetimeSpec[] {
  const steps = years ?? 5;
  return [
    { key: 'cumulative_d2', observed: true, label: { en: 'Lived: defaulted (tab 2)', es: 'Vivido: incumplidas (pestaña 2)' }, short: { en: 'Lived, tab 2', es: 'Vivido, pestaña 2' }, color: '--color-fg' },
    { key: 'default_end', observed: true, label: { en: 'Lived: in default at the end (tab 4)', es: 'Vivido: en incumplimiento al final (pestaña 4)' }, short: { en: 'Lived, tab 4 at the end', es: 'Vivido, pestaña 4 al final' }, color: '--color-fg-subtle' },
    { key: 'chain_state', observed: false, label: { en: 'Chained, withdrawals a state', es: 'Encadenado, retiros como estado' }, short: { en: 'Chained, state', es: 'Encadenado, estado' }, color: DEFINITION_COLOR.keep, width: 2.4 },
    { key: 'chain_exclude', observed: false, label: { en: 'Chained, withdrawals removed', es: 'Encadenado, sin retiros' }, short: { en: 'Chained, removed', es: 'Encadenado, sin retiros' }, color: DEFINITION_COLOR.d4, width: 2, dash: [7, 4] },
    { key: 'pooled_power', observed: false, label: { en: `Pooled matrix, ${steps} steps`, es: `Matriz agrupada, ${steps} pasos` }, short: { en: 'Pooled matrix', es: 'Matriz agrupada' }, color: '--color-accent-2', width: 1.6 },
    { key: 'em', observed: false, label: { en: `EM generator, ${steps} years`, es: `Generador EM, ${steps} años` }, short: { en: 'EM generator', es: 'Generador EM' }, color: '--color-accent', width: 1.6, dash: [2, 3] },
  ];
}

function lifetimeValue(w: C04Lifetime, key: LifetimeKey, g: number): number | null {
  if (key === 'cumulative_d2') return w.observed.cumulative_d2 ? num(w.observed.cumulative_d2[g]) : null;
  if (key === 'default_end') return num(w.observed.default_end[g]);
  return num(w.projected[key][g]);
}

/** The window (index) where two shares differ most, both given; null where no window gives both. */
function widestGap(a: (number | null)[], b: (number | null)[]): number | null {
  let marked: number | null = null;
  let widest = -1;
  for (let i = 0; i < a.length; i++) {
    const x = a[i];
    const y = b[i];
    if (x === null || y === null || Math.abs(x - y) <= widest) continue;
    widest = Math.abs(x - y);
    marked = i;
  }
  return marked;
}

/** A mark on a window chart: the window (index) where two shares differ most. */
const gapMark = (marked: number | null): Array<{ x: number; label: BiText }> => (marked === null ? [] : [{ x: marked + 1, label: { en: 'widest gap', es: 'mayor brecha' } }]);

export interface LifetimeChart {
  windows: C04Lifetime[];
  /** the window numbers 1 to n, with room before the first where the mark sits on it */
  x: number[];
  series: ChartSeries[];
  /** the observed and projected values by key, one per window (unpadded) */
  values: Record<LifetimeKey, (number | null)[]>;
  /** the window (index) where tab 2's count and the window's chained matrices differ most, if both exist anywhere */
  marked: number | null;
  /** the windows' common length in years, null where they differ */
  years: number | null;
  top: number;
}

/** The lifetime check of grade g: one point per window for what the cohort lived, one line per projection; a series
 * without a value in any window (Moody's projections and tab 4 share) is left out. */
export function lifetimeChart(o: C04AgencyOutputs, g: number): LifetimeChart {
  const windows = o.lifetime;
  const lengths = [...new Set(windows.map((w) => w.last - w.first + 1))];
  const years = lengths.length === 1 ? lengths[0] : null;
  const specs = lifetimeSpecs(years);
  const values = Object.fromEntries(specs.map((s) => [s.key, windows.map((w) => lifetimeValue(w, s.key, g))])) as Record<LifetimeKey, (number | null)[]>;
  const marked = widestGap(values.cumulative_d2, values.chain_state);
  const axis = axisFor(
    windows.map((_, i) => i + 1),
    gapMark(marked),
  );
  const series: ChartSeries[] = specs
    .filter((s) => values[s.key].some((x) => x !== null))
    .map((s) => ({ label: s.label, values: axis.pad(values[s.key]), color: s.color, ...(s.observed ? { mode: 'points' as const } : { width: s.width ?? 2, ...(s.dash ? { dash: s.dash } : {}) }) }));
  const all = Object.values(values).flatMap((vals) => vals.filter((x): x is number => x !== null));
  return { windows, x: axis.x, series, values, marked, years, top: all.length ? Math.max(...all) : 0 };
}

export interface WithdrawnChart {
  /** the window's own page: the share withdrawn by its end; the window's annual matrices chained, withdrawals a state */
  lived: (number | null)[];
  chained: (number | null)[];
  x: number[];
  series: ChartSeries[];
  /** the window (index) where the two differ most */
  marked: number | null;
  top: number;
}

/** The share of grade g's cohort withdrawn by each window's end, lived (points) against chained (line): the rows the
 * lifetime table closes with, drawn; Moody's has them too. */
export function withdrawnChart(o: C04AgencyOutputs, g: number): WithdrawnChart {
  const lived = o.lifetime.map((w) => num(w.observed.withdrawn_end[g]));
  const chained = o.lifetime.map((w) => num(w.projected.chain_state_withdrawn[g]));
  const marked = widestGap(lived, chained);
  const axis = axisFor(
    o.lifetime.map((_, i) => i + 1),
    gapMark(marked),
  );
  const series: ChartSeries[] = [
    { label: { en: 'Lived: withdrawn by the end', es: 'Vivido: retiradas al final' }, values: lived, color: '--color-fg' as const, mode: 'points' as const },
    { label: { en: 'Chained: withdrawn, a state', es: 'Encadenado: retiradas, como estado' }, values: chained, color: DEFINITION_COLOR.keep, width: 2.4 },
  ]
    .filter((s) => s.values.some((x) => x !== null))
    .map((s) => ({ ...s, values: axis.pad(s.values) }));
  const all = [...lived, ...chained].filter((x): x is number => x !== null);
  return { lived, chained, x: axis.x, series, marked, top: all.length ? Math.max(...all) : 0 };
}

/** The five-year windows of CEREP (CT-415) for the chosen grade: the share of the window's cohort that defaulted within
 * it (tab 2) and that is in a default category at its end (tab 4), against what one-year matrices project for it. */
export function LifetimeView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = agencyOf(sel);
  const g = sel?.grade ?? N_GRADES - 1;
  const data = useMemo(() => (v ? lifetimeChart(v.outputs, g) : null), [v, g]);
  const withdrawn = useMemo(() => (v ? withdrawnChart(v.outputs, g) : null), [v, g]);
  if (!sel) return <Pending />;
  if (!v || !data || !withdrawn) return <NotAgency sel={sel} />;
  const o = v.outputs;
  const prov = provenanceOf(v.provenance.truth_status);
  const name = agencyName(sel, v);
  const grade = GRADES[g];
  if (data.windows.length === 0) {
    return (
      <ViewsRow>
        <PlotCard fill title={bi((l) => t(l, `${pick(name, l)}: the lifetime check`, `${pick(name, l)}: la verificación de vida`))} lane={REPLAY} provenance={prov} dataKey={stateKey} note={bi((l) => sourceText(o, l))}>
          <p className="ct-note">{pick({ en: 'No five-year window has data for this agency: CEREP gives no fixed five-year cohort to follow.', es: 'Ninguna ventana de cinco años tiene datos para esta agencia: CEREP no da una cohorte fija de cinco años que seguir.' }, lang)}</p>
        </PlotCard>
      </ViewsRow>
    );
  }
  const projected = PROJECTIONS.some((k) => data.values[k].some((x) => x !== null));
  const hasDefault = o.pd.d4 !== null;
  const emptyYears = emptyDefaultYears(o).map((y) => y.year);
  const steps = data.years ?? 5;
  const xLabel = bi((l) => `${t(l, 'Five-year window', 'Ventana de cinco años')} (${data.windows.map((w, i) => `${i + 1} ${w.label}`).join(', ')})`);
  const markText = (l: Lang): string => {
    if (data.marked === null) return '';
    const w = data.windows[data.marked];
    const lv = pcs(l, data.values.cumulative_d2[data.marked]);
    const ch = pcs(l, data.values.chain_state[data.marked]);
    return t(
      l,
      ` Marked: ${w.label}, the widest gap (${lv} lived against ${ch} chained). The chain's default column cannot hold a default withdrawn or re-rated within the year it happened (that year's tab 4 already misses it), so what it targets lies between tab 4's share at the window's end and tab 2's: part of any gap to tab 2 is the definitions', not the chain's.`,
      ` Marcada: ${w.label}, la mayor brecha (${lv} vivido contra ${ch} encadenado). La columna de incumplimiento de la cadena no puede retener un incumplimiento retirado o recalificado dentro del año en que ocurrió (la pestaña 4 de ese año ya no lo tiene), así que lo que mide queda entre la fracción de la pestaña 4 al final de la ventana y la de la pestaña 2: parte de cualquier brecha con la pestaña 2 es de las definiciones, no de la cadena.`,
    );
  };
  // the windows every year of which has an empty default column on its transition page (Fitch's 2010 to 2014): their
  // chained matrices never reach default; whether the window's own five-year page shows a default is read, not assumed
  const empty = new Set(emptyYears);
  const whole = data.windows.filter((w) => Array.from({ length: w.last - w.first + 1 }, (_, i) => w.first + i).every((y) => empty.has(y)));
  const affected = whole.map((w) => w.label);
  const endEmpty = whole.length > 0 && whole.every((w) => w.observed.default_end.every((x) => x === 0));
  const chartNote = bi(
    (l) =>
      (projected
        ? t(
            l,
            `Each window's ${grade} cohort followed to its end, in shares of the cohort. Points, lived: defaulted within the window (tab 2) and in default at its end (tab 4). Lines, projected: the window's annual matrices chained (withdrawals a state, or removed), the pooled matrix and the EM generator over ${steps} years (the same in every window). The chained default column counts ratings in default at some year-end; tab 4, only those still in default at the window's end: a rating that defaulted and was then withdrawn leaves it.`,
            `La cohorte ${grade} de cada ventana seguida hasta su final, en fracciones de la cohorte. Puntos, lo vivido: incumplidas en la ventana (pestaña 2) y en incumplimiento a su final (pestaña 4). Líneas, lo proyectado: las matrices anuales de la ventana encadenadas (retiros como estado, o quitados), la matriz agrupada y el generador EM en ${steps} años (iguales en cada ventana). La columna de incumplimiento encadenada cuenta las calificaciones en incumplimiento al cierre de algún año; la pestaña 4, solo las que siguen en incumplimiento al final: una que incumplió y luego fue retirada sale de ella.`,
          ) + markText(l)
        : t(
            l,
            `Each window's cohort of ${grade} ratings followed to its end: the share that defaulted within the window (tab 2, D2's page). The transition page of ${pick(name, l)} has no default category, so there is no share in default at a window's end and no projection of one; the table sets the withdrawn shares, lived and chained, side by side.`,
            `La cohorte de calificaciones ${grade} de cada ventana seguida hasta su final: la fracción que incumplió dentro de la ventana (pestaña 2, la página de D2). La página de transiciones de ${pick(name, l)} no tiene categoría de incumplimiento, así que no hay fracción en incumplimiento al final de una ventana ni su proyección; la tabla pone lado a lado las fracciones retiradas, vividas y encadenadas.`,
          )) +
      (affected.length
        ? t(
            l,
            ` The transition pages hold no default ${inYears(l, emptyYears)}: the chain never defaults in ${list(l, affected)}${endEmpty ? ', nor does its own page show one' : ''}; a 0 there is the page's, not the cohort's.`,
            ` Las páginas de transiciones no registran incumplimientos ${inYears(l, emptyYears)}: la cadena nunca incumple en ${list(l, affected)}${endEmpty ? ', ni su propia página muestra uno' : ''}; un 0 allí es de la página, no de la cohorte.`,
          )
        : '') +
      pdSource(o, l),
  );
  const title = projected
    ? bi((l) => t(l, `${pick(name, l)} ${grade}: five years lived against the chained one-year matrices`, `${pick(name, l)} ${grade}: cinco años vividos contra las matrices anuales encadenadas`))
    : bi((l) => t(l, `${pick(name, l)} ${grade}: rated defaulters within each five-year window (tab 2)`, `${pick(name, l)} ${grade}: calificaciones incumplidas en cada ventana de cinco años (pestaña 2)`));
  // the chart's shares in its order, named short, then the withdrawn shares; a row the pages give nowhere is left out
  const shares: Array<{ key: string; label: BiText; values: (number | null)[] }> = [
    ...lifetimeSpecs(data.years).map((s) => ({ key: s.key, label: s.short, values: data.values[s.key] })),
    { key: 'withdrawn_end', label: { en: 'Lived, withdrawn', es: 'Vivido, retiradas' }, values: withdrawn.lived },
    { key: 'chain_state_withdrawn', label: { en: 'Chained, withdrawn', es: 'Encadenado, retiradas' }, values: withdrawn.chained },
  ];
  const given = shares.filter((r) => r.values.some((x) => x !== null));
  const rows: Array<{ key: string; label: BiText; cells: string[] }> = [
    { key: 'size', label: { en: 'Ratings at the start', es: 'Cohorte al inicio' }, cells: data.windows.map((w) => count(lang, w.size[g])) },
    ...given.map((r) => ({ key: r.key, label: r.label, cells: r.values.map((x) => pc(lang, x)) })),
  ];
  const omitted = shares.length - given.length;
  const tableNote = bi(
    (l) =>
      t(
        l,
        `Shares of each window's ${grade} cohort in percent, the chart's in its order; the first row counts the cohort at the window's start (tab 4), the last two the share withdrawn by the window's end, lived and chained (withdrawals an absorbing state).${omitted ? ` ${omitted} rows the pages give for no window are left out.` : ''}${data.marked !== null ? ` The chart marks ${data.windows[data.marked].label}.` : ''}`,
        `Fracciones de la cohorte ${grade} de cada ventana en porcentaje, las del gráfico en su orden; la primera fila cuenta la cohorte al inicio de la ventana (pestaña 4), las dos últimas la fracción retirada al final de la ventana, vivida y encadenada (los retiros como estado absorbente).${omitted ? ` Se omiten ${omitted} filas que las páginas no dan para ninguna ventana.` : ''}${data.marked !== null ? ` El gráfico marca ${data.windows[data.marked].label}.` : ''}`,
      ) + pdSource(o, l),
  );
  const withdrawnNote = bi((l) => {
    const marked =
      withdrawn.marked === null
        ? ''
        : t(
            l,
            ` Marked: ${data.windows[withdrawn.marked].label}, the widest gap (${pcs(l, withdrawn.lived[withdrawn.marked])} lived against ${pcs(l, withdrawn.chained[withdrawn.marked])} chained).`,
            ` Marcada: ${data.windows[withdrawn.marked].label}, la mayor brecha (${pcs(l, withdrawn.lived[withdrawn.marked])} vivido contra ${pcs(l, withdrawn.chained[withdrawn.marked])} encadenado).`,
          );
    const counted = hasDefault
      ? t(
          l,
          " A rating that defaulted and was then withdrawn within the window is withdrawn on the window's page, and stays in default in the chain, whose default state is absorbing.",
          ' Una calificación que incumplió y luego fue retirada dentro de la ventana está retirada en la página de la ventana, y sigue en incumplimiento en la cadena, cuyo estado de incumplimiento es absorbente.',
        )
      : t(l, ` The transition page of ${pick(name, l)} has no default category.`, ` La página de transiciones de ${pick(name, l)} no tiene categoría de incumplimiento.`);
    return (
      t(
        l,
        `The share of each window's ${grade} cohort withdrawn by the window's end, in shares of the cohort: lived (points, the window's own transition page) against the window's annual matrices chained with withdrawals an absorbing state (line).`,
        `La fracción de la cohorte ${grade} de cada ventana retirada al final de la ventana, en fracciones de la cohorte: lo vivido (puntos, la propia página de transiciones de la ventana) contra las matrices anuales de la ventana encadenadas con los retiros como estado absorbente (línea).`,
      ) +
      counted +
      marked +
      ` ${sourceText(o, l)}`
    );
  });
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={title}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={chartNote}
      >
        {data.series.length ? (
          <UPlotChart
            height="fill"
            x={{ values: data.x, label: xLabel, format: { decimals: 0 } }}
            y={{ label: { en: 'Share of the cohort', es: 'Fracción de la cohorte' }, format: { percent: true, digits: 2 }, range: [0, data.top > 0 ? data.top * 1.08 : 0.01] }}
            series={data.series}
            marks={gapMark(data.marked)}
          />
        ) : (
          <p className="ct-note">{pick({ en: `No share of the ${grade} cohort is given in any window: the table beside lists the windows.`, es: `Ninguna fracción de la cohorte ${grade} está dada en ninguna ventana: la tabla al lado lista las ventanas.` }, lang)}</p>
        )}
      </PlotCard>
      <>
        <PlotCard fill title={bi((l) => t(l, `${grade}, window by window`, `${grade}, ventana por ventana`))} lane={REPLAY} provenance={prov} dataKey={stateKey} note={tableNote}>
          <div className="ct-scroll">
            <table className="caos-table ct-wrap-head" data-table="lifetime" data-grade={grade}>
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Share, %', es: 'Fracción, %' }, lang)}</th>
                  {data.windows.map((w) => (
                    <th key={w.label} data-window={w.label}>
                      {w.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.key} data-row={r.key}>
                    <td className="ct-text">{pick(r.label, lang)}</td>
                    {r.cells.map((c, i) => (
                      <td key={data.windows[i].label}>{c}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
        <div className="ct-tall-only">
          <PlotCard
            fill
            title={bi((l) => t(l, `${grade}: withdrawn by the window's end, lived against chained`, `${grade}: retiradas al final de la ventana, vivido contra encadenado`))}
            lane={REPLAY}
            provenance={prov}
            dataKey={stateKey}
            note={withdrawnNote}
          >
            {withdrawn.series.length ? (
              <UPlotChart
                height="fill"
                x={{ values: withdrawn.x, label: xLabel, format: { decimals: 0 } }}
                y={{ label: { en: 'Share of the cohort', es: 'Fracción de la cohorte' }, format: { percent: true, digits: 2 }, range: [0, withdrawn.top > 0 ? withdrawn.top * 1.08 : 0.01] }}
                series={withdrawn.series}
                marks={gapMark(withdrawn.marked)}
              />
            ) : (
              <p className="ct-note">{pick({ en: `No withdrawn share of the ${grade} cohort is given in any window: the table above lists the windows.`, es: `Ninguna fracción retirada de la cohorte ${grade} está dada en ninguna ventana: la tabla de arriba lista las ventanas.` }, lang)}</p>
            )}
          </PlotCard>
        </div>
      </>
    </ViewsRow>
  );
}

// ---------------------------------------------------------------------------------------------------------------------

/** What these views say on a variant that is not an agency's: they read CEREP cohorts, which only S&P, Moody's and
 * Fitch carry. The instrument never mounts them there; this keeps the card honest if one is. */
function NotAgency({ sel }: { sel: C04Sel }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = sel.data.variant as VariantArtifact<unknown>;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: "An agency's CEREP view", es: 'Una vista de CEREP de una agencia' }}
        lane={REPLAY}
        provenance={provenanceOf(v.provenance.truth_status)}
        dataKey={stateKey}
        note={{ en: "This view reads the CEREP cohorts of an agency variant (S&P, Moody's or Fitch).", es: "Esta vista lee las cohortes de CEREP de una variante de agencia (S&P, Moody's o Fitch)." }}
      >
        <p className="ct-note">
          {pick({ en: `The variant ${v.variant_id} carries no CEREP cohorts: pick an agency.`, es: `La variante ${v.variant_id} no trae cohortes de CEREP: elija una agencia.` }, lang)}
        </p>
      </PlotCard>
    </ViewsRow>
  );
}
