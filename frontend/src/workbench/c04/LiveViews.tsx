// C04's Impact group (CT-410, CT-411; docs/design/features/c04-transitions/web.md, "Impact (live)"): three tools
// recomputed in the browser on the variant's one-year chain by engine/transitions.ts, which the parity points of the
// models artifact hold to riskvalidation. Drift: Engelmann's (2024) projection (9) of the rail's starting portfolio and
// the TTC portfolio (10) it drifts to. Intervals: the Wald (2.2) and Agresti-Coull (3.3) intervals of each grade's
// pooled counts with Schuermann and Hanson's (2004) effective number of obligors (3.4), and the equal-tailed Jeffreys
// interval, which has no correlation correction. Capital: the IRB risk weight of the variant's portfolio by grade under
// each PD definition and generator, at the card's LGD. Every number drawn here is live; the counts, the matrices and
// the PDs they start from are the artifact's. The published variant's Impact is PublishedViews' (Table 5's inputs).
//
// Two things the shell's chart does decide the layout: a mark's label is drawn beside its line wherever the canvas
// left the text alignment, so a mark at the edge of the plot is cut (year 1 is marked by a point instead, and a mark's
// label is kept short); and a filling card's note takes height from its drawing, so the notes say what is drawn and
// the tables' notes carry the rest.
import { Knob, PlotCard, SubTabs, formatNumber, pick, useShellLang, useWorkbenchState, type BiText, type ShellColorToken } from '@fasl-work/caos-app-shell';
import { UPlotChart, type ChartSeries } from '@fasl-work/caos-app-shell/chart';
import { useMemo } from 'react';
import { effectiveN, pdAgrestiCoull, pdJeffreys, pdWald, project, type Projection } from '../../engine/transitions';
import type { VariantArtifact } from '../../lib/contract.types';
import { provenanceOf } from '../model';
import { Pending } from '../Pending';
import { PublishedImpactView, RHO_GRID } from './PublishedViews';
import {
  DEFINITION_COLOR,
  DEFINITION_LABEL,
  ESMA_DEFINITIONS,
  ESTIMATOR_COLOR,
  GRADE_AXIS,
  GRADE_COLOR,
  GRADES,
  START_LABEL,
  definitionsOf,
  isAgency,
  isFamily,
  isPublished,
  liveChain,
  startPortfolio,
  useCapital,
  useIntervals,
  useProjection,
  type C04Sel,
  type CapitalRow,
  type Definition,
  type Estimator,
  type GradeIntervals,
  type StartPortfolio,
} from './selection';

const LIVE = 'live' as const;
type Lang = 'en' | 'es';
type Both = { en: string; es: string };

/** A bilingual text from one function of the language, so each number is formatted in its own language. */
export const both = (f: (lang: Lang) => string): Both => ({ en: f('en'), es: f('es') });
/** A shared label read in both languages. */
const twice = (t: BiText): Both => ({ en: pick(t, 'en'), es: pick(t, 'es') });
/** A probability as a percentage with three significant digits (a PD of 0.0049% and one of 27% both read). */
const pctd = (lang: Lang, v: number | null | undefined, digits = 3) => formatNumber(v, lang, { percent: true, digits });
/** A difference of two probabilities in percentage points, signed. */
const pp = (lang: Lang, v: number) => `${v > 0 ? '+' : ''}${formatNumber(v * 100, lang, { digits: 2 })} pp`;
/** Counts by grade in a sentence: a list separator that a thousands separator cannot be read as. */
const counts = (lang: Lang, xs: readonly number[]) => xs.map((x) => formatNumber(x, lang, { decimals: 0 })).join('; ');
/** A value a log axis can draw: positive and finite, else a gap. */
const onLog = (x: number | null | undefined): number | null => (x !== null && x !== undefined && Number.isFinite(x) && x > 0 ? x : null);
/** Series with at least one value: a series whose every value is null is left out of a chart, never drawn empty. */
export const drawable = (series: ChartSeries[]) => series.filter((s) => s.values.some((x) => x !== null));
/** A categorical axis of n positions with half a step of room on each side (C22's cited rates), so a point at the
 * first or last position is not cut by the plot's edge; `pad` gives a series the matching gap at each end. */
export const padded = (n: number) => [0.5, ...Array.from({ length: n }, (_, i) => i + 1), n + 0.5];
const pad = (s: ChartSeries): ChartSeries => ({ ...s, values: [null, ...s.values, null] });

function variantOf(sel: C04Sel | null): VariantArtifact<unknown> | null {
  return (sel?.data.variant as VariantArtifact<unknown> | undefined) ?? null;
}

/** The variant's short name as the manifest gives it (S&P, Moody's, Fitch). */
function shortName(sel: C04Sel): Both {
  const v = sel.data.variant as VariantArtifact<unknown>;
  const e = sel.data.manifest.artifacts.find((a) => a.variant_id === v.variant_id);
  const t = e?.short_title ?? e?.title;
  return t ? twice(t) : { en: v.variant_id, es: v.variant_id };
}

/** An English possessive that does not double a name's own: S&P's, Fitch's, and Moody's as it is. */
const possessive = (name: string) => (/'s$/.test(name) ? name : `${name}'s`);

/** Who the numbers are about and where they come from, closing a card's note: CEREP's attribution, verbatim, and the
 * agency's EU entity on an agency variant; on a generator family, the CEREP counts its known truth was fitted to. */
export function sourceNote(sel: C04Sel): Both {
  const v = sel.data.variant as VariantArtifact<unknown>;
  if (isAgency(v)) {
    const a = v.outputs.agency;
    const att = v.outputs.attribution;
    return { en: `${att}. Entity: ${a.name} (${a.code}).`, es: `Atribución: "${att}". Entidad: ${a.name} (${a.code}).` };
  }
  const att = sel.data.manifest.source_details?.['esma-cerep']?.attribution;
  return {
    en: `Known truth: the EM generator of S&P's pooled CEREP counts${att ? ` (${att})` : ''}.`,
    es: `Verdad conocida: el generador EM de los conteos agrupados de S&P en CEREP${att ? ` (atribución: "${att}")` : ''}.`,
  };
}

