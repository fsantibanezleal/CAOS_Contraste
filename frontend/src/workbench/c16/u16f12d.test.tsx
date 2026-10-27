// U16-F12d (fix round 5, the fourth capture review R4, batches c19 and c20 (C16)), on the committed documents, in both languages.
// M1: the Variants view and the LCR composition hid table rows and whole tables at 1280 with no cue; the variants table now takes
// the height the drawing leaves (not the shared 42 % box), the reverse stress is its own card beside it, and the LCR tables are a
// card of their own. The minors: the CBC and time-block drawings at their size (c20 n1, c19 m3), the HTM table's unit (m4), the
// fast-run sensitivities (m5), "no comparator" for a test with no segment (m6), the call reports in date order (m7), the two
// realised-run points told apart (n8), the HTM note in the card's note (n9), the LCR caveat said twice, not three times (n6), a
// reason for a run speed with no implied rate (c20 n4) and the run-off axis in percent (c20 n7).
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc, fixtureData, html, setLang, visibleText } from '../c14/testkit';
import { CbcView, LcrView, TimeBlockView } from './BufferViews';
import { C16ContextView, C16ReverseCard, C16TestsView, C16VariantsTable } from './C16Common';
import { RunSpeedsView, RunoffView } from './LadderViews';
import { HtmLossView, UninsuredShareView } from './SensitivityViews';
import { defaultSel, type C16Outputs, type C16Reverse, type C16Sel } from './selection';

const models = committedDoc<ModelsArtifact>('C16', 'models-svb-liquidity');
const title = { en: 'Liquidity stress', es: 'Estrés de liquidez' };
const doc = <T,>(name: string) => committedDoc<VariantArtifact<T>>('C16', name);
const selOf = (name: string): C16Sel => defaultSel(fixtureData('C16', committedDoc<VariantArtifact>('C16', name), models, title)) as C16Sel;
const SCENARIOS = ['lcr-standard', 'list-adverse', 'list-extreme', 'fast-run', 'htm-losses'];
const variants = SCENARIOS.map((id) => ({ id, title: { en: id, es: id }, v: doc<C16Outputs>(id) }));
const view = (el: React.ReactElement, lang: 'en' | 'es') => { setLang(lang); return html(el); };

describe('U16-F12d C16', () => {
  afterEach(() => setLang('en'));

  for (const lang of ['en', 'es'] as const) {
    it(`M1 (${lang}): the variants table takes the height its drawing leaves, and the reverse stress is a card of its own`, () => {
      const markup = view(<C16VariantsTable variants={variants} onPick={() => undefined} current="list-adverse" medians={{ adverse: 176, extreme: 122, nBanks: 103 }} />, lang);
      // five bars on the committed documents (three survival days and the two LiST medians): 5 x 1.5 + 3 rem
      expect(markup).toContain('class="ct-stack-fixed" style="min-height:10.5rem');
      expect(markup).not.toContain('class="ct-stack-table"');
      expect(markup).toMatch(/class="ct-stack-rest"[\s\S]*data-table="variants-c16"/);
      expect(markup).not.toContain('data-table="variants-c16-reverse"');
      const reverse = view(<C16ReverseCard reverse={doc<C16Reverse>('reverse-stress')} current="reverse-stress" onPick={() => undefined} />, lang);
      expect(reverse).toContain('data-table="variants-c16-reverse"');
      expect((reverse.match(/<tr data-base=/g) ?? []).length).toBe(3);
    });

    it(`M1, n6 (${lang}): the LCR composition puts its tables in a card of their own and says the caveat twice, not three times`, () => {
      const markup = view(<LcrView sel={selOf('lcr-standard')} />, lang);
      expect(markup).toContain('data-views="2"');
      expect(markup).toContain('data-share="3"');
      const second = markup.split('class="caos-views-col"')[2] ?? '';
      expect(second).toContain('data-table="c16-lcr-flows"');
      expect(second).toContain('data-table="c16-lcr-mapping"');
      expect(markup).not.toContain('<strong>');
    });

    it(`c20 n1, m3 (${lang}): the CBC drawing keeps 12rem for six bars and the time block 18rem`, () => {
      expect(view(<CbcView sel={selOf('list-adverse')} />, lang)).toContain('class="ct-stack-fixed" style="min-height:12rem');
      expect(view(<TimeBlockView sel={selOf('list-adverse')} />, lang)).toContain('class="ct-stack-fixed" style="min-height:18rem');
    });

    it(`m4, n9 (${lang}): the HTM table states its unit and its note is the card's note, outside the table box`, () => {
      const markup = view(<HtmLossView sel={selOf('list-adverse')} />, lang);
      expect(visibleText(markup)).toContain(lang === 'en' ? 'CBC (USD thousands)' : 'CBC (miles de USD)');
      const note = lang === 'en' ? 'the table keeps the whole amounts of the loss and the CBC' : 'la tabla conserva los montos completos de la pérdida y del CBC';
      expect(markup).toMatch(new RegExp(`class="caos-plot-note">[^<]*${note}`));
    });

    it(`m5 (${lang}): with no survival day drawn the share note does not say a mark is drawn, and the HTM chart draws the survivors`, () => {
      const share = visibleText(view(<UninsuredShareView sel={selOf('fast-run')} />, lang));
      expect(share).not.toContain(lang === 'en' ? "The document's own share is marked." : 'Se marca la parte propia del documento.');
      expect(visibleText(view(<UninsuredShareView sel={selOf('list-adverse')} />, lang))).toContain(lang === 'en' ? "The document's own share is marked." : 'Se marca la parte propia del documento.');
      const htm = view(<HtmLossView sel={selOf('fast-run')} />, lang);
      expect(htm).toContain('data-series="2"');
      expect(visibleText(htm)).toContain(lang === 'en' ? 'Survives the horizon, drawn at day 5' : 'Sobrevive el horizonte, dibujado en el día 5');
    });

    it(`m6 (${lang}): a test with no segment says it has no comparator`, () => {
      const text = visibleText(view(<C16TestsView sel={selOf('list-adverse')} />, lang));
      expect(text).toContain(lang === 'en' ? 'no comparator' : 'sin comparador');
    });

    it(`m7 (${lang}): the call reports read are in date order`, () => {
      const text = visibleText(view(<C16ContextView sel={selOf('list-adverse')} />, lang));
      expect(text).toContain('2021-12-31, 2022-06-30, 2022-12-31');
    });

    it(`n8, c20 n7 (${lang}): the two realised-run points are told apart, and the run-off axis is in percent`, () => {
      const markup = view(<RunoffView sel={selOf('list-adverse')} />, lang);
      expect(markup).toContain(lang === 'en' ? 'Cumulative outflow (percent of the segment)' : 'Salida acumulada (porcentaje del segmento)');
      expect(markup).toContain('--swatch:var(--color-bad)');
      expect(markup).toContain('--swatch:var(--color-warn)');
    });

    it(`c20 n4 (${lang}): a run speed with no implied daily rate says why`, () => {
      const text = visibleText(view(<RunSpeedsView sel={selOf('list-extreme')} />, lang));
      expect(text).toContain(lang === 'en' ? 'only the calibration rows and the SVB anchor imply a daily rate' : 'solo las filas de calibración y el ancla de SVB implican una tasa diaria');
    });
  }
});
