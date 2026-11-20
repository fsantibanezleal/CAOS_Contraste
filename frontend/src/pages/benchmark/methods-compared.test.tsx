// BL-113 T3: the methods-compared document on the Benchmark page. The overview tab and each question's section are rendered on the server
// from the committed document (data/derived/benchmark/methods-compared.json), in both languages, and read back as a reader sees them:
// the standing labels, the nulls with their reasons, the best marks, no tier word, no raw id. Requirements BM-102 to BM-110
// (docs/design/features/benchmark-methods/requirements.md); BM-101 is in benchmark-tabs.test.tsx; BM-115 to BM-117 (the truth status of a run,
// the published title and DOI of a manuscript, no process word) and BM-118 (the overview on a phone) close the file.
import { readFileSync } from 'node:fs';
import { afterEach, describe, expect, it } from 'vitest';
import type { MethodsCompared, McQuestion } from '../../lib/methodsCompared';
import {
  METHODS_CASES,
  localDecimals,
  OMITTED_METRICS,
  QUESTION_HOME,
  STANDING_LABEL,
  STANDING_ORDER,
  barPoints,
  bestPerMetric,
  chunkColumns,
  columnDigits,
  docText,
  defaultMetric,
  isRanked,
  metricsOf,
  overviewRows,
  questionsOf,
  runOf,
  tableGroups,
  unplacedQuestions,
} from '../../lib/methodsCompared';
import { provenanceOf } from '../../workbench/model';
import { html, setLang } from '../../workbench/c03/u6-testkit';
import { PUBLICATIONS } from '../Publications';
import { MethodsOverviewView, MethodsQuestionView } from './MethodsCompared';

const doc = JSON.parse(readFileSync(new URL('../../../../data/derived/benchmark/methods-compared.json', import.meta.url), 'utf8')) as MethodsCompared;
const question = (id: string) => doc.questions.find((q) => q.id === id) as McQuestion;
const plain = (markup: string) =>
  markup
    .replace(/<script[\s\S]*?<\/script>/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&nbsp;| /g, ' ')
    .replace(/\s+/g, ' ');
