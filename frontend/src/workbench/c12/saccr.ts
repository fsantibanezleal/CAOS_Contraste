// The live SA-CCR of C12: a TypeScript port of the interest rate class of CRE52 (in force 2023-01-01), held to the C12
// documents' `sa_ccr` block by a parity test at 1e-9 relative (the SDD's lanes rule; C05's engine/credit.ts is the
// model). Every formula is transcribed from dossier 01 section E.2 (read at the BIS page on 2026-10-04):
//   EAD = alpha (RC + PFE), alpha = 1.4                                                     CRE52.1
//   RC unmargined = max(V - C, 0); RC margined = max(V - C, TH + MTA - NICA, 0)              CRE52.10, CRE52.18
//   PFE = multiplier AddOn, multiplier = min(1, Floor + (1 - Floor) exp((V - C) / (2 (1 - Floor) AddOn))), Floor 5%   CRE52.20, CRE52.23
//   supervisory duration SD = (exp(-0.05 S) - exp(-0.05 E)) / 0.05                           CRE52.34
//   maturity factor, unmargined sqrt(min(M, 1)); margined 3/2 sqrt(MPOR / 1 year), 250 business days to the year   CRE52.48, CRE52.52
//   interest rate buckets B1 (under 1 year), B2 (1 to 5 years), B3 (over 5), offset formula or the sum of absolute values   CRE52.57
//   interest rate supervisory factor 0.50%                                                   CRE52.72 Table 2
// The swaps of the case are linear: the supervisory delta is +1 for a payer and -1 for a receiver and is read from the
// document. The other four asset classes (FX, credit, equity, commodity) hold no trade in C12 and enter as add-ons the
// caller states, so the port is the whole formula for the case's book and an honest limit for any other.

/** Alpha of CRE52.1. */
export const SA_CCR_ALPHA = 1.4;
/** The floor of the multiplier, CRE52.23. */
export const SA_CCR_FLOOR = 0.05;
/** The supervisory factor of the interest rate class, CRE52.72 Table 2. */
export const SA_CCR_IR_FACTOR = 0.005;
/** The supervisory discount rate of the duration, CRE52.34. */
export const SA_CCR_RATE = 0.05;
/** The business days to the year of the margined maturity factor, CRE52.52. */
export const SA_CCR_BUSINESS_DAYS = 250;

export type Bucket = 'B1' | 'B2' | 'B3';

export interface SaCcrTradeInput {
  tradeId: string;
  hedgingSet: string;
  startYears: number;
  endYears: number;
  notional: number;
  /** The supervisory delta: +1 for a payer swap, -1 for a receiver swap. */
  delta: number;
}

export interface SaCcrInput {
  trades: SaCcrTradeInput[];
  /** The current value of the netting set, V. */
  v: number;
  /** The net independent collateral amount held, C. */
  c: number;
  th: number;
  mta: number;
  nica: number;
  /** The margin period of risk in business days, or null for an unmargined netting set. */
  mporBusinessDays: number | null;
  /** Whether each hedging set takes the offset formula of CRE52.57 (true when absent) or the sum of the absolute values. */
  offset?: Record<string, boolean>;
  /** The add-ons of the classes the case holds no trade in (zero when absent). */
  otherAddOns?: { fx: number; credit: number; equity: number; commodity: number };
}

export interface SaCcrTradeResult {
  tradeId: string;
  hedgingSet: string;
  supervisoryDuration: number;
  adjustedNotional: number;
  maturityFactor: number;
  bucket: Bucket;
  effectiveNotional: number;
}

export interface SaCcrHedgingSetResult {
  hedgingSet: string;
  dB1: number;
  dB2: number;
  dB3: number;
  offset: boolean;
  effectiveNotional: number;
  addOn: number;
}

export interface SaCcrResult {
  rc: number;
  trades: SaCcrTradeResult[];
  hedgingSets: SaCcrHedgingSetResult[];
  addOnInterestRate: number;
  addOnAggregate: number;
  multiplier: number;
  pfe: number;
  ead: number;
}

/** CRE52.34. */
export const supervisoryDuration = (start: number, end: number): number => (Math.exp(-SA_CCR_RATE * start) - Math.exp(-SA_CCR_RATE * end)) / SA_CCR_RATE;

