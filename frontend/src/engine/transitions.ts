// The live lane of C04 (CT-410, CT-411): a reader's portfolio by grade projected under an agency's pooled one-year
// matrix with an origination mix, the through-the-cycle portfolio it drifts to, the intervals of a PD by grade at a
// reader's default correlation, and the IRB capital of a portfolio by grade under each PD definition, recomputed in
// the browser. Ports of riskvalidation 0.4.0 (transitions.ttc.project, ttc_portfolio, propagation_matrix,
// is_primitive; transitions.intervals.pd_wald, pd_agresti_coull, effective_n, pd_jeffreys), held to the engine by
// engine/transitions.test.ts on the parity points the pipeline exports in C04's models artifact (1e-9 relative, 1e-12
// absolute below that). Sources: Engelmann (2024), Spurious default probability projections in credit risk stress
// testing models, arXiv 2401.08892v1, the propagation (9) and Theorem 1's TTC portfolio (10); Schuermann and Hanson
// (2004), Estimating probabilities of default, FRBNY Staff Report 190, the Wald interval (2.2), the Agresti-Coull
// interval (3.2) to (3.3) and the effective number of observations (3.4) after Miao and Gastwirth (2004); the
// equal-tailed Jeffreys interval (Brown, Cai and DasGupta 2001, doi:10.1214/ss/1009213286, as defined in Zhou, Li and
// Yang 2008, doi:10.1098/rsta.2008.0037, Appendix C). The IRB risk weight is credit.ts irbCapital (the port of
// regulatory.irb C05 holds to the engine), never re-implemented here. States are the grades best first, default last.
// Every input is checked as the engine checks it, and none is coerced: null, a string or NaN where a number belongs is
// refused, never read as 0 (a PD by grade may be null, a grade without a PD, as the case's impact reads it).
import { irbCapital, nquantile, type AssetClass, type Regime } from './credit';
import { betaCdf } from './sizepower';

/** How far a row may sum from 1 (a printed matrix's rounding), the engine's default atol. */
export const ATOL = 1e-3;
/** The TTC iteration stops when one period moves the portfolio by less than this in L1 (the engine's tol). */
export const TTC_TOL = 1e-14;
const TTC_MAX_ITER = 1_000_000;

const sum = (a: readonly number[]): number => a.reduce((s, v) => s + v, 0);

/** w' A for a row vector w. */
function vecMat(w: number[], a: number[][]): number[] {
  const out = new Array<number>(a[0].length).fill(0);
  for (let i = 0; i < w.length; i++) {
    const wi = w[i];
    if (wi === 0) continue;
    const row = a[i];
    for (let j = 0; j < out.length; j++) out[j] += wi * row[j];
  }
  return out;
}

/** w' T V_w, the portfolio's default rate over the next period (the last column of T). */
function defaultRate(w: number[], t: number[][]): number {
  const d = t.length - 1;
  let s = 0;
  for (let i = 0; i < w.length; i++) s += w[i] * t[i][d];
  return s;
}

// ---------------------------------------------------------------------------------------------------------------------
// the inputs, checked as the engine checks them (riskvalidation.transitions.ttc._transition, _origination)

/** A transition matrix, default last and absorbing, its rows summing to 1 within `atol`, kept as given. Returns the
 * largest row-sum deviation. */
function checkTransition(t: number[][], atol: number): number {
  const n = t.length;
  if (n < 3 || t.some((row) => row.length !== n)) {
    throw new Error('the transition matrix must be square with at least two grades and default');
  }
  let dev = 0;
  for (const row of t) {
    if (row.some((v) => !Number.isFinite(v) || v < 0)) {
      throw new Error('the transition matrix must be finite and non-negative');
    }
    dev = Math.max(dev, Math.abs(sum(row) - 1));
  }
  if (dev > atol) throw new Error(`a row sums to 1 +- ${dev.toPrecision(2)}, beyond atol ${atol}`);
  // numpy.allclose(T[-1], e_n, atol): |a - b| <= atol + 1e-5 |b|
  for (let j = 0; j < n; j++) {
    const e = j === n - 1 ? 1 : 0;
    if (!(Math.abs(t[n - 1][j] - e) <= atol + 1e-5 * e)) throw new Error('default (the last state) must be absorbing');
  }
  return dev;
}

