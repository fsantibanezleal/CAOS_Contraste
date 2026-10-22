// C08's Severity group: the distribution of the loss given default, with its masses at 0 and 1 and the values outside
// [0, 1] kept and flagged (never clipped), and the LGD proxy of the SBA charge-off twin with its bias stated. Each draws
// what the c08-outputs document carries.
import { BarChart, Callout, PlotCard, ViewsRow, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { ChartOverTable, axisScale, money } from '../c06/format';
import { FixtureNotice } from '../c06/C06Common';
import { Pending } from '../Pending';
import { Flagged, p2, useCard } from '../c03/U6Shared';
import { INCOMPLETE_TEXT, WORKOUT_CONVENTION, outputsOf, type C08Sel } from './selection';

const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });
const edge = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { percent: true, decimals: 0 });

/** The LGD of the defaults of this cohort: a histogram on [0, 1] with the values outside it flagged beside it. */
export function DistributionView({ sel }: { sel: C08Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const d = o.lgd_distribution;
  const to = pick({ en: 'to', es: 'a' }, lang);
  const data = [
    { id: 'below-zero', label: { en: 'Below 0 (flagged)', es: 'Bajo 0 (marcado)' }, value: d.share_below_zero, tone: 'bad' as const },
    ...d.bins.map((b, i) => ({ id: `bin-${i}`, label: { en: `${edge(b.lower, 'en')} to ${edge(b.upper, 'en')}`, es: `${edge(b.lower, 'es')} a ${edge(b.upper, 'es')}` }, value: b.share, tone: 'accent' as const })),
    { id: 'above-one', label: { en: 'Above 1 (flagged)', es: 'Sobre 1 (marcado)' }, value: d.share_above_one, tone: 'bad' as const },
  ];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'LGD distribution', es: 'Distribución de la LGD' }}
        {...card}
        note={{
          en: 'The share of the defaults of this cohort in each tenth of the loss given default. The first and last tenths hold the masses at exactly 0 and exactly 1. A value below 0 or above 1 is a real observation (a recovery above the exposure, a charge-off above the approval) and is kept and flagged, never clipped into the range.',
          es: 'La proporción de los incumplimientos de esta cohorte en cada décima de la pérdida dado el incumplimiento. La primera y la última décima contienen las masas en exactamente 0 y exactamente 1. Un valor bajo 0 o sobre 1 es una observación real (una recuperación sobre la exposición, un castigo sobre lo aprobado) y se conserva y se marca, nunca se recorta al rango.',
        }}
      >
        <ChartOverTable
          chartMin={`${data.length * 1.5 + 3}rem`}
          chart={<BarChart title={{ en: 'Share of defaults by LGD tenth', es: 'Proporción de incumplimientos por décima de LGD' }} height="fill" orientation="horizontal" data={data} axis={{ label: { en: 'Share of the defaults', es: 'Proporción de los incumplimientos' }, format: { percent: true, digits: 2 } }} />}
        >
          <table className="caos-table ct-wrap-head" data-table="lgd-summary" data-treatment={d.treatment}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Of the defaults', es: 'De los incumplimientos' }, lang)}</th>
                <th>{pick({ en: 'Count', es: 'Cantidad' }, lang)}</th>
                <th>{pick({ en: 'Share', es: 'Proporción' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              <tr data-mass="zero">
                <td className="ct-text">{pick({ en: 'Exactly 0 (full recovery)', es: 'Exactamente 0 (recuperación total)' }, lang)}</td>
                <td>{count(d.mass_at_zero.n, lang)}</td>
                <td>{p2(d.mass_at_zero.share, lang)}</td>
              </tr>
              <tr data-mass="one">
                <td className="ct-text">{pick({ en: 'Exactly 1 (no recovery)', es: 'Exactamente 1 (sin recuperación)' }, lang)}</td>
                <td>{count(d.mass_at_one.n, lang)}</td>
                <td>{p2(d.mass_at_one.share, lang)}</td>
              </tr>
              <tr data-range="below-zero">
                <td className="ct-text">{pick({ en: 'Below 0, kept and flagged', es: 'Bajo 0, conservados y marcados' }, lang)}</td>
                <td>{count(d.n_below_zero, lang)}</td>
                <td>{p2(d.share_below_zero, lang)}</td>
              </tr>
              <tr data-range="above-one">
                <td className="ct-text">{pick({ en: 'Above 1, kept and flagged', es: 'Sobre 1, conservados y marcados' }, lang)}</td>
                <td>{count(d.n_above_one, lang)}</td>
                <td>{p2(d.share_above_one, lang)}</td>
              </tr>
              <tr>
                <td className="ct-text">{pick({ en: 'Lowest LGD', es: 'LGD más baja' }, lang)}</td>
                <td colSpan={2}>
                  <Flagged value={d.lowest.value} flag={d.lowest.flag} extreme="lowest" />
                </td>
              </tr>
              <tr>
                <td className="ct-text">{pick({ en: 'Highest LGD', es: 'LGD más alta' }, lang)}</td>
                <td colSpan={2}>
                  <Flagged value={d.highest.value} flag={d.highest.flag} extreme="highest" />
                </td>
              </tr>
              <tr>
                <td className="ct-text">{pick({ en: 'Mean', es: 'Media' }, lang)}</td>
                <td colSpan={2}>
                  <Flagged value={d.mean.value} flag={d.mean.flag} extreme="mean" />
                </td>
              </tr>
              <tr>
                <td className="ct-text">{pick({ en: 'Median', es: 'Mediana' }, lang)}</td>
                <td colSpan={2}>
                  <Flagged value={d.median.value} flag={d.median.flag} extreme="median" />
                </td>
              </tr>
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head ct-wide-only" data-table="lgd-bins">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'LGD tenth', es: 'Décima de LGD' }, lang)}</th>
                <th>{pick({ en: 'Count', es: 'Cantidad' }, lang)}</th>
                <th>{pick({ en: 'Share', es: 'Proporción' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {d.bins.map((b, i) => (
                <tr key={i} data-bin={i}>
                  <td className="ct-text">{`${edge(b.lower, lang)} ${to} ${edge(b.upper, lang)}`}</td>
                  <td>{count(b.n, lang)}</td>
                  <td>{p2(b.share, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** What the LGD of this case is: a charge-off proxy, its formula, its fields, its bias and the data it stands on. */
export function ProxyView({ sel }: { sel: C08Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const p = o.lgd_proxy;
  const w = o.workout;
  const d = o.data_status;
  const scale = axisScale(Math.max(o.exposure.gross_approval_total, o.exposure.gross_charge_off_total), o.exposure.currency);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The LGD proxy and its bias', es: 'El proxy de LGD y su sesgo' }}
        {...card}
        note={{
          en: 'The LGD of this case is a proxy, not a workout LGD: the public SBA 7(a) file carries no recovery cash flows, so the loss is the gross charge-off over the approved amount.',
          es: 'La LGD de este caso es un proxy, no una LGD de recuperación: el archivo público SBA 7(a) no trae flujos de recuperación, así que la pérdida es el castigo bruto sobre el monto aprobado.',
        }}
      >
        <ChartOverTable
          chart={
            <BarChart
              title={{ en: 'The two totals of the proxy', es: 'Los dos totales del proxy' }}
              height="fill"
              orientation="horizontal"
              data={[
                { id: 'approved', label: { en: 'Approved amount (the denominator)', es: 'Monto aprobado (el denominador)' }, value: o.exposure.gross_approval_total / scale.div, tone: 'neutral' as const },
                { id: 'charged-off', label: { en: 'Charged off (the numerator)', es: 'Castigado (el numerador)' }, value: o.exposure.gross_charge_off_total / scale.div, tone: 'accent' as const },
              ]}
              axis={{ label: { en: `Gross amount (${pick(scale.unit, 'en')})`, es: `Monto bruto (${pick(scale.unit, 'es')})` }, format: { digits: 3 } }}
            />
          }
        >
          <FixtureNotice variant={sel.data.variant} />
          <dl className="ct-defs" data-table="lgd-proxy">
            <dt>{pick({ en: 'Definition', es: 'Definición' }, lang)}</dt>
            <dd>{pick(p.definition, lang)}</dd>
            <dt>{pick({ en: 'Formula', es: 'Fórmula' }, lang)}</dt>
            <dd>{p.formula}</dd>
            <dt>{pick({ en: 'Fields', es: 'Campos' }, lang)}</dt>
            <dd>{`${p.source_field} / ${p.exposure_field}`}</dd>
            <dt>{pick({ en: 'Recovery cash flows', es: 'Flujos de recuperación' }, lang)}</dt>
            <dd data-recovery-flows={String(p.recovery_cash_flows_available)}>{p.recovery_cash_flows_available ? pick({ en: 'available', es: 'disponibles' }, lang) : pick({ en: 'not available in the file', es: 'no disponibles en el archivo' }, lang)}</dd>
            <dt>{pick({ en: 'Bias', es: 'Sesgo' }, lang)}</dt>
            <dd data-bias={p.bias_direction}>{pick({ en: 'The proxy is biased downward (low).', es: 'El proxy tiene un sesgo a la baja.' }, lang)}</dd>
            <dt>{pick({ en: 'Why', es: 'Por qué' }, lang)}</dt>
            <dd>{pick(p.bias_statement, lang)}</dd>
            <dt>{pick({ en: 'Charged off, in total', es: 'Castigado, en total' }, lang)}</dt>
            <dd data-total="gross-charge-off">{money(o.exposure.gross_charge_off_total, lang, o.exposure.currency)}</dd>
            <dt>{pick({ en: 'Approved, in total', es: 'Aprobado, en total' }, lang)}</dt>
            <dd data-total="gross-approval">{money(o.exposure.gross_approval_total, lang, o.exposure.currency)}</dd>
            <dt>{pick({ en: 'Discounting', es: 'Descuento' }, lang)}</dt>
            <dd data-convention={w.discount_rate_convention}>{pick(WORKOUT_CONVENTION[w.discount_rate_convention], lang)}</dd>
            <dt>{pick({ en: 'Open workouts', es: 'Recuperaciones abiertas' }, lang)}</dt>
            <dd data-treatment={w.incomplete_workouts.treatment}>{`${pick(INCOMPLETE_TEXT[w.incomplete_workouts.treatment], lang)}${w.incomplete_workouts.reason ? `: ${pick(w.incomplete_workouts.reason, lang)}` : ''}`}</dd>
            <dt>Freddie Mac</dt>
            <dd data-freddie-mac={String(d.freddie_mac_available)}>
              {d.freddie_mac_available ? pick({ en: 'available', es: 'disponible' }, lang) : `${pick({ en: 'not available', es: 'no disponible' }, lang)}: ${d.freddie_mac_reason ? pick(d.freddie_mac_reason, lang) : ''}`}
            </dd>
          </dl>
          <Callout variant="honest" title={pick({ en: 'How the workout is treated', es: 'Cómo se trata la recuperación' }, lang)}>
            {pick(w.note, lang)}
          </Callout>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
