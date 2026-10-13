// U6-W: the Methodology topic on LGD and EAD (pages/methodology/lgd-ead.tsx) rendered on the server in both languages.
// ADR-0017 section 2.1 asks a `method` topic for dense paragraphs, captioned equations, a figure, exactly one honest
// callout and references; every reference the topic lists exists in the citation registry; the Spanish is Spanish.
import { readFileSync } from 'node:fs';
import { CitationsProvider } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it } from 'vitest';
import { CITATIONS } from '../../content/citations';
import { CASES } from '../../content/coverage';
import { methodologySection } from '../../pages/methodology/lgd-ead';
import { REGISTERED_SECTIONS } from '../../pages/methodologyRegistry';
import { html, setLang } from '../c03/u6-testkit';

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

describe('the LGD and EAD Methodology topic', () => {
  afterEach(() => setLang('en'));

  it('is registered in the loss severity and exposure group (a group of its own, so no group holds more than the six peers rule 5 allows) with the area and kind the gate reads', () => {
    expect(REGISTERED_SECTIONS.map((s) => s.id)).toContain('lgd-ead');
    expect(methodologySection.group).toBe('loss');
    expect(markup('en')).toContain('data-area="method"');
    expect(markup('en')).toContain('data-method-kind="classical"');
  });

  it('opens on the LGD part with four dense paragraphs, captioned equations and a figure, in both languages', () => {
    for (const lang of ['en', 'es'] as const) {
      const m = markup(lang);
      expect(paragraphs(m).length, lang).toBeGreaterThanOrEqual(4);
      expect(m.match(/class="equation"/g)?.length ?? 0, lang).toBeGreaterThanOrEqual(2);
      expect(m.match(/<figure/g)?.length ?? 0, lang).toBeGreaterThanOrEqual(1);
      expect(m.match(/data-callout="honest"/g)?.length ?? 0, lang).toBe(1);
    }
  });

  it('lists and cites only references the registry holds, each with a DOI or a URL', () => {
    const source = readFileSync(new URL('../../pages/methodology/lgd-ead.tsx', import.meta.url), 'utf8');
    const listed = [...(/refs=\{\[([^\]]*)\]\}/.exec(source)?.[1] ?? '').matchAll(/'([a-z0-9]+)'/g)].map((x) => x[1]);
    const cited = [...source.matchAll(/<Cite id="([a-z0-9]+)"/g)].map((x) => x[1]);
    expect(listed.length).toBe(21);
    for (const id of new Set([...listed, ...cited])) {
      const c = CITATIONS.find((x) => x.id === id);
      expect(c, id).toBeDefined();
      expect(Boolean(c?.doi || c?.url), id).toBe(true);
    }
    for (const id of cited) expect(listed, id).toContain(id);
    expect(markup('en')).toContain('data-refs="21"');
    expect(new Set(CITATIONS.map((c) => c.id)).size).toBe(CITATIONS.length);
  });

  it('the Spanish is written in Spanish, not the English paragraph', () => {
    const es = markup('es');
    expect(es).toContain('pérdida realizada');
    expect(es).not.toContain('The realised loss of a defaulted exposure');
    // a paragraph number of the framework is marked translate="no" (G11); every other decimal takes a comma
    expect(paragraphs(es).join(' ').replace(/<span translate="no">.*?<\/span>/g, '').replace(/<[^>]+>/g, ' ')).not.toMatch(/\d\.\d/);
  });

  it('has no em-dash and no emoji', () => {
    const all = markup('en') + markup('es');
    expect(all).not.toMatch(/[\u2014\u2015]|[\u{1F000}-\u{1FAFF}]/u);
  });
});

describe('the coverage rows of the cases U6 builds', () => {
  it('name the data and the truth status of C03, C08 and C09, built by U6', () => {
    for (const id of ['C03', 'C08', 'C09']) {
      const row = CASES.find((c) => c.id === id);
      expect(row, id).toBeDefined();
      expect(row?.unit).toBe('U6');
      const data = row?.data as { en: string; es: string };
      expect(data.en.length).toBeGreaterThan(20);
      expect(data.es).not.toBe(data.en);
    }
  });
});
