// C10's Model group and the models half of its Context group: the ladder of rungs with the engine function and the
// reference of each, the illustrative portfolio's specification (labelled illustrative), and the loan types, the two
// correlation estimators and the simulator grid the bake runs. Read from the models artifact, so a rung or a group is the
// same words here and in the loss views.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { ChartOverTable } from '../c06/format';
import { Pending } from '../Pending';
import { barMin } from './format';
import { useCard } from '../c03/U6Shared';
import { NoticeFlow } from './C10Common';
import { noteText } from '../c08/notes';
import { ESTIMATOR_KIND_TEXT, ESTIMATOR_TEXT, INTERVAL_TEXT, IRB_CLASS_TEXT, METHOD_TEXT, PARAMETER_TEXT, SECTOR_TEXT, fitOf, gridOf, measureText, outputsOf, referenceNote, rungOf, text, type C10GridOutputs, type C10Sel } from './selection';

const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });

/** The inputs a simulator grid sets for every rung: the known PD and the asset correlations of its cells, as its generator states them. */
export function gridInputs(g: C10GridOutputs, lang: 'en' | 'es'): string {
  const pd = formatNumber(g.generator.known_pd, lang, { digits: 4 });
  const rhos = g.generator.rho_grid;
  const lo = formatNumber(Math.min(...rhos), lang, { digits: 4 });
  const hi = formatNumber(Math.max(...rhos), lang, { digits: 4 });
  return lang === 'es'
    ? `fijadas por la grilla simulada: PD conocida ${pd}; correlación de activos de ${lo} a ${hi} según la celda`
    : `set by the simulated grid: known PD ${pd}; asset correlation ${lo} to ${hi} by cell`;
}

