// C18's Aggregation group: how the capital of the four risks is added. The headline capital is the simple sum, as the IAPE adds
// it; the band of the ladder (the lower bound, variance-covariance, the Gaussian and Student t copulas, the worst case) shows
// what the dependence assumption hides, and every figure in it that is not the simple sum is labelled information for the
// validator, never capital. The Euler allocation splits the expected shortfall of the aggregate by risk, the marginals show
// where each risk's number comes from, and the aggregation variant adds the stressed matrix, the copula sensitivity and the
// Rosenberg and Schuermann reference, which is a reference and never a gate.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable, MaybeNumber } from '../c06/format';
import { useCard, type Bi } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { HWaterfall, stackRows } from './Waterfall';
import { NOT_AGGREGATION, NOT_AGG_VARIANT, PCT, UnavailableCard, cell, digits, producerText } from './C18Common';
import {
  MONEY_UNIT, NOT_CAPITAL, RISK_ORDER, RISK_TEXT, aggDocOf, aggOf, axisOf, methodShort, methodText, text,
  type C18Sel,
} from './selection';

const MATRIX_TEXT: Record<string, Bi> = {
  correlation_matrix_base: { en: 'Base matrix: Rosenberg and Schuermann, with the IRRBB values as a convention', es: 'Matriz base: Rosenberg y Schuermann, con los valores de IRRBB como convención' },
  correlation_matrix_stress: { en: 'Stress matrix: market-credit raised to 0.8', es: 'Matriz bajo estrés: mercado-crédito elevada a 0,8' },
};

