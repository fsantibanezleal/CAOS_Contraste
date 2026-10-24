// U16-R2b (batch c12): every hyperparameter the documents list is named in words (B2: five printed as ids, in the Spanish view too),
// and the Z2 chart keeps every mark (M1: a mark between the outer bin edge and its centre fell off the axis, 45 of 168 states).
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { committed } from '../c08/spanish-testkit';
import { HYPERPARAMETER_TEXT, REASON_ES } from './selection';

const FILES = ['calm-2004-06.json', 'equity-2007-09.json', 'equity-2020.json', 'fx-2008.json', 'mixed-2023.json', 'rates-2022.json'];

describe('U16-R2b c12: C11', () => {
  it('B2: names every hyperparameter key of every document', () => {
    for (const f of FILES) {
      const o = committed<{ outputs: { hyperparameters: { others: Array<{ name: string }> } } }>('C11', f).outputs;
      for (const h of o.hyperparameters.others) expect(HYPERPARAMETER_TEXT[h.name], `${f} ${h.name}`).toBeDefined();
    }
  });
  it('M3: the FZ0 reason has its Spanish', () => {
    expect(REASON_ES['the model forecasts no ES: FZ0 is not defined']).toMatch(/no pronostica ES/);
  });
  it('M1: the axis of the Z2 chart extends past the outer bin centres, where the bars are drawn', () => {
    const src = readFileSync(new URL('./BacktestViews.tsx', import.meta.url), 'utf8');
    expect(src).toMatch(/const lo = Math\.min\(c0,/);
    expect(src).toMatch(/\.\.\.\(hi > cN \? \[hi \+ pad\] : \[\]\)/);
  });
});
