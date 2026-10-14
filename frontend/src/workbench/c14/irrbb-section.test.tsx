// U10-W: the Methodology topic on interest rate risk in the banking book (pages/methodology/irrbb.tsx) rendered on the
// server in both languages. ADR-0017 section 2.1 asks a `method` topic for dense paragraphs, captioned equations, a figure,
// exactly one honest callout and references; every reference the topic lists exists in the citation registry; the Spanish
// is Spanish; the coverage rows of C14 and C15 name their data and their truth status.
import { readFileSync } from 'node:fs';
import { CitationsProvider } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it } from 'vitest';
import { CITATIONS } from '../../content/citations';
import { CASES } from '../../content/coverage';
import { ChilePart, DynamicsPart, EvePart, MeasuresPart, methodologySection } from '../../pages/methodology/irrbb';
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
const words = (p: string) => p.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
const paragraphs = (m: string) => [...m.matchAll(/<p>(.*?)<\/p>/gs)].map((x) => x[1]).filter((p) => words(p) >= 40);

describe('the IRRBB Methodology topic', () => {
  afterEach(() => setLang('en'));

  it('is registered with the area and kind the gate reads, in a group the page already has', () => {
    expect(REGISTERED_SECTIONS.map((s) => s.id)).toContain('irrbb');
    expect(['models', 'tests', 'loss']).toContain(methodologySection.group);
    expect(markup('en')).toContain('data-area="method"');
    expect(markup('en')).toContain('data-method-kind="classical"');
  });

  it('opens on its first part with dense paragraphs, captioned equations and a figure, and has exactly one honest callout, in both languages', () => {
    for (const lang of ['en', 'es'] as const) {
      const m = markup(lang);
      expect(paragraphs(m).length, lang).toBeGreaterThanOrEqual(3);
      expect(m.match(/class="equation"/g)?.length ?? 0, lang).toBeGreaterThanOrEqual(1);
      expect(m.match(/<figure/g)?.length ?? 0, lang).toBeGreaterThanOrEqual(1);
      expect(m.match(/data-callout="honest"/g)?.length ?? 0, lang).toBe(1);
    }
  });

  it('has four parts as sub-tabs, with the equations, figures and paragraphs ADR-0017 asks for across them', () => {
    const source = readFileSync(new URL('../../pages/methodology/irrbb.tsx', import.meta.url), 'utf8');
    expect(source.match(/\{ id: '[a-z]+', label: t\(/g)?.length).toBe(4);
    expect(source.match(/<Equation$/gm)?.length ?? source.match(/<Equation\n/g)?.length).toBeGreaterThanOrEqual(4);
    expect(source.match(/<Figure /g)?.length).toBeGreaterThanOrEqual(3);
    expect(source.match(/<Callout /g)?.length).toBe(1);
    expect(source.match(/^ {6}<P$/gm)?.length ?? 0).toBeGreaterThanOrEqual(8);
  });

  it('every part, not only the one open, has dense paragraphs, a captioned equation and Spanish decimals with a comma', () => {
    const parts = [MeasuresPart, EvePart, DynamicsPart, ChilePart];
    for (const Part of parts) {
      for (const lang of ['en', 'es'] as const) {
        setLang(lang);
        const m = html(
          <CitationsProvider items={CITATIONS}>
            <Part />
          </CitationsProvider>,
        );
        expect(paragraphs(m).length, `${Part.name} ${lang}`).toBeGreaterThanOrEqual(2);
        expect(m.match(/class="equation"/g)?.length ?? 0, `${Part.name} ${lang}`).toBeGreaterThanOrEqual(1);
        if (lang === 'es') {
          // the displayed prose is the paragraphs and the captions (KaTeX carries the TeX source); a marked reference may keep its point
          const prose = [...m.matchAll(/<(?:p|div class="equation-caption"|figcaption)[^>]*>(.*?)<\/(?:p|div|figcaption)>/gs)].map((x) => x[1]).join(' ');
          const text = prose.replace(/<span translate="no">.*?<\/span>/g, '').replace(/<[^>]+>/g, ' ');
          expect([...text.matchAll(/.{30}\d\.\d.{20}/gs)].map((x) => x[0]), Part.name).toEqual([]);
        }
      }
    }
  });

  it('lists and cites only references the registry holds, each with a DOI or a URL', () => {
    const source = readFileSync(new URL('../../pages/methodology/irrbb.tsx', import.meta.url), 'utf8');
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

  it('the Spanish is written in Spanish, not the English paragraph', () => {
    const es = markup('es');
    expect(es).toContain('riesgo de tasa de interés');
    expect(es).not.toContain('Interest rate risk in the banking book is measured two ways');
    // a paragraph number of the framework is marked translate="no" (G11); every other decimal takes a comma
    expect(paragraphs(es).join(' ').replace(/<span translate="no">.*?<\/span>/g, '').replace(/<[^>]+>/g, ' ')).not.toMatch(/\d\.\d/);
  });

  it('has no em-dash and no emoji', () => {
    const all = markup('en') + markup('es');
    expect(all).not.toMatch(/[\u2014\u2015]|[\u{1F000}-\u{1FAFF}]/u);
  });
});

describe('the coverage rows of the cases U10 builds', () => {
  it('name the data and the truth status of C14 and C15, built by U10, in both languages', () => {
    for (const id of ['C14', 'C15']) {
      const row = CASES.find((c) => c.id === id);
      expect(row, id).toBeDefined();
      expect(row?.unit).toBe('U10');
      const data = row?.data as { en: string; es: string };
      expect(data.en.length).toBeGreaterThan(20);
      expect(data.es).not.toBe(data.en);
      const truth = row?.truth as { en: string; es: string };
      expect(truth.es).not.toBe(truth.en);
    }
    expect((CASES.find((c) => c.id === 'C14')?.truth as { en: string }).en).toBe('real aggregates, synthetic behaviour');
  });
});
