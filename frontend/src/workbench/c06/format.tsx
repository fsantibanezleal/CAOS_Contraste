// What the provisions instruments (C06 and C07) share: the number formats, the "not available, with its reason" cell,
// the text of the four stages and the colour of each stage as a shell token. Nothing here computes a statistic.
import { formatNumber, pick, useShellLang, type BiText, type ShellColorToken } from '@fasl-work/caos-app-shell';

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
      {reason ? <span className="ct-note"> ({reason})</span> : null}
    </span>
  );
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
