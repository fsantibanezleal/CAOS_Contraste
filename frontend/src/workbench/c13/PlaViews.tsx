// C13's PLA group: the P&L attribution test of MAR32.36 to MAR32.44 on a desk whose risk model has one planted
// deficiency. The rank scatter and the two ECDFs draw the example replication the document keeps whole; the zone counts
// and the detection rate are the replications' (the power of the PLA for this deficiency, or its false-alarm rate for the
// control). Every view names the deficiency the generator planted.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable, MaybeNumber } from '../c06/format';
import { rowsMin } from '../c11/MarketCommon';
import { Pending } from '../Pending';
import { useCard } from '../c03/U6Shared';
import { ViewFoot, deficiencyName } from './C13Common';
import { STATISTIC_TEXT, ZONE_TEXT, ecdfGap, seedText, outputsOf, rankSeries, text, type C13Sel } from './selection';

const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });
const pct = (v: number, lang: 'en' | 'es', decimals = 1) => formatNumber(v, lang, { percent: true, decimals });

/** The ranks of the HPL and the RTPL of the example replication: the Spearman statistic is their correlation. */
export function RanksView({ sel }: { sel: C13Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const ex = o.example;
  const t = o.pla.thresholds;
  const { x, y } = rankSeries(ex.hpl, ex.rtpl);
  const name = deficiencyName(o);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `Rank scatter, ${name.en}`, es: `Dispersión de rangos, ${name.es}` }}
        {...card}
        note={{
          en: `One replication kept whole (number ${count(ex.replication_index, 'en')}, seed ${seedText(ex.seed, 'en')}): each point is a day, ranked on the hypothetical and on the risk-theoretical P&L. A model that explains the desk puts the points on the diagonal.`,
          es: `Una replicación guardada completa (número ${count(ex.replication_index, 'es')}, semilla ${seedText(ex.seed, 'es')}): cada punto es un día, ordenado por el P&L hipotético y por el P&L teórico del riesgo. Un modelo que explica la mesa pone los puntos en la diagonal.`,
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: x, label: { en: 'Rank of the hypothetical P&L (HPL)', es: 'Rango del P&L hipotético (HPL)' }, format: { decimals: 0 } }}
              y={{ label: { en: 'Rank of the RTPL', es: 'Rango del RTPL' }, format: { decimals: 0 } }}
              series={[
                { label: { en: 'Days', es: 'Días' }, values: y, mode: 'points', color: '--color-accent', size: 5 },
                { label: { en: 'Same rank', es: 'Mismo rango' }, values: x, color: '--color-fg-faint', width: 1, dash: [4, 3] },
              ]}
            />
          }
        >
          <dl className="ct-defs" data-table="c13-spearman" data-zone={ex.zone}>
            <dt>{pick({ en: 'Spearman of this replication', es: 'Spearman de esta replicación' }, lang)}</dt>
            <dd data-zone={ex.zone}>{formatNumber(ex.spearman, lang, { decimals: 3 })}</dd>
            <dt>{pick({ en: 'Zone of this replication (joint)', es: 'Zona de esta replicación (conjunta)' }, lang)}</dt>
            <dd>{pick(text(ZONE_TEXT, ex.zone), lang)}</dd>
            <dt>{pick({ en: 'Spearman zones', es: 'Zonas de Spearman' }, lang)}</dt>
            <dd>
              {pick(
                {
                  en: `green above ${formatNumber(t.spearman_green, 'en', { decimals: 2 })}, red below ${formatNumber(t.spearman_red, 'en', { decimals: 2 })} (${t.reference})`,
                  es: `verde sobre ${formatNumber(t.spearman_green, 'es', { decimals: 2 })}, rojo bajo ${formatNumber(t.spearman_red, 'es', { decimals: 2 })} (${t.reference})`,
                },
                lang,
              )}
            </dd>
          </dl>
          <ViewFoot o={o} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The two empirical distribution functions of the example replication and the largest gap between them. */
