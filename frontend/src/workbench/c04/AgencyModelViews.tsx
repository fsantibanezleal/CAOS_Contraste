// C04's agency variants (S&P's, Moody's and Fitch's EU entities on ESMA's CEREP), the Model group (web.md, "Agency
// variants"): the one-year matrix as a heat map with its withdrawals column, pooled over the annual cohorts or one
// cohort's own; and the generators of the pooled matrix: the one-year PD by grade each gives on a log axis, their L1
// distances to the matrix, and Israel, Rosenthal and Wei's (2001) diagnostics of whether an exact generator can exist.
// Every number is the artifact's, as riskvalidation computed it (contract.md section 1); a cohort's own matrix is its
// counts over its size, the shares the engine's cohort estimator gives with the withdrawals a state. Where a cohort's
// transition page holds no rating in default while its default page counts rated defaulters (Fitch's 2006 to 2014,
// finding F-D4-EMPTY), every PD read from the matrix is 0 by the page, and the views say so beside the number.
import { ChipGroup, Knob, PlotCard, formatNumber, pick, useShellLang, useWorkbenchState, type BiText, type Lang } from '@fasl-work/caos-app-shell';
import { UPlotChart, type ChartSeries } from '@fasl-work/caos-app-shell/chart';
import { useMemo } from 'react';
import type { C04AgencyOutputs, Text, VariantArtifact } from '../../lib/contract.types';
import { REPLAY, provenanceOf } from '../model';
import { Pending } from '../Pending';
import { MatrixMap, type MapScale, type MatrixMapProps } from './MatrixMap';
import {
  DEFINITION_LABEL,
  ESMA_DEFINITIONS,
  ESTIMATOR_COLOR,
  ESTIMATOR_LABEL,
  GENERATOR_KEYS,
  GRADES,
  GRADE_AXIS,
  N_GRADES,
  definitionsOf,
  isAgency,
  type AgencyVariant,
  type C04Sel,
  type GeneratorKey,
} from './selection';

/** The default state's index (after the seven grades) and the withdrawals' in the nine states of `matrix_state`. */
const D = N_GRADES;
const W = N_GRADES + 1;
const ROWS: string[] = [...GRADES];
const DIAGONAL: number[] = GRADES.map((_, i) => i);
const sum = (a: readonly number[]) => a.reduce((s, x) => s + x, 0);

const both = (f: (lang: Lang) => string): Text => ({ en: f('en'), es: f('es') });
/** A shell text in both languages, to build a longer text from it. */
const bi = (t: BiText): Text => ({ en: pick(t, 'en'), es: pick(t, 'es') });
const NONE: Text = { en: '', es: '' };
const pct = (lang: Lang, v: number | null | undefined, digits = 3) => (v === null || v === undefined ? '-' : formatNumber(v, lang, { percent: true, digits }));
/** A share in percent without its sign, for a column whose header carries the unit. */
const pctNum = (lang: Lang, v: number | null | undefined) => (v === null || v === undefined ? '-' : formatNumber(v * 100, lang, { digits: 3 }));
const ratings = (lang: Lang, v: number) => formatNumber(v, lang, { decimals: 0 });
const num = (lang: Lang, v: number | null | undefined, digits = 4) => (v === null || v === undefined ? '-' : formatNumber(v, lang, { digits }));
/** A number the pipeline computed: it writes null where a value is not finite (contract.md section 1). */
const finite = (x: number | null | undefined): x is number => typeof x === 'number' && Number.isFinite(x);
const joinList = (items: string[], lang: Lang) =>
  items.length <= 1 ? items.join('') : `${items.slice(0, -1).join(', ')} ${lang === 'es' ? 'y' : 'and'} ${items[items.length - 1]}`;

/** The variant as an agency variant, or null (the instrument shows this group on agency variants only). */
export function agencyOf(sel: C04Sel | null): AgencyVariant | null {
  const v = sel?.data.variant as VariantArtifact<unknown> | undefined;
  return v && isAgency(v) ? v : null;
}

/** The agency as the variant chips name it (S&P, Moody's, Fitch). */
function shortOf(sel: C04Sel, v: AgencyVariant): Text {
  const e = sel.data.manifest.artifacts.find((a) => a.role === 'variant' && a.variant_id === v.variant_id);
  return e?.short_title ?? { en: v.outputs.agency.code, es: v.outputs.agency.code };
}