/** Shares over the n - 1 grades (a zero in default appended) or over all n states, as given. */
function states(v: number[], n: number): number[] {
  return v.length === n - 1 ? [...v, 0] : [...v];
}

/** The origination vector O: non-negative, none into default (Theorem 1's second condition), summing to 1 within
 * `atol`, normalised to sum 1. */
function checkOrigination(o: number[], n: number, atol: number): number[] {
  const v = states(o, n);
  if (v.length !== n || v.some((x) => !Number.isFinite(x) || x < 0)) {
    throw new Error(`the origination vector must give ${n - 1} or ${n} non-negative shares`);
  }
  if (v[n - 1] > 0) throw new Error("origination into default breaks Theorem 1's second condition (o_n = 0)");
  const s = sum(v);
  if (Math.abs(s - 1) > atol) throw new Error(`the origination shares sum to ${s.toPrecision(6)}, not 1`);
  return v.map((x) => x / s);
}

/** Wielandt: a non-negative k x k matrix is primitive iff its ((k - 1)^2 + 1)-th power is strictly positive. */
export function isPrimitive(a: number[][]): boolean {
  const k = a.length;
  const mul = (x: boolean[][], y: boolean[][]): boolean[][] =>
    x.map((row) => Array.from({ length: k }, (_, j) => row.some((xil, l) => xil && y[l][j])));
  let base = a.map((row) => row.map((v) => v > 0));
  let result = Array.from({ length: k }, (_, i) => Array.from({ length: k }, (_, j) => i === j));
  let power = (k - 1) ** 2 + 1;
  while (power) {
    if (power & 1) result = mul(result, base);
    base = mul(base, base);
    power >>= 1;
  }
  return result.every((row) => row.every(Boolean));
}

/** M = T I_w + (T V_w) O': the defaulted balance of each row re-originated by O, so (9) with a constant T is
 * W_t' = W_{t-1}' M. */
export function propagationMatrix(t: number[][], origination: number[], atol = ATOL): number[][] {
  checkTransition(t, atol);
  const n = t.length;
  const o = checkOrigination(origination, n, atol);
  return t.map((row) => row.map((v, j) => (j === n - 1 ? 0 : v) + row[n - 1] * o[j]));
}

// ---------------------------------------------------------------------------------------------------------------------
// Engelmann (2024): the TTC portfolio (Theorem 1) and the projection (9)

export interface TtcPortfolio {
  /** W_ttc over the n states (0 in default). */
  portfolio: number[];
  /** W_ttc' T V_w, the TTC default rate. */
  defaultRate: number;
  iterations: number;
  converged: boolean;
  /** The largest |row sum - 1| of T (a printed matrix's rounding). */
  rowSumDeviation: number;
}

/** Engelmann's W_ttc: (9) iterated with the unstressed T from the uniform performing portfolio, at unit balance, until
 * one period moves it by less than 1e-14 in L1. Refuses a performing block that is not primitive or an origination
 * into default (Theorem 1's conditions). */
export function ttcPortfolio(t: number[][], origination: number[]): TtcPortfolio {
  const rowSumDeviation = checkTransition(t, ATOL);
  const n = t.length;
  if (!isPrimitive(t.slice(0, n - 1).map((row) => row.slice(0, n - 1)))) {
    throw new Error("the performing block is not primitive (Theorem 1's first condition): no unique TTC portfolio");
  }
  const m = propagationMatrix(t, origination, ATOL);
  let w = [...new Array<number>(n - 1).fill(1 / (n - 1)), 0];
  let converged = false;
  let iterations = 0;
  while (!converged && iterations < TTC_MAX_ITER) {
    iterations++;
    const nxt = vecMat(w, m);
    const s = sum(nxt);
    let change = 0;
    for (let j = 0; j < n; j++) {
      nxt[j] /= s;
      change += Math.abs(nxt[j] - w[j]);
    }
    converged = change < TTC_TOL;
    w = nxt;
  }
  return { portfolio: w, defaultRate: defaultRate(w, t), iterations, converged, rowSumDeviation };
}

