// BL-113 T4: the Introduction and the Experiments point at the methods compared, and a link opens the Benchmark tab that holds them.
// Requirements BM-111 to BM-114 (docs/design/features/benchmark-methods/requirements.md). The pointers read every count from the
// committed document (data/derived/benchmark/methods-compared.json); the pages are rendered with the document loaded.
import { readFileSync } from 'node:fs';
import type { ReactNode } from 'react';
import { CitationsProvider } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { CaseManifest } from '../../lib/contract.types';
import type { MethodsCompared } from '../../lib/methodsCompared';
import { CITATIONS } from '../../content/citations';
import { html, setLang } from '../../workbench/c03/u6-testkit';

type TabDef = { id: string; label: ReactNode; content: ReactNode };
const doc = JSON.parse(readFileSync(new URL('../../../../data/derived/benchmark/methods-compared.json', import.meta.url), 'utf8')) as MethodsCompared;
/** The document the pointers read: the committed one, or a planted one when a test sets it. */
const state: { doc: MethodsCompared | null } = { doc };

vi.mock('../../lib/methodsCompared', async (importOriginal) => {
  const mod = await importOriginal<Record<string, unknown>>();
  return { ...mod, useMethodsCompared: () => (state.doc ? { state: 'ready', data: state.doc } : { state: 'loading' }) };
});
// every tab is rendered, so one render reads the whole page (the shell draws only the active one)
vi.mock('@fasl-work/caos-app-shell', async (importOriginal) => {
  const shell = await importOriginal<Record<string, unknown>>();
  const all = ({ tabs }: { tabs: TabDef[] }) => (
    <>
      {tabs.map((t) => (
        <section key={t.id} data-test-tab={t.id}>
          <h2>{t.label}</h2>
          {t.content}
        </section>
      ))}
    </>
  );
  return { ...shell, Tabs: all, SubTabs: all };
});

const { Introduction } = await import('../Introduction');
const { CaseTopic } = await import('../Experiments');
const { methodsCounts, benchmarkLink, casePointers } = await import('./MethodsPointer');
const { selectionFromHash } = await import('../Benchmark');

const plain = (m: string) =>
  m
    .replace(/<script[\s\S]*?<\/script>/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&nbsp;| /g, ' ')
    .replace(/\s+/g, ' ');
/** The text of the pointers alone: the pages carry other words of their own (an executive text says "beyond the model"). */
const pointerText = (m: string) => [...m.matchAll(/<(p|div) data-methods-pointer[\s\S]*?<\/\1>/g)].map((x) => plain(x[0])).join(' ');
const TIER = /state[\s-]+of[\s-]+the[\s-]+art|\bsota\b|classical|cl[áa]sic[oa]|\btiers?\b|\bbeyond\b|m[áa]s allá|\bBS-\d+|\bM-\d+\b|estado del arte/i;
const manifest = (id: string) => JSON.parse(readFileSync(new URL(`../../../../data/derived/manifests/${id}.json`, import.meta.url), 'utf8')) as CaseManifest;
const clone = <T,>(x: T): T => JSON.parse(JSON.stringify(x)) as T;
const introHtml = (lang: 'en' | 'es') => {
  setLang(lang);
  return html(
    <CitationsProvider items={CITATIONS}>
      <Introduction />
    </CitationsProvider>,
  );
};
const topic = (id: string, lang: 'en' | 'es') => {
  setLang(lang);
  return html(
    <CitationsProvider items={CITATIONS}>
      <CaseTopic m={manifest(id)} />
    </CitationsProvider>,
  );
};
afterEach(() => {
  state.doc = doc;
  setLang('en');
});

