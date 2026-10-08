// CT-410, CT-411: the live C04 ports against riskvalidation on the parity points the pipeline exports in C04's models
// artifact (fit.parity, contract section 4), within 1e-9 relative (1e-12 absolute below that): every projection (the
// default rate of each year, the last portfolio, the TTC portfolio and its default rate, also under the origination
// printed to rounding, which the engine normalises) with each date's L1 distance to the TTC portfolio, every interval
// (Wald and Agresti-Coull at their correlation, the effective number of observations, Jeffreys; at 90, 95 and 99% and
// at CEREP's pooled sizes) and every IRB risk weight (a PD of 0 at the floor's). Known values that need no artifact:
// Schuermann and Hanson's Table 5 (BB, 2002, 15 defaults of 531 obligors), the engine's (3.4) with unequal trials, the
// TTC portfolio of two grades in closed form, the first period of (9) from a start with a share already in default,
// the engine's 1e-3 tolerance on a row, the origination and the start, the capital of a portfolio by grade with a
// grade without a PD, and the refusals: no input is coerced. The artifact is read from the path in C04_PARITY when it
// is set (a development preview), else from data/derived/C04/models-transitions.json.
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { irbCapital, type AssetClass, type Regime } from './credit';
import { betaCdf } from './sizepower';
import {
  betaQuantile,
  effectiveN,
  isPrimitive,
  pdAgrestiCoull,
  pdJeffreys,
  pdWald,
  portfolioRiskWeight,
  project,
  propagationMatrix,
  ttcPortfolio,
  type IrbAssumptions,
} from './transitions';

interface ProjectionPoint {
  agency: string;
  matrix: number[][];
  origination: number[];
  w0: number[];
  years: number;
  default_rate: number[];
  portfolio_last: number[];
  ttc: number[];
  ttc_default_rate: number;
}

interface IntervalPoint {
  defaults: number;
  n: number;
  rho: number;
  level: number;
  wald: [number, number];
  agresti_coull: [number, number];
  jeffreys: [number, number];
  n_effective: number;
}

interface CapitalPoint {
  pd: number;
  lgd: number;
  maturity: number;
  regime: Regime;
  asset_class: AssetClass;
  risk_weight: number;
}

interface C04Parity {
  projection: ProjectionPoint[];
  intervals: IntervalPoint[];
  capital: CapitalPoint[];
}

const DERIVED = new URL('../../../data/derived/C04/models-transitions.json', import.meta.url);
const ARTIFACT = process.env.C04_PARITY || fileURLToPath(DERIVED);
let cached: C04Parity | undefined;

/** The parity block, read once; a missing artifact fails the parity tests (a gate never passes without its subject). */
function parity(): C04Parity {
  if (!cached) {
    if (!existsSync(ARTIFACT)) {
      throw new Error(`no C04 models artifact at ${ARTIFACT}: bake C04, or point C04_PARITY at a preview`);
    }
    cached = (JSON.parse(readFileSync(ARTIFACT, 'utf8')) as { fit: { parity: C04Parity } }).fit.parity;
  }
  return cached;
}

const close = (got: number, want: number, what: string): void => {
  expect(Math.abs(got - want), `${what}: got ${got}, want ${want}`).toBeLessThanOrEqual(1e-9 * Math.abs(want) + 1e-12);
};
const closeAll = (got: readonly number[], want: readonly number[], what: string): void => {
  expect(got.length, what).toBe(want.length);
  got.forEach((v, i) => close(v, want[i], `${what}[${i}]`));
};
/** Whether a value rounds to the printed one: within half a unit of the printed last digit. */
const printsAs = (value: number, printed: number, decimals: number): boolean =>
  Math.abs(value - printed) <= 0.5 * 10 ** -decimals + 1e-9;
/** The L1 distance between two portfolios, the engine's distance_to_ttc. */
const l1 = (a: readonly number[], b: readonly number[]): number => a.reduce((s, v, j) => s + Math.abs(v - b[j]), 0);
/** The values of a list that must hold no null. */
const present = (xs: readonly (number | null)[], what: string): number[] =>
  xs.map((x, i) => {
    if (x === null) throw new Error(`${what}[${i}] is null`);
    return x;
  });
