// C06's validation views: the lifetime PD ladder the fit carries, the lifetime backtest, the calibration by predicted
// risk decile, the rung comparison, the identities of the reconciliation on their one tolerance basis, and the rows of
// the tests the engine returned. A value the contract allows to be null is "not available" with its reason.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, useWorkbenchState, type ShellColorToken } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import type { TestRow, VariantArtifact } from '../../lib/contract.types';
import { LIGHT_TEXT } from '../../lib/policy';
import { REPLAY, provenanceOf } from '../model';
import { Pending } from '../Pending';
import { modelName } from '../names';
import { STAGE_TEXT, ChartOverTable, MaybeNumber, alignTo, money, pct, segmentLabel, unionX } from './format';
import { referenceText } from '../c03/U6Shared';
import { cohortText, fitOf, ifrs9TestText, movementText, outputsOf, type C06Sel } from './selection';

// seven cohorts are seven curves: seven distinct colour tokens (the predicted line of each stays dashed)
const COLORS: ShellColorToken[] = ['--color-accent', '--color-magenta', '--color-warn', '--color-good', '--color-bad', '--color-fg-subtle', '--color-fg'];

const ESTIMATOR = { 'kaplan-meier': 'Kaplan-Meier', 'aalen-johansen': 'Aalen-Johansen' } as const;

