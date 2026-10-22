// What the provisions instruments (C06 and C07) share: the number formats, the "not available, with its reason" cell,
// the text of the four stages and the colour of each stage as a shell token. Nothing here computes a statistic.
import { formatNumber, pick, useShellLang, type BiText, type FormatOptions, type ShellColorToken } from '@fasl-work/caos-app-shell';
import type { CSSProperties, ReactNode } from 'react';

/** The stages of the contracts, with the words a reader uses. */
export type StageId = 'stage1' | 'stage2' | 'stage3' | 'poci';

export const STAGE_TEXT: Record<string, BiText> = {
  stage1: { en: 'Stage 1', es: 'Etapa 1' },
  stage2: { en: 'Stage 2', es: 'Etapa 2' },
  stage3: { en: 'Stage 3', es: 'Etapa 3' },
  poci: { en: 'POCI', es: 'POCI' },
  new: { en: 'New', es: 'Nuevas' },
  derecognised: { en: 'Derecognised', es: 'Dadas de baja' },
  'written-off': { en: 'Written off', es: 'Castigadas' },
};

/** The colour of a stage; the word is always printed beside it, never colour alone. */
export const STAGE_COLOR: Record<string, ShellColorToken> = {
  stage1: '--color-accent',
  stage2: '--color-warn',
  stage3: '--color-bad',
  poci: '--color-magenta',
  new: '--color-fg-subtle',
  derecognised: '--color-fg-faint',
  'written-off': '--color-fg-faint',
};

export type Lang = 'en' | 'es';

/** Money in the document's currency: whole units for a currency of large nominal amounts (CLP), cents otherwise. */
export function money(v: number | null | undefined, lang: Lang, currency: string): string {
  return formatNumber(v, lang, { decimals: currency === 'CLP' ? 0 : 2 });
}

export const pct = (v: number | null | undefined, lang: Lang, decimals = 3) => formatNumber(v, lang, { percent: true, decimals });

/** A value the contract allows to be null: the number, or "not available" with the contract's own reason. */
export function MaybeNumber({ value, reason, format }: { value: number | null; reason: string | null; format: (v: number) => string }) {
  const lang = useShellLang();
  if (value !== null) return <>{format(value)}</>;
  return (
    <span data-na="true">
      {formatNumber(null, lang)}
      {reason ? <span className="ct-note" style={{ display: 'block', whiteSpace: 'normal', maxWidth: '18rem', marginLeft: 'auto', textAlign: 'right' }}>({reason})</span> : null}
    </span>
  );
}

/**
 * An amount for a place that is narrow (the rail's read-outs, an axis): the value scaled to billions or millions with
 * the unit that says so ("19.6 bn USD", "19,6 mil M USD"), never an eleven-digit amount. The table beside a drawing
 * keeps the whole amount; a null stays null so the read-out says "not available" in the same unit.
 */
export function compactMoney(v: number | null | undefined, currency: string): { value: number | null; unit: BiText; format: FormatOptions } {
  const a = v === null || v === undefined || !Number.isFinite(v) ? 0 : Math.abs(v);
  const [div, en, es] = a >= 1e9 || a === 0 ? [1e9, 'bn', 'mil M'] : a >= 1e6 ? [1e6, 'm', 'M'] : [1, '', ''];
  const unit: BiText = div === 1 ? { en: currency, es: currency } : { en: `${en} ${currency}`, es: `${es} ${currency}` };
  return { value: v === null || v === undefined || !Number.isFinite(v) ? null : v / div, unit, format: { digits: 4 } };
}

/** The scale of an axis of amounts: the divisor and the unit text its title carries, chosen from the largest tick. */
export function axisScale(max: number, currency: string): { div: number; unit: BiText } {
  const c = compactMoney(max, currency);
  const div = max >= 1e9 ? 1e9 : max >= 1e6 ? 1e6 : 1;
  return { div, unit: c.unit };
}

/** The unit of an axis or a column, "USD" or "CLP", as a bilingual text. */
export const currencyUnit = (currency: string): BiText => ({ en: currency, es: currency });

/** Months as a label of a horizon: "12 m" in English, "12 m" in Spanish (a symbol, the same in both). */
export const monthsLabel = (m: number): string => `${m} m`;

export function useText() {
  const lang = useShellLang();
  return (t: BiText) => pick(t, lang);
}

/** The sorted union of several x arrays (no duplicates). */
export function unionX(...arrays: ReadonlyArray<readonly number[]>): number[] {
  return [...new Set(arrays.flat())].sort((a, b) => a - b);
}

/**
 * The values of a polyline (`xs`, `ys`) at the grid `grid`: the document's own value where the grid hits one of its
 * x, the straight segment between two of its points elsewhere (so the drawn line is the polyline of the document, not
 * a smoother one), null outside its range. A uPlot line breaks at a null, so every line of a chart needs a value at
 * every x of the shared grid.
 */
export function alignTo(xs: readonly number[], ys: readonly number[], grid: readonly number[]): Array<number | null> {
  return grid.map((g) => {
    const exact = xs.indexOf(g);
    if (exact >= 0) return ys[exact];
    const i = xs.findIndex((x) => x > g);
    if (i <= 0) return null;
    const t = (g - xs[i - 1]) / (xs[i] - xs[i - 1]);
    return ys[i - 1] + t * (ys[i] - ys[i - 1]);
  });
}

/**
 * A drawing over its tables inside one filling card: the drawing takes the height the tables leave and the tables
 * scroll under it. One card per view keeps the drawing and the numbers it draws together, and the gate measures the
 * drawing (ADR-0071 rule 8), not a short table beside it.
 */
export function ChartOverTable({ chart, children, chartMin = '15rem' }: { chart: ReactNode; children?: ReactNode; chartMin?: string }) {
  // `chartMin`: a horizontal bar chart needs about 1.5rem a row, or its rows scroll inside the drawing
  return (
    <div className="ct-stack">
      <div className="ct-stack-chart" style={{ minHeight: chartMin, '--ct-chart-min': chartMin } as CSSProperties}>{chart}</div>
      {children ? <div className="ct-stack-table">{children}</div> : null}
    </div>
  );
}

/** A loan-term segment of the documents (`term-le-60`, `term-61-120`, `term-121-240`, `term-gt-240`) in words. */
export function segmentLabel(id: string): { en: string; es: string } {
  const m = /^term-(le|gt)-(\d+)$/.exec(id);
  if (m) return m[1] === 'le'
    ? { en: `Term up to ${m[2]} months`, es: `Plazo hasta ${m[2]} meses` }
    : { en: `Term over ${m[2]} months`, es: `Plazo sobre ${m[2]} meses` };
  const r = /^term-(\d+)-(\d+)$/.exec(id);
  if (r) return { en: `Term ${r[1]} to ${r[2]} months`, es: `Plazo de ${r[1]} a ${r[2]} meses` };
  return { en: id, es: id };
}