/** CRE52.48 (unmargined) and CRE52.52 (margined). */
export function maturityFactor(endYears: number, mporBusinessDays: number | null): number {
  if (mporBusinessDays === null) return Math.sqrt(Math.min(endYears, 1));
  return 1.5 * Math.sqrt(mporBusinessDays / SA_CCR_BUSINESS_DAYS);
}

/** CRE52.57: B1 under one year, B2 from one to five years, B3 over five. */
export const irBucket = (endYears: number): Bucket => (endYears < 1 ? 'B1' : endYears <= 5 ? 'B2' : 'B3');

/** CRE52.57: the offset formula, or the sum of the absolute values of the three buckets. */
export function hedgingSetEffectiveNotional(d1: number, d2: number, d3: number, offset = true): number {
  if (!offset) return Math.abs(d1) + Math.abs(d2) + Math.abs(d3);
  return Math.sqrt(d1 * d1 + d2 * d2 + d3 * d3 + 1.4 * d1 * d2 + 1.4 * d2 * d3 + 0.6 * d1 * d3);
}

/** CRE52.10 and CRE52.18. */
export function replacementCost(v: number, c: number, margined: boolean, th = 0, mta = 0, nica = 0): number {
  return margined ? Math.max(v - c, th + mta - nica, 0) : Math.max(v - c, 0);
}

/** CRE52.23: the multiplier is one when the aggregate add-on is not positive. */
export function multiplier(vMinusC: number, addOn: number): number {
  if (addOn <= 0) return 1;
  return Math.min(1, SA_CCR_FLOOR + (1 - SA_CCR_FLOOR) * Math.exp(vMinusC / (2 * (1 - SA_CCR_FLOOR) * addOn)));
}

/** The whole calculation, every intermediate value returned so the CRE99 style step-by-step check is possible. */
export function saCcr(input: SaCcrInput): SaCcrResult {
  const margined = input.mporBusinessDays !== null;
  const trades: SaCcrTradeResult[] = input.trades.map((t) => {
    const sd = supervisoryDuration(t.startYears, t.endYears);
    const adjusted = t.notional * sd;
    const mf = maturityFactor(t.endYears, input.mporBusinessDays);
    return { tradeId: t.tradeId, hedgingSet: t.hedgingSet, supervisoryDuration: sd, adjustedNotional: adjusted, maturityFactor: mf, bucket: irBucket(t.endYears), effectiveNotional: adjusted * t.delta * mf };
  });
  const sets = new Map<string, [number, number, number]>();
  for (const t of trades) {
    const d = sets.get(t.hedgingSet) ?? [0, 0, 0];
    d[t.bucket === 'B1' ? 0 : t.bucket === 'B2' ? 1 : 2] += t.effectiveNotional;
    sets.set(t.hedgingSet, d);
  }
  const hedgingSets: SaCcrHedgingSetResult[] = [...sets.entries()].map(([hedgingSet, [d1, d2, d3]]) => {
    const offset = input.offset?.[hedgingSet] ?? true;
    const effectiveNotional = hedgingSetEffectiveNotional(d1, d2, d3, offset);
    return { hedgingSet, dB1: d1, dB2: d2, dB3: d3, offset, effectiveNotional, addOn: SA_CCR_IR_FACTOR * effectiveNotional };
  });
  const addOnInterestRate = hedgingSets.reduce((s, h) => s + h.addOn, 0);
  const other = input.otherAddOns ?? { fx: 0, credit: 0, equity: 0, commodity: 0 };
  const addOnAggregate = addOnInterestRate + other.fx + other.credit + other.equity + other.commodity;
  const rc = replacementCost(input.v, input.c, margined, input.th, input.mta, input.nica);
  const mult = multiplier(input.v - input.c, addOnAggregate);
  const pfe = mult * addOnAggregate;
  return { rc, trades, hedgingSets, addOnInterestRate, addOnAggregate, multiplier: mult, pfe, ead: SA_CCR_ALPHA * (rc + pfe) };
}

