// U16-F13d (fix round 6, the fifth capture review R5, batch c21 (C16)), on the committed documents, in both languages.
// M1: under 640 px the tests table hides its Against column, and only the back-test rows carried their segment under the name; R5
// ruling 2 gives a row with no segment its scope in words, "whole balance sheet" / "todo el balance", at every width (the phone span
// and the wide Against cell). jsdom applies no media query, so the test reads the phone span itself. The minors: the Table A.1 bars
// leave the table its room at 1280 (n2), the reason for a missing implied rate is said once in the note (n3) and the cliff reason
// reads in its value cell (n5).
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc, fixtureData, html, setLang, visibleText } from '../c14/testkit';
import { C16TestsView } from './C16Common';
import { LadderView, RunSpeedsView } from './LadderViews';
import { defaultSel, type C16Sel } from './selection';

const models = committedDoc<ModelsArtifact>('C16', 'models-svb-liquidity');
const title = { en: 'Liquidity stress', es: 'Estrés de liquidez' };
const selOf = (name: string): C16Sel => defaultSel(fixtureData('C16', committedDoc<VariantArtifact>('C16', name), models, title)) as C16Sel;
const SCENARIOS = ['lcr-standard', 'list-adverse', 'list-extreme', 'fast-run', 'htm-losses'];
const view = (el: React.ReactElement, lang: 'en' | 'es') => { setLang(lang); return html(el); };
const rowsOf = (markup: string) => markup.split('<tr data-test="').slice(1).map((r) => r.split('</tr>')[0]);
const REASON = { en: 'only the calibration rows and the SVB anchor imply a daily rate', es: 'solo las filas de calibración y el ancla de SVB implican una tasa diaria' };

describe('U16-F13d C16', () => {
  afterEach(() => setLang('en'));

  for (const lang of ['en', 'es'] as const) {
    it(`M1 (${lang}): every row carries its segment on the phone, a row with no segment "whole balance sheet"`, () => {
      const whole = lang === 'en' ? 'whole balance sheet' : 'todo el balance';
      for (const name of SCENARIOS) {
        const d = committedDoc<VariantArtifact>('C16', name);
        const rows = rowsOf(view(<C16TestsView sel={selOf(name)} />, lang));
        expect(rows.length, name).toBe(d.tests.length);
        rows.forEach((r, i) => {
          const phone = r.match(/<span class="ct-narrow-only" data-segment="[^"]*">([^<]*)<\/span>/);
          expect(phone, `${name} ${d.tests[i].test_id} ${lang}`).not.toBeNull();
          const wide = visibleText(r.split('</td>')[1] ?? '');
          if (d.tests[i].segment === null) {
            expect(phone![1].toLowerCase(), d.tests[i].test_id).toContain(whole);
            expect(wide.toLowerCase(), d.tests[i].test_id).toContain(whole);
          } else {
            expect(phone![1].toLowerCase()).not.toContain(whole);
          }
        });
      }
    });

    it(`n2 (${lang}): the nine Table A.1 bars keep 16.5rem, not 22rem, so the table has its room at 1280`, () => {
      const markup = view(<RunSpeedsView sel={selOf('fast-run')} />, lang);
      expect(markup).toContain('class="ct-stack-chart" style="min-height:16.5rem');
    });

    it(`n3 (${lang}): the reason for a row with no implied daily rate is said once, in the note, not in each cell`, () => {
      const text = visibleText(view(<RunSpeedsView sel={selOf('list-extreme')} />, lang));
      expect(text.split(REASON[lang]).length - 1).toBe(1);
    });

    it(`n5 (${lang}): the cliff reason reads in its value cell, in lower case after the dash`, () => {
      const markup = view(<LadderView sel={selOf('fast-run')} />, lang);
      const cell = markup.split('data-table="c16-ladder"')[1]?.split('</dl>')[0] ?? '';
      expect(cell).not.toContain('text-align:right');
      const reason = visibleText(cell).split(/\(|:/).slice(-1)[0] ?? '';
      expect(visibleText(cell)).not.toMatch(/\(The horizon|\(El horizonte/);
      expect(reason.length).toBeGreaterThan(0);
    });
  }
});
