// C11's beyond-tier view (BS-16): the adaptive conformal recalibration of the VaR of HS-250, GARCH-t and FHS. The first card draws the wrapped
// VaR against the ladder's own (unwrapped) VaR and the realised loss, with the days the wrapped VaR was exceeded marked, and tabulates the
// back-tests and the FZ0 of each wrapped model beside the unwrapped one at the level in focus. The second card states the plan's hypothesis
// with its measured cells and its verdict, whether it holds or not. Everything is what the c11-outputs document carries (`outputs.conformal`);
// a p-value that did not run is "not available", never a zero.
import { PlotCard, ViewsRow, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { UPlotChart, type ChartSeries } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable, MaybeNumber } from '../c06/format';
import { Pending } from '../Pending';
import { useCard } from '../c03/U6Shared';
import { ConventionLine } from './MarketCommon';
import { P_FORMAT } from './ComparisonViews';
import { WINDOW_TEXT, levelOf, modelLabel, outputsOf, seconds, text, type C11Alpha, type C11Outputs, type C11Sel } from './selection';

type Conformal = NonNullable<C11Outputs['conformal']>;
type Row = Conformal['rows'][number];
type Score = Row['wrapped'];

const tail = (alpha: number, lang: 'en' | 'es') => formatNumber(alpha, lang, { percent: true, decimals: alpha === 0.025 ? 1 : 0 });
const p3 = (v: number | null, lang: 'en' | 'es') => (v === null ? formatNumber(null, lang) : formatNumber(v, lang, P_FORMAT));

/** The model whose path is drawn: the one in focus when it is wrapped, otherwise the first wrapped model of the document. */
export function wrappedFocus(conf: Conformal, model: string): string {
  return conf.method.wrapped_models.includes(model) ? model : conf.method.wrapped_models[0];
}

function ScoreRow({ sel, row, side, score, change }: { sel: C11Sel; row: Row; side: 'unwrapped' | 'wrapped'; score: Score; change: number | null }) {
  const lang = useShellLang();
  const name = modelLabel(sel, row.model_id);
  return (
    <tr data-row={`${row.model_id}-${side}`} data-side={side} data-passes={String(score.passes_coverage)}>
      <td className="ct-text">{pick(name, lang)}</td>
      <td className="ct-text">{side === 'wrapped' ? pick({ en: 'Wrapped', es: 'Envuelto' }, lang) : pick({ en: 'Unwrapped', es: 'Sin envolver' }, lang)}</td>
      <td>{formatNumber(score.n_exceedances, lang, { decimals: 0 })}</td>
      <td><MaybeNumber value={score.kupiec_p} reason={null} format={(v) => formatNumber(v, lang, P_FORMAT)} /></td>
      <td><MaybeNumber value={score.conditional_coverage_p} reason={null} format={(v) => formatNumber(v, lang, P_FORMAT)} /></td>
      <td className="ct-wide-only"><MaybeNumber value={score.independence_p} reason={null} format={(v) => formatNumber(v, lang, P_FORMAT)} /></td>
      <td className="ct-wide-only"><MaybeNumber value={score.es_test_p} reason={null} format={(v) => formatNumber(v, lang, P_FORMAT)} /></td>
      <td><MaybeNumber value={score.fz0_mean} reason={null} format={(v) => formatNumber(v, lang, { digits: 4 })} /></td>
      <td className="ct-wide-only">{side === 'wrapped' ? (change === null ? formatNumber(null, lang) : formatNumber(change, lang, { percent: true, decimals: 1 })) : ''}</td>
      <td className="ct-text">{score.passes_coverage ? pick({ en: 'yes', es: 'sí' }, lang) : pick({ en: 'no', es: 'no' }, lang)}</td>
    </tr>
  );
}

