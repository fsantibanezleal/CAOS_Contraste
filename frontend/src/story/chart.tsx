// The small drawing kit of the story views: linear scales, paths, date ticks and the one day control every dated view shares.
// The views are SVGs the product owns (ADR-0082 rule 1: the domain's own diagram), sized from their measured box.
import { formatNumber, prefersReducedMotion, runStagedTransition, useLinkedView, useShellLang } from '@fasl-work/caos-app-shell';
import { useEffect, useRef, useState, type ChangeEvent, type PointerEvent, type ReactNode } from 'react';
import type { Lang } from './text';

export interface Size {
  width: number;
  height: number;
}

/** The days a dated view shows, as first and last day indexes (a zoom); the whole window is `fullRange(n)`. */
export type Range = [number, number];
export const fullRange = (n: number): Range => [0, Math.max(0, n - 1)];
export const isFull = (range: Range, n: number): boolean => range[0] <= 0 && range[1] >= n - 1;
/** The narrowest zoom: a range shows at least this many days. */
export const MIN_SPAN = 12;
/** The range with its width scaled (0.5 zooms in, 2 zooms out) around a day, kept inside the window and at least `MIN_SPAN` days wide. */
export function zoomRange(range: Range, n: number, factor: number, centre: number): Range {
  const span = Math.max(MIN_SPAN, Math.min(n - 1, Math.round((range[1] - range[0]) * factor)));
  let a = Math.round(centre - span / 2);
  a = Math.max(0, Math.min(n - 1 - span, a));
  return [a, Math.min(n - 1, a + span)];
}

export const lin = (d0: number, d1: number, r0: number, r1: number) => (v: number): number => r0 + ((v - d0) / (d1 - d0 || 1)) * (r1 - r0);
/** The x scale of a plot showing the days of a range between pixels l and r. */
export const xOfRange = (range: Range, l: number, r: number) => lin(range[0], range[1], l, r);

export const easeInOut = (t: number): number => (t <= 0 ? 0 : t >= 1 ? 1 : t * t * (3 - 2 * t));
/** The series between two others at progress t (eased by the caller); series of different lengths do not mix: the target is returned. */
export function mixSeries(from: readonly number[], to: readonly number[], t: number): number[] {
  if (from.length !== to.length) return [...to];
  return to.map((v, i) => from[i]! + (v - from[i]!) * t);
}

const STAGES = 8;
/**
 * Staged easing of a value toward its target on the shell's `runStagedTransition` (instant under reduced motion): each stage sets the
 * eased fraction of the move, so a change of selection or window is a short eased move, never a cut. The first value is the target
 * itself, so a view that mounts on a value does not animate.
 */
function useStaged<T>(target: T, mix: (from: T, to: T, t: number) => T, same: (a: T, b: T) => boolean, ms: number, enabled = true): T {
  const [shown, setShown] = useState<T>(target);
  const shownRef = useRef<T>(target);
  const armed = useRef(false);
  shownRef.current = shown;
  useEffect(() => {
    if (!enabled || !armed.current) {
      // nothing is loaded yet, or this is the first loaded value: it is taken as it is, so a value that arrives with the data does not
      // count up from the placeholder it replaces
      armed.current = enabled;
      if (!same(shownRef.current, target)) setShown(target);
      return undefined;
    }
    if (same(shownRef.current, target)) return undefined;
    const from = shownRef.current;
    const ctl = new AbortController();
    const reduced = prefersReducedMotion();
    const stages = Array.from({ length: reduced ? 1 : STAGES }, (_, k) => {
      const t = reduced ? 1 : easeInOut((k + 1) / STAGES);
      return { run: () => setShown(t >= 1 ? target : mix(from, target, t)), durationMs: reduced ? 0 : Math.round(ms / STAGES) };
    });
    void runStagedTransition(stages, { signal: ctl.signal, reducedMotion: reduced });
    return () => ctl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, enabled]);
  return enabled ? shown : target;
}
const sameSeries = (a: readonly number[], b: readonly number[]): boolean => a === b || (a.length === b.length && a.every((v, i) => v === b[i]));
/** A series that eases to a new one of the same length (the path of another model or window). */
export const useEasedSeries = (target: readonly number[], ms = 320): readonly number[] => useStaged<readonly number[]>(target, (a, b, t) => mixSeries(a, b, t), sameSeries, ms);
/** A count that eases to a new one, shown as a whole number. */
export const useEasedCount = (target: number, enabled = true, ms = 320): number => Math.round(useStaged<number>(target, (a, b, t) => a + (b - a) * t, (a, b) => a === b, ms, enabled));

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
/** About `count` day indexes evenly spread over a range, ends included. */
export const tickIndicesIn = (range: Range, count: number): number[] => tickIndices(range[1] - range[0] + 1, count).map((i) => i + range[0]);

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
 * A dated view passes its zoom (`range`, `onRange`) and the control carries the buttons of the zoom.
 */
