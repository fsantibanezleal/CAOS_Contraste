// C05's low-default variants: the Pluto and Tasche example (published answers) and three generated years (known
// truth). The bounds are riskvalidation's, replayed at the six published levels; the live bounds (any level,
// correlation and scaling) and the capital are the ports in engine/credit.ts.
import { PlotCard, ViewsRow, formatNumber, pick, useShellLang, useWorkbenchState, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useMemo } from 'react';
import { irbCapital, mostPrudent, mostPrudentScaled } from '../../engine/credit';
import type { ModelsArtifact } from '../../lib/contract.types';
import { LightCell } from '../ValidationViews';
import { REPLAY, provenanceOf } from '../model';
import { Pending } from '../Pending';
import { GRADE_COLOR, averageRiskWeight, isLdp, quadrature, useLiveBounds, type C05Sel, type LdpVariant } from './selection';

const LIVE = 'live' as const;
const pct = (lang: 'en' | 'es', v: number | null | undefined, decimals = 3) => formatNumber(v, lang, { percent: true, decimals });

function ldpOf(sel: C05Sel | null): LdpVariant | null {
  const v = sel?.data.variant;
  return v && isLdp(v) ? v : null;
}

const GAMMA_AXIS: BiText = { en: 'Confidence level', es: 'Nivel de confianza' };

