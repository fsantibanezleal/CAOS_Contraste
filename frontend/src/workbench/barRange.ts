// The domain of a horizontal BarChart that holds a negative value (BL-120).
//
// The shell writes a negative bar's value label at the bar's far end, anchored on its right edge, and pins it to the start of the
// axis when the bar ends closer to that start than the label is wide: the label then lies over its own bar (known shell defect,
// entry 45 of conventions/shell-known-defects.md, CAOS_APP_SHELL#233). The longest negative bar of a chart reaches the start of an
// automatic domain, so on a narrow plot (390 px, Spanish) its light label sat on the bar's green fill at 1.65:1 (G13). The chart's
// own `axis.range` is the shell's documented way to fix a domain, so the product gives the negative side room for one label.

/** The share of the longest negative bar that the domain adds beyond it: a label of up to about 50 px fits on the plot of a phone. */
export const SIGNED_HEADROOM = 0.35;

/**
 * The `axis.range` for a bar chart whose values can fall below zero: the negative side extends past the longest negative bar by
 * `SIGNED_HEADROOM` of its length, the positive side is the data's own top (zero when all are negative), so a positive bar keeps its
 * label to its right as before. `undefined` (the shell's automatic domain) for data with no finite negative value.
 */
export function signedRange(values: ReadonlyArray<number | null | undefined>): [number, number] | undefined {
  let low = 0;
  let high = 0;
  for (const v of values) {
    if (typeof v !== 'number' || !Number.isFinite(v)) continue;
    if (v < low) low = v;
    if (v > high) high = v;
  }
  if (low >= 0) return undefined;
  return [low * (1 + SIGNED_HEADROOM), high];
}
