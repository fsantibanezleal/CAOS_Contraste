// C11's Findings, Variants (the windows) and Context groups, and the live read-outs of its rail (ADR-0017 rule 3: every
// section shows a value that moves with its controls). The Findings card and the fixture notice are the ones C06 to C09 use.
import { Fragment } from 'react';
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { loadAllVariants, useArtifact } from '../../api/artifacts';
import type { VariantArtifact } from '../../lib/contract.types';
import { FindingsCard, FixtureNotice } from '../c06/C06Common';
import { ChartOverTable } from '../c06/format';
import { Pending } from '../Pending';
import { LiveReadout, useCard, type Bi } from '../c03/U6Shared';
import { ConventionLine, rowsMin, zoneText } from './MarketCommon';
import {
  CLASS_TEXT, SOURCE_CLASS_TEXT, WINDOW_TEXT, alphaLabel, championOf, fitOf, levelOf, modelLabel, outputsOf, rungOf, spanLine, testName, testsOf, text,
  type C11Outputs, type C11Sel,
} from './selection';

const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });
const NONE = (lang: 'en' | 'es') => formatNumber(null, lang);
const na = (): BiText => ({ en: NONE('en'), es: NONE('es') });

export function C11FindingsView({ sel }: { sel: C11Sel | null }) {
  if (!sel) return <Pending />;
  return (
    <ViewsRow>
      <FindingsCard variant={sel.data.variant} />
    </ViewsRow>
  );
}