/** The dependence band of the ladder: the simple sum as the headline, every other row as information, with the model risk measures beside it. */
export function BandView({ sel }: { sel: C18Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const a = aggOf(sel);
  const title: BiText = { en: 'The aggregation band', es: 'La banda de agregación' };
  if (!sel) return <Pending />;
  if (!a) return <UnavailableCard sel={sel} title={title} reason={NOT_AGGREGATION} />;
  const scale = axisOf([...a.band.map((b) => b.capital_clp_m), a.headline.capital_clp_m]);
  const mr = a.model_risk;
  const idx = Math.min(sel.row, a.band.length - 1);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: `The capital of the four risks at ${PCT(a.confidence_level, 'en', 1)} and ${a.horizon_years} year, added in six ways over the same marginals. Only the simple sum is the capital of this case: it is how the IAPE adds the risks. Every other bar is information for the validator, never capital, and a bar above the simple sum is shown as it is, because VaR is not subadditive. ${pick(NOT_CAPITAL, 'en')}`,
          es: `El capital de los cuatro riesgos a ${PCT(a.confidence_level, 'es', 1)} y ${a.horizon_years} año, sumado de seis maneras sobre las mismas marginales. Solo la suma simple es el capital de este caso: así suma el IAPE los riesgos. Toda otra barra es información para el validador, nunca capital, y una barra sobre la suma simple se muestra tal cual, porque el VaR no es subaditivo. ${pick(NOT_CAPITAL, 'es')}`,
        }}
      >
        <ChartOverTable
          chartMin={`${a.band.length * 2.3 + 4}rem`}
          chart={
            <BarChart
              title={{ en: 'Capital of the four risks by aggregation method', es: 'Capital de los cuatro riesgos por método de agregación' }}
              height="fill"
              orientation="horizontal"
              data={a.band.map((b, i) => ({
                id: `${b.method}-${b.nu ?? 'x'}`,
                label: methodShort(b),
                value: b.capital_clp_m / scale.div,
                tone: b.status === 'headline-capital' ? ('accent' as const) : b.method === 'worst-case' ? ('warn' as const) : ('neutral' as const),
                highlight: i === idx,
                hint: b.status === 'headline-capital' ? { en: 'The headline capital', es: 'El capital principal' } : NOT_CAPITAL,
              }))}
              axis={{ label: { en: 'Capital at 99.9 percent, one year', es: 'Capital a 99,9 por ciento, un año' }, unit: scale.unit, format: { digits: 4 } }}
            />
          }
        >
          <p className="ct-note" data-headline="simple-sum">
            {`${pick({ en: 'Headline capital, the simple sum', es: 'Capital principal, la suma simple' }, lang)}: ${cell(a.headline.capital_clp_m, lang)} ${pick(MONEY_UNIT, lang)}. ${pick(a.headline.label, lang)}`}
          </p>
          <table className="caos-table ct-wrap-head" data-table="c18-band" data-matrix={a.correlation.name}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Method', es: 'Método' }, lang)}</th>
                <th>{pick({ en: `Capital (${pick(MONEY_UNIT, 'en')})`, es: `Capital (${pick(MONEY_UNIT, 'es')})` }, lang)}</th>
                <th>{pick({ en: 'Over the simple sum', es: 'Sobre la suma simple' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Monte Carlo error', es: 'Error de Monte Carlo' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Status', es: 'Estado' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {a.band.map((b, i) => (
                <tr key={`${b.method}-${b.nu ?? 'x'}`} data-band={b.method} data-nu={b.nu ?? undefined} data-band-status={b.status} data-status={b.status === 'information-not-capital' ? 'information-not-capital' : undefined} className={i === idx ? 'ct-current' : undefined}>
                  <td className="ct-text" title={pick(methodText(b), lang)}>{pick(methodText(b), lang)}</td>
                  <td>{cell(b.capital_clp_m, lang)}</td>
                  <td>{PCT(b.diversification_factor, lang)}</td>
                  <td className="ct-wide-only" data-na={b.mc_se_clp_m === null ? 'true' : undefined}>{b.mc_se_clp_m === null ? formatNumber(null, lang) : cell(b.mc_se_clp_m, lang)}</td>
                  <td className="ct-text">{b.status === 'headline-capital' ? pick({ en: 'headline capital', es: 'capital principal' }, lang) : pick({ en: 'information, not capital', es: 'información, no capital' }, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3 className="ct-sub">{pick({ en: 'Inter-risk correlation', es: 'Correlación entre riesgos' }, lang)}</h3>
          <p className="ct-note">{`${pick(text(MATRIX_TEXT, a.correlation.name), lang)}. ${pick(a.correlation.basis, lang)}`}</p>
          <table className="caos-table ct-wrap-head" data-table="c18-correlation" data-matrix={a.correlation.name}>
            <thead>
              <tr>
                <th className="ct-text" />
                {a.correlation.order.map((r) => (
                  <th key={r}>{pick(text(RISK_TEXT, r), lang)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {a.correlation.matrix.map((row, i) => (
                <tr key={a.correlation.order[i]}>
                  <td className="ct-text">{pick(text(RISK_TEXT, a.correlation.order[i]), lang)}</td>
                  {row.map((v, j) => (
                    <td key={a.correlation.order[j]}>{formatNumber(v, lang, { digits: 4 })}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <h3 className="ct-sub">{pick({ en: 'Model risk of the aggregation', es: 'Riesgo de modelo de la agregación' }, lang)}</h3>
          <p className="ct-note" data-status={mr.status}>{`${pick(NOT_CAPITAL, lang)} ${pick(mr.label, lang)}`}</p>
          <dl className="ct-defs" data-table="c18-model-risk">
            <dt>{pick({ en: 'Reference model', es: 'Modelo de referencia' }, lang)}</dt>
            <dd>{pick(methodText(mr.reference_model), lang)}</dd>
            <dt>{pick({ en: 'Highest, reference and lowest capital of the set', es: 'Mayor capital, de referencia y menor del conjunto' }, lang)}</dt>
            <dd>{`${cell(mr.barrieu_scandolo.rho_max_clp_m, lang)} / ${cell(mr.barrieu_scandolo.rho_x0_clp_m, lang)} / ${cell(mr.barrieu_scandolo.rho_min_clp_m, lang)}`}</dd>
            <dt>{pick({ en: 'Ambiguity measure, Barrieu and Scandolo', es: 'Medida de ambigüedad, Barrieu y Scandolo' }, lang)}</dt>
            <dd data-measure="am">{formatNumber(mr.barrieu_scandolo.am, lang, { digits: 4 })}</dd>
            <dt>{pick({ en: 'Relative measure, from 0 to 1', es: 'Medida relativa, de 0 a 1' }, lang)}</dt>
            <dd data-measure="rm">{formatNumber(mr.barrieu_scandolo.rm, lang, { digits: 4 })}</dd>
            <dt>{pick({ en: 'Worst case by reweighting, Glasserman and Xu', es: 'Peor caso por reponderación, Glasserman y Xu' }, lang)}</dt>
            <dd>{`${cell(mr.glasserman_xu.baseline_clp_m, lang)} ${pick({ en: 'to', es: 'a' }, lang)} ${cell(mr.glasserman_xu.worst_case_clp_m, lang)}; ${pick({ en: 'entropy budget', es: 'presupuesto de entropía' }, lang)} ${formatNumber(mr.glasserman_xu.relative_entropy_budget, lang, { digits: 4 })}; theta ${formatNumber(mr.glasserman_xu.theta, lang, { digits: 4 })}`}</dd>
          </dl>
          <p className="ct-note">{pick(mr.glasserman_xu.quantity, lang)}</p>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The Euler allocation of the expected shortfall of the aggregate, risk by risk, with the diversification benefit of each. */
export function EulerView({ sel }: { sel: C18Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const a = aggOf(sel);
  const title: BiText = { en: 'The Euler allocation', es: 'La asignación de Euler' };
  if (!sel) return <Pending />;
  if (!a) return <UnavailableCard sel={sel} title={title} reason={NOT_AGGREGATION} />;
  const e = a.euler;
  const d = a.diversification;
  const scale = axisOf([e.es_total_clp_m, ...e.allocation.map((x) => x.contribution_clp_m)]);
  const fmt = (v: number) => formatNumber(v / scale.div, lang, { digits: 4 });
  const rows = stackRows(
    e.allocation.map((x) => ({ id: x.risk, label: text(RISK_TEXT, x.risk), size: x.contribution_clp_m, tone: x.risk === sel.risk ? ('--color-warn' as const) : ('--color-accent' as const), value: fmt(x.contribution_clp_m) })),
    { id: 'total', label: { en: 'Aggregate expected shortfall', es: 'Déficit esperado agregado' }, value: fmt(e.es_total_clp_m), tone: '--color-fg' },
  );
  const additive = e.additivity.relative_error <= e.additivity.tolerance;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: `The expected shortfall of the aggregate at ${PCT(e.level, 'en', 1)} under the ${e.copula.family === 'gaussian' ? 'Gaussian' : 'Student t'} copula, split by risk so the parts add up to the whole. ${pick(NOT_CAPITAL, 'en')} The risk in the rail is drawn in orange.`,
          es: `El déficit esperado del agregado a ${PCT(e.level, 'es', 1)} bajo la cópula ${e.copula.family === 'gaussian' ? 'gaussiana' : 't de Student'}, repartido por riesgo para que las partes sumen el total. ${pick(NOT_CAPITAL, 'es')} El riesgo del panel va en naranja.`,
        }}
      >
        <ChartOverTable
          chartMin="16rem"
          chart={
            <HWaterfall
              rows={rows}
              axisLabel={{ en: `Expected shortfall (${pick(scale.unit, 'en')})`, es: `Déficit esperado (${pick(scale.unit, 'es')})` }}
              tickFormat={(v) => formatNumber(v / scale.div, lang, { digits: 4 })}
              ariaLabel={{ en: 'Euler allocation of the expected shortfall by risk', es: 'Asignación de Euler del déficit esperado por riesgo' }}
            />
          }
        >
          <p className="ct-note" data-status={e.status}>{`${pick(NOT_CAPITAL, lang)} ${pick(e.label, lang)}`}</p>
          <table className="caos-table ct-wrap-head" data-table="c18-euler" data-additivity={String(additive)}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Risk', es: 'Riesgo' }, lang)}</th>
                <th>{pick({ en: `Contribution (${pick(MONEY_UNIT, 'en')})`, es: `Contribución (${pick(MONEY_UNIT, 'es')})` }, lang)}</th>
                <th>{pick({ en: 'Share', es: 'Parte' }, lang)}</th>
                <th>{pick({ en: 'Diversification benefit', es: 'Beneficio de diversificación' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {e.allocation.map((x) => (
                <tr key={x.risk} data-bar={x.risk} className={x.risk === sel.risk ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(text(RISK_TEXT, x.risk), lang)}</td>
                  <td>{cell(x.contribution_clp_m, lang)}</td>
                  <td>{PCT(x.share, lang)}</td>
                  <td>{PCT(d.euler_benefit_by_risk.find((b) => b.risk === x.risk)?.benefit ?? null, lang, 3)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr data-total="es">
                <td className="ct-text">{pick({ en: 'Aggregate expected shortfall', es: 'Déficit esperado agregado' }, lang)}</td>
                <td>{cell(e.es_total_clp_m, lang)}</td>
                <td />
                <td />
              </tr>
            </tfoot>
          </table>
          <p className="ct-note" data-additivity={String(additive)}>
            {pick(
              {
                en: `The contributions add up to ${cell(e.additivity.sum_clp_m, 'en')} against the aggregate, a relative error of ${formatNumber(e.additivity.relative_error, 'en', { digits: 4 })} for a tolerance of ${formatNumber(e.additivity.tolerance, 'en', { digits: 4 })}.`,
                es: `Las contribuciones suman ${cell(e.additivity.sum_clp_m, 'es')} frente al agregado, un error relativo de ${formatNumber(e.additivity.relative_error, 'es', { digits: 4 })} para una tolerancia de ${formatNumber(e.additivity.tolerance, 'es', { digits: 4 })}.`,
              },
              lang,
            )}
          </p>
          <p className="ct-note" data-status={d.status}>
            {`${pick(NOT_CAPITAL, lang)} ${pick(d.label, lang)} ${pick({ en: 'Diversification factor', es: 'Factor de diversificación' }, lang)} ${PCT(d.factor, lang)}; ${pick({ en: 'benefit', es: 'beneficio' }, lang)} ${PCT(d.benefit, lang)} (${pick(methodText(d.reference_row), lang)}).`}
          </p>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** Where each risk's number comes from: expected loss, VaR, expected shortfall and capital, with the way it was produced. */
export function MarginalsView({ sel }: { sel: C18Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const a = aggOf(sel);
  const title: BiText = { en: 'The marginals of the four risks', es: 'Las marginales de los cuatro riesgos' };
  if (!sel) return <Pending />;
  if (!a) return <UnavailableCard sel={sel} title={title} reason={NOT_AGGREGATION} />;
  const scale = axisOf([...a.marginals.map((m) => m.ec_clp_m), a.headline.capital_clp_m]);
  const ordered = RISK_ORDER.flatMap((r) => a.marginals.filter((m) => m.risk === r));
  const bars = [
    ...ordered.map((m) => ({ id: m.risk, label: text(RISK_TEXT, m.risk), value: m.ec_clp_m / scale.div, tone: 'accent' as const, highlight: m.risk === sel.risk })),
    { id: 'sum', label: { en: 'Simple sum (headline)', es: 'Suma simple (principal)' } as BiText, value: a.headline.capital_clp_m / scale.div, tone: 'neutral' as const },
  ];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'One horizon and one confidence level across the four risks. The capital of a risk is its VaR less its expected loss; when the mean of a heavy-tailed marginal is infinite the expected loss is undefined and the capital is the VaR alone, which the row says.',
          es: 'Un horizonte y un nivel de confianza en los cuatro riesgos. El capital de un riesgo es su VaR menos su pérdida esperada; cuando la media de una marginal de cola pesada es infinita la pérdida esperada no está definida y el capital es el VaR solo, lo que la fila dice.',
        }}
      >
        <ChartOverTable
          chartMin="17rem"
          chart={
            <BarChart
              title={{ en: 'Capital of each risk and their simple sum', es: 'Capital de cada riesgo y su suma simple' }}
              height="fill"
              orientation="horizontal"
              data={bars}
              axis={{ label: { en: 'Capital at 99.9 percent, one year', es: 'Capital a 99,9 por ciento, un año' }, unit: scale.unit, format: { digits: 4 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c18-marginals">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Risk', es: 'Riesgo' }, lang)}</th>
                <th>{pick({ en: 'Expected loss', es: 'Pérdida esperada' }, lang)}</th>
                <th>{pick({ en: 'VaR', es: 'VaR' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Expected shortfall', es: 'Déficit esperado' }, lang)}</th>
                <th>{pick({ en: 'Capital', es: 'Capital' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'VaR error', es: 'Error del VaR' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {ordered.map((m) => (
                <tr key={m.risk} data-risk={m.risk} data-el-status={m.el_status} className={m.risk === sel.risk ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(text(RISK_TEXT, m.risk), lang)}</td>
                  <td data-na={m.el_clp_m === null ? 'true' : undefined}>
                    <MaybeNumber value={m.el_clp_m} reason={m.ec_label ? pick(m.ec_label, lang) : null} format={(v) => cell(v, lang)} />
                  </td>
                  <td>{cell(m.var_clp_m, lang)}</td>
                  <td className="ct-wide-only">{cell(m.es_clp_m, lang)}</td>
                  <td data-ec-basis={m.ec_basis}>{cell(m.ec_clp_m, lang)}</td>
                  <td className="ct-wide-only" data-na={m.var_se_clp_m === null ? 'true' : undefined}>{m.var_se_clp_m === null ? formatNumber(null, lang) : cell(m.var_se_clp_m, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head" data-table="c18-producers">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Risk', es: 'Riesgo' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'How it is produced and scaled', es: 'Cómo se produce y se escala' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {ordered.map((m) => (
                <tr key={m.risk} data-risk={m.risk}>
                  <td className="ct-text">{pick(text(RISK_TEXT, m.risk), lang)}</td>
                  <td className="ct-text">{`${pick(producerText(m.producer), lang)}. ${pick(m.scaling.statement, lang)}`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The aggregation variant only: the stressed matrix against the base, the copula sensitivity over the degrees of freedom, and the published reference. */
export function SensitivityView({ sel }: { sel: C18Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const doc = aggDocOf(sel);
  const title: BiText = { en: 'Copula choice, correlation stress and the reference', es: 'Elección de cópula, estrés de correlación y la referencia' };
  if (!sel) return <Pending />;
  if (!doc) return <UnavailableCard sel={sel} title={title} reason={NOT_AGG_VARIANT} />;
  const cs = doc.copula_sensitivity;
  const rs = doc.rosenberg_schuermann;
  const base = doc.aggregation;
  const stress = doc.correlation_stress.aggregation;
  const scale = axisOf(cs.flatMap((r) => [r.gaussian_capital_clp_m, r.t_capital_clp_m]));
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'The Gaussian copula against the Student t copula at each degrees-of-freedom value of the convention set, then the base matrix against the one with market-credit raised to 0.8. A capital that falls when a correlation rises is shown as it is. Every figure here is information, not capital.',
          es: 'La cópula gaussiana frente a la cópula t de Student en cada valor de grados de libertad del conjunto convenido, luego la matriz base frente a la de mercado-crédito elevada a 0,8. Un capital que baja cuando sube una correlación se muestra tal cual. Toda cifra aquí es información, no capital.',
        }}
      >
        <ChartOverTable
          chartMin="16rem"
          chart={
            <UPlotChart
              height="fill"
              x={{ values: cs.map((r) => r.nu), label: { en: 'Degrees of freedom of the t copula', es: 'Grados de libertad de la cópula t' }, format: { decimals: 0 } }}
              y={{ label: { en: `Aggregate capital (${pick(scale.unit, 'en')})`, es: `Capital agregado (${pick(scale.unit, 'es')})` }, format: { digits: 4 } }}
              series={[
                { label: { en: 'Gaussian copula', es: 'Cópula gaussiana' }, values: cs.map((r) => r.gaussian_capital_clp_m / scale.div), color: '--color-accent', width: 2.6 },
                { label: { en: 'Student t copula', es: 'Cópula t de Student' }, values: cs.map((r) => r.t_capital_clp_m / scale.div), color: '--color-warn', width: 2.6 },
              ]}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c18-copula-sensitivity">
            <thead>
              <tr>
                <th>{pick({ en: 'Degrees of freedom', es: 'Grados de libertad' }, lang)}</th>
                <th>{pick({ en: 'Gaussian', es: 'Gaussiana' }, lang)}</th>
                <th>{pick({ en: 'Student t', es: 't de Student' }, lang)}</th>
                <th>{pick({ en: 'Relative difference', es: 'Diferencia relativa' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {cs.map((r) => (
                <tr key={r.nu} data-nu={r.nu}>
                  <td>{formatNumber(r.nu, lang, { digits: 4 })}</td>
                  <td>{cell(r.gaussian_capital_clp_m, lang)}</td>
                  <td>{cell(r.t_capital_clp_m, lang)}</td>
                  <td>{PCT(r.relative_difference, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3 className="ct-sub">{pick({ en: 'Base matrix against the stressed matrix', es: 'Matriz base frente a la matriz bajo estrés' }, lang)}</h3>
          <table className="caos-table ct-wrap-head" data-table="c18-correlation-stress" data-pair={`${doc.correlation_stress.pair.a}-${doc.correlation_stress.pair.b}`}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Method', es: 'Método' }, lang)}</th>
                <th>{pick({ en: 'Base matrix', es: 'Matriz base' }, lang)}</th>
                <th>{pick({ en: 'Market-credit 0.8', es: 'Mercado-crédito 0,8' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {base.band.map((b, i) => (
                <tr key={`${b.method}-${b.nu ?? 'x'}`} data-band={b.method} data-nu={b.nu ?? undefined}>
                  <td className="ct-text">{pick(methodText(b), lang)}</td>
                  <td>{cell(b.capital_clp_m, lang)}</td>
                  <td>{cell(stress.band[i]?.capital_clp_m ?? null, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3 className="ct-sub">{pick({ en: 'Rosenberg and Schuermann reference', es: 'Referencia de Rosenberg y Schuermann' }, lang)}</h3>
          <dl className="ct-defs" data-table="c18-rs" data-role={rs.role} data-within-published-range={String(rs.within_published_range)}>
            <dt>{pick({ en: 'Status', es: 'Estado' }, lang)}</dt>
            <dd>{pick({ en: 'A published reference point, not a gate: the case does not pass or fail on it.', es: 'Un punto de referencia publicado, no un umbral: el caso no aprueba ni falla por él.' }, lang)}</dd>
            <dt>{pick({ en: 'Weights of the benchmark bank', es: 'Ponderaciones del banco de referencia' }, lang)}</dt>
            <dd>{`${pick(RISK_TEXT.market, lang)} ${PCT(rs.weights.market, lang, 1)}; ${pick(RISK_TEXT.credit, lang)} ${PCT(rs.weights.credit, lang, 1)}; ${pick(RISK_TEXT.operational, lang)} ${PCT(rs.weights.operational, lang, 1)}`}</dd>
            <dt>{pick({ en: 'Correlations', es: 'Correlaciones' }, lang)}</dt>
            <dd>{`${pick({ en: 'market-credit', es: 'mercado-crédito' }, lang)} ${formatNumber(rs.correlations.market_credit, lang, { digits: 4 })}; ${pick({ en: 'market-operational', es: 'mercado-operacional' }, lang)} ${formatNumber(rs.correlations.market_operational, lang, { digits: 4 })}; ${pick({ en: 'credit-operational', es: 'crédito-operacional' }, lang)} ${formatNumber(rs.correlations.credit_operational, lang, { digits: 4 })}`}</dd>
            <dt>{pick({ en: 'Published overestimate by the additive approximation', es: 'Sobrestimación publicada de la aproximación aditiva' }, lang)}</dt>
            <dd>{`${PCT(rs.published_additive_overestimate.low, lang, 0)} ${pick({ en: 'to', es: 'a' }, lang)} ${PCT(rs.published_additive_overestimate.high, lang, 0)}`}</dd>
            <dt>{pick({ en: 'Overestimate in this case', es: 'Sobrestimación en este caso' }, lang)}</dt>
            <dd>{`${PCT(rs.case_additive_overestimate, lang, 1)} (${rs.within_published_range ? pick({ en: 'inside the published range', es: 'dentro del rango publicado' }, lang) : pick({ en: 'outside the published range', es: 'fuera del rango publicado' }, lang)})`}</dd>
          </dl>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

export { digits };