export interface Projection {
  /** The portfolio at each date, years + 1 rows over the n states, each at unit balance. */
  portfolio: number[][];
  /** defaultRate[t] = W_t' T V_w, the default rate of year t + 1 (years values). */
  defaultRate: number[];
  /** The TTC portfolio the projection drifts to. */
  ttc: TtcPortfolio;
  /** Each date's L1 distance to the TTC portfolio. */
  distanceToTtc: number[];
}

/** Propagate a starting portfolio `w0` (n - 1 grades or n states, summing to 1) by Engelmann's (9) under one unstressed
 * matrix for `years`: each period the portfolio migrates by T, its defaulted part is written off and re-originated
 * by O, and the balance is rescaled to one (his step 5, which a printed matrix's rows need). */
export function project(t: number[][], w0: number[], origination: number[], years: number): Projection {
  if (!Number.isInteger(years) || years < 1) throw new Error('one matrix needs years >= 1');
  checkTransition(t, ATOL);
  const n = t.length;
  const start = states(w0, n);
  if (start.length !== n || start.some((x) => !Number.isFinite(x) || x < 0) || Math.abs(sum(start) - 1) > ATOL) {
    throw new Error(`the portfolio must give ${n - 1} or ${n} non-negative shares summing to 1`);
  }
  const o = checkOrigination(origination, n, ATOL);
  const s0 = sum(start);
  const portfolio = [start.map((x) => x / s0)];
  const rates: number[] = [];
  for (let y = 0; y < years; y++) {
    const w = portfolio[portfolio.length - 1];
    rates.push(defaultRate(w, t));
    const moved = vecMat(w, t);
    const nxt = moved.map((v, j) => (j === n - 1 ? 0 : v) + moved[n - 1] * o[j]);
    const s = sum(nxt);
    portfolio.push(nxt.map((v) => v / s));
  }
  const ttc = ttcPortfolio(t, o);
  const distanceToTtc = portfolio.map((p) => p.reduce((acc, v, j) => acc + Math.abs(v - ttc.portfolio[j]), 0));
  return { portfolio, defaultRate: rates, ttc, distanceToTtc };
}

// ---------------------------------------------------------------------------------------------------------------------
// Schuermann and Hanson (2004): intervals for a PD by grade, D defaults in N firm-years (or obligors)

export type IntervalMethod = 'wald' | 'agresti_coull' | 'jeffreys';

export interface PdInterval {
  method: IntervalMethod;
  /** D / N (Wald, Jeffreys) or the Agresti-Coull centre. */
  estimate: number;
  lower: number;
  upper: number;
  length: number;
  n: number;
  /** N, or N-dagger (3.4) at a default correlation. */
  nEffective: number;
  level: number;
}

/** The Wald interval with Schuermann and Hanson's rule of thumb (PD N >= 10). */
export type WaldInterval = PdInterval & { ruleOfThumb: boolean };
/** The Agresti-Coull interval (estimate: its centre) with the observed rate D / N. */
export type AgrestiCoullInterval = PdInterval & { observedRate: number };

export interface IntervalOptions {
  /** The confidence level, 0.95 when omitted. */
  level?: number;
  /** One default correlation between every pair of obligors (3.4), 0 when omitted. */
  rho?: number;
  /** Each obligor's trials (years) in the grade, summing to n; one each when omitted. */
  trials?: readonly number[];
}

function checkCounts(d: number, n: number): void {
  if (!Number.isFinite(d) || !Number.isFinite(n)) throw new Error('defaults and n must be finite');
  if (n <= 0) throw new Error('an empty grade (n = 0) has no PD to bound');
  if (d < 0 || d > n) throw new Error('defaults must lie between 0 and n');
}

/** kappa, the 100(1 - alpha/2)th percentile of the standard normal. */
function kappa(level: number): number {
  if (!(Number.isFinite(level) && level > 0 && level < 1)) throw new Error('level must lie in (0, 1)');
  return nquantile(0.5 + level / 2);
}

/** An option's value, its default only when it is omitted: an explicit null is passed on, to be refused. */
const given = (value: number | undefined, fallback: number): number => (value === undefined ? fallback : value);

const clip01 = (x: number): number => Math.min(Math.max(x, 0), 1);

