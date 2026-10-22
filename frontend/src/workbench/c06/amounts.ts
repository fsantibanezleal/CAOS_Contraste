// The amounts of a C06 table in the unit of their column (U16-F6, V06-3): eleven digits of an amount (19,172,497,231.81) made
// the columns wider than their card and clipped the last ones; scaled to billions or millions with the unit in the header, a
// column keeps the figures a reader compares (19.172 bn USD) and every row of the table is whole.
import { formatNumber, type BiText } from '@fasl-work/caos-app-shell';
import { axisScale, type Lang } from './format';

export interface ColumnScale {
  /** The unit the header carries ("bn USD", "mil M USD"). */
  unit: BiText;
  /** One amount of the column in that unit; null stays "not available". */
  fmt: (v: number | null | undefined, lang: Lang) => string;
}

/** The scale of a column of amounts, from its largest absolute value; the figures keep three significant decimals in billions, two in millions. */
export function columnScale(values: ReadonlyArray<number | null | undefined>, currency: string): ColumnScale {
  const max = Math.max(0, ...values.map((v) => (v === null || v === undefined || !Number.isFinite(v) ? 0 : Math.abs(v))));
  const { div, unit } = axisScale(max, currency);
  const decimals = div >= 1e9 ? 3 : div >= 1e6 ? 2 : 2;
  return { unit, fmt: (v, lang) => formatNumber(v === null || v === undefined ? null : v / div, lang, { decimals }) };
}
