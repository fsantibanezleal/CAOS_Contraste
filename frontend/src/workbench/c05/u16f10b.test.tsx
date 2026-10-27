// U16-F10b (fix round 4, R3 c06 minors of C05 and c05 minors of C04), on the committed documents and the view sources: the Context
// names the data readers and quotes the paper's "All" row (n5), the level mark says what it is (m9), the captions name no pixel
// width and no "beside" for a chart above (m2, m4); C04 prints no engine function or class in prose (m10) and no equation number
// as a header (m12).
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { committedData, render, textOf } from '../c03/u16f2-kit';
import { C05ContextView } from './C05Common';
import type { C05Sel } from './selection';

const sel = (): C05Sel => ({ data: committedData('C05'), alphas: { amber: 0.05, red: 0.01 } } as unknown as C05Sel);
const src = (rel: string) => readFileSync(new URL(rel, import.meta.url), 'utf8');

describe('U16-R3 c06 and c05 minors', () => {
  it('n5: the Context names the data readers and quotes the paper row in Spanish', () => {
    const en = textOf(render(<C05ContextView sel={sel()} />, 'en'));
    const es = textOf(render(<C05ContextView sel={sel()} />, 'es'));
    expect(en).toContain('The data readers check each paper');
    expect(es).toContain('Los lectores de datos verifican');
    expect(es).toContain('su fila «All» (el total)');
  });

  it('m2, m4 and m9: no pixel width, no "beside" for a stacked chart, a level mark in words', () => {
    const sp = src('./SpViews.tsx');
    expect(sp).not.toContain('1500 px');
    expect(sp).not.toContain('The chart beside draws every case 1');
    expect(src('./LdpViews.tsx')).not.toMatch(/label: \{ en: 'rail', es: 'panel' \}/);
  });

  it('C04 m10 and m12: no engine function or module in prose, no equation number as a header', () => {
    const fam = src('../c04/FamilyViews.tsx');
    expect(fam).not.toContain("riskvalidation's size_bound");
    expect(fam).not.toContain('el size_bound de riskvalidation');
    expect(fam).not.toMatch(/\(riskvalidation\.transitions\.em\)/);
    expect(src('../c04/C04Common.tsx')).not.toContain("riskvalidation's RatingPaths generator");
    expect(src('../c04/LiveViews.tsx')).not.toContain('<Ref>(3.4)</Ref>');
  });
});
