// The measured layout of the instrument (U16-F12a, the R4 ruling 8): what CSS alone cannot know, measured in the browser
// on every layout change, never assumed from a row count or a font.
//
// 1. A scroll box that has content past its edge says so. Every box of the app that scrolls (the stacks' table boxes, the
//    scroll boxes, the panel grids) carries `data-more-y` while content lies below its visible bottom, with the count of
//    table rows not wholly in view in `data-more-text` ("3 more rows below"), which contraste.css draws as a band over the
//    box's last visible line: a fade over content and the count, wherever the box ends (on a row boundary too, where the
//    earlier fade fell on a blank gap and showed nothing: R4 c06 M1, c19 M1, c20 M1). `data-more-x` marks content past
//    the right edge, which fades at every width (R4 c09 M1: the gap columns cut at 1280 with no cue).
// 2. Every drawing's least height is on its plot, not on the box that also holds its key, its axis titles and its
//    readout (R4 c01 M1, M2, c11 M1, c23 M1, c26 M1, c27 M1). A plot (`.caos-chart-plot` of a filling chart, `.caos-bars`
//    of a filling bar chart) keeps the floor its nearest `data-plot-floor` holder declares, or DEFAULT_PLOT_FLOOR; a bar
//    chart also keeps the height its bars need, so it never scrolls inside itself. A plot under its floor grows the nearest
//    box of the app that sizes it (a floor holder, a stack's drawing box) by what the key, the titles and the readout take;
//    in a stack the drawing box leaves the tables under it at least their header and cue, which then scroll. A plot with no
//    such box is sized by its view's layout, which the layout probe (layout-probe.mjs) measures.
// Nothing here draws, and nothing restyles a shell class: the cues are attributes on the app's own boxes and the floors
// inline heights on them.
import { useEffect } from 'react';

/** The boxes of the app that scroll inside a card. A view may mark another one with `data-scroll-box`. */
export const SCROLL_BOXES = '.ct-stack-table, .ct-stack-rest, .ct-stack-fill, .ct-scroll, .ct-fade-scroll, .ct-panels-fill, .ct-c20-bars, [data-scroll-box]';
/** The least height of a plot that declares none: the axis of ticks under it and about four ticks of a value axis. */
export const DEFAULT_PLOT_FLOOR = '9rem';
/** The plots of filling drawings (a fixed-height drawing has the height it asked for). */
export const PLOTS = '.caos-chart.fill > .caos-chart-plot, .caos-bars-host.fill > .caos-bars';
/** The app's boxes that size a drawing, nearest first. */
const SIZERS = '[data-plot-floor], .ct-stack-chart, .ct-stack-fixed';
/** The height of the cue's band over a box's last visible line (contraste.css, `[data-more-y]::after`). */
export const CUE_BAND = '2.3rem';
/** What a stack's drawing box leaves the tables under it, at least: their header row and the cue under it. */
const TABLE_KEEP = '4.5rem';

/** A length of the code ("14rem", "220px") in pixels; 0 for anything else. */
export function toPx(v: string | null | undefined, remPx: number): number {
  const m = /^\s*(\d+(?:\.\d+)?)(rem|px)\s*$/.exec(v ?? '');
  if (!m) return 0;
  return m[2] === 'rem' ? Number(m[1]) * remPx : Number(m[1]);
}

/** The cue under a box with content below: the count of table rows not wholly in view, or "more below". */
export function cueText(rows: number, lang: 'en' | 'es'): string {
  if (rows <= 0) return lang === 'es' ? 'Hay más abajo: desplace el recuadro' : 'More below: scroll the box';
  if (lang === 'es') return rows === 1 ? '1 fila más abajo: desplace el recuadro' : `${rows} filas más abajo: desplace el recuadro`;
  return rows === 1 ? '1 more row below: scroll the box' : `${rows} more rows below: scroll the box`;
}

/** The body rows of the visible tables inside a box whose bottom lies below `bottom` (a page coordinate). */
export function rowsBelow(box: Element, bottom: number): number {
  let n = 0;
  for (const tr of box.querySelectorAll('tbody > tr')) {
    // a drawing's screen-reader table is not a row a reader scrolls to
    if (tr.closest('.sr-only')) continue;
    const r = tr.getBoundingClientRect();
    if (r.height > 0 && r.bottom > bottom + 1) n += 1;
  }
  return n;
}

const scrolls = (v: string) => v === 'auto' || v === 'scroll';
const langOf = (): 'en' | 'es' => ((document.documentElement.lang || 'en').toLowerCase().startsWith('es') ? 'es' : 'en');

/** Marks one scroll box: whether content lies below or to the right of what it shows, and the cue text. True if it changed. */
export function markBox(box: HTMLElement, lang: 'en' | 'es'): boolean {
  const cs = getComputedStyle(box);
  const moreY = scrolls(cs.overflowY) && box.clientHeight > 0 && box.scrollHeight - box.clientHeight - box.scrollTop > 2;
  const moreX = scrolls(cs.overflowX) && box.clientWidth > 0 && box.scrollWidth - box.clientWidth - box.scrollLeft > 2;
  // the band of the cue covers the box's last visible line, so a row under it counts as below
  const band = toPx(CUE_BAND, parseFloat(getComputedStyle(document.documentElement).fontSize) || 16);
  const text = moreY ? cueText(rowsBelow(box, box.getBoundingClientRect().top + box.clientTop + box.clientHeight - band), lang) : null;
  let changed = false;
  const set = (name: string, value: string | null) => {
    if (box.getAttribute(name) === value) return;
    changed = true;
    if (value === null) box.removeAttribute(name);
    else box.setAttribute(name, value);
  };
  set('data-more-y', moreY ? '1' : null);
  set('data-more-text', text);
  set('data-more-x', moreX ? '1' : null);
  return changed;
}

