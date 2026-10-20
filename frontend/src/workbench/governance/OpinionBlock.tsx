// The opinion of an entry (dossier 06 B.6, decisions W15-7 and W15-11) and the block of each case's Findings group: the
// opinion level of the case's inventory entries, read from their validation report documents, with the rule that gave it
// and the recommendation, labelled "the rule's output on the evidence; Contraste approves no model". A case without a
// governance document shows "not available yet" with its reason, never a guess. The opinion is the rule's output over the
// open findings, an evidence summary for a validator, never an approval or a certification.
import { Callout, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { useState, type ReactNode } from 'react';
import { Doc, GovernanceDoc } from './common';
import { unavailableBlock } from './states';
import {
  ECB_F_OF,
  GOVERNANCE_FILES,
  OPINION_NAME,
  RECOMMENDATION_NAME,
  reportFile,
  severityText,
  type GovInventory,
  type GovReport,
  type InvEntry,
  type ReportSection,
  type Severity,
} from './model';

export type Opinion = Extract<ReportSection, { number: 11 }>['opinion'];

/** The opinion of one entry: level, the rule, the open findings it was computed on and the labelled recommendation. */
export function OpinionCard({ opinion }: { opinion: Opinion }) {
  const lang = useShellLang();
  const bySeverity = (['S1', 'S2', 'S3', 'S4'] as Severity[]).map((s) => ({ s, n: opinion.open_findings.filter((f) => f.severity === s).length })).filter((x) => x.n > 0);
  const tone = opinion.level >= 4 ? 'honest' : opinion.level === 3 ? 'honest' : 'note';
  return (
    <div data-opinion data-level={opinion.level} data-outcome={opinion.recommendation.outcome}>
      <Callout variant={tone} title={`${pick({ en: 'Opinion level ', es: 'Nivel de opinión ' }, lang)}${opinion.level}: ${pick(OPINION_NAME[opinion.level] ?? opinion.level_label, lang)}`}>
        <p data-opinion-rule>
          {pick({ en: 'Rule ', es: 'Regla ' }, lang)}
          <span translate="no">{opinion.rule.id}</span>: <Doc t={opinion.rule.text} />
        </p>
        <p data-opinion-findings>
          {opinion.open_findings.length === 0
            ? pick({ en: 'No finding is open.', es: 'Ningún hallazgo está abierto.' }, lang)
            : `${pick({ en: 'Open findings: ', es: 'Hallazgos abiertos: ' }, lang)}${formatNumber(opinion.open_findings.length, lang, { decimals: 0 })} (${bySeverity.map((x) => `${severityText(x.s, ECB_F_OF[x.s], lang)}: ${formatNumber(x.n, lang, { decimals: 0 })}`).join('; ')})`}
          {opinion.rwea_cut_points_applied ? ` ${pick({ en: 'An RWEA cut point raised the level.', es: 'Un punto de corte de RWEA subió el nivel.' }, lang)}` : ''}
        </p>
        <p data-recommendation={opinion.recommendation.outcome}>
          <strong>{pick({ en: 'Recommendation: ', es: 'Recomendación: ' }, lang)}</strong>
          {pick(RECOMMENDATION_NAME[opinion.recommendation.outcome], lang)}. <Doc t={opinion.recommendation.text} />
        </p>
        <p data-rule-label>
          <em><Doc t={opinion.label} /></em>
        </p>
      </Callout>
    </div>
  );
}

/** The opinion of a report document: its section 11, or the reason it has none. */
export function ReportOpinion({ report }: { report: GovReport }) {
  const s = report.sections.find((x) => x.number === 11);
  if (!s || !('opinion' in s)) return unavailableBlock({ en: 'The report has no opinion section.', es: 'El informe no tiene sección de opinión.' });
  return <OpinionCard opinion={s.opinion} />;
}

/** The entries of a case in the inventory. */
export const entriesOf = (inv: GovInventory, caseId: string): InvEntry[] => inv.entries.filter((e) => e.case_id === caseId);

/** The block, from the inventory: one opinion per entry of the case, or the reason the case has none yet. */
export function OpinionBlockView({ caseId, inv }: { caseId: string; inv: GovInventory }) {
  const lang = useShellLang();
  const mine = entriesOf(inv, caseId);
  if (!mine.length) {
    const left = inv.excluded.find((x) => x.case_id === caseId);
    return unavailableBlock(
      left
        ? { en: `The inventory leaves ${caseId} out: ${left.reason.en}`, es: `El inventario deja fuera a ${caseId}: ${left.reason.es}` }
        : { en: `The inventory holds no entry of ${caseId} yet.`, es: `El inventario aún no tiene ninguna entrada de ${caseId}.` },
    );
  }
  return (
    <>
      {mine.map((e) => (
        <div key={e.key} data-opinion-entry={e.key}>
          {mine.length > 1 && (
            <h4>
              <span translate="no">{e.key}</span>: {pick(e.title, lang)}
            </h4>
          )}
          <GovernanceDoc<GovReport> file={reportFile(e.key)}>{(report) => <ReportOpinion report={report} />}</GovernanceDoc>
        </div>
      ))}
    </>
  );
}

/** The opinion block of a case's Findings group, from the governance documents: "not available yet" with the reason while a document is not written. */
export function OpinionBlock({ caseId }: { caseId: string }) {
  const lang = useShellLang();
  return (
    <section data-governance-opinion={caseId} style={{ minWidth: 0 }}>
      <h3 className="ct-sub">{pick({ en: 'Overall opinion on the evidence', es: 'Opinión global sobre la evidencia' }, lang)}</h3>
      <GovernanceDoc<GovInventory> file={GOVERNANCE_FILES.inventory}>{(inv) => <OpinionBlockView caseId={caseId} inv={inv} />}</GovernanceDoc>
    </section>
  );
}

/**
 * The Findings group of a case with its opinion: the group's own content keeps its height, and the opinion sits under it
 * in a disclosure that is one line when closed, so the instrument stays inside its panel (ADR-0071 rule 6); opened, the
 * opinion scrolls inside its own box. One registration point serves every case (Workbench.tsx, the patch in changes/U15-W.md).
 */
export function FindingsWithOpinion({ caseId, children }: { caseId: string; children: ReactNode }) {
  const lang = useShellLang();
  // the governance documents are read when the reader opens the disclosure, not when the group opens: a case page makes no
  // request (and no 404 while the bake has not written them) for an opinion nobody asked to read
  const [opened, setOpened] = useState(false);
  return (
    <div className="ct-part" data-findings-with-opinion={caseId} style={{ height: '100%', gap: 0 }}>
      <div className="ct-part ct-part-3">{children}</div>
      <details className="ct-note" data-opinion-disclosure onToggle={(e) => { if ((e.currentTarget as HTMLDetailsElement).open) setOpened(true); }} style={{ margin: 0, fontSize: '0.72rem', lineHeight: 1, padding: 0 }}>
        <summary>{pick({ en: 'Overall opinion on the evidence (governance)', es: 'Opinión global sobre la evidencia (gobernanza)' }, lang)}</summary>
        <div style={{ maxHeight: 260, overflow: 'auto', minWidth: 0 }}>
          {opened ? <OpinionBlock caseId={caseId} /> : null}
        </div>
      </details>
    </div>
  );
}
