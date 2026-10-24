// C17's Capital group: the 99.9 percent capital of each rung of the ladder across the independent histories of a cell,
// always beside the true quantile of the generator; the same capital across the cells of the grid (years of data and
// collection threshold); and the influence of each scenario on the capital. Each draws what the c17-outputs document
// carries. A rung the bake did not evaluate shows its reason and no bar; the mean-corrected SLA keeps its UNVERIFIED label
// wherever it is named.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { ChartOverTable, axisScale } from '../c06/format';
import { useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { KeyTable } from './KeyTable';
import { C17TestsTable } from './Tests';
import { RUNG_ORDER, SCENARIO_KIND_TEXT, UNVERIFIED, capitalOf, cellLabel, cellOf, METHOD_TEXT, outputsOf, rungName, scenarioOf, text, whole, type C17Capital, type C17Sel } from './selection';
import { es, inSentence } from './localise';

const ratio = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { digits: 3 });
const pct = (v: number, lang: 'en' | 'es', decimals = 2) => formatNumber(v, lang, { percent: true, decimals });

/** The cells of a summary row: the percentiles, the ratio to the truth, the share that underestimates, the spread. */
function SummaryCells({ s, lang }: { s: C17Capital; lang: 'en' | 'es' }) {
  return (
    <>
      <td className="ct-wide-only">{whole(s.capital_eur.p05, lang)}</td>
      <td>{whole(s.capital_eur.median, lang)}</td>
      <td className="ct-wide-only">{whole(s.capital_eur.p95, lang)}</td>
      <td>{ratio(s.ratio_to_truth.median, lang)}</td>
      <td>{pct(s.share_underestimating, lang)}</td>
      <td className="ct-wide-only">{pct(s.iqr_over_truth, lang)}</td>
      <td className="ct-wide-only">{formatNumber(s.log_sd, lang, { digits: 3 })}</td>
    </>
  );
}

function HeadCells({ lang }: { lang: 'en' | 'es' }) {
  return (
    <>
      <th className="ct-wide-only">{pick({ en: '5th percentile (EUR)', es: 'Percentil 5 (EUR)' }, lang)}</th>
      <th>{pick({ en: 'Median (EUR)', es: 'Mediana (EUR)' }, lang)}</th>
      <th className="ct-wide-only">{pick({ en: '95th percentile (EUR)', es: 'Percentil 95 (EUR)' }, lang)}</th>
      <th>{pick({ en: 'Median over the truth', es: 'Mediana sobre la verdad' }, lang)}</th>
      <th>{pick({ en: 'Histories below the truth', es: 'Historias bajo la verdad' }, lang)}</th>
      <th className="ct-wide-only">{pick({ en: 'Spread over the truth', es: 'Dispersión sobre la verdad' }, lang)}</th>
      <th className="ct-wide-only">{pick({ en: 'Log standard deviation', es: 'Desviación estándar log' }, lang)}</th>
    </>
  );
}

