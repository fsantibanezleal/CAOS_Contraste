// C14's Shocks group: how large the loss is under each of the six prescribed shocks (delta EVE and, for the parallel
// shocks, delta NII), the shapes of the six shock curves, and the outlier test against 15 percent of Tier 1. A positive
// delta is a loss and the document's convention is printed on every view that shows one; the numbers are the bake's.
import { Fragment, type ReactNode } from 'react';
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart, type UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable, MaybeNumber } from '../c06/format';
import { useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { IrrbbTestsTable, UnavailableCard, docText } from './C14Common';
import {
  CALIBRATION_SHORT, CALIBRATION_TEXT, NMD_LONG, NMD_TEXT, ORIGIN_TEXT, SHOCK_ORDER, SHOCK_TEXT, axisOf, cell, outputsOf, scaleUnit, scenarioFor, scenarioOf, text,
  type C14Sel,
} from './selection';
import { IRRBB_SOURCE_RULES, localise } from './localise';

const SHARE = (v: number | null | undefined, lang: 'en' | 'es') => formatNumber(v, lang, { percent: true, decimals: 2 });

/** The prescribed shocks in rows, the delta EVE of the scenario in focus in currency and as a share of Tier 1, and the NII of the parallel ones. */
/** A shock form of the models document ("exp(-t_k / x)") as the symbols a reader reads: a minus sign and the subscript k (R3 c15 n2). */
export function formOf(form: string): ReactNode {
  const parts = form.replace(/-/g, '\u2212').split('t_k');
  return (
    <>
      {parts.map((p, j) => (
        <Fragment key={j}>
          {p}
          {j < parts.length - 1 ? <>t<sub>k</sub></> : null}
        </Fragment>
      ))}
    </>
  );
}

export function EveByShockView({ sel }: { sel: C14Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const s = scenarioFor(sel);
  if (!s) {
    return <UnavailableCard sel={sel} title={{ en: 'Delta EVE by shock', es: 'Delta EVE por choque' }} reason={{ en: 'Not available: this document has no scenario for this calibration and deposit assumption.', es: 'No disponible: este documento no trae un escenario para esta calibración y este supuesto de depósitos.' }} />;
  }
  const other = scenarioOf(o, sel.calibration === '2024' ? '2016' : '2024', sel.nmd);
  const axis = axisOf(o, s.shocks.map((r) => r.delta_eve));
  const unit = pick(scaleUnit(o), lang);
  const z = s.shock_size;
  const sizes = { en: `${z.parallel_bp} bp parallel, ${z.short_bp} bp short, ${z.long_bp} bp long`, es: `${z.parallel_bp} pb paralelo, ${z.short_bp} pb corto, ${z.long_bp} pb largo` };
  const origin = text(ORIGIN_TEXT, z.origin);
  const labelled = z.origin === 'contraste-estimate' && z.label ? ` ${pick(z.label, lang)}${z.method ? ` (${z.method})` : ''}.` : '';
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `Delta EVE by shock: ${text(CALIBRATION_TEXT, sel.calibration).en}, ${text(NMD_TEXT, sel.nmd).en.toLowerCase()} NMD`, es: `Delta EVE por choque: ${text(CALIBRATION_TEXT, sel.calibration).es.toLowerCase()}, NMD ${text(NMD_TEXT, sel.nmd).es.toLowerCase()}` }}
        {...card}
        note={{
          en: `${o.sign_convention.statement.en} ${text(NMD_LONG, sel.nmd).en}. Sizes: ${sizes.en} (${origin.en}).${labelled}`,
          es: `${o.sign_convention.statement.es} ${text(NMD_LONG, sel.nmd).es}. Tamaños: ${sizes.es} (${origin.es}).${labelled}`,
        }}
      >
        <ChartOverTable
          chartMin="13rem"
          chart={
            <BarChart
              title={{ en: 'Delta EVE by prescribed shock', es: 'Delta EVE por choque prescrito' }}
              height="fill"
              orientation="horizontal"
              data={s.shocks.map((r) => ({ id: r.shock, label: text(SHOCK_TEXT, r.shock), value: r.delta_eve / axis.div, tone: r.delta_eve > 0 ? ('bad' as const) : ('good' as const), highlight: r.shock === sel.shock }))}
              axis={{ label: { en: 'Delta EVE, positive is a loss', es: 'Delta EVE, positivo es una pérdida' }, unit: axis.unit, format: { digits: 4 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="eve-by-shock">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Shock', es: 'Choque' }, lang)}</th>
                <th>{pick({ en: `Delta EVE (${unit})`, es: `Delta EVE (${unit})` }, lang)}</th>
                <th>{pick({ en: 'Share of Tier 1', es: 'Parte del capital N1' }, lang)}</th>
                <th>{pick({ en: `Delta NII (${unit})`, es: `Delta NII (${unit})` }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Floored buckets', es: 'Tramos con piso' }, lang)}</th>
                <th className="ct-wide-only" data-col="other-calibration">
                  {pick({ en: `Delta EVE, ${text(CALIBRATION_TEXT, sel.calibration === '2024' ? '2016' : '2024').en.toLowerCase()}`, es: `Delta EVE, ${text(CALIBRATION_TEXT, sel.calibration === '2024' ? '2016' : '2024').es.toLowerCase()}` }, lang)}
                </th>
              </tr>
            </thead>
            <tbody>
              {SHOCK_ORDER.map((id) => {
                const r = s.shocks.find((x) => x.shock === id);
                if (!r) return null;
                const r2 = other?.shocks.find((x) => x.shock === id) ?? null;
                return (
                  <tr key={id} data-shock={id} data-loss={r.delta_eve > 0} className={id === sel.shock ? 'ct-current' : undefined}>
                    <td className="ct-text">{pick(text(SHOCK_TEXT, id), lang)}</td>
                    <td>{cell(r.delta_eve, lang)}</td>
                    <td>{SHARE(r.delta_eve_share_tier1, lang)}</td>
                    <td>
                      <MaybeNumber value={r.delta_nii} reason={r.delta_nii_reason ? pick(r.delta_nii_reason, lang) : null} format={(v) => cell(v, lang)} />
                    </td>
                    <td className="ct-wide-only">{formatNumber(r.floor_bound_buckets.length, lang, { decimals: 0 })}</td>
                    <td className="ct-wide-only" data-col="other-calibration" data-na={r2 ? undefined : 'true'}>{r2 ? cell(r2.delta_eve, lang) : formatNumber(null, lang)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <IrrbbTestsTable variant={sel.data.variant} only={(t) => t.test_id === 'irrbb.srp31_92_goldens' || t.test_id === 'irrbb.eve_sum_of_parts'} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

const SHAPE_COLORS = ['--color-accent', '--color-magenta', '--color-warn', '--color-good', '--color-bad', '--color-fg-subtle'] as const;

/** The six shock curves over the 19 bucket midpoints, in basis points before the floor, with the buckets where the floor binds. */
export function ShapesView({ sel }: { sel: C14Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const s = scenarioFor(sel);
  if (!s) {
    return <UnavailableCard sel={sel} title={{ en: 'The shock shapes', es: 'Las formas de los choques' }} reason={{ en: 'Not available: this document has no scenario for this calibration and deposit assumption.', es: 'No disponible: este documento no trae un escenario para esta calibración y este supuesto de depósitos.' }} />;
  }
  const midpoints = o.ladder[0].repricing_gap.map((g) => g.midpoint_years);
  const shape = (sel.data.models as unknown as { fit?: { shock_shape?: { x: number; steepener_short: number; steepener_long: number; flattener_short: number; flattener_long: number; short_form: string; long_form: string; reference: string } } } | undefined)?.fit?.shock_shape ?? null;
  const share = (v: number) => formatNumber(v, lang, { percent: true, decimals: 2 });
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The six shock curves', es: 'Las seis curvas de choque' }}
        {...card}
        note={{
          en: 'Each curve is the shift in basis points at the midpoint of the 19 time buckets, before the post-shock floor. The parallel shocks are flat, the short-rate shocks decay with the term, and the steepener and the flattener rotate around the short rate.',
          es: 'Cada curva es el desplazamiento en puntos base en el punto medio de los 19 tramos, antes del piso posterior al choque. Los choques paralelos son planos, los de tasas cortas decaen con el plazo, y el empinamiento y el aplanamiento rotan en torno a la tasa corta.',
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: midpoints, label: { en: 'Bucket midpoint', es: 'Punto medio del tramo' }, unit: { en: 'years', es: 'años' }, format: { digits: 3 } }}
              y={{ label: { en: 'Shift of the rate', es: 'Desplazamiento de la tasa' }, unit: { en: 'bp', es: 'pb' }, format: { decimals: 0 } }}
              series={s.shocks.map((r, i) => ({ label: text(SHOCK_TEXT, r.shock), values: r.shape_bp, color: SHAPE_COLORS[i % SHAPE_COLORS.length], width: 2.2, ...(i >= 3 ? { dash: [6, 3] } : {}) }))}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="shock-shapes">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Shock', es: 'Choque' }, lang)}</th>
                <th>{pick({ en: 'Shift at the shortest bucket', es: 'Desplazamiento en el tramo más corto' }, lang)}</th>
                <th>{pick({ en: 'Shift at the longest bucket', es: 'Desplazamiento en el tramo más largo' }, lang)}</th>
                <th>{pick({ en: 'Buckets where the floor binds', es: 'Tramos donde rige el piso' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {s.shocks.map((r) => (
                <tr key={r.shock} data-shock={r.shock} data-floored={r.floor_bound_buckets.length} className={r.shock === sel.shock ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(text(SHOCK_TEXT, r.shock), lang)}</td>
                  <td>{`${formatNumber(r.shape_bp[0], lang, { decimals: 0 })} ${pick({ en: 'bp', es: 'pb' }, lang)}`}</td>
                  <td>{`${formatNumber(r.shape_bp[r.shape_bp.length - 1], lang, { decimals: 0 })} ${pick({ en: 'bp', es: 'pb' }, lang)}`}</td>
                  <td>{r.floor_bound_buckets.length === 0 ? pick({ en: 'none', es: 'ninguno' }, lang) : `${formatNumber(r.floor_bound_buckets.length, lang, { decimals: 0 })} ${pick({ en: 'of', es: 'de' }, lang)} ${midpoints.length}`}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {shape ? (
            <dl className="ct-defs" data-table="shock-shape-constants">
              <dt>{pick({ en: 'Short-rate form', es: 'Forma de tasa corta' }, lang)}</dt>
              <dd translate="no" data-form={shape.short_form}>{formOf(shape.short_form)}</dd>
              <dt>{pick({ en: 'Long-rate form', es: 'Forma de tasa larga' }, lang)}</dt>
              <dd translate="no" data-form={shape.long_form}>{formOf(shape.long_form)}</dd>
              <dt>{pick({ en: 'Decay constant x', es: 'Constante de decaimiento x' }, lang)}</dt>
              <dd>{`${formatNumber(shape.x, lang, { decimals: 0 })} ${pick({ en: 'years', es: 'años' }, lang)}`}</dd>
              <dt>{pick({ en: 'Steepener', es: 'Empinamiento' }, lang)}</dt>
              <dd>{pick({ en: `${share(shape.steepener_short)} of the short-rate size, ${share(shape.steepener_long)} of the long-rate size`, es: `${share(shape.steepener_short)} del tamaño de tasa corta, ${share(shape.steepener_long)} del tamaño de tasa larga` }, lang)}</dd>
              <dt>{pick({ en: 'Flattener', es: 'Aplanamiento' }, lang)}</dt>
              <dd>{pick({ en: `${share(shape.flattener_short)} of the short-rate size, ${share(shape.flattener_long)} of the long-rate size`, es: `${share(shape.flattener_short)} del tamaño de tasa corta, ${share(shape.flattener_long)} del tamaño de tasa larga` }, lang)}</dd>
              <dt>{pick({ en: 'Reference', es: 'Referencia' }, lang)}</dt>
              <dd>{docText(shape.reference, lang)}</dd>
            </dl>
          ) : (
            <p className="ct-note" data-state="unavailable">{pick({ en: 'Not available: the models artifact carries no shock-shape constants.', es: 'No disponible: el artefacto de modelos no trae las constantes de forma de los choques.' }, lang)}</p>
          )}
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The chart of the outlier view: the share of Tier 1 of every shock with and without the behavioural assumption, and the 15 percent line. */
export function outlierChart(sel: C14Sel | null): Pick<UPlotChartProps, 'x' | 'y' | 'series' | 'yMarks'> | null {
  const o = outputsOf(sel);
  if (!sel || !o) return null;
  const share = (nmd: string) => {
    const s = scenarioOf(o, sel.calibration, nmd);
    return SHOCK_ORDER.map((id) => s?.shocks.find((r) => r.shock === id)?.delta_eve_share_tier1 ?? null);
  };
  return {
    x: { values: SHOCK_ORDER.map((_, i) => i + 1), label: { en: 'Shock (numbered as in the table)', es: 'Choque (numerado como en la tabla)' }, format: { decimals: 0 } },
    y: { label: { en: 'Delta EVE over Tier 1', es: 'Delta EVE sobre el capital de nivel 1' }, format: { percent: true, decimals: 1 } },
    series: [
      { label: NMD_TEXT.behavioural, values: share('behavioural'), color: '--color-accent', width: 2.4, mode: 'points', size: 12 },
      { label: NMD_TEXT.contractual, values: share('contractual'), color: '--color-magenta', width: 2.4, mode: 'points', size: 12 },
    ],
    yMarks: [{ y: 0.15, label: { en: 'Outlier threshold: 15% of Tier 1', es: 'Umbral de valor atípico: 15 % del capital de nivel 1' }, tone: 'bad' }],
  };
}

/** Would the outlier test have fired: every scenario's risk measure over Tier 1 against the 15 percent threshold. */
export function OutlierView({ sel }: { sel: C14Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const chart = outlierChart(sel);
  if (!sel || !o || !chart) return <Pending />;
  const unit = pick(scaleUnit(o), lang);
  const note: BiText = {
    en: 'The outlier test (SRP31.82 to SRP31.83) compares the largest EVE loss over the six shocks with 15 percent of Tier 1 capital. The line is that threshold; a point above it fires the test. Each shock is a point, numbered as in the table.',
    es: 'La prueba de valor atípico (SRP31.82 a SRP31.83) compara la mayor pérdida de EVE entre los seis choques con el 15 por ciento del capital de nivel 1. La línea es ese umbral; un punto sobre ella activa la prueba. Cada choque es un punto, numerado como en la tabla.',
  };
  return (
    <ViewsRow>
      <PlotCard fill title={{ en: `The outlier test: ${text(CALIBRATION_TEXT, sel.calibration).en}`, es: `La prueba de valor atípico: ${text(CALIBRATION_TEXT, sel.calibration).es.toLowerCase()}` }} {...card} note={note}>
        <ChartOverTable
          chart={<UPlotChart height="fill" x={chart.x} y={chart.y} series={chart.series} yMarks={chart.yMarks} readout={(i) => `${pick(text(SHOCK_TEXT, SHOCK_ORDER[i]), lang)}`} />}
        >
          <table className="caos-table ct-wrap-head" data-table="outlier" data-threshold="0.15">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Scenario', es: 'Escenario' }, lang)}</th>
                <th>{pick({ en: `Risk measure (${unit})`, es: `Medida de riesgo (${unit})` }, lang)}</th>
                <th>{pick({ en: `Tier 1 (${unit})`, es: `Capital N1 (${unit})` }, lang)}</th>
                <th>{pick({ en: 'Ratio', es: 'Razón' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Outlier', es: 'Valor atípico' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Worst shock', es: 'Peor choque' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.scenarios.map((s) => (
                <tr key={`${s.calibration}-${s.nmd_assumption}`} data-scenario={`${s.calibration}-${s.nmd_assumption}`} data-breached={s.outlier.breached} className={s.calibration === sel.calibration && s.nmd_assumption === sel.nmd ? 'ct-current' : undefined}>
                  <td className="ct-text" title={pick(NMD_LONG[s.nmd_assumption], lang)}>{`${pick(text(CALIBRATION_SHORT, s.calibration), lang)}, ${pick(text(NMD_TEXT, s.nmd_assumption), lang).toLowerCase()}`}</td>
                  <td>{cell(s.outlier.eve_risk_measure, lang)}</td>
                  <td>{cell(s.outlier.tier1, lang)}</td>
                  <td>{SHARE(s.outlier.ratio, lang)}</td>
                  <td className="ct-text">{pick(s.outlier.breached ? { en: 'fires', es: 'se activa' } : { en: 'does not fire', es: 'no se activa' }, lang)}</td>
                  <td className="ct-text ct-wide-only" data-na={s.worst_shock ? undefined : 'true'}>{s.worst_shock ? pick(text(SHOCK_TEXT, s.worst_shock), lang) : pick({ en: 'no loss in any shock', es: 'sin pérdida en ningún choque' }, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="ct-note">{localise(o.scenarios[0].outlier.reference, lang, IRRBB_SOURCE_RULES)}</p>
          <table className="caos-table ct-wrap-head" data-table="shock-numbers">
            <thead>
              <tr>
                <th>{pick({ en: 'No.', es: 'N.º' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Shock', es: 'Choque' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {SHOCK_ORDER.map((id, i) => (
                <tr key={id} data-shock-number={i + 1}>
                  <td>{i + 1}</td>
                  <td className="ct-text">{pick(text(SHOCK_TEXT, id), lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
