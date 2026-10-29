// C03's Sequential view (BS-15, unit D15): the e-process of defaults against the predicted PD, read at every age of the vintages instead of once at
// the 5-year mark. It draws what the cohort document carries in `outputs.sequential`: log E of each vintage by age against the threshold (log 20),
// and a table with the month each vintage first rejects beside the light of the fixed-window binomial test at the mark. A value outside the
// drawn range sits on the edge of the chart; the table keeps it whole. An age that no loan of the vintage has reached is a gap, never a zero.
import { PlotCard, ViewsRow, formatNumber, pick, useShellLang, type ShellColorToken } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable, MaybeNumber } from '../c06/format';
import { Pending } from '../Pending';
import { LIGHT_TEXT } from '../../lib/policy';
import { useCard } from './U6Shared';
import { outputsOf, type C03Sel } from './selection';
import { curveTicks, fyText } from './VintageViews';

const COLORS: ShellColorToken[] = ['--color-accent', '--color-magenta', '--color-warn', '--color-good', '--color-bad'];
/** The drawn range of log E: the threshold (log 20 = 3.0) and a few units beyond it each way. */
const CLIP = 20;
const clip = (v: number | null) => (v === null ? null : Math.max(-CLIP, Math.min(CLIP, v)));

export function SequentialView({ sel }: { sel: C03Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const s = o?.sequential ?? null;
  if (!sel || !o || !s) return <Pending />;
  const threshold = Math.log(s.threshold);
  const month = (m: number | null) => (m === null ? null : m);
  const series = [
    ...s.vintages.map((v, i) => ({
      label: { en: `log E, ${fyText(v.fiscal_year).en}`, es: `log E, ${fyText(v.fiscal_year).es}` },
      values: v.log_e.map(clip),
      color: COLORS[i % COLORS.length],
      width: v.fiscal_year === sel.vintage ? 3 : 1.8,
    })),
    {
      label: { en: `log E, the cohort (${s.headline === 'average' ? 'average' : 'product'} of the vintages)`, es: `log E, la cohorte (${s.headline === 'average' ? 'promedio' : 'producto'} de las cosechas)` },
      values: s[s.headline].log_e.map(clip),
      color: '--color-fg' as ShellColorToken,
      width: 3,
      dash: [10, 3, 2, 3],
    },
    { label: { en: `Threshold, log ${formatNumber(s.threshold, 'en', { decimals: 0 })}`, es: `Umbral, log ${formatNumber(s.threshold, 'es', { decimals: 0 })}` }, values: s.months.map(() => threshold), color: '--color-bad' as ShellColorToken, width: 1.4, dash: [6, 3] },
  ];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'E-process by age: defaults against the predicted PD', es: 'Proceso e por edad: incumplimientos contra la PD predicha' }}
        {...card}
        note={{
          en: `${s.reading.en} The monitor looks for more defaults than predicted (upper direction) and rejects when log E reaches the threshold; the fixed-window tests read a vintage once, at the 5-year mark. Values beyond ${CLIP} on either side are drawn on the edge; the table has them whole.`,
          es: `${s.reading.es} El monitor busca más incumplimientos que los predichos (dirección superior) y rechaza cuando log E llega al umbral; las pruebas de ventana fija leen una cosecha una vez, en la marca de 5 años. Los valores sobre ${CLIP} a cada lado se dibujan en el borde; la tabla los tiene completos.`,
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: s.months, label: { en: 'Months since approval', es: 'Meses desde la aprobación' }, format: { decimals: 0 }, ticks: curveTicks(s.months) }}
              y={{ label: { en: 'log E (dimensionless)', es: 'log E (adimensional)' }, format: { decimals: 0 } }}
              series={series}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="sequential-vintages">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Vintage', es: 'Cosecha' }, lang)}</th>
                <th>{pick({ en: 'Charge-offs / predicted', es: 'Castigos / predichos' }, lang)}</th>
                <th>{pick({ en: 'First month rejected', es: 'Primer mes rechazado' }, lang)}</th>
                <th>{pick({ en: 'Months before the mark', es: 'Meses antes de la marca' }, lang)}</th>
                <th>{pick({ en: 'Largest log E', es: 'Mayor log E' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Binomial light at 60 months', es: 'Luz binomial a 60 meses' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {s.vintages.map((v) => (
                <tr key={v.fiscal_year} data-vintage={v.fiscal_year} data-rejected={v.rejection_month === null ? 'no' : 'yes'} className={v.fiscal_year === sel.vintage ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(fyText(v.fiscal_year), lang)}</td>
                  <td>{`${formatNumber(v.defaults, lang, { decimals: 0 })} / ${formatNumber(v.predicted_defaults, lang, { decimals: 0 })}`}</td>
                  <td>{v.rejection_month === null ? pick({ en: 'never', es: 'nunca' }, lang) : formatNumber(month(v.rejection_month), lang, { decimals: 0 })}</td>
                  <td>{v.months_before_the_mark === null ? '-' : formatNumber(v.months_before_the_mark, lang, { decimals: 0 })}</td>
                  <td>
                    <MaybeNumber value={v.max_log_e} reason={null} format={(x) => formatNumber(x, lang, { decimals: 1 })} />
                  </td>
                  <td className="ct-text">{v.five_year_light === null ? '-' : pick(LIGHT_TEXT[v.five_year_light] ?? { en: v.five_year_light, es: v.five_year_light }, lang)}</td>
                </tr>
              ))}
              <tr data-cohort="average">
                <td className="ct-text">{pick({ en: 'The cohort, by average', es: 'La cohorte, por promedio' }, lang)}</td>
                <td>-</td>
                <td>{s.average.rejection_month === null ? pick({ en: 'never', es: 'nunca' }, lang) : formatNumber(s.average.rejection_month, lang, { decimals: 0 })}</td>
                <td>{s.average.rejection_month === null ? '-' : formatNumber(s.months[s.months.length - 1] - s.average.rejection_month, lang, { decimals: 0 })}</td>
                <td>{formatNumber(s.average.max_log_e, lang, { decimals: 1 })}</td>
                <td className="ct-text">-</td>
              </tr>
              <tr data-cohort="product">
                <td className="ct-text">{pick({ en: 'The cohort, by product', es: 'La cohorte, por producto' }, lang)}</td>
                <td>-</td>
                <td>{s.product.rejection_month === null ? pick({ en: 'never', es: 'nunca' }, lang) : formatNumber(s.product.rejection_month, lang, { decimals: 0 })}</td>
                <td>{s.product.rejection_month === null ? '-' : formatNumber(s.months[s.months.length - 1] - s.product.rejection_month, lang, { decimals: 0 })}</td>
                <td>{formatNumber(s.product.max_log_e, lang, { decimals: 1 })}</td>
                <td className="ct-text">-</td>
              </tr>
            </tbody>
          </table>
          <p className="ct-note">{pick(s.limits, lang)}</p>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