/** The wrapped VaR against the unwrapped one, and the back-tests and FZ0 of the three wrapped models beside the unwrapped. */
export function ConformalView({ sel }: { sel: C11Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const conf = o.conformal;
  if (!conf) {
    return (
      <ViewsRow>
        <PlotCard title={{ en: 'Conformal recalibration of the VaR', es: 'Recalibración conforme del VaR' }} {...card}>
          <p className="ct-note" data-state="unavailable">{pick({ en: 'This window carries no conformal recalibration.', es: 'Esta ventana no trae recalibración conforme.' }, lang)}</p>
        </PlotCard>
      </ViewsRow>
    );
  }
  const focus = wrappedFocus(conf, sel.model);
  const row = conf.rows.find((r) => r.model_id === focus && r.alpha === sel.alpha) ?? null;
  const own = levelOf(o, focus, sel.alpha);
  const grid = o.grid;
  const loss = grid.realised_loss.status === 'included' ? grid.realised_loss.loss : null;
  const name = modelLabel(sel, focus);
  const rows = conf.rows.filter((r) => r.alpha === sel.alpha);
  const series: ChartSeries[] = [];
  if (row && own) {
    const hit = new Set(row.series.exceedance_days);
    if (loss) series.push({ label: { en: 'Realised loss', es: 'Pérdida realizada' }, values: loss, color: '--color-fg-faint', width: 1 });
    series.push({ label: { en: 'VaR, unwrapped', es: 'VaR, sin envolver' }, values: own.var, color: '--color-accent', width: 2 });
    series.push({ label: { en: 'VaR, wrapped', es: 'VaR, envuelto' }, values: row.series.var, color: '--color-magenta', width: 2 });
    series.push({
      label: { en: 'Exceedance of the wrapped VaR', es: 'Excedencia del VaR envuelto' },
      values: grid.dates.map((_, i) => (hit.has(i) ? (loss ? loss[i] : row.series.var[i]) : null)),
      color: '--color-bad',
      mode: 'points',
      size: 7,
    });
  }
  const m = conf.method;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `Conformal recalibration at the ${tail(sel.alpha, 'en')} tail: ${name.en}`, es: `Recalibración conforme en la cola de ${tail(sel.alpha, 'es')}: ${name.es}` }}
        {...card}
        note={{
          en: `Beyond the ladder (BS-16). The working tail level starts at the target and moves by ${formatNumber(m.gamma, 'en', { digits: 3 })} times the target minus the hit; the model is asked for its VaR at that level. The step and the band (${formatNumber(m.level_min, 'en', { digits: 3 })} to ${formatNumber(m.level_max, 'en', { digits: 3 })}) were fixed before any run.`,
          es: `Más allá de la escalera (BS-16). El nivel de cola de trabajo parte del objetivo y se mueve en ${formatNumber(m.gamma, 'es', { digits: 3 })} por el objetivo menos la excedencia; al modelo se le pide su VaR en ese nivel. El paso y la banda (${formatNumber(m.level_min, 'es', { digits: 3 })} a ${formatNumber(m.level_max, 'es', { digits: 3 })}) se fijaron antes de cualquier corrida.`,
        }}
      >
        <ChartOverTable
          chart={
            row ? (
              <UPlotChart
                height="fill"
                x={{ values: grid.dates.map(seconds), time: true, label: { en: 'Forecast day', es: 'Día pronosticado' } }}
                y={{ label: { en: 'Loss, share of the portfolio value', es: 'Pérdida, parte del valor de la cartera' }, format: { percent: true, decimals: 2 } }}
                series={series}
              />
            ) : (
              <p className="ct-note" data-state="unavailable">{pick({ en: 'No wrapped run at this level.', es: 'No hay corrida envuelta en este nivel.' }, lang)}</p>
            )
          }
        >
          <div data-level={sel.alpha}>
            <ConventionLine />
            {conf.method.wrapped_models.includes(sel.model) ? null : (
              <p className="ct-note">{pick({ en: `The model in focus is not wrapped; the path of ${name.en} is drawn.`, es: `El modelo en foco no está envuelto; se dibuja la trayectoria de ${name.es}.` }, lang)}</p>
            )}
            {row ? (
              <p className="ct-note" data-block="conformal-path">
                {pick(
                  {
                    en: `The working level stayed between ${formatNumber(row.working_level.min, 'en', { digits: 3 })} and ${formatNumber(row.working_level.max, 'en', { digits: 3 })} (mean ${formatNumber(row.working_level.mean, 'en', { digits: 3 })}) and was cut by the band on ${formatNumber(row.n_clipped, 'en', { decimals: 0 })} days; the wrapped VaR was exceeded on ${formatNumber(row.wrapped.n_exceedances, 'en', { decimals: 0 })} days against ${formatNumber(row.unwrapped.n_exceedances, 'en', { decimals: 0 })} unwrapped and ${formatNumber(row.wrapped.expected_exceedances, 'en', { decimals: 2 })} expected.`,
                    es: `El nivel de trabajo se mantuvo entre ${formatNumber(row.working_level.min, 'es', { digits: 3 })} y ${formatNumber(row.working_level.max, 'es', { digits: 3 })} (media ${formatNumber(row.working_level.mean, 'es', { digits: 3 })}) y la banda lo cortó en ${formatNumber(row.n_clipped, 'es', { decimals: 0 })} días; el VaR envuelto fue superado en ${formatNumber(row.wrapped.n_exceedances, 'es', { decimals: 0 })} días frente a ${formatNumber(row.unwrapped.n_exceedances, 'es', { decimals: 0 })} sin envolver y ${formatNumber(row.wrapped.expected_exceedances, 'es', { decimals: 2 })} esperados.`,
                  },
                  lang,
                )}
              </p>
            ) : null}
            <table className="caos-table ct-wrap-head" data-table="c11-conformal">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Model', es: 'Modelo' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Run', es: 'Corrida' }, lang)}</th>
                  <th>{pick({ en: 'Exceedances', es: 'Excedencias' }, lang)}</th>
                  <th>{pick({ en: 'Kupiec p', es: 'p de Kupiec' }, lang)}</th>
                  <th>{pick({ en: 'Conditional coverage p', es: 'p de cobertura condicional' }, lang)}</th>
                  <th className="ct-wide-only">{pick({ en: 'Independence p', es: 'p de independencia' }, lang)}</th>
                  <th className="ct-wide-only">{pick({ en: 'ES test p', es: 'p de la prueba de ES' }, lang)}</th>
                  <th>{pick({ en: 'Average FZ0', es: 'FZ0 medio' }, lang)}</th>
                  <th className="ct-wide-only">{pick({ en: 'FZ0 change', es: 'Cambio de FZ0' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Passes coverage', es: 'Aprueba cobertura' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {rows.flatMap((r) => [
                  <ScoreRow key={`${r.model_id}-u`} sel={sel} row={r} side="unwrapped" score={r.unwrapped} change={null} />,
                  <ScoreRow key={`${r.model_id}-w`} sel={sel} row={r} side="wrapped" score={r.wrapped} change={r.fz0_change} />,
                ])}
              </tbody>
            </table>
          </div>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The hypothesis of BS-16 with its measured cells over the three stress windows and its verdict. */
