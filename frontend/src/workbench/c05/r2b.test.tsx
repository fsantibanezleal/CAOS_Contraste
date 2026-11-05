// U16-R2b (batch c06, C05): the Spanish Context names the paper's tables in Spanish (B1: ", Tables 2 to 9"), the size-and-power rows
// are named (B3: "jeffreys, A"), and the notes of the recomputed tables read in Spanish (M2).
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { committedData, render, textOf } from '../c03/u16f2-kit';
import { C05ContextView } from './C05Common';
import type { C05Sel } from './selection';

const sel = (): C05Sel => ({ data: committedData('C05'), alphas: { amber: 0.05, red: 0.01 } } as unknown as C05Sel);

describe('U16-R2b c06: C05', () => {
  it('B1: the Spanish context names the tables of each source in Spanish, the paper titles as published', () => {
    const es = textOf(render(<C05ContextView sel={sel()} />, 'es'));
    expect(es).not.toMatch(/\bTables \d/);
    expect(es).toContain('tablas 2 a 9');
    expect(es).toContain('The art of probability-of-default curve calibration');
    expect(textOf(render(<C05ContextView sel={sel()} />, 'en'))).toContain('Tables 2 to 9');
  });
  it('B3 and M2: the size-and-power rows go through the test names, and every note of the committed golden block has its Spanish', () => {
    const src = readFileSync(new URL('./LdpViews.tsx', import.meta.url), 'utf8');
    expect(src).not.toMatch(/k\.replace\('_', ', '\)/);
    const notes = Object.values(JSON.parse(readFileSync(new URL('../../../../data/derived/C05/ldp-published.json', import.meta.url), 'utf8')).outputs.golden.notes as Record<string, string>);
    for (const n of notes) expect(src, n).toContain(JSON.stringify(n).slice(1, 30).replace(/\\"/g, '"'));
  });
});
