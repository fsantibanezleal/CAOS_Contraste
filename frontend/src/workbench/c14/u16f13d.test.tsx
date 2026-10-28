// U16-F13d (fix round 6, the fifth capture review R5, batches c19 (C14) and c20 (C15)), on the committed documents, in both languages.
// M1 of both: the IRRBB tests table printed a segment only when the document gave one; R5 ruling 2 gives a row with no segment its
// scope in words, "whole balance sheet" / "todo el balance", and the two C14 tests that read the wholesale fit name that category.
// The minors: the Spanish quarter is "2022-T4" (c19 n3), the C15 rail reads the bars' two decimals (c20 m-n1) and the NII lead is a
// sentence (c20 m-n2).
import { afterEach, describe, expect, it } from 'vitest';
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { ReplicatingView } from './BehaviouralViews';
import { C14ContextView, C14VariantsTable, IrrbbTestsTable, quarterText } from './C14Common';
import { defaultSel, type C14Outputs, type C14Sel } from './selection';
import { committedDoc, fixtureData, html, setLang, visibleText } from './testkit';
import { ShockReadout } from '../c15/C15Common';
import { NiiView } from '../c15/RateViews';
import { amount, defaultSel as c15Default, eveRowOf, moneyDoc, type C15Outputs, type C15Sel } from '../c15/selection';

const c14Models = committedDoc<ModelsArtifact>('C14', 'models-svb-2021-2022');
const c15Models = committedDoc<ModelsArtifact>('C15', 'models-banco-andino-2026-09');
const C14 = ['vd-2021-q4', 'vd-2022-q2', 'vd-2022-q4'];
const C15 = ['long-uf', 'short-uf', 'clp-steepener', 'cpi-surprise', 'floors-active', 'offset-on-off'];
const doc = (c: string, name: string) => committedDoc<VariantArtifact>(c, name);
const c14Sel = (name: string): C14Sel => defaultSel(fixtureData('C14', doc('C14', name), c14Models, { en: 'IRRBB', es: 'IRRBB' })) as C14Sel;
const c15Sel = (name: string): C15Sel => c15Default(fixtureData('C15', doc('C15', name), c15Models, { en: 'IRRBB', es: 'IRRBB' })) as C15Sel;
const view = (el: React.ReactElement, lang: 'en' | 'es') => { setLang(lang); return html(el); };
const rowsOf = (markup: string) => markup.split('<tr data-test="').slice(1).map((r) => r.split('</tr>')[0]);
const WHOLESALE = new Set(['irrbb.nmd_parameter_stability', 'irrbb.behavioural_change_at_breach']);

describe('U16-F13d C14 and C15', () => {
  afterEach(() => setLang('en'));

  for (const lang of ['en', 'es'] as const) {
    const whole = lang === 'en' ? 'Whole balance sheet' : 'Todo el balance';
    const wholesale = lang === 'en' ? 'Wholesale deposits' : 'Depósitos mayoristas';

    it(`c19 M1 (${lang}): every C14 tests row names its scope, the wholesale fit's tests their category`, () => {
      for (const name of C14) {
        const d = doc('C14', name);
        const rows = rowsOf(view(<IrrbbTestsTable variant={d} />, lang));
        expect(rows.length, name).toBe(d.tests.length);
        expect(rows.filter((r) => !/data-segment="/.test(r)).length, `${name} ${lang}`).toBe(0);
        d.tests.forEach((t, i) => {
          const seg = visibleText(rows[i].split('</td>')[0]);
          expect(seg, `${name} ${t.test_id}`).toContain(WHOLESALE.has(t.test_id) ? wholesale : whole);
        });
      }
      // the view the reviewer read: the replicating portfolio's test says "wholesale", as its title does
      expect(visibleText(view(<ReplicatingView sel={c14Sel('vd-2022-q4')} />, lang))).toContain(wholesale);
    });

    it(`c20 M1 (${lang}): every C15 tests row names its scope, the golden-value rows "whole balance sheet"`, () => {
      for (const name of C15) {
        const d = doc('C15', name);
        const rows = rowsOf(view(<IrrbbTestsTable variant={d} />, lang));
        expect(rows.length, name).toBe(d.tests.length);
        expect(rows.filter((r) => !/data-segment="/.test(r)).length, `${name} ${lang}`).toBe(0);
        d.tests.forEach((t, i) => {
          const seg = visibleText(rows[i].split('</td>')[0]);
          if (t.segment === null) expect(seg, `${name} ${t.test_id}`).toContain(whole);
          else expect(seg, `${name} ${t.test_id}`).not.toContain(whole);
        });
      }
      const nii = rowsOf(view(<NiiView sel={c15Sel('long-uf')} />, lang));
      expect(nii.length).toBe(1);
      expect(visibleText(nii[0])).toContain(whole);
    });

    it(`c20 m-n1 (${lang}): the shock read-out prints the bars' two decimals`, () => {
      const s = c15Sel('clp-steepener');
      const o = s.data.variant.outputs as unknown as C15Outputs;
      const r = eveRowOf(o, s.shock)!;
      const text = visibleText(view(<ShockReadout sel={s} />, lang));
      for (const v of [r.clp.delta_eve, r.ur.delta_eve, r.pair.without_offset, r.pair.with_offset]) {
        expect(text).toContain(formatNumber(amount(moneyDoc(o), v).value, lang, { decimals: 2 }));
      }
    });
  }

  it('c19 n3: the Spanish quarter is "2022-T4", the English one "2022-Q4"', () => {
    expect(quarterText('2022-Q4', 'es')).toBe('2022-T4');
    expect(quarterText('Fecha de valoración 2022-12-31 (2022-Q4)', 'es')).toBe('Fecha de valoración 2022-12-31 (2022-T4)');
    expect(quarterText('2022-Q4', 'en')).toBe('2022-Q4');
    const es = visibleText(view(<C14ContextView sel={c14Sel('vd-2022-q4')} />, 'es'));
    expect(es).toContain('2022-12-31 (2022-T4)');
    expect(es).not.toMatch(/\d{4}-Q\d/);
    const variants = C14.map((id) => ({ id, title: { en: `Valuation date (${id.slice(3, 7)}-Q4)`, es: `Fecha de valoración (${id.slice(3, 7)}-Q4)` }, v: doc('C14', id) as unknown as VariantArtifact<C14Outputs> }));
    const table = visibleText(view(<C14VariantsTable variants={variants} onPick={() => undefined} current="vd-2022-q4" calibration="2024" />, 'es'));
    expect(table).not.toMatch(/\d{4}-Q\d/);
    expect(table).toContain('-T4');
  });

  it('c20 m-n2: the NII lead is a sentence with its verb', () => {
    expect(visibleText(view(<NiiView sel={c15Sel('long-uf')} />, 'en'))).toContain('This view shows the test of the CMF golden values, which covers the delta NII.');
    expect(visibleText(view(<NiiView sel={c15Sel('long-uf')} />, 'es'))).toContain('Esta vista muestra la prueba de los valores de referencia de la CMF, que cubre el delta NII.');
  });
});