/** The ladder: every rung of the models artifact with its method, scenarios, engine function, reference and inputs. */
export function LadderView({ sel }: { sel: C10Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const fit = fitOf(sel);
  if (!sel || !fit) return <Pending />;
  const o = outputsOf(sel);
  const grid = o ? null : gridOf(sel);
  // the scenarios a rung ran: the variant's own simulation when it carries the rung (a rung that did not run has none, whatever the
  // ladder plans for it), the planned count of the models artifact for a document that does not (U16-R2 b05 B2)
  const ran = (id: string, planned: number | null, evaluated?: boolean): { n: number | null; why: BiText | undefined } => {
    const rung = o ? rungOf(o, id) : undefined;
    // a document without rungs of its own (a simulator grid) draws a rung no variant runs as not run, never its plan (R2b c11 B4)
    if (!rung && evaluated === false) return { n: null, why: { en: 'Not run: no variant evaluates this rung.', es: 'No corre: ninguna variante evalúa este escalón.' } };
    if (!rung) return { n: planned, why: planned === null ? ({ en: 'Analytic: no scenarios.', es: 'Analítico: sin escenarios.' } as BiText) : undefined };
    if (!rung.evaluated) return { n: null, why: { en: noteText(rung.reason, 'en'), es: noteText(rung.reason, 'es') } };
    return { n: rung.simulation?.n_scenarios ?? null, why: rung.simulation ? undefined : ({ en: 'Analytic: no scenarios.', es: 'Analítico: sin escenarios.' } as BiText) };
  };
  const data = fit.ladder.map((r) => ({ id: r.id, label: { en: r.label.en, es: r.label.es } as BiText, value: ran(r.id, r.n_scenarios, r.evaluated).n, tone: 'accent' as const, hint: ran(r.id, r.n_scenarios, r.evaluated).why }));
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The ladder of portfolio models', es: 'La escalera de modelos de cartera' }}
        {...card}
        note={{
          en: 'From the infinitely granular approximation to the sampled and recursive models: each rung is a function of the engine with its reference and its inputs. The bars are the Monte Carlo scenarios of the sampled rungs; an analytic rung has none, so its bar reads not available.',
          es: 'De la aproximación infinitamente granular a los modelos muestreados y recursivos: cada escalón es una función del motor con su referencia y sus entradas. Las barras son los escenarios de Monte Carlo de los escalones muestreados; un escalón analítico no tiene, así que su barra dice no disponible.',
        }}
      >
        <ChartOverTable
          chartMin={barMin(data.length)}
          chart={<BarChart title={{ en: 'Monte Carlo scenarios by rung', es: 'Escenarios de Monte Carlo por escalón' }} height="fill" orientation="horizontal" data={data} axis={{ label: { en: 'Scenarios', es: 'Escenarios' }, format: { decimals: 0 } }} />}
        >
          <table className="caos-table ct-wrap-head" data-table="c10-ladder">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Rung', es: 'Escalón' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Method', es: 'Método' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Estimator', es: 'Estimador' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Scenarios', es: 'Escenarios' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Engine function', es: 'Función del motor' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Reference', es: 'Referencia' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Inputs', es: 'Entradas' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {fit.ladder.map((r) => (
                <tr key={r.id} data-rung={r.id} data-ladder={r.rung}>
                  <td className="ct-text">{`${r.rung}: ${pick(r.label, lang)}`}</td>
                  <td className="ct-text">{pick(text(METHOD_TEXT, r.method), lang)}</td>
                  <td className="ct-text ct-wide-only">{pick(text(ESTIMATOR_KIND_TEXT, r.estimator), lang)}</td>
                  <td className="ct-text ct-wide-only" data-na={ran(r.id, r.n_scenarios, r.evaluated).n === null ? 'true' : undefined}>{ran(r.id, r.n_scenarios, r.evaluated).n === null ? (ran(r.id, r.n_scenarios, r.evaluated).why ? pick(ran(r.id, r.n_scenarios, r.evaluated).why as BiText, lang) : formatNumber(null, lang)) : count(ran(r.id, r.n_scenarios).n as number, lang)}</td>
                  {/* a rung that does not run calls no engine function: the planned one is not named (R4 c12 m-N3) */}
                  <td className="ct-text ct-wide-only" translate="no">{r.evaluated === false ? <span translate="yes">{pick({ en: 'none: the rung does not run', es: 'ninguna: el escalón no corre' }, lang)}</span> : <code>{r.engine_function}</code>}</td>
                  <td className="ct-text">{referenceNote(r.reference, lang)}</td>
                  {/* the variant's own calibration of the rung (each loan type fits its own PD and correlation); the fit's ladder only when the variant has none (R3 c11 B1) */}
                  {/* a simulator grid has no rungs of its own: its inputs are the generator's known PD and correlation grid, never the
                      calibration of a loan type from the models artifact (R4 c12 and c13 B1) */}
                  <td className="ct-text ct-wide-only" data-inputs={r.id}>{grid ? gridInputs(grid, lang) : ((o ? rungOf(o, r.id)?.parameters : undefined) ?? r.parameters).map((p) => measureText(PARAMETER_TEXT, p.name, p.value, p.unit, lang)).join('; ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The illustrative portfolio: its groups, the loss given default and its dispersion, the concentration measures. */
export function PortfolioView({ sel }: { sel: C10Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const fit = fitOf(sel);
  const spec = o?.portfolio ?? fit?.portfolio_spec ?? null;
  if (!sel || !spec) return <Pending />;
  const pc = (v: number, d = 2) => formatNumber(v, lang, { percent: true, decimals: d });
  const ccy = spec.currency;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The illustrative portfolio', es: 'La cartera ilustrativa' }}
        {...card}
        note={{
          en: 'Names grouped by size, probability of default and loading on the systematic factor: a few large names, a middle group and many small ones. It is constructed to show how concentration and dependence move the tail, and it is never a bank\'s portfolio.',
          es: 'Nombres agrupados por tamaño, probabilidad de incumplimiento y carga en el factor sistemático: pocos nombres grandes, un grupo medio y muchos pequeños. Está construida para mostrar cómo la concentración y la dependencia mueven la cola, y nunca es la cartera de un banco.',
        }}
      >
        <NoticeFlow notice={spec.notice}>
        <ChartOverTable
          chartMin={barMin(spec.groups.length)}
          chart={
            <BarChart
              title={{ en: 'Probability of default by group', es: 'Probabilidad de incumplimiento por grupo' }}
              height="fill"
              orientation="horizontal"
              data={spec.groups.map((g) => ({ id: g.id, label: { en: g.label.en, es: g.label.es } as BiText, value: g.pd, tone: 'accent' as const, highlight: g.id === sel.group }))}
              axis={{ label: { en: 'Probability of default', es: 'Probabilidad de incumplimiento' }, format: { percent: true, decimals: 2 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c10-groups">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Group', es: 'Grupo' }, lang)}</th>
                <th>{pick({ en: 'Names', es: 'Nombres' }, lang)}</th>
                <th>{pick({ en: `Exposure each, ${ccy}`, es: `Exposición c/u, ${ccy}` }, lang)}</th>
                <th>PD</th>
                <th className="ct-wide-only">{pick({ en: 'Loss given default', es: 'Pérdida dado el incumplimiento' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Loading', es: 'Carga' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Sector', es: 'Sector' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {spec.groups.map((g) => (
                <tr key={g.id} data-group={g.id} className={g.id === sel.group ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(g.label, lang)}</td>
                  <td>{count(g.n_names, lang)}</td>
                  <td>{count(g.ead_each, lang)}</td>
                  <td>{pc(g.pd)}</td>
                  <td className="ct-wide-only">{pc(g.lgd, 0)}</td>
                  <td className="ct-wide-only">{formatNumber(g.loading, lang, { digits: 3 })}</td>
                  <td className="ct-text ct-wide-only">{pick(text(SECTOR_TEXT, g.sector), lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <dl className="ct-defs" data-table="c10-portfolio">
            <dt>{pick({ en: 'Expected loss given default and its dispersion', es: 'Pérdida dado el incumplimiento esperada y su dispersión' }, lang)}</dt>
            <dd>{`${pc(spec.lgd_mean, 0)}, ${formatNumber(spec.lgd_gamma, lang, { digits: 3 })}`}</dd>
            {o ? (
              <>
                <dt>{pick({ en: 'Names and total exposure', es: 'Nombres y exposición total' }, lang)}</dt>
                <dd>{`${count(o.portfolio.n_names, lang)}, ${count(o.portfolio.total_ead, lang)} ${o.portfolio.currency}`}</dd>
                <dt>{pick({ en: 'Concentration index', es: 'Índice de concentración' }, lang)}</dt>
                <dd>{formatNumber(o.portfolio.hhi, lang, { digits: 4 })}</dd>
                <dt>{pick({ en: 'Effective number of names', es: 'Número efectivo de nombres' }, lang)}</dt>
                <dd>{formatNumber(o.portfolio.effective_names, lang, { digits: 4 })}</dd>
                <dt>{pick({ en: 'Largest share of the exposure', es: 'Mayor parte de la exposición' }, lang)}</dt>
                <dd>{pc(o.portfolio.largest_share)}</dd>
                <dt>{pick({ en: 'Calibrated to the fit', es: 'Calibrada al ajuste' }, lang)}</dt>
                <dd>{`PD ${pc(o.portfolio.calibration.pd)}, ${pick({ en: 'correlation', es: 'correlación' }, lang)} ${pc(o.portfolio.calibration.rho, 1)}`}</dd>
              </>
            ) : null}
          </dl>
        </ChartOverTable>
        </NoticeFlow>
      </PlotCard>
    </ViewsRow>
  );
}

/** The loan types with their IRB class, the two correlation estimators, and the simulator's grid: the models half of the Context. */
export function EstimatorsView({ sel }: { sel: C10Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const fit = fitOf(sel);
  if (!sel || !fit) return <Pending />;
  const s = fit.simulator;
  return (
    <>
      <PlotCard title={{ en: 'Loan types and estimators', es: 'Tipos de crédito y estimadores' }} {...card} note={{ en: 'The five loan types of the Federal Reserve charge-off table and the regulatory class whose IRB correlation each fitted correlation is compared with; the two ways the correlation is estimated and how each gets its interval.', es: 'Los cinco tipos de crédito de la tabla de castigos de la Reserva Federal y la clase regulatoria con cuya correlación IRB se compara cada correlación ajustada; las dos formas de estimar la correlación y cómo cada una obtiene su intervalo.' }}>
        <table className="caos-table ct-wrap-head" data-table="c10-loan-types">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Loan type', es: 'Tipo de crédito' }, lang)}</th>
              <th className="ct-text">{pick({ en: 'IRB class', es: 'Clase IRB' }, lang)}</th>
              <th className="ct-text">{pick({ en: 'Reference', es: 'Referencia' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {fit.loan_types.map((l) => (
              <tr key={l.id} data-loan-type={l.id}>
                <td className="ct-text">{pick(l.label, lang)}</td>
                <td className="ct-text">{pick(text(IRB_CLASS_TEXT, l.irb_asset_class), lang)}</td>
                <td className="ct-text" translate="no">{l.irb_reference}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <table className="caos-table ct-wrap-head" data-table="c10-estimator-specs">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Estimator', es: 'Estimador' }, lang)}</th>
              <th className="ct-text">{pick({ en: 'Interval', es: 'Intervalo' }, lang)}</th>
              <th className="ct-text">{pick({ en: 'Engine function', es: 'Función del motor' }, lang)}</th>
              <th className="ct-text ct-wide-only">{pick({ en: 'Reference', es: 'Referencia' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {fit.estimators.map((e) => (
              <tr key={e.id} data-estimator-spec={e.id}>
                <td className="ct-text">{pick(text(ESTIMATOR_TEXT, e.id), lang)}</td>
                <td className="ct-text">{pick(text(INTERVAL_TEXT, e.interval_method), lang)}</td>
                <td className="ct-text" translate="no"><code>{e.engine_function}</code></td>
                <td className="ct-text ct-wide-only">{referenceNote(e.reference, lang)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </PlotCard>
      {/* the simulator's card is synthetic on every variant, a loan type's too (R4 c13 n4: it was badged real) */}
      <PlotCard title={{ en: 'The simulator grid', es: 'La grilla del simulador' }} {...card} provenance="synthetic">
        <dl className="ct-defs" data-table="c10-simulator-spec">
          <dt>{pick({ en: 'Known correlations', es: 'Correlaciones conocidas' }, lang)}</dt>
          <dd>{s.rho_grid.map((r) => formatNumber(r, lang, { percent: true, decimals: 0 })).join(', ')}</dd>
          <dt>{pick({ en: 'Years in the series', es: 'Años de la serie' }, lang)}</dt>
          <dd>{s.series_lengths_years.join(', ')}</dd>
          <dt>{pick({ en: 'Replications and seed', es: 'Replicaciones y semilla' }, lang)}</dt>
          <dd>{`${count(s.n_replications, lang)}, ${s.seed}`}</dd>
          <dt>{pick({ en: 'Correlation under the null', es: 'Correlación bajo la nula' }, lang)}</dt>
          <dd>{formatNumber(s.null_rho, lang, { percent: true, decimals: 0 })}</dd>
          <dt>{pick({ en: 'Known PD and level of the test', es: 'PD conocida y nivel de la prueba' }, lang)}</dt>
          <dd>{`${formatNumber(s.known_pd, lang, { percent: true, decimals: 2 })}, ${formatNumber(s.alpha, lang, { percent: true, decimals: 0 })}`}</dd>
        </dl>
      </PlotCard>
    </>
  );
}
