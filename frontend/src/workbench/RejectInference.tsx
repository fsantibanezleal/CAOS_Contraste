// S-6, reject inference on a sample with a known rejected population: a card of the Ladder on the German twin (a seventh
// sub-view would break ADR-0071 rule 5, as TabPFN's card shows). The pipeline simulated a legacy acceptance policy on the 1,000
// fully labelled applicants, hid the outcomes of those it rejected, fitted the rungs on what a lender would have and scored
// them on an accept-all population; the card draws the judged policy's level bias with its interval beside the table of the
// same numbers, the bias of the accepted-only model under every policy, and the three hypotheses with their verdicts.
import { BarChart, PlotCard, formatNumber, pick, useShellLang, useWorkbenchState, type BiText } from '@fasl-work/caos-app-shell';
import { REPLAY, provenanceOf, type Selection } from './model';
import type { RejectInference, RejectRung } from '../lib/contract.types';

/** The policy the hypotheses are judged on (pipeline/cases/c01_reject.py PRIMARY). */
export const JUDGED_POLICY = 'moderate';

type Lang = 'en' | 'es';

const points = (x: number, lang: Lang, decimals = 2) => `${x > 0 ? '+' : ''}${formatNumber(x * 100, lang, { decimals })}`;
const signed = (x: number, lang: Lang, decimals = 4) => `${x > 0 ? '+' : ''}${formatNumber(x, lang, { decimals })}`;
const span = (lo: string, hi: string) => `${lo} / ${hi}`;

export function rungName(ri: RejectInference, id: string): BiText {
  return ri.rungs.find((r) => r.id === id)?.short_title ?? { en: id, es: id };
}

export function judgedRungs(ri: RejectInference): RejectRung[] {
  return (ri.regimes.find((g) => g.id === JUDGED_POLICY) ?? ri.regimes[ri.regimes.length - 1]).rungs;
}

