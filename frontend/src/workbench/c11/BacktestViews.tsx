// C11's Back-tests group: the traditional tests of the model at the level in focus (Kupiec, Christoffersen, duration,
// each with its light, and the eligibility they decide), and the expected shortfall back-test (Acerbi-Szekely Z2) drawn
// against the model's own simulated null distribution. The published reference points of Acerbi and Szekely are drawn
// as a reference only; the critical values that decide are the model's own.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable } from '../c06/format';
import { Pending } from '../Pending';
import { noteText } from '../c08/notes';
import { useCard } from '../c03/U6Shared';
import { ConventionLine, MarketTestsTable, lightWord, rowsMin } from './MarketCommon';
import { alphaLabel, fitOf, levelOf, modelLabel, outputsOf, testName, testsOf, type C11Sel } from './selection';

const TONE = { green: 'good', amber: 'warn', red: 'bad' } as const;

/** The traditional back-tests of the model at the level, with the eligibility they decide and the gates that failed. */
export function TestsView({ sel }: { sel: C11Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const model = o.models.find((m) => m.model_id === sel.model) ?? null;
  const rows = testsOf(sel, o, sel.model, sel.alpha);
  const name = modelLabel(sel, sel.model);
  const failed = model?.failed_gates ?? [];
  const gates = fitOf(sel)?.eligibility_gates ?? [];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `Back-tests of ${name.en}`, es: `Backtests de ${name.es}` }}
        {...card}
        note={{
          en: 'Each p-value is the engine\'s; the bar is empty for a test that did not run. A model is eligible for the comparison when no gate test is red at either level.',
          es: 'Cada valor p es del motor; la barra queda vacía para una prueba que no corrió. Un modelo es elegible para la comparación cuando ninguna prueba de compuerta está en rojo en ningún nivel.',
        }}
      >
        <ChartOverTable
          chartMin={rowsMin(rows.length)}
          chart={
            <BarChart
              title={{ en: 'p-value of each back-test', es: 'Valor p de cada backtest' }}
              height="fill"
              orientation="horizontal"
              data={rows.map((t) => ({
                id: `${t.test_id}-${t.segment}`,
                label: testName(t.test_id),
                value: t.light === 'not_evaluated' || t.light === 'error' ? null : t.p_value,
                tone: t.light === 'not_evaluated' || t.light === 'error' ? ('neutral' as const) : TONE[t.light],
              }))}
              axis={{ label: { en: 'p-value', es: 'Valor p' }, format: { decimals: 2 }, range: [0, 1] }}
            />
          }
        >
          <ConventionLine />
          <p className="ct-note" data-eligible={String(model?.eligible ?? false)}>
            {model
              ? pick(
                  model.eligible
                    ? { en: 'Eligible for the comparison: no gate test is red.', es: 'Elegible para la comparación: ninguna prueba de compuerta está en rojo.' }
                    : {
                        en: `Not eligible: ${failed.map((g) => testName(g).en).join(', ')} red.`,
                        es: `No elegible: ${failed.map((g) => testName(g).es).join(', ')} en rojo.`,
                      },
                  lang,
                )
              : pick({ en: 'This window carries no result for this model.', es: 'Esta ventana no trae resultado para este modelo.' }, lang)}
          </p>
          {gates.length > 0 ? (
            <p className="ct-note">
              {gates.map((g) => `${pick(testName(g.test_id), lang)}: ${pick(g.rule, lang)}`).join(' ')}
            </p>
          ) : null}
          <MarketTestsTable rows={rows} table="c11-tests" />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** Z2 of Acerbi and Szekely against the model's simulated null: the realised statistic, the model's own critical values, and the published points as a reference. */