/** The pools of the most prudent principle and the bounds at the rail's level, correlation and scaling (live). */
export function BoundsView({ sel }: { sel: C05Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = ldpOf(sel);
  const live = useLiveBounds(sel);
  const chart = useMemo(() => {
    if (!v) return null;
    const o = v.outputs;
    const series = o.grades.flatMap((g, j) => [
      { label: { en: `${g}, independent`, es: `${g}, independiente` }, values: o.bounds.independent.map((b) => b[j]), color: GRADE_COLOR[j], width: 2 },
      { label: { en: `${g}, correlation 12%`, es: `${g}, correlación 12%` }, values: o.bounds.correlated.map((b) => b[j]), color: GRADE_COLOR[j], width: 1.4, dash: [6, 4] },
    ]);
    const flat = (vals: number[]) => o.grades.map((g, j) => ({ label: { en: `${g} expert`, es: `${g} experta` }, values: o.gammas.map(() => vals[j]), color: GRADE_COLOR[j], width: 1, dash: [1, 4] }));
    return { x: o.gammas, series: [...series, ...flat(o.expert_pd)] };
  }, [v]);
  if (!sel || !v || !chart || !live) return <Pending />;
  const o = v.outputs;
  const prov = provenanceOf(v.provenance.truth_status);
  let pn = 0;
  let pd = 0;
  const pools = o.grades
    .map((_, j) => j)
    .reverse()
    .map((j) => {
      pn += o.obligors[j];
      pd += o.defaults[j];
      return { j, n: pn, d: pd };
    })
    .reverse();
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={{ en: 'Most prudent bounds against the confidence level', es: 'Cotas más prudentes según el nivel de confianza' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: `Grades ${o.grades.join(', ')} with ${o.obligors.join(', ')} obligors and ${o.defaults.join(', ')} defaults. Each grade's bound pools it with every worse grade (Pluto and Tasche 2005); log scale.`,
          es: `Grados ${o.grades.join(', ')} con ${o.obligors.join(', ')} deudores y ${o.defaults.join(', ')} incumplimientos. La cota de cada grado lo agrupa con todos los peores (Pluto y Tasche 2005); escala logarítmica.`,
        }}
      >
        <UPlotChart
          height="fill"
          x={{ values: chart.x, label: GAMMA_AXIS, format: { percent: true, decimals: 1 } }}
          y={{ label: { en: 'PD bound (log scale)', es: 'Cota de la PD (escala log.)' }, log: true, format: { percent: true, digits: 2 } }}
          series={chart.series}
          marks={[{ x: sel.gamma, label: { en: 'rail', es: 'panel' } }]}
        />
      </PlotCard>
      <PlotCard
        fill
        title={{ en: 'The pools and the live bounds', es: 'Los grupos y las cotas en vivo' }}
        lane={LIVE}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: `At ${pct(lang, sel.gamma, 1)}, correlation ${pct(lang, sel.rho, 0)}${sel.scaled ? `, scaled to the portfolio bound (K ${formatNumber(live.k, lang, { decimals: 3 })})` : ''}.`,
          es: `Al ${pct(lang, sel.gamma, 1)}, correlación ${pct(lang, sel.rho, 0)}${sel.scaled ? `, escaladas a la cota de la cartera (K ${formatNumber(live.k, lang, { decimals: 3 })})` : ''}.`,
        }}
      >
        <div className="ct-scroll">
          <table className="caos-table" data-table="pools">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Grade', es: 'Grado' }, lang)}</th>
                <th>{pick({ en: 'Pool', es: 'Grupo' }, lang)}</th>
                <th>{pick({ en: 'Live bound', es: 'Cota en vivo' }, lang)}</th>
                <th>{pick({ en: 'Expert PD', es: 'PD experta' }, lang)}</th>
                {o.true_pd && <th>{pick({ en: 'True PD', es: 'PD verdadera' }, lang)}</th>}
                {/* the pool's counts are in its own column and in the chart's note: these two need a wide instrument */}
                <th className="ct-room-only">{pick({ en: 'Obligors', es: 'Deudores' }, lang)}</th>
                <th className="ct-room-only">{pick({ en: 'Defaults', es: 'Incumpl.' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {pools.map((p) => (
                <tr key={o.grades[p.j]}>
                  <td className="ct-text">{o.grades[p.j]}</td>
                  <td>{`${formatNumber(p.d, lang)} / ${formatNumber(p.n, lang)}`}</td>
                  <td>{pct(lang, live.pd[p.j], 3)}</td>
                  <td>{pct(lang, o.expert_pd[p.j], 2)}</td>
                  {o.true_pd && <td>{pct(lang, o.true_pd[p.j], 2)}</td>}
                  <td className="ct-room-only">{formatNumber(o.obligors[p.j], lang)}</td>
                  <td className="ct-room-only">{formatNumber(o.defaults[p.j], lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

/** Section 5: the bounds scaled by one factor K to the portfolio's upper bound, at the six levels. */
export function ScalingView({ sel }: { sel: C05Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = ldpOf(sel);
  if (!sel || !v) return <Pending />;
  const o = v.outputs;
  const prov = provenanceOf(v.provenance.truth_status);
  const rows = o.gammas.map((g, i) => ({ g, raw: o.bounds.independent[i], s: o.bounds.scaled_upper_bound[i], sc: o.bounds.scaled_upper_bound_correlated[i] }));
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Scaled to the portfolio bound (Pluto and Tasche, section 5)', es: 'Escaladas a la cota de la cartera (Pluto y Tasche, sección 5)' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: 'One factor K for every grade makes the obligor-weighted mean of the bounds equal the most prudent bound of the whole portfolio (the best grade\'s): ordering and ratios kept, the reading as confidence bounds given up. The paper proposes it at a moderate level.',
          es: 'Un factor K común a todos los grados iguala la media ponderada de las cotas a la cota más prudente de toda la cartera (la del mejor grado): se conservan el orden y las razones y se abandona su lectura como cotas de confianza. El artículo lo propone a un nivel moderado.',
        }}
      >
        <div className="ct-scroll">
          <table className="caos-table" data-table="scaling">
            <thead>
              <tr>
                <th>{pick(GAMMA_AXIS, lang)}</th>
                <th>K</th>
                {o.grades.map((g) => (
                  <th key={g}>{pick({ en: `${g} scaled`, es: `${g} escalada` }, lang)}</th>
                ))}
                {o.grades.map((g) => (
                  <th key={`raw-${g}`} className="ct-wide-only">{pick({ en: `${g} unscaled`, es: `${g} sin escalar` }, lang)}</th>
                ))}
                <th className="ct-room-only">{pick({ en: 'K, correlation 12%', es: 'K, correlación 12%' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.g} className={Math.abs(r.g - sel.gamma) < 1e-9 ? 'ct-current' : undefined}>
                  <td>{pct(lang, r.g, 1)}</td>
                  <td>{formatNumber(r.s.k, lang, { decimals: 3 })}</td>
                  {r.s.pd.map((p, j) => (
                    <td key={j}>{pct(lang, p, 3)}</td>
                  ))}
                  {r.raw.map((p, j) => (
                    <td key={`raw-${j}`} className="ct-wide-only">{pct(lang, p, 3)}</td>
                  ))}
                  <td className="ct-room-only">{formatNumber(r.sc.k, lang, { decimals: 3 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

/** The battery on the expert model: Jeffreys per grade and for the portfolio, the binomial and the Vasicek binomial. */
export function LdpTestsView({ sel }: { sel: C05Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = ldpOf(sel);
  if (!sel || !v) return <Pending />;
  const prov = provenanceOf(v.provenance.truth_status);
  const NAME: Record<string, BiText> = {
    'pd.jeffreys': { en: 'Jeffreys', es: 'Jeffreys' },
    'pd.binomial': { en: 'Binomial', es: 'Binomial' },
    'pd.binomial_vasicek': { en: 'Vasicek binomial (12%)', es: 'Binomial de Vasicek (12%)' },
  };
  const kt = v.outputs.known_truth;
  return (
    <ViewsRow shares={kt ? [3, 2] : undefined}>
      <PlotCard
        fill
        title={{ en: 'The battery on the expert PDs', es: 'La batería sobre las PD expertas' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: `Expert PDs ${v.outputs.expert_pd.map((p) => pct(lang, p, 2)).join(', ')} for grades ${v.outputs.grades.join(', ')}, against this year's defaults. One-sided: a low p-value means more defaults than the PD allows. The lights follow the rail's policy.`,
          es: `PD expertas ${v.outputs.expert_pd.map((p) => pct(lang, p, 2)).join(', ')} para los grados ${v.outputs.grades.join(', ')}, contra los incumplimientos de este año. Unilateral: un valor p bajo significa más incumplimientos de los que la PD permite. Las luces siguen la política del panel.`,
        }}
      >
        <div className="ct-scroll">
          <table className="caos-table" data-table="ldp-tests">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Test', es: 'Prueba' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Segment', es: 'Segmento' }, lang)}</th>
                <th>{pick({ en: 'Defaults', es: 'Incumpl.' }, lang)}</th>
                <th>{pick({ en: 'p and light', es: 'p y luz' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {v.tests.map((t) => (
                <tr key={`${t.test_id}-${t.segment}`}>
                  <td className="ct-text">{pick(NAME[t.test_id] ?? { en: t.test_id, es: t.test_id }, lang)}</td>
                  <td className="ct-text">{t.segment === 'portfolio' ? pick({ en: 'portfolio', es: 'cartera' }, lang) : t.segment}</td>
                  <td>{t.n_events !== null && t.n !== null ? `${formatNumber(t.n_events, lang)} / ${formatNumber(t.n, lang)}` : '-'}</td>
                  <LightCell row={t} alphas={sel.alphas} />
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
      {kt && (
        <PlotCard
          fill
          title={{ en: 'Size and power over 20,000 generated years', es: 'Tamaño y potencia en 20.000 años generados' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: 'Share of years each test rejects at 5%: against the true PDs (its size, 5% if it is right) and against the expert PDs, half the truth (its power).',
            es: 'Fracción de años en que cada prueba rechaza al 5%: contra las PD verdaderas (su tamaño, 5% si es correcta) y contra las PD expertas, la mitad de la verdad (su potencia).',
          }}
        >
          <div className="ct-scroll">
            <table className="caos-table" data-table="size-power">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Test', es: 'Prueba' }, lang)}</th>
                  <th>{pick({ en: 'Size', es: 'Tamaño' }, lang)}</th>
                  <th>{pick({ en: 'Power', es: 'Potencia' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(kt.tests.true).map((k) => (
                  <tr key={k}>
                    <td className="ct-text">{k.replace('_', ', ')}</td>
                    <td>{pct(lang, kt.tests.true[k].reject_5, 1)}</td>
                    <td>{pct(lang, kt.tests.expert[k].reject_5, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
      )}
    </ViewsRow>
  );
}

/** A row of the Pluto-Tasche reproduction by name, with its unit: a grade's bound (percent), scaled or not, or K. */
function goldenRow(row: string): BiText {
  if (row === 'k') return { en: 'K (a factor)', es: 'K (un factor)' };
  const m = /^p([abc])(,scaled)?$/.exec(row);
  if (!m) return { en: row, es: row };
  const g = m[1].toUpperCase();
  return m[2] ? { en: `Grade ${g}, scaled (%)`, es: `Grado ${g}, escalada (%)` } : { en: `Grade ${g} (%)`, es: `Grado ${g} (%)` };
}

/** Known truth (generated years) or the published answers (the example): what the bounds are worth. */
export function KnownTruthView({ sel }: { sel: C05Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = ldpOf(sel);
  if (!sel || !v) return <Pending />;
  const o = v.outputs;
  const prov = provenanceOf(v.provenance.truth_status);
  if (o.golden) {
    const cells = o.golden.cells;
    return (
      <ViewsRow>
        <PlotCard
          fill
          title={{ en: 'Pluto and Tasche, Tables 1 to 14, recomputed', es: 'Pluto y Tasche, tablas 1 a 14, recalculadas' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: `${cells.filter((c) => c.gap === 0).length} of ${cells.length} cells identical at the printed precision; the others, cell by cell: ${Object.values(o.golden.notes).join('; ')}.`,
            es: `${cells.filter((c) => c.gap === 0).length} de ${cells.length} celdas idénticas a la precisión impresa; las demás, celda por celda: ${Object.values(o.golden.notes).join('; ')}.`,
          }}
        >
          <div className="ct-scroll">
            <table className="caos-table" data-table="golden-ldp">
              <thead>
                <tr>
                  <th>{pick({ en: 'Table', es: 'Tabla' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Row', es: 'Fila' }, lang)}</th>
                  <th>{pick(GAMMA_AXIS, lang)}</th>
                  <th>{pick({ en: 'Printed', es: 'Impreso' }, lang)}</th>
                  <th>{pick({ en: 'Recomputed', es: 'Recalculado' }, lang)}</th>
                  <th>{pick({ en: 'Gap', es: 'Diferencia' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {cells.map((c) => (
                  <tr key={`${c.table}-${c.row}-${c.gamma}`} className={c.gap !== 0 ? 'ct-current' : undefined}>
                    <td>{c.table}</td>
                    <td className="ct-text">{pick(goldenRow(c.row), lang)}</td>
                    <td>{pct(lang, c.gamma, 1)}</td>
                    <td>{formatNumber(c.printed, lang, { decimals: 2 })}</td>
                    <td>{formatNumber(c.ours, lang, { decimals: 4 })}</td>
                    <td>{formatNumber(c.gap, lang, { decimals: 2 })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </ViewsRow>
    );
  }
  const kt = o.known_truth;
  if (!kt) return <Pending />;
  const methods: Array<{ id: string; label: BiText }> = [
    { id: 'independent', label: { en: 'Independent', es: 'Independiente' } },
    { id: 'correlated', label: { en: 'Correlation 12%', es: 'Correlación 12%' } },
    { id: 'scaled', label: { en: 'Scaled', es: 'Escalada' } },
    { id: 'scaled_correlated', label: { en: 'Scaled, 12%', es: 'Escalada, 12%' } },
  ];
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={{ en: `Coverage of the bounds over ${formatNumber(kt.years, lang)} generated years`, es: `Cobertura de las cotas en ${formatNumber(kt.years, lang)} años generados` }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: 'Share of years in which each bound is at least the true PD, and its median at 75% as a multiple of the truth (true PDs 0.05%, 0.10%, 0.20%; correlation 12%). From 75% up a one-year bound covers the truth in every year; at 50% a year without defaults puts grade B\'s just under it, and scaling lowers the bounds further.',
          es: 'Fracción de años en que cada cota es al menos la PD verdadera, y su mediana al 75% como múltiplo de la verdad (PD verdaderas 0,05%, 0,10%, 0,20%; correlación 12%). Desde el 75% una cota de un año cubre la verdad todos los años; al 50% un año sin incumplimientos deja la del grado B justo bajo ella, y el escalado baja más las cotas.',
        }}
      >
        <div className="ct-scroll">
          <table className="caos-table" data-table="coverage">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Bound', es: 'Cota' }, lang)}</th>
                <th>{pick({ en: 'Grade', es: 'Grado' }, lang)}</th>
                {/* 95% lies between 90% and 99% and adds the least: a narrower instrument keeps the median ratio instead */}
                {kt.coverage.independent.A.map((r) => (
                  <th key={r.gamma} className={r.gamma === 0.95 ? 'ct-room-only' : undefined}>{pct(lang, r.gamma, 0)}</th>
                ))}
                <th className="ct-wide-only">{pick({ en: 'Median / truth', es: 'Mediana / verdad' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {methods.flatMap((m) =>
                o.grades.map((g) => (
                  <tr key={`${m.id}-${g}`}>
                    <td className="ct-text">{pick(m.label, lang)}</td>
                    <td>{g}</td>
                    {kt.coverage[m.id][g].map((r) => (
                      <td key={r.gamma} className={r.gamma === 0.95 ? 'ct-room-only' : undefined} title={`SE ${formatNumber(r.se, lang, { digits: 2 })}`}>{pct(lang, r.coverage, 1)}</td>
                    ))}
                    <td className="ct-wide-only">{formatNumber(kt.coverage[m.id][g].find((r) => r.gamma === 0.75)?.ratio_median, lang, { decimals: 2 })}</td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </div>
      </PlotCard>
      <PlotCard
        fill
        title={{ en: 'Defaults per generated year', es: 'Incumplimientos por año generado' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: `Variance ${formatNumber(kt.overdispersion.variance_simulated, lang, { decimals: 2 })} against ${formatNumber(kt.overdispersion.variance_independent, lang, { decimals: 2 })} if defaults were independent; the moment estimate of the correlation is ${pct(lang, kt.overdispersion.rho_moment_estimate, 1)}. This year: ${o.defaults.reduce((a, b) => a + b, 0)}.`,
          es: `Varianza ${formatNumber(kt.overdispersion.variance_simulated, lang, { decimals: 2 })} contra ${formatNumber(kt.overdispersion.variance_independent, lang, { decimals: 2 })} si los incumplimientos fueran independientes; la estimación de momentos de la correlación es ${pct(lang, kt.overdispersion.rho_moment_estimate, 1)}. Este año: ${o.defaults.reduce((a, b) => a + b, 0)}.`,
        }}
      >
        <UPlotChart
          height="fill"
          x={{ values: kt.total_defaults_histogram.map((_, i) => i), label: { en: 'Defaults in the year', es: 'Incumplimientos en el año' }, format: { decimals: 0 } }}
          y={{ label: { en: 'Share of the years', es: 'Fracción de los años' }, format: { percent: true, decimals: 0 } }}
          series={[{ label: { en: 'Generated years', es: 'Años generados' }, values: kt.total_defaults_histogram.map((n) => n / kt.years), color: '--color-accent', width: 2 }]}
          marks={[{ x: o.defaults.reduce((a, b) => a + b, 0), label: { en: 'this year', es: 'este año' } }]}
        />
      </PlotCard>
    </ViewsRow>
  );
}

/** The levels of the capital chart: 50% to 99.5% by half a point, the rail's range. */
const LEVELS = Array.from({ length: 100 }, (_, i) => Math.round((0.5 + 0.005 * i) * 1000) / 1000);

/**
 * The capital of the portfolio under each estimate at the rail's level (the expert PDs, the three kinds of bound and,
 * for a generated year, the truth), and what the level itself costs: the average risk weight of each kind of bound
 * from 50% to 99.5%, against the expert PDs and the truth. The bounds along the level depend only on the variant and
 * the correlation, so they are computed apart from the regime and the LGD, which only re-weight them.
 */
export function LdpImpactView({ sel }: { sel: C05Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = ldpOf(sel);
  const quad = sel ? quadrature(sel.data.models as ModelsArtifact<unknown>) : null;
  const rho = sel?.rho ?? 0;
  const grid = useMemo(() => {
    if (!v || !quad) return null;
    const o = v.outputs;
    return {
      independent: LEVELS.map((g) => mostPrudent(o.obligors, o.defaults, g, 0, quad)),
      correlated: LEVELS.map((g) => mostPrudent(o.obligors, o.defaults, g, rho, quad)),
      scaled: LEVELS.map((g) => mostPrudentScaled(o.obligors, o.defaults, g, rho, quad).pd),
    };
  }, [v, quad, rho]);
  const data = useMemo(() => {
    if (!v || !sel || !quad || !grid) return null;
    const o = v.outputs;
    const m = o.irb.maturity;
    const avg = (pds: number[]) => averageRiskWeight(pds, o.obligors, sel.regime, sel.lgd, m);
    // a non-breaking space before the sign, so a wrapped label never strands "%" (known shell defect 22)
    const rhoText = { en: pct('en', sel.rho, 0), es: pct('es', sel.rho, 0) };
    const rows: Array<{ id: string; label: BiText; pds: number[] }> = [
      { id: 'expert', label: { en: 'Expert PDs', es: 'PD expertas' }, pds: o.expert_pd },
      ...(o.true_pd ? [{ id: 'truth', label: { en: 'True PDs', es: 'PD verdaderas' }, pds: o.true_pd }] : []),
      { id: 'independent', label: { en: 'Independent bounds', es: 'Cotas independientes' }, pds: mostPrudent(o.obligors, o.defaults, sel.gamma, 0, quad) },
      { id: 'correlated', label: { en: `Bounds, correlation ${rhoText.en}`, es: `Cotas, correlación ${rhoText.es}` }, pds: mostPrudent(o.obligors, o.defaults, sel.gamma, sel.rho, quad) },
      { id: 'scaled', label: { en: `Scaled, correlation ${rhoText.en}`, es: `Escaladas, correlación ${rhoText.es}` }, pds: mostPrudentScaled(o.obligors, o.defaults, sel.gamma, sel.rho, quad).pd },
    ];
    const flat = (pds: number[]) => LEVELS.map(() => avg(pds));
    return {
      rows: rows.map((r) => ({ ...r, avg: avg(r.pds), rw: r.pds.map((p) => irbCapital('corporate', p, sel.lgd, { maturity: m, regime: sel.regime }).riskWeight) })),
      series: [
        { label: { en: 'Independent', es: 'Independientes' }, values: grid.independent.map(avg), color: '--color-accent' as const, width: 2 },
        { label: { en: `Correlation ${rhoText.en}`, es: `Correlación ${rhoText.es}` }, values: grid.correlated.map(avg), color: '--color-accent-2' as const, width: 2, dash: [6, 4] },
        { label: { en: 'Scaled', es: 'Escaladas' }, values: grid.scaled.map(avg), color: '--color-warn' as const, width: 1.6 },
        { label: { en: 'Expert PDs', es: 'PD expertas' }, values: flat(o.expert_pd), color: '--color-fg-subtle' as const, width: 1.2, dash: [2, 4] },
        ...(o.true_pd ? [{ label: { en: 'True PDs', es: 'PD verdaderas' }, values: flat(o.true_pd), color: '--color-fg' as const, width: 1.2, dash: [8, 4] }] : []),
      ],
    };
  }, [v, sel, quad, grid]);
  if (!sel || !v || !data) return <Pending />;
  const o = v.outputs;
  const prov = provenanceOf(v.provenance.truth_status);
  const current = sel.scaled ? 'scaled' : 'correlated';
  return (
    <ViewsRow shares={[2, 3]}>
      <PlotCard
        fill
        title={{ en: `IRB capital at the rail's level, ${pct('en', sel.gamma, 1)}`, es: `Capital IRB al nivel del panel, ${pct('es', sel.gamma, 1)}` }}
        lane={LIVE}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: `Corporate function, maturity ${formatNumber(o.irb.maturity, 'en', { decimals: 1 })} years, regime and LGD from the rail, one unit of EAD per obligor; the highlighted row is the rail's estimate, whose PDs the bounds view shows. The PD floor (0.05% in Basel III and CRR3, 0.03% in Basel II) lifts the expert PDs of the best grades: what the floor does and does not cure.`,
          es: `Función corporativa, vencimiento ${formatNumber(o.irb.maturity, 'es', { decimals: 1 })} años, régimen y LGD del panel, una unidad de EAD por deudor; la fila destacada es la estimación del panel, cuyas PD muestra la vista de cotas. El piso de PD (0,05% en Basilea III y CRR3, 0,03% en Basilea II) eleva las PD expertas de los mejores grados: lo que el piso corrige y lo que no.`,
        }}
      >
        <div className="ct-scroll">
          <table className="caos-table" data-table="ldp-capital">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Estimate', es: 'Estimación' }, lang)}</th>
                <th>{pick({ en: 'Average risk weight', es: 'Ponderador medio' }, lang)}</th>
                {/* each grade's risk weight needs a wide instrument (the bounds view shows the PDs themselves) */}
                <th className="ct-room-only">{pick({ en: `Risk weight (${o.grades.join(', ')})`, es: `Ponderador (${o.grades.join(', ')})` }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {data.rows.map((r) => (
                <tr key={r.id} className={r.id === current ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(r.label, lang)}</td>
                  <td>{pct(lang, r.avg, 1)}</td>
                  <td className="ct-room-only">{r.rw.map((w) => pct(lang, w, 1)).join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
      <PlotCard
        fill
        title={{ en: 'What the confidence level costs', es: 'Lo que cuesta el nivel de confianza' }}
        lane={LIVE}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: `The portfolio's average risk weight under each kind of bound, from 50% to 99.5%, at the rail's correlation, regime and LGD; flat lines for the expert PDs${o.true_pd ? ' and the truth' : ''}. The paper argues for a moderate level: the bound is a conservative PD, and its price grows fastest near the top.`,
          es: `El ponderador medio de la cartera con cada tipo de cota, de 50% a 99,5%, a la correlación, el régimen y la LGD del panel; líneas planas para las PD expertas${o.true_pd ? ' y la verdad' : ''}. El artículo aboga por un nivel moderado: la cota es una PD conservadora y su precio crece más rápido cerca del máximo.`,
        }}
      >
        <UPlotChart
          height="fill"
          x={{ values: LEVELS, label: GAMMA_AXIS, format: { percent: true, decimals: 1 } }}
          y={{ label: { en: 'Average risk weight (share of EAD)', es: 'Ponderador medio (fracción de la EAD)' }, format: { percent: true, decimals: 0 } }}
          series={data.series}
          marks={[{ x: sel.gamma, label: { en: 'rail', es: 'panel' } }]}
        />
      </PlotCard>
    </ViewsRow>
  );
}
