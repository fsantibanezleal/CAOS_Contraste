// The live lane of C05 (SDD section 3, CT-209): the credit calculators the browser recomputes from committed inputs.
// Each is a port of a riskvalidation 0.2.0 function and is held to it by engine/credit.test.ts on the parity points the
// pipeline exports with every artifact (1e-9 relative): the IRB risk weight by regime (regulatory.irb), the most
// prudent bounds (engines.low_default, sections 2 to 5 of Pluto and Tasche), quasi moment matching and the four case 1
// approaches of Tasche (2013) (engines.pd_curve). Grades are best first, as in the engine.

// ---------------------------------------------------------------------------------------------------------------------
// the standard normal distribution, to near machine precision

const SQRT2PI = Math.sqrt(2 * Math.PI);

/** The standard normal density. */
export const phi = (x: number): number => Math.exp(-0.5 * x * x) / SQRT2PI;

/** The upper tail Q(x) = 1 - N(x) for x >= 0: the Taylor series of N on [0, 3), Laplace's continued fraction beyond
 * (evaluated by the modified Lentz method), both to about 1e-16 relative. */
function upperTail(x: number): number {
  if (x < 3) {
    // N(x) - 1/2 = phi(x) * sum_{k>=0} x^(2k+1) / (2k+1)!!
    let term = x;
    let sum = x;
    for (let k = 1; k < 500; k++) {
      term *= (x * x) / (2 * k + 1);
      sum += term;
      if (Math.abs(term) < 1e-17 * Math.abs(sum)) break;
    }
    return 0.5 - phi(x) * sum;
  }
  // Q(x) = phi(x) / (x + 1/(x + 2/(x + 3/(x + ...))))
  const tiny = 1e-300;
  let f = x;
  let c = x;
  let d = 0;
  for (let k = 1; k < 500; k++) {
    d = x + k * d;
    d = Math.abs(d) < tiny ? tiny : d;
    c = x + k / c;
    c = Math.abs(c) < tiny ? tiny : c;
    d = 1 / d;
    const delta = c * d;
    f *= delta;
    if (Math.abs(delta - 1) < 1e-16) break;
  }
  return phi(x) / f;
}

/** The standard normal distribution function N(x). */
export function ncdf(x: number): number {
  if (Number.isNaN(x)) return NaN;
  if (x === Infinity) return 1;
  if (x === -Infinity) return 0;
  return x >= 0 ? 1 - upperTail(x) : upperTail(-x);
}

/** The standard normal quantile G(p) = N^{-1}(p): a rational start (Abramowitz and Stegun 26.2.23) refined by Halley
 * steps on the accurate N until the step is below 1e-15. */
export function nquantile(p: number): number {
  if (!(p > 0 && p < 1)) {
    if (p === 0) return -Infinity;
    if (p === 1) return Infinity;
    return NaN;
  }
  const q = p < 0.5 ? p : 1 - p;
  const t = Math.sqrt(-2 * Math.log(q));
  let x = t - (2.515517 + 0.802853 * t + 0.010328 * t * t) / (1 + 1.432788 * t + 0.189269 * t * t + 0.001308 * t * t * t);
  x = p < 0.5 ? -x : x;
  for (let i = 0; i < 12; i++) {
    // the error in the tail the root lies in, to keep relative precision for small p
    const e = x < 0 ? upperTail(-x) - p : 1 - p - upperTail(x);
    const u = e / phi(x);
    const step = u / (1 + (x * u) / 2);
    x -= step;
    if (Math.abs(step) < 1e-15 * Math.max(1, Math.abs(x))) break;
  }
  return x;
}

// ---------------------------------------------------------------------------------------------------------------------
// Brent's method, the root finder the engine uses (scipy.optimize.brentq)

