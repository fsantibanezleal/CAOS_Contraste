// C12's regulatory group: the regulatory measures against the modelled ones (SA-CCR EAD against alpha times EEPE, BA-CVA
// capital against the CVA, the GIRR delta charge with and without the division by sqrt(2)); the live SA-CCR and the live
// BA-CVA, TypeScript ports of CRE52 and MAR50 held to the document's blocks by a parity test at 1e-9 relative; and the
// GIRR delta charge by tenor. The live lines are computed by the ports on the controls of the rail and are labelled
// live; everything else is a field of the document. A convention carries its "convention" label.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable } from '../c06/format';
import { useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { rangeText } from '../c08/words';
import { useMedia } from '../../lib/useMedia';
import { Fragment } from 'react';
import { BA_CVA_DS, SECTORS, baCvaMismatches, riskWeight } from './bacva';
import { saCcr, saCcrInputFrom, saCcrMismatches } from './saccr';
import { NOT_SWAP, NumbersCard, SHARE, TallTables, UnavailableCard, cell, digits, years, DEFS_STYLE, Nw } from './C12Common';
import { RATING_SHORT, RATING_TEXT, SECTOR_TEXT, amount, axisOf, collateralRange, committedCollateral, fitOf, liveBaCva, liveSaCcr, outputsOf, text, type C12Sel } from './selection';
import { axisScale } from '../c06/format';

/** The regulatory measures of the document beside the modelled ones, in USD. */
export function ComparisonView({ sel }: { sel: C12Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'Regulatory against modelled', es: 'Regulatorio contra modelado' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SWAP} />;
  const r = o.regulatory_comparison;
  const g = o.girr;
  const bars = [
    { id: 'ead', label: { en: 'SA-CCR EAD', es: 'EAD SA-CCR' } as BiText, value: r.sa_ccr_ead.amount, tone: 'accent' as const },
    { id: 'imm', label: { en: 'Alpha times EEPE (IMM)', es: 'Alfa por EEPE (IMM)' } as BiText, value: r.alpha_times_eepe.amount, tone: 'good' as const },
    { id: 'ba', label: { en: 'BA-CVA capital', es: 'Capital BA-CVA' } as BiText, value: o.ba_cva.capital.amount, tone: 'accent' as const },
    { id: 'cva', label: { en: 'CVA of the model', es: 'CVA del modelo' } as BiText, value: o.cva_dva.cva.amount, tone: 'good' as const },
    { id: 'girr', label: { en: 'GIRR delta, divided by sqrt(2)', es: 'GIRR delta, dividido por raíz de 2' } as BiText, value: g.delta_charge.amount, tone: 'accent' as const },
    { id: 'girr-u', label: { en: 'GIRR delta, undivided', es: 'GIRR delta, sin dividir' } as BiText, value: g.delta_charge_undivided.amount, tone: 'neutral' as const },
  ];
  const axis = axisOf(bars.map((b) => b.value));
  const unit = pick(axis.unit, lang);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'The regulatory measure is a supervisory formula (SA-CCR for the exposure, BA-CVA for the CVA risk, the sensitivities-based delta charge for the rate risk); the modelled one is the simulation of the case (alpha 1.4 times the effective EPE, the discounted CVA). Blue bars are regulatory, green ones modelled. The division of the GIRR risk weights by sqrt(2) is the bank\'s discretion for a specified currency (MAR21.44) and a convention of the case; the undivided charge is shown beside it.',
          es: 'La medida regulatoria es una fórmula supervisora (SA-CCR para la exposición, BA-CVA para el riesgo de CVA, el cargo delta del método basado en sensibilidades para el riesgo de tasa); la modelada es la simulación del caso (alfa 1,4 por la EPE efectiva, el CVA descontado). Las barras azules son regulatorias, las verdes modeladas. La división de los ponderadores GIRR por raíz de 2 es una opción del banco para una moneda especificada (MAR21.44) y una convención del caso; el cargo sin dividir se muestra al lado.',
        }}
      >
        <TallTables>
        <ChartOverTable
          chartMin="clamp(11rem, 20rem - 15vw, 17rem)"
          chart={
            <BarChart
              title={{ en: 'Regulatory and modelled measures', es: 'Medidas regulatorias y modeladas' }}
              height="fill"
              orientation="horizontal"
              data={bars.map((b) => ({ ...b, value: b.value / axis.div }))}
              axis={{ label: { en: `Amount (${pick(axis.unit, 'en')})`, es: `Monto (${pick(axis.unit, 'es')})` }, format: { digits: 4 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c12-regulatory">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Question', es: 'Pregunta' }, lang)}</th>
                <th>{pick({ en: 'Regulatory (USD)', es: 'Regulatorio (USD)' }, lang)}</th>
                <th>{pick({ en: 'Modelled (USD)', es: 'Modelado (USD)' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              <tr data-row="ead">
                <td className="ct-text">{pick({ en: 'Exposure at default: SA-CCR against alpha times EEPE', es: 'Exposición al incumplimiento: SA-CCR contra alfa por EEPE' }, lang)}</td>
                <td>{cell(r.sa_ccr_ead.amount, lang)}</td>
                <td>{cell(r.alpha_times_eepe.amount, lang)}</td>
              </tr>
              <tr data-row="ratio">
                <td className="ct-text">{pick({ en: 'SA-CCR over alpha times EEPE', es: 'SA-CCR sobre alfa por EEPE' }, lang)}</td>
                <td colSpan={2}>{formatNumber(r.sa_ccr_over_alpha_eepe, lang, { digits: 4 })}</td>
              </tr>
              <tr data-row="stressed">
                <td className="ct-text">{pick({ en: `Stressed effective EPE, ${r.stressed.window_start} to ${r.stressed.window_end} (${r.stressed.label === 'convention' ? 'convention' : r.stressed.label}; ${r.stressed.paragraph})`, es: `EPE efectiva en estrés, ${r.stressed.window_start} a ${r.stressed.window_end} (${r.stressed.label === 'convention' ? 'convención' : r.stressed.label}; ${rangeText(r.stressed.paragraph, 'es')})` }, lang)}</td>
                <td data-na="true">{formatNumber(null, lang)}</td>
                <td data-stressed-epe={r.stressed.effective_epe.amount}>{cell(r.stressed.effective_epe.amount, lang)}</td>
              </tr>
              <tr data-row="spread">
                <td className="ct-text">{pick({ en: 'HQM spread in the stress window: start and peak', es: 'Spread HQM en la ventana de estrés: inicio y máximo' }, lang)}</td>
                <td colSpan={2} data-spread-rose={String(r.stressed.spread_rose)}>{`${SHARE(r.stressed.hqm_spread_start, lang)} / ${SHARE(r.stressed.hqm_spread_peak, lang)} (${r.stressed.spread_rose ? pick({ en: 'it rose', es: 'subió' }, lang) : pick({ en: 'it did not rise: the window is not a stress window', es: 'no subió: la ventana no es de estrés' }, lang)})`}</td>
              </tr>
              <tr data-row="cva">
                <td className="ct-text">{pick({ en: 'CVA risk: BA-CVA capital against the CVA', es: 'Riesgo de CVA: capital BA-CVA contra el CVA' }, lang)}</td>
                <td>{cell(o.ba_cva.capital.amount, lang)}</td>
                <td>{cell(o.cva_dva.cva.amount, lang)}</td>
              </tr>
              <tr data-row="girr">
                <td className="ct-text">{pick({ en: 'Rate risk: GIRR delta charge, divided by sqrt(2) (a convention) and undivided', es: 'Riesgo de tasa: cargo delta GIRR, dividido por raíz de 2 (una convención) y sin dividir' }, lang)}</td>
                <td>{`${cell(g.delta_charge.amount, lang)} / ${cell(g.delta_charge_undivided.amount, lang)}`}</td>
                <td data-na="true">{formatNumber(null, lang)}</td>
              </tr>
            </tbody>
          </table>
          <p className="ct-note">{pick({ en: `The axis is in ${unit}; the table keeps the whole amounts. Alpha ${r.alpha} (${r.alpha_paragraph}); effective maturity ${years(r.effective_maturity_years, 'en')} years.`, es: `El eje está en ${unit}; la tabla guarda los montos completos. Alfa ${formatNumber(r.alpha, 'es', { digits: 4 })} (${r.alpha_paragraph}); vencimiento efectivo ${years(r.effective_maturity_years, 'es')} años.` }, lang)}</p>
        </ChartOverTable>
        </TallTables>
      </PlotCard>
    </ViewsRow>
  );
}

const PARITY_TEXT = {
  match: { en: 'The live port reproduces the committed block of the document at 1e-9 relative.', es: 'La réplica en vivo reproduce el bloque del documento a 1e-9 relativo.' },
  moved: { en: 'A control moved the inputs away from the document\'s: the live values are the port\'s own and the committed column is the document\'s.', es: 'Un control movió los insumos fuera de los del documento: los valores en vivo son los de la réplica y la columna del documento es la comprometida.' },
  mismatch: { en: 'The live port departs from the committed block of the document:', es: 'La réplica en vivo difiere del bloque comprometido del documento:' },
} as const;

/** The live SA-CCR: EAD against the collateral held, the trades and the hedging sets, live and committed. */
export function SaCcrView({ sel }: { sel: C12Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The live SA-CCR', es: 'El SA-CCR en vivo' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SWAP} />;
  const sa = o.sa_ccr;
  const committed = committedCollateral(o);
  const c = sel.collateral ?? committed;
  const live = liveSaCcr(o, sel.collateral);
  if (!live) return <UnavailableCard sel={sel} title={title} reason={NOT_SWAP} />;
  const moved = sel.collateral !== null && sel.collateral !== committed;
  const mism = moved ? [] : saCcrMismatches(live, sa);
  const state = moved ? 'moved' : mism.length ? 'mismatch' : 'match';
  const range = collateralRange(o);
  const xmin = range.min * 1000;
  const xmax = range.max * 1000;
  const xs = Array.from({ length: 41 }, (_, i) => xmin + (i / 40) * (xmax - xmin));
  const input = saCcrInputFrom(sa);
  const sweep = xs.map((x) => saCcr({ ...input, c: x }));
  const ax = axisScale(Math.max(xmax, -xmin), 'USD');
  const ay = axisOf(sweep.flatMap((s) => [s.ead, 1.4 * s.rc, 1.4 * s.pfe]));
  const clamp = (x: number) => Math.min(Math.max(x, xmin), xmax) / ax.div;
  const marks = [
    { x: clamp(c), label: { en: `Collateral in focus: ${formatNumber(clamp(c), 'en', { digits: 4 })} ${pick(ax.unit, 'en')}`, es: `Colateral en foco: ${formatNumber(clamp(c), 'es', { digits: 4 })} ${pick(ax.unit, 'es')}` } },
    ...(moved ? [{ x: clamp(committed), label: { en: 'Committed collateral', es: 'Colateral del documento' } }] : []),
  ];
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={title}
        {...card}
        lane="live"
        note={{
          en: `EAD = 1.4 (RC + PFE) (CRE52.1). The port computes the interest rate class of CRE52 on the swaps of the book: supervisory duration, delta, maturity factor, the three maturity buckets and the offset formula of CRE52.57, the multiplier with its 5 percent floor. The other four asset classes hold no trade here. Move the collateral held: the replacement cost falls to its floor (zero without a CSA; under one, the threshold plus the minimum transfer amount less the independent amount) and the multiplier falls with the over-collateralisation.`,
          es: `EAD = 1,4 (RC + PFE) (CRE52.1). La réplica calcula la clase de tasa de interés de CRE52 sobre los swaps de la cartera: duración supervisora, delta, factor de vencimiento, los tres tramos de vencimiento y la fórmula de compensación de CRE52.57, el multiplicador con su piso de 5 por ciento. Las otras cuatro clases de activos no tienen operaciones aquí. Mueva el colateral mantenido: el costo de reemplazo baja a su piso (cero sin CSA; con uno, el umbral más el monto mínimo de transferencia menos el monto independiente) y el multiplicador baja con la sobrecolateralización.`,
        }}
      >
                    <UPlotChart
              height="fill"
              x={{ values: xs.map((x) => x / ax.div), label: { en: `Collateral held (${pick(ax.unit, 'en')})`, es: `Colateral mantenido (${pick(ax.unit, 'es')})` }, format: { digits: 4 } }}
              y={{ label: { en: `EAD and its parts (${pick(ay.unit, 'en')})`, es: `EAD y sus partes (${pick(ay.unit, 'es')})` }, format: { digits: 4 } }}
              series={[
                { label: { en: 'EAD', es: 'EAD' }, values: sweep.map((s) => s.ead / ay.div), color: '--color-accent', width: 2.8 },
                { label: { en: 'Alpha times RC', es: 'Alfa por RC' }, values: sweep.map((s) => (1.4 * s.rc) / ay.div), color: '--color-warn', width: 1.8, dash: [6, 3] },
                { label: { en: 'Alpha times PFE', es: 'Alfa por PFE' }, values: sweep.map((s) => (1.4 * s.pfe) / ay.div), color: '--color-good', width: 1.8, dash: [2, 3] },
              ]}
              marks={marks}
            />
      </PlotCard>
      <NumbersCard card={card}>
          <p className="ct-note" data-parity={state} data-live-ead={live.ead} data-committed-ead={sa.ead.amount}>
            {pick(PARITY_TEXT[state], lang)}
            {state === 'mismatch' ? ` ${mism.join('; ')}` : ''}
            {live.rc === 0 ? ` ${pick({ en: 'With RC = 0 the EAD is alpha times the PFE, so the PFE line lies under the EAD line.', es: 'Con RC = 0 el EAD es alfa por el PFE, así que la línea del PFE queda bajo la del EAD.' }, lang)}` : ''}
          </p>
          <table className="caos-table ct-wrap-head" data-table="c12-saccr-chain">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Step', es: 'Paso' }, lang)}</th>
                <th>{pick({ en: 'Live (USD)', es: 'En vivo (USD)' }, lang)}</th>
                <th>{pick({ en: 'Committed (USD)', es: 'Documento (USD)' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {[
                { id: 'rc', label: { en: 'RC, replacement cost', es: 'RC, costo de reemplazo' }, live: live.rc, doc: sa.rc.amount },
                { id: 'addon', label: { en: 'Aggregate add-on', es: 'Complemento agregado' }, live: live.addOnAggregate, doc: sa.addon_aggregate.amount },
                { id: 'multiplier', label: { en: 'Multiplier (unitless)', es: 'Multiplicador (sin unidad)' }, live: live.multiplier, doc: sa.multiplier },
                { id: 'pfe', label: { en: 'PFE, multiplier times add-on', es: 'PFE, multiplicador por complemento' }, live: live.pfe, doc: sa.pfe.amount },
                { id: 'ead', label: { en: 'EAD, 1.4 (RC + PFE)', es: 'EAD, 1,4 (RC + PFE)' }, live: live.ead, doc: sa.ead.amount },
              ].map((r) => (
                <tr key={r.id} data-step={r.id}>
                  <td className="ct-text">{pick(r.label, lang)}</td>
                  <td>{r.id === 'multiplier' ? digits(r.live, lang) : cell(r.live, lang)}</td>
                  <td>{r.id === 'multiplier' ? digits(r.doc, lang) : cell(r.doc, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head" data-table="c12-saccr-trades">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Swap', es: 'Swap' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Bucket', es: 'Tramo' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Duration', es: 'Duración' }, lang)}</th>
                <th>{pick({ en: 'Effective notional, live (USD)', es: 'Nocional efectivo, en vivo (USD)' }, lang)}</th>
                <th>{pick({ en: 'Committed (USD)', es: 'Documento (USD)' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {sa.trades.map((t) => {
                const l = live.trades.find((x) => x.tradeId === t.trade_id);
                return (
                  <tr key={t.trade_id} data-trade={t.trade_id}>
                    <td className="ct-text">{t.trade_id}</td>
                    <td className="ct-text">{l?.bucket ?? t.bucket}</td>
                    <td className="ct-wide-only">{digits(l?.supervisoryDuration ?? null, lang)}</td>
                    <td>{cell(l?.effectiveNotional ?? null, lang)}</td>
                    <td>{cell(t.effective_notional, lang)}</td>
                  </tr>
                );
              })}
              {live.hedgingSets.map((h) => (
                <tr key={h.hedgingSet} data-hedging-set={h.hedgingSet}>
                  <td className="ct-text" colSpan={3}>{pick({ en: `Hedging set ${h.hedgingSet}: effective notional after the offset formula of CRE52.57 (the add-on is 0.5 percent of it)`, es: `Conjunto de cobertura ${h.hedgingSet}: nocional efectivo tras la fórmula de compensación de CRE52.57 (el complemento es 0,5 por ciento de él)` }, lang)}</td>
                  <td>{cell(h.effectiveNotional, lang)}</td>
                  <td>{cell(sa.hedging_sets.find((x) => x.hedging_set === h.hedgingSet)?.effective_notional ?? null, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
      </NumbersCard>
    </ViewsRow>
  );
}

/** The live BA-CVA: the capital by sector at the rating class in focus, with the live EAD of the SA-CCR, and the counterparty's chain. */
export function BaCvaView({ sel }: { sel: C12Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The live BA-CVA', es: 'El BA-CVA en vivo' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SWAP} />;
  const sa = liveSaCcr(o, sel.collateral);
  const ba = liveBaCva(o, sa?.ead ?? null, sel.sector, sel.rating);
  const cp = o.ba_cva.counterparties[0];
  if (!sa || !ba || !cp) return <UnavailableCard sel={sel} title={title} reason={NOT_SWAP} />;
  const committed = o.ba_cva;
  const moved = (sel.collateral !== null && sel.collateral !== committedCollateral(o)) || sel.sector !== cp.sector || sel.rating !== cp.rating_class;
  const mism = moved ? [] : baCvaMismatches(ba, committed);
  const state = moved ? 'moved' : mism.length ? 'mismatch' : 'match';
  const bySector = SECTORS.map((s) => ({ id: s, capital: liveBaCva(o, sa.ead, s, sel.rating)?.capital ?? null }));
  const axis = axisOf(bySector.map((b) => b.capital));
  const unit = pick(axis.unit, lang);
  const cap = amount(ba.capital);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        lane="live"
        note={{
          en: `Reduced BA-CVA (MAR50.14 to MAR50.16): capital = 0.65 K, K = sqrt((rho sum SCVA)^2 + (1 - rho^2) sum SCVA^2) with rho 50 percent, SCVA = (1 / alpha) RW M EAD DF with alpha 1.4. The EAD is the live SA-CCR of the netting set. The bars give the capital under every sector of MAR50.16 Table 1 at the rating class in focus. ${pick(committed.limit, 'en')} The materiality threshold of MAR50.9 and the hedges of the full version are not modelled: the book holds none.`,
          es: `BA-CVA reducido (MAR50.14 a MAR50.16): capital = 0,65 K, K = raíz((rho suma SCVA)^2 + (1 - rho^2) suma SCVA^2) con rho de 50 por ciento, SCVA = (1 / alfa) RW M EAD DF con alfa 1,4. La EAD es el SA-CCR en vivo del conjunto de neteo. Las barras dan el capital bajo cada sector de la Tabla 1 de MAR50.16 en la clase de calificación en foco. ${pick(committed.limit, 'es')} El umbral de materialidad de MAR50.9 y las coberturas de la versión completa no se modelan: la cartera no tiene ninguna.`,
        }}
      >
        <ChartOverTable
          chartMin="clamp(15rem, 30rem - 20vw, 22rem)"
          chart={
            <BarChart
              title={{ en: 'BA-CVA capital by sector', es: 'Capital BA-CVA por sector' }}
              height="fill"
              orientation="horizontal"
              data={bySector.map((b) => ({ id: b.id, label: text(SECTOR_TEXT, b.id), value: b.capital === null ? null : b.capital / axis.div, tone: 'accent' as const, highlight: b.id === sel.sector }))}
              axis={{ label: { en: `Capital, ${pick(text(RATING_TEXT, sel.rating), 'en').toLowerCase()} (${pick(axis.unit, 'en')})`, es: `Capital, ${pick(text(RATING_TEXT, sel.rating), 'es').toLowerCase()} (${pick(axis.unit, 'es')})` }, format: { digits: 4 } }}
            />
          }
        >
          <p className="ct-note" data-parity={state} data-live-capital={ba.capital} data-committed-capital={committed.capital.amount}>
            {pick(PARITY_TEXT[state], lang)}
            {state === 'mismatch' ? ` ${mism.join('; ')}` : ''}
          </p>
          <table className="caos-table ct-wrap-head" data-table="c12-bacva">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Step', es: 'Paso' }, lang)}</th>
                <th>{pick({ en: 'Live', es: 'En vivo' }, lang)}</th>
                <th>{pick({ en: 'Committed', es: 'Documento' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              <tr data-step="sector">
                <td className="ct-text">{pick({ en: 'Sector and rating class', es: 'Sector y clase de calificación' }, lang)}</td>
                <td className="ct-text">{`${pick(text(SECTOR_TEXT, sel.sector), lang)}, ${pick(text(RATING_SHORT, sel.rating), lang)}`}</td>
                <td className="ct-text">{`${pick(text(SECTOR_TEXT, cp.sector), lang)}, ${pick(text(RATING_SHORT, cp.rating_class), lang)}`}</td>
              </tr>
              <tr data-step="rw">
                <td className="ct-text">{pick({ en: 'Risk weight (MAR50.16 Table 1)', es: 'Ponderador (Tabla 1 de MAR50.16)' }, lang)}</td>
                <td>{SHARE(riskWeight(sel.sector, sel.rating), lang)}</td>
                <td>{SHARE(cp.risk_weight, lang)}</td>
              </tr>
              <tr data-step="ead">
                <td className="ct-text">{pick({ en: 'EAD of the netting set (USD)', es: 'EAD del conjunto de neteo (USD)' }, lang)}</td>
                <td>{cell(sa.ead, lang)}</td>
                <td>{cell(cp.ead.amount, lang)}</td>
              </tr>
              <tr data-step="m">
                <td className="ct-text">{pick({ en: 'Maturity M (years) and discount factor', es: 'Vencimiento M (años) y factor de descuento' }, lang)}</td>
                <td>{`${years(cp.m_years, lang)} / ${digits(cp.discount_factor, lang)}`}</td>
                <td>{`${years(cp.m_years, lang)} / ${digits(cp.discount_factor, lang)}`}</td>
              </tr>
              <tr data-step="scva">
                <td className="ct-text">{pick({ en: 'SCVA (USD)', es: 'SCVA (USD)' }, lang)}</td>
                <td>{cell(ba.scva[0], lang)}</td>
                <td>{cell(cp.scva, lang)}</td>
              </tr>
              <tr data-step="k">
                <td className="ct-text">{pick({ en: 'K reduced (USD)', es: 'K reducido (USD)' }, lang)}</td>
                <td>{cell(ba.kReduced, lang)}</td>
                <td>{cell(committed.k_reduced, lang)}</td>
              </tr>
              <tr data-step="capital">
                <td className="ct-text"><strong>{pick({ en: `Capital, DS ${formatNumber(BA_CVA_DS, 'en', { digits: 4 })} K (USD)`, es: `Capital, DS ${formatNumber(BA_CVA_DS, 'es', { digits: 4 })} K (USD)` }, lang)}</strong></td>
                <td>{cell(ba.capital, lang)}</td>
                <td>{cell(committed.capital.amount, lang)}</td>
              </tr>
            </tbody>
          </table>
          <p className="ct-note">{pick({ en: `The axis is in ${unit}; the live capital is ${formatNumber(cap.value, 'en', cap.format)} ${pick(cap.unit, 'en')}.`, es: `El eje está en ${unit}; el capital en vivo es ${formatNumber(cap.value, 'es', cap.format)} ${pick(cap.unit, 'es')}.` }, lang)}</p>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The GIRR delta charge by tenor: the sensitivities, the risk weights of MAR21.42, the weighted sensitivities and the three correlation scenarios. */
export function GirrView({ sel }: { sel: C12Sel | null }) {
  const lang = useShellLang();
  // at a phone width the value labels of twelve tenors run together: the table under the chart holds the values (U16-R2 b06 M3)
  const narrow = useMedia('(max-width: 600px)');
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The GIRR delta charge', es: 'El cargo delta GIRR' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SWAP} />;
  const fit = fitOf(sel);
  const g = o.girr;
  const p = fit?.girr_parameters ?? null;
  const tenors = p ? (p.tenors_years as number[]) : null;
  const label = (i: number): BiText => (tenors ? { en: `${formatNumber(tenors[i], 'en', { digits: 4 })} y`, es: `${formatNumber(tenors[i], 'es', { digits: 4 })} a` } : { en: `Tenor ${i + 1}`, es: `Plazo ${i + 1}` });
  const axis = axisOf(g.weighted_sensitivities);
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: `The change in value for a basis point, divided by 0.0001 (MAR21.19), times the delta risk weight of the tenor (MAR21.42), divided by sqrt(2) as the bank may for a specified currency such as USD (MAR21.44, a convention of the case); the weighted sensitivities are aggregated with the correlations of MAR21.46 in three scenarios and the largest is the charge. The curvature shock is the undivided ${p ? formatNumber(p.curvature_shock, 'en', { percent: true, decimals: 1 }) : formatNumber(null, 'en')} (MAR21.99). A swap book has no vega.`,
          es: `El cambio de valor por un punto base, dividido por 0,0001 (MAR21.19), por el ponderador de riesgo delta del plazo (MAR21.42), dividido por raíz de 2 como puede hacerlo el banco para una moneda especificada como USD (MAR21.44, una convención del caso); las sensibilidades ponderadas se agregan con las correlaciones de MAR21.46 en tres escenarios y el mayor es el cargo. El shock de curvatura es el ${p ? formatNumber(p.curvature_shock, 'es', { percent: true, decimals: 1 }) : formatNumber(null, 'es')} sin dividir (MAR21.99). Una cartera de swaps no tiene vega.`,
        }}
      >
                    <BarChart
              title={{ en: 'Weighted sensitivities by tenor', es: 'Sensibilidades ponderadas por plazo' }}
              height="fill"
              orientation="vertical"
              values={!narrow}
              data={g.weighted_sensitivities.map((v, i) => ({ id: `t${i}`, label: label(i), value: (Math.round(v) + 0) / axis.div, tone: v < 0 ? ('bad' as const) : ('accent' as const) }))}
              axis={{ label: { en: `Weighted sensitivity (${pick(axis.unit, 'en')})`, es: `Sensibilidad ponderada (${pick(axis.unit, 'es')})` }, format: { digits: 4 } }}
            />
      </PlotCard>
      <NumbersCard card={card}>
          <table className="caos-table ct-wrap-head" data-table="c12-girr-tenors">
            <thead>
              <tr>
                <th>{pick({ en: 'Tenor (years)', es: 'Plazo (años)' }, lang)}</th>
                <th>{pick({ en: 'Risk weight', es: 'Ponderador' }, lang)}</th>
                <th>{pick({ en: 'Sensitivity (USD)', es: 'Sensibilidad (USD)' }, lang)}</th>
                <th>{pick({ en: 'Weighted (USD)', es: 'Ponderada (USD)' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {g.sensitivities.map((s, i) => (
                <tr key={i} data-tenor={tenors ? tenors[i] : i}>
                  <td data-na={tenors ? undefined : 'true'}>{tenors ? years(tenors[i], lang) : formatNumber(null, lang)}</td>
                  <td data-na={p ? undefined : 'true'}>{p ? formatNumber(p.risk_weights[i], lang, { percent: true, decimals: 2 }) : formatNumber(null, lang)}</td>
                  <td>{cell(s, lang)}</td>
                  <td>{cell(g.weighted_sensitivities[i], lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <dl className="ct-defs" style={DEFS_STYLE} data-table="c12-girr">
            <dt>{pick({ en: 'Delta charge, divided and undivided (USD)', es: 'Cargo delta, dividido y sin dividir (USD)' }, lang)}</dt>
            <dd data-girr-charge={g.delta_charge.amount}><Nw>{`${cell(g.delta_charge.amount, lang)} / ${cell(g.delta_charge_undivided.amount, lang)}`}</Nw></dd>
            <dt>{pick({ en: 'Division by sqrt(2)', es: 'División por raíz de 2' }, lang)}</dt>
            <dd data-status={g.sqrt2_label}>{`${g.sqrt2_division ? pick({ en: 'applied', es: 'aplicada' }, lang) : pick({ en: 'not applied', es: 'no aplicada' }, lang)} (${g.sqrt2_label === 'convention' ? pick({ en: 'convention', es: 'convención' }, lang) : g.sqrt2_label})`}</dd>
            {g.scenarios.map((s) => (
              <Fragment key={s.scenario}>
                <dt>{pick({ en: `Scenario ${s.scenario}: bucket charge (USD)`, es: `Escenario ${{ low: 'bajo', medium: 'medio', high: 'alto' }[s.scenario]}: cargo del tramo (USD)` }, lang)}</dt>
                <dd data-scenario={s.scenario}><Nw>{cell(s.k_b, lang)}</Nw></dd>
              </Fragment>
            ))}
          </dl>
      </NumbersCard>
    </ViewsRow>
  );
}

