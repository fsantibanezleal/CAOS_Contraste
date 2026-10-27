// C10's Fit group: the Vasicek distribution fitted to the yearly loss rates of the fit window with the years of both
// windows placed in it, the profile likelihood of the asset correlation with the two estimators, the tail back-test of
// the evaluation years against the fitted quantiles, and the comparison with the IRB correlation and capital. Each draws
// what the c10-outputs document carries; a year without a rate is a gap with its reason, never a zero.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { LIGHT_TEXT } from '../../lib/policy';
import { ChartOverTable, alignTo, unionX } from '../c06/format';
import { Pending } from '../Pending';
import { noteText } from '../c08/notes';
import { barMin } from './format';
import { useCard } from '../c03/U6Shared';
import { C10TestsTable } from './C10Common';
import { DENSITY_TITLE, ESTIMATOR_TEXT, LIKELIHOOD_TITLE, MARK_SHORT, cutoffLabel, INTERVAL_TEXT, IRB_CLASS_TEXT, REGIME_TEXT, levelBi, outputsOf, text, type C10Sel } from './selection';

const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });
const NA = (lang: 'en' | 'es') => formatNumber(null, lang);

/** The fitted density with the years of the series placed in it: the fit years grey, the evaluation years amber. */
export function FittedView({ sel }: { sel: C10Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const fd = o.fitted_distribution;
  const rated = o.annual_rates.filter((a) => a.loss_rate !== null);
  const grid = unionX(fd.curve.x, rated.map((a) => a.loss_rate as number));
  const line = alignTo(fd.curve.x, fd.curve.pdf, grid);
  // a year past either end of the drawn curve keeps its place on the end of the curve, never off the chart
  const clamp = (x: number, i: number) => line[i] ?? (x < fd.curve.x[0] ? fd.curve.pdf[0] : fd.curve.pdf[fd.curve.pdf.length - 1]);
  const placed = (win: 'fit' | 'evaluation') => grid.map((x, i) => (rated.some((a) => a.window === win && a.loss_rate === x) ? clamp(x, i) : null));
  const yearsAt = (x: number) => rated.filter((a) => a.loss_rate === x);
  const marks = fd.quantiles
    .filter((q) => q.level >= 0.95)
    .map((q) => ({ x: q.value, label: { en: `${levelBi(q.level).en} quantile`, es: `Cuantil ${levelBi(q.level).es}` } }));
  const readout = (i: number) => {
    const ys = yearsAt(grid[i]);
    if (ys.length === 0) return `${formatNumber(grid[i], lang, { percent: true, decimals: 2 })}`;
    return ys.map((a) => `${a.year} (${pick(a.window === 'fit' ? { en: 'fit', es: 'ajuste' } : { en: 'evaluation', es: 'evaluación' }, lang)}): ${formatNumber(a.loss_rate, lang, { percent: true, decimals: 2 })}${a.fitted_cdf !== null ? `, ${pick({ en: 'fitted distribution function', es: 'función de distribución ajustada' }, lang)} ${formatNumber(a.fitted_cdf, lang, { percent: true, decimals: 2 })}` : ''}`).join('; ');
  };
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The fitted distribution and the years in it', es: 'La distribución ajustada y los años en ella' }}
        {...card}
        note={{
          en: `The Vasicek distribution of the yearly loss rate fitted by maximum likelihood on ${o.windows.fit.first_year} to ${o.windows.fit.last_year}, with its 95 %, 99 % and 99.9 % quantiles. Each year of the series is a point on the curve: grey for the fit window, amber for the evaluation window ${o.windows.evaluation.first_year} to ${o.windows.evaluation.last_year}, which the fit never saw. A year the table lacks has no point and says why below.`,
          es: `La distribución de Vasicek de la tasa de pérdida anual ajustada por máxima verosimilitud en ${o.windows.fit.first_year} a ${o.windows.fit.last_year}, con sus cuantiles del 95 %, 99 % y 99,9 %. Cada año de la serie es un punto en la curva: gris para la ventana de ajuste, ámbar para la ventana de evaluación ${o.windows.evaluation.first_year} a ${o.windows.evaluation.last_year}, que el ajuste nunca vio. Un año que la tabla no tiene no lleva punto y dice por qué abajo.`,
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: grid, label: { en: 'Yearly loss rate', es: 'Tasa de pérdida anual' }, format: { percent: true, decimals: 1 } }}
              y={{ label: DENSITY_TITLE, format: { decimals: 0 } }}
              series={[
                { label: { en: 'Fitted Vasicek density', es: 'Densidad de Vasicek ajustada' }, values: line, color: '--color-accent', width: 2.4 },
                { label: { en: 'Fit-window years', es: 'Años de la ventana de ajuste' }, values: placed('fit'), color: '--color-fg-subtle', mode: 'points', size: 8 },
                { label: { en: 'Evaluation-window years', es: 'Años de la ventana de evaluación' }, values: placed('evaluation'), color: '--color-warn', mode: 'points', size: 11 },
              ]}
              marks={marks}
              readout={readout}
            />
          }
        >
          <p className="ct-note" data-fit="summary">
            {pick(
              {
                en: `Fitted probability of default ${formatNumber(fd.pd, 'en', { percent: true, decimals: 2 })}, asset correlation ${formatNumber(fd.rho, 'en', { percent: true, decimals: 1 })}; ${count(o.fit.n_years_used, 'en')} years of the fit window carry a rate.`,
                es: `Probabilidad de incumplimiento ajustada ${formatNumber(fd.pd, 'es', { percent: true, decimals: 2 })}, correlación de activos ${formatNumber(fd.rho, 'es', { percent: true, decimals: 1 })}; ${count(o.fit.n_years_used, 'es')} años de la ventana de ajuste traen una tasa.`,
              },
              lang,
            )}
          </p>
          <table className="caos-table ct-wrap-head" data-table="c10-years">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Year', es: 'Año' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Window', es: 'Ventana' }, lang)}</th>
                <th>{pick({ en: 'Loss rate', es: 'Tasa de pérdida' }, lang)}</th>
                <th>{pick({ en: 'Fitted distribution function', es: 'Función de distribución ajustada' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Implied factor', es: 'Factor implícito' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Above 99 %', es: 'Sobre el 99 %' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Above 99.9 %', es: 'Sobre el 99,9 %' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.annual_rates.map((a) => {
                const yes = pick({ en: 'yes', es: 'sí' }, lang);
                const no = pick({ en: 'no', es: 'no' }, lang);
                return a.loss_rate === null ? (
                  <tr key={a.year} data-year={a.year} data-window={a.window} data-state="no-rate">
                    <td className="ct-text">{a.year}</td>
                    <td className="ct-text">{pick(a.window === 'fit' ? { en: 'fit', es: 'ajuste' } : { en: 'evaluation', es: 'evaluación' }, lang)}</td>
                    <td data-na="true" colSpan={5} className="ct-text">{`${NA(lang)} (${noteText(a.reason, lang)})`}</td>
                  </tr>
                ) : (
                  <tr key={a.year} data-year={a.year} data-window={a.window} data-exceeds-99={String(a.exceeds_99)} data-exceeds-999={String(a.exceeds_999)}>
                    <td className="ct-text">{a.year}</td>
                    <td className="ct-text">{pick(a.window === 'fit' ? { en: 'fit', es: 'ajuste' } : { en: 'evaluation', es: 'evaluación' }, lang)}</td>
                    <td>{formatNumber(a.loss_rate, lang, { percent: true, decimals: 2 })}</td>
                    <td>{formatNumber(a.fitted_cdf, lang, { percent: true, decimals: 2 })}</td>
                    <td className="ct-wide-only">{formatNumber(a.implied_factor, lang, { digits: 3 })}</td>
                    <td className="ct-text">{a.exceeds_99 ? yes : no}</td>
                    <td className="ct-text">{a.exceeds_999 ? yes : no}</td>
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

/** The profile likelihood of the asset correlation and the two estimators with their intervals. */
export function CorrelationView({ sel }: { sel: C10Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const p = o.profile_likelihood;
  const ml = o.fit.maximum_likelihood;
  const mo = o.fit.moments;
  const rows = [
    { id: 'maximum-likelihood', pd: ml.pd, rho: ml.rho, method: ml.interval_method, extra: pick({ en: `log-likelihood ${formatNumber(ml.log_likelihood, 'en', { digits: 4 })}, ${ml.converged ? 'converged' : 'did not converge'}`, es: `log-verosimilitud ${formatNumber(ml.log_likelihood, 'es', { digits: 4 })}, ${ml.converged ? 'convergió' : 'no convergió'}` }, lang) },
    { id: 'moments', pd: mo.pd, rho: mo.rho, method: mo.interval_method, extra: pick({ en: `${count(mo.n_bootstrap, 'en')} bootstrap samples`, es: `${count(mo.n_bootstrap, 'es')} muestras de remuestreo` }, lang) },
  ];
  const marks = rows.map((r) => ({ x: r.rho.estimate, label: { en: `${text(MARK_SHORT, r.id).en} ${formatNumber(r.rho.estimate, 'en', { percent: true, decimals: 1 })}`, es: `${text(MARK_SHORT, r.id).es} ${formatNumber(r.rho.estimate, 'es', { percent: true, decimals: 1 })}` } }));
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'How sure the fitted correlation is', es: 'Qué tan segura es la correlación ajustada' }}
        {...card}
        note={{
          en: `The log-likelihood of the yearly loss rates as the asset correlation moves, the probability of default re-optimised at each value. The correlation is as uncertain as the curve is flat: the 95 % interval holds every value above the dashed cutoff. With ${count(o.fit.n_years_used, 'en')} years the interval is wide.`,
          es: `La log-verosimilitud de las tasas de pérdida anuales al mover la correlación de activos, con la probabilidad de incumplimiento re-optimizada en cada valor. La correlación es tan incierta como plana es la curva: el intervalo del 95 % contiene todo valor sobre el corte punteado. Con ${count(o.fit.n_years_used, 'es')} años el intervalo es ancho.`,
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: p.rho, label: { en: 'Asset correlation', es: 'Correlación de activos' }, format: { percent: true, decimals: 0 } }}
              y={{ label: LIKELIHOOD_TITLE, format: { decimals: 0 } }}
              series={[{ label: { en: 'Profile log-likelihood', es: 'Log-verosimilitud perfilada' }, values: p.log_likelihood, color: '--color-accent', width: 2.4 }]}
              yMarks={[{ y: p.cutoff, label: { en: cutoffLabel(formatNumber(p.cutoff, 'en', { digits: 4 }), 'en'), es: cutoffLabel(formatNumber(p.cutoff, 'es', { digits: 4 }), 'es') }, tone: 'warn' }]}
              marks={marks}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c10-estimators">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Estimator', es: 'Estimador' }, lang)}</th>
                <th>{pick({ en: 'Correlation', es: 'Correlación' }, lang)}</th>
                <th>{pick({ en: 'Interval of the correlation', es: 'Intervalo de la correlación' }, lang)}</th>
                <th>{pick({ en: 'Probability of default', es: 'Probabilidad de incumplimiento' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Interval of the PD', es: 'Intervalo de la PD' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Interval method', es: 'Método del intervalo' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Detail', es: 'Detalle' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} data-estimator={r.id} className={r.id === sel.estimator ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(text(ESTIMATOR_TEXT, r.id), lang)}</td>
                  <td>{formatNumber(r.rho.estimate, lang, { percent: true, decimals: 1 })}</td>
                  <td>{`${formatNumber(r.rho.ci_low, lang, { percent: true, decimals: 1 })} ${pick({ en: 'to', es: 'a' }, lang)} ${formatNumber(r.rho.ci_high, lang, { percent: true, decimals: 1 })}`}</td>
                  <td>{formatNumber(r.pd.estimate, lang, { percent: true, decimals: 2 })}</td>
                  <td className="ct-wide-only">{`${formatNumber(r.pd.ci_low, lang, { percent: true, decimals: 2 })} ${pick({ en: 'to', es: 'a' }, lang)} ${formatNumber(r.pd.ci_high, lang, { percent: true, decimals: 2 })}`}</td>
                  <td className="ct-text">{pick(text(INTERVAL_TEXT, r.method), lang)}</td>
                  <td className="ct-text ct-wide-only">{r.extra}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="ct-note" data-profile="cutoff">
            {pick(
              {
                en: `Cutoff ${formatNumber(p.cutoff, 'en', { digits: 4 })} is the maximum ${formatNumber(p.max_log_likelihood, 'en', { digits: 4 })} less half the chi-square quantile with one degree of freedom at ${formatNumber(p.level, 'en', { percent: true, decimals: 0 })}.`,
                es: `El corte ${formatNumber(p.cutoff, 'es', { digits: 4 })} es el máximo ${formatNumber(p.max_log_likelihood, 'es', { digits: 4 })} menos la mitad del cuantil de la chi cuadrado con un grado de libertad al ${formatNumber(p.level, 'es', { percent: true, decimals: 0 })}.`,
              },
              lang,
            )}
          </p>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

const LIGHT_TONE = { green: 'good', amber: 'warn', red: 'bad', not_evaluated: 'neutral', error: 'bad' } as const;

/** The evaluation years against the quantiles fitted on the fit window: expected and observed years above each. */
export function BacktestView({ sel }: { sel: C10Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const b = o.backtest;
  const data = b.rows.flatMap((r) => {
    const lv = levelBi(r.level);
    return [
      { id: `exp-${r.level}`, label: { en: `${lv.en} quantile, expected`, es: `Cuantil ${lv.es}, esperados` } as BiText, value: r.expected_exceedances, tone: 'neutral' as const },
      { id: `obs-${r.level}`, label: { en: `${lv.en} quantile, observed`, es: `Cuantil ${lv.es}, observados` } as BiText, value: r.observed_exceedances, tone: LIGHT_TONE[r.light] },
    ];
  });
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Did the crisis years fall where the fit said', es: 'Si los años de crisis cayeron donde dijo el ajuste' }}
        {...card}
        note={{
          en: `The fit saw ${o.windows.fit.first_year} to ${o.windows.fit.last_year}. Of the ${count(b.n_years_evaluated, 'en')} evaluation years, a fitted quantile at level q should be exceeded in n times (1 - q) of them. Grey is the expected number of years, the colour of the observed one is the light of the binomial tail probability. Few years give the test little power: read the p-value beside the counts.`,
          es: `El ajuste vio ${o.windows.fit.first_year} a ${o.windows.fit.last_year}. De los ${count(b.n_years_evaluated, 'es')} años de evaluación, un cuantil ajustado de nivel q debería ser superado en n veces (1 - q) de ellos. El gris es el número esperado de años, el color del observado es la luz de la probabilidad de cola binomial. Pocos años dan poca potencia a la prueba: lea el valor p junto a los conteos.`,
        }}
      >
        <ChartOverTable
          chartMin={barMin(data.length)}
          chart={<BarChart title={{ en: 'Evaluation years above each fitted quantile', es: 'Años de evaluación sobre cada cuantil ajustado' }} height="fill" orientation="horizontal" data={data} axis={{ label: { en: 'Number of years', es: 'Número de años' }, format: { digits: 3 } }} />}
        >
          <table className="caos-table ct-wrap-head" data-table="c10-backtest">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Level', es: 'Nivel' }, lang)}</th>
                <th>{pick({ en: 'Fitted quantile', es: 'Cuantil ajustado' }, lang)}</th>
                <th>{pick({ en: 'Years expected above', es: 'Años esperados sobre él' }, lang)}</th>
                <th>{pick({ en: 'Years observed above', es: 'Años observados sobre él' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Which years', es: 'Cuáles años' }, lang)}</th>
                <th>{pick({ en: 'p-value, upper tail', es: 'Valor p, cola superior' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Light', es: 'Luz' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {b.rows.map((r) => (
                <tr key={r.level} data-level={r.level} data-light={r.light} className={r.level === sel.level ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(levelBi(r.level), lang)}</td>
                  <td>{formatNumber(r.fitted_quantile, lang, { percent: true, decimals: 2 })}</td>
                  <td>{formatNumber(r.expected_exceedances, lang, { digits: 3 })}</td>
                  <td>{count(r.observed_exceedances, lang)}</td>
                  <td className="ct-text ct-wide-only">{r.years_exceeding.length ? r.years_exceeding.join(', ') : pick({ en: 'none', es: 'ninguno' }, lang)}</td>
                  <td>{formatNumber(r.p_value_upper, lang, { digits: 3 })}</td>
                  <td className={`ct-text ct-light ct-light-${r.light}`}>
                    <span className="ct-light-word">{pick(LIGHT_TEXT[r.light], lang)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <C10TestsTable variant={sel.data.variant} only={(t) => t.test_id === 'portfolio.tail_backtest'} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The fitted correlation and capital against the IRB ones of the loan type's regulatory class. */
export function IrbView({ sel }: { sel: C10Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const x = o.irb_reference;
  const retail = x.maturity === null || x.maturity === undefined;
  const pc = (v: number, d = 2) => formatNumber(v, lang, { percent: true, decimals: d });
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The fitted correlation against the IRB correlation', es: 'La correlación ajustada contra la correlación IRB' }}
        {...card}
        note={{
          en: 'Capital per unit of exposure at 99.9 %: the IRB requirement of the loan type\'s regulatory class, and the large-homogeneous-portfolio capital with the fitted correlation, with the same loss given default, probability of default and maturity treatment on both sides, so the ratio isolates the correlation.',
          es: 'Capital por unidad de exposición al 99,9 %: el requerimiento IRB de la clase regulatoria del tipo de crédito, y el capital de cartera homogénea grande con la correlación ajustada, con la misma pérdida dado el incumplimiento, probabilidad de incumplimiento y tratamiento del plazo en ambos lados, de modo que la razón aísla la correlación.',
        }}
      >
        <ChartOverTable
          chartMin="9rem"
          chart={
            <BarChart
              title={{ en: 'Capital per unit of exposure', es: 'Capital por unidad de exposición' }}
              height="fill"
              orientation="horizontal"
              data={[
                { id: 'irb', label: { en: 'IRB requirement', es: 'Requerimiento IRB' }, value: x.k_irb, tone: 'neutral' as const },
                { id: 'fitted', label: { en: 'LHP at the fitted correlation', es: 'LHP con la correlación ajustada' }, value: x.ec_lhp_fitted, tone: 'accent' as const },
              ]}
              axis={{ label: { en: 'Share of exposure at default', es: 'Parte de la exposición al incumplimiento' }, format: { percent: true, decimals: 2 } }}
            />
          }
        >
          <dl className="ct-defs" data-table="c10-irb">
            <dt>{pick({ en: 'Regime and reference', es: 'Régimen y referencia' }, lang)}</dt>
            <dd>{`${pick(text(REGIME_TEXT, x.regime), lang)}, `}<span translate="no">{x.reference}</span></dd>
            <dt>{pick({ en: 'Regulatory class', es: 'Clase regulatoria' }, lang)}</dt>
            <dd>{pick(text(IRB_CLASS_TEXT, x.asset_class), lang)}</dd>
            <dt>{pick({ en: 'Probability of default and loss given default', es: 'Probabilidad de incumplimiento y pérdida dado el incumplimiento' }, lang)}</dt>
            <dd>{`${pc(x.pd)}, ${pc(x.lgd, 0)}`}</dd>
            <dt>{pick({ en: 'Maturity', es: 'Plazo' }, lang)}</dt>
            <dd data-maturity={retail ? 'none' : String(x.maturity)}>
              {retail
                ? pick({ en: 'none: a retail class has no maturity adjustment', es: 'ninguno: una clase minorista no tiene ajuste por plazo' }, lang)
                : `${formatNumber(x.maturity, lang, { digits: 3 })} ${pick({ en: 'years', es: 'años' }, lang)}, ${pick({ en: 'adjustment', es: 'ajuste' }, lang)} ${formatNumber(x.maturity_adjustment, lang, { digits: 4 })}`}
            </dd>
            <dt>{pick({ en: 'IRB correlation', es: 'Correlación IRB' }, lang)}</dt>
            <dd>{pc(x.irb_correlation, 1)}</dd>
            <dt>{pick({ en: 'Fitted correlation', es: 'Correlación ajustada' }, lang)}</dt>
            <dd>{pc(x.fitted_correlation, 1)}</dd>
            <dt>{pick({ en: 'IRB capital requirement', es: 'Requerimiento de capital IRB' }, lang)}</dt>
            <dd>{pc(x.k_irb)}</dd>
            <dt>{pick({ en: 'LHP capital at the fitted correlation', es: 'Capital LHP con la correlación ajustada' }, lang)}</dt>
            <dd>{pc(x.ec_lhp_fitted)}</dd>
            <dt>{pick({ en: 'Fitted over IRB', es: 'Ajustado sobre IRB' }, lang)}</dt>
            <dd>{formatNumber(x.ratio_fitted_to_irb, lang, { digits: 3 })}</dd>
          </dl>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
