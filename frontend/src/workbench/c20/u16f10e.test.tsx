// U16-F10e (fix round 4, the third capture review R3, batch c20), on the six committed documents in both languages: the decision
// flips name every shift (no raw shift id, the SGCD shocks by their names), the synthetic-shift note names its evaluation set, the
// planted leak and the CBPE assumptions are printed by their names, the explainer reads the input names of the names module, the
// Spanish views of these files carry no "commit" and no "bootstrap", the Fed shift options of the rail differ at their start, and the
// minors of the batch.
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { committedDoc, fixtureData } from '../c14/testkit';
import { C20ContextView, SeedReadout } from './C20Common';
import { DecisionFlipView, FairnessView, shiftName } from './FairnessViews';
import { ExplainerView, LeakageView, PerturbationView, featureLabel } from './RobustnessViews';
import { inputName } from '../names';
import { CbpeView, ConformalView, SyntheticShiftView, windowTone } from './ShiftViews';
import { DriftView } from './ShockViews';
import { defaultSel, evaluationSet, railShiftName, type C20Sel } from './selection';

const models = committedDoc<ModelsArtifact>('C20', 'models-c20-ladder');
const title = { en: 'ML model validation', es: 'Validación de modelos de ML' };
const selOf = (name: string): C20Sel => defaultSel(fixtureData('C20', committedDoc<VariantArtifact>('C20', name), models, title)) as C20Sel;
const DOCS = ['fed-shift', 'leakage-planted', 'perturbation-grid', 'seed-sweep', 'sgcd-held-out', 'sgcd-seen'] as const;
const RAW_SHIFT = /\b(fed-higher-risk-x[\d.]+|noise-[\d.]+|seed-\d+|decision-time-leak-unavailable|applied-F\d|applied-numeric-noise)\b/;

