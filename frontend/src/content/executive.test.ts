// The executive view of Contraste (CAOS_MANAGE conventions/problem-context-first.md, BL-073, schema 2.0.0): its data is valid against
// the shell's rules and its three illustrations meet the standard the shell's gate measures in the page.
import { readFileSync } from 'node:fs';
import { EXECUTIVE_SCHEMA_VERSION, FOUR_CS, validateExecutive } from '@fasl-work/caos-app-shell';
import { describe, expect, it } from 'vitest';
import executive from '../../../content/executive.json';

const PUBLIC = new URL('../../public/', import.meta.url);
const NAMES = ['pain', 'situation', 'proposal'] as const;
const read = (name: (typeof NAMES)[number]) => readFileSync(new URL(executive.illustrations[name].file as string, PUBLIC), 'utf8');

const TOKEN = /^(none|currentColor|var\(--color-[a-z0-9-]+\))$/;

/** What is wrong with one illustration, in the terms of the gate: literal colours, charts, labels without a twin, no viewBox. */
export function svgProblems(svg: string): string[] {
  const out: string[] = [];
  if (!/viewBox="[^"]+"/.test(svg)) out.push('no viewBox');
  if (/<(img|image|script|foreignObject)\b/i.test(svg)) out.push('holds an img, image, script or foreignObject');
  if (/data-chart/i.test(svg)) out.push('declares a chart (data-chart)');
  if (/#[0-9a-f]{3,8}\b|rgba?\(|hsla?\(/i.test(svg)) out.push('a literal colour');
  for (const m of svg.matchAll(/\b(fill|stroke|stop-color|flood-color)="([^"]*)"/g)) {
    if (!TOKEN.test(m[2])) out.push(`${m[1]}="${m[2]}" is not a theme token`);
  }
  for (const m of svg.matchAll(/style="([^"]*)"/g)) {
    if (/(fill|stroke|color)\s*:/.test(m[1])) out.push('a colour set in a style attribute');
  }
  const count = (lang: string) => [...svg.matchAll(new RegExp(`<text[^>]*data-lang="${lang}"`, 'g'))].length;
  if (count('en') < 4) out.push(`only ${count('en')} English label(s)`);
  if (count('en') !== count('es')) out.push(`${count('en')} English and ${count('es')} Spanish labels`);
  if (/<text(?![^>]*data-lang=)/.test(svg)) out.push('a label with no data-lang');
  if (/font-family/.test(svg)) out.push('a label sets its own font family');
  for (const m of svg.matchAll(/<text[^>]*font-size="([\d.]+)"/g)) if (Number(m[1]) < 18) out.push(`a label at ${m[1]} in a 640 wide drawing is under 9 px on a phone`);
  return [...new Set(out)];
}

/** The geometry of every rectangle, so two scenes can be compared for the setting they share. */
const rects = (svg: string) => new Set([...svg.matchAll(/<rect x="([\d.-]+)" y="([\d.-]+)" width="([\d.-]+)" height="([\d.-]+)"/g)].map((m) => m.slice(1, 5).join(',')));

