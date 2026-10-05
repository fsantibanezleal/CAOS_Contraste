// The Impact group: what the model changes in a decision. The champion and the challenger approve the same share of
// applicants (the rail's approval rate); the bad rate and the expected loss of each follow from the committed cut-off
// curves, recomputed live; the swap sets at 80%, which need the applicants themselves, are the pipeline's. The money
// is in the case's own currency, named by the artifact (NT dollars for Taiwan, Deutsche Mark for the German twin).
import { PlotCard, Verdict, formatNumber, pick, useShellLang, useWorkbenchState } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useMemo } from 'react';
import { CHAMPION, REPLAY, atApproval, grid, interp, provenanceOf, rung, shortName, type Selection } from './model';
import { Pending } from './Pending';

/** Money in millions, so a sum of exposures reads at a glance. */
const MILLION = 1e6;

export function ImpactView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const curves = useMemo(() => {
    if (!sel) return null;
    const v = sel.data.variant;
    const x = grid(0.3, 1, 71);
    const c = v.outputs.rungs[CHAMPION].cutoff;
    const h = v.outputs.rungs[sel.challenger].cutoff;
    return { x, champion: interp(c.approval_rate, c.bad_rate, x), challenger: interp(h.approval_rate, h.bad_rate, x) };
  }, [sel]);
  if (!sel || !curves) return <Pending />;
  const v = sel.data.variant;
  const prov = provenanceOf(v.provenance.truth_status);
  const champ = atApproval(v.outputs.rungs[CHAMPION].cutoff, sel.approval);
  const chall = atApproval(v.outputs.rungs[sel.challenger].cutoff, sel.approval);
  const names = [shortName(rung(v, CHAMPION), CHAMPION), shortName(rung(v, sel.challenger), sel.challenger)];
  const better = champ.bad !== null && chall.bad !== null ? chall.bad < champ.bad : null;
  const im = v.impact;
  const currency = im.el_champion?.unit ?? '';
  const money = { en: `million ${currency}`, es: `millones de ${currency}` };
  const pairs: Array<[string, string]> = [
    ['bad_rate_champion', 'bad_rate_challenger'],
    ['el_champion', 'el_challenger'],
    ['loss_champion', 'loss_challenger'],
    ['swap_out', 'swap_in'],
    ['swap_out_bad_rate', 'swap_in_bad_rate'],
    ['min_cost_champion', 'min_cost_challenger'],
  ];
  const fmt = (key: string) => {
    const it = im[key];
    if (!it) return '-';
    if (it.unit === 'fraction') return formatNumber(it.value, lang, { percent: true, decimals: 1 });
    if (it.unit === currency) return formatNumber(it.value !== null ? it.value / MILLION : null, lang, { digits: 3 });
    return formatNumber(it.value, lang, { digits: 4 });
  };
  const unitOf = (key: string) => {
    const u = im[key]?.unit;
    if (!u || u === 'fraction') return '';
    return u === currency ? ` (${pick(money, lang)})` : ` (${u})`;
  };
  return (
    <>
      <PlotCard title={{ en: 'The decision at this approval rate', es: 'La decisión con esta tasa de aprobación' }} lane="live" provenance={prov} dataKey={stateKey}>
        <Verdict
          compact
          title={{ en: 'Who approves the better book', es: 'Quién aprueba la mejor cartera' }}
          tone={better === null ? 'neutral' : better ? 'accent' : 'neutral'}
          verdict={
            better === null
              ? { en: 'Not available at this approval rate.', es: 'No disponible con esta tasa de aprobación.' }
              : {
                  en: `Approving ${formatNumber(sel.approval, 'en', { percent: true, decimals: 0 })} of applicants: the champion's bad rate is ${formatNumber(champ.bad, 'en', { percent: true, decimals: 2 })}, the challenger's ${formatNumber(chall.bad, 'en', { percent: true, decimals: 2 })}.`,
                  es: `Aprobando el ${formatNumber(sel.approval, 'es', { percent: true, decimals: 0 })} de los solicitantes: la tasa de malos del campeón es ${formatNumber(champ.bad, 'es', { percent: true, decimals: 2 })}, la del retador ${formatNumber(chall.bad, 'es', { percent: true, decimals: 2 })}.`,
                }
          }
        />
        <table className="caos-table">
          <thead>
            <tr>
              <th className="caos-col-text">{pick({ en: "At the rail's approval rate (live)", es: 'Con la tasa de aprobación del panel (en vivo)' }, lang)}</th>
              <th>{pick(names[0], lang)}</th>
              <th>{pick(names[1], lang)}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="caos-col-text">{pick({ en: 'Bad rate among the approved', es: 'Tasa de malos entre los aprobados' }, lang)}</td>
              <td>{formatNumber(champ.bad, lang, { percent: true, decimals: 2 })}</td>
              <td>{formatNumber(chall.bad, lang, { percent: true, decimals: 2 })}</td>
            </tr>
            <tr>
              <td className="caos-col-text">
                {pick({ en: `Expected loss: LGD ${formatNumber(sel.lgd, 'en', { percent: true, decimals: 0 })} x sum of PD x EAD`, es: `Pérdida esperada: LGD ${formatNumber(sel.lgd, 'es', { percent: true, decimals: 0 })} x suma de PD x EAD` }, lang)} ({pick(money, lang)})
              </td>
              <td>{formatNumber(champ.pdEad !== null ? (champ.pdEad * sel.lgd) / MILLION : null, lang, { digits: 3 })}</td>
              <td>{formatNumber(chall.pdEad !== null ? (chall.pdEad * sel.lgd) / MILLION : null, lang, { digits: 3 })}</td>
            </tr>
            <tr>
              <td className="caos-col-text">
                {pick({ en: 'Exposure approved (EAD)', es: 'Exposición aprobada (EAD)' }, lang)} ({pick(money, lang)})
              </td>
              <td>{formatNumber(champ.ead !== null ? champ.ead / MILLION : null, lang, { digits: 3 })}</td>
              <td>{formatNumber(chall.ead !== null ? chall.ead / MILLION : null, lang, { digits: 3 })}</td>
            </tr>
          </tbody>
        </table>
      </PlotCard>
      <div className="caos-views-row" data-views="2">
        <div className="ct-col ct-share-3">
          <PlotCard
            fill
            title={{ en: 'Bad rate against approval rate', es: 'Tasa de malos contra tasa de aprobación' }}
            lane="live"
            provenance={prov}
            dataKey={stateKey}
            note={{ en: 'Approve the lowest PDs first; a lower curve is the better book at the same volume.', es: 'Aprobar primero las PD más bajas; una curva más baja es la mejor cartera al mismo volumen.' }}
          >
            <UPlotChart
              height="fill"
              x={{ values: curves.x, label: { en: 'Approval rate', es: 'Tasa de aprobación' }, format: { percent: true, decimals: 0 } }}
              y={{ label: { en: 'Bad rate among the approved', es: 'Tasa de malos entre aprobados' }, format: { percent: true, decimals: 0 } }}
              series={[
                { label: names[0], values: curves.champion, color: '--color-accent', width: 2 },
                { label: names[1], values: curves.challenger, color: '--color-magenta', width: 2 },
              ]}
              marks={[{ x: sel.approval, label: { en: 'rail', es: 'panel' } }]}
            />
          </PlotCard>
        </div>
        <div className="ct-col ct-share-2">
          <PlotCard
            fill
            title={{ en: 'At 80% approval, applicant by applicant (pipeline)', es: 'Con 80% de aprobación, solicitante por solicitante (pipeline)' }}
            lane={REPLAY}
            provenance={prov}
            dataKey={stateKey}
            note={{ en: 'Swap sets: the applicants one model approves and the other rejects. Ties broken by the raw score, so both approve the same count.', es: 'Conjuntos de intercambio: los solicitantes que un modelo aprueba y el otro rechaza. Empates resueltos por el puntaje crudo, así ambos aprueban la misma cantidad.' }}
          >
            <div className="ct-scroll">
              <table className="caos-table">
                <thead>
                  <tr>
                    <th className="caos-col-text">{pick({ en: 'Champion, then challenger', es: 'Campeón, luego retador' }, lang)}</th>
                    <th>{pick(names[0], lang)}</th>
                    <th>{pick(names[1], lang)}</th>
                  </tr>
                </thead>
                <tbody>
                  {pairs
                    .filter(([a]) => im[a])
                    .map(([a, b]) => (
                      <tr key={a}>
                        <td className="caos-col-text">
                          {pick(im[a].label, lang).replace(/ \(LGD 50%\)/, '').replace(/, (champion|campeón)$/, '')}
                          {unitOf(a)}
                        </td>
                        <td>{fmt(a)}</td>
                        <td>{fmt(b)}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </PlotCard>
        </div>
      </div>
    </>
  );
}
