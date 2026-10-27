// U16-F12c (R4 batches c12 and c13, C10): the minors of the batches that the view owns. The headline counts the years that have a rate
// (m-N4), the profile-likelihood and density axes read the correlation and the loss rate with their decimals (c13 n3), the rung that
// does not run names no engine function (m-N3, c13 n5), the granularity level table writes δ (c13 n5), the LHP anchor's segment writes
// its percent as the shell does (n7, c13 n6), a missing year of the Federal Reserve table is one row named by its year (c13 n8) and the
// simulator grid card carries the simulator's badge on every variant (c13 n4). Reads the committed documents, in both languages.
import type { UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { html, setLang } from '../c03/u6-testkit';
import { committedData, view } from '../c08/spanish-testkit';
import { CorrelationView, FittedView } from './FitViews';
import { GranularityView } from './CapitalViews';
import { EstimatorsView, LadderView } from './ModelViews';
import { C10ContextView, segmentText } from './C10Common';
import { defaultSel, fitOf, referenceNote, type C10Sel } from './selection';

const lines = vi.hoisted(() => [] as UPlotChartProps[]);
vi.mock('@fasl-work/caos-app-shell/chart', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell/chart')>();
  return { ...mod, UPlotChart: (p: UPlotChartProps) => (lines.push(p), mod.UPlotChart(p)) };
});

const TITLE = { en: 'Portfolio credit capital', es: 'Capital de crédito de cartera' };
const LOANS = ['commercial-industrial', 'commercial-real-estate', 'credit-cards', 'other-consumer', 'residential'];
const GRIDS = ['grid-22', 'grid-40'];
const selOf = (v: string) => defaultSel(committedData('C10', `${v}.json`, 'models-c10.json', TITLE)) as C10Sel;
const NBSP = ' ';

describe('U16-F12c, C10 (R4 c12 and c13)', () => {
  afterEach(() => setLang('en'));

  it('m-N4: the fitted headline says the years of the fit window that have a rate, in both languages', () => {
    const en = view(<FittedView sel={selOf('commercial-industrial')} />);
    expect(en).toContain('years of the fit window have a rate');
    expect(en).not.toContain('carry a rate');
    setLang('es');
    const es = view(<FittedView sel={selOf('commercial-industrial')} />);
    expect(es).toContain('años de la ventana de ajuste tienen tasa');
    expect(es).not.toContain('traen una tasa');
  });

  it('c13 n3: the profile-likelihood axis reads the correlation with one decimal and the density axis the loss rate with two', () => {
    lines.length = 0;
    html(<CorrelationView sel={selOf('other-consumer')} />);
    expect(lines.at(-1)!.x.format).toEqual({ percent: true, decimals: 1 });
    lines.length = 0;
    html(<FittedView sel={selOf('other-consumer')} />);
    expect(lines.at(-1)!.x.format).toEqual({ percent: true, decimals: 2 });
  });

  it('m-N3: a rung that does not run names no engine function, on every variant and in both languages', () => {
    for (const v of [...LOANS, ...GRIDS]) {
      for (const lang of ['en', 'es'] as const) {
        setLang(lang);
        const sel = selOf(v);
        const markup = html(<LadderView sel={sel} />);
        const off = fitOf(sel)!.ladder.filter((r) => !r.evaluated);
        expect(off.length, v).toBeGreaterThan(0);
        for (const r of off) {
          const row = new RegExp(`<tr[^>]*data-rung="${r.id}"[^>]*>(.*?)</tr>`, 's').exec(markup)?.[1] ?? '';
          expect(row, `${v} ${r.id}`).not.toBe('');
          expect(row).not.toContain(r.engine_function);
          expect(row).toContain(lang === 'en' ? 'none: the rung does not run' : 'ninguna: el escalón no corre');
        }
      }
    }
  });

  it('c13 n5: the reference the producer now writes for the rung with no twist reads in Spanish', () => {
    expect(referenceNote('Glasserman and Li (2005); no Student-t twist is specified, so the rung does not run', 'es')).toBe(
      'Glasserman y Li (2005); no se especifica una inclinación para la t de Student, así que el escalón no corre',
    );
  });

  it('c13 n5: the granularity level table and its note write the Greek δ, never the word delta', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const markup = html(<GranularityView sel={selOf('residential')} />);
      expect(markup).toContain('<th>δ</th>');
      expect(view(<GranularityView sel={selOf('residential')} />)).not.toMatch(/\bdelta\b/);
    }
  });

  it('n7: the LHP anchor segment writes 99.9 % with the shell\'s no-break space, as the Euler segments do', () => {
    expect(segmentText('lhp-like-99.9', 'en')).toBe(`the LHP anchor at 99.9${NBSP}%`);
    expect(segmentText('lhp-like-99.9', 'es')).toBe(`el ancla LHP al 99,9${NBSP}%`);
    expect(segmentText('var-0.999', 'en')).toBe(`VaR at 99.9${NBSP}%`);
  });

  it('c13 n8: a year the table lacks is one row named by the year and its quarters, in both languages', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const markup = html(<C10ContextView sel={selOf('residential')} />);
      const t = /<table[^>]*data-table="c10-missing-quarters"[^>]*>(.*?)<\/table>/s.exec(markup)?.[1] ?? '';
      const first = [...t.matchAll(/<tr[^>]*data-quarter="[^"]*"[^>]*><td[^>]*>(.*?)<\/td>/gs)].map((m) => m[1]);
      expect(first[0]).toBe(lang === 'en' ? '1985, Q1 to Q4' : '1985, T1 a T4');
      expect(t).toContain(lang === 'en' ? 'Missing quarters' : 'Trimestres faltantes');
    }
  });

  it('c13 n4: the simulator grid card is badged synthetic on a loan-type variant too', () => {
    const markup = html(<EstimatorsView sel={selOf('commercial-industrial')} />);
    const card = markup.split('<figure class="caos-plot').slice(1).find((c) => c.includes('The simulator grid')) ?? '';
    expect(card).toContain('data-provenance="synthetic"');
    expect(card).not.toContain('data-provenance="real"');
  });
});
