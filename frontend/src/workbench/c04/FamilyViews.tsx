// C04's generator families (CT-405, CT-411): the Model view every family shares (the true chain, its PDs, the design)
// and each family's Validation views, read from the family artifacts as the pipeline wrote them (riskvalidation's
// estimators, intervals and tests on rating paths drawn from a known generator). Every replayed rate and mean carries
// its Monte Carlo SE; the thin family is exact (enumerated, no Monte Carlo error). The truth of every family is the EM
// generator of the pooled annual CEREP counts of S&P's EU entity, so the views name that entity and carry ESMA's
// attribution. Each chart is built by a pure function (exported for the tests through FAMILY_VIEWS and
// generatorCharts), and a series with no drawable value is left out before it reaches the chart.
import {
  ChipGroup,
  PlotCard,
  SubTabs,
  formatNumber,
  pick,
  useShellLang,
  useWorkbenchState,
  type BiText,
  type FormatOptions,
  type ShellColorToken,
} from '@fasl-work/caos-app-shell';
import { UPlotChart, type ChartSeries, type UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { useMemo, type ReactElement, type ReactNode } from 'react';
import type {
  C04CycleRung,
  C04Family,
  C04MarkovRung,
  C04MomentumRung,
  C04Performance,
  C04Rate,
  C04Simulation,
  C04ThinRung,
  C04WithdrawalsRung,
  VariantArtifact,
} from '../../lib/contract.types';
import { REPLAY, provenanceOf } from '../model';
import { Pending } from '../Pending';
import { MatrixMap, type MapScale } from './MatrixMap';
import {
  DEFINITION_COLOR,
  DEFINITION_LABEL,
  ESMA_DEFINITIONS,
  ESTIMATORS,
  ESTIMATOR_COLOR,
  ESTIMATOR_LABEL,
  GRADES,
  GRADE_AXIS,
  N_GRADES,
  isFamily,
  type C04Sel,
  type Estimator,
  type FamilyVariant,
} from './selection';

type Lang = 'en' | 'es';

// ---------------------------------------------------------------------------------------------------------------------
// constants the views state, each checked against the artifacts by FamilyViews.test.tsx

/** S&P's EU entity, whose pooled annual CEREP counts the families' generator is fitted on (sp.json's outputs.agency). */
export const SP_ENTITY = { code: 'STPGB', name: "Standard & Poor's Credit Market Services Europe Limited" } as const;
/** ESMA's attribution for CEREP (the manifest's source_details['esma-cerep'].attribution, read from there first). */
const CEREP_ATTRIBUTION = 'Source: ESMA CEREP; tables transformed by Contraste';
/** The momentum rung whose fitted hazard coefficient matches dos Reis, Pfeuffer and Smith's estimate on Moody's data
 * (research dossier 13 section 16; the momentum artifact's findings). */
export const EMPIRICAL_ALPHA = 0.125;
/** dos Reis, Pfeuffer and Smith's hazard coefficient on Moody's data (their Table 2: 0.33010), as the findings cite it. */
export const DOS_REIS_C = 0.33;
/** riskvalidation's size bound: the level plus this many Monte Carlo SEs (harness.rates.Z_SIZE, one-sided 0.1%). */
const Z_SIZE = 3.090232306167813;
/** The largest rejection rate over n repetitions consistent with a true size of at most alpha (harness size_bound). */
export const sizeBound = (alpha: number, n: number): number => alpha + Z_SIZE * Math.sqrt((alpha * (1 - alpha)) / n);

const AT5 = 'p<0.05';
const AT1 = 'p<0.01';

// ---------------------------------------------------------------------------------------------------------------------
// text and numbers

const t = (en: string, es: string): BiText => ({ en, es });
/** The string of the current language (both are written at the call, the current one shown). */
const L = (lang: Lang, en: string, es: string): string => (lang === 'es' ? es : en);
/** A BiText whose two strings carry numbers formatted in their own language. */
const bi = (f: (l: Lang) => string): BiText => ({ en: f('en'), es: f('es') });
const na = (lang: Lang) => formatNumber(null, lang);
const num = (lang: Lang, v: number | null | undefined, opts: FormatOptions = {}) => formatNumber(v, lang, opts);
/** A fixed level in percent, as the text names it ("95 %"). */
const pct0 = (lang: Lang, v: number) => formatNumber(v, lang, { percent: true, decimals: 0 });
/** A probability (a PD, a bias, an error) in percent at three significant digits, for a table whose header says %:
 * 0.0000657 prints 0.00657. */
const pctSig = (lang: Lang, v: number | null | undefined) => (v === null || v === undefined ? na(lang) : formatNumber(v * 100, lang, { digits: 3 }));
/** The same with its sign, for prose: "0.00657 %". */
const pctText = (lang: Lang, v: number | null | undefined) => formatNumber(v, lang, { percent: true, digits: 3 });

/** An estimate and its Monte Carlo SE, already in the unit printed: the SE at two significant digits and the estimate
 * at the same decimals (an estimate is no more precise than its error); a zero or missing SE leaves the estimate at
 * three significant digits. */
function withSe(lang: Lang, value: number, se: number | null | undefined): string {
  const decimals = se !== null && se !== undefined && Number.isFinite(se) && se > 0 ? Math.min(8, Math.max(0, 1 - Math.floor(Math.log10(se)))) : null;
  if (decimals === null) return `${formatNumber(value, lang, { digits: 3 })} (${se === null || se === undefined ? na(lang) : formatNumber(se, lang, { digits: 2 })})`;
  return `${formatNumber(value, lang, { decimals })} (${formatNumber(se, lang, { decimals })})`;
}

/** A mean (or bias) and its Monte Carlo SE, both in percent: "1.555 (0.021)". */
export function meanSe(lang: Lang, v: number | null | undefined, se: number | null | undefined): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return na(lang);
  return withSe(lang, v * 100, se === null || se === undefined ? se : se * 100);
}

/** A harness rate and its Monte Carlo SE, in percent with two decimals: "10.00 (2.12)". */
export function rateSe(lang: Lang, r: C04Rate | null | undefined): string {
  if (!r || !Number.isFinite(r.rate)) return na(lang);
  return `${formatNumber(r.rate * 100, lang, { decimals: 2 })} (${formatNumber(r.se * 100, lang, { decimals: 2 })})`;
}

/** A relative bias (bias over the truth) and its Monte Carlo SE, in percent: "-33.88 (0.75)". */
export function relativeSe(lang: Lang, bias: number | null | undefined, se: number | null | undefined, truth: number): string {
  if (bias === null || bias === undefined || !Number.isFinite(bias) || !(truth > 0)) return na(lang);
  return withSe(lang, (100 * bias) / truth, se === null || se === undefined ? se : (100 * se) / truth);
}

const TEST_LABEL: Record<string, BiText> = {
  'rating.time_homogeneity': t('Time homogeneity', 'Homogeneidad temporal'),
  'rating.markov_order': t('Markov order', 'Orden de Markov'),
  'rating.matrix_reference': t('Against the reference matrix', 'Contra la matriz de referencia'),
  'rating.momentum': t('Momentum hazard', 'Riesgo de momentum'),
};
const TEST_COLOR: Record<string, ShellColorToken> = {
  'rating.time_homogeneity': '--color-accent',
  'rating.markov_order': '--color-magenta',
  'rating.matrix_reference': '--color-accent-2',
  'rating.momentum': '--color-good',
};

type Analytic = 'wald' | 'agresti_coull' | 'jeffreys';
type Interval = Analytic | 'bootstrap';
const INTERVAL_LABEL: Record<Interval, BiText> = {
  wald: t('Wald', 'Wald'),
  agresti_coull: t('Agresti-Coull', 'Agresti-Coull'),
  jeffreys: t('Jeffreys', 'Jeffreys'),
  bootstrap: t('Bootstrap', 'Bootstrap'),
};
const INTERVAL_COLOR: Record<Interval, ShellColorToken> = { wald: '--color-bad', agresti_coull: '--color-accent-2', jeffreys: '--color-accent', bootstrap: '--color-magenta' };
const ANALYTIC: Analytic[] = ['wald', 'agresti_coull', 'jeffreys'];

/** One colour per rung of a five-rung ladder (the marks' amber is left to the marks). */
const RUNG_COLOR: ShellColorToken[] = ['--color-fg-subtle', '--color-accent-2', '--color-accent', '--color-magenta', '--color-bad'];

const UNIT_TEXT: Record<string, BiText> = {
  unitless: t('unitless', 'sin unidad'),
  ratio: t('a multiplier', 'un multiplicador'),
  count: t('obligors', 'deudores'),
};

// ---------------------------------------------------------------------------------------------------------------------
// charts: a spec per chart, what reaches the chart, and the card around it

/** One chart of a view: what UPlotChart draws, before the series without a drawable value are left out. */
export interface ChartSpec {
  /** the chart's name within its view */
  key: string;
  x: UPlotChartProps['x'];
  y: UPlotChartProps['y'];
  series: ChartSeries[];
  marks?: UPlotChartProps['marks'];
}

/** The series a chart can draw: non-finite values become gaps, and on a log axis so do zeros and negatives (counted,
 * so the card can say so); a series left with no value is left out. */
export function drawable(spec: ChartSpec): { series: ChartSeries[]; dropped: number } {
  let dropped = 0;
  const series = spec.series
    .map((s) => ({
      ...s,
      values: s.values.map((x) => {
        if (x === null || !Number.isFinite(x)) return null;
        if (spec.y.log && x <= 0) {
          dropped += 1;
          return null;
        }
        return x;
      }),
    }))
    .filter((s) => s.values.some((x) => x !== null));
  return { series, dropped };
}

/** True when the positive values span a decade or more: such a chart is drawn on a log axis. */
function spansDecades(values: Array<number | null>[]): boolean {
  const pos = values.flat().filter((x): x is number => x !== null && Number.isFinite(x) && x > 0);
  return pos.length >= 2 && Math.max(...pos) / Math.min(...pos) >= 10;
}

/** A PD axis in percent, on a log scale where its values span decades; short for a chart on the narrow side, whose
 * axis title must fit a short plot. */
function pdAxis(label: (l: Lang) => string, values: Array<number | null>[], short = false): UPlotChartProps['y'] {
  const log = spansDecades(values);
  const scale = (l: Lang) => (short ? ', log' : L(l, ', log scale', ', escala log.'));
  return {
    label: bi((l) => `${label(l)} (%${log ? scale(l) : ''})`),
    log,
    format: { percent: true, digits: 3 },
  };
}

const RATE_AXIS: UPlotChartProps['y'] = { label: t('Rejection rate (%)', 'Tasa de rechazo (%)'), range: [0, 1], format: { percent: true, digits: 3 } };

function gradeX(): UPlotChartProps['x'] {
  return { values: GRADES.map((_, i) => i + 1), label: GRADE_AXIS, format: { decimals: 0 } };
}

const gradeMark = (g: number) => ({ x: g + 1, label: GRADES[g] });

/** Two Monte Carlo SEs below and above a named quantity, dashed in its colour; the short legend labels ("EM - 2 MC
 * SE") keep a key of several bands on two lines in a narrow card. */
function seBand(name: BiText, values: Array<number | null>, se: Array<number | null>, color: ShellColorToken, scale = 1): ChartSeries[] {
  const at = (sign: number) => values.map((v, i) => (v === null || se[i] === null ? null : (v + sign * 2 * (se[i] as number)) * scale));
  return [
    { label: bi((l) => `${pick(name, l)} - 2 ${L(l, 'MC SE', 'EE MC')}`), values: at(-1), color, width: 1, dash: [3, 3] },
    { label: bi((l) => `${pick(name, l)} + 2 ${L(l, 'MC SE', 'EE MC')}`), values: at(1), color, width: 1, dash: [3, 3] },
  ];
}

const flat = (xs: readonly unknown[], v: number) => xs.map(() => v);

