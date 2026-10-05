// C05's calibration variants (sp-2010, sp-2011): the S&P rating system of Tasche (2013), its 2009 curve carried to the
// forecast year by every approach of the paper. Replayed numbers are riskvalidation's, from the artifact; the live
// curve and capital are the ports in engine/credit.ts at the rail's approach, forecast PD, regime and LGD.
import { PlotCard, formatNumber, pick, useShellLang, useWorkbenchState, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useMemo } from 'react';
import { irbCapital } from '../../engine/credit';
import type { TestRow } from '../../lib/contract.types';
import { LightCell } from '../ValidationViews';
import { REPLAY, provenanceOf } from '../model';
import { Pending } from '../Pending';
import { APPROACH_COLOR, CASE1, approachShort, averageRiskWeight, isSp, useLiveCurve, type C05Sel, type SpVariant } from './selection';

const LIVE = 'live' as const;
// The x axis counts grades from the best; its title names the letter grades a reader looks for (the shell's marks are
// for what an engine detected, and six of them buried the curves).
const GRADE_AXIS: BiText = { en: 'Grade (1 AAA, 6 A, 9 BBB, 12 BB, 15 B, 17 CCC-C)', es: 'Grado (1 AAA, 6 A, 9 BBB, 12 BB, 15 B, 17 CCC-C)' };

function spOf(sel: C05Sel | null): SpVariant | null {
  const v = sel?.data.variant;
  return v && isSp(v) ? v : null;
}

const pct = (lang: 'en' | 'es', v: number | null | undefined, decimals = 3) => formatNumber(v, lang, { percent: true, decimals });

