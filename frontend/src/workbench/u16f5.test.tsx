// U16-F5: the shared views and the pages, fix round 2. One describe per row or minor of the U16-R2 triage that this unit
// owns; each fails on the defect the second capture review found, in both languages where the defect is a language one.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const here = (rel: string) => new URL(rel, import.meta.url);
const text = (rel: string) => readFileSync(here(rel), 'utf8');
const css = text('../styles/contraste.css');

/** The rules inside every `@media (<feature>: <px>px)` block of the product stylesheet, braces balanced. */
function media(feature: 'max-width' | 'min-width', px: number): string {
  const out: string[] = [];
  const re = new RegExp(`@media \\(${feature}: ${px}px\\)\\s*\\{`, 'g');
  for (let m = re.exec(css); m; m = re.exec(css)) {
    let depth = 1;
    let i = m.index + m[0].length;
    const start = i;
    while (i < css.length && depth) depth += css[i] === '{' ? 1 : css[i] === '}' ? -1 : 0, i++;
    out.push(css.slice(start, i - 1));
  }
  return out.join('\n');
}

describe('VS-1, V02-4, V06-5, V21-1: a table of a filling card keeps its rows at 390', () => {
  const narrow = media('max-width', 900);
  it('a scroll box (.ct-scroll, also inside a stack) flows below 900 px instead of keeping the clamp of the card', () => {
    expect(narrow).toMatch(/\.ct-scroll[^{]*\{[^}]*height:\s*auto/);
    expect(narrow).toMatch(/\.ct-stack\s*>\s*\.ct-scroll[^{]*\{[^}]*flex:\s*none/);
  });
  it('the card body that holds a scroll box grows with it', () => {
    expect(narrow).toMatch(/:has\(\.ct-scroll\)[^{]*\{[^}]*height:\s*auto/);
  });
});

describe('V21-4: each evidence chart keeps room for at least three y ticks, its title, legend and readout', () => {
  const src = text('./c21/FindingsEvidence.tsx');
  it('asks for at least 21 rem a chart (the plot kept 76 px of 15 rem at 1280 x 800)', () => {
    const m = /'--ct-chart-min': '(\d+(?:\.\d+)?)rem'/.exec(src);
    expect(m).not.toBeNull();
    expect(Number(m![1])).toBeGreaterThanOrEqual(21);
  });
  it('the card of the evidence is not shorter than its drawings below 900 px either', () => {
    expect(media('max-width', 900)).toMatch(/finding-evidence[^{]*\.ct-stack-chart[^{]*\{[^}]*height:/);
  });
});

describe('V21-5: a scroll box never ends in a line cut through its middle', () => {
  const wide = media('min-width', 901);
  for (const cls of ['.ct-stack-table', '.ct-stack-rest', '.ct-stack-fill', '.ct-scroll']) {
    it(`${cls} fades its bottom edge and keeps a gap under its last row`, () => {
      const rule = new RegExp(`${cls.replace('.', '\\.')}[^{}]*\\{[^}]*\\}`, 'g');
      const rules = (wide.match(rule) ?? []).join('\n');
      expect(rules).toMatch(/mask-image:\s*linear-gradient/);
      expect(rules).toMatch(/padding-bottom:/);
    });
  }
});
