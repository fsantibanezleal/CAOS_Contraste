// The "Findings and appetite" tab (U15-W): the findings register across cases, sortable, with the product's severity
// shown beside its ECB F equivalent (decision W15-2), the status beside the product status it came from (W15-5), the
// quantitative anchor or its absence with the reason (W15-5), and the due date, ageing and overdue flag; beside it the
// severity-by-status bars and the ageing of the findings not closed; and the seven B.6 model risk appetite metrics, each
// with its light, value, distinct-finding count and register-row count (W15-14) and its convention label. Every number
// is read from findings.json and appetite.json; a missing document is the declared "not available yet" state.
import { BarChart, PlotCard, formatNumber, pick, useShellLang, type BarDatum, type BiText } from '@fasl-work/caos-app-shell';
import { useMemo, useState } from 'react';
import { P } from '../../content/bi';
import { LIGHT_TEXT } from '../../lib/policy';
import { AsOf, Basis, ConventionNote, Doc, GovernanceDoc, Tag } from './common';
import {
  GOVERNANCE_FILES,
  PRODUCT_STATUS_NAME,
  STATUS_NAME,
  ageingBins,
  severityByStatus,
  severityText,
  sortRows,
  type AppetiteMetric,
  type FindingRow,
  type GovAppetite,
  type GovFindings,
  type SortKey,
} from './model';

const COLUMNS: Array<{ key: SortKey; label: BiText }> = [
  { key: 'entry', label: { en: 'Entry', es: 'Entrada' } },
  { key: 'severity', label: { en: 'Severity, with its ECB F equivalent', es: 'Severidad, con su equivalente F del BCE' } },
  { key: 'status', label: { en: 'Status, and the product status it came from', es: 'Estado, y el estado del producto del que viene' } },
  { key: 'anchor', label: { en: 'Anchor', es: 'Ancla' } },
  { key: 'due', label: { en: 'Due', es: 'Vence' } },
  { key: 'ageing', label: { en: 'Ageing', es: 'Antigüedad' } },
];

/** The segment colour of a status in the stacked bars: open warns, a stated limit is faint, a closed finding is good. */
const STATUS_FILL: Record<string, string> = {
  open: 'var(--color-warn)',
  action_plan_agreed: 'var(--color-accent-2)',
  in_progress: 'var(--color-accent)',
  submitted_for_closure: 'var(--color-magenta)',
  validated_closed: 'var(--color-good)',
  overdue: 'var(--color-bad)',
  risk_accepted: 'var(--color-fg-faint)',
};

function AnchorCell({ row }: { row: FindingRow }) {
  const lang = useShellLang();
  if (row.anchor) {
    const a = row.anchor;
    return (
      <>
        {pick(a.metric === 'statistic' ? { en: 'statistic', es: 'estadístico' } : { en: 'metric', es: 'métrica' }, lang)} {formatNumber(a.value, lang, { digits: 4 })}
        <br />
        <span translate="no" title={a.basis}>
          {a.test_id}@{a.model_id}
        </span>
      </>
    );
  }
  return (
    <span data-anchor="unavailable">
      {pick({ en: 'not available: ', es: 'no disponible: ' }, lang)}
      {row.anchor_reason ? <Doc t={row.anchor_reason} /> : ''}
    </span>
  );
}