/** The forecast curves: the year's observed default rates, every case 1 curve, the 2009 curve, the live one. */
export function CurvesView({ sel }: { sel: C05Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = spOf(sel);
  const live = useLiveCurve(sel);
  const chart = useMemo(() => {
    if (!v) return null;
    const o = v.outputs;
    const x = o.grades.map((_, i) => i + 1);
    const series = [
      { label: { en: `Observed ${o.year}`, es: `Observado ${o.year}` }, values: o.default_rate1.map((d) => (d > 0 ? d : null)), color: '--color-fg' as const, mode: 'points' as const },
      { label: { en: '2009 curve (QMM)', es: 'Curva 2009 (QMM)' }, values: o.qmm0.curve, color: '--color-fg-faint' as const, dash: [4, 4], width: 1.2 },
      ...CASE1.map((id) => ({ label: approachShort(v, id), values: o.approaches[id].curve, color: APPROACH_COLOR[id], width: 1.4 })),
    ];
    return { x, series };
  }, [v]);
  if (!sel || !v || !chart || !live) return <Pending />;
  const o = v.outputs;
  const liveSeries = live.curve.length
    ? [{ label: { en: `Live: ${approachShort(v, live.approach).en}`, es: `En vivo: ${approachShort(v, live.approach).es}` }, values: live.curve, color: APPROACH_COLOR[live.approach], width: 3, dash: [7, 3] }]
    : [];
  const prov = provenanceOf(v.provenance.truth_status);
  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col ct-share-3">
        <PlotCard
          fill
          title={{ en: `PD curves for ${o.year}, from the 2009 rating system`, es: `Curvas de PD para ${o.year}, desde el sistema de 2009` }}
          lane={LIVE}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `Log scale. The ${o.year} default rates (dots; ${o.default_rate1.filter((d) => d === 0).length} grades without a default cannot be drawn), the four case 1 approaches at the observed PD, and the live curve at the rail's forecast PD.`,
            es: `Escala logarítmica. Las tasas de ${o.year} (puntos; ${o.default_rate1.filter((d) => d === 0).length} grados sin incumplimientos no se pueden dibujar), los cuatro enfoques del caso 1 a la PD observada, y la curva en vivo a la PD pronosticada del panel.`,
          }}
        >
          <UPlotChart
            height="fill"
            x={{ values: chart.x, label: GRADE_AXIS, format: { decimals: 0 } }}
            y={{ label: { en: 'PD (log scale)', es: 'PD (escala log.)' }, log: true, format: { percent: true, digits: 2 } }}
            series={[...chart.series, ...liveSeries]}
          />
        </PlotCard>
      </div>
      <div className="ct-col ct-share-2">
        <PlotCard
          fill
          title={{ en: 'Grade by grade', es: 'Grado a grado' }}
          lane={LIVE}
          provenance={prov}
          dataKey={stateKey}
          note={{ en: 'The live column follows the rail; the 2009 curve is replayed. The chart beside draws every case 1 approach grade by grade.', es: 'La columna en vivo sigue al panel; la curva 2009 se reproduce. El gráfico al lado dibuja cada enfoque del caso 1 grado a grado.' }}
        >
          <div className="ct-scroll">
            <table className="caos-table" data-table="curves">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Grade', es: 'Grado' }, lang)}</th>
                  <th>{pick({ en: `Observed ${o.year}`, es: `Observado ${o.year}` }, lang)}</th>
                  <th>{pick({ en: 'Live', es: 'En vivo' }, lang)}</th>
                  <th className="ct-wide-only">{pick({ en: '2009 curve', es: 'Curva 2009' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {o.grades.map((g, i) => (
                  <tr key={g}>
                    <td className="ct-text">{g}</td>
                    <td>{pct(lang, o.default_rate1[i], 2)}</td>
                    <td>{live.curve.length ? pct(lang, live.curve[i]) : '-'}</td>
                    <td className="ct-wide-only">{pct(lang, o.qmm0.curve[i])}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
    </div>
  );
}

/** The rating profiles: where the obligors sit in 2009 and in the forecast year (Tasche Table 3). */
export function ProfilesView({ sel }: { sel: C05Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = spOf(sel);
  if (!sel || !v) return <Pending />;
  const o = v.outputs;
  const x = o.grades.map((_, i) => i + 1);
  const prov = provenanceOf(v.provenance.truth_status);
  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col ct-share-3">
        <PlotCard
          fill
          title={{ en: `Rating profiles, 2009 and ${o.year}`, es: `Perfiles de calificación, 2009 y ${o.year}` }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{ en: 'The share of obligors in each grade at the start of each year. A calibration needs to know which of these moves.', es: 'La fracción de deudores en cada grado al inicio de cada año. Una calibración necesita saber cuál de estos se mueve.' }}
        >
          <UPlotChart
            height="fill"
            x={{ values: x, label: GRADE_AXIS, format: { decimals: 0 } }}
            y={{ label: { en: 'Share of obligors', es: 'Fracción de deudores' }, format: { percent: true, decimals: 0 } }}
            series={[
              { label: { en: '2009 profile', es: 'Perfil 2009' }, values: o.profile0, color: '--color-fg-subtle', width: 1.6, dash: [4, 4] },
              { label: { en: `${o.year} profile`, es: `Perfil ${o.year}` }, values: o.profile1, color: '--color-accent', width: 2.2 },
            ]}
          />
        </PlotCard>
      </div>
      <div className="ct-col ct-share-2">
        <PlotCard fill title={{ en: 'The profiles and the PD', es: 'Los perfiles y la PD' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
          <div className="ct-scroll">
            <table className="caos-table" data-table="profiles">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Grade', es: 'Grado' }, lang)}</th>
                  <th>2009</th>
                  <th>{o.year}</th>
                  <th className="ct-wide-only">{pick({ en: 'Change', es: 'Cambio' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {o.grades.map((g, i) => (
                  <tr key={g}>
                    <td className="ct-text">{g}</td>
                    <td>{pct(lang, o.profile0[i], 2)}</td>
                    <td>{pct(lang, o.profile1[i], 2)}</td>
                    <td className="ct-wide-only">{formatNumber((o.profile1[i] - o.profile0[i]) * 100, lang, { decimals: 2 })}</td>
                  </tr>
                ))}
                <tr className="ct-current">
                  <td className="ct-text">{pick({ en: 'Unconditional PD', es: 'PD incondicional' }, lang)}</td>
                  <td>{pct(lang, o.pd0, 3)}</td>
                  <td>{pct(lang, o.pd1, 3)}</td>
                  <td className="ct-wide-only" />
                </tr>
                <tr>
                  <td className="ct-text">{pick({ en: 'Accuracy ratio', es: 'Razón de precisión' }, lang)}</td>
                  <td>{pct(lang, o.ar0, 1)}</td>
                  <td>{pct(lang, o.ar1, 1)}</td>
                  <td className="ct-wide-only" />
                </tr>
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
    </div>
  );
}

function defaultProfileRow(v: SpVariant, id: string): TestRow | undefined {
  return v.tests.find((t) => t.test_id === 'pd.default_profile' && t.model_id === id);
}

/** Every approach of the paper: what it keeps, its forecast PD, its constants, how its curve fits the year. */
export function ApproachesView({ sel }: { sel: C05Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = spOf(sel);
  if (!sel || !v) return <Pending />;
  const o = v.outputs;
  const prov = provenanceOf(v.provenance.truth_status);
  const constant = (id: string): string => {
    const c = o.approaches[id].constants;
    if ('c_pd' in c) return `c_PD ${formatNumber(c.c_pd, lang, { decimals: 4 })}`;
    if ('c_lr' in c) return `c_LR ${formatNumber(c.c_lr, lang, { decimals: 4 })}`;
    if ('accuracy_ratio_target' in c) return `AR1 ${pct(lang, c.accuracy_ratio_target, 1)}`;
    if ('beta' in c) return `alpha ${formatNumber(c.alpha, lang, { decimals: 3 })}, beta ${formatNumber(c.beta, lang, { decimals: 3 })}`;
    return '';
  };
  return (
    <div className="caos-views-row" data-views="1">
      <div className="ct-col">
        <PlotCard
          fill
          title={{ en: `Every calibration approach of Tasche (2013) for ${o.year}`, es: `Cada enfoque de calibración de Tasche (2013) para ${o.year}` }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `Case 1 knows the ${o.year} profile and PD (${pct(lang, o.pd1, 2)}, the observed one, as the paper does); case 2 only the PD; case 3 only the profile, so it forecasts the PD. The default-profile test is the paper's chi-square of the implied default profile, Monte Carlo p-value.`,
            es: `El caso 1 conoce el perfil y la PD de ${o.year} (${pct(lang, o.pd1, 2)}, la observada, como el artículo); el caso 2 solo la PD; el caso 3 solo el perfil, así que pronostica la PD. La prueba del perfil es el chi-cuadrado del perfil de incumplimiento implícito del artículo, con valor p de Monte Carlo.`,
          }}
        >
          <div className="ct-scroll">
            <table className="caos-table" data-table="approaches">
              <thead>
                <tr>
                  <th>{pick({ en: 'Case', es: 'Caso' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Approach', es: 'Enfoque' }, lang)}</th>
                  <th>{pick({ en: 'Forecast PD', es: 'PD pronosticada' }, lang)}</th>
                  <th className="ct-wide-only">{pick({ en: 'Accuracy ratio', es: 'Razón de precisión' }, lang)}</th>
                  <th className="ct-wide-only ct-text">{pick({ en: 'Constants', es: 'Constantes' }, lang)}</th>
                  <th>{pick({ en: 'Default profile, p', es: 'Perfil de incumpl., p' }, lang)}</th>
                  <th className="ct-room-only">{pick({ en: 'Average risk weight', es: 'Ponderador medio' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {v.model.map((m) => (
                  <tr key={m.id} data-approach={m.id} className={m.id === sel.approach ? 'ct-current' : undefined} title={pick(m.title, lang)}>
                    <td>{m.rung.replace('case-', '')}</td>
                    <td className="ct-text">{pick(m.title, lang)}</td>
                    <td>{pct(lang, o.approaches[m.id].pd, 2)}</td>
                    <td className="ct-wide-only">{pct(lang, o.approaches[m.id].accuracy_ratio, 1)}</td>
                    <td className="ct-wide-only ct-text">{constant(m.id)}</td>
                    <LightCell row={defaultProfileRow(v, m.id)} alphas={sel.alphas} />
                    <td className="ct-room-only">{pct(lang, v.impact[`rw_${m.id}`]?.value, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
    </div>
  );
}

/** The paper's test: the chi-square of each approach's implied default profile against the year's defaults. */
export function DefaultProfileView({ sel }: { sel: C05Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = spOf(sel);
  const chart = useMemo(() => {
    if (!v || !sel) return null;
    const o = v.outputs;
    const observed = o.profile1.map((p, i) => (p * o.default_rate1[i]) / o.pd1);
    const cur = o.approaches[sel.approach].curve;
    const s = cur.reduce((a, c, i) => a + c * o.profile1[i], 0);
    const implied = cur.map((c, i) => (c * o.profile1[i]) / s);
    return { x: o.grades.map((_, i) => i + 1), observed, implied };
  }, [v, sel]);
  if (!sel || !v || !chart) return <Pending />;
  const prov = provenanceOf(v.provenance.truth_status);
  const rows = v.model.map((m) => ({ m, row: defaultProfileRow(v, m.id) }));
  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col ct-share-3">
        <PlotCard
          fill
          title={{ en: 'Default-profile test, every approach', es: 'Prueba del perfil de incumplimiento, cada enfoque' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: 'Pearson statistic of the implied default profile against the defaults by grade, given their number; the p-value is a Monte Carlo one (100,000 multinomial samples, seed 2013), the chi-square approximation beside it for reference. The light follows the rail\'s policy.',
            es: 'Estadístico de Pearson del perfil de incumplimiento implícito contra los incumplimientos por grado, dado su número; el valor p es de Monte Carlo (100.000 muestras multinomiales, semilla 2013), con la aproximación chi-cuadrado al lado como referencia. La luz sigue la política del panel.',
          }}
        >
          <div className="ct-scroll">
            <table className="caos-table" data-table="default-profile">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Approach', es: 'Enfoque' }, lang)}</th>
                  <th>T</th>
                  <th>{pick({ en: 'p (Monte Carlo)', es: 'p (Monte Carlo)' }, lang)}</th>
                  <th className="ct-wide-only">{pick({ en: 'Standard error', es: 'Error estándar' }, lang)}</th>
                  <th className="ct-room-only">{pick({ en: 'p (chi-square)', es: 'p (chi-cuadrado)' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(({ m, row }) => (
                  <tr key={m.id} className={m.id === sel.approach ? 'ct-current' : undefined}>
                    <td className="ct-text">{pick(m.short_title, lang)}</td>
                    <td>{formatNumber(row?.statistic, lang, { decimals: 2 })}</td>
                    <LightCell row={row} alphas={sel.alphas} />
                    <td className="ct-wide-only">{formatNumber(row?.extras?.mc_standard_error as number, lang, { digits: 2 })}</td>
                    <td className="ct-room-only">{formatNumber(row?.extras?.p_value_asymptotic as number, lang, { digits: 2 })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
      <div className="ct-col ct-share-2">
        <PlotCard
          fill
          title={{ en: 'Where the defaults fell, and where the curve put them', es: 'Dónde cayeron los incumplimientos y dónde los puso la curva' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{ en: `The default profile of ${v.outputs.year} against the one the rail's approach implies.`, es: `El perfil de incumplimiento de ${v.outputs.year} contra el que implica el enfoque del panel.` }}
        >
          <UPlotChart
            height="fill"
            x={{ values: chart.x, label: GRADE_AXIS, format: { decimals: 0 } }}
            y={{ label: { en: 'Share of the defaults', es: 'Fracción de los incumplimientos' }, format: { percent: true, decimals: 0 } }}
            series={[
              { label: { en: 'Observed', es: 'Observado' }, values: chart.observed, color: '--color-fg', mode: 'points' },
              { label: approachShort(v, sel.approach), values: chart.implied, color: APPROACH_COLOR[sel.approach], width: 2 },
            ]}
          />
        </PlotCard>
      </div>
    </div>
  );
}

/** Jeffreys per grade (the ECB test) for each case 1 curve: where each calibration fails grade by grade. */
export function GradeTestsView({ sel }: { sel: C05Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = spOf(sel);
  if (!sel || !v) return <Pending />;
  const o = v.outputs;
  const row = (id: string, g: string) => v.tests.find((t) => t.test_id === 'pd.jeffreys' && t.model_id === id && t.segment === g);
  return (
    <div className="caos-views-row" data-views="1">
      <div className="ct-col">
        <PlotCard
          fill
          title={{ en: 'Jeffreys test by grade, every case 1 curve', es: 'Prueba de Jeffreys por grado, cada curva del caso 1' }}
          lane={REPLAY}
          provenance={provenanceOf(v.provenance.truth_status)}
          dataKey={stateKey}
          note={{
            en: 'One-sided: a low p-value means more defaults than the curve allows (the PD is underestimated). Grade counts of the derived-only S&P table are not published, only rates and results.',
            es: 'Unilateral: un valor p bajo significa más incumplimientos de los que permite la curva (la PD está subestimada). Los conteos por grado de la tabla S&P, solo derivados, no se publican; solo tasas y resultados.',
          }}
        >
          <div className="ct-scroll">
            <table className="caos-table ct-battery" data-table="jeffreys-by-grade">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Grade', es: 'Grado' }, lang)}</th>
                  <th>{pick({ en: `Observed ${o.year}`, es: `Observado ${o.year}` }, lang)}</th>
                  {CASE1.map((id) => (
                    <th key={id}>{pick(approachShort(v, id), lang)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[...o.grades, 'portfolio'].map((g, i) => (
                  <tr key={g}>
                    <td className="ct-text">{g === 'portfolio' ? pick({ en: 'Portfolio', es: 'Cartera' }, lang) : g}</td>
                    <td>{pct(lang, g === 'portfolio' ? o.pd1 : o.default_rate1[i], 2)}</td>
                    {CASE1.map((id) => (
                      <LightCell key={id} row={row(id, g)} alphas={sel.alphas} />
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
    </div>
  );
}

/** Tasche (2013) Tables 5, 7 and 8 against the recomputation, cell by cell (CT-203). */
export function GoldenSpView({ sel }: { sel: C05Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = spOf(sel);
  if (!sel || !v) return <Pending />;
  const g = v.outputs.golden;
  const t7 = g.table7[sel.approach] ?? g.table7['A4-slr'];
  const prov = provenanceOf(v.provenance.truth_status);
  const f4 = (x: number) => formatNumber(x, lang, { decimals: 4 });
  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col ct-share-3">
        <PlotCard
          fill
          title={{ en: 'The paper\'s tables, recomputed from its counts', es: 'Las tablas del artículo, recalculadas desde sus conteos' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `Table 5 (the 2009 QMM curve, three decimals) and Table 7 (${pick(approachShort(v, sel.approach), lang)}, ${v.outputs.year}, four decimals), in percent. Gaps of one unit come from the paper's own solver, measured on its Table 9.`,
            es: `Tabla 5 (la curva QMM 2009, tres decimales) y Tabla 7 (${pick(approachShort(v, sel.approach), lang)}, ${v.outputs.year}, cuatro decimales), en porcentaje. Las diferencias de una unidad vienen del propio solucionador del artículo, medido en su Tabla 9.`,
          }}
        >
          <div className="ct-scroll">
            <table className="caos-table" data-table="golden-sp">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Grade', es: 'Grado' }, lang)}</th>
                  <th>{pick({ en: 'Table 5', es: 'Tabla 5' }, lang)}</th>
                  <th>{pick({ en: 'Recomputed', es: 'Recalculado' }, lang)}</th>
                  <th>{pick({ en: 'Table 7', es: 'Tabla 7' }, lang)}</th>
                  <th>{pick({ en: 'Recomputed', es: 'Recalculado' }, lang)}</th>
                  <th className="ct-wide-only">{pick({ en: 'Gap', es: 'Diferencia' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {g.table5.map((c, i) => (
                  <tr key={c.grade}>
                    <td className="ct-text">{c.grade}</td>
                    <td>{formatNumber(c.printed, lang, { decimals: 3 })}</td>
                    <td>{formatNumber(c.ours, lang, { decimals: 3 })}</td>
                    <td>{f4(t7[i].printed)}</td>
                    <td>{f4(t7[i].ours)}</td>
                    <td className="ct-wide-only">{f4(t7[i].gap)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
      <div className="ct-col ct-share-2">
        <PlotCard fill title={{ en: 'p-values and the case 3 forecasts', es: 'Valores p y los pronósticos del caso 3' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
          <div className="ct-scroll">
            <table className="caos-table" data-table="golden-p">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Table 7 p-value', es: 'Valor p, Tabla 7' }, lang)}</th>
                  <th>{pick({ en: 'Printed', es: 'Impreso' }, lang)}</th>
                  <th>{pick({ en: 'Here', es: 'Aquí' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {g.table7_p_values.map((r) => (
                  <tr key={r.approach}>
                    <td className="ct-text">{pick(approachShort(v, r.approach), lang)}</td>
                    <td>{formatNumber(r.printed_pct, lang, { decimals: 1 })}%</td>
                    <td>{formatNumber(r.ours_pct, lang, { decimals: 2 })}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <table className="caos-table" data-table="golden-case3">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Table 8 forecast PD', es: 'PD pronosticada, Tabla 8' }, lang)}</th>
                  <th>{pick({ en: 'Printed', es: 'Impreso' }, lang)}</th>
                  <th>{pick({ en: 'Here', es: 'Aquí' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {g.table8.map((r) => (
                  <tr key={r.approach}>
                    <td className="ct-text">{pick(approachShort(v, r.approach), lang)}</td>
                    <td>{formatNumber(r.printed_pct, lang, { decimals: 2 })}%</td>
                    <td>{formatNumber(r.ours_pct, lang, { decimals: 3 })}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
    </div>
  );
}

/** The capital each calibration implies for the forecast portfolio, live at the rail's regime and LGD. */
export function SpImpactView({ sel }: { sel: C05Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = spOf(sel);
  const live = useLiveCurve(sel);
  const data = useMemo(() => {
    if (!v || !sel) return null;
    const o = v.outputs;
    const m = o.irb.maturity;
    const rw = Object.fromEntries(v.model.map((x) => [x.id, averageRiskWeight(o.approaches[x.id].curve, o.profile1, sel.regime, sel.lgd, m)]));
    const byGrade = (curve: number[]) => curve.map((p) => irbCapital('corporate', p, sel.lgd, { maturity: m, regime: sel.regime }).riskWeight);
    return { rw, x: o.grades.map((_, i) => i + 1), stale: byGrade(o.qmm0.curve), cur: live && live.curve.length ? byGrade(live.curve) : null, slr: byGrade(o.approaches['A4-slr'].curve) };
  }, [v, sel, live]);
  if (!sel || !v || !data) return <Pending />;
  const prov = provenanceOf(v.provenance.truth_status);
  const ref = data.rw['A4-slr'];
  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col ct-share-2">
        <PlotCard
          fill
          title={{ en: 'Average risk weight of the forecast portfolio', es: 'Ponderador medio de la cartera pronosticada' }}
          lane={LIVE}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `IRB corporate function, maturity ${formatNumber(v.outputs.irb.maturity, 'en', { decimals: 1 })} years, one unit of EAD per obligor, the PD floored at the regime's floor; regime and LGD from the rail. Relative to the scaled likelihood ratio, the approach the paper's backtest favours.`,
            es: `Función IRB corporativa, vencimiento ${formatNumber(v.outputs.irb.maturity, 'es', { decimals: 1 })} años, una unidad de EAD por deudor, la PD con el piso del régimen; régimen y LGD del panel. Relativo a la razón de verosimilitud escalada, el enfoque que favorece el backtest del artículo.`,
          }}
        >
          <div className="ct-scroll">
            <table className="caos-table" data-table="capital">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Approach', es: 'Enfoque' }, lang)}</th>
                  <th>{pick({ en: 'Risk weight', es: 'Ponderador' }, lang)}</th>
                  <th>{pick({ en: 'Against scaled LR', es: 'Contra RV escalada' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {v.model.map((m) => (
                  <tr key={m.id} className={m.id === sel.approach ? 'ct-current' : undefined}>
                    <td className="ct-text">{pick(m.short_title, lang)}</td>
                    <td>{pct(lang, data.rw[m.id], 1)}</td>
                    <td>{formatNumber((data.rw[m.id] / ref - 1) * 100, lang, { decimals: 1 })}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
      <div className="ct-col ct-share-3">
        <PlotCard
          fill
          title={{ en: 'Risk weight by grade', es: 'Ponderador por grado' }}
          lane={LIVE}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `The live curve, the scaled likelihood ratio and the 2009 curve unchanged, at the rail's regime and LGD. The risk weight peaks at a PD near 30% (maturity 2.5 years) and falls beyond it, where the expected loss the function deducts grows faster: the 2009 curve puts CCC-C at ${pct('en', v.outputs.qmm0.curve[v.outputs.qmm0.curve.length - 1], 1)}.`,
            es: `La curva en vivo, la razón de verosimilitud escalada y la curva 2009 sin cambios, al régimen y la LGD del panel. El ponderador alcanza su máximo con una PD cercana al 30% (vencimiento 2,5 años) y cae más allá, donde la pérdida esperada que la función descuenta crece más rápido: la curva 2009 pone CCC-C en ${pct('es', v.outputs.qmm0.curve[v.outputs.qmm0.curve.length - 1], 1)}.`,
          }}
        >
          <UPlotChart
            height="fill"
            x={{ values: data.x, label: GRADE_AXIS, format: { decimals: 0 } }}
            y={{ label: { en: 'Risk weight (share of EAD)', es: 'Ponderador (fracción de la EAD)' }, format: { percent: true, decimals: 0 } }}
            series={[
              { label: { en: '2009 curve, unchanged', es: 'Curva 2009, sin cambios' }, values: data.stale, color: '--color-fg-faint', dash: [4, 4], width: 1.2 },
              { label: approachShort(v, 'A4-slr'), values: data.slr, color: APPROACH_COLOR['A4-slr'], width: 1.6 },
              ...(data.cur ? [{ label: { en: `Live: ${approachShort(v, sel.approach).en}`, es: `En vivo: ${approachShort(v, sel.approach).es}` }, values: data.cur, color: APPROACH_COLOR[sel.approach], width: 3, dash: [7, 3] }] : []),
            ]}
          />
        </PlotCard>
      </div>
    </div>
  );
}
