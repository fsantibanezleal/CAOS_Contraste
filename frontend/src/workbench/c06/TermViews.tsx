// C06's Model group views on the PD side: the term structures per scenario with the origination forward curve of the
// selected account, the SICR scatter with the multiplier, floor and threefold lines, and the non-linearity panel.
// Each draws what the c06-outputs document carries; the lines of the SICR rule are drawn from the document's own
// `settings.sicr`, never from constants of this file.
import { PlotCard, ViewsRow, formatNumber, pick, useShellLang, useWorkbenchState, type BiText, type ShellColorToken } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { provenanceOf, REPLAY } from '../model';
import { Pending } from '../Pending';
import { ChartOverTable, STAGE_COLOR, STAGE_TEXT, alignTo, money, pct, unionX, MaybeNumber, segmentLabel } from './format';
import { outputsOf, type C06Outputs, type C06Sel } from './selection';
import { PCT_AXIS } from './ValidationViews';

const WEIGHTED: BiText = { en: 'Probability-weighted', es: 'Ponderada por probabilidad' };
const SCENARIO_COLORS: ShellColorToken[] = ['--color-accent', '--color-magenta', '--color-warn', '--color-good'];

const TRIGGER_TEXT: Record<string, BiText> = {
  none: { en: 'none', es: 'ninguno' },
  'relative-absolute': { en: 'multiplier and floor', es: 'multiplicador y piso' },
  threefold: { en: 'threefold', es: 'triple' },
  'dpd-backstop': { en: '30 days past due backstop', es: 'respaldo de 30 días de mora' },
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
          es: 'h(t) es la PD condicional de un período dada la supervivencia, q(t) = S(t-1) h(t) su PD incondicional (marginal) y F(t) la suma de q: el documento nombra ambas. La curva ponderada es la PD ponderada por probabilidad; el par discontinuo es la cuenta elegida, su curva de originación contra la actual en la misma ventana restante.',
        }}
      >
        <ChartOverTable chartMin="18rem"
          chart={
        <UPlotChart
          height="fill"
          x={{ values: grid, label: { en: 'Months after the reporting date', es: 'Meses desde la fecha de reporte' }, format: { decimals: 0 } }}
          y={{ label: m.label, format: PCT_AXIS }}
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

/**
 * The note of the non-linearity panel, each comparison stated as the committed numbers give it (R3 c07 B1: at Dec 2010 the index is
 * -0.07 % and the note said averaging first would understate the loss). The PD comparison reads the two PDs; the loss conclusion
 * reads the sign of the ECL index (ECL weighted over ECL at the mean path, minus 1).
 */
export function nonLinearityNote(n: C06Outputs['non_linearity']): BiText {
  const mz = (lang: 'en' | 'es') => formatNumber(n.mean_z, lang, { decimals: 2 });
  const pdSide: BiText = n.pd_weighted >= n.pd_at_mean_z
    ? { en: 'The weighted PD sits above the PD at the weighted-average factor', es: 'La PD ponderada queda sobre la PD en el factor promedio ponderado' }
    : { en: 'The weighted PD sits below the PD at the weighted-average factor', es: 'La PD ponderada queda bajo la PD en el factor promedio ponderado' };
  const idx = (lang: 'en' | 'es') => pct(n.index, lang, 2);
  const loss: BiText = n.index >= 0
    ? { en: `The ECL index is ${idx('en')}: averaging the scenarios first would understate the loss.`, es: `El índice de la PCE es ${idx('es')}: promediar primero los escenarios subestimaría la pérdida.` }
    : {
        en: `The ECL index is ${idx('en')}: the weighted ECL is below the ECL at the mean path, because the loss of a path is not its PD alone, so here averaging the scenarios first would overstate the loss.`,
        es: `El índice de la PCE es ${idx('es')}: la PCE ponderada queda bajo la PCE en la trayectoria media, porque la pérdida de una trayectoria no es solo su PD, así que aquí promediar primero los escenarios sobrestimaría la pérdida.`,
      };
  return {
    en: `One-factor model with PD through the cycle ${pct(n.parameters.pd_ttc, 'en', 2)} and correlation ${pct(n.parameters.rho, 'en', 0)}. ${pdSide.en} (mean z = ${mz('en')}). ${loss.en}`,
    es: `Modelo de un factor con PD a través del ciclo ${pct(n.parameters.pd_ttc, 'es', 2)} y correlación ${pct(n.parameters.rho, 'es', 0)}. ${pdSide.es} (z medio = ${mz('es')}). ${loss.es}`,
  };
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
  // a PD above 100% cannot be reached: a line of the rule is drawn only where it can be crossed, so the axis does not run to 1,000%
  const reachable = (v: number): number | null => (v > 1 ? null : v);
  const series = [
    { label: { en: 'No change (current = origination)', es: 'Sin cambio (actual = originación)' }, values: grid.map((x) => x), color: '--color-fg-faint' as ShellColorToken, width: 1, dash: [2, 4] },
    // the schedule in the subtle ink, apart from the Stage 2 points (warn; R3 c07 m2)
    { label: { en: 'Multiplier schedule', es: 'Tabla de multiplicadores' }, values: grid.map((x) => reachable(multiplierAt(o, x) * x)), color: '--color-fg-subtle' as ShellColorToken, width: 1.8 },
    { label: { en: 'Absolute floor', es: 'Piso absoluto' }, values: grid.map((x) => reachable(x + s.absolute_floor)), color: '--color-magenta' as ShellColorToken, width: 1.4, dash: [6, 3] },
    { label: { en: `Threefold backstop (x${s.threefold_ratio})`, es: `Respaldo del triple (x${s.threefold_ratio})` }, values: grid.map((x) => reachable(s.threefold_ratio * x)), color: '--color-bad' as ShellColorToken, width: 1.8, dash: [8, 3] },
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
  // the sampled accounts (400) are drawn; the table counts them by stage and trigger, so the card reads whole at 1280 and a phone page
  // is not 22,500 px of rows (R2b c07, the ruling of 2026-10-24 on long tables); one account is read on the chart or in the rail
  const groups = [...new Set(o.sicr_points.map((p) => `${p.stage}|${p.trigger}`))]
    .map((k) => {
      const [stage, trigger] = k.split('|');
      return { stage, trigger, n: o.sicr_points.filter((p) => p.stage === stage && p.trigger === trigger).length };
    })
    .sort((a, b) => stages.indexOf(a.stage as (typeof stages)[number]) - stages.indexOf(b.stage as (typeof stages)[number]) || b.n - a.n);
  const total = o.sicr_points.length;
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={{ en: 'SICR: annualised PD at origination against now', es: 'SICR: PD anualizada en la originación contra hoy' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: 'Log axes. An account above a line has had its risk rise past that test. Only the presumptions at 30 and 90 days past due are IFRS 9; the multiplier schedule and the absolute floor are Contraste policy, and the threefold ratio is an EBA supervisory expectation, not law.',
          es: 'Ejes logarítmicos. Una cuenta sobre una línea ha subido su riesgo más allá de esa prueba. Solo las presunciones a 30 y 90 días de mora son de IFRS 9; la tabla de multiplicadores y el piso absoluto son política de Contraste, y el triple es una expectativa supervisora de la EBA, no ley.',
        }}
      >
        <UPlotChart
          height="fill"
          x={{ values: grid, label: { en: 'PD at origination (annualised)', es: 'PD en la originación (anualizada)' }, log: true, format: { percent: true, digits: 2 } }}
          y={{ label: { en: 'PD now (annualised)', es: 'PD hoy (anualizada)' }, log: true, format: { percent: true, digits: 2 } }}
          series={series}
        />
      </PlotCard>
      <PlotCard fill title={{ en: 'The rule and the accounts', es: 'La regla y las cuentas' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <div className="ct-scroll" data-caos-flow="">
          {/* the counts first, so they show at 1280 above the rule (R3 c07 m3) */}
          <p className="ct-note" data-accounts={total}>
            {pick(
              {
                en: `${formatNumber(total, 'en', { decimals: 0 })} sampled accounts are drawn; the table counts them by stage and trigger. Point at an account on the chart to read it, or pick one in the rail's Account section.`,
                es: `Se dibujan ${formatNumber(total, 'es', { decimals: 0 })} cuentas muestreadas; la tabla las cuenta por etapa y gatillo. Apunte a una cuenta en el gráfico para leerla, o elija una en la sección Cuenta del panel.`,
              },
              lang,
            )}
          </p>
          <table className="caos-table ct-wrap-head" data-table="sicr-summary">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Stage', es: 'Etapa' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Trigger', es: 'Gatillo' }, lang)}</th>
                <th>{pick({ en: 'Accounts', es: 'Cuentas' }, lang)}</th>
                <th>{pick({ en: 'Share', es: 'Parte' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {groups.map((g) => (
                <tr key={`${g.stage}-${g.trigger}`} data-stage={g.stage} data-trigger={g.trigger}>
                  <td className="ct-text">{pick(STAGE_TEXT[g.stage] ?? { en: g.stage, es: g.stage }, lang)}</td>
                  <td className="ct-text">{pick(TRIGGER_TEXT[g.trigger] ?? { en: g.trigger, es: g.trigger }, lang)}</td>
                  <td>{formatNumber(g.n, lang, { decimals: 0 })}</td>
                  <td>{pct(g.n / total, lang, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {/* the rule as a table of test and condition: with the counts below, the card's tables span it, so the gate counts
              the card as drawn at 1280 (a list above one small table drew on 23% of its stage, G6) */}
          <table className="caos-table ct-wrap-head" data-table="sicr-rule">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Test', es: 'Prueba' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Condition', es: 'Condición' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {s.multiplier_schedule.map((m) => (
                <tr key={m.pd_origination_upper} data-multiplier={m.multiplier}>
                  <td className="ct-text">{pick({ en: `Origination PD up to ${pct(m.pd_origination_upper, 'en', 2)}`, es: `PD de originación hasta ${pct(m.pd_origination_upper, 'es', 2)}` }, lang)}</td>
                  <td className="ct-text">{pick({ en: `the PD must reach ${formatNumber(m.multiplier, 'en', { decimals: 1 })} times`, es: `la PD debe llegar a ${formatNumber(m.multiplier, 'es', { decimals: 1 })} veces` }, lang)}</td>
                </tr>
              ))}
              <tr data-floor={s.absolute_floor}>
                <td className="ct-text">{pick({ en: 'Absolute floor', es: 'Piso absoluto' }, lang)}</td>
                <td className="ct-text">{pick({ en: `and rise by at least ${pct(s.absolute_floor, 'en', 2)} in absolute terms`, es: `y subir al menos ${pct(s.absolute_floor, 'es', 2)} en términos absolutos` }, lang)}</td>
              </tr>
              <tr data-threefold={s.threefold_ratio}>
                <td className="ct-text">{pick({ en: 'Threefold backstop', es: 'Respaldo del triple' }, lang)}</td>
                <td className="ct-text">{pick({ en: `or reach ${formatNumber(s.threefold_ratio, 'en', { decimals: 1 })} times the origination PD`, es: `o llegar a ${formatNumber(s.threefold_ratio, 'es', { decimals: 1 })} veces la PD de originación` }, lang)}</td>
              </tr>
              <tr data-dpd={s.dpd_backstop}>
                <td className="ct-text">{pick({ en: 'Days past due', es: 'Días de mora' }, lang)}</td>
                <td className="ct-text">{pick({ en: `${s.dpd_backstop} (presumption) and ${s.default_dpd} (default)`, es: `${s.dpd_backstop} (presunción) y ${s.default_dpd} (incumplimiento)` }, lang)}</td>
              </tr>
              <tr data-lcr={String(s.low_credit_risk_pd)}>
                <td className="ct-text">{pick({ en: 'Low-credit-risk exemption', es: 'Exención de bajo riesgo de crédito' }, lang)}</td>
                <td className="ct-text">
                  {s.low_credit_risk_pd === null
                    ? pick({ en: 'not used', es: 'no se usa' }, lang)
                    : pick({ en: `at an annualised PD of ${pct(s.low_credit_risk_pd, 'en', 2)} or less`, es: `con PD anualizada de ${pct(s.low_credit_risk_pd, 'es', 2)} o menos` }, lang)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
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
    { id: 'ecl-weighted', label: { en: `ECL, weighted scenarios (${n.currency})`, es: `PCE, escenarios ponderados (${n.currency})` }, value: n.ecl_weighted, format: (v) => money(v, lang, n.currency) },
    { id: 'ecl-mean', label: { en: `ECL at the mean path (${n.currency})`, es: `PCE en la trayectoria media (${n.currency})` }, value: n.ecl_at_mean_path, format: (v) => money(v, lang, n.currency) },
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
        note={nonLinearityNote(n)}
      >
        <UPlotChart
          height="fill"
          x={{ values: grid, label: { en: 'Systematic factor z (negative is adverse)', es: 'Factor sistemático z (negativo es adverso)' }, format: { decimals: 1 } }}
          y={{ label: { en: 'Conditional PD', es: 'PD condicional' }, format: PCT_AXIS }}
          yMarks={[
            { y: n.pd_weighted, label: { en: 'Weighted PD', es: 'PD ponderada' }, tone: 'warn' },
            { y: n.pd_at_mean_z, label: { en: 'PD at the mean factor', es: 'PD en el factor medio' }, tone: 'neutral' },
          ]}
          series={series}
        />
      </PlotCard>
      <PlotCard fill title={{ en: 'The panel in numbers', es: 'El panel en números' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <div className="ct-scroll" data-caos-flow="">
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
                  <td>{formatNumber(p.z, lang, { decimals: 2 })}</td>
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