/** The register: sortable by column, the document's order kept on ties. */
export function RegisterTable({ rows }: { rows: FindingRow[] }) {
  const lang = useShellLang();
  const [sort, setSort] = useState<{ key: SortKey; dir: 'asc' | 'desc' }>({ key: 'severity', dir: 'asc' });
  const sorted = useMemo(() => sortRows(rows, sort.key, sort.dir), [rows, sort]);
  return (
    <div style={{ maxHeight: 520, overflow: 'auto', minWidth: 0 }}>
      <table className="caos-table" data-state="ready" data-register data-rows={rows.length}>
        <thead>
          <tr>
            {COLUMNS.map((c) => (
              <th key={c.key} className="caos-col-text" aria-sort={sort.key === c.key ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none'}>
                <button type="button" className="ct-linkbutton" data-sort={c.key} onClick={() => setSort((s) => ({ key: c.key, dir: s.key === c.key && s.dir === 'asc' ? 'desc' : 'asc' }))}>
                  {pick(c.label, lang)}
                  {sort.key === c.key ? (sort.dir === 'asc' ? ' (+)' : ' (-)') : ''}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={r.key} data-finding={r.key} data-severity={r.severity} data-status={r.status} data-overdue={r.overdue ? 'true' : 'false'}>
              <td className="caos-col-text">
                <span translate="no">{r.entry_key}</span>
                <br />
                <span translate="no">{r.id}</span>
              </td>
              <td className="caos-col-text">{severityText(r.severity, r.ecb_f, lang)}</td>
              <td className="caos-col-text">
                {pick(STATUS_NAME[r.status] ?? { en: r.status, es: r.status }, lang)}
                <br />
                <span className="ct-note">
                  {pick({ en: 'product status: ', es: 'estado del producto: ' }, lang)}
                  {pick(PRODUCT_STATUS_NAME[r.product_status] ?? { en: r.product_status, es: r.product_status }, lang)}
                </span>
              </td>
              <td className="caos-col-text">
                <AnchorCell row={r} />
              </td>
              <td className="caos-col-text">
                {r.due}
                {r.overdue ? <strong> {pick({ en: '(overdue)', es: '(vencido)' }, lang)}</strong> : null}
              </td>
              <td>
                {formatNumber(r.ageing_days, lang, { decimals: 0 })} {pick({ en: 'days', es: 'días' }, lang)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Severity by status as stacked bars: one bar per severity, one segment per status, its width in proportion to its count. */
export function SeverityStatusBars({ rows }: { rows: FindingRow[] }) {
  const lang = useShellLang();
  const data = severityByStatus(rows);
  const max = Math.max(1, ...data.map((d) => d.total));
  const statuses = Object.keys(STATUS_NAME).filter((s) => data.some((d) => d.byStatus[s]));
  const ecb = (sev: string) => rows.find((r) => r.severity === sev)?.ecb_f ?? '';
  return (
    <div data-stacked-bars>
      {data.map((d) => (
        <div key={d.severity} data-severity-bar={d.severity} data-total={d.total} style={{ display: 'grid', gridTemplateColumns: 'minmax(7rem, 11rem) 1fr', alignItems: 'center', gap: '0.5rem', margin: '0.35rem 0', minWidth: 0 }}>
          <span>{severityText(d.severity, ecb(d.severity), lang)}</span>
          <div
            role="img"
            aria-label={`${d.severity}: ${statuses.filter((s) => d.byStatus[s]).map((s) => `${pick(STATUS_NAME[s], lang)} ${d.byStatus[s]}`).join(', ') || '0'}`}
            style={{ display: 'flex', height: 22, width: `${(d.total / max) * 100}%`, minWidth: d.total ? 22 : 0, background: 'var(--color-surface-2)', borderRadius: 3, overflow: 'hidden' }}
          >
            {statuses.map((s) =>
              d.byStatus[s] ? (
                <span key={s} data-segment={s} title={`${pick(STATUS_NAME[s], lang)}: ${d.byStatus[s]}`} style={{ flex: d.byStatus[s], background: STATUS_FILL[s], display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-bg)', fontSize: 11, fontWeight: 600, minWidth: 0 }}>
                  {formatNumber(d.byStatus[s], lang, { decimals: 0 })}
                </span>
              ) : null,
            )}
          </div>
        </div>
      ))}
      <ul className="ct-evidence" style={{ listStyle: 'none', paddingLeft: 0, display: 'flex', flexWrap: 'wrap', gap: '0.3rem 1rem' }}>
        {statuses.map((s) => (
          <li key={s}>
            <span aria-hidden style={{ display: 'inline-block', width: 12, height: 12, background: STATUS_FILL[s], marginRight: 6, verticalAlign: 'middle' }} />
            {pick(STATUS_NAME[s], lang)}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** The ageing of the findings not closed, in bins of thirty days; a bin that holds an overdue finding is flagged. */
export function AgeingChart({ rows }: { rows: FindingRow[] }) {
  const lang = useShellLang();
  const bins = ageingBins(rows);
  if (!bins.length) return <p className="caos-pending" data-state="unavailable">{pick({ en: 'No finding is open: there is nothing to age.', es: 'Ningún hallazgo está abierto: no hay nada que envejecer.' }, lang)}</p>;
  const data: BarDatum[] = bins.map((b) => ({
    id: `${b.from}`,
    label: { en: `${b.from} to ${b.to} days`, es: `${b.from} a ${b.to} días` },
    value: b.count,
    tone: b.overdue > 0 ? 'bad' : 'accent',
    hint: { en: `${b.count} findings not closed, ${b.overdue} overdue`, es: `${b.count} hallazgos no cerrados, ${b.overdue} vencidos` },
  }));
  return (
    <BarChart
      title={{ en: 'Findings not closed, by age', es: 'Hallazgos no cerrados, por antigüedad' }}
      data={data}
      axis={{ label: { en: 'Findings', es: 'Hallazgos' }, format: { decimals: 0 } }}
    />
  );
}

const fmtMetric = (m: AppetiteMetric, v: number | null, lang: 'en' | 'es'): string => {
  if (v === null) return pick({ en: 'not available', es: 'no disponible' }, lang);
  if (m.unit === 'count') return formatNumber(v, lang, { decimals: 0 });
  return formatNumber(v, lang, { percent: true, decimals: m.kind === 'magnitude' ? 2 : 0 });
};

/** A threshold written in words from its direction and limits; it is the document's convention, never a regulatory value. */
function thresholdText(m: AppetiteMetric, lang: 'en' | 'es'): string {
  const t = m.threshold;
  const g = fmtMetric(m, t.green_limit, lang);
  const a = fmtMetric(m, t.amber_limit, lang);
  return t.direction === 'higher-is-better'
    ? pick({ en: `green from ${g}, amber from ${a}`, es: `verde desde ${g}, ámbar desde ${a}` }, lang)
    : pick({ en: `green up to ${g}, amber up to ${a}`, es: `verde hasta ${g}, ámbar hasta ${a}` }, lang);
}

/** The seven B.6 metrics: light, value, distinct-finding count and register-row count (W15-14), threshold with its convention label. */
export function AppetiteTable({ appetite }: { appetite: GovAppetite }) {
  const lang = useShellLang();
  return (
    <div style={{ overflowX: 'auto', minWidth: 0 }}>
      <table className="caos-table" data-state="ready" data-appetite data-metrics={appetite.metrics.length}>
        <thead>
          <tr>
            <th className="caos-col-text">{pick({ en: 'Metric', es: 'Métrica' }, lang)}</th>
            <th>{pick({ en: 'Light', es: 'Luz' }, lang)}</th>
            <th>{pick({ en: 'Value', es: 'Valor' }, lang)}</th>
            <th>{pick({ en: 'Distinct findings or entries', es: 'Hallazgos distintos o entradas' }, lang)}</th>
            <th>{pick({ en: 'Register rows', es: 'Filas del registro' }, lang)}</th>
            <th className="caos-col-text">{pick({ en: 'Threshold (a convention)', es: 'Umbral (una convención)' }, lang)}</th>
          </tr>
        </thead>
        <tbody>
          {appetite.metrics.map((m) => (
            <tr key={m.id} data-metric={m.id} data-light={m.light}>
              <td className="caos-col-text">{pick(m.name, lang)}</td>
              <td className={`ct-light ct-light-${m.light}`}>
                <span className="ct-light-word">{pick(LIGHT_TEXT[m.light], lang)}</span>
              </td>
              <td>{fmtMetric(m, m.value, lang)}</td>
              <td>
                {m.kind === 'magnitude' || m.numerator === null || m.denominator === null
                  ? '-'
                  : `${formatNumber(m.numerator, lang, { decimals: 0 })} ${pick({ en: 'of', es: 'de' }, lang)} ${formatNumber(m.denominator, lang, { decimals: 0 })}`}
              </td>
              <td>{m.register_rows === null ? '-' : formatNumber(m.register_rows, lang, { decimals: 0 })}</td>
              <td className="caos-col-text">
                <Tag tag={m.threshold.label} />: {thresholdText(m, lang)}
                {m.reason ? <><br /><Doc t={m.reason} /></> : null}
                <Basis label={pick(m.name, lang)} text={m.threshold.basis} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** The register and its charts, drawn from the findings document. */
export function RegisterSection({ findings }: { findings: GovFindings }) {
  const lang = useShellLang();
  const n = (v: number) => formatNumber(v, lang, { decimals: 0 });
  return (
    <>
      <P
        en="The findings register gathers the findings of every case's variant documents in one table, with what the validation workflow needs and the case documents do not hold: the quantitative anchor where the evidence is a test row, the owner role, the due date from the deadline table, and the ageing. The product's severity direction is kept (S1 critical to S4 minor) and every severity is shown beside its ECB F equivalent. The register enriches the findings; it rewrites no case document."
        es="El registro de hallazgos reúne en una tabla los hallazgos de los documentos de variante de cada caso, con lo que el flujo de validación necesita y los documentos de los casos no tienen: el ancla cuantitativa donde la evidencia es una fila de prueba, el rol responsable, la fecha de vencimiento de la tabla de plazos y la antigüedad. Se mantiene la dirección de severidad del producto (S1 crítico a S4 menor) y cada severidad se muestra junto a su equivalente F del BCE. El registro enriquece los hallazgos; no reescribe ningún documento de caso."
      />
      <p data-register-summary>
        {pick(
          {
            en: `${n(findings.counts.total)} register rows, ${n(findings.counts.overdue)} of them overdue as of the date below.`,
            es: `${n(findings.counts.total)} filas del registro, ${n(findings.counts.overdue)} de ellas vencidas a la fecha de abajo.`,
          },
          lang,
        )}
      </p>
      <ConventionNote />
      <AsOf asOf={findings.as_of} basis={findings.as_of_basis} />
      <PlotCard title={{ en: 'The findings register', es: 'El registro de hallazgos' }} lane="replay" provenance="synthetic" note={{ en: 'Sort by any column. A due date is the raised date plus the deadline of its severity and tier, a stated convention.', es: 'Ordene por cualquier columna. Una fecha de vencimiento es la fecha de levantamiento más el plazo de su severidad y nivel, una convención declarada.' }}>
        <RegisterTable rows={findings.rows} />
      </PlotCard>
      <PlotCard title={{ en: 'Severity by status', es: 'Severidad por estado' }} lane="replay" provenance="synthetic">
        <SeverityStatusBars rows={findings.rows} />
      </PlotCard>
      <PlotCard title={{ en: 'Ageing of the findings not closed', es: 'Antigüedad de los hallazgos no cerrados' }} lane="replay" provenance="synthetic" note={{ en: 'A bar in the alert colour holds at least one overdue finding.', es: 'Una barra en el color de alerta contiene al menos un hallazgo vencido.' }}>
        <AgeingChart rows={findings.rows} />
      </PlotCard>
    </>
  );
}

/** The appetite metrics, drawn from the appetite document. */
export function AppetiteSection({ appetite }: { appetite: GovAppetite }) {
  const lang = useShellLang();
  const n = (v: number) => formatNumber(v, lang, { decimals: 0 });
  return (
    <>
      <h3 className="ct-sub">{pick({ en: 'The model risk appetite', es: 'El apetito de riesgo de modelo' }, lang)}</h3>
      <P
        en="Seven metrics of the model risk appetite (dossier 06 B.6). The count metrics count distinct findings, which is what the appetite states; the register rows behind them are shown beside. Each light follows a threshold that is a convention of Contraste."
        es="Siete métricas del apetito de riesgo de modelo (dossier 06 B.6). Las métricas de conteo cuentan hallazgos distintos, que es lo que el apetito declara; las filas del registro detrás de ellas se muestran al lado. Cada luz sigue un umbral que es una convención de Contraste."
      />
      <p data-appetite-population>
        {pick(
          {
            en: `${n(appetite.population.distinct_findings)} distinct findings (${n(appetite.population.findings)} register rows) across ${n(appetite.population.entries)} entries, ${n(appetite.population.tier1_entries)} of them Tier 1.`,
            es: `${n(appetite.population.distinct_findings)} hallazgos distintos (${n(appetite.population.findings)} filas del registro) en ${n(appetite.population.entries)} entradas, ${n(appetite.population.tier1_entries)} de ellas de Nivel 1.`,
          },
          lang,
        )}
      </p>
      <AsOf asOf={appetite.as_of} basis={appetite.as_of_basis} />
      <AppetiteTable appetite={appetite} />
    </>
  );
}

/** Both sections from their documents, for a test that has both. */
export function FindingsTab({ findings, appetite }: { findings: GovFindings; appetite: GovAppetite }) {
  return (
    <>
      <RegisterSection findings={findings} />
      <AppetiteSection appetite={appetite} />
    </>
  );
}

/** The tab: each document in its own declared state, so a missing appetite never hides the register. */
export function FindingsTabLoader() {
  return (
    <>
      <GovernanceDoc<GovFindings> file={GOVERNANCE_FILES.findings}>{(findings) => <RegisterSection findings={findings} />}</GovernanceDoc>
      <GovernanceDoc<GovAppetite> file={GOVERNANCE_FILES.appetite}>{(appetite) => <AppetiteSection appetite={appetite} />}</GovernanceDoc>
    </>
  );
}
