// The Impact group's Capital view (CT-212 to CT-216): the IRB capital (8% of the RWA) of the champion's and the
// challenger's approved books at the rail's approval rate and LGD, under Basel III final, EU CRR3 and Basel II. The
// pipeline commits each book's capital at unit LGD along its cut-off curve; retail capital is linear in the LGD, so
// the view multiplies by the rail's LGD and interpolates at the rail's approval rate, exactly.
import { PlotCard, Verdict, formatNumber, pick, useShellLang, useWorkbenchState, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useMemo } from 'react';
import type { RungOutputs } from '../lib/contract.types';
import { CHAMPION, grid, interp, provenanceOf, rung, shortName, type Selection } from './model';
import { Pending } from './Pending';

/** Money in millions, as in the decision view. */
const MILLION = 1e6;

const REGIME: Record<string, BiText> = {
  basel3: { en: 'Basel III final', es: 'Basilea III final' },
  crr3: { en: 'EU CRR3', es: 'CRR3 de la UE' },
  basel2: { en: 'Basel II', es: 'Basilea II' },
};

const CLASS: Record<string, BiText> = {
  qrre: { en: 'Qualifying revolving retail (QRRE)', es: 'Minorista renovable calificada (QRRE)' },
  other_retail: { en: 'Other retail', es: 'Otro minorista' },
};

type Cut = RungOutputs['cutoff'];

/** The capital at unit LGD of a book at an approval rate, under one regime; null outside the committed range. */
function unitAt(cut: Cut, regime: string, share: number, transactors = false): number | null {
  const series = transactors ? cut.capital_per_lgd_transactors?.[regime] : cut.capital_per_lgd[regime];
  return series ? interp(cut.approval_rate, series, [share])[0] : null;
}

