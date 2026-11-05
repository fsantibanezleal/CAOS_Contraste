// U16-F12d (fix round 5, the fourth capture review R4, batch c18 (C15)), on the committed documents, in both languages: every test
// of the document is on a C15 view (n1: the tests table was filtered to one test, so the one that did not run was never shown), the
// bar labels of a chart share one precision (m4), a breached test is drawn apart from the others (m6), a variant parameter reads as
// a value with its unit, not "0.3 share of Tier 1" (m12), and the prioritised-bank verdict comes before the table (m15).
import { readFileSync } from 'node:fs';
import { pick } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc, fixtureData, html, setLang, visibleText } from '../c14/testkit';
import { C15ContextView } from './C15Common';
import { ThresholdsView, thresholdsChart } from './FloorViews';
import { EveByLegView } from './LegViews';
import { NiiView } from './RateViews';
import { defaultSel, type C15Sel } from './selection';

const models = committedDoc<ModelsArtifact>('C15', 'models-banco-andino-2026-09');
const doc = (name: string) => committedDoc<VariantArtifact>('C15', name);
const selOf = (name: string): C15Sel => defaultSel(fixtureData('C15', doc(name), models, { en: 'IRRBB', es: 'IRRBB' })) as C15Sel;
const view = (el: React.ReactElement, lang: 'en' | 'es') => { setLang(lang); return html(el); };

describe('U16-F12d C15', () => {
  afterEach(() => setLang('en'));

  for (const lang of ['en', 'es'] as const) {
    it(`n1 (${lang}): the delta EVE view lists every test of the document, the one that did not run included`, () => {
      for (const name of ['long-uf', 'clp-steepener']) {
        const d = doc(name);
        const markup = view(<EveByLegView sel={selOf(name)} />, lang);
        const shown = [...markup.matchAll(/<tr data-test="([^"]+)" data-light="([^"]+)"/g)].map((m) => `${m[1]} ${m[2]}`);
        expect(shown, name).toEqual(d.tests.map((t) => `${t.test_id} ${t.light}`));
        expect(shown.some((s) => s.endsWith('not_evaluated')), name).toBe(true);
      }
      const nii = visibleText(view(<NiiView sel={selOf('long-uf')} />, lang));
      expect(nii).toContain(lang === 'en' ? 'The delta EVE view lists every test of the document.' : 'La vista del delta EVE lista todas las pruebas del documento.');
    });

    it(`m6 (${lang}): a breached test is drawn in its own series, apart from the tests within their threshold`, () => {
      const chart = thresholdsChart(selOf('clp-steepener'))!;
      const o = doc('clp-steepener').outputs as unknown as { thresholds: { tests: Array<{ ratio: number; breached: boolean }> } };
      const breached = chart.series.find((s) => pick(s.label, 'en') === 'Measured, above its threshold')!;
      expect(breached.values).toEqual(o.thresholds.tests.map((t) => (t.breached ? t.ratio : null)));
      expect(o.thresholds.tests.some((t) => t.breached)).toBe(true);
      const within = chart.series.find((s) => pick(s.label, 'en') === 'Measured, within its threshold')!;
      expect(within.values).toEqual(o.thresholds.tests.map((t) => (t.breached ? null : t.ratio)));
      // a variant with no breach draws no empty series
      expect(thresholdsChart(selOf('long-uf'))!.series.some((s) => pick(s.label, 'en') === 'Measured, above its threshold')).toBe(false);
    });

    it(`m12 (${lang}): a variant parameter reads as a value with its unit`, () => {
      const text = visibleText(view(<C15ContextView sel={selOf('long-uf')} />, lang));
      expect(text).not.toMatch(/\d share of|\d parte de|\d factor (on|sobre)/);
      expect(text).toContain(lang === 'en' ? '30 % of Tier 1' : '30 % del capital de nivel 1');
      expect(text).toContain(lang === 'en' ? '1 times the maturity' : '1 vez el plazo');
    });

    it(`m15 (${lang}): the prioritised-bank verdict comes before the thresholds table`, () => {
      for (const name of ['long-uf', 'clp-steepener']) {
        const markup = view(<ThresholdsView sel={selOf(name)} />, lang);
        expect(markup.indexOf('data-block="verdict"'), name).toBeGreaterThan(0);
        expect(markup.indexOf('data-block="verdict"'), name).toBeLessThan(markup.indexOf('data-table="thresholds"'));
      }
    });
  }

  it('m4: the bar labels of the floors, NII and EaR charts carry fixed decimals, not four significant digits', () => {
    const src = (f: string) => readFileSync(new URL(f, import.meta.url), 'utf8');
    const barAxes = (s: string) => [...s.matchAll(/<BarChart[\s\S]*?axis=\{\{([^\n]*)\}\}/g)].map((m) => m[1]);
    for (const f of ['./FloorViews.tsx', './RateViews.tsx', './LegViews.tsx', './C15Common.tsx']) {
      for (const axis of barAxes(src(f))) expect(axis, f).not.toContain('digits: 4');
    }
  });
});
