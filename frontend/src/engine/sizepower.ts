// The live lane of C22 (CT-308): the exact size and power of the three count tests, recomputed in the browser for a
// reader's portfolio. Each test sees the data only through one default count D of n obligors, and its p-value falls as
// D grows, so it rejects at level alpha exactly when D >= k*, the smallest count whose p-value is below alpha under
// the PD applied; the rejection probability is the tail of the count's true distribution at k*. Ports of
// riskvalidation 0.3.0 (harness.exact.rejection_probability, validation.calibration.default_count_sf, pd_binomial,
// pd_binomial_vasicek, pd_jeffreys), held to the engine by engine/sizepower.test.ts on the parity points the pipeline
// exports (1e-9 relative, 1e-12 absolute for tails below that).
import { ncdf, nquantile, type Quadrature } from './credit';

export type CountTest = 'pd.binomial' | 'pd.binomial_vasicek' | 'pd.jeffreys';

// ---------------------------------------------------------------------------------------------------------------------
// log gamma and the regularised incomplete beta (the Jeffreys posterior)

const LANCZOS = [
  0.99999999999980993, 676.5203681218851, -1259.1392167224028, 771.32342877765313, -176.61502916214059,
  12.507343278686905, -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7,
];

/** ln Gamma(x) for x > 0 (Lanczos, g = 7, nine terms: about 1e-15 relative). */
export function lgamma(x: number): number {
  if (x < 0.5) return Math.log(Math.PI / Math.sin(Math.PI * x)) - lgamma(1 - x);
  const z = x - 1;
  let a = LANCZOS[0];
  const t = z + 7.5;
  for (let i = 1; i < 9; i++) a += LANCZOS[i] / (z + i);
  return 0.5 * Math.log(2 * Math.PI) + (z + 0.5) * Math.log(t) - t + Math.log(a);
}

/** The continued fraction of the incomplete beta (modified Lentz), converging for x < (a + 1) / (a + b + 2). */
function betacf(x: number, a: number, b: number): number {
  const tiny = 1e-300;
  let c = 1;
  let d = 1 - ((a + b) * x) / (a + 1);
  d = Math.abs(d) < tiny ? tiny : d;
  d = 1 / d;
  let h = d;
  for (let m = 1; m <= 10000; m++) {
    const m2 = 2 * m;
    let aa = (m * (b - m) * x) / ((a + m2 - 1) * (a + m2));
    d = 1 + aa * d;
    d = Math.abs(d) < tiny ? tiny : d;
    c = 1 + aa / c;
    c = Math.abs(c) < tiny ? tiny : c;
    d = 1 / d;
    h *= d * c;
    aa = (-(a + m) * (a + b + m) * x) / ((a + m2) * (a + m2 + 1));
    d = 1 + aa * d;
    d = Math.abs(d) < tiny ? tiny : d;
    c = 1 + aa / c;
    c = Math.abs(c) < tiny ? tiny : c;
    d = 1 / d;
    const del = d * c;
    h *= del;
    if (Math.abs(del - 1) < 1e-16) break;
  }
  return h;
}

/** The regularised incomplete beta I_x(a, b), the Beta(a, b) distribution function at x. */
export function betaCdf(x: number, a: number, b: number): number {
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  const lbt = lgamma(a + b) - lgamma(a) - lgamma(b) + a * Math.log(x) + b * Math.log1p(-x);
  if (x < (a + 1) / (a + b + 2)) return (Math.exp(lbt) * betacf(x, a, b)) / a;
  return 1 - (Math.exp(lbt) * betacf(1 - x, b, a)) / b;
}

// ---------------------------------------------------------------------------------------------------------------------
// the count's distribution

