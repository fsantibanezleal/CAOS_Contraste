// U16-F9c (fix round 3, the partial R2b review of C21, report c21), on the six committed documents: the rates and replication tables
// get the taller box, the evidence names each finding by its number and title, the Spanish page gives each legal sentence in Spanish
// with the English original marked, and the controls note names its fields in English.
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc, fixtureData, html, setLang, visibleText } from '../c14/testkit';
import { C21ContextView, C21FindingsView } from './C21Common';
import { ControlledView, ReplicationView } from './EstimateViews';
import { RatesView } from './RateViews';
import { defaultSel, type C21Sel } from './selection';

const NAMES = ['pair-2018-19', 'pair-2019-20', 'pair-2020-21', 'pair-2021-22', 'pair-2022-23', 'pair-2023-24'] as const;
const models = committedDoc<ModelsArtifact>('C21', 'models-hmda-de-2018-2023');
const title = { en: 'Disparate impact on mortgage decisions', es: 'Impacto dispar en decisiones hipotecarias' };
const selOf = (name: string): C21Sel => defaultSel(fixtureData('C21', committedDoc<VariantArtifact>('C21', name), models, title)) as C21Sel;
const FINDING_ID = /\bF-[A-Z][A-Z-]+\b/;
const FIELD_CODE = /\b(debt_to_income_ratio|combined_loan_to_value_ratio|loan_amount|property_value|credit_score|loan_type|loan_purpose|lien_status|occupancy_type)\b/;

describe('U16-F9c C21', () => {
  afterEach(() => setLang('en'));

  for (const name of NAMES) {
    it(`${name}: the rates and the replication give their tables the taller box`, () => {
      expect(html(<RatesView sel={selOf(name)} />)).toMatch(/class="ct-c21-tall"[\s\S]*data-table=/);
      expect(html(<ReplicationView sel={selOf(name)} />)).toMatch(/class="ct-c21-tall"/);
    });

    for (const lang of ['en', 'es'] as const) {
      it(`${name} (${lang}): the evidence names no finding by its id`, () => {
        setLang(lang);
        expect(visibleText(html(<C21FindingsView sel={selOf(name)} />))).not.toMatch(FINDING_ID);
      });
    }

    it(`${name} (es): each legal sentence in Spanish, the English original marked, the citations in Spanish`, () => {
      setLang('es');
      const markup = html(<C21ContextView sel={selOf(name)} />);
      const block = markup.match(/data-block="legal-sentences"[\s\S]*?<\/ul>/)?.[0] ?? '';
      expect((block.match(/data-original="en"/g) ?? []).length).toBe(3);
      expect(visibleText(block)).toContain('La Ley no dispone');
      expect(visibleText(block)).not.toMatch(/as amended at|recital of|effective \d/);
    });

    it(`${name} (en): the controls note names its fields`, () => {
      setLang('en');
      expect(visibleText(html(<ControlledView sel={selOf(name)} />))).not.toMatch(FIELD_CODE);
    });
  }
});
