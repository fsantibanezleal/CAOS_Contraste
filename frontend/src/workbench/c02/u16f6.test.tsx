// U16-F6 (the second fix round, C02): the minors of the b01 review that belong to C02's views, on the committed documents.
import { afterEach, describe, expect, it } from 'vitest';
import { committedData, render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { C02ContextView } from './C02Common';
import { EclImpactView } from './HorizonViews';
import { span, defaultSel } from './selection';
import { RungsView } from './DiscriminationViews';

const sel = () => defaultSel(committedData('C02', 'h1'))!;

describe('U16-F6 C02', () => {
  afterEach(() => setLang('en'));

  it('b01 m10: an interval is told with to / a, never a hyphen beside a negative bound', () => {
    expect(span('-0.0221', '-0.0118', 'en')).toBe('-0.0221 to -0.0118');
    expect(span('-0,0221', '-0,0118', 'es')).toBe('-0,0221 a -0,0118');
  });

  it('b01 m10: the rungs compared print no " - " between two numbers', () => {
    const t = textOf(render(<RungsView sel={sel()} />, 'en'));
    expect(t).not.toMatch(/\d - -?\d/);
  });

  it('b01 m15: the impact note says whose PDs replace the ones in use', () => {
    const en = textOf(render(<EclImpactView sel={sel()} />, 'en'));
    expect(en).toContain('five file event rates, not the rung');
    const es = textOf(render(<EclImpactView sel={sel()} />, 'es'));
    expect(es).toContain('no las del peldaño');
  });

  it('b01 m8: Spanish says peldaño and agrupación, not escalón or Binning', () => {
    const es = textOf(render(<C02ContextView sel={sel()} />, 'es')) + textOf(render(<RungsView sel={sel()} />, 'es'));
    expect(es).not.toMatch(/Binning|escalón|escalones/);
  });
});