/** An English possessive: S&P's, Fitch's, and Moody's as it is. */
export const possessive = (name: string) => (/'s$/.test(name) ? name : /s$/.test(name) ? `${name}'` : `${name}'s`);

const SCOPE_TEXT: Record<string, Text> = {
  'corporate, long-term, categories': { en: 'corporate long-term ratings by category', es: 'calificaciones corporativas de largo plazo por categoría' },
};

/** The attribution CEREP's reuse terms ask for, and the entity whose statistics these are: ESMA's tables of the agency's
 * EU entity, not the agency's own studies (design.md, "What not to claim"). */
export function sourceText(o: C04AgencyOutputs): Text {
  const scope = SCOPE_TEXT[o.agency.scope] ?? { en: o.agency.scope, es: o.agency.scope };
  return {
    en: `${o.attribution}. Entity: ${o.agency.name} (${o.agency.code}), ${scope.en}.`,
    es: `${o.attribution}. Entidad: ${o.agency.name} (${o.agency.code}), ${scope.es}.`,
  };
}

/** Whether the agency's transition page has a default category (Moody's has none: no D4, no Keep). */
export const hasDefaultCategory = (o: C04AgencyOutputs) => definitionsOf(o).includes('d4');

/** A state of the eight the pooled matrix and its generators run on (seven grades, then D). */
const stateName = (o: C04AgencyOutputs, j: number) => o.states[j] ?? (j < N_GRADES ? GRADES[j] : 'D');

/** The rail's grade, kept on the scale. */
const gradeOf = (sel: C04Sel) => Math.min(N_GRADES - 1, Math.max(0, Math.round(sel.grade)));

// ---------------------------------------------------------------------------------------------------------------------
// The cohorts whose transition page has an empty default column

export interface EmptyColumn {
  /** the index of the annual cohort */
  cohort: number;
  label: string;
  /** the rated defaulters the default page counts in that cohort, every grade */
  defaulted: number;
}

/** The annual cohorts whose transition page holds no rating in default in any grade while the default page counts rated
 * defaulters (Fitch's 2006 to 2014, finding F-D4-EMPTY): those defaulters sit in the withdrawals, so the matrix's D
 * column, and D4 and Keep, read 0 there by the page, not by the cohort. The rule of AgencyValidationViews'
 * `emptyDefaultYears`, by cohort index (the tests hold the two to the same cohorts); only where the page has a default
 * category. */
export function emptyColumnCohorts(o: C04AgencyOutputs): EmptyColumn[] {
  if (!hasDefaultCategory(o)) return [];
  return o.cohorts.flatMap((c, k) => {
    const defaulted = sum(c.defaulted ?? []);
    return defaulted > 0 && c.counts.every((row) => (row[D] ?? 0) === 0) ? [{ cohort: k, label: c.label, defaulted }] : [];
  });
}

/** Cohorts by their labels, consecutive ones as a range: "2006 to 2014". */
function cohortRanges(o: C04AgencyOutputs, ks: number[], lang: Lang): string {
  const runs: Array<[number, number]> = [];
  for (const k of [...ks].sort((a, b) => a - b)) {
    const last = runs[runs.length - 1];
    if (last && k === last[1] + 1) last[1] = k;
    else runs.push([k, k]);
  }
  return joinList(
    runs.map(([a, b]) => (a === b ? o.cohorts[a].label : `${o.cohorts[a].label} ${lang === 'es' ? 'a' : 'to'} ${o.cohorts[b].label}`)),
    lang,
  );
}

/** What the empty default columns do to the pooled matrix: `row`, under the grade's PDs, in full (the D column and the
 * D4 and Keep PDs read from it); `map`, the map's note, short; `generators`, the PD chart's note and the distances,
 * short (every PD of the matrix and of its generators). Empty where no cohort has an empty column. The short forms keep
 * the notes, which take their height from the drawing above them, to a line or two. */
export function emptyPooledText(o: C04AgencyOutputs, scope: 'row' | 'map' | 'generators'): Text {
  const empty = emptyColumnCohorts(o);
  if (!empty.length) return NONE;
  const ks = empty.map((e) => e.cohort);
  const n = sum(empty.map((e) => e.defaulted));
  return both((l) => {
    const years = cohortRanges(o, ks, l);
    const count = ratings(l, n);
    if (l === 'es') {
      if (scope === 'map') return `D incluye ${years}, cuando la página de transiciones no cuenta ninguna calificación en incumplimiento mientras la página de incumplimientos cuenta ${count} calificaciones incumplidas (aquí en W): D subestima los incumplimientos de esa página.`;
      if (scope === 'generators') return `La matriz agrupada incluye ${years}, cuando la página de transiciones no cuenta ninguna calificación en incumplimiento mientras la página de incumplimientos cuenta ${count} calificaciones incumplidas: estas PD subestiman las de esa página.`;
      return `La columna de incumplimiento agrupada incluye las cohortes ${years}, en las que la página de transiciones no tiene ninguna calificación en incumplimiento en ningún grado mientras la página de incumplimientos cuenta ${count} calificaciones incumplidas: la página de transiciones las cuenta como retiradas, así que la columna D agrupada, y las PD con D4 y Con retiros que se leen de ella, subestiman los incumplimientos que cuenta la página de incumplimientos.`;
    }
    if (scope === 'map') return `D includes ${years}, when the transition page counts no rating in default while the default page counts ${count} rated defaulters (in W here): D understates that page's defaults.`;
    if (scope === 'generators') return `The pooled matrix includes ${years}, when the transition page counts no rating in default while the default page counts ${count} rated defaulters: these PDs understate that page's.`;
    return `The pooled default column includes the cohorts ${years}, in which the transition page holds no rating in default in any grade while the default page counts ${count} rated defaulters: the transition page counts them as withdrawn, so the pooled D column, and the D4 and Keep PDs read from it, understate the defaults the default page counts.`;
  });
}

/** What the empty default column of the annual cohort `k` means: given a grade, in full under that grade's PDs (its
 * rated defaulters on the default page and their D2 rate); without one (null), short, for the map's note. Empty where
 * the cohort's column is not empty. */
export function emptyCohortText(o: C04AgencyOutputs, k: number, g: number | null): Text {
  const e = emptyColumnCohorts(o).find((x) => x.cohort === k);
  if (!e) return NONE;
  const c = o.cohorts[k];
  const d2Label = bi(DEFINITION_LABEL.d2);
  return both((l) => {
    const count = ratings(l, e.defaulted);
    if (g === null) {
      return l === 'es'
        ? `En ${c.label} la página de transiciones no cuenta ninguna calificación en incumplimiento mientras la página de incumplimientos cuenta ${count} calificaciones incumplidas (aquí en W): D marca 0 por la página, no por la cohorte.`
        : `In ${c.label} the transition page counts no rating in default while the default page counts ${count} rated defaulters (in W here): D reads 0 by the page, not by the cohort.`;
    }
    const ng = c.defaulted?.[g] ?? 0;
    const d2 = o.pd.d2?.[k]?.[g] ?? null;
    const grade = GRADES[g];
    const of =
      l === 'es'
        ? ng > 0
          ? `, ${ratings(l, ng)} de ellas en ${grade} (${pct(l, d2)} con "${d2Label.es}")`
          : `, ninguna de ellas en ${grade}`
        : ng > 0
          ? `, ${ratings(l, ng)} of them in ${grade} (${pct(l, d2)} under "${d2Label.en}")`
          : `, none of them in ${grade}`;
    return l === 'es'
      ? `En ${c.label} la página de transiciones no tiene ninguna calificación en incumplimiento en ningún grado mientras la página de incumplimientos cuenta ${count} calificaciones incumplidas${of}: la página de transiciones las cuenta como retiradas (W), así que la columna D, D4 y Con retiros marcan 0 por la página, no por la cohorte.`
      : `In ${c.label} the transition page holds no rating in default in any grade while the default page counts ${count} rated defaulters${of}: the transition page counts them as withdrawn (W), so the D column, D4 and Keep read 0 by the page, not by the cohort.`;
  });
}

// ---------------------------------------------------------------------------------------------------------------------
// Matrix

/** The matrix the map draws: rows the seven grades at the start of the year, columns the state at its end (the seven
 * grades, D where the page has a default category, W withdrawn by the end), each row the shares of its cohort with the
 * withdrawals in it; and the counts behind every cell. */
export interface MatrixData {
  /** null: the matrix pooled over the annual cohorts; else the index of the annual cohort shown */
  cohort: number | null;
  /** the cohort's label ("2010"), null for the pooled matrix */
  label: string | null;
  hasDefault: boolean;
  /** each column's index in the nine states of `matrix_state` */
  states: number[];
  cols: string[];
  values: (number | null)[][];
  counts: number[][];
  /** by grade: the ratings at the start, withdrawals included (each row's total) */
  size: number[];
  /** by grade: the ratings withdrawn by the end of the year */
  withdrawn: number[];
}

/** The pooled matrix with the withdrawals a state (`pooled.matrix_state`, Anderson and Goodman 2.8, its counts
 * `pooled.counts` and `pooled.withdrawn`), or the annual cohort `cohort`'s own (its counts and withdrawals over its
 * size); an index outside the cohorts reads as the pooled matrix. */
export function matrixData(o: C04AgencyOutputs, cohort: number | null): MatrixData {
  const hasDefault = hasDefaultCategory(o);
  const states = [...DIAGONAL, ...(hasDefault ? [D] : []), W];
  const cols = states.map((j) => (j === W ? 'W' : j === D ? 'D' : GRADES[j]));
  const k = cohort !== null && Number.isInteger(cohort) && cohort >= 0 && cohort < o.cohorts.length ? cohort : null;
  const c = k === null ? null : o.cohorts[k];
  const counts = GRADES.map((_, g) => {
    const row = c ? c.counts[g] : o.pooled.counts[g];
    const w = c ? c.withdrawn[g] : o.pooled.withdrawn[g];
    return states.map((j) => (j === W ? w : row[j]));
  });
  const withdrawn = GRADES.map((_, g) => (c ? c.withdrawn[g] : o.pooled.withdrawn[g]));
  const size = GRADES.map((_, g) => (c ? c.size[g] : sum(o.pooled.counts[g]) + o.pooled.withdrawn[g]));
  const values = GRADES.map((_, g) => {
    if (!c) return states.map((j) => o.pooled.matrix_state[g]?.[j] ?? null);
    return size[g] > 0 ? counts[g].map((x) => x / size[g]) : states.map(() => null);
  });
  return { cohort: k, label: c ? c.label : null, hasDefault, states, cols, values, counts, size, withdrawn };
}

/** The knob's position of a matrix (0 the pooled one, i + 1 the annual cohort i) and back. */
export const knobOfCohort = (cohort: number | null) => (cohort === null ? 0 : cohort + 1);
export function cohortOfKnob(x: number, cohorts: number): number | null {
  const k = Math.round(x);
  return k <= 0 || cohorts <= 0 ? null : Math.min(k, cohorts) - 1;
}

/** The map's props as the view passes them: the grade picked on the map is the rail's grade; the withdrawals column is
 * kept out of the migrations scale (W is no migration, and at up to 31% of a speculative row it set the top of the
 * range, darkening every move between grades). */
export function mapProps(sel: C04Sel, m: MatrixData, label: BiText): MatrixMapProps {
  return {
    label,
    rows: ROWS,
    cols: m.cols,
    values: m.values,
    counts: m.counts,
    scale: sel.mapScale,
    diagonal: DIAGONAL,
    outside: m.states.flatMap((s, j) => (s === W ? [j] : [])),
    selectedRow: gradeOf(sel),
    onPickRow: (row) => sel.act.setGrade(row),
  };
}

interface ScaleText {
  id: MapScale;
  label: Text;
  hint: Text;
  note: Text;
}

/** The three colour scales of the map; the migrations scale names D among the migrations where the page has one. */
export function scaleTexts(hasDefault: boolean): ScaleText[] {
  return [
    {
      id: 'migrations',
      label: { en: 'Migrations', es: 'Migraciones' },
      hint: {
        en: `Linear over the moves between ${hasDefault ? 'states, those to D included' : 'grades'} only: the diagonal (most of a row stays in its grade) and W (withdrawn by the end, no migration) are kept out of the range and drawn grey, so the migrations are told apart.`,
        es: `Lineal solo sobre los movimientos entre ${hasDefault ? 'estados, los que van a D incluidos' : 'grados'}: la diagonal (la mayor parte de una fila se queda en su grado) y W (retiradas antes del fin, no una migración) quedan fuera del rango y se dibujan en gris, para distinguir las migraciones.`,
      },
      note: {
        en: `Colour: viridis, linear over the migrations${hasDefault ? ', D included' : ''}; the diagonal and W grey and out of the range.`,
        es: `Color: viridis, lineal sobre las migraciones${hasDefault ? ', D incluida' : ''}; la diagonal y W en gris y fuera del rango.`,
      },
    },
    {
      id: 'linear',
      label: { en: 'Linear', es: 'Lineal' },
      hint: { en: 'Every cell on one linear scale, the diagonal and W included.', es: 'Todas las celdas en una escala lineal, la diagonal y W incluidas.' },
      note: { en: 'Colour: viridis, linear over every cell.', es: 'Color: viridis, lineal sobre todas las celdas.' },
    },
    {
      id: 'log',
      label: { en: 'Log', es: 'Log.' },
      hint: { en: 'Every cell on a log scale: the rare moves show; a zero sits at the bottom and prints 0.', es: 'Todas las celdas en escala logarítmica: se ven los movimientos raros; un cero queda abajo y se imprime 0.' },
      note: { en: 'Colour: viridis, log scale over every cell, a zero at the bottom.', es: 'Color: viridis, escala logarítmica sobre todas las celdas, un cero abajo.' },
    },
  ];
}

const STATE_TEXT: Record<'D' | 'W', Text> = {
  D: { en: 'D, a default category', es: 'D, una categoría de incumplimiento' },
  W: { en: 'W, withdrawn by the end', es: 'W, retirada antes del fin' },
};

/** The one-year matrix of the agency, pooled or one cohort's (a cohort knob and the colour scale above the map), and
 * the rail's grade read along its row: where its ratings were at the end of the year, then the cohort's size, its
 * withdrawals and the two PDs the row gives (Keep withdrawals and D4). */
export function MatrixView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = agencyOf(sel);
  const cohort = sel?.cohort ?? null;
  const m = useMemo(() => (v ? matrixData(v.outputs, cohort) : null), [v, cohort]);
  if (!sel) return <Pending />;
  if (!v || !m) return <NotAgency sel={sel} />;
  const o = v.outputs;
  const prov = provenanceOf(v.provenance.truth_status);
  const short = shortOf(sel, v);
  const src = sourceText(o);
  const g = gradeOf(sel);
  const grade = GRADES[g];
  const n = o.cohorts.length;
  const nText = both((l) => ratings(l, n));
  const first = o.cohorts[0]?.label ?? '';
  const last = o.cohorts[n - 1]?.label ?? '';
  const scales = scaleTexts(m.hasDefault);
  const scale = scales.find((s) => s.id === sel.mapScale) ?? scales[0];
  const pooled = m.label === null;
  const k = m.cohort;
  const keepLabel = bi(DEFINITION_LABEL.keep);
  const d4Label = bi(DEFINITION_LABEL.d4);
  const esma = bi(ESMA_DEFINITIONS);
  // the cohort's default column is empty while its default page counts defaulters (Fitch 2006 to 2014): the map's note
  // and the row's PDs say so; the pooled matrix says which cohorts it holds of that kind
  const emptyCohort = k !== null && emptyColumnCohorts(o).some((e) => e.cohort === k);
  const mapEmpty = k === null ? emptyPooledText(o, 'map') : emptyCohortText(o, k, null);
  const rowEmpty = k === null ? emptyPooledText(o, 'row') : emptyCohortText(o, k, g);

  const title: Text = pooled
    ? { en: `${short.en}: the pooled one-year matrix, ${first} to ${last}`, es: `${short.es}: la matriz anual agrupada, ${first} a ${last}` }
    : { en: `${short.en}: the ${m.label} cohort's one-year matrix`, es: `${short.es}: la matriz anual de la cohorte ${m.label}` };
  // the note is short: it takes its height from the map above it (the readout line under the map says how to read it)
  const columns: Text = m.hasDefault
    ? {
        en: `columns its state at the end (D a default category of the transition page, W withdrawn by the end; D over the whole cohort is "${keepLabel.en}")`,
        es: `columnas su estado al final (D una categoría de incumplimiento de la página de transiciones, W retirada antes del fin; D sobre toda la cohorte es "${keepLabel.es}")`,
      }
    : {
        en: `columns its state at the end (W withdrawn by the end; ${possessive(short.en)} transition page has no default category, so no D column and no PD)`,
        es: `columnas su estado al final (W retirada antes del fin; la página de transiciones de ${short.es} no tiene categoría de incumplimiento: no hay columna D ni PD)`,
      };
  const rowsText: Text = pooled
    ? {
        en: `each row the shares of its cohort in percent, pooled over the ${nText.en} annual cohorts (Anderson and Goodman (2.8), withdrawals a state)`,
        es: `cada fila las fracciones de su cohorte en porcentaje, agrupadas sobre las ${nText.es} cohortes anuales (Anderson y Goodman (2.8), los retiros un estado)`,
      }
    : {
        en: `each row the shares of the ${m.label} cohort in percent: its counts over its size`,
        es: `cada fila las fracciones de la cohorte ${m.label} en porcentaje: sus conteos sobre su tamaño`,
      };
  const note: Text = {
    en: `Rows the grade at the start of the year, ${columns.en}; ${rowsText.en}.${mapEmpty.en ? ` ${mapEmpty.en}` : ''} ${scale.note.en} ${src.en}`,
    es: `Filas el grado al inicio del año, ${columns.es}; ${rowsText.es}.${mapEmpty.es ? ` ${mapEmpty.es}` : ''} ${scale.note.es} ${src.es}`,
  };
  const mapLabel: Text = pooled
    ? { en: `${short.en} one-year matrix pooled over ${first} to ${last}, withdrawals a state`, es: `Matriz anual de ${short.es} agrupada de ${first} a ${last}, los retiros un estado` }
    : { en: `${short.en} one-year matrix of the ${m.label} cohort, withdrawals a state`, es: `Matriz anual de ${short.es} de la cohorte ${m.label}, los retiros un estado` };

  const cohortUnit: Text = pooled ? { en: '(pooled)', es: '(agrupada)' } : { en: `(${m.label})`, es: `(${m.label})` };
  // above the map, not in the card's head: at 1280 x 800 the head holds the title and the lane badges, and the two
  // controls beside them squeezed the title to one word a line, clipped the scale chips and, in Spanish, overflowed
  // the card (measured on the rendered card, 2026-10-07). Side by side from 900 px (ct-row): the map keeps the height
  // a second row of controls took, and the range input's 2 px of user-agent margin fall in the gap, not past the card
  const controls = (
    <div className="ct-row" data-controls="c04-map">
      <Knob
        id="c04-map-cohort"
        label={{ en: 'Cohort', es: 'Cohorte' }}
        hint={{
          en: `0 is the matrix pooled over the ${nText.en} annual cohorts; 1 to ${nText.en} one cohort's own matrix, oldest first (${first} to ${last}).`,
          es: `0 es la matriz agrupada sobre las ${nText.es} cohortes anuales; 1 a ${nText.es} la matriz propia de una cohorte, de la más antigua a la más reciente (${first} a ${last}).`,
        }}
        value={knobOfCohort(m.cohort)}
        min={0}
        max={n}
        step={1}
        format={{ decimals: 0 }}
        unit={cohortUnit}
        onChange={(x) => sel.act.setCohort(cohortOfKnob(x, n))}
      />
      <ChipGroup
        id="c04-map-scale"
        label={{ en: 'Colour scale', es: 'Escala de color' }}
        options={scales.map((s) => ({ id: s.id, label: s.label, hint: s.hint }))}
        value={scale.id}
        onChange={(id) => sel.act.setMapScale(id as MapScale)}
      />
    </div>
  );

  // the rail's grade along its row
  const size = m.size[g];
  const wd = m.withdrawn[g];
  const rated = size - wd;
  const keep = !m.hasDefault ? null : k === null ? o.pooled.matrix_state[g]?.[D] ?? null : o.pd.keep?.[k]?.[g] ?? null;
  const d4 = !m.hasDefault ? null : k === null ? o.pooled.matrix[g]?.[D] ?? null : o.pd.d4?.[k]?.[g] ?? null;
  // a PD the page's empty default column gives says so beside the number
  const emptyMark: Text = { en: ' (empty default column)', es: ' (columna de incumplimiento vacía)' };
  const pdOf = (l: Lang, x: number | null) => (x === null ? '-' : `${pct(l, x)}${emptyCohort ? pick(emptyMark, l) : ''}`);
  const where: Text = pooled ? { en: `over the ${nText.en} cohorts ${first} to ${last}`, es: `en las ${nText.es} cohortes ${first} a ${last}` } : { en: `in the ${m.label} cohort`, es: `en la cohorte ${m.label}` };
  // the states by their symbols, explained here: the words ran the table past its card at 1000 px (measured, 2026-10-07)
  const rowNote: Text = {
    en: `The ${grade} row of the ${pooled ? 'pooled matrix' : `${m.label} cohort's matrix`}: each state's share of the cohort at the start of the year (percent) and its count of ratings; ${m.hasDefault ? 'D a default category of the transition page, ' : ''}W withdrawn by the end of the year.${m.hasDefault ? ` ${esma.en}` : ''} ${src.en}`,
    es: `La fila ${grade} de la ${pooled ? 'matriz agrupada' : `matriz de la cohorte ${m.label}`}: la fracción de la cohorte al inicio del año en cada estado (porcentaje) y su conteo de calificaciones; ${m.hasDefault ? 'D una categoría de incumplimiento de la página de transiciones, ' : ''}W retirada antes del fin del año.${m.hasDefault ? ` ${esma.es}` : ''} ${src.es}`,
  };
  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col ct-share-3">
        <PlotCard fill title={title} lane={REPLAY} provenance={prov} dataKey={stateKey} note={note}>
          <div className="ct-stack">
            {controls}
            <MatrixMap {...mapProps(sel, m, mapLabel)} />
          </div>
        </PlotCard>
      </div>
      <div className="ct-col ct-share-2">
        <PlotCard
          fill
          title={{ en: `Where ${grade} ended the year`, es: `Dónde quedó ${grade} al final del año` }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={rowNote}
        >
          {/* the row first, what the card is for; the sentences that read it after it (at 1280 x 800 the sentences
              above it pushed B, CCC-C, D and W below the card's fold, measured 2026-10-07) */}
          <div className="ct-scroll">
            <table className="caos-table ct-wrap-head" data-table="c04-matrix-row" data-grade={grade} data-cohort={m.label ?? 'pooled'}>
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'At the end', es: 'Al final' }, lang)}</th>
                  <th>{pick({ en: 'Share', es: 'Fracción' }, lang)}</th>
                  <th>{pick({ en: 'Count', es: 'Conteo' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {m.cols.map((col, j) => (
                  <tr key={col} data-state={col} className={j === g ? 'ct-current' : undefined}>
                    <td className="ct-text" title={col === 'D' || col === 'W' ? pick(STATE_TEXT[col], lang) : undefined}>
                      {col}
                    </td>
                    <td>{pct(lang, m.values[g][j])}</td>
                    <td>{ratings(lang, m.counts[g][j])}</td>
                  </tr>
                ))}
                <tr data-state="all">
                  <td className="ct-text">{pick({ en: 'The cohort', es: 'La cohorte' }, lang)}</td>
                  <td>{size > 0 ? pct(lang, 1) : '-'}</td>
                  <td>{ratings(lang, size)}</td>
                </tr>
              </tbody>
            </table>
            <p className="ct-note" data-summary="cohort">
              {size > 0
                ? pick(
                    {
                      en: `${ratings('en', size)} ratings in ${grade} at the start ${where.en}; ${ratings('en', wd)} withdrawn by the end of the year (${pct('en', wd / size)}), ${ratings('en', rated)} rated at the end.`,
                      es: `${ratings('es', size)} calificaciones en ${grade} al inicio ${where.es}; ${ratings('es', wd)} retiradas antes del fin del año (${pct('es', wd / size)}), ${ratings('es', rated)} calificadas al final.`,
                    },
                    lang,
                  )
                : pick({ en: `No rating in ${grade} at the start ${where.en}: the row is empty.`, es: `Ninguna calificación en ${grade} al inicio ${where.es}: la fila está vacía.` }, lang)}
            </p>
            <p className="ct-note" data-summary="pd">
              {m.hasDefault
                ? pick(
                    {
                      en: `One-year PD of ${grade}: ${pdOf('en', keep)} under "${keepLabel.en}" (over the whole cohort), ${pdOf('en', d4)} under "${d4Label.en}" (over the ${ratings('en', rated)} rated at the end).`,
                      es: `PD a un año de ${grade}: ${pdOf('es', keep)} con "${keepLabel.es}" (sobre toda la cohorte), ${pdOf('es', d4)} con "${d4Label.es}" (sobre las ${ratings('es', rated)} calificadas al final).`,
                    },
                    lang,
                  )
                : pick(
                    {
                      en: `${possessive(short.en)} transition page has no default category: its PDs by grade come from the default pages (D2 and D3), in the Validation group.`,
                      es: `La página de transiciones de ${short.es} no tiene categoría de incumplimiento: sus PD por grado vienen de las páginas de incumplimientos (D2 y D3), en el grupo Validación.`,
                    },
                    lang,
                  )}
            </p>
            {rowEmpty.en && (
              <p className="ct-note" data-summary="empty">
                {pick(rowEmpty, lang)}
              </p>
            )}
          </div>
        </PlotCard>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// Generators

const POOLED_LABEL: Text = { en: 'Pooled matrix', es: 'Matriz agrupada' };
const GRADE_X = DIAGONAL.map((i) => i + 1);
/** Room right of the last grade: the shell draws a mark's label right of its line and its chart takes no x range, so
 * the label of CCC-C (the rail's default grade) was cut at the canvas's edge (seen on the rendered chart, 2026-10-07).
 * The padding x is 7.9: it adds no tick (8 is past the axis' end) and every series is a gap there. */
const ROOM = 0.9;
/** EM, the diagonal and the weighted repairs nearly coincide on these matrices: their dashes tell them apart. */
const GENERATOR_STYLE: Record<GeneratorKey, { width: number; dash?: number[] }> = {
  em: { width: 2.4 },
  diagonal: { width: 1.6, dash: [7, 4] },
  weighted: { width: 1.6, dash: [2, 4] },
  jlt: { width: 1.6 },
};
/** A generator as a sentence names it. */
const GENERATOR_NOUN: Record<GeneratorKey, Text> = {
  em: { en: 'EM', es: 'EM' },
  diagonal: { en: 'the diagonal repair', es: 'la reparación diagonal' },
  weighted: { en: 'the weighted repair', es: 'la reparación ponderada' },
  jlt: { en: "JLT's approximation", es: 'la aproximación de JLT' },
};

/** Why a generator is missing from the artifact (contract.md section 1: the pipeline writes none where its method
 * does not apply). */
function missingReason(o: C04AgencyOutputs, k: GeneratorKey): Text {
  if (k === 'jlt') return { en: 'none: equation (3) takes log p_ii, and a grade has p_ii = 0', es: 'ninguno: la ecuación (3) toma log p_ii, y un grado tiene p_ii = 0' };
  if (!o.embedding.series_converges) return { en: "none: Theorem 1's series does not converge, so there is no series generator to repair", es: 'ninguno: la serie del teorema 1 no converge, así que no hay generador de la serie que reparar' };
  return { en: 'none in the artifact', es: 'ninguno en el artefacto' };
}

/** The series of the PD chart: the pooled matrix's default column (points) and the default column of exp(Q) of every
 * generator the artifact holds; a value that is not positive is a gap on the log axis, and a series without any value
 * is left out (Moody's: none at all). */
export function pdSeries(o: C04AgencyOutputs): ChartSeries[] {
  const positive = (xs: readonly (number | null)[]) => xs.map((x) => (x !== null && x > 0 ? x : null));
  const out: ChartSeries[] = [];
  if (hasDefaultCategory(o)) {
    const pooled = positive(o.pooled.matrix.slice(0, N_GRADES).map((r) => r[D]));
    if (pooled.some((x) => x !== null)) out.push({ label: POOLED_LABEL, values: pooled, color: ESTIMATOR_COLOR.cohort, mode: 'points' });
  }
  for (const k of GENERATOR_KEYS) {
    const gen = o.generators[k];
    if (!gen) continue;
    const values = positive(gen.pd_1y);
    if (values.some((x) => x !== null)) out.push({ label: ESTIMATOR_LABEL[k], values, color: ESTIMATOR_COLOR[k], ...GENERATOR_STYLE[k] });
  }
  return out;
}

/** The log axis of the PD chart, in whole decades: from the decade under the smallest PD to 100% (or a decade above the
 * largest PD where all are below 1%). The highest PD, CCC-C's, then sits a decade under the top of the plot, where the
 * mark's label is drawn: with the axis ending at the largest PD the label sat on the curve when the rail's grade was
 * CCC-C (seen on the rendered chart, 2026-10-07). */
export function pdRange(series: ChartSeries[]): [number, number] | null {
  const values = series.flatMap((s) => s.values.filter((x): x is number => x !== null && x > 0));
  if (!values.length) return null;
  const lo = 10 ** Math.floor(Math.log10(Math.min(...values)));
  const top = Math.max(...values);
  return [lo, top > 0.01 ? 1 : 10 ** (Math.ceil(Math.log10(top)) + 1)];
}

/** The PD chart as the view draws it: the grades 1 to 7 and the room after them (every series a gap there), the
 * series, the log axis' range, and the rail's grade marked and labelled. */
export interface PdChart {
  x: number[];
  series: ChartSeries[];
  range: [number, number] | null;
  marks: Array<{ x: number; label: Text }>;
}
export function pdChart(o: C04AgencyOutputs, g: number): PdChart {
  const series = pdSeries(o);
  return {
    x: [...GRADE_X, GRADE_X[GRADE_X.length - 1] + ROOM],
    series: series.map((s) => ({ ...s, values: [...s.values, null] })),
    range: pdRange(series),
    marks: [{ x: g + 1, label: { en: GRADES[g], es: GRADES[g] } }],
  };
}

/** The grades the pooled matrix never saw default (no point on the log axis), and whether every generator still gives
 * them a PD; empty where every grade has one, and on a page without a default category. */
export function zeroDefaultText(o: C04AgencyOutputs): Text {
  const zero = hasDefaultCategory(o) ? DIAGONAL.filter((i) => o.pooled.matrix[i]?.[D] === 0) : [];
  if (!zero.length) return NONE;
  const present = GENERATOR_KEYS.filter((k) => o.generators[k]);
  const lifted = present.length > 0 && present.every((k) => zero.every((i) => (o.generators[k]?.pd_1y[i] ?? 0) > 0));
  return both((l) => {
    const names = joinList(
      zero.map((i) => GRADES[i]),
      l,
    );
    const one = zero.length === 1;
    if (l === 'es') {
      return `${names} no ${one ? 'tiene' : 'tienen'} incumplimientos en la matriz agrupada, así que no ${one ? 'tiene' : 'tienen'} punto en el eje logarítmico${lifted ? `; cada generador le${one ? '' : 's'} da una PD positiva, por movimientos a grados peores dentro del año` : ''}.`;
    }
    return `${names} ${one ? 'has' : 'have'} no default in the pooled matrix, so no point on the log axis${lifted ? `; every generator gives ${one ? 'it' : 'them'} a positive PD, through moves to lower grades within the year` : ''}.`;
  });
}

/** EM's fit: its iterations, whether it converged, and its log-likelihood. */
export function emLine(o: C04AgencyOutputs): Text {
  const em = o.generators.em;
  return {
    en: `EM: ${ratings('en', em.iterations)} iterations, ${em.converged ? 'converged' : 'not converged'}; log-likelihood ${finite(em.loglik) ? formatNumber(em.loglik, 'en', { decimals: 1 }) : '-'}.`,
    es: `EM: ${ratings('es', em.iterations)} iteraciones, ${em.converged ? 'convergió' : 'no convergió'}; log-verosimilitud ${finite(em.loglik) ? formatNumber(em.loglik, 'es', { decimals: 1 }) : '-'}.`,
  };
}

/** Theorem 3's verdict in one line, with the conditions that give it. */
export function verdict(o: C04AgencyOutputs): Text {
  const e = o.embedding;
  if (!e.exact_generator_excluded) return { en: 'Theorem 3 does not rule out an exact generator of the pooled matrix.', es: 'El teorema 3 no descarta un generador exacto de la matriz agrupada.' };
  const why = both((lang) =>
    joinList(
      [
        ...(e.theorem3.a ? [lang === 'es' ? '(a) det P no es positivo' : '(a) det P is not positive'] : []),
        ...(e.theorem3.b ? [lang === 'es' ? '(b) det P supera el producto de la diagonal' : '(b) det P is above the product of the diagonal'] : []),
        ...(e.theorem3.c.length
          ? [lang === 'es' ? `(c) ${ratings(lang, e.theorem3.c.length)} movimientos alcanzables nunca observados` : `(c) ${ratings(lang, e.theorem3.c.length)} moves reachable but never observed`]
          : []),
      ],
      lang,
    ),
  );
  return {
    en: `No exact generator: exp(Q) = P has no solution with Q a generator, by ${why.en}. Every generator here is an approximation, judged by its L1 distance.`,
    es: `Sin generador exacto: exp(Q) = P no tiene solución con Q un generador, por ${why.es}. Cada generador aquí es una aproximación, juzgada por su distancia L1.`,
  };
}

/** The generators closest to and farthest from the pooled matrix by L1; empty with fewer than two. */
export function closestText(o: C04AgencyOutputs): Text {
  const present = GENERATOR_KEYS.flatMap((k) => {
    const d = o.generators[k]?.l1;
    return finite(d) ? [{ k, l1: d }] : [];
  });
  if (present.length < 2) return NONE;
  const sorted = [...present].sort((a, b) => a.l1 - b.l1);
  const lo = sorted[0];
  const hi = sorted[sorted.length - 1];
  return both((l) =>
    l === 'es'
      ? `Más cerca de la matriz agrupada: ${pick(GENERATOR_NOUN[lo.k], l)} (L1 ${num(l, lo.l1)}); más lejos: ${pick(GENERATOR_NOUN[hi.k], l)} (L1 ${num(l, hi.l1)}).`
      : `Closest to the pooled matrix: ${pick(GENERATOR_NOUN[lo.k], l)} (L1 ${num(l, lo.l1)}); farthest: ${pick(GENERATOR_NOUN[hi.k], l)} (L1 ${num(l, hi.l1)}).`,
  );
}

/** A generator's full name, as the variant's model list gives it (with its source), else its short label. */
function generatorName(v: AgencyVariant, rung: string, fallback: BiText): BiText {
  return v.model.find((m) => m.rung === rung)?.title ?? fallback;
}

/** Two shares written with as many digits as it takes to tell them apart (three at least, eight at most). */
export function distinct(a: number, b: number, lang: Lang): [string, string] {
  for (let d = 3; d <= 8; d++) {
    const x = formatNumber(a, lang, { percent: true, digits: d });
    const y = formatNumber(b, lang, { percent: true, digits: d });
    if (x !== y || d === 8) return [x, y];
  }
  return [pct(lang, a), pct(lang, b)];
}

/** The L1 distance of each generator's exp(Q) to the pooled matrix, with its validity and, where the page has a
 * default category, the rail's grade's one-year PD under D4 (in percent, the header carries the unit) beside the pooled
 * matrix's own. The repairs, JLT's approximation and EM's M-step give a generator by construction (the artifact's flag
 * says whether it is one): the validity column needs a wide instrument, and a generator that is not one says so in its
 * name's cell at every width. The short names are the chart's keys; the full ones, with their sources, are each cell's
 * tooltip and the notes'. */
function DistanceTable({ v, grade }: { v: AgencyVariant; grade: number }) {
  const lang = useShellLang();
  const o = v.outputs;
  const withPd = hasDefaultCategory(o);
  const yes = pick({ en: 'yes', es: 'sí' }, lang);
  const no = pick({ en: 'no', es: 'no' }, lang);
  return (
    <table className="caos-table ct-wrap-head" data-table="c04-generators">
      <thead>
        <tr>
          <th className="ct-text">{pick({ en: 'Generator', es: 'Generador' }, lang)}</th>
          <th>{pick({ en: 'L1 to the pooled matrix', es: 'L1 a la matriz agrupada' }, lang)}</th>
          {withPd && <th data-col="pd">{pick({ en: `One-year PD (D4, %), ${GRADES[grade]}`, es: `PD a un año (D4, %), ${GRADES[grade]}` }, lang)}</th>}
          <th className="ct-room-only">{pick({ en: 'Valid generator', es: 'Generador válido' }, lang)}</th>
        </tr>
      </thead>
      <tbody>
        {withPd && (
          <tr data-generator="pooled">
            <td className="ct-text" title={pick(generatorName(v, 'cohort', POOLED_LABEL), lang)}>{pick(POOLED_LABEL, lang)}</td>
            <td>-</td>
            <td>{pctNum(lang, o.pooled.matrix[grade]?.[D])}</td>
            <td className="ct-room-only">-</td>
          </tr>
        )}
        {GENERATOR_KEYS.map((k) => {
          const gen = o.generators[k];
          const name = pick(ESTIMATOR_LABEL[k], lang);
          const full = pick(generatorName(v, k, ESTIMATOR_LABEL[k]), lang);
          return gen ? (
            <tr key={k} data-generator={k}>
              <td className="ct-text" title={full}>{gen.valid ? name : `${name} (${pick({ en: 'not a valid generator', es: 'no es un generador válido' }, lang)})`}</td>
              <td>{num(lang, gen.l1)}</td>
              {withPd && <td>{pctNum(lang, gen.pd_1y[grade])}</td>}
              <td className="ct-room-only">{gen.valid ? yes : no}</td>
            </tr>
          ) : (
            <tr key={k} data-generator={k}>
              <td className="ct-text" title={full}>{`${name}: ${pick(missingReason(o, k), lang)}`}</td>
              <td>-</td>
              {withPd && <td>-</td>}
              <td className="ct-room-only">-</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

const IRW: Text = { en: 'Israel et al. (2001)', es: 'Israel et al. (2001)' };

/** Theorem 1's S, Theorem 3's three conditions and Lemma 1's stochastic monotonicity of the pooled matrix, each read
 * and sourced. */
function EmbeddingList({ o }: { o: C04AgencyOutputs }) {
  const lang = useShellLang();
  const e = o.embedding;
  const to = lang === 'es' ? 'a' : 'to';
  const moves = e.theorem3.c.map(([i, j]) => `${stateName(o, i)} ${to} ${stateName(o, j)}`);
  const violations = e.monotonicity_violations.map((x) => {
    const [a, b] = finite(x.tail) && finite(x.next_tail) ? distinct(x.tail, x.next_tail, lang) : [pct(lang, x.tail), pct(lang, x.next_tail)];
    const end = x.column === D ? stateName(o, D) : `${stateName(o, x.column)} ${lang === 'es' ? 'o peor' : 'or worse'}`;
    return lang === 'es'
      ? `${stateName(o, x.row)} ${a} y ${stateName(o, x.next_row)} ${b} terminan en ${end}`
      : `${stateName(o, x.row)} ${a} and ${stateName(o, x.next_row)} ${b} end in ${end}`;
  });
  const breaks = violations.length;
  const rows: Array<{ id: string; name: Text; value: string; reading: Text; source: Text }> = [
    {
      id: 'S',
      name: { en: "S, the largest |λ - 1|² over P's eigenvalues", es: 'S, el mayor |λ - 1|² entre los valores propios de P' },
      value: num(lang, e.S),
      reading: e.series_converges
        ? {
            en: `The log series converges${finite(e.S) && e.S < 1 ? ' (S below 1)' : ''}: its sum Q has exp(Q) = P but may hold negative rates, which the diagonal and weighted repairs remove.`,
            es: `La serie logarítmica converge${finite(e.S) && e.S < 1 ? ' (S menor que 1)' : ''}: su suma Q cumple exp(Q) = P pero puede tener tasas negativas, que las reparaciones diagonal y ponderada eliminan.`,
          }
        : { en: 'The log series does not converge: there is no series generator to repair.', es: 'La serie logarítmica no converge: no hay generador de la serie que reparar.' },
      source: { en: `${IRW.en}, Theorem 1`, es: `${IRW.es}, teorema 1` },
    },
    {
      id: 'det',
      name: { en: 'det P against the product of the diagonal', es: 'det P contra el producto de la diagonal' },
      value: `${num(lang, e.det)} ${lang === 'es' ? 'contra' : 'against'} ${num(lang, e.prod_diagonal)}`,
      reading: e.theorem3.a
        ? { en: 'det P is not positive: no exact generator, by (a).', es: 'det P no es positivo: sin generador exacto, por (a).' }
        : e.theorem3.b
          ? { en: 'det P is above the product: no exact generator, by (b).', es: 'det P supera el producto: sin generador exacto, por (b).' }
          : { en: 'det P is positive and at most the product: neither (a) nor (b) rules a generator out.', es: 'det P es positivo y como máximo el producto: ni (a) ni (b) descartan un generador.' },
      source: { en: `${IRW.en}, Theorem 3 (a) and (b)`, es: `${IRW.es}, teorema 3 (a) y (b)` },
    },
    {
      id: 'c',
      name: { en: 'Moves reachable but never observed', es: 'Movimientos alcanzables pero nunca observados' },
      value: ratings(lang, moves.length),
      reading: moves.length
        ? { en: `${joinList(moves, 'en')}: no exact generator, by (c).`, es: `${joinList(moves, 'es')}: sin generador exacto, por (c).` }
        : { en: 'None: (c) does not rule a generator out.', es: 'Ninguno: (c) no descarta un generador.' },
      source: { en: `${IRW.en}, Theorem 3 (c)`, es: `${IRW.es}, teorema 3 (c)` },
    },
    {
      id: 'monotone',
      name: { en: 'Stochastic monotonicity', es: 'Monotonía estocástica' },
      value: e.stochastically_monotone
        ? pick({ en: 'yes', es: 'sí' }, lang)
        : pick({ en: `no, ${ratings('en', breaks)} ${breaks === 1 ? 'break' : 'breaks'}`, es: `no, ${ratings('es', breaks)} ${breaks === 1 ? 'quiebre' : 'quiebres'}` }, lang),
      reading: e.stochastically_monotone
        ? { en: 'A worse grade never ends in a state or worse less often than the grade above it.', es: 'Un grado peor nunca termina en un estado o peor con menos frecuencia que el grado sobre él.' }
        : { en: `A grade ends lower more often than the next worse one: ${violations.join('; ')}.`, es: `Un grado termina más abajo con más frecuencia que el siguiente peor: ${violations.join('; ')}.` },
      source: { en: `Lemma 1 (Jarrow, Lando and Turnbull 1997, p. 495), in ${IRW.en}`, es: `Lema 1 (Jarrow, Lando y Turnbull 1997, p. 495), en ${IRW.es}` },
    },
  ];
  // one column, each diagnostic a row with its name, value, reading and source: in the narrow card, columns wrapped
  // each diagnostic's name over seven lines, and a fourth column ran the table past the card at 1280 x 800 (measured,
  // 2026-10-07)
  return (
    <table className="caos-table" data-table="c04-embedding">
      <thead>
        <tr>
          <th className="ct-text">{pick({ en: 'Diagnostic, value and reading', es: 'Diagnóstico, valor y lectura' }, lang)}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.id} data-diagnostic={r.id}>
            <td className="ct-text">
              <strong>{pick(r.name, lang)}</strong>: <span data-value={r.id}>{r.value}</span>. {pick(r.reading, lang)}{' '}
              <span className="ct-note" data-source={r.id}>
                ({pick(r.source, lang)})
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** The one-year PD by grade from the pooled matrix and from each of its generators (log axis), then Israel, Rosenthal
 * and Wei's verdict, the diagnostics behind it and the generators' distances. An agency without a default category
 * (Moody's) has no PD to draw: one card gives the verdict, the distances and the diagnostics instead. */
export function GeneratorsView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = agencyOf(sel);
  const g = sel ? gradeOf(sel) : N_GRADES - 1;
  const chart = useMemo(() => (v ? pdChart(v.outputs, g) : null), [v, g]);
  if (!sel) return <Pending />;
  if (!v || !chart) return <NotAgency sel={sel} />;
  const o = v.outputs;
  const prov = provenanceOf(v.provenance.truth_status);
  const short = shortOf(sel, v);
  const src = sourceText(o);
  const n = o.cohorts.length;
  const d4Label = bi(DEFINITION_LABEL.d4);
  const em = emLine(o);
  const zero = zeroDefaultText(o);
  const empty = emptyPooledText(o, 'generators');
  const missing = GENERATOR_KEYS.filter((k) => !o.generators[k]);
  const missingText = both((l) => (missing.length ? ` ${missing.map((k) => `${pick(ESTIMATOR_LABEL[k], l)}: ${pick(missingReason(o, k), l)}`).join('; ')}.` : ''));
  // the notes are short: a card's note takes its height from the drawing or the table above it. The methods' long
  // names and sources are the distances' tooltips (the variant's model list) and the Context's write-up
  const irw: Text = {
    en: 'Israel, Rosenthal and Wei (2001), Mathematical Finance 11(2), 245-265, doi:10.1111/1467-9965.00114',
    es: 'Israel, Rosenthal y Wei (2001), Mathematical Finance 11(2), 245-265, doi:10.1111/1467-9965.00114',
  };
  const methods: Text = {
    en: `EM on the ${ratings('en', n)} annual count matrices (Bladt and Sørensen 2005), the diagonal and weighted repairs of the log series and JLT's approximation (${irw.en})`,
    es: `EM sobre las ${ratings('es', n)} matrices de conteos anuales (Bladt y Sørensen 2005), las reparaciones diagonal y ponderada de la serie logarítmica y la aproximación de JLT (${irw.es})`,
  };
  const l1Note: Text = {
    en: 'L1: the sum of the absolute entries of P - exp(Q), P the pooled one-year matrix with the withdrawals removed.',
    es: 'L1: la suma de los valores absolutos de las entradas de P - exp(Q), P la matriz anual agrupada sin los retiros.',
  };
  const verdictText = verdict(o);
  const closest = closestText(o);
  const verdictLine = (
    <p className="ct-note" data-verdict={o.embedding.exact_generator_excluded ? 'excluded' : 'open'}>
      {pick(verdictText, lang)}
      {closest.en ? ` ${pick(closest, lang)}` : ''}
    </p>
  );
  const emText = <p className="ct-note" data-em="">{pick(em, lang)}</p>;

  if (!chart.series.length) {
    // Moody's: no default column, so no PD series; one card at the row's width, the distances leading (they need no
    // default column), then EM's fit and the diagnostics. Two cards left the wide one mostly empty and cut the narrow
    // one's diagnostics mid-line at 1280 x 800 (measured, 2026-10-07)
    return (
      <div className="caos-views-row" data-views="1">
        <div className="ct-col">
          <PlotCard
            fill
            title={{ en: `${short.en}: the generators of the pooled matrix, their distances and diagnostics`, es: `${short.es}: los generadores de la matriz agrupada, sus distancias y diagnósticos` }}
            lane={REPLAY}
            provenance={prov}
            dataKey={stateKey}
            note={{
              en: `${possessive(short.en)} transition page has no default category: neither the pooled matrix nor any of its generators gives a PD, and no PD series is drawn. The table gives each generator's distance to the pooled matrix: ${methods.en}. ${l1Note.en} Then Israel, Rosenthal and Wei's diagnostics of P, each with its theorem. ${src.en}`,
              es: `La página de transiciones de ${short.es} no tiene categoría de incumplimiento: ni la matriz agrupada ni sus generadores dan una PD, y no se dibuja ninguna serie de PD. La tabla da la distancia de cada generador a la matriz agrupada: ${methods.es}. ${l1Note.es} Luego los diagnósticos de P de Israel, Rosenthal y Wei, cada uno con su teorema. ${src.es}`,
            }}
          >
            <div className="ct-scroll">
              {verdictLine}
              <DistanceTable v={v} grade={g} />
              {emText}
              <EmbeddingList o={o} />
            </div>
          </PlotCard>
        </div>
      </div>
    );
  }

  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col ct-share-3">
        <PlotCard
          fill
          title={{ en: `${short.en}: one-year PD by grade, the pooled matrix and its generators`, es: `${short.es}: PD a un año por grado, la matriz agrupada y sus generadores` }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `One-year PD by grade under "${d4Label.en}", in percent on a log axis: the pooled matrix's default column (points) and that of exp(Q) for each generator of the matrix: ${methods.en}.${zero.en ? ` ${zero.en}` : ''}${missingText.en}${empty.en ? ` ${empty.en}` : ''} The marked grade is the rail's. ${src.en}`,
            es: `PD a un año por grado con "${d4Label.es}", en porcentaje sobre un eje logarítmico: la columna de incumplimiento de la matriz agrupada (puntos) y la de exp(Q) de cada generador de la matriz: ${methods.es}.${zero.es ? ` ${zero.es}` : ''}${missingText.es}${empty.es ? ` ${empty.es}` : ''} El grado marcado es el del panel. ${src.es}`,
          }}
        >
          <UPlotChart
            height="fill"
            x={{ values: chart.x, label: GRADE_AXIS, format: { decimals: 0 } }}
            y={{ label: { en: 'PD, D4 (%, log scale)', es: 'PD, D4 (%, escala log.)' }, log: true, format: { percent: true, digits: 3 }, ...(chart.range ? { range: chart.range } : {}) }}
            series={chart.series}
            marks={chart.marks}
          />
        </PlotCard>
      </div>
      <div className="ct-col ct-share-2">
        <PlotCard
          fill
          title={{ en: 'Diagnostics and distances', es: 'Diagnósticos y distancias' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `Israel, Rosenthal and Wei's (2001) diagnostics of the pooled one-year matrix P (withdrawals removed), each with its theorem; each generator's L1 distance to P (the sum of the absolute entries of P - exp(Q)) and its PD under "${d4Label.en}", in percent. ${src.en}`,
            es: `Los diagnósticos de Israel, Rosenthal y Wei (2001) de la matriz anual agrupada P (sin los retiros), cada uno con su teorema; la distancia L1 de cada generador a P (la suma de los valores absolutos de las entradas de P - exp(Q)) y su PD con "${d4Label.es}", en porcentaje. ${src.es}`,
          }}
        >
          {/* the verdict and the diagnostics behind it first, the distances after them: at 1280 x 800 the distances
              and EM's fit above pushed all four diagnostics below the card's fold (measured, 2026-10-07); the verdict
              names the closest and the farthest generator, so the distances' headline stays in view. Fitch's empty
              default columns are said under the distances, whose PDs they lower */}
          <div className="ct-scroll">
            {verdictLine}
            <EmbeddingList o={o} />
            <DistanceTable v={v} grade={g} />
            {emText}
            {empty.en && (
              <p className="ct-note" data-empty="">
                {pick(empty, lang)}
              </p>
            )}
          </div>
        </PlotCard>
      </div>
    </div>
  );
}

/** What a view of this group says on a variant that is not an agency's (the instrument shows the group on agency
 * variants only). */
function NotAgency({ sel }: { sel: C04Sel }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = sel.data.variant as VariantArtifact<unknown>;
  return (
    <div className="caos-views-row" data-views="1">
      <div className="ct-col">
        <PlotCard
          title={{ en: 'An agency view', es: 'Una vista de agencia' }}
          lane={REPLAY}
          provenance={provenanceOf(v.provenance.truth_status)}
          dataKey={stateKey}
          note={{
            en: "This view draws an agency variant's CEREP tables (S&P, Moody's or Fitch); the variant open is a generator family or the papers, which have none.",
            es: "Esta vista dibuja las tablas de CEREP de una variante de agencia (S&P, Moody's o Fitch); la variante abierta es una familia de generadores o los artículos, que no las tienen.",
          }}
        >
          <p className="ct-note">{pick({ en: "Pick S&P, Moody's or Fitch among the variants.", es: "Elija S&P, Moody's o Fitch entre las variantes." }, lang)}</p>
        </PlotCard>
      </div>
    </div>
  );
}
