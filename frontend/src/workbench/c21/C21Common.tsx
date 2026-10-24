// C21's legal label, Findings, Variants and Context groups and the live read-outs of its rail. Every C21 view carries the
// "no legal claim" label and the three legal sentences of the research addendum (H3): Regulation B does not apply the
// effects test, the Fair Housing Act is a separate statute under which disparate-impact claims are cognizable, and the
// Interagency Procedures say gross HMDA disparities are not appropriate for adverse impact analysis. The unconditional
// rates are indicators only; the controlled disparity is an approximation of comparative evidence with its missing
// controls named, and never a finding of a violation.
import { Fragment, type ReactNode } from 'react';
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { loadAllVariants, useArtifact } from '../../api/artifacts';
import type { VariantArtifact } from '../../lib/contract.types';
import { FindingsCard, FixtureNotice } from '../c06/C06Common';
import { Pending } from '../Pending';
import { LiveReadout, useCard } from '../c03/U6Shared';
import { Marked } from './Marked';
import { FindingsEvidenceCard } from './FindingsEvidence';
import { LabelledOverTable, barMin, f3, int, pc, pc1 } from '../c20/U14Common';
import { BASIS_TEXT, CONTROL_TEXT, FIELD_TEXT, attributeFor, contrastFor, fitOf, groupBi, outputsOf, text, type C21Legal, type C21Outputs, type C21Sel } from './selection';
import { es, treatmentName } from './localise';

/** The short label every C21 view says before its content. */

/** The HMDA fields the data notes list that the attribute and control maps do not name (the CFPB data dictionary). */
const DATA_FIELD_TEXT: Record<string, { en: string; es: string }> = {
  action_taken: { en: 'Action taken on the application', es: 'Acción tomada sobre la solicitud' },
  rate_spread: { en: 'Rate spread', es: 'Diferencial de tasa' },
};

export function NoLegalClaim({ legal }: { legal: C21Legal | null }) {
  const lang = useShellLang();
  return (
    <p className="ct-note" data-label="no-legal-claim">
      <strong>{legal ? pick(legal.label, lang) : pick({ en: 'no legal claim', es: 'sin afirmación legal' }, lang)}.</strong>{' '}
      {pick({ en: 'Statistical disparity in public decisions; it scores nobody and certifies nothing.', es: 'Disparidad estadística en decisiones públicas; no puntúa a nadie ni certifica nada.' }, lang)}
    </p>
  );
}

/** The three legal sentences of the addendum, each with its citation, quoted as the source writes it. */
export function LegalSentences({ legal }: { legal: C21Legal | null }) {
  const lang = useShellLang();
  if (!legal) return <p className="ct-note" data-state="unavailable">{pick({ en: 'The legal sentences are not available in this document.', es: 'Las frases legales no están disponibles en este documento.' }, lang)}</p>;
  const rows: Array<[string, { citation: string; quote: string; text: BiText }]> = [
    ['regulation-b', legal.regulation_b],
    ['fair-housing-act', legal.fair_housing_act],
    ['procedures', legal.procedures],
  ];
  return (
    <div data-block="legal-sentences">
      <ul className="ct-note">
        {rows.map(([id, r]) => (
          <li key={id} data-legal={id}>
            <span translate="no" lang="en">{`"${r.quote}"`}</span> (<Marked>{r.citation}</Marked>)
          </li>
        ))}
      </ul>
      <p className="ct-note" data-legal-reading="unconditional">
        {pick({ en: 'The unconditional rates are indicators only. The controlled disparity is an approximation of comparative evidence, with its missing controls named, and never a finding of a violation.', es: 'Las tasas incondicionales son solo indicadores. La disparidad controlada es una aproximación de evidencia comparativa, con sus controles faltantes nombrados, y nunca una constatación de infracción.' }, lang)}
      </p>
    </div>
  );
}