export function EcdfView({ sel }: { sel: C13Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const ex = o.example;
  const t = o.pla.thresholds;
  const g = ecdfGap(ex.hpl, ex.rtpl, t.ecdf_step);
  const name = deficiencyName(o);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `The two ECDFs and the KS gap, ${name.en}`, es: `Las dos ECDF y la brecha KS, ${name.es}` }}
        {...card}
        note={{
          en: `The same replication as the rank scatter. Each ECDF rises by ${formatNumber(t.ecdf_step, 'en', { decimals: 3 })} per observation (${t.reference}); the Kolmogorov-Smirnov statistic is the largest vertical gap between them.`,
          es: `La misma replicación que la dispersión de rangos. Cada ECDF sube ${formatNumber(t.ecdf_step, 'es', { decimals: 3 })} por observación (${t.reference}); el estadístico de Kolmogorov-Smirnov es la mayor brecha vertical entre ellas.`,
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: g.points, label: { en: 'Daily P&L, share of the desk notional', es: 'P&L diario, parte del nocional de la mesa' }, format: { percent: true, decimals: 1 } }}
              y={{ label: { en: 'Share of days at or below', es: 'Parte de los días iguales o menores' }, format: { percent: true, decimals: 0 } }}
              series={[
                { label: { en: 'HPL', es: 'HPL' }, values: g.hpl, color: '--color-accent', width: 2 },
                { label: { en: 'RTPL', es: 'RTPL' }, values: g.rtpl, color: '--color-magenta', width: 2 },
              ]}
              marks={[{ x: g.at, label: { en: `KS gap ${formatNumber(g.gap, 'en', { decimals: 3 })}`, es: `Brecha KS ${formatNumber(g.gap, 'es', { decimals: 3 })}` } }]}
            />
          }
        >
          <dl className="ct-defs" data-table="c13-ks" data-zone={ex.zone}>
            <dt>{pick({ en: 'KS of this replication', es: 'KS de esta replicación' }, lang)}</dt>
            <dd>{formatNumber(ex.ks, lang, { decimals: 3 })}</dd>
            <dt>{pick({ en: 'KS zones', es: 'Zonas de KS' }, lang)}</dt>
            <dd>
              {pick(
                {
                  en: `green below ${formatNumber(t.ks_green, 'en', { decimals: 2 })}, red above ${formatNumber(t.ks_red, 'en', { decimals: 2 })} (${t.reference})`,
                  es: `verde bajo ${formatNumber(t.ks_green, 'es', { decimals: 2 })}, rojo sobre ${formatNumber(t.ks_red, 'es', { decimals: 2 })} (${t.reference})`,
                },
                lang,
              )}
            </dd>
          </dl>
          <ViewFoot o={o} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

const ZONE_TONE = { green: 'good', amber: 'warn', red: 'bad' } as const;

