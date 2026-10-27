// U16-F10c (R3 batch c09, C08): the rail's Floor section names its segments, the counts per LGD tenth reach a phone, the Downturn
// chart draws the downturn years and marks the cohort the add-on leaves uncovered, the floors axis is the same on every cohort,
// and the Spanish page writes the words the view owns in Spanish (no "proxy", no "Gradient boosting"). Reads the committed
// documents, in both languages.
import type { UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import type { BarChartProps } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { fixtureData, html, setLang } from '../c03/u6-testkit';
import { committed, committedData, view } from './spanish-testkit';
import { useC08Instrument } from './instrument';
import { DistributionView, ProxyView } from './SeverityViews';
import { DownturnView, FloorsView } from './DownturnViews';
import { EndpointsView, RungsView } from './ModelViews';
import { C08ContextView } from './C08Common';
import { defaultSel, outputsOf, type C08Sel } from './selection';

const lines = vi.hoisted(() => [] as UPlotChartProps[]);
const bars = vi.hoisted(() => [] as BarChartProps[]);
vi.mock('@fasl-work/caos-app-shell/chart', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell/chart')>();
  return { ...mod, UPlotChart: (p: UPlotChartProps) => (lines.push(p), mod.UPlotChart(p)) };
});
vi.mock('@fasl-work/caos-app-shell', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell')>();
  return { ...mod, BarChart: (p: BarChartProps) => (bars.push(p), mod.BarChart(p)) };
});

const TITLE = { en: 'LGD and downturn LGD', es: 'LGD y LGD de recesión' };
const COHORTS = ['dc-2003-06', 'dc-2007-08', 'dc-2009-10', 'dc-2011-13', 'dc-2014-19', 'dc-2020-23'];
const selOf = (c: string) => defaultSel(committedData('C08', `${c}.json`, `models-${c}.json`, TITLE)) as C08Sel;

/** A committed document with every Spanish text the producer wrote blanked: what is left in a Spanish view is the view's own words. */
function viewWordsOnly(c: string) {
  const blank = (x: unknown): unknown => {
    if (Array.isArray(x)) return x.map(blank);
    if (x && typeof x === 'object') {
      const o = x as Record<string, unknown>;
      if (typeof o.en === 'string' && typeof o.es === 'string') return { ...o, es: '·' };
      return Object.fromEntries(Object.entries(o).map(([k, v]) => [k, blank(v)]));
    }
    return x;
  };
  const v = blank(committed<VariantArtifact>('C08', `${c}.json`)) as VariantArtifact;
  const m = blank(committed<ModelsArtifact>('C08', `models-${c}.json`)) as ModelsArtifact;
  return defaultSel(fixtureData('C08', v, m, TITLE)) as C08Sel;
}

function Rail({ sel, at }: { sel: C08Sel; at: number }) {
  const inst = useC08Instrument(sel.data, () => undefined);
  return <div>{inst ? inst.rail[at].content : null}</div>;
}
function Groups({ sel }: { sel: C08Sel }) {
  const inst = useC08Instrument(sel.data, () => undefined);
  return <div>{inst ? inst.groups.map((g) => <section key={g.id}>{g.content}</section>) : null}</div>;
}

