// The "Reports" tab (U15-W): the twelve sections of the validation report (dossier 06 I.3) for one inventory entry,
// chosen by a select. A section is shown filled with its inputs, or absent with its reason; an element of the template
// the product holds nothing behind is listed as missing, with the reason. Section 11 shows the opinion level, the rule
// that gave it and the recommendation, labelled "the rule's output on the evidence; Contraste approves no model"
// (decisions W15-7 and W15-11). Everything is read from governance/reports/<case>-<fit>.json; a report the bake has not
// written is the declared "not available yet" state.
import { formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { useId, useState } from 'react';
import { P } from '../../content/bi';
import type { Text } from '../../lib/contract.types';
import { LIGHT_TEXT } from '../../lib/policy';
import { AsOf, ConventionNote, Doc, GovernanceDoc } from './common';
import { OpinionCard } from './OpinionBlock';
import { GOVERNANCE_FILES, OPINION_NAME, STATUS_NAME, entryLabel, reportFile, tierName, type GovInventory, type GovReport, type ReportSection } from './model';

type Block = ReportSection['blocks'][number];
type OutcomeRow = Extract<Block, { kind: 'outcomes' }>['rows'][number];

const SOURCE_NAME: Record<string, Text> = {
  'packaged-policy': { en: 'packaged policy file', es: 'archivo de política empaquetado' },
  'inline-battery': { en: 'inline battery string', es: 'cadena de batería en línea' },
  unresolved: { en: 'unresolved', es: 'sin resolver' },
};
const KIND_NAME: Record<string, Text> = { p_value: { en: 'p-value', es: 'valor p' }, metric: { en: 'metric', es: 'métrica' } };
const DIRECTION_NAME: Record<string, Text> = { upper_bad: { en: 'upper is bad', es: 'lo alto es malo' }, lower_bad: { en: 'lower is bad', es: 'lo bajo es malo' } };
const INPUT_KIND: Record<string, Text> = { document: { en: 'document', es: 'documento' }, engine: { en: 'engine', es: 'motor' }, convention: { en: 'convention', es: 'convención' } };

/** The role a model plays in a table of the report (decision W15: champion, challenger, benchmark, reference). */
const ROLE_NAME: Record<string, Text> = {
  champion: { en: 'champion', es: 'campeón' },
  challenger: { en: 'challenger', es: 'retador' },
  benchmark: { en: 'benchmark', es: 'referencia externa' },
  reference: { en: 'reference', es: 'referencia' },
  dgp: { en: 'generating process', es: 'proceso generador' },
};
/** The words of a column whose cells are tokens of a closed set, by the column's English title; any other column prints as written. */
const TOKEN_COLUMNS: Record<string, Record<string, Text>> = { light: LIGHT_TEXT, status: STATUS_NAME, role: ROLE_NAME };

function PolicyCell({ row }: { row: OutcomeRow }) {
  const lang = useShellLang();
  const p = row.policy;
  const unknown = pick({ en: 'not available', es: 'no disponible' }, lang);
  return (
    <>
      <span translate="no">{p.label}</span>
      <br />
      <span className="ct-note">
        {pick(SOURCE_NAME[p.source] ?? { en: p.source, es: p.source }, lang)}; {pick({ en: 'kind: ', es: 'tipo: ' }, lang)}
        {p.kind ? pick(KIND_NAME[p.kind], lang) : unknown}; {pick({ en: 'direction: ', es: 'sentido: ' }, lang)}
        {p.direction ? pick(DIRECTION_NAME[p.direction], lang) : p.source === 'inline-battery' ? pick({ en: 'not available (no policy file, backlog BL-085)', es: 'no disponible (sin archivo de política, pendiente BL-085)' }, lang) : unknown}
      </span>
    </>
  );
}

function OutcomesTable({ rows, variant }: { rows: OutcomeRow[]; variant: string }) {
  const lang = useShellLang();
  const num = (v: number | null) => formatNumber(v, lang, { digits: 4 });
  return (
    <div className="ct-fade-scroll" style={{ maxHeight: 420, minWidth: 0 }} data-outcomes={variant}>
      <table className="caos-table" data-state="ready">
        <caption className="ct-note">
          {pick({ en: 'Test rows of the variant ', es: 'Filas de prueba de la variante ' }, lang)}
          <span translate="no">{variant}</span>
        </caption>
        <thead>
          <tr>
            <th className="caos-col-text">{pick({ en: 'Test', es: 'Prueba' }, lang)}</th>
            <th className="caos-col-text ct-wide-only">{pick({ en: 'Model, segment', es: 'Modelo, segmento' }, lang)}</th>
            <th>{pick({ en: 'Statistic', es: 'Estadístico' }, lang)}</th>
            <th>{pick({ en: 'p-value', es: 'valor p' }, lang)}</th>
            <th>{pick({ en: 'Metric', es: 'Métrica' }, lang)}</th>
            <th>{pick({ en: 'Light', es: 'Luz' }, lang)}</th>
            <th className="caos-col-text ct-wide-only">{pick({ en: 'Policy', es: 'Política' }, lang)}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} data-test={r.test_id} data-light={r.light}>
              <td className="caos-col-text">
                <span translate="no">{r.test_id}</span>
                <span className="ct-narrow-only" translate="no">
                  {r.model_id ?? '-'}
                  {r.segment ? `, ${r.segment}` : ''}
                </span>
              </td>
              <td className="caos-col-text ct-wide-only">
                <span translate="no">
                  {r.model_id ?? '-'}
                  {r.segment ? `, ${r.segment}` : ''}
                </span>
              </td>
              <td>{num(r.statistic)}</td>
              <td>{num(r.p_value)}</td>
              <td>{num(r.metric)}</td>
              <td className={`ct-light ct-light-${r.light}`}>
                <span className="ct-light-word">{pick(LIGHT_TEXT[r.light], lang)}</span>
              </td>
              <td className="caos-col-text ct-wide-only">
                <PolicyCell row={r} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BlockView({ block }: { block: Block }) {
  const lang = useShellLang();
  if (block.kind === 'text') return <p><Doc t={block.text} /></p>;
  if (block.kind === 'list')
    return (
      <ul>
        {block.items.map((it, i) => (
          <li key={i}><Doc t={it} /></li>
        ))}
      </ul>
    );
  if (block.kind === 'outcomes') return <OutcomesTable rows={block.rows} variant={block.variant_id} />;
  const cell = (v: string | number | boolean | null, column?: string): string => {
    if (typeof v === 'number') return formatNumber(v, lang, { digits: 4 });
    if (v === null) return pick({ en: 'not available', es: 'no disponible' }, lang);
    if (typeof v === 'boolean') return pick(v ? { en: 'yes', es: 'sí' } : { en: 'no', es: 'no' }, lang);
    const words = column ? TOKEN_COLUMNS[column.toLowerCase()]?.[v] : undefined;
    return words ? pick(words, lang) : v;
  };
  return (
    <div className="ct-fade-scroll" style={{ maxHeight: 360, minWidth: 0 }}>
      <table className="caos-table" data-state="ready">
        <caption className="ct-note">{pick(block.caption, lang)}</caption>
        <thead>
          <tr>
            {block.columns.map((c, i) => (
              <th key={i} className="caos-col-text">
                {pick(c, lang)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {block.rows.map((r, i) => (
            <tr key={i}>
              {r.map((v, j) => (
                <td key={j} className="caos-col-text">
                  <span translate={typeof v === 'string' && !TOKEN_COLUMNS[block.columns[j]?.en.toLowerCase()]?.[v] ? 'no' : undefined}>{cell(v, block.columns[j]?.en)}</span>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** One of the twelve sections: filled with its inputs, or absent with its reason; what the template asks for and the product lacks is listed as missing. */
export function SectionView({ section }: { section: ReportSection }) {
  const lang = useShellLang();
  const opinion = 'opinion' in section ? section.opinion : null;
  const level = 'opinion_level' in section ? section.opinion_level : null;
  return (
    <section data-section={section.number} data-key={section.key} data-status={section.status} style={{ borderLeft: '3px solid var(--color-border)', paddingLeft: '0.75rem', margin: '1rem 0', minWidth: 0 }}>
      <h4 style={{ margin: '0 0 0.35rem' }}>
        {section.number}. {pick(section.title, lang)}{' '}
        <span className="ct-note" data-section-status={section.status}>
          ({pick(section.status === 'filled' ? { en: 'filled', es: 'completa' } : { en: 'absent', es: 'ausente' }, lang)})
        </span>
      </h4>
      {section.status === 'absent' && section.absent_reason && (
        <p data-state="unavailable" className="caos-pending">
          {pick({ en: 'Not available: ', es: 'No disponible: ' }, lang)}
          <Doc t={section.absent_reason} capital />
        </p>
      )}
      {level !== null && (
        <p data-opinion-level={level}>
          {pick({ en: 'Opinion level ', es: 'Nivel de opinión ' }, lang)}
          {level}: {pick(OPINION_NAME[level], lang)}
        </p>
      )}
      {section.blocks.map((b, i) => (
        <BlockView key={i} block={b} />
      ))}
      {opinion && <OpinionCard opinion={opinion} />}
      {section.missing.length > 0 && (
        <ul className="ct-evidence" data-missing>
          {section.missing.map((m, i) => (
            <li key={i}>
              <strong>{pick({ en: 'Not available: ', es: 'No disponible: ' }, lang)}</strong>
              <Doc t={m.element} capital />. <Doc t={m.reason} capital />
            </li>
          ))}
        </ul>
      )}
      {section.inputs.length > 0 && (
        <details className="ct-note" data-inputs={section.inputs.length}>
          <summary>
            {pick({ en: 'Inputs', es: 'Insumos' }, lang)} ({section.inputs.length})
          </summary>
          <ul className="ct-evidence">
            {section.inputs.map((inp, i) => (
              <li key={i}>
                <span lang="en" translate="no" style={{ overflowWrap: 'anywhere' }}>
                  {inp.ref}
                </span>{' '}
                ({pick(INPUT_KIND[inp.kind], lang)})
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}

/** The report of one entry: its title, tier and test counts, and its twelve sections. */
export function ReportDocument({ report }: { report: GovReport }) {
  const lang = useShellLang();
  const c = report.test_counts;
  const n = (v: number) => formatNumber(v, lang, { decimals: 0 });
  return (
    <article data-report={report.entry_key} data-sections={report.sections.length}>
      <h3 className="ct-sub">{pick(report.title, lang)}</h3>
      <p data-report-header>
        <span translate="no">{report.entry_key}</span>, {tierName(report.tier, lang)}. {pick({ en: 'Test rows: ', es: 'Filas de prueba: ' }, lang)}
        {pick(LIGHT_TEXT.green, lang)}: {n(c.green)}, {pick(LIGHT_TEXT.amber, lang)}: {n(c.amber)}, {pick(LIGHT_TEXT.red, lang)}: {n(c.red)}, {pick({ en: 'not evaluated', es: 'no evaluadas' }, lang)}: {n(c.not_evaluated)}, {pick(LIGHT_TEXT.error, lang)}: {n(c.error)}.
      </p>
      <AsOf asOf={report.as_of} basis={report.as_of_basis} />
      {report.sections.map((s) => (
        <SectionView key={s.number} section={s} />
      ))}
    </article>
  );
}

/** The select of the entries and the report of the chosen one. */
export function ReportReader({ inv }: { inv: GovInventory }) {
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
        {(report) => <ReportDocument report={report} />}
      </GovernanceDoc>
    </>
  );
}

/** The tab: the inventory (for the select) and then the report of the chosen entry, each in its declared state. */
export function ReportsTabLoader() {
  return (
    <>
      <P
        en="One validation report per inventory entry, in the twelve sections of the template of dossier 06 I.3. A section is filled from named inputs, or absent with its reason, and what the template asks for and Contraste holds nothing behind is listed as not available. Section 11 gives the opinion on the ECB four-level scale as the output of a stated rule: it is not an approval."
        es="Un informe de validación por entrada del inventario, en las doce secciones de la plantilla del dossier 06 I.3. Una sección se completa con insumos nombrados, o queda ausente con su razón, y lo que la plantilla pide y Contraste no tiene detrás se lista como no disponible. La sección 11 da la opinión en la escala de cuatro niveles del BCE como resultado de una regla declarada: no es una aprobación."
      />
      <P
        en="Pick an entry to read its report. Each section names the inputs it was assembled from, in a fold under it: a committed document, an engine function or a stated convention. A section that is filled can still list elements of the template that Contraste holds nothing behind, such as a written soundness assessment or a monitoring pack; those are not invented, they are listed as not available with the reason. The report of an entry the bake has not written is shown as not available yet, with the file that is missing."
        es="Elija una entrada para leer su informe. Cada sección nombra los insumos con que se armó, en un pliegue bajo ella: un documento comprometido, una función del motor o una convención declarada. Una sección completa puede igualmente listar elementos de la plantilla que Contraste no tiene detrás, como una evaluación escrita de solidez o un paquete de monitoreo; no se inventan, se listan como no disponibles con su razón. El informe de una entrada que la generación no ha escrito se muestra como aún no disponible, con el archivo que falta."
      />
      <ConventionNote />
      <GovernanceDoc<GovInventory> file={GOVERNANCE_FILES.inventory}>{(inv) => <ReportReader inv={inv} />}</GovernanceDoc>
    </>
  );
}
