// The methods compared on the Benchmark page (BL-113 T3): an overview tab in the reading group (one row per question) and each question's
// table and chart as a section of its case's tab. The page reads data/derived/benchmark/methods-compared.json and recomputes nothing:
// every number, every best mark and every reading is the document's. The words for a method's standing are "Long-established",
// "Recent published" and "Proposed in this work" (and "Reference" for the rows that set the scale); each method is named with its source
// and year. A cell the product does not compute shows its reason; a long table is split by column, never scrolled sideways.
import { BarChart, ChipGroup, DocSection, PlotCard, Verdict, formatNumber, pick, useShellLang, type BarDatum, type BiText, type Lang } from '@fasl-work/caos-app-shell';
import { useState, type CSSProperties } from 'react';
import { useT } from '../../content/bi';
import {
  STANDING_LABEL,
  STANDING_NOTE,
  barPoints,
  chunkColumns,
  columnLabel,
  defaultMetric,
  isNumeric,
  isRanked,
  metricsOf,
  overviewRows,
  runOf,
  columnPrecision,
  docText,
  tableGroups,
  useMethodsCompared,
  type CellValue,
  type McCell,
  type McMetric,
  type McQuestion,
  type McRow,
  type MethodsCompared,
  type OverviewRow,
} from '../../lib/methodsCompared';
import type { Text } from '../../lib/contract.types';
import { provenanceOf } from '../../workbench/model';
import { PUBLICATIONS } from '../Publications';
import { Table } from '../U6Sections';

/** A document text with its decimals in the form of each language, for a shell prop that takes both. */
const loc = (t: Text): Text => ({ en: docText(t, 'en'), es: docText(t, 'es') });

/** The box of a table: a safety net at the narrowest width; the tables are split by column so it rarely scrolls. */
const BOX: CSSProperties = { overflowX: 'auto', maxWidth: '100%', minWidth: 0, position: 'relative' };
const CONTROLS: CSSProperties = { display: 'flex', flexDirection: 'column', gap: '0.5rem', margin: '0.75rem 0', minWidth: 0, maxWidth: '100%' };
const BEST: CSSProperties = { fontWeight: 700, textDecoration: 'underline', textDecorationThickness: '2px', textUnderlineOffset: '3px' };
/** Columns of a table per page: a method name beside three values fits a phone. */
const COLUMNS_PER_PAGE = 3;

/** The words of a categorical value (a Basel zone, a light, a verdict clause), in the page language, never the id. */
const WORDS: Record<string, BiText> = {
  green: { en: 'Green', es: 'Verde' },
  amber: { en: 'Amber', es: 'Ámbar' },
  red: { en: 'Red', es: 'Rojo' },
  not_evaluated: { en: 'Not evaluated', es: 'No evaluado' },
};
/** A cell with no value and no reason is a defect of the document; the page says so rather than hide it. */
const NO_REASON: Text = { en: 'The document gives no reason for this cell.', es: 'El documento no da una razón para esta celda.' };
const YES: BiText = { en: 'Yes', es: 'Sí' };
const NO: BiText = { en: 'No', es: 'No' };

function valueText(v: CellValue, lang: Lang, digits = 4): string {
  if (typeof v === 'number') return formatNumber(v, lang, { digits });
  if (typeof v === 'boolean') return pick(v ? YES : NO, lang);
  return WORDS[v] ? pick(WORDS[v], lang) : v;
}

/** The rule of a metric in words: which end is the best. */
function ruleText(q: McQuestion, m: McMetric, lang: Lang): string {
  const b = m.better;
  if (b === 'lower') return lang === 'es' ? 'menor es mejor' : 'lower is better';
  if (b === 'higher') return lang === 'es' ? 'mayor es mejor' : 'higher is better';
  if (b === 'none') return lang === 'es' ? 'contexto: no se ordena' : 'context: not ranked';
  if (b.startsWith('nearer-metric:')) {
    const other = q.metrics.find((x) => x.id === b.slice('nearer-metric:'.length));
    const name = other ? docText(other.label, lang) : '';
    return lang === 'es' ? `más cerca de «${name}» es mejor` : `nearer “${name}” is better`;
  }
  if (b.startsWith('nearer:')) {
    const target = formatNumber(Number(b.slice('nearer:'.length)), lang);
    return lang === 'es' ? `más cerca de ${target} es mejor` : `nearer ${target} is better`;
  }
  const order = b.slice('order:'.length).split(',').map((w) => (WORDS[w] ? pick(WORDS[w], lang) : w));
  return lang === 'es' ? `orden, de mejor a peor: ${order.join(', ')}` : `order, best to worst: ${order.join(', ')}`;
}

