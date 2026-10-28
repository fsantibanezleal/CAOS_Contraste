// The measured layout of the instrument (U16-F12a, the R4 ruling 8): what CSS alone cannot know, measured in the browser
// on every layout change, never assumed from a row count or a font.
//
// 1. A scroll box that has content past its edge says so. Every box of the app that scrolls (the stacks' table boxes, the
//    scroll boxes, the panel grids) carries `data-more-y` while content lies below its visible bottom, with the count of
//    table rows not wholly in view in `data-more-text` ("3 more rows below"), which contraste.css draws as a band over the
//    box's last visible line: a fade over content and the count, wherever the box ends (on a row boundary too, where the
//    earlier fade fell on a blank gap and showed nothing: R4 c06 M1, c19 M1, c20 M1). `data-more-x` marks content past
//    the right edge, which fades at every width (R4 c09 M1: the gap columns cut at 1280 with no cue). A row counts as below
//    when its text line (its middle) lies under the line where the band's fade reaches half its opacity: a whole row in the
//    band's clear top is read, and was counted (R5 c06 B1, c22 m2, c01 n3, c05 n5: "20 more rows below" under 7 of 26 rows).
//    The band sits at the box's real bottom, so no line shows under it (R5 c27 n5).
// 2. Every drawing's least height is on its plot, not on the box that also holds its key, its axis titles and its
//    readout (R4 c01 M1, M2, c11 M1, c23 M1, c26 M1, c27 M1). A plot (`.caos-chart-plot` of a filling chart, `.caos-bars`
//    of a filling bar chart) keeps the floor its nearest `data-plot-floor` holder declares, or DEFAULT_PLOT_FLOOR; a bar
//    chart also keeps the height its bars need, so it never scrolls inside itself. A plot under its floor grows the nearest
//    box of the app that sizes it (a floor holder, a stack's drawing box) by what the key, the titles and the readout take;
//    in a stack the drawing box leaves the tables under it at least their header and cue, which then scroll. A plot with no
//    such box grows its card's body (R5 c05 M1, M3: no C04 drawing had one, and the long notes took the plots' height); in a
//    card of a fixed height the note keeps its first lines and scrolls with the cue. The layout probe (layout-probe.mjs)
//    measures the result.
// Nothing here draws, and nothing restyles a shell class: the cues are attributes on the app's own boxes and the floors
// inline heights on them.
import { useEffect } from 'react';

/** The boxes of the app that scroll inside a card. A view may mark another one with `data-scroll-box`. The C21 evidence card
 * scrolls as a whole and was not listed, so it hid a drawing and a table with no cue (R5 c27 M1); a filling card's note scrolls
 * when its card has no room for it (the shell caps it at 35 %; C04 lets it give way to its drawing's floor, R5 c05 M1). */
export const SCROLL_BOXES =
  '.ct-stack-table, .ct-stack-rest, .ct-stack-fill, .ct-scroll, .ct-fade-scroll, .ct-panels-fill, .ct-c20-bars, .ct-stack[data-block="finding-evidence"], .caos-plot.fill > .caos-plot-note, [data-scroll-box]';
/** The least height of a plot that declares none: the axis of ticks under it and about four ticks of a value axis. */
export const DEFAULT_PLOT_FLOOR = '9rem';
/** The plots of filling drawings (a fixed-height drawing has the height it asked for). */
export const PLOTS = '.caos-chart.fill > .caos-chart-plot, .caos-bars-host.fill > .caos-bars';
/** The app's boxes that size a drawing, nearest first; a plot with none is sized by its card's body (`sizerOf`). */
const SIZERS = '[data-plot-floor], .ct-stack-chart, .ct-stack-fixed';
/** What a card of a fixed height leaves its note when its body grows for a plot's floor: about two lines over the cue. */
export const NOTE_KEEP = '4.6rem';
/** What a part of a column keeps when the card of another part grows for its plot's floor: its title, a table header, a row or two
 * and the cue, which then scroll. */
const PART_KEEP = '10rem';
/** The height of the cue's band over a box's last visible line (contraste.css, `[data-more-y]::after`). */
export const CUE_BAND = '2.3rem';
/** Where the band's fade reaches half its opacity, as a share of its height from its top: the gradient runs from transparent to
 * the surface over the band's top 55 % (contraste.css), so a text line under this line is more hidden than shown. */
export const CUE_HALF = 0.275;
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

/** Whether a row of a box whose visible bottom is `visibleBottom` (a page coordinate) is not read above the cue: its text line,
 * the row's middle, lies under the line where the band of `band` px reaches half its opacity. A row in the band's clear top is
 * read (R5 c06 B1: such a row was counted, "20 more rows below" under 7 of 26 rows). */
export function rowHidden(r: { top: number; bottom: number; height: number }, visibleBottom: number, band: number): boolean {
  return r.height > 0 && (r.top + r.bottom) / 2 > visibleBottom - band + CUE_HALF * band;
}

/** A row's text line: the union of its text's glyph boxes, so a row of two lines or of a tall cell is judged by its text, not its
 * padded box; the row's box where it has no text (or outside a browser). */
function textLine(tr: Element): { top: number; bottom: number; height: number } {
  const r = tr.getBoundingClientRect();
  if (typeof document === 'undefined' || typeof document.createTreeWalker !== 'function') return r;
  let top = Number.POSITIVE_INFINITY;
  let bottom = Number.NEGATIVE_INFINITY;
  const walker = document.createTreeWalker(tr, NodeFilter.SHOW_TEXT);
  const range = document.createRange();
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    if (!n.textContent?.trim() || n.parentElement?.closest('.sr-only')) continue;
    range.selectNodeContents(n);
    for (const g of range.getClientRects()) {
      if (g.height <= 0) continue;
      top = Math.min(top, g.top);
      bottom = Math.max(bottom, g.bottom);
    }
  }
  return top === Number.POSITIVE_INFINITY ? r : { top, bottom, height: bottom - top };
}

