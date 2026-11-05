// C08's Models group: the LGD models side by side, realised against predicted LGD by default cohort, the calibration by
// bucket of predicted LGD, and the sensitivity of the beta regression to its endpoint shift. A model with no number in
// this document says so with its reason; a realised LGD outside [0, 1] keeps its flag.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { UPlotChart, parityRange, type ChartTick } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable, MaybeNumber } from '../c06/format';
import { Flagged, U6TestsTable, p2, useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { cohortLabel, cohortYear, outputsOf, rungLabel, type C08Sel } from './selection';
import { YEAR_FORMAT, withPortfolioScope } from './words';
import { CohortName } from './DownturnViews';

export { YEAR_FORMAT };

// fixed decimals, so models that differ in the third decimal never read 0.17 beside 0.175 (R3 c09 m1)
const d3 = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 3 });
const d4 = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 4 });
const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });

/** The steps a whole-percent axis may tick at, finest first. */
const PERCENT_STEPS = [0.01, 0.02, 0.05, 0.1, 0.2, 0.25, 0.5, 1];

/**
 * The x ticks of a parity chart at whole percents, at most six over the parity box: two-decimal tick labels ("50.00 % 60.00 % ...")
 * nearly touched at 1280 (R5 c11 n5), while the readout keeps the axis format's two decimals (a named tick labels only an x that sits
 * on it).
 */
export function wholePercentTicks(...arrays: ReadonlyArray<ReadonlyArray<number | null>>): ChartTick[] {
  const [lo, hi] = parityRange(...arrays);
  const step = PERCENT_STEPS.find((s) => (hi - lo) / s <= 6) ?? 1;
  const ticks: ChartTick[] = [];
  for (let k = Math.ceil(lo / step - 1e-9); k * step <= hi + 1e-9; k += 1) {
    const v = Math.round(k * step * 1e6) / 1e6;
    ticks.push({ value: v, label: { en: formatNumber(v, 'en', { percent: true, decimals: 0 }), es: formatNumber(v, 'es', { percent: true, decimals: 0 }) } });
  }
  return ticks;
}

/** A card that says why there is nothing to draw for the model in focus, in place of an empty chart. */
function NoRows({ sel, title, why }: { sel: C08Sel; title: { en: string; es: string }; why: { en: string; es: string } }) {
  const lang = useShellLang();
  const card = useCard(sel.data.variant);
  return (
    <ViewsRow>
      <PlotCard fill title={title} {...card}>
        <p className="caos-pending" data-state="unavailable">
          {pick(why, lang)}
        </p>
      </PlotCard>
    </ViewsRow>
  );
}

