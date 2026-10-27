// U16-F12d (fix round 5, the fourth capture review R4, batch c17 (C14)), on the committed documents, in both languages: the
// Parameter changes view lists only the changes up to the selected valuation date, so its flagged rows agree with the test row
// below them (M1, ruling 5), the dynamic NII items are named (m8), ISO dates stay whole in the window cells at 390 (n10), and the
// EaR note points up to the method rows it names (n11).
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { ChangesView, ReplicatingView } from './BehaviouralViews';
import { C14VariantsTable } from './C14Common';
import { DynamicNiiView, EarEvarView } from './NiiViews';
import { defaultSel, type C14Sel } from './selection';
import { committedDoc, fixtureData, html, setLang, visibleText } from './testkit';

const models = committedDoc<ModelsArtifact>('C14', 'models-svb-2021-2022');
const doc = (name: string) => committedDoc<VariantArtifact>('C14', name);
const selOf = (name: string): C14Sel => defaultSel(fixtureData('C14', doc(name), models, { en: 'IRRBB', es: 'IRRBB' })) as C14Sel;
const VARIANTS = ['vd-2021-q4', 'vd-2022-q2', 'vd-2022-q4'];

describe('U16-F12d C14', () => {
  afterEach(() => setLang('en'));

  for (const lang of ['en', 'es'] as const) {
    it(`M1 (${lang}): the changes view keeps the rows up to the valuation date, and its flagged rows equal the test's count`, () => {
      for (const name of VARIANTS) {
        const v = doc(name) as unknown as { outputs: { valuation_date: string }; tests: Array<{ test_id: string; statistic: number | null }> };
        setLang(lang);
        const markup = html(<ChangesView sel={selOf(name)} />);
        const windows = [...markup.matchAll(/data-window="(\d{4}-\d{2}-\d{2}) (\d{4}-\d{2}-\d{2})"/g)].map((m) => m[2]);
        for (const to of windows) expect(to <= v.outputs.valuation_date, `${name} ${to}`).toBe(true);
        const flagged = (markup.match(/data-flagged="true"/g) ?? []).length;
        const test = v.tests.find((t) => t.test_id === 'irrbb.behavioural_change_at_breach')!;
        expect(flagged, name).toBe(test.statistic ?? 0);
      }
      setLang(lang);
      const none = visibleText(html(<ChangesView sel={selOf('vd-2021-q4')} />));
      expect(none).toContain(lang === 'en' ? 'no behavioural parameter changed between the valuation dates' : 'ningún parámetro conductual cambió entre las fechas de valoración');
      setLang(lang);
      expect((html(<ChangesView sel={selOf('vd-2022-q4')} />).match(/data-window="/g) ?? []).length).toBe(6);
    });

    it(`m8 (${lang}): the dynamic NII items are named, never "Asset 1" or "Liability 8"`, () => {
      setLang(lang);
      const text = visibleText(html(<DynamicNiiView sel={selOf('vd-2022-q4')} />));
      expect(text).not.toMatch(/\b(Asset|Liability|Activo|Pasivo) \d+\b/);
      expect(text).toContain(lang === 'en' ? 'Non-interest-bearing deposits' : 'Depósitos sin interés');
      expect(text).toContain(lang === 'en' ? 'Loans repricing within 3 months' : 'Préstamos que reprecian en 3 meses o menos');
    });

    it(`n10 (${lang}): the ISO dates of the window cells never break at their hyphen`, () => {
      for (const el of [<ChangesView key="c" sel={selOf('vd-2022-q4')} />, <ReplicatingView key="r" sel={selOf('vd-2022-q4')} />]) {
        setLang(lang);
        const markup = html(el);
        const bare = markup.replace(/<span style="white-space:nowrap">\d{4}-\d{2}-\d{2}<\/span>/g, '').replace(/data-window="[^"]*"/g, '');
        expect(bare).not.toMatch(/>[^<]*\d{4}-\d{2}-\d{2}/);
      }
      const entry = (name: string) => ({ id: name, title: { en: name, es: name }, v: doc(name) as never });
      setLang(lang);
      const table = html(<C14VariantsTable variants={VARIANTS.map(entry)} onPick={() => undefined} current="vd-2022-q4" calibration="2024" />);
      expect(table).toMatch(/<span style="white-space:nowrap">2021-12-31<\/span>/);
    });

    it(`n11 (${lang}): the EaR note names the method rows above it`, () => {
      setLang(lang);
      const text = visibleText(html(<EarEvarView sel={selOf('vd-2022-q4')} />));
      expect(text).toContain(lang === 'en' ? 'the method named above' : 'el método nombrado arriba');
      expect(text).not.toMatch(/named below|nombrado abajo/);
    });
  }
});
