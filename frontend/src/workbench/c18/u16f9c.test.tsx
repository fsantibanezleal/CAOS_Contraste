// U16-F9c (fix round 3, the partial R2b review of C18, report c19, M-new-1): the stack view gives its two drawings the whole card
// and its tables a card beside them, so at 1280 the upper drawing keeps its axis and the legal minimum bar, on the committed documents.
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc, fixtureData, html, setLang } from '../c14/testkit';
import { StackView } from './CapitalViews';
import { defaultSel, type C18Sel } from './selection';

const models = committedDoc<ModelsArtifact>('C18', 'models-banco-andino');
const title = { en: 'ICAAP and IAPE capital aggregation under macro scenarios', es: 'Agregación de capital ICAAP e IAPE bajo escenarios macro' };
const selOf = (name: string): C18Sel => defaultSel(fixtureData('C18', committedDoc<VariantArtifact>('C18', name), models, title)) as C18Sel;
const SCENARIOS = ['baseline', 'eba-2025-adverse', 'fed-2026-severely-adverse', 'ngfs-delayed-transition'];

describe('U16-F9c C18 stack view', () => {
  afterEach(() => setLang('en'));

  for (const name of SCENARIOS) {
    it(`${name}: the drawings fill their card and the tables sit in a card beside them`, () => {
      const markup = html(<StackView sel={selOf(name)} />);
      expect(markup).toContain('class="ct-c18-stack-charts"');
      // no drawing over a 42 % table box: the stack is not a ChartOverTable any more
      expect(markup).not.toContain('class="ct-stack-table"');
      const at = markup.indexOf('data-block="numbers"');
      expect(at).toBeGreaterThan(markup.indexOf('class="ct-c18-stack-charts"'));
      for (const t of ['c18-stack', 'c18-stack-refs', 'c18-legal-stack']) expect(markup.indexOf(`data-table="${t}"`)).toBeGreaterThan(at);
    });
  }
});