/** The height a plot needs: its floor, and for a bar chart the height of its bars. */
export function plotNeed(plot: HTMLElement, remPx: number): number {
  const holder = plot.closest('[data-plot-floor]');
  const floor = toPx(holder ? holder.getAttribute('data-plot-floor') : DEFAULT_PLOT_FLOOR, remPx) || toPx(DEFAULT_PLOT_FLOOR, remPx);
  return plot.classList.contains('caos-bars') ? Math.max(floor, plot.scrollHeight) : floor;
}

// the height a view gave each box a pass grew, and the plot it was grown for: a box that later holds another drawing (React
// keeps the element across sub-views) starts again from the view's own height
const grown = new WeakMap<HTMLElement, { min: string; plot: Element }>();

/** One pass over the plots: grows the box that sizes each plot under its floor. True if anything changed. */
export function floorPlots(remPx: number): boolean {
  let changed = false;
  for (const el of document.querySelectorAll<HTMLElement>('[data-plot-grown]')) {
    const g = grown.get(el);
    if (g && g.plot === el.querySelector(PLOTS)) continue;
    if (g) el.style.minHeight = g.min;
    grown.delete(el);
    el.removeAttribute('data-plot-grown');
    changed = true;
  }
  for (const plot of document.querySelectorAll<HTMLElement>(PLOTS)) {
    if (plot.closest('.caos-wb-rail, .ct-c20-bars') || plot.clientWidth === 0) continue;
    const need = plotNeed(plot, remPx);
    if (need - plot.clientHeight <= 1) continue;
    const sizer = plot.closest<HTMLElement>(SIZERS);
    if (!sizer) continue;
    // the sizer's own height less the plot's is what its key, titles and readout take; the plot gets its floor on top
    let want = Math.ceil(sizer.getBoundingClientRect().height - plot.clientHeight + need);
    const stack = sizer.parentElement;
    if (stack && stack.classList.contains('ct-stack') && stack.querySelector(':scope > .ct-stack-table, :scope > .ct-stack-rest, :scope > .ct-stack-fill')) {
      // in a stack the tables under the drawing keep their header and cue (they scroll); what else the stack holds keeps its height
      const others = [...stack.children].filter((c) => c !== sizer && !c.matches('.ct-stack-table, .ct-stack-rest, .ct-stack-fill'));
      const room = stack.clientHeight - others.reduce((s, c) => s + c.getBoundingClientRect().height, 0) - toPx(TABLE_KEEP, remPx);
      // a stack that flows (a phone) has the height of what it holds: no room to keep
      if (getComputedStyle(stack).height !== 'auto' && stack.scrollHeight <= stack.clientHeight + 1) want = Math.min(want, Math.floor(room));
    }
    if (want <= toPx(sizer.style.minHeight, remPx) + 1 || want <= sizer.getBoundingClientRect().height + 1) continue;
    if (!grown.has(sizer)) grown.set(sizer, { min: sizer.style.minHeight, plot });
    sizer.setAttribute('data-plot-grown', '');
    sizer.style.minHeight = `${want}px`;
    changed = true;
  }
  return changed;
}

/** One pass over the scroll boxes. */
export function markBoxes(): boolean {
  const lang = langOf();
  let changed = false;
  for (const box of document.querySelectorAll<HTMLElement>(SCROLL_BOXES)) changed = markBox(box, lang) || changed;
  return changed;
}

/**
 * Keeps the cues and the floors measured while the instrument is shown: after every change of the DOM, of a size or of a
 * scroll position, a pass (a few chained passes while one still changes something; a pass that grows a box moves the
 * boxes under it). Mounted once, by the workbench.
 */
export function useMeasuredLayout(): void {
  useEffect(() => {
    if (typeof window === 'undefined' || typeof ResizeObserver === 'undefined' || typeof MutationObserver === 'undefined') return;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let chain = 0;
    const remPx = () => parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
    const sizes = new ResizeObserver(() => schedule(true));
    const watched = new WeakSet<Element>();
    const watch = () => {
      for (const el of document.querySelectorAll(`${SCROLL_BOXES}, ${PLOTS}`)) {
        if (watched.has(el)) continue;
        watched.add(el);
        sizes.observe(el);
      }
    };
    const run = () => {
      timer = null;
      watch();
      const grew = floorPlots(remPx());
      markBoxes();
      if (grew && chain < 8) {
        chain += 1;
        schedule(false);
      }
    };
    function schedule(fresh: boolean) {
      if (fresh) chain = 0;
      if (timer === null) timer = setTimeout(run, 40);
    }
    const dom = new MutationObserver(() => schedule(true));
    dom.observe(document.body, { childList: true, subtree: true });
    // a scroll moves no size: only the cues change, at once
    const onScroll = (e: Event) => {
      const t = e.target;
      if (t instanceof HTMLElement && t.matches(SCROLL_BOXES)) markBox(t, langOf());
    };
    const onResize = () => schedule(true);
    document.addEventListener('scroll', onScroll, true);
    window.addEventListener('resize', onResize);
    schedule(true);
    return () => {
      if (timer !== null) clearTimeout(timer);
      dom.disconnect();
      sizes.disconnect();
      document.removeEventListener('scroll', onScroll, true);
      window.removeEventListener('resize', onResize);
    };
  }, []);
}
