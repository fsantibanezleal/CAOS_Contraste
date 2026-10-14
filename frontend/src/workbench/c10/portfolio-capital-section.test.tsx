// U7-W: the Methodology topic on portfolio credit capital (pages/methodology/portfolio-capital.tsx) rendered on the
// server in both languages. ADR-0017 section 2.1 asks a `method` topic for dense paragraphs, captioned equations, a
// figure, exactly one honest callout and references; every reference the topic lists exists in the citation registry;
// the Spanish is Spanish; what the research marks unverified is said so.
import { readFileSync } from 'node:fs';
import { CitationsProvider } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it } from 'vitest';
import { CITATIONS } from '../../content/citations';
import { CASES } from '../../content/coverage';
import { methodologySection } from '../../pages/methodology/portfolio-capital';
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
const source = readFileSync(new URL('../../pages/methodology/portfolio-capital.tsx', import.meta.url), 'utf8');
/** The source of one part of the topic: from its function to the next one. */
const part = (name: string) => {
  const at = source.indexOf(`function ${name}()`);
  const next = source.indexOf('\nfunction ', at + 10);
  return source.slice(at, next === -1 ? undefined : next);
};

describe('the portfolio credit capital Methodology topic', () => {
  afterEach(() => setLang('en'));

  it('is registered in the loss group with the area and kind the gate reads', () => {
    expect(REGISTERED_SECTIONS.map((s) => s.id)).toContain('portfolio-capital');
    expect(methodologySection.group).toBe('loss');
    expect(markup('en')).toContain('data-area="method"');
    expect(markup('en')).toContain('data-method-kind="classical"');
  });

  it('opens on the Vasicek part with four dense paragraphs, captioned equations and a figure, in both languages', () => {
    for (const lang of ['en', 'es'] as const) {
      const m = markup(lang);
      expect(paragraphs(m).length, lang + ' ' + [...m.matchAll(/<p>(.*?)<\/p>/gs)].map((x) => words(x[1])).join(',')).toBeGreaterThanOrEqual(4);
      expect(m.match(/class="equation"/g)?.length ?? 0, lang).toBeGreaterThanOrEqual(2);
      expect(m.match(/<figure/g)?.length ?? 0, lang).toBeGreaterThanOrEqual(1);
      expect(m.match(/data-callout="honest"/g)?.length ?? 0, lang).toBe(1);
    }
  });

  it('has three parts, each with four paragraphs, at least two equations with captions and one figure', () => {
    for (const name of ['VasicekPart', 'CapitalPart', 'TailPart']) {
      const src = part(name);
      expect(src.match(/<P\s/g)?.length ?? 0, name).toBe(4);
      expect(src.match(/<Equation\s/g)?.length ?? 0, name).toBeGreaterThanOrEqual(2);
      expect(src.match(/caption=\{<T en=/g)?.length ?? 0, name).toBe(src.match(/<Equation\s/g)?.length ?? 0);
      expect(src.match(/<Figure /g)?.length ?? 0, name).toBe(1);
    }
    expect(source.match(/<Callout /g)?.length ?? 0).toBe(1);
  });

  it('lists and cites only references the registry holds, each with a DOI or a URL', () => {
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

  it('transcribes the constants of the sources: the IRB coefficients, the granularity test value and the unverified marks', () => {
    expect(source).toContain('0.11852');
    expect(source).toContain('0.05478');
    expect(source).toContain('12.5');
    expect(source).toContain('delta 4.83');
    expect(source).toContain('xi 0.25 and q 0.999');
    expect(source).toMatch(/unverified/);
    expect(source).toContain('infinitely granular');
  });

  it('the Spanish is written in Spanish, not the English paragraph', () => {
    const es = markup('es');
    expect(es).toContain('modelo de Vasicek');
    expect(es).not.toContain("Vasicek's model, with the foundation");
    // a paragraph number of the sources is marked translate="no" (G11); every other decimal takes a comma
    // the same rule for the other two parts, read from the source's Spanish segments
    const segments = [...source.matchAll(/es=\{<>(.*?)<\/>\}/gs)].map((x) => x[1].replace(/<Ref>.*?<\/Ref>/g, ' ').replace(/<[^>]+>/g, ' '));
    expect(segments.length).toBeGreaterThanOrEqual(19);
    for (const seg of segments) expect(seg).not.toMatch(/\d\.\d/);
    expect(paragraphs(es).join(' ').replace(/<span translate="no">.*?<\/span>/g, '').replace(/<[^>]+>/g, ' ')).not.toMatch(/\d\.\d/);
  });

  it('has no em-dash and no emoji', () => {
    const all = markup('en') + markup('es') + source;
    expect(all).not.toMatch(/[\u2014\u2015]|[\u{1F000}-\u{1FAFF}]/u);
  });
});

describe('the coverage row of the case U7 builds', () => {
  it('names the data and the truth status of C10, built by U7', () => {
    const row = CASES.find((c) => c.id === 'C10');
    expect(row).toBeDefined();
    expect(row?.unit).toBe('U7');
    const data = row?.data as { en: string; es: string };
    expect(data.en).toContain('Federal Reserve');
    expect(data.es).not.toBe(data.en);
    expect((row?.truth as { en: string }).en).toContain('known truth');
  });
});
