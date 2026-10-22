// C06's Model group views on the PD side: the term structures per scenario with the origination forward curve of the
// selected account, the SICR scatter with the multiplier, floor and threefold lines, and the non-linearity panel.
// Each draws what the c06-outputs document carries; the lines of the SICR rule are drawn from the document's own
// `settings.sicr`, never from constants of this file.
import { PlotCard, ViewsRow, pick, useShellLang, useWorkbenchState, type BiText, type ShellColorToken } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { provenanceOf, REPLAY } from '../model';
import { Pending } from '../Pending';
import { ChartOverTable, STAGE_COLOR, STAGE_TEXT, alignTo, money, pct, unionX, MaybeNumber, segmentLabel } from './format';
import { outputsOf, type C06Outputs, type C06Sel } from './selection';

const WEIGHTED: BiText = { en: 'Probability-weighted', es: 'Ponderada por probabilidad' };
const SCENARIO_COLORS: ShellColorToken[] = ['--color-accent', '--color-magenta', '--color-warn', '--color-good'];

const TRIGGER_TEXT: Record<string, BiText> = {
  none: { en: 'none', es: 'ninguno' },
  'relative-absolute': { en: 'multiplier and floor', es: 'multiplicador y piso' },
  threefold: { en: 'threefold', es: 'triple' },
  'dpd-backstop': { en: '30 dpd backstop', es: 'respaldo de 30 dpd' },
  forbearance: { en: 'forbearance', es: 'refinanciación' },
  'watch-list': { en: 'watch list', es: 'lista de vigilancia' },
  default: { en: 'default', es: 'incumplimiento' },
  collective: { en: 'collective', es: 'colectivo' },
  'cure-probation': { en: 'cure probation', es: 'prueba de cura' },
};

const MEASURE: Record<string, { key: 'cumulative_pd' | 'marginal_pd' | 'hazard'; label: { en: string; es: string } }> = {
  cumulative: { key: 'cumulative_pd', label: { en: 'Cumulative PD F(t)', es: 'PD acumulada F(t)' } },
  marginal: { key: 'marginal_pd', label: { en: 'Marginal PD q(t)', es: 'PD marginal q(t)' } },
  hazard: { key: 'hazard', label: { en: 'Conditional PD h(t) (hazard)', es: 'PD condicional h(t) (riesgo instantáneo)' } },
};

