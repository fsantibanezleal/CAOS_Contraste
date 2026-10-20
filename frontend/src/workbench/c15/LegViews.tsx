// C15's Legs group: the two legs of the Banco Andino book apart (the CLP leg and the UF-indexed UR leg), the delta EVE of
// each under the six shocks with the 50 percent CLP and CLF offset shown on and off, the positions of the legs in their
// own currencies, and the dynamic NII of each leg. Money is in the reporting currency (CLP) except where a position is
// in its own currency (CLF for the UR leg); the document's scale says in what unit. The EaR and EVaR of each leg are the last view
// (c15-outputs 1.1.0).
import { Fragment } from 'react';
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable } from '../c06/format';
import { useCard, type Bi } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { IrrbbTestsTable, UnavailableCard } from '../c14/C14Common';
import { DYN_TEXT, itemName } from '../c14/NiiViews';
import {
  LEG_SHORT, LEG_TEXT, OFFSET_LONG, ORIGIN_TEXT, SHOCK_ORDER, SHOCK_TEXT, axisOf, eveRowOf, fitOf, legOf, moneyDoc, outputsOf, pairTotal, scaleUnit, text, worst,
  type C15Sel,
} from './selection';

const cell = (v: number | null | undefined, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });

const CATEGORY_TEXT: Record<string, Bi> = {
  cash: { en: 'Cash', es: 'Efectivo' },
  securities: { en: 'Securities', es: 'Valores' },
  'loans-fixed': { en: 'Fixed-rate loans', es: 'Créditos a tasa fija' },
  'loans-floating': { en: 'Floating-rate loans', es: 'Créditos a tasa variable' },
  'loans-uf': { en: 'UF loans', es: 'Créditos en UF' },
  'deposits-nmd': { en: 'Non-maturity deposits', es: 'Depósitos sin vencimiento' },
  'deposits-time': { en: 'Time deposits', es: 'Depósitos a plazo' },
  borrowings: { en: 'Borrowings', es: 'Obligaciones' },
  other: { en: 'Other', es: 'Otros' },
};