/** One explanation in place of a drawing: a view that cannot draw says why, in a table (a drawing surface). */
function ReasonTable({ reason }: { reason: BiText }) {
  const lang = useShellLang();
  return (
    <div className="ct-scroll">
      <table className="caos-table" data-table="reason">
        <tbody>
          <tr>
            <td className="caos-col-text">{pick(reason, lang)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// The group

/** The Impact group of an agency or a generator family: Drift, Intervals and Capital, each live. The published variant
 * holds no chain; its Impact is the live intervals at Table 5's inputs. */
export function ImpactView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const v = variantOf(sel);
  if (!sel || !v) return <Pending />;
  if (isPublished(v)) return <PublishedImpactView sel={sel} />;
  const tabs = [
    { id: 'drift', label: pick({ en: 'Drift', es: 'Deriva' }, lang), content: <DriftView sel={sel} /> },
    { id: 'intervals', label: pick({ en: 'Intervals', es: 'Intervalos' }, lang), content: <IntervalsView sel={sel} /> },
    { id: 'capital', label: pick({ en: 'Capital', es: 'Capital' }, lang), content: <CapitalView sel={sel} /> },
  ];
  return <SubTabs ariaLabel={pick({ en: 'Views of the impact', es: 'Vistas del impacto' }, lang)} tabs={tabs} />;
}

// ---------------------------------------------------------------------------------------------------------------------
// Drift: Engelmann's projection and his TTC portfolio

export type Drift =
  /** the projection with defaults: an agency with a default column, a family */
  | { kind: 'drift'; projection: Projection; w0: number[] }
  /** an agency without a default column (Moody's): the same propagation, which never defaults; the composition only */
  | { kind: 'composition'; projection: Projection; w0: number[] }
  | { kind: 'error'; message: string }
  | { kind: 'none' };

/** The drift of the rail's starting portfolio over the rail's horizon. On an agency whose transition page has no
 * default category the projection hook has no chain (no route to default); the matrix still moves the portfolio
 * between grades, so the same port propagates it without defaults and only its composition is shown. */
export function useDrift(sel: C04Sel | null): Drift | null {
  const live = useProjection(sel);
  const bare = useMemo((): Drift | null => {
    const v = variantOf(sel);
    if (!sel || !v || !isAgency(v) || liveChain(v)) return null;
    const o = v.outputs;
    const w0 = startPortfolio(sel.start, o.origination);
    try {
      return { kind: 'composition', projection: project(o.pooled.matrix, w0, o.origination, sel.horizon), w0 };
    } catch (e) {
      return { kind: 'error', message: String((e as Error).message ?? e) };
    }
  }, [sel]);
  if (!sel) return null;
  if (live) return 'error' in live ? { kind: 'error', message: live.error } : { kind: 'drift', projection: live.projection, w0: live.w0 };
  return bare ?? { kind: 'none' };
}

/** The year (1-based) whose projected default rate lies furthest from the TTC rate, and that signed gap; the earliest
 * such year on a tie. */
export function largestGap(rates: readonly number[], ttc: number): { year: number; gap: number } {
  let year = 1;
  let gap = rates[0] - ttc;
  for (let i = 1; i < rates.length; i++) {
    if (Math.abs(rates[i] - ttc) > Math.abs(gap)) {
      gap = rates[i] - ttc;
      year = i + 1;
    }
  }
  return { year, gap };
}

/** The marked points of the default-rate chart, by year: year 1 and the year of the largest gap to the TTC rate, one
 * point labelled with both when they coincide. Points, not vertical marks: year 1 is the plot's first position, where
 * a mark's label is cut. */
export function driftPoints(rates: readonly number[], ttc: number): ChartSeries[] {
  const g = largestGap(rates, ttc);
  const at = (year: number) => rates.map((r, i) => (i + 1 === year ? r : null));
  const first = (l: Lang) => `${l === 'en' ? 'Year 1' : 'Año 1'}: ${pctd(l, rates[0])}`;
  const gapText = (l: Lang) => `${l === 'en' ? 'largest gap' : 'mayor diferencia'} ${pp(l, g.gap)}`;
  if (g.year === 1) return [{ label: both((l) => `${first(l)}, ${gapText(l)}`), values: at(1), color: '--color-warn', mode: 'points' }];
  return [
    { label: both(first), values: at(1), color: '--color-warn', mode: 'points' },
    { label: both((l) => `${l === 'en' ? 'Year' : 'Año'} ${g.year}: ${gapText(l)}`), values: at(g.year), color: '--color-bad', mode: 'points' },
  ];
}

/** How the rail's starting portfolio is built, in words: the origination mix is the agency's pooled cohort mix, or a
 * family's design (its cohort sizes). */
function startText(start: StartPortfolio, agency: boolean): Both {
  if (start === 'origination') {
    return agency
      ? { en: "the agency's cohort mix pooled over the years", es: 'la composición de las cohortes de la agencia, agrupada en los años' }
      : { en: "the design's cohort mix", es: 'la composición de las cohortes del diseño' };
  }
  if (start === 'best') return { en: 'all of it in AAA', es: 'todo en AAA' };
  if (start === 'uniform') return { en: 'equal shares in the seven grades', es: 'partes iguales en los siete grados' };
  return { en: 'equal shares in BB, B and CCC-C', es: 'partes iguales en BB, B y CCC-C' };
}

export function DriftView({ sel }: { sel: C04Sel | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const drift = useDrift(sel);
  const v = variantOf(sel);
  if (!sel || !v || !drift) return <Pending />;
  const prov = provenanceOf(v.provenance.truth_status);
  const src = sourceNote(sel);
  const agency = isAgency(v) ? v : null;
  const family = isFamily(v) ? v : null;
  const start = twice(START_LABEL[sel.start]);
  const built = startText(sel.start, Boolean(agency));
  if (drift.kind === 'error' || drift.kind === 'none') {
    const reason =
      drift.kind === 'error'
        ? { en: `The projection refused this chain; the port's message: ${drift.message}`, es: `La proyección rechazó esta cadena; el mensaje del puerto: ${drift.message}` }
        : { en: 'This variant holds no one-year matrix, so there is nothing to project.', es: 'Esta variante no contiene una matriz anual, así que no hay nada que proyectar.' };
    return (
      <div className="caos-views-row" data-views="1">
        <div className="ct-col">
          <PlotCard fill title={{ en: 'Projected default rate', es: 'Tasa de incumplimiento proyectada' }} lane={LIVE} provenance={prov} dataKey={stateKey} note={reason}>
            <ReasonTable reason={reason} />
          </PlotCard>
        </div>
      </div>
    );
  }
  const p = drift.projection;
  const H = p.defaultRate.length;
  const name = shortName(sel);
  const cohorts = agency ? agency.outputs.cohorts.length : 0;
  const longRun = drift.kind === 'composition';
  const composition = (
    <CompositionCard
      sel={sel}
      projection={p}
      note={
        longRun
          ? {
              en: `${possessive(name.en)} transition page has no default category, so its pooled matrix has no default column: the portfolio never defaults, and Engelmann's (2024) projection (9) has no default rate to give, since his TTC portfolio (10) needs a default column to write off and re-originate. Drawn: the starting portfolio (${start.en}: ${built.en}) moved by the matrix alone (${cohorts} annual cohorts, withdrawals removed), each grade's share of the balance by year, the chosen grade thicker. ${src.en}`,
              es: `La página de transiciones de ${name.es} no tiene categoría de incumplimiento, así que su matriz agrupada no tiene columna de incumplimiento: la cartera nunca incumple, y la proyección (9) de Engelmann (2024) no tiene tasa de incumplimiento que dar, pues su cartera TTC (10) necesita una columna de incumplimiento para castigar y reoriginar. Se dibuja: la cartera inicial (${start.es}: ${built.es}) movida solo por la matriz (${cohorts} cohortes anuales, sin retiros), la fracción del saldo en cada grado por año, el grado elegido más grueso. ${src.es}`,
            }
          : {
              en: `Each grade's share of the balance at the start of each year, the chosen grade thicker; default holds nothing once the defaulted balance is re-originated.`,
              es: `La fracción del saldo en cada grado al inicio de cada año, el grado elegido más grueso; el incumplimiento no retiene nada una vez reoriginado el saldo incumplido.`,
            }
      }
    />
  );
  const table = (
    <PortfolioTable
      sel={sel}
      projection={p}
      w0={drift.w0}
      longRun={longRun}
      note={
        longRun
          ? {
              en: `Shares of the balance, with the L1 distance to the matrix's own long-run mix, to which the portfolio drifts with nothing leaving it; * the chosen grade. ${src.en}`,
              es: `Fracciones del saldo, con la distancia L1 a la mezcla de largo plazo de la propia matriz, hacia la que deriva la cartera sin que nada salga de ella; * el grado elegido. ${src.es}`,
            }
          : {
              en: `Shares of the balance: the start (${built.en}${family ? `, ${counts('en', family.outputs.generator.obligors)} obligors` : ''}), the mix after ${H} years and the TTC portfolio (10), with the L1 distance to it; * the chosen grade. ${src.en}`,
              es: `Fracciones del saldo: el inicio (${built.es}${family ? `, ${counts('es', family.outputs.generator.obligors)} deudores` : ''}), la mezcla tras ${H} años y la cartera TTC (10), con la distancia L1 a ella; * el grado elegido. ${src.es}`,
            }
      }
    />
  );
  if (longRun) {
    return (
      <>
        <div className="caos-views-row" data-views="1">
          <div className="ct-col">{composition}</div>
        </div>
        {table}
      </>
    );
  }
  const years = Array.from({ length: H }, (_, i) => i + 1);
  const ttc = p.ttc.defaultRate;
  const gap = largestGap(p.defaultRate, ttc);
  const d4 = twice(DEFINITION_LABEL.d4);
  const rateSeries: ChartSeries[] = [
    { label: { en: 'Projected', es: 'Proyectada' }, values: p.defaultRate, color: '--color-accent', width: 2.4 },
    { label: { en: `TTC rate ${pctd('en', ttc)}`, es: `Tasa TTC ${pctd('es', ttc)}` }, values: years.map(() => ttc), color: '--color-fg-subtle', width: 1.4, dash: [6, 4] },
    ...driftPoints(p.defaultRate, ttc),
  ];
  const chain: Both = agency
    ? {
        en: `${possessive(name.en)} pooled one-year matrix, defaults re-originated by the cohort mix; the rate is the matrix's default column ("${d4.en}", withdrawals removed)`,
        es: `la matriz anual agrupada de ${name.es}, con los incumplimientos reoriginados según la composición de las cohortes; la tasa es la columna de incumplimiento de la matriz ("${d4.es}", sin retiros)`,
      }
    : {
        en: "the generator's true one-year matrix exp(Q), defaults re-originated by the design's cohort mix",
        es: 'la matriz anual verdadera exp(Q) del generador, con los incumplimientos reoriginados según la composición de las cohortes del diseño',
      };
  return (
    <>
      <div className="caos-views-row" data-views="2">
        <div className="ct-col ct-share-3">
          <PlotCard
            fill
            title={{ en: `Projected default rate, start: ${start.en}`, es: `Tasa proyectada, inicio: ${start.es}` }}
            lane={LIVE}
            provenance={prov}
            dataKey={stateKey}
            note={{
              en: `Engelmann (2024), (9): the start projected under ${chain.en}. Dashed: the TTC rate (10); points: year 1, the largest gap (year ${gap.year}). ${src.en}`,
              es: `Engelmann (2024), (9): el inicio proyectado con ${chain.es}. Segmentada: la tasa TTC (10); puntos: el año 1, la mayor diferencia (año ${gap.year}). ${src.es}`,
            }}
          >
            <UPlotChart
              height="fill"
              x={{ values: [0.5, ...years, H + 0.5], label: { en: 'Year of the projection', es: 'Año de la proyección' }, unit: { en: 'years', es: 'años' }, format: { decimals: 0 } }}
              y={{ label: { en: 'Default rate', es: 'Tasa de incumpl.' }, format: { percent: true, digits: 3 } }}
              series={rateSeries.map(pad)}
            />
          </PlotCard>
        </div>
        <div className="ct-col ct-share-2">{composition}</div>
      </div>
      {table}
    </>
  );
}

/** The portfolio's mix by grade over the horizon: one series per grade, the chosen one thicker. */
function CompositionCard({ sel, projection, note }: { sel: C04Sel; projection: Projection; note: BiText }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const v = sel.data.variant as VariantArtifact<unknown>;
  const p = projection;
  const H = p.portfolio.length - 1;
  const steps = Array.from({ length: H + 1 }, (_, i) => i);
  const series: ChartSeries[] = GRADES.map((g, k) => ({
    label: k === sel.grade ? { en: `${g}, chosen grade`, es: `${g}, grado elegido` } : g,
    values: p.portfolio.map((w) => w[k]),
    color: GRADE_COLOR[k],
    width: k === sel.grade ? 3.2 : 1.5,
  }));
  return (
    <PlotCard
      fill
      title={{ en: "The portfolio's mix by grade", es: 'La composición de la cartera por grado' }}
      lane={LIVE}
      provenance={provenanceOf(v.provenance.truth_status)}
      dataKey={stateKey}
      note={note}
    >
      <UPlotChart
        height="fill"
        x={{ values: steps, label: { en: 'Years from the start', es: 'Años desde el inicio' }, unit: { en: 'years', es: 'años' }, format: { decimals: 0 } }}
        y={{ label: { en: 'Share of the balance', es: 'Fracción del saldo' }, format: { percent: true, decimals: 0 } }}
        series={drawable(series)}
      />
    </PlotCard>
  );
}

/** The start, the mix at the horizon and the TTC portfolio (or, without a default column, the matrix's long-run
 * mix), grade by grade across one table under the drawings, each with its L1 distance to the TTC portfolio. */
function PortfolioTable({ sel, projection, w0, longRun, note }: { sel: C04Sel; projection: Projection; w0: number[]; longRun: boolean; note: BiText }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = sel.data.variant as VariantArtifact<unknown>;
  const p = projection;
  const H = p.portfolio.length - 1;
  const rows: Array<{ key: string; label: BiText; shares: (number | null)[]; distance: number | null }> = [
    { key: 'start', label: { en: 'Start', es: 'Inicio' }, shares: w0, distance: p.distanceToTtc[0] },
    { key: 'horizon', label: { en: `After ${H} years`, es: `Tras ${H} años` }, shares: p.portfolio[H], distance: p.distanceToTtc[H] },
    {
      key: 'ttc',
      label: longRun ? { en: 'Long-run mix', es: 'Mezcla de largo plazo' } : { en: 'TTC portfolio (10)', es: 'Cartera TTC (10)' },
      shares: p.ttc.converged ? p.ttc.portfolio : GRADES.map(() => null),
      distance: p.ttc.converged ? 0 : null,
    },
  ];
  return (
    <PlotCard
      title={longRun ? { en: 'The start, the horizon and the long-run mix', es: 'El inicio, el horizonte y la mezcla de largo plazo' } : { en: 'The start, the horizon and the TTC portfolio', es: 'El inicio, el horizonte y la cartera TTC' }}
      lane={LIVE}
      provenance={provenanceOf(v.provenance.truth_status)}
      dataKey={stateKey}
      note={note}
    >
      <table className="caos-table ct-wrap-head" data-table="ttc-portfolio">
        <thead>
          <tr>
            <th>{pick({ en: 'Portfolio', es: 'Cartera' }, lang)}</th>
            {GRADES.map((g, k) => (
              <th key={g}>{k === sel.grade ? `${g} *` : g}</th>
            ))}
            <th>{pick(longRun ? { en: 'L1 to the long-run mix', es: 'L1 a la mezcla de largo plazo' } : { en: 'L1 to TTC', es: 'L1 a TTC' }, lang)}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key} data-row={r.key}>
              <td>{pick(r.label, lang)}</td>
              {GRADES.map((g, k) => (
                <td key={g}>{r.shares[k] === null || r.shares[k] === undefined ? '-' : pctd(lang, r.shares[k])}</td>
              ))}
              <td>{r.distance === null ? '-' : formatNumber(r.distance, lang, { decimals: 3 })}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </PlotCard>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// Intervals: Wald, Agresti-Coull and Jeffreys for every grade

const METHODS: Array<{ key: 'wald' | 'agrestiCoull' | 'jeffreys'; label: Both; color: ShellColorToken }> = [
  { key: 'wald', label: { en: 'Wald', es: 'Wald' }, color: '--color-warn' },
  { key: 'agrestiCoull', label: { en: 'Agresti-Coull', es: 'Agresti-Coull' }, color: '--color-magenta' },
  { key: 'jeffreys', label: { en: 'Jeffreys', es: 'Jeffreys' }, color: '--color-accent' },
];

/** The series of the intervals chart, by grade on a log axis: each method's upper and lower bounds, the observed rate
 * D / N and, on a generator family, the true one-year PD; a bound of 0 is a gap (a log axis has no 0). Series whose
 * every value is a gap are returned apart, so the note can name them. */
export function intervalSeries(rows: GradeIntervals[], truth: readonly number[] | null): { drawn: ChartSeries[]; dropped: ChartSeries[] } {
  const at = (f: (r: GradeIntervals) => number) =>
    GRADES.map((_, g) => {
      const r = rows.find((x) => x.grade === g);
      return r ? onLog(f(r)) : null;
    });
  const series: ChartSeries[] = METHODS.flatMap((m) => [
    { label: { en: `${m.label.en}, upper`, es: `${m.label.es}, superior` }, values: at((r) => r[m.key].upper), color: m.color, width: 2 },
    { label: { en: `${m.label.en}, lower`, es: `${m.label.es}, inferior` }, values: at((r) => r[m.key].lower), color: m.color, width: 1.4, dash: [5, 4] },
  ]);
  series.push({ label: { en: 'Observed D / N', es: 'Observada D / N' }, values: at((r) => r.defaults / r.n), color: '--color-fg', mode: 'points' });
  if (truth) series.push({ label: { en: 'True one-year PD', es: 'PD anual verdadera' }, values: truth.map(onLog), color: '--color-good', width: 1.4, dash: [2, 3] });
  const drawn = drawable(series);
  return { drawn, dropped: series.filter((s) => !drawn.includes(s)) };
}

/** The chosen grade's interval widths along the default correlation (0 to 5%, the rail's range) at a level: how fast
 * N dagger (3.4) widens Wald and Agresti-Coull, beside Jeffreys, which ignores the correlation; a width of 0 is a gap
 * on the log axis (Wald at D = 0). */
export function widthSeries(defaults: number, n: number, level: number): ChartSeries[] {
  const jeffreys = pdJeffreys(defaults, n, { level }).length;
  return drawable([
    { label: { en: 'Wald width', es: 'Ancho Wald' }, values: RHO_GRID.map((rho) => onLog(pdWald(defaults, n, { level, rho }).length)), color: '--color-warn', width: 2 },
    { label: { en: 'Agresti-Coull width', es: 'Ancho Agresti-Coull' }, values: RHO_GRID.map((rho) => onLog(pdAgrestiCoull(defaults, n, { level, rho }).length)), color: '--color-magenta', width: 2 },
    { label: { en: 'Jeffreys width, no correlation', es: 'Ancho Jeffreys, sin correlación' }, values: RHO_GRID.map(() => onLog(jeffreys)), color: '--color-accent', width: 1.4, dash: [5, 4] },
  ]);
}

export function IntervalsView({ sel }: { sel: C04Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const rows = useIntervals(sel);
  const v = variantOf(sel);
  if (!sel || !v) return <Pending />;
  const prov = provenanceOf(v.provenance.truth_status);
  const src = sourceNote(sel);
  const agency = isAgency(v) ? v : null;
  const family = isFamily(v) ? v : null;
  const name = shortName(sel);
  const level = both((l) => formatNumber(sel.level, l, { percent: true, decimals: 0 }));
  const rho = both((l) => formatNumber(sel.rho, l, { percent: true, decimals: 1 }));
  const def = twice(DEFINITION_LABEL[sel.definition]);
  const title = { en: `Intervals for the PD of each grade at ${level.en}, correlation ${rho.en}`, es: `Intervalos para la PD de cada grado al ${level.es}, correlación ${rho.es}` };
  if (rows.length === 0) {
    // an agency whose pages do not give this definition (Moody's has no D4 or Keep): the counts it does give
    const defs = agency ? definitionsOf(agency.outputs).filter((d) => d !== 'keep' && agency.outputs.lra[d as 'd2' | 'd3' | 'd4']) : [];
    const note = {
      en: `${agency ? `${possessive(name.en)} pages give no "${def.en}": its transition page has no default category, so there are no counts to bound. The pooled counts it does give, D defaults of N ratings by definition, are in the table; pick one of those definitions in the rail.` : 'This variant gives no counts by grade.'} ${src.en}`,
      es: `${agency ? `Las páginas de ${name.es} no dan "${def.es}": su página de transiciones no tiene categoría de incumplimiento, así que no hay conteos que acotar. Los conteos agrupados que sí da, D incumplimientos de N calificaciones por definición, están en la tabla; elija una de esas definiciones en el panel.` : 'Esta variante no da conteos por grado.'} ${src.es}`,
    };
    return (
      <div className="caos-views-row" data-views="1">
        <div className="ct-col">
          <PlotCard fill title={title} lane={LIVE} provenance={prov} dataKey={stateKey} note={note}>
            {agency && defs.length ? (
              <div className="ct-scroll">
                <table className="caos-table" data-table="counts-by-definition">
                  <thead>
                    <tr>
                      <th>{pick({ en: 'Grade', es: 'Grado' }, lang)}</th>
                      {defs.map((d) => (
                        <th key={d}>{`${pick(DEFINITION_LABEL[d], lang)}, D / N`}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {GRADES.map((g, k) => (
                      <tr key={g} className={k === sel.grade ? 'ct-current' : undefined}>
                        <td>{g}</td>
                        {defs.map((d) => {
                          const l = agency.outputs.lra[d as 'd2' | 'd3' | 'd4'];
                          return <td key={d}>{l ? `${formatNumber(l.defaults[k], lang, { decimals: 0 })} / ${formatNumber(l.n[k], lang, { decimals: 0 })}` : '-'}</td>;
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <ReasonTable reason={note} />
            )}
          </PlotCard>
        </div>
      </div>
    );
  }
  const truth = family ? family.outputs.generator.pd_1y : null;
  const { drawn, dropped } = intervalSeries(rows, truth);
  const droppedText = (l: Lang) =>
    dropped.length ? (l === 'en' ? ` Not drawn, every value 0: ${dropped.map((s) => pick(s.label, 'en')).join('; ')}.` : ` Sin dibujar, todo valor 0: ${dropped.map((s) => pick(s.label, 'es')).join('; ')}.`) : '';
  // Schuermann and Hanson's rule of thumb for the Wald interval: PD N = D at least 10
  const thin = rows.filter((r) => r.defaults < 10).map((r) => GRADES[r.grade]);
  const thumb = (l: Lang) =>
    thin.length
      ? l === 'en'
        ? ` Their rule of thumb for Wald, D = PD N of at least 10, fails in ${thin.join(', ')}; at D = 0 the Wald interval collapses to a point.`
        : ` Su regla práctica para Wald, D = PD N de al menos 10, falla en ${thin.join(', ')}; con D = 0 el intervalo de Wald se reduce a un punto.`
      : '';
  const first = agency?.outputs.cohorts[0]?.label ?? '';
  const last = agency?.outputs.cohorts[agency.outputs.cohorts.length - 1]?.label ?? '';
  const basis: Both = agency
    ? {
        en: `each grade's pooled counts under the definition "${def.en}" over ${possessive(name.en)} ${agency.outputs.cohorts.length} annual cohorts (${first} to ${last})`,
        es: `los conteos agrupados de cada grado con la definición "${def.es}" sobre las ${agency.outputs.cohorts.length} cohortes anuales de ${name.es} (${first} a ${last})`,
      }
    : {
        en: "each grade's design counts, beside the truth (dotted)",
        es: 'los conteos del diseño de cada grado, junto a la verdad (punteada)',
      };
  const countsText: Both = agency
    ? { en: 'D defaults among N ratings, pooled over the cohorts.', es: 'D incumplimientos entre N calificaciones, agrupados en las cohortes.' }
    : {
        en: `N the obligors by grade times the ${family?.outputs.design.years ?? ''} years observed (obligor-years), D the defaults expected at the true one-year PD, rounded: an interval that misses the truth misses the PD it was built for.`,
        es: `N los deudores por grado por los ${family?.outputs.design.years ?? ''} años observados (deudor-años), D los incumplimientos esperados a la PD anual verdadera, redondeados: un intervalo que no contiene la verdad no contiene la PD para la que se construyó.`,
      };
  const chosenRow = rows.find((r) => r.grade === sel.grade);
  const widths = chosenRow ? widthSeries(chosenRow.defaults, chosenRow.n, sel.level) : [];
  const G = GRADES[sel.grade];
  const top = RHO_GRID[RHO_GRID.length - 1];
  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col">
        <PlotCard
          fill
          title={title}
          lane={LIVE}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `Schuermann and Hanson (2004) on ${basis.en}: Wald (2.2) and Agresti-Coull (3.3) with the effective number of obligors N† (3.4) at the rail's correlation; Jeffreys has no correlation correction. Log scale, a bound of 0 is a gap. Marked: the chosen grade. ${src.en}`,
            es: `Schuermann y Hanson (2004) sobre ${basis.es}: Wald (2.2) y Agresti-Coull (3.3) con el número efectivo de deudores N† (3.4) a la correlación del panel; Jeffreys no tiene corrección por correlación. Escala logarítmica, una cota de 0 queda en blanco. Marcado: el grado elegido. ${src.es}`,
          }}
        >
          <UPlotChart
            height="fill"
            x={{ values: padded(GRADES.length), label: GRADE_AXIS, format: { decimals: 0 } }}
            y={{ label: { en: 'PD bound (log scale)', es: 'Cota de la PD (escala log.)' }, log: true, format: { percent: true, digits: 2 } }}
            series={drawn.map(pad)}
            marks={[{ x: sel.grade + 1, label: G }]}
          />
        </PlotCard>
      </div>
      <div className="ct-col">
        <PlotCard
          fill
          title={{ en: 'Counts, effective obligors and widths', es: 'Conteos, deudores efectivos y anchos' }}
          lane={LIVE}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `${countsText.en} N† = N / (1 + (N - 1) rho) at a correlation of ${rho.en} between every pair (3.4); the widths are the upper less the lower bound at ${level.en}, in percentage points. Jeffreys, the equal-tailed Beta(D + 1/2, N - D + 1/2) interval, is the posterior of independent trials: it ignores the correlation.${thumb('en')}${droppedText('en')}`,
            es: `${countsText.es} N† = N / (1 + (N - 1) rho) con una correlación de ${rho.es} entre cada par (3.4); los anchos son la cota superior menos la inferior al ${level.es}, en puntos porcentuales. Jeffreys, el intervalo de colas iguales Beta(D + 1/2, N - D + 1/2), es la posterior de ensayos independientes: ignora la correlación.${thumb('es')}${droppedText('es')}`,
          }}
        >
          <div className="ct-scroll">
            <table className="caos-table ct-wrap-head" data-table="intervals">
              <thead>
                <tr>
                  <th>{pick({ en: 'Grade', es: 'Grado' }, lang)}</th>
                  <th>D</th>
                  <th>N</th>
                  <th>N† (3.4)</th>
                  <th>{pick({ en: 'Wald width', es: 'Ancho Wald' }, lang)}</th>
                  <th className="ct-room-only">{pick({ en: 'Agresti-Coull width', es: 'Ancho Agresti-Coull' }, lang)}</th>
                  <th>{pick({ en: 'Jeffreys width', es: 'Ancho Jeffreys' }, lang)}</th>
                  <th className="ct-room-only">{pick({ en: 'Observed D / N', es: 'Observada D / N' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.grade} data-grade={GRADES[r.grade]} className={r.grade === sel.grade ? 'ct-current' : undefined}>
                    <td>{GRADES[r.grade]}</td>
                    <td>{formatNumber(r.defaults, lang, { decimals: 0 })}</td>
                    <td>{formatNumber(r.n, lang, { decimals: 0 })}</td>
                    <td>{formatNumber(r.nEffective, lang, { digits: 4 })}</td>
                    <td>{formatNumber(r.wald.length * 100, lang, { digits: 3 })}</td>
                    <td className="ct-room-only">{formatNumber(r.agrestiCoull.length * 100, lang, { digits: 3 })}</td>
                    <td>{formatNumber(r.jeffreys.length * 100, lang, { digits: 3 })}</td>
                    <td className="ct-room-only">{pctd(lang, r.defaults / r.n)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
        <div className="ct-tall-only">
          <PlotCard
            fill
            title={{ en: `How the correlation widens ${G}'s intervals`, es: `Cómo la correlación ensancha los intervalos de ${G}` }}
            lane={LIVE}
            provenance={prov}
            dataKey={stateKey}
            note={
              chosenRow
                ? {
                    en: `${G}: ${formatNumber(chosenRow.defaults, 'en', { decimals: 0 })} defaults of ${formatNumber(chosenRow.n, 'en', { decimals: 0 })}; N† falls from ${formatNumber(chosenRow.n, 'en', { decimals: 0 })} with independent defaults to ${formatNumber(effectiveN(chosenRow.n, top), 'en', { digits: 3 })} at a correlation of ${formatNumber(top, 'en', { percent: true, decimals: 0 })}. Widths at ${level.en}, log scale; Jeffreys' does not move. Marked: the rail's correlation.`,
                    es: `${G}: ${formatNumber(chosenRow.defaults, 'es', { decimals: 0 })} incumplimientos de ${formatNumber(chosenRow.n, 'es', { decimals: 0 })}; N† cae de ${formatNumber(chosenRow.n, 'es', { decimals: 0 })} con incumplimientos independientes a ${formatNumber(effectiveN(chosenRow.n, top), 'es', { digits: 3 })} con una correlación de ${formatNumber(top, 'es', { percent: true, decimals: 0 })}. Anchos al ${level.es}, escala logarítmica; el de Jeffreys no se mueve. Marcada: la correlación del panel.`,
                  }
                : { en: `${G} has no counts under this definition, so it has no interval to widen.`, es: `${G} no tiene conteos con esta definición, así que no tiene intervalo que ensanchar.` }
            }
          >
            {widths.length ? (
              <UPlotChart
                height="fill"
                x={{ values: RHO_GRID, label: { en: 'Default correlation between every pair', es: 'Correlación de incumplimiento entre cada par' }, format: { percent: true, decimals: 2 } }}
                y={{ label: { en: 'Interval width (log scale)', es: 'Ancho del intervalo (escala log.)' }, log: true, format: { percent: true, digits: 2 } }}
                series={widths}
                marks={[{ x: sel.rho, label: { en: 'rail', es: 'panel' } }]}
              />
            ) : (
              <ReasonTable reason={{ en: `${G} has no counts under this definition.`, es: `${G} no tiene conteos con esta definición.` }} />
            )}
          </PlotCard>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// Capital: the IRB risk weight under each PD definition and generator

const REGIME_TEXT: Record<string, Both> = {
  basel3: { en: 'Basel III final', es: 'Basilea III final' },
  crr3: { en: 'CRR3', es: 'CRR3' },
  basel2: { en: 'Basel II', es: 'Basilea II' },
};
const CLASS_TEXT: Record<string, Both> = { corporate: { en: 'corporate', es: 'corporativa' } };
/** A capital row's name on the categorical axis, short enough for the axis title to fit its chart. */
const AXIS_NAME: Record<string, Both> = {
  d2: { en: 'D2', es: 'D2' },
  d3: { en: 'D3', es: 'D3' },
  d4: { en: 'D4', es: 'D4' },
  em: { en: 'EM', es: 'EM' },
  diagonal: { en: 'diagonal', es: 'diagonal' },
  weighted: { en: 'weighted', es: 'ponderado' },
  jlt: { en: 'JLT', es: 'JLT' },
};
const isGenerator = (key: string) => key in ESTIMATOR_COLOR && !(key in DEFINITION_COLOR);

/** The colour of a capital row: its definition's or its generator's, the truth's on a family. Some definitions and
 * generators share a colour (D2 and EM, D3 and the diagonal adjustment); their points are numbered and their lines
 * dashed apart. */
function rowColor(key: string): ShellColorToken {
  if (key in DEFINITION_COLOR) return DEFINITION_COLOR[key as Definition];
  if (key in ESTIMATOR_COLOR) return ESTIMATOR_COLOR[key as Estimator];
  return '--color-good';
}

/** The PD floor, in a note's words. */
const floorText = (floor: number, ref: string) =>
  both((l) =>
    l === 'en'
      ? `every PD below the ${formatNumber(floor, 'en', { percent: true, decimals: 2 })} floor (${ref}) takes the floor, a PD of 0 (a grade that never defaulted) among them`
      : `toda PD bajo el piso de ${formatNumber(floor, 'es', { percent: true, decimals: 2 })} (${ref}) toma el piso, una PD de 0 (un grado que nunca incumplió) entre ellas`,
  );
const peakText = both((l) =>
  l === 'en'
    ? `The risk weight peaks near a PD of ${formatNumber(0.3, 'en', { percent: true, decimals: 0 })} and falls beyond it, where the expected loss the formula deducts grows faster.`
    : `El ponderador alcanza su máximo cerca de una PD de ${formatNumber(0.3, 'es', { percent: true, decimals: 0 })} y cae más allá, donde la pérdida esperada que la fórmula descuenta crece más rápido.`,
);

/** The knob of the capital card: the LGD of every exposure, a field of the selection. */
function LgdKnob({ sel }: { sel: C04Sel }) {
  return (
    <Knob
      id="c04-lgd"
      label={{ en: 'LGD', es: 'LGD' }}
      hint={{
        en: 'Loss given default of every exposure; 45% is the F-IRB senior unsecured LGD for financial institutions (CRE32.6).',
        es: 'Pérdida dado el incumplimiento de toda exposición; 45% es la LGD F-IRB senior no garantizada de instituciones financieras (CRE32.6).',
      }}
      value={sel.lgd}
      min={0.1}
      max={0.9}
      step={0.05}
      format={{ percent: true, decimals: 0 }}
      onChange={sel.act.setLgd}
    />
  );
}

export function CapitalView({ sel }: { sel: C04Sel | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const rows = useCapital(sel);
  const v = variantOf(sel);
  if (!sel || !v) return <Pending />;
  const prov = provenanceOf(v.provenance.truth_status);
  const src = sourceNote(sel);
  const g = sel.grade;
  const lgd = both((l) => formatNumber(sel.lgd, l, { percent: true, decimals: 0 }));
  if (isFamily(v)) return <FamilyCapital sel={sel} rows={rows} lgd={lgd} src={src} />;
  const agency = isAgency(v) ? v : null;
  const name = shortName(sel);
  const irb = agency?.outputs.irb;
  const code = (ref: string | undefined) => (ref ?? '').split(' ')[0];
  const floor = irb ? floorText(irb.pd_floor, code(irb.references.pd_floor)) : { en: '', es: '' };
  const convention: Both = irb
    ? {
        en: `${(REGIME_TEXT[irb.regime] ?? { en: irb.regime }).en}, ${(CLASS_TEXT[irb.asset_class] ?? { en: irb.asset_class }).en}, ${code(irb.references.risk_weight)}; maturity ${formatNumber(irb.maturity, 'en', { decimals: 1 })} years, ${code(irb.references.maturity)}`,
        es: `${(REGIME_TEXT[irb.regime] ?? { es: irb.regime }).es}, ${(CLASS_TEXT[irb.asset_class] ?? { es: irb.asset_class }).es}, ${code(irb.references.risk_weight)}; vencimiento ${formatNumber(irb.maturity, 'es', { decimals: 1 })} años, ${code(irb.references.maturity)}`,
      }
    : { en: '', es: '' };
  const drawnRows = rows.filter((r) => r.result && r.result.average !== null);
  // a row without a PD for some grade holding exposure (Moody's generators) is left out of the chart and said why; a
  // row the port refused says the port's reason
  const missing = rows.filter((r) => r.result && r.result.average === null);
  const failed = rows.filter((r) => !r.result);
  const axisName = (r: CapitalRow, l: Lang) => (AXIS_NAME[r.key] ?? twice(r.label))[l];
  const order = (l: Lang) => drawnRows.map((r, i) => `${i + 1} ${axisName(r, l)}`).join(', ');
  const x = padded(drawnRows.length);
  // one point per drawn row at its position, numbered as on the axis (two pairs of rows share a colour)
  const series: ChartSeries[] = drawnRows.map((r, i) => ({
    label: { en: `${i + 1} ${pick(r.label, 'en')}`, es: `${i + 1} ${pick(r.label, 'es')}` },
    values: drawnRows.map((_, j) => (j === i ? r.result?.average ?? null : null)),
    color: rowColor(r.key),
    mode: 'points',
  }));
  series.push({
    label: { en: `${GRADES[g]}'s own risk weight`, es: `Ponderador propio de ${GRADES[g]}` },
    values: drawnRows.map((r) => onLog(r.result?.riskWeights[g])),
    color: '--color-fg',
    mode: 'points',
  });
  const chartSeries = drawable(series).map(pad);
  // the tall screen's second drawing: every drawn row's risk weight grade by grade (generators dashed), and the chosen
  // grade's spread across them
  const byGrade = drawable(
    drawnRows.map((r) => ({ label: r.label, values: (r.result?.riskWeights ?? []).map(onLog), color: rowColor(r.key), width: 1.8, ...(isGenerator(r.key) ? { dash: [6, 3] } : {}) })),
  ).map(pad);
  const atGrade = drawnRows
    .map((r) => ({ label: r.label, value: r.result?.riskWeights[g] ?? null }))
    .filter((y): y is { label: BiText; value: number } => y.value !== null);
  const spread = atGrade.length
    ? { lo: atGrade.reduce((a, b) => (b.value < a.value ? b : a)), hi: atGrade.reduce((a, b) => (b.value > a.value ? b : a)) }
    : null;
  const keepMissing = agency !== null && agency.outputs.pd.keep !== null;
  const keep = twice(DEFINITION_LABEL.keep);
  const missingText = (l: Lang) => {
    const parts: string[] = [];
    if (missing.length) {
      const why = agency && !liveChain(agency);
      parts.push(
        l === 'en'
          ? `No PD, so no risk weight: ${missing.map((r) => pick(r.label, 'en')).join(', ')}${why ? ` (${possessive(name.en)} transition page has no default category, so its generators reach no default)` : ''}.`
          : `Sin PD, así que sin ponderador: ${missing.map((r) => pick(r.label, 'es')).join(', ')}${why ? ` (la página de transiciones de ${name.es} no tiene categoría de incumplimiento, así que sus generadores no llegan al incumplimiento)` : ''}.`,
      );
    }
    if (failed.length) {
      parts.push(
        l === 'en'
          ? `Refused by the port: ${failed.map((r) => `${pick(r.label, 'en')} (${r.error ?? ''})`).join('; ')}.`
          : `Rechazadas por el puerto: ${failed.map((r) => `${pick(r.label, 'es')} (mensaje del puerto: ${r.error ?? ''})`).join('; ')}.`,
      );
    }
    if (keepMissing) parts.push(l === 'en' ? `"${keep.en}" has no long-run average in the artifact, so no row.` : `"${keep.es}" no tiene promedio de largo plazo en el artefacto, así que no tiene fila.`);
    return parts.length ? ` ${parts.join(' ')}` : '';
  };
  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col ct-share-3">
        <PlotCard
          fill
          title={{ en: `Risk weight of ${possessive(name.en)} cohort mix by PD definition, LGD ${lgd.en}`, es: `Ponderador de la composición de cohortes de ${name.es} por definición de PD, LGD ${lgd.es}` }}
          lane={LIVE}
          provenance={prov}
          dataKey={stateKey}
          actions={<LgdKnob sel={sel} />}
          note={{
            en: `The IRB risk weight (${convention.en}) per unit of EAD at the knob's LGD, of ${possessive(name.en)} cohort mix pooled over the years: one point per PD definition (its long-run average) and generator (exp(Q)'s one-year default column), and the chosen grade's own; log scale.${missing.length || failed.length ? ' A row without a PD has no point (the table says why).' : ''} ${pick(ESMA_DEFINITIONS, 'en')} ${src.en}`,
            es: `El ponderador IRB (${convention.es}) por unidad de EAD a la LGD de la perilla, de la composición de cohortes de ${name.es} agrupada en los años: un punto por definición de PD (su promedio de largo plazo) y por generador (la columna de incumplimiento a un año de exp(Q)), y el propio del grado elegido; escala logarítmica.${missing.length || failed.length ? ' Una fila sin PD no tiene punto (la tabla dice por qué).' : ''} ${pick(ESMA_DEFINITIONS, 'es')} ${src.es}`,
          }}
        >
          {chartSeries.length ? (
            <UPlotChart
              height="fill"
              x={{ values: x, label: { en: `PD definition or generator: ${order('en')}`, es: `Definición de PD o generador: ${order('es')}` }, format: { decimals: 0 } }}
              y={{ label: { en: 'Risk weight, share of EAD (log scale)', es: 'Ponderador, fracción de la EAD (escala log.)' }, log: true, format: { percent: true, digits: 3 } }}
              series={chartSeries}
            />
          ) : (
            <ReasonTable reason={{ en: 'No definition gives a PD for every grade with exposure.', es: 'Ninguna definición da una PD para cada grado con exposición.' }} />
          )}
        </PlotCard>
      </div>
      <div className="ct-col ct-share-2">
        <PlotCard
          fill
          title={{ en: 'Risk weights by definition', es: 'Ponderadores por definición' }}
          lane={LIVE}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `Share of EAD at LGD ${lgd.en}: the chosen grade's PD and risk weight under each definition (its long-run average, EBA/GL/2017/16 paragraph 84) and generator, beside the portfolio's average; ${floor.en}.${missingText('en')} ${peakText.en}`,
            es: `Fracción de la EAD con LGD ${lgd.es}: la PD y el ponderador del grado elegido con cada definición (su promedio de largo plazo, párrafo 84 de EBA/GL/2017/16) y generador, junto al promedio de la cartera; ${floor.es}.${missingText('es')} ${peakText.es}`,
          }}
        >
          <div className="ct-scroll">
            <CapitalTable rows={rows} grade={g} />
          </div>
        </PlotCard>
        <div className="ct-tall-only">
          <PlotCard
            fill
            title={{ en: 'Risk weight by grade under each definition', es: 'Ponderador por grado con cada definición' }}
            lane={LIVE}
            provenance={prov}
            dataKey={stateKey}
            note={{
              en: `Each definition's and generator's (dashed) risk weight grade by grade at LGD ${lgd.en}, log scale: where the lines part, the definition decides the capital.${spread ? ` ${GRADES[g]} runs from ${pctd('en', spread.lo.value)} (${pick(spread.lo.label, 'en')}) to ${pctd('en', spread.hi.value)} (${pick(spread.hi.label, 'en')}).` : ''} Marked: the chosen grade.`,
              es: `El ponderador de cada definición y generador (segmentados) grado a grado con LGD ${lgd.es}, escala logarítmica: donde las líneas se separan, la definición decide el capital.${spread ? ` ${GRADES[g]} va de ${pctd('es', spread.lo.value)} (${pick(spread.lo.label, 'es')}) a ${pctd('es', spread.hi.value)} (${pick(spread.hi.label, 'es')}).` : ''} Marcado: el grado elegido.`,
            }}
          >
            {byGrade.length ? (
              <UPlotChart
                height="fill"
                x={{ values: padded(GRADES.length), label: GRADE_AXIS, format: { decimals: 0 } }}
                y={{ label: { en: 'Risk weight, share of EAD (log scale)', es: 'Ponderador, fracción de la EAD (escala log.)' }, log: true, format: { percent: true, digits: 3 } }}
                series={byGrade}
                marks={[{ x: g + 1, label: GRADES[g] }]}
              />
            ) : (
              <ReasonTable reason={{ en: 'No definition gives a PD for every grade with exposure.', es: 'Ninguna definición da una PD para cada grado con exposición.' }} />
            )}
          </PlotCard>
        </div>
      </div>
    </div>
  );
}

/** The capital rows: each definition's and generator's PD and risk weight for the chosen grade, and the average. */
function CapitalTable({ rows, grade }: { rows: CapitalRow[]; grade: number }) {
  const lang = useShellLang();
  return (
    <table className="caos-table ct-wrap-head" data-table="capital">
      <thead>
        <tr>
          <th className="ct-text">{pick({ en: 'PD definition or generator', es: 'Definición de PD o generador' }, lang)}</th>
          <th>{pick({ en: `${GRADES[grade]} PD`, es: `PD de ${GRADES[grade]}` }, lang)}</th>
          <th>{pick({ en: `${GRADES[grade]} risk weight`, es: `Ponderador de ${GRADES[grade]}` }, lang)}</th>
          <th>{pick({ en: 'Average risk weight', es: 'Ponderador medio' }, lang)}</th>
          <th className="ct-text ct-room-only">{pick({ en: 'Risk weight, AAA to CCC-C', es: 'Ponderador, AAA a CCC-C' }, lang)}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.key} data-row={r.key} title={r.error ?? undefined}>
            <td className="ct-text">{pick(r.label, lang)}</td>
            <td>{r.pds[grade] === null || r.pds[grade] === undefined ? '-' : pctd(lang, r.pds[grade])}</td>
            <td>{r.result?.riskWeights[grade] === null || r.result?.riskWeights[grade] === undefined ? '-' : pctd(lang, r.result.riskWeights[grade])}</td>
            <td>{r.result?.average === null || r.result?.average === undefined ? '-' : pctd(lang, r.result.average)}</td>
            <td className="ct-text ct-room-only">{r.result ? r.result.riskWeights.map((w) => (w === null ? '-' : formatNumber(w, lang, { percent: true, decimals: 0 }))).join('; ') : '-'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** A generator family's capital: one PD, the truth, so the risk weight is drawn grade by grade, the portfolio average
 * beside it. The convention is the case's (useCapital: Basel III final, corporate, maturity 2.5 years). */
function FamilyCapital({ sel, rows, lgd, src }: { sel: C04Sel; rows: CapitalRow[]; lgd: Both; src: Both }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = sel.data.variant as VariantArtifact<unknown>;
  const prov = provenanceOf(v.provenance.truth_status);
  const family = isFamily(v) ? v : null;
  const truth = rows.find((r) => r.key === 'truth') ?? rows[0];
  const obligors = family?.outputs.generator.obligors ?? [];
  const total = obligors.reduce((a, b) => a + b, 0);
  const rw = truth?.result?.riskWeights ?? [];
  const avg = truth?.result?.average ?? null;
  const floor = floorText(0.0005, 'CRE32.4');
  const series = drawable([
    { label: { en: 'Risk weight at the true one-year PD', es: 'Ponderador a la PD anual verdadera' }, values: GRADES.map((_, k) => onLog(rw[k])), color: '--color-good', width: 2.2 },
    {
      label: { en: `Portfolio average ${avg === null ? '' : pctd('en', avg)}`.trim(), es: `Promedio de la cartera ${avg === null ? '' : pctd('es', avg)}`.trim() },
      values: GRADES.map(() => onLog(avg)),
      color: '--color-fg-subtle',
      width: 1.4,
      dash: [6, 4],
    },
  ]).map(pad);
  const g = sel.grade;
  // each grade's share of the obligors and of the risk-weighted exposure (one unit of EAD per obligor)
  const share = obligors.map((x) => (total > 0 ? x / total : 0));
  const weighted = share.map((x, k) => {
    const w = rw[k];
    return avg !== null && avg > 0 && w !== null && w !== undefined ? (x * w) / avg : null;
  });
  const speculative = [4, 5, 6];
  const sits = {
    obligors: speculative.reduce((a, k) => a + share[k], 0),
    capital: speculative.reduce((a, k) => a + (weighted[k] ?? 0), 0),
  };
  const sitsSeries = drawable([
    { label: { en: 'Share of the obligors', es: 'Fracción de los deudores' }, values: share, color: '--color-fg-subtle', width: 1.6, dash: [6, 4] },
    { label: { en: 'Share of the risk-weighted exposure', es: 'Fracción de la exposición ponderada por riesgo' }, values: weighted, color: '--color-good', width: 2.2 },
  ]).map(pad);
  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col ct-share-3">
        <PlotCard
          fill
          title={{ en: `Risk weight by grade at the true PD, LGD ${lgd.en}`, es: `Ponderador por grado a la PD verdadera, LGD ${lgd.es}` }}
          lane={LIVE}
          provenance={prov}
          dataKey={stateKey}
          actions={<LgdKnob sel={sel} />}
          note={{
            en: `The IRB risk weight (Basel III final, corporate, CRE31.5; maturity 2.5 years, CRE32.44) per unit of EAD at the knob's LGD, of each grade at the generator's true one-year PD, the only PD a known truth has; dashed, the average over the design's obligors. Log scale; marked: the chosen grade. ${src.en}`,
            es: `El ponderador IRB (Basilea III final, corporativa, CRE31.5; vencimiento 2,5 años, CRE32.44) por unidad de EAD a la LGD de la perilla, de cada grado a la PD anual verdadera del generador, la única PD que tiene una verdad conocida; segmentada, el promedio sobre los deudores del diseño. Escala logarítmica; marcado: el grado elegido. ${src.es}`,
          }}
        >
          {series.length ? (
            <UPlotChart
              height="fill"
              x={{ values: padded(GRADES.length), label: GRADE_AXIS, format: { decimals: 0 } }}
              y={{ label: { en: 'Risk weight, share of EAD (log scale)', es: 'Ponderador, fracción de la EAD (escala log.)' }, log: true, format: { percent: true, digits: 3 } }}
              series={series}
              marks={[{ x: g + 1, label: GRADES[g] }]}
            />
          ) : (
            <ReasonTable reason={{ en: `The risk weight could not be computed; the port's message: ${truth?.error ?? ''}`, es: `El ponderador no se pudo calcular; el mensaje del puerto: ${truth?.error ?? ''}` }} />
          )}
        </PlotCard>
      </div>
      <div className="ct-col ct-share-2">
        <PlotCard
          fill
          title={{ en: 'Risk weight by grade', es: 'Ponderador por grado' }}
          lane={LIVE}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `Share of EAD at LGD ${lgd.en}; the design's obligors (${counts('en', obligors)}, AAA to CCC-C) weigh the average; ${floor.en}. ${peakText.en}`,
            es: `Fracción de la EAD con LGD ${lgd.es}; los deudores del diseño (${counts('es', obligors)}, de AAA a CCC-C) ponderan el promedio; ${floor.es}. ${peakText.es}`,
          }}
        >
          <div className="ct-scroll">
            <table className="caos-table" data-table="capital">
              <thead>
                <tr>
                  <th>{pick({ en: 'Grade', es: 'Grado' }, lang)}</th>
                  <th>{pick({ en: 'Obligors', es: 'Deudores' }, lang)}</th>
                  <th>{pick({ en: 'True PD', es: 'PD verdadera' }, lang)}</th>
                  <th>{pick({ en: 'Risk weight', es: 'Ponderador' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {GRADES.map((name, k) => (
                  <tr key={name} className={k === g ? 'ct-current' : undefined}>
                    <td>{name}</td>
                    <td>{formatNumber(obligors[k], lang, { decimals: 0 })}</td>
                    <td>{pctd(lang, truth?.pds[k])}</td>
                    <td>{pctd(lang, rw[k])}</td>
                  </tr>
                ))}
                <tr data-row="average">
                  <td>{pick({ en: 'Portfolio', es: 'Cartera' }, lang)}</td>
                  <td>{formatNumber(total, lang, { decimals: 0 })}</td>
                  <td>-</td>
                  <td>{pctd(lang, avg)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </PlotCard>
        <div className="ct-tall-only">
          <PlotCard
            fill
            title={{ en: 'Where the capital sits', es: 'Dónde está el capital' }}
            lane={LIVE}
            provenance={prov}
            dataKey={stateKey}
            note={{
              en: `Each grade's share of the obligors (one unit of EAD each) and of the risk-weighted exposure at the true PD: the speculative grades BB, B and CCC-C hold ${pctd('en', sits.obligors)} of the obligors and ${pctd('en', sits.capital)} of the capital. Marked: the chosen grade.`,
              es: `La fracción de los deudores de cada grado (una unidad de EAD cada uno) y de la exposición ponderada por riesgo a la PD verdadera: los grados especulativos BB, B y CCC-C tienen ${pctd('es', sits.obligors)} de los deudores y ${pctd('es', sits.capital)} del capital. Marcado: el grado elegido.`,
            }}
          >
            <UPlotChart
              height="fill"
              x={{ values: padded(GRADES.length), label: GRADE_AXIS, format: { decimals: 0 } }}
              y={{ label: { en: 'Share of the portfolio', es: 'Fracción de la cartera' }, format: { percent: true, decimals: 0 } }}
              series={sitsSeries}
              marks={[{ x: g + 1, label: GRADES[g] }]}
            />
          </PlotCard>
        </div>
      </div>
    </div>
  );
}