/** PD term structures per scenario for the selected segment, the weighted curve, and the account's origination curve. */
export function TermStructureView({ sel }: { sel: C06Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const m = MEASURE[sel.measure];
  const ids = [...o.scenarios.map((s) => s.id), 'weighted'];
  const rows = ids.map((id) => ({ id, ts: o.term_structures.find((t) => t.scenario_id === id && t.segment_id === sel.segment) })).filter((r) => r.ts);
  const acct = o.account_curves.find((a) => a.account_id === sel.account);
  const grid = unionX(...rows.map((r) => r.ts!.months), ...(sel.measure === 'cumulative' && acct ? [acct.months] : []));
  const label = (id: string): BiText => (id === 'weighted' ? WEIGHTED : (o.scenarios.find((s) => s.id === id)?.label ?? { en: id, es: id }));
  const series = [
    ...rows.map((r, i) => ({
      label: label(r.id),
      values: alignTo(r.ts!.months, r.ts![m.key], grid),
      color: (r.id === 'weighted' ? '--color-fg' : SCENARIO_COLORS[i % SCENARIO_COLORS.length]) as ShellColorToken,
      width: r.id === sel.scenario || r.id === 'weighted' ? 3 : 1.6,
    })),
    ...(sel.measure === 'cumulative' && acct
      ? [
          { label: { en: `Origination forward curve, ${acct.account_id}`, es: `Curva a plazo de originación, ${acct.account_id}` }, values: alignTo(acct.months, acct.origination_cumulative_pd, grid), color: '--color-fg-subtle' as ShellColorToken, width: 1.6, dash: [5, 4] },
          { label: { en: `Current curve, ${acct.account_id}`, es: `Curva actual, ${acct.account_id}` }, values: alignTo(acct.months, acct.current_cumulative_pd, grid), color: '--color-bad' as ShellColorToken, width: 1.6, dash: [2, 3] },
        ]
      : []),
  ];
  const at = (months: number[], v: number[], t: number) => {
    const i = months.indexOf(t);
    return i >= 0 ? v[i] : null;
  };
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `${MEASURE[sel.measure].label.en} by scenario, ${segmentLabel(sel.segment).en.toLowerCase()}`, es: `${MEASURE[sel.measure].label.es} por escenario, ${segmentLabel(sel.segment).es.toLowerCase()}` }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: 'h(t) is the conditional PD of a period given survival, q(t) = S(t-1) h(t) its unconditional (marginal) PD and F(t) the sum of q: the document names both. The weighted curve is the probability-weighted PD; the dashed pair is the selected account, its origination curve against the current one over the same remaining window.',
          es: 'h(t) es la PD condicional de un período dada la supervivencia, q(t) = S(t-1) h(t) su PD incondicional (marginal) y F(t) la suma de q: el documento nombra ambas. La curva ponderada es la PD ponderada por probabilidad; el par segmentado es la cuenta elegida, su curva de originación contra la actual en la misma ventana restante.',
        }}
      >
        <ChartOverTable chartMin="18rem"
          chart={
        <UPlotChart
          height="fill"
          x={{ values: grid, label: { en: 'Months after the reporting date', es: 'Meses desde la fecha de reporte' }, format: { decimals: 0 } }}
          y={{ label: m.label, format: { percent: true, digits: 2 } }}
          series={series}
        />
          }
        >
        <div>
          <table className="caos-table" data-table="term-structures">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Scenario', es: 'Escenario' }, lang)}</th>
                <th>{pick({ en: 'Weight', es: 'Peso' }, lang)}</th>
                <th>{`F(${o.horizon.stage1_months} m)`}</th>
                <th>{pick({ en: 'F(last)', es: 'F(último)' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const w = o.scenarios.find((s) => s.id === r.id)?.weight ?? null;
                const last = r.ts!.cumulative_pd[r.ts!.cumulative_pd.length - 1];
                return (
                  <tr key={r.id} data-scenario={r.id} className={r.id === sel.scenario ? 'ct-current' : undefined}>
                    <td className="ct-text">{pick(label(r.id), lang)}</td>
                    <td>{w === null ? '-' : pct(w, lang, 0)}</td>
                    <td>
                      <MaybeNumber value={at(r.ts!.months, r.ts!.cumulative_pd, o.horizon.stage1_months)} reason={lang === 'es' ? 'la grilla no tiene ese mes' : 'the grid has no such month'} format={(v) => pct(v, lang)} />
                    </td>
                    <td>{pct(last, lang)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The log-spaced x grid of the SICR lines, with the schedule boundaries on it. */
function sicrGrid(o: C06Outputs): number[] {
  const xs = o.sicr_points.flatMap((p) => [p.pd_origination_annualised, p.pd_current_annualised]);
  const lo = Math.max(1e-4, Math.min(...xs, ...o.settings.sicr.multiplier_schedule.map((m) => m.pd_origination_upper)) / 2);
  const hi = Math.min(1, Math.max(...xs) * 2);
  const grid = Array.from({ length: 41 }, (_, i) => lo * (hi / lo) ** (i / 40));
  const bounds = o.settings.sicr.multiplier_schedule.map((m) => m.pd_origination_upper).filter((b) => b > lo && b < hi);
  return unionX(grid, bounds, bounds.map((b) => b * (1 + 1e-9)), o.sicr_points.map((p) => p.pd_origination_annualised));
}

/** The multiplier of the schedule at an origination PD: the first row whose upper bound holds it, else the last. */
function multiplierAt(o: C06Outputs, pd: number): number {
  const s = o.settings.sicr.multiplier_schedule;
  return (s.find((m) => pd <= m.pd_origination_upper) ?? s[s.length - 1]).multiplier;
}

/** Annualised origination PD against annualised current PD on log axes, with the lines of the rule, points by stage. */
export function SicrView({ sel }: { sel: C06Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const s = o.settings.sicr;
  const grid = sicrGrid(o);
  const stages = ['stage1', 'stage2', 'stage3', 'poci'] as const;
  const used = stages.filter((st) => o.sicr_points.some((p) => p.stage === st));
  const series = [
    { label: { en: 'No change (current = origination)', es: 'Sin cambio (actual = originación)' }, values: grid.map((x) => x), color: '--color-fg-faint' as ShellColorToken, width: 1, dash: [2, 4] },
    { label: { en: 'Multiplier schedule', es: 'Tabla de multiplicadores' }, values: grid.map((x) => multiplierAt(o, x) * x), color: '--color-warn' as ShellColorToken, width: 1.8 },
    { label: { en: 'Absolute floor', es: 'Piso absoluto' }, values: grid.map((x) => x + s.absolute_floor), color: '--color-magenta' as ShellColorToken, width: 1.4, dash: [6, 3] },
    { label: { en: `Threefold backstop (x${s.threefold_ratio})`, es: `Respaldo del triple (x${s.threefold_ratio})` }, values: grid.map((x) => s.threefold_ratio * x), color: '--color-bad' as ShellColorToken, width: 1.8, dash: [8, 3] },
    ...used.map((st) => ({
      label: STAGE_TEXT[st],
      values: grid.map((x) => {
        const p = o.sicr_points.find((q) => q.stage === st && q.pd_origination_annualised === x);
        return p ? p.pd_current_annualised : null;
      }),
      color: STAGE_COLOR[st],
      mode: 'points' as const,
      size: 11,
    })),
  ];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'SICR: annualised PD at origination against now', es: 'SICR: PD anualizada en la originación contra hoy' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: 'Log axes. An account above a line has had its risk rise past that test. Only the 30 dpd and 90 dpd presumptions are IFRS 9; the multiplier schedule and the absolute floor are Contraste policy, and the threefold ratio is an EBA supervisory expectation, not law.',
          es: 'Ejes logarítmicos. Una cuenta sobre una línea ha subido su riesgo más allá de esa prueba. Solo las presunciones de 30 y 90 dpd son de IFRS 9; la tabla de multiplicadores y el piso absoluto son política de Contraste, y el triple es una expectativa supervisora de la EBA, no ley.',
        }}
      >
        <ChartOverTable chartMin="18rem"
          chart={
        <UPlotChart
          height="fill"
          x={{ values: grid, label: { en: 'PD at origination (annualised)', es: 'PD en la originación (anualizada)' }, log: true, format: { percent: true, digits: 2 } }}
          y={{ label: { en: 'PD now (annualised)', es: 'PD hoy (anualizada)' }, log: true, format: { percent: true, digits: 2 } }}
          series={series}
        />
          }
        >
        <div>
          <ul className="ct-evidence" data-table="sicr-rule">
            {s.multiplier_schedule.map((m) => (
              <li key={m.pd_origination_upper} data-multiplier={m.multiplier}>
                {pick({ en: `Origination PD up to ${pct(m.pd_origination_upper, 'en', 2)}: the PD must reach ${m.multiplier} times`, es: `PD de originación hasta ${pct(m.pd_origination_upper, 'es', 2)}: la PD debe llegar a ${m.multiplier} veces` }, lang)}
              </li>
            ))}
            <li data-floor={s.absolute_floor}>{pick({ en: `and rise by at least ${pct(s.absolute_floor, 'en', 2)} in absolute terms`, es: `y subir al menos ${pct(s.absolute_floor, 'es', 2)} en términos absolutos` }, lang)}</li>
            <li data-threefold={s.threefold_ratio}>{pick({ en: `or reach ${s.threefold_ratio} times the origination PD (backstop)`, es: `o llegar a ${s.threefold_ratio} veces la PD de originación (respaldo)` }, lang)}</li>
            <li data-dpd={s.dpd_backstop}>{pick({ en: `${s.dpd_backstop} days past due (presumption) and ${s.default_dpd} (default)`, es: `${s.dpd_backstop} días de mora (presunción) y ${s.default_dpd} (incumplimiento)` }, lang)}</li>
            <li data-lcr={String(s.low_credit_risk_pd)}>
              {s.low_credit_risk_pd === null
                ? pick({ en: 'No low-credit-risk exemption is used.', es: 'No se usa la exención de bajo riesgo de crédito.' }, lang)
                : pick({ en: `Low-credit-risk exemption at an annualised PD of ${pct(s.low_credit_risk_pd, 'en', 2)} or less.`, es: `Exención de bajo riesgo de crédito con PD anualizada de ${pct(s.low_credit_risk_pd, 'es', 2)} o menos.` }, lang)}
            </li>
          </ul>
          <table className="caos-table" data-table="sicr-points">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Account', es: 'Cuenta' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Stage', es: 'Etapa' }, lang)}</th>
                <th>{pick({ en: 'Origination', es: 'Originación' }, lang)}</th>
                <th>{pick({ en: 'Now', es: 'Hoy' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Trigger', es: 'Gatillo' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.sicr_points.map((p) => (
                <tr key={p.account_id} data-account={p.account_id} data-trigger={p.trigger}>
                  <td className="ct-text">{p.account_id}</td>
                  <td className="ct-text">{pick(STAGE_TEXT[p.stage], lang)}</td>
                  <td>{pct(p.pd_origination_annualised, lang, 2)}</td>
                  <td>{pct(p.pd_current_annualised, lang, 2)}</td>
                  <td className="ct-text">{pick(TRIGGER_TEXT[p.trigger] ?? { en: p.trigger, es: p.trigger }, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** PD_PIT(z), the scenario points, and the weighted PD against the PD at the weighted-average factor. */
export function NonLinearityView({ sel }: { sel: C06Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const n = o.non_linearity;
  const zs = n.z_curve.map((p) => p.z);
  const grid = unionX(zs, n.scenario_points.map((p) => p.z));
  const series = [
    { label: { en: 'PD point in time, PD(z)', es: 'PD puntual, PD(z)' }, values: alignTo(zs, n.z_curve.map((p) => p.pd_pit), grid), color: '--color-accent' as ShellColorToken, width: 2.4 },
    {
      label: { en: 'Scenarios', es: 'Escenarios' },
      values: grid.map((z) => n.scenario_points.find((p) => p.z === z)?.pd_pit ?? null),
      color: '--color-fg' as ShellColorToken,
      mode: 'points' as const,
      size: 11,
    },
  ];
  const rows: Array<{ id: string; label: BiText; value: number; format: (v: number) => string }> = [
    { id: 'pd-weighted', label: { en: 'Weighted PD, E[PD(z)]', es: 'PD ponderada, E[PD(z)]' }, value: n.pd_weighted, format: (v) => pct(v, lang, 3) },
    { id: 'pd-at-mean', label: { en: 'PD at the weighted-average factor', es: 'PD en el factor promedio ponderado' }, value: n.pd_at_mean_z, format: (v) => pct(v, lang, 3) },
    { id: 'ecl-weighted', label: { en: 'ECL, weighted scenarios', es: 'PCE, escenarios ponderados' }, value: n.ecl_weighted, format: (v) => money(v, lang, n.currency) },
    { id: 'ecl-mean', label: { en: 'ECL at the mean path', es: 'PCE en la trayectoria media' }, value: n.ecl_at_mean_path, format: (v) => money(v, lang, n.currency) },
    { id: 'index', label: { en: 'Non-linearity index, ECL weighted / ECL at the mean path - 1', es: 'Índice de no linealidad, PCE ponderada / PCE en la trayectoria media - 1' }, value: n.index, format: (v) => pct(v, lang, 2) },
  ];
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={{ en: 'Non-linearity: the PD is convex in the systematic factor', es: 'No linealidad: la PD es convexa en el factor sistemático' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: `One-factor model with PD through the cycle ${pct(n.parameters.pd_ttc, 'en', 2)} and correlation ${pct(n.parameters.rho, 'en', 0)}. The weighted PD sits above the PD at the weighted-average factor (mean z = ${n.mean_z}): averaging the scenarios first would understate the loss.`,
          es: `Modelo de un factor con PD a través del ciclo ${pct(n.parameters.pd_ttc, 'es', 2)} y correlación ${pct(n.parameters.rho, 'es', 0)}. La PD ponderada queda sobre la PD en el factor promedio ponderado (z medio = ${String(n.mean_z).replace('.', ',')}): promediar primero los escenarios subestimaría la pérdida.`,
        }}
      >
        <UPlotChart
          height="fill"
          x={{ values: grid, label: { en: 'Systematic factor z (negative is adverse)', es: 'Factor sistemático z (negativo es adverso)' }, format: { decimals: 1 } }}
          y={{ label: { en: 'Conditional PD', es: 'PD condicional' }, format: { percent: true, digits: 2 } }}
          yMarks={[
            { y: n.pd_weighted, label: { en: 'Weighted PD', es: 'PD ponderada' }, tone: 'warn' },
            { y: n.pd_at_mean_z, label: { en: 'PD at the mean factor', es: 'PD en el factor medio' }, tone: 'neutral' },
          ]}
          series={series}
        />
      </PlotCard>
      <PlotCard fill title={{ en: 'The panel in numbers', es: 'El panel en números' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <div className="ct-scroll">
          <table className="caos-table" data-table="non-linearity">
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} data-row={r.id}>
                  <td className="ct-text">{pick(r.label, lang)}</td>
                  <td>{r.format(r.value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="caos-table" data-table="scenario-points">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Scenario', es: 'Escenario' }, lang)}</th>
                <th>z</th>
                <th>{pick({ en: 'Weight', es: 'Peso' }, lang)}</th>
                <th>PD(z)</th>
              </tr>
            </thead>
            <tbody>
              {n.scenario_points.map((p) => (
                <tr key={p.scenario_id} data-scenario={p.scenario_id}>
                  <td className="ct-text">{pick(o.scenarios.find((s) => s.id === p.scenario_id)?.label ?? { en: p.scenario_id, es: p.scenario_id }, lang)}</td>
                  <td>{pick({ en: String(p.z), es: String(p.z).replace('.', ',') }, lang)}</td>
                  <td>{pct(p.weight, lang, 0)}</td>
                  <td>{pct(p.pd_pit, lang, 3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}