/** The head every C21 view opens with, and the sentences it closes with: what a view passes to `ChartOverTable` and `LabelledOverTable`. */
export function legalOf(sel: Pick<C21Sel, 'data'> | null): C21Legal | null {
  return outputsOf(sel)?.legal ?? fitOf(sel)?.legal ?? null;
}

export function C21FindingsView({ sel }: { sel: C21Sel | null }) {
  const lang = useShellLang();
  if (!sel) return <Pending />;
  const legal = legalOf(sel);
  // with findings, the sentences sit under the evidence so the two cards take the height of the group; with none, they stay in the head
  const none = sel.data.variant.findings.length === 0;
  return (
    <>
      <div className="ct-stack-natural" data-block="legal-head">
        <NoLegalClaim legal={legal} />
        {none ? <LegalSentences legal={legal} /> : null}
      </div>
      <ViewsRow>
        <FindingsCard variant={sel.data.variant} />
        <FindingsEvidenceCard
          variant={sel.data.variant}
          footer={
            <>
              <LegalSentences legal={legal} />
              <p className="ct-note">{pick({ en: 'The tests the engine returned sit under the view they belong to; a test that did not run shows its reason there.', es: 'Las pruebas que devolvió el motor están bajo la vista a la que pertenecen; una prueba que no corrió muestra allí su razón.' }, lang)}</p>
            </>
          }
        />
      </ViewsRow>
    </>
  );
}

type Entry = { id: string; title: BiText; v: VariantArtifact<C21Outputs> };

