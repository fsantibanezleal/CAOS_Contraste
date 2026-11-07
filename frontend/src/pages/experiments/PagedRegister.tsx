// The "Findings and appetite" tab as a document that fits its sized box (GATE-15B, ADR-0071 and ADR-0017.2): the register of
// 732 findings was one table of 70,231 px in a 520 px box. Here it is filtered by severity and by the question family of the
// finding's case (`ChipGroup`, with the count each choice shows) and read a page at a time (`RowPager`, the shell's deck
// window), the position always stated. The table, the charts and the appetite are the governance views' own parts
// (`RegisterTable`, `SeverityStatusBars`, `AgeingChart`, `AppetiteSection`), unchanged; the severity bars and the ageing
// chart keep drawing the whole register, because they summarise it. The sort buttons of the table order the rows of the
// page shown: the pages themselves follow severity, S1 first, then the document's order.
import { ChipGroup, PlotCard, formatNumber, pick, useShellLang, type BiText, type ChipOption } from '@fasl-work/caos-app-shell';
import { useState } from 'react';
import { P } from '../../content/bi';
import { AsOf, ConventionNote, GovernanceDoc } from '../../workbench/governance/common';
import { AgeingChart, AppetiteSection, RegisterTable, SeverityStatusBars } from '../../workbench/governance/RegisterView';
import { GOVERNANCE_FILES, SEVERITY_NAME, useGovernance, type FindingRow, type GovAppetite, type GovFindings } from '../../workbench/governance/model';
import { RowPager } from './RowPager';
import { ALL, REGISTER_PER_PAGE, SEVERITIES, familyOptions, registerView, severityCounts, type RegisterFilter } from './registerPaging';

const bi = (en: string, es: string): BiText => ({ en, es });

/** The filters, the count of what they hide, the page of rows and its bar. `initial` seeds the state (tests, a deep link). */
export function RegisterBrowser({ rows, initial, per = REGISTER_PER_PAGE }: { rows: FindingRow[]; initial?: Partial<RegisterFilter> & { start?: number }; per?: number }) {
  const lang = useShellLang();
  const [filter, setFilter] = useState<RegisterFilter>({ severity: initial?.severity ?? ALL, family: initial?.family ?? ALL });
  const [start, setStart] = useState(initial?.start ?? 0);
  const n = (v: number) => formatNumber(v, lang, { decimals: 0 });
  const view = registerView(rows, filter, start, per);
  const bySeverity = severityCounts(rows, filter.family);
  const families = familyOptions(rows, filter.severity);
  const total = rows.length;
  const severityChips: ChipOption[] = [
    { id: ALL, label: bi(`All (${n(Object.values(bySeverity).reduce((a, b) => a + b, 0))})`, `Todas (${n(Object.values(bySeverity).reduce((a, b) => a + b, 0))})`) },
    ...SEVERITIES.map((s) => ({ id: s, label: bi(`${s} ${SEVERITY_NAME[s].en} (${n(bySeverity[s])})`, `${s} ${SEVERITY_NAME[s].es} (${n(bySeverity[s])})`), disabled: false })),
  ];
  const familyChips: ChipOption[] = [
    { id: ALL, label: bi(`All (${n(families.reduce((a, f) => a + f.count, 0))})`, `Todas (${n(families.reduce((a, f) => a + f.count, 0))})`) },
    ...families.map((f) => ({ id: f.id, label: bi(`${pick(f.label, 'en')} (${n(f.count)})`, `${pick(f.label, 'es')} (${n(f.count)})`) })),
  ];
  const change = (next: RegisterFilter) => {
    setFilter(next);
    setStart(0);
  };
  const filtered = filter.severity !== ALL || filter.family !== ALL;
  return (
    <div data-register-browser data-filter-severity={filter.severity} data-filter-family={filter.family}>
      <ChipGroup id="register-severity" label={bi('Severity', 'Severidad')} options={severityChips} value={filter.severity} onChange={(id) => change({ ...filter, severity: id })} />
      <ChipGroup id="register-family" label={bi('Question family of the case', 'Familia de preguntas del caso')} options={familyChips} value={filter.family} onChange={(id) => change({ ...filter, family: id })} />
      <p data-register-count data-matching={view.matching} data-hidden={view.hidden}>
        {filtered
          ? pick(
              {
                en: `${n(view.matching)} of ${n(total)} register rows match the filter; the filter hides the other ${n(view.hidden)}. Choose All in both rows to see every row.`,
                es: `${n(view.matching)} de ${n(total)} filas del registro cumplen el filtro; el filtro oculta las otras ${n(view.hidden)}. Elija Todas en ambas filas para ver todas las filas.`,
              },
              lang,
            )
          : pick({ en: `All ${n(total)} register rows are listed, no filter applied.`, es: `Se listan las ${n(total)} filas del registro, sin filtro.` }, lang)}
      </p>
      {view.matching === 0 ? (
        <p className="caos-pending" data-state="empty" data-register-empty>
          {pick({ en: 'No register row matches this filter: no finding of that severity has a case in that family. Choose another severity or family, or All.', es: 'Ninguna fila del registro cumple este filtro: ningún hallazgo de esa severidad tiene un caso en esa familia. Elija otra severidad u otra familia, o Todas.' }, lang)}
        </p>
      ) : (
        <PlotCard
          title={{ en: 'The findings register', es: 'El registro de hallazgos' }}
          lane="replay"
          provenance="synthetic"
          note={{ en: `${n(per)} rows a page, S1 first and then the document's order; the column buttons sort the rows of the page shown. A due date is the raised date plus the deadline of its severity and tier, a stated convention.`, es: `${n(per)} filas por página, primero S1 y luego el orden del documento; los botones de columna ordenan las filas de la página que se muestra. Una fecha de vencimiento es la fecha de registro más el plazo de su severidad y nivel, una convención declarada.` }}
        >
          <RegisterTable rows={view.page} />
        </PlotCard>
      )}
      <RowPager n={view.matching} per={per} start={view.start} onStart={setStart} label={pick({ en: 'Register page', es: 'Página del registro' }, lang)} />
    </div>
  );
}

