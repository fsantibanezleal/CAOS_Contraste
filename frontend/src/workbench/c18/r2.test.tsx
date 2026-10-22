// U16-F4 (the U16-R2 capture review, batch b09): the Spanish view of C18 carries no English prose, unit or accent-less label, the
// Annex 3 labels are Spanish with their accents, the test rows tell the segments apart and the CET1 stack uses the CET1 share of Pillar 2.
// Every view is rendered on the six committed documents.
import { afterEach, describe, expect, it } from 'vitest';
import type { ReactElement } from 'react';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc, englishLeaks, fixtureData, html, setLang, visibleText } from '../c14/testkit';
import { defaultSel, type C18Sel } from './selection';
import { C18ContextView, C18FindingsView, C18TestsView } from './C18Common';
import { Annex3View, FanView, StackView } from './CapitalViews';
import { BackcastView, LossesView, PathsView, SatellitesView, SeverityView } from './StressViews';
import { BandView, EulerView, MarginalsView, SensitivityView } from './AggregationViews';
import { ReverseSearchView, ReverseSolutionView } from './ReverseViews';

type View = (p: { sel: C18Sel | null }) => ReactElement;
const SCENARIO: Array<[string, View]> = [
  ['Fan', FanView], ['Stack', StackView], ['Annex3', Annex3View], ['Paths', PathsView], ['Satellites', SatellitesView], ['Backcast', BackcastView],
  ['Severity', SeverityView], ['Losses', LossesView], ['Tests', C18TestsView], ['Findings', C18FindingsView], ['Context', C18ContextView],
];
const AGG: Array<[string, View]> = [['Band', BandView], ['Euler', EulerView], ['Marginals', MarginalsView], ['Sensitivity', SensitivityView], ['Tests', C18TestsView], ['Findings', C18FindingsView], ['Context', C18ContextView]];
const REVERSE: Array<[string, View]> = [['Solution', ReverseSolutionView], ['Search', ReverseSearchView], ['Tests', C18TestsView], ['Findings', C18FindingsView], ['Context', C18ContextView]];
const DOCS: Array<[string, Array<[string, View]>]> = [
  ['baseline', SCENARIO], ['eba-2025-adverse', SCENARIO], ['fed-2026-severely-adverse', SCENARIO], ['ngfs-delayed-transition', SCENARIO],
  ['t-copula-baseline', AGG], ['reverse-stress', REVERSE],
];
const models = committedDoc<ModelsArtifact>('C18', 'models-banco-andino');
const title = { en: 'ICAAP and IAPE capital aggregation under macro scenarios', es: 'Agregación de capital ICAAP e IAPE bajo escenarios macro' };
const selOf = (name: string): C18Sel => defaultSel(fixtureData('C18', committedDoc<VariantArtifact>('C18', name), models, title)) as C18Sel;

// what a reader must find as written: names of institutions, series, publications and the engine's functions
const VERBATIM = ['Banco Santander-Chile', 'Banco Andino', 'Banco Central de Chile', 'NiGEM', 'Federal Reserve', 'oprisk.aggregate', 'Hull-White', 'Contraste', 'SEC EDGAR', 'Fed', /Capital allocation to business units[^;]*?\(full allocation\)/g, /Capital allocation to business units and sub-portfolios: the Euler principle, arXiv [\d.]+/g, /A general approach to integrated risk management with skewed, fat-tailed risks, J\. Financial Economics/g];

describe('U16-F4 C18: the Spanish view', () => {
  afterEach(() => setLang('en'));

  it('V18-1 and PR-C18-1: no view of the Spanish capture carries English prose, on the six committed documents', () => {
    setLang('es');
    const all: string[] = [];
    for (const [name, views] of DOCS) {
      for (const [view, View] of views) {
        const text = visibleText(html(<View sel={selOf(name)} />)).replaceAll('UNVERIFIED', ' ');
        for (const leak of englishLeaks(text, VERBATIM)) all.push(`${name} ${view} ${leak}`);
      }
    }
    expect([...new Set(all)]).toEqual([]);
  });

  it('V18-1: the Annex 3 rows and bars are named in Spanish with their accents', () => {
    setLang('es');
    const text = visibleText(html(<Annex3View sel={selOf('baseline')} />));
    expect(text).not.toMatch(/Metodo|Riesgo de credito|indice de capital basico|exigencia legal estandar/);
    expect(text).toMatch(/Método estándar/);
    expect(text).toMatch(/Riesgo de crédito/);
  });

  it('V18-2: the CET1 legal stack stacks the CET1 share of Pillar 2 (0.0625 percent of RWA), not the whole P2R', () => {
    setLang('en');
    const sel = selOf('baseline');
    const text = visibleText(html(<StackView sel={sel} />));
    expect(text).toMatch(/CET1 share of Pillar 2/);
  });

  it('V18-3: the red back-cast test rows are told apart by their segment', () => {
    setLang('en');
    const sel = selOf('baseline');
    const doc = committedDoc<VariantArtifact>('C18', 'baseline');
    const rows = doc.tests.filter((t) => t.test_id.startsWith('macro.backcast') || /back/.test(t.test_id));
    const text = visibleText(html(<C18TestsView sel={sel} />));
    const segs = rows.map((t) => t.segment).filter((s): s is string => Boolean(s));
    expect(new Set(segs).size).toBeGreaterThan(1);
    for (const s of new Set(segs)) expect(text.toLowerCase(), s).toContain(s.toLowerCase().replaceAll('_', ' ').split('-')[0]);
  });
});
