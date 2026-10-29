// C17's Model group: the ladder of operational risk methods as the models artifact specifies it (the severity law, the
// truncation, the aggregation, the status) beside how often each rung underestimates the truth, and the standardised
// approach of OPE25 as specified (the marginal coefficients, the loss component, the discretions, the golden value).
// Each draws what the c17-models and c17-outputs documents carry; a models artifact that carries no fit says so.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { ChartOverTable } from '../c06/format';
import { useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { KeyTable, keepDates } from './KeyTable';
import { C17TestsTable } from './Tests';
import { AGGREGATION_TEXT, DISCRETION_TEXT, SEVERITY_TEXT, STATUS_TEXT, capitalOf, isCaution, cellLabel, cellOf, fitOf, outputsOf, rungName, text, whole, type C17Sel } from './selection';
import { es } from './localise';

const pct = (v: number, lang: 'en' | 'es', decimals = 2) => formatNumber(v, lang, { percent: true, decimals });

function Unavailable({ sel, title }: { sel: C17Sel; title: { en: string; es: string } }) {
  const lang = useShellLang();
  const card = useCard(sel.data.variant);
  return (
    <ViewsRow>
      <PlotCard fill title={title} {...card}>
        <p className="ct-note" data-state="unavailable">{pick({ en: 'Not available: the models artifact carries no fit.', es: 'No disponible: el artefacto de modelos no trae el ajuste.' }, lang)}</p>
      </PlotCard>
    </ViewsRow>
  );
}

/** The six rungs of the ladder with their specification, and the share of histories each one underestimates the truth in. */
export function LadderView({ sel }: { sel: C17Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const fit = fitOf(sel);
  const title = { en: 'The ladder of methods', es: 'La escalera de métodos' };
  if (!fit) return <Unavailable sel={sel} title={title} />;
  const cell = cellOf(o, sel.years, sel.threshold);
  const label = cellLabel(cell.years, cell.collection_threshold_eur);
  const data = fit.ladder.map((r) => ({
    id: r.rung_id,
    label: rungName(r.rung_id),
    value: capitalOf(cell, r.rung_id).summary?.share_underestimating ?? null,
    tone: isCaution(r.status) ? ('warn' as const) : ('accent' as const),
    highlight: r.rung_id === sel.rung,
  }));
  const a = fit.aggregation;
  const g = cell.aggregation_agreement;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'Rung 1 fits a lognormal and ignores that losses under the collection threshold are not recorded; rung 2 fits the truncated severity and rescales the frequency; rung 3 splices a lognormal body with a generalised Pareto tail; rung 4 is the closed-form single loss approximation, and rung 5 its mean-corrected form, UNVERIFIED; rung 6 combines scenario points with the losses; rungs 7 to 10 (S-3) apply the mean-adjusted single loss approximation to a generalised Pareto fitted by maximum likelihood, by minimum Cramer-von Mises distance and by the optimally bias-robust estimator, and to a lognormal fitted by Cramer-von Mises as the control. The bars give the share of histories whose capital falls below the true quantile.',
          es: 'El peldaño 1 ajusta una lognormal e ignora que las pérdidas bajo el umbral de recolección no se registran; el 2 ajusta la severidad truncada y reescala la frecuencia; el 3 empalma un cuerpo lognormal con una cola de Pareto generalizada; el 4 es la aproximación de una pérdida en forma cerrada, y el 5 su forma corregida por la media, SIN VERIFICAR; el 6 combina puntos de escenario con las pérdidas; los peldaños 7 a 10 (S-3) aplican la aproximación de una pérdida con ajuste por media a una Pareto generalizada ajustada por máxima verosimilitud, por distancia mínima de Cramér-von Mises y por el estimador óptimamente robusto al sesgo, y a una lognormal ajustada por Cramér-von Mises como control. Las barras dan la proporción de historias cuyo capital cae bajo el cuantil verdadero.',
        }}
      >
        <ChartOverTable
          chartMin={`${data.length * 2.5 + 3}rem`}
          chart={
            <BarChart
              title={{ en: `Share of histories below the true quantile, ${label.en}`, es: `Proporción de historias bajo el cuantil verdadero, ${label.es}` }}
              height="fill"
              orientation="horizontal"
              data={data}
              axis={{ label: { en: 'Share of histories that underestimate', es: 'Proporción de historias que subestiman' }, format: { percent: true, decimals: 0 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="ladder">
            <thead>
              <tr>
                <th className="ct-text" style={{ minWidth: '11rem' }}>{pick({ en: 'Method', es: 'Método' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Severity', es: 'Severidad' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Truncated', es: 'Truncada' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Aggregation', es: 'Agregación' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Status', es: 'Estado' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Reference', es: 'Referencia' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {fit.ladder.map((r) => (
                <tr key={r.rung_id} data-rung={r.rung_id} data-status={r.status} className={r.rung_id === sel.rung ? 'ct-current' : undefined}>
                  <td className="ct-text" title={pick(rungName(r.rung_id), lang)}>{pick(r.label, lang)}</td>
                  <td className="ct-text ct-wide-only">{pick(text(SEVERITY_TEXT, r.severity_law), lang)}</td>
                  <td className="ct-text ct-wide-only">{r.truncated ? pick({ en: 'yes', es: 'sí' }, lang) : pick({ en: 'no', es: 'no' }, lang)}</td>
                  <td className="ct-text">{pick(text(AGGREGATION_TEXT, r.aggregation), lang)}</td>
                  <td className="ct-text">{pick(text(STATUS_TEXT, r.status), lang)}</td>
                  <td className="ct-text ct-wide-only">{es(r.reference, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <KeyTable
            table="aggregation"
            rows={[
              { id: 'panjer', label: { en: 'Panjer recursion', es: 'Recursión de Panjer' }, value: pick({ en: `step ${whole(a.panjer_step_eur, 'en')} EUR, ${whole(a.panjer_points, 'en')} points`, es: `paso de ${whole(a.panjer_step_eur, 'es')} EUR, ${whole(a.panjer_points, 'es')} puntos` }, lang) },
              { id: 'fft', label: { en: 'FFT', es: 'FFT' }, value: pick({ en: `${whole(a.fft_points, 'en')} points, padding factor ${a.fft_padding_factor}, tilt ${formatNumber(a.fft_tilt, 'en', { digits: 3 })}`, es: `${whole(a.fft_points, 'es')} puntos, factor de relleno ${a.fft_padding_factor}, inclinación ${formatNumber(a.fft_tilt, 'es', { digits: 3 })}` }, lang) },
              { id: 'mc', label: { en: 'Monte Carlo', es: 'Monte Carlo' }, value: pick({ en: `${whole(a.mc_years_truth, 'en')} years for the truth, ${whole(a.mc_years_replication, 'en')} per history`, es: `${whole(a.mc_years_truth, 'es')} años para la verdad, ${whole(a.mc_years_replication, 'es')} por historia` }, lang) },
              {
                id: 'agreement',
                label: { en: 'Panjer against FFT in this cell', es: 'Panjer contra FFT en esta celda' },
                attrs: { 'data-agreement': String(g.n_compared) },
                value: pick({ en: `largest relative difference ${formatNumber(g.max_rel_diff_panjer_fft, 'en', { digits: 3 })} over ${whole(g.n_compared, 'en')} fits`, es: `mayor diferencia relativa ${formatNumber(g.max_rel_diff_panjer_fft, 'es', { digits: 3 })} en ${whole(g.n_compared, 'es')} ajustes` }, lang),
              },
            ]}
          />
          <C17TestsTable variant={sel.data.variant} host="ladder" />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The standardised approach of OPE25 as the models artifact specifies it: the coefficients by bucket, the golden value, the discretions. */
export function SmaSpecView({ sel }: { sel: C17Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const fit = fitOf(sel);
  const title = { en: 'The standardised approach as specified', es: 'El enfoque estandarizado como se especifica' };
  if (!fit) return <Unavailable sel={sel} title={title} />;
  const s = fit.sma;
  const bn = (v: number, l: 'en' | 'es') => `EUR ${formatNumber(v / 1e9, l, { digits: 4 })} ${l === 'en' ? 'bn' : 'mil M'}`;
  const data = s.buckets.map((b, i) => {
    const below = i > 0 ? s.buckets[i - 1].upper_eur : null;
    return {
      id: `bucket-${b.bucket}`,
      label: {
        en: b.upper_eur === null ? `Bucket ${b.bucket}: above ${below === null ? 'the limit' : bn(below, 'en')}` : `Bucket ${b.bucket}: up to ${bn(b.upper_eur, 'en')}`,
        es: b.upper_eur === null ? `Tramo ${b.bucket}: sobre ${below === null ? 'el límite' : bn(below, 'es')}` : `Tramo ${b.bucket}: hasta ${bn(b.upper_eur, 'es')}`,
      },
      value: b.coefficient,
      tone: 'accent' as const,
    };
  });
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'OPE25 of the Basel Framework: the capital is the business indicator component, which applies a marginal coefficient to each slice of the business indicator, times the internal loss multiplier, which compares fifteen times the average annual loss of the last ten years with that component. The golden value of the standard is reproduced by the engine.',
          es: 'OPE25 del Marco de Basilea: el capital es el componente del indicador de negocio, que aplica un coeficiente marginal a cada tramo del indicador de negocio, por el multiplicador de pérdidas internas, que compara quince veces la pérdida anual promedio de los últimos diez años con ese componente. El motor reproduce el valor de referencia de la norma.',
        }}
      >
        <ChartOverTable
          chartMin={`${data.length * 2.5 + 3}rem`}
          chart={<BarChart title={{ en: 'Marginal coefficient of the business indicator by bucket', es: 'Coeficiente marginal del indicador de negocio por tramo' }} height="fill" orientation="horizontal" data={data} axis={{ label: { en: 'Marginal coefficient', es: 'Coeficiente marginal' }, format: { percent: true, decimals: 0 } }} />}
        >
          <table className="caos-table ct-wrap-head" data-table="sma-spec">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Bucket', es: 'Tramo' }, lang)}</th>
                <th>{pick({ en: 'Upper limit of BI (EUR)', es: 'Límite superior del BI (EUR)' }, lang)}</th>
                <th>{pick({ en: 'Marginal coefficient', es: 'Coeficiente marginal' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {s.buckets.map((b) => (
                <tr key={b.bucket} data-bucket={b.bucket}>
                  <td className="ct-text">{b.bucket}</td>
                  <td>{b.upper_eur === null ? pick({ en: 'no upper limit', es: 'sin límite superior' }, lang) : whole(b.upper_eur, lang)}</td>
                  <td>{pct(b.coefficient, lang, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <KeyTable
            table="sma-constants"
            rows={[
              { id: 'lc', label: { en: 'Loss component', es: 'Componente de pérdidas' }, value: pick({ en: `${s.loss_multiple} times the average annual loss over ${s.loss_window_years} years; at least ${s.minimum_years} years of data, otherwise the capital is the business indicator component alone`, es: `${s.loss_multiple} veces la pérdida anual promedio en ${s.loss_window_years} años; al menos ${s.minimum_years} años de datos, si no el capital es solo el componente del indicador de negocio` }, lang) },
              { id: 'exponent', label: { en: 'Multiplier exponent', es: 'Exponente del multiplicador' }, value: formatNumber(s.ilm_exponent, lang, { digits: 3 }) },
              { id: 'rwa', label: { en: 'Risk-weighted assets', es: 'Activos ponderados por riesgo' }, value: pick({ en: `${formatNumber(s.rwa_factor, 'en', { digits: 4 })} times the capital`, es: `${formatNumber(s.rwa_factor, 'es', { digits: 4 })} veces el capital` }, lang) },
              { id: 'golden', label: { en: 'Golden value', es: 'Valor de referencia' }, attrs: { 'data-golden': String(s.golden.bic_eur) }, value: pick({ en: `a business indicator of ${whole(s.golden.bi_eur, 'en')} EUR gives a component of ${whole(s.golden.bic_eur, 'en')} EUR (${s.golden.reference})`, es: `un indicador de negocio de ${whole(s.golden.bi_eur, 'es')} EUR da un componente de ${whole(s.golden.bic_eur, 'es')} EUR (${es(s.golden.reference, 'es')})` }, lang) },
              { id: 'reference', label: { en: 'Reference', es: 'Referencia' }, value: keepDates(es(s.reference, lang)) },
            ]}
          />
          <table className="caos-table ct-wrap-head" data-table="sma-discretions">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Discretion', es: 'Discreción' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'What it does', es: 'Qué hace' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Reference', es: 'Referencia' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {s.discretions.map((d) => (
                <tr key={d.id} data-discretion={d.id}>
                  <td className="ct-text">{pick(text(DISCRETION_TEXT, d.id), lang)}</td>
                  <td className="ct-text">{pick(d.description, lang)}</td>
                  <td className="ct-text ct-wide-only">{es(d.reference, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
