// C12's exposure group: the EE, ENE and PFE profiles with the Monte Carlo band and the ORE overlay; the uncollateralised
// profile against variation margin at the two margin periods and initial margin on one time axis; the netting benefit;
// and the sensitivity of EE and PFE to the short-rate calibration. Every line is a field of the document (a band is the
// document's EE plus and minus two of its own Monte Carlo standard errors); nothing is computed here but a division by
// the axis scale. A block the document lacks is "not available" with its reason, never an empty chart.
import { PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable, alignTo, unionX } from '../c06/format';
import { useCard, type Bi } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { platformText } from '../c08/notes';
import { NOT_SWAP, TallTables, UnavailableCard, cell, years, DEFS_STYLE, Nw } from './C12Common';
import { BASIS_TEXT, CASE_ORDER, CASE_TEXT, VARIANT_TEXT, axisOf, gridOf, outputsOf, sensitivityOf, text, type C12Profile, type C12Sel } from './selection';

/** The ORE platform in Spanish: the shared rule, with the package kind left out ("paquete wheel" kept the English word, R4 c15 B1). */
const platformSpanish = (platform: string | null | undefined): string =>
  platformText(platform, 'es').replace('paquete wheel', 'paquete')
    // the noun before the name, in Spanish order: "el paquete open-source-risk-engine 1.8.17.0", never "<name> paquete" (R5 c16 n6)
    .replace(/^(\S+ \S+) paquete\b/, 'el paquete $1');

const YEARS_AXIS = { label: { en: 'Time (years)', es: 'Tiempo (años)' } as BiText, format: { decimals: 1 } };

