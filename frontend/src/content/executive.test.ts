// The executive view of Contraste (CAOS_MANAGE conventions/problem-context-first.md, BL-070): its data is valid against
// the shell's rules and its three illustrations meet the standard the shell's gate measures in the page.
import { readFileSync } from 'node:fs';
import { FOUR_CS, validateExecutive } from '@fasl-work/caos-app-shell';
import { describe, expect, it } from 'vitest';
import executive from '../../../content/executive.json';

const PUBLIC = new URL('../../public/', import.meta.url);
const NAMES = ['initiative', 'problem', 'solution'] as const;
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
  it('the executive data is valid against the shell schema, with the 4 CS absent while the shell holds none', () => {
    expect(validateExecutive(executive)).toEqual([]);
    expect('four_cs' in executive).toBe(FOUR_CS.length > 0);
  });

  it('names one executive in one organisation and a source for every figure', () => {
    expect(executive.executive.en).toBe('Chief Risk Officer');
    expect(executive.organisation.en).toMatch(/^a Chilean commercial bank/);
    expect(executive.outcomes.length).toBeGreaterThanOrEqual(3);
    expect(executive.outcomes.length).toBeLessThanOrEqual(5);
    const fields = executive.sources.map((s) => s.field);
    expect(fields).toEqual(['why_now.figure', ...executive.outcomes.map((_, i) => `outcomes[${i}].proof`)]);
    for (const s of executive.sources) {
      expect(s.source.en.length).toBeGreaterThan(80);
      expect(s.source.es.length).toBeGreaterThan(80);
    }
  });

  it('no proof is a test statistic named as such: no AUC, no p-value, no count of reproduced cells as an outcome', () => {
    for (const o of executive.outcomes) {
      const text = JSON.stringify([o.capability, o.outcome]);
      expect(text).not.toMatch(/\bAUC\b|p-value|valor p|cells|celdas/i);
    }
  });

  it('the three illustrations use only theme tokens, big labels and both languages', () => {
    for (const name of NAMES) expect(svgProblems(read(name)), name).toEqual([]);
  });

  it('the problem and the solution share the setting of the initiative', () => {
    const [ini, pro, sol] = NAMES.map((n) => rects(read(n)));
    const shared = (a: Set<string>, b: Set<string>) => [...a].filter((r) => b.has(r)).length / Math.min(a.size, b.size);
    expect(shared(pro, sol)).toBeGreaterThan(0.6);
    expect(shared(ini, pro)).toBeGreaterThan(0.6);
    expect(shared(ini, sol)).toBeGreaterThan(0.6);
  });

  it('adversarial: planted literal colours, charts, missing labels and long sentences are refused', () => {
    const svg = read('problem');
    expect(svgProblems(svg.replace('var(--color-bad)', '#ff0000'))).toContain('a literal colour');
    expect(svgProblems(svg.replace('var(--color-bad)', 'red')).join()).toMatch(/not a theme token/);
    expect(svgProblems(svg.replace('<svg ', '<svg data-chart="line" '))).toContain('declares a chart (data-chart)');
    expect(svgProblems(svg.replace(/<text data-lang="es"[^>]*>[^<]*<\/text>/, ''))[0]).toMatch(/English and \d+ Spanish/);
    expect(svgProblems(svg.replace(/ viewBox="[^"]*"/, ''))).toContain('no viewBox');
    const long = JSON.parse(JSON.stringify(executive));
    long.vision.en = Array.from({ length: 31 }, () => 'word').join(' ') + '.';
    expect(validateExecutive(long).map((p) => p.path)).toContain('vision.en');
    const unsourced = JSON.parse(JSON.stringify(executive));
    unsourced.sources.pop();
    expect(validateExecutive(unsourced).map((p) => p.message).join()).toMatch(/no source/);
  });
});
