// The Variants bars of C16 draw the survival days and the LiST annex medians in one unit. The variants' days are relevant days (the
// ladder counts US business days); the ECB annex gives its medians in calendar days, so a median is drawn at its converted relevant day
// through the document's own calendar (`relevantDayOfCalendarDay`, the function the ladder view uses), never at its raw number, and the
// reference bars and the axis say which unit they are in. Rendered on the committed documents.
import { afterEach, describe, expect, it } from 'vitest';
import type { VariantArtifact } from '../../lib/contract.types';
import { committedDoc, html, setLang, visibleText } from '../c14/testkit';
import { C16VariantsTable, survivalBars, type SurvivalBar } from './C16Common';
import { relevantDayOfCalendarDay } from './LadderViews';
import type { C16Outputs } from './selection';

const doc = <T,>(name: string) => committedDoc<VariantArtifact<T>>('C16', name);
const SCENARIOS = ['lcr-standard', 'list-adverse', 'list-extreme', 'fast-run', 'htm-losses'];
const variants = SCENARIOS.map((id) => ({ id, title: { en: id, es: id }, v: doc<C16Outputs>(id) }));
const medians = { adverse: 176, extreme: 122, nBanks: 103 };
const adverse = doc<C16Outputs>('list-adverse');
const text = (b: SurvivalBar | undefined) => b?.label as { en: string; es: string };

describe('C16 Variants bars: one unit', () => {
  afterEach(() => setLang('en'));

  it('draws the survival days as they are and the annex medians at their converted relevant days', () => {
    const bars = survivalBars(variants, 'list-adverse', medians);
    const byId = Object.fromEntries(bars.map((b) => [b.id, b]));
    expect(byId['list-adverse'].value).toBe(62);
    expect(byId['list-extreme'].value).toBe(41);
    expect(byId['htm-losses'].value).toBe(44);
    const o = adverse.outputs;
    const cal = o.conventions.day_calendar;
    expect(byId['median-adverse'].value).toBe(relevantDayOfCalendarDay(176, o.valuation_date, cal));
    expect(byId['median-extreme'].value).toBe(relevantDayOfCalendarDay(122, o.valuation_date, cal));
    // a calendar day is at least a relevant day: the converted bars are shorter than the raw medians
    expect(byId['median-adverse'].value).toBeLessThan(176);
    expect(byId['median-extreme'].value).toBeLessThan(122);
    expect(byId['median-adverse'].value).toBeGreaterThan(byId['median-extreme'].value);
  });

  it('names both units on every reference bar and draws no bar for a variant without a daily path', () => {
    const bars = survivalBars(variants, 'list-adverse', medians);
    expect(bars.map((b) => b.id)).toEqual(['list-adverse', 'list-extreme', 'htm-losses', 'median-adverse', 'median-extreme']);
    for (const b of bars.filter((x) => x.id.startsWith('median-'))) {
      expect(text(b).en).toMatch(/calendar days/);
      expect(text(b).en).toMatch(/relevant day/);
      expect(text(b).es).toMatch(/días calendario/);
      expect(text(b).es).toMatch(/día relevante/);
    }
    expect(text(bars.find((b) => b.id === 'median-adverse')).en).toContain('176 calendar days');
    expect(text(bars.find((b) => b.id === 'median-adverse')).en).toContain('103 banks');
  });

  it('without the annex it draws the variants alone', () => {
    expect(survivalBars(variants, 'list-adverse', null).map((b) => b.id)).toEqual(['list-adverse', 'list-extreme', 'htm-losses']);
  });

  for (const lang of ['en', 'es'] as const) {
    it(`labels the unit in the card (${lang})`, () => {
      setLang(lang);
      const text = visibleText(html(<C16VariantsTable variants={variants} onPick={() => undefined} current="list-adverse" medians={medians} />));
      expect(text).toContain(lang === 'en' ? 'relevant days' : 'días relevantes');
      expect(text).toContain(lang === 'en' ? 'calendar days' : 'días calendario');
    });
  }
});