/** P(Bin(n, p) >= k), summed in logs from whichever side is shorter. */
export function binomTail(k: number, n: number, p: number): number {
  if (k <= 0) return 1;
  if (k > n) return 0;
  if (p <= 0) return 0;
  if (p >= 1) return 1;
  const lp = Math.log(p);
  const lq = Math.log1p(-p);
  const lodds = lp - lq;
  const logPmf = (i: number) => lgamma(n + 1) - lgamma(i + 1) - lgamma(n - i + 1) + i * lp + (n - i) * lq;
  if (k - 1 < n * p) {
    // 1 - P(D <= k - 1). k - 1 lies at or below the mode, so the terms fall from pmf(k - 1) downward, by the ratio
    // pmf(i - 1) / pmf(i) = i / (n - i + 1) * (1 - p) / p: summed relative to pmf(k - 1), stopping once a term adds
    // nothing; a pmf(k - 1) below e^-800 leaves the tail at one in doubles
    const l1 = logPmf(k - 1);
    if (l1 < -800) return 1;
    let lr = 0;
    let s = 1;
    for (let i = k - 1; i > 0; i--) {
      lr += Math.log(i / (n - i + 1)) - lodds;
      const term = Math.exp(lr);
      s += term;
      if (term < 1e-17 * s) break;
    }
    return Math.max(0, 1 - Math.exp(l1) * s);
  }
  // k - 1 >= np puts k at or past the mode, so the terms only fall from pmf(k) on: sum them relative to pmf(k), which
  // cannot underflow, and stop once a term adds nothing. A pmf(k) below e^-800 leaves a tail under (n + 1) e^-800,
  // zero in doubles (summing absolute terms there compared 0 with 0 and ran all n terms: seconds per tail at 10,000).
  const l0 = logPmf(k);
  if (l0 < -800) return 0;
  let lr = 0;
  let s = 1;
  for (let i = k; i < n; i++) {
    lr += Math.log((n - i) / (i + 1)) + lodds;
    const term = Math.exp(lr);
    s += term;
    if (term < 1e-17 * s) break;
  }
  return Math.min(1, Math.exp(l0) * s);
}

/** P(D >= k) for n obligors with PD `pd` and asset correlation `rho`: the binomial tail, or its one-factor mixture by
 * the engine's 256-node Gauss-Hermite rule (riskvalidation default_count_sf). */
export function countTail(k: number, n: number, pd: number, rho: number, quad: Quadrature): number {
  if (k <= 0) return 1;
  if (rho === 0) return binomTail(k, n, pd);
  const g = nquantile(pd);
  const sr = Math.sqrt(rho);
  const s1r = Math.sqrt(1 - rho);
  let s = 0;
  for (let i = 0; i < quad.nodes.length; i++) s += quad.weights[i] * binomTail(k, n, ncdf((g - sr * quad.nodes[i]) / s1r));
  return Math.min(1, Math.max(0, s));
}

/** The test's p-value at a count k under the PD applied. */
export function countPValue(test: CountTest, n: number, k: number, pd: number, rhoAssumed: number, quad: Quadrature): number {
  if (test === 'pd.jeffreys') return betaCdf(pd, k + 0.5, n - k + 0.5);
  if (test === 'pd.binomial') return binomTail(k, n, pd);
  return countTail(k, n, pd, rhoAssumed, quad);
}

/** The smallest count whose p-value is below alpha, or null when no count rejects (the engine's critical_count). */
export function criticalCount(test: CountTest, n: number, pd: number, alpha: number, rhoAssumed: number, quad: Quadrature): number | null {
  const p = (k: number) => countPValue(test, n, k, pd, rhoAssumed, quad);
  if (p(n) >= alpha) return null;
  if (p(0) < alpha) return 0;
  let lo = 0;
  let hi = n;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (p(mid) < alpha) hi = mid;
    else lo = mid;
  }
  return hi;
}

export interface Rejection {
  probability: number;
  criticalCount: number | null;
}

/** The exact probability that the test rejects at alpha when the true PD is `pdTrue` and the true asset correlation
 * `rhoTrue` (the size when pdTrue equals the PD applied). */
export function rejectionProbability(
  test: CountTest,
  n: number,
  pdApplied: number,
  alpha: number,
  pdTrue: number,
  rhoTrue: number,
  rhoAssumed: number,
  quad: Quadrature,
): Rejection {
  const k = criticalCount(test, n, pdApplied, alpha, rhoAssumed, quad);
  return { criticalCount: k, probability: k === null ? 0 : countTail(k, n, pdTrue, rhoTrue, quad) };
}
