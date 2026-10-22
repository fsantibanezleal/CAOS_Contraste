// U16-F4 (the U16-R2 capture review, batch b10): the Spanish view of C21 carries no English rule, unit, normalisation, interval
// description or data note, and an interval reads "from a to b" without a double minus. Every view is rendered on the six committed
// documents.
import { afterEach, describe, expect, it } from 'vitest';
import type { ReactElement } from 'react';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc, englishLeaks, fixtureData, html, setLang, visibleText } from '../c14/testkit';
import { defaultSel, type C21Sel } from './selection';
import { C21ContextView, C21FindingsView } from './C21Common';
import { ControlledView, RateSpreadView, ReplicationView, SituationView } from './EstimateViews';
import { FourFifthsView, RatesView, TestsView } from './RateViews';

const VIEWS: Array<[string, (p: { sel: C21Sel | null }) => ReactElement]> = [
  ['Rates', RatesView], ['FourFifths', FourFifthsView], ['Tests', TestsView], ['Controlled', ControlledView], ['RateSpread', RateSpreadView],
  ['Replication', ReplicationView], ['Situation', SituationView], ['Findings', C21FindingsView], ['Context', C21ContextView],
];
const NAMES = ['pair-2018-19', 'pair-2019-20', 'pair-2020-21', 'pair-2021-22', 'pair-2022-23', 'pair-2023-24'] as const;
const models = committedDoc<ModelsArtifact>('C21', 'models-hmda-de-2018-2023');
const title = { en: 'Disparate impact on mortgage decisions', es: 'Impacto dispar en decisiones hipotecarias' };
const selOf = (name: string): C21Sel => defaultSel(fixtureData('C21', committedDoc<VariantArtifact>('C21', name), models, title)) as C21Sel;

// what a reader must find as written: the statute and rule names, the dataset, the paper, the evidence ids of the shared findings
// card and the quotations of the law (a legal text is quoted, also inside a finding title)
const VERBATIM = [
  'HMDA', 'Fair Housing Act', 'Regulation B', 'arXiv', 'Wald', 'Home Mortgage Disclosure Act', 'FFIEC', 'CFPB',
  /\b[a-z]+(?:[-_][a-z0-9]+)+\b/g, /@[A-Za-z0-9:_-]+/g, /91 FR 21620[^)]*Inc\./g, /62 or over vs under 62/g,
  /the Supreme Court held[^.]*\./g, /Gross HMDA denial[^.]*\./g, /The Act does not provide[^.]*\./g,
];

describe('U16-F4 C21: the Spanish view', () => {
  afterEach(() => setLang('en'));

  it('V21-2: no view of the Spanish capture carries an English rule, unit, normalisation or note, on the committed documents', () => {
    setLang('es');
    const all: string[] = [];
    for (const name of NAMES) {
      for (const [view, View] of VIEWS) {
        const text = visibleText(html(<View sel={selOf(name)} />));
        for (const leak of englishLeaks(text, VERBATIM)) all.push(`${name} ${view} ${leak}`);
      }
    }
    expect([...new Set(all)]).toEqual([]);
  });

  it('m2: an interval with a negative end is written without a bare minus between the ends', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      for (const name of NAMES) {
        const text = visibleText(html(<ControlledView sel={selOf(name)} />)) + visibleText(html(<RateSpreadView sel={selOf(name)} />));
        expect(text, `${name} ${lang}`).not.toMatch(/\d - -\d/);
      }
    }
  });
});
