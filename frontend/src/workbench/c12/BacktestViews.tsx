// C12's backtest group: would the simulated exposure distributions have held against the curves that were later realised.
// Each initialisation date is calibrated only on data up to that date; the realised value of the synthetic book (or of the
// short-rate proxy) is mapped to its PIT in the simulated sample by the (i + 1) / (N + 2) rule; uniformity of the PITs is
// tested with the Anderson-Darling W^2 against critical values that come from simulating the whole backtest under the
// model itself, the independent-sample table values being reported beside them. The PFE exceedance counts are a secondary
// row (BCBS 185 paragraph 27). The only arithmetic is the binning of the document's PITs into ten equal classes.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { useMedia } from '../../lib/useMedia';
import { ChartOverTable } from '../c06/format';
import { useCard, type Bi } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { NOT_SWAP, NumbersCard, TallTables, UnavailableCard, digits, DEFS_STYLE, Nw } from './C12Common';
import { HORIZON_LONG, HORIZON_SHORT, HORIZONS, SUBJECT_LONG, histogram, horizonOf, horizonsOf, outputsOf, text, type C12Sel } from './selection';

const WINDOW_TEXT: Record<string, Bi> = {
  'before-2008': { en: 'Before 2008', es: 'Antes de 2008' },
  '2008-2019': { en: '2008 to 2019', es: '2008 a 2019' },
  'from-2020': { en: 'From 2020', es: 'Desde 2020' },
};