/** A value the types forbid, as an artifact's null or a stray string would arrive. */
const loose = (x: unknown): number => x as number;
const CORPORATE: IrbAssumptions = { assetClass: 'corporate', lgd: 0.45, maturity: 2.5, regime: 'basel3' };

describe('known values, without the artifact', () => {
  it("Schuermann and Hanson's Table 5: BB in 2002, 15 defaults of 531 obligors, in basis points", () => {
    // rho: N-dagger, Wald (lower, upper, length), Agresti-Coull (lower, upper, length), as printed
    const printed: [number, number, number[], number[]][] = [
      [0, 531, [141.56, 423.41, 281.84], [168.03, 464.71, 296.68]],
      [0.01, 84.3, [0.0, 636.2, 636.2], [38.25, 938.0, 899.75]],
      [0.02, 45.8, [0.0, 762.45, 762.45], [0.0, 1332.56, 1332.56]],
    ];
    for (const [rho, nDagger, wald, ac] of printed) {
      const w = pdWald(15, 531, { rho });
      const a = pdAgrestiCoull(15, 531, { rho });
      expect(printsAs(w.nEffective, nDagger, 1), `N-dagger at rho ${rho}: ${w.nEffective}`).toBe(true);
      [w.lower, w.upper, w.length].forEach((v, i) => {
        expect(printsAs(1e4 * v, wald[i], 2), `Wald at rho ${rho}: ${1e4 * v}`).toBe(true);
      });
      [a.lower, a.upper, a.length].forEach((v, i) => {
        expect(printsAs(1e4 * v, ac[i], 2), `Agresti-Coull at rho ${rho}: ${1e4 * v}`).toBe(true);
      });
    }
    // 15 is the one count that gives every printed bound (the count is not printed)
    for (const d of [14, 16]) expect(printsAs(1e4 * pdWald(d, 531).lower, 141.56, 2)).toBe(false);
  });

  it('(3.4): unequal trials, one trial each, and the bounds at the edges', () => {
    const pairs = Math.SQRT2 + Math.sqrt(3) + Math.sqrt(6);
    close(effectiveN(6, 0.1, [1, 2, 3]), 1 / (1 / 6 + (2 * pairs * 0.1) / 36), 'N-dagger with trials 1, 2, 3');
    close(effectiveN(531, 0.01), 531 / (1 + 530 * 0.01), 'N-dagger with one trial each');
    close(pdWald(3, 6, { rho: 0.1, trials: [1, 2, 3] }).nEffective, effectiveN(6, 0.1, [1, 2, 3]), 'Wald with trials');
    expect(pdWald(3, 100).lower).toBe(0); // 0.03 - 1.96 sqrt(0.03 x 0.97 / 100) < 0: bounded at 0, as printed
    const zero = pdWald(0, 100);
    expect([zero.lower, zero.upper]).toEqual([0, 0]); // the Wald interval collapses at no default
    expect(pdWald(10, 100).ruleOfThumb && !pdWald(3, 100).ruleOfThumb).toBe(true);
    const ac = pdAgrestiCoull(0, 100);
    expect(ac.lower === 0 && ac.upper > 0 && ac.estimate > 0).toBe(true);
    expect(pdJeffreys(0, 100).lower).toBe(0);
    expect(pdJeffreys(10, 10).upper).toBe(1);
    expect(() => pdWald(0, 0)).toThrow();
    expect(() => pdAgrestiCoull(5, 3)).toThrow();
    expect(() => pdJeffreys(1, 10, { level: 1 })).toThrow();
    expect(() => effectiveN(10, 1.5)).toThrow();
    // an omitted option takes its default
    expect(pdWald(15, 531, { rho: undefined, level: undefined }).nEffective).toBe(531);
  });

  it('nothing is coerced: null, a string or NaN where a number belongs is refused, as the engine refuses it', () => {
    for (const rho of [null, '0.01', NaN, -0.01, 1.01]) {
      const at = `rho ${String(rho)}`;
      expect(() => effectiveN(531, loose(rho)), `effectiveN, ${at}`).toThrow();
      expect(() => pdWald(15, 531, { rho: loose(rho) }), `Wald, ${at}`).toThrow();
      expect(() => pdAgrestiCoull(15, 531, { rho: loose(rho) }), `Agresti-Coull, ${at}`).toThrow();
    }
    for (const trials of [[1, null, 2], [1, '1', 1], [1, NaN, 2], [1, -1, 3], null]) {
      expect(() => effectiveN(3, 0.1, trials as unknown as number[]), `trials ${String(trials)}`).toThrow();
    }
    for (const level of [null, '0.95', NaN, 0, 1]) {
      const at = `level ${String(level)}`;
      expect(() => pdWald(15, 531, { level: loose(level) }), `Wald, ${at}`).toThrow();
      expect(() => pdAgrestiCoull(15, 531, { level: loose(level) }), `Agresti-Coull, ${at}`).toThrow();
      expect(() => pdJeffreys(15, 531, { level: loose(level) }), `Jeffreys, ${at}`).toThrow();
    }
    for (const bad of [null, '15', NaN]) {
      expect(() => pdWald(loose(bad), 531), `defaults ${String(bad)}`).toThrow();
      expect(() => pdJeffreys(15, loose(bad)), `n ${String(bad)}`).toThrow();
    }
    expect(() => effectiveN(0, 0.1)).toThrow(); // the engine returns NaN
    expect(() => betaQuantile(loose(null), 1, 1)).toThrow();
    expect(() => betaQuantile(0.5, loose('2'), 1)).toThrow();
  });

  it('the Jeffreys bounds invert the Beta distribution function', () => {
    for (const [d, n] of [[1, 50], [15, 531], [50, 2000], [49, 50], [3, 100000]]) {
      for (const level of [0.9, 0.95, 0.99]) {
        const j = pdJeffreys(d, n, { level });
        const [a, b] = [d + 0.5, n - d + 0.5];
        const at = `${d} of ${n} at ${level}`;
        expect(Math.abs(betaCdf(j.lower, a, b) - (1 - level) / 2), `lower, ${at}`).toBeLessThan(1e-12);
        expect(Math.abs(betaCdf(j.upper, a, b) - (0.5 + level / 2)), `upper, ${at}`).toBeLessThan(1e-12);
      }
    }
    // Beta(1/2, 1/2) is the arcsine law, F(x) = (2 / pi) asin(sqrt(x)): its quantile in closed form
    for (const q of [0.025, 0.3, 0.975]) {
      close(betaQuantile(q, 0.5, 0.5), Math.sin((Math.PI * q) / 2) ** 2, `arcsine quantile at ${q}`);
    }
  });

  it("the TTC portfolio of two grades in closed form, and Theorem 1's conditions", () => {
    const [a, b, p1, p2, o1] = [0.1, 0.2, 0.01, 0.05, 0.7];
    const t = [
      [1 - a - p1, a, p1],
      [b, 1 - b - p2, p2],
      [0, 0, 1],
    ];
    const r = ttcPortfolio(t, [o1, 1 - o1, 0]);
    const w1 = (b + p2 * o1) / (a + p1 * (1 - o1) + b + p2 * o1); // the balance of flows between the two grades
    expect(r.converged).toBe(true);
    closeAll(r.portfolio, [w1, 1 - w1, 0], 'two-grade TTC portfolio');
    close(r.defaultRate, w1 * p1 + (1 - w1) * p2, 'two-grade TTC default rate');
    const m = propagationMatrix(t, [o1, 1 - o1]);
    const moved = [0, 1, 2].map((j) => r.portfolio.reduce((s, w, i) => s + w * m[i][j], 0));
    closeAll(moved, r.portfolio, 'the fixed point of (10)');
    // from opposite starts the projection reaches it; the first year's rate is the start's PD; each date's distance
    // to the TTC portfolio is the L1 distance
    for (const start of [[1, 0], [0, 1]]) {
      const pr = project(t, start, [o1, 1 - o1], 300);
      expect(pr.portfolio.length).toBe(301);
      expect(pr.distanceToTtc[300]).toBeLessThan(1e-9);
      close(pr.defaultRate[0], start[0] * p1 + start[1] * p2, 'first-year default rate');
      close(pr.distanceToTtc[0], 2 * Math.abs(start[0] - w1), 'L1 distance of the start');
      pr.portfolio.forEach((w, y) => close(pr.distanceToTtc[y], l1(w, pr.ttc.portfolio), `L1 distance, year ${y}`));
    }
    // Engelmann's counterexample (the two grades swap every year), an origination into default, a default that is not
    // absorbing, a row off by 0.1
    expect(() => ttcPortfolio([[0, 1, 0], [1, 0, 0], [0, 0, 1]], [0.5, 0.5, 0])).toThrow();
    expect(isPrimitive([[0, 1], [1, 0]])).toBe(false);
    expect(isPrimitive([[0.5, 0.5], [1, 0]])).toBe(true);
    expect(() => ttcPortfolio(t, [0.5, 0.4, 0.1])).toThrow();
    expect(() => ttcPortfolio([[0.9, 0.1, 0], [0.1, 0.8, 0.1], [0.5, 0, 0.5]], [0.5, 0.5])).toThrow();
    expect(() => ttcPortfolio([[0.9, 0.2, 0], [0.1, 0.8, 0.1], [0, 0, 1]], [0.5, 0.5])).toThrow();
  });

  it('(9) from a start with a share already in default: written off and re-originated in the first period', () => {
    const [a, b, p1, p2, o1] = [0.1, 0.2, 0.01, 0.05, 0.7];
    const t = [
      [1 - a - p1, a, p1],
      [b, 1 - b - p2, p2],
      [0, 0, 1],
    ];
    const o = [o1, 1 - o1, 0];
    const [w, d] = [[0.3, 0.7], 0.02];
    const from = project(t, w, o, 10);
    // the first period of (9) in closed form: the migrated balance, and the defaulted part re-originated by O
    const dr = w[0] * p1 + w[1] * p2;
    const stay = [w[0] * (1 - a - p1) + w[1] * b, w[0] * a + w[1] * (1 - b - p2)];
    closeAll(from.portfolio[1], [stay[0] + dr * o1, stay[1] + dr * (1 - o1), 0], 'the first period of (9)');
    // with 2% already in default, the first year counts it and re-originates it: (1 - d) of the path plus d O
    const withDefault = project(t, [(1 - d) * w[0], (1 - d) * w[1], d], o, 10);
    close(withDefault.defaultRate[0], (1 - d) * dr + d, "the first year's rate with 2% in default");
    closeAll(withDefault.portfolio[1], from.portfolio[1].map((v, j) => (1 - d) * v + d * o[j]), 'its first period');
  });

  it("a printed matrix's rounding: the balance stays at one, as Engelmann's step 5 keeps it", () => {
    const t = [
      [0.9001, 0.0899, 0.0101],
      [0.0999, 0.8501, 0.0499],
      [0, 0, 1],
    ];
    const pr = project(t, [0.5, 0.5], [0.6, 0.4], 50);
    for (const w of pr.portfolio) close(w.reduce((s, v) => s + v, 0), 1, 'unit balance');
    close(pr.ttc.rowSumDeviation, 1e-4, 'row-sum deviation');
  });

  it("the engine's tolerance: a row, the origination and the start within 1e-3 of 1 kept, beyond it refused", () => {
    const t = [
      [0.9, 0.09, 0.01],
      [0.1, 0.85, 0.05],
      [0, 0, 1],
    ];
    const off = (dev: number): number[][] => [[0.9 + dev, 0.09, 0.01], t[1], t[2]];
    expect(() => project(off(0.9e-3), [0.5, 0.5], [0.6, 0.4], 5)).not.toThrow();
    expect(() => project(off(-0.9e-3), [0.5, 0.5], [0.6, 0.4], 5)).not.toThrow();
    for (const dev of [1.1e-3, -1.1e-3]) {
      expect(() => project(off(dev), [0.5, 0.5], [0.6, 0.4], 5), `a row off by ${dev}`).toThrow();
      expect(() => ttcPortfolio(off(dev), [0.6, 0.4]), `a row off by ${dev}, TTC`).toThrow();
      expect(() => propagationMatrix(off(dev), [0.6, 0.4]), `a row off by ${dev}, M`).toThrow();
    }
    // the origination and the start within the tolerance are normalised: the projection is the exact one's
    const exact = project(t, [0.5, 0.5], [0.6, 0.4], 30);
    const s = 1.0009;
    for (const [what, pr] of [
      ['origination', project(t, [0.5, 0.5], [0.6 * s, 0.4 * s], 30)],
      ['start', project(t, [0.5 * s, 0.5 * s], [0.6, 0.4], 30)],
    ] as const) {
      closeAll(pr.defaultRate, exact.defaultRate, `default rate, the ${what} summing to ${s}`);
      closeAll(pr.portfolio[30], exact.portfolio[30], `portfolio, the ${what} summing to ${s}`);
      closeAll(pr.ttc.portfolio, exact.ttc.portfolio, `TTC portfolio, the ${what} summing to ${s}`);
    }
    closeAll(ttcPortfolio(t, [0.6 * s, 0.4 * s]).portfolio, exact.ttc.portfolio, 'TTC portfolio alone');
    expect(() => project(t, [0.5, 0.5], [0.6 * 1.0011, 0.4 * 1.0011], 5)).toThrow();
    expect(() => project(t, [0.5 * 1.0011, 0.5 * 1.0011], [0.6, 0.4], 5)).toThrow();
  });

  it('the capital of a portfolio by grade: a PD of 0, a grade without a PD, and the refusals', () => {
    const { assetClass, lgd, maturity, regime } = CORPORATE;
    const rw = (pd: number): number => irbCapital(assetClass, pd, lgd, { maturity, regime }).riskWeight;
    // a PD of 0, a grade with no default in any cohort, takes the floor's risk weight (CRE32.4, 0.05%)
    const zero = portfolioRiskWeight([0, 0.01], [1, 3], CORPORATE);
    closeAll(present(zero.riskWeights, 'risk weights'), [rw(0.0005), rw(0.01)], 'a PD of 0 at the floor');
    close(zero.average ?? NaN, (rw(0.0005) + 3 * rw(0.01)) / 4, 'the average with a PD of 0');
    // a grade without a PD (null): no average while it holds exposure, as Moody's generators give no PD; left out of
    // the average when it holds none
    const none = portfolioRiskWeight(new Array<null>(7).fill(null), [1, 2, 3, 4, 5, 6, 7], CORPORATE);
    expect(none.average).toBeNull();
    expect(none.riskWeights.every((r) => r === null)).toBe(true);
    expect(portfolioRiskWeight([null, 0.01], [1, 1], CORPORATE).average).toBeNull();
    const without = portfolioRiskWeight([null, 0.01], [0, 1], CORPORATE);
    expect(without.riskWeights[0]).toBeNull();
    close(without.average ?? NaN, rw(0.01), 'a grade without a PD or exposure, left out');
    // refused: a PD that is not a number in [0, 1) (1 is a defaulted exposure), exposures that are not non-negative
    // numbers or are all zero, an LGD outside [0, 1], a PD of 0 where no floor applies (sovereigns are exempt)
    for (const pd of [undefined, '0.01', NaN, Infinity, -0.001, 1]) {
      expect(() => portfolioRiskWeight([loose(pd)], [1], CORPORATE), `PD ${String(pd)}`).toThrow();
    }
    for (const e of [[null], ['1'], [-1], [NaN], [0]]) {
      expect(() => portfolioRiskWeight([0.01], e as unknown as number[], CORPORATE), `exposure ${String(e)}`).toThrow();
    }
    expect(() => portfolioRiskWeight([0.01], [1, 1], CORPORATE)).toThrow();
    expect(() => portfolioRiskWeight([0.01], [1], { ...CORPORATE, lgd: 1.2 })).toThrow();
    expect(() => portfolioRiskWeight([0.01], [1], { ...CORPORATE, lgd: loose(null) })).toThrow();
    expect(() => portfolioRiskWeight([0], [1], { ...CORPORATE, assetClass: 'sovereign' })).toThrow();
  });
});