export function ConformalVerdictView({ sel }: { sel: C11Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const h = o.conformal?.hypothesis ?? null;
  if (!h) {
    return (
      <ViewsRow>
        <PlotCard title={{ en: 'The hypothesis of BS-16', es: 'La hipótesis de BS-16' }} {...card}>
          <p className="ct-note" data-state="unavailable">{pick({ en: 'This window carries no conformal recalibration.', es: 'Esta ventana no trae recalibración conforme.' }, lang)}</p>
        </PlotCard>
      </ViewsRow>
    );
  }
  const windows = h.run.stress_windows.map((w) => pick(text(WINDOW_TEXT, w), lang)).join(', ');
  return (
    <ViewsRow>
      <PlotCard
        title={{ en: 'The hypothesis of BS-16 and its verdict', es: 'La hipótesis de BS-16 y su veredicto' }}
        {...card}
        note={{ en: 'Written before the first run and reported whatever the result: the cells are measured, not tuned.', es: 'Escrita antes de la primera corrida e informada sea cual sea el resultado: las celdas se miden, no se ajustan.' }}
      >
        <div data-block="conformal-hypothesis" data-holds={String(h.holds)} data-refuted={String(h.refuted)}>
          <p className="ct-note">{pick(h.statement, lang)}</p>
          <p className="ct-note">{pick({ en: 'Refuted if: ', es: 'Se refuta si: ' }, lang) + pick(h.refuted_if, lang)}</p>
          <p className="ct-note">{pick(h.pass_rule, lang)}</p>
          <p className="ct-note" data-block="conformal-verdict"><strong>{pick(h.verdict, lang)}</strong></p>
          <p className="ct-note">
            {pick(
              {
                en: `Run: ${formatNumber(h.run.n_runs, 'en', { decimals: 0 })} model, level and window runs over ${windows} (${formatNumber(h.run.n_stress_days, 'en', { decimals: 0 })} forecast days), step ${formatNumber(h.run.gamma, 'en', { digits: 3 })}, FZ0 tolerance ${formatNumber(h.run.fz0_tolerance, 'en', { percent: true, decimals: 0 })}, one realised path per window.`,
                es: `Corrida: ${formatNumber(h.run.n_runs, 'es', { decimals: 0 })} corridas por modelo, nivel y ventana en ${windows} (${formatNumber(h.run.n_stress_days, 'es', { decimals: 0 })} días pronosticados), paso ${formatNumber(h.run.gamma, 'es', { digits: 3 })}, tolerancia de FZ0 ${formatNumber(h.run.fz0_tolerance, 'es', { percent: true, decimals: 0 })}, una trayectoria realizada por ventana.`,
              },
              lang,
            )}
          </p>
          <table className="caos-table ct-wrap-head" data-table="c11-conformal-cells">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Model', es: 'Modelo' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Tail', es: 'Cola' }, lang)}</th>
                <th>{pick({ en: 'Windows passed, unwrapped', es: 'Ventanas aprobadas, sin envolver' }, lang)}</th>
                <th>{pick({ en: 'Windows passed, wrapped', es: 'Ventanas aprobadas, envuelto' }, lang)}</th>
                <th>{pick({ en: 'Worst FZ0 change', es: 'Peor cambio de FZ0' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Holds', es: 'Se cumple' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {h.cells.map((c) => (
                <tr key={`${c.model_id}-${c.alpha}`} data-cell={`${c.model_id}-${c.alpha}`} data-holds={String(c.holds)}>
                  <td className="ct-text">{pick(modelLabel(sel, c.model_id), lang)}</td>
                  <td className="ct-text">{tail(c.alpha as C11Alpha, lang)}</td>
                  <td>{formatNumber(c.windows_passed_unwrapped, lang, { decimals: 0 })}</td>
                  <td>{formatNumber(c.windows_passed_wrapped, lang, { decimals: 0 })}</td>
                  <td><MaybeNumber value={c.worst_fz0_change} reason={null} format={(v) => formatNumber(v, lang, { percent: true, decimals: 1 })} /></td>
                  <td className="ct-text">{c.holds ? pick({ en: 'yes', es: 'sí' }, lang) : pick({ en: 'no', es: 'no' }, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head" data-table="c11-conformal-independence">
            <caption className="ct-note">{pick({ en: 'Independence of the wrapped hits in equity 2007 to 2009 (the refutation test)', es: 'Independencia de las excedencias envueltas en acciones 2007 a 2009 (la prueba de refutación)' }, lang)}</caption>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Model', es: 'Modelo' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Tail', es: 'Cola' }, lang)}</th>
                <th>{pick({ en: 'Independence p', es: 'p de independencia' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Fails', es: 'Falla' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {h.independence_2007_09.map((x) => (
                <tr key={`${x.model_id}-${x.alpha}`} data-independence={`${x.model_id}-${x.alpha}`} data-fails={String(x.fails)}>
                  <td className="ct-text">{pick(modelLabel(sel, x.model_id), lang)}</td>
                  <td className="ct-text">{tail(x.alpha as C11Alpha, lang)}</td>
                  <td>{p3(x.independence_p, lang)}</td>
                  <td className="ct-text">{x.fails ? pick({ en: 'yes', es: 'sí' }, lang) : pick({ en: 'no', es: 'no' }, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}