/** The PITs of the horizon in focus in ten equal classes: uniform when the model holds. */
export function PitView({ sel }: { sel: C12Sel | null }) {
  const lang = useShellLang();
  // ten classes at a phone width cannot carry "0.0 to 0.1": the lower edge of each class names it (U16-R2 b06 m10)
  const narrow = useMedia('(max-width: 600px)');
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The PIT histogram', es: 'El histograma de los PIT' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SWAP} />;
  const h = horizonOf(o, sel.subject, sel.horizon);
  if (!h) return <UnavailableCard sel={sel} title={title} reason={{ en: 'Not available: the document holds no back-test of this horizon.', es: 'No disponible: el documento no trae el backtest de este horizonte.' }} />;
  const bins = 10;
  const counts = histogram(h.pits, bins);
  const expected = h.n / bins;
  const bt = o.backtest;
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: `Back-tested: ${pick(text(SUBJECT_LONG, sel.subject), 'en')}, at ${pick(text(HORIZON_LONG, sel.horizon), 'en')}. Each realised value is mapped to its PIT, the share of the simulated sample below it, by the rule ${bt.pit_rule}; if the model holds, the PITs of the back-test dates are uniform and each class holds about ${formatNumber(expected, 'en', { digits: 4 })} of the ${h.n} dates. Each date was calibrated only on data up to that date.`,
          es: `Evaluado: ${pick(text(SUBJECT_LONG, sel.subject), 'es')}, a ${pick(text(HORIZON_LONG, sel.horizon), 'es')}. Cada valor realizado se mapea a su PIT, la parte de la muestra simulada bajo él, con la regla ${bt.pit_rule}; si el modelo se sostiene, los PIT de las fechas del backtest son uniformes y cada clase tiene cerca de ${formatNumber(expected, 'es', { digits: 4 })} de las ${h.n} fechas. Cada fecha se calibró solo con datos hasta esa fecha.`,
        }}
      >
                    <BarChart
              title={narrow ? { en: 'Back-test dates by PIT class (lower edge)', es: 'Fechas del backtest por clase de PIT (borde inferior)' } : { en: 'Number of back-test dates by PIT class', es: 'Número de fechas del backtest por clase de PIT' }}
              height="fill"
              orientation="vertical"
              data={counts.map((n, i) => ({ id: `bin${i}`, label: narrow ? { en: formatNumber(i / bins, 'en', { decimals: 1 }), es: formatNumber(i / bins, 'es', { decimals: 1 }) } : { en: `${formatNumber(i / bins, 'en', { decimals: 1 })} to ${formatNumber((i + 1) / bins, 'en', { decimals: 1 })}`, es: `${formatNumber(i / bins, 'es', { decimals: 1 })} a ${formatNumber((i + 1) / bins, 'es', { decimals: 1 })}` }, value: n, tone: 'accent' as const }))}
              axis={{ label: { en: 'Back-test dates', es: 'Fechas del backtest' }, format: { decimals: 0 }, range: [0, Math.max(4, ...counts)] }}
            />
      </PlotCard>
      <NumbersCard card={card}>
          <table className="caos-table ct-wrap-head" data-table="c12-pit-bins">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'PIT class', es: 'Clase de PIT' }, lang)}</th>
                <th>{pick({ en: 'Dates', es: 'Fechas' }, lang)}</th>
                <th>{pick({ en: 'Expected if uniform', es: 'Esperadas si es uniforme' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {counts.map((n, i) => (
                <tr key={i} data-bin={i}>
                  <td className="ct-text">{`${formatNumber(i / bins, lang, { decimals: 1 })} ${pick({ en: 'to', es: 'a' }, lang)} ${formatNumber((i + 1) / bins, lang, { decimals: 1 })}`}</td>
                  <td>{n}</td>
                  <td>{formatNumber(expected, lang, { digits: 4 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <dl className="ct-defs" style={DEFS_STYLE} data-table="c12-pit">
            <dt>{pick({ en: 'Statistic W²', es: 'Estadístico W²' }, lang)}</dt>
            <dd data-w2={h.w2}><Nw>{digits(h.w2, lang)}</Nw></dd>
            <dt>{pick({ en: 'Critical values from the simulated back-test, 5% and 1%', es: 'Valores críticos del backtest simulado, 5 % y 1 %' }, lang)}</dt>
            <dd><Nw>{`${digits(h.critical_simulated.p05, lang)} / ${digits(h.critical_simulated.p01, lang)}`}</Nw></dd>
            <dt>{pick({ en: 'Independent-sample table, 5% and 1% (reported beside, not in its place)', es: 'Tabla de muestras independientes, 5 % y 1 % (informada al lado, no en su lugar)' }, lang)}</dt>
            <dd><Nw>{`${digits(h.critical_iid.p05, lang)} / ${digits(h.critical_iid.p01, lang)}`}</Nw></dd>
            <dt>{pick({ en: 'Dates and effective sample size', es: 'Fechas y tamaño de muestra efectivo' }, lang)}</dt>
            <dd>
              <Nw>{`${h.n} / ${formatNumber(h.effective_sample_size, lang, { digits: 4 })}`}</Nw>
              {` (${pick({ en: 'overlapping horizons share information', es: 'los horizontes que se traslapan comparten información' }, lang)})`}
            </dd>
            <dt>{pick({ en: 'Decision at 5%', es: 'Decisión al 5 %' }, lang)}</dt>
            <dd data-reject={String(h.reject_at_5pct)}>{h.reject_at_5pct ? pick({ en: 'the distribution is rejected', es: 'la distribución se rechaza' }, lang) : pick({ en: 'the distribution is not rejected', es: 'la distribución no se rechaza' }, lang)}</dd>
          </dl>
      </NumbersCard>
    </ViewsRow>
  );
}

/** The statistic W² of every horizon of the subject in focus against its critical value, the exceedance counts beside, and the sub-windows. */
export function ExceedanceView({ sel }: { sel: C12Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'Exceedances and the test', es: 'Excedencias y la prueba' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SWAP} />;
  const rows = horizonsOf(o, sel.subject);
  const bt = o.backtest;
  const quantiles = rows[0]?.exceedances.map((e) => e.quantile) ?? [];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: `Back-tested: ${pick(text(SUBJECT_LONG, sel.subject), 'en')}, from ${bt.window_start} to ${bt.window_end}, with ${bt.paths_per_date} simulated paths per date. A bar in red is a horizon the Anderson-Darling test rejects at 5 percent against the simulated critical value. The horizons include the margin periods of 10 and 20 business days and the year, and several percentiles are counted, never one (BCBS 185 paragraphs 18, 19 and 31); the exceedance counts assume independence and are a secondary row.`,
          es: `Evaluado: ${pick(text(SUBJECT_LONG, sel.subject), 'es')}, de ${bt.window_start} a ${bt.window_end}, con ${bt.paths_per_date} trayectorias simuladas por fecha. Una barra roja es un horizonte que la prueba de Anderson-Darling rechaza al 5 por ciento contra el valor crítico simulado. Los horizontes incluyen los periodos de margen de 10 y 20 días hábiles y el año, y se cuentan varios percentiles, nunca uno (BCBS 185, párrafos 18, 19 y 31); los conteos de excedencias suponen independencia y son una fila secundaria.`,
        }}
      >
        <TallTables>
        <ChartOverTable
          chartMin="clamp(11rem, 20rem - 15vw, 17rem)"
          chart={
            <BarChart
              title={{ en: 'W² by horizon', es: 'W² por horizonte' }}
              height="fill"
              orientation="horizontal"
              data={HORIZONS.flatMap((id) => {
                const h = rows.find((r) => r.horizon === id);
                return h ? [{ id, label: text(HORIZON_LONG, id), value: h.w2, tone: h.reject_at_5pct ? ('bad' as const) : ('accent' as const), highlight: id === sel.horizon, hint: { en: `5% critical value ${formatNumber(h.critical_simulated.p05, 'en', { digits: 4 })}`, es: `Valor crítico al 5 % ${formatNumber(h.critical_simulated.p05, 'es', { digits: 4 })}` } }] : [];
              })}
              axis={{ label: { en: 'Anderson-Darling W²', es: 'W² de Anderson-Darling' }, format: { digits: 4 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c12-backtest">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Horizon', es: 'Horizonte' }, lang)}</th>
                <th>{pick({ en: 'Dates', es: 'Fechas' }, lang)}</th>
                <th>{pick({ en: 'W²', es: 'W²' }, lang)}</th>
                <th>{pick({ en: '5% value', es: 'Valor al 5 %' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: '1% value', es: 'Valor al 1 %' }, lang)}</th>
                {quantiles.map((q) => (
                  <th key={q} className="ct-wide-only">{pick({ en: `Above the ${formatNumber(q, 'en', { percent: true, decimals: 0 })} PFE (count / expected)`, es: `Sobre el PFE ${formatNumber(q, 'es', { percent: true, decimals: 0 })} (cuenta / esperadas)` }, lang)}</th>
                ))}
                <th className="ct-text">{pick({ en: 'Decision', es: 'Decisión' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((h) => (
                <tr key={h.horizon} data-horizon={h.horizon} data-reject={String(h.reject_at_5pct)} className={h.horizon === sel.horizon ? 'ct-current' : undefined}>
                  <td className="ct-text" title={pick(text(HORIZON_LONG, h.horizon), lang)}>{pick(text(HORIZON_SHORT, h.horizon), lang)}</td>
                  <td>{h.n}</td>
                  <td>{digits(h.w2, lang)}</td>
                  <td>{digits(h.critical_simulated.p05, lang)}</td>
                  <td className="ct-wide-only">{digits(h.critical_simulated.p01, lang)}</td>
                  {h.exceedances.map((e) => (
                    <td key={e.quantile} className="ct-wide-only">{`${e.count} / ${formatNumber(e.expected, lang, { digits: 4 })}`}</td>
                  ))}
                  <td className="ct-text" style={{ whiteSpace: 'nowrap' }}>{h.reject_at_5pct ? pick({ en: 'rejected', es: 'rechazado' }, lang) : pick({ en: 'not rejected', es: 'no rechazado' }, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {sel.subject === 'book' ? (
            <table className="caos-table ct-wrap-head" data-table="c12-subwindows">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Sub-window', es: 'Subventana' }, lang)}</th>
                  {HORIZONS.map((id) => (
                    <th key={id} className="ct-wide-only" title={pick(text(HORIZON_LONG, id), lang)}>{`W² ${pick(text(HORIZON_SHORT, id), lang)}`}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {bt.sub_windows.map((w) => (
                  <tr key={w.window} data-window={w.window}>
                    <td className="ct-text">{`${pick(text(WINDOW_TEXT, w.window), lang)} (${w.start} ${pick({ en: 'to', es: 'a' }, lang)} ${w.end})`}</td>
                    {HORIZONS.map((id) => {
                      const r = w.results.find((x) => x.horizon === id);
                      return (
                        <td key={id} className="ct-wide-only" data-na={r ? undefined : 'true'}>
                          {r ? `${digits(r.w2, lang)} (${r.n})` : formatNumber(null, lang)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="ct-note" data-block="risk-factor">{pick({ en: `The risk factor is the zero rate of ${formatNumber(bt.risk_factor.proxy_tenor_years, 'en', { digits: 4 })} years, the proxy of the short rate; the exposure operator is not applied to it (BCBS 185 paragraph 20).`, es: `El factor de riesgo es la tasa cero de ${formatNumber(bt.risk_factor.proxy_tenor_years, 'es', { digits: 4 })} años, el proxy de la tasa corta; el operador de exposición no se le aplica (BCBS 185, párrafo 20).` }, lang)}</p>
          )}
          <p className="ct-note">{pick({ en: 'The sub-windows before 2008, from 2008 to 2019 and from 2020 are reported apart for the book, so a failure in one regime is not averaged away.', es: 'Las subventanas antes de 2008, de 2008 a 2019 y desde 2020 se informan aparte para la cartera, de modo que una falla en un régimen no se diluya en el promedio.' }, lang)}</p>
        </ChartOverTable>
        </TallTables>
      </PlotCard>
    </ViewsRow>
  );
}