describe('BM-111 the counts of the pointers are the document\'s', () => {
  it('counts the questions of the document and each method once, the reference rows aside', () => {
    const c = methodsCounts(doc);
    const methods = new Set(doc.questions.flatMap((q) => q.rows.filter((r) => r.standing !== 'reference').map((r) => r.ladder_id ?? r.id)));
    expect(c.questions).toBe(doc.questions.length);
    expect(c.methods).toBe(methods.size);
    expect(c.questions).toBeGreaterThan(1);
    expect(c.methods).toBeGreaterThan(c.questions);
  });
  it('prints those counts in the Introduction, in both languages, with a link to the methods compared', () => {
    const c = methodsCounts(doc);
    for (const lang of ['en', 'es'] as const) {
      const text = plain(introHtml(lang));
      expect(text, lang).toContain(`${c.questions} ${lang === 'en' ? 'questions' : 'preguntas'}`);
      expect(text, lang).toContain(`${c.methods} ${lang === 'en' ? 'methods' : 'métodos'}`);
    }
    expect(introHtml('en')).toContain('href="/benchmark#methods"');
  });
  it('prints how many methods are left out and how many questions are not compared, from the document, and drops a clause whose count is zero', () => {
    expect(doc.left_out.length).toBeGreaterThan(0);
    expect(doc.not_built.length).toBeGreaterThan(0);
    const en = plain(introHtml('en'));
    expect(en).toContain(`${doc.left_out.length} methods are left out and ${doc.not_built.length} questions are not compared, with their reasons on the Benchmark page`);
    expect(plain(introHtml('es'))).toContain(`${doc.left_out.length} métodos quedan fuera y ${doc.not_built.length} preguntas no se comparan, con sus razones en la página de los métodos comparados`);
    const planted = clone(doc);
    planted.left_out = [];
    planted.not_built = planted.not_built.slice(0, 1);
    state.doc = planted;
    expect(plain(introHtml('en'))).toContain('1 question is not compared, with their reasons');
    expect(plain(introHtml('en'))).not.toContain('left out');
    planted.not_built = [];
    expect(plain(introHtml('en'))).not.toMatch(/left out|not compared/);
  });
  it('adversarial: a planted document moves the printed counts, so they are read and never typed', () => {
    const planted = clone(doc);
    planted.questions = planted.questions.slice(0, 3);
    state.doc = planted;
    const c = methodsCounts(planted);
    expect(c.questions).toBe(3);
    const text = plain(introHtml('en'));
    expect(text).toContain(`3 questions and ${c.methods} methods`);
    expect(text).toContain('The methods the product runs are compared');
    expect(text).not.toContain('Every method');
    expect(text).not.toContain(`${doc.questions.length} questions`);
  });
  it('adversarial: while the document is not loaded the pointer states the comparison with no count and keeps its link', () => {
    state.doc = null;
    const text = plain(introHtml('en'));
    expect(text).toContain('compared with the published practice');
    expect(text).not.toMatch(/\d+ questions and \d+ methods/);
    expect(introHtml('en')).toContain('href="/benchmark#methods"');
  });
});

describe('BM-112 each experiment links to its question', () => {
  it('lists, in the section of a case, every question the document holds for it, with the number of its methods and a link to it', () => {
    for (const id of ['C11', 'C01', 'C22', 'C13']) {
      const qs = casePointers(doc, id);
      expect(qs.length, id).toBeGreaterThan(0);
      for (const lang of ['en', 'es'] as const) {
        const m = topic(id, lang);
        for (const p of qs) {
          expect(m, `${id} ${p.question.id}`).toContain(`href="${benchmarkLink(p.question.id)}"`);
          expect(plain(m), `${id} ${p.question.id} ${lang}`).toContain(`${p.methods} ${lang === 'en' ? 'methods' : 'métodos'}`);
        }
      }
    }
  });
  it('finds the questions of C11 (Q1 and Q2) and of C01 (Q5 and Q12) from the document', () => {
    expect(casePointers(doc, 'C11').map((p) => p.question.id)).toEqual(['Q1', 'Q2']);
    expect(casePointers(doc, 'C01').map((p) => p.question.id)).toEqual(['Q5', 'Q12']);
  });
  it('says nothing for a case with no question in the document', () => {
    expect(casePointers(doc, 'C99')).toEqual([]);
    expect(topic('C05', 'en')).not.toContain('data-methods-pointer');
  });
  it('adversarial: a question moved out of the document leaves the section of its case without that link', () => {
    const planted = clone(doc);
    planted.questions = planted.questions.filter((q) => q.id !== 'Q5');
    state.doc = planted;
    const m = topic('C01', 'en');
    expect(m).not.toContain(`href="${benchmarkLink('Q5')}"`);
    expect(m).toContain(`href="${benchmarkLink('Q12')}"`);
  });
});

describe('BM-113 a link opens the tab of the methods compared', () => {
  it('opens the overview tab of the reading group for the bare link', () => {
    const link = benchmarkLink();
    expect(selectionFromHash(link.slice(link.indexOf('#')))).toEqual({ sel: { group: 'reading', tab: 'methods' }, scrollTo: null });
  });
  it('opens the tab of the home case of a question and scrolls to it', () => {
    const r = selectionFromHash('#methods-q1');
    expect(r?.sel.tab).toBe('case-c11');
    expect(r?.scrollTo).toBe('Q1');
    expect(selectionFromHash('#methods-q12')?.sel.tab).toBe('case-c01');
  });
  it('adversarial: a hash that is not a methods link, and a question with no home, change nothing or fall back to the overview', () => {
    expect(selectionFromHash('')).toBeNull();
    expect(selectionFromHash('#provenance')).toBeNull();
    expect(selectionFromHash('#methods-q99')).toEqual({ sel: { group: 'reading', tab: 'methods' }, scrollTo: null });
  });
});

describe('BM-114 no tier word reaches the pointers', () => {
  it('reads clean in the pointer of the Introduction and in the pointer of a case section, in both languages', () => {
    for (const lang of ['en', 'es'] as const) {
      const a = pointerText(introHtml(lang));
      const b = pointerText(topic('C11', lang));
      expect(a.length, lang).toBeGreaterThan(100);
      expect(b.length, lang).toBeGreaterThan(50);
      expect(a, lang).not.toMatch(TIER);
      expect(b, lang).not.toMatch(TIER);
    }
  });
  it('adversarial: the pattern matches a tier word planted in a pointer sentence', () => {
    expect('compared with the state of the art on one protocol').toMatch(TIER);
    expect('comparado con el estado del arte').toMatch(TIER);
  });
});
