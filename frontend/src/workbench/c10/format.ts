// The number formats the C10 views share. Nothing here computes a statistic: it only writes an amount, a percent or a
// year in the unit its place can hold.
import { formatNumber, pick } from '@fasl-work/caos-app-shell';
import type { Bi } from '../c03/U6Shared';
import { axisScale, compactMoney } from '../c06/format';

export type Lang = 'en' | 'es';

/** An amount for a label or a read-out: scaled to millions or billions with the unit that says so ("0.8738 m USD"). */
export function moneyText(v: number, currency: string, lang: Lang): string {
  const c = compactMoney(v, currency);
  return `${formatNumber(c.value, lang, c.format)} ${pick(c.unit, lang)}`;
}

/** The amount in full, with separators and no unit: for the tables that sit under a drawing. */
export const fullMoney = (v: number | null | undefined, lang: Lang): string => formatNumber(v, lang, { decimals: 0 });

/** The divisor and the unit text for an axis of amounts whose largest tick is `max`. */
export function moneyAxis(max: number, currency: string): { div: number; unit: Bi } {
  const a = axisScale(max, currency);
  return { div: a.div, unit: a.unit as Bi };
}

/** A rate as a percent with the decimals its place can hold. */
export const pctText = (v: number | null | undefined, lang: Lang, decimals = 2): string => formatNumber(v, lang, { percent: true, decimals });