/** The PLA zone counts across the replications: of the joint zone and of each statistic alone, and the two distributions. */
export function ZonesView({ sel }: { sel: C13Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const z = o.pla.zones;
  const name = deficiencyName(o);
  const focus = z[sel.statistic];
  const dist = (label: BiText, d: typeof o.pla.spearman, key: string) => (
    <tr key={key} data-distribution={key}>
      <td className="ct-text">{pick(label, lang)}</td>
      {[d.mean, d.sd, d.q05, d.q50, d.q95, d.min, d.max].map((v, i) => (
        <td key={i} className={i >= 5 ? 'ct-wide-only' : undefined}>{formatNumber(v, lang, { decimals: 3 })}</td>
      ))}
    </tr>
  );
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `PLA zones across the replications, ${name.en}`, es: `Zonas PLA entre las replicaciones, ${name.es}` }}
        {...card}
        note={{
          en: `${count(z.n, 'en')} independent replications of the desk. The bars are the statistic chosen on the rail; the table gives the three.`,
          es: `${count(z.n, 'es')} replicaciones independientes de la mesa. Las barras son el estadístico elegido en el riel; la tabla da los tres.`,
        }}
      >
        <ChartOverTable
          chartMin="12rem"
          chart={
            <BarChart
              title={{ en: `Replications by zone: ${STATISTIC_TEXT[sel.statistic].en}`, es: `Replicaciones por zona: ${STATISTIC_TEXT[sel.statistic].es}` }}
              height="fill"
              orientation="vertical"
              data={(['green', 'amber', 'red'] as const).map((zone) => ({ id: zone, label: text(ZONE_TEXT, zone), value: focus[zone], tone: ZONE_TONE[zone] }))}
              axis={{ label: { en: 'Replications', es: 'Replicaciones' }, format: { decimals: 0 }, range: [0, z.n] }}
            />
          }
        >
          <div data-statistic={sel.statistic}>
            <table className="caos-table ct-wrap-head" data-table="c13-zones">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Statistic', es: 'Estadístico' }, lang)}</th>
                  <th>{pick(ZONE_TEXT.green, lang)}</th>
                  <th>{pick(ZONE_TEXT.amber, lang)}</th>
                  <th>{pick(ZONE_TEXT.red, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {(['overall', 'spearman', 'ks'] as const).map((k) => (
                  <tr key={k} className={k === sel.statistic ? 'ct-current' : undefined}>
                    <td className="ct-text">{pick(STATISTIC_TEXT[k], lang)}</td>
                    {(['green', 'amber', 'red'] as const).map((zone) => (
                      <td key={zone} data-count={`${k}-${zone}-${z[k][zone]}`}>{count(z[k][zone], lang)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <table className="caos-table ct-wrap-head" data-table="c13-distributions">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Across the replications', es: 'Entre las replicaciones' }, lang)}</th>
                  <th>{pick({ en: 'Mean', es: 'Media' }, lang)}</th>
                  <th>{pick({ en: 'SD', es: 'DE' }, lang)}</th>
                  <th>5%</th>
                  <th>{pick({ en: 'Median', es: 'Mediana' }, lang)}</th>
                  <th>95%</th>
                  <th className="ct-wide-only">{pick({ en: 'Min', es: 'Mín' }, lang)}</th>
                  <th className="ct-wide-only">{pick({ en: 'Max', es: 'Máx' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {dist({ en: 'Spearman', es: 'Spearman' }, o.pla.spearman, 'spearman')}
                {dist({ en: 'Kolmogorov-Smirnov', es: 'Kolmogorov-Smirnov' }, o.pla.ks, 'ks')}
              </tbody>
            </table>
          </div>
          <ViewFoot o={o} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** How often the PLA catches the planted deficiency: its power, or for the control its false-alarm rate. */
export function DetectionView({ sel }: { sel: C13Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const d = o.detection;
  const name = deficiencyName(o);
  const power = d.role === 'power';
  const bars = [
    { id: 'amber-red', label: { en: 'Amber or red zone', es: 'Zona ámbar o roja' }, value: d.n_amber_or_red, tone: 'accent' as const },
    { id: 'red', label: { en: 'Red zone', es: 'Zona roja' }, value: d.n_red, tone: 'bad' as const },
    { id: 'spearman', label: { en: 'Spearman flagged', es: 'Marcada por Spearman' }, value: d.by_test.spearman_flagged, tone: 'neutral' as const },
    { id: 'ks', label: { en: 'KS flagged', es: 'Marcada por KS' }, value: d.by_test.ks_flagged, tone: 'neutral' as const },
    { id: 'desk', label: { en: 'Desk back-test flagged', es: 'Marcada por el backtest de mesa' }, value: d.by_test.desk_backtest_flagged, tone: 'neutral' as const },
  ];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `How often the PLA catches it, ${name.en}`, es: `Con qué frecuencia la detecta el PLA, ${name.es}` }}
        {...card}
        note={{
          en: power
            ? `Power: the replications in which the PLA zone is amber or red out of ${count(d.n_replications, 'en')}. The chart counts replications.`
            : `Size: no deficiency is planted, so the replications flagged are the false-alarm rate, out of ${count(d.n_replications, 'en')}. The chart counts replications.`,
          es: power
            ? `Potencia: las replicaciones en que la zona PLA es ámbar o roja de ${count(d.n_replications, 'es')}. El gráfico cuenta replicaciones.`
            : `Tamaño: no se siembra deficiencia, así que las replicaciones marcadas son la tasa de falsas alarmas, de ${count(d.n_replications, 'es')}. El gráfico cuenta replicaciones.`,
        }}
      >
        <ChartOverTable
          chartMin={rowsMin(bars.length)}
          chart={
            <BarChart
              title={{ en: 'Replications flagged', es: 'Replicaciones marcadas' }}
              height="fill"
              orientation="horizontal"
              data={bars}
              axis={{ label: { en: 'Replications', es: 'Replicaciones' }, format: { decimals: 0 }, range: [0, d.n_replications] }}
            />
          }
        >
          <dl className="ct-defs" data-table="c13-detection" data-role={d.role}>
            <dt>{pick({ en: 'What the rate measures', es: 'Qué mide la tasa' }, lang)}</dt>
            <dd>{power ? pick({ en: 'The power of the PLA to catch this deficiency', es: 'La potencia del PLA para detectar esta deficiencia' }, lang) : pick({ en: 'The false-alarm rate of the PLA on an exact model', es: 'La tasa de falsas alarmas del PLA sobre un modelo exacto' }, lang)}</dd>
            <dt>{pick({ en: 'Rule', es: 'Regla' }, lang)}</dt>
            <dd>{pick(d.rule, lang)}</dd>
            <dt>{pick({ en: 'Amber or red', es: 'Ámbar o roja' }, lang)}</dt>
            <dd>{`${pct(d.share_amber_or_red, lang, 2)} (${count(d.n_amber_or_red, lang)} / ${count(d.n_replications, lang)})`}</dd>
            <dt>{pick({ en: 'Interval', es: 'Intervalo' }, lang)}</dt>
            <dd>{`${pct(d.ci_low, lang, 2)} - ${pct(d.ci_high, lang, 2)} (${pick({ en: 'Monte Carlo SE', es: 'error estándar de Monte Carlo' }, lang)} ${pct(d.mc_se, lang, 2)})`}</dd>
            <dt>{pick({ en: 'Red', es: 'Roja' }, lang)}</dt>
            <dd>{`${pct(d.share_red, lang, 2)} (${count(d.n_red, lang)})`}</dd>
            <dt>{pick({ en: 'Flagged by Spearman, KS, desk back-test', es: 'Marcadas por Spearman, KS, backtest de mesa' }, lang)}</dt>
            <dd>{`${count(d.by_test.spearman_flagged, lang)}, ${count(d.by_test.ks_flagged, lang)}, ${count(d.by_test.desk_backtest_flagged, lang)}`}</dd>
            <dt>{pick({ en: 'Flagged by the test meant to catch it', es: 'Marcadas por la prueba que debe detectarla' }, lang)}</dt>
            <dd>
              <MaybeNumber value={d.intended_test_flagged} reason={d.intended_test_flagged === null ? pick({ en: 'no deficiency planted, so no test is meant to catch it', es: 'no se siembra deficiencia, así que ninguna prueba debe detectarla' }, lang) : null} format={(v) => count(v, lang)} />
            </dd>
          </dl>
          <ViewFoot o={o} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
