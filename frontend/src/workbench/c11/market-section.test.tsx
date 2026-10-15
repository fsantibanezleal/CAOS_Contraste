// U8-W: the Methodology topic on market risk (pages/methodology/market.tsx) rendered on the server in both languages.
// ADR-0017 section 2.1 asks a `method` topic for dense paragraphs, captioned equations, a figure, exactly one honest
// callout and references; every reference the topic lists exists in the citation registry; the Spanish is Spanish; the
// numbers of MAR32.9 and MAR32.42 are the transcribed ones.
import { readFileSync } from 'node:fs';
import { CitationsProvider } from '@fasl-work/caos-app-shell';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import { CITATIONS } from '../../content/citations';
import { CASES } from '../../content/coverage';
import { BacktestsPart, DeskPart, EstimatorsPart, methodologySection } from '../../pages/methodology/market';
import { REGISTERED_SECTIONS } from '../../pages/methodologyRegistry';
import { html, setLang } from '../c03/u6-testkit';

const render = (el: ReactElement, lang: 'en' | 'es') => {
  setLang(lang);
  return html(<CitationsProvider items={CITATIONS}>{el}</CitationsProvider>);
};
const Body = methodologySection.Body;
const words = (p: string) => p.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
const paragraphs = (m: string) => [...m.matchAll(/<p>(.*?)<\/p>/gs)].map((x) => x[1]).filter((p) => words(p) >= 40);
const PARTS: Array<[string, () => ReactElement]> = [
  ['estimators', () => <EstimatorsPart />],
  ['back-tests', () => <BacktestsPart />],
  ['desk tests', () => <DeskPart />],
];

describe('the market risk Methodology topic', () => {
  afterEach(() => setLang('en'));

  it('is registered in the market group with the area and kind the gate reads, and holds one honest callout', () => {
    expect(REGISTERED_SECTIONS.map((s) => s.id)).toContain('market');
    expect(methodologySection.group).toBe('market');
    const m = render(<Body />, 'en');
    expect(m).toContain('data-area="method"');
    expect(m).toContain('data-method-kind="classical"');
    for (const lang of ['en', 'es'] as const) expect(render(<Body />, lang).match(/data-callout="honest"/g)?.length, lang).toBe(1);
  });

  it('every part has its dense paragraphs, captioned equations and a figure, in both languages', () => {
    for (const [name, Part] of PARTS) {
      for (const lang of ['en', 'es'] as const) {
        const m = render(<Part />, lang);
        expect(paragraphs(m).length, `${name} ${lang}`).toBeGreaterThanOrEqual(3);
        expect(m.match(/class="equation"/g)?.length ?? 0, `${name} ${lang}`).toBeGreaterThanOrEqual(2);
        expect(m.match(/<figure/g)?.length ?? 0, `${name} ${lang}`).toBeGreaterThanOrEqual(1);
      }
    }
    const first = render(<Body />, 'en');
    expect(paragraphs(first).length).toBeGreaterThanOrEqual(4);
  });

  it('transcribes the MAR32.9 table, the MAR32.42 boundaries and the Z2 reference from the dossiers', () => {
    const bt = render(<BacktestsPart />, 'en');
    for (const v of ['8.11', '28.58', '54.32', '75.81', '89.22', '95.88', '98.63', '99.60', '99.89', '99.97', '99.99', '3.841', '5.991', '1.50', '2.00', '-0.70', '-1.8']) expect(bt, v).toContain(v);
    const desk = render(<DeskPart />, 'en');
    for (const v of ['0.80', '0.09', '0.70', '0.12', '0.264', '0.055', '0.004', 'MAR32.42']) expect(desk, v).toContain(v);
    expect(desk).toContain('more than 12 exceptions at 99 %');
    expect(desk).toContain('more than 30 at 97.5 %');
    // the published Z2 points are a reference, never a threshold
    expect(bt).toContain('only as a published reference, never as a threshold');
  });

  it('lists and cites only references the registry holds, each with a DOI or a URL', () => {
    const source = readFileSync(new URL('../../pages/methodology/market.tsx', import.meta.url), 'utf8');
    const listed = [...(/refs=\{\[([^\]]*)\]\}/.exec(source)?.[1] ?? '').matchAll(/'([a-z0-9]+)'/g)].map((x) => x[1]);
    const cited = [...source.matchAll(/<Cite id="([a-z0-9]+)"/g)].map((x) => x[1]);
    expect(listed.length).toBe(29);
    for (const id of new Set([...listed, ...cited])) {
      const c = CITATIONS.find((x) => x.id === id);
      expect(c, id).toBeDefined();
      expect(Boolean(c?.doi || c?.url), id).toBe(true);
    }
    for (const id of cited) expect(listed, id).toContain(id);
    expect(render(<Body />, 'en')).toContain('data-refs="29"');
    expect(new Set(CITATIONS.map((c) => c.id)).size).toBe(CITATIONS.length);
  });

  it('the Spanish is written in Spanish, with decimal commas outside a source reference', () => {
    for (const [name, Part] of PARTS) {
      const es = render(<Part />, 'es');
      expect(paragraphs(es).join(' ').replace(/<span translate="no">.*?<\/span>/g, '').replace(/<[^>]+>/g, ' '), name).not.toMatch(/\d\.\d/);
    }
    expect(render(<EstimatorsPart />, 'es')).toContain('Contraste fija una convención de signo');
    expect(render(<EstimatorsPart />, 'es')).not.toContain('Contraste fixes one sign convention');
    expect(render(<DeskPart />, 'es')).toContain('0,264');
  });

  it('has no em-dash, no en-dash, no arrow and no emoji', () => {
    const all = PARTS.map(([, P]) => render(<P />, 'en') + render(<P />, 'es')).join('') + render(<Body />, 'en') + render(<Body />, 'es');
    expect(all).not.toMatch(/[\u2013\u2014\u2015\u2190-\u21ff\u27f5-\u27ff]|[\u{1F000}-\u{1FAFF}]/u);
  });
});

describe('the coverage rows of the cases U8 builds', () => {
  it('name the data and the truth status of C11 and C13, built by U8', () => {
    for (const [id, truth] of [['C11', 'real outcomes'], ['C13', 'known truth']] as const) {
      const row = CASES.find((c) => c.id === id);
      expect(row, id).toBeDefined();
      expect(row?.unit).toBe('U8');
      expect((row?.truth as { en: string }).en).toBe(truth);
      const data = row?.data as { en: string; es: string };
      expect(data.en.length).toBeGreaterThan(20);
      expect(data.es).not.toBe(data.en);
    }
    expect((CASES.find((c) => c.id === 'C11')?.data as { en: string }).en).toContain('derived results only');
  });
});