describe('U16-F10c, C08 (R3 c09)', () => {
  afterEach(() => setLang('en'));

  it('BN1: the Floor section names each segment, in Spanish on the Spanish page, never the id in words', () => {
    const sel = selOf('dc-2009-10');
    setLang('es');
    const es = html(<Rail sel={sel} at={3} />);
    expect(es).toContain('Línea rotativa pyme');
    expect(es).toContain('Préstamo a plazo pyme, de 85 a 239 meses');
    expect(es).not.toMatch(/SME (revolver|term)/);
    // each option is whole in the rail (no ellipsis) and no two read the same
    const opts = (m: string) => [...m.matchAll(/<option[^>]*>([^<]*)<\/option>/g)].map((x) => x[1]);
    expect(opts(es)).toEqual(['Línea rotativa', 'Hasta 84 meses', 'De 85 a 239 meses', '240 meses o más']);
    setLang('en');
    const en = html(<Rail sel={sel} at={3} />);
    expect(en).toContain('SME revolving line');
    expect(en).not.toMatch(/SME term 85 239|SME revolver\b/);
    expect(new Set(opts(en)).size).toBe(4);
    for (const o of [...opts(en), ...opts(es)]) expect(o).not.toContain('…');
  });

  it('MN1: the counts per LGD tenth are a table a phone shows (it scrolls in its box, it is not hidden)', () => {
    const markup = html(<DistributionView sel={selOf('dc-2009-10')} />);
    const cls = /<table class="([^"]*)" data-table="lgd-bins"/.exec(markup)?.[1];
    expect(cls).toBeDefined();
    expect(cls).not.toContain('ct-wide-only');
  });

  it('MN2: the Downturn chart draws the downturn years and marks the uncovered cohort with its shortfall, in both languages', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      lines.length = 0;
      const sel = selOf('dc-2009-10');
      const t = outputsOf(sel)!.downturn;
      html(<DownturnView sel={sel} />);
      const p = lines.at(-1)!;
      const xs = (p.marks ?? []).map((m) => m.x);
      expect(xs).toContain(t.period.first_year);
      expect(xs).toContain(t.period.last_year);
      expect(p.x.range![0]).toBeLessThanOrEqual(t.period.first_year);
      expect(p.x.range![1]).toBeGreaterThanOrEqual(t.period.last_year);
      const uncovered = t.rows.filter((r) => !r.covered);
      expect(uncovered.length).toBeGreaterThan(0);
      const labels = (p.marks ?? []).map((m) => (typeof m.label === 'string' ? m.label : m.label[lang]));
      for (const r of uncovered) expect(labels.join(' | ')).toContain(formatNumber(r.shortfall, lang, { percent: true, decimals: 2 }));
      // covered and uncovered cohorts are two series in two tones, not one red series for both
      const pts = p.series.filter((s) => s.mode === 'points');
      expect(pts).toHaveLength(2);
      expect(new Set(pts.map((s) => s.color)).size).toBe(2);
    }
  });

  it('m9: the floors bar axis is 0 to 100 % on every cohort, so a 0.006 % bar is not drawn full length', () => {
    for (const c of COHORTS) {
      bars.length = 0;
      html(<FloorsView sel={selOf(c)} />);
      expect(bars.at(-1)!.axis.range, c).toEqual([0, 1]);
    }
  });

  it('m1: the rung table and the endpoint RMSE print fixed decimals, so the sensitivity shows', () => {
    const sel = selOf('dc-2003-06');
    const o = outputsOf(sel)!;
    const rungs = view(<RungsView sel={sel} />);
    for (const r of o.rung_comparison) expect(rungs).toContain(formatNumber(r.mae, 'en', { decimals: 3 }));
    const ends = view(<EndpointsView sel={sel} />);
    for (const e of o.endpoint_sensitivity) expect(ends).toContain(formatNumber(e.rmse, 'en', { decimals: 4 }));
  });

  it('m3: the Freddie Mac line does not repeat its own name', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const sel = selOf('dc-2009-10');
      expect(view(<ProxyView sel={sel} />)).not.toMatch(/: Freddie Mac:/);
      expect(view(<C08ContextView sel={sel} />)).not.toMatch(/: Freddie Mac:/);
    }
  });

  it('m11: the proxy totals carry their currency and the Fields row does not repeat the Formula', () => {
    const sel = selOf('dc-2009-10');
    const markup = view(<ProxyView sel={sel} />);
    expect(markup).toMatch(/Charged off, in total [\d,.]+ USD/);
    expect(markup).toMatch(/Approved, in total [\d,.]+ USD/);
    expect(markup).not.toContain('Fields');
  });

  it('the Spanish page writes the words the view owns in Spanish: no proxy, no Gradient boosting, no add-on', () => {
    setLang('es');
    for (const c of ['dc-2009-10', 'dc-2014-19']) {
      const sel = viewWordsOnly(c);
      const markup = view(<Groups sel={sel} />) + view(<ProxyView sel={sel} />) + view(<FloorsView sel={sel} />) + view(<C08ContextView sel={sel} />) + [0, 1, 2, 3].map((at) => view(<Rail sel={sel} at={at} />)).join(' ');
      expect(markup).not.toMatch(/\bproxy\b/i);
      expect(markup).not.toMatch(/Gradient boosting/);
      expect(markup).not.toMatch(/\badd-on\b/);
      expect(markup).toContain('La aproximación de la LGD y su sesgo');
    }
  });

  it('mn5: a retail cell names its portfolio once ("Minorista, revolvente calificado")', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const markup = view(<FloorsView sel={selOf('dc-2009-10')} />);
      expect(markup).not.toMatch(/Minorista, minorista|Retail, qualifying revolving retail/);
      expect(markup).toContain(lang === 'es' ? 'Minorista, revolvente calificado' : 'Retail, qualifying revolving');
    }
  });
});
