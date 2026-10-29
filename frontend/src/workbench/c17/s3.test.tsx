// S-3 of the method tiers plan (D03), on the committed documents: the four robust-severity rungs appear where the case shows its ladder,
// named in both languages, with their secondary-source status, and no raw id reaches the text of a view.
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { committedDoc, fixtureData } from '../c14/testkit';
import { ByMethodView } from './CapitalViews';
import { LadderView } from './ModelViews';
import { RUNG_ORDER, STATUS_TEXT, capitalOf, cellOf, defaultSel, outputsOf, rungName, type C17Sel } from './selection';

const NAMES = ['xi-0-6', 'xi-0-8', 'xi-0-96', 'xi-1-1'] as const;
const NEW = ['sla-mean-adjusted', 'sla-cvm', 'sla-obre', 'sla-cvm-lognormal'] as const;
const models = committedDoc<ModelsArtifact>('C17', 'models-generator');
const title = { en: 'Operational risk: LDA vs SMA', es: 'Riesgo operacional: LDA vs SMA' };
const selOf = (name: string): C17Sel => defaultSel(fixtureData('C17', committedDoc<VariantArtifact>('C17', name), models, title)) as C17Sel;

describe('S-3 C17: the robust severity rungs', () => {
  afterEach(() => setLang('en'));

  it('the ladder lists the four rungs after the six, each named in both languages', () => {
    expect(RUNG_ORDER.slice(6)).toEqual(NEW);
    for (const r of NEW) {
      const n = rungName(r);
      expect(n.en.length).toBeGreaterThan(5);
      expect(n.es.length).toBeGreaterThan(5);
      expect(n.es).not.toBe(n.en);
    }
    expect(STATUS_TEXT.SECONDARY_SOURCE).toEqual({ en: 'secondary source', es: 'fuente secundaria' });
  });

  for (const name of NAMES) {
    for (const lang of ['en', 'es'] as const) {
      it(`${name} (${lang}): the capital by method shows each new rung with a summary or the reason the document gives, and no raw id`, () => {
        const s = selOf(name);
        const o = outputsOf(s)!;
        const cell = cellOf(o, s.years, s.threshold);
        const element = render(<ByMethodView sel={s} />, lang);
        const markup = textOf(element);
        for (const r of NEW) {
          const { summary, reason } = capitalOf(cell, r);
          expect((summary === null) !== (reason === null)).toBe(true);
          if (summary) expect(summary.status).toBe('SECONDARY_SOURCE');
          expect(markup).toContain(rungName(r)[lang]);
        }
        expect(markup).not.toMatch(/\bsla[-_](cvm|obre|mean-adjusted)/);
      });

      it(`${name} (${lang}): the ladder table names the new rungs with the secondary-source status`, () => {
        const text = textOf(render(<LadderView sel={selOf(name)} />, lang));
        expect(text).toContain(STATUS_TEXT.SECONDARY_SOURCE[lang]);
        expect(text).not.toMatch(/\bsla[-_](cvm|obre|mean-adjusted)/);
      });
    }
  }
});