/** The ladder of lifetime PD rungs, the one-factor conversion, LGD and EAD that the bake used (the models artifact). */
export function LadderView({ sel }: { sel: C06Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const fit = fitOf(sel);
  if (!fit) {
    return (
      <PlotCard title={{ en: 'The lifetime PD ladder', es: 'La escalera de PD de vida' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <p className="caos-pending" data-state="unavailable">
          {pick({ en: 'Not available: the models artifact of this variant carries no fit.', es: 'No disponible: el artefacto de modelos de esta variante no trae el ajuste.' }, lang)}
        </p>
      </PlotCard>
    );
  }
  const grid = unionX(...fit.ladder.map((r) => r.baseline.months));
  const series = fit.ladder.map((r, i) => ({
    label: { en: `${r.rung_id} (${r.kind})`, es: `${r.rung_id} (${r.kind})` },
    values: alignTo(r.baseline.months, r.baseline.cumulative_pd, grid),
    color: COLORS[i % COLORS.length],
    width: 2,
  }));
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={{ en: 'Baseline cumulative PD by rung of the ladder', es: 'PD acumulada base por peldaño de la escalera' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: 'Kaplan-Meier, discrete-time hazard and Cox: each rung adds a piece (covariates, macro covariates, competing prepayment) over the one before, and each is checked against the same outcomes.',
          es: 'Kaplan-Meier, riesgo discreto en el tiempo y Cox: cada peldaño agrega una pieza (covariables, covariables macro, prepago como riesgo competitivo) sobre el anterior, y cada uno se contrasta con los mismos resultados.',
        }}
      >
        <UPlotChart
          height="fill"
          x={{ values: grid, label: { en: 'Months since origination', es: 'Meses desde la originación' }, format: { decimals: 0 } }}
          y={{ label: { en: 'Cumulative PD', es: 'PD acumulada' }, format: { percent: true, digits: 2 } }}
          series={series}
        />
      </PlotCard>
      <PlotCard fill title={{ en: 'The rungs, the conversion, LGD and EAD', es: 'Los peldaños, la conversión, LGD y EAD' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <div className="ct-scroll" data-caos-flow="">
          <table className="caos-table ct-wrap-head" data-table="ladder">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Rung', es: 'Peldaño' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Covariates', es: 'Covariables' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Prepayment competes', es: 'Prepago compite' }, lang)}</th>
                <th>{pick({ en: 'Cut-off', es: 'Corte' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {fit.ladder.map((r) => (
                <tr key={r.rung_id} data-rung={r.rung_id}>
                  <td className="ct-text">{r.rung_id}</td>
                  <td className="ct-text">
                    {r.covariates.length || r.macro_covariates.length ? (
                      <details data-covariates={r.rung_id}>
                        <summary>{pick({ en: `${r.covariates.length} covariates, ${r.macro_covariates.length} macro`, es: `${r.covariates.length} covariables, ${r.macro_covariates.length} macro` }, lang)}</summary>
                        <p className="ct-note">{r.covariates.join(', ')}</p>
                        {r.macro_covariates.length ? <p className="ct-note">{`${pick({ en: 'Macro', es: 'Macro' }, lang)}: ${r.macro_covariates.join(', ')}`}</p> : null}
                      </details>
                    ) : (
                      pick({ en: 'none', es: 'ninguna' }, lang)
                    )}
                  </td>
                  <td className="ct-text">{r.competing_prepayment ? pick({ en: 'yes', es: 'sí' }, lang) : pick({ en: 'no', es: 'no' }, lang)}</td>
                  <td>{r.training_cutoff}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="caos-table" data-table="conversion">
            <tbody>
              <tr data-row="pit">
                <td className="ct-text">{pick({ en: 'Through the cycle to point in time', es: 'De a través del ciclo a puntual' }, lang)}</td>
                <td>{`${fit.pit.method}; rho ${pct(fit.pit.rho, lang, 0)}`}</td>
              </tr>
              <tr data-row="lgd">
                <td className="ct-text">{pick({ en: 'LGD', es: 'LGD' }, lang)}</td>
                <td>{`${fit.lgd.kind}, ${fit.lgd.discounting}: ${fit.lgd.segments.map((s) => `${s.segment_id} ${pct(s.lgd, lang, 0)}`).join(', ')}`}</td>
              </tr>
              <tr data-row="ead">
                <td className="ct-text">{pick({ en: 'EAD: revolving conversion factor', es: 'EAD: factor de conversión revolvente' }, lang)}</td>
                <td>
                  <MaybeNumber value={fit.ead.ccf_revolving} reason={fit.ead.reason} format={(v) => pct(v, lang, 0)} />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

/** Observed against predicted cumulative default by origination cohort and horizon; a horizon not observed is not available, with its reason. */
export function BacktestView({ sel }: { sel: C06Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const rows = o.lifetime_backtest.rows;
  const cohorts = [...new Set(rows.map((r) => r.origination_cohort))];
  const grid = unionX(rows.map((r) => r.months));
  const series = cohorts.flatMap((c, i) => {
    const mine = rows.filter((r) => r.origination_cohort === c);
    const at = (field: 'predicted_cumulative_pd' | 'observed_cumulative_pd') => grid.map((m) => mine.find((r) => r.months === m)?.[field] ?? null);
    return [
      { label: { en: `Predicted, ${cohortText(c).en}`, es: `Predicha, ${cohortText(c).es}` }, values: at('predicted_cumulative_pd'), color: COLORS[i % COLORS.length], width: 1.8, dash: [6, 3] },
      { label: { en: `Observed, ${cohortText(c).en}`, es: `Observada, ${cohortText(c).es}` }, values: at('observed_cumulative_pd'), color: COLORS[i % COLORS.length], width: 2.6 },
    ];
  });
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={{ en: 'Lifetime backtest: predicted against observed cumulative PD', es: 'Backtest de vida: PD acumulada predicha contra observada' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: 'Observed cumulative incidence by origination cohort: Aalen-Johansen when prepayment competes with default, Kaplan-Meier otherwise. A horizon not yet observed is a gap with its reason in the table, never a zero.',
          es: 'Incidencia acumulada observada por cohorte de originación: Aalen-Johansen cuando el prepago compite con el incumplimiento, Kaplan-Meier en otro caso. Un horizonte aún no observado es un hueco con su razón en la tabla, nunca un cero.',
        }}
      >
        <UPlotChart
          height="fill"
          x={{ values: grid, label: { en: 'Months since origination', es: 'Meses desde la originación' }, format: { decimals: 0 } }}
          y={{ label: { en: 'Cumulative PD', es: 'PD acumulada' }, format: { percent: true, digits: 2 } }}
          series={series}
        />
      </PlotCard>
      <PlotCard fill title={{ en: 'The backtest in numbers', es: 'El backtest en números' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <div className="ct-scroll" data-caos-flow="">
          <table className="caos-table ct-wrap-head" data-table="lifetime-backtest">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Cohort', es: 'Cohorte' }, lang)}</th>
                <th>{pick({ en: 'Months', es: 'Meses' }, lang)}</th>
                <th>{pick({ en: 'Predicted', es: 'Predicha' }, lang)}</th>
                <th>{pick({ en: 'Observed', es: 'Observada' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Gap', es: 'Brecha' }, lang)}</th>
                <th className="ct-wide-only">Brier</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Estimator', es: 'Estimador' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={`${r.origination_cohort}-${r.months}`} data-cohort={r.origination_cohort} data-months={r.months}>
                  <td className="ct-text">{pick(cohortText(r.origination_cohort), lang)}</td>
                  <td>{r.months}</td>
                  <td>{pct(r.predicted_cumulative_pd, lang, 3)}</td>
                  <td>
                    <MaybeNumber value={r.observed_cumulative_pd} reason={r.reason} format={(v) => pct(v, lang, 3)} />
                  </td>
                  <td className="ct-wide-only">
                    <MaybeNumber value={r.gap} reason={null} format={(v) => pct(v, lang, 3)} />
                  </td>
                  <td className="ct-wide-only">
                    <MaybeNumber value={r.brier} reason={null} format={(v) => formatNumber(v, lang, { digits: 3 })} />
                  </td>
                  <td className="ct-text ct-wide-only">{ESTIMATOR[r.estimator]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

/** Calibration at 12, 24 and 36 months by predicted-risk decile against the observed cumulative incidence. */
export function DecileView({ sel }: { sel: C06Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const d = o.decile_calibration;
  const cohort = d.rows.find((r) => r.origination_cohort === 'all')?.origination_cohort ?? d.rows[0]?.origination_cohort;
  const mine = d.rows.filter((r) => r.origination_cohort === cohort);
  // a Cohort column that holds one value in every row says nothing: the cohort is in the title of the drawing
  const oneCohort = new Set(d.rows.map((r) => r.origination_cohort)).size === 1;
  const deciles = unionX(mine.map((r) => r.decile));
  const horizons = [...new Set(mine.map((r) => r.months))].sort((a, b) => a - b);
  const series = horizons.flatMap((h, i) => {
    const at = (field: 'predicted_cumulative_pd' | 'observed_cumulative_pd') => deciles.map((x) => mine.find((r) => r.months === h && r.decile === x)?.[field] ?? null);
    return [
      { label: { en: `Predicted, ${h} m`, es: `Predicha, ${h} m` }, values: at('predicted_cumulative_pd'), color: COLORS[i % COLORS.length], width: 1.8, dash: [6, 3] },
      { label: { en: `Observed, ${h} m`, es: `Observada, ${h} m` }, values: at('observed_cumulative_pd'), color: COLORS[i % COLORS.length], width: 2.6 },
    ];
  });
  return (
    <ViewsRow shares={[1, 1]}>
      <PlotCard
        fill
        title={{ en: `Calibration by risk decile, rung ${d.rung_id}${cohort ? `, cohort ${cohortText(cohort).en}` : ''}`, es: `Calibración por decil de riesgo, peldaño ${d.rung_id}${cohort ? `, cohorte ${cohortText(cohort).es}` : ''}` }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{ en: 'Decile 1 is the lowest predicted risk. A cell with no observation yet is a gap with its reason in the table.', es: 'El decil 1 es el de menor riesgo predicho. Una celda sin observación aún es un hueco con su razón en la tabla.' }}
      >
        <UPlotChart
          height="fill"
          x={{ values: deciles, label: { en: 'Predicted-risk decile', es: 'Decil de riesgo predicho' }, format: { decimals: 0 } }}
          y={{ label: { en: 'Cumulative PD', es: 'PD acumulada' }, format: { percent: true, digits: 2 } }}
          series={series}
        />
      </PlotCard>
      <PlotCard fill title={{ en: 'The deciles in numbers', es: 'Los deciles en números' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <div className="ct-scroll" data-caos-flow="">
          <table className="caos-table ct-wrap-head" data-table="decile-calibration">
            <thead>
              <tr>
                {oneCohort ? null : <th className="ct-text">{pick({ en: 'Cohort', es: 'Cohorte' }, lang)}</th>}
                <th>{pick({ en: 'Months', es: 'Meses' }, lang)}</th>
                <th>{pick({ en: 'Decile', es: 'Decil' }, lang)}</th>
                <th>{pick({ en: 'Accounts', es: 'Cuentas' }, lang)}</th>
                <th>{pick({ en: 'Predicted', es: 'Predicha' }, lang)}</th>
                <th>{pick({ en: 'Observed', es: 'Observada' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {d.rows.map((r) => (
                <tr key={`${r.origination_cohort}-${r.months}-${r.decile}`} data-cohort={r.origination_cohort} data-months={r.months} data-decile={r.decile}>
                  {oneCohort ? null : <td className="ct-text">{pick(cohortText(r.origination_cohort), lang)}</td>}
                  <td>{r.months}</td>
                  <td>{r.decile}</td>
                  <td>{formatNumber(r.n, lang, { decimals: 0 })}</td>
                  <td>{pct(r.predicted_cumulative_pd, lang, 3)}</td>
                  <td>
                    <MaybeNumber value={r.observed_cumulative_pd} reason={r.reason} format={(v) => pct(v, lang, 3)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

/** The rungs side by side on discrimination, integrated Brier and the 12-month calibration gap. */
export function RungsView({ sel }: { sel: C06Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The rungs compared: integrated Brier score', es: 'Los peldaños comparados: puntaje de Brier integrado' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{ en: 'Lower is better. A rung with no covariates has no concordance index: the table says why instead of a number.', es: 'Menor es mejor. Un peldaño sin covariables no tiene índice de concordancia: la tabla dice por qué en vez de un número.' }}
      >
        <ChartOverTable
          chart={
            <BarChart
              title={{ en: 'Integrated Brier score by rung', es: 'Puntaje de Brier integrado por peldaño' }}
              height="fill"
              orientation="vertical"
              data={o.rung_comparison.map((r) => ({ id: r.rung_id, label: { en: r.rung_id, es: r.rung_id }, value: r.integrated_brier, tone: 'accent' as const }))}
              axis={{ label: { en: 'Integrated Brier', es: 'Brier integrado' }, format: { digits: 3 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="rung-comparison">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Rung', es: 'Peldaño' }, lang)}</th>
                <th>{pick({ en: 'Concordance index', es: 'Índice de concordancia' }, lang)}</th>
                <th>{pick({ en: 'Integrated Brier', es: 'Brier integrado' }, lang)}</th>
                <th>{pick({ en: '12-month gap', es: 'Brecha a 12 meses' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.rung_comparison.map((r) => (
                <tr key={r.rung_id} data-rung={r.rung_id}>
                  <td className="ct-text">
                    {r.rung_id}
                    {r.reason ? <span className="ct-note" data-reason="rung" style={{ display: 'block', whiteSpace: 'normal' }}>{pick(r.reason, lang)}</span> : null}
                  </td>
                  <td>
                    <MaybeNumber value={r.c_index} reason={null} format={(v) => formatNumber(v, lang, { digits: 3 })} />
                  </td>
                  <td>
                    <MaybeNumber value={r.integrated_brier} reason={null} format={(v) => formatNumber(v, lang, { digits: 3 })} />
                  </td>
                  <td>
                    <MaybeNumber value={r.calibration_gap_12m} reason={null} format={(v) => pct(v, lang, 3)} />
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

/** The roll-forwards of the reconciliation: each identity closes within the one tolerance basis, or the table says it does not. */
export function IdentitiesView({ sel }: { sel: C06Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const r = o.reconciliation;
  const g = r.gross_carrying_amount.reduce((a, row) => a + Math.abs(row.closing), 0);
  const basis = r.tolerance * Math.max(1, g);
  const cur = r.currency;
  const yes = pick({ en: 'closes', es: 'cierra' }, lang);
  const no = pick({ en: 'does not close', es: 'no cierra' }, lang);
  const stage = (s: string) => s;
  return (
    <ViewsRow>
      <PlotCard
        title={{ en: 'The allowance roll-forward (IFRS 7 35H)', es: 'La conciliación de la cobertura (IFRS 7 35H)' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: `Opening plus movements equals closing within ${formatNumber(basis, 'en', { digits: 3 })} ${cur}: ${formatNumber(r.tolerance, 'en', { digits: 1 })} times the larger of 1 and the total gross carrying amount.`,
          es: `La inicial más los movimientos es igual a la final dentro de ${formatNumber(basis, 'es', { digits: 3 })} ${cur}: ${formatNumber(r.tolerance, 'es', { digits: 1 })} veces el mayor entre 1 y el valor en libros bruto total.`,
        }}
      >
        <div className="ct-scroll" data-caos-flow="">
          <table className="caos-table ct-wrap-head" data-table="allowance-roll-forward">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Stage', es: 'Etapa' }, lang)}</th>
                <th>{pick({ en: 'Opening', es: 'Inicial' }, lang)}</th>
                <th>{pick({ en: 'Movements', es: 'Movimientos' }, lang)}</th>
                <th>{pick({ en: 'Closing', es: 'Final' }, lang)}</th>
                <th>{pick({ en: 'Residual', es: 'Residuo' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Identity', es: 'Identidad' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {r.allowance.map((row) => {
                const closes = Math.abs(row.residual) <= basis;
                return (
                  <tr key={row.stage} data-stage={stage(row.stage)} data-closes={String(closes)}>
                    <td className="ct-text">{pick(STAGE_TEXT[row.stage] ?? { en: row.stage, es: row.stage }, lang)}</td>
                    <td>{money(row.opening, lang, cur)}</td>
                    <td>{row.movements.map((m) => `${pick(movementText(m.line_id), lang)} ${money(m.amount, lang, cur)}`).join('; ')}</td>
                    <td>{money(row.closing, lang, cur)}</td>
                    <td>{formatNumber(row.residual, lang, { digits: 3 })}</td>
                    <td className="ct-text">{closes ? yes : no}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head" data-table="gca-roll-forward">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Stage (gross carrying amount, 35I)', es: 'Etapa (valor en libros bruto, 35I)' }, lang)}</th>
                <th>{pick({ en: 'Opening', es: 'Inicial' }, lang)}</th>
                <th>{pick({ en: 'Movements', es: 'Movimientos' }, lang)}</th>
                <th>{pick({ en: 'Closing', es: 'Final' }, lang)}</th>
                <th>{pick({ en: 'Residual', es: 'Residuo' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Identity', es: 'Identidad' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {r.gross_carrying_amount.map((row) => {
                const closes = Math.abs(row.residual) <= basis;
                return (
                  <tr key={row.stage} data-gca-stage={row.stage} data-closes={String(closes)}>
                    <td className="ct-text">{pick(STAGE_TEXT[row.stage] ?? { en: row.stage, es: row.stage }, lang)}</td>
                    <td>{money(row.opening, lang, cur)}</td>
                    <td>{row.movements.map((m) => `${pick(movementText(m.line_id), lang)} ${money(m.amount, lang, cur)}`).join('; ')}</td>
                    <td>{money(row.closing, lang, cur)}</td>
                    <td>{formatNumber(row.residual, lang, { digits: 3 })}</td>
                    <td className="ct-text">{closes ? yes : no}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

/** The rows the engine returned for the tests of this variant, each with its light, its reference and its notes. */
export function TestRowsCard({ variant, prov }: { variant: VariantArtifact; prov: ReturnType<typeof provenanceOf> }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const rows: TestRow[] = variant.tests;
  // a segment by the label its document gives it (C07's portfolio segments), else the term words of C06 (R2b c08 B2)
  const portfolio = (variant.outputs as { portfolio?: { segments?: Array<{ segment_id: string; label: { en: string; es: string } }> } }).portfolio;
  const segmentOf = (id: string) => portfolio?.segments?.find((s) => s.segment_id === id)?.label ?? segmentLabel(id);
  return (
    <PlotCard
      title={{ en: 'The tests the engine returned', es: 'Las pruebas que devolvió el motor' }}
      lane={REPLAY}
      provenance={prov}
      dataKey={stateKey}
      note={{ en: 'One row per test: its statistic, p-value when it has one, the light under the committed policy and its reference.', es: 'Una fila por prueba: su estadístico, valor p cuando lo tiene, la luz bajo la política versionada y su referencia.' }}
    >
      {rows.length === 0 ? (
        <p className="ct-note" data-state="unavailable">{pick({ en: 'This variant carries no test row.', es: 'Esta variante no trae filas de pruebas.' }, lang)}</p>
      ) : (
        <div className="ct-scroll" data-caos-flow="">
          <table className="caos-table ct-wrap-head" data-table="tests">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Test', es: 'Prueba' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Model', es: 'Modelo' }, lang)}</th>
                <th>{pick({ en: 'Statistic or metric', es: 'Estadístico o métrica' }, lang)}</th>
                <th>p</th>
                <th className="ct-text">{pick({ en: 'Light', es: 'Luz' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Reference', es: 'Referencia' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((t, i) => (
                <tr key={`${t.test_id}-${t.model_id}-${t.segment}-${i}`} data-test={t.test_id} data-light={t.light}>
                  <td className="ct-text">
                    <span title={t.test_id}>{pick(ifrs9TestText(t.test_id), lang)}</span>
                    {t.segment ? <span className="ct-note" style={{ display: 'block', whiteSpace: 'normal' }}>{pick(segmentOf(t.segment), lang)}</span> : null}
                  </td>
                  <td className="ct-text">{t.model_id ? pick(modelName(t.model_id, { caseId: variant.case_id, models: variant.model }) ?? { en: t.model_id, es: t.model_id }, lang) : '-'}</td>
                  <td>{formatNumber(t.statistic ?? t.metric, lang, { digits: 4 })}</td>
                  <td>{t.p_value === null ? formatNumber(null, lang) : formatNumber(t.p_value, lang, { digits: 2 })}</td>
                  <td className={`ct-text ct-light ct-light-${t.light}`}>
                    <span className="ct-light-word">{pick(LIGHT_TEXT[t.light], lang)}</span>
                  </td>
                  <td className="ct-text ct-wide-only">{referenceText(t, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PlotCard>
  );
}

export function TestsView({ sel }: { sel: C06Sel | null }) {
  if (!sel) return <Pending />;
  return <TestRowsCard variant={sel.data.variant} prov={provenanceOf(sel.data.variant.provenance.truth_status)} />;
}
