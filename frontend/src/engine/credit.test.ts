// CT-209: every live C05 calculator equals riskvalidation 0.2.0 on the parity points the pipeline exports with each
// artifact, within 1e-9 relative: the IRB risk weight by regime, the most prudent bounds (independent, correlated and
// scaled), and the four case 1 calibrations of Tasche (2013) with their quasi moment matching.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { calibrate, irbCapital, mostPrudent, mostPrudentScaled, ncdf, nquantile, type Case1, type Quadrature, type Regime } from './credit';

const derived = new URL('../../../data/derived/', import.meta.url);
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const read = (rel: string): any => JSON.parse(readFileSync(new URL(rel, derived), 'utf8'));
const manifest = read('manifests/C05.json');
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const variants: Record<string, any> = Object.fromEntries(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  manifest.artifacts.filter((a: any) => a.role === 'variant').map((a: any) => [a.variant_id, read(a.path)]),
);
const quad: Quadrature = read('C05/models-ldp.json').model[0].details.quadrature;

const close = (got: number, want: number, rel = 1e-9) => {
  expect(Math.abs(got - want)).toBeLessThanOrEqual(rel * Math.max(Math.abs(want), 1e-300));
};

describe('the normal distribution', () => {
  it('matches known values to near machine precision', () => {
    close(ncdf(0), 0.5, 1e-15);
    close(ncdf(-1.959963984540054), 0.025, 1e-13);
    close(ncdf(-6), 9.865876450376981e-10, 1e-12);
    close(ncdf(3.090232306167813), 0.999, 1e-14);
    close(nquantile(0.999), 3.090232306167813, 1e-13);
    close(nquantile(0.0005), -3.290526731491926, 1e-13);
    for (const p of [1e-10, 1e-4, 0.01, 0.3, 0.5, 0.7, 0.99]) close(ncdf(nquantile(p)), p, 1e-12);
  });
});

describe('the IRB risk weight equals regulatory.irb on the exported points', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const pts: any[] = variants['sp-2010'].outputs.parity.irb;
  it(`${pts.length} points across Basel III, CRR3 and Basel II`, () => {
    expect(pts.length).toBeGreaterThan(40);
    for (const p of pts) close(irbCapital(p.asset_class, p.pd, p.lgd, { maturity: p.maturity, regime: p.regime as Regime }).riskWeight, p.risk_weight);
  });
});

describe('the most prudent bounds equal engines.low_default on the exported points', () => {
  const par = variants['ldp-published'].outputs.parity.bounds;
  it(`${par.points.length} observations, levels and correlations`, () => {
    for (const p of par.points) {
      const live = mostPrudent(par.obligors, p.defaults, p.gamma, p.rho, quad);
      live.forEach((v: number, i: number) => close(v, p.pd[i]));
      const scaled = mostPrudentScaled(par.obligors, p.defaults, p.gamma, p.rho, quad);
      scaled.pd.forEach((v: number, i: number) => close(v, p.scaled_upper_bound[i]));
    }
  });
});

describe('the case 1 calibrations equal engines.pd_curve on the exported grid of forecast PDs', () => {
  for (const vid of ['sp-2010', 'sp-2011']) {
    const o = variants[vid].outputs;
    const model = { curve0: o.qmm0.curve, pd0: o.qmm0.pd, ar0: o.ar0, defaultProfile0: o.default_profile0 };
    it(vid, () => {
      for (const p1 of o.parity.calibration.pd_grid) {
        const key = p1.toFixed(6);
        for (const approach of ['A1-idp', 'A2-iar', 'A3-spd', 'A4-slr'] as Case1[]) {
          const want: number[] = o.parity.calibration.curves[key][approach];
          const got = calibrate(approach, model, o.profile1, p1).curve;
          expect(got.length).toBe(want.length);
          got.forEach((v, i) => close(v, want[i]));
        }
      }
    });
  }
});