/** The slice of a C12 document's `sa_ccr` block the port reads and is held to (the generated type, narrowed to what the parity needs). */
export interface SaCcrBlock {
  margined: boolean;
  v: { amount: number };
  c: { amount: number };
  th: { amount: number };
  mta: { amount: number };
  nica: { amount: number };
  mpor_business_days: number | null;
  rc: { amount: number };
  trades: Array<{
    trade_id: string;
    hedging_set: string;
    start_years: number;
    end_years: number;
    notional: { amount: number };
    supervisory_duration: number;
    adjusted_notional: { amount: number };
    delta: number;
    maturity_factor: number;
    bucket: string;
    effective_notional: number;
  }>;
  hedging_sets: Array<{ hedging_set: string; d_b1: number; d_b2: number; d_b3: number; offset: boolean; effective_notional: number; addon: number }>;
  addon_by_class: { interest_rate: number; fx: number; credit: number; equity: number; commodity: number };
  addon_aggregate: { amount: number };
  multiplier: number;
  pfe: { amount: number };
  ead: { amount: number };
}

/** The port's input from the document's block: what the bake used, so the port's output is the block's (the parity test). */
export function saCcrInputFrom(block: SaCcrBlock): SaCcrInput {
  return {
    trades: block.trades.map((t) => ({ tradeId: t.trade_id, hedgingSet: t.hedging_set, startYears: t.start_years, endYears: t.end_years, notional: t.notional.amount, delta: t.delta })),
    v: block.v.amount,
    c: block.c.amount,
    th: block.th.amount,
    mta: block.mta.amount,
    nica: block.nica.amount,
    mporBusinessDays: block.mpor_business_days,
    offset: Object.fromEntries(block.hedging_sets.map((h) => [h.hedging_set, h.offset])),
    otherAddOns: { fx: block.addon_by_class.fx, credit: block.addon_by_class.credit, equity: block.addon_by_class.equity, commodity: block.addon_by_class.commodity },
  };
}

/** Two numbers equal to a relative tolerance (1e-9, the SDD's deterministic parity); equal numbers, zeros included, always agree. */
export const closeTo = (a: number, b: number, rel = 1e-9): boolean => a === b || Math.abs(a - b) <= rel * Math.max(Math.abs(a), Math.abs(b));

/** Every field in which the port's result departs from the document's block at the relative tolerance; empty when it is the block. */
export function saCcrMismatches(r: SaCcrResult, block: SaCcrBlock, rel = 1e-9): string[] {
  const out: string[] = [];
  const check = (name: string, live: number, committed: number) => {
    if (!closeTo(live, committed, rel)) out.push(`${name}: live ${live}, committed ${committed}`);
  };
  check('rc', r.rc, block.rc.amount);
  check('addon_by_class.interest_rate', r.addOnInterestRate, block.addon_by_class.interest_rate);
  check('addon_aggregate', r.addOnAggregate, block.addon_aggregate.amount);
  check('multiplier', r.multiplier, block.multiplier);
  check('pfe', r.pfe, block.pfe.amount);
  check('ead', r.ead, block.ead.amount);
  for (const t of block.trades) {
    const live = r.trades.find((x) => x.tradeId === t.trade_id);
    if (!live) {
      out.push(`${t.trade_id}: absent from the port`);
      continue;
    }
    check(`${t.trade_id}.supervisory_duration`, live.supervisoryDuration, t.supervisory_duration);
    check(`${t.trade_id}.adjusted_notional`, live.adjustedNotional, t.adjusted_notional.amount);
    check(`${t.trade_id}.maturity_factor`, live.maturityFactor, t.maturity_factor);
    check(`${t.trade_id}.effective_notional`, live.effectiveNotional, t.effective_notional);
    if (live.bucket !== t.bucket) out.push(`${t.trade_id}.bucket: live ${live.bucket}, committed ${t.bucket}`);
  }
  for (const h of block.hedging_sets) {
    const live = r.hedgingSets.find((x) => x.hedgingSet === h.hedging_set);
    if (!live) {
      out.push(`${h.hedging_set}: absent from the port`);
      continue;
    }
    check(`${h.hedging_set}.d_b1`, live.dB1, h.d_b1);
    check(`${h.hedging_set}.d_b2`, live.dB2, h.d_b2);
    check(`${h.hedging_set}.d_b3`, live.dB3, h.d_b3);
    check(`${h.hedging_set}.effective_notional`, live.effectiveNotional, h.effective_notional);
    check(`${h.hedging_set}.addon`, live.addOn, h.addon);
  }
  return out;
}
