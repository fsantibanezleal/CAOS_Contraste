// C13's PLA complement (BS-13, the beyond tier): three statistics the regulatory PLA lacks, beside its zone and never in place of
// it. The Mincer-Zarnowitz Wald test sees a mis-scaled model, the Spearman correlation of the absolute P&L and that of its
// 20-day rolling means see a risk model whose volatility lags. Their critical values are calibrated on a simulated null so the
// stated type I error holds; every number is the bake's, computed by the engine. The lag ladder re-runs the stale-volatility
// desk at 5, 10, 20 and 40 days, and the hypothesis of the plan is shown with its measured number and its verdict, whichever it is.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable } from '../c06/format';
import { rowsMin } from '../c11/MarketCommon';
import { Pending } from '../Pending';
import { useCard, type Bi } from '../c03/U6Shared';
import { ViewFoot, deficiencyName } from './C13Common';
import { outputsOf, type C13Outputs, type C13Sel } from './selection';

type Complement = NonNullable<C13Outputs['pla_complement']>;
type Rate = Complement['flags']['pla_amber_or_red'];

const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });
const pct = (v: number, lang: 'en' | 'es', decimals = 1) => formatNumber(v, lang, { percent: true, decimals });
const interval = (r: Rate, lang: 'en' | 'es') => `${pct(r.ci_low, lang)} - ${pct(r.ci_high, lang)}`;

const VERDICT_TEXT: Record<string, Bi> = {
  holds: { en: 'Holds', es: 'Se sostiene' },
  refuted: { en: 'Refuted', es: 'Refutada' },
  'not-established': { en: 'Not established', es: 'No establecida' },
};

const STAT_TEXT: Record<'wald' | 'spearman_abs' | 'spearman_roll', Bi> = {
  wald: { en: 'Scale and level (Wald test of a = 0, b = 1)', es: 'Escala y nivel (prueba de Wald de a = 0, b = 1)' },
  spearman_abs: { en: 'Size of the move (Spearman of the absolute P&L)', es: 'Tamaño del movimiento (Spearman del P&L absoluto)' },
  spearman_roll: { en: 'Lagging scale (Spearman of the 20-day rolling means)', es: 'Escala rezagada (Spearman de las medias móviles de 20 días)' },
};

/** The note shown when a document predates the complement: older documents stay valid, the view says so. */
function Unavailable({ o, name }: { o: C13Outputs; name: Bi }) {
  const lang = useShellLang();
  const card = useCard(undefined);
  return (
    <ViewsRow>
      <PlotCard fill title={{ en: `The PLA complement, ${name.en}`, es: `El complemento del PLA, ${name.es}` }} {...card}>
        <p className="ct-note" data-state="unavailable">
          {pick({ en: 'This document predates the PLA complement: it carries no complement result.', es: 'Este documento es anterior al complemento del PLA: no trae resultado del complemento.' }, lang)}
        </p>
        <ViewFoot o={o} />
      </PlotCard>
    </ViewsRow>
  );
}

