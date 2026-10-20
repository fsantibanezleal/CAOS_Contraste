// C12's CVA group: the CVA and DVA built up over the time buckets from the discounted exposure, the survival of the
// counterparty and its loss given default; and the CVA of the wrong-way variant against the parameter b of the Hull and
// White (2012) hazard model, with the largest b w stated. The counterparty curve is a proxy (an AAA to A market spread
// derived from the Treasury HQM curve, or a stated synthetic spread), never a counterparty's own curve. The running sum
// of the buckets is the only arithmetic: its last value is the document's CVA.
import { PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable } from '../c06/format';
import { useCard, type Bi } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { NOT_SWAP, SHARE, UnavailableCard, cell, years } from './C12Common';
import { amount, axisOf, outputsOf, runningSum, wwrOf, VARIANT_TEXT, text, type C12Sel } from './selection';

const YEARS_AXIS = { label: { en: 'Time (years)', es: 'Tiempo (años)' } as BiText, format: { decimals: 1 } };

const SOURCE_TEXT: Record<string, Bi> = {
  'hqm-minus-treasury': { en: 'Treasury HQM corporate spot curve minus the Treasury zero curve of the same date', es: 'Curva spot corporativa HQM del Tesoro menos la curva cero del Tesoro de la misma fecha' },
  'synthetic-flat': { en: 'a synthetic flat spread, a convention of the case', es: 'un spread plano sintético, una convención del caso' },
};

