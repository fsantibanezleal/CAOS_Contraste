// U16-P2 (BL-091, BL-075): C22's views for the 21 p-value tests outside the five credit families. The null variant lists
// them with their size (the engine's documented excess shown with its measure and page), and the `other-families`
// variant draws their power against the engine's stated alternatives, in both languages. Rendered on the server from the
// committed artifacts, like the other C22 tests.
import { readFileSync } from 'node:fs';
import { afterEach, describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { COMMITTED } from '../../lib/policy';
import { setLang, html, escapeHtml } from '../c03/u6-testkit';
import { START, useC22Instrument } from './instrument';
import { isC22, excessOf, type C22Sel } from './selection';
import { C22FindingsView, GeneratorsView, PValuesView, PowerView, RatesTableView, SizeView } from './Views';

const derived = new URL('../../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const manifest = read<CaseManifest>('manifests/C22.json');
const load = (id: string): CaseData => {
  const a = manifest.artifacts.find((x) => x.variant_id === id);
  if (!a) throw new Error(`C22 has no ${id} variant`);
  return { manifest, variant: read<VariantArtifact>(a.path), models: read<ModelsArtifact>(a.models_ref as string) };
};
const sel = (data: CaseData, level = 0.05): C22Sel => ({ data, alphas: COMMITTED, level, portfolio: { ...START } });
const variant = (data: CaseData) => {
  const v = data.variant as VariantArtifact<unknown>;
  if (!isC22(v)) throw new Error('not a C22 variant');
  return v;
};

const OTHER_PANELS = ['ccr', 'ifrs9', 'lgd-ead', 'market-var', 'market-es', 'portfolio-credit', 'fairness', 'ml'];

describe('C22, the other families', () => {
  afterEach(() => setLang('en'));

  it('the manifest lists the new variant after the eight of the design', () => {
    expect(manifest.artifacts.filter((a) => a.role === 'variant').map((a) => a.variant_id)).toEqual([
      'null', 'miscalibration', 'clustering', 'drift', 'discrimination-decay', 'leakage', 'broken-monotonicity', 'concentration', 'other-families',
    ]);
  });

  it('the null variant draws the 25 studies of the 21 tests in its size table and its p-value histograms', () => {
    const data = load('null');
    const v = variant(data);
    const studies = v.outputs.simulations.filter((s) => s.study);
    expect(studies).toHaveLength(25);
    expect(new Set(studies.map((s) => s.test_id)).size).toBe(21);
    const size = html(<SizeView sel={sel(data)} />);
    for (const s of studies) expect(size, `${s.key}: no row in the size table`).toContain(`data-sim="${s.key}"`);
    const pv = html(<PValuesView sel={sel(data)} />);
    for (const id of OTHER_PANELS) expect(pv, `panel ${id} is not drawn`).toContain(`data-panel="${id}"`);
  });

  it('the documented excess is shown with its measure, its bound and the engine page, in both languages', () => {
    const data = load('null');
    const v = variant(data);
    const row = v.outputs.simulations.find((s) => excessOf(s));
    expect(row?.test_id).toBe('portfolio.mc_convergence');
    const ex = excessOf(row!)!;
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const markup = html(<SizeView sel={sel(data)} />);
      expect(markup).toContain('data-list="documented-excess"');
      expect(markup).toContain(escapeHtml(ex.page));
      expect(markup).toContain(escapeHtml(ex.repository));
      expect(markup).toContain(escapeHtml(ex.engine[lang]));
      expect(markup).toContain(`data-exceeds="${ex.exceeds ? 'yes' : 'no'}"`);
    }
    // the excess is shown at the level it is stated at, whichever level the rail reads
    expect(html(<SizeView sel={sel(data, 0.01)} />)).toContain('data-list="documented-excess"');
  });

  it('the findings of the null variant cite the new studies', () => {
    const data = load('null');
    const markup = html(<C22FindingsView sel={sel(data)} />);
    for (const id of ['F-OTHER-SIZE', 'F-OTHER-MC-EXCESS']) expect(markup).toContain(`data-finding="${id}"`);
  });

  it('the other-families variant draws every panel with two points per study, in both languages', () => {
    const data = load('other-families');
    const v = variant(data);
    expect(v.outputs.ladder?.values).toEqual([0, 1]);
    expect(v.outputs.panels.map((p) => p.id)).toEqual(OTHER_PANELS);
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const markup = html(<PowerView sel={sel(data)} />);
      for (const id of OTHER_PANELS) expect(markup, `${lang}: panel ${id} not drawn`).toContain(`data-panel="${id}"`);
      expect(markup).toContain(lang === 'en' ? 'Two points per study' : 'Dos puntos por estudio');
    }
    const rates = html(<RatesTableView sel={sel(data)} />);
    for (const s of v.outputs.simulations) expect(rates).toContain(`data-sim="${s.key}"`);
    expect(v.outputs.simulations).toHaveLength(50);
    expect(html(<GeneratorsView sel={sel(data)} />)).toContain('data-table="generators"');
  });

  it('the other-families variant has no single report to read: its Validation tabs leave out One report', () => {
    function Validation({ data }: { data: CaseData }) {
      const inst = useC22Instrument(data, () => undefined);
      return <div>{inst?.groups.find((g) => g.id === 'validation')?.content}</div>;
    }
    const other = html(<Validation data={load('other-families')} />);
    expect(other).toContain('Power');
    expect(other).toContain('Rates');
    expect(other).not.toContain('One report');
    expect(variant(load('other-families')).tests).toEqual([]);
    expect(html(<Validation data={load('null')} />)).toContain('One report');
  });
});