export function CapitalView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const chart = useMemo(() => {
    if (!sel) return null;
    const v = sel.data.variant;
    const x = grid(0.3, 1, 71);
    const series = (cut: Cut) => interp(cut.approval_rate, cut.capital_per_lgd.basel3, x).map((y) => (y === null ? null : (y * sel.lgd) / MILLION));
    return { x, champion: series(v.outputs.rungs[CHAMPION].cutoff), challenger: series(v.outputs.rungs[sel.challenger].cutoff) };
  }, [sel]);
  if (!sel || !chart) return <Pending />;
  const v = sel.data.variant;
  const irb = v.outputs.irb;
  const prov = provenanceOf(v.provenance.truth_status);
  const champ = v.outputs.rungs[CHAMPION].cutoff;
  const chall = v.outputs.rungs[sel.challenger].cutoff;
  const names = [shortName(rung(v, CHAMPION), CHAMPION), shortName(rung(v, sel.challenger), sel.challenger)];
  const currency = v.impact.el_champion?.unit ?? '';
  const money = (x: number | null) => formatNumber(x === null ? null : x / MILLION, lang, { digits: 3 });
  const [eadA] = interp(champ.approval_rate, champ.ead, [sel.approval]);
  const [eadB] = interp(chall.approval_rate, chall.ead, [sel.approval]);
  const rows = irb.regimes.map((r) => {
    const a = unitAt(champ, r, sel.approval);
    const b = unitAt(chall, r, sel.approval);
    return { r, a: a === null ? null : a * sel.lgd, b: b === null ? null : b * sel.lgd };
  });
  const b3 = rows.find((r) => r.r === 'basel3');
  const diff = b3 && b3.a && b3.b !== null ? b3.b / b3.a - 1 : null;
  const cell = (c: number | null, e: number | null) =>
    `${money(c)} (${c !== null && e ? formatNumber(c / e, lang, { percent: true, decimals: 2 }) : '-'})`;
  const belowFloor = sel.lgd < irb.lgd_floor_basel3 - 1e-12;
  const floorText = formatNumber(irb.lgd_floor_basel3, lang, { percent: true, decimals: 0 });
  // the six-month full payers as transactors, at the rail's approval rate, for both books under Basel III
  const effect = (cut: Cut): number | null => {
    const rev = unitAt(cut, 'basel3', sel.approval);
    const trn = unitAt(cut, 'basel3', sel.approval, true);
    return irb.six_month_full_payers !== null && rev && trn !== null ? 1 - trn / rev : null;
  };
  const effects = [effect(champ), effect(chall)];
  const effectText = (e: number | null, l: 'en' | 'es') =>
    e === null ? '-' : e < 5e-7 ? (l === 'en' ? 'unchanged' : 'sin cambio') : `${formatNumber(e, l, { percent: true, decimals: 4 })} ${l === 'en' ? 'lower' : 'menos'}`;
  const payers = irb.six_month_full_payers;
  const sensitivity = (l: 'en' | 'es'): string =>
    payers === null || effects.every((e) => e === null)
      ? ''
      : l === 'en'
        ? ` The ${formatNumber(payers, 'en')} six-month full payers as transactors (PD floor 0.05% instead of 0.1%): ${names[0].en} ${effectText(effects[0], 'en')}, ${names[1].en} ${effectText(effects[1], 'en')}.`
        : ` Los ${formatNumber(payers, 'es')} que pagaron todo los seis meses como transaccionales (piso de PD 0,05% en vez de 0,1%): ${names[0].es} ${effectText(effects[0], 'es')}, ${names[1].es} ${effectText(effects[1], 'es')}.`;
  // the pipeline's books at exactly the committed approval rate, applicant by applicant (ties broken by the raw score)
  const exactA = v.impact.capital_champion?.value ?? null;
  const exactB = v.impact.capital_challenger?.value ?? null;
  const exactAt = v.impact.approval_rate?.value ?? null;
  const lgdText = { en: formatNumber(sel.lgd, 'en', { percent: true, decimals: 0 }), es: formatNumber(sel.lgd, 'es', { percent: true, decimals: 0 }) };
  const approvalText = { en: formatNumber(sel.approval, 'en', { percent: true, decimals: 0 }), es: formatNumber(sel.approval, 'es', { percent: true, decimals: 0 }) };
  const klass = CLASS[irb.asset_class] ?? { en: irb.asset_class, es: irb.asset_class };
  // the numbers at their own height across the instrument, the curve filling the rest (as the Decision view)
  return (
    <>
      <PlotCard
        title={{ en: `IRB capital at ${approvalText.en} approved, LGD ${lgdText.en}`, es: `Capital IRB con ${approvalText.es} aprobado, LGD ${lgdText.es}` }}
        lane="live"
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: `${pick(klass, 'en')}; EAD ${irb.ead.en}; capital is 8% of the RWA, in million ${currency} (share of EAD).${irb.revolvers_only ? ' Every card is a revolver: a Basel III transactor needs twelve months of repayment history (BCBS d424, paragraphs 56 and 25), and the data hold six.' : ''}`,
          es: `${pick(klass, 'es')}; EAD ${irb.ead.es}; el capital es el 8% de los APR, en millones de ${currency} (fracción de la EAD).${irb.revolvers_only ? ' Toda tarjeta es renovable: una transaccional de Basilea III requiere doce meses de historia de pagos (BCBS d424, párrafos 56 y 25), y los datos tienen seis.' : ''}`,
        }}
      >
        <div className="ct-row">
          <div className="ct-share-3">
            <table className="caos-table" data-table="capital">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Regime', es: 'Régimen' }, lang)}</th>
                  <th>{pick(names[0], lang)}</th>
                  <th>{pick(names[1], lang)}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.r}>
                    <td className="ct-text">{pick(REGIME[r.r] ?? { en: r.r, es: r.r }, lang)}</td>
                    <td>{cell(r.a, eadA)}</td>
                    <td>{cell(r.b, eadB)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="ct-share-2 ct-stack-natural">
            <Verdict
              compact
              title={{ en: 'What the model choice costs', es: 'Lo que cuesta la elección del modelo' }}
              tone="accent"
              verdict={{
                en: diff === null ? 'Not available at this approval rate.' : `${names[1].en}: ${formatNumber(Math.abs(diff), 'en', { percent: true, decimals: 1 })} ${diff >= 0 ? 'more' : 'less'} Basel III capital than ${names[0].en}.`,
                es: diff === null ? 'No disponible con esta tasa de aprobación.' : `${names[1].es}: un ${formatNumber(Math.abs(diff), 'es', { percent: true, decimals: 1 })} ${diff >= 0 ? 'más' : 'menos'} de capital de Basilea III que ${names[0].es}.`,
              }}
            />
            {exactA !== null && exactB !== null && exactAt !== null && (
              <p className="ct-note" data-exact="pipeline">
                {pick(
                  {
                    en: `Exactly ${formatNumber(exactAt, 'en', { percent: true, decimals: 0 })} approved, applicant by applicant (LGD 50%): ${money(exactA)} and ${money(exactB)}, ${formatNumber(Math.abs(exactB / exactA - 1), 'en', { percent: true, decimals: 1 })} ${exactB >= exactA ? 'more' : 'less'}; the live figures interpolate the cut-off curve.`,
                    es: `Exactamente ${formatNumber(exactAt, 'es', { percent: true, decimals: 0 })} aprobado, solicitante a solicitante (LGD 50%): ${money(exactA)} y ${money(exactB)}, un ${formatNumber(Math.abs(exactB / exactA - 1), 'es', { percent: true, decimals: 1 })} ${exactB >= exactA ? 'más' : 'menos'}; las cifras en vivo interpolan la curva de corte.`,
                  },
                  lang,
                )}
              </p>
            )}
            {belowFloor && (
              <p className="ct-note" data-lgd-floor="below">
                {pick(
                  {
                    en: `The rail's LGD is below the Basel III input floor of ${floorText} for this class (BCBS d424, IRB paragraph 121): a bank's Basel III capital would use ${floorText}. Basel II has none; CRR3's (Article 164(4)) is not stated until read.`,
                    es: `La LGD del panel está bajo el piso de Basilea III de ${floorText} para esta clase (BCBS d424, párrafo 121 del IRB): el capital de Basilea III de un banco usaría ${floorText}. Basilea II no tiene; el de CRR3 (artículo 164(4)) no se indica hasta leerlo.`,
                  },
                  lang,
                )}
              </p>
            )}
          </div>
        </div>
      </PlotCard>
      <PlotCard
        fill
        title={{ en: 'Capital against the approval rate, Basel III', es: 'Capital según la tasa de aprobación, Basilea III' }}
        lane="live"
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: `At the rail's LGD, in million ${currency}.${sensitivity('en')}`,
          es: `A la LGD del panel, en millones de ${currency}.${sensitivity('es')}`,
        }}
      >
        <UPlotChart
          height="fill"
          x={{ values: chart.x, label: { en: 'Approval rate', es: 'Tasa de aprobación' }, format: { percent: true, decimals: 0 } }}
          y={{ label: { en: `Capital (million ${currency})`, es: `Capital (millones de ${currency})` }, format: { digits: 3 } }}
          series={[
            { label: names[0], values: chart.champion, color: '--color-accent', width: 2 },
            { label: names[1], values: chart.challenger, color: '--color-magenta', width: 2, dash: [6, 4] },
          ]}
          marks={[{ x: sel.approval, label: { en: 'rail', es: 'panel' } }]}
        />
      </PlotCard>
    </>
  );
}