/** The manuscript of a negative result: its published title, linked to the concept DOI the document gives; a DOI the publications do not list is shown as itself. */
function ManuscriptLink({ doi }: { doi: string }) {
  const title = PUBLICATIONS.find((p) => p.concept_doi === doi)?.title ?? doi;
  return (
    <a href={`https://doi.org/${doi}`}>
      <span lang="en" translate="no">
        {title}
      </span>
    </a>
  );
}

/** The source of a method with its year, as the document gives them; the source is a citation and keeps its own words. */
function Source({ row }: { row: McRow }) {
  const lang = useShellLang();
  if (!row.source) return null;
  const text = row.source.text;
  const year = row.year !== null && !text.includes(String(row.year)) ? `, ${formatNumber(row.year, lang, { grouping: false })}` : '';
  const body = <span translate="no">{`${text}${year}`}</span>;
  return (
    <span className="ct-note" style={{ display: 'block', margin: '0.1rem 0 0' }}>
      {row.source.url ? (
        <a href={row.source.url} target="_blank" rel="noreferrer noopener">
          {body}
        </a>
      ) : (
        body
      )}
    </span>
  );
}

function MethodCell({ row }: { row: McRow }) {
  const lang = useShellLang();
  const t = useT();
  return (
    <td className="caos-col-text" style={{ minWidth: '11rem' }}>
      {docText(row.method, lang)}
      {!row.ranked && row.standing !== 'reference' ? <span className="ct-note"> ({t('shown, not ranked', 'se muestra, no se ordena')})</span> : null}
      <Source row={row} />
      {row.note ? <span className="ct-note" style={{ display: 'block', margin: '0.1rem 0 0' }}>{docText(row.note, lang)}</span> : null}
    </td>
  );
}

// ---------------------------------------------------------------------------------------------------------------- one question

