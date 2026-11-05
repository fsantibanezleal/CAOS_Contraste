// C13's Desk back-test group: the desk's exception count over 250 days against the MAR32.18 limit (more than 12 at the
// 99 percent level, or 30 at 97.5 percent, moves the desk to the standardised approach), across the replications. The
// distribution of the count and the share of replications over the limit are the document's.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { ChartOverTable } from '../c06/format';
import { Pending } from '../Pending';
import { rangeText } from '../c08/words';
import { useCard } from '../c03/U6Shared';
import { ViewFoot, deficiencyName } from './C13Common';
import { fitOf, levelLabel, outputsOf, type C13Sel } from './selection';

const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });

export function DeskView({ sel }: { sel: C13Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const lvl = o.desk_backtest.find((l) => l.alpha === sel.alpha) ?? null;
  const name = deficiencyName(o);
  const reference = fitOf(sel)?.desk_limits.find((l) => l.alpha === sel.alpha)?.reference ?? 'MAR32.18 to MAR32.19';
  if (!lvl) {
    return (
      <ViewsRow>
        <PlotCard fill title={{ en: `Desk back-test, ${name.en}`, es: `Prueba retrospectiva de la mesa, ${name.es}` }} {...card}>
          <p className="ct-note" data-state="unavailable">{pick({ en: 'This variant carries no desk back-test at this level.', es: 'Esta variante no trae prueba retrospectiva de la mesa en este nivel.' }, lang)}</p>
          <ViewFoot o={o} />
        </PlotCard>
      </ViewsRow>
    );
  }
  const e = lvl.exceptions;
  const bars = [
    // short labels a 390 px chart writes whole ("5th perce...", R3 c14 m10); the hint names the percentile
    { id: 'min', label: { en: 'Fewest', es: 'Mínimo' }, value: e.min, tone: 'accent' as const },
    { id: 'q05', label: { en: 'P5', es: 'P5' }, hint: { en: '5th percentile', es: 'Percentil 5' }, value: e.q05, tone: 'accent' as const },
    { id: 'q50', label: { en: 'Median', es: 'Mediana' }, value: e.q50, tone: 'accent' as const },
    // the mean with the decimal of the table (R3 c14 m2: a bar "22" beside 22.2)
    { id: 'mean', label: { en: 'Mean', es: 'Media' }, value: e.mean, tone: 'accent' as const, format: { decimals: 1 } },
    { id: 'q95', label: { en: 'P95', es: 'P95' }, hint: { en: '95th percentile', es: 'Percentil 95' }, value: e.q95, tone: 'accent' as const },
    { id: 'max', label: { en: 'Most', es: 'Máximo' }, value: e.max, tone: 'accent' as const },
    { id: 'limit', label: { en: 'Limit', es: 'Límite' }, value: lvl.limit_exceptions, tone: 'bad' as const },
  ];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `Desk back-test at the ${levelLabel(lvl.alpha, 'en')}, ${name.en}`, es: `Prueba retrospectiva de la mesa en la ${levelLabel(lvl.alpha, 'es', true)}, ${name.es}` }}
        {...card}
        note={{
          en: `Exceptions of the ${lvl.basis} against the desk VaR over ${count(lvl.n_days, 'en')} days, across the replications. More than ${count(lvl.limit_exceptions, 'en')} moves the desk to the standardised approach.`,
          es: `Excepciones del ${lvl.basis} frente al VaR de la mesa en ${count(lvl.n_days, 'es')} días, entre las replicaciones. Más de ${count(lvl.limit_exceptions, 'es')} pasa la mesa al método estandarizado.`,
        }}
      >
        <ChartOverTable
          chartMin="14rem"
          chart={
            <BarChart
              title={{ en: 'Exceptions in 250 days across the replications', es: 'Excepciones en 250 días entre las replicaciones' }}
              height="fill"
              orientation="vertical"
              data={bars}
              axis={{ label: { en: 'Exceptions', es: 'Excepciones' }, format: { decimals: 0 } }}
            />
          }
        >
          <div data-level={lvl.alpha}>
            <table className="caos-table ct-wrap-head" data-table="c13-desk">
              <caption className="ct-note">{rangeText(reference, lang)}</caption>
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Level', es: 'Nivel' }, lang)}</th>
                  <th className="ct-text ct-wide-only">{pick({ en: 'Basis', es: 'Base' }, lang)}</th>
                  <th>{pick({ en: 'Limit', es: 'Límite' }, lang)}</th>
                  <th>{pick({ en: 'Mean', es: 'Media' }, lang)}</th>
                  <th>{pick({ en: '95th percentile', es: 'Percentil 95' }, lang)}</th>
                  <th>{pick({ en: 'Within the limit', es: 'Dentro del límite' }, lang)}</th>
                  <th>{pick({ en: 'Over the limit', es: 'Sobre el límite' }, lang)}</th>
                  <th>{pick({ en: 'Share over', es: 'Parte sobre' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {o.desk_backtest.map((l) => (
                  <tr key={l.alpha} data-level={l.alpha} className={l.alpha === lvl.alpha ? 'ct-current' : undefined}>
                    <td className="ct-text">{levelLabel(l.alpha, lang)}</td>
                    <td className="ct-text ct-wide-only">{l.basis}</td>
                    <td>{count(l.limit_exceptions, lang)}</td>
                    <td>{formatNumber(l.exceptions.mean, lang, { decimals: 1 })}</td>
                    <td>{formatNumber(l.exceptions.q95, lang, { decimals: 1 })}</td>
                    <td>{count(l.n_within_limit, lang)}</td>
                    <td>{count(l.n_over_limit, lang)}</td>
                    <td>{formatNumber(l.share_over_limit, lang, { percent: true, decimals: 1 })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ViewFoot o={o} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
