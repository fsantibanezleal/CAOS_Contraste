// The "Reports" tab as a document that fits its sized box (GATE-15B): the validation report of one inventory entry has twelve
// sections and about 14,000 px; here one section is read at a time, chosen by a select or stepped with the page bar (the
// shell's deck window), the position ("3 of 12") always stated. Every section stays reachable: the select lists all twelve
// with their status. The report header, the as-of line, the section and the opinion block are the governance views' own
// (`ReportDocument` handed the one section, `SectionView` inside it), unchanged.
import { pick, useShellLang } from '@fasl-work/caos-app-shell';
import { useId, useState } from 'react';
import { P } from '../../content/bi';
import { ConventionNote, GovernanceDoc } from '../../workbench/governance/common';
import { ReportDocument } from '../../workbench/governance/ReportView';
import { GOVERNANCE_FILES, entryLabel, reportFile, type GovFindings, type GovInventory, type GovReport } from '../../workbench/governance/model';
import { RowPager } from './RowPager';

/** One section of a report at a time: the select of the sections, the page bar and the report restricted to the chosen section. */
export function PagedReport({ report, findings, initial = 0 }: { report: GovReport; findings?: GovFindings; initial?: number }) {
  const lang = useShellLang();
  const id = useId();
  const [at, setAt] = useState(initial);
  const n = report.sections.length;
  const i = Math.min(Math.max(0, at), Math.max(0, n - 1));
  const section = report.sections[i];
  return (
    <div data-report-paged data-section-at={i + 1} data-section-count={n}>
      <p>
        <label htmlFor={id}>{pick({ en: 'Section of the report: ', es: 'Sección del informe: ' }, lang)}</label>
        <select id={id} value={i} onChange={(e) => setAt(Number(e.target.value))} data-report-section-select style={{ maxWidth: '100%' }}>
          {report.sections.map((s, k) => (
            <option key={s.number} value={k}>
              {s.number}. {pick(s.title, lang)} ({pick(s.status === 'filled' ? { en: 'filled', es: 'completa' } : { en: 'absent', es: 'ausente' }, lang)})
            </option>
          ))}
        </select>
      </p>
      <RowPager n={n} per={1} start={i} onStart={setAt} label={pick({ en: 'Report section', es: 'Sección del informe' }, lang)} />
      {section ? <ReportDocument report={{ ...report, sections: [section] as unknown as GovReport['sections'] }} findings={findings} /> : null}
    </div>
  );
}

/** The select of the entries and the report of the chosen one, a section at a time. */
export function PagedReportReader({ inv }: { inv: GovInventory }) {
  const lang = useShellLang();
  const id = useId();
  const [key, setKey] = useState(inv.entries[0]?.key ?? '');
  if (!inv.entries.length) {
    return (
      <p className="caos-pending" data-state="unavailable">
        {pick({ en: 'Not available yet. The inventory holds no entry, so there is no report to read.', es: 'Aún no disponible. El inventario no tiene ninguna entrada, por lo que no hay informe que leer.' }, lang)}
      </p>
    );
  }
  return (
    <>
      <p>
        <label htmlFor={id}>{pick({ en: 'Inventory entry: ', es: 'Entrada del inventario: ' }, lang)}</label>
        <select id={id} value={key} onChange={(e) => setKey(e.target.value)} data-report-select style={{ maxWidth: '100%' }}>
          {inv.entries.map((e) => (
            <option key={e.key} value={e.key}>
              {entryLabel(e, lang)}
            </option>
          ))}
        </select>
      </p>
      <GovernanceDoc<GovReport> key={key} file={reportFile(key)}>
        {(report) => <GovernanceDoc<GovFindings> file={GOVERNANCE_FILES.findings}>{(findings) => <PagedReport report={report} findings={findings} />}</GovernanceDoc>}
      </GovernanceDoc>
    </>
  );
}

/** The tab: the text of the governance view, the inventory (for the select) and then the report of the chosen entry, each in its declared state. */
export function PagedReportsTabLoader() {
  return (
    <>
      <P
        en="One validation report per inventory entry, in the twelve sections of the template of dossier 06 I.3. A section is filled from named inputs, or absent with its reason, and what the template asks for and Contraste holds nothing behind is listed as not available. Section 11 gives the opinion on the ECB four-level scale as the output of a stated rule: it is not an approval."
        es="Un informe de validación por entrada del inventario, en las doce secciones de la plantilla del dossier 06 I.3. Una sección se completa con insumos nombrados, o queda ausente con su razón, y lo que la plantilla pide y Contraste no tiene detrás se lista como no disponible. La sección 11 da la opinión en la escala de cuatro niveles del BCE como resultado de una regla declarada: no es una aprobación."
      />
      <P
        en="Pick an entry to read its report, one section at a time: the select lists the twelve sections and the buttons step through them. Each section names the inputs it was assembled from, in a fold under it: a committed document, an engine function or a stated convention. A section that is filled can still list elements of the template that Contraste holds nothing behind, such as a written soundness assessment or a monitoring pack; those are not invented, they are listed as not available with the reason. The report of an entry that has not been written yet is shown as not available yet, with the file that is missing."
        es="Elija una entrada para leer su informe, una sección a la vez: el selector lista las doce secciones y los botones las recorren. Cada sección nombra los insumos con que se armó, en un pliegue bajo ella: un documento versionado, una función del motor o una convención declarada. Una sección completa puede igualmente listar elementos de la plantilla que Contraste no tiene detrás, como una evaluación escrita de solidez o un paquete de monitoreo; no se inventan, se listan como no disponibles con su razón. El informe de una entrada que la generación no ha escrito se muestra como aún no disponible, con el archivo que falta."
      />
      <ConventionNote />
      <GovernanceDoc<GovInventory> file={GOVERNANCE_FILES.inventory}>{(inv) => <PagedReportReader inv={inv} />}</GovernanceDoc>
    </>
  );
}
