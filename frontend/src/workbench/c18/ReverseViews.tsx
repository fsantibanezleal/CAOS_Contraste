// C18's reverse-stress group: the most plausible scenario that breaks the bank. The scenario is the minimum Mahalanobis
// distance point of the loss threshold under the covariance of the standardised satellite regressors of 1985 to 2019, with its
// plausibility (the chi-square tail probability of its distance). The failure point, the Chilean legal minimum stack of the
// CET1, and the whole formulation are Contraste's, not regulatory text, and the views say so. Nothing is solved here: the
// solution, the starts and the checks are the bake's.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { ChartOverTable, MaybeNumber } from '../c06/format';
import { useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { Defs, NOT_REVERSE, PCT, UnavailableCard, cell, digits } from './C18Common';
import { MONEY_UNIT, amount, reverseOf, type C18Sel } from './selection';

const METHOD_TEXT: Record<string, BiText> = {
  'closed-form-linear': { en: 'closed form, linear loss', es: 'forma cerrada, pérdida lineal' },
  'scipy-optimize': { en: 'numerical optimisation', es: 'optimización numérica' },
};

/** The solved scenario, factor by factor, with its distance, its plausibility and the failure point it reaches. */
export function ReverseSolutionView({ sel }: { sel: C18Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const r = reverseOf(sel);
  const title: BiText = { en: 'The reverse stress scenario', es: 'El escenario del estrés inverso' };
  if (!sel) return <Pending />;
  if (!r) return <UnavailableCard sel={sel} title={title} reason={NOT_REVERSE} />;
  const f = r.failure_point;
  const s = r.solution;
  const fs = r.factor_space;
  const lm = r.loss_model;
  const unitOf = (i: number) => fs.factors[i].unit;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'The failure point is the CET1 reaching the Chilean legal minimum stack at the end of the three years; the scenario is the point of least Mahalanobis distance from the baseline that gets there, under the covariance of the satellite regressors of 1985 to 2019, a US-calibrated adaptation. The formulation is Contraste\'s, not regulatory text. The bars give each factor of the scenario in standard deviations.',
          es: 'El punto de falla es el CET1 llegando al mínimo legal apilado chileno al final de los tres años; el escenario es el punto de menor distancia de Mahalanobis a la línea base que llega ahí, bajo la covarianza de los regresores de los satélites de 1985 a 2019, una adaptación calibrada en EE. UU. La formulación es de Contraste, no texto regulatorio. Las barras dan cada factor del escenario en desviaciones estándar.',
        }}
      >
        <ChartOverTable
          chartMin={`${fs.factors.length * 2.4 + 4}rem`}
          chart={
            <BarChart
              title={{ en: 'The solved scenario in standard deviations of each factor', es: 'El escenario resuelto en desviaciones estándar de cada factor' }}
              height="fill"
              orientation="horizontal"
              data={fs.factors.map((x, i) => ({ id: x.id, label: x.label, value: s.z_star[i], tone: 'accent' as const, highlight: i === sel.factor }))}
              axis={{ label: { en: 'Deviation from the baseline, in standard deviations', es: 'Desviación de la línea base, en desviaciones estándar' }, format: { digits: 4 } }}
            />
          }
        >
          <Defs data-table="c18-failure" data-failure-point={f.label}>
            <dt>{pick({ en: 'Status', es: 'Estado' }, lang)}</dt>
            <dd>{pick({ en: 'Contraste\'s own formulation, not regulatory text.', es: 'Formulación propia de Contraste, no texto regulatorio.' }, lang)}</dd>
            <dt>{pick({ en: 'Failure point', es: 'Punto de falla' }, lang)}</dt>
            <dd>{pick(f.definition, lang)}</dd>
            <dt>{pick({ en: 'Legal minimum stack of the CET1', es: 'Mínimo legal apilado de CET1' }, lang)}</dt>
            <dd data-stack-total={f.stack.total}>{`${PCT(f.stack.total, lang, 3)}: CET1 ${PCT(f.stack.cet1_min, lang)} + ${pick({ en: 'conservation', es: 'conservación' }, lang)} ${PCT(f.stack.c_ccob, lang)} + ${pick({ en: 'countercyclical', es: 'contracíclico' }, lang)} ${PCT(f.stack.c_ccyb, lang)} + D-SIB ${PCT(f.stack.c_dsib, lang)} + ${pick({ en: 'Pillar 2, CET1 part (case assumption)', es: 'Pilar 2, parte CET1 (supuesto del caso)' }, lang)} ${PCT(f.stack.p2_cet1.value, lang, 3)}`}</dd>
            <dt>{pick({ en: 'From', es: 'Desde' }, lang)}</dt>
            <dd>{`CET1 ${PCT(f.cet1_ratio_start, lang)}; ${pick({ en: 'RWA', es: 'APR' }, lang)} ${cell(f.rwa_clp_m, lang)} ${pick(MONEY_UNIT, lang)}; ${f.horizon_years} ${pick({ en: 'years', es: 'años' }, lang)}`}</dd>
            <dt>{pick({ en: 'Method of the solution', es: 'Método de la solución' }, lang)}</dt>
            <dd data-method={s.method}>{pick(METHOD_TEXT[s.method], lang)}</dd>
            <dt>{pick({ en: 'Mahalanobis distance', es: 'Distancia de Mahalanobis' }, lang)}</dt>
            <dd data-distance={s.mahalanobis_distance}>{formatNumber(s.mahalanobis_distance, lang, { digits: 4 })}</dd>
            <dt>{pick({ en: 'Plausibility', es: 'Plausibilidad' }, lang)}</dt>
            <dd data-tail-probability={s.plausibility.tail_probability}>{`${PCT(s.plausibility.tail_probability, lang)} ${pick({ en: `(chi-square tail with ${s.plausibility.chi_square_df} degrees of freedom: the probability of a scenario at least this far from the baseline)`, es: `(cola chi cuadrado con ${s.plausibility.chi_square_df} grados de libertad: la probabilidad de un escenario al menos así de lejos de la línea base)` }, lang)}`}</dd>
            <dt>{pick({ en: 'Loss model', es: 'Modelo de pérdida' }, lang)}</dt>
            <dd data-loss-model={lm.kind}>{pick(lm.description, lang)}</dd>
          </Defs>
          <table className="caos-table ct-wrap-head" data-table="c18-reverse-factors">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Factor', es: 'Factor' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Unit', es: 'Unidad' }, lang)}</th>
                <th>{pick({ en: 'Spread', es: 'Dispersión' }, lang)}</th>
                <th>{pick({ en: 'Solved shock', es: 'Choque resuelto' }, lang)}</th>
                <th>{pick({ en: 'In standard deviations', es: 'En desviaciones estándar' }, lang)}</th>
                <th>{pick({ en: 'Loss per unit', es: 'Pérdida por unidad' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {fs.factors.map((x, i) => {
                const g = lm.gradient_clp_m_per_unit?.[i] ?? null;
                const a = amount(g);
                return (
                  <tr key={x.id} data-factor={x.id} className={i === sel.factor ? 'ct-current' : undefined}>
                    <td className="ct-text">{pick(x.label, lang)}</td>
                    <td className="ct-text ct-wide-only">{unitOf(i)}</td>
                    <td>{formatNumber(x.sd, lang, { digits: 4 })}</td>
                    <td>{formatNumber(s.x_star[i], lang, { digits: 4 })}</td>
                    <td>{formatNumber(s.z_star[i], lang, { digits: 4 })}</td>
                    <td data-na={g === null ? 'true' : undefined}>
                      <MaybeNumber value={a.value} reason={g === null ? pick({ en: 'the loss model is nonlinear, so it has no single gradient', es: 'el modelo de pérdida es no lineal, así que no tiene un único gradiente' }, lang) : null} format={(v) => `${formatNumber(v, lang, { digits: 4 })} ${pick(a.unit, lang)}`} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head" data-table="c18-reverse-covariance">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Covariance of the factors, 1985 to 2019', es: 'Covarianza de los factores, 1985 a 2019' }, lang)}</th>
                {fs.factors.map((x) => (
                  <th key={x.id}>{pick(x.label, lang)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {fs.covariance.map((row, i) => (
                <tr key={fs.factors[i].id}>
                  <td className="ct-text">{pick(fs.factors[i].label, lang)}</td>
                  {row.map((v, j) => (
                    <td key={fs.factors[j].id}>{formatNumber(v, lang, { digits: 4 })}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The search for the scenario: every start, whether it converged, and the check that the loss at the solution equals the threshold. */
export function ReverseSearchView({ sel }: { sel: C18Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const r = reverseOf(sel);
  const title: BiText = { en: 'The search and its check', es: 'La búsqueda y su verificación' };
  if (!sel) return <Pending />;
  if (!r) return <UnavailableCard sel={sel} title={title} reason={NOT_REVERSE} />;
  const s = r.solution;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'The search starts from several points. The solution holds when the loss at the solved scenario equals the threshold within the tolerance and no start finds a closer scenario that breaks the bank.',
          es: 'La búsqueda parte de varios puntos. La solución se sostiene cuando la pérdida en el escenario resuelto iguala el umbral dentro de la tolerancia y ningún inicio encuentra un escenario más cercano que quiebre al banco.',
        }}
      >
        <ChartOverTable
          chartMin={`${r.starts.length * 2.4 + 4}rem`}
          chart={
            <BarChart
              title={{ en: 'Distance reached from each start', es: 'Distancia alcanzada desde cada inicio' }}
              height="fill"
              orientation="horizontal"
              data={r.starts.map((x, i) => ({ id: x.start_id, label: { en: `Start ${i + 1}`, es: `Inicio ${i + 1}` }, value: x.converged ? x.distance : null, tone: 'accent' as const, highlight: x.start_id === sel.start }))}
              axis={{ label: { en: 'Mahalanobis distance of the scenario found', es: 'Distancia de Mahalanobis del escenario hallado' }, format: { digits: 4 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c18-starts">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Start', es: 'Inicio' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Converged', es: 'Convergió' }, lang)}</th>
                <th>{pick({ en: 'Distance', es: 'Distancia' }, lang)}</th>
                <th>{pick({ en: `Loss (${pick(MONEY_UNIT, 'en')})`, es: `Pérdida (${pick(MONEY_UNIT, 'es')})` }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {r.starts.map((x, i) => (
                <tr key={x.start_id} data-start={x.start_id} data-converged={String(x.converged)} className={x.start_id === sel.start ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick({ en: `Start ${i + 1}`, es: `Inicio ${i + 1}` }, lang)}</td>
                  <td className="ct-text">{x.converged ? pick({ en: 'yes', es: 'sí' }, lang) : pick({ en: 'no', es: 'no' }, lang)}</td>
                  <td>{digits(x.distance, lang)}</td>
                  <td>{cell(x.loss_clp_m, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Defs data-table="c18-solution-check">
            <dt>{pick({ en: 'Loss threshold', es: 'Umbral de pérdida' }, lang)}</dt>
            <dd>{`${cell(s.loss_threshold_clp_m, lang)} ${pick(MONEY_UNIT, lang)}`}</dd>
            <dt>{pick({ en: 'Loss at the solved scenario', es: 'Pérdida en el escenario resuelto' }, lang)}</dt>
            <dd>{`${cell(s.loss_at_z_star_clp_m, lang)} ${pick(MONEY_UNIT, lang)}`}</dd>
            <dt>{pick({ en: 'Relative gap and tolerance', es: 'Brecha relativa y tolerancia' }, lang)}</dt>
            <dd>{`${formatNumber(s.relative_gap, lang, { digits: 4 })} ${pick({ en: 'for a tolerance of', es: 'para una tolerancia de' }, lang)} ${formatNumber(s.tolerance, lang, { digits: 4 })}`}</dd>
          </Defs>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
