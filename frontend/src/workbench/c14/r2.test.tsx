// U16-F4 (the U16-R2 capture review, batch b07): the Spanish view of C14 carries no English prose, the parameter changes are
// named in words and keep their window at 390 px. Every view is rendered on the three committed valuation-date documents.
import { afterEach, describe, expect, it } from 'vitest';
import type { ReactElement } from 'react';
import type { VariantArtifact, ModelsArtifact } from '../../lib/contract.types';
import { committedDoc, englishLeaks, fixtureData, html, setLang, visibleText } from './testkit';
import { defaultSel, type C14Sel } from './selection';
import { C14ContextView, C14FindingsView } from './C14Common';
import { EveByShockView, OutlierView, ShapesView } from './ShockViews';
import { CapsView, ChangesView, ReplicatingView, WithWithoutView } from './BehaviouralViews';
import { DynamicNiiView, EarEvarView, GapView } from './NiiViews';

const NAMES = ['vd-2021-q4', 'vd-2022-q2', 'vd-2022-q4'] as const;
const models = committedDoc<ModelsArtifact>('C14', 'models-svb-2021-2022');
const title = { en: 'IRRBB on a USD balance sheet', es: 'IRRBB sobre un balance en USD' };
const selOf = (name: string): C14Sel => defaultSel(fixtureData('C14', committedDoc<VariantArtifact>('C14', name), models, title)) as C14Sel;

const VIEWS: Array<[string, (p: { sel: C14Sel | null }) => ReactElement]> = [
  ['EveByShock', EveByShockView], ['Shapes', ShapesView], ['Outlier', OutlierView], ['WithWithout', WithWithoutView],
  ['Replicating', ReplicatingView], ['Caps', CapsView], ['Changes', ChangesView], ['Gap', GapView], ['DynamicNii', DynamicNiiView],
  ['EarEvar', EarEvarView], ['Findings', C14FindingsView], ['Context', C14ContextView],
];
/** Strings a reader must find as they are: a URL, a regulation or a dataset name. */
const VERBATIM = [/https?:\/\/\S+/g, 'Daily Treasury Par Yield Curve Rates', 'US Treasury', 'bootstrap_zero_curve', 'nmd_segments', 'Contraste', 'Silicon Valley Bank', /[a-z]+(?:-[a-z]+){2,}/g];

describe('U16-F4 C14: the Spanish view', () => {
  afterEach(() => setLang('en'));

  it('V14-1: a behavioural parameter is named in words in both languages, never by its contract phrase', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const text = visibleText(html(<ChangesView sel={selOf('vd-2022-q4')} />));
      expect(text).not.toMatch(/requested core|replicating-portfolio/);
    }
    setLang('es');
    const es = visibleText(html(<ChangesView sel={selOf('vd-2022-q4')} />));
    expect(es).toContain('Plazo medio ponderado de la cartera replicante, mayorista');
    expect(es).toContain('Parte estable solicitada, mayorista');
    expect(es).toContain('Plazo estable solicitado, mayorista');
  });

  it('V14-4: the window of a parameter change stays visible at 390 px (From and To are not wide-only columns)', () => {
    const markup = html(<ChangesView sel={selOf('vd-2022-q4')} />);
    const head = markup.slice(markup.indexOf('data-table="parameter-changes"'), markup.indexOf('</thead>'));
    expect(head).not.toMatch(/ct-wide-only[^>]*>(From|To)</);
    expect(markup).toContain('data-window="2021-12-31 2022-06-30"');
    setLang('es');
    expect(visibleText(html(<ChangesView sel={selOf('vd-2022-q4')} />))).toContain('2021-12-31 a 2022-06-30');
  });

  it('V14-3: no view of the Spanish capture carries English prose, on the three committed documents', () => {
    setLang('es');
    const all: string[] = [];
    for (const name of NAMES) {
      for (const [view, View] of VIEWS) {
        for (const leak of englishLeaks(visibleText(html(<View sel={selOf(name)} />)), VERBATIM)) all.push(`${name} ${view} ${leak}`);
      }
    }
    expect([...new Set(all)]).toEqual([]);
  });

  it('V14-2: the y title of the dynamic NII chart is short enough for the plot at 390 px', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const markup = html(<DynamicNiiView sel={selOf('vd-2022-q4')} />);
      const m = /data-y-label="([^"]*)"/.exec(markup);
      if (m) expect(m[1].length).toBeLessThanOrEqual(30);
    }
  });

  it('V14-3: the note of a test row is written in Spanish in the Spanish view and kept in English in the English one', () => {
    const markup = () => visibleText(html(<ChangesView sel={selOf('vd-2022-q4')} />));
    expect(markup()).toContain('2 change(s) coincide with a breach');
    setLang('es');
    expect(markup()).toContain('2 cambios coinciden con un exceso');
  });
});
