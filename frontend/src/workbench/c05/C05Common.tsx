// C05's Findings, Variants and Context groups, and the live read-outs of its rail (ADR-0017 rule 3: every section
// shows a value that moves with its controls).
import { PlotCard, Readout, formatNumber, pick, useShellLang, useWorkbenchState, type BiText, type ShellColorToken } from '@fasl-work/caos-app-shell';
import { UPlotChart, type UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { loadAllVariants, useArtifact } from '../../api/artifacts';
import { C05WriteUp } from '../../content/cases/C05';
import type { Finding, TestRow, VariantArtifact } from '../../lib/contract.types';
import { LIGHT_TEXT, LIGHT_TONE, relight } from '../../lib/policy';
import { REPLAY, provenanceOf } from '../model';
import { Pending } from '../Pending';
import { CASE1, approachShort, averageRiskWeight, isLdp, isSp, useLiveBounds, useLiveCurve, type C05Sel, type LdpVariant, type SpVariant } from './selection';

const LIVE = 'live' as const;
const pct = (lang: 'en' | 'es', v: number | null | undefined, decimals = 3) => formatNumber(v, lang, { percent: true, decimals });

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

function findRow(v: VariantArtifact<unknown>, e: string): TestRow | undefined {
  const [testId, model, segment] = e.split('@');
  return v.tests.find((t) => t.test_id === testId && t.model_id === model && (segment ? t.segment === segment : t.segment === null || t.segment === 'portfolio'));
}

export function C05FindingsView({ sel }: { sel: C05Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  if (!sel) return <Pending />;
  const v = sel.data.variant as VariantArtifact<unknown>;
  const order = ['S1', 'S2', 'S3', 'S4'];
  const findings: Finding[] = [...v.findings].sort((a, b) => order.indexOf(a.severity) - order.indexOf(b.severity));
  return (
    <div className="caos-views-row" data-views="1">
      <div className="ct-col">
        <PlotCard
          fill
          title={{ en: 'What the validation found', es: 'Lo que encontró la validación' }}
          lane={REPLAY}
          provenance={provenanceOf(v.provenance.truth_status)}
          dataKey={stateKey}
          note={{ en: 'Each finding cites the tests behind it (their light under the rail\'s policy) or a stated design limit.', es: 'Cada hallazgo cita las pruebas que lo respaldan (su luz con la política del panel) o un límite de diseño declarado.' }}
        >
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
                        {f.evidence.map((e) => {
                          if (e.startsWith('design:')) return <li key={e}>{pick({ en: 'Design limit: ', es: 'Límite de diseño: ' }, lang)}{e.slice(7)}</li>;
                          const row = findRow(v, e);
                          return (
                            <li key={e}>
                              {e}: {row ? `p ${formatNumber(row.p_value, lang, { digits: 2 })}, ${pick(LIGHT_TEXT[relight(row, sel.alphas)], lang)}` : ''}
                            </li>
                          );
                        })}
                      </ul>
                    </td>
                    <td className="ct-wide-only">{pick(STATUS_TEXT[f.status], lang)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
    </div>
  );
}

export function C05VariantsView({ sel, onPick }: { sel: C05Sel | null; onPick: (id: string) => void }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const manifest = sel?.data.manifest;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  if (!sel || all.state !== 'ready') return <Pending />;
  const entries = sel.data.manifest.artifacts.filter((a) => a.role === 'variant');
  const sp = (all.data as VariantArtifact<unknown>[]).filter(isSp);
  const ldp = (all.data as VariantArtifact<unknown>[]).filter(isLdp);
  const title = (id: string) => entries.find((e) => e.variant_id === id)?.title ?? { en: id, es: id };
  // the chip's short label names the row, as it does in the rail; the full title is the button's tooltip
  const short = (id: string) => entries.find((e) => e.variant_id === id)?.short_title ?? title(id);
  const prov = provenanceOf((sel.data.variant as VariantArtifact<unknown>).provenance.truth_status);
  const dp = (v: (typeof sp)[number], id: string) => v.tests.find((t) => t.test_id === 'pd.default_profile' && t.model_id === id);
  const chart = isSp(sel.data.variant as VariantArtifact<unknown>) ? spCompare(sp, sel, dp) : ldpCompare(ldp, short);
  return (
    <>
      <div className="ct-row">
      <div className="ct-share-3">
        <PlotCard title={{ en: 'The calibration variants', es: 'Las variantes de calibración' }} lane={REPLAY} provenance={prov} dataKey={stateKey}
          note={{ en: 'The default-profile p-value of each case 1 approach, and the least squares forecast of the PD (case 3) against the observed one. Pick a variant to load it.', es: 'El valor p del perfil de cada enfoque del caso 1, y el pronóstico de la PD por mínimos cuadrados (caso 3) contra la observada. Elija una variante para cargarla.' }}>
          <div className="ct-scroll">
            <table className="caos-table ct-wrap-head" data-table="variants-sp">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Variant', es: 'Variante' }, lang)}</th>
                  <th>{pick({ en: 'Observed PD', es: 'PD observada' }, lang)}</th>
                  {sp.length > 0 && CASE1.map((id) => <th key={id}>{pick(approachShort(sp[0], id), lang)}</th>)}
                  <th className="ct-wide-only">{pick({ en: 'Least squares PD', es: 'PD mín. cuadrados' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {sp.map((v) => (
                  <tr key={v.variant_id} className={v.variant_id === sel.data.variant.variant_id ? 'ct-current' : undefined}>
                    <td className="ct-text">
                      <button type="button" className="ct-linkbutton" title={pick(title(v.variant_id), lang)} onClick={() => onPick(v.variant_id)}>{pick(short(v.variant_id), lang)}</button>
                    </td>
                    <td>{pct(lang, v.outputs.pd1, 2)}</td>
                    {CASE1.map((id) => {
                      const r = dp(v, id);
                      const l = r ? relight(r, sel.alphas) : 'not_evaluated';
                      return <td key={id} className={`ct-light ct-light-${l}`}>{formatNumber(r?.p_value, lang, { digits: 2 })}</td>;
                    })}
                    <td className="ct-wide-only">{pct(lang, v.outputs.approaches['C2-ls'].pd, 2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
      <div className="ct-share-2">
        <PlotCard title={{ en: 'The low-default variants', es: 'Las variantes de bajo incumplimiento' }} lane={REPLAY} provenance={prov} dataKey={stateKey}
          note={{ en: 'The defaults observed and the independent bounds at 75%, grades A, B, C.', es: 'Los incumplimientos observados y las cotas independientes al 75%, grados A, B, C.' }}>
          <div className="ct-scroll">
            <table className="caos-table" data-table="variants-ldp">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Variant', es: 'Variante' }, lang)}</th>
                  <th>{pick({ en: 'Defaults', es: 'Incumpl.' }, lang)}</th>
                  <th>{pick({ en: 'Bounds at 75%', es: 'Cotas al 75%' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {ldp.map((v) => {
                  const k = v.outputs.gammas.indexOf(0.75);
                  return (
                    <tr key={v.variant_id} className={v.variant_id === sel.data.variant.variant_id ? 'ct-current' : undefined}>
                      <td className="ct-text">
                        <button type="button" className="ct-linkbutton" title={pick(title(v.variant_id), lang)} onClick={() => onPick(v.variant_id)}>{pick(short(v.variant_id), lang)}</button>
                      </td>
                      <td>{v.outputs.defaults.join(', ')}</td>
                      <td>{v.outputs.bounds.independent[k].map((b) => pct(lang, b, 2)).join(', ')}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
      </div>
      <PlotCard fill title={chart.title} lane={REPLAY} provenance={prov} dataKey={stateKey} note={chart.note}>
        <UPlotChart height="fill" x={chart.x} y={chart.y} series={chart.series} />
      </PlotCard>
    </>
  );
}

/** Every approach of Tasche (2013) with a default-profile test, in the paper's order (cases 1, 2, 3). */
const ALL_APPROACHES = [...CASE1, 'B1-ilr', 'C1-ipc', 'C2-ls', 'C3-chi2', 'C4-ilr'] as const;

type Compare = Pick<UPlotChartProps, 'x' | 'y' | 'series'> & { title: BiText; note: BiText };

/** The calibration years side by side: the default-profile p-value of every approach, against the rail's policy. */
function spCompare(sp: SpVariant[], sel: C05Sel, dp: (v: SpVariant, id: string) => TestRow | undefined): Compare {
  const x = ALL_APPROACHES.map((_, i) => i + 1);
  const numbered = (lang: 'en' | 'es') => ALL_APPROACHES.map((id, i) => `${i + 1} ${pick(sp[0] ? approachShort(sp[0], id) : { en: id, es: id }, lang)}`).join(', ');
  const level = (a: number, lang: 'en' | 'es') => formatNumber(a, lang, { decimals: 3 });
  // how far the case 3 forecasts of the PD land from the observed one, over the years shown
  const ratios = sp.flatMap((v) => ALL_APPROACHES.filter((id) => id.startsWith('C')).map((id) => v.outputs.approaches[id].pd / v.outputs.pd1));
  const times = (lang: 'en' | 'es') => `${formatNumber(Math.min(...ratios), lang, { decimals: 1 })} ${lang === 'en' ? 'to' : 'a'} ${formatNumber(Math.max(...ratios), lang, { decimals: 1 })}`;
  return {
    title: { en: 'The default-profile test of every approach, year by year', es: 'La prueba del perfil de incumplimiento de cada enfoque, año a año' },
    note: {
      en: `One point per approach: ${numbered('en')}. Dashed, the rail's thresholds. The test sees the shape of the curve, not its level: the case 3 approaches (6 to 9) forecast ${times('en')} times the observed PD in these years, and that does not show here.`,
      es: `Un punto por enfoque: ${numbered('es')}. Segmentadas, los umbrales del panel. La prueba ve la forma de la curva, no su nivel: los enfoques del caso 3 (6 a 9) pronostican ${times('es')} veces la PD observada en estos años, y eso no se ve aquí.`,
    },
    x: { values: x, label: { en: 'Approach (numbered in the note)', es: 'Enfoque (numerado en la nota)' }, format: { decimals: 0 } },
    y: { label: { en: 'p-value (log scale)', es: 'Valor p (escala log.)' }, log: true, format: { digits: 2 } },
    series: [
      ...sp.map((v, i) => ({ label: { en: String(v.outputs.year), es: String(v.outputs.year) }, values: ALL_APPROACHES.map((id) => dp(v, id)?.p_value ?? null), color: (i === 0 ? '--color-accent' : '--color-magenta') as ShellColorToken, mode: 'points' as const })),
      { label: { en: `Amber below ${level(sel.alphas.amber, 'en')}`, es: `Ámbar bajo ${level(sel.alphas.amber, 'es')}` }, values: x.map(() => sel.alphas.amber), color: '--color-warn', width: 1.2, dash: [4, 4] },
      { label: { en: `Red below ${level(sel.alphas.red, 'en')}`, es: `Rojo bajo ${level(sel.alphas.red, 'es')}` }, values: x.map(() => sel.alphas.red), color: '--color-bad', width: 1.2, dash: [4, 4] },
    ],
  };
}

const LDP_COLOR: ShellColorToken[] = ['--color-accent', '--color-accent-2', '--color-magenta', '--color-fg'];

/** The low-default observations side by side: the independent bounds at 75% each one implies, against the expert PDs
 * under test and, for the generated years, the truth. */
function ldpCompare(ldp: LdpVariant[], short: (id: string) => BiText): Compare {
  const truth = ldp.find((v) => v.outputs.true_pd)?.outputs.true_pd;
  return {
    title: { en: 'What each observed year implies: the bounds at 75%', es: 'Lo que implica cada año observado: las cotas al 75%' },
    note: {
      en: 'The independent most prudent bound of each grade at 75%, one line per observation, against the expert PDs under test (dotted) and the true PDs of the generator (dashed). Every bound lies above the truth; the fewer the defaults, the closer it comes.',
      es: 'La cota más prudente independiente de cada grado al 75%, una línea por observación, contra las PD expertas en prueba (punteada) y las PD verdaderas del generador (segmentada). Toda cota queda sobre la verdad; mientras menos incumplimientos, más se acerca.',
    },
    x: { values: [1, 2, 3], label: { en: 'Grade (1 A, 2 B, 3 C)', es: 'Grado (1 A, 2 B, 3 C)' }, format: { decimals: 0 } },
    y: { label: { en: 'Bound at 75% (log scale)', es: 'Cota al 75% (escala log.)' }, log: true, format: { percent: true, digits: 2 } },
    series: [
      ...ldp.map((v, i) => ({ label: short(v.variant_id), values: v.outputs.bounds.independent[v.outputs.gammas.indexOf(0.75)], color: LDP_COLOR[i % LDP_COLOR.length], width: 2 })),
      ...(ldp[0] ? [{ label: { en: 'Expert PDs', es: 'PD expertas' }, values: ldp[0].outputs.expert_pd, color: '--color-warn' as ShellColorToken, width: 1.2, dash: [2, 4] }] : []),
      ...(truth ? [{ label: { en: 'True PDs', es: 'PD verdaderas' }, values: truth, color: '--color-fg-subtle' as ShellColorToken, width: 1.2, dash: [8, 4] }] : []),
    ],
  };
}

const CLASS_TEXT: Record<string, BiText> = {
  'mirror-allowed': { en: 'mirror-allowed: rows may be redistributed with attribution', es: 'espejo permitido: las filas pueden redistribuirse con atribución' },
  'derived-only': { en: 'derived-only: the PDF stays in the data root; only rates and results are published', es: 'solo derivados: el PDF queda en la raíz de datos; solo se publican tasas y resultados' },
};

export function C05ContextView({ sel }: { sel: C05Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  if (!sel) return <Pending />;
  const m = sel.data.manifest;
  const v = sel.data.variant as VariantArtifact<unknown>;
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard title={{ en: 'The case', es: 'El caso' }} lane={REPLAY} provenance={provenanceOf(v.provenance.truth_status)} dataKey={stateKey}>
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        <table className="caos-table" data-sources={m.sources.join(' ')}>
          <thead>
            <tr>
              <th className="caos-col-text">{pick({ en: 'Source', es: 'Fuente' }, lang)}</th>
              <th className="caos-col-text">{pick({ en: 'Licence and class', es: 'Licencia y clase' }, lang)}</th>
              <th className="caos-col-text">{pick({ en: 'Attribution', es: 'Atribución' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {m.sources.map((id) => {
              const s = m.source_details[id];
              return (
                <tr key={id} data-licence-class={s.class}>
                  <td className="caos-col-text">
                    <a href={s.landing} target="_blank" rel="noreferrer">{s.name}</a>
                  </td>
                  <td className="caos-col-text">
                    {s.licence} <em>({pick(CLASS_TEXT[s.class] ?? { en: s.class, es: s.class }, lang)})</em>
                  </td>
                  <td className="caos-col-text">{s.attribution}</td>
                </tr>
              );
            })}
            <tr data-licence-class="generator">
              <td className="caos-col-text">{pick({ en: 'Vasicek generator (Contraste\'s own)', es: 'Generador de Vasicek (de Contraste)' }, lang)}</td>
              <td className="caos-col-text">{pick({ en: 'MIT, no third-party data', es: 'MIT, sin datos de terceros' }, lang)}</td>
              <td className="caos-col-text">{pick({ en: 'True PDs 0.05%, 0.10%, 0.20%; correlation 12%; 20,000 seeded years', es: 'PD verdaderas 0,05%, 0,10%, 0,20%; correlación 12%; 20.000 años con semilla' }, lang)}</td>
            </tr>
          </tbody>
        </table>
        <p className="ct-note">
          {pick(
            {
              en: `Truth status of this variant: ${v.provenance.truth_status}. The readers check each paper against its own print (Table 2's grades add up to its All row; every printed rate is the counts' ratio; every low-default table has its six levels and named rows) and refuse the bake otherwise. riskvalidation ${m.engine.riskvalidation ?? ''}.`,
              es: `Estado de verdad de esta variante: ${v.provenance.truth_status}. Los lectores verifican cada artículo contra su propia impresión (los grados de la Tabla 2 suman su fila All; cada tasa impresa es la razón de los conteos; cada tabla de bajo incumplimiento tiene sus seis niveles y sus filas nombradas) y si no, rechazan el horneado. riskvalidation ${m.engine.riskvalidation ?? ''}.`,
            },
            lang,
          )}
        </p>
      </PlotCard>
      <PlotCard title={{ en: 'The case in depth', es: 'El caso en profundidad' }} lane={REPLAY} provenance={provenanceOf(v.provenance.truth_status)} dataKey={stateKey}>
        <div className="ct-prose">
          <C05WriteUp />
        </div>
      </PlotCard>
    </div>
  );
}

/** The live read-out of the Calibration section: the constant, the worst grade's PD, and whether the model is proper
 * (every grade's live PD is in the Curves view's table). */
export function CalibrationReadout({ sel }: { sel: C05Sel | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const live = useLiveCurve(sel);
  const v = sel?.data.variant as VariantArtifact<unknown> | undefined;
  const sp = v && isSp(v) ? v : null;
  const label: BiText = sel?.approach === 'A3-spd' ? { en: 'c_PD', es: 'c_PD' } : sel?.approach === 'A4-slr' ? { en: 'c_LR', es: 'c_LR' } : sel?.approach === 'A1-idp' ? { en: 'Forecast AR', es: 'AR pronosticada' } : { en: 'AR kept', es: 'AR conservada' };
  const constant = sel?.approach === 'A2-iar' ? sp?.outputs.ar0 ?? null : live?.constant ?? null;
  return (
    <Readout
      title={{ en: 'The live curve', es: 'La curva en vivo' }}
      lane={LIVE}
      provenance={provenanceOf(v?.provenance.truth_status)}
      dataKey={stateKey}
      items={[
        { label, value: constant, unitless: true, format: sel?.approach === 'A1-idp' || sel?.approach === 'A2-iar' ? { percent: true, decimals: 1 } : { decimals: 4 } },
        { label: { en: 'PD of CCC-C', es: 'PD de CCC-C' }, value: live?.curve.length ? live.curve[16] : null, unitless: true, format: { percent: true, decimals: 2 } },
        {
          label: { en: 'Model', es: 'Modelo' },
          text: live?.improper ? { en: 'improper', es: 'impropio' } : { en: 'proper', es: 'propio' },
          tone: live?.improper ? 'bad' : 'good',
          unitless: true,
          hint: { en: live?.improper ?? 'A proper joint distribution of grade and state.', es: live?.improper ?? 'Una distribución conjunta propia de grado y estado.' },
        },
      ]}
    />
  );
}

/** The live read-out of the Bounds section: the three grades' bounds at the rail's level, correlation and scaling. */
export function BoundsReadout({ sel }: { sel: C05Sel | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const live = useLiveBounds(sel);
  const v = sel?.data.variant as VariantArtifact<unknown> | undefined;
  const grades = v && isLdp(v) ? v.outputs.grades : ['A', 'B', 'C'];
  return (
    <Readout
      title={{ en: 'The live bounds', es: 'Las cotas en vivo' }}
      lane={LIVE}
      provenance={provenanceOf(v?.provenance.truth_status)}
      dataKey={stateKey}
      items={grades.map((g, j) => ({ label: { en: `Grade ${g}`, es: `Grado ${g}` }, value: live?.pd[j] ?? null, unitless: true, format: { percent: true, decimals: 3 } }))}
    />
  );
}

/** The live read-out of the Capital section: the average risk weight under the rail's regime and LGD. */
export function CapitalReadout({ sel }: { sel: C05Sel | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const curve = useLiveCurve(sel);
  const bounds = useLiveBounds(sel);
  const v = sel?.data.variant as VariantArtifact<unknown> | undefined;
  let mine: number | null = null;
  let ref: number | null = null;
  let refLabel: BiText = { en: 'Reference', es: 'Referencia' };
  if (sel && v && isSp(v)) {
    const o = v.outputs;
    if (curve?.curve.length) mine = averageRiskWeight(curve.curve, o.profile1, sel.regime, sel.lgd, o.irb.maturity);
    ref = averageRiskWeight(o.qmm0.curve, o.profile1, sel.regime, sel.lgd, o.irb.maturity);
    refLabel = { en: '2009 curve', es: 'Curva 2009' };
  } else if (sel && v && isLdp(v)) {
    const o = v.outputs;
    if (bounds) mine = averageRiskWeight(bounds.pd, o.obligors, sel.regime, sel.lgd, o.irb.maturity);
    ref = averageRiskWeight(o.expert_pd, o.obligors, sel.regime, sel.lgd, o.irb.maturity);
    refLabel = { en: 'Expert PDs', es: 'PD expertas' };
  }
  return (
    <Readout
      title={{ en: 'Average risk weight', es: 'Ponderador medio' }}
      lane={LIVE}
      provenance={provenanceOf(v?.provenance.truth_status)}
      dataKey={stateKey}
      items={[
        { label: { en: 'Live', es: 'En vivo' }, value: mine, unitless: true, format: { percent: true, decimals: 1 }, hint: { en: 'Share of EAD, IRB corporate function.', es: 'Fracción de la EAD, función IRB corporativa.' } },
        { label: refLabel, value: ref, unitless: true, format: { percent: true, decimals: 1 } },
      ]}
    />
  );
}

/** The live read-out of the Policy section: the lights of the variant's tests under the rail's thresholds. */
export function C05PolicyReadout({ sel }: { sel: C05Sel | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const v = sel?.data.variant as VariantArtifact<unknown> | undefined;
  let red = 0;
  let amber = 0;
  if (sel && v) {
    for (const t of v.tests) {
      const l = relight(t, sel.alphas);
      if (l === 'red') red++;
      if (l === 'amber') amber++;
    }
  }
  const first = v && isSp(v) ? v.tests.find((t) => t.test_id === 'pd.default_profile' && t.model_id === sel?.approach) : v?.tests.find((t) => t.test_id === 'pd.binomial_vasicek');
  const light = first && sel ? relight(first, sel.alphas) : null;
  return (
    <Readout
      title={{ en: 'Under this policy', es: 'Con esta política' }}
      lane={LIVE}
      provenance={provenanceOf(v?.provenance.truth_status)}
      dataKey={stateKey}
      items={[
        { label: { en: 'Red lights', es: 'Luces rojas' }, value: sel ? red : null, unit: { en: 'tests', es: 'pruebas' } },
        { label: { en: 'Amber lights', es: 'Luces ámbar' }, value: sel ? amber : null, unit: { en: 'tests', es: 'pruebas' } },
        {
          label: v && isSp(v) ? { en: 'Default profile, this approach', es: 'Perfil, este enfoque' } : { en: 'Vasicek binomial', es: 'Binomial de Vasicek' },
          text: light ? LIGHT_TEXT[light] : undefined,
          tone: light ? LIGHT_TONE[light] : 'neutral',
          unitless: true,
        },
      ]}
    />
  );
}
