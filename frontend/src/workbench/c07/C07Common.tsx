// C07's Findings, Variants and Context groups, and the live read-outs of its rail (ADR-0017 rule 3: every section shows
// a value that moves with its controls).
import { BarChart, Callout, PlotCard, Readout, ViewsRow, formatNumber, pick, useShellLang, useWorkbenchState } from '@fasl-work/caos-app-shell';
import { loadAllVariants, useArtifact } from '../../api/artifacts';
import type { VariantArtifact } from '../../lib/contract.types';
import { FindingsCard, FixtureNotice } from '../c06/C06Common';
import { ChartOverTable, compactMoney, money } from '../c06/format';
import { CalibrationView, TestsView } from './ValidationViews';
import { REPLAY, provenanceOf } from '../model';
import { Pending } from '../Pending';
import { truthStatusText } from '../c05/selection';
import { componentLabel, fitOf, liveIfrs9, outputsOf, type C07Outputs, type C07Sel } from './selection';

const LIVE = 'live' as const;

export function C07FindingsView({ sel }: { sel: C07Sel | null }) {
  if (!sel) return <Pending />;
  return (
    <ViewsRow>
      <FindingsCard variant={sel.data.variant} />
    </ViewsRow>
  );
}

/** The scenario variants side by side: the three totals and the change against the base that the document carries. */
export function C07VariantsTable({ variants, onPick, current }: { variants: Array<{ id: string; title: { en: string; es: string }; v: VariantArtifact<C07Outputs> }>; onPick: (id: string) => void; current: string }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const first = variants[0]?.v;
  return (
    <PlotCard
      fill
      title={{ en: 'The scenarios', es: 'Los escenarios' }}
      lane={REPLAY}
      provenance={provenanceOf(first?.provenance.truth_status)}
      dataKey={stateKey}
      note={{ en: 'The total provision of each regime under each scenario; the IFRS 9 column is the probability-weighted measure. The base scenario has no change to report. Pick a scenario to load it.', es: 'La provisión total de cada régimen bajo cada escenario; la columna IFRS 9 es la medida ponderada por probabilidad. El escenario base no tiene cambio que informar. Elija un escenario para cargarlo.' }}
    >
      <ChartOverTable
        chart={
          <BarChart
            title={{ en: 'IFRS 9 total by scenario (probability-weighted)', es: 'Total IFRS 9 por escenario (ponderada por probabilidad)' }}
            height="fill"
            orientation="vertical"
            data={variants.map(({ id, title, v }) => ({ id, label: title, value: ((v.outputs.regimes.find((r) => r.regime === 'ifrs9')?.total_provision) ?? null) === null ? null : (v.outputs.regimes.find((r) => r.regime === 'ifrs9')!.total_provision / 1e9), tone: 'warn' as const, highlight: id === current }))}
            axis={{ label: { en: `IFRS 9 total (bn ${first?.outputs.currency ?? ''})`, es: `Total IFRS 9 (mil M ${first?.outputs.currency ?? ''})` }, format: { digits: 3 } }}
          />
        }
      >
        <table className="caos-table ct-wrap-head" data-table="variants-c07">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Scenario', es: 'Escenario' }, lang)}</th>
              <th>CMF B-1</th>
              <th>{pick({ en: 'IFRS 9 (weighted)', es: 'IFRS 9 (ponderada)' }, lang)}</th>
              <th>{pick({ en: 'BdE Annex 9', es: 'Anexo 9 del BdE' }, lang)}</th>
              <th className="ct-wide-only">{pick({ en: 'IFRS 9 change vs base', es: 'Cambio IFRS 9 vs base' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {variants.map(({ id, title, v }) => {
              const o = v.outputs;
              const total = (r: string) => o.regimes.find((x) => x.regime === r)?.total_provision ?? null;
              return (
                <tr key={id} data-variant={id} className={id === current ? 'ct-current' : undefined}>
                  <td className="ct-text">
                    <button type="button" className="ct-linkbutton" onClick={() => onPick(id)}>{pick(title, lang)}</button>
                  </td>
                  <td>{money(total('cmf-b1'), lang, o.currency)}</td>
                  <td>{money(total('ifrs9'), lang, o.currency)}</td>
                  <td>{money(total('bde-annex9'), lang, o.currency)}</td>
                  <td className="ct-wide-only">{o.delta_vs_base ? money(o.delta_vs_base.ifrs9_delta, lang, o.delta_vs_base.currency) : formatNone(lang)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </ChartOverTable>
    </PlotCard>
  );
}

const formatNone = (lang: 'en' | 'es') => (lang === 'es' ? 'sin cambio (base)' : 'none (base)');

export function C07VariantsView({ sel, onPick }: { sel: C07Sel | null; onPick: (id: string) => void }) {
  const manifest = sel?.data.manifest;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  if (!sel || all.state !== 'ready') return <Pending />;
  const entries = sel.data.manifest.artifacts.filter((a) => a.role === 'variant');
  const variants = (all.data as unknown as Array<VariantArtifact<C07Outputs>>)
    .filter((v) => v.outputs.kind === 'three-regime')
    .map((v) => ({ id: v.variant_id, title: entries.find((e) => e.variant_id === v.variant_id)?.short_title ?? { en: v.variant_id, es: v.variant_id }, v }));
  return (
    <ViewsRow>
      <C07VariantsTable variants={variants} onPick={onPick} current={sel.data.variant.variant_id} />
    </ViewsRow>
  );
}

/** The case, the synthetic bank, what each regime is, and the statement that nothing here is about a real bank. */
export function C07ContextView({ sel }: { sel: C07Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const m = sel.data.manifest;
  const v = sel.data.variant;
  const prov = provenanceOf(v.provenance.truth_status);
  const fit = fitOf(sel);
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard title={{ en: 'The case', es: 'El caso' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <FixtureNotice variant={v} />
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        <Callout variant="honest" title={pick({ en: 'Synthetic, and a comparison', es: 'Sintético, y una comparación' }, lang)}>
          <span data-notice="true">{pick(o.notice, lang)}</span>
        </Callout>
        <dl className="ct-defs" data-table="c07-context">
          <dt>{pick({ en: 'Bank', es: 'Banco' }, lang)}</dt>
          <dd data-bank={fit?.bank.name ?? ''}>{fit ? `${fit.bank.name} (${pick({ en: 'synthetic', es: 'sintético' }, lang)})` : pick({ en: 'Not available: the models artifact carries no bank.', es: 'No disponible: el artefacto de modelos no trae el banco.' }, lang)}</dd>
          <dt>{pick({ en: 'Truth status of this variant', es: 'Estado de verdad de esta variante' }, lang)}</dt>
          <dd>{pick(truthStatusText(v.provenance.truth_status), lang)}</dd>
          <dt>CMF B-1</dt>
          <dd>{pick({ en: 'The statutory provision on loans in Chile: IFRS 9 5.5 is carved out for loans in the CMF compendium.', es: 'La provisión estatutaria sobre créditos en Chile: IFRS 9 5.5 está excluida para créditos en el compendio de la CMF.' }, lang)}</dd>
          <dt>IFRS 9</dt>
          <dd>{pick({ en: 'A comparison measure: the probability-weighted ECL of the same portfolio, not what Chilean banks book on loans.', es: 'Una medida de comparación: la PCE ponderada por probabilidad de la misma cartera, no lo que los bancos chilenos constituyen sobre los créditos.' }, lang)}</dd>
          <dt>{pick({ en: 'BdE Annex 9', es: 'Anexo 9 del BdE' }, lang)}</dt>
          <dd>{pick({ en: 'Spanish GAAP, the alternative solutions, aligned with IFRS 9.', es: 'PGC español, las soluciones alternativas, alineadas con IFRS 9.' }, lang)}</dd>
        </dl>
      </PlotCard>
      <PlotCard title={{ en: 'The portfolio', es: 'La cartera' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <div className="ct-scroll">
          <table className="caos-table ct-wrap-head" data-table="portfolio">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Segment', es: 'Segmento' }, lang)}</th>
                <th>{pick({ en: 'Accounts', es: 'Cuentas' }, lang)}</th>
                <th>{`${pick({ en: 'Gross exposure', es: 'Exposición bruta' }, lang)} (${o.portfolio.currency})`}</th>
              </tr>
            </thead>
            <tbody>
              {o.portfolio.segments.map((s) => (
                <tr key={s.segment_id} data-segment={s.segment_id}>
                  <td className="ct-text">{pick(s.label, lang)}</td>
                  <td>{money(s.accounts, lang, 'CLP')}</td>
                  <td>{money(s.gross_exposure, lang, o.portfolio.currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
      <CalibrationView sel={sel} />
      <TestsView sel={sel} />
    </div>
  );
}

/** The live read-out of the Weight section: the weighted model ECL at the rail's weights, and the IFRS 9 total with the overlays. */
export function Ifrs9Readout({ sel }: { sel: C07Sel | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  const prov = provenanceOf(sel?.data.variant.provenance.truth_status);
  const title = { en: 'IFRS 9 at this weight', es: 'IFRS 9 con este peso' };
  if (!sel || !o) return <Readout title={title} lane={LIVE} provenance={prov} dataKey={stateKey} items={[]} />;
  const amount = (v: number | null | undefined) => compactMoney(v, o.currency);
  const live = liveIfrs9(sel);
  const name = componentLabel(sel, sel.scenario);
  return (
    <Readout
      title={title}
      lane={LIVE}
      provenance={prov}
      dataKey={stateKey}
      items={[
        { label: { en: 'Weighted ECL', es: 'PCE ponderada' }, ...amount(live), hint: { en: `Sum of weight times the ECL of each component, with ${name.en} at ${formatNumber(sel.weight, 'en', { percent: true, decimals: 1 })} and the others in their ratios; overlays excluded. 100% on one scenario is a sensitivity, never the IFRS 9 measure.`, es: `Suma del peso por la PCE de cada componente, con ${name.es} en ${formatNumber(sel.weight, 'es', { percent: true, decimals: 1 })} y los otros en sus proporciones; sin ajustes. 100% en un escenario es una sensibilidad, nunca la medida IFRS 9.` } },
        { label: { en: 'IFRS 9 total', es: 'Total IFRS 9' }, ...amount(live + o.ifrs9_detail.overlays_total), hint: { en: 'The weighted model ECL plus the overlays, which are kept apart from the model.', es: 'La PCE ponderada del modelo más los ajustes, que se mantienen aparte del modelo.' } },
      ]}
    />
  );
}

/** The live read-out of the Scenario section: what the document says of the weighted scenario in focus. */
export function ScenarioReadout({ sel }: { sel: C07Sel | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  const prov = provenanceOf(sel?.data.variant.provenance.truth_status);
  const title = { en: 'Scenario in the document', es: 'Escenario en el documento' };
  const c = o?.ifrs9_detail.weighted_components.find((x) => x.scenario_id === sel?.scenario) ?? null;
  const amount = (v: number | null | undefined) => compactMoney(v, o?.currency ?? '');
  return (
    <Readout
      title={title}
      lane={LIVE}
      provenance={prov}
      dataKey={stateKey}
      items={[
        { label: { en: 'Scenario weight', es: 'Peso del escenario' }, value: c?.weight ?? null, unitless: true, format: { percent: true, decimals: 1 } },
        { label: { en: 'Factor z', es: 'Factor z' }, value: c?.z ?? null, unitless: true, format: { digits: 3 }, hint: { en: 'The systemic factor the scenario sets, in standard deviations.', es: 'El factor sistémico que fija el escenario, en desviaciones estándar.' } },
        { label: { en: 'ECL, alone', es: 'PCE, sola' }, ...amount(c?.single_scenario_ecl ?? null), hint: { en: 'The ECL if this scenario had all the weight: a sensitivity, never the measure.', es: 'La PCE si este escenario tuviera todo el peso: una sensibilidad, nunca la medida.' } },
      ]}
    />
  );
}

/** The live read-out of the Regimes section: the total and the coverage of the regime in focus. */
export function RegimeReadout({ sel }: { sel: C07Sel | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  const prov = provenanceOf(sel?.data.variant.provenance.truth_status);
  const title = { en: 'Regime in focus', es: 'Régimen en foco' };
  const r = o?.regimes.find((x) => x.regime === sel?.regime) ?? null;
  const amount = (v: number | null | undefined) => compactMoney(v, o?.currency ?? '');
  return (
    <Readout
      title={title}
      lane={LIVE}
      provenance={prov}
      dataKey={stateKey}
      items={[
        { label: { en: 'Total provision', es: 'Provisión total' }, ...amount(r?.total_provision ?? null), hint: r ? { en: r.label.en, es: r.label.es } : undefined },
        { label: { en: 'Coverage', es: 'Cobertura' }, value: r?.coverage_rate ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'The total provision over the gross exposure it is measured on.', es: 'La provisión total sobre la exposición bruta en que se mide.' } },
      ]}
    />
  );
}

/** The live read-out of the Segment section: the three provisions of the chosen segment and the gap of IFRS 9 to B-1. */
export function GapReadout({ sel }: { sel: C07Sel | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  const prov = provenanceOf(sel?.data.variant.provenance.truth_status);
  const title = { en: 'Segment provisions', es: 'Provisiones del segmento' };
  const row = o?.comparison.rows.find((r) => r.segment_id === sel?.segment) ?? null;
  const amount = (v: number | null | undefined) => compactMoney(v, o?.currency ?? '');
  return (
    <Readout
      title={title}
      lane={LIVE}
      provenance={prov}
      dataKey={stateKey}
      items={[
        { label: { en: 'CMF B-1', es: 'CMF B-1' }, ...amount(row?.cmf_b1_provision ?? null) },
        { label: { en: 'IFRS 9', es: 'IFRS 9' }, hint: { en: 'The probability-weighted measure.', es: 'La medida ponderada por probabilidad.' }, ...amount(row?.ifrs9_provision ?? null) },
        { label: { en: 'BdE 9', es: 'BdE 9' }, ...amount(row?.bde_annex9_provision ?? null) },
        { label: { en: 'IFRS 9 - B-1', es: 'IFRS 9 - B-1' }, hint: { en: 'The gap of the IFRS 9 measure to B-1; the gap of BdE to B-1 is in the Segments view.', es: 'La brecha de la medida IFRS 9 a B-1; la brecha de BdE a B-1 está en la vista de segmentos.' }, ...amount(row?.gap_ifrs9_minus_b1 ?? null) },
      ]}
    />
  );
}

/** The live read-out of the B-1 section: the booked total at the additional provisions tried, and the minimum check. */
export function B1Readout({ sel }: { sel: C07Sel | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  const prov = provenanceOf(sel?.data.variant.provenance.truth_status);
  const title = { en: 'B-1 booked total', es: 'Total constituido B-1' };
  if (!sel || !o) return <Readout title={title} lane={LIVE} provenance={prov} dataKey={stateKey} items={[]} />;
  const d = o.b1_detail;
  const comparable = o.regimes.find((r) => r.regime === 'cmf-b1')?.total_provision ?? 0;
  const additional = sel.additional ?? d.additional_provisions.amount;
  const amount = (v: number | null | undefined) => compactMoney(v, o.currency);
  return (
    <Readout
      title={title}
      lane={LIVE}
      provenance={prov}
      dataKey={stateKey}
      items={[
        { label: { en: 'Comparable total', es: 'Total comparable' }, ...amount(comparable), hint: { en: 'Group, individual and the minimum top-up: what the regimes are compared on.', es: 'Grupal, individual y el complemento del mínimo: lo que se compara entre regímenes.' } },
        { label: { en: 'Booked total', es: 'Total constituido' }, ...amount(comparable + additional), hint: { en: 'The comparable total plus the additional provisions tried above.', es: 'El total comparable más las provisiones adicionales probadas arriba.' } },
        { label: { en: 'Minimum top-up', es: 'Compl. del mínimo' }, ...amount(d.minimum_check.top_up) },
        { label: { en: 'Minimum rate', es: 'Tasa mínima' }, value: d.minimum_check.minimum_rate, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'The minimum rate on the normal portfolio.', es: 'La tasa mínima sobre la cartera normal.' } },
      ]}
    />
  );
}
