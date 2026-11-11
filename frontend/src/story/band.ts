// The header band of the story stage (shell 0.24.0, known defect 60). The callout cards of `SceneCallouts` (`placement="header"`)
// are laid out on their measured heights, and the layer reports the band they take through `onLayout` (and the CSS property
// `--caos-callout-band`). The stage pads its drawing by that band, so no card covers a subject. Until the cards are measured
// (the first frame) the stage holds the nominal band the 0.23 cards took.
import { useLayoutEffect } from 'react';

/** The band held for the first frame, before the cards are measured: wide stages, and a phone stage under 760 px. */
export const FIRST_FRAME_BAND = { wide: 86, phone: 130 } as const;

/** The height the drawing keeps on a phone under the band: the views' controls and labels fit in it. */
export const PHONE_DRAWING_FLOOR = 490;

/** The band the stage reserves: the measured one (whole pixels, rounded up), or the nominal band of the first frame. */
export function bandOf(measured: number | undefined, stageWidth: number): number {
  if (typeof measured === 'number' && Number.isFinite(measured) && measured > 0) return Math.ceil(measured);
  return stageWidth < 760 ? FIRST_FRAME_BAND.phone : FIRST_FRAME_BAND.wide;
}

/** The phone stage floor: the band plus the drawing's floor, within the shell's bounds (620 to 900 px; 620 before the band is measured). */
export function storyStageFloor(band: number): number {
  if (!Number.isFinite(band) || band <= 0) return 620;
  return Math.min(900, Math.max(620, Math.round(band + PHONE_DRAWING_FLOOR)));
}

/**
 * How long the measured band must hold before the stage is settled. When the cards are measured the band changes (130 to 146 px on a
 * phone at /story/recalibrate) and the stage grows to its new floor, and for about one frame the callout layer still carries the
 * anchors of the band before: a card then sits on its own anchor (the live gate's G21 at 390 x 844, 2026-11-10; the shell's layer
 * reports bands from transient layouts too, known defect 65). Until the band has held this long the stage declares itself stale
 * (`data-stale="1"`, the shell's readiness contract), so nothing reads a layout in between; the reader sees the stage as it is.
 */
export const BAND_HOLD_MS = 200;

/**
 * Marks `el` stale (`data-stale="1"`) from the commit that changes the measured band until it has held for `ms`, without a render of
 * its own: the stage's drawing is rebuilt on every render, so the marker is set on the element in a layout effect (before the frame
 * is painted) and cleared by a timer.
 */
export function useStaleUntilBandHolds(el: { current: HTMLElement | null }, measured: number, ms: number): void {
  useLayoutEffect(() => {
    const node = el.current;
    if (!node) return undefined;
    node.setAttribute('data-stale', '1');
    if (!(Number.isFinite(measured) && measured > 0)) return undefined;
    const timer = setTimeout(() => node.removeAttribute('data-stale'), ms);
    return () => clearTimeout(timer);
  }, [el, measured, ms]);
}
