// U13-W: the Methodology topic on capital aggregation and macro stress testing (pages/methodology/aggregation-stress.tsx)
// rendered on the server in both languages. ADR-0017 section 2.1 asks a `method` topic for dense paragraphs, captioned
// equations, a figure, exactly one honest callout and references; every reference the topic lists exists in the citation
// registry with a DOI or a URL; the Spanish is Spanish; the coverage rows say C18 is built and C19 stays planned with its reason.
import { readFileSync } from 'node:fs';
import { CitationsProvider } from '@fasl-work/caos-app-shell';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import { CITATIONS } from '../../content/citations';
import { CASES } from '../../content/coverage';
import { AggregationPart, AllocationPart, IapePart, SatellitePart, ScenarioPart, methodologySection } from '../../pages/methodology/aggregation-stress';
import { REGISTERED_SECTIONS } from '../../pages/methodologyRegistry';
import { html, setLang } from '../c03/u6-testkit';

const Body = methodologySection.Body;
const wrap = (el: ReactElement) => <CitationsProvider items={CITATIONS}>{el}</CitationsProvider>;
const markup = (lang: 'en' | 'es') => {
  setLang(lang);
  return html(wrap(<Body />));
};
const words = (p: string) => p.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
const paragraphs = (m: string) => [...m.matchAll(/<p>(.*?)<\/p>/gs)].map((x) => x[1]).filter((p) => words(p) >= 40);
const source = readFileSync(new URL('../../pages/methodology/aggregation-stress.tsx', import.meta.url), 'utf8');
const PARTS = [AggregationPart, AllocationPart, SatellitePart, ScenarioPart, IapePart];

describe('the aggregation and stress Methodology topic', () => {
  afterEach(() => setLang('en'));

  it('is registered with the area and kind the gate reads, in the capital group the page already has', () => {
    expect(REGISTERED_SECTIONS.map((s) => s.id)).toContain('aggregation-stress');
    expect(methodologySection.group).toBe('capital');
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

  it('has five parts as sub-tabs, with the equations, figures and paragraphs ADR-0017 asks for across them', () => {
    expect(source.match(/\{ id: '[a-z0-9]+', label: t\(/g)?.length).toBe(5);
    expect(source.match(/<Equation$/gm)?.length ?? 0).toBeGreaterThanOrEqual(7);
    expect(source.match(/<Figure /g)?.length).toBeGreaterThanOrEqual(5);
    expect(source.match(/<Callout /g)?.length).toBe(1);
    expect(source.match(/^ {6}<P$/gm)?.length ?? 0).toBeGreaterThanOrEqual(12);
  });

  it('every part, not only the one open, has dense paragraphs, a figure and Spanish decimals with a comma', () => {
    let equations = 0;
    for (const Part of PARTS) {
      for (const lang of ['en', 'es'] as const) {
        setLang(lang);
        const m = html(wrap(<Part />));
        expect(paragraphs(m).length, `${Part.name} ${lang}`).toBeGreaterThanOrEqual(2);
        expect(m.match(/<figure/g)?.length ?? 0, `${Part.name} ${lang}`).toBeGreaterThanOrEqual(1);
        if (lang === 'en') equations += m.match(/class="equation"/g)?.length ?? 0;
        if (lang === 'es') {
          // the displayed prose is the paragraphs, the captions and the drawings' labels (KaTeX carries the TeX source)
          const prose = [...m.matchAll(/<(?:p|div class="equation-caption"|figcaption|text)(?=[\s>])[^>]*>(.*?)<\/(?:p|div|figcaption|text)>/gs)].map((x) => x[1]).join(' ');
          const text = prose.replace(/<span translate="no">.*?<\/span>/g, '').replace(/<[^>]+>/g, ' ');
          expect([...text.matchAll(/.{30}\d\.\d.{20}/gs)].map((x) => x[0]), Part.name).toEqual([]);
        }
      }
    }
    expect(equations).toBeGreaterThanOrEqual(7);
  });

  it('lists and cites only references the registry holds, each with a DOI or a URL', () => {
    const listed = [...(/refs=\{\[([^\]]*)\]\}/.exec(source)?.[1] ?? '').matchAll(/'([a-z0-9]+)'/g)].map((x) => x[1]);
    const cited = [...source.matchAll(/<Cite id="([a-z0-9]+)"/g)].map((x) => x[1]);
    expect(listed.length).toBeGreaterThanOrEqual(25);
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
    expect(es).toContain('El capital de los riesgos de un banco se suma');
    expect(es).not.toContain('The capital of the risks of a bank is added');
    expect(paragraphs(es).join(' ').replace(/<span translate="no">.*?<\/span>/g, '').replace(/<[^>]+>/g, ' ')).not.toMatch(/\d\.\d/);
  });

  it('keeps the rearrangement figure to the published values and the callout to the unverified items, with no em-dash and no emoji', () => {
    const en = markup('en');
    // the figure carries Table 4, d = 8, of Embrechts, Puccetti and Rueschendorf (2013) as the research addendum transcribes it
    for (const v of ['9.00', '72.00', '141.67', '13.13', '105.14', '203.66', '30.47', '244.98', '465.29']) expect(en, v).toContain(v);
    expect(en).toContain('are conventions or case assumptions');
    expect(en).toContain('Several items of the sources stay unverified');
    expect(en + markup('es')).not.toMatch(/[—―]|[\u{1F000}-\u{1FAFF}]/u);
  });
});

describe('the coverage rows of the cases U13 owns', () => {
  it('name the data and the truth status of C18, built by U13, in both languages', () => {
    const row = CASES.find((c) => c.id === 'C18');
    expect(row?.unit).toBe('U13');
    const data = row?.data as { en: string; es: string };
    expect(data.en).toContain('Banco Andino');
    expect(data.es).not.toBe(data.en);
    expect((row?.truth as { en: string }).en).toBe('real paths, synthetic bank');
  });

  it('keep C19 planned with its reason and no replication claim', () => {
    const row = CASES.find((c) => c.id === 'C19');
    expect(row?.unit).toBe('U13');
    const data = row?.data as { en: string; es: string };
    expect(data.en).toMatch(/^Planned, not built/);
    expect(data.en).toContain('2025 model vintage');
    expect(data.es).toMatch(/^Planificado, no construido/);
  });
});
