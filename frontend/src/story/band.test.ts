// The story's header band (shell 0.24.0, known defect 60): the stage reserves the band the callout cards measure
// (`SceneCallouts` `onLayout`, the CSS property `--caos-callout-band`), never a band computed from the nominal card sizes. Contraste
// reserved a fixed 86 px (130 px on a phone) for the shell 0.23 cards; 0.24.0's cards carry their state word and are taller.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { FIRST_FRAME_BAND, PHONE_DRAWING_FLOOR, bandOf, storyStageFloor } from './band';

const source = (rel: string) => readFileSync(new URL(rel, import.meta.url), 'utf8');

describe('the header band of the story stage', () => {
  it('holds the nominal band only until the cards are measured, then follows the measured band', () => {
    expect(bandOf(0, 1000)).toBe(FIRST_FRAME_BAND.wide);
    expect(bandOf(0, 400)).toBe(FIRST_FRAME_BAND.phone);
    expect(bandOf(undefined, 1000)).toBe(FIRST_FRAME_BAND.wide);
    expect(bandOf(Number.NaN, 400)).toBe(FIRST_FRAME_BAND.phone);
    expect(bandOf(142.2, 1000)).toBe(143);
    expect(bandOf(142.2, 400)).toBe(143);
    expect(bandOf(60, 1000)).toBe(60);
  });

  it('sets the phone stage floor from the band within the shell bounds (620 to 900 px)', () => {
    expect(storyStageFloor(0)).toBe(620);
    expect(storyStageFloor(100)).toBe(620);
    expect(storyStageFloor(150)).toBe(Math.round(150 + PHONE_DRAWING_FLOOR));
    expect(storyStageFloor(500)).toBe(900);
    expect(storyStageFloor(Number.NaN)).toBe(620);
  });

  it('adversarial: the stage reads the measured band and keeps no fixed band of its own', () => {
    const story = source('../pages/Story.tsx');
    const css = source('../pages/story.css');
    // what a stage that reserves a fixed band looks like: findings by name
    const fixedBand = (tsx: string, styles: string): string[] => [
      ...(tsx.includes('onLayout') ? [] : ['the callouts report no band (onLayout)']),
      ...(tsx.includes('bandOf(') ? [] : ['the band is not read through bandOf']),
      ...(tsx.includes('storyStageFloor(') ? [] : ['the phone stage floor is not set from the band']),
      ...(/const BAND\s*=/.test(tsx) ? ['a band function of the stage'] : []),
      ...(/mobileStageMinHeight=\{620\}/.test(tsx) ? ['a literal phone stage floor'] : []),
      ...(/padding-top:\s*\d+px/.test(styles) ? ['a bare pixel padding of the drawing'] : []),
      ...(/padding-top:\s*var\(--story-band,\s*\d+px\)/.test(styles) ? [] : ['the drawing is not padded by the band property']),
    ];
    expect(fixedBand(story, css)).toEqual([]);
    expect(fixedBand(story.replaceAll('onLayout', 'onResize'), css)).toEqual(['the callouts report no band (onLayout)']);
    expect(fixedBand(`${story} const BAND = (w: number) => (w < 760 ? 130 : 86);`, css)).toEqual(['a band function of the stage']);
    expect(fixedBand(story.replace('mobileStageMinHeight={storyStageFloor(stageBand)}', 'mobileStageMinHeight={620}'), css)).toEqual(
      ['the phone stage floor is not set from the band', 'a literal phone stage floor'],
    );
    expect(fixedBand(story, css.replace('padding-top: var(--story-band, 86px)', 'padding-top: 86px'))).toEqual(
      ['a bare pixel padding of the drawing', 'the drawing is not padded by the band property'],
    );
  });
});
