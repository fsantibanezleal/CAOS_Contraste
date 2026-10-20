// U14-W: the Methodology topic on ML model validation and fairness (pages/methodology/ml-validation.tsx) rendered on the
// server in both languages. ADR-0017 section 2.1 asks a `method` topic for dense paragraphs, captioned equations, a
// figure, exactly one honest callout and references; every reference the topic lists exists in the citation registry; the
// Spanish is Spanish; the legal sentences and the employment-benchmark label are in the text; the coverage rows of C02,
// C20 and C21 name their data and their truth status.
import { readFileSync } from 'node:fs';
import { CitationsProvider } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it } from 'vitest';
import { CITATIONS } from '../../content/citations';
import { CASES } from '../../content/coverage';
import { methodologySection } from '../../pages/methodology/ml-validation';
import { REGISTERED_SECTIONS } from '../../pages/methodologyRegistry';
import { html, setLang } from './testkit';

const Body = methodologySection.Body;
const markup = (lang: 'en' | 'es') => {
  setLang(lang);
  return html(
    <CitationsProvider items={CITATIONS}>
      <Body />
    </CitationsProvider>,
  );
};
const source = readFileSync(new URL('../../pages/methodology/ml-validation.tsx', import.meta.url), 'utf8').replaceAll(String.fromCharCode(13, 10), String.fromCharCode(10));
const words = (p: string) => p.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
const paragraphs = (m: string) => [...m.matchAll(/<p>(.*?)<\/p>/gs)].map((x) => x[1]).filter((p) => words(p) >= 40);

describe('the ML validation Methodology topic', () => {
  afterEach(() => setLang('en'));

  it('is registered with the area and kind the gate reads, in a group the page already has', () => {
    expect(REGISTERED_SECTIONS.map((s) => s.id)).toContain('ml-validation');
    expect(methodologySection.group).toBe('tests');
    expect(markup('en')).toContain('data-area="method"');
    expect(markup('en')).toContain('data-method-kind="classical"');
  });

  it('opens with dense paragraphs, captioned equations and a figure, and has exactly one honest callout, in both languages', () => {
    for (const lang of ['en', 'es'] as const) {
      const m = markup(lang);
      expect(paragraphs(m).length, lang).toBeGreaterThanOrEqual(3);
      expect(m.match(/class="equation"/g)?.length ?? 0, lang).toBeGreaterThanOrEqual(1);
      expect(m.match(/<figure/g)?.length ?? 0, lang).toBeGreaterThanOrEqual(1);
      expect(m.match(/data-callout="honest"/g)?.length ?? 0, lang).toBe(1);
    }
  });

  it('has three parts as sub-tabs with the equations, figures and paragraphs ADR-0017 asks for across them', () => {
    expect(source.match(/\{ id: '[a-z]+', label: t\(/g)?.length).toBe(3);
    expect(source.match(/<Equation\n/g)?.length).toBeGreaterThanOrEqual(4);
    expect(source.match(/<Figure /g)?.length).toBeGreaterThanOrEqual(3);
    expect(source.match(/<Callout /g)?.length).toBe(1);
    expect(source.match(/^ {6}<P$/gm)?.length ?? 0).toBeGreaterThanOrEqual(8);
  });

  it('says the four-fifths line is an employment benchmark and gives the legal sentences', () => {
    const src = source;
    expect(src).toContain('employment-selection benchmark');
    expect(src).toContain('not a credit-law threshold');
    for (const s of ['effects test', 'disparate-impact claims are cognizable', 'Gross HMDA denial or approval rate disparities are not appropriate']) {
      expect(src.includes(s) || src.includes(s.replace("'", '&apos;')), s).toBe(true);
    }
    expect(source).toContain('A passed test is evidence, not compliance.');
  });

  it('lists and cites only references the registry holds, each with a DOI or a URL', () => {
    const listed = [...(/refs=\{\[([^\]]*)\]\}/.exec(source)?.[1] ?? '').matchAll(/'([a-z0-9]+)'/g)].map((x) => x[1]);
    const cited = [...source.matchAll(/<Cite id="([a-z0-9]+)"/g)].map((x) => x[1]);
    expect(listed.length).toBeGreaterThanOrEqual(20);
    for (const id of new Set([...listed, ...cited])) {
      const c = CITATIONS.find((x) => x.id === id);
      expect(c, id).toBeDefined();
      expect(Boolean(c?.doi || c?.url), id).toBe(true);
    }
    for (const id of cited) expect(listed, id).toContain(id);
    expect(markup('en')).toContain(`data-refs="${listed.length}"`);
    expect(new Set(CITATIONS.map((c) => c.id)).size).toBe(CITATIONS.length);
  });

  it('the Spanish is written in Spanish and takes a comma for every decimal; a quoted source keeps its words', () => {
    const es = markup('es');
    expect(es).toContain('aprendizaje automático');
    expect(es).not.toContain('A machine learning model has no coefficient to read');
    const prose = paragraphs(es).join(' ').replace(/<span translate="no">.*?<\/span>/g, '').replace(/<[^>]+>/g, ' ');
    expect(prose).not.toMatch(/\d\.\d/);
    expect(paragraphs(markup('en')).join(' ').replace(/<[^>]+>/g, ' ')).not.toMatch(/\d,\d/);
  });

  it('has no em-dash and no emoji', () => {
    expect(markup('en') + markup('es')).not.toMatch(/[\u2014\u2015]|[\u{1F000}-\u{1FAFF}]/u);
  });
});

describe('the coverage rows of the cases U14 builds', () => {
  it('name the data and the truth status of C02, C20 and C21, built by U14, in both languages', () => {
    for (const id of ['C02', 'C20', 'C21']) {
      const row = CASES.find((c) => c.id === id);
      expect(row, id).toBeDefined();
      expect(row?.unit).toBe('U14');
      const data = row?.data as { en: string; es: string };
      expect(data.es).not.toBe(data.en);
      const truth = row?.truth as { en: string; es: string };
      expect(truth.es).not.toBe(truth.en);
    }
    expect((CASES.find((c) => c.id === 'C20')?.data as { en: string }).en).toContain('research and benchmarking only');
  });
});
