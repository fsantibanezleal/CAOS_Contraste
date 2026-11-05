// U16-R2b (batch c12): every hyperparameter the documents list is named in words (B2: five printed as ids, in the Spanish view too),
// and the Z2 chart keeps every mark (M1: a mark between the outer bin edge and its centre fell off the axis, 45 of 168 states).
import { z2Axis } from './BacktestViews';
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
  it('M1: the axis of the Z2 chart extends past the outer bin centres, where the bars are drawn (run, not read: R3 c12 m14)', () => {
    // a realised Z2 of 1.0 on the last edge, past the last centre 0.95: the axis takes a point beyond it
    const centers = [-0.95, -0.85, 0.85, 0.95];
    const right = z2Axis(centers, [1.0]);
    expect(right.front).toBe(0);
    expect(right.xs.at(-1)!).toBeGreaterThan(1.0);
    expect(right.xs.slice(0, centers.length)).toEqual(centers);
    // a critical value left of the first centre: one point before it, and front says so
    const left = z2Axis(centers, [-1.8, 0]);
    expect(left.front).toBe(1);
    expect(left.xs[0]).toBeLessThan(-1.8);
    // every mark inside: the centres alone
    expect(z2Axis(centers, [0.1, -0.2])).toEqual({ xs: centers, front: 0 });
  });
});