/** The CVA and the DVA as the running sum of their terms over the time buckets, and each bucket's term, survival and default probability. */
export function CvaView({ sel }: { sel: C12Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The CVA built up by time bucket', es: 'El CVA acumulado por tramo de tiempo' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SWAP} />;
  const c = o.cva_dva;
  const ends = c.buckets.map((b) => b.t_end);
  const cumCva = runningSum(c.buckets.map((b) => b.cva_term));
  const cumDva = runningSum(c.buckets.map((b) => b.dva_term));
  const axis = axisOf([...cumCva, ...cumDva]);
  const termAxis = axisOf(c.buckets.flatMap((b) => [b.cva_term, b.dva_term]));
  const cva = amount(c.cva.amount);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: `CVA = the sum over the buckets of the default probability of the bucket, times the loss given default of ${formatNumber(c.lgd, 'en', { percent: true, decimals: 0 })}, times the discounted expected exposure at the bucket end (dossier 05, C.2); DVA is the same with the bank's own default probability and the discounted ENE. The counterparty curve is a proxy: ${pick(text(SOURCE_TEXT, c.credit_curve_source), 'en')}; ${c.credit_curve_label}.`,
          es: `CVA = la suma sobre los tramos de la probabilidad de incumplimiento del tramo, por la pérdida dado el incumplimiento de ${formatNumber(c.lgd, 'es', { percent: true, decimals: 0 })}, por la exposición esperada descontada al final del tramo (dossier 05, C.2); el DVA es lo mismo con la probabilidad de incumplimiento propia del banco y la ENE descontada. La curva de la contraparte es un proxy: ${pick(text(SOURCE_TEXT, c.credit_curve_source), 'es')}; proxy de un spread de mercado AAA a A, un piso para calificaciones menores.`,
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: ends, ...YEARS_AXIS }}
              y={{ label: { en: `Accumulated CVA and DVA (${pick(axis.unit, 'en')})`, es: `CVA y DVA acumulados (${pick(axis.unit, 'es')})` }, format: { digits: 4 } }}
              series={[
                { label: { en: 'CVA, accumulated', es: 'CVA acumulado' }, values: cumCva.map((v) => v / axis.div), color: '--color-accent', width: 2.8 },
                { label: { en: 'DVA, accumulated', es: 'DVA acumulado' }, values: cumDva.map((v) => v / axis.div), color: '--color-good', width: 2, dash: [6, 3] },
              ]}
              yMarks={[{ y: c.cva.amount / axis.div, label: { en: `CVA of the document: ${formatNumber(cva.value, 'en', cva.format)} ${pick(cva.unit, 'en')}`, es: `CVA del documento: ${formatNumber(cva.value, 'es', cva.format)} ${pick(cva.unit, 'es')}` }, tone: 'neutral' }]}
            />
          }
        >
          <dl className="ct-defs" data-table="c12-cva">
            <dt>{pick({ en: 'CVA, DVA and BCVA (USD)', es: 'CVA, DVA y BCVA (USD)' }, lang)}</dt>
            <dd data-cva={c.cva.amount}>{`${cell(c.cva.amount, lang)} / ${cell(c.dva.amount, lang)} / ${cell(c.bcva.amount, lang)} (${pick({ en: 'Monte Carlo SE of the CVA', es: 'ES de Monte Carlo del CVA' }, lang)} ${formatNumber(c.cva.mc_se, lang, { digits: 4 })})`}</dd>
            <dt>{pick({ en: 'Counterparty curve', es: 'Curva de la contraparte' }, lang)}</dt>
            <dd data-credit-source={c.credit_curve_source} data-label="proxy">{`${pick({ en: 'proxy', es: 'proxy' }, lang)}: ${pick(text(SOURCE_TEXT, c.credit_curve_source), lang)}`}</dd>
            <dt>{pick({ en: 'Negative spreads set to zero', es: 'Spreads negativos llevados a cero' }, lang)}</dt>
            <dd>{c.spreads_floored_at_zero}</dd>
          </dl>
        </ChartOverTable>
      </PlotCard>
      <PlotCard fill title={{ en: 'The terms of each bucket', es: 'Los términos de cada tramo' }} {...card}>
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: ends, ...YEARS_AXIS }}
              y={{ label: { en: `Term of the bucket (${pick(termAxis.unit, 'en')})`, es: `Término del tramo (${pick(termAxis.unit, 'es')})` }, format: { digits: 4 } }}
              series={[
                { label: { en: 'CVA term', es: 'Término del CVA' }, values: c.buckets.map((b) => b.cva_term / termAxis.div), color: '--color-accent', width: 2.2 },
                { label: { en: 'DVA term', es: 'Término del DVA' }, values: c.buckets.map((b) => b.dva_term / termAxis.div), color: '--color-good', width: 1.8, dash: [6, 3] },
              ]}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c12-cva-buckets">
            <thead>
              <tr>
                <th>{pick({ en: 'Bucket end (years)', es: 'Fin del tramo (años)' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Spread', es: 'Spread' }, lang)}</th>
                <th>{pick({ en: 'Survival', es: 'Supervivencia' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Default probability', es: 'Prob. de incumplimiento' }, lang)}</th>
                <th>{pick({ en: 'CVA term (USD)', es: 'Término CVA (USD)' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {c.buckets.map((b) => (
                <tr key={b.t_end} data-bucket={b.t_end}>
                  <td>{years(b.t_end, lang)}</td>
                  <td className="ct-wide-only">{SHARE(b.spread, lang)}</td>
                  <td>{formatNumber(b.survival, lang, { percent: true, decimals: 3 })}</td>
                  <td className="ct-wide-only">{formatNumber(b.pd_counterparty, lang, { percent: true, decimals: 3 })}</td>
                  <td>{formatNumber(b.cva_term, lang, { digits: 4 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The CVA against the wrong-way parameter b: b = 0 is the independent CVA on the same paths, a positive b raises it. */
export function WwrView({ sel }: { sel: C12Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The CVA against the wrong-way parameter b', es: 'El CVA contra el parámetro b de correlación adversa' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SWAP} />;
  const found = wwrOf(sel);
  if (!found) {
    return <UnavailableCard sel={sel} title={title} reason={sel.peers ? { en: 'Not available: this variant has no wrong-way block, and the case holds none of the wrong-way variant.', es: 'No disponible: esta variante no tiene bloque de correlación adversa, y el caso no tiene la variante de correlación adversa.' } : { en: 'Not available: this variant has no wrong-way block; the wrong-way variant is loading.', es: 'No disponible: esta variante no tiene bloque de correlación adversa; la variante de correlación adversa se está cargando.' }} />;
  }
  const w = found.block;
  const own = found.owner === o;
  const ore = found.owner.ore_reconciliation;
  const axis = axisOf(w.sweep.map((p) => p.cva.amount));
  const picked = w.sweep[Math.min(sel.b, w.sweep.length - 1)];
  const independent = w.sweep.find((p) => p.independent);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: `The Hull and White (2012) model: the hazard rate of the counterparty is h(t) = exp(a(t) + b w(t)) with w the simulated portfolio value in USD million; a(t) is calibrated path by path to today's survival curve, so b = 0 is the independent CVA on the same paths and a positive b is wrong-way risk. ${own ? '' : 'Drawn from the wrong-way variant of the case. '}The largest b w of the sweep is ${formatNumber(w.largest_b_w, 'en', { digits: 4 })}: the largest |b| times the largest simulated value of ${formatNumber(w.w_max_usd_million, 'en', { digits: 4 })} USD million.`,
          es: `El modelo de Hull y White (2012): la tasa de riesgo de la contraparte es h(t) = exp(a(t) + b w(t)) con w el valor simulado de la cartera en millones de USD; a(t) se calibra trayectoria por trayectoria a la curva de supervivencia de hoy, así que b = 0 es el CVA independiente sobre las mismas trayectorias y un b positivo es riesgo de correlación adversa. ${own ? '' : 'Dibujado desde la variante de correlación adversa del caso. '}El mayor b w del barrido es ${formatNumber(w.largest_b_w, 'es', { digits: 4 })}: el mayor |b| por el mayor valor simulado de ${formatNumber(w.w_max_usd_million, 'es', { digits: 4 })} millones de USD.`,
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: w.sweep.map((p) => p.b), label: { en: 'b (per USD million of portfolio value)', es: 'b (por millón de USD de valor de la cartera)' }, format: { decimals: 1 } }}
              y={{ label: { en: `CVA (${pick(axis.unit, 'en')})`, es: `CVA (${pick(axis.unit, 'es')})` }, format: { digits: 4 } }}
              series={[
                { label: { en: 'CVA of the sweep', es: 'CVA del barrido' }, values: w.sweep.map((p) => p.cva.amount / axis.div), color: '--color-accent', width: 2.6 },
                { label: { en: 'Points of the sweep', es: 'Puntos del barrido' }, values: w.sweep.map((p) => p.cva.amount / axis.div), color: '--color-accent', mode: 'points', size: 8 },
              ]}
              marks={picked ? [{ x: picked.b, label: { en: `b = ${formatNumber(picked.b, 'en', { digits: 4 })}`, es: `b = ${formatNumber(picked.b, 'es', { digits: 4 })}` } }] : []}
              yMarks={[{ y: w.independent_cva.amount / axis.div, label: { en: 'Independent CVA (b = 0)', es: 'CVA independiente (b = 0)' }, tone: 'neutral' }]}
            />
          }
        >
          <p className="ct-note" data-block="ore-limit" data-ore-status={ore.status}>
            {ore.status === 'not-applicable' ? `${pick({ en: 'This variant has no ORE reconciliation.', es: 'Esta variante no tiene conciliación con ORE.' }, lang)} ` : ''}
            {pick(w.ore_limit, lang)}
          </p>
          <table className="caos-table ct-wrap-head" data-table="c12-wwr">
            <thead>
              <tr>
                <th>{pick({ en: 'b (per USD million)', es: 'b (por millón de USD)' }, lang)}</th>
                <th>{pick({ en: 'CVA (USD)', es: 'CVA (USD)' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Monte Carlo SE', es: 'ES de Monte Carlo' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Reading', es: 'Lectura' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Calibration error of a(t)', es: 'Error de calibración de a(t)' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {w.sweep.map((p, i) => (
                <tr key={p.b} data-b={p.b} data-independent={p.independent ? 'true' : undefined} className={i === Math.min(sel.b, w.sweep.length - 1) ? 'ct-current' : undefined}>
                  <td>{formatNumber(p.b, lang, { digits: 4 })}</td>
                  <td>{cell(p.cva.amount, lang)}</td>
                  <td className="ct-wide-only">{formatNumber(p.cva.mc_se, lang, { digits: 4 })}</td>
                  <td className="ct-text">{p.independent ? pick({ en: 'independent', es: 'independiente' }, lang) : p.b > 0 ? pick({ en: 'wrong-way', es: 'correlación adversa' }, lang) : pick({ en: 'right-way', es: 'correlación favorable' }, lang)}</td>
                  <td className="ct-wide-only">{formatNumber(p.a_calibration_max_error, lang, { digits: 2 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="ct-note">
            {pick({ en: `Variant: ${pick(text(VARIANT_TEXT, found.owner.variant), 'en')}. Independent CVA ${independent ? cell(independent.cva.amount, 'en') : formatNumber(null, 'en')} USD.`, es: `Variante: ${pick(text(VARIANT_TEXT, found.owner.variant), 'es')}. CVA independiente ${independent ? cell(independent.cva.amount, 'es') : formatNumber(null, 'es')} USD.` }, lang)}
          </p>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