function interval(
  method: IntervalMethod,
  estimate: number,
  lo: number,
  hi: number,
  n: number,
  nEffective: number,
  level: number,
): PdInterval {
  const lower = clip01(lo);
  const upper = clip01(hi);
  return { method, estimate, lower, upper, length: upper - lower, n, nEffective, level };
}

/** (3.4): N-dagger = [1/N + (2/N^2) sum_{i<j} sqrt(N_i N_j) rho]^-1 with one correlation rho between every pair;
 * `trials` gives each obligor's N_i (n is then their sum), and without it N-dagger = N / (1 + (N - 1) rho). Refuses,
 * as the engine does, a rho outside [0, 1] and trials that are not non-negative numbers summing to n (numpy's
 * isclose); and an n that is not positive, where the engine returns NaN (n = 0) or a negative count. */
export function effectiveN(n: number, rho = 0, trials?: readonly number[]): number {
  if (!(Number.isFinite(n) && n > 0)) throw new Error('n must be a positive number of obligors (or trials)');
  if (!(Number.isFinite(rho) && rho >= 0 && rho <= 1)) throw new Error('rho must lie in [0, 1]');
  let pairs: number;
  if (trials === undefined) {
    pairs = (n * (n - 1)) / 2;
  } else {
    const counts = Array.isArray(trials) && trials.every((x) => Number.isFinite(x) && x >= 0);
    if (!counts || !(Math.abs(sum(trials) - n) <= 1e-8 + 1e-5 * Math.abs(n))) {
      throw new Error("trials must be one obligor's count each, summing to n");
    }
    const roots = sum(trials.map(Math.sqrt));
    pairs = (roots * roots - sum(trials)) / 2;
  }
  return 1 / (1 / n + (2 * pairs * rho) / (n * n));
}

function nEff(n: number, rho: number, trials: readonly number[] | undefined): number {
  if (rho === 0 && trials === undefined) return n;
  return effectiveN(n, rho, trials);
}

/** The Wald interval (2.2), N replaced by N-dagger (3.4) at a correlation; bounded to [0, 1]. Their rule of thumb,
 * PD N >= 10, says when it may be trusted at all. */
export function pdWald(defaults: number, n: number, opts: IntervalOptions = {}): WaldInterval {
  checkCounts(defaults, n);
  const level = given(opts.level, 0.95);
  const z = kappa(level);
  const ne = nEff(n, given(opts.rho, 0), opts.trials);
  const p = defaults / n;
  const half = z * Math.sqrt((p * (1 - p)) / ne);
  return { ...interval('wald', p, p - half, p + half, n, ne, level), ruleOfThumb: p * n >= 10 };
}

/** The Agresti-Coull interval (3.2) to (3.3) with N-dagger (3.4): centre (PD N-dagger + kappa^2/2) / (N-dagger +
 * kappa^2); bounded to [0, 1]. */
export function pdAgrestiCoull(defaults: number, n: number, opts: IntervalOptions = {}): AgrestiCoullInterval {
  checkCounts(defaults, n);
  const level = given(opts.level, 0.95);
  const z = kappa(level);
  const ne = nEff(n, given(opts.rho, 0), opts.trials);
  const pHat = defaults / n;
  const nTilde = ne + z ** 2;
  const centre = (pHat * ne + z ** 2 / 2) / nTilde;
  const half = z * Math.sqrt((centre * (1 - centre)) / nTilde);
  return { ...interval('agresti_coull', centre, centre - half, centre + half, n, ne, level), observedRate: pHat };
}

/** The q-quantile of Beta(a, b): bisection on betaCdf until no double lies between the bracket's ends, so the quantile
 * carries betaCdf's own precision, which falls as N grows (its log-gamma terms cancel). Measured against scipy's
 * beta.ppf (the engine's, itself within 7e-16 of a 50-digit quantile at every point measured), as Jeffreys bounds:
 * 6e-13 relative at most on the parity's grid (N up to 2,000), 3e-11 at CEREP's pooled sizes (N 2,000 to 47,000; the
 * worst at one default in 20,000), 1.1e-10 at one default in 45,000, 6e-11 in 150,000, 3.4e-10 at N = 1,000,000. */