/** The delta EVE of each leg under every shock, the pair without and with the offset, and the Annex 1 measure under the offset chosen. */
export function EveByLegView({ sel }: { sel: C15Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const row = eveRowOf(o, sel.shock);
  if (!row) {
    return <UnavailableCard sel={sel} title={{ en: 'Delta EVE by leg', es: 'Delta EVE por tramo' }} reason={{ en: 'Not available: this document has no row for this shock.', es: 'No disponible: este documento no trae una fila para este choque.' }} />;
  }
  const doc = moneyDoc(o);
  const unit = pick(scaleUnit(doc), lang);
  const axis = axisOf(doc, [row.clp.delta_eve, row.ur.delta_eve, row.pair.with_offset, row.pair.without_offset]);
  const measure = worst(o.eve.rows, (r) => r.pair, sel.offset);
  const sizes = o.eve_shock_sizes
    .map((z) => `${z.currency} ${z.parallel_bp}/${z.short_bp}/${z.long_bp} ${pick({ en: 'bp', es: 'pb' }, lang)} (${pick(text(ORIGIN_TEXT, z.origin), lang)})${z.origin === 'contraste-estimate' && z.label ? ` ${pick(z.label, lang)}` : ''}`)
    .join('; ');
  const chartData: Array<{ id: string; label: BiText; value: number; tone: 'bad' | 'good' | 'accent'; highlight?: boolean }> = [
    { id: 'clp', label: LEG_TEXT.CLP, value: row.clp.delta_eve / axis.div, tone: row.clp.delta_eve > 0 ? 'bad' : 'good' },
    { id: 'ur', label: LEG_TEXT.UR, value: row.ur.delta_eve / axis.div, tone: row.ur.delta_eve > 0 ? 'bad' : 'good' },
    { id: 'without', label: { en: 'Pair, no offset', es: 'Par, sin compensación' }, value: row.pair.without_offset / axis.div, tone: 'accent', highlight: sel.offset === 'off' },
    { id: 'with', label: { en: 'Pair, with offset', es: 'Par, con compensación' }, value: row.pair.with_offset / axis.div, tone: 'accent', highlight: sel.offset === 'on' },
  ];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `Delta EVE by leg: ${text(SHOCK_TEXT, sel.shock).en.toLowerCase()}`, es: `Delta EVE por tramo: ${text(SHOCK_TEXT, sel.shock).es.toLowerCase()}` }}
        {...card}
        note={{
          en: `${o.sign_convention.statement.en} ${o.offset_rule.rule.en} Sizes: ${sizes}.`,
          es: `${o.sign_convention.statement.es} ${o.offset_rule.rule.es} Tamaños: ${sizes}.`,
        }}
      >
        <ChartOverTable
          chartMin="11rem"
          chart={
            <BarChart
              title={{ en: 'Delta EVE of the legs and of the pair', es: 'Delta EVE de los tramos y del par' }}
              height="fill"
              orientation="horizontal"
              data={chartData}
              axis={{ label: { en: 'Delta EVE, positive is a loss', es: 'Delta EVE, pérdida positiva' }, unit: axis.unit, format: { digits: 4 } }}
            />
          }
        >
          <dl className="ct-defs" data-table="eve-measure" data-measure={measure} data-offset={sel.offset}>
            <dt>{pick({ en: `Annex 1 delta EVE under the offset chosen (${unit})`, es: `Delta EVE del Anexo 1 con la compensación elegida (${unit})` }, lang)}</dt>
            <dd>{cell(measure, lang)}</dd>
            <dt>{pick({ en: `The document's own measure (${unit}), offset ${o.offset_rule.state === 'compared' ? 'compared' : o.offset_rule.state}`, es: `La medida propia del documento (${unit}), compensación ${o.offset_rule.state === 'compared' ? 'comparada' : o.offset_rule.state === 'on' ? 'activa' : 'inactiva'}` }, lang)}</dt>
            <dd>{`${cell(o.eve.delta_eve, lang)} (${formatNumber(o.eve.delta_eve_share_tier1, lang, { percent: true, decimals: 2 })} ${pick({ en: 'of Tier 1', es: 'del capital N1' }, lang)})`}</dd>
          </dl>
          <table className="caos-table ct-wrap-head" data-table="eve-by-leg">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Shock', es: 'Choque' }, lang)}</th>
                <th data-leg="CLP">{pick({ en: `CLP leg (${unit})`, es: `Tramo CLP (${unit})` }, lang)}</th>
                <th data-leg="UR">{pick({ en: `UF (UR) leg (${unit})`, es: `Tramo UF (UR) (${unit})` }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Opposite signs', es: 'Signos opuestos' }, lang)}</th>
                <th>{pick({ en: 'No offset', es: 'Sin compensación' }, lang)}</th>
                <th>{pick({ en: 'With offset', es: 'Con compensación' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {SHOCK_ORDER.map((id) => {
                const r = eveRowOf(o, id);
                if (!r) return null;
                return (
                  <tr key={id} data-shock={id} data-opposite={r.pair.opposite_signs} className={id === sel.shock ? 'ct-current' : undefined}>
                    <td className="ct-text">{pick(text(SHOCK_TEXT, id), lang)}</td>
                    <td>{cell(r.clp.delta_eve, lang)}</td>
                    <td>{cell(r.ur.delta_eve, lang)}</td>
                    <td className="ct-text ct-wide-only">{pick(r.pair.opposite_signs ? { en: 'yes', es: 'sí' } : { en: 'no', es: 'no' }, lang)}</td>
                    <td>{cell(r.pair.without_offset, lang)}</td>
                    <td>{cell(r.pair.with_offset, lang)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="ct-note">{pick(OFFSET_LONG[sel.offset], lang)}.</p>
          <IrrbbTestsTable variant={sel.data.variant} only={(t) => t.test_id === 'irrbb.cmf_annex1_goldens'} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The legs in their own currencies, the net repricing cash flows of both legs under the shock in focus, and the items of the leg in focus. */
export function PositionsView({ sel }: { sel: C15Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const row = eveRowOf(o, sel.shock);
  const leg = legOf(o, sel.leg);
  const doc = moneyDoc(o);
  const unit = pick(scaleUnit(doc), lang);
  const buckets = fitOf(sel)?.buckets ?? null;
  const x = buckets ? buckets.map((b) => b.midpoint_years) : Array.from({ length: row?.clp.net_cash_flows.length ?? 19 }, (_, i) => i + 1);
  const axis = axisOf(doc, row ? [...row.clp.net_cash_flows, ...row.ur.net_cash_flows] : []);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The positions of the legs', es: 'Las posiciones de los tramos' }}
        {...card}
        note={{
          en: `The CLP leg is in CLP and the UF-indexed leg in CLF; the curves show the net notional repricing cash flows of both legs in CLP (the UF leg converted at the UF value of ${o.ur_currency.uf_date}) under the shock chosen. Assets are positive and liabilities negative.`,
          es: `El tramo CLP está en CLP y el tramo indexado a UF en CLF; las curvas muestran los flujos nocionales netos de repreciación de ambos tramos en CLP (el tramo UF convertido al valor de la UF del ${o.ur_currency.uf_date}) bajo el choque elegido. Los activos son positivos y los pasivos negativos.`,
        }}
      >
        <ChartOverTable
          chart={
            row ? (
              <UPlotChart
                height="fill"
                x={{ values: x, label: buckets ? { en: 'Bucket midpoint', es: 'Punto medio del tramo' } : { en: 'Time bucket', es: 'Tramo' }, ...(buckets ? { unit: { en: 'years', es: 'años' } } : {}), format: { digits: 3 } }}
                y={{ label: { en: `Net repricing cash flow (${pick(axis.unit, 'en')})`, es: `Flujo neto de repreciación (${pick(axis.unit, 'es')})` }, format: { digits: 4 } }}
                series={[
                  { label: LEG_TEXT.CLP, values: row.clp.net_cash_flows.map((v) => v / axis.div), color: '--color-accent', width: 2.4 },
                  { label: LEG_TEXT.UR, values: row.ur.net_cash_flows.map((v) => v / axis.div), color: '--color-magenta', width: 2.4, dash: [6, 3] },
                ]}
              />
            ) : (
              <p className="caos-pending" data-state="unavailable">{pick({ en: 'Not available: this document has no cash flows for this shock.', es: 'No disponible: este documento no trae flujos para este choque.' }, lang)}</p>
            )
          }
        >
          <table className="caos-table ct-wrap-head" data-table="legs">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Leg', es: 'Tramo' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Currency', es: 'Moneda' }, lang)}</th>
                <th>{pick({ en: 'Assets', es: 'Activos' }, lang)}</th>
                <th>{pick({ en: 'Liabilities', es: 'Pasivos' }, lang)}</th>
                <th>{pick({ en: 'Net position', es: 'Posición neta' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.legs.map((l) => (
                <tr key={l.leg} data-leg={l.leg} className={l.leg === sel.leg ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(text(LEG_SHORT, l.leg), lang)}</td>
                  <td className="ct-text">{l.currency}</td>
                  <td>{cell(l.assets_total, lang)}</td>
                  <td>{cell(l.liabilities_total, lang)}</td>
                  <td>{cell(l.net_position, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="ct-note">{pick({ en: `Amounts of the CLP leg in ${unit} and of the UF leg in ${pick(scaleUnit({ ...doc, currency: 'CLF' }), 'en')}. One UF is worth ${cell(o.ur_currency.uf_value, 'en')} CLP on ${o.ur_currency.uf_date}.`, es: `Montos del tramo CLP en ${unit} y del tramo UF en ${pick(scaleUnit({ ...doc, currency: 'CLF' }), 'es')}. Una UF vale ${cell(o.ur_currency.uf_value, 'es')} CLP el ${o.ur_currency.uf_date}.` }, lang)}</p>
          {leg ? (
            <table className="caos-table ct-wrap-head" data-table="leg-items">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: `Items of the leg: ${text(LEG_SHORT, leg.leg).en}`, es: `Partidas del tramo: ${text(LEG_SHORT, leg.leg).es}` }, lang)}</th>
                  <th className="ct-text ct-wide-only">{pick({ en: 'Category', es: 'Categoría' }, lang)}</th>
                  <th className="ct-text ct-wide-only">{pick({ en: 'Side', es: 'Lado' }, lang)}</th>
                  <th>{pick({ en: `Amount (${leg.currency})`, es: `Monto (${leg.currency})` }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {leg.items.map((i) => (
                  <tr key={i.item_id} data-item={i.item_id}>
                    <td className="ct-text">{pick(i.label, lang)}</td>
                    <td className="ct-text ct-wide-only">{pick(text(CATEGORY_TEXT, i.category), lang)}</td>
                    <td className="ct-text ct-wide-only">{pick(i.side === 'asset' ? { en: 'asset', es: 'activo' } : { en: 'liability', es: 'pasivo' }, lang)}</td>
                    <td>{cell(i.amount, lang)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The dynamic NII of the leg in focus: three paths month by month, the totals and the loss against the base. */
export function DynamicLegView({ sel }: { sel: C15Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const d = o.dynamic_nii;
  const leg = d.legs.find((l) => l.leg === sel.leg);
  if (!leg) {
    return <UnavailableCard sel={sel} title={{ en: 'The dynamic NII', es: 'El NII dinámico' }} reason={{ en: 'Not available: this document has no dynamic NII for this leg.', es: 'No disponible: este documento no trae NII dinámico para este tramo.' }} />;
  }
  const doc = moneyDoc(o);
  const unit = pick(scaleUnit(doc), lang);
  const months = leg.scenarios[0].monthly_nii.map((_, i) => i + 1);
  const axis = axisOf(doc, leg.scenarios.flatMap((s) => s.monthly_nii));
  const labels = new Map<string, BiText>(o.legs.flatMap((l) => l.items.map((i) => [i.item_id, i.label] as const)));
  const colors = ['--color-accent', '--color-bad', '--color-good'] as const;
  const converted = leg.leg === 'UR';
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `The dynamic NII: ${text(LEG_SHORT, leg.leg).en} leg`, es: `El NII dinámico: tramo ${text(LEG_SHORT, leg.leg).es}` }}
        {...card}
        note={{
          en: `${o.sign_convention.statement.en} Month by month under the base path and the two parallel shocks${converted ? '; balances and NII of the UF leg are converted at the UF value' : ''}.`,
          es: `${o.sign_convention.statement.es} Mes a mes bajo la trayectoria base y los dos choques paralelos${converted ? '; los saldos y el NII del tramo UF se convierten al valor de la UF' : ''}.`,
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: months, label: { en: 'Month of the projection', es: 'Mes de la proyección' }, format: { decimals: 0 } }}
              y={{ label: { en: `Net interest income per month (${pick(axis.unit, 'en')})`, es: `Margen financiero neto por mes (${pick(axis.unit, 'es')})` }, format: { digits: 4 } }}
              series={leg.scenarios.map((s, i) => ({ label: DYN_TEXT[s.scenario], values: s.monthly_nii.map((v) => v / axis.div), color: colors[i % colors.length], width: 2.4, ...(i === 0 ? {} : { dash: [6, 3] }) }))}
            />
          }
        >
          <p data-block="balance-sheet-assumption" data-kind={d.balance_sheet_assumption.kind}>
            <strong>{pick({ en: 'Balance-sheet assumption: ', es: 'Supuesto de balance: ' }, lang)}</strong>
            {pick(d.balance_sheet_assumption.description, lang)}
            {converted ? ` ${pick({ en: 'The UF leg is converted at the UF value.', es: 'El tramo UF se convierte al valor de la UF.' }, lang)}` : ''}
          </p>
          <table className="caos-table ct-wrap-head" data-table="dynamic-nii" data-horizon={d.horizon_months}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Path', es: 'Trayectoria' }, lang)}</th>
                <th>{pick({ en: 'Shock (bp)', es: 'Choque (pb)' }, lang)}</th>
                <th>{pick({ en: `NII over ${d.horizon_months} months (${unit})`, es: `NII a ${d.horizon_months} meses (${unit})` }, lang)}</th>
                <th>{pick({ en: `Loss against the base (${unit})`, es: `Pérdida contra la base (${unit})` }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {leg.scenarios.map((s) => (
                <tr key={s.scenario} data-scenario={s.scenario}>
                  <td className="ct-text">{pick(DYN_TEXT[s.scenario], lang)}</td>
                  <td>{formatNumber(s.shock_bp, lang, { decimals: 0 })}</td>
                  <td>{cell(s.total, lang)}</td>
                  <td>{cell(s.delta_vs_base, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head" data-table="dynamic-items">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Item', es: 'Partida' }, lang)}</th>
                <th>{pick({ en: `Balance (${unit})`, es: `Saldo (${unit})` }, lang)}</th>
                <th>{pick({ en: 'Starting rate', es: 'Tasa inicial' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Spread', es: 'Margen' }, lang)}</th>
                <th>{pick({ en: 'Beta', es: 'Beta' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Resets every', es: 'Reprecia cada' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {leg.items.map((i, k) => (
                <tr key={i.item_id} data-item={i.item_id} data-side={i.side}>
                  <td className="ct-text">{pick(itemName(i.side, i.item_id, labels, k + 1), lang)}</td>
                  <td>{cell(i.balance, lang)}</td>
                  <td>{formatNumber(i.rate0, lang, { percent: true, decimals: 2 })}</td>
                  <td className="ct-wide-only">{formatNumber(i.spread, lang, { percent: true, decimals: 2 })}</td>
                  <td>{formatNumber(i.beta, lang, { percent: true, decimals: 2 })}</td>
                  <td className="ct-wide-only">{i.reprice_months === 0 ? pick({ en: 'every month', es: 'cada mes' }, lang) : `${i.reprice_months} ${pick({ en: 'months', es: 'meses' }, lang)}`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

export { pairTotal };

const METHOD_TEXT: Record<string, BiText> = {
  hw1f: { en: 'Hull-White one-factor', es: 'Hull-White de un factor' },
  dns: { en: 'dynamic Nelson-Siegel', es: 'Nelson-Siegel dinámico' },
};

/** EaR and EVaR of the leg in focus at 95 and 99 percent from scenario Monte Carlo, with the method, the parameters, the paths, the seed and the error. */
export function EarEvarLegView({ sel }: { sel: C15Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const e = o.ear_evar?.find((x) => x.leg === sel.leg);
  if (!e) {
    return <UnavailableCard sel={sel} title={{ en: 'Earnings at risk and economic value at risk', es: 'Ganancias en riesgo y valor económico en riesgo' }} reason={{ en: 'Not available: this document has no EaR and EVaR for this leg.', es: 'No disponible: este documento no trae EaR ni EVaR para este tramo.' }} />;
  }
  const doc = moneyDoc(o);
  const axis = axisOf(doc, e.levels.flatMap((l) => [l.ear, l.evar]));
  const unit = pick(scaleUnit(doc), lang);
  const pctLevel = (l: number) => formatNumber(l, lang, { percent: true, decimals: 0 });
  const bars = e.levels.flatMap((l) => [
    { id: `ear-${l.level}`, label: { en: `EaR ${pctLevel(l.level)}`, es: `EaR ${pctLevel(l.level)}` }, value: l.ear / axis.div, tone: 'warn' as const },
    { id: `evar-${l.level}`, label: { en: `EVaR ${pctLevel(l.level)}`, es: `EVaR ${pctLevel(l.level)}` }, value: l.evar / axis.div, tone: 'bad' as const },
  ]);
  const converted = e.leg === 'UR';
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `Earnings at risk and economic value at risk: ${text(LEG_SHORT, e.leg).en} leg`, es: `Ganancias en riesgo y valor económico en riesgo: tramo ${text(LEG_SHORT, e.leg).es}` }}
        {...card}
        note={{
          en: `${o.sign_convention.statement.en} EaR is the base NII of the leg minus the lower quantile of its simulated NII; EVaR is the same for the EVE. Both come from short-rate scenarios drawn by the method named below and carry the Monte Carlo error of the number of paths${converted ? '; the UF leg is converted at the UF value' : ''}.`,
          es: `${o.sign_convention.statement.es} El EaR es el NII base del tramo menos el cuantil inferior de su NII simulado; el EVaR es lo mismo para el EVE. Ambos vienen de escenarios de tasa corta generados por el método nombrado abajo y llevan el error de Monte Carlo del número de trayectorias${converted ? '; el tramo UF se convierte al valor de la UF' : ''}.`,
        }}
      >
        <ChartOverTable
          chartMin="13rem"
          chart={
            <BarChart
              title={{ en: 'EaR and EVaR by confidence level', es: 'EaR y EVaR por nivel de confianza' }}
              height="fill"
              orientation="vertical"
              data={bars}
              axis={{ label: { en: 'Loss at the confidence level', es: 'Pérdida al nivel de confianza' }, unit: axis.unit, format: { digits: 4 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="ear-evar" data-leg={e.leg}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Confidence level', es: 'Nivel de confianza' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: `NII quantile (${unit})`, es: `Cuantil del NII (${unit})` }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: `EVE quantile (${unit})`, es: `Cuantil del EVE (${unit})` }, lang)}</th>
                <th>{pick({ en: `EaR (${unit})`, es: `EaR (${unit})` }, lang)}</th>
                <th>{pick({ en: `EVaR (${unit})`, es: `EVaR (${unit})` }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: `EaR Monte Carlo error (${unit})`, es: `Error de Monte Carlo del EaR (${unit})` }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: `EVaR Monte Carlo error (${unit})`, es: `Error de Monte Carlo del EVaR (${unit})` }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {e.levels.map((l) => (
                <tr key={l.level} data-level={l.level}>
                  <td className="ct-text">{pctLevel(l.level)}</td>
                  <td className="ct-wide-only">{cell(l.nii_quantile, lang)}</td>
                  <td className="ct-wide-only">{cell(l.eve_quantile, lang)}</td>
                  <td>{cell(l.ear, lang)}</td>
                  <td>{cell(l.evar, lang)}</td>
                  <td className="ct-wide-only" data-ear-se={l.ear_se}>{cell(l.ear_se, lang)}</td>
                  <td className="ct-wide-only" data-evar-se={l.evar_se}>{cell(l.evar_se, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <dl className="ct-defs" data-table="ear-evar-method">
            <dt>{pick({ en: 'Scenario method', es: 'Método de escenarios' }, lang)}</dt>
            <dd>{pick(METHOD_TEXT[e.method] ?? { en: e.method, es: e.method }, lang)}</dd>
            {e.parameters.map((p) => (
              <Fragment key={p.name}>
                <dt>{pick({ en: 'Parameter', es: 'Parámetro' }, lang)}</dt>
                <dd data-parameter={p.name}>{`${p.name} = ${formatNumber(p.value, lang, { digits: 4 })} (${lang === 'es' && p.unit === 'per year' ? 'por año' : p.unit})`}</dd>
              </Fragment>
            ))}
            <dt>{pick({ en: 'Paths', es: 'Trayectorias' }, lang)}</dt>
            <dd>{formatNumber(e.n_paths, lang, { decimals: 0 })}</dd>
            <dt>{pick({ en: 'Seed', es: 'Semilla' }, lang)}</dt>
            <dd data-seed={e.seed}>{e.seed}</dd>
            <dt>{pick({ en: 'Horizon', es: 'Horizonte' }, lang)}</dt>
            <dd>{`${e.horizon_months} ${pick({ en: 'months', es: 'meses' }, lang)}`}</dd>
            <dt>{pick({ en: `Base NII (${unit})`, es: `NII base (${unit})` }, lang)}</dt>
            <dd>{cell(e.base_nii, lang)}</dd>
            <dt>{pick({ en: `Base EVE (${unit})`, es: `EVE base (${unit})` }, lang)}</dt>
            <dd>{cell(e.base_eve, lang)}</dd>
            <dt>{pick({ en: 'Monte Carlo error', es: 'Error de Monte Carlo' }, lang)}</dt>
            <dd data-mc-method={e.mc_error_method}>{pick({ en: `batch means over ${e.n_batches} batches of the paths, per level in the table`, es: `medias por lotes sobre ${e.n_batches} lotes de las trayectorias, por nivel en la tabla` }, lang)}</dd>
          </dl>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