/** The windows side by side: the champion's exceedances against the expected count and its zone. Pick one to load it. */
export function C11VariantsTable({ variants, onPick, current }: { variants: Array<{ id: string; title: Bi; v: VariantArtifact<C11Outputs> }>; onPick: (id: string) => void; current: string }) {
  const lang = useShellLang();
  const card = useCard(variants[0]?.v as unknown as VariantArtifact | undefined);
  const alpha = 0.01;
  const rows = variants.map(({ id, title, v }) => {
    const champ = championOf(v.outputs, alpha);
    const lv = champ ? levelOf(v.outputs, champ, alpha) : null;
    const label = champ ? (v.model.find((m) => m.id === champ)?.title ?? na()) : null;
    return { id, title, v, champ, lv, label };
  });
  const bars = rows.flatMap((r) => [
    { id: `${r.id}-observed`, label: { en: `${r.title.en}, observed`, es: `${r.title.es}, observadas` }, value: r.lv?.n_exceedances ?? null, tone: 'accent' as const, highlight: r.id === current },
    { id: `${r.id}-expected`, label: { en: `${r.title.en}, expected`, es: `${r.title.es}, esperadas` }, value: r.lv?.expected_exceedances ?? null, tone: 'neutral' as const },
  ]);
  return (
    <PlotCard
      fill
      title={{ en: 'The test windows', es: 'Las ventanas de prueba' }}
      {...card}
      note={{
        en: 'Each window is a stress or calm period of public daily series, forecast one day ahead with data strictly before the day. The bars are the exceedances of the champion at the 1% tail against the count expected; windows differ in length. Pick one to load it.',
        es: 'Cada ventana es un período de tensión o calma de series públicas diarias, pronosticado un día adelante con datos estrictamente anteriores al día. Las barras son las excedencias del campeón en la cola de 1% frente a las esperadas; las ventanas difieren en largo. Elija una para cargarla.',
      }}
    >
      <ChartOverTable
        chartMin={rowsMin(bars.length)}
        chart={
          <BarChart
            title={{ en: 'Exceedances of the champion at the 1% tail', es: 'Excedencias del campeón en la cola de 1%' }}
            height="fill"
            orientation="horizontal"
            data={bars}
            axis={{ label: { en: 'Days', es: 'Días' }, format: { decimals: 0 } }}
          />
        }
      >
        <ConventionLine />
        <table className="caos-table ct-wrap-head" data-table="variants-c11">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Window', es: 'Ventana' }, lang)}</th>
              <th className="ct-wide-only ct-text">{pick({ en: 'Class', es: 'Clase' }, lang)}</th>
              <th>{pick({ en: 'Forecast days', es: 'Días pronosticados' }, lang)}</th>
              <th className="ct-text">{pick({ en: 'Champion', es: 'Campeón' }, lang)}</th>
              <th>{pick({ en: 'Exceedances', es: 'Excedencias' }, lang)}</th>
              <th>{pick({ en: 'Expected', es: 'Esperadas' }, lang)}</th>
              <th className="ct-text">{pick({ en: 'Zone', es: 'Zona' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ id, title, v, champ, lv, label }) => {
              const zone = lv?.traffic_light?.final_zone ?? null;
              return (
                <tr key={id} data-variant={id} className={id === current ? 'ct-current' : undefined}>
                  <td className="ct-text">
                    <button type="button" className="ct-linkbutton" onClick={() => onPick(id)}>{pick(title, lang)}</button>
                  </td>
                  <td className="ct-wide-only ct-text">{pick(text(CLASS_TEXT, v.outputs.window.asset_class), lang)}</td>
                  <td>{count(v.outputs.window.n_forecast_days, lang)}</td>
                  <td className="ct-text">{champ && label ? pick(label, lang) : NONE(lang)}</td>
                  <td data-na={lv ? undefined : 'true'}>{lv ? count(lv.n_exceedances, lang) : NONE(lang)}</td>
                  <td data-na={lv ? undefined : 'true'}>{lv ? formatNumber(lv.expected_exceedances, lang, { decimals: 2 }) : NONE(lang)}</td>
                  <td className="ct-text" data-zone={zone ?? undefined}>{zone ? pick(zoneText(zone), lang) : NONE(lang)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </ChartOverTable>
    </PlotCard>
  );
}

export function C11VariantsView({ sel, onPick }: { sel: C11Sel | null; onPick: (id: string) => void }) {
  const manifest = sel?.data.manifest;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  if (!sel || all.state !== 'ready') return <Pending />;
  const entries = sel.data.manifest.artifacts.filter((a) => a.role === 'variant');
  const variants = (all.data as unknown as Array<VariantArtifact<C11Outputs>>)
    .filter((v) => v.outputs.kind === 'window')
    .map((v) => ({ id: v.variant_id, title: entries.find((e) => e.variant_id === v.variant_id)?.short_title ?? text(WINDOW_TEXT, v.outputs.window.window_id), v }));
  return (
    <ViewsRow>
      <C11VariantsTable variants={variants} onPick={onPick} current={sel.data.variant.variant_id} />
    </ViewsRow>
  );
}

/** The case, the span of the hyperparameters first, then the window, its portfolio and data, the ladder and the convention. */
export function C11ContextView({ sel }: { sel: C11Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const m = sel.data.manifest;
  const v = sel.data.variant;
  const fit = fitOf(sel);
  const h = o.hyperparameters;
  const w = o.window;
  const p = o.portfolio;
  const d = o.data_status;
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard title={{ en: 'The case and its sign convention', es: 'El caso y su convención de signo' }} {...card}>
        <FixtureNotice variant={v} />
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        <dl className="ct-defs" data-table="c11-convention">
          <dt>{pick({ en: 'Convention', es: 'Convención' }, lang)}</dt>
          <dd data-convention="definition">{pick(o.sign_convention.definition, lang)}</dd>
          <dt>{pick({ en: 'Truth status of this variant', es: 'Estado de verdad de esta variante' }, lang)}</dt>
          <dd>{v.provenance.truth_status}</dd>
        </dl>
      </PlotCard>
      <PlotCard title={{ en: 'The hyperparameters, fixed before any test window', es: 'Los hiperparámetros, fijados antes de cualquier ventana de prueba' }} {...card} note={spanLine(o)}>
        <dl className="ct-defs" data-table="c11-hyperparameters" data-tuned-on-test={String(h.tuned_on_test_window)}>
          <dt>{pick({ en: 'Fixed on', es: 'Fijados en' }, lang)}</dt>
          <dd>{`${h.fixed_on.start} - ${h.fixed_on.end}`}</dd>
          <dt>{pick({ en: 'Tuned on a test window', es: 'Ajustados en una ventana de prueba' }, lang)}</dt>
          <dd>{pick({ en: 'no', es: 'no' }, lang)}</dd>
          <dt>{pick({ en: 'Estimation window', es: 'Ventana de estimación' }, lang)}</dt>
          <dd>{pick({ en: `${count(h.estimation_window_days, 'en')} observed days`, es: `${count(h.estimation_window_days, 'es')} días observados` }, lang)}</dd>
          <dt>{pick({ en: 'EWMA decay', es: 'Decaimiento EWMA' }, lang)}</dt>
          <dd>{formatNumber(h.ewma_lambda, lang, { decimals: 2 })}</dd>
          <dt>{pick({ en: 'Age-weighting decay', es: 'Decaimiento de la ponderación por edad' }, lang)}</dt>
          <dd>{formatNumber(h.age_weight_lambda, lang, { decimals: 2 })}</dd>
          <dt>{pick({ en: 'EVT threshold fraction', es: 'Fracción del umbral EVT' }, lang)}</dt>
          <dd>{formatNumber(h.evt_threshold_fraction, lang, { percent: true, decimals: 0 })}</dd>
          <dt>{pick({ en: 'GARCH refit every', es: 'Reajuste GARCH cada' }, lang)}</dt>
          <dd>{pick({ en: `${count(h.garch_refit_every_days, 'en')} days`, es: `${count(h.garch_refit_every_days, 'es')} días` }, lang)}</dd>
          <dt>{pick({ en: 'CAViaR and GAS starts', es: 'Inicios de CAViaR y GAS' }, lang)}</dt>
          <dd>{`${count(h.caviar_n_starts, lang)}, ${count(h.gas_n_starts, lang)}`}</dd>
          <dt>{pick({ en: 'Seed', es: 'Semilla' }, lang)}</dt>
          <dd>{count(h.seed, lang)}</dd>
          {h.others.map((x) => (
            <Fragment key={x.name}>
              <dt>{x.name}</dt>
              <dd>{`${formatNumber(x.value, lang, { digits: 4 })} ${x.unit}`}</dd>
            </Fragment>
          ))}
        </dl>
      </PlotCard>
      <PlotCard title={{ en: 'The window and its portfolio', es: 'La ventana y su cartera' }} {...card}>
        <dl className="ct-defs" data-table="c11-window">
          <dt>{pick({ en: 'Window', es: 'Ventana' }, lang)}</dt>
          <dd>{pick(w.title, lang)}</dd>
          <dt>{pick({ en: 'Forecast days', es: 'Días pronosticados' }, lang)}</dt>
          <dd>{`${w.start_date} - ${w.end_date} (${count(w.n_forecast_days, lang)})`}</dd>
          <dt>{pick({ en: 'Portfolio', es: 'Cartera' }, lang)}</dt>
          <dd>{pick(p.description, lang)}</dd>
          <dt>{pick({ en: 'Weighting', es: 'Ponderación' }, lang)}</dt>
          <dd>{p.weighting === 'buy-and-hold' ? pick({ en: 'buy and hold', es: 'comprar y mantener' }, lang) : pick({ en: 'constant weights, rebalanced daily', es: 'pesos constantes, rebalanceo diario' }, lang)}</dd>
          <dt>{pick({ en: 'Components', es: 'Componentes' }, lang)}</dt>
          <dd>
            {p.components.map((c) => `${pick(c.label, lang)} (${formatNumber(c.weight, lang, { percent: true, decimals: 0 })}, ${pick(text(SOURCE_CLASS_TEXT, c.source_class), lang)})`).join('; ')}
          </dd>
          <dt>{pick({ en: 'Public series', es: 'Series públicas' }, lang)}</dt>
          <dd>
            {pick(
              {
                en: `${d.first_observation} to ${d.last_observation}, ${count(d.n_observed_days, 'en')} observed days; ${count(d.missing_days.count, 'en')} days skipped, not filled`,
                es: `${d.first_observation} a ${d.last_observation}, ${count(d.n_observed_days, 'es')} días observados; ${count(d.missing_days.count, 'es')} días omitidos, sin rellenar`,
              },
              lang,
            )}
          </dd>
        </dl>
        {o.grid.realised_loss.status === 'withheld-derived-only' ? (
          <p className="ct-note" data-state="unavailable">{`${NONE(lang)} (${o.grid.realised_loss.reason ?? ''})`}</p>
        ) : null}
        {fit ? (
          <ul className="ct-evidence" data-table="c11-sources">
            {fit.data_sources.map((s) => (
              <li key={s.series_id}>
                {pick(s.title, lang)}: <a href={s.url} rel="noreferrer noopener" target="_blank">{s.url}</a>. {pick(s.licence_note, lang)}
              </li>
            ))}
          </ul>
        ) : null}
      </PlotCard>
      {fit ? (
        <PlotCard title={{ en: 'The ladder of models', es: 'La escalera de modelos' }} {...card} note={{ en: 'From historical simulation to a challenger: each rung is refitted on the rolling window and forecasts one day ahead.', es: 'Desde la simulación histórica hasta un retador: cada escalón se reajusta en la ventana móvil y pronostica un día adelante.' }}>
          <table className="caos-table ct-wrap-head" data-table="c11-ladder">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Model', es: 'Modelo' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Rung', es: 'Escalón' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Source', es: 'Fuente' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'How it forecasts the ES', es: 'Cómo pronostica la ES' }, lang)}</th>
                <th>{pick({ en: 'Refits here', es: 'Reajustes aquí' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {fit.ladder.map((r) => {
                const wf = r.window_fits.find((x) => x.window_id === w.window_id);
                return (
                  <tr key={r.model_id} data-rung={r.rung} data-status={r.status}>
                    <td className="ct-text">{pick(r.title, lang)}</td>
                    <td className="ct-wide-only">{r.rung}</td>
                    <td className="ct-text ct-wide-only">{r.source}</td>
                    <td className="ct-text">
                      {r.es_method}
                      {r.not_run_reason ? <span className="ct-note" style={{ display: 'block' }}>{r.not_run_reason}</span> : null}
                    </td>
                    <td data-na={wf ? undefined : 'true'}>{wf ? `${count(wf.n_refits, lang)} (${count(wf.n_convergence_failures, lang)} ${pick({ en: 'failed', es: 'fallidos' }, lang)})` : NONE(lang)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </PlotCard>
      ) : null}
    </div>
  );
}

/** The live read-out of the Level section: the exceedances against the expected count and the Basel zone. */
export function LevelReadout({ sel }: { sel: C11Sel | null }) {
  const o = outputsOf(sel);
  const lv = o && sel ? levelOf(o, sel.model, sel.alpha) : null;
  const tl = lv?.traffic_light ?? null;
  const zone: BiText = tl ? zoneText(tl.final_zone) : sel?.alpha === 0.025 ? { en: 'Not defined at this level', es: 'No definida en este nivel' } : na();
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel ? alphaLabel(sel.alpha) : { en: 'This level', es: 'Este nivel' }}
      items={[
        { label: { en: 'Exceedances', es: 'Excedencias' }, value: lv?.n_exceedances ?? null, unitless: true, format: { decimals: 0 }, hint: { en: 'Days the loss exceeded the VaR of the model chosen.', es: 'Días en que la pérdida superó al VaR del modelo elegido.' } },
        { label: { en: 'Expected', es: 'Esperadas' }, value: lv?.expected_exceedances ?? null, unitless: true, format: { decimals: 2 }, hint: { en: 'The tail level times the days scored.', es: 'El nivel de cola por los días evaluados.' } },
        { label: { en: 'Basel zone', es: 'Zona de Basilea' }, text: zone, hint: { en: 'MAR32.9 on the last 250 days, at the 99 percent level only.', es: 'MAR32.9 en los últimos 250 días, solo al nivel de 99 por ciento.' } },
      ]}
    />
  );
}

/** The live read-out of the Model section: the eligibility, the average FZ0 score and the rung. */
export function ModelReadout({ sel }: { sel: C11Sel | null }) {
  const o = outputsOf(sel);
  const model = o?.models.find((x) => x.model_id === sel?.model) ?? null;
  const lv = o && sel ? levelOf(o, sel.model, sel.alpha) : null;
  const yes: BiText = { en: 'Yes', es: 'Sí' };
  const no: BiText = { en: 'No', es: 'No' };
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel ? modelLabel(sel, sel.model) : { en: 'This model', es: 'Este modelo' }}
      items={[
        { label: { en: 'Eligible', es: 'Elegible' }, text: model ? (model.eligible ? yes : no) : na(), hint: { en: 'No gate back-test is red at either level.', es: 'Ninguna prueba de compuerta está en rojo en ningún nivel.' } },
        { label: { en: 'Average FZ0', es: 'FZ0 medio' }, value: lv?.fz0_mean ?? null, unitless: true, format: { digits: 4 }, hint: lv?.fz0_reason ? { en: lv.fz0_reason, es: lv.fz0_reason } : { en: 'The joint VaR and ES score, lower is better.', es: 'El puntaje conjunto de VaR y ES, menor es mejor.' } },
        { label: { en: 'Rung', es: 'Escalón' }, text: sel && rungOf(sel, sel.model) ? { en: rungOf(sel, sel.model), es: rungOf(sel, sel.model) } : na(), hint: { en: 'The place of the model on the ladder from historical simulation to a challenger.', es: 'El lugar del modelo en la escalera desde la simulación histórica hasta un retador.' } },
      ]}
    />
  );
}

/** The live read-out of the Back-test section: the statistic, the p-value and the light of the test chosen. */
export function TestReadout({ sel }: { sel: C11Sel | null }) {
  const o = outputsOf(sel);
  const t = sel ? testsOf(sel, o, sel.model, sel.alpha).find((x) => x.test_id === sel.test) ?? null : null;
  const ran = t !== null && t.light !== 'not_evaluated' && t.light !== 'error';
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel?.test ? testName(sel.test) : { en: 'This back-test', es: 'Este backtest' }}
      items={[
        { label: { en: 'Statistic', es: 'Estadístico' }, value: ran ? t.statistic : null, unitless: true, format: { digits: 4 }, hint: { en: t?.notes ?? 'The statistic of the test, when it ran.', es: t?.notes ?? 'El estadístico de la prueba, cuando corrió.' } },
        { label: { en: 'p-value', es: 'Valor p' }, value: ran ? t.p_value : null, unitless: true, format: { digits: 2 }, hint: { en: 'The probability of a statistic this large if the model were right.', es: 'La probabilidad de un estadístico así de grande si el modelo fuera correcto.' } },
        { label: { en: 'Light', es: 'Luz' }, text: t ? zoneText(t.light) : na(), hint: { en: 'Under the committed policy; a test that did not run is not evaluated.', es: 'Bajo la política comprometida; una prueba que no corrió no se evalúa.' } },
      ]}
    />
  );
}
