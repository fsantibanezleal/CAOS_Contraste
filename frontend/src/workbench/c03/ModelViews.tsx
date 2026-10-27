// C03's Model and Validation groups: the PD rungs compared on the test cohort, the calibration by predicted-risk
// decile, the training window of each test cohort (it ends before the cohort starts) with the rungs fitted, and the
// tests the engine returned. A rung that was not fitted on this cohort is "not available" with its reason.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable, MaybeNumber } from '../c06/format';
import { Pending } from '../Pending';
import { inputName } from '../names';
import { U6TestsTable, p2, useCard } from './U6Shared';
import { fitOf, fyRange, outputsOf, reasonText, rungLabel, type C03Sel } from './selection';

// three fixed decimals: the precision does not change inside a column (R3 c04 m2)
const d3 = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 3 });
const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });

/** The PD rungs on this test cohort: discrimination with its interval, Brier and the calibration gap at five years. */
export function RungsView({ sel }: { sel: C03Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const label = (id: string) => rungLabel(sel, id);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The PD rungs on this cohort', es: 'Los peldaños de PD en esta cohorte' }}
        {...card}
        note={{
          en: 'AUC on the vintages of the test cohort that have reached their 5-year mark, with its interval. A rung that was not fitted on this cohort has no number, and its reason says why.',
          es: 'AUC sobre las cosechas de la cohorte de prueba que alcanzaron su marca de 5 años, con su intervalo. Un peldaño que no se ajustó en esta cohorte no tiene número, y su razón dice por qué.',
        }}
      >
        <ChartOverTable
          chart={
            <BarChart
              title={{ en: 'AUC by rung', es: 'AUC por peldaño' }}
              height="fill"
              orientation="horizontal"
              data={o.rung_comparison.map((r) => ({ id: r.rung_id, label: label(r.rung_id), value: r.auc, tone: 'accent' as const, highlight: r.rung_id === sel.rung, hint: label(r.rung_id) }))}
              axis={{ label: { en: 'AUC (higher is better)', es: 'AUC (más alto es mejor)' }, format: { digits: 3 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="pd-rungs">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Model', es: 'Modelo' }, lang)}</th>
                <th>AUC</th>
                <th className="ct-wide-only">{pick({ en: 'AUC interval', es: 'Intervalo del AUC' }, lang)}</th>
                <th>Brier</th>
                <th>{pick({ en: 'Gap at 5 years', es: 'Brecha a 5 años' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.rung_comparison.map((r) => (
                <tr key={r.rung_id} data-rung={r.rung_id} className={r.rung_id === sel.rung ? 'ct-current' : undefined}>
                  <td className="ct-text" title={r.rung_id}>{pick(label(r.rung_id), lang)}</td>
                  <td>
                    <MaybeNumber value={r.auc} reason={r.reason ? pick(reasonText(r.reason), lang) : r.reason} format={(v) => d3(v, lang)} />
                  </td>
                  <td className="ct-wide-only">
                    {r.auc_ci_low !== null && r.auc_ci_high !== null ? `${d3(r.auc_ci_low, lang)} ${pick({ en: 'to', es: 'a' }, lang)} ${d3(r.auc_ci_high, lang)}` : formatNumber(null, lang)}
                  </td>
                  <td>
                    <MaybeNumber value={r.brier} reason={null} format={(v) => d3(v, lang)} />
                  </td>
                  <td>
                    <MaybeNumber value={r.calibration_gap_5y} reason={null} format={(v) => p2(v, lang)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** Predicted against observed PD by decile of predicted risk, with the interval of the observed rate, and the tests the engine returned. */
export function CalibrationView({ sel }: { sel: C03Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const rows = o.calibration.rows;
  const series = [
    { label: { en: 'Observed rate', es: 'Tasa observada' }, values: rows.map((r) => r.observed_pd), color: '--color-accent' as const, mode: 'points' as const, size: 10 },
    { label: { en: 'Interval, low', es: 'Intervalo, inferior' }, values: rows.map((r) => r.ci_low), color: '--color-fg-subtle' as const, width: 1.2, dash: [4, 3] },
    { label: { en: 'Interval, high', es: 'Intervalo, superior' }, values: rows.map((r) => r.ci_high), color: '--color-fg-subtle' as const, width: 1.2, dash: [4, 3] },
  ];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Calibration by predicted-risk decile', es: 'Calibración por decil de riesgo predicho' }}
        {...card}
        note={{
          en: 'Each point is a tenth of the loans, ordered by predicted PD: the predicted PD on the horizontal axis, the observed rate on the vertical one, the identity line is a perfect calibration.',
          es: 'Cada punto es una décima parte de los créditos, ordenados por PD predicha: la PD predicha en el eje horizontal, la tasa observada en el vertical, la línea identidad es una calibración perfecta.',
        }}
      >
        {/* the parity plot keeps a stage of 22 rem, so it is drawn square at about 300 px at 1280 (R3 c04 m1: 140 x 170 px) */}
        <ChartOverTable
          chartMin="22rem"
          chart={
            <UPlotChart
              height="fill"
              parity
              x={{ values: rows.map((r) => r.predicted_pd), label: { en: 'Predicted PD', es: 'PD predicha' }, format: { percent: true, digits: 2 } }}
              y={{ label: { en: 'Observed rate', es: 'Tasa observada' }, format: { percent: true, digits: 2 } }}
              series={series}
            />
          }
        >
          <p className="ct-note" data-scope="calibration">{`${pick({ en: 'Scope', es: 'Alcance' }, lang)}: ${pick(o.calibration.scope, lang)}`}</p>
          <table className="caos-table ct-wrap-head" data-table="deciles">
            <thead>
              <tr>
                <th>{pick({ en: 'Decile', es: 'Decil' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Loans', es: 'Créditos' }, lang)}</th>
                <th>{pick({ en: 'Predicted', es: 'Predicha' }, lang)}</th>
                <th>{pick({ en: 'Observed', es: 'Observada' }, lang)}</th>
                <th>{pick({ en: 'Interval', es: 'Intervalo' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.decile} data-decile={r.decile}>
                  <td>{r.decile}</td>
                  <td className="ct-wide-only">{count(r.n, lang)}</td>
                  <td>{p2(r.predicted_pd, lang)}</td>
                  <td>{p2(r.observed_pd, lang)}</td>
                  <td>{`${p2(r.ci_low, lang)} ${pick({ en: 'to', es: 'a' }, lang)} ${p2(r.ci_high, lang)}`}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <U6TestsTable variant={sel.data.variant} modelLabel={(id) => pick(rungLabel(sel, id), lang)} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The training window of this cohort and of every test cohort, and the rungs the models artifact fitted. */
export function TrainingView({ sel }: { sel: C03Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const fit = fitOf(sel);
  const t = o.training;
  const yes = pick({ en: 'yes', es: 'sí' }, lang);
  const no = pick({ en: 'no', es: 'no' }, lang);
  const windows = fit?.cohort_windows ?? [];
  const rung = fit?.ladder.find((r) => r.rung_id === sel.rung);
  // the models artifact fits one ladder, on the window of the latest cohort: say so under every cohort (the rungs are not refitted per cohort)
  const fitWindow = rung ? windows.find((w) => w.training.cutoff_date === rung.training_cutoff) : undefined;
  const fitCaption = (l: 'en' | 'es') => {
    if (!rung) return '';
    const label = rungLabel(sel, rung.rung_id)[l];
    const window = fitWindow ? fitWindow.label[l] : rung.training_cutoff;
    const range = fitWindow ? fyRange(fitWindow.training.first_fy, fitWindow.training.last_fy) : '';
    const other = fitWindow && fitWindow.id !== o.cohort.id;
    // each input by its name (the raw-id scan: log10_amount, term_months)
    const inputs = rung.covariates.map((c) => (inputName(c) ?? { en: c, es: c })[l]).join(', ');
    return l === 'en'
      ? `${label}: ${inputs} (${rung.engine}). Rungs as fitted for the window of the cohort ${window}${range ? ` (vintages ${range})` : ''}, cut-off ${rung.training_cutoff}${other ? `, not for the window of this cohort (${o.cohort.label.en})` : ''}`
      : `${label}: ${inputs} (${rung.engine}). Peldaños tal como se ajustaron para la ventana de la cohorte ${window}${range ? ` (cosechas ${range})` : ''}, corte ${rung.training_cutoff}${other ? `, no para la ventana de esta cohorte (${o.cohort.label.es})` : ''}`;
  };
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={{ en: 'The training window of each test cohort', es: 'La ventana de entrenamiento de cada cohorte de prueba' }}
        {...card}
        note={{
          en: 'A test cohort is trained only on vintages whose 5-year mark closed before the cohort\'s first approval, so no outcome is seen early: the last vintage trained on is at least six fiscal years before the first vintage tested. The crisis is in the training of the later cohorts only.',
          es: 'Una cohorte de prueba se entrena solo con cosechas cuya marca de 5 años cerró antes de la primera aprobación de la cohorte, así que ningún resultado se ve antes de tiempo: la última cosecha de entrenamiento está al menos seis años fiscales antes de la primera cosecha probada. La crisis está en el entrenamiento de las cohortes posteriores solamente.',
        }}
      >
        {windows.length === 0 ? (
          <p className="ct-note" data-state="unavailable">{pick({ en: 'Not available: the models artifact of this variant carries no cohort windows.', es: 'No disponible: el artefacto de modelos de esta variante no trae las ventanas de cohortes.' }, lang)}</p>
        ) : (
          <ChartOverTable
            chart={
              <UPlotChart
                height="fill"
                x={{ values: windows.map((w) => w.first_fy), label: { en: 'First fiscal year of the test cohort', es: 'Primer año fiscal de la cohorte de prueba' }, format: { decimals: 0, grouping: false } }}
                y={{ label: { en: 'Fiscal year', es: 'Año fiscal' }, format: { decimals: 0, grouping: false } }}
                series={[
                  { label: { en: 'Last vintage trained on', es: 'Última cosecha de entrenamiento' }, values: windows.map((w) => w.training.last_fy), color: '--color-accent', mode: 'points', size: 11 },
                  { label: { en: 'First vintage tested', es: 'Primera cosecha de prueba' }, values: windows.map((w) => w.first_fy), color: '--color-fg-subtle', width: 1.6, dash: [5, 4] },
                ]}
              />
            }
          >
            <table className="caos-table ct-wrap-head" data-table="training-windows">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Test cohort', es: 'Cohorte de prueba' }, lang)}</th>
                  <th>{pick({ en: 'Trained on', es: 'Entrenada con' }, lang)}</th>
                  <th className="ct-wide-only">{pick({ en: 'Cut-off', es: 'Corte' }, lang)}</th>
                  <th className="ct-wide-only">{pick({ en: 'Loans', es: 'Créditos' }, lang)}</th>
                  <th>{pick({ en: 'Crisis in training', es: 'Crisis en el entrenamiento' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {windows.map((w) => (
                  <tr key={w.id} data-window={w.id} className={w.id === o.cohort.id ? 'ct-current' : undefined}>
                    <td className="ct-text">{pick(w.label, lang)}</td>
                    <td>{fyRange(w.training.first_fy, w.training.last_fy)}</td>
                    <td className="ct-wide-only">{w.training.cutoff_date}</td>
                    <td className="ct-wide-only">{count(w.training.n_loans, lang)}</td>
                    <td data-crisis={String(w.training.crisis_included)}>{w.training.crisis_included ? yes : no}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ChartOverTable>
        )}
      </PlotCard>
      <PlotCard fill title={{ en: 'This cohort and its rung', es: 'Esta cohorte y su peldaño' }} {...card}>
        <div className="ct-scroll" data-caos-flow="">
          {/* the cohort's facts as a two-column table: a table is what a card draws (gate G6), so a rung with no coefficients still
              fills its card (a definition list left it painting 22% of its stage) */}
          <table className="caos-table" data-training={o.cohort.id} data-table="cohort-facts">
            <tbody>
              <tr>
                <th scope="row" className="ct-text">{pick({ en: 'Test cohort', es: 'Cohorte de prueba' }, lang)}</th>
                <td className="ct-text">{`${pick(o.cohort.label, lang)} (${fyRange(o.cohort.first_fy, o.cohort.last_fy)})`}</td>
              </tr>
              <tr>
                <th scope="row" className="ct-text">{pick({ en: 'Trained on vintages', es: 'Entrenada con cosechas' }, lang)}</th>
                <td className="ct-text">{fyRange(t.first_fy, t.last_fy)}</td>
              </tr>
              <tr>
                <th scope="row" className="ct-text">{pick({ en: 'Cut-off', es: 'Corte' }, lang)}</th>
                <td className="ct-text">{t.cutoff_date}</td>
              </tr>
              <tr>
                <th scope="row" className="ct-text">{pick({ en: 'Loans and charge-offs', es: 'Créditos y castigos' }, lang)}</th>
                <td className="ct-text">{`${count(t.n_loans, lang)} / ${count(t.n_events, lang)}`}</td>
              </tr>
              <tr>
                <th scope="row" className="ct-text">{pick({ en: 'Crisis in the training', es: 'Crisis en el entrenamiento' }, lang)}</th>
                <td className="ct-text" data-crisis={String(t.crisis_included)}>{t.crisis_included ? yes : no}</td>
              </tr>
            </tbody>
          </table>
          {rung ? (
            <table className="caos-table ct-wrap-head" data-table="rung-coefficients">
              <caption className="ct-note" data-block="rung-fit-window">{fitCaption(lang)}</caption>
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Coefficient', es: 'Coeficiente' }, lang)}</th>
                  <th>{pick({ en: 'Estimate', es: 'Estimación' }, lang)}</th>
                  <th>{pick({ en: 'Std. error', es: 'Error est.' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {rung.coefficients.length === 0 ? (
                  <tr>
                    <td className="ct-text" colSpan={3}>{pick({ en: 'This rung has no coefficients to list.', es: 'Este peldaño no tiene coeficientes que listar.' }, lang)}</td>
                  </tr>
                ) : (
                  rung.coefficients.map((c) => (
                    <tr key={c.name}>
                      <td className="ct-text">{pick(inputName(c.name) ?? { en: c.name, es: c.name }, lang)}</td>
                      <td>{formatNumber(c.estimate, lang, { digits: 3 })}</td>
                      <td>
                        <MaybeNumber value={c.std_error} reason={null} format={(v) => formatNumber(v, lang, { digits: 3 })} />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          ) : (
            <p className="ct-note" data-state="unavailable">{pick({ en: 'Not available: the models artifact does not list the rung in focus.', es: 'No disponible: el artefacto de modelos no lista el peldaño en foco.' }, lang)}</p>
          )}
          {/* the rationale is a paragraph under the coefficients: as a row of the list it ran to a dozen lines in a narrow column and
              pushed the table out of the card, which then painted 6% of its stage (G6, floor 30%) */}
          <p className="ct-note" data-block="window-rationale">
            <strong>{pick({ en: 'Why this window.', es: 'Por qué esta ventana.' }, lang)}</strong> {pick(t.rationale, lang)}
          </p>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}
