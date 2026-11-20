// BL-120: the value label of a negative bar. The shell's horizontal BarChart writes a negative bar's label at the bar's far end and,
// when that end lies closer to the axis start than the label is wide, pins the label to the axis start, over the bar (known shell
// defect, entry 45 of conventions/shell-known-defects.md, CAOS_APP_SHELL#233). At 390 px in Spanish the plot is narrow enough that
// the longest negative bar of C14 (-4,286) and C15 (-127,26) printed its light label on the green bar: contrast 1.65:1 (G13).
// The product leaves the label room: every horizontal BarChart of C14 and C15 that can hold a negative value gets a domain with headroom
// on the negative side (`signedRange`). Not a gate threshold, not a hidden label.
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ReactElement } from 'react';
import type { ModelsArtifact, VariantArtifact } from '../lib/contract.types';
import { committedDoc, fixtureData, html, setLang } from './c14/testkit';
import { defaultSel as defaultSel14, type C14Sel } from './c14/selection';
import { defaultSel as defaultSel15, type C15Sel } from './c15/selection';
import { signedRange, SIGNED_HEADROOM } from './barRange';
import { EveByShockView } from './c14/ShockViews';
import { CapsView, ChangesView, ReplicatingView, WithWithoutView } from './c14/BehaviouralViews';
import { DynamicNiiView, EarEvarView, GapView } from './c14/NiiViews';
import { DynamicLegView, EarEvarLegView, EveByLegView, PositionsView } from './c15/LegViews';
import { IndexationView, NiiView } from './c15/RateViews';
import { FloorsView, ThresholdsView } from './c15/FloorViews';

type Captured = { view: string; orientation?: string; data: Array<{ id: string; value: number | null | undefined; span?: unknown }>; axis: { range?: [number, number] } };
const captured: Captured[] = [];
let current = '';

// the real chart is replaced by a recorder: the shell draws nothing on the server (no width), so the props are the evidence
vi.mock('@fasl-work/caos-app-shell', async (importOriginal) => {
  const real = await importOriginal<typeof import('@fasl-work/caos-app-shell')>();
  return {
    ...real,
    BarChart: (p: Captured) => {
      captured.push({ view: current, orientation: p.orientation ?? 'horizontal', data: p.data, axis: p.axis });
      return null;
    },
  };
});

describe('signedRange', () => {
  it('gives the negative side headroom for the value label and keeps the positive side as the data have it', () => {
    const r = signedRange([3.058, -4.286, 3.073, -2.663]);
    expect(r).toBeDefined();
    expect(r![0]).toBeCloseTo(-4.286 * (1 + SIGNED_HEADROOM), 10);
    expect(r![1]).toBe(3.073);
  });

  it('has no opinion on data with no negative value, with no finite value, or empty', () => {
    expect(signedRange([1, 2, 3])).toBeUndefined();
    expect(signedRange([0, 0])).toBeUndefined();
    expect(signedRange([null, undefined, Number.NaN, Number.POSITIVE_INFINITY])).toBeUndefined();
    expect(signedRange([])).toBeUndefined();
  });

  it('skips a missing value and uses zero as the top of an all-negative set', () => {
    const r = signedRange([null, -2, -1]);
    expect(r).toEqual([-2 * (1 + SIGNED_HEADROOM), 0]);
  });
});

const models14 = committedDoc<ModelsArtifact>('C14', 'models-svb-2021-2022');
const models15 = committedDoc<ModelsArtifact>('C15', 'models-banco-andino-2026-09');
const sel14 = (name: string): C14Sel => defaultSel14(fixtureData('C14', committedDoc<VariantArtifact>('C14', name), models14, { en: 'IRRBB', es: 'IRRBB' })) as C14Sel;
const sel15 = (name: string): C15Sel => defaultSel15(fixtureData('C15', committedDoc<VariantArtifact>('C15', name), models15, { en: 'IRRBB', es: 'IRRBB' })) as C15Sel;

const VIEWS14: Array<[string, (p: { sel: C14Sel | null }) => ReactElement]> = [
  ['C14 Delta EVE by shock', EveByShockView], ['C14 With and without', WithWithoutView], ['C14 Replicating', ReplicatingView], ['C14 Caps', CapsView],
  ['C14 Changes', ChangesView], ['C14 Gap', GapView], ['C14 Dynamic NII', DynamicNiiView], ['C14 EaR and EVaR', EarEvarView],
];
const VIEWS15: Array<[string, (p: { sel: C15Sel | null }) => ReactElement]> = [
  ['C15 Delta EVE by leg', EveByLegView], ['C15 Positions', PositionsView], ['C15 Dynamic', DynamicLegView], ['C15 EaR and EVaR', EarEvarLegView],
  ['C15 Delta NII', NiiView], ['C15 Indexation', IndexationView], ['C15 Floors', FloorsView], ['C15 Thresholds', ThresholdsView],
];

function render(name: string, View: (p: { sel: never }) => ReactElement, sel: unknown) {
  current = name;
  html(<View sel={sel as never} />);
}

describe('every BarChart of C14 and C15 that holds a negative value leaves its label room (BL-120)', () => {
  afterEach(() => {
    setLang('en');
    captured.length = 0;
  });

  const check = (rows: Captured[]) => {
    let signed = 0;
    for (const c of rows) {
      const v = c.data.map((d) => d.value).filter((x): x is number => typeof x === 'number' && Number.isFinite(x));
      const lo = Math.min(0, ...v);
      if (c.orientation !== 'horizontal' || lo >= 0 || c.data.some((d) => d.span !== undefined)) continue;
      signed += 1;
      expect(c.axis.range, `${c.view}: a bar below zero with no headroom for its value label`).toBeDefined();
      expect(c.axis.range![0], `${c.view}: the negative side`).toBeLessThanOrEqual(lo * (1 + SIGNED_HEADROOM) + 1e-9);
      expect(c.axis.range![1], `${c.view}: the positive side`).toBeGreaterThanOrEqual(Math.max(0, ...v));
    }
    return signed;
  };

  it('C14, on every committed valuation date', () => {
    let signed = 0;
    for (const name of ['vd-2021-q4', 'vd-2022-q2', 'vd-2022-q4']) {
      for (const [view, View] of VIEWS14) render(`${view} ${name}`, View as never, sel14(name));
    }
    expect(captured.length).toBeGreaterThan(0);
    signed += check(captured);
    expect(signed, 'the committed data hold no negative bar: the test proves nothing').toBeGreaterThan(0);
  });

  it('C15, on every committed variant', () => {
    let signed = 0;
    for (const name of ['clp-steepener', 'cpi-surprise', 'floors-active', 'long-uf', 'offset-on-off', 'short-uf']) {
      for (const [view, View] of VIEWS15) render(`${view} ${name}`, View as never, sel15(name));
    }
    expect(captured.length).toBeGreaterThan(0);
    signed += check(captured);
    expect(signed, 'the committed data hold no negative bar: the test proves nothing').toBeGreaterThan(0);
  });
});