describe('the Contraste executive view', () => {
  it('the data is valid against the shell schema 2.0.0 and the 4 CS are present in order', () => {
    expect(EXECUTIVE_SCHEMA_VERSION).toBe('2.0.0');
    expect(validateExecutive(executive)).toEqual([]);
    expect(executive.proposal.four_cs.map((c) => c.c.en)).toEqual(FOUR_CS.map((c) => c.name.en));
  });

  it('keeps the supervisor figure as a headline, with its linked source and no bank named', () => {
    const cmf = executive.headline_figures.find((f) => f.value.en === '571');
    expect(cmf, 'the 571 million figure').toBeDefined();
    expect(cmf!.unit.en).toMatch(/million US dollars/);
    expect(cmf!.unit.en).toMatch(/January 2031/);
    const src = executive.sources.find((s) => s.id === cmf!.source);
    expect(src!.url).toMatch(/^https:\/\/www\.cmfchile\.cl\//);
  });

  it('every source is an https link whose title and note are not a file name', () => {
    expect(executive.sources.length).toBeGreaterThanOrEqual(8);
    for (const s of executive.sources) {
      expect(s.url, s.id).toMatch(/^https:\/\/[^\s]+$/);
      expect(`${s.title.en} ${s.title.es} ${'note' in s ? JSON.stringify(s.note) : ''}`, s.id).not.toMatch(/\bfile\s*\d|\barchivo\s*\d|\.pdf\b/i);
    }
  });

  it('is general: no named bank, no first person, no offer, no price', () => {
    const text = JSON.stringify({ ...executive, sources: [] });
    expect(text).not.toMatch(/Contraste|Banco Andino|Santander|BancoEstado|Itaú|Scotiabank|Banco de Chile|BBVA|HSBC|\bour\b|\bwe\b|nuestro|nosotros/i);
  });

  it('has more than the floors: the five sections read as a document', () => {
    const words = (v: unknown): number => (typeof v === 'string' ? v.split(/\s+/).filter(Boolean).length : v && typeof v === 'object' ? Object.entries(v as object).reduce((n, [k, x]) => n + (k === 'es' ? 0 : words(x)), 0) : 0);
    const total = words({ ...executive, sources: [], illustrations: [] });
    expect(total).toBeGreaterThan(1500);
    expect(total).toBeLessThan(3200);
  });

  it('the three illustrations use only theme tokens, big labels and both languages', () => {
    expect(Object.keys(executive.illustrations).sort()).toEqual(['pain', 'proposal', 'situation']);
    for (const name of NAMES) expect(svgProblems(read(name)), name).toEqual([]);
  });

  it('the illustrations name no organisation and none is a chart', () => {
    for (const name of NAMES) {
      const svg = read(name);
      expect(svg, name).not.toMatch(/\bCMF\b|\bECB\b|\bBCE\b|\bEBA\b|\bPRA\b|\bOSFI\b|\bFed\b|Basel|Basilea/);
      expect(svg, name).not.toMatch(/<(polyline|axis)\b|tick|axis/i);
    }
  });

  it('the pain and the proposal share the setting', () => {
    const [pain, , proposal] = NAMES.map((n) => rects(read(n)));
    const shared = [...pain].filter((r) => proposal.has(r)).length / Math.min(pain.size, proposal.size);
    expect(shared).toBeGreaterThan(0.6);
  });

  it('adversarial: planted literal colours, charts, missing labels and long sentences are refused', () => {
    const svg = read('pain');
    expect(svgProblems(svg.replace('var(--color-bad)', '#ff0000'))).toContain('a literal colour');
    expect(svgProblems(svg.replace('var(--color-bad)', 'red')).join()).toMatch(/not a theme token/);
    expect(svgProblems(svg.replace('<svg ', '<svg data-chart="line" '))).toContain('declares a chart (data-chart)');
    expect(svgProblems(svg.replace(/<text data-lang="es"[^>]*>[^<]*<\/text>/, ''))[0]).toMatch(/English and \d+ Spanish/);
    expect(svgProblems(svg.replace(/ viewBox="[^"]*"/, ''))).toContain('no viewBox');
    const long = JSON.parse(JSON.stringify(executive));
    long.key_statement.en = Array.from({ length: 31 }, () => 'word').join(' ') + '.';
    expect(validateExecutive(long).map((p) => p.path)).toContain('key_statement.en');
    const unsourced = JSON.parse(JSON.stringify(executive));
    unsourced.sources.pop();
    expect(validateExecutive(unsourced).length).toBeGreaterThan(0);
    const promo = JSON.parse(JSON.stringify(executive));
    promo.proposal.paragraphs[0].en += ' Contact us to buy it.';
    expect(validateExecutive(promo).length).toBeGreaterThan(0);
  });
});