/** The body rows of the visible tables inside a box that a reader cannot read above its cue (`rowHidden`, on the row's text line). */
export function rowsBelow(box: Pick<Element, 'querySelectorAll'>, visibleBottom: number, band: number): number {
  let n = 0;
  for (const tr of box.querySelectorAll('tbody > tr')) {
    // a drawing's screen-reader table is not a row a reader scrolls to
    if (tr.closest('.sr-only')) continue;
    const r = tr.getBoundingClientRect();
    if (r.height <= 0 || r.bottom <= visibleBottom - band) continue;
    // a row wholly under the box's edge is hidden; a row across the band is judged by its text
    if (r.top >= visibleBottom || rowHidden(textLine(tr), visibleBottom, band)) n += 1;
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
  // the band of the cue covers the box's last visible line at its real bottom: a row under its half-opacity line counts as below
  const band = toPx(CUE_BAND, parseFloat(getComputedStyle(document.documentElement).fontSize) || 16);
  const text = moreY ? cueText(rowsBelow(box, box.getBoundingClientRect().top + box.clientTop + box.clientHeight, band), lang) : null;
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

/** The box that sizes a plot: its nearest floor holder or stack drawing box, else the body of its filling card (R5 c05 M1, M3: a
 * plot with no holder was never floored, and C04's long notes took its height); null for a plot outside a filling card. */
export function sizerOf(plot: Pick<Element, 'closest'>): HTMLElement | null {
  return plot.closest<HTMLElement>(SIZERS) ?? plot.closest<HTMLElement>('.caos-plot.fill > .caos-plot-body');
}

/** The most a card body grown for a plot may take in a card of a fixed height: the card's inner height less its other parts and
 * the first lines of its note (`NOTE_KEEP`, or the note's whole height when shorter); unbounded in a card that flows (a phone). */
export function bodyRoom(card: { inner: number; others: number[]; note: number | null; flows: boolean }, remPx: number): number {
  if (card.flows) return Number.POSITIVE_INFINITY;
  const keep = card.note === null ? 0 : Math.min(card.note, toPx(NOTE_KEEP, remPx));
  return card.inner - card.others.reduce((s, h) => s + h, 0) - keep;
}

// the height a view gave each box a pass grew, and the plot it was grown for: a box that later holds another drawing (React
// keeps the element across sub-views) starts again from the view's own height
const grown = new WeakMap<HTMLElement, { min: string; plot: Element }>();

/** One pass over the plots: grows the box that sizes each plot under its floor. True if anything changed. */
export function floorPlots(remPx: number): boolean {
  let changed = false;
  for (const el of document.querySelectorAll<HTMLElement>('[data-plot-grown]')) {
    const g = grown.get(el);
    // a card body may hold several plots: it keeps its height while the plot it grew for is still in it
    if (g && g.plot.isConnected && el.contains(g.plot)) continue;
    if (g) el.style.minHeight = g.min;
    grown.delete(el);
    el.removeAttribute('data-plot-grown');
    changed = true;
  }
  for (const plot of document.querySelectorAll<HTMLElement>(PLOTS)) {
    if (plot.closest('.caos-wb-rail, .ct-c20-bars') || plot.clientWidth === 0) continue;
    const need = plotNeed(plot, remPx);
    if (need - plot.clientHeight <= 1) continue;
    const sizer = sizerOf(plot);
    if (!sizer) continue;
    // the sizer's own height less the plot's is what its key, titles and readout take; the plot gets its floor on top
    let want = Math.ceil(sizer.getBoundingClientRect().height - plot.clientHeight + need);
    const card = sizer.classList.contains('caos-plot-body') ? sizer.parentElement : null;
    if (card) {
      // a card body: its card keeps its title and the first lines of its note, which then scrolls with its cue
      const note = card.querySelector<HTMLElement>(':scope > .caos-plot-note');
      const cs = getComputedStyle(card);
      const gaps = (parseFloat(cs.rowGap) || 0) * Math.max(0, card.children.length - 1);
      const inner = card.clientHeight - (parseFloat(cs.paddingTop) || 0) - (parseFloat(cs.paddingBottom) || 0) - gaps;
      const others = [...card.children].filter((c) => c !== sizer && c !== note).map((c) => c.getBoundingClientRect().height);
      // a card that does not take the panel's height (a phone, where the shell gives it `flex: none` and the document scrolls) flows
      const flows = cs.flexGrow === '0';
      const room = Math.floor(bodyRoom({ inner, others, note: note ? note.scrollHeight : null, flows }, remPx));
      // a card that shares its column with another (a part of a column, C04's chart over its table) and has no room for the floor
      // takes it from the other parts, which keep their title, header and cue and scroll (R5 c05 M3: markov's bias plot of 50 px)
      const part = card.parentElement;
      if (want > room && part && part.classList.contains('ct-part') && part.parentElement && !flows) {
        const spare = [...part.parentElement.children]
          .filter((c) => c !== part && c.classList.contains('ct-part'))
          .reduce((s, c) => s + Math.max(0, c.getBoundingClientRect().height - toPx(PART_KEEP, remPx)), 0);
        const grow = Math.floor(Math.min(want - room, spare));
        if (grow > 1) {
          if (!grown.has(part)) grown.set(part, { min: part.style.minHeight, plot });
          part.setAttribute('data-plot-grown', '');
          part.style.minHeight = `${Math.ceil(part.getBoundingClientRect().height) + grow}px`;
          changed = true;
        }
      }
      want = Math.min(want, room);
    }
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
