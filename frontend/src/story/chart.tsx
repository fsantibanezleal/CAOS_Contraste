// The small drawing kit of the story views: linear scales, paths, date ticks and the one day control every dated view shares.
// The views are SVGs the product owns (ADR-0082 rule 1: the domain's own diagram), sized from their measured box.
import { formatNumber, useLinkedView, useShellLang } from '@fasl-work/caos-app-shell';
import type { ChangeEvent } from 'react';
import type { Lang } from './text';

export interface Size {
  width: number;
  height: number;
}

export const lin = (d0: number, d1: number, r0: number, r1: number) => (v: number): number => r0 + ((v - d0) / (d1 - d0 || 1)) * (r1 - r0);
const r2 = (v: number): string => String(Math.round(v * 100) / 100);

/** A line over indexes from..to; a null value breaks the line. */
export function linePath(values: readonly (number | null)[], x: (i: number) => number, y: (v: number) => number, from = 0, to = values.length - 1): string {
  let d = '';
  let pen = false;
  for (let i = Math.max(0, from); i <= Math.min(values.length - 1, to); i++) {
    const v = values[i];
    if (v == null || !Number.isFinite(v)) {
      pen = false;
      continue;
    }
    d += `${pen ? 'L' : 'M'}${r2(x(i))},${r2(y(v))}`;
    pen = true;
  }
  return d;
}

/** A step line: the value holds until the next day, as an integer count does. */
export function stepPath(values: readonly number[], x: (i: number) => number, y: (v: number) => number, from = 0, to = values.length - 1): string {
  let d = '';
  for (let i = Math.max(0, from); i <= Math.min(values.length - 1, to); i++) {
    d += i === Math.max(0, from) ? `M${r2(x(i))},${r2(y(values[i]!))}` : `H${r2(x(i))}V${r2(y(values[i]!))}`;
  }
  return d;
}

/** The area between two series. */
export function bandPath(lo: readonly number[], hi: readonly number[], x: (i: number) => number, y: (v: number) => number): string {
  const n = Math.min(lo.length, hi.length);
  let d = '';
  for (let i = 0; i < n; i++) d += `${i ? 'L' : 'M'}${r2(x(i))},${r2(y(hi[i]!))}`;
  for (let i = n - 1; i >= 0; i--) d += `L${r2(x(i))},${r2(y(lo[i]!))}`;
  return `${d}Z`;
}

/** About `count` indexes evenly spread over 0..n-1, ends included. */
export function tickIndices(n: number, count: number): number[] {
  if (n <= 1) return [0];
  const out = new Set<number>();
  for (let k = 0; k < count; k++) out.add(Math.round((k * (n - 1)) / (count - 1)));
  return [...out];
}

const monthYear = (iso: string, lang: Lang) => new Intl.DateTimeFormat(lang, { month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${iso}T00:00:00Z`));
const fullDate = (iso: string, lang: Lang) => new Intl.DateTimeFormat(lang, { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${iso}T00:00:00Z`));
export const dayLabel = (iso: string | undefined, lang: Lang): string => (iso ? fullDate(iso, lang) : formatNumber(null, lang));
export const monthLabel = (iso: string | undefined, lang: Lang): string => (iso ? monthYear(iso, lang) : '');

export const pct = (v: number | null | undefined, lang: Lang, decimals = 2): string => formatNumber(v ?? null, lang, { percent: true, decimals });
export const int = (v: number | null | undefined, lang: Lang): string => formatNumber(v ?? null, lang, { decimals: 0 });

/** The text cut to `max` characters with an ellipsis. */
export const fit = (text: string, max: number): string => (text.length <= max ? text : `${text.slice(0, Math.max(1, max - 1)).trimEnd()}…`);

/** The marker of the shared day cursor on a drawing: the gate reads its position against the control's value. */
export const cursorMarker = (index: number) => ({ 'data-linked-cursor-marker': '', 'data-linked-cursor-position': index }) as const;

/**
 * The one day control of the story: a range input over the days of the window, bound to the shared cursor of the linked-view
 * store, so the Basel light, the crisis and the recalibration read the same day and the market node of the flow shows it too.
 */
export function DayScrubber({ dates, index, onChange }: { dates: readonly string[]; index: number; onChange: (i: number) => void }) {
  const lang = useShellLang();
  const scrub = useLinkedView((s) => s.scrub);
  const t = (en: string, es: string) => (lang === 'es' ? es : en);
  const set = (e: ChangeEvent<HTMLInputElement>) => {
    const i = Number(e.currentTarget.value);
    scrub(i);
    onChange(i);
  };
  return (
    <label className="story-scrub" data-caos-plot-control="">
      <span>{t('Day', 'Día')}</span>
      <strong>{dayLabel(dates[index], lang)}</strong>
      <input aria-label={t('Move the shared day', 'Mover el día compartido')} type="range" min={0} max={Math.max(0, dates.length - 1)} step={1} value={index} data-linked-cursor="" onChange={set} />
      <span className="story-scrub-n">
        {int(index + 1, lang)} / {int(dates.length, lang)}
      </span>
    </label>
  );
}

/** The key of a line or a mark in a drawing: a swatch and its words, so a state is never colour alone. */
export function Swatch({ x, y, color, dash, label, size = 11 }: { x: number; y: number; color: string; dash?: string; label: string; size?: number }) {
  return (
    <g>
      <line x1={x} x2={x + 18} y1={y} y2={y} stroke={color} strokeWidth={2.4} strokeDasharray={dash} />
      <text x={x + 23} y={y + 4} fill="var(--color-fg-subtle)" fontSize={size}>
        {label}
      </text>
    </g>
  );
}

/** Pointer position in the viewBox of an SVG whose viewBox is its pixel size. */
export function pointerX(event: { clientX: number; currentTarget: Element }): number {
  const r = event.currentTarget.getBoundingClientRect();
  return event.clientX - r.left;
}
