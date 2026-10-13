// C06's Findings, Variants and Context groups, and the live read-outs of its rail (ADR-0017 rule 3: every section shows
// a value that moves with its controls). The Findings card and the fixture notice are shared with C07.
import { BarChart, Callout, PlotCard, Readout, ViewsRow, pick, useShellLang, useWorkbenchState, type BiText } from '@fasl-work/caos-app-shell';
import { loadAllVariants, useArtifact } from '../../api/artifacts';
import type { Finding, VariantArtifact } from '../../lib/contract.types';
import { REPLAY, provenanceOf } from '../model';
import { Pending } from '../Pending';
import { ChartOverTable, compactMoney, money, pct } from './format';
import { IdentitiesView, TestRowsCard } from './ValidationViews';
import { fitOf, liveEcl, nearestPoint, outputsOf, rescaled, type C06Outputs, type C06Sel } from './selection';

const LIVE = 'live' as const;

const SEVERITY_TEXT: Record<string, BiText> = {
  S1: { en: 'S1 critical', es: 'S1 crítico' },
  S2: { en: 'S2 significant', es: 'S2 significativo' },
  S3: { en: 'S3 moderate', es: 'S3 moderado' },
  S4: { en: 'S4 minor', es: 'S4 menor' },
};
const STATUS_TEXT: Record<string, BiText> = {
  open: { en: 'open', es: 'abierto' },
  accepted: { en: 'accepted (a stated limit)', es: 'aceptado (un límite declarado)' },
  closed: { en: 'closed', es: 'cerrado' },
};

/** True when the document says it stands on a fixture: its inputs carry the class `fixture` (a contract example, not a result). */
export function isFixture(v: VariantArtifact): boolean {
  return v.provenance.inputs.some((i) => i.class === 'fixture');
}

/** The notice of a document that is a fixture: said at the top of the Context and the Findings, never a result. */
export function FixtureNotice({ variant }: { variant: VariantArtifact }) {
  const lang = useShellLang();
  if (!isFixture(variant)) return null;
  return (
    <Callout variant="honest" title={pick({ en: 'A fixture, not a result', es: 'Un ejemplo, no un resultado' }, lang)}>
      <span data-fixture="true">
        {pick(
          {
            en: 'The numbers on this view come from the contract fixture: a few round-number accounts that exercise every field. They are not a measurement and say nothing about a portfolio or a bank. The real bake replaces them.',
            es: 'Los números de esta vista vienen del ejemplo del contrato: unas pocas cuentas de números redondos que ejercitan cada campo. No son una medición y no dicen nada de una cartera ni de un banco. La corrida real los reemplaza.',
          },
          lang,
        )}
      </span>
    </Callout>
  );
}

