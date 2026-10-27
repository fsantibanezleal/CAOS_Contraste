// C08's Downturn and floors group: the downturn add-on against the losses the crisis cohorts realised (did the add-on
// cover them), and the bite of the IRB LGD floors with the transcribed floor cells. Each draws what the c08-outputs
// and c08-models documents carry; an LGD outside [0, 1] keeps its flag.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable } from '../c06/format';
import { Flagged, p2, useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { cohortLabel, cohortYear, fitOf, floorCellLabel, outputsOf, segmentLabel, type C08Sel } from './selection';
import { YEAR_FORMAT, rangeText } from './words';

export { YEAR_FORMAT };

const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });

/** The downturn add-on: long-run LGD, downturn LGD and the LGD the crisis cohorts realised, with the coverage. */
export function DownturnView({ sel }: { sel: C08Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const t = o.downturn;
  const rows = [...t.rows].sort((a, b) => cohortYear(sel, a.cohort_id) - cohortYear(sel, b.cohort_id));
  const yes = pick({ en: 'covered', es: 'cubierta' }, lang);
  const no = pick({ en: 'not covered', es: 'no cubierta' }, lang);
  // the downturn years the bake detected and every cohort the add-on fails to cover are drawn and labelled on the chart, with the
  // shortfall, not only named under it (rubric law 2; R3 c09 MN2)
  const marks = [
    { x: t.period.first_year, label: { en: `Downturn from ${t.period.first_year}`, es: `Recesión desde ${t.period.first_year}` } },
    { x: t.period.last_year, label: { en: `Downturn to ${t.period.last_year}`, es: `Recesión hasta ${t.period.last_year}` } },
    ...rows
      .filter((r) => !r.covered)
      .map((r) => {
        const name = cohortLabel(sel, r.cohort_id);
        return { x: cohortYear(sel, r.cohort_id), label: { en: `${name.en}: not covered, shortfall ${p2(r.shortfall, 'en')}`, es: `${name.es}: no cubierta, faltante ${p2(r.shortfall, 'es')}` } };
      }),
  ];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Downturn LGD against the crisis losses', es: 'LGD de recesión contra las pérdidas de la crisis' }}
        {...card}
        note={{
          en: 'The downturn LGD is the long-run LGD plus an add-on. A crisis cohort whose realised LGD lies above the downturn line was not covered by the add-on, and the shortfall is the distance. The downturn years are marked on the chart and named below it with the indicator that identifies them; a cohort the add-on does not cover is drawn in red and labelled with its shortfall.',
          es: 'La LGD de recesión es la LGD de largo plazo más un ajuste. Una cohorte de crisis cuya LGD realizada queda sobre la línea de recesión no fue cubierta por el ajuste, y el faltante es la distancia. Los años de recesión se marcan en el gráfico y se nombran bajo él con el indicador que los identifica; una cohorte que el ajuste no cubre se dibuja en rojo y se rotula con su faltante.',
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: rows.map((r) => cohortYear(sel, r.cohort_id)), label: { en: 'First default year of the cohort', es: 'Primer año de incumplimiento de la cohorte' }, format: YEAR_FORMAT }}
              y={{ label: { en: 'Mean LGD', es: 'LGD media' }, format: { percent: true, digits: 2 } }}
              series={[
                { label: { en: 'Long-run LGD', es: 'LGD de largo plazo' }, values: rows.map((r) => r.long_run_lgd.value), color: '--color-fg-subtle', width: 1.8, dash: [6, 3] },
                { label: { en: 'Downturn LGD', es: 'LGD de recesión' }, values: rows.map((r) => r.downturn_lgd.value), color: '--color-warn', width: 2.6 },
                { label: { en: 'Realised, covered by the add-on', es: 'Realizada, cubierta por el ajuste' }, values: rows.map((r) => (r.covered ? r.crisis_realised_lgd.value : null)), color: '--color-good', mode: 'points', size: 11 },
                { label: { en: 'Realised, not covered by the add-on', es: 'Realizada, no cubierta por el ajuste' }, values: rows.map((r) => (r.covered ? null : r.crisis_realised_lgd.value)), color: '--color-bad', mode: 'points', size: 11 },
              ]}
              marks={marks}
            />
          }
        >
          <p className="ct-note" data-downturn-period={`${t.period.first_year}-${t.period.last_year}`}>
            {pick(
              {
                en: `Downturn years ${t.period.first_year} to ${t.period.last_year}, identified by the ${pick(t.period.indicator, 'en')}. Macro source: ${pick(t.period.macro_source, 'en')}.`,
                es: `Años de recesión ${t.period.first_year} a ${t.period.last_year}, identificados por la ${pick(t.period.indicator, 'es')}. Fuente macro: ${pick(t.period.macro_source, 'es')}.`,
              },
              lang,
            )}
          </p>
          <p className="ct-note">{pick(t.approach, lang)}</p>
          <p className="ct-note" data-coverage={t.coverage.share_covered}>
            {pick(
              {
                en: `Share of the crisis cohorts covered by the add-on: ${p2(t.coverage.share_covered, 'en')} of ${count(t.coverage.n_cohorts, 'en')} cohorts.`,
                es: `Proporción de las cohortes de crisis cubiertas por el ajuste: ${p2(t.coverage.share_covered, 'es')} de ${count(t.coverage.n_cohorts, 'es')} cohortes.`,
              },
              lang,
            )}
          </p>
          <table className="caos-table ct-wrap-head" data-table="downturn">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Default cohort', es: 'Cohorte de incumplimiento' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Long-run LGD', es: 'LGD de largo plazo' }, lang)}</th>
                <th>{pick({ en: 'Downturn LGD', es: 'LGD de recesión' }, lang)}</th>
                <th>{pick({ en: 'Add-on', es: 'Ajuste' }, lang)}</th>
                <th>{pick({ en: 'Realised in the crisis', es: 'Realizada en la crisis' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Covered', es: 'Cubierta' }, lang)}</th>
                <th>{pick({ en: 'Shortfall', es: 'Faltante' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.cohort_id} data-cohort={r.cohort_id} data-covered={String(r.covered)} className={r.cohort_id === sel.cohort ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(cohortLabel(sel, r.cohort_id), lang)}</td>
                  <td className="ct-wide-only">
                    <Flagged value={r.long_run_lgd.value} flag={r.long_run_lgd.flag} />
                  </td>
                  <td>
                    <Flagged value={r.downturn_lgd.value} flag={r.downturn_lgd.flag} />
                  </td>
                  <td>{p2(r.add_on, lang)}</td>
                  <td>
                    <Flagged value={r.crisis_realised_lgd.value} flag={r.crisis_realised_lgd.flag} />
                  </td>
                  <td className="ct-text">{r.covered ? yes : no}</td>
                  <td>{p2(r.shortfall, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The bite of the IRB LGD floors on the estimates, and the floor cells the bake transcribed from the framework. */
export function FloorsView({ sel }: { sel: C08Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const fb = o.floors_bite;
  const fit = fitOf(sel);
  const cells = fit?.floors.cells ?? [];
  const cellOf = (id: string) => cells.find((c) => c.id === id);
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={{ en: 'The bite of the LGD floors', es: 'El efecto de los pisos de LGD' }}
        {...card}
        note={{
          en: 'A floor lifts an estimate that falls below it. The bar is the share of the defaults of each segment where the floor binds; the table gives the mean LGD before and after and the uplift the floor causes.',
          es: 'Un piso sube una estimación que cae bajo él. La barra es la proporción de los incumplimientos de cada segmento donde el piso se activa; la tabla da la LGD media antes y después y el alza que causa el piso.',
        }}
      >
        <ChartOverTable
          chart={
            <BarChart
              title={{ en: 'Share of defaults where the floor binds', es: 'Proporción de incumplimientos donde el piso se activa' }}
              height="fill"
              orientation="horizontal"
              data={fb.rows.map((r) => ({ id: r.segment_id, label: segmentLabel(r.segment_id), value: r.share_binding, tone: 'accent' as const, highlight: r.segment_id === sel.segment }))}
              axis={{ label: { en: 'Share where the floor binds', es: 'Proporción donde el piso se activa' }, format: { percent: true, digits: 2 }, range: [0, 1] }}
            />
          }
        >
          <p className="ct-note">{pick(fb.note, lang)}</p>
          <table className="caos-table ct-wrap-head" data-table="floors-bite">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Segment', es: 'Segmento' }, lang)}</th>
                <th>{pick({ en: 'Floor', es: 'Piso' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Defaults', es: 'Incumplimientos' }, lang)}</th>
                <th>{pick({ en: 'Binds', es: 'Se activa' }, lang)}</th>
                <th>{pick({ en: 'Before', es: 'Antes' }, lang)}</th>
                <th>{pick({ en: 'After', es: 'Después' }, lang)}</th>
                <th>{pick({ en: 'Uplift', es: 'Alza' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {fb.rows.map((r) => (
                <tr key={r.segment_id} data-floor={r.floor_id} data-segment={r.segment_id} className={r.segment_id === sel.segment ? 'ct-current' : undefined}>
                  <td className="ct-text" title={rangeText(r.reference, lang)}>{pick(segmentLabel(r.segment_id), lang)}</td>
                  <td>{p2(r.floor, lang)}</td>
                  <td className="ct-wide-only">{count(r.n, lang)}</td>
                  <td>{p2(r.share_binding, lang)}</td>
                  <td>{p2(r.mean_before.value, lang)}</td>
                  <td>{p2(r.mean_after.value, lang)}</td>
                  <td>{p2(r.uplift, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
      <PlotCard fill title={{ en: 'The floor cells', es: 'Las celdas de los pisos' }} {...card} note={{ en: 'The LGD floors of the framework as the run recorded them: a floor per portfolio and collateral class.', es: 'Los pisos de LGD del marco tal como los registró la corrida: un piso por cartera y clase de garantía.' }}>
        {cells.length === 0 ? (
          <p className="caos-pending" data-state="unavailable">
            {pick({ en: 'Not available: the models artifact carries no floor cells.', es: 'No disponible: el artefacto de modelos no trae las celdas de pisos.' }, lang)}
          </p>
        ) : (
          <div className="ct-scroll" data-caos-flow="">
            <table className="caos-table ct-wrap-head" data-table="floor-cells">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Class', es: 'Clase' }, lang)}</th>
                  <th>{pick({ en: 'Floor', es: 'Piso' }, lang)}</th>
                  <th className="ct-text ct-wide-only">{pick({ en: 'Paragraph', es: 'Párrafo' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {cells.map((c) => (
                  <tr key={c.id} data-cell={c.id} className={cellOf(fb.rows.find((r) => r.segment_id === sel.segment)?.floor_id ?? '')?.id === c.id ? 'ct-current' : undefined}>
                    <td className="ct-text">{pick(floorCellLabel(c), lang)}</td>
                    <td>{p2(c.floor, lang)}</td>
                    <td className="ct-text ct-wide-only" translate="no">{rangeText(c.reference, lang)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="ct-note" data-regime={fit?.floors.regime} translate="no">{fit?.floors.source ? pick(fit.floors.source, lang) : null}</p>
          </div>
        )}
      </PlotCard>
    </ViewsRow>
  );
}