describe('CT-410: the projections equal riskvalidation (transitions.ttc) on the parity points', () => {
  it('every agency matrix, three starting portfolios, 20 years, and the TTC portfolio', () => {
    const rows = parity().projection;
    expect(rows.length).toBeGreaterThanOrEqual(3);
    for (const pt of rows) {
      const what = `${pt.agency} from ${JSON.stringify(pt.w0)}`;
      // some grade reaches default: the pipeline refuses a matrix in which none does (zeros held to zeros)
      expect(pt.matrix.slice(0, -1).some((row) => row[row.length - 1] > 0), `${what}: a default column`).toBe(true);
      expect(pt.default_rate.length, what).toBe(pt.years);
      const live = project(pt.matrix, pt.w0, pt.origination, pt.years);
      closeAll(live.defaultRate, pt.default_rate, `${what}: default rate by year`);
      closeAll(live.portfolio[pt.years], pt.portfolio_last, `${what}: portfolio after ${pt.years} years`);
      expect(live.ttc.converged, what).toBe(true);
      closeAll(live.ttc.portfolio, pt.ttc, `${what}: TTC portfolio`);
      close(live.ttc.defaultRate, pt.ttc_default_rate, `${what}: TTC default rate`);
      // each date's distance to the TTC portfolio is the L1 distance, as the engine's distance_to_ttc
      live.portfolio.forEach((w, y) => close(live.distanceToTtc[y], l1(w, live.ttc.portfolio), `${what}: L1, ${y}`));
      const fixed = ttcPortfolio(pt.matrix, pt.origination);
      closeAll(fixed.portfolio, pt.ttc, `${pt.agency}: TTC portfolio, alone`);
      close(fixed.defaultRate, pt.ttc_default_rate, `${pt.agency}: TTC default rate, alone`);
      // the origination printed to rounding (its shares summing to 1.0005, within the engine's 1e-3): the engine
      // normalises it, so the projection and the TTC portfolio are the parity's
      const printed = pt.origination.map((x) => x * 1.0005);
      const rounded = project(pt.matrix, pt.w0, printed, pt.years);
      closeAll(rounded.defaultRate, pt.default_rate, `${what}: default rate, origination summing to 1.0005`);
      closeAll(rounded.portfolio[pt.years], pt.portfolio_last, `${what}: portfolio, origination summing to 1.0005`);
      const alone = ttcPortfolio(pt.matrix, printed).portfolio;
      closeAll(alone, pt.ttc, `${what}: TTC portfolio, origination summing to 1.0005`);
      // 2% of the start already in default: the first year counts it, and (9) re-originates it by O
      const [d, last] = [0.02, pt.w0.length - 1];
      expect(pt.w0[last], `${what}: a performing start`).toBe(0);
      const withDefault = project(pt.matrix, pt.w0.map((v, j) => (j === last ? d : (1 - d) * v)), pt.origination, 1);
      close(withDefault.defaultRate[0], (1 - d) * pt.default_rate[0] + d, `${what}: first year with 2% in default`);
      const reoriginated = live.portfolio[1].map((v, j) => (1 - d) * v + d * pt.origination[j]);
      closeAll(withDefault.portfolio[1], reoriginated, `${what}: first period with 2% in default`);
    }
    // three starts per agency: all in the first grade, the origination mix, uniform over the grades
    const agencies = new Set(rows.map((r) => r.agency));
    expect(rows.length).toBe(3 * agencies.size);
  });
});