export function brent(f: (x: number) => number, a: number, b: number, xtol = 1e-15, rtol = 4 * Number.EPSILON, maxiter = 500): number {
  let fa = f(a);
  let fb = f(b);
  if (fa === 0) return a;
  if (fb === 0) return b;
  if (fa * fb > 0) throw new Error('brent: the interval does not bracket a root');
  let c = a;
  let fc = fa;
  let d = b - a;
  let e = d;
  for (let i = 0; i < maxiter; i++) {
    if (fb * fc > 0) {
      c = a;
      fc = fa;
      d = b - a;
      e = d;
    }
    if (Math.abs(fc) < Math.abs(fb)) {
      a = b;
      b = c;
      c = a;
      fa = fb;
      fb = fc;
      fc = fa;
    }
    const tol = 2 * rtol * Math.abs(b) + 0.5 * xtol;
    const m = 0.5 * (c - b);
    if (Math.abs(m) <= tol || fb === 0) return b;
    if (Math.abs(e) >= tol && Math.abs(fa) > Math.abs(fb)) {
      const s = fb / fa;
      let p: number;
      let q: number;
      if (a === c) {
        p = 2 * m * s;
        q = 1 - s;
      } else {
        const qq = fa / fc;
        const r = fb / fc;
        p = s * (2 * m * qq * (qq - r) - (b - a) * (r - 1));
        q = (qq - 1) * (r - 1) * (s - 1);
      }
      if (p > 0) q = -q;
      else p = -p;
      if (2 * p < Math.min(3 * m * q - Math.abs(tol * q), Math.abs(e * q))) {
        e = d;
        d = p / q;
      } else {
        d = m;
        e = d;
      }
    } else {
      d = m;
      e = d;
    }
    a = b;
    fa = fb;
    b += Math.abs(d) > tol ? d : m > 0 ? tol : -tol;
    fb = f(b);
  }
  throw new Error('brent: no convergence');
}

// ---------------------------------------------------------------------------------------------------------------------
// the IRB risk-weight functions (riskvalidation.regulatory.irb; CRE31, CRE32; CRR3 Article 153; Basel II CRE30.4)

export type Regime = 'basel3' | 'crr3' | 'basel2';
export type AssetClass = 'corporate' | 'sovereign' | 'bank' | 'financial_institution' | 'residential_mortgage' | 'qrre' | 'other_retail';

const REGIME_SPEC: Record<Regime, { scaling: number; floor: number; floorQrre: number }> = {
  basel3: { scaling: 1.0, floor: 0.0005, floorQrre: 0.001 },
  crr3: { scaling: 1.0, floor: 0.0005, floorQrre: 0.001 },
  basel2: { scaling: 1.06, floor: 0.0003, floorQrre: 0.0003 },
};
const RETAIL: AssetClass[] = ['residential_mortgage', 'qrre', 'other_retail'];

const w = (pd: number, k: number): number => (1 - Math.exp(-k * pd)) / (1 - Math.exp(-k));

/** The asset correlation of CRE31.5 to CRE31.16 (sales in EUR million for the firm-size adjustment). */
export function irbCorrelation(cls: AssetClass, pd: number, salesEurM?: number, largeFi = false): number {
  if (cls === 'residential_mortgage') return 0.15;
  if (cls === 'qrre') return 0.04;
  if (cls === 'other_retail') return 0.03 * w(pd, 35) + 0.16 * (1 - w(pd, 35));
  let r = 0.12 * w(pd, 50) + 0.24 * (1 - w(pd, 50));
  if (cls === 'corporate' && salesEurM !== undefined && salesEurM < 50) {
    const s = Math.min(Math.max(salesEurM, 5), 50);
    r -= 0.04 * (1 - (s - 5) / 45);
  }
  if (largeFi || cls === 'financial_institution') r *= 1.25;
  return r;
}

export interface IrbResult {
  pdApplied: number;
  correlation: number;
  maturityAdjustment: number | null;
  k: number;
  riskWeight: number;
}