/** What the validation found, with the evidence each finding cites; an empty list is said, not drawn as an empty table. */
export function FindingsCard({ variant }: { variant: VariantArtifact }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const order = ['S1', 'S2', 'S3', 'S4'];
  const findings: Finding[] = [...variant.findings].sort((a, b) => order.indexOf(a.severity) - order.indexOf(b.severity));
  return (
    <PlotCard
      fill
      title={{ en: 'What the validation found', es: 'Lo que encontró la validación' }}
      lane={REPLAY}
      provenance={provenanceOf(variant.provenance.truth_status)}
      dataKey={stateKey}
      note={{ en: 'Each finding cites the tests behind it or a stated design limit.', es: 'Cada hallazgo cita las pruebas que lo respaldan o un límite de diseño declarado.' }}
    >
      <FixtureNotice variant={variant} />
      {findings.length === 0 ? (
        <p className="ct-note" data-state="unavailable">
          {pick({ en: 'No finding is recorded in this variant.', es: 'Esta variante no registra hallazgos.' }, lang)}
        </p>
      ) : (
        <div className="ct-scroll">
          <table className="caos-table" data-table="findings">
            <thead>
              <tr>
                <th>{pick({ en: 'Severity', es: 'Severidad' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Finding', es: 'Hallazgo' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Status', es: 'Estado' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {findings.map((f) => (
                <tr key={f.id} data-finding={f.id}>
                  <td>{pick(SEVERITY_TEXT[f.severity], lang)}</td>
                  <td className="ct-text">
                    {pick(f.title, lang)}
                    <ul className="ct-evidence">
                      {f.evidence.map((e) => (
                        <li key={e}>{e.startsWith('design:') ? `${pick({ en: 'Design limit: ', es: 'Límite de diseño: ' }, lang)}${e.slice(7)}` : e}</li>
                      ))}
                    </ul>
                  </td>
                  <td className="ct-wide-only">{pick(STATUS_TEXT[f.status], lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PlotCard>
  );
}

export function C06FindingsView({ sel }: { sel: C06Sel | null }) {
  if (!sel) return <Pending />;
  return (
    <ViewsRow>
      <FindingsCard variant={sel.data.variant} />
    </ViewsRow>
  );
}

/** The variants side by side (one reporting date each): their model ECL by stage, overlays apart; pick one to load it. */
export function C06VariantsTable({ variants, onPick, current }: { variants: Array<{ id: string; title: BiText; v: VariantArtifact<C06Outputs> }>; onPick: (id: string) => void; current: string }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const first = variants[0]?.v;
  return (
    <PlotCard
      fill
      title={{ en: 'The reporting dates', es: 'Las fechas de reporte' }}
      lane={REPLAY}
      provenance={provenanceOf(first?.provenance.truth_status)}
      dataKey={stateKey}
      note={{ en: 'The model ECL by stage of each reporting date, and the overlays apart from it. Pick a date to load it.', es: 'La PCE del modelo por etapa de cada fecha de reporte, y los ajustes aparte. Elija una fecha para cargarla.' }}
    >
      <ChartOverTable
        chart={
          <BarChart
            title={{ en: 'Model ECL by reporting date', es: 'PCE del modelo por fecha de reporte' }}
            height="fill"
            orientation="vertical"
            data={variants.map(({ id, title, v }) => ({ id, label: title, value: v.outputs.stage_summary.rows.reduce((a, r) => a + r.ecl, 0), tone: 'accent' as const, highlight: id === current }))}
            axis={{ label: { en: `Model ECL (${first?.outputs.currency ?? ''})`, es: `PCE del modelo (${first?.outputs.currency ?? ''})` }, format: { digits: 3 } }}
          />
        }
      >
        <table className="caos-table ct-wrap-head" data-table="variants-c06">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Variant', es: 'Variante' }, lang)}</th>
              <th className="ct-text">{pick({ en: 'Reporting date', es: 'Fecha de reporte' }, lang)}</th>
              <th className="ct-text ct-wide-only">{pick({ en: 'Data', es: 'Datos' }, lang)}</th>
              <th>{pick({ en: 'ECL Stage 1', es: 'PCE Etapa 1' }, lang)}</th>
              <th>{pick({ en: 'ECL Stage 2', es: 'PCE Etapa 2' }, lang)}</th>
              <th>{pick({ en: 'ECL Stage 3', es: 'PCE Etapa 3' }, lang)}</th>
              <th>{pick({ en: 'Overlays', es: 'Ajustes' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {variants.map(({ id, title, v }) => {
              const o = v.outputs;
              const ecl = (st: string) => o.stage_summary.rows.find((r) => r.stage === st)?.ecl ?? null;
              return (
                <tr key={id} data-variant={id} className={id === current ? 'ct-current' : undefined}>
                  <td className="ct-text">
                    <button type="button" className="ct-linkbutton" onClick={() => onPick(id)}>{pick(title, lang)}</button>
                  </td>
                  <td className="ct-text">{o.reporting_date}</td>
                  <td className="ct-text ct-wide-only">{o.data_status.primary_source}</td>
                  <td>{money(ecl('stage1'), lang, o.currency)}</td>
                  <td>{money(ecl('stage2'), lang, o.currency)}</td>
                  <td>{money(ecl('stage3'), lang, o.currency)}</td>
                  <td>{money(o.overlays.reduce((a, x) => a + x.amount, 0), lang, o.currency)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </ChartOverTable>
    </PlotCard>
  );
}

export function C06VariantsView({ sel, onPick }: { sel: C06Sel | null; onPick: (id: string) => void }) {
  const manifest = sel?.data.manifest;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  if (!sel || all.state !== 'ready') return <Pending />;
  const entries = sel.data.manifest.artifacts.filter((a) => a.role === 'variant');
  const variants = (all.data as unknown as Array<VariantArtifact<C06Outputs>>)
    .filter((v) => v.outputs.kind === 'reporting-date')
    .map((v) => ({ id: v.variant_id, title: entries.find((e) => e.variant_id === v.variant_id)?.short_title ?? { en: v.variant_id, es: v.variant_id }, v }));
  return (
    <ViewsRow>
      <C06VariantsTable variants={variants} onPick={onPick} current={sel.data.variant.variant_id} />
    </ViewsRow>
  );
}

/** The case, the data it stands on (and why Freddie Mac is or is not there), the policy and the scenarios. */
export function C06ContextView({ sel }: { sel: C06Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const m = sel.data.manifest;
  const v = sel.data.variant;
  const prov = provenanceOf(v.provenance.truth_status);
  const fit = fitOf(sel);
  const d = o.data_status;
  const s = o.settings;
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard title={{ en: 'The case', es: 'El caso' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <FixtureNotice variant={v} />
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        <dl className="ct-defs" data-table="c06-data-status">
          <dt>{pick({ en: 'Reporting date', es: 'Fecha de reporte' }, lang)}</dt>
          <dd>{`${o.reporting_date} (${pick({ en: `periods of ${o.period_months} months`, es: `períodos de ${o.period_months} meses` }, lang)}; ${pick({ en: `12-month horizon ${o.horizon.stage1_months}, lifetime cap ${o.horizon.lifetime_cap_months} months`, es: `horizonte a 12 meses ${o.horizon.stage1_months}, tope de vida ${o.horizon.lifetime_cap_months} meses` }, lang)})`}</dd>
          <dt>{pick({ en: 'Primary data', es: 'Datos principales' }, lang)}</dt>
          <dd data-primary-source={d.primary_source}>{d.primary_source}</dd>
          <dt>Freddie Mac</dt>
          <dd data-freddie-mac={String(d.freddie_mac_available)}>
            {d.freddie_mac_available ? pick({ en: 'available', es: 'disponible' }, lang) : `${pick({ en: 'not available', es: 'no disponible' }, lang)}: ${d.freddie_mac_reason ?? ''}`}
          </dd>
          <dt>{pick({ en: 'Notice of the document', es: 'Aviso del documento' }, lang)}</dt>
          <dd>{pick(d.notice, lang)}</dd>
          <dt>{pick({ en: 'Truth status of this variant', es: 'Estado de verdad de esta variante' }, lang)}</dt>
          <dd>{v.provenance.truth_status}</dd>
        </dl>
      </PlotCard>
      <PlotCard title={{ en: 'The policy of the run', es: 'La política de la corrida' }} lane={REPLAY} provenance={prov} dataKey={stateKey} note={{ en: 'Only the 30 dpd and 90 dpd presumptions are in IFRS 9. The multipliers, the floor, the probation and the discounting convention are documented model settings, not requirements of the standard.', es: 'Solo las presunciones de 30 y 90 dpd están en IFRS 9. Los multiplicadores, el piso, la prueba y la convención de descuento son parámetros documentados del modelo, no requisitos de la norma.' }}>
        <dl className="ct-defs" data-table="c06-settings">
          <dt>{pick({ en: 'Discounting', es: 'Descuento' }, lang)}</dt>
          <dd>{`${s.discount_convention}; ${pick({ en: 'EIR basis', es: 'base de la TIE' }, lang)} ${s.eir_basis}`}</dd>
          <dt>{pick({ en: 'Probation', es: 'Prueba de cura' }, lang)}</dt>
          <dd>{pick({ en: `${s.probation_months} months`, es: `${s.probation_months} meses` }, lang)}</dd>
          <dt>{pick({ en: 'Low credit risk exemption', es: 'Exención de bajo riesgo' }, lang)}</dt>
          <dd>{s.low_credit_risk_exemption ? pick({ en: 'used', es: 'usada' }, lang) : pick({ en: 'not used', es: 'no usada' }, lang)}</dd>
          <dt>{pick({ en: 'Stage 3 at', es: 'Etapa 3 desde' }, lang)}</dt>
          <dd>{`${s.sicr.default_dpd} dpd`}</dd>
        </dl>
        {fit ? (
          <table className="caos-table ct-wrap-head" data-table="scenario-definitions">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Scenario', es: 'Escenario' }, lang)}</th>
                <th>{pick({ en: 'Weight', es: 'Peso' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Source', es: 'Fuente' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {fit.scenario_definitions.map((sc) => (
                <tr key={sc.id} data-scenario={sc.id}>
                  <td className="ct-text">{pick(sc.label, lang)}</td>
                  <td>{pct(sc.weight, lang, 0)}</td>
                  <td className="ct-text">{sc.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="ct-note" data-state="unavailable">{pick({ en: 'Not available: the models artifact carries no scenario definitions.', es: 'No disponible: el artefacto de modelos no trae definiciones de escenarios.' }, lang)}</p>
        )}
        <p className="ct-note" data-capital-bridge="not-in-contract">
          {pick(
            {
              en: 'The capital bridge (the allowance against the IRB expected loss) is not in the c06-outputs 1.0.0 contract, so this instrument does not draw it; it comes with the capital case.',
              es: 'El puente de capital (la cobertura contra la pérdida esperada IRB) no está en el contrato c06-outputs 1.0.0, así que este instrumento no lo dibuja; llega con el caso de capital.',
            },
            lang,
          )}
        </p>
      </PlotCard>
      <IdentitiesView sel={sel} />
      <TestRowsCard variant={v} prov={prov} />
    </div>
  );
}

/** The live read-out of the Scenarios section: the weight, the ECL at the rail's weights and the nearest precomputed simplex point. */
export function WeightReadout({ sel }: { sel: C06Sel | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  const prov = provenanceOf(sel?.data.variant.provenance.truth_status);
  if (!sel || !o) return <Readout title={{ en: 'ECL at these weights', es: 'PCE con estos pesos' }} lane={LIVE} provenance={prov} dataKey={stateKey} items={[]} />;
  const weights = rescaled(o, sel.scenario, sel.weight);
  const near = nearestPoint(o, weights);
  const label = o.scenarios.find((s) => s.id === sel.scenario)?.label ?? { en: sel.scenario, es: sel.scenario };
  const amount = (v: number | null | undefined) => compactMoney(v, o.currency);
  return (
    <Readout
      title={{ en: 'ECL at these weights', es: 'PCE con estos pesos' }}
      lane={LIVE}
      provenance={prov}
      dataKey={stateKey}
      items={[
        { label: { en: 'ECL, frozen', es: 'PCE cong.' }, ...amount(liveEcl(sel)), hint: { en: `The model ECL at these weights: the sum of weight times the ECL of each scenario at the staging of the weighted conditions, with ${label.en} at ${(sel.weight * 100).toFixed(1)}% and the others in their ratios; overlays excluded.`, es: `La PCE del modelo con estos pesos: la suma del peso por la PCE de cada escenario con las etapas de las condiciones ponderadas, con ${label.es} en ${(sel.weight * 100).toFixed(1).replace('.', ',')}% y los otros en sus proporciones; sin ajustes.` } },
        { label: { en: 'Grid, recalc.', es: 'Grilla, recalc.' }, ...amount(near?.ecl_recomputed), hint: { en: 'At the precomputed simplex point nearest to these weights, staging recomputed.', es: 'En el punto del simplex precalculado más cercano a estos pesos, con etapas recalculadas.' } },
        { label: { en: 'Stage 2 share', es: 'Frac. Etapa 2' }, value: near?.stage2_ratio_recomputed ?? null, unitless: true, format: { percent: true, decimals: 1 }, hint: { en: 'At the same grid point, staging recomputed.', es: 'En el mismo punto de la grilla, con etapas recalculadas.' } },
      ]}
    />
  );
}

/** The live read-out of the Curves section: the weighted curve of the segment, in the measure chosen, at the first horizon and at the last. */
export function CurveReadout({ sel }: { sel: C06Sel | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  const prov = provenanceOf(sel?.data.variant.provenance.truth_status);
  const title = { en: 'Weighted curve, this segment', es: 'Curva ponderada, este segmento' };
  if (!sel || !o) return <Readout title={title} lane={LIVE} provenance={prov} dataKey={stateKey} items={[]} />;
  const key = sel.measure === 'cumulative' ? 'cumulative_pd' : sel.measure === 'marginal' ? 'marginal_pd' : 'hazard';
  const symbol = sel.measure === 'cumulative' ? 'F' : sel.measure === 'marginal' ? 'q' : 'h';
  const ts = o.term_structures.find((t) => t.scenario_id === 'weighted' && t.segment_id === sel.segment) ?? null;
  const first = ts ? ts[key][ts.months.indexOf(o.horizon.stage1_months)] : undefined;
  const last = ts ? ts[key][ts[key].length - 1] : undefined;
  const lastMonth = ts ? ts.months[ts.months.length - 1] : null;
  return (
    <Readout
      title={title}
      lane={LIVE}
      provenance={prov}
      dataKey={stateKey}
      items={[
        { label: { en: `${symbol}(${o.horizon.stage1_months} m)`, es: `${symbol}(${o.horizon.stage1_months} m)` }, value: first ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: `The probability-weighted curve of ${sel.segment} at month ${o.horizon.stage1_months}, in the measure chosen above.`, es: `La curva ponderada por probabilidad de ${sel.segment} en el mes ${o.horizon.stage1_months}, en la medida elegida arriba.` } },
        { label: { en: `${symbol}(${lastMonth ?? 'last'} m)`, es: `${symbol}(${lastMonth ?? 'último'} m)` }, value: last ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: `The same curve at its last month.`, es: `La misma curva en su último mes.` } },
      ]}
    />
  );
}

/** The live read-out of the Account section: the SICR test of one sampled account against the policy of the run. */
export function AccountReadout({ sel }: { sel: C06Sel | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  const prov = provenanceOf(sel?.data.variant.provenance.truth_status);
  const p = o?.sicr_points.find((x) => x.account_id === sel?.account) ?? null;
  const rule = o?.settings.sicr;
  const multiplier = p && rule ? (rule.multiplier_schedule.find((m) => p.pd_origination_annualised <= m.pd_origination_upper) ?? rule.multiplier_schedule[rule.multiplier_schedule.length - 1]).multiplier : null;
  return (
    <Readout
      title={{ en: 'SICR test, this account', es: 'Prueba SICR, esta cuenta' }}
      lane={LIVE}
      provenance={prov}
      dataKey={stateKey}
      items={[
        { label: { en: 'PD at origination', es: 'PD originación' }, hint: { en: 'Annualised.', es: 'Anualizada.' }, value: p?.pd_origination_annualised ?? null, unitless: true, format: { percent: true, decimals: 2 } },
        { label: { en: 'PD now', es: 'PD hoy' }, hint: { en: 'Annualised.', es: 'Anualizada.' }, value: p?.pd_current_annualised ?? null, unitless: true, format: { percent: true, decimals: 2 } },
        { label: { en: 'Increase', es: 'Aumento' }, value: p ? p.pd_current_annualised / p.pd_origination_annualised : null, unit: { en: 'times', es: 'veces' }, format: { digits: 3 }, hint: { en: 'The PD now over the PD at origination; the multiplier the schedule asks for at this origination PD is in the next line.', es: 'La PD hoy sobre la PD de originación; el multiplicador que pide la tabla con esta PD de originación está en la línea siguiente.' } },
        { label: { en: 'Multiplier asked', es: 'Multiplicador pedido' }, hint: { en: 'The multiplier of the schedule at this origination PD.', es: 'El multiplicador de la tabla con esta PD de originación.' }, value: multiplier, unit: { en: 'times', es: 'veces' }, format: { digits: 3 } },
      ]}
    />
  );
}


/** The live read-out of the Simplex section: the range of the surface drawn and its value at the rail's weights. */
export function SurfaceReadout({ sel }: { sel: C06Sel | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  const prov = provenanceOf(sel?.data.variant.provenance.truth_status);
  if (!sel || !o) return <Readout title={{ en: 'The surface drawn', es: 'La superficie dibujada' }} lane={LIVE} provenance={prov} dataKey={stateKey} items={[]} />;
  const pick1 = (p: C06Outputs['weight_grid']['points'][number]) =>
    sel.surface === 'ecl' ? (sel.staging === 'recomputed' ? p.ecl_recomputed : p.ecl_frozen) : sel.staging === 'recomputed' ? p.stage2_ratio_recomputed : p.stage2_ratio_frozen;
  const vals = o.weight_grid.points.map(pick1);
  const near = nearestPoint(o, rescaled(o, sel.scenario, sel.weight));
  const money1 = sel.surface === 'ecl';
  // an amount is scaled to billions or millions with its unit, each value in its own scale (the rail is 248 px wide)
  const item = (v: number | null) => (money1 ? compactMoney(v, o.currency) : { value: v, unitless: true as const, format: { percent: true, decimals: 1 } });
  return (
    <Readout
      title={{ en: 'The surface drawn', es: 'La superficie dibujada' }}
      lane={LIVE}
      provenance={prov}
      dataKey={stateKey}
      items={[
        { label: { en: 'Lowest', es: 'Mínimo' }, hint: { en: 'The lowest value of the surface on the grid.', es: 'El valor más bajo de la superficie en la grilla.' }, ...item(Math.min(...vals)) },
        { label: { en: 'Highest', es: 'Máximo' }, hint: { en: 'The highest value of the surface on the grid.', es: 'El valor más alto de la superficie en la grilla.' }, ...item(Math.max(...vals)) },
        { label: { en: 'At weights', es: 'Con pesos' }, ...item(near ? pick1(near) : null), hint: { en: 'At the simplex point nearest to the weights of the rail.', es: 'En el punto del simplex más cercano a los pesos del panel.' } },
      ]}
    />
  );
}