/** What the complement flags on this desk beside the regulatory zone, with its critical values and, on the stale-volatility desk, the plan's verdict. */
export function ComplementView({ sel }: { sel: C13Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const name = deficiencyName(o);
  const c = o.pla_complement;
  if (!c) return <Unavailable o={o} name={name} />;
  const f = c.flags;
  const power = c.role === 'power';
  const n = c.n_replications;
  const bars = [
    { id: 'pla', label: { en: 'Regulatory PLA, amber or red', es: 'PLA regulatorio, ámbar o rojo' }, value: f.pla_amber_or_red.k, tone: 'neutral' as const },
    { id: 'wald', label: { en: 'Scale and level', es: 'Escala y nivel' }, value: f.per_statistic.wald.k, tone: 'accent' as const },
    { id: 'abs', label: { en: 'Size of the move', es: 'Tamaño del movimiento' }, value: f.per_statistic.spearman_abs.k, tone: 'accent' as const },
    { id: 'roll', label: { en: 'Lagging scale', es: 'Escala rezagada' }, value: f.per_statistic.spearman_roll.k, tone: 'accent' as const },
    { id: 'union', label: { en: 'Any of the three, size 1% for the union', es: 'Cualquiera de las tres, tamaño 1 % para la unión' }, value: f.family.any.k, tone: 'good' as const },
    { id: 'both', label: { en: 'Complement or PLA', es: 'Complemento o PLA' }, value: f.family_with_pla.k, tone: 'good' as const },
  ];
  const rows: Array<{ id: string; label: Bi; r: Rate }> = [
    { id: 'pla', label: { en: 'Regulatory PLA, amber or red (MAR32.42)', es: 'PLA regulatorio, ámbar o rojo (MAR32.42)' }, r: f.pla_amber_or_red },
    ...(['wald', 'spearman_abs', 'spearman_roll'] as const).map((k) => ({ id: k, label: STAT_TEXT[k], r: f.per_statistic[k] })),
    { id: 'any', label: { en: 'Any of the three statistics, size 1% for each', es: 'Cualquiera de los tres estadísticos, tamaño 1 % para cada uno' }, r: f.per_statistic.any },
    { id: 'family', label: { en: 'Any of the three statistics, size 1% for the union', es: 'Cualquiera de los tres estadísticos, tamaño 1 % para la unión' }, r: f.family.any },
    { id: 'family-roll', label: { en: 'Lagging scale alone, size 1% for the union', es: 'Escala rezagada sola, tamaño 1 % para la unión' }, r: f.family.spearman_roll },
    { id: 'both', label: { en: 'Complement (union at 1%) or regulatory PLA', es: 'Complemento (unión al 1 %) o PLA regulatorio' }, r: f.family_with_pla },
  ];
  const th = c.calibration.thresholds_per_statistic;
  const h = c.hypothesis;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `The scale-and-level complement beside the PLA, ${name.en}`, es: `El complemento de escala y nivel junto al PLA, ${name.es}` }}
        {...card}
        note={{
          en: `${power ? 'Power' : 'Size'}: the replications flagged out of ${count(n, 'en')}${power ? '' : ', all with an exact model, so the rate is the false-alarm rate'}. Beyond the state of the art and added to the regulatory zone, never in place of it; it has no regulatory standing. The critical values come from ${count(c.calibration.n_null, 'en')} simulated null desk-years.`,
          es: `${power ? 'Potencia' : 'Tamaño'}: las replicaciones marcadas de ${count(n, 'es')}${power ? '' : ', todas con un modelo exacto, así que la tasa es la de falsas alarmas'}. Más allá del estado del arte y agregado a la zona regulatoria, nunca en su lugar; no tiene valor regulatorio. Los valores críticos vienen de ${count(c.calibration.n_null, 'es')} años de mesa nulos simulados.`,
        }}
      >
        <ChartOverTable
          chartMin={rowsMin(bars.length)}
          chart={
            <BarChart
              title={{ en: 'Replications flagged', es: 'Replicaciones marcadas' }}
              height="fill"
              orientation="horizontal"
              data={bars}
              axis={{ label: { en: 'Replications', es: 'Replicaciones' }, format: { decimals: 0 }, range: [0, n] }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c13-complement" data-role={c.role}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Rule', es: 'Regla' }, lang)}</th>
                <th>{pick({ en: 'Flagged', es: 'Marcadas' }, lang)}</th>
                <th>{pick({ en: 'Rate', es: 'Tasa' }, lang)}</th>
                <th>{pick({ en: '95% interval', es: 'Intervalo de 95 %' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} data-rule={r.id}>
                  <td className="ct-text">{pick(r.label, lang)}</td>
                  <td>{`${count(r.r.k, lang)} / ${count(r.r.n, lang)}`}</td>
                  <td>{pct(r.r.rate, lang)}</td>
                  <td>{interval(r.r, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <dl className="ct-defs" data-table="c13-complement-calibration">
            <dt>{pick({ en: 'Critical values at 1% for each statistic', es: 'Valores críticos con 1 % para cada estadístico' }, lang)}</dt>
            <dd>
              {pick(
                {
                  en: `Wald above ${formatNumber(th.wald, 'en', { decimals: 2 })}; Spearman of the absolute P&L below ${formatNumber(th.spearman_abs, 'en', { decimals: 3 })}; Spearman of the rolling means below ${formatNumber(th.spearman_roll, 'en', { decimals: 3 })}`,
                  es: `Wald sobre ${formatNumber(th.wald, 'es', { decimals: 2 })}; Spearman del P&L absoluto bajo ${formatNumber(th.spearman_abs, 'es', { decimals: 3 })}; Spearman de las medias móviles bajo ${formatNumber(th.spearman_roll, 'es', { decimals: 3 })}`,
                },
                lang,
              )}
            </dd>
            <dt>{pick({ en: 'Null used', es: 'Nulo usado' }, lang)}</dt>
            <dd>
              {pick(
                {
                  en: `${count(c.calibration.n_null, 'en')} desk-years of the exact model in ${count(c.calibration.null_case_seeds.length, 'en')} blocks, under case seeds that share none with the committed run`,
                  es: `${count(c.calibration.n_null, 'es')} años de mesa del modelo exacto en ${count(c.calibration.null_case_seeds.length, 'es')} bloques, con semillas de caso que no comparten ninguna con la corrida versionada`,
                },
                lang,
              )}
            </dd>
            {c.against_ks ? (
              <>
                <dt>{pick({ en: 'Scale-and-level test against KS alone', es: 'Prueba de escala y nivel frente a KS solo' }, lang)}</dt>
                <dd data-wald-at-least-ks={String(c.against_ks.wald_at_least_ks)}>
                  {pick(
                    {
                      en: `${count(c.against_ks.wald_flagged, 'en')} flagged against ${count(c.against_ks.ks_flagged, 'en')} for the Kolmogorov-Smirnov statistic alone: ${c.against_ks.wald_at_least_ks ? 'at least as many' : 'fewer'}`,
                      es: `${count(c.against_ks.wald_flagged, 'es')} marcadas frente a ${count(c.against_ks.ks_flagged, 'es')} del estadístico de Kolmogorov-Smirnov solo: ${c.against_ks.wald_at_least_ks ? 'al menos tantas' : 'menos'}`,
                    },
                    lang,
                  )}
                </dd>
              </>
            ) : null}
            {h ? (
              <>
                <dt>{pick({ en: 'Hypothesis of the plan', es: 'Hipótesis del plan' }, lang)}</dt>
                <dd>{pick(h.statement, lang)}</dd>
                <dt>{pick({ en: 'Verdict', es: 'Veredicto' }, lang)}</dt>
                <dd data-verdict={h.verdict}>
                  <strong>{pick(VERDICT_TEXT[h.verdict] ?? { en: h.verdict, es: h.verdict }, lang)}</strong>
                  {`. ${pick(h.reading, lang)}`}
                </dd>
              </>
            ) : null}
          </dl>
          <ViewFoot o={o} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The stale-volatility desk at a lag of 5, 10, 20 and 40 days: the regulatory zone against the complement, and the power by size. */
export function LagLadderView({ sel }: { sel: C13Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const name = deficiencyName(o);
  const c = o.pla_complement;
  const ladder = c?.lag_ladder ?? null;
  if (!c || !ladder) {
    return (
      <ViewsRow>
        <PlotCard fill title={{ en: `Lag ladder, ${name.en}`, es: `Escalera de rezagos, ${name.es}` }} {...card}>
          <p className="ct-note" data-state="unavailable">
            {pick(
              {
                en: 'The lag ladder runs on the stale-volatility desk only: pick that variant to see how fast the complement and the regulatory PLA lose or gain power as the model lags the true volatility.',
                es: 'La escalera de rezagos corre solo sobre la mesa con volatilidad desactualizada: elija esa variante para ver con qué rapidez el complemento y el PLA regulatorio ganan o pierden potencia a medida que el modelo rezaga la volatilidad verdadera.',
              },
              lang,
            )}
          </p>
          <ViewFoot o={o} />
        </PlotCard>
      </ViewsRow>
    );
  }
  const lags = ladder.map((r) => r.lag_days);
  const n = c.n_replications;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `Lag ladder, ${name.en}`, es: `Escalera de rezagos, ${name.es}` }}
        {...card}
        note={{
          en: `The same ${count(n, 'en')} desk-years (the committed seeds) with the model fed a volatility of 5, 10, 20 and 40 days earlier; the critical values are the ones of the exact model, unchanged. The 20-day row is the variant itself.`,
          es: `Los mismos ${count(n, 'es')} años de mesa (las semillas versionadas) con el modelo alimentado con una volatilidad de 5, 10, 20 y 40 días antes; los valores críticos son los del modelo exacto, sin cambio. La fila de 20 días es la variante misma.`,
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: lags, label: { en: 'Days the model volatility lags', es: 'Días de rezago de la volatilidad del modelo' }, format: { decimals: 0 } }}
              y={{ label: { en: 'Share of replications flagged', es: 'Parte de las replicaciones marcadas' }, format: { percent: true, decimals: 0 } }}
              series={[
                { label: { en: 'Regulatory PLA', es: 'PLA regulatorio' }, values: ladder.map((r) => r.pla_amber_or_red.rate), color: '--color-fg-subtle', width: 2 },
                { label: { en: 'Lagging scale', es: 'Escala rezagada' }, values: ladder.map((r) => r.per_statistic.spearman_roll.rate), color: '--color-accent', width: 2 },
                { label: { en: 'Size of the move', es: 'Tamaño del movimiento' }, values: ladder.map((r) => r.per_statistic.spearman_abs.rate), color: '--color-magenta', width: 2 },
                { label: { en: 'Scale and level', es: 'Escala y nivel' }, values: ladder.map((r) => r.per_statistic.wald.rate), color: '--color-warn', width: 2 },
              ]}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c13-lag-ladder">
            <thead>
              <tr>
                <th>{pick({ en: 'Lag (days)', es: 'Rezago (días)' }, lang)}</th>
                <th>{pick({ en: 'Regulatory PLA', es: 'PLA regulatorio' }, lang)}</th>
                <th>{pick({ en: 'Lagging scale', es: 'Escala rezagada' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Size of the move', es: 'Tamaño del movimiento' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Scale and level', es: 'Escala y nivel' }, lang)}</th>
                <th>{pick({ en: 'Any, size 1% for the union', es: 'Cualquiera, tamaño 1 % para la unión' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {ladder.map((r) => (
                <tr key={r.lag_days} data-lag={r.lag_days}>
                  <td>{count(r.lag_days, lang)}</td>
                  <td>{pct(r.pla_amber_or_red.rate, lang)}</td>
                  <td>{pct(r.per_statistic.spearman_roll.rate, lang)}</td>
                  <td className="ct-wide-only">{pct(r.per_statistic.spearman_abs.rate, lang)}</td>
                  <td className="ct-wide-only">{pct(r.per_statistic.wald.rate, lang)}</td>
                  <td>{pct(r.family_any.rate, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head" data-table="c13-power-by-size">
            <thead>
              <tr>
                <th>{pick({ en: 'Size per statistic', es: 'Tamaño por estadístico' }, lang)}</th>
                <th>{pick({ en: 'Lagging scale: power', es: 'Escala rezagada: potencia' }, lang)}</th>
                <th>{pick({ en: 'Lagging scale: false alarms', es: 'Escala rezagada: falsas alarmas' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Scale and level: power', es: 'Escala y nivel: potencia' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Scale and level: false alarms', es: 'Escala y nivel: falsas alarmas' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {c.by_size.map((r) => (
                <tr key={r.size} data-size={r.size}>
                  <td>{pct(r.size, lang)}</td>
                  <td>{pct(r.spearman_roll.rate, lang)}</td>
                  <td>{pct(r.spearman_roll_held_out.rate, lang)}</td>
                  <td className="ct-wide-only">{pct(r.wald.rate, lang)}</td>
                  <td className="ct-wide-only">{pct(r.wald_held_out.rate, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <ViewFoot o={o} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
