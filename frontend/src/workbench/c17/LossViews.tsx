// C17's Loss group: the exceedance curve of the annual loss of the generator (log scale, Monte Carlo, Panjer and FFT
// overlaid, the true 99.9 percent quantile and the single loss approximation marked), and the stability of the fitted
// tail index across thresholds with the infinite-mean flag. Each draws what the c17-outputs document carries; a mean
// the document does not carry (a tail index of 1 or more) is not available, with the reason, and nothing replaces it.
import { Callout, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart, type UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable } from '../c06/format';
import { useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { KeyTable } from './KeyTable';
import { C17TestsTable } from './Tests';
import { AGGREGATION_TEXT, cellLabel, cellOf, outputsOf, text, whole, type C17Outputs, type C17Sel } from './selection';
import { es } from './localise';

type Chart = Pick<UPlotChartProps, 'x' | 'y' | 'series' | 'marks' | 'yMarks'>;

/** A probability on a log axis: a zero has no place there, so it is left out (a gap), never drawn as a number. */
const positive = (v: number | null): number | null => (v !== null && v > 0 ? v : null);

/**
 * The exceedance chart of the true annual loss: P(annual loss > x) on log-log axes with the three aggregations
 * overlaid. The true 99.9 percent quantile and the single loss approximation are vertical marks, and the level
 * 1 - 0.999 is a horizontal reference line. Pure, so a test reads the very values the chart draws.
 */
export function exceedanceChart(e: C17Outputs['exceedance'], truth?: C17Outputs['truth']): Chart {
  const level = truth ? truth.annual_loss_quantile.level : 0.999;
  return {
    x: {
      values: e.grid_eur.map((v) => v / 1e6),
      label: { en: 'Annual loss', es: 'Pérdida anual' },
      unit: { en: 'mn EUR', es: 'M EUR' },
      log: true,
      format: { digits: 3 },
    },
    y: {
      label: { en: 'Probability of exceeding', es: 'Probabilidad de superar' },
      log: true,
      format: { percent: true, digits: 3 },
    },
    series: [
      { label: { en: 'Monte Carlo', es: 'Monte Carlo' }, values: e.monte_carlo.exceedance.map(positive), color: '--color-fg-subtle', width: 2.4 },
      { label: { en: 'Panjer recursion', es: 'Recursión de Panjer' }, values: e.panjer.exceedance.map(positive), color: '--color-accent', width: 2.4, dash: [7, 4] },
      { label: { en: 'FFT', es: 'FFT' }, values: e.fft.exceedance.map(positive), color: '--color-magenta', width: 2, dash: [2, 3] },
    ],
    marks: truth
      ? [
          { x: truth.annual_loss_quantile.value_eur / 1e6, label: { en: 'True 99.9% quantile', es: 'Cuantil verdadero 99,9 %' } },
          { x: e.quantile_999_eur.sla / 1e6, label: { en: 'SLA', es: 'SLA' } },
        ]
      : [{ x: e.quantile_999_eur.sla / 1e6, label: { en: 'SLA', es: 'SLA' } }],
    yMarks: [{ y: 1 - level, label: { en: '99.9% level', es: 'Nivel 99,9 %' }, tone: 'neutral' }],
  };
}

/** The exceedance curve with the quantile of every method beside the true one, and the benchmark test under it. */
export function ExceedanceView({ sel }: { sel: C17Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const e = o.exceedance;
  const t = o.truth;
  const q = t.annual_loss_quantile;
  const chart = exceedanceChart(e, t);
  // the Panjer recursion computes the probabilities up to the end of its grid only: the points after it are absent in the document.
  // The sentence names the last point of the axis inside the grid, never the end of the grid itself, which lies between that point
  // and the next one (U16-R4 c21 B1: the step times the point count puts the end up to 1.6 times later)
  const lastPanjer = e.panjer.exceedance.map((v) => v !== null).lastIndexOf(true);
  const panjerEnd = lastPanjer >= 0 && lastPanjer < e.grid_eur.length - 1 ? e.grid_eur[lastPanjer] : null;
  // the FFT too stops where its grid ends (U16-R3 c18 B2: past it the bake held the last value flat; the re-bake writes nulls)
  const lastFft = (e.fft.exceedance as Array<number | null>).map((v) => v !== null).lastIndexOf(true);
  const fftEnd = lastFft >= 0 && lastFft < e.grid_eur.length - 1 ? e.grid_eur[lastFft] : null;
  const rows: Array<{ id: string; label: BiText; value: number; how: BiText }> = [
    {
      id: 'true',
      label: { en: 'True quantile of the generator', es: 'Cuantil verdadero del generador' },
      value: q.value_eur,
      how: {
        en: `${text(AGGREGATION_TEXT, q.method).en} on a grid of ${whole(q.grid_step_eur, 'en')} EUR; Monte Carlo check with ${whole(q.mc_check.n_years, 'en')} years gives ${whole(q.mc_check.value_eur, 'en')} EUR, standard error ${whole(q.mc_check.standard_error_eur, 'en')} EUR`,
        es: `${text(AGGREGATION_TEXT, q.method).es} en una grilla de ${whole(q.grid_step_eur, 'es')} EUR; la verificación Monte Carlo con ${whole(q.mc_check.n_years, 'es')} años da ${whole(q.mc_check.value_eur, 'es')} EUR, error estándar ${whole(q.mc_check.standard_error_eur, 'es')} EUR`,
      },
    },
    { id: 'monte-carlo', label: { en: 'Monte Carlo', es: 'Monte Carlo' }, value: e.quantile_999_eur.monte_carlo, how: { en: `${whole(e.monte_carlo.n_years, 'en')} simulated years, seed ${e.monte_carlo.seed}`, es: `${whole(e.monte_carlo.n_years, 'es')} años simulados, semilla ${e.monte_carlo.seed}` } },
    { id: 'panjer', label: { en: 'Panjer recursion', es: 'Recursión de Panjer' }, value: e.quantile_999_eur.panjer, how: { en: `step ${whole(e.panjer.step_eur, 'en')} EUR${panjerEnd === null ? '' : `; its last point inside the grid is ${whole(panjerEnd, 'en')} EUR and the curve stops there`}`, es: `paso de ${whole(e.panjer.step_eur, 'es')} EUR${panjerEnd === null ? '' : `; su último punto dentro de la grilla es ${whole(panjerEnd, 'es')} EUR y la curva se detiene ahí`}` } },
    { id: 'fft', label: { en: 'FFT', es: 'FFT' }, value: e.quantile_999_eur.fft, how: { en: `${whole(e.fft.n_points, 'en')} points, padding factor ${e.fft.padding_factor}, tilt ${formatNumber(e.fft.tilt, 'en', { digits: 3 })}${fftEnd === null ? '' : `; its last point inside the grid is ${whole(fftEnd, 'en')} EUR and the curve stops there`}`, es: `${whole(e.fft.n_points, 'es')} puntos, factor de relleno ${e.fft.padding_factor}, inclinación ${formatNumber(e.fft.tilt, 'es', { digits: 3 })}${fftEnd === null ? '' : `; su último punto dentro de la grilla es ${whole(fftEnd, 'es')} EUR y la curva se detiene ahí`}` } },
    { id: 'sla', label: { en: 'Single loss approximation', es: 'Aproximación de una pérdida' }, value: e.quantile_999_eur.sla, how: { en: 'closed form, from the true severity and frequency', es: 'forma cerrada, desde la severidad y la frecuencia verdaderas' } },
  ];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Exceedance curve of the annual loss', es: 'Curva de excedencia de la pérdida anual' }}
        {...card}
        note={{
          en: 'The probability that the annual loss of the generator exceeds each value, on log axes. Monte Carlo, Panjer recursion and FFT are three computations of the same distribution; the true 99.9 percent quantile and the single loss approximation are marked. Where the curve crosses the level 0.1 percent is the capital. The Panjer cross-check runs on a coarser grid (its step is in the table), so at the smallest losses its curve can sit below the other two.',
          es: 'La probabilidad de que la pérdida anual del generador supere cada valor, en ejes logarítmicos. Monte Carlo, recursión de Panjer y FFT son tres cálculos de la misma distribución; se marcan el cuantil verdadero al 99,9 por ciento y la aproximación de una pérdida. Donde la curva cruza el nivel de 0,1 por ciento está el capital. La verificación de Panjer corre en una grilla más gruesa (su paso está en la tabla), así que en las pérdidas menores su curva puede quedar bajo las otras dos.',
        }}
      >
        <ChartOverTable chart={<UPlotChart height="fill" {...chart} />}>
          <table className="caos-table ct-wrap-head" data-table="quantile-999">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Method', es: 'Método' }, lang)}</th>
                <th>{pick({ en: '99.9% quantile (EUR)', es: 'Cuantil 99,9 % (EUR)' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'How', es: 'Cómo' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} data-method={r.id}>
                  <td className="ct-text">{pick(r.label, lang)}</td>
                  <td>{whole(r.value, lang)}</td>
                  <td className="ct-text ct-wide-only">{pick(r.how, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head ct-wide-only" data-table="exceedance-grid">
            <thead>
              <tr>
                <th>{pick({ en: 'Loss (EUR)', es: 'Pérdida (EUR)' }, lang)}</th>
                <th>{pick({ en: 'Monte Carlo', es: 'Monte Carlo' }, lang)}</th>
                <th>{pick({ en: 'Panjer', es: 'Panjer' }, lang)}</th>
                <th>FFT</th>
              </tr>
            </thead>
            <tbody>
              {e.grid_eur.map((x, i) => (
                <tr key={x} data-x={x}>
                  <td>{whole(x, lang)}</td>
                  <td>{formatNumber(e.monte_carlo.exceedance[i], lang, { digits: 4 })}</td>
                  <td>{formatNumber(e.panjer.exceedance[i], lang, { digits: 4 })}</td>
                  <td>{formatNumber(e.fft.exceedance[i], lang, { digits: 4 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <C17TestsTable variant={sel.data.variant} host="exceedance" />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/**
 * The threshold-stability chart: the fitted tail index across the replications (the 5th, 50th and 95th percentile) at
 * each threshold, with the true tail index and the boundary of 1 as reference lines. Pure, so a test reads its values.
 */
export function stabilityChart(rows: C17Outputs['cells'][number]['threshold_stability'], tailIndex: number): Chart {
  return {
    x: {
      values: rows.map((r) => r.threshold_eur / 1e3),
      label: { en: 'Threshold above which the tail is fitted', es: 'Umbral sobre el cual se ajusta la cola' },
      unit: { en: 'thousand EUR', es: 'mil EUR' },
      format: { decimals: 0 },
    },
    y: {
      label: { en: 'Fitted tail index', es: 'Índice de cola ajustado' },
      format: { decimals: 2 },
    },
    series: [
      { label: { en: '5th percentile of the fits', es: 'Percentil 5 de los ajustes' }, values: rows.map((r) => r.tail_index.p05), color: '--color-fg-subtle', width: 1.6, dash: [3, 3] },
      { label: { en: 'Median of the fits', es: 'Mediana de los ajustes' }, values: rows.map((r) => r.tail_index.median), color: '--color-accent', width: 2.6 },
      { label: { en: '95th percentile of the fits', es: 'Percentil 95 de los ajustes' }, values: rows.map((r) => r.tail_index.p95), color: '--color-magenta', width: 1.6, dash: [3, 3] },
    ],
    yMarks: [
      { y: tailIndex, label: { en: 'True tail index', es: 'Índice de cola verdadero' }, tone: 'good' },
      { y: 1, label: { en: 'Infinite mean from 1', es: 'Media infinita desde 1' }, tone: 'bad' },
    ],
  };
}

/** The tail index fitted above each threshold, the share of fits with an infinite mean, and the true mean when it exists. */
export function TailIndexView({ sel }: { sel: C17Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const cell = cellOf(o, sel.years, sel.threshold);
  const mean = o.truth.annual_loss_mean;
  const label = cellLabel(cell.years, cell.collection_threshold_eur);
  if (cell.threshold_stability.length === 0) {
    return (
      <ViewsRow>
        <PlotCard fill title={{ en: `Tail index across thresholds: ${label.en}`, es: `Índice de cola entre umbrales: ${label.es}` }} {...card}>
          <p className="ct-note" data-state="unavailable">{pick({ en: 'Not available: this cell carries no threshold-stability profile, so no chart is drawn.', es: 'No disponible: esta celda no trae el perfil de estabilidad por umbral, así que no se dibuja ningún gráfico.' }, lang)}</p>
        </PlotCard>
      </ViewsRow>
    );
  }
  const chart = stabilityChart(cell.threshold_stability, o.tail_index);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `Tail index across thresholds: ${label.en}`, es: `Índice de cola entre umbrales: ${label.es}` }}
        {...card}
        note={{
          en: 'The generalised Pareto tail index fitted to the losses above each threshold, over the independent histories of the cell: the median and the band from the 5th to the 95th percentile. A stable tail index is a flat line near the true one; a fit at 1 or above implies an infinite mean, and the share of such fits is in the table.',
          es: 'El índice de cola de la Pareto generalizada ajustado a las pérdidas sobre cada umbral, en las historias independientes de la celda: la mediana y la banda del percentil 5 al 95. Un índice de cola estable es una línea plana cerca del verdadero; un ajuste en 1 o más implica una media infinita, y la proporción de esos ajustes está en la tabla.',
        }}
      >
        <ChartOverTable chart={<UPlotChart height="fill" {...chart} />}>
          <div data-infinite-mean={String(o.infinite_mean)}>
            {o.infinite_mean ? (
              <Callout variant="strong" title={pick({ en: 'Infinite mean', es: 'Media infinita' }, lang)}>
                {pick(
                  {
                    en: `The true tail index is ${formatNumber(o.tail_index, 'en', { digits: 3 })}, which is 1 or more: the severity has an infinite mean, so the annual loss has no mean and no mean-based quantity is computed for this variant.`,
                    es: `El índice de cola verdadero es ${formatNumber(o.tail_index, 'es', { digits: 3 })}, que es 1 o más: la severidad tiene media infinita, así que la pérdida anual no tiene media y no se calcula ninguna cantidad basada en la media en esta variante.`,
                  },
                  lang,
                )}
              </Callout>
            ) : null}
            <KeyTable
              table="tail-truth"
              rows={[
                { id: 'tail-index', label: { en: 'True tail index', es: 'Índice de cola verdadero' }, value: formatNumber(o.tail_index, lang, { digits: 3 }), attrs: { 'data-tail-index': String(o.tail_index) } },
                {
                  id: 'mean',
                  label: { en: 'True annual mean', es: 'Media anual verdadera' },
                  value: mean.value_eur === null ? `${formatNumber(null, lang)} (${es(mean.reason, lang)})` : `${whole(mean.value_eur, lang)} EUR`,
                  attrs: { 'data-mean': mean.value_eur === null ? 'not-available' : 'available' },
                },
              ]}
            />
          </div>
          <table className="caos-table ct-wrap-head" data-table="threshold-stability">
            <thead>
              <tr>
                <th>{pick({ en: 'Threshold (EUR)', es: 'Umbral (EUR)' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Exceedances, median', es: 'Excedencias, mediana' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Fits', es: 'Ajustes' }, lang)}</th>
                <th>{pick({ en: '5th percentile', es: 'Percentil 5' }, lang)}</th>
                <th>{pick({ en: 'Median', es: 'Mediana' }, lang)}</th>
                <th>{pick({ en: '95th percentile', es: 'Percentil 95' }, lang)}</th>
                <th>{pick({ en: 'Fits with index of 1 or more', es: 'Ajustes con índice de 1 o más' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {cell.threshold_stability.map((r) => (
                <tr key={r.threshold_eur} data-threshold={r.threshold_eur}>
                  <td>{whole(r.threshold_eur, lang)}</td>
                  <td className="ct-wide-only">{formatNumber(r.n_exceedances_median, lang, { digits: 4 })}</td>
                  <td className="ct-wide-only">{whole(r.n_fits, lang)}</td>
                  <td>{formatNumber(r.tail_index.p05, lang, { digits: 3 })}</td>
                  <td>{formatNumber(r.tail_index.median, lang, { digits: 3 })}</td>
                  <td>{formatNumber(r.tail_index.p95, lang, { digits: 3 })}</td>
                  <td>{formatNumber(r.share_at_least_one, lang, { percent: true, decimals: 2 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <C17TestsTable variant={sel.data.variant} host="tail" cell={cell.id} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
