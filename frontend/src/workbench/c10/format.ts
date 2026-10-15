// The number formats the C10 views share. Nothing here computes a statistic: it only writes an amount, a percent or a
// year in the unit its place can hold.
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { Bi } from '../c03/U6Shared';
import { axisScale } from '../c06/format';

export type Lang = 'en' | 'es';

/** The amount in full, with separators and no unit: for the tables that sit under a drawing. */
export const fullMoney = (v: number | null | undefined, lang: Lang): string => formatNumber(v, lang, { decimals: 0 });

/** The divisor and the unit text for an axis of amounts whose largest tick is `max`. */
export function moneyAxis(max: number, currency: string): { div: number; unit: Bi } {
  const a = axisScale(max, currency);
  return { div: a.div, unit: a.unit as Bi };
}

/**
 * The height a horizontal bar chart needs for `rows` rows so it never scrolls inside its drawing: about 1.5 rem a row
 * plus 3 rem for the axis at a desktop width, and more on a phone where a long label wraps to two lines, so 2.2 rem a row.
 */
export const barMin = (rows: number): string => `${Math.round((rows * 2.2 + 3) * 10) / 10}rem`;
