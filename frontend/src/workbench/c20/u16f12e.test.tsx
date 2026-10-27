// U16-F12e (fix round 5, the fourth capture review R4, batch c24: the minors of C20 in these files), on the six committed documents
// in both languages: an AUC loss is drawn in the bad tone, the Variants card takes the provenance of the variant on screen and no bar
// reads as selected when the variant has none, one standard deviation is singular, no parentheses nest, the decision flips open on the
// largest and share the table's decimals, the Spanish unit of a list of multiples is plural, p keeps fixed decimals, the SGCD sentence
// stays on the SGCD variants and the noise chart marks its tolerance.
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { committedDoc, fixtureData } from '../c14/testkit';
import { C20ContextView, variantBars } from './C20Common';
import { flipBars, shiftName } from './FairnessViews';
import { LeakageView, toleranceMark } from './RobustnessViews';
import { syntheticShiftBars } from './ShiftViews';
import { DriftView, QUALITY_FORMAT } from './ShockViews';
import { unitEs } from './localise';
import { defaultSel, type C20Sel } from './selection';

const models = committedDoc<ModelsArtifact>('C20', 'models-c20-ladder');
const title = { en: 'ML model validation', es: 'Validación de modelos de ML' };
const doc = (name: string) => committedDoc<VariantArtifact>('C20', name);
const selOf = (name: string): C20Sel => defaultSel(fixtureData('C20', doc(name), models, title)) as C20Sel;
const DOCS = ['fed-shift', 'leakage-planted', 'perturbation-grid', 'seed-sweep', 'sgcd-held-out', 'sgcd-seen'] as const;
const LANGS = ['en', 'es'] as const;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const out = (name: string): any => doc(name).outputs;

describe('U16-F12e C20', () => {
  afterEach(() => setLang('en'));

  it('c24 n2: every AUC loss of the synthetic shift is drawn in the bad tone, a gain in the good one', () => {
    const s = out('fed-shift').synthetic_shift;
    const bars = syntheticShiftBars(s, null);
    expect(bars.length).toBeGreaterThan(1);
    for (const b of bars) expect(b.tone, b.id).toBe(b.value > 0 ? 'bad' : 'good');
  });

  it('c24 n6: with no bar for the variant on screen, no bar is drawn as the selection', () => {
    const measured = [{ id: 'a', title: { en: 'A', es: 'A' }, loss: 0.1 }, { id: 'b', title: { en: 'B', es: 'B' }, loss: 0.2 }];
    for (const b of variantBars(measured, 'seed-sweep')) {
      expect(b.highlight).toBe(false);
      expect(b.tone).toBe('neutral');
    }
    expect(variantBars(measured, 'a').find((b) => b.id === 'a')!.highlight).toBe(true);
  });

  it('c24 n7: one standard deviation is singular in both languages', () => {
    expect(shiftName('noise-1')).toEqual({ en: 'noise at 1 standard deviation', es: 'ruido de 1 desviación estándar' });
    expect(shiftName('noise-0.5').en).toBe('noise at 0.5 standard deviations');
  });

  it('c24 n8: the leakage view nests no parentheses', () => {
    for (const lang of LANGS) {
      const text = textOf(render(<LeakageView sel={selOf('leakage-planted')} />, lang));
      expect(text, lang).not.toMatch(/\([^()]*\([^()]*\)\)/);
    }
  });

  it('c24 n9, n10: the decision flips open on the largest share and keep the table\'s one decimal', () => {
    const rows = out('seed-sweep').impact_detail.rows as Array<{ shift_id: string; flip_share: number }>;
    const bars = flipBars(rows);
    for (let i = 1; i < bars.length; i++) expect(bars[i - 1].value).toBeGreaterThanOrEqual(bars[i].value);
    for (const b of bars) expect(b.format).toEqual({ percent: true, decimals: 1 });
    expect(QUALITY_FORMAT).toEqual({ percent: true, decimals: 1 });
  });

  it('c24 n11: the Spanish unit of a list of multiples is plural', () => {
    expect(unitEs("multiple of each feature's standard deviation", 'es')).toBe('múltiplos de la desviación estándar de cada variable');
    expect(unitEs('multiple of the average test error', 'es')).toBe('múltiplos del error promedio de prueba');
  });

  it('c24 n12: a p value of the inputs table keeps three decimals', () => {
    for (const lang of LANGS) {
      const html = render(<DriftView sel={selOf('sgcd-seen')} />, lang);
      // 0.4979 is printed 0.498 / 0,498, never "0.5" beside 0.031
      expect(textOf(html), lang).not.toMatch(/(?:^|\s)0[.,]5(?:\s|$)/);
    }
  });

  it('c24 n13: the SGCD sentence about the view a shock reaches is on the SGCD variants only', () => {
    for (const name of DOCS) {
      const text = textOf(render(<C20ContextView sel={selOf(name)} />, 'en'));
      const said = text.includes('a shock that does not reach that view cannot move it');
      expect(said, name).toBe(name.startsWith('sgcd'));
    }
  });

  it('c24 n15: the noise chart marks the tolerance at the preset scale as a level of the AUC', () => {
    const o = out('perturbation-grid');
    const m = toleranceMark(o);
    expect(m).not.toBeNull();
    const preset = o.rows.find((r: { eps: number }) => r.eps === o.preset_eps);
    const tol = o.parameters.find((p: { name: string }) => p.name === 'perturbation_tolerance').value as number;
    expect(m!.y).toBeCloseTo(preset.metric.auc - preset.metric.auc_delta - tol, 9);
    expect((m!.label as { en: string }).en).toMatch(/Tolerance \(convention\)/);
  });
});