/** The LGD models on the test cohort: error, rank correlation and the calibration gap, and the tests the engine returned. */
export function RungsView({ sel }: { sel: C08Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const label = (id: string) => rungLabel(sel, id);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The LGD models on this cohort', es: 'Los modelos de LGD en esta cohorte' }}
        {...card}
        note={{
          en: 'Error of each model on the defaults of this cohort (RMSE, lower is better), with R squared, MAE, the rank correlation and the calibration gap in the table. A statistic that is not defined for a model has no number, and its reason says why.',
          es: 'Error de cada modelo sobre los incumplimientos de esta cohorte (RMSE, menor es mejor), con R cuadrado, MAE, la correlación de rangos y la brecha de calibración en la tabla. Un estadístico no definido para un modelo no tiene número, y su razón dice por qué.',
        }}
      >
        <ChartOverTable
          chart={
            <BarChart
              title={{ en: 'RMSE by model', es: 'RMSE por modelo' }}
              height="fill"
              orientation="horizontal"
              data={o.rung_comparison.map((r) => ({ id: r.rung_id, label: label(r.rung_id), value: r.rmse, tone: 'accent' as const, highlight: r.rung_id === sel.rung, hint: label(r.rung_id) }))}
              // three fixed decimals, as the table: 0.300 beside 0.297, never 0.3 (R4 c10 m1)
              axis={{ label: { en: 'RMSE of the LGD', es: 'RMSE de la LGD' }, format: { decimals: 3 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="lgd-rungs">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Model', es: 'Modelo' }, lang)}</th>
                <th>R²</th>
                <th>RMSE</th>
                <th className="ct-wide-only">MAE</th>
                <th>Spearman</th>
                <th>{pick({ en: 'Calibration gap', es: 'Brecha de calibración' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.rung_comparison.map((r) => (
                <tr key={r.rung_id} data-rung={r.rung_id} className={r.rung_id === sel.rung ? 'ct-current' : undefined}>
                  <td className="ct-text" title={r.rung_id}>{pick(label(r.rung_id), lang)}</td>
                  <td>
                    <MaybeNumber value={r.r2} reason={r.reason} format={(v) => d3(v, lang)} />
                  </td>
                  <td>{d3(r.rmse, lang)}</td>
                  <td className="ct-wide-only">{d3(r.mae, lang)}</td>
                  <td>
                    <MaybeNumber value={r.spearman} reason={null} format={(v) => d3(v, lang)} />
                  </td>
                  <td>{p2(r.calibration_gap, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <U6TestsTable variant={withPortfolioScope(sel.data.variant, lang)} modelLabel={(id) => pick(label(id), lang)} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** Realised against predicted mean LGD for each default cohort, for the model in focus, with the interval of the realised mean. */
export function RealisedView({ sel }: { sel: C08Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const rows = o.realised_vs_predicted.filter((r) => r.rung_id === sel.rung).sort((a, b) => cohortYear(sel, a.cohort_id) - cohortYear(sel, b.cohort_id));
  if (rows.length === 0) {
    return (
      <NoRows
        sel={sel}
        title={{ en: 'Realised against predicted LGD', es: 'LGD realizada contra predicha' }}
        why={{ en: 'Not available: this document has no realised-against-predicted row for the model in focus.', es: 'No disponible: este documento no trae filas de realizada contra predicha para el modelo en foco.' }}
      />
    );
  }
  const years = rows.map((r) => cohortYear(sel, r.cohort_id));
  // a variant that tests one cohort (dc-2020-23) has one x value: drawn as points on a range of a year each side, since a one-point
  // line draws nothing and uPlot ranged a single year to 0..4,000 (R2b c09 B1)
  const single = years.length < 2;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Realised against predicted LGD, by default cohort', es: 'LGD realizada contra predicha, por cohorte de incumplimiento' }}
        {...card}
        note={{
          en: 'The mean LGD realised by the defaults of each cohort with its interval, against the mean the model predicted. A cohort whose predicted mean lies below the interval of the realised mean was under-predicted. The horizontal axis is the first default year of the cohort.',
          es: 'La LGD media realizada por los incumplimientos de cada cohorte con su intervalo, contra la media que predijo el modelo. Una cohorte cuya media predicha queda bajo el intervalo de la media realizada fue subpredicha. El eje horizontal es el primer año de incumplimiento de la cohorte.',
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: years, label: { en: 'First default year of the cohort', es: 'Primer año de incumplimiento de la cohorte' }, format: YEAR_FORMAT, ...(single ? { range: [years[0] - 1, years[0] + 1] as [number, number] } : {}) }}
              y={{ label: { en: 'Mean LGD', es: 'LGD media' }, format: { percent: true, decimals: 2 } }}
              zoomOff={single ? { en: 'One cohort: a single point has no range to zoom.', es: 'Una cohorte: un solo punto no tiene rango que acercar.' } : undefined}
              series={[
                { label: { en: 'Realised', es: 'Realizada' }, values: rows.map((r) => r.realised.value), color: '--color-accent', width: 2.6, ...(single ? { mode: 'points' as const, size: 11 } : {}) },
                { label: { en: 'Interval, low', es: 'Intervalo, inferior' }, values: rows.map((r) => r.ci_low), color: '--color-accent', width: 1, dash: [3, 3], ...(single ? { mode: 'points' as const, size: 6 } : {}) },
                { label: { en: 'Interval, high', es: 'Intervalo, superior' }, values: rows.map((r) => r.ci_high), color: '--color-accent', width: 1, dash: [3, 3], ...(single ? { mode: 'points' as const, size: 6 } : {}) },
                { label: { en: 'Predicted', es: 'Predicha' }, values: rows.map((r) => r.predicted.value), color: '--color-magenta', width: 2, dash: [6, 3], ...(single ? { mode: 'points' as const, size: 9 } : {}) },
              ]}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="lgd-realised">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Default cohort', es: 'Cohorte de incumplimiento' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Defaults', es: 'Incumplimientos' }, lang)}</th>
                <th>{pick({ en: 'Realised', es: 'Realizada' }, lang)}</th>
                <th>{pick({ en: 'Predicted', es: 'Predicha' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Interval of the realised', es: 'Intervalo de la realizada' }, lang)}</th>
                <th>{pick({ en: 'Gap', es: 'Brecha' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.cohort_id} data-cohort={r.cohort_id} className={r.cohort_id === sel.cohort ? 'ct-current' : undefined}>
                  <td className="ct-text"><CohortName name={pick(cohortLabel(sel, r.cohort_id), lang)} /></td>
                  <td className="ct-wide-only">{count(r.n, lang)}</td>
                  <td>
                    <Flagged value={r.realised.value} flag={r.realised.flag} />
                  </td>
                  <td>{p2(r.predicted.value, lang)}</td>
                  <td className="ct-wide-only">{`${p2(r.ci_low, lang)} ${pick({ en: 'to', es: 'a' }, lang)} ${p2(r.ci_high, lang)}`}</td>
                  <td>{p2(r.gap, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** Predicted against realised mean LGD by bucket of predicted LGD, for the model in focus. */
export function CalibrationView({ sel }: { sel: C08Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const rows = o.calibration_by_bucket.filter((r) => r.rung_id === sel.rung);
  if (rows.length === 0) {
    return (
      <NoRows
        sel={sel}
        title={{ en: 'Calibration by bucket of predicted LGD', es: 'Calibración por tramo de LGD predicha' }}
        why={{ en: 'Not available: this document has no calibration buckets for the model in focus.', es: 'No disponible: este documento no trae tramos de calibración para el modelo en foco.' }}
      />
    );
  }
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Calibration by bucket of predicted LGD', es: 'Calibración por tramo de LGD predicha' }}
        {...card}
        note={{
          en: 'The defaults are cut into buckets by predicted LGD: the predicted mean on the horizontal axis, the realised mean on the vertical one; the identity line is a perfect calibration.',
          es: 'Los incumplimientos se cortan en tramos por LGD predicha: la media predicha en el eje horizontal, la realizada en el vertical; la línea identidad es una calibración perfecta.',
        }}
      >
        <ChartOverTable
          // the parity box is square on the height it gets: 22 rem, so it is not a 180 px square in a wide card (R4 c10 m10)
          chartMin="22rem"
          chart={
            <UPlotChart
              height="fill"
              parity
              x={{ values: rows.map((r) => r.predicted.value), label: { en: 'Predicted mean LGD', es: 'LGD media predicha' }, format: { percent: true, decimals: 2 }, ticks: wholePercentTicks(rows.map((r) => r.predicted.value), rows.map((r) => r.realised.value)) }}
              y={{ label: { en: 'Realised mean LGD', es: 'LGD media realizada' }, format: { percent: true, decimals: 2 } }}
              series={[{ label: { en: 'Realised', es: 'Realizada' }, values: rows.map((r) => r.realised.value), color: '--color-accent', mode: 'points', size: 10 }]}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="lgd-buckets">
            <thead>
              <tr>
                <th>{pick({ en: 'Bucket', es: 'Tramo' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Defaults', es: 'Incumplimientos' }, lang)}</th>
                <th>{pick({ en: 'Predicted', es: 'Predicha' }, lang)}</th>
                <th>{pick({ en: 'Realised', es: 'Realizada' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.bucket} data-bucket={r.bucket}>
                  <td>{r.bucket}</td>
                  <td className="ct-wide-only">{count(r.n, lang)}</td>
                  <td>{p2(r.predicted.value, lang)}</td>
                  <td>
                    <Flagged value={r.realised.value} flag={r.realised.flag} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The beta regression cannot take a 0 or a 1: the endpoints are shifted by epsilon, and the prediction moves with it. */
export function EndpointsView({ sel }: { sel: C08Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const rows = [...o.endpoint_sensitivity].sort((a, b) => a.epsilon - b.epsilon);
  const eps = (e: number) => (lang === 'es' ? String(e).replace('.', ',') : String(e));
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Sensitivity to the endpoint shift', es: 'Sensibilidad al desplazamiento de los extremos' }}
        {...card}
        note={{
          en: 'Beta regression needs a response strictly inside (0, 1), so the LGDs of exactly 0 and 1 are moved in by a small shift epsilon. A prediction that moves with epsilon depends on that choice, which is why the shift is stated and tried at several sizes.',
          es: 'La regresión beta necesita una respuesta estrictamente dentro de (0, 1), así que las LGD de exactamente 0 y 1 se mueven hacia adentro en un desplazamiento pequeño epsilon. Una predicción que se mueve con epsilon depende de esa elección, por eso el desplazamiento se declara y se prueba en varios tamaños.',
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: rows.map((r) => r.epsilon), label: { en: 'Endpoint shift epsilon', es: 'Desplazamiento de los extremos epsilon' }, log: true, format: { notation: 'scientific', digits: 2 } }}
              y={{ label: { en: 'Mean predicted LGD', es: 'LGD media predicha' }, format: { percent: true, decimals: 2 } }}
              series={[
                { label: { en: 'Mean predicted LGD', es: 'LGD media predicha' }, values: rows.map((r) => r.mean_predicted.value), color: '--color-accent', width: 2.4 },
              ]}
              marks={[{ x: sel.epsilon, label: { en: 'In focus', es: 'En foco' } }]}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="lgd-endpoints">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Model', es: 'Modelo' }, lang)}</th>
                <th>{pick({ en: 'Shift', es: 'Desplazamiento' }, lang)}</th>
                <th>{pick({ en: 'Mean predicted LGD', es: 'LGD media predicha' }, lang)}</th>
                <th>RMSE</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.epsilon} data-epsilon={r.epsilon} className={r.epsilon === sel.epsilon ? 'ct-current' : undefined}>
                  <td className="ct-text" title={r.rung_id}>{pick(rungLabel(sel, r.rung_id), lang)}</td>
                  <td>{eps(r.epsilon)}</td>
                  <td>{p2(r.mean_predicted.value, lang)}</td>
                  <td>{d4(r.rmse, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
