// U16-F9c (fix round 3, the partial R2b review of C20, report c20), on the committed documents: the Fed inputs, the shifts and the
// rungs by name in the drawings; a drawing of many bars keeps its full height in a box that scrolls (the real drift's 38 bars, the
// seed flips' 20); the seeds drawing gives the AUC range and the reasons kept an axis each.
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc, fixtureData, html, setLang, visibleText } from '../c14/testkit';
import { BARS_WHOLE } from './C20Common';
import { DecisionFlipView } from './FairnessViews';
import { SeedsView } from './RobustnessViews';
import { CbpeView, RealDriftView, SyntheticShiftView } from './ShiftViews';
import { defaultSel, type C20Sel } from './selection';

const models = committedDoc<ModelsArtifact>('C20', 'models-c20-ladder');
const title = { en: 'ML model validation', es: 'Validación de modelos de ML' };
const selOf = (name: string): C20Sel => defaultSel(fixtureData('C20', committedDoc<VariantArtifact>('C20', name), models, title)) as C20Sel;
const FED_FIELDS = /\b(committed_exposure_amt|utilized_exposure_amt|interest_rate|orig_year|facility_type_cat|lien_position_cat|domestic_flag|naics_two_digit_cat|interest_rate_variability|guarantor_flag)\b/;

describe('U16-F9c C20', () => {
  afterEach(() => setLang('en'));

  for (const lang of ['en', 'es'] as const) {
    it(`fed-shift (${lang}): the real drift names the Fed inputs, and its bars keep their height in a box that scrolls`, () => {
      setLang(lang);
      const markup = html(<RealDriftView sel={selOf('fed-shift')} />);
      expect(visibleText(markup)).not.toMatch(FED_FIELDS);
      const n = Number(markup.match(/data-bars="(\d+)"/)?.[1] ?? 0);
      expect(n).toBeGreaterThan(BARS_WHOLE);
      expect(markup).toContain('class="ct-c20-bars"');
    });

    it(`fed-shift (${lang}): the synthetic shift and the label-free estimate name each shift`, () => {
      setLang(lang);
      for (const V of [SyntheticShiftView, CbpeView]) expect(visibleText(html(<V sel={selOf('fed-shift')} />))).not.toMatch(/fed-higher-risk-x[\d.]+/);
    });

    it(`seed-sweep (${lang}): the rungs by their short titles and one axis per unit`, () => {
      setLang(lang);
      const markup = html(<SeedsView sel={selOf('seed-sweep')} />);
      expect(visibleText(markup)).not.toMatch(/\bP\d-(lightgbm|xgboost|logit|ebm)\b/i);
      expect(markup).toContain('class="ct-c20-pair"');
    });

    it(`seed-sweep (${lang}): the 20 seed flips keep their height in a box that scrolls`, () => {
      setLang(lang);
      expect(html(<DecisionFlipView sel={selOf('seed-sweep')} />)).toMatch(/class="ct-c20-bars"[^>]*data-bars="20"/);
    });
  }
});