export function betaQuantile(q: number, a: number, b: number): number {
  const positive = (x: number): boolean => Number.isFinite(x) && x > 0;
  if (!(Number.isFinite(q) && q >= 0 && q <= 1) || !positive(a) || !positive(b)) {
    throw new Error('betaQuantile needs q in [0, 1] and finite a, b > 0');
  }
  if (q === 0) return 0;
  if (q === 1) return 1;
  let lo = 0;
  let hi = 1;
  for (let i = 0; i < 1100; i++) {
    const mid = 0.5 * (lo + hi);
    if (mid <= lo || mid >= hi) break;
    if (betaCdf(mid, a, b) < q) lo = mid;
    else hi = mid;
  }
  return 0.5 * (lo + hi);
}

/** The equal-tailed Jeffreys interval, the quantiles of Beta(D + 1/2, N - D + 1/2), the lower bound 0 at D = 0 and
 * the upper 1 at D = N; the estimate is D / N. No correlation: the posterior of independent trials. */
export function pdJeffreys(defaults: number, n: number, opts: { level?: number } = {}): PdInterval {
  checkCounts(defaults, n);
  const level = given(opts.level, 0.95);
  kappa(level);
  const a = defaults + 0.5;
  const b = n - defaults + 0.5;
  const lo = defaults > 0 ? betaQuantile((1 - level) / 2, a, b) : 0;
  const hi = defaults < n ? betaQuantile(0.5 + level / 2, a, b) : 1;
  return interval('jeffreys', defaults / n, lo, hi, n, n, level);
}

// ---------------------------------------------------------------------------------------------------------------------
// the IRB capital of a portfolio by grade (credit.ts irbCapital, the port of regulatory.irb)

export interface IrbAssumptions {
  assetClass: AssetClass;
  lgd: number;
  maturity: number;
  regime: Regime;
}

export interface PortfolioRiskWeight {
  /** Each grade's risk weight, a share of EAD; null where the grade has no PD. */
  riskWeights: (number | null)[];
  /** The exposure-weighted average risk weight; null when a grade holding exposure has no PD. */
  average: number | null;
}

/** Each grade's IRB risk weight (share of EAD, the regime's PD floor applied, so a PD of 0, a grade that never
 * defaulted, takes the floor's) and the portfolio's exposure-weighted average: the capital of a portfolio by grade
 * under one PD definition, as the case's impact computes it (c04_transitions._portfolio_rw). A grade's PD is null
 * where the definition gives none (Moody's scale has no default category, so its generators give no PD): the average
 * is then null when that grade holds exposure, and a grade without exposure is left out of it. Refused: a PD that is
 * neither null nor a number in [0, 1) (1 is a defaulted exposure, outside the formula, which the engine refuses too),
 * an exposure that is not a non-negative number, no exposure at all, an LGD outside [0, 1], and a PD the formula has
 * no value at (0 in a class exempt from the floor). */
export function portfolioRiskWeight(
  pds: readonly (number | null)[],
  exposure: readonly number[],
  irb: IrbAssumptions,
): PortfolioRiskWeight {
  if (pds.length !== exposure.length) throw new Error('one exposure per grade');
  if (pds.some((p) => p !== null && !(Number.isFinite(p) && p >= 0 && p < 1))) {
    throw new Error("a grade's PD is null (none) or a number in [0, 1)");
  }
  if (exposure.some((e) => !(Number.isFinite(e) && e >= 0))) throw new Error('the exposures are non-negative numbers');
  const total = sum(exposure);
  if (!(total > 0)) throw new Error('the exposures are all zero');
  if (!(Number.isFinite(irb.lgd) && irb.lgd >= 0 && irb.lgd <= 1)) throw new Error('lgd must lie in [0, 1]');
  const opts = { maturity: irb.maturity, regime: irb.regime };
  const riskWeights = pds.map((pd) => {
    if (pd === null) return null;
    const rw = irbCapital(irb.assetClass, pd, irb.lgd, opts).riskWeight;
    if (!Number.isFinite(rw)) throw new Error(`the IRB formula has no value at PD ${pd} (${irb.assetClass})`);
    return rw;
  });
  let weighted = 0;
  for (let i = 0; i < riskWeights.length; i++) {
    if (exposure[i] === 0) continue;
    const rw = riskWeights[i];
    if (rw === null) return { riskWeights, average: null };
    weighted += rw * exposure[i];
  }
  return { riskWeights, average: weighted / total };
}
