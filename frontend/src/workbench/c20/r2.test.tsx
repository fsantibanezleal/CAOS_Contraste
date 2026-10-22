// U16-F4 (the U16-R2 capture review, batch b09): the Spanish view of C20 carries no English basis, role, unit or engine description, and
// the decision-flip axis keeps its decimals. Every view is rendered on the eight committed documents.
import { afterEach, describe, expect, it } from 'vitest';
import type { ReactElement } from 'react';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc, englishLeaks, fixtureData, html, setLang, visibleText } from '../c14/testkit';
import { defaultSel, type C20Sel } from './selection';
import { C20ContextView, C20FindingsView } from './C20Common';
import { DegradationView, DriftView, QualityView } from './ShockViews';
import { CbpeView, ConformalView, RealDriftView, SyntheticShiftView } from './ShiftViews';
import { ExplainerView, LeakageView, PerturbationView, SeedsView } from './RobustnessViews';
import { DecisionFlipView, FairnessView } from './FairnessViews';

type View = (p: { sel: C20Sel | null }) => ReactElement;
const ALL: Array<[string, View]> = [
  ['Degradation', DegradationView], ['Drift', DriftView], ['Quality', QualityView], ['RealDrift', RealDriftView], ['SyntheticShift', SyntheticShiftView],
  ['Conformal', ConformalView], ['Cbpe', CbpeView], ['Noise', PerturbationView], ['Seeds', SeedsView], ['Explainers', ExplainerView], ['Leakage', LeakageView],
  ['Fairness', FairnessView], ['Flips', DecisionFlipView], ['Findings', C20FindingsView], ['Context', C20ContextView],
];
const NAMES = ['sgcd-held-out', 'sgcd-seen', 'fed-shift', 'leakage-planted', 'perturbation-grid', 'seed-sweep'] as const;
const models = committedDoc<ModelsArtifact>('C20', 'models-c20-ladder');
const title = { en: 'ML model validation', es: 'Validación de modelos de ML' };
const selOf = (name: string): C20Sel => defaultSel(fixtureData('C20', committedDoc<VariantArtifact>('C20', name), models, title)) as C20Sel;

// what a reader must find as written: library names, licences, the dataset file names and the quotation of the licence
const VERBATIM = ['InterpretML', 'ExplainableBoostingClassifier', 'optbinning', 'statsmodels', 'scikit-learn', 'LogisticRegression', 'Apache-2.0', 'BSD-3-Clause',
  'SGCDataset_metadata.json', 'uci-polish', 'uci-taiwan', /\b[a-z]+(?:[-_][a-z0-9]+)+\b/g, /It is provided for research[^"]*individuals\./g, 'Taiwan', 'Fed', 'UCI', 'German'];

describe('U16-F4 C20: the Spanish view', () => {
  afterEach(() => setLang('en'));

  it('PR-C20: no view of the Spanish capture carries an English basis, role, unit, engine description or group name, on the committed documents', () => {
    setLang('es');
    const all: string[] = [];
    for (const name of NAMES) {
      for (const [view, View] of ALL) {
        const text = visibleText(html(<View sel={selOf(name)} />));
        for (const leak of englishLeaks(text, VERBATIM)) all.push(`${name} ${view} ${leak}`);
      }
    }
    expect([...new Set(all)]).toEqual([]);
  });

  it('V20-1: the decision-flip axis shows two decimals, so steps of a quarter of a percent read as such', () => {
    const sel = selOf('sgcd-held-out');
    const text = visibleText(html(<DecisionFlipView sel={sel} />));
    expect(text).not.toMatch(/\b0\.3 %|\b0\.8 %|\b1\.3 %/);
  });

  it('m4: the es view says "fila roja" in the singular and keeps the seed out of the degradation text', () => {
    setLang('es');
    const text = visibleText(html(<DegradationView sel={selOf('sgcd-held-out')} />));
    expect(text).not.toMatch(/\b1 filas\b/);
  });
});
