// C14's NII and dynamics group: the repricing gap and the duration gap (ladder rungs 1 and 2), the dynamic NII
// projection under the base path and the two parallel shocks with the out-of-sample comparison against the realised NII
// (rung 5), and the distribution summary of NII and EVE under scenario Monte Carlo, EaR and EVaR (rung 6). A positive
// delta NII or delta EVE is a loss; the balance-sheet assumption, the deposit betas and the Monte Carlo error are stated.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable } from '../c06/format';
import { useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { IrrbbTestsTable, UnavailableCard } from './C14Common';
import { NMD_TEXT, axisOf, cell, fitOf, outputsOf, scaleUnit, text, type C14Outputs, type C14Sel } from './selection';

const SHARE = (v: number | null | undefined, lang: 'en' | 'es') => formatNumber(v, lang, { percent: true, decimals: 2 });
const digits = (v: number | null | undefined, lang: 'en' | 'es') => formatNumber(v, lang, { digits: 4 });

/** The repricing gap by bucket under the deposit assumption in focus, and the duration gap with its first-order change in equity. */
export function GapView({ sel }: { sel: C14Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const ladder = o.ladder.find((l) => l.nmd_assumption === sel.nmd);
  if (!ladder) {
    return <UnavailableCard sel={sel} title={{ en: 'The repricing gap', es: 'La brecha de repreciación' }} reason={{ en: 'Not available: this document has no ladder for this deposit assumption.', es: 'No disponible: este documento no trae la escalera para este supuesto de depósitos.' }} />;
  }
  const labels = new Map<number, BiText>((fitOf(sel)?.buckets ?? []).map((b) => [b.bucket, b.label] as const));
  const axis = axisOf(o, ladder.repricing_gap.map((g) => g.gap));
  const unit = pick(scaleUnit(o), lang);
  const d = ladder.duration_gap;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `The repricing gap: ${text(NMD_TEXT, sel.nmd).en.toLowerCase()} NMD`, es: `La brecha de repreciación: NMD ${text(NMD_TEXT, sel.nmd).es.toLowerCase()}` }}
        {...card}
        note={{
          en: 'Assets minus liabilities that reprice in each of the 19 time buckets, in notional terms. The NII approximation sums the gap of the buckets under one year, each weighted by the part of the year left after it reprices. The duration gap gives the first-order change in equity for a 100 bp rise.',
          es: 'Activos menos pasivos que reprecian en cada uno de los 19 tramos, en términos nominales. La aproximación del NII suma la brecha de los tramos bajo un año, cada una ponderada por la parte del año que queda después de repreciar. La brecha de duración da el cambio de primer orden del patrimonio ante un alza de 100 pb.',
        }}
      >
        <ChartOverTable
          chart={
            <BarChart
              title={{ en: 'Repricing gap by time bucket', es: 'Brecha de repreciación por tramo' }}
              height="fill"
              orientation="vertical"
              values={false}
              data={ladder.repricing_gap.map((g) => ({ id: String(g.bucket), label: { en: String(g.bucket), es: String(g.bucket) }, value: g.gap / axis.div, tone: g.gap >= 0 ? ('accent' as const) : ('warn' as const), hint: labels.get(g.bucket) ?? { en: `${g.midpoint_years} years`, es: `${g.midpoint_years} años` } }))}
              axis={{ label: { en: 'Gap, assets minus liabilities (buckets 1 to 19, overnight to over 20 years)', es: 'Brecha, activos menos pasivos (tramos 1 a 19, a la vista a más de 20 años)' }, unit: axis.unit, format: { digits: 4 } }}
            />
          }
        >
          <dl className="ct-defs" data-table="duration-gap">
            <dt>{pick({ en: 'Asset duration', es: 'Duración de activos' }, lang)}</dt>
            <dd>{`${digits(d.asset_duration_years, lang)} ${pick({ en: 'years', es: 'años' }, lang)}`}</dd>
            <dt>{pick({ en: 'Liability duration', es: 'Duración de pasivos' }, lang)}</dt>
            <dd>{`${digits(d.liability_duration_years, lang)} ${pick({ en: 'years', es: 'años' }, lang)}`}</dd>
            <dt>{pick({ en: 'Duration gap', es: 'Brecha de duración' }, lang)}</dt>
            <dd>{`${digits(d.duration_gap_years, lang)} ${pick({ en: 'years', es: 'años' }, lang)}`}</dd>
            <dt>{pick({ en: `Change in equity for +100 bp (${unit})`, es: `Cambio del patrimonio por +100 pb (${unit})` }, lang)}</dt>
            <dd>{cell(d.equity_change_100bp_up, lang)}</dd>
            <dt>{pick({ en: `Delta NII for +100 bp, from the gap (${unit}); positive is a loss`, es: `Delta NII por +100 pb, desde la brecha (${unit}); positivo es una pérdida` }, lang)}</dt>
            <dd>{cell(ladder.delta_nii_gap_100bp_up, lang)}</dd>
          </dl>
          <table className="caos-table ct-wrap-head" data-table="repricing-gap">
            <thead>
              <tr>
                <th>{pick({ en: 'Bucket', es: 'Tramo' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Range', es: 'Rango' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Midpoint (years)', es: 'Punto medio (años)' }, lang)}</th>
                <th>{pick({ en: `Assets (${unit})`, es: `Activos (${unit})` }, lang)}</th>
                <th>{pick({ en: `Liabilities (${unit})`, es: `Pasivos (${unit})` }, lang)}</th>
                <th>{pick({ en: `Gap (${unit})`, es: `Brecha (${unit})` }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {ladder.repricing_gap.map((g) => (
                <tr key={g.bucket} data-bucket={g.bucket}>
                  <td>{g.bucket}</td>
                  <td className="ct-text">{labels.get(g.bucket) ? pick(labels.get(g.bucket) as BiText, lang) : formatNumber(null, lang)}</td>
                  <td className="ct-wide-only">{formatNumber(g.midpoint_years, lang, { digits: 4 })}</td>
                  <td>{cell(g.assets, lang)}</td>
                  <td>{cell(g.liabilities, lang)}</td>
                  <td>{cell(g.gap, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The words of a dynamic-NII scenario. */
export const DYN_TEXT: Record<string, BiText> = {
  base: { en: 'Base path', es: 'Trayectoria base' },
  'parallel-up': { en: 'Parallel up', es: 'Paralelo al alza' },
  'parallel-down': { en: 'Parallel down', es: 'Paralelo a la baja' },
};

/** The side of a dynamic-NII item in words, with its ordinal when the balance sheet has no label for the id. */
export function itemName(side: 'asset' | 'liability', id: string, labels: Map<string, BiText>, ordinal: number): BiText {
  return labels.get(id) ?? (side === 'asset' ? { en: `Asset ${ordinal}`, es: `Activo ${ordinal}` } : { en: `Liability ${ordinal}`, es: `Pasivo ${ordinal}` });
}

/** The monthly NII under the base path and the two parallel shocks, the totals and the loss against the base, and the projection against the realised NII. */
export function DynamicNiiView({ sel }: { sel: C14Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const d = o.dynamic_nii;
  const months = d.scenarios[0].monthly_nii.map((_, i) => i + 1);
  const axis = axisOf(o, d.scenarios.flatMap((s) => s.monthly_nii));
  const unit = pick(scaleUnit(o), lang);
  const labels = new Map<string, BiText>(o.balance_sheet.items.map((i) => [i.item_id, i.label] as const));
  const oos: C14Outputs['out_of_sample'] = o.out_of_sample;
  const colors = ['--color-accent', '--color-bad', '--color-good'] as const;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The dynamic NII projection', es: 'La proyección dinámica del NII' }}
        {...card}
        note={{
          en: `${o.sign_convention.statement.en} The projection runs month by month under the base path and the two parallel shocks of the 2024 calibration; floating items follow the short rate with the deposit beta of each item.`,
          es: `${o.sign_convention.statement.es} La proyección corre mes a mes bajo la trayectoria base y los dos choques paralelos de la calibración 2024; las partidas variables siguen la tasa corta con el beta de depósitos de cada partida.`,
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: months, label: { en: 'Month of the projection', es: 'Mes de la proyección' }, format: { decimals: 0 } }}
              y={{ label: { en: `NII per month (${pick(axis.unit, 'en')})`, es: `NII por mes (${pick(axis.unit, 'es')})` }, format: { digits: 4 } }}
              series={d.scenarios.map((s, i) => ({ label: DYN_TEXT[s.scenario], values: s.monthly_nii.map((v) => v / axis.div), color: colors[i % colors.length], width: 2.4, ...(i === 0 ? {} : { dash: [6, 3] }) }))}
            />
          }
        >
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
              {d.scenarios.map((s) => (
                <tr key={s.scenario} data-scenario={s.scenario}>
                  <td className="ct-text">{pick(DYN_TEXT[s.scenario], lang)}</td>
                  <td>{formatNumber(s.shock_bp, lang, { decimals: 0 })}</td>
                  <td>{cell(s.total, lang)}</td>
                  <td>{cell(s.delta_vs_base, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p data-block="balance-sheet-assumption" data-kind={d.balance_sheet_assumption.kind}>
            <strong>{pick({ en: 'Balance-sheet assumption: ', es: 'Supuesto de balance: ' }, lang)}</strong>
            {pick(d.balance_sheet_assumption.description, lang)}
          </p>
          <dl className="ct-defs" data-table="out-of-sample" data-applicable={oos.applicable}>
            <dt>{pick({ en: 'Projection date', es: 'Fecha de la proyección' }, lang)}</dt>
            <dd>{oos.projection_date}</dd>
            {oos.applicable ? (
              <>
                <dt>{pick({ en: 'Realised period', es: 'Período realizado' }, lang)}</dt>
                <dd>{`${oos.realised_period_start} ${pick({ en: 'to', es: 'a' }, lang)} ${oos.realised_period_end}`}</dd>
                <dt>{pick({ en: `Projected delta NII (${unit})`, es: `Delta NII proyectado (${unit})` }, lang)}</dt>
                <dd>{cell(oos.projected_delta_nii, lang)}</dd>
                <dt>{pick({ en: `Realised delta NII (${unit})`, es: `Delta NII realizado (${unit})` }, lang)}</dt>
                <dd>{cell(oos.realised_delta_nii, lang)}</dd>
                <dt>{pick({ en: 'Relative error', es: 'Error relativo' }, lang)}</dt>
                <dd>{SHARE(oos.relative_error, lang)}</dd>
              </>
            ) : (
              <>
                <dt>{pick({ en: 'Comparison with the realised NII', es: 'Comparación con el NII realizado' }, lang)}</dt>
                <dd data-na="true">{`${formatNumber(null, lang)} (${oos.reason ? pick(oos.reason, lang) : ''})`}</dd>
              </>
            )}
          </dl>
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
              {d.items.map((i, k) => (
                <tr key={i.item_id} data-item={i.item_id} data-side={i.side}>
                  <td className="ct-text">{pick(itemName(i.side, i.item_id, labels, k + 1), lang)}</td>
                  <td>{cell(i.balance, lang)}</td>
                  <td>{SHARE(i.rate0, lang)}</td>
                  <td className="ct-wide-only">{SHARE(i.spread, lang)}</td>
                  <td>{SHARE(i.beta, lang)}</td>
                  <td className="ct-wide-only">{i.reprice_months === 0 ? pick({ en: 'every month', es: 'cada mes' }, lang) : `${i.reprice_months} ${pick({ en: 'months', es: 'meses' }, lang)}`}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <IrrbbTestsTable variant={sel.data.variant} only={(t) => t.test_id === 'irrbb.nii_out_of_sample'} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

const METHOD_TEXT: Record<string, BiText> = {
  hw1f: { en: 'Hull-White one-factor', es: 'Hull-White de un factor' },
  dns: { en: 'dynamic Nelson-Siegel', es: 'Nelson-Siegel dinámico' },
};

/** EaR and EVaR at 95 and 99 percent from scenario Monte Carlo, with the method, the parameters, the paths, the seed and the Monte Carlo error. */
export function EarEvarView({ sel }: { sel: C14Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const e = o.ear_evar;
  const axis = axisOf(o, e.levels.flatMap((l) => [l.ear, l.evar]));
  const unit = pick(scaleUnit(o), lang);
  const pctLevel = (l: number) => formatNumber(l, lang, { percent: true, decimals: 0 });
  const bars = e.levels.flatMap((l) => [
    { id: `ear-${l.level}`, label: { en: `EaR ${pctLevel(l.level)}`, es: `EaR ${pctLevel(l.level)}` }, value: l.ear / axis.div, tone: 'warn' as const },
    { id: `evar-${l.level}`, label: { en: `EVaR ${pctLevel(l.level)}`, es: `EVaR ${pctLevel(l.level)}` }, value: l.evar / axis.div, tone: 'bad' as const },
  ]);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Earnings at risk and economic value at risk', es: 'Ganancias en riesgo y valor económico en riesgo' }}
        {...card}
        note={{
          en: `${o.sign_convention.statement.en} EaR is the base NII minus the lower quantile of the simulated NII; EVaR is the same for the EVE. Both come from short-rate scenarios drawn by the method named below, and carry the Monte Carlo error of the number of paths.`,
          es: `${o.sign_convention.statement.es} El EaR es el NII base menos el cuantil inferior del NII simulado; el EVaR es lo mismo para el EVE. Ambos vienen de escenarios de tasa corta generados por el método nombrado abajo, y llevan el error de Monte Carlo del número de trayectorias.`,
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
          <table className="caos-table ct-wrap-head" data-table="ear-evar">
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
            <dd>{pick(METHOD_TEXT[e.method], lang)}</dd>
            {e.parameters.map((p) => (
              <Param key={p.name} name={p.name} value={p.value} unit={p.unit} />
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

function Param({ name, value, unit }: { name: string; value: number; unit: string }) {
  const lang = useShellLang();
  return (
    <>
      <dt>{pick({ en: 'Parameter', es: 'Parámetro' }, lang)}</dt>
      <dd data-parameter={name}>{`${name} = ${formatNumber(value, lang, { digits: 4 })} (${lang === 'es' ? (unit === 'per year' ? 'por año' : unit === 'per square-root year' ? 'por raíz cuadrada del año' : unit) : unit})`}</dd>
    </>
  );
}