/** The capital of every rung of the ladder in the cell chosen, drawn beside the true quantile of the generator. */
export function ByMethodView({ sel }: { sel: C17Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const cell = cellOf(o, sel.years, sel.threshold);
  const truth = o.truth.annual_loss_quantile.value_eur;
  const rungs = RUNG_ORDER.map((id) => ({ id, ...capitalOf(cell, id) }));
  const scale = axisScale(Math.max(truth, ...rungs.map((r) => r.summary?.capital_eur.median ?? 0)), 'EUR');
  const label = cellLabel(cell.years, cell.collection_threshold_eur);
  const data = [
    { id: 'truth', label: { en: 'True quantile', es: 'Cuantil verdadero' }, value: truth / scale.div, tone: 'neutral' as const, hint: { en: 'The 99.9 percent quantile of the annual loss of the generator', es: 'El cuantil al 99,9 por ciento de la pérdida anual del generador' } },
    ...rungs.map((r) => ({
      id: r.id,
      label: rungName(r.id),
      value: r.summary ? r.summary.capital_eur.median / scale.div : null,
      tone: r.summary?.status === UNVERIFIED || r.id === 'sla-mean-corrected' ? ('warn' as const) : ('accent' as const),
      highlight: r.id === sel.rung,
    })),
  ];
  const na = formatNumber(null, lang);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `Capital by method: ${label.en}`, es: `Capital por método: ${label.es}` }}
        {...card}
        note={{
          en: 'The 99.9 percent capital each method gives, as the median over the independent histories of the cell, beside the true quantile of the generator (grey). A method below the grey bar underestimates the capital. Amber is the mean-corrected approximation, kept UNVERIFIED until it is checked against its primary text. A method with no bar was not evaluated for this cell, and the table says why.',
          es: 'El capital al 99,9 por ciento que da cada método, como la mediana sobre las historias independientes de la celda, junto al cuantil verdadero del generador (gris). Un método bajo la barra gris subestima el capital. Ámbar es la aproximación corregida por la media, que sigue SIN VERIFICAR hasta que se verifique contra su texto primario. Un método sin barra no se evaluó para esta celda, y la tabla dice por qué.',
        }}
      >
        <ChartOverTable
          chartMin={`${data.length * 2.5 + 3}rem`}
          chart={
            <BarChart
              title={{ en: `Median capital by method against the true quantile, ${label.en}`, es: `Capital mediano por método contra el cuantil verdadero, ${label.es}` }}
              height="fill"
              orientation="horizontal"
              data={data}
              axis={{ label: { en: `99.9% capital (${pick(scale.unit, 'en')})`, es: `Capital al 99,9 % (${pick(scale.unit, 'es')})` }, format: { digits: 3 } }}
            />
          }
        >
          <div data-infinite-mean={String(o.infinite_mean)}>
            {o.infinite_mean ? (
              <p className="ct-note">
                {pick({ en: 'The tail index of this variant is 1 or more, so the severity has no mean: the mean-corrected approximation needs it and is not available.', es: 'El índice de cola de esta variante es 1 o más, así que la severidad no tiene media: la aproximación corregida por la media la necesita y no está disponible.' }, lang)}
              </p>
            ) : null}
          </div>
          <p className="ct-note" data-bar-truth data-quantile={truth}>
            {pick(
              {
                en: `True 99.9% quantile of the generator, the grey bar: ${whole(truth, 'en')} EUR. A method that is exact has a median over the truth of 1.`,
                es: `Cuantil verdadero 99,9 % del generador, la barra gris: ${whole(truth, 'es')} EUR. Un método exacto tiene una mediana sobre la verdad de 1.`,
              },
              lang,
            )}
          </p>
          <table className="caos-table ct-wrap-head" data-table="capital-by-rung" data-cell={cell.id}>
            <thead>
              <tr>
                <th className="ct-text" style={{ minWidth: '11rem' }}>{pick({ en: 'Method', es: 'Método' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Histories', es: 'Historias' }, lang)}</th>
                <HeadCells lang={lang} />
              </tr>
            </thead>
            <tbody>
              {rungs.map((r) => {
                const status = r.summary?.status ?? (r.id === 'sla-mean-corrected' ? UNVERIFIED : 'verified');
                return (
                  <tr key={r.id} data-rung={r.id} data-status={status} className={r.id === sel.rung ? 'ct-current' : undefined}>
                    <td className="ct-text" title={pick(rungName(r.id), lang)}>{pick(rungName(r.id), lang)}</td>
                    {r.summary ? (
                      <>
                        <td className="ct-wide-only">{whole(r.summary.n_defined, lang)}</td>
                        <SummaryCells s={r.summary} lang={lang} />
                      </>
                    ) : (
                      <td colSpan={8} data-na="true" className="ct-text">
                        {na}
                        <span className="ct-note">{` (${es(r.reason, lang)})`}</span>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
          <C17TestsTable variant={sel.data.variant} host="method" />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The capital of the rung in focus across the four cells of the grid: years of data and collection threshold. */
export function ByYearsView({ sel }: { sel: C17Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const truth = o.truth.annual_loss_quantile.value_eur;
  const rung = rungName(sel.rung);
  const cells = o.cells.map((c) => ({ c, ...capitalOf(c, sel.rung) }));
  const scale = axisScale(Math.max(truth, ...cells.map((x) => x.summary?.capital_eur.median ?? 0)), 'EUR');
  const na = formatNumber(null, lang);
  const data = [
    { id: 'truth', label: { en: 'True quantile', es: 'Cuantil verdadero' }, value: truth / scale.div, tone: 'neutral' as const },
    ...cells.map(({ c, summary }) => ({
      id: c.id,
      label: cellLabel(c.years, c.collection_threshold_eur),
      value: summary ? summary.capital_eur.median / scale.div : null,
      tone: summary?.status === UNVERIFIED ? ('warn' as const) : ('accent' as const),
      highlight: c.years === sel.years && c.collection_threshold_eur === sel.threshold,
    })),
  ];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `Capital by years of data and threshold: ${rung.en}`, es: `Capital por años de datos y umbral: ${rung.es}` }}
        {...card}
        note={{
          en: 'The same method on every cell of the grid: 5 or 10 years of recorded losses, and losses recorded from EUR 10,000 or from EUR 20,000. Each bar is the median over the independent histories of the cell; the spread of the histories is in the table. The grey bar is the true quantile.',
          es: 'El mismo método en cada celda de la grilla: 5 o 10 años de pérdidas registradas, y pérdidas registradas desde EUR 10.000 o desde EUR 20.000. Cada barra es la mediana sobre las historias independientes de la celda; la dispersión de las historias está en la tabla. La barra gris es el cuantil verdadero.',
        }}
      >
        <div className="ct-c17-tall">
        <ChartOverTable
          chartMin={`${data.length * 2 + 3}rem`}
          chart={
            <BarChart
              title={{ en: `Median capital of ${inSentence(rung.en)} by cell, against the true quantile`, es: `Capital mediano de ${inSentence(rung.es)} por celda, contra el cuantil verdadero` }}
              height="fill"
              orientation="horizontal"
              data={data}
              axis={{ label: { en: `99.9% capital (${pick(scale.unit, 'en')})`, es: `Capital al 99,9 % (${pick(scale.unit, 'es')})` }, format: { digits: 3 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="capital-by-cell" data-rung={sel.rung}>
            <thead>
              <tr>
                <th className="ct-text" style={{ minWidth: '8rem' }}>{pick({ en: 'Cell', es: 'Celda' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Histories', es: 'Historias' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Failed fits', es: 'Ajustes fallidos' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Defined for this method', es: 'Definido para este método' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Losses per history, median', es: 'Pérdidas por historia, mediana' }, lang)}</th>
                <HeadCells lang={lang} />
              </tr>
            </thead>
            <tbody>
              {cells.map(({ c, summary, reason }) => (
                <tr key={c.id} data-cell={c.id} className={c.years === sel.years && c.collection_threshold_eur === sel.threshold ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(cellLabel(c.years, c.collection_threshold_eur), lang)}</td>
                  <td className="ct-wide-only">{whole(c.replications.n_replications, lang)}</td>
                  <td className="ct-wide-only">{whole(c.replications.n_failed, lang)}</td>
                  <td className="ct-wide-only" data-n-defined={summary ? summary.n_defined : undefined}>{summary ? whole(summary.n_defined, lang) : na}</td>
                  <td className="ct-wide-only">{whole(c.replications.n_losses_median, lang)}</td>
                  {summary ? (
                    <SummaryCells s={summary} lang={lang} />
                  ) : (
                    <td colSpan={7} data-na="true" className="ct-text">
                      {na}
                      <span className="ct-note">{` (${es(reason, lang)})`}</span>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

/** The influence of each scenario point on the 99.9 percent capital of one history, with the prior that combines them. */
export function ScenarioView({ sel }: { sel: C17Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const s = o.scenario_influence;
  const focus = scenarioOf(o, sel.scenario);
  const cell = o.cells.find((c) => c.id === s.cell_id);
  const where: BiText = cell ? cellLabel(cell.years, cell.collection_threshold_eur) : { en: s.cell_id, es: s.cell_id };
  const method = text(METHOD_TEXT, s.method);
  const data = s.scenarios.map((x) => ({
    id: x.scenario_id,
    label: x.label,
    value: x.influence,
    tone: x.influence < 0 ? ('warn' as const) : ('accent' as const),
    highlight: x.scenario_id === focus?.scenario_id,
  }));
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Influence of each scenario on the capital', es: 'Influencia de cada escenario en el capital' }}
        {...card}
        note={{
          en: `One history (${where.en}, seed ${s.seed}) with its scenario points combined with the losses by ${inSentence(method.en)}. The influence of a scenario is the capital with all the points, minus the capital without that point, over the capital with all of them. A negative influence means the point lowers the capital.`,
          es: `Una historia (${where.es}, semilla ${s.seed}) con sus puntos de escenario combinados con las pérdidas por ${inSentence(method.es)}. La influencia de un escenario es el capital con todos los puntos, menos el capital sin ese punto, sobre el capital con todos. Una influencia negativa significa que el punto baja el capital.`,
        }}
      >
        <ChartOverTable
          chartMin={`${data.length * 2.5 + 3}rem`}
          chart={<BarChart title={{ en: 'Influence of each scenario on the 99.9 percent capital', es: 'Influencia de cada escenario en el capital al 99,9 por ciento' }} height="fill" orientation="horizontal" data={data} axis={{ label: { en: 'Influence on the capital', es: 'Influencia en el capital' }, format: { percent: true, decimals: 0 } }} />}
        >
          <KeyTable
            table="scenario-prior"
            rows={[
              { id: 'base', label: { en: 'Capital with every point', es: 'Capital con todos los puntos' }, value: `${whole(s.base_capital_eur, lang)} EUR` },
              { id: 'method', label: { en: 'Combination', es: 'Combinación' }, value: pick(method, lang), attrs: { 'data-method': s.method } },
              {
                id: 'prior',
                label: { en: 'Prior', es: 'A priori' },
                attrs: { 'data-prior': s.prior_kind },
                value: pick(
                  {
                    en: 'Gamma on the Pareto shape alpha = 1 / xi, unrestricted (an infinite mean is not excluded); mean and 90 percent interval from the scenario points. The Contraste reading of the method, stated on every result.',
                    es: 'Gamma sobre la forma de Pareto alfa = 1 / xi, sin restricción (no se excluye una media infinita); media e intervalo del 90 por ciento desde los puntos de escenario. Lectura de Contraste del método, declarada en cada resultado.',
                  },
                  lang,
                ),
              },
              { id: 'reference', label: { en: 'Reference', es: 'Referencia' }, value: es(s.reference, lang) },
            ]}
          />
          <table className="caos-table ct-wrap-head" data-table="scenarios">
            <thead>
              <tr>
                <th className="ct-text" style={{ minWidth: '11rem' }}>{pick({ en: 'Scenario', es: 'Escenario' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Kind', es: 'Tipo' }, lang)}</th>
                <th>{pick({ en: 'Loss (EUR)', es: 'Pérdida (EUR)' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Exceedances per year', es: 'Excedencias por año' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Capital without it (EUR)', es: 'Capital sin él (EUR)' }, lang)}</th>
                <th>{pick({ en: 'Influence', es: 'Influencia' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {s.scenarios.map((x) => (
                <tr key={x.scenario_id} data-scenario={x.scenario_id} className={x.scenario_id === focus?.scenario_id ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(x.label, lang)}</td>
                  <td className="ct-text ct-wide-only">{pick(text(SCENARIO_KIND_TEXT, x.kind), lang)}</td>
                  <td>{whole(x.loss_eur, lang)}</td>
                  <td className="ct-wide-only">{formatNumber(x.exceedance_frequency_per_year, lang, { digits: 3 })}</td>
                  <td className="ct-wide-only">{whole(x.capital_without_eur, lang)}</td>
                  <td>{pct(x.influence, lang, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <C17TestsTable variant={sel.data.variant} host="scenario" />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