export function DayScrubber({ dates, index, onChange, range, onRange }: { dates: readonly string[]; index: number; onChange: (i: number) => void; range?: Range; onRange?: (r: Range | null) => void }) {
  const lang = useShellLang();
  const scrub = useLinkedView((s) => s.scrub);
  const t = (en: string, es: string) => (lang === 'es' ? es : en);
  const set = (e: ChangeEvent<HTMLInputElement>) => {
    const i = Number(e.currentTarget.value);
    scrub(i);
    onChange(i);
  };
  return (
    <div className="story-scrub-row">
      <label className="story-scrub" data-caos-plot-control="">
        <span>{t('Day', 'Día')}</span>
        <strong>{dayLabel(dates[index], lang)}</strong>
        <input aria-label={t('Move the shared day', 'Mover el día compartido')} type="range" min={0} max={Math.max(0, dates.length - 1)} step={1} value={index} data-linked-cursor="" onChange={set} />
        <span className="story-scrub-n">
          {int(index + 1, lang)} / {int(dates.length, lang)}
        </span>
      </label>
      {range && onRange && <ZoomButtons n={dates.length} range={range} centre={index} onRange={onRange} />}
    </div>
  );
}

/** Zoom in, out and back to the whole window: the keyboard route to the drag on the plot (rubric section 2, Tier A). */
export function ZoomButtons({ n, range, centre, onRange }: { n: number; range: Range; centre: number; onRange: (r: Range | null) => void }) {
  const lang = useShellLang();
  const t = (en: string, es: string) => (lang === 'es' ? es : en);
  const whole = isFull(range, n);
  return (
    <span className="story-zoom" role="group" aria-label={t('Zoom the days shown', 'Acercar los días mostrados')} data-zoom={whole ? 'full' : `${range[0]}-${range[1]}`}>
      <button type="button" onClick={() => onRange(zoomRange(range, n, 0.5, centre))} disabled={range[1] - range[0] <= MIN_SPAN} aria-label={t('Zoom in on the shared day', 'Acercar sobre el día compartido')} title={t('Zoom in', 'Acercar')}>
        +
      </button>
      <button type="button" onClick={() => onRange(zoomRange(range, n, 2, centre))} disabled={whole} aria-label={t('Zoom out', 'Alejar')} title={t('Zoom out', 'Alejar')}>
        &minus;
      </button>
      <button type="button" onClick={() => onRange(null)} disabled={whole} aria-label={t('Show the whole window', 'Mostrar toda la ventana')} title={t('Whole window', 'Toda la ventana')}>
        {t('All', 'Todo')}
      </button>
    </span>
  );
}

/**
 * The drag-to-zoom (brush) of a dated plot. A press-drag over the plot rectangle selects days and the release zooms to them; a plain
 * move still scrubs the shared day through `hover`. The brush rectangle comes back in plot pixels for the view to draw.
 */