/** K, the risk weight 12.5 K times the regime's scaling, for a non-defaulted exposure. */
export function irbCapital(cls: AssetClass, pd: number, lgd: number, opts: { maturity?: number; regime?: Regime; salesEurM?: number; revolver?: boolean; largeFi?: boolean } = {}): IrbResult {
  const regime = REGIME_SPEC[opts.regime ?? 'basel3'];
  const floor = cls === 'qrre' && opts.revolver ? regime.floorQrre : regime.floor;
  const pdApplied = cls === 'sovereign' ? pd : Math.max(pd, floor);
  const r = irbCorrelation(cls, pdApplied, opts.salesEurM, opts.largeFi);
  let k = lgd * ncdf((nquantile(pdApplied) + Math.sqrt(r) * nquantile(0.999)) / Math.sqrt(1 - r)) - pdApplied * lgd;
  let ma: number | null = null;
  if (!RETAIL.includes(cls)) {
    const m = Math.min(Math.max(opts.maturity ?? 2.5, 1), 5);
    const b = (0.11852 - 0.05478 * Math.log(pdApplied)) ** 2;
    ma = (1 + (m - 2.5) * b) / (1 - 1.5 * b);
    k *= ma;
  }
  k = Math.max(k, 0);
  return { pdApplied, correlation: r, maturityAdjustment: ma, k, riskWeight: 12.5 * k * regime.scaling };
}

// ---------------------------------------------------------------------------------------------------------------------
// most prudent estimation (riskvalidation.engines.low_default)

/** P(Binomial(n, p) <= d), by direct summation in logs (d is small in a low-default portfolio). */
export function binomCdf(d: number, n: number, p: number): number {
  if (d >= n) return 1;
  if (p <= 0) return 1;
  if (p >= 1) return d >= n ? 1 : 0;
  const lp = Math.log(p);
  const lq = Math.log1p(-p);
  let logC = 0;
  let sum = 0;
  for (let i = 0; i <= d; i++) {
    if (i > 0) logC += Math.log(n - i + 1) - Math.log(i);
    sum += Math.exp(logC + i * lp + (n - i) * lq);
  }
  return Math.min(sum, 1);
}

export interface Quadrature {
  nodes: number[];
  weights: number[];
}

function pooled(obligors: number[], defaults: number[]): { n: number[]; d: number[] } {
  const n: number[] = [];
  const d: number[] = [];
  let sn = 0;
  let sd = 0;
  for (let i = obligors.length - 1; i >= 0; i--) {
    sn += obligors[i];
    sd += defaults[i];
    n.unshift(sn);
    d.unshift(sd);
  }
  return { n, d };
}

function bound(n: number, d: number, gamma: number, rho: number, quad: Quadrature): number {
  if (d >= n) return 1;
  const target = 1 - gamma;
  if (rho === 0) {
    if (d === 0) return -Math.expm1(Math.log1p(-gamma) / n); // 1 - (1 - gamma)^(1/n)
    return brent((p) => binomCdf(d, n, p) - target, 1e-15, 1 - 1e-15, 1e-17, 1e-13);
  }
  const sr = Math.sqrt(rho);
  const s1r = Math.sqrt(1 - rho);
  const tail = (p: number) => {
    const g = nquantile(p);
    let s = 0;
    for (let i = 0; i < quad.nodes.length; i++) s += quad.weights[i] * binomCdf(d, n, ncdf((g - sr * quad.nodes[i]) / s1r));
    return s - target;
  };
  return brent(tail, 1e-12, 1 - 1e-12, 1e-17, 1e-13);
}

/** The most prudent bounds per grade (best first) at confidence `gamma`, independent or with asset correlation `rho`. */
export function mostPrudent(obligors: number[], defaults: number[], gamma: number, rho: number, quad: Quadrature): number[] {
  const { n, d } = pooled(obligors, defaults);
  return n.map((ni, i) => bound(ni, d[i], gamma, rho, quad));
}

