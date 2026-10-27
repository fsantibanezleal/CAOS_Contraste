// C10's Simulator group: the exact size and power of the correlation estimates on a simulator with a known correlation.
// The known correlation is the truth and is always read beside the estimates: the rejection rate of H0 at the null
// correlation is the size where the known correlation is the null and the power elsewhere, and the mean estimate is drawn
// against the line of the truth. A replication that failed is counted, never dropped silently.
import { PlotCard, ViewsRow, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable } from '../c06/format';
import { Pending } from '../Pending';
import { useCard } from '../c03/U6Shared';
import { C10TestsTable } from './C10Common';
import { ESTIMATOR_SHORT, ESTIMATOR_TEXT, gridOf, text, type C10Sel } from './selection';

const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });
const ROLE = { size: { en: 'size', es: 'tamaño' }, power: { en: 'power', es: 'potencia' } } as const;
const COLORS = { 'maximum-likelihood': '--color-accent', moments: '--color-magenta' } as const;

/** The rejection rate of the null correlation against the known correlation: size at the null, power elsewhere. */
export function SizePowerView({ sel }: { sel: C10Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const g = gridOf(sel);
  if (!sel || !g) return <Pending />;
  const xs = g.cells.map((c) => c.known_rho);
  const ids = [...new Set(g.cells.flatMap((c) => c.estimators.map((e) => e.estimator)))];
  const rate = (id: string) => g.cells.map((c) => c.estimators.find((e) => e.estimator === id)?.rejection_rate ?? null);
  const focus = g.cells.map((c) => c.estimators.find((e) => e.estimator === sel.estimator));
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Size and power of the correlation test', es: 'Tamaño y potencia de la prueba de correlación' }}
        {...card}
        note={{
          en: `${g.size_power_definition.en} The simulator draws a yearly factor with the known correlation, so the truth is known. Where the known correlation equals the null the rejection rate is the exact size and should sit at the nominal level; elsewhere it is the power. The dotted curves are the 95 % interval of the estimator in focus.`,
          es: `${g.size_power_definition.es} El simulador sortea un factor anual con la correlación conocida, así que la verdad se conoce. Donde la correlación conocida es la de la nula, la tasa de rechazo es el tamaño exacto y debería quedar en el nivel nominal; en las demás es la potencia. Las curvas punteadas son el intervalo del 95 % del estimador en foco.`,
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: xs, label: { en: 'Known correlation', es: 'Correlación conocida' }, format: { percent: true, decimals: 0 } }}
              y={{ label: { en: 'Rejection rate of H0', es: 'Tasa de rechazo de H0' }, format: { percent: true, decimals: 0 }, range: [0, 1] }}
              series={[
                ...ids.map((id) => ({ label: text(ESTIMATOR_TEXT, id), values: rate(id), color: COLORS[id as keyof typeof COLORS] ?? ('--color-accent' as const), width: 2.4 })),
                { label: { en: 'Interval, low', es: 'Intervalo, inferior' }, values: focus.map((e) => e?.rejection_ci_low ?? null), color: '--color-fg-subtle', width: 1, dash: [3, 3] },
                { label: { en: 'Interval, high', es: 'Intervalo, superior' }, values: focus.map((e) => e?.rejection_ci_high ?? null), color: '--color-fg-subtle', width: 1, dash: [3, 3] },
              ]}
              marks={[{ x: g.generator.null_rho, label: { en: `Null: correlation ${formatNumber(g.generator.null_rho, 'en', { percent: true, decimals: 0 })}`, es: `Nula: correlación ${formatNumber(g.generator.null_rho, 'es', { percent: true, decimals: 0 })}` } }]}
              yMarks={[{ y: g.generator.alpha, label: { en: `Nominal size ${formatNumber(g.generator.alpha, 'en', { percent: true, decimals: 0 })}`, es: `Tamaño nominal ${formatNumber(g.generator.alpha, 'es', { percent: true, decimals: 0 })}` }, tone: 'neutral' }]}
            />
          }
        >
          <p className="ct-note">{pick(g.generator.notice, lang)}</p>
          <p className="ct-note" data-generator="null">
            {pick(
              {
                en: `Null correlation ${formatNumber(g.generator.null_rho, 'en', { percent: true, decimals: 0 })}, ${count(g.generator.n_replications, 'en')} replications of ${count(g.generator.series_length_years, 'en')} years each, known PD ${formatNumber(g.generator.known_pd, 'en', { percent: true, decimals: 2 })}.`,
                es: `Correlación nula ${formatNumber(g.generator.null_rho, 'es', { percent: true, decimals: 0 })}, ${count(g.generator.n_replications, 'es')} replicaciones de ${count(g.generator.series_length_years, 'es')} años cada una, PD conocida ${formatNumber(g.generator.known_pd, 'es', { percent: true, decimals: 2 })}.`,
              },
              lang,
            )}
          </p>
          <table className="caos-table ct-wrap-head" data-table="c10-size-power">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Known correlation', es: 'Correlación conocida' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Role', es: 'Papel' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Estimator', es: 'Estimador' }, lang)}</th>
                <th>{pick({ en: 'Rejection rate', es: 'Tasa de rechazo' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Interval of the rate', es: 'Intervalo de la tasa' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Valid replications', es: 'Replicaciones válidas' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {g.cells.flatMap((c) =>
                c.estimators.map((e) => (
                  <tr key={`${c.known_rho}-${e.estimator}`} data-known-rho={c.known_rho} data-role={c.role} data-estimator={e.estimator} className={String(c.known_rho) === sel.cell && e.estimator === sel.estimator ? 'ct-current' : undefined}>
                    <td className="ct-text" data-truth="known">{formatNumber(c.known_rho, lang, { percent: true, decimals: 1 })}</td>
                    <td className="ct-text">{pick(ROLE[c.role], lang)}</td>
                    <td className="ct-text">{pick(text(ESTIMATOR_SHORT, e.estimator), lang)}</td>
                    <td>{formatNumber(e.rejection_rate, lang, { percent: true, decimals: 1 })}</td>
                    <td className="ct-wide-only">{`${formatNumber(e.rejection_ci_low, lang, { percent: true, decimals: 1 })} ${pick({ en: 'to', es: 'a' }, lang)} ${formatNumber(e.rejection_ci_high, lang, { percent: true, decimals: 1 })}`}</td>
                    <td className="ct-wide-only">{`${count(c.n_valid, lang)} / ${count(c.n_replications, lang)}`}</td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
          <C10TestsTable variant={sel.data.variant} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The mean estimate of each estimator against the known correlation, with bias, rmse and the coverage of the interval. */
export function EstimatesView({ sel }: { sel: C10Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const g = gridOf(sel);
  if (!sel || !g) return <Pending />;
  const xs = g.cells.map((c) => c.known_rho);
  const ids = [...new Set(g.cells.flatMap((c) => c.estimators.map((e) => e.estimator)))];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The estimates against the known correlation', es: 'Las estimaciones contra la correlación conocida' }}
        {...card}
        note={{
          en: `The mean of the correlation estimates over the valid replications of ${count(g.generator.series_length_years, 'en')}-year series, against the line of the truth. An estimator on the line is unbiased; the table gives the bias, the root mean squared error and how often its 95 % interval holds the known correlation. A replication whose fit failed is counted, not dropped.`,
          es: `La media de las estimaciones de la correlación en las replicaciones válidas de series de ${count(g.generator.series_length_years, 'es')} años, contra la línea de la verdad. Un estimador sobre la línea no tiene sesgo; la tabla da el sesgo, la raíz del error cuadrático medio y con qué frecuencia su intervalo del 95 % contiene la correlación conocida. Una replicación cuyo ajuste falló se cuenta, no se descarta.`,
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: xs, label: { en: 'Known correlation', es: 'Correlación conocida' }, format: { percent: true, decimals: 0 } }}
              y={{ label: { en: 'Mean estimate', es: 'Estimación media' }, format: { percent: true, decimals: 0 } }}
              series={[
                { label: { en: 'Known correlation', es: 'Correlación conocida' }, values: xs, color: '--color-fg-subtle', width: 1.6, dash: [6, 4] },
                ...ids.map((id) => ({ label: text(ESTIMATOR_TEXT, id), values: g.cells.map((c) => c.estimators.find((e) => e.estimator === id)?.mean_estimate ?? null), color: COLORS[id as keyof typeof COLORS] ?? ('--color-accent' as const), width: 2.4 })),
              ]}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c10-estimates">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Known correlation', es: 'Correlación conocida' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Estimator', es: 'Estimador' }, lang)}</th>
                <th>{pick({ en: 'Mean estimate', es: 'Estimación media' }, lang)}</th>
                <th>{pick({ en: 'Bias', es: 'Sesgo' }, lang)}</th>
                <th>RMSE</th>
                <th>{pick({ en: 'Coverage', es: 'Cobertura' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Failed fits', es: 'Ajustes fallidos' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {g.cells.flatMap((c) =>
                c.estimators.map((e) => (
                  <tr key={`${c.known_rho}-${e.estimator}`} data-known-rho={c.known_rho} data-estimator={e.estimator} className={String(c.known_rho) === sel.cell ? 'ct-current' : undefined}>
                    <td className="ct-text" data-truth="known">{formatNumber(c.known_rho, lang, { percent: true, decimals: 1 })}</td>
                    <td className="ct-text">{pick(text(ESTIMATOR_SHORT, e.estimator), lang)}</td>
                    <td>{formatNumber(e.mean_estimate, lang, { percent: true, decimals: 1 })}</td>
                    <td>{formatNumber(e.bias, lang, { percent: true, decimals: 2 })}</td>
                    {/* in percent, as the bias beside it (R3 c11 m-U) */}
                    <td>{formatNumber(e.rmse, lang, { percent: true, decimals: 2 })}</td>
                    <td>{formatNumber(e.coverage, lang, { percent: true, decimals: 1 })}</td>
                    <td className="ct-wide-only">{count(c.n_failed, lang)}</td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
