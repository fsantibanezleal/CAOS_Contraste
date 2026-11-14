// The header band of the story stage (shell 0.24.0, known defect 60). The callout cards of `SceneCallouts` (`placement="header"`)
// are laid out on their measured heights, and the layer reports the band they take through `onLayout` (and the CSS property
// `--caos-callout-band`). The stage pads its drawing by that band, so no card covers a subject. Until the cards are measured
// (the first frame) the stage holds the nominal band the 0.23 cards took.

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
