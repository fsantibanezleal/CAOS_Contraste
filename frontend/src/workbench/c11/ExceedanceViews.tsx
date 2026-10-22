// C11's Exceedances group: the timeline of the VaR and ES forecasts against the realised loss with a point on each day
// the loss exceeded the VaR, and the rolling 250-day exceedance count against the MAR32.9 zones. Each draws what the
// c11-outputs document carries (every VaR and ES a positive loss); a series the contract allows to be null is a gap or
// "not available" with its reason, never a zero.
import { PlotCard, ViewsRow, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { UPlotChart, type ChartSeries } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable } from '../c06/format';
import { Pending } from '../Pending';
import { noteText } from '../c08/notes';
import { useCard } from '../c03/U6Shared';
import { ConventionLine, zoneText } from './MarketCommon';
import { fitOf, levelOf, lossPct, modelLabel, outputsOf, rollingCounts, seconds, spanLine, zoneStart, type C11Sel } from './selection';

const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });

/** The VaR and ES of the model against the realised loss, with the exceedance days marked. */
export function TimelineView({ sel }: { sel: C11Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const lv = levelOf(o, sel.model, sel.alpha);
  const name = modelLabel(sel, sel.model);
  if (!lv) {
    return (
      <ViewsRow>
        <PlotCard fill title={{ en: 'VaR, ES and the realised loss', es: 'VaR, ES y la pérdida realizada' }} {...card}>
          <p className="ct-note" data-state="unavailable">{pick({ en: 'This window carries no forecast for this model and level.', es: 'Esta ventana no trae pronóstico para este modelo y nivel.' }, lang)}</p>
        </PlotCard>
      </ViewsRow>
    );
  }
  const grid = o.grid;
  const loss = grid.realised_loss.status === 'included' ? grid.realised_loss.loss : null;
  const hit = new Set(lv.exceedance_days);
  const series: ChartSeries[] = [];
  if (loss) series.push({ label: { en: 'Realised loss', es: 'Pérdida realizada' }, values: loss, color: '--color-fg-faint', width: 1 });
  series.push({ label: { en: 'VaR', es: 'VaR' }, values: lv.var, color: '--color-accent', width: 2 });
  if (lv.es_status !== 'not-forecast') series.push({ label: { en: 'ES', es: 'ES' }, values: lv.es, color: '--color-magenta', width: 2 });
  series.push({
    label: loss ? { en: 'Exceedance', es: 'Excedencia' } : { en: 'Exceedance', es: 'Excedencia' },
    values: grid.dates.map((_, i) => (hit.has(i) ? (loss ? loss[i] : lv.var[i]) : null)),
    color: '--color-bad',
    mode: 'points',
    size: 7,
  });
  const alphaPct = formatNumber(lv.alpha, lang, { percent: true, decimals: lv.alpha === 0.025 ? 1 : 0 });
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `VaR and ES of ${name.en} at the ${formatNumber(lv.alpha, 'en', { percent: true, decimals: lv.alpha === 0.025 ? 1 : 0 })} tail`, es: `VaR y ES de ${name.es} en la cola de ${formatNumber(lv.alpha, 'es', { percent: true, decimals: lv.alpha === 0.025 ? 1 : 0 })}` }}
        {...card}
        note={{
          en: `${spanLine(o).en} One-step forecasts, each from data strictly before its day. A red point is a day the loss exceeded the VaR.`,
          es: `${spanLine(o).es} Pronósticos a un paso, cada uno con datos estrictamente anteriores a su día. Un punto rojo es un día en que la pérdida superó al VaR.`,
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: grid.dates.map(seconds), time: true, label: { en: 'Forecast day', es: 'Día pronosticado' } }}
              y={{ label: { en: 'Loss, share of the portfolio value', es: 'Pérdida, parte del valor de la cartera' }, format: { percent: true, decimals: 2 } }}
              series={series}
            />
          }
        >
          <div data-level={lv.alpha}>
            <ConventionLine />
            {loss === null ? (
              <p className="ct-note" data-state="unavailable">
                {`${formatNumber(null, lang)} (${noteText(grid.realised_loss.reason, lang)}) ${pick({ en: 'The exceedances are marked on the VaR.', es: 'Las excedencias se marcan sobre el VaR.' }, lang)}`}
              </p>
            ) : null}
            {lv.es_status === 'not-forecast' ? (
              <p className="ct-note" data-state="unavailable">
                {pick({ en: 'This model forecasts no ES: only the VaR is drawn, and its FZ0 score is not available.', es: 'Este modelo no pronostica la ES: solo se dibuja el VaR y su puntaje FZ0 no está disponible.' }, lang)}
              </p>
            ) : null}
            {lv.es_status === 'undefined-on-days' ? (
              <p className="ct-note">
                {pick({ en: `The ES is undefined on ${count(lv.es_undefined_days.length, 'en')} days (a gap in its line, never a zero).`, es: `La ES no está definida en ${count(lv.es_undefined_days.length, 'es')} días (un hueco en su línea, nunca un cero).` }, lang)}
              </p>
            ) : null}
            <p className="ct-note">
              {pick(
                {
                  en: `${count(lv.n_exceedances, 'en')} exceedances in ${count(lv.n_scored, 'en')} days against ${formatNumber(lv.expected_exceedances, 'en', { decimals: 2 })} expected at ${alphaPct}. The public series skipped ${count(o.data_status.missing_days.count, 'en')} days (not filled).`,
                  es: `${count(lv.n_exceedances, 'es')} excedencias en ${count(lv.n_scored, 'es')} días frente a ${formatNumber(lv.expected_exceedances, 'es', { decimals: 2 })} esperadas al ${alphaPct}. Las series públicas omitieron ${count(o.data_status.missing_days.count, 'es')} días (sin rellenar).`,
                },
                lang,
              )}
            </p>
            <table className="caos-table ct-wrap-head" data-table="exceedance-days">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Exceedance day', es: 'Día de excedencia' }, lang)}</th>
                  <th>VaR</th>
                  <th>{pick({ en: 'Realised loss', es: 'Pérdida realizada' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {lv.exceedance_days.length === 0 ? (
                  <tr>
                    <td className="ct-text" colSpan={3}>{pick({ en: 'No day exceeded the VaR.', es: 'Ningún día superó al VaR.' }, lang)}</td>
                  </tr>
                ) : (
                  lv.exceedance_days.map((d) => (
                    <tr key={d} data-exceedance-day={grid.dates[d]}>
                      <td className="ct-text">{grid.dates[d]}</td>
                      <td>{lossPct(lv.var[d], lang)}</td>
                      <td data-na={loss ? undefined : 'true'}>{loss ? lossPct(loss[d], lang) : formatNumber(null, lang)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The rolling 250-day exceedance count of the model against the MAR32.9 zones, and the table of the zones. */
export function ZonesView({ sel }: { sel: C11Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const fit = fitOf(sel);
  const lv = levelOf(o, sel.model, sel.alpha);
  const tl = lv?.traffic_light ?? null;
  const name = modelLabel(sel, sel.model);
  const title = { en: `Basel traffic light of ${name.en}`, es: `Semáforo de Basilea de ${name.es}` };
  if (!lv || tl === null) {
    return (
      <ViewsRow>
        <PlotCard fill title={title} {...card}>
          <ConventionLine />
          <p className="ct-note" data-state="unavailable">
            {pick({ en: 'Not available at this level: the Basel traffic light (MAR32.9) is defined at the 99 percent level over 250 days, the 1% tail.', es: 'No disponible en este nivel: el semáforo de Basilea (MAR32.9) se define al nivel de 99 por ciento sobre 250 días, la cola de 1%.' }, lang)}
          </p>
        </PlotCard>
      </ViewsRow>
    );
  }
  const rolling = tl.final_zone === 'not_evaluated' ? [] : rollingCounts(lv.exceedance_days, o.grid.dates.length, tl.window_days);
  const amber = zoneStart(fit, 'amber');
  const red = zoneStart(fit, 'red');
  const marks = [
    ...(amber !== null ? [{ y: amber, label: { en: `Amber from ${amber}`, es: `Ámbar desde ${amber}` }, tone: 'warn' as const }] : []),
    ...(red !== null ? [{ y: red, label: { en: `Red from ${red}`, es: `Rojo desde ${red}` }, tone: 'bad' as const }] : []),
  ];
  const table = fit?.traffic_light;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: `${spanLine(o).en} The count of exceedances in the last 250 forecast days, read against MAR32.9 Table 1 at the 99 percent level.`,
          es: `${spanLine(o).es} La cuenta de excedencias en los últimos 250 días pronosticados, leída contra la Tabla 1 de MAR32.9 al nivel de 99 por ciento.`,
        }}
      >
        <ChartOverTable
          chart={
            rolling.length > 0 ? (
              <UPlotChart
                height="fill"
                x={{ values: o.grid.dates.slice(tl.window_days - 1).map((_, i) => tl.window_days + i), label: { en: 'Forecast day number at the end of the window', es: 'Número de día pronosticado al final de la ventana' }, format: { decimals: 0 } }}
                y={{ label: { en: 'Exceedances in 250 days', es: 'Excedencias en 250 días' }, format: { decimals: 0 } }}
                series={[{ label: { en: 'Rolling exceedances', es: 'Excedencias móviles' }, values: rolling, color: '--color-accent', width: 2 }]}
                yMarks={marks}
              />
            ) : (
              <p className="ct-note" data-state="unavailable">
                {`${formatNumber(null, lang)} (${noteText(tl.reason, lang)})`}
              </p>
            )
          }
        >
          <div data-level={lv.alpha}>
            <ConventionLine />
            <dl className="ct-defs" data-table="traffic-light" data-final-zone={tl.final_zone}>
              <dt>{pick({ en: 'Zone at the last day', es: 'Zona al último día' }, lang)}</dt>
              <dd>{pick(zoneText(tl.final_zone), lang)}</dd>
              <dt>{pick({ en: 'Complete windows', es: 'Ventanas completas' }, lang)}</dt>
              <dd>{count(tl.n_windows, lang)}</dd>
              <dt>{pick({ en: 'Most exceedances in a window', es: 'Máximo de excedencias en una ventana' }, lang)}</dt>
              <dd data-na={tl.max_rolling_exceedances === null ? 'true' : undefined}>{tl.max_rolling_exceedances === null ? formatNumber(null, lang) : count(tl.max_rolling_exceedances, lang)}</dd>
              <dt>{pick({ en: 'Exceedances in the last window', es: 'Excedencias en la última ventana' }, lang)}</dt>
              <dd data-na={tl.final_rolling_exceedances === null ? 'true' : undefined}>{tl.final_rolling_exceedances === null ? formatNumber(null, lang) : count(tl.final_rolling_exceedances, lang)}</dd>
              <dt>{pick({ en: 'Days in green, amber, red', es: 'Días en verde, ámbar, rojo' }, lang)}</dt>
              <dd data-na={tl.days_green === null ? 'true' : undefined}>
                {tl.days_green === null ? formatNumber(null, lang) : `${count(tl.days_green, lang)}, ${count(tl.days_amber ?? 0, lang)}, ${count(tl.days_red ?? 0, lang)}`}
              </dd>
              {tl.reason ? (
                <>
                  <dt>{pick({ en: 'Why not evaluated', es: 'Por qué no se evalúa' }, lang)}</dt>
                  <dd>{noteText(tl.reason, lang)}</dd>
                </>
              ) : null}
            </dl>
            {table ? (
              <table className="caos-table ct-wrap-head" data-table="mar32-9">
                <caption className="ct-note">{`${table.reference}`}</caption>
                <thead>
                  <tr>
                    <th>{pick({ en: 'Exceptions in 250 days', es: 'Excepciones en 250 días' }, lang)}</th>
                    <th className="ct-text">{pick({ en: 'Zone', es: 'Zona' }, lang)}</th>
                    <th>{pick({ en: 'FRTB multiplier', es: 'Multiplicador FRTB' }, lang)}</th>
                    <th>{pick({ en: 'US factor', es: 'Factor de EE.UU.' }, lang)}</th>
                    <th>{pick({ en: 'Cumulative probability', es: 'Probabilidad acumulada' }, lang)}</th>
                  </tr>
                </thead>
                <tbody>
                  {table.rows.map((r) => (
                    <tr key={r.exceptions} data-exceptions={r.exceptions} data-zone={r.zone} className={r.exceptions === Math.min(tl.final_rolling_exceedances ?? -1, 10) ? 'ct-current' : undefined}>
                      <td>{r.exceptions === 10 ? `${count(10, lang)}+` : count(r.exceptions, lang)}</td>
                      <td className={`ct-text ct-light ct-light-${r.zone}`}>
                        <span className="ct-light-word">{pick(zoneText(r.zone), lang)}</span>
                      </td>
                      <td>{formatNumber(r.frtb_multiplier, lang, { decimals: 2 })}</td>
                      <td>{formatNumber(r.us_multiplier, lang, { decimals: 2 })}</td>
                      <td>{`${formatNumber(r.cumulative_probability_pct, lang, { decimals: 2 })} %`}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : null}
          </div>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