export function EsBacktestView({ sel }: { sel: C11Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const fit = fitOf(sel);
  const name = modelLabel(sel, sel.model);
  const title: BiText = { en: `Expected shortfall back-test of ${name.en}`, es: `Backtest de la pérdida esperada de ${name.es}` };
  // Z2 is defined at the 2.5 percent tail: at the level in focus when the document has it, else at the level it does have
  const es = o.es_backtests.find((e) => e.model_id === sel.model && e.alpha === sel.alpha) ?? o.es_backtests.find((e) => e.model_id === sel.model) ?? null;
  const esAlpha = es?.alpha ?? sel.alpha;
  if (!es) {
    const row = [0.025, 0.01].map((a) => testsOf(sel, o, sel.model, a).find((t) => t.test_id === 'market.acerbi_szekely')).find(Boolean);
    const level = levelOf(o, sel.model, sel.alpha);
    return (
      <ViewsRow>
        <PlotCard fill title={title} {...card}>
          <ConventionLine />
          <p className="ct-note" data-state="unavailable">
            {row
              ? `${formatNumber(null, lang)} (${row.notes ? noteText(row.notes, lang) : row.reference})`
              : sel.alpha === 0.01
                ? pick({ en: 'The expected shortfall back-test (Z2) is defined at the 2.5 percent tail, the FRTB expected shortfall level; pick the 2.5% tail on the rail.', es: 'El backtest de la pérdida esperada (Z2) se define en la cola de 2,5 por ciento, el nivel de pérdida esperada de FRTB; elija la cola de 2,5% en el riel.' }, lang)
                : level && level.es_status === 'not-forecast'
                  ? pick({ en: 'Not available: this model forecasts no ES, so there is nothing to back-test.', es: 'No disponible: este modelo no pronostica la ES, así que no hay nada que probar.' }, lang)
                  : pick({ en: 'Not available: the document carries no Z2 for this model and level.', es: 'No disponible: el documento no trae Z2 para este modelo y nivel.' }, lang)}
          </p>
        </PlotCard>
      </ViewsRow>
    );
  }
  const h = es.histogram;
  const centers = h.counts.map((_, i) => (h.edges[i] + h.edges[i + 1]) / 2);
  const ref = fit?.es_reference ?? null;
  const fmt = (v: number) => formatNumber(v, lang, { digits: 4 });
  const marks = [
    { x: es.realised, label: { en: `Z2 ${formatNumber(es.realised, 'en', { digits: 3 })}`, es: `Z2 ${formatNumber(es.realised, 'es', { digits: 3 })}` } },
    { x: es.critical_5pct, label: { en: 'Crit. 5%', es: 'Crít. 5 %' } },
    { x: es.critical_0_01pct, label: { en: 'Crit. 0.01%', es: 'Crít. 0,01 %' } },
    ...(ref
      ? [
          { x: ref.yellow, label: { en: `Ref. ${formatNumber(ref.yellow, 'en', { decimals: 2 })}`, es: `Ref. ${formatNumber(ref.yellow, 'es', { decimals: 2 })}` } },
          { x: ref.red, label: { en: `Ref. ${formatNumber(ref.red, 'en', { decimals: 2 })}`, es: `Ref. ${formatNumber(ref.red, 'es', { decimals: 2 })}` } },
        ]
      : []),
  ];
  // the axis takes in every mark: a Z2 far from the null is drawn at its place, with the histogram between
  const lo = Math.min(h.edges[0], ...marks.map((m) => m.x));
  const hi = Math.max(h.edges[h.edges.length - 1], ...marks.map((m) => m.x));
  const pad = (hi - lo) * 0.04;
  const xs = [...(lo < h.edges[0] ? [lo - pad] : []), ...centers, ...(hi > h.edges[h.edges.length - 1] ? [hi + pad] : [])];
  const front = lo < h.edges[0] ? 1 : 0;
  const counts: Array<number | null> = xs.map((_, i) => (i >= front && i < front + centers.length ? h.counts[i - front] : null));
  const test = testsOf(sel, o, sel.model, esAlpha).find((t) => t.test_id === 'market.acerbi_szekely');
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'The model\'s own simulated null distribution of Z2 from its predictive distributions, with the realised statistic. Negative values mean the risk is underestimated.',
          es: 'La distribución nula simulada de Z2 propia del modelo a partir de sus distribuciones predictivas, con el estadístico realizado. Los valores negativos significan que el riesgo está subestimado.',
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: xs, label: { en: 'Z2 statistic', es: 'Estadístico Z2' }, format: { decimals: 2 } }}
              y={{ label: { en: 'Draws per bin', es: 'Simulaciones' }, format: { decimals: 0 } }}
              series={[{ label: { en: 'Null distribution', es: 'Distribución nula' }, values: counts, color: '--color-accent', width: 2 }]}
              marks={marks}
            />
          }
        >
          <ConventionLine />
          <dl className="ct-defs" data-table="z2" data-zone={test?.light}>
            <dt>{pick({ en: 'Tail level', es: 'Nivel de cola' }, lang)}</dt>
            <dd data-level={esAlpha}>{pick(alphaLabel(esAlpha), lang)}</dd>
            <dt>{pick({ en: 'Realised Z2', es: 'Z2 realizado' }, lang)}</dt>
            <dd>{fmt(es.realised)}</dd>
            <dt>{pick({ en: 'Model 5% critical value (yellow)', es: 'Valor crítico del modelo al 5% (amarillo)' }, lang)}</dt>
            <dd>{fmt(es.critical_5pct)}</dd>
            <dt>{pick({ en: 'Model 0.01% critical value (red)', es: 'Valor crítico del modelo al 0,01% (rojo)' }, lang)}</dt>
            <dd>{fmt(es.critical_0_01pct)}</dd>
            <dt>{pick({ en: 'Simulated draws', es: 'Simulaciones' }, lang)}</dt>
            <dd>{formatNumber(es.n_draws, lang, { decimals: 0 })}</dd>
            <dt>{pick({ en: 'Simulated p-value', es: 'Valor p simulado' }, lang)}</dt>
            <dd>{formatNumber(es.p_value, lang, { digits: 3 })}</dd>
            <dt>{pick({ en: 'Light', es: 'Luz' }, lang)}</dt>
            <dd data-zone={test?.light}>{test ? pick(lightWord(test.light), lang) : formatNumber(null, lang)}</dd>
            {ref ? (
              <>
                <dt>{pick({ en: 'Published reference', es: 'Referencia publicada' }, lang)}</dt>
                <dd data-reference="true">
                  {pick(
                    {
                      en: `${formatNumber(ref.yellow, 'en', { decimals: 2 })} (yellow) and ${formatNumber(ref.red, 'en', { decimals: 2 })} (red) for ${ref.n_days} days at ${formatNumber(ref.alpha, 'en', { percent: true, decimals: 1 })}: ${ref.status.en}`,
                      es: `${formatNumber(ref.yellow, 'es', { decimals: 2 })} (amarillo) y ${formatNumber(ref.red, 'es', { decimals: 2 })} (rojo) para ${ref.n_days} días al ${formatNumber(ref.alpha, 'es', { percent: true, decimals: 1 })}: ${ref.status.es}`,
                    },
                    lang,
                  )}
                </dd>
              </>
            ) : null}
          </dl>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
