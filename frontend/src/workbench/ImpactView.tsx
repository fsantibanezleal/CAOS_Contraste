// The Impact group: what the model changes in a decision. The champion and the challenger approve the same share of
// applicants (the rail's approval rate); the bad rate and the expected loss of each follow from the committed cut-off
// curves, recomputed live; the swap sets at 80%, which need the applicants themselves, are the pipeline's. The money
// is in the case's own currency, named by the artifact (NT dollars for Taiwan, Deutsche Mark for the German twin).
import { PlotCard, SubTabs, Verdict, ViewsRow, formatNumber, pick, useShellLang, useWorkbenchState } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useMemo } from 'react';
import { CapitalView } from './CapitalView';
import { CHAMPION, REPLAY, atApproval, grid, interp, provenanceOf, rung, shortName, type Selection } from './model';
import { Pending } from './Pending';

/** The Impact group: the decision (bad rate and expected loss) and the capital (CT-212 to CT-216). */
export function ImpactGroup({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const tabs = [
    { id: 'decision', label: pick({ en: 'Decision', es: 'Decisión' }, lang), content: <ImpactView sel={sel} /> },
    { id: 'capital', label: pick({ en: 'Capital', es: 'Capital' }, lang), content: <CapitalView sel={sel} /> },
  ];
  return <SubTabs ariaLabel={pick({ en: 'Views of the impact', es: 'Vistas del impacto' }, lang)} tabs={tabs} />;
}

/** Money in millions, so a sum of exposures reads at a glance. */
const MILLION = 1e6;

/** The pipeline's rows at 80% approval, in the champion-then-challenger pairs the table shows. */
const PAIRS: Array<{ a: string; b: string; label: { en: string; es: string } }> = [
  { a: 'bad_rate_champion', b: 'bad_rate_challenger', label: { en: 'Bad rate', es: 'Tasa de malos' } },
  { a: 'el_champion', b: 'el_challenger', label: { en: 'Expected loss', es: 'Pérdida esperada' } },
  { a: 'loss_champion', b: 'loss_challenger', label: { en: 'Realised loss', es: 'Pérdida realizada' } },
  { a: 'swap_out', b: 'swap_in', label: { en: 'Approved by this model only', es: 'Aprobados solo por este modelo' } },
  { a: 'swap_out_bad_rate', b: 'swap_in_bad_rate', label: { en: 'Their bad rate', es: 'Su tasa de malos' } },
  { a: 'min_cost_champion', b: 'min_cost_challenger', label: { en: 'Least cost (German matrix)', es: 'Costo mínimo (matriz alemana)' } },
];

export function ImpactView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const curves = useMemo(() => {
    if (!sel) return null;
    const v = sel.data.variant;
    const x = grid(0.3, 1, 71);
    const c = v.outputs.rungs[CHAMPION].cutoff;
    const h = v.outputs.rungs[sel.challenger].cutoff;
    const el = (cut: typeof c) => interp(cut.approval_rate, cut.pd_ead, x).map((y) => (y === null ? null : (y * sel.lgd) / MILLION));
    return { x, champion: interp(c.approval_rate, c.bad_rate, x), challenger: interp(h.approval_rate, h.bad_rate, x), elChampion: el(c), elChallenger: el(h) };
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
  const fmt = (key: string) => {
    const it = im[key];
    if (!it) return '-';
    if (it.unit === 'fraction') return formatNumber(it.value, lang, { percent: true, decimals: 1 });
    if (it.unit === currency) return formatNumber(it.value !== null ? it.value / MILLION : null, lang, { digits: 3 });
    return formatNumber(it.value, lang, { digits: 4 });
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
      <ViewsRow shares={[3, 2]}>
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
        <>
          <PlotCard
            fill
            title={{ en: 'At 80% approval, applicant by applicant (pipeline)', es: 'Con 80% de aprobación, solicitante por solicitante (pipeline)' }}
            lane={REPLAY}
            provenance={prov}
            dataKey={stateKey}
            note={{ en: `Swap sets: the applicants one model approves and the other rejects; ties broken by the raw score, so both approve the same count. Losses at LGD 50%, in ${pick(money, 'en')}.`, es: `Conjuntos de intercambio: los solicitantes que un modelo aprueba y el otro rechaza; empates resueltos por el puntaje crudo, así ambos aprueban la misma cantidad. Pérdidas con LGD 50%, en ${pick(money, 'es')}.` }}
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
                  {PAIRS.filter((r) => im[r.a]).map((r) => (
                    <tr key={r.a} title={pick(im[r.a].label, lang)}>
                      <td className="caos-col-text">{pick(r.label, lang)}</td>
                      <td>{fmt(r.a)}</td>
                      <td>{fmt(r.b)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </PlotCard>
          <div className="ct-tall-only">
            <PlotCard
              fill
              title={{ en: 'Expected loss against approval rate', es: 'Pérdida esperada contra tasa de aprobación' }}
              lane="live"
              provenance={prov}
              dataKey={stateKey}
              note={{ en: `LGD from the rail (${formatNumber(sel.lgd, 'en', { percent: true, decimals: 0 })}) times the sum of PD x EAD of the approved, in ${pick(money, 'en')}.`, es: `LGD del panel (${formatNumber(sel.lgd, 'es', { percent: true, decimals: 0 })}) por la suma de PD x EAD de los aprobados, en ${pick(money, 'es')}.` }}
            >
              <UPlotChart
                height="fill"
                x={{ values: curves.x, label: { en: 'Approval rate', es: 'Tasa de aprobación' }, format: { percent: true, decimals: 0 } }}
                y={{ label: { en: 'Expected loss', es: 'Pérdida esperada' }, unit: money, format: { digits: 3 } }}
                series={[
                  { label: names[0], values: curves.elChampion, color: '--color-accent', width: 2 },
                  { label: names[1], values: curves.elChallenger, color: '--color-magenta', width: 2 },
                ]}
                marks={[{ x: sel.approval, label: { en: 'rail', es: 'panel' } }]}
              />
            </PlotCard>
          </div>
        </>
      </ViewsRow>
    </>
  );
}
