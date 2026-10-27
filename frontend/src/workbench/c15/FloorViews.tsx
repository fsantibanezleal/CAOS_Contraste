// C15's Floors and thresholds group: the effect of the post-shock floors of Annex 1 (-2 percent for the UR rates, 0 percent
// for the others, or the pre-shock rate if lower) on each leg and shock where one binds, and the three tests that make a
// bank prioritised (delta NII over 5 percent of Tier 1, delta EVE over 15 percent of Tier 1, delta NII over 18 percent of
// the twelve-month net interest and indexation margin), each drawn against its threshold as a line.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart, type UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable } from '../c06/format';
import { useCard, type Bi } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { docText } from '../c14/C14Common';
import { LEG_SHORT, SHOCK_TEXT, moneyDoc, outputsOf, scaleUnit, text, type C15Sel } from './selection';

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
  const distLabel = (x: (typeof f.distances)[number]): BiText => {
    const leg = text(LEG_SHORT, x.leg);
    const shock = text(SHOCK_TEXT, x.shock);
    const measure = text(MEASURE_TEXT, x.measure);
    return { en: `${leg.en}, ${measure.en}, ${shock.en.toLowerCase()}`, es: `${leg.es}, ${measure.es}, ${shock.es.toLowerCase()}` };
  };
  const lowest = f.distances.reduce((m, x) => (x.distance_bp < m.distance_bp ? x : m), f.distances[0]);
  const nBind = f.distances.filter((x) => x.binds).length;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The post-shock floors', es: 'Los pisos posteriores al choque' }}
        {...card}
        note={{
          en: 'After a shock the rate of each bucket cannot fall below its floor: -2 percent for the UR rates and 0 percent for the others, or the pre-shock rate if that is lower. Each bar is the distance of a leg and a shock to its floor: the lowest post-shock rate minus the floor, in basis points. The floor is the zero line; a bar at or below it is a floor that binds, and its effect on the measure is in the table.',
          es: 'Después de un choque la tasa de cada tramo no puede caer bajo su piso: -2 por ciento para las tasas UR y 0 por ciento para las demás, o la tasa previa al choque si es menor. Cada barra es la distancia de un tramo y un choque a su piso: la tasa más baja posterior al choque menos el piso, en puntos base. El piso es la línea cero; una barra en cero o bajo él es un piso que rige, y su efecto sobre la medida está en la tabla.',
        }}
      >
        <ChartOverTable
          chartMin={`${Math.min(Math.max(f.distances.length, 2), 24) * 1.5 + 3}rem`}
          chart={
            <BarChart
              title={{ en: 'Distance of each leg and shock to its floor', es: 'Distancia de cada tramo y choque a su piso' }}
              height="fill"
              orientation="horizontal"
              data={f.distances.map((x) => ({ id: `${x.leg}-${x.measure}-${x.shock}`, label: distLabel(x), value: x.distance_bp, tone: x.binds ? ('bad' as const) : ('accent' as const) }))}
              axis={{ label: { en: 'Lowest post-shock rate minus the floor (the floor is zero)', es: 'Tasa más baja posterior al choque menos el piso (el piso es cero)' }, unit: { en: 'bp', es: 'pb' }, format: { decimals: 1 } }}
            />
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
          <p data-block="floor-closest" data-binding={nBind}>
            {pick({ en: `Closest to a floor: ${text(LEG_SHORT, lowest.leg).en}, ${text(MEASURE_TEXT, lowest.measure).en}, ${text(SHOCK_TEXT, lowest.shock).en.toLowerCase()}, bucket ${lowest.bucket}, ${formatNumber(lowest.distance_bp, 'en', { digits: 4 })} bp ${lowest.binds ? 'past' : 'above'} the floor. Floors that bind: ${nBind} of ${f.distances.length}.`, es: `Más cerca de un piso: ${text(LEG_SHORT, lowest.leg).es}, ${text(MEASURE_TEXT, lowest.measure).es}, ${text(SHOCK_TEXT, lowest.shock).es.toLowerCase()}, tramo ${lowest.bucket}, ${formatNumber(lowest.distance_bp, 'es', { digits: 4 })} pb ${lowest.binds ? 'bajo' : 'sobre'} el piso. Pisos que rigen: ${nBind} de ${f.distances.length}.` }, lang)}
          </p>
          <table className="caos-table ct-wrap-head" data-table="floor-distances">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Leg', es: 'Tramo' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Measure', es: 'Medida' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Shock', es: 'Choque' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Bucket', es: 'Tramo temporal' }, lang)}</th>
                <th>{pick({ en: 'Lowest rate', es: 'Tasa más baja' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Floor', es: 'Piso' }, lang)}</th>
                <th>{pick({ en: 'Distance (bp)', es: 'Distancia (pb)' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Binds', es: 'Rige' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {f.distances.map((x) => (
                <tr key={`${x.leg}-${x.measure}-${x.shock}`} data-leg={x.leg} data-measure={x.measure} data-shock={x.shock} data-binds={x.binds}>
                  <td className="ct-text">{pick(text(LEG_SHORT, x.leg), lang)}</td>
                  <td className="ct-text">{pick(text(MEASURE_TEXT, x.measure), lang)}</td>
                  <td className="ct-text">{pick(text(SHOCK_TEXT, x.shock), lang)}</td>
                  <td className="ct-wide-only">{x.bucket}</td>
                  <td>{SHARE(x.lowest_rate, lang)}</td>
                  <td className="ct-wide-only">{SHARE(x.floor, lang)}</td>
                  <td>{formatNumber(x.distance_bp, lang, { digits: 4 })}</td>
                  <td className="ct-text">{pick(x.binds ? { en: 'Yes', es: 'Sí' } : { en: 'No', es: 'No' }, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
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
          {f.effects.length === 0 ? (
            <p className="ct-note" data-block="floor-effects-none">{pick({ en: 'The effects table is empty: in this variant no floor changes the measure.', es: 'La tabla de efectos está vacía: en esta variante ningún piso cambia la medida.' }, lang)}</p>
          ) : null}
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
    y: { label: { en: 'Measure over its base', es: 'Medida sobre su base' }, format: { percent: true, decimals: 0 } },
    series: [
      // a breached test is drawn apart from the tests within their threshold, not only named in the table (R4 c18 m6)
      { label: { en: 'Measured, within its threshold', es: 'Medido, dentro de su umbral' }, values: tests.map((t) => (t.breached ? null : t.ratio)), color: '--color-accent', width: 2.4, mode: 'points', size: 12 },
      ...(tests.some((t) => t.breached)
        ? [{ label: { en: 'Measured, above its threshold', es: 'Medido, sobre su umbral' }, values: tests.map((t) => (t.breached ? t.ratio : null)), color: '--color-warn' as const, width: 2.4, mode: 'points' as const, size: 14 }]
        : []),
      // a mark per test, not a line: the three thresholds belong to three different tests and a line would join them (U16-R2 b07 m6)
      { label: { en: 'Threshold of the test', es: 'Umbral de la prueba' }, values: tests.map((t) => t.threshold), color: '--color-bad', width: 2.2, mode: 'points', size: 8 },
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
          en: 'A bank is prioritised when any of three tests is breached: delta NII over 5 percent of Tier 1, delta EVE over 15 percent of Tier 1, or delta NII over 18 percent of the twelve-month net interest and indexation margin. Each red mark is the threshold of its test; a blue point is within its threshold, and an amber point above the red mark of its own test breaches it.',
          es: 'Un banco es priorizado cuando se supera cualquiera de tres pruebas: delta NII sobre el 5 por ciento del capital de nivel 1, delta EVE sobre el 15 por ciento del capital de nivel 1, o delta NII sobre el 18 por ciento del margen neto de intereses y reajustes a doce meses. Cada marca roja es el umbral de su prueba; un punto azul está dentro de su umbral, y un punto ámbar sobre la marca roja de su propia prueba la supera.',
        }}
      >
        <ChartOverTable
          chart={<UPlotChart height="fill" x={chart.x} y={chart.y} series={chart.series} readout={(i) => `${pick(TEST_TEXT[t.tests[i].id].name, lang)}`} />}
        >
          {/* the view's answer first, never at the fold of its box (R4 c18 m15) */}
          <p data-block="verdict" data-prioritised={t.prioritised}>
            <strong>{pick(t.prioritised ? { en: 'The bank is prioritised: at least one test is breached.', es: 'El banco es priorizado: al menos una prueba excede su umbral.' } : { en: 'The bank is not prioritised: no test is breached.', es: 'El banco no es priorizado: ninguna prueba excede su umbral.' }, lang)}</strong>
          </p>
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
            <dt>{pick({ en: 'Reference', es: 'Referencia' }, lang)}</dt>
            <dd>{docText(t.reference, lang)}</dd>
          </dl>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