/** The register and its charts: the text, the summary and the charts of the governance view, around the filtered pages. */
export function PagedRegisterSection({ findings }: { findings: GovFindings }) {
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
      <RegisterBrowser rows={findings.rows} />
      <PlotCard title={{ en: 'Severity by status', es: 'Severidad por estado' }} lane="replay" provenance="synthetic">
        <SeverityStatusBars rows={findings.rows} />
      </PlotCard>
      <PlotCard title={{ en: 'Ageing of the findings not closed', es: 'Antigüedad de los hallazgos no cerrados' }} lane="replay" provenance="synthetic" note={{ en: 'A bar in the alert colour holds at least one overdue finding.', es: 'Una barra en el color de alerta contiene al menos un hallazgo vencido.' }}>
        <AgeingChart rows={findings.rows} />
      </PlotCard>
    </>
  );
}

/** The appetite with the register's row count when the register was read; without it, the appetite's own count alone. */
function AppetiteWithRegister({ appetite }: { appetite: GovAppetite }) {
  const findings = useGovernance<GovFindings>(GOVERNANCE_FILES.findings);
  return <AppetiteSection appetite={appetite} registerRows={findings.state === 'ready' ? findings.data.counts.total : undefined} />;
}

/** The tab: each document in its own declared state, so a missing appetite never hides the register. */
export function PagedFindingsTabLoader() {
  return (
    <>
      <GovernanceDoc<GovFindings> file={GOVERNANCE_FILES.findings}>{(findings) => <PagedRegisterSection findings={findings} />}</GovernanceDoc>
      <GovernanceDoc<GovAppetite> file={GOVERNANCE_FILES.appetite}>{(appetite) => <AppetiteWithRegister appetite={appetite} />}</GovernanceDoc>
    </>
  );
}
