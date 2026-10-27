// U9-W1: the Methodology topic on counterparty credit risk (pages/methodology/ccr.tsx) rendered on the server in both
// languages. ADR-0017 section 2.1 asks a `method` topic for dense paragraphs, captioned equations, a figure, exactly one
// honest callout and references; every reference the topic lists exists in the citation registry with a DOI or a URL; the
// Spanish is Spanish; the coverage row of C12 names its data and its truth status. The topic states the limits the
// research addendum marks: initial margin a regression proxy and never SIMM, the wrong-way variant without an ORE
// reconciliation, the unverified papers.
import { readFileSync } from 'node:fs';
import { CitationsProvider } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it } from 'vitest';
import { CITATIONS } from '../../content/citations';
import { CASES } from '../../content/coverage';
import { BacktestPart, CollateralPart, CvaPart, ExposurePart, RegulatoryPart, methodologySection } from '../../pages/methodology/ccr';
import { REGISTERED_SECTIONS } from '../../pages/methodologyRegistry';
import { html, setLang } from '../c03/u6-testkit';

const Body = methodologySection.Body;
const wrap = (el: React.ReactElement) => <CitationsProvider items={CITATIONS}>{el}</CitationsProvider>;
const markup = (lang: 'en' | 'es') => {
  setLang(lang);
  return html(wrap(<Body />));
};
const words = (p: string) => p.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
const paragraphs = (m: string) => [...m.matchAll(/<p>(.*?)<\/p>/gs)].map((x) => x[1]).filter((p) => words(p) >= 40);
const source = readFileSync(new URL('../../pages/methodology/ccr.tsx', import.meta.url), 'utf8');

describe('the counterparty credit risk Methodology topic', () => {
  afterEach(() => setLang('en'));

  it('is registered with the area and kind the gate reads, in a group the page already has', () => {
    expect(REGISTERED_SECTIONS.map((s) => s.id)).toContain('ccr');
    expect(methodologySection.group).toBe('market');
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
    expect(source.match(/\{ id: '[a-z]+', label: t\(/g)?.length).toBe(5);
    expect(source.match(/^ {6}<Eq$/gm)?.length ?? 0).toBeGreaterThanOrEqual(8);
    expect(source.match(/<Figure /g)?.length).toBeGreaterThanOrEqual(4);
    expect(source.match(/<Callout /g)?.length).toBe(1);
    expect(source.match(/^ {6}<P$/gm)?.length ?? 0).toBeGreaterThanOrEqual(12);
  });

  it('every part, not only the one open, has dense paragraphs, a captioned equation and Spanish decimals with a comma', () => {
    const parts = [ExposurePart, CollateralPart, CvaPart, RegulatoryPart, BacktestPart];
    for (const Part of parts) {
      for (const lang of ['en', 'es'] as const) {
        setLang(lang);
        const m = html(wrap(<Part />));
        expect(paragraphs(m).length, `${Part.name} ${lang}`).toBeGreaterThanOrEqual(2);
        if (Part !== BacktestPart || lang === 'en') expect(m.match(/class="equation"/g)?.length ?? 0, `${Part.name} ${lang}`).toBeGreaterThanOrEqual(1);
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
    const listed = [...(/refs=\{\[([^\]]*)\]\}/.exec(source)?.[1] ?? '').matchAll(/'([a-z0-9]+)'/g)].map((x) => x[1]);
    const cited = [...source.matchAll(/<Cite id="([a-z0-9]+)"/g)].map((x) => x[1]);
    expect(listed.length).toBeGreaterThanOrEqual(15);
    for (const id of new Set([...listed, ...cited])) {
      const c = CITATIONS.find((x) => x.id === id);
      expect(c, id).toBeDefined();
      expect(Boolean(c?.doi || c?.url), id).toBe(true);
    }
    for (const id of cited) expect(listed, id).toContain(id);
    expect(markup('en')).toContain(`data-refs="${listed.length}"`);
    expect(new Set(CITATIONS.map((c) => c.id)).size).toBe(CITATIONS.length);
  });

  it('states the limits: initial margin is a regression proxy and never SIMM, the wrong-way variant has no ORE reconciliation, the papers are unverified', () => {
    const en = markup('en');
    expect(en).toContain('regression proxy and never SIMM');
    expect(en).toContain('has no ORE reconciliation');
    expect(en).toContain('were not read');
    expect(en).toContain('proxy');
    const es = markup('es');
    // "proxy" translated (R3 c25 B2, the ruling of 2026-10-27)
    expect(es).toContain('aproximación por regresión y nunca SIMM');
    expect(es).toContain('no tiene conciliación con ORE');
    expect(es).toContain('no se leyeron');
  });

  it('the Spanish is written in Spanish, not the English paragraph', () => {
    const es = markup('es');
    expect(es).toContain('Riesgo de crédito de contraparte');
    expect(es).not.toContain('For a netting set with mark-to-market');
    expect(paragraphs(es).join(' ').replace(/<span translate="no">.*?<\/span>/g, '').replace(/<[^>]+>/g, ' ')).not.toMatch(/\d\.\d/);
  });

  it('has no em-dash and no emoji', () => {
    const all = markup('en') + markup('es') + source;
    expect(all).not.toMatch(/[\u2014\u2015]|[\u{1F000}-\u{1FAFF}]/u);
  });
});

describe('the coverage row of the case U9 builds', () => {
  it('names the data and the truth status of C12, built by U9, in both languages', () => {
    const row = CASES.find((c) => c.id === 'C12');
    expect(row).toBeDefined();
    expect(row?.unit).toBe('U9');
    const data = row?.data as { en: string; es: string };
    expect(data.en.length).toBeGreaterThan(20);
    expect(data.en).toContain('ORE 1.8.17.0');
    expect(data.es).not.toBe(data.en);
    const truth = row?.truth as { en: string; es: string };
    expect(truth.en).toBe('real market, synthetic trades');
    expect(truth.es).not.toBe(truth.en);
  });
});