/** Section 5, (5.1) and (5.2): one factor K so that the obligor-weighted mean of the bounds meets `target`. */
export function scaleBounds(bounds: number[], obligors: number[], target: number): { pd: number[]; k: number } {
  const total = obligors.reduce((a, b) => a + b, 0);
  const mean = bounds.reduce((a, b, i) => a + b * obligors[i], 0) / total;
  const k = target / mean;
  return { pd: bounds.map((b) => k * b), k };
}

/** The bounds scaled to the portfolio's upper bound, the best grade's bound (the paper's proposal). */
export function mostPrudentScaled(obligors: number[], defaults: number[], gamma: number, rho: number, quad: Quadrature): { pd: number[]; k: number; raw: number[] } {
  const raw = mostPrudent(obligors, defaults, gamma, rho, quad);
  return { ...scaleBounds(raw, obligors, raw[0]), raw };
}

// ---------------------------------------------------------------------------------------------------------------------
// PD curve calibration (riskvalidation.engines.pd_curve; Tasche 2013)

const sum = (a: number[]): number => a.reduce((s, v) => s + v, 0);
const norm = (a: number[]): number[] => {
  const t = sum(a);
  return a.map((v) => v / t);
};
const rev = (a: number[]): number[] => [...a].reverse();

/** (3.7), worst first. */
function arProfilesW(dp: number[], sp: number[]): number {
  let below = 0;
  let pos = 0;
  let neg = 0;
  const above: number[] = new Array(dp.length).fill(0);
  for (let x = dp.length - 2; x >= 0; x--) above[x] = above[x + 1] + dp[x + 1];
  for (let x = 0; x < dp.length; x++) {
    pos += sp[x] * below;
    neg += sp[x] * above[x];
    below += dp[x];
  }
  return pos - neg;
}

/** (A.11b), worst first. */
function arCurveW(cur: number[], pi: number[]): number {
  let p = 0;
  for (let i = 0; i < cur.length; i++) p += cur[i] * pi[i];
  let riskier = 0;
  let total = 0;
  for (let x = 0; x < cur.length; x++) {
    total += 2 * (1 - cur[x]) * pi[x] * riskier + cur[x] * (1 - cur[x]) * pi[x] * pi[x];
    riskier += cur[x] * pi[x];
  }
  return total / (p * (1 - p)) - 1;
}

/** The accuracy ratio of a PD curve and a profile, best first (A.11b). */
export const accuracyRatioFromCurve = (curve: number[], profile: number[]): number => arCurveW(rev(curve), rev(norm(profile)));

export interface QmmResult {
  curve: number[];
  alpha: number;
  beta: number;
}

/** Quasi moment matching (appendix A): the robust logistic curve on the profile (best first) with unconditional PD
 * `pdTarget` and accuracy ratio `arTarget`; `survival` (best first) defines F~_N, the profile standing in for it. */
