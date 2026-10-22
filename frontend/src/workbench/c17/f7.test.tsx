// U16-F7 (the U16-R2 capture review, batch b08, C17): the minors of the operational-risk views, read on the committed documents.
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc, fixtureData, html, setLang, visibleText } from '../c14/testkit';
import { defaultSel, type C17Sel } from './selection';
import { ScenarioView } from './CapitalViews';

const models = committedDoc<ModelsArtifact>('C17', 'models-generator');
const title = { en: 'Operational risk: LDA vs SMA', es: 'Riesgo operacional: LDA vs SMA' };
const selOf = (name: string): C17Sel => defaultSel(fixtureData('C17', committedDoc<VariantArtifact>('C17', name), models, title)) as C17Sel;

describe('U16-F7 C17 (b08 minors)', () => {
  afterEach(() => setLang('en'));

  it('m7: no sentence of the scenario table starts in lower case after a full stop', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const text = visibleText(html(<ScenarioView sel={selOf('xi-0-8')} />));
      expect(text, lang).not.toMatch(/\. [a-záéíóúñ]/);
    }
  });
});
