// C11's Comparison group: eligibility first, then the comparative back-test of Nolde and Ziegel. The champion view ranks
// the ladder by its average FZ0 score and draws the model confidence set (the elimination p-value of each model); the
// Diebold-Mariano view compares every model with the champion under the FZ0 score and the tick loss. A score that is not
// available (a model that forecasts no ES has no FZ0) shows its reason, never a zero.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { MaybeNumber } from '../c06/format';
import { ChartAbove } from '../c16/C16Common';
import { Pending } from '../Pending';
import { useCard } from '../c03/U6Shared';
import { ConventionLine, rowsMin } from './MarketCommon';
import { DIRECTION_TEXT, LOSS_TEXT, championOf, fitOf, modelLabel, outputsOf, rungOf, text, reasonText, type C11Sel } from './selection';

const rowsHeight = rowsMin;

/** The ladder by average FZ0, the champion and the model confidence set at the level in focus. */
export function ChampionView({ sel }: { sel: C11Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const fit = fitOf(sel);
  const champion = championOf(o, sel.alpha);
  const champ = o.comparison.champions.find((c) => c.alpha === sel.alpha);
  const mcs = o.comparison.mcs.find((m) => m.alpha === sel.alpha) ?? null;
  const ranked = o.models
    .map((m) => ({ m, lv: m.by_level.find((l) => l.alpha === sel.alpha) ?? null }))
    .sort((a, b) => (a.lv?.fz0_mean ?? Infinity) - (b.lv?.fz0_mean ?? Infinity));
  const inSet = (id: string) => mcs?.members.find((x) => x.model_id === id) ?? null;
  const confidence = mcs ? formatNumber(mcs.confidence, lang, { percent: true, decimals: 0 }) : '';
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The champion and the model confidence set', es: 'El campeón y el conjunto de confianza de modelos' }}
        {...card}
        note={{
          en: 'Ranked by average FZ0 score, lower is better. The bars are the elimination p-value of the model confidence set on FZ0.',
          es: 'Ordenados por puntaje FZ0 medio, menor es mejor. Las barras son el valor p de eliminación del conjunto de confianza de modelos sobre FZ0.',
        }}
      >
        <ChartAbove
          chartHeight={rowsHeight(mcs?.members.length ?? 0)}
          chart={
            <BarChart
              title={{ en: 'Model confidence set p-value on FZ0', es: 'Valor p del conjunto de confianza de modelos sobre FZ0' }}
              height="fill"
              orientation="horizontal"
              // the bars follow the ranking the note states: lowest average FZ0 first (U16-R2 b05 m6)
              data={[...(mcs?.members ?? [])].sort((a, b) => ranked.findIndex((r) => r.m.model_id === a.model_id) - ranked.findIndex((r) => r.m.model_id === b.model_id)).map((x) => ({
                id: x.model_id,
                label: modelLabel(sel, x.model_id),
                value: x.p_value,
                tone: x.in_set ? ('good' as const) : ('bad' as const),
                highlight: x.model_id === champion,
              }))}
              axis={{ label: { en: 'p-value', es: 'Valor p' }, format: { decimals: 2 }, range: [0, 1] }}
            />
          }
        >
          <ConventionLine />
          <p className="ct-note" data-state={champion === null ? 'unavailable' : undefined}>
            {champion === null
              ? `${formatNumber(null, lang)} (${reasonText(champ?.reason, lang)})`
              : pick({ en: `Champion at this level: ${modelLabel(sel, champion).en}, the lowest average FZ0 among the eligible models.`, es: `Campeón en este nivel: ${modelLabel(sel, champion).es}, el menor FZ0 medio entre los modelos elegibles.` }, lang)}
          </p>
          {mcs ? (
            <p className="ct-note">
              {pick(
                {
                  en: `Model confidence set at ${confidence}: ${mcs.n_in_set} of ${mcs.members.length} models stay in the set (${mcs.statistic} statistic, ${formatNumber(mcs.n_bootstrap, 'en', { decimals: 0 })} bootstrap draws, block ${mcs.block_length}).`,
                  es: `Conjunto de confianza de modelos al ${confidence}: ${mcs.n_in_set} de ${mcs.members.length} modelos siguen en el conjunto (estadístico ${mcs.statistic}, ${formatNumber(mcs.n_bootstrap, 'es', { decimals: 0 })} remuestreos, bloque ${mcs.block_length}).`,
                },
                lang,
              )}
            </p>
          ) : null}
          {fit ? <p className="ct-note">{pick(fit.scoring.selection_rule, lang)}</p> : null}
          <table className="caos-table ct-wrap-head" data-table="c11-champion">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Model', es: 'Modelo' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Rung', es: 'Escalón' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Eligible', es: 'Elegible' }, lang)}</th>
                <th>{pick({ en: 'Average FZ0', es: 'FZ0 medio' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Average tick loss', es: 'Pérdida tick media' }, lang)}</th>
                <th>{pick({ en: 'MCS p-value', es: 'Valor p del MCS' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'In the set', es: 'En el conjunto' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {ranked.map(({ m, lv }) => {
                const member = inSet(m.model_id);
                return (
                  <tr key={m.model_id} data-model={m.model_id} data-champion={m.model_id === champion ? 'true' : undefined} data-in-set={member ? String(member.in_set) : undefined} className={m.model_id === sel.model ? 'ct-current' : undefined}>
                    <td className="ct-text">{pick(modelLabel(sel, m.model_id), lang)}{m.model_id === champion ? ` (${pick({ en: 'champion', es: 'campeón' }, lang)})` : ''}</td>
                    <td className="ct-wide-only">{rungOf(sel, m.model_id)}</td>
                    <td className="ct-text">{m.eligible ? pick({ en: 'yes', es: 'sí' }, lang) : pick({ en: 'no', es: 'no' }, lang)}</td>
                    <td>
                      <MaybeNumber value={lv?.fz0_mean ?? null} reason={lv?.fz0_reason ? reasonText(lv.fz0_reason, lang) : null} format={(v) => formatNumber(v, lang, { digits: 4 })} />
                    </td>
                    <td className="ct-wide-only">{lv ? formatNumber(lv.tick_loss_mean, lang, { digits: 3 }) : formatNumber(null, lang)}</td>
                    <td data-na={member ? undefined : 'true'}>{member ? formatNumber(member.p_value, lang, { digits: 2 }) : formatNumber(null, lang)}</td>
                    <td className="ct-text">{member ? (member.in_set ? pick({ en: 'in', es: 'dentro' }, lang) : pick({ en: 'out', es: 'fuera' }, lang)) : formatNumber(null, lang)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </ChartAbove>
      </PlotCard>
    </ViewsRow>
  );
}

/** Every model against the champion under the FZ0 score and the tick loss: the Diebold-Mariano statistic and its p-value. */
export function DmView({ sel }: { sel: C11Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const rows = o.comparison.dm.filter((d) => d.alpha === sel.alpha);
  const champion = championOf(o, sel.alpha);
  const fz0 = rows.filter((d) => d.loss === 'fz0');
  const tone = { better: 'good', worse: 'bad', indistinguishable: 'neutral', 'not-evaluated': 'neutral' } as const;
  // no champion, nothing to draw: the reason is the view, with no empty stage above it (R3 c12 m3)
  if (champion === null) {
    return (
      <ViewsRow>
        <PlotCard fill title={{ en: 'Diebold-Mariano against the champion', es: 'Diebold-Mariano contra el campeón' }} {...card}>
          <div className="ct-scroll" data-caos-flow="">
            <ConventionLine />
            <p className="ct-note" data-state="unavailable">{pick({ en: 'No champion at this level, so there is nothing to compare with.', es: 'No hay campeón en este nivel, así que no hay con qué comparar.' }, lang)}</p>
          </div>
        </PlotCard>
      </ViewsRow>
    );
  }
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Diebold-Mariano against the champion', es: 'Diebold-Mariano contra el campeón' }}
        {...card}
        note={{
          en: `The loss differential is the model minus the champion on the days both are defined: negative favours the model. Bartlett long-run variance with ${o.comparison.hac_lags} lags (one-step forecasts), significance ${formatNumber(o.comparison.significance, 'en', { percent: true, decimals: 0 })}.`,
          es: `El diferencial de pérdida es el modelo menos el campeón en los días en que ambos están definidos: negativo favorece al modelo. Varianza de largo plazo de Bartlett con ${o.comparison.hac_lags} rezagos (pronósticos a un paso), significancia ${formatNumber(o.comparison.significance, 'es', { percent: true, decimals: 0 })}.`,
        }}
      >
        <ChartAbove
          chartHeight={rowsHeight(fz0.length)}
          chart={
            <BarChart
              title={{ en: 'Diebold-Mariano p-value on FZ0', es: 'Valor p de Diebold-Mariano sobre FZ0' }}
              height="fill"
              orientation="horizontal"
              data={fz0.map((d) => ({ id: d.model_id, label: modelLabel(sel, d.model_id), value: d.p_value, tone: tone[d.direction] }))}
              axis={{ label: { en: 'p-value', es: 'Valor p' }, format: { decimals: 2 }, range: [0, 1] }}
            />
          }
        >
          <ConventionLine />
          {champion === null ? (
            <p className="ct-note" data-state="unavailable">{pick({ en: 'No champion at this level, so there is nothing to compare with.', es: 'No hay campeón en este nivel, así que no hay con qué comparar.' }, lang)}</p>
          ) : (
            <p className="ct-note">{pick({ en: `Compared with ${modelLabel(sel, champion).en}.`, es: `Comparado con ${modelLabel(sel, champion).es}.` }, lang)}</p>
          )}
          <table className="caos-table ct-wrap-head" data-table="c11-dm">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Model', es: 'Modelo' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Score', es: 'Puntaje' }, lang)}</th>
                <th>{pick({ en: 'Mean difference', es: 'Diferencia media' }, lang)}</th>
                <th>DM</th>
                <th>p</th>
                <th className="ct-wide-only">{pick({ en: 'Common days', es: 'Días comunes' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Verdict', es: 'Veredicto' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((d) => (
                <tr key={`${d.model_id}-${d.loss}`} data-dm={`${d.model_id}-${d.loss}`} data-direction={d.direction}>
                  <td className="ct-text">{pick(modelLabel(sel, d.model_id), lang)}</td>
                  <td className="ct-text">{pick(text(LOSS_TEXT, d.loss), lang)}</td>
                  <td>
                    <MaybeNumber value={d.mean_diff} reason={null} format={(v) => formatNumber(v, lang, { digits: 4 })} />
                  </td>
                  <td>
                    <MaybeNumber value={d.dm_statistic} reason={null} format={(v) => formatNumber(v, lang, { digits: 4 })} />
                  </td>
                  <td>
                    <MaybeNumber value={d.p_value} reason={null} format={(v) => formatNumber(v, lang, { digits: 2 })} />
                  </td>
                  <td className="ct-wide-only">{d.n_common === null ? formatNumber(null, lang) : formatNumber(d.n_common, lang, { decimals: 0 })}</td>
                  <td className="ct-text">
                    {pick(text(DIRECTION_TEXT, d.direction), lang)}
                    {d.not_evaluated_reason ? <span className="ct-note" style={{ display: 'block' }}>{reasonText(d.not_evaluated_reason, lang)}</span> : null}
                  </td>
                </tr>
              ))}
              {rows.length === 0 ? (
                <tr>
                  <td className="ct-text" colSpan={7}>{pick({ en: 'No comparison at this level.', es: 'No hay comparación en este nivel.' }, lang)}</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </ChartAbove>
      </PlotCard>
    </ViewsRow>
  );
}