export function qmm(profile: number[], pdTarget: number, arTarget: number, survival?: number[]): QmmResult {
  const pi = rev(norm(profile));
  const sp = survival ? rev(norm(survival)) : pi;
  const z: number[] = [];
  let cum = 0;
  for (const s of sp) {
    const prev = cum;
    cum += s;
    z.push(nquantile(Math.min(Math.max((prev + cum) / 2, 1e-15), 1 - 1e-15)));
  }
  const curve = (a: number, b: number) => z.map((zi) => 1 / (1 + Math.exp(Math.min(Math.max(a + b * zi, -700), 700))));
  let mu = 0;
  for (let i = 0; i < pi.length; i++) mu += pi[i] * z[i];
  let tau2 = 0;
  for (let i = 0; i < pi.length; i++) tau2 += pi[i] * (z[i] - mu) ** 2;
  const p = pdTarget;
  const c = Math.SQRT2 * nquantile((arTarget + 1) / 2);
  const sigma2 = tau2 / (1 + p * (1 - p) * c * c);
  const sigma = Math.sqrt(sigma2);
  const muN = mu + p * sigma * c;
  const muD = mu - (1 - p) * sigma * c;
  const start = [(muD * muD - muN * muN) / (2 * sigma2) + Math.log((1 - p) / p), (muN - muD) / sigma2];
  const alphaFor = (beta: number): number => {
    const f = (a: number) => {
      const cur = curve(a, beta);
      let s = 0;
      for (let i = 0; i < pi.length; i++) s += cur[i] * pi[i];
      return s - p;
    };
    const centre = start[0] + (start[1] - beta) * mu;
    let width = 1;
    for (let k = 0; k < 60; k++) {
      if (f(centre - width) >= 0 && f(centre + width) <= 0) return brent(f, centre - width, centre + width, 1e-14);
      width *= 2;
    }
    throw new Error('qmm: no bracket for alpha');
  };
  const g = (beta: number) => arCurveW(curve(alphaFor(beta), beta), pi) - arTarget;
  let hi = Math.max(start[1], 1e-3);
  while (g(hi) < 0) {
    hi *= 2;
    if (hi > 1e4) throw new Error('qmm: the accuracy ratio is not attainable on this grade scale');
  }
  let lo = hi / 2;
  while (lo > 1e-12 && g(lo) > 0) lo /= 2;
  const beta = brent(g, lo, hi, 1e-14);
  const alpha = alphaFor(beta);
  return { curve: rev(curve(alpha, beta)), alpha, beta };
}

/** The forecast curve of a case 1 approach (Tasche 2013, section 4.2), from the 2009 model and the forecast year's
 * profile at the forecast PD `p1`. */
export type Case1 = 'A1-idp' | 'A2-iar' | 'A3-spd' | 'A4-slr';

export interface EstimationModel {
  curve0: number[];          // the QMM curve of the estimation period
  pd0: number;               // its unconditional PD
  ar0: number;               // the estimation accuracy ratio
  defaultProfile0: number[]; // the observed estimation default profile
}

export function calibrate(approach: Case1, model: EstimationModel, profile1: number[], p1: number): { curve: number[]; constant: number | null; improper?: string } {
  const pi1 = norm(profile1);
  if (approach === 'A3-spd') {
    const cpd = p1 / sum(model.curve0.map((c, i) => c * pi1[i]));
    const cur = model.curve0.map((c) => cpd * c);
    if (cur.some((v) => v >= 1)) return { curve: cur, constant: cpd, improper: 'a scaled PD exceeds one (section 4.2.3)' };
    return { curve: cur, constant: cpd };
  }
  if (approach === 'A4-slr') {
    const lam0 = model.curve0.map((c) => ((1 - c) / c) * (model.pd0 / (1 - model.pd0)));
    const lo = 1 / sum(pi1.map((v, i) => v * lam0[i]));
    const hi = sum(pi1.map((v, i) => v / lam0[i]));
    const f = (c: number) => sum(pi1.map((v, i) => v / (p1 + (1 - p1) * c * lam0[i]))) - 1;
    const c = brent(f, lo / 2, 2 * hi, 1e-300);
    return { curve: lam0.map((l) => p1 / (p1 + (1 - p1) * c * l)), constant: c };
  }
  if (approach === 'A2-iar') return { curve: qmm(pi1, p1, model.ar0).curve, constant: null };
  // A1-idp, approach (ii) of section 4.2.1
  const dp0 = norm(model.defaultProfile0);
  const bad = dp0.findIndex((d, i) => p1 * d > pi1[i] + 1e-12 || p1 * (1 - d) > 1 - pi1[i] + 1e-12);
  if (bad >= 0) return { curve: [], constant: null, improper: 'condition (4.6a) fails' };
  const raw = pi1.map((v, i) => Math.max((v - p1 * dp0[i]) / (1 - p1), 0));
  const ar1 = arProfilesW(rev(dp0), rev(norm(raw)));
  return { curve: qmm(pi1, p1, ar1, raw).curve, constant: ar1 };
}