export function useBrush(opts: { l: number; r: number; range: Range; n: number; onRange?: (r: Range | null) => void; hover: (e: PointerEvent<SVGRectElement>) => void }) {
  const { l, r, range, n, onRange, hover } = opts;
  const [drag, setDrag] = useState<{ a: number; b: number } | null>(null);
  const ix = (px: number): number => Math.max(0, Math.min(n - 1, Math.round(range[0] + ((px - l) / Math.max(1, r - l)) * (range[1] - range[0]))));
  const at = (e: PointerEvent<SVGRectElement>): number => Math.max(l, Math.min(r, pointerX(e)));
  const handlers = {
    onPointerDown: (e: PointerEvent<SVGRectElement>) => {
      if (!onRange || e.button !== 0) return;
      try {
        e.currentTarget.setPointerCapture(e.pointerId);
      } catch {
        /* a synthetic pointer has nothing to capture */
      }
      setDrag({ a: at(e), b: at(e) });
    },
    onPointerMove: (e: PointerEvent<SVGRectElement>) => {
      if (drag) setDrag({ a: drag.a, b: at(e) });
      else hover(e);
    },
    onPointerUp: (e: PointerEvent<SVGRectElement>) => {
      if (!drag) return;
      const a = ix(Math.min(drag.a, at(e)));
      const b = ix(Math.max(drag.a, at(e)));
      setDrag(null);
      if (Math.abs(at(e) - drag.a) >= 8 && b - a >= 2) onRange?.([a, Math.min(n - 1, Math.max(b, a + MIN_SPAN))]);
      else hover(e);
    },
    onPointerCancel: () => setDrag(null),
  };
  return { handlers, brush: drag ? ([Math.min(drag.a, drag.b), Math.max(drag.a, drag.b)] as [number, number]) : null };
}

/** The data of a drawing as a table for a screen reader (rubric section 8, the data-table fallback): visually hidden, in reading order. */
export function SrTable({ id, caption, head, rows }: { id: string; caption: string; head: readonly string[]; rows: readonly (readonly ReactNode[])[] }) {
  return (
    <table className="story-sr" data-data-table={id}>
      <caption>{caption}</caption>
      <thead>
        <tr>
          {head.map((h) => (
            <th key={h} scope="col">
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i}>
            {row.map((c, j) =>
              j === 0 ? (
                <th key={j} scope="row">
                  {c}
                </th>
              ) : (
                <td key={j}>{c}</td>
              ),
            )}
          </tr>
        ))}
      </tbody>
    </table>
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

export interface LegendItem {
  kind: 'line' | 'dash' | 'band' | 'mark';
  color: string;
  label: string;
}
/**
 * The key of a drawing in one line that stays inside it: each item is a swatch and its words, laid out left to right by the width
 * of the words. The caller passes the short words on a phone, so no key is dropped there; an item that would not fit is the last
 * thing left out, never the first.
 */
export function Legend({ items, x, y, maxWidth, fontSize = 11 }: { items: readonly LegendItem[]; x: number; y: number; maxWidth: number; fontSize?: number }) {
  let cursor = 0;
  const gap = fontSize * 1.1;
  return (
    <g transform={`translate(${x},${y})`} fontSize={fontSize} data-legend="">
      {items.map((it) => {
        const w = fontSize * 1.9 + it.label.length * fontSize * 0.56;
        const at = cursor;
        cursor += w + gap;
        if (at + w > maxWidth) return null;
        return (
          <g key={it.label} transform={`translate(${at},0)`}>
            {it.kind === 'band' ? (
              <rect x={0} y={-5} width={fontSize * 1.4} height={9} fill={it.color} fillOpacity={0.12} stroke={it.color} strokeOpacity={0.4} />
            ) : it.kind === 'mark' ? (
              <path transform={`translate(${fontSize * 0.7},0)`} d="M0,-5 L5,0 L0,5 L-5,0 Z" fill={it.color} />
            ) : (
              <line x1={0} x2={fontSize * 1.4} y1={0} y2={0} stroke={it.color} strokeWidth={2.4} strokeDasharray={it.kind === 'dash' ? '5 3' : undefined} />
            )}
            <text x={fontSize * 1.7} y={4} fill="var(--color-fg-subtle)">
              {it.label}
            </text>
          </g>
        );
      })}
    </g>
  );
}

/** Pointer position in the viewBox of an SVG whose viewBox is its pixel size. */
export function pointerX(event: { clientX: number; currentTarget: Element }): number {
  const r = event.currentTarget.getBoundingClientRect();
  return event.clientX - r.left;
}