const BAD = /NaN|(?<!is )undefined|Infinity|\[object/; // a null reason may say a quantity "is undefined"
/** The tier words, a ladder id and an internal id never reach the reader. */
const TIER = /state[\s-]+of[\s-]+the[\s-]+art|\bsota\b|classical|cl[áa]sic[oa]|\btiers?\b|\bbeyond\b|m[áa]s allá|\bBS-\d+|\bM-\d+\b|estado del arte/i;
const esc = (x: string) => x.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const rawIds = new Set<string>(['not_evaluated']);
for (const q of doc.questions) {
  for (const m of q.metrics) if (m.id.includes('_')) rawIds.add(m.id);
  for (const r of q.runs) for (const c of r.columns) if (/[-_]/.test(c.id) && /[a-z]/.test(c.id) && !/^[a-z]+-d+$/.test(c.id)) rawIds.add(c.id);
  for (const r of q.rows) if (/[_\d]/.test(r.id) && /[a-z]/.test(r.id)) rawIds.add(r.id);
}
const RAW_IDS = new RegExp([...rawIds].map(esc).join('|'));
const LANGS = ['en', 'es'] as const;
const clone = <T,>(x: T): T => JSON.parse(JSON.stringify(x)) as T;
const everyMetric = doc.questions.flatMap((q) => metricsOf(q).map((m) => ({ q, m })));
const cellsOf = (q: McQuestion, id: string) => q.rows.flatMap((r) => r.cells.filter((c) => c.metric === id).map((c) => ({ r, c })));
/** The first measure whose cells include one without a value (the null cells the document states with a reason). */
const withNull = () => everyMetric.find(({ q, m }) => cellsOf(q, m.id).some(({ c }) => c.value === null))!;
/** A measure the document ranks by no rule (context) and that has numbers. */
const contextMetric = () => everyMetric.find(({ q, m }) => !isRanked(m) && cellsOf(q, m.id).some(({ c }) => typeof c.value === 'number'))!;
/** A measure whose cells are words (a zone, a light) or booleans. */
const categorical = () => everyMetric.find(({ q, m }) => cellsOf(q, m.id).some(({ c }) => typeof c.value === 'string'))!;
/** The measure with the most columns. */
const widest = () => everyMetric.reduce((a, b) => (b.m.columns.length > a.m.columns.length ? b : a));
/** A standing of the document where several methods tie. */
const tied = () => {
  for (const q of doc.questions) {
    const st = q.standings.find((x) => x.tie && x.best.length > 1);
    if (st) return { q, st };
  }
  throw new Error('the document has no tie');
};

const render = (q: McQuestion, lang: 'en' | 'es', initialMetric?: string, initialPage?: number, d: MethodsCompared = doc) => {
  setLang(lang);
  return html(<MethodsQuestionView doc={d} question={q} initialMetric={initialMetric} initialPage={initialPage} />);
};
const overview = (lang: 'en' | 'es', d: MethodsCompared = doc) => {
  setLang(lang);
  return html(<MethodsOverviewView doc={d} onOpen={() => undefined} />);
};
/** The table of a markup: the document's own readings are read apart. */
const tableOf = (markup: string) => plain(markup.slice(markup.indexOf('data-methods-table'), markup.indexOf('</table>')));
const columnLabelOf = (q: McQuestion, metricId: string, column: string) => {
  const m = q.metrics.find((x) => x.id === metricId)!;
  return q.runs.find((r) => r.id === m.run_id)!.columns.find((c) => c.id === column)!.label;
};

describe('BM-102: where each question lives, and a question no tab holds is named', () => {
  it('names a home case for every question of the document and for none that is not built', () => {
    expect(doc.questions.map((q) => q.id).sort()).toEqual(Object.keys(QUESTION_HOME).sort());
    for (const q of doc.questions) expect(QUESTION_HOME[q.id], q.id).toBe(q.case_ids[0]);
    for (const n of doc.not_built) expect(QUESTION_HOME[n.id], n.id).toBeUndefined();
  });
  it('lists the questions of a case in order, Q5 and Q12 together in C01', () => {
    expect(questionsOf('C01')).toEqual(['Q5', 'Q12']);
    expect(questionsOf('C06')).toEqual(['Q6']);
    expect(METHODS_CASES).toEqual(['C01', 'C04', 'C06', 'C08', 'C11', 'C13', 'C14', 'C16', 'C17', 'C20', 'C22']);
  });
  it('adversarial: a question the page does not place is named, and so is a question with no home case', () => {
    const all = doc.questions.map((q) => `methods:${q.id}`);
    expect(unplacedQuestions(doc, all)).toEqual([]);
    expect(unplacedQuestions(doc, all.filter((s) => s !== 'methods:Q7'))).toEqual(['Q7']);
    const grown = clone(doc);
    grown.questions.push({ ...clone(doc.questions[0]), id: 'Q99' });
    expect(unplacedQuestions(grown, [...all, 'methods:Q99'])).toEqual(['Q99']);
  });
});

describe('BM-103: the overview tab lists every question and every question not built', () => {
  it('lists, in both languages, one row per question with its protocol, its best methods and a control that opens it, and the reasons of the questions not built', () => {
    for (const lang of LANGS) {
      const markup = overview(lang);
      const text = plain(markup);
      for (const q of doc.questions) {
        expect(text, `${q.id} title`).toContain(docText(q.title, lang));
        expect(markup, `${q.id} link`).toContain(`data-open-question="${q.id}"`);
      }
      for (const n of doc.not_built) {
        expect(text, `${n.id} title`).toContain(docText(n.title, lang));
        expect(text, `${n.id} reason`).toContain(docText(n.reason, lang));
      }
      expect((markup.match(/data-open-question="/g) ?? []).length).toBe(doc.questions.length);
      for (const r of overviewRows(doc)) {
        expect(text, r.question.id).toContain(docText(r.protocol, lang));
        for (const b of r.best) for (const w of b.winners) expect(text, `${r.question.id} ${b.metric.id}`).toContain(docText(w.method, lang));
      }
      expect(text).not.toMatch(BAD);
      expect(text).not.toMatch(TIER);
      expect(text.match(RAW_IDS)?.[0]).toBeUndefined();
    }
  });
  it('says whether a method proposed in this work is the best, and says so where none is proposed', () => {
    const en = plain(overview('en'));
    expect(en).toMatch(/Proposed in this work/);
    expect(en).toMatch(/best on \d+ of \d+ metrics/);
    expect(en).toMatch(/No method is proposed in this work on this question/);
    const es = plain(overview('es'));
    expect(es).toMatch(/Propuesto en este trabajo/);
    expect(es).toMatch(/mejor en \d+ de \d+ métricas/);
    expect(es).toMatch(/Ningún método se propone en este trabajo para esta pregunta/);
    const rows = overviewRows(doc);
    for (const r of rows) expect(r.hasProposed, r.question.id).toBe(r.question.rows.some((x) => x.standing === 'proposed'));
    expect(rows.some((r) => !r.hasProposed)).toBe(true);
    expect(rows.some((r) => r.hasProposed)).toBe(true);
  });
  it('names the best method of each ranked metric by the most columns won, ties named', () => {
    for (const q of doc.questions) {
      for (const b of bestPerMetric(q)) {
        expect(b.metric.better, `${q.id} ${b.metric.id}`).not.toBe('none');
        expect(b.winners.every((w) => w.wins === b.winners[0].wins), `${q.id} ${b.metric.id}`).toBe(true);
      }
    }
    // a metric the document ranks by no rule has no best method
    for (const q of doc.questions) for (const m of q.metrics.filter((x) => !isRanked(x))) expect(bestPerMetric(q).map((b) => b.metric.id)).not.toContain(m.id);
  });
  it('adversarial: a proposed method planted to lose every standing reads "No", and one planted to win every standing reads "Yes"', () => {
    const lose = clone(doc);
    const q4 = lose.questions.find((q) => q.id === 'Q4')!;
    const proposed = q4.rows.filter((r) => r.standing === 'proposed').map((r) => r.id);
    const other = q4.rows.find((r) => r.standing !== 'proposed')!.id;
    for (const s of q4.standings) {
      const rest = s.best.filter((id) => !proposed.includes(id));
      s.best = rest.length ? rest : [other];
    }
    expect(plain(overview('en', lose))).toMatch(/Q4: [^]*?No: best on 0 of \d+ metrics/);
    const win = clone(doc);
    for (const s of win.questions.find((q) => q.id === 'Q4')!.standings) s.best = [proposed[0]];
    expect(plain(overview('en', win))).toMatch(/Q4: [^]*?Yes: best on \d+ of \d+ metrics/);
    expect(plain(overview('es', win))).toMatch(/Sí: mejor en \d+ de \d+ métricas/);
  });
  afterEach(() => setLang('en'));
});

describe('BM-104: the rows sit in their standing, each method named with its source and year', () => {
  it('groups the rows by standing in the page order with a group only where a row exists', () => {
    for (const q of doc.questions) {
      for (const m of metricsOf(q)) {
        const groups = tableGroups(q, m, m.columns);
        const order = groups.map((g) => STANDING_ORDER.indexOf(g.standing));
        expect([...order].sort((a, b) => a - b), `${q.id} ${m.id}`).toEqual(order);
        const rows = groups.reduce((n, g) => n + g.rows.length, 0);
        expect(rows, `${q.id} ${m.id}`).toBe(q.rows.filter((r) => r.cells.some((c) => c.metric === m.id)).length);
      }
    }
  });
  it('groups the rows of Q1 and Q4 under the standing labels in both languages', () => {
    expect(plain(render(question('Q1'), 'en'))).toMatch(/Long-established.*Recent published.*Proposed in this work/);
    expect(plain(render(question('Q1'), 'es'))).toMatch(/De larga data.*Publicado recientemente.*Propuesto en este trabajo/);
    expect(plain(render(question('Q4'), 'en'))).toMatch(/Proposed in this work.*Reference/);
    expect(plain(render(question('Q4'), 'es'))).toMatch(/Propuesto en este trabajo.*Referencia/);
  });
  it('names every method with its source', () => {
    for (const lang of LANGS) {
      const text = plain(render(question('Q1'), lang));
      for (const r of question('Q1').rows.filter((x) => x.source)) expect(text, r.id).toContain(r.source!.text);
    }
  });
  it('states a not-ranked row as shown and not ranked', () => {
    expect(plain(render(question('Q10'), 'en'))).toMatch(/shown, not ranked/);
    expect(plain(render(question('Q10'), 'es'))).toMatch(/se muestra, no se ordena/);
  });
  it('adversarial: a method moved to the reference standing leaves its group, comes last, and a year the source lacks is added', () => {
    const moved = clone(doc);
    const q1 = moved.questions.find((q) => q.id === 'Q1')!;
    const target = q1.rows.find((r) => r.standing === 'established' && r.source && r.year !== null)!;
    target.standing = 'reference';
    target.source = { text: 'A source without a year', url: null };
    target.year = 1987;
    const groups = tableGroups(q1, metricsOf(q1)[0], metricsOf(q1)[0].columns);
    expect(groups[groups.length - 1].standing).toBe('reference');
    expect(groups[groups.length - 1].rows.map((r) => r.row.id)).toContain(target.id);
    expect(groups.find((g) => g.standing === 'established')!.rows.map((r) => r.row.id)).not.toContain(target.id);
    expect(plain(render(q1, 'en', undefined, undefined, moved))).toContain('A source without a year, 1987');
  });
  afterEach(() => setLang('en'));
});

describe('BM-105: the best value of a ranked metric is marked from the document and nowhere else', () => {
  it('marks as best exactly the rows of the document standings, ties included, and never a null', () => {
    for (const q of doc.questions) {
      for (const m of metricsOf(q)) {
        const marked = tableGroups(q, m, m.columns).flatMap((g) => g.rows.flatMap((r) => r.best.map((b, i) => (b ? `${r.row.id}@${m.columns[i]}` : null)).filter(Boolean)));
        // the document's best, and every ranked row equal to it at full precision (a tie the printed digits would hide); a reference row is never marked
        const expected = q.standings.filter((s) => s.metric === m.id).flatMap((s) => [...new Set([...s.best, ...q.rows.filter((r) => r.ranked && r.cells.some((c) => c.metric === m.id && c.column === s.column && c.value === s.value)).map((r) => r.id)])].map((id) => `${id}@${s.column}`));
        expect(marked.sort(), `${q.id} ${m.id}`).toEqual(expected.sort());
        for (const g of tableGroups(q, m, m.columns)) for (const r of g.rows) r.best.forEach((b, i) => b && expect(r.cells[i]?.value, `${q.id} ${r.row.id}`).not.toBeNull());
      }
    }
  });
  it('marks the best value of a ranked metric on the page and none on a metric that is context', () => {
    const q1 = question('Q1');
    expect((render(q1, 'en', defaultMetric(q1).id).match(/data-best/g) ?? []).length).toBeGreaterThanOrEqual(2);
    const { q, m } = contextMetric();
    expect(render(q, 'en', m.id)).not.toContain('data-best');
    for (const lang of LANGS) for (const x of everyMetric.filter((e) => !isRanked(e.m))) expect(render(x.q, lang, x.m.id), `${x.q.id} ${x.m.id}`).not.toContain('data-best');
  });
  it('adversarial: a standing planted on a null cell marks nothing, and a tie marks every tied method', () => {
    const planted = clone(doc);
    const { q: q0, m } = withNull();
    const q1 = planted.questions.find((q) => q.id === q0.id)!;
    const hit = cellsOf(q1, m.id).find(({ c }) => c.value === null)!;
    q1.standings = q1.standings.filter((s) => !(s.metric === m.id && s.column === hit.c.column));
    q1.standings.push({ metric: m.id, column: hit.c.column, best: [hit.r.id], value: 0, tie: false, n_ranked: 1 });
    const markup = render(q1, 'en', m.id, Math.max(0, chunkColumns(m.columns).findIndex((p) => p.includes(hit.c.column))), planted);
    const rowMarkup = markup.slice(markup.indexOf(`data-standing="${hit.r.standing}"`));
    expect(rowMarkup).toContain('not computed');
    const { q: q4, st } = tied();
    const metric = q4.metrics.find((x) => x.id === st.metric)!;
    const marked = tableGroups(q4, metric, [st.column])
      .flatMap((g) => g.rows)
      .filter((r) => r.best[0]);
    expect(marked.length).toBeGreaterThanOrEqual(st.best.length);
    expect(marked.map((r) => r.row.id)).toEqual(expect.arrayContaining(st.best));
  });
  it('prints a column with the digits that separate its best cell from the others, and marks every cell equal at full precision', () => {
    expect(columnDigits([{ value: -4.65901, best: true }, { value: -4.65904, best: false }])).toBeGreaterThan(4);
    expect(columnDigits([{ value: -4.659, best: true }, { value: -3.1, best: false }])).toBe(4);
    expect(columnDigits([{ value: 0.5, best: false }])).toBe(4);
    const q = clone(question('Q1'));
    const m = defaultMetric(q);
    const col = m.columns[0];
    const st = q.standings.find((x) => x.metric === m.id && x.column === col)!;
    const best = cellsOf(q, m.id).find(({ r, c }) => c.column === col && r.id === st.best[0])!;
    const other = cellsOf(q, m.id).find(({ r, c }) => c.column === col && !st.best.includes(r.id) && typeof c.value === 'number')!;
    // a cell planted 1e-6 from the best prints alike at four digits: the column takes more digits, and one planted equal is marked best
    other.c.value = (best.c.value as number) + (m.better === 'higher' ? -1 : 1) * 1e-6;
    const equal = cellsOf(q, m.id).find(({ r, c }) => c.column === col && r.id !== other.r.id && !st.best.includes(r.id) && typeof c.value === 'number');
    if (equal) equal.c.value = best.c.value;
    const rows = tableGroups(q, m, [col]).flatMap((g) => g.rows);
    expect(rows.find((r) => r.row.id === other.r.id)!.best[0]).toBe(false);
    if (equal) expect(rows.find((r) => r.row.id === equal.r.id)!.best[0]).toBe(true);
    const text = tableOf(render(q, 'en', m.id, 0, { ...doc, questions: doc.questions.map((x) => (x.id === q.id ? q : x)) }));
    const digits = columnDigits(rows.flatMap((r) => (typeof r.cells[0]?.value === 'number' ? [{ value: r.cells[0].value as number, best: r.best[0] }] : [])));
    expect(digits).toBeGreaterThan(4);
    expect(text).toContain((best.c.value as number).toPrecision(digits).replace(/0+$/, '').slice(0, 6));
  });
  afterEach(() => setLang('en'));
});

describe('BM-106: a cell the product does not compute shows its reason in the page language', () => {
  it('shows the reason of a cell not computed yet in both languages, with no backlog row in the text', () => {
    const { q, m } = withNull();
    const cell = cellsOf(q, m.id).find(({ c }) => c.value === null)!.c;
    const page = chunkColumns(m.columns).findIndex((p) => p.includes(cell.column));
    for (const lang of LANGS) {
      const text = plain(render(q, lang, m.id, page));
      expect(text).toContain(docText(cell.null_reason!, lang));
      expect(docText(cell.null_reason!, lang)).not.toMatch(/BL-\d+|backlog/i);
    }
  });
  it('shows the reason of every null cell of every question, on the column page where it sits', () => {
    for (const q of doc.questions) {
      for (const m of metricsOf(q)) {
        const pages = chunkColumns(m.columns);
        pages.forEach((_, i) => {
          const nulls = q.rows.flatMap((r) => r.cells).filter((c) => c.metric === m.id && c.value === null && pages[i].includes(c.column));
          if (!nulls.length) return;
          const text = plain(render(q, 'es', m.id, i));
          for (const c of nulls) expect(text, `${q.id} ${m.id} ${c.column}`).toContain(docText(c.null_reason!, 'es'));
        });
      }
    }
  });
  it('adversarial: a null cell planted with no reason says the document gives none, and a reason planted is the one shown', () => {
    const planted = clone(doc);
    const { q: q0, m } = withNull();
    const q1 = planted.questions.find((q) => q.id === q0.id)!;
    const target = cellsOf(q1, m.id).find(({ c }) => c.value === null)!.c;
    const page = chunkColumns(m.columns).findIndex((p) => p.includes(target.column));
    target.null_reason = null;
    expect(plain(render(q1, 'en', m.id, page, planted))).toContain('The document gives no reason for this cell.');
    target.null_reason = { en: 'A planted reason for the test.', es: 'Una razón sembrada para la prueba.' };
    expect(plain(render(q1, 'es', m.id, page, planted))).toContain('Una razón sembrada para la prueba.');
  });
  afterEach(() => setLang('en'));
});

describe('BM-107: a long table is split by column, never scrolled sideways', () => {
  it('splits the columns into pages of at most three, every column once', () => {
    for (const { q, m } of everyMetric) {
      const pages = chunkColumns(m.columns);
      expect(pages.flat(), `${q.id} ${m.id}`).toEqual(m.columns);
      for (const p of pages) expect(p.length).toBeLessThanOrEqual(3);
      expect(pages.length).toBe(Math.ceil(m.columns.length / 3));
    }
    expect(widest().m.columns.length).toBeGreaterThan(3);
  });
  it('shows at most three value columns in a table and a selector for the pages', () => {
    for (const q of doc.questions) {
      for (const m of metricsOf(q)) {
        const markup = render(q, 'en', m.id);
        const head = markup.slice(markup.indexOf('<thead>'), markup.indexOf('</thead>'));
        expect((head.match(/<th[ >]/g) ?? []).length, `${q.id} ${m.id}`).toBeLessThanOrEqual(4);
        if (m.columns.length > 3) expect(markup, `${q.id} ${m.id}`).toContain('Columns 1 to 3');
        else expect(markup, `${q.id} ${m.id}`).not.toContain('Columns 1 to');
      }
    }
  });
  it('adversarial: the last page of a fifteen-column measure shows its last columns and not the first', () => {
    const { q: q2, m } = widest();
    const pages = chunkColumns(m.columns);
    expect(pages.length).toBeGreaterThan(1);
    const table = tableOf(render(q2, 'en', m.id, pages.length - 1));
    for (const c of pages[pages.length - 1]) expect(table).toContain(docText(columnLabelOf(q2, m.id, c), 'en'));
    expect(table).not.toContain(`${docText(columnLabelOf(q2, m.id, m.columns[0]), 'en')} `);
  });
  afterEach(() => setLang('en'));
});

describe('BM-108: each question has a bar chart of one measure and column, from the numbers of the table', () => {
  it('draws a bar for every numeric cell of a column and none for a null', () => {
    for (const { q, m } of everyMetric) {
      for (const col of m.columns) {
        const numeric = cellsOf(q, m.id).filter(({ c }) => c.column === col && typeof c.value === 'number');
        expect(barPoints(q, m, col).length, `${q.id} ${m.id} ${col}`).toBe(numeric.length);
      }
    }
    const { q, m } = withNull();
    const nullCol = cellsOf(q, m.id).find(({ c }) => c.value === null)!.c.column;
    expect(barPoints(q, m, nullCol).length).toBeLessThan(cellsOf(q, m.id).filter(({ c }) => c.column === nullCol).length);
  });
  it('puts a chart or the reason it has none on every question, and a chart on the measure the section opens on', () => {
    for (const q of doc.questions) {
      expect(render(q, 'en'), q.id).toMatch(/data-methods-chart=|data-methods-chart-none=/);
      expect(barPoints(q, defaultMetric(q), defaultMetric(q).columns[0]).length, q.id).toBeGreaterThan(0);
    }
  });
  it('names a categorical measure in words (zone, light) in the table and not by its id', () => {
    const { q, m } = categorical();
    const words = cellsOf(q, m.id).flatMap(({ c }) => (typeof c.value === 'string' ? [c.value] : []));
    const text = tableOf(render(q, 'es', m.id));
    if (words.some((w) => ['green', 'amber', 'red'].includes(w))) {
      expect(text).toMatch(/Verde|Ámbar|Rojo/);
      expect(text).not.toMatch(/\bgreen\b|\bamber\b|\bred\b/);
      expect(tableOf(render(q, 'en', m.id))).toMatch(/Green|Amber|Red/);
    }
    for (const w of words) if (w.includes('_')) expect(text).not.toContain(w);
  });
  it('adversarial: a column planted with no number draws no bar and says the table is its view', () => {
    const planted = clone(doc);
    const q = planted.questions.find((x) => x.id === 'Q3')!;
    const target = defaultMetric(q);
    for (const r of q.rows)
      for (const c of r.cells)
        if (c.metric === target.id && c.column === target.columns[0]) {
          c.value = null;
          c.null_reason = { en: 'planted', es: 'sembrado' };
          c.cited = null;
        }
    const markup = render(q, 'en', target.id, 0, planted);
    expect(markup).toContain('data-methods-chart-none');
    expect(markup).not.toContain('data-methods-chart=""');
  });
  afterEach(() => setLang('en'));
});

describe('BM-109: both languages, no tier word, no raw id', () => {
  it('renders every question in both languages with its title, protocol, reading and standing labels, and without a gap, a tier word or an id', () => {
    for (const q of doc.questions) {
      for (const lang of LANGS) {
        const markup = render(q, lang);
        const text = plain(markup);
        expect(markup, q.id).toContain(`id="methods-${q.id.toLowerCase()}"`);
        expect(text, q.id).toContain(docText(q.title, lang));
        expect(text, q.id).toContain(docText(q.protocol, lang));
        expect(text, q.id).toContain(docText(q.reading, lang));
        const m = defaultMetric(q);
        for (const g of tableGroups(q, m, chunkColumns(m.columns)[0])) {
          expect(text, `${q.id} ${g.standing}`).toContain(docText(STANDING_LABEL[g.standing], lang));
          for (const r of g.rows) expect(text, `${q.id} ${r.row.id}`).toContain(docText(r.row.method, lang));
        }
        const other = lang === 'en' ? 'es' : 'en';
        for (const s of STANDING_ORDER) if (docText(STANDING_LABEL[s], other) !== docText(STANDING_LABEL[s], lang)) expect(text, `${q.id} ${lang}`).not.toContain(docText(STANDING_LABEL[s], other));
        expect(text, q.id).not.toMatch(BAD);
        expect(text, q.id).not.toMatch(TIER);
        expect(text.match(RAW_IDS)?.[0], q.id).toBeUndefined();
        expect(markup, q.id).toContain('data-methods-table');
      }
    }
  });
  it('shows a question split by run with each run, its protocol and its seed', () => {
    for (const q of doc.questions.filter((x) => x.runs.length > 1)) {
      for (const run of q.runs.filter((r) => r.seed)) {
        const m = metricsOf(q).find((x) => x.run_id === run.id);
        if (!m) continue;
        expect(plain(render(q, 'en', m.id)), `${q.id} ${run.id}`).toContain(`seed ${run.seed!.value}`);
        expect(plain(render(q, 'es', m.id)), `${q.id} ${run.id}`).toContain(`semilla ${run.seed!.value}`);
      }
    }
    expect(doc.questions.some((x) => x.runs.length > 1)).toBe(true);
  });
  it('shows the manuscript that reports a proposed method losing, and the methods a question states absent', () => {
    const q2 = question('Q2');
    expect(plain(render(q2, 'en'))).toContain(docText(q2.negative_results[0].text, 'en'));
    expect(plain(render(question('Q4'), 'es'))).toContain(docText(question('Q4').negative_results[0].text, 'es'));
    for (const a of q2.absent) expect(plain(render(q2, 'en'))).toContain(docText(a.reason, 'en'));
  });
  it('adversarial: a tier word planted in a method name or a reading is caught by the pattern the page is held to', () => {
    for (const planted of ['a method of the beyond tier', 'a state of the art method', 'a classical estimator', 'BS-14 refuted', 'M-18 variant', 'un método clásico', 'más allá del estado del arte']) expect(planted, planted).toMatch(TIER);
    const dirty = clone(doc);
    const q3 = dirty.questions.find((q) => q.id === 'Q3')!;
    q3.rows[0].method.en = 'A classical attribution test';
    expect(plain(render(q3, 'en', undefined, undefined, dirty))).toMatch(TIER);
  });
  afterEach(() => setLang('en'));
});

describe('BM-109 decimals: the Spanish page writes the decimals of the document in the Spanish form', () => {
  it('adversarial: a decimal planted in a Spanish text is written with a comma and a thousand is left alone', () => {
    expect(localDecimals('cerca de 0.85 con 2.5 y 1.000 días', 'es')).toBe('cerca de 0,85 con 2,5 y 1.000 días');
    expect(localDecimals('near 0.85 with 2.5', 'en')).toBe('near 0.85 with 2.5');
    const planted = clone(doc);
    const q = planted.questions.find((x) => x.id === 'Q3')!;
    q.reading.es = 'Lectura sembrada con un corte de 0.85 en la prueba.';
    expect(plain(render(q, 'es', undefined, undefined, planted))).toContain('corte de 0,85 en la prueba');
  });
  it('writes no decimal point in the Spanish text of any question or of the overview', () => {
    const point = /(?<![\w.,])\d+\.\d{1,2}(?![\w.])/;
    for (const q of doc.questions) expect(plain(render(q, 'es')).match(point)?.[0], q.id).toBeUndefined();
    expect(plain(overview('es')).match(point)?.[0]).toBeUndefined();
  });
  afterEach(() => setLang('en'));
});

describe('BM-110: the section of a question extends what its case tab shows and never repeats it', () => {
  it('omits from Q1 the exceedance counts the C11 ladder already prints, and from no other question', () => {
    expect(OMITTED_METRICS.Q1).toEqual(['exceed_1', 'expected_1']);
    expect(metricsOf(question('Q1')).map((m) => m.id)).not.toContain('exceed_1');
    for (const q of doc.questions.filter((x) => x.id !== 'Q1')) expect(metricsOf(q).length, q.id).toBe(q.metrics.length);
    expect(defaultMetric(question('Q1')).id).not.toMatch(/exceed|expected/);
  });
  it('adversarial: the exceedance measures listed first in the document still stay out of the section and out of its selector', () => {
    const planted = clone(doc);
    const q1 = planted.questions.find((q) => q.id === 'Q1')!;
    const exceed = (id: string) => (id.startsWith('exceed') || id.startsWith('expected') ? 0 : 1);
    q1.metrics.sort((a, b) => exceed(a.id) - exceed(b.id));
    expect(q1.metrics[0].id).toMatch(/exceed|expected/);
    expect(defaultMetric(q1).id).not.toMatch(/exceed|expected/);
    const markup = render(q1, 'en', 'exceed_1', 0, planted);
    const controls = markup.slice(markup.indexOf('data-methods-controls'), markup.indexOf('data-methods-run'));
    expect(controls.length).toBeGreaterThan(0);
    for (const id of OMITTED_METRICS.Q1) expect(controls).not.toContain(docText(q1.metrics.find((m) => m.id === id)!.label, 'en'));
  });
  afterEach(() => setLang('en'));
});

// ------------------------------------------------------------------------------ BM-115 to BM-117 (contract 2.0.0)

/** The provenance label of the chart card a measure draws (the shell writes it as data-provenance on the figure). */
const chartProvenance = (markup: string): string | null => {
  const at = markup.indexOf('data-methods-chart=""');
  if (at < 0) return null;
  return /data-provenance="([^"]*)"/.exec(markup.slice(at))?.[1] ?? null;
};
/** Title text as the server renders it into markup (the characters React escapes). */
const esc2 = (t: string) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');

const TRUTH_LIST = ['real-outcomes', 'synthetic-known-truth', 'synthetic-calibrated', 'published-answer'];
/** Process vocabulary and repository paths: none reaches a reader. */
const PROCESS = /\bBL-\d+|\bK-\d+|backlog|method ladder|escalera de m[eé]todos/i;
const PATHS = /manuscripts\/|\.tex\b|data\/derived/;
const chartable = () => everyMetric.filter(({ q, m }) => barPoints(q, m, m.columns[0]).length > 0);

describe('BM-115: each chart card is labelled from the truth status the document gives its run', () => {
  it('labels the chart of every measure of every question with provenanceOf of the status of its run', () => {
    const measures = chartable();
    expect(measures.length).toBeGreaterThan(30);
    for (const { q, m } of measures) {
      const run = runOf(q, m);
      expect(TRUTH_LIST, `${q.id} ${run.id}`).toContain(run.truth_status);
      expect(chartProvenance(render(q, 'en', m.id)), `${q.id} ${m.id}`).toBe(provenanceOf(run.truth_status));
    }
  });
  it('reads Q10 labelled run as synthetic and Q12 twin as real, the two runs the typed list had wrong', () => {
    const q10 = question('Q10');
    const q12 = question('Q12');
    expect(q10.runs[0].truth_status).toBe('synthetic-calibrated');
    expect(q12.runs[0].truth_status).toBe('real-outcomes');
    expect(chartProvenance(render(q10, 'en', defaultMetric(q10).id))).toBe('synthetic');
    expect(chartProvenance(render(q12, 'es', defaultMetric(q12).id))).toBe('real');
  });
  it('adversarial: a run planted with another status changes the label, and a run id the page has never seen is labelled by its status', () => {
    const planted = clone(doc);
    const q12 = planted.questions.find((q) => q.id === 'Q12')!;
    q12.runs[0].truth_status = 'published-answer';
    expect(chartProvenance(render(q12, 'en', defaultMetric(q12).id, 0, planted))).toBe('published');
    q12.runs[0].truth_status = 'synthetic-known-truth';
    expect(chartProvenance(render(q12, 'en', defaultMetric(q12).id, 0, planted))).toBe('synthetic');
    // a typed list would decide by the id: 'desk' (Q3) was labelled synthetic and a new id real, whatever the document says
    const q3 = planted.questions.find((q) => q.id === 'Q3')!;
    const m3 = defaultMetric(q3);
    q3.runs.find((r) => r.id === m3.run_id)!.truth_status = 'real-outcomes';
    expect(chartProvenance(render(q3, 'en', m3.id, 0, planted))).toBe('real');
    const fresh = clone(doc);
    const q7 = fresh.questions.find((q) => q.id === 'Q7')!;
    const m7 = defaultMetric(q7);
    q7.runs.find((r) => r.id === m7.run_id)!.id = 'a-run-the-page-never-saw';
    for (const m of q7.metrics) if (m.run_id === 'out-of-time') m.run_id = 'a-run-the-page-never-saw';
    q7.runs.find((r) => r.id === 'a-run-the-page-never-saw')!.truth_status = 'synthetic-calibrated';
    expect(chartProvenance(render(q7, 'en', m7.id, 0, fresh))).toBe('synthetic');
  });
  afterEach(() => setLang('en'));
});

describe('BM-116: a negative result names its manuscript by the published title linked to its DOI, never by a path', () => {
  const withNegative = doc.questions.filter((q) => q.negative_results.length > 0);
  it('shows, for every negative result, the published title in an English span that is not translated, linked to the concept DOI', () => {
    expect(withNegative.map((q) => q.id)).toEqual(['Q2', 'Q4', 'Q9', 'Q11']);
    for (const q of withNegative) {
      for (const n of q.negative_results) {
        const pub = PUBLICATIONS.find((p) => p.concept_doi === n.concept_doi);
        expect(pub, n.concept_doi).toBeDefined();
        for (const lang of LANGS) {
          const markup = render(q, lang);
          const anchor = new RegExp(`<a[^>]*href="https://doi\\.org/${esc(n.concept_doi)}"[^>]*>\\s*<span lang="en" translate="no">${esc(esc2(pub!.title))}</span>`);
          expect(markup, `${q.id} ${lang}`).toMatch(anchor);
        }
      }
    }
  });
  it('prints no repository path in any question or in the overview, in either language', () => {
    for (const lang of LANGS) {
      for (const q of doc.questions) expect(plain(render(q, lang)), `${q.id} ${lang}`).not.toMatch(PATHS);
      expect(plain(overview(lang)), lang).not.toMatch(PATHS);
    }
  });
  it('adversarial: a DOI the publications do not hold is the link text, never the path', () => {
    const planted = clone(doc);
    const q4 = planted.questions.find((q) => q.id === 'Q4')!;
    q4.negative_results[0].concept_doi = '10.5281/zenodo.9999999';
    for (const lang of LANGS) {
      const markup = render(q4, lang, undefined, undefined, planted);
      expect(markup).toMatch(/<a[^>]*href="https:\/\/doi\.org\/10\.5281\/zenodo\.9999999"[^>]*>\s*<span lang="en" translate="no">10\.5281\/zenodo\.9999999<\/span>/);
      expect(plain(markup)).not.toMatch(PATHS);
    }
  });
  afterEach(() => setLang('en'));
});

describe('BM-117: no process id or process word reaches a rendered text of the page', () => {
  it('holds no backlog id, computation id or backlog word in any question or in the overview, in both languages', () => {
    for (const lang of LANGS) {
      for (const q of doc.questions) {
        for (const m of metricsOf(q)) expect(plain(render(q, lang, m.id)), `${q.id} ${m.id} ${lang}`).not.toMatch(PROCESS);
        expect(plain(render(q, lang)), `${q.id} ${lang}`).not.toMatch(PROCESS);
      }
      expect(plain(overview(lang)), lang).not.toMatch(PROCESS);
    }
  });
  it('keeps the pointer the texts lost as a structured field of the document, which the page does not print', () => {
    expect(doc.left_out.every((i) => 'backlog' in i)).toBe(true);
    expect(question('Q4').absent[0].backlog).toBe('BL-119 (K-4)');
    expect(plain(render(question('Q4'), 'en'))).not.toContain('BL-119');
  });
  it('adversarial: a backlog id planted in an absent reason is caught by the pattern the page is held to', () => {
    for (const planted of ['see BL-121', 'adds the treatment (K-4)', 'the backlog row', 'the method ladder has none', 'la escalera de métodos no la tiene']) expect(planted, planted).toMatch(PROCESS);
    const dirty = clone(doc);
    const q4 = dirty.questions.find((q) => q.id === 'Q4')!;
    q4.absent[0].reason.en = 'a later computation adds it (backlog BL-119, K-4)';
    expect(plain(render(q4, 'en', undefined, undefined, dirty))).toMatch(PROCESS);
  });
  afterEach(() => setLang('en'));
});

// ------------------------------------------------------------------------------ BM-118 (the overview on a phone)

/** The rows of the overview table of a markup, each as its own markup. */
const overviewRowsOf = (markup: string) => markup.split('data-overview-row="').slice(1).map((part) => part.slice(0, part.indexOf('</tr>')));
/** The text of the first element of a row's markup that carries the attribute and value. */
const partOf = (row: string, attribute: string, value: string) => {
  const at = row.indexOf(`${attribute}="${value}"`);
  if (at < 0) return null;
  const open = row.indexOf('>', at) + 1;
  const close = row.indexOf(row[row.lastIndexOf('<', at) + 1] === 's' ? '</span>' : '</td>', open);
  return plain(row.slice(open, close));
};

describe('BM-118: on a phone the overview hides a column only when the row repeats its value', () => {
  it('repeats the protocol and the proposed-method line under the question, in both languages, and hides only those two columns', () => {
    for (const lang of ['en', 'es'] as const) {
      const markup = overview(lang);
      const rows = overviewRowsOf(markup);
      expect(rows.length).toBe(doc.questions.length);
      for (const row of rows) {
        for (const column of ['protocol', 'proposed'] as const) {
          const hidden = partOf(row, 'data-column', column);
          const repeated = partOf(row, 'data-repeats', column);
          expect(hidden, column).toBeTruthy();
          expect(repeated, column).toContain(hidden!);
        }
        // the hidden cells are the two repeated ones and no other: the question and the best methods always show
        expect(row.split('ct-wide-only ct-repeated').length - 1).toBe(2);
        expect(row.split('class="ct-narrow-only"').length - 1).toBe(2);
      }
      const head = markup.slice(markup.indexOf('data-methods-overview-table'), markup.indexOf('</thead>'));
      expect(head.split('ct-wide-only ct-repeated').length - 1).toBe(2);
    }
  });
  it('adversarial: a hidden column whose value the row does not repeat is found by the same reading', () => {
    const markup = overview('en');
    const row = overviewRowsOf(markup)[0];
    const start = row.indexOf('data-repeats="protocol"');
    const stripped = row.slice(0, row.lastIndexOf('<span', start)) + row.slice(row.indexOf('</span>', start) + '</span>'.length);
    expect(partOf(stripped, 'data-repeats', 'protocol')).toBeNull();
    expect(partOf(stripped, 'data-column', 'protocol')).toBeTruthy();
  });
  afterEach(() => setLang('en'));
});
