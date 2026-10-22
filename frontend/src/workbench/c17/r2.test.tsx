// U16-F4 (the U16-R2 capture review, batch b08): the Spanish view of C17 carries no English tag or reference, the Panjer curve is
// not drawn past its grid, the SMA note is computed from the committed rows and the sample sizes shown are the ones the medians
// rest on. Every view is rendered on the four committed documents.
import { afterEach, describe, expect, it } from 'vitest';
import type { ReactElement } from 'react';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc, englishLeaks, fixtureData, html, setLang, visibleText } from '../c14/testkit';
import { capitalOf, defaultSel, outputsOf, type C17Sel } from './selection';
import { C17ContextView, C17FindingsView, RungReadout } from './C17Common';
import { ByMethodView, ByYearsView, ScenarioView } from './CapitalViews';
import { ExceedanceView, TailIndexView, exceedanceChart } from './LossViews';
import { LadderView, SmaSpecView } from './ModelViews';
import { ResponseView, SmaView } from './SmaViews';

const NAMES = ['xi-0-6', 'xi-0-8', 'xi-0-96', 'xi-1-1'] as const;
const models = committedDoc<ModelsArtifact>('C17', 'models-generator');
const title = { en: 'Operational risk: LDA vs SMA', es: 'Riesgo operacional: LDA vs SMA' };
const selOf = (name: string): C17Sel => defaultSel(fixtureData('C17', committedDoc<VariantArtifact>('C17', name), models, title)) as C17Sel;

const VIEWS: Array<[string, (p: { sel: C17Sel | null }) => ReactElement]> = [
  ['Exceedance', ExceedanceView], ['TailIndex', TailIndexView], ['ByMethod', ByMethodView], ['ByYears', ByYearsView], ['Scenarios', ScenarioView],
  ['Sma', SmaView], ['Response', ResponseView], ['Ladder', LadderView], ['Spec', SmaSpecView], ['Findings', C17FindingsView], ['Context', C17ContextView],
];
const VERBATIM = ['Mignola and Ugoccioni', 'Shevchenko', 'Basel', 'Contraste', 'Frachot', 'Cope', 'Opdyke', 'Cruz', 'Chernobai', 'Embrechts', 'LDCE', /\(\d{4}\)/g];

describe('U16-F4 C17: the Spanish view', () => {
  afterEach(() => setLang('en'));

  it('V17-1: no view of the Spanish capture carries an English tag, reference or sentence, on the four committed documents', () => {
    setLang('es');
    const all: string[] = [];
    for (const name of NAMES) {
      for (const [view, View] of VIEWS) {
        const text = visibleText(html(<View sel={selOf(name)} />));
        for (const leak of englishLeaks(text.replaceAll('UNVERIFIED', ' ').replaceAll('rung', ' '), VERBATIM)) all.push(`${name} ${view} ${leak}`);
        if (/UNVERIFIED|\brung\b/.test(text)) all.push(`${name} ${view} English tag: ${/(.{20})(UNVERIFIED|\brung\b)(.{20})/.exec(text)?.[0]}`);
      }
    }
    expect([...new Set(all)]).toEqual([]);
  });

  it('PR-C17: the Panjer exceedance is drawn only where the recursion computes it (no flat plateau as data)', () => {
    // the documents past the recursion grid hold nulls, never the last value repeated
    expect(NAMES.some((n) => (outputsOf(selOf(n))!.exceedance.panjer.exceedance as Array<number | null>).includes(null))).toBe(true);
    for (const name of NAMES) {
      const o = outputsOf(selOf(name))!;
      const values = exceedanceChart(o.exceedance, o.truth).series.find((s) => (s.label as { en: string }).en === 'Panjer recursion')!.values;
      const points = o.exceedance.panjer.exceedance as Array<number | null>;
      expect(values.length, name).toBe(points.length);
      // a point past the grid is a gap, never the last value repeated
      const lastReal = points.map((v) => v !== null).lastIndexOf(true);
      for (let i = lastReal + 1; i < points.length; i++) expect(values[i], `${name} ${i}`).toBeNull();
      expect(points.slice(lastReal + 1).every((v) => v === null), name).toBe(true);
      if (lastReal < points.length - 1) expect(visibleText(html(<ExceedanceView sel={selOf(name)} />)), name).toMatch(/the recursion grid ends at/);
    }
  });

  it('V17-2: the SMA response note is computed from the committed rows and names the larger relative rise', () => {
    for (const name of NAMES) {
      setLang('en');
      const en = visibleText(html(<ResponseView sel={selOf(name)} />));
      expect(en, name).not.toMatch(/changes far less/);
      expect(en, name).toMatch(/SMA capital rises by [\d.,]+ percent[^.]*the LDA capital rises by [\d.,]+ percent/);
      setLang('es');
      expect(visibleText(html(<ResponseView sel={selOf(name)} />)), name).toMatch(/el capital SMA sube [\d.,]+ por ciento[^.]*el capital LDA sube [\d.,]+ por ciento/);
    }
  });

  it('V17-3: the sample size shown beside a splice median is the number of histories it rests on', () => {
    const sel0 = selOf('xi-1-1');
    const o = outputsOf(sel0)!;
    const cell = o.cells.find((c) => (capitalOf(c, 'lda-splice').summary?.n_defined ?? 1000) < c.replications.n_replications)!;
    expect(cell).toBeTruthy();
    const sel: C17Sel = { ...sel0, rung: 'lda-splice', years: cell.years, threshold: cell.collection_threshold_eur };
    const years = html(<ByYearsView sel={sel} />);
    const n = capitalOf(cell, 'lda-splice').summary!.n_defined;
    expect(years).toMatch(new RegExp(String.raw`data-cell="${cell.id}"[\s\S]*?data-n-defined="${n}"`));
    // the rail says it too
    expect(visibleText(html(<RungReadout sel={sel} />))).toContain(`${n}`);
  });
});