/** What a chart card shows when nothing of its chart can be drawn: the values the artifact holds, as a table. */
function SpecTable({ spec }: { spec: ChartSpec }) {
  const lang = useShellLang();
  return (
    <table className="caos-table ct-wrap-head" data-table={`fallback-${spec.key}`}>
      <thead>
        <tr>
          <th className="ct-text">{pick(spec.x.label, lang)}</th>
          {spec.series.map((s, i) => (
            <th key={i}>{pick(s.label, lang)}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {spec.x.values.map((x, j) => (
          <tr key={j}>
            <td className="ct-text">{num(lang, x, spec.x.format ?? {})}</td>
            {spec.series.map((s, i) => (
              <td key={i}>{num(lang, s.values[j], spec.y.format ?? {})}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** A filling card with one chart; a chart with nothing to draw says why and shows the values as a table instead. */
function ChartCard({ v, spec, title, note }: { v: FamilyVariant; spec: ChartSpec; title: BiText; note: string }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const d = useMemo(() => drawable(spec), [spec]);
  const prov = provenanceOf(v.provenance.truth_status);
  if (d.series.length === 0) {
    const why = L(
      lang,
      'Nothing to draw: no value of this chart is defined in the artifact (an estimate needs two defined repetitions, a log scale a positive value); the table lists what it holds.',
      'Nada que dibujar: ningún valor de este gráfico está definido en el artefacto (una estimación necesita dos repeticiones definidas, una escala logarítmica un valor positivo); la tabla muestra lo que contiene.',
    );
    return (
      <PlotCard fill title={title} lane={REPLAY} provenance={prov} dataKey={stateKey} note={`${note} ${why}`}>
        <div className="ct-scroll">
          <SpecTable spec={spec} />
        </div>
      </PlotCard>
    );
  }
  const gaps = d.dropped > 0 ? ` ${L(lang, 'Zeros cannot sit on a log scale and are left as gaps.', 'Los ceros no caben en una escala logarítmica y quedan como vacíos.')}` : '';
  return (
    <PlotCard fill title={title} lane={REPLAY} provenance={prov} dataKey={stateKey} note={`${note}${gaps}`}>
      <UPlotChart height="fill" x={spec.x} y={spec.y} series={d.series} marks={spec.marks} />
    </PlotCard>
  );
}

/** A filling card holding tables that scroll inside it. */
function TableCard({ v, title, note, children }: { v: FamilyVariant; title: BiText; note: string; children: ReactNode }) {
  const stateKey = useWorkbenchState()?.stateKey;
  return (
    <PlotCard fill title={title} lane={REPLAY} provenance={provenanceOf(v.provenance.truth_status)} dataKey={stateKey} note={note}>
      <div className="ct-scroll">{children}</div>
    </PlotCard>
  );
}

/** A view: the main drawing on the left; on the right a second drawing over the numbers, three shares of the column to
 * two. Measured in the app at 1280 x 800: a table at its own height under the second chart left the chart no height,
 * an even split left it 150 px, and in a column of two fifths of the row the cards' heads wrapped and the chart kept
 * 60 px of plot; two even columns and the 3 to 2 split keep the chart readable there, and the table still covers most
 * of its card on a 2560 x 1440 screen (the gate's stage floor). Half the row also suits the Model view's matrix, whose
 * cells print their values from 40 px wide: 41 px at 1280 x 800. */
function ViewRow({ left, top, bottom }: { left: ReactNode; top?: ReactNode; bottom: ReactNode }) {
  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col">{left}</div>
      <div className="ct-col">
        {top ? (
          <>
            <div className="ct-col ct-share-3">{top}</div>
            <div className="ct-col ct-share-2">{bottom}</div>
          </>
        ) : (
          bottom
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// reading the artifact

function familyOf(sel: C04Sel | null): FamilyVariant | null {
  const v = sel?.data.variant as VariantArtifact<unknown> | undefined;
  return v && isFamily(v) ? v : null;
}

function rungsOf<R>(v: FamilyVariant, family: C04Family): R[] | null {
  return v.outputs.family === family ? (v.outputs.rungs as unknown as R[]) : null;
}

const markovRung = (v: FamilyVariant): C04MarkovRung | null => rungsOf<C04MarkovRung>(v, 'markov')?.[0] ?? null;

/** A test's simulation row at a rung (the Markov family's rows have no rung; the order test's forms are apart). */
function simAt(v: FamilyVariant, testId: string, rung: number | null): C04Simulation | undefined {
  return v.outputs.simulations.find((s) => s.test_id === testId && s.rung === rung && !s.key.includes('@form-'));
}

/** The repetitions behind the family's rates, and the largest Monte Carlo SE a rate of that many can have. */
function repetitions(v: FamilyVariant): { n: number; maxSe: number } {
  const n = v.outputs.design.reps;
  return { n, maxSe: n > 0 ? 0.5 / Math.sqrt(n) : 0 };
}

const attributionOf = (sel: C04Sel): string => sel.data.manifest.source_details?.['esma-cerep']?.attribution ?? CEREP_ATTRIBUTION;

/** The sentence every family view carries: where its truth comes from, the entity and ESMA's attribution. */
function truthNote(lang: Lang, sel: C04Sel): string {
  return L(
    lang,
    `The truth is the EM generator of the pooled annual CEREP counts of S&P's EU entity (${SP_ENTITY.name}); ${attributionOf(sel)}.`,
    `La verdad es el generador EM de los conteos anuales agrupados de CEREP de la entidad UE de S&P (${SP_ENTITY.name}); atribución: ${attributionOf(sel)}.`,
  );
}

/** The default definition of the families' PDs: the chain's absorbing state, fitted on the transition page's default
 * column with withdrawals removed. */
const definitionNote = (lang: Lang) =>
  L(
    lang,
    `Default: the chain's absorbing state, fitted on the transition page's default column with withdrawals removed (${pick(DEFINITION_LABEL.d4, 'en')}).`,
    `Incumplimiento: el estado absorbente de la cadena, ajustado sobre la columna de incumplimiento de la página de transiciones, sin los retiros (${pick(DEFINITION_LABEL.d4, 'es')}).`,
  );

/** What the design means for the family: one chain drawn again and again with a defect planted along a ladder, the
 * null itself, or no draw at all. */
function designNote(lang: Lang, family: C04Family): string {
  if (family === 'thin') {
    return L(
      lang,
      "Nothing is drawn: each rung is a cohort size, and the intervals' coverage, length and overlap are enumerated over the binomial counts at the true one-year PD. The obligors column is S&P's mean CEREP cohort, the cohort the other families draw.",
      'No se sortea nada: cada peldaño es un tamaño de cohorte, y la cobertura, la longitud y el traslape de los intervalos se enumeran sobre los conteos binomiales a la PD anual verdadera. La columna de deudores es la cohorte media de S&P en CEREP, la que sortean las demás familias.',
    );
  }
  if (family === 'markov') {
    return L(
      lang,
      "The same chain and cohorts in every repetition: the obligors per grade are S&P's mean CEREP cohort, and the chain is Markov and stable, the null every estimator and test is measured on.",
      'La misma cadena y cohortes en cada repetición: los deudores por grado son la cohorte media de S&P en CEREP, y la cadena es de Markov y estable, la nula sobre la que se mide cada estimador y cada prueba.',
    );
  }
  return L(
    lang,
    "The same chain and cohorts in every repetition: the obligors per grade are S&P's mean CEREP cohort; each rung plants the family's defect at one strength, on a seed of its own.",
    'La misma cadena y cohortes en cada repetición: los deudores por grado son la cohorte media de S&P en CEREP; cada peldaño planta el defecto de la familia con una fuerza, con una semilla propia.',
  );
}

function NotThisFamily() {
  const lang = useShellLang();
  return (
    <p className="ct-note">
      {L(lang, 'This view reads a generator family of C04; the selected variant is not one.', 'Esta vista lee una familia generadora de C04; la variante elegida no lo es.')}
    </p>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// Model: the true chain every family simulates

const SCALES: Array<{ id: MapScale; label: BiText; hint: BiText }> = [
  { id: 'migrations', label: t('Migrations', 'Migraciones'), hint: t('Linear, the diagonal kept out of the range: the moves between grades stand out.', 'Lineal, con la diagonal fuera del rango: destacan los movimientos entre grados.') },
  { id: 'linear', label: t('Linear', 'Lineal'), hint: t('Every cell on one linear scale.', 'Cada celda en una misma escala lineal.') },
  { id: 'log', label: t('Log', 'Log.'), hint: t('Every cell on a log scale, zeros at its bottom.', 'Cada celda en escala logarítmica, los ceros al fondo.') },
];

/** The true PD by grade at one and five years, on a log axis, the chosen grade marked. */
export function generatorCharts(v: FamilyVariant, sel: C04Sel): ChartSpec[] {
  const g = v.outputs.generator;
  return [
    {
      key: 'true-pd',
      x: gradeX(),
      y: { label: t('PD (%, log)', 'PD (%, log)'), log: true, format: { percent: true, digits: 2 } },
      series: [
        { label: t('One year, exp(Q)', 'Un año, exp(Q)'), values: [...g.pd_1y], color: '--color-accent', width: 2.2 },
        { label: t('Five years, exp(5Q)', 'Cinco años, exp(5Q)'), values: [...g.pd_5y], color: '--color-magenta', width: 2.2, dash: [6, 3] },
      ],
      marks: [gradeMark(sel.grade)],
    },
  ];
}

/** The Model group of every generator family: the true one-year matrix, the true PDs and the design. */
export function GeneratorView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = familyOf(sel);
  const charts = useMemo(() => (v && sel ? generatorCharts(v, sel) : null), [v, sel]);
  if (!sel) return <Pending />;
  if (!v || !charts) return <NotThisFamily />;
  const o = v.outputs;
  const prov = provenanceOf(v.provenance.truth_status);
  const att = attributionOf(sel);
  const ladder = o.ladder;
  const design = o.design;
  const entity = `${SP_ENTITY.name} (${SP_ENTITY.code})`;
  const rows: Array<[string, string]> = [
    [
      L(lang, 'Generator', 'Generador'),
      L(lang, "EM generator of the pooled annual CEREP counts of S&P's EU entity (riskvalidation.transitions.em)", 'Generador EM de los conteos anuales agrupados de CEREP de la entidad UE de S&P (riskvalidation.transitions.em)'),
    ],
    [L(lang, 'Entity', 'Entidad'), entity],
    [
      L(lang, 'Years observed', 'Años observados'),
      L(lang, `${num(lang, design.years)}, snapshots at ${design.snapshots.map((s) => num(lang, s)).join(', ')}`, `${num(lang, design.years)}, instantáneas en ${design.snapshots.map((s) => num(lang, s)).join('; ')}`),
    ],
    [
      L(lang, 'Repetitions per rung', 'Repeticiones por peldaño'),
      design.reps > 0 ? num(lang, design.reps) : L(lang, 'none: exact, by enumerating the binomial counts', 'ninguna: exacto, enumerando los conteos binomiales'),
    ],
    [
      L(lang, 'Ladder', 'Escalera'),
      ladder
        ? `${pick(ladder.name, lang)}: ${ladder.values.map((x) => num(lang, x)).join(lang === 'es' ? '; ' : ', ')} (${pick(UNIT_TEXT[ladder.unit] ?? ladder.unit, lang)})`
        : L(lang, 'none: the chain is Markov and stable (the null)', 'ninguna: la cadena es de Markov y estable (la nula)'),
    ],
    [
      L(lang, 'Seeds', 'Semillas'),
      design.seed_key
        ? L(lang, `case seed ${num(lang, v.provenance.seed)}, one seed per rung from the key ${design.seed_key}`, `semilla del caso ${num(lang, v.provenance.seed)}, una semilla por peldaño desde la clave ${design.seed_key}`)
        : L(lang, 'none: nothing is drawn', 'ninguna: no se sortea nada'),
    ],
    [L(lang, 'Engine', 'Motor'), `riskvalidation ${v.provenance.riskvalidation_version ?? ''}`.trim()],
  ];
  return (
    <ViewRow
      left={
        <PlotCard
          fill
          title={t('The true one-year matrix, exp(Q)', 'La matriz anual verdadera, exp(Q)')}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={L(
            lang,
            `Every repetition simulates this chain: the one-year transition probabilities of the true generator Q, the EM generator of the pooled annual CEREP counts of S&P's EU entity, ${entity}. Rows: the grade at the start of the year; columns: the state at its end, default (D) last; percent. ${definitionNote('en')} A row picks its grade. ${att}.`,
            `Cada repetición simula esta cadena: las probabilidades de transición a un año del generador verdadero Q, el generador EM de los conteos anuales agrupados de CEREP de la entidad UE de S&P, ${entity}. Filas: el grado al inicio del año; columnas: el estado al final, con el incumplimiento (D) al último; porcentaje. ${definitionNote('es')} Una fila elige su grado. Atribución: ${att}.`,
          )}
        >
          {/* the scale above the map, not in the card's head: there the title and the lane badges leave it no room (the
              agency matrix view measured the head overflowing in Spanish at 1280 x 800) */}
          <div className="ct-stack">
            <div className="ct-stack-natural" data-controls="c04-map">
              <ChipGroup id="c04-map-scale" label={t('Colour scale', 'Escala de color')} options={SCALES} value={sel.mapScale} onChange={(id) => sel.act.setMapScale(id as MapScale)} />
            </div>
            <MatrixMap
              label={t('The true one-year matrix', 'La matriz anual verdadera')}
              rows={[...GRADES]}
              cols={[...GRADES, 'D']}
              values={o.generator.one_year_matrix.slice(0, N_GRADES).map((r) => [...r])}
              scale={sel.mapScale}
              diagonal={GRADES.map((_, i) => i)}
              selectedRow={sel.grade}
              onPickRow={sel.act.setGrade}
            />
          </div>
        </PlotCard>
      }
      top={
        <ChartCard
          v={v}
          spec={charts[0]}
          title={t('True PD by grade, one and five years', 'PD verdadera por grado, a uno y cinco años')}
          note={L(
            lang,
            `The default column of exp(Q) and exp(5Q), percent on a log scale (${pick(DEFINITION_LABEL.d4, 'en')}); ${GRADES[sel.grade]} marked. CEREP counts of ${SP_ENTITY.name}; ${att}.`,
            `La columna de incumplimiento de exp(Q) y exp(5Q), en porcentaje y escala logarítmica (${pick(DEFINITION_LABEL.d4, 'es')}); se marca ${GRADES[sel.grade]}. Conteos de CEREP de ${SP_ENTITY.name}; atribución: ${att}.`,
          )}
        />
      }
      bottom={
        <TableCard
          v={v}
          title={t('The design', 'El diseño')}
          note={L(
            lang,
            `${designNote('en', o.family)} The exit rate is minus Q's diagonal, per year; the PDs are exp(Q)'s and exp(5Q)'s, in percent. ${att}.`,
            `${designNote('es', o.family)} La tasa de salida es menos la diagonal de Q, por año; las PD son las de exp(Q) y exp(5Q), en porcentaje. Atribución: ${att}.`,
          )}
        >
          <table className="caos-table" data-table="family-design">
            <tbody>
              {rows.map(([k, val]) => (
                <tr key={k}>
                  <td className="ct-text">{k}</td>
                  <td className="ct-text">{val}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head" data-table="family-by-grade">
            <thead>
              <tr>
                <th className="ct-text">{L(lang, 'Grade', 'Grado')}</th>
                <th>{L(lang, 'Obligors', 'Deudores')}</th>
                <th>{L(lang, 'Exit rate (per year)', 'Tasa de salida (por año)')}</th>
                <th>{L(lang, 'PD one year (%)', 'PD a un año (%)')}</th>
                <th>{L(lang, 'PD five years (%)', 'PD a cinco años (%)')}</th>
              </tr>
            </thead>
            <tbody>
              {GRADES.map((g, i) => (
                <tr key={g} className={i === sel.grade ? 'ct-current' : undefined}>
                  <td className="ct-text">{g}</td>
                  <td>{num(lang, o.generator.obligors[i])}</td>
                  <td>{num(lang, -o.generator.q[i][i], { digits: 3 })}</td>
                  <td>{pctSig(lang, o.generator.pd_1y[i])}</td>
                  <td>{pctSig(lang, o.generator.pd_5y[i])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableCard>
      }
    />
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// markov: the estimators, the zeros, the tests' size, the intervals' coverage

/** The RMSE of each estimator by grade (log) against the true PD, and each one's bias over the truth (linear), the
 * rail's estimator highlighted with two Monte Carlo SEs either side of its bias. */
export function markovEstimatorCharts(v: FamilyVariant, sel: C04Sel): ChartSpec[] {
  const r = markovRung(v);
  if (!r) return [];
  const truth = v.outputs.generator.pd_1y;
  const width = (e: Estimator) => (e === sel.estimator ? 3 : 1.4);
  const relative = (xs: Array<number | null>) => xs.map((b, g) => (b === null ? null : b / truth[g]));
  const chosen = r.estimators[sel.estimator];
  return [
    {
      key: 'rmse',
      x: gradeX(),
      y: { label: t('RMSE of the one-year PD (%, log scale)', 'RMSE de la PD a un año (%, escala log.)'), log: true, format: { percent: true, digits: 2 } },
      series: [
        ...ESTIMATORS.map((e) => ({ label: ESTIMATOR_LABEL[e], values: [...r.estimators[e].rmse], color: ESTIMATOR_COLOR[e], width: width(e) })),
        { label: t('True one-year PD', 'PD anual verdadera'), values: [...truth], color: '--color-fg-subtle' as ShellColorToken, width: 1.2, dash: [6, 4] },
      ],
      marks: [gradeMark(sel.grade)],
    },
    {
      key: 'bias',
      x: gradeX(),
      y: { label: t('Relative bias (%)', 'Sesgo relativo (%)'), format: { percent: true, digits: 3 } },
      series: [
        ...ESTIMATORS.map((e) => ({ label: ESTIMATOR_LABEL[e], values: relative(r.estimators[e].bias), color: ESTIMATOR_COLOR[e], width: width(e) })),
        ...seBand(ESTIMATOR_LABEL[sel.estimator], relative(chosen.bias), relative(chosen.bias_mcse), ESTIMATOR_COLOR[sel.estimator]),
        { label: t('Unbiased', 'Insesgado'), values: flat(truth, 0), color: '--color-fg-subtle', width: 1, dash: [2, 4] },
      ],
      marks: [gradeMark(sel.grade)],
    },
  ];
}

export function MarkovEstimatorsView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const v = familyOf(sel);
  const charts = useMemo(() => (v && sel ? markovEstimatorCharts(v, sel) : []), [v, sel]);
  if (!sel) return <Pending />;
  const r = v ? markovRung(v) : null;
  if (!v || !r || charts.length < 2) return <NotThisFamily />;
  const g = sel.grade;
  const truth = v.outputs.generator.pd_1y[g];
  const { n } = repetitions(v);
  const label = pick(ESTIMATOR_LABEL[sel.estimator], lang);
  const conv = r.em.converged;
  const converged = (l: Lang) =>
    `${formatNumber(conv.rate, l, { percent: true, decimals: 1 })} ${L(l, 'of them', 'de ellas')} (${L(l, 'Monte Carlo SE', 'EE de Monte Carlo')} ${formatNumber(100 * conv.se, l, { decimals: 1 })} ${L(l, 'points', 'puntos')})`;
  return (
    <ViewRow
      left={
        <ChartCard
          v={v}
          spec={charts[0]}
          title={t('RMSE of the one-year PD by grade, every estimator', 'RMSE de la PD a un año por grado, cada estimador')}
          note={L(
            lang,
            `${num(lang, n)} repetitions of five years observed at annual snapshots, percent on a log scale, against the true PD (dashed): where an estimator's RMSE is above the PD, one estimate says little about it. Thick: the rail's estimator (${label}); ${GRADES[g]} is marked. Cohort: the five annual cohorts pooled (Anderson and Goodman (2.8)); duration: the transition times; EM: the snapshots; diagonal, weighted and JLT: the log of the pooled matrix repaired (Israel, Rosenthal and Wei). ${definitionNote('en')} ${truthNote('en', sel)}`,
            `${num(lang, n)} repeticiones de cinco años observados en instantáneas anuales, en porcentaje y escala logarítmica, contra la PD verdadera (segmentada): donde la RMSE de un estimador supera la PD, una estimación dice poco de ella. Gruesa: el estimador del panel (${label}); se marca ${GRADES[g]}. Cohortes: las cinco cohortes anuales agrupadas (Anderson y Goodman (2.8)); duración: los tiempos de transición; EM: las instantáneas; diagonal, ponderado y JLT: el logaritmo de la matriz agrupada reparado (Israel, Rosenthal y Wei). ${definitionNote('es')} ${truthNote('es', sel)}`,
          )}
        />
      }
      top={
        <ChartCard
          v={v}
          spec={charts[1]}
          title={t('Bias over the true PD by grade', 'Sesgo sobre la PD verdadera por grado')}
          note={L(
            lang,
            "The mean estimate minus the truth, over the truth, in percent; the rail's estimator thick, with two Monte Carlo SEs either side (dashed).",
            'La estimación media menos la verdad, sobre la verdad, en porcentaje; el estimador del panel en grueso, con dos EE de Monte Carlo a cada lado (segmentadas).',
          )}
        />
      }
      bottom={
        <TableCard
          v={v}
          title={bi((l) => `${L(l, 'Every estimator at', 'Cada estimador en')} ${GRADES[g]}`)}
          note={L(
            lang,
            `True one-year PD of ${GRADES[g]}: ${pctText('en', truth)}. Percent, each with its Monte Carlo SE in parentheses, over ${num('en', r.estimators.cohort.n[g])} defined repetitions; the zero share is the share of repetitions with a PD of exactly 0. EM converged in ${converged('en')}, after ${num('en', r.em.iterations_mean, { digits: 3 })} iterations on average and ${num('en', r.em.iterations_max)} at most.`,
            `PD anual verdadera de ${GRADES[g]}: ${pctText('es', truth)}. Porcentaje, cada uno con su EE de Monte Carlo entre paréntesis, sobre ${num('es', r.estimators.cohort.n[g])} repeticiones definidas; la fracción de ceros es la fracción de repeticiones con PD exactamente 0. EM convergió en ${converged('es')}, tras ${num('es', r.em.iterations_mean, { digits: 3 })} iteraciones en promedio y ${num('es', r.em.iterations_max)} a lo más.`,
          )}
        >
          <table className="caos-table ct-wrap-head" data-table="markov-estimators">
            <thead>
              <tr>
                <th className="ct-text">{L(lang, 'Estimator', 'Estimador')}</th>
                <th>{L(lang, 'Mean, %', 'Media, %')}</th>
                <th>{L(lang, 'Bias, %', 'Sesgo, %')}</th>
                <th className="ct-room-only">{L(lang, 'Empirical SE, %', 'EE empírico, %')}</th>
                <th>{L(lang, 'RMSE, %', 'RMSE, %')}</th>
                <th>{L(lang, 'Zeros, %', 'Ceros, %')}</th>
              </tr>
            </thead>
            <tbody>
              {ESTIMATORS.map((e) => {
                const p = r.estimators[e];
                return (
                  <tr key={e} data-estimator={e} className={e === sel.estimator ? 'ct-current' : undefined}>
                    <td className="ct-text">{pick(ESTIMATOR_LABEL[e], lang)}</td>
                    <td>{meanSe(lang, p.mean[g], p.bias_mcse[g])}</td>
                    <td>{meanSe(lang, p.bias[g], p.bias_mcse[g])}</td>
                    <td className="ct-room-only">{meanSe(lang, p.empirical_se[g], p.empirical_se_mcse[g])}</td>
                    <td>{meanSe(lang, p.rmse[g], p.rmse_mcse[g])}</td>
                    <td>{rateSe(lang, p.zero[g])}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </TableCard>
      }
    />
  );
}

/** The share of repetitions with a PD of exactly zero, by grade and estimator (the rail's estimator with its Wilson
 * interval); and the defaults the pooled cohort expects, its mean obligor-years times the true PD, against one. */
export function markovZeroCharts(v: FamilyVariant, sel: C04Sel): ChartSpec[] {
  const r = markovRung(v);
  if (!r) return [];
  const chosen = r.estimators[sel.estimator].zero;
  const name = ESTIMATOR_LABEL[sel.estimator];
  const truth = v.outputs.generator.pd_1y;
  const x = gradeX();
  return [
    {
      key: 'zeros',
      x,
      y: { label: t('Repetitions with a PD of exactly zero (%)', 'Repeticiones con PD exactamente cero (%)'), range: [0, 1], format: { percent: true, digits: 3 } },
      series: [
        ...ESTIMATORS.map((e) => ({ label: ESTIMATOR_LABEL[e], values: r.estimators[e].zero.map((z) => z.rate), color: ESTIMATOR_COLOR[e], width: e === sel.estimator ? 3 : 1.4 })),
        { label: bi((l) => `${pick(name, l)}, Wilson ${pct0(l, 0.95)} ${L(l, 'low', 'inferior')}`), values: chosen.map((z) => z.wilson_low), color: ESTIMATOR_COLOR[sel.estimator], width: 1, dash: [3, 3] },
        { label: bi((l) => `${pick(name, l)}, Wilson ${pct0(l, 0.95)} ${L(l, 'high', 'superior')}`), values: chosen.map((z) => z.wilson_high), color: ESTIMATOR_COLOR[sel.estimator], width: 1, dash: [3, 3] },
      ],
      marks: [gradeMark(sel.grade)],
    },
    {
      key: 'expected-defaults',
      x,
      y: { label: t('Defaults (log)', 'Incumpl. (log)'), log: true, format: { digits: 3 } },
      series: [
        { label: t('Obligor-years times the true PD', 'Años-deudor por la PD verdadera'), values: r.obligor_years.map((n, g) => n * truth[g]), color: '--color-fg', width: 2.4 },
        { label: t('One default', 'Un incumplimiento'), values: flat(x.values, 1), color: '--color-fg-subtle', width: 1, dash: [2, 4] },
      ],
      marks: [gradeMark(sel.grade)],
    },
  ];
}

export function MarkovZerosView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const v = familyOf(sel);
  const charts = useMemo(() => (v && sel ? markovZeroCharts(v, sel) : []), [v, sel]);
  if (!sel) return <Pending />;
  const r = v ? markovRung(v) : null;
  if (!v || !r || charts.length < 2) return <NotThisFamily />;
  const { n } = repetitions(v);
  return (
    <ViewRow
      left={
        <ChartCard
          v={v}
          spec={charts[0]}
          title={t('One-year PDs of exactly zero', 'PD a un año exactamente cero')}
          note={L(
            lang,
            `The share of the ${num('en', n)} repetitions in which each estimator's one-year PD is exactly 0, in percent: a pooled cohort without a default in a grade gives 0, the generator estimators give a positive PD. Thick: the rail's estimator, with its ${pct0('en', 0.95)} Wilson interval (dashed). ${definitionNote('en')} ${truthNote('en', sel)}`,
            `La fracción de las ${num('es', n)} repeticiones en que la PD a un año de cada estimador es exactamente 0, en porcentaje: una cohorte agrupada sin incumplimientos en un grado da 0, los estimadores por generador dan una PD positiva. Gruesa: el estimador del panel, con su intervalo de Wilson al ${pct0('es', 0.95)} (segmentadas). ${definitionNote('es')} ${truthNote('es', sel)}`,
          )}
        />
      }
      top={
        <ChartCard
          v={v}
          spec={charts[1]}
          title={t('Why the cohort gives zero: the defaults it expects', 'Por qué la cohorte da cero: los incumplimientos que espera')}
          note={L(
            lang,
            'The mean obligor-years of the pooled cohort times the true PD, log scale: below one (dotted), most repetitions see no default.',
            'Los años-deudor medios de la cohorte agrupada por la PD verdadera, en escala logarítmica: bajo uno (punteada), la mayoría de las repeticiones no ve incumplimientos.',
          )}
        />
      }
      bottom={
        <TableCard
          v={v}
          title={t('Zero shares by grade and estimator', 'Fracción de ceros por grado y estimador')}
          note={L(
            lang,
            "Percent of the repetitions, each with its Monte Carlo SE in parentheses. Obligor-years: the ratings of the five annual cohorts pooled, the cohort estimator's denominator, mean over the repetitions.",
            'Porcentaje de las repeticiones, cada uno con su EE de Monte Carlo entre paréntesis. Años-deudor: las calificaciones de las cinco cohortes anuales agrupadas, el denominador del estimador de cohortes, en promedio sobre las repeticiones.',
          )}
        >
          <table className="caos-table ct-wrap-head" data-table="markov-zeros">
            <thead>
              <tr>
                <th className="ct-text">{L(lang, 'Grade', 'Grado')}</th>
                <th className="ct-wide-only">{L(lang, 'Obligor-years', 'Años-deudor')}</th>
                {ESTIMATORS.map((e) => (
                  <th key={e}>{pick(ESTIMATOR_LABEL[e], lang)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {GRADES.map((gr, g) => (
                <tr key={gr} className={g === sel.grade ? 'ct-current' : undefined}>
                  <td className="ct-text">{gr}</td>
                  <td className="ct-wide-only">{num(lang, r.obligor_years[g], { decimals: 0 })}</td>
                  {ESTIMATORS.map((e) => (
                    <td key={e}>{rateSe(lang, r.estimators[e].zero[g])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </TableCard>
      }
    />
  );
}

/** A Markov-family simulation row's name: the test, and for the order test's forms the form. */
function simName(s: C04Simulation): BiText {
  const base = TEST_LABEL[s.test_id] ?? t(s.test_id, s.test_id);
  if (s.key.endsWith('@form-chi2')) return bi((l) => `${pick(base, l)}, ${L(l, 'chi-square form', 'forma chi-cuadrado')}`);
  if (s.key.endsWith('@form-lr')) return bi((l) => `${pick(base, l)}, ${L(l, 'likelihood-ratio form', 'forma de razón de verosimilitud')}`);
  return base;
}

/** Categorical positions for a few items: one per item from 1, a gap between items that belong to different groups
 * (so a line across them breaks there), half a step of room at each end. */
function categorical<T>(items: T[], group: (a: T) => unknown = () => 0): { x: number[]; at: Array<number | null> } {
  const x: number[] = [0.5];
  const at: Array<number | null> = [null];
  items.forEach((s, i) => {
    if (i > 0 && group(s) !== group(items[i - 1])) {
      x.push(i + 0.5);
      at.push(null);
    }
    x.push(i + 1);
    at.push(i);
  });
  x.push(items.length + 0.5);
  at.push(null);
  return { x, at };
}

/** Every Markov-family rate at 5% and at 1%, with its Wilson interval, against its size bound and the nominal level;
 * the size bound breaks between the rows of different repetitions. */
export function markovSizeCharts(v: FamilyVariant): ChartSpec[] {
  if (v.outputs.family !== 'markov') return [];
  const rows = v.outputs.simulations;
  const pos = categorical(rows, (s) => s.n_rep);
  const along = (f: (s: C04Simulation) => number | null) => pos.at.map((i) => (i === null ? null : f(rows[i])));
  return ([0.05, 0.01] as const).map((alpha) => {
    const rule = alpha === 0.05 ? AT5 : AT1;
    const series: ChartSeries[] = [
      { label: t('Rejection rate', 'Tasa de rechazo'), values: along((s) => s.rates[rule]?.rate ?? null), color: '--color-accent', mode: 'points' },
      { label: bi((l) => `Wilson ${pct0(l, 0.95)}, ${L(l, 'low', 'inferior')}`), values: along((s) => s.rates[rule]?.wilson_low ?? null), color: '--color-fg-subtle', mode: 'points' },
      { label: bi((l) => `Wilson ${pct0(l, 0.95)}, ${L(l, 'high', 'superior')}`), values: along((s) => s.rates[rule]?.wilson_high ?? null), color: '--color-fg-subtle', mode: 'points' },
      { label: t('Size bound', 'Cota de tamaño'), values: along((s) => sizeBound(alpha, s.rates[rule]?.n ?? s.n_rep)), color: '--color-bad', width: 1.6, dash: [6, 3] },
      { label: bi((l) => `${L(l, 'Nominal level', 'Nivel nominal')} ${pct0(l, alpha)}`), values: flat(pos.x, alpha), color: '--color-fg-subtle', width: 1, dash: [2, 4] },
    ];
    return {
      key: `size-${rule}`,
      x: { values: pos.x, label: t('Test (numbered in the note and the table)', 'Prueba (numerada en la nota y la tabla)'), format: { decimals: 0 } },
      y: { label: alpha === 0.05 ? t('Rejection rate (%)', 'Tasa de rechazo (%)') : t('Rate (%)', 'Tasa (%)'), format: { percent: true, digits: 3 } },
      series,
    };
  });
}

export function MarkovSizeView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const v = familyOf(sel);
  const charts = useMemo(() => (v ? markovSizeCharts(v) : []), [v]);
  if (!sel) return <Pending />;
  if (!v || charts.length < 2) return <NotThisFamily />;
  const rows = v.outputs.simulations;
  const numbered = (l: Lang) => rows.map((s, i) => `${i + 1} ${pick(simName(s), l)} (${num(l, s.n_rep)})`).join('; ');
  const holds = (s: C04Simulation, alpha: number, rule: string) => {
    const r = s.rates[rule];
    return r ? r.rate <= sizeBound(alpha, r.n) : null;
  };
  return (
    <ViewRow
      left={
        <ChartCard
          v={v}
          spec={charts[0]}
          title={bi((l) => `${L(l, 'Size of the transition tests on a Markov chain, at', 'Tamaño de las pruebas de transición en una cadena de Markov, al')} ${pct0(l, 0.05)}`)}
          note={L(
            lang,
            `The chain is Markov and stable, so every rejection is a false alarm. Each test's rejection rate in percent (dots) with its ${pct0('en', 0.95)} Wilson interval (small dots), against its size bound (dashed): the level plus 3.09 Monte Carlo SEs at its repetitions, riskvalidation's size_bound. Tests and repetitions: ${numbered('en')}; the order test's two forms run on a seed of their own. The reference matrix is the true one, against the first year's counts. ${truthNote('en', sel)}`,
            `La cadena es de Markov y estable, así que cada rechazo es una falsa alarma. La tasa de rechazo de cada prueba en porcentaje (puntos) con su intervalo de Wilson al ${pct0('es', 0.95)} (puntos pequeños), contra su cota de tamaño (segmentada): el nivel más 3,09 EE de Monte Carlo a sus repeticiones, el size_bound de riskvalidation. Pruebas y repeticiones: ${numbered('es')}; las dos formas de la prueba de orden corren con una semilla propia. La matriz de referencia es la verdadera, contra los conteos del primer año. ${truthNote('es', sel)}`,
          )}
        />
      }
      top={
        <ChartCard
          v={v}
          spec={charts[1]}
          title={bi((l) => `${L(l, 'The same at', 'Lo mismo al')} ${pct0(l, 0.01)}`)}
          note={L(
            lang,
            `The rates at ${pct0('en', 0.01)} against their own size bound, the tests numbered as at ${pct0('en', 0.05)}.`,
            `Las tasas al ${pct0('es', 0.01)} contra su propia cota de tamaño, con las pruebas numeradas como al ${pct0('es', 0.05)}.`,
          )}
        />
      }
      bottom={
        <TableCard
          v={v}
          title={t('Rejection rates and the size bound', 'Tasas de rechazo y la cota de tamaño')}
          note={L(
            lang,
            'Each rate in percent with its Monte Carlo SE in parentheses, its size bound, and whether the test holds its size at both levels.',
            'Cada tasa en porcentaje con su EE de Monte Carlo entre paréntesis, su cota de tamaño, y si la prueba mantiene su tamaño en ambos niveles.',
          )}
        >
          <table className="caos-table ct-wrap-head" data-table="markov-size">
            <thead>
              <tr>
                <th className="ct-text">{L(lang, 'Test', 'Prueba')}</th>
                <th className="ct-room-only">{L(lang, 'Repetitions', 'Repeticiones')}</th>
                <th>{L(lang, `At ${pct0('en', 0.05)}, %`, `Al ${pct0('es', 0.05)}, %`)}</th>
                <th className="ct-room-only">{L(lang, 'Bound, %', 'Cota, %')}</th>
                <th>{L(lang, `At ${pct0('en', 0.01)}, %`, `Al ${pct0('es', 0.01)}, %`)}</th>
                <th className="ct-room-only">{L(lang, 'Bound, %', 'Cota, %')}</th>
                <th>{L(lang, 'Size', 'Tamaño')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((s, i) => {
                const h5 = holds(s, 0.05, AT5);
                const h1 = holds(s, 0.01, AT1);
                const ok = h5 !== false && h1 !== false;
                const verdict = ok
                  ? t('holds', 'se mantiene')
                  : h5 === false && h1 === false
                    ? t('exceeds at both', 'excede en ambos')
                    : h5 === false
                      ? bi((l) => `${L(l, 'exceeds at', 'excede al')} ${pct0(l, 0.05)}`)
                      : bi((l) => `${L(l, 'exceeds at', 'excede al')} ${pct0(l, 0.01)}`);
                return (
                  <tr key={s.key} data-sim={s.key} className={ok ? undefined : 'ct-current'}>
                    <td className="ct-text">{`${i + 1} ${pick(simName(s), lang)}`}</td>
                    <td className="ct-room-only">{num(lang, s.n_rep)}</td>
                    <td>{rateSe(lang, s.rates[AT5])}</td>
                    <td className="ct-room-only">{num(lang, 100 * sizeBound(0.05, s.rates[AT5]?.n ?? s.n_rep), { decimals: 2 })}</td>
                    <td>{rateSe(lang, s.rates[AT1])}</td>
                    <td className="ct-room-only">{num(lang, 100 * sizeBound(0.01, s.rates[AT1]?.n ?? s.n_rep), { decimals: 2 })}</td>
                    <td data-holds={ok ? 'yes' : 'no'}>{pick(verdict, lang)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </TableCard>
      }
    />
  );
}

/** The coverage of the four intervals by grade against their level, with the band a correct interval's measured
 * coverage falls in (two Monte Carlo SEs at the analytical intervals' repetitions); and the chosen grade's four
 * coverages, each with its Wilson interval. */
export function markovCoverageCharts(v: FamilyVariant, sel: C04Sel): ChartSpec[] {
  const r = markovRung(v);
  if (!r) return [];
  const level = r.level;
  const n = r.coverage.wald[0]?.n ?? v.outputs.design.reps;
  const half = n > 0 ? 2 * Math.sqrt((level * (1 - level)) / n) : 0;
  const x = gradeX();
  const methods: Interval[] = [...ANALYTIC, 'bootstrap'];
  const pos = categorical(methods);
  const at = (f: (c: C04Rate) => number) => pos.at.map((i) => (i === null ? null : f(r.coverage[methods[i]][sel.grade])));
  return [
    {
      key: 'coverage',
      x,
      y: { label: t('Coverage (%)', 'Cobertura (%)'), range: [0, 1], format: { percent: true, digits: 3 } },
      series: [
        ...methods.map((m) => ({ label: INTERVAL_LABEL[m], values: r.coverage[m].map((c) => c.rate), color: INTERVAL_COLOR[m], width: 2 })),
        { label: bi((l) => `${L(l, 'Nominal', 'Nominal')} ${pct0(l, level)}`), values: flat(x.values, level), color: '--color-fg-subtle', width: 1, dash: [2, 4] },
        {
          label: bi((l) => `${pct0(l, level)} - 2 ${L(l, 'MC SE', 'EE MC')}`),
          values: flat(x.values, Math.max(0, level - half)),
          color: '--color-fg-faint',
          width: 1,
          dash: [6, 4],
        },
        {
          label: bi((l) => `${pct0(l, level)} + 2 ${L(l, 'MC SE', 'EE MC')}`),
          values: flat(x.values, Math.min(1, level + half)),
          color: '--color-fg-faint',
          width: 1,
          dash: [6, 4],
        },
      ] as ChartSeries[],
      marks: [gradeMark(sel.grade)],
    },
    {
      key: 'coverage-grade',
      x: {
        values: pos.x,
        label: bi((l) => `${L(l, 'Interval', 'Intervalo')} (${methods.map((m, i) => `${i + 1} ${pick(INTERVAL_LABEL[m], l)}`).join(', ')})`),
        format: { decimals: 0 },
      },
      y: { label: t('Coverage (%)', 'Cobertura (%)'), range: [0, 1], format: { percent: true, digits: 3 } },
      series: [
        { label: t('Coverage', 'Cobertura'), values: at((c) => c.rate), color: '--color-accent', mode: 'points' },
        { label: bi((l) => `Wilson ${pct0(l, 0.95)}, ${L(l, 'low', 'inferior')}`), values: at((c) => c.wilson_low), color: '--color-fg-subtle', mode: 'points' },
        { label: bi((l) => `Wilson ${pct0(l, 0.95)}, ${L(l, 'high', 'superior')}`), values: at((c) => c.wilson_high), color: '--color-fg-subtle', mode: 'points' },
        { label: bi((l) => `${L(l, 'Nominal', 'Nominal')} ${pct0(l, level)}`), values: flat(pos.x, level), color: '--color-fg-subtle', width: 1, dash: [2, 4] },
      ] as ChartSeries[],
    },
  ];
}

export function MarkovCoverageView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const v = familyOf(sel);
  const charts = useMemo(() => (v && sel ? markovCoverageCharts(v, sel) : []), [v, sel]);
  if (!sel) return <Pending />;
  const r = v ? markovRung(v) : null;
  if (!v || !r || charts.length < 2) return <NotThisFamily />;
  const methods: Interval[] = [...ANALYTIC, 'bootstrap'];
  const n = r.coverage.wald[0]?.n ?? v.outputs.design.reps;
  const nb = r.bootstrap.repetitions;
  return (
    <ViewRow
      left={
        <ChartCard
          v={v}
          spec={charts[0]}
          title={bi((l) => `${L(l, 'Coverage of the', 'Cobertura de los intervalos al')} ${pct0(l, r.level)} ${L(l, 'intervals by grade', 'por grado')}`)}
          note={L(
            lang,
            `The share of repetitions whose interval holds the true one-year PD, in percent: Wald (2.2), Agresti-Coull (3.3) and Jeffreys on the pooled cohort counts (${num('en', n)} repetitions), and the resampling bootstrap of the duration PD (${num('en', r.bootstrap.n_boot)} replicates, in the first ${num('en', nb)} repetitions). Dashed: ${pct0('en', r.level)} plus or minus two Monte Carlo SEs at ${num('en', n)} repetitions, where a correct interval's coverage falls. ${definitionNote('en')} ${truthNote('en', sel)}`,
            `La fracción de repeticiones cuyo intervalo contiene la PD anual verdadera, en porcentaje: Wald (2.2), Agresti-Coull (3.3) y Jeffreys sobre los conteos de cohortes agrupados (${num('es', n)} repeticiones), y el bootstrap por remuestreo de la PD de duración (${num('es', r.bootstrap.n_boot)} réplicas, en las primeras ${num('es', nb)} repeticiones). Segmentadas: ${pct0('es', r.level)} más o menos dos EE de Monte Carlo a ${num('es', n)} repeticiones, donde cae la cobertura de un intervalo correcto. ${definitionNote('es')} ${truthNote('es', sel)}`,
          )}
        />
      }
      top={
        <ChartCard
          v={v}
          spec={charts[1]}
          title={bi((l) => `${L(l, 'The four intervals at', 'Los cuatro intervalos en')} ${GRADES[sel.grade]}`)}
          note={L(
            lang,
            `Each interval's coverage at ${GRADES[sel.grade]} with its ${pct0('en', 0.95)} Wilson interval (small dots), in percent; dotted, the level.`,
            `La cobertura de cada intervalo en ${GRADES[sel.grade]} con su intervalo de Wilson al ${pct0('es', 0.95)} (puntos pequeños), en porcentaje; punteada, el nivel.`,
          )}
        />
      }
      bottom={
        <TableCard
          v={v}
          title={t('Coverage by grade', 'Cobertura por grado')}
          note={L(lang, `Percent of the repetitions, each with its Monte Carlo SE in parentheses; the bootstrap over ${num('en', nb)} repetitions.`, `Porcentaje de las repeticiones, cada uno con su EE de Monte Carlo entre paréntesis; el bootstrap sobre ${num('es', nb)} repeticiones.`)}
        >
          <table className="caos-table ct-wrap-head" data-table="markov-coverage">
            <thead>
              <tr>
                <th className="ct-text">{L(lang, 'Grade', 'Grado')}</th>
                {methods.map((m) => (
                  <th key={m}>{`${pick(INTERVAL_LABEL[m], lang)}, %`}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {GRADES.map((gr, g) => (
                <tr key={gr} className={g === sel.grade ? 'ct-current' : undefined}>
                  <td className="ct-text">{gr}</td>
                  {methods.map((m) => (
                    <td key={m}>{rateSe(lang, r.coverage[m][g])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </TableCard>
      }
    />
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// the tests along a ladder (momentum, cycle, withdrawals)

interface LadderAxis {
  label: BiText;
  /** the rung's name in a table's first column */
  short: BiText;
  format: FormatOptions;
}
const LADDER_AXIS: Record<'momentum' | 'cycle' | 'withdrawals', LadderAxis> = {
  momentum: { label: t('Momentum alpha (beta 1 a year)', 'Alfa de momentum (beta 1 por año)'), short: t('Alpha', 'Alfa'), format: { decimals: 3 } },
  cycle: { label: t('k, the downgrade multiplier of the third year', 'k, el multiplicador de las rebajas del tercer año'), short: 'k', format: { decimals: 2 } },
  withdrawals: { label: t('k: withdrawal times 1 + k in the year before default', 'k: retiro por 1 + k en el año previo al incumplimiento'), short: 'k', format: { decimals: 0 } },
};

const rungValues = (v: FamilyVariant): number[] => v.outputs.rungs.map((r) => (r as { value: number }).value);

const alphaMark = (v: FamilyVariant) => (rungValues(v).includes(EMPIRICAL_ALPHA) ? [{ x: EMPIRICAL_ALPHA, label: bi((l) => `${L(l, 'alpha', 'alfa')} ${num(l, EMPIRICAL_ALPHA)}`) }] : []);

/** Tests' rejection rates along the family's ladder: solid at 5%, dashed at 1%, the nominal 5% dotted. */
function ladderRateChart(v: FamilyVariant, testIds: string[], axis: LadderAxis, key: string, marks: UPlotChartProps['marks'] = [], narrow = false): ChartSpec {
  const xs = rungValues(v);
  const at = (tid: string, rule: string) => xs.map((x) => simAt(v, tid, x)?.rates[rule]?.rate ?? null);
  return {
    key,
    x: { values: xs, label: axis.label, format: axis.format },
    y: narrow ? { ...RATE_AXIS, label: t('Rate (%)', 'Tasa (%)') } : RATE_AXIS,
    series: [
      ...testIds.map((tid) => ({ label: bi((l) => `${pick(TEST_LABEL[tid], l)}, ${L(l, 'at', 'al')} ${pct0(l, 0.05)}`), values: at(tid, AT5), color: TEST_COLOR[tid], width: 2.2 })),
      ...testIds.map((tid) => ({ label: bi((l) => `${pick(TEST_LABEL[tid], l)}, ${L(l, 'at', 'al')} ${pct0(l, 0.01)}`), values: at(tid, AT1), color: TEST_COLOR[tid], width: 1.4, dash: [6, 3] })),
      { label: bi((l) => `${L(l, 'Nominal level', 'Nivel nominal')} ${pct0(l, 0.05)}`), values: flat(xs, 0.05), color: '--color-fg-subtle' as ShellColorToken, width: 1, dash: [2, 4] },
    ],
    marks,
  };
}

/** The rates table of a ladder: a row per rung and level, a column per test, every rate with its Monte Carlo SE. */
function LadderRatesTable({ v, testIds, axis, table }: { v: FamilyVariant; testIds: string[]; axis: LadderAxis; table: string }) {
  const lang = useShellLang();
  const xs = rungValues(v);
  const levels = [
    { alpha: 0.05, rule: AT5 },
    { alpha: 0.01, rule: AT1 },
  ];
  return (
    <table className="caos-table ct-wrap-head" data-table={table}>
      <thead>
        <tr>
          <th className="ct-text">{pick(axis.short, lang)}</th>
          <th>{L(lang, 'Level', 'Nivel')}</th>
          {testIds.map((tid) => (
            <th key={tid}>{`${pick(TEST_LABEL[tid], lang)}, %`}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {xs.flatMap((x) =>
          levels.map(({ alpha, rule }) => (
            <tr key={`${x}-${rule}`} data-rung={x} data-rule={rule}>
              <td className="ct-text">{num(lang, x)}</td>
              <td>{pct0(lang, alpha)}</td>
              {testIds.map((tid) => (
                <td key={tid}>{rateSe(lang, simAt(v, tid, x)?.rates[rule])}</td>
              ))}
            </tr>
          )),
        )}
      </tbody>
    </table>
  );
}

/** The two matrix tests of a ladder family, one chart each (left the first, right the second over the rates table):
 * the cycle's and the withdrawals' Power and Tests views. */
function TwoTestsView({ v, sel, charts, testIds, axis, table, title, note }: { v: FamilyVariant; sel: C04Sel; charts: ChartSpec[]; testIds: string[]; axis: LadderAxis; table: string; title: (tid: string) => BiText; note: (lang: Lang) => string }) {
  const lang = useShellLang();
  const { n, maxSe } = repetitions(v);
  const common = (l: Lang) =>
    L(
      l,
      `Rejection rates in percent along the ladder (${num('en', n)} repetitions per rung, Monte Carlo SE at most ${num('en', 100 * maxSe, { decimals: 1 })} points; each in the table): solid at ${pct0('en', 0.05)}, dashed at ${pct0('en', 0.01)}, dotted the nominal ${pct0('en', 0.05)}.`,
      `Tasas de rechazo en porcentaje a lo largo de la escalera (${num('es', n)} repeticiones por peldaño, EE de Monte Carlo a lo más ${num('es', 100 * maxSe, { decimals: 1 })} puntos; cada uno en la tabla): continuas al ${pct0('es', 0.05)}, segmentadas al ${pct0('es', 0.01)}, punteada el nivel nominal del ${pct0('es', 0.05)}.`,
    );
  return (
    <ViewRow
      left={<ChartCard v={v} spec={charts[0]} title={title(testIds[0])} note={`${common(lang)} ${note(lang)} ${truthNote(lang, sel)}`} />}
      top={
        <ChartCard
          v={v}
          spec={charts[1]}
          title={title(testIds[1])}
          note={L(
            lang,
            `Solid at ${pct0('en', 0.05)}, dashed at ${pct0('en', 0.01)}, dotted the nominal ${pct0('en', 0.05)}; each rate's Monte Carlo SE in the table.`,
            `Continuas al ${pct0('es', 0.05)}, segmentadas al ${pct0('es', 0.01)}, punteada el nivel nominal del ${pct0('es', 0.05)}; el EE de Monte Carlo de cada tasa en la tabla.`,
          )}
        />
      }
      bottom={
        <TableCard v={v} title={t('Rates by rung', 'Tasas por peldaño')} note={L(lang, 'Rejection rates in percent, each with its Monte Carlo SE in parentheses.', 'Tasas de rechazo en porcentaje, cada una con su EE de Monte Carlo entre paréntesis.')}>
          <LadderRatesTable v={v} testIds={testIds} axis={axis} table={table} />
        </TableCard>
      }
    />
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// momentum: the tests' power and the fitted coefficient; the five-year projection

const MOMENTUM_TESTS = ['rating.time_homogeneity', 'rating.markov_order', 'rating.momentum'];

/** The three tests along alpha, and the fitted hazard coefficient c per rung against dos Reis et al.'s 0.33, the
 * empirical rung marked on both. */
export function momentumPowerCharts(v: FamilyVariant): ChartSpec[] {
  const rungs = rungsOf<C04MomentumRung>(v, 'momentum');
  if (!rungs) return [];
  const marks = alphaMark(v);
  const xs = rungValues(v);
  const c = rungs.map((r) => r.coefficient);
  const mean = c.map((x) => x?.mean ?? null);
  const mcse = c.map((x) => x?.bias_mcse ?? null);
  const name = t('Fitted c', 'c ajustado');
  return [
    ladderRateChart(v, MOMENTUM_TESTS, LADDER_AXIS.momentum, 'rates', marks),
    {
      key: 'coefficient',
      x: { values: xs, label: LADDER_AXIS.momentum.label, format: LADDER_AXIS.momentum.format },
      y: { label: t('c (unitless)', 'c (sin unidad)'), format: { digits: 3 } },
      series: [
        { label: bi((l) => `${pick(name, l)}, ${L(l, 'mean', 'media')}`), values: mean, color: '--color-accent', width: 2.4 },
        ...seBand(name, mean, mcse, '--color-accent'),
        { label: bi((l) => `dos Reis et al., Moody's: ${num(l, DOS_REIS_C)}`), values: flat(xs, DOS_REIS_C), color: '--color-fg', width: 1.2, dash: [2, 4] },
      ],
      marks,
    },
  ];
}

export function MomentumPowerView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const v = familyOf(sel);
  const charts = useMemo(() => (v ? momentumPowerCharts(v) : []), [v]);
  if (!sel) return <Pending />;
  const rungs = v ? rungsOf<C04MomentumRung>(v, 'momentum') : null;
  if (!v || !rungs || charts.length < 2) return <NotThisFamily />;
  const { n, maxSe } = repetitions(v);
  return (
    <ViewRow
      left={
        <ChartCard
          v={v}
          spec={charts[0]}
          title={t('What the tests see of rating momentum', 'Lo que ven las pruebas del momentum de calificación')}
          note={L(
            lang,
            `Rejection rates in percent along alpha (${num('en', n)} repetitions per rung, Monte Carlo SE at most ${num('en', 100 * maxSe, { decimals: 1 })} points; each in the table): solid at ${pct0('en', 0.05)}, dashed at ${pct0('en', 0.01)}, dotted the nominal ${pct0('en', 0.05)}. Alpha 0 is a Markov chain, so its rates are the tests' size; alpha ${num('en', EMPIRICAL_ALPHA)} (marked) gives the hazard coefficient dos Reis, Pfeuffer and Smith estimate on Moody's data: c, with which a stay entered by a downgrade is left exp(c) times faster. ${truthNote('en', sel)}`,
            `Tasas de rechazo en porcentaje a lo largo de alfa (${num('es', n)} repeticiones por peldaño, EE de Monte Carlo a lo más ${num('es', 100 * maxSe, { decimals: 1 })} puntos; cada uno en la tabla): continuas al ${pct0('es', 0.05)}, segmentadas al ${pct0('es', 0.01)}, punteada el nivel nominal del ${pct0('es', 0.05)}. Alfa 0 es una cadena de Markov, así que sus tasas son el tamaño de las pruebas; alfa ${num('es', EMPIRICAL_ALPHA)} (marcado) da el coeficiente de riesgo que dos Reis, Pfeuffer y Smith estiman con datos de Moody's: c, con el que una estadía que empieza con una rebaja se deja exp(c) veces más rápido. ${truthNote('es', sel)}`,
          )}
        />
      }
      top={
        <ChartCard
          v={v}
          spec={charts[1]}
          title={t('The fitted hazard coefficient', 'El coeficiente de riesgo ajustado')}
          note={L(
            lang,
            `The mean fitted c (0 for a Markov chain) with two Monte Carlo SEs either side (dashed), against dos Reis et al.'s ${num('en', DOS_REIS_C)} on Moody's data (dotted); alpha ${num('en', EMPIRICAL_ALPHA)} marked.`,
            `El c ajustado medio (0 en una cadena de Markov) con dos EE de Monte Carlo a cada lado (segmentadas), contra el ${num('es', DOS_REIS_C)} de dos Reis et al. con datos de Moody's (punteada); alfa ${num('es', EMPIRICAL_ALPHA)} marcado.`,
          )}
        />
      }
      bottom={
        <TableCard
          v={v}
          title={t('Rates and the coefficient by rung', 'Tasas y coeficiente por peldaño')}
          note={L(
            lang,
            "Rejection rates in percent and c, each with its Monte Carlo SE in parentheses; the empirical SE says how far one dataset's estimate of c strays.",
            'Tasas de rechazo en porcentaje y c, cada uno con su EE de Monte Carlo entre paréntesis; el EE empírico dice cuánto se aleja la estimación de c de un solo conjunto de datos.',
          )}
        >
          <LadderRatesTable v={v} testIds={MOMENTUM_TESTS} axis={LADDER_AXIS.momentum} table="momentum-power" />
          <table className="caos-table ct-wrap-head" data-table="momentum-coefficient">
            <thead>
              <tr>
                <th className="ct-text">{L(lang, 'Alpha', 'Alfa')}</th>
                <th>{L(lang, 'Fitted c, mean', 'c ajustado, media')}</th>
                <th>{L(lang, 'Empirical SE', 'EE empírico')}</th>
              </tr>
            </thead>
            <tbody>
              {rungs.map((r) => (
                <tr key={r.value} className={r.value === EMPIRICAL_ALPHA ? 'ct-current' : undefined}>
                  <td className="ct-text">{num(lang, r.value)}</td>
                  <td>{r.coefficient ? withSe(lang, r.coefficient.mean, r.coefficient.bias_mcse) : na(lang)}</td>
                  <td>{r.coefficient ? withSe(lang, r.coefficient.empirical_se, r.coefficient.empirical_se_mcse) : na(lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableCard>
      }
    />
  );
}

/** For the chosen grade along alpha: the momentum chain's five-year default frequency against the two Markov
 * projections from its one-year data and the plain chain's PD; and the projections' errors in percentage points. */
export function momentumProjectionCharts(v: FamilyVariant, sel: C04Sel): ChartSpec[] {
  const rungs = rungsOf<C04MomentumRung>(v, 'momentum');
  if (!rungs) return [];
  const g = sel.grade;
  const xs = rungValues(v);
  const x = { values: xs, label: LADDER_AXIS.momentum.label, format: LADDER_AXIS.momentum.format };
  const marks = alphaMark(v);
  const freq = rungs.map((r) => r.pd_5y_frequency.mean[g]);
  const power = rungs.map((r) => r.pd_5y_cohort_power.mean[g]);
  const dur = rungs.map((r) => r.pd_5y_duration.mean[g]);
  const plain = rungs.map((r) => r.pd_5y_frequency.truth[g]);
  const pp = (xs2: Array<number | null>) => xs2.map((e) => (e === null ? null : 100 * e));
  const ePow = rungs.map((r) => r.error_cohort_power.mean[g]);
  const eDur = rungs.map((r) => r.error_duration.mean[g]);
  const powName = t('Cohort matrix to the fifth power', 'Matriz de cohortes a la quinta potencia');
  const durName = t('exp(5Q), duration generator', 'exp(5Q), generador de duración');
  return [
    {
      key: 'five-year',
      x,
      y: pdAxis((l) => `${L(l, 'Five-year PD of', 'PD a cinco años de')} ${GRADES[g]}`, [freq, power, dur, plain]),
      series: [
        { label: t('Default frequency of the momentum chain', 'Frecuencia de incumplimiento de la cadena con momentum'), values: freq, color: '--color-fg', width: 2.6 },
        { label: powName, values: power, color: '--color-accent', width: 2 },
        { label: durName, values: dur, color: '--color-magenta', width: 2 },
        { label: t('Plain chain, no momentum', 'Cadena sin momentum'), values: plain, color: '--color-fg-subtle', width: 1.2, dash: [6, 4] },
      ],
      marks,
    },
    {
      key: 'error',
      x,
      y: { label: t('Error (points)', 'Error (puntos)'), format: { digits: 3 } },
      series: [
        { label: powName, values: pp(ePow), color: '--color-accent', width: 2.2 },
        ...seBand(t('Matrix^5', 'Matriz^5'), ePow, rungs.map((r) => r.error_cohort_power.bias_mcse[g]), '--color-accent', 100),
        { label: durName, values: pp(eDur), color: '--color-magenta', width: 2.2 },
        ...seBand('exp(5Q)', eDur, rungs.map((r) => r.error_duration.bias_mcse[g]), '--color-magenta', 100),
        { label: t('No error', 'Sin error'), values: flat(xs, 0), color: '--color-fg-subtle', width: 1, dash: [2, 4] },
      ],
      marks,
    },
  ];
}

export function MomentumProjectionView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const v = familyOf(sel);
  const charts = useMemo(() => (v && sel ? momentumProjectionCharts(v, sel) : []), [v, sel]);
  if (!sel) return <Pending />;
  const rungs = v ? rungsOf<C04MomentumRung>(v, 'momentum') : null;
  if (!v || !rungs || charts.length < 2) return <NotThisFamily />;
  const g = sel.grade;
  const grade = GRADES[g];
  const { n } = repetitions(v);
  const perf = (p: C04Performance) => meanSe(lang, p.mean[g], p.bias_mcse[g]);
  return (
    <ViewRow
      left={
        <ChartCard
          v={v}
          spec={charts[0]}
          title={bi((l) => `${L(l, 'Five-year PD of', 'PD a cinco años de')} ${grade}: ${L(l, 'what the chain lives and what one-year data project', 'lo que vive la cadena y lo que proyectan los datos anuales')}`)}
          note={L(
            lang,
            `Means over ${num('en', n)} repetitions, in percent: the initial cohort's default frequency after five years (the momentum chain's own), the pooled one-year cohort matrix to the fifth power and exp(5Q) of the duration generator, both from the same paths, against the plain chain's five-year PD (dashed). Alpha ${num('en', EMPIRICAL_ALPHA)} marked. ${definitionNote('en')} ${truthNote('en', sel)}`,
            `Medias sobre ${num('es', n)} repeticiones, en porcentaje: la frecuencia de incumplimiento de la cohorte inicial a cinco años (la propia de la cadena con momentum), la matriz de cohortes anual agrupada a la quinta potencia y exp(5Q) del generador de duración, ambas de las mismas trayectorias, contra la PD a cinco años de la cadena sin momentum (segmentada). Alfa ${num('es', EMPIRICAL_ALPHA)} marcado. ${definitionNote('es')} ${truthNote('es', sel)}`,
          )}
        />
      }
      top={
        <ChartCard
          v={v}
          spec={charts[1]}
          title={bi((l) => `${L(l, 'Projection error for', 'Error de proyección para')} ${grade}`)}
          note={L(
            lang,
            'Each projection minus the frequency, paired by repetition, in percentage points; two Monte Carlo SEs either side (dashed).',
            'Cada proyección menos la frecuencia, pareadas por repetición, en puntos porcentuales; dos EE de Monte Carlo a cada lado (segmentadas).',
          )}
        />
      }
      bottom={
        <TableCard
          v={v}
          title={bi((l) => `${grade} ${L(l, 'by rung', 'por peldaño')}`)}
          note={L(
            lang,
            `Percent, the mean over the repetitions with its Monte Carlo SE in parentheses; the errors are the projection minus the frequency. Plain chain's five-year PD of ${grade}: ${pctText('en', rungs[0]?.pd_5y_frequency.truth[g])}. The one-year cohort PD shows momentum raising the one-year rate as well.`,
            `Porcentaje, la media sobre las repeticiones con su EE de Monte Carlo entre paréntesis; los errores son la proyección menos la frecuencia. PD a cinco años de ${grade} en la cadena sin momentum: ${pctText('es', rungs[0]?.pd_5y_frequency.truth[g])}. La PD de cohorte a un año muestra que el momentum también sube la tasa a un año.`,
          )}
        >
          <table className="caos-table ct-wrap-head" data-table="momentum-projection">
            <thead>
              <tr>
                <th className="ct-text">{L(lang, 'Alpha', 'Alfa')}</th>
                <th>{L(lang, 'Frequency, %', 'Frecuencia, %')}</th>
                <th>{L(lang, 'Matrix^5, %', 'Matriz^5, %')}</th>
                <th>{L(lang, 'exp(5Q), %', 'exp(5Q), %')}</th>
                <th>{L(lang, 'Error, matrix^5, %', 'Error, matriz^5, %')}</th>
                <th>{L(lang, 'Error, exp(5Q), %', 'Error, exp(5Q), %')}</th>
                <th className="ct-room-only">{L(lang, 'One-year cohort PD, %', 'PD de cohorte a un año, %')}</th>
              </tr>
            </thead>
            <tbody>
              {rungs.map((r) => (
                <tr key={r.value} data-rung={r.value} className={r.value === EMPIRICAL_ALPHA ? 'ct-current' : undefined}>
                  <td className="ct-text">{num(lang, r.value)}</td>
                  <td>{perf(r.pd_5y_frequency)}</td>
                  <td>{perf(r.pd_5y_cohort_power)}</td>
                  <td>{perf(r.pd_5y_duration)}</td>
                  <td>{perf(r.error_cohort_power)}</td>
                  <td>{perf(r.error_duration)}</td>
                  <td className="ct-room-only">{perf(r.pd_1y_cohort)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableCard>
      }
    />
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// cycle: the tests' power; the stressed year, the long-run average and the truth

const CYCLE_TESTS = ['rating.time_homogeneity', 'rating.matrix_reference'];

/** Time homogeneity and the stressed year's reference test along k, one chart each. */
export function cyclePowerCharts(v: FamilyVariant): ChartSpec[] {
  if (!rungsOf<C04CycleRung>(v, 'cycle')) return [];
  return CYCLE_TESTS.map((tid, i) => ladderRateChart(v, [tid], LADDER_AXIS.cycle, `rates-${tid.split('.')[1]}`, [], i > 0));
}

export function CyclePowerView({ sel }: { sel: C04Sel | null }) {
  const v = familyOf(sel);
  const charts = useMemo(() => (v ? cyclePowerCharts(v) : []), [v]);
  if (!sel) return <Pending />;
  if (!v || charts.length < 2) return <NotThisFamily />;
  return (
    <TwoTestsView
      v={v}
      sel={sel}
      charts={charts}
      testIds={CYCLE_TESTS}
      axis={LADDER_AXIS.cycle}
      table="cycle-power"
      title={(tid) =>
        tid === 'rating.time_homogeneity'
          ? t('Time homogeneity across the five years', 'Homogeneidad temporal entre los cinco años')
          : t("The stressed year's counts against the pooled matrix", 'Los conteos del año de estrés contra la matriz agrupada')
      }
      note={(l) =>
        L(
          l,
          "Time homogeneity compares the five annual matrices; the reference test, the stressed year's counts against the pooled matrix of the same draw. k 1 is the stable chain, so its rates are the tests' size.",
          'La homogeneidad temporal compara las cinco matrices anuales; la prueba de referencia, los conteos del año de estrés contra la matriz agrupada de la misma simulación. k 1 es la cadena estable, así que sus tasas son el tamaño de las pruebas.',
        )
      }
    />
  );
}

/** The year of the five whose generator is stressed (the end of the stressed period: [2, 3] is the third year), or
 * null for the stable rung. */
const stressedYear = (r: C04CycleRung): number | null => (r.stressed_period ? Math.round(r.stressed_period[1]) : null);

/** The true one-year PD of grade g in each of the five years: the stable chain's, the stressed one in the stressed
 * year (the family's truth: four years at Q, the third at Q_k; their mean is pd_true_average). */
export function trueYearProfile(r: C04CycleRung, g: number, years: number): number[] {
  const s = stressedYear(r);
  return Array.from({ length: years }, (_, i) => (s !== null && i + 1 === s ? r.pd_true_stressed[g] : r.pd_true_base[g]));
}

export function cyclePitCharts(v: FamilyVariant, sel: C04Sel): ChartSpec[] {
  const rungs = rungsOf<C04CycleRung>(v, 'cycle');
  if (!rungs) return [];
  const g = sel.grade;
  const xs = rungValues(v);
  const est = (k: 'pd_stressed_year' | 'pd_lra' | 'pd_pooled') => rungs.map((r) => r[k].mean[g]);
  const stressedTruth = rungs.map((r) => r.pd_true_stressed[g]);
  const averageTruth = rungs.map((r) => r.pd_true_average[g]);
  const base = rungs.map((r) => r.pd_true_base[g]);
  const sy = est('pd_stressed_year');
  const lra = est('pd_lra');
  const pooled = est('pd_pooled');
  const years = v.outputs.design.years;
  const yx = Array.from({ length: years }, (_, i) => i + 1);
  const profiles = rungs.map((r) => trueYearProfile(r, g, years));
  const stressAt = rungs.map(stressedYear).find((s) => s !== null) ?? null;
  return [
    {
      key: 'pit-ttc',
      x: { values: xs, label: LADDER_AXIS.cycle.label, format: LADDER_AXIS.cycle.format },
      y: pdAxis((l) => `${L(l, 'One-year PD of', 'PD a un año de')} ${GRADES[g]}`, [sy, stressedTruth, lra, averageTruth, pooled, base]),
      series: [
        { label: t("The stressed year's cohort PD", 'PD de cohorte del año de estrés'), values: sy, color: '--color-bad', width: 2.2 },
        { label: t('True PD of the stressed year', 'PD verdadera del año de estrés'), values: stressedTruth, color: '--color-bad', width: 1.2, dash: [6, 4] },
        { label: t('Long-run average (EBA paragraph 84)', 'Promedio de largo plazo (párrafo 84 de la EBA)'), values: lra, color: '--color-accent', width: 2.2 },
        { label: t('True five-year average', 'Promedio verdadero de cinco años'), values: averageTruth, color: '--color-accent', width: 1.2, dash: [6, 4] },
        { label: t('Pooled PD (Anderson and Goodman)', 'PD agrupada (Anderson y Goodman)'), values: pooled, color: '--color-good', width: 1.8 },
        { label: t('Stable chain, exp(Q)', 'Cadena estable, exp(Q)'), values: base, color: '--color-fg-subtle', width: 1.2, dash: [2, 4] },
      ],
    },
    {
      key: 'by-year',
      x: { values: yx, label: t('Year of the five', 'Año de los cinco'), format: { decimals: 0 } },
      y: pdAxis((l) => L(l, 'True PD', 'PD verdadera'), profiles, true),
      series: rungs.map((r, i) => ({ label: bi((l) => `k ${num(l, r.value)}`), values: profiles[i], color: RUNG_COLOR[i % RUNG_COLOR.length], width: 2 })),
      marks: stressAt === null ? [] : [{ x: stressAt, label: t('stressed year', 'año de estrés') }],
    },
  ];
}

export function CyclePitTtcView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const v = familyOf(sel);
  const charts = useMemo(() => (v && sel ? cyclePitCharts(v, sel) : []), [v, sel]);
  if (!sel) return <Pending />;
  const rungs = v ? rungsOf<C04CycleRung>(v, 'cycle') : null;
  if (!v || !rungs || charts.length < 2) return <NotThisFamily />;
  const g = sel.grade;
  const grade = GRADES[g];
  const { n } = repetitions(v);
  const perf = (p: C04Performance) => meanSe(lang, p.mean[g], p.bias_mcse[g]);
  const stress = rungs.map(stressedYear).find((s) => s !== null);
  return (
    <ViewRow
      left={
        <ChartCard
          v={v}
          spec={charts[0]}
          title={bi((l) => `${grade}: ${L(l, 'the stressed year, the long-run average and the truth', 'el año de estrés, el promedio de largo plazo y la verdad')}`)}
          note={L(
            lang,
            `Means over ${num('en', n)} repetitions (solid) against their truths (dashed), in percent: the stressed year's cohort PD (a point-in-time reading), the long-run average of EBA/GL/2017/16 paragraph 84 (the mean of the five yearly cohort PDs) and Anderson and Goodman's pooled PD (2.8); dotted, the stable chain's exp(Q), the through-the-cycle reference. ${definitionNote('en')} ${truthNote('en', sel)}`,
            `Medias sobre ${num('es', n)} repeticiones (continuas) contra sus verdades (segmentadas), en porcentaje: la PD de cohorte del año de estrés (una lectura puntual en el tiempo), el promedio de largo plazo del párrafo 84 de EBA/GL/2017/16 (la media de las cinco PD de cohorte anuales) y la PD agrupada de Anderson y Goodman (2.8); punteada, exp(Q) de la cadena estable, la referencia a lo largo del ciclo. ${definitionNote('es')} ${truthNote('es', sel)}`,
          )}
        />
      }
      top={
        <ChartCard
          v={v}
          spec={charts[1]}
          title={bi((l) => `${L(l, 'True one-year PD of', 'PD anual verdadera de')} ${grade} ${L(l, 'by year', 'por año')}`)}
          note={L(
            lang,
            `Downgrades times k in year ${num('en', stress ?? null)} (marked), the stable generator in the others, in percent; their mean is the long-run average's truth.`,
            `Rebajas por k en el año ${num('es', stress ?? null)} (marcado), el generador estable en los demás, en porcentaje; su media es la verdad del promedio de largo plazo.`,
          )}
        />
      }
      bottom={
        <TableCard
          v={v}
          title={bi((l) => `${grade} ${L(l, 'by rung', 'por peldaño')}`)}
          note={L(lang, 'Percent: the mean over the repetitions, with its Monte Carlo SE in parentheses, beside its truth.', 'Porcentaje: la media sobre las repeticiones, con su EE de Monte Carlo entre paréntesis, junto a su verdad.')}
        >
          <table className="caos-table ct-wrap-head" data-table="cycle-pit">
            <thead>
              <tr>
                <th className="ct-text">k</th>
                <th>{L(lang, 'Stressed year, %', 'Año de estrés, %')}</th>
                <th>{L(lang, 'Its truth, %', 'Su verdad, %')}</th>
                <th>{L(lang, 'Long-run average, %', 'Promedio de largo plazo, %')}</th>
                <th>{L(lang, 'Its truth, %', 'Su verdad, %')}</th>
                <th>{L(lang, 'Pooled, %', 'Agrupada, %')}</th>
                <th className="ct-wide-only">{L(lang, 'Stable chain, %', 'Cadena estable, %')}</th>
              </tr>
            </thead>
            <tbody>
              {rungs.map((r) => (
                <tr key={r.value} data-rung={r.value}>
                  <td className="ct-text">{num(lang, r.value)}</td>
                  <td>{perf(r.pd_stressed_year)}</td>
                  <td>{pctSig(lang, r.pd_true_stressed[g])}</td>
                  <td>{perf(r.pd_lra)}</td>
                  <td>{pctSig(lang, r.pd_true_average[g])}</td>
                  <td>{perf(r.pd_pooled)}</td>
                  <td className="ct-wide-only">{pctSig(lang, r.pd_true_base[g])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableCard>
      }
    />
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// withdrawals: the PD under three treatments of the withdrawn ratings; the matrix tests

const WITHDRAWAL_TESTS = ['rating.time_homogeneity', 'rating.matrix_reference'];
type Treatment = 'pd_removed' | 'pd_kept' | 'pd_followed' | 'pd_latent';
const TREATMENTS: Treatment[] = ['pd_removed', 'pd_kept', 'pd_followed', 'pd_latent'];
const TREATMENT_LABEL: Record<Treatment, BiText> = {
  pd_removed: bi((l) => `${L(l, 'Removed', 'Eliminados')} (${pick(DEFINITION_LABEL.d4, l)})`),
  pd_kept: bi((l) => `${L(l, 'Kept in the denominator', 'Mantenidos en el denominador')} (${pick(DEFINITION_LABEL.keep, l)})`),
  pd_followed: t('Followed to the year end (EBA paragraphs 73 and 76)', 'Seguidos al fin del año (párrafos 73 y 76 de la EBA)'),
  pd_latent: t('Latent chain, every obligor followed', 'Cadena latente, todo deudor seguido'),
};
const TREATMENT_SHORT: Record<Treatment, BiText> = {
  pd_removed: t('Removed', 'Eliminados'),
  pd_kept: t('Kept', 'Mantenidos'),
  pd_followed: t('Followed', 'Seguidos'),
  pd_latent: t('Latent', 'Latente'),
};
const TREATMENT_COLOR: Record<Treatment, ShellColorToken> = { pd_removed: DEFINITION_COLOR.d4, pd_kept: DEFINITION_COLOR.keep, pd_followed: '--color-accent', pd_latent: '--color-good' };
/** What the two CEREP definitions the withdrawals family compares count, short enough for a chart's note. */
const WITHDRAWAL_DEFINITIONS = {
  en: `${pick(DEFINITION_LABEL.d4, 'en')}: the default column over the cohort less its withdrawals; ${pick(DEFINITION_LABEL.keep, 'en')}: the default column over the whole cohort`,
  es: `${pick(DEFINITION_LABEL.d4, 'es')}: la columna de incumplimiento sobre la cohorte menos sus retiros; ${pick(DEFINITION_LABEL.keep, 'es')}: la columna de incumplimiento sobre toda la cohorte`,
};

export function withdrawalBiasCharts(v: FamilyVariant, sel: C04Sel): ChartSpec[] {
  const rungs = rungsOf<C04WithdrawalsRung>(v, 'withdrawals');
  if (!rungs) return [];
  const g = sel.grade;
  const xs = rungValues(v);
  const x = { values: xs, label: LADDER_AXIS.withdrawals.label, format: LADDER_AXIS.withdrawals.format };
  const means = TREATMENTS.map((k) => rungs.map((r) => r[k].mean[g]));
  const truth = rungs.map((r) => r.pd_removed.truth[g]);
  const share = rungs.map((r) => r.withdrawn_share.mean[g]);
  const shareSe = rungs.map((r) => r.withdrawn_share.mean_mcse[g]);
  const rate = rungs[0]?.withdrawal_rate ?? null;
  const shareName = t('Withdrawn share', 'Fracción retirada');
  return [
    {
      key: 'treatments',
      x,
      y: pdAxis((l) => `${L(l, 'One-year PD of', 'PD a un año de')} ${GRADES[g]}`, [...means, truth]),
      series: [
        ...TREATMENTS.map((k, i) => ({ label: TREATMENT_LABEL[k], values: means[i], color: TREATMENT_COLOR[k], width: k === 'pd_latent' ? 1.6 : 2.2 })),
        { label: t('True one-year PD', 'PD anual verdadera'), values: truth, color: '--color-fg', width: 1.2, dash: [6, 4] },
      ],
    },
    {
      key: 'withdrawn-share',
      x,
      y: { label: t('Withdrawn (%)', 'Retiradas (%)'), format: { percent: true, digits: 3 } },
      series: [
        { label: shareName, values: share, color: '--color-accent', width: 2.2 },
        ...seBand(t('Share', 'Fracción'), share, shareSe, '--color-accent'),
        ...(rate === null ? [] : [{ label: bi((l) => `${L(l, 'Base withdrawal rate', 'Tasa base de retiro')}, ${pct0(l, rate)} ${L(l, 'a year', 'al año')}`), values: flat(xs, rate), color: '--color-fg-subtle' as ShellColorToken, width: 1, dash: [2, 4] }]),
      ],
    },
  ];
}

export function WithdrawalsBiasView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const v = familyOf(sel);
  const charts = useMemo(() => (v && sel ? withdrawalBiasCharts(v, sel) : []), [v, sel]);
  if (!sel) return <Pending />;
  const rungs = v ? rungsOf<C04WithdrawalsRung>(v, 'withdrawals') : null;
  if (!v || !rungs || charts.length < 2) return <NotThisFamily />;
  const g = sel.grade;
  const grade = GRADES[g];
  const truth = rungs[0]?.pd_removed.truth[g] ?? null;
  const { n } = repetitions(v);
  const rate = rungs[0]?.withdrawal_rate ?? null;
  return (
    <ViewRow
      left={
        <ChartCard
          v={v}
          spec={charts[0]}
          title={bi((l) => `${grade}: ${L(l, 'the PD under each treatment of withdrawals', 'la PD con cada tratamiento de los retiros')}`)}
          note={L(
            lang,
            `Means over ${num('en', n)} repetitions in percent, against the true one-year PD (dashed): withdrawals removed (CEREP's transition page), kept in the denominator, followed to the year end (a withdrawn rating that defaults counts) and the latent chain (every obligor followed, withdrawn or not). ${WITHDRAWAL_DEFINITIONS.en}. ${pick(ESMA_DEFINITIONS, 'en')} ${truthNote('en', sel)}`,
            `Medias sobre ${num('es', n)} repeticiones en porcentaje, contra la PD anual verdadera (segmentada): retiros eliminados (la página de transiciones de CEREP), mantenidos en el denominador, seguidos al fin del año (una calificación retirada que incumple cuenta) y la cadena latente (todo deudor seguido, retirado o no). ${WITHDRAWAL_DEFINITIONS.es}. ${pick(ESMA_DEFINITIONS, 'es')} ${truthNote('es', sel)}`,
          )}
        />
      }
      top={
        <ChartCard
          v={v}
          spec={charts[1]}
          title={bi((l) => `${L(l, 'Withdrawn share of', 'Fracción retirada de')} ${grade}`)}
          note={L(
            lang,
            `The grade's ratings withdrawn within a year, in percent, two Monte Carlo SEs either side (dashed)${rate === null ? '' : `; dotted, the base ${pct0('en', rate)} a year`}.`,
            `Las calificaciones del grado retiradas en el año, en porcentaje, dos EE de Monte Carlo a cada lado (segmentadas)${rate === null ? '' : `; punteada, la base del ${pct0('es', rate)} al año`}.`,
          )}
        />
      }
      bottom={
        <TableCard
          v={v}
          title={bi((l) => `${L(l, 'Bias over the truth', 'Sesgo sobre la verdad')}, ${grade}`)}
          note={L(
            lang,
            `Each treatment's bias over the true one-year PD of ${grade} (${pctText('en', truth)}), and the withdrawn share, in percent, each with its Monte Carlo SE in parentheses.`,
            `El sesgo de cada tratamiento sobre la PD anual verdadera de ${grade} (${pctText('es', truth)}), y la fracción retirada, en porcentaje, cada uno con su EE de Monte Carlo entre paréntesis.`,
          )}
        >
          <table className="caos-table ct-wrap-head" data-table="withdrawals-bias">
            <thead>
              <tr>
                <th className="ct-text">k</th>
                {TREATMENTS.map((k) => (
                  <th key={k} className={k === 'pd_latent' ? 'ct-wide-only' : undefined}>
                    {`${pick(TREATMENT_SHORT[k], lang)}, %`}
                  </th>
                ))}
                <th>{L(lang, 'Withdrawn, %', 'Retirada, %')}</th>
              </tr>
            </thead>
            <tbody>
              {rungs.map((r) => (
                <tr key={r.value} data-rung={r.value}>
                  <td className="ct-text">{num(lang, r.value)}</td>
                  {TREATMENTS.map((k) => (
                    <td key={k} className={k === 'pd_latent' ? 'ct-wide-only' : undefined}>
                      {relativeSe(lang, r[k].bias[g], r[k].bias_mcse[g], r[k].truth[g])}
                    </td>
                  ))}
                  <td>{meanSe(lang, r.withdrawn_share.mean[g], r.withdrawn_share.mean_mcse[g])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableCard>
      }
    />
  );
}

/** Time homogeneity and the last year's reference test along k, one chart each. */
export function withdrawalTestCharts(v: FamilyVariant): ChartSpec[] {
  if (!rungsOf<C04WithdrawalsRung>(v, 'withdrawals')) return [];
  return WITHDRAWAL_TESTS.map((tid, i) => ladderRateChart(v, [tid], LADDER_AXIS.withdrawals, `rates-${tid.split('.')[1]}`, [], i > 0));
}

export function WithdrawalsTestsView({ sel }: { sel: C04Sel | null }) {
  const v = familyOf(sel);
  const charts = useMemo(() => (v ? withdrawalTestCharts(v) : []), [v]);
  if (!sel) return <Pending />;
  if (!v || charts.length < 2) return <NotThisFamily />;
  return (
    <TwoTestsView
      v={v}
      sel={sel}
      charts={charts}
      testIds={WITHDRAWAL_TESTS}
      axis={LADDER_AXIS.withdrawals}
      table="withdrawals-tests"
      title={(tid) =>
        tid === 'rating.time_homogeneity'
          ? t('Time homogeneity across the five years', 'Homogeneidad temporal entre los cinco años')
          : t("The last year's counts against exp(Q)", 'Los conteos del último año contra exp(Q)')
      }
      note={(l) =>
        L(
          l,
          "Time homogeneity compares the five annual matrices; the reference test, the last year's counts against exp(Q) (the last: every path starts without a withdrawal history). The latent chain is Markov at every k: what a rejection would see is the withdrawals alone.",
          'La homogeneidad temporal compara las cinco matrices anuales; la prueba de referencia, los conteos del último año contra exp(Q) (el último: toda trayectoria parte sin historia de retiros). La cadena latente es de Markov con todo k: lo que un rechazo vería son solo los retiros.',
        )
      }
    />
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// thin: exact coverage and length by cohort size; adjacent grades' overlap

/** The cohort sizes as a categorical axis (1 to 5), its title naming each size. */
function thinX(rungs: C04ThinRung[]): UPlotChartProps['x'] {
  return {
    values: rungs.map((_, i) => i + 1),
    label: bi((l) => `${L(l, 'Obligors', 'Deudores')} (${rungs.map((r, i) => `${i + 1}: ${num(l, r.value)}`).join(', ')})`),
    format: { decimals: 0 },
  };
}

export function thinCoverageCharts(v: FamilyVariant, sel: C04Sel): ChartSpec[] {
  const rungs = rungsOf<C04ThinRung>(v, 'thin');
  if (!rungs) return [];
  const g = sel.grade;
  const x = thinX(rungs);
  const level = rungs[0]?.level ?? 0.95;
  const lengths = ANALYTIC.map((m) => rungs.map((r) => r.length[m][g]));
  return [
    {
      key: 'coverage',
      x,
      y: { label: bi((l) => `${L(l, 'Exact coverage for', 'Cobertura exacta para')} ${GRADES[g]} (%)`), range: [0, 1], format: { percent: true, digits: 3 } },
      series: [
        ...ANALYTIC.map((m) => ({ label: INTERVAL_LABEL[m], values: rungs.map((r) => r.coverage[m][g]), color: INTERVAL_COLOR[m], width: 2.2 })),
        { label: bi((l) => `${L(l, 'Nominal', 'Nominal')} ${pct0(l, level)}`), values: flat(rungs, level), color: '--color-fg-subtle' as ShellColorToken, width: 1, dash: [2, 4] },
      ],
    },
    {
      key: 'length',
      x,
      y: pdAxis((l) => L(l, 'Length', 'Longitud'), lengths, true),
      series: ANALYTIC.map((m, i) => ({ label: INTERVAL_LABEL[m], values: lengths[i], color: INTERVAL_COLOR[m], width: 2.2 })),
    },
  ];
}

export function ThinCoverageView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const v = familyOf(sel);
  const charts = useMemo(() => (v && sel ? thinCoverageCharts(v, sel) : []), [v, sel]);
  if (!sel) return <Pending />;
  const rungs = v ? rungsOf<C04ThinRung>(v, 'thin') : null;
  if (!v || !rungs || charts.length < 2) return <NotThisFamily />;
  const g = sel.grade;
  const grade = GRADES[g];
  const pd = v.outputs.generator.pd_1y[g];
  const level = rungs[0]?.level ?? 0.95;
  return (
    <ViewRow
      left={
        <ChartCard
          v={v}
          spec={charts[0]}
          title={bi((l) => `${L(l, 'Exact coverage of the', 'Cobertura exacta de los intervalos al')} ${pct0(l, level)} ${L(l, 'intervals for', 'para')} ${grade}`)}
          note={L(
            lang,
            `The probability that the interval holds the true one-year PD of ${grade} (${pctText('en', pd)}) with n obligors observed for one year, in percent: exact, by enumerating the binomial counts, so no Monte Carlo error. Dotted: the nominal ${pct0('en', level)}. ${definitionNote('en')} ${truthNote('en', sel)}`,
            `La probabilidad de que el intervalo contenga la PD anual verdadera de ${grade} (${pctText('es', pd)}) con n deudores observados un año, en porcentaje: exacta, enumerando los conteos binomiales, así que sin error de Monte Carlo. Punteada: el nivel nominal del ${pct0('es', level)}. ${definitionNote('es')} ${truthNote('es', sel)}`,
          )}
        />
      }
      top={
        <ChartCard
          v={v}
          spec={charts[1]}
          title={bi((l) => `${L(l, 'Expected length for', 'Longitud esperada para')} ${grade}`)}
          note={L(
            lang,
            "Each interval's expected width in percent, exact; Wald collapses to zero width when no default occurs.",
            'El ancho esperado de cada intervalo en porcentaje, exacto; Wald colapsa a ancho cero cuando no hay incumplimientos.',
          )}
        />
      }
      bottom={
        <TableCard
          v={v}
          title={bi((l) => `${grade} ${L(l, 'by cohort size', 'por tamaño de cohorte')}`)}
          note={L(lang, 'Coverage and expected length in percent, exact; expected defaults: n times the true PD.', 'Cobertura y longitud esperada en porcentaje, exactas; incumplimientos esperados: n por la PD verdadera.')}
        >
          <table className="caos-table ct-wrap-head" data-table="thin-coverage">
            <thead>
              <tr>
                <th className="ct-text">{L(lang, 'Obligors', 'Deudores')}</th>
                <th>{L(lang, 'Expected defaults', 'Incumplimientos esperados')}</th>
                {ANALYTIC.map((m) => (
                  <th key={m}>{`${pick(INTERVAL_LABEL[m], lang)}, ${L(lang, 'coverage', 'cobertura')} %`}</th>
                ))}
                {ANALYTIC.map((m) => (
                  <th key={`len-${m}`} className="ct-room-only">{`${pick(INTERVAL_LABEL[m], lang)}, ${L(lang, 'length', 'longitud')} %`}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rungs.map((r) => (
                <tr key={r.value} data-rung={r.value}>
                  <td className="ct-text">{num(lang, r.value)}</td>
                  <td>{num(lang, r.expected_defaults[g], { digits: 3 })}</td>
                  {ANALYTIC.map((m) => (
                    <td key={m}>{num(lang, 100 * r.coverage[m][g], { decimals: 2 })}</td>
                  ))}
                  {ANALYTIC.map((m) => (
                    <td key={`len-${m}`} className="ct-room-only">{pctSig(lang, r.length[m][g])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </TableCard>
      }
    />
  );
}

/** The adjacent pairs of grades, best first: AAA and AA, ..., B and CCC-C. */
const PAIRS = GRADES.slice(0, -1).map((g, i) => [g, GRADES[i + 1]] as const);

/** The overlap of adjacent grades' Jeffreys intervals, drawn between the two grades (pair i at i + 1.5 on the grade
 * axis, whose ends hold no pair), one line per cohort size; and the defaults each grade expects in its year at each
 * size, against one; the chosen grade marked on both. */
export function thinOverlapCharts(v: FamilyVariant, sel: C04Sel): ChartSpec[] {
  const rungs = rungsOf<C04ThinRung>(v, 'thin');
  if (!rungs) return [];
  const x = [1, ...PAIRS.map((_, i) => i + 1.5), N_GRADES];
  const sized = (r: C04ThinRung) => bi((l) => `${num(l, r.value)} ${L(l, 'obligors', 'deudores')}`);
  const grades = gradeX();
  return [
    {
      key: 'overlap',
      x: { values: x, label: GRADE_AXIS, format: { decimals: 0 } },
      y: { label: t('Probability of overlap (0 to 1)', 'Probabilidad de traslape (0 a 1)'), range: [0, 1], format: { digits: 3 } },
      series: rungs.map((r, i) => ({ label: sized(r), values: [null, ...r.overlap_jeffreys, null], color: RUNG_COLOR[i % RUNG_COLOR.length], width: 2 })),
      marks: [gradeMark(sel.grade)],
    },
    {
      key: 'expected-defaults',
      x: grades,
      y: { label: t('Defaults (log)', 'Incumpl. (log)'), log: true, format: { digits: 3 } },
      series: [
        ...rungs.map((r, i) => ({ label: sized(r), values: [...r.expected_defaults], color: RUNG_COLOR[i % RUNG_COLOR.length], width: 2 })),
        { label: t('One default', 'Un incumplimiento'), values: flat(grades.values, 1), color: '--color-fg', width: 1, dash: [2, 4] },
      ],
      marks: [gradeMark(sel.grade)],
    },
  ];
}

export function ThinOverlapView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const v = familyOf(sel);
  const charts = useMemo(() => (v && sel ? thinOverlapCharts(v, sel) : []), [v, sel]);
  if (!sel) return <Pending />;
  const rungs = v ? rungsOf<C04ThinRung>(v, 'thin') : null;
  if (!v || !rungs || charts.length < 2) return <NotThisFamily />;
  const level = rungs[0]?.level ?? 0.95;
  const chosen = GRADES[sel.grade];
  return (
    <ViewRow
      left={
        <ChartCard
          v={v}
          spec={charts[0]}
          title={t('Can adjacent grades be told apart?', '¿Se distinguen los grados adyacentes?')}
          note={L(
            lang,
            `The probability that the ${pct0('en', level)} Jeffreys intervals of two adjacent grades overlap, drawn between the two grades, one line per cohort size (obligors per grade, one year); exact, by enumerating both binomial counts. Near 1 the intervals cannot separate the grades (Hanson and Schuermann's question whether notches can be told apart); ${chosen} is marked. ${definitionNote('en')} ${truthNote('en', sel)}`,
            `La probabilidad de que los intervalos de Jeffreys al ${pct0('es', level)} de dos grados adyacentes se traslapen, dibujada entre ambos grados, una línea por tamaño de cohorte (deudores por grado, un año); exacta, enumerando ambos conteos binomiales. Cerca de 1 los intervalos no separan los grados (la pregunta de Hanson y Schuermann de si se distinguen los escalones); se marca ${chosen}. ${definitionNote('es')} ${truthNote('es', sel)}`,
          )}
        />
      }
      top={
        <ChartCard
          v={v}
          spec={charts[1]}
          title={t('The defaults each grade expects', 'Los incumplimientos que espera cada grado')}
          note={L(
            lang,
            'n obligors times the true PD, log scale: below one a year (dotted), the counts cannot tell the grades apart.',
            'n deudores por la PD verdadera, en escala logarítmica: bajo uno al año (punteada), los conteos no distinguen los grados.',
          )}
        />
      }
      bottom={
        <TableCard
          v={v}
          title={t('Overlap by pair and cohort size', 'Traslape por par y tamaño de cohorte')}
          note={L(lang, 'Probability from 0 to 1, exact; the pairs with the chosen grade are highlighted.', 'Probabilidad de 0 a 1, exacta; se destacan los pares con el grado elegido.')}
        >
          <table className="caos-table ct-wrap-head" data-table="thin-overlap">
            <thead>
              <tr>
                <th className="ct-text">{L(lang, 'Adjacent grades', 'Grados adyacentes')}</th>
                {rungs.map((r) => (
                  <th key={r.value}>{`${num(lang, r.value)} ${L(lang, 'obligors', 'deudores')}`}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {PAIRS.map(([a, b], i) => (
                <tr key={a} className={i === sel.grade || i + 1 === sel.grade ? 'ct-current' : undefined}>
                  <td className="ct-text">{L(lang, `${a} and ${b}`, `${a} y ${b}`)}</td>
                  {rungs.map((r) => (
                    <td key={r.value}>{num(lang, r.overlap_jeffreys[i], { digits: 4 })}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </TableCard>
      }
    />
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// the Validation group: one sub-tab per view of the family

export interface FamilyViewDef {
  id: string;
  label: BiText;
  View: (p: { sel: C04Sel | null }) => ReactElement;
  /** the charts the view draws, from the same builders the view calls */
  charts: (v: FamilyVariant, sel: C04Sel) => ChartSpec[];
}

/** The Validation views of each family, in tab order. */
export const FAMILY_VIEWS: Record<C04Family, FamilyViewDef[]> = {
  markov: [
    { id: 'estimators', label: t('Estimators', 'Estimadores'), View: MarkovEstimatorsView, charts: markovEstimatorCharts },
    { id: 'zeros', label: t('Zeros', 'Ceros'), View: MarkovZerosView, charts: markovZeroCharts },
    { id: 'size', label: t('Size', 'Tamaño'), View: MarkovSizeView, charts: (v) => markovSizeCharts(v) },
    { id: 'coverage', label: t('Coverage', 'Cobertura'), View: MarkovCoverageView, charts: markovCoverageCharts },
  ],
  momentum: [
    { id: 'power', label: t('Power', 'Potencia'), View: MomentumPowerView, charts: (v) => momentumPowerCharts(v) },
    { id: 'projection', label: t('Projection', 'Proyección'), View: MomentumProjectionView, charts: momentumProjectionCharts },
  ],
  cycle: [
    { id: 'power', label: t('Power', 'Potencia'), View: CyclePowerView, charts: (v) => cyclePowerCharts(v) },
    { id: 'pit-ttc', label: t('PIT and TTC', 'PIT y TTC'), View: CyclePitTtcView, charts: cyclePitCharts },
  ],
  withdrawals: [
    { id: 'bias', label: t('Bias', 'Sesgo'), View: WithdrawalsBiasView, charts: withdrawalBiasCharts },
    { id: 'tests', label: t('Tests', 'Pruebas'), View: WithdrawalsTestsView, charts: (v) => withdrawalTestCharts(v) },
  ],
  thin: [
    { id: 'coverage', label: t('Coverage', 'Cobertura'), View: ThinCoverageView, charts: thinCoverageCharts },
    { id: 'overlap', label: t('Overlap', 'Traslape'), View: ThinOverlapView, charts: thinOverlapCharts },
  ],
};

/** The Validation group of a generator family: its own views as sub-tabs (C05's instrument nests them the same way). */
export function FamilyValidationView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const v = familyOf(sel);
  if (!sel) return <Pending />;
  const defs = v ? FAMILY_VIEWS[v.outputs.family] : undefined;
  if (!v || !defs) return <NotThisFamily />;
  return (
    <SubTabs
      key={v.variant_id}
      ariaLabel={L(lang, 'Views of the family\'s validation', 'Vistas de la validación de la familia')}
      tabs={defs.map((d) => ({ id: d.id, label: pick(d.label, lang), content: <d.View sel={sel} /> }))}
    />
  );
}
