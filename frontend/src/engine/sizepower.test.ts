// CT-308: the live exact size and power of the count tests against riskvalidation on the parity points the pipeline
// exports in C22's models artifact (1e-9 relative; 1e-12 absolute for tails below that), critical counts equal.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import type { C22Fit, ModelsArtifact } from '../lib/contract.types';
import type { Quadrature } from './credit';
import { betaCdf, binomTail, criticalCount, lgamma, rejectionProbability, type CountTest } from './sizepower';

const derived = new URL('../../../data/derived/', import.meta.url);
const models = JSON.parse(readFileSync(new URL('C22/models-generators.json', derived), 'utf8')) as ModelsArtifact<C22Fit>;
const quad = (models.model.find((m) => m.id === 'X1-exact')?.details as { quadrature: Quadrature }).quadrature;

describe('the special functions', () => {
  it('log gamma and the incomplete beta at known values', () => {
    expect(lgamma(1)).toBeCloseTo(0, 14);
    expect(lgamma(0.5)).toBeCloseTo(0.5 * Math.log(Math.PI), 14);
    expect(lgamma(101)).toBeCloseTo(363.73937555556347, 9); // ln(100!)
    expect(betaCdf(0.3, 1, 1)).toBeCloseTo(0.3, 14);
    expect(betaCdf(0.5, 2.5, 2.5)).toBeCloseTo(0.5, 14);
    expect(binomTail(1, 10, 0.1)).toBeCloseTo(1 - 0.9 ** 10, 14);
    expect(binomTail(0, 10, 0.1)).toBe(1);
    expect(binomTail(11, 10, 0.1)).toBe(0);
  });
});

describe('CT-308: the count tests, exactly as riskvalidation computes them', () => {
  it(`every one of the ${models.fit.parity.length} parity points`, () => {
    expect(models.fit.parity.length).toBeGreaterThan(100);
    for (const pt of models.fit.parity) {
      const test = pt.test_id as CountTest;
      const k = criticalCount(test, pt.n, pt.pd, pt.alpha, pt.rho_assumed ?? 0, quad);
      expect(k, JSON.stringify(pt)).toBe(pt.critical_count);
      const r = rejectionProbability(test, pt.n, pt.pd, pt.alpha, pt.pd * pt.ratio, pt.rho_true, pt.rho_assumed ?? 0, quad);
      expect(Math.abs(r.probability - pt.probability), JSON.stringify(pt)).toBeLessThanOrEqual(1e-9 * Math.abs(pt.probability) + 1e-12);
    }
  });
});