/** The six year pairs in rows: for the attribute in focus, the lowest approval rate and whether the controlled estimate kept its sign in the next year. */
export function C21VariantsTable({ variants, onPick, current, field }: { variants: Entry[]; onPick: (id: string) => void; current: string; field: string }) {
  const lang = useShellLang();
  const card = useCard(variants[0]?.v as unknown as VariantArtifact | undefined);
  const sorted = [...variants].sort((a, b) => a.v.outputs.fit_year - b.v.outputs.fit_year);
  const legal = sorted[0]?.v.outputs.legal ?? null;
  const lowest = sorted.flatMap(({ id, v }) => {
    const a = v.outputs.attributes.find((x) => x.field === field) ?? v.outputs.attributes[0];
    const g = a && a.groups.length ? a.groups.reduce((m, x) => (x.selection_rate < m.selection_rate ? x : m)) : null;
    return g ? [{ id, fit: v.outputs.fit_year, confirm: v.outputs.confirm_year, rate: g.selection_rate, group: g.group }] : [];
  });
  return (
    <PlotCard
      fill
      title={{ en: 'The year pairs', es: 'Los pares de años' }}
      {...card}
      note={{
        en: 'Each pair fits the estimate on year t and confirms it on year t+1. The columns follow the attribute in focus. Pick a pair to load it.',
        es: 'Cada par ajusta la estimación en el año t y la confirma en el año t+1. Las columnas siguen al atributo en foco. Elija un par para cargarlo.',
      }}
    >
      <LabelledOverTable
        head={<NoLegalClaim legal={legal} />}
        chartMin={barMin(Math.max(1, lowest.length))}
        chart={
          lowest.length === 0 ? (
            <p className="caos-pending" data-state="unavailable">{pick({ en: 'Not available: no year pair carries a group rate.', es: 'No disponible: ningún par de años trae una tasa de grupo.' }, lang)}</p>
          ) : (
            <BarChart
              title={{ en: 'Lowest approval rate by year pair', es: 'Menor tasa de aprobación por par de años' }}
              height="fill"
              orientation="horizontal"
              data={lowest.map((l) => ({ id: l.id, label: { en: `${l.fit}-${l.confirm}`, es: `${l.fit}-${l.confirm}` } as BiText, value: l.rate, highlight: l.id === current, hint: groupBi(l.group) as BiText }))}
              axis={{ label: { en: 'Lowest group approval rate (an indicator only)', es: 'Menor tasa de aprobación de un grupo (solo un indicador)' }, format: { percent: true, decimals: 0 }, range: [0, 1] }}
            />
          )
        }
      >
        <table className="caos-table ct-wrap-head" data-table="variants-c21">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Pair', es: 'Par' }, lang)}</th>
              <th className="ct-wide-only">{pick({ en: 'Rows, fit', es: 'Filas, ajuste' }, lang)}</th>
              <th>{pick({ en: 'Lowest approval rate', es: 'Menor tasa de aprobación' }, lang)}</th>
              <th className="ct-text">{pick({ en: 'Next year', es: 'Año siguiente' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map(({ id, title, v }) => {
              const o = v.outputs;
              const a = o.attributes.find((x) => x.field === field) ?? o.attributes[0];
              const lowest = a && a.groups.length ? a.groups.reduce((m, g) => (g.selection_rate < m.selection_rate ? g : m)) : null;
              const conf = a?.contrasts.map((c) => c.confirmation.estimate).filter((e) => e !== null) ?? [];
              const same = conf.length ? conf.every((e) => e.same_sign) : null;
              return (
                <tr key={id} data-variant={id} data-pair={o.pair_id} className={id === current ? 'ct-current' : undefined}>
                  <td className="ct-text">
                    <button type="button" className="ct-linkbutton" onClick={() => onPick(id)}>{pick(title, lang)}</button>
                    <span className="ct-note">{` ${o.fit_year} - ${o.confirm_year}`}</span>
                  </td>
                  <td className="ct-wide-only">{int(o.scope.rows_fit, lang)}</td>
                  <td data-na={lowest ? undefined : 'true'}>{lowest ? `${pc1(lowest.selection_rate, lang)} (${pick(groupBi(lowest.group), lang)})` : formatNumber(null, lang)}</td>
                  <td className="ct-text" data-same-sign={same === null ? 'none' : same}>
                    {same === null ? formatNumber(null, lang) : pick(same ? { en: 'same sign', es: 'mismo signo' } : { en: 'sign changed', es: 'signo cambiado' }, lang)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <LegalSentences legal={legal} />
      </LabelledOverTable>
    </PlotCard>
  );
}

export function C21VariantsView({ sel, onPick }: { sel: C21Sel | null; onPick: (id: string) => void }) {
  const manifest = sel?.data.manifest;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  if (!sel || all.state !== 'ready') return <Pending />;
  const entries = sel.data.manifest.artifacts.filter((a) => a.role === 'variant');
  const variants = (all.data as unknown as Array<VariantArtifact<C21Outputs>>)
    .filter((v) => v.outputs.kind === 'year-pair')
    .map((v) => ({ id: v.variant_id, title: entries.find((e) => e.variant_id === v.variant_id)?.short_title ?? { en: v.variant_id, es: v.variant_id }, v }));
  return (
    <ViewsRow>
      <C21VariantsTable variants={variants} onPick={onPick} current={sel.data.variant.variant_id} field={sel.field} />
    </ViewsRow>
  );
}

const dd = (children: ReactNode, key: string) => <Fragment key={key}>{children}</Fragment>;

/** The case, the scope, the conventions of the outcome and the identifiers, the licence sentence (UNVERIFIED) and the data notes. */
export function C21ContextView({ sel }: { sel: C21Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const m = sel.data.manifest;
  const v = sel.data.variant;
  const c = o.conventions;
  const l = o.licence;
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard title={{ en: 'The case', es: 'El caso' }} {...card}>
        <FixtureNotice variant={v} />
        <NoLegalClaim legal={o.legal} />
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        <dl className="ct-defs" data-table="c21-scope">
          <dt>{pick({ en: 'Year pair', es: 'Par de años' }, lang)}</dt>
          <dd>{`${o.fit_year} - ${o.confirm_year}`}</dd>
          <dt>{pick({ en: 'State', es: 'Estado' }, lang)}</dt>
          <dd>{o.scope.state}</dd>
          <dt>{pick({ en: 'Source', es: 'Fuente' }, lang)}</dt>
          <dd>{o.scope.source === 'hmda' ? 'HMDA' : o.scope.source}</dd>
          <dt>{pick({ en: 'Rows', es: 'Filas' }, lang)}</dt>
          <dd>{`${int(o.scope.rows_fit, lang)} / ${int(o.scope.rows_confirm, lang)}`}</dd>
        </dl>
      </PlotCard>
      <PlotCard title={{ en: 'The legal reading', es: 'La lectura legal' }} {...card}>
        <div className="ct-scroll" data-caos-flow="">
          <LegalSentences legal={o.legal} />
        </div>
      </PlotCard>
      <PlotCard title={{ en: 'The conventions', es: 'Las convenciones' }} {...card} note={{ en: 'Each is a named convention of Contraste.', es: 'Cada una es una convención con nombre de Contraste.' }}>
        <dl className="ct-defs" data-table="c21-conventions" data-status={c.label}>
          <dt>{pick({ en: 'Decision outcome', es: 'Resultado de la decisión' }, lang)}</dt>
          <dd>{pick(c.outcome.note, lang)}</dd>
          {dd(
            <>
              <dt>{pick({ en: 'Codes', es: 'Códigos' }, lang)}</dt>
              <dd>{pick({ en: `approval ${c.outcome.approval_codes.join(', ')}; denial ${c.outcome.denial_codes.join(', ')}; left out ${c.outcome.excluded_codes.join(', ')}`, es: `aprobación ${c.outcome.approval_codes.join(', ')}; rechazo ${c.outcome.denial_codes.join(', ')}; excluidos ${c.outcome.excluded_codes.join(', ')}` }, lang)}</dd>
            </>,
            'codes',
          )}
          <dt>{pick({ en: 'Debt-to-income bins', es: 'Tramos de deuda sobre ingreso' }, lang)}</dt>
          <dd><Marked>{`${c.dti_recode.bins.join(', ')}. ${pick(c.dti_recode.note, lang)}`}</Marked></dd>
          <dt>{pick({ en: 'Groups left out of the pairwise tests', es: 'Grupos fuera de las pruebas de a pares' }, lang)}</dt>
          <dd><Marked>{pick(c.group_exclusion, lang)}</Marked></dd>
          <dt>{pick({ en: 'Identifiers', es: 'Identificadores' }, lang)}</dt>
          <dd data-status={c.identifiers.label}>{`${pick(c.identifiers.note, lang)} (${c.identifiers.id}; ${c.identifiers.observation_date})`}</dd>
        </dl>
      </PlotCard>
      <PlotCard title={{ en: 'The licence of the data', es: 'La licencia de los datos' }} {...card}>
        <dl className="ct-defs" data-table="c21-licence" data-status={l.status}>
          <dt>{pick({ en: 'Status', es: 'Estado' }, lang)}</dt>
          <dd>{`${l.status}: ${pick(l.note, lang)}`}</dd>
          <dt>{pick({ en: 'Platform terms', es: 'Términos de la plataforma' }, lang)}</dt>
          <dd><span translate="no" lang="en">{`"${l.platform_terms}"`}</span> (<Marked>{es(l.platform_terms_cover, lang)}</Marked>)</dd>
          <dt>{pick({ en: 'CFPB statement', es: 'Declaración de la CFPB' }, lang)}</dt>
          <dd><span translate="no" lang="en">{`"${l.modified_statement}"`}</span></dd>
        </dl>
      </PlotCard>
      <PlotCard title={{ en: 'How each field is published', es: 'Cómo se publica cada campo' }} {...card} note={{ en: 'A field the release bins, rounds, tops or withholds says so, with its reason; the public data carry no credit score.', es: 'Un campo que la publicación agrupa, redondea, trunca o retiene lo dice, con su razón; los datos públicos no traen puntaje de crédito.' }}>
        <div className="ct-scroll" data-caos-flow="">
          <table className="caos-table ct-wrap-head" data-table="c21-notes">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Field', es: 'Campo' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Treatment', es: 'Tratamiento' }, lang)}</th>
                <th>{pick({ en: 'Missing', es: 'Faltantes' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Reason', es: 'Razón' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.data_notes.map((n) => (
                <tr key={n.field} data-field={n.field}>
                  {/* the field by its name, its code in the public file beside it (a data dictionary) */}
                  <td className="ct-text">{DATA_FIELD_TEXT[n.field] ?? FIELD_TEXT[n.field] ?? CONTROL_TEXT[n.field] ? <>{pick(DATA_FIELD_TEXT[n.field] ?? FIELD_TEXT[n.field] ?? CONTROL_TEXT[n.field], lang)} <code translate="no">{n.field}</code></> : n.field}</td>
                  <td className="ct-text">{treatmentName(n.treatment, lang)}</td>
                  <td data-na={n.n_missing === null ? 'true' : undefined}>{n.n_missing === null ? formatNumber(null, lang) : int(n.n_missing, lang)}</td>
                  <td className="ct-text ct-wide-only">{pick(n.reason, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
    </div>
  );
}

// --- the read-outs of the rail ---------------------------------------------------------------------------------------

const hint = (en: string, es: string): BiText => ({ en, es });

/** The live read-out of the Attribute section: the legal basis named, the reference group and the highest-rate group. */
export function AttributeReadout({ sel }: { sel: C21Sel | null }) {
  const a = attributeFor(sel);
  const na: BiText = { en: formatNumber(null, 'en'), es: formatNumber(null, 'es') };
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel && a ? text(FIELD_TEXT, a.field) : { en: 'The attribute', es: 'El atributo' }}
      items={[
        { label: { en: 'Basis', es: 'Base' }, text: a ? text(BASIS_TEXT, a.legal.basis) : na, unitless: true, hint: hint('The prohibited basis the field maps to in the research addendum; no legal claim.', 'La base prohibida a la que se asigna el campo en el anexo de investigación; sin afirmación legal.') },
        { label: { en: 'Reference', es: 'Referencia' }, text: a ? groupBi(a.reference_group) : na, unitless: true, hint: hint('The group the contrasts compare with.', 'El grupo con el que comparan los contrastes.') },
        { label: { en: 'Highest rate', es: 'Mayor tasa' }, text: a ? groupBi(a.four_fifths.highest_rate_group) : na, unitless: true, hint: hint('The group the four-fifths line is measured against.', 'El grupo contra el que se mide la línea de cuatro quintos.') },
      ]}
    />
  );
}

/** The live read-out of the Group section: the rates, the ratio, the test and the controlled estimate of the group in focus. */
export function GroupReadout({ sel }: { sel: C21Sel | null }) {
  const c = contrastFor(sel);
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={c ? groupBi(c.group) : { en: 'The group', es: 'El grupo' }}
      items={[
        { label: { en: 'Approval rate', es: 'Tasa de aprobación' }, value: c?.selection_rate_group ?? null, unitless: true, format: { percent: true, decimals: 1 }, hint: hint('The share of the decided applications that were approved: an indicator only.', 'La parte de las solicitudes decididas que se aprobó: solo un indicador.') },
        { label: { en: 'Parity gap', es: 'Brecha de paridad' }, value: c?.parity_gap ?? null, unitless: true, format: { percent: true, decimals: 1 }, hint: hint('The rate of the group minus the rate of the reference group.', 'La tasa del grupo menos la tasa del grupo de referencia.') },
        { label: { en: 'Impact ratio', es: 'Razón de impacto' }, value: c?.adverse_impact_ratio.value ?? null, unitless: true, format: { decimals: 3 }, hint: hint('The group rate over the reference rate.', 'La tasa del grupo sobre la tasa de referencia.') },
        { label: { en: 'Controlled effect', es: 'Efecto controlado' }, value: c?.controlled.estimate?.coefficient ?? null, unitless: true, format: { decimals: 3 }, hint: hint('The coefficient of the group in the decision model with the permitted controls: an approximation of comparative evidence.', 'El coeficiente del grupo en el modelo de decisión con los controles permitidos: una aproximación de evidencia comparativa.') },
      ]}
    />
  );
}

export { f3, pc };