describe('U16-F10e C20', () => {
  afterEach(() => setLang('en'));

  it('c20 B1 and B2: every shift of the decision flips has a name, the SGCD shocks with their words', () => {
    for (const name of DOCS) {
      for (const lang of ['en', 'es'] as const) {
        const text = textOf(render(<DecisionFlipView sel={selOf(name)} />, lang));
        expect(text, `${name} ${lang}`).not.toMatch(RAW_SHIFT);
      }
    }
    expect(shiftName('applied-F1').es).toBe('Aplicado por Contraste, F1 campo faltante');
    expect(shiftName('applied-F4').en).toBe('Applied by Contraste, F4 contradiction');
    expect(shiftName('noise-0.05')).toEqual({ en: 'noise at 0.05 standard deviations', es: 'ruido de 0,05 desviaciones estándar' });
    expect(shiftName('seed-42')).toEqual({ en: 'retraining seed 42', es: 'semilla de reentrenamiento 42' });
    expect(shiftName('decision-time-leak-unavailable').en).toBe('at decision time, without the leak');
    expect(shiftName('fed-higher-risk-x0.25').en).not.toMatch(RAW_SHIFT);
  });

  it('c20 B3: the synthetic-shift note names its evaluation set and writes its rows in the language', () => {
    expect(evaluationSet({ evaluation_set: 'uci-polish-3year-holdout (3,151 rows, locked)' })).toEqual({ id: 'uci-polish-3year-holdout', rows: 3151 });
    expect(evaluationSet({ evaluation_set: 'uci-polish-3year-holdout', evaluation_rows: 3151 })).toEqual({ id: 'uci-polish-3year-holdout', rows: 3151 });
    for (const lang of ['en', 'es'] as const) {
      const text = textOf(render(<SyntheticShiftView sel={selOf('fed-shift')} />, lang));
      expect(text, lang).not.toMatch(/uci-polish-3year-holdout|rows, locked/);
      expect(text, lang).toContain(lang === 'en' ? '3,151 rows' : '3.151 filas');
      expect(text, lang).toContain(lang === 'en' ? 'UCI Polish company bankruptcy' : 'UCI quiebra de empresas polacas');
    }
  });

  it('c20 B4: the planted feature is printed by its name', () => {
    for (const lang of ['en', 'es'] as const) {
      const text = textOf(render(<LeakageView sel={selOf('leakage-planted')} />, lang));
      expect(text, lang).not.toMatch(/future_status_code/);
      expect(text, lang).toContain(lang === 'en' ? 'future status code' : 'código de estado futuro');
    }
  });

  it('c20 B5: the CBPE test row names its assumptions in words', () => {
    for (const lang of ['en', 'es'] as const) {
      const html = render(<CbpeView sel={selOf('fed-shift')} />, lang);
      const rows = [...html.matchAll(/<tr[^>]*data-test="ml\.cbpe_estimate"[\s\S]*?<\/tr>/g)].map((m) => textOf(m[0])).join(' ');
      expect(rows, lang).not.toMatch(/calibrated-probabilities|no-concept-drift|no-extrapolation|adequate-sample/);
    }
    const en = textOf(render(<CbpeView sel={selOf('fed-shift')} />, 'en'));
    expect(en).toMatch(/calibrated probabilities, no concept drift, no extrapolation and an adequate sample/);
  });

  it('c20 B6: the explainer names its features through the names module (the Taiwan names are the names module\'s)', () => {
    // a feature without a name in the names module prints as the file names it; the view never bypasses inputName
    expect(featureLabel('future_status_code').en).toBe('future status code (the planted leak)');
    expect(featureLabel('PAY_0')).toEqual(inputName('PAY_0') ?? { en: 'PAY_0', es: 'PAY_0' });
    const text = textOf(render(<ExplainerView sel={selOf('seed-sweep')} />, 'en'));
    expect(text).toContain(featureLabel('PAY_0').en);
    expect(render(<ExplainerView sel={selOf('seed-sweep')} />, 'en')).toMatch(/data-feature="PAY_0"/);
  });

  it('c20 B7: the Spanish views of these files carry no "commit" and no "bootstrap"', () => {
    const sgcd = selOf('sgcd-seen');
    expect(textOf(render(<C20ContextView sel={sgcd} />, 'es'))).not.toMatch(/\bcommit\b/);
    expect(textOf(render(<C20ContextView sel={sgcd} />, 'es'))).toContain('en la versión');
    expect(textOf(render(<SeedReadout sel={selOf('seed-sweep')} />, 'es'))).not.toMatch(/bootstrap/);
  });

  it('c20 M1: the Fed shift options of the rail differ in their first words', () => {
    const ids = ['fed-higher-risk-x0.25', 'fed-higher-risk-x0.5', 'fed-higher-risk-x1'];
    for (const lang of ['en', 'es'] as const) {
      const starts = ids.map((id) => railShiftName(id)![lang].slice(0, 12));
      expect(new Set(starts).size, lang).toBe(ids.length);
    }
    expect(railShiftName('baseline')).toBeNull();
  });

  it('m1: the chi-square cell reads "significant at 5 %" for p below 0.05, never "above the benchmark"', () => {
    for (const lang of ['en', 'es'] as const) {
      const text = textOf(render(<DriftView sel={selOf('sgcd-held-out')} />, lang));
      expect(text, lang).not.toMatch(/the benchmark at 5|umbral al 5/);
      expect(text, lang).toMatch(lang === 'en' ? /significant at 5 ?%/ : /significativo al 5 %/);
    }
  });

  it('m2: the drift title keeps the shock code upper case', () => {
    const text = textOf(render(<DriftView sel={selOf('sgcd-seen')} />, 'en'));
    expect(text).not.toMatch(/inputs of f\d/);
    expect(text).toMatch(/inputs of F\d/);
  });

  it('m5: the conformal bars take the tone of the window test, not of the coverage alone', () => {
    const sel = selOf('fed-shift');
    // the baseline window covers 89.5 % against a 90 % target with a green test: it is not drawn red
    expect(windowTone('baseline', sel.data.variant.tests)).toBe('good');
    expect(windowTone('fed-higher-risk-x0.25', sel.data.variant.tests)).toBe('bad');
    expect(windowTone('fed-higher-risk-x1', sel.data.variant.tests)).toBe('warn');
    expect(render(<ConformalView sel={sel} />, 'en')).toBeTruthy();
  });

  it('m6: the drift table says its PSI is the largest input PSI', () => {
    expect(textOf(render(<DriftView sel={selOf('sgcd-seen')} />, 'en'))).toContain('Largest input PSI');
    expect(textOf(render(<DriftView sel={selOf('sgcd-seen')} />, 'es'))).toContain('Mayor PSI de las entradas');
  });

  it('m8: the perturbation table says what the finding is at a scale other than the preset', () => {
    const text = textOf(render(<PerturbationView sel={selOf('perturbation-grid')} />, 'en'));
    expect(text).not.toMatch(/(?<!\()not the preset scale/);
    expect(text).toMatch(/loss above the tolerance \(not the preset scale\)/);
  });

  it('m9: the equalized-odds groups column names the rate it shows', () => {
    const sel = { ...selOf('seed-sweep'), test: 'fair.equalized_odds' } as C20Sel;
    const text = textOf(render(<FairnessView sel={sel} />, 'en'));
    expect(text).toMatch(/Groups \(rows, (true|false) positive rate\)/);
  });

  it('Q1 ruling: the SGCD card sentence is rendered in Spanish with the English original marked', () => {
    const html = render(<DriftView sel={selOf('sgcd-seen')} />, 'es');
    expect(html).toContain('«Se ofrece solo para investigación');
    expect(html).toMatch(/original en inglés: <span translate="no" lang="en">(&quot;|")It is provided for research/);
    expect(render(<DriftView sel={selOf('sgcd-seen')} />, 'en')).not.toContain('original en inglés');
  });
});