export function RejectInferenceCard({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const ri = sel?.data.variant.outputs.reject_inference ?? null;
  if (!sel || !ri) return null;
  const regime = ri.regimes.find((g) => g.id === JUDGED_POLICY) ?? ri.regimes[ri.regimes.length - 1];
  const rows = regime.rungs;
  const d = ri.design;
  const held = ri.hypotheses.filter((h) => h.holds).length;
  const best = ri.hypotheses.find((h) => h.id === 'H2');
  return (
    <PlotCard
      fill
      title={{ en: 'Reject inference, simulated policy', es: 'Inferencia de rechazados simulada' }}
      lane={REPLAY}
      provenance={provenanceOf(sel.data.variant.provenance.truth_status)}
      dataKey={stateKey}
    >
      <div className="ct-scroll" data-caos-flow="" data-reject-inference="">
        <div className="ct-stack">
        <p className="ct-note" data-reject-verdict="">
          <strong>
            {pick(
              {
                en: `${held} of ${ri.hypotheses.length} hypotheses hold under ${regime.short_title.en.toLowerCase()}.${best ? ` ${best.outcome.en}` : ''}`,
                es: `${held} de ${ri.hypotheses.length} hipótesis se cumplen con ${regime.short_title.es.toLowerCase()}.${best ? ` ${best.outcome.es}` : ''}`,
              },
              lang,
            )}
          </strong>
        </p>
        <p className="ct-note" data-reject-design="">
          {pick(
            {
              en: `${formatNumber(d.reps, 'en')} repetitions on the ${formatNumber(d.n_rows, 'en')} applicants: a legacy policy accepts ${formatNumber(d.accept_share, 'en', { percent: true, decimals: 0 })} of ${formatNumber(d.n_dev, 'en')}, the outcomes of the rejected are hidden, each rung is fitted on what a lender would have and scored on ${formatNumber(d.n_test, 'en')} applicants nobody screened. Level bias: mean PD minus the observed default rate, in points; intervals are 95 % bootstrap intervals over the repetitions.`,
              es: `${formatNumber(d.reps, 'es')} repeticiones sobre los ${formatNumber(d.n_rows, 'es')} solicitantes: una política heredada acepta el ${formatNumber(d.accept_share, 'es', { percent: true, decimals: 0 })} de ${formatNumber(d.n_dev, 'es')}, se ocultan los resultados de los rechazados, cada peldaño se ajusta con lo que tendría un prestamista y se puntúa con ${formatNumber(d.n_test, 'es')} solicitantes que nadie filtró. Sesgo de nivel: PD media menos la tasa de incumplimiento observada, en puntos; los intervalos son intervalos de remuestreo del 95 % sobre las repeticiones.`,
            },
            lang,
          )}
        </p>
        <div className="ct-tall-only">
          <BarChart
            title={{ en: `Level bias by rung, ${regime.short_title.en.toLowerCase()}`, es: `Sesgo de nivel por peldaño, ${regime.short_title.es.toLowerCase()}` }}
            orientation="horizontal"
            height="fill"
            data={rows.map((r) => ({
              id: r.id,
              label: rungName(ri, r.id),
              value: r.bias.mean * 100,
              span: [r.bias.lo * 100, r.bias.hi * 100] as [number, number],
              tone: r.id === 'accepted-only' ? ('warn' as const) : r.id === 'oracle' ? ('neutral' as const) : ('accent' as const),
            }))}
            axis={{ label: { en: 'Level bias, points (95 % interval)', es: 'Sesgo de nivel, puntos (intervalo 95 %)' }, format: { decimals: 1 } }}
          />
        </div>
        <div>
          <table className="caos-table" data-reject-table="rungs">
            <thead>
              <tr>
                <th>{pick({ en: 'Rung', es: 'Peldaño' }, lang)}</th>
                <th>{pick({ en: 'Level bias, points', es: 'Sesgo de nivel, puntos' }, lang)}</th>
                <th>{pick({ en: 'Reduction of the bias', es: 'Reducción del sesgo' }, lang)}</th>
                <th>{pick({ en: 'AUC against accepted only', es: 'AUC frente a solo aceptados' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} data-rung={r.id} title={pick(ri.rungs.find((x) => x.id === r.id)?.what ?? { en: '', es: '' }, lang)}>
                  <td>{pick(rungName(ri, r.id), lang)}</td>
                  <td>
                    {points(r.bias.mean, lang)}
                    <span className="ct-narrow-only">{span(points(r.bias.lo, lang), points(r.bias.hi, lang))}</span>
                    <span className="ct-wide-only ct-repeated">{` (${span(points(r.bias.lo, lang), points(r.bias.hi, lang))})`}</span>
                  </td>
                  <td>
                    {r.id === 'accepted-only' ? pick({ en: 'reference', es: 'referencia' }, lang) : formatNumber(r.reduction.value, lang, { percent: true, decimals: 0 })}
                    {r.id === 'accepted-only' ? null : <span className="ct-wide-only ct-repeated">{` (${span(formatNumber(r.reduction.lo, lang, { percent: true, decimals: 0 }), formatNumber(r.reduction.hi, lang, { percent: true, decimals: 0 }))})`}</span>}
                  </td>
                  <td>
                    {r.id === 'accepted-only' ? formatNumber(r.auc.mean, lang, { decimals: 4 }) : signed(r.auc_vs_accepted_only.mean, lang)}
                    {r.id === 'accepted-only' ? null : <span className="ct-wide-only ct-repeated">{` (${span(signed(r.auc_vs_accepted_only.lo, lang), signed(r.auc_vs_accepted_only.hi, lang))})`}</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div>
          <table className="caos-table" data-reject-table="policies">
            <thead>
              <tr>
                <th>{pick({ en: 'Legacy policy', es: 'Política heredada' }, lang)}</th>
                <th>{pick({ en: 'Defaults among accepted', es: 'Incumplimiento entre aceptados' }, lang)}</th>
                <th>{pick({ en: 'Accepted-only bias, points', es: 'Sesgo de solo aceptados, puntos' }, lang)}</th>
                <th>{pick({ en: 'Best reduction', es: 'Mejor reducción' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {ri.regimes.map((g) => {
                const ao = g.rungs.find((r) => r.id === 'accepted-only');
                const fixers = g.rungs.filter((r) => r.id !== 'oracle' && r.id !== 'accepted-only');
                const top = fixers.reduce((a, b) => (b.reduction.value > a.reduction.value ? b : a), fixers[0]);
                return (
                  <tr key={g.id} data-policy={g.id} data-judged={g.id === JUDGED_POLICY ? 'true' : 'false'}>
                    <td>{pick(g.short_title, lang)}</td>
                    <td>{formatNumber(g.default_rate.accepted, lang, { percent: true, decimals: 1 })}</td>
                    <td>{ao ? `${points(ao.bias.mean, lang)} (${span(points(ao.bias.lo, lang), points(ao.bias.hi, lang))})` : ''}</td>
                    <td>{top ? `${pick(rungName(ri, top.id), lang)}, ${formatNumber(top.reduction.value, lang, { percent: true, decimals: 0 })}` : ''}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        </div>
      </div>
    </PlotCard>
  );
}
