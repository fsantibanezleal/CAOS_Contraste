// C15's Floors and thresholds group: the effect of the post-shock floors of Annex 1 (-2 percent for the UR rates, 0 percent
// for the others, or the pre-shock rate if lower) on each leg and shock where one binds, and the three tests that make a
// bank prioritised (delta NII over 5 percent of Tier 1, delta EVE over 15 percent of Tier 1, delta NII over 18 percent of
// the twelve-month net interest and indexation margin), each drawn against its threshold as a line.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart, type UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable } from '../c06/format';
import { useCard, type Bi } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { LEG_SHORT, SHOCK_TEXT, axisOf, moneyDoc, outputsOf, scaleUnit, text, type C15Sel } from './selection';

const cell = (v: number | null | undefined, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });
const SHARE = (v: number | null | undefined, lang: 'en' | 'es') => formatNumber(v, lang, { percent: true, decimals: 2 });

const MEASURE_TEXT: Record<string, Bi> = {
  'delta-eve': { en: 'Delta EVE', es: 'Delta EVE' },
  'delta-nii': { en: 'Delta NII', es: 'Delta NII' },
};

/** Where a post-shock floor binds: the measure with and without the floor, and what the floor changes. */
export function FloorsView({ sel }: { sel: C15Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const f = o.floors;
  const doc = moneyDoc(o);
  const unit = pick(scaleUnit(doc), lang);
  const axis = axisOf(doc, f.effects.map((e) => e.effect));
  const rowLabel = (e: (typeof f.effects)[number]): BiText => {
    const leg = text(LEG_SHORT, e.leg);
    const shock = text(SHOCK_TEXT, e.shock);
    const measure = text(MEASURE_TEXT, e.measure);
    return { en: `${leg.en}, ${measure.en}, ${shock.en.toLowerCase()}`, es: `${leg.es}, ${measure.es}, ${shock.es.toLowerCase()}` };
  };
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The post-shock floors', es: 'Los pisos posteriores al choque' }}
        {...card}
        note={{
          en: 'After a shock the rate of each bucket cannot fall below its floor: -2 percent for the UR rates and 0 percent for the others, or the pre-shock rate if that is lower. Each row is a leg, a measure and a shock where the floor binds; the effect is the measure with the floor minus the measure without it.',
          es: 'Después de un choque la tasa de cada tramo no puede caer bajo su piso: -2 por ciento para las tasas UR y 0 por ciento para las demás, o la tasa previa al choque si es menor. Cada fila es un tramo, una medida y un choque donde el piso rige; el efecto es la medida con el piso menos la medida sin él.',
        }}
      >
        <ChartOverTable
          chartMin={`${Math.min(Math.max(f.effects.length, 2), 24) * 1.5 + 3}rem`}
          chart={
            f.effects.length === 0 ? (
              <p className="caos-pending" data-state="unavailable">{pick({ en: 'No floor binds in this variant: the measures with and without the floor are the same.', es: 'En esta variante ningún piso rige: las medidas con y sin piso son las mismas.' }, lang)}</p>
            ) : (
              <BarChart
                title={{ en: 'Effect of the floor on each measure', es: 'Efecto del piso en cada medida' }}
                height="fill"
                orientation="horizontal"
                data={f.effects.map((e) => ({ id: `${e.leg}-${e.measure}-${e.shock}`, label: rowLabel(e), value: e.effect / axis.div, tone: e.effect > 0 ? ('bad' as const) : ('good' as const) }))}
                axis={{ label: { en: 'Measure with the floor minus without it', es: 'Medida con el piso menos sin él' }, unit: axis.unit, format: { digits: 4 } }}
              />
            )
          }
        >
          <dl className="ct-defs" data-table="floor-rule">
            <dt>{pick({ en: 'Floor of the UR rates', es: 'Piso de las tasas UR' }, lang)}</dt>
            <dd>{SHARE(f.ur_floor, lang)}</dd>
            <dt>{pick({ en: 'Floor of the other rates', es: 'Piso de las demás tasas' }, lang)}</dt>
            <dd>{SHARE(f.other_floor, lang)}</dd>
            <dt>{pick({ en: 'Rule', es: 'Regla' }, lang)}</dt>
            <dd>{pick(f.rule, lang)}</dd>
          </dl>
          <table className="caos-table ct-wrap-head" data-table="floor-effects">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Leg', es: 'Tramo' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Measure', es: 'Medida' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Shock', es: 'Choque' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Floored buckets', es: 'Tramos con piso' }, lang)}</th>
                <th>{pick({ en: `With floor (${unit})`, es: `Con piso (${unit})` }, lang)}</th>
                <th>{pick({ en: `Without floor (${unit})`, es: `Sin piso (${unit})` }, lang)}</th>
                <th>{pick({ en: 'Effect', es: 'Efecto' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {f.effects.map((e) => (
                <tr key={`${e.leg}-${e.measure}-${e.shock}`} data-leg={e.leg} data-measure={e.measure} data-shock={e.shock}>
                  <td className="ct-text">{pick(text(LEG_SHORT, e.leg), lang)}</td>
                  <td className="ct-text">{pick(text(MEASURE_TEXT, e.measure), lang)}</td>
                  <td className="ct-text">{pick(text(SHOCK_TEXT, e.shock), lang)}</td>
                  <td className="ct-wide-only">{formatNumber(e.buckets_floored, lang, { decimals: 0 })}</td>
                  <td>{cell(e.delta_with_floor, lang)}</td>
                  <td>{cell(e.delta_without_floor, lang)}</td>
                  <td>{cell(e.effect, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

const TEST_TEXT: Record<string, { name: BiText; base: BiText }> = {
  'nii-tier1': { name: { en: 'Delta NII over Tier 1', es: 'Delta NII sobre el capital de nivel 1' }, base: { en: 'Tier 1 capital', es: 'Capital de nivel 1' } },
  'eve-tier1': { name: { en: 'Delta EVE over Tier 1', es: 'Delta EVE sobre el capital de nivel 1' }, base: { en: 'Tier 1 capital', es: 'Capital de nivel 1' } },
  'nii-margin': { name: { en: 'Delta NII over the margin', es: 'Delta NII sobre el margen' }, base: { en: '12-month net interest and indexation margin', es: 'Margen neto de intereses y reajustes a 12 meses' } },
};

/** The chart of the thresholds view: the ratio of each test and its threshold as a line, 5, 15 and 18 percent. */
export function thresholdsChart(sel: C15Sel | null): Pick<UPlotChartProps, 'x' | 'y' | 'series'> | null {
  const o = outputsOf(sel);
  if (!sel || !o) return null;
  const tests = o.thresholds.tests;
  return {
    x: { values: tests.map((_, i) => i + 1), label: { en: 'Test (numbered as in the table)', es: 'Prueba (numerada como en la tabla)' }, format: { decimals: 0 } },
    y: { label: { en: 'Ratio of the measure to its base', es: 'Razón de la medida a su base' }, format: { percent: true, decimals: 0 } },
    series: [
      { label: { en: 'Measured', es: 'Medido' }, values: tests.map((t) => t.ratio), color: '--color-accent', width: 2.4, mode: 'points', size: 12 },
      { label: { en: 'Threshold of the test', es: 'Umbral de la prueba' }, values: tests.map((t) => t.threshold), color: '--color-bad', width: 2.2, dash: [6, 3] },
    ],
  };
}

/** The three prioritised-bank tests of Annex 1, each measured against its threshold, and whether the bank is prioritised. */
export function ThresholdsView({ sel }: { sel: C15Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const chart = thresholdsChart(sel);
  if (!sel || !o || !chart) return <Pending />;
  const t = o.thresholds;
  const unit = pick(scaleUnit(moneyDoc(o)), lang);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The prioritised-bank tests', es: 'Las pruebas de banco priorizado' }}
        {...card}
        note={{
          en: 'A bank is prioritised when any of three tests is breached: delta NII over 5 percent of Tier 1, delta EVE over 15 percent of Tier 1, or delta NII over 18 percent of the twelve-month net interest and indexation margin. The dashed line joins the three thresholds, one per test, and a point above the line at its own test breaches.',
          es: 'Un banco es priorizado cuando se supera cualquiera de tres pruebas: delta NII sobre el 5 por ciento del capital de nivel 1, delta EVE sobre el 15 por ciento del capital de nivel 1, o delta NII sobre el 18 por ciento del margen neto de intereses y reajustes a doce meses. La línea punteada une los tres umbrales, uno por prueba, y un punto sobre la línea en su propia prueba la supera.',
        }}
      >
        <ChartOverTable
          chart={<UPlotChart height="fill" x={chart.x} y={chart.y} series={chart.series} readout={(i) => `${pick(TEST_TEXT[t.tests[i].id].name, lang)}`} />}
        >
          <table className="caos-table ct-wrap-head" data-table="thresholds" data-prioritised={t.prioritised}>
            <thead>
              <tr>
                <th>{pick({ en: 'No.', es: 'N.º' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Test', es: 'Prueba' }, lang)}</th>
                <th>{pick({ en: `Measure (${unit})`, es: `Medida (${unit})` }, lang)}</th>
                <th>{pick({ en: `Base (${unit})`, es: `Base (${unit})` }, lang)}</th>
                <th>{pick({ en: 'Ratio', es: 'Razón' }, lang)}</th>
                <th>{pick({ en: 'Threshold', es: 'Umbral' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Result', es: 'Resultado' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {t.tests.map((x, i) => (
                <tr key={x.id} data-test-id={x.id} data-breached={x.breached}>
                  <td>{i + 1}</td>
                  <td className="ct-text" title={pick(TEST_TEXT[x.id].base, lang)}>{pick(TEST_TEXT[x.id].name, lang)}</td>
                  <td>{cell(x.measure, lang)}</td>
                  <td>{cell(x.base, lang)}</td>
                  <td>{SHARE(x.ratio, lang)}</td>
                  <td>{SHARE(x.threshold, lang)}</td>
                  <td className="ct-text">{pick(x.breached ? { en: 'breached', es: 'superada' } : { en: 'within the threshold', es: 'dentro del umbral' }, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <dl className="ct-defs" data-table="thresholds-base">
            <dt>{pick({ en: `Tier 1 capital (${unit})`, es: `Capital de nivel 1 (${unit})` }, lang)}</dt>
            <dd>{cell(t.tier1, lang)}</dd>
            <dt>{pick({ en: `Net interest and indexation margin, 12 months (${unit})`, es: `Margen neto de intereses y reajustes, 12 meses (${unit})` }, lang)}</dt>
            <dd>{cell(t.net_interest_and_indexation_margin_12m, lang)}</dd>
            <dt>{pick({ en: 'The bank', es: 'El banco' }, lang)}</dt>
            <dd>{pick(t.prioritised ? { en: 'is prioritised: at least one test is breached', es: 'es priorizado: al menos una prueba es superada' } : { en: 'is not prioritised: no test is breached', es: 'no es priorizado: ninguna prueba es superada' }, lang)}</dd>
            <dt>{pick({ en: 'Reference', es: 'Referencia' }, lang)}</dt>
            <dd>{t.reference}</dd>
          </dl>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
