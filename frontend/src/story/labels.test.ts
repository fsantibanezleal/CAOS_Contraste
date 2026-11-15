// The story's day and count labels are built once per language, not once per call: the hidden data table of the Basel light formats
// every day of the window, and building a formatter per day cost about 150 ms of the step change into the light (the live gate's G21
// frame rate at /story/inventory, 2026-11-10). The labels are the same text as before.
import { formatNumber } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { dayLabel, int, monthLabel } from './chart';

const fresh = (iso: string, lang: 'en' | 'es', options: Intl.DateTimeFormatOptions) =>
  new Intl.DateTimeFormat(lang, { ...options, timeZone: 'UTC' }).format(new Date(`${iso}T00:00:00Z`));

describe('the story labels', () => {
  afterEach(() => vi.restoreAllMocks());

  it('read the same as a formatter built for the call, in both languages', () => {
    for (const lang of ['en', 'es'] as const) {
      for (const iso of ['2008-10-15', '2020-03-09', '2004-06-30']) {
        expect(dayLabel(iso, lang)).toBe(fresh(iso, lang, { day: 'numeric', month: 'short', year: 'numeric' }));
        expect(monthLabel(iso, lang)).toBe(fresh(iso, lang, { month: 'short', year: 'numeric' }));
      }
      for (const v of [0, 7, 1234, 250000, -3]) expect(int(v, lang)).toBe(formatNumber(v, lang, { decimals: 0 }));
      expect(int(null, lang)).toBe(formatNumber(null, lang, { decimals: 0 }));
      expect(dayLabel(undefined, lang)).toBe(formatNumber(null, lang));
    }
  });

  it('build each date formatter once per language, however many days they label', () => {
    const spy = vi.spyOn(Intl, 'DateTimeFormat');
    for (let i = 0; i < 500; i += 1) {
      const iso = new Date(Date.UTC(2007, 0, 1 + i)).toISOString().slice(0, 10);
      dayLabel(iso, 'en');
      monthLabel(iso, 'en');
      dayLabel(iso, 'es');
    }
    expect(spy.mock.calls.length).toBeLessThanOrEqual(3);
  });
});