describe('CT-411: the intervals and the IRB risk weight equal riskvalidation on the parity points', () => {
  it('Wald and Agresti-Coull at each correlation, the effective N, and Jeffreys', () => {
    const rows = parity().intervals;
    expect(rows.some((r) => r.defaults === 15 && r.n === 531 && r.rho === 0.01 && r.level === 0.95)).toBe(true);
    // the web's three levels, and CEREP's pooled sizes (tens of thousands of ratings, a thousand defaults and more)
    for (const level of [0.9, 0.95, 0.99]) expect(rows.some((r) => r.level === level), `level ${level}`).toBe(true);
    expect(rows.some((r) => r.n >= 40000 && r.level === 0.99)).toBe(true);
    expect(rows.some((r) => r.defaults >= 1000)).toBe(true);
    for (const pt of rows) {
      const what = `${pt.defaults} of ${pt.n}, rho ${pt.rho}, level ${pt.level}`;
      const w = pdWald(pt.defaults, pt.n, { level: pt.level, rho: pt.rho });
      closeAll([w.lower, w.upper], pt.wald, `${what}: Wald`);
      close(w.nEffective, pt.n_effective, `${what}: N-dagger`);
      if (pt.rho > 0) close(effectiveN(pt.n, pt.rho), pt.n_effective, `${what}: effectiveN`);
      const a = pdAgrestiCoull(pt.defaults, pt.n, { level: pt.level, rho: pt.rho });
      closeAll([a.lower, a.upper], pt.agresti_coull, `${what}: Agresti-Coull`);
      const j = pdJeffreys(pt.defaults, pt.n, { level: pt.level });
      closeAll([j.lower, j.upper], pt.jeffreys, `${what}: Jeffreys`);
    }
  });

  it("the IRB risk weight of each PD under the case's convention, alone and in a portfolio by grade", () => {
    const rows = parity().capital;
    expect(rows.length).toBeGreaterThanOrEqual(5);
    for (const pt of rows) {
      const live = irbCapital(pt.asset_class, pt.pd, pt.lgd, { maturity: pt.maturity, regime: pt.regime });
      close(live.riskWeight, pt.risk_weight, `PD ${pt.pd}`);
    }
    // a PD of 0 (a grade with no default in any cohort) takes the floor's risk weight, as a PD below the floor does
    const at = (pd: number): CapitalPoint => {
      const row = rows.find((r) => r.pd === pd);
      if (!row) throw new Error(`no capital row at PD ${pd}`);
      return row;
    };
    close(at(0).risk_weight, at(0.0005).risk_weight, 'PD 0 at the floor');
    close(at(0.0003).risk_weight, at(0.0005).risk_weight, 'PD 0.0003 at the floor');
    // the same assumptions on every row; a portfolio holding the PDs as grades averages their risk weights
    const { lgd, maturity, regime, asset_class: assetClass } = rows[0];
    const same = (r: CapitalPoint): boolean =>
      r.lgd === lgd && r.maturity === maturity && r.regime === regime && r.asset_class === assetClass;
    expect(rows.every(same)).toBe(true);
    const irb: IrbAssumptions = { assetClass, lgd, maturity, regime };
    const exposure = rows.map((_, i) => i + 1);
    const port = portfolioRiskWeight(rows.map((r) => r.pd), exposure, irb);
    closeAll(present(port.riskWeights, 'risk weight by grade'), rows.map((r) => r.risk_weight), 'risk weight by grade');
    const total = exposure.reduce((s, e) => s + e, 0);
    const average = rows.reduce((s, r, i) => s + r.risk_weight * exposure[i], 0) / total;
    close(port.average ?? NaN, average, 'exposure-weighted risk weight');
    // a grade without a PD: no average while it holds exposure, left out once it holds none
    const pds = [null, ...rows.map((r) => r.pd)];
    expect(portfolioRiskWeight(pds, [1, ...exposure], irb).average).toBeNull();
    close(portfolioRiskWeight(pds, [0, ...exposure], irb).average ?? NaN, average, 'a grade without a PD or exposure');
  });
});