/** The EE, ENE and PFE of the document over the grid, with the Monte Carlo band of the EE and the ORE profile where the variant has one. */
export function ProfileView({ sel }: { sel: C12Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'Exposure profiles: EE, ENE and PFE', es: 'Perfiles de exposición: EE, ENE y PFE' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SWAP} />;
  const e = o.exposure;
  const grid = e.time_grid_years;
  const ore = o.ore_reconciliation;
  const oreEe = ore.status === 'reconciled' ? ore.ore_ee : null;
  const axis = axisOf([...e.ee.values, ...e.ene.values, ...e.pfe.values, ...e.ee.values.map((v, i) => v + 2 * e.ee.mc_se[i]), ...(oreEe?.values ?? [])]);
  const unit = pick(axis.unit, lang);
  const div = (a: number[]) => a.map((v) => v / axis.div);
  const lower = e.ee.values.map((v, i) => (v - 2 * e.ee.mc_se[i]) / axis.div);
  const upper = e.ee.values.map((v, i) => (v + 2 * e.ee.mc_se[i]) / axis.div);
  const at = Math.min(sel.t, grid.length - 1);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: `${pick(text(VARIANT_TEXT, o.variant), 'en')}, ${pick(text(BASIS_TEXT, e.basis), 'en')}. ${pick(e.measure_note, 'en')} The band is the EE plus and minus two Monte Carlo standard errors; the PFE is the ${formatNumber(e.pfe_quantile, 'en', { percent: true, decimals: 0 })} quantile. The exposure is a Hull-White one-factor simulation fitted to the Treasury curve of the date.`,
          es: `${pick(text(VARIANT_TEXT, o.variant), 'es')}, ${pick(text(BASIS_TEXT, e.basis), 'es')}. ${pick(e.measure_note, 'es')} La banda es la EE más y menos dos errores estándar de Monte Carlo; el PFE es el cuantil ${formatNumber(e.pfe_quantile, 'es', { percent: true, decimals: 0 })}. La exposición es una simulación de Hull-White de un factor ajustada a la curva del Tesoro de la fecha.`,
        }}
      >
        <TallTables>
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: grid, ...YEARS_AXIS }}
              y={{ label: { en: `Exposure (${pick(axis.unit, 'en')})`, es: `Exposición (${pick(axis.unit, 'es')})` }, format: { digits: 4 } }}
              series={[
                { label: { en: 'EE, minus 2 SE', es: 'EE, menos 2 ES' }, values: lower, color: '--color-accent', width: 1, dash: [2, 3] },
                { label: { en: 'EE, plus 2 SE', es: 'EE, más 2 ES' }, values: upper, color: '--color-accent', width: 1, dash: [2, 3] },
                { label: { en: 'EE', es: 'EE' }, values: div(e.ee.values), color: '--color-accent', width: 2.6 },
                { label: { en: 'ENE', es: 'ENE' }, values: div(e.ene.values), color: '--color-warn', width: 2, dash: [6, 3] },
                { label: { en: 'PFE', es: 'PFE' }, values: div(e.pfe.values), color: '--color-bad', width: 2.2 },
                { label: { en: 'Effective EE', es: 'EE efectiva' }, values: div(e.effective_ee.values), color: '--color-fg-subtle', width: 1.6, dash: [8, 3] },
                ...(oreEe ? [{ label: { en: 'EE of ORE', es: 'EE de ORE' }, values: div(oreEe.values), color: '--color-magenta' as const, mode: 'points' as const, size: 7 }] : []),
              ]}
              marks={[{ x: grid[at], label: { en: `Year ${formatNumber(grid[at], 'en', { digits: 4 })}`, es: `Año ${formatNumber(grid[at], 'es', { digits: 4 })}` } }]}
            />
          }
        >
          <dl className="ct-defs" style={DEFS_STYLE} data-table="c12-profile">
            <dt>{pick({ en: 'EPE and EEPE (USD)', es: 'EPE y EEPE (USD)' }, lang)}</dt>
            <dd data-eepe={e.eepe.amount}>
              <Nw>{`${cell(e.epe.amount, lang)} / ${cell(e.eepe.amount, lang)}`}</Nw>
              {` (${e.eepe_horizon_years === 1 ? pick({ en: 'first year', es: 'primer año' }, lang) : `${pick({ en: 'first', es: 'primeros' }, lang)} ${years(e.eepe_horizon_years, lang)} ${pick({ en: 'years', es: 'años' }, lang)}`}; ${pick({ en: 'Monte Carlo SE', es: 'error estándar de Monte Carlo' }, lang)} ${cell(e.eepe.mc_se, lang)})`}
            </dd>
          </dl>
          <table className="caos-table ct-wrap-head" data-table="c12-profile-grid">
            <thead>
              <tr>
                <th>{pick({ en: 'Year', es: 'Año' }, lang)}</th>
                <th>{pick({ en: 'EE (USD)', es: 'EE (USD)' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'SE of the EE', es: 'ES de la EE' }, lang)}</th>
                <th>{pick({ en: 'ENE (USD)', es: 'ENE (USD)' }, lang)}</th>
                <th>{pick({ en: 'PFE (USD)', es: 'PFE (USD)' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'EE of ORE (USD)', es: 'EE de ORE (USD)' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {grid.map((t, i) => (
                <tr key={t} data-point={i} className={i === at ? 'ct-current' : undefined}>
                  <td>{years(t, lang)}</td>
                  <td>{cell(e.ee.values[i], lang)}</td>
                  <td className="ct-wide-only">{cell(e.ee.mc_se[i], lang)}</td>
                  <td>{cell(e.ene.values[i], lang)}</td>
                  <td>{cell(e.pfe.values[i], lang)}</td>
                  <td className="ct-wide-only" data-na={oreEe ? undefined : 'true'}>{oreEe ? cell(oreEe.values[i], lang) : formatNumber(null, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <dl className="ct-defs" style={DEFS_STYLE} data-table="c12-profile-ore">
            <dt>{pick({ en: 'ORE 1.8.17.0', es: 'ORE 1.8.17.0' }, lang)}</dt>
            <dd data-ore={ore.status}>
              {ore.status === 'reconciled' && ore.eepe_agreement && ore.cva_agreement
                ? pick(
                    {
                      // "reconciled" only when every point is within two combined standard errors (R4 c15 m2: the Variants wording)
                      en: `${ore.all_within_two_se ? 'reconciled' : 'compared'} on ${platformText(ore.platform, 'en')}: EEPE ${cell(ore.eepe_agreement.python, 'en')} against ${cell(ore.eepe_agreement.ore, 'en')}, CVA ${cell(ore.cva_agreement.python, 'en')} against ${cell(ore.cva_agreement.ore, 'en')}; every point within two combined standard errors: ${ore.all_within_two_se ? 'yes' : 'no'}`,
                      es: `${ore.all_within_two_se ? 'conciliada' : 'comparada'} en ${platformSpanish(ore.platform)}: EEPE ${cell(ore.eepe_agreement.python, 'es')} contra ${cell(ore.eepe_agreement.ore, 'es')}, CVA ${cell(ore.cva_agreement.python, 'es')} contra ${cell(ore.cva_agreement.ore, 'es')}; todos los puntos dentro de dos errores estándar combinados: ${ore.all_within_two_se ? 'sí' : 'no'}`,
                    },
                    lang,
                  )
                : `${pick({ en: 'no ORE reconciliation', es: 'sin conciliación con ORE' }, lang)}${ore.reason ? `: ${pick(ore.reason, lang)}` : ''}`}
            </dd>
          </dl>
          <p className="ct-note">{pick({ en: `The axis is in ${unit}; the table keeps the whole amounts.`, es: `El eje está en ${unit}; la tabla guarda los montos completos.` }, lang)}</p>
        </ChartOverTable>
        </TallTables>
      </PlotCard>
    </ViewsRow>
  );
}

const MPOR_LABEL: Record<string, BiText> = {
  'netting-set': { en: 'Uncollateralised', es: 'Sin colateral' },
  'csa-mpor-10d': { en: 'Variation margin, MPoR 10 days', es: 'Margen de variación, MPoR de 10 días' },
  'csa-mpor-20d': { en: 'Variation margin, MPoR 20 days', es: 'Margen de variación, MPoR de 20 días' },
  'with-im': { en: 'Variation and initial margin (regression proxy)', es: 'Margen de variación e inicial (aproximación por regresión)' },
};
const MPOR_COLOR = { 'netting-set': '--color-accent', 'csa-mpor-10d': '--color-good', 'csa-mpor-20d': '--color-warn', 'with-im': '--color-magenta' } as const;

/** The value axis of the collateral chart: it also draws the dynamic initial margin when the with-im document is loaded (R3 c13 m7). */
export const collateralAxisLabel = (withDim: boolean, unit: BiText): Bi => {
  const u = { en: pick(unit, 'en'), es: pick(unit, 'es') };
  return withDim ? { en: `EE and initial margin (${u.en})`, es: `EE y margen inicial (${u.es})` } : { en: `EE (${u.en})`, es: `EE (${u.es})` };
};

/** The uncollateralised EE against variation margin at the two margin periods and initial margin, on one time axis, from the four netting-set documents. */
export function CollateralView({ sel }: { sel: C12Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'Collateral, margin period and initial margin', es: 'Colateral, periodo de margen y margen inicial' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SWAP} />;
  if (!sel.peers) return <Pending />;
  const ids = (['netting-set', 'csa-mpor-10d', 'csa-mpor-20d', 'with-im'] as const).filter((id) => sel.peers?.[id]);
  const docs = ids.map((id) => ({ id, o: sel.peers![id].o }));
  const withIm = sel.peers['with-im']?.o ?? null;
  const dim = withIm?.initial_margin?.dim ?? null;
  const grids = docs.map((d) => d.o.exposure.time_grid_years);
  const grid = unionX(...grids, ...(dim && withIm ? [withIm.exposure.time_grid_years] : []));
  const axis = axisOf([...docs.flatMap((d) => d.o.exposure.ee.values), ...(dim?.values ?? [])]);
  const unit = pick(axis.unit, lang);
  const line = (xs: number[], ys: number[]) => alignTo(xs, ys, grid).map((v) => (v === null ? null : v / axis.div));
  const csa = o.collateral?.csa ?? null;
  const im = o.initial_margin;
  const marks = sel.t < gridOf(o).length ? [{ x: gridOf(o)[sel.t], label: { en: `Year ${formatNumber(gridOf(o)[sel.t], 'en', { digits: 4 })}`, es: `Año ${formatNumber(gridOf(o)[sel.t], 'es', { digits: 4 })}` } }] : [];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'The EE of the netting set without collateral, with daily variation margin at a margin period of risk of 10 and of 20 business days (the CRE53.24 floor and the floor for illiquid or large netting sets), and with initial margin added. The initial margin is a regression proxy of the dynamic margin that ORE documents, never ISDA SIMM. The curves come from the four netting-set variants of the case.',
          es: 'La EE del conjunto de neteo sin colateral, con margen de variación diario a un periodo de riesgo de margen de 10 y de 20 días hábiles (el piso de CRE53.24 y el piso para conjuntos ilíquidos o grandes), y con margen inicial agregado. El margen inicial es una aproximación por regresión del margen dinámico que documenta ORE, nunca ISDA SIMM. Las curvas vienen de las cuatro variantes con conjunto de neteo del caso.',
        }}
      >
        <TallTables>
        <ChartOverTable
          chartMin="19rem"
          chart={
            <UPlotChart
              height="fill"
              x={{ values: grid, ...YEARS_AXIS }}
              y={{ label: collateralAxisLabel(Boolean(dim && withIm), axis.unit), format: { digits: 4 } }}
              series={[
                ...docs.map((d) => ({ label: MPOR_LABEL[d.id], values: line(d.o.exposure.time_grid_years, d.o.exposure.ee.values), color: MPOR_COLOR[d.id], width: d.id === 'netting-set' ? 2.6 : 2, ...(d.id === 'csa-mpor-20d' ? { dash: [6, 3] } : {}) })),
                ...(dim && withIm ? [{ label: { en: 'Dynamic initial margin (regression proxy)', es: 'Margen inicial dinámico (aproximación por regresión)' } as BiText, values: line(withIm.exposure.time_grid_years, dim.values), color: '--color-fg-subtle' as const, width: 1.6, dash: [2, 3] }] : []),
              ]}
              marks={marks}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c12-collateral">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Variant', es: 'Variante' }, lang)}</th>
                <th>{pick({ en: 'EEPE (USD)', es: 'EEPE (USD)' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Peak EE (USD)', es: 'EE máxima (USD)' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id} data-variant={d.id} className={d.o.variant === o.variant ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(MPOR_LABEL[d.id], lang)}</td>
                  <td>{cell(d.o.exposure.eepe.amount, lang)}</td>
                  <td className="ct-wide-only">{cell(Math.max(...d.o.exposure.ee.values), lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <dl className="ct-defs" style={DEFS_STYLE} data-table="c12-csa">
            <dt>{pick({ en: 'CSA of this variant', es: 'CSA de esta variante' }, lang)}</dt>
            <dd data-na={csa ? undefined : 'true'}>
              {csa
                ? pick(
                    {
                      en: `threshold ${cell(csa.threshold.amount, 'en')}, minimum transfer ${cell(csa.minimum_transfer_amount.amount, 'en')}, independent amount ${cell(csa.independent_amount.amount, 'en')} USD; margin period ${csa.mpor_business_days} business days; re-margined every ${csa.remargining_days} day; sticky-date close-out; ${csa.floor_reference}`,
                      es: `umbral ${cell(csa.threshold.amount, 'es')}, transferencia mínima ${cell(csa.minimum_transfer_amount.amount, 'es')}, monto independiente ${cell(csa.independent_amount.amount, 'es')} USD; periodo de margen ${csa.mpor_business_days} días hábiles; reajuste cada ${csa.remargining_days} día; cierre con fecha fija; piso de CRE53.24: 10 días hábiles, 20 para conjuntos ilíquidos o grandes`,
                    },
                    lang,
                  )
                : pick({ en: 'none: this variant has no CSA (the curves above come from the variants that do)', es: 'ninguno: esta variante no tiene CSA (las curvas de arriba vienen de las variantes que sí lo tienen)' }, lang)}
            </dd>
            <dt>{pick({ en: 'Initial margin', es: 'Margen inicial' }, lang)}</dt>
            <dd data-im={im ? 'regression-proxy' : 'none'} data-simm-used={im ? String(im.simm_used) : undefined}>
              {im
                ? pick(
                    {
                      en: `the ORE dynamic margin by regression of order ${im.regression_order}, quantile ${formatNumber(im.quantile, 'en', { percent: true, decimals: 0 })} (alpha ${formatNumber(im.alpha, 'en', { digits: 4 })}), horizon ${im.horizon_calendar_days} and margin period ${im.mpor_calendar_days} calendar days. ${pick(im.limit, 'en')}`,
                      es: `el margen dinámico de ORE por regresión de orden ${im.regression_order}, cuantil ${formatNumber(im.quantile, 'es', { percent: true, decimals: 0 })} (alfa ${formatNumber(im.alpha, 'es', { digits: 4 })}), horizonte de ${im.horizon_calendar_days} y periodo de margen de ${im.mpor_calendar_days} días corridos. ${pick(im.limit, 'es')}`,
                    },
                    lang,
                  )
                : pick({ en: 'none in this variant: only the variant with initial margin carries it, as a regression proxy and never SIMM', es: 'ninguno en esta variante: solo la variante con margen inicial lo trae, como aproximación por regresión y nunca SIMM' }, lang)}
            </dd>
            {o.collateral ? (
              <>
                <dt>{pick({ en: 'Limit', es: 'Límite' }, lang)}</dt>
                <dd>{pick(o.collateral.limit, lang)}</dd>
              </>
            ) : null}
          </dl>
          <p className="ct-note">{pick({ en: `The axis is in ${unit}; the table keeps the whole amounts.`, es: `El eje está en ${unit}; la tabla guarda los montos completos.` }, lang)}</p>
        </ChartOverTable>
        </TallTables>
      </PlotCard>
    </ViewsRow>
  );
}

/** The sum of the single-trade EE against the netted EE, and the benefit between them. */
export function NettingView({ sel }: { sel: C12Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The netting benefit', es: 'El beneficio del neteo' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SWAP} />;
  const nb = o.netting_benefit;
  const grid = gridOf(o);
  const at = Math.min(sel.t, grid.length - 1);
  const axis = axisOf([...nb.sum_of_single_trade_ee.values, ...nb.netted_ee.values, ...nb.benefit.values]);
  const div = (p: C12Profile) => p.values.map((v) => v / axis.div);
  const single = nb.per_trade_ee.length === 1;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: `Netting works on the sum of the swap values, not on the sum of their positive parts: the netted EE is never above the sum of the single-trade EE, and the difference is the benefit. A one-swap book has nothing to net, so the benefit is zero.${o.collateral ? ' In this variant the comparison is made without collateral; the EE after margin is in the collateral view.' : ''}`,
          es: `El neteo opera sobre la suma de los valores de las permutas, no sobre la suma de sus partes positivas: la EE neteada nunca supera la suma de las EE individuales, y la diferencia es el beneficio. Una cartera de una sola permuta no tiene qué netear, así que el beneficio es cero.${o.collateral ? ' En esta variante la comparación se hace sin colateral; la EE tras el margen está en la vista del colateral.' : ''}`,
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: grid, ...YEARS_AXIS }}
              y={{ label: { en: `EE (${pick(axis.unit, 'en')})`, es: `EE (${pick(axis.unit, 'es')})` }, format: { digits: 4 } }}
              series={[
                ...nb.per_trade_ee.map((t, i) => ({ label: { en: `EE of ${t.trade_id}`, es: `EE de ${t.trade_id}` } as BiText, values: div(t.ee), color: (['--color-fg-subtle', '--color-fg-faint', '--color-magenta', '--color-warn'] as const)[i % 4], width: 1.3, dash: [3, 3] })),
                ...(single ? [] : [{ label: { en: 'Sum of single-trade EE', es: 'Suma de EE individuales' } as BiText, values: div(nb.sum_of_single_trade_ee), color: '--color-accent' as const, width: 2.4 }]),
                { label: { en: 'Netted EE', es: 'EE neteada' }, values: div(nb.netted_ee), color: '--color-good', width: 2.6 },
                { label: { en: 'Netting benefit', es: 'Beneficio del neteo' }, values: div(nb.benefit), color: '--color-bad', width: 2, dash: [6, 3] },
              ]}
              marks={[{ x: grid[at], label: { en: `Year ${formatNumber(grid[at], 'en', { digits: 4 })}`, es: `Año ${formatNumber(grid[at], 'es', { digits: 4 })}` } }]}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c12-netting">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: `At year ${formatNumber(grid[at], 'en', { digits: 4 })}`, es: `En el año ${formatNumber(grid[at], 'es', { digits: 4 })}` }, lang)}</th>
                <th>{pick({ en: 'EE (USD)', es: 'EE (USD)' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {nb.per_trade_ee.map((t) => (
                <tr key={t.trade_id} data-trade={t.trade_id}>
                  <td className="ct-text">{pick({ en: `EE of ${t.trade_id}`, es: `EE de ${t.trade_id}` }, lang)}</td>
                  <td>{cell(t.ee.values[at], lang)}</td>
                </tr>
              ))}
              <tr data-row="sum">
                <td className="ct-text">{pick({ en: 'Sum of single-trade EE', es: 'Suma de EE individuales' }, lang)}</td>
                <td>{cell(nb.sum_of_single_trade_ee.values[at], lang)}</td>
              </tr>
              <tr data-row="netted">
                <td className="ct-text">{pick(o.collateral ? { en: 'Netted EE, without collateral', es: 'EE neteada, sin colateral' } : { en: 'Netted EE', es: 'EE neteada' }, lang)}</td>
                <td>{cell(nb.netted_ee.values[at], lang)}</td>
              </tr>
              <tr data-row="benefit">
                <td className="ct-text"><strong>{pick({ en: 'Netting benefit', es: 'Beneficio del neteo' }, lang)}</strong></td>
                <td>{cell(nb.benefit.values[at], lang)}</td>
              </tr>
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

const SENS_COLORS = { base: '--color-accent', 'a-plus-1se': '--color-good', 'a-minus-1se': '--color-warn', 'sigma-plus-1se': '--color-magenta', 'sigma-minus-1se': '--color-bad' } as const;

/** EE and PFE with the reversion a and the volatility sigma at the base estimate and at plus and minus one standard error. */
export function SensitivityView({ sel }: { sel: C12Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'Sensitivity to the calibration', es: 'Sensibilidad a la calibración' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SWAP} />;
  const grid = gridOf(o);
  const cases = CASE_ORDER.flatMap((id) => {
    const c = sensitivityOf(o, id);
    return c ? [c] : [];
  });
  const axisEe = axisOf(cases.flatMap((c) => c.ee.values));
  const axisPfe = axisOf(cases.flatMap((c) => c.pfe.values));
  const note: BiText = {
    en: 'The short-rate parameters are estimated on data before the back-test date, so they carry a standard error. Each line moves the reversion a or the volatility sigma by one standard error and re-runs the exposure on the same paths.',
    es: 'Los parámetros de la tasa corta se estiman con datos anteriores a la fecha de la prueba retrospectiva, así que traen un error estándar. Cada línea mueve la reversión a o la volatilidad sigma en un error estándar y repite la exposición sobre las mismas trayectorias.',
  };
  const chart = (kind: 'ee' | 'pfe', axis: ReturnType<typeof axisOf>) => (
    <UPlotChart
      height="fill"
      x={{ values: grid, ...YEARS_AXIS }}
      y={{ label: { en: `${kind === 'ee' ? 'EE' : 'PFE'} (${pick(axis.unit, 'en')})`, es: `${kind === 'ee' ? 'EE' : 'PFE'} (${pick(axis.unit, 'es')})` }, format: { digits: 4 } }}
      series={cases.map((c) => ({ label: text(CASE_TEXT, c.case), values: c[kind].values.map((v) => v / axis.div), color: SENS_COLORS[c.case], width: c.case === sel.caseId ? 3 : 1.6, ...(c.case === 'base' ? {} : { dash: [6, 3] }) }))}
    />
  );
  return (
    <ViewsRow>
      <PlotCard fill title={{ en: 'Expected exposure by calibration case', es: 'Exposición esperada por caso de calibración' }} {...card} note={note}>
        <ChartOverTable chart={chart('ee', axisEe)}>
          <table className="caos-table ct-wrap-head" data-table="c12-sensitivity-ee">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Case', es: 'Caso' }, lang)}</th>
                <th>{pick({ en: 'a', es: 'a' }, lang)}</th>
                <th>{pick({ en: 'Sigma', es: 'Sigma' }, lang)}</th>
                <th>{pick({ en: 'EEPE (USD)', es: 'EEPE (USD)' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.case} data-case={c.case} className={c.case === sel.caseId ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(text(CASE_TEXT, c.case), lang)}</td>
                  <td>{formatNumber(c.a, lang, { digits: 4 })}</td>
                  <td>{formatNumber(c.sigma, lang, { digits: 4 })}</td>
                  <td>{cell(c.eepe.amount, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
      <PlotCard fill title={{ en: 'Potential future exposure by calibration case', es: 'Exposición futura potencial por caso de calibración' }} {...card}>
        <ChartOverTable chart={chart('pfe', axisPfe)}>
          <table className="caos-table ct-wrap-head" data-table="c12-sensitivity-pfe">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Case', es: 'Caso' }, lang)}</th>
                <th>{pick({ en: 'PFE peak (USD)', es: 'Pico del PFE (USD)' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.case} data-case={c.case} className={c.case === sel.caseId ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(text(CASE_TEXT, c.case), lang)}</td>
                  <td>{cell(c.pfe_peak.amount, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