function QuestionTable({ q, metric, columns, lang }: { q: McQuestion; metric: McMetric; columns: string[]; lang: Lang }) {
  const t = useT();
  const groups = tableGroups(q, metric, columns);
  const digits = columnPrecision(groups, columns.length);
  // the distinct reasons of the null cells of this table, numbered in the order they first appear
  const reasons: Text[] = [];
  const noteOf = (c: McCell): number => {
    const key = c.null_reason?.en ?? NO_REASON.en;
    let i = reasons.findIndex((r) => r.en === key);
    if (i < 0) {
      reasons.push(c.null_reason ?? NO_REASON);
      i = reasons.length - 1;
    }
    return i + 1;
  };
  const body = groups.map((g) => (
    <tbody key={g.standing} data-standing={g.standing}>
      <tr>
        <th scope="rowgroup" colSpan={columns.length + 1} className="caos-col-text" style={{ background: 'var(--color-surface-2, transparent)' }}>
          {pick(STANDING_LABEL[g.standing], lang)}
          <span className="ct-note" style={{ fontWeight: 400, marginLeft: '0.5rem' }}>
            {pick(STANDING_NOTE[g.standing], lang)}
          </span>
        </th>
      </tr>
      {g.rows.map((r) => (
        <tr key={r.row.id}>
          <MethodCell row={r.row} />
          {r.cells.map((c, i) => (
            <td key={columns[i]} style={{ whiteSpace: 'nowrap', textAlign: 'right' }}>
              {!c ? (
                '-'
              ) : c.value === null ? (
                <>
                  {t('not computed', 'no calculado')}
                  <sup aria-label={t('See the reason', 'Ver la razón')}>{noteOf(c)}</sup>
                </>
              ) : r.best[i] ? (
                <strong data-best="" style={BEST}>
                  {valueText(c.value, lang, digits[i])}
                  <span className="sr-only"> ({t('best of the column', 'el mejor de la columna')})</span>
                </strong>
              ) : (
                valueText(c.value, lang, digits[i])
              )}
            </td>
          ))}
        </tr>
      ))}
    </tbody>
  ));
  return (
    <div data-methods-table="" data-metric={metric.id} data-state="ready">
      <div data-table-box="" style={BOX}>
        <table className="caos-table ct-wrap-head ct-top">
          <caption className="ct-note" style={{ textAlign: 'left' }}>
            {docText(metric.label, lang)} ({docText(metric.unit, lang)}; {ruleText(q, metric, lang)})
          </caption>
          <thead>
            <tr>
              <th className="caos-col-text">{t('Method', 'Método')}</th>
              {columns.map((c) => (
                <th key={c}>{docText(columnLabel(q, metric, c), lang)}</th>
              ))}
            </tr>
          </thead>
          {body}
        </table>
      </div>
      {isRanked(metric) ? (
        <p className="ct-note">{t('Bold and underlined: the best value of each column by the rule in the caption; every method tied on it is marked.', 'En negrita y subrayado: el mejor valor de cada columna según la regla del título; se marcan todos los métodos empatados.')}</p>
      ) : null}
      {reasons.length > 0 && (
        <ol className="ct-note" style={{ paddingLeft: '1.25rem' }} data-null-reasons="">
          {reasons.map((r, i) => (
            <li key={i} id={`${q.id.toLowerCase()}-null-${i + 1}`}>
              {docText(r, lang)}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function Chart({ q, metric, column }: { q: McQuestion; metric: McMetric; column: string }) {
  const t = useT();
  const points = barPoints(q, metric, column);
  if (!points.length) {
    return (
      <p className="ct-note" data-methods-chart-none="">
        {t('This measure is a category or a verdict, or no method has a number in this column: the table above is its view.', 'Esta medida es una categoría o un veredicto, o ningún método tiene un número en esta columna: la tabla de arriba es su vista.')}
      </p>
    );
  }
  const data: BarDatum[] = points.map((p) => ({
    id: p.id,
    label: loc(p.method),
    value: p.value,
    // the best bar of a ranked metric is the accent and the others fade; a reference bar is neutral, so it reads as the scale
    highlight: isRanked(metric) && p.best,
    tone: p.standing === 'reference' ? 'neutral' : undefined,
    group: { id: p.standing, label: STANDING_LABEL[p.standing] },
  }));
  const col = columnLabel(q, metric, column);
  return (
    <div data-methods-chart="" data-metric={metric.id} data-column={column}>
      <PlotCard
        title={{ en: `${loc(metric.label).en}: ${loc(col).en}`, es: `${loc(metric.label).es}: ${loc(col).es}` }}
        lane="replay"
        provenance={provenanceOf(runOf(q, metric).truth_status)}
        note={{ en: `${ruleText(q, metric, 'en')}. The bars read from the table; the groups are the standing of each method.`, es: `${ruleText(q, metric, 'es')}. Las barras se leen de la tabla; los grupos son el lugar de cada método.` }}
      >
        <BarChart
          title={{ en: `${loc(metric.label).en}, ${loc(col).en}, by method`, es: `${loc(metric.label).es}, ${loc(col).es}, por método` }}
          data={data}
          axis={{ label: loc(metric.label), unit: loc(metric.unit), format: { digits: 4 } }}
          orientation="horizontal"
          values={points.every((p) => p.value >= 0)}
          zoomOff={points.length <= 8 ? { en: 'Few enough bars to read at once: there is nothing to zoom.', es: 'Hay pocas barras y se leen a la vez: no hay nada que ampliar.' } : undefined}
        />
      </PlotCard>
    </div>
  );
}

/** One question: its protocol, its reading, the table by standing with a metric and a column page to choose, and the chart of one column. */
export function MethodsQuestionView({ doc, question: q, initialMetric, initialPage = 0 }: { doc: MethodsCompared; question: McQuestion; initialMetric?: string; initialPage?: number }) {
  const lang = useShellLang();
  const t = useT();
  const metrics = metricsOf(q);
  const [metricId, setMetricId] = useState(initialMetric && metrics.some((m) => m.id === initialMetric) ? initialMetric : defaultMetric(q).id);
  const metric = metrics.find((m) => m.id === metricId) ?? metrics[0];
  const pages = chunkColumns(metric.columns, COLUMNS_PER_PAGE);
  const [page, setPage] = useState(initialPage);
  const [chartCol, setChartCol] = useState<string | null>(null);
  const columns = pages[Math.min(page, pages.length - 1)];
  const column = chartCol && metric.columns.includes(chartCol) ? chartCol : columns[0];
  const run = runOf(q, metric);
  const runs = [...new Set(metrics.map((m) => m.run_id))];
  const byRun = runs.map((id) => ({ run: q.runs.find((r) => r.id === id)!, metrics: metrics.filter((m) => m.run_id === id) }));
  const seed = run.seed ? run.seed.value : null;
  // a measure is named with its run when the question has several, so two runs' alike measures stay apart
  const measureLabel = (m: McMetric): BiText => {
    const r = q.runs.find((x) => x.id === m.run_id);
    const suffix = (l: 'en' | 'es') => (byRun.length > 1 && r ? ` [${r.label[l]}]` : '');
    return { en: `${docText(m.label, 'en')} (${docText(m.unit, 'en')})${suffix('en')}`, es: `${docText(m.label, 'es')} (${docText(m.unit, 'es')})${suffix('es')}` };
  };
  const here = q.negative_results.filter((n) => n.rows.some((id) => q.rows.some((r) => r.id === id)));
  return (
    <DocSection
      id={`methods-${q.id.toLowerCase()}`}
      area="comparison"
      title={{ en: `${q.id}: ${loc(q.title).en}`, es: `${q.id}: ${loc(q.title).es}` }}
      noRefsReason={{ en: 'Read from the committed methods-compared document, which cites the file and path of every number.', es: 'Leído del documento versionado de métodos comparados, que cita el archivo y la ruta de cada número.' }}
    >
      <div data-methods-question={q.id} data-state="ready">
        <p>
          <strong>{t('Protocol', 'Protocolo')}.</strong> {docText(q.protocol, lang)}
        </p>
        <Verdict compact title={{ en: 'What the comparison shows', es: 'Lo que muestra la comparación' }} tone="accent" verdict={{ en: docText(q.reading, 'en'), es: docText(q.reading, 'es') }} />
        <div style={CONTROLS} data-methods-controls="">
          {metrics.length > 1 && (
            <ChipGroup
              id={`methods-${q.id}-metric`}
              label={{ en: 'Measure', es: 'Medida' }}
              options={metrics.map((m) => ({ id: m.id, label: measureLabel(m) }))}
              value={metric.id}
              onChange={(v) => {
                setMetricId(v);
                setPage(0);
                setChartCol(null);
              }}
            />
          )}
          {pages.length > 1 && (
            <ChipGroup
              id={`methods-${q.id}-page`}
              label={{ en: 'Columns shown in the table', es: 'Columnas mostradas en la tabla' }}
              options={pages.map((p, i) => ({ id: String(i), label: { en: `Columns ${i * COLUMNS_PER_PAGE + 1} to ${i * COLUMNS_PER_PAGE + p.length}`, es: `Columnas ${i * COLUMNS_PER_PAGE + 1} a ${i * COLUMNS_PER_PAGE + p.length}` } }))}
              value={String(Math.min(page, pages.length - 1))}
              onChange={(v) => {
                setPage(Number(v));
                setChartCol(null);
              }}
            />
          )}
        </div>
        <p className="ct-note" data-methods-run="">
          {byRun.length > 1 || seed !== null ? (
            <>
              <strong>{t('Run', 'Corrida')}:</strong> {docText(run.label, lang)}
              {seed !== null ? `, ${t('seed', 'semilla')} ${seed}` : ''}. {byRun.length > 1 ? docText(run.protocol, lang) : ''}
            </>
          ) : null}
        </p>
        <QuestionTable q={q} metric={metric} columns={columns} lang={lang} />
        {metric.columns.length > 1 && isChartable(q, metric) ? (
          <div style={CONTROLS}>
            <ChipGroup
              id={`methods-${q.id}-chart`}
              label={{ en: 'Chart column', es: 'Columna del gráfico' }}
              options={metric.columns.map((c) => ({ id: c, label: loc(columnLabel(q, metric, c)) }))}
              value={column}
              onChange={setChartCol}
            />
          </div>
        ) : null}
        <Chart q={q} metric={metric} column={column} />
        {q.absent.length > 0 && (
          <div data-methods-absent="">
            <p>
              <strong>{t('Methods this comparison does not show', 'Métodos que esta comparación no muestra')}</strong>
            </p>
            <ul>
              {q.absent.map((a, i) => (
                <li key={i}>
                  {docText(a.method, lang)}: {docText(a.reason, lang)}
                </li>
              ))}
            </ul>
          </div>
        )}
        <p className="ct-note" data-methods-provenance="">
          {t(`Every number is copied from a committed file; the document (methods-compared, version ${doc.schema_version}) cites the file, the path and the SHA-256 of each.`, `Cada número se copia de un archivo versionado; el documento (métodos comparados, versión ${doc.schema_version}) cita el archivo, la ruta y el SHA-256 de cada uno.`)}
        </p>
        {here.map((n, i) => (
          <p key={i} data-methods-negative="">
            <strong>{t('A proposed method that does not win', 'Un método propuesto que no gana')}.</strong> {docText(n.text, lang)} <span className="ct-note">{t('Manuscript', 'Manuscrito')}: <ManuscriptLink doi={n.concept_doi} /></span>
          </p>
        ))}
      </div>
    </DocSection>
  );
}

/** Some metric of the question has a number in the column page: there is a bar to draw. */
function isChartable(q: McQuestion, m: McMetric): boolean {
  return q.rows.some((r) => r.cells.some((c) => c.metric === m.id && isNumeric(c.value)));
}

/** A question's section in its case's tab: the document loads once and says so while it does. */
export function MethodsQuestionSection({ id }: { id: string }) {
  const t = useT();
  const lang = useShellLang();
  const loaded = useMethodsCompared();
  const q = loaded.state === 'ready' ? loaded.data.questions.find((x) => x.id === id) : undefined;
  if (loaded.state === 'ready' && q) return <MethodsQuestionView doc={loaded.data} question={q} />;
  return (
    <DocSection
      id={`methods-${id.toLowerCase()}`}
      area="comparison"
      title={{ en: `${id}: the methods compared`, es: `${id}: los métodos comparados` }}
      noRefsReason={{ en: 'Read from the committed methods-compared document.', es: 'Leído del documento versionado de métodos comparados.' }}
    >
      {loaded.state === 'unavailable' ? (
        <p className="caos-pending" data-state="unavailable">
          {pick(loaded.reason, lang)}
        </p>
      ) : loaded.state === 'error' ? (
        <p className="caos-pending" data-state="error">
          {t('The methods-compared document could not be read.', 'No se pudo leer el documento de métodos comparados.')}
        </p>
      ) : (
        <p className="caos-pending" data-state="loading">
          {t('Loading the methods compared', 'Cargando los métodos comparados')}
        </p>
      )}
    </DocSection>
  );
}

// ---------------------------------------------------------------------------------------------------------------- the overview

function OverviewBest({ row, lang }: { row: OverviewRow; lang: Lang }) {
  return (
    <ul style={{ margin: 0, paddingLeft: '1.1rem' }}>
      {row.best.map((b) => (
        <li key={b.metric.id}>
          <span className="ct-note" style={{ margin: 0 }}>
            {docText(b.metric.label, lang)}:
          </span>{' '}
          {b.winners.map((w) => `${docText(w.method, lang)} (${formatNumber(w.wins, lang)}/${formatNumber(w.of, lang)})`).join('; ')}
        </li>
      ))}
    </ul>
  );
}

/** The overview: one row per question, the questions not built and why. */
export function MethodsOverviewView({ doc, onOpen }: { doc: MethodsCompared; onOpen: (questionId: string, caseId: string) => void }) {
  const lang = useShellLang();
  const t = useT();
  const rows = overviewRows(doc);
  const proposed = (r: OverviewRow) =>
    !r.hasProposed
      ? t('No method is proposed in this work on this question.', 'Ningún método se propone en este trabajo para esta pregunta.')
      : r.proposedWins > 0
        ? t(`Yes: best on ${r.proposedWins} of ${r.ranked} metrics.`, `Sí: mejor en ${r.proposedWins} de ${r.ranked} métricas.`)
        : t(`No: best on 0 of ${r.ranked} metrics.`, `No: mejor en 0 de ${r.ranked} métricas.`);
  return (
    <>
      <DocSection
        id="methods-overview"
        area="comparison"
        title={{ en: 'Methods compared, question by question', es: 'Métodos comparados, pregunta por pregunta' }}
        noRefsReason={{ en: 'Read from the committed methods-compared document.', es: 'Leído del documento versionado de métodos comparados.' }}
      >
        <div data-methods-overview="" data-state="ready">
          <p>
            {t(
              'Each question puts the methods the product runs on it side by side on one protocol: long-established methods, recent published ones and the methods proposed in this work, each named with its source and year. The best method of each measure is read from the numbers by the rule stated for it; a proposed method that loses is shown losing. Each question opens in the tab of its case.',
              'Cada pregunta pone lado a lado los métodos que el producto ejecuta sobre ella con un mismo protocolo: métodos de larga data, métodos publicados recientemente y los métodos propuestos en este trabajo, cada uno con su fuente y año. El mejor método de cada medida se lee de los números con la regla declarada para ella; un método propuesto que pierde se muestra perdiendo. Cada pregunta se abre en la pestaña de su caso.',
            )}
          </p>
          <Table
            head={[t('Question', 'Pregunta'), t('Protocol', 'Protocolo'), t('Best method on each measure (columns won of the columns compared)', 'Mejor método en cada medida (columnas ganadas de las comparadas)'), t('Proposed in this work', 'Propuesto en este trabajo')]}
            wide={3}
            rows={rows.map((r) => [
              <span key="q">
                <strong>{`${r.question.id}: ${docText(r.question.title, lang)}`}</strong>
                <br />
                <button type="button" className="btn" data-open-question={r.question.id} onClick={() => onOpen(r.question.id, r.home)}>
                  {t(`Open in ${r.home}`, `Abrir en ${r.home}`)}
                </button>
              </span>,
              <span key="p">{docText(r.protocol, lang)}</span>,
              <OverviewBest key="b" row={r} lang={lang} />,
              <span key="x">{proposed(r)}</span>,
            ])}
          />
        </div>
      </DocSection>
      <DocSection
        id="methods-not-built"
        area="comparison"
        title={{ en: 'Questions not compared, and why', es: 'Preguntas no comparadas, y por qué' }}
        noRefsReason={{ en: 'States why a question is not compared; read from the committed document.', es: 'Declara por qué una pregunta no se compara; leído del documento versionado.' }}
      >
        <Table
          head={[t('Question', 'Pregunta'), t('Why it is not compared', 'Por qué no se compara')]}
          wide={2}
          rows={doc.not_built.map((n) => [`${n.id}: ${docText(n.title, lang)}`, docText(n.reason, lang)])}
        />
      </DocSection>
    </>
  );
}

/** The overview tab: loads the document and opens a question in its case's tab. */
export function MethodsOverview({ onOpen }: { onOpen: (questionId: string, caseId: string) => void }) {
  const t = useT();
  const lang = useShellLang();
  const loaded = useMethodsCompared();
  if (loaded.state === 'ready') return <MethodsOverviewView doc={loaded.data} onOpen={onOpen} />;
  return loaded.state === 'unavailable' ? (
    <p className="caos-pending" data-state="unavailable">
      {pick(loaded.reason, lang)}
    </p>
  ) : loaded.state === 'error' ? (
    <p className="caos-pending" data-state="error">
      {t('The methods-compared document could not be read.', 'No se pudo leer el documento de métodos comparados.')}
    </p>
  ) : (
    <p className="caos-pending" data-state="loading">
      {t('Loading the methods compared', 'Cargando los métodos comparados')}
    </p>
  );
}
