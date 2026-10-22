// C03's Vintages group: the cumulative PD curves of each approval vintage (predicted against observed, the unobserved
// months a gap with the reason), the five-year mark of each vintage read only at its mark, and the stability of the
// vintages. Each draws what the c03-outputs document carries; a field the contract allows to be null is "not available"
// with its reason, never a zero.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type ShellColorToken } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable, MaybeNumber, money, unionX } from '../c06/format';
import { Pending } from '../Pending';
import { p2, useCard, type Bi } from './U6Shared';
import { outputsOf, type C03Sel } from './selection';

const COLORS: ShellColorToken[] = ['--color-accent', '--color-magenta', '--color-warn', '--color-good', '--color-bad'];

/** A fiscal year as a label: "FY2018" in English, "AF2018" in Spanish (año fiscal). */
export const fyText = (fy: number): Bi => ({ en: `FY${fy}`, es: `AF${fy}` });

const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });

/** The cumulative PD of every vintage by month since approval: the model's prediction against what was observed. */
export function CurvesView({ sel }: { sel: C03Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const grid = unionX(...o.vintage_curves.map((c) => c.months));
  const at = (months: number[], values: Array<number | null>) => grid.map((g) => (months.includes(g) ? values[months.indexOf(g)] : null));
  const series = o.vintage_curves.flatMap((c, i) => {
    const color = COLORS[i % COLORS.length];
    const width = c.fiscal_year === sel.vintage ? 3 : 1.6;
    return [
      { label: { en: `Predicted, ${fyText(c.fiscal_year).en}`, es: `Predicha, ${fyText(c.fiscal_year).es}` }, values: at(c.months, c.predicted_cumulative_pd), color, width, dash: [6, 3] },
      { label: { en: `Observed, ${fyText(c.fiscal_year).en}`, es: `Observada, ${fyText(c.fiscal_year).es}` }, values: at(c.months, c.observed_cumulative_pd), color, width: width + 0.8 },
    ];
  });
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Cumulative PD by vintage: predicted and observed', es: 'PD acumulada por cosecha: predicha y observada' }}
        {...card}
        note={{
          en: 'One pair of curves per approval fiscal year. A month the vintage has not reached by the cut-off of the files is a gap in the observed curve, with the reason in the table; it is never drawn as a zero. Loans still active are right-censored and exempt from the target.',
          es: 'Un par de curvas por año fiscal de aprobación. Un mes que la cosecha no ha alcanzado al corte de los archivos es un hueco en la curva observada, con la razón en la tabla; nunca se dibuja como cero. Los créditos vigentes son censurados por la derecha y quedan exentos del objetivo.',
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: grid, label: { en: 'Months since approval', es: 'Meses desde la aprobación' }, format: { decimals: 0 } }}
              y={{ label: { en: 'Cumulative PD', es: 'PD acumulada' }, format: { percent: true, digits: 2 } }}
              series={series}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="vintage-curves">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Vintage', es: 'Cosecha' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Loans', es: 'Créditos' }, lang)}</th>
                <th>{pick({ en: 'Observed to month', es: 'Observada hasta el mes' }, lang)}</th>
                <th>{pick({ en: 'Predicted at the last month', es: 'Predicha al último mes' }, lang)}</th>
                <th>{pick({ en: 'Observed at the last month', es: 'Observada al último mes' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.vintage_curves.map((c) => {
                const last = c.months.length - 1;
                const complete = c.observed_cumulative_pd.every((v) => v !== null);
                return (
                  <tr key={c.fiscal_year} data-vintage={c.fiscal_year} data-observed={complete ? 'complete' : 'partial'} className={c.fiscal_year === sel.vintage ? 'ct-current' : undefined}>
                    <td className="ct-text">{pick(fyText(c.fiscal_year), lang)}</td>
                    <td className="ct-wide-only">{count(c.n, lang)}</td>
                    <td>{count(c.observed_until_month, lang)}</td>
                    <td>{p2(c.predicted_cumulative_pd[last], lang)}</td>
                    <td>
                      <MaybeNumber value={c.observed_cumulative_pd[last]} reason={c.reason} format={(v) => p2(v, lang)} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The five-year mark of each vintage: observed against predicted PD, read only at the mark. */
export function FiveYearView({ sel }: { sel: C03Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const rows = o.vintage_summary.rows;
  const data = rows.flatMap((r) => [
    { id: `${r.fiscal_year}-observed`, label: { en: `${fyText(r.fiscal_year).en}, observed`, es: `${fyText(r.fiscal_year).es}, observada` }, value: r.observed_5y_pd, tone: 'accent' as const, highlight: r.fiscal_year === sel.vintage },
    { id: `${r.fiscal_year}-predicted`, label: { en: `${fyText(r.fiscal_year).en}, predicted`, es: `${fyText(r.fiscal_year).es}, predicha` }, value: r.predicted_5y_pd, tone: 'neutral' as const },
  ]);
  const num = (v: number | null, reason: string | null = null) => <MaybeNumber value={v} reason={reason} format={(x) => p2(x, lang)} />;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The five-year mark of each vintage', es: 'La marca de cinco años de cada cosecha' }}
        {...card}
        note={{
          en: 'The target is charged off within 60 months of approval, and a vintage is read only at its 5-year mark: before that date the observed PD is not available, and its reason says when the mark falls. Predicted is the model\'s PD at 60 months.',
          es: 'El objetivo es el castigo dentro de 60 meses desde la aprobación, y una cosecha se lee solo en su marca de 5 años: antes de esa fecha la PD observada no está disponible, y su razón dice cuándo cae la marca. La predicha es la PD del modelo a 60 meses.',
        }}
      >
        <ChartOverTable
          chart={<BarChart title={{ en: 'Five-year PD by vintage', es: 'PD a cinco años por cosecha' }} height="fill" orientation="horizontal" data={data} axis={{ label: { en: 'PD at 60 months', es: 'PD a 60 meses' }, format: { percent: true, digits: 2 } }} />}
        >
          <table className="caos-table ct-wrap-head" data-table="five-year-mark">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Vintage', es: 'Cosecha' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Resolved', es: 'Resueltos' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Exempt (active)', es: 'Exentos (vigentes)' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: `Approved (${o.vintage_summary.currency})`, es: `Aprobado (${o.vintage_summary.currency})` }, lang)}</th>
                <th className="ct-text">{pick({ en: 'The mark falls on', es: 'La marca cae el' }, lang)}</th>
                <th>{pick({ en: 'Observed', es: 'Observada' }, lang)}</th>
                <th>{pick({ en: 'Predicted', es: 'Predicha' }, lang)}</th>
                <th>{pick({ en: 'Gap', es: 'Brecha' }, lang)}</th>
                <th className="ct-wide-only">Brier</th>
                <th className="ct-wide-only">AUC</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.fiscal_year} data-vintage={r.fiscal_year} data-mark-observed={String(r.mark_observed)} className={r.fiscal_year === sel.vintage ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(fyText(r.fiscal_year), lang)}</td>
                  <td className="ct-wide-only">{count(r.n_resolved, lang)}</td>
                  <td className="ct-wide-only">{count(r.n_exempt_censored, lang)}</td>
                  <td className="ct-wide-only">{money(r.gross_approval, lang, o.vintage_summary.currency)}</td>
                  <td className="ct-text">{r.five_year_mark_date}</td>
                  <td>{num(r.observed_5y_pd, r.reason)}</td>
                  <td>{p2(r.predicted_5y_pd, lang)}</td>
                  <td>{num(r.gap)}</td>
                  <td className="ct-wide-only">
                    <MaybeNumber value={r.brier} reason={null} format={(x) => formatNumber(x, lang, { digits: 3 })} />
                  </td>
                  <td className="ct-wide-only">
                    <MaybeNumber value={r.auc} reason={null} format={(x) => formatNumber(x, lang, { digits: 3 })} />
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

/** The population stability index of each vintage against the training population. */
/** The conventional band of a PSI (below 0.10, 0.10 to 0.25, above 0.25): a rule of thumb with no error control, told in words because the bar chart draws no reference line. */
export function psiBand(psi: number): { en: string; es: string } {
  if (psi < 0.1) return { en: 'below 0.10', es: 'bajo 0,10' };
  if (psi <= 0.25) return { en: '0.10 to 0.25', es: '0,10 a 0,25' };
  return { en: 'above 0.25', es: 'sobre 0,25' };
}

export function StabilityView({ sel }: { sel: C03Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const s = o.stability;
  const reasonOf = (fy: number) => o.vintage_summary.rows.find((r) => r.fiscal_year === fy)?.reason ?? null;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Stability of the vintages', es: 'Estabilidad de las cosechas' }}
        {...card}
        note={s.psi_note}
      >
        <ChartOverTable
          chart={
            <BarChart
              title={{ en: 'Population stability index by vintage', es: 'Índice de estabilidad poblacional por cosecha' }}
              height="fill"
              orientation="horizontal"
              data={s.rows.map((r) => ({ id: `${r.fiscal_year}`, label: fyText(r.fiscal_year), value: r.psi, tone: 'accent' as const, highlight: r.fiscal_year === sel.vintage }))}
              axis={{ label: { en: 'PSI against the training population', es: 'PSI contra la población de entrenamiento' }, format: { digits: 2 } }}
            />
          }
        >
          <p className="ct-note" data-training-mean={s.training_mean_5y_pd}>
            {pick({ en: `Mean 5-year PD of the training window: ${p2(s.training_mean_5y_pd, 'en')}`, es: `PD media a 5 años de la ventana de entrenamiento: ${p2(s.training_mean_5y_pd, 'es')}` }, lang)}
          </p>
          <table className="caos-table ct-wrap-head" data-table="stability">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Vintage', es: 'Cosecha' }, lang)}</th>
                <th>PSI</th>
                <th className="ct-text">{pick({ en: 'Convention band', es: 'Banda convencional' }, lang)}</th>
                <th>{pick({ en: 'Observed 5-year PD', es: 'PD observada a 5 años' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {s.rows.map((r) => (
                <tr key={r.fiscal_year} data-vintage={r.fiscal_year} className={r.fiscal_year === sel.vintage ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(fyText(r.fiscal_year), lang)}</td>
                  <td>{formatNumber(r.psi, lang, { digits: 3 })}</td>
                  <td className="ct-text" data-band>{pick(psiBand(r.psi), lang)}</td>
                  <td>
                    <MaybeNumber value={r.observed_5y_pd} reason={reasonOf(r.fiscal_year)} format={(v) => p2(v, lang)} />
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
