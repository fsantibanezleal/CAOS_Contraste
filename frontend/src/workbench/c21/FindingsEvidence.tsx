// C21's Findings group, second card: the evidence each finding cites, drawn. Every finding that cites a
// fair.conditional_disparity row gets the controlled odds ratio of that contrast (the line at 1 is no disparity), and a
// fair.rate_spread_disparity row the coefficient in percentage points (the line at 0). Each value is the `metric` of the
// document's row; a cited row the document lacks is listed as not available with its id. A finding that cites only a
// design limit draws nothing. An approximation of comparative evidence, never a legal claim.
import type { CSSProperties, ReactNode } from 'react';
import { PlotCard, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import type { Finding, TestRow, VariantArtifact } from '../../lib/contract.types';
import { useCard } from '../c03/U6Shared';
import { f3 } from '../c20/U14Common';
import { FIELD_TEXT, contrastText, text } from './selection';

export type EvidenceKind = 'odds-ratio' | 'rate-spread';
export interface EvidenceRow {
  finding: string;
  kind: EvidenceKind;
  /** The cited id, `test_id@model_id@segment`. */
  id: string;
  field: string;
  contrast: string;
  /** The `metric` of the document's row; null when the document lacks the row or the row carries no number. */
  metric: number | null;
}

const KIND_OF: Record<string, EvidenceKind> = { 'fair.conditional_disparity': 'odds-ratio', 'fair.rate_spread_disparity': 'rate-spread' };
const ORDER = ['S1', 'S2', 'S3', 'S4'];
const TOKENS = ['--color-accent', '--color-magenta', '--color-warn', '--color-good', '--color-accent-2', '--color-bad'] as const;

/** The cited rows of the controlled and rate-spread tests, by finding in severity order, read from the document only. */
export function evidenceOf(variant: Pick<VariantArtifact, 'findings' | 'tests'>): { findings: Finding[]; rows: EvidenceRow[]; designOnly: Finding[] } {
  const findings = [...variant.findings].sort((a, b) => ORDER.indexOf(a.severity) - ORDER.indexOf(b.severity));
  const find = (t: string, m: string, s: string): TestRow | undefined => variant.tests.find((r) => r.test_id === t && r.model_id === m && r.segment === s);
  const rows = findings.flatMap((f) =>
    f.evidence.flatMap((e): EvidenceRow[] => {
      const [t, m, ...rest] = e.split('@');
      const kind = KIND_OF[t];
      if (!kind || m === undefined) return [];
      const seg = rest.join('@');
      const [field, contrast = seg] = seg.split('|');
      const metric = find(t, m, seg)?.metric;
      return [{ finding: f.id, kind, id: e, field, contrast, metric: typeof metric === 'number' && Number.isFinite(metric) ? metric : null }];
    }),
  );
  const designOnly = findings.filter((f) => f.evidence.length > 0 && f.evidence.every((e) => e.startsWith('design:')));
  return { findings, rows, designOnly };
}

const KIND_TEXT: Record<EvidenceKind, { title: BiText; axis: BiText; line: BiText; at: number; log: boolean }> = {
  'odds-ratio': {
    title: { en: 'Controlled odds ratio of each cited contrast', es: 'Razón de odds controlada de cada contraste citado' },
    axis: { en: 'Odds ratio', es: 'Razón de odds' },
    line: { en: 'No disparity (1)', es: 'Sin disparidad (1)' },
    at: 1,
    log: false,
  },
  'rate-spread': {
    title: { en: 'Rate-spread coefficient of each cited contrast', es: 'Coeficiente del diferencial de tasa de cada contraste citado' },
    axis: { en: 'Spread (pp)', es: 'Diferencial (pp)' },
    line: { en: 'No difference (0)', es: 'Sin diferencia (0)' },
    at: 0,
    log: false,
  },
};

function EvidenceChart({ kind, rows, findings, lang }: { kind: EvidenceKind; rows: EvidenceRow[]; findings: Finding[]; lang: 'en' | 'es' }) {
  const k = KIND_TEXT[kind];
  if (!rows.some((r) => r.metric !== null)) {
    return <p className="ct-note" data-state="unavailable">{pick({ en: 'Not available: no cited row of this kind carries a number.', es: 'No disponible: ninguna fila citada de este tipo trae un número.' }, lang)}</p>;
  }
  const ids = findings.filter((f) => rows.some((r) => r.finding === f.id && r.metric !== null));
  return (
    <UPlotChart
      height="fill"
      x={{ values: rows.map((_, i) => i + 1), label: { en: 'Row of the table below', es: 'Fila de la tabla de abajo' }, format: { decimals: 0 } }}
      y={{ label: k.axis, format: { decimals: 2 }, log: k.log }}
      yMarks={[{ y: k.at, label: k.line, tone: 'neutral' }]}
      series={ids.map((f, i) => ({
        label: { en: f.id, es: f.id },
        values: rows.map((r) => (r.finding === f.id ? r.metric : null)),
        color: TOKENS[i % TOKENS.length],
        mode: 'points' as const,
        size: 11,
      }))}
    />
  );
}

/** `footer` is the text the view keeps under the evidence (the legal sentences), so the cards take the height of the group. */
export function FindingsEvidenceCard({ variant, footer }: { variant: VariantArtifact; footer?: ReactNode }) {
  const lang = useShellLang();
  const card = useCard(variant);
  const { findings, rows, designOnly } = evidenceOf(variant);
  if (findings.length === 0) return null;
  const kinds = (['odds-ratio', 'rate-spread'] as const).filter((k) => rows.some((r) => r.kind === k));
  const note: BiText = {
    en: 'A ratio below 1 is approval at lower controlled odds than the reference group, and above 1 at higher odds; a rate-spread coefficient above 0 is a higher spread. The estimates are approximations of comparative evidence, controlled for the permitted underwriting fields with the credit score missing from the public data: no legal claim.',
    es: 'Una razón bajo 1 es aprobación con menores odds controlados que el grupo de referencia, y sobre 1 con mayores odds; un coeficiente de diferencial de tasa sobre 0 es un diferencial mayor. Las estimaciones son aproximaciones de evidencia comparativa, controladas por los campos de suscripción permitidos y sin el puntaje de crédito, que falta en los datos públicos: sin afirmación legal.',
  };
  return (
    <PlotCard fill title={{ en: 'The evidence of each finding', es: 'La evidencia de cada hallazgo' }} {...card} note={note}>
      <div className="ct-stack" data-block="finding-evidence">
        {kinds.length === 0 ? (
          <p className="ct-note" data-state="unavailable">{pick({ en: 'No finding of this variant cites a controlled or rate-spread row.', es: 'Ningún hallazgo de esta variante cita una fila controlada o de diferencial de tasa.' }, lang)}</p>
        ) : null}
        {kinds.map((kind) => (
          <div key={kind} className="ct-stack-chart" data-evidence-chart={kind} data-reference-line={KIND_TEXT[kind].at} style={{ minHeight: '15rem', '--ct-chart-min': '15rem' } as CSSProperties}>
            <p className="ct-note">{pick(KIND_TEXT[kind].title, lang)}</p>
            <div style={{ flex: '1 1 0', minHeight: 0, display: 'flex', flexDirection: 'column' }}>
              <EvidenceChart kind={kind} rows={rows.filter((r) => r.kind === kind)} findings={findings} lang={lang} />
            </div>
          </div>
        ))}
        <div className="ct-stack-table">
          {kinds.length > 0 ? (
            <table className="caos-table ct-wrap-head" data-table="finding-evidence">
              <thead>
                <tr>
                  <th>{pick({ en: 'Row', es: 'Fila' }, lang)}</th>
                  <th className="ct-text ct-wide-only">{pick({ en: 'Finding', es: 'Hallazgo' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Contrast', es: 'Contraste' }, lang)}</th>
                  <th>{pick({ en: 'Value', es: 'Valor' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {kinds.flatMap((kind) =>
                  rows
                    .filter((r) => r.kind === kind)
                    .map((r, i) => (
                      <tr key={`${r.finding}|${r.id}`} data-evidence-kind={kind} data-evidence-row={r.id} data-finding={r.finding} data-metric={r.metric ?? undefined} data-na={r.metric === null ? 'true' : undefined}>
                        <td>{`${kind === 'odds-ratio' ? 'OR' : 'pp'} ${i + 1}`}</td>
                        <td className="ct-text ct-wide-only">{r.finding}</td>
                        <td className="ct-text">{`${pick(text(FIELD_TEXT, r.field), lang)}: ${contrastText(r.contrast, lang)}`}</td>
                        <td>{r.metric === null ? `${formatNumber(null, lang)} (${r.id})` : f3(r.metric, lang)}</td>
                      </tr>
                    )),
                )}
              </tbody>
            </table>
          ) : null}
          {designOnly.length > 0 ? (
            <p className="ct-note" data-note="design-only">
              {pick({ en: 'Accepted limits draw nothing, because they rest on a design limit and no test row: ', es: 'Los límites aceptados no dibujan nada, porque se apoyan en un límite de diseño y no en una fila de prueba: ' }, lang)}
              {designOnly.map((f) => f.id).join(', ')}.
            </p>
          ) : null}
          {footer}
        </div>
      </div>
    </PlotCard>
  );
}
